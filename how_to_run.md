# How to Run and Test the Autonomous Research Agent

This guide documents the prerequisites, installation steps, and test queries to run the Autonomous Research Agent (Assignment 7).

---

## 1. Setup & Environment

### Verify Python & uv
Ensure that Python 3.11+ and `uv` (dependency manager) are installed. 

### API Keys
Verify that `.env` file in the root directory contains the required API keys (e.g., `TAVILY_API_KEY`).

---

## 2. LLM Gateway Server

The agent makes LLM requests through the custom local gateway. 
*Note: The server runs on port `8101`.*

* **If the gateway is already running**: You do not need to do anything. If you receive an error `[Errno 48] address already in use` when starting it, it is already active.
* **Starting it manually**:
  ```bash
  cd llm_gatewayV3
  ./run.sh
  ```

---

## 3. Running via Interactive Web Dashboard (Recommended for Video Recording)

We have built a premium, modern Web Dashboard where you can run the queries end-to-end, monitor progress, see ANSI logs stream in real-time, and watch the agent memory state update dynamically.

### Start the Dashboard
From the project root:
```bash
uv run uvicorn web_server:app --host 0.0.0.0 --port 8102
```

### Accessing the UI
Open your browser and navigate to:
[http://localhost:8102](http://localhost:8102)

Inside the interface:
1. You will see cards for **Query A**, **Query B**, **Query C (1 & 2)**, and **Query D**.
2. Click **"Execute Run"** on any query to see it execute and watch the real-time logs scroll.
3. Use **"Run All Sequentially"** to run the complete pipeline cleanly in order.
4. Watch the **Cognitive Inspector** on the right update memory (`state/memory.json`) and step logs live as the agent runs.

---

## 4. Running the Agent via CLI (Alternative)

Ensure you are in the root project directory (`assignment-7/`):
```bash
cd /Users/mahipal/Desktop/My_Plugins/assignment-7
```

Run the agent queries using the `uv` tool wrapper:

### Query A: Web Research
```bash
uv run python agent7.py "Find latest AI regulations in India and summarize key changes"
```

### Query B: Multi-Hop Reasoning
```bash
uv run python agent7.py "Find top open-source vector databases and compare licensing"
```

### Query C: Durable Memory (Stateful Persistence)
Execute Run 1 to store the preference, then Run 2 to retrieve it.
* **Run 1 (Save):**
  ```bash
  uv run python agent7.py "Remember that my preferred database is PostgreSQL"
  ```
* **Run 2 (Retrieve):**
  ```bash
  uv run python agent7.py "What database do I prefer?"
  ```

### Query D: Tool Chaining
```bash
uv run python agent7.py "Find best MCP servers for browser automation and explain installation"
```

---

## 5. Verification & Output Files

* **Memory Database**: Persistent memory is stored in `state/memory.json`.
* **Execution logs**: Historical iterations are logged to `state/history.json`.

