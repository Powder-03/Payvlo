"""Health Check Endpoint."""
from fastapi import APIRouter, Request
from ..core.config import settings

router = APIRouter(tags=["Health & Status"])


@router.get("/healthz")
def health_check(request: Request):
    """System health check returning protocol readiness and active node identity."""
    app_state = getattr(request.app, "state", None)
    merchant_name = getattr(app_state, "active_merchant_name", "Payvlo Commerce Gateway")
    merchant_id = getattr(app_state, "active_merchant_id", settings.ACTIVE_MERCHANT_ID)

    return {
        "status": "healthy",
        "active_merchant_id": merchant_id,
        "node_name": merchant_name,
        "protocols": ["MCP/SSE", "UAP/A2A", "Merchant-SaaS-Auth"],
        "gatekeeper": "Upstash-Redis / Atomic Lua",
        "payment_rail": "Razorpay Test Rails",
    }
