"""FastAPI router: application endpoints under /api (PLAN §3, D9/D10/D13)."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

from backend.app import assembler, loader, llm_client, pdf
from backend.app.config import Settings
from backend.app.llm_client import LLMError
from backend.app.parser import parse_llm_response
from backend.app.pdf import PDFCompileError
from backend.app.storage import (
    application_dir,
    create_application_dir,
    generate_application_id,
    list_applications,
    save_llm_response,
    save_request_json,
    save_tex,
)

router = APIRouter(prefix="/api")


class ApplicationRequest(BaseModel):
    """POST /api/applications body: job target plus optional company blurb."""

    job_position: str
    job_description: str
    company_name: str
    company_description: str | None = None


@router.post("/applications")
async def create_application(payload: ApplicationRequest, request: Request) -> JSONResponse:
    """Generate a tailored resume and persist all four app files (D9).

    LLM and reconstruction failures are fatal (500 + named phase); PDF
    compile failure is non-fatal and surfaces as ``pdf_error`` while the
    tex/llm_response/request.json files are still saved.
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

    return JSONResponse(
        status_code=200,
        content={
            "status": 200,
            "llm_generation": "OK",
            "reconstruction": "OK",
            "saved": "OK",
            "pdf_error": pdf_error,
            "application_id": application_id,
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
    response_file = app_dir / "llm_response.md"
    if not response_file.is_file():
        raise HTTPException(status_code=404, detail="llm_response.md missing")
    return PlainTextResponse(response_file.read_text(encoding="utf-8"))


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


def _app_dir_or_404(root: Path, application_id: str) -> Path:
    """Resolve an application dir or raise the locked 404 response."""
    try:
        return application_dir(root, application_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Application not found") from exc


def _fatal(phase: str, error: str) -> JSONResponse:
    """Build the locked 500 body with a top-level named phase (D10)."""
    return JSONResponse(status_code=500, content={"phase": phase, "error": error})
