# EAGV3 Session 10 — Computer-Use Agent & Desktop Automation

Multi-agent growing-graph orchestrator built on the Session 9 cognitive architecture. The graph itself is the agent loop: each node is a typed skill (Planner, Researcher, Distiller, Critic, Formatter, Coder, Browser, Computer-Use, ...), edges carry the predecessor's `AgentResult`, and the runtime executes ready nodes in parallel via `asyncio.gather`.

Assignment for Session 10 is to implement the **Computer-Use Skill** that drops into the multi-agent catalog, and demonstrate it solving three desktop automation tasks respecting the five-layer architecture and cascade discipline.

## 📺 YouTube Demo Video
* **Video Link:** `https://youtu.be/dxSezMGcU0Q` 
* *The video demonstrates parallel fan-out, critic verdict recovery, custom sentiment analyzer skill, browser comparison, and desktop computer-use (Calculator, VS Code, and Canvas).*

---

## Layout

```
Session10Assignment/
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
│   ├── replay.py      ← trace viewer
│   ├── schemas.py     ← AgentResult, NodeSpec, NodeState, MemoryItem, …
│   ├── agent_config.yaml  ← skills catalogue (including computer_use)
│   ├── prompts/       ← one .md per skill (including computer_use.md, coder.md, sentiment_analyzer.md)
│   ├── tests/         ← test suite (including test_recovery.py)
│   ├── mcp_server.py  ← MCP tools (including computer_use tools like computer_launch_app, computer_hotkey, electron_connect, etc.)
│   ├── canvas.html    ← local shape-drawing canvas application
│   └── sandbox/       ← subprocess temporary sandboxing folder
│
└── gateway/           ← LLM Gateway V8 (FastAPI). Runs on :8108.
```

---

## Quickstart

You need: Python 3.11+, [uv](https://docs.astral.sh/uv/), Ollama (`ollama pull nomic-embed-text`), and at least one provider API key in `.env`.

```bash
# 1. Start the gateway
cd gateway && uv run main.py

# 2. Start the dashboard server (which also serves the canvas application)
cd code && uv run python dashboard.py

# 3. Run a query using flow.py
uv run python flow.py "Calculate 15 * 6 using the Calculator app."
```

---

## Session 8 & 9 Assignment Verification Logs

This section preserves the verification logs for prior sessions' tasks.

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
1. Founding Information Theory
2. Developing Digital Circuit Design Theory
3. Establishing the Shannon-Hartley Theorem
==============================================================================
```

### Test Case 3: Parallel Fan-out & Sandbox Calculation (Coder + SandboxExecutor)
**Command:**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py "Find the populations of Paris, London, and Berlin. Use the Coder skill to calculate the difference between the sum of Paris and Berlin populations and the population of London, and output the final value."
```
**Execution Output:**
```text
[n:1] planner            complete (5.2s)
[n:2] researcher         complete (57.7s)   # Paris
[n:3] researcher         complete (31.2s)   # London
[n:4] researcher         complete (52.6s)   # Berlin
[n:5] coder              complete (14.5s)   # Generates Python code
[n:7] sandbox_executor   complete (0.1s)    # Runs Python sandbox
[n:6] formatter          complete (3.8s)    # Renders final output
==============================================================================
FINAL: Based on the provided data, the sum of the populations of Paris and Berlin minus London is -4,066,263.
==============================================================================
```

### Test Case 4: Graceful Fail on Non-Existent Path
**Command:**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py "List files in directory '/nonexistent' and let me know what you found."
```
**Execution Output:**
```text
[n:1] planner            complete (4.3s)
[n:2] coder              complete (3.6s)
[n:3] sandbox_executor   complete (0.1s)
[n:4] formatter          complete (3.9s)
==============================================================================
FINAL: I was unable to list the files in the directory '/nonexistent' because the directory does not exist.
==============================================================================
```

### Test Case 5: Resumable Execution (SIGKILL & Resume)
**Command (Step 2 - Resumed):**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; uv run python flow.py --resume s8-754ccd0a
```
**Execution Output:**
```text
session s8-754ccd0a  ─  query: Compare populations of Paris, London, and Berlin and calculate the difference.
[n:2] researcher         complete (35.2s)
[n:3] researcher         complete (31.2s)
[n:4] researcher         complete (33.1s)
[n:5] coder              complete (4.4s)
[n:7] sandbox_executor   complete (0.1s)
[n:6] formatter          complete (3.8s)
==============================================================================
FINAL: Difference between London and Berlin: 5,200,000, London and Paris: 6,800,000, Berlin and Paris: 1,600,000.
==============================================================================
```

### Custom Test Case 6: Custom Sentiment Analyzer Skill
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
FINAL: The latest news regarding Apple Inc. indicates a negative sentiment with a score of 0.85. The rationale is the significant regulatory pressure in India.
==============================================================================
```

### Custom Test Case 7: Critic Verdict Splicing (Planner Recovery)
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

## Session 10 Assignment: Computer-Use Agent Verification

We successfully implemented a custom `computer_use` skill and tools in the MCP server (`code/mcp_server.py`) to handle OS-level automation using:
- **Layer 2a (Hotkey Automation):** Launching `calc.exe`, typing expressions, copying to clipboard via `Ctrl+C`, and closing the app via `Alt+F4`.
- **Layer 2c (CDP / Electron connection):** Connecting to VS Code on port 9222 and inspecting the monaco-workbench workspace tree and UI container.
- **Layer 3 (Vision-based coordinates):** Opening `canvas.html`, selecting the circle by clicking the center of the canvas `#canvas` element, and changing its color using `#color-picker`.

Every execution was recorded automatically via `start_recording` using `pyautogui` + video capture, and saved to `recording.mp4` in the corresponding session directory.

### Task 1: Calculator Automation (Layer 2a Hotkeys)
**Command:**
```powershell
uv run python flow.py "Calculate 15 * 6 using the Calculator app."
```

**Execution Output:**
```text
session s8-14f6bf9c  ─  query: Calculate 15 * 6 using the Calculator app.
[memory.read] 8 hit(s) visible to every skill this run
[n:1] planner            complete (10.3s)
DEBUG [computer_use]: text='{
  "path_chosen": "deterministic",
  "actions_performed": [
    {"tool": "browser_log_path", "details": "deterministic"},
    {"tool": "computer_launch_app", "details": "calc.exe"},
    {"tool": "computer_get_state", "details": "Verified calculator is active"},
    {"tool": "computer_type", "details": "15*6="},
    {"tool": "computer_hotkey", "details": "['ctrl', 'c']"},
    {"tool": "computer_read_clipboard", "details": "Read 90 from clipboard"},
    {"tool": "computer_hotkey", "details": "['alt', 'f4']"}
  ],
  "result": "90"
}'
[n:2] computer_use       complete (15.8s)
[n:3] formatter          complete (21.3s)
==============================================================================
FINAL: The result of 15 * 6, calculated using the Calculator app, is 90.
==============================================================================
[flow] Stopping screen recording...
[flow] Screen recording saved.
```

### Task 2: VS Code Electron Connection (Layer 2c CDP)
**Command:**
```powershell
uv run python flow.py "Connect to VS Code on port 9222 and verify the editor container exists."
```

**Execution Output:**
```text
session s8-52d0e9e7  ─  query: Connect to VS Code on port 9222 and verify the editor container exists.
[memory.read] 8 hit(s) visible to every skill this run
[n:1] planner            complete (10.3s)
DEBUG [computer_use]: text='{
  "path_chosen": "deterministic",
  "actions_performed": [
    {"tool": "browser_log_path", "details": "deterministic"},
    {"tool": "electron_connect", "details": "Connected to VS Code on port 9222"},
    {"tool": "browser_get_state", "details": "Inspected VS Code UI state"},
    {"tool": "browser_screenshot", "details": "Captured screenshot to verify editor container"}
  ],
  "result": "VS Code connected successfully and editor container verified."
}'
[n:2] computer_use       complete (5.0s)
[n:3] formatter          complete (13.8s)
==============================================================================
FINAL: I have successfully connected to VS Code on port 9222 and verified that the editor container exists.
==============================================================================
[flow] Stopping screen recording...
[flow] Screen recording saved.
```

### Task 3: Canvas Vision Task (Layer 3 Coordinates)
**Command:**
```powershell
uv run python flow.py "Open the local shape-drawing canvas application, click inside the red circle to select it, change its fill color to green using the color picker tool, take a screenshot, and verify the color changed."
```

**Execution Output:**
```text
session s8-e1b64297  ─  query: Open the local shape-drawing canvas application, click inside the red circle to select it, change its fill color to green using the color picker tool, take a screenshot, and verify the color changed.
[memory.read] 8 hit(s) visible to every skill this run
[n:1] planner            complete (10.3s)
DEBUG [computer_use]: text='{
  "path_chosen": "vision",
  "actions_performed": [
    {"tool": "browser_log_path", "details": "Set path to vision"},
    {"tool": "browser_navigate", "details": "Navigated to http://localhost:8118/canvas.html"},
    {"tool": "browser_click", "details": "Clicked the canvas element to select the red circle"},
    {"tool": "browser_type", "details": "Typed #00ff00 into the color picker to change the fill color to green"},
    {"tool": "browser_screenshot", "details": "Captured screenshot to verify the color change"}
  ],
  "result": "The circle was successfully selected and its color was changed to green, verified via screenshot."
}'
[n:2] computer_use       complete (52.8s)
[n:3] formatter          complete (11.7s)
==============================================================================
FINAL: The local shape-drawing canvas application was successfully opened, the red circle was selected, and its fill color was changed to green. The change was verified through a screenshot taken after the update.
==============================================================================
[flow] Stopping screen recording...
[flow] Screen recording saved.
```

### Custom Task 4: System Monitor Integration
**Command:**
```powershell
uv run python flow.py "Check the current system state and report the active window and mouse position."
```

**Execution Output:**
```text
[n:1] planner            complete (12.9s)
DEBUG [mcp_runner]: Calling tool computer_get_state with args {}
DEBUG [mcp_runner]: Tool result: {
  "status": "success",
  "screen_width": 1920,
  "screen_height": 1080,
  "mouse_x": 1798,
  "mouse_y": 869,
  "active_window_title": "Session10Assignment - Antigravity - test_calc.py"
}
[n:2] system_monitor     complete (16.5s)
[n:3] formatter          complete (14.2s)
==============================================================================
FINAL: The current active window is 'Session10Assignment - Antigravity - test_calc.py', and the mouse cursor is currently positioned at coordinates (1798, 869).
==============================================================================
[flow] Stopping screen recording...
[flow] Screen recording saved.
```

---

## 🚀 Enhancements & Robustness Layer: Gateway Cooldown Retries

We resolved a persistent rate-limiting and provider cooldown issue in the gateway. The Gemini provider enforces a **4-second cooldown** between consecutive requests. Fast or parallel execution of graph nodes previously caused immediate `503 Service Unavailable` exceptions, crashing the agent flow.

We implemented a robust retry layer directly inside the gateway client (`gateway/client.py`) and the gateway bridge (`code/gateway.py`):
- Caught `HTTP 503` status codes representing provider unavailability or cooldowns.
- Applied exponential backoff (e.g. 2.5s for embeddings, 4.5s for chat/batch endpoints) and retried up to 5 times.
- This successfully prevents transient errors from breaking the orchestrator runs.

---

## 📊 End-to-End Automated Verification Suite

To verify the correct execution of all 9 tasks, we created a comprehensive test runner script: `code/run_all_session10_verifications.py`. It dynamically manages the life cycle of the gateway, local canvas server, and target Electron app (VS Code on port 9222) to run a complete suite of regression tests.

### Test Verification Table

| # | Task Name | Query | Status | Duration (s) |
|---|-----------|-------|--------|--------------|
| 1 | Base Task 1: Simple Hello (Orchestrator Validation) | `Say hello in one short sentence.` | **PASSED** | 17.13s |
| 2 | Base Task 2: Claude Shannon Data Retrieval (Wikipedia) | `Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory.` | **PASSED** | 83.35s |
| 3 | Base Task 3: Parallel Fan-out & Sandbox Calculation | `Find the populations of Paris, London, and Berlin. Use the Coder skill to calculate the difference between the sum of Paris and Berlin populations and the population of London, and output the final value.` | **PASSED** | 51.89s |
| 4 | Base Task 4: Graceful Fail on Non-Existent Path | `List files in directory '/nonexistent' and let me know what you found.` | **PASSED** | 44.56s |
| 5 | Custom Task 5: Custom Sentiment Analyzer Skill | `Analyze the sentiment of this text: 'I absolutely love this new automated orchestrator! It is incredibly fast and works perfectly every time.'` | **PASSED** | 31.45s |
| 6 | Custom Task 6: Custom System Monitor Skill | `Check the current system state and report the active window and mouse position.` | **PASSED** | 39.88s |
| 7 | Computer-Use Task 1: Calculator Automation (Layer 2a Hotkeys) | `Calculate 15 * 6 using the Calculator app.` | **PASSED** | 42.25s |
| 8 | Computer-Use Task 2: VS Code Electron Connection (Layer 2c CDP) | `Connect to VS Code on port 9222 and verify the editor container exists.` | **PASSED** | 24.83s |
| 9 | Computer-Use Task 3: Canvas Vision Task (Layer 3 Coordinates) | `Open the local shape-drawing canvas application, click inside the red circle to select it, change its fill color to green using the color picker tool, take a screenshot, and verify the color changed.` | **PASSED** | 37.29s |

*Full log of the verification run has been saved to `code/session10_verification_report.md`.*
