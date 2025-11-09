"""Service for clustering keyword embeddings using multiple algorithms."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Protocol

import hdbscan
import numpy as np
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)

logger = logging.getLogger(__name__)


@dataclass
class ClusteringResult:
    """Result from a clustering algorithm."""

    algorithm_name: str
    labels: np.ndarray  # Cluster assignment for each keyword (-1 for noise in HDBSCAN)
    n_clusters: int  # Number of clusters found (excluding noise)
    noise_count: int  # Number of points classified as noise (0 for non-density-based)
    config: dict  # Configuration used for this run


@dataclass
class ClusterMetrics:
    """Quality metrics for clustering results."""

    silhouette: float  # -1 to 1, higher is better (measures separation)
    davies_bouldin: float  # 0+, lower is better (measures cluster similarity)
    calinski_harabasz: float  # 0+, higher is better (variance ratio)


class ClusteringStrategy(Protocol):
    """Protocol for clustering strategies."""

    @abstractmethod
    def cluster(self, embeddings: np.ndarray) -> ClusteringResult:
        """Apply clustering algorithm to embeddings."""
        ...


class KMeansClusteringStrategy:
    """
    K-Means clustering with automatic k selection.

    Tests k from min_k to max_k and selects optimal using silhouette score.
    Good for spherical, evenly-sized clusters.
    """

    def __init__(
        self,
        min_k: int = 5,
        max_k: int = 20,
        random_state: int = 42,
    ):
        """
        Initialize K-Means strategy.

        Args:
            min_k: Minimum number of clusters to test
            max_k: Maximum number of clusters to test
            random_state: Random seed for reproducibility
        """
        self.min_k = min_k
        self.max_k = max_k
        self.random_state = random_state

    def cluster(self, embeddings: np.ndarray) -> ClusteringResult:
        """
        Cluster embeddings using K-Means with optimal k selection.

        Args:
            embeddings: Array of shape (n_samples, n_features)

        Returns:
            ClusteringResult with optimal k selection
        """
        n_samples = embeddings.shape[0]
        actual_max_k = min(self.max_k, n_samples - 1)

        logger.info(f"Testing K-Means with k={self.min_k} to k={actual_max_k}")

        best_k = self.min_k
        best_score = -1
        best_labels = None

        for k in range(self.min_k, actual_max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
            labels = kmeans.fit_predict(embeddings)

            # Calculate silhouette score for this k
            score = silhouette_score(embeddings, labels)

            logger.debug(f"  k={k}: silhouette={score:.4f}")

            if score > best_score:
                best_score = score
                best_k = k
                best_labels = labels

        logger.info(f"Selected optimal k={best_k} (silhouette={best_score:.4f})")

        return ClusteringResult(
            algorithm_name="K-Means",
            labels=best_labels,
            n_clusters=best_k,
            noise_count=0,
            config={
                "optimal_k": best_k,
                "tested_range": f"{self.min_k}-{actual_max_k}",
                "best_silhouette": round(best_score, 4),
                "random_state": self.random_state,
            },
        )


class HDBSCANClusteringStrategy:
    """
    HDBSCAN density-based clustering.

    Automatically discovers number of clusters and handles noise/outliers.
    Good for irregularly-shaped clusters and varying densities.
    """

    def __init__(
        self,
        min_cluster_size: int = 15,
        min_samples: int = 5,
        cluster_selection_epsilon: float = 0.0,
    ):
        """
        Initialize HDBSCAN strategy.

        Args:
            min_cluster_size: Minimum size of a cluster (smaller = more granular)
            min_samples: Minimum samples in neighborhood (higher = more conservative)
            cluster_selection_epsilon: Distance threshold for cluster merging
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.cluster_selection_epsilon = cluster_selection_epsilon

    def cluster(self, embeddings: np.ndarray) -> ClusteringResult:
        """
        Cluster embeddings using HDBSCAN.

        Args:
            embeddings: Array of shape (n_samples, n_features)

        Returns:
            ClusteringResult with noise detection
        """
        logger.info(
            f"Running HDBSCAN with min_cluster_size={self.min_cluster_size}, "
            f"min_samples={self.min_samples}"
        )

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
            metric="euclidean",
        )

        labels = clusterer.fit_predict(embeddings)

        # Count clusters (excluding noise label -1)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        noise_count = np.sum(labels == -1)

        logger.info(
            f"Found {n_clusters} clusters with {noise_count} noise points "
            f"({noise_count / len(labels) * 100:.1f}%)"
        )

        return ClusteringResult(
            algorithm_name="HDBSCAN",
            labels=labels,
            n_clusters=n_clusters,
            noise_count=noise_count,
            config={
                "min_cluster_size": self.min_cluster_size,
                "min_samples": self.min_samples,
                "cluster_selection_epsilon": self.cluster_selection_epsilon,
                "noise_percentage": round(noise_count / len(labels) * 100, 2),
            },
        )


class AgglomerativeClusteringStrategy:
    """
    Agglomerative (hierarchical) clustering.

    Builds hierarchy bottom-up, can specify number of clusters.
    Good for hierarchical relationships and dendrograms.
    """

    def __init__(
        self,
        n_clusters: int | None = None,
        linkage: str = "ward",
    ):
        """
        Initialize Agglomerative strategy.

        Args:
            n_clusters: Number of clusters (if None, will be set to optimal k from dataset)
            linkage: Linkage criterion ('ward', 'complete', 'average', 'single')
        """
        self.n_clusters = n_clusters
        self.linkage = linkage

    def cluster(self, embeddings: np.ndarray) -> ClusteringResult:
        """
        Cluster embeddings using Agglomerative Clustering.

        Args:
            embeddings: Array of shape (n_samples, n_features)

        Returns:
            ClusteringResult
        """
        # If n_clusters not specified, use heuristic (sqrt of samples)
        if self.n_clusters is None:
            n_clusters = max(5, int(np.sqrt(embeddings.shape[0] / 2)))
        else:
            n_clusters = self.n_clusters

        logger.info(
            f"Running Agglomerative Clustering with "
            f"n_clusters={n_clusters}, linkage={self.linkage}"
        )

        clusterer = AgglomerativeClustering(n_clusters=n_clusters, linkage=self.linkage)
        labels = clusterer.fit_predict(embeddings)

        logger.info(f"Created {n_clusters} clusters")

        return ClusteringResult(
            algorithm_name="Agglomerative",
            labels=labels,
            n_clusters=n_clusters,
            noise_count=0,
            config={
                "n_clusters": n_clusters,
                "linkage": self.linkage,
            },
        )


class ClusteringService:
    """
    Service for clustering keyword embeddings and comparing algorithms.
    """

    @staticmethod
    def calculate_metrics(
        embeddings: np.ndarray, labels: np.ndarray
    ) -> ClusterMetrics | None:
        """
        Calculate quality metrics for clustering results.

        Args:
            embeddings: Array of shape (n_samples, n_features)
            labels: Cluster labels for each sample

        Returns:
            ClusterMetrics or None if metrics cannot be calculated
        """
        # Filter out noise points (label -1) for metrics calculation
        valid_mask = labels != -1
        valid_embeddings = embeddings[valid_mask]
        valid_labels = labels[valid_mask]

        # Need at least 2 clusters for meaningful metrics
        n_clusters = len(set(valid_labels))
        if n_clusters < 2 or len(valid_embeddings) < 2:
            logger.warning("Cannot calculate metrics: need at least 2 clusters")
            return None

        try:
            silhouette = silhouette_score(valid_embeddings, valid_labels)
            davies_bouldin = davies_bouldin_score(valid_embeddings, valid_labels)
            calinski_harabasz = calinski_harabasz_score(valid_embeddings, valid_labels)

            return ClusterMetrics(
                silhouette=silhouette,
                davies_bouldin=davies_bouldin,
                calinski_harabasz=calinski_harabasz,
            )
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return None

    @staticmethod
    def get_cluster_samples(
        labels: np.ndarray,
        keywords: List[str],
        samples_per_cluster: int = 5,
        max_clusters: int = 5,
    ) -> dict:
        """
        Get sample keywords from each cluster.

        Args:
            labels: Cluster labels
            keywords: Original keywords
            samples_per_cluster: Number of sample keywords per cluster
            max_clusters: Maximum number of clusters to include

        Returns:
            Dictionary mapping cluster_id -> list of sample keywords
        """
        cluster_samples = {}

        # Get unique clusters (excluding noise -1)
        unique_clusters = [c for c in set(labels) if c != -1]

        # Sort by cluster size (largest first)
        cluster_sizes = [(c, np.sum(labels == c)) for c in unique_clusters]
        cluster_sizes.sort(key=lambda x: x[1], reverse=True)

        # Get samples from top clusters
        for cluster_id, size in cluster_sizes[:max_clusters]:
            # Get indices of keywords in this cluster
            cluster_indices = np.where(labels == cluster_id)[0]

            # Sample keywords (take first N, could randomize if needed)
            sample_indices = cluster_indices[:samples_per_cluster]
            sample_keywords = [keywords[i] for i in sample_indices]

            cluster_samples[cluster_id] = {
                "size": size,
                "samples": sample_keywords,
            }

        return cluster_samples

    @staticmethod
    def format_comparison_report(
        results: List[tuple[ClusteringResult, ClusterMetrics | None, dict]],
        keywords: List[str],
    ) -> str:
        """
        Format clustering comparison results as a readable report.

        Args:
            results: List of (ClusteringResult, ClusterMetrics, cluster_samples) tuples
            keywords: Original keywords

        Returns:
            Formatted string report
        """
        lines = [
            "\n" + "=" * 70,
            "🎯 CLUSTERING COMPARISON REPORT",
            "=" * 70,
            f"\nDataset: {len(keywords)} keywords, 384-dimensional embeddings\n",
        ]

        for result, metrics, cluster_samples in results:
            lines.append(f"\n{'─' * 70}")
            lines.append(f"Algorithm: {result.algorithm_name}")
            lines.append(f"{'─' * 70}")

            # Configuration
            lines.append("\n📋 Configuration:")
            for key, value in result.config.items():
                lines.append(f"   {key}: {value}")

            # Cluster summary
            lines.append(f"\n📊 Clusters Found: {result.n_clusters}")
            if result.noise_count > 0:
                noise_pct = result.noise_count / len(result.labels) * 100
                lines.append(f"   Noise points: {result.noise_count} ({noise_pct:.1f}%)")

            # Quality metrics
            if metrics:
                lines.append("\n📈 Quality Metrics:")
                lines.append(f"   Silhouette Score: {metrics.silhouette:.4f} {'⭐' if metrics.silhouette > 0.3 else ''}")
                lines.append(f"   Davies-Bouldin Index: {metrics.davies_bouldin:.4f} (lower is better)")
                lines.append(f"   Calinski-Harabasz Score: {metrics.calinski_harabasz:.2f} {'⭐' if metrics.calinski_harabasz > 100 else ''}")
            else:
                lines.append("\n📈 Quality Metrics: Unable to calculate")

            # Sample clusters
            if cluster_samples:
                lines.append("\n🔍 Top Clusters (by size):")
                for cluster_id, data in cluster_samples.items():
                    lines.append(f"\n   Cluster {cluster_id} ({data['size']} keywords):")
                    for kw in data["samples"]:
                        lines.append(f"      • {kw}")

        lines.append("\n" + "=" * 70 + "\n")

        return "\n".join(lines)
