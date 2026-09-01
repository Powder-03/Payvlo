"""Price Quotation and Deterministic Discount Clamping Service."""
import uuid
import json
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.orm import sessionmaker

from ..core.config import settings
from ..core.exceptions import MerchantConfigError, ProductNotFoundError, OutOfStockError
from ..models.quote import QuoteModel
from ..schemas.quote import (
    QuoteRequestInputSchema,
    QuoteResponseSchema,
    QuoteItemSchema,
)
from .catalog_service import CatalogService
from .audit_service import AuditService, hash_user_id


class QuoteService:
    """Computes deterministic discount clamped quotes and manages quote lifecycles."""

    def __init__(
        self,
        session_factory: sessionmaker,
        catalog_service: CatalogService,
        audit_service: Optional[AuditService] = None,
        default_merchant_id: str = "dominos_in",
        quote_validity_minutes: int = 15,
    ):
        self.session_factory = session_factory
        self.catalog_service = catalog_service
        self.audit_service = audit_service
        self.default_merchant_id = default_merchant_id
        self.quote_validity_minutes = quote_validity_minutes

    def get_quote(self, quote_id: str) -> Optional[QuoteModel]:
        with self.session_factory() as session:
            return session.query(QuoteModel).filter_by(quote_id=quote_id).first()

    def mark_quote_consumed(self, quote_id: str) -> None:
        with self.session_factory() as session:
            q = session.query(QuoteModel).filter_by(quote_id=quote_id).first()
            if q:
                q.status = "CONSUMED"
                session.commit()

    def calculate_quote(self, request: QuoteRequestInputSchema) -> QuoteResponseSchema:
        merchant_id = request.merchant_id or self.default_merchant_id
        merchant = self.catalog_service.get_merchant(merchant_id)
        if not merchant:
            raise MerchantConfigError(merchant_id, "Merchant profile not found.")

        quote_items: List[QuoteItemSchema] = []
        total_original_price = 0.0
        total_discount_amount = 0.0
        clamping_reasons: List[str] = []

        for req_item in request.items:
            product = self.catalog_service.get_product(merchant_id, req_item.product_id)
            if not product:
                raise ProductNotFoundError(req_item.product_id, merchant_id)

            if product.inventory_count < req_item.quantity:
                raise OutOfStockError(
                    product.product_id, req_item.quantity, product.inventory_count
                )

            requested_discount = max(
                req_item.requested_discount_pct, request.overall_requested_discount_pct
            )

            # Pure deterministic clamping: min(requested, product.max, merchant.max)
            effective_discount = min(
                requested_discount,
                product.max_discount_percentage,
                merchant.max_discount_percentage,
            )

            clamping_reason = None
            if requested_discount > effective_discount:
                clamping_reason = (
                    f"Requested {requested_discount:.1f}% discount was clamped to "
                    f"{effective_discount:.1f}% due to max allowed caps "
                    f"(Product cap: {product.max_discount_percentage:.1f}%, "
                    f"Merchant cap: {merchant.max_discount_percentage:.1f}%)."
                )
                clamping_reasons.append(f"SKU {product.sku}: {clamping_reason}")

            subtotal = round(product.price_inr * req_item.quantity, 2)
            item_discount = round(subtotal * (effective_discount / 100.0), 2)
            final_item_price = round(subtotal - item_discount, 2)

            total_original_price += subtotal
            total_discount_amount += item_discount

            quote_items.append(
                QuoteItemSchema(
                    product_id=product.product_id,
                    sku=product.sku,
                    title=product.title,
                    quantity=req_item.quantity,
                    unit_price=product.price_inr,
                    requested_discount_pct=requested_discount,
                    effective_discount_pct=effective_discount,
                    discount_amount=item_discount,
                    subtotal=subtotal,
                    final_price=final_item_price,
                    clamping_reason=clamping_reason,
                )
            )

        final_total_price = round(total_original_price - total_discount_amount, 2)
        quote_id = f"quot_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=self.quote_validity_minutes)

        created_at_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        expires_at_str = expires.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Persist Quote in DB
        with self.session_factory() as session:
            quote_model = QuoteModel(
                quote_id=quote_id,
                merchant_id=merchant_id,
                items_json=json.dumps([item.model_dump() for item in quote_items]),
                total_original_price=total_original_price,
                total_discount_amount=total_discount_amount,
                final_total_price=final_total_price,
                currency=merchant.currency or "INR",
                clamped_discount_reasons_json=json.dumps(clamping_reasons),
                created_at=created_at_str,
                expires_at=expires_at_str,
                status="ACTIVE",
            )
            session.add(quote_model)
            session.commit()

        # Audit logging
        if self.audit_service:
            self.audit_service.record_audit(
                merchant_id=merchant_id,
                user_id_hash=hash_user_id("anonymous_quote_requester"),
                action="QUOTE_GENERATED",
                status="SUCCESS",
                explainability_notes=(
                    f"Generated quote for {len(quote_items)} items. Total: ₹{final_total_price:.2f}. "
                    f"Discount Clamping Applied: {len(clamping_reasons) > 0}."
                ),
                quote_id=quote_id,
                amount=final_total_price,
                currency=merchant.currency or "INR",
            )

        return QuoteResponseSchema(
            quote_id=quote_id,
            merchant_id=merchant_id,
            items=quote_items,
            total_original_price=total_original_price,
            total_discount_amount=total_discount_amount,
            final_total_price=final_total_price,
            currency=merchant.currency or "INR",
            clamped_discount_reasons=clamping_reasons,
            created_at=created_at_str,
            expires_at=expires_at_str,
            status="ACTIVE",
            explainability={
                "merchant_cap_pct": merchant.max_discount_percentage,
                "discounts_clamped": len(clamping_reasons) > 0,
                "validity_minutes": self.quote_validity_minutes,
            },
        )
