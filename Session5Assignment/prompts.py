"""
Prompt versioning: original (unqualified) vs evaluated (qualified).

This file stores both prompts so the evaluator can show a before/after
comparison against the this.md Prompt Evaluation criteria.
"""

# --- ORIGINAL PROMPT (before evaluation) ---
ORIGINAL_SYSTEM_PROMPT = """
You are a logic puzzle solver. Solve the given problem step by step.

Problem: {problem}

Solve it and give the answer.
"""

# --- QUALIFIED SYSTEM PROMPT (after evaluation via this.md criteria) ---
QUALIFIED_SYSTEM_PROMPT = """
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

Now solve the following problem step by step, using the format above:

{problem}
"""

# --- PROMPT EVALUATION CRITERIA (from this.md) ---
EVALUATION_CRITERIA = {
    "explicit_reasoning": {
        "description": "Does the prompt tell the model to reason step-by-step and explain thinking?",
        "check_for": ["step by step", "think before", "explain", "reason", "never jump"],
    },
    "structured_output": {
        "description": "Does the prompt enforce a predictable, parseable output format?",
        "check_for": ["STEP", "FORMAT", "FINAL_ANSWER", "structure", "exactly this"],
    },
    "tool_separation": {
        "description": "Are reasoning steps clearly separated from computation steps?",
        "check_for": ["ARITHMETIC", "TOOL", "compute", "calculate", "REASONING_TYPE"],
    },
    "conversation_loop": {
        "description": "Can this prompt work in a multi-turn setting with context updates?",
        "check_for": ["prior", "context", "previous", "multi-turn", "new information"],
    },
    "instructional_framing": {
        "description": "Are there format examples or templates to follow?",
        "check_for": ["STEP 1:", "Observation:", "Deduction:", "exactly this", "REASONING_CHAIN"],
    },
    "internal_self_checks": {
        "description": "Does the prompt instruct the model to self-verify intermediate steps?",
        "check_for": ["SELF_CHECK", "verify", "sanity", "still satisfied", "BACKTRACKING"],
    },
    "reasoning_type_awareness": {
        "description": "Does the prompt ask the model to tag or identify reasoning type?",
        "check_for": ["DEDUCTION", "ELIMINATION", "LOGIC", "ARITHMETIC", "reasoning type", "TAG"],
    },
    "fallbacks": {
        "description": "Does the prompt specify behavior when uncertain or tool fails?",
        "check_for": ["CONTRADICTION_FOUND", "UNSOLVABLE", "NEED_INFO", "TOOL_ERROR", "uncertain"],
    },
}
