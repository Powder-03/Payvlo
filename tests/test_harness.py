"""Autonomous E2E Test Harness for Universal Agentic Commerce Node.

Validates:
1. MCP Tool calling flow (Claude Desktop / Cursor simulation: discovery -> clamping -> spend cap rejection -> checkout).
2. UAP / A2A Protocol flow (Agent Card discovery -> Intent negotiation -> Transact settlement).
3. Zero-Trust Bounded Gatekeeper (Atomic spend limits, user budget clamping).
4. 24-Hour Idempotency Replay Defense (Zero double-charge guarantee).
5. Privacy-Preserving Masked PII Audit Ledger verification.
"""
import uuid
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from src.infrastructure.server import create_application
from src.domain.exceptions import SpendCapExceededError, OutOfStockError


def run_e2e_suite():
    print("=" * 80)
    print("🚀 STARTING UNIVERSAL AGENTIC COMMERCE NODE E2E TEST SUITE")
    print("=" * 80)

    app = create_application()
    client = TestClient(app)

    # -------------------------------------------------------------------------
    # TEST 1: Health & Discovery Endpoints
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Verifying System Health & Protocol Registrations...")
    resp = client.get("/healthz")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    health_data = resp.json()
    assert health_data["status"] == "healthy"
    assert "MCP/SSE" in health_data["protocols"]
    assert "UAP/A2A" in health_data["protocols"]
    print("  ✅ Health check passed. Dual protocols online.")

    # -------------------------------------------------------------------------
    # TEST 2: MCP Tool Discovery & Catalog Search
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Simulating Tool-Calling Agent: Catalog Search & Discovery...")
    tools_resp = client.get("/mcp/tools")
    assert tools_resp.status_code == 200
    tools = tools_resp.json()["tools"]
    tool_names = [t["name"] for t in tools]
    assert "search_store_catalog" in tool_names
    assert "request_price_quote" in tool_names
    assert "execute_bounded_checkout" in tool_names
    assert "inspect_audit_trail" in tool_names
    print(f"  ✅ Discovered {len(tools)} MCP tools: {', '.join(tool_names)}")

    # Call search tool via direct MCP controller
    mcp_ctrl = app.state.mcp_controller
    search_res = mcp_ctrl.search_store_catalog(query="Pizza", merchant_id="dominos_in")
    assert search_res["success"] is True
    assert len(search_res["products"]) >= 2
    print(f"  ✅ Catalog search returned {len(search_res['products'])} pizza products.")

    # Multi-merchant search check (BeastLife & Havells)
    beast_res = mcp_ctrl.search_store_catalog(query="Protein", merchant_id="beastlife_d2c")
    assert beast_res["success"] is True
    assert len(beast_res["products"]) >= 1
    print(f"  ✅ Multi-merchant catalog check passed: Found BeastLife '{beast_res['products'][0]['title']}'.")

    # -------------------------------------------------------------------------
    # TEST 3: Deterministic Discount Clamping Verification
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Verifying Deterministic Discount Clamping Guardrails...")
    # Domino's Farmhouse pizza price is ₹459.00 with max 15% discount.
    # Agent requests an aggressive 50% discount.
    quote_req = {
        "items": [
            {"product_id": "DOM-PIZ-001", "quantity": 2, "requested_discount_pct": 50.0}
        ],
        "merchant_id": "dominos_in",
    }
    quote_res = mcp_ctrl.request_price_quote(**quote_req)
    assert quote_res["success"] is True
    quote = quote_res["quote"]

    original_price = 459.0 * 2  # 918.0
    expected_clamped_discount_pct = 15.0  # Clamped from 50% to 15%
    expected_discount = round(original_price * (expected_clamped_discount_pct / 100.0), 2)  # 137.70
    expected_final = round(original_price - expected_discount, 2)  # 780.30

    assert quote["total_original_price"] == original_price
    assert quote["items"][0]["effective_discount_pct"] == 15.0
    assert quote["final_total_price"] == expected_final
    assert len(quote["clamped_discount_reasons"]) > 0
    print(
        f"  ✅ Clamping passed: Requested 50.0% was deterministically clamped to "
        f"{quote['items'][0]['effective_discount_pct']}% (Saved ₹{quote['total_discount_amount']:.2f}, Final: ₹{quote['final_total_price']:.2f})."
    )

    # -------------------------------------------------------------------------
    # TEST 4: Zero-Trust Spend Cap Gatekeeper Rejection
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Verifying Zero-Trust Spend Cap Enforcement (Rejection Case)...")
    # Quote total is ₹780.30, but buyer agent only authorized ₹500.00
    underfunded_key = f"idemp_{uuid.uuid4().hex[:10]}"
    reject_res = mcp_ctrl.execute_bounded_checkout(
        quote_id=quote["quote_id"],
        idempotency_key=underfunded_key,
        user_id="agent_claude_desktop_001",
        max_spend_budget=500.0,  # Below quote total of 780.30!
        shipping_address={"line1": "123 Tech Park", "city": "Bengaluru", "phone": "9876543210"},
        merchant_id="dominos_in",
    )
    assert reject_res["success"] is False
    assert reject_res["error"]["error_type"] == "SpendCapExceededError"
    print(f"  ✅ Gatekeeper correctly blocked under-budget transaction: {reject_res['error']['message']}")

    # -------------------------------------------------------------------------
    # TEST 5: Cart Downsizing & Successful Razorpay Checkout
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Cart Downsizing & Validated Bounded Checkout...")
    # Downsize cart to 1 Pizza (₹459 - 15% = ₹390.15), within ₹500 budget
    downsized_quote = mcp_ctrl.request_price_quote(
        items=[{"product_id": "DOM-PIZ-001", "quantity": 1}],
        requested_discount=15.0,
        merchant_id="dominos_in",
    )["quote"]

    valid_idemp_key = f"idemp_{uuid.uuid4().hex[:12]}"
    checkout_res = mcp_ctrl.execute_bounded_checkout(
        quote_id=downsized_quote["quote_id"],
        idempotency_key=valid_idemp_key,
        user_id="agent_claude_desktop_001",
        max_spend_budget=500.0,
        shipping_address={
            "line1": "Flat 402, Sunshine Apartments, Indiranagar",
            "city": "Bengaluru",
            "state": "KA",
            "postal_code": "560038",
            "phone": "+919876543210",
            "email": "buyer.agent@example.com",
        },
        merchant_id="dominos_in",
    )

    assert checkout_res["success"] is True, f"Checkout failed: {checkout_res}"
    order = checkout_res["order"]
    assert order["final_amount"] == downsized_quote["final_total_price"]
    assert order["payment_status"] == "created"
    assert "razorpay.com" in order["payment_link"]
    assert order["is_replayed"] is False
    print(f"  ✅ Checkout successful. Order ID: {order['order_id']}, Razorpay Rail: {order['payment_rail_id']}")

    # -------------------------------------------------------------------------
    # TEST 6: 24-Hour Idempotency Replay Defense
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing 24-Hour Idempotency Replay Defense...")
    # Replay identical checkout with same idempotency key
    replay_res = mcp_ctrl.execute_bounded_checkout(
        quote_id=downsized_quote["quote_id"],
        idempotency_key=valid_idemp_key,  # SAME KEY
        user_id="agent_claude_desktop_001",
        max_spend_budget=500.0,
        shipping_address={"line1": "Flat 402", "city": "Bengaluru"},
        merchant_id="dominos_in",
    )
    assert replay_res["success"] is True
    assert replay_res["order"]["is_replayed"] is True
    assert replay_res["order"]["order_id"] == order["order_id"]
    print(f"  ✅ Replay defense verified: Returned existing order {order['order_id']} without double charging.")

    # -------------------------------------------------------------------------
    # TEST 7: UAP / A2A Protocol Flow (Handshake, Negotiate, Transact)
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing Universal Agent Protocol (UAP / A2A Peer-to-Peer)...")
    # 1. Discovery /.well-known/agent.json
    agent_card_resp = client.get("/.well-known/agent.json")
    assert agent_card_resp.status_code == 200
    agent_card = agent_card_resp.json()
    assert agent_card["protocol_version"] == "uap/v1"
    assert "intent_negotiation" in agent_card["capabilities"]
    print(f"  ✅ UAP Agent Card discovered: {agent_card['name']}")

    # 2. Negotiate Intent
    negotiate_payload = {
        "buyer_agent_id": "buyer_swarm_peer_88",
        "intent_summary": "Looking for Garlic Breadsticks and Choco Lava Cake",
        "target_skus_or_ids": ["DOM-SD-001", "DOM-DS-001"],
        "buyer_max_budget": 300.0,
        "merchant_id": "dominos_in",
    }
    neg_resp = client.post("/uap/v1/negotiate", json=negotiate_payload)
    assert neg_resp.status_code == 200, f"Negotiation failed: {neg_resp.text}"
    negotiation = neg_resp.json()
    assert negotiation["status"] == "OFFERED"
    assert negotiation["within_budget"] is True
    negotiated_quote = negotiation["quote"]
    print(f"  ✅ UAP Negotiation completed: {negotiation['counter_offer_notes']}")

    # 3. Transact Settlement
    uap_idemp_key = f"uap_tx_{uuid.uuid4().hex[:12]}"
    transact_payload = {
        "buyer_agent_id": "buyer_swarm_peer_88",
        "quote_id": negotiated_quote["quote_id"],
        "idempotency_key": uap_idemp_key,
        "authorized_spend_limit": 300.0,
        "shipping_address": {
            "line1": "Building 5, Cyber City",
            "city": "Gurugram",
            "state": "HR",
            "postal_code": "122002",
            "country": "IN",
            "phone": "+919811122233",
            "email": "procurement.agent@corp.ai",
        },
        "merchant_id": "dominos_in",
    }
    tx_resp = client.post("/uap/v1/transact", json=transact_payload)
    assert tx_resp.status_code == 200, f"Transact failed: {tx_resp.text}"
    transact_res = tx_resp.json()
    assert transact_res["status"] == "SETTLED"
    assert transact_res["amount_settled"] == negotiated_quote["final_total_price"]
    print(f"  ✅ UAP Transact settled on Razorpay: Order {transact_res['order_id']}, Amount: ₹{transact_res['amount_settled']:.2f}")

    # -------------------------------------------------------------------------
    # TEST 8: Privacy-Preserving Masked PII Audit Ledger Verification
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Verifying Privacy-Preserving Masked PII Audit Ledger...")
    audit_res = mcp_ctrl.inspect_audit_trail(merchant_id="dominos_in", limit=10)
    assert audit_res["success"] is True
    entries = audit_res["entries"]
    assert len(entries) >= 3

    # Check for raw PII leakage
    for entry in entries:
        payload_str = str(entry["masked_pii_payload"])
        # Verify plain phone / email is NOT in payload
        assert "9876543210" not in payload_str or "+91-XXXXX-3210" in payload_str
        assert "buyer.agent@example.com" not in payload_str or "bu***@example.com" in payload_str
        # Verify user hash is 16-char SHA256 substring, not plain text
        if entry["user_id_hash"] != "anonymous_agent":
            assert len(entry["user_id_hash"]) == 16
    print(f"  ✅ Audit ledger verified: {len(entries)} entries logged with privacy-safe masked PII.")

    print("\n" + "=" * 80)
    print("🎉 ALL E2E INTEGRATION & PROTOCOL TESTS PASSED PERFECTLY!")
    print("=" * 80)


def test_e2e_flow():
    """Pytest entrypoint."""
    run_e2e_suite()


if __name__ == "__main__":
    run_e2e_suite()
