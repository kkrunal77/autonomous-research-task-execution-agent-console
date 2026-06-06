"""
MCP server for EAGV3 Session 6.

Nine tools, stdio transport:
    web_search, fetch_url, get_time, currency_convert,
    read_file, list_dir, create_file, update_file, edit_file

web_search:  Tavily primary, DuckDuckGo fallback. Hard-capped at 5 results.
fetch_url:   crawl4ai only — clean markdown via headless Chromium.
Usage for tavily and duckduckgo is logged to ./usage.json with monthly
rollover and a soft cap of 950/1000 on Tavily.

File tools are sandboxed under ./sandbox/. Run:  python mcp_server.py
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from ddgs import DDGS
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

MAX_SEARCH_RESULTS = 5  # hard cap — Tavily prices per result

import sys
sys.path.append(str(Path(__file__).parent))

load_dotenv(Path(__file__).parent / ".env")

mcp = FastMCP("eagv3-s6-server")

SANDBOX = Path(__file__).parent / "sandbox"
SANDBOX.mkdir(exist_ok=True)

USAGE_PATH = Path(__file__).parent / "usage.json"
MONTHLY_CAP = 950  # leave 50/mo headroom on Tavily
_usage_lock = threading.Lock()


def _safe(path: str) -> Path:
    p = (SANDBOX / path).resolve()
    base = SANDBOX.resolve()
    if p != base and base not in p.parents:
        raise ValueError(f"Path '{path}' escapes the sandbox")
    return p


def _empty_usage(month: str) -> dict:
    return {
        "month": month,
        "tavily": {"count": 0, "errors": 0},
        "duckduckgo": {"count": 0, "errors": 0},
    }


def _load_usage() -> dict:
    month = datetime.now().strftime("%Y-%m")
    if not USAGE_PATH.exists():
        return _empty_usage(month)
    try:
        data = json.loads(USAGE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_usage(month)
    if data.get("month") != month:
        return _empty_usage(month)
    for k in ("tavily", "duckduckgo"):
        data.setdefault(k, {"count": 0, "errors": 0})
    return data


def _save_usage(data: dict) -> None:
    USAGE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _bump(provider: str, field: str = "count") -> None:
    with _usage_lock:
        data = _load_usage()
        data[provider][field] = data[provider].get(field, 0) + 1
        _save_usage(data)


def _under_cap(provider: str) -> bool:
    return _load_usage()[provider]["count"] < MONTHLY_CAP


def _tavily_search(query: str, max_results: int) -> list[dict]:
    from tavily import TavilyClient

    client = TavilyClient(os.environ["TAVILY_API_KEY"])
    resp = client.search(query=query, max_results=max_results, search_depth="advanced")
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        }
        for r in resp.get("results", [])
    ]


async def _ddg_search(query: str, max_results: int) -> list[dict]:
    from bs4 import BeautifulSoup
    import sys
    from urllib.parse import urlparse, parse_qs, quote
    from crawl4ai import AsyncWebCrawler

    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"

    # redirect stdout to avoid crawl4ai logs corrupting MCP JSON-RPC
    saved_fd = os.dup(1)
    os.dup2(2, 1)
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            r = await crawler.arun(url=url)
    finally:
        os.dup2(saved_fd, 1)
        os.close(saved_fd)

    if not r.success or not r.html:
        return []

    try:
        soup = BeautifulSoup(r.html, "html.parser")
        results = soup.find_all("div", class_="result")

        hits = []
        for div in results:
            a_title = div.find("a", class_="result__a")
            a_url = div.find("a", class_="result__url")
            snippet = div.find("a", class_="result__snippet")

            if a_title:
                title = a_title.text.strip()
                raw_href = a_url["href"] if a_url else a_title.get("href", "")

                # Extract real URL from the uddg query parameter if present
                parsed = urlparse(raw_href)
                qs = parse_qs(parsed.query)
                real_url = qs.get("uddg", [raw_href])[0]

                if real_url.startswith("//"):
                    real_url = "https:" + real_url

                body = snippet.text.strip() if snippet else ""
                hits.append({
                    "title": title,
                    "url": real_url,
                    "snippet": body,
                })

                if len(hits) >= max_results:
                    break
        return hits
    except Exception as exc:
        print(f"[DDG Search Error] Fallback failed: {exc}", file=sys.stderr)
        return []


async def _crawl4ai_fetch(url: str) -> dict:
    from crawl4ai import AsyncWebCrawler

    # crawl4ai uses Rich which writes via its own captured stdout reference, so
    # contextlib.redirect_stdout doesn't catch it. Redirect at the file-descriptor
    # level — crawl4ai's banner / [FETCH] / [SCRAPE] markers would otherwise
    # corrupt the MCP stdio JSON-RPC stream.
    saved_fd = os.dup(1)
    os.dup2(2, 1)
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            r = await crawler.arun(url=url)
    finally:
        os.dup2(saved_fd, 1)
        os.close(saved_fd)
    # r.markdown is a str subclass (StringCompatibleMarkdown) that Pydantic
    # serializes as {} because its real field is private. Pull the raw string
    # out and force a plain str so FastMCP serializes correctly.
    md = r.markdown
    raw = (
        getattr(md, "raw_markdown", None)
        or getattr(md, "fit_markdown", None)
        or md
        or r.cleaned_html
        or r.html
        or ""
    )
    text = str(raw)
    return {
        "status": int(getattr(r, "status_code", None) or 200),
        "content_type": "text/markdown",
        "length_bytes": len(text.encode("utf-8")),
        "text": text,
    }


@mcp.tool()
async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web (Tavily primary, DDG fallback). Hard-capped at 5 results. Example: web_search("python asyncio tutorial", 3)."""
    max_results = max(1, min(max_results, MAX_SEARCH_RESULTS))
    if os.environ.get("TAVILY_API_KEY") and _under_cap("tavily"):
        try:
            results = _tavily_search(query, max_results)
            if results:
                _bump("tavily")
                return results
        except Exception:
            _bump("tavily", "errors")
    results = await _ddg_search(query, max_results)
    _bump("duckduckgo")
    return results


@mcp.tool()
def retrieve_context(query: str, max_results: int = 3) -> list[dict]:
    """Retrieve highly relevant context from the local document corpus using semantic search.
    Useful when the user asks about local specs, incident logs, personnel archives, or Project Aegis.
    Example: retrieve_context("Who is the lead scientist for the Chronos project?", 3)."""
    from tools.retrieve_tool import retrieve_corpus_context
    return retrieve_corpus_context(query, max_results)


def _resolve_path(path: str) -> Path:
    if path.startswith("art:"):
        art_id = path[4:]
        p1 = Path(__file__).parent / "state" / "artifacts" / art_id
        if p1.exists():
            return p1
        p2 = Path(__file__).parent / "artifacts" / art_id
        if p2.exists():
            return p2
        return Path(__file__).parent / "sandbox" / art_id
    else:
        return (Path(__file__).parent / "sandbox" / path).resolve()


def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i : i + chunk_size]
        chunks.append(" ".join(chunk_words))
        i += chunk_size - overlap
        if chunk_size - overlap <= 0:
            break
    return chunks


@mcp.tool()
def index_document(path: str, chunk_size: int = 400, overlap: int = 80) -> dict:
    """Chunk a sandbox file or artifact and write the chunks into Memory as
    fact records, where they become FAISS-searchable for later queries.
    Use this when the content must be searchable across later turns or runs.
    For one-shot inspection of a file's contents, use read_file."""
    try:
        resolved_path = _resolve_path(path)
        if not resolved_path.exists():
            raise ValueError(f"File not found: {path} (resolved: {resolved_path})")
            
        text = resolved_path.read_text(encoding="utf-8")
        chunks = _chunk_text(text, chunk_size, overlap)
        num_chunks = len(chunks)
        
        if path.startswith("art:"):
            source_name = f"artifact:{path[4:]}"
        else:
            source_name = f"sandbox:{path}"
            
        import memory
        import uuid
        run_id = uuid.uuid4().hex[:8]
        
        for idx, chunk in enumerate(chunks, 1):
            descriptor = f"[{source_name} chunk {idx}/{num_chunks}] {chunk}"
            memory.add_fact(
                descriptor=descriptor,
                value={"chunk": chunk},
                keywords=["fact", "chunk"],
                source=source_name,
                run_id=run_id
            )
            
        return {"status": "success", "chunks_indexed": num_chunks}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def search_knowledge(query: str, k: int = 5) -> list[dict]:
    """Vector search over previously indexed fact chunks. Use this rather
    than re-fetching or re-reading source files when Memory already
    contains indexed chunks for the topic."""
    try:
        import memory
        k = int(k)
        records = memory.search_memory(query, k=k)
        
        results = []
        for r in records:
            if r.key.startswith("[") or "chunk" in r.tags:
                results.append({
                    "key": r.key,
                    "value": r.value,
                    "tags": r.tags
                })
        return results
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def fetch_url(url: str, timeout: int = 20) -> dict:
    """Fetch clean markdown from a URL via crawl4ai (headless Chromium). Example: fetch_url("https://example.com")."""
    return await _crawl4ai_fetch(url)


@mcp.tool()
def get_time(timezone: str = "UTC") -> dict:
    """Current time in a named IANA timezone. Example: get_time("Asia/Kolkata")."""
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    offset = now.utcoffset()
    offset_hours = offset.total_seconds() / 3600 if offset else 0.0
    return {
        "iso": now.isoformat(),
        "human": now.strftime("%A, %d %B %Y %H:%M:%S %Z"),
        "timezone": timezone,
        "offset_hours": offset_hours,
    }


@mcp.tool()
def currency_convert(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert money between ISO-3 currencies via frankfurter.dev. Example: currency_convert(100, "USD", "INR")."""
    f = from_currency.upper()
    t = to_currency.upper()
    url = f"https://api.frankfurter.dev/v1/latest?amount={amount}&base={f}&symbols={t}"
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        data = r.json()
    converted = data["rates"][t]
    return {
        "amount": amount,
        "from": f,
        "to": t,
        "rate": converted / amount if amount else 0.0,
        "converted": converted,
        "date": data["date"],
        "source": "frankfurter.dev",
    }


@mcp.tool()
def read_file(path: str) -> dict:
    """Read a UTF-8 text file from the sandbox. Example: read_file("notes.txt")."""
    p = _safe(path)
    text = p.read_text(encoding="utf-8")
    return {
        "path": path,
        "size_bytes": p.stat().st_size,
        "content": text,
        "encoding": "utf-8",
    }


@mcp.tool()
def list_dir(path: str = ".") -> list[dict]:
    """List a directory inside the sandbox. Example: list_dir(".")."""
    p = _safe(path)
    out = []
    for child in sorted(p.iterdir()):
        is_dir = child.is_dir()
        out.append({
            "name": child.name,
            "type": "dir" if is_dir else "file",
            "size_bytes": 0 if is_dir else child.stat().st_size,
        })
    return out


@mcp.tool()
def create_file(path: str, content: str) -> dict:
    """Create a new file in the sandbox; errors if it exists. Example: create_file("hello.txt", "hi")."""
    p = _safe(path)
    if p.exists():
        raise ValueError(f"File '{path}' already exists")
    if not p.parent.exists():
        raise ValueError(f"Parent directory of '{path}' does not exist")
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": path, "size_bytes": p.stat().st_size}


@mcp.tool()
def update_file(path: str, content: str) -> dict:
    """Overwrite an existing sandbox file. Example: update_file("hello.txt", "new body")."""
    p = _safe(path)
    if not p.exists():
        raise ValueError(f"File '{path}' does not exist")
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": path, "size_bytes": p.stat().st_size}


@mcp.tool()
def edit_file(path: str, find: str, replace: str, replace_all: bool = False) -> dict:
    """Find-and-replace inside a sandbox file. Example: edit_file("hello.txt", "foo", "bar")."""
    p = _safe(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(find)
    if count == 0:
        raise ValueError(f"'{find}' not found in '{path}'")
    if count > 1 and not replace_all:
        raise ValueError(
            f"'{find}' occurs {count} times in '{path}'; pass replace_all=True"
        )
    new_text = text.replace(find, replace) if replace_all else text.replace(find, replace, 1)
    p.write_text(new_text, encoding="utf-8")
    replacements = count if replace_all else 1
    return {
        "ok": True,
        "path": path,
        "replacements": replacements,
        "size_bytes": p.stat().st_size,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
