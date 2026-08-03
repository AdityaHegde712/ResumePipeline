"""LaTeX assembler: section_order loop, escaping, project link resolution (PLAN §5)."""

import re

from backend.app.parser import ParsedResume, ProjectEntry
from backend.resume_config import (
    bottommatter,
    education,
    escape_ampersands,
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

# Single-pass LaTeX escaping map; "&" is routed through escape_ampersands.
_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "^": r"\^{}",
    "~": r"\textasciitilde{}",
}
_LATEX_SPECIAL_RE = re.compile(r"[\\{}$%&#_^~]")

# Profile fallback skill groups: (profile key, rendered label).
_SKILL_GROUP_LABELS = [
    ("languages", "Languages"),
    ("frameworks", "Frameworks"),
    ("tools", "Developer Tools"),
    ("domains", "Domains"),
]

_FUZZY_MIN_TOKEN_OVERLAP = 0.5


def escape_latex(text: str) -> str:
    """Escape all LaTeX special characters in ``text`` in a single pass.

    Replaces every occurrence of ``\\ { } $ % & # _ ^ ~`` with its LaTeX
    escape; inserted escapes are never re-scanned. Static resume_config
    templates must not be passed through this function.

    Args:
        text: Raw text (typically LLM- or profile-derived).

    Returns:
        Text safe to embed verbatim in a LaTeX document.
    """
    if not text:
        return ""
    return _LATEX_SPECIAL_RE.sub(_replace_special, text)


def assemble_resume(
    parsed: ParsedResume,
    profile: dict,
    sweep_headings: dict[int, str],
    project_links: dict[int, str],
) -> str:
    """Assemble the full LaTeX document from parsed LLM output and profile.

    Iterates ``profile["section_order"]``, renders each section through its
    builder, omits empty sections, and joins ``topmatter`` + sections +
    ``bottommatter`` with ``"\\n\\n"``.

    Args:
        parsed: Parsed LLM resume (skills, experience, projects).
        profile: Profile dict mirroring ``backend/profile.yaml``.
        sweep_headings: Project sweep index -> heading text.
        project_links: Project sweep index -> URL.

    Returns:
        Complete LaTeX document string.
    """
    sections: list[str] = []
    for key in profile.get("section_order", []):
        section = _build_section(key, parsed, profile, sweep_headings, project_links)
        if section is not None:
            sections.append(section)
    return "\n\n".join([topmatter, *sections, bottommatter])


def _replace_special(match: re.Match[str]) -> str:
    """Return the LaTeX escape for one matched special character."""
    char = match.group(0)
    if char == "&":
        return escape_ampersands(char)
    return _LATEX_ESCAPES[char]


def _build_section(
    key: str,
    parsed: ParsedResume,
    profile: dict,
    sweep_headings: dict[int, str],
    project_links: dict[int, str],
) -> str | None:
    """Render one section by its ``section_order`` key, or None when empty."""
    if key == "education":
        return education
    if key == "publications":
        return publications
    if key == "leadership":
        return leadership
    if key == "certifications":
        return None
    if key == "skills":
        return _build_skills_section(parsed, profile)
    if key == "experience":
        return _build_experience_section(parsed, profile)
    if key == "projects":
        return _build_projects_section(parsed, sweep_headings, project_links)
    return None


def _build_skills_section(parsed: ParsedResume, profile: dict) -> str | None:
    """Render the Technical Skills section from LLM lines or profile groups."""
    groups = parsed.skills or _profile_skill_groups(profile.get("skills", {}))
    if not groups:
        return None
    bullet_lines = [
        skills_bullet.format(type=escape_latex(stype), skills=escape_latex(skills_text))
        for stype, skills_text in groups
    ]
    return skills_top + "\n".join(bullet_lines) + skills_bottom


def _profile_skill_groups(skills: dict) -> list[tuple[str, str]]:
    """Build (label, joined-items) fallback pairs from profile skill groups."""
    groups = []
    for group_key, label in _SKILL_GROUP_LABELS:
        items = [item for item in skills.get(group_key, []) if item]
        if not items:
            continue
        groups.append((label, ", ".join(items)))
    return groups


def _build_experience_section(parsed: ParsedResume, profile: dict) -> str | None:
    """Render one entry-level experience entry per profile entry."""
    profile_entries = profile.get("experience", [])
    if not profile_entries:
        return None
    rendered = [
        _render_experience_entry(parsed, entry, index)
        for index, entry in enumerate(profile_entries)
    ]
    return experience_top + "".join(rendered) + experience_bottom


def _render_experience_entry(parsed: ParsedResume, entry: dict, index: int) -> str:
    """Render one experience entry: profile metadata plus bullets."""
    bullets = _experience_bullets(parsed, entry, index)
    return (
        experience_entry_top.format(
            experience_name=escape_latex(str(entry.get("role", ""))),
            experience_start_end=escape_latex(
                f"{entry.get('start_date', '')} -- {entry.get('end_date', '')}"
            ),
            company_name=escape_latex(str(entry.get("company", ""))),
            location=escape_latex(str(entry.get("location", ""))),
        )
        + "\n"
        + "\n".join(
            experience_entry_bullet.format(bullet=escape_latex(bullet))
            for bullet in bullets
        )
        + experience_entry_bottom
    )


def _experience_bullets(parsed: ParsedResume, entry: dict, index: int) -> list[str]:
    """Return positional LLM bullets, falling back to profile highlights."""
    if index < len(parsed.experience) and parsed.experience[index].bullets:
        return parsed.experience[index].bullets
    return [bullet for bullet in entry.get("highlights", []) if bullet]


def _build_projects_section(
    parsed: ParsedResume,
    sweep_headings: dict[int, str],
    project_links: dict[int, str],
) -> str | None:
    """Render projects in LLM output order with resolved links."""
    if not parsed.projects:
        return None
    rendered = [
        _render_project_entry(project, sweep_headings, project_links)
        for project in parsed.projects
    ]
    return projects_top + ("\n" + project_entry_separator + "\n").join(rendered) + project_bottom


def _render_project_entry(
    project: ProjectEntry,
    sweep_headings: dict[int, str],
    project_links: dict[int, str],
) -> str:
    """Render one project entry; unresolved links omit the resumeLink macro."""
    name = escape_latex(project.name)
    tech = escape_latex(project.tech or "")
    link = _resolve_project_link(project, sweep_headings, project_links)
    if link is None:
        heading = project_entry_top.format(project_name=name, tech_stack=tech, link="")
        heading = heading.replace("{\\resumeLink{}}", "{}")
    else:
        heading = project_entry_top.format(
            project_name=name, tech_stack=tech, link=escape_latex(link)
        )
    bullets = [escape_latex(bullet) for bullet in project.bullets if bullet]
    return (
        heading
        + "\n".join(project_entry_bullet.format(bullet=bullet) for bullet in bullets)
        + project_entry_bottom
    )


def _resolve_project_link(
    project: ProjectEntry,
    sweep_headings: dict[int, str],
    project_links: dict[int, str],
) -> str | None:
    """Resolve a project URL: exact index, then fuzzy name, else None."""
    if project.index is not None and project.index in project_links:
        return project_links[project.index]
    heading_index = _fuzzy_heading_index(project.name, sweep_headings)
    if heading_index is not None and heading_index in project_links:
        return project_links[heading_index]
    return None


def _fuzzy_heading_index(name: str, sweep_headings: dict[int, str]) -> int | None:
    """Return the sweep index whose heading fuzzy-matches ``name``, if any."""
    normalized_name = _normalize_text(name)
    if not normalized_name:
        return None
    for index, heading in sweep_headings.items():
        if not heading:
            continue
        if _fuzzy_matches(normalized_name, _normalize_text(heading)):
            return index
    return None


def _fuzzy_matches(name: str, heading: str) -> bool:
    """Compare two normalized strings: exact, containment, token overlap."""
    if name == heading:
        return True
    if name in heading or heading in name:
        return True
    name_tokens = set(name.split())
    heading_tokens = set(heading.split())
    if not name_tokens or not heading_tokens:
        return False
    overlap = len(name_tokens & heading_tokens)
    return overlap / min(len(name_tokens), len(heading_tokens)) >= _FUZZY_MIN_TOKEN_OVERLAP


def _normalize_text(text: str) -> str:
    """Lowercase and collapse all non-alphanumeric runs to single spaces."""
    lowered = text.lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()
