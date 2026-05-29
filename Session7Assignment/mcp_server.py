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
import retriever

MAX_SEARCH_RESULTS = 5  # hard cap — Tavily prices per result

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


def _ddg_search(query: str, max_results: int) -> list[dict]:
    hits: list[dict] = []
    with DDGS() as ddgs:
        for backend in ("auto", "html", "lite"):
            try:
                hits = list(ddgs.text(query, max_results=max_results, backend=backend))
            except Exception:
                hits = []
            if hits:
                break
    return [
        {
            "title": h.get("title", ""),
            "url": h.get("href", ""),
            "snippet": h.get("body", ""),
        }
        for h in hits
    ]


async def _httpx_fetch(url: str) -> dict:
    """Fast fallback fetch using plain HTTP (no browser). Works for Wikipedia and most static pages."""
    import re
    headers = {"User-Agent": "Mozilla/5.0 (compatible; EAGAgent/1.0)"}
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
        r = await c.get(url, headers=headers)
        r.raise_for_status()
    html = r.text
    # Strip scripts, styles, then all tags → plain text
    html = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"[ \t]{2,}", " ", html).strip()
    text = "\n".join(ln.strip() for ln in text.splitlines() if ln.strip())
    return {
        "status": r.status_code,
        "content_type": "text/plain",
        "length_bytes": len(text.encode("utf-8")),
        "text": text[:60_000],
    }


async def _crawl4ai_fetch(url: str, timeout: int = 25) -> dict:
    import asyncio
    from crawl4ai import AsyncWebCrawler

    saved_fd = os.dup(1)
    os.dup2(2, 1)
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            r = await asyncio.wait_for(
                crawler.arun(url=url, page_timeout=timeout * 1000),
                timeout=timeout + 5,
            )
    except Exception:
        os.dup2(saved_fd, 1)
        os.close(saved_fd)
        # crawl4ai timed out or failed — fall back to fast httpx fetch
        return await _httpx_fetch(url)
    finally:
        try:
            os.dup2(saved_fd, 1)
            os.close(saved_fd)
        except OSError:
            pass
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
def web_search(query: str, max_results: int = 5) -> list[dict]:
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
    results = _ddg_search(query, max_results)
    _bump("duckduckgo")
    return results


@mcp.tool()
async def fetch_url(url: str, timeout: int = 30) -> dict:
    """Fetch clean text from a URL via fast HTTP. Example: fetch_url("https://example.com")."""
    return await _httpx_fetch(url)


@mcp.tool()
def retrieve_cosmic_docs(query: str, limit: int = 3) -> list[dict]:
    """Retrieve relevant documentation and runbooks from the Cosmic Operations & Developer Portal (CODP) database.
    This database contains 52 articles and chunks covering:
    - Live operational status and metrics
    - API endpoint definitions, schemas, and usage examples (including login, wallets, and leverage settings)
    - Post-mortem logs of platform incident reports (including WebSocket disconnections and Redis locks)
    - Configuration guides and recovery scripts (including update_leverage.py and bulk_update_funds.py)
    - Performance SLAs and server parameters (Tokyo and London groups)
    
    Use this tool when a query asks about Cosmic platform APIs, incidents, clients (e.g., MM001, INTMM1), or operations.
    Returns matching chunks sorted by relevance, with content and metadata.
    """
    return retriever.retrieve(query, limit)


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


def run_db_cmd(args: list[str]) -> str:
    """Helper to safely execute vector_db.py in an isolated subprocess, preventing handle sharing hangs on Windows."""
    import subprocess
    import sys
    import os
    db_script = os.path.join(os.path.dirname(__file__), "vector_db.py")
    res = subprocess.run(
        [sys.executable, "-u", db_script] + args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )
    return res.stdout


@mcp.tool()
async def index_paper(path: str) -> dict:
    """Index a single markdown paper file in papers/ directory into the FAISS index. Example: index_paper("papers/attention.md")."""
    import json
    out = run_db_cmd(["index", path])
    return json.loads(out.strip())


@mcp.tool()
async def index_all_papers(directory: str = "papers") -> dict:
    """Index all markdown files (*.md) under the specified papers/ directory into the FAISS index. Example: index_all_papers("papers")."""
    import json
    out = run_db_cmd(["index", directory])
    return json.loads(out.strip())


@mcp.tool()
async def query_papers_index(query: str, limit: int = 3) -> list[dict]:
    """Search the indexed academic papers (FAISS vector storage) using semantic search query.
    Use this tool when retrieving information from academic papers, such as Attention, ReAct, or Chain-of-Thought papers.
    Example: query_papers_index("What are Transformer contributions?", 3)
    """
    import json
    out = run_db_cmd(["query", query, str(limit)])
    return json.loads(out.strip())


if __name__ == "__main__":
    mcp.run(transport="stdio")
