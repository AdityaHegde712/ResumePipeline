FROM python:3.12-slim-bookworm

# Install dependencies and setup
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg && \
    # Add MiKTeX repository (official)
    curl -fsSL https://miktex.org/download/key | gpg --dearmor -o /usr/share/keyrings/miktex.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/miktex.gpg] https://miktex.org/download/debian bookworm universe" > /etc/apt/sources.list.d/miktex.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends miktex pandoc && \
    # Finish MiKTeX setup (private installation)
    miktexsetup finish && \
    # Enable auto-install for MiKTeX packages
    initexmf --set-config-value [MPM]AutoInstall=1 && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy backend source and project files
COPY backend/ ./backend/
COPY pyproject.toml ./
COPY uv.lock ./

# Install uv and dependencies (builder stage)
RUN pip install --no-cache-dir uv && \
    uv sync --frozen

# Set HOME for non-root user (after uv sync so uv cache is root-owned)
ENV HOME=/home/appuser

# Clean up any root-owned uv cache leftovers
RUN rm -rf /home/appuser/.cache/uv

# Pre-create MiKTeX cache dir with appuser ownership so the named volume inherits it
RUN mkdir -p /home/appuser/.cache/miktex && chown -R appuser:appuser /home/appuser/.cache

# Fix venv ownership for appuser
RUN chown -R appuser:appuser /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER appuser

# Initialize MiKTeX user config as appuser (auto-install + package DB)
RUN initexmf --set-config-value [MPM]AutoInstall=1 && \
    mpm --update-db

# Expose backend port
EXPOSE 8000

# Health check using curl
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the backend application
CMD ["uv", "run", "--frozen", "uvicorn", "backend.app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]