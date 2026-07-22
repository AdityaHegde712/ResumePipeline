"""
Tests for MatchingService result validation.

Regression coverage for a bug found via live reproduction: the project_matching
prompt never asks the LLM for project_name, but MatchResult required it as a
mandatory field, so every real match call crashed with a pydantic ValidationError.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.generation import MatchResult
from app.models.project import ProjectEntry
from app.pipeline.matching_service import MatchingService


@pytest.fixture
def sample_projects():
    return [
        ProjectEntry(id="recsysproject", name="RecSysProject", type="ML", summary="A recommender system"),
        ProjectEntry(id="sentry", name="Sentry", type="CV", summary="A vision project"),
    ]


@pytest.fixture
def matching_service():
    return MatchingService(llm_service=MagicMock(), prompt_manager=MagicMock())


class TestValidateResults:
    def test_backfills_project_name_when_llm_omits_it(self, matching_service, sample_projects):
        """MatchResult.project_name defaults to '' -- validation must not
        depend on the LLM providing it, since the prompt never asks for it."""
        results = [
            MatchResult(project_id="recsysproject", relevance_score=0.9, reasoning="good fit"),
        ]

        validated = matching_service._validate_results(results, sample_projects)

        assert len(validated) == 1
        assert validated[0].project_name == "RecSysProject"

    def test_drops_results_for_unknown_project_ids(self, matching_service, sample_projects):
        results = [
            MatchResult(project_id="does-not-exist", relevance_score=0.5, reasoning="hallucinated"),
        ]

        validated = matching_service._validate_results(results, sample_projects)

        assert validated == []

    def test_clamps_relevance_score_to_unit_range(self, matching_service, sample_projects):
        results = [
            MatchResult(project_id="sentry", relevance_score=1.5, reasoning="too high"),
        ]

        validated = matching_service._validate_results(results, sample_projects)

        assert validated[0].relevance_score == 1.0

    @pytest.mark.asyncio
    async def test_match_end_to_end_survives_llm_response_missing_project_name(
        self, matching_service, sample_projects
    ):
        """Full match() call with a mocked LLM response shaped exactly like the
        real Gemini output that triggered the original crash (no project_name key)."""
        matching_service.llm.generate_structured = AsyncMock(
            return_value=[
                MatchResult(project_id="recsysproject", relevance_score=0.95, reasoning="strong match"),
            ]
        )
        matching_service.prompts.render = MagicMock(return_value="prompt text")

        results = await matching_service.match(
            job_title="ML Engineer",
            company_name="TestCo",
            job_description="Build ML systems",
            projects=sample_projects,
        )

        assert len(results) == 1
        assert results[0].project_name == "RecSysProject"
