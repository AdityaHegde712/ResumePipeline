# Plan: PDFCompiler Implementation

## Task
Create `backend/app/pipeline/pdf_compiler.py` implementing the `PDFCompiler` class
that wraps MiKTeX's `pdflatex.exe`.

## Why General-Builder?
This is a standalone utility component that bridges system-level subprocess
management (MiKTeX) with the FastAPI application layer. It is not purely
backend (no DB/routes), not frontend, and not ML — a cross-cutting build task
best suited for the generalist agent.

## Design

### Components
1. **`PDFResult`** — Pydantic `BaseModel` for compilation results
2. **`PDFCompiler`** — Main class wrapping pdflatex
3. **Error classes** — `PDFCompilerUnavailableError`, `PDFCompilerTimeoutError`,
   `PDFCompilerError`

### Compilation flow
1. Write `.tex` file (UTF-8)
2. Run 3-pass `pdflatex -interaction=nonstopmode` with 30s timeout per pass
3. Parse `.log` for errors, warnings, page count
4. Verify `.pdf` exists and > 0 bytes
5. On success: read bytes, clean up intermediates (`.aux`, `.log`, `.out`, `.toc`)
6. On failure: return `PDFResult(success=False, ...)` or raise on timeout

### Key decisions
- Use `asyncio.create_subprocess_exec` for async subprocess management
- Set `MIKTEX_AUTOINSTALL=1` in subprocess env for MiKTeX auto-package-install
- `get_compiler_version()` uses synchronous `subprocess.run` (diagnostic tool)
- Retry logic in `compile_with_retry` only retries timeouts and zero-byte PDFs
  (not deterministic LaTeX errors)

## Files
- **Create**: `backend/app/pipeline/pdf_compiler.py` (~320 lines)
- **Create**: `.agent-tasks/general-builder/STATUS.md` (this plan)
