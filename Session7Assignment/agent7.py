"""
agent7.py — EAGV3 Session 7 Cognitive Agent with RAG.

Wires four cognitive layers in a loop:
    Perception → Decision → Action → Memory (repeat)

Supports RAG (index enabled) vs Closed Book (index disabled via --disable-rag).
All LLM calls go through LLM Gateway V3 (must be running on localhost:8101).
All tool calls go through the MCP server via stdio transport.
Memory persists across runs in state/memory.json.

Usage:
    # Run a custom RAG query (index enabled)
    uv run agent7.py --query-id RAG_A
    
    # Run the same query in closed-book mode (index disabled)
    uv run agent7.py --query-id RAG_A --disable-rag
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

# ── Pre-defined queries ────────────────────────────────────────────────────────

QUERIES: dict[str, str] = {
    # Session 7 base queries
    "A": (
        "Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his "
        "birth date, death date, and three key contributions to information "
        "theory."
    ),
    "B": (
        "Find 3 family-friendly things to do in Tokyo this weekend. "
        "Check Saturday's weather forecast there and tell me which one "
        "is most appropriate."
    ),
    "C1": (
        "My mom's birthday is 15 May 2026. Remember that and create "
        "reminders for two weeks before and on the day."
    ),
    "C2": (
        "When is mom's birthday?"
    ),
    "D": (
        "Search for \"Python asyncio best practices\", read the top 3 results, "
        "and give me a short numbered list of the advice they agree on."
    ),
    
    # Session 7 Queries
    "E": (
        "Index the file papers/attention.md and tell me what the three key "
        "contributions of the Transformer architecture are according to this paper."
    ),
    "F1": (
        "Index every .md file under papers/. Confirm how many chunks "
        "were indexed in total."
    ),
    "F2": (
        "Across the papers I have indexed, what do they say about "
        "chain-of-thought reasoning?"
    ),
    "G": (
        "Across these papers, how do they handle the credit assignment problem?"
    ),
    "H": (
        "Compare how the ReAct paper and the Chain-of-Thought paper differ "
        "in their treatment of intermediate reasoning."
    ),

    # Session 7 RAG specific custom queries
    "RAG_A": "What was the root cause of the Cosmic API WebSocket storm on 2026-02-19, and which developer resolved it?",
    "RAG_B": "How do we recover if the market-maker's automated hedging system goes out of sync due to leverage anomalies?",
    "RAG_C": "Tell me the procedure to bulk-update client wallets when the 2FA token generation service is down.",
    "RAG_D": "What are the three specific API endpoints and JSON parameters required to configure the leverage settings for client ID INTMM1?",
    "RAG_E": "Compare the trade execution latency SLAs of the Tokyo server group versus the London server group for the Cosmic Trading network."
}

# Expected iteration counts
EXPECTED_ITERATIONS: dict[str, int] = {
    "A": 4,
    "B": 5,
    "C1": 4,
    "C2": 3,
    "D": 5,
    "E": 3,
    "F1": 3,
    "F2": 3,
    "G": 3,
    "H": 3,
    "RAG_A": 3,
    "RAG_B": 3,
    "RAG_C": 3,
    "RAG_D": 3,
    "RAG_E": 3,
}


# ── Agent loop ────────────────────────────────────────────────────────────────


async def run(query: str, disable_rag: bool = False, max_iterations: int = MAX_ITERATIONS) -> str:
    """Run the full perception → decision → action → memory loop."""
    mem = memory.load()
    history: list[HistoryEntry] = []

    # Configure available tools based on RAG status
    available_tools = [
        "web_search",
        "fetch_url",
        "get_time",
        "currency_convert",
        "read_file",
        "list_dir",
        "create_file",
        "update_file",
        "edit_file",
        "index_paper",
        "index_all_papers",
        "query_papers_index",
    ]
    if not disable_rag:
        available_tools.append("retrieve_cosmic_docs")

    _banner("EAGV3 Session 7 Agent", [
        f"Query      : {query[:100]}{'…' if len(query) > 100 else ''}",
        f"RAG Index  : {'DISABLED (Closed-Book Mode)' if disable_rag else 'ENABLED (RAG Mode)'}",
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
                    available_tools=available_tools,
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
        prog="agent7",
        description="EAGV3 Session 7 Cognitive Agent with RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "query",
        nargs="*",
        help="Free-form query text (alternative to --query-id)",
    )
    p.add_argument(
        "--query-id",
        choices=list(QUERIES.keys()),
        help="Run one of the pre-defined target/RAG queries",
    )
    p.add_argument(
        "--disable-rag",
        action="store_true",
        help="Disable the retrieve_cosmic_docs tool (Closed-Book simulation)",
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

    asyncio.run(run(query_text, disable_rag=args.disable_rag, max_iterations=args.max_iterations))


if __name__ == "__main__":
    main()
