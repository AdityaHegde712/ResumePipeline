"""
LaTeX Renderer — converts profile + generated content to .tex using Jinja2.
"""
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.models.profile import UserProfile
from app.models.application import SectionPoints, BulletPoint

logger = logging.getLogger(__name__)


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters.

    Single-pass character-by-character replacement prevents re-escaping
    of replacement text (e.g., braces in ``\\textbackslash{}``).
    """
    if not text:
        return ""
    result: list[str] = []
    for ch in text:
        if ch == '\\':
            result.append('\\textbackslash{}')
        elif ch == '{':
            result.append('\\{')
        elif ch == '}':
            result.append('\\}')
        elif ch == '$':
            result.append('\\$')
        elif ch == '%':
            result.append('\\%')
        elif ch == '&':
            result.append('\\&')
        elif ch == '#':
            result.append('\\#')
        elif ch == '_':
            result.append('\\_')
        elif ch == '^':
            result.append('\\textasciicircum{}')
        elif ch == '~':
            result.append('\\textasciitilde{}')
        else:
            result.append(ch)
    return ''.join(result)


def format_dates(start: str, end: str) -> str:
    """Format dates: 'Aug 2025 -- May 2027' or 'Aug 2025 -- Present'."""
    return f"{start} -- {end}"


def format_skills(skill_set) -> str:
    """Format skills as LaTeX: \\textbf{Category}: items \\\\

    Returns a LaTeX string suitable for the Technical Skills section.
    """
    from app.models.profile import SkillSet
    parts = []
    if skill_set.languages:
        parts.append(
            f"\\textbf{{Languages}}: {', '.join(skill_set.languages)} \\\\"
        )
    if skill_set.frameworks:
        parts.append(
            f"\\textbf{{Frameworks}}: {', '.join(skill_set.frameworks)} \\\\"
        )
    if skill_set.tools:
        parts.append(
            f"\\textbf{{Developer Tools}}: {', '.join(skill_set.tools)} \\\\"
        )
    if skill_set.domains:
        parts.append(
            f"\\textbf{{Domains}}: {', '.join(skill_set.domains)}"
        )
    return '\n'.join(parts)


def _distribute_bullets(bullets: List[str], num_groups: int) -> List[List[str]]:
    """Distribute a flat list of bullets across N groups as evenly as possible.

    Args:
        bullets: Flat list of bullet text strings.
        num_groups: Number of groups to distribute into.

    Returns:
        List of num_groups sub-lists, each containing the assigned bullets.
    """
    if not bullets or num_groups == 0:
        return [[] for _ in range(num_groups)] if num_groups > 0 else []

    groups: List[List[str]] = [[] for _ in range(num_groups)]
    for i, bullet in enumerate(bullets):
        groups[i % num_groups].append(bullet)
    return groups


class LaTeXRenderer:
    """Renders profile + generated content into LaTeX .tex string.

    Uses Jinja2 with a pre-built sections approach: each section's LaTeX is
    built in Python (allowing complex logic), and the template simply iterates
    over ``profile.section_order`` to output each pre-rendered block.
    """

    def __init__(self, template_path: Path):
        self.template_dir = template_path.parent
        self.template_name = template_path.name

        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Register custom filters for use in the Jinja2 template
        self.env.filters["escape_latex"] = escape_latex
        self.env.filters["format_dates"] = format_dates

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self,
        profile: UserProfile,
        sections: Optional[List[SectionPoints]] = None,
    ) -> str:
        """Render profile + generated content to LaTeX.

        Args:
            profile: UserProfile with all fields.
            sections: Optional list of SectionPoints with generated bullets.
                      If omitted or empty, profile.highlights are used as fallback.

        Returns:
            Complete .tex document as string.
        """
        section_map = self._build_section_map(sections or [])

        # Pre-build each section's LaTeX string
        sections_tex: Dict[str, str] = {}
        for section_key in profile.section_order:
            tex = self._build_section(section_key, profile, section_map)
            if tex:
                sections_tex[section_key] = tex

        context = {
            "profile": profile,
            "sections_tex": sections_tex,
        }

        template = self.env.get_template(self.template_name)
        tex_content = template.render(**context)

        return tex_content

    def validate_latex(self, tex_content: str) -> List[str]:
        """Validate LaTeX content and return warnings.

        Returns:
            List of warning strings. Empty list = clean document.
        """
        warnings: List[str] = []

        # Check balanced braces
        brace_count = 0
        for char in tex_content:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
        if brace_count != 0:
            warnings.append(
                f"Unbalanced braces: {brace_count} unclosed (negative = extra '}}')"
            )

        # Check document environment
        if "\\begin{document}" not in tex_content:
            warnings.append("Missing \\begin{document}")
        if "\\end{document}" not in tex_content:
            warnings.append("Missing \\end{document}")

        # Check for common issues
        begin_count = tex_content.count("\\begin{")
        end_count = tex_content.count("\\end{")
        if begin_count != end_count:
            warnings.append(
                f"Unbalanced environments: {begin_count} \\begin{{...}} vs "
                f"{end_count} \\end{{...}}"
            )

        return warnings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_section_map(
        sections: List[SectionPoints],
    ) -> Dict[str, SectionPoints]:
        """Build a dict of section_key -> SectionPoints for template access."""
        section_map: Dict[str, SectionPoints] = {}
        for section in sections:
            section_map[section.section_key] = section
        return section_map

    def _build_section(
        self,
        section_key: str,
        profile: UserProfile,
        section_map: Dict[str, SectionPoints],
    ) -> str:
        """Route section_key to the appropriate builder method."""
        builders = {
            "education": self._build_education_section,
            "experience": self._build_experience_section,
            "projects": self._build_projects_section,
            "skills": self._build_skills_section,
            "publications": self._build_publications_section,
            "leadership": self._build_leadership_section,
            "certifications": self._build_certifications_section,
        }
        builder = builders.get(section_key)
        if builder is None:
            logger.debug("No builder registered for section '%s' — skipping", section_key)
            return ""
        return builder(profile, section_map)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_education_section(
        self,
        profile: UserProfile,
        section_map: Dict[str, SectionPoints],
    ) -> str:
        """Render Education section from profile.education."""
        if not profile.education:
            return ""

        lines = [
            "%-----------EDUCATION-----------",
            "\\section{Education}",
            "\\resumeSubHeadingListStart",
        ]
        for edu in profile.education:
            lines.append("\\resumeSubheading")
            lines.append(
                f"  {{{escape_latex(edu.school)}}}"
                f"{{{format_dates(edu.start_date, edu.end_date)}}}"
            )
            lines.append(
                f"  {{{escape_latex(edu.degree)}}}"
                f"{{{escape_latex(edu.location)}}}"
            )
            # Render relevant coursework inline if present
            if edu.coursework:
                lines.append("  \\resumeItemListStart")
                for course in edu.coursework:
                    lines.append(
                        f"    \\resumeItem{{{escape_latex(course)}}}"
                    )
                lines.append("  \\resumeItemListEnd")

            # Include generated bullets from section_map if available
            sp = section_map.get("education")
            if sp and sp.bullets:
                lines.append("  \\resumeItemListStart")
                for bp in sp.bullets:
                    lines.append(
                        f"    \\resumeItem{{{escape_latex(bp.text)}}}"
                    )
                lines.append("  \\resumeItemListEnd")

        lines.append("\\resumeSubHeadingListEnd")
        return "\n".join(lines)

    def _build_experience_section(
        self,
        profile: UserProfile,
        section_map: Dict[str, SectionPoints],
    ) -> str:
        """Render Experience section from profile.experience + generated bullets."""
        if not profile.experience:
            return ""

        # Collect generated bullets for this section
        sp = section_map.get("experience")
        generated_bullets = [bp.text for bp in sp.bullets] if sp and sp.bullets else []

        lines = [
            "%-----------EXPERIENCE-----------",
            "\\section{Experience}",
            "\\resumeSubHeadingListStart",
        ]

        entries = len(profile.experience)

        if generated_bullets and entries > 0:
            # Distribute generated bullets evenly across entries
            dist = _distribute_bullets(generated_bullets, entries)
            for i, exp in enumerate(profile.experience):
                lines.append("\\resumeSubheading")
                lines.append(
                    f"  {{{escape_latex(exp.company)}}}"
                    f"{{{format_dates(exp.start_date, exp.end_date)}}}"
                )
                lines.append(
                    f"  {{{escape_latex(exp.role)}}}"
                    f"{{{escape_latex(exp.location)}}}"
                )
                lines.append("  \\resumeItemListStart")
                for bullet in dist[i]:
                    lines.append(
                        f"    \\resumeItem{{{escape_latex(bullet)}}}"
                    )
                lines.append("  \\resumeItemListEnd")
        else:
            # Fall back to profile highlights
            for exp in profile.experience:
                lines.append("\\resumeSubheading")
                lines.append(
                    f"  {{{escape_latex(exp.company)}}}"
                    f"{{{format_dates(exp.start_date, exp.end_date)}}}"
                )
                lines.append(
                    f"  {{{escape_latex(exp.role)}}}"
                    f"{{{escape_latex(exp.location)}}}"
                )
                lines.append("  \\resumeItemListStart")
                for highlight in exp.highlights:
                    lines.append(
                        f"    \\resumeItem{{{escape_latex(highlight)}}}"
                    )
                lines.append("  \\resumeItemListEnd")

        lines.append("\\resumeSubHeadingListEnd")
        lines.append("\\vspace{-16pt}")
        return "\n".join(lines)

    def _build_projects_section(
        self,
        profile: UserProfile,
        section_map: Dict[str, SectionPoints],
    ) -> str:
        """Render Projects section from profile.personal_projects + generated bullets."""
        if not profile.personal_projects:
            return ""

        # Collect generated bullets for this section
        sp = section_map.get("projects")
        generated_bullets = [bp.text for bp in sp.bullets] if sp and sp.bullets else []

        lines = [
            "%-----------PROJECTS-----------",
            "\\section{Projects}",
            "\\vspace{-5pt}",
            "\\resumeSubHeadingListStart",
        ]

        entries = len(profile.personal_projects)

        if generated_bullets and entries > 0:
            # Distribute generated bullets evenly across projects
            dist = _distribute_bullets(generated_bullets, entries)
            for i, proj in enumerate(profile.personal_projects):
                tech = ", ".join(proj.tech_stack) if proj.tech_stack else ""
                heading = f"\\textbf{{{escape_latex(proj.name)}}}"
                if tech:
                    heading += f" $|$ \\emph{{{escape_latex(tech)}}}"
                lines.append("\\resumeProjectHeading")
                lines.append(f"  {{{heading}}}{{}}")
                lines.append("  \\resumeItemListStart")
                for bullet in dist[i]:
                    lines.append(
                        f"    \\resumeItem{{{escape_latex(bullet)}}}"
                    )
                lines.append("  \\resumeItemListEnd")
                lines.append("  \\vspace{-13pt}")
        else:
            # Fall back to project description as a single bullet
            for proj in profile.personal_projects:
                tech = ", ".join(proj.tech_stack) if proj.tech_stack else ""
                heading = f"\\textbf{{{escape_latex(proj.name)}}}"
                if tech:
                    heading += f" $|$ \\emph{{{escape_latex(tech)}}}"
                lines.append("\\resumeProjectHeading")
                lines.append(f"  {{{heading}}}{{}}")
                if proj.description:
                    lines.append("  \\resumeItemListStart")
                    lines.append(
                        f"    \\resumeItem{{{escape_latex(proj.description)}}}"
                    )
                    lines.append("  \\resumeItemListEnd")
                    lines.append("  \\vspace{-13pt}")

        lines.append("\\resumeSubHeadingListEnd")
        lines.append("\\vspace{-15pt}")
        return "\n".join(lines)

    def _build_skills_section(
        self,
        profile: UserProfile,
        section_map: Dict[str, SectionPoints],
    ) -> str:
        """Render Technical Skills section from profile.skills."""
        skills = profile.skills
        has_any = (
            skills.languages
            or skills.frameworks
            or skills.tools
            or skills.domains
        )
        if not has_any:
            return ""

        skills_latex = format_skills(skills)

        lines = [
            "%-----------PROGRAMMING SKILLS-----------",
            "\\section{Technical Skills}",
            " \\begin{itemize}[leftmargin=0.15in, label={}]",
            "    \\small{\\item{",
            skills_latex,
            "    }}",
            " \\end{itemize}",
            " \\vspace{-16pt}",
        ]
        return "\n".join(lines)

    def _build_publications_section(
        self,
        profile: UserProfile,
        section_map: Dict[str, SectionPoints],
    ) -> str:
        """Render Publications section from profile.publications."""
        if not profile.publications:
            return ""

        lines = [
            "%-----------PUBLICATIONS-----------",
            "\\section{Publications}",
            "\\resumeSubHeadingListStart",
        ]
        for pub in profile.publications:
            # Render as a subheading-style entry
            lines.append("\\resumeSubheading")
            lines.append(
                f"  {{{escape_latex(pub.title)}}}"
                f"{{{escape_latex(pub.year)}}}"
            )
            lines.append(
                f"  {{{escape_latex(pub.authors)}}}"
                f"{{{escape_latex(pub.venue)}}}"
            )
            if pub.description:
                lines.append("  \\resumeItemListStart")
                lines.append(
                    f"    \\resumeItem{{{escape_latex(pub.description)}}}"
                )
                lines.append("  \\resumeItemListEnd")

        lines.append("\\resumeSubHeadingListEnd")
        return "\n".join(lines)

    def _build_leadership_section(
        self,
        profile: UserProfile,
        section_map: Dict[str, SectionPoints],
    ) -> str:
        """Render Leadership / Extracurricular section from profile.leadership."""
        if not profile.leadership:
            return ""

        lines = [
            "%-----------LEADERSHIP-----------",
            "\\section{Leadership / Extracurricular}",
            "\\resumeSubHeadingListStart",
        ]
        for lead in profile.leadership:
            lines.append("\\resumeSubheading")
            lines.append(
                f"  {{{escape_latex(lead.organization)}}}"
                f"{{{format_dates(lead.start_date, lead.end_date)}}}"
            )
            lines.append(
                f"  {{{escape_latex(lead.role)}}}{{}}"
            )
            if lead.description:
                lines.append("  \\resumeItemListStart")
                lines.append(
                    f"    \\resumeItem{{{escape_latex(lead.description)}}}"
                )
                lines.append("  \\resumeItemListEnd")

        lines.append("\\resumeSubHeadingListEnd")
        return "\n".join(lines)

    def _build_certifications_section(
        self,
        profile: UserProfile,
        section_map: Dict[str, SectionPoints],
    ) -> str:
        """Render Certifications section from profile.certifications."""
        if not profile.certifications:
            return ""

        lines = [
            "%-----------CERTIFICATIONS-----------",
            "\\section{Certifications}",
            "\\resumeSubHeadingListStart",
        ]
        for cert in profile.certifications:
            lines.append("\\resumeSubheading")
            lines.append(
                f"  {{{escape_latex(cert.name)}}}"
                f"{{{escape_latex(cert.date or '')}}}"
            )
            lines.append(
                f"  {{{escape_latex(cert.issuer)}}}{{}}"
            )

        lines.append("\\resumeSubHeadingListEnd")
        return "\n".join(lines)
