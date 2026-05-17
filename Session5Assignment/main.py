"""
LogiSolve — CLI Entry Point.

Usage:
  python main.py                    # interactive puzzle selector
  python main.py evaluate           # show prompt qualification report
  python main.py solve <puzzle_id>  # solve a built-in puzzle
  python main.py custom             # enter your own problem

Puzzles: einstein, scheduling, river_crossing, math_proof, knights_knaves
"""

import sys
import os

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import box
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


def print_banner():
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold cyan]LogiSolve[/bold cyan]\n"
            "[dim]Multi-Step Constraint Reasoning Engine[/dim]\n"
            "[dim]Powered by Claude with Chain-of-Thought prompting[/dim]",
            border_style="cyan",
            box=box.DOUBLE,
        ))
    else:
        print("\n" + "=" * 50)
        print("  LogiSolve — Multi-Step Reasoning Engine")
        print("  Powered by Claude + Chain-of-Thought Prompting")
        print("=" * 50 + "\n")


def show_puzzle_menu():
    from puzzles import PUZZLES

    if RICH_AVAILABLE:
        table = Table(title="Available Puzzles", box=box.ROUNDED, show_header=True)
        table.add_column("ID", style="bold cyan", width=16)
        table.add_column("Name", width=28)
        table.add_column("Category", width=24)
        table.add_column("Difficulty", width=10)
        for pid, data in PUZZLES.items():
            color = {"easy": "green", "medium": "yellow", "hard": "red"}.get(data["difficulty"], "white")
            table.add_row(
                pid, data["name"], data["category"],
                f"[{color}]{data['difficulty']}[/{color}]"
            )
        console.print(table)
    else:
        print("\nAvailable puzzles:")
        from puzzles import PUZZLES
        for pid, data in PUZZLES.items():
            print(f"  {pid:20s} {data['name']} ({data['difficulty']})")


def run_evaluate():
    from prompt_evaluator import run_comparison
    run_comparison()


def run_solver(puzzle_id: str):
    from puzzles import PUZZLES
    from solver import LogiSolver

    if puzzle_id not in PUZZLES:
        print(f"Unknown puzzle: '{puzzle_id}'. Run without arguments to see available puzzles.")
        sys.exit(1)

    puzzle = PUZZLES[puzzle_id]

    if RICH_AVAILABLE:
        console.print(Panel(
            f"[bold]{puzzle['name']}[/bold]\n"
            f"[dim]Category: {puzzle['category']} | Difficulty: {puzzle['difficulty']}[/dim]\n\n"
            + puzzle["problem"],
            title="[cyan]Problem Statement[/cyan]",
            border_style="blue",
        ))
    else:
        print(f"\n--- {puzzle['name']} ---")
        print(puzzle["problem"])

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("\nAPI KEY not set. Set either ANTHROPIC_API_KEY or GEMINI_API_KEY in your environment.")
        print("  Windows: $env:GEMINI_API_KEY='your-key'")
        sys.exit(1)

    solver = LogiSolver(api_key=api_key)
    solver.solve(puzzle["problem"])

    # Multi-turn follow-up loop
    try:
        if RICH_AVAILABLE:
            while Confirm.ask("\n[cyan]Ask a follow-up question?[/cyan]", default=False):
                question = Prompt.ask("[cyan]Your question[/cyan]")
                solver.follow_up(question)
        else:
            while True:
                ans = input("\nAsk a follow-up? (y/n): ").strip().lower()
                if ans != "y":
                    break
                question = input("Your question: ").strip()
                solver.follow_up(question)
    except (EOFError, KeyboardInterrupt):
        pass


def run_custom():
    from solver import LogiSolver

    if RICH_AVAILABLE:
        console.print("[bold]Enter your custom problem.[/bold] Type END on a new line when done.\n")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        problem = "\n".join(lines)
    else:
        print("Enter your problem (type END on a new line when done):")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        problem = "\n".join(lines)

    if not problem.strip():
        print("No problem entered.")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("\nAPI KEY not set. Set either ANTHROPIC_API_KEY or GEMINI_API_KEY in your environment.")
        sys.exit(1)

    solver = LogiSolver(api_key=api_key)
    solver.solve(problem)


def main():
    print_banner()
    args = sys.argv[1:]

    if not args:
        # Interactive mode
        show_puzzle_menu()
        if RICH_AVAILABLE:
            choice = Prompt.ask(
                "\n[cyan]Choose mode[/cyan]",
                choices=["evaluate", "einstein", "scheduling", "river_crossing", "math_proof", "knights_knaves", "custom"],
                default="evaluate",
            )
        else:
            choice = input("\nEnter puzzle ID, 'evaluate', or 'custom': ").strip()
        args = [choice]

    command = args[0].lower()

    if command == "evaluate":
        run_evaluate()
    elif command == "custom":
        run_custom()
    else:
        run_solver(command)


if __name__ == "__main__":
    main()
