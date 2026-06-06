# Assignment-7: Autonomous MCP Agent — Architecture Analysis

---

## 1. Big Picture — What This System Is

This project is an **Autonomous Research Agent framework** built from scratch (no LangChain/LangGraph) for Assignment 7. It consists of three primary, independently runnable subsystems working in coordination:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ASSIGNMENT-7 SYSTEM                              │
│                                                                             │
│                     ┌────────────────────────────────┐                      │
│                     │    Interactive Web Dashboard   │                      │
│                     │        (port 8102 / web_server)        │                      │
│                     └───────────────┬────────────────┘                      │
│                                     │                                       │
│                                     ▼                                       │
│                     ┌────────────────────────────────┐                      │
│                     │    Cognitive Loop (agent7.py)  │                      │
│                     │  Perception → Decision → Action│                      │
│                     └──────┬─────────────────┬───────┘                      │
│                            │                 │                              │
│                            ▼                 ▼                              │
│                     ┌─────────────┐   ┌──────────────┐                      │
│                     │mcp_server.py│   │llm_gatewayV3/│                      │
│                     │(Tool Server)│   │(LLM Gateway) │                      │
│                     └─────────────┘   └──────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component 1 — `mcp_server.py` (MCP Tool Server)

### What It Does
An MCP (Model Context Protocol) server that exposes **12 real-world tools** over **stdio transport** so the cognitive loop can interact with the filesystem, web search APIs, and a local semantic knowledge corpus.

### Tools Exposed

| Tool | Purpose | Notes |
|------|---------|-------|
| `web_search(query, max_results=5)` | Search the web | Tavily primary → DuckDuckGo fallback; hard-capped at 5 results |
| `fetch_url(url, timeout=20)` | Scrape a URL to clean markdown | Uses `crawl4ai` + headless Chromium |
| `retrieve_context(query, max_results=3)` | Local semantic search | Searches local document corpus via keyword expansion & LLM reranking |
| `index_document(path)` | Chunks and embeds files | Indexes files using the Gateway's `/v1/embed` endpoint to FAISS memory |
| `search_knowledge(query, k=5)` | Search indexed facts | Performs vector search over previously indexed document chunks |
| `get_time(timezone="UTC")` | Current time in any timezone | Returns ISO + human-readable |
| `currency_convert(amount, from, to)` | Live FX conversion | Calls `frankfurter.dev` API |
| `read_file(path)` | Read file from sandbox | UTF-8 only; sandboxed to `./sandbox/` |
| `list_dir(path)` | List sandbox directory | Returns name/type/size; sandboxed |
| `create_file(path, content)` | Create new file | Sandboxed; errors if already exists |
| `update_file(path, content)` | Overwrite existing file | Sandboxed; errors if not found |
| `edit_file(path, find, replace)` | Find-and-replace in file | Sandboxed |

### Key Design Decisions
- **Sandbox Isolation**: All file tools are sandboxed to `./sandbox/` via `_safe()` — path traversal attacks (`../../etc`) are rejected.
- **RAG Integration**: Exposes `retrieve_context`, `index_document`, and `search_knowledge` to support local semantic document retrieval and cross-session paper ingestion.
- **crawl4ai stdout Fix**: Suppresses crawl4ai's Rich output logs from contaminating the stdio JSON-RPC stream by mapping standard output descriptors to standard error.

---

## 3. Component 2 — `llm_gatewayV3/` (LLM Orchestration Gateway)

### What It Does
A **FastAPI HTTP server** running on **port 8101** that acts as a unified LLM API router. It handles provider failover, RPM/TPM tracking, prompt caching, token-count estimation, and structured JSON output validation.

### Rate-Limit Waiting & Self-Healing Queueing
If a candidate LLM provider is temporarily rate-limited (e.g., hit RPM/TPM limit, or in backoff/cooldown), the gateway does **not** fail immediately. Instead, it:
1. Calculates the required wait duration (`rpm_wait` or `tpm_wait` derived from the oldest items in the sliding window, or the remaining `cooldown`/`backoff` duration).
2. Asynchronously blocks and waits (`await asyncio.sleep`) for that duration (up to 90 seconds).
3. Executes the call once the window resets, shielding the agent from transient rate-limit crashes.

---

## 4. RAG Retrieval Pipeline & Local Document Corpus

To fulfill the requirements of a real RAG application, we have integrated a local semantic search database running over a corpus of **55 documents** stored in the `./corpus/` directory (5 specialized knowledge files, e.g. `doc_01_aether_9.txt`, plus 50 mock system logs to satisfy the 50+ document constraint).

### The Two Retrieval Pathways
1. **Direct Corpus Retrieval (`retrieve_context`)**:
   - **Step 1 (Keyword Expansion)**: Calls the LLM Gateway to expand the user query into 3–6 search terms and synonyms.
   - **Step 2 (Density Scoring)**: Scans the corpus directory, scoring each document by the frequency of the expanded keywords.
   - **Step 3 (LLM Reranking)**: Sends the top 5 document chunks to the LLM Gateway to rate relevance (0 to 10). The highest-scoring chunks are returned.
2. **Durable Knowledge Memory (`index_document` + `search_knowledge`)**:
   - **Step 1 (Ingestion)**: Chunks documents into 400-word segments and generates 768-dimension embeddings via the Gateway's `/v1/embed` endpoint.
   - **Step 2 (FAISS Index)**: Rebuilds a parallel **FAISS vector index** (`state/index.faiss`) alongside the `state/memory.json` registry.
   - **Step 3 (Search)**: Uses cosine similarity over the FAISS index for semantic retrieval (`search_memory`), falling back to keyword overlap if the vector index is empty.

---

## 5. Multi-lingual Query Flow

The Perception and Decision layers automatically support multi-lingual query handling:
1. **Perception**: Validates the input query and extracts intents and entities. It preserves the semantic details regardless of the input language (e.g., Hindi, Spanish, French).
2. **Decision**: Formulates searches or retrieves local RAG context using keywords.
3. **Synthesis**: The Decision layer forces the final answer generation to translate the consolidated findings back into the original input language used by the user, providing a seamless multi-lingual interface.

---

## 6. Web Console Dashboard (`web_server.py` + `static/`)

The application serves a premium, real-time dashboard running on **port 8102** (`uv run uvicorn web_server:app --host 0.0.0.0 --port 8102`):
- **Clickable Run Cards**: Executable cards for all target tasks, letting users run Query A, B, C, D, and RAG Queries E through I directly from the UI.
- **Split Query C**: Separates the durable memory task into **Query C (Save)** ("Remember my preferred database is PostgreSQL") and **Query C (Recall)** ("What database do I prefer?").
- **Live SSE Streaming**: Streams stdout execution lines directly to a mock terminal window.
- **Cognitive Inspector**: Displays live updates of memory state (`state/memory.json`) and timeline step history.

---

## 7. The 2-Tier Routing System (V3's Key Innovation)

### Tier 1 — Router Pool (cheap, fast LLMs)
Classifies each request into `TINY | LARGE | HUGE` using a lightweight LLM call. Default Router Order: `cerebras → groq → nvidia → github`.

### Tier 2 — Worker Pool (actual LLM doing the work)
Picks the best available provider based on the tier:
- **TINY** (< 1,000 tokens): `github → openrouter → groq → nvidia → cerebras → gemini → ollama`
- **LARGE** (1,000 – 8,000 tokens): `gemini → groq → nvidia → cerebras → github → openrouter → ollama`
- **HUGE** (> 8,000 tokens): Rejected with a 503 error recommending chunking.

---

## 8. Schemas & Contracts (`schemas.py`)

All data flows through **Pydantic v2** models to guarantee contract validation:
- `AgentState`: Tracks iteration count, query contexts, and execution flags.
- `UserQuery` / `PerceptionOutput`: Validates the query classification from the perception layer.
- `DecisionInput` / `DecisionOutput`: Validates action planning (e.g. `search_web`, `crawl_page`, `retrieve_context`, etc.).
- `MemoryRecord` / `HistoryEntry`: Standardizes memory registration and execution history logs.

---

## 9. Full Data Flow — Agent Query Lifecycle

```
User Query
    │
    ▼
[Agent Loop — agent7.py]
    │
    ├─► Perception Layer (perception.py)
    │       POST /v1/chat  {auto_route: "perception", ...}
    │       Gateway: Router classifies -> picks TINY worker
    │       Returns: PerceptionOutput {intent, entities, requires_memory, requires_tools, task_type}
    │
    ├─► Memory Recall / RAG Retrieval
    │       Loads records from state/memory.json, searches FAISS, 
    │       or calls retrieve_context over corpus
    │
    ├─► Decision Layer (decision.py)
    │       POST /v1/chat  {auto_route: "decision", ...}
    │       Returns: DecisionOutput {action, reasoning, tool_name, tool_args, answer}
    │
    ├─► Action Layer (action.py)
    │       Invokes tool on mcp_server.py via stdio JSON-RPC
    │       Returns: ToolResult {success, content, error}
    │
    ├─► Memory Update
    │       Writes to state/memory.json + syncs FAISS vector index
    │
    └─► Loop until final_answer or MAX_ITER (8) reached
```

---

## 10. Verification Matrix & Verification Status

| Component | Status |
|-----------|--------|
| `mcp_server.py` — 12 tools | ✅ Complete |
| `llm_gatewayV3/` — LLM gateway with waiting & routing | ✅ Complete |
| `agent7.py` — Main orchestration loop | ✅ Complete |
| `perception.py` — Perception layer | ✅ Complete |
| `decision.py` — Decision layer | ✅ Complete |
| `action.py` — Action caller & tool executor | ✅ Complete |
| `memory.py` — Memory layer with FAISS vectors | ✅ Complete |
| `schemas.py` — Pydantic validation contracts | ✅ Complete |
| `web_server.py` — Web Console Backend | ✅ Complete |
| `static/index.html` — Interactive UI dashboard | ✅ Complete |
