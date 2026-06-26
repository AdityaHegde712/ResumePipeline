"""
Tests for LaTeXRenderer — rendering, validation, and helper functions.

Tests cover:
- Rendering with various profile configurations (full, empty, partial)
- Section ordering, including publication and leadership sections
- Latex validation (balanced braces, document environment)
- Helper functions: escape_latex, format_dates, format_skills
- Edge cases: None/empty strings, special characters, empty categories
"""

import pytest
from pathlib import Path
from typing import List, Optional

from app.pipeline.latex_renderer import (
    LaTeXRenderer,
    escape_latex,
    format_dates,
    format_skills,
)
from app.models.profile import (
    UserProfile,
    Education,
    Experience,
    PersonalProject,
    SkillSet,
    Publication,
    Leadership,
    Certificate,
    Link,
)
from app.models.application import SectionPoints, BulletPoint

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def renderer() -> LaTeXRenderer:
    """A LaTeXRenderer pointed at the real template file.

    The template lives at ``backend/app/templates/latex/resume_template.tex.j2``
    and tests are run from the ``backend/`` directory.
    """
    template_path = Path("app/templates/latex/resume_template.tex.j2")
    if not template_path.exists():
        pytest.skip(f"Template not found at {template_path.resolve()}")
    return LaTeXRenderer(template_path)


@pytest.fixture
def empty_profile() -> UserProfile:
    """A profile with all fields at their defaults (mostly empty)."""
    return UserProfile(
        name="Test User",
        email="test@example.com",
    )


@pytest.fixture
def full_profile() -> UserProfile:
    """A profile with data in every section."""
    return UserProfile(
        name="Ada Lovelace",
        email="ada@example.com",
        phone="+1-555-1234",
        location="London, UK",
        links=Link(
            linkedin="https://linkedin.com/in/ada",
            github="https://github.com/ada",
        ),
        education=[
            Education(
                school="University of Cambridge",
                degree="BA Mathematics",
                start_date="Jun 1834",
                end_date="Jun 1836",
                location="Cambridge, UK",
                coursework=["Algebra", "Calculus", "Logic"],
            ),
        ],
        skills=SkillSet(
            languages=["Python", "JavaScript"],
            frameworks=["PyTorch", "React"],
            tools=["Git", "Docker"],
            domains=["ML", "Systems"],
        ),
        personal_projects=[
            PersonalProject(
                name="Analytical Engine",
                tech_stack=["Gears", "Punched Cards"],
                description="Designed the first general-purpose computer.",
            ),
        ],
        experience=[
            Experience(
                company="Charles Babbage Lab",
                role="Research Associate",
                start_date="Jun 1834",
                end_date="Present",
                location="London, UK",
                description="Worked on the Analytical Engine.",
                highlights=[
                    "Authored first algorithm intended for machine execution.",
                    "Developed concepts for loops and conditional branching.",
                ],
            ),
        ],
        publications=[
            Publication(
                title="Sketch of the Analytical Engine",
                authors="Ada Lovelace",
                venue="Taylor's Scientific Memoirs",
                year="1843",
                description="Translation and extensive notes on Babbage's machine.",
            ),
        ],
        leadership=[
            Leadership(
                organization="London Mathematical Society",
                role="Founding Member",
                start_date="Jan 1865",
                end_date="Dec 1870",
                description="Helped establish the society's early bylaws.",
            ),
        ],
        certifications=[
            Certificate(
                name="Early Computing Pioneer",
                issuer="Computer History Museum",
                date="2023",
            ),
        ],
        section_order=[
            "education",
            "skills",
            "projects",
            "experience",
            "publications",
            "leadership",
            "certifications",
        ],
    )


@pytest.fixture
def profile_without_optional_sections() -> UserProfile:
    """A profile with only education, skills, and experience — no projects, pubs, etc."""
    return UserProfile(
        name="Engineer Person",
        email="eng@example.com",
        education=[
            Education(
                school="MIT",
                degree="BS Computer Science",
                start_date="Sep 2018",
                end_date="May 2022",
                location="Cambridge, MA",
            ),
        ],
        skills=SkillSet(
            languages=["Java", "Python"],
            frameworks=["Spring"],
            tools=["IntelliJ"],
            domains=["Backend"],
        ),
        experience=[
            Experience(
                company="Tech Corp",
                role="Software Engineer",
                start_date="Jun 2022",
                end_date="Present",
                location="NYC",
                description="Building backend services.",
                highlights=["Designed microservices architecture."],
            ),
        ],
        section_order=["education", "skills", "experience"],
    )


@pytest.fixture
def profile_with_custom_order() -> UserProfile:
    """Profile with non-default section order (skills first)."""
    return UserProfile(
        name="Custom Order",
        email="order@test.com",
        skills=SkillSet(languages=["Go"]),
        education=[
            Education(
                school="State U",
                degree="BS",
                start_date="Sep 2019",
                end_date="May 2023",
                location="St. Paul",
            ),
        ],
        section_order=["skills", "education"],
    )


@pytest.fixture
def sample_sections() -> list[SectionPoints]:
    """Generated bullet points for education and experience sections."""
    return [
        SectionPoints(
            section_key="education",
            section_title="Education",
            bullets=[
                BulletPoint(
                    id="e1",
                    section="education",
                    text="Graduated with honors (GPA 3.9)",
                    order=1,
                    edited=False,
                ),
            ],
        ),
        SectionPoints(
            section_key="experience",
            section_title="Experience",
            bullets=[
                BulletPoint(
                    id="x1",
                    section="experience",
                    text="Led a team of 5 engineers on a high-impact project",
                    order=1,
                    edited=False,
                ),
                BulletPoint(
                    id="x2",
                    section="experience",
                    text="Reduced deployment time by 40% using CI/CD pipelines",
                    order=2,
                    edited=False,
                ),
                BulletPoint(
                    id="x3",
                    section="experience",
                    text="Migrated legacy monolith to microservices",
                    order=3,
                    edited=False,
                ),
            ],
        ),
    ]


# ===================================================================
# Helper: escape_latex
# ===================================================================


class TestEscapeLatex:
    """Tests for the ``escape_latex`` helper function."""

    def test_backslash_first(self):
        """Backslash must be escaped before braces to avoid double-escaping."""
        result = escape_latex("\\{")
        assert "\\textbackslash{}\\{" in result or result == "\\textbackslash{}\\{"

    def test_escapes_all_special_chars(self):
        """Every special LaTeX character is replaced."""
        specials = "# $ % & ~ _ ^ \\ { }"
        result = escape_latex(specials)
        assert "#" not in result or "\\#" in result
        assert "$" not in result or "\\$" in result
        assert "%" not in result or "\\%" in result
        assert "&" not in result or "\\&" in result
        assert "~" not in result or "\\textasciitilde{}" in result
        assert "_" not in result or "\\_" in result
        assert "^" not in result or "\\textasciicircum{}" in result
        assert "\\textbackslash{}" in result
        assert "\\{" in result
        assert "\\}" in result

    def test_ampersand_escaped(self):
        """& becomes \\&."""
        assert escape_latex("A&B") == "A\\&B"

    def test_percent_escaped(self):
        """% becomes \\%."""
        assert escape_latex("100%") == "100\\%"

    def test_dollar_escaped(self):
        """$ becomes \\$."""
        assert escape_latex("$5.00") == "\\$5.00"

    def test_hash_escaped(self):
        """# becomes \\#."""
        assert escape_latex("#1") == "\\#1"

    def test_underscore_escaped(self):
        """_ becomes \\_."""
        assert escape_latex("a_b") == "a\\_b"

    def test_caret_escaped(self):
        """^ becomes \\textasciicircum{}."""
        assert escape_latex("x^2") == "x\\textasciicircum{}2"

    def test_tilde_escaped(self):
        """~ becomes \\textasciitilde{}."""
        assert escape_latex("foo~bar") == "foo\\textasciitilde{}bar"

    def test_no_op_for_clean_text(self):
        """Plain text with no special chars returns unchanged."""
        text = "Hello, World!"
        assert escape_latex(text) == text

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert escape_latex("") == ""

    def test_none_coerced_to_empty_string(self):
        """None input is treated as empty/falsy, returning empty string."""
        assert escape_latex(None) == ""


# ===================================================================
# Helper: format_dates
# ===================================================================


class TestFormatDates:
    """Tests for the ``format_dates`` helper function."""

    def test_standard_dates(self):
        """Both dates provided produces 'start -- end'."""
        assert format_dates("Jun 2020", "May 2023") == "Jun 2020 -- May 2023"

    def test_present_date(self):
        """"Present" is passed through verbatim."""
        assert format_dates("Aug 2025", "Present") == "Aug 2025 -- Present"

    def test_single_month_format(self):
        """Short month format is preserved."""
        assert format_dates("Jan 2020", "Dec 2020") == "Jan 2020 -- Dec 2020"

    def test_whitespace_handling(self):
        """Whitespace around dates is preserved (no stripping)."""
        result = format_dates("  2020 ", " 2023 ")
        assert result == "  2020  --  2023 "


# ===================================================================
# Helper: format_skills
# ===================================================================


class TestFormatSkills:
    """Tests for the ``format_skills`` helper function."""

    def test_all_categories(self):
        """All four categories are rendered with proper LaTeX formatting."""
        skill_set = SkillSet(
            languages=["Python", "TypeScript"],
            frameworks=["React", "Django"],
            tools=["Git", "Docker"],
            domains=["Web", "ML"],
        )
        result = format_skills(skill_set)
        assert "\\textbf{Languages}" in result
        assert "Python, TypeScript" in result
        assert "\\textbf{Frameworks}" in result
        assert "React, Django" in result
        assert "\\textbf{Developer Tools}" in result
        assert "Git, Docker" in result
        assert "\\textbf{Domains}" in result
        assert "Web, ML" in result
        # Domains line should NOT end with \\
        assert result.strip().endswith("Web, ML")

    def test_only_languages(self):
        """Only languages category is present."""
        skill_set = SkillSet(languages=["Python"])
        result = format_skills(skill_set)
        assert "\\textbf{Languages}" in result
        assert "\\textbf{Frameworks}" not in result
        assert "\\textbf{Developer Tools}" not in result
        assert "\\textbf{Domains}" not in result

    def test_only_frameworks(self):
        """Only frameworks category is present."""
        skill_set = SkillSet(frameworks=["PyTorch"])
        result = format_skills(skill_set)
        assert "\\textbf{Frameworks}" in result
        assert "\\textbf{Languages}" not in result

    def test_only_tools(self):
        """Only tools category is present."""
        skill_set = SkillSet(tools=["Docker"])
        result = format_skills(skill_set)
        assert "\\textbf{Developer Tools}" in result
        assert "\\textbf{Languages}" not in result

    def test_only_domains(self):
        """Only domains category is present."""
        skill_set = SkillSet(domains=["ML"])
        result = format_skills(skill_set)
        assert "\\textbf{Domains}" in result
        # Domains should not have trailing \\
        assert "\\\\" not in result

    def test_empty_skill_set(self):
        """An entirely empty SkillSet produces an empty string."""
        skill_set = SkillSet()
        assert format_skills(skill_set) == ""


# ===================================================================
# LaTeXRenderer.validate_latex
# ===================================================================


class TestValidateLatex:
    """Tests for ``LaTeXRenderer.validate_latex()``."""

    def test_clean_document(self, renderer):
        """A well-formed document returns an empty warning list."""
        tex = (
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Hello\n"
            "\\end{document}\n"
        )
        assert renderer.validate_latex(tex) == []

    def test_missing_end_document(self, renderer):
        """Missing \\end{document} is reported."""
        tex = "\\documentclass{article}\n\\begin{document}\nHello\n"
        warnings = renderer.validate_latex(tex)
        assert any("Missing \\end{document}" in w for w in warnings)

    def test_missing_begin_document(self, renderer):
        """Missing \\begin{document} is reported."""
        tex = "\\documentclass{article}\nHello\n\\end{document}\n"
        warnings = renderer.validate_latex(tex)
        assert any("Missing \\begin{document}" in w for w in warnings)

    def test_unbalanced_braces_extra_open(self, renderer):
        """More { than } is flagged."""
        tex = "\\begin{document}{\\textbf{hello}\\end{document}"
        warnings = renderer.validate_latex(tex)
        assert any("Unbalanced braces" in w for w in warnings)

    def test_unbalanced_braces_extra_close(self, renderer):
        """More } than { is flagged."""
        tex = "\\begin{document}\\textbf{hello}}\\end{document}"
        warnings = renderer.validate_latex(tex)
        assert any("Unbalanced braces" in w for w in warnings)

    def test_unbalanced_environments(self, renderer):
        """Mismatched \\begin{...} / \\end{...} counts are flagged."""
        tex = (
            "\\begin{document}\n"
            "\\begin{itemize}\n"
            "\\item A\n"
            "\\end{document}\n"
        )
        warnings = renderer.validate_latex(tex)
        assert any("Unbalanced environments" in w for w in warnings)

    def test_multiple_warnings(self, renderer):
        """Missing \\end{document} and unbalanced braces are both reported."""
        tex = "\\begin{document}\\textbf{hello}"
        warnings = renderer.validate_latex(tex)
        assert len(warnings) >= 2


# ===================================================================
# LaTeXRenderer.render – basic output quality
# ===================================================================


class TestRenderBasic:
    """Core rendering sanity checks."""

    def test_render_returns_string(self, renderer, full_profile):
        """Output is a non-empty string containing LaTeX document markers."""
        tex = renderer.render(full_profile)
        assert isinstance(tex, str)
        assert len(tex) > 0
        assert "\\begin{document}" in tex
        assert "\\end{document}" in tex

    def test_render_produces_valid_latex(self, renderer, full_profile):
        """Rendered output passes validate_latex (no warnings)."""
        tex = renderer.render(full_profile)
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_render_empty_profile(self, renderer, empty_profile):
        """A profile with no sections produces a valid but minimal document."""
        tex = renderer.render(empty_profile)
        assert "\\begin{document}" in tex
        assert "\\end{document}" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_render_profile_name_appears(self, renderer, empty_profile):
        """The profile name appears in the rendered header."""
        tex = renderer.render(empty_profile)
        assert "Test User" in tex

    def test_render_email_appears(self, renderer, empty_profile):
        """The profile email appears in the rendered heading."""
        tex = renderer.render(empty_profile)
        assert "test@example.com" in tex

    def test_render_phone_appears(self, renderer, full_profile):
        """Phone number is included when present."""
        tex = renderer.render(full_profile)
        assert "+1-555-1234" in tex

    def test_render_location_appears(self, renderer, full_profile):
        """Location is included when present."""
        tex = renderer.render(full_profile)
        assert "London, UK" in tex

    def test_render_links_appear(self, renderer, full_profile):
        """LinkedIn and GitHub links appear in the rendered header."""
        tex = renderer.render(full_profile)
        assert "linkedin.com/in/ada" in tex
        assert "github.com/ada" in tex


# ===================================================================
# Render with sections / generated content
# ===================================================================


class TestRenderWithSections:
    """Rendering behavior when ``sections`` kwarg is provided."""

    def test_generated_bullets_appear_in_output(
        self, renderer, full_profile, sample_sections
    ):
        """Generated bullet text appears in the rendered LaTeX."""
        tex = renderer.render(full_profile, sections=sample_sections)
        # From education section
        assert "Graduated with honors (GPA 3.9)" in tex
        # From experience section
        assert "Led a team of 5 engineers" in tex
        assert "Reduced deployment time" in tex
        assert "Migrated legacy monolith" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_sections_empty_list_falls_back_to_highlights(
        self, renderer, full_profile
    ):
        """When ``sections=[]``, profile highlights are used as fallback."""
        tex = renderer.render(full_profile, sections=[])
        # Profile highlights should appear
        assert "Authored first algorithm" in tex
        assert "Developed concepts for loops" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_sections_none_falls_back_to_highlights(
        self, renderer, full_profile
    ):
        """When ``sections=None``, profile highlights are used as fallback."""
        tex = renderer.render(full_profile, sections=None)
        assert "Authored first algorithm" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_generated_bullets_are_escaped(
        self, renderer, full_profile
    ):
        """Special characters in generated bullets are properly escaped."""
        sections = [
            SectionPoints(
                section_key="experience",
                section_title="Experience",
                bullets=[
                    BulletPoint(
                        id="x_esc",
                        section="experience",
                        text="Cost savings > $50K & 100% improvement",
                        order=1,
                        edited=False,
                    ),
                ],
            ),
        ]
        tex = renderer.render(full_profile, sections=sections)
        # Dollar sign should be escaped
        assert "\\$50K" in tex or "\\$50" in tex
        # Ampersand should be escaped
        assert "\\&" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"


# ===================================================================
# Render – empty / edge-case profiles
# ===================================================================


class TestRenderEdgeCases:
    """Edge cases: empty collections, missing fields, etc."""

    def test_all_empty_sections(self, renderer):
        """A profile with all empty collections still produces valid LaTeX."""
        profile = UserProfile(
            name="Empty",
            email="empty@test.com",
        )
        tex = renderer.render(profile)
        assert "\\begin{document}" in tex
        assert "\\end{document}" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_no_skills_education_only(self, renderer):
        """Profile with education but no skills still renders cleanly."""
        profile = UserProfile(
            name="No Skills",
            email="noskills@test.com",
            education=[
                Education(
                    school="Test University",
                    degree="BS Test",
                    start_date="Sep 2020",
                    end_date="May 2024",
                    location="Testville",
                ),
            ],
            section_order=["education"],
        )
        tex = renderer.render(profile)
        assert "Test University" in tex
        assert "\\section{Education}" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_no_experience_skills_only(self, renderer):
        """Profile with skills but no experience renders cleanly."""
        profile = UserProfile(
            name="Skills Only",
            email="skills@test.com",
            skills=SkillSet(languages=["Rust"], tools=["Cargo"]),
            section_order=["skills"],
        )
        tex = renderer.render(profile)
        assert "Technical Skills" in tex or "\\section{Technical Skills}" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_special_characters_in_profile_fields(self, renderer):
        """Special characters in profile fields are escaped in output."""
        profile = UserProfile(
            name="$pecial $Name",
            email="special@test.com",
            location="100% Real City & Co.",
        )
        # Manually set name with special chars since pydantic field is str
        profile.name = "$pecial $Name"
        profile.location = "100% Real City & Co."
        profile.phone = "+$ 50"

        tex = renderer.render(profile)
        # Dollar signs should be escaped in the name
        assert "\\$" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"


# ===================================================================
# Render – section ordering
# ===================================================================


class TestRenderSectionOrder:
    """The ``profile.section_order`` list controls output order."""

    def test_sections_appear_in_section_order(self, renderer, profile_with_custom_order):
        """Sections appear in the exact order specified by section_order."""
        tex = renderer.render(profile_with_custom_order)
        skills_pos = tex.find("Technical Skills")
        education_pos = tex.find("Education")
        assert skills_pos >= 0, "Skills section not found"
        assert education_pos >= 0, "Education section not found"
        assert skills_pos < education_pos, (
            f"Skills (pos {skills_pos}) should appear before Education "
            f"(pos {education_pos})"
        )

    def test_default_section_order(self, renderer, full_profile):
        """Default section order (education first, certifications last)."""
        tex = renderer.render(full_profile)
        edu_pos = tex.find("\\section{Education}")
        cert_pos = tex.find("\\section{Certifications}")
        assert edu_pos >= 0
        assert cert_pos >= 0
        assert edu_pos < cert_pos

    def test_section_order_respected_with_sections_param(
        self, renderer, profile_with_custom_order, sample_sections
    ):
        """Section order is preserved even when generated sections are provided."""
        tex = renderer.render(profile_with_custom_order, sections=sample_sections)
        skills_pos = tex.find("Technical Skills")
        education_pos = tex.find("Education")
        assert skills_pos < education_pos


# ===================================================================
# Render – specific sections
# ===================================================================


class TestRenderPublications:
    """Publications section rendering."""

    def test_publications_rendered(self, renderer, full_profile):
        """Publication title, authors, venue, year appear."""
        tex = renderer.render(full_profile)
        assert "\\section{Publications}" in tex
        assert "Sketch of the Analytical Engine" in tex
        assert "Ada Lovelace" in tex
        assert "Taylor's Scientific Memoirs" in tex
        assert "1843" in tex

    def test_publications_no_description(self, renderer):
        """Publications without description don't produce itemize."""
        profile = UserProfile(
            name="Pub Tester",
            email="pub@test.com",
            publications=[
                Publication(
                    title="Short Paper",
                    authors="A. Author",
                    venue="Journal of X",
                    year="2024",
                    description="",
                ),
            ],
            section_order=["publications"],
        )
        tex = renderer.render(profile)
        assert "\\section{Publications}" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_publications_empty_list_omitted(self, renderer, empty_profile):
        """Profile with empty publications list does not produce the section."""
        tex = renderer.render(empty_profile)
        assert "\\section{Publications}" not in tex


class TestRenderLeadership:
    """Leadership section rendering."""

    def test_leadership_rendered(self, renderer, full_profile):
        """Leadership organization, role, dates appear."""
        tex = renderer.render(full_profile)
        assert "\\section{Leadership / Extracurricular}" in tex
        assert "London Mathematical Society" in tex
        assert "Founding Member" in tex
        assert "Jan 1865" in tex
        assert "Dec 1870" in tex

    def test_leadership_without_description_optional(self, renderer):
        """Leadership entries can omit description and still render."""
        profile = UserProfile(
            name="Leader",
            email="lead@test.com",
            leadership=[
                Leadership(
                    organization="Chess Club",
                    role="President",
                    start_date="Sep 2020",
                    end_date="May 2021",
                    description="",
                ),
            ],
            section_order=["leadership"],
        )
        tex = renderer.render(profile)
        assert "Chess Club" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_leadership_empty_list_omitted(self, renderer, empty_profile):
        """Profile with empty leadership list does not produce the section."""
        tex = renderer.render(empty_profile)
        assert "\\section{Leadership / Extracurricular}" not in tex


class TestRenderCertifications:
    """Certifications section rendering."""

    def test_certifications_rendered(self, renderer, full_profile):
        """Certification name, issuer, date appear."""
        tex = renderer.render(full_profile)
        assert "\\section{Certifications}" in tex
        assert "Early Computing Pioneer" in tex
        assert "Computer History Museum" in tex
        assert "2023" in tex

    def test_certification_without_date(self, renderer):
        """Certification without a date still renders."""
        profile = UserProfile(
            name="Cert Tester",
            email="cert@test.com",
            certifications=[
                Certificate(
                    name="Some Cert",
                    issuer="Some Issuer",
                    date=None,
                ),
            ],
            section_order=["certifications"],
        )
        tex = renderer.render(profile)
        assert "Some Cert" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"


class TestRenderSkills:
    """Technical Skills section specifics."""

    def test_skills_section_rendered(self, renderer, full_profile):
        """Skills section with all categories renders valid LaTeX."""
        tex = renderer.render(full_profile)
        assert "\\section{Technical Skills}" in tex
        assert "Python" in tex or "JavaScript" in tex
        assert "PyTorch" in tex or "React" in tex
        assert "Git" in tex or "Docker" in tex
        assert "ML" in tex or "Systems" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_skills_section_omitted_when_empty(self, renderer, empty_profile):
        """Profile with empty SkillSet does not produce a skills section."""
        tex = renderer.render(empty_profile)
        assert "\\section{Technical Skills}" not in tex


class TestRenderProjects:
    """Projects section specifics."""

    def test_projects_section_rendered(self, renderer, full_profile):
        """Projects section includes project name and tech stack."""
        tex = renderer.render(full_profile)
        assert "\\section{Projects}" in tex
        assert "Analytical Engine" in tex
        assert "Gears" in tex or "Punched Cards" in tex

    def test_projects_fallback_description(self, renderer, full_profile):
        """When no generated sections, project description is used."""
        tex = renderer.render(full_profile)
        assert "Designed the first general-purpose computer." in tex

    def test_projects_empty_list_omitted(self, renderer, empty_profile):
        """Profile with empty projects list does not produce the section."""
        tex = renderer.render(empty_profile)
        assert "\\section{Projects}" not in tex


class TestRenderEducation:
    """Education section specifics."""

    def test_education_coursework_rendered(self, renderer, full_profile):
        """Coursework items within education are rendered."""
        tex = renderer.render(full_profile)
        assert "Algebra" in tex
        assert "Calculus" in tex
        assert "Logic" in tex

    def test_education_without_coursework(self, renderer):
        """Education without coursework still renders cleanly."""
        profile = UserProfile(
            name="No Coursework",
            email="nc@test.com",
            education=[
                Education(
                    school="Simple U",
                    degree="BS Simplicity",
                    start_date="Sep 2020",
                    end_date="May 2024",
                    location="Simpleton",
                ),
            ],
            section_order=["education"],
        )
        tex = renderer.render(profile)
        assert "Simple U" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"


class TestRenderExperience:
    """Experience section specifics."""

    def test_experience_highlights_rendered(self, renderer, full_profile):
        """Profile experience highlights are rendered in fallback mode."""
        tex = renderer.render(full_profile)
        assert "Authored first algorithm" in tex
        assert "Developed concepts for loops" in tex

    def test_experience_without_highlights(self, renderer):
        """Experience with empty highlights still renders."""
        profile = UserProfile(
            name="No Highlights",
            email="nh@test.com",
            experience=[
                Experience(
                    company="Quiet Corp",
                    role="Silent Engineer",
                    start_date="Jan 2020",
                    end_date="Present",
                    location="Remote",
                    description="Keeps things running.",
                ),
            ],
            section_order=["experience"],
        )
        tex = renderer.render(profile)
        assert "Quiet Corp" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"


# ===================================================================
# Render – error handling
# ===================================================================


class TestRenderErrors:
    """Error / edge cases with render()."""

    def test_render_with_duplicate_bullet_ids(
        self, renderer, full_profile
    ):
        """Duplicate bullet IDs should not cause rendering errors."""
        sections = [
            SectionPoints(
                section_key="experience",
                section_title="Experience",
                bullets=[
                    BulletPoint(
                        id="same_id", section="experience",
                        text="Bullet A", order=1, edited=False,
                    ),
                    BulletPoint(
                        id="same_id", section="experience",
                        text="Bullet B", order=2, edited=False,
                    ),
                ],
            ),
        ]
        tex = renderer.render(full_profile, sections=sections)
        assert "Bullet A" in tex
        assert "Bullet B" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"

    def test_render_with_very_long_text(self, renderer, full_profile):
        """Very long bullet text does not break rendering."""
        long_text = "A" * 10_000
        sections = [
            SectionPoints(
                section_key="experience",
                section_title="Experience",
                bullets=[
                    BulletPoint(
                        id="long", section="experience",
                        text=long_text, order=1, edited=False,
                    ),
                ],
            ),
        ]
        tex = renderer.render(full_profile, sections=sections)
        assert long_text in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"


# ===================================================================
# Render – distribution of bullets across entries
# ===================================================================


class TestBulletDistribution:
    """Generated bullets are distributed evenly across experience/project entries."""

    def test_bullets_distributed_across_experiences(self, renderer):
        """3 bullets across 2 experiences: one gets 2, the other gets 1."""
        profile = UserProfile(
            name="Multi Exp",
            email="multi@test.com",
            experience=[
                Experience(
                    company="Co A", role="Eng",
                    start_date="Jan 2020", end_date="Present",
                    location="NYC", description="",
                ),
                Experience(
                    company="Co B", role="Lead",
                    start_date="Jan 2018", end_date="Dec 2019",
                    location="SF", description="",
                ),
            ],
            section_order=["experience"],
        )
        sections = [
            SectionPoints(
                section_key="experience",
                section_title="Experience",
                bullets=[
                    BulletPoint(id="b1", section="experience", text="Bullet 1", order=1),
                    BulletPoint(id="b2", section="experience", text="Bullet 2", order=2),
                    BulletPoint(id="b3", section="experience", text="Bullet 3", order=3),
                ],
            ),
        ]
        tex = renderer.render(profile, sections=sections)
        # Both companies appear
        assert "Co A" in tex
        assert "Co B" in tex
        warnings = renderer.validate_latex(tex)
        assert warnings == [], f"Validation warnings: {warnings}"


# ===================================================================
# Integration: render + validate round-trip
# ===================================================================


class TestRenderValidateRoundTrip:
    """Round-trip checks: rendered output always passes validation."""

    @pytest.mark.parametrize(
        "profile_fixture",
        [
            "full_profile",
            "empty_profile",
            "profile_without_optional_sections",
            "profile_with_custom_order",
        ],
    )
    def test_all_profiles_validate_cleanly(self, renderer, profile_fixture, request):
        """Every profile fixture renders to valid LaTeX with no warnings."""
        profile = request.getfixturevalue(profile_fixture)
        tex = renderer.render(profile)
        warnings = renderer.validate_latex(tex)
        assert warnings == [], (
            f"Validation warnings for {profile_fixture}: {warnings}"
        )
