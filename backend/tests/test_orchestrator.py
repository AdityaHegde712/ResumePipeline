"""
Tests for Orchestrator error formatting and end-to-end pipeline wiring.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.application import Application, GenerationStatus, SectionPoints, BulletPoint
from app.models.generation import GenerationRequest, MatchResult
from app.models.profile import UserProfile
from app.pipeline.orchestrator import Orchestrator
from app.services.llm_service import (
    LLMConnectionError,
    LLMAuthError,
    LLMRateLimitError,
    LLMParseError,
)


@pytest.fixture
def orchestrator():
    """Orchestrator instance with all dependencies mocked."""
    return Orchestrator(
        profile_service=MagicMock(),
        project_service=MagicMock(),
        history_service=MagicMock(),
        llm_service=MagicMock(),
        prompt_manager=MagicMock(),
        matching_service=MagicMock(),
        keyword_service=MagicMock(),
        points_generator=MagicMock(),
        resume_writer=MagicMock(),
        latex_renderer=MagicMock(),
    )


class TestOrchestratorErrorFormatting:
    """Tests for _format_user_error static method."""

    def test_format_user_error_rate_limit(self, orchestrator):
        """Rate limit errors should mention quota exhaustion."""
        msg = orchestrator._format_user_error(LLMRateLimitError("test"))
        assert "quota exhausted" in msg or "high demand" in msg

    def test_format_user_error_auth(self, orchestrator):
        """Auth errors should mention API key."""
        msg = orchestrator._format_user_error(LLMAuthError("test"))
        assert "API key" in msg

    def test_format_user_error_connection(self, orchestrator):
        """Connection errors should mention network."""
        msg = orchestrator._format_user_error(LLMConnectionError("test"))
        assert "network connection" in msg

    def test_format_user_error_parse(self, orchestrator):
        """Parse errors should mention unexpected response."""
        msg = orchestrator._format_user_error(LLMParseError("test"))
        assert "unexpected response" in msg

    def test_format_user_error_generic(self, orchestrator):
        """Generic errors should fall back to unexpected error message."""
        msg = orchestrator._format_user_error(Exception("something else"))
        assert "unexpected error" in msg


class TestRunPointsOnlyEndToEnd:
    """Regression coverage for a bug found via live reproduction: every
    run_* method's final _emit_complete(emit, app, sections=...) call passed
    'sections' both explicitly and via app.generated.resume_points, causing
    SSEEventBuilder.complete() to raise 'got multiple values for keyword
    argument sections' right as the pipeline finished -- on every single
    generation request. These tests exercise the full method with mocks so a
    regression surfaces as a raised exception / FAILED status, not silence."""

    @pytest.fixture
    def wired_orchestrator(self):
        history = MagicMock()
        history.create = AsyncMock(side_effect=lambda app: app)
        history.update = AsyncMock(side_effect=lambda app: app)

        project_service = MagicMock()
        project_service.get_all.return_value = []

        matching_service = MagicMock()
        matching_service.match = AsyncMock(
            return_value=[
                MatchResult(project_id="p1", project_name="Proj One", relevance_score=0.9, reasoning="fit")
            ]
        )

        keyword_service = MagicMock()
        keyword_service.analyze = AsyncMock(return_value={"required_skills": ["Python"]})
        keyword_service.extract_keywords_text = MagicMock(return_value="required: Python")

        points_generator = MagicMock()
        section = SectionPoints(
            section_key="project:p1",
            section_title="Proj One",
            bullets=[BulletPoint(id="b1", section="project:p1", text="Did a thing", order=0)],
        )
        points_generator.generate_all = AsyncMock(return_value=[section])

        profile_service = MagicMock()
        profile_service.load = AsyncMock(return_value=UserProfile())

        llm_service = MagicMock()
        llm_service.get_model_for_task.return_value = "gemini/gemini-3-flash-preview"

        return Orchestrator(
            profile_service=profile_service,
            project_service=project_service,
            history_service=history,
            llm_service=llm_service,
            prompt_manager=MagicMock(),
            matching_service=matching_service,
            keyword_service=keyword_service,
            points_generator=points_generator,
            resume_writer=MagicMock(),
            latex_renderer=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_run_points_only_completes_without_kwarg_collision(self, wired_orchestrator):
        events = []

        async def emit(event_type, data):
            events.append((event_type, data))

        request = GenerationRequest(
            application_id="",
            job_title="ML Engineer",
            company_name="TestCo",
            job_description="Build ML systems",
            selected_project_ids=[],
        )

        app = await wired_orchestrator.run_points_only(request, emit)

        assert app.generation_status != GenerationStatus.FAILED
        assert app.error_message is None
        event_types = [e[0] for e in events]
        assert "complete" in event_types
        assert "error" not in event_types
