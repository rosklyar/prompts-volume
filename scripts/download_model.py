#!/usr/bin/env python3
"""
Pre-download the embedding model for Docker image build.

This script downloads the sentence-transformers model (~450MB) during
the Docker build phase, allowing it to be cached in the Docker layer.
"""

import logging

from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def main():
    """Download the embedding model to the cache directory."""
    logger.info(f"Downloading model: {MODEL_NAME}")
    logger.info("This will cache ~450MB to TRANSFORMERS_CACHE location")

    # This downloads the model to the cache directory specified by
    # TRANSFORMERS_CACHE environment variable (or default ~/.cache)
    model = SentenceTransformer(MODEL_NAME)

    logger.info(f"Model downloaded successfully!")
    logger.info(f"Embedding dimension: {model.get_sentence_embedding_dimension()}")


if __name__ == "__main__":
    main()
