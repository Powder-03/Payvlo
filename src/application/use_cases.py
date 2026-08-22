"""Application Layer Use Cases for Agentic Commerce Node.

Clean Architecture layer: Application.
Coordinates domain entities, value objects, ports, and business policies.
Independent of web frameworks, database ORMs, and payment gateways.
"""
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from ..domain.entities import (
    MerchantProfile,
    Product,
    Address,
    QuoteItem,
    Quote,
    Order,
    AuditEntry,
    current_utc_timestamp,
)
from ..domain.exceptions import (
    DomainError,
    SpendCapExceededError,
    OutOfStockError,
    ProductNotFoundError,
    QuoteExpiredError,
    PolicyViolationError,
    IdempotencyReplayError,
    MerchantConfigError,
)
from ..domain.ports import (
    ICatalogRepository,
    IAuditRepository,
    IGatekeeper,
    IPaymentRail,
)
from .dto import (
    ProductDTO,
    CatalogSearchInputDTO,
    CatalogSearchResultDTO,
    QuoteRequestInputDTO,
    QuoteResponseDTO,
    QuoteItemDTO,
    CheckoutInputDTO,
    CheckoutResponseDTO,
    AuditInspectInputDTO,
    AuditInspectResponseDTO,
    AuditEntryDTO,
    UAPNegotiateRequestDTO,
    UAPNegotiateResponseDTO,
    QuoteRequestItemDTO,
)


class SearchCatalogUseCase:
    """Use case to discover products and evaluate inventory across merchant catalog."""

    def __init__(self, catalog_repo: ICatalogRepository, default_merchant_id: str):
        self.catalog_repo = catalog_repo
        self.default_merchant_id = default_merchant_id

    def execute(self, params: CatalogSearchInputDTO) -> CatalogSearchResultDTO:
        merchant_id = params.merchant_id or self.default_merchant_id
        merchant = self.catalog_repo.get_merchant(merchant_id)
        if not merchant:
            raise MerchantConfigError(merchant_id, "Merchant profile does not exist.")

        products = self.catalog_repo.search_products(
            merchant_id=merchant_id,
            query=params.query,
            category=params.category,
            min_price=params.min_price,
            max_price=params.max_price,
            limit=params.limit,
            offset=params.offset,
        )

        dtos = [
            ProductDTO(
                product_id=p.product_id,
                merchant_id=p.merchant_id,
                sku=p.sku,
                title=p.title,
                description=p.description,
                price_inr=p.price_inr,
                inventory_count=p.inventory_count,
                category=p.category,
                max_discount_percentage=p.max_discount_percentage,
                tags=p.tags,
                metadata=p.metadata,
            )
            for p in products
        ]

        return CatalogSearchResultDTO(
            merchant_id=merchant_id,
            total_count=len(dtos),
            products=dtos,
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


class ExecuteCheckoutUseCase:
    """Use case to validate spend caps, execute atomic settlement, and log masked audit trail."""

    def __init__(
        self,
        catalog_repo: ICatalogRepository,
        audit_repo: IAuditRepository,
        gatekeeper: IGatekeeper,
        payment_rail: IPaymentRail,
        default_merchant_id: str,
    ):
        self.catalog_repo = catalog_repo
        self.audit_repo = audit_repo
        self.gatekeeper = gatekeeper
        self.payment_rail = payment_rail
        self.default_merchant_id = default_merchant_id

    def execute(self, checkout_in: CheckoutInputDTO) -> CheckoutResponseDTO:
        merchant_id = checkout_in.merchant_id or self.default_merchant_id
        merchant = self.catalog_repo.get_merchant(merchant_id)
        if not merchant:
            raise MerchantConfigError(merchant_id, "Merchant profile does not exist.")

        user_id_hash = AuditEntry.hash_user_id(checkout_in.user_id)
        shipping_entity = None
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

        # 1. Check Idempotency Key (24h defense)
        is_new_tx, cached_json = self.gatekeeper.check_and_acquire_idempotency(
            idempotency_key=checkout_in.idempotency_key,
            payload="",  # will update after completion
            ttl_seconds=86400,
        )

        if not is_new_tx and cached_json:
            # Replay defense hit! Return existing order without re-charging
            try:
                cached_data = json.loads(cached_json)
                # Append replay audit record
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
            # Release spend cap in gatekeeper
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
            # Rollback inventory and spend cap
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


class InspectAuditUseCase:
    """Use case to safely inspect the append-only ledger with privacy filtering."""

    def __init__(self, audit_repo: IAuditRepository):
        self.audit_repo = audit_repo

    def execute(self, params: AuditInspectInputDTO) -> AuditInspectResponseDTO:
        user_id_hash = None
        if params.user_id:
            user_id_hash = AuditEntry.hash_user_id(params.user_id)

        entries = self.audit_repo.get_audit_trail(
            merchant_id=params.merchant_id,
            user_id_hash=user_id_hash,
            limit=params.limit,
        )

        dtos = [
            AuditEntryDTO(
                audit_id=e.audit_id,
                timestamp=e.timestamp,
                merchant_id=e.merchant_id,
                user_id_hash=e.user_id_hash,
                action=e.action,
                idempotency_key=e.idempotency_key,
                quote_id=e.quote_id,
                order_id=e.order_id,
                amount=e.amount,
                currency=e.currency,
                masked_pii_payload=e.masked_pii_payload,
                status=e.status,
                explainability_notes=e.explainability_notes,
            )
            for e in entries
        ]

        return AuditInspectResponseDTO(
            total_entries=len(dtos),
            entries=dtos,
        )


class NegotiateIntentUseCase:
    """Use case for autonomous peer-to-peer buyer agent negotiation (UAP / A2A Protocol)."""

    def __init__(
        self,
        catalog_repo: ICatalogRepository,
        request_quote_uc: RequestQuoteUseCase,
        default_merchant_id: str,
    ):
        self.catalog_repo = catalog_repo
        self.request_quote_uc = request_quote_uc
        self.default_merchant_id = default_merchant_id

    def execute(self, req: UAPNegotiateRequestDTO) -> UAPNegotiateResponseDTO:
        merchant_id = req.merchant_id or self.default_merchant_id
        merchant = self.catalog_repo.get_merchant(merchant_id)
        if not merchant:
            raise MerchantConfigError(merchant_id, "Merchant profile not found.")

        quote_items_req: List[QuoteRequestItemDTO] = []

        if req.items and len(req.items) > 0:
            quote_items_req = req.items
        elif req.target_skus_or_ids:
            for sku in req.target_skus_or_ids:
                quote_items_req.append(QuoteRequestItemDTO(product_id=sku, quantity=1))
        else:
            # Match keywords from intent_summary against catalog
            search_results = self.catalog_repo.search_products(
                merchant_id=merchant_id,
                query=req.intent_summary,
                limit=3,
            )
            if not search_results:
                return UAPNegotiateResponseDTO(
                    status="REJECTED",
                    quote=None,
                    counter_offer_notes=f"No matching products found for intent '{req.intent_summary}'.",
                    within_budget=False,
                    requires_approval=False,
                    settlement_endpoint="/uap/v1/transact",
                )
            for prod in search_results:
                quote_items_req.append(
                    QuoteRequestItemDTO(product_id=prod.product_id, quantity=1)
                )

        # Generate quote with merchant maximum allowed discount ceiling to negotiate best rate
        quote_dto = self.request_quote_uc.execute(
            QuoteRequestInputDTO(
                items=quote_items_req,
                overall_requested_discount_pct=merchant.max_discount_percentage,
                merchant_id=merchant_id,
            )
        )

        within_budget = quote_dto.final_total_price <= req.buyer_max_budget
        counter_notes = (
            f"Offered {len(quote_dto.items)} items for ₹{quote_dto.final_total_price:.2f} "
            f"(includes max allowable discount ₹{quote_dto.total_discount_amount:.2f})."
        )
        status = "OFFERED" if within_budget else "COUNTER_OFFER"

        return UAPNegotiateResponseDTO(
            status=status,
            quote=quote_dto,
            counter_offer_notes=counter_notes,
            within_budget=within_budget,
            requires_approval=not within_budget,
            settlement_endpoint="/uap/v1/transact",
        )
