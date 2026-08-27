"""E2E Test 3: Deterministic Discount Clamping Verification."""


def run_test(client, app):
    print("\n[TEST 3] Verifying Deterministic Discount Clamping Guardrails...")
    mcp_ctrl = app.state.mcp_controller

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
    return quote
