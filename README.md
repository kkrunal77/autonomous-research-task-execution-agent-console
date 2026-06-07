# Autonomous Research Agent Console 🤖

This repository contains a clean-room, custom implementation of an **Autonomous Research & Task Execution Agent** built from scratch for Assignment 7. 

The system features an interactive, premium **Web Dashboard** to run and monitor the agent, which implements a four-layer cognitive loop (**Perception**, **Decision**, **Action**, and **Memory**) strictly validated via **Pydantic v2** contracts.

---

## 🏗️ System Architecture

The project is structured as a modular, stateful agentic system composed of three primary layers working in unison:

```
                  ┌─────────────────────────────────┐
                  │           User Query            │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │    Cognitive Loop (agent7.py)   │
                  │  Perception → Decision → Action │
                  └────────────────┬────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
       ┌────────────────────────┐    ┌────────────────────────┐
       │   mcp_server.py (stdio)│    │ llm_gatewayV3 (HTTP)   │
       │   ─ Web Search (Tavily)│    │ ─ 2-Tier Auto Routing  │
       │   ─ Crawler (crawl4ai) │    │ ─ Rate Limit Queueing  │
       │   ─ Vector DB Retrieval│    │ ─ Cache & JSON Schema  │
       │   ─ Sandbox File I/O   │    │                        │
       └────────────────────────┘    └────────────────────────┘
```

### 1. The Four-Layer Cognitive Loop (`agent7.py`)
The agent runs an iterative execution loop matching the Human-in-the-Loop agent paradigm, converging on a final answer within a hard cap of 8 iterations:
- **Perception Layer ([`perception.py`](perception.py))**: Classifies query intent, extracts entities, and detects whether tools or persistent memory are needed.
- **Decision Layer ([`decision.py`](decision.py))**: A convergent state machine (Brain) that decides the next best action (`search_web`, `crawl_page`, `retrieve_context`, `recall_memory`, `save_memory`, or `final_answer`) based on Pydantic v2 validation contracts.
- **Action Layer ([`action.py`](action.py))**: Connects to the local MCP server over stdio to execute tools and returns unified, structured outputs.
- **Memory Layer ([`memory.py`](memory.py))**: Manages persistent JSON memory state (`state/memory.json`) and historical steps (`state/history.json`).

### 2. Unified LLM Gateway ([`llm_gatewayV3/`](llm_gatewayV3))
A FastAPI service running on **port 8101** that acts as the orchestration layer for all LLM calls:
- **2-Tier Routing**: Automatically classifies inputs into `TINY`, `LARGE`, or `HUGE` tiers using a lightweight router pool and selects the optimal worker provider (Ollama, Gemini, NVIDIA, Groq, Cerebras, etc.).
- **Rate-Limit Queuing & Self-Healing**: Automatically catches rate limits (such as Gemini 429 quota exhaustion) and blocks incoming requests to wait out the cooldown/sliding-window reset period, ensuring the agent client never crashes due to transient rate limits.
- **Structured Validation**: Validates output conformity against JSON schemas with automatic single-shot retry formatting.

### 3. MCP Tool Server ([`mcp_server.py`](mcp_server.py))
Exposes the agent's real-world tools over standard Model Context Protocol (stdio transport):
- **Web & Crawler Tools**: `web_search` (primary Tavily with DuckDuckGo fallback) and `fetch_url` (Crawl4AI scraping).
- **RAG & Filesystem**: Local vector context search (`retrieve_context`), document indexing (`index_document`), and safe sandboxed file I/O operations restricted to `./sandbox/`.

---

## 🖥️ Web Console Dashboard

Below is the interface of the agent console. It runs locally and provides real-time SSE console streaming, an active memory database viewer, and step timeline history.

![Autonomous Research Agent Console](screenshot.png)

---

## 🚀 How to Setup and Run

### 1. Prerequisites
- **Python 3.11+**
- **`uv`** (fast Python dependency manager)
- A `.env` file containing required credentials (e.g. `TAVILY_API_KEY`)

### 2. Run the Web Dashboard (Recommended)
Launch the interactive console in your browser:
```bash
uv run uvicorn web_server:app --host 0.0.0.0 --port 8102
```
Open **[http://localhost:8102](http://localhost:8102)** to run queries, clear state, and view the inspector live.

### 3. Run via CLI (Alternative)
You can also run individual queries directly in your shell:
```bash
# Query A: Web Research
uv run python agent7.py "Find latest AI regulations in India and summarize key changes"

# Query B: Multi-Hop Reasoning
uv run python agent7.py "Find top open-source vector databases and compare licensing"

# Query C (Run 1): Save to Memory
uv run python agent7.py "Remember that my preferred database is PostgreSQL"

# Query C (Run 2): Recall from Memory
uv run python agent7.py "What database do I prefer?"

# Query D: Tool Chaining
uv run python agent7.py "Find best MCP servers for browser automation and explain installation"
```

---

## 📊 Verification Matrix & Convergence

The agent executes all queries successfully under the hard limit of **8 iterations** (usually converging in 1–5 iterations):

| Target Query | Cognitive Intent | Iteration Count | Status |
| :--- | :--- | :---: | :---: |
| **Query A** | Web Research | **3** | **PASSED** |
| **Query B** | Multi-Hop Reasoning | **5** | **PASSED** |
| **Query C (Run 1)** | Durable Memory (Write) | **1** | **PASSED** |
| **Query C (Run 2)** | Durable Memory (Read) | **2** | **PASSED** |
| **Query D** | Tool Chaining | **3** | **PASSED** |
| **Query E (RAG 1)** | RAG Semantic (Clean Air system Kyoto) | **2** | **PASSED** |
| **Query F (RAG 2)** | RAG Semantic (Underground messages) | **2** | **PASSED** |
| **Query G (RAG 3)** | RAG Direct (Aegis shield power source) | **2** | **PASSED** |
| **Query H (RAG 4)** | RAG Direct (Chronos lead scientist) | **2** | **PASSED** |
| **Query I (RAG 5)** | RAG Direct (Zephyr payload capacity) | **2** | **PASSED** |

---

## 🗂️ RAG Application & Local Document Corpus

To fulfill the requirements of a real RAG application, we have integrated a local semantic search database running over a corpus of **55 documents** stored in the [corpus/](corpus) directory.

### 📋 Corpus Manifest
- **Specialized Knowledge Files (5 files)**:
  - [doc_01_aether_9.txt](corpus/doc_01_aether_9.txt): Fictional atmospheric carbon scrubbing system (Aether-9) in New Kyoto.
  - [doc_02_whisper_net.txt](corpus/doc_02_whisper_net.txt): Fictional subterranean acoustic communication framework (Whisper-Net) for military silos.
  - [doc_03_aegis_power.txt](corpus/doc_03_aegis_power.txt): Fictional system specifications for Aegis shielding deuterium fusion power source.
  - [doc_04_chronos_personnel.txt](corpus/doc_04_chronos_personnel.txt): Dr. Evelyn Thorne's profile as lead scientist and director of Chronos temporal engine.
  - [doc_05_zephyr_payload.txt](corpus/doc_05_zephyr_payload.txt): Zephyr heavy lifter drone cargo specs (12 metric tons capacity).
- **Fictional System Logs (50 files)**:
  - `doc_06_system_log.txt` through `doc_55_system_log.txt`: Outlining mock maintenance schedules, temperatures, power draws, and operational technician groups to meet the 50+ document constraint.

### 🔍 Designed RAG Queries (E through I)
We designed 5 specific queries against this local corpus. Each query retrieves the correct answer when the corpus index is active, and fails completely when the corpus is removed.

1. **Query E (RAG 1 - Semantic Recall)**
   - **Verbatim Query**: `"What is the name of the system designed to clean the air in New Kyoto?"`
   - **Semantic Aspect**: The query uses the phrase `"clean the air"` which does not appear verbatim in `doc_01_aether_9.txt`. The document uses `"atmospheric carbon scrubbing facility"` and `"clean-air initiative"`.
   - **Successful Answer**: `Aether-9 Atmospheric Scrubbing Facility` (from `doc_01_aether_9.txt`).
   - **No-Corpus Behavior**: Fails to retrieve any context and outputs an empty answer (as the query targets private local fictional systems).

2. **Query F (RAG 2 - Semantic Recall)**
   - **Verbatim Query**: `"How do underground military silos send messages to each other without cables?"`
   - **Semantic Aspect**: The query uses `"send messages to each other without cables"`. The matching document `doc_02_whisper_net.txt` uses `"acoustic communication framework"` and `"transmitted through rock layers"`.
   - **Successful Answer**: `Project Whisper-Net Subterranean System` via acoustic resonance.
   - **No-Corpus Behavior**: Fails completely (returns 0 retrieved characters and no answer).

3. **Query G (RAG 3 - Direct Retrieval)**
   - **Verbatim Query**: `"What is the primary power source of the Aegis shielding system?"`
   - **Successful Answer**: `central deuterium fusion reactor` (from `doc_03_aegis_power.txt`).
   - **No-Corpus Behavior**: Fails completely.

4. **Query H (RAG 4 - Direct Retrieval)**
   - **Verbatim Query**: `"Who is the lead scientist for the Chronos project?"`
   - **Successful Answer**: `Dr. Evelyn Thorne` (from `doc_04_chronos_personnel.txt`).
   - **No-Corpus Behavior**: Fails completely.

5. **Query I (RAG 5 - Direct Retrieval)**
   - **Verbatim Query**: `"What is the maximum payload capacity of the Zephyr heavy lifter drone?"`
   - **Successful Answer**: `12 metric tons of cargo` (from `doc_05_zephyr_payload.txt`).
   - **No-Corpus Behavior**: Fails completely.

---

## 📜 Complete Benchmark Traces & No-Corpus Comparisons

All traces generated during the end-to-end benchmark execution are stored under the [traces/](traces) directory:

### 8 Base Traces:
- [Query A Trace (Web Research)](traces/query_a.txt)
- [Query B Trace (Multi-Hop Reasoning)](traces/query_b.txt)
- [Query C (Save) Trace](traces/query_c_save.txt)
- [Query C (Recall) Trace](traces/query_c_recall.txt)
- [Query D Trace (Tool Chaining)](traces/query_d.txt)
- [Query E Trace (RAG Semantic - With Corpus)](traces/query_e_with_corpus.txt)
- [Query F Trace (RAG Semantic - With Corpus)](traces/query_f_with_corpus.txt)
- [Query G Trace (RAG Direct - With Corpus)](traces/query_g_with_corpus.txt)

### 5 Custom RAG No-Corpus Comparisons:
- **Query E (Kyoto Carbon Scrubbing)**:
  - [With Corpus Trace](traces/query_e_with_corpus.txt) vs [No Corpus Trace (Fails)](traces/query_e_no_corpus.txt)
- **Query F (Underground Silos acoustic)**:
  - [With Corpus Trace](traces/query_f_with_corpus.txt) vs [No Corpus Trace (Fails)](traces/query_f_no_corpus.txt)
- **Query G (Aegis Shield deuterium)**:
  - [With Corpus Trace](traces/query_g_with_corpus.txt) vs [No Corpus Trace (Fails)](traces/query_g_no_corpus.txt)
- **Query H (Chronos Lead Scientist)**:
  - [With Corpus Trace](traces/query_h_with_corpus.txt) vs [No Corpus Trace (Fails)](traces/query_h_no_corpus.txt)
- **Query I (Zephyr Drone Payload)**:
  - [With Corpus Trace](traces/query_i_with_corpus.txt) vs [No Corpus Trace (Fails)](traces/query_i_no_corpus.txt)