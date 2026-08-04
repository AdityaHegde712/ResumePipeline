"""Application settings for ResumePipeline v2.

All paths are pathlib.Path objects resolved relative to the repository root.
"""

import shutil
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]

# Load backend/.env into os.environ BEFORE Settings is constructed so the
# LLM layer (LiteLLM) sees GEMINI_API_KEY. override=False keeps env vars
# that are already set (tests set APPLICATIONS_ROOT/PDFLATEX_PATH) winning.
load_dotenv(BACKEND_DIR / ".env", override=False)

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


def resolve_pandoc_path(env_value: str | None = None) -> Path | None:
    """Resolve the pandoc executable via the PANDOC_PATH chain.

    A truthy env value is used as-is (expanded); otherwise the PATH lookup
    decides. Returns None when pandoc cannot be found anywhere.

    Args:
        env_value: Raw PANDOC_PATH value, or None to skip the env branch.

    Returns:
        Resolved Path to pandoc, or None if nothing could be resolved.
    """
    if env_value:
        return Path(env_value).expanduser()
    found = shutil.which("pandoc")
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
    applications_root: Path = Field(
        default=PROJECT_ROOT / "backend" / "data" / "applications",
        validation_alias="APPLICATIONS_ROOT",
    )
    pdf_compile_timeout_seconds: int = Field(
        default=60, validation_alias="PDF_COMPILE_TIMEOUT_SECONDS"
    )
    pdf_latex_path: Path | None = Field(
        default=None, validation_alias="PDFLATEX_PATH"
    )
    cover_letter_export_timeout_seconds: int = Field(
        default=60, validation_alias="COVER_LETTER_EXPORT_TIMEOUT_SECONDS"
    )
    pandoc_path: Path | None = Field(
        default=None, validation_alias="PANDOC_PATH"
    )

    @field_validator("pdf_latex_path", mode="before")
    @classmethod
    def normalize_pdf_latex_path(cls, raw_value: Any) -> Path | None:
        """Run the raw PDFLATEX_PATH value through the resolution chain."""
        return resolve_pdf_latex_path(raw_value)

    @field_validator("pandoc_path", mode="before")
    @classmethod
    def normalize_pandoc_path(cls, raw_value: Any) -> Path | None:
        """Run the raw PANDOC_PATH value through the resolution chain."""
        return resolve_pandoc_path(raw_value)
