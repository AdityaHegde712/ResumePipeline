"""
Tests for HistoryService.
"""
import pytest
from app.services.history_service import HistoryService
from app.models.application import Application, GenerationStatus
from datetime import datetime


@pytest.mark.asyncio
async def test_create_auto_generates_id(tmp_data_dir):
    """Create should auto-generate an ID if none provided."""
    svc = HistoryService(tmp_data_dir)
    app = Application(
        id="", created_at=datetime.now(), updated_at=datetime.now(),
        company_name="TestCo", job_title="Engineer", job_description="Build",
    )
    created = await svc.create(app)
    assert created.id.startswith("app-")
    assert len(created.id) > 10


@pytest.mark.asyncio
async def test_get_returns_created_app(tmp_data_dir):
    """Get by ID should return the created application."""
    svc = HistoryService(tmp_data_dir)
    app = Application(
        id="", created_at=datetime.now(), updated_at=datetime.now(),
        company_name="TestCo", job_title="Engineer", job_description="Build",
    )
    created = await svc.create(app)
    fetched = await svc.get(created.id)
    assert fetched is not None
    assert fetched.company_name == "TestCo"
    assert fetched.job_title == "Engineer"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(tmp_data_dir):
    """Get for non-existent ID should return None."""
    svc = HistoryService(tmp_data_dir)
    result = await svc.get("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_list_all_returns_summaries(tmp_data_dir):
    """list_all() should return application summaries."""
    svc = HistoryService(tmp_data_dir)
    app1 = Application(
        id="", created_at=datetime.now(), updated_at=datetime.now(),
        company_name="Co1", job_title="T1", job_description="D1",
    )
    app2 = Application(
        id="", created_at=datetime.now(), updated_at=datetime.now(),
        company_name="Co2", job_title="T2", job_description="D2",
    )
    await svc.create(app1)
    await svc.create(app2)

    apps = await svc.list_all()
    assert len(apps) == 2


@pytest.mark.asyncio
async def test_update_modifies_record(tmp_data_dir):
    """Update should modify and persist changes."""
    svc = HistoryService(tmp_data_dir)
    app = Application(
        id="", created_at=datetime.now(), updated_at=datetime.now(),
        company_name="TestCo", job_title="Engineer", job_description="Build",
    )
    created = await svc.create(app)

    created.generation_status = GenerationStatus.COMPLETED
    await svc.update(created)

    fetched = await svc.get(created.id)
    assert fetched.generation_status == GenerationStatus.COMPLETED


@pytest.mark.asyncio
async def test_delete_removes_record(tmp_data_dir):
    """Delete should remove the application file."""
    svc = HistoryService(tmp_data_dir)
    app = Application(
        id="", created_at=datetime.now(), updated_at=datetime.now(),
        company_name="TestCo", job_title="Engineer", job_description="Build",
    )
    created = await svc.create(app)

    result = await svc.delete(created.id)
    assert result is True
    assert await svc.get(created.id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_false(tmp_data_dir):
    """Delete of non-existent ID should return False."""
    svc = HistoryService(tmp_data_dir)
    result = await svc.delete("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_count_increments_correctly(tmp_data_dir):
    """Count should reflect the number of applications."""
    svc = HistoryService(tmp_data_dir)
    assert await svc.count() == 0

    app1 = Application(
        id="", created_at=datetime.now(), updated_at=datetime.now(),
        company_name="Co1", job_title="T1", job_description="D1",
    )
    await svc.create(app1)
    assert await svc.count() == 1

    app2 = Application(
        id="", created_at=datetime.now(), updated_at=datetime.now(),
        company_name="Co2", job_title="T2", job_description="D2",
    )
    await svc.create(app2)
    assert await svc.count() == 2

    await svc.delete(app2.id)
    assert await svc.count() == 1
