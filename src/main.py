"""Payvlo Universal Agentic Commerce Node - Main Application Entrypoint."""
import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .core.config import settings
from .core.database import init_database
from .core.scheduler import CatalogSyncScheduler
from .services import (
    AuthService,
    GatekeeperService,
    PaymentService,
    AuditService,
    CatalogService,
    QuoteService,
    CheckoutService,
)
from .api import api_router
from .api.mcp.tools import execute_tool_call
from .schemas.mcp import get_mcp_tool_definitions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("PayvloServer")


class MCPControllerBridge:
    """Direct invocation helper for test harness and internal tool calls."""

    def __init__(self, app: FastAPI, merchant_name: str):
        self.app = app
        self.merchant_name = merchant_name

    def search_store_catalog(self, **kwargs) -> Dict[str, Any]:
        return execute_tool_call(self.app, "search_store_catalog", kwargs)

    def request_price_quote(self, **kwargs) -> Dict[str, Any]:
        return execute_tool_call(self.app, "request_price_quote", kwargs)

    def execute_bounded_checkout(self, **kwargs) -> Dict[str, Any]:
        return execute_tool_call(self.app, "execute_bounded_checkout", kwargs)

    def inspect_audit_trail(self, **kwargs) -> Dict[str, Any]:
        return execute_tool_call(self.app, "inspect_audit_trail", kwargs)

    def onboard_merchant(self, **kwargs) -> Dict[str, Any]:
        return execute_tool_call(self.app, "onboard_merchant", kwargs)

    def sync_merchant_catalog(self, **kwargs) -> Dict[str, Any]:
        return execute_tool_call(self.app, "sync_merchant_catalog", kwargs)

    def get_tool_definitions(self):
        return get_mcp_tool_definitions()


class SyncCatalogUseCaseBridge:
    def __init__(self, catalog_service: CatalogService):
        self.catalog_service = catalog_service

    def execute(self, merchant_id: str):
        return self.catalog_service.sync_merchant_catalog(merchant_id)


def create_application() -> FastAPI:
    """Creates, configures, and wires the Payvlo FastAPI application."""
    # 1. Initialize Database
    engine, session_factory = init_database(settings.DATABASE_URL)

    # 2. Initialize Core Services
    redis_url = settings.REDIS_URL or settings.UPSTASH_REDIS_REST_URL
    gatekeeper_service = GatekeeperService(redis_url=redis_url)

    payment_service = PaymentService(
        key_id=settings.RAZORPAY_KEY_ID,
        key_secret=settings.RAZORPAY_KEY_SECRET,
        is_sandbox=settings.RAZORPAY_SANDBOX_MODE,
    )

    audit_service = AuditService(session_factory=session_factory)

    active_merchant_id = settings.ACTIVE_MERCHANT_ID
    catalog_service = CatalogService(
        session_factory=session_factory,
        default_merchant_id=active_merchant_id,
    )

    active_merchant = catalog_service.get_merchant(active_merchant_id)
    merchant_name = active_merchant.merchant_name if active_merchant else "Payvlo Commerce Node"

    quote_service = QuoteService(
        session_factory=session_factory,
        catalog_service=catalog_service,
        audit_service=audit_service,
        default_merchant_id=active_merchant_id,
        quote_validity_minutes=settings.QUOTE_VALIDITY_MINUTES,
    )

    auth_service = AuthService(session_factory=session_factory)

    checkout_service = CheckoutService(
        session_factory=session_factory,
        catalog_service=catalog_service,
        quote_service=quote_service,
        gatekeeper_service=gatekeeper_service,
        payment_service=payment_service,
        audit_service=audit_service,
        auth_service=auth_service,
        default_merchant_id=active_merchant_id,
    )

    # 3. Background Async Auto-Sync Scheduler
    scheduler = CatalogSyncScheduler(
        catalog_service=catalog_service,
        check_interval_seconds=300,
    )

    # 4. Lifespan context
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            f"🚀 Payvlo Agentic Commerce Node & Portal online for [{merchant_name}] ({active_merchant_id})."
        )
        logger.info(
            "Protocols enabled: Model Context Protocol (MCP/SSE) + Universal Agent Protocol (UAP/A2A) + Webhooks."
        )
        scheduler.start()
        yield
        scheduler.stop()
        logger.info("Payvlo Commerce Node shutting down.")

    # 5. FastAPI Application Instance
    app = FastAPI(
        title="Payvlo Universal Agentic Commerce Node & Merchant Portal",
        description="Dual-Interface Gateway for Tool-Calling & Autonomous Peer Agents with Zero-Trust Spend Bounds, Real-Time Webhooks & Background Scheduler.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount Unified API Router
    app.include_router(api_router)

    # Serve Embedded Dashboard HTML
    dashboard_candidates = [
        os.path.join(os.path.dirname(__file__), "dashboard.html"),
        os.path.join(os.path.dirname(__file__), "infrastructure", "dashboard.html"),
    ]

    @app.get("/", response_class=HTMLResponse)
    @app.get("/portal", response_class=HTMLResponse)
    def merchant_portal():
        for candidate in dashboard_candidates:
            if os.path.exists(candidate):
                with open(candidate, "r", encoding="utf-8") as f:
                    return f.read()
        return "<h1>Payvlo Merchant Portal</h1><p>Dashboard template not found.</p>"

    # Expose helper references for application state & test harness
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.gatekeeper_service = gatekeeper_service
    app.state.gatekeeper = gatekeeper_service
    app.state.payment_service = payment_service
    app.state.payment_rail = payment_service
    app.state.audit_service = audit_service
    app.state.audit_repo = audit_service
    app.state.catalog_service = catalog_service
    app.state.catalog_repo = catalog_service
    app.state.quote_service = quote_service
    app.state.auth_service = auth_service
    app.state.user_repo = auth_service
    app.state.checkout_service = checkout_service
    app.state.scheduler = scheduler
    app.state.sync_catalog_uc = SyncCatalogUseCaseBridge(catalog_service)
    app.state.active_merchant_id = active_merchant_id
    app.state.active_merchant_name = merchant_name
    app.state.mcp_controller = MCPControllerBridge(app, merchant_name)

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", settings.PORT))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=False)
