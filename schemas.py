"""
schemas.py — Pydantic v2 typed contracts for the Autonomous Research Agent.

Every cognitive layer (Perception → Decision → Action → Memory) communicates
exclusively through these validated models.  No raw dicts, no json.loads().
"""
from __future__ import annotations

from typing import Any, List, Literal, Optional, Union
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────
# Input
# ─────────────────────────────────────────────────

class UserQuery(BaseModel):
    query: str
    session_id: Optional[str] = None


# ─────────────────────────────────────────────────
# Perception Layer Output
# ─────────────────────────────────────────────────

class PerceptionOutput(BaseModel):
    intent: str                         # short description of what the user wants
    entities: List[str]                 # key concepts / entities extracted
    requires_memory: bool               # should we look up prior memory?
    requires_tools: bool                # do we need external tools?
    task_type: Literal[
        "web_research",
        "multi_hop_reasoning",
        "memory_recall",
        "tool_chaining",
        "general_qa",
    ]


# ─────────────────────────────────────────────────
# Decision Layer Output
# ─────────────────────────────────────────────────

class DecisionOutput(BaseModel):
    action: Literal[
        "search_web",
        "crawl_page",
        "retrieve_context",
        "recall_memory",
        "save_memory",
        "final_answer",
    ]
    reasoning: str                      # why this action was chosen
    tool_name: Optional[str] = None     # which MCP tool to call (if any)
    tool_args: Optional[dict] = None    # arguments for the tool call
    answer: Optional[str] = None        # populated when action == "final_answer"


# Typed input contract for the Decision Layer
class DecisionInput(BaseModel):
    query: str
    perception: PerceptionOutput
    context: List[str] = Field(default_factory=list)
    memory_context: str = "(no relevant memory found)"
    iteration: int = 1
    max_iterations: int = 8


# ─────────────────────────────────────────────────
# Tool / Action Layer
# ─────────────────────────────────────────────────

class ToolResult(BaseModel):
    success: bool
    content: str
    tool_name: str
    error: Optional[str] = None


# ─────────────────────────────────────────────────
# Memory Layer
# ─────────────────────────────────────────────────

class MemoryRecord(BaseModel):
    key: str
    value: Union[str, dict, Any]
    timestamp: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None


class HistoryEntry(BaseModel):
    iteration: int
    action: str
    summary: str
    timestamp: Optional[str] = None


# ─────────────────────────────────────────────────
# Agent State (internal loop state)
# ─────────────────────────────────────────────────

class AgentState(BaseModel):
    query: str
    iteration: int = 0
    max_iterations: int = 8
    perception: Optional[PerceptionOutput] = None
    last_decision: Optional[DecisionOutput] = None
    context: List[str] = Field(default_factory=list)   # accumulated search/crawl results
    memory_context: List[MemoryRecord] = Field(default_factory=list)
    done: bool = False
    final_answer: Optional[str] = None


# ─────────────────────────────────────────────────
# Final Output
# ─────────────────────────────────────────────────

class FinalAnswer(BaseModel):
    query: str
    answer: str
    iterations_used: int
    sources: List[str] = Field(default_factory=list)
