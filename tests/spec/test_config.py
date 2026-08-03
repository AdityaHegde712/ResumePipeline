"""Frozen spec tests for backend.app.config (T02).

Contract: paths are pathlib.Path, defaults are locked, and PDFLATEX_PATH
resolution follows env override → default MiKTeX path → PATH lookup.
"""

from pathlib import Path

import pytest

from backend.app.config import (
    BACKEND_DIR,
    DEFAULT_PDFLATEX_PATH,
    PROJECT_ROOT,
    Settings,
    resolve_pdf_latex_path,
)

TEST_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestDefaults:
    def test_model_default(self) -> None:
        assert Settings().model == "gemini/gemini-3-flash-preview"

    def test_temperature_default(self) -> None:
        assert Settings().temperature == 0.2

    def test_pdf_compile_timeout_default(self) -> None:
        assert Settings().pdf_compile_timeout_seconds == 60


class TestPaths:
    def test_project_root_is_repo_root(self) -> None:
        settings = Settings()
        assert settings.project_root == TEST_PROJECT_ROOT

    def test_backend_dir_points_to_backend(self) -> None:
        settings = Settings()
        assert settings.backend_dir == TEST_PROJECT_ROOT / "backend"

    def test_all_path_fields_are_pathlib_paths(self) -> None:
        settings = Settings()
        assert isinstance(settings.project_root, Path)
        assert isinstance(settings.backend_dir, Path)
        assert settings.pdf_latex_path is None or isinstance(settings.pdf_latex_path, Path)


class TestPdfLatexResolution:
    def test_env_directory_appends_pdflatex_exe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PDFLATEX_PATH", str(tmp_path))
        assert Settings().pdf_latex_path == tmp_path / "pdflatex.exe"

    def test_env_file_path_used_as_is(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exe_path = tmp_path / "pdflatex.exe"
        monkeypatch.setenv("PDFLATEX_PATH", str(exe_path))
        assert Settings().pdf_latex_path == exe_path

    def test_env_unset_resolves_to_pdflatex_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("PDFLATEX_PATH", raising=False)
        settings = Settings()
        assert settings.pdf_latex_path is not None
        assert settings.pdf_latex_path.name == "pdflatex.exe"

    def test_chain_uses_default_when_env_missing(self) -> None:
        assert resolve_pdf_latex_path(None) == DEFAULT_PDFLATEX_PATH

    def test_settings_env_file_points_to_backend_env(self) -> None:
        settings = Settings()
        assert Path(settings.model_config.get("env_file")) == BACKEND_DIR / ".env"
