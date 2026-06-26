# Tasks — ResumeWriter

## Checklist

- [x] Explore existing codebase (models, services, templates)
- [x] Create `backend/app/pipeline/resume_writer.py`
  - [x] Imports and module docstring (`from __future__ import annotations`)
  - [x] Class `ResumeWriter` with `__init__(llm_service, prompt_manager)`
  - [x] `async compile_resume()` — main pipeline
  - [x] `deduplicate()` — cross-section Jaccard > 0.8 removal
  - [x] `order_sections()` — profile-driven sorting
  - [x] `_has_writeup_template()` — check for `resume_writeup.j2`
  - [x] `async _polish_with_llm()` — LLM streaming/non-streaming polish
  - [x] Module-level helpers:
    - [x] `_normalize(text) → set[str]`
    - [x] `_jaccard_similarity(text_a, text_b) → float`
    - [x] `_section_rank(section_key, order) → int`
    - [x] `_parse_llm_response(text) → list[SectionPoints] | None`
- [x] Create task documentation artifacts (PLAN.md, TASKS.md, STATUS.md)
