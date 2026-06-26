from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: configure LiteLLM, warm sweep cache, create services
    settings.configure_litellm()

    from app.services.project_sweep_service import ProjectSweepService
    sweep_service = ProjectSweepService(settings.sweep_file_path)
    projects = sweep_service.get_all()  # warm cache (sync method)
    import logging
    logging.getLogger(__name__).info(f"Loaded {len(projects)} projects from sweep file")
    yield
    # Shutdown: nothing to clean up


def create_app() -> FastAPI:
    app = FastAPI(
        title="Resume Pipeline",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    from app.api.router import api_router
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
