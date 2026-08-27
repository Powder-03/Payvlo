"""E2E Test 1 & 2: Health, Discovery & MCP Tool Discovery."""


def run_test(client, app):
    print("\n[TEST 1] Verifying System Health & Protocol Registrations...")
    resp = client.get("/healthz")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    health_data = resp.json()
    assert health_data["status"] == "healthy"
    assert "MCP/SSE" in health_data["protocols"]
    assert "UAP/A2A" in health_data["protocols"]
    print("  ✅ Health check passed. Dual protocols online.")

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

    mcp_ctrl = app.state.mcp_controller
    search_res = mcp_ctrl.search_store_catalog(query="Pizza", merchant_id="dominos_in")
    assert search_res["success"] is True
    assert len(search_res["products"]) >= 2
    print(f"  ✅ Catalog search returned {len(search_res['products'])} pizza products.")

    beast_res = mcp_ctrl.search_store_catalog(query="Protein", merchant_id="beastlife_d2c")
    assert beast_res["success"] is True
    assert len(beast_res["products"]) >= 1
    print(f"  ✅ Multi-merchant catalog check passed: Found BeastLife '{beast_res['products'][0]['title']}'.")
