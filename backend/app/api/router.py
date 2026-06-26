"""
Aggregate router — mounts all sub-routers under a single APIRouter.

Usage:
    from app.api.router import api_router
    app.include_router(api_router, prefix="/api")
"""

from fastapi import APIRouter
from app.api import profile, projects, resume, history, config

api_router = APIRouter()
api_router.include_router(profile.router, prefix="/profile", tags=["Profile"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(resume.router, prefix="/generate", tags=["Generation"])
api_router.include_router(history.router, prefix="/applications", tags=["History"])
api_router.include_router(config.router, prefix="/config", tags=["Config"])


@api_router.get("/health")
async def health_check():
    """Health-check endpoint — returns service status and version."""
    return {"status": "ok", "version": "1.0.0"}
