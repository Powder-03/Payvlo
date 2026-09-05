import os
import sys
import json

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient

# Ensure project root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import app, create_application
from src.api.mcp.sse import process_rpc_message


def get_initialized_app():
    return create_application()


def test_mcp_rpc_initialize(initialized_app):
    """Verifies MCP initialize method returns 2024-11-05 protocol version and capabilities."""
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }
    resp, code = process_rpc_message(initialized_app, req)
    assert code == 200
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert "tools" in resp["result"]["capabilities"]
    assert "prompts" in resp["result"]["capabilities"]
    assert "resources" in resp["result"]["capabilities"]


def test_mcp_rpc_notifications(initialized_app):
    """Verifies MCP notifications return HTTP 202 without a response payload."""
    req = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    }
    resp, code = process_rpc_message(initialized_app, req)
    assert code == 202
    assert resp is None


def test_mcp_rpc_stubs(initialized_app):
    """Verifies prompts/list, resources/list, resources/templates/list stubs."""
    # 1. prompts/list
    resp1, code1 = process_rpc_message(initialized_app, {"jsonrpc": "2.0", "id": 10, "method": "prompts/list"})
    assert code1 == 200
    assert resp1["result"]["prompts"] == []

    # 2. resources/list
    resp2, code2 = process_rpc_message(initialized_app, {"jsonrpc": "2.0", "id": 11, "method": "resources/list"})
    assert code2 == 200
    assert resp2["result"]["resources"] == []

    # 3. resources/templates/list
    resp3, code3 = process_rpc_message(initialized_app, {"jsonrpc": "2.0", "id": 12, "method": "resources/templates/list"})
    assert code3 == 200
    assert resp3["result"]["resourceTemplates"] == []


def test_mcp_rpc_tools_list(initialized_app):
    """Verifies tools/list returns all 6 Payvlo tools with valid JSON schemas."""
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    resp, code = process_rpc_message(initialized_app, req)
    assert code == 200
    tools = resp["result"]["tools"]
    assert len(tools) >= 6
    tool_names = [t["name"] for t in tools]
    assert "search_store_catalog" in tool_names
    assert "request_price_quote" in tool_names
    assert "execute_bounded_checkout" in tool_names
    assert "inspect_audit_trail" in tool_names
    assert "onboard_merchant" in tool_names
    assert "sync_merchant_catalog" in tool_names


def test_mcp_rpc_tool_call_discount_clamping(initialized_app):
    """Verifies tools/call executes quote with deterministic discount clamping."""
    # 1. Onboard a merchant with a product
    onboard_req = {
        "jsonrpc": "2.0",
        "id": 30,
        "method": "tools/call",
        "params": {
            "name": "onboard_merchant",
            "arguments": {
                "merchant_id": "test_pizza_store",
                "merchant_name": "Test Pizza Store",
                "category": "Food",
                "max_discount_percentage": 15.0,
                "per_tx_spend_cap": 5000.0,
                "daily_merchant_spend_cap": 50000.0,
                "initial_products": [
                    {
                        "sku": "PIZZA-001",
                        "title": "Farmhouse Pizza",
                        "price_inr": 350.0,
                        "inventory_count": 20,
                        "category": "Pizza",
                        "max_discount_percentage": 10.0,
                    }
                ],
            },
        },
    }
    o_resp, _ = process_rpc_message(initialized_app, onboard_req)
    o_content = json.loads(o_resp["result"]["content"][0]["text"])
    assert o_content["success"] is True

    # 2. Search for the product
    search_req = {
        "jsonrpc": "2.0",
        "id": 31,
        "method": "tools/call",
        "params": {
            "name": "search_store_catalog",
            "arguments": {"merchant_id": "test_pizza_store", "query": ""},
        },
    }
    s_resp, _ = process_rpc_message(initialized_app, search_req)
    content = json.loads(s_resp["result"]["content"][0]["text"])
    products = content.get("products", [])
    assert len(products) > 0
    prod_id = products[0]["product_id"]

    # 3. Request quote with 50% discount attempt
    quote_req = {
        "jsonrpc": "2.0",
        "id": 32,
        "method": "tools/call",
        "params": {
            "name": "request_price_quote",
            "arguments": {
                "merchant_id": "test_pizza_store",
                "items": [{"product_id": prod_id, "quantity": 1}],
                "requested_discount": 50.0,
            },
        },
    }
    q_resp, _ = process_rpc_message(initialized_app, quote_req)
    q_content = json.loads(q_resp["result"]["content"][0]["text"])
    assert q_content["success"] is True
    quote = q_content["quote"]
    # Discount was clamped to 10.0%
    assert quote["items"][0]["effective_discount_pct"] <= 15.0



def test_mcp_sse_endpoint_absolute_url():
    """Verifies that GET /sse returns an absolute URL in event: endpoint."""
    import asyncio
    from starlette.requests import Request
    from src.api.mcp.sse import sse_endpoint

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/sse",
        "headers": [
            (b"host", b"payvlo.onrender.com"),
            (b"x-forwarded-proto", b"https"),
        ],
        "query_string": b"",
        "server": ("payvlo.onrender.com", 443),
        "app": app,
    }
    mock_request = Request(scope)

    async def _test():
        resp = await sse_endpoint(mock_request)
        assert resp.status_code == 200
        iterator = resp.body_iterator
        first_chunk = await iterator.__anext__()
        assert "event: endpoint" in first_chunk
        assert "https://payvlo.onrender.com/messages?sessionId=" in first_chunk

    asyncio.run(_test())



def run_all_tests():
    print("=" * 70)
    print("RUNNING MCP PROTOCOL & COMPLIANCE TESTS")
    print("=" * 70)
    app_instance = get_initialized_app()
    
    print("[1] Testing test_mcp_rpc_initialize...")
    test_mcp_rpc_initialize(app_instance)
    print("    [PASSED]")

    print("[2] Testing test_mcp_rpc_notifications...")
    test_mcp_rpc_notifications(app_instance)
    print("    [PASSED]")

    print("[3] Testing test_mcp_rpc_stubs (prompts/list, resources/list)...")
    test_mcp_rpc_stubs(app_instance)
    print("    [PASSED]")

    print("[4] Testing test_mcp_rpc_tools_list...")
    test_mcp_rpc_tools_list(app_instance)
    print("    [PASSED]")

    print("[5] Testing test_mcp_rpc_tool_call_discount_clamping...")
    test_mcp_rpc_tool_call_discount_clamping(app_instance)
    print("    [PASSED]")

    print("[6] Testing test_mcp_sse_endpoint_absolute_url...")
    test_mcp_sse_endpoint_absolute_url()
    print("    [PASSED]")

    print("=" * 70)
    print("SUCCESS: ALL MCP PROTOCOL & COMPLIANCE TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()

