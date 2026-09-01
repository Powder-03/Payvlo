"""MCP Tool Invocation and Discovery Endpoints."""
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request

from ...schemas.mcp import get_mcp_tool_definitions
from ...schemas.catalog import CatalogSearchInputSchema
from ...schemas.quote import QuoteRequestInputSchema, QuoteRequestItemSchema
from ...schemas.checkout import CheckoutInputSchema, AddressSchema
from ...schemas.audit import AuditInspectInputSchema
from ...schemas.catalog import MerchantOnboardInputSchema, DirectProductInputSchema
from ...core.exceptions import DomainError

logger = logging.getLogger("MCPToolsAPI")
router = APIRouter(tags=["MCP Interface"])


def execute_tool_call(app, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatches MCP tool execution directly to application services."""
    try:
        if tool_name == "search_store_catalog":
            catalog_service = app.state.catalog_service
            dto = CatalogSearchInputSchema(
                query=arguments.get("query"),
                category=arguments.get("category"),
                min_price=arguments.get("min_price"),
                max_price=arguments.get("max_price"),
                merchant_id=arguments.get("merchant_id"),
                limit=arguments.get("limit", 20),
            )
            res = catalog_service.search_products(dto)
            return {
                "success": True,
                "merchant_id": res.merchant_id,
                "total_items": res.total_count,
                "products": [p.model_dump() for p in res.products],
            }

        elif tool_name == "request_price_quote":
            quote_service = app.state.quote_service
            items_raw = arguments.get("items", [])
            items = [
                QuoteRequestItemSchema(
                    product_id=it.get("product_id") or it.get("sku", ""),
                    quantity=it.get("quantity", 1),
                    requested_discount_pct=it.get("requested_discount_pct", 0.0),
                )
                for it in items_raw
            ]
            dto = QuoteRequestInputSchema(
                items=items,
                overall_requested_discount_pct=arguments.get("requested_discount", 0.0),
                merchant_id=arguments.get("merchant_id"),
            )
            quote = quote_service.calculate_quote(dto)
            return {"success": True, "quote": quote.model_dump()}

        elif tool_name == "execute_bounded_checkout":
            checkout_service = app.state.checkout_service
            budget = (
                arguments.get("max_spend_budget")
                if arguments.get("max_spend_budget") is not None
                else arguments.get("user_authorized_budget", 100000.0)
            )

            addr_raw = arguments.get("shipping_address")
            addr_dto = None
            if addr_raw:
                addr_dto = AddressSchema(
                    line1=addr_raw.get("line1") or addr_raw.get("street_address", "Default Street"),
                    line2=addr_raw.get("line2"),
                    city=addr_raw.get("city", "Bengaluru"),
                    state=addr_raw.get("state", "KA"),
                    postal_code=addr_raw.get("postal_code", "560001"),
                    country=addr_raw.get("country", "IN"),
                    phone=addr_raw.get("phone"),
                    email=addr_raw.get("email"),
                )

            lbl = arguments.get("address_label") or arguments.get("label") or arguments.get("address_shortcut")
            ftype = arguments.get("fulfillment_type") or arguments.get("fulfillment", "DELIVERY")
            fnotes = arguments.get("fulfillment_notes") or arguments.get("notes") or arguments.get("table_number")

            dto = CheckoutInputSchema(
                quote_id=arguments["quote_id"],
                idempotency_key=arguments["idempotency_key"],
                user_id=arguments["user_id"],
                max_spend_budget=budget,
                shipping_address=addr_dto,
                address_label=lbl,
                fulfillment_type=ftype,
                fulfillment_notes=fnotes,
                merchant_id=arguments.get("merchant_id"),
            )
            order_res = checkout_service.execute_checkout(dto)
            return {"success": True, "order": order_res.model_dump()}

        elif tool_name == "inspect_audit_trail":
            audit_service = app.state.audit_service
            dto = AuditInspectInputSchema(
                merchant_id=arguments.get("merchant_id"),
                user_id=arguments.get("user_id"),
                limit=arguments.get("limit", 20),
            )
            res = audit_service.inspect_audit_trail(dto)
            return {
                "success": True,
                "total_entries": res.total_entries,
                "entries": [e.model_dump() for e in res.entries],
            }

        elif tool_name == "onboard_merchant":
            catalog_service = app.state.catalog_service
            initial_p = None
            if arguments.get("initial_products"):
                initial_p = [
                    DirectProductInputSchema(
                        sku=p["sku"],
                        title=p["title"],
                        price_inr=p["price_inr"],
                        inventory_count=p.get("inventory_count", 10),
                        category=p.get("category", "General"),
                        max_discount_percentage=p.get("max_discount_percentage", 0.0),
                    )
                    for p in arguments["initial_products"]
                ]

            dto = MerchantOnboardInputSchema(
                merchant_id=arguments["merchant_id"],
                merchant_name=arguments["merchant_name"],
                category=arguments["category"],
                max_discount_percentage=arguments.get("max_discount_percentage", 15.0),
                per_tx_spend_cap=arguments.get("per_tx_spend_cap", 10000.0),
                daily_merchant_spend_cap=arguments.get("daily_merchant_spend_cap", 100000.0),
                support_email=arguments.get("support_email", "support@merchant.com"),
                initial_products=initial_p,
            )
            res = catalog_service.onboard_merchant(dto)
            return {"success": True, "result": res.model_dump()}

        elif tool_name == "sync_merchant_catalog":
            catalog_service = app.state.catalog_service
            res = catalog_service.sync_merchant_catalog(arguments["merchant_id"])
            return {"success": True, "result": res.model_dump()}

        else:
            return {
                "success": False,
                "error": {"type": "InvalidTool", "message": f"Tool '{tool_name}' is not recognized."},
            }
    except DomainError as de:
        return {"success": False, "error": de.to_dict()}
    except Exception as ex:
        logger.error(f"Error executing MCP tool {tool_name}: {ex}")
        return {"success": False, "error": {"type": "ExecutionError", "message": str(ex)}}


@router.get("/mcp/tools")
def list_mcp_tools(request: Request):
    """Lists all registered tools for Claude Desktop / Cursor MCP clients."""
    node_name = getattr(request.app.state, "active_merchant_name", "Payvlo Commerce Gateway")
    return {
        "node_name": node_name,
        "transport": "sse",
        "tools": get_mcp_tool_definitions(),
    }


@router.post("/mcp/call")
async def call_tool_direct(request: Request):
    """Standard HTTP tool invocation bridge."""
    body = await request.json()
    tool_name = body.get("name") or body.get("tool")
    arguments = body.get("arguments") or body.get("params") or {}
    return execute_tool_call(request.app, tool_name, arguments)
