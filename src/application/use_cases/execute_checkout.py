"""Use case for executing bounded checkout, spend verification, idempotency locks, and payment rails.

Clean Architecture layer: Application.
"""
import uuid
import json
from typing import Optional

from ...domain.checkout import Address, Order, IPaymentRail
from ...domain.audit import AuditEntry, IAuditRepository
from ...domain.common import current_utc_timestamp
from ...domain.catalog import ICatalogRepository
from ...domain.gatekeeper import IGatekeeper
from ...domain.auth.ports import IUserRepository
from ...domain.exceptions import (
    SpendCapExceededError,
    OutOfStockError,
    QuoteExpiredError,
    PolicyViolationError,
    MerchantConfigError,
)
from ..dto import CheckoutInputDTO, CheckoutResponseDTO


class ExecuteCheckoutUseCase:
    """Use case to validate spend caps, execute atomic settlement, and log masked audit trail."""

    def __init__(
        self,
        catalog_repo: ICatalogRepository,
        audit_repo: IAuditRepository,
        gatekeeper: IGatekeeper,
        payment_rail: IPaymentRail,
        default_merchant_id: str,
        user_repo: Optional[IUserRepository] = None,
    ):
        self.catalog_repo = catalog_repo
        self.audit_repo = audit_repo
        self.gatekeeper = gatekeeper
        self.payment_rail = payment_rail
        self.default_merchant_id = default_merchant_id
        self.user_repo = user_repo

    def execute(self, checkout_in: CheckoutInputDTO) -> CheckoutResponseDTO:
        merchant_id = checkout_in.merchant_id or self.default_merchant_id
        merchant = self.catalog_repo.get_merchant(merchant_id)
        if not merchant:
            raise MerchantConfigError(merchant_id, "Merchant profile does not exist.")

        user_id_hash = AuditEntry.hash_user_id(checkout_in.user_id)
        shipping_entity = None

        # 0. Resolve Shipping Address (Direct Address DTO or Semantic Label Lookup)
        if checkout_in.shipping_address:
            shipping_entity = Address(
                line1=checkout_in.shipping_address.line1,
                line2=checkout_in.shipping_address.line2,
                city=checkout_in.shipping_address.city,
                state=checkout_in.shipping_address.state,
                postal_code=checkout_in.shipping_address.postal_code,
                country=checkout_in.shipping_address.country,
                phone=checkout_in.shipping_address.phone,
                email=checkout_in.shipping_address.email,
            )
        elif checkout_in.address_label and self.user_repo:
            saved = self.user_repo.get_user_address_by_label(checkout_in.user_id, checkout_in.address_label)
            if saved:
                line2_combined = saved.line2
                if checkout_in.fulfillment_notes:
                    line2_combined = f"{saved.line2} ({checkout_in.fulfillment_notes})" if saved.line2 else checkout_in.fulfillment_notes

                shipping_entity = Address(
                    line1=saved.line1,
                    line2=line2_combined,
                    city=saved.city,
                    state=saved.state,
                    postal_code=saved.postal_code,
                    country=saved.country,
                    phone=saved.phone,
                    email=saved.email,
                )


        # 1. Check Idempotency Key (24h defense in Redis Gatekeeper)
        is_new_tx, cached_json = self.gatekeeper.check_and_acquire_idempotency(
            idempotency_key=checkout_in.idempotency_key,
            payload="",
            ttl_seconds=86400,
        )

        if not is_new_tx and cached_json:
            try:
                cached_data = json.loads(cached_json)
                self.audit_repo.record_audit(
                    AuditEntry(
                        audit_id=f"aud_{uuid.uuid4().hex[:12]}",
                        timestamp=current_utc_timestamp(),
                        merchant_id=merchant_id,
                        user_id_hash=user_id_hash,
                        action="IDEMPOTENCY_REPLAY",
                        idempotency_key=checkout_in.idempotency_key,
                        quote_id=checkout_in.quote_id,
                        order_id=cached_data.get("order_id"),
                        amount=cached_data.get("final_amount", 0.0),
                        currency=cached_data.get("currency", "INR"),
                        masked_pii_payload=shipping_entity.to_masked_dict() if shipping_entity else {},
                        status="REPLAYED",
                        explainability_notes=(
                            f"Idempotent transaction replayed successfully. "
                            f"Existing Order ID: {cached_data.get('order_id')}."
                        ),
                    )
                )
                return CheckoutResponseDTO(
                    order_id=cached_data["order_id"],
                    idempotency_key=checkout_in.idempotency_key,
                    merchant_id=merchant_id,
                    quote_id=checkout_in.quote_id,
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

        # 1.1 Secondary Idempotency check against persistent repository
        existing_order = self.catalog_repo.get_order_by_idempotency(checkout_in.idempotency_key)
        if existing_order:
            self.audit_repo.record_audit(
                AuditEntry(
                    audit_id=f"aud_{uuid.uuid4().hex[:12]}",
                    timestamp=current_utc_timestamp(),
                    merchant_id=merchant_id,
                    user_id_hash=user_id_hash,
                    action="IDEMPOTENCY_REPLAY",
                    idempotency_key=checkout_in.idempotency_key,
                    quote_id=checkout_in.quote_id,
                    order_id=existing_order.order_id,
                    amount=existing_order.final_amount,
                    currency=existing_order.currency,
                    masked_pii_payload=shipping_entity.to_masked_dict() if shipping_entity else {},
                    status="REPLAYED",
                    explainability_notes=(
                        f"Idempotent transaction replayed successfully from repository. "
                        f"Existing Order ID: {existing_order.order_id}."
                    ),
                )
            )
            return CheckoutResponseDTO(
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
        quote = self.catalog_repo.get_quote(checkout_in.quote_id)
        if not quote:
            raise PolicyViolationError(
                "QUOTE_NOT_FOUND", f"Price quote '{checkout_in.quote_id}' does not exist."
            )

        if quote.is_expired():
            raise QuoteExpiredError(quote.quote_id, quote.expires_at)

        if quote.status != "ACTIVE":
            raise PolicyViolationError(
                "QUOTE_ALREADY_CONSUMED",
                f"Price quote '{quote.quote_id}' has already been consumed or closed.",
            )

        # 3. Deterministic Spend Budget Validation (User Budget Constraint)
        if quote.final_total_price > checkout_in.max_spend_budget:
            audit_id = f"aud_{uuid.uuid4().hex[:12]}"
            self.audit_repo.record_audit(
                AuditEntry(
                    audit_id=audit_id,
                    timestamp=current_utc_timestamp(),
                    merchant_id=merchant_id,
                    user_id_hash=user_id_hash,
                    action="SPEND_CAP_REJECTED",
                    idempotency_key=checkout_in.idempotency_key,
                    quote_id=quote.quote_id,
                    order_id=None,
                    amount=quote.final_total_price,
                    currency=quote.currency,
                    masked_pii_payload=shipping_entity.to_masked_dict() if shipping_entity else {},
                    status="REJECTED",
                    explainability_notes=(
                        f"Order total ₹{quote.final_total_price:.2f} exceeded user agent's "
                        f"authorized budget of ₹{checkout_in.max_spend_budget:.2f}."
                    ),
                )
            )
            raise SpendCapExceededError(
                attempted_amount=quote.final_total_price,
                limit_amount=checkout_in.max_spend_budget,
                limit_type="USER_AGENT_MAX_BUDGET",
            )

        # 4. Check Per-Transaction Cap on Merchant
        if quote.final_total_price > merchant.per_tx_spend_cap:
            raise SpendCapExceededError(
                attempted_amount=quote.final_total_price,
                limit_amount=merchant.per_tx_spend_cap,
                limit_type="MERCHANT_PER_TX_CAP",
            )

        # 5. Atomic Redis Gatekeeper Spend Cap Check (Sub-ms Lua execution)
        approved, reason, curr_user, curr_merch = self.gatekeeper.check_and_record_spend(
            merchant_id=merchant_id,
            user_id=checkout_in.user_id,
            amount=quote.final_total_price,
            user_budget=checkout_in.max_spend_budget,
            merchant_cap=merchant.daily_merchant_spend_cap,
        )

        if not approved:
            audit_id = f"aud_{uuid.uuid4().hex[:12]}"
            self.audit_repo.record_audit(
                AuditEntry(
                    audit_id=audit_id,
                    timestamp=current_utc_timestamp(),
                    merchant_id=merchant_id,
                    user_id_hash=user_id_hash,
                    action="GATEKEEPER_SPEND_REJECTED",
                    idempotency_key=checkout_in.idempotency_key,
                    quote_id=quote.quote_id,
                    order_id=None,
                    amount=quote.final_total_price,
                    currency=quote.currency,
                    masked_pii_payload=shipping_entity.to_masked_dict() if shipping_entity else {},
                    status="REJECTED",
                    explainability_notes=f"Gatekeeper spend cap rejected: {reason}",
                )
            )
            raise SpendCapExceededError(
                attempted_amount=quote.final_total_price,
                limit_amount=merchant.daily_merchant_spend_cap,
                limit_type=reason,
                message=f"Spend cap rejected by gatekeeper: {reason}.",
            )

        # 6. Inventory Deduction
        try:
            for item in quote.items:
                self.catalog_repo.update_inventory(
                    merchant_id=merchant_id,
                    product_id=item.product_id,
                    quantity_delta=-item.quantity,
                )
        except OutOfStockError as oos:
            self.gatekeeper.release_spend(
                merchant_id=merchant_id,
                user_id=checkout_in.user_id,
                amount=quote.final_total_price,
            )
            raise oos

        # 7. Invoke Payment Rail (Razorpay test mode order)
        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        notes = {
            "idempotency_key": checkout_in.idempotency_key,
            "user_id_hash": user_id_hash,
            "quote_id": quote.quote_id,
            "merchant_id": merchant_id,
        }

        try:
            rail_result = self.payment_rail.create_order(
                merchant_id=merchant_id,
                order_id=order_id,
                amount_in_inr=quote.final_total_price,
                currency=quote.currency,
                notes=notes,
            )
        except Exception as ex:
            for item in quote.items:
                self.catalog_repo.update_inventory(
                    merchant_id=merchant_id,
                    product_id=item.product_id,
                    quantity_delta=item.quantity,
                )
            self.gatekeeper.release_spend(
                merchant_id=merchant_id,
                user_id=checkout_in.user_id,
                amount=quote.final_total_price,
            )
            raise ex

        # 8. Mark Quote Consumed
        quote.status = "CONSUMED"
        self.catalog_repo.save_quote(quote)

        # 9. Create Order & Audit Entry with Masked PII
        audit_id = f"aud_{uuid.uuid4().hex[:12]}"
        masked_pii = shipping_entity.to_masked_dict() if shipping_entity else {}
        explain_notes = (
            f"Successfully authorized and placed order {order_id} on Razorpay test rails. "
            f"Billed ₹{quote.final_total_price:.2f} {quote.currency} for {len(quote.items)} items."
        )

        audit_entry = AuditEntry(
            audit_id=audit_id,
            timestamp=current_utc_timestamp(),
            merchant_id=merchant_id,
            user_id_hash=user_id_hash,
            action="ORDER_CREATED",
            idempotency_key=checkout_in.idempotency_key,
            quote_id=quote.quote_id,
            order_id=order_id,
            amount=quote.final_total_price,
            currency=quote.currency,
            masked_pii_payload=masked_pii,
            status="SUCCESS",
            explainability_notes=explain_notes,
        )
        self.audit_repo.record_audit(audit_entry)

        order = Order(
            order_id=order_id,
            idempotency_key=checkout_in.idempotency_key,
            merchant_id=merchant_id,
            user_id=checkout_in.user_id,
            quote_id=quote.quote_id,
            items=quote.items,
            final_amount=quote.final_total_price,
            currency=quote.currency,
            shipping_address=shipping_entity,
            payment_rail_id=rail_result.rail_order_id,
            payment_status=rail_result.status,
            payment_link=rail_result.payment_link,
            audit_id=audit_id,
            created_at=current_utc_timestamp(),
        )
        self.catalog_repo.save_order(order)

        # Cache result in Gatekeeper for 24h idempotency replay
        cached_payload = json.dumps(
            {
                "order_id": order.order_id,
                "final_amount": order.final_amount,
                "currency": order.currency,
                "payment_rail_id": order.payment_rail_id,
                "payment_status": order.payment_status,
                "payment_link": order.payment_link,
                "audit_id": order.audit_id,
                "created_at": order.created_at,
            }
        )
        self.gatekeeper.check_and_acquire_idempotency(
            idempotency_key=checkout_in.idempotency_key,
            payload=cached_payload,
            ttl_seconds=86400,
        )

        return CheckoutResponseDTO(
            order_id=order.order_id,
            idempotency_key=order.idempotency_key,
            merchant_id=order.merchant_id,
            quote_id=order.quote_id,
            final_amount=order.final_amount,
            currency=order.currency,
            payment_rail_id=order.payment_rail_id,
            payment_status=order.payment_status,
            payment_link=order.payment_link,
            audit_id=order.audit_id,
            is_replayed=False,
            explainability_notes=explain_notes,
            created_at=order.created_at,
        )
