"""pdflatex compilation: two passes, timeout, aux cleanup (PLAN D11)."""

import asyncio
import subprocess
from pathlib import Path

from backend.app.config import Settings

# Compile artifacts removed after a successful second pass (kept: resume.tex).
_ARTIFACT_SUFFIXES = (".aux", ".log", ".out")


class PDFCompileError(Exception):
    """Raised when the LaTeX compile fails or times out."""


async def compile_resume(settings: Settings, app_dir: Path) -> Path:
    """Compile ``app_dir/resume.tex`` to ``app_dir/resume.pdf`` (two passes).

    Runs ``settings.pdf_latex_path`` in a worker thread with
    ``settings.pdf_compile_timeout_seconds`` as the per-pass timeout, then
    removes the ``.aux``/``.log``/``.out`` artifacts on success.

    Args:
        settings: Runtime settings supplying the pdflatex executable and
            the compile timeout.
        app_dir: Application directory containing ``resume.tex``.

    Returns:
        The compiled ``app_dir / resume.pdf`` path.

    Raises:
        PDFCompileError: When pdflatex is missing, the source file is
            absent, a pass exits non-zero, or a pass times out.
    """
    exe = settings.pdf_latex_path
    if exe is None or not exe.is_file():
        raise PDFCompileError(f"pdflatex executable not found: {exe}")
    tex_path = app_dir / "resume.tex"
    if not tex_path.is_file():
        raise PDFCompileError(f"Missing LaTeX source: {tex_path}")

    # Two passes resolve hyperref anchors; each pass gets the full timeout.
    try:
        for _ in range(2):
            await asyncio.to_thread(
                _run_pdflatex_pass,
                exe,
                app_dir,
                settings.pdf_compile_timeout_seconds,
            )
    except subprocess.TimeoutExpired as exc:
        raise PDFCompileError(
            f"pdflatex timed out after {settings.pdf_compile_timeout_seconds}s"
        ) from exc

    _remove_artifacts(app_dir)
    return app_dir / "resume.pdf"


def _run_pdflatex_pass(exe: Path, app_dir: Path, timeout_seconds: int) -> None:
    """Run one pdflatex pass in ``app_dir``; raise on non-zero exit."""
    result = subprocess.run(
        [str(exe), "resume.tex"],
        cwd=app_dir,
        timeout=timeout_seconds,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr_tail = result.stderr.decode(errors="replace")[-500:]
        raise PDFCompileError(
            f"pdflatex exited with code {result.returncode}: {stderr_tail}"
        )


def _remove_artifacts(app_dir: Path) -> None:
    """Delete per-pass artifacts for ``resume``, keeping the tex source."""
    for suffix in _ARTIFACT_SUFFIXES:
        artifact = app_dir / f"resume{suffix}"
        if artifact.is_file():
            artifact.unlink()
