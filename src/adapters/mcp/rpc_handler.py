"""MCP JSON-RPC 2.0 Protocol Handler."""
import json
import logging
from typing import Dict, Any, Optional, Tuple
from .tool_executor import MCPToolExecutor

logger = logging.getLogger("MCPRpcHandler")


class MCPRpcHandler:
    """Dispatches JSON-RPC 2.0 requests according to Model Context Protocol specification."""

    def __init__(self, executor: MCPToolExecutor):
        self.executor = executor
        self.tool_dispatch = {
            "search_store_catalog": executor.search_store_catalog,
            "request_price_quote": executor.request_price_quote,
            "execute_bounded_checkout": executor.execute_bounded_checkout,
            "inspect_audit_trail": executor.inspect_audit_trail,
            "onboard_merchant": executor.onboard_merchant,
            "sync_merchant_catalog": executor.sync_merchant_catalog,
        }

    def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        handler = self.tool_dispatch.get(tool_name)
        if not handler:
            return {
                "success": False,
                "error": {
                    "type": "InvalidTool",
                    "message": f"Tool '{tool_name}' is not recognized.",
                },
            }
        try:
            return handler(**arguments)
        except Exception as ex:
            logger.error(f"Error executing MCP tool {tool_name}: {ex}")
            return {
                "success": False,
                "error": {
                    "type": "ExecutionError",
                    "message": str(ex),
                },
            }

    def process_rpc_message(self, body: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], int]:
        """Processes JSON-RPC 2.0 message and returns (response_dict, status_code)."""
        msg_id = body.get("id")
        method = body.get("method")
        params = body.get("params") or {}

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": f"Payvlo Commerce Gateway ({self.executor.merchant_name})",
                        "version": "1.0.0",
                    },
                },
            }, 200

        elif method == "notifications/initialized":
            return None, 202

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": self.executor.get_tool_definitions()},
            }, 200

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            tool_res = self.execute_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(tool_res, indent=2)}
                    ],
                    "isError": not tool_res.get("success", True),
                },
            }, 200

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}, 200

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"},
        }, 404
