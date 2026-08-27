"""E2E Test 8: Privacy-Preserving Masked PII Audit Ledger Verification."""


def run_test(client, app):
    print("\n[TEST 8] Verifying Privacy-Preserving Masked PII Audit Ledger...")
    mcp_ctrl = app.state.mcp_controller
    audit_res = mcp_ctrl.inspect_audit_trail(merchant_id="dominos_in", limit=10)
    assert audit_res["success"] is True
    entries = audit_res["entries"]
    assert len(entries) >= 3

    # Check for raw PII leakage
    for entry in entries:
        payload_str = str(entry["masked_pii_payload"])
        assert "9876543210" not in payload_str or "+91-XXXXX-3210" in payload_str
        assert "buyer.agent@example.com" not in payload_str or "bu***@example.com" in payload_str
        if entry["user_id_hash"] != "anonymous_agent":
            assert len(entry["user_id_hash"]) == 16
    print(f"  ✅ Audit ledger verified: {len(entries)} entries logged with privacy-safe masked PII.")
