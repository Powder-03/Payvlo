"""FastAPI Application Server mounting FastMCP SSE and UAP / A2A Routers.

Clean Architecture layer: Infrastructure.
Assembles and connects Domain Entities, Use Cases, Repositories, Gatekeepers, and Ingress Adapters.
Binds to Render $PORT for production deployment.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from .config import settings
from .database import init_database, seed_merchants_and_catalog
from ..adapters.redis_gatekeeper import RedisGatekeeperAdapter
from ..adapters.razorpay_rails import RazorpayPaymentRailAdapter
from ..adapters.mcp_controller import MCPController, create_mcp_router
from ..adapters.uap_controller import create_uap_router
from ..adapters.merchant_controller import create_merchant_router
from ..adapters.auth_controller import create_auth_router
from ..adapters.postgres_repo import PostgresUserRepository
from ..adapters.catalog_sync_providers import CatalogSyncDispatcher
from ..application.use_cases import (
    SearchCatalogUseCase,
    RequestQuoteUseCase,
    ExecuteCheckoutUseCase,
    InspectAuditUseCase,
    NegotiateIntentUseCase,
    OnboardMerchantUseCase,
    SyncMerchantCatalogUseCase,
    ListMerchantsUseCase,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("CommerceNodeServer")


def create_application() -> FastAPI:
    """Dependency Injection & Application Assembler."""
    # 1. Initialize Database & Repositories
    db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    engine, session_factory, catalog_repo, audit_repo = init_database(db_url)
    user_repo = PostgresUserRepository(session_factory)

    # Run Seeder
    seed_merchants_and_catalog(catalog_repo)

    # 2. Initialize Redis Gatekeeper (Upstash or In-Memory)
    redis_url = (
        os.getenv("UPSTASH_REDIS_REST_URL")
        or os.getenv("REDIS_URL")
        or settings.REDIS_URL
    )
    gatekeeper = RedisGatekeeperAdapter(redis_url=redis_url)

    # 3. Initialize Razorpay Payment Rail
    rzp_key_id = os.getenv("RAZORPAY_KEY_ID", settings.RAZORPAY_KEY_ID)
    rzp_key_secret = os.getenv("RAZORPAY_KEY_SECRET", settings.RAZORPAY_KEY_SECRET)
    payment_rail = RazorpayPaymentRailAdapter(
        key_id=rzp_key_id,
        key_secret=rzp_key_secret,
        is_sandbox=settings.RAZORPAY_SANDBOX_MODE,
    )

    # 4. Initialize Catalog Sync Dispatcher (Shopify, Custom REST API, Direct)
    sync_dispatcher = CatalogSyncDispatcher()

    # Active Merchant
    active_merchant_id = os.getenv(
        "ACTIVE_MERCHANT_ID", settings.ACTIVE_MERCHANT_ID
    )
    active_merchant = catalog_repo.get_merchant(active_merchant_id)
    merchant_name = active_merchant.merchant_name if active_merchant else "Agentic Merchant"

    # 5. Instantiate Use Cases
    search_catalog_uc = SearchCatalogUseCase(
        catalog_repo=catalog_repo,
        default_merchant_id=active_merchant_id,
    )
    request_quote_uc = RequestQuoteUseCase(
        catalog_repo=catalog_repo,
        audit_repo=audit_repo,
        default_merchant_id=active_merchant_id,
        quote_validity_minutes=settings.QUOTE_VALIDITY_MINUTES,
    )
    execute_checkout_uc = ExecuteCheckoutUseCase(
        catalog_repo=catalog_repo,
        audit_repo=audit_repo,
        gatekeeper=gatekeeper,
        payment_rail=payment_rail,
        default_merchant_id=active_merchant_id,
    )
    inspect_audit_uc = InspectAuditUseCase(
        audit_repo=audit_repo,
    )
    negotiate_intent_uc = NegotiateIntentUseCase(
        catalog_repo=catalog_repo,
        request_quote_uc=request_quote_uc,
        default_merchant_id=active_merchant_id,
    )
    onboard_merchant_uc = OnboardMerchantUseCase(
        catalog_repo=catalog_repo,
        audit_repo=audit_repo,
        sync_provider=sync_dispatcher,
        base_url=settings.PUBLIC_BASE_URL,
    )
    sync_catalog_uc = SyncMerchantCatalogUseCase(
        catalog_repo=catalog_repo,
        audit_repo=audit_repo,
        sync_provider=sync_dispatcher,
    )
    list_merchants_uc = ListMerchantsUseCase(
        catalog_repo=catalog_repo,
    )

    # 6. Instantiate MCP, UAP, Merchant, and Auth Controllers
    mcp_controller = MCPController(
        search_catalog_uc=search_catalog_uc,
        request_quote_uc=request_quote_uc,
        execute_checkout_uc=execute_checkout_uc,
        inspect_audit_uc=inspect_audit_uc,
        onboard_merchant_uc=onboard_merchant_uc,
        sync_catalog_uc=sync_catalog_uc,
        merchant_name=merchant_name,
    )

    mcp_router = create_mcp_router(mcp_controller)
    uap_router = create_uap_router(
        catalog_repo=catalog_repo,
        negotiate_uc=negotiate_intent_uc,
        checkout_uc=execute_checkout_uc,
        active_merchant_id=active_merchant_id,
        base_url=settings.PUBLIC_BASE_URL,
    )
    auth_router = create_auth_router(
        user_repo=user_repo,
        catalog_repo=catalog_repo,
    )
    merchant_router = create_merchant_router(
        onboard_uc=onboard_merchant_uc,
        sync_uc=sync_catalog_uc,
        list_uc=list_merchants_uc,
        catalog_repo=catalog_repo,
        user_repo=user_repo,
        base_url=settings.PUBLIC_BASE_URL,
    )

    # 7. Lifespan context
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            f"🚀 Universal Agentic Commerce Node & SaaS Portal online for [{merchant_name}] ({active_merchant_id})."
        )
        logger.info("Protocols enabled: Model Context Protocol (MCP/SSE) + Universal Agent Protocol (UAP/A2A) + Merchant SaaS Auth.")
        yield
        logger.info("Commerce Node shutting down.")

    # 8. Create FastAPI App
    app = FastAPI(
        title="Universal Agentic Commerce Node & Merchant Portal",
        description="Dual-Interface Gateway for Tool-Calling & Autonomous Peer Agents with Zero-Trust Spend Bounds, Merchant SaaS Auth & Razorpay Rails.",
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

    # Mount Protocol, Auth & Admin Routers
    app.include_router(mcp_router)
    app.include_router(uap_router)
    app.include_router(auth_router)
    app.include_router(merchant_router)

    # Public Discovery & Health Routes
    @app.get("/healthz")
    def health_check():
        return {
            "status": "healthy",
            "active_merchant_id": active_merchant_id,
            "node_name": merchant_name,
            "protocols": ["MCP/SSE", "UAP/A2A", "Merchant-SaaS-Auth"],
            "gatekeeper": "Upstash-Redis / Atomic Lua",
            "payment_rail": "Razorpay Test Rails",
        }

    # Serve Dashboard HTML
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")

    @app.get("/", response_class=HTMLResponse)
    @app.get("/portal", response_class=HTMLResponse)
    def merchant_portal():
        if os.path.exists(dashboard_path):
            with open(dashboard_path, "r", encoding="utf-8") as f:
                return f.read()
        return "<h1>Payvlo Merchant Portal</h1><p>Dashboard template not found.</p>"

    # Expose helper references for test harness
    app.state.catalog_repo = catalog_repo
    app.state.audit_repo = audit_repo
    app.state.user_repo = user_repo
    app.state.gatekeeper = gatekeeper
    app.state.payment_rail = payment_rail
    app.state.mcp_controller = mcp_controller
    app.state.search_catalog_uc = search_catalog_uc
    app.state.request_quote_uc = request_quote_uc
    app.state.execute_checkout_uc = execute_checkout_uc
    app.state.inspect_audit_uc = inspect_audit_uc
    app.state.negotiate_intent_uc = negotiate_intent_uc
    app.state.onboard_merchant_uc = onboard_merchant_uc
    app.state.sync_catalog_uc = sync_catalog_uc
    app.state.list_merchants_uc = list_merchants_uc
    app.state.sync_dispatcher = sync_dispatcher

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", settings.PORT))
    uvicorn.run("src.infrastructure.server:app", host="0.0.0.0", port=port, reload=False)
