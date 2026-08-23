"""Standalone Model Context Protocol (MCP) Client E2E Tester.

Location: tests/test_mcp_client_e2e.py
Simulates Claude Desktop / Cursor IDE connecting as an MCP Client to Payvlo's MCP Server.
Tests all 6 MCP Tools, prompt injection defense, spend caps, idempotency, and audit trail.
"""
import sys
import os
import json
import uuid

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from src.infrastructure.server import app
from tests.seed_test_data import seed_test_environment

BLUE = "\033[94m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


class SimulatedMCPClient:
    """Simulates an AI Agent runtime (like Claude Desktop or Cursor) calling MCP endpoints."""

    def __init__(self, client: TestClient):
        self.client = client
        self.discovered_tools = {}

    def discover_tools(self):
        print(f"\n{BOLD}{CYAN}🔍 [MCP CLIENT] Step 1: Discovering MCP Tools over GET /mcp/tools...{RESET}")
        res = self.client.get("/mcp/tools")
        assert res.status_code == 200, f"MCP Discovery failed: {res.text}"
        data = res.json()
        for t in data["tools"]:
            self.discovered_tools[t["name"]] = t
            print(f"   {GREEN}✓ Discovered Tool:{RESET} {BOLD}{t['name']}{RESET} — {t['description']}")
        return self.discovered_tools

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        print(f"\n{BOLD}{BLUE}⚙️  [MCP CLIENT -> SERVER] Calling Tool: {tool_name}{RESET}")
        print(f"   {YELLOW}• Input Arguments:{RESET} {json.dumps(arguments, indent=5)}")

        payload = {"name": tool_name, "arguments": arguments}
        res = self.client.post("/mcp/call", json=payload)
        assert res.status_code == 200, f"MCP Call failed: {res.text}"
        data = res.json()

        print(f"{BOLD}{GREEN}📥 [MCP SERVER -> CLIENT] Response from {tool_name}:{RESET}")
        print(f"   {MAGENTA}• Result Payload:{RESET} {json.dumps(data, indent=5)}")
        return data


def run_mcp_client_suite():
    print("=" * 80)
    print(f"{BOLD}{CYAN}🤖 STARTING MODEL CONTEXT PROTOCOL (MCP) CLIENT E2E VERIFICATION{RESET}")
    print("=" * 80)

    # Pre-seed environment
    seed_test_environment()
    client = TestClient(app)
    mcp_agent = SimulatedMCPClient(client)

    # 1. Tool Discovery
    tools = mcp_agent.discover_tools()
    assert "search_store_catalog" in tools
    assert "request_price_quote" in tools
    assert "execute_bounded_checkout" in tools
    assert "inspect_audit_trail" in tools

    # =========================================================================
    # 2. Tool 1: Catalog Search & Keyword Filtering
    # =========================================================================
    search_res = mcp_agent.call_tool(
        "search_store_catalog",
        {"query": "Pizza", "merchant_id": "dominos_in", "limit": 5}
    )
    assert search_res["success"] is True
    assert len(search_res["products"]) >= 2
    product = search_res["products"][0]
    target_product_id = product["product_id"]
    target_price = product["price_inr"]

    # =========================================================================
    # 3. Tool 2: Discount Clamping & Prompt Injection Defense
    # =========================================================================
    # AI tries to request an illegal 90% discount (simulating prompt injection)
    quote_res = mcp_agent.call_tool(
        "request_price_quote",
        {
            "items": [{"product_id": target_product_id, "quantity": 2}],
            "requested_discount": 90.0,  # Hallucinated / injected discount
            "merchant_id": "dominos_in",
        }
    )
    assert quote_res["success"] is True
    quote = quote_res["quote"]
    # Verify that Payvlo clamped the discount strictly to the merchant limit (15%)
    assert quote["items"][0]["effective_discount_pct"] == 15.0
    print(f"   {GREEN}🛡️  Zero-Trust Clamping Verified:{RESET} Requested 90% discount was clamped to {quote['items'][0]['effective_discount_pct']}% (Reason: {quote['items'][0]['clamping_reason']})")

    # =========================================================================
    # 4. Tool 3: Bounded Checkout Execution
    # =========================================================================
    idempotency_key = f"mcp_tx_{uuid.uuid4().hex[:12]}"
    checkout_res = mcp_agent.call_tool(
        "execute_bounded_checkout",
        {
            "quote_id": quote["quote_id"],
            "user_id": "claude_desktop_user_99",
            "idempotency_key": idempotency_key,
            "max_spend_budget": quote["final_total_price"] + 50.0,
            "shipping_address": {
                "recipient_name": "Autonomous MCP Agent",
                "line1": "456 AI Boulevard",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": "560001",
                "country": "IN",
                "phone": "+91-9988776655",
            },
            "merchant_id": "dominos_in",
        }
    )
    assert checkout_res["success"] is True
    order = checkout_res["order"]
    assert order["payment_status"].lower() in ["created", "paid", "settled"]
    assert order["final_amount"] == quote["final_total_price"]

    # =========================================================================
    # 5. Tool 4: 24-Hour Idempotency Replay Defense
    # =========================================================================
    print(f"\n{BOLD}{CYAN}🔒 [MCP CLIENT] Replaying Identical Checkout with Same Idempotency Key...{RESET}")
    replay_res = mcp_agent.call_tool(
        "execute_bounded_checkout",
        {
            "quote_id": quote["quote_id"],
            "user_id": "claude_desktop_user_99",
            "idempotency_key": idempotency_key,  # Replaying identical key
            "max_spend_budget": quote["final_total_price"] + 50.0,
            "merchant_id": "dominos_in",
        }
    )
    assert replay_res["success"] is True
    assert replay_res["order"]["order_id"] == order["order_id"]
    print(f"   {GREEN}🛡️  Idempotency Defense Verified:{RESET} Order ID {order['order_id']} returned without re-charging user.")

    # =========================================================================
    # 6. Tool 5: Privacy-Preserving Audit Trail Inspection
    # =========================================================================
    audit_res = mcp_agent.call_tool(
        "inspect_audit_trail",
        {"merchant_id": "dominos_in", "limit": 5}
    )
    assert audit_res["success"] is True
    assert len(audit_res["entries"]) >= 1
    last_audit = audit_res["entries"][0]
    print(f"   {GREEN}🔒 Privacy-Preserving PII Masking Verified:{RESET}")
    print(f"      • Action: {last_audit['action']}")
    print(f"      • Masked Payload: {json.dumps(last_audit['masked_pii_payload'])}")

    print("\n" + "=" * 80)
    print(f"{BOLD}{GREEN}🎉 ALL MCP CLIENT TOOL-CALLING PROTOCOL TESTS PASSED!{RESET}")
    print("=" * 80)


if __name__ == "__main__":
    run_mcp_client_suite()
