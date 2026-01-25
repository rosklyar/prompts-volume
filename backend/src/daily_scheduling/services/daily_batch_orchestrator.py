"""Orchestrator for daily scheduled batch processing."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.services.charge_service import ChargeService
from src.brightdata.services.brightdata_service import BrightDataService
from src.daily_scheduling.models.domain import EnabledGroup, GroupPromptAnalysis
from src.daily_scheduling.repositories.daily_batch_repo import DailyBatchRepository
from src.daily_scheduling.services.batch_completion_service import BatchCompletionService
from src.daily_scheduling.services.batch_report_generator import BatchReportGenerator
from src.daily_scheduling.services.group_collector_service import GroupCollectorService
from src.daily_scheduling.services.prompt_aggregator_service import PromptAggregatorService
from src.database.evals_models import DailyBatchStatus

logger = logging.getLogger(__name__)


@dataclass
class GroupAssistantAnalysis:
    """Analysis for a (group, assistant) pair."""

    group_id: int
    user_id: str
    assistant_id: int
    prompts_in_group: int
    prompts_needing_refresh: list[int]
    fresh_prompt_selections: dict[int, int]


class DailyBatchOrchestrator:
    """Orchestrates the daily scheduled batch processing.

    Single Responsibility: Coordinate the entire daily batch lifecycle.

    Flow:
    1. Collect enabled groups (with assistant_ids)
    2. Aggregate prompts and check freshness PER (group, assistant)
    3. Trigger BrightData batches for prompts needing refresh
    4. Create DailyScheduleBatch and DailyBatchGroupResult records (one per group+assistant)
    5. Wait for webhooks or timeout
    6. Generate reports (one per group+assistant)

    Open/Closed: Can add new scheduling strategies without modifying core logic.
    """

    TIMEOUT_HOURS = 6

    def __init__(
        self,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
        *,
        charge_service: ChargeService,
        group_collector: GroupCollectorService | None = None,
        prompt_aggregator: PromptAggregatorService | None = None,
        batch_repo: DailyBatchRepository | None = None,
        brightdata_service: BrightDataService | None = None,
        completion_service: BatchCompletionService | None = None,
        report_generator: BatchReportGenerator | None = None,
    ) -> None:
        self._prompts_session = prompts_session
        self._evals_session = evals_session

        self._group_collector = group_collector or GroupCollectorService(prompts_session)
        self._prompt_aggregator = prompt_aggregator or PromptAggregatorService(evals_session)
        self._batch_repo = batch_repo or DailyBatchRepository(evals_session)
        self._brightdata_service = brightdata_service
        self._completion_service = completion_service or BatchCompletionService(evals_session)
        self._report_generator = report_generator or BatchReportGenerator(
            prompts_session, evals_session, charge_service=charge_service
        )

    async def start_daily_batch(self) -> int | None:
        """Start daily batch processing.

        Called by APScheduler at 6 AM UTC.

        Returns the batch ID if created, None if no groups to process.
        """
        today = date.today()

        # Check if batch already exists for today
        existing = await self._batch_repo.get_batch_for_date(today)
        if existing is not None:
            logger.info(f"Batch already exists for {today}")
            return existing.id

        logger.info(f"Starting daily batch for {today}")

        # 1. Collect enabled groups
        enabled_groups = await self._group_collector.get_enabled_groups()
        if not enabled_groups:
            logger.info("No groups with scheduling enabled")
            return None

        logger.info(f"Found {len(enabled_groups)} enabled groups")

        # 2. Create batch record
        now = datetime.now(timezone.utc)
        timeout_at = now + timedelta(hours=self.TIMEOUT_HOURS)

        batch = await self._batch_repo.create_batch(
            scheduled_date=today,
            timeout_at=timeout_at,
        )
        batch_id = batch.id

        try:
            # 3. Get prompts for all groups
            group_ids = [g.group_id for g in enabled_groups]
            groups_prompts = await self._group_collector.get_all_prompts_for_groups(group_ids)

            # 4. Analyze freshness for each (group, assistant) pair
            group_assistant_analyses: list[GroupAssistantAnalysis] = []
            for group in enabled_groups:
                prompts = groups_prompts.get(group.group_id, [])
                for assistant_id in group.assistant_ids:
                    analysis = await self._prompt_aggregator.analyze_group_prompts(
                        group.group_id,
                        group.user_id,
                        prompts,
                        assistant_id=assistant_id,
                    )
                    group_assistant_analyses.append(GroupAssistantAnalysis(
                        group_id=group.group_id,
                        user_id=group.user_id,
                        assistant_id=assistant_id,
                        prompts_in_group=len(prompts),
                        prompts_needing_refresh=analysis.prompts_needing_refresh,
                        fresh_prompt_selections=analysis.fresh_prompt_selections,
                    ))

            # 5. Create group result records - one per (group, assistant)
            for analysis in group_assistant_analyses:
                await self._batch_repo.create_group_result(
                    batch_id=batch_id,
                    group_id=analysis.group_id,
                    user_id=analysis.user_id,
                    assistant_id=analysis.assistant_id,
                    prompts_in_group=analysis.prompts_in_group,
                    prompts_needing_refresh=len(analysis.prompts_needing_refresh),
                    prompts_already_fresh=len(analysis.fresh_prompt_selections),
                    fresh_prompt_selections=analysis.fresh_prompt_selections or None,
                )

            # 6. Trigger BrightData grouped by (country, assistant)
            brightdata_batch_ids = await self._trigger_brightdata_batches_by_country_assistant(
                list(enabled_groups),
                group_assistant_analyses,
                groups_prompts,
            )

            # Calculate stats - unique prompts per assistant
            total_prompts_per_assistant = self._count_total_prompts_per_assistant(
                group_assistant_analyses
            )
            total_prompts = sum(total_prompts_per_assistant.values())
            prompts_needing = self._count_unique_prompts_needing_refresh(group_assistant_analyses)
            prompts_fresh = total_prompts - prompts_needing

            # 7. Update batch with stats and batch IDs
            await self._batch_repo.set_batch_group_ids(batch_id, group_ids)
            await self._batch_repo.set_batch_brightdata_ids(batch_id, brightdata_batch_ids)
            await self._batch_repo.set_batch_prompt_stats(
                batch_id,
                total_prompts=total_prompts,
                prompts_needing_refresh=prompts_needing,
                prompts_already_fresh=prompts_fresh,
            )

            # 8. Set status to AWAITING or trigger immediate report generation
            if brightdata_batch_ids:
                await self._batch_repo.update_batch_status(
                    batch_id,
                    DailyBatchStatus.AWAITING,
                )
                logger.info(
                    f"Batch {batch_id} waiting for {len(brightdata_batch_ids)} "
                    f"BrightData batches ({prompts_needing} prompts)"
                )
            else:
                # All prompts fresh - generate reports immediately
                logger.info(f"Batch {batch_id} - all prompts fresh, generating reports")
                await self._batch_repo.update_batch_status(
                    batch_id,
                    DailyBatchStatus.GENERATING,
                )
                await self._evals_session.commit()
                await self._report_generator.generate_all_reports(batch_id)

            await self._evals_session.commit()
            await self._prompts_session.commit()

            return batch_id

        except Exception:
            logger.exception(f"Failed to process daily batch {batch_id}")
            await self._batch_repo.update_batch_status(
                batch_id,
                DailyBatchStatus.FAILED,
            )
            await self._evals_session.commit()
            raise

    def _count_total_prompts_per_assistant(
        self,
        analyses: list[GroupAssistantAnalysis],
    ) -> dict[int, int]:
        """Count total prompts per assistant across all groups."""
        counts: dict[int, int] = {}
        for a in analyses:
            if a.assistant_id not in counts:
                counts[a.assistant_id] = 0
            counts[a.assistant_id] += a.prompts_in_group
        return counts

    def _count_unique_prompts_needing_refresh(
        self,
        analyses: list[GroupAssistantAnalysis],
    ) -> int:
        """Count unique (prompt, assistant) pairs needing refresh."""
        unique_pairs: set[tuple[int, int]] = set()
        for a in analyses:
            for prompt_id in a.prompts_needing_refresh:
                unique_pairs.add((prompt_id, a.assistant_id))
        return len(unique_pairs)

    def _build_prompts_by_country_assistant(
        self,
        enabled_groups: list[EnabledGroup],
        analyses: list[GroupAssistantAnalysis],
        groups_prompts: dict[int, list[dict]],
    ) -> dict[tuple[int, str, int], dict[int, str]]:
        """Build prompts grouped by (country_id, country_iso_code, assistant_id).

        Returns dict mapping (country_id, country_iso_code, assistant_id) -> (prompt_id -> prompt_text).
        """
        # Build mapping from group_id to country info
        group_to_country: dict[int, tuple[int, str]] = {
            g.group_id: (g.country_id, g.country_iso_code)
            for g in enabled_groups
        }

        # Build prompt_id to prompt_text mapping
        prompt_texts: dict[int, str] = {}
        for prompts in groups_prompts.values():
            for p in prompts:
                prompt_texts[p["prompt_id"]] = p["prompt_text"]

        # Group prompts by (country, assistant)
        country_assistant_prompts: dict[tuple[int, str, int], dict[int, str]] = {}

        for analysis in analyses:
            country_key = group_to_country.get(analysis.group_id)
            if not country_key:
                continue

            key = (country_key[0], country_key[1], analysis.assistant_id)

            for prompt_id in analysis.prompts_needing_refresh:
                if prompt_id not in prompt_texts:
                    continue

                if key not in country_assistant_prompts:
                    country_assistant_prompts[key] = {}

                country_assistant_prompts[key][prompt_id] = prompt_texts[prompt_id]

        return country_assistant_prompts

    async def _trigger_brightdata_batches(
        self,
        prompts: dict[int, str],
        *,
        country_id: int,
        country_iso_code: str,
        assistant_id: int = 1,
    ) -> list[str]:
        """Trigger BrightData batches for prompts.

        Args:
            prompts: Dict of prompt_id -> prompt_text
            country_id: Country ID for scraping
            country_iso_code: Country ISO code for scraping
            assistant_id: AI assistant ID to scrape

        Returns list of batch IDs.
        """
        if not prompts or self._brightdata_service is None:
            return []

        return await self._brightdata_service.trigger_batches_chunked(
            prompts=prompts,
            user_id="system",
            country_id=country_id,
            country_iso_code=country_iso_code,
            assistant_id=assistant_id,
        )

    async def _trigger_brightdata_batches_by_country_assistant(
        self,
        enabled_groups: list[EnabledGroup],
        analyses: list[GroupAssistantAnalysis],
        groups_prompts: dict[int, list[dict]],
    ) -> list[str]:
        """Trigger BrightData batches grouped by (country, assistant).

        Returns list of all batch IDs.
        """
        country_assistant_prompts = self._build_prompts_by_country_assistant(
            enabled_groups, analyses, groups_prompts
        )

        all_batch_ids: list[str] = []

        for (country_id, country_iso_code, assistant_id), prompts in country_assistant_prompts.items():
            batch_ids = await self._trigger_brightdata_batches(
                prompts,
                country_id=country_id,
                country_iso_code=country_iso_code,
                assistant_id=assistant_id,
            )
            all_batch_ids.extend(batch_ids)

        return all_batch_ids

    async def process_completed_batch(self, batch_id: int) -> int:
        """Process a batch that's ready for report generation.

        Called after batch completion check determines it's ready.

        Returns count of generated reports.
        """
        return await self._report_generator.generate_all_reports(batch_id)
