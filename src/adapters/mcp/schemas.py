"""Model Context Protocol (MCP) JSON Schema Definitions.

Clean Architecture layer: Adapters (MCP).
Defines inputSchema objects for Claude Desktop, Cursor, and MCP Inspector tools.
"""
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
                        "description": "Buyer agent identity or customer identifier",
                    },
                    "max_spend_budget": {
                        "type": "number",
                        "description": "Maximum authorized budget for this purchase",
                    },
                    "shipping_address": {
                        "type": "object",
                        "description": "Customer delivery address (optional if address_label is provided)",
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
                    "address_label": {
                        "type": "string",
                        "description": "Shortcut label from user's address book (e.g. 'Home', 'Work', 'Hostel')",
                    },
                    "fulfillment_type": {
                        "type": "string",
                        "enum": ["DELIVERY", "DINE_IN", "PICKUP"],
                        "default": "DELIVERY",
                        "description": "Fulfillment method: DELIVERY, DINE_IN, or PICKUP",
                    },
                    "fulfillment_notes": {
                        "type": "string",
                        "description": "Table number or delivery notes (e.g. 'Table #4', 'Gate 2 Concourse')",
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
            "description": "Inspect append-only ledger entries with privacy-preserving masked PII and explainable decisions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "merchant_id": {
                        "type": "string",
                        "description": "Filter by merchant ID",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Filter by user ID (will be hashed automatically)",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of ledger entries to inspect",
                    },
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
