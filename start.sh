#!/bin/bash
#
# start.sh — Launch both backend (FastAPI) and frontend (Vite) dev servers
#            concurrently in the foreground with a single command.
#
# Usage:  ./start.sh
# Press Ctrl-C to stop both servers gracefully.
#

set -e

# Colors for status messages
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print a colored status message
info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

# Run from the project root (where this script lives)
cd "$(dirname "$0")"

info "Starting ResumePipeline dev servers..."
echo ""

# --- Start backend in background ---
info "Starting backend (FastAPI) on http://localhost:8000 ..."
(cd backend && uv run uvicorn app.main:app --port 8000 --reload) &
BACKEND_PID=$!

# --- Start frontend in background ---
info "Starting frontend (Vite) on http://localhost:5173 ..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

# --- Trap Ctrl-C (SIGINT/SIGTERM) to kill both processes ---
trap 'echo ""; info "Shutting down..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' SIGINT SIGTERM

# --- Status banner ---
echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}  Backend:  http://localhost:8000${NC}"
echo -e "${CYAN}  Frontend: http://localhost:5173${NC}"
echo -e "${CYAN}  Press Ctrl-C to stop both servers${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""

# Wait for both processes to finish (foreground keeps them alive)
wait
