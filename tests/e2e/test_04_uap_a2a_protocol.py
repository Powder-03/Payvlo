"""E2E Test 7: Universal Agent Protocol (UAP / A2A) Flow."""
import uuid


def run_test(client, app):
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
