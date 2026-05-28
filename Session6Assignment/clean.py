"""
clean.py — Reset agent state between assignment attempts.

Deletes state/memory.json and clears sandbox/ contents.
Run before a fresh assignment attempt to ensure clean state.

Usage:
    uv run clean.py              # clear memory + sandbox
    uv run clean.py --memory     # clear memory only
    uv run clean.py --sandbox    # clear sandbox only
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
STATE_FILE = ROOT / "state" / "memory.json"
SANDBOX_DIR = ROOT / "sandbox"


def clear_memory() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print(f"✓ Deleted {STATE_FILE}")
    else:
        print(f"  (no memory file at {STATE_FILE})")


def clear_sandbox() -> None:
    if SANDBOX_DIR.exists():
        for item in SANDBOX_DIR.iterdir():
            if item.name == ".gitkeep":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            print(f"✓ Removed {item}")
    else:
        print(f"  (sandbox/ does not exist)")


def main() -> None:
    p = argparse.ArgumentParser(description="Reset agent state")
    p.add_argument("--memory", action="store_true", help="Clear memory only")
    p.add_argument("--sandbox", action="store_true", help="Clear sandbox only")
    args = p.parse_args()

    if args.memory:
        clear_memory()
    elif args.sandbox:
        clear_sandbox()
    else:
        clear_memory()
        clear_sandbox()
        print("✓ State reset complete.")


if __name__ == "__main__":
    main()
