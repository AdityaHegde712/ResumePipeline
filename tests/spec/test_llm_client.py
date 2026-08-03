"""Frozen spec tests for the LiteLLM client (T09, Phase 5).

LOCKED contract — ``backend/app/llm_client.py`` must satisfy this file
exactly. This file is frozen after Phase 5 and may not be modified to fit
an implementation.

Public interface (all exported from ``backend.app.llm_client``):

    class LLMError(Exception):
        \"\"\"Raised for every failure of the generation call.

        Attributes:
            category: str -- one of "authentication", "rate_limit",
                "connection", or "unknown". ``str(exc)`` is a readable
                message that also contains the category token.
        \"\"\"

    async def generate_resume_text(prompt: str, settings: Settings) -> str

Call surface locked by these tests (PLAN D7):

- ``generate_resume_text`` performs exactly ONE non-streaming call to
  ``litellm.acompletion`` with keyword arguments ``model=settings.model``,
  ``temperature=settings.temperature``,
  ``messages=[{"role": "user", "content": prompt}]``, and a falsy/absent
  ``stream``. The implementation must reach the function through the
  ``litellm`` module object (``litellm.acompletion``), so tests can
  monkeypatch ``litellm.acompletion`` directly. No network is touched.
- The success path returns ``response.choices[0].message.content``
  verbatim.
- Every failure of the underlying call is mapped to ``LLMError``; raw
  provider exceptions never leak. Mapping by exception type:

      litellm.AuthenticationError  -> category "authentication"
      litellm.RateLimitError       -> category "rate_limit"
      litellm.APIConnectionError   -> category "connection"
      any other exception          -> category "unknown"

  ``str(exc)`` is readable and contains the category token; ``exc.category``
  exposes it programmatically.
"""

import pytest
import litellm

from backend.app.config import Settings
from backend.app.llm_client import LLMError, generate_resume_text

PROMPT = "Write a tailored resume for a Data Scientist role at SUHORA."


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    """Minimal stand-in for a LiteLLM ``ModelResponse``."""

    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class TestSuccessPath:
    """The one non-streaming acompletion call returns response text."""

    async def test_returns_response_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The generated text comes straight from the completion response."""

        captured_kwargs: dict[str, object] = {}

        async def fake_acompletion(**kwargs: object) -> _FakeResponse:
            captured_kwargs.update(kwargs)
            return _FakeResponse("Generated resume text.")

        monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

        result = await generate_resume_text(PROMPT, Settings())

        assert result == "Generated resume text."

    async def test_calls_acompletion_with_model_temperature_and_messages(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Model and temperature come from settings; the prompt is the user message."""

        captured_kwargs: dict[str, object] = {}

        async def fake_acompletion(**kwargs: object) -> _FakeResponse:
            captured_kwargs.update(kwargs)
            return _FakeResponse("text")

        monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
        settings = Settings()

        await generate_resume_text(PROMPT, settings)

        assert captured_kwargs["model"] == settings.model
        assert captured_kwargs["temperature"] == settings.temperature
        assert captured_kwargs["messages"] == [{"role": "user", "content": PROMPT}]

    async def test_call_is_non_streaming(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The acompletion call never requests streaming (D7)."""

        captured_kwargs: dict[str, object] = {}

        async def fake_acompletion(**kwargs: object) -> _FakeResponse:
            captured_kwargs.update(kwargs)
            return _FakeResponse("text")

        monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

        await generate_resume_text(PROMPT, Settings())

        assert not captured_kwargs.get("stream")


class TestErrorMapping:
    """Provider failures become typed LLMError categories; nothing leaks."""

    @pytest.mark.parametrize(
        ("provider_error", "expected_category"),
        [
            (
                litellm.AuthenticationError(
                    message="invalid api key",
                    llm_provider="gemini",
                    model="gemini/gemini-3-flash-preview",
                ),
                "authentication",
            ),
            (
                litellm.RateLimitError(
                    message="rate limit hit",
                    llm_provider="gemini",
                    model="gemini/gemini-3-flash-preview",
                ),
                "rate_limit",
            ),
            (
                litellm.APIConnectionError(
                    message="connection refused",
                    llm_provider="gemini",
                    model="gemini/gemini-3-flash-preview",
                ),
                "connection",
            ),
            (RuntimeError("unexpected failure"), "unknown"),
        ],
    )
    async def test_provider_errors_map_to_llm_error_categories(
        self,
        monkeypatch: pytest.MonkeyPatch,
        provider_error: Exception,
        expected_category: str,
    ) -> None:
        """Each provider error type maps to its locked LLMError category."""

        async def fake_acompletion(**kwargs: object) -> _FakeResponse:
            raise provider_error

        monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

        with pytest.raises(LLMError) as exc_info:
            await generate_resume_text(PROMPT, Settings())

        assert exc_info.value.category == expected_category
        assert expected_category in str(exc_info.value)
