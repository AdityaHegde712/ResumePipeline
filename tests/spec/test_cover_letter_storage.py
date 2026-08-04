"""Frozen spec tests for the cover-letter storage contract (T24, Phase 15).

LOCKED contract — ``backend/app/storage.py`` must satisfy this file exactly.
This file is frozen after Phase 15 and may not be modified to fit an
implementation. It is RED against the current code: the cover-letter storage
functions do not exist yet and are implemented in Phase 16 (T25).

Public interface (all exported from ``backend.app.storage``):

    def save_cover_letter(app_dir: Path, text: str) -> Path
    def save_cover_letter_pdf(app_dir: Path, pdf_bytes: bytes) -> Path
    def update_request_json(app_dir: Path, updates: dict) -> Path

Rules locked by these tests (PLAN D9, D17, D20):

- ``save_cover_letter`` writes utf-8 ``cover_letter.md`` inside ``app_dir``
  and returns its Path. Text round-trips exactly, including non-ASCII
  characters. A missing app dir raises ``FileNotFoundError``.
- ``save_cover_letter_pdf`` writes raw bytes ``cover_letter.pdf`` inside
  ``app_dir`` and returns its Path. Bytes round-trip exactly. A missing app
  dir raises ``FileNotFoundError``.
- ``update_request_json`` merges the ``updates`` dict into the existing
  ``request.json`` WITHOUT clobbering existing keys (e.g. ``application_id``,
  ``job_position`` stay intact); keys present in ``updates`` override their
  prior values. It writes valid JSON and returns the ``request.json`` Path.
  A missing app dir or a missing ``request.json`` raises
  ``FileNotFoundError``.
"""

import json
from pathlib import Path

import pytest

from backend.app.storage import (
    create_application_dir,
    save_cover_letter,
    save_cover_letter_pdf,
    save_request_json,
    update_request_json,
)

EXAMPLE_APPLICATION_ID = "application-20260802-143045"

COVER_LETTER_TEXT = (
    "Dear Hiring Team,\n\n"
    "I am applying for the Data Scientist Intern role at SUHORA.\n\n"
    "Sincerely,\nAditya Hegde"
)


def make_metadata() -> dict:
    """Build representative D9 request.json metadata for an application."""

    return {
        "application_id": EXAMPLE_APPLICATION_ID,
        "job_position": "Data Scientist Intern",
        "company_name": "SUHORA Technologies Pvt. Ltd.",
        "company_description": None,
        "job_description": "Build and ship ML features.",
        "timestamp": "2026-08-02T14:30:45Z",
        "status": "completed",
        "llm_generation": "OK",
        "reconstruction": "OK",
        "saved": "OK",
        "pdf_error": None,
    }


class TestSaveCoverLetter:
    """``save_cover_letter`` writes utf-8 ``cover_letter.md``."""

    def test_save_cover_letter_round_trips_unicode_text(self, tmp_path: Path) -> None:
        """``cover_letter.md`` stores the utf-8 letter text byte-for-byte."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)

        saved_path = save_cover_letter(app_dir, COVER_LETTER_TEXT)

        assert saved_path == app_dir / "cover_letter.md"
        assert saved_path.read_text(encoding="utf-8") == COVER_LETTER_TEXT

    def test_save_cover_letter_missing_app_dir_raises(self, tmp_path: Path) -> None:
        """A missing app dir raises FileNotFoundError."""

        with pytest.raises(FileNotFoundError):
            save_cover_letter(tmp_path / "missing", COVER_LETTER_TEXT)


class TestSaveCoverLetterPdf:
    """``save_cover_letter_pdf`` writes binary ``cover_letter.pdf``."""

    def test_save_cover_letter_pdf_round_trips_binary_bytes(self, tmp_path: Path) -> None:
        """``cover_letter.pdf`` stores raw bytes without text encoding."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        pdf_bytes = b"%PDF-1.7\n\x00\x01\x02\xff binary payload"

        saved_path = save_cover_letter_pdf(app_dir, pdf_bytes)

        assert saved_path == app_dir / "cover_letter.pdf"
        assert saved_path.read_bytes() == pdf_bytes

    def test_save_cover_letter_pdf_missing_app_dir_raises(self, tmp_path: Path) -> None:
        """A missing app dir raises FileNotFoundError."""

        with pytest.raises(FileNotFoundError):
            save_cover_letter_pdf(tmp_path / "missing", b"%PDF-1.7")


class TestUpdateRequestJson:
    """``update_request_json`` merges cover-letter fields without clobbering."""

    def test_merges_updates_without_clobbering_existing_keys(self, tmp_path: Path) -> None:
        """Existing keys stay intact; new cover-letter keys are added."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        save_request_json(app_dir, make_metadata())
        updates = {
            "cover_letter": COVER_LETTER_TEXT,
            "cover_letter_generated": True,
            "cover_letter_error": None,
        }

        update_request_json(app_dir, updates)

        merged = json.loads((app_dir / "request.json").read_text(encoding="utf-8"))
        assert merged["application_id"] == EXAMPLE_APPLICATION_ID
        assert merged["job_position"] == "Data Scientist Intern"
        assert merged["company_name"] == "SUHORA Technologies Pvt. Ltd."
        assert merged["job_description"] == "Build and ship ML features."
        assert merged["status"] == "completed"
        assert merged["cover_letter"] == COVER_LETTER_TEXT
        assert merged["cover_letter_generated"] is True
        assert merged["cover_letter_error"] is None

    def test_updates_override_existing_cover_letter_keys(self, tmp_path: Path) -> None:
        """A key already present in request.json is overridden by the update."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        metadata = make_metadata()
        metadata["cover_letter_generated"] = False
        save_request_json(app_dir, metadata)

        update_request_json(app_dir, {"cover_letter_generated": True})

        merged = json.loads((app_dir / "request.json").read_text(encoding="utf-8"))
        assert merged["cover_letter_generated"] is True

    def test_returns_request_json_path(self, tmp_path: Path) -> None:
        """The function returns the ``request.json`` Path."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)
        save_request_json(app_dir, make_metadata())

        saved_path = update_request_json(app_dir, {"cover_letter_generated": True})

        assert saved_path == app_dir / "request.json"

    def test_missing_app_dir_raises(self, tmp_path: Path) -> None:
        """A missing app dir raises FileNotFoundError."""

        with pytest.raises(FileNotFoundError):
            update_request_json(tmp_path / "missing", {"cover_letter_generated": True})

    def test_missing_request_json_raises(self, tmp_path: Path) -> None:
        """An app dir without ``request.json`` raises FileNotFoundError."""

        app_dir = create_application_dir(tmp_path, EXAMPLE_APPLICATION_ID)

        with pytest.raises(FileNotFoundError):
            update_request_json(app_dir, {"cover_letter_generated": True})