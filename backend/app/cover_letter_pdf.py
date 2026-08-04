"""pandoc export of cover_letter.md to cover_letter.pdf (PLAN D19/D21)."""

import asyncio
import subprocess
from pathlib import Path

from backend.app.config import Settings, resolve_pandoc_path

# Optional custom LaTeX template honored when present (PLAN D23).
_COVER_LETTER_TEMPLATE = "cover_letter_template.tex"


class CoverLetterExportError(Exception):
    """Raised when the pandoc export fails, times out, or pandoc is missing."""


async def export_cover_letter_pdf(app_dir: Path, settings: Settings) -> Path:
    """Export ``app_dir/cover_letter.md`` to ``app_dir/cover_letter.pdf``.

    Runs pandoc in a worker thread with
    ``settings.cover_letter_export_timeout_seconds`` as the timeout. The
    optional ``backend/cover_letter_template.tex`` is passed via ``--template``
    only when it exists.

    Args:
        app_dir: Application directory containing ``cover_letter.md``.
        settings: Runtime settings supplying the pandoc executable and timeout.

    Returns:
        The exported ``app_dir / cover_letter.pdf`` path.

    Raises:
        CoverLetterExportError: When pandoc is missing, the source file is
            absent, pandoc exits non-zero, or the export times out.
    """
    exe = settings.pandoc_path or resolve_pandoc_path()
    if exe is None or not exe.is_file():
        raise CoverLetterExportError("pandoc not found")
    source = app_dir / "cover_letter.md"
    if not source.is_file():
        raise CoverLetterExportError(f"Missing cover letter source: {source}")

    command = _build_command(exe, app_dir)
    try:
        await asyncio.to_thread(
            _run_pandoc,
            command,
            app_dir,
            settings.cover_letter_export_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise CoverLetterExportError(
            f"pandoc timed out after {settings.cover_letter_export_timeout_seconds}s"
        ) from exc
    return app_dir / "cover_letter.pdf"


def _build_command(exe: Path, app_dir: Path) -> list[str]:
    """Assemble the pandoc invocation, adding the template when present."""
    command = [
        str(exe),
        "cover_letter.md",
        "-o",
        "cover_letter.pdf",
        "--pdf-engine=pdflatex",
    ]
    template = app_dir / _COVER_LETTER_TEMPLATE
    if template.is_file():
        command.extend(["--template", str(template)])
    return command


def _run_pandoc(command: list[str], app_dir: Path, timeout_seconds: int) -> None:
    """Run pandoc in ``app_dir``; raise on non-zero exit or timeout."""
    result = subprocess.run(
        command,
        cwd=app_dir,
        timeout=timeout_seconds,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr_tail = result.stderr.decode(errors="replace")[-500:]
        raise CoverLetterExportError(
            f"pandoc exited with code {result.returncode}: {stderr_tail}"
        )