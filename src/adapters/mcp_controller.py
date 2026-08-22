"""Model Context Protocol (MCP) Tool Ingress Controller.

Clean Architecture layer: Adapters.
Exposes merchant catalog, quote, checkout, and audit tools to tool-calling agents
(Claude Desktop, Cursor, OpenAI Swarm) over FastMCP / SSE.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, Query, Response
from fastapi.responses import StreamingResponse

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
        max_spend_budget: float,
        shipping_address: Optional[Dict[str, Any]] = None,
        merchant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tool: execute_bounded_checkout

        Execute checkout with strict budget bounds, atomic spend cap validation, 24h idempotency defense, and Razorpay test payment rails.
        """
        try:
            addr_dto = None
            if shipping_address:
                addr_dto = AddressDTO(
                    line1=shipping_address.get("line1", "Default Street"),
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
                max_spend_budget=max_spend_budget,
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

    # ==========================================
    # MCP Protocol Schemas & Tool Definitions
    # ==========================================
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns JSON-Schema tool definitions formatted for Claude Desktop & Cursor MCP clients."""
        return [
            {
                "name": "search_store_catalog",
                "description": "Discover available products, live stock counts, and prices in the merchant store catalog.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search keyword or SKU"},
                        "category": {"type": "string", "description": "Category filter"},
                        "min_price": {"type": "number", "description": "Minimum price in INR"},
                        "max_price": {"type": "number", "description": "Maximum price in INR"},
                        "merchant_id": {"type": "string", "description": "Merchant ID"},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            },
            {
                "name": "request_price_quote",
                "description": "Submit a list of products to compute a bound quote with deterministic discount clamping.",
                "inputSchema": {
                    "type": "object",
                    "required": ["items"],
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["product_id"],
                                "properties": {
                                    "product_id": {"type": "string"},
                                    "quantity": {"type": "integer", "default": 1},
                                    "requested_discount_pct": {"type": "number", "default": 0.0},
                                },
                            },
                        },
                        "requested_discount": {"type": "number", "default": 0.0},
                        "merchant_id": {"type": "string"},
                    },
                },
            },
            {
                "name": "execute_bounded_checkout",
                "description": "Execute checkout with strict budget bounds, 24h idempotency key, atomic spend cap check, and Razorpay rails.",
                "inputSchema": {
                    "type": "object",
                    "required": ["quote_id", "idempotency_key", "user_id", "max_spend_budget"],
                    "properties": {
                        "quote_id": {"type": "string"},
                        "idempotency_key": {"type": "string"},
                        "user_id": {"type": "string"},
                        "max_spend_budget": {"type": "number"},
                        "shipping_address": {
                            "type": "object",
                            "properties": {
                                "line1": {"type": "string"},
                                "line2": {"type": "string"},
                                "city": {"type": "string"},
                                "state": {"type": "string"},
                                "postal_code": {"type": "string"},
                                "phone": {"type": "string"},
                                "email": {"type": "string"},
                            },
                        },
                        "merchant_id": {"type": "string"},
                    },
                },
            },
            {
                "name": "inspect_audit_trail",
                "description": "Inspect append-only ledger entries with privacy-preserving masked PII and explainable decisions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "merchant_id": {"type": "string"},
                        "user_id": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                },
            },
            {
                "name": "onboard_merchant",
                "description": "Dynamically onboard any merchant (Shopify, Custom REST API, or Direct) with custom spending guardrails.",
                "inputSchema": {
                    "type": "object",
                    "required": ["merchant_id", "merchant_name", "category"],
                    "properties": {
                        "merchant_id": {"type": "string", "description": "Unique merchant slug"},
                        "merchant_name": {"type": "string", "description": "Brand / Store name"},
                        "category": {"type": "string", "description": "Store category"},
                        "currency": {"type": "string", "default": "INR"},
                        "max_discount_percentage": {"type": "number", "default": 15.0},
                        "per_tx_spend_cap": {"type": "number", "default": 10000.0},
                        "daily_merchant_spend_cap": {"type": "number", "default": 100000.0},
                        "sync_config": {
                            "type": "object",
                            "properties": {
                                "provider": {"type": "string", "description": "'shopify', 'custom_api', or 'direct'"},
                                "endpoint_url": {"type": "string"},
                                "access_token": {"type": "string"},
                            },
                        },
                    },
                },
            },
            {
                "name": "sync_merchant_catalog",
                "description": "Trigger catalog synchronization from Shopify or external REST API for a registered merchant.",
                "inputSchema": {
                    "type": "object",
                    "required": ["merchant_id"],
                    "properties": {
                        "merchant_id": {"type": "string", "description": "Merchant ID to sync"},
                    },
                },
            },
        ]


def create_mcp_router(controller: MCPController) -> APIRouter:
    """Builds FastAPI router for MCP SSE transport and HTTP endpoints."""
    router = APIRouter(tags=["MCP Interface"])

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
        """Standard JSON-RPC 2.0 / HTTP tool invocation bridge."""
        body = await request.json()
        tool_name = body.get("name") or body.get("tool")
        arguments = body.get("arguments") or body.get("params") or {}

        if tool_name == "search_store_catalog":
            return controller.search_store_catalog(**arguments)
        elif tool_name == "request_price_quote":
            return controller.request_price_quote(**arguments)
        elif tool_name == "execute_bounded_checkout":
            return controller.execute_bounded_checkout(**arguments)
        elif tool_name == "inspect_audit_trail":
            return controller.inspect_audit_trail(**arguments)
        elif tool_name == "onboard_merchant":
            return controller.onboard_merchant(**arguments)
        elif tool_name == "sync_merchant_catalog":
            return controller.sync_merchant_catalog(**arguments)
        else:
            return {
                "success": False,
                "error": {
                    "type": "InvalidTool",
                    "message": f"Tool '{tool_name}' is not recognized.",
                },
            }

    @router.get("/sse")
    async def sse_endpoint(request: Request):
        """Server-Sent Events (SSE) stream for FastMCP protocol connections."""
        async def event_generator():
            # Initial handshake message
            init_event = {
                "event": "connected",
                "data": json.dumps({
                    "status": "ready",
                    "protocol": "mcp/sse/1.0",
                    "server": controller.merchant_name,
                    "tools_count": len(controller.get_tool_definitions()),
                }),
            }
            yield f"event: {init_event['event']}\ndata: {init_event['data']}\n\n"

            # Ping keep-alive
            ping_event = {
                "event": "ping",
                "data": json.dumps({"timestamp": current_utc_timestamp()}),
            }
            yield f"event: {ping_event['event']}\ndata: {ping_event['data']}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )

    return router
