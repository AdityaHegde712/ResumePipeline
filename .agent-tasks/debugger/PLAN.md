# Debug Plan — LLM Error Handling Remediation

**Prepared for:** Orchestrator  
**Priority:** High  
**Owner decisions:** Logged in `.agent-tasks/debugger/DECISIONS.md`  

**Sub-agents available (from `.agent-tasks/architect/AGENT_TEAM.md`):**  
- `@backend-dev` — Backend Python, FastAPI, business logic  
- `@tester` — Unit/integration testing, regression suite  
- `@clean-coder` — Code quality, linting, type hints  

---

## Task Summary

| # | Bug | File(s) | Agent | Est. Effort |
|---|-----|---------|-------|-------------|
| 1 | Streaming calls get zero retries | `backend/app/services/llm_service.py` | `@backend-dev` | ~30 min |
| 2 | Quota errors masked as `LLMParseError` | `backend/app/services/llm_service.py` | `@backend-dev` | ~10 min |
| 3 | Raw Python exception type exposed to users | `backend/app/pipeline/orchestrator.py` | `@backend-dev` | ~20 min |
| 4 | Test all fixes | `backend/tests/` | `@tester` | ~45 min |
| 5 | Code quality pass | All modified files | `@clean-coder` | ~10 min |

---

## Task 1: Add Retry Logic to Streaming Path

**Assignee:** `@backend-dev`  
**File:** `backend/app/services/llm_service.py`  

### 1.1 Replace `_stream_generate` with `_stream_generate_with_retry`

**Location:** Lines 142-166 (current `_stream_generate` method)

**Replace the entire method** with a new one that includes retry logic:

```python
async def _stream_generate_with_retry(
    self,
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    max_retries: int = 3,
) -> AsyncIterator[str]:
    """Internal streaming generator with retry for transient errors.

    Retries on ``LLMConnectionError`` and ``LLMRateLimitError`` with
    exponential backoff (1s, 2s, 4s).  Non-retriable errors (auth, parse)
    propagate immediately.

    Args:
        model: Provider/model string for LiteLLM.
        messages: Message list with system + user prompts.
        temperature: Sampling temperature.
        max_tokens: Maximum output tokens.
        max_retries: Maximum retries for transient errors (default 3).

    Yields:
        Token strings from the LLM stream.

    Raises:
        LLMConnectionError: If API unreachable after all retries.
        LLMRateLimitError: If rate limited after all retries.
        LLMAuthError: If authentication fails (not retried).
        LLMServiceError: For other LLM failures.
    """
    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            from litellm import acompletion

            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return  # Success — generator exits cleanly

        except (LLMConnectionError, LLMRateLimitError) as e:
            last_error = e
            if attempt < max_retries:
                delay = 2 ** attempt  # 1, 2, 4 seconds
                logger.warning(
                    f"Streaming LLM call failed (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)
            else:
                raise

        except Exception as e:
            # Non-retriable: auth errors, parse errors, etc.
            self._handle_error(e)
```

### 1.2 Update `generate()` to use the new method

**Location:** Lines 115-116

**Change this:**

```python
if stream:
    return self._stream_generate(model, messages, temperature, max_tokens)
```

**To this:**

```python
if stream:
    return self._stream_generate_with_retry(
        model, messages, temperature, max_tokens, max_retries,
    )
```

### 1.3 Remove old `_stream_generate` method

**Location:** Lines 142-166

After adding `_stream_generate_with_retry`, delete the old `_stream_generate` method entirely. It is replaced.

### 1.4 Verification

- Run `cd backend && uv run pytest tests/test_llm_service.py -v` — all existing LLM service tests must pass.
- Confirm no other code in the project imports or references `_stream_generate` (grep for it).

---

## Task 2: Fix Error Type Masking in `generate_structured()`

**Assignee:** `@backend-dev`  
**File:** `backend/app/services/llm_service.py`  

### 2.1 Narrow the outer except clause

**Location:** Line 195

**Change this:**

```python
except (json.JSONDecodeError, Exception) as e:
```

**To this:**

```python
except (json.JSONDecodeError, LLMParseError) as e:
```

**Rationale:** Only parsing-related errors should trigger the "fix your JSON" retry. `LLMRateLimitError`, `LLMConnectionError`, `LLMAuthError`, and `LLMServiceError` are not parsing errors — they should propagate naturally to the caller.

### 2.2 Narrow the inner except clause

**Location:** Line 208

**Change this:**

```python
except (json.JSONDecodeError, Exception) as e2:
```

**To this:**

```python
except (json.JSONDecodeError, LLMParseError) as e2:
```

**Rationale:** Same reasoning — the inner catch should match the same error types as the outer catch. Any `LLMServiceError` from the retry `generate()` call should propagate, not be wrapped in `LLMParseError`.

### 2.3 Import check

Verify that `LLMParseError` is already imported at the top of the file (line 38: `LLMParseError` is imported alongside other error classes). No import changes needed.

### 2.4 Verification

- Run `cd backend && uv run pytest tests/test_llm_service.py -v` — all existing tests must pass.
- Specifically check that any test expecting `LLMParseError` from rate-limit scenarios will now correctly get `LLMRateLimitError` instead (update those tests if they exist in Task 4).

---

## Task 3: Add User-Friendly Error Messages

**Assignee:** `@backend-dev`  
**File:** `backend/app/pipeline/orchestrator.py`  

### 3.1 Import the LLM error classes

**Location:** Top of file (after line 52)

**Add import:**

```python
from app.services.llm_service import (
    LLMAuthError,
    LLMConnectionError,
    LLMParseError,
    LLMRateLimitError,
    LLMServiceError,
)
```

### 3.2 Add `_format_user_error()` static method

**Location:** After `_infer_current_stage()` (after line 949), before the class ends.

**Add this method:**

```python
@staticmethod
def _format_user_error(exc: Exception) -> str:
    """Convert a technical exception into a user-friendly, actionable message.

    The returned string is sent via SSE to the frontend.  The original
    technical error (``f"{type(exc).__name__}: {exc}"``) is still logged
    server-side and persisted in ``app.error_message`` for diagnostics.

    Mappings::

        LLMRateLimitError  → "The AI service quota has been exhausted. "
                             "Please wait a while and try again, or check "
                             "your API plan and key limits."
        LLMAuthError       → "AI service authentication failed. Please go "
                             "to Settings and verify your API key."
        LLMConnectionError → "Could not connect to the AI service. Please "
                             "check your internet connection and try again."
        LLMParseError      → "The AI service returned an unexpected "
                             "response. Please try again."
        LLMServiceError    → "The AI service encountered an error. Please "
                             "try again."
        Exception (other)  → f"An unexpected error occurred: {exc}"
    """
    if isinstance(exc, LLMRateLimitError):
        return (
            "The AI service quota has been exhausted. "
            "Please wait a while and try again, or check your API plan and key limits."
        )
    if isinstance(exc, LLMAuthError):
        return (
            "AI service authentication failed. "
            "Please go to Settings and verify your API key."
        )
    if isinstance(exc, LLMConnectionError):
        return (
            "Could not connect to the AI service. "
            "Please check your internet connection and try again."
        )
    if isinstance(exc, LLMParseError):
        return (
            "The AI service returned an unexpected response. "
            "Please try again."
        )
    if isinstance(exc, LLMServiceError):
        return (
            "The AI service encountered an error. Please try again."
        )
    # Fallback for unexpected exception types
    return f"An unexpected error occurred: {exc}"
```

### 3.3 Update `_handle_pipeline_error()` to use user-friendly messages

**Location:** Lines 913-937

**Change the `_emit_error` call** to send the user-friendly message instead of the raw technical one:

**Current (line 936):**
```python
await self._emit_error(emit, stage, error_msg)
```

**Replace with:**
```python
user_message = self._format_user_error(exc)
await self._emit_error(emit, stage, user_message)
```

**Keep the rest unchanged.** The `error_msg` variable still holds the technical details, which are:
- Logged via `logger.exception(...)` (line 926) — stays in server logs
- Persisted in `app.error_message` (line 929) — available in the stored Application record

The SSE event sent to the frontend now carries the human-readable message instead.

### 3.4 Verification

- `cd backend && uv run pytest tests/test_api.py -v` — API tests must pass
- `cd backend && uv run pytest tests/test_phase7_regressions.py -v` — regression tests must pass

---

## Task 4: Update and Add Tests

**Assignee:** `@tester`  
**File:** `backend/tests/test_llm_service.py` (primary), possibly `backend/tests/test_api.py`  

### 4.1 Test streaming retry logic

**Add test cases to `test_llm_service.py`:**

1. **`test_streaming_retries_on_rate_limit`** — Verify that when `_stream_generate_with_retry` encounters `LLMRateLimitError`, it retries up to `max_retries` times before re-raising. Use a mock that fails N times then succeeds.

2. **`test_streaming_does_not_retry_on_auth_error`** — Verify that `LLMAuthError` in the streaming path is **not** retried (propagates immediately).

3. **`test_streaming_retry_exhaustion`** — Verify that after exhausting all retries, the last `LLMRateLimitError` propagates to the caller.

4. **`test_streaming_success_after_retry`** — Verify that a transient failure followed by a successful response yields the correct tokens.

### 4.2 Test error classification fix in `generate_structured()`

**Add/update test cases:**

1. **`test_generate_structured_passes_through_rate_limit_error`** — Verify that when `generate()` raises `LLMRateLimitError`, `generate_structured()` does **not** catch it — it propagates as `LLMRateLimitError` (not `LLMParseError`).

2. **`test_generate_structured_passes_through_auth_error`** — Same for `LLMAuthError`.

3. **`test_generate_structured_retries_on_parse_error`** — Verify that genuine `json.JSONDecodeError` still triggers the "fix your JSON" retry.

### 4.3 Test user-friendly error mapping

**Add test cases to `test_llm_service.py` or a new section in `test_phase7_regressions.py`:**

1. **`test_format_user_error_rate_limit`** — Call `Orchestrator._format_user_error(LLMRateLimitError("test"))` and assert the result contains "quota" and does not contain "LLMRateLimitError".

2. **`test_format_user_error_auth`** — Same for `LLMAuthError`, assert result contains "API key".

3. **`test_format_user_error_connection`** — Same for `LLMConnectionError`, assert result contains "internet connection".

4. **`test_format_user_error_parse`** — Same for `LLMParseError`.

5. **`test_format_user_error_unknown`** — Same for a plain `Exception`, assert result contains the original error message.

### 4.4 Regression check

Run the full test suite:
```bash
cd backend && uv run pytest -v
```

Confirm all 184+ tests pass with no regressions.

---

## Task 5: Code Quality Pass

**Assignee:** `@clean-coder`  
**Files:** `backend/app/services/llm_service.py`, `backend/app/pipeline/orchestrator.py`, `backend/tests/test_llm_service.py`  

### 5.1 Linting & formatting

```bash
cd backend
uv run ruff check --fix app/services/llm_service.py app/pipeline/orchestrator.py
uv run ruff format app/services/llm_service.py app/pipeline/orchestrator.py
```

### 5.2 Type hints

- Verify all new methods have complete type annotations.
- Verify the `_stream_generate_with_retry` method signature matches the existing code style (return type `AsyncIterator[str]`).
- Remove the old `_stream_generate` method completely (no dead code).

---

## Execution Order

```
Task 1: @backend-dev  ─────────────────────── llm_service.py streaming retry
        │
Task 2: @backend-dev  ─────────────────────── llm_service.py error masking fix
        │
Task 3: @backend-dev  ─────────────────────── orchestrator.py user-friendly messages
        │
        (Tasks 1-3 are independent — can run in parallel)
        │
Task 4: @tester       ─────────────────────── test all fixes + regression suite
        │
Task 5: @clean-coder  ─────────────────────── code quality pass on modified files
```

---

## Rollback Plan

Each fix is in a separate logical change. If any fix causes a regression:

1. Revert the specific commit/task (not the entire plan).
2. Inform the Orchestrator which task was reverted and why.
3. The remaining tasks hold independently.
