# Resume Pipeline — Status

> **Current Phase:** Awaiting Owner Confirmation  
> **Plan Version:** 2.2 (Final Draft + PDF Compiler + Prompt Overrides)  
> **Last Updated:** June 25, 2026 — 01:41 PM

---

## Current State

| Item | Status |
|------|--------|
| Requirements gathered | ✅ Complete |
| R&D (LiteLLM validation) | ✅ Complete |
| Template.tex acquired | ✅ Complete |
| Architecture plan (v2.2) | ✅ Complete — 5 design updates applied |
| Two-profile model (profile.yaml + subjective_profile.md) | ✅ Integrated into PLAN.md, TASKS.md |
| Publications model + LaTeX section | ✅ Integrated into models, renderer, profile editor |
| Section ordering (configurable) | ✅ Integrated into profile model, LaTeX template, UI |
| **PDF Compiler (MiKTeX wrapper)** | ✅ Added — Task 3.7 (new), Task 4.4 PDF endpoint |
| **Prompt env-var overrides** | ✅ PromptManager checks PROMPT_* env vars before .j2 files |
| Open questions resolved | ✅ Complete (11/11) |
| Owner confirmation | ⏳ Pending — sample .j2 in docs/ |

---

## Design Decisions (June 25, Session #2)

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | **LLM providers** | Gemini primary (MVP). Second OpenAI-compatible block ready for DeepSeek swap-in. | One API key for MVP; DeepSeek V4 Flash added later for keyword matching. LiteLLM handles all. |
| 2 | **Profile storage** | YAML for profile, JSON for history | Human-editability where it matters (profile), reliable programmatic storage for history |
| 3 | **Cover letter output** | Deferred entirely | Build corpus of 15-20 manually-written letters first, extract patterns, then automate |
| 4 | **Sweep file refresh** | Auto-detect on startup + manual refresh button | Both for best UX; auto-detect is lightweight (file mtime check) |
| 5 | **UI streaming** | Both stage progress + token streaming | Stage indicators for pipeline overview, token stream for generation detail |
| 6 | **Bullet editing** | Full edit/resequence | User controls final output before .tex export |
| 7 | **History retention** | Keep all + delete buttons + view | No automatic pruning; user manages cleanup |
| 8 | **MVP provider scope** | Gemini-only with LiteLLM abstraction + OpenAI-client block ready for DeepSeek | Ship faster, optimize later |
| 9 | **Cover letter UI** | Skip entirely — no cover letter fields in v1.0 | Pure vNext feature |

---

## Updated Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-25 | Provider-agnostic LLM layer via LiteLLM | User hasn't decided provider; LiteLLM supports 100+ with unified interface |
| 2026-06-25 | LaTeX export (not direct PDF) | User has existing Overleaf workflow with template.tex |
| 2026-06-25 | Two-stage generation (points → write-up) | Allows user review/edit at bullet-point level before final composition |
| 2026-06-25 | JSON/YAML storage first, SQLite as upgrade | Simpler MVP; user can decide at detailed planning |
| 2026-06-25 | Multi-provider LLM architecture | Different LLMs suited to different tasks in the pipeline |
| 2026-06-25 | Cover letter deferred to vNext | Build pattern library from 15-20 manual samples first |
| 2026-06-25 | YAML for profile, JSON for history | Optimal fit for human-editability vs programmatic access |
| 2026-06-25 | Cover letter output: Markdown → PDF (vNext) | User's preferred workflow when implemented |
| 2026-06-25 | **Two-profile storage model** | YAML for objective/profile data (human-editable), Markdown for subjective/narrative (vNext cover letters). Prose belongs in markdown, not YAML. |
| 2026-06-25 | **Publications as static model** | Publications are fixed text from profile, rendered directly into LaTeX via section_order. No LLM generation needed. |
| 2026-06-25 | **Section ordering configurable in profile** | `section_order` list in UserProfile defaults to evidence-backed order (Education→Skills→Projects→Experience→Publications→Leadership). User can reorder via UI. |
| 2026-06-25 | **PDF compilation via MiKTeX pdflatex** | Local .tex→.PDF compilation gives instant downloads from the app. Separate API endpoint, not part of generation pipeline. User can choose .tex or .pdf. |
| 2026-06-25 | **Prompt env-var overrides** | PROMPT_MATCHING, PROMPT_KEYWORD_ANALYSIS, PROMPT_RESUME_POINTS, PROMPT_RESUME_WRITEUP env vars override .j2 template files at runtime. Jinja2 syntax preserved. |
| 2026-06-25 | **Sample .j2 template in docs/** | Generated `docs/resume_points_sample.j2` so user can review the prompt template pattern before implementation. |

---

## Open Questions

All ✅ resolved. No remaining blockers.

---

## Next Actions

1. ☐ **Review `docs/resume_points_sample.j2`** — sample prompt template to understand how Jinja2 + LLM prompts work together
2. ☐ **Confirm v2.2 plan** (all 5 design changes applied: two-profile, publications, section_order, PDF compiler, prompt overrides)
3. ☐ Upon confirmation → deliver PLAN.md, TASKS.md, AGENT_TEAM.md to Orchestrator
4. ☐ Phase 0: Monorepo scaffolding, Python + React init, config, models, types
5. ☐ Phase 1: Data layer — ProfileService (two files), ProjectSweepService, HistoryService
6. ☐ Phase 2: LLM integration — LLMService, PromptManager, 4 prompt templates
7. ☐ Phase 3: Generation pipeline — 7 pipeline services + orchestrator + SSE + PDF compiler
8. ☐ Phase 4: API layer — 13 REST endpoints, SSE streaming, PDF download
9. ☐ Phase 5: Frontend — 6 pages, ~17 components, dark theme
10. ☐ Phase 6: Integration, testing, security, docs
