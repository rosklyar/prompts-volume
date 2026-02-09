"""Service for aggregating dashboard data across reports in a time period."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.evals_models import (
    AIAssistant,
    GroupReport,
    GroupReportItem,
    ReportItemStatus,
)
from src.database.models import Prompt
from src.reports.models.dashboard_models import (
    BrandVisibilityPoint,
    CompetitorVisibility,
    DashboardResponse,
    PeriodLiteral,
    PromptGap,
    SourceStat,
    TimelineDataPoint,
)
from src.reports.services.results_enricher import (
    ReportEnricher,
    extract_brands_and_domains,
)


class DashboardService:
    """Service for building dashboard analytics from reports in a time period.

    Uses dual session pattern:
    - prompts_session: for Prompt (prompts_db)
    - evals_session: for GroupReport, GroupReportItem, PromptEvaluation (evals_db)
    """

    def __init__(
        self,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
        enricher: ReportEnricher,
    ):
        self._prompts_session = prompts_session
        self._evals_session = evals_session
        self._enricher = enricher

    async def get_dashboard_data(
        self,
        group_id: int,
        user_id: str,
        assistant_id: int,
        from_date: datetime,
        to_date: datetime,
        preset_used: PeriodLiteral | None = None,
    ) -> DashboardResponse:
        """Get dashboard analytics aggregated across reports in a time period.

        Args:
            group_id: The prompt group ID
            user_id: The user ID
            assistant_id: The AI assistant ID to filter by
            from_date: Start date (inclusive)
            to_date: End date (exclusive)
            preset_used: Preset period used to resolve dates, if any

        Returns:
            DashboardResponse with brand visibility, competitors, sources, and prompt gaps
        """
        # Get assistant name
        assistant_query = select(AIAssistant).where(AIAssistant.id == assistant_id)
        assistant_result = await self._evals_session.execute(assistant_query)
        assistant = assistant_result.scalar_one_or_none()
        assistant_name = assistant.name if assistant else "Unknown"

        # Get all reports in time window for this group and assistant
        report_query = (
            select(GroupReport)
            .where(
                GroupReport.group_id == group_id,
                GroupReport.user_id == user_id,
                GroupReport.assistant_id == assistant_id,
                GroupReport.created_at >= from_date,
                GroupReport.created_at < to_date,
            )
            .options(
                selectinload(GroupReport.items).selectinload(GroupReportItem.evaluation)
            )
            .order_by(GroupReport.created_at.desc())
        )
        report_result = await self._evals_session.execute(report_query)
        reports = list(report_result.scalars().unique().all())

        # Empty response if no reports exist
        if not reports:
            return DashboardResponse(
                group_id=group_id,
                from_date=from_date,
                to_date=to_date,
                preset_used=preset_used,
                reports_included=0,
                assistant_name=assistant_name,
                brand_name=None,
                brand_visibility_percent=0.0,
                competitors=[],
                sources=[],
                prompt_gaps=[],
                prompt_gaps_count=0,
            )

        # Get brand/competitors config from most recent report
        latest_report = reports[0]
        brand_config = latest_report.brand_snapshot
        competitors_config = latest_report.competitors_snapshot or []

        brand_name = brand_config.get("name") if brand_config else None
        target_brand_name = brand_name

        # Extract brands and domains for detection
        brands, domains = extract_brands_and_domains(brand_config, competitors_config)

        # Deduplication and aggregation across all reports
        seen_evaluation_ids: set[int] = set()
        prompt_brand_ever_mentioned: dict[int, bool] = {}
        all_prompt_ids: set[int] = set()

        brand_mentions_per_eval: list[list | None] = []
        all_answers: list[dict | None] = []

        # Per-report tracking for timeline
        per_report_mentions: list[tuple[datetime, int, list[list | None]]] = []

        for report in reports:
            current_report_mentions: list[list | None] = []

            for item in report.items:
                if item.status != ReportItemStatus.INCLUDED:
                    continue
                if item.evaluation_id is None or item.evaluation is None:
                    continue

                all_prompt_ids.add(item.prompt_id)

                # Skip if we've already processed this evaluation
                if item.evaluation_id in seen_evaluation_ids:
                    continue
                seen_evaluation_ids.add(item.evaluation_id)

                answer = item.evaluation.answer
                all_answers.append(answer)

                response_text = answer.get("response") if answer else None

                # Detect brand mentions
                brand_mentions = None
                if brands and response_text:
                    brand_mentions = self._enricher.detect_brand_mentions(
                        response_text, brands
                    )
                brand_mentions_per_eval.append(brand_mentions)
                current_report_mentions.append(brand_mentions)

                # Track if target brand is mentioned for this prompt (across any eval)
                if target_brand_name and brand_mentions:
                    for mention in brand_mentions:
                        if mention.brand_name == target_brand_name:
                            prompt_brand_ever_mentioned[item.prompt_id] = True
                            break

            if current_report_mentions:
                per_report_mentions.append(
                    (report.created_at, report.id, current_report_mentions)
                )

        # Get prompt texts for gaps
        prompts_map = await self._get_prompts_by_ids(list(all_prompt_ids))

        # Prompt gaps: prompts that NEVER had brand mention in ANY evaluation
        prompt_gaps: list[PromptGap] = []
        for prompt_id in all_prompt_ids:
            if not prompt_brand_ever_mentioned.get(prompt_id, False):
                prompt = prompts_map.get(prompt_id)
                prompt_gaps.append(
                    PromptGap(
                        prompt_id=prompt_id,
                        prompt_text=prompt.prompt_text if prompt else "",
                    )
                )

        # Build citation leaderboard
        citation_leaderboard = self._enricher.build_citation_leaderboard(all_answers)

        # Convert to sources stats
        sources = self._build_sources(citation_leaderboard)

        # Build visibility timeline (chronological, oldest first)
        timeline = self._calculate_timeline(
            brand_config, competitors_config, per_report_mentions
        )

        # Use latest report's visibility for gauge and competitors
        if timeline:
            latest_point = timeline[-1]
            competitors = [
                CompetitorVisibility(
                    name=b.name,
                    domain=b.domain,
                    visibility_percent=b.visibility_percent,
                    is_target_brand=b.is_target_brand,
                )
                for b in latest_point.brands
            ]
            competitors.sort(key=lambda x: x.visibility_percent, reverse=True)
        else:
            competitors = []

        # Find target brand visibility
        brand_visibility = 0.0
        for comp in competitors:
            if comp.is_target_brand:
                brand_visibility = comp.visibility_percent
                break

        # Compute visibility change from the last two timeline points
        if len(timeline) >= 2:
            prev_vis = {b.name: b.visibility_percent for b in timeline[-2].brands}
            for comp in competitors:
                if comp.name in prev_vis:
                    delta = round(comp.visibility_percent - prev_vis[comp.name], 1)
                    comp.visibility_change = delta if delta != 0.0 else None

        return DashboardResponse(
            group_id=group_id,
            from_date=from_date,
            to_date=to_date,
            preset_used=preset_used,
            reports_included=len(reports),
            assistant_name=assistant_name,
            brand_name=brand_name,
            brand_visibility_percent=brand_visibility,
            competitors=competitors,
            sources=sources,
            prompt_gaps=prompt_gaps,
            prompt_gaps_count=len(prompt_gaps),
            timeline=timeline,
        )

    async def _get_prompts_by_ids(self, prompt_ids: list[int]) -> dict[int, Prompt]:
        """Fetch prompts from prompts_db, returns dict keyed by prompt_id."""
        if not prompt_ids:
            return {}
        result = await self._prompts_session.execute(
            select(Prompt).where(Prompt.id.in_(prompt_ids))
        )
        return {p.id: p for p in result.scalars().all()}

    def _calculate_visibility(
        self,
        brand_config: dict | None,
        competitors_config: list[dict],
        brand_mentions_per_item: list[list | None],
    ) -> list[CompetitorVisibility]:
        """Calculate visibility percentage for brand and all competitors.

        Visibility = (prompts with mentions / total prompts with answers) * 100
        """
        # Count items with answers (not None mentions list means had answer)
        items_with_answers = sum(
            1 for mentions in brand_mentions_per_item if mentions is not None
        )

        if items_with_answers == 0:
            return []

        # Build config list with target brand first
        all_configs = []
        if brand_config:
            all_configs.append((brand_config, True))
        for comp in competitors_config:
            all_configs.append((comp, False))

        # Count mentions per brand
        visibility_results: list[CompetitorVisibility] = []

        for config, is_target in all_configs:
            brand_name = config.get("name", "")
            domain = config.get("domain")

            # Count prompts where this brand is mentioned
            prompts_with_mention = 0
            for mentions in brand_mentions_per_item:
                if mentions is None:
                    continue
                for mention in mentions:
                    if mention.brand_name == brand_name:
                        prompts_with_mention += 1
                        break

            visibility_percent = (prompts_with_mention / items_with_answers) * 100

            visibility_results.append(
                CompetitorVisibility(
                    name=brand_name,
                    domain=domain,
                    visibility_percent=round(visibility_percent, 1),
                    is_target_brand=is_target,
                )
            )

        # Sort by visibility percentage descending
        visibility_results.sort(key=lambda x: x.visibility_percent, reverse=True)

        return visibility_results

    def _calculate_timeline(
        self,
        brand_config: dict | None,
        competitors_config: list[dict],
        per_report_mentions: list[tuple[datetime, int, list[list | None]]],
    ) -> list[TimelineDataPoint]:
        """Build chronological visibility timeline from per-report mention data.

        Reuses _calculate_visibility() for each report's mentions to get
        per-brand visibility at each point in time.
        """
        if not per_report_mentions:
            return []

        # Sort chronologically (oldest first) — reports were loaded desc
        per_report_mentions.sort(key=lambda x: x[0])

        timeline: list[TimelineDataPoint] = []
        for timestamp, report_id, mentions in per_report_mentions:
            competitors = self._calculate_visibility(
                brand_config, competitors_config, mentions
            )
            brands = [
                BrandVisibilityPoint(
                    name=c.name,
                    domain=c.domain,
                    visibility_percent=c.visibility_percent,
                    is_target_brand=c.is_target_brand,
                )
                for c in competitors
            ]
            timeline.append(
                TimelineDataPoint(
                    timestamp=timestamp,
                    report_id=report_id,
                    brands=brands,
                )
            )

        return timeline

    def _build_sources(self, citation_leaderboard) -> list[SourceStat]:
        """Build sources list from citation leaderboard.

        Uses domain counts from the leaderboard.
        """
        if not citation_leaderboard or not citation_leaderboard.domains:
            return []

        # Calculate total citations for percentage
        total_citations = sum(d.count for d in citation_leaderboard.domains)

        if total_citations == 0:
            return []

        sources: list[SourceStat] = []
        for domain_item in citation_leaderboard.domains:  # All domains, no limit
            percent = (domain_item.count / total_citations) * 100
            sources.append(
                SourceStat(
                    domain=domain_item.path,  # CitationCountItemModel uses 'path' for domain
                    citation_count=domain_item.count,
                    citation_percent=round(percent, 1),
                    coverage_percent=domain_item.coverage_percent,
                )
            )

        return sources
