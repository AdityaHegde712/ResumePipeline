# Dockerize ResumePipeline for Development Mode

## Objective
Create Docker configuration files for the ResumePipeline project (Python/FastAPI backend + React/Vite frontend) to enable development mode with hot-reload.

## Rationale for General-Builder Assignment
This task spans both backend and frontend layers — creating Dockerfiles, docker-compose orchestration, and .dockerignore files — making it a perfect fit for the General-Builder role rather than a layer-specific specialist.

## Plan

### Files to Create
1. `backend/Dockerfile` — Python 3.12-slim + uv + uvicorn with `--reload`
2. `frontend/Dockerfile` — Node 20-alpine + npm ci + Vite dev server with `--host 0.0.0.0`
3. `backend/.dockerignore` — Exclude .venv, __pycache__, .env, etc.
4. `frontend/.dockerignore` — Exclude node_modules, dist
5. `docker-compose.yml` — Orchestrate both services with hot-reload volumes

### Key Design Decisions
- **Named volume `backend-venv`** at `/app/.venv` prevents the host machine's `.venv` from shadowing the container's installed packages when the host code is mounted
- **Anonymous volume `/app/node_modules`** ensures the container's node_modules survive the host mount
- **Host source mounts** (`./backend:/app`, `./frontend:/app`) enable file change detection for hot-reload
- **`env_file`** passes `GEMINI_API_KEY` and other environment variables from `backend/.env`

### Verification
- Run `docker compose build` and confirm both images build without errors
- Both images should be taggable as `resumepipeline-backend:latest` and `resumepipeline-frontend:latest`
- No existing files should be modified
