"""Service for clustering keyword embeddings using HDBSCAN algorithm."""

import logging
from dataclasses import dataclass
from typing import Dict, List

import hdbscan
import numpy as np
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)

logger = logging.getLogger(__name__)


@dataclass
class ClusteringResult:
    """Result from HDBSCAN clustering."""

    labels: np.ndarray  # Cluster assignment for each keyword (-1 for noise)
    n_clusters: int  # Number of clusters found (excluding noise)
    clusters: Dict[int, List[str]]  # cluster_id -> list of keywords
    noise: List[str]  # Keywords marked as noise
    keyword_embeddings: Dict[str, np.ndarray]  # keyword -> embedding vector


@dataclass
class ClusterMetrics:
    """Quality metrics for clustering results."""

    silhouette: float  # -1 to 1, higher is better (measures separation)
    davies_bouldin: float  # 0+, lower is better (measures cluster similarity)
    calinski_harabasz: float  # 0+, higher is better (variance ratio)


class ClusteringService:
    """
    Service for clustering keyword embeddings using HDBSCAN.
    """

    def _subcluster_large_clusters(
        self,
        clusters: Dict[int, List[str]],
        keyword_embeddings: Dict[str, np.ndarray],
        min_cluster_size: int,
        min_samples: int,
        cluster_selection_epsilon: float,
    ) -> Dict[int, List[str]]:
        """
        Split large clusters into subclusters using recursive HDBSCAN.

        Args:
            clusters: Initial cluster assignments
            keyword_embeddings: Mapping of keyword to embedding vector
            min_cluster_size: Original min_cluster_size parameter
            min_samples: Original min_samples parameter
            cluster_selection_epsilon: Original cluster_selection_epsilon parameter

        Returns:
            Flattened dictionary with renumbered clusters
        """
        threshold = 5 * min_cluster_size
        new_clusters: Dict[int, List[str]] = {}
        next_cluster_id = 0

        for cluster_id, keywords_in_cluster in clusters.items():
            cluster_size = len(keywords_in_cluster)

            # Keep small clusters as-is
            if cluster_size < threshold:
                new_clusters[next_cluster_id] = keywords_in_cluster
                next_cluster_id += 1
                continue

            # Try to split large clusters
            logger.info(
                f"Attempting to split large cluster {cluster_id} "
                f"with {cluster_size} keywords (threshold={threshold})"
            )

            # Extract embeddings for this cluster
            cluster_keywords = keywords_in_cluster
            cluster_embeddings = np.array(
                [keyword_embeddings[kw] for kw in cluster_keywords]
            )

            # Run HDBSCAN with reduced parameters for finer granularity
            sub_min_cluster_size = max(2, min_cluster_size // 2)
            sub_min_samples = max(1, min_samples // 2)

            sub_clusterer = hdbscan.HDBSCAN(
                min_cluster_size=sub_min_cluster_size,
                min_samples=sub_min_samples,
                cluster_selection_epsilon=cluster_selection_epsilon,
                metric="euclidean",
            )

            sub_labels = sub_clusterer.fit_predict(cluster_embeddings)
            sub_n_clusters = len(set(sub_labels)) - (1 if -1 in sub_labels else 0)

            # If we found meaningful subclusters, use them
            if sub_n_clusters > 1:
                logger.info(
                    f"Split cluster {cluster_id} into {sub_n_clusters} subclusters"
                )

                # Organize subclusters
                for keyword, sub_label in zip(cluster_keywords, sub_labels):
                    # Treat noise as a separate subcluster (keep original cluster)
                    if sub_label == -1:
                        # Add to a "remaining" cluster
                        if next_cluster_id not in new_clusters:
                            new_clusters[next_cluster_id] = []
                        new_clusters[next_cluster_id].append(keyword)
                    else:
                        # Map sub_label to global cluster ID
                        global_cluster_id = next_cluster_id + sub_label + 1
                        if global_cluster_id not in new_clusters:
                            new_clusters[global_cluster_id] = []
                        new_clusters[global_cluster_id].append(keyword)

                # Update next_cluster_id to account for all subclusters
                next_cluster_id += sub_n_clusters + 1  # +1 for noise/"remaining"
            else:
                # No meaningful split, keep original cluster
                logger.info(
                    f"Could not split cluster {cluster_id}, keeping as single cluster"
                )
                new_clusters[next_cluster_id] = keywords_in_cluster
                next_cluster_id += 1

        return new_clusters

    def cluster(
        self,
        keywords: List[str],
        embeddings: np.ndarray,
        min_cluster_size: int = 5,
        min_samples: int = 5,
        cluster_selection_epsilon: float = 0.0,
    ) -> ClusteringResult:
        """
        Cluster keywords using HDBSCAN algorithm.

        Args:
            keywords: List of keywords corresponding to embeddings
            embeddings: Array of shape (n_keywords, n_features)
            min_cluster_size: Minimum size of a cluster (smaller = more granular)
            min_samples: Minimum samples in neighborhood (higher = more conservative)
            cluster_selection_epsilon: Distance threshold for cluster merging

        Returns:
            ClusteringResult with organized clusters and noise

        Example:
            >>> service = ClusteringService()
            >>> result = service.cluster(keywords, embeddings, min_cluster_size=5)
            >>> print(f"Found {result.n_clusters} clusters")
            >>> print(f"Cluster 0 has {len(result.clusters[0])} keywords")
        """
        logger.info(
            f"Running HDBSCAN clustering on {len(keywords)} keywords "
            f"(min_cluster_size={min_cluster_size}, min_samples={min_samples})"
        )

        # Run HDBSCAN clustering
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            cluster_selection_epsilon=cluster_selection_epsilon,
            metric="euclidean",
        )

        labels = clusterer.fit_predict(embeddings)

        # Count clusters (excluding noise label -1)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        noise_count = np.sum(labels == -1)

        # Build keyword embeddings dict (needed for subclustering)
        keyword_embeddings = {kw: emb for kw, emb in zip(keywords, embeddings)}

        # Organize keywords by cluster
        clusters: Dict[int, List[str]] = {}
        noise: List[str] = []

        for keyword, label in zip(keywords, labels):
            if label == -1:
                noise.append(keyword)
            else:
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(keyword)

        logger.info(
            f"Found {n_clusters} clusters with {noise_count} noise points "
            f"({noise_count / len(labels) * 100:.1f}%)"
        )

        # Apply subclustering to large clusters
        if clusters:
            clusters = self._subcluster_large_clusters(
                clusters=clusters,
                keyword_embeddings=keyword_embeddings,
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                cluster_selection_epsilon=cluster_selection_epsilon,
            )
            n_clusters = len(clusters)
            logger.info(f"After subclustering: {n_clusters} total clusters")

        return ClusteringResult(
            labels=labels,
            n_clusters=n_clusters,
            clusters=clusters,
            noise=noise,
            keyword_embeddings=keyword_embeddings,
        )

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
