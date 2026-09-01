"""UAP / A2A Protocol Negotiation & Settlement API Router."""
from typing import List
from fastapi import APIRouter, HTTPException, Request, status

from ...schemas.uap import (
    UAPNegotiateRequestSchema,
    UAPNegotiateResponseSchema,
    UAPTransactRequestSchema,
    UAPTransactResponseSchema,
)
from ...schemas.quote import QuoteRequestInputSchema, QuoteRequestItemSchema
from ...schemas.checkout import CheckoutInputSchema
from ...core.exceptions import DomainError

router = APIRouter(prefix="/uap/v1", tags=["UAP / A2A Protocol"])


@router.post("/negotiate", response_model=UAPNegotiateResponseSchema)
def negotiate_intent(request: Request, body: UAPNegotiateRequestSchema):
    """Multi-turn intent negotiation and pricing agreement for autonomous peer agents."""
    catalog_service = request.app.state.catalog_service
    quote_service = request.app.state.quote_service

    mid = body.merchant_id or getattr(request.app.state, "active_merchant_id", "dominos_in")
    merchant = catalog_service.get_merchant(mid)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant '{mid}' not found.",
        )

    try:
        # Build items list
        items: List[QuoteRequestItemSchema] = []
        if body.items:
            items = body.items
        elif body.target_skus_or_ids:
            for target in body.target_skus_or_ids:
                p = catalog_service.get_product(mid, target)
                if p:
                    items.append(
                        QuoteRequestItemSchema(
                            product_id=p.product_id,
                            quantity=1,
                            requested_discount_pct=10.0,
                        )
                    )

        if not items:
            # Fallback search if no SKUs supplied
            from ...schemas.catalog import CatalogSearchInputSchema
            search_res = catalog_service.search_products(
                CatalogSearchInputSchema(merchant_id=mid, query=body.intent_summary, limit=2)
            )
            for p in search_res.products:
                items.append(
                    QuoteRequestItemSchema(
                        product_id=p.product_id,
                        quantity=1,
                        requested_discount_pct=5.0,
                    )
                )

        if not items:
            return UAPNegotiateResponseSchema(
                status="NO_MATCH",
                quote=None,
                counter_offer_notes="No matching products found in store catalog.",
                within_budget=False,
                requires_approval=False,
            )

        quote = quote_service.calculate_quote(
            QuoteRequestInputSchema(
                items=items,
                overall_requested_discount_pct=0.0,
                merchant_id=mid,
            )
        )

        within_budget = quote.final_total_price <= body.buyer_max_budget
        status_str = "OFFERED" if within_budget else "COUNTER_OFFER"
        notes = (
            f"Clamped quote generated for {len(quote.items)} items. Total: ₹{quote.final_total_price:.2f}."
            if within_budget
            else f"Quote total ₹{quote.final_total_price:.2f} exceeds buyer's max budget of ₹{body.buyer_max_budget:.2f}."
        )

        return UAPNegotiateResponseSchema(
            status=status_str,
            quote=quote,
            counter_offer_notes=notes,
            within_budget=within_budget,
            requires_approval=not within_budget,
            settlement_endpoint="/uap/v1/transact",
        )
    except DomainError as de:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=de.to_dict())
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Negotiation failed: {str(ex)}",
        )


@router.post("/transact", response_model=UAPTransactResponseSchema)
def transact_settlement(request: Request, body: UAPTransactRequestSchema):
    """Final signed order settlement against Razorpay payment rails."""
    checkout_service = request.app.state.checkout_service

    try:
        checkout_in = CheckoutInputSchema(
            quote_id=body.quote_id,
            idempotency_key=body.idempotency_key,
            user_id=body.buyer_agent_id,
            max_spend_budget=body.authorized_spend_limit,
            shipping_address=body.shipping_address,
            merchant_id=body.merchant_id,
        )
        order_res = checkout_service.execute_checkout(checkout_in)

        tx_status = "REPLAYED" if order_res.is_replayed else "SETTLED"
        msg = (
            f"Order {order_res.order_id} successfully authorized on Razorpay rails."
            if not order_res.is_replayed
            else "Idempotent transaction replayed without double-charge."
        )

        return UAPTransactResponseSchema(
            status=tx_status,
            order_id=order_res.order_id,
            razorpay_order_id=order_res.payment_rail_id,
            payment_link=order_res.payment_link,
            amount_settled=order_res.final_amount,
            currency=order_res.currency,
            audit_id=order_res.audit_id,
            message=msg,
        )
    except DomainError as de:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=de.to_dict())
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Settlement failed: {str(ex)}",
        )
