"""MCP Tool Execution Handler.

Connects Model Context Protocol tool requests with domain use cases.
"""
import logging
from typing import List, Dict, Any, Optional

from ...application.use_cases import (
    SearchCatalogUseCase,
    RequestQuoteUseCase,
    ExecuteCheckoutUseCase,
    InspectAuditUseCase,
    OnboardMerchantUseCase,
    SyncMerchantCatalogUseCase,
)
from ...application.dto import (
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
from ...domain.exceptions import DomainError
from .schemas import get_mcp_tool_definitions

logger = logging.getLogger("MCPToolExecutor")


class MCPToolExecutor:
    """Wraps Application Use Cases into directly invokable MCP Tool functions."""

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

    def search_store_catalog(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        merchant_id: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Tool: search_store_catalog."""
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
        """Tool: request_price_quote."""
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
        address_label: Optional[str] = None,
        fulfillment_type: str = "DELIVERY",
        fulfillment_notes: Optional[str] = None,
        merchant_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Tool: execute_bounded_checkout."""
        try:
            budget = max_spend_budget if max_spend_budget is not None else user_authorized_budget
            if budget is None:
                budget = 100000.0

            # Fallback check kwargs for label/notes
            lbl = address_label or kwargs.get("label") or kwargs.get("address_shortcut")
            ftype = fulfillment_type or kwargs.get("fulfillment", "DELIVERY")
            fnotes = fulfillment_notes or kwargs.get("notes") or kwargs.get("table_number")

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
                address_label=lbl,
                fulfillment_type=ftype,
                fulfillment_notes=fnotes,
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
        """Tool: inspect_audit_trail."""
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
        """Tool: onboard_merchant."""
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
        """Tool: sync_merchant_catalog."""
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


# Backward compatibility alias
MCPController = MCPToolExecutor
