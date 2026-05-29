"""
perception.py — Perception cognitive layer.

Input:  PerceptionInput  (query + iteration + tool-call history + memory)
Output: PerceivedContext (goal, progress, facts, gaps, completion flag)

Every LLM call is routed through LLM Gateway V3 (auto_route="perception").
Output is forced to JSON via response_format=json_object and validated by
Pydantic — no regex is used anywhere on LLM output.
"""
from __future__ import annotations

import json
import re
import sys  # noqa: F401 — kept for potential future use
from pathlib import Path

# Import the gateway HTTP client via importlib to avoid polluting sys.path
# (the llm_gatewayV3/ package has its own schemas.py that must not shadow ours).
import importlib.util as _ilu

_client_path = Path(__file__).parent / "llm_gatewayV3" / "client.py"
_spec = _ilu.spec_from_file_location("llm_gatewayV3.client", _client_path)
_client_mod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_client_mod)  # type: ignore[union-attr]
_GatewayLLM = _client_mod.LLM

from schemas import PerceptionInput, PerceivedContext

_llm = _GatewayLLM()

_SYSTEM = """\
You are the Perception layer of a multi-step cognitive agent.
Analyse the agent's current state and return ONLY a valid JSON object — \
no markdown fences, no prose.

Required JSON fields:
  goal               : string  — the user's ultimate objective in one sentence
  progress_summary   : string  — what has been accomplished based on tool results
  key_facts          : array   — specific facts extracted from results (numbers, names, dates, quotes)
  missing_information: array   — what is still needed to produce the final answer
  is_complete        : boolean — true ONLY when key_facts contains everything for a full answer
  suggested_answer   : string|null — draft answer when is_complete=true, otherwise null

Rules:
- key_facts must quote concrete values from actual tool results, not assumptions.
- missing_information should list only genuinely unknown items.
- Set is_complete=true only when the answer can be given right now without more tool calls.
- suggested_answer must be null when is_complete=false.
"""


def _strip_fence(text: str) -> str:
    """Remove markdown code fences that some models add despite json_object mode."""
    t = text.strip()
    if t.startswith("```"):
        newline = t.find("\n")
        t = t[newline + 1:] if newline != -1 else t[3:]
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def perceive(inp: PerceptionInput) -> PerceivedContext:
    """Run the perception LLM call and return a validated PerceivedContext."""
    history_lines: list[str] = []
    for h in inp.history:
        status = "OK " if h.success else "ERR"
        tool_part = ""
        if h.tool_name and h.tool_name not in ("memory", None):
            args_str = json.dumps(h.arguments, ensure_ascii=False)[:160]
            tool_part = f" → {h.tool_name}({args_str})"
        history_lines.append(
            f"  [{status}] iter={h.iteration} {h.action}{tool_part}\n"
            f"         result: {h.result_summary[:3000]}"
        )

    prompt = "\n".join([
        f"USER QUERY: {inp.query}",
        "",
        f"ITERATION: {inp.iteration} of {inp.max_iterations}",
        "",
        "PERSISTENT MEMORY (facts that survived from previous runs):",
        inp.memory.as_text(),
        "",
        "TOOL CALL HISTORY (this run):",
        "\n".join(history_lines) if history_lines else "  (no tool calls yet)",
        "",
        "Produce the PerceivedContext JSON now.",
    ])

    resp = _llm.chat(
        prompt=prompt,
        system=_SYSTEM,
        auto_route="perception",
        response_format={"type": "json_object"},
        max_tokens=1024,
        temperature=0.2,
    )

    raw = _strip_fence(resp.get("text", "{}"))
    parsed = resp.get("parsed")
    if not parsed:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Try to salvage a JSON object even if the text has trailing garbage
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
        if not parsed:
            # Last-resort: return a safe minimal context so the agent can continue
            parsed = {
                "goal": inp.query,
                "progress_summary": "Perception parse failed; continuing.",
                "key_facts": [],
                "missing_information": ["All information still needed."],
                "is_complete": False,
                "suggested_answer": None,
            }
    return PerceivedContext.model_validate(parsed)