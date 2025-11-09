"""Integration test for embeddings service with real model."""

import json
from pathlib import Path

import numpy as np
import pytest

from src.embeddings.service import get_embeddings_service


@pytest.mark.skip(reason="Integration test - requires model download (~450MB). Run manually to test embeddings.")
def test_embeddings_last_500_keywords():
    """
    Lucky test: Generate embeddings for last 500 keywords from sample file.

    This test:
    - Loads last 500 keywords from moyo_ukr_keyword.json
    - Generates 384-dimensional embeddings
    - Validates output shape and data types

    To run: Remove @pytest.mark.skip and run:
    uv run pytest tests/test_embeddings_integration.py::test_embeddings_last_500_keywords -v
    """
    # Load sample keywords
    sample_file = Path(__file__).parent.parent / "samples" / "moyo_ukr_keyword.json"
    with open(sample_file) as f:
        data = json.load(f)
        all_keywords = data["keywords"]

    # Take last 500 keywords
    keywords = all_keywords[-500:]
    assert len(keywords) == 500, "Should have 500 keywords"

    # Get embeddings service (loads model)
    service = get_embeddings_service()

    # Generate embeddings
    embeddings = service.encode_keywords(
        keywords,
        batch_size=32,
        show_progress=True  # Show progress during manual test
    )

    # Validate shape
    assert isinstance(embeddings, np.ndarray), "Should return numpy array"
    assert embeddings.shape == (500, 384), f"Expected (500, 384), got {embeddings.shape}"

    # Validate data types
    assert embeddings.dtype == np.float32, f"Expected float32, got {embeddings.dtype}"

    # Validate values are reasonable (not all zeros, not NaN/Inf)
    assert not np.all(embeddings == 0), "Embeddings should not be all zeros"
    assert not np.any(np.isnan(embeddings)), "Should not contain NaN values"
    assert not np.any(np.isinf(embeddings)), "Should not contain Inf values"

    # Check that embeddings are different for different keywords
    assert not np.array_equal(embeddings[0], embeddings[1]), "Different keywords should have different embeddings"
