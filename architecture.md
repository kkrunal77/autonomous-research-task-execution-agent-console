# architecture.md

# Autonomous MCP Agent Architecture Guide

---

# Table of Contents

1. Overview
2. Assignment Goals
3. System Architecture
4. Cognitive Layers
5. Project Structure
6. Data Flow
7. Memory Architecture
8. MCP Architecture
9. LLM Gateway Architecture
10. Pydantic Contracts
11. Iterative Agent Loop
12. Tooling Layer
13. Prompting Strategy
14. State Management
15. Database Design
16. Dependency Management
17. Query Execution Flow
18. Recommended Development Plan
19. Common Mistakes
20. Final Recommended System

---

# 1. Overview

This assignment requires building a mini autonomous AI agent system from scratch.

The system must:
- reason iteratively
- use tools through MCP
- persist memory across runs
- use structured contracts
- avoid agent frameworks

The project should resemble a lightweight AI operating system.

---

# 2. Assignment Goals

The assignment evaluates:

- agent orchestration
- reasoning loops
- structured outputs
- memory persistence
- MCP tool execution
- architectural clarity

This is NOT:
- a chatbot
- a single LLM call
- a summarizer
- a stock analyzer

The focus is on autonomous multi-step reasoning.

---

# 3. High-Level System Architecture

```text
                  ┌─────────────────┐
                  │   User Query    │
                  └────────┬────────┘
                           │
                           ▼
                ┌────────────────────┐
                │  Perception Layer  │
                └────────┬───────────┘
                         │
                         ▼
                ┌────────────────────┐
                │   Decision Layer   │
                └────────┬───────────┘
                         │
                         ▼
                ┌────────────────────┐
                │    Action Layer    │
                └────────┬───────────┘
                         │
                         ▼
                ┌────────────────────┐
                │    MCP Tools       │
                └────────┬───────────┘
                         │
                         ▼
                ┌────────────────────┐
                │    Memory Layer    │
                └────────┬───────────┘
                         │
                         ▼
                ┌────────────────────┐
                │ Iteration Controller│
                └────────────────────┘
                
                
```
This assignment is basically asking you to build a mini autonomous AI agent framework from scratch — without using LangChain/LangGraph.

You need to design:

An agent loop
Cognitive layers
Tool calling through MCP
Persistent memory
Typed contracts using Pydantic
LLM orchestration through llm_gatewayV3

This is actually a very good portfolio project for:

AI Engineer
Agentic AI Engineer
Applied LLM Engineer
MCP ecosystem developer
What They Actually Want

They want you to build something like:

User Query
   ↓
Perception Layer
   ↓
Decision Layer
   ↓
Action Layer (tools/MCP)
   ↓
Memory Layer (store/retrieve)
   ↓
Loop until final answer

NOT:

simple chatbot
one-shot LLM call
stock analyzer
summarizer

They want a multi-step reasoning agent.

Most Important Part

This line:

“The four target queries are the assignment.”

Means:

Your system will be tested against 4 hidden or predefined tasks.

Example:

Query A:
Find X using web + tools

Query B:
Multi-hop reasoning

Query C:
Memory persistence across runs

Query D:
Tool usage + reasoning loop

So your architecture matters more than UI.

BEST APPLICATION IDEA

Choose something that naturally requires:

Memory
Multiple tools
Multi-step reasoning
Iterative loops
Recommended Best Project
“Research & Task Execution Agent”

This is the safest and strongest architecture.

Your agent can:

Search web
Crawl websites
Remember information
Plan tasks
Use tools
Iterate until answer found

This perfectly matches assignment requirements.

Example Queries Your Agent Can Solve
Query Type A — Web Research
Find latest AI regulations in India and summarize key changes.

Agent flow:

Perception → identify research task
Decision → search web
Action → Tavily/DDGS
Memory → store findings
Final answer
Query Type B — Multi-Hop Reasoning
Find top open-source vector databases and compare licensing.

Needs:

Search
Crawl docs
Reasoning
Multiple iterations
Query Type C — Persistent Memory

Run 1:

Remember that my preferred database is PostgreSQL.

Run 2:

What database do I prefer?

Must persist in:

state/memory.json
Query Type D — Tool Chaining
Find best MCP servers for browser automation and explain installation.

Agent:

searches
crawls
plans
extracts
returns final answer
BEST TECH STACK
Core
Component	Recommended
Python	3.11+
Dependency Manager	uv
Validation	Pydantic v2
LLM Access	llm_gatewayV3
MCP Transport	stdio
Search	ddgs + tavily
Crawling	crawl4ai
Storage	JSON or SQLite
Recommended Architecture
Folder Structure
project/
│
├── agent7.py
├── schemas.py
├── memory.py
├── perception.py
├── decision.py
├── action.py
├── mcp_server.py
│
├── prompts/
│   ├── perception.txt
│   ├── decision.txt
│
├── state/
│   ├── memory.json
│   └── history.json
│
├── tools/
│   ├── search_tool.py
│   ├── crawl_tool.py
│
├── tests/
│
├── .env
├── .gitignore
├── pyproject.toml
└── README.md
What Each File Does
1. schemas.py

MOST IMPORTANT FILE.

Every layer must use typed contracts.

Example:

from pydantic import BaseModel
from typing import List, Optional

class UserQuery(BaseModel):
    query: str

class PerceptionOutput(BaseModel):
    intent: str
    entities: List[str]
    requires_memory: bool
    requires_tools: bool

class DecisionOutput(BaseModel):
    action: str
    reasoning: str
    tool_name: Optional[str]

class ToolResult(BaseModel):
    success: bool
    content: str

class MemoryRecord(BaseModel):
    key: str
    value: str

This is REQUIRED.

2. perception.py

Purpose:
Understand user query.

Input:

UserQuery

Output:

PerceptionOutput

Example:

classify intent
determine whether tools needed
determine whether memory needed
3. decision.py

Brain/planner.

Takes:

user query
perception result
memory context

Returns:

next action

Example:

DecisionOutput(
    action="search_web",
    tool_name="tavily"
)
4. action.py

Executes tools.

This layer:

calls MCP tools
calls search
calls crawler
validates outputs
5. memory.py

Persistent memory.

Must survive runs.

Best Memory Design

Start simple.

Use:

state/memory.json

Example:

[
  {
    "key": "favorite_database",
    "value": "PostgreSQL"
  }
]

Functions:

save_memory()
load_memory()
search_memory()
6. agent7.py

Main orchestration loop.

Pseudo:

while iterations < MAX_ITER:
    
    perception = perception_layer()

    decision = decision_layer()

    result = action_layer()

    memory.store()

    if result.final:
        break
Important Part — Iteration Count

They explicitly said:

queries exceeding 2x expected iterations FAIL

So your agent must converge quickly.

Best Strategy

Instead of free autonomous chaos:

Use controlled finite states.

Example:

SEARCH
→ CRAWL
→ SUMMARIZE
→ FINALIZE

This avoids infinite loops.

Database Recommendation

You asked:

how database are working

For THIS assignment:

Start with JSON

Easier.

state/memory.json

Enough to pass.

If You Want Better Architecture

Use SQLite.

Benefits:

persistent
queryable
scalable
easier retrieval

Schema:

CREATE TABLE memory (
    id INTEGER PRIMARY KEY,
    key TEXT,
    value TEXT,
    timestamp TEXT
);

But JSON is simpler for assignment.

MCP Server

You MUST use MCP stdio transport.

Your MCP Server Should Expose Tools Like
search_web(query)
crawl_page(url)
save_memory(key, value)
read_memory(key)
Recommended MCP Tools
Tool	Purpose
tavily	web search
ddgs	fallback search
crawl4ai	webpage extraction
Your .env

Example:

OPENAI_API_KEY=xxx
TAVILY_API_KEY=xxx
MODEL=gpt-4.1-mini
pyproject.toml

Using uv.

Example dependencies:

dependencies = [
  "pydantic>=2",
  "python-dotenv",
  "ddgs",
  "crawl4ai",
  "tavily-python"
]
Installation Flow
uv init
uv add pydantic python-dotenv ddgs crawl4ai tavily-python

Run:

uv run agent7.py
Most Important Knowledge You Need
1. Pydantic v2

You MUST know:

BaseModel
model_validate()
model_dump()

Critical for assignment.

2. Agent Loops

Understand:

perceive
decide
act
reflect
3. MCP

Must know:

stdio transport
tool registration
tool invocation
4. Prompt Engineering

You need:

deterministic outputs
structured JSON outputs
5. LLM Structured Output

VERY IMPORTANT.

You cannot do:

json.loads(random_text)

Use:

Pydantic contracts
validated schemas
Recommended Prompt Strategy

Perception prompt:

You are the perception layer.

Extract:
- intent
- entities
- tool requirement
- memory requirement

Return valid JSON only.

Decision prompt:

You are the decision layer.

Choose ONE next action:
- search_web
- crawl_page
- save_memory
- final_answer
Biggest Mistakes Students Make
1. Using LangChain

Assignment explicitly forbids it.

2. Free-form outputs

Must use typed schemas.

3. Infinite loops

Need bounded iterations.

4. One-shot agent

They want multi-step reasoning.

Best Minimal Passing Architecture
User Query
    ↓
Perception
    ↓
Decision
    ↓
Action
    ↓
Memory Update
    ↓
Repeat if needed

This is enough.

What I Recommend You Build
Final Recommendation

Build:

“Autonomous Research Agent”

Capabilities:

web search
crawl websites
remember facts
multi-step reasoning
persistent memory
MCP tools
structured contracts

This is:

easiest to pass
scalable
impressive on resume
aligns perfectly with assignment
Suggested Development Order
Phase 1

Schemas

Phase 2

Memory layer

Phase 3

Perception layer

Phase 4

Decision layer

Phase 5

Action layer

Phase 6

Agent loop

Phase 7

MCP server

Phase 8

README + demo

Final Goal

Your system should feel like:

A tiny GPT-style autonomous operating system

not a chatbot.

That is exactly what the assignment is testing.

---

# 21. Verification Results & Terminal Outputs

The framework was verified on a clean state against all four target queries. Here are the captured execution outputs:

## Query A: Web Research (Expected: ~3 iterations, Got: 3)

**Command:**
```bash
uv run python agent7.py "Find latest AI regulations in India and summarize key changes"
```

**Terminal Output:**
```text
======================================================================
  🤖  Autonomous Research Agent  |  Assignment 7
======================================================================
  Query  : Find latest AI regulations in India and summarize key changes
  Max iterations: 8

🔍  [PERCEPTION]
     Analysing query intent…

  →  [Intent]
     Find and summarize latest AI regulations in India

  →  [Task type]
     web_research

  →  [Entities]
     AI regulations, India

  →  [Requires tools]
     True

  →  [Requires memory]
     False

======================================================================
  ⚡  ITERATION 1 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     search_web

  →  [Reasoning]
     The user is asking for the latest AI regulations in India, which
     requires searching for current information online. This is the
     first iteration and no prior context exists, making web search
     the most appropriate action.

🌐  [ACTION: web_search]
     latest AI regulations India

  →  [Result]
     Got 498 chars of search results

======================================================================
  ⚡  ITERATION 2 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     crawl_page

  →  [Reasoning]
     The previous search provided a relevant URL that summarizes India's AI
     regulations, so crawling this page will provide detailed
     information to fulfill the user's request.

🕷️   [ACTION: crawl_page]
     https://regulations.ai/regulations/india-summary

  →  [Result]
     Got 8000 chars from https://regulations.ai/regulations/india-summary

======================================================================
  ⚡  ITERATION 3 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     final_answer

  →  [Reasoning]
     The accumulated context provides a comprehensive overview of India's
     AI regulations, including its principle-based framework, key
     guidelines, and sectoral oversight. This is sufficient to answer
     the user's request.

✅  [FINAL ANSWER]

India's AI regulatory framework is primarily principle-based and techno-legal, emphasizing a balance between innovation and safety. The core of this framework is built upon the "AI Governance Guidelines" (expected by 2025) and the Digital Personal Data Protection (DPDP) Act of 2023. This approach is guided by seven principles, or 'Sutras': Trust, People First, Innovation over Restraint, Fairness & Equity, Accountability, Understandable by Design, and Safety, Resilience & Sustainability.

Key aspects of India's AI regulations include:

*   **Hybrid Regulatory Model:** India employs a combination of horizontal principles and sectoral enforcement. Instead of a single AI regulator, existing authorities like the Reserve Bank of India (RBI) and the Telecom Regulatory Authority of India (TRAI) are empowered to create domain-specific rules that align with national guidelines. This ensures context-specific regulation and avoids stifling innovation in low-risk applications.
*   **Risk-Based Approach:** The framework is explicitly risk-based, with 'regulatory-lite' approaches for low-risk AI uses and more stringent safety testing, red-teaming, and impact assessments mandated for higher-risk applications.
*   **Focus on 'AI for All':** The overarching philosophy is to leverage AI for social empowerment and inclusive growth, ensuring that its benefits reach all segments of society, particularly in priority sectors like healthcare, agriculture, and education.
*   **'IndiaAI Mission':** A significant national program with a substantial budget (over INR 10,372 crore) is dedicated to building sovereign compute capacity, high-quality datasets, and indigenous AI models.
*   **AI Safety Institute (AISI):** Recently established, the AISI focuses on operationalizing technical standards and testing frontier AI models against rigorous safety benchmarks before widespread deployment.

In summary, India's AI regulations are characterized by a proactive, adaptive, and multi-stakeholder approach, aiming to foster responsible AI development and deployment through a blend of guiding principles, data protection laws, and sectoral oversight.

======================================================================
  🏁  DONE  |  3 iterations  |  34.8s
======================================================================

======================================================================
📋  STRUCTURED RESULT
======================================================================
Query          : Find latest AI regulations in India and summarize key changes
Iterations used: 3
Sources        : 1 URL(s)
  - https://regulations.ai/regulations/india-summary
```

## Query B: Multi-Hop Reasoning (Expected: ~6 iterations, Got: 6)

**Command:**
```bash
uv run python agent7.py "Find top open-source vector databases and compare licensing"
```

**Terminal Output:**
```text
======================================================================
  🤖  Autonomous Research Agent  |  Assignment 7
======================================================================
  Query  : Find top open-source vector databases and compare licensing
  Max iterations: 8

🔍  [PERCEPTION]
     Analysing query intent…

  →  [Intent]
     Find and compare open-source vector databases based on their
     licensing.

  →  [Task type]
     web_research

  →  [Entities]
     open-source vector databases, licensing

  →  [Requires tools]
     True

  →  [Requires memory]
     False

======================================================================
  ⚡  ITERATION 1 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     search_web

  →  [Reasoning]
     The user is asking to find and compare open-source vector databases
     and their licensing, which requires gathering information from
     the web.

🌐  [ACTION: web_search]
     top open-source vector databases and compare licensing

  →  [Result]
     Got 572 chars of search results

======================================================================
  ⚡  ITERATION 2 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     crawl_page

  →  [Reasoning]
     The previous search provided a relevant URL that likely contains the
     comparison of open-source vector databases and their licensing,
     so crawling this page is the next logical step.

🕷️   [ACTION: crawl_page]
     https://redis.io/blog/best-open-source-vector-databases-comparison/

  →  [Result]
     Got 25274 chars from https://redis.io/blog/best-open-source-vector-
     databases-comparison/

======================================================================
  ⚡  ITERATION 3 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     search_web

  →  [Reasoning]
     The previous search provided a good overview of vector databases, but
     did not explicitly detail their licensing. A new search is needed
     to find specific licensing information for the identified open-
     source vector databases.

🌐  [ACTION: web_search]
     open-source vector databases licensing comparison

  →  [Result]
     Got 572 chars of search results

======================================================================
  ⚡  ITERATION 4 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     search_web

  →  [Reasoning]
     The previous search provided a good overview of vector databases but
     did not explicitly detail their licensing. A new search is needed
     to find specific licensing information for open-source vector
     databases.

🌐  [ACTION: web_search]
     open-source vector databases licensing comparison

  →  [Result]
     Got 407 chars of search results

======================================================================
  ⚡  ITERATION 5 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     crawl_page

  →  [Reasoning]
     The previous search results provided a promising article comparing
     vector databases, and I need to crawl it to extract detailed
     information about their licensing and features.

🕷️   [ACTION: crawl_page]
     https://redis.io/blog/best-open-source-vector-databases-comparison/

  →  [Result]
     Got 25274 chars from https://redis.io/blog/best-open-source-vector-
     databases-comparison/

======================================================================
  ⚡  ITERATION 6 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     final_answer

  →  [Reasoning]
     The iteration count is 6, which triggers the final_answer action
     according to the convergence rules. The accumulated context
     provides information on several open-source vector databases and
     their comparison, which is sufficient to answer the user's query.

✅  [FINAL ANSWER]

Here's a comparison of top open-source vector databases, focusing on their licensing and key features:

**1. Redis**
*   **Licensing:** Redis Open Source is free and has no orchestration needs. Redis Cloud and Redis Software offer managed and self-managed enterprise options.
*   **Key Features:** Acts as a unified real-time data platform, combining vector search with operational data and caching. Offers sub-millisecond latency for many operations and sub-100ms for vector search. Supports HNSW and FLAT indexing, hybrid search (combining vector similarity with metadata filtering), and semantic caching (Redis LangCache). Flexible deployment options (cloud, self-managed, open source).
*   **Best for:** Applications needing vector search alongside operational data, aiming to consolidate infrastructure.

**2. Milvus**
*   **Licensing:** Apache 2.0 licensed.
*   **Key Features:** Cloud-native, distributed vector database designed for horizontal scaling. Version 2.0 uses a microservices architecture. Commonly deployed on Kubernetes for large-scale production, with a standalone option for simpler needs.
*   **Best for:** Large enterprises with massive vector workloads, especially those already using Kubernetes.

**3. Weaviate**
*   **Licensing:** Not explicitly stated in the provided text, but generally known to be open-source with a permissive license.
*   **Key Features:** Combines vector similarity with keyword search (hybrid search) using HNSW indexing. Offers multiple API options (REST, GraphQL, gRPC). Requires separate systems for caching and operational data.
*   **Best for:** Teams comfortable with GraphQL or gRPC for queries, needing hybrid search capabilities.

**4. Qdrant**
*   **Licensing:** Not explicitly stated in the provided text, but generally known to be open-source with a permissive license.
*   **Key Features:** Built in Rust, emphasizing memory safety. Strong filtering capabilities for metadata-heavy queries. Performance varies based on dataset size, dimensionality, and filter complexity.
*   **Best for:** Queries involving complex metadata filtering, where memory safety is a priority.

**5. Chroma**
*   **Licensing:** Not explicitly stated in the provided text, but generally known to be open-source with a permissive license.
*   **Key Features:** Prioritizes simplicity and developer experience, especially for Python workflows. Popular for rapid prototyping and local development. Requires evaluation for high availability and distributed scaling in production.
*   **Best for:** Rapid prototyping, local development, and early-stage projects.

**6. pgvector (PostgreSQL Extension)**
*   **Licensing:** Open-source extension for PostgreSQL.
*   **Key Features:** Adds vector search capabilities to existing PostgreSQL deployments. Performance has improved significantly in recent versions. Requires PostgreSQL tuning expertise and does not include native caching.
*   **Best for:** Teams already running PostgreSQL who want to add vector search capabilities without introducing a new system.

**7. Faiss (Meta AI Research)**
*   **Licensing:** Open-source library.
*   **Key Features:** A C++ library for efficient similarity search and clustering of dense vectors. It is a library, not a database, meaning users must build persistence, backup, replication, and monitoring infrastructure themselves.
*   **Best for:** Research environments or teams with strong C++ engineering resources who need maximum control over implementation details and are willing to build the surrounding database infrastructure.

======================================================================
  🏁  DONE  |  6 iterations  |  57.7s
======================================================================

======================================================================
📋  STRUCTURED RESULT
======================================================================
Query          : Find top open-source vector databases and compare licensing
Iterations used: 6
Sources        : 1 URL(s)
  - https://redis.io/blog/best-open-source-vector-databases-comparison/
```

## Query C: Durable Memory (Run 1: 1 iteration, Run 2: 2 iterations)

### Run 1: Store Fact
**Command:**
```bash
uv run python agent7.py "Remember that my preferred database is PostgreSQL"
```

**Terminal Output:**
```text
======================================================================
  🤖  Autonomous Research Agent  |  Assignment 7
======================================================================
  Query  : Remember that my preferred database is PostgreSQL
  Max iterations: 8

🔍  [PERCEPTION]
     Analysing query intent…

  →  [Intent]
     store user preference for database

  →  [Task type]
     memory_recall

  →  [Entities]
     PostgreSQL

  →  [Requires tools]
     False

  →  [Requires memory]
     True

======================================================================
  ⚡  ITERATION 1 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     save_memory

  →  [Reasoning]
     The user explicitly asked to remember their preferred database, so I
     should save this information to memory.

💾  [ACTION: save_memory]

✅  [SAVED]
     ✔ Saved to memory: preferred_database = PostgreSQL

======================================================================
  🏁  DONE  |  1 iterations  |  11.2s
======================================================================

======================================================================
📋  STRUCTURED RESULT
======================================================================
Query          : Remember that my preferred database is PostgreSQL
Iterations used: 1
```

### Run 2: Retrieve Fact
**Command:**
```bash
uv run python agent7.py "What database do I prefer?"
```

**Terminal Output:**
```text
======================================================================
  🤖  Autonomous Research Agent  |  Assignment 7
======================================================================
  Query  : What database do I prefer?
  Max iterations: 8

🔍  [PERCEPTION]
     Analysing query intent…

  →  [Intent]
     recall preferred database

  →  [Task type]
     memory_recall

  →  [Entities]
     database preference

  →  [Requires tools]
     False

  →  [Requires memory]
     True

======================================================================
  ⚡  ITERATION 1 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     recall_memory

  →  [Reasoning]
     The user is asking about their preferred database, and I have a memory
     of their preferred database being PostgreSQL.

💾  [ACTION: recall_memory]
     preferred_database

  →  [Result]
     Found 1 memory record(s)

======================================================================
  ⚡  ITERATION 2 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     final_answer

  →  [Reasoning]
     The user is asking about their preferred database, and this
     information has already been retrieved from memory in a previous
     step.

✅  [FINAL ANSWER]

You prefer PostgreSQL.

======================================================================
  🏁  DONE  |  2 iterations  |  21.8s
======================================================================

======================================================================
📋  STRUCTURED RESULT
======================================================================
Query          : What database do I prefer?
Iterations used: 2
```

## Query D: Tool Chaining (Expected: ~3 iterations, Got: 3)

**Command:**
```bash
uv run python agent7.py "Find best MCP servers for browser automation and explain installation"
```

**Terminal Output:**
```text
======================================================================
  🤖  Autonomous Research Agent  |  Assignment 7
======================================================================
  Query  : Find best MCP servers for browser automation and explain installation
  Max iterations: 8

🔍  [PERCEPTION]
     Analysing query intent…

  →  [Intent]
     Find best MCP servers for browser automation and explain installation

  →  [Task type]
     web_research

  →  [Entities]
     MCP servers, browser automation, installation

  →  [Requires tools]
     True

  →  [Requires memory]
     False

======================================================================
  ⚡  ITERATION 1 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     search_web

  →  [Reasoning]
     The user is asking for information about 'best MCP servers for browser
     automation' and how to install them, which requires searching the
     web for relevant resources.

🌐  [ACTION: web_search]
     best MCP servers for browser automation installation

  →  [Result]
     Got 325 chars of search results

======================================================================
  ⚡  ITERATION 2 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     crawl_page

  →  [Reasoning]
     The previous search provided a relevant URL that likely contains the
     information needed to answer the query about the best MCP servers
     for browser automation and their installation.

🕷️   [ACTION: crawl_page]
     https://pagebolt.dev/blog/best-mcp-browser-automation-servers

  →  [Result]
     Got 6532 chars from https://pagebolt.dev/blog/best-mcp-browser-
     automation-servers

======================================================================
  ⚡  ITERATION 3 / 8
======================================================================

🧠  [DECISION]
     Choosing next action…

  →  [Action]
     final_answer

  →  [Reasoning]
     The crawled page provides a comprehensive comparison of MCP servers
     for browser automation, including their features, pros, cons,
     costs, and ideal use cases, directly answering the user's query.
     Therefore, a final answer can be compiled.

✅  [FINAL ANSWER]

Here's a breakdown of the best MCP servers for browser automation and their installation considerations:

**1. Playwright MCP**
*   **What it does:** Full browser automation via accessibility trees, allowing interaction like clicking, filling forms, and navigation.
*   **Pros:** Most mature, full interactivity, real browser automation, wide compatibility, enterprise support.
*   **Cons:** High token cost (~$0.15 per interaction), requires infrastructure, verbose accessibility trees, can be slow at scale.
*   **Best for:** Complex form filling, multi-step workflows, UI testing where token cost is not critical.
*   **Installation:** Requires setting up infrastructure or using a managed service.

**2. Puppeteer MCP**
*   **What it does:** Node.js headless browser control, similar to Playwright but JavaScript-native.
*   **Pros:** Native Node.js integration, full Chromium control, good for JavaScript-heavy sites.
*   **Cons:** High token cost (~$0.15 per interaction), requires running a Node.js process, infrastructure overhead, cold start delays.
*   **Best for:** JavaScript-heavy site testing, developers already using Node.js, on-premise solutions.
*   **Installation:** Requires running a Node.js process and managing infrastructure.

**3. PageBolt MCP**
*   **What it does:** Visual screenshot capture, PDF generation, and video recording with narration. Claude sees images, not DOM.
*   **Pros:** Ultra-low token cost (~$0.001 per page), built for video/narration, zero infrastructure needed, fast, great for batch operations.
*   **Cons:** No interactivity (cannot click/fill without separate API), vision-limited (cannot see hidden elements), not suitable for complex form workflows.
*   **Best for:** Visual capture, monitoring, testing, narrated demos, batch screenshot operations, cost-sensitive use cases.
*   **Installation:** Zero infrastructure needed; typically involves signing up for an API key.

**4. browser-use**
*   **What it does:** An open-source browser automation framework.
*   **Pros:** Open source (full control), flexible architecture, active community, self-hosted option.
*   **Cons:** Requires self-hosting, infrastructure overhead, token cost similar to Playwright/Puppeteer, less polished than commercial alternatives.
*   **Best for:** Teams with DevOps resources, full control requirements, on-premise mandates.
*   **Installation:** Requires self-hosting and managing infrastructure.

**5. Stagehand**
*   **What it does:** Mimics human-like browser interaction to evade bot detection.
*   **Pros:** Anti-bot evasion, JavaScript rendering, good for sites with aggressive bot detection.
*   **Cons:** Slower than other approaches, less transparent on token cost, newer, limited community examples.
*   **Best for:** Sites with bot protection, anti-scraping measures, evasion-heavy environments.
*   **Installation:** Varies; the framework is open-source, but managed hosting has separate pricing.

**Summary & Recommendations:**
*   **For complex interactions and workflows:** Playwright MCP is the default due to its maturity and reliability, provided token cost is acceptable.
*   **For visual capture, cost-effectiveness, and batch operations:** PageBolt MCP is the best choice, especially if interactivity is not a primary requirement.
*   **For full control and on-premise deployment:** browser-use offers flexibility for teams with DevOps resources.
*   **For JavaScript-heavy sites and Node.js environments:** Puppeteer MCP is a strong contender.
*   **For evading aggressive bot detection:** Stagehand is specialized for human-like interaction.

Installation complexity varies significantly, from zero infrastructure for PageBolt to self-hosting requirements for browser-use and Puppeteer.

======================================================================
  🏁  DONE  |  3 iterations  |  23.9s
======================================================================

======================================================================
📋  STRUCTURED RESULT
======================================================================
Query          : Find best MCP servers for browser automation and explain installation
Iterations used: 3
Sources        : 1 URL(s)
  - https://pagebolt.dev/blog/best-mcp-browser-automation-servers
```

## 22. RAG Semantic & Direct Retrieval Queries (Queries E through I)

We have verified 5 additional RAG queries against the local semantic corpus of 55 documents under `./corpus/`. These queries successfully retrieve context and converge within 2 iterations when the corpus index is active, but fail completely when the corpus is removed.

### Query E: RAG Semantic (Clean Air System in New Kyoto)
- **Command**: `uv run python agent7.py "What is the name of the system designed to clean the air in New Kyoto?"`
- **Expected Result**: **Aether-9 Atmospheric Scrubbing Facility** (retrieved from `doc_01_aether_9.txt`).
- **No-Corpus Behavior**: Fails to retrieve context and outputs an empty answer.

### Query F: RAG Semantic (Underground messages resonance)
- **Command**: `uv run python agent7.py "How do underground military silos send messages to each other without cables?"`
- **Expected Result**: **Project Whisper-Net Subterranean System** using acoustic resonance through rock layers (from `doc_02_whisper_net.txt`).
- **No-Corpus Behavior**: Fails to find details.

### Query G: RAG Direct (Aegis shield power source)
- **Command**: `uv run python agent7.py "What is the primary power source of the Aegis shielding system?"`
- **Expected Result**: **Central deuterium fusion reactor** (from `doc_03_aegis_power.txt`).
- **No-Corpus Behavior**: Fails completely.

### Query H: RAG Direct (Chronos lead scientist)
- **Command**: `uv run python agent7.py "Who is the lead scientist for the Chronos project?"`
- **Expected Result**: **Dr. Evelyn Thorne** (from `doc_04_chronos_personnel.txt`).
- **No-Corpus Behavior**: Fails completely.

### Query I: RAG Direct (Zephyr payload capacity)
- **Command**: `uv run python agent7.py "What is the maximum payload capacity of the Zephyr heavy lifter drone?"`
- **Expected Result**: **12 metric tons of cargo** (from `doc_05_zephyr_payload.txt`).
- **No-Corpus Behavior**: Fails completely.