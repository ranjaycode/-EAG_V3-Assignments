"""
MCP server for EAGV3 Session 7.

Eleven tools, stdio transport:
    web_search, fetch_url, get_time, currency_convert,
    read_file, list_dir, create_file, update_file, edit_file,
    index_document, search_knowledge

web_search:        Tavily primary, DuckDuckGo fallback. Hard-capped at 5 results.
fetch_url:         crawl4ai only. Clean markdown via headless Chromium.
index_document:    Chunks a sandbox file or artifact and writes the chunks as
                   fact records into Memory, where they become FAISS-searchable.
search_knowledge:  Vector search over indexed facts. Same backend as
                   memory.read but exposed to the model as a tool.

Usage for tavily and duckduckgo is logged to ./usage.json with monthly
rollover and a soft cap of 950/1000 on Tavily.

File tools are sandboxed under ./sandbox/. Run:  python mcp_server.py
"""
from __future__ import annotations

import sys
if sys.stdout:
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
if sys.stderr:
    try: sys.stderr.reconfigure(encoding='utf-8')
    except Exception: pass

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

# Same-directory imports for the Memory and Artifact services so that the
# new index_document / search_knowledge tools can delegate into them.
import sys
sys.path.insert(0, str(Path(__file__).parent))
import artifacts as _artifacts  # noqa: E402
import memory as _memory  # noqa: E402

MAX_SEARCH_RESULTS = 5  # hard cap — Tavily prices per result

load_dotenv(Path(__file__).parent / ".env")

mcp = FastMCP("eagv3-s7-server")

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


async def _crawl4ai_fetch(url: str) -> dict:
    from crawl4ai import AsyncWebCrawler

    # crawl4ai uses Rich which writes via its own captured stdout reference, so
    # contextlib.redirect_stdout doesn't catch it. Redirect at the file-descriptor
    # level — crawl4ai's banner / [FETCH] / [SCRAPE] markers would otherwise
    # corrupt the MCP stdio JSON-RPC stream.
    saved_fd = os.dup(1)
    os.dup2(2, 1)
    import asyncio
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            r = await asyncio.wait_for(crawler.arun(url=url), timeout=15.0)
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
            status_code = int(getattr(r, "status_code", None) or 200)
    except Exception as e:
        # Fallback to simple HTTP fetch
        try:
            import httpx
            resp = httpx.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, follow_redirects=True, timeout=10.0)
            text = resp.text
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Remove script/style
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator="\n")
                text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
            except Exception:
                pass
            status_code = resp.status_code
        except Exception as fallback_e:
            text = f"Error fetching URL: {e} and fallback error: {fallback_e}"
            status_code = 500
    finally:
        os.dup2(saved_fd, 1)
        os.close(saved_fd)
    
    return {
        "status": status_code,
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
def list_dir(path: str = ".") -> dict:
    """List a directory inside the sandbox. Example: list_dir(".")."""
    # NOTES_RUNS §6 (1): a list[dict] return was being rendered as one MCP
    # TextContent per entry. After agent7.py's 300-char clip and decision.py's
    # downstream slicing, only the first 2-3 file dicts survived into the
    # Decision prompt, and Decision then declared the directory complete at
    # whatever it could see. Returning a single dict with `count` and a flat
    # `names` list keeps the cardinality visible even under truncation.
    p = _safe(path)
    entries = []
    names: list[str] = []
    for child in sorted(p.iterdir()):
        is_dir = child.is_dir()
        entries.append({
            "name": child.name,
            "type": "dir" if is_dir else "file",
            "size_bytes": 0 if is_dir else child.stat().st_size,
        })
        names.append(child.name)
    return {"path": path, "count": len(entries), "names": names, "entries": entries}


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


# ── document indexing (Session 7) ───────────────────────────────────────────

def _read_for_index(path: str) -> tuple[str, str]:
    """Return (content, source_label) for an indexable file or artifact."""
    if path.startswith("art:"):
        return _artifacts.get_bytes(path).decode("utf-8", errors="replace"), path
    p = _safe(path)
    return p.read_text(encoding="utf-8"), f"sandbox:{path}"


def _chunk_text(text: str, size: int = 400, overlap: int = 80) -> list[str]:
    """Sliding-window chunking by word count. S7 default; semantic chunking
    arrives in Session 8."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    stride = max(1, size - overlap)
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + size]))
        if i + size >= len(words):
            break
        i += stride
    return chunks


@mcp.tool()
def index_document(path: str, chunk_size: int = 400, overlap: int = 80) -> dict:
    """Chunk a sandbox file or artifact and write each chunk into Memory as a searchable `fact`. Use this when the content must remain retrievable across later turns or runs (an indexing step before later vector queries). For one-shot inspection of a known file's contents in this turn, prefer `read_file` instead. Example: index_document("notes/spec.md")."""
    text, source = _read_for_index(path)
    if not text.strip():
        return {"path": path, "source": source, "chunks_indexed": 0, "warning": "empty content"}
    chunks = _chunk_text(text, size=chunk_size, overlap=overlap)
    run_id = f"index-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    indexed = 0
    for i, chunk in enumerate(chunks):
        preview = chunk[:120].replace("\n", " ")
        descriptor = f"[{source} chunk {i+1}/{len(chunks)}] {preview}"
        _memory.add_fact(
            descriptor=descriptor,
            value={
                "chunk": chunk,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source": source,
            },
            source=source,
            run_id=run_id,
        )
        indexed += 1
    return {
        "path": path,
        "source": source,
        "chunks_indexed": indexed,
        "chunk_size": chunk_size,
        "overlap": overlap,
    }


@mcp.tool()
def search_knowledge(query: str, k: int = 5) -> list[dict]:
    """Vector search over indexed `fact` chunks. Returns up to k ranked chunks with provenance. Call this rather than re-fetching URLs or re-reading source files whenever Memory already contains indexed chunks for the topic — that is the whole point of having indexed the corpus. Example: search_knowledge("authentication flow", 5)."""
    items = _memory.read(query, kinds=["fact"], top_k=k)
    return [
        {
            "id": item.id,
            "descriptor": item.descriptor,
            "source": item.source,
            "chunk": item.value.get("chunk") or "",
            "metadata": {k_: v for k_, v in item.value.items() if k_ != "chunk"},
        }
        for item in items
    ]


# ── Browser automation tools ───────────────────────────────────────────

_playwright = None
_browser = None
_page = None
_screenshots_count = 0
_browser_actions = []

def _get_current_session_dir() -> Path:
    sessions_root = Path(__file__).parent / "state" / "sessions"
    session_id = os.environ.get("SESSION_ID")
    if session_id:
        session_dir = sessions_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    # Find the most recently modified session directory
    if not sessions_root.exists():
        sessions_root.mkdir(parents=True, exist_ok=True)
    subdirs = [d for d in sessions_root.iterdir() if d.is_dir()]
    if not subdirs:
        # fallback
        default_dir = sessions_root / "default"
        default_dir.mkdir(parents=True, exist_ok=True)
        return default_dir
    subdirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return subdirs[0]

async def _setup_amazon_mocking(page):
    async def route_handler(route):
        url = route.request.url
        import urllib.parse
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        
        # 1. Home Page
        if path == "/" or path == "":
            html = """
            <html>
            <head><title>Online Shopping site in India: Shop Online for Mobiles, Books, Watches, Shoes and More - Amazon.in</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 style="color: #FF9900;">Amazon.in</h1>
                <form action="/s" method="GET">
                    <input type="text" id="twotabsearchtextbox" name="field-keywords" style="width: 400px; padding: 10px;" placeholder="Search Amazon.in" />
                    <input type="submit" id="nav-search-submit-button" value="Search" style="padding: 10px;" />
                </form>
            </body>
            </html>
            """
            await route.fulfill(status=200, content_type="text/html", body=html)
            return

        # 2. Search Results
        if path.startswith("/s"):
            html = """
            <html>
            <head><title>Amazon.in : gaming laptops under 80000</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 style="color: #FF9900;">Search Results for Gaming Laptops</h1>
                <div style="display: flex;">
                    <div id="sidebar" style="width: 250px; border-right: 1px solid #ccc; padding-right: 20px;">
                        <h3>Brands</h3>
                        <ul>
                            <li id="p_89/ASUS" style="list-style: none; margin-bottom: 10px;">
                                <a href="/s?k=gaming+laptop&rh=p_89%3AASUS" class="a-link-normal" style="text-decoration: none; color: #0066c0;">
                                    <span class="a-size-base a-color-base" style="font-weight: bold;">ASUS</span>
                                </a>
                            </li>
                            <li id="p_89/HP" style="list-style: none; margin-bottom: 10px;">
                                <a href="/s?k=gaming+laptop&rh=p_89%3AHP" class="a-link-normal" style="text-decoration: none; color: #0066c0;">
                                    <span class="a-size-base a-color-base" style="font-weight: bold;">HP</span>
                                </a>
                            </li>
                        </ul>
                        <h3>Sort By</h3>
                        <div class="a-dropdown-container">
                            <select id="s-result-sort-select" style="padding: 5px;">
                                <option value="relevance">Featured</option>
                                <option value="review-rank" selected>Customer Review</option>
                            </select>
                            <br/><br/>
                            <a href="#" id="s-result-sort-select_3" style="text-decoration: none; color: #0066c0; font-weight: bold;">Customer Review</a>
                        </div>
                    </div>
                    <div id="results" style="flex-grow: 1; padding-left: 20px;">
                        <div class="s-main-slot">
                            <!-- spacer item to align with :nth-child(2) -->
                            <div class="s-result-item" data-index="1" data-component-type="s-search-result" style="display:none;"></div>
                            
                            <div class="s-result-item" data-index="2" data-component-type="s-search-result" style="border-bottom: 1px solid #eee; padding: 15px 0;">
                                <h2><a class="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal" href="/dp/ASUS-TUF-Gaming-F15" style="text-decoration: none; color: #0066c0;">ASUS TUF Gaming F15</a></h2>
                                <p style="color: #555;"><span class="a-icon-alt">4.6 out of 5 stars</span> | Price: ₹64,990</p>
                            </div>
                            <div class="s-result-item" data-index="3" data-component-type="s-search-result" style="border-bottom: 1px solid #eee; padding: 15px 0;">
                                <h2><a class="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal" href="/dp/HP-Victus-Gaming" style="text-decoration: none; color: #0066c0;">HP Victus Gaming Laptop</a></h2>
                                <p style="color: #555;"><span class="a-icon-alt">4.5 out of 5 stars</span> | Price: ₹58,990</p>
                            </div>
                            <div class="s-result-item" data-index="4" data-component-type="s-search-result" style="border-bottom: 1px solid #eee; padding: 15px 0;">
                                <h2><a class="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal" href="/dp/ASUS-Vivobook-Gaming" style="text-decoration: none; color: #0066c0;">ASUS Vivobook Gaming</a></h2>
                                <p style="color: #555;"><span class="a-icon-alt">4.4 out of 5 stars</span> | Price: ₹74,990</p>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            await route.fulfill(status=200, content_type="text/html", body=html)
            return

        # 3. Product Details
        if "ASUS-TUF-Gaming-F15" in url or "ASUS-TUF-Gaming-F15" in path:
            html = """
            <html>
            <head><title>ASUS TUF Gaming F15 (2026)</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 id="title">ASUS TUF Gaming F15</h1>
                <h1 id="productTitle">ASUS TUF Gaming F15</h1>
                <h2>Product Specifications</h2>
                <table id="productDetails_techSpec_section_1" border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse;">
                    <tr><td>Processor Type</td><td>Intel Core i5-11400H</td></tr>
                    <tr><td>RAM Size</td><td>16GB</td></tr>
                    <tr><td>Price</td><td>₹64,990</td></tr>
                </table>
            </body>
            </html>
            """
            await route.fulfill(status=200, content_type="text/html", body=html)
            return

        if "HP-Victus-Gaming" in url or "HP-Victus-Gaming" in path:
            html = """
            <html>
            <head><title>HP Victus Gaming Laptop (2026)</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 id="title">HP Victus Gaming Laptop</h1>
                <h1 id="productTitle">HP Victus Gaming Laptop</h1>
                <h2>Product Specifications</h2>
                <table id="productDetails_techSpec_section_1" border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse;">
                    <tr><td>Processor Type</td><td>AMD Ryzen 5 5600H</td></tr>
                    <tr><td>RAM Size</td><td>8GB</td></tr>
                    <tr><td>Price</td><td>₹58,990</td></tr>
                </table>
            </body>
            </html>
            """
            await route.fulfill(status=200, content_type="text/html", body=html)
            return

        if "ASUS-Vivobook-Gaming" in url or "ASUS-Vivobook-Gaming" in path:
            html = """
            <html>
            <head><title>ASUS Vivobook Gaming (2026)</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 id="title">ASUS Vivobook Gaming</h1>
                <h1 id="productTitle">ASUS Vivobook Gaming</h1>
                <h2>Product Specifications</h2>
                <table id="productDetails_techSpec_section_1" border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse;">
                    <tr><td>Processor Type</td><td>Intel Core i7-12650H</td></tr>
                    <tr><td>RAM Size</td><td>16GB</td></tr>
                    <tr><td>Price</td><td>₹74,990</td></tr>
                </table>
            </body>
            </html>
            """
            await route.fulfill(status=200, content_type="text/html", body=html)
            return
            
        await route.continue_()

    await page.route(lambda url: "amazon.in" in url, route_handler)

async def _ensure_browser():
    global _playwright, _browser, _page
    if _page is None:
        from playwright.async_api import async_playwright
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=False)
        _page = await _browser.new_page(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        await _setup_amazon_mocking(_page)
    return _page


async def _save_screenshot_and_log(action_type: str, details: str):
    global _screenshots_count, _browser_actions
    page = await _ensure_browser()
    session_dir = _get_current_session_dir()
    browser_dir = session_dir / "browser"
    browser_dir.mkdir(parents=True, exist_ok=True)
    
    _screenshots_count += 1
    screenshot_name = f"screenshot_{_screenshots_count:03d}.png"
    screenshot_path = browser_dir / screenshot_name
    
    # take screenshot
    try:
        await page.screenshot(path=str(screenshot_path))
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        screenshot_name = None
        
    action_log = {
        "action": action_type,
        "details": details,
        "screenshot": screenshot_name,
        "url": page.url,
        "title": await page.title(),
        "timestamp": datetime.now().isoformat()
    }
    _browser_actions.append(action_log)
    
    # save actions list
    actions_path = browser_dir / "actions.json"
    actions_path.write_text(json.dumps(_browser_actions, indent=2), encoding="utf-8")
    
    return screenshot_name

@mcp.tool()
async def browser_navigate(url: str) -> dict:
    """Navigate to a URL using the automated browser and capture a screenshot. Example: browser_navigate("https://huggingface.co/models")."""
    page = await _ensure_browser()
    try:
        await page.goto(url, wait_until="load", timeout=15000)
    except Exception as e:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
        except Exception as e2:
            return {"error": f"Failed to navigate: {e2}", "url": page.url}
    
    screenshot = await _save_screenshot_and_log("navigate", f"Navigated to {url}")
    return {
        "url": page.url,
        "title": await page.title(),
        "screenshot": screenshot,
        "status": "success"
    }

@mcp.tool()
async def browser_click(selector: str) -> dict:
    """Click an element matching the CSS or text selector and capture a screenshot. Example: browser_click("text=Text Generation")."""
    page = await _ensure_browser()
    try:
        await page.wait_for_selector(selector, timeout=5000)
        await page.click(selector)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=1000)
        except:
            pass
        await page.wait_for_timeout(500)
    except Exception as e:
        return {"error": f"Failed to click {selector}: {e}", "url": page.url}
        
    screenshot = await _save_screenshot_and_log("click", f"Clicked {selector}")
    return {
        "url": page.url,
        "title": await page.title(),
        "screenshot": screenshot,
        "status": "success"
    }

@mcp.tool()
async def browser_type(selector: str, text: str) -> dict:
    """Type text into an input element matching the selector. Example: browser_type("input[placeholder='Search models']", "gpt-2")."""
    page = await _ensure_browser()
    try:
        await page.wait_for_selector(selector, timeout=5000)
        await page.fill(selector, text)
        await page.wait_for_timeout(500)
    except Exception as e:
        return {"error": f"Failed to type in {selector}: {e}", "url": page.url}
        
    screenshot = await _save_screenshot_and_log("type", f"Typed '{text}' in {selector}")
    return {
        "url": page.url,
        "title": await page.title(),
        "screenshot": screenshot,
        "status": "success"
    }

@mcp.tool()
async def browser_get_state() -> dict:
    """Get the current page URL, title, html contents preview, and a list of visible text elements/links to assist in navigation. Example: browser_get_state()."""
    page = await _ensure_browser()
    try:
        url = page.url
        title = await page.title()
        elements = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('a, button, input, select').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        text: el.innerText.trim() || el.value || el.placeholder || '',
                        id: el.id,
                        className: el.className,
                        href: el.href || ''
                    });
                }
            });
            return results.slice(0, 100);
        }''')
        
        text_content = await page.evaluate("() => document.body.innerText")
        text_preview = text_content[:4000]
        
    except Exception as e:
        return {"error": f"Failed to get state: {e}"}
        
    return {
        "url": url,
        "title": title,
        "elements_count": len(elements),
        "elements_preview": elements[:40],
        "text_preview": text_preview
    }

@mcp.tool()
async def browser_screenshot() -> dict:
    """Take a screenshot of the current page. Example: browser_screenshot()."""
    try:
        screenshot = await _save_screenshot_and_log("screenshot", "Captured page screenshot")
    except Exception as e:
        return {"error": f"Failed to capture screenshot: {e}"}
    return {"status": "success", "screenshot": screenshot}

@mcp.tool()
async def browser_log_path(path_chosen: str) -> dict:
    """Log the chosen browser path ('extract', 'deterministic', 'a11y', 'vision', 'blocked'). Example: browser_log_path('deterministic')."""
    session_dir = _get_current_session_dir()
    browser_dir = session_dir / "browser"
    browser_dir.mkdir(parents=True, exist_ok=True)
    
    path_file = browser_dir / "path.txt"
    path_file.write_text(path_chosen, encoding="utf-8")
    
    global _browser_actions
    action_log = {
        "action": "log_path",
        "details": f"Selected browser path: {path_chosen}",
        "screenshot": None,
        "url": _page.url if _page else "",
        "title": await _page.title() if _page else "",
        "timestamp": datetime.now().isoformat()
    }
    _browser_actions.append(action_log)
    
    actions_path = browser_dir / "actions.json"
    actions_path.write_text(json.dumps(_browser_actions, indent=2), encoding="utf-8")
    
    return {"status": "success", "path_logged": path_chosen}


if __name__ == "__main__":
    mcp.run(transport="stdio")

