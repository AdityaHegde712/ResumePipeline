"""
Tests for KeywordAnalysisService.

Tests cover:
  - analyze() returns correct dict structure with all expected keys
  - analyze() delegates to prompt_manager.render and llm.generate_structured
  - extract_keywords_text() formatting with all/missing/empty categories
  - action_verbs truncation to 5 items
  - Edge cases: empty dict, missing keys, None values
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.pipeline.keyword_analysis_service import KeywordAnalysisService


# ── Shared sample data ──────────────────────────────────────────────────────

SAMPLE_ANALYSIS = {
    "required_skills": ["Python", "PyTorch", "Docker", "Kubernetes"],
    "preferred_skills": ["GraphQL", "React"],
    "domains": ["Machine Learning", "Computer Vision"],
    "action_verbs": [
        "developed", "deployed", "optimized", "architected", "led",
        "mentored", "automated",
    ],
    "technologies": ["AWS", "PostgreSQL", "Redis"],
    "seniority_level": "Senior",
}

SAMPLE_JOB_TITLE = "Senior ML Engineer"
SAMPLE_COMPANY = "Acme Corp"
SAMPLE_DESCRIPTION = "We are looking for a Senior ML Engineer..."


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_llm_service():
    """Mock LLMService with an async generate_structured method."""
    svc = MagicMock()
    svc.generate_structured = AsyncMock(return_value=dict(SAMPLE_ANALYSIS))
    return svc


@pytest.fixture
def mock_prompt_manager():
    """Mock PromptManager with a sync render method."""
    mgr = MagicMock()
    mgr.render.return_value = "Rendered prompt text for keyword_analysis"
    return mgr


@pytest.fixture
def service(mock_llm_service, mock_prompt_manager):
    """KeywordAnalysisService instance with fully mocked dependencies."""
    return KeywordAnalysisService(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
    )


# ── Tests: analyze() ────────────────────────────────────────────────────────


class TestAnalyze:
    """Tests for the analyze() async method."""

    @pytest.mark.asyncio
    async def test_analyze_returns_expected_keys(self, service):
        """analyze() should return a dict with all six keyword categories."""
        result = await service.analyze(
            job_title=SAMPLE_JOB_TITLE,
            company_name=SAMPLE_COMPANY,
            job_description=SAMPLE_DESCRIPTION,
        )

        expected_keys = {
            "required_skills", "preferred_skills", "domains",
            "action_verbs", "technologies", "seniority_level",
        }
        assert isinstance(result, dict)
        assert set(result.keys()) == expected_keys

    @pytest.mark.asyncio
    async def test_analyze_returns_all_categories_as_lists(self, service):
        """List-valued fields should be returned as lists, seniority_level as string."""
        result = await service.analyze(
            job_title=SAMPLE_JOB_TITLE,
            company_name=SAMPLE_COMPANY,
            job_description=SAMPLE_DESCRIPTION,
        )

        list_fields = ["required_skills", "preferred_skills", "domains",
                       "action_verbs", "technologies"]
        for field in list_fields:
            assert isinstance(result[field], list), (
                f"{field} should be a list, got {type(result[field])}"
            )
        assert isinstance(result["seniority_level"], str)

    @pytest.mark.asyncio
    async def test_analyze_passes_correct_context_to_prompt_manager(
        self, service, mock_prompt_manager
    ):
        """analyze() should render prompt with job_title, company_name, job_description."""
        await service.analyze(
            job_title=SAMPLE_JOB_TITLE,
            company_name=SAMPLE_COMPANY,
            job_description=SAMPLE_DESCRIPTION,
        )

        mock_prompt_manager.render.assert_called_once_with(
            "keyword_analysis",
            {
                "job_title": SAMPLE_JOB_TITLE,
                "company_name": SAMPLE_COMPANY,
                "job_description": SAMPLE_DESCRIPTION,
            },
        )

    @pytest.mark.asyncio
    async def test_analyze_calls_llm_with_correct_task(
        self, service, mock_llm_service
    ):
        """analyze() should call generate_structured with task='keyword_analysis'."""
        await service.analyze(
            job_title=SAMPLE_JOB_TITLE,
            company_name=SAMPLE_COMPANY,
            job_description=SAMPLE_DESCRIPTION,
        )

        mock_llm_service.generate_structured.assert_called_once()
        _call_kwargs = mock_llm_service.generate_structured.call_args.kwargs
        assert _call_kwargs["task"] == "keyword_analysis"

    @pytest.mark.asyncio
    async def test_analyze_uses_low_temperature(self, service, mock_llm_service):
        """analyze() should use temperature=0.2 for consistent output."""
        await service.analyze(
            job_title=SAMPLE_JOB_TITLE,
            company_name=SAMPLE_COMPANY,
            job_description=SAMPLE_DESCRIPTION,
        )

        _call_kwargs = mock_llm_service.generate_structured.call_args.kwargs
        assert _call_kwargs["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_analyze_sends_two_messages(self, service, mock_llm_service):
        """analyze() should send a system and user message to the LLM."""
        await service.analyze(
            job_title=SAMPLE_JOB_TITLE,
            company_name=SAMPLE_COMPANY,
            job_description=SAMPLE_DESCRIPTION,
        )

        _call_args = mock_llm_service.generate_structured.call_args
        messages = _call_args[0][0] if _call_args[0] else _call_args.kwargs.get("messages")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_analyze_system_message_is_about_job_analysis(
        self, service, mock_llm_service
    ):
        """System message should instruct the LLM to extract structured keyword data."""
        await service.analyze(
            job_title=SAMPLE_JOB_TITLE,
            company_name=SAMPLE_COMPANY,
            job_description=SAMPLE_DESCRIPTION,
        )

        _call_args = mock_llm_service.generate_structured.call_args
        messages = _call_args[0][0] if _call_args[0] else _call_args.kwargs.get("messages")
        assert "structured keyword data" in messages[0]["content"]
        assert "JSON" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_analyze_user_message_contains_rendered_prompt(
        self, service, mock_prompt_manager, mock_llm_service
    ):
        """User message content should be the rendered prompt text."""
        mock_prompt_manager.render.return_value = "CUSTOM_RENDERED_PROMPT"

        await service.analyze(
            job_title=SAMPLE_JOB_TITLE,
            company_name=SAMPLE_COMPANY,
            job_description=SAMPLE_DESCRIPTION,
        )

        _call_args = mock_llm_service.generate_structured.call_args
        messages = _call_args[0][0] if _call_args[0] else _call_args.kwargs.get("messages")
        assert messages[1]["content"] == "CUSTOM_RENDERED_PROMPT"

    @pytest.mark.asyncio
    async def test_analyze_returns_raw_dict_from_llm(self, service, mock_llm_service):
        """analyze() should pass through the dict returned by generate_structured."""
        llm_return = {
            "required_skills": ["Go", "Rust"],
            "preferred_skills": [],
            "domains": ["Systems"],
            "action_verbs": ["built"],
            "technologies": ["Linux"],
            "seniority_level": "Staff",
        }
        mock_llm_service.generate_structured.return_value = llm_return

        result = await service.analyze(
            job_title=SAMPLE_JOB_TITLE,
            company_name=SAMPLE_COMPANY,
            job_description=SAMPLE_DESCRIPTION,
        )

        assert result is llm_return  # same object identity


# ── Tests: extract_keywords_text() ──────────────────────────────────────────


class TestExtractKeywordsText:
    """Tests for the extract_keywords_text() synchronous method."""

    def test_all_categories_formatted_correctly(self, service):
        """extract_keywords_text() should format all six categories."""
        result = service.extract_keywords_text(SAMPLE_ANALYSIS)

        assert "required: Python, PyTorch, Docker, Kubernetes" in result
        assert "preferred: GraphQL, React" in result
        assert "domains: Machine Learning, Computer Vision" in result
        assert "technologies: AWS, PostgreSQL, Redis" in result

    def test_action_verbs_truncated_to_five(self, service):
        """action_verbs should be limited to the first 5 items."""
        result = service.extract_keywords_text(SAMPLE_ANALYSIS)

        assert "verbs: developed, deployed, optimized, architected, led" in result
        # "mentored" and "automated" should NOT appear
        assert "mentored" not in result

    def test_missing_category_is_skipped(self, service):
        """A missing key should be skipped without raising."""
        incomplete = {
            "required_skills": ["Python"],
            "domains": ["ML"],
        }
        result = service.extract_keywords_text(incomplete)
        assert "required: Python" in result
        assert "domains: ML" in result
        assert "preferred:" not in result
        assert "technologies:" not in result
        assert "verbs:" not in result

    def test_empty_dict_returns_empty_string(self, service):
        """An empty dict should produce an empty string."""
        result = service.extract_keywords_text({})
        assert result == ""

    def test_empty_list_categories_skipped(self, service):
        """A category with an empty list should be skipped."""
        empty_lists = {
            "required_skills": [],
            "preferred_skills": [],
            "domains": [],
            "action_verbs": [],
            "technologies": [],
            "seniority_level": "Senior",
        }
        result = service.extract_keywords_text(empty_lists)
        assert result == ""

    def test_category_with_none_skipped_gracefully(self, service):
        """A category with None value should be skipped without error."""
        with_none = {
            "required_skills": None,
            "domains": ["ML"],
        }
        result = service.extract_keywords_text(with_none)
        # None is falsy, so get() returns None which is falsy → skipped
        assert "domains: ML" in result
        assert "required:" not in result

    def test_single_item_categories(self, service):
        """A single-item list should produce one-element output."""
        single = {
            "required_skills": ["Python"],
            "technologies": ["Docker"],
        }
        result = service.extract_keywords_text(single)
        assert result == "required: Python | technologies: Docker"

    def test_pipe_separator_between_categories(self, service):
        """Multiple categories should be joined with ' | '."""
        two_cats = {
            "required_skills": ["A"],
            "preferred_skills": ["B"],
        }
        result = service.extract_keywords_text(two_cats)
        assert result == "required: A | preferred: B"

    def test_seniority_level_not_in_output(self, service):
        """seniority_level key should be ignored in extract_keywords_text."""
        with_seniority = {
            "required_skills": ["Python"],
            "seniority_level": "Senior",
        }
        result = service.extract_keywords_text(with_seniority)
        assert "senior" not in result.lower() or "Senior" not in result

    def test_verbs_label_is_verbs_not_action_verbs(self, service):
        """The output label for action_verbs should be 'verbs:', not 'action_verbs:'."""
        with_verbs = {
            "action_verbs": ["ran", "walked"],
        }
        result = service.extract_keywords_text(with_verbs)
        assert "verbs: ran, walked" in result
        assert "action_verbs:" not in result

    def test_order_of_categories(self, service):
        """Categories should appear in the expected order."""
        result = service.extract_keywords_text(SAMPLE_ANALYSIS)
        required_idx = result.index("required:")
        preferred_idx = result.index("preferred:")
        domains_idx = result.index("domains:")
        tech_idx = result.index("technologies:")
        verbs_idx = result.index("verbs:")

        assert required_idx < preferred_idx < domains_idx < tech_idx < verbs_idx, (
            "Categories out of expected order"
        )

    def test_output_does_not_end_with_separator(self, service):
        """Output string should not end with ' | '."""
        result = service.extract_keywords_text(SAMPLE_ANALYSIS)
        assert not result.endswith(" | ")

    def test_special_characters_in_skills(self, service):
        """Skills containing special characters should be preserved."""
        special = {
            "required_skills": ["C++", "C#", ".NET"],
            "domains": ["AI/ML"],
        }
        result = service.extract_keywords_text(special)
        assert "C++" in result
        assert "C#" in result
        assert ".NET" in result
        assert "AI/ML" in result


# ── Tests: integration-style (mocked dependencies, real service) ────────────


class TestKeywordAnalysisServiceIntegration:
    """Verify the service wires its dependencies correctly."""

    @pytest.mark.asyncio
    async def test_full_analyze_extract_round_trip(self, service):
        """After analyze(), extract_keywords_text() should produce a non-empty string."""
        result = await service.analyze(
            job_title=SAMPLE_JOB_TITLE,
            company_name=SAMPLE_COMPANY,
            job_description=SAMPLE_DESCRIPTION,
        )
        formatted = service.extract_keywords_text(result)
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "required: Python, PyTorch, Docker, Kubernetes" in formatted

    @pytest.mark.asyncio
    async def test_analyze_with_empty_description(self, service, mock_llm_service):
        """analyze() should handle an empty job description gracefully."""
        empty_result = {
            "required_skills": [],
            "preferred_skills": [],
            "domains": [],
            "action_verbs": [],
            "technologies": [],
            "seniority_level": "",
        }
        mock_llm_service.generate_structured.return_value = empty_result

        result = await service.analyze(
            job_title="",
            company_name="",
            job_description="",
        )
        assert result["required_skills"] == []
        assert service.extract_keywords_text(result) == ""

    @pytest.mark.asyncio
    async def test_analyze_llm_error_propagates(self, mock_llm_service, mock_prompt_manager):
        """If generate_structured raises, analyze() should let it propagate."""
        mock_llm_service.generate_structured.side_effect = ValueError(
            "LLM call failed"
        )
        svc = KeywordAnalysisService(
            llm_service=mock_llm_service,
            prompt_manager=mock_prompt_manager,
        )

        with pytest.raises(ValueError, match="LLM call failed"):
            await svc.analyze(
                job_title=SAMPLE_JOB_TITLE,
                company_name=SAMPLE_COMPANY,
                job_description=SAMPLE_DESCRIPTION,
            )

    def test_init_stores_dependencies(self, mock_llm_service, mock_prompt_manager):
        """Constructor should store references to llm and prompts."""
        svc = KeywordAnalysisService(
            llm_service=mock_llm_service,
            prompt_manager=mock_prompt_manager,
        )
        assert svc.llm is mock_llm_service
        assert svc.prompts is mock_prompt_manager
