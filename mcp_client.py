#!/usr/bin/env python3
"""Payvlo Official Model Context Protocol (MCP) Client CLI & Testing Tool.

Usage:
  python mcp_client.py                                 # Launch interactive REPL
  python mcp_client.py --test                          # Run automated protocol verification
  python mcp_client.py --test --url https://payvlo.onrender.com/sse
  python mcp_client.py --list-tools
  python mcp_client.py --call search_store_catalog --args '{"query": "pizza"}'
"""
import sys
import os
import json
import argparse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.client.mcp_client import PayvloMCPClient, interactive_cli


def resolve_default_url() -> str:
    """Attempts to resolve server URL from mcp_config.json or environment."""
    config_paths = [
        os.path.join(os.path.dirname(__file__), ".agents", "mcp_config.json"),
        os.path.expanduser("~/.gemini/config/mcp_config.json"),
    ]
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    url = cfg.get("mcpServers", {}).get("payvlo-commerce", {}).get("serverUrl")
                    if url:
                        return url
            except Exception:
                pass
    return os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")


def main():
    parser = argparse.ArgumentParser(
        description="Official Model Context Protocol (MCP) Client & Verification Tool"
    )
    parser.add_argument(
        "--url",
        default=resolve_default_url(),
        help="MCP SSE Endpoint URL (default: from mcp_config.json or http://localhost:8000/sse)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("MCP_TOKEN"),
        help="Optional JWT Bearer Token for authenticated sessions",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run full automated MCP protocol & tool verification suite",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="Connect, list all registered tools, and exit",
    )
    parser.add_argument(
        "--call",
        metavar="TOOL_NAME",
        help="Invoke a specific MCP tool and exit",
    )
    parser.add_argument(
        "--args",
        default="{}",
        help="JSON string of arguments for --call",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose raw wire transport logging",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=25.0,
        help="Connection and RPC timeout in seconds",
    )

    args = parser.parse_args()

    # Mode 1: Automated Verification
    if args.test:
        client = PayvloMCPClient(
            server_url=args.url,
            token=args.token,
            timeout=args.timeout,
            verbose=args.verbose,
        )
        try:
            success = client.run_verification_suite()
            sys.exit(0 if success else 1)
        finally:
            client.close()

    # Mode 2: Quick List Tools
    elif args.list_tools:
        client = PayvloMCPClient(
            server_url=args.url,
            token=args.token,
            timeout=args.timeout,
            verbose=args.verbose,
        )
        try:
            client.connect()
            client.initialize()
            tools = client.list_tools()
            print(json.dumps(tools, indent=2), flush=True)
            client.close()
            os._exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr, flush=True)
            client.close()
            os._exit(1)

    # Mode 3: Quick Tool Call
    elif args.call:
        client = PayvloMCPClient(
            server_url=args.url,
            token=args.token,
            timeout=args.timeout,
            verbose=args.verbose,
        )
        try:
            client.connect()
            client.initialize()
            parsed_args = json.loads(args.args)
            result = client.call_tool(args.call, parsed_args)
            print(json.dumps(result.get("data", result), indent=2), flush=True)
            client.close()
            os._exit(0 if result["success"] else 1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr, flush=True)
            client.close()
            os._exit(1)

    # Mode 4: Interactive REPL
    else:
        interactive_cli(server_url=args.url, token=args.token)


if __name__ == "__main__":
    main()
