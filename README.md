# ResumePipeline v2

A locally-run full-stack application that generates a tailored LaTeX resume from your `profile.yaml`, project sweep summaries, and an LLM prompt template. A single Gemini API call produces the resume content, which is deterministically parsed, assembled into LaTeX per your `section_order`, and compiled to PDF via MiKTeX. Cover letter generation is out of scope for v2.

## Features

- One-call generation: a single LLM request produces skills, experience bullets, and project selections
- Deterministic parsing: structured output parsed without LLM post-processing or retries
- Dark minimal UI: Mantine-based React frontend with a flat, modern design
- Non-fatal PDF flag: PDF compilation failure saves the `.tex` source and flags the error without losing work
- Application history: every generation is persisted on disk with full metadata

## Architecture

```
backend/              FastAPI app, LLM client, parser, assembler, PDF compiler
frontend/             React + Vite + TypeScript (Mantine, dark theme)
tests/
  spec/               Frozen core-module tests (parser, assembler, storage, config)
  integration/        Mutable API and PDF tests (mocked LLM)
```

**Generation flow:**

1. Frontend sends form data to `POST /api/applications`
2. Backend fills `resume_prompt.md` placeholders with job and profile context
3. One LiteLLM call to Gemini produces raw plaintext
4. Parser splits into skills, experience, projects
5. Assembler renders LaTeX per `section_order` with link resolution
6. MiKTeX compiles `.tex` to `.pdf` (non-fatal if missing)
7. Response JSON returns per-phase status

## Prerequisites

- **uv** (Python 3.11+, 3.12 recommended) -- package manager for the backend
- **Node.js 20+** and **npm** -- for the frontend
- **MiKTeX** (optional) -- required only for PDF compilation; the app saves `.tex` without it

## Setup

### Backend

```powershell
uv sync
Copy-Item backend\.env.example backend\.env
```

Edit `backend/.env` and set at minimum:

- `GEMINI_API_KEY` -- your Gemini API key
- `PDFLATEX_PATH` -- full path to `pdflatex.exe` (for PDF output)

### Frontend

```powershell
cd frontend
npm install
```

## Run

### Backend

```powershell
uv run uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000
```

The server loads `profile.yaml`, `PROJECT_SWEEP_SUMMARIES.md`, and `resume_prompt.md` at startup. On Windows, run from a non-elevated shell so MiKTeX can install packages automatically (known quirk with elevated terminals).

### Frontend

```powershell
cd frontend
npm run dev
```

Opens at `http://localhost:5173`. Vite proxies `/api` requests to the backend on port 8000.

### Docker

Build and run both services with a single command:

```bash
docker compose up --build
```

The backend runs on port 8000 and the frontend on port 80. The application data (`backend/data/applications`) is persisted in a Docker volume.

To stop the containers:

```bash
docker compose down
```

Open the page, fill in job position, company name, and job description, then submit.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | API key for Gemini via LiteLLM | (required) |
| `GROQ_API_KEY` | API key for Groq (unused in v2) | (empty) |
| `LLM_DEFAULT_MODEL` | LiteLLM model identifier | `gemini/gemini-3-flash-preview` |
| `LLM_DEFAULT_TEMPERATURE` | Sampling temperature | `0.3` |
| `LLM_MAX_TOKENS` | Max output tokens per LLM call | `4096` |
| `DATA_DIR` | Application data storage root | `./data` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |
| `PDFLATEX_PATH` | Full path to `pdflatex.exe`; leave empty to disable PDF | (empty) |

## API

All endpoints are under `/api`.

| Method | Path | Purpose | Response |
|---|---|---|---|
| `POST` | `/api/applications` | Generate a tailored resume | `{status, llm_generation, reconstruction, saved, pdf_error?, application_id}` |
| `GET` | `/api/applications` | List all past applications (newest first) | `[{application_id, job_position, company_name, ...}]` |
| `GET` | `/api/applications/{id}/llm_response` | Serve raw LLM response text | Plain text |
| `GET` | `/api/applications/{id}/tex` | Download `resume.tex` as attachment | File download |
| `GET` | `/api/applications/{id}/pdf` | Download `resume.pdf` as attachment (404 if compile failed) | File download |

A `GET /health` endpoint returns `{"status": "ok"}`.

Fatal errors (LLM call, parse, reconstruction) return `500` with `{phase, error}`. PDF compile failure is non-fatal and appears as a `pdf_error` string in the success response.

## `backend/project_links.yaml`

An index-keyed YAML map (14 entries) that maps sweep indices to GitHub URLs. The assembler resolves project links in this order:

1. Exact index match from the parsed LLM header (e.g., `## 7. Agentic Cybersecurity Lab`)
2. Normalized fuzzy name match against sweep headings (lowercase, strip punctuation, containment check, token overlap >= 0.5)
3. Omit the link if neither resolves

Example:

```yaml
1: https://github.com/AdityaHegde712/ARVR
7: https://github.com/AdityaHegde712/Agentic-Cybersecurity-Lab
```

## Testing

### Backend

```powershell
uv run pytest
```

### Frontend

```powershell
cd frontend
npm run test
```

## Project Structure

```
backend/
  app/
    main.py          FastAPI app factory; lifespan loads profile/sweep/prompt; CORS
    config.py        Settings from env and .env; PDFLATEX_PATH resolution
    loader.py        Startup reads: profile.yaml, sweep summaries, resume_prompt.md
    llm_client.py    Single LiteLLM call with typed error mapping
    parser.py        Deterministic parse of LLM response into structured data
    assembler.py     LaTeX assembly per section_order with link resolution
    pdf.py           pdflatex subprocess (2 passes, timeout, cleanup)
    storage.py       Application directory management and file persistence
    api.py           5 endpoints under /api
  resume_config.py   LaTeX templates and static sections
  resume_prompt.md      Prompt template with placeholders
  project_links.yaml Index-keyed URL map (sweep index to GitHub URL)
  profile.yaml       User profile data
frontend/            React + Vite + TypeScript (Mantine dark theme)
tests/
  spec/              Frozen tests: parser, assembler, storage, config
  integration/       Mutable tests: API, PDF (mocked LLM)
  fixtures/          Golden test data
```

## Notes and Limitations

- **Cover letter**: Deferred to a future version; will follow the same application directory pattern
- **PDF compilation**: Non-fatal; `.tex` source is always saved. Set `PDFLATEX_PATH` or have MiKTeX on PATH for PDF output
- **Windows elevated shell**: MiKTeX cannot auto-install packages when running from an elevated terminal; use a normal shell
- **LLM provider**: v2 targets Gemini via LiteLLM; no local fallback
