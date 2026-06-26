"""
Central pipeline orchestrator — ties together all services for resume generation.

The Orchestrator is the top-level coordinator that manages the full generation
lifecycle: creating applications, running the pipeline stages (project loading,
matching, keyword analysis, points generation, resume writing, LaTeX rendering),
and streaming SSE progress events to the caller.

Usage::
    orchestrator = Orchestrator(
        profile_service=profile_service,
        project_service=project_sweep_service,
        history_service=history_service,
        llm_service=llm_service,
        prompt_manager=prompt_manager,
        matching_service=matching_service,
        keyword_service=keyword_analysis_service,
        points_generator=resume_points_generator,
        resume_writer=resume_writer,
        latex_renderer=latex_renderer,
    )
    app = await orchestrator.run_full_pipeline(request, emit)
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Optional

from app.models.application import (
    Application,
    BulletPoint,
    GeneratedContent,
    GenerationStatus,
    SectionPoints,
)
from app.models.generation import GenerationRequest, MatchResult
from app.models.profile import Experience, UserProfile
from app.models.project import ProjectEntry
from app.pipeline.keyword_analysis_service import KeywordAnalysisService
from app.pipeline.latex_renderer import LaTeXRenderer
from app.pipeline.matching_service import MatchingService
from app.pipeline.resume_points_generator import ResumePointsGenerator
from app.pipeline.resume_writer import ResumeWriter
from app.services.history_service import HistoryService
from app.services.llm_service import LLMService
from app.services.profile_service import ProfileService
from app.services.project_sweep_service import ProjectSweepService
from app.services.prompt_manager import PromptManager
from app.utils.sse import SSEEventBuilder

logger = logging.getLogger(__name__)


def _format_project_details(project: ProjectEntry) -> str:
    """Format a ProjectEntry into a text block suitable for prompt injection.

    This mirrors the private helper in ``ResumePointsGenerator`` so the
    orchestrator can build section details when regenerating individual sections
    without depending on an internal method.
    """
    parts = [
        f"Type: {project.type}",
        f"Tech Stack: {', '.join(project.tech_stack)}",
        f"Summary: {project.summary}",
    ]
    if project.key_features:
        parts.append(f"Key Features: {'; '.join(project.key_features)}")
    if project.resume_value_bullets:
        parts.append(f"Resume Value: {'; '.join(project.resume_value_bullets)}")
    if project.lines_of_code:
        parts.append(f"Scale: {project.lines_of_code:,} lines of code")
    return "\n".join(parts)


def _format_experience_details(exp: Experience) -> str:
    """Format an Experience entry into a text block for the prompt.

    Mirrors the private helper in ``ResumePointsGenerator``.
    """
    parts = [
        f"Company: {exp.company}",
        f"Role: {exp.role}",
        f"Dates: {exp.start_date} - {exp.end_date}",
        f"Location: {exp.location}",
        f"Description: {exp.description}",
    ]
    if exp.highlights:
        parts.append(f"Highlights: {'; '.join(exp.highlights)}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Stage name constants — must match SSEEventBuilder.STAGES
# ---------------------------------------------------------------------------
STAGE_INITIALIZING = "initializing"
STAGE_LOADING_PROJECTS = "loading_projects"
STAGE_MATCHING_PROJECTS = "matching_projects"
STAGE_ANALYZING_KEYWORDS = "analyzing_keywords"
STAGE_GENERATING_POINTS = "generating_points"
STAGE_WRITING_RESUME = "writing_resume"
STAGE_RENDERING_LATEX = "rendering_latex"
STAGE_COMPLETE = "complete"


class Orchestrator:
    """Central pipeline orchestrator for resume generation.

    Coordinates all pipeline services, manages the Application lifecycle, and
    streams progress events via the ``emit`` callback.

    Every public method returns the final ``Application`` object. On failure,
    the application's ``generation_status`` is set to ``FAILED`` and
    ``error_message`` contains the error details.
    """

    def __init__(
        self,
        profile_service: ProfileService,
        project_service: ProjectSweepService,
        history_service: HistoryService,
        llm_service: LLMService,
        prompt_manager: PromptManager,
        matching_service: MatchingService,
        keyword_service: KeywordAnalysisService,
        points_generator: ResumePointsGenerator,
        resume_writer: ResumeWriter,
        latex_renderer: LaTeXRenderer,
    ) -> None:
        """Initialize the orchestrator with all required services.

        Args:
            profile_service: Loads the user's profile (YAML + markdown).
            project_service: Reads and indexes PROJECT_SWEEP_SUMMARIES.md.
            history_service: Persists/loads Application records as JSON files.
            llm_service: Provider-agnostic LLM client (LiteLLM).
            prompt_manager: Loads Jinja2 prompt templates.
            matching_service: Scores project relevance against job descriptions.
            keyword_service: Extracts structured keywords from job descriptions.
            points_generator: Generates ATS-optimized bullet points per section.
            resume_writer: Compiles and optionally polishes sections.
            latex_renderer: Renders profile + sections into a LaTeX string.
        """
        self.profile_service = profile_service
        self.project_service = project_service
        self.history = history_service
        self.llm = llm_service
        self.prompts = prompt_manager
        self.matching_service = matching_service
        self.keyword_service = keyword_service
        self.points_generator = points_generator
        self.resume_writer = resume_writer
        self.latex_renderer = latex_renderer

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_full_pipeline(
        self,
        request: GenerationRequest,
        emit: Callable[[str, dict], Awaitable[None]],
    ) -> Application:
        """Run the complete resume generation pipeline — all 8 stages.

        Pipeline stages:
            1. **initializing** — Create Application with ``PENDING`` status,
               persist to history.
            2. **loading_projects** — Load all projects from the sweep file.
            3. **matching_projects** — Score/re-rank projects against the JD.
            4. **analyzing_keywords** — Extract structured keywords from the JD.
            5. **generating_points** — Generate bullet points per section
               (streaming tokens via SSE).
            6. **writing_resume** — Compile, deduplicate, order, and polish
               sections.
            7. **rendering_latex** — Convert profile + sections to LaTeX.
            8. **complete** — Update status to ``COMPLETED`` and emit final
               event.

        Args:
            request: Generation parameters (job title, description, etc.).
            emit: Async callback ``(event_type, data_dict)`` for SSE streaming.

        Returns:
            The final ``Application`` with generated content. On failure the
            status is ``FAILED`` and ``error_message`` is populated.
        """
        # ── Stage 1: Initialise ─────────────────────────────────────────
        app = await self._create_application(request)
        app.generation_status = GenerationStatus.PENDING
        app = await self.history.create(app)
        await self._emit_stage(emit, STAGE_INITIALIZING, "start")
        logger.info("Pipeline started: app=%s job=%s @ %s", app.id, request.job_title, request.company_name)

        try:
            # ── Stage 2: Load projects ─────────────────────────────────
            await self._emit_stage(emit, STAGE_LOADING_PROJECTS, "start")
            all_projects = self.project_service.get_all()
            projects = self._filter_selected_projects(all_projects, request.selected_project_ids)
            logger.info("Loaded %d projects (%d after selection)", len(all_projects), len(projects))
            await self._emit_stage(emit, STAGE_LOADING_PROJECTS, "complete", count=len(projects))

            # ── Stage 3: Match projects ────────────────────────────────
            await self._emit_stage(emit, STAGE_MATCHING_PROJECTS, "start")
            app.generation_status = GenerationStatus.MATCHING
            await self.history.update(app)

            match_results = await self.matching_service.match(
                job_title=request.job_title,
                company_name=request.company_name,
                job_description=request.job_description,
                projects=projects,
                company_description=request.company_description or "",
            )
            # Persist selected project IDs from matches
            app.selected_project_ids = [m.project_id for m in match_results]
            await self.history.update(app)
            await self._emit_stage(
                emit, STAGE_MATCHING_PROJECTS, "complete",
                matches=[m.model_dump() for m in match_results],
            )

            # ── Stage 4: Analyse keywords ──────────────────────────────
            await self._emit_stage(emit, STAGE_ANALYZING_KEYWORDS, "start")
            keyword_data = await self.keyword_service.analyze(
                job_title=request.job_title,
                company_name=request.company_name,
                job_description=request.job_description,
            )
            jd_keywords_text = self.keyword_service.extract_keywords_text(keyword_data)
            logger.info("Keyword analysis complete — %d skill categories", len(keyword_data))
            await self._emit_stage(emit, STAGE_ANALYZING_KEYWORDS, "complete")

            # ── Stage 5: Generate points ───────────────────────────────
            await self._emit_stage(emit, STAGE_GENERATING_POINTS, "start")
            app.generation_status = GenerationStatus.GENERATING_POINTS
            await self.history.update(app)

            # Load the user profile
            profile = await self._load_profile()

            # Matched project entries (full objects, not just IDs)
            matched_projects = self._resolve_matched_projects(match_results, projects)

            sections = await self.points_generator.generate_all(
                job_title=request.job_title,
                company_name=request.company_name,
                job_description=request.job_description,
                jd_keywords=jd_keywords_text,
                selected_projects=matched_projects,
                profile=profile,
                tone=request.tone,
                on_token=self._make_on_token(emit),
                on_section_complete=self._make_on_section_complete(emit),
            )
            app.generated = GeneratedContent(
                resume_points=sections,
                model_used=self.llm.get_model_for_task("resume_points"),
            )
            await self.history.update(app)
            await self._emit_stage(
                emit, STAGE_GENERATING_POINTS, "complete",
                section_count=len(sections),
                bullet_count=sum(len(s.bullets) for s in sections),
            )

            # ── Stage 6: Write resume ──────────────────────────────────
            await self._emit_stage(emit, STAGE_WRITING_RESUME, "start")
            app.generation_status = GenerationStatus.WRITING_RESUME
            await self.history.update(app)

            compiled_sections = await self.resume_writer.compile_resume(
                sections=sections,
                profile=profile,
                job_title=request.job_title,
                company_name=request.company_name,
                on_token=self._make_on_write_token(emit),
            )
            app.generated.resume_points = compiled_sections
            await self.history.update(app)
            await self._emit_stage(
                emit, STAGE_WRITING_RESUME, "complete",
                section_count=len(compiled_sections),
            )

            # ── Stage 7: Render LaTeX ──────────────────────────────────
            await self._emit_stage(emit, STAGE_RENDERING_LATEX, "start")
            app.generation_status = GenerationStatus.RENDERING_LATEX
            await self.history.update(app)

            latex_content = self.latex_renderer.render(
                profile=profile,
                sections=compiled_sections,
            )
            app.generated.resume_latex = latex_content
            await self.history.update(app)
            await self._emit_stage(
                emit, STAGE_RENDERING_LATEX, "complete",
                latex_length=len(latex_content),
            )

            # ── Stage 8: Complete ──────────────────────────────────────
            app.generation_status = GenerationStatus.COMPLETED
            app = await self.history.update(app)
            await self._emit_complete(emit, app, sections=compiled_sections)
            logger.info("Pipeline completed successfully: app=%s", app.id)
            return app

        except Exception as exc:
            return await self._handle_pipeline_error(emit, app, exc)

    async def run_points_only(
        self,
        request: GenerationRequest,
        emit: Callable[[str, dict], Awaitable[None]],
    ) -> Application:
        """Run the pipeline through points generation only (steps 1-5).

        Stops after bullet-point generation and sets status to
        ``GENERATING_POINTS``.  Useful for the "Review & Edit" phase where the
        user wants to inspect / tweak generated content before the final resume
        export.

        Args:
            request: Generation parameters.
            emit: Async callback for SSE streaming.

        Returns:
            ``Application`` with generated points (``app.generated.resume_points``
            populated) but no compiled resume or LaTeX.
        """
        app = await self._create_application(request)
        app.generation_status = GenerationStatus.PENDING
        app = await self.history.create(app)
        await self._emit_stage(emit, STAGE_INITIALIZING, "start")

        try:
            # Stage 2 — Load projects
            await self._emit_stage(emit, STAGE_LOADING_PROJECTS, "start")
            all_projects = self.project_service.get_all()
            projects = self._filter_selected_projects(all_projects, request.selected_project_ids)
            await self._emit_stage(emit, STAGE_LOADING_PROJECTS, "complete", count=len(projects))

            # Stage 3 — Match projects
            await self._emit_stage(emit, STAGE_MATCHING_PROJECTS, "start")
            app.generation_status = GenerationStatus.MATCHING
            await self.history.update(app)

            match_results = await self.matching_service.match(
                job_title=request.job_title,
                company_name=request.company_name,
                job_description=request.job_description,
                projects=projects,
                company_description=request.company_description or "",
            )
            app.selected_project_ids = [m.project_id for m in match_results]
            await self.history.update(app)
            await self._emit_stage(
                emit, STAGE_MATCHING_PROJECTS, "complete",
                matches=[m.model_dump() for m in match_results],
            )

            # Stage 4 — Analyse keywords
            await self._emit_stage(emit, STAGE_ANALYZING_KEYWORDS, "start")
            keyword_data = await self.keyword_service.analyze(
                job_title=request.job_title,
                company_name=request.company_name,
                job_description=request.job_description,
            )
            jd_keywords_text = self.keyword_service.extract_keywords_text(keyword_data)
            await self._emit_stage(emit, STAGE_ANALYZING_KEYWORDS, "complete")

            # Stage 5 — Generate points
            await self._emit_stage(emit, STAGE_GENERATING_POINTS, "start")
            app.generation_status = GenerationStatus.GENERATING_POINTS
            await self.history.update(app)

            profile = await self._load_profile()
            matched_projects = self._resolve_matched_projects(match_results, projects)

            sections = await self.points_generator.generate_all(
                job_title=request.job_title,
                company_name=request.company_name,
                job_description=request.job_description,
                jd_keywords=jd_keywords_text,
                selected_projects=matched_projects,
                profile=profile,
                tone=request.tone,
                on_token=self._make_on_token(emit),
                on_section_complete=self._make_on_section_complete(emit),
            )
            app.generated = GeneratedContent(
                resume_points=sections,
                model_used=self.llm.get_model_for_task("resume_points"),
            )
            app = await self.history.update(app)
            await self._emit_stage(
                emit, STAGE_GENERATING_POINTS, "complete",
                section_count=len(sections),
                bullet_count=sum(len(s.bullets) for s in sections),
            )

            # Done — points are ready
            await self._emit_complete(
                emit, app,
                sections=sections,
                message="Points generation complete — ready for review",
            )
            logger.info("Points-only pipeline completed: app=%s", app.id)
            return app

        except Exception as exc:
            return await self._handle_pipeline_error(emit, app, exc)

    async def run_resume_only(
        self,
        application_id: str,
        emit: Callable[[str, dict], Awaitable[None]],
    ) -> Application:
        """Re-run the write + render stages for an existing application.

        Skips directly to:
            6. **writing_resume** — Compile/deduplicate/polish existing points.
            7. **rendering_latex** — Re-render the LaTeX string.
            8. **complete** — Mark ``COMPLETED`` and notify.

        Used when a user already has generated points and wants to re-export
        (e.g. after editing bullets or changing the target job).

        Args:
            application_id: ID of the existing application to resume from.
            emit: Async callback for SSE streaming.

        Returns:
            Updated ``Application`` with new compiled content and LaTeX.
        """
        app = await self._load_application_or_fail(application_id, emit)
        if app is None:
            # _load_application_or_fail already emitted the error
            return app

        # Start from initializing stage
        await self._emit_stage(emit, STAGE_INITIALIZING, "start")

        try:
            profile = await self._load_profile()
            sections = app.generated.resume_points if app.generated and app.generated.resume_points else []

            if not sections:
                msg = f"Application {application_id} has no generated points to compile"
                raise ValueError(msg)

            # Stage 6 — Write resume
            await self._emit_stage(emit, STAGE_WRITING_RESUME, "start")
            app.generation_status = GenerationStatus.WRITING_RESUME
            await self.history.update(app)

            compiled_sections = await self.resume_writer.compile_resume(
                sections=sections,
                profile=profile,
                job_title=app.job_title,
                company_name=app.company_name,
                on_token=self._make_on_write_token(emit),
            )
            if app.generated is None:
                app.generated = GeneratedContent()
            app.generated.resume_points = compiled_sections
            await self.history.update(app)
            await self._emit_stage(
                emit, STAGE_WRITING_RESUME, "complete",
                section_count=len(compiled_sections),
            )

            # Stage 7 — Render LaTeX
            await self._emit_stage(emit, STAGE_RENDERING_LATEX, "start")
            app.generation_status = GenerationStatus.RENDERING_LATEX
            await self.history.update(app)

            latex_content = self.latex_renderer.render(
                profile=profile,
                sections=compiled_sections,
            )
            app.generated.resume_latex = latex_content
            await self.history.update(app)
            await self._emit_stage(
                emit, STAGE_RENDERING_LATEX, "complete",
                latex_length=len(latex_content),
            )

            # Stage 8 — Complete
            app.generation_status = GenerationStatus.COMPLETED
            app = await self.history.update(app)
            await self._emit_complete(emit, app)
            logger.info("Resume-only pipeline completed: app=%s", app.id)
            return app

        except Exception as exc:
            return await self._handle_pipeline_error(emit, app, exc)

    async def regenerate_section(
        self,
        application_id: str,
        section_key: str,
        emit: Callable[[str, dict], Awaitable[None]],
        custom_instructions: str = "",
    ) -> Application:
        """Regenerate bullet points for a single section of an existing application.

        Workflow:
            1. Load the existing application and its profile.
            2. Build section context (project details / experience details).
            3. Call ``ResumePointsGenerator`` to generate new bullets for the
               section.
            4. Replace the section's bullets in ``app.generated.resume_points``.
            5. Re-run the LaTeX renderer with the updated sections.
            6. Save and return the updated application.

        Args:
            application_id: Existing application ID.
            section_key: Which section to regenerate (e.g. ``"project:abc123"``
                or ``"experience:company-x"``).
            emit: Async callback for SSE streaming.
            custom_instructions: Optional user-provided instructions to guide
                the LLM during regeneration.

        Returns:
            Updated ``Application`` with regenerated bullets for the given section.
        """
        app = await self._load_application_or_fail(application_id, emit)
        if app is None:
            return app

        await self._emit_stage(emit, STAGE_INITIALIZING, "start")

        try:
            profile = await self._load_profile()

            # Resolve the section to regenerate
            existing_sections = (
                app.generated.resume_points
                if app.generated and app.generated.resume_points
                else []
            )

            # Find the target section index
            target_idx: Optional[int] = None
            for i, sec in enumerate(existing_sections):
                if sec.section_key == section_key:
                    target_idx = i
                    break

            if target_idx is None:
                msg = f"Section '{section_key}' not found in application {application_id}"
                raise ValueError(msg)

            # Build section context for the LLM
            section_type, section_name, section_details = self._build_section_context(
                section_key, profile,
            )

            # Get the JD keywords from stored data or recompute
            jd_keywords_text = await self._get_or_recompute_keywords(app)

            # Emit that we're generating points for this section
            await self._emit_stage(emit, STAGE_GENERATING_POINTS, "start", section=section_key)

            # Generate new bullets for this section
            new_bullet_texts = await self.points_generator.generate_for_section(
                section_type=section_type,
                section_name=section_name,
                section_details=section_details,
                job_title=app.job_title,
                company_name=app.company_name,
                jd_keywords_text=jd_keywords_text,
                tone=self._infer_tone(app),
                num_bullets=max(len(existing_sections[target_idx].bullets), 3),
                on_token=self._make_on_section_token(emit, section_key),
            )

            # Rebuild the section with new bullets
            new_bullets: list[BulletPoint] = []
            for i, text in enumerate(new_bullet_texts):
                new_bullets.append(
                    BulletPoint(
                        id=f"regenerated-{section_key}-{i}",
                        section=section_key,
                        text=text,
                        order=i,
                    )
                )

            # Replace the old section
            existing_sections[target_idx] = SectionPoints(
                section_key=existing_sections[target_idx].section_key,
                section_title=existing_sections[target_idx].section_title,
                bullets=new_bullets,
            )

            await self._emit_stage(
                emit, STAGE_GENERATING_POINTS, "complete",
                section=section_key,
                bullet_count=len(new_bullets),
            )

            # Re-render LaTeX
            await self._emit_stage(emit, STAGE_RENDERING_LATEX, "start")
            latex_content = self.latex_renderer.render(
                profile=profile,
                sections=existing_sections,
            )
            if app.generated is None:
                app.generated = GeneratedContent()
            app.generated.resume_points = existing_sections
            app.generated.resume_latex = latex_content
            app = await self.history.update(app)
            await self._emit_stage(
                emit, STAGE_RENDERING_LATEX, "complete",
                latex_length=len(latex_content),
            )

            await self._emit_complete(emit, app, sections=existing_sections)
            logger.info(
                "Section regenerated: app=%s section=%s (%d bullets)",
                app.id, section_key, len(new_bullets),
            )
            return app

        except Exception as exc:
            return await self._handle_pipeline_error(emit, app, exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _create_application(self, request: GenerationRequest) -> Application:
        """Build a minimal ``Application`` from a ``GenerationRequest``.

        The application is **not** persisted here — the caller is responsible
        for calling ``history.create()``.
        """
        now = datetime.now()
        app = Application(
            id="",  # history.create() will auto-generate
            created_at=now,
            updated_at=now,
            company_name=request.company_name,
            company_description=request.company_description,
            job_title=request.job_title,
            job_description=request.job_description,
            selected_project_ids=list(request.selected_project_ids),
            generation_status=GenerationStatus.PENDING,
            generated=None,
            error_message=None,
        )
        return app

    async def _load_profile(self) -> UserProfile:
        """Load the user profile, logging a warning if not found."""
        try:
            profile = await self.profile_service.load()
            if not profile.name:
                logger.warning("Profile loaded but 'name' field is empty")
            return profile
        except Exception as exc:
            logger.warning("Failed to load user profile: %s", exc)
            # Return a default profile so the pipeline can continue
            return UserProfile()

    async def _load_application_or_fail(
        self,
        application_id: str,
        emit: Callable[[str, dict], Awaitable[None]],
    ) -> Optional[Application]:
        """Load an application by ID, emitting an error if not found.

        Returns ``None`` if the application could not be loaded — the caller
        should short-circuit and return immediately.
        """
        try:
            app = await self.history.get(application_id)
            if app is None:
                msg = f"Application not found: {application_id}"
                await self._emit_error(emit, STAGE_INITIALIZING, msg)
                logger.error(msg)
                return None
            return app
        except Exception as exc:
            msg = f"Failed to load application {application_id}: {exc}"
            await self._emit_error(emit, STAGE_INITIALIZING, msg)
            logger.exception(msg)
            return None

    async def _get_or_recompute_keywords(self, app: Application) -> str:
        """Return the JD keywords text for an application.

        Attempts to recompute from the stored job description.  Returns an
        empty string if the job description is missing.
        """
        if not app.job_description:
            return ""
        try:
            keyword_data = await self.keyword_service.analyze(
                job_title=app.job_title,
                company_name=app.company_name,
                job_description=app.job_description,
            )
            return self.keyword_service.extract_keywords_text(keyword_data)
        except Exception as exc:
            logger.warning("Failed to recompute keywords for %s: %s", app.id, exc)
            return ""

    def _filter_selected_projects(
        self,
        all_projects: list[ProjectEntry],
        selected_ids: list[str],
    ) -> list[ProjectEntry]:
        """Filter projects to only those in *selected_ids*.

        If *selected_ids* is empty, all projects are returned.
        """
        if not selected_ids:
            return all_projects
        id_set = set(selected_ids)
        return [p for p in all_projects if p.id in id_set]

    def _resolve_matched_projects(
        self,
        match_results: list[MatchResult],
        all_projects: list[ProjectEntry],
    ) -> list[ProjectEntry]:
        """Resolve ``MatchResult`` objects back to full ``ProjectEntry`` objects.

        Preserves the ordering from *match_results* (highest score first).
        """
        project_map = {p.id: p for p in all_projects}
        resolved: list[ProjectEntry] = []
        seen: set[str] = set()
        for mr in match_results:
            project = project_map.get(mr.project_id)
            if project is not None and project.id not in seen:
                resolved.append(project)
                seen.add(project.id)
        return resolved

    def _build_section_context(
        self,
        section_key: str,
        profile: UserProfile,
    ) -> tuple[str, str, str]:
        """Build (section_type, section_name, section_details) for a section key.

        Handles ``project:<id>`` and ``experience:<company-slug>`` keys.
        Raises ``ValueError`` if the section type cannot be determined or the
        underlying data is missing.
        """
        if section_key.startswith("project:"):
            project_id = section_key[len("project:"):]
            project = self.project_service.get_by_id(project_id)
            if project is None:
                raise ValueError(f"Project '{project_id}' not found in sweep data")
            return "Project", project.name, _format_project_details(project)

        if section_key.startswith("experience:"):
            # Match by normalized company name
            target_slug = section_key[len("experience:"):].lower().replace("-", " ")
            for exp in profile.experience:
                exp_slug = exp.company.lower().replace(" ", "-")
                if exp_slug == section_key[len("experience:"):] or exp.company.lower() == target_slug:
                    return "Experience", f"{exp.role} @ {exp.company}", _format_experience_details(exp)
            raise ValueError(
                f"Experience entry matching '{section_key}' not found in profile"
            )

        # Fallback for top-level sections (education, skills, etc.)
        # These typically don't need regeneration, but provide a basic context.
        if section_key in ("education", "skills", "publications", "leadership", "certifications"):
            return section_key.capitalize(), section_key.replace("_", " ").title(), ""

        raise ValueError(f"Unrecognised section key: '{section_key}'")

    def _infer_tone(self, app: Application) -> str:
        """Infer the tone setting from an Application.

        Since the Application model does not persist the tone, default to
        ``"professional"``.  Subclasses that need tone persistence can override.
        """
        return "professional"

    # ------------------------------------------------------------------
    # SSE event helpers
    # ------------------------------------------------------------------

    async def _emit_stage(
        self,
        emit: Callable[[str, dict], Awaitable[None]],
        stage_name: str,
        status: str,
        **extra,
    ) -> None:
        """Emit a stage event via the SSE callback."""
        event_type, data = SSEEventBuilder.stage(stage_name, status, **extra)
        await emit(event_type, data)

    async def _emit_error(
        self,
        emit: Callable[[str, dict], Awaitable[None]],
        stage: str,
        message: str,
        **extra,
    ) -> None:
        """Emit an error event via the SSE callback."""
        event_type, data = SSEEventBuilder.error(stage, message, **extra)
        await emit(event_type, data)

    async def _emit_complete(
        self,
        emit: Callable[[str, dict], Awaitable[None]],
        app: Application,
        **extra,
    ) -> None:
        """Emit a pipeline-complete event via the SSE callback."""
        total_tokens = 0
        if app.generated and app.generated.resume_points:
            total_tokens = sum(
                len(b.text.split()) for s in app.generated.resume_points for b in s.bullets
            )

        event_type, data = SSEEventBuilder.complete(
            app.id,
            latex=app.generated.resume_latex if app.generated else "",
            sections=app.generated.resume_points if app.generated else [],
            total_tokens=total_tokens,
            **extra,
        )
        await emit(event_type, data)

    # ------------------------------------------------------------------
    # Token-streaming callback factories
    # ------------------------------------------------------------------

    def _make_on_token(
        self,
        emit: Callable[[str, dict], Awaitable[None]],
    ) -> Callable[[str, str], Awaitable[None]]:
        """Build an ``on_token`` callback for ``ResumePointsGenerator.generate_all``.

        The returned callback accepts ``(section_key, token_text)`` and emits
        an SSE token event.
        """

        async def on_token(section_key: str, token_text: str) -> None:
            event_type, data = SSEEventBuilder.token(section_key, token_text)
            await emit(event_type, data)

        return on_token

    def _make_on_section_token(
        self,
        emit: Callable[[str, dict], Awaitable[None]],
        section_key: str,
    ) -> Callable:
        """Build an ``on_token`` callback for a single-section regeneration.

        The returned callback accepts a single token string and emits an SSE
        token event scoped to the given *section_key*.
        """

        async def on_token(token_text: str) -> None:
            event_type, data = SSEEventBuilder.token(section_key, token_text)
            await emit(event_type, data)

        return on_token

    def _make_on_section_complete(
        self,
        emit: Callable[[str, dict], Awaitable[None]],
    ) -> Callable[[str, list[str]], Awaitable[None]]:
        """Build an ``on_section_complete`` callback.

        The returned callback accepts ``(section_key, bullet_texts)`` and emits
        an SSE section_complete event.
        """

        async def on_section_complete(section_key: str, bullet_texts: list[str]) -> None:
            event_type, data = SSEEventBuilder.section_complete(
                section_key, len(bullet_texts),
            )
            await emit(event_type, data)

        return on_section_complete

    def _make_on_write_token(
        self,
        emit: Callable[[str, dict], Awaitable[None]],
    ) -> Callable[[str], Awaitable[None]]:
        """Build an ``on_token`` callback for ``ResumeWriter.compile_resume``.

        The ``ResumeWriter`` emits raw token strings without a section context,
        so we use a generic ``"resume_writeup"`` section key for SSE events.
        """

        async def on_token(token_text: str) -> None:
            event_type, data = SSEEventBuilder.token("resume_writeup", token_text)
            await emit(event_type, data)

        return on_token

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    async def _handle_pipeline_error(
        self,
        emit: Callable[[str, dict], Awaitable[None]],
        app: Application,
        exc: Exception,
    ) -> Application:
        """Unified error handler for pipeline failures.

        Sets the application to ``FAILED``, records the error message, persists
        the application, emits an SSE error event, and returns the application.
        """
        stage = self._infer_current_stage(app)
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.exception("Pipeline error at stage '%s': %s", stage, error_msg)

        app.generation_status = GenerationStatus.FAILED
        app.error_message = error_msg

        try:
            app = await self.history.update(app)
        except Exception as persist_exc:
            logger.error("Failed to persist failed application %s: %s", app.id, persist_exc)

        await self._emit_error(emit, stage, error_msg)
        return app

    @staticmethod
    def _infer_current_stage(app: Application) -> str:
        """Map ``GenerationStatus`` to the most recent pipeline stage name."""
        status_map = {
            GenerationStatus.PENDING: STAGE_INITIALIZING,
            GenerationStatus.MATCHING: STAGE_MATCHING_PROJECTS,
            GenerationStatus.GENERATING_POINTS: STAGE_GENERATING_POINTS,
            GenerationStatus.WRITING_RESUME: STAGE_WRITING_RESUME,
            GenerationStatus.RENDERING_LATEX: STAGE_RENDERING_LATEX,
        }
        return status_map.get(app.generation_status, STAGE_INITIALIZING)
