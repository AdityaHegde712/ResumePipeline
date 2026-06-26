# Tasks — Orchestrator Implementation

- [x] Read all existing models (`application.py`, `generation.py`, `profile.py`, `project.py`)
- [x] Read all existing services (history, profile, project_sweep, llm, prompt_manager)
- [x] Read all existing pipeline services (matching, keyword_analysis, resume_points_generator, resume_writer, latex_renderer)
- [x] Read SSE event builder (`utils/sse.py`)
- [x] Read config and package init files
- [x] Design `Orchestrator.__init__` with dependency injection
- [x] Implement `run_full_pipeline()` — 8 stages with error handling
- [x] Implement `run_points_only()` — steps 1-5
- [x] Implement `run_resume_only()` — steps 6-8 from existing app
- [x] Implement `regenerate_section()` — single section regen + re-render
- [x] Implement SSE callback factories (`_make_on_token`, etc.)
- [x] Implement error handling (`_handle_pipeline_error`)
- [x] Implement helper methods (`_create_application`, `_load_profile`, `_build_section_context`, etc.)
- [x] Verify syntax (`ast.parse`)
- [x] Verify imports (`python -c "from app.pipeline.orchestrator import Orchestrator"`)
- [x] Write plan/log documentation
