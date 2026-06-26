"""
API integration tests using FastAPI TestClient.

All external services (file I/O, LLM, subprocess) are mocked to keep
tests fast, deterministic, and environment-independent.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.application import Application, GeneratedContent, GenerationStatus
from app.models.generation import LLMConfig
from app.models.profile import UserProfile
from app.models.project import ProjectEntry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """Create a fresh FastAPI app for each test."""
    return create_app()


@pytest.fixture
def client(app):
    """TestClient wrapping the fresh app."""
    return TestClient(app)


@pytest.fixture
def sample_profile() -> UserProfile:
    return UserProfile(
        name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="Test City",
        links={"linkedin": "https://linkedin.com/in/test", "github": "https://github.com/test"},
    )


@pytest.fixture
def sample_projects() -> list[ProjectEntry]:
    return [
        ProjectEntry(
            id="test-project",
            name="Test Project",
            type="Web App",
            tech_stack=["Python", "FastAPI"],
            summary="A test project",
            domains=["Web Development"],
        ),
    ]


@pytest.fixture
def sample_application() -> Application:
    now = datetime.now(timezone.utc)
    return Application(
        id="app-20260625-001",
        created_at=now,
        updated_at=now,
        company_name="Test Corp",
        job_title="Software Engineer",
        job_description="A great job",
        generation_status=GenerationStatus.COMPLETED,
        generated=GeneratedContent(
            resume_points=[],
            resume_latex="\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}",
            model_used="gemini-2.5-pro",
        ),
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class TestProfile:
    def test_get_profile(self, client, sample_profile):
        mock_service = MagicMock()
        mock_service.load = AsyncMock(return_value=sample_profile)

        with patch("app.api.profile.get_profile_service", return_value=mock_service):
            resp = client.get("/api/profile")

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test User"
        assert data["email"] == "test@example.com"

    def test_get_profile_validation_error(self, client):
        mock_service = MagicMock()
        from app.services.profile_service import ProfileValidationError
        mock_service.load = AsyncMock(side_effect=ProfileValidationError("Bad YAML"))

        with patch("app.api.profile.get_profile_service", return_value=mock_service):
            resp = client.get("/api/profile")

        assert resp.status_code == 422
        assert "Bad YAML" in resp.text

    def test_update_profile(self, client, sample_profile):
        mock_service = MagicMock()
        mock_service.save = AsyncMock(return_value=sample_profile)

        with patch("app.api.profile.get_profile_service", return_value=mock_service):
            resp = client.put("/api/profile", json=sample_profile.model_dump())

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test User"

    def test_profile_exists_true(self, client):
        mock_service = MagicMock()
        mock_service.exists = AsyncMock(return_value=True)

        with patch("app.api.profile.get_profile_service", return_value=mock_service):
            resp = client.get("/api/profile/exists")

        assert resp.status_code == 200
        assert resp.json() == {"exists": True}

    def test_profile_exists_false(self, client):
        mock_service = MagicMock()
        mock_service.exists = AsyncMock(return_value=False)

        with patch("app.api.profile.get_profile_service", return_value=mock_service):
            resp = client.get("/api/profile/exists")

        assert resp.status_code == 200
        assert resp.json() == {"exists": False}


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class TestProjects:
    def test_list_projects(self, client, sample_projects):
        mock_service = MagicMock()
        mock_service.get_all.return_value = sample_projects
        mock_service.is_stale.return_value = False

        with patch("app.api.projects.get_projects_service", return_value=mock_service):
            resp = client.get("/api/projects")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "Test Project"
        assert data["stale"] is False

    def test_list_projects_empty(self, client):
        mock_service = MagicMock()
        mock_service.get_all.return_value = []
        mock_service.is_stale.return_value = False

        with patch("app.api.projects.get_projects_service", return_value=mock_service):
            resp = client.get("/api/projects")

        assert resp.status_code == 200
        assert resp.json()["projects"] == []

    def test_get_project_found(self, client, sample_projects):
        mock_service = MagicMock()
        mock_service.get_by_id.return_value = sample_projects[0]

        with patch("app.api.projects.get_projects_service", return_value=mock_service):
            resp = client.get("/api/projects/test-project")

        assert resp.status_code == 200
        assert resp.json()["project"]["name"] == "Test Project"

    def test_get_project_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get_by_id.return_value = None

        with patch("app.api.projects.get_projects_service", return_value=mock_service):
            resp = client.get("/api/projects/nonexistent")

        assert resp.status_code == 404

    def test_search_projects(self, client, sample_projects):
        mock_service = MagicMock()
        mock_service.search.return_value = sample_projects

        with patch("app.api.projects.get_projects_service", return_value=mock_service):
            resp = client.get("/api/projects/search?q=test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "test"
        assert data["count"] == 1

    def test_refresh_projects(self, client, sample_projects):
        mock_service = MagicMock()
        mock_service.refresh.return_value = sample_projects

        with patch("app.api.projects.get_projects_service", return_value=mock_service):
            resp = client.post("/api/projects/refresh")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["projects_count"] == 1

    def test_match_projects(self, client, sample_projects):
        """Test the match endpoint with mocked LLM."""
        mock_project_service = MagicMock()
        mock_project_service.get_all.return_value = sample_projects

        mock_matcher = MagicMock()
        mock_matcher.match = AsyncMock(return_value=[])

        with (
            patch("app.api.projects.get_projects_service", return_value=mock_project_service),
            patch("app.pipeline.matching_service.MatchingService", return_value=mock_matcher),
        ):
            resp = client.post(
                "/api/projects/match",
                json={
                    "job_title": "SWE",
                    "company_name": "Test",
                    "job_description": "Python dev",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["matches"] == []


# ---------------------------------------------------------------------------
# Applications / History
# ---------------------------------------------------------------------------


class TestHistory:
    def test_list_applications(self, client, sample_application):
        mock_service = MagicMock()
        mock_service.list_all = AsyncMock(return_value=[sample_application])

        with patch("app.api.history.get_history_service", return_value=mock_service):
            resp = client.get("/api/applications")

        assert resp.status_code == 200
        assert len(resp.json()["applications"]) == 1

    def test_get_application_found(self, client, sample_application):
        mock_service = MagicMock()
        mock_service.get = AsyncMock(return_value=sample_application)

        with patch("app.api.history.get_history_service", return_value=mock_service):
            resp = client.get("/api/applications/app-20260625-001")

        assert resp.status_code == 200
        assert resp.json()["id"] == "app-20260625-001"

    def test_get_application_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get = AsyncMock(return_value=None)

        with patch("app.api.history.get_history_service", return_value=mock_service):
            resp = client.get("/api/applications/nonexistent")

        assert resp.status_code == 404

    def test_delete_application(self, client):
        mock_service = MagicMock()
        mock_service.delete = AsyncMock(return_value=True)

        with patch("app.api.history.get_history_service", return_value=mock_service):
            resp = client.delete("/api/applications/app-001")

        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_delete_application_not_found(self, client):
        mock_service = MagicMock()
        mock_service.delete = AsyncMock(return_value=False)

        with patch("app.api.history.get_history_service", return_value=mock_service):
            resp = client.delete("/api/applications/nonexistent")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_get_llm_config(self, client):
        resp = client.get("/api/config/llm")
        assert resp.status_code == 200
        data = resp.json()
        assert "default_model" in data
        assert "default_provider" in data

    def test_update_llm_config(self, client):
        new_config = {
            "default_provider": "openai",
            "default_model": "gpt-4",
            "tasks": {},
        }
        resp = client.put("/api/config/llm", json=new_config)
        assert resp.status_code == 200
        assert resp.json()["default_model"] == "gpt-4"

    def test_pdf_available(self, client):
        resp = client.get("/api/config/pdf-available")
        assert resp.status_code == 200
        assert "available" in resp.json()


# ---------------------------------------------------------------------------
# Generation (SSE + tex/pdf export)
# ---------------------------------------------------------------------------


class TestGeneration:
    def test_generate_points_sse(self, client, sample_application):
        """Test SSE streaming returns events."""
        async def mock_run_points_only(_request, emit):
            await emit("stage", {"stage": "initializing", "status": "start"})
            await emit("stage", {"stage": "initializing", "status": "complete"})
            await emit("complete", {"application_id": "app-001"})
            return sample_application

        mock_orch = MagicMock()
        mock_orch.run_points_only = mock_run_points_only

        with patch("app.api.resume.get_orchestrator", return_value=mock_orch):
            resp = client.post(
                "/api/generate/points",
                json={
                    "application_id": "app-001",
                    "job_title": "SWE",
                    "company_name": "Test Corp",
                    "job_description": "Python developer",
                    "selected_project_ids": ["test-project"],
                },
                headers={"Accept": "text/event-stream"},
            )

        # Should get SSE response
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        # Should contain SSE events
        assert "event: stage" in resp.text
        assert "event: complete" in resp.text

    def test_export_tex_found(self, client, sample_application):
        """Download .tex for completed application."""
        mock_history = MagicMock()
        mock_history.get = AsyncMock(return_value=sample_application)

        with patch("app.services.history_service.HistoryService", return_value=mock_history):
            resp = client.get("/api/generate/app-20260625-001/tex")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"
        assert "documentclass" in resp.text

    def test_export_tex_not_found(self, client):
        """Download .tex for missing application."""
        mock_history = MagicMock()
        mock_history.get = AsyncMock(return_value=None)

        with patch("app.services.history_service.HistoryService", return_value=mock_history):
            resp = client.get("/api/generate/nonexistent/tex")

        assert resp.status_code == 404

    def test_export_tex_no_latex(self, client, sample_application):
        """Download .tex when no generated content exists."""
        app_no_latex = sample_application
        app_no_latex.generated = GeneratedContent(resume_points=[], resume_latex=None)

        mock_history = MagicMock()
        mock_history.get = AsyncMock(return_value=app_no_latex)

        with patch("app.services.history_service.HistoryService", return_value=mock_history):
            resp = client.get("/api/generate/app-001/tex")

        assert resp.status_code == 404

    def test_export_pdf_not_found(self, client):
        """PDF export for missing application."""
        mock_history = MagicMock()
        mock_history.get = AsyncMock(return_value=None)

        with patch("app.services.history_service.HistoryService", return_value=mock_history):
            resp = client.get("/api/generate/nonexistent/pdf")

        assert resp.status_code == 404

    def test_export_pdf_no_latex(self, client, sample_application):
        """PDF export when no generated content."""
        app_no_latex = sample_application
        app_no_latex.generated = GeneratedContent(resume_points=[], resume_latex=None)

        mock_history = MagicMock()
        mock_history.get = AsyncMock(return_value=app_no_latex)

        with patch("app.services.history_service.HistoryService", return_value=mock_history):
            resp = client.get("/api/generate/app-001/pdf")

        assert resp.status_code == 404

