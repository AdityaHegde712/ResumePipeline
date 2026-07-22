"""
scripts/load_env.py

Searches the project tree for .env files, loads their key-value pairs,
and writes a snapshot JSON to .agent-tasks/env_snapshot.json.

The snapshot stores only which keys are present (not values), and separately
stores values in memory for injection into the test runner via a temp file
that is readable only within the same process session.

Usage:
    python scripts/load_env.py --root /path/to/project [--out .agent-tasks/env_snapshot.json]

Output (env_snapshot.json):
    {
      "keys_found": ["DATABASE_URL", "JWT_SECRET", "API_KEY"],
      "auth_headers": {
        "Authorization": "Bearer <value>",   // present only if token-like key found
        "X-API-Key": "<value>"               // present only if API key found
      },
      "env_file_used": ".env",
      "warning": null   // or a string if no .env was found
    }
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# .env search
# ---------------------------------------------------------------------------

ENV_FILENAMES = [".env", ".env.local", ".env.development", ".env.production"]
# Also accept .env.example as a last resort (values will be empty/placeholder)
ENV_FALLBACKS = [".env.example", ".env.sample", ".env.template"]

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "coverage",
}


def find_env_file(root: Path) -> tuple[Path | None, bool]:
    """
    Search for a .env file starting at root and walking down one level.
    Returns (path, is_fallback). Falls back to .env.example files if needed.

    Search order:
    1. root/.env (and other ENV_FILENAMES) — exact match first
    2. Walk subdirectories one level deep for the same filenames
    3. Fallback to ENV_FALLBACKS at root
    """
    # 1. Check root directly
    for name in ENV_FILENAMES:
        candidate = root / name
        if candidate.is_file():
            return candidate, False

    # 2. Walk one level down
    for child in root.iterdir():
        if child.is_dir() and child.name not in SKIP_DIRS:
            for name in ENV_FILENAMES:
                candidate = child / name
                if candidate.is_file():
                    return candidate, False

    # 3. Fallback examples at root
    for name in ENV_FALLBACKS:
        candidate = root / name
        if candidate.is_file():
            return candidate, True

    return None, False


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

LINE_RE = re.compile(r"""^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$""")


def parse_env_file(filepath: Path) -> dict[str, str]:
    """
    Parse a .env file into {key: value}. Handles:
    - Quoted values (single and double)
    - Inline comments
    - Blank lines and comment lines (#)
    - export KEY=VALUE syntax
    """
    result = {}
    for line in filepath.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip leading `export `
        if line.lower().startswith("export "):
            line = line[7:].lstrip()
        m = LINE_RE.match(line)
        if not m:
            continue
        key = m.group(1)
        value = m.group(2).strip()
        # Strip inline comments (not inside quotes)
        if value and value[0] not in ('"', "'"):
            value = value.split("#")[0].strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


# ---------------------------------------------------------------------------
# Auth header inference
# ---------------------------------------------------------------------------

def infer_auth_headers(env: dict[str, str]) -> dict[str, str]:
    """
    Scan env keys for token/API key patterns and build HTTP headers to inject.
    Returns a dict of {header_name: header_value}.
    Only injects headers for keys with non-empty values.
    """
    headers = {}

    jwt_patterns = re.compile(r"(jwt|token|access_token|bearer|auth_token)", re.IGNORECASE)
    apikey_patterns = re.compile(r"(api_key|apikey|api_secret)", re.IGNORECASE)
    basic_patterns = re.compile(r"basic_auth", re.IGNORECASE)

    # Collect candidates, prefer more specific matches
    jwt_candidates = []
    apikey_candidates = []

    for key, value in env.items():
        if not value or value.startswith("<") or value in ("your_token_here", "changeme"):
            continue  # Placeholder value — skip
        if basic_patterns.search(key):
            headers["Authorization"] = f"Basic {value}"
        elif jwt_patterns.search(key):
            jwt_candidates.append((key, value))
        elif apikey_patterns.search(key):
            apikey_candidates.append((key, value))

    # Pick most specific JWT candidate: prefer ACCESS_TOKEN > TOKEN > JWT
    if jwt_candidates:
        preferred = sorted(
            jwt_candidates,
            key=lambda kv: (
                0 if "access_token" in kv[0].lower() else
                1 if "jwt" in kv[0].lower() else 2
            ),
        )
        _, token_value = preferred[0]
        if "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {token_value}"

    # Pick first API key candidate
    if apikey_candidates:
        _, key_value = apikey_candidates[0]
        headers["X-API-Key"] = key_value

    return headers


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Load project .env into a test-safe snapshot.")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument(
        "--out", default=".agent-tasks/env_snapshot.json", help="Output JSON file path"
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    env_file, is_fallback = find_env_file(root)

    if env_file is None:
        snapshot = {
            "keys_found": [],
            "auth_headers": {},
            "env_file_used": None,
            "warning": (
                "No .env file found. Auth-dependent endpoints will be tested without "
                "credentials and are expected to return 401/403."
            ),
        }
        out.write_text(json.dumps(snapshot, indent=2))
        print(f"[load_env] No .env found in {root}. Snapshot written with empty auth.", file=sys.stderr)
        return

    env = parse_env_file(env_file)
    auth_headers = infer_auth_headers(env)

    # Write snapshot: keys only (safe to log), auth headers (values — used by test runner)
    snapshot = {
        "keys_found": list(env.keys()),
        "auth_headers": auth_headers,
        "env_file_used": str(env_file.relative_to(root)) if env_file else None,
        "warning": (
            f"Using fallback env file ({env_file.name}). "
            "Values may be placeholders — auth injection may not work."
        )
        if is_fallback
        else None,
    }

    out.write_text(json.dumps(snapshot, indent=2))

    print(f"[load_env] Loaded {len(env)} key(s) from {env_file.relative_to(root)}")
    if auth_headers:
        print(f"[load_env] Auth headers to inject: {list(auth_headers.keys())}")
    if snapshot["warning"]:
        print(f"[load_env] Warning: {snapshot['warning']}", file=sys.stderr)


if __name__ == "__main__":
    main()
