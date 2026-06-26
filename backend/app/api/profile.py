"""
Profile API endpoints — CRUD operations for the user profile.

Uses a lightweight singleton pattern for dependency injection of the
ProfileService, which manages the two-profile model:
  1. profile.yaml (structured YAML for objective data)
  2. subjective_profile.md (free-form narrative for cover letters)
"""

from fastapi import APIRouter, HTTPException
from app.services.profile_service import ProfileService, ProfileValidationError
from app.models.profile import UserProfile

router = APIRouter()

# ---------------------------------------------------------------------------
# Singleton service provider (simple DI without a full framework)
# ---------------------------------------------------------------------------
_profile_service: ProfileService | None = None


def get_profile_service() -> ProfileService:
    """Return (or lazily initialise) the singleton ProfileService instance."""
    global _profile_service
    if _profile_service is None:
        from app.config import settings

        _profile_service = ProfileService(settings.data_dir)
    return _profile_service


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def get_profile() -> UserProfile:
    """Get the current user profile (objective + subjective content)."""
    service = get_profile_service()
    try:
        profile = await service.load()
        return profile
    except ProfileValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.put("")
async def update_profile(profile: UserProfile) -> UserProfile:
    """Update the user profile (saves both YAML and subjective markdown)."""
    service = get_profile_service()
    saved = await service.save(profile)
    return saved


@router.get("/exists")
async def profile_exists() -> dict:
    """Check whether a profile has been created (name field is populated)."""
    service = get_profile_service()
    exists = await service.exists()
    return {"exists": exists}
