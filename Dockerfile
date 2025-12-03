# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Set cache directory for transformers models
# This ensures the model is cached in a known location within the image
ENV TRANSFORMERS_CACHE=/app/.cache/transformers
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/transformers

# Pre-download the embedding model (~450MB)
# This layer will be cached and reused unless dependencies change
COPY scripts/download_model.py ./scripts/
RUN uv run python scripts/download_model.py

# Copy source code (most frequently changed, should be last)
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
