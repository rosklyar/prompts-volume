# Keyword Clustering Implementation

## What's New

This implementation adds keyword clustering capabilities to help group semantically similar keywords into topics.

## Files Added/Modified

### New Files
1. **[src/embeddings/clustering_service.py](src/embeddings/clustering_service.py)** - Main clustering service with 3 algorithms
2. **[docs/clustering_guide.md](docs/clustering_guide.md)** - Comprehensive guide for using clustering

### Modified Files
1. **[pyproject.toml](pyproject.toml)** - Added `scikit-learn` and `hdbscan` dependencies
2. **[tests/test_embeddings_integration.py](tests/test_embeddings_integration.py)** - Added `test_clustering_comparison()` test

## Quick Start

### 1. Install Dependencies
```bash
uv sync
```

### 2. Run the Comparison Test
```bash
# Remove @pytest.mark.skip from test_clustering_comparison first, then:
uv run pytest tests/test_embeddings_integration.py::test_clustering_comparison -v -s
```

This will:
- Load and filter keywords from your sample data
- Generate embeddings using the multilingual model
- Run all 3 clustering algorithms (K-Means, HDBSCAN, Agglomerative)
- Print a detailed comparison report with metrics and sample keywords

## Clustering Algorithms Included

| Algorithm | Best For | Pros | Cons |
|-----------|----------|------|------|
| **K-Means** | Spherical, balanced clusters | Fast, consistent, auto-detects k | Assumes spherical shape |
| **HDBSCAN** | Irregular shapes, auto-discovery | No k needed, handles noise | Slower, parameter-sensitive |
| **Agglomerative** | Hierarchical relationships | Flexible, interpretable | Slower, needs k specified |

## Quality Metrics Explained

- **Silhouette Score** (0.3-0.5 = good ⭐): How well-separated clusters are
- **Davies-Bouldin Index** (<1.0 = good): How distinct clusters are (lower is better)
- **Calinski-Harabasz Score** (>100 = good ⭐): Variance ratio (higher is better)

## Example Usage in Code

```python
from src.embeddings.clustering_service import (
    KMeansClusteringStrategy,
    ClusteringService
)
from src.embeddings.service import get_embeddings_service

# 1. Generate embeddings
embeddings_service = get_embeddings_service()
embeddings = embeddings_service.encode_keywords(keywords)

# 2. Cluster using K-Means
kmeans = KMeansClusteringStrategy(min_k=5, max_k=20)
result = kmeans.cluster(embeddings)

# 3. Calculate metrics
service = ClusteringService()
metrics = service.calculate_metrics(embeddings, result.labels)

# 4. Get sample keywords from each cluster
samples = service.get_cluster_samples(
    result.labels,
    keywords,
    samples_per_cluster=5
)

print(f"Found {result.n_clusters} clusters")
print(f"Silhouette score: {metrics.silhouette:.4f}")
```

## Next Steps

1. **Run the test** to see which algorithm works best for your keyword data
2. **Choose an algorithm** based on the metrics and cluster quality
3. **Integrate into API** to provide topic-based keyword grouping
4. **Tune parameters** if needed (see [docs/clustering_guide.md](docs/clustering_guide.md))

## Architecture

The implementation follows the **Strategy Pattern**:

```
ClusteringStrategy (Protocol)
    ├── KMeansClusteringStrategy
    ├── HDBSCANClusteringStrategy
    └── AgglomerativeClusteringStrategy

ClusteringService
    ├── calculate_metrics()
    ├── get_cluster_samples()
    └── format_comparison_report()
```

This makes it easy to:
- Add new clustering algorithms
- Switch between algorithms
- Compare results side-by-side
- Test different configurations

## Dependencies Added

- `scikit-learn>=1.3.0` - For K-Means, Agglomerative, and metrics
- `hdbscan>=0.8.33` - For density-based clustering

Both are widely-used, well-maintained libraries in the Python data science ecosystem.
