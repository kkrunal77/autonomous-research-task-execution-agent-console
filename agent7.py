"""
agent7.py — Autonomous Research Agent (Session 7 / Assignment 7)

Performs cognitive loop (Perception → Decision → Action → Memory).
Supports index_document and search_knowledge.
"""
from __future__ import annotations

import argparse
import sys
import textwrap
import time
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

# ── local imports ─────────────────────────────────
from schemas import (
    AgentState,
    DecisionInput,
    DecisionOutput,
    FinalAnswer,
    HistoryEntry,
    MemoryRecord,
    UserQuery,
)
from memory import (
    append_history,
    format_memory_for_prompt,
    load_memory,
    save_memory,
    search_memory,
)
from perception import perceive
from decision import decide
from action import execute_tool, shutdown_mcp

# ── constants ─────────────────────────────────────
MAX_ITER = 8          # hard cap
BANNER = "=" * 70


# ─────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────

def _print_banner(title: str) -> None:
    print(f"\n{BANNER}")
    print(f"  {title}")
    print(BANNER)


def _print_step(icon: str, label: str, text: str = "") -> None:
    print(f"\n{icon}  [{label}]")
    if text:
        wrapped = textwrap.fill(text, width=70, subsequent_indent="     ")
        print(f"     {wrapped}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────
# Memory helpers
# ─────────────────────────────────────────────────

def _retrieve_memory(state: AgentState) -> str:
    """Search memory using query + entities from perception."""
    # For memory-focused tasks, load everything
    if state.perception and state.perception.requires_memory:
        all_records = load_memory()
        if all_records:
            state.memory_context = all_records[:20]
            return format_memory_for_prompt(all_records[:20])

    # Otherwise search by entities
    terms: list[str] = []
    if state.perception:
        for entity in state.perception.entities:
            terms.append(entity)
            for word in entity.split():
                if len(word) > 3:
                    terms.append(word)
    terms.append(state.query)

    results: list[MemoryRecord] = []
    seen_keys: set[str] = set()
    for term in terms:
        for rec in search_memory(term):
            if rec.key not in seen_keys:
                results.append(rec)
                seen_keys.add(rec.key)
    state.memory_context = results[:10]
    return format_memory_for_prompt(results[:10])


def _handle_save_memory(decision: DecisionOutput, state: AgentState) -> str:
    """Execute a save_memory decision."""
    args = decision.tool_args or {}
    key = args.get("key", "")
    value = args.get("value", "")
    if key and value:
        rec = save_memory(key, value)
        return f"✔ Saved to memory: {rec.key} = {rec.value}"
    return "⚠ save_memory: missing key or value in tool_args"


# ─────────────────────────────────────────────────
# Main Agent Loop
# ─────────────────────────────────────────────────

def run_agent(query: str) -> FinalAnswer:
    start_time = time.time()

    _print_banner(f"🤖  Autonomous Research Agent  |  Assignment 7")
    print(f"  Query  : {query}")
    print(f"  Max iterations: {MAX_ITER}")

    state = AgentState(query=query, max_iterations=MAX_ITER)
    sources: list[str] = []

    # ── Step 0: Perception ──
    _print_step("🔍", "PERCEPTION", "Analysing query intent…")
    state.perception = perceive(UserQuery(query=query))
    _print_step("  →", "Intent", state.perception.intent)
    _print_step("  →", "Task type", state.perception.task_type)
    _print_step("  →", "Entities", ", ".join(state.perception.entities) or "none")
    _print_step("  →", "Requires tools", str(state.perception.requires_tools))
    _print_step("  →", "Requires memory", str(state.perception.requires_memory))

    # ── Main iteration loop ──
    while state.iteration < MAX_ITER and not state.done:
        state.iteration += 1
        _print_banner(f"⚡  ITERATION {state.iteration} / {MAX_ITER}")

        # 1. Retrieve memory context
        memory_text = _retrieve_memory(state)

        # 2. Decision layer
        _print_step("🧠", "DECISION", "Choosing next action…")
        decision = decide(DecisionInput(
            query=state.query,
            perception=state.perception,
            context=state.context,
            memory_context=memory_text,
            iteration=state.iteration,
            max_iterations=MAX_ITER,
        ))
        state.last_decision = decision
        _print_step("  →", "Action", decision.action)
        _print_step("  →", "Reasoning", decision.reasoning)

        # 3. Execute the decided action
        action_summary = ""

        if decision.action == "final_answer":
            answer = decision.answer or "\n\n".join(state.context) or "No answer generated."
            state.final_answer = answer
            state.done = True
            action_summary = f"Final answer compiled ({len(answer)} chars)"
            _print_step("✅", "FINAL ANSWER")
            print()
            print(answer)

        elif decision.action == "search_web":
            tool_name = "web_search"
            tool_args = decision.tool_args or {}
            if "query" not in tool_args:
                tool_args["query"] = query
            tool_args.setdefault("max_results", 5)

            _print_step("🌐", "ACTION: web_search", tool_args["query"])
            result = execute_tool(tool_name, tool_args)

            if result.success:
                state.context.append(f"[Search: {tool_args['query']}]\n{result.content}")
                action_summary = f"Got {len(result.content)} chars of search results"
                for line in result.content.splitlines():
                    if line.startswith("http"):
                        sources.append(line.strip())
            else:
                state.context.append(f"[Search failed]: {result.error}")
                action_summary = f"Search failed: {result.error}"

            _print_step("  →", "Result", action_summary)

        elif decision.action == "crawl_page":
            tool_name = decision.tool_name or "fetch_url"
            tool_args = decision.tool_args or {}
            
            if tool_name == "index_document":
                path = tool_args.get("path", "")
                _print_step("📚", "ACTION: index_document", path)
                result = execute_tool("index_document", tool_args)
                if result.success:
                    try:
                        res_dict = json.loads(result.content)
                        chunks_indexed = res_dict.get("chunks_indexed", 0)
                    except Exception:
                        chunks_indexed = result.content
                    state.context.append(f"[Indexed: {path}]\nIndexed {chunks_indexed} chunks into memory.")
                    action_summary = f"Indexed {path} ({chunks_indexed} chunks)"
                else:
                    state.context.append(f"[Index failed: {path}]: {result.error}")
                    action_summary = f"Index failed: {result.error}"
            else:
                url = tool_args.get("url", "")
                if not url:
                    for entry in reversed(state.context):
                        for line in entry.splitlines():
                            if line.startswith("http"):
                                url = line.strip()
                                break
                        if url:
                            break

                if url:
                    _print_step("🕷️ ", "ACTION: crawl_page", url)
                    sources.append(url)
                    result = execute_tool("fetch_url", {"url": url, "timeout": 30})
                    if result.success:
                        state.context.append(f"[Crawled: {url}]\n{result.content[:30000]}")
                        action_summary = f"Got {len(result.content)} chars from {url}"
                    else:
                        state.context.append(f"[Crawl failed: {url}]: {result.error}")
                        action_summary = f"Crawl failed: {result.error}"
                else:
                    action_summary = "crawl_page: no URL available, skipping"
                    state.context.append("[crawl_page: no URL available]")

            _print_step("  →", "Result", action_summary)

        elif decision.action == "retrieve_context":
            tool_name = decision.tool_name or "retrieve_context"
            tool_args = decision.tool_args or {}
            if "query" not in tool_args:
                tool_args["query"] = query
            tool_args.setdefault("max_results", 3)

            _print_step("🔍", f"ACTION: {tool_name}", tool_args["query"])
            result = execute_tool(tool_name, tool_args)

            if result.success:
                state.context.append(f"[{tool_name.replace('_', ' ').title()}: {tool_args['query']}]\n{result.content}")
                action_summary = f"Retrieved {len(result.content)} chars"
            else:
                state.context.append(f"[{tool_name} failed]: {result.error}")
                action_summary = f"{tool_name} failed: {result.error}"

            _print_step("  →", "Result", action_summary)

        elif decision.action == "recall_memory":
            search_term = (decision.tool_args or {}).get("query", query)
            _print_step("💾", "ACTION: recall_memory", search_term)
            records = search_memory(search_term)
            if records:
                mem_text = format_memory_for_prompt(records)
                state.context.append(f"[Memory recall: {search_term}]\n{mem_text}")
                action_summary = f"Found {len(records)} memory record(s)"
            else:
                state.context.append(f"[Memory recall: {search_term}]\n(no matching records found)")
                action_summary = "No matching memory records"
            _print_step("  →", "Result", action_summary)

        elif decision.action == "save_memory":
            _print_step("💾", "ACTION: save_memory")
            action_summary = _handle_save_memory(decision, state)
            state.context.append(f"[{action_summary}]")
            state.done = True
            state.final_answer = action_summary
            _print_step("✅", "SAVED", action_summary)

        else:
            _print_step("⚠️ ", "UNKNOWN ACTION", decision.action)
            action_summary = f"Unknown action: {decision.action}"
            state.context.append(f"[Unknown action: {decision.action}]")

        # 4. Log iteration history
        append_history(HistoryEntry(
            iteration=state.iteration,
            action=decision.action,
            summary=action_summary,
            timestamp=_now(),
        ))

    if not state.final_answer:
        state.final_answer = "\n\n".join(state.context) or "Agent exhausted iterations without a final answer."

    elapsed = time.time() - start_time
    _print_banner(f"🏁  DONE  |  {state.iteration} iterations  |  {elapsed:.1f}s")

    return FinalAnswer(
        query=query,
        answer=state.final_answer,
        iterations_used=state.iteration,
        sources=list(dict.fromkeys(sources))[:10],
    )


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Research Agent (Assignment 7)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="The research query")
    parser.add_argument("--max-iter", type=int, default=MAX_ITER, help="Max iterations (default: 8)")
    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        sys.exit(0)

    try:
        result = run_agent(args.query)
        print(f"\n{'='*70}")
        print("📋  STRUCTURED RESULT")
        print('='*70)
        print(f"Query          : {result.query}")
        print(f"Iterations used: {result.iterations_used}")
        if result.sources:
            print(f"Sources        : {len(result.sources)} URL(s)")
            for s in result.sources[:3]:
                print(f"  - {s}")
    except KeyboardInterrupt:
        print("\n[Interrupted by user]")
    finally:
        shutdown_mcp()


if __name__ == "__main__":
    main()
