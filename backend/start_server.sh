#!/bin/bash

# Navigate to the script's directory to ensure relative paths resolve correctly
cd "$(dirname "$0")"

# Start uvicorn server in the background using nohup and uv
nohup uv run uvicorn app.main:app --port 8000 > uvicorn.log 2>&1 &

# Store the process ID (PID) to a file for easy shutdown or reference later
PID=$!
echo $PID > uvicorn.pid

echo "Server started in the background (PID: $PID)."
echo "Logs are being redirected to uvicorn.log"
