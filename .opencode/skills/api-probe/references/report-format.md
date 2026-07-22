# Report Format — API_TEST_RESULTS.md

Canonical structure for the report written to `.agent-tasks/API_TEST_RESULTS.md`.
The `write_report.py` script follows this template exactly. Do not deviate.

---

## File Header

```markdown
# API Test Results

**Generated:** <ISO 8601 timestamp>
**Base URL:** <base_url>
**Discovery source:** <CODEBASE.md | <filename> | tree-sitter AST scan>
**Endpoints tested:** <N>
**Passed:** <N> | **Failed:** <N> | **Skipped:** <N> | **Flaky (recovered):** <N>

---
```

---

## Summary Table

Immediately after the header:

```markdown
## Summary

| Method | Path | Status | Result | Notes |
|--------|------|--------|--------|-------|
| GET | /users | 200 | ✅ Pass | |
| POST | /users | 201 | ✅ Pass | Payload inferred from UserCreate model |
| GET | /users/{id} | 200 | ✅ Pass | Path param substituted: id=1 |
| DELETE | /users/{id} | 401 | ⚠️ Auth-gated | No auth token in env |
| POST | /items | 500 | ❌ Fail | Retried once — still 500 |
| POST | /upload | — | ⏭️ Skipped | File upload — manual test required |
| GET | /ws | — | ⏭️ Skipped | WebSocket endpoint |
```

Result values and their meanings:

| Symbol | Label | Meaning |
|---|---|---|
| ✅ | Pass | 2xx on first attempt |
| 🔁 | Flaky | Failed attempt 1, passed attempt 2 (retry) |
| ⚠️ | Auth-gated | Got 401/403; no auth env var present |
| ❌ | Fail | Non-2xx on both attempts |
| ⏭️ | Skipped | File upload, WebSocket, or SSE |
| 🔌 | No connection | Server not responding |

---

## Per-Endpoint Detail Sections

After the summary table, one collapsible section per non-passing endpoint
(failures, flaky, auth-gated). Passing endpoints do not need detail sections
unless they had interesting notes (e.g. redirect followed).

```markdown
---

## Endpoint Details

### ❌ POST /items — Attempt Log

**Attempt 1**
- Sent: `POST http://localhost:8000/items`
- Payload:
  ```json
  { "name": "test", "price": 1.0, "category_id": 1 }
  ```
- Response status: `500 Internal Server Error`
- Response body (truncated to 500 chars):
  ```
  {"detail": "relation \"items\" does not exist"}
  ```
- Error type: Server error (5xx)

**Attempt 2 (retry after 1.5s)**
- Same payload
- Response status: `500 Internal Server Error`
- Response body: Same as attempt 1
- **Result: FAILED**

---

### 🔁 GET /users/{id} — Attempt Log

**Attempt 1**
- Sent: `GET http://localhost:8000/users/1`
- Response status: `503 Service Unavailable`
- Error type: Server temporarily unavailable

**Attempt 2 (retry after 1.5s)**
- Response status: `200 OK`
- Response body (truncated):
  ```json
  {"id": 1, "name": "Alice", "email": "alice@example.com"}
  ```
- **Result: RECOVERED (flaky)**

---

### ⚠️ DELETE /users/{id} — Auth-Gated

- Sent: `DELETE http://localhost:8000/users/1`
- No Authorization header injected (no JWT/token env var found)
- Response status: `401 Unauthorized`
- **Result: AUTH-GATED** — endpoint likely works correctly; test with a valid token
```

---

## Debugger Handoff Section

Always include this section. If there are no failures, write "No issues found."

```markdown
---

## Debugger Handoff

> This section is structured for a debugger agent to parse and act on.
> Each issue includes a hypothesis and recommended entry point.

### Issue #<N>: <short label>

- **Endpoint:** `<METHOD> <path>`
- **Status received:** `<code>`
- **Expected:** `<2xx or describe expected behavior>`
- **Payload sent:**
  ```json
  <payload>
  ```
- **Response excerpt:**
  ```
  <truncated response body, max 300 chars>
  ```
- **Hypothesis:** <one sentence — what is likely wrong>
- **Recommended entry point:** <file, function, or middleware to inspect first>
- **Priority:** High | Medium | Low

---

**Recommended next steps for debugger agent:**

1. <Specific action — file + function>
2. <Specific action — file + function>
3. ...

**Endpoints requiring manual follow-up:**
- <list of skipped or auth-gated endpoints that could not be auto-tested>
```

### Hypothesis heuristics

Use response body content + status code to generate the hypothesis:

| Signal | Hypothesis template |
|---|---|
| 5xx + "does not exist" (DB) | "Missing migration or table not created; check Alembic/migration state" |
| 5xx + "NoneType" / `AttributeError` | "Null reference in handler; check for unguarded `.attribute` access" |
| 5xx + "connection refused" (internal) | "Downstream service (DB/Redis/queue) not running or misconfigured" |
| 422 Unprocessable Entity | "Request schema mismatch; generated payload may not match expected model" |
| 401 with auth token present | "Token validation failing; check middleware or token expiry" |
| 404 on documented endpoint | "Route not registered or prefix mismatch; check router include" |
| Timeout (no response) | "Handler blocking; check for synchronous I/O or missing await" |
| Redirect loop | "Redirect chain cyclic; check redirect target configuration" |

---

## Redirect Notation

When a request was followed through a redirect, annotate the summary table Notes
column and add a detail entry:

```markdown
**Redirect followed:** `GET /login` → `302` → `GET /login/callback` → `200`
- Final URL: `http://localhost:8000/login/callback`
- Result: ✅ Pass (final status 200)
```

---

## Footer

```markdown
---

*Report generated by api-probe skill. Intermediate files: `.agent-tasks/routes.json`,
`.agent-tasks/test_results.json`, `.agent-tasks/env_snapshot.json`.*
```
