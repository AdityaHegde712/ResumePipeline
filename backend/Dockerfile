FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install dependencies (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy application code
COPY . .

# Run with hot-reload for development
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
