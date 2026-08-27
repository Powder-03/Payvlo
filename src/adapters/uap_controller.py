"""Universal Agent Protocol (UAP / A2A) Handshake & Settlement Controller.

Clean Architecture layer: Adapters.
Enables peer-to-peer autonomous buyer agents to discover capabilities (/.well-known/agent.json),
negotiate intent (/uap/v1/negotiate), and execute signed settlements (/uap/v1/transact).
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status

from ..domain.catalog import ICatalogRepository
from ..domain.exceptions import DomainError
from ..application.use_cases import (
    NegotiateIntentUseCase,
    ExecuteCheckoutUseCase,
)
from ..application.dto import (
    UAPAgentCardDTO,
    UAPNegotiateRequestDTO,
    UAPNegotiateResponseDTO,
    UAPTransactRequestDTO,
    UAPTransactResponseDTO,
    CheckoutInputDTO,
)


def create_uap_router(
    catalog_repo: ICatalogRepository,
    negotiate_uc: NegotiateIntentUseCase,
    checkout_uc: ExecuteCheckoutUseCase,
    active_merchant_id: str,
    base_url: str = "https://agentic-commerce-node.onrender.com",
) -> APIRouter:
    """Builds FastAPI router for UAP / A2A protocol routes and discovery."""
    router = APIRouter(tags=["UAP / A2A Protocol"])

    @router.get("/.well-known/agent.json", response_model=UAPAgentCardDTO)
    def get_agent_card(merchant_id: Optional[str] = None):
        """Universal Agent Protocol Capability Card Discovery.

        Autonomous buyer agents query this endpoint to inspect capabilities, pricing bounds,
        and settlement endpoints.
        """
        mid = merchant_id or active_merchant_id
        merchant = catalog_repo.get_merchant(mid)
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Merchant '{mid}' not found on this node.",
            )

        return UAPAgentCardDTO(
            agent_id=f"agent_{merchant.merchant_id}",
            name=f"{merchant.merchant_name} Autonomous Commerce Gateway",
            description=(
                f"Universal Agentic Node for {merchant.merchant_name} ({merchant.category}). "
                "Enables zero-trust catalog queries, deterministic discount negotiation, and bounded Razorpay settlements."
            ),
            version="1.0.0",
            protocol_version="uap/v1",
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            category=merchant.category,
            currency=merchant.currency,
            capabilities=[
                "catalog_discovery",
                "intent_negotiation",
                "deterministic_discount_clamping",
                "atomic_spend_gatekeeping",
                "razorpay_test_rails",
                "masked_pii_audit_ledger",
            ],
            endpoints={
                "agent_card": "/.well-known/agent.json",
                "negotiate": "/uap/v1/negotiate",
                "transact": "/uap/v1/transact",
                "mcp_sse": "/sse",
                "mcp_tools": "/mcp/tools",
            },
            pricing_guardrails={
                "currency": merchant.currency,
                "max_discount_percentage": merchant.max_discount_percentage,
                "per_tx_spend_cap": merchant.per_tx_spend_cap,
                "daily_merchant_spend_cap": merchant.daily_merchant_spend_cap,
            },
            supported_payment_rails=["razorpay_test_mode", "upi_intent", "card_sandbox"],
        )

    @router.post("/uap/v1/negotiate", response_model=UAPNegotiateResponseDTO)
    def negotiate_intent(request: UAPNegotiateRequestDTO):
        """Multi-turn intent negotiation and pricing agreement for autonomous peer agents."""
        try:
            return negotiate_uc.execute(request)
        except DomainError as de:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=de.to_dict())
        except Exception as ex:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Negotiation failed: {str(ex)}",
            )

    @router.post("/uap/v1/transact", response_model=UAPTransactResponseDTO)
    def transact_settlement(request: UAPTransactRequestDTO):
        """Final signed order settlement against Razorpay payment rails."""
        try:
            checkout_in = CheckoutInputDTO(
                quote_id=request.quote_id,
                idempotency_key=request.idempotency_key,
                user_id=request.buyer_agent_id,
                max_spend_budget=request.authorized_spend_limit,
                shipping_address=request.shipping_address,
                merchant_id=request.merchant_id,
            )
            order_res = checkout_uc.execute(checkout_in)

            tx_status = "REPLAYED" if order_res.is_replayed else "SETTLED"
            msg = (
                f"Order {order_res.order_id} successfully authorized on Razorpay rails."
                if not order_res.is_replayed
                else "Idempotent transaction replayed without double-charge."
            )

            return UAPTransactResponseDTO(
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

    return router
