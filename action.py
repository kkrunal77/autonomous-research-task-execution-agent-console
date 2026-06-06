"""
action.py — Action Layer (MCP stdio tool executor).

Spawns mcp_server.py as a child process over stdio JSON-RPC and
sends tool calls in MCP protocol format.

Supported tools (from mcp_server.py):
    web_search(query, max_results=5)
    fetch_url(url, timeout=20)
    get_time(timezone="UTC")
    currency_convert(amount, from_currency, to_currency)
    read_file(path)
    list_dir(path)
    create_file(path, content)
    update_file(path, content)
    edit_file(path, find, replace, replace_all=False)
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

from schemas import ToolResult

ROOT = Path(__file__).parent
MCP_SERVER = ROOT / "mcp_server.py"

# ── MCP JSON-RPC message IDs ──────────────────────
_id_counter = 0
_id_lock = threading.Lock()


def _next_id() -> int:
    global _id_counter
    with _id_lock:
        _id_counter += 1
        return _id_counter


# ─────────────────────────────────────────────────
# Low-level MCP stdio client
# ─────────────────────────────────────────────────

class MCPClient:
    """Persistent subprocess-based MCP stdio client."""

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._initialized = False

    def _start(self):
        if self._proc and self._proc.poll() is None:
            return  # already running
        self._proc = subprocess.Popen(
            [sys.executable, str(MCP_SERVER)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # suppress MCP server logs from our stdout
            text=True,
            bufsize=1,
        )
        self._initialized = False
        self._handshake()

    def _send(self, message: dict) -> None:
        line = json.dumps(message) + "\n"
        self._proc.stdin.write(line)
        self._proc.stdin.flush()

    def _recv(self) -> dict:
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server closed stdout unexpectedly")
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue  # skip non-JSON lines

    def _handshake(self):
        """MCP initialize + initialized notification."""
        msg_id = _next_id()
        self._send({
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "agent7", "version": "1.0"},
            },
        })
        resp = self._recv()
        if "error" in resp:
            raise RuntimeError(f"MCP initialize failed: {resp['error']}")

        # Send initialized notification (no response expected)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        self._initialized = True

    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool and return the parsed result."""
        self._start()
        msg_id = _next_id()
        self._send({
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        })
        # Read responses until we get ours (skip any notifications)
        deadline = time.time() + 120
        while time.time() < deadline:
            resp = self._recv()
            if resp.get("id") == msg_id:
                if "error" in resp:
                    raise RuntimeError(f"Tool error: {resp['error']}")
                result = resp.get("result", {})
                content = result.get("content", [])
                if isinstance(content, list):
                    parsed_blocks = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "")
                            try:
                                parsed_blocks.append(json.loads(text))
                            except json.JSONDecodeError:
                                parsed_blocks.append(text)
                    if len(parsed_blocks) == 1:
                        return parsed_blocks[0]
                    return parsed_blocks
                return content
        raise TimeoutError(f"Timed out waiting for tool '{tool_name}' response")

    def close(self):
        if self._proc:
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()

    def __enter__(self):
        self._start()
        return self

    def __exit__(self, *_):
        self.close()


# Singleton MCP client reused across the agent loop
_mcp_client: Optional[MCPClient] = None


def _get_client() -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
        _mcp_client._start()
    return _mcp_client


def shutdown_mcp():
    global _mcp_client
    if _mcp_client:
        _mcp_client.close()
        _mcp_client = None


# ─────────────────────────────────────────────────
# High-level action executor
# ─────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_args: dict) -> ToolResult:
    """Execute an MCP tool and return a validated ToolResult."""
    try:
        client = _get_client()
        raw = client.call_tool(tool_name, tool_args)

        # Convert raw result to human-readable content string
        if tool_name == "web_search" and isinstance(raw, dict):
            raw = [raw]

        if isinstance(raw, list):
            parts = []
            for item in raw:
                if isinstance(item, dict):
                    if tool_name == "web_search":
                        title   = item.get("title", "")
                        url     = item.get("url", "")
                        snippet = item.get("snippet", "")
                        parts.append(f"**{title}**\n{url}\n{snippet}")
                    elif tool_name == "retrieve_context":
                        file_name = item.get("file_name", "")
                        content_str = item.get("content", "")
                        score = item.get("score") or item.get("kw_score", "")
                        parts.append(f"**{file_name}** (relevance/score: {score})\n{content_str}")
                    elif tool_name == "search_knowledge":
                        key = item.get("key", "")
                        value = item.get("value", "")
                        parts.append(f"**{key}**\n{json.dumps(value) if isinstance(value, dict) else str(value)}")
                    else:
                        parts.append(json.dumps(item, indent=2))
                else:
                    parts.append(str(item))
            content = "\n\n".join(parts)
        elif isinstance(raw, dict):
            # fetch_url returns {status, content_type, length_bytes, text}
            if "text" in raw:
                content = raw["text"][:30000]  # cap at 30K chars
            else:
                content = json.dumps(raw, indent=2)
        else:
            content = str(raw)

        return ToolResult(success=True, content=content, tool_name=tool_name)

    except Exception as exc:
        error_msg = str(exc)
        print(f"[Action] Tool '{tool_name}' failed: {error_msg}", file=sys.stderr)
        return ToolResult(
            success=False,
            content="",
            tool_name=tool_name,
            error=error_msg,
        )


# ─────────────────────────────────────────────────
# Convenience wrappers (also used by tools/ layer)
# ─────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> ToolResult:
    return execute_tool("web_search", {"query": query, "max_results": max_results})


def fetch_url(url: str, timeout: int = 20) -> ToolResult:
    return execute_tool("fetch_url", {"url": url, "timeout": timeout})


def get_time(timezone: str = "UTC") -> ToolResult:
    return execute_tool("get_time", {"timezone": timezone})


def currency_convert(amount: float, from_currency: str, to_currency: str) -> ToolResult:
    return execute_tool("currency_convert", {
        "amount": amount,
        "from_currency": from_currency,
        "to_currency": to_currency,
    })


def list_tools() -> list[dict]:
    """List available MCP tools from the server."""
    try:
        client = _get_client()
        msg_id = _next_id()
        client._send({
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": "tools/list",
            "params": {}
        })
        deadline = time.time() + 10
        while time.time() < deadline:
            resp = client._recv()
            if resp.get("id") == msg_id:
                if "error" in resp:
                    raise RuntimeError(f"List tools error: {resp['error']}")
                result = resp.get("result", {})
                return result.get("tools", [])
    except Exception as exc:
        print(f"[Action] Failed to list tools: {exc}", file=sys.stderr)
    return []


if __name__ == "__main__":
    result = web_search("latest AI news 2025", max_results=3)
    print(result.model_dump_json(indent=2))
    shutdown_mcp()
