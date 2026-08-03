"""FastAPI application factory for ResumePipeline v2."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and return the configured FastAPI application."""

    app = FastAPI(title="ResumePipeline")

    @app.get("/health")
    def health() -> dict[str, str]:
        """Return service health status."""
        return {"status": "ok"}

    return app


app = create_app()
