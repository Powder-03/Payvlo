"""FastMCP Server-Sent Events (SSE) Transport & API Router."""
import json
import uuid
import asyncio
import logging
from typing import Dict, Optional
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse

from ...domain.common.timestamps import current_utc_timestamp
from .tool_executor import MCPToolExecutor
from .rpc_handler import MCPRpcHandler

logger = logging.getLogger("MCPSSETransport")


def create_mcp_router(controller: MCPToolExecutor) -> APIRouter:
    """Builds FastAPI router for MCP SSE transport and JSON-RPC 2.0 endpoints."""
    router = APIRouter(tags=["MCP Interface"])
    sse_sessions: Dict[str, asyncio.Queue] = {}
    rpc_handler = MCPRpcHandler(controller)

    @router.get("/mcp/tools")
    def list_mcp_tools():
        """Lists all registered tools for tool-calling agents."""
        return {
            "node_name": controller.merchant_name,
            "transport": "sse",
            "tools": controller.get_tool_definitions(),
        }

    @router.post("/mcp/call")
    async def call_tool_direct(request: Request):
        """Standard HTTP tool invocation bridge."""
        body = await request.json()
        tool_name = body.get("name") or body.get("tool")
        arguments = body.get("arguments") or body.get("params") or {}
        return rpc_handler.execute_tool(tool_name, arguments)

    @router.get("/sse")
    async def sse_endpoint(request: Request):
        """Official MCP SSE Transport endpoint. Emits endpoint event and streams JSON-RPC responses."""
        session_id = uuid.uuid4().hex
        queue: asyncio.Queue = asyncio.Queue()
        sse_sessions[session_id] = queue

        async def event_generator():
            try:
                # 1. Official MCP Spec: emit endpoint URL where client must POST messages
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
                        yield f": ping {current_utc_timestamp()}\n\n"
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

        response, status_code = rpc_handler.process_rpc_message(body)

        # If connected via active SSE session, stream message back on SSE channel
        if sessionId and sessionId in sse_sessions and response:
            await sse_sessions[sessionId].put(response)
            return Response(status_code=202)

        # Fallback to direct HTTP JSON response
        if response:
            return JSONResponse(content=response, status_code=status_code)
        return Response(status_code=status_code)

    return router
