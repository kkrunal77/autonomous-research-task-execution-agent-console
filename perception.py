"""
perception.py — Perception Layer.

Input  : UserQuery  (Pydantic)
Output : PerceptionOutput  (Pydantic)

Calls llm_gatewayV3 with response_format=json_object so Gemini returns
pure JSON — no regex, no markdown stripping. Plain json.loads() only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

from schemas import PerceptionOutput, UserQuery

GATEWAY_URL = "http://localhost:8101"
PROMPT_PATH = ROOT / "prompts" / "perception.txt"


def _system_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return _DEFAULT_SYSTEM


_DEFAULT_SYSTEM = """\
You are the Perception Layer of an Autonomous Research Agent.

Your ONLY job is to analyse the user's query and return a JSON object.

Return exactly this JSON structure — nothing else, no prose:

{
  "intent": "<short description of what the user wants>",
  "entities": ["<key concept 1>", "<key concept 2>"],
  "requires_memory": <true|false>,
  "requires_tools": <true|false>,
  "task_type": "<one of: web_research | multi_hop_reasoning | memory_recall | tool_chaining | general_qa>"
}

Rules:
- requires_memory = true  when user references past conversations or personal facts
- requires_tools  = true  when current knowledge alone cannot answer (needs web search / crawl)
- task_type choices:
    web_research       → single-hop web lookup
    multi_hop_reasoning → needs multiple searches + reasoning steps
    memory_recall      → user wants something they told us before
    tool_chaining      → needs search + crawl + extraction chain
    general_qa         → can be answered from training data alone
"""

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "intent":           {"type": "string"},
        "entities":         {"type": "array", "items": {"type": "string"}},
        "requires_memory":  {"type": "boolean"},
        "requires_tools":   {"type": "boolean"},
        "task_type": {
            "type": "string",
            "enum": ["web_research", "multi_hop_reasoning", "memory_recall", "tool_chaining", "general_qa"],
        },
    },
    "required": ["intent", "entities", "requires_memory", "requires_tools", "task_type"],
}

def perceive(user_query: UserQuery) -> PerceptionOutput:
    """Run the perception layer. Returns a validated PerceptionOutput."""
    system = _system_prompt()

    body = {
        "messages": [{"role": "user", "content": user_query.query}],
        "system": system,
        "max_tokens": 512,
        "temperature": 0.0,
        "response_format": {
            "type": "json_schema",
            "schema": _RESPONSE_SCHEMA
        },
        "auto_route": "perception",
    }

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
                parsed = json.loads(raw_text)
            return PerceptionOutput.model_validate(parsed)
        except Exception as exc:
            last_exc = exc
            print(f"[Perception] Attempt {attempt + 1} failed: {exc}. Retrying...", file=sys.stderr)
            time.sleep(2.5 * (attempt + 1))

    # Graceful fallback — treat as general web research
    print(f"[Perception] fallback due to: {last_exc}", file=sys.stderr)
    return PerceptionOutput(
        intent=user_query.query,
        entities=[],
        requires_memory=False,
        requires_tools=True,
        task_type="web_research",
    )


if __name__ == "__main__":
    q = UserQuery(query=sys.argv[1] if len(sys.argv) > 1 else "What is the capital of France?")
    result = perceive(q)
    print(result.model_dump_json(indent=2))
