"""
PromptManager — loads Jinja2 prompt templates with env-var override support.

The manager checks for env var overrides before falling back to .j2 files,
so users can tune prompts in .env without touching code.

Override flow:
  render("resume_points", context)
    -> settings.prompt_resume_points is set?
      -> YES: Use env var value as Jinja2 template string
      -> NO: Load resume_points.j2 from disk, render with Jinja2
"""
import os
import logging
from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader, StrictUndefined, Template

logger = logging.getLogger(__name__)

# Map template names to their settings attributes
TEMPLATE_ENV_MAP = {
    "project_matching": "prompt_matching",
    "keyword_analysis": "prompt_keyword_analysis",
    "resume_points": "prompt_resume_points",
    "resume_writeup": "prompt_resume_writeup",
}


class PromptManager:
    """Manages Jinja2 prompt templates with env-var override capability."""

    def __init__(self, templates_dir: Path, settings=None):
        """Initialize the prompt manager.
        
        Args:
            templates_dir: Path to the directory containing .j2 template files.
            settings: App Settings instance for env-var prompt overrides.
                     If None, no env-var overrides are available.
        """
        self.templates_dir = Path(templates_dir)
        self.settings = settings
        
        # Jinja2 environment with strict undefined checking
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # Cache for loaded templates
        self._template_cache: dict[str, Template] = {}

    def render(self, template_name: str, context: dict) -> str:
        """Render a template with the given context.
        
        1. Check if settings has prompt_{template_name} override
        2. If yes, use that string as the Jinja2 template
        3. Otherwise load the .j2 file from disk
        4. Render with context dict
        5. Return rendered string
        
        Args:
            template_name: Name of template (without .j2 extension).
            context: Dict of variables to pass to the template.
            
        Returns:
            Rendered template string.
            
        Raises:
            jinja2.UndefinedError: If a required variable is missing from context.
            FileNotFoundError: If template file not found and no env override.
        """
        # Step 1: Check for env-var override
        override = self._get_override(template_name)
        
        if override is not None:
            # Use the override value as the template string
            template = self.env.from_string(override)
        else:
            # Load from file (cached)
            template = self._load_template(template_name)
        
        # Render with context
        return template.render(**context)

    def list_templates(self) -> list[str]:
        """Return template names without .j2 extension."""
        templates = []
        if self.templates_dir.exists():
            for f in sorted(self.templates_dir.glob("*.j2")):
                templates.append(f.stem)
        return templates

    def reload(self) -> None:
        """Force reload all templates from disk (re-reads env overrides too)."""
        self._template_cache.clear()
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        logger.info("PromptManager templates reloaded")

    def _get_override(self, template_name: str) -> Optional[str]:
        """Check if there's an env-var override for this template.
        
        Returns the override string, or None if no override is set.
        """
        if template_name not in TEMPLATE_ENV_MAP:
            return None
        
        attr_name = TEMPLATE_ENV_MAP[template_name]
        if self.settings is None:
            return None
        
        return getattr(self.settings, attr_name, None)

    def _load_template(self, template_name: str) -> Template:
        """Load a template file from disk (with caching)."""
        # Check cache first
        if template_name in self._template_cache:
            return self._template_cache[template_name]
        
        # Load from disk
        template_path = self.templates_dir / f"{template_name}.j2"
        if not template_path.exists():
            raise FileNotFoundError(
                f"Template '{template_name}.j2' not found at {template_path}"
            )
        
        template = self.env.get_template(f"{template_name}.j2")
        self._template_cache[template_name] = template
        return template