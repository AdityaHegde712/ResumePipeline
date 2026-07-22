# Debugger Decisions — LLM Error Handling Audit

**Date:** 2026-07-01
**Owner consulted:** Yes
**Owner decision profile:** Conservative mode (Alignment scores < 50)

---

## Bugs Identified & Resolutions

### Bug #1: Streaming Calls Get Zero Retries on Rate-Limit/Quota Errors

**Location:** `backend/app/services/llm_service.py`, lines 115-116
**Root cause:** `generate()` returns `self._stream_generate(...)` immediately when `stream=True`, bypassing the retry loop entirely. All other LLM calls get up to 3 retries with exponential backoff.
**Impact:** Bullet-point generation (the most expensive pipeline stage) has zero resilience to transient quota/rate-limit errors.
**Decision:** Fix to add retry logic to the streaming path.
**Approach:** Single viable approach — create `_stream_generate_with_retry()` in `LLMService` that wraps the `acompletion()` call in the same retry loop pattern as the non-streaming path, then yields tokens from the response. `generate()` routes to this instead of `_stream_generate()` when `stream=True`.

---

### Bug #2: Quota Errors Masked as `LLMParseError` in `generate_structured()`

**Location:** `backend/app/services/llm_service.py`, lines 195 and 208
**Root cause:** `generate_structured()` uses `except (json.JSONDecodeError, Exception)` which catches `LLMRateLimitError` and other `LLMServiceError` subclasses. These are then re-raised as misleading `LLMParseError` after the "fix your JSON" retry fails.
**Impact:** Project matching and keyword analysis stages show confusing "parse error" messages when the real problem is quota exhaustion.
**Decision:** Fix to let `LLMServiceError` subclasses propagate naturally.
**Approach:** Single viable approach — narrow both `except` clauses to `(json.JSONDecodeError, LLMParseError)` so genuine `LLMServiceError` types (`LLMRateLimitError`, `LLMAuthError`, `LLMConnectionError`) pass through uncaught.

---

### Bug #3: Raw Python Exception Type Exposed to Users

**Location:** `backend/app/pipeline/orchestrator.py`, line 925
**Root cause:** `_handle_pipeline_error()` formats errors as `f"{type(exc).__name__}: {exc}"` and sends this verbatim through SSE events to the frontend.
**Impact:** Users see technical Python exception names (`LLMRateLimitError`, `LLMAuthError`) with no actionable guidance.
**Decision:** Add backend-side error message mapping. Frontend stays unchanged.
**Approach:** Selected option A (backend mapping — recommended). Add `_format_user_error()` static method in `Orchestrator` that maps exception types to human-readable, actionable messages. The SSE `error` event sends the user-friendly message. The raw technical message is still logged server-side and persisted in `app.error_message`.

---
