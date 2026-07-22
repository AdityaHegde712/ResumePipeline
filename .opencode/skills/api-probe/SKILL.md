---
name: api-probe
description: >
  Postman-equivalent API testing skill for AI agents. Use this skill whenever a user wants
  to test their backend API, probe endpoints, validate routes, check if their server is
  working, ping endpoints, run API tests, or get a health check of their running service.
  Trigger on phrases like "test my API", "probe my endpoints", "check my routes", "test
  my backend", "scan my API", "run API tests", "validate my endpoints", or "does my server
  work". The skill discovers endpoints from CODEBASE.md or a user-provided resource first,
  falls back to tree-sitter AST scanning only if neither is available. Executes requests in
  parallel with 1 retry per failure, loads env vars from the project's .env file, and writes
  results to .agent-tasks/API_TEST_RESULTS.md with a structured debugger handoff section.
license: MIT
compatibility: opencode
metadata:
  author: user
  version: "1.0"
---

# API Probe Skill

Discovers, tests, and reports on all API endpoints in a running backend. Produces
`.agent-tasks/API_TEST_RESULTS.md` with pass/fail results and a structured debugger
handoff section.

Before doing anything, read `references/payload-rules.md` and `references/report-format.md`.

---

## Workflow

### Step 0 — Confirm the server is running

Ask the user to confirm their backend server is running and on which base URL
(e.g. `http://localhost:8000`). Do not proceed until confirmed. If no base URL is
given, default to `http://localhost:8000` but state the assumption explicitly.

---

### Step 1 — Discover endpoints

Use the following priority order. Stop at the first source that yields results.

#### 1a. CODEBASE.md or user-provided resource (preferred)

Check for `CODEBASE.md` at the repo root:

```bash
ls CODEBASE.md 2>/dev/null && echo "found" || echo "not found"
```

If found, extract endpoints from it: look for sections titled "API", "Routes",
"Endpoints", "Services", or any table/list that enumerates HTTP methods and paths.

If the user's prompt referenced a specific file (e.g. "use my openapi.yaml" or
"here's my routes file"), use that file instead — it takes precedence over CODEBASE.md.

Accept any of these as sufficient discovery output:
- A table of `METHOD /path` rows
- An OpenAPI/Swagger spec (parse `paths`)
- A Postman collection JSON (parse `item[].request`)
- A plain list of routes from a framework's route dump

If discovery from this source yields ≥ 1 endpoint, proceed to Step 2.

#### 1b. Tree-sitter AST scan (fallback only)

Use this path **only if** neither CODEBASE.md nor a user-provided resource exists or
yields any endpoints.

Run the discovery script:

```bash
pip install tree-sitter tree-sitter-python tree-sitter-javascript \
            tree-sitter-typescript --break-system-packages -q

python scripts/discover_routes.py --root .
```

The script outputs `routes.json` to `.agent-tasks/routes.json`. Read that file
for the endpoint list.

If tree-sitter still yields 0 endpoints, report this to the user and ask them to
provide a routes file or OpenAPI spec before continuing.

---

### Step 2 — Load environment variables

Run the env loader to find and parse `.env` files:

```bash
python scripts/load_env.py --root .
```

The script outputs `.agent-tasks/env_snapshot.json` (keys only, no values printed
to stdout — secrets stay local). This file is consumed by the test runner in Step 3.

If no `.env` is found, the script prints a warning. Continue without env vars but
note in the report that auth-dependent tests may fail due to missing credentials.

---

### Step 3 — Run tests

Execute all discovered endpoints in parallel with a 1-retry policy:

```bash
python scripts/run_tests.py \
  --base-url <BASE_URL> \
  --routes .agent-tasks/routes.json \
  --env .agent-tasks/env_snapshot.json \
  --output .agent-tasks/test_results.json
```

The runner:
- Generates payloads from type hints / Pydantic schemas; falls back to conservative
  defaults for unknown schemas (see `references/payload-rules.md`)
- Runs all requests concurrently with `asyncio.gather`, keyed by a stable request ID
  so response ordering is always traceable back to its request
- On any non-2xx response or network error: waits 1.5s and retries once
- Records attempt 1 and attempt 2 separately in `test_results.json`
- Follows redirects automatically (`httpx` default); logs the final URL if it
  differs from the original path

---

### Step 4 — Write the report

```bash
python scripts/write_report.py \
  --results .agent-tasks/test_results.json \
  --routes .agent-tasks/routes.json \
  --output .agent-tasks/API_TEST_RESULTS.md
```

The report format is defined in `references/report-format.md`. Follow it exactly.

After the script runs, read `.agent-tasks/API_TEST_RESULTS.md` and present a
one-paragraph summary to the user: total endpoints tested, how many passed,
how many failed, and whether a debugger handoff section was generated.

---

## Edge Cases

| Situation | Handling |
|---|---|
| Dynamic route (`/users/{id}`) | Substitute placeholder ID: `1` for int, `"test"` for str |
| File upload endpoint | Skip execution; note in report as "manual test required" |
| WebSocket / SSE endpoint | Skip execution; note in report as "manual test required" |
| Required field missing type hint | Use `null` for nullable, `""` for str, `0` for int |
| Enum field | Use the first declared enum value |
| Nested Pydantic model | Recurse into model fields; apply same rules |
| Auth header required but env var missing | Send request without auth; expected to 401; record as "auth-gated" |
| Endpoint returns redirect (3xx) | Follow redirect; record both original and final status |
| Server not responding | Mark all endpoints as "connection refused"; skip retries |

---

## Files Written

| Path | Contents |
|---|---|
| `.agent-tasks/routes.json` | Discovered routes (method, path, params, schema hints) |
| `.agent-tasks/env_snapshot.json` | Env var keys present (no values) |
| `.agent-tasks/test_results.json` | Raw per-endpoint results with attempt logs |
| `.agent-tasks/API_TEST_RESULTS.md` | Final human + agent readable report |

The `.agent-tasks/` directory is created automatically if it does not exist.

---

## Reference Files

- `references/payload-rules.md` — How to generate request payloads from type hints,
  conservative defaults, and schema inference rules
- `references/report-format.md` — Exact markdown structure for `API_TEST_RESULTS.md`,
  including the debugger handoff section template
