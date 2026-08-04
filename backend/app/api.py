"""FastAPI router: application endpoints under /api (PLAN §3, D9/D10/D13)."""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

from backend.app import assembler, cover_letter_pdf, loader, llm_client, pdf
from backend.app.config import Settings
from backend.app.cover_letter_pdf import CoverLetterExportError
from backend.app.llm_client import LLMError
from backend.app.parser import parse_llm_response
from backend.app.pdf import PDFCompileError
from backend.app.storage import (
    application_dir,
    create_application_dir,
    generate_application_id,
    list_applications,
    save_cover_letter,
    save_llm_response,
    save_request_json,
    save_tex,
    update_request_json,
)

router = APIRouter(prefix="/api")


class ApplicationRequest(BaseModel):
    """POST /api/applications body: job target plus optional company blurb."""

    job_position: str
    job_description: str
    company_name: str
    company_description: str | None = None
    generate_cover_letter: bool = True


@router.post("/applications")
async def create_application(payload: ApplicationRequest, request: Request) -> JSONResponse:
    """Generate a tailored resume and persist the application files (D9).

    LLM and reconstruction failures are fatal (500 + named phase); PDF
    compile and cover-letter failures are non-fatal and surface as
    ``pdf_error`` / ``cover_letter_error`` while the other files are
    still saved.
    """
    state = request.app.state
    settings: Settings = state.settings
    application_id = generate_application_id()
    app_dir = create_application_dir(settings.applications_root, application_id)

    prompt = loader.build_prompt(
        template=state.prompt_template,
        job_position=payload.job_position,
        company_name=payload.company_name,
        job_description=payload.job_description,
        company_description=payload.company_description,
        profile=state.profile,
        sweep_text=state.sweep_text,
    )

    # Fatal phase 1: the single LLM call (D10).
    try:
        llm_text = await llm_client.generate_resume_text(prompt, settings)
    except LLMError as exc:
        return _fatal(phase="llm_generation", error=str(exc))
    save_llm_response(app_dir, llm_text)

    # Fatal phase 2: deterministic parse + LaTeX assembly (D10). Any failure
    # here means the LLM output could not be reconstructed into a resume.
    try:
        parsed = parse_llm_response(llm_text)
        tex = assembler.assemble_resume(
            parsed,
            state.profile,
            state.sweep_headings,
            state.project_links,
        )
    except Exception as exc:
        return _fatal(phase="reconstruction", error=str(exc))
    save_tex(app_dir, tex)

    # Non-fatal phase 3: PDF compile (D10) — tex still usable without a PDF.
    pdf_error: str | None = None
    try:
        await pdf.compile_resume(settings, app_dir)
    except PDFCompileError as exc:
        pdf_error = str(exc)

    # Non-fatal phase 4: cover letter (D19) — never fails the POST.
    cover_letter_status: str | None = None
    cover_letter_generated = False
    cover_letter_error: str | None = None
    if payload.generate_cover_letter:
        cover_letter_status, cover_letter_generated, cover_letter_error, _ = (
            await _cover_letter_phase(
                cover_letter_prompt_template=state.cover_letter_prompt,
                subjective_profile=state.subjective_profile,
                settings=settings,
                app_dir=app_dir,
                job_position=payload.job_position,
                company_name=payload.company_name,
                job_description=payload.job_description,
                company_description=payload.company_description,
                resume_text=llm_text,
            )
        )

    metadata = {
        "application_id": application_id,
        "job_position": payload.job_position,
        "company_name": payload.company_name,
        "company_description": payload.company_description,
        "job_description": payload.job_description,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "completed",
        "llm_generation": "OK",
        "reconstruction": "OK",
        "saved": "OK",
        "pdf_error": pdf_error,
    }
    save_request_json(app_dir, metadata)
    update_request_json(
        app_dir,
        {
            "cover_letter": cover_letter_status,
            "cover_letter_generated": cover_letter_generated,
            "cover_letter_error": cover_letter_error,
        },
    )

    return JSONResponse(
        status_code=200,
        content={
            "status": 200,
            "llm_generation": "OK",
            "reconstruction": "OK",
            "saved": "OK",
            "pdf_error": pdf_error,
            "application_id": application_id,
            "cover_letter": cover_letter_status,
            "cover_letter_generated": cover_letter_generated,
            "cover_letter_error": cover_letter_error,
        },
    )


@router.get("/applications")
def list_application_metadata(request: Request) -> list[dict]:
    """Return every application's request.json metadata, newest first."""
    return list_applications(request.app.state.settings.applications_root)


@router.get("/applications/{application_id}/llm_response")
def get_llm_response(application_id: str, request: Request) -> PlainTextResponse:
    """Serve the raw llm_response.md text verbatim."""
    app_dir = _app_dir_or_404(request.app.state.settings.applications_root, application_id)
    return PlainTextResponse(_llm_response_or_404(app_dir))


@router.get("/applications/{application_id}/tex")
def get_tex(application_id: str, request: Request) -> FileResponse:
    """Download resume.tex as an attachment (D13)."""
    app_dir = _app_dir_or_404(request.app.state.settings.applications_root, application_id)
    tex_file = app_dir / "resume.tex"
    if not tex_file.is_file():
        raise HTTPException(status_code=404, detail="resume.tex missing")
    return FileResponse(
        tex_file,
        media_type="text/plain",
        filename=f"resume-{application_id}.tex",
    )


@router.get("/applications/{application_id}/pdf")
def get_pdf(application_id: str, request: Request) -> FileResponse:
    """Download resume.pdf as an attachment; 404 when compile failed (D13)."""
    app_dir = _app_dir_or_404(request.app.state.settings.applications_root, application_id)
    pdf_file = app_dir / "resume.pdf"
    missing_or_empty = not pdf_file.is_file() or pdf_file.stat().st_size == 0
    if missing_or_empty:
        raise HTTPException(status_code=404, detail="resume.pdf missing")
    return FileResponse(
        pdf_file,
        media_type="application/pdf",
        filename=f"resume-{application_id}.pdf",
    )


@router.post("/applications/{application_id}/cover_letter")
async def generate_cover_letter_late(application_id: str, request: Request) -> JSONResponse:
    """Generate a cover letter for an existing application (D20).

    Rebuilds the prompt from the stored ``request.json`` job fields plus
    the saved ``llm_response.md`` so late generation never needs a new
    request body. The LLM failure is non-fatal: the response stays 200
    with an ``ERROR`` flag.
    """
    state = request.app.state
    settings: Settings = state.settings
    app_dir = _app_dir_or_404(state.settings.applications_root, application_id)
    if (app_dir / "cover_letter.md").is_file():
        raise HTTPException(status_code=409, detail="cover_letter.md already exists")
    job_fields = _cover_letter_job_fields(app_dir)
    job_position, company_name, job_description, company_description = job_fields
    resume_text = _llm_response_or_404(app_dir)

    cover_letter_status, _, cover_letter_error, letter_text = await _cover_letter_phase(
        cover_letter_prompt_template=state.cover_letter_prompt,
        subjective_profile=state.subjective_profile,
        settings=settings,
        app_dir=app_dir,
        job_position=job_position,
        company_name=company_name,
        job_description=job_description,
        company_description=company_description,
        resume_text=resume_text,
    )
    update_request_json(
        app_dir,
        {
            "cover_letter": cover_letter_status,
            "cover_letter_generated": cover_letter_status == "OK",
            "cover_letter_error": cover_letter_error,
        },
    )
    if cover_letter_status != "OK":
        return JSONResponse(
            status_code=200,
            content={
                "cover_letter": "ERROR",
                "cover_letter_generated": False,
                "cover_letter_error": cover_letter_error,
            },
        )
    return JSONResponse(
        status_code=200,
        content={
            "cover_letter": "OK",
            "cover_letter_generated": True,
            "cover_letter_text": letter_text,
        },
    )


@router.get("/applications/{application_id}/cover_letter")
def get_cover_letter(application_id: str, request: Request) -> PlainTextResponse:
    """Serve the saved cover_letter.md text verbatim."""
    app_dir = _app_dir_or_404(request.app.state.settings.applications_root, application_id)
    letter_file = app_dir / "cover_letter.md"
    if not letter_file.is_file():
        raise HTTPException(status_code=404, detail="cover_letter.md missing")
    return PlainTextResponse(letter_file.read_text(encoding="utf-8"))


@router.get("/applications/{application_id}/cover_letter/pdf")
async def get_cover_letter_pdf(application_id: str, request: Request) -> FileResponse:
    """Lazily export and download cover_letter.pdf (D21)."""
    state = request.app.state
    app_dir = _app_dir_or_404(state.settings.applications_root, application_id)
    if not (app_dir / "cover_letter.md").is_file():
        raise HTTPException(status_code=404, detail="cover_letter.md missing")
    try:
        pdf_file = await cover_letter_pdf.export_cover_letter_pdf(app_dir, state.settings)
    except CoverLetterExportError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return FileResponse(
        pdf_file,
        media_type="application/pdf",
        filename=f"cover_letter-{application_id}.pdf",
    )


def _app_dir_or_404(root: Path, application_id: str) -> Path:
    """Resolve an application dir or raise the locked 404 response."""
    try:
        return application_dir(root, application_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Application not found") from exc


def _fatal(phase: str, error: str) -> JSONResponse:
    """Build the locked 500 body with a top-level named phase (D10)."""
    return JSONResponse(status_code=500, content={"phase": phase, "error": error})


async def _cover_letter_phase(
    *,
    cover_letter_prompt_template: str,
    subjective_profile: str,
    settings: Settings,
    app_dir: Path,
    job_position: str,
    company_name: str,
    job_description: str,
    company_description: str | None,
    resume_text: str,
) -> tuple[str, bool, str | None, str]:
    """Run the non-fatal cover-letter phase: prompt -> LLM -> save.

    Returns the ``(status, generated, error, letter_text)`` tuple;
    ``letter_text`` is ``""`` when the LLM call failed. Never raises
    ``LLMError`` so the enclosing POST can always complete.
    """
    try:
        prompt = loader.build_cover_letter_prompt(
            template=cover_letter_prompt_template,
            job_position=job_position,
            company_name=company_name,
            job_description=job_description,
            company_description=company_description,
            subjective_profile=subjective_profile,
            llm_resume_response=resume_text,
        )
        letter_text = await llm_client.generate_cover_letter_text(prompt, settings)
    except LLMError as exc:
        return "ERROR", False, str(exc), ""
    save_cover_letter(app_dir, letter_text)
    return "OK", True, None, letter_text


def _cover_letter_job_fields(app_dir: Path) -> tuple[str, str, str, str | None]:
    """Read the stored job fields from request.json for late generation."""
    request_file = app_dir / "request.json"
    if not request_file.is_file():
        raise HTTPException(status_code=404, detail="request.json missing")
    metadata = json.loads(request_file.read_text(encoding="utf-8"))
    return (
        str(metadata.get("job_position", "")),
        str(metadata.get("company_name", "")),
        str(metadata.get("job_description", "")),
        metadata.get("company_description"),
    )


def _llm_response_or_404(app_dir: Path) -> str:
    """Read llm_response.md or raise the locked 404 response."""
    response_file = app_dir / "llm_response.md"
    if not response_file.is_file():
        raise HTTPException(status_code=404, detail="llm_response.md missing")
    return response_file.read_text(encoding="utf-8")
