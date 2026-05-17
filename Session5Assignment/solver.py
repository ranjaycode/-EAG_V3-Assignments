"""
LogiSolve — Multi-Step Constraint Reasoning Solver.

Uses the qualified Chain-of-Thought prompt to solve logic puzzles via Gemini or Claude API.
Supports single-turn and multi-turn (conversation loop) modes.
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from google import genai as google_genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.spinner import Spinner
    from rich.live import Live
    from rich import box
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

from prompts import QUALIFIED_SYSTEM_PROMPT


class LogiSolver:
    """
    Multi-turn constraint reasoning solver backed by Claude or Gemini.
    Maintains conversation history for context accumulation across turns.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, silent: bool = False):
        # Detect which provider to use
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or (api_key if api_key and api_key.startswith("AIza") else None)

        if self.gemini_key:
            self.provider = "gemini"
            self.api_key = self.gemini_key
            self.model_name = model or "gemini-2.5-flash"
            if not GEMINI_AVAILABLE:
                raise ImportError("google-genai package not installed. Run: pip install google-genai")
            # Use the new google-genai SDK
            self.client = google_genai.Client(api_key=self.api_key)
        elif self.anthropic_key:
            self.provider = "anthropic"
            self.api_key = self.anthropic_key
            self.model_name = model or "claude-3-5-sonnet-20240620"
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            raise ValueError("No API key found. Set GEMINI_API_KEY or ANTHROPIC_API_KEY in your .env file.")

        self.silent = silent  # suppress all terminal output (for API use)
        self.conversation_history: list[dict] = []
        self.prior_context_summary: str = "None"

    def _build_system_prompt(self, new_info: str = "") -> str:
        return QUALIFIED_SYSTEM_PROMPT.replace("{prior_context}", self.prior_context_summary).replace("{new_info}", new_info or "None")

    def solve(self, problem: str, new_info: str = "", stream_output: bool = True) -> str:
        """
        Solve a problem using the qualified Chain-of-Thought prompt.
        Adds the exchange to conversation history for multi-turn use.
        """
        system_prompt = self._build_system_prompt(new_info).replace("{problem}", "")

        user_message = f"Problem to solve:\n\n{problem}"
        if new_info:
            user_message += f"\n\nAdditional information provided this turn:\n{new_info}"

        self.conversation_history.append({"role": "user", "content": user_message})

        if RICH_AVAILABLE and not self.silent:
            console.print()
            console.rule(f"[bold cyan]LogiSolve — Reasoning Engine ({self.provider.upper()})[/bold cyan]")
            console.print(f"[dim]Model: {self.model_name} | Context turns: {len(self.conversation_history)}[/dim]\n")

        response_text = ""

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=self.conversation_history,
                )
                response_text = response.content[0].text
            else:
                # google-genai SDK — system_instruction persists across all turns
                contents = []
                for msg in self.conversation_history:
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": msg["content"]}]})

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        max_output_tokens=4096,
                    ),
                )
                response_text = response.text

        except Exception as e:
            response_text = f"ERROR: {str(e)}"
            if RICH_AVAILABLE:
                console.print(f"[bold red]AI Provider Error:[/bold red] {e}")

        self.conversation_history.append({"role": "assistant", "content": response_text})

        # Summarize established deductions for next turn context
        self._update_context_summary(response_text)

        if not self.silent:
            if RICH_AVAILABLE:
                console.print(Panel(
                    Markdown(response_text),
                    title="[bold green]Step-by-Step Solution[/bold green]",
                    border_style="green",
                    box=box.ROUNDED,
                ))
            else:
                print("\n--- Solution ---")
                print(response_text)
                print("--- End ---\n")

        return response_text

    def follow_up(self, follow_up_question: str) -> str:
        """Ask a follow-up question in the same reasoning context."""
        return self.solve(
            problem=follow_up_question,
            new_info="This is a follow-up to the previously established reasoning chain.",
        )

    def reset_context(self):
        """Clear conversation history and start fresh."""
        self.conversation_history = []
        self.prior_context_summary = "None"
        if RICH_AVAILABLE:
            console.print("[yellow]Context reset. Starting fresh conversation.[/yellow]")

    def _update_context_summary(self, response: str):
        """Extract key deductions from the response to carry forward as context."""
        lines = response.split("\n")
        deductions = [
            line.strip()
            for line in lines
            if "Deduction:" in line or "Solution:" in line or "FINAL_ANSWER" in line
        ]
        if deductions:
            self.prior_context_summary = " | ".join(deductions[:5])  # keep top 5
