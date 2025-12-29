"""Service for generating and managing reports."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.billing.services.charge_service import ChargeService
from src.database.evals_models import (
    EvaluationStatus,
    GroupReport,
    GroupReportItem,
    PromptEvaluation,
    ReportItemStatus,
)
from src.database.models import (
    Prompt,
    PromptGroup,
    PromptGroupBinding,
)
from src.reports.services.comparison_service import ComparisonService


class ReportService:
    """Service for generating and managing prompt group reports.

    Uses dual session pattern:
    - prompts_session: for PromptGroup, Prompt, PromptGroupBinding (prompts_db)
    - evals_session: for GroupReport, GroupReportItem, PromptEvaluation (evals_db)
    """

    def __init__(
        self,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
        charge_service: ChargeService,
    ):
        self._prompts_session = prompts_session
        self._evals_session = evals_session
        self._charge_service = charge_service
        self._comparison_service = ComparisonService(prompts_session, evals_session)

    async def _get_prompts_by_ids(self, prompt_ids: list[int]) -> dict[int, Prompt]:
        """Fetch prompts from prompts_db, returns dict keyed by prompt_id."""
        if not prompt_ids:
            return {}
        result = await self._prompts_session.execute(
            select(Prompt).where(Prompt.id.in_(prompt_ids))
        )
        return {p.id: p for p in result.scalars().all()}

    async def preview_report(
        self,
        group_id: int,
        user_id: str,
        price_per_evaluation: Decimal,
    ) -> dict:
        """Preview what a report generation would look like."""
        # Get prompt IDs in group
        prompt_ids = await self._comparison_service.get_prompt_ids_in_group(group_id)
        total_prompts = len(prompt_ids)

        # Get prompts with evaluations
        prompts_with_data = await self._comparison_service.get_prompts_with_evaluations(
            prompt_ids
        )

        # Get all evaluation IDs
        evaluation_ids = await self._comparison_service.get_evaluation_ids_for_prompts(
            prompt_ids
        )

        # Get consumed evaluation IDs
        consumed = await self._comparison_service.get_consumed_evaluation_ids(
            user_id, evaluation_ids
        )

        # Calculate fresh count
        fresh_count = len(evaluation_ids) - len(consumed)
        estimated_cost = price_per_evaluation * fresh_count

        # Get user balance (through charge service preview)
        if evaluation_ids:
            preview = await self._charge_service.preview_charge(user_id, evaluation_ids)
            user_balance = preview["user_balance"]
            affordable_count = preview["affordable_count"]
        else:
            user_balance = Decimal("0")
            affordable_count = 0

        return {
            "group_id": group_id,
            "total_prompts": total_prompts,
            "prompts_with_data": len(prompts_with_data),
            "prompts_awaiting": total_prompts - len(prompts_with_data),
            "fresh_evaluations": fresh_count,
            "already_consumed": len(consumed),
            "estimated_cost": estimated_cost,
            "user_balance": user_balance,
            "affordable_count": affordable_count,
            "needs_top_up": fresh_count > affordable_count,
        }

    async def generate_report(
        self,
        group_id: int,
        user_id: str,
        title: str | None = None,
        include_previous: bool = True,
    ) -> GroupReport:
        """Generate a report for a prompt group.

        1. Gets all prompts in the group
        2. Gets all completed evaluations for those prompts
        3. Charges for fresh (not consumed) evaluations
        4. Creates report snapshot with all items
        """
        # Get group to verify it exists (from prompts_db)
        group_query = select(PromptGroup).where(PromptGroup.id == group_id)
        group_result = await self._prompts_session.execute(group_query)
        group = group_result.scalar_one_or_none()
        if not group:
            raise ValueError(f"Group {group_id} not found")

        # Get prompts in group with their texts (from prompts_db)
        prompts_query = (
            select(Prompt)
            .join(PromptGroupBinding, Prompt.id == PromptGroupBinding.prompt_id)
            .where(PromptGroupBinding.group_id == group_id)
        )
        prompts_result = await self._prompts_session.execute(prompts_query)
        prompts = list(prompts_result.scalars().all())
        prompt_ids = [p.id for p in prompts]

        if not prompt_ids:
            # Empty group - create empty report
            report = GroupReport(
                group_id=group_id,
                user_id=user_id,
                title=title,
                total_prompts=0,
                prompts_with_data=0,
                prompts_awaiting=0,
                total_evaluations_loaded=0,
                total_cost=Decimal("0"),
            )
            self._evals_session.add(report)
            await self._evals_session.flush()
            return report

        # Get completed evaluations for these prompts (from evals_db)
        evals_query = (
            select(PromptEvaluation)
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
            )
        )
        evals_result = await self._evals_session.execute(evals_query)
        evaluations = list(evals_result.scalars().all())
        evaluation_ids = [e.id for e in evaluations]

        # Get consumed evaluation IDs
        consumed_ids = await self._comparison_service.get_consumed_evaluation_ids(
            user_id, evaluation_ids
        )

        # Fresh evaluations = not consumed
        fresh_eval_ids = [eid for eid in evaluation_ids if eid not in consumed_ids]

        # Charge for fresh evaluations
        charge_result = None
        if fresh_eval_ids:
            charge_result = await self._charge_service.charge_for_evaluations(
                user_id=user_id,
                evaluation_ids=fresh_eval_ids,
            )

        # Build prompt_id -> evaluations map
        prompt_evaluations: dict[int, list[PromptEvaluation]] = {}
        for e in evaluations:
            if e.prompt_id not in prompt_evaluations:
                prompt_evaluations[e.prompt_id] = []
            prompt_evaluations[e.prompt_id].append(e)

        # Calculate stats
        prompts_with_data = len(prompt_evaluations)
        prompts_awaiting = len(prompt_ids) - prompts_with_data
        total_evaluations_loaded = len(evaluations) if include_previous else len(
            charge_result.charged_evaluation_ids if charge_result else []
        )
        total_cost = charge_result.total_charged if charge_result else Decimal("0")

        # Create report (in evals_db)
        report = GroupReport(
            group_id=group_id,
            user_id=user_id,
            title=title,
            total_prompts=len(prompt_ids),
            prompts_with_data=prompts_with_data,
            prompts_awaiting=prompts_awaiting,
            total_evaluations_loaded=total_evaluations_loaded,
            total_cost=total_cost,
        )
        self._evals_session.add(report)
        await self._evals_session.flush()

        # Create report items (in evals_db)
        charged_eval_ids = set(
            charge_result.charged_evaluation_ids if charge_result else []
        )

        for prompt in prompts:
            evals_for_prompt = prompt_evaluations.get(prompt.id, [])

            if not evals_for_prompt:
                # No evaluations - awaiting
                item = GroupReportItem(
                    report_id=report.id,
                    prompt_id=prompt.id,
                    evaluation_id=None,
                    status=ReportItemStatus.AWAITING,
                    is_fresh=False,
                    amount_charged=None,
                )
                self._evals_session.add(item)
            else:
                # Has evaluations - include them
                for evaluation in evals_for_prompt:
                    is_fresh = evaluation.id in charged_eval_ids
                    item = GroupReportItem(
                        report_id=report.id,
                        prompt_id=prompt.id,
                        evaluation_id=evaluation.id,
                        status=ReportItemStatus.INCLUDED,
                        is_fresh=is_fresh,
                        amount_charged=(
                            charge_result.total_charged / len(charged_eval_ids)
                            if is_fresh and charged_eval_ids
                            else None
                        ),
                    )
                    self._evals_session.add(item)

        await self._evals_session.flush()
        return report

    async def get_report(self, report_id: int, user_id: str) -> dict | None:
        """Get a report by ID with all items.

        Returns dict with report and items (prompts fetched separately due to cross-db).
        """
        # Get report with items (from evals_db)
        query = (
            select(GroupReport)
            .where(
                GroupReport.id == report_id,
                GroupReport.user_id == user_id,
            )
            .options(
                selectinload(GroupReport.items).selectinload(GroupReportItem.evaluation),
            )
        )
        result = await self._evals_session.execute(query)
        report = result.scalar_one_or_none()

        if not report:
            return None

        # Fetch prompts for items (from prompts_db)
        prompt_ids = [item.prompt_id for item in report.items]
        prompts_map = await self._get_prompts_by_ids(prompt_ids)

        return {
            "report": report,
            "prompts_map": prompts_map,
        }

    async def list_reports(
        self,
        group_id: int,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[GroupReport], int]:
        """List reports for a group."""
        # Count total (in evals_db)
        count_query = select(func.count(GroupReport.id)).where(
            GroupReport.group_id == group_id,
            GroupReport.user_id == user_id,
        )
        count_result = await self._evals_session.execute(count_query)
        total = count_result.scalar() or 0

        # Get reports (from evals_db)
        query = (
            select(GroupReport)
            .where(
                GroupReport.group_id == group_id,
                GroupReport.user_id == user_id,
            )
            .order_by(GroupReport.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._evals_session.execute(query)
        reports = list(result.scalars().all())

        return reports, total

    async def get_latest_report(
        self, group_id: int, user_id: str
    ) -> GroupReport | None:
        """Get the most recent report for a group."""
        return await self._comparison_service.get_latest_report(group_id, user_id)
