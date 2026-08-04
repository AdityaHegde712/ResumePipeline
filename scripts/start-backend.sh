#!/usr/bin/env bash

# Resolve script directory and change to repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Create logs directory
mkdir -p ".logs"

# Start backend
uv run uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000 >> ".logs/backend.log" 2>&1