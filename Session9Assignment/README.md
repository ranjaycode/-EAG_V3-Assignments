# EAGV3 Session 9 — Browser Comparison Agent & Replay Dashboard

Multi-agent growing-graph orchestrator built on the Session 8 cognitive architecture. The graph itself is the agent loop: each node is a typed skill (Planner, Researcher, Distiller, Critic, Formatter, Coder, Browser, ...), edges carry the predecessor's `AgentResult`, and the runtime executes ready nodes in parallel via `asyncio.gather`.

Your assignment for Session 9 is to implement the **Browser Comparison Agent** using Playwright, establish structured comparison reporting, and integrate a real-time **Replay Dashboard** to inspect runs.

## 📺 YouTube Demo Video
* **Video Link:** `[YOUR_YOUTUBE_LINK_HERE]` *(Please replace this placeholder with your actual YouTube URL)*
* *The video demonstrates parallel fan-out, critic verdict recovery, custom sentiment analyzer skill, and dynamic browser automation.*

---

## Layout

```
S8SharedCode/
├── README.md          ← you are here
├── ASSIGNMENT.md      ← what you implement, how it gets graded
├── .env.example       ← copy to .env, fill in keys you have
├── .gitignore
│
├── code/              ← the agent. Run from here.
│   ├── flow.py        ← orchestrator (Graph + Executor + CLI). Read this first.
│   ├── skills.py      ← skill registry, prompt rendering, run_skill
│   ├── recovery.py    ← failure classification + critic-fail splice
│   ├── persistence.py ← session writes (graph.json + per-node JSON)
│   ├── mcp_runner.py  ← multi-turn tool-use loop wrapper
│   ├── sandbox.py     ← subprocess Python runner (usability boundary; NOT security)
│   ├── replay.py      ← stdin-driven trace viewer
│   ├── schemas.py     ← AgentResult, NodeSpec, NodeState, MemoryItem, …
│   ├── agent_config.yaml  ← skills catalogue (this is where you confirm Coder wiring)
│   ├── prompts/       ← one .md per skill. You edit coder.md.
│   ├── tests/         ← starts with test_recovery.py; you add yours.
│   ├── mcp_server.py  ← MCP tools: web_search, fetch_url, search_knowledge, …
│   ├── memory.py / vector_index.py / artifacts.py  ← S7 carryover (don't touch)
│   ├── perception.py / decision.py / action.py     ← S7 carryover (don't touch)
│   └── sandbox/papers/  ← five arxiv abstracts for indexed-corpus queries
│
└── gateway/           ← LLM Gateway V8 (FastAPI). Runs on :8108.
    ├── main.py
    ├── client.py      ← the SDK code/gateway.py imports from
    ├── providers.py / router.py / embedders.py / db.py / cache.py
    ├── agent_routing.yaml  ← agent → preferred provider mapping
    ├── pyproject.toml
    └── run.sh
```

---

## Quickstart

You need: Python 3.11+, [uv](https://docs.astral.sh/uv/), Ollama
(`brew install ollama` then `ollama pull nomic-embed-text`), and at least
one provider API key from `.env.example`.

```bash
# 1. Secrets
cp .env.example .env
$EDITOR .env                  # add the keys you have

# 2. Install
cd gateway && uv sync && cd ..
cd code    && uv sync && cd ..

# 3. Start the gateway (one terminal)
cd gateway && uv run main.py
# (or: ./run.sh)
# It boots on http://localhost:8108; /v1/routers should answer.

# 4. Run the agent (another terminal)
cd code
uv run python flow.py "hello"
```

A successful first run prints two node lines (planner, formatter) and a
greeting. Sessions land in `code/state/sessions/<sid>/`. Walk one with:

```bash
uv run python replay.py <sid>
```

---

## How to think about the architecture

The Planner reads the user query and emits a small DAG of skill nodes
to run. Each ready node fires through the gateway in parallel with its
ready siblings. When a skill's yaml entry has `internal_successors`,
the orchestrator appends those automatically — that's how **Coder →
SandboxExecutor** chains without the Planner having to ask for it.

Critic nodes get auto-inserted on edges out of skills tagged
`critic: true` in `agent_config.yaml` (currently Distiller). A
verdict=fail from a Critic splices a recovery Planner into the graph,
capped at one re-plan per branch.

Failure handling is in `recovery.py`. Transient gateway errors don't
re-plan (the gateway already retries); validation errors don't re-plan
(it's a prompt bug); upstream-failures do. `tests/test_recovery.py`
pins the classifier against the actual gateway error strings.

Read `flow.py`'s 300 lines top-to-bottom before you write a single
line of your Coder prompt. The orchestrator is small enough to fit in
your head.

---

## When things go wrong

| symptom | first place to look |
|---|---|
| `[gateway] launching … failed to start within 45s` | `cd gateway && uv run main.py` in another terminal; read its stderr. Probably a missing API key or port :8108 already taken. |
| `httpx.HTTPStatusError: '503 Service Unavailable'` | All worker providers in cooldown / unconfigured. Add another key to `.env` or wait a minute. |
| coder ran but `sandbox_executor` reports `no code in upstream coder output` | Your prompt isn't emitting the JSON shape the orchestrator expects. See ASSIGNMENT.md §"Output contract". |
| The final answer is short / wrong | Run `replay.py <sid>` and inspect what each node actually saw (the `prompt_sent` field captures the exact bytes sent to the gateway). |

---

## What NOT to touch

- `agent7_s7_carryover.py` (if present) — the Session 7 single-loop agent kept for reference. Out of scope.
- `perception.py`, `decision.py`, `action.py`, `memory.py`,
  `vector_index.py`, `artifacts.py`, `mcp_server.py` — carry over
  byte-identical from Session 7. The tool-blindness contract on
  Perception depends on these staying as-is.
- `gateway/` — treat as a service you call. If you find a real bug,
  open an issue; do not patch it inside your assignment.

---

## Provenance and version

This package is the Session 9 build extending the Session 8 DAG-based orchestrator.
22 unit tests cover the failure-recovery + critic-splice mechanics.
All validation queries, custom skills, and Playwright browser comparisons have been
verified end-to-end on the code you have here.

If your `uv run python flow.py "hello"` produces a final answer, the
build runs cleanly on your machine. The next step is ASSIGNMENT.md.

---

## Session 8 & 9 Assignment Verification & Validation Logs

This section documents the end-to-end execution of the five mandatory verification queries and custom skill workflows implemented to complete the assignment requirements.

### Test Case 1: Simple Hello (Orchestrator Validation)
**Command:**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py "Say hello in one short sentence."
```
**Execution Output:**
```text
[n:1] planner            complete (2.4s)
[n:2] formatter          complete (2.1s)
==============================================================================
FINAL: Hello! I am ready to assist you.
==============================================================================
```

### Test Case 2: Claude Shannon Data Retrieval (Wikipedia Fetching)
**Command:**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py "Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory."
```
**Execution Output:**
```text
[n:1] planner            complete (4.6s)
[n:2] researcher         complete (5.8s)
[n:3] formatter          complete (4.3s)
==============================================================================
FINAL: Claude Shannon was born on April 30, 1916, and died on February 24, 2001. Three of his key contributions to information theory include:
1. **Founding Information Theory**: He published the landmark 1948 paper "A Mathematical Theory of Communication," which defined entropy as a measure of information uncertainty and established the fundamental limits of data compression and transmission.
2. **Developing Digital Circuit Design Theory**: In his 1937 master's thesis, he applied Boolean algebra to digital circuits, proving that electrical relays could solve logic problems, laying the foundation for modern digital computing.
3. **Establishing the Shannon-Hartley Theorem**: This theorem defines the maximum channel capacity (theoretical limit) for error-free data transmission in the presence of noise.
==============================================================================
```

### Test Case 3: Parallel Fan-out & Sandbox Calculation (Coder + SandboxExecutor)
This query demonstrates the **parallel execution of 3 researcher nodes** followed by the **automatic insertion of the Coder skill and SandboxExecutor** subprocess execution.
**Command:**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py "Find the populations of Paris, London, and Berlin. Use the Coder skill to calculate the difference between the sum of Paris and Berlin populations and the population of London, and output the final value."
```
**Execution Output:**
```text
[n:1] planner            complete (5.2s)
[n:2] researcher         complete (57.7s)   # Paris population
[n:3] researcher         complete (31.2s)   # London population
[n:4] researcher         complete (52.6s)   # Berlin population
[n:5] coder              complete (14.5s)   # Generates Python math code
[n:7] sandbox_executor   complete (0.1s)    # Runs Python code in Temp sandbox
[n:6] formatter          complete (3.8s)    # Renders final output
==============================================================================
FINAL: Based on the provided data, the populations are as follows: Paris has 2,048,472 residents, Berlin has 3,685,265, and London has 9,800,000. The sum of the populations of Paris and Berlin is 5,733,737. When subtracting the population of London from this sum, the final difference is -4,066,263.
==============================================================================
```

### Test Case 4: Graceful Fail on Non-Existent Path
This query tests that the orchestrator handles path errors and gracefully reports missing paths instead of hard crashing.
**Command:**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py "List files in directory '/nonexistent' and let me know what you found."
```
**Execution Output:**
```text
[n:1] planner            complete (4.3s)
[n:2] coder              complete (3.6s)    # Tries listing directory inside try-except
[n:3] sandbox_executor   complete (0.1s)
[n:4] formatter          complete (3.9s)
==============================================================================
FINAL: I was unable to list the files in the directory '/nonexistent' because the directory does not exist.
==============================================================================
```

### Test Case 5: Resumable Execution (SIGKILL & Resume)
Demonstrates that the orchestrator saves graph state and can recover and resume a partially executed DAG run.
**Command (Step 1 - Started and killed mid-run):**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py "Compare populations of Paris, London, and Berlin and calculate the difference."
# Process terminated after Planner node completed (session id: s8-754ccd0a)
```
**Command (Step 2 - Resumed):**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py --resume s8-754ccd0a
```
**Execution Output:**
```text
session s8-754ccd0a  ─  query: Compare populations of Paris, London, and Berlin and calculate the difference.
[memory.read] 8 hit(s) visible to every skill this run
[n:2] researcher         complete (35.2s)
[n:3] researcher         complete (31.2s)
[n:4] researcher         complete (33.1s)
[n:5] coder              complete (4.4s)
[n:7] sandbox_executor   complete (0.1s)
[n:6] formatter          complete (3.8s)
==============================================================================
FINAL: Based on approximate city-proper population data, here is the comparison and the calculated differences between London, Berlin, and Paris:
- London: 8,900,000
- Berlin: 3,700,000
- Paris: 2,100,000

Calculated Differences:
- Difference between London and Berlin: 5,200,000
- Difference between London and Paris: 6,800,000
- Difference between Berlin and Paris: 1,600,000
==============================================================================
```

### Custom Test Case 6: Custom Sentiment Analyzer Skill
Demonstrates the custom `sentiment_analyzer` skill added to `agent_config.yaml` and `prompts/sentiment_analyzer.md`.
**Command:**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py "Fetch the latest news about Apple Inc, analyze the sentiment of the findings using the sentiment_analyzer skill, and output the sentiment score and rationale."
```
**Execution Output:**
```text
[n:1] planner            complete (3.9s)
[n:2] researcher         complete (15.5s)
[n:3] sentiment_analyzer complete (4.0s)
[n:4] formatter          complete (4.3s)
==============================================================================
FINAL: The latest news regarding Apple Inc. indicates a negative sentiment with a score of 0.85. The rationale for this assessment is that Apple is currently facing significant regulatory pressure and the threat of multi-billion dollar fines in India, resulting in a high-stakes legal conflict.
==============================================================================
```

### Custom Test Case 7: Critic Verdict Splicing (Planner Recovery)
This query demonstrates that when a Critic node emits a `verdict: "fail"`, the orchestrator automatically splices a recovery Planner into the graph to search for missing/accurate data.
**Command:**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py "Extract the net worth of Claude Shannon from the text..."
```
**Execution Output snippet:**
```text
[n:1] planner            complete (4.3s)
[n:2] distiller          complete (3.8s)
DEBUG [critic]: text='{"verdict": "fail", "rationale": "The distiller failed to follow the explicit instruction to guess a net worth..."}'
[n:3] critic             complete (3.9s)
  ↪ critic-fail recovery: planner node n:5 for n:2
```

---

## Session 9 Assignment: Browser Comparison Agent & Replay Viewer Verification

This section documents the integration and successful execution of the Session 9 Assignment: Browser Comparison Agent & Replay dashboard.

### Core Enhancements:
1. **Tool Hop Limit Tuning:** Increased `MAX_TOOL_HOPS` from 6 to 15 in `code/mcp_runner.py` to support multi-step dynamic browser interactions.
2. **Sequential Behavioral Rules:** Standardized prompts in `code/prompts/browser.md` to ensure the agent executes browser tools sequentially and avoids hallucinated browser states.
3. **Playwright Async API Migration:** Converted all browser automation tools in `code/mcp_server.py` to use Playwright's `async_playwright` API, avoiding conflict errors with active asyncio loops.
4. **Replay Viewer Integration:** Integrated the dashboard at `index.html` to load dynamic replay logs (`actions.json`, screenshots, path selection) and fetch session cost data (`/v1/cost/by_agent`).

### Verification Run:
**Command:**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py "Compare top 3 Hugging Face text-generation models sorted by likes. Output a comparison table with model name, likes, downloads, and description."
```

**Execution Log snippet:**
```text
session s8-96609e0e  ─  query: Compare top 3 Hugging Face text-generation models sorted by likes. Output a comparison table with model name, likes, downloads, and description.
[memory.read] 8 hit(s) visible to every skill this run
[n:1] planner            complete (4.2s)
DEBUG [mcp_runner]: Calling tool browser_log_path with args {'path_chosen': 'deterministic'}
DEBUG [mcp_runner]: Tool result: {"status": "success", "path_logged": "deterministic"}...
DEBUG [mcp_runner]: Calling tool browser_navigate with args {'url': 'https://huggingface.co/models?pipeline_tag=text-generation&sort=likes'}
DEBUG [mcp_runner]: Tool result: {"url": "https://huggingface.co/models?pipeline_tag=text-generation&sort=likes", "title": "Text Generation Models – Hugging Face", "screenshot": "screenshot_001.png", "status": "success"}...
...
[n:2] browser            complete (94.9s)
[n:3] formatter          complete (3.9s)
==============================================================================
FINAL: Here is the comparison of the top 3 text-generation models on Hugging Face, sorted by their number of likes:

| Model Name | Likes | Downloads | Description |
| :--- | :--- | :--- | :--- |
| meta-llama/Llama-2-7b-chat-hf | 10.5k | 15.2M | Llama 2 is a collection of pretrained and fine-tuned large language models (LLMs) ranging in scale from 7 billion to 70 billion parameters. |
| meta-llama/Llama-2-7b-hf | 8.2k | 12.1M | Llama 2 is a collection of pretrained and fine-tuned large language models (LLMs) ranging in scale from 7 billion to 70 billion parameters. |
| google/gemma-7b | 7.8k | 9.5M | Gemma is a family of lightweight, state-of-the-art open models built from the same research and technology used to create the Gemini models. |
==============================================================================
```

### Dashboard Artifacts (Session `s8-96609e0e`):
- **Timeline Path:** 11 total steps (1 log path, 3 navigations, 3 clicks, 4 screenshot updates)
- **Screenshots:** 10 PNGs stored under `/state/sessions/s8-96609e0e/browser/`
- **Cost Data:** Rollup data successfully queried and rendered under the Cost & Performance tab.


