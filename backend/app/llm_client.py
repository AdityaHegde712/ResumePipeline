"""LiteLLM client: one non-streaming call with typed error mapping."""

import litellm

from backend.app.config import Settings

class LLMError(Exception):
    """Raised for every failure of the resume generation call.

    Attributes:
        category: One of "authentication", "rate_limit", "connection",
            or "unknown".
    """

    def __init__(self, message: str, category: str) -> None:
        super().__init__(f"{message} (category: {category})")
        self.category = category


def _error_category(exc: Exception) -> str:
    """Map a provider exception to its locked LLMError category."""

    if isinstance(exc, litellm.AuthenticationError):
        return "authentication"
    if isinstance(exc, litellm.RateLimitError):
        return "rate_limit"
    if isinstance(exc, litellm.APIConnectionError):
        return "connection"
    return "unknown"


async def generate_resume_text(prompt: str, settings: Settings) -> str:
    """Generate tailored resume text with a single non-streaming call.

    Args:
        prompt: Fully-built resume prompt (templating stays in the API layer).
        settings: Runtime settings supplying the model and temperature.

    Returns:
        The generated resume text verbatim.

    Raises:
        LLMError: For every failure of the underlying completion call,
            categorized as authentication, rate_limit, connection, or unknown.
    """
    return await _generate_text(prompt, settings, "Resume")


async def generate_cover_letter_text(prompt: str, settings: Settings) -> str:
    """Generate tailored cover-letter text with a single non-streaming call.

    Uses the same settings-driven model and temperature as the resume call.

    Args:
        prompt: Fully-built cover-letter prompt (templating stays in the API).
        settings: Runtime settings supplying the model and temperature.

    Returns:
        The generated cover-letter text verbatim.

    Raises:
        LLMError: For every failure of the underlying completion call,
            categorized as authentication, rate_limit, connection, or unknown.
    """
    return await _generate_text(prompt, settings, "Cover letter")


async def _generate_text(prompt: str, settings: Settings, phase: str) -> str:
    """Run one non-streaming acompletion call with the locked error mapping."""
    try:
        response = await litellm.acompletion(
            model=settings.model,
            temperature=settings.temperature,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
    except Exception as exc:
        raise LLMError(
            message=f"{phase} generation failed: {exc}",
            category=_error_category(exc),
        ) from exc
    return response.choices[0].message.content
