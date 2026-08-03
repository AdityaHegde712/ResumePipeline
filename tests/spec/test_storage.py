"""Frozen spec tests for application storage (T08, Phase 5).

LOCKED contract — ``backend/app/storage.py`` must satisfy this file exactly.
This file is frozen after Phase 5 and may not be modified to fit an
implementation.

Public interface (all exported from ``backend.app.storage``):

    def generate_application_id(now: datetime | None = None) -> str
    def create_application_dir(root: Path, application_id: str) -> Path
    def save_tex(app_dir: Path, content: str) -> Path
    def save_pdf(app_dir: Path, content: bytes) -> Path
    def save_llm_response(app_dir: Path, content: str) -> Path
    def save_request_json(app_dir: Path, metadata: dict) -> Path
    def application_dir(root: Path, application_id: str) -> Path
    def list_applications(root: Path) -> list[dict]

Rules locked by these tests (PLAN D8, D9, D13):

- ``generate_application_id`` returns ``application-YYYYMMDD-HHMMSS``. The
  timestamp comes from ``now`` when provided (deterministic clock
  injection), else from the current wall clock; the result is within ten
  seconds of the wall clock at call time.
- The id is Windows-filesystem-safe: it never contains any of the illegal
  characters ``< > : " / \\ | ? *`` and contains no path separators
  (``Path(application_id).name == application_id``).
- Every root-relative function takes the root as an explicit argument; no
  module-level data directory is consulted. Tests pass pytest's ``tmp_path``
  so nothing is written outside the temporary directory.
- ``create_application_dir`` creates ``root / application_id`` (including
  missing parents) and returns that directory Path.
- The four save helpers each write one file inside ``app_dir`` and return
  its Path: ``save_tex`` -> ``resume.tex`` (utf-8 text), ``save_pdf`` ->
  ``resume.pdf`` (raw bytes), ``save_llm_response`` -> ``llm_response.md``
  (utf-8 text), ``save_request_json`` -> ``request.json`` (JSON serialized
  from the given dict). Text round-trips exactly, including non-ASCII
  characters; PDF content round-trips as raw bytes; the JSON metadata dict
  round-trips through ``json.loads``.
- ``application_dir`` returns ``root / application_id`` and raises
  ``FileNotFoundError`` when that directory does not exist (404-style).
- ``list_applications`` returns the parsed ``request.json`` metadata dicts
  for every application directory, sorted descending by ``application_id``
  (newest first). An empty root yields ``[]``.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from backend.app.storage import (
    application_dir,
    create_application_dir,
    generate_application_id,
    list_applications,
    save_llm_response,
    save_pdf,
    save_request_json,
    save_tex,
)

APPLICATION_ID_PATTERN = re.compile(r"^application-\d{8}-\d{6}$")
WINDOWS_ILLEGAL_CHARACTERS = set('<>:"/\\|?*')

EXAMPLE_APPLICATION_ID = "application-20260802-143045"
EXAMPLE_TIMESTAMP = datetime(2026, 8, 2, 14, 30, 45)


def make_metadata(application_id: str, timestamp: str) -> dict:
    """Build representative D9 request.json metadata for an application."""

    return {
        "application_id": application_id,
        "job_position": "Data Scientist Intern",
        "company_name": "SUHORA Technologies Pvt. Ltd.",
        "company_description": None,
        "job_description": "Build and ship ML features.",
        "timestamp": timestamp,
        "status": "completed",
        "llm_generation": "OK",
        "reconstruction": "OK",
        "saved": "OK",
        "pdf_error": None,
    }


class TestApplicationIdFormat:
    """The locked ``application-YYYYMMDD-HHMMSS`` id contract (D8)."""

    def test_injected_clock_produces_exact_application_id(self) -> None:
        """A provided ``now`` fully determines the id (deterministic)."""

        application_id = generate_application_id(now=EXAMPLE_TIMESTAMP)

        assert application_id == "application-20260802-143045"

    def test_application_id_matches_locked_pattern(self) -> None:
        """The id always matches ``application-YYYYMMDD-HHMMSS``."""

        application_id = generate_application_id(now=EXAMPLE_TIMESTAMP)

        assert APPLICATION_ID_PATTERN.fullmatch(application_id) is not None

    def test_defaults_to_wall_clock_within_tolerance(self) -> None:
        """Without a clock, the id timestamp is within ten seconds of now."""

        before = datetime.now()
        application_id = generate_application_id()
        after = datetime.now()

        timestamp_text = application_id.removeprefix("application-")
        parsed_timestamp = datetime.strptime(timestamp_text, "%Y%m%d-%H%M%S")
        tolerance = timedelta(seconds=10)
        assert before - tolerance <= parsed_timestamp <= after + tolerance

    def test_application_id_has_no_windows_illegal_characters(self) -> None:
        """The id is a safe Windows filename: no illegal chars or separators."""

        application_id = generate_application_id(now=EXAMPLE_TIMESTAMP)

        assert not WINDOWS_ILLEGAL_CHARACTERS & set(application_id)
        assert Path(application_id).name == application_id


class TestCreateApplicationDir:
    """Root-explicit, hermetic app directory creation."""

    def test_creates_directory_under_root(self, tmp_path: Path) -> None:
        """The app dir is created at ``root / application_id``."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)

        assert app_dir == tmp_path / EXAMPLE_APPLICATION_ID
        assert app_dir.is_dir()

    def test_creates_missing_parents(self, tmp_path: Path) -> None:
        """A nested root that does not exist yet is created too."""

        nested_root = tmp_path / "data" / "applications"
        app_dir = create_application_dir(nested_root, EXAMPLE_APPLICATION_ID)

        assert app_dir.is_dir()
        assert app_dir == nested_root / EXAMPLE_APPLICATION_ID


class TestSaveFiles:
    """The four save helpers write one file each and round-trip content."""

    def test_save_tex_round_trips_unicode_text(self, tmp_path: Path) -> None:
        """``resume.tex`` stores the utf-8 tex content byte-for-byte."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        tex_content = "\\section{Technical Skills} — Python & C# 100%\nünïcode ✓"

        saved_path = save_tex(app_dir, tex_content)

        assert saved_path == app_dir / "resume.tex"
        assert saved_path.read_text(encoding="utf-8") == tex_content

    def test_save_pdf_round_trips_binary_bytes(self, tmp_path: Path) -> None:
        """``resume.pdf`` stores raw bytes without any text encoding."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        pdf_bytes = b"%PDF-1.7\n\x00\x01\x02\xff binary payload"

        saved_path = save_pdf(app_dir, pdf_bytes)

        assert saved_path == app_dir / "resume.pdf"
        assert saved_path.read_bytes() == pdf_bytes

    def test_save_llm_response_round_trips_text(self, tmp_path: Path) -> None:
        """``llm_response.md`` stores the raw LLM text verbatim."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        response_text = "# Skills\nLanguages: Python\n---\n"

        saved_path = save_llm_response(app_dir, response_text)

        assert saved_path == app_dir / "llm_response.md"
        assert saved_path.read_text(encoding="utf-8") == response_text

    def test_save_request_json_round_trips_metadata_dict(self, tmp_path: Path) -> None:
        """``request.json`` serializes the D9 metadata dict losslessly."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        metadata = make_metadata(EXAMPLE_APPLICATION_ID, "2026-08-02T14:30:45Z")

        saved_path = save_request_json(app_dir, metadata)

        assert saved_path == app_dir / "request.json"
        assert json.loads(saved_path.read_text(encoding="utf-8")) == metadata

    def test_all_save_helpers_write_inside_app_dir(self, tmp_path: Path) -> None:
        """Every save helper places its file directly in the app dir."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        saved_paths = [
            save_tex(app_dir, "tex"),
            save_pdf(app_dir, b"pdf"),
            save_llm_response(app_dir, "md"),
            save_request_json(app_dir, {"ok": True}),
        ]

        assert len(saved_paths) == 4
        assert all(path.parent == app_dir for path in saved_paths)


class TestApplicationDirLookup:
    """Resolution of an app dir by id; missing dirs are 404-style."""

    def test_application_dir_returns_path_for_existing_dir(self, tmp_path: Path) -> None:
        """An existing application resolves to its directory."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)

        assert application_dir(tmp_path, EXAMPLE_APPLICATION_ID) == app_dir

    def test_application_dir_missing_raises_file_not_found(self, tmp_path: Path) -> None:
        """A missing application raises FileNotFoundError, never a partial path."""

        with pytest.raises(FileNotFoundError):
            application_dir(tmp_path, "application-20260802-000000")


class TestListApplications:
    """History listing: descending order and request.json metadata."""

    def test_list_applications_empty_root_returns_empty_list(self, tmp_path: Path) -> None:
        """A root with no applications yields [].

        An empty directory is a valid state for a fresh install.
        """

        assert list_applications(tmp_path) == []

    def test_list_applications_sorted_descending_by_application_id(self, tmp_path: Path) -> None:
        """Applications are listed newest first by application_id."""

        older_dir = create_application_dir(tmp_path, "application-20260802-143045")
        newer_dir = create_application_dir(tmp_path, "application-20260802-153000")
        save_request_json(older_dir, make_metadata("application-20260802-143045", "2026-08-02T14:30:45Z"))
        save_request_json(newer_dir, make_metadata("application-20260802-153000", "2026-08-02T15:30:00Z"))

        listed = list_applications(tmp_path)

        assert [entry["application_id"] for entry in listed] == [
            "application-20260802-153000",
            "application-20260802-143045",
        ]

    def test_list_applications_returns_request_json_metadata(self, tmp_path: Path) -> None:
        """Each listed entry is the full metadata dict from request.json."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        metadata = make_metadata(EXAMPLE_APPLICATION_ID, "2026-08-02T14:30:45Z")
        save_request_json(app_dir, metadata)

        assert list_applications(tmp_path) == [metadata]
