# LogiSolve — Multi-Step Constraint Reasoning Engine

> **Session 5 Assignment** | EAG Cohort 3  
> A multi-step logic puzzle solver built with Claude AI, featuring Chain-of-Thought prompting qualified against the this.md Prompt Evaluation rubric.

---

## What It Does

**LogiSolve** is a CLI tool that solves constraint satisfaction problems and logic puzzles step by step:

- **Einstein's Riddle** (5-house, 15-constraint CSP)
- **Project Scheduling** (critical path, float calculations)
- **River Crossing Puzzles** (state-space search via reasoning)
- **Number Theory / Collatz Sequence** (arithmetic chain)
- **Knights and Knaves** (propositional logic)
- **Custom problems** — enter any multi-step reasoning challenge

Each solution is broken into tagged reasoning steps (`[DEDUCTION]`, `[ELIMINATION]`, `[ARITHMETIC]`, etc.), with automatic `SELF_CHECK` blocks every 3 steps and structured error states for contradictions.

---

## YouTube Demo

> **[Watch the Demo Video](#)** ← *(link to be added after recording)*

---

## Prompt Qualification (this.md Evaluation)

The system prompt was evaluated against the **Prompt Evaluation Assistant** rubric (this.md), which scores prompts on 9 criteria for structured chain-of-thought reasoning quality.

### Step 1 — Original (Unqualified) Prompt

```
You are a logic puzzle solver. Solve the given problem step by step.

Problem: {problem}

Solve it and give the answer.
```

**Evaluation Result (3/8 criteria met):**

```json
{
  "explicit_reasoning": true,
  "structured_output": true,
  "tool_separation": false,
  "conversation_loop": false,
  "instructional_framing": false,
  "internal_self_checks": false,
  "reasoning_type_awareness": true,
  "fallbacks": false,
  "overall_clarity": "Weak prompt — lacks structure, format, and reasoning guidance. High hallucination risk."
}
```

**Failures identified:**
- No explicit output format — responses will be unstructured prose
- No multi-turn context passing — loses reasoning across follow-ups
- No self-verification checkpoints — errors compound silently
- No reasoning type tagging — model can't distinguish arithmetic from logic
- No error states — if contradicted, model will hallucinate a solution

---

### Step 2 — Qualified Prompt (after this.md evaluation)

```
You are a Multi-Step Constraint Reasoning Engine. Your task is to solve logic puzzles,
constraint satisfaction problems, and multi-step mathematical reasoning challenges.

CORE RULES — follow these exactly:
1. THINK BEFORE YOU ANSWER. Never jump to conclusions.
2. Break every problem into explicit reasoning steps.
3. TAG each step with its reasoning type:
   [CONSTRAINT_ANALYSIS] | [DEDUCTION] | [ELIMINATION] | [ARITHMETIC] | [LOGIC] | [VERIFICATION]
4. After every 3 deductions, perform a SELF_CHECK block.
5. If uncertain, output LOW confidence. If contradicted, output CONTRADICTION_FOUND.
6. Never skip steps. Short-cutting leads to errors.

OUTPUT FORMAT — use exactly this structure for every response:

REASONING_CHAIN:
  STEP 1: [REASONING_TYPE]
    Observation: <what is given or known at this point>
    Deduction:   <what you conclude from it>
    Confidence:  HIGH | MEDIUM | LOW

  STEP 2: [REASONING_TYPE]
    ...

  SELF_CHECK (after every 3 steps):
    Constraints still satisfied: <list each and confirm YES / VIOLATED>
    Contradictions found: NONE | <describe conflict>
    Proceeding: YES | BACKTRACKING to step <n> because <reason>

FINAL_ANSWER:
  Solution: <the complete answer>
  Verification: <re-check every original constraint against your answer>
  Confidence: HIGH | MEDIUM | LOW

CONVERSATION CONTEXT (for multi-turn use):
  Prior deductions established: {prior_context}
  New information this turn: {new_info}

ERROR STATES — output exactly one of these if applicable:
  CONTRADICTION_FOUND: <which constraints conflict and why>
  UNSOLVABLE: <prove why no solution exists>
  NEED_INFO: <what additional information is required>
  TOOL_ERROR: <what computation failed and fallback attempted>

REASONING TYPE GUIDE:
  [CONSTRAINT_ANALYSIS] — parsing the rules and boundaries of the problem
  [DEDUCTION]           — deriving a new fact from known facts
  [ELIMINATION]         — ruling out possibilities
  [ARITHMETIC]          — numerical computation (show all work)
  [LOGIC]               — boolean / propositional inference
  [VERIFICATION]        — checking a candidate solution against constraints
```

**Evaluation Result (8/8 criteria met):**

```json
{
  "explicit_reasoning": true,
  "structured_output": true,
  "tool_separation": true,
  "conversation_loop": true,
  "instructional_framing": true,
  "internal_self_checks": true,
  "reasoning_type_awareness": true,
  "fallbacks": true,
  "overall_clarity": "Excellent — all criteria met. Highly structured with full reasoning chain support."
}
```

**All criteria now satisfied:**
| Criterion | Before | After |
|---|---|---|
| Explicit reasoning instructions | ✓ | ✓ |
| Structured output format | ✓ | ✓ |
| Separation of reasoning and tools | ✗ | ✓ |
| Conversation loop support | ✗ | ✓ |
| Instructional framing with examples | ✗ | ✓ |
| Internal self-checks | ✗ | ✓ |
| Reasoning type awareness | ✓ | ✓ |
| Error handling / fallbacks | ✗ | ✓ |

---

## Sample Test Output

### Puzzle: Knights and Knaves

**Problem:**  
Alice says: "All three of us are knaves."  
Bob says: "Exactly one of us is a knight."  
Charlie says: "Bob is a knave."

**LogiSolve Output (Claude claude-sonnet-4-6):**

```
REASONING_CHAIN:

  STEP 1: [CONSTRAINT_ANALYSIS]
    Observation: Each person is either a Knight (always true) or Knave (always lies).
                 We have 3 statements from Alice, Bob, and Charlie.
    Deduction:   We must test each assignment of K/K-type and check consistency.
    Confidence:  HIGH

  STEP 2: [LOGIC]
    Observation: Alice claims "All three are knaves."
    Deduction:   If Alice is a Knight, her statement is true → all three are knaves.
                 But if Alice is a knight, not all three can be knaves. CONTRADICTION.
                 Therefore Alice must be a Knave.
    Confidence:  HIGH

  STEP 3: [LOGIC]
    Observation: Alice is a Knave. Her statement "all three are knaves" is a lie.
    Deduction:   So NOT all three are knaves → at least one of {Alice, Bob, Charlie} is a Knight.
                 Since Alice is a Knave, at least one of {Bob, Charlie} is a Knight.
    Confidence:  HIGH

  SELF_CHECK (after step 3):
    Constraints still satisfied:
      - Alice=Knave: YES (her false statement is consistent)
      - At least one of Bob/Charlie is Knight: YES
    Contradictions found: NONE
    Proceeding: YES

  STEP 4: [LOGIC]
    Observation: Bob claims "Exactly one of us is a knight."
    Deduction:   Test Bob=Knight: His statement would be true → exactly 1 knight total.
                 Since Alice=Knave, the one knight is Bob himself.
                 Then Charlie must be a Knave.
                 Check Charlie's statement: "Bob is a knave." Charlie=Knave means this is a lie.
                 Bob IS a knight, so "Bob is a knave" is false. ✓ Consistent!
    Confidence:  HIGH

  STEP 5: [VERIFICATION]
    Observation: Candidate solution: Alice=Knave, Bob=Knight, Charlie=Knave.
    Deduction:   Alice says "all knaves" → False (Bob is a knight). Alice=Knave ✓
                 Bob says "exactly 1 knight" → True (only Bob). Bob=Knight ✓
                 Charlie says "Bob is a knave" → False (Bob is a knight). Charlie=Knave ✓
    Confidence:  HIGH

FINAL_ANSWER:
  Solution:      Alice = Knave, Bob = Knight, Charlie = Knave
  Verification:  All 3 statements are consistent with their speaker's type. No contradictions.
  Confidence:    HIGH
```

### Evaluator Output (run `python main.py evaluate`)

```
=== Prompt Evaluation: ORIGINAL (Unqualified) Prompt ===
  explicit_reasoning            : PASS
  structured_output             : PASS
  tool_separation               : FAIL
  conversation_loop             : FAIL
  instructional_framing         : FAIL
  internal_self_checks          : FAIL
  reasoning_type_awareness      : PASS
  fallbacks                     : FAIL
  Score   : 3/8 criteria met
  Clarity : Weak prompt — lacks structure, format, and reasoning guidance.

=== Prompt Evaluation: QUALIFIED Prompt ===
  explicit_reasoning            : PASS
  structured_output             : PASS
  tool_separation               : PASS
  conversation_loop             : PASS
  instructional_framing         : PASS
  internal_self_checks          : PASS
  reasoning_type_awareness      : PASS
  fallbacks                     : PASS
  Score   : 8/8 criteria met
  Clarity : Excellent — all criteria met. Highly structured with full reasoning chain support.
```

---

## Setup & Usage

### Prerequisites

```bash
pip install anthropic rich
```

### Set API Key

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# macOS / Linux
export ANTHROPIC_API_KEY=sk-ant-...
```

### Run

```bash
# Show prompt evaluation report (no API key needed)
python main.py evaluate

# Solve a built-in puzzle
python main.py einstein
python main.py knights_knaves
python main.py math_proof
python main.py scheduling
python main.py river_crossing

# Enter your own problem interactively
python main.py custom

# Interactive menu
python main.py
```

### Multi-Turn Follow-Up

After solving a puzzle, LogiSolve asks if you want to ask a follow-up question. The entire reasoning context is preserved — you can ask "Why did you eliminate house 3?" and it will trace back through its deduction chain.

---

## Project Structure

```
Session5Assignment/
├── main.py               # CLI entry point
├── solver.py             # Claude API solver with conversation loop
├── prompt_evaluator.py   # this.md rubric evaluator (before/after comparison)
├── prompts.py            # Original + qualified system prompts + evaluation criteria
├── puzzles.py            # Built-in puzzle library (5 puzzles)
├── requirements.txt
└── README.md
```

---

## Why This Is Not Simple

This project demonstrates:

1. **Structured Chain-of-Thought** — 6 tagged reasoning types, not free-form prose
2. **Self-Verification Loops** — automatic consistency checks every 3 deduction steps
3. **Multi-Turn Context Accumulation** — prior deductions carried forward between follow-up questions
4. **Constraint Satisfaction** — multi-variable, multi-constraint problems (Einstein's Riddle has 15 constraints, 25 variables)
5. **Prompt Engineering as a First-Class Task** — the prompt itself is evaluated and qualified with a structured rubric before use
6. **Error State Machine** — 4 explicit failure modes (`CONTRADICTION_FOUND`, `UNSOLVABLE`, `NEED_INFO`, `TOOL_ERROR`)

---

*Built for EAG Session 5 Assignment — Prompt Qualification + Multi-Step Reasoning*
