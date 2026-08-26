"""Use case for calculating deterministic quotes and zero-trust discount clamping.

Clean Architecture layer: Application.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List

from ...domain.entities import Quote, QuoteItem, AuditEntry
from ...domain.ports import ICatalogRepository, IAuditRepository
from ...domain.exceptions import (
    MerchantConfigError,
    ProductNotFoundError,
    OutOfStockError,
)
from ..dto import (
    QuoteRequestInputDTO,
    QuoteResponseDTO,
    QuoteItemDTO,
)


class RequestQuoteUseCase:
    """Use case to compute deterministic clamped pricing and issue a bound quotation."""

    def __init__(
        self,
        catalog_repo: ICatalogRepository,
        audit_repo: IAuditRepository,
        default_merchant_id: str,
        quote_validity_minutes: int = 15,
    ):
        self.catalog_repo = catalog_repo
        self.audit_repo = audit_repo
        self.default_merchant_id = default_merchant_id
        self.quote_validity_minutes = quote_validity_minutes

    def execute(self, request: QuoteRequestInputDTO) -> QuoteResponseDTO:
        merchant_id = request.merchant_id or self.default_merchant_id
        merchant = self.catalog_repo.get_merchant(merchant_id)
        if not merchant:
            raise MerchantConfigError(merchant_id, "Merchant profile not found.")

        quote_items: List[QuoteItem] = []
        total_original_price = 0.0
        total_discount_amount = 0.0
        clamping_reasons: List[str] = []

        for req_item in request.items:
            product = self.catalog_repo.get_product(merchant_id, req_item.product_id)
            if not product:
                raise ProductNotFoundError(req_item.product_id, merchant_id)

            if not product.is_available(req_item.quantity):
                raise OutOfStockError(
                    product.product_id, req_item.quantity, product.inventory_count
                )

            # Combine item-level requested discount with overall requested discount
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
                QuoteItem(
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
        quote_id = f"qt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(minutes=self.quote_validity_minutes)).isoformat()

        quote = Quote(
            quote_id=quote_id,
            merchant_id=merchant_id,
            items=quote_items,
            total_original_price=round(total_original_price, 2),
            total_discount_amount=round(total_discount_amount, 2),
            final_total_price=final_total_price,
            currency=merchant.currency,
            clamped_discount_reasons=clamping_reasons,
            created_at=now.isoformat(),
            expires_at=expires_at,
            status="ACTIVE",
        )

        self.catalog_repo.save_quote(quote)

        # Audit ledger logging
        audit_entry = AuditEntry(
            audit_id=f"aud_{uuid.uuid4().hex[:12]}",
            timestamp=now.isoformat(),
            merchant_id=merchant_id,
            user_id_hash="anonymous_agent",
            action="QUOTE_GENERATED",
            idempotency_key=None,
            quote_id=quote_id,
            order_id=None,
            amount=final_total_price,
            currency=merchant.currency,
            masked_pii_payload={"items_count": len(quote_items)},
            status="SUCCESS",
            explainability_notes=(
                f"Quoted ₹{final_total_price:.2f} for {len(quote_items)} line items. "
                f"Discount savings: ₹{total_discount_amount:.2f}."
            ),
        )
        self.audit_repo.record_audit(audit_entry)

        return QuoteResponseDTO(
            quote_id=quote.quote_id,
            merchant_id=quote.merchant_id,
            items=[
                QuoteItemDTO(
                    product_id=it.product_id,
                    sku=it.sku,
                    title=it.title,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    requested_discount_pct=it.requested_discount_pct,
                    effective_discount_pct=it.effective_discount_pct,
                    discount_amount=it.discount_amount,
                    subtotal=it.subtotal,
                    final_price=it.final_price,
                    clamping_reason=it.clamping_reason,
                )
                for it in quote.items
            ],
            total_original_price=quote.total_original_price,
            total_discount_amount=quote.total_discount_amount,
            final_total_price=quote.final_total_price,
            currency=quote.currency,
            clamped_discount_reasons=quote.clamped_discount_reasons,
            created_at=quote.created_at,
            expires_at=quote.expires_at,
            status=quote.status,
            explainability={
                "clamped": len(clamping_reasons) > 0,
                "merchant_cap_pct": merchant.max_discount_percentage,
                "validity_minutes": self.quote_validity_minutes,
            },
        )
