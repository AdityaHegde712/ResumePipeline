"""
History CRUD endpoints — list, retrieve, and delete application records.

All application data is persisted as individual JSON files on disk via the
``HistoryService``.  No database is required for v1.0.
"""

from fastapi import APIRouter, HTTPException
from app.models.application import Application
from app.services.history_service import HistoryService

router = APIRouter()

# Module-level singleton so the service is lazily initialised once.
_history_service: HistoryService | None = None


def get_history_service() -> HistoryService:
    """Return the shared ``HistoryService`` instance, creating it if needed.

    The service reads/writes application JSON files under
    ``settings.data_dir / "applications"``.
    """
    global _history_service
    if _history_service is None:
        from app.config import settings

        _history_service = HistoryService(settings.data_dir)
    return _history_service


@router.get("")
async def list_applications() -> dict:
    """List all applications (summary view).

    Returns a lightweight list of application summaries (without the full
    ``generated`` content payload) sorted by creation date descending.
    """
    service = get_history_service()
    apps = await service.list_all()
    return {"applications": apps}


@router.get("/{application_id}")
async def get_application(application_id: str) -> Application:
    """Retrieve the full details of a single application by its ID.

    Args:
        application_id: The application identifier
            (e.g. ``"app-20260626-001"``).

    Returns:
        The complete ``Application`` model including generated content.

    Raises:
        HTTPException 404: If no application with the given ID exists.
    """
    service = get_history_service()
    app = await service.get(application_id)
    if app is None:
        raise HTTPException(
            status_code=404,
            detail=f"Application '{application_id}' not found",
        )
    return app


@router.delete("/{application_id}")
async def delete_application(application_id: str) -> dict:
    """Delete an application record and its JSON file from disk.

    Args:
        application_id: The application identifier to remove.

    Returns:
        A confirmation dictionary with ``status`` and ``id`` keys.

    Raises:
        HTTPException 404: If no application with the given ID exists.
    """
    service = get_history_service()
    deleted = await service.delete(application_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Application '{application_id}' not found",
        )
    return {"status": "deleted", "id": application_id}
