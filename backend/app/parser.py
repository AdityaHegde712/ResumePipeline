"""Deterministic parser for the LLM response (PLAN §4)."""

from dataclasses import dataclass, field


@dataclass
class ExperienceEntry:
    """One experience block: a header label plus stripped bullet lines."""

    label: str
    bullets: list[str] = field(default_factory=list)


@dataclass
class ProjectEntry:
    """One project block; the link slot is deliberately never stored (D5)."""

    index: int | None = None
    name: str = ""
    tech: str | None = None
    bullets: list[str] = field(default_factory=list)


@dataclass
class ParsedResume:
    """Structured result of parsing a raw LLM response."""

    skills: list[tuple[str, str]] = field(default_factory=list)
    experience: list[ExperienceEntry] = field(default_factory=list)
    projects: list[ProjectEntry] = field(default_factory=list)


class ReconstructionError(Exception):
    """Raised when an LLM block cannot be reconstructed into resume data."""


_BULLET_PREFIXES = ("- ", "• ", "* ")
_SEPARATOR_CHARS = frozenset("-=")
_MIN_SEPARATOR_LENGTH = 3


def parse_llm_response(raw_text: str) -> ParsedResume:
    """Parse a raw LLM response into a ParsedResume (PLAN §4).

    The response uses ``# Skills`` / ``# Experience`` / ``# Projects``
    section headers and ``## `` entry headers for experience and projects.

    Args:
        raw_text: Plaintext response produced by the LLM.

    Returns:
        ParsedResume with ordered skills, experience, and projects.

    Raises:
        ReconstructionError: If a block is malformed (missing skills
            colon, empty project name, or too many project parts).
    """
    lines = _strip_separators(raw_text.splitlines())
    skills_start = _find_header(lines, "# Skills")
    experience_start = _find_header(lines, "# Experience")
    projects_start = _find_header(lines, "# Projects")
    skills = _parse_skills(
        _block_lines(lines, skills_start, _next_header_index(skills_start, [experience_start, projects_start]))
    )
    experience = _parse_experience(
        _block_lines(lines, experience_start, _next_header_index(experience_start, [projects_start]))
    )
    projects = _parse_projects(_block_lines(lines, projects_start, None))
    return ParsedResume(skills=skills, experience=experience, projects=projects)


def _strip_separators(lines: list[str]) -> list[str]:
    """Drop lines made only of 3+ dashes/equals; keep shorter lines."""
    kept = []
    for line in lines:
        stripped = line.strip()
        if len(stripped) >= _MIN_SEPARATOR_LENGTH and all(ch in _SEPARATOR_CHARS for ch in stripped):
            continue
        kept.append(line)
    return kept


def _find_header(lines: list[str], header: str) -> int | None:
    """Return the index of the first exact section header line, if any."""
    for index, line in enumerate(lines):
        if line.strip() == header:
            return index
    return None


def _next_header_index(start: int | None, candidates: list[int | None]) -> int | None:
    """Return the smallest candidate header index after ``start``, if any."""
    if start is None:
        return None
    following = [idx for idx in candidates if idx is not None and idx > start]
    return min(following) if following else None


def _block_lines(lines: list[str], start_idx: int | None, end_idx: int | None) -> list[str]:
    """Return the lines belonging to a section, excluding its header."""
    if start_idx is None:
        return []
    start = start_idx + 1
    end = end_idx if end_idx is not None else len(lines)
    return lines[start:end]


def _is_blank(line: str) -> bool:
    """Return True when a line is empty or whitespace-only."""
    return not line.strip()


def _strip_bullet_prefix(line: str) -> str:
    """Strip at most one bullet marker (``- ``, ``• ``, ``* ``) from a line."""
    for prefix in _BULLET_PREFIXES:
        if line.startswith(prefix):
            return line[len(prefix):]
    return line


def _parse_skills(lines: list[str]) -> list[tuple[str, str]]:
    """Parse ``type: skill, skill`` lines, splitting on the first colon."""
    skills = []
    for line in lines:
        if _is_blank(line):
            continue
        if ":" not in line:
            raise ReconstructionError("reconstruction: skills - line missing ':' separator")
        skill_type, skills_value = line.split(":", 1)
        skills.append((skill_type.strip(), skills_value.strip()))
    return skills


def _parse_experience(lines: list[str]) -> list[ExperienceEntry]:
    """Parse ``## label`` headers and following bullet lines in order."""
    entries = []
    current: ExperienceEntry | None = None
    for line in lines:
        if line.startswith("## "):
            current = ExperienceEntry(label=line[3:].strip())
            entries.append(current)
            continue
        if _is_blank(line) or current is None:
            continue
        current.bullets.append(_strip_bullet_prefix(line).strip())
    return entries


def _parse_projects(lines: list[str]) -> list[ProjectEntry]:
    """Parse ``## N. name | tech | link`` headers and following bullets."""
    projects = []
    current: ProjectEntry | None = None
    for line in lines:
        if line.startswith("## "):
            current = _parse_project_header(line[3:])
            projects.append(current)
            continue
        if _is_blank(line) or current is None:
            continue
        current.bullets.append(_strip_bullet_prefix(line).strip())
    return projects


def _parse_project_header(header_text: str) -> ProjectEntry:
    """Parse a project header into an entry, ignoring the link slot."""
    parts = [part.strip() for part in header_text.split(" | ")]
    if len(parts) > 3:
        raise ReconstructionError("reconstruction: projects - header has more than 3 parts")
    index, name = _split_project_index(parts[0])
    if not name:
        raise ReconstructionError("reconstruction: projects - project name is empty")
    tech = parts[1] if len(parts) > 1 and parts[1] else None
    return ProjectEntry(index=index, name=name, tech=tech)


def _split_project_index(name_part: str) -> tuple[int | None, str]:
    """Split a leading sweep index like ``11.`` from a project name."""
    first = name_part.strip()
    if not first or not first[0].isdigit():
        return None, first
    digit_end = 0
    while digit_end < len(first) and first[digit_end].isdigit():
        digit_end += 1
    index = int(first[:digit_end])
    remainder = first[digit_end:]
    if remainder.startswith("."):
        remainder = remainder[1:].strip()
    return index, remainder
