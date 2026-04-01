"""Service for persisting and retrieving GEO audit results."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.users_models import GeoAuditPageResult, GeoAuditResult
from src.geo_audit.models.api_models import GeoAuditResponse


class GeoAuditService:
    """CRUD operations for persisted GEO audit results."""

    def __init__(self, session: AsyncSession, *, cooldown_hours: int):
        self._session = session
        self._cooldown_hours = cooldown_hours

    async def get_latest(self, user_id: str) -> GeoAuditResult | None:
        stmt = (
            select(GeoAuditResult)
            .where(GeoAuditResult.user_id == user_id)
            .order_by(GeoAuditResult.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, audit_id: int) -> GeoAuditResult | None:
        return await self._session.get(GeoAuditResult, audit_id)

    async def check_cooldown(self, user_id: str) -> datetime | None:
        """Return retry_after datetime if cooldown is active, else None."""
        latest = await self.get_latest(user_id)
        if latest is None:
            return None

        retry_after = latest.created_at + timedelta(hours=self._cooldown_hours)
        if retry_after > datetime.now(timezone.utc):
            return retry_after
        return None

    async def save(
        self,
        *,
        user_id: str,
        url: str,
        result: GeoAuditResponse,
    ) -> GeoAuditResult:
        row = GeoAuditResult(
            user_id=user_id,
            url=url,
            status="completed",
            score_total=result.score.total,
            score_rating=result.score.rating,
            result_json=result.model_dump(mode="json"),
            pages_discovered=1,
            pages_audited=1,
            pages_total=1,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def create_pending(self, *, user_id: str, url: str) -> GeoAuditResult:
        """Create a pending audit row for a background site audit."""
        row = GeoAuditResult(
            user_id=user_id,
            url=url,
            status="pending",
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_page_results(self, audit_id: int) -> list[GeoAuditPageResult]:
        stmt = (
            select(GeoAuditPageResult)
            .where(GeoAuditPageResult.audit_id == audit_id)
            .order_by(GeoAuditPageResult.id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_page_result(self, page_id: int) -> GeoAuditPageResult | None:
        return await self._session.get(GeoAuditPageResult, page_id)
