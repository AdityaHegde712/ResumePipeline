"""
LLM Service — provider-agnostic client using LiteLLM.

Architecture:
  [v1.0] LiteLLM exclusively → Gemini 3 Flash Preview for all tasks
  [v1.1] Per-task routing via TaskModelConfig (DeepSeek swap-in ready)

Provider keying (LiteLLM format):
  Gemini:   "gemini/gemini-3-flash-preview"
  DeepSeek: "deepseek/deepseek-v4-flash"
  OpenAI:   "openai/gpt-4o"
  Anthropic: "anthropic/claude-sonnet-4-20250514"
"""
import asyncio
import os
import json
import logging
from typing import AsyncIterator, Callable, Optional, Type
from pydantic import BaseModel

from app.models.generation import LLMConfig, TaskModelConfig

logger = logging.getLogger(__name__)

# ── Error classes ──
class LLMServiceError(Exception):
    """Base exception for LLM service errors."""

class LLMConnectionError(LLMServiceError):
    """API unreachable or network error."""

class LLMAuthError(LLMServiceError):
    """Bad API key or authentication failure."""

class LLMRateLimitError(LLMServiceError):
    """Rate limited by the provider."""

class LLMParseError(LLMServiceError):
    """Could not parse the LLM response."""
class LLMService:
    """Provider-agnostic LLM client.
    
    v1.0: Routes everything through LiteLLM → Gemini.
    v1.1: Per-task routing via TaskModelConfig.
    """

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        gemini_api_key: Optional[str] = None,
    ):
        """Initialize the LLM service.
        
        Args:
            config: LLMConfig for per-task model routing. If None, uses defaults.
            gemini_api_key: Optional key override. If provided, sets env var.
        """
        self.config = config or LLMConfig()
        
        if gemini_api_key:
            os.environ["GEMINI_API_KEY"] = gemini_api_key
        
        # ▼▼▼ v1.1: DeepSeek swap-in — uncomment when ready ▼▼▼
        # from openai import OpenAI
        # self.deepseek_client = OpenAI(
        #     api_key=os.getenv("DEEPSEEK_API_KEY"),
        #     base_url="https://api.deepseek.com/v1"
        # )

    def get_model_for_task(self, task: str) -> str:
        """Return 'provider/model' string for the given task.
        
        If task has per-task config, use that. Otherwise use default.
        """
        if task in self.config.tasks:
            task_config = self.config.tasks[task]
            return f"{task_config.provider}/{task_config.model}"
        return f"{self.config.default_provider}/{self.config.default_model}"

    async def generate(
        self,
        messages: list[dict],
        task: str = "default",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        stream: bool = False,
        max_retries: int = 3,
    ) -> str | AsyncIterator[str]:
        """Send a completion request to the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            task: Task name for model routing.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            stream: If True, returns async generator yielding tokens.
            max_retries: Maximum number of retries for transient errors.
            
        Returns:
            If stream=False: Full response text as string.
            If stream=True: AsyncIterator yielding tokens.
            
        Raises:
            LLMConnectionError: If API unreachable.
            LLMAuthError: If authentication fails.
            LLMRateLimitError: If rate limited.
        """
        model = self.get_model_for_task(task)

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                from litellm import acompletion

                if stream:
                    return self._stream_generate(model, messages, temperature, max_tokens)

                response = await acompletion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                return response.choices[0].message.content or ""

            except (LLMConnectionError, LLMRateLimitError) as e:
                last_error = e
                if attempt < max_retries:
                    delay = 2 ** attempt  # 1, 2, 4 seconds
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
            except Exception as e:
                # Non-retryable: auth errors, parse errors, etc.
                self._handle_error(e)

    async def _stream_generate(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Internal streaming generator."""
        from litellm import acompletion
        
        try:
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            self._handle_error(e)

    async def generate_structured(
        self,
        messages: list[dict],
        task: str = "default",
        response_model: Optional[Type[BaseModel]] = None,
        temperature: float = 0.3,
    ) -> BaseModel:
        """Generate and parse a structured JSON response.
        
        Args:
            messages: Message list with system + user prompts.
            task: Task name for model routing.
            response_model: Pydantic model to parse response into.
            temperature: Sampling temperature.
            
        Returns:
            Parsed Pydantic model instance.
            
        Raises:
            LLMParseError: If JSON parsing fails after retry.
        """
        # First attempt
        text = await self.generate(messages, task=task, temperature=temperature)
        
        try:
            parsed = self._parse_json_response(text, response_model)
            return parsed
        except (json.JSONDecodeError, Exception) as e:
            # Retry with fix instruction
            logger.warning(f"JSON parse failed on first attempt for task '{task}', retrying...")
            
            retry_messages = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": "Fix your JSON output. Return ONLY valid JSON that matches the expected schema. No markdown fences, no explanation."},
            ]
            
            try:
                text2 = await self.generate(retry_messages, task=task, temperature=temperature)
                parsed = self._parse_json_response(text2, response_model)
                return parsed
            except (json.JSONDecodeError, Exception) as e2:
                raise LLMParseError(
                    f"Failed to parse structured response for task '{task}' after retry: {e2}"
                ) from e2

    def _parse_json_response(self, text: str, model: Type[BaseModel]) -> BaseModel:
        """Parse JSON from LLM response, stripping markdown fences if present."""
        # Strip markdown code fences
        text = text.strip()
        if text.startswith("```"):
            # Find the first and last ```
            start = text.find("\n") + 1
            end = text.rfind("```")
            if end > start:
                text = text[start:end].strip()
        
        # Also handle ```json prefix
        if text.startswith("```json"):
            text = text[7:]
            end = text.rfind("```")
            if end > 0:
                text = text[:end].strip()
        
        data = json.loads(text)
        
        if model is None:
            return data
        
        if isinstance(data, list):
            # For List[Model] responses, parse each item
            return [model(**item) for item in data]
        
        return model(**data)

    async def validate_connection(self) -> bool:
        """Validate the LLM connection by sending a simple prompt."""
        try:
            result = await self.generate(
                [{"role": "user", "content": "Say hello in one word."}],
                task="default",
                max_tokens=10,
            )
            return bool(result and len(result.strip()) > 0)
        except LLMServiceError:
            return False

    def _handle_error(self, error: Exception) -> None:
        """Map raw exceptions to LLMServiceError subclasses."""
        error_str = str(error).lower()
        
        if "authentication" in error_str or "api key" in error_str or "auth" in error_str:
            raise LLMAuthError(f"Authentication failed: {error}") from error
        elif "rate limit" in error_str or "too many requests" in error_str or "429" in error_str:
            raise LLMRateLimitError(f"Rate limited: {error}") from error
        elif any(x in error_str for x in ["connection", "timeout", "unreachable", "unavailable", "503"]):
            raise LLMConnectionError(f"Connection failed: {error}") from error
        else:
            raise LLMServiceError(f"LLM call failed: {error}") from error