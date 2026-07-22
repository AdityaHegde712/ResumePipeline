"""
scripts/write_report.py

Reads test_results.json and routes.json, writes API_TEST_RESULTS.md
following the format defined in references/report-format.md exactly.

Usage:
    python scripts/write_report.py \\
        --results .agent-tasks/test_results.json \\
        --routes .agent-tasks/routes.json \\
        --output .agent-tasks/API_TEST_RESULTS.md
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Result symbol + label mapping
# ---------------------------------------------------------------------------

RESULT_DISPLAY = {
    "pass":          ("✅", "Pass"),
    "flaky":         ("🔁", "Flaky"),
    "auth-gated":    ("⚠️", "Auth-gated"),
    "fail":          ("❌", "Fail"),
    "skipped":       ("⏭️", "Skipped"),
    "no-connection": ("🔌", "No connection"),
}


# ---------------------------------------------------------------------------
# Hypothesis generation from response signals
# ---------------------------------------------------------------------------

HYPOTHESIS_MAP = [
    ("does not exist",              "Missing migration or table not created; check Alembic/migration state"),
    ("relation",                    "Missing migration or table not created; check Alembic/migration state"),
    ("nonetype",                    "Null reference in handler; check for unguarded `.attribute` access"),
    ("attributeerror",              "Null reference in handler; check for unguarded `.attribute` access"),
    ("connection refused",          "Downstream service (DB/Redis/queue) not running or misconfigured"),
    ("operationalerror",            "Downstream service (DB/Redis/queue) not running or misconfigured"),
    ("422",                         "Request schema mismatch; generated payload may not match expected model"),
    ("token",                       "Token validation failing; check middleware or token expiry"),
    ("not found",                   "Route not registered or prefix mismatch; check router include"),
    ("timeout",                     "Handler blocking; check for synchronous I/O or missing await"),
    ("redirect",                    "Redirect chain may be cyclic; check redirect target configuration"),
]


def infer_hypothesis(result: dict) -> str:
    attempts = result.get("attempts", [])
    status = None
    body = ""
    for a in attempts:
        if a.get("status"):
            status = a["status"]
        if a.get("body_excerpt"):
            body = (a["body_excerpt"] or "").lower()

    if result["result"] == "auth-gated":
        return "Endpoint likely requires valid credentials; test with a token from the .env file"
    if result["result"] == "no-connection":
        return "Server not responding on base URL; ensure the backend is running"
    if result["result"] == "flaky":
        return "Transient failure on first attempt; endpoint may have a race condition or cold-start delay"

    for signal, hypothesis in HYPOTHESIS_MAP:
        if signal in body or (status and str(status) in signal):
            return hypothesis

    if status and status >= 500:
        return "Server error; check application logs for the stack trace at this endpoint"
    if status == 422:
        return "Request schema mismatch; generated payload may not match expected model"
    if status == 404:
        return "Route not found; check router registration and path prefixes"

    return "Unknown failure; inspect application logs and the response body for details"


def infer_entry_point(result: dict, routes: list[dict]) -> str:
    """Suggest a file + function to inspect first."""
    path = result.get("path", "")
    method = result.get("method", "").upper()

    # Find the matching route for handler/file info
    for route in routes:
        if route.get("path") == path and route.get("method", "").upper() == method:
            handler = route.get("handler")
            file_ = route.get("file")
            if handler and file_:
                return f"`{handler}` in `{file_}`"
            if file_:
                return f"`{file_}`"

    return "Check the route handler file for this endpoint"


def infer_priority(result: dict) -> str:
    if result["result"] == "no-connection":
        return "High"
    attempts = result.get("attempts", [])
    for a in attempts:
        status = a.get("status")
        if status and status >= 500:
            return "High"
        if status == 422:
            return "Medium"
    if result["result"] == "flaky":
        return "Medium"
    return "Medium"


# ---------------------------------------------------------------------------
# Markdown builders
# ---------------------------------------------------------------------------

def build_summary_table(results: list[dict]) -> str:
    lines = [
        "## Summary",
        "",
        "| Method | Path | Status | Result | Notes |",
        "|--------|------|--------|--------|-------|",
    ]
    for r in results:
        symbol, label = RESULT_DISPLAY.get(r["result"], ("❓", r["result"]))
        method = r.get("method", "?")
        path = r.get("path", "?")

        # Determine status to show
        attempts = r.get("attempts", [])
        final_status = "—"
        if attempts:
            last = attempts[-1]
            final_status = str(last.get("status") or "—")

        # Notes
        notes_parts = []
        if r.get("skip_reason"):
            notes_parts.append(r["skip_reason"])
        if r.get("path_substitutions"):
            subs = ", ".join(f"{k}={v}" for k, v in r["path_substitutions"].items())
            notes_parts.append(f"Path params substituted: {subs}")
        if r.get("headers_injected"):
            notes_parts.append(f"Headers injected: {', '.join(r['headers_injected'])}")
        if r["result"] == "flaky" and len(attempts) >= 1:
            notes_parts.append("Recovered on retry")
        # Check for redirect
        for a in attempts:
            if a.get("redirect"):
                notes_parts.append(f"Redirected → {a['final_url']}")
                break

        notes = "; ".join(notes_parts) if notes_parts else ""
        lines.append(f"| {method} | `{path}` | {final_status} | {symbol} {label} | {notes} |")

    return "\n".join(lines)


def build_detail_sections(results: list[dict], routes: list[dict]) -> str:
    detail_results = [r for r in results if r["result"] not in ("pass", "skipped")]
    if not detail_results:
        return ""

    lines = ["---", "", "## Endpoint Details", ""]

    for r in detail_results:
        symbol, label = RESULT_DISPLAY.get(r["result"], ("❓", r["result"]))
        method = r.get("method", "?")
        path = r.get("path", "?")
        attempts = r.get("attempts", [])

        lines.append(f"### {symbol} {method} `{path}` — Attempt Log")
        lines.append("")

        for a in attempts:
            attempt_num = a["attempt"]
            retry_note = " (retry after 1.5s)" if attempt_num > 1 else ""
            lines.append(f"**Attempt {attempt_num}{retry_note}**")
            lines.append(f"- Sent: `{method} {r.get('url', path)}`")

            payload = r.get("payload")
            if payload is not None:
                lines.append("- Payload:")
                lines.append("  ```json")
                lines.append(f"  {json.dumps(payload, indent=2)}")
                lines.append("  ```")
            elif method not in ("GET", "HEAD", "OPTIONS", "DELETE"):
                lines.append("- Payload: `{}` (no schema found, empty body)")

            if a.get("error"):
                lines.append(f"- Error: `{a['error']}`")
            else:
                lines.append(f"- Response status: `{a.get('status')}`")
                if a.get("redirect"):
                    lines.append(f"- Redirected to: `{a['final_url']}`")
                if a.get("body_excerpt"):
                    lines.append("- Response body (excerpt):")
                    lines.append("  ```")
                    lines.append(f"  {a['body_excerpt']}")
                    lines.append("  ```")

            lines.append(f"- Elapsed: {a.get('elapsed_ms', '?')}ms")
            lines.append("")

        # Result line
        if r["result"] == "fail":
            lines.append("**Result: ❌ FAILED** (both attempts non-2xx)")
        elif r["result"] == "flaky":
            lines.append("**Result: 🔁 RECOVERED** (failed attempt 1, passed attempt 2)")
        elif r["result"] == "auth-gated":
            lines.append(
                "**Result: ⚠️ AUTH-GATED** — endpoint likely works correctly; "
                "retest with a valid token in `.env`"
            )
        elif r["result"] == "no-connection":
            lines.append("**Result: 🔌 NO CONNECTION** — server not responding")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def build_debugger_handoff(results: list[dict], routes: list[dict]) -> str:
    issues = [r for r in results if r["result"] in ("fail", "flaky", "no-connection")]
    manual = [r for r in results if r["result"] in ("skipped", "auth-gated")]

    lines = [
        "## Debugger Handoff",
        "",
        "> This section is structured for a debugger agent to parse and act on.",
        "> Each issue includes a hypothesis and recommended entry point.",
        "",
    ]

    if not issues:
        lines.append("**No issues found.** All reachable endpoints passed.")
        lines.append("")
    else:
        next_steps = []
        for idx, r in enumerate(issues, start=1):
            symbol, label = RESULT_DISPLAY.get(r["result"], ("❓", r["result"]))
            method = r.get("method", "?")
            path = r.get("path", "?")
            attempts = r.get("attempts", [])

            # Pick the most informative attempt for display
            display_attempt = attempts[-1] if attempts else {}
            status = display_attempt.get("status", "—")
            body_excerpt = display_attempt.get("body_excerpt") or ""

            hypothesis = infer_hypothesis(r)
            entry_point = infer_entry_point(r, routes)
            priority = infer_priority(r)

            lines.append(f"### Issue #{idx}: {label} on `{method} {path}`")
            lines.append("")
            lines.append(f"- **Endpoint:** `{method} {path}`")
            lines.append(f"- **Status received:** `{status}`")
            lines.append(f"- **Expected:** 2xx success response")

            payload = r.get("payload")
            if payload is not None:
                lines.append("- **Payload sent:**")
                lines.append("  ```json")
                lines.append(f"  {json.dumps(payload, indent=2)}")
                lines.append("  ```")

            if body_excerpt:
                lines.append("- **Response excerpt:**")
                lines.append("  ```")
                lines.append(f"  {body_excerpt[:300]}")
                lines.append("  ```")

            lines.append(f"- **Hypothesis:** {hypothesis}")
            lines.append(f"- **Recommended entry point:** {entry_point}")
            lines.append(f"- **Priority:** {priority}")
            lines.append("")

            next_steps.append(f"- Inspect {entry_point} for `{method} {path}`: {hypothesis}")

        lines.append("---")
        lines.append("")
        lines.append("**Recommended next steps for debugger agent:**")
        lines.append("")
        lines.extend(next_steps)
        lines.append("")

    if manual:
        lines.append("**Endpoints requiring manual follow-up:**")
        lines.append("")
        for r in manual:
            symbol, label = RESULT_DISPLAY.get(r["result"], ("❓", r["result"]))
            reason = r.get("skip_reason") or label
            lines.append(f"- `{r['method']} {r['path']}` — {reason}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Write API_TEST_RESULTS.md from test result JSON.")
    parser.add_argument("--results", default=".agent-tasks/test_results.json")
    parser.add_argument("--routes", default=".agent-tasks/routes.json")
    parser.add_argument("--output", default=".agent-tasks/API_TEST_RESULTS.md")
    args = parser.parse_args()

    results_path = Path(args.results)
    routes_path = Path(args.routes)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not results_path.exists():
        print(f"[write_report] ERROR: results file not found: {results_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(results_path.read_text())
    routes = json.loads(routes_path.read_text()) if routes_path.exists() else []

    results = data.get("results", [])
    summary = data.get("summary", {})
    base_url = data.get("base_url", "unknown")
    timestamp = data.get("timestamp", datetime.now(timezone.utc).isoformat())

    # Discovery source heuristic
    if routes and routes[0].get("source") == "tree-sitter":
        discovery_source = "tree-sitter AST scan"
    elif routes:
        discovery_source = routes[0].get("source", "CODEBASE.md")
    else:
        discovery_source = "unknown"

    total = len(results)
    passed = summary.get("pass", 0)
    flaky = summary.get("flaky", 0)
    failed = summary.get("fail", 0)
    auth_gated = summary.get("auth-gated", 0)
    skipped = summary.get("skipped", 0)
    no_conn = summary.get("no-connection", 0)

    sections = []

    # Header
    sections.append("# API Test Results")
    sections.append("")
    sections.append(f"**Generated:** {timestamp}")
    sections.append(f"**Base URL:** `{base_url}`")
    sections.append(f"**Discovery source:** {discovery_source}")
    sections.append(f"**Endpoints tested:** {total}")
    sections.append(
        f"**Passed:** {passed} &nbsp;|&nbsp; "
        f"**Failed:** {failed} &nbsp;|&nbsp; "
        f"**Skipped:** {skipped} &nbsp;|&nbsp; "
        f"**Flaky (recovered):** {flaky} &nbsp;|&nbsp; "
        f"**Auth-gated:** {auth_gated} &nbsp;|&nbsp; "
        f"**No connection:** {no_conn}"
    )
    sections.append("")
    sections.append("---")
    sections.append("")

    # Summary table
    sections.append(build_summary_table(results))
    sections.append("")

    # Endpoint details
    details = build_detail_sections(results, routes)
    if details:
        sections.append(details)

    # Debugger handoff
    sections.append(build_debugger_handoff(results, routes))

    # Footer
    sections.append("---")
    sections.append("")
    sections.append(
        "*Report generated by api-probe skill. "
        "Intermediate files: `.agent-tasks/routes.json`, "
        "`.agent-tasks/test_results.json`, `.agent-tasks/env_snapshot.json`.*"
    )

    report = "\n".join(sections)
    out_path.write_text(report, encoding="utf-8")

    print(f"[write_report] Report written to {out_path}")
    print(
        f"[write_report] {passed} passed, {failed} failed, {flaky} flaky, "
        f"{auth_gated} auth-gated, {skipped} skipped"
    )


if __name__ == "__main__":
    main()
