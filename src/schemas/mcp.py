"""Model Context Protocol (MCP) JSON Schema Definitions."""
from typing import List, Dict, Any


def get_mcp_tool_definitions() -> List[Dict[str, Any]]:
    """Returns official MCP JSON-Schema tool definitions for registered agent tools."""
    return [
        {
            "name": "search_store_catalog",
            "description": "Discover available products, live stock counts, and prices in the merchant store catalog.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword or SKU (e.g. 'Pizza', 'Protein', 'DOM-PIZ-001')",
                    },
                    "category": {
                        "type": "string",
                        "description": "Category filter (e.g. 'Pizzas', 'Supplements')",
                    },
                    "min_price": {
                        "type": "number",
                        "description": "Minimum price in INR",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price in INR",
                    },
                    "merchant_id": {
                        "type": "string",
                        "description": "Merchant ID (defaults to active node merchant if omitted)",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "description": "Maximum products to return (1-100)",
                    },
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
                        "description": "List of products and quantities to purchase",
                        "items": {
                            "type": "object",
                            "required": ["product_id"],
                            "properties": {
                                "product_id": {"type": "string"},
                                "quantity": {"type": "integer", "default": 1},
                                "requested_discount_pct": {
                                    "type": "number",
                                    "default": 0.0,
                                },
                            },
                        },
                    },
                    "requested_discount": {
                        "type": "number",
                        "default": 0.0,
                        "description": "Overall requested discount percentage",
                    },
                    "merchant_id": {
                        "type": "string",
                        "description": "Merchant ID",
                    },
                },
            },
        },
        {
            "name": "execute_bounded_checkout",
            "description": "Execute checkout with strict budget bounds, 24h idempotency key, atomic spend cap check, and Razorpay rails.",
            "inputSchema": {
                "type": "object",
                "required": [
                    "quote_id",
                    "idempotency_key",
                    "user_id",
                    "max_spend_budget",
                ],
                "properties": {
                    "quote_id": {
                        "type": "string",
                        "description": "Active quote ID obtained from request_price_quote",
                    },
                    "idempotency_key": {
                        "type": "string",
                        "description": "Unique transaction key (UUID) to prevent double billing within 24h",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Buyer user or agent ID",
                    },
                    "max_spend_budget": {
                        "type": "number",
                        "description": "Strict maximum authorized budget in INR",
                    },
                    "address_label": {
                        "type": "string",
                        "description": "Address shortcut from user's address book (e.g. 'Home', 'Work', 'Hostel')",
                    },
                    "fulfillment_type": {
                        "type": "string",
                        "enum": ["DELIVERY", "DINE_IN", "PICKUP"],
                        "default": "DELIVERY",
                        "description": "Fulfillment type (e.g. 'DELIVERY', 'DINE_IN', 'PICKUP')",
                    },
                    "fulfillment_notes": {
                        "type": "string",
                        "description": "Table number or delivery notes (e.g. 'Table #4', 'Ring doorbell')",
                    },
                    "shipping_address": {
                        "type": "object",
                        "properties": {
                            "line1": {"type": "string"},
                            "line2": {"type": "string"},
                            "city": {"type": "string", "default": "Bengaluru"},
                            "state": {"type": "string", "default": "KA"},
                            "postal_code": {"type": "string", "default": "560001"},
                            "country": {"type": "string", "default": "IN"},
                            "phone": {"type": "string"},
                            "email": {"type": "string"},
                        },
                    },
                    "merchant_id": {
                        "type": "string",
                        "description": "Merchant ID",
                    },
                },
            },
        },
        {
            "name": "inspect_audit_trail",
            "description": "Query immutable, privacy-masked transaction audit ledger.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "merchant_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        },
        {
            "name": "onboard_merchant",
            "description": "Onboard a new merchant store node with pricing guardrails, inventory, and sync configuration.",
            "inputSchema": {
                "type": "object",
                "required": ["merchant_id", "merchant_name", "category"],
                "properties": {
                    "merchant_id": {"type": "string"},
                    "merchant_name": {"type": "string"},
                    "category": {"type": "string"},
                    "max_discount_percentage": {"type": "number", "default": 15.0},
                    "per_tx_spend_cap": {"type": "number", "default": 10000.0},
                    "daily_merchant_spend_cap": {
                        "type": "number",
                        "default": 100000.0,
                    },
                    "support_email": {
                        "type": "string",
                        "default": "support@merchant.com",
                    },
                    "initial_products": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["sku", "title", "price_inr"],
                            "properties": {
                                "sku": {"type": "string"},
                                "title": {"type": "string"},
                                "price_inr": {"type": "number"},
                                "inventory_count": {
                                    "type": "integer",
                                    "default": 10,
                                },
                                "category": {"type": "string", "default": "General"},
                                "max_discount_percentage": {
                                    "type": "number",
                                    "default": 0.0,
                                },
                            },
                        },
                    },
                },
            },
        },
        {
            "name": "sync_merchant_catalog",
            "description": "Trigger catalog synchronization for a merchant from Shopify or external API.",
            "inputSchema": {
                "type": "object",
                "required": ["merchant_id"],
                "properties": {
                    "merchant_id": {"type": "string"},
                },
            },
        },
    ]
