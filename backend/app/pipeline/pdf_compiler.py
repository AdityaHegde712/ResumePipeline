"""
PDF Compiler — wraps MiKTeX's ``pdflatex.exe`` to compile LaTeX to PDF.

This is an **optional** component called separately from the Export API
endpoint. It is NOT part of the core generation pipeline.

Usage::

    compiler = PDFCompiler(pdflatex_path="/usr/bin/pdflatex",
                           output_dir=Path("./tmp"))
    result = await compiler.compile(tex_content, filename="resume")
    if result.success:
        serve_bytes = result.pdf_bytes
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess  # used only in get_compiler_version (sync call)
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ── Error classes ──────────────────────────────────────────────────────────


class PDFCompilerUnavailableError(Exception):
    """Raised when ``pdflatex`` is not configured or the binary is missing."""


class PDFCompilerTimeoutError(Exception):
    """Raised when a ``pdflatex`` subprocess exceeds the allowed timeout."""


class PDFCompilerError(Exception):
    """Raised for general compilation failures (wraps stderr / non-zero exit)."""


# ── Result model ───────────────────────────────────────────────────────────


class PDFResult(BaseModel):
    """Result of a PDF compilation attempt.

    Attributes:
        success: ``True`` if the PDF was produced and is non-empty.
        pdf_path: Path to the compiled PDF on disk (only when *success*).
        pdf_bytes: Raw bytes of the compiled PDF, ready for HTTP serving.
        log: Full ``pdflatex`` log content (all three passes concatenated).
        errors: Parsed error messages extracted from the log.
        warnings: Parsed warning messages extracted from the log.
        page_count: Number of pages in the PDF, if parseable from the log.
    """

    success: bool
    pdf_path: Optional[Path] = None
    pdf_bytes: Optional[bytes] = None
    log: str = ""
    errors: list[str] = []
    warnings: list[str] = []
    page_count: Optional[int] = None


# ── Compiler ───────────────────────────────────────────────────────────────


# Default timeout per pdflatex pass (seconds).
_PDFLATEX_TIMEOUT: float = 30.0


class PDFCompiler:
    """Compiles LaTeX source to PDF using MiKTeX's ``pdflatex``.

    The compiler performs a standard **three-pass** sequence to resolve
    cross-references, table of contents entries, page numbers, etc.

    When *pdflatex_path* is ``None`` or an empty string ``is_available()``
    returns ``False`` and any call to ``compile()`` raises
    :class:`PDFCompilerUnavailableError`.

    .. code-block:: python

        compiler = PDFCompiler(
            pdflatex_path="C:/texlive/.../pdflatex.exe",
            output_dir=Path("./tmp"),
        )
        result = await compiler.compile(tex_content, filename="resume")
        if result.success:
            pdf_bytes = result.pdf_bytes

    All temporary files (``.tex``, ``.aux``, ``.log``, ``.out``, ``.toc``) are
    written inside *output_dir*.  Intermediate files are removed after a
    successful compilation; the original ``.tex`` is kept.
    """

    # File extensions generated during a typical pdflatex run that should be
    # cleaned up on success.  The ``.tex`` source is preserved.
    _INTERMEDIATE_EXTS: tuple[str, ...] = (".aux", ".log", ".out", ".toc")

    # ── Log-parsing regular expressions ────────────────────────────────────

    # Lines beginning with "!" at column 0 are LaTeX errors.
    _ERROR_RE: re.Pattern = re.compile(r"^!\s+(.+)$", re.MULTILINE)

    # Three categories of warning:
    #   1. "LaTeX Warning: ..."
    #   2. "Package <name> Warning: ..."
    #   3. "Overfull/Underfull \\hbox ..."
    _WARNING_RE: re.Pattern = re.compile(
        r"^(?:"
        r"LaTeX\s+Warning:\s+(.*)"
        r"|"
        r"Package\s+\S+\s+Warning:\s+(.*)"
        r"|"
        r"((?:Overfull|Underfull)\s+\\hbox.*)"
        r")",
        re.MULTILINE,
    )

    # Output line:  Output written on "resume.pdf" (1 page, 12345 bytes).
    _PAGE_COUNT_RE: re.Pattern = re.compile(
        r"Output\s+written\s+on\s+.+?\s+\((\d+)\s+page",
        re.MULTILINE | re.IGNORECASE,
    )

    # ── Initialisation ─────────────────────────────────────────────────────

    def __init__(
        self,
        pdflatex_path: str | Path | None,
        output_dir: Path,
    ) -> None:
        """Initialise the PDF compiler.

        Args:
            pdflatex_path: Absolute or relative path to ``pdflatex``
                (``pdflatex.exe`` on Windows).  Accepts ``str``, ``Path``, or
                ``None``.  When ``None`` or an empty string, compilation is
                disabled.
            output_dir: Directory where temporary ``.tex``, log files, and the
                final ``.pdf`` will be written.  Created recursively if it does
                not exist.
        """
        self._raw_path: str | Path | None = pdflatex_path
        self._pdflatex_path: Optional[Path] = None

        if pdflatex_path:
            resolved = Path(str(pdflatex_path)).resolve()
            if resolved.exists():
                self._pdflatex_path = resolved

        self._output_dir: Path = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(
            "PDFCompiler initialised: pdflatex=%s, output=%s",
            self._pdflatex_path or "(unavailable)",
            self._output_dir,
        )

    # ── Public API ─────────────────────────────────────────────────────────

    async def compile(
        self,
        tex_content: str,
        filename: str = "resume",
    ) -> PDFResult:
        """Compile LaTeX source to PDF via a three-pass ``pdflatex`` run.

        The pipeline is:

        1. Write *tex_content* to ``{filename}.tex`` inside *output_dir*
           (UTF-8 encoded).
        2. Execute three passes of ``pdflatex -interaction=nonstopmode``,
           each with a 30-second timeout.
        3. Read the combined ``.log`` file and parse errors, warnings, and
           page count.
        4. Verify the output ``.pdf`` exists and is non-empty.
        5. On success, read the PDF bytes and clean up intermediate files.

        Args:
            tex_content: Complete LaTeX document as a string (UTF-8).
            filename: Base name for all output files (without extension).
                      Defaults to ``"resume"``.

        Returns:
            A :class:`PDFResult` with the compilation outcome.

        Raises:
            PDFCompilerUnavailableError: When ``pdflatex`` is not configured
                or the binary does not exist on disk.
            PDFCompilerTimeoutError: When any single ``pdflatex`` pass exceeds
                the 30-second timeout.  The subprocess is killed before the
                exception propagates.
        """
        if not self.is_available():
            raise PDFCompilerUnavailableError(
                "pdflatex is not available — either the path was not provided "
                "or the binary does not exist.  "
                f"Configured path: {self._raw_path!r}"
            )

        tex_path = self._output_dir / f"{filename}.tex"
        pdf_path = self._output_dir / f"{filename}.pdf"

        # ── 1. Write the .tex source (UTF-8) ───────────────────────────────
        tex_path.write_text(tex_content, encoding="utf-8")
        tex_size = tex_path.stat().st_size
        logger.info("Wrote temporary .tex: %s (%d bytes)", tex_path, tex_size)

        if tex_size == 0:
            return PDFResult(
                success=False,
                log="Source .tex file is empty.",
                errors=["Empty .tex source — nothing to compile."],
            )

        # ── 2. Three-pass compilation ──────────────────────────────────────
        full_log_parts: list[str] = []

        for pass_num in (1, 2, 3):
            logger.debug("pdflatex pass %d/3 for '%s'", pass_num, filename)
            try:
                return_code = await self._run_pdflatex(filename)
            except asyncio.TimeoutError:
                raise PDFCompilerTimeoutError(
                    f"pdflatex pass {pass_num}/3 timed out after "
                    f"{_PDFLATEX_TIMEOUT}s for file {filename!r}"
                )

            # Read the .log file that pdflatex produced on this pass.
            log_path = self._output_dir / f"{filename}.log"
            pass_log = self._read_log(log_path)
            full_log_parts.append(pass_log)

            if return_code != 0:
                logger.warning(
                    "pdflatex pass %d/3 exited with code %d for '%s'",
                    pass_num,
                    return_code,
                    filename,
                )
                # Continue passes — pdflatex often exits non-zero on early
                # passes when cross-references are still undefined but the
                # final pass still produces a valid PDF.

        # ── 3. Parse the combined log ──────────────────────────────────────
        combined_log = "\n".join(full_log_parts)
        errors = self._parse_errors(combined_log)
        warnings = self._parse_warnings(combined_log)
        page_count = self._parse_page_count(combined_log)

        # ── 4. Verify the output PDF ───────────────────────────────────────
        pdf_bytes: Optional[bytes] = None
        success = False

        if pdf_path.exists():
            pdf_size = pdf_path.stat().st_size
            if pdf_size > 0:
                pdf_bytes = pdf_path.read_bytes()
                success = True
                logger.info(
                    "PDF compilation successful: %s (%d page(s), %d bytes)",
                    pdf_path,
                    page_count or 0,
                    pdf_size,
                )
                # ── 5. Clean up intermediate files on success ─────────────
                self._cleanup_intermediates(filename)
            else:
                logger.error(
                    "PDF compilation failed — output %s is zero bytes",
                    pdf_path,
                )
                errors.append(
                    "Compiled PDF is zero bytes — compilation did not produce "
                    "valid output."
                )
        else:
            logger.error(
                "PDF compilation failed — output %s does not exist",
                pdf_path,
            )
            errors.append(
                "Compiled PDF not found — compilation did not produce output."
            )

        return PDFResult(
            success=success,
            pdf_path=pdf_path if success else None,
            pdf_bytes=pdf_bytes,
            log=combined_log,
            errors=errors,
            warnings=warnings,
            page_count=page_count,
        )

    async def compile_with_retry(
        self,
        tex_content: str,
        filename: str = "resume",
        max_retries: int = 2,
    ) -> PDFResult:
        """Compile LaTeX with automatic retries on transient failures.

        Transient failures include:
        * Subprocess timeouts (heavy system load).
        * Zero-byte or missing PDF produced despite a clean log.

        **Deterministic** errors — such as LaTeX syntax errors, undefined
        references, or missing packages — are **never** retried because they
        will fail identically on every attempt.

        Args:
            tex_content: Complete LaTeX document as a string (UTF-8).
            filename: Base name for output files (default ``"resume"``).
            max_retries: Maximum number of **additional** attempts after the
                first failure (default 2, so up to 3 total attempts).

        Returns:
            :class:`PDFResult` from the first successful compilation, or the
            last failure result if all retries are exhausted.

        Raises:
            PDFCompilerUnavailableError: If the compiler is not available
                (raised immediately, **not** retried).
            PDFCompilerTimeoutError: If all attempts timed out.
            PDFCompilerError: If all attempts completed without success but
                without timeout (e.g. persistent zero-byte PDF).
        """
        if not self.is_available():
            raise PDFCompilerUnavailableError(
                "pdflatex is not available — cannot retry compilation.  "
                f"Configured path: {self._raw_path!r}"
            )

        last_exc: Optional[Exception] = None
        attempt = 0

        while attempt <= max_retries:
            try:
                result = await self.compile(tex_content, filename=filename)
            except PDFCompilerTimeoutError as exc:
                last_exc = exc
                logger.warning(
                    "Compilation attempt %d/%d timed out — retrying "
                    "(%d remaining)",
                    attempt + 1,
                    max_retries + 1,
                    max_retries - attempt,
                )
                attempt += 1
                continue

            # Successful — return immediately.
            if result.success:
                return result

            # LaTeX errors → deterministic, do not retry.
            if result.errors:
                logger.info(
                    "Compilation returned %d LaTeX error(s) on attempt %d/%d "
                    "— not retrying (deterministic failure)",
                    len(result.errors),
                    attempt + 1,
                    max_retries + 1,
                )
                return result

            # No errors but also no PDF — possibly transient (e.g. disk I/O
            # glitch or anti-virus interference on Windows).
            logger.warning(
                "Compilation attempt %d/%d produced no PDF (missing or "
                "zero-byte) with no errors — retrying",
                attempt + 1,
                max_retries + 1,
            )
            attempt += 1

        # ── All retries exhausted ──────────────────────────────────────────
        if last_exc is not None:
            raise PDFCompilerTimeoutError(
                f"Compilation failed after {max_retries + 1} attempt(s) — "
                f"all timed out.  Last error: {last_exc}"
            )

        raise PDFCompilerError(
            f"Compilation failed after {max_retries + 1} attempt(s) — "
            f"PDF could not be produced.  "
            f"Check the log and LaTeX source for issues."
        )

    def is_available(self) -> bool:
        """Return ``True`` if ``pdflatex`` is configured and the file exists.

        Returns:
            ``True`` when the compiler binary is ready to be invoked.
        """
        return self._pdflatex_path is not None

    def get_compiler_version(self) -> str:
        """Return the first line of ``pdflatex --version`` output.

        This method uses a **synchronous** subprocess call because it is
        intended for one-off diagnostic use (startup logging, health checks).

        Returns:
            Version string, e.g. ``"MiKTeX-pdflatex 4.10 (MiKTeX 23.5)"``,
            or ``"unknown"`` if the version could not be retrieved.

        Raises:
            PDFCompilerUnavailableError: If the binary is not available.
        """
        if not self.is_available():
            raise PDFCompilerUnavailableError(
                "Cannot retrieve compiler version — pdflatex is not available."
            )

        try:
            # Synchronous call — simpler for a one-line diagnostic utility.
            result = subprocess.run(
                [str(self._pdflatex_path), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            first_line = result.stdout.split("\n")[0].strip()
            logger.debug("pdflatex version: %s", first_line)
            return first_line if first_line else "unknown"
        except FileNotFoundError:
            logger.warning("pdflatex binary not found at %s", self._pdflatex_path)
            return "unknown"
        except subprocess.TimeoutExpired:
            logger.warning("pdflatex --version timed out")
            return "unknown"
        except Exception as exc:
            logger.warning("Failed to retrieve pdflatex version: %s", exc)
            return "unknown"

    # ── Private helpers ────────────────────────────────────────────────────

    async def _run_pdflatex(self, filename: str) -> int:
        """Execute a single ``pdflatex`` pass.

        Args:
            filename: Base name of the ``.tex`` file (without extension).

        Returns:
            Process return code (0 on success, non-zero on failure).

        Raises:
            asyncio.TimeoutError: If the process does not complete within
                ``_PDFLATEX_TIMEOUT`` seconds.  The subprocess is killed
                before the exception propagates.
        """
        tex_file = f"{filename}.tex"
        args = [
            str(self._pdflatex_path),
            "-interaction=nonstopmode",
            tex_file,
        ]

        # Enable MiKTeX's automatic package installation.
        env = os.environ.copy()
        env["MIKTEX_AUTOINSTALL"] = "1"

        logger.debug("Running: %s (cwd=%s)", " ".join(args), self._output_dir)

        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(self._output_dir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            _, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=_PDFLATEX_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "pdflatex process for '%s' timed out after %ss — killing",
                filename,
                _PDFLATEX_TIMEOUT,
            )
            try:
                process.kill()
                # Await the killed process to clean up the zombie.
                await process.wait()
            except ProcessLookupError:
                pass
            raise

        return process.returncode if process.returncode is not None else -1

    # ── Log helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _read_log(log_path: Path) -> str:
        """Read a ``pdflatex`` log file with graceful encoding fallback.

        Args:
            log_path: Path to the ``.log`` file.

        Returns:
            Log content as a string, or ``""`` if the file cannot be read.
        """
        try:
            return log_path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            logger.debug("Log file not found (may be expected on early pass): %s", log_path)
            return ""
        except Exception as exc:
            logger.warning("Failed to read log file %s: %s", log_path, exc)
            return ""

    @staticmethod
    def _parse_errors(log: str) -> list[str]:
        """Extract distinct LaTeX error messages from the log.

        LaTeX errors begin with ``!`` at column 0.  Only the first line of
        each error is captured (e.g. ``"Undefined control sequence."``).

        Args:
            log: Full ``pdflatex`` log content (all passes).

        Returns:
            Deduplicated list of error message strings.
        """
        if not log:
            return []
        matches = PDFCompiler._ERROR_RE.findall(log)
        seen: set[str] = set()
        errors: list[str] = []
        for msg in matches:
            clean = msg.split("\n")[0].strip()
            if clean and clean not in seen:
                seen.add(clean)
                errors.append(clean)
        return errors

    @staticmethod
    def _parse_warnings(log: str) -> list[str]:
        """Extract distinct LaTeX warnings from the log.

        Captures three types of warning:
        * ``LaTeX Warning: ...``
        * ``Package <name> Warning: ...``
        * ``Overfull/Underfull \\hbox ...``

        Args:
            log: Full ``pdflatex`` log content (all passes).

        Returns:
            Deduplicated list of warning message strings.
        """
        if not log:
            return []
        matches = PDFCompiler._WARNING_RE.findall(log)
        seen: set[str] = set()
        warnings: list[str] = []
        for groups in matches:
            # The regex captures three groups; pick the first non-empty one.
            msg = next((g for g in groups if g and g.strip()), "")
            clean = msg.strip()
            if clean and clean not in seen:
                seen.add(clean)
                warnings.append(clean)
        return warnings

    @staticmethod
    def _parse_page_count(log: str) -> Optional[int]:
        """Parse the page count from the ``pdflatex`` log.

        Looks for the standard output line::

            Output written on "resume.pdf" (1 page, 12345 bytes).

        Args:
            log: Full ``pdflatex`` log content (all passes).

        Returns:
            Page count integer, or ``None`` if it could not be determined.
        """
        if not log:
            return None
        match = PDFCompiler._PAGE_COUNT_RE.search(log)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                pass
        return None

    # ── Cleanup ────────────────────────────────────────────────────────────

    def _cleanup_intermediates(self, filename: str) -> None:
        """Delete auxiliary files produced during compilation.

        Called **only** after a successful compilation.  The ``.tex`` source
        and the final ``.pdf`` are preserved.

        Removed extensions: ``.aux``, ``.log``, ``.out``, ``.toc``.

        Args:
            filename: Base name of the compiled file (without extension).
        """
        for ext in self._INTERMEDIATE_EXTS:
            path = self._output_dir / f"{filename}{ext}"
            try:
                if path.exists():
                    path.unlink()
                    logger.debug("Cleaned up intermediate file: %s", path)
            except Exception as exc:
                logger.warning(
                    "Failed to remove intermediate file %s: %s", path, exc
                )
