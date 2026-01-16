"""Service for generating reports for all groups in a daily batch."""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models.domain import ChargeResult
from src.daily_scheduling.repositories.daily_batch_repo import DailyBatchRepository
from src.database.evals_models import (
    DailyBatchGroupStatus,
    DailyBatchStatus,
    DailyScheduleBatch,
    EvaluationStatus,
    GroupReport,
    PromptEvaluation,
)
from src.database.models import PromptGroup
from src.reports.models.api_models import PromptSelection
from src.reports.services.report_service import ReportService

logger = logging.getLogger(__name__)


class NoOpChargeService:
    """No-op charge service for scheduled reports.

    Scheduled reports are free - no billing charges applied.
    Returns success without actually charging the user.
    """

    async def charge_for_evaluations(
        self,
        user_id: str,
        evaluation_ids: list[int],
    ) -> ChargeResult:
        """Return success without charging."""
        return ChargeResult(
            charged_evaluation_ids=evaluation_ids,
            skipped_evaluation_ids=[],
            total_charged=Decimal("0"),
            remaining_balance=Decimal("0"),
        )

    async def preview_charge(
        self,
        user_id: str,
        evaluation_ids: list[int],
    ) -> dict:
        """Preview returns zero cost."""
        return {
            "fresh_count": len(evaluation_ids),
            "already_consumed_count": 0,
            "estimated_cost": Decimal("0"),
            "user_balance": Decimal("0"),
            "affordable_count": len(evaluation_ids),
            "needs_top_up": False,
        }


class BatchReportGenerator:
    """Generates reports for all groups in a daily batch.

    Single Responsibility: Generate reports from batch data.
    """

    def __init__(
        self,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
        *,
        report_service: ReportService | None = None,
        batch_repo: DailyBatchRepository | None = None,
    ) -> None:
        self._prompts_session = prompts_session
        self._evals_session = evals_session
        self._report_service = report_service or ReportService(
            prompts_session,
            evals_session,
            charge_service=NoOpChargeService(),
        )
        self._batch_repo = batch_repo or DailyBatchRepository(evals_session)

    async def generate_all_reports(self, batch_id: int) -> int:
        """Generate reports for all groups in the batch.

        Returns count of successfully generated reports.
        """
        batch = await self._batch_repo.get_batch_by_id(batch_id)
        if batch is None:
            logger.error(f"Batch {batch_id} not found")
            return 0

        if batch.status != DailyBatchStatus.GENERATING:
            logger.warning(f"Batch {batch_id} not in GENERATING status")
            return 0

        group_results = await self._batch_repo.get_group_results_for_batch(batch_id)
        if not group_results:
            logger.warning(f"No group results for batch {batch_id}")
            await self._batch_repo.update_batch_status(
                batch_id,
                DailyBatchStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
            )
            return 0

        generated_count = 0
        for result in group_results:
            if result.status != DailyBatchGroupStatus.PENDING:
                continue

            try:
                report_id = await self._generate_group_report(
                    result.group_id,
                    result.user_id,
                    result.fresh_prompt_selections or {},
                )

                await self._batch_repo.update_group_result_status(
                    result.id,
                    DailyBatchGroupStatus.COMPLETED,
                    report_id=report_id,
                )
                generated_count += 1
                logger.info(
                    f"Generated report {report_id} for group {result.group_id}"
                )

            except Exception:
                logger.exception(
                    f"Failed to generate report for group {result.group_id}"
                )
                await self._batch_repo.update_group_result_status(
                    result.id,
                    DailyBatchGroupStatus.FAILED,
                )

        # Mark batch as completed
        now = datetime.now(timezone.utc)
        await self._batch_repo.update_batch_status(
            batch_id,
            DailyBatchStatus.COMPLETED,
            completed_at=now,
        )

        # Update schedule_last_run_at for all groups
        await self._update_groups_last_run(batch.group_ids, now)

        return generated_count

    async def _generate_group_report(
        self,
        group_id: int,
        user_id: str,
        fresh_prompt_selections: dict[int, int],
    ) -> int:
        """Generate a report for a single group.

        Args:
            group_id: The group ID
            user_id: The user ID
            fresh_prompt_selections: Map of prompt_id -> evaluation_id
                for prompts that were fresh at scheduling time

        Returns:
            The generated report ID
        """
        # Get group for brand/competitor snapshot
        group = await self._get_group(group_id)
        if group is None:
            raise ValueError(f"Group {group_id} not found")

        # Get all prompts in group
        from src.daily_scheduling.services.group_collector_service import (
            GroupCollectorService,
        )
        collector = GroupCollectorService(self._prompts_session)
        prompt_ids = await collector.get_prompt_ids_for_group(group_id)

        # Build selections using:
        # 1. Pre-recorded selections for fresh prompts
        # 2. Latest evaluation for prompts that needed refresh
        selections = await self._build_selections(
            prompt_ids,
            fresh_prompt_selections,
        )

        # Generate report
        report = await self._report_service.generate_report_with_selections(
            group_id=group_id,
            user_id=user_id,
            selections=selections,
            title="Scheduled Report",
            brand_snapshot=group.brand,
            competitors_snapshot=group.competitors,
        )

        return report.id

    async def _build_selections(
        self,
        prompt_ids: list[int],
        fresh_prompt_selections: dict[int, int],
    ) -> list[PromptSelection]:
        """Build evaluation selections for report.

        For prompts with pre-recorded fresh evaluation: use that ID.
        For prompts needing refresh: use latest completed evaluation.
        For prompts with no data: use None (will be marked AWAITING).
        """
        # Convert dict keys from str to int if needed (JSON serialization)
        fresh_selections = {
            int(k): v for k, v in fresh_prompt_selections.items()
        }

        # Get latest evaluations for prompts that needed refresh
        prompts_needing_lookup = [
            pid for pid in prompt_ids if pid not in fresh_selections
        ]

        latest_evals: dict[int, int] = {}
        if prompts_needing_lookup:
            latest_evals = await self._get_latest_evaluations(prompts_needing_lookup)

        # Build selections
        selections: list[PromptSelection] = []
        for prompt_id in prompt_ids:
            if prompt_id in fresh_selections:
                # Use pre-recorded fresh evaluation
                eval_id = fresh_selections[prompt_id]
            elif prompt_id in latest_evals:
                # Use latest evaluation (from refresh)
                eval_id = latest_evals[prompt_id]
            else:
                # No evaluation available
                eval_id = None

            selections.append(PromptSelection(
                prompt_id=prompt_id,
                evaluation_id=eval_id,
            ))

        return selections

    async def _get_latest_evaluations(
        self,
        prompt_ids: list[int],
    ) -> dict[int, int]:
        """Get latest completed evaluation ID for each prompt."""
        if not prompt_ids:
            return {}

        subq = (
            select(
                PromptEvaluation.prompt_id,
                func.max(PromptEvaluation.id).label("max_id"),
            )
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
            )
            .group_by(PromptEvaluation.prompt_id)
            .subquery()
        )

        query = (
            select(PromptEvaluation.prompt_id, PromptEvaluation.id)
            .join(
                subq,
                (PromptEvaluation.prompt_id == subq.c.prompt_id) &
                (PromptEvaluation.id == subq.c.max_id),
            )
        )

        result = await self._evals_session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def _get_group(self, group_id: int) -> PromptGroup | None:
        """Get group from prompts_db."""
        query = select(PromptGroup).where(PromptGroup.id == group_id)
        result = await self._prompts_session.execute(query)
        return result.scalar_one_or_none()

    async def _update_groups_last_run(
        self,
        group_ids: list[int],
        last_run_at: datetime,
    ) -> None:
        """Update schedule_last_run_at for all groups."""
        from sqlalchemy import update
        stmt = (
            update(PromptGroup)
            .where(PromptGroup.id.in_(group_ids))
            .values(schedule_last_run_at=last_run_at)
        )
        await self._prompts_session.execute(stmt)
