"""
Application configuration loaded from environment variables and .env file.

Uses pydantic-settings BaseSettings for type-safe, validated config.
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    # ── LLM — field name maps to GEMINI_API_KEY env var via pydantic-settings ──
    gemini_api_key: str = ""
    llm_default_model: str = "gemini/gemini-3-flash-preview"  # reads from LLM_DEFAULT_MODEL env var
    llm_default_temperature: float = 0.3  # Gemini 3+ models override to 1.0 internally
    llm_max_tokens: int = 4096

    # ── Paths ──
    data_dir: Path = Path("./data")
    sweep_file_path: Path = Path("../docs/PROJECT_SWEEP_SUMMARIES.md")
    latex_template_path: Path = Path("../docs/tex_templates/template_blank.tex")

    # ── Server ──
    cors_origins: str = "http://localhost:5173"

    # ── PDF Compilation (MiKTeX — optional) ──
    pdflatex_path: Optional[str] = None

    # ── Prompt Overrides (optional — overrides .j2 files at runtime) ──
    prompt_matching: Optional[str] = None
    prompt_keyword_analysis: Optional[str] = None
    prompt_resume_points: Optional[str] = None
    prompt_resume_writeup: Optional[str] = None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def configure_litellm(self) -> None:
        """Set the LiteLLM GEMINI_API_KEY in os.environ before any LLM call.

        Call this at startup (and after any key rotation) so LiteLLM can
        authenticate with Google's Gemini API.
        """
        import os
        os.environ["GEMINI_API_KEY"] = self.gemini_api_key


# Singleton — import this everywhere
settings = Settings()  # type: ignore[call-arg]
