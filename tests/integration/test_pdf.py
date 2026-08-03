"""Integration tests for pdflatex compilation (T12, Phase 7).

MUTABLE contract — ``backend/app/pdf.py`` must satisfy this file. The
implementation phase may adjust this file only on proven necessity, never
by weakening the timeout or cleanup guarantees.

Locked pdf module contract (PLAN D11):

    class PDFCompileError(Exception):
        \"\"\"Raised when the LaTeX compile fails or times out.\"\"\"

    async def compile_resume(settings: Settings, app_dir: Path) -> Path:
        \"\"\"Compile app_dir/resume.tex to app_dir/resume.pdf (two passes).

        Returns the resume.pdf Path on success. The compile runs in a
        thread with settings.pdf_compile_timeout_seconds as the per-call
        timeout, removes .aux/.log/.out on success, and keeps resume.tex.
        Raises PDFCompileError when pdflatex is missing, the compile exits
        non-zero, or the timeout elapses.
        \"\"\"

The executable comes from ``settings.pdf_latex_path`` (the PDFLATEX_PATH
resolution chain in backend/app/config.py); a missing tex engine is the
caller's PDFCompileError, never a silent skip inside the module.

Tests that exercise a real TeX engine are skipped when no pdflatex can be
resolved (via ``settings.pdf_latex_path`` or PATH). The timeout test uses
a fake slow executable, so it always runs. All tests use pytest
``tmp_path``; the real ``backend/data/applications`` is never touched.
"""

import shutil
from pathlib import Path

import pytest

from backend.app.config import Settings
from backend.app.pdf import PDFCompileError, compile_resume
from backend.app.storage import create_application_dir

EXAMPLE_APPLICATION_ID = "application-20260802-143045"

MINIMAL_TEX = (
    "\\documentclass{article}\n"
    "\\begin{document}\n"
    "ResumePipeline v2 test\n"
    "\\end{document}\n"
)

AUX_SUFFIXES = (".aux", ".log", ".out")


def _pdflatex_available() -> bool:
    """True when a real pdflatex executable can be resolved."""

    settings = Settings()
    resolved = settings.pdf_latex_path
    if resolved is not None and resolved.is_file():
        return True
    return shutil.which("pdflatex") is not None


REQUIRES_PDFLATEX = pytest.mark.skipif(
    not _pdflatex_available(),
    reason="pdflatex not found (set PDFLATEX_PATH or install a TeX engine)",
)


@REQUIRES_PDFLATEX
class TestPdfCompileRealLatex:
    """End-to-end compile against a real TeX engine."""

    async def test_minimal_tex_compiles_to_pdf(self, tmp_path: Path) -> None:
        """A minimal valid document produces a non-empty resume.pdf."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        (app_dir / "resume.tex").write_text(MINIMAL_TEX, encoding="utf-8")

        pdf_path = await compile_resume(Settings(), app_dir)

        assert pdf_path == app_dir / "resume.pdf"
        assert pdf_path.is_file()
        assert pdf_path.stat().st_size > 0

    async def test_cleanup_removes_aux_log_out_keeps_tex(self, tmp_path: Path) -> None:
        """Compile artifacts are removed on success; the source stays."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        (app_dir / "resume.tex").write_text(MINIMAL_TEX, encoding="utf-8")

        pdf_path = await compile_resume(Settings(), app_dir)

        assert pdf_path.is_file()
        assert (app_dir / "resume.tex").is_file()
        for aux_suffix in AUX_SUFFIXES:
            assert not (app_dir / f"resume{aux_suffix}").exists()


class TestPdfCompileTimeout:
    """Timeout behaviour uses a fake slow executable, no TeX engine needed."""

    async def test_timeout_raises_pdf_compile_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A compile exceeding the timeout raises PDFCompileError."""

        fake_latex = tmp_path / "fake_pdflatex.cmd"
        fake_latex.write_text(
            "@echo off\r\nping -n 4 127.0.0.1 >nul\r\nexit /b 0\r\n",
            encoding="utf-8",
        )
        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        (app_dir / "resume.tex").write_text(MINIMAL_TEX, encoding="utf-8")
        monkeypatch.setenv("PDFLATEX_PATH", str(fake_latex))
        monkeypatch.setenv("PDF_COMPILE_TIMEOUT_SECONDS", "1")

        with pytest.raises(PDFCompileError):
            await compile_resume(Settings(), app_dir)
