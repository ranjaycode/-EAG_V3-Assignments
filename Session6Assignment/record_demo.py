"""
record_demo.py — Run all Session 6 demo queries and produce a terminal-style
MP4 video saved as demo_recording.mp4 in this directory.

Usage:  uv run record_demo.py
"""
from __future__ import annotations

import io
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 output so Unicode box-drawing chars don't crash on Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── Paths ───────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
GATEWAY_DIR = BASE_DIR / "llm_gatewayV3"
STATE_DIR = BASE_DIR / "state"
OUTPUT_MP4 = BASE_DIR / "demo_recording.mp4"

# ── Video settings ───────────────────────────────────────────────────────────────
W, H = 1280, 720
FPS = 15
MAX_QUERY_SECS = 120   # cap each query to 2-min video segment (speed up if longer)
HOLD_SECS = 2.5        # hold final frame between queries

# ── Terminal colour palette ─────────────────────────────────────────────────────
BG     = (13,  17,  23)
FG     = (201, 209, 217)
BLUE   = (88,  166, 255)
GREEN  = (63,  185, 80)
RED    = (248, 81,  73)
YELLOW = (210, 153, 34)
GRAY   = (110, 118, 129)
PURPLE = (188, 140, 255)

FONT_SIZE = 16
LINE_H    = FONT_SIZE + 5
HEADER_H  = 40
MAX_LINES = (H - HEADER_H - 10) // LINE_H

# ── Query definitions ────────────────────────────────────────────────────────────
QUERIES = [
    dict(
        id="Q1", num=1,
        title="Wikipedia Fetch — Claude Shannon",
        query=(
            "Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his "
            "birth date, death date, and three key contributions to information theory."
        ),
        clear_memory=False,
    ),
    dict(
        id="Q2", num=2,
        title="Tokyo Weekend Activities + Weather",
        query=(
            "Find 3 family-friendly things to do in Tokyo this weekend. "
            "Check Saturday's weather forecast there and tell me which one "
            "is most appropriate."
        ),
        clear_memory=False,
    ),
    dict(
        id="Q3-Run1", num=3,
        title="Durable Memory — Store Mom's Birthday",
        query=(
            "My mom's birthday is 15 May 2026. Remember that and give me "
            "a calendar reminder for two weeks before and on the day."
        ),
        clear_memory=True,
    ),
    dict(
        id="Q3-Run2", num=4,
        title="Durable Memory — Recall Mom's Birthday",
        query="When is mom's birthday?",
        clear_memory=False,
    ),
    dict(
        id="Q4", num=5,
        title="Python asyncio Best Practices (3-source synthesis)",
        query=(
            "Search for 'Python asyncio best practices', read the top 3 results, "
            "and give me a short numbered list of the advice they agree on."
        ),
        clear_memory=False,
    ),
]


# ── Font helper ──────────────────────────────────────────────────────────────────
_font_cache: dict[int, ImageFont.FreeTypeFont] = {}


def get_font(size: int) -> ImageFont.FreeTypeFont:
    if size in _font_cache:
        return _font_cache[size]
    for path in [
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\cour.ttf",
        r"C:\Windows\Fonts\lucon.ttf",
    ]:
        try:
            f = ImageFont.truetype(path, size)
            _font_cache[size] = f
            return f
        except OSError:
            pass
    f = ImageFont.load_default()
    _font_cache[size] = f
    return f


# ── Frame renderer ───────────────────────────────────────────────────────────────
def render_frame(
    lines: list[str], qid: str, title: str, q_num: int, total: int = 5
) -> np.ndarray:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    fh = get_font(15)
    fb = get_font(FONT_SIZE)

    # Header bar
    d.rectangle([0, 0, W, HEADER_H - 1], fill=(22, 33, 48))
    d.text((10, 10), f"▶  EAGV3 Session 6  —  {qid}: {title}", fill=BLUE, font=fh)
    d.text((W - 90, 10), f"[{q_num}/{total}]", fill=GRAY, font=fh)

    # Terminal output (last MAX_LINES lines)
    y = HEADER_H + 4
    for raw in lines[-MAX_LINES:]:
        raw = raw.rstrip()
        if not raw:
            y += LINE_H
            continue
        if len(raw) > 125:
            raw = raw[:122] + "…"

        c = FG
        if raw.startswith("═") or raw.startswith("┌") or "EAGV3" in raw:
            c = BLUE
        elif "FINAL ANSWER" in raw or "✓" in raw:
            c = GREEN
        elif "ERROR" in raw or "✗" in raw or "Traceback" in raw:
            c = RED
        elif raw.strip().startswith("│  ["):
            c = PURPLE
        elif "complete  :" in raw or "goal      :" in raw:
            c = YELLOW
        elif raw.strip().startswith("│") and "Memory" in raw:
            c = (150, 220, 150)

        d.text((8, y), raw, fill=c, font=fb)
        y += LINE_H

    return np.array(img)


def title_card_frames(line1: str, line2: str = "", secs: float = 2.5) -> list[np.ndarray]:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((W // 2, H // 2 - 35), line1, fill=BLUE, font=get_font(36), anchor="mm")
    if line2:
        d.text((W // 2, H // 2 + 30), line2, fill=FG, font=get_font(22), anchor="mm")
    arr = np.array(img)
    return [arr] * int(secs * FPS)


# ── Gateway management ───────────────────────────────────────────────────────────
def _gateway_alive() -> bool:
    try:
        with socket.create_connection(("localhost", 8101), timeout=1):
            return True
    except OSError:
        return False


def start_gateway() -> subprocess.Popen | None:
    """Start the gateway if not already running. Returns the Popen or None (already up)."""
    if _gateway_alive():
        print("[recorder] Gateway already running on :8101 — reusing it.", flush=True)
        return None  # caller must NOT kill it

    print("[recorder] Starting LLM Gateway on :8101 …", flush=True)
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", "0.0.0.0", "--port", "8101", "--log-level", "warning",
        ],
        cwd=str(GATEWAY_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        if _gateway_alive():
            print("[recorder] Gateway ready.", flush=True)
            return proc
        time.sleep(1)
    raise RuntimeError("Gateway did not start within 60 s")


# ── Query runner ─────────────────────────────────────────────────────────────────
def run_query(q: dict) -> list[tuple[float, str]]:
    if q["clear_memory"]:
        mem = STATE_DIR / "memory.json"
        if mem.exists():
            mem.unlink()
        print(f"[recorder] Memory cleared for {q['id']}", flush=True)

    uv_exe = shutil.which("uv") or "uv"
    cmd = [uv_exe, "run", "agent6.py", q["query"]]

    print(f"\n[recorder] >> {q['id']}: {q['title']}", flush=True)
    print("-" * 60, flush=True)

    t0 = time.monotonic()
    timed: list[tuple[float, str]] = []

    proc = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"},
    )

    QUERY_TIMEOUT = 240  # 4 minutes max per query
    deadline = time.monotonic() + QUERY_TIMEOUT

    for line in proc.stdout:
        stripped = line.rstrip("\n\r")
        timed.append((time.monotonic() - t0, stripped))
        print(stripped, flush=True)
        if time.monotonic() > deadline:
            timed.append((time.monotonic() - t0, "⚠ Query timeout — moving to next query"))
            proc.kill()
            break

    proc.wait(timeout=10)
    return timed


# ── Frame builder ─────────────────────────────────────────────────────────────────
def build_frames(timed: list[tuple[float, str]], q: dict) -> list[np.ndarray]:
    if not timed:
        blank = np.zeros((H, W, 3), dtype=np.uint8)
        return [blank] * int(2 * FPS)

    total_real = timed[-1][0]
    speed = max(1.0, total_real / MAX_QUERY_SECS)
    target_secs = total_real / speed

    frames: list[np.ndarray] = []
    screen: list[str] = []
    idx = 0
    dt = 1.0 / FPS
    vt = 0.0

    while vt <= target_secs + dt:
        rt = vt * speed
        while idx < len(timed) and timed[idx][0] <= rt:
            screen.append(timed[idx][1])
            idx += 1
        frames.append(render_frame(screen, q["id"], q["title"], q["num"]))
        vt += dt

    # Drain any remaining lines
    while idx < len(timed):
        screen.append(timed[idx][1])
        idx += 1
    final = render_frame(screen, q["id"], q["title"], q["num"])
    for _ in range(int(HOLD_SECS * FPS)):
        frames.append(final)

    return frames


# ── Main ──────────────────────────────────────────────────────────────────────────
def main() -> None:
    print(f"Output: {OUTPUT_MP4}", flush=True)

    gw_proc = start_gateway()   # None if already running (we must not kill it)
    writer = imageio.get_writer(str(OUTPUT_MP4), fps=FPS, quality=8, macro_block_size=1)

    try:
        # Intro title card
        for f in title_card_frames(
            "EAGV3 Session 6 — Four-Layer Cognitive Agent",
            "5 demo queries  ·  MCP tools  ·  Durable memory",
            secs=3.0,
        ):
            writer.append_data(f)

        for q in QUERIES:
            # Query transition card
            for f in title_card_frames(
                f"Query {q['num']}/5  —  {q['id']}",
                q["title"],
            ):
                writer.append_data(f)

            timed = run_query(q)
            print(f"[recorder] {q['id']}: {len(timed)} lines captured, building frames …",
                  flush=True)

            for f in build_frames(timed, q):
                writer.append_data(f)

            print(f"[recorder] {q['id']} done.", flush=True)

        # Outro
        for f in title_card_frames("All 5 queries complete!", "EAGV3 Session 6 Demo", secs=3.0):
            writer.append_data(f)

    finally:
        writer.close()
        if gw_proc is not None:   # only stop if we started it
            gw_proc.terminate()
            gw_proc.wait()

    size_mb = OUTPUT_MP4.stat().st_size / 1_048_576
    print(f"\n[recorder] DONE. Saved -> {OUTPUT_MP4}  ({size_mb:.1f} MB)", flush=True)


if __name__ == "__main__":
    main()
