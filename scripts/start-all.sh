#!/usr/bin/env bash

set -euo pipefail

# Resolve script directory and change to repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Create logs directory
mkdir -p ".logs"

# Start backend in background
./scripts/start-backend.sh &
BACKEND_PID=$!

echo "Backend started (PID: $BACKEND_PID)"

# Trap signals to clean up backend on exit
trap 'echo "Stopping backend..."; kill $BACKEND_PID 2>/dev/null || true; wait $BACKEND_PID || true; echo "Backend stopped."' INT EXIT

# Start frontend in foreground
echo "Starting frontend..."
./scripts/start-frontend.sh