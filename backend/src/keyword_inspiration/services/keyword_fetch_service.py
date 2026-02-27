"""Fetch and cache keywords from DataForSEO."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.keyword_inspiration.repository import KeywordCacheRepository
from src.keyword_inspiration.services.data_for_seo_service import (
    DataForSEOPaymentError,
    DataForSEOService,
)
from src.utils.keyword_filters import filter_by_brand_exclusion, filter_by_word_count

logger = logging.getLogger(__name__)


class KeywordFetchService:
    """Fetches ranked keywords from DataForSEO with caching."""

    def __init__(
        self,
        session: AsyncSession,
        dataforseo_service: DataForSEOService,
        *,
        cache_ttl_days: int,
    ):
        self.repo = KeywordCacheRepository(session)
        self.dataforseo = dataforseo_service
        self.cache_ttl_days = cache_ttl_days

    async def fetch_if_needed(
        self,
        domains: list[str],
        country_code: str,
        language_name: str,
        *,
        brand_names: list[str] | None = None,
    ) -> None:
        """Fetch keywords for all domains, using cache when fresh. No return value."""
        for domain in domains:
            cached = await self.repo.get_cached(
                domain, country_code, language_name, ttl_days=self.cache_ttl_days
            )
            if cached is not None:
                logger.info(f"Cache hit for {domain}: {len(cached)} keywords")
                continue

            logger.info(f"Cache miss for {domain}, fetching from DataForSEO")
            try:
                ranked_keywords = await self.dataforseo.get_all_ranked_keywords_for_site(
                    target_domain=domain,
                    location_name=country_code,
                    language=language_name,
                    batch_size=settings.dataforseo_batch_size,
                    max_total=settings.dataforseo_max_total,
                    timeout=settings.dataforseo_timeout,
                )
            except DataForSEOPaymentError:
                logger.warning(f"DataForSEO has no credits, skipping {domain}")
                continue

            # Filter keywords before caching
            keyword_texts = [rk.keyword for rk in ranked_keywords]
            filtered_texts = filter_by_word_count(keyword_texts, min_words=3)
            if brand_names:
                filtered_texts = filter_by_brand_exclusion(filtered_texts, brand_names)
            filtered_set = set(filtered_texts)

            keywords_data = [
                {
                    "keyword": rk.keyword,
                    "search_volume": rk.search_volume,
                    "rank_group": rk.rank_group,
                }
                for rk in ranked_keywords
                if rk.keyword in filtered_set
            ]

            await self.repo.upsert(domain, country_code, language_name, keywords_data)
