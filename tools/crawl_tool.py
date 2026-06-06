"""
tools/crawl_tool.py — Convenience wrapper for fetch_url MCP tool.
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action import fetch_url
from schemas import ToolResult


def crawl(url: str, timeout: int = 30) -> ToolResult:
    """Fetch a URL and return clean markdown via crawl4ai."""
    return fetch_url(url, timeout=timeout)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    result = crawl(url)
    print(result.content[:2000])
