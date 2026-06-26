"""
API endpoints for project listing, search, refresh, and LLM-powered relevance matching.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.generation import MatchRequest

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy singleton for the sweep-file service
# ---------------------------------------------------------------------------
_projects_service: Optional["ProjectSweepService"] = None


def get_projects_service() -> "ProjectSweepService":
    """Return the shared ProjectSweepService, initialising it on first call."""
    global _projects_service
    if _projects_service is None:
        from app.config import settings
        from app.services.project_sweep_service import ProjectSweepService

        logger.info("Initialising ProjectSweepService with path=%s", settings.sweep_file_path)
        _projects_service = ProjectSweepService(settings.sweep_file_path)
    return _projects_service


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_projects() -> dict:
    """Return all parsed projects with file staleness info."""
    try:
        service = get_projects_service()
        projects = service.get_all()
        return {
            "projects": [p.model_dump() for p in projects],
            "stale": service.is_stale(),
        }
    except Exception:
        logger.exception("Failed to list projects")
        raise HTTPException(status_code=500, detail="Failed to read project data.")


@router.get("/search")
async def search_projects(
    q: str = Query(..., min_length=1, description="Search keyword"),
) -> dict:
    """Search projects by keyword (matches name, summary, tech stack, domains)."""
    try:
        service = get_projects_service()
        results = service.search(q)
        return {
            "query": q,
            "results": [p.model_dump() for p in results],
            "count": len(results),
        }
    except Exception:
        logger.exception("Failed to search projects for query=%r", q)
        raise HTTPException(status_code=500, detail="Search failed.")


@router.get("/{project_id}")
async def get_project(project_id: str) -> dict:
    """Return a single project by its slug-style id."""
    # NOTE: This route MUST come after /search so literal paths match first.
    try:
        service = get_projects_service()
        project = service.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
        return {"project": project.model_dump()}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get project %s", project_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve project.")


@router.post("/refresh")
async def refresh_projects() -> dict:
    """Force a re-parse of the sweep file and return the updated project count."""
    try:
        service = get_projects_service()
        projects = service.refresh()
        return {
            "status": "ok",
            "projects_count": len(projects),
        }
    except Exception:
        logger.exception("Failed to refresh projects")
        raise HTTPException(status_code=500, detail="Failed to refresh project data.")


@router.post("/match")
async def match_projects(request: MatchRequest) -> dict:
    """Score all projects by relevance to a target job description using an LLM."""
    try:
        service = get_projects_service()
        projects = service.get_all()

        if not projects:
            return {"matches": []}

        from app.config import settings
        from app.services.llm_service import LLMService
        from app.services.prompt_manager import PromptManager
        from app.pipeline.matching_service import MatchingService

        llm = LLMService()
        prompts = PromptManager(settings.data_dir.parent / "app" / "templates" / "prompts")
        matcher = MatchingService(llm, prompts)

        matches = await matcher.match(
            job_title=request.job_title,
            company_name=request.company_name,
            job_description=request.job_description,
            projects=projects,
        )

        return {"matches": [m.model_dump() for m in matches]}

    except Exception:
        logger.exception("Failed to match projects")
        raise HTTPException(status_code=500, detail="Project matching failed.")
