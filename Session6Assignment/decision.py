"""
decision.py — Decision cognitive layer.

Input:  DecisionInput  (perceived context + memory + available tools + iteration)
Output: DecisionPlan   (action=tool_call|remember|answer with required fields)

Every LLM call is routed through LLM Gateway V3 (auto_route="decision").
Output is forced to JSON via response_format=json_object and validated by
Pydantic — no regex is used anywhere on LLM output.
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import re
from pathlib import Path

_client_path = Path(__file__).parent / "llm_gatewayV3" / "client.py"
_spec = _ilu.spec_from_file_location("llm_gatewayV3.client", _client_path)
_client_mod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_client_mod)  # type: ignore[union-attr]
_GatewayLLM = _client_mod.LLM

from schemas import DecisionInput, DecisionPlan

_llm = _GatewayLLM()

# One-line doc for each available MCP tool shown in the decision prompt.
_TOOL_DOCS: dict[str, str] = {
    "web_search": (
        'web_search(query: str, max_results: int=5) '
        '→ list[{title, url, snippet}]  — search the live web'
    ),
    "fetch_url": (
        'fetch_url(url: str) '
        '→ {text: str, status: int}  — fetch a page as clean markdown'
    ),
    "get_time": (
        'get_time(timezone: str="UTC") '
        '→ {iso, human, timezone, offset_hours}  — current date/time'
    ),
    "currency_convert": (
        'currency_convert(amount: float, from_currency: str, to_currency: str) '
        '→ {converted, rate, date}  — live FX rate via frankfurter.dev'
    ),
    "read_file": (
        'read_file(path: str) '
        '→ {content: str}  — read a file from the MCP sandbox/'
    ),
    "list_dir": (
        'list_dir(path: str=".") '
        '→ list[{name, type, size_bytes}]  — list sandbox/ directory'
    ),
    "create_file": (
        'create_file(path: str, content: str) '
        '→ {ok: bool}  — create a new file in sandbox/ (errors if exists)'
    ),
    "update_file": (
        'update_file(path: str, content: str) '
        '→ {ok: bool}  — overwrite an existing sandbox/ file'
    ),
    "edit_file": (
        'edit_file(path: str, find: str, replace: str, replace_all: bool=False) '
        '→ {ok: bool}  — find-and-replace in a sandbox/ file'
    ),
}

_SYSTEM = """\
You are the Decision layer of a multi-step cognitive agent.
Choose EXACTLY ONE action and return ONLY a valid JSON object — \
no markdown fences, no prose.

Required JSON fields:
  reasoning     : string           — why you chose this action (1-2 sentences)
  action        : "tool_call" | "remember" | "answer"
  tool_name     : string | null    — required when action=tool_call
  tool_arguments: object | null    — required when action=tool_call
  memory_key    : string | null    — required when action=remember
  memory_value  : string | null    — required when action=remember
  final_answer  : string | null    — required when action=answer

Decision rules (follow strictly):
1. action=tool_call  → fill tool_name + tool_arguments; set everything else to null.
2. action=remember   → fill memory_key + memory_value; set everything else to null.
   Use remember to persist facts that MUST survive between separate process runs.
   Remember before gathering additional information if the user asked you to remember.
3. action=answer     → fill final_answer with a complete, well-structured response;
   set everything else to null. Use only when is_complete=true and all data is in hand.
4. Never repeat an identical tool call (same tool + same arguments) that already succeeded.
5. If a search query keeps returning the same results, try a DIFFERENT, more specific query.
6. If you reach the final iteration, you MUST use action=answer with whatever you have.
7. Prefer tools over guessing. Do not fabricate data.
"""


def _strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        newline = t.find("\n")
        t = t[newline + 1:] if newline != -1 else t[3:]
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def decide(inp: DecisionInput) -> DecisionPlan:
    """Run the decision LLM call and return a validated DecisionPlan."""
    tools_text = "\n".join(
        f"  • {_TOOL_DOCS[t]}"
        for t in inp.available_tools
        if t in _TOOL_DOCS
    )

    facts_text = (
        "\n".join(f"  • {f}" for f in inp.perceived.key_facts)
        or "  (none gathered yet)"
    )
    missing_text = (
        "\n".join(f"  • {m}" for m in inp.perceived.missing_information)
        or "  (none — all information available)"
    )

    is_last = inp.iteration >= inp.max_iterations
    urgency = (
        "\n⚠️  THIS IS THE FINAL ITERATION. You MUST use action=answer NOW.\n"
        if is_last else ""
    )
    suggested = (
        f"\nSUGGESTED ANSWER (from Perception):\n  {inp.perceived.suggested_answer}\n"
        if inp.perceived.suggested_answer else ""
    )

    prompt = "\n".join([
        f"GOAL: {inp.perceived.goal}",
        "",
        f"PROGRESS: {inp.perceived.progress_summary}",
        "",
        "KEY FACTS GATHERED:",
        facts_text,
        "",
        "MISSING INFORMATION:",
        missing_text,
        "",
        "PERSISTENT MEMORY:",
        inp.memory.as_text(),
        "",
        f"IS_COMPLETE: {inp.perceived.is_complete}",
        suggested,
        f"ITERATION: {inp.iteration} of {inp.max_iterations}{urgency}",
        "",
        "AVAILABLE MCP TOOLS:",
        tools_text,
        "",
        "Choose the single best next action.",
    ])

    resp = _llm.chat(
        prompt=prompt,
        system=_SYSTEM,
        auto_route="decision",
        response_format={"type": "json_object"},
        max_tokens=768,
        temperature=0.1,
    )

    raw = _strip_fence(resp.get("text", "{}"))
    parsed = resp.get("parsed")
    if not parsed:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
        if not parsed:
            parsed = {
                "reasoning": "Decision parse failed; defaulting to answer with available data.",
                "action": "answer",
                "tool_name": None,
                "tool_arguments": None,
                "memory_key": None,
                "memory_value": None,
                "final_answer": inp.perceived.suggested_answer or inp.perceived.progress_summary or "Unable to complete task.",
            }
    return DecisionPlan.model_validate(parsed)