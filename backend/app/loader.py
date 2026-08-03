"""Startup data loading: profile.yaml, project sweep summaries, LLM prompt."""

from pathlib import Path

import yaml

# Owner-authored input files, resolved against the backend / project roots.
PROFILE_FILENAME = "profile.yaml"
PROMPT_FILENAME = "llm_prompt.md"
PROJECT_LINKS_FILENAME = "project_links.yaml"
SWEEP_FILENAME = "PROJECT_SWEEP_SUMMARIES.md"

# Prompt placeholders filled by build_prompt (must match llm_prompt.md).
_PLACEHOLDER_JOB_POSITION = "{job_position}"
_PLACEHOLDER_COMPANY_NAME = "{company_name}"
_PLACEHOLDER_JOB_DESCRIPTION = "{job_description}"
_PLACEHOLDER_COMPANY_DESC = "{company_desc_string}"
_PLACEHOLDER_SKILLS = "{skills}"
_PLACEHOLDER_EXPERIENCE = "{experience}"
_PLACEHOLDER_SWEEP = "{project_sweep_file_contents}"

# Profile skill groups rendered in this stable order in the prompt.
_SKILL_GROUP_ORDER = ("languages", "frameworks", "tools", "domains")


def load_profile(backend_dir: Path) -> dict:
    """Load ``backend/profile.yaml`` as a plain dict (utf-8)."""
    profile_path = backend_dir / PROFILE_FILENAME
    return yaml.safe_load(profile_path.read_text(encoding="utf-8"))


def load_prompt(backend_dir: Path) -> str:
    """Load the full ``backend/llm_prompt.md`` template text (utf-8)."""
    prompt_path = backend_dir / PROMPT_FILENAME
    return prompt_path.read_text(encoding="utf-8")


def load_project_links(backend_dir: Path) -> dict[int, str]:
    """Load the index-keyed ``backend/project_links.yaml`` URL map.

    Returns:
        Sweep index -> project URL; ``{}`` when the file is missing or
        does not contain a mapping.
    """
    links_path = backend_dir / PROJECT_LINKS_FILENAME
    if not links_path.is_file():
        return {}
    data = yaml.safe_load(links_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {int(key): str(value) for key, value in data.items()}


def load_sweep_summaries(project_root: Path) -> str:
    """Load the full project sweep file ``docs/PROJECT_SWEEP_SUMMARIES.md``."""
    sweep_path = project_root / "docs" / SWEEP_FILENAME
    return sweep_path.read_text(encoding="utf-8")


def parse_sweep_headings(sweep_text: str) -> dict[int, str]:
    """Map ``## N. name`` headings in the sweep file to their names.

    Only headings with a leading integer index and a non-empty name are
    kept; other ``##`` lines (e.g. a table of contents) are ignored.

    Args:
        sweep_text: Full text of the project sweep file.

    Returns:
        Sweep index -> heading name, in file order.
    """
    headings: dict[int, str] = {}
    for line in sweep_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("## "):
            continue
        index, name = _split_index_and_name(stripped[3:].strip())
        if index is not None and name:
            headings[index] = name
    return headings


def build_prompt(
    template: str,
    *,
    job_position: str,
    company_name: str,
    job_description: str,
    company_description: str | None,
    profile: dict,
    sweep_text: str,
) -> str:
    """Fill the llm_prompt.md placeholders with job and profile context.

    ``company_desc_string`` becomes ``- COMPANY DESCRIPTION: {desc}\\n``
    when a company description is supplied, else an empty string.

    Args:
        template: Raw llm_prompt.md text containing the placeholders.
        job_position: Target job title.
        company_name: Target company name.
        job_description: Raw job description text.
        company_description: Optional one-line company description.
        profile: Loaded profile.yaml dict.
        sweep_text: Full project sweep file text.

    Returns:
        The fully-filled prompt, ready for a single LLM call.
    """
    company_desc_string = (
        f"- COMPANY DESCRIPTION: {company_description}\n"
        if company_description
        else ""
    )
    placeholders = {
        _PLACEHOLDER_JOB_POSITION: job_position,
        _PLACEHOLDER_COMPANY_NAME: company_name,
        _PLACEHOLDER_JOB_DESCRIPTION: job_description,
        _PLACEHOLDER_COMPANY_DESC: company_desc_string,
        _PLACEHOLDER_SKILLS: _format_skills(profile),
        _PLACEHOLDER_EXPERIENCE: _format_experience(profile),
        _PLACEHOLDER_SWEEP: sweep_text,
    }
    prompt = template
    for placeholder, value in placeholders.items():
        prompt = prompt.replace(placeholder, value)
    return prompt


def _format_skills(profile: dict) -> str:
    """Join every profile skill item across the standard groups with ', '."""
    skill_groups = profile.get("skills", {})
    items: list[str] = []
    for group in _SKILL_GROUP_ORDER:
        items.extend(item for item in skill_groups.get(group, []) if item)
    return ", ".join(items)


def _format_experience(profile: dict) -> str:
    """Render every experience entry: role/company/dates plus highlights."""
    entries = profile.get("experience", [])
    blocks: list[str] = []
    for entry in entries:
        header = (
            f"- Role: {entry.get('role', '')} | "
            f"Company: {entry.get('company', '')} | "
            f"Dates: {entry.get('start_date', '')} - {entry.get('end_date', '')}"
        )
        if entry.get("location"):
            header += f" | Location: {entry['location']}"
        lines = [header]
        lines.extend(f"  - {highlight}" for highlight in entry.get("highlights", []))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _split_index_and_name(text: str) -> tuple[int | None, str]:
    """Split a leading integer index from a heading like ``1. ARVR``."""
    digits_end = 0
    while digits_end < len(text) and text[digits_end].isdigit():
        digits_end += 1
    if digits_end == 0:
        return None, text
    index = int(text[:digits_end])
    remainder = text[digits_end:].lstrip(". ").strip()
    return index, remainder
