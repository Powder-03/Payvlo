"""Model Context Protocol (MCP) Tool Ingress Controller.

Clean Architecture layer: Adapters.
Exposes merchant catalog, quote, checkout, and audit tools to tool-calling agents
(Claude Desktop, Cursor, OpenAI Swarm) over FastMCP / SSE.
"""
import json
import uuid
import asyncio
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, Query, Response
from fastapi.responses import StreamingResponse, JSONResponse

from ..application.use_cases import (
    SearchCatalogUseCase,
    RequestQuoteUseCase,
    ExecuteCheckoutUseCase,
    InspectAuditUseCase,
    OnboardMerchantUseCase,
    SyncMerchantCatalogUseCase,
)
from ..application.dto import (
    CatalogSearchInputDTO,
    QuoteRequestInputDTO,
    QuoteRequestItemDTO,
    CheckoutInputDTO,
    AddressDTO,
    AuditInspectInputDTO,
    MerchantOnboardInputDTO,
    CatalogSyncConfigDTO,
    DirectProductInputDTO,
    CatalogSyncTriggerDTO,
)
from ..domain.exceptions import DomainError
from ..domain.entities import current_utc_timestamp
from .mcp_schemas import get_mcp_tool_definitions

logger = logging.getLogger("MCPController")


class MCPController:
    """Ingress controller wrapping Application Use Cases into MCP Tool definitions and SSE handler."""

    def __init__(
        self,
        search_catalog_uc: SearchCatalogUseCase,
        request_quote_uc: RequestQuoteUseCase,
        execute_checkout_uc: ExecuteCheckoutUseCase,
        inspect_audit_uc: InspectAuditUseCase,
        onboard_merchant_uc: Optional[OnboardMerchantUseCase] = None,
        sync_catalog_uc: Optional[SyncMerchantCatalogUseCase] = None,
        merchant_name: str = "Universal Agentic Merchant",
    ):
        self.search_catalog_uc = search_catalog_uc
        self.request_quote_uc = request_quote_uc
        self.execute_checkout_uc = execute_checkout_uc
        self.inspect_audit_uc = inspect_audit_uc
        self.onboard_merchant_uc = onboard_merchant_uc
        self.sync_catalog_uc = sync_catalog_uc
        self.merchant_name = merchant_name

    # ==========================================
    # Tool Methods (Direct Callable by Agent Runtimes)
    # ==========================================
    def search_store_catalog(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        merchant_id: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Tool: search_store_catalog

        Search and discover available products, live stock counts, and prices in the merchant store.
        """
        try:
            dto = CatalogSearchInputDTO(
                query=query,
                category=category,
                min_price=min_price,
                max_price=max_price,
                merchant_id=merchant_id,
                limit=limit,
            )
            result = self.search_catalog_uc.execute(dto)
            return {
                "success": True,
                "merchant_id": result.merchant_id,
                "total_items": result.total_count,
                "products": [p.model_dump() for p in result.products],
            }
        except DomainError as de:
            return {"success": False, "error": de.to_dict()}
        except Exception as ex:
            return {"success": False, "error": {"type": "InternalError", "message": str(ex)}}

    def request_price_quote(
        self,
        items: List[Dict[str, Any]],
        requested_discount: float = 0.0,
        merchant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tool: request_price_quote

        Submit a list of product IDs and quantities to receive a cryptographically & temporally bound quote with deterministic discount clamping.
        """
        try:
            parsed_items = [
                QuoteRequestItemDTO(
                    product_id=it.get("product_id") or it.get("sku", ""),
                    quantity=it.get("quantity", 1),
                    requested_discount_pct=it.get("requested_discount_pct", 0.0),
                )
                for it in items
            ]
            dto = QuoteRequestInputDTO(
                items=parsed_items,
                overall_requested_discount_pct=requested_discount,
                merchant_id=merchant_id,
            )
            quote = self.request_quote_uc.execute(dto)
            return {
                "success": True,
                "quote": quote.model_dump(),
            }
        except DomainError as de:
            return {"success": False, "error": de.to_dict()}
        except Exception as ex:
            return {"success": False, "error": {"type": "InternalError", "message": str(ex)}}

    def execute_bounded_checkout(
        self,
        quote_id: str,
        idempotency_key: str,
        user_id: str,
        max_spend_budget: Optional[float] = None,
        user_authorized_budget: Optional[float] = None,
        shipping_address: Optional[Dict[str, Any]] = None,
        merchant_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Tool: execute_bounded_checkout

        Execute checkout with strict budget bounds, atomic spend cap validation, 24h idempotency defense, and Razorpay test payment rails.
        """
        try:
            budget = max_spend_budget if max_spend_budget is not None else user_authorized_budget
            if budget is None:
                budget = 100000.0

            addr_dto = None
            if shipping_address:
                addr_dto = AddressDTO(
                    line1=shipping_address.get("line1") or shipping_address.get("street_address", "Default Street"),
                    line2=shipping_address.get("line2"),
                    city=shipping_address.get("city", "Bengaluru"),
                    state=shipping_address.get("state", "KA"),
                    postal_code=shipping_address.get("postal_code", "560001"),
                    country=shipping_address.get("country", "IN"),
                    phone=shipping_address.get("phone"),
                    email=shipping_address.get("email"),
                )

            dto = CheckoutInputDTO(
                quote_id=quote_id,
                idempotency_key=idempotency_key,
                user_id=user_id,
                max_spend_budget=budget,
                shipping_address=addr_dto,
                merchant_id=merchant_id,
            )
            order_res = self.execute_checkout_uc.execute(dto)
            return {
                "success": True,
                "order": order_res.model_dump(),
            }
        except DomainError as de:
            return {"success": False, "error": de.to_dict()}
        except Exception as ex:
            return {"success": False, "error": {"type": "InternalError", "message": str(ex)}}

    def inspect_audit_trail(
        self,
        merchant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Tool: inspect_audit_trail

        Inspect explainable append-only ledger entries with privacy-preserving masked PII.
        """
        try:
            dto = AuditInspectInputDTO(
                merchant_id=merchant_id,
                user_id=user_id,
                limit=limit,
            )
            res = self.inspect_audit_uc.execute(dto)
            return {
                "success": True,
                "total_entries": res.total_entries,
                "entries": [e.model_dump() for e in res.entries],
            }
        except DomainError as de:
            return {"success": False, "error": de.to_dict()}
    def onboard_merchant(
        self,
        merchant_id: str,
        merchant_name: str,
        category: str,
        currency: str = "INR",
        max_discount_percentage: float = 15.0,
        per_tx_spend_cap: float = 10000.0,
        daily_merchant_spend_cap: float = 100000.0,
        sync_config: Optional[Dict[str, Any]] = None,
        initial_products: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Tool: onboard_merchant

        Dynamically onboard a new merchant (Shopify, Custom REST API, or Direct) onto the agentic node.
        """
        if not self.onboard_merchant_uc:
            return {"success": False, "error": {"type": "FeatureDisabled", "message": "Onboarding use case not configured."}}
        try:
            sync_dto = None
            if sync_config:
                sync_dto = CatalogSyncConfigDTO(
                    provider=sync_config.get("provider", "direct"),
                    endpoint_url=sync_config.get("endpoint_url"),
                    access_token=sync_config.get("access_token"),
                    field_mapping=sync_config.get("field_mapping", {}),
                    auto_sync=sync_config.get("auto_sync", False),
                )

            products_dto = None
            if initial_products:
                products_dto = [
                    DirectProductInputDTO(
                        sku=p["sku"],
                        title=p["title"],
                        description=p.get("description", ""),
                        price_inr=float(p.get("price_inr", p.get("price", 0.0))),
                        inventory_count=int(p.get("inventory_count", p.get("inventory", 10))),
                        category=p.get("category", category),
                        max_discount_percentage=float(p.get("max_discount_percentage", max_discount_percentage)),
                        tags=p.get("tags", []),
                    )
                    for p in initial_products
                ]

            dto = MerchantOnboardInputDTO(
                merchant_id=merchant_id,
                merchant_name=merchant_name,
                category=category,
                currency=currency,
                max_discount_percentage=max_discount_percentage,
                per_tx_spend_cap=per_tx_spend_cap,
                daily_merchant_spend_cap=daily_merchant_spend_cap,
                sync_config=sync_dto,
                initial_products=products_dto,
            )
            res = self.onboard_merchant_uc.execute(dto)
            return {"success": True, "result": res.model_dump()}
        except DomainError as de:
            return {"success": False, "error": de.to_dict()}
        except Exception as ex:
            return {"success": False, "error": {"type": "InternalError", "message": str(ex)}}

    def sync_merchant_catalog(
        self,
        merchant_id: str,
        raw_payload: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Tool: sync_merchant_catalog

        Trigger on-demand catalog sync from Shopify or Custom REST API for a merchant.
        """
        if not self.sync_catalog_uc:
            return {"success": False, "error": {"type": "FeatureDisabled", "message": "Sync use case not configured."}}
        try:
            trigger_dto = CatalogSyncTriggerDTO(raw_payload=raw_payload) if raw_payload else None
            res = self.sync_catalog_uc.execute(merchant_id, trigger_dto)
            return {"success": True, "result": res.model_dump()}
        except DomainError as de:
            return {"success": False, "error": de.to_dict()}
        except Exception as ex:
            return {"success": False, "error": {"type": "InternalError", "message": str(ex)}}

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns JSON-Schema tool definitions formatted for Claude Desktop & Cursor MCP clients."""
        return get_mcp_tool_definitions()


def create_mcp_router(controller: MCPController) -> APIRouter:
    """Builds FastAPI router for MCP SSE transport and JSON-RPC 2.0 endpoints."""
    router = APIRouter(tags=["MCP Interface"])
    sse_sessions: Dict[str, asyncio.Queue] = {}

    tool_dispatch = {
        "search_store_catalog": controller.search_store_catalog,
        "request_price_quote": controller.request_price_quote,
        "execute_bounded_checkout": controller.execute_bounded_checkout,
        "inspect_audit_trail": controller.inspect_audit_trail,
        "onboard_merchant": controller.onboard_merchant,
        "sync_merchant_catalog": controller.sync_merchant_catalog,
    }

    def _execute_tool(tool_name: str, arguments: dict) -> dict:
        handler = tool_dispatch.get(tool_name)
        if not handler:
            return {
                "success": False,
                "error": {
                    "type": "InvalidTool",
                    "message": f"Tool '{tool_name}' is not recognized.",
                },
            }
        try:
            return handler(**arguments)
        except Exception as ex:
            logger.error(f"Error executing MCP tool {tool_name}: {ex}")
            return {
                "success": False,
                "error": {
                    "type": "ExecutionError",
                    "message": str(ex),
                },
            }

    @router.get("/mcp/tools")
    def list_mcp_tools():
        """Lists all registered tools for tool-calling agents."""
        return {
            "node_name": controller.merchant_name,
            "transport": "sse",
            "tools": controller.get_tool_definitions(),
        }

    @router.post("/mcp/call")
    async def call_tool_direct(request: Request):
        """Standard HTTP tool invocation bridge."""
        body = await request.json()
        tool_name = body.get("name") or body.get("tool")
        arguments = body.get("arguments") or body.get("params") or {}
        return _execute_tool(tool_name, arguments)

    @router.get("/sse")
    async def sse_endpoint(request: Request):
        """Official MCP SSE Transport endpoint. Emits endpoint event and streams JSON-RPC responses."""
        session_id = uuid.uuid4().hex
        queue: asyncio.Queue = asyncio.Queue()
        sse_sessions[session_id] = queue

        async def event_generator():
            try:
                # 1. Official MCP Spec: emit endpoint URL where client must POST messages
                endpoint_url = f"/messages?sessionId={session_id}"
                yield f"event: endpoint\ndata: {endpoint_url}\n\n"

                # 2. Stream JSON-RPC messages and ping keep-alives
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                        yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                    except asyncio.TimeoutError:
                        yield f": ping {current_utc_timestamp()}\n\n"
            finally:
                sse_sessions.pop(session_id, None)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )

    @router.post("/messages")
    async def handle_mcp_messages(request: Request, sessionId: Optional[str] = None):
        """Official MCP JSON-RPC 2.0 Message Ingress."""
        try:
            body = await request.json()
        except Exception:
            return Response(status_code=400, content="Invalid JSON")

        msg_id = body.get("id")
        method = body.get("method")
        params = body.get("params") or {}

        response = None

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": f"Payvlo Commerce Gateway ({controller.merchant_name})",
                        "version": "1.0.0"
                    }
                }
            }
        elif method == "notifications/initialized":
            return Response(status_code=202)
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": controller.get_tool_definitions()
                }
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            tool_res = _execute_tool(tool_name, arguments)
            
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(tool_res, indent=2)
                        }
                    ],
                    "isError": not tool_res.get("success", True)
                }
            }
        elif method == "ping":
            response = {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        # If connected via active SSE session, stream message back on SSE channel
        if sessionId and sessionId in sse_sessions and response:
            await sse_sessions[sessionId].put(response)
            return Response(status_code=202)

        # Fallback to direct HTTP JSON response
        if response:
            return JSONResponse(content=response)
        return Response(status_code=202)

    return router
