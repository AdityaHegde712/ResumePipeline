"""FastAPI application factory for ResumePipeline v2."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app import loader
from backend.app.api import router
from backend.app.config import Settings

# Dev-only CORS: Vite's default dev server origins (PLAN §7).
_DEV_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app() -> FastAPI:
    """Create and return the configured FastAPI application.

    Reads environment variables (APPLICATIONS_ROOT, PDFLATEX_PATH, ...) at
    call time so tests can redirect storage roots before construction.
    """
    settings = Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Load Owner input files once at startup into ``app.state``."""
        app.state.settings = settings
        app.state.profile = loader.load_profile(settings.backend_dir)
        app.state.sweep_text = loader.load_sweep_summaries(settings.project_root)
        app.state.sweep_headings = loader.parse_sweep_headings(app.state.sweep_text)
        app.state.prompt_template = loader.load_prompt(settings.backend_dir)
        app.state.project_links = loader.load_project_links(settings.backend_dir)
        yield

    app = FastAPI(title="ResumePipeline", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_DEV_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
