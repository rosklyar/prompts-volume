# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install uv

# Create non-root user and group (moved up for better layer caching)
# - Create 'appuser' with UID 1000 and GID 1000 (standard non-root IDs)
# - Don't create home directory (-M) to keep image lean
# - Make user system account (-r) for service processes
RUN groupadd -r -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -M -s /sbin/nologin appuser

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Set cache directories for transformers models and uv
# This ensures caches are in known locations within the image where appuser has write access
ENV TRANSFORMERS_CACHE=/app/.cache/transformers \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/transformers \
    UV_CACHE_DIR=/app/.cache/uv

# Pre-download the embedding model (~450MB)
# This layer will be cached and reused unless dependencies change
COPY scripts/download_model.py ./scripts/
RUN uv run python scripts/download_model.py && \
    mkdir -p /app/.cache/uv && \
    chown -R appuser:appuser /app/.cache

# Copy source code (most frequently changed, should be last)
# Use --chown to set ownership during copy for efficiency
COPY --chown=appuser:appuser src/ ./src/

# Switch to non-root user
USER appuser

# Health check (reduced start-period since model is pre-loaded)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD uv run python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Run the application as non-root user
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
