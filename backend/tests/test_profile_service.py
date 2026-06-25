"""
Tests for ProfileService.
"""
import pytest
from app.services.profile_service import ProfileService, ProfileValidationError
from app.models.profile import UserProfile


@pytest.mark.asyncio
async def test_load_default_when_no_files(tmp_data_dir):
    """ProfileService.load() should return defaults when no files exist."""
    svc = ProfileService(tmp_data_dir)
    profile = await svc.load()
    assert profile.name == "Aditya Hegde"
    assert profile.email == ""
    assert profile.subjective_profile_content == ""


@pytest.mark.asyncio
async def test_save_load_round_trip(tmp_data_dir):
    """Save then load should preserve all fields."""
    svc = ProfileService(tmp_data_dir)
    profile = UserProfile(name="Test User", email="test@example.com")
    profile.links.linkedin = "https://linkedin.com/in/test"
    profile.skills.languages = ["Python", "TypeScript"]
    profile.subjective_profile_content = "## Narrative"
    await svc.save(profile)

    loaded = await svc.load()
    assert loaded.name == "Test User"
    assert loaded.email == "test@example.com"
    assert loaded.links.linkedin == "https://linkedin.com/in/test"
    assert loaded.skills.languages == ["Python", "TypeScript"]
    assert loaded.subjective_profile_content == "## Narrative"


@pytest.mark.asyncio
async def test_save_writes_subjective_content(tmp_data_dir):
    """Save should write subjective content to the markdown file."""
    svc = ProfileService(tmp_data_dir)
    profile = UserProfile(name="Test", email="t@t.com")
    profile.subjective_profile_content = "## Custom Narrative\n\nTest content."
    await svc.save(profile)

    assert (tmp_data_dir / "subjective_profile.md").exists()
    content = (tmp_data_dir / "subjective_profile.md").read_text()
    assert "## Custom Narrative" in content


@pytest.mark.asyncio
async def test_save_creates_data_dir(tmp_data_dir):
    """Save should create the data directory if it doesn't exist."""
    nested = tmp_data_dir / "nested" / "data"
    svc = ProfileService(nested)
    profile = UserProfile(name="Test", email="t@t.com")
    await svc.save(profile)
    assert nested.exists()
    assert (nested / "profile.yaml").exists()


@pytest.mark.asyncio
async def test_exists_returns_false_when_missing(tmp_data_dir):
    """exists() should return False when profile.yaml doesn't exist."""
    svc = ProfileService(tmp_data_dir)
    assert await svc.exists() is False


@pytest.mark.asyncio
async def test_exists_returns_true_when_valid(tmp_data_dir):
    """exists() should return True when profile.yaml exists with name."""
    svc = ProfileService(tmp_data_dir)
    profile = UserProfile(name="Test User", email="t@t.com")
    await svc.save(profile)
    assert await svc.exists() is True


@pytest.mark.asyncio
async def test_invalid_yaml_raises_error(tmp_data_dir):
    """Invalid YAML should raise ProfileValidationError."""
    f = tmp_data_dir / "profile.yaml"
    f.write_text("invalid: [yaml: broken")
    svc = ProfileService(tmp_data_dir)
    with pytest.raises(ProfileValidationError):
        await svc.load()


@pytest.mark.asyncio
async def test_load_subjective_missing(tmp_data_dir):
    """load_subjective() should return empty string when file missing."""
    svc = ProfileService(tmp_data_dir)
    content = await svc.load_subjective()
    assert content == ""


@pytest.mark.asyncio
async def test_partial_profile_fills_defaults(tmp_data_dir):
    """Minimal profile should fill missing fields with defaults."""
    f = tmp_data_dir / "profile.yaml"
    f.write_text("name: Minimal User\nemail: m@u.com")
    svc = ProfileService(tmp_data_dir)
    profile = await svc.load()
    assert profile.name == "Minimal User"
    assert profile.email == "m@u.com"
    assert profile.education == []
    assert profile.skills.languages == []
