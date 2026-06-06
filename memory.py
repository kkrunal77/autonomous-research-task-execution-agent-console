"""
memory.py — Persistent Memory Layer with Vector Search (FAISS).

Stores facts that survive across runs in state/memory.json.
Stores per-session history in state/history.json.
Maintains a parallel FAISS index under state/index.faiss for semantic vector retrieval.
"""
from __future__ import annotations

import json
import os
import sys
import httpx
import faiss
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Any, Optional

from schemas import HistoryEntry, MemoryRecord

# ── paths and config ──────────────────────────────
ROOT = Path(__file__).parent
STATE_DIR = ROOT / "state"
MEMORY_PATH = STATE_DIR / "memory.json"
HISTORY_PATH = STATE_DIR / "history.json"
INDEX_PATH = STATE_DIR / "index.faiss"
INDEX_IDS_PATH = STATE_DIR / "index_ids.json"

LLM_GATEWAY_V3_URL = os.getenv("LLM_GATEWAY_V3_URL", "http://localhost:8101")

def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(exist_ok=True)
    if not MEMORY_PATH.exists():
        MEMORY_PATH.write_text("[]", encoding="utf-8")
    if not HISTORY_PATH.exists():
        HISTORY_PATH.write_text("[]", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────
# Gateway Embed helper
# ─────────────────────────────────────────────────

def _try_embed(text: str, task_type: str = "retrieval_query") -> list[float] | None:
    """Get embedding from LLM Gateway v1/embed."""
    try:
        r = httpx.post(
            f"{LLM_GATEWAY_V3_URL}/v1/embed",
            json={"text": text, "task_type": task_type},
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("embedding")
    except Exception as e:
        print(f"[Memory] Warning: Gateway embedding call failed: {e}", file=sys.stderr)
    return None


# ─────────────────────────────────────────────────
# FAISS Index Sync
# ─────────────────────────────────────────────────

def _sync_index(records: List[MemoryRecord]) -> None:
    """Rebuild the FAISS index and the index ids list from all records that have embeddings."""
    _ensure_state_dir()
    
    ids = []
    vectors = []
    
    for r in records:
        if r.embedding and len(r.embedding) == 768:
            ids.append(r.key)
            vectors.append(r.embedding)
            
    if not vectors:
        # If no embeddings, remove the files if they exist to avoid stale indices
        if INDEX_PATH.exists():
            try: INDEX_PATH.unlink()
            except Exception: pass
        if INDEX_IDS_PATH.exists():
            try: INDEX_IDS_PATH.unlink()
            except Exception: pass
        return

    # Build IndexFlatIP (cosine similarity when L2 normalized)
    arr = np.array(vectors, dtype="float32")
    faiss.normalize_L2(arr)
    
    index = faiss.IndexFlatIP(768)
    index.add(arr)
    
    faiss.write_index(index, str(INDEX_PATH))
    with open(INDEX_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(ids, f, indent=2)


# ─────────────────────────────────────────────────
# Memory CRUD
# ─────────────────────────────────────────────────

def load_memory() -> List[MemoryRecord]:
    """Load all persisted memory records."""
    _ensure_state_dir()
    try:
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        return [MemoryRecord.model_validate(r) for r in data]
    except (json.JSONDecodeError, Exception):
        return []


def _write_memory(records: List[MemoryRecord]) -> None:
    MEMORY_PATH.write_text(
        json.dumps([r.model_dump() for r in records], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def save_memory(key: str, value: str, tags: List[str] | None = None) -> MemoryRecord:
    """Save or update a fact in persistent memory."""
    _ensure_state_dir()
    records = load_memory()

    # Calculate embedding
    embedding = _try_embed(key, task_type="retrieval_document")

    # Update existing key if found
    for rec in records:
        if rec.key.lower() == key.lower():
            rec.value = value
            rec.timestamp = _now()
            rec.tags = tags or rec.tags
            rec.embedding = embedding
            _write_memory(records)
            _sync_index(records)
            return rec

    # Create new record
    new_rec = MemoryRecord(
        key=key,
        value=value,
        timestamp=_now(),
        tags=tags or [],
        embedding=embedding
    )
    records.append(new_rec)
    _write_memory(records)
    _sync_index(records)
    return new_rec


def add_fact(descriptor: str, *, value: dict, keywords: list[str],
             source: str, run_id: str, goal_id: str | None = None) -> MemoryRecord:
    """Add a raw fact chunk directly to memory and sync the vector index."""
    _ensure_state_dir()
    records = load_memory()
    
    embedding = _try_embed(descriptor, task_type="retrieval_document")
    
    new_rec = MemoryRecord(
        key=descriptor,
        value=value,
        timestamp=_now(),
        tags=[k.lower() for k in keywords],
        embedding=embedding
    )
    records.append(new_rec)
    _write_memory(records)
    _sync_index(records)
    return new_rec


def search_memory(query: str, k: int = 5) -> List[MemoryRecord]:
    """Search memory using vector similarity first, falling back to keyword overlap."""
    _ensure_state_dir()
    records = load_memory()
    if not records:
        return []

    # 1. Try vector search
    try:
        embedding = _try_embed(query, task_type="retrieval_query")
        if embedding:
            # Sync index if missing but we have records with embeddings
            if (not INDEX_PATH.exists() or not INDEX_IDS_PATH.exists()) and any(r.embedding for r in records):
                _sync_index(records)

            if INDEX_PATH.exists() and INDEX_IDS_PATH.exists():
                index = faiss.read_index(str(INDEX_PATH))
                with open(INDEX_IDS_PATH, "r", encoding="utf-8") as f:
                    ids = json.load(f)

                if index.ntotal > 0 and len(ids) == index.ntotal:
                    q_arr = np.array(embedding, dtype="float32").reshape(1, -1)
                    faiss.normalize_L2(q_arr)

                    search_k = min(k, index.ntotal)
                    distances, indices = index.search(q_arr, search_k)

                    results = []
                    seen_keys = set()

                    for idx in indices[0]:
                        if idx < 0 or idx >= len(ids):
                            continue
                        key = ids[idx]
                        if key in seen_keys:
                            continue
                        # Find matching record
                        for r in records:
                            if r.key == key:
                                results.append(r)
                                seen_keys.add(key)
                                break
                    if results:
                        return results
    except Exception as e:
        print(f"[Memory] Vector search failed or skipped: {e}", file=sys.stderr)

    # 2. Fallback to keyword overlap search
    return _keyword_search_fallback(query, records)


def _keyword_search_fallback(query: str, records: List[MemoryRecord]) -> List[MemoryRecord]:
    """Fuzzy keyword search fallback over keys and values."""
    if not query:
        return records
    
    import re
    # Extract alphanumeric words of length > 2
    words = [w.lower() for w in re.findall(r'[a-zA-Z0-9]+', query) if len(w) > 2]
    if not words:
        return []

    results = []
    for rec in records:
        # Normalize fields for matching (replacing underscores/hyphens with spaces)
        key_norm = rec.key.lower().replace('_', ' ').replace('-', ' ')
        val_norm = str(rec.value).lower()
        tags_norm = [t.lower() for t in rec.tags]
        
        match = False
        full_query_norm = " ".join(words)
        if full_query_norm in key_norm or full_query_norm in val_norm:
            match = True
        else:
            # check if any individual word matches
            for w in words:
                if w in key_norm or w in val_norm or any(w in t for t in tags_norm):
                    match = True
                    break
        if match:
            results.append(rec)
            
    return results


def delete_memory(key: str) -> bool:
    """Remove a memory record by key. Returns True if found and deleted."""
    records = load_memory()
    new = [r for r in records if r.key.lower() != key.lower()]
    if len(new) == len(records):
        return False
    _write_memory(new)
    _sync_index(new)
    return True


# ─────────────────────────────────────────────────
# History
# ─────────────────────────────────────────────────

def load_history() -> List[HistoryEntry]:
    _ensure_state_dir()
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return [HistoryEntry.model_validate(e) for e in data]
    except Exception:
        return []


def append_history(entry: HistoryEntry) -> None:
    _ensure_state_dir()
    history = load_history()
    history.append(entry)
    # Keep last 200 entries to avoid unbounded growth
    history = history[-200:]
    HISTORY_PATH.write_text(
        json.dumps([e.model_dump() for e in history], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def format_memory_for_prompt(records: List[MemoryRecord]) -> str:
    """Format memory records as a bullet list for injection into prompts."""
    if not records:
        return "(no relevant memory found)"
    lines = []
    for r in records:
        val = r.value
        if isinstance(val, dict) and "chunk" in val:
            val_str = val["chunk"]
        else:
            val_str = str(val)
        lines.append(f"- {r.key}: {val_str}")
    return "\n".join(lines)
