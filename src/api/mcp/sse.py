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
from ...services.auth_service import decode_access_token
from .tools import execute_tool_call

logger = logging.getLogger("MCPSSETransport")
router = APIRouter(tags=["MCP Interface"])

sse_sessions: Dict[str, asyncio.Queue] = {}
sse_user_sessions: Dict[str, Dict[str, Any]] = {}
streamable_http_sessions: Dict[str, Dict[str, Any]] = {}


def process_rpc_message(app, body: Dict[str, Any], user_id: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], int]:
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
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": {
                    "name": f"Payvlo Commerce Gateway ({merchant_name})",
                    "version": "1.0.0",
                },
            },
        }, 200

    elif method == "notifications/initialized" or (method and method.startswith("notifications/")):
        # Notifications MUST NOT receive a response per JSON-RPC 2.0
        return None, 202

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": get_mcp_tool_definitions()},
        }, 200

    elif method == "prompts/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"prompts": []},
        }, 200

    elif method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"resources": []},
        }, 200

    elif method == "resources/templates/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"resourceTemplates": []},
        }, 200

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        if user_id and not arguments.get("user_id"):
            arguments["user_id"] = user_id
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

    # If it's a notification without id, ignore gracefully
    if msg_id is None:
        return None, 202

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method '{method}' not found"},
    }, 200


@router.options("/sse")
@router.options("/messages")
async def mcp_cors_preflight():
    """CORS preflight for web/desktop based MCP clients."""
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Expose-Headers": "Mcp-Session-Id",
        },
    )


@router.get("/sse")
async def sse_endpoint(request: Request):
    """Official FastMCP SSE Transport endpoint with Bearer token authentication."""
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    token = request.query_params.get("token") or request.query_params.get("api_key")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()

    session_user: Dict[str, Any] = {}
    if token:
        payload = decode_access_token(token)
        if payload:
            session_user = {
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "role": payload.get("role"),
            }

    session_id = uuid.uuid4().hex
    queue: asyncio.Queue = asyncio.Queue()
    sse_sessions[session_id] = queue
    if session_user:
        sse_user_sessions[session_id] = session_user

    # Resolve absolute URL for strict MCP SDK clients (handles Cloudflare/Render reverse proxies)
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    base_url = f"{proto}://{host}".rstrip("/")
    endpoint_url = f"{base_url}/messages?sessionId={session_id}"

    async def event_generator():
        try:
            # 1. Emit endpoint URL where client must POST messages
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
            sse_user_sessions.pop(session_id, None)

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


@router.post("/sse")
async def streamable_http_endpoint(request: Request):
    """MCP Streamable HTTP Transport – accepts POST JSON-RPC 2.0 messages directly.

    This allows modern MCP clients (Antigravity, etc.) that use the `serverUrl`
    config key to communicate without establishing an SSE session first.
    """
    # ── Auth ──────────────────────────────────────────────────────────────
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    token = request.query_params.get("token") or request.query_params.get("api_key")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()

    user_id: Optional[str] = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub")

    # ── Parse body ────────────────────────────────────────────────────────
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
        )

    # ── Session management ────────────────────────────────────────────────
    session_id = request.headers.get("mcp-session-id")

    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Expose-Headers": "Mcp-Session-Id",
    }

    # ── Batch request (array of JSON-RPC messages) ────────────────────────
    if isinstance(body, list):
        responses = []
        for msg in body:
            resp, _ = process_rpc_message(request.app, msg, user_id=user_id)
            if resp is not None:
                responses.append(resp)

        if not session_id:
            session_id = uuid.uuid4().hex
            streamable_http_sessions[session_id] = {"user_id": user_id}

        headers = {**cors_headers, "Mcp-Session-Id": session_id}

        if not responses:
            return Response(status_code=202, headers=headers)
        return JSONResponse(
            content=responses if len(responses) > 1 else responses[0],
            headers=headers,
        )

    # ── Single message ────────────────────────────────────────────────────
    method = body.get("method") if isinstance(body, dict) else None

    if method == "initialize":
        # Reuse the client's session ID if it already exists in our store
        # (handles re-initialization / retries). Otherwise mint a new one.
        if session_id and session_id in streamable_http_sessions:
            streamable_http_sessions[session_id]["user_id"] = user_id
        else:
            session_id = uuid.uuid4().hex
            streamable_http_sessions[session_id] = {"user_id": user_id}
    elif not session_id or session_id not in streamable_http_sessions:
        # Unknown/missing session on a non-init request → create one to be lenient
        session_id = session_id or uuid.uuid4().hex
        streamable_http_sessions[session_id] = {"user_id": user_id}

    response, status_code = process_rpc_message(request.app, body, user_id=user_id)
    headers = {**cors_headers, "Mcp-Session-Id": session_id}

    if response is None:
        return Response(status_code=status_code, headers=headers)

    # If client prefers SSE streaming (non-initialize requests)
    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept and method != "initialize":
        async def single_event():
            yield f"event: message\ndata: {json.dumps(response)}\n\n"
        return StreamingResponse(
            single_event(),
            media_type="text/event-stream",
            headers={**headers, "Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    return JSONResponse(content=response, status_code=status_code, headers=headers)


@router.delete("/sse")
async def streamable_http_session_terminate(request: Request):
    """Terminate a Streamable HTTP session."""
    session_id = request.headers.get("mcp-session-id")
    if session_id and session_id in streamable_http_sessions:
        streamable_http_sessions.pop(session_id, None)
        return Response(status_code=200)
    return Response(status_code=404)


@router.post("/messages")
async def handle_mcp_messages(
    request: Request,
    sessionId: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """Official MCP JSON-RPC 2.0 Message Ingress with automatic session user context."""
    active_session_id = sessionId or session_id or request.query_params.get("sessionId") or request.query_params.get("session_id")
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=400, content="Invalid JSON")

    # If active_session_id was not in query param, check body
    if not active_session_id and isinstance(body, dict):
        active_session_id = body.get("sessionId") or body.get("session_id")

    # Resolve authenticated user from session or header
    user_id = None
    if active_session_id and active_session_id in sse_user_sessions:
        user_id = sse_user_sessions[active_session_id].get("user_id")

    if not user_id:
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        token = request.query_params.get("token") or request.query_params.get("api_key")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        if token:
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub")

    response, status_code = process_rpc_message(request.app, body, user_id=user_id)

    # If connected via active SSE session, stream message back on SSE channel
    if active_session_id and active_session_id in sse_sessions and response:
        await sse_sessions[active_session_id].put(response)
        return Response(
            status_code=202,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )

    # Fallback to direct HTTP JSON response
    if response:
        return JSONResponse(
            content=response,
            status_code=status_code,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )
    return Response(
        status_code=status_code,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )
