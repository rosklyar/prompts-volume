# Clustering Service Guide

## Overview

The clustering service provides three different algorithms to cluster keyword embeddings, allowing you to compare and choose the best approach for your use case.

## Algorithms Implemented

### 1. **K-Means Clustering**
- **Best for**: Spherical, evenly-sized clusters
- **Auto k-selection**: Tests k from 5 to 20, selects optimal using silhouette score
- **Pros**: Fast, well-understood, consistent results
- **Cons**: Requires specifying k (though we auto-detect), assumes spherical clusters

### 2. **HDBSCAN (Density-Based)**
- **Best for**: Irregularly-shaped clusters, varying densities, automatic cluster discovery
- **Noise detection**: Identifies outliers/noise points (labeled as -1)
- **Pros**: Finds clusters automatically, handles noise well, no need to specify k
- **Cons**: Slower, sensitive to parameters, may mark too many points as noise

### 3. **Agglomerative Clustering (Hierarchical)**
- **Best for**: Hierarchical relationships, understanding cluster structure
- **Linkage**: Uses Ward linkage (minimizes within-cluster variance)
- **Pros**: Creates hierarchy, good interpretability, flexible
- **Cons**: Slower for large datasets, needs to specify k

## Running the Comparison Test

### 1. Install dependencies:
```bash
uv sync
```

### 2. Remove the `@pytest.mark.skip` decorator from the test or run:
```bash
uv run pytest tests/test_embeddings_integration.py::test_clustering_comparison -v -s
```

The test will:
1. Load keywords from `samples/moyo_ukr_keyword.json`
2. Filter to 3+ word keywords without brand mentions
3. Generate 384-dimensional embeddings
4. Run all 3 clustering algorithms
5. Print detailed comparison report

## Example Output

```
======================================================================
🎯 CLUSTERING COMPARISON REPORT
======================================================================

Dataset: 450 keywords, 384-dimensional embeddings

──────────────────────────────────────────────────────────────────────
Algorithm: K-Means
──────────────────────────────────────────────────────────────────────

📋 Configuration:
   optimal_k: 8
   tested_range: 5-20
   best_silhouette: 0.3421
   random_state: 42

📊 Clusters Found: 8

📈 Quality Metrics:
   Silhouette Score: 0.3421 ⭐
   Davies-Bouldin Index: 1.234 (lower is better)
   Calinski-Harabasz Score: 456.78 ⭐

🔍 Top Clusters (by size):
   Cluster 0 (67 keywords):
      • телевізор samsung smart tv
      • смарт тв lg 43
      • телевізор 55 дюймів
      ...

──────────────────────────────────────────────────────────────────────
Algorithm: HDBSCAN
──────────────────────────────────────────────────────────────────────

📋 Configuration:
   min_cluster_size: 15
   min_samples: 5
   cluster_selection_epsilon: 0.0
   noise_percentage: 12.4

📊 Clusters Found: 12
   Noise points: 56 (12.4%)

📈 Quality Metrics:
   Silhouette Score: 0.4123 ⭐
   Davies-Bouldin Index: 0.987 (lower is better)
   Calinski-Harabasz Score: 523.45 ⭐
...
```

## Interpreting Metrics

### Silhouette Score (-1 to 1)
- **> 0.5**: Strong clustering
- **0.3-0.5**: Reasonable clustering ⭐
- **< 0.3**: Weak clustering
- Higher is better

### Davies-Bouldin Index (0+)
- **< 1.0**: Good separation
- **1.0-2.0**: Moderate separation
- **> 2.0**: Poor separation
- Lower is better

### Calinski-Harabasz Score (0+)
- **> 100**: Generally good ⭐
- Higher indicates better-defined clusters
- Higher is better

## Using in Code

```python
from src.embeddings.clustering_service import (
    KMeansClusteringStrategy,
    HDBSCANClusteringStrategy,
    AgglomerativeClusteringStrategy,
    ClusteringService
)

# Generate embeddings first
embeddings = embeddings_service.encode_keywords(keywords)

# Try K-Means
kmeans = KMeansClusteringStrategy(min_k=5, max_k=20)
result = kmeans.cluster(embeddings)

# Calculate metrics
service = ClusteringService()
metrics = service.calculate_metrics(embeddings, result.labels)

# Get sample keywords from clusters
samples = service.get_cluster_samples(
    result.labels,
    keywords,
    samples_per_cluster=5
)
```

## Tuning Parameters

### K-Means
- `min_k`: Minimum clusters to test (default: 5)
- `max_k`: Maximum clusters to test (default: 20)
- `random_state`: Random seed for reproducibility (default: 42)

### HDBSCAN
- `min_cluster_size`: Smaller = more granular clusters (default: 15)
- `min_samples`: Higher = more conservative clustering (default: 5)
- `cluster_selection_epsilon`: Distance threshold for merging (default: 0.0)

### Agglomerative
- `n_clusters`: Number of clusters (default: auto-calculated)
- `linkage`: 'ward', 'complete', 'average', or 'single' (default: 'ward')

## Recommendations

1. **Start with K-Means**: Good baseline, fast, interpretable
2. **Try HDBSCAN**: If you see irregular cluster sizes or want automatic discovery
3. **Use Agglomerative**: If you need hierarchical structure or K-Means doesn't work well
4. **Compare all three**: Use the test to see which works best for your data
5. **Adjust parameters**: Based on cluster sizes and quality metrics

## Next Steps

After identifying the best algorithm:
1. Integrate into your API endpoint for topic clustering
2. Use cluster labels to group keywords by theme
3. Return top keywords from each cluster as topic suggestions
4. Consider caching cluster results for performance
