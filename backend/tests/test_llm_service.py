"""
Tests for LLMService with mocked LiteLLM.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.llm_service import (
    LLMService, LLMServiceError, LLMConnectionError,
    LLMAuthError, LLMRateLimitError, LLMParseError,
)


@pytest.fixture
def mock_litellm():
    """Mock litellm.acompletion for deterministic testing."""
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def llm_service():
    """LLMService instance with default config."""
    return LLMService()


class TestLLMServiceGenerate:
    """Tests for the generate method."""

    @pytest.mark.asyncio
    async def test_generate_returns_text(self, mock_litellm, llm_service):
        """generate() should return the response text."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello! I am an AI assistant."))]
        mock_litellm.return_value = mock_response

        result = await llm_service.generate([{"role": "user", "content": "Say hello"}])
        assert result == "Hello! I am an AI assistant."

    @pytest.mark.asyncio
    async def test_generate_empty_response(self, mock_litellm, llm_service):
        """generate() should return empty string for empty content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=""))]
        mock_litellm.return_value = mock_response

        result = await llm_service.generate([{"role": "user", "content": "Say nothing"}])
        assert result == ""

    @pytest.mark.asyncio
    async def test_generate_auth_error(self, mock_litellm, llm_service):
        """Auth errors should raise LLMAuthError."""
        mock_litellm.side_effect = Exception("Authentication failed: Invalid API key")
        with pytest.raises(LLMAuthError):
            await llm_service.generate([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_generate_rate_limit_error(self, mock_litellm, llm_service):
        """Rate limit errors should raise LLMRateLimitError."""
        mock_litellm.side_effect = Exception("Rate limit exceeded: 429")
        with pytest.raises(LLMRateLimitError):
            await llm_service.generate([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, mock_litellm, llm_service):
        """Connection errors should raise LLMConnectionError."""
        mock_litellm.side_effect = Exception("Connection timeout")
        with pytest.raises(LLMConnectionError):
            await llm_service.generate([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_generate_generic_error(self, mock_litellm, llm_service):
        """Unclassified errors should raise LLMServiceError."""
        mock_litellm.side_effect = Exception("Some random error")
        with pytest.raises(LLMServiceError):
            await llm_service.generate([{"role": "user", "content": "Hi"}])


class TestLLMServiceGenerateStructured:
    """Tests for the generate_structured method."""

    @pytest.mark.asyncio
    async def test_generate_structured_parses_json(self, mock_litellm, llm_service):
        """generate_structured() should parse JSON response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(
            content='[{"project_id": "test", "project_name": "Test Project", "relevance_score": 0.9, "reasoning": "Good match"}]'
        ))]
        mock_litellm.return_value = mock_response

        from app.models.generation import MatchResult
        result = await llm_service.generate_structured(
            [{"role": "user", "content": "Match projects"}],
            response_model=MatchResult,
        )
        assert isinstance(result, list)
        assert result[0].project_id == "test"
        assert result[0].relevance_score == 0.9

    @pytest.mark.asyncio
    async def test_generate_structured_strips_markdown_fences(self, mock_litellm, llm_service):
        """generate_structured() should handle markdown-fenced JSON."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='```json\n{"name": "Test"}\n```'))]
        mock_litellm.return_value = mock_response

        from pydantic import BaseModel
        class TestModel(BaseModel):
            name: str

        result = await llm_service.generate_structured(
            [{"role": "user", "content": "Test"}],
            response_model=TestModel,
        )
        assert result.name == "Test"

    @pytest.mark.asyncio
    async def test_generate_structured_retry_on_failure(self, mock_litellm, llm_service):
        """generate_structured() should retry once on JSON parse failure."""
        mock_response_bad = MagicMock()
        mock_response_bad.choices = [MagicMock(message=MagicMock(content="not json"))]
        mock_response_good = MagicMock()
        mock_response_good.choices = [MagicMock(message=MagicMock(content='{"name": "Retried"}'))]
        mock_litellm.side_effect = [mock_response_bad, mock_response_good]

        from pydantic import BaseModel
        class TestModel(BaseModel):
            name: str

        result = await llm_service.generate_structured(
            [{"role": "user", "content": "Test"}],
            response_model=TestModel,
        )
        assert result.name == "Retried"
        assert mock_litellm.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_structured_raises_on_retry_failure(self, mock_litellm, llm_service):
        """generate_structured() should raise LLMParseError after failed retry."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="still not json"))]
        mock_litellm.return_value = mock_response

        from pydantic import BaseModel
        class TestModel(BaseModel):
            name: str

        with pytest.raises(LLMParseError):
            await llm_service.generate_structured(
                [{"role": "user", "content": "Test"}],
                response_model=TestModel,
            )


class TestLLMServiceMisc:
    """Tests for other LLMService methods."""

    def test_get_model_for_task_default(self, llm_service):
        """Default model should be gemini/gemini-2.5-pro."""
        model = llm_service.get_model_for_task("default")
        assert model == "gemini/gemini-2.5-pro"

    def test_get_model_for_task_custom(self):
        """Per-task config should override default model."""
        from app.models.generation import LLMConfig, TaskModelConfig
        config = LLMConfig(
            tasks={"keyword_analysis": TaskModelConfig(provider="gemini", model="gemini-3-pro-preview")}
        )
        svc = LLMService(config=config)
        model = svc.get_model_for_task("keyword_analysis")
        assert model == "gemini/gemini-3-pro-preview"

    def test_get_model_for_task_unknown_falls_back_to_default(self, llm_service):
        """Unknown task should fall back to default model."""
        model = llm_service.get_model_for_task("nonexistent_task")
        assert model == "gemini/gemini-2.5-pro"

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, mock_litellm, llm_service):
        """validate_connection() should return True on success."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello"))]
        mock_litellm.return_value = mock_response

        result = await llm_service.validate_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, mock_litellm, llm_service):
        """validate_connection() should return False on error."""
        mock_litellm.side_effect = Exception("API error")
        result = await llm_service.validate_connection()
        assert result is False
