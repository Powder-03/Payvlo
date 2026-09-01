"""UAP / A2A Agent Card Discovery Endpoint."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, status

from ...schemas.uap import UAPAgentCardSchema
from ...core.config import settings

router = APIRouter(tags=["UAP / A2A Protocol"])


@router.get("/.well-known/agent.json", response_model=UAPAgentCardSchema)
def get_agent_card(request: Request, merchant_id: Optional[str] = None):
    """Universal Agent Protocol Capability Card Discovery."""
    catalog_service = request.app.state.catalog_service
    mid = merchant_id or getattr(request.app.state, "active_merchant_id", settings.ACTIVE_MERCHANT_ID)
    merchant = catalog_service.get_merchant(mid)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant '{mid}' not found on this node.",
        )

    return UAPAgentCardSchema(
        agent_id=f"agent_{merchant.merchant_id}",
        name=f"{merchant.merchant_name} Autonomous Commerce Gateway",
        description=(
            f"Universal Agentic Node for {merchant.merchant_name} ({merchant.category}). "
            "Enables zero-trust catalog queries, deterministic discount negotiation, and bounded settlements."
        ),
        version="1.0.0",
        protocol_version="uap/v1",
        merchant_id=merchant.merchant_id,
        merchant_name=merchant.merchant_name,
        category=merchant.category,
        currency=merchant.currency or "INR",
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
            "currency": merchant.currency or "INR",
            "max_discount_percentage": merchant.max_discount_percentage,
            "per_tx_spend_cap": merchant.per_tx_spend_cap,
            "daily_merchant_spend_cap": merchant.daily_merchant_spend_cap,
        },
        supported_payment_rails=["razorpay_test_mode", "upi_intent", "card_sandbox"],
    )
