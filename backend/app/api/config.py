"""
LLM configuration and PDF availability endpoints.

Provides runtime access to the current LLM provider/model settings and a
health-check endpoint for PDF (pdflatex) compilation support.

.. note::

   LLM configuration is stored **in-memory only** in v1.0 and is not persisted
   across server restarts.
"""

from fastapi import APIRouter
from app.models.generation import LLMConfig

router = APIRouter()

# In-memory configuration singleton — reset on every server restart.
_llm_config: LLMConfig | None = None


def get_llm_config() -> LLMConfig:
    """Return the shared ``LLMConfig``, initialising it from ``settings`` on
    first access.

    The default model name is stripped of any ``"gemini/"`` prefix that may
    be present in the ``settings.llm_default_model`` environment variable so
    that downstream consumers receive a clean model identifier.
    """
    global _llm_config
    if _llm_config is None:
        from app.config import settings

        _llm_config = LLMConfig(
            default_provider="gemini",
            default_model=settings.llm_default_model.replace("gemini/", ""),
            tasks={},
        )
    return _llm_config


@router.get("/llm")
async def get_llm_config_endpoint() -> LLMConfig:
    """Get the current LLM configuration.

    Returns:
        The active ``LLMConfig`` with default provider, model, and optional
        per-task model overrides.
    """
    return get_llm_config()


@router.put("/llm")
async def update_llm_config(config: LLMConfig) -> LLMConfig:
    """Update the LLM configuration (in-memory only).

    Accepts a full ``LLMConfig`` payload and replaces the current in-memory
    configuration.  Changes are **not** persisted to disk and will be lost
    when the server restarts.

    Args:
        config: The complete ``LLMConfig`` object to apply.

    Returns:
        The newly applied ``LLMConfig`` as confirmation.
    """
    global _llm_config
    _llm_config = config
    return _llm_config


@router.get("/pdf-available")
async def is_pdf_available() -> dict:
    """Check whether PDF compilation (pdflatex) is configured and the binary
    exists on disk.

    Creates a temporary ``PDFCompiler`` instance and delegates to its
    ``is_available()`` method, which checks that ``settings.pdflatex_path``
    points to an existing file.

    Returns:
        A dictionary with a single boolean key ``"available"``.
    """
    from pathlib import Path

    from app.config import settings
    from app.pipeline.pdf_compiler import PDFCompiler

    compiler = PDFCompiler(settings.pdflatex_path, Path("./temp_pdf"))
    return {"available": compiler.is_available()}
