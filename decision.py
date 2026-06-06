"""
decision.py — Decision Layer (Brain / Planner).

Input  : DecisionInput  (Pydantic)
Output : DecisionOutput (Pydantic)

Calls llm_gatewayV3 with response_format=json_object so Gemini returns
pure JSON — no regex, no markdown stripping. Plain json.loads() only.

Controlled state machine keeps the agent convergent:
    SEARCH → CRAWL → SUMMARIZE → FINALIZE
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

from schemas import DecisionInput, DecisionOutput, PerceptionOutput

GATEWAY_URL = "http://localhost:8101"
PROMPT_PATH = ROOT / "prompts" / "decision.txt"
DECISION_SCHEMA_PATH = ROOT / "validation" / "decision_schema.json"


def _load_schema() -> dict:
    if DECISION_SCHEMA_PATH.exists():
        try:
            return json.loads(DECISION_SCHEMA_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DecisionOutput.model_json_schema()


def _system_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return _DEFAULT_SYSTEM


_DEFAULT_SYSTEM = """\
You are the Decision Layer of an Autonomous Research Agent.

Your ONLY job is to choose the single best next action and return a JSON object.

Available actions:
  search_web       → use web_search tool with a query string
  crawl_page       → use fetch_url tool with a URL to scrape
  retrieve_context → use retrieve_context tool to search local documents/corpus (specs, incident logs, personnel, Aegis network)
  recall_memory    → retrieve facts from persistent memory
  save_memory      → store an important fact (key + value)
  final_answer     → compile the answer and finish

Return exactly this JSON — nothing else:

{
  "action": "<one of the 6 actions above>",
  "reasoning": "<one sentence: why this action now>",
  "tool_name": "<mcp tool name if action needs a tool, else null>",
  "tool_args": { "<arg_name>": "<arg_value>" },
  "answer": "<full answer text if action is final_answer, else null>"
}

Tool names for reference:
  search_web       → tool_name: "web_search",       tool_args: {"query": "...", "max_results": 5}
  crawl_page       → tool_name: "fetch_url",        tool_args: {"url": "https://..."}
  retrieve_context → tool_name: "retrieve_context", tool_args: {"query": "..."}
  recall_memory    → no tool_name, tool_args: {"query": "search term"}
  save_memory      → no tool_name, tool_args: {"key": "...", "value": "..."}
  final_answer     → no tool_name, answer: "full answer here"

RESEARCH STRATEGY:
- To compare facts, licenses, or features across multiple entities (e.g., Milvus, Qdrant, Weaviate, Chroma, pgvector), perform targeted individual searches for each entity (e.g., 'Qdrant open source license type', 'Chroma database license type') rather than a single broad comparison query. This helps retrieve the exact values directly from search snippets.

CONVERGENCE RULES — follow strictly:
1. If requires_memory is true AND iteration is 1 AND memory context has facts → choose final_answer immediately.
2. If requires_memory is true AND no context yet → choose recall_memory first.
3. If no context yet and requires_tools is true:
   - YOU MUST choose retrieve_context (and NEVER search_web) if the query asks about or mentions:
     * New Kyoto, air cleaning, carbon scrubbing, or Aether-9.
     * Subterranean or underground communication, sending messages without cables, or Whisper-Net.
     * Aegis shielding power, deuterium fusion reactor, plasma bubble, or central reactor.
     * Chronos temporal engine, wormhole stability, quantum entanglement, or its director/lead scientist (Dr. Evelyn Thorne).
     * Zephyr heavy lifter drone, its payload capacity, hydrogen-cell thrusters, or payload.
     * Any local fictional systems/logs/personnel of Project Aegis, Aether-9, Whisper-Net, Chronos, or Zephyr.
   - Otherwise → choose search_web.
4. After finding URLs in search results, use crawl_page on the MOST relevant one.
5. Maximum 3 crawl_page actions per session. If key details (like specific database licenses) are still missing after crawling, perform targeted search_web actions or crawl specific LICENSE/GitHub pages to find the missing details before moving to final_answer.
6. If iteration >= 8 → MUST choose final_answer regardless of context.
7. save_memory ONLY when the user explicitly asks you to remember something.
8. If user query says "remember" or "save" → choose save_memory with key and value extracted from the query.
"""


def decide(inp: DecisionInput) -> DecisionOutput:
    """Run the decision layer. Returns a validated DecisionOutput."""
    q_lower = inp.query.lower()
    # Force direct retrieve_context routing for local RAG corpus queries on turn 1
    if not inp.context:
        is_rag_query = False
        if "new kyoto" in q_lower or "air cleaning" in q_lower or "clean the air" in q_lower or "aether-9" in q_lower:
            is_rag_query = True
        elif "silo" in q_lower or "whisper-net" in q_lower or "without cables" in q_lower or "underground" in q_lower:
            is_rag_query = True
        elif "aegis" in q_lower or "deuterium" in q_lower or "plasma" in q_lower:
            is_rag_query = True
        elif "chronos" in q_lower or "lead scientist" in q_lower or "temporal engine" in q_lower or "evelyn thorne" in q_lower:
            is_rag_query = True
        elif "zephyr" in q_lower or "payload capacity" in q_lower or "lifter drone" in q_lower:
            is_rag_query = True
            
        if is_rag_query:
            return DecisionOutput(
                action="retrieve_context",
                reasoning="Query refers to a local Project Aegis/Aether/Whisper-Net/Chronos/Zephyr fictional document, routing directly to retrieve_context.",
                tool_name="retrieve_context",
                tool_args={"query": inp.query},
            )

    context_block = "\n\n".join(c[:25000] + ("\n... (truncated for context length)" if len(c) > 25000 else "") for c in inp.context) if inp.context else "(no context yet)"
    system = _system_prompt()

    user_message = f"""\
ORIGINAL QUERY: {inp.query}

PERCEPTION:
- Intent: {inp.perception.intent}
- Entities: {', '.join(inp.perception.entities) or 'none'}
- Task type: {inp.perception.task_type}
- Requires tools: {inp.perception.requires_tools}
- Requires memory: {inp.perception.requires_memory}

ITERATION: {inp.iteration} of {inp.max_iterations}
(If iteration >= 6 you MUST return final_answer)

MEMORY CONTEXT:
{inp.memory_context}

ACCUMULATED CONTEXT (last 3 entries):
{context_block}

Choose the single best next action.
"""

    # Fetch available MCP tools to present to Decision via tool_choice="none"
    from action import list_tools
    mcp_tools = list_tools()
    
    gateway_tools = []
    for t in mcp_tools:
        gateway_tools.append({
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": t.get("inputSchema") or t.get("input_schema") or {}
        })

    body = {
        "messages": [{"role": "user", "content": user_message}],
        "system": system,
        "max_tokens": 2048,
        "temperature": 0.0,
        "response_format": {
            "type": "json_schema",
            "schema": _load_schema()
        },
        "auto_route": "decision",
    }
    if gateway_tools:
        body["tools"] = gateway_tools
        body["tool_choice"] = "none"

    import time
    last_exc = None
    for attempt in range(4):
        try:
            r = httpx.post(f"{GATEWAY_URL}/v1/chat", json=body, timeout=120)
            r.raise_for_status()
            data = r.json()
            parsed = data.get("parsed")
            if not parsed:
                raw_text = data.get("text", "") or ""
                parsed = json.loads(raw_text)          # pure JSON — no regex

            print(f"[Decision Debug] parsed: {parsed}", flush=True)

            # Safety clamp: force final_answer near iteration limit
            if inp.iteration >= inp.max_iterations - 1:
                parsed["action"] = "final_answer"
                if not parsed.get("answer"):
                    parsed["answer"] = context_block or "I could not find a complete answer."

            return DecisionOutput.model_validate(parsed)
        except Exception as exc:
            last_exc = exc
            err_msg = str(exc)
            if "r" in locals() and hasattr(r, "text") and r.text:
                err_msg += f" | Response: {r.text}"
            print(f"[Decision] Attempt {attempt + 1} failed: {err_msg}. Retrying...", file=sys.stderr)
            time.sleep(2.5 * (attempt + 1))

    print(f"[Decision] error (all attempts failed): {last_exc}", file=sys.stderr)
    # Pure Pydantic fallbacks — no regex
    if inp.context:
        return DecisionOutput(
            action="final_answer",
            reasoning="Gateway error — compiling from accumulated context.",
            answer="\n\n".join(inp.context),
        )
    return DecisionOutput(
        action="search_web",
        reasoning="Gateway error — defaulting to web search.",
        tool_name="web_search",
        tool_args={"query": inp.query, "max_results": 5},
    )


if __name__ == "__main__":
    from schemas import DecisionInput, PerceptionOutput
    p = PerceptionOutput(
        intent="test", entities=[], requires_memory=False,
        requires_tools=True, task_type="web_research"
    )
    inp = DecisionInput(
        query="test query", perception=p, context=[],
        memory_context="(no memory)", iteration=1,
    )
    result = decide(inp)
    print(result.model_dump_json(indent=2))
