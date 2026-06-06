import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
TRACES_DIR = ROOT / "traces"
TRACES_DIR.mkdir(exist_ok=True)

QUERIES = [
    {"letter": "a", "desc": "web_research", "query": "Find latest AI regulations in India and summarize key changes"},
    {"letter": "b", "desc": "multi_hop", "query": "Find top open-source vector databases and compare licensing"},
    {"letter": "c_save", "desc": "memory_save", "query": "Remember that my preferred database is PostgreSQL"},
    {"letter": "c_recall", "desc": "memory_recall", "query": "What database do I prefer?"},
    {"letter": "d", "desc": "tool_chaining", "query": "Find best MCP servers for browser automation and explain installation"},
    {"letter": "e", "desc": "rag_kyoto", "query": "What is the name of the system designed to clean the air in New Kyoto?", "is_rag": True},
    {"letter": "f", "desc": "rag_whisper", "query": "How do underground military silos send messages to each other without cables?", "is_rag": True},
    {"letter": "g", "desc": "rag_aegis", "query": "What is the primary power source of the Aegis shielding system?", "is_rag": True},
    {"letter": "h", "desc": "rag_chronos", "query": "Who is the lead scientist for the Chronos project?", "is_rag": True},
    {"letter": "i", "desc": "rag_zephyr", "query": "What is the maximum payload capacity of the Zephyr heavy lifter drone?", "is_rag": True},
]

def clean_state():
    print("🧹 Resetting agent memory state...")
    state_dir = ROOT / "state"
    for filename in ["memory.json", "history.json"]:
        file_path = state_dir / filename
        if file_path.exists():
            file_path.write_text("[]", encoding="utf-8")
    print("✨ State cleaned.")

def run_agent(query: str) -> str:
    cmd = ["uv", "run", "python", "agent7.py", query]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(ROOT))
    # Combine stdout and stderr for the trace
    output = process.stdout + "\n" + process.stderr
    return output

def main():
    clean_state()
    
    for item in QUERIES:
        letter = item["letter"]
        desc = item["desc"]
        query = item["query"]
        is_rag = item.get("is_rag", False)
        
        print(f"\n🚀 Running Query {letter.upper()} ({desc}): '{query}'")
        
        if is_rag:
            # 1. Run WITH corpus
            print("  -> Running WITH corpus...")
            output_with = run_agent(query)
            trace_path_with = TRACES_DIR / f"query_{letter}_with_corpus.txt"
            trace_path_with.write_text(output_with, encoding="utf-8")
            print(f"  Saved trace: {trace_path_with.name}")
            
            # Wait for rate limit reset
            print("  Sleeping 10s...")
            time.sleep(10)
            
            # 2. Run WITHOUT corpus
            print("  -> Running WITHOUT corpus...")
            corpus_path = ROOT / "corpus"
            temp_corpus_path = ROOT / "corpus_disabled"
            
            if corpus_path.exists():
                corpus_path.rename(temp_corpus_path)
            
            try:
                output_no = run_agent(query)
                trace_path_no = TRACES_DIR / f"query_{letter}_no_corpus.txt"
                trace_path_no.write_text(output_no, encoding="utf-8")
                print(f"  Saved trace: {trace_path_no.name}")
            finally:
                if temp_corpus_path.exists():
                    temp_corpus_path.rename(corpus_path)
            
        else:
            # Standard query
            output = run_agent(query)
            trace_path = TRACES_DIR / f"query_{letter}.txt"
            trace_path.write_text(output, encoding="utf-8")
            print(f"  Saved trace: {trace_path.name}")
            
        # Wait to prevent API quota issues
        print("  Sleeping 10s...")
        time.sleep(10)

    print("\n🎉 Benchmark completed! All traces saved in the 'traces' directory.")

if __name__ == "__main__":
    main()
