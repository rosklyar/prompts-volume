"""Cluster keywords by embedding similarity and score by SEO value."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.embeddings.clustering_service import ClusteringService
from src.embeddings.embeddings_service import EmbeddingsService
from src.keyword_inspiration.models.api_models import (
    ClusterKeywordsResponse,
    ScoredClusterResponse,
)
from src.keyword_inspiration.models.domain import RankedKeyword, ScoredCluster
from src.keyword_inspiration.predicates import build_chain_from_config
from src.keyword_inspiration.repository import KeywordCacheRepository
from src.keyword_inspiration.services.keyword_fetch_service import KeywordFetchService

logger = logging.getLogger(__name__)


class ClusterScoringService:
    """Fetches keywords (if needed), clusters them, scores and ranks clusters."""

    def __init__(
        self,
        session: AsyncSession,
        embeddings_service: EmbeddingsService,
        clustering_service: ClusteringService,
        keyword_fetch_service: KeywordFetchService,
        *,
        cache_ttl_days: int,
        top_clusters: int,
    ):
        self.repo = KeywordCacheRepository(session)
        self.embeddings_service = embeddings_service
        self.clustering_service = clustering_service
        self.keyword_fetch_service = keyword_fetch_service
        self.cache_ttl_days = cache_ttl_days
        self.top_clusters = top_clusters

    async def discover_clusters(
        self,
        domains: list[str],
        country_code: str,
        language_name: str,
        *,
        brand_names: list[str] | None = None,
        keyword_filter_config: list[dict] | None = None,
    ) -> ClusterKeywordsResponse:
        """Fetch keywords (cached), merge, filter, cluster, score, and return top clusters."""
        # 1. Ensure keywords are cached
        await self.keyword_fetch_service.fetch_if_needed(
            domains, country_code, language_name
        )

        # 2. Load from cache
        all_ranked = await self._load_and_merge(domains, country_code, language_name)

        # 3. Apply predicate chain
        chain = build_chain_from_config(keyword_filter_config, brand_names=brand_names)
        all_ranked = chain.apply(all_ranked)

        if not all_ranked:
            return ClusterKeywordsResponse(clusters=[], total_keywords=0, noise_keywords=0)

        keyword_texts = [rk.keyword for rk in all_ranked]
        keyword_map = {rk.keyword: rk for rk in all_ranked}

        # 3. Embed
        embeddings_result = self.embeddings_service.encode_texts(keyword_texts)
        embeddings = [e.embedding for e in embeddings_result]

        # 4. Cluster
        clustering_result = self.clustering_service.cluster(keyword_texts, embeddings)

        # 5. Score each cluster
        scored_clusters: list[ScoredCluster] = []
        for cluster_id, cluster_keywords in clustering_result.clusters.items():
            if cluster_id == -1:
                continue  # skip noise
            score = sum(
                keyword_map[kw].search_volume
                for kw in cluster_keywords
                if kw in keyword_map and keyword_map[kw].rank_group <= 3
            )
            title_keyword = max(
                cluster_keywords,
                key=lambda kw: keyword_map[kw].search_volume if kw in keyword_map else 0,
            )
            scored_clusters.append(ScoredCluster(
                cluster_id=cluster_id,
                keywords=cluster_keywords,
                score=score,
                title=title_keyword,
                keyword_count=len(cluster_keywords),
            ))

        # 6. Sort and take top N
        scored_clusters.sort(key=lambda c: c.score, reverse=True)
        top = scored_clusters[: self.top_clusters]

        noise_count = len(clustering_result.noise)

        return ClusterKeywordsResponse(
            clusters=[
                ScoredClusterResponse(
                    cluster_id=c.cluster_id,
                    keywords=c.keywords,
                    score=c.score,
                    title=c.title,
                    keyword_count=c.keyword_count,
                )
                for c in top
            ],
            total_keywords=len(all_ranked),
            noise_keywords=noise_count,
        )

    async def _load_and_merge(
        self,
        domains: list[str],
        country_code: str,
        language_name: str,
    ) -> list[RankedKeyword]:
        """Load keywords from cache for all domains, merge and dedup."""
        seen: dict[str, RankedKeyword] = {}

        for domain in domains:
            cached = await self.repo.get_cached(
                domain, country_code, language_name, ttl_days=self.cache_ttl_days
            )
            if cached is None:
                logger.warning(f"No cache for {domain}, skipping")
                continue

            for entry in cached:
                kw = entry["keyword"]
                rk = RankedKeyword(
                    keyword=kw,
                    search_volume=entry.get("search_volume", 0),
                    rank_group=entry.get("rank_group", 0),
                )
                # Keep entry with highest search_volume
                if kw not in seen or rk.search_volume > seen[kw].search_volume:
                    seen[kw] = rk

        return list(seen.values())
