"""
memory.py — Durable memory layer.

Reads and writes state/memory.json so facts persist across separate agent
runs. Query C depends on this: run 1 stores the user's profile, run 2
reads it without being told.

All public functions accept and return typed MemoryState / MemoryEntry
objects — no raw dicts cross the module boundary.
"""
from __future__ import annotations

import json
from pathlib import Path

from schemas import MemoryEntry, MemoryState

STATE_DIR = Path(__file__).parent / "state"
_MEMORY_FILE = STATE_DIR / "memory.json"


def load() -> MemoryState:
    """Load memory from disk. Returns an empty MemoryState if the file is absent or corrupt."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not _MEMORY_FILE.exists():
        return MemoryState()
    try:
        raw = json.loads(_MEMORY_FILE.read_text(encoding="utf-8"))
        return MemoryState.model_validate(raw)
    except Exception:
        return MemoryState()


def save(state: MemoryState) -> None:
    """Persist a MemoryState to disk atomically."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _MEMORY_FILE.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def upsert(state: MemoryState, key: str, value: str) -> MemoryState:
    """Add or update a key-value entry, then persist. Returns the updated state."""
    key_lower = key.lower()
    for entry in state.entries:
        if entry.key.lower() == key_lower:
            entry.value = value
            save(state)
            return state
    state.entries.append(MemoryEntry(key=key, value=value))
    save(state)
    return state


def clear_all() -> None:
    """Delete all stored memory. Used for clean assignment re-runs."""
    if _MEMORY_FILE.exists():
        _MEMORY_FILE.unlink()