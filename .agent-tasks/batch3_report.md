# API Test Results

**Generated:** 2026-06-29T17:33:20.369060+00:00
**Base URL:** `http://localhost:8000`
**Discovery source:** user-provided (Batch 3)
**Endpoints tested:** 8
**Passed:** 1 &nbsp;|&nbsp; **Failed:** 4 &nbsp;|&nbsp; **Skipped:** 3 &nbsp;|&nbsp; **Flaky (recovered):** 0 &nbsp;|&nbsp; **Auth-gated:** 0 &nbsp;|&nbsp; **No connection:** 0

---

## Summary

| Method | Path | Status | Result | Notes |
|--------|------|--------|--------|-------|
| GET | `/api/applications` | 200 | ✅ Pass | Headers injected: Authorization, X-API-Key |
| GET | `/api/applications/{application_id}` | 404 | ❌ Fail | Path params substituted: application_id=1; Headers injected: Authorization, X-API-Key |
| DELETE | `/api/applications/{application_id}` | 404 | ❌ Fail | Path params substituted: application_id=1; Headers injected: Authorization, X-API-Key |
| GET | `/api/generate/{application_id}/tex` | 404 | ❌ Fail | Path params substituted: application_id=1; Headers injected: Authorization, X-API-Key |
| GET | `/api/generate/{application_id}/pdf` | 404 | ❌ Fail | Path params substituted: application_id=1; Headers injected: Authorization, X-API-Key |
| POST | `/api/generate/points` | — | ⏭️ Skipped | SSE endpoint — manual test required |
| POST | `/api/generate/resume` | — | ⏭️ Skipped | SSE endpoint — manual test required |
| POST | `/api/generate/regenerate-section` | — | ⏭️ Skipped | SSE endpoint — manual test required |

---

## Endpoint Details

### ❌ GET `/api/applications/{application_id}` — Attempt Log

**Attempt 1**
- Sent: `GET http://localhost:8000/api/applications/1`
- Response status: `404`
- Response body (excerpt):
  ```
  {"detail":"Application '1' not found"}
  ```
- Elapsed: 288ms

**Attempt 2 (retry after 1.5s)**
- Sent: `GET http://localhost:8000/api/applications/1`
- Response status: `404`
- Response body (excerpt):
  ```
  {"detail":"Application '1' not found"}
  ```
- Elapsed: 3ms

**Result: ❌ FAILED** (both attempts non-2xx)

---

### ❌ DELETE `/api/applications/{application_id}` — Attempt Log

**Attempt 1**
- Sent: `DELETE http://localhost:8000/api/applications/1`
- Response status: `404`
- Response body (excerpt):
  ```
  {"detail":"Application '1' not found"}
  ```
- Elapsed: 287ms

**Attempt 2 (retry after 1.5s)**
- Sent: `DELETE http://localhost:8000/api/applications/1`
- Response status: `404`
- Response body (excerpt):
  ```
  {"detail":"Application '1' not found"}
  ```
- Elapsed: 2ms

**Result: ❌ FAILED** (both attempts non-2xx)

---

### ❌ GET `/api/generate/{application_id}/tex` — Attempt Log

**Attempt 1**
- Sent: `GET http://localhost:8000/api/generate/1/tex`
- Response status: `404`
- Response body (excerpt):
  ```
  {"detail":"Application '1' not found."}
  ```
- Elapsed: 288ms

**Attempt 2 (retry after 1.5s)**
- Sent: `GET http://localhost:8000/api/generate/1/tex`
- Response status: `404`
- Response body (excerpt):
  ```
  {"detail":"Application '1' not found."}
  ```
- Elapsed: 3ms

**Result: ❌ FAILED** (both attempts non-2xx)

---

### ❌ GET `/api/generate/{application_id}/pdf` — Attempt Log

**Attempt 1**
- Sent: `GET http://localhost:8000/api/generate/1/pdf`
- Response status: `404`
- Response body (excerpt):
  ```
  {"detail":"Application '1' not found."}
  ```
- Elapsed: 270ms

**Attempt 2 (retry after 1.5s)**
- Sent: `GET http://localhost:8000/api/generate/1/pdf`
- Response status: `404`
- Response body (excerpt):
  ```
  {"detail":"Application '1' not found."}
  ```
- Elapsed: 2ms

**Result: ❌ FAILED** (both attempts non-2xx)

---

## Debugger Handoff

> This section is structured for a debugger agent to parse and act on.
> Each issue includes a hypothesis and recommended entry point.

### Issue #1: Fail on `GET /api/applications/{application_id}`

- **Endpoint:** `GET /api/applications/{application_id}`
- **Status received:** `404`
- **Expected:** 2xx success response
- **Response excerpt:**
  ```
  {"detail":"Application '1' not found"}
  ```
- **Hypothesis:** Route not registered or prefix mismatch; check router include
- **Recommended entry point:** Check the route handler file for this endpoint
- **Priority:** Medium

### Issue #2: Fail on `DELETE /api/applications/{application_id}`

- **Endpoint:** `DELETE /api/applications/{application_id}`
- **Status received:** `404`
- **Expected:** 2xx success response
- **Response excerpt:**
  ```
  {"detail":"Application '1' not found"}
  ```
- **Hypothesis:** Route not registered or prefix mismatch; check router include
- **Recommended entry point:** Check the route handler file for this endpoint
- **Priority:** Medium

### Issue #3: Fail on `GET /api/generate/{application_id}/tex`

- **Endpoint:** `GET /api/generate/{application_id}/tex`
- **Status received:** `404`
- **Expected:** 2xx success response
- **Response excerpt:**
  ```
  {"detail":"Application '1' not found."}
  ```
- **Hypothesis:** Route not registered or prefix mismatch; check router include
- **Recommended entry point:** Check the route handler file for this endpoint
- **Priority:** Medium

### Issue #4: Fail on `GET /api/generate/{application_id}/pdf`

- **Endpoint:** `GET /api/generate/{application_id}/pdf`
- **Status received:** `404`
- **Expected:** 2xx success response
- **Response excerpt:**
  ```
  {"detail":"Application '1' not found."}
  ```
- **Hypothesis:** Route not registered or prefix mismatch; check router include
- **Recommended entry point:** Check the route handler file for this endpoint
- **Priority:** Medium

---

**Recommended next steps for debugger agent:**

- Inspect Check the route handler file for this endpoint for `GET /api/applications/{application_id}`: Route not registered or prefix mismatch; check router include
- Inspect Check the route handler file for this endpoint for `DELETE /api/applications/{application_id}`: Route not registered or prefix mismatch; check router include
- Inspect Check the route handler file for this endpoint for `GET /api/generate/{application_id}/tex`: Route not registered or prefix mismatch; check router include
- Inspect Check the route handler file for this endpoint for `GET /api/generate/{application_id}/pdf`: Route not registered or prefix mismatch; check router include

**Endpoints requiring manual follow-up:**

- `POST /api/generate/points` — SSE endpoint — manual test required
- `POST /api/generate/resume` — SSE endpoint — manual test required
- `POST /api/generate/regenerate-section` — SSE endpoint — manual test required

---

*Report generated by api-probe skill. Intermediate files: `.agent-tasks/routes.json`, `.agent-tasks/test_results.json`, `.agent-tasks/env_snapshot.json`.*