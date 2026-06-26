# Orchestrator Implementation Plan

## Task
Create `backend/app/pipeline/orchestrator.py` implementing the `Orchestrator` class
— the central pipeline coordinator for resume generation.

## Architecture

The Orchestrator ties together 10 services into a sequenced pipeline with
SSE streaming events:

1. **ProfileService** → Load user profile
2. **ProjectSweepService** → Load projects from sweep file
3. **MatchingService** → Score/re-rank projects vs job description
4. **KeywordAnalysisService** → Extract structured keywords from JD
5. **ResumePointsGenerator** → Generate bullet points per section (streaming)
6. **ResumeWriter** → Compile, deduplicate, order, polish sections
7. **LaTeXRenderer** → Render profile + sections to LaTeX string
8. **HistoryService** → Persist Application lifecycle

## Routes

- `run_full_pipeline()` — All 8 stages (create → match → keywords → points → write → latex → complete)
- `run_points_only()` — Stages 1-5 (stop after points generation for review)
- `run_resume_only()` — Stages 6-8 (re-compile and re-render existing app)
- `regenerate_section()` — Regenerate bullets for one section, re-render LaTeX

## Design Decisions

### Dependency Injection
All services passed via constructor — no service locator or global state.

### Error Handling
Each pipeline stage wrapped in try/except. On failure:
1. Set `app.generation_status = FAILED`
2. Set `app.error_message`
3. Persist via `history.update()`
4. Emit SSE error event
5. Return the Application (don't re-raise)

### Model Alignment
Adapted the spec to match actual codebase models:
- Uses `Application.generated: GeneratedContent` (not flat fields)
- Uses `GenerationStatus` enum (PENDING, MATCHING, GENERATING_POINTS, etc.)
- `MatchResult.relevance_score` (not `.score`)
- `KeywordAnalysisService.analyze()` returns `dict` (not `KeywordAnalysisResult`)

### SSE Streaming
`on_token` callbacks bridge generator streaming to SSE token events.
`on_section_complete` callbacks emit `section_complete` events.
