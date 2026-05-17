"""
Prompt Evaluator — implements the this.md Prompt Evaluation Assistant.

Evaluates any system prompt against 9 structured criteria and outputs a JSON report.
Shows the before/after scores for the original vs qualified prompts.
"""

import json
from prompts import ORIGINAL_SYSTEM_PROMPT, QUALIFIED_SYSTEM_PROMPT, EVALUATION_CRITERIA

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.json import JSON
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def evaluate_prompt(prompt: str) -> dict:
    """
    Score a prompt against the 9 criteria from this.md.
    Returns a structured evaluation dict.
    """
    prompt_lower = prompt.lower()
    results = {}

    for criterion, meta in EVALUATION_CRITERIA.items():
        matched = any(kw.lower() in prompt_lower for kw in meta["check_for"])
        results[criterion] = matched

    # Overall clarity narrative
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    if passed == total:
        clarity = "Excellent — all criteria met. Highly structured with full reasoning chain support."
    elif passed >= 6:
        missing = [k for k, v in results.items() if not v]
        clarity = f"Good structure, but missing: {', '.join(missing)}. Add these to reduce hallucination."
    elif passed >= 4:
        missing = [k for k, v in results.items() if not v]
        clarity = f"Partial structure. Significant gaps in: {', '.join(missing)}. LLM will likely drift."
    else:
        clarity = "Weak prompt — lacks structure, format, and reasoning guidance. High hallucination risk."

    results["overall_clarity"] = clarity
    results["score"] = f"{passed}/{total} criteria met"
    return results


def print_evaluation_report(prompt_name: str, prompt: str, results: dict):
    """Print the evaluation report, using rich if available."""
    if RICH_AVAILABLE:
        _print_rich(prompt_name, results)
    else:
        _print_plain(prompt_name, results)


def _print_rich(prompt_name: str, results: dict):
    console = Console(highlight=False)
    console.print(f"\n[bold cyan]Prompt Evaluation: {prompt_name}[/bold cyan]")

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta")
    table.add_column("Criterion", style="dim", width=30)
    table.add_column("Result", justify="center", width=10)

    criteria_order = [
        "explicit_reasoning", "structured_output", "tool_separation",
        "conversation_loop", "instructional_framing", "internal_self_checks",
        "reasoning_type_awareness", "fallbacks",
    ]

    for key in criteria_order:
        val = results.get(key, False)
        icon = "[green]PASS[/green]" if val else "[red]FAIL[/red]"
        table.add_row(key.replace("_", " ").title(), icon)

    console.print(table)
    console.print(f"[bold]Score:[/bold] {results.get('score')}")
    console.print(f"[bold]Clarity:[/bold] {results.get('overall_clarity')}\n")


def _print_plain(prompt_name: str, results: dict):
    print(f"\n=== Prompt Evaluation: {prompt_name} ===")
    criteria_order = [
        "explicit_reasoning", "structured_output", "tool_separation",
        "conversation_loop", "instructional_framing", "internal_self_checks",
        "reasoning_type_awareness", "fallbacks",
    ]
    for key in criteria_order:
        val = results.get(key, False)
        print(f"  {key:30s}: {'PASS' if val else 'FAIL'}")
    print(f"  Score   : {results.get('score')}")
    print(f"  Clarity : {results.get('overall_clarity')}\n")


def run_comparison():
    """Run full before/after evaluation and print comparison."""
    if RICH_AVAILABLE:
        console = Console()
        console.rule("[bold yellow]PROMPT QUALIFICATION REPORT (this.md criteria)[/bold yellow]")
    else:
        print("\n" + "=" * 60)
        print("   PROMPT QUALIFICATION REPORT (this.md criteria)")
        print("=" * 60)

    original_results = evaluate_prompt(ORIGINAL_SYSTEM_PROMPT)
    qualified_results = evaluate_prompt(QUALIFIED_SYSTEM_PROMPT)

    print_evaluation_report("ORIGINAL (Unqualified) Prompt", ORIGINAL_SYSTEM_PROMPT, original_results)
    print_evaluation_report("QUALIFIED Prompt (after this.md evaluation)", QUALIFIED_SYSTEM_PROMPT, qualified_results)

    # Print JSON outputs
    def clean(r):
        return {k: v for k, v in r.items() if k not in ("score",)}

    print("\n--- Original Prompt Evaluation JSON ---")
    print(json.dumps(clean(original_results), indent=2))

    print("\n--- Qualified Prompt Evaluation JSON ---")
    print(json.dumps(clean(qualified_results), indent=2))

    return original_results, qualified_results


if __name__ == "__main__":
    run_comparison()
