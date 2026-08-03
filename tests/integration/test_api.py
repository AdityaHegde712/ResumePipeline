"""Integration tests for the /api application endpoints (T11, Phase 7).

MUTABLE contract — ``backend/app/api.py`` and ``backend/app/main.py`` must
satisfy this file. The implementation phase may adjust this file only on
proven necessity, never by weakening the phase-failure matrix.

Locked API contract (PLAN D9, D10, D13 and §3):

    create_app() -> FastAPI
        App factory in ``backend.app.main``. Must mount the /api router
        and read the ``APPLICATIONS_ROOT`` environment variable when
        constructing runtime Settings.

    POST /api/applications
        Request body: {job_position, job_description, company_name,
        company_description?} (all strings; company_description optional).
        Response 200 JSON (snake_case):
            {status: 200, llm_generation: "OK", reconstruction: "OK",
             saved: "OK", pdf_error: str | None, application_id: str}
        ``application_id`` matches application-YYYYMMDD-HHMMSS and the app
        dir (root / application_id) contains resume.tex, llm_response.md
        and request.json; resume.pdf is present when the PDF phase
        succeeds. Fatal failures return 500 with JSON {phase, error} where
        phase is "llm_generation" (LLM call) or "reconstruction"
        (parse/assembly). PDF compile failure is non-fatal: the response
        stays 200, ``pdf_error`` is a non-empty string, and resume.tex +
        llm_response.md + request.json are still saved.

    GET /api/applications
        Response 200: bare JSON list of request.json metadata dicts,
        newest first (descending application_id).

    GET /api/applications/{application_id}/llm_response
        Response 200: the raw llm_response.md text verbatim.

    GET /api/applications/{application_id}/tex
        Response 200: resume.tex as an attachment download with
        Content-Disposition filename ``resume-{application_id}.tex``.

    GET /api/applications/{application_id}/pdf
        Response 200: resume.pdf as an attachment download with
        Content-Disposition filename ``resume-{application_id}.pdf``;
        404 when the PDF phase failed and resume.pdf is absent.

    Any GET for an unknown application_id returns 404.

App-dir isolation (locked mechanism):

    The storage root is taken from the ``APPLICATIONS_ROOT`` environment
    variable (default ``<project_root>/data/applications``). Every test
    sets ``APPLICATIONS_ROOT`` to a pytest ``tmp_path`` so no real
    application data is ever touched. ``create_app()`` reads the
    environment at startup; tests never write outside tmp_path.

LLM isolation:

    ``backend.app.llm_client.generate_resume_text`` is monkeypatched (and
    the copy bound in ``backend.app.api`` when the API imports the name
    directly) so no network is touched. The golden fixture
    ``tests/fixtures/llm_response_sample.txt`` stands in for the raw LLM
    response. The PDF compiler is monkeypatched the same way; no real
    MiKTeX run happens in this file.
"""

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from backend.app.config import Settings
from backend.app.llm_client import LLMError
from backend.app.main import create_app
from backend.app.pdf import PDFCompileError
from backend.app.storage import create_application_dir, save_request_json

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
GOLDEN_LLM_TEXT = (FIXTURES_DIR / "llm_response_sample.txt").read_text(encoding="utf-8")

MALFORMED_LLM_TEXT = "# Skills\nmalformed line without colon\n# Experience\n# Projects\n"

APPLICATION_ID_PATTERN = re.compile(r"^application-\d{8}-\d{6}$")

REQUEST_PAYLOAD = {
    "job_position": "Data Scientist Intern",
    "job_description": "Build and ship ML features end to end.",
    "company_name": "SUHORA Technologies Pvt. Ltd.",
    "company_description": "Maritime surveillance and geospatial analytics.",
}


async def fake_generate_resume_text(prompt: str, settings: Settings) -> str:
    """Return the golden fixture instead of calling an LLM (no network)."""

    return GOLDEN_LLM_TEXT


async def fake_generate_resume_text_malformed(prompt: str, settings: Settings) -> str:
    """Return text the deterministic parser must reject."""

    return MALFORMED_LLM_TEXT


async def fake_generate_resume_text_failure(prompt: str, settings: Settings) -> str:
    """Raise the typed LLM error the API must map to llm_generation."""

    raise LLMError(
        "Resume generation failed: injected test failure",
        category="unknown",
    )


async def fake_pdf_success(settings: Settings, app_dir: Path) -> Path:
    """Write a fake resume.pdf and return its path (compile success)."""

    pdf_path = app_dir / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.7 test fixture")
    return pdf_path


async def fake_pdf_failure(settings: Settings, app_dir: Path) -> Path:
    """Raise the typed pdf error the API must treat as non-fatal."""

    raise PDFCompileError("pdflatex compile failed (test fixture)")


def raise_assembler_error(*args: Any, **kwargs: Any) -> str:
    """Raise an assembly-time error the API must map to reconstruction."""

    raise RuntimeError("assembler failure injected by test fixture")


def patch_module_call(
    monkeypatch: pytest.MonkeyPatch,
    dotted_target: str,
    replacement: Any,
) -> None:
    """Patch a callable at its home module and the binding in backend.app.api.

    Covers both call styles the API layer may use: module-attribute access
    (``pdf.compile_resume(...)``) and direct name import
    (``from backend.app.pdf import compile_resume``). Patching
    ``backend.app.api`` with ``raising=False`` is harmless when the API
    does not bind the name.
    """

    monkeypatch.setattr(dotted_target, replacement)
    api_binding = "backend.app.api." + dotted_target.rsplit(".", 1)[-1]
    monkeypatch.setattr(api_binding, replacement, raising=False)


def patch_llm(monkeypatch: pytest.MonkeyPatch, fake: Any) -> None:
    """Point the API's LLM call at a deterministic fake."""

    patch_module_call(monkeypatch, "backend.app.llm_client.generate_resume_text", fake)


def patch_pdf_compile(monkeypatch: pytest.MonkeyPatch, fake: Any) -> None:
    """Point the API's PDF phase at a deterministic fake."""

    patch_module_call(monkeypatch, "backend.app.pdf.compile_resume", fake)


def patch_assembler(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the API's assembly phase raise a test error."""

    patch_module_call(monkeypatch, "backend.app.assembler.assemble_resume", raise_assembler_error)


def make_metadata(application_id: str, timestamp: str) -> dict:
    """Build D9 request.json metadata for a seeded application."""

    return {
        "application_id": application_id,
        "job_position": "Data Scientist Intern",
        "company_name": "SUHORA Technologies Pvt. Ltd.",
        "company_description": None,
        "job_description": "Build and ship ML features.",
        "timestamp": timestamp,
        "status": "completed",
        "llm_generation": "OK",
        "reconstruction": "OK",
        "saved": "OK",
        "pdf_error": None,
    }


def post_application(client: TestClient) -> Response:
    """POST the standard request payload to the generate endpoint."""

    return client.post("/api/applications", json=REQUEST_PAYLOAD)


@pytest.fixture
def applications_root(tmp_path: Path) -> Path:
    """The throwaway root where the app must store its applications."""

    return tmp_path / "applications"


@pytest.fixture
def client(
    applications_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """A TestClient whose app stores data under tmp_path only.

    ``APPLICATIONS_ROOT`` redirects the storage root; ``PDFLATEX_PATH``
    points at a nonexistent executable as a second line of defense so no
    real MiKTeX run can ever happen from an unpatched API test.
    """

    monkeypatch.setenv("APPLICATIONS_ROOT", str(applications_root))
    monkeypatch.setenv("PDFLATEX_PATH", str(applications_root / "no-pdflatex.exe"))
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestCreateApplication:
    """The POST /api/applications phase matrix (D9, D10)."""

    def test_post_happy_path_returns_ok_flags_and_saves_files(
        self,
        client: TestClient,
        applications_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """All flags OK and the app dir holds the four generated files."""

        patch_llm(monkeypatch, fake_generate_resume_text)
        patch_pdf_compile(monkeypatch, fake_pdf_success)

        response = post_application(client)

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {
            "status",
            "llm_generation",
            "reconstruction",
            "saved",
            "pdf_error",
            "application_id",
        }
        assert body["status"] == 200
        assert body["llm_generation"] == "OK"
        assert body["reconstruction"] == "OK"
        assert body["saved"] == "OK"
        assert body["pdf_error"] is None
        application_id = body["application_id"]
        assert APPLICATION_ID_PATTERN.fullmatch(application_id) is not None

        app_dir = applications_root / application_id
        assert (app_dir / "resume.tex").is_file()
        assert (app_dir / "resume.pdf").is_file()
        assert (app_dir / "llm_response.md").read_text(encoding="utf-8") == GOLDEN_LLM_TEXT
        saved_metadata = json.loads((app_dir / "request.json").read_text(encoding="utf-8"))
        assert saved_metadata["application_id"] == application_id

    def test_post_llm_failure_returns_500_llm_generation_phase(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An LLM error is fatal and names the llm_generation phase."""

        patch_llm(monkeypatch, fake_generate_resume_text_failure)

        response = post_application(client)

        assert response.status_code == 500
        body = response.json()
        assert body["phase"] == "llm_generation"
        assert isinstance(body["error"], str)
        assert body["error"]

    def test_post_parse_failure_returns_500_reconstruction_phase(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Malformed LLM output is fatal and names the reconstruction phase."""

        patch_llm(monkeypatch, fake_generate_resume_text_malformed)

        response = post_application(client)

        assert response.status_code == 500
        body = response.json()
        assert body["phase"] == "reconstruction"
        assert isinstance(body["error"], str)

    def test_post_assembler_failure_returns_500_reconstruction_phase(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An assembly error is fatal and names the reconstruction phase."""

        patch_llm(monkeypatch, fake_generate_resume_text)
        patch_assembler(monkeypatch)

        response = post_application(client)

        assert response.status_code == 500
        assert response.json()["phase"] == "reconstruction"

    def test_post_pdf_failure_is_non_fatal_and_keeps_tex(
        self,
        client: TestClient,
        applications_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A PDF failure sets pdf_error but still saves tex and metadata."""

        patch_llm(monkeypatch, fake_generate_resume_text)
        patch_pdf_compile(monkeypatch, fake_pdf_failure)

        response = post_application(client)

        assert response.status_code == 200
        body = response.json()
        assert body["llm_generation"] == "OK"
        assert body["reconstruction"] == "OK"
        assert body["saved"] == "OK"
        assert isinstance(body["pdf_error"], str)
        assert body["pdf_error"]

        app_dir = applications_root / body["application_id"]
        assert (app_dir / "resume.tex").is_file()
        assert (app_dir / "request.json").is_file()
        assert not (app_dir / "resume.pdf").exists()


class TestListApplications:
    """The GET /api/applications history contract (D9)."""

    def test_list_applications_returns_metadata_newest_first(
        self,
        client: TestClient,
        applications_root: Path,
    ) -> None:
        """Seeded applications are listed newest first with full metadata."""

        older_id = "application-20260802-143045"
        newer_id = "application-20260802-153000"
        older_dir = create_application_dir(applications_root, older_id)
        newer_dir = create_application_dir(applications_root, newer_id)
        older_metadata = make_metadata(older_id, "2026-08-02T14:30:45Z")
        newer_metadata = make_metadata(newer_id, "2026-08-02T15:30:00Z")
        save_request_json(older_dir, older_metadata)
        save_request_json(newer_dir, newer_metadata)

        response = client.get("/api/applications")

        assert response.status_code == 200
        assert response.json() == [newer_metadata, older_metadata]


class TestGetEndpoints:
    """Download and raw-text endpoints for one generated application."""

    def _create_application(
        self,
        client: TestClient,
        applications_root: Path,
        monkeypatch: pytest.MonkeyPatch,
        with_pdf: bool,
    ) -> str:
        """POST a generated application with a mocked PDF outcome."""

        patch_llm(monkeypatch, fake_generate_resume_text)
        pdf_fake = fake_pdf_success if with_pdf else fake_pdf_failure
        patch_pdf_compile(monkeypatch, pdf_fake)
        response = post_application(client)
        assert response.status_code == 200
        assert (applications_root / response.json()["application_id"]).is_dir()
        return response.json()["application_id"]

    def test_get_llm_response_returns_raw_text(
        self,
        client: TestClient,
        applications_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The saved llm_response.md is served verbatim."""

        application_id = self._create_application(client, applications_root, monkeypatch, True)

        response = client.get(f"/api/applications/{application_id}/llm_response")

        assert response.status_code == 200
        assert response.text == GOLDEN_LLM_TEXT

    def test_get_tex_returns_attachment_download(
        self,
        client: TestClient,
        applications_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """resume.tex downloads as an attachment named by application id."""

        application_id = self._create_application(client, applications_root, monkeypatch, True)

        response = client.get(f"/api/applications/{application_id}/tex")

        assert response.status_code == 200
        content_disposition = response.headers["content-disposition"]
        assert content_disposition.lower().startswith("attachment")
        assert f"resume-{application_id}.tex" in content_disposition
        expected_tex = (applications_root / application_id / "resume.tex").read_text(
            encoding="utf-8"
        )
        assert response.text == expected_tex

    def test_get_pdf_returns_attachment_when_compiled(
        self,
        client: TestClient,
        applications_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """resume.pdf downloads as an attachment when the compile succeeded."""

        application_id = self._create_application(client, applications_root, monkeypatch, True)

        response = client.get(f"/api/applications/{application_id}/pdf")

        assert response.status_code == 200
        content_disposition = response.headers["content-disposition"]
        assert content_disposition.lower().startswith("attachment")
        assert f"resume-{application_id}.pdf" in content_disposition
        expected_pdf = (applications_root / application_id / "resume.pdf").read_bytes()
        assert response.content == expected_pdf

    def test_get_pdf_returns_404_when_compile_failed(
        self,
        client: TestClient,
        applications_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A missing resume.pdf is a 404, not a broken download."""

        application_id = self._create_application(client, applications_root, monkeypatch, False)

        response = client.get(f"/api/applications/{application_id}/pdf")

        assert response.status_code == 404

    @pytest.mark.parametrize("path_suffix", ["/llm_response", "/tex", "/pdf"])
    def test_get_missing_application_returns_404(
        self,
        client: TestClient,
        path_suffix: str,
    ) -> None:
        """Every per-application endpoint 404s for an unknown id."""

        missing_id = "application-20260802-000000"

        response = client.get(f"/api/applications/{missing_id}{path_suffix}")

        assert response.status_code == 404
