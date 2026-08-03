"""Frozen spec tests for the LLM response parser (T03, T04).

LOCKED contract — ``backend/app/parser.py`` must satisfy this file exactly.
This file is frozen after Phase 1 and may not be modified to fit an
implementation.

Public interface (all exported from ``backend.app.parser``):

    parse_llm_response(raw_text: str) -> ParsedResume

    @dataclass ParsedResume:
        skills: list[tuple[str, str]]      # ordered (type, skills_str)
        experience: list[ExperienceEntry]  # positional, profile.yaml order
        projects: list[ProjectEntry]       # LLM relevance order

    @dataclass ExperienceEntry:
        label: str                         # text after ``## ``, verbatim
        bullets: list[str]                 # bullet prefixes stripped

    @dataclass ProjectEntry:
        index: int | None                  # leading sweep index, else None
        name: str                          # required; empty name is fatal
        tech: str | None                   # second `` | `` part, optional
        bullets: list[str]                 # bullet prefixes stripped

    class ReconstructionError(Exception):
        ...                                # message includes the phase name,
                                           # e.g. "reconstruction: skills"

Parsing rules locked by these tests (PLAN §4):

- Separator lines of 3+ dashes or equals signs (``---``, ``===``) are
  stripped before section splitting; 2-char lines such as ``--`` are content.
- Sections are delimited by exact ``# Skills``, ``# Experience``,
  ``# Projects`` headers in order; content after ``# Projects`` belongs to
  projects.
- Skills lines split on the FIRST colon only.
- Experience headers are lines starting ``## ``; subsequent non-blank lines
  are bullets with at most one ``- `` / ``• `` / ``* `` prefix stripped.
- Project headers split on `` | `` into 1-3 parts; a leading integer in the
  first part becomes ``index``; the third part (link) is NEVER stored.
- A missing section body or blank-only section yields [] for that field.
- An unparseable block raises ReconstructionError naming the phase.
"""

from pathlib import Path

import pytest

from backend.app.parser import (
    ExperienceEntry,
    ParsedResume,
    ProjectEntry,
    ReconstructionError,
    parse_llm_response,
)

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "llm_response_sample.txt"
FIXTURE_TEXT = FIXTURE_PATH.read_text(encoding="utf-8")


def assert_reconstruction_error(raw_text: str) -> None:
    """Assert that parsing ``raw_text`` fails with a reconstruction phase error."""

    with pytest.raises(ReconstructionError) as exc_info:
        parse_llm_response(raw_text)
    assert "reconstruction" in str(exc_info.value).lower()


class TestGoldenFixture:
    """Full happy-path parse of tests/fixtures/llm_response_sample.txt."""

    def test_golden_fixture_parses_all_sections(self) -> None:
        """The frozen fixture populates skills, experience, and projects."""

        result = parse_llm_response(FIXTURE_TEXT)

        assert isinstance(result, ParsedResume)
        assert result.skills == [
            ("Languages", "Python, TypeScript, JavaScript"),
            ("Frameworks", "React, FastAPI, PyTorch"),
            ("Developer Tools", "Docker, AWS, Git"),
            ("Domains", "LLM Integration, Multi-Agent Orchestration"),
        ]
        assert [entry.label for entry in result.experience] == [
            "Data Scientist Intern — SUHORA Technologies",
            "AI Research Assistant — San Jose State University",
            "Graduate Teaching Assistant — SJSU AI&ML Department",
        ]
        assert [project.index for project in result.projects] == [11, 1, 6, 13, 4, 10]
        assert [project.name for project in result.projects] == [
            "Sentry",
            "ARVR",
            "WorkoutApp",
            "Space Debris Research",
            "RecSysProject",
            "Course Visualizer",
        ]
        assert [project.tech for project in result.projects] == [
            "Python, FastAPI, YOLO",
            "React, TypeScript, Three.js, WebXR",
            "React Native, Firebase, Expo",
            "Python, PyTorch, NumPy",
            "PyTorch, Pandas, Scikit-Learn",
            "React, D3.js, FastAPI",
        ]

    def test_golden_fixture_first_experience_bullets_are_exact(self) -> None:
        """The first experience entry keeps its three bullets verbatim."""

        result = parse_llm_response(FIXTURE_TEXT)

        assert result.experience[0].bullets == [
            "Built a real-time vision pipeline for maritime surveillance, processing 900+ SAR and optical satellite images.",
            "Engineered a C# and Python preprocessing system with parallelized GPU usage, cutting batch inference latency from 7 minutes to under 1 minute.",
            "Produced GIS-compatible GeoJSON outputs via overlap-aware postprocessing, enabling downstream geospatial ingestion.",
        ]

    def test_golden_fixture_all_bullet_prefixes_stripped(self) -> None:
        """No parsed bullet retains a ``- `` prefix from the fixture."""

        result = parse_llm_response(FIXTURE_TEXT)
        all_bullets = [
            bullet
            for entry in result.experience
            for bullet in entry.bullets
        ] + [
            bullet
            for project in result.projects
            for bullet in project.bullets
        ]

        assert all_bullets
        assert all(not bullet.startswith("- ") for bullet in all_bullets)

    def test_golden_fixture_projects_never_store_link(self) -> None:
        """Project entries expose no link attribute; the ``| -`` slot is dropped."""

        result = parse_llm_response(FIXTURE_TEXT)

        assert result.projects
        assert all(not hasattr(project, "link") for project in result.projects)


class TestSeparators:
    """Separator-line stripping (3+ dashes/equals, 2-char lines kept)."""

    def test_separator_lines_are_stripped(self) -> None:
        """``---`` and ``===`` lines disappear from every block."""

        raw = (
            "# Skills\n"
            "Languages: Python\n"
            "---\n"
            "===\n"
            "# Experience\n"
            "---\n"
            "## Role A\n"
            "- bullet one\n"
            "# Projects\n"
            "## 1. Proj A | Tech | -\n"
            "---\n"
            "- bullet two\n"
        )

        result = parse_llm_response(raw)

        assert result.skills == [("Languages", "Python")]
        assert result.experience == [ExperienceEntry(label="Role A", bullets=["bullet one"])]
        assert result.projects == [
            ProjectEntry(index=1, name="Proj A", tech="Tech", bullets=["bullet two"])
        ]

    def test_two_char_dash_line_is_content_not_separator(self) -> None:
        """A 2-char ``--`` line is not a separator; it survives as a bullet."""

        raw = (
            "# Skills\n"
            "Languages: Python\n"
            "# Experience\n"
            "## Role A\n"
            "--\n"
            "- bullet one\n"
        )

        result = parse_llm_response(raw)

        assert result.experience[0].bullets == ["--", "bullet one"]


class TestSectionSplit:
    """Section headers split the response into skills/experience/projects."""

    def test_sections_are_split_in_order(self) -> None:
        """Skills, experience, and projects map to their own blocks in order."""

        raw = (
            "# Skills\n"
            "Languages: Python\n"
            "# Experience\n"
            "## Role A\n"
            "- bullet\n"
            "# Projects\n"
            "## 1. Proj A | Tech | -\n"
            "- project bullet\n"
        )

        result = parse_llm_response(raw)

        assert result.skills == [("Languages", "Python")]
        assert [entry.label for entry in result.experience] == ["Role A"]
        assert [project.name for project in result.projects] == ["Proj A"]

    def test_content_after_projects_header_belongs_to_projects(self) -> None:
        """Everything after ``# Projects`` is parsed as project content."""

        raw = (
            "# Skills\n"
            "Languages: Python\n"
            "# Experience\n"
            "## Role A\n"
            "- bullet\n"
            "# Projects\n"
            "## 1. Proj A | Tech | -\n"
            "- project bullet\n"
            "Languages: JavaScript\n"
        )

        result = parse_llm_response(raw)

        assert result.skills == [("Languages", "Python")]
        assert result.projects[0].bullets == ["project bullet", "Languages: JavaScript"]


class TestSkillsParsing:
    """Skills block lines of the form ``type: skill_1, skill_2``."""

    def test_skills_line_splits_on_first_colon(self) -> None:
        """``type: a, b`` parses to (type, "a, b") using the first colon."""

        raw = "# Skills\nLanguages: Python, TypeScript\n"

        result = parse_llm_response(raw)

        assert result.skills == [("Languages", "Python, TypeScript")]

    def test_skills_value_keeps_remaining_colons(self) -> None:
        """Only the first colon is the separator; later colons stay in the value."""

        raw = "# Skills\nLanguages: Python: Advanced\n"

        result = parse_llm_response(raw)

        assert result.skills == [("Languages", "Python: Advanced")]


class TestExperienceParsing:
    """Experience headers and positional entry mapping."""

    def test_experience_entries_preserve_positional_order(self) -> None:
        """Each ``## `` header starts a new entry; order maps to profile.yaml."""

        raw = (
            "# Experience\n"
            "## Software Engineer — Acme Corp\n"
            "- bullet a1\n"
            "## Data Scientist — Globex\n"
            "- bullet b1\n"
            "- bullet b2\n"
            "## Intern — Initech\n"
            "- bullet c1\n"
        )

        result = parse_llm_response(raw)

        assert [entry.label for entry in result.experience] == [
            "Software Engineer — Acme Corp",
            "Data Scientist — Globex",
            "Intern — Initech",
        ]
        assert result.experience[0].bullets == ["bullet a1"]
        assert result.experience[1].bullets == ["bullet b1", "bullet b2"]
        assert result.experience[2].bullets == ["bullet c1"]

    def test_bullet_prefixes_are_stripped(self) -> None:
        """``- ``, ``• ``, and ``* `` prefixes are stripped; plain lines kept."""

        raw = (
            "# Experience\n"
            "## Role\n"
            "- dash\n"
            "• bullet\n"
            "* star\n"
            "plain\n"
        )

        result = parse_llm_response(raw)

        assert result.experience[0].bullets == ["dash", "bullet", "star", "plain"]


class TestProjectParsing:
    """Project headers of the form ``## N. name | tech | link``."""

    def test_project_header_with_index_name_and_tech(self) -> None:
        """``## N. name | tech | -`` yields index, name, and tech."""

        raw = "# Projects\n## 12. Safety | YOLO | -\n- bullet\n"

        result = parse_llm_response(raw)

        assert result.projects == [
            ProjectEntry(index=12, name="Safety", tech="YOLO", bullets=["bullet"])
        ]

    def test_project_header_without_index_has_none_index(self) -> None:
        """A header without a leading integer still parses with index None."""

        raw = "# Projects\n## Sentry | Python, FastAPI | -\n- bullet\n"

        result = parse_llm_response(raw)

        project = result.projects[0]
        assert project.index is None
        assert project.name == "Sentry"
        assert project.tech == "Python, FastAPI"

    def test_project_link_is_never_stored(self) -> None:
        """The third `` | `` part (placeholder or URL) never appears on the entry."""

        raw = (
            "# Projects\n"
            "## 3. DailyBrief | Python, Typer | -\n"
            "- bullet\n"
            "## 4. RecSys | PyTorch | https://github.com/x/y\n"
            "- bullet\n"
        )

        result = parse_llm_response(raw)

        assert len(result.projects) == 2
        assert result.projects[0].tech == "Python, Typer"
        assert result.projects[1].tech == "PyTorch"
        assert not hasattr(result.projects[0], "link")
        assert not hasattr(result.projects[1], "link")

    def test_project_without_tech_or_link_parses(self) -> None:
        """A bare ``## name`` header is valid: index None and tech None."""

        raw = "# Projects\n## Portfolio Website\n- bullet\n"

        result = parse_llm_response(raw)

        project = result.projects[0]
        assert project.index is None
        assert project.name == "Portfolio Website"
        assert project.tech is None

    def test_project_header_too_many_parts_raises(self) -> None:
        """A header split into more than 3 `` | `` parts is malformed."""

        assert_reconstruction_error("# Projects\n## 1. Name | Tech | - | extra\n- bullet\n")


class TestEmptyBlocks:
    """Empty or missing sections produce empty lists."""

    def test_missing_sections_yield_empty_lists(self) -> None:
        """Headers with no body produce [] for that field."""

        raw = (
            "# Skills\n"
            "# Experience\n"
            "# Projects\n"
        )

        result = parse_llm_response(raw)

        assert result.skills == []
        assert result.experience == []
        assert result.projects == []

    def test_blank_only_block_yields_empty_list(self) -> None:
        """A section containing only blank or whitespace lines yields []."""

        raw = (
            "# Skills\n"
            "Languages: Python\n"
            "# Experience\n"
            "\n"
            "   \n"
            "# Projects\n"
            "## 1. Name | Tech | -\n"
            "- bullet\n"
        )

        result = parse_llm_response(raw)

        assert result.skills == [("Languages", "Python")]
        assert result.experience == []
        assert len(result.projects) == 1

    def test_empty_raw_text_yields_empty_lists(self) -> None:
        """An empty response parses to an empty ParsedResume, not an error."""

        result = parse_llm_response("")

        assert result == ParsedResume(skills=[], experience=[], projects=[])


class TestMalformedInput:
    """Unparseable blocks raise ReconstructionError naming the phase."""

    def test_skills_line_without_colon_raises(self) -> None:
        """A ``# Skills`` line without a colon is unparseable and fatal."""

        assert_reconstruction_error("# Skills\nPython\n")

    def test_project_header_with_missing_name_raises(self) -> None:
        """A project header with an index but no name is unparseable and fatal."""

        assert_reconstruction_error("# Projects\n## 5. | Tech | -\n- bullet\n")
