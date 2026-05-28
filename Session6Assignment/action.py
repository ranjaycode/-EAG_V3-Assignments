"""
action.py — Action execution layer.

Input:  ActionInput  (a validated DecisionPlan)
Output: ActionResult (success flag, raw result, summary, memory flag)

Tool calls are dispatched to the running MCP server via the ClientSession
that agent6.py keeps alive for the duration of a run. No tool dispatch is
reimplemented here — everything goes through the MCP stdio transport.
"""
from __future__ import annotations

import json
from typing import Any

from mcp import ClientSession

from schemas import ActionInput, ActionResult


async def execute(inp: ActionInput, session: ClientSession) -> ActionResult:
    """Execute one DecisionPlan step and return a typed ActionResult."""
    plan = inp.plan

    # ── Final answer ──────────────────────────────────────────────────────────
    if plan.action == "answer":
        return ActionResult(
            success=True,
            action="answer",
            is_final=True,
            final_answer=plan.final_answer,
            result_summary=f"Final answer delivered ({len(plan.final_answer or '')} chars)",
        )

    # ── Durable memory write ───────────────────────────────────────────────────
    if plan.action == "remember":
        return ActionResult(
            success=True,
            action="remember",
            tool_name="memory",
            result={"key": plan.memory_key, "value": plan.memory_value},
            result_summary=(
                f"Stored [{plan.memory_key}] = "
                f"{(plan.memory_value or '')[:120]}"
            ),
            memory_stored=True,
        )

    # ── MCP tool call ─────────────────────────────────────────────────────────
    if plan.action == "tool_call":
        if not plan.tool_name:
            return ActionResult(
                success=False,
                action="tool_call",
                error="DecisionPlan has action=tool_call but tool_name is None",
                result_summary="ERROR: missing tool_name in DecisionPlan",
            )

        args: dict[str, Any] = plan.tool_arguments or {}
        try:
            mcp_result = await session.call_tool(plan.tool_name, args)
            content = _extract_content(mcp_result)
            summary = _summarize(content)
            return ActionResult(
                success=True,
                action="tool_call",
                tool_name=plan.tool_name,
                result=content,
                result_summary=summary,
            )
        except Exception as exc:
            err_msg = str(exc)
            return ActionResult(
                success=False,
                action="tool_call",
                tool_name=plan.tool_name,
                error=err_msg,
                result_summary=f"ERROR in {plan.tool_name}: {err_msg[:200]}",
            )

    # ── Unknown action ────────────────────────────────────────────────────────
    return ActionResult(
        success=False,
        action=plan.action,
        error=f"Unrecognised action: {plan.action!r}",
        result_summary=f"ERROR: unknown action {plan.action!r}",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract_content(mcp_result: Any) -> Any:
    """Pull a usable Python value out of an MCP CallToolResult."""
    if mcp_result is None:
        return None
    content_list = getattr(mcp_result, "content", None) or []
    if not content_list:
        return None
    item = content_list[0]
    raw = getattr(item, "text", None)
    if raw is None:
        return str(item)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


def _summarize(content: Any) -> str:
    """Short displayable summary of a tool result."""
    if content is None:
        return "(no content returned)"
    if isinstance(content, str):
        s = content
    else:
        s = json.dumps(content, ensure_ascii=False)
    return s[:500] + ("…" if len(s) > 500 else "")