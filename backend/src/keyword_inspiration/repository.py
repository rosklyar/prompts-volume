"""Repository for keyword cache database operations."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import KeywordCache

logger = logging.getLogger(__name__)


class KeywordCacheRepository:
    """Manages cached keyword data per domain."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_cached(
        self,
        domain: str,
        country_code: str,
        language_name: str,
        *,
        ttl_days: int,
    ) -> list[dict] | None:
        """Return cached keywords if fresh, None if stale or missing."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
        stmt = select(KeywordCache).where(
            KeywordCache.domain == domain,
            KeywordCache.country_code == country_code,
            KeywordCache.language_name == language_name,
            KeywordCache.fetched_at >= cutoff,
        )
        result = await self.session.execute(stmt)
        cache = result.scalar_one_or_none()
        if cache is None:
            return None
        return cache.keywords_data

    async def upsert(
        self,
        domain: str,
        country_code: str,
        language_name: str,
        keywords_data: list[dict],
    ) -> None:
        """Insert or update cached keywords for a domain."""
        now = datetime.now(timezone.utc)
        stmt = (
            insert(KeywordCache)
            .values(
                domain=domain,
                country_code=country_code,
                language_name=language_name,
                keywords_data=keywords_data,
                fetched_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_keyword_cache_domain_country_lang",
                set_={"keywords_data": keywords_data, "fetched_at": now},
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
        logger.info(f"Cached {len(keywords_data)} keywords for {domain}")
