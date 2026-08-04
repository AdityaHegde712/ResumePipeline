"""Frozen spec tests for the cover-letter loader contract (T23, Phase 15).

LOCKED contract — ``backend/app/loader.py`` must satisfy this file exactly.
This file is frozen after Phase 15 and may not be modified to fit an
implementation. It is RED against the current code: the cover-letter loader
functions do not exist yet and are implemented in Phase 16 (T25).

Public interface (all exported from ``backend.app.loader``):

    PROMPT_FILENAME: str                      # must be "resume_prompt.md"
    COVER_LETTER_PROMPT_FILENAME: str         # must be "cover_letter_prompt.md"
    SUBJECTIVE_PROFILE_FILENAME: str          # must be "subjective_profile.md"

    def load_prompt(backend_dir: Path) -> str
    def load_cover_letter_prompt(backend_dir: Path) -> str
    def build_cover_letter_prompt(
        template: str,
        *,
        job_position: str,
        company_name: str,
        job_description: str,
        company_description: str | None,
        subjective_profile: str,
        llm_resume_response: str,
    ) -> str
    def load_subjective_profile(backend_dir: Path) -> str

Rules locked by these tests (PLAN D18, D25):

- ``PROMPT_FILENAME`` is ``"resume_prompt.md"`` (the renamed resume prompt,
  NOT ``llm_prompt.md``). ``load_prompt`` reads exactly that file from the
  given backend dir and never falls back to ``llm_prompt.md``.
- ``load_cover_letter_prompt`` reads exactly ``cover_letter_prompt.md``
  (utf-8) from the given backend dir; a missing file raises
  ``FileNotFoundError`` (no fallback to another filename).
- ``build_cover_letter_prompt`` fills ALL six placeholders
  ``{job_position}``, ``{company_name}``, ``{job_description}``,
  ``{company_desc_string}``, ``{subjective_profile}``,
  ``{llm_resume_response}`` and leaves no placeholder behind. It replaces
  exactly those six tokens and preserves any other ``{...}`` text verbatim.
- ``company_desc_string`` matches the resume builder (PLAN step 2): a
  non-empty ``company_description`` becomes ``- COMPANY DESCRIPTION: {desc}\\n``;
  ``None`` or an empty string yields ``""`` (no line emitted).
- ``load_subjective_profile`` returns ``""`` when the file is missing or
  empty, and the stripped file text when present.
"""

from pathlib import Path

import pytest

from backend.app.loader import (
    COVER_LETTER_PROMPT_FILENAME,
    PROMPT_FILENAME,
    SUBJECTIVE_PROFILE_FILENAME,
    build_cover_letter_prompt,
    load_cover_letter_prompt,
    load_prompt,
    load_subjective_profile,
)

# Hermetic synthetic template: the tests never read the real prompt file.
SYNTHETIC_TEMPLATE = (
    "Job: {job_position}\n"
    "Company: {company_name}\n"
    "Description: {job_description}\n"
    "{company_desc_string}"
    "Profile: {subjective_profile}\n"
    "Resume: {llm_resume_response}\n"
)

ALL_PLACEHOLDERS = (
    "{job_position}",
    "{company_name}",
    "{job_description}",
    "{company_desc_string}",
    "{subjective_profile}",
    "{llm_resume_response}",
)

COMPANY_DESC_PREFIX = "- COMPANY DESCRIPTION: "


def build_cover_letter(
    *,
    company_description: str | None = "AI startup",
    subjective_profile: str = "I value craft.",
    llm_resume_response: str = "# Skills\npython",
) -> str:
    """Call ``build_cover_letter_prompt`` with representative defaults."""

    return build_cover_letter_prompt(
        SYNTHETIC_TEMPLATE,
        job_position="Data Scientist Intern",
        company_name="SUHORA",
        job_description="Build ML features.",
        company_description=company_description,
        subjective_profile=subjective_profile,
        llm_resume_response=llm_resume_response,
    )


class TestPromptFilenames:
    """The locked prompt filename constants (D25 rename)."""

    def test_prompt_filename_is_resume_prompt_md(self) -> None:
        """The resume prompt constant points at the renamed file."""

        assert PROMPT_FILENAME == "resume_prompt.md"

    def test_cover_letter_prompt_filename(self) -> None:
        """The cover-letter prompt constant points at its exact file."""

        assert COVER_LETTER_PROMPT_FILENAME == "cover_letter_prompt.md"

    def test_subjective_profile_filename(self) -> None:
        """The subjective-profile constant points at its exact file."""

        assert SUBJECTIVE_PROFILE_FILENAME == "subjective_profile.md"


class TestLoadPrompt:
    """``load_prompt`` reads the renamed resume prompt, never the old name."""

    def test_load_prompt_reads_resume_prompt_not_llm_prompt(self, tmp_path: Path) -> None:
        """When both files exist, ``resume_prompt.md`` wins (D25)."""

        (tmp_path / "resume_prompt.md").write_text("RESUME PROMPT", encoding="utf-8")
        (tmp_path / "llm_prompt.md").write_text("OLD PROMPT", encoding="utf-8")

        assert load_prompt(tmp_path) == "RESUME PROMPT"


class TestLoadCoverLetterPrompt:
    """``load_cover_letter_prompt`` reads exactly ``cover_letter_prompt.md``."""

    def test_reads_cover_letter_prompt_md_utf8(self, tmp_path: Path) -> None:
        """The cover-letter template round-trips as utf-8 text."""

        template_text = "<context>\nJOB: {job_position} — ünïcode ✓\n</context>"
        (tmp_path / "cover_letter_prompt.md").write_text(template_text, encoding="utf-8")

        assert load_cover_letter_prompt(tmp_path) == template_text

    def test_missing_cover_letter_prompt_raises(self, tmp_path: Path) -> None:
        """A missing file raises FileNotFoundError (no fallback filename)."""

        with pytest.raises(FileNotFoundError):
            load_cover_letter_prompt(tmp_path)


class TestBuildCoverLetterPrompt:
    """``build_cover_letter_prompt`` fills all six placeholders (D18)."""

    def test_fills_all_six_placeholders(self) -> None:
        """Every placeholder is substituted with its exact value."""

        prompt = build_cover_letter(
            company_description="AI startup",
            subjective_profile="I value craft.",
            llm_resume_response="# Skills\npython",
        )

        expected = (
            "Job: Data Scientist Intern\n"
            "Company: SUHORA\n"
            "Description: Build ML features.\n"
            "- COMPANY DESCRIPTION: AI startup\n"
            "Profile: I value craft.\n"
            "Resume: # Skills\npython\n"
        )
        assert prompt == expected
        assert all(placeholder not in prompt for placeholder in ALL_PLACEHOLDERS)

    def test_company_description_none_emits_no_desc_line(self) -> None:
        """``None`` company description yields an empty desc string."""

        prompt = build_cover_letter(company_description=None)

        expected = (
            "Job: Data Scientist Intern\n"
            "Company: SUHORA\n"
            "Description: Build ML features.\n"
            "Profile: I value craft.\n"
            "Resume: # Skills\npython\n"
        )
        assert prompt == expected
        assert COMPANY_DESC_PREFIX not in prompt
        assert "{company_desc_string}" not in prompt

    def test_company_description_empty_string_emits_no_desc_line(self) -> None:
        """An empty-string company description behaves like ``None``."""

        prompt = build_cover_letter(company_description="")

        assert COMPANY_DESC_PREFIX not in prompt
        assert "{company_desc_string}" not in prompt

    def test_company_description_uses_exact_prefix(self) -> None:
        """A non-empty description uses the resume-builder prefix + newline."""

        prompt = build_cover_letter(company_description="A fast AI lab")

        assert f"{COMPANY_DESC_PREFIX}A fast AI lab\n" in prompt

    def test_subjective_profile_and_resume_response_round_trip(self) -> None:
        """Multi-line profile and resume text are preserved verbatim."""

        profile = "First line\nSecond line"
        resume = "# Skills\nLanguages: Python\n---\n# Experience\n"

        prompt = build_cover_letter(
            subjective_profile=profile,
            llm_resume_response=resume,
        )

        assert f"Profile: {profile}\n" in prompt
        assert f"Resume: {resume}\n" in prompt

    def test_unknown_braces_are_preserved(self) -> None:
        """Only the six placeholders are replaced; other braces survive."""

        prompt = build_cover_letter(
            subjective_profile="Note {x}",
            llm_resume_response="Keep {custom} intact",
        )

        assert "Note {x}" in prompt
        assert "Keep {custom} intact" in prompt


class TestLoadSubjectiveProfile:
    """``load_subjective_profile`` returns ``""`` for missing/empty files."""

    def test_missing_file_returns_empty_string(self, tmp_path: Path) -> None:
        """A backend dir without the profile file yields ``""``."""

        assert load_subjective_profile(tmp_path) == ""

    def test_empty_file_returns_empty_string(self, tmp_path: Path) -> None:
        """An empty profile file yields ``""``."""

        (tmp_path / "subjective_profile.md").write_text("", encoding="utf-8")

        assert load_subjective_profile(tmp_path) == ""

    def test_whitespace_only_file_returns_empty_string(self, tmp_path: Path) -> None:
        """A whitespace-only profile file strips to ``""``."""

        (tmp_path / "subjective_profile.md").write_text("  \n\t\n", encoding="utf-8")

        assert load_subjective_profile(tmp_path) == ""

    def test_present_file_returns_stripped_text(self, tmp_path: Path) -> None:
        """A present profile file returns its stripped text."""

        (tmp_path / "subjective_profile.md").write_text(
            "\n\n  I value craft and clarity.\n\n", encoding="utf-8"
        )

        assert load_subjective_profile(tmp_path) == "I value craft and clarity."