"""Application directory storage: save tex/pdf/llm_response/request.json."""

import json
import re
from datetime import datetime
from pathlib import Path

APPLICATION_ID_FORMAT = "%Y%m%d-%H%M%S"
APPLICATION_ID_PREFIX = "application"
APPLICATION_ID_PATTERN = re.compile(r"^application-\d{8}-\d{6}$")


def generate_application_id(now: datetime | None = None) -> str:
    """Build a Windows-safe application id from a timestamp.

    Args:
        now: Clock to format; defaults to the current wall clock.

    Returns:
        An id of the form ``application-YYYYMMDD-HHMMSS``.
    """
    timestamp = now or datetime.now()
    return f"{APPLICATION_ID_PREFIX}-{timestamp.strftime(APPLICATION_ID_FORMAT)}"


def create_application_dir(root: Path, application_id: str) -> Path:
    """Create and return the directory for an application.

    Args:
        root: Parent directory that holds all application directories.
        application_id: Id of the application (Windows-safe filename).

    Returns:
        The created ``root / application_id`` directory.
    """
    app_dir = root / application_id
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def save_tex(app_dir: Path, content: str) -> Path:
    """Write the LaTeX source as utf-8 ``resume.tex`` and return its path."""

    return _write_text(app_dir, "resume.tex", content)


def save_pdf(app_dir: Path, content: bytes) -> Path:
    """Write the compiled PDF as raw bytes ``resume.pdf`` and return its path."""

    return _write_bytes(app_dir, "resume.pdf", content)


def save_llm_response(app_dir: Path, content: str) -> Path:
    """Write the raw LLM response as utf-8 ``llm_response.md`` and return it."""

    return _write_text(app_dir, "llm_response.md", content)


def save_cover_letter(app_dir: Path, text: str) -> Path:
    """Write the cover letter as utf-8 ``cover_letter.md`` and return it."""

    return _write_text(app_dir, "cover_letter.md", text)


def save_cover_letter_pdf(app_dir: Path, pdf_bytes: bytes) -> Path:
    """Write the exported cover-letter PDF as raw bytes and return its path."""

    return _write_bytes(app_dir, "cover_letter.pdf", pdf_bytes)


def update_request_json(app_dir: Path, updates: dict) -> Path:
    """Merge ``updates`` into ``request.json`` without clobbering other keys.

    Existing keys stay intact; keys present in ``updates`` override their
    prior values. Returns the ``request.json`` Path.

    Raises:
        FileNotFoundError: When the app dir or ``request.json`` is missing.
    """
    request_file = app_dir / "request.json"
    if not request_file.is_file():
        raise FileNotFoundError(f"Missing request.json: {request_file}")
    metadata = json.loads(request_file.read_text(encoding="utf-8"))
    metadata.update(updates)
    return _write_text(app_dir, "request.json", json.dumps(metadata, ensure_ascii=False))


def save_request_json(app_dir: Path, metadata: dict) -> Path:
    """Serialize the metadata dict to ``request.json`` and return its path."""

    return _write_text(app_dir, "request.json", json.dumps(metadata, ensure_ascii=False))


def application_dir(root: Path, application_id: str) -> Path:
    """Resolve the directory for an application id.

    Args:
        root: Parent directory that holds all application directories.
        application_id: Id of the application to locate.

    Returns:
        The ``root / application_id`` directory.

    Raises:
        ValueError: When ``application_id`` is not a valid application id.
        FileNotFoundError: When no such application directory exists.
    """
    if APPLICATION_ID_PATTERN.fullmatch(application_id) is None:
        raise ValueError(f"Invalid application id: {application_id!r}")
    app_dir = root / application_id
    if not app_dir.is_dir():
        raise FileNotFoundError(f"No application directory: {app_dir}")
    return app_dir


def list_applications(root: Path) -> list[dict]:
    """List metadata for every application, newest first.

    Reads each ``request.json`` under ``root`` and returns the parsed
    metadata dicts sorted descending by ``application_id``.

    Args:
        root: Parent directory that holds all application directories.

    Returns:
        Metadata dicts for all applications, newest first; ``[]`` when
        the root is empty or does not exist.
    """
    if not root.is_dir():
        return []
    entries: list[dict] = []
    for app_dir in root.iterdir():
        if not app_dir.is_dir():
            continue
        request_file = app_dir / "request.json"
        if not request_file.is_file():
            continue
        entries.append(json.loads(request_file.read_text(encoding="utf-8")))
    return sorted(entries, key=lambda entry: entry.get("application_id", ""), reverse=True)


def _write_text(app_dir: Path, filename: str, content: str) -> Path:
    """Write utf-8 text content inside the application directory.

    ``newline="\\n"`` keeps LF endings on Windows so raw-served bytes match
    ``Path.read_text`` output (text-mode would translate to CRLF on disk).
    """
    target = app_dir / filename
    target.write_text(content, encoding="utf-8", newline="\n")
    return target


def _write_bytes(app_dir: Path, filename: str, content: bytes) -> Path:
    """Write raw bytes inside the application directory."""

    target = app_dir / filename
    target.write_bytes(content)
    return target
