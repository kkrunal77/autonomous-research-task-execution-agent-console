import os
import json
import re
import sys
from pathlib import Path
import httpx

ROOT = Path(__file__).parent.parent
CORPUS_DIR = ROOT / "corpus"
GATEWAY_URL = "http://localhost:8101"

# Stopwords to filter out during basic keyword extraction
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "cant", "cannot", "could",
    "did", "do", "does", "doing", "dont", "down", "during", "each", "few", "for", "from", "further", "had", "has",
    "have", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into",
    "is", "it", "its", "itself", "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "same", "should", "so", "some", "such",
    "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which",
    "while", "who", "whom", "why", "with", "would", "you", "your", "yours", "yourself", "yourselves"
}

def _llm_expand_query(query: str) -> list[str]:
    """Call LLM Gateway to get search keywords and synonyms for the query."""
    prompt = f"""Given this user query: "{query}"
Extract 3 to 6 search terms, synonyms, or key concepts that would help retrieve the relevant document chunk.
Respond with only the terms separated by spaces, absolutely no other text, markdown, or punctuation."""
    
    body = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 128,
        "temperature": 0.0,
    }
    
    try:
        r = httpx.post(f"{GATEWAY_URL}/v1/chat", json=body, timeout=10)
        if r.status_code == 200:
            data = r.json()
            text = data.get("text", "").strip().lower()
            # Clean up punctuation
            text = re.sub(r"[^\w\s-]", "", text)
            words = [w for w in text.split() if w and w not in STOPWORDS]
            if words:
                return list(set(words))
    except Exception as e:
        print(f"[RAG] Warning: LLM query expansion failed: {e}", file=sys.stderr)
    
    # Fallback: simple tokenization of original query
    clean = re.sub(r"[^\w\s-]", "", query.lower())
    return list(set(w for w in clean.split() if w and w not in STOPWORDS and len(w) > 2))

def _llm_rerank(query: str, candidates: list[dict]) -> list[dict]:
    """Consolidated LLM Gateway call to score candidates from 0 to 10."""
    if not candidates:
        return []
    
    prompt_chunks = []
    for i, c in enumerate(candidates):
        prompt_chunks.append(f"--- CANDIDATE {i} (File: {c['file_name']}) ---\n{c['content']}")
    
    chunks_text = "\n\n".join(prompt_chunks)
    
    system_prompt = "You are a RAG Re-ranking Assistant. Rank chunks by relevance to the query."
    prompt = f"""User Query: "{query}"

Review these candidate document chunks and rate each of them from 0 to 10 based on how relevant and useful they are for answering the query.
Return a JSON array of objects, each containing "file_name" and "relevance_score" (integer 0 to 10).

Candidate Chunks:
{chunks_text}

Respond ONLY with a valid JSON array. Do not include markdown blocks like ```json or any explanation."""

    body = {
        "messages": [{"role": "user", "content": prompt}],
        "system": system_prompt,
        "max_tokens": 1024,
        "temperature": 0.0,
    }
    
    try:
        r = httpx.post(f"{GATEWAY_URL}/v1/chat", json=body, timeout=15)
        if r.status_code == 200:
            data = r.json()
            raw_text = data.get("text", "").strip()
            # Extract JSON array
            m = re.search(r"\[[\s\S]*\]", raw_text)
            if m:
                scores_list = json.loads(m.group(0))
                score_map = {item["file_name"]: int(item.get("relevance_score", 0)) for item in scores_list if "file_name" in item}
                
                # Apply scores to candidates
                for c in candidates:
                    c["score"] = score_map.get(c["file_name"], 0)
                
                # Sort descending
                candidates.sort(key=lambda x: x["score"], reverse=True)
                return [c for c in candidates if c["score"] > 2]  # threshold
    except Exception as e:
        print(f"[RAG] Warning: LLM reranking failed: {e}", file=sys.stderr)
        
    # Fallback: keep current ranking based on keyword density
    return candidates

def retrieve_corpus_context(query: str, max_results: int = 3) -> list[dict]:
    """Search the corpus and return the top matching documents."""
    if not CORPUS_DIR.exists():
        print(f"[RAG] Error: Corpus directory {CORPUS_DIR} does not exist.", file=sys.stderr)
        return []
    
    # 1. Expand query keywords via LLM
    keywords = _llm_expand_query(query)
    print(f"[RAG] Expanded search terms: {keywords}", flush=True)
    
    # 2. Retrieve candidates by keyword density match
    candidates = []
    for entry in CORPUS_DIR.iterdir():
        if entry.is_file() and entry.suffix == ".txt":
            try:
                content = entry.read_text(encoding="utf-8")
                content_lower = content.lower()
                
                # Score keyword frequency
                kw_score = 0
                for kw in keywords:
                    # check for word boundaries where possible
                    kw_score += len(re.findall(r'\b' + re.escape(kw) + r'\b', content_lower))
                
                if kw_score > 0:
                    candidates.append({
                        "file_name": entry.name,
                        "content": content.strip(),
                        "kw_score": kw_score
                    })
            except Exception as e:
                print(f"[RAG] Error reading {entry.name}: {e}", file=sys.stderr)
                
    # Sort candidates by keyword score
    candidates.sort(key=lambda x: x["kw_score"], reverse=True)
    
    # Select top 5 for LLM reranking
    top_candidates = candidates[:5]
    
    # 3. Rerank via LLM
    reranked = _llm_rerank(query, top_candidates)
    
    # Return top max_results
    return reranked[:max_results]

if __name__ == "__main__":
    # Quick standalone test
    q = "What is the name of the system designed to clean the air in New Kyoto?"
    res = retrieve_corpus_context(q)
    print(json.dumps(res, indent=2))
