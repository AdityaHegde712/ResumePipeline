#!/usr/bin/env bash

# Resolve script directory and change to repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Start frontend
cd frontend && npm run dev