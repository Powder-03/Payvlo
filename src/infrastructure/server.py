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
from ..application.use_cases import (
    SearchCatalogUseCase,
    RequestQuoteUseCase,
    ExecuteCheckoutUseCase,
    InspectAuditUseCase,
    NegotiateIntentUseCase,
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

    # Active Merchant
    active_merchant_id = os.getenv(
        "ACTIVE_MERCHANT_ID", settings.ACTIVE_MERCHANT_ID
    )
    active_merchant = catalog_repo.get_merchant(active_merchant_id)
    merchant_name = active_merchant.merchant_name if active_merchant else "Agentic Merchant"

    # 4. Instantiate Use Cases
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

    # 5. Instantiate MCP & UAP Controllers
    mcp_controller = MCPController(
        search_catalog_uc=search_catalog_uc,
        request_quote_uc=request_quote_uc,
        execute_checkout_uc=execute_checkout_uc,
        inspect_audit_uc=inspect_audit_uc,
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

    # 6. Lifespan context
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            f"🚀 Universal Agentic Commerce Node online for [{merchant_name}] ({active_merchant_id})."
        )
        logger.info("Protocols enabled: Model Context Protocol (MCP/SSE) + Universal Agent Protocol (UAP/A2A).")
        yield
        logger.info("Commerce Node shutting down.")

    # 7. Create FastAPI App
    app = FastAPI(
        title="Universal Agentic Commerce Node",
        description="Dual-Interface Gateway for Tool-Calling & Autonomous Peer Agents with Zero-Trust Spend Bounds & Razorpay Rails.",
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

    # Mount Protocol Routers
    app.include_router(mcp_router)
    app.include_router(uap_router)

    # Public Discovery & Health Routes
    @app.get("/healthz")
    def health_check():
        return {
            "status": "healthy",
            "active_merchant_id": active_merchant_id,
            "node_name": merchant_name,
            "protocols": ["MCP/SSE", "UAP/A2A"],
            "gatekeeper": "Upstash-Redis / Atomic Lua",
            "payment_rail": "Razorpay Test Rails",
        }

    @app.get("/", response_class=HTMLResponse)
    def landing_page():
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Universal Agentic Commerce Node</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0B0F19; color: #E2E8F0; margin: 0; padding: 40px 20px; }}
                .container {{ max-width: 860px; margin: 0 auto; background: #1E293B; border-radius: 16px; padding: 36px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); border: 1px solid #334155; }}
                h1 {{ color: #38BDF8; font-size: 28px; margin-top: 0; display: flex; align-items: center; gap: 12px; }}
                .badge {{ background: #0284C7; color: white; font-size: 12px; padding: 4px 10px; border-radius: 999px; font-weight: bold; text-transform: uppercase; }}
                .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 24px; }}
                .card {{ background: #0F172A; padding: 20px; border-radius: 12px; border: 1px solid #1E293B; }}
                .card h3 {{ color: #F1F5F9; margin-top: 0; font-size: 18px; }}
                code {{ background: #020617; color: #38BDF8; padding: 3px 8px; border-radius: 6px; font-family: monospace; font-size: 13px; }}
                ul {{ padding-left: 20px; color: #94A3B8; font-size: 14px; line-height: 1.6; }}
                a {{ color: #38BDF8; text-decoration: none; font-weight: 500; }}
                a:hover {{ text-decoration: underline; }}
                .footer {{ margin-top: 30px; text-align: center; color: #64748B; font-size: 13px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Universal Agentic Commerce Node <span class="badge">Production Ready</span></h1>
                <p style="color: #94A3B8; font-size: 16px;">
                    Dual-interface autonomous commerce gateway running <strong>Clean Architecture</strong> on Render.
                    Current Active Merchant: <strong style="color: #F8FAFC;">{merchant_name}</strong> (<code>{active_merchant_id}</code>).
                </p>

                <div class="grid">
                    <div class="card">
                        <h3>⚡ MCP Interface (M2T)</h3>
                        <p style="font-size: 14px; color: #94A3B8;">For tool-calling agents (Claude Desktop, Cursor, Swarm):</p>
                        <ul>
                            <li>SSE Endpoint: <code><a href="/sse">/sse</a></code></li>
                            <li>Tools Discovery: <code><a href="/mcp/tools">/mcp/tools</a></code></li>
                            <li>Direct RPC Call: <code>POST /mcp/call</code></li>
                        </ul>
                    </div>
                    <div class="card">
                        <h3>🌐 UAP / A2A Protocol</h3>
                        <p style="font-size: 14px; color: #94A3B8;">For peer-to-peer autonomous buyer agents:</p>
                        <ul>
                            <li>Agent Card: <code><a href="/.well-known/agent.json">/.well-known/agent.json</a></code></li>
                            <li>Intent Negotiation: <code>POST /uap/v1/negotiate</code></li>
                            <li>Signed Settlement: <code>POST /uap/v1/transact</code></li>
                        </ul>
                    </div>
                </div>

                <div class="card" style="margin-top: 20px;">
                    <h3>🛡️ Zero-Trust Security & Bounded Gatekeeper</h3>
                    <ul>
                        <li><strong>Deterministic Clamping:</strong> <code>min(requested, product.max, merchant.max)</code></li>
                        <li><strong>Atomic Redis Gatekeeper:</strong> Sub-ms Lua script spend budget verification</li>
                        <li><strong>24-Hour Idempotency:</strong> Replay attack cache & double-charge defense</li>
                        <li><strong>Privacy-Preserving Audit:</strong> Masked PII append-only PostgreSQL ledger</li>
                        <li><strong>Payment Rails:</strong> Razorpay Sandbox Test Mode</li>
                    </ul>
                </div>

                <div class="footer">
                    Universal Agentic Commerce Node &bull; Clean Architecture &bull; Ready for Render Web Service
                </div>
            </div>
        </body>
        </html>
        """

    # Expose helper references for test harness
    app.state.catalog_repo = catalog_repo
    app.state.audit_repo = audit_repo
    app.state.gatekeeper = gatekeeper
    app.state.payment_rail = payment_rail
    app.state.mcp_controller = mcp_controller
    app.state.search_catalog_uc = search_catalog_uc
    app.state.request_quote_uc = request_quote_uc
    app.state.execute_checkout_uc = execute_checkout_uc
    app.state.inspect_audit_uc = inspect_audit_uc
    app.state.negotiate_intent_uc = negotiate_intent_uc

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", settings.PORT))
    uvicorn.run("src.infrastructure.server:app", host="0.0.0.0", port=port, reload=False)
