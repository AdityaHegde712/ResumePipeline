"""Security integration tests: path traversal via application_id (RED).

MUTABLE contract — these tests are written RED against the current code to
prove the path-traversal vulnerability in ``backend.app.storage.application_dir``
(``root / application_id`` with no ID-format validation). They must FAIL now
and PASS once ``application_id`` is validated against
``^application-\\d{8}-\\d{6}$``.

The GET endpoints ``/api/applications/{application_id}/llm_response|tex|pdf``
pass the raw ID through to ``application_dir``. A crafted ID such as
``..%2F..%2F<name>`` decodes to ``../../<name>`` and escapes the applications
root, letting an attacker read files outside it.

Fixture conventions mirror ``tests/integration/test_api.py``: the
``APPLICATIONS_ROOT`` env var is redirected to a pytest ``tmp_path`` before
``create_app()`` runs, and the app is exercised through a ``TestClient``.
"""

import os
import re
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app

SENTINEL_CONTENT = "TOP-SECRET-SENTINEL-7f3a9c2b"

APPLICATION_ID_PATTERN = re.compile(r"^application-\d{8}-\d{6}$")


@pytest.fixture
def applications_root(tmp_path: Path) -> Path:
    """The throwaway root where the app must store its applications."""

    return tmp_path / "applications"


@pytest.fixture
def client(
    applications_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """A TestClient whose app stores data under tmp_path only."""

    monkeypatch.setenv("APPLICATIONS_ROOT", str(applications_root))
    monkeypatch.setenv("PDFLATEX_PATH", str(applications_root / "no-pdflatex.exe"))
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sentinel_dir(tmp_path: Path) -> Iterator[Path]:
    """A directory OUTSIDE the applications root holding a secret llm_response.

    Lives one level above ``tmp_path`` (the pytest basetemp) so the traversal
    needs two ``..`` segments, matching the ``..%2F..%2F`` attack shape. The
    directory is removed after the test so no state leaks between runs.
    """

    sentinel = tmp_path.parent / f"secretbox_{uuid4().hex[:8]}"
    sentinel.mkdir()
    (sentinel / "llm_response.md").write_text(SENTINEL_CONTENT, encoding="utf-8")
    yield sentinel
    for child in sentinel.iterdir():
        child.unlink()
    sentinel.rmdir()


class TestPathTraversal:
    """The application_id path-traversal vulnerability (RED until fixed)."""

    @pytest.mark.parametrize(
        "separator",
        [
            pytest.param("%2F", id="forward-slash"),
            pytest.param("%5C", id="backslash"),
        ],
    )
    def test_traversal_does_not_leak_sentinel(
        self,
        client: TestClient,
        applications_root: Path,
        sentinel_dir: Path,
        separator: str,
    ) -> None:
        """A traversal ID must not return 200 or leak the sentinel content."""

        traversal = _encode_traversal(sentinel_dir, applications_root, separator)
        url = f"/api/applications/{traversal}/llm_response"

        response = client.get(url)

        assert response.status_code != 200
        assert SENTINEL_CONTENT not in response.text

    def test_valid_format_missing_id_returns_404(self, client: TestClient) -> None:
        """A well-formed but unknown id is a clean 404, never a crash."""

        missing_id = "application-20260101-000000"

        response = client.get(f"/api/applications/{missing_id}/llm_response")

        assert response.status_code == 404

    @pytest.mark.parametrize(
        "bad_id",
        [
            "not-an-id",
            "application-1234%2F..%2Fx",
            "application-20260101-000000%2F..%2Fx",
            "..%2F..%2Fetc",
            "application-20260101-000000%5C..%5Cx",
        ],
    )
    def test_malformed_id_is_rejected_never_200(
        self,
        client: TestClient,
        bad_id: str,
    ) -> None:
        """Malformed ids are rejected cleanly (404/422), never served."""

        response = client.get(f"/api/applications/{bad_id}/llm_response")

        assert response.status_code in (404, 422)
        assert response.status_code != 200


def _encode_traversal(
    sentinel_dir: Path,
    applications_root: Path,
    separator: str,
) -> str:
    """Encode the traversal path from the app root to the sentinel dir.

    ``os.path.relpath`` yields ``..\\..\\secretbox_xxx`` on Windows; the
    separators are normalized to forward slashes and then URL-encoded with
    the requested separator (``%2F`` for slashes, ``%5C`` for backslashes).
    """

    raw = os.path.relpath(sentinel_dir, applications_root).replace("\\", "/")
    return raw.replace("/", separator)