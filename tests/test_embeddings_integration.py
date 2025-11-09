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


#@pytest.mark.skip(
#    reason="Integration test - requires model download (~450MB) and clustering. Run manually to compare algorithms."
#)
def test_clustering_comparison():
    """
    Test: Compare K-Means, HDBSCAN, and Agglomerative clustering on filtered keywords.

    This test:
    - Loads and filters keywords from moyo_ukr_keyword.json (3+ words, no brand)
    - Generates 384-dimensional embeddings
    - Applies all 3 clustering algorithms
    - Compares quality metrics and cluster characteristics
    - Prints detailed comparison report with sample keywords

    To run: Remove @pytest.mark.skip and run:
    uv run pytest tests/test_embeddings_integration.py::test_clustering_comparison -v -s
    """
    from src.embeddings.clustering_service import (
        AgglomerativeClusteringStrategy,
        ClusteringService,
        HDBSCANClusteringStrategy,
        KMeansClusteringStrategy,
    )

    # ========================================================================
    # 1. Load and filter keywords (same as test_embeddings_filtered_keywords)
    # ========================================================================
    sample_file = Path(__file__).parent.parent / "samples" / "moyo_ukr_keyword.json"
    with open(sample_file) as f:
        data = json.load(f)
        all_keywords = data["keywords"]

    print(f"\n📊 Loaded {len(all_keywords)} keywords from sample file")

    filtering_service = KeywordFilteringService(brand_name="moyo")
    filtered_keywords = filtering_service.filter_keywords(all_keywords, min_words=3)

    print(f"🔍 Filtered to {len(filtered_keywords)} keywords (3+ words, no brand)")

    assert len(filtered_keywords) > 0, "Need keywords for clustering"

    # ========================================================================
    # 2. Generate embeddings
    # ========================================================================
    print(f"\n🧬 Generating embeddings for {len(filtered_keywords)} keywords...")

    embeddings_service = get_embeddings_service()
    embeddings = embeddings_service.encode_keywords(
        filtered_keywords, batch_size=64, show_progress=True
    )

    assert embeddings.shape == (len(filtered_keywords), 384)
    print(f"✅ Embeddings generated: {embeddings.shape}")

    # ========================================================================
    # 3. Run clustering algorithms
    # ========================================================================
    print("\n" + "=" * 70)
    print("🎯 RUNNING CLUSTERING ALGORITHMS")
    print("=" * 70)

    clustering_service = ClusteringService()
    results = []

    # Strategy 1: K-Means with auto k-selection
    print("\n[1/3] K-Means Clustering...")
    kmeans_strategy = KMeansClusteringStrategy(min_k=5, max_k=20)
    kmeans_result = kmeans_strategy.cluster(embeddings)
    kmeans_metrics = clustering_service.calculate_metrics(embeddings, kmeans_result.labels)
    kmeans_samples = clustering_service.get_cluster_samples(
        kmeans_result.labels, filtered_keywords, samples_per_cluster=5, max_clusters=5
    )
    results.append((kmeans_result, kmeans_metrics, kmeans_samples))

    # Strategy 2: HDBSCAN density-based
    print("\n[2/3] HDBSCAN Clustering...")
    hdbscan_strategy = HDBSCANClusteringStrategy(
        min_cluster_size=15, min_samples=5
    )
    hdbscan_result = hdbscan_strategy.cluster(embeddings)
    hdbscan_metrics = clustering_service.calculate_metrics(embeddings, hdbscan_result.labels)
    hdbscan_samples = clustering_service.get_cluster_samples(
        hdbscan_result.labels, filtered_keywords, samples_per_cluster=5, max_clusters=5
    )
    results.append((hdbscan_result, hdbscan_metrics, hdbscan_samples))

    # Strategy 3: Agglomerative hierarchical (use same k as KMeans for fair comparison)
    print("\n[3/3] Agglomerative Clustering...")
    agg_strategy = AgglomerativeClusteringStrategy(
        n_clusters=kmeans_result.n_clusters, linkage="ward"
    )
    agg_result = agg_strategy.cluster(embeddings)
    agg_metrics = clustering_service.calculate_metrics(embeddings, agg_result.labels)
    agg_samples = clustering_service.get_cluster_samples(
        agg_result.labels, filtered_keywords, samples_per_cluster=5, max_clusters=5
    )
    results.append((agg_result, agg_metrics, agg_samples))

    # ========================================================================
    # 4. Generate comparison report
    # ========================================================================
    report = clustering_service.format_comparison_report(results, filtered_keywords)
    print(report)

    # ========================================================================
    # 5. Basic assertions
    # ========================================================================
    for result, metrics, _ in results:
        # Each algorithm should find at least 2 clusters
        assert result.n_clusters >= 2, f"{result.algorithm_name} should find at least 2 clusters"

        # Labels should match number of keywords
        assert len(result.labels) == len(filtered_keywords)

        # Metrics should be calculated (unless not enough clusters)
        if result.n_clusters >= 2 and result.noise_count < len(filtered_keywords) - 1:
            assert metrics is not None, f"{result.algorithm_name} should have metrics"

    print("\n✅ All clustering algorithms completed successfully!")
