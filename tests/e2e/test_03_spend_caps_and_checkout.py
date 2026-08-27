"""E2E Test 4, 5, 6: Spend Cap Rejection, Bounded Checkout & Idempotency Replay."""
import uuid


def run_test(client, app, quote):
    print("\n[TEST 4] Verifying Zero-Trust Spend Cap Enforcement (Rejection Case)...")
    mcp_ctrl = app.state.mcp_controller

    underfunded_key = f"idemp_{uuid.uuid4().hex[:10]}"
    reject_res = mcp_ctrl.execute_bounded_checkout(
        quote_id=quote["quote_id"],
        idempotency_key=underfunded_key,
        user_id="agent_claude_desktop_001",
        max_spend_budget=500.0,
        shipping_address={"line1": "123 Tech Park", "city": "Bengaluru", "phone": "9876543210"},
        merchant_id="dominos_in",
    )
    assert reject_res["success"] is False
    assert reject_res["error"]["error_type"] == "SpendCapExceededError"
    print(f"  ✅ Gatekeeper correctly blocked under-budget transaction: {reject_res['error']['message']}")

    print("\n[TEST 5] Cart Downsizing & Validated Bounded Checkout...")
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

    print("\n[TEST 6] Testing 24-Hour Idempotency Replay Defense...")
    replay_res = mcp_ctrl.execute_bounded_checkout(
        quote_id=downsized_quote["quote_id"],
        idempotency_key=valid_idemp_key,
        user_id="agent_claude_desktop_001",
        max_spend_budget=500.0,
        shipping_address={"line1": "Flat 402", "city": "Bengaluru"},
        merchant_id="dominos_in",
    )
    assert replay_res["success"] is True
    assert replay_res["order"]["is_replayed"] is True
    assert replay_res["order"]["order_id"] == order["order_id"]
    print(f"  ✅ Replay defense verified: Returned existing order {order['order_id']} without double charging.")
    return order
