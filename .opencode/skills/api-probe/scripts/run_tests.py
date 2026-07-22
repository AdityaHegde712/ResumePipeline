"""
scripts/run_tests.py

Async parallel API test runner with 1-retry policy.

Usage:
    python scripts/run_tests.py \\
        --base-url http://localhost:8000 \\
        --routes .agent-tasks/routes.json \\
        --env .agent-tasks/env_snapshot.json \\
        --output .agent-tasks/test_results.json

Output (test_results.json):
    {
      "base_url": "http://localhost:8000",
      "timestamp": "2024-01-01T12:00:00Z",
      "results": [
        {
          "id": "get_/users_0",
          "method": "GET",
          "path": "/users",
          "url": "http://localhost:8000/users",
          "payload": null,
          "headers_injected": ["Authorization"],
          "path_substitutions": {},
          "attempts": [
            {
              "attempt": 1,
              "status": 200,
              "body_excerpt": "{...}",
              "final_url": "http://localhost:8000/users",
              "redirect": false,
              "error": null,
              "elapsed_ms": 42
            }
          ],
          "result": "pass",        // pass | flaky | fail | auth-gated | skipped | no-connection
          "skip_reason": null      // populated for skipped endpoints
        }
      ]
    }
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


RETRY_WAIT_S = 1.5
TIMEOUT_S = 30.0
BODY_EXCERPT_MAX = 500

SKIP_HINTS = {
    "multipart", "form-data", "UploadFile", "file", "bytes",
    "websocket", "ws://", "wss://", "SSE", "text/event-stream",
}


# ---------------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------------

def _coerce_default(field_name: str, type_str: str) -> object:
    """
    Map a type string (from type hints or name heuristics) to a conservative
    default value. Mirrors the rules in references/payload-rules.md.
    """
    t = (type_str or "").lower()
    n = (field_name or "").lower()

    if "uploadfile" in t or "bytes" in t:
        return "__SKIP__"
    if "optional" in t or t.endswith("| none") or t.startswith("none |"):
        return None
    if t in ("str", "string", "emailstr"):
        if "email" in n:
            return "test@example.com"
        if "url" in n or "link" in n:
            return "https://example.com"
        return "test"
    if t in ("int", "integer"):
        return 1
    if t in ("float", "number"):
        return 1.0
    if t in ("bool", "boolean"):
        return True
    if "datetime" in t:
        return "2024-01-01T00:00:00Z"
    if "date" in t:
        return "2024-01-01"
    if "uuid" in t:
        return "00000000-0000-0000-0000-000000000001"
    if "list" in t or "array" in t:
        return []
    if "dict" in t or "object" in t:
        return {}

    # Name-based heuristics when type is unknown
    if n.endswith("_id") or n == "id":
        return 1
    if "email" in n:
        return "test@example.com"
    if "url" in n or "link" in n:
        return "https://example.com"
    if "name" in n or "title" in n or "label" in n:
        return "test"
    if "count" in n or "num" in n or "total" in n or "amount" in n:
        return 1
    if "date" in n or n.endswith("_at"):
        return "2024-01-01T00:00:00Z"
    if "flag" in n or n.startswith("is_") or "enabled" in n or "active" in n:
        return True

    return None  # safest fallback


def build_payload(route: dict) -> tuple[dict | None, bool]:
    """
    Build a request body dict from route param info.
    Returns (payload_dict, should_skip).
    should_skip=True means the endpoint requires file uploads etc.
    """
    body_info = route.get("params", {}).get("body", {})
    fields = body_info.get("fields", {})
    method = route.get("method", "GET").upper()

    if method in ("GET", "HEAD", "DELETE", "OPTIONS"):
        return None, False

    if not fields:
        # No schema info — return empty object (safe conservative)
        return {}, False

    payload = {}
    for field_name, type_str in fields.items():
        value = _coerce_default(field_name, type_str)
        if value == "__SKIP__":
            return None, True  # File upload — skip entire endpoint
        payload[field_name] = value

    return payload, False


def build_query_params(route: dict) -> dict:
    """Build query parameter dict from route query param definitions."""
    qparams = route.get("params", {}).get("query", [])
    result = {}
    for param in qparams:
        name = param.get("name", "")
        type_str = param.get("type", "unknown")
        value = _coerce_default(name, type_str)
        if value is not None and value != "__SKIP__":
            result[name] = value
    return result


def substitute_path_params(path: str, route: dict) -> tuple[str, dict]:
    """
    Replace {param} placeholders in path with test values.
    Returns (substituted_path, {param: value}).
    """
    path_params = route.get("params", {}).get("path", [])
    substitutions = {}

    for param in path_params:
        name = param["name"]
        type_str = param.get("type", "unknown")
        value = _coerce_default(name, type_str)
        if value is None:
            value = 1  # Integer ID fallback for unknown path params
        substitutions[name] = value
        path = path.replace(f"{{{name}}}", str(value))

    # Catch any remaining {param} placeholders not in the params list
    import re
    for placeholder in re.findall(r"\{([^}]+)\}", path):
        value = 1
        substitutions[placeholder] = value
        path = path.replace(f"{{{placeholder}}}", str(value))

    return path, substitutions


def should_skip(route: dict) -> str | None:
    """Return a skip reason string, or None if the endpoint should be tested."""
    combined = json.dumps(route).lower()
    if any(hint.lower() in combined for hint in SKIP_HINTS):
        if "websocket" in combined or "ws://" in combined or "wss://" in combined:
            return "WebSocket endpoint — manual test required"
        if "sse" in combined or "event-stream" in combined:
            return "SSE endpoint — manual test required"
        if "uploadfile" in combined or "multipart" in combined or "form-data" in combined:
            return "File upload endpoint — manual test required"
    return None


# ---------------------------------------------------------------------------
# HTTP execution
# ---------------------------------------------------------------------------

async def execute_request(
    client,
    method: str,
    url: str,
    payload: dict | None,
    query_params: dict,
    headers: dict,
    attempt_num: int,
) -> dict:
    """Execute a single HTTP request and return an attempt record."""
    start = time.monotonic()
    try:
        kwargs = {
            "headers": headers,
            "params": query_params if query_params else None,
            "follow_redirects": True,
            "timeout": TIMEOUT_S,
        }
        if payload is not None:
            kwargs["json"] = payload

        response = await client.request(method, url, **kwargs)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        body_text = response.text[:BODY_EXCERPT_MAX] if response.text else ""
        final_url = str(response.url)
        redirected = final_url != url

        return {
            "attempt": attempt_num,
            "status": response.status_code,
            "body_excerpt": body_text,
            "final_url": final_url if redirected else url,
            "redirect": redirected,
            "error": None,
            "elapsed_ms": elapsed_ms,
        }

    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "attempt": attempt_num,
            "status": None,
            "body_excerpt": None,
            "final_url": url,
            "redirect": False,
            "error": str(e),
            "elapsed_ms": elapsed_ms,
        }


def classify_result(attempts: list[dict]) -> str:
    """Classify overall result from attempt records."""
    if not attempts:
        return "fail"

    a1 = attempts[0]
    a1_status = a1.get("status")

    # Connection refused / network error on attempt 1
    if a1_status is None and a1.get("error"):
        error_lower = a1["error"].lower()
        if "connection refused" in error_lower or "connect" in error_lower:
            return "no-connection"

    # Check 401/403 — auth-gated (only if single attempt because no token)
    if a1_status in (401, 403):
        return "auth-gated"

    def is_success(status):
        return status is not None and 200 <= status < 300

    if is_success(a1_status):
        return "pass"

    # If there was a retry
    if len(attempts) >= 2:
        a2 = attempts[1]
        a2_status = a2.get("status")
        if is_success(a2_status):
            return "flaky"

    return "fail"


async def test_route(client, route: dict, base_url: str, auth_headers: dict, idx: int) -> dict:
    """Test a single route, with 1 retry on failure."""
    route_id = f"{route['method'].lower()}_{route['path']}_{idx}"
    method = route["method"].upper()

    # Skip check
    skip_reason = should_skip(route)
    payload, file_skip = build_payload(route)
    if file_skip:
        skip_reason = skip_reason or "File upload endpoint — manual test required"

    if skip_reason:
        return {
            "id": route_id,
            "method": method,
            "path": route["path"],
            "url": f"{base_url.rstrip('/')}{route['path']}",
            "payload": None,
            "headers_injected": [],
            "path_substitutions": {},
            "attempts": [],
            "result": "skipped",
            "skip_reason": skip_reason,
        }

    # Build URL with path param substitution
    substituted_path, substitutions = substitute_path_params(route["path"], route)
    url = f"{base_url.rstrip('/')}{substituted_path}"

    # Build headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        **auth_headers,
    }
    injected_header_names = list(auth_headers.keys())

    # Build query params
    query_params = build_query_params(route)

    attempts = []

    # Attempt 1
    a1 = await execute_request(client, method, url, payload, query_params, headers, 1)
    attempts.append(a1)

    # Retry if not 2xx and not auth-gated
    a1_status = a1.get("status")
    needs_retry = (
        a1_status is None or (a1_status not in (401, 403) and not (200 <= a1_status < 300))
    )
    if needs_retry:
        await asyncio.sleep(RETRY_WAIT_S)
        a2 = await execute_request(client, method, url, payload, query_params, headers, 2)
        attempts.append(a2)

    result = classify_result(attempts)

    return {
        "id": route_id,
        "method": method,
        "path": route["path"],
        "url": url,
        "payload": payload,
        "headers_injected": injected_header_names,
        "path_substitutions": substitutions,
        "attempts": attempts,
        "result": result,
        "skip_reason": None,
    }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

async def run_all(base_url: str, routes: list[dict], auth_headers: dict) -> list[dict]:
    """Run all routes concurrently using a shared httpx async client."""
    try:
        import httpx
    except ImportError:
        print("[run_tests] Installing httpx...", file=sys.stderr)
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "httpx", "--break-system-packages", "-q"],
            check=True,
        )
        import httpx

    async with httpx.AsyncClient() as client:
        tasks = [
            test_route(client, route, base_url, auth_headers, idx)
            for idx, route in enumerate(routes)
        ]
        results = await asyncio.gather(*tasks)

    return list(results)


def main():
    parser = argparse.ArgumentParser(description="Run API endpoint tests in parallel.")
    parser.add_argument("--base-url", required=True, help="Base URL, e.g. http://localhost:8000")
    parser.add_argument("--routes", default=".agent-tasks/routes.json")
    parser.add_argument("--env", default=".agent-tasks/env_snapshot.json")
    parser.add_argument("--output", default=".agent-tasks/test_results.json")
    args = parser.parse_args()

    routes_path = Path(args.routes)
    env_path = Path(args.env)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not routes_path.exists():
        print(f"[run_tests] ERROR: routes file not found: {routes_path}", file=sys.stderr)
        sys.exit(1)

    routes = json.loads(routes_path.read_text())
    env_snapshot = json.loads(env_path.read_text()) if env_path.exists() else {}
    auth_headers = env_snapshot.get("auth_headers", {})

    if env_snapshot.get("warning"):
        print(f"[run_tests] Env warning: {env_snapshot['warning']}", file=sys.stderr)

    print(f"[run_tests] Testing {len(routes)} endpoint(s) against {args.base_url} ...", file=sys.stderr)

    results = asyncio.run(run_all(args.base_url, routes, auth_headers))

    # Count results
    counts = {"pass": 0, "flaky": 0, "fail": 0, "auth-gated": 0, "skipped": 0, "no-connection": 0}
    for r in results:
        counts[r["result"]] = counts.get(r["result"], 0) + 1

    output = {
        "base_url": args.base_url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": counts,
        "results": results,
    }

    out_path.write_text(json.dumps(output, indent=2))

    print(
        f"[run_tests] Done. Pass={counts['pass']} Flaky={counts['flaky']} "
        f"Fail={counts['fail']} Auth-gated={counts['auth-gated']} "
        f"Skipped={counts['skipped']} No-connection={counts['no-connection']}"
    )


if __name__ == "__main__":
    main()
