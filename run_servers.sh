#!/bin/bash

# Get project root dir
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kill any existing processes running on port 8101 or 8102 to avoid address conflicts
echo "Cleaning up any existing server instances..."
lsof -ti:8101 | xargs kill -9 2>/dev/null
lsof -ti:8102 | xargs kill -9 2>/dev/null

echo "Starting LLM Gateway on port 8101..."
(cd "$ROOT_DIR/llm_gatewayV3" && ./run.sh) &
GATEWAY_PID=$!

# Trap Ctrl+C (SIGINT) and terminal termination (SIGTERM)
cleanup() {
    echo ""
    echo "Stopping LLM Gateway (PID: $GATEWAY_PID) and exiting..."
    kill $GATEWAY_PID 2>/dev/null
    # Make sure port 8101 is fully cleared
    lsof -ti:8101 | xargs kill -9 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "Waiting for LLM Gateway to initialize..."
sleep 3

echo "Starting Web Dashboard Console on port 8102..."
uv run uvicorn web_server:app --host 0.0.0.0 --port 8102

# Clean up background process if uvicorn exits naturally
cleanup
