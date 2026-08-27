"""Autonomous AI Buyer Agent Simulator (A2A / UAP Protocol Tester).

Location: tests/test_ai_buyer_agent.py
Simulates an external autonomous buyer agent (e.g. Claude Desktop, AutoGPT, or Custom AI Agent)
interacting machine-to-machine with Payvlo's Universal Agent Protocol (UAP / A2A).
"""
import sys
import os
import json
import uuid
import time
import requests

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from src.infrastructure.server import app
from tests.seed_test_data import seed_test_environment

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log_agent(step: str, title: str, details: dict):
    print(f"\n{BOLD}{CYAN}🤖 [AI BUYER AGENT] {step}: {title}{RESET}")
    for k, v in details.items():
        print(f"   {YELLOW}• {k}:{RESET} {v}")


def log_node(title: str, details: dict):
    print(f"{BOLD}{GREEN}⚡ [PAYVLO GATEWAY] {title}{RESET}")
    for k, v in details.items():
        print(f"   {MAGENTA}• {k}:{RESET} {v}")


def run_a2a_agent_simulation():
    print("=" * 80)
    print(f"{BOLD}{CYAN}🚀 STARTING AUTONOMOUS AI-TO-AI (A2A / UAP) COMMERCE SIMULATION{RESET}")
    print("=" * 80)

    # 0. Ensure environment is seeded
    seed_test_environment()
    client = TestClient(app)

    target_merchant = "dominos_in"
    buyer_agent_id = "ai_buyer_agent_nexus_01"

    # =========================================================================
    # PHASE 1: Autonomous Agent Discovery
    # =========================================================================
    log_agent(
        "PHASE 1",
        "Discovering Machine Capability Card",
        {"Target Merchant": target_merchant, "Protocol": "UAP / A2A", "Discovery URL": f"/.well-known/agent.json?merchant_id={target_merchant}"}
    )

    card_res = client.get(f"/.well-known/agent.json?merchant_id={target_merchant}")
    assert card_res.status_code == 200, f"Discovery failed: {card_res.text}"
    card = card_res.json()

    log_node(
        "Machine Capability Card Delivered",
        {
            "Merchant Name": card["name"],
            "Category": card["category"],
            "Max Discount Ceiling": f"{card['pricing_guardrails']['max_discount_percentage']}%",
            "Max Spend Cap": f"{card['pricing_guardrails']['currency']} {card['pricing_guardrails']['per_tx_spend_cap']}",
            "Supported Rails": ", ".join(card["supported_payment_rails"]),
            "Negotiate Endpoint": card["endpoints"]["negotiate"],
            "Transact Endpoint": card["endpoints"]["transact"],
        }
    )

    # =========================================================================
    # PHASE 2: Multi-Turn Intent & Discount Negotiation (Successful Case)
    # =========================================================================
    buyer_intent = "Order 2 Farmhouse Veg Pizzas and 1 Garlic Bread with maximum allowable discount"
    buyer_budget = 1500.0

    log_agent(
        "PHASE 2",
        "Negotiating Intent & Pricing Constraints",
        {
            "Buyer Agent": buyer_agent_id,
            "Intent": buyer_intent,
            "Target SKUs": ["DOM-PIZ-001", "DOM-SD-001"],
            "Buyer Max Budget": f"₹{buyer_budget}",
        }
    )

    negotiate_payload = {
        "buyer_agent_id": buyer_agent_id,
        "intent_summary": buyer_intent,
        "target_skus_or_ids": ["DOM-PIZ-001", "DOM-SD-001"],
        "items": [
            {"product_id": "DOM-PIZ-001", "quantity": 2},
            {"product_id": "DOM-SD-001", "quantity": 1},
        ],
        "buyer_max_budget": buyer_budget,
        "merchant_id": target_merchant,
    }

    neg_res = client.post("/uap/v1/negotiate", json=negotiate_payload)
    assert neg_res.status_code == 200, f"Negotiation failed: {neg_res.text}"
    neg_data = neg_res.json()

    quote = neg_data["quote"]
    log_node(
        f"Negotiation Status: {neg_data['status']}",
        {
            "Within Budget": neg_data["within_budget"],
            "Original Total": f"₹{quote['total_original_price']}",
            "Discount Saved": f"₹{quote['total_discount_amount']}",
            "Final Negotiated Price": f"₹{quote['final_total_price']}",
            "Quote ID": quote["quote_id"],
            "Quote Validity": f"Valid for {quote.get('validity_minutes', 15)} minutes (expires at {quote['expires_at']})",
            "Notes": neg_data["counter_offer_notes"],
        }
    )
    assert neg_data["status"] == "OFFERED"
    assert neg_data["within_budget"] is True
    assert quote["final_total_price"] <= buyer_budget

    # =========================================================================
    # PHASE 3: Cryptographic Transact & Bounded Settlement
    # =========================================================================
    idempotency_key = f"a2a_order_{uuid.uuid4().hex[:12]}"
    agent_sig = f"sig_ed25519_{uuid.uuid4().hex[:24]}"

    log_agent(
        "PHASE 3",
        "Executing Cryptographic Transaction & Settlement",
        {
            "Idempotency Key": idempotency_key,
            "Quote ID": quote["quote_id"],
            "Authorized Spend Ceiling": f"₹{quote['final_total_price']}",
            "Agent Digital Signature": agent_sig,
        }
    )

    transact_payload = {
        "buyer_agent_id": buyer_agent_id,
        "quote_id": quote["quote_id"],
        "idempotency_key": idempotency_key,
        "authorized_spend_limit": quote["final_total_price"],
        "agent_signature": agent_sig,
        "merchant_id": target_merchant,
        "shipping_address": {
            "recipient_name": "Rishabh AI Autonomous Delivery",
            "line1": "Tech Hub Block 4, Indiranagar",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postal_code": "560038",
            "country": "IN",
            "phone": "+91-9876543210",
        },
    }

    tx_res = client.post("/uap/v1/transact", json=transact_payload)
    assert tx_res.status_code == 200, f"Transact failed: {tx_res.text}"
    tx_data = tx_res.json()

    log_node(
        f"Settlement Status: {tx_data['status']}",
        {
            "Order ID": tx_data["order_id"],
            "Settled Amount": f"{tx_data['currency']} {tx_data['amount_settled']}",
            "Razorpay Order ID": tx_data["razorpay_order_id"],
            "Payment / Checkout Link": tx_data["payment_link"],
            "Audit Trail ID": tx_data["audit_id"],
            "Message": tx_data["message"],
        }
    )
    assert tx_data["status"] == "SETTLED"
    assert tx_data["amount_settled"] == quote["final_total_price"]

    # =========================================================================
    # PHASE 4: 24-Hour Idempotency Replay Defense Check
    # =========================================================================
    log_agent(
        "PHASE 4",
        "Testing Idempotency Replay Defense (Duplicate Checkout Attempt)",
        {"Replayed Key": idempotency_key}
    )

    replay_res = client.post("/uap/v1/transact", json=transact_payload)
    assert replay_res.status_code == 200
    replay_data = replay_res.json()

    log_node(
        f"Replay Handled Safely: {replay_data['status']}",
        {
            "Existing Order ID": replay_data["order_id"],
            "Amount": f"₹{replay_data['amount_settled']}",
            "Defense Reason": "Returned existing processed order with ZERO duplicate charge.",
        }
    )
    assert replay_data["order_id"] == tx_data["order_id"]

    # =========================================================================
    # PHASE 5: Budget-Exceeded / Policy Rejection Test
    # =========================================================================
    log_agent(
        "PHASE 5",
        "Testing Negotiation Guardrail (Budget Underflow Rejection)",
        {"Intent": "2 Pizzas with impossible low budget", "Budget": "₹100"}
    )

    low_budget_payload = {
        "buyer_agent_id": buyer_agent_id,
        "intent_summary": "2 Pizzas with only 100 rupees budget",
        "items": [{"product_id": "DOM-PIZ-001", "quantity": 2}],
        "buyer_max_budget": 100.0,
        "merchant_id": target_merchant,
    }
    low_res = client.post("/uap/v1/negotiate", json=low_budget_payload)
    assert low_res.status_code == 200
    low_data = low_res.json()

    log_node(
        f"Negotiation Status: {low_data['status']}",
        {
            "Within Budget": low_data["within_budget"],
            "Requires Approval": low_data["requires_approval"],
            "Counter Notes": low_data["counter_offer_notes"],
        }
    )
    assert low_data["status"] == "COUNTER_OFFER"
    assert low_data["within_budget"] is False

    print("\n" + "=" * 80)
    print(f"{BOLD}{GREEN}🎉 ALL A2A / UAP AUTONOMOUS BUYER AGENT TESTS PASSED SUCCESSFULLY!{RESET}")
    print("=" * 80)


if __name__ == "__main__":
    run_a2a_agent_simulation()
