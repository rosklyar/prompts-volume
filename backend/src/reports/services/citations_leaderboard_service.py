"""Service for aggregating citations across multiple reports."""

from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.evals_models import GroupReport, GroupReportItem, ReportItemStatus
from src.reports.models.citation_models import CitationLeaderboardModel
from src.reports.services.results_enricher import ReportEnricher


PeriodLiteral = Literal["1d", "7d", "30d"]

_PERIOD_DAYS: dict[PeriodLiteral, int] = {
    "1d": 1,
    "7d": 7,
    "30d": 30,
}


class AggregatedLeaderboardResult:
    """Result from aggregating citations across reports."""

    __slots__ = ("citation_leaderboard", "reports_included")

    def __init__(
        self,
        citation_leaderboard: CitationLeaderboardModel,
        reports_included: int,
    ):
        self.citation_leaderboard = citation_leaderboard
        self.reports_included = reports_included


class CitationsLeaderboardService:
    """Aggregates citations across multiple group reports."""

    def __init__(
        self,
        evals_session: AsyncSession,
        enricher: ReportEnricher,
    ):
        self.evals_session = evals_session
        self.enricher = enricher

    async def get_aggregated_leaderboard(
        self,
        *,
        group_id: int,
        user_id: str,
        period: PeriodLiteral,
        assistant_id: int | None = None,
    ) -> AggregatedLeaderboardResult:
        """Aggregate citation leaderboard across reports in a time period.

        Args:
            group_id: The prompt group ID.
            user_id: The user who owns the group.
            period: Time period literal ("1d", "7d", "30d").
            assistant_id: Optional AI assistant filter.

        Returns:
            AggregatedLeaderboardResult with leaderboard and report count.
        """
        from_date = datetime.now(timezone.utc) - timedelta(days=_PERIOD_DAYS[period])

        # Build query for reports in the time window
        conditions = [
            GroupReport.group_id == group_id,
            GroupReport.user_id == user_id,
            GroupReport.created_at >= from_date,
        ]
        if assistant_id is not None:
            conditions.append(GroupReport.assistant_id == assistant_id)

        reports_result = await self.evals_session.execute(
            select(GroupReport)
            .where(*conditions)
            .options(
                selectinload(GroupReport.items).selectinload(
                    GroupReportItem.evaluation
                )
            )
            .order_by(GroupReport.created_at.desc())
        )
        reports = list(reports_result.scalars().unique().all())

        # Collect unique (evaluation_id, answer) pairs across all reports
        seen_evaluation_ids: set[int] = set()
        all_answers: list[dict | None] = []

        for report in reports:
            for item in report.items:
                if item.status != ReportItemStatus.INCLUDED:
                    continue
                if item.evaluation_id is None or item.evaluation is None:
                    continue
                if item.evaluation_id in seen_evaluation_ids:
                    continue
                seen_evaluation_ids.add(item.evaluation_id)
                all_answers.append(item.evaluation.answer)

        citation_leaderboard = self.enricher.build_citation_leaderboard(all_answers)

        return AggregatedLeaderboardResult(
            citation_leaderboard=citation_leaderboard,
            reports_included=len(reports),
        )
