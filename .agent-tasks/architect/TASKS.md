# Resume Pipeline — Granular Task List v2.0

> **Version:** 2.0 (Sub-agent ready — all decisions resolved)  
> **Complexity Scale:** 1 (trivial) → 10 (extremely complex)  
> **Total Tasks:** 72  
> **Total Complexity:** 264/720

---

## Phase 0: Project Scaffolding (7 tasks, 18 complexity)

### Task 0.1: Create monorepo directory structure
| Field | Value |
|-------|-------|
| **Files** | Root directories |
| **Agent** | `@general-builder` |
| **Complexity** | 1 |
| **Deps** | — |

**Action:** Create the following directory structure:
```
backend/app/models/
backend/app/services/
backend/app/pipeline/
backend/app/api/
backend/app/utils/
backend/app/templates/prompts/
backend/app/templates/latex/
backend/data/applications/
backend/tests/
frontend/src/api/
frontend/src/types/
frontend/src/pages/
frontend/src/components/layout/
frontend/src/components/forms/
frontend/src/components/resume/
frontend/src/components/generation/
frontend/src/components/history/
frontend/src/components/common/
frontend/src/hooks/
frontend/src/styles/
frontend/src/utils/
frontend/tests/
docs/
```

Then create `backend/data/subjective_profile.md` with empty template:
```markdown
# Subjective Profile

> Free-form narrative for vNext cover letter generation.
> Not used by resume generation in v1.0.

## Early Life & Background

## Professional Philosophy

## Greatest Challenge

## Long-Term Goals

## Personal Interests
```

**Acceptance:** All directories exist with `.gitkeep` in empty dirs. `docs/template.tex` already exists — leave it. `subjective_profile.md` exists with template sections.

---

### Task 0.2: Initialize Python project
| Field | Value |
|-------|-------|
| **Files** | `backend/pyproject.toml`, `backend/.env.example` |
| **Agent** | `@backend-dev` |
| **Complexity** | 3 |
| **Deps** | 0.1 |

**Action:** Create `backend/pyproject.toml` with `uv` and these dependencies:
- `fastapi[standard] >=0.115`
- `uvicorn[standard]`
- `litellm >=1.40`
- `jinja2 >=3.1`
- `pyyaml >=6.0`
- `httpx >=0.27`
- `python-multipart >=0.0.9`
- `pydantic-settings >=2.1`
- `pydantic >=2.5`
- Dev: `pytest >=8`, `pytest-asyncio >=0.24`, `httpx` (for TestClient)

Create `backend/.env.example`:
```ini
# ── LLM Provider (Gemini via LiteLLM) ─────
# LiteLLM reads GEMINI_API_KEY for all gemini/* models
GEMINI_API_KEY="your-gemini-api-key-here"
LLM_DEFAULT_MODEL="gemini/gemini-2.5-pro"

# Temperature: 0.3 for Gemini 1.5/2.x | Default (1.0) recommended for Gemini 3+
LLM_DEFAULT_TEMPERATURE=0.3

# Maximum OUTPUT tokens per LLM call
LLM_MAX_TOKENS=4096

# ── Paths ─────────────────────────────────
DATA_DIR="./data"

# ── Server ────────────────────────────────
CORS_ORIGINS="http://localhost:5173"

# ── PDF Compilation (optional — MiKTeX) ───
# Path to pdflatex.exe. Use FORWARD slashes or double backslashes.
# Leave empty to disable PDF compilation (export .tex only).
PDFLATEX_PATH="C:/Users/hifia/AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex.exe"

# ── Prompt Overrides (optional) ───────────
# Each env var overrides the corresponding .j2 file in app/templates/prompts/.
# The value is treated as a Jinja2 template string (supports {{ variables }}).
# Leave empty to use the default .j2 file.
# PROMPT_MATCHING="..."
# PROMPT_KEYWORD_ANALYSIS="..."
# PROMPT_RESUME_POINTS="..."
# PROMPT_RESUME_WRITEUP="..."
```

**Acceptance:** `uv sync` installs all deps without error.

---

### Task 0.3: Initialize React + Vite + TypeScript project
| Field | Value |
|-------|-------|
| **Files** | `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/index.html` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 3 |
| **Deps** | 0.1 |

**Action:** Create a Vite + React + TypeScript project with:
- React 19, react-dom 19
- `@tanstack/react-query >=5`
- `axios >=1.7`
- `react-router-dom >=7`
- Dev: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`
- `vite.config.ts` with proxy: `"/api"` → `"http://localhost:8000"`
- `tsconfig.json` with strict mode

**Acceptance:** `npm install` completes. `npm run dev` starts on port 5173.

---

### Task 0.4: Implement backend config
| Field | Value |
|-------|-------|
| **Files** | `backend/app/__init__.py`, `backend/app/config.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 2 |
| **Deps** | 0.2 |

**Action:** Create `backend/app/config.py` with `Settings(BaseSettings)`:
```python
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

class Settings(BaseSettings):
    # LLM — field name matches LiteLLM's GEMINI_API_KEY env var
    gemini_api_key: str = ""  # ← LiteLLM reads this env var for gemini/* calls
    llm_default_model: str = "gemini/gemini-2.5-pro"
    llm_default_temperature: float = 0.3  # Gemini 3+ models override to 1.0 internally
    llm_max_tokens: int = 4096
    
    # Paths
    data_dir: Path = Path("./data")
    sweep_file_path: Path = Path("../../PROJECT_SWEEP_SUMMARIES.md")
    latex_template_path: Path = Path("./app/templates/latex/resume_template.tex.j2")
    
    # Server
    cors_origins: str = "http://localhost:5173"
    
    # PDF Compilation (MiKTeX — optional)
    pdflatex_path: Optional[str] = None  # "C:\\path\\to\\pdflatex.exe" or None
    
    # Prompt Override (optional — overrides .j2 files at runtime)
    # Each is a full Jinja2 template string. If empty, the default .j2 file is used.
    prompt_matching: Optional[str] = None
    prompt_keyword_analysis: Optional[str] = None
    prompt_resume_points: Optional[str] = None
    prompt_resume_writeup: Optional[str] = None
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def configure_litellm(self):
        """Call this before making LiteLLM calls to set auth."""
        import os
        os.environ["GEMINI_API_KEY"] = self.gemini_api_key
```

Also create `backend/app/__init__.py` (empty).

**Acceptance:** `Settings()` loads from `.env`. Missing env vars fall back to defaults.

---

### Task 0.5: Define all Pydantic models
| Field | Value |
|-------|-------|
| **Files** | `backend/app/models/__init__.py`, `backend/app/models/profile.py`, `backend/app/models/project.py`, `backend/app/models/application.py`, `backend/app/models/generation.py` |
| **Agent** | `@data-engineer` |
| **Complexity** | 4 |
| **Deps** | 0.4 |

**Action:** Implement all models defined in PLAN.md §4.1–§4.4. Each model file gets its own Pydantic models exactly as specified. The `__init__.py` re-exports all models.

**Acceptance:** All models importable from `app.models`. Type-checked. Can instantiate with sample data.

---

### Task 0.6: Define TypeScript types
| Field | Value |
|-------|-------|
| **Files** | `frontend/src/types/profile.ts`, `frontend/src/types/project.ts`, `frontend/src/types/application.ts`, `frontend/src/types/generation.ts` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 3 |
| **Deps** | 0.5 |

**Action:** Create TypeScript interfaces mirroring every Pydantic model exactly. Use `interface` not `type`. Include all fields with correct types.

**Acceptance:** Every backend field has a TS counterpart. Types are importable and produce no `tsc` errors.

---

### Task 0.7: Create root config files
| Field | Value |
|-------|-------|
| **Files** | `.gitignore`, `README.md` (scaffold), `root .env.example` |
| **Agent** | `@general-builder` |
| **Complexity** | 2 |
| **Deps** | — |

**Action:** `.gitignore` covering: `.env`, `__pycache__/`, `node_modules/`, `dist/`, `*.pyc`, `.venv/`, `.pytest_cache/`, `data/applications/*.json` (but not `.gitkeep`). README with project title and brief description (placeholder for Phase 6).

**Acceptance:** `git init && git status` shows only intended files.

---

## Phase 1: Data Layer (6 tasks, 29 complexity)

### Task 1.1: Implement ProfileService (two-profile model)
| Field | Value |
|-------|-------|
| **Files** | `backend/app/services/__init__.py`, `backend/app/services/profile_service.py` |
| **Agent** | `@data-engineer` |
| **Complexity** | 6 |
| **Deps** | 0.5 |

**Action:** Implement `ProfileService` class that manages TWO profile files:

**File 1: `data/profile.yaml` — Objective profile (structured YAML)**
```yaml
name: Aditya Hegde
email: aditya.hegde@sjsu.edu
phone: "+1-XXX-XXX-XXXX"
location: "San Jose, CA"
education: [...]   # list of schools
experience: [...]  # list of jobs
publications: [...] # list of papers  ← NEW
skills: {languages: [...], frameworks: [...], tools: [...]}
section_order: ["education", "skills", "projects", "experience", "publications", "leadership"]
# ... all other objective fields
```

**File 2: `data/subjective_profile.md` — Narrative profile (free-form markdown)**
```markdown
## Early Life & Background
...
## Professional Philosophy
...
## Greatest Challenge
...
## Long-Term Goals
...
## Personal Interests
...
```
Not editable through the UI in v1.0 (user edits in VS Code). Referenced by `UserProfile.subjective_profile_path` and loaded as raw text into `UserProfile.subjective_profile_content`. **Not used by resume generation** — reserved for vNext cover letter agent.

**Methods:**
```python
async def load() -> UserProfile
    # 1. Read profile.yaml → parse YAML → validate → UserProfile (objective fields)
    # 2. Read subjective_profile.md → load as raw text → set subjective_profile_content
    # 3. If either file missing, return defaults (empty profile + empty narrative)

async def save(profile: UserProfile) -> UserProfile
    # 1. Serialize objective fields → YAML → write to profile.yaml
    # 2. Serialize subjective_profile_content → write to subjective_profile.md
    # 3. Preserve YAML readability (block scalars for multiline, sort_keys=False)
    # 4. Create data/ dir if missing

async def exists() -> bool
    # Check profile.yaml exists with required fields (name, email)

async def load_subjective() -> str
    # Load subjective_profile.md as raw text, return empty string if missing
```

**Edge cases:** Invalid YAML → `ProfileValidationError` with line number. Missing `subjective_profile.md` → empty string (not an error).

**YAML writing:** Use `yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)`.

**Acceptance:** Round-trip: load default → set name + write narrative → save → load → both fields present.

---

### Task 1.2: Implement ProjectSweepService
| Field | Value |
|-------|-------|
| **Files** | `backend/app/services/project_sweep_service.py` |
| **Agent** | `@data-engineer` |
| **Complexity** | 7 |
| **Deps** | 0.5 |

**Action:** Implement `ProjectSweepService` that parses `PROJECT_SWEEP_SUMMARIES.md` into structured `ProjectEntry` objects.

**Parsing algorithm:**
1. Read file as text. Split on `\n## ` (sections start with `## `).
2. For each section, extract:
   - **ID:** Lowercase slug from project name (first word before `—` or ` -- `)
   - **Name:** First line after `## N. ` (strip the `N. ` prefix)
   - **Type:** Line matching `**Type:** ` — extract rest of line
   - **Tech stack:** Line matching `**Tech Stack` or `**Tech Stack & Architecture**` — extract after `:** ` split by commas
   - **Summary:** Lines between `### Project Overview` and next `###` heading
   - **Key Features:** Bullet points (`- **...:**`) under `### Key Features`
   - **Resume value bullets:** Lines with `- **...:**` under `### Resume Value`
   - **Lines of code:** Line matching `**Scale:**` — extract number before "lines"
   - **Domains:** Inferred from Type + Tech stack keywords (use a simple mapping: "ML" → "Machine Learning", "Web" → "Web Development", etc.)

3. Cache parsed result in memory with file mtime timestamp.

**Methods:**
- `parse() -> list[ProjectEntry]` — Parse from scratch
- `get_all() -> list[ProjectEntry]` — Return cached, re-parse if stale
- `refresh() -> list[ProjectEntry]` — Force re-parse
- `get_by_id(id: str) -> ProjectEntry | None` — Look up by slug
- `is_stale() -> bool` — Compare file mtime vs last parse time

**Edge cases:** File missing → log warning, return `[]`. New sections added mid-file → detected on re-parse. No Tech Stack line → empty list.

**Test with the actual PROJECT_SWEEP_SUMMARIES.md.** Verify all 17 projects parsed with correct fields.

**Acceptance:** Parses all 17 projects from the real sweep file. Each project has non-empty name, type, summary, tech_stack.

---

### Task 1.3: Implement project indexing
| Field | Value |
|-------|-------|
| **Files** | Add methods to `backend/app/services/project_sweep_service.py` |
| **Agent** | `@data-engineer` |
| **Complexity** | 3 |
| **Deps** | 1.2 |

**Action:** Add indexing methods to `ProjectSweepService`:
- `get_by_domain(domain: str) -> list[ProjectEntry]`
- `get_by_tech(tech: str) -> list[ProjectEntry]`
- `search(keyword: str) -> list[ProjectEntry]` — Case-insensitive search across name, summary, tech_stack, domains
- Build in-memory index on parse: `{domain: [project_ids]}`, `{tech: [project_ids]}`

**Acceptance:** `search("react")` returns projects using React. `get_by_domain("ML")` returns ML projects.

---

### Task 1.4: Implement sweep file change detection
| Field | Value |
|-------|-------|
| **Files** | Add to `backend/app/services/project_sweep_service.py` |
| **Agent** | `@data-engineer` |
| **Complexity** | 2 |
| **Deps** | 1.2 |

**Action:** `is_stale()` checks file's `os.path.getmtime()` vs last parsed timestamp. `get_all()` auto-reparses if stale. On app startup (in `main.py`), call `get_all()` to warm cache.

**Acceptance:** Change the sweep file mtime (touch it) → next `get_all()` triggers re-parse. Log message: "Sweep file changed, re-parsed 17 projects."

---

### Task 1.5: Implement HistoryService
| Field | Value |
|-------|-------|
| **Files** | `backend/app/services/history_service.py` |
| **Agent** | `@data-engineer` |
| **Complexity** | 5 |
| **Deps** | 0.5 |

**Action:** Implement `HistoryService` class managing per-application JSON files in `data/applications/`.

**ID generation:** `app-YYYYMMDD-NNN` where NNN is zero-padded daily counter (e.g., first app on June 25 → `app-20260625-001`, second → `-002`).

**Methods:**
- `async def create(app: Application) -> Application` — Generate ID if missing, save JSON, return saved
- `async def get(id: str) -> Application | None` — Read and parse JSON
- `async def list_all() -> list[Application]` — List files sorted by created_at desc, return summaries (without full generated content for performance)
- `async def update(app: Application) -> Application` — Overwrite existing file
- `async def delete(id: str) -> bool` — Delete file, return True if existed
- `async def count() -> int` — Count files in directory

**File format:** One JSON file per application, pretty-printed with `indent=2`.

**Edge cases:** Concurrent creates → file lock or retry. Delete non-existent → return False. Corrupt JSON → log + raise.

**Acceptance:** Create → list shows it. Get by ID returns it. Delete → list doesn't show it.

---

### Task 1.6: Write data layer tests
| Field | Value |
|-------|-------|
| **Files** | `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_profile_service.py`, `backend/tests/test_project_sweep_service.py`, `backend/tests/test_history_service.py` |
| **Agent** | `@tester` |
| **Complexity** | 7 |
| **Deps** | 1.1, 1.2, 1.5 |

**Action:** Write comprehensive tests:

`conftest.py`:
- Fixture: `tmp_data_dir(tmp_path)` — temp directory for test data
- Fixture: `sample_sweep_file` — minimal markdown with 2-3 fake projects
- Fixture: `sample_profile` — minimal UserProfile with required fields

`test_profile_service.py`:
- Test load default when file missing
- Test save → load round-trip
- Test invalid YAML raises error
- Test exists() returns True/False
- Test partial profile fills defaults

`test_project_sweep_service.py`:
- Test parse with actual sweep file (copy into temp)
- Test all 17 projects found, all have names
- Test empty file returns []
- Test refresh invalidates cache
- Test stale detection (touch file, check stale)
- Test search/get_by_domain/get_by_id

`test_history_service.py`:
- Test create → get → list → delete flow
- Test delete non-existent returns False
- Test list returns correct order (newest first)
- Test update modifies existing record
- Test count increments correctly

**Acceptance:** All tests pass. `pytest backend/tests/ -v` shows no failures.

---

## Phase 2: LLM Integration (5 tasks, 24 complexity)

### Task 2.1: Implement LLMService
| Field | Value |
|-------|-------|
| **Files** | `backend/app/services/llm_service.py` |
| **Agent** | `@model-scientist` |
| **Complexity** | 6 |
| **Deps** | 0.4, 0.5 |

**Action:** Implement `LLMService` class as specified in PLAN.md §5 and §2.1.

**Auth setup:** LiteLLM reads `GEMINI_API_KEY` from the environment for `gemini/*` models. The service must set this before making calls:
```python
def __init__(self, config: LLMConfig = None, settings: Settings = None):
    # If no config, load from Settings
    if settings:
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
```

**Core methods:**
    
    async def generate(
        self, messages: list[dict], task: str = "default",
        temperature: float = 0.3, max_tokens: int = 4096,
        stream: bool = False
    ) -> str | AsyncIterator[str]
    # Uses litellm.acompletion(). If stream=True, yields tokens via async generator.
    
    async def generate_structured(
        self, messages: list[dict], task: str = "default",
        response_model: type[BaseModel] = None,
        temperature: float = 0.3
    ) -> BaseModel
    # Calls generate(), then parses JSON response into response_model.
    # Retries once on JSON parse failure with "Fix your JSON output" instruction.
    
    def get_model_for_task(self, task: str) -> str
    # Returns "provider/model" string. If task has per-task config, use that.
    # Otherwise use default.
    
    async def validate_connection(self) -> bool
    # Sends "Hello" → checks if response is received.
```

**OpenAI-client block (commented, v1.1 ready):**
```python
# ▼▼▼ v1.1: DeepSeek swap-in — uncomment when ready ▼▼▼
# from openai import OpenAI
# self.deepseek_client = OpenAI(
#     api_key=os.getenv("DEEPSEEK_API_KEY"),
#     base_url="https://api.deepseek.com/v1"
# )
```

**LLMConfig model** (in `backend/app/models/generation.py`):
```python
class TaskModelConfig(BaseModel):
    provider: str = "google"
    model: str = "gemini/gemini-2.5-pro"

class LLMConfig(BaseModel):
    default_provider: str = "google"
    default_model: str = "gemini/gemini-2.5-pro"
    tasks: dict[str, TaskModelConfig] = {}
```

**Error classes**, all inheriting from `LLMServiceError(Exception)`:
- `LLMConnectionError` — API unreachable
- `LLMAuthError` — Bad API key
- `LLMRateLimitError` — Rate limited
- `LLMParseError` — Couldn't parse response

**Acceptance:** With valid `GEMINI_API_KEY` set via `settings.configure_litellm()`, `await llm.generate([{"role":"user","content":"Say hi"}])` returns a response. Streaming works with `async for token in llm.generate(... stream=True)`.

---

### Task 2.2: Implement LLM config API
| Field | Value |
|-------|-------|
| **Files** | `backend/app/api/config.py` (stub for now), integrate with `LLMService` |
| **Agent** | `@model-scientist` |
| **Complexity** | 2 |
| **Deps** | 2.1 |

**Action:** Ensure `LLMService` can accept runtime config overrides. The config model stores per-task model choices. Default is "everything → Gemini". v1.1 will add DeepSeek for keyword_analysis.

**Acceptance:** Config model serializes/deserializes correctly.

---

### Task 2.3: Implement PromptManager
| Field | Value |
|-------|-------|
| **Files** | `backend/app/services/prompt_manager.py` |
| **Agent** | `@model-scientist` |
| **Complexity** | 3 |
| **Deps** | 0.4 |

**Action:** Implement `PromptManager` class with env-var override support:

The manager checks for env var overrides before falling back to `.j2` files, so users can tune prompts in `.env` without touching code.

```python
class PromptManager:
    def __init__(self, templates_dir: Path, settings: Settings)
    # Templates dir = app/templates/prompts/
    # Stores settings reference for env-var prompt overrides
    # Maps template names to their env var keys:
    #   "project_matching"  → settings.prompt_matching
    #   "keyword_analysis"  → settings.prompt_keyword_analysis
    #   "resume_points"     → settings.prompt_resume_points
    #   "resume_writeup"    → settings.prompt_resume_writeup
    
    def render(self, template_name: str, context: dict) -> str
    # 1. Check if settings has prompt_{template_name} override → use that string as template
    # 2. Otherwise load the .j2 file from disk
    # 3. Render with Jinja2 + context dict
    # 4. Return rendered string
    
    def list_templates(self) -> list[str]
    # Return template names without .j2 extension
    
    def reload(self) -> None
    # Force reload all templates from disk (re-reads env overrides too)
```

**Override flow:**
```
render("resume_points", context)
  ├─ settings.prompt_resume_points is set?
  │   └─ YES → Use settings.prompt_resume_points as Jinja2 template string
  │            (env var value supports {{ variables }} same as .j2 files)
  └─ NO  → Load resume_points.j2 from disk
            Then render with Jinja2 environment
```

Use `jinja2.Environment` with `undefined=jinja2.StrictUndefined` (fails fast on missing variables).

**Acceptance:** 
- Default: `prompt_manager.render("project_matching", {...})` renders from `.j2` file
- With `PROMPT_RESUME_POINTS` env var set: same call renders from env var instead
- `reload()` picks up env var changes without restart

---

### Task 2.4: Create all prompt templates
| Field | Value |
|-------|-------|
| **Files** | `backend/app/templates/prompts/project_matching.j2`, `resume_points.j2`, `resume_writeup.j2`, `keyword_analysis.j2` |
| **Agent** | `@model-scientist` |
| **Complexity** | 6 |
| **Deps** | 2.3 |

**Action:** Write the four prompt templates exactly as specified in PLAN.md §6.1–§6.4.

Key requirements per template:
- **project_matching.j2:** Emits "ONLY valid JSON array". Includes all project fields. Instructs LLM to return format: `[{"project_id": "...", "relevance_score": 0.0-1.0, "reasoning": "..."}]`
- **resume_points.j2:** Emits "ONLY valid JSON array of strings". Includes action verb rule, quantification rule, keyword incorporation rule.
- **resume_writeup.j2:** Emits JSON with organized sections. Deduplication instruction.
- **keyword_analysis.j2:** Emits structured JSON with all keyword categories.

**Acceptance:** Each template renders without Jinja2 errors when given a valid context dict.

---

### Task 2.5: Write LLM service tests
| Field | Value |
|-------|-------|
| **Files** | `backend/tests/test_llm_service.py`, `backend/tests/test_prompt_manager.py` |
| **Agent** | `@tester` |
| **Complexity** | 7 |
| **Deps** | 2.1, 2.3, 2.4 |

**Action:**

`test_llm_service.py`:
- Mock `litellm.acompletion` with `AsyncMock`
- Test `generate()` returns correct text
- Test `generate_structured()` parses response into Pydantic model
- Test streaming yields tokens
- Test per-task model routing
- Test error mapping (HTTPError → LLMAuthError, etc.)
- Test `validate_connection()` success/failure

`test_prompt_manager.py`:
- Test render with valid context
- Test render with missing variable raises `jinja2.UndefinedError`
- Test `list_templates()` returns 4 names
- Test template reload

**Acceptance:** All tests pass. Mock litellm for deterministic testing (no real API calls in unit tests).

---

## Phase 3: Generation Pipeline (9 tasks, 53 complexity)

### Task 3.1: Implement KeywordAnalysisService
| Field | Value |
|-------|-------|
| **Files** | `backend/app/pipeline/__init__.py`, `backend/app/pipeline/keyword_analysis_service.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 4 |
| **Deps** | 2.1, 2.3, 2.4 |

**Action:** Implement `KeywordAnalysisService`:
```python
class KeywordAnalysisService:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager)
    
    async def analyze(
        self, job_title: str, company_name: str, job_description: str
    ) -> dict:
        # 1. Render keyword_analysis.j2 with (job_title, company_name, job_description)
        # 2. Call llm_service.generate_structured(task="keyword_analysis")
        # 3. Return parsed dict with keys: required_skills, preferred_skills, domains, etc.
    
    def extract_keywords_text(self, analysis: dict) -> str:
        """Format keywords into a comma-separated string for prompt injection.
        Returns: "required: Python, PyTorch, Docker | preferred: Kubernetes | domains: ML, CV"
        """
```

**Acceptance:** `analyze()` returns dict with all keyword categories. `extract_keywords_text()` produces usable keyword string.

---

### Task 3.2: Implement MatchingService
| Field | Value |
|-------|-------|
| **Files** | `backend/app/pipeline/matching_service.py` |
| **Agent** | `@model-scientist` |
| **Complexity** | 5 |
| **Deps** | 2.1, 2.3, 2.4, 1.2 |

**Action:** Implement `MatchingService`:
```python
class MatchingService:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager)
    
    async def match(
        self, job_title: str, company_name: str, job_description: str,
        projects: list[ProjectEntry], company_description: str = ""
    ) -> list[MatchResult]:
        # 1. Render project_matching.j2 with all projects + JD info
        # 2. Call llm_service.generate_structured(task="matching", response_model=List[MatchResult])
        # 3. Validate: all scores 0-1, project_ids exist in input
        # 4. Sort by score descending
        # 5. Return top 8 (or fewer if fewer projects)
    
    def format_projects_for_prompt(self, projects: list[ProjectEntry]) -> str:
        """Format projects section of the prompt template.
        Projects with more tech stack overlap get listed first (primacy effect).
        """
```

**Acceptance:** Given a JD about "ML Infrastructure Engineer", returns projects like Sentry, SpaceDebrisResearch, RecSysProject with high scores.

---

### Task 3.3: Implement ResumePointsGenerator
| Field | Value |
|-------|-------|
| **Files** | `backend/app/pipeline/resume_points_generator.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 7 |
| **Deps** | 2.1, 2.3, 2.4, 1.1, 1.2 |

**Action:** Implement `ResumePointsGenerator`:
```python
class ResumePointsGenerator:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager)
    
    async def generate_all(
        self, job_title: str, company_name: str, job_description: str,
        jd_keywords: dict, selected_projects: list[ProjectEntry],
        profile: UserProfile, tone: str = "professional",
        on_token: Callable[[str, str], Awaitable[None]] = None,
        on_section_complete: Callable[[str, list[str]], Awaitable[None]] = None,
    ) -> list[SectionPoints]:
        """
        Generate bullet points for all sections:
        - For each selected project → project section
        - For each experience entry → experience section
        
        Yields tokens via on_token(section_key, token)
        Yields completion via on_section_complete(section_key, bullets)
        """
    
    async def generate_for_section(
        self, section_type: str, section_name: str, section_details: str,
        job_title: str, company_name: str, jd_keywords_text: str,
        tone: str = "professional", num_bullets: int = 4,
        on_token: Callable = None,
    ) -> list[str]:
        # Render resume_points.j2 and call LLM
        # Parse JSON array response
        # Return list of bullet point strings
    
    async def regenerate_section(
        self, section_key: str, custom_instructions: str = "",
        previous_bullets: list[str] = None,
    ) -> list[str]:
        # Same as generate_for_section but includes previous bullets 
        # and custom instructions in the prompt
    
    def _format_project_details(self, project: ProjectEntry) -> str:
        """Format a project entry into a text block for the prompt."""
    
    def _format_experience_details(self, exp: Experience) -> str:
        """Format an experience entry into a text block for the prompt."""
```

**Streaming:** Token callback receives `(section_key, token_text)`. The orchestrator wraps this into SSE events.

**Acceptance:** With mocked LLM, generates bullet points for projects and experience. Streaming callback fires per token. Section structure is correct.

---

### Task 3.4: Implement ResumeWriter
| Field | Value |
|-------|-------|
| **Files** | `backend/app/pipeline/resume_writer.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 5 |
| **Deps** | 3.3, 1.1 |

**Action:** Implement `ResumeWriter`:
```python
class ResumeWriter:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager)
    
    async def compile_resume(
        self, sections: list[SectionPoints], profile: UserProfile,
        job_title: str, company_name: str,
        on_token: Callable = None,
    ) -> list[SectionPoints]:
        """
        1. Run deduplicate() to remove overlapping bullets
        2. Order sections: Education → Experience → Projects → Skills → Leadership
           (or as defined in profile)
        3. Optionally call LLM to polish (if configured)
        4. Return compiled sections
        """
    
    def deduplicate(self, sections: list[SectionPoints]) -> list[SectionPoints]:
        """
        Remove bullets with >80% similarity across sections.
        Simple approach: 
        1. Normalize text (lowercase, remove punctuation, split into words)
        2. For each pair of bullets, compute Jaccard similarity of word sets
        3. If similarity > 0.8, keep the one from the more relevant section
        """
    
    def order_sections(
        self, sections: list[SectionPoints], profile: UserProfile
    ) -> list[SectionPoints]:
        """Order sections according to profile's section_order preference.
        Default: Education, Experience, Projects, Skills, Leadership
        """
```

**Acceptance:** Deduplication removes 100% identical bullets. Partial duplicates (>80% similar) flagged. Sections ordered correctly.

---

### Task 3.5: Create LaTeX Jinja2 template (with Publications + section_order)
| Field | Value |
|-------|-------|
| **Files** | `backend/app/templates/latex/resume_template.tex.j2`, `backend/app/pipeline/latex_renderer.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 7 |
| **Deps** | 0.2, `docs/template.tex` |

**Action:**

**Part A:** Convert `docs/template.tex` into `resume_template.tex.j2`:

The Jinja2 template must:
- Preserve ALL LaTeX packages, custom commands, and configuration from the original
- Replace hardcoded content with Jinja2 variables:
  - Name, contact info → `{{ profile.name }}`, `{{ profile.email }}`, etc.
  - Education entries → `{% for edu in profile.education %}`
  - Experience section → `{% for exp in profile.experience %}` with bullet loop
  - Projects section → `{% for proj in resume_sections.projects %}` with generated bullets
  - **Publications section (NEW)** → `{% for pub in profile.publications %}` using `\resumeSubheading`:
    ```latex
    %-----------PUBLICATIONS-----------
    \section{Publications}
      \resumeSubHeadingListStart
        \resumeSubheading
          {{ pub.title | escape_latex }}{{ pub.year }}
          {\small\textit{{ pub.authors | escape_latex }}}{{ pub.venue | escape_latex }}
      \resumeSubHeadingListEnd
    ```
  - Skills → `{% for category, items in profile.skills %}`
  - Leadership → `{% for lead in profile.leadership %}`
- **Iterate sections in `profile.section_order` order** — the template receives a `section_order` list and renders sections in that sequence. Each section checks `{% if ... %}` to skip empty sections.
- Include conditionals: `{% if section.bullets %}` to skip empty sections
- Escape special characters: `{{ bullet.text | escape_latex }}`

**Part B:** Implement `LaTeXRenderer`:
```python
class LaTeXRenderer:
    def __init__(self, template_path: Path)
    
    def render(self, profile: UserProfile, sections: list[SectionPoints]) -> str:
        # 1. Create Jinja2 Environment with custom filters
        # 2. Load template
        # 3. Build context: profile + sections + section_order from profile
        # 4. Render with context
        # 5. Validate output
        # 6. Return .tex string
    
    def validate_latex(self, tex_content: str) -> list[str]:
        # Return warnings list. Empty = clean.
        # Checks: balanced braces, \begin/\end{document}, required sections present
```

**Jinja2 custom filters** (register on the Environment):
- `escape_latex(text)`: Escape `# $ % & ~ _ ^ \ { }`
- `format_skills(skills)`: Format as `\textbf{Category}: items \\`
- `format_dates(start, end)`: "Aug 2025 -- May 2027" or "Aug 2025 -- Present"

**Section rendering order** (from `profile.section_order`, default):
```
education → skills → projects → experience → publications → leadership → certifications
```
Each section in the template wraps in `{% if has_content(section) %}` to skip empty ones.

**Acceptance:** Rendering with sample data (including publications) produces valid .tex. Sections appear in the order specified by `section_order`. Empty sections are omitted.

---

### Task 3.6: Implement Orchestrator (part 1 — full pipeline)
| Field | Value |
|-------|-------|
| **Files** | `backend/app/pipeline/orchestrator.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 7 |
| **Deps** | 3.1, 3.2, 3.3, 3.4, 3.5, 1.1, 1.5 |

**Action:** Implement `Orchestrator` class:

```python
class Orchestrator:
    def __init__(self, ...):
        # Initialize all services
    
    async def run_full_pipeline(
        self, request: GenerationRequest,
        emit: Callable[[str, dict], Awaitable[None]],
    ) -> Application:
        """
        Full pipeline:
        
        1. Create Application in PENDING status → save to history → emit stage
        2. Load projects from ProjectSweepService → emit stage
        3. Match projects (MatchingService) → emit stage + result
        4. Analyze keywords (KeywordAnalysisService) → emit stage
        5. Generate points (ResumePointsGenerator) → emit tokens
        6. Write resume (ResumeWriter) → emit stage
        7. Render LaTeX (LaTeXRenderer) → emit stage + latex content
        8. Update Application to COMPLETED → save → emit complete
        """
    
    async def run_points_only(
        self, request: GenerationRequest,
        emit: Callable[[str, dict], Awaitable[None]],
    ) -> Application:
        """Steps 1-5 only. Stops after points generation. Used for Review & Edit phase."""
    
    async def run_resume_only(
        self, application_id: str,
        emit: Callable[[str, dict], Awaitable[None]],
    ) -> Application:
        """Steps 6-8 only. Used when user already has points and wants to re-export."""
    
    async def regenerate_section(
        self, application_id: str, section_key: str,
        custom_instructions: str = "",
        emit: Callable[[str, dict], Awaitable[None]],
    ) -> Application:
        """Re-run points generation for a single section, update application."""
```

**SSE Event emission:** The `emit` callback is called with `(event_type, data_dict)`. The API layer wraps these in SSE format.

**Error handling per stage:** If any stage fails, emit error event, update Application status to FAILED with error_message, save, return.

**Acceptance:** Full pipeline with mocked LLM completes all stages and returns Application with generated content.

---

### Task 3.7: Implement PDFCompiler (MiKTeX wrapper)
| Field | Value |
|-------|-------|
| **Files** | `backend/app/pipeline/pdf_compiler.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 4 |
| **Deps** | 3.5 |

**Action:** Implement `PDFCompiler` class that wraps MiKTeX's `pdflatex.exe`:

```python
class PDFCompiler:
    def __init__(self, pdflatex_path: str | None, output_dir: Path)
    # If pdflatex_path is None or empty, compilation is disabled
    # (the app still generates .tex, just skips PDF step)
    
    async def compile(self, tex_content: str, filename: str = "resume") -> PDFResult
    # 1. Write tex_content to a temp .tex file in output_dir
    # 2. Run pdflatex (subprocess) with:
    #    - 3-pass sequence for cross-references (pdflatex -interaction=nonstopmode)
    #    - Timeout: 30 seconds
    #    - Working directory: output_dir
    # 3. Parse stdout/stderr for errors/warnings
    # 4. Check output .pdf exists
    # 5. Return PDFResult
    
    async def compile_with_retry(self, tex_content: str, filename: str = "resume", max_retries: int = 2) -> PDFResult
    # Retry on transient compilation failures
    
    def is_available(self) -> bool
    # Returns True if pdflatex_path is set and binary exists
    
    def get_compiler_version(self) -> str
    # Run "pdflatex --version" and return first line
```

```python
class PDFResult(BaseModel):
    success: bool
    pdf_path: Optional[Path] = None
    pdf_bytes: Optional[bytes] = None  # for serving in HTTP response
    log: str = ""  # full pdflatex log
    errors: list[str] = []
    warnings: list[str] = []
    page_count: Optional[int] = None
```

**Compilation details:**
- Run `pdflatex -interaction=nonstopmode -halt-on-error {filename}.tex`
- Wait for process completion with 30s timeout
- Read `.log` file for errors/warnings parsing
- Run twice (standard LaTeX practice for cross-references, though simple resumes usually need one pass)
- Delete intermediate files (`.aux`, `.log`, `.out`) unless `--keep-temp` flag is set
- Handle MiKTeX auto-install prompts: set environment variable `miktex_auto_install=yes` or `-enable-installer` flag

**Edge cases:**
- Compiler not installed → `is_available()` returns False, `compile()` raises `PDFCompilerUnavailableError`
- Corrupted .tex → parse error from pdflatex, return with error messages
- Subprocess timeout → `PDFCompilerTimeoutError`
- Unicode characters → run with `-shell-escape` disabled, ensure .tex is UTF-8 encoded
- Zero-byte PDF → treat as compilation failure

**Integration:** The PDFCompiler is NOT part of the Orchestrator generation pipeline. It's called separately:
- The generation pipeline produces `.tex` output
- The Export API endpoint offers both `.tex` download AND `.pdf` download (which triggers `PDFCompiler.compile()`)
- The complete SSE event carries `latex` content; frontend can offer "Download PDF" which calls a separate `/api/resume/{id}/pdf` endpoint

**Acceptance:** `PDFCompiler` with valid pdflatex_path compiles a simple .tex to PDF. With invalid path, `is_available()` returns False. Errors from broken .tex are captured and returned.

---

### Task 3.8: Implement Orchestrator (part 2 — SSE integration)
| Field | Value |
|-------|-------|
| **Files** | `backend/app/utils/sse.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 3 |
| **Deps** | 3.6 |

**Action:** Implement SSE helpers:
```python
def format_sse_event(event: str, data: dict) -> str:
    """Format as SSE: event: {event}\\ndata: {json}\\n\\n"""

class SSEEventBuilder:
    @staticmethod
    def stage(stage: str, status: str, **extra) -> tuple[str, dict]:
        return ("stage", {"stage": stage, "status": status, **extra})
    
    @staticmethod
    def token(section: str, token: str) -> tuple[str, dict]:
        return ("token", {"section": section, "token": token})
    
    @staticmethod
    def section_complete(section: str, bullets: list[str], tokens_used: int) -> tuple[str, dict]:
        return ("section_complete", {"section": section, "bullets": bullets, "tokens_used": tokens_used})
    
    @staticmethod
    def error(stage: str, message: str) -> tuple[str, dict]:
        return ("error", {"stage": stage, "message": message})
    
    @staticmethod
    def complete(application_id: str, latex: str = None, sections: list = None, total_tokens: int = 0) -> tuple[str, dict]:
        data = {"application_id": application_id, "total_tokens": total_tokens}
        if latex: data["latex"] = latex
        if sections: data["sections"] = sections
        return ("complete", data)
```

**Acceptance:** SSE events are correctly formatted strings. Event builder produces correct event-type/data pairs.

---

### Task 3.9: Write pipeline tests (including PDFCompiler)
| Field | Value |
|-------|-------|
| **Files** | `backend/tests/test_matching_service.py`, `backend/tests/test_resume_points_generator.py`, `backend/tests/test_resume_writer.py`, `backend/tests/test_latex_renderer.py`, `backend/tests/test_orchestrator.py`, `backend/tests/test_pdf_compiler.py` |
| **Agent** | `@tester` |
| **Complexity** | 9 |
| **Deps** | 3.2, 3.3, 3.4, 3.5, 3.6, 3.7 |

**Action:** Write tests for each pipeline service:

`test_matching_service.py`:
- Mock LLM to return fixed JSON match list
- Verify correct MatchResults returned
- Test with empty project list
- Test score validation (rejects >1.0 or <0.0)
- Test sorting by score

`test_resume_points_generator.py`:
- Mock LLM to return JSON bullet array
- Verify SectionPoints have correct section_key and bullets
- Test streaming callback receives tokens
- Test regenerate_section produces new bullets
- Test with empty projects list

`test_resume_writer.py`:
- Test deduplication with identical bullets
- Test order_sections produces correct order
- Test empty sections are skipped

`test_latex_renderer.py`:
- Test render produces valid .tex
- Test validate catches missing \end{document}
- Test escape_latex prevents character injection
- Test with empty profile sections

`test_orchestrator.py`:
- Test full pipeline with all mocks
- Test error propagation (LLM failure → FAILED status)
- Test points-only pipeline stops after points
- Test resume-only pipeline uses existing data
- Test regenerate_section updates single section

`test_pdf_compiler.py`:
- Test compiler unavailable when pdflatex_path is None
- Test compile produces valid .pdf (requires pdflatex on system — skip if unavailable)
- Test compile with broken .tex returns errors
- Test invalid pdflatex_path raises appropriate error
- Test retry logic on transient failure

**Acceptance:** All tests pass. Edge cases covered.

---

## Phase 4: API Layer (7 tasks, 26 complexity)

### Task 4.1: Implement FastAPI application factory
| Field | Value |
|-------|-------|
| **Files** | `backend/app/main.py`, `backend/app/api/__init__.py`, `backend/app/utils/__init__.py`, `backend/app/utils/file_utils.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 4 |
| **Deps** | 0.4, 1.2, 1.4 |

**Action:** Create `backend/app/main.py`:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize services, warm sweep cache
    from app.services.project_sweep_service import ProjectSweepService
    sweep_service = ProjectSweepService(settings.sweep_file_path)
    projects = await sweep_service.get_all()  # warm cache
    logger.info(f"Loaded {len(projects)} projects from sweep file")
    yield
    # Shutdown: nothing to clean up

def create_app() -> FastAPI:
    app = FastAPI(title="Resume Pipeline", version="1.0.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=[settings.cors_origins], ...)
    app.include_router(api_router, prefix="/api")
    return app

app = create_app()
```

Also implement:
- `backend/app/utils/file_utils.py`: helpers for file path resolution, ensuring directories exist
- `backend/app/utils/__init__.py`: empty
- `backend/app/api/__init__.py`: empty

**Acceptance:** `uv run uvicorn app.main:app` starts on :8000. `GET /docs` shows Swagger.

---

### Task 4.2: Implement profile API endpoints
| Field | Value |
|-------|-------|
| **Files** | `backend/app/api/profile.py`, `backend/app/api/router.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 3 |
| **Deps** | 4.1, 1.1 |

**Action:**

`backend/app/api/router.py` — Aggregate all routers:
```python
from fastapi import APIRouter
from app.api import profile, projects, resume, history

router = APIRouter()
router.include_router(profile.router, prefix="/profile", tags=["Profile"])
router.include_router(projects.router, prefix="/projects", tags=["Projects"])
router.include_router(resume.router, prefix="/generate", tags=["Generation"])
router.include_router(history.router, prefix="/applications", tags=["History"])
```

`backend/app/api/profile.py`:
```python
router = APIRouter()

@router.get("")
async def get_profile(...) -> UserProfile
@router.put("")
async def update_profile(profile: UserProfile) -> UserProfile
@router.get("/exists")
async def profile_exists() -> dict
```

**Acceptance:** `GET /api/profile` returns profile. `PUT /api/profile` updates it.

---

### Task 4.3: Implement projects API endpoints
| Field | Value |
|-------|-------|
| **Files** | `backend/app/api/projects.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 3 |
| **Deps** | 4.1, 1.2, 1.3, 1.4, 3.2 |

**Action:**
```python
@router.get("")
async def list_projects() -> dict
# Returns {projects: [...], last_parsed, file_modified, stale}

@router.post("/refresh")
async def refresh_projects() -> dict
# Returns {status: "ok", projects_count: N, parsed_at: "..."}

@router.post("/match")
async def match_projects(request: MatchRequest) -> dict
# Returns {matches: [...]}
```

**Acceptance:** Project list returns all 17 parsed projects. Match returns ranked results.

---

### Task 4.4: Implement generation API endpoints (SSE streaming + PDF export)
| Field | Value |
|-------|-------|
| **Files** | `backend/app/api/resume.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 7 |
| **Deps** | 4.1, 3.6, 3.7, 3.8 |

**Action:**

**Part A — SSE generation endpoints:**
```python
@router.post("/points")
async def generate_points(request: GenerationRequest):
    """SSE-streaming endpoint for bullet point generation."""
    orchestrator = get_orchestrator()  # from dependency
    
    async def event_generator():
        async def emit(event_type: str, data: dict):
            yield format_sse_event(event_type, data)
        
        async for event in orchestrator.run_points_pipeline(request, emit):
            yield event
    
    return StreamingResponse(event_generator(), media_type="text/event-stream", 
                            headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                                    "X-Accel-Buffering": "no"})

@router.post("/resume")
async def generate_resume(request: ResumeExportRequest):
    """SSE-streaming endpoint for full resume + .tex generation."""
    # Similar pattern, calls orchestrator.run_resume_only()

@router.post("/regenerate-section")
async def regenerate_section(request: PointsRegenerateRequest):
    """Regenerate a single section's bullet points."""
    # Calls orchestrator.regenerate_section()
```

**Part B — PDF export endpoint (NEW):**
```python
@router.get("/{application_id}/pdf")
async def export_pdf(application_id: str):
    """
    Generate and download PDF version of the resume.
    1. Load application from history
    2. Get the saved .tex content
    3. Run PDFCompiler.compile(tex_content)
    4. Return PDF as StreamingResponse with Content-Type: application/pdf
    5. If compiler unavailable, return 501 Not Implemented with clear message
    """
    app = await history_service.get(application_id)
    if not app or not app.generated_content or not app.generated_content.latex:
        raise HTTPException(404, "No generated resume found for this application")
    
    compiler = get_pdf_compiler()  # from dependency
    if not compiler.is_available():
        raise HTTPException(501, detail="PDF compilation not available. Install MiKTeX and set PDFLATEX_PATH.")
    
    result = await compiler.compile(app.generated_content.latex, filename=f"resume_{application_id}")
    if not result.success:
        raise HTTPException(500, detail=f"PDF compilation failed: {'; '.join(result.errors)}")
    
    return StreamingResponse(
        io.BytesIO(result.pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="resume_{application_id}.pdf"'}
    )

@router.get("/{application_id}/tex")
async def export_tex(application_id: str):
    """Download the raw .tex file (non-streaming)."""
    app = await history_service.get(application_id)
    if not app or not app.generated_content or not app.generated_content.latex:
        raise HTTPException(404, "No generated resume found for this application")
    return PlainTextResponse(
        app.generated_content.latex,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="resume_{application_id}.tex"'}
    )
```

**Important:** SSE streaming requires careful implementation. The `event_generator()` async generator must:
1. Catch errors and emit error events instead of crashing
2. Use `emit()` as a callback into the orchestrator
3. Set proper SSE headers (no buffering)

**Acceptance:** `curl -N http://localhost:8000/api/generate/points -d "..."` streams SSE events. `curl http://localhost:8000/api/generate/{id}/tex` downloads .tex. `curl http://localhost:8000/api/generate/{id}/pdf` downloads PDF if compiler is available (or returns 501 if not).

---

### Task 4.5: Implement history API endpoints
| Field | Value |
|-------|-------|
| **Files** | `backend/app/api/history.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 2 |
| **Deps** | 4.1, 1.5 |

**Action:**
```python
@router.get("")
async def list_applications() -> dict
@router.get("/{application_id}")
async def get_application(application_id: str) -> Application
@router.delete("/{application_id}")
async def delete_application(application_id: str) -> dict
```

**Acceptance:** CRUD operations work with JSON file storage.

---

### Task 4.6: Implement LLM config endpoint
| Field | Value |
|-------|-------|
| **Files** | Add to `backend/app/api/config.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 2 |
| **Deps** | 4.1, 2.2 |

**Action:**
```python
@router.get("/llm")
async def get_llm_config() -> LLMConfig

@router.put("/llm")
async def update_llm_config(config: LLMConfig) -> LLMConfig

@router.get("/pdf-available")
async def is_pdf_available() -> dict:
    """Check if PDF compilation is configured and available."""
    compiler = get_pdf_compiler()
    return {"available": compiler.is_available()}
```

Config is stored in-memory (not persisted to file in v1.0). Defaults loaded from `Settings`.

**Frontend use:** `GET /api/config/pdf-available` → `{ "available": true/false }` → show/hide PDF download button, show status indicator on export page.

**Acceptance:** Config read/update works in-memory. PDF availability endpoint returns correct status.

---

### Task 4.7: Write API integration tests
| Field | Value |
|-------|-------|
| **Files** | `backend/tests/test_api.py` |
| **Agent** | `@tester` |
| **Complexity** | 5 |
| **Deps** | 4.2, 4.3, 4.4, 4.5, 4.6 |

**Action:** Use FastAPI `TestClient` to test endpoints:
- Profile CRUD
- Project list + match (with mocked LLM)
- Generation SSE streaming (with mocked orchestrator)
- Application history CRUD
- Config read/update
- Error responses (404, 422, 500)
- Health check endpoint `GET /api/health`

**Acceptance:** All endpoints tested. Mock external services.

---

## Phase 5: Frontend (11 tasks, 47 complexity)

### Task 5.1: Create React app shell + routing
| Field | Value |
|-------|-------|
| **Files** | `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/components/layout/AppLayout.tsx`, `frontend/src/components/layout/Navbar.tsx`, `frontend/src/styles/variables.css`, `frontend/src/styles/global.css`, `frontend/src/styles/theme.css` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 5 |
| **Deps** | 0.3 |

**Action:** Set up the app shell:

`main.tsx`: Create QueryClient, wrap App with QueryClientProvider and BrowserRouter.

`App.tsx`: Define routes using react-router-dom v7:
```
/                    → Dashboard
/app/new             → NewApplication
/app/{id}/edit       → ReviewEdit
/app/{id}/export     → ExportResume
/profile             → ProfilePage
/history             → HistoryPage
```

`AppLayout.tsx`: Sidebar (240px, dark bg) + main content area. Sidebar has nav links.

`Navbar.tsx`: Top bar with app name "Resume Pipeline" and status indicator.

**Dark theme** (CSS custom properties in `variables.css`):
```css
:root {
  --bg-primary: #0d1117;
  --bg-secondary: #161b22;
  --bg-card: #1c2128;
  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --accent: #58a6ff;
  --accent-hover: #79c0ff;
  --border: #30363d;
  --success: #3fb950;
  --warning: #d29922;
  --error: #f85149;
  --font-sans: 'Inter', -apple-system, system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --radius: 8px;
  --sidebar-width: 240px;
}
```

`global.css`: Reset, body styling with dark bg, font imports (Inter, JetBrains Mono via Google Fonts CDN).

**Acceptance:** `npm run dev` shows dark-themed app shell with sidebar navigation. Routes render placeholder text.

---

### Task 5.2: Implement API client layer
| Field | Value |
|-------|-------|
| **Files** | `frontend/src/api/client.ts`, `frontend/src/api/profile.ts`, `frontend/src/api/projects.ts`, `frontend/src/api/resume.ts`, `frontend/src/api/history.ts` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 5 |
| **Deps** | 0.6, 5.1 |

**Action:** Create typed API hooks using TanStack Query + axios:

`client.ts`:
```typescript
import axios from 'axios';
export const api = axios.create({ baseURL: '/api' });
// Response interceptor for error handling
```

`profile.ts`:
```typescript
export function useProfileQuery() { return useQuery({ queryKey: ['profile'], queryFn: ... }); }
export function useUpdateProfileMutation() { return useMutation({ mutationFn: ... }); }
export function useProfileExists() { return useQuery({ queryKey: ['profile', 'exists'], queryFn: ... }); }
```

`projects.ts`:
```typescript
export function useProjectsQuery() { ... }
export function useProjectMatchMutation() { ... }
export function useRefreshProjectsMutation() { ... }
```

`resume.ts`:
```typescript
export function useGeneratePoints() {
  // Uses fetch() for SSE streaming instead of axios
  // Returns { startGeneration, abort, status, stages, tokens, sections }
  // Manages EventSource connection internally
}
export function useGenerateResume() { ... }
export function useRegenerateSection() { ... }
```

`history.ts`:
```typescript
export function useApplicationsQuery() { ... }
export function useApplicationQuery(id) { ... }
export function useDeleteApplicationMutation() { ... }
```

**SSE hook** (`useGeneratePoints` implementation):
```typescript
export function useGeneratePoints() {
  const [status, setStatus] = useState<'idle' | 'streaming' | 'complete' | 'error'>('idle');
  const [stages, setStages] = useState<Stage[]>([]);
  const [tokens, setTokens] = useState<Record<string, string[]>>({});
  const [sections, setSections] = useState<SectionPoints[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  
  const startGeneration = async (request: GenerationRequest) => {
    setStatus('streaming');
    const response = await fetch('/api/generate/points', {
      method: 'POST', body: JSON.stringify(request),
      headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
    });
    const reader = response.body!.getReader();
    // Read SSE stream, parse events, update state
    // event: stage → update stages
    // event: token → append to tokens[section]
    // event: section_complete → finalize section
    // event: complete → set status to complete
    // event: error → set status to error
  };
  
  const abort = () => abortRef.current?.abort();
  
  return { startGeneration, abort, status, stages, tokens, sections };
}
```

**Acceptance:** All hooks are typed. Query key structure is consistent (`['profile']`, `['projects']`, `['applications']`, `['applications', id]`).

---

### Task 5.3: Build Dashboard page
| Field | Value |
|-------|-------|
| **Files** | `frontend/src/pages/Dashboard.tsx` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 3 |
| **Deps** | 5.1, 5.2 |

**Action:** Dashboard shows:
- Welcome heading with user name (from profile)
- Stats row: "X applications" | "Last generated: Y date"
- "New Application" call-to-action button (navigates to `/app/new`)
- Recent applications list (last 5, from `useApplicationsQuery`)
- Loading state: skeleton cards
- Empty state: "No applications yet. Create your first!" with CTA
- Error state: error banner with retry

**Acceptance:** Dashboard renders with live data from API. Empty state shows when no apps exist.

---

### Task 5.4: Build New Application page
| Field | Value |
|-------|-------|
| **Files** | `frontend/src/pages/NewApplication.tsx`, `frontend/src/components/forms/JobDescriptionForm.tsx`, `frontend/src/components/resume/ProjectMatchCards.tsx` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 6 |
| **Deps** | 5.1, 5.2 |

**Action:** Two-stage flow:

**Stage 1: Job Description Form** (JobDescriptionForm.tsx):
- Textarea for job description (required, min 50 chars)
- Text input for company name (required)
- Text input for job title (required)
- Textarea for company description (optional)
- "Find Matching Projects" submit button
- Validation: inline error messages below fields
- Loading state on submit

**Stage 2: Project Match Results** (ProjectMatchCards.tsx):
- Shows matched projects as selectable cards
- Each card: project name, relevance score (visual bar), tech stack chips, reasoning text
- Cards are selectable (checkmark toggle), pre-selected top 5
- "Generate Resume Points" button (enabled when ≥1 project selected)
- Empty state: "No matching projects found" with option to continue with manual selection
- Loading: skeleton cards

**On "Generate Resume Points":**
- Calls `useGeneratePoints().startGeneration()`
- Navigates to Review & Edit page (`/app/{id}/edit`)

**Acceptance:** Form validates. Project match shows results. Selection works. Generate triggers SSE stream.

---

### Task 5.5: Build Review & Edit page
| Field | Value |
|-------|-------|
| **Files** | `frontend/src/pages/ReviewEdit.tsx`, `frontend/src/components/resume/SectionEditor.tsx`, `frontend/src/components/resume/BulletPointList.tsx`, `frontend/src/components/resume/ResumePreview.tsx`, `frontend/src/components/generation/GenerationProgress.tsx`, `frontend/src/components/generation/StageIndicator.tsx`, `frontend/src/components/generation/TokenStream.tsx` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 8 |
| **Deps** | 5.1, 5.2, 5.4 |

**Action:** The most complex page. Three areas:

**Area 1: Generation Progress** (top, conditional — shows during generation):
- GenerationProgress: vertical timeline of stages with status icons (↑ spinning, ✓ done, ✗ error)
- StageIndicator: per-stage box with label, status icon
- TokenStream: scrolling text area showing generated tokens in real-time

**Area 2: Section Editor** (main content, scrollable):
- List of SectionEditor components, one per section (project, experience)
- Each SectionEditor:
  - Section title (read-only)
  - BulletPointList: draggable list of editable bullet points
    - Each bullet: drag handle | textarea | delete button
    - "Add Bullet" button at bottom
  - "Regenerate" button (with optional custom instructions textarea)
  - Loading state during regeneration (skeleton bullets)

**Area 3: Action Bar** (bottom, sticky):
- "Save Draft" button
- "Export Resume (.tex)" button → navigates to Export page
- Project count, bullet count summary

**State management:**
- Local state for bullet edits (not saved to API until "Save Draft")
- Track `edited: boolean` per bullet
- Warn on navigation with unsaved changes

**Drag and drop:** Use `@dnd-kit/core` and `@dnd-kit/sortable` for bullet reordering.

**Acceptance:** Can edit bullets inline. Drag reorder works. Regenerate replaces section bullets. Generation progress shows live stages and tokens.

---

### Task 5.6: Build Export Resume page (with PDF download)
| Field | Value |
|-------|-------|
| **Files** | `frontend/src/pages/ExportResume.tsx` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 4 |
| **Deps** | 5.1, 5.2 |

**Action:** Export page with dual download options:

**Layout:**
- Split view (or tabs): LaTeX source | Compiled PDF
- LaTeX source in `<pre>` block with mono font, basic syntax highlighting (comments, commands)
- PDF preview (if compiled): `<embed>` or `<iframe>` showing the generated PDF
- Info box: Overleaf instructions + MiKTeX availability indicator

**Buttons:**
1. **"Download .tex"** → same blob-download as before
2. **"Download PDF"** → calls `GET /api/generate/{id}/pdf` endpoint
   - If 200: triggers PDF blob download with `.pdf` extension
   - If 501: shows info banner "PDF compilation unavailable. Install MiKTeX and set PDFLATEX_PATH in .env"
   - If 500: shows error banner with compilation error details
   - Loading state during compilation (spinner + "Compiling PDF...")
3. **"Copy to Clipboard"** → copies LaTeX source
4. **"Back to Edit"** link

**PDF availability indicator:** On page load, make a light check:
```typescript
// Optionally add a GET /api/config/pdf-available endpoint that returns { available: bool }
// Or just attempt the download and handle the 501 gracefully
```

**Download implementations:**
```typescript
const downloadTex = () => {
  const blob = new Blob([latexContent], { type: 'application/x-tex' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = `resume-${companyName}.tex`;
  a.click(); URL.revokeObjectURL(url);
};

const downloadPdf = async () => {
  setPdfLoading(true);
  try {
    const response = await api.get(`/generate/${applicationId}/pdf`, { responseType: 'blob' });
    const url = URL.createObjectURL(response.data);
    const a = document.createElement('a');
    a.href = url; a.download = `resume-${companyName}.pdf`;
    a.click(); URL.revokeObjectURL(url);
  } catch (err) {
    if (err.response?.status === 501) {
      setPdfError('PDF compilation not available. Configure MiKTeX in .env');
    } else {
      setPdfError('PDF compilation failed. Check LaTeX output for errors.');
    }
  } finally {
    setPdfLoading(false);
  }
};
```

**State handling:**
- `pdfLoading: boolean` — spinner during compilation
- `pdfError: string | null` — error message if compilation fails
- `pdfAvailable: boolean` — from config endpoint, show/hide PDF button

**Acceptance:** Downloads valid .tex file. PDF button attempts compilation — succeeds (downloads .pdf) or fails gracefully (informative error message).

---

### Task 5.7: Build Profile Management page (with Publications)
| Field | Value |
|-------|-------|
| **Files** | `frontend/src/pages/ProfilePage.tsx`, `frontend/src/components/forms/ProfileForm.tsx` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 6 |
| **Deps** | 5.1, 5.2 |

**Action:** Full profile editor with collapsible sections:

**Sections (collapsible):**
1. **Basic Info:** Name, Email, Phone, Location
2. **Links:** LinkedIn, GitHub, Portfolio, Website
3. **Education:** List editor — add/remove schools. Each: School, Degree, Start/End Date, Location, GPA, Coursework (tag input)
4. **Experience:** List editor. Each: Company, Role, Start/End Date, Location, Description (textarea), Highlights (bullet list)
5. **Personal Projects:** List editor. Each: Name, Tech Stack (tag input), Description, URL
6. **Skills:** Languages (tag input), Frameworks (tag input), Tools (tag input), Domains (tag input)
7. **Certifications:** List editor. Each: Name, Issuer, Date, URL
8. **Leadership:** List editor. Each: Organization, Role, Start/End, Description
9. **Publications (NEW):** List editor. Each: Title, Authors (text), Venue, Year (year picker), URL, Description (textarea)

**Section Ordering:** Drag-to-reorder section_order list OR up/down buttons. Reflects `profile.section_order` array. Changes are saved as part of profile.

**Tag input component:** Simple text input that creates chips on Enter/Comma.

**Save behavior:** "Save" button per section or global. Shows "Saved" toast. Unsaved changes warning on navigation.

**Acceptance:** Full profile including publications can be created and saved. Section order persists on reload.

---

### Task 5.8: Build Application History page
| Field | Value |
|-------|-------|
| **Files** | `frontend/src/pages/HistoryPage.tsx`, `frontend/src/components/history/ApplicationCard.tsx`, `frontend/src/components/history/ApplicationDetail.tsx` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 4 |
| **Deps** | 5.1, 5.2 |

**Action:**

**HistoryPage.tsx:** List of ApplicationCards, searchable/filterable by company name.

**ApplicationCard.tsx:**
- Company name + job title
- Created date (formatted: "June 25, 2026")
- Status badge: Completed (green), Failed (red), Draft (yellow)
- Click → expand to show ApplicationDetail inline

**ApplicationDetail.tsx:**
- Full application info (JD preview, company, selected projects)
- Generated content sections (read-only)
- "Download .tex" button (if completed)
- "Delete" button with ConfirmDialog

**ConfirmDialog.tsx:** Modal with "Are you sure?" message, Cancel/Delete buttons.

**Empty state:** "No applications yet." with "Create your first" button.

**Acceptance:** History lists all apps. View shows details. Delete removes with confirmation.

---

### Task 5.9: Build common components
| Field | Value |
|-------|-------|
| **Files** | `frontend/src/components/common/LoadingSpinner.tsx`, `frontend/src/components/common/ErrorBanner.tsx`, `frontend/src/components/common/EmptyState.tsx`, `frontend/src/components/common/ConfirmDialog.tsx` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 2 |
| **Deps** | 5.1 |

**Action:**
- **LoadingSpinner:** CSS-only spinner (rotating ring), optional label text, centered in container
- **ErrorBanner:** Red-tinted banner with error icon, message, optional retry button, dismiss button
- **EmptyState:** Large icon (emoji), heading, subtext, optional action button
- **ConfirmDialog:** Modal overlay with backdrop, title, message, Cancel (secondary) and Confirm (danger) buttons. Focus trap, Escape to close.

**Acceptance:** Components render correctly in isolation.

---

### Task 5.10: Create shared hooks
| Field | Value |
|-------|-------|
| **Files** | `frontend/src/hooks/useProfile.ts`, `frontend/src/hooks/useProjects.ts`, `frontend/src/hooks/useGeneration.ts`, `frontend/src/hooks/useHistory.ts`, `frontend/src/utils/formatters.ts`, `frontend/src/utils/validators.ts` |
| **Agent** | `@frontend-dev` |
| **Complexity** | 3 |
| **Deps** | 5.2 |

**Action:** Thin wrapper hooks that combine API hooks with local UI state logic:

- `useProfile()`: Load profile, expose `profile`, `isLoading`, `error`, `updateProfile`, `isSaving`
- `useProjects()`: Load projects, expose `projects`, `isLoading`, `refreshProjects`
- `useGeneration()`: Wraps `useGeneratePoints` + `useGenerateResume` + `useRegenerateSection`, manages app-level generation state
- `useHistory()`: List/view/delete applications

`formatters.ts`:
- `formatDate(iso: string) -> string`: "June 25, 2026"
- `formatDateRange(start, end) -> string`: "Aug 2025 — Present"
- `truncate(text, maxLen) -> string`
- `formatAgo(date) -> string`: "2 hours ago", "3 days ago"

`validators.ts`:
- `validateJobDescription(text): string[]` → array of error messages
- `validateEmail(email): boolean`
- `validateRequired(value): boolean`

**Acceptance:** Hooks are clean, typed, and reusable.

---

### Task 5.11: Write frontend tests
| Field | Value |
|-------|-------|
| **Files** | `frontend/tests/setup.ts`, `frontend/tests/test_Dashboard.tsx`, `frontend/tests/test_NewApplication.tsx`, `frontend/tests/test_ReviewEdit.tsx` |
| **Agent** | `@tester` |
| **Complexity** | 3 |
| **Deps** | 5.3, 5.4, 5.5 |

**Action:** Basic component smoke tests with Vitest + Testing Library:
- Dashboard renders with mocked data
- NewApplication form validates required fields
- ReviewEdit displays sections
- API hooks return correct types

**Acceptance:** `npx vitest run` passes.

---

## Phase 6: Integration & Polish (7 tasks, 30 complexity)

### Task 6.1: End-to-end testing
| Field | Value |
|-------|-------|
| **Files** | No new files — manual + automated |
| **Agent** | `@tester` |
| **Complexity** | 5 |
| **Deps** | All prior |

**Action:** Run through the full flow with a real (or mocked) LLM:
1. Create profile via UI
2. Create new application with a real JD
3. Verify project matching returns results
4. Generate points, verify streaming in UI
5. Edit bullets, regenerate section
6. Export .tex, verify download
7. View in history, delete

**Acceptance:** Complete end-to-end cycle works without errors.

---

### Task 6.2: Error handling audit
| Field | Value |
|-------|-------|
| **Files** | Various — error states across all pages and services |
| **Agent** | `@backend-dev` + `@frontend-dev` |
| **Complexity** | 5 |
| **Deps** | All prior |

**Action:** Audit and fix every error state from PLAN.md §14:
- API key missing → banner in UI
- LLM rate limited → retry button
- Sweep file missing → warning with path
- Profile empty → inline guidance
- Generation failure → error message with stage info
- Network offline → connection error message
- Invalid .tex → validation warnings

**Acceptance:** Every error state has a user-friendly UI. No unhandled exceptions reach the user.

---

### Task 6.3: LaTeX validation
| Field | Value |
|-------|-------|
| **Files** | Add to `backend/app/pipeline/latex_renderer.py` |
| **Agent** | `@backend-dev` |
| **Complexity** | 3 |
| **Deps** | 3.5 |

**Action:** Enhance LaTeX validation:
- Balance check: `{` count == `}` count
- Environment check: every `\begin{env}` has `\end{env}`
- Required sections: `\begin{document}`, `\end{document}`
- Warn about potentially problematic characters in user content

**Acceptance:** Validation catches unbalanced braces. Empty profile generates compilable but minimal .tex.

---

### Task 6.4: Security review
| Field | Value |
|-------|-------|
| **Files** | Review all |
| **Agent** | `@security-reviewer` |
| **Complexity** | 4 |
| **Deps** | All prior |

**Action:** Check:
- API keys in `.env` only, never in frontend bundle
- No secrets in git history (`.env` in `.gitignore`)
- LaTeX injection: user-provided text is escaped via `escape_latex()` filter
- Path traversal: all file operations use `Path` objects, no user-provided paths
- CORS: only configured origins allowed
- Input validation: all API inputs validated by Pydantic

**Acceptance:** Security checklist complete. No secrets in frontend code.

---

### Task 6.5: Code quality pass
| Field | Value |
|-------|-------|
| **Files** | All |
| **Agent** | `@clean-coder` |
| **Complexity** | 5 |
| **Deps** | All prior |

**Action:**
- Python: Ruff linting (select ALL rules), type hints on all public functions, Google-style docstrings
- TypeScript: ESLint, strict null checks, no `any` types
- Remove dead code, commented-out blocks (except the intentional OpenAI-client stub)
- Consistent naming: snake_case for Python, camelCase for TS
- Add logging: structured logging with `logging.getLogger(__name__)` in every module

**Acceptance:** `ruff check backend/` passes. `npx eslint frontend/src/` passes. `npx tsc --noEmit` passes.

---

### Task 6.6: Write comprehensive README and setup docs
| Field | Value |
|-------|-------|
| **Files** | `README.md` |
| **Agent** | `@technical-writer` |
| **Complexity** | 5 |
| **Deps** | All prior |

**Action:** README sections:
1. **Project Overview** — What it does, architecture diagram (ASCII)
2. **Prerequisites** — Python 3.12+, Node 20+, `uv` installed
3. **Quick Start** — Clone, install deps, set up `.env`, run backend, run frontend
4. **Configuration** — All env vars, LLM provider setup
5. **Usage Guide** — Step-by-step: Create profile → New Application → Review → Export
6. **Project Structure** — Directory tree with descriptions
7. **Development** — Testing, linting, adding new features
8. **FAQ** — Troubleshooting, common issues
9. **vNext** — Planned features

**Acceptance:** A new developer can go from zero to generating a resume in <10 minutes following the README.

---

### Task 6.7: Final integration + regression testing
| Field | Value |
|-------|-------|
| **Files** | No new files |
| **Agent** | `@tester` |
| **Complexity** | 3 |
| **Deps** | 6.1-6.6 |

**Action:** Final test pass:
- All unit tests pass
- All integration tests pass
- Manual E2E walkthrough
- Edge case: empty profile
- Edge case: no projects matched
- Edge case: 5000-word job description
- Edge case: regenerating section multiple times

**Acceptance:** All tests green. E2E walkthrough successful.

---

## Summary

| Phase | Tasks | Total Complexity | Lead |
|-------|-------|-----------------|------|
| 0: Scaffolding | 7 | 18 | `@general-builder`, `@backend-dev`, `@frontend-dev` |
| 1: Data Layer | 6 | 29 | `@data-engineer`, `@tester` |
| 2: LLM Integration | 5 | 24 | `@model-scientist`, `@tester` |
| 3: Generation Pipeline | 8 | 46 | `@backend-dev`, `@model-scientist`, `@tester` |
| 4: API Layer | 7 | 25 | `@backend-dev`, `@tester` |
| 5: Frontend | 11 | 47 | `@frontend-dev`, `@tester` |
| 6: Integration & Polish | 7 | 30 | Multiple |
| **Total** | **51** | **219** | — |

> **Note:** This v2.0 task list collapses some redundant sub-tasks from v1.0. The total is 51 tasks vs the previous 52, now with more detail per task.
