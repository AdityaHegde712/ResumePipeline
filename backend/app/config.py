"""Application settings for ResumePipeline v2.

All paths are pathlib.Path objects resolved relative to the repository root.
"""

import shutil
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]

# Owner-specified MiKTeX default for this dev machine (architect D11).
DEFAULT_PDFLATEX_PATH = Path(
    "C:/Users/hifia/AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex.exe"
)


def resolve_pdf_latex_path(env_value: str | None = None) -> Path | None:
    """Resolve the pdflatex executable via the PDFLATEX_PATH chain.

    A truthy env value wins: a directory gets ``pdflatex.exe`` appended,
    anything else is used as-is. With no env value, the default MiKTeX path
    is used if present, then ``shutil.which("pdflatex")`` as a last resort.

    Args:
        env_value: Raw PDFLATEX_PATH value, or None to skip the env branch.

    Returns:
        Resolved Path to pdflatex.exe, or None if nothing could be resolved.
    """
    if env_value:
        candidate = Path(env_value).expanduser()
        if candidate.is_dir():
            return candidate / "pdflatex.exe"
        return candidate
    if DEFAULT_PDFLATEX_PATH.exists():
        return DEFAULT_PDFLATEX_PATH
    found = shutil.which("pdflatex")
    if found:
        return Path(found)
    return None


class Settings(BaseSettings):
    """Runtime settings, loaded from environment and backend/.env."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        extra="ignore",
    )

    project_root: Path = PROJECT_ROOT
    backend_dir: Path = BACKEND_DIR
    model: str = "gemini/gemini-3-flash-preview"
    temperature: float = 0.2
    pdf_compile_timeout_seconds: int = 60
    pdf_latex_path: Path | None = Field(
        default=None, validation_alias="PDFLATEX_PATH"
    )

    @field_validator("pdf_latex_path", mode="before")
    @classmethod
    def normalize_pdf_latex_path(cls, raw_value: Any) -> Path | None:
        """Run the raw PDFLATEX_PATH value through the resolution chain."""
        return resolve_pdf_latex_path(raw_value)
