r"""Frozen spec tests for the LaTeX assembler (T06, Phase 3).

LOCKED contract — ``backend.app.assembler`` must satisfy this file exactly.
Amended by Owner decision (2026-08-03): the section wrapper templates
(``experience_top``/``experience_bottom``, ``projects_top``/``project_bottom``,
and ``project_entry_separator``) ARE part of the contract. The previous
wrapper-free contract was incorrect and has been replaced.

Public interface (all exported from ``backend.app.assembler``):

    def assemble_resume(
        parsed: ParsedResume,
        profile: dict,
        sweep_headings: dict[int, str],
        project_links: dict[int, str],
    ) -> str:

    def escape_latex(text: str) -> str:

Parameter shapes:

- ``parsed``: a ``ParsedResume`` from ``backend.app.parser`` (skills,
  experience, and projects exactly as the parser produces them).
- ``profile``: a plain dict mirroring ``backend/profile.yaml``. Only these
  keys are read:
  * ``section_order``: list[str] — the order in which sections render.
  * ``skills``: dict[str, list[str]] with keys ``languages``,
    ``frameworks``, ``tools``, ``domains`` (fallback groups only).
  * ``experience``: list[dict] with keys ``role``, ``company``,
    ``location``, ``start_date``, ``end_date``, ``highlights`` (list[str]).
- ``sweep_headings``: dict[int, str] mapping project sweep index -> heading
  text (used only for fuzzy link fallback).
- ``project_links``: dict[int, str] mapping project sweep index -> URL.

Assembly rules locked by these tests (PLAN §5):

- Iterate ``profile["section_order"]`` in order and build one section per
  key. Full document = ``topmatter`` + ordered sections + ``bottommatter``
  joined with ``"\n\n"``.
- ``education``, ``publications``, ``leadership`` render verbatim from
  ``backend.resume_config``. ``certifications`` always renders nothing.
- ``skills``: each LLM ``(type, skills_str)`` line becomes one
  ``skills_bullet`` line; fallback (no LLM lines) maps the four profile
  groups ``languages``/``frameworks``/``tools``/``domains`` to labels
  ``Languages``/``Frameworks``/``Developer Tools``/``Domains``, each
  group's items joined with ``", "``.
- ``experience``: the section is ``experience_top`` + entries +
  ``experience_bottom``. One entry per profile entry i. Metadata (role,
  company, location, ``"start_date -- end_date"``) comes from the profile;
  bullets come from ``parsed.experience[i].bullets``. When entry i is
  missing or has no bullets, the profile entry's ``highlights`` are used.
  Extra LLM entries beyond the profile length are ignored. Entries are
  concatenated with NO separator; each entry is
  ``experience_entry_top`` + ``"\n"`` + bullets joined by ``"\n"`` +
  ``experience_entry_bottom``.
- ``projects``: the section is ``projects_top`` + entries joined with
  ``"\n" + project_entry_separator + "\n"`` + ``project_bottom``. One
  entry per parsed project, rendered in LLM output order (relevance) —
  never sorted by index. Each entry is ``project_entry_top`` + bullets
  joined by ``"\n"`` + ``project_entry_bottom``.
- Project link resolution: exact ``project_links[project.index]`` first;
  else a normalized fuzzy match of the project name against
  ``sweep_headings`` (lowercase, collapse non-alphanumerics to a space;
  exact -> containment -> token overlap >= 0.5) to derive an index, then
  ``project_links[index]``; else the link is omitted entirely and the
  ``\resumeLink`` macro is NOT emitted (the heading's second argument is
  an empty ``{}``).
- ALL LLM-derived and profile-fallback text is escaped with
  ``escape_latex``; static ``resume_config`` templates are never escaped.
- Empty sections (no content) are omitted from the document.
- The wrapped experience and projects sections therefore DO contain
  ``\section{\textbf{Experience}}`` and ``\section{\textbf{Projects}}``.
  When ``section_order`` lists experience before projects, the experience
  section renders first.

``escape_latex`` replaces every occurrence of these ten characters in a
single pass (left-to-right, inserted escapes are not re-scanned):

    \    ->   \textbackslash{}
    {    ->   \{
    }    ->   \}
    $    ->   \$
    %    ->   \%
    &    ->   \&
    #    ->   \#
    _    ->   \_
    ^    ->   \^{}
    ~    ->   \textasciitilde{}
"""

from pathlib import Path

import pytest

from backend.app.assembler import assemble_resume, escape_latex
from backend.app.parser import (
    ExperienceEntry,
    ParsedResume,
    ProjectEntry,
    parse_llm_response,
)
from backend.resume_config import (
    bottommatter,
    education,
    experience_bottom,
    experience_entry_bottom,
    experience_entry_bullet,
    experience_entry_top,
    experience_top,
    leadership,
    project_bottom,
    project_entry_bottom,
    project_entry_bullet,
    project_entry_separator,
    project_entry_top,
    projects_top,
    publications,
    skills_bottom,
    skills_bullet,
    skills_top,
    topmatter,
)

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "llm_response_sample.txt"
PARSED_GOLDEN = parse_llm_response(FIXTURE_PATH.read_text(encoding="utf-8"))

GOLDEN_SWEEP_HEADINGS = {
    11: "Sentry",
    1: "ARVR",
    6: "WorkoutApp",
    13: "Space Debris Research",
    4: "RecSysProject",
    10: "Course Visualizer",
}

GOLDEN_PROJECT_LINKS = {
    1: "https://github.com/AdityaHegde712/ARVR",
    2: "https://github.com/AdityaHegde712/Autoencoders-for-Compression",
    3: "https://github.com/AdityaHegde712/dailybrief",
    4: "https://github.com/AdityaHegde712/RecSysProject",
    5: "https://github.com/AdityaHegde712/UniversalAssistant/",
    6: "https://github.com/AdityaHegde712/FitnessTracker",
    7: "https://github.com/AdityaHegde712/Agentic-Cybersecurity-Lab",
    8: "https://github.com/AdityaHegde712/AdityaHegde712.github.io",
    9: "https://github.com/AdityaHegde712/Recommender-Systems-Kaggle-Assignment",
    10: "https://github.com/AdityaHegde712/Course-Visualizer",
    11: "https://github.com/Aero-inc/sentry",
    12: "https://github.com/AdityaHegde712/Industrial-Safety-Detection",
    13: "https://github.com/AdityaHegde712/SpaceDebrisResearch",
    14: "https://github.com/AdityaHegde712/agent-setup",
}


def build_golden_profile() -> dict:
    """Mirror the relevant keys of backend/profile.yaml for hermetic tests."""

    return {
        "section_order": [
            "education",
            "skills",
            "experience",
            "projects",
            "publications",
            "leadership",
            "certifications",
        ],
        "skills": {
            "languages": ["Python", "C++ (proficient)", "JavaScript", "HTML/CSS"],
            "frameworks": ["PyTorch", "TensorFlow", "ONNX"],
            "tools": ["Docker", "Terraform", "Git"],
            "domains": ["LLM Integration", "Multi-Agent Orchestration"],
        },
        "experience": [
            {
                "role": "Data Scientist Intern",
                "company": "SUHORA Technologies Pvt. Ltd.",
                "location": "Uttar Pradesh, India",
                "start_date": "Mar 2024",
                "end_date": "Jul 2024",
                "highlights": [
                    "Built a real-time vision pipeline for maritime surveillance, processing 900+ SAR and optical satellite images while sustaining over 95% evaluation accuracy and improving detection performance by 40%+ mAP.",
                    "Engineered a C#+Python preprocessing system with parallelized GPU usage, runtime memory guards, and overflow controls, reducing batch inference latency from 7 minutes to sub-1 minute for deployment.",
                    "Stress-tested the pipeline against 15B-pixel batches, achieved 45-second processing per 10,000 km² image, and built a fault-tolerant ingestion system monitoring NAS for continued high-resolution geospatial input.",
                    "Produced GIS-compatible GeoJSON outputs via overlap-aware postprocessing, integrated structured logging with automated exception reporting for rapid debugging, collaborating with engineers to ship models.",
                ],
            }
        ],
    }


def expected_skills_section(groups: list[tuple[str, str]]) -> str:
    """Compose the expected skills section; ``groups`` are (type, skills) pairs, pre-escaped."""

    bullet_lines = [
        skills_bullet.format(type=stype, skills=skills)
        for stype, skills in groups
    ]
    return skills_top + "\n".join(bullet_lines) + skills_bottom


def expected_experience_section(entries: list[dict]) -> str:
    """Compose the expected wrapped experience section; each entry's bullets must be pre-escaped."""

    rendered = []
    for entry in entries:
        rendered.append(
            experience_entry_top.format(
                experience_name=entry["role"],
                experience_start_end=f"{entry['start_date']} -- {entry['end_date']}",
                company_name=entry["company"],
                location=entry["location"],
            )
            + "\n"
            + "\n".join(
                experience_entry_bullet.format(bullet=bullet)
                for bullet in entry["bullets"]
            )
            + experience_entry_bottom
        )
    return experience_top + "".join(rendered) + experience_bottom


def expected_project_entry(
    name: str,
    tech: str | None,
    link: str | None,
    bullets: list[str],
) -> str:
    """Compose one expected project entry; name, tech, link, and bullets are pre-escaped."""

    if link is None:
        heading = project_entry_top.format(
            project_name=name,
            tech_stack=tech or "",
            link="",
        ).replace("{\\resumeLink{}}", "{}")
    else:
        heading = project_entry_top.format(
            project_name=name,
            tech_stack=tech or "",
            link=link,
        )
    return (
        heading
        + "\n".join(project_entry_bullet.format(bullet=bullet) for bullet in bullets)
        + project_entry_bottom
    )


def expected_projects_section(entries: list[str]) -> str:
    """Compose the expected wrapped projects section; ``entries`` are pre-rendered project entries."""

    return (
        projects_top
        + ("\n" + project_entry_separator + "\n").join(entries)
        + project_bottom
    )


class TestEscapeLatex:
    """The pure ``escape_latex`` function is the frozen escaping contract."""

    def test_empty_string_is_unchanged(self) -> None:
        assert escape_latex("") == ""

    def test_plain_text_without_special_characters_is_unchanged(self) -> None:
        assert escape_latex("Plain text, Python - 123 / ok") == "Plain text, Python - 123 / ok"

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("\\", "\\textbackslash{}"),
            ("{", "\\{"),
            ("}", "\\}"),
            ("$", "\\$"),
            ("%", "\\%"),
            ("&", "\\&"),
            ("#", "\\#"),
            ("_", "\\_"),
            ("^", "\\^{}"),
            ("~", "\\textasciitilde{}"),
        ],
    )
    def test_special_character_is_escaped(self, raw: str, expected: str) -> None:
        assert escape_latex(raw) == expected

    def test_compound_text_escapes_all_special_characters(self) -> None:
        raw = r"A&B #2 {a} 100% $5 _x y^2 ~"
        expected = r"A\&B \#2 \{a\} 100\% \$5 \_x y\^{}2 \textasciitilde{}"
        assert escape_latex(raw) == expected


class TestSkillsSection:
    """Skills: LLM path, profile fallback, and escaping."""

    def test_llm_skills_are_used_when_present(self) -> None:
        parsed = ParsedResume(
            skills=[("Languages", "Python, TypeScript"), ("Frameworks", "React, FastAPI")],
            experience=[],
            projects=[],
        )
        profile = {
            "section_order": ["skills"],
            "skills": {"languages": ["Python"], "frameworks": ["PyTorch"], "tools": [], "domains": []},
            "experience": [],
        }
        expected_skills = expected_skills_section(
            [("Languages", "Python, TypeScript"), ("Frameworks", "React, FastAPI")]
        )
        doc = assemble_resume(parsed, profile, {}, {})
        assert doc == "\n\n".join([topmatter, expected_skills, bottommatter])

    def test_profile_skills_fallback_when_llm_skills_empty(self) -> None:
        parsed = ParsedResume(skills=[], experience=[], projects=[])
        profile = {
            "section_order": ["skills"],
            "skills": {
                "languages": ["Python", "TypeScript"],
                "frameworks": ["PyTorch"],
                "tools": ["Docker", "Git"],
                "domains": ["LLM Integration"],
            },
            "experience": [],
        }
        expected_skills = expected_skills_section(
            [
                ("Languages", "Python, TypeScript"),
                ("Frameworks", "PyTorch"),
                ("Developer Tools", "Docker, Git"),
                ("Domains", "LLM Integration"),
            ]
        )
        doc = assemble_resume(parsed, profile, {}, {})
        assert doc == "\n\n".join([topmatter, expected_skills, bottommatter])

    def test_llm_skills_win_over_profile_fallback(self) -> None:
        parsed = ParsedResume(skills=[("Languages", "Python")], experience=[], projects=[])
        profile = {
            "section_order": ["skills"],
            "skills": {"languages": ["Rust"], "frameworks": [], "tools": [], "domains": []},
            "experience": [],
        }
        doc = assemble_resume(parsed, profile, {}, {})
        assert "Python" in doc
        assert "Rust" not in doc

    def test_skills_text_is_escaped(self) -> None:
        parsed = ParsedResume(
            skills=[("Languages", "C++ & C# (100%)"), ("AI & ML", "x ~ y ^ z")],
            experience=[],
            projects=[],
        )
        profile = {"section_order": ["skills"], "skills": {}, "experience": []}
        doc = assemble_resume(parsed, profile, {}, {})
        assert "\\textbf{Languages}: C++ \\& C\\# (100\\%) \\\\" in doc
        assert "\\textbf{AI \\& ML}: x \\textasciitilde{} y \\^{} z \\\\" in doc


class TestExperienceSection:
    """Experience: profile metadata, positional LLM bullets, highlights fallback."""

    def test_profile_metadata_with_llm_bullets_and_extra_entries_ignored(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[
                ExperienceEntry(
                    label="Data Scientist Intern — SUHORA Technologies",
                    bullets=[
                        "Built a real-time vision pipeline for maritime surveillance, processing 900+ SAR and optical satellite images.",
                        "Engineered a C# and Python preprocessing system with parallelized GPU usage, cutting batch inference latency from 7 minutes to under 1 minute.",
                        "Produced GIS-compatible GeoJSON outputs via overlap-aware postprocessing, enabling downstream geospatial ingestion.",
                    ],
                ),
                ExperienceEntry(
                    label="AI Research Assistant — San Jose State University",
                    bullets=["ignored entry bullets"],
                ),
                ExperienceEntry(
                    label="Graduate Teaching Assistant — SJSU AI&ML Department",
                    bullets=["ignored entry bullets"],
                ),
            ],
            projects=[],
        )
        profile = {
            "section_order": ["experience"],
            "skills": {},
            "experience": [
                {
                    "role": "Data Scientist Intern",
                    "company": "SUHORA Technologies Pvt. Ltd.",
                    "location": "Uttar Pradesh, India",
                    "start_date": "Mar 2024",
                    "end_date": "Jul 2024",
                    "highlights": ["fallback highlight that must not appear"],
                }
            ],
        }
        escaped_bullets = [
            "Built a real-time vision pipeline for maritime surveillance, processing 900+ SAR and optical satellite images.",
            "Engineered a C\\# and Python preprocessing system with parallelized GPU usage, cutting batch inference latency from 7 minutes to under 1 minute.",
            "Produced GIS-compatible GeoJSON outputs via overlap-aware postprocessing, enabling downstream geospatial ingestion.",
        ]
        expected_section = expected_experience_section(
            [
                {
                    "role": "Data Scientist Intern",
                    "company": "SUHORA Technologies Pvt. Ltd.",
                    "location": "Uttar Pradesh, India",
                    "start_date": "Mar 2024",
                    "end_date": "Jul 2024",
                    "bullets": escaped_bullets,
                }
            ]
        )
        doc = assemble_resume(parsed, profile, {}, {})
        assert "\\section{\\textbf{Experience}}" in doc
        assert doc == "\n\n".join([topmatter, expected_section, bottommatter])
        assert doc.count("\n    \\resumeSubheading") == 1
        assert "AI Research Assistant" not in doc
        assert "Graduate Teaching Assistant" not in doc

    def test_highlights_fallback_when_llm_bullets_missing(self) -> None:
        parsed = ParsedResume(skills=[], experience=[], projects=[])
        profile = {
            "section_order": ["experience"],
            "skills": {},
            "experience": [
                {
                    "role": "Data Scientist Intern",
                    "company": "SUHORA Technologies Pvt. Ltd.",
                    "location": "Uttar Pradesh, India",
                    "start_date": "Mar 2024",
                    "end_date": "Jul 2024",
                    "highlights": [
                        "Achieved over 95% evaluation accuracy and improved detection performance by 40%+ mAP.",
                        "Built a C#+Python preprocessing system with parallelized GPU usage.",
                    ],
                }
            ],
        }
        escaped_bullets = [
            "Achieved over 95\\% evaluation accuracy and improved detection performance by 40\\%+ mAP.",
            "Built a C\\#+Python preprocessing system with parallelized GPU usage.",
        ]
        expected_section = expected_experience_section(
            [
                {
                    "role": "Data Scientist Intern",
                    "company": "SUHORA Technologies Pvt. Ltd.",
                    "location": "Uttar Pradesh, India",
                    "start_date": "Mar 2024",
                    "end_date": "Jul 2024",
                    "bullets": escaped_bullets,
                }
            ]
        )
        doc = assemble_resume(parsed, profile, {}, {})
        assert "\\section{\\textbf{Experience}}" in doc
        assert doc == "\n\n".join([topmatter, expected_section, bottommatter])

    def test_partial_llm_bullets_fall_back_per_entry(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[ExperienceEntry(label="First Role", bullets=["LLM bullet for first role"])],
            projects=[],
        )
        profile = {
            "section_order": ["experience"],
            "skills": {},
            "experience": [
                {
                    "role": "First Role",
                    "company": "Acme",
                    "location": "NY",
                    "start_date": "Jan 2020",
                    "end_date": "Dec 2020",
                    "highlights": ["WRONG highlight for first role"],
                },
                {
                    "role": "Second Role",
                    "company": "Globex",
                    "location": "CA",
                    "start_date": "Jan 2021",
                    "end_date": "Dec 2021",
                    "highlights": ["Right highlight for second role"],
                },
            ],
        }
        doc = assemble_resume(parsed, profile, {}, {})
        assert "\\section{\\textbf{Experience}}" in doc
        assert doc.count("\n    \\resumeSubheading") == 2
        assert "LLM bullet for first role" in doc
        assert "WRONG highlight for first role" not in doc
        assert "Right highlight for second role" in doc

    def test_experience_metadata_is_escaped(self) -> None:
        parsed = ParsedResume(skills=[], experience=[], projects=[])
        profile = {
            "section_order": ["experience"],
            "skills": {},
            "experience": [
                {
                    "role": "AI & ML Engineer #1",
                    "company": "X Corp",
                    "location": "San Jose, CA",
                    "start_date": "Mar 2024",
                    "end_date": "Jul 2024",
                    "highlights": [],
                }
            ],
        }
        doc = assemble_resume(parsed, profile, {}, {})
        assert "\\section{\\textbf{Experience}}" in doc
        assert "AI \\& ML Engineer \\#1" in doc


class TestProjectsSection:
    """Projects: LLM relevance order, link resolution, and escaping."""

    def test_projects_render_in_llm_order_not_sorted_by_index(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[],
            projects=[
                ProjectEntry(
                    index=11,
                    name="Sentry",
                    tech="Python, FastAPI, YOLO",
                    bullets=["Built a real-time video threat detection platform."],
                ),
                ProjectEntry(
                    index=1,
                    name="ARVR",
                    tech="React, TypeScript, Three.js, WebXR",
                    bullets=["Developed a PWA for natural-language furniture search."],
                ),
                ProjectEntry(
                    index=6,
                    name="WorkoutApp",
                    tech="React Native, Firebase, Expo",
                    bullets=["Built a cross-platform fitness tracker."],
                ),
            ],
        )
        profile = {"section_order": ["projects"], "skills": {}, "experience": []}
        expected_section = expected_projects_section(
            [
                expected_project_entry(
                    name="Sentry",
                    tech="Python, FastAPI, YOLO",
                    link="https://github.com/Aero-inc/sentry",
                    bullets=["Built a real-time video threat detection platform."],
                ),
                expected_project_entry(
                    name="ARVR",
                    tech="React, TypeScript, Three.js, WebXR",
                    link="https://github.com/AdityaHegde712/ARVR",
                    bullets=["Developed a PWA for natural-language furniture search."],
                ),
                expected_project_entry(
                    name="WorkoutApp",
                    tech="React Native, Firebase, Expo",
                    link="https://github.com/AdityaHegde712/FitnessTracker",
                    bullets=["Built a cross-platform fitness tracker."],
                ),
            ]
        )
        doc = assemble_resume(parsed, profile, GOLDEN_SWEEP_HEADINGS, GOLDEN_PROJECT_LINKS)
        assert "\\section{\\textbf{Projects}}" in doc
        assert doc.count("\n\\vspace{-2pt}\n") == 2
        assert doc == "\n\n".join([topmatter, expected_section, bottommatter])
        assert doc.index("Sentry") < doc.index("ARVR") < doc.index("WorkoutApp")
        assert "\\resumeLink{https://github.com/Aero-inc/sentry}" in doc
        assert "\\resumeLink{https://github.com/AdityaHegde712/ARVR}" in doc
        assert "\\resumeLink{https://github.com/AdityaHegde712/FitnessTracker}" in doc

    def test_link_resolves_by_exact_index(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[],
            projects=[ProjectEntry(index=11, name="Sentry", tech="Python", bullets=["b"])],
        )
        profile = {"section_order": ["projects"], "skills": {}, "experience": []}
        expected_section = expected_projects_section(
            [
                expected_project_entry(
                    name="Sentry",
                    tech="Python",
                    link="https://github.com/Aero-inc/sentry",
                    bullets=["b"],
                )
            ]
        )
        doc = assemble_resume(parsed, profile, GOLDEN_SWEEP_HEADINGS, GOLDEN_PROJECT_LINKS)
        assert "\\section{\\textbf{Projects}}" in doc
        assert doc == "\n\n".join([topmatter, expected_section, bottommatter])
        assert "\\resumeLink{https://github.com/Aero-inc/sentry}" in doc

    def test_index_missing_from_links_falls_back_to_name(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[],
            projects=[ProjectEntry(index=999, name="ARVR", tech="React", bullets=["b"])],
        )
        sweep_headings = {1: "ARVR"}
        project_links = {1: "https://github.com/AdityaHegde712/ARVR"}
        profile = {"section_order": ["projects"], "skills": {}, "experience": []}
        doc = assemble_resume(parsed, profile, sweep_headings, project_links)
        assert "\\resumeLink{https://github.com/AdityaHegde712/ARVR}" in doc

    def test_link_fuzzy_exact_name_fallback(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[],
            projects=[ProjectEntry(index=None, name="Space Debris Research", tech="Python", bullets=["b"])],
        )
        sweep_headings = {13: "Space Debris Research"}
        project_links = {13: "https://github.com/AdityaHegde712/SpaceDebrisResearch"}
        profile = {"section_order": ["projects"], "skills": {}, "experience": []}
        doc = assemble_resume(parsed, profile, sweep_headings, project_links)
        assert "\\resumeLink{https://github.com/AdityaHegde712/SpaceDebrisResearch}" in doc

    def test_link_fuzzy_normalized_punctuation_fallback(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[],
            projects=[ProjectEntry(index=None, name="Course-Visualizer!", tech="React", bullets=["b"])],
        )
        sweep_headings = {10: "Course Visualizer"}
        project_links = {10: "https://github.com/AdityaHegde712/Course-Visualizer"}
        profile = {"section_order": ["projects"], "skills": {}, "experience": []}
        doc = assemble_resume(parsed, profile, sweep_headings, project_links)
        assert "\\resumeLink{https://github.com/AdityaHegde712/Course-Visualizer}" in doc

    def test_link_fuzzy_containment_fallback(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[],
            projects=[ProjectEntry(index=None, name="Visualizer", tech="React", bullets=["b"])],
        )
        sweep_headings = {10: "Course Visualizer"}
        project_links = {10: "https://github.com/AdityaHegde712/Course-Visualizer"}
        profile = {"section_order": ["projects"], "skills": {}, "experience": []}
        doc = assemble_resume(parsed, profile, sweep_headings, project_links)
        assert "\\resumeLink{https://github.com/AdityaHegde712/Course-Visualizer}" in doc

    def test_link_fuzzy_token_overlap_fallback(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[],
            projects=[ProjectEntry(index=None, name="Space Research", tech="Python", bullets=["b"])],
        )
        sweep_headings = {13: "Space Debris Research"}
        project_links = {13: "https://github.com/AdityaHegde712/SpaceDebrisResearch"}
        profile = {"section_order": ["projects"], "skills": {}, "experience": []}
        doc = assemble_resume(parsed, profile, sweep_headings, project_links)
        assert "\\resumeLink{https://github.com/AdityaHegde712/SpaceDebrisResearch}" in doc

    def test_unresolved_link_omits_resume_link_macro(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[],
            projects=[ProjectEntry(index=None, name="Unknown Project XYZ", tech=None, bullets=["bullet text"])],
        )
        profile = {"section_order": ["projects"], "skills": {}, "experience": []}
        doc = assemble_resume(parsed, profile, {}, {})
        assert "\\section{\\textbf{Projects}}" in doc
        assert "\\resumeLink{" not in doc
        assert "{\\textbf{Unknown Project XYZ} $|$ \\emph{}}{}" in doc
        assert "\\resumeItem{bullet text}" in doc

    def test_resolved_link_url_is_escaped(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[],
            projects=[ProjectEntry(index=5, name="Repo", tech="Python", bullets=["b"])],
        )
        project_links = {5: "https://github.com/org/y_z"}
        profile = {"section_order": ["projects"], "skills": {}, "experience": []}
        doc = assemble_resume(parsed, profile, {}, project_links)
        assert "\\resumeLink{https://github.com/org/y\\_z}" in doc

    def test_project_name_tech_and_bullets_are_escaped(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[],
            projects=[ProjectEntry(index=1, name="C# & C++", tech="100% ML", bullets=["50% done & 2# bugs"])],
        )
        project_links = {1: "https://example.com"}
        profile = {"section_order": ["projects"], "skills": {}, "experience": []}
        doc = assemble_resume(parsed, profile, {}, project_links)
        assert "\\section{\\textbf{Projects}}" in doc
        assert "{\\textbf{C\\# \\& C++} $|$ \\emph{100\\% ML}}" in doc
        assert "\\resumeItem{50\\% done \\& 2\\# bugs}" in doc


class TestDocumentAssembly:
    """Section ordering, static sections, omission, and the top/bottom join."""

    def test_sections_follow_section_order(self) -> None:
        parsed = ParsedResume(
            skills=[("Languages", "Python")],
            experience=[ExperienceEntry(label="X", bullets=["b1"])],
            projects=[ProjectEntry(index=1, name="ARVR", tech="React", bullets=["pb"])],
        )
        profile = {
            "section_order": ["skills", "experience", "projects"],
            "skills": {"languages": ["Python"], "frameworks": [], "tools": [], "domains": []},
            "experience": [
                {
                    "role": "Data Scientist Intern",
                    "company": "SUHORA",
                    "location": "India",
                    "start_date": "Mar 2024",
                    "end_date": "Jul 2024",
                    "highlights": ["h"],
                }
            ],
        }
        doc = assemble_resume(parsed, profile, {1: "ARVR"}, {1: "https://x"})
        assert doc.index("\\section{\\textbf{Technical Skills}}") < doc.index("\\section{\\textbf{Experience}}")
        assert doc.index("\\section{\\textbf{Experience}}") < doc.index("{Data Scientist Intern}{Mar 2024 -- Jul 2024}")
        assert doc.index("{Data Scientist Intern}{Mar 2024 -- Jul 2024}") < doc.index("\\section{\\textbf{Projects}}")
        assert doc.index("\\section{\\textbf{Projects}}") < doc.index("ARVR")

    def test_section_not_in_section_order_is_omitted(self) -> None:
        parsed = ParsedResume(
            skills=[],
            experience=[],
            projects=[ProjectEntry(index=1, name="ARVR", tech="React", bullets=["pb"])],
        )
        profile = {
            "section_order": ["skills"],
            "skills": {"languages": ["Python"], "frameworks": [], "tools": [], "domains": []},
            "experience": [],
        }
        doc = assemble_resume(parsed, profile, {1: "ARVR"}, {1: "https://x"})
        assert "Python" in doc
        assert "\n    \\resumeProjectHeading" not in doc

    def test_static_sections_included_verbatim(self) -> None:
        parsed = ParsedResume(skills=[], experience=[], projects=[])
        profile = {
            "section_order": ["education", "publications", "leadership"],
            "skills": {},
            "experience": [],
        }
        doc = assemble_resume(parsed, profile, {}, {})
        assert doc == "\n\n".join([topmatter, education, publications, leadership, bottommatter])

    def test_empty_sections_are_omitted(self) -> None:
        parsed = ParsedResume(skills=[], experience=[], projects=[])
        profile = {
            "section_order": ["skills", "projects", "experience", "certifications"],
            "skills": {},
            "experience": [],
        }
        doc = assemble_resume(parsed, profile, {}, {})
        assert doc == "\n\n".join([topmatter, bottommatter])


class TestGoldenFixtureEndToEnd:
    """Full document built from the frozen fixture plus golden profile data."""

    def test_golden_fixture_document_structure_and_order(self) -> None:
        profile = build_golden_profile()
        doc = assemble_resume(PARSED_GOLDEN, profile, GOLDEN_SWEEP_HEADINGS, GOLDEN_PROJECT_LINKS)
        assert doc.startswith(topmatter)
        assert doc.endswith(bottommatter)
        assert doc.index("\\section{\\textbf{Education}}") < doc.index("\\section{\\textbf{Technical Skills}}")
        assert doc.index("\\section{\\textbf{Technical Skills}}") < doc.index("\\section{\\textbf{Experience}}")
        assert doc.index("\\section{\\textbf{Experience}}") < doc.index("{Data Scientist Intern}{Mar 2024 -- Jul 2024}")
        assert doc.index("{Data Scientist Intern}{Mar 2024 -- Jul 2024}") < doc.index("\\section{\\textbf{Projects}}")
        assert doc.index("\\section{\\textbf{Projects}}") < doc.index("Sentry")
        assert doc.index("Sentry") < doc.index("\\section{Publications and Awards}")
        assert doc.index("\\section{Publications and Awards}") < doc.index("\\section{\\textbf{Campus Involvement and Leadership}}")
        assert "Certifications" not in doc
        assert "\\section{\\textbf{Experience}}" in doc
        assert "\\section{\\textbf{Projects}}" in doc

    def test_golden_experience_uses_llm_bullets_and_ignores_extra_entries(self) -> None:
        profile = build_golden_profile()
        doc = assemble_resume(PARSED_GOLDEN, profile, GOLDEN_SWEEP_HEADINGS, GOLDEN_PROJECT_LINKS)
        assert "\\section{\\textbf{Experience}}" in doc
        assert doc.count("{Data Scientist Intern}{Mar 2024 -- Jul 2024}") == 1
        assert "AI Research Assistant" not in doc
        assert "Graduate Teaching Assistant" not in doc
        assert "C\\# and Python" in doc
        assert "95% evaluation accuracy" not in doc
        assert "95\\% evaluation accuracy" not in doc
        assert "\\textbf{Languages}: Python, TypeScript, JavaScript \\\\" in doc
        assert "TensorFlow" not in doc

    def test_golden_projects_render_in_llm_order_with_exact_links(self) -> None:
        profile = build_golden_profile()
        doc = assemble_resume(PARSED_GOLDEN, profile, GOLDEN_SWEEP_HEADINGS, GOLDEN_PROJECT_LINKS)
        project_names = [
            "Sentry",
            "ARVR",
            "WorkoutApp",
            "Space Debris Research",
            "RecSysProject",
            "Course Visualizer",
        ]
        positions = [doc.index(name) for name in project_names]
        assert positions == sorted(positions)
        assert "\\section{\\textbf{Projects}}" in doc
        assert doc.count("\n\\vspace{-2pt}\n") == 5
        assert "\n    \\resumeProjectHeading" in doc
        assert doc.count("\n    \\resumeProjectHeading") == 6
        assert "\\resumeLink{https://github.com/Aero-inc/sentry}" in doc
        assert "\\resumeLink{https://github.com/AdityaHegde712/ARVR}" in doc
        assert "\\resumeLink{https://github.com/AdityaHegde712/FitnessTracker}" in doc
        assert "\\resumeLink{https://github.com/AdityaHegde712/SpaceDebrisResearch}" in doc
        assert "\\resumeLink{https://github.com/AdityaHegde712/RecSysProject}" in doc
        assert "\\resumeLink{https://github.com/AdityaHegde712/Course-Visualizer}" in doc
