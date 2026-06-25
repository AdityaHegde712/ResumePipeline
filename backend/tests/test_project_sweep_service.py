"""
Tests for ProjectSweepService.
"""
import pytest
from app.services.project_sweep_service import ProjectSweepService


def test_parse_with_sample_file(tmp_data_dir, sample_sweep_file):
    """Parse should return 3 projects from sample file."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    projects = svc.parse()
    assert len(projects) == 3


def test_parse_projects_have_required_fields(tmp_data_dir, sample_sweep_file):
    """All parsed projects should have name, type, summary."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    projects = svc.parse()
    for p in projects:
        assert p.name, f"Project missing name: {p.id}"
        assert p.type, f"Project missing type: {p.id}"
        assert p.summary, f"Project missing summary: {p.id}"


def test_parse_correct_ids(tmp_data_dir, sample_sweep_file):
    """Projects should have correct slug IDs."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    projects = svc.parse()
    ids = [p.id for p in projects]
    assert "arvr" in ids
    assert "sentry" in ids
    assert "dailybrief" in ids


def test_parse_correct_tech_stack(tmp_data_dir, sample_sweep_file):
    """Tech stack should be correctly parsed as list."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    projects = svc.parse()
    for p in projects:
        assert isinstance(p.tech_stack, list)
        assert len(p.tech_stack) > 0, f"{p.id} has no tech stack"


def test_empty_file_returns_empty(tmp_data_dir):
    """Parse should return [] when file is missing."""
    svc = ProjectSweepService(sweep_file_path=tmp_data_dir / "nonexistent.md")
    projects = svc.parse()
    assert projects == []


def test_get_all_returns_cached(tmp_data_dir, sample_sweep_file):
    """get_all() should return cached results after initial parse."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    first = svc.get_all()
    second = svc.get_all()
    assert len(first) == 3
    assert len(second) == 3


def test_refresh_reparses(tmp_data_dir, sample_sweep_file):
    """refresh() should force re-parse."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    svc.get_all()
    assert len(svc._projects) == 3

    with open(sample_sweep_file, "a") as f:
        f.write("\n---\n\n## 4. NewProject — Test\n**Type:** Test\n\n### Overview\nTest\n")

    refreshed = svc.refresh()
    assert len(refreshed) >= 4


def test_stale_detection(tmp_data_dir, sample_sweep_file):
    """is_stale() should detect file modifications."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    svc.parse()
    assert not svc.is_stale()

    sample_sweep_file.touch()
    assert svc.is_stale()


def test_get_by_id(tmp_data_dir, sample_sweep_file):
    """get_by_id should return correct project."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    svc.parse()
    p = svc.get_by_id("sentry")
    assert p is not None
    assert p.name == "Sentry"


def test_get_by_id_nonexistent(tmp_data_dir, sample_sweep_file):
    """get_by_id should return None for missing ID."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    svc.parse()
    assert svc.get_by_id("nonexistent") is None


def test_search_by_keyword(tmp_data_dir, sample_sweep_file):
    """search() should find projects by keyword."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    svc.parse()
    results = svc.search("computer vision")
    assert len(results) >= 1
    assert any("Sentry" in r.name for r in results)


def test_get_by_domain(tmp_data_dir, sample_sweep_file):
    """get_by_domain() should filter by domain."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    svc.parse()
    ml_projects = svc.get_by_domain("Machine Learning")
    assert len(ml_projects) >= 1


def test_get_by_tech(tmp_data_dir, sample_sweep_file):
    """get_by_tech() should filter by technology."""
    svc = ProjectSweepService(sweep_file_path=sample_sweep_file)
    svc.parse()
    docker_projects = svc.get_by_tech("docker")
    assert len(docker_projects) >= 1
