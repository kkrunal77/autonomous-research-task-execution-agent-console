import os
import json
import asyncio
import httpx
from pathlib import Path
from typing import Generator
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Autonomous Research Agent Console")

ROOT = Path(__file__).parent
STATE_DIR = ROOT / "state"
MEMORY_PATH = STATE_DIR / "memory.json"
HISTORY_PATH = STATE_DIR / "history.json"
GATEWAY_URL = "http://localhost:8101"

# Ensure state files exist
STATE_DIR.mkdir(exist_ok=True)
if not MEMORY_PATH.exists():
    MEMORY_PATH.write_text("[]", encoding="utf-8")
if not HISTORY_PATH.exists():
    HISTORY_PATH.write_text("[]", encoding="utf-8")

# Mount static files directory if it exists, or we can serve the main HTML directly
# We will serve the index.html from static/index.html
static_dir = ROOT / "static"
static_dir.mkdir(exist_ok=True)

@app.get("/api/gateway-status")
async def check_gateway():
    """Check if the local LLM gateway is running on port 8101."""
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            # Try to query the gateway health or root
            resp = await client.get(f"{GATEWAY_URL}/")
            return {"status": "connected" if resp.status_code == 200 else "disconnected", "code": resp.status_code}
    except Exception:
        # Check if port is open by attempting connection
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 8101)
            writer.close()
            await writer.wait_closed()
            return {"status": "connected", "details": "Port open"}
        except Exception:
            return {"status": "disconnected"}

@app.get("/api/clean-state")
def clean_state():
    """Clear memory.json, history.json, and FAISS index files."""
    try:
        MEMORY_PATH.write_text("[]", encoding="utf-8")
        HISTORY_PATH.write_text("[]", encoding="utf-8")
        index_path = STATE_DIR / "index.faiss"
        if index_path.exists():
            index_path.unlink()
        ids_path = STATE_DIR / "index_ids.json"
        if ids_path.exists():
            ids_path.unlink()
        return {"status": "success", "message": "State reset successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/get-state")
def get_state():
    """Fetch current memory and history entries."""
    try:
        memory_data = []
        if MEMORY_PATH.exists():
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    memory_data = json.loads(content)
        
        history_data = []
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    history_data = json.loads(content)
        
        return {
            "memory": memory_data,
            "history": history_data
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def run_agent_and_stream(query: str):
    """
    Run the agent7.py script as an asynchronous subprocess
    and yield output lines in real-time.
    """
    # Unbuffered python execution to ensure immediate output flushing
    cmd = ["uv", "run", "python", "-u", "agent7.py", query]
    
    # Inherit existing environment variables
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
        cwd=str(ROOT)
    )
    
    try:
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            decoded_line = line.decode("utf-8", errors="replace")
            yield f"data: {decoded_line.rstrip('\r\n')}\n\n"
            # Small sleep to yield execution control and keep it smooth
            await asyncio.sleep(0.001)
    except Exception as e:
        yield f"data: [Backend streaming error: {str(e)}]\n\n"
    finally:
        try:
            await process.wait()
        except Exception:
            pass
        yield "data: __EOF__\n\n"

@app.get("/api/stream-query")
async def stream_query(query: str = Query(..., description="Query to execute")):
    """Streams terminal output of agent execution."""
    return StreamingResponse(
        run_agent_and_stream(query),
        media_type="text/event-stream"
    )

# Fallback endpoint to serve index.html if static files mount isn't used
@app.get("/", response_class=HTMLResponse)
def get_index():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return HTMLResponse("index.html not found. Please create it in static/index.html", status_code=404)
