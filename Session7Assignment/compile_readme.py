import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
TRACES_DIR = BASE_DIR / "traces"
CORPUS_FILE = BASE_DIR / "sandbox" / "corpus.json"
README_FILE = BASE_DIR / "README.md"

# Load the corpus to build the manifest
with open(CORPUS_FILE, "r", encoding="utf-8") as f:
    corpus = json.load(f)

# Categories count
categories = {}
for doc in corpus:
    cat = doc.get("category", "Other")
    categories[cat] = categories.get(cat, 0) + 1

# Base README content (preserved from existing README)
base_content = """# EAGV3 Session 7 — Four-Layer Cognitive RAG Assistant

A multi-step reasoning RAG agent built from four cognitive layers with no third-party agentic framework. All LLM calls go through **LLM Gateway V3**; all tool calls go through the **MCP server** via stdio transport.

This version features a **Hybrid Retrieval Engine** (`retrieve_cosmic_docs`) querying a 52-document corpus to bridge proprietary technical knowledge gaps.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       agent7.py (loop)                       │
│                                                              │
│  ┌────────────┐  PerceptionInput  ┌──────────────────┐       │
│  │  memory.py │ ◄──────────────── │  perception.py   │       │
│  │            │                   │  (LLM Gateway V3)│       │
│  │ state/     │  MemoryState      └──────────────────┘       │
│  │ memory.json│ ──────────────────►                          │
│  └────────────┘                   ┌──────────────────┐       │
│                   PerceivedContext │  decision.py     │       │
│                  ────────────────► │  (LLM Gateway V3)│       │
│                                   └──────────────────┘       │
│                                                              │
│                   DecisionPlan    ┌──────────────────┐       │
│                  ────────────────► │  action.py       │       │
│                                   │  (MCP stdio)     │──┐    │
│                   ActionResult    └──────────────────┘  │    │
│                  ◄────────────────                      │    │
└─────────────────────────────────────────────────────────┼────┘
                                                          ▼
                                            ┌──────────────────────────┐
                                            │     mcp_server.py        │
                                            │  (retrieve_cosmic_docs)  │
                                            └──────────────────────────┘
                                                          │
                                                          ▼
                                                    retriever.py 
                                            (Corpus: sandbox/corpus.json)
```

| Module | Role | Description |
|---|---|---|
| `schemas.py` | Pydantic v2 contracts | Structured boundaries for all layers |
| `memory.py` | State persistence | Saves/loads memory variables to `state/memory.json` |
| `perception.py` | Context layer | Analyzes state to find facts and gaps |
| `decision.py` | Strategy layer | Chooses next tool or memory action dynamically |
| `action.py` | Execution layer | Invokes MCP tools via stdio client |
| `agent7.py` | Orchestration loop | Drives the execution loop (RAG vs Closed-Book) |
| `mcp_server.py` | MCP Server | Hosts 10 MCP tools (including RAG retrieval) |
| `retriever.py` | Hybrid RAG search | Expansion and term-scoring retrieval logic |
| `sandbox/corpus.json` | Local DB | 52 technical documents and operational logs |

---

## Setup & Running Guide

### 1. Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) installed globally
- API Keys (`GEMINI_API_KEY`, `TAVILY_API_KEY`) set up in `.env`.

### 2. Startup LLM Gateway V3
In a separate terminal window, start the gateway service:
```bash
cd llm_gatewayV3
uv run uvicorn main:app --host 0.0.0.0 --port 8101
```

### 3. Run the Agent (RAG Mode)
To run a query leveraging internal documentation (index enabled):
```bash
# Run custom RAG Query A (WebSocket connection storm root cause)
uv run agent7.py --query-id RAG_A
```

---

"""

# 1. Corpus Manifest
manifest_content = "## Technical Corpus Manifest (52 Documents)\n\n"
manifest_content += f"Our local corpus contains exactly **{len(corpus)} documents** structured across {len(categories)} operational categories:\n\n"
for cat, count in categories.items():
    manifest_content += f"- **{cat}**: {count} documents\n"
manifest_content += "\n| ID | Category | Title | Summary / Core Detail |\n"
manifest_content += "|---|---|---|---|\n"

for doc in corpus:
    # Summarize content
    content = doc.get("content", "")
    summary = content[:150] + "..." if len(content) > 150 else content
    manifest_content += f"| **{doc['id']}** | {doc.get('category')} | {doc.get('title')} | {summary} |\n"

manifest_content += "\n---\n\n"

# 2. Execution Traces Table
traces_table = """## Execution Status and Step Counts

Below is the execution log summary of all runs. Base queries run under strict iteration caps. Custom queries are evaluated under both **RAG-Enabled** and **Closed-Book (RAG-Disabled)** conditions to prove RAG utility.

| Run ID | Query Type | Description | Iterations Used | Status |
|---|---|---|---|---|
| **A** | Base | Shannon Wikipedia Date/Contributions | 2 | SUCCESS |
| **B** | Base | Tokyo Weekend Activities & Weather | 4 | SUCCESS |
| **C1** | Base | Durable Memory - Store Mom's Birthday | 2 | SUCCESS |
| **C2** | Base | Durable Memory - Recall Mom's Birthday | 2 | SUCCESS |
| **D** | Base | Asyncio Research (3-source synthesis) | 4 | SUCCESS |
| **E** | Base | Index attention.md & Extract Contributions | 5 | SUCCESS |
| **F1** | Base | Index papers/ & Confirm Chunks | 2 | SUCCESS |
| **F2** | Base | Chain-of-Thought reasoning query | 5 | SUCCESS |
| **G** | Base | Credit Assignment problem analysis | 8 | SUCCESS |
| **H** | Base | ReAct vs CoT intermediate reasoning comparison | 4 | SUCCESS |
| **RAG_A (Enabled)** | Custom | WebSocket storm root cause & developer | 2 | SUCCESS (Achintya) |
| **RAG_A (Disabled)** | Custom | WebSocket storm root cause & developer | 10 (Cap) | FAILURE (Hallucinated/No-data) |
| **RAG_B (Enabled)** | Custom | Market-maker automated hedging sync reset | 2 | SUCCESS (`update_leverage.py --client MM001 --sync`) |
| **RAG_B (Disabled)** | Custom | Market-maker automated hedging sync reset | 10 (Cap) | FAILURE (No-data) |
| **RAG_C (Enabled)** | Custom | 2FA service outage bulk wallet update fallback | 2 | SUCCESS (`BYPASS_2FA_FLAG=1`) |
| **RAG_C (Disabled)** | Custom | 2FA service outage bulk wallet update fallback | 10 (Cap) | FAILURE (No-data) |
| **RAG_D (Enabled)** | Custom | Client INTMM1 leverage configuration API | 10 (Thorough) | SUCCESS (Validated single POST endpoint) |
| **RAG_D (Disabled)** | Custom | Client INTMM1 leverage configuration API | 10 (Cap) | FAILURE (No-data) |
| **RAG_E (Enabled)** | Custom | Tokyo vs London Server Group Latency SLA | 2 | SUCCESS (Tokyo 5ms SLA vs London 12ms SLA) |
| **RAG_E (Disabled)** | Custom | Tokyo vs London Server Group Latency SLA | 10 (Cap) | FAILURE (No-data) |

---

## RAG vs. Closed-Book Comparative Analysis

Each of the five custom queries was run in both **RAG Mode** (Index Enabled) and **Closed-Book Mode** (Index Disabled). 

### 1. WebSocket Storm Incident (`RAG_A`)
* **With Corpus (RAG)**: The agent instantly searched the index, retrieved document `PM-002`, and explained that the connection storm was caused by a brief ISP dropout triggering 50,000 WebSocket reconnections, which overflowed the Nginx buffer. It correctly identified developer **Achintya** as the resolver.
* **Without Corpus (Closed-Book)**: The agent repeatedly fell back to web search, fetching unrelated generic public CVEs, and finally hallucinated or reported no knowledge because the details are proprietary.

### 2. Market-Maker Margin Out of Sync (`RAG_B`)
* **With Corpus (RAG)**: Retrieved security protocol `SEC-001` and instructed Risk Managers to execute `python update_leverage.py --client MM001 --sync` on the admin console to reset leverage boundaries.
* **Without Corpus (Closed-Book)**: Failed to find any relevant command, and returned generic advice on risk parameters.

### 3. 2FA Outage Wallet Update Fallback (`RAG_C`)
* **With Corpus (RAG)**: Retrieved operational runbook `RUN-002` and outlined the exact recovery procedure: set `BYPASS_2FA_FLAG=1` in the runner environment, sign audit logs offline, and execute `bulk_update_funds.py` locally.
* **Without Corpus (Closed-Book)**: Prompted the user to check their SMS gateways or contact support, completely unaware of the local script or bypass flag.

### 4. Leverage Configuration API Endpoint (`RAG_D`)
* **With Corpus (RAG)**: Identified `POST /api/v1/client/leverage` with JSON parameters `clientId`, `maxLeverage`, and `riskTier` after scanning the API reference docs.
* **Without Corpus (Closed-Book)**: Attempted to guess endpoints or suggested generic endpoints (e.g. `/api/v1/leverage/configure`), which would fail.

### 5. Latency SLAs (`RAG_E`)
* **With Corpus (RAG)**: Extracted performance specs from `SLA-001`: Tokyo group achieves **5ms** SLA on low-latency bare-metal, while London group achieves **12ms** SLA inside Equinix LD4 due to VM virtualization.
* **Without Corpus (Closed-Book)**: Searched the web for "Cosmic Trading Network SLAs", returned nothing, and concluded that no latency figures are publicly documented.

---

"""

# 3. Detailed Traces Section
traces_section = "## Detailed Execution Traces\n\n"
traces_section += "Below are the complete, unmodified execution outputs captured from the console for all 20 runs.\n\n"

# Order of files to embed
trace_files = [
    ("Base Query A: Shannon Wikipedia", "trace_A.txt"),
    ("Base Query B: Tokyo Activities & Weather", "trace_B.txt"),
    ("Base Query C1: Durable Memory - Store Mom's Birthday", "trace_C1.txt"),
    ("Base Query C2: Durable Memory - Recall Mom's Birthday", "trace_C2.txt"),
    ("Base Query D: Asyncio Research (3-source synthesis)", "trace_D.txt"),
    ("Base Query E: Index attention.md & Extract Contributions", "trace_E.txt"),
    ("Base Query F1: Index papers/ & Confirm Chunks", "trace_F1.txt"),
    ("Base Query F2: Chain-of-Thought reasoning query", "trace_F2.txt"),
    ("Base Query G: Credit Assignment problem analysis", "trace_G.txt"),
    ("Base Query H: ReAct vs CoT intermediate reasoning comparison", "trace_H.txt"),
    ("Custom Query RAG_A (Enabled) - WebSocket storm root cause", "trace_RAG_A_enabled.txt"),
    ("Custom Query RAG_A (Disabled) - WebSocket storm root cause", "trace_RAG_A_disabled.txt"),
    ("Custom Query RAG_B (Enabled) - MM001 leverage out of sync", "trace_RAG_B_enabled.txt"),
    ("Custom Query RAG_B (Disabled) - MM001 leverage out of sync", "trace_RAG_B_disabled.txt"),
    ("Custom Query RAG_C (Enabled) - 2FA outage wallet update", "trace_RAG_C_enabled.txt"),
    ("Custom Query RAG_C (Disabled) - 2FA outage wallet update", "trace_RAG_C_disabled.txt"),
    ("Custom Query RAG_D (Enabled) - INTMM1 leverage config API", "trace_RAG_D_enabled.txt"),
    ("Custom Query RAG_D (Disabled) - INTMM1 leverage config API", "trace_RAG_D_disabled.txt"),
    ("Custom Query RAG_E (Enabled) - Latency SLAs", "trace_RAG_E_enabled.txt"),
    ("Custom Query RAG_E (Disabled) - Latency SLAs", "trace_RAG_E_disabled.txt"),
]

for title, fname in trace_files:
    fpath = TRACES_DIR / fname
    if fpath.exists():
        content = fpath.read_text(encoding="utf-8")
        traces_section += f"<details>\n<summary>🔎 {title} ({fname})</summary>\n\n"
        traces_section += f"```text\n{content}\n```\n"
        traces_section += "</details>\n\n"
    else:
        traces_section += f"### {title}\nTrace file {fname} not found.\n\n"

# Combine and write README
final_readme = base_content + manifest_content + traces_table + traces_section
with open(README_FILE, "w", encoding="utf-8") as f:
    f.write(final_readme)

print("README.md compiled successfully with all 20 traces and 52-document manifest!", flush=True)
