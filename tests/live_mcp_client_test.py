"""Live MCP & A2A Client Test against running server.

Executes actual HTTP tool calls and SSE transport verification as an MCP Client.
"""
import sys
import os
import json
import uuid
import requests

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.seed_test_data import seed_test_environment

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def test_live_mcp():
    print("=" * 80)
    print("🤖 LIVE MCP CLIENT: CONNECTING TO PAYVLO SERVER")
    print(f"Target URL: {BASE_URL}")
    print("=" * 80)

    # 0. Ensure environment is seeded
    seed_test_environment()

    # 1. Health check
    h = requests.get(f"{BASE_URL}/healthz").json()
    print(f"\n[1] Server Health: {h['status']} | Active Node: {h['node_name']}")

    # 2. Tool Discovery (GET /mcp/tools)
    tools = requests.get(f"{BASE_URL}/mcp/tools").json()
    tool_names = [t["name"] for t in tools["tools"]]
    print(f"[2] Discovered {len(tool_names)} MCP Tools: {', '.join(tool_names)}")

    # 3. Tool Call: search_store_catalog on BeastLife
    print("\n[3] Tool Call -> search_store_catalog (BeastLife Nutrition)")
    res1 = requests.post(f"{BASE_URL}/mcp/call", json={
        "name": "search_store_catalog",
        "arguments": {"query": "protein", "merchant_id": "beastlife_d2c"}
    }).json()
    print(f"    ✓ Found {res1['total_items']} items:")
    for p in res1["products"][:2]:
        print(f"      • {p['title']} — ₹{p['price_inr']} (Max Disc: {p['max_discount_percentage']}%)")

    # 4. Tool Call: search_store_catalog on Urban Threads
    print("\n[4] Tool Call -> search_store_catalog (Urban Threads Streetwear)")
    res2 = requests.post(f"{BASE_URL}/mcp/call", json={
        "name": "search_store_catalog",
        "arguments": {"query": "hoodie", "merchant_id": "urban_threads"}
    }).json()
    print(f"    ✓ Found {res2['total_items']} items:")
    for p in res2["products"][:2]:
        print(f"      • {p['title']} — ₹{p['price_inr']} (Max Disc: {p['max_discount_percentage']}%)")

    # 5. Tool Call: request_price_quote with 90% prompt injection discount
    print("\n[5] Tool Call -> request_price_quote (Testing 90% Discount Clamping)")
    res3 = requests.post(f"{BASE_URL}/mcp/call", json={
        "name": "request_price_quote",
        "arguments": {
            "items": [{"product_id": "DOM-PIZ-001", "quantity": 2}],
            "requested_discount": 90.0,
            "merchant_id": "dominos_in"
        }
    }).json()
    q = res3["quote"]
    print(f"    🛡️  Original: ₹{q['total_original_price']} | Final: ₹{q['final_total_price']}")
    print(f"    🛡️  Clamped Rate: {q['items'][0]['effective_discount_pct']}% (Reason: {q['items'][0]['clamping_reason']})")
    quote_id = q["quote_id"]

    # 6. Tool Call: execute_bounded_checkout
    print("\n[6] Tool Call -> execute_bounded_checkout (Placing Bounded Order)")
    tx_key = f"live_tx_{uuid.uuid4().hex[:10]}"
    res4 = requests.post(f"{BASE_URL}/mcp/call", json={
        "name": "execute_bounded_checkout",
        "arguments": {
            "quote_id": quote_id,
            "user_id": "live_ai_mcp_client",
            "idempotency_key": tx_key,
            "max_spend_budget": 1000.0,
            "shipping_address": {
                "recipient_name": "Rishabh",
                "line1": "Indiranagar 100ft Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": "560038",
                "country": "IN",
                "phone": "+91-9876543210"
            },
            "merchant_id": "dominos_in"
        }
    }).json()
    order = res4["order"]
    print(f"    💳 Order ID: {order['order_id']}")
    print(f"    💳 Razorpay Rail ID: {order['payment_rail_id']}")
    print(f"    💳 Payment Link: {order['payment_link']}")
    print(f"    💳 Status: {order['payment_status']} | Final Billed: ₹{order['final_amount']}")

    # 7. Tool Call: 24h Idempotency Replay
    print("\n[7] Tool Call -> execute_bounded_checkout (Replaying identical idempotency key)")
    res5 = requests.post(f"{BASE_URL}/mcp/call", json={
        "name": "execute_bounded_checkout",
        "arguments": {
            "quote_id": quote_id,
            "user_id": "live_ai_mcp_client",
            "idempotency_key": tx_key,
            "max_spend_budget": 1000.0,
            "merchant_id": "dominos_in"
        }
    }).json()
    print(f"    🔒 Replay Defense Verified: is_replayed={res5['order']['is_replayed']} | Order ID matches: {res5['order']['order_id'] == order['order_id']}")

    # 8. Tool Call: inspect_audit_trail
    print("\n[8] Tool Call -> inspect_audit_trail (Verifying Masked PII Ledger)")
    res6 = requests.post(f"{BASE_URL}/mcp/call", json={
        "name": "inspect_audit_trail",
        "arguments": {"merchant_id": "dominos_in", "limit": 3}
    }).json()
    for e in res6["entries"][:2]:
        print(f"    📜 Audit ID: {e['audit_id']} | Action: {e['action']} | Status: {e['status']}")
        print(f"       Masked PII: {e['masked_pii_payload']}")

    print("\n" + "=" * 80)
    print("🎉 ALL LIVE MCP CLIENT TOOL CALLS EXECUTED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    test_live_mcp()
