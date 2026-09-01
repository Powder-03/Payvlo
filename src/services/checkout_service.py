"""Checkout, Spend Bounds, Idempotency Locks, and Payment Rails Service."""
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import sessionmaker

from ..core.exceptions import (
    SpendCapExceededError,
    OutOfStockError,
    QuoteExpiredError,
    PolicyViolationError,
    MerchantConfigError,
)
from ..models.order import OrderModel
from ..schemas.checkout import CheckoutInputSchema, CheckoutResponseSchema, AddressSchema
from .catalog_service import CatalogService
from .quote_service import QuoteService
from .gatekeeper_service import GatekeeperService
from .payment_service import PaymentService
from .audit_service import AuditService, hash_user_id, mask_shipping_address
from .auth_service import AuthService


class CheckoutService:
    """Orchestrates bounded checkout, spend verification, idempotency locks, and payment rails."""

    def __init__(
        self,
        session_factory: sessionmaker,
        catalog_service: CatalogService,
        quote_service: QuoteService,
        gatekeeper_service: GatekeeperService,
        payment_service: PaymentService,
        audit_service: AuditService,
        auth_service: Optional[AuthService] = None,
        default_merchant_id: str = "dominos_in",
    ):
        self.session_factory = session_factory
        self.catalog_service = catalog_service
        self.quote_service = quote_service
        self.gatekeeper = gatekeeper_service
        self.payment_service = payment_service
        self.audit_service = audit_service
        self.auth_service = auth_service
        self.default_merchant_id = default_merchant_id

    def execute_checkout(self, req: CheckoutInputSchema) -> CheckoutResponseSchema:
        merchant_id = req.merchant_id or self.default_merchant_id
        merchant = self.catalog_service.get_merchant(merchant_id)
        if not merchant:
            raise MerchantConfigError(merchant_id, "Merchant profile does not exist.")

        user_id_hash = hash_user_id(req.user_id)
        shipping_addr_dict = None

        # 0. Resolve Shipping Address (Direct DTO or Saved Address Label Shortcut)
        if req.shipping_address:
            shipping_addr_dict = req.shipping_address.model_dump()
        elif req.address_label and self.auth_service:
            saved = self.auth_service.get_user_address_by_label(req.user_id, req.address_label)
            if saved:
                line2_combined = saved.line2
                if req.fulfillment_notes:
                    line2_combined = (
                        f"{saved.line2} ({req.fulfillment_notes})"
                        if saved.line2
                        else req.fulfillment_notes
                    )

                shipping_addr_dict = {
                    "line1": saved.line1,
                    "line2": line2_combined,
                    "city": saved.city,
                    "state": saved.state,
                    "postal_code": saved.postal_code,
                    "country": saved.country,
                    "phone": saved.phone,
                    "email": saved.email,
                }

        masked_address = mask_shipping_address(shipping_addr_dict)

        # 1. 24h Idempotency Key Lock (Redis Gatekeeper)
        is_new_tx, cached_json = self.gatekeeper.check_and_acquire_idempotency(
            idempotency_key=req.idempotency_key,
            payload="",
            ttl_seconds=86400,
        )

        if not is_new_tx and cached_json:
            try:
                cached_data = json.loads(cached_json)
                self.audit_service.record_audit(
                    merchant_id=merchant_id,
                    user_id_hash=user_id_hash,
                    action="IDEMPOTENCY_REPLAY",
                    idempotency_key=req.idempotency_key,
                    quote_id=req.quote_id,
                    order_id=cached_data.get("order_id"),
                    amount=cached_data.get("final_amount", 0.0),
                    currency=cached_data.get("currency", "INR"),
                    masked_pii_payload=masked_address,
                    status="REPLAYED",
                    explainability_notes=(
                        f"Idempotent transaction replayed successfully. "
                        f"Existing Order ID: {cached_data.get('order_id')}."
                    ),
                )
                return CheckoutResponseSchema(
                    order_id=cached_data["order_id"],
                    idempotency_key=req.idempotency_key,
                    merchant_id=merchant_id,
                    quote_id=req.quote_id,
                    final_amount=cached_data["final_amount"],
                    currency=cached_data.get("currency", "INR"),
                    payment_rail_id=cached_data["payment_rail_id"],
                    payment_status=cached_data["payment_status"],
                    payment_link=cached_data["payment_link"],
                    audit_id=cached_data["audit_id"],
                    is_replayed=True,
                    explainability_notes="Replay of previously processed transaction (Zero Double-Charge Guarantee).",
                    created_at=cached_data["created_at"],
                )
            except Exception:
                pass

        # 1.1 Secondary Idempotency check against Database
        with self.session_factory() as session:
            existing_order = (
                session.query(OrderModel)
                .filter_by(idempotency_key=req.idempotency_key)
                .first()
            )
            if existing_order:
                self.audit_service.record_audit(
                    merchant_id=merchant_id,
                    user_id_hash=user_id_hash,
                    action="IDEMPOTENCY_REPLAY",
                    idempotency_key=req.idempotency_key,
                    quote_id=req.quote_id,
                    order_id=existing_order.order_id,
                    amount=existing_order.final_amount,
                    currency=existing_order.currency,
                    masked_pii_payload=masked_address,
                    status="REPLAYED",
                    explainability_notes=(
                        f"Idempotent transaction replayed from database. "
                        f"Existing Order ID: {existing_order.order_id}."
                    ),
                )
                return CheckoutResponseSchema(
                    order_id=existing_order.order_id,
                    idempotency_key=existing_order.idempotency_key,
                    merchant_id=merchant_id,
                    quote_id=existing_order.quote_id,
                    final_amount=existing_order.final_amount,
                    currency=existing_order.currency,
                    payment_rail_id=existing_order.payment_rail_id,
                    payment_status=existing_order.payment_status,
                    payment_link=existing_order.payment_link,
                    audit_id=existing_order.audit_id,
                    is_replayed=True,
                    explainability_notes="Replay of previously processed transaction (Zero Double-Charge Guarantee).",
                    created_at=existing_order.created_at,
                )

        # 2. Retrieve and Validate Quote
        quote = self.quote_service.get_quote(req.quote_id)
        if not quote:
            raise PolicyViolationError(
                "QUOTE_NOT_FOUND", f"Price quote '{req.quote_id}' does not exist."
            )

        # Expiration check
        try:
            exp_time = datetime.fromisoformat(quote.expires_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp_time:
                raise QuoteExpiredError(quote.quote_id, quote.expires_at)
        except (ValueError, TypeError):
            pass

        if quote.status != "ACTIVE":
            raise PolicyViolationError(
                "QUOTE_ALREADY_CONSUMED",
                f"Price quote '{quote.quote_id}' has already been consumed or closed.",
            )

        # 3. User Budget Constraint Check
        if quote.final_total_price > req.max_spend_budget:
            self.audit_service.record_audit(
                merchant_id=merchant_id,
                user_id_hash=user_id_hash,
                action="SPEND_CAP_REJECTED",
                idempotency_key=req.idempotency_key,
                quote_id=quote.quote_id,
                amount=quote.final_total_price,
                currency=quote.currency,
                masked_pii_payload=masked_address,
                status="REJECTED",
                explainability_notes=(
                    f"Order total ₹{quote.final_total_price:.2f} exceeded user agent's "
                    f"authorized budget of ₹{req.max_spend_budget:.2f}."
                ),
            )
            raise SpendCapExceededError(
                attempted_amount=quote.final_total_price,
                limit_amount=req.max_spend_budget,
                limit_type="USER_AGENT_MAX_BUDGET",
            )

        # 4. Merchant Per-Transaction Cap Check
        if quote.final_total_price > merchant.per_tx_spend_cap:
            raise SpendCapExceededError(
                attempted_amount=quote.final_total_price,
                limit_amount=merchant.per_tx_spend_cap,
                limit_type="MERCHANT_PER_TX_CAP",
            )

        # 5. Atomic Redis Gatekeeper Spend Cap Check (sub-ms Lua script)
        approved, reason, _, _ = self.gatekeeper.check_and_record_spend(
            merchant_id=merchant_id,
            user_id=req.user_id,
            amount=quote.final_total_price,
            user_budget=req.max_spend_budget,
            merchant_cap=merchant.daily_merchant_spend_cap,
        )

        if not approved:
            self.audit_service.record_audit(
                merchant_id=merchant_id,
                user_id_hash=user_id_hash,
                action="GATEKEEPER_SPEND_REJECTED",
                idempotency_key=req.idempotency_key,
                quote_id=quote.quote_id,
                amount=quote.final_total_price,
                currency=quote.currency,
                masked_pii_payload=masked_address,
                status="REJECTED",
                explainability_notes=f"Gatekeeper spend cap rejected: {reason}",
            )
            raise SpendCapExceededError(
                attempted_amount=quote.final_total_price,
                limit_amount=merchant.daily_merchant_spend_cap,
                limit_type=reason,
                message=f"Spend cap rejected by gatekeeper: {reason}.",
            )

        # 6. Inventory Deduction
        quote_items = json.loads(quote.items_json or "[]")
        try:
            for item in quote_items:
                self.catalog_service.update_inventory(
                    merchant_id=merchant_id,
                    product_id_or_sku=item["product_id"],
                    quantity_delta=-item["quantity"],
                )
        except OutOfStockError as oos:
            self.gatekeeper.release_spend(
                merchant_id=merchant_id,
                user_id=req.user_id,
                amount=quote.final_total_price,
            )
            raise oos

        # 7. Create Payment Order on Razorpay
        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        notes = {
            "idempotency_key": req.idempotency_key,
            "user_id_hash": user_id_hash,
            "quote_id": quote.quote_id,
            "merchant_id": merchant_id,
        }

        try:
            rail_result = self.payment_service.create_order(
                merchant_id=merchant_id,
                order_id=order_id,
                amount_in_inr=quote.final_total_price,
                currency=quote.currency,
                notes=notes,
            )
        except Exception as ex:
            # Rollback inventory and spend reservation
            for item in quote_items:
                try:
                    self.catalog_service.update_inventory(
                        merchant_id=merchant_id,
                        product_id_or_sku=item["product_id"],
                        quantity_delta=item["quantity"],
                    )
                except Exception:
                    pass
            self.gatekeeper.release_spend(
                merchant_id=merchant_id,
                user_id=req.user_id,
                amount=quote.final_total_price,
            )
            raise ex

        # 8. Mark Quote as Consumed
        self.quote_service.mark_quote_consumed(quote.quote_id)

        # 9. Record Audit Log
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        audit_id = self.audit_service.record_audit(
            merchant_id=merchant_id,
            user_id_hash=user_id_hash,
            action="ORDER_CREATED",
            idempotency_key=req.idempotency_key,
            quote_id=quote.quote_id,
            order_id=order_id,
            amount=quote.final_total_price,
            currency=quote.currency,
            masked_pii_payload=masked_address,
            status="SUCCESS",
            explainability_notes=(
                f"Successfully authorized and placed order {order_id} on Razorpay rails. "
                f"Total: ₹{quote.final_total_price:.2f}."
            ),
        )

        # 10. Persist Order in Database
        with self.session_factory() as session:
            order_model = OrderModel(
                order_id=order_id,
                idempotency_key=req.idempotency_key,
                merchant_id=merchant_id,
                user_id=req.user_id,
                quote_id=quote.quote_id,
                items_json=quote.items_json,
                final_amount=quote.final_total_price,
                currency=quote.currency,
                shipping_address_json=json.dumps(shipping_addr_dict or {}),
                payment_rail_id=rail_result["payment_rail_id"],
                payment_status=rail_result["payment_status"],
                payment_link=rail_result["payment_link"],
                audit_id=audit_id,
                created_at=now_str,
                metadata_json=json.dumps(
                    {
                        "fulfillment_type": req.fulfillment_type,
                        "fulfillment_notes": req.fulfillment_notes,
                        "address_label": req.address_label,
                    }
                ),
            )
            session.add(order_model)
            session.commit()

        # 11. Cache in Gatekeeper for 24h Idempotency Replays
        cached_payload = {
            "order_id": order_id,
            "final_amount": quote.final_total_price,
            "currency": quote.currency,
            "payment_rail_id": rail_result["payment_rail_id"],
            "payment_status": rail_result["payment_status"],
            "payment_link": rail_result["payment_link"],
            "audit_id": audit_id,
            "created_at": now_str,
        }
        self.gatekeeper.check_and_acquire_idempotency(
            idempotency_key=req.idempotency_key,
            payload=json.dumps(cached_payload),
            ttl_seconds=86400,
        )

        return CheckoutResponseSchema(
            order_id=order_id,
            idempotency_key=req.idempotency_key,
            merchant_id=merchant_id,
            quote_id=quote.quote_id,
            final_amount=quote.final_total_price,
            currency=quote.currency,
            payment_rail_id=rail_result["payment_rail_id"],
            payment_status=rail_result["payment_status"],
            payment_link=rail_result["payment_link"],
            audit_id=audit_id,
            is_replayed=False,
            explainability_notes="Order settled on Razorpay rails with zero-trust budget verification.",
            created_at=now_str,
        )
