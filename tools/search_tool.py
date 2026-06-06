"""
tools/search_tool.py — Convenience wrapper for web_search MCP tool.
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action import web_search
from schemas import ToolResult


def search(query: str, max_results: int = 5) -> ToolResult:
    """Search the web and return a ToolResult."""
    return web_search(query, max_results=max_results)


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Python asyncio tutorial"
    result = search(q)
    print(result.model_dump_json(indent=2))
