# Project Status

## Phase: Debugger Remediation — LLM Error Handling Chain

### Status: ✅ COMPLETE — All 3 bugs fixed, 197/197 tests passing

---

## Bugs Fixed

### Bug #1: Streaming generation gets zero retries
- **File**: `backend/app/services/llm_service.py`
- **Root cause**: `generate()` short-circuited to `_stream_generate()` when `stream=True`, bypassing the retry loop entirely
- **Fix**: Replaced `_stream_generate()` with `_stream_generate_with_retry()` which wraps `acompletion()` + token iteration in an exponential backoff retry loop (1s, 2s, 4s). `generate()` calls the new method and passes `max_retries`.

### Bug #2: Quota/auth errors masked as LLMParseError in generate_structured()
- **File**: `backend/app/services/llm_service.py`
- **Root cause**: `except (json.JSONDecodeError, Exception)` caught `LLMRateLimitError` (and friends) and re-raised them as `LLMParseError`
- **Fix**: Narrowed to `except (json.JSONDecodeError,)` on first attempt; `except (json.JSONDecodeError, LLMParseError)` on retry. LLM errors now propagate with their correct type.

### Bug #3: Raw Python exception names exposed to users via SSE
- **File**: `backend/app/pipeline/orchestrator.py`
- **Root cause**: `error_msg = f"{type(exc).__name__}: {exc}"` sent directly to the SSE stream
- **Fix**: Added `_format_user_error()` static method mapping `LLMRateLimitError` → "quota exhausted", `LLMAuthError` → "check API key", etc. Raw error is still logged server-side and stored in `app.error_message`; user-friendly message goes to SSE.

## Code Quality (Clean-Coder)
- Removed unused imports (`Callable`, `TaskModelConfig`)
- Removed unused `last_error` variable assignments
- Replaced unused `as e` with bare `except`
- Both files reformatted with `ruff format`
- Zero `ruff check` warnings

## Tests Added (14 new tests)
- `TestLLMServiceStreaming` (5): success, retry on rate-limit, retry on connection-error, auth-no-retry, retry exhaustion
- `TestLLMServiceGenerateStructuredErrors` (4): preserves rate-limit, auth, connection errors; JSON-retry-then-rate-limit
- `TestOrchestratorErrorFormatting` (5): rate-limit, auth, connection, parse, and generic error messages

## Test Suite
- **197/197 tests passing** (183 pre-existing + 14 new)
- No production code was modified to make tests pass

## Files Modified
| File | Changes |
|------|---------|
| `backend/app/services/llm_service.py` | Added `_stream_generate_with_retry()`, removed `_stream_generate()`, narrowed exception handlers in `generate_structured()`, added nested try/except for retry of mapped errors in `generate()` |
| `backend/app/pipeline/orchestrator.py` | Added imports for error classes, `_format_user_error()` static method, updated `_handle_pipeline_error()` to send user-friendly SSE messages |
| `backend/tests/test_llm_service.py` | Added 9 tests (streaming + error preservation) |
| `backend/tests/test_orchestrator.py` | NEW — 5 tests for error formatting |
