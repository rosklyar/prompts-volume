"""Service for persisting and retrieving GEO audit results."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.users_models import GeoAuditResult
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
            score_total=result.score.total,
            score_rating=result.score.rating,
            result_json=result.model_dump(mode="json"),
        )
        self._session.add(row)
        await self._session.flush()
        return row
