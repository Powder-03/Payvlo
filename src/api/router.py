"""Unified Master API Router."""
from fastapi import APIRouter

from .health import router as health_router
from .v1.auth import router as auth_router
from .v1.merchants import router as merchants_router
from .v1.webhooks import router as webhooks_router
from .mcp.sse import router as mcp_sse_router
from .mcp.tools import router as mcp_tools_router
from .uap.discovery import router as uap_discovery_router
from .uap.protocol import router as uap_protocol_router

api_router = APIRouter()

# Mount all protocol & REST routers
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(merchants_router)
api_router.include_router(webhooks_router)
api_router.include_router(mcp_sse_router)
api_router.include_router(mcp_tools_router)
api_router.include_router(uap_discovery_router)
api_router.include_router(uap_protocol_router)
