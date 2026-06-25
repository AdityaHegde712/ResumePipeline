# Resume Pipeline — Technical Specification v2.0

> **Status:** Draft — Awaiting Owner Confirmation  
> **Version:** 2.0 (Granular — sub-agent ready)  
> **Generated:** June 25, 2026  
> **Target:** End-to-end local full-stack application for AI-powered resume generation

---

## 1. Executive Summary

A locally-running full-stack application (FastAPI + React + LiteLLM) that produces **ATS-optimized resume bullet points** and a **compilable LaTeX resume** from:

- **`PROJECT_SWEEP_SUMMARIES.md`** — detailed technical summaries of 17 projects
- **Your personal profile** (education, experience, skills, etc.) in a `profile.yaml`
- **A job description** + **company name** you paste into the web UI

**What it does NOT do (v1.0):** Cover letters. Those are deferred to vNext after collecting 15-20 manually-written samples.

**LLM strategy:** Gemini 2.5 Pro primary (MVP). LiteLLM abstraction layer ready for DeepSeek V4 Flash swap-in per task.

---

## 2. Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           React + Vite Frontend                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │Dashboard  │ │New App   │ │Review/   │ │Export    │ │Profile Manager   │ │
│  │(stats,    │ │(JD form, │ │Edit      │ │Resume    │ │(edit profile     │ │
│  │recent)    │ │match)    │ │(points)  │ │(.tex dl) │ │ YAML)            │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              TanStack Query (React Query) Hooks Layer                │  │
│  │  useProfile  useProjects  useGeneration  useHistory                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ HTTP REST (localhost:8000)
                                │ SSE Stream (for generation progress)
┌───────────────────────────────▼────────────────────────────────────────────┐
│                           FastAPI Backend                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  MIDDLEWARE: CORS, Request Logging, Error Handler                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  API ROUTES                                                          │  │
│  │  /api/profile/*        → profile_router.py                          │  │
│  │  /api/projects/*       → projects_router.py                         │  │
│  │  /api/generate/*       → resume_router.py   (POST, SSE-streaming)   │  │
│  │  /api/applications/*   → history_router.py                          │  │
│  │  /api/config/*         → config_router.py                           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  SERVICES LAYER                                                      │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │  │
│  │  │ ProfileService   │  │ ProjectSweep     │  │ HistoryService   │   │  │
│  │  │ (profile.yaml    │  │ Service          │  │ (applications/   │   │  │
│  │  │  CRUD)           │  │ (parse & index   │  │  *.json)         │   │  │
│  │  └──────────────────┘  │  sweep file)     │  └──────────────────┘   │  │
│  │                        └──────────────────┘                         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  AI LAYER                                                            │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │  │
│  │  │ LLMService       │  │ PromptManager    │  │ MatchingService  │   │  │
│  │  │ (LiteLLM wrapper │  │ (loads .j2       │  │ (JD→project      │   │  │
│  │  │  + OpenAI-client │  │  templates)      │  │  relevance)      │   │  │
│  │  │  stub for v2)    │  └──────────────────┘  └──────────────────┘   │  │
│  │  └──────────────────┘                                              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  PIPELINE LAYER                                                      │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │  │
│  │  │ ResumePoints     │  │ ResumeWriter     │  │ LaTeXRenderer    │   │  │
│  │  │ Generator        │  │ (compiles        │  │ (Jinja2→.tex     │   │  │
│  │  │ (per-section     │  │  all sections)   │  │  output)         │   │  │
│  │  │  bullets)        │  └──────────────────┘  └──────────────────┘   │  │
│  │  └──────────────────┘                                              │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                        │  │
│  │  │ PDFCompiler      │  │ Orchestrator     │                        │  │
│  │  │ (MiKTeX          │  │ (match → points  │                        │  │
│  │  │  pdflatex        │  │  → write →       │                        │  │
│  │  │  wrapper)        │  │  render)         │                        │  │
│  │  └──────────────────┘  └──────────────────┘                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  STORAGE LAYER                                                      │  │
│  │  /data/profile.yaml               (objective profile — YAML)        │  │
│  │  /data/subjective_profile.md      (narrative profile — Markdown)    │  │
│  │  /data/applications/{id}.json     (per-application JSON)            │  │
│  │  /PROJECT_SWEEP_SUMMARIES.md      (source-of-truth markdown)        │  │
│  │  /app/templates/prompts/*.j2      (Jinja2 prompt templates)          │  │
│  │  /app/templates/latex/*.tex.j2    (Jinja2 LaTeX template)           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Project File Tree

```
ResumePipeline/
│
├── backend/
│   ├── pyproject.toml              # Python deps: fastapi, litellm, jinja2, pyyaml, httpx, python-multipart, pydantic-settings
│   ├── .env.example                 # Template for environment variables
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app factory, lifespan, CORS, middleware registration
│   │   ├── config.py                # Pydantic BaseSettings: GOOGLE_API_KEY, DATA_DIR, LLM_MODEL, etc.
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── profile.py           # UserProfile, Education, Experience, Project_SweepEntry, SkillSet
│   │   │   ├── project.py           # ProjectEntry (parsed from sweep file)
│   │   │   ├── application.py       # Application, GenerationStatus, GeneratedContent, BulletPoint
│   │   │   └── generation.py        # GenerationConfig, GenerationRequest, GenerationResponse, MatchResult
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── profile_service.py   # ProfileService: load/save/validate profile.yaml
│   │   │   ├── project_sweep_service.py  # ProjectSweepService: parse sweep file, index, cache, refresh detection
│   │   │   ├── history_service.py   # HistoryService: CRUD for application JSON files
│   │   │   ├── llm_service.py       # LLMService: LiteLLM wrapper + OpenAI-client stub for DeepSeek
│   │   │   └── prompt_manager.py    # PromptManager: load .j2 templates, render with context
│   │   │
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── matching_service.py       # MatchingService: JD → ranked project list via LLM
│   │   │   ├── resume_points_generator.py  # ResumePointsGenerator: per-section bullet generation
│   │   │   ├── resume_writer.py         # ResumeWriter: compile all sections, de-duplicate, order
│   │   │   ├── latex_renderer.py        # LaTeXRenderer: Jinja2 → .tex output
│   │   │   ├── pdf_compiler.py          # PDFCompiler: MiKTeX pdflatex → .pdf output (optional)
│   │   │   └── orchestrator.py          # Orchestrator: full pipeline coordinator with SSE events
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py            # Aggregates all sub-routers
│   │   │   ├── profile.py           # Profile endpoints
│   │   │   ├── projects.py          # Project list + match + refresh endpoints
│   │   │   ├── resume.py            # Generation endpoints (SSE streaming)
│   │   │   ├── history.py           # Application history endpoints
│   │   │   └── config.py            # LLM config read/update
│   │   │
│   │   ├── templates/
│   │   │   ├── prompts/
│   │   │   │   ├── project_matching.j2      # Match JD → projects
│   │   │   │   ├── resume_points.j2         # Generate bullet points
│   │   │   │   ├── resume_writeup.j2        # Compile full resume
│   │   │   │   └── keyword_analysis.j2      # Extract JD keywords (for matching)
│   │   │   └── latex/
│   │   │       └── resume_template.tex.j2   # Jinja2 version of template.tex
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── file_utils.py        # File path helpers, ensured directories
│   │       └── sse.py               # SSE event builder helpers
│   │
│   ├── data/
│   │   ├── profile.yaml             # YOUR PROFILE — objective YAML, hand-editable
│   │   ├── subjective_profile.md    # Narrative profile (Markdown, vNext cover letters)
│   │   └── applications/            # Per-application JSON files
│   │       └── .gitkeep
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py              # Shared fixtures, test data, profile.yaml template
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
│
├── frontend/
│   ├── package.json                 # React 19, Vite, TanStack Query, axios
│   ├── vite.config.ts               # Proxy /api → localhost:8000
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx                  # React entry, QueryClient provider
│       ├── App.tsx                   # Router setup (react-router-dom v7)
│       │
│       ├── api/                      # TanStack Query hooks + axios instance
│       │   ├── client.ts             # Axios instance with baseURL, interceptors
│       │   ├── profile.ts            # useProfileQuery, useUpdateProfileMutation
│       │   ├── projects.ts           # useProjectsQuery, useProjectMatchMutation, useRefreshProjectsMutation
│       │   ├── resume.ts             # useGeneratePoints, useGenerateResume (SSE stream)
│       │   └── history.ts            # useApplicationsQuery, useApplicationQuery, useDeleteApplicationMutation
│       │
│       ├── types/
│       │   ├── profile.ts            # TypeScript interfaces mirroring Pydantic models
│       │   ├── project.ts
│       │   ├── application.ts
│       │   └── generation.ts
│       │
│       ├── pages/
│       │   ├── Dashboard.tsx         # Stats, recent applications, "New Application" CTA
│       │   ├── NewApplication.tsx    # JD form + company fields → project match results → generate
│       │   ├── ReviewEdit.tsx        # Per-section editor, bullet edit/regenerate, → export
│       │   ├── ExportResume.tsx      # .tex preview + download button
│       │   ├── ProfilePage.tsx       # Full profile editor
│       │   └── HistoryPage.tsx       # Application list with view/delete
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppLayout.tsx     # Sidebar + main content area
│       │   │   └── Navbar.tsx        # Top nav with page links
│       │   ├── forms/
│       │   │   ├── JobDescriptionForm.tsx   # Textarea + company name + optional description
│       │   │   └── ProfileForm.tsx          # All profile sections as editable form
│       │   ├── resume/
│       │   │   ├── ProjectMatchCards.tsx    # Match results as selectable cards
│       │   │   ├── SectionEditor.tsx        # Per-section editor with regenerate button
│       │   │   ├── BulletPointList.tsx      # Draggable, editable bullet list
│       │   │   └── ResumePreview.tsx        # Read-only resume section display
│       │   ├── generation/
│       │   │   ├── GenerationProgress.tsx   # Multi-stage progress tracker
│       │   │   ├── StageIndicator.tsx       # Single stage: pending/active/complete/error
│       │   │   └── TokenStream.tsx          # Live streaming text display
│       │   ├── history/
│       │   │   ├── ApplicationCard.tsx      # Summary card for history list
│       │   │   └── ApplicationDetail.tsx    # Full detail modal/page for past app
│       │   └── common/
│       │       ├── LoadingSpinner.tsx
│       │       ├── ErrorBanner.tsx
│       │       ├── EmptyState.tsx
│       │       └── ConfirmDialog.tsx
│       │
│       ├── hooks/
│       │   ├── useProfile.ts         # Wraps profile API hooks
│       │   ├── useProjects.ts        # Wraps projects API hooks
│       │   ├── useGeneration.ts      # Manages generation state, SSE connection
│       │   └── useHistory.ts         # Wraps history API hooks
│       │
│       ├── styles/
│       │   ├── variables.css         # CSS custom properties (dark theme colors, spacing, fonts)
│       │   ├── global.css            # Reset, base typography, dark background
│       │   └── theme.css             # Component-level theme tokens
│       │
│       └── utils/
│           ├── formatters.ts         # Date formatters, text truncation
│           └── validators.ts         # Form validation helpers
│
├── docs/
│   └── template.tex                  # Your existing LaTeX resume template (source)
│
├── PROJECT_SWEEP_SUMMARIES.md        # 17-project sweep file
├── .env.example                      # Environment variable template
├── .gitignore
├── README.md
│
└── .agent-tasks/
    └── architect/
        ├── PLAN.md                   # ← This file
        ├── TASKS.md                  # Granular task list
        ├── AGENT_TEAM.md
        └── STATUS.md
```

---

## 4. Data Models (Pydantic)

### 4.1 `backend/app/models/profile.py`

The profile has two parts:
- **`profile.yaml`** (objective/structured) — education, experience, skills, publications, etc. Field-based, machine-parseable, human-editable.
- **`subjective_profile.md`** (narrative) — free-form markdown sections for cover letter material: early life, professional philosophy, challenges overcome, long-term goals, etc. Not used by resume generation at all. Reserved for vNext cover letter generation.

```python
from pydantic import BaseModel, Field
from typing import Optional, List

# ────────────────────────────────────────────
# Objective Profile (profile.yaml)
# ────────────────────────────────────────────

class Link(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None

class Education(BaseModel):
    school: str
    degree: str
    start_date: str  # e.g. "Aug 2025"
    end_date: str    # e.g. "May 2027"
    location: str
    gpa: Optional[str] = None
    coursework: List[str] = Field(default_factory=list)

class Experience(BaseModel):
    company: str
    role: str
    start_date: str
    end_date: str  # or "Present"
    location: str
    description: str  # raw description → LLM will generate bullet points
    highlights: List[str] = Field(default_factory=list)  # pre-written bullets (bypass LLM)

class PersonalProject(BaseModel):
    """Projects NOT in the sweep file (side projects, hackathons, etc.)"""
    name: str
    tech_stack: List[str] = Field(default_factory=list)
    description: str
    url: Optional[str] = None

class Publication(BaseModel):
    """Academic publications — rendered as static content, no LLM generation needed."""
    title: str
    authors: str          # "A. Hegde, J. Smith, S. Lee"
    venue: str            # "IEEE/CVF Conference on Computer Vision..."
    year: str             # "2025"
    url: Optional[str] = None
    description: Optional[str] = ""  # optional 1-2 line summary

class SkillSet(BaseModel):
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)

class Certificate(BaseModel):
    name: str
    issuer: str
    date: Optional[str] = None
    url: Optional[str] = None

class Leadership(BaseModel):
    organization: str
    role: str
    start_date: str
    end_date: str
    description: str

class CustomSection(BaseModel):
    title: str
    items: List[str] = Field(default_factory=list)

class UserProfile(BaseModel):
    # Identity
    name: str = "Aditya Hegde"
    email: str = ""
    phone: str = ""
    location: str = ""
    links: Link = Link()
    
    # Resume sections (order controlled by section_order below)
    education: List[Education] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    personal_projects: List[PersonalProject] = Field(default_factory=list)
    publications: List[Publication] = Field(default_factory=list)
    skills: SkillSet = SkillSet()
    certifications: List[Certificate] = Field(default_factory=list)
    leadership: List[Leadership] = Field(default_factory=list)
    custom_sections: List[CustomSection] = Field(default_factory=list)
    
    # Section ordering (default: optimized for early-career with strong projects)
    section_order: List[str] = Field(default_factory=lambda: [
        "education",
        "skills",
        "projects",      # ← main showcase for early-career candidates
        "experience",
        "publications",
        "leadership",
        "certifications",
    ])
    
    # Subjective/narrative profile (vNext: cover letter generation)
    subjective_profile_path: str = "data/subjective_profile.md"
    subjective_profile_content: str = ""  # loaded from file, not stored in YAML
```

### 4.2 `backend/app/models/project.py`

```python
from pydantic import BaseModel
from typing import List, Optional

class ProjectEntry(BaseModel):
    id: str  # lowercase slug: "arvr", "sentry"
    name: str
    type: str  # "Full-Stack Web Application", "ML Research", etc.
    summary: str
    tech_stack: List[str] = []
    key_features: List[str] = []
    resume_value_bullets: List[str] = []
    domains: List[str] = []
    lines_of_code: Optional[int] = None
    source_section: str  # e.g. "section-1"
```

### 4.3 `backend/app/models/application.py`

```python
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class GenerationStatus(str, Enum):
    PENDING = "pending"
    MATCHING = "matching"
    GENERATING_POINTS = "generating_points"
    WRITING_RESUME = "writing_resume"
    RENDERING_LATEX = "rendering_latex"
    COMPLETED = "completed"
    FAILED = "failed"

class BulletPoint(BaseModel):
    id: str  # uuid
    section: str  # "experience:company_name" or "project:arvr"
    text: str
    order: int = 0
    edited: bool = False  # true if user manually edited

class SectionPoints(BaseModel):
    section_key: str  # "experience:company_name" or "project:arvr"
    section_title: str  # "Software Engineer Intern @ Electronics Company"
    bullets: List[BulletPoint] = []

class GeneratedContent(BaseModel):
    resume_points: List[SectionPoints] = []
    resume_latex: Optional[str] = None  # full .tex content
    model_used: str = ""

class Application(BaseModel):
    id: str  # "app-20260625-001"
    created_at: datetime
    updated_at: datetime
    company_name: str
    company_description: Optional[str] = None
    job_title: str
    job_description: str
    selected_project_ids: List[str] = []
    generation_status: GenerationStatus = GenerationStatus.PENDING
    generated: Optional[GeneratedContent] = None
    error_message: Optional[str] = None
```

### 4.4 `backend/app/models/generation.py`

```python
from pydantic import BaseModel
from typing import Optional, List, Dict

class TaskModelConfig(BaseModel):
    """Per-task model configuration"""
    provider: str = "google"  # "google", "openai", "deepseek", "anthropic"
    model: str = "gemini/gemini-2.5-pro"

class LLMConfig(BaseModel):
    default_provider: str = "google"
    default_model: str = "gemini/gemini-2.5-pro"
    tasks: Dict[str, TaskModelConfig] = {}  # keyed by task name

class GenerationRequest(BaseModel):
    application_id: str
    job_title: str
    company_name: str
    company_description: Optional[str] = None
    job_description: str
    selected_project_ids: List[str]
    tone: str = "professional"  # "professional" | "technical" | "balanced"

class MatchRequest(BaseModel):
    job_title: str
    company_name: str
    job_description: str

class MatchResult(BaseModel):
    project_id: str
    project_name: str
    relevance_score: float  # 0.0 - 1.0
    reasoning: str

class PointsRegenerateRequest(BaseModel):
    application_id: str
    section_key: str  # which section to regenerate
    custom_instructions: Optional[str] = None

class ResumeExportRequest(BaseModel):
    application_id: str
    # uses the last generated content

class SSEEvent(BaseModel):
    """Server-Sent Event payload"""
    event: str  # "stage" | "token" | "section_complete" | "error" | "complete"
    data: dict
```

---

## 5. LLM Provider Architecture

### Design: Multi-Provider with LiteLLM + OpenAI-Compatible Stub

```python
# backend/app/services/llm_service.py

"""
LLM Service Architecture (v1.0 MVP)
───────────────────────────────────
[v1.0] Uses LiteLLM exclusively with Gemini 2.5 Pro as the sole provider.
       All generation tasks route through litellm.acompletion().

[v1.1] DeepSeek V4 Flash is swapped in for keyword matching and tailoring
       tasks by uncommenting the OpenAI-client block and toggling the
       TaskModelConfig. LiteLLM also supports DeepSeek natively.

Provider keying (LiteLLM format):
  Gemini:   "gemini/gemini-2.5-pro"
  DeepSeek: "deepseek/deepseek-v4-flash"  (or OpenAI-compat endpoint)
  OpenAI:   "openai/gpt-4o"
  Anthropic: "anthropic/claude-sonnet-4-20250514"
"""

# ── Primary: LiteLLM (used in v1.0) ──
from litellm import acompletion as litellm_acompletion
# from openai import OpenAI  # <-- UNCOMMENT for DeepSeek swap-in (v1.1)
```

**LLMService class interface:**

```python
class LLMService:
    """
    Provider-agnostic LLM client.
    
    v1.0: Routes everything through LiteLLM → Gemini.
    v1.1: Per-task routing via TaskModelConfig.
          Uncomment OpenAI-client block and set task config to:
            tasks.keyword_analysis.model = "deepseek/deepseek-v4-flash"
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        # ── Secondary: OpenAI-compatible client (READY for v1.1 swap-in) ──
        # self.deepseek_client = OpenAI(
        #     api_key=os.getenv("DEEPSEEK_API_KEY"),
        #     base_url="https://api.deepseek.com/v1"
        # )
        # self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate(
        self,
        messages: list[dict],
        task: str = "default",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """
        Send messages to the configured LLM for the given task.
        
        Args:
            messages: OpenAI-format message list [{"role": "...", "content": "..."}]
            task: Task identifier for per-task model routing ("default" | "matching" | "points" | "writeup" | "keywords")
            temperature: Generation temperature (0.0 - 1.0)
            max_tokens: Maximum output tokens
            stream: If True, returns AsyncIterator[str] of tokens
                    If False, returns complete response string
        
        Returns:
            Generated text content (or token iterator if streaming)
        
        Raises:
            LLMServiceError: On API failure, rate limit, auth error
            LLMConfigurationError: If no API key configured for provider
        """
```

**Per-task model routing (v1.1 pattern, built into config from day one):**

```yaml
# config.yaml (or env vars)
llm:
  default_provider: "google"
  default_model: "gemini/gemini-2.5-pro"
  tasks:
    keyword_analysis:
      provider: "deepseek"
      model: "deepseek/deepseek-v4-flash"
```

The task->model mapping is stored in config and consulted on each `generate()` call. If no per-task mapping exists, it falls back to the default.

---

## 6. Prompt Template Specifications

### 6.1 `project_matching.j2`
**Purpose:** Given a JD + all project summaries, select the 3-5 most relevant projects.

```jinja2
You are an expert resume consultant. Your task is to select the 3-5 most relevant
projects from the user's portfolio for a specific job application.

**Selection criteria** (in order of importance):
1. Tech stack overlap with job requirements
2. Domain/industry relevance to the company
3. Complexity and impact demonstrated
4. Diversity of skills shown across selected projects

**Output format:** ONLY valid JSON array. No markdown, no explanation.
Each object: {"project_id": "...", "relevance_score": 0.85, "reasoning": "..."}

---
Target Job Title: {{ job_title }}
Target Company: {{ company_name }}
Company Description: {{ company_description }}

Job Description:
{{ job_description }}

Available Projects:
{% for project in projects %}
--- {{ project.name }} (ID: {{ project.id }}) ---
Type: {{ project.type }}
Tech Stack: {{ project.tech_stack | join(", ") }}
Summary: {{ project.summary }}
Key Features: {{ project.key_features | join("; ") }}
Resume Value: {{ project.resume_value_bullets | join("; ") }}
---
{% endfor %}

Select the 3-5 most relevant projects and output ONLY a JSON array:
```

### 6.2 `resume_points.j2`
**Purpose:** Generate 3-5 ATS-optimized bullet points for a single project or experience entry.

```jinja2
You are a technical resume writer specializing in ATS-optimized bullet points.
Generate {{ num_bullets }} bullet points for the following {{ section_type }}.

**Bullet point rules:**
- Start with a strong action verb (engineered, designed, implemented, optimized, architected)
- Include quantified impact where possible (% improvements, time saved, scale handled)
- Naturally incorporate relevant keywords from the job description
- Focus on accomplishments and outcomes, not responsibilities
- Be concise: 1-2 lines per bullet
- Use past tense for completed work
- Each bullet should stand alone (avoid "this project also...")

**Output format:** ONLY valid JSON array of strings. No markdown, no numbering.

---
Section Type: {{ section_type }}  ("Project" or "Experience")
Section Name: {{ section_name }}
Section Details:
{{ section_details }}

Target Job Title: {{ job_title }}
Target Company: {{ company_name }}

Job Description Keywords: {{ jd_keywords }}
Tone: {{ tone }}  ("professional", "technical", or "balanced")

Generate {{ num_bullets }} bullet points. Output ONLY a JSON array:
```

### 6.3 `resume_writeup.j2`
**Purpose:** Compile all sections into a coherent, non-redundant resume structure.

```jinja2
You are a resume compilation expert. Organize the following bullet points into
a coherent, ready-to-render resume structure.

**Rules:**
- Remove any duplicate or overlapping bullet points across sections
- Order sections as specified (typically: Education → Experience → Projects → Skills → Leadership)
- Within each section, order by relevance/impact (most impressive first)
- Keep consistent past tense throughout
- Respect 1-page constraint: if too long, prioritize most relevant content
- Do not rewrite bullets — only organize, deduplicate, and truncate if needed

**Output format:** A JSON object with sections preserved in order.
Each section has: {"section_key": "...", "section_title": "...", "bullets": [...]}

---
User Name: {{ user_name }}
Target Role: {{ job_title }} at {{ company_name }}

Section Order (from profile):
{% for section in section_order %}
- {{ section }}
{% endfor %}

Generated Content Per Section:
{% for section in sections %}
=== {{ section.section_key }}: {{ section.section_title }} ===
{% for bullet in section.bullets %}
- {{ bullet.text }}
{% endfor %}
{% endfor %}

Compile the resume. Output ONLY a JSON object with the organized sections:
```

### 6.4 `keyword_analysis.j2`
**Purpose:** Extract structured keyword data from a job description.

```jinja2
Analyze the following job description and extract structured information.

**Output format:** ONLY valid JSON object with these keys:
- required_skills: list of strings (skills explicitly required)
- preferred_skills: list of strings (skills mentioned as preferred/nice-to-have)
- domains: list of strings (industry domains, e.g. "cybersecurity", "recommender systems")
- action_verbs: list of strings (action verbs used, e.g. "design", "implement", "optimize")
- technologies: list of strings (specific tools/frameworks mentioned)
- seniority_level: string (e.g. "intern", "junior", "mid", "senior", "lead")

---
Job Title: {{ job_title }}
Company: {{ company_name }}
Job Description:
{{ job_description }}

Output ONLY a valid JSON object:
```

---

## 7. API Contract

### 7.1 Profile Endpoints

**`GET /api/profile`**
Returns the full user profile.
```json
// Response 200
{
  "name": "Aditya Hegde",
  "email": "aditya.hegde@sjsu.edu",
  "phone": "+1-XXX-XXX-XXXX",
  "location": "San Jose, CA",
  "links": { "linkedin": "...", "github": "...", ... },
  "education": [...],
  "experience": [...],
  "personal_projects": [...],
  "skills": { "languages": [...], "frameworks": [...], "tools": [...] },
  "certifications": [...],
  "leadership": [...],
  "custom_sections": [...]
}
```

**`PUT /api/profile`**
Updates the profile. Accepts the same structure as the GET response. Partial updates are NOT supported — send the full profile. Returns the updated profile.
```json
// Request Body: same structure as UserProfile
// Response 200: updated UserProfile
```

**`GET /api/profile/exists`**
Returns whether a profile has been created yet.
```json
// Response 200
{ "exists": true }
```

### 7.2 Projects Endpoints

**`GET /api/projects`**
Returns all parsed projects from the sweep file.
```json
// Response 200
{
  "projects": [
    {
      "id": "arvr",
      "name": "ARVR — AI-Powered AR Furniture Visualizer",
      "type": "Full-Stack Web Application (AR/VR + AI)",
      "summary": "...",
      "tech_stack": ["React 18", "Three.js", "WebXR", ...],
      "key_features": [...],
      "resume_value_bullets": [...],
      "domains": ["AR/VR", "Full-Stack", "AI"],
      "lines_of_code": 6695,
      "source_section": "section-1"
    },
    ...
  ],
  "last_parsed": "2026-06-25T12:00:00Z",
  "file_modified": "2026-06-25T04:00:00Z",
  "stale": false
}
```

**`POST /api/projects/refresh`**
Force re-parses the sweep file.
```json
// Response 200
{
  "status": "ok",
  "projects_count": 17,
  "parsed_at": "2026-06-25T12:15:00Z"
}
```

**`POST /api/projects/match`**
Matches a job description to the most relevant projects. Returns ranked list.
```json
// Request
{
  "job_title": "ML Infrastructure Engineer",
  "company_name": "Acme Corp",
  "job_description": "...",
  "company_description": "optional"
}

// Response 200
{
  "matches": [
    {
      "project_id": "sentry",
      "project_name": "Sentry — Real-Time Video Threat Detection",
      "relevance_score": 0.92,
      "reasoning": "Strong overlap in ML infra, Docker/Terraform, production deployment"
    },
    ...
  ]
}
```

### 7.3 Generation Endpoints (SSE Streaming)

**`POST /api/generate/points`**
Generates bullet points for selected projects and experience. Returns SSE stream.

**SSE Stream Protocol:**
```
event: stage
data: {"stage": "matching", "status": "start"}

event: stage
data: {"stage": "matching", "status": "complete", "result": [{"project_id": "...", "relevance_score": 0.92, ...}]}

event: stage
data: {"stage": "keyword_analysis", "status": "start"}

event: token
data: {"token": "{"}

event: token
data: {"token": "required_skills"}

event: token
data: {"token": ":"}

event: token
data: {"token": "["}

...

event: stage
data: {"stage": "keyword_analysis", "status": "complete"}

event: stage
data: {"stage": "generating_points", "status": "start", "section": "project:arvr"}

event: token
data: {"section": "project:arvr", "token": "Engineered"}

event: token
data: {"section": "project:arvr", "token": " an"}

event: token
data: {"section": "project:arvr", "token": " end-to-end"}

...

event: section_complete
data: {"section": "project:arvr", "bullets": ["...", "...", "..."], "tokens_used": 245}

event: stage
data: {"stage": "generating_points", "status": "complete"}

event: complete
data: {"application_id": "app-20260625-003", "sections": [...], "total_tokens": 1240}
```

**Request:**
```json
// POST /api/generate/points
// Content-Type: application/json
// Accept: text/event-stream
{
  "application_id": "app-20260625-003",
  "job_title": "ML Infrastructure Engineer",
  "company_name": "Acme Corp",
  "company_description": null,
  "job_description": "We are looking for...",
  "selected_project_ids": ["sentry", "spaceDebrisResearch", "recsysproject"],
  "tone": "professional"
}
```

**`POST /api/generate/resume`**
Compiles points into full resume and renders .tex. Returns SSE stream.

```json
// Request
{
  "application_id": "app-20260625-003"
}

// SSE Stream (same protocol)
event: stage
data: {"stage": "writing_resume", "status": "start"}

event: token
data: {"token": "..."}  // streaming .tex content

event: stage
data: {"stage": "writing_resume", "status": "complete"}

event: stage
data: {"stage": "rendering_latex", "status": "start"}

event: stage
data: {"stage": "rendering_latex", "status": "complete"}

event: complete
data: {"application_id": "app-20260625-003", "latex": "\\documentclass..."}
```

### 7.4 Application History Endpoints

**`GET /api/applications`**
List all past applications.
```json
// Response 200
{
  "applications": [
    {
      "id": "app-20260625-003",
      "company_name": "Acme Corp",
      "job_title": "ML Infrastructure Engineer",
      "created_at": "2026-06-25T12:00:00Z",
      "generation_status": "completed",
      "selected_project_ids": ["sentry", "spacedebrisresearch", "recsysproject"]
    },
    ...
  ],
  "total": 12
}
```

**`GET /api/applications/{id}`**
Get full application details including generated content.
```json
// Response 200
{
  "id": "app-20260625-003",
  "created_at": "...",
  "company_name": "Acme Corp",
  "job_title": "ML Infrastructure Engineer",
  "job_description": "...",
  "selected_project_ids": [...],
  "generation_status": "completed",
  "generated": {
    "resume_points": [
      {
        "section_key": "project:sentry",
        "section_title": "Sentry — Real-Time Video Threat Detection",
        "bullets": [
          {"id": "b1", "section": "project:sentry", "text": "Engineered...", "order": 0, "edited": false},
          ...
        ]
      }
    ],
    "resume_latex": "\\documentclass...",
    "model_used": "gemini/gemini-2.5-pro"
  }
}
```

**`DELETE /api/applications/{id}`**
Delete an application and its generated content.
```json
// Response 200
{ "status": "deleted" }
```

### 7.5 Config Endpoints

**`GET /api/config/llm`**
```json
// Response 200
{
  "default_provider": "google",
  "default_model": "gemini/gemini-2.5-pro",
  "tasks": {
    "keyword_analysis": {
      "provider": "google",
      "model": "gemini/gemini-2.5-pro"
    }
  }
}
```

**`PUT /api/config/llm`**
```json
// Request: same structure as above
// Response 200: updated config
```

---

## 8. Streaming Protocol Detail

The generation endpoints use **Server-Sent Events (SSE)** with the following event types:

| Event Type | When | data payload |
|-----------|------|-------------|
| `stage` | Stage transitions | `{"stage": "matching", "status": "start\|complete\|error", "section?": "...", "result?": [...]}` |
| `token` | During LLM streaming | `{"section?": "...", "token": "..."}` |
| `section_complete` | Per-section done | `{"section": "...", "bullets": [...], "tokens_used": N}` |
| `error` | Any failure | `{"stage": "...", "message": "..."}` |
| `complete` | Pipeline done | `{"application_id": "...", "sections?": [...], "latex?": "...", "total_tokens": N}` |

**Frontend consumption pattern (pseudocode):**
```
const eventSource = new EventSource(`/api/generate/points`);
eventSource.addEventListener('stage', (e) => updateStageIndicator(JSON.parse(e.data)));
eventSource.addEventListener('token', (e) => appendToken(JSON.parse(e.data)));
eventSource.addEventListener('section_complete', (e) => finalizeSection(JSON.parse(e.data)));
eventSource.addEventListener('error', (e) => showError(JSON.parse(e.data)));
eventSource.addEventListener('complete', (e) => onGenerationComplete(JSON.parse(e.data)));
```

---

## 9. Key Sequence Diagrams

### 9.1 New Application → Resume Export (Happy Path)

```
User              Frontend              Backend              LLM (Gemini)        Filesystem
 │                    │                     │                     │                  │
 │ Click "New"        │                     │                     │                  │
 │───────────────────>│                     │                     │                  │
 │                    │ GET /api/profile    │                     │                  │
 │                    │────────────────────>│                     │                  │
 │                    │                     │──read profile.yaml─>│                  │
 │                    │<─── UserProfile ────│                     │                  │
 │                    │                     │                     │                  │
 │                    │ GET /api/projects   │                     │                  │
 │                    │────────────────────>│                     │                  │
 │                    │                     │──parse sweep.md──>  │                  │
 │                    │                     │  (or use cache)     │                  │
 │                    │<─── Project[] ──────│                     │                  │
 │                    │                     │                     │                  │
 │ Fill JD form       │                     │                     │                  │
 │───────────────────>│                     │                     │                  │
 │                    │ POST /api/projects/match                 │                  │
 │                    │────────────────────>│                     │                  │
 │                    │                     │──prompt: matching──>│                  │
 │                    │                     │<── JSON matches ────│                  │
 │                    │<── MatchResult[] ───│                     │                  │
 │                    │                     │                     │                  │
 │ Select projects    │                     │                     │                  │
 │ Click "Generate"   │                     │                     │                  │
 │───────────────────>│                     │                     │                  │
 │                    │ POST /api/generate/points (SSE)           │                  │
 │                    │────────────────────>│                     │                  │
 │                    │                     │─── event: stage ────│                  │
 │                    │<── (matching start)─│                     │                  │
 │                    │                     │─── prompt: keyword──>│                  │
 │                    │                     │<─── keywords ───────│                  │
 │                    │<── (keyword done)───│                     │                  │
 │                    │                     │                     │                  │
 │                    │                     │  FOR each project:  │                  │
 │                    │                     │─── prompt: points──>│                  │
 │                    │<──   tokens stream ─│<─── tokens stream ──│                  │
 │                    │<── (section done)───│                     │                  │
 │                    │                     │                     │                  │
 │ Edit bullets       │                     │                     │                  │
 │───────────────────>│ (local state)       │                     │                  │
 │                    │                     │                     │                  │
 │ Click "Export"     │                     │                     │                  │
 │───────────────────>│                     │                     │                  │
 │                    │ POST /api/generate/resume (SSE)           │                  │
 │                    │────────────────────>│                     │                  │
 │                    │                     │─── prompt: write──> │                  │
 │                    │<──   tokens stream ─│<─── tokens stream ──│                  │
 │                    │                     │                     │                  │
 │                    │                     │── render Jinja2 ───>│                  │
 │                    │                     │<── .tex output ─────│                  │
 │                    │<── (complete + .tex)│                     │                  │
 │                    │                     │                     │                  │
 │                    │                     │── save application──>│                  │
 │                    │                     │   to applications/   │                  │
 │                    │                     │                     │                  │
 │ Download .tex      │                     │                     │                  │
 │───────────────────>│                     │                     │                  │
 ```

### 9.2 Application History View/Delete

```
User              Frontend              Backend              Filesystem
 │                    │                     │                     │
 │ Click "History"    │                     │                     │
 │───────────────────>│                     │                     │
 │                    │ GET /api/applications                     │
 │                    │────────────────────>│                     │
 │                    │                     │── read dir: apps──> │
 │                    │<── Application[] ───│                     │
 │                    │                     │                     │
 │ Click application  │                     │                     │
 │───────────────────>│                     │                     │
 │                    │ GET /api/applications/{id}                │
 │                    │────────────────────>│                     │
 │                    │                     │── read {id}.json──> │
 │                    │<── Full Application─│                     │
 │                    │                     │                     │
 │ Click Delete       │                     │                     │
 │───────────────────>│                     │                     │
 │ (ConfirmDialog)    │                     │                     │
 │ Confirm            │                     │                     │
 │───────────────────>│                     │                     │
 │                    │ DELETE /api/applications/{id}             │
 │                    │────────────────────>│                     │
 │                    │                     │── delete {id}.json─>│
 │                    │<── {status: deleted}│                     │
 ```

---

## 10. LaTeX Template Adaptation Plan

**Source:** `docs/template.tex` (Jake Gutierrez-based)

**Target:** `backend/app/templates/latex/resume_template.tex.j2`

The adaptation preserves the exact LaTeX styling while replacing hardcoded content with Jinja2 variables.

### Mapping: template.tex → Jinja2 variables

| LaTeX Section | Jinja2 Variable | Notes |
|--------------|----------------|-------|
| Name in `\begin{center}` | `{{ profile.name }}` | `\Huge \scshape` preserved |
| Address | `{{ profile.location }}` | |
| Phone | `{{ profile.phone }}` | |
| Email | `{{ profile.email }}` | With `\href{mailto:...}` |
| LinkedIn | `{{ profile.links.linkedin }}` | With `\href{...}` |
| GitHub | `{{ profile.links.github }}` | With `\href{...}` |
| Education section | `{% for edu in profile.education %}` | `\resumeSubheading{...}` |
| Relevant Coursework | `{% for course in edu.coursework %}` | Inside `multicols` |
| Experience section | `{% for exp in profile.experience %}` | `\resumeSubheading{...}` + bullet loops |
| Projects section | `{% for proj in resume_sections.projects %}` | `\resumeProjectHeading{...}` + generated bullets |
| Publications section | `{% for pub in profile.publications %}` | `\resumeSubheading{title}{year}\n\small{authors}{venue}` |
| Technical Skills | `{{ profile.skills \| format_skills }}` | Custom Jinja2 filter |
| Leadership | `{% for lead in profile.leadership %}` | `\resumeSubheading{...}` |

### Custom Jinja2 filters needed:
- `format_skills(skills: SkillSet) → str` — formats into `\textbf{Category}: item1, item2 \\`
- `escape_latex(text: str) → str` — escapes `# $ % & ~ _ ^ \ { }`
- `format_date_range(start, end) → str` — "Aug 2025 -- Present"

**Publications section rendering:**
```latex
%-----------PUBLICATIONS-----------
\section{Publications}
  \resumeSubHeadingListStart
    \resumeSubheading
      {{ pub.title | escape_latex }}{{ pub.year }}
      {\small\textit{{ pub.authors | escape_latex }}}{{ pub.venue | escape_latex }}
  \resumeSubHeadingListEnd
```

### Output verification:
Generated `.tex` must be compilable. Basic verification:
- Balanced `{ }` — count of `{` == `}`
- No undefined commands (template.tex defines all custom commands)
- `\begin{document}` ... `\end{document}` present exactly once
- All `\href` URLs have valid syntax

---

## 11. Cover Letter Deferral (vNext)

**Current design:** The application data model has no cover letter field. Cover letters are entirely deferred.

**vNext plan (after 15-20 samples collected):**
1. User writes cover letters manually on Claude Haiku web platform
2. User stores them as Markdown files in a `docs/cover_letters/` directory
3. After collecting sufficient samples, agents analyze patterns
4. A CoverLetterGenerator agent is built using extracted patterns
5. Output: Markdown → PDF via pandoc or similar

**No cover letter code will be written in v1.0.** The frontend has no cover letter tab/page.

---

## 12. Phased Implementation Plan

### Phase 0: Project Scaffolding (Tasks: 0.1–0.7)

**Goal:** Runnable monorepo with both dev servers, type parity, no business logic yet.

| Task | File(s) | Detail |
|------|---------|--------|
| 0.1 Monorepo structure | Root dirs | Create `backend/`, `frontend/`, `data/applications/`, `docs/`, `.gitignore` |
| 0.2 Python project init | `backend/pyproject.toml`, `backend/.env.example` | FastAPI, LiteLLM, Jinja2, PyYAML, httpx, python-multipart, pydantic-settings, uvicorn[standard], pytest, pytest-asyncio |
| 0.3 React project init | `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json` | React 19, TanStack Query, axios, react-router-dom v7, Vitest, @testing-library/react |
| 0.4 Backend config | `backend/app/config.py` | `Settings(BaseSettings)`: GOOGLE_API_KEY, DATA_DIR, LLM_DEFAULT_MODEL, LLM_DEFAULT_TEMPERATURE, CORS_ORIGINS |
| 0.5 Pydantic models | `backend/app/models/*.py` | All models from §4.1-§4.4 |
| 0.6 TypeScript types | `frontend/src/types/*.ts` | Mirror all Pydantic models exactly |
| 0.7 Vite proxy config | `frontend/vite.config.ts` | Proxy `/api` → `http://localhost:8000` |

**Verification:**
- `uv run uvicorn app.main:app --reload` starts on :8000
- `npm run dev` starts on :5173, proxies /api to backend
- `curl localhost:8000/api/health` returns `{"status":"ok"}`

---

### Phase 1: Data Layer (Tasks: 1.1–1.6)

**Goal:** All data services operational — profile, sweep parsing, history.

#### 1.1 ProfileService (`backend/app/services/profile_service.py`)
```
class ProfileService:
    @staticmethod
    def get_path() -> Path  # returns data/profile.yaml

    async def load() -> UserProfile
        # Read YAML, parse, validate. Return UserProfile with defaults if file missing.
    
    async def save(profile: UserProfile) -> UserProfile
        # Write YAML, create dir if needed, return saved profile.
    
    async def exists() -> bool
        # Check if profile.yaml exists and has required fields.
```

**Edge cases:**
- File not found → return default UserProfile
- Invalid YAML → raise ProfileValidationError with details
- Missing required fields → raise ProfileValidationError

**Test cases:**
- Load default profile when file missing
- Round-trip save → load
- Invalid YAML raises error
- Partial profile (missing fields) fills defaults

#### 1.2 ProjectSweepService (`backend/app/services/project_sweep_service.py`)
```
class ProjectSweepService:
    def __init__(self, file_path: Path)
    
    async def parse() -> list[ProjectEntry]
        # Read markdown, detect ## headers, extract per-section:
        #   - Project name (from ## header)
        #   - Type (from "Type:" line)
        #   - Tech stack (from "Tech Stack:" line, split by commas)
        #   - Summary (paragraph after "### Project Overview")
        #   - Key features (bullet points under "### Key Features")
        #   - Resume value bullets (bullet points under "### Resume Value")
        #   - Domains (inferred from type + tech stack)
        #   - Lines of code (from "**Scale:**" line)
        # Cache parsed result in memory with file mtime
    
    async def get_all() -> list[ProjectEntry]
        # Return cached, re-parse if file changed
    
    async def refresh() -> list[ProjectEntry]
        # Force re-parse regardless
    
    async def get_by_id(id: str) -> ProjectEntry | None
        # Return single project by slug
    
    def is_stale() -> bool
        # File mtime > last parse time
```

**Markdown parsing approach:**
Use regex to detect `## N. Title` headers. Between headers, extract metadata by scanning for `**Label:**` patterns and section headers (`### Section Name`). This is simpler and more maintainable than an AST parser.

**Edge cases:**
- File doesn't exist → empty list
- Malformed section → skip with warning log
- New projects added mid-file → detected on re-parse
- Line count varies → flexible parsing

**Test cases:**
- Parse full 17-project sweep file, verify count
- Parse specific section, verify fields extracted
- File not found returns empty
- Refresh invalidates cache
- Stale detection works

#### 1.3 HistoryService (`backend/app/services/history_service.py`)
```
class HistoryService:
    def __init__(self, data_dir: Path)
    
    async def create(application: Application) -> Application
        # Save new application JSON. Generate ID if missing.
    
    async def get(id: str) -> Application | None
        # Read single application JSON
    
    async def list_all() -> list[Application]
        # List all applications sorted by created_at desc
    
    async def update(application: Application) -> Application
        # Overwrite existing application JSON
    
    async def delete(id: str) -> bool
        # Delete application file
    
    async def count() -> int
        # Count total applications
```

**File naming:** `app-YYYYMMDD-NNN.json` (auto-incrementing per day)

**Test cases:**
- Create → list → get round-trip
- Delete existing
- Delete non-existent returns False
- List empty returns []
- Concurrent create has unique IDs

---

### Phase 2: LLM Integration (Tasks: 2.1–2.5)

#### 2.1 LLMService (`backend/app/services/llm_service.py`)
```
class LLMService:
    def __init__(self, config: LLMConfig)
    
    async def generate(
        self,
        messages: list[dict],
        task: str = "default",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> str | AsyncIterator[str]
    
    async def generate_structured(
        self,
        messages: list[dict],
        task: str = "default",
        response_model: type[BaseModel] = None,
        temperature: float = 0.3,
    ) -> BaseModel
        # Generate and parse structured response. Retry on parse failure (max 2).
    
    def get_model_for_task(self, task: str) -> str
        # Return "provider/model" string for the task
    
    async def validate_connection(self) -> bool
        # Test LLM connectivity with a simple prompt
```

**Error handling:**
- `LLMConnectionError`: API unreachable, timeout
- `LLMAuthError`: Invalid/missing API key
- `LLMRateLimitError`: Rate limited, includes retry-after info
- `LLMParseError`: Response couldn't be parsed as expected format

**OpenAI-client block (commented, ready for v1.1):**
```python
# ── Secondary: Direct OpenAI client (v1.1: DeepSeek swap-in) ──
# DeepSeek and many providers support OpenAI-compatible endpoints.
# Uncomment and configure in TaskModelConfig to use:
#
# self.deepseek_client = OpenAI(
#     api_key=os.getenv("DEEPSEEK_API_KEY"),
#     base_url="https://api.deepseek.com/v1"
# )
# 
# Usage (when task's provider == "deepseek"):
#   response = self.deepseek_client.chat.completions.create(
#       model="deepseek-chat",
#       messages=messages,
#       temperature=temperature,
#       max_tokens=max_tokens,
#       stream=stream
#   )
```

**Test cases:**
- Mock litellm.acompletion, verify messages flow correctly
- Task routing returns correct model string
- Connection validation success/failure
- Structured generation parses response into Pydantic model
- Error mapping: API error → LLMServiceError

#### 2.2 PromptManager (`backend/app/services/prompt_manager.py`)
```
class PromptManager:
    def __init__(self, templates_dir: Path)
    
    async def render(
        self,
        template_name: str,  # "project_matching", "resume_points", etc.
        context: dict,
    ) -> str
        # Load .j2 template, render with context, return string
    
    def list_templates(self) -> list[str]
        # Return available template names
    
    def get_template_path(self, name: str) -> Path
        # Return full path to template file
```

**Template files stored at:** `backend/app/templates/prompts/`

**Test cases:**
- Render each template with valid context
- Missing template name raises TemplateNotFound
- Invalid context (missing variables) renders with Jinja2 undefined handling
- Template listing returns all 4 templates

---

### Phase 3: Generation Pipeline (Tasks: 3.1–3.8)

#### 3.1 MatchingService (`backend/app/pipeline/matching_service.py`)
```
class MatchingService:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager)
    
    async def match(
        self,
        job_title: str,
        company_name: str,
        job_description: str,
        projects: list[ProjectEntry],
        company_description: str = "",
    ) -> list[MatchResult]
        # 1. Render project_matching.j2 with JD + all projects
        # 2. Call LLM (task="matching")
        # 3. Parse JSON response into list[MatchResult]
        # 4. Validate: scores in 0-1, project_ids exist
        # 5. Sort by score descending, return top 8
```

**Test cases:**
- Returns top matches sorted by score
- Handles empty project list
- LLM returns invalid JSON → retry or ParseError
- All project_ids in result exist in input list
- Score validation (0.0-1.0 range)

#### 3.2 KeywordAnalysisService (`backend/app/pipeline/keyword_analysis_service.py`)
```
class KeywordAnalysisService:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager)
    
    async def analyze(self, job_title: str, company_name: str, job_description: str) -> dict
        # 1. Render keyword_analysis.j2
        # 2. Call LLM (task="keyword_analysis")
        # 3. Parse JSON: required_skills, preferred_skills, domains, action_verbs, technologies
        # 4. Return structured keywords for prompt enhancement
```

#### 3.3 ResumePointsGenerator (`backend/app/pipeline/resume_points_generator.py`)
```
class ResumePointsGenerator:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager)
    
    async def generate_points(
        self,
        job_title: str,
        company_name: str,
        job_description: str,
        jd_keywords: dict,
        projects: list[ProjectEntry],
        profile: UserProfile,
        tone: str = "professional",
        stream_callback: Callable = None,
    ) -> list[SectionPoints]
        # For each selected project:
        #   1. Format project details (name, tech stack, features, existing resume bullets)
        #   2. Render resume_points.j2 with context
        #   3. Call LLM with streaming, yield tokens via callback
        #   4. Parse JSON response, create BulletPoints
        #   5. Return SectionPoints per project/experience
        #
        # For each experience entry:
        #   Same flow, using experience.description as context
    
    async def regenerate_section(
        self,
        section_key: str,
        custom_instructions: str = "",
        previous_bullets: list[str] = None,
    ) -> list[BulletPoint]
        # Regenerate single section with optional custom instructions
```

**Test cases:**
- Generates correct number of bullets (3-5)
- Bullets include JD keywords
- Streaming callback invoked per token
- Regenerate produces different output (different seed/temperature)
- Section key format: "project:{id}" or "experience:{company}"

#### 3.4 ResumeWriter (`backend/app/pipeline/resume_writer.py`)
```
class ResumeWriter:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager)
    
    async def compile_resume(
        self,
        sections: list[SectionPoints],
        profile: UserProfile,
        job_title: str,
        company_name: str,
        stream_callback: Callable = None,
    ) -> list[SectionPoints]
        # 1. Check for duplicate bullets across sections
        # 2. Order sections by profile's section_order (Education → Experience → Projects → Skills → Leadership)
        # 3. Optional: Call LLM (task="writeup") to deduplicate and polish
        # 4. Return organized SectionPoints list
    
    def deduplicate(self, sections: list[SectionPoints]) -> list[SectionPoints]
        # Remove bullets with >80% similarity across sections
        # Simple approach: normalize text, check string overlap
```

**Test cases:**
- Deduplication catches identical bullets
- Section ordering matches profile config
- Empty sections are omitted (not included with 0 bullets)
- All original content preserved (no hallucination of new bullets)

#### 3.5 LaTeXRenderer (`backend/app/pipeline/latex_renderer.py`)
```
class LaTeXRenderer:
    def __init__(self, template_path: Path)
    
    async def render(
        self,
        profile: UserProfile,
        sections: list[SectionPoints],
    ) -> str
        # 1. Load Jinja2 environment with custom filters (escape_latex, format_skills, format_date)
        # 2. Load resume_template.tex.j2
        # 3. Render with context: profile, sections
        # 4. Validate output (balanced braces, sections present)
        # 5. Return complete .tex string
    
    def validate_latex(self, tex_content: str) -> list[str]
        # Check:
        # - { count == } count
        # - \begin{document} present once
        # - \end{document} present once
        # - No obvious LaTeX errors
        # Return list of warnings (empty = clean)
```

**Jinja2 custom filters:**
```python
def escape_latex(text: str) -> str:
    """Escape LaTeX special characters: # $ % & ~ _ ^ \ { }"""
    replacements = {
        '\\': '\\textbackslash{}',
        '{': '\\{', '}': '\\}',
        '#': '\\#', '$': '\\$', '%': '\\%',
        '&': '\\&', '~': '\\textasciitilde{}',
        '_': '\\_', '^': '\\textasciicircum{}',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

def format_skills(skills: SkillSet) -> str:
    """Format skills into LaTeX: \\textbf{Languages}: Python, TypeScript \\\\"""
    parts = []
    if skills.languages:
        parts.append(f"\\\\textbf{{Languages}}: {', '.join(skills.languages)}")
    if skills.frameworks:
        parts.append(f"\\\\textbf{{Frameworks}}: {', '.join(skills.frameworks)}")
    if skills.tools:
        parts.append(f"\\\\textbf{{Tools}}: {', '.join(skills.tools)}")
    return ' \\\\\n'.join(parts) + ' \\\\'
```

**Test cases:**
- Renders valid .tex from sample data
- Validate catches unbalanced braces
- Escape prevents LaTeX injection from user text
- Empty sections gracefully omitted
- Jinja2 template renders all sections

#### 3.6 Orchestrator (`backend/app/pipeline/orchestrator.py`)
```
class Orchestrator:
    """
    End-to-end pipeline coordinator.
    Manages the sequence: match → keywords → points → write → render.
    Emits SSE events for frontend progress tracking.
    """
    def __init__(
        self,
        llm_service: LLMService,
        prompt_manager: PromptManager,
        project_sweep_service: ProjectSweepService,
        profile_service: ProfileService,
        history_service: HistoryService,
    )
    
    async def run_full_pipeline(
        self,
        request: GenerationRequest,
        event_callback: Callable[[str, dict], Awaitable[None]],
    ) -> Application
        # 1. Create Application record (status: matching)
        # 2. Load profile + projects
        # 3. Emit stage: matching start
        # 4. Run MatchingService.match()
        # 5. Emit stage: matching complete
        # 6. Emit stage: keyword_analysis start
        # 7. Run KeywordAnalysisService.analyze()
        # 8. Emit stage: keyword_analysis complete
        # 9. Emit stage: generating_points start
        # 10. Run ResumePointsGenerator.generate_points()
        #     → emit tokens via callback
        # 11. Emit stage: generating_points complete
        # 12. Emit stage: writing_resume start
        # 13. Run ResumeWriter.compile_resume()
        # 14. Emit stage: writing_resume complete
        # 15. Emit stage: rendering_latex start
        # 16. Run LaTeXRenderer.render()
        # 17. Emit stage: rendering_latex complete
        # 18. Save Application to history
        # 19. Emit complete with application_id + latex content
```

---

### Phase 4: API Layer (Tasks: 4.1–4.8)

#### FastAPI Application (`backend/app/main.py`)
```python
app = FastAPI(title="Resume Pipeline", version="1.0.0")

@app.on_event("startup")
async def startup():
    # Initialize services
    # Auto-detect sweep file staleness

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
```

#### SSE Streaming Implementation (`backend/app/utils/sse.py`)
```python
async def generate_sse_events(orchestrator, request):
    """Generator for SSE events from the pipeline orchestrator."""
    
    async def emit(event_type: str, data: dict):
        yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    async for event in orchestrator.run_full_pipeline(request, emit):
        yield event
```

**API endpoint for generation:**
```python
@router.post("/generate/points")
async def generate_points(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
):
    return StreamingResponse(
        orchestrator.run_points_pipeline(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
```

---

### Phase 5: Frontend (Tasks: 5.1–5.11)

#### Page Component Specifications

**Dashboard.tsx**
- Shows: welcome message, "New Application" button, last 5 applications
- State: loading apps list → show skeleton → show cards
- Empty state: "No applications yet. Create your first!"
- Error state: "Could not load applications. Check backend connection."

**NewApplication.tsx**
- Sections: JobDescriptionForm (textarea + company name + company description) → ProjectMatchCards
- Flow: submit JD → show loading spinner → show match cards → user selects → "Generate" button
- Validation: JD required (min 50 chars), company name required
- Error states: JD too short, match API fails, no projects matched

**ReviewEdit.tsx**
- Sections list: each section is a SectionEditor
- Each SectionEditor has: section title, BulletPointList, "Regenerate" button, "Add bullet" button
- BulletPointList: draggable bullets (react-beautiful-dnd or @dnd-kit), each is editable textarea
- "Export Resume" button at bottom
- State: loading → show sections → editing

**ExportResume.tsx**
- Shows: .tex content in a <pre> or code block with syntax highlighting (simple)
- Buttons: "Download .tex" (blob download), "Copy to clipboard"
- Info box: "Upload this .tex file to Overleaf and compile to PDF"
- No-cover-letter notice (optional): "Cover letters coming in a future update"

**ProfilePage.tsx**
- Sections: Basic Info (name, email, phone, location), Links, Education list, Experience list, Skills, etc.
- Each section is a form with save button
- "Save" triggers PUT /api/profile
- Unsaved changes warning on navigation

**HistoryPage.tsx**
- List of ApplicationCards, sort by date desc
- Each card: company name, job title, date, status badge
- Click → show ApplicationDetail (modal or expand)
- ApplicationDetail: full application info, generated content, "Download .tex" button, "Delete" button with ConfirmDialog

---

## 13. Design Decisions & Rationale (Updated)

| Decision | Choice | Why |
|----------|--------|-----|
| **LLM abstraction** | LiteLLM + OpenAI-client stub | Swap providers per-task with config change; stub ready for DeepSeek v1.1 |
| **Objective profile storage** | YAML (`profile.yaml`) | Human-editable, version-controllable, supports nested lists/comments. User edits this directly. |
| **Subjective profile storage** | Markdown (`subjective_profile.md`) | Free-form narrative sections (life stories, goals, challenges) for vNext cover letter generation. Prose belongs in markdown, not YAML. |
| **History storage** | JSON per file | Programmatically managed (app creates/reads/updates), strict parsing, no human editing needed |
| **LaTeX output** | .tex via Jinja2 | Preserves exact template formatting; user compiles in Overleaf |
| **Cover letter** | Deferred to vNext | Build pattern library from 15-20 manual samples first. Subjective profile feeds this. |
| **Generation pipeline** | Two-stage (points → resume) | User edits bullets before full resume composition |
| **Section ordering** | Configurable `section_order` in profile | Evidence-backed default: Education → Skills → Projects → Experience → Publications → Leadership (ATS-first, projects-as-showcase) |
| **Streaming** | SSE events | Native browser support, clean stage + token events |
| **Sweep file refresh** | Auto-detect + manual | Minimal overhead (mtime check); manual as fallback |
| **Frontend state** | TanStack Query | Built-in caching, loading/error states, refetch on focus |
| **Dark theme** | CSS custom properties | User preference; easy to maintain and extend |
| **Publications** | Static model, no LLM gen | Publications are fixed text from profile, rendered directly into LaTeX. No prompt needed. |

---

## 14. Error Handling Strategy

| Error | Where | UX |
|-------|-------|----|
| API key not configured | Backend startup, first LLM call | Backend returns 503 with `LLMConfigurationError`. Frontend shows banner: "⚠️ LLM API key not configured. Set GOOGLE_API_KEY in .env" |
| LLM rate limited | During generation | Event: `{"event": "error", "stage": "generating_points", "message": "Rate limited. Retry in 30s."}` Frontend shows retry button |
| LLM timeout | During generation | Event: `{"event": "error", "stage": "keyword_analysis", "message": "LLM timed out. The job description may be too long."}` Frontend offers retry |
| Sweep file not found | Startup, project list | Backend returns empty list. Frontend shows: "📄 Project sweep file not found at PROJECT_SWEEP_SUMMARIES.md" |
| Profile not found | Profile page | Backend returns default empty profile. Frontend shows form to fill in basics |
| Generation parse failure | LLM returns non-JSON | Orchestrator retries once, then fails with error event |
| Invalid YAML in profile | Profile load | Backend returns 422 with parse error details. Frontend shows error with line number |

---

## 15. Files That Will Be Created (Complete List)

### Backend (20 files)
```
backend/pyproject.toml
backend/.env.example
backend/app/__init__.py
backend/app/main.py
backend/app/config.py
backend/app/models/__init__.py
backend/app/models/profile.py
backend/app/models/project.py
backend/app/models/application.py
backend/app/models/generation.py
backend/app/services/__init__.py
backend/app/services/profile_service.py
backend/app/services/project_sweep_service.py
backend/app/services/history_service.py
backend/app/services/llm_service.py
backend/app/services/prompt_manager.py
backend/app/pipeline/__init__.py
backend/app/pipeline/matching_service.py
backend/app/pipeline/keyword_analysis_service.py
backend/app/pipeline/resume_points_generator.py
backend/app/pipeline/resume_writer.py
backend/app/pipeline/latex_renderer.py
backend/app/pipeline/orchestrator.py
backend/app/api/__init__.py
backend/app/api/router.py
backend/app/api/profile.py
backend/app/api/projects.py
backend/app/api/resume.py
backend/app/api/history.py
backend/app/api/config.py
backend/app/utils/__init__.py
backend/app/utils/file_utils.py
backend/app/utils/sse.py
backend/app/templates/prompts/project_matching.j2
backend/app/templates/prompts/resume_points.j2
backend/app/templates/prompts/resume_writeup.j2
backend/app/templates/prompts/keyword_analysis.j2
backend/app/templates/latex/resume_template.tex.j2
```

### Test files (12 files)
```
backend/tests/__init__.py
backend/tests/conftest.py
backend/tests/test_profile_service.py
backend/tests/test_project_sweep_service.py
backend/tests/test_history_service.py
backend/tests/test_llm_service.py
backend/tests/test_prompt_manager.py
backend/tests/test_matching_service.py
backend/tests/test_resume_points_generator.py
backend/tests/test_resume_writer.py
backend/tests/test_latex_renderer.py
backend/tests/test_orchestrator.py
backend/tests/test_api.py
```

### Frontend (~30 files)
```
frontend/package.json
frontend/vite.config.ts
frontend/tsconfig.json
frontend/tsconfig.node.json
frontend/index.html
frontend/src/main.tsx
frontend/src/App.tsx
frontend/src/api/client.ts
frontend/src/api/profile.ts
frontend/src/api/projects.ts
frontend/src/api/resume.ts
frontend/src/api/history.ts
frontend/src/types/profile.ts
frontend/src/types/project.ts
frontend/src/types/application.ts
frontend/src/types/generation.ts
frontend/src/pages/Dashboard.tsx
frontend/src/pages/NewApplication.tsx
frontend/src/pages/ReviewEdit.tsx
frontend/src/pages/ExportResume.tsx
frontend/src/pages/ProfilePage.tsx
frontend/src/pages/HistoryPage.tsx
frontend/src/components/layout/AppLayout.tsx
frontend/src/components/layout/Navbar.tsx
frontend/src/components/forms/JobDescriptionForm.tsx
frontend/src/components/forms/ProfileForm.tsx
frontend/src/components/resume/ProjectMatchCards.tsx
frontend/src/components/resume/SectionEditor.tsx
frontend/src/components/resume/BulletPointList.tsx
frontend/src/components/resume/ResumePreview.tsx
frontend/src/components/generation/GenerationProgress.tsx
frontend/src/components/generation/StageIndicator.tsx
frontend/src/components/generation/TokenStream.tsx
frontend/src/components/history/ApplicationCard.tsx
frontend/src/components/history/ApplicationDetail.tsx
frontend/src/components/common/LoadingSpinner.tsx
frontend/src/components/common/ErrorBanner.tsx
frontend/src/components/common/EmptyState.tsx
frontend/src/components/common/ConfirmDialog.tsx
frontend/src/hooks/useProfile.ts
frontend/src/hooks/useProjects.ts
frontend/src/hooks/useGeneration.ts
frontend/src/hooks/useHistory.ts
frontend/src/styles/variables.css
frontend/src/styles/global.css
frontend/src/styles/theme.css
frontend/src/utils/formatters.ts
frontend/src/utils/validators.ts
```

### Root files
```
.gitignore
.env.example
README.md
```

**Total: ~72 files**
