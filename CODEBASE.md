# Codebase Overview

> Full-stack resume generation pipeline: accepts a job description, calls an LLM to tailor resume content, deterministically reconstructs a LaTeX document from the output, and compiles it to PDF.

**Last updated:** 2026-08-03
**Primary language:** Python 3.12 (backend) / TypeScript (frontend)
**Architecture style:** Full-stack monolith (two separate runtimes in one repo, Dockerized)

---

## Architecture overview

The system has two runtimes connected by a reverse proxy. In development, Vite's dev server proxies `/api` to the backend on `:8000`. In Docker, nginx proxies `/api/` to `backend:8000` (without prefix stripping — the backend mounts its own `/api` prefix).

The React frontend collects job details and calls five FastAPI endpoints. The backend loads profile and project data once at startup, builds a prompt, makes a single non-streaming LLM call, parses the LLM's structured plaintext response, assembles a LaTeX document from the parsed data and hardcoded templates, then optionally compiles it to PDF via pdflatex.

State lives entirely on the filesystem. Each generated application gets a timestamped directory under `backend/data/applications/` containing four artifacts: `llm_response.md`, `request.json`, `resume.tex`, and (on success) `resume.pdf`. There is no database, cache, or message queue.

```mermaid
graph LR
    Frontend[React SPA] -->|POST /api/applications| API[FastAPI]
    API -->|prompt| LLM[LiteLLM / Gemini]
    API -->|parse + assemble| Assembler[Parser + Assembler]
    Assembler -->|resume.tex| PDF[pdflatex]
    API -->|save artifacts| FS[(filesystem)]
    Frontend -->|GET /api/applications/{id}/*| API
```

**Docker topology** (two services, two named volumes):

```
┌─ docker-compose ────────────────────────────────┐
│                                                  │
│  frontend (nginx:alpine)  ──/api/──>  backend    │
│       :80                           :8000        │
│                                                  │
│  Volumes:                                        │
│    applications_data  →  /app/backend/data/apps  │
│    miktex_cache       →  /home/appuser/.cache/…  │
└──────────────────────────────────────────────────┘
```

---

## Tech stack

| Layer | Technology | Notes |
|---|---|---|
| Backend runtime | Python 3.12 | Managed via `uv`; `pyproject.toml` at repo root; `uv.lock` committed for frozen Docker builds |
| Web framework | FastAPI | Pydantic v2 models; async handlers; lifespan loads startup data |
| LLM client | LiteLLM (`acompletion`) | Single non-streaming call; `LLMError` categories: auth/rate_limit/connection/unknown |
| Settings | pydantic-settings | Reads `backend/.env`; env vars win over defaults |
| Frontend runtime | Vite 8 + React 19 + TypeScript 6 | Mantine v9 component library; dark theme forced |
| Testing (backend) | pytest + pytest-asyncio | `tests/spec/` (frozen), `tests/integration/` (mutable) |
| Testing (frontend) | vitest 4 | `frontend/src/api/client.test.ts` |
| PDF compilation | pdflatex (MiKTeX) | Two-pass compile; 60s per-pass timeout; runs in `asyncio.to_thread` |
| Container (backend) | Docker — python:3.12-slim-bookworm | MiKTeX official apt repo; non-root `appuser`; healthcheck on `/health` |
| Container (frontend) | Docker — multi-stage: node:20-alpine → nginx:alpine | SPA root; `/api/` reverse proxy to `backend:8000` |
| Orchestration | Docker Compose | Two services, two named volumes (`applications_data`, `miktex_cache`); `.env` mounted read-only |

---

## Entry points

| Entry | Command | Purpose |
|---|---|---|
| Backend API | `uvicorn backend.app.main:app --reload` | FastAPI app; lifespan loads profile/sweep/prompt/links into `app.state` |
| Frontend dev | `npm run dev` (in `frontend/`) | Vite dev server on :5173; proxies `/api` to :8000 |
| Backend tests | `pytest -x -q` | Runs from repo root; `asyncio_mode = "auto"` |
| Frontend tests | `npm test` (in `frontend/`) | vitest; single `client.test.ts` |
| Start scripts | `./scripts/start-all.sh` | Runs backend (background) + frontend (foreground); traps INT/EXIT to kill backend |
| Docker (production) | `docker compose up --build` | Builds both images, starts backend (:8000) + frontend (:80) |

`backend/app/main.py` defines `create_app()` (no-arg factory). Lifespan loads five items into `app.state`: `settings`, `profile`, `sweep_text`, `sweep_headings`, `prompt_template`, `project_links`. CORS is hardcoded to `localhost:5173` and `127.0.0.1:5173`.

---

## Key modules

### Backend (`backend/app/`)

| Path | Responsibility |
|---|---|
| `main.py` | App factory; lifespan; CORS; `/health` endpoint |
| `api.py` | 5 endpoints: POST/GET `/api/applications`, GET `.../llm_response`, `.../tex`, `.../pdf` |
| `config.py` | `Settings` (pydantic-settings); `PDFLATEX_PATH` resolution chain; `applications_root` default |
| `loader.py` | Loads `profile.yaml`, `PROJECT_SWEEP_SUMMARIES.md`, `llm_prompt.md`, `project_links.yaml`; `build_prompt()` fills 7 placeholders |
| `llm_client.py` | Single `litellm.acompletion` call; `LLMError` with 4 categories |
| `parser.py` | `parse_llm_response` -> `ParsedResume(skills, experience, projects)`; `ReconstructionError` |
| `assembler.py` | `assemble_resume()`; section_order loop; LaTeX escaping; project link resolution (exact index -> fuzzy name -> omit) |
| `storage.py` | Application dirs `application-YYYYMMDD-HHMMSS`; save tex/pdf/llm_response/request_json; list desc |
| `pdf.py` | `compile_resume()`; two-pass pdflatex; timeout; cleanup; `PDFCompileError` |

### Data / Owner files (read-only, not code)

| Path | Purpose |
|---|---|
| `backend/resume_config.py` | LaTeX templates (topmatter, section wrappers, macros); `escape_ampersands()` |
| `backend/profile.yaml` | Personal info, experience, skills, section_order |
| `backend/llm_prompt.md` | Prompt template with 7 placeholders |
| `backend/project_links.yaml` | 14 entries mapping sweep index to GitHub URL |
| `backend/data/subjective_profile.md` | Freeform profile notes (not loaded by code) |

### Frontend (`frontend/src/`)

| Path | Responsibility |
|---|---|
| `App.tsx` | Main form + results view; single-page layout |
| `main.tsx` | MantineProvider with dark theme |
| `theme.ts` | Dark palette (#121212 body, #e0e0e0 text); accent blue-gray; no shadows; radius 0 |
| `api/client.ts` | Typed fetch wrapper; `ApplicationApiError` class; `createApplication`, `getLlmsResponse`, `getDownloadUrl` |
| `components/PhaseChips.tsx` | Phase status indicators: llm_generation, reconstruction, saved, pdf_error |
| `components/ExportMenu.tsx` | Dropdown menu for .tex and .pdf downloads |

### Tests

| Path | Stability | Coverage |
|---|---|---|
| `tests/spec/test_config.py` | Frozen | Settings resolution |
| `tests/spec/test_parser.py` | Frozen | LLM response parsing |
| `tests/spec/test_assembler.py` | Frozen | LaTeX assembly |
| `tests/spec/test_storage.py` | Frozen | Application directory I/O |
| `tests/spec/test_llm_client.py` | Frozen | Error categorization |
| `tests/integration/test_api.py` | Mutable | Full endpoint flow |
| `tests/integration/test_pdf.py` | Mutable | PDF compilation |
| `tests/integration/test_security.py` | Mutable | Path-traversal attack vectors (8 tests) |
| `tests/fixtures/llm_response_sample.txt` | Frozen | Golden LLM response for parser tests |
| `frontend/src/api/client.test.ts` | Mutable | Frontend API client |

### Scripts and ops

| Path | Responsibility |
|---|---|
| `scripts/start-backend.sh` | Starts backend via `uv run uvicorn`; logs to `.logs/backend.log` |
| `scripts/start-frontend.sh` | Starts frontend dev server (`npm run dev`) |
| `scripts/start-all.sh` | Runs backend in background, frontend in foreground; traps signals to clean up backend on exit |
| `Dockerfile` | Backend image: python:3.12-slim-bookworm + MiKTeX apt repo; non-root `appuser`; healthcheck |
| `frontend/Dockerfile` | Multi-stage: node:20-alpine build → nginx:alpine serve |
| `frontend/nginx.conf` | SPA root (`try_files $uri /index.html`); `/api/` reverse proxy to `backend:8000` (no prefix strip) |
| `docker-compose.yml` | Two services; `applications_data` and `miktex_cache` named volumes; `.env` mounted read-only; `docs/` mounted read-only |
| `.dockerignore` | Excludes `.venv`, `node_modules`, `.env`, `scratch/`, agent task files, OS junk |
| `frontend/.dockerignore` | Excludes `node_modules`, `dist`, logs, IDE files |

---

## Non-obvious patterns

**LLM response is structured plaintext, not JSON**
The LLM is prompted to output `# Skills`, `# Experience`, `# Projects` sections with `## ` entry headers. The parser (`parser.py`) is a deterministic line-by-line state machine -- it does not use JSON or any data format. This means the LLM output format is tightly coupled to the parser's expectations; changing the prompt's output instructions requires updating the parser.

**Project link resolution is three-tier**
`assembler.py` resolves project links by: (1) exact sweep index match from `project_links.yaml`, (2) fuzzy heading name match (token overlap >= 50%), (3) omit the `\resumeLink` macro entirely. The fuzzy matcher normalizes by lowercasing and collapsing non-alphanumeric runs to spaces.

**PDF compile failure is non-fatal**
`api.py` catches `PDFCompileError` and stores it as `pdf_error` in the response. The tex source and llm_response are still saved and downloadable. The frontend shows a `pdf_error` chip but the export menu still works for `.tex`.

**Two-pass pdflatex is required**
`pdf.py` runs pdflatex twice to resolve hyperref anchors. Each pass gets the full timeout independently. A failed pass cleans up partial artifacts (`.aux`, `.out`) but preserves `resume.log` for diagnostics.

**LaTeX escaping is single-pass**
`assembler.py` uses a compiled regex to replace `\ { } $ % & # _ ^ ~` in one pass. Inserted escapes are never re-scanned. The `resume_config.py` templates must NOT be passed through `escape_latex()` -- they contain pre-escaped LaTeX macros.

**Startup data is immutable**
The lifespan handler loads `profile.yaml`, `PROJECT_SWEEP_SUMMARIES.md`, `llm_prompt.md`, and `project_links.yaml` once into `app.state`. Changing these files requires a server restart. There is no hot-reload for owner data.

**application_id is regex-validated, not path-joined raw**
`storage.py` defines `APPLICATION_ID_PATTERN = r"^application-\d{8}-\d{6}$"`. `application_dir()` raises `ValueError` if the ID does not match, and `api.py` catches `(FileNotFoundError, ValueError)` to return 404. This prevents path traversal via encoded `..` segments — a `..%2F..%2F` ID is rejected before any filesystem lookup occurs.

**Docker backend runs as non-root appuser**
The root `Dockerfile` creates `appuser` (uid 1000), switches to it after installing dependencies as root, and pre-creates the MiKTeX cache dir with `appuser` ownership so the named volume inherits correct permissions. The `.env` file is never copied into the image — it is mounted read-only at runtime.

**nginx proxy does not strip the /api prefix**
`frontend/nginx.conf` proxies `/api/` directly to `http://backend:8000` (no `location /api/ { proxy_pass http://backend:8000; }` with trailing slash). This means the backend sees the full `/api/applications` path, matching the dev-server behavior exactly. Adding a trailing slash to `proxy_pass` would break routing.

---

## Development workflow

```bash
# 1. Backend dependencies
uv sync

# 2. Backend environment
cp backend/.env.example backend/.env
# Edit backend/.env: set GEMINI_API_KEY and PDFLATEX_PATH

# 3. Run backend
uvicorn backend.app.main:app --reload --port 8000

# 4. Frontend dependencies
cd frontend && npm install

# 5. Run frontend (separate terminal)
cd frontend && npm run dev

# 6. Backend tests
pytest -x -q

# 7. Frontend tests
cd frontend && npm test

# --- Alternative: bash scripts (logs to .logs/) ---
./scripts/start-all.sh     # backend (background) + frontend (foreground)

# --- Alternative: Docker (production-like) ---
docker compose up --build  # builds both images, starts on :8000 and :80
docker compose down        # stop and remove containers
```

Environment variables: copy `backend/.env.example` to `backend/.env`. The critical vars are `GEMINI_API_KEY` (required for LLM calls) and `PDFLATEX_PATH` (required for PDF compilation; if unset, the system falls back to MiKTeX default path, then `shutil.which("pdflatex")`).

In Docker, `.env` is mounted read-only. `APPLICATIONS_ROOT` is overridden to `/app/backend/data/applications` to match the named volume mount. `MIKTEX_CACHE_DIR` is set to `/home/appuser/.cache/miktex` to persist the MiKTeX package cache across container restarts.

---

## Architecture Decisions

**No database -- filesystem only**
Each application is a directory with four files. This is sufficient for a single-user tool and avoids schema migration overhead. The tradeoff is no concurrent writes and no query capability beyond listing directories.

**Single LLM call, no streaming**
The LLM is called once with `stream=False`. The entire response is parsed deterministically. Streaming would add complexity without benefit since the parser needs the complete response to extract all three sections.

**section_order drives assembly order**
The assembler iterates `profile["section_order"]` (education, skills, experience, projects, publications, leadership, certifications) to build the LaTeX document. Empty sections are omitted. This means the resume section order is controlled by the owner's YAML file, not hardcoded in the assembler.

**Hardcoded CORS origins**
Dev CORS is hardcoded to Vite's defaults in `main.py`. Production deployment would need a different CORS configuration, but the current architecture assumes local-only use.

---

## Before you change code

- Changing `backend/profile.yaml` requires a server restart -- data is loaded once at startup.
- The LLM output format (section headers, entry headers) is tightly coupled to `parser.py`. Changing the prompt's `<output_format>` section requires updating the parser's `_find_header` and `_block_lines` logic.
- `backend/resume_config.py` templates contain pre-escaped LaTeX. Never pass them through `escape_latex()`.
- `tests/spec/` tests are frozen -- they encode the expected contract. If the parser or assembler behavior changes, the spec tests must be updated to match, not the other way around.
- The `PDFLATEX_PATH` resolution chain: env value -> MiKTeX default -> `shutil.which("pdflatex")` -> None. Tests can override this by setting the env var before `Settings()` construction.
- `backend/data/applications/` is gitignored (only `.gitkeep` is tracked). Generated resumes are local-only.
- `APPLICATION_ID_PATTERN` in `storage.py` must stay in sync with the test data in `test_security.py`. Changing the ID format requires updating both the pattern regex and the security test parametrization.
- The backend Dockerfile runs `uv sync --frozen` -- this requires `uv.lock` to be committed. Never delete or regenerate `uv.lock` without testing the Docker build.
- `frontend/nginx.conf` proxies `/api/` without stripping the prefix. Do not add a trailing slash to `proxy_pass` — it would break routing by stripping `/api` from the forwarded path.
- Docker volumes `applications_data` and `miktex_cache` persist across `docker compose down`. Use `docker compose down -v` to wipe them (e.g., to clear stale MiKTeX packages).
