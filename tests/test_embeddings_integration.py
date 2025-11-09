"""Integration test for embeddings service with real model."""

import json
from pathlib import Path

import numpy as np
import pytest

from src.embeddings.filtering_service import KeywordFilteringService
from src.embeddings.service import get_embeddings_service


@pytest.mark.skip(
    reason="Integration test - requires model download (~450MB). Run manually to test embeddings."
)
def test_embeddings_filtered_keywords():
    """
    Test: Generate embeddings for filtered keywords from sample file.

    This test:
    - Loads ALL keywords from moyo_ukr_keyword.json
    - Filters to keywords with 3+ words and no brand mentions
    - Generates 384-dimensional embeddings for filtered keywords
    - Validates output shape and data types

    To run: Remove @pytest.mark.skip and run:
    uv run pytest tests/test_embeddings_integration.py::test_embeddings_filtered_keywords -v
    """
    # Load sample keywords
    sample_file = Path(__file__).parent.parent / "samples" / "moyo_ukr_keyword.json"
    with open(sample_file) as f:
        data = json.load(f)
        all_keywords = data["keywords"]

    print(f"\n📊 Loaded {len(all_keywords)} keywords from sample file")

    # Filter keywords (3+ words, no brand mentions)
    filtering_service = KeywordFilteringService(brand_name="moyo")

    # Get filtering statistics
    stats = filtering_service.get_filter_stats(all_keywords, min_words=3)
    print(f"\n🔍 Filtering Statistics:")
    print(f"   Total keywords: {stats['total']}")
    print(f"   Removed (short): {stats['removed_short']}")
    print(f"   Removed (brand): {stats['removed_brand']}")
    print(f"   Removed (both): {stats['removed_both']}")
    print(f"   ✅ Kept: {stats['filtered']}")

    # Apply filter
    filtered_keywords = filtering_service.filter_keywords(all_keywords, min_words=3)

    assert len(filtered_keywords) > 0, "Should have some keywords after filtering"
    assert len(filtered_keywords) < len(all_keywords), "Should filter out some keywords"

    # Verify no brand mentions in filtered keywords
    for kw in filtered_keywords:
        assert "moyo" not in kw.lower(), f"Keyword '{kw}' should not contain 'moyo'"
        assert len(kw.split()) >= 3, f"Keyword '{kw}' should have 3+ words"

    print(f"\n🧬 Generating embeddings for {len(filtered_keywords)} filtered keywords...")

    # Get embeddings service (loads model)
    embeddings_service = get_embeddings_service()

    # Generate embeddings
    embeddings = embeddings_service.encode_keywords(
        filtered_keywords,
        batch_size=64,  # Larger batch for efficiency
        show_progress=True
    )

    # Validate shape
    expected_shape = (len(filtered_keywords), 384)
    assert isinstance(embeddings, np.ndarray), "Should return numpy array"
    assert embeddings.shape == expected_shape, f"Expected {expected_shape}, got {embeddings.shape}"

    # Validate data types
    assert embeddings.dtype == np.float32, f"Expected float32, got {embeddings.dtype}"

    # Validate values are reasonable
    assert not np.all(embeddings == 0), "Embeddings should not be all zeros"
    assert not np.any(np.isnan(embeddings)), "Should not contain NaN values"
    assert not np.any(np.isinf(embeddings)), "Should not contain Inf values"

    # Check that embeddings are different for different keywords
    if len(filtered_keywords) > 1:
        assert not np.array_equal(
            embeddings[0], embeddings[1]
        ), "Different keywords should have different embeddings"

    print(f"\n✅ Successfully generated embeddings!")
    print(f"   Shape: {embeddings.shape}")
    print(f"   Dtype: {embeddings.dtype}")
    print(f"   Min value: {embeddings.min():.4f}")
    print(f"   Max value: {embeddings.max():.4f}")
    print(f"   Mean value: {embeddings.mean():.4f}")
    print(f"\n   Sample keyword: '{filtered_keywords[0]}'")
    print(f"   First 5 embedding values: {embeddings[0][:5]}")
