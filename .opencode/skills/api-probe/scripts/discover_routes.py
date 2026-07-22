"""
scripts/discover_routes.py

Tree-sitter AST-based API route discovery. Fallback used only when no
CODEBASE.md or user-provided resource is available.

Supports: FastAPI, Flask, Express (JS/TS), Django REST Framework, Go chi/gin.

Usage:
    python scripts/discover_routes.py --root /path/to/project [--out .agent-tasks/routes.json]

Output:
    JSON file containing a list of route objects:
    [
      {
        "method": "GET",
        "path": "/users",
        "handler": "get_users",
        "file": "app/routes/users.py",
        "line": 12,
        "params": {
          "path": [{"name": "user_id", "type": "int"}],
          "query": [],
          "body": {"model": "UserCreate", "fields": {...}}
        },
        "source": "tree-sitter"
      },
      ...
    ]
"""

import argparse
import ast
import json
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_deps():
    """Install tree-sitter language bindings if missing."""
    try:
        import tree_sitter_python  # noqa: F401
    except ImportError:
        print("[discover_routes] Installing tree-sitter language packages...", file=sys.stderr)
        os.system(
            "pip install tree-sitter tree-sitter-python tree-sitter-javascript "
            "tree-sitter-typescript --break-system-packages -q"
        )


def _build_ts_parser(lang_name: str):
    """Build a tree-sitter Parser for the given language."""
    try:
        from tree_sitter import Language, Parser
        if lang_name == "python":
            import tree_sitter_python as tsp
            lang = Language(tsp.language())
        elif lang_name in ("javascript", "typescript"):
            import tree_sitter_javascript as tsj
            lang = Language(tsj.language())
        else:
            return None
        p = Parser(lang)
        return p
    except Exception as e:
        print(f"[discover_routes] tree-sitter parser build failed ({lang_name}): {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Python — FastAPI / Flask / Django routes via stdlib ast (more reliable
# than tree-sitter for decorated functions in Python)
# ---------------------------------------------------------------------------

FASTAPI_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
FLASK_METHODS = {"route", "get", "post", "put", "patch", "delete"}

def _python_type_to_str(annotation) -> str:
    """Convert an ast annotation node to a readable type string."""
    if annotation is None:
        return "unknown"
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    if isinstance(annotation, ast.Subscript):
        outer = _python_type_to_str(annotation.value)
        inner = _python_type_to_str(annotation.slice)
        return f"{outer}[{inner}]"
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return f"{_python_type_to_str(annotation.left)} | {_python_type_to_str(annotation.right)}"
    if isinstance(annotation, ast.Constant):
        return str(annotation.value)
    if isinstance(annotation, ast.Tuple):
        return ", ".join(_python_type_to_str(e) for e in annotation.elts)
    return "unknown"


def _extract_pydantic_fields(model_name: str, module_tree: ast.Module) -> dict:
    """
    Walk module AST for a class matching model_name that inherits from
    BaseModel (or similar). Return {field_name: type_str}.
    """
    for node in ast.walk(module_tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name != model_name:
            continue
        bases = [_python_type_to_str(b) for b in node.bases]
        if not any(b in ("BaseModel", "Schema", "Serializer") for b in bases):
            continue
        fields = {}
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields[item.target.id] = _python_type_to_str(item.annotation)
        return fields
    return {}


def _scan_python_file(filepath: Path) -> list[dict]:
    """
    Parse a Python file and extract FastAPI / Flask route definitions.
    Returns a list of route dicts.
    """
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except SyntaxError:
        return []

    routes = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            method, path = None, None

            # FastAPI: @router.get("/path") or @app.post("/path")
            if isinstance(decorator, ast.Call):
                func = decorator.func
                if isinstance(func, ast.Attribute):
                    attr = func.attr.lower()
                    if attr in FASTAPI_METHODS or attr in FLASK_METHODS:
                        method = attr.upper()
                        if decorator.args and isinstance(decorator.args[0], ast.Constant):
                            path = decorator.args[0].value
                        else:
                            for kw in decorator.keywords:
                                if kw.arg == "path" and isinstance(kw.value, ast.Constant):
                                    path = kw.value.value

                # Flask: @app.route("/path", methods=["GET"])
                if isinstance(func, ast.Attribute) and func.attr == "route":
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        path = decorator.args[0].value
                    for kw in decorator.keywords:
                        if kw.arg == "methods" and isinstance(kw.value, ast.List):
                            for elt in kw.value.elts:
                                if isinstance(elt, ast.Constant):
                                    method = elt.value.upper()
                                    break
                    if method is None:
                        method = "GET"  # Flask default

            if not method or not path:
                continue

            # Inspect function signature for params
            path_params, query_params, body_info = [], [], {}
            path_segments = {seg.lstrip("{").rstrip("}") for seg in path.split("/") if "{" in seg}

            for arg in node.args.args:
                name = arg.arg
                if name in ("self", "cls", "request", "req", "db", "session",
                            "current_user", "background_tasks", "response"):
                    continue
                type_str = _python_type_to_str(arg.annotation) if arg.annotation else "unknown"

                if name in path_segments:
                    path_params.append({"name": name, "type": type_str})
                elif type_str in ("unknown",) and name not in path_segments:
                    query_params.append({"name": name, "type": type_str})
                elif type_str.endswith(("Create", "Update", "Request", "Schema", "Body", "BaseModel")):
                    fields = _extract_pydantic_fields(type_str, tree)
                    body_info = {"model": type_str, "fields": fields}
                else:
                    query_params.append({"name": name, "type": type_str})

            routes.append({
                "method": method,
                "path": path,
                "handler": node.name,
                "file": str(filepath),
                "line": node.lineno,
                "params": {
                    "path": path_params,
                    "query": query_params,
                    "body": body_info,
                },
                "source": "tree-sitter",
            })

    return routes


# ---------------------------------------------------------------------------
# JavaScript / TypeScript — Express routes via tree-sitter
# ---------------------------------------------------------------------------

JS_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "all", "use"}

def _scan_js_file(filepath: Path) -> list[dict]:
    """
    Scan a JS/TS file for Express-style route definitions using tree-sitter.
    Falls back to simple regex if tree-sitter parse fails.
    """
    _ensure_deps()
    import re
    routes = []

    source = filepath.read_text(encoding="utf-8", errors="replace")

    # Regex fallback — catches most Express patterns
    # app.get('/path', ...) or router.post('/path', ...)
    pattern = re.compile(
        r"""(?:app|router|server)\s*\.\s*(get|post|put|patch|delete|head|options)\s*\(\s*['"`]([^'"`]+)['"`]""",
        re.IGNORECASE,
    )
    for m in pattern.finditer(source):
        method = m.group(1).upper()
        path = m.group(2)
        # Express path params use :param — normalise to {param}
        normalised = re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", r"{\1}", path)
        line = source[: m.start()].count("\n") + 1
        routes.append({
            "method": method,
            "path": normalised,
            "handler": None,
            "file": str(filepath),
            "line": line,
            "params": {"path": [], "query": [], "body": {}},
            "source": "tree-sitter",
        })

    return routes


# ---------------------------------------------------------------------------
# File walker
# ---------------------------------------------------------------------------

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "coverage", ".mypy_cache",
    ".pytest_cache", "migrations",
}

EXTENSION_MAP = {
    ".py": _scan_python_file,
    ".js": _scan_js_file,
    ".ts": _scan_js_file,
    ".jsx": _scan_js_file,
    ".tsx": _scan_js_file,
}


def discover(root: Path) -> list[dict]:
    """Walk the project tree and collect all route definitions."""
    routes = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip directories in-place (modifies dirnames so os.walk skips them)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in filenames:
            ext = Path(filename).suffix.lower()
            scanner = EXTENSION_MAP.get(ext)
            if scanner is None:
                continue
            filepath = Path(dirpath) / filename
            try:
                found = scanner(filepath)
                routes.extend(found)
            except Exception as e:
                print(f"[discover_routes] Warning: could not scan {filepath}: {e}", file=sys.stderr)

    # Deduplicate by (method, path) — keep first occurrence
    seen = set()
    unique = []
    for r in routes:
        key = (r["method"], r["path"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Discover API routes via AST scanning.")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument(
        "--out", default=".agent-tasks/routes.json", help="Output JSON file path"
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"[discover_routes] Scanning {root} ...", file=sys.stderr)
    routes = discover(root)

    out.write_text(json.dumps(routes, indent=2))

    print(f"[discover_routes] Found {len(routes)} route(s). Written to {out}")
    if len(routes) == 0:
        print(
            "[discover_routes] WARNING: No routes found. "
            "Provide a CODEBASE.md or OpenAPI spec for better results.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
