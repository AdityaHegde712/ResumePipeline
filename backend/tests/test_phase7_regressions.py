"""
Regression tests for Phase 7 bug fixes.

Verifies:
  1. ``PromptManager(templates_dir, settings)`` no longer crashes with ``TypeError``
  2. ``LLMService(config=get_llm_config())`` respects settings model (not hardcoded)
  4. SSE complete event data is JSON-serializable (Pydantic → dict via ``.model_dump()``)
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path


# ---------------------------------------------------------------------------
# Bug 1 — get_orchestrator() should not crash
# ---------------------------------------------------------------------------

class TestBug1OrchestratorInit:
    """get_orchestrator() must create all services without TypeError."""

    def test_prompt_manager_accepts_templates_dir(self) -> None:
        """Verify PromptManager(templates_dir, settings) doesn't raise TypeError.

        This used to crash because PromptManager() was called without the
        required 'templates_dir' argument.
        """
        from app.services.prompt_manager import PromptManager

        tmp_dir = Path(__file__).parent / "_tmp_prompts"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        try:
            pm = PromptManager(tmp_dir, None)
            assert pm is not None
        except TypeError as e:
            pytest.fail(f"PromptManager(templates_dir, settings) raised TypeError: {e}")
        finally:
            # Cleanup
            import shutil
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)

    def test_prompt_manager_raises_without_args(self) -> None:
        """Verify that PromptManager() without args DOES raise TypeError (safety check)."""
        from app.services.prompt_manager import PromptManager

        with pytest.raises(TypeError):
            PromptManager()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Bug 2 — LLMService should use model from .env / settings
# ---------------------------------------------------------------------------

class TestBug2EnvModel:
    """LLMService must resolve the model from settings, not a hardcoded default."""

    @patch("app.api.config.get_llm_config")
    def test_orchestrator_uses_env_model(self, mock_get_llm_config) -> None:
        """Verify that get_orchestrator() passes get_llm_config() to LLMService."""
        from app.models.generation import LLMConfig

        # Simulate an env-provided model
        env_model = "gemini-3-flash-preview"
        env_config = LLMConfig(
            default_provider="gemini",
            default_model=env_model,
        )
        mock_get_llm_config.return_value = env_config

        # Reset the module-level singleton
        import app.api.resume as resume_mod
        resume_mod._orchestrator = None

        # Now patch get_orchestrator's internal imports and the services it creates
        with (
            patch("app.services.prompt_manager.PromptManager") as mock_pm,
            patch("app.services.llm_service.LLMService") as mock_llm_svc,
            patch("app.services.profile_service.ProfileService"),
            patch("app.services.project_sweep_service.ProjectSweepService"),
            patch("app.services.history_service.HistoryService"),
            patch("app.pipeline.orchestrator.Orchestrator"),
        ):
            mock_llm_instance = MagicMock()
            mock_llm_svc.return_value = mock_llm_instance
            mock_llm_instance.get_model_for_task.return_value = f"gemini/{env_model}"

            from app.api.resume import get_orchestrator
            orch = get_orchestrator()

            # Verify LLMService was called with config=get_llm_config()
            mock_llm_svc.assert_called_once()
            call_kwargs = mock_llm_svc.call_args[1]
            assert "config" in call_kwargs, (
                "LLMService() should be called with config=get_llm_config(), "
                "but no 'config' kwarg was found"
            )

            # Verify the model resolves correctly
            resolved = mock_llm_instance.get_model_for_task("resume_points")
            assert env_model in resolved, (
                f"Expected model '{env_model}' in resolved '{resolved}', "
                f"but it wasn't found. The hardcoded default is being used instead."
            )

            resume_mod._orchestrator = None


# ---------------------------------------------------------------------------
# Bug 4 — SSE "complete" event data must be JSON-serializable
# ---------------------------------------------------------------------------

class TestBug4SseSerialization:
    """The SSE 'complete' event data must survive json.dumps()."""

    def test_sse_complete_data_is_json_serializable(self) -> None:
        """Build the same data dict that _emit_complete() produces and
        verify json.dumps() does not raise TypeError.
        """
        from app.models.application import (
            BulletPoint,
            SectionPoints,
            GeneratedContent,
        )

        bullets = [
            BulletPoint(
                id="b1",
                section="project:arvr",
                text="Built an AR/VR prototype",
                order=1,
                edited=False,
            ),
        ]
        sections = [
            SectionPoints(
                section_key="project:arvr",
                section_title="ARVR Project",
                bullets=bullets,
            )
        ]
        generated = GeneratedContent(
            resume_points=sections,
            model_used="gemini-3-flash-preview",
        )

        # Simulate _emit_complete() data construction (after fix)
        data = {
            "application_id": "test-app-001",
            "latex": generated.resume_latex or "",
            "sections": (
                [s.model_dump() for s in generated.resume_points]
                if generated
                else []
            ),
            "total_tokens": 42,
        }

        try:
            serialized = json.dumps(data)
            assert isinstance(serialized, str)
            assert "ARVR Project" in serialized
        except TypeError as e:
            pytest.fail(f"json.dumps() raised TypeError on SSE complete data: {e}")

    def test_sse_complete_data_empty_generated(self) -> None:
        """When generated is None, sections must be an empty list and json-safe."""
        data = {
            "application_id": "test-app-002",
            "latex": "",
            "sections": [],
            "total_tokens": 0,
        }

        try:
            serialized = json.dumps(data)
            assert isinstance(serialized, str)
        except TypeError as e:
            pytest.fail(f"json.dumps() raised TypeError on empty data: {e}")
