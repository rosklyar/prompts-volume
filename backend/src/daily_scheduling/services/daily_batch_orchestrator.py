"""Orchestrator for daily scheduled batch processing."""

import logging
import uuid
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


class DailyBatchOrchestrator:
    """Orchestrates the daily scheduled batch processing.

    Single Responsibility: Coordinate the entire daily batch lifecycle.

    Flow:
    1. Collect enabled groups
    2. Aggregate prompts and check freshness
    3. Trigger BrightData batches for prompts needing refresh
    4. Create DailyScheduleBatch and DailyBatchGroupResult records
    5. Wait for webhooks or timeout
    6. Generate reports

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
        chunk_size: int = 50,
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
        self._chunk_size = chunk_size

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

            # 4. Analyze freshness for each group
            group_analyses: list[GroupPromptAnalysis] = []
            for group in enabled_groups:
                prompts = groups_prompts.get(group.group_id, [])
                analysis = await self._prompt_aggregator.analyze_group_prompts(
                    group.group_id,
                    group.user_id,
                    prompts,
                )
                group_analyses.append(analysis)

            # 5. Create group result records
            for group, analysis in zip(enabled_groups, group_analyses):
                prompts = groups_prompts.get(group.group_id, [])
                await self._batch_repo.create_group_result(
                    batch_id=batch_id,
                    group_id=group.group_id,
                    user_id=group.user_id,
                    prompts_in_group=len(prompts),
                    prompts_needing_refresh=len(analysis.prompts_needing_refresh),
                    prompts_already_fresh=len(analysis.fresh_prompt_selections),
                    fresh_prompt_selections=analysis.fresh_prompt_selections or None,
                )

            # 6. Deduplicate and trigger BrightData
            unique_prompts = self._prompt_aggregator.get_unique_prompts_needing_refresh(
                group_analyses
            )

            # Get prompt texts for unique prompts needing refresh
            prompts_for_refresh = await self._build_prompts_for_refresh(
                unique_prompts,
                groups_prompts,
            )

            brightdata_batch_ids = await self._trigger_brightdata_batches(
                prompts_for_refresh,
            )

            # 7. Update batch with stats and batch IDs
            total_prompts = sum(len(prompts) for prompts in groups_prompts.values())
            prompts_needing = len(unique_prompts)
            prompts_fresh = total_prompts - prompts_needing

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

    async def _build_prompts_for_refresh(
        self,
        prompt_ids: set[int],
        groups_prompts: dict[int, list[dict]],
    ) -> dict[int, str]:
        """Build dict of prompt_id -> prompt_text for prompts needing refresh."""
        prompts_dict: dict[int, str] = {}
        for prompts in groups_prompts.values():
            for p in prompts:
                if p["prompt_id"] in prompt_ids:
                    prompts_dict[p["prompt_id"]] = p["prompt_text"]
        return prompts_dict

    async def _trigger_brightdata_batches(
        self,
        prompts: dict[int, str],
    ) -> list[str]:
        """Trigger BrightData batches for prompts.

        Returns list of batch IDs.
        """
        if not prompts:
            return []

        if self._brightdata_service is None:
            logger.warning("BrightDataService not configured, skipping trigger")
            return []

        # Chunk prompts
        prompt_items = list(prompts.items())
        chunks = [
            prompt_items[i:i + self._chunk_size]
            for i in range(0, len(prompt_items), self._chunk_size)
        ]

        batch_ids: list[str] = []
        for chunk in chunks:
            batch_id = str(uuid.uuid4())
            chunk_dict = dict(chunk)

            await self._brightdata_service.trigger_batch(
                batch_id,
                chunk_dict,
                user_id="system",  # System-triggered
            )
            batch_ids.append(batch_id)

        return batch_ids

    async def process_completed_batch(self, batch_id: int) -> int:
        """Process a batch that's ready for report generation.

        Called after batch completion check determines it's ready.

        Returns count of generated reports.
        """
        return await self._report_generator.generate_all_reports(batch_id)
