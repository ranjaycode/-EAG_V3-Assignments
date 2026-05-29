"""
schemas.py — Pydantic v2 contracts for every inter-module boundary.

Architecture-level types:
  Artifact      — handle + metadata for large stored content
  MemoryItem    — one entry in the persistent memory store (fact or artifact ref)
  MemoryEntry   — backwards-compat alias (key/value pair)
  MemoryState   — the whole memory file  (supports both entries and items)
  Goal          — one sub-goal with open/done status and optional artifact attach
  HistoryEntry  — one completed iteration step

Layer contracts:
  PerceptionInput  / PerceivedContext
  DecisionInput    / DecisionPlan
  ActionInput      / ActionResult
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ── Artifact store ────────────────────────────────────────────────────────────


class Artifact(BaseModel):
    handle: str           # "art:<16 hex chars>"
    size_bytes: int
    content_type: str = "text/markdown"
    preview: str = ""     # first ~200 chars for display / logging


# ── Memory ────────────────────────────────────────────────────────────────────


class MemoryItem(BaseModel):
    """New-style memory entry with keyword search support."""
    id: str
    kind: Literal["fact", "artifact"]
    text: str                           # full fact text or artifact description
    keywords: list[str]                 # bag-of-words for keyword search
    value: str                          # fact text  OR  artifact handle
    artifact_handle: Optional[str] = None   # set only when kind="artifact"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class MemoryEntry(BaseModel):
    """Old-style key/value memory entry — kept for backwards compatibility."""
    key: str
    value: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class MemoryState(BaseModel):
    """
    Memory store that supports both old-style entries and new-style items.
    Existing code uses .entries / .get() / .as_text().
    New code uses .items for richer keyword-searchable facts.
    """
    entries: list[MemoryEntry] = Field(default_factory=list)
    items: list[MemoryItem] = Field(default_factory=list)

    def get(self, key: str) -> Optional[str]:
        """Retrieve the most recently stored value for a key (case-insensitive)."""
        for e in reversed(self.entries):
            if e.key.lower() == key.lower():
                return e.value
        return None

    def as_text(self) -> str:
        """Render all entries as a human-readable block for LLM prompts."""
        if not self.entries:
            return "  (no memories stored)"
        return "\n".join(f"  [{e.key}]: {e.value}" for e in self.entries)


# ── Shared history ────────────────────────────────────────────────────────────


class HistoryEntry(BaseModel):
    iteration: int
    action: str
    tool_name: Optional[str] = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_summary: str = ""
    artifact_handle: Optional[str] = None   # set when action produced an artifact
    success: bool = True


# ── Perception layer ──────────────────────────────────────────────────────────


class Goal(BaseModel):
    description: str
    status: Literal["open", "done"] = "open"
    attach_artifact_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            v = data.get("attach_artifact_id")
            if isinstance(v, str) and v.strip().lower() in {"null", "none", "n/a", ""}:
                data["attach_artifact_id"] = None
        return data


class PerceptionInput(BaseModel):
    query: str
    iteration: int
    max_iterations: int
    history: list[HistoryEntry] = Field(default_factory=list)
    memory: MemoryState = Field(default_factory=MemoryState)       # old API
    memory_hits: list[MemoryItem] = Field(default_factory=list)    # new API


class PerceivedContext(BaseModel):
    # New-style fields (goal-list model)
    goals: list[Goal] = Field(default_factory=list)
    all_done: bool = False

    # Old-style flat fields — kept so perception.py / decision.py don't break
    goal: str = Field(
        default="",
        description="The user's ultimate objective in one clear sentence",
    )
    progress_summary: str = Field(
        default="",
        description="What has been accomplished so far based on tool results",
    )
    key_facts: list[str] = Field(
        default_factory=list,
        description="Specific facts extracted from tool results",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="What is still needed to produce the final answer",
    )
    is_complete: bool = Field(
        default=False,
        description="True only when all required information is available",
    )
    suggested_answer: Optional[str] = Field(
        default=None,
        description="Draft final answer when is_complete=true, else null",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            v = data.get("suggested_answer")
            if isinstance(v, str) and v.strip().lower() in {"null", "none", "n/a", ""}:
                data["suggested_answer"] = None
        return data


# ── Decision layer ────────────────────────────────────────────────────────────


class DecisionInput(BaseModel):
    perceived: PerceivedContext
    available_tools: list[str]
    iteration: int
    max_iterations: int
    memory: MemoryState = Field(default_factory=MemoryState)       # old API
    query: str = ""                                                  # new API
    memory_hits: list[MemoryItem] = Field(default_factory=list)    # new API
    attached_content: Optional[str] = None                         # new API


class DecisionPlan(BaseModel):
    reasoning: str = Field(
        description="Brief explanation of why this action was chosen (1-2 sentences)"
    )
    action: Literal["tool_call", "remember", "answer"] = Field(
        description=(
            "tool_call = invoke an MCP tool; "
            "remember = persist a fact to durable memory; "
            "answer = deliver the complete final answer"
        )
    )
    # Fields for action=tool_call
    tool_name: Optional[str] = Field(
        default=None,
        description="MCP tool name. Required when action=tool_call.",
    )
    tool_arguments: Optional[dict[str, Any]] = Field(
        default=None,
        description="Tool arguments dict. Required when action=tool_call.",
    )
    # Fields for action=remember
    memory_key: Optional[str] = Field(
        default=None,
        description="Key to store in durable memory. Required when action=remember.",
    )
    memory_value: Optional[str] = Field(
        default=None,
        description="Value to store. Required when action=remember.",
    )
    # Fields for action=answer
    final_answer: Optional[str] = Field(
        default=None,
        description="The complete, well-formatted final answer. Required when action=answer.",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: Any) -> Any:
        """Normalise LLM null-string artefacts to Python None."""
        if not isinstance(data, dict):
            return data
        null_strings = {"null", "none", "n/a", "na", ""}
        for field in (
            "tool_name",
            "tool_arguments",
            "memory_key",
            "memory_value",
            "final_answer",
        ):
            v = data.get(field)
            if isinstance(v, str) and v.strip().lower() in null_strings:
                data[field] = None
        return data


# ── Action layer ──────────────────────────────────────────────────────────────


class ActionInput(BaseModel):
    plan: DecisionPlan


class ActionResult(BaseModel):
    success: bool
    action: str
    tool_name: Optional[str] = None
    result: Any = None
    result_summary: str = ""
    error: Optional[str] = None
    artifact: Optional[Artifact] = None   # set when result was stored as artifact
    memory_stored: bool = False
    is_final: bool = False
    final_answer: Optional[str] = None
