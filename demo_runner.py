import os
import sys
import subprocess
import time
from pathlib import Path

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def clean_state():
    print("\n🧹 Cleaning agent state (state/memory.json, state/history.json, state/index.faiss, state/index_ids.json)...")
    state_dir = Path("state")
    for filename in ["memory.json", "history.json"]:
        file_path = state_dir / filename
        if file_path.exists():
            file_path.write_text("[]", encoding="utf-8")
    for filename in ["index.faiss", "index_ids.json"]:
        file_path = state_dir / filename
        if file_path.exists():
            try: file_path.unlink()
            except Exception: pass
    print("✨ State cleaned successfully!")
    time.sleep(1.5)

def run_query(query: str):
    print(f"\n🚀 Running: uv run python agent7.py \"{query}\"\n")
    try:
        # Run and stream output in real-time
        process = subprocess.Popen(
            ["uv", "run", "python", "agent7.py", query],
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True
        )
        process.wait()
    except KeyboardInterrupt:
        print("\n\n⚠️ Execution interrupted.")

def main():
    while True:
        clear_screen()
        print("======================================================================")
        print("          🤖  Autonomous Research Agent — Demo Video Runner  🤖")
        print("======================================================================")
        print("  1. 🔍 Run Query A: Web Research")
        print("     \"Find latest AI regulations in India and summarize key changes\"")
        print("  2. 🧠 Run Query B: Multi-Hop Reasoning")
        print("     \"Find top open-source vector databases and compare licensing\"")
        print("  3. 💾 Run Query C: Durable Memory (Run 1 & 2)")
        print("     \"Remember PostgreSQL preference\" -> \"Recall preferred database\"")
        print("  4. 🕷️ Run Query D: Tool Chaining")
        print("     \"Find best MCP servers for browser automation and explain installation\"")
        print("  5. 🔄 Run All Queries sequentially (A -> B -> C -> D)")
        print("  6. 🧹 Clean State (Reset memory & history)")
        print("  7. 🚪 Exit")
        print("======================================================================")
        
        choice = input("\nSelect an option (1-7): ").strip()
        
        if choice == "1":
            run_query("Find latest AI regulations in India and summarize key changes")
            input("\nPress Enter to return to menu...")
        elif choice == "2":
            run_query("Find top open-source vector databases and compare licensing")
            input("\nPress Enter to return to menu...")
        elif choice == "3":
            print("\n--- Part 1: Storing preference in memory ---")
            run_query("Remember that my preferred database is PostgreSQL")
            print("\n--- Part 2: Recalling preference from memory ---")
            run_query("What database do I prefer?")
            input("\nPress Enter to return to menu...")
        elif choice == "4":
            run_query("Find best MCP servers for browser automation and explain installation")
            input("\nPress Enter to return to menu...")
        elif choice == "5":
            clean_state()
            print("\n=== STARTING QUERY A ===")
            run_query("Find latest AI regulations in India and summarize key changes")
            time.sleep(2)
            print("\n=== STARTING QUERY B ===")
            run_query("Find top open-source vector databases and compare licensing")
            time.sleep(2)
            print("\n=== STARTING QUERY C (Run 1) ===")
            run_query("Remember that my preferred database is PostgreSQL")
            time.sleep(2)
            print("\n=== STARTING QUERY C (Run 2) ===")
            run_query("What database do I prefer?")
            time.sleep(2)
            print("\n=== STARTING QUERY D ===")
            run_query("Find best MCP servers for browser automation and explain installation")
            input("\nAll queries completed! Press Enter to return to menu...")
        elif choice == "6":
            clean_state()
        elif choice == "7":
            print("\nGoodbye!\n")
            break
        else:
            print("\nInvalid choice. Please select 1-7.")
            time.sleep(1.5)

if __name__ == "__main__":
    main()
