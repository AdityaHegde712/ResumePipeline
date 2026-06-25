# Resume Pipeline — Agent Team Composition v2.2

> **Version:** 2.2 (Final — ready for handoff)  
> **Status:** 8 static agents, 0 dynamic agents — all tasks within existing roster

---

## Agent Assignments by Phase

### Phase 0: Project Scaffolding
| Task | Agent | Files |
|------|-------|-------|
| 0.1 Directory structure | `@general-builder` | Root directories |
| 0.2 Python project init | `@backend-dev` | `backend/pyproject.toml`, `.env.example` |
| 0.3 React project init | `@frontend-dev` | `frontend/package.json`, `vite.config.ts`, etc. |
| 0.4 Backend config | `@backend-dev` | `backend/app/config.py` |
| 0.5 Pydantic models | `@data-engineer` | `backend/app/models/*.py` |
| 0.6 TypeScript types | `@frontend-dev` | `frontend/src/types/*.ts` |
| 0.7 Root config files | `@general-builder` | `.gitignore`, `README.md` |

### Phase 1: Data Layer
| Task | Agent | Files |
|------|-------|-------|
| 1.1 ProfileService | `@data-engineer` | `profile_service.py` |
| 1.2 ProjectSweepService | `@data-engineer` | `project_sweep_service.py` |
| 1.3 Project indexing | `@data-engineer` | Extension of above |
| 1.4 Change detection | `@data-engineer` | Extension of above |
| 1.5 HistoryService | `@data-engineer` | `history_service.py` |
| 1.6 Data layer tests | `@tester` | `tests/test_*.py` |

### Phase 2: LLM Integration
| Task | Agent | Files |
|------|-------|-------|
| 2.1 LLMService | `@model-scientist` | `llm_service.py` |
| 2.2 LLM config | `@model-scientist` | Config model |
| 2.3 PromptManager | `@model-scientist` | `prompt_manager.py` |
| 2.4 Prompt templates | `@model-scientist` | `templates/prompts/*.j2` |
| 2.5 LLM tests | `@tester` | `tests/test_llm*.py` |

### Phase 3: Generation Pipeline
| Task | Agent | Files |
|------|-------|-------|
| 3.1 KeywordAnalysisService | `@backend-dev` | `pipeline/keyword_analysis_service.py` |
| 3.2 MatchingService | `@model-scientist` | `pipeline/matching_service.py` |
| 3.3 ResumePointsGenerator | `@backend-dev` | `pipeline/resume_points_generator.py` |
| 3.4 ResumeWriter | `@backend-dev` | `pipeline/resume_writer.py` |
| 3.5 LaTeXRenderer + template | `@backend-dev` | `pipeline/latex_renderer.py`, `templates/latex/*.tex.j2` |
| 3.6 Orchestrator (core) | `@backend-dev` | `pipeline/orchestrator.py` |
| 3.7 PDFCompiler (MiKTeX) | `@backend-dev` | `pipeline/pdf_compiler.py` |
| 3.8 SSE integration | `@backend-dev` | `utils/sse.py` |
| 3.9 Pipeline tests | `@tester` | `tests/test_*.py` |

### Phase 4: API Layer
| Task | Agent | Files |
|------|-------|-------|
| 4.1 App factory + middleware | `@backend-dev` | `main.py`, `utils/file_utils.py` |
| 4.2 Profile API | `@backend-dev` | `api/profile.py` |
| 4.3 Projects API | `@backend-dev` | `api/projects.py` |
| 4.4 Generation API (SSE) | `@backend-dev` | `api/resume.py` |
| 4.5 History API | `@backend-dev` | `api/history.py` |
| 4.6 Config API | `@backend-dev` | `api/config.py` |
| 4.7 API tests | `@tester` | `tests/test_api.py` |

### Phase 5: Frontend
| Task | Agent | Files |
|------|-------|-------|
| 5.1 App shell + routing | `@frontend-dev` | `App.tsx`, `layout/*`, `styles/*` |
| 5.2 API client + hooks | `@frontend-dev` | `api/*.ts`, `hooks/*.ts` |
| 5.3 Dashboard | `@frontend-dev` | `pages/Dashboard.tsx` |
| 5.4 New Application | `@frontend-dev` | `pages/NewApplication.tsx`, `forms/*`, `resume/ProjectMatchCards.tsx` |
| 5.5 Review & Edit | `@frontend-dev` | `pages/ReviewEdit.tsx`, `resume/*`, `generation/*` |
| 5.6 Export Resume | `@frontend-dev` | `pages/ExportResume.tsx` |
| 5.7 Profile Page | `@frontend-dev` | `pages/ProfilePage.tsx`, `forms/ProfileForm.tsx` |
| 5.8 History Page | `@frontend-dev` | `pages/HistoryPage.tsx`, `history/*` |
| 5.9 Common components | `@frontend-dev` | `common/*` |
| 5.10 Shared hooks + utils | `@frontend-dev` | `hooks/*`, `utils/*` |
| 5.11 Frontend tests | `@tester` | `tests/*.tsx` |

### Phase 6: Integration & Polish
| Task | Agent |
|------|-------|
| 6.1 E2E testing | `@tester` |
| 6.2 Error handling audit | `@backend-dev` + `@frontend-dev` |
| 6.3 LaTeX validation | `@backend-dev` |
| 6.4 Security review | `@security-reviewer` |
| 6.5 Code quality pass | `@clean-coder` |
| 6.6 README + docs | `@technical-writer` |
| 6.7 Final regression | `@tester` |

---

## Agent Responsibility Summary

| Agent | Total Tasks | Key Deliverables |
|-------|-------------|------------------|
| `@data-engineer` | 6 | Pydantic models, ProfileService (two-file), ProjectSweepService, HistoryService, indexing |
| `@model-scientist` | 5 | LLMService (LiteLLM), PromptManager (+ env overrides), 4 prompt templates, MatchingService |
| `@backend-dev` | 18 | Project setup, ALL pipeline services (6 incl. PDFCompiler), ALL API endpoints (8 + PDF/tex exports), LaTeX, SSE, error handling |
| `@frontend-dev` | 11 | React app shell, ALL pages (6 incl. PDF download), ALL components (~17), API hooks, styles |
| `@tester` | 7 | Unit tests × data layer, LLM, pipeline (+ PDFCompiler), API. Integration tests. E2E. Regression. |
| `@general-builder` | 2 | Directory structure, gitignore, README scaffold |
| `@security-reviewer` | 1 | Security audit (API keys, LaTeX injection, path traversal) |
| `@clean-coder` | 1 | Linting, type hints, docstrings, code quality |
| `@technical-writer` | 1 | README, setup guide, usage docs |

**Total unique agents:** 9 (8 static + 0 dynamic — all new features fit existing roster)

---

## Execution Order

```
Phase 0 ──────────────────────────────────────────────────────────────
 0.1 → 0.2 → 0.4 → 0.5 → 0.6
 0.3 → (parallel with 0.2-0.6)
 0.7 (after 0.1)

Phase 1 (after 0.5) ─────────────────────────────────────────────────
 1.1, 1.2, 1.5 (parallel, after models defined)
 1.3, 1.4 (after 1.2)
 1.6 (after 1.1, 1.2, 1.5)

Phase 2 (after 0.4, parallel with Phase 1) ──────────────────────────
 2.1, 2.3 (parallel)
 2.2 (after 2.1)
 2.4 (after 2.3)
 2.5 (after 2.1, 2.3)

Phase 3 (after 1.2, 2.1, 2.3) ───────────────────────────────────────
  3.1, 3.2 (parallel)
  3.3 (after 3.1)
  3.4 (after 3.3)
  3.5 (parallel with 3.3-3.4)
  3.6 (after 3.1-3.5)
  3.7 (PDFCompiler, parallel with 3.8 — independent of orchestrator)
  3.8 (SSE, after 3.6 — needs orchestrator interface)
  3.9 (after 3.2-3.8)

Phase 4 (after 3.6, 3.7) ──────────────────────────────────────────────
  4.1, 4.2, 4.3, 4.5, 4.6 (partially parallel)
  4.4 (after 4.1, needs orchestrator + PDFCompiler — includes PDF/tex export endpoints)
  4.7 (after all endpoints)

Phase 5 (after 4.x, partial parallel with 3.x) ──────────────────────
 5.1, 5.2 → 5.3 → 5.4 → 5.5 → 5.6 → 5.7 → 5.8 → 5.9 → 5.10 → 5.11
 (mostly sequential due to component dependencies)

Phase 6 (after all prior) ───────────────────────────────────────────
 6.1 → 6.2-6.5 (parallel) → 6.6 → 6.7
```

---

## Key Interfaces Between Agents

### DataEngineer → BackendDev
Pydantic models → imported by all services and API endpoints. Must be stable before Phase 3-4 work begins.

### ModelScientist → BackendDev
LLMService + PromptManager → consumed by Pipeline services (MatchingService, ResumePointsGenerator, Orchestrator). Interface: `llm.generate(messages, task, ...)`.

### BackendDev → FrontendDev
API endpoints → consumed by frontend API hooks. Must document request/response shapes. FastAPI auto-generates OpenAPI spec at `/api/docs`.

### Tester (cross-phase)
Tests written alongside implementation, not at end. Each phase's tests are in that phase's task list.
