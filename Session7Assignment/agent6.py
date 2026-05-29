"""
agent6.py — EAGV3 Session 6 Cognitive Agent.

Wires four cognitive layers in a loop:
    Perception → Decision → Action → Memory (repeat)

All LLM calls go through LLM Gateway V3 (must be running on localhost:8101).
All tool calls go through the MCP server via stdio transport.
Memory persists across runs in state/memory.json.

Usage:
    uv run agent6.py --query-id A
    uv run agent6.py --query-id B
    uv run agent6.py --query-id C1          # run 1: stores memory
    uv run agent6.py --query-id C2          # run 2: reads memory
    uv run agent6.py --query-id D
    uv run agent6.py --clear-memory --query-id C1   # fresh start
    uv run agent6.py "any custom query here"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Force UTF-8 output so Unicode box-drawing chars don't crash on Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

import action
import decision
import memory
import perception
from schemas import ActionInput, DecisionInput, HistoryEntry, PerceptionInput

# ── Configuration ─────────────────────────────────────────────────────────────

MCP_SCRIPT = Path(__file__).parent / "mcp_server.py"
MAX_ITERATIONS = 10

AVAILABLE_TOOLS = [
    "web_search",
    "fetch_url",
    "get_time",
    "currency_convert",
    "read_file",
    "list_dir",
    "create_file",
    "update_file",
    "edit_file",
]

# ── Pre-defined target queries ────────────────────────────────────────────────

QUERIES: dict[str, str] = {
    "A": (
        "What is the current time right now in Tokyo and in London? "
        "Also find 2 major AI or technology conferences scheduled in the next "
        "6 months and state their dates and locations."
    ),
    "B": (
        "Convert 1000 USD to EUR and to JPY using today's live exchange rates. "
        "Then find the current price of a Big Mac in Germany (in EUR) and in "
        "Japan (in JPY). Calculate exactly how many Big Macs 1000 USD would buy "
        "in each country, showing the working."
    ),
    "C1": (
        "My name is Ranjay and my research focus is solid-state battery technology "
        "for electric vehicles. Please remember both facts about me (my name and "
        "my research focus) to durable memory. Then find 3 companies or research "
        "groups that are leading solid-state battery development as of 2024-2025."
    ),
    "C2": (
        "Based on what you already know about me and my research interests stored "
        "in memory, find the most recent breakthrough or news story in my research "
        "field from 2025 and summarise it."
    ),
    "D": (
        "Research the top 3 AI companies by venture-capital funding raised in 2024. "
        "Fetch the Wikipedia page for the top-funded company to get its founding "
        "year, headquarters, and key products or services. Then create a file called "
        "top_ai.txt in the sandbox with a structured summary that includes: company "
        "name, 2024 funding amount, founding year, headquarters, and key products."
    ),
}

# Expected iteration counts per query (for grading).
# Queries that exceed 2× this count are not considered passing.
EXPECTED_ITERATIONS: dict[str, int] = {
    "A": 4,
    "B": 5,
    "C1": 4,
    "C2": 3,
    "D": 5,
}


# ── Agent loop ────────────────────────────────────────────────────────────────


async def run(query: str, max_iterations: int = MAX_ITERATIONS) -> str:
    """Run the full perception → decision → action → memory loop."""
    mem = memory.load()
    history: list[HistoryEntry] = []

    _banner("EAGV3 Session 6 Agent", [
        f"Query      : {query[:100]}{'…' if len(query) > 100 else ''}",
        f"Memory     : {mem.as_text().strip()}",
        f"Max iters  : {max_iterations}",
        f"MCP server : {MCP_SCRIPT}",
    ])

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(MCP_SCRIPT)],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            for iteration in range(1, max_iterations + 1):
                _divider(f"Iteration {iteration}/{max_iterations}")

                # ── 1. Perception ──────────────────────────────────────────
                perc_inp = PerceptionInput(
                    query=query,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    history=history,
                    memory=mem,
                )
                perceived = perception.perceive(perc_inp)
                _log("Perception", [
                    f"goal      : {perceived.goal}",
                    f"complete  : {perceived.is_complete}",
                    f"facts     : {len(perceived.key_facts)} gathered",
                    f"missing   : {perceived.missing_information[:2]}",
                ])

                # ── 2. Decision ────────────────────────────────────────────
                dec_inp = DecisionInput(
                    perceived=perceived,
                    available_tools=AVAILABLE_TOOLS,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    memory=mem,
                )
                plan = decision.decide(dec_inp)
                _log("Decision", [
                    f"action    : {plan.action}",
                    f"tool      : {plan.tool_name}({_short(plan.tool_arguments)})"
                    if plan.tool_name else "",
                    f"remember  : [{plan.memory_key}]" if plan.memory_key else "",
                    f"reasoning : {plan.reasoning[:100]}",
                ])

                # ── 3. Action ──────────────────────────────────────────────
                act_inp = ActionInput(plan=plan)
                result = await action.execute(act_inp, session)
                status = "✓" if result.success else "✗"
                _log("Action", [
                    f"{status} {result.result_summary[:140]}",
                ])

                # ── 4. Memory update ───────────────────────────────────────
                if result.memory_stored and plan.memory_key and plan.memory_value:
                    mem = memory.upsert(mem, plan.memory_key, plan.memory_value)
                    _log("Memory", [f"stored [{plan.memory_key}]"])

                # ── Record history ─────────────────────────────────────────
                history.append(HistoryEntry(
                    iteration=iteration,
                    action=plan.action,
                    tool_name=result.tool_name,
                    arguments=plan.tool_arguments or {},
                    result_summary=result.result_summary,
                    success=result.success,
                ))

                # ── Done? ──────────────────────────────────────────────────
                if result.is_final:
                    answer = result.final_answer or ""
                    _banner(f"FINAL ANSWER  (completed in {iteration} iterations)", [answer])
                    return answer

                # Pace iterations slightly
                import time as _time
                _time.sleep(2)

    # Fell through without a clean answer
    fallback_parts = [h.result_summary for h in history[-3:] if h.success]
    fallback = (
        "(Max iterations reached — best-effort answer from gathered data)\n\n"
        + "\n".join(fallback_parts)
    )
    print(f"\n⚠️  Reached max iterations ({max_iterations}). Returning best-effort answer.")
    return fallback


# ── Formatting helpers ────────────────────────────────────────────────────────

_WIDTH = 70


def _banner(title: str, lines: list[str]) -> None:
    print(f"\n{'═' * _WIDTH}")
    print(f"  {title}")
    print(f"{'═' * _WIDTH}")
    for line in lines:
        if line:
            print(f"  {line}")
    print()


def _divider(label: str) -> None:
    pad = _WIDTH - len(label) - 4
    print(f"\n┌── {label} {'─' * max(pad, 2)}")


def _log(layer: str, lines: list[str]) -> None:
    prefix = f"│  [{layer:<10}]"
    for line in lines:
        if line.strip():
            print(f"{prefix} {line}")


def _short(obj: object | None) -> str:
    if obj is None:
        return "null"
    s = json.dumps(obj, ensure_ascii=False)
    return s[:80] + "…" if len(s) > 80 else s


# ── CLI entry point ───────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="agent6",
        description="EAGV3 Session 6 Cognitive Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Target queries (pre-defined):
  A   Time zones + upcoming conferences
  B   Currency conversion + Big Mac price calculation
  C1  Remember user profile + research companies      (run BEFORE C2)
  C2  Recall user profile from memory + find news     (run AFTER C1)
  D   Top AI companies + Wikipedia fetch + file write

Examples:
  uv run agent6.py --query-id A
  uv run agent6.py --clear-memory --query-id C1
  uv run agent6.py --query-id C2
  uv run agent6.py "What is the capital of France?"
""",
    )
    p.add_argument(
        "query",
        nargs="*",
        help="Free-form query text (alternative to --query-id)",
    )
    p.add_argument(
        "--query-id",
        choices=list(QUERIES.keys()),
        help="Run one of the four pre-defined target queries",
    )
    p.add_argument(
        "--clear-memory",
        action="store_true",
        help="Wipe state/memory.json before running (clean slate)",
    )
    p.add_argument(
        "--max-iterations",
        type=int,
        default=MAX_ITERATIONS,
        help=f"Override max iterations (default {MAX_ITERATIONS})",
    )
    p.add_argument(
        "--list-queries",
        action="store_true",
        help="Print all pre-defined target queries and exit",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_queries:
        for qid, qtext in QUERIES.items():
            exp = EXPECTED_ITERATIONS.get(qid, "?")
            print(f"\n[{qid}]  (expected ~{exp} iterations)")
            print(f"  {qtext}")
        return

    if args.clear_memory:
        memory.clear_all()
        print("✓ Memory cleared (state/memory.json deleted).")

    if args.query_id:
        query_text = QUERIES[args.query_id]
    elif args.query:
        query_text = " ".join(args.query)
    else:
        parser.print_help()
        sys.exit(0)

    asyncio.run(run(query_text, max_iterations=args.max_iterations))


if __name__ == "__main__":
    main()