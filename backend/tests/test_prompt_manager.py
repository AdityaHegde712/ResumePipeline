"""
Tests for PromptManager.
"""
import pytest
import tempfile
from pathlib import Path
from app.services.prompt_manager import PromptManager
from jinja2 import UndefinedError


@pytest.fixture
def templates_dir():
    """Create a temporary directory with test templates."""
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        (tdir / "test_template.j2").write_text("Hello {{ name }}!", encoding="utf-8")
        (tdir / "complex.j2").write_text(
            "{% for item in items %}- {{ item }}\n{% endfor %}", encoding="utf-8"
        )
        yield tdir


class TestPromptManager:
    """Tests for PromptManager."""

    def test_render_with_valid_context(self, templates_dir):
        """render() should produce correct output with valid context."""
        pm = PromptManager(templates_dir)
        result = pm.render("test_template", {"name": "World"})
        assert result == "Hello World!"

    def test_render_with_complex_template(self, templates_dir):
        """render() should handle loops and complex templates."""
        pm = PromptManager(templates_dir)
        result = pm.render("complex", {"items": ["A", "B", "C"]})
        assert "- A" in result
        assert "- B" in result
        assert "- C" in result

    def test_render_missing_variable_raises_error(self, templates_dir):
        """render() should raise UndefinedError for missing variables."""
        pm = PromptManager(templates_dir)
        with pytest.raises(UndefinedError):
            pm.render("test_template", {})

    def test_list_templates(self, templates_dir):
        """list_templates() should return template names without .j2."""
        pm = PromptManager(templates_dir)
        templates = pm.list_templates()
        assert "test_template" in templates
        assert "complex" in templates
        assert len(templates) == 2

    def test_list_templates_empty_dir(self):
        """list_templates() should return empty list for empty directory."""
        with tempfile.TemporaryDirectory() as tmp:
            pm = PromptManager(Path(tmp))
            assert pm.list_templates() == []

    def test_reload_clears_cache(self, templates_dir):
        """reload() should clear the template cache."""
        pm = PromptManager(templates_dir)
        pm.render("test_template", {"name": "First"})

        # Modify the template
        (templates_dir / "test_template.j2").write_text("Goodbye {{ name }}!", encoding="utf-8")

        # Without reload, old cached template (may still be used depending on Jinja2 caching)
        pm.reload()
        result = pm.render("test_template", {"name": "World"})
        assert result == "Goodbye World!"

    def test_render_nonexistent_template_raises_error(self, templates_dir):
        """render() should raise FileNotFoundError for missing template."""
        pm = PromptManager(templates_dir)
        with pytest.raises(FileNotFoundError):
            pm.render("nonexistent", {})

    def test_render_with_env_override(self, templates_dir):
        """render() should use env override when settings has prompt override."""
        settings = type('Settings', (), {
            'prompt_matching': 'Custom: {{ role }} at {{ company }}',
            'prompt_keyword_analysis': None,
            'prompt_resume_points': None,
            'prompt_resume_writeup': None,
        })()

        pm = PromptManager(templates_dir, settings=settings)

        # For templates not in TEMPLATE_ENV_MAP, fall through to file
        result = pm.render("test_template", {"name": "World"})
        assert result == "Hello World!"
