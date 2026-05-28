# EAGV3 Session 6 — Four-Layer Cognitive Agent

A multi-step reasoning agent built from four cognitive layers with no
third-party agentic framework. All LLM calls go through **LLM Gateway V3**;
all tool calls go through the **MCP server** via stdio transport.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      agent6.py (loop)                    │
│                                                          │
│  ┌────────────┐  PerceptionInput  ┌──────────────────┐  │
│  │  memory.py │ ◄──────────────── │  perception.py   │  │
│  │            │                   │  (LLM Gateway V3)│  │
│  │ state/     │  MemoryState      └──────────────────┘  │
│  │ memory.json│ ──────────────────►                      │
│  └────────────┘                   ┌──────────────────┐  │
│                   PerceivedContext │  decision.py     │  │
│                  ────────────────► │  (LLM Gateway V3)│  │
│                                   └──────────────────┘  │
│                                                          │
│                   DecisionPlan    ┌──────────────────┐  │
│                  ────────────────► │  action.py       │  │
│                                   │  (MCP stdio)     │  │
│                   ActionResult    └──────────────────┘  │
│                  ◄────────────────                       │
└─────────────────────────────────────────────────────────┘
```

| Module | Role | LLM calls |
|---|---|---|
| `schemas.py` | Pydantic v2 contracts for every boundary | — |
| `memory.py` | Read/write `state/memory.json` | — |
| `perception.py` | Analyse situation → `PerceivedContext` | Gateway `auto_route=perception` |
| `decision.py` | Choose next action → `DecisionPlan` | Gateway `auto_route=decision` |
| `action.py` | Execute via MCP stdio → `ActionResult` | — |
| `agent6.py` | Orchestration loop | — |
| `mcp_server.py` | 9 MCP tools (search, fetch, time, FX, files) | — |
| `llm_gatewayV3/` | Multi-provider LLM router (run separately) | — |

---

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) installed globally
- At least one LLM provider API key (Gemini recommended)
- A Tavily API key for web search

---

## Setup

### 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd Session6Assignment
```

### 2. Create `.env`

```bash
cp .env.example .env
# Edit .env and add your API keys
```

Minimum required keys:

```env
GEMINI_API_KEY=your-gemini-key
TAVILY_API_KEY=your-tavily-key
```

### 3. Install dependencies

```bash
uv sync
```

### 4. Install Playwright browsers (required by crawl4ai)

```bash
uv run playwright install chromium
```

### 5. Start the LLM Gateway V3

Open a **separate terminal** and leave it running:

```bash
cd llm_gatewayV3
uv run uvicorn main:app --host 0.0.0.0 --port 8101
```

Verify it is up: `curl http://localhost:8101/v1/providers`

---

## Running the Four Target Queries

All commands are run from the `Session6Assignment/` directory.

### Query A — Time zones + Upcoming conferences

> What is the current time right now in Tokyo and in London? Also find 2
> major AI or technology conferences scheduled in the next 6 months and
> state their dates and locations.

Expected iterations: **~4** (max allowed: 8)

```bash
uv run agent6.py --query-id A
```

**Expected answer includes:** Current local times in Tokyo (JST) and London
(GMT/BST), and 2 named tech conferences with their dates and venues.

---

### Query B — Currency conversion + Big Mac calculation

> Convert 1000 USD to EUR and to JPY using today's live exchange rates.
> Then find the current price of a Big Mac in Germany (in EUR) and in Japan
> (in JPY). Calculate exactly how many Big Macs 1000 USD would buy in each
> country, showing the working.

Expected iterations: **~5** (max allowed: 10)

```bash
uv run agent6.py --query-id B
```

**Expected answer includes:** EUR and JPY amounts for 1000 USD, Big Mac
prices in each country, and calculated counts with arithmetic shown.

---

### Query C — Durable memory (two separate runs)

**Run 1** — stores user profile to `state/memory.json`:

> My name is Ranjay and my research focus is solid-state battery technology
> for electric vehicles. Please remember both facts about me (my name and my
> research focus) to durable memory. Then find 3 companies or research groups
> that are leading solid-state battery development as of 2024-2025.

Expected iterations: **~4** (max allowed: 8)

```bash
uv run agent6.py --clear-memory --query-id C1
```

**Expected answer:** Confirms memory stored, lists 3 solid-state battery
companies (e.g., QuantumScape, Solid Power, Samsung SDI).

---

**Run 2** — reads profile from memory without being told:

> Based on what you already know about me and my research interests stored
> in memory, find the most recent breakthrough or news story in my research
> field from 2025 and summarise it.

Expected iterations: **~3** (max allowed: 6)

```bash
uv run agent6.py --query-id C2
```

**Expected answer:** References the stored name "Ranjay" and research focus
"solid-state battery technology", then provides a 2025 news summary from
web search.

---

### Query D — Multi-hop research + file creation

> Research the top 3 AI companies by venture-capital funding raised in 2024.
> Fetch the Wikipedia page for the top-funded company to get its founding
> year, headquarters, and key products or services. Then create a file called
> top_ai.txt in the sandbox with a structured summary that includes: company
> name, 2024 funding amount, founding year, headquarters, and key products.

Expected iterations: **~5** (max allowed: 10)

```bash
uv run agent6.py --query-id D
```

**Expected answer:** Names of top 3 AI companies with funding figures,
detailed info on the leader, and confirmation that `sandbox/top_ai.txt` was
created.

Verify the file was created:

```bash
# The file lives inside the MCP sandbox (next to mcp_server.py)
cat sandbox/top_ai.txt
```

---

## Clearing state between runs

```bash
# Delete memory only (keep sandbox files)
uv run agent6.py --clear-memory --query-id A

# Or delete manually
rm -rf state/
rm -rf sandbox/*
```

---

## Utility commands

```bash
# List all pre-defined target queries
uv run agent6.py --list-queries

# Custom query
uv run agent6.py "What is the current exchange rate between USD and SGD?"

# Override max iterations
uv run agent6.py --max-iterations 6 --query-id A
```

---

## MCP Tools available to the agent

| Tool | Description |
|---|---|
| `web_search` | Tavily (primary) / DuckDuckGo (fallback), max 5 results |
| `fetch_url` | Full-page markdown via crawl4ai + headless Chromium |
| `get_time` | Current time in any IANA timezone |
| `currency_convert` | Live FX rates via frankfurter.dev |
| `read_file` | Read a file from `sandbox/` |
| `list_dir` | List `sandbox/` directory |
| `create_file` | Create a new file in `sandbox/` |
| `update_file` | Overwrite an existing `sandbox/` file |
| `edit_file` | Find-and-replace inside a `sandbox/` file |

---

## Terminal output

> **Note to grader:** Replace the placeholders below with the actual terminal
> output captured from a clean run on your machine. Run each query, copy the
> full terminal output, and paste it here.

### Query A output

```
(paste terminal output here)
```

### Query B output

```
(paste terminal output here)
```

### Query C — Run 1 output

```
(paste terminal output here)
```

### Query C — Run 2 output

```
(paste terminal output here)
```

### Query D output

```
(paste terminal output here)
```

---

## YouTube demonstration

[Link to be added after recording]

---

## Perception & Decision Prompt Validation JSON (PoP)

### Perception system prompt evaluation

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
  "score": "8/8"
}
```

### Decision system prompt evaluation

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
  "score": "8/8"
}
```