"""FastMCP Server-Sent Events (SSE) Transport & JSON-RPC 2.0 Router."""
import json
import uuid
import time
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse

from ...schemas.mcp import get_mcp_tool_definitions
from .tools import execute_tool_call

logger = logging.getLogger("MCPSSETransport")
router = APIRouter(tags=["MCP Interface"])

sse_sessions: Dict[str, asyncio.Queue] = {}


def process_rpc_message(app, body: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], int]:
    """Processes incoming JSON-RPC 2.0 message and returns (response_dict, status_code)."""
    msg_id = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}
    merchant_name = getattr(app.state, "active_merchant_name", "Payvlo Commerce Gateway")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": f"Payvlo Commerce Gateway ({merchant_name})",
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
            "result": {"tools": get_mcp_tool_definitions()},
        }, 200

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        tool_res = execute_tool_call(app, tool_name, arguments)
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


@router.get("/sse")
async def sse_endpoint(request: Request):
    """Official FastMCP SSE Transport endpoint. Emits endpoint event and streams JSON-RPC responses."""
    session_id = uuid.uuid4().hex
    queue: asyncio.Queue = asyncio.Queue()
    sse_sessions[session_id] = queue

    async def event_generator():
        try:
            # 1. Emit endpoint URL where client must POST messages
            endpoint_url = f"/messages?sessionId={session_id}"
            yield f"event: endpoint\ndata: {endpoint_url}\n\n"

            # 2. Stream JSON-RPC messages and ping keep-alives
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    yield f": ping {now_str}\n\n"
        finally:
            sse_sessions.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.post("/messages")
async def handle_mcp_messages(request: Request, sessionId: Optional[str] = None):
    """Official MCP JSON-RPC 2.0 Message Ingress."""
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=400, content="Invalid JSON")

    response, status_code = process_rpc_message(request.app, body)

    # If connected via active SSE session, stream message back on SSE channel
    if sessionId and sessionId in sse_sessions and response:
        await sse_sessions[sessionId].put(response)
        return Response(status_code=202)

    # Fallback to direct HTTP JSON response
    if response:
        return JSONResponse(content=response, status_code=status_code)
    return Response(status_code=status_code)
