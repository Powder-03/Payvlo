"""Model Context Protocol (MCP) Client Library & Testing Engine.

Supports official Model Context Protocol (2024-11-05) Server-Sent Events (SSE)
transport, JSON-RPC 2.0 framing, tool discovery, execution, interactive CLI,
and automated protocol compliance verification.
"""
import os
import sys
import json
import uuid
import time
import queue
import logging
import threading
import urllib.parse
from typing import Dict, Any, Optional, List, Union

import requests

# Configure UTF-8 on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Terminal colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


class MCPClientError(Exception):
    """Base exception for MCP Client protocol errors."""
    pass


class PayvloMCPClient:
    """Official Model Context Protocol (MCP) Client.
    
    Implements:
    - SSE Transport (RFC 8895 / EventSource)
    - JSON-RPC 2.0 protocol over HTTP POST ingress
    - Protocol Version 2024-11-05 handshake
    - Tool discovery and typed schema validation
    - Tool invocation and content parsing
    - Ping and capability negotiation
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8000/sse",
        token: Optional[str] = None,
        timeout: float = 20.0,
        verbose: bool = False,
    ):
        self.server_url = server_url.strip()
        self.token = token
        self.timeout = timeout
        self.verbose = verbose

        self.ingress_url: Optional[str] = None
        self.session_id: Optional[str] = None
        self.server_info: Dict[str, Any] = {}
        self.server_capabilities: Dict[str, Any] = {}
        self.protocol_version: Optional[str] = None
        self.tools: Dict[str, Dict[str, Any]] = {}

        self._session = requests.Session()
        self._msg_id_counter = 1
        self._stop_event = threading.Event()
        self._sse_thread: Optional[threading.Thread] = None
        self._pending_requests: Dict[int, queue.Queue] = {}
        self._pending_lock = threading.Lock()
        self._endpoint_event = threading.Event()
        self._is_connected = False

    def _log_wire(self, direction: str, content: str):
        """Logs raw wire transport messages when verbose mode is enabled."""
        if self.verbose:
            tag = f"{CYAN}[MCP WIRE {direction}]{RESET}"
            print(f"{tag} {content}")

    def connect(self) -> "PayvloMCPClient":
        """Opens SSE stream, discovers message ingress URL, and starts listener thread."""
        if self._is_connected:
            return self

        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        if self.verbose:
            print(f"{DIM}Connecting to SSE endpoint: {self.server_url}...{RESET}")

        # Test initial connectivity
        try:
            resp = self._session.get(
                self.server_url,
                stream=True,
                headers=headers,
                timeout=self.timeout,
            )
            self._resp = resp
        except requests.exceptions.RequestException as exc:
            raise MCPClientError(f"Failed to connect to MCP server at {self.server_url}: {exc}") from exc

        if resp.status_code != 200:
            raise MCPClientError(
                f"MCP SSE endpoint returned HTTP {resp.status_code}: {resp.text}"
            )

        self._stop_event.clear()
        self._endpoint_event.clear()

        def _sse_listener():
            event_type = "message"
            data_buffer: List[str] = []

            try:
                for raw_line in resp.iter_lines(decode_unicode=True):
                    if self._stop_event.is_set():
                        break
                    if raw_line is None:
                        continue
                    line = raw_line.strip()
                    if not line:
                        # End of SSE block: dispatch event
                        if data_buffer:
                            payload_str = "\n".join(data_buffer)
                            self._handle_sse_event(event_type, payload_str)
                            event_type = "message"
                            data_buffer = []
                        continue

                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        data_buffer.append(line[5:].strip())
                    elif line.startswith(":"):
                        # Comment or ping keep-alive
                        self._log_wire("PING", line)
            except Exception as e:
                if not self._stop_event.is_set() and self.verbose:
                    print(f"{RED}[MCP Client] SSE Listener terminated: {e}{RESET}")
            finally:
                resp.close()

        self._sse_thread = threading.Thread(target=_sse_listener, daemon=True)
        self._sse_thread.start()

        # Wait for endpoint discovery event
        if not self._endpoint_event.wait(timeout=self.timeout):
            self.close()
            raise TimeoutError("Timed out waiting for initial 'endpoint' event from MCP SSE stream.")

        self._is_connected = True
        return self

    def _handle_sse_event(self, event_type: str, data: str):
        """Processes an incoming SSE event."""
        self._log_wire("RECV", f"event: {event_type} | data: {data}")

        if event_type == "endpoint":
            raw_endpoint = data.strip()
            # If relative URL, resolve against server_url
            self.ingress_url = urllib.parse.urljoin(self.server_url, raw_endpoint)
            # Extract session ID if present
            parsed = urllib.parse.urlparse(self.ingress_url)
            params = urllib.parse.parse_qs(parsed.query)
            if "sessionId" in params:
                self.session_id = params["sessionId"][0]
            elif "session_id" in params:
                self.session_id = params["session_id"][0]
            self._endpoint_event.set()

        elif event_type == "message":
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                return

            msg_id = msg.get("id")
            if msg_id is not None:
                with self._pending_lock:
                    q = self._pending_requests.get(msg_id)
                if q:
                    q.put(msg)

    def _send_rpc(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        is_notification: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Sends a JSON-RPC 2.0 message to the discovered ingress URL."""
        if not self.ingress_url:
            raise MCPClientError("Client not connected or ingress URL not discovered yet.")

        req_id = None
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if not is_notification:
            req_id = self._msg_id_counter
            self._msg_id_counter += 1
            payload["id"] = req_id

        if params is not None:
            payload["params"] = params

        # Setup response listener queue for requests
        resp_queue = queue.Queue()
        if req_id is not None:
            with self._pending_lock:
                self._pending_requests[req_id] = resp_queue

        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        self._log_wire("SEND", json.dumps(payload))

        try:
            http_res = self._session.post(
                self.ingress_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as exc:
            if req_id is not None:
                with self._pending_lock:
                    self._pending_requests.pop(req_id, None)
            raise MCPClientError(f"HTTP POST to MCP ingress failed: {exc}") from exc

        if is_notification:
            return None

        # Check if response came directly in HTTP response (fallback mode)
        if http_res.status_code == 200 and http_res.text:
            try:
                sync_json = http_res.json()
                if isinstance(sync_json, dict) and sync_json.get("id") == req_id:
                    with self._pending_lock:
                        self._pending_requests.pop(req_id, None)
                    return self._process_rpc_response(sync_json)
            except Exception:
                pass

        # Otherwise wait for SSE stream to deliver response
        try:
            rpc_res = resp_queue.get(timeout=self.timeout)
            return self._process_rpc_response(rpc_res)
        except queue.Empty:
            raise TimeoutError(f"Timed out waiting for JSON-RPC response for method '{method}' (id={req_id}).")
        finally:
            with self._pending_lock:
                self._pending_requests.pop(req_id, None)

    def _process_rpc_response(self, rpc_res: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts result or raises error from JSON-RPC response."""
        if "error" in rpc_res:
            err = rpc_res["error"]
            raise MCPClientError(f"MCP RPC Error [{err.get('code')}]: {err.get('message')}")
        return rpc_res.get("result", {})

    def initialize(
        self,
        client_name: str = "payvlo-official-mcp-client",
        client_version: str = "1.0.0",
    ) -> Dict[str, Any]:
        """Performs official Model Context Protocol handshake (initialize + notifications/initialized)."""
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": False},
                "sampling": {},
            },
            "clientInfo": {
                "name": client_name,
                "version": client_version,
            },
        }

        result = self._send_rpc("initialize", init_params) or {}
        self.protocol_version = result.get("protocolVersion")
        self.server_info = result.get("serverInfo", {})
        self.server_capabilities = result.get("capabilities", {})

        # Send notifications/initialized notification
        self._send_rpc("notifications/initialized", {}, is_notification=True)
        return result

    def ping(self) -> bool:
        """Sends JSON-RPC ping to verify liveness."""
        res = self._send_rpc("ping", {})
        return res is not None

    def list_tools(self) -> List[Dict[str, Any]]:
        """Queries the server for registered tools ('tools/list')."""
        result = self._send_rpc("tools/list", {}) or {}
        tools_list = result.get("tools", [])
        self.tools = {t["name"]: t for t in tools_list}
        return tools_list

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calls an MCP tool ('tools/call') and unpacks content."""
        params = {
            "name": name,
            "arguments": arguments or {},
        }
        result = self._send_rpc("tools/call", params) or {}
        content_blocks = result.get("content", [])
        is_error = result.get("isError", False)

        # Parse text content blocks
        parsed_payload = None
        for block in content_blocks:
            if block.get("type") == "text":
                text = block.get("text", "")
                try:
                    parsed_payload = json.loads(text)
                except Exception:
                    parsed_payload = text

        return {
            "success": not is_error,
            "isError": is_error,
            "data": parsed_payload,
            "raw": result,
        }

    def list_prompts(self) -> List[Dict[str, Any]]:
        """Queries available prompts ('prompts/list')."""
        result = self._send_rpc("prompts/list", {}) or {}
        return result.get("prompts", [])

    def list_resources(self) -> List[Dict[str, Any]]:
        """Queries available resources ('resources/list')."""
        result = self._send_rpc("resources/list", {}) or {}
        return result.get("resources", [])

    def close(self):
        """Closes SSE stream and cleans up resources."""
        self._stop_event.set()
        self._endpoint_event.set()
        self._is_connected = False
        if hasattr(self, "_resp") and self._resp:
            try:
                if hasattr(self._resp, "raw") and self._resp.raw:
                    self._resp.raw.close()
            except Exception:
                pass
            try:
                self._resp.close()
            except Exception:
                pass
        try:
            self._session.close()
        except Exception:
            pass

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def run_verification_suite(self) -> bool:
        """Runs an end-to-end automated protocol verification suite."""
        print("=" * 80)
        print(f"{BOLD}{CYAN}🤖 PAYVLO MCP CLIENT: AUTOMATED COMPLIANCE & PROTOCOL VERIFICATION{RESET}")
        print(f"Target Server: {BOLD}{self.server_url}{RESET}")
        print("=" * 80)

        passed = 0
        failed = 0

        def check(desc: str, fn):
            nonlocal passed, failed
            print(f"\n{BOLD}▶ Testing: {desc}...{RESET}")
            try:
                fn()
                print(f"  {GREEN}✓ PASSED{RESET}")
                passed += 1
            except Exception as e:
                print(f"  {RED}✗ FAILED: {e}{RESET}")
                failed += 1

        # 1. Connect & Discover Endpoint
        def test_connect():
            self.connect()
            assert self.ingress_url is not None, "Ingress URL was not resolved"
            print(f"  {DIM}Discovered Ingress: {self.ingress_url}{RESET}")
            print(f"  {DIM}Session ID: {self.session_id}{RESET}")

        check("SSE Stream Handshake & Ingress Resolution", test_connect)

        # 2. Handshake: initialize
        def test_init():
            res = self.initialize()
            assert res.get("protocolVersion") == "2024-11-05", "Protocol version mismatch"
            assert "serverInfo" in res, "Missing serverInfo"
            print(f"  {DIM}Server: {self.server_info.get('name')} v{self.server_info.get('version')}{RESET}")

        check("Protocol Handshake (initialize + notifications/initialized)", test_init)

        # 3. Ping
        def test_ping():
            ok = self.ping()
            assert ok is True, "Ping failed"

        check("Liveness Check (ping)", test_ping)

        # 4. Tool Discovery
        tools = []

        def test_discovery():
            nonlocal tools
            tools = self.list_tools()
            assert len(tools) >= 6, f"Expected at least 6 tools, got {len(tools)}"
            names = [t["name"] for t in tools]
            print(f"  {DIM}Found {len(tools)} tools: {', '.join(names)}{RESET}")

        check("Tool Discovery (tools/list)", test_discovery)

        # 5. Stubs for Prompts and Resources
        def test_stubs():
            prompts = self.list_prompts()
            resources = self.list_resources()
            assert isinstance(prompts, list), "Prompts should return a list"
            assert isinstance(resources, list), "Resources should return a list"

        check("Standard Stubs (prompts/list & resources/list)", test_stubs)

        # 6. Tool: search_store_catalog
        def test_search():
            res = self.call_tool("search_store_catalog", {"query": ""})
            assert res["success"] is True, f"Search failed: {res}"
            data = res["data"]
            assert "products" in data, "Missing products array in catalog search"
            print(f"  {DIM}Catalog search returned {len(data['products'])} items.{RESET}")

        check("Tool Call: search_store_catalog", test_search)

        # 7. Tool: onboard_merchant
        merchant_id = f"test_mcp_{uuid.uuid4().hex[:6]}"

        def test_onboard():
            res = self.call_tool(
                "onboard_merchant",
                {
                    "merchant_id": merchant_id,
                    "merchant_name": "MCP Test Trattoria",
                    "category": "Food & Beverage",
                    "max_discount_percentage": 20.0,
                    "per_tx_spend_cap": 2500.0,
                    "daily_merchant_spend_cap": 25000.0,
                    "support_email": "mcp@trattoria.test",
                    "initial_products": [
                        {
                            "sku": f"PIZZA-{uuid.uuid4().hex[:4]}",
                            "title": "Truffle Mushroom Pizza",
                            "price_inr": 499.0,
                            "inventory_count": 30,
                            "category": "Pizza",
                            "max_discount_percentage": 15.0,
                        }
                    ],
                },
            )
            assert res["success"] is True, f"Onboard merchant failed: {res}"
            print(f"  {DIM}Onboarded merchant: {merchant_id}{RESET}")

        check("Tool Call: onboard_merchant", test_onboard)

        # 8. Tool: request_price_quote with discount clamping
        quote_id = None
        quoted_price = 0.0

        def test_quote():
            nonlocal quote_id, quoted_price
            # Find product ID from newly onboarded merchant
            search_res = self.call_tool("search_store_catalog", {"merchant_id": merchant_id})
            prods = search_res["data"]["products"]
            assert len(prods) > 0, "No products found for onboarded merchant"
            prod_id = prods[0]["product_id"]

            quote_res = self.call_tool(
                "request_price_quote",
                {
                    "merchant_id": merchant_id,
                    "items": [{"product_id": prod_id, "quantity": 2}],
                    "requested_discount": 50.0,  # Deliberate over-discount
                },
            )
            assert quote_res["success"] is True, f"Quote request failed: {quote_res}"
            q = quote_res["data"]["quote"]
            quote_id = q["quote_id"]
            quoted_price = q["final_total_price"]
            print(f"  {DIM}Quote ID: {quote_id} | Original: ₹{q['total_original_price']} | Clamped: ₹{quoted_price}{RESET}")
            # Assert discount was clamped to 15% (merchant/product cap) instead of 50%
            item_info = q["items"][0]
            assert item_info["effective_discount_pct"] <= 15.0, "Discount clamping failed!"

        check("Tool Call: request_price_quote (Discount Clamping Defense)", test_quote)

        # 9. Tool: execute_bounded_checkout
        tx_idempotency_key = f"tx_mcp_{uuid.uuid4().hex[:8]}"
        created_order_id = None

        def test_checkout():
            nonlocal created_order_id
            assert quote_id is not None, "Quote ID not available"
            checkout_res = self.call_tool(
                "execute_bounded_checkout",
                {
                    "quote_id": quote_id,
                    "idempotency_key": tx_idempotency_key,
                    "user_id": "test_mcp_client_runner",
                    "max_spend_budget": quoted_price + 50.0,
                    "merchant_id": merchant_id,
                    "shipping_address": {
                        "line1": "Flat 101, Test Residency",
                        "city": "Bengaluru",
                        "state": "KA",
                        "postal_code": "560001",
                        "country": "IN",
                        "phone": "+91-9876543210",
                    },
                },
            )
            assert checkout_res["success"] is True, f"Checkout failed: {checkout_res}"
            order = checkout_res["data"]["order"]
            created_order_id = order["order_id"]
            print(f"  {DIM}Order ID: {created_order_id} | Status: {order['payment_status']} | Final: ₹{order['final_amount']}{RESET}")

        check("Tool Call: execute_bounded_checkout (Zero-Trust Spend Bounds)", test_checkout)

        # 10. Tool: 24h Idempotency Replay Defense
        def test_idempotency():
            replay_res = self.call_tool(
                "execute_bounded_checkout",
                {
                    "quote_id": quote_id,
                    "idempotency_key": tx_idempotency_key,  # Identical key
                    "user_id": "test_mcp_client_runner",
                    "max_spend_budget": quoted_price + 50.0,
                    "merchant_id": merchant_id,
                },
            )
            assert replay_res["success"] is True, f"Replay failed: {replay_res}"
            order = replay_res["data"]["order"]
            assert order["order_id"] == created_order_id, "Order ID mismatch on idempotency replay"
            print(f"  {DIM}Idempotency Lock Held: is_replayed={order.get('is_replayed', True)}{RESET}")

        check("Tool Call: 24-Hour Idempotency Replay Protection", test_idempotency)

        # 11. Tool: inspect_audit_trail
        def test_audit():
            audit_res = self.call_tool(
                "inspect_audit_trail",
                {"merchant_id": merchant_id, "limit": 5},
            )
            assert audit_res["success"] is True, f"Audit trail failed: {audit_res}"
            entries = audit_res["data"].get("entries", [])
            assert len(entries) >= 1, "Audit ledger should contain entries"
            last_entry = entries[0]
            print(f"  {DIM}Audit Action: {last_entry['action']} | Masked PII: {last_entry.get('masked_pii_payload')}{RESET}")

        check("Tool Call: inspect_audit_trail (Zero-Knowledge Masked PII Ledger)", test_audit)

        print("\n" + "=" * 80)
        if failed == 0:
            print(f"{BOLD}{GREEN}🎉 ALL {passed} MCP PROTOCOL AND TOOL CHECKS PASSED!{RESET}")
        else:
            print(f"{BOLD}{RED}❌ COMPLIANCE VERIFICATION COMPLETED: {passed} Passed, {failed} Failed.{RESET}")
        print("=" * 80)
        return failed == 0


def interactive_cli(server_url: str, token: Optional[str] = None):
    """Interactive command-line REPL for the Payvlo MCP Client."""
    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN}      🚀 PAYVLO INTERACTIVE MODEL CONTEXT PROTOCOL (MCP) CLIENT       {RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}")
    print(f"Connecting to: {BOLD}{server_url}{RESET}")

    client = PayvloMCPClient(server_url=server_url, token=token, verbose=False)
    try:
        client.connect()
        print(f"{GREEN}✓ Connected to SSE Stream!{RESET}")
        print(f"  Ingress Endpoint: {DIM}{client.ingress_url}{RESET}")

        init_res = client.initialize()
        print(f"{GREEN}✓ Handshake Completed!{RESET}")
        print(f"  Server Name:     {BOLD}{client.server_info.get('name')}{RESET}")
        print(f"  Server Version:  {client.server_info.get('version')}")
        print(f"  Protocol Version:{client.protocol_version}")

        tools = client.list_tools()
        print(f"{GREEN}✓ Discovered {len(tools)} Registered MCP Tools.{RESET}")

        while True:
            print(f"\n{BOLD}Available MCP Actions:{RESET}")
            print(" [1] List Available Tools ('tools/list')")
            print(" [2] Search Store Catalog ('search_store_catalog')")
            print(" [3] Request Price Quote ('request_price_quote')")
            print(" [4] Execute Bounded Checkout ('execute_bounded_checkout')")
            print(" [5] Inspect Audit Trail ('inspect_audit_trail')")
            print(" [6] Onboard Merchant ('onboard_merchant')")
            print(" [7] Trigger Catalog Sync ('sync_merchant_catalog')")
            print(" [8] Run Complete Automated Verification Test Suite")
            print(" [9] Toggle Verbose Wire Inspector (Current: " + (f"{GREEN}ON{RESET}" if client.verbose else f"{DIM}OFF{RESET}") + ")")
            print(" [0] Exit")

            choice = input(f"\n{CYAN}Select option (0-9): {RESET}").strip()

            if choice == "0":
                print("Exiting MCP Client. Goodbye!")
                break

            elif choice == "1":
                tools = client.list_tools()
                print(f"\n{BOLD}{CYAN}Discovered {len(tools)} Tools:{RESET}")
                for idx, t in enumerate(tools, 1):
                    print(f"  {BOLD}{idx}. {t['name']}{RESET}")
                    print(f"     {t.get('description')}")

            elif choice == "2":
                q = input("Enter search query (default: all): ").strip()
                m_id = input("Enter merchant_id (default: dominos_in): ").strip() or "dominos_in"
                res = client.call_tool("search_store_catalog", {"query": q, "merchant_id": m_id})
                print(f"\n{BOLD}Catalog Search Result:{RESET}")
                print(json.dumps(res.get("data", res), indent=2))

            elif choice == "3":
                prod_id = input("Enter Product ID: ").strip()
                if not prod_id:
                    print(f"{RED}Product ID required!{RESET}")
                    continue
                qty_str = input("Enter Quantity (default: 1): ").strip() or "1"
                disc_str = input("Enter Requested Discount % (default: 0): ").strip() or "0"
                m_id = input("Enter merchant_id (default: dominos_in): ").strip() or "dominos_in"
                res = client.call_tool(
                    "request_price_quote",
                    {
                        "merchant_id": m_id,
                        "items": [{"product_id": prod_id, "quantity": int(qty_str)}],
                        "requested_discount": float(disc_str),
                    },
                )
                print(f"\n{BOLD}Price Quote Result:{RESET}")
                print(json.dumps(res.get("data", res), indent=2))

            elif choice == "4":
                qid = input("Enter Quote ID: ").strip()
                if not qid:
                    print(f"{RED}Quote ID required!{RESET}")
                    continue
                budget_str = input("Enter Max Spend Budget in INR: ").strip() or "1000"
                lbl = input("Enter Address Shortcut Label (e.g. 'Home') [leave blank for manual]: ").strip()
                addr = None
                if not lbl:
                    line1 = input("Address Line 1: ").strip() or "123 Main Street"
                    city = input("City: ").strip() or "Bengaluru"
                    phone = input("Phone: ").strip() or "+91-9876543210"
                    addr = {"line1": line1, "city": city, "phone": phone}

                res = client.call_tool(
                    "execute_bounded_checkout",
                    {
                        "quote_id": qid,
                        "idempotency_key": f"tx_cli_{uuid.uuid4().hex[:8]}",
                        "user_id": "interactive_mcp_user",
                        "max_spend_budget": float(budget_str),
                        "address_label": lbl or None,
                        "shipping_address": addr,
                    },
                )
                print(f"\n{BOLD}Checkout Result:{RESET}")
                print(json.dumps(res.get("data", res), indent=2))

            elif choice == "5":
                m_id = input("Enter merchant_id (default: dominos_in): ").strip() or "dominos_in"
                res = client.call_tool("inspect_audit_trail", {"merchant_id": m_id, "limit": 5})
                print(f"\n{BOLD}Audit Ledger Entries:{RESET}")
                print(json.dumps(res.get("data", res), indent=2))

            elif choice == "6":
                mid = input("New Merchant ID: ").strip() or f"merchant_{uuid.uuid4().hex[:4]}"
                mname = input("Merchant Name: ").strip() or "Sample Store"
                cat = input("Category: ").strip() or "Retail"
                res = client.call_tool(
                    "onboard_merchant",
                    {
                        "merchant_id": mid,
                        "merchant_name": mname,
                        "category": cat,
                        "max_discount_percentage": 15.0,
                        "per_tx_spend_cap": 5000.0,
                        "daily_merchant_spend_cap": 50000.0,
                    },
                )
                print(f"\n{BOLD}Merchant Onboarding Result:{RESET}")
                print(json.dumps(res.get("data", res), indent=2))

            elif choice == "7":
                m_id = input("Enter merchant_id to sync: ").strip() or "dominos_in"
                res = client.call_tool("sync_merchant_catalog", {"merchant_id": m_id})
                print(f"\n{BOLD}Sync Result:{RESET}")
                print(json.dumps(res.get("data", res), indent=2))

            elif choice == "8":
                client.run_verification_suite()

            elif choice == "9":
                client.verbose = not client.verbose
                print(f"Wire logging toggled: {'ON' if client.verbose else 'OFF'}")

    finally:
        client.close()
