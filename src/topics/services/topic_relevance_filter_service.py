"""Service for filtering clusters by relevance to business topics/categories."""

import logging
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from src.embeddings.clustering_service import ClusteringResult
from src.embeddings.embeddings_service import EmbeddingsService, get_embeddings_service

logger = logging.getLogger(__name__)


@dataclass
class ClusterWithRelevance:
    """A cluster with its relevance score and best matching topic."""

    cluster_id: int
    keywords: List[str]
    best_topic: str  # Topic with highest average similarity
    relevance_score: float  # % of keywords above threshold
    avg_similarity: float  # Average similarity with best topic


class TopicRelevanceFilterService:
    """
    Filter clusters by relevance to business topics/categories.

    Returns clusters organized by their best-matching topic.
    """

    def __init__(self, embeddings_service: EmbeddingsService):
        """
        Initialize with embeddings service for generating topic embeddings.

        Args:
            embeddings_service: Service for generating embeddings
        """
        self.embeddings_service = embeddings_service

    def filter_by_topics(
        self,
        clustering_result: ClusteringResult,
        topics: List[str],
        similarity_threshold: float = 0.7,
        min_relevant_ratio: float = 0.5,
    ) -> Dict[str, List[ClusterWithRelevance]]:
        """
        Filter clusters by topic relevance and organize by best-matching topic.

        Algorithm:
        1. Generate embeddings for all topics
        2. For each cluster:
           - Get keyword embeddings from clustering_result
           - Calculate cosine similarity: keywords x topics
           - Count keywords with max_similarity >= threshold
           - If relevant_ratio >= min_relevant_ratio: keep cluster
           - Assign cluster to topic with highest average similarity
        3. Return: topic -> list of relevant clusters

        Args:
            clustering_result: Result from clustering with embeddings
            topics: Business topics/categories to match against
            similarity_threshold: Min cosine similarity for keyword relevance (default: 0.7)
            min_relevant_ratio: Min % of relevant keywords to keep cluster (default: 0.5)

        Returns:
            Dictionary mapping topic name -> list of ClusterWithRelevance objects

        Example:
            >>> result = service.filter_by_topics(
            ...     clustering_result,
            ...     topics=["laptops", "smartphones", "TVs"],
            ...     similarity_threshold=0.7,
            ...     min_relevant_ratio=0.5
            ... )
            >>> result["laptops"]
            [ClusterWithRelevance(cluster_id=0, keywords=[...], relevance_score=0.75, ...)]
        """
        logger.info(
            f"Filtering {clustering_result.n_clusters} clusters by {len(topics)} topics "
            f"(threshold={similarity_threshold}, min_ratio={min_relevant_ratio})"
        )

        # Generate topic embeddings
        topic_embeddings_list = self.embeddings_service.encode_texts(topics)
        topic_embeddings = np.array([te.embedding for te in topic_embeddings_list])

        # Initialize result dict with empty lists for each topic
        result: Dict[str, List[ClusterWithRelevance]] = {topic: [] for topic in topics}

        kept_clusters = 0
        removed_clusters = 0

        # Process each cluster
        for cluster_id, cluster_keywords in clustering_result.clusters.items():
            # Get keyword embeddings for this cluster
            cluster_embeddings = np.array(
                [clustering_result.keyword_embeddings[kw] for kw in cluster_keywords]
            )

            # Calculate similarity matrix: (n_keywords, n_topics)
            similarity_matrix = cosine_similarity(cluster_embeddings, topic_embeddings)

            # For each keyword, find max similarity across all topics
            max_similarities = similarity_matrix.max(axis=1)

            # Count relevant keywords (those with max_similarity >= threshold)
            relevant_count = np.sum(max_similarities >= similarity_threshold)
            relevance_score = relevant_count / len(cluster_keywords)

            # Keep cluster if relevance_score meets threshold
            if relevance_score >= min_relevant_ratio:
                # Find best matching topic (highest average similarity)
                avg_similarities_per_topic = similarity_matrix.mean(axis=0)
                best_topic_idx = avg_similarities_per_topic.argmax()
                best_topic = topics[best_topic_idx]
                avg_similarity = avg_similarities_per_topic[best_topic_idx]

                # Create cluster info
                cluster_info = ClusterWithRelevance(
                    cluster_id=cluster_id,
                    keywords=cluster_keywords,
                    best_topic=best_topic,
                    relevance_score=relevance_score,
                    avg_similarity=avg_similarity,
                )

                # Add to result under best topic
                result[best_topic].append(cluster_info)
                kept_clusters += 1
            else:
                removed_clusters += 1

        logger.info(
            f"Topic filtering complete: kept {kept_clusters} clusters, "
            f"removed {removed_clusters} clusters"
        )

        # Log distribution across topics
        for topic, clusters in result.items():
            if clusters:
                logger.info(f"  Topic '{topic}': {len(clusters)} clusters")

        return result


# Global instance for dependency injection
_topic_relevance_filter_service = None


def get_topic_relevance_filter_service() -> TopicRelevanceFilterService:
    """
    Get the global TopicRelevanceFilterService instance.
    Creates one if it doesn't exist yet.

    Uses the singleton EmbeddingsService instance.

    Returns:
        TopicRelevanceFilterService instance
    """
    global _topic_relevance_filter_service
    if _topic_relevance_filter_service is None:
        _topic_relevance_filter_service = TopicRelevanceFilterService(
            embeddings_service=get_embeddings_service()
        )
    return _topic_relevance_filter_service
