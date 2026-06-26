# Resume Pipeline

A locally-running full-stack application that generates ATS-optimized resume bullet points and compilable LaTeX resumes from your project portfolio, personal profile, and target job descriptions. Powered by Gemini 2.5 Pro via a provider-agnostic LLM abstraction layer.

## Architecture

```
React 19 + Vite + TypeScript          Python 3.12+ + FastAPI
(Frontend, localhost:5173)             (Backend, localhost:8000)
         |                                      |
    HTTP REST + SSE Stream                      |
         |                                      |
    TanStack Query                     LiteLLM (Gemini 2.5 Pro)
         |                                      |
    7 Pages                        Jinja2 Prompt Templates
         |                                      |
    Dark Theme                     LaTeX Renderer + MiKTeX (optional)
```

**Data flow:** User pastes a job description -> LLM matches relevant projects from `PROJECT_SWEEP_SUMMARIES.md` -> generates tailored bullet points -> compiles into `.tex` via Jinja2 -> optionally renders to PDF via MiKTeX.

## Prerequisites

- **Python 3.12+** (3.11 minimum, 3.12+ recommended)
- **Node.js 18+** (for Vite frontend build)
- **uv** (Python package manager -- install via `pip install uv`)
- **MiKTeX** (optional -- required only for PDF compilation)
- **Google Gemini API key** (for LLM generation)

## Quick Start

### 1. Clone and configure

```bash
git clone <repository-url> ResumePipeline
cd ResumePipeline

# Create environment file
cp backend/.env.example backend/.env  # if available, or create manually:
```

Create `backend/.env` with the following content:

```env
GEMINI_API_KEY=your-gemini-api-key-here
PDFLATEX_PATH=C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe
CORS_ORIGINS=http://localhost:5173
```

### 2. Backend setup

```bash
cd backend

# Install dependencies
uv sync

# Install dev dependencies (for testing)
uv sync --extra dev

# Start the server
uv run uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 3. Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`.

## Configuration

All configuration is managed through environment variables in `backend/.env`.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | -- | Google Gemini API key for LLM generation |
| `PDFLATEX_PATH` | No | Auto-detected | Path to `pdflatex` binary (MiKTeX) |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Allowed CORS origins |
| `LLM_DEFAULT_MODEL` | No | `gemini-2.5-pro` | Default LLM model identifier |
| `SWEEP_FILE_PATH` | No | `PROJECT_SWEEP_SUMMARIES.md` | Path to project sweep file |

### Per-task model overrides

The LLM configuration supports per-task model routing. This allows using different models for different stages of the pipeline (e.g., a faster model for keyword analysis, a stronger model for bullet point generation). Configuration is managed at runtime via the `/api/config/llm` endpoint.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check and version |
| `GET` | `/api/profile` | Get full user profile |
| `PUT` | `/api/profile` | Update user profile |
| `GET` | `/api/profile/exists` | Check if profile is created |
| `GET` | `/api/projects` | List all projects from sweep file |
| `GET` | `/api/projects/search?q=` | Search projects by keyword |
| `GET` | `/api/projects/{id}` | Get single project by ID |
| `POST` | `/api/projects/refresh` | Force re-parse sweep file |
| `POST` | `/api/projects/match` | Match job description to projects via LLM |
| `POST` | `/api/generate/points` | Generate bullet points (SSE stream) |
| `POST` | `/api/generate/resume` | Compile full resume + LaTeX (SSE stream) |
| `POST` | `/api/generate/regenerate-section` | Regenerate single section (SSE stream) |
| `GET` | `/api/generate/{id}/tex` | Download `.tex` file |
| `GET` | `/api/generate/{id}/pdf` | Download compiled PDF |
| `GET` | `/api/applications` | List all past applications |
| `GET` | `/api/applications/{id}` | Get application details |
| `DELETE` | `/api/applications/{id}` | Delete an application |
| `GET` | `/api/config/llm` | Get current LLM configuration |
| `PUT` | `/api/config/llm` | Update LLM configuration (in-memory) |
| `GET` | `/api/config/pdf-available` | Check if PDF compilation is available |

## Frontend Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Stats overview, recent applications, new application CTA |
| `/new` | New Application | Job description form, project matching, generation trigger |
| `/review/:id` | Review & Edit | Per-section bullet editor with regenerate capability |
| `/export/:id` | Export Resume | LaTeX preview, `.tex` and PDF download |
| `/profile` | Profile | Full profile editor (education, experience, skills, etc.) |
| `/history` | History | Application list with view and delete actions |
| `/config` | Configuration | Runtime LLM model settings and PDF availability check |

## Project Structure

```
ResumePipeline/
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory, lifespan, CORS
│   │   ├── config.py                # Pydantic BaseSettings (env vars)
│   │   ├── models/                  # Pydantic data models
│   │   │   ├── profile.py           # UserProfile, Education, Experience, etc.
│   │   │   ├── project.py           # ProjectEntry (parsed from sweep file)
│   │   │   ├── application.py       # Application, BulletPoint, SectionPoints
│   │   │   └── generation.py        # GenerationRequest, MatchResult, LLMConfig
│   │   ├── services/                # Business logic layer
│   │   │   ├── profile_service.py   # Load/save/validate profile.yaml
│   │   │   ├── project_sweep_service.py  # Parse PROJECT_SWEEP_SUMMARIES.md
│   │   │   ├── history_service.py   # CRUD for application JSON files
│   │   │   ├── llm_service.py       # LiteLLM wrapper (provider-agnostic)
│   │   │   └── prompt_manager.py    # Load and render Jinja2 templates
│   │   ├── pipeline/                # Generation pipeline
│   │   │   ├── matching_service.py  # JD -> ranked project list via LLM
│   │   │   ├── keyword_analysis_service.py  # Extract JD keywords
│   │   │   ├── resume_points_generator.py  # Per-section bullet generation
│   │   │   ├── resume_writer.py     # Compile all sections, deduplicate
│   │   │   ├── latex_renderer.py    # Jinja2 -> .tex output
│   │   │   ├── pdf_compiler.py      # MiKTeX pdflatex -> .pdf (optional)
│   │   │   └── orchestrator.py      # Full pipeline coordinator with SSE
│   │   ├── api/                     # FastAPI route handlers
│   │   │   ├── router.py            # Aggregate router
│   │   │   ├── profile.py           # /api/profile/*
│   │   │   ├── projects.py          # /api/projects/*
│   │   │   ├── resume.py            # /api/generate/* (SSE streaming)
│   │   │   ├── history.py           # /api/applications/*
│   │   │   └── config.py            # /api/config/*
│   │   ├── templates/
│   │   │   ├── prompts/             # Jinja2 prompt templates (.j2)
│   │   │   └── latex/               # LaTeX resume template (.tex.j2)
│   │   └── utils/
│   │       ├── file_utils.py        # Path helpers
│   │       └── sse.py               # SSE event formatter
│   ├── data/
│   │   ├── profile.yaml             # User profile (YAML)
│   │   ├── subjective_profile.md    # Narrative profile (Markdown)
│   │   └── applications/            # Per-application JSON files
│   └── tests/
│       ├── conftest.py
│       ├── test_profile_service.py
│       ├── test_project_sweep_service.py
│       ├── test_history_service.py
│       ├── test_llm_service.py
│       ├── test_prompt_manager.py
│       ├── test_matching_service.py
│       ├── test_resume_points_generator.py
│       ├── test_resume_writer.py
│       ├── test_latex_renderer.py
│       ├── test_orchestrator.py
│       └── test_api.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts               # Proxy /api -> localhost:8000
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx                  # React entry, QueryClient provider
│       ├── App.tsx                   # Router setup (react-router-dom v7)
│       ├── api/                      # TanStack Query hooks + axios client
│       │   ├── client.ts
│       │   ├── profile.ts
│       │   ├── projects.ts
│       │   ├── resume.ts
│       │   └── history.ts
│       ├── types/                    # TypeScript interfaces
│       ├── pages/                    # 7 page components
│       ├── components/               # Reusable UI components
│       ├── hooks/                    # Custom React hooks
│       ├── styles/                   # CSS variables, dark theme
│       └── utils/                    # Formatters, validators
├── docs/
│   └── template.tex                  # Source LaTeX template
├── PROJECT_SWEEP_SUMMARIES.md        # Project summaries (17 projects)
└── README.md
```

## Testing

### Backend tests

```bash
cd backend

# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_orchestrator.py
```

### Frontend build

```bash
cd frontend

# Type-check and build
npm run build

# Run tests
npm test

# Run tests in watch mode
npm run test:watch
```

## Data Files

The application uses three primary data formats:

- **`PROJECT_SWEEP_SUMMARIES.md`** -- Markdown file containing detailed technical summaries of all projects. Parsed by the backend into structured `ProjectEntry` objects. This is the source of truth for project data.

- **`backend/data/profile.yaml`** -- YAML file containing your personal profile (education, experience, skills, certifications, etc.). Edit directly or through the profile editor in the frontend.

- **`backend/data/applications/*.json`** -- Per-application JSON files storing job descriptions, selected projects, and generated content. Created automatically during the generation pipeline.

## License

See [LICENSE](LICENSE) for details.
