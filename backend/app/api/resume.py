"""
API endpoints for resume generation via SSE streaming + PDF/tex export.

Provides:
- POST /points       — SSE-streaming bullet point generation
- POST /resume       — SSE-streaming full resume (write-up + LaTeX)
- POST /regenerate   — SSE-streaming single-section regeneration
- GET  /{id}/pdf     — download compiled PDF (requires MiKTeX)
- GET  /{id}/tex     — download raw .tex source
"""

from __future__ import annotations

import asyncio
import io
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.models.generation import GenerationRequest, PointsRegenerateRequest, ResumeExportRequest

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy singleton for the orchestrator (wires all services, created once)
# ---------------------------------------------------------------------------
_orchestrator: Optional["Orchestrator"] = None


def get_orchestrator() -> "Orchestrator":
    """Return the shared Orchestrator, initialising it on first call."""
    global _orchestrator
    if _orchestrator is None:
        from app.config import settings
        from app.services.profile_service import ProfileService
        from app.services.project_sweep_service import ProjectSweepService
        from app.services.history_service import HistoryService
        from app.services.llm_service import LLMService
        from app.services.prompt_manager import PromptManager
        from app.api.config import get_llm_config
        from app.pipeline.matching_service import MatchingService
        from app.pipeline.keyword_analysis_service import KeywordAnalysisService
        from app.pipeline.resume_points_generator import ResumePointsGenerator
        from app.pipeline.resume_writer import ResumeWriter
        from app.pipeline.latex_renderer import LaTeXRenderer
        from app.pipeline.orchestrator import Orchestrator

        logger.info("Initialising Orchestrator with all services")

        profile_service = ProfileService(settings.data_dir)
        project_service = ProjectSweepService(settings.sweep_file_path)
        history_service = HistoryService(settings.data_dir / "applications")
        llm_service = LLMService(config=get_llm_config())
        prompt_manager = PromptManager(Path("./app/templates/prompts"), settings)

        _orchestrator = Orchestrator(
            profile_service=profile_service,
            project_service=project_service,
            history_service=history_service,
            llm_service=llm_service,
            prompt_manager=prompt_manager,
            matching_service=MatchingService(llm_service, prompt_manager),
            keyword_service=KeywordAnalysisService(llm_service, prompt_manager),
            points_generator=ResumePointsGenerator(llm_service, prompt_manager),
            resume_writer=ResumeWriter(llm_service, prompt_manager),
            latex_renderer=LaTeXRenderer(settings.latex_template_path),
        )
    return _orchestrator


# ---------------------------------------------------------------------------
# Internal: SSE event generator helper
# ---------------------------------------------------------------------------


async def _sse_event_generator(
    run_coro,
) -> str:
    """Run an orchestrator method and yield SSE-formatted events.

    Args:
        run_coro: Coroutine that takes an ``emit`` callback and returns an Application.

    Yields:
        SSE-formatted event strings.
    """
    from app.utils.sse import format_sse_event

    queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

    async def emit(event_type: str, data: dict) -> None:
        await queue.put((event_type, data))

    task = asyncio.create_task(run_coro(emit))

    try:
        while True:
            event_type, data = await queue.get()
            yield format_sse_event(event_type, data)
            if event_type in ("complete", "error"):
                break
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/points")
async def generate_points(request: GenerationRequest):
    """SSE-streaming endpoint for bullet point generation (stops after points)."""
    orchestrator = get_orchestrator()

    async def run(emit):
        return await orchestrator.run_points_only(request, emit)

    return StreamingResponse(
        _sse_event_generator(run),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/resume")
async def generate_resume(request: ResumeExportRequest):
    """SSE-streaming endpoint for full resume + .tex generation.

    Requires an existing application with generated points.
    """
    orchestrator = get_orchestrator()

    async def run(emit):
        return await orchestrator.run_resume_only(request.application_id, emit)

    return StreamingResponse(
        _sse_event_generator(run),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/regenerate-section")
async def regenerate_section(request: PointsRegenerateRequest):
    """Regenerate a single section's bullet points via SSE streaming."""
    orchestrator = get_orchestrator()

    async def run(emit):
        return await orchestrator.regenerate_section(
            request.application_id,
            request.section_key,
            emit,
            request.custom_instructions or "",
        )

    return StreamingResponse(
        _sse_event_generator(run),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{application_id}/tex")
async def export_tex(application_id: str):
    """Download the raw .tex file for a completed application."""
    from app.services.history_service import HistoryService
    from app.config import settings

    history = HistoryService(settings.data_dir / "applications")
    app_record = await history.get(application_id)

    if app_record is None:
        raise HTTPException(status_code=404, detail=f"Application '{application_id}' not found.")

    latex = app_record.generated.resume_latex if app_record.generated else None
    if not latex:
        raise HTTPException(
            status_code=404,
            detail="No generated resume found for this application. Run generation first.",
        )

    return PlainTextResponse(
        latex,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="resume_{application_id}.tex"'
        },
    )


@router.get("/{application_id}/pdf")
async def export_pdf(application_id: str):
    """Generate and download PDF version of the resume.

    Requires MiKTeX (pdflatex) to be installed and PDFLATEX_PATH configured.
    Returns 501 if compiler is unavailable, 404 if no generated content.
    """
    from app.config import settings
    from app.services.history_service import HistoryService
    from app.pipeline.pdf_compiler import PDFCompiler

    history = HistoryService(settings.data_dir / "applications")
    app_record = await history.get(application_id)

    if app_record is None:
        raise HTTPException(status_code=404, detail=f"Application '{application_id}' not found.")

    latex = app_record.generated.resume_latex if app_record.generated else None
    if not latex:
        raise HTTPException(
            status_code=404,
            detail="No generated resume found for this application. Run generation first.",
        )

    compiler = PDFCompiler(
        settings.pdflatex_path,
        settings.data_dir / "temp_pdf",
    )

    if not compiler.is_available():
        raise HTTPException(
            status_code=501,
            detail="PDF compilation not available. Install MiKTeX and set PDFLATEX_PATH.",
        )

    try:
        result = await compiler.compile(
            latex,
            filename=f"resume_{application_id}",
        )
    except Exception as e:
        logger.exception("PDF compilation failed for %s", application_id)
        raise HTTPException(status_code=500, detail=f"PDF compilation error: {e}")

    if not result.success:
        errors = "; ".join(result.errors) if result.errors else "Unknown compilation error"
        raise HTTPException(status_code=500, detail=f"PDF compilation failed: {errors}")

    return StreamingResponse(
        io.BytesIO(result.pdf_bytes or b""),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="resume_{application_id}.pdf"'
        },
    )
