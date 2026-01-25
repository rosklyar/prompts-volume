"""Service for unified report request handling (manual + scheduled)."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.brightdata.services.brightdata_service import BrightDataService
from src.database.evals_models import (
    EvaluationStatus,
    PromptEvaluation,
    ReportRequest,
    ReportRequestStatus,
)
from src.database.models import Prompt, PromptGroup, PromptGroupBinding
from src.reports.models.api_models import PromptSelection
from src.reports.repositories.report_request_repo import ReportRequestRepository
from src.reports.services.report_service import DuplicateReportError, ReportService

logger = logging.getLogger(__name__)

# Same timeout as scheduled batches
TIMEOUT_HOURS = 6

# Freshness threshold in hours
FRESH_THRESHOLD_HOURS = 24


class ReportRequestService:
    """Service for creating and managing report requests.

    Handles the full lifecycle:
    1. Create request (record fresh prompts, trigger BrightData for stale/absent)
    2. Check completion (called from webhook or timeout checker)
    3. Generate report when ready
    """

    def __init__(
        self,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
        *,
        brightdata_service: BrightDataService | None = None,
        report_service: ReportService | None = None,
        repo: ReportRequestRepository | None = None,
    ) -> None:
        self._prompts_session = prompts_session
        self._evals_session = evals_session
        self._brightdata_service = brightdata_service
        self._report_service = report_service
        self._repo = repo or ReportRequestRepository(evals_session)

    async def create_request(
        self,
        group_id: int,
        user_id: str,
        assistant_id: int,
    ) -> ReportRequest:
        """Create a new report request for a group.

        1. Analyzes all prompts in the group
        2. Records fresh prompt -> evaluation mappings
        3. Triggers BrightData for stale/absent prompts
        4. Returns the created request

        Returns:
            The created ReportRequest
        """
        now = datetime.now(timezone.utc)
        timeout_at = now + timedelta(hours=TIMEOUT_HOURS)

        # Get group with country info for BrightData
        group_result = await self._prompts_session.execute(
            select(PromptGroup)
            .where(PromptGroup.id == group_id)
            .options(selectinload(PromptGroup.country))
        )
        group = group_result.scalar_one_or_none()

        if not group:
            raise ValueError(f"Group {group_id} not found")

        if not group.country:
            raise ValueError(f"Group {group_id} has no country configured")

        country_id = group.country_id
        country_iso_code = group.country.iso_code

        # Get prompt IDs in the group
        bindings_result = await self._prompts_session.execute(
            select(PromptGroupBinding.prompt_id)
            .where(PromptGroupBinding.group_id == group_id)
        )
        prompt_ids = list(bindings_result.scalars().all())

        if not prompt_ids:
            # Empty group - create request with no BrightData trigger
            request = await self._repo.create(
                group_id=group_id,
                user_id=user_id,
                assistant_id=assistant_id,
                batch_ids=[],
                fresh_prompt_selections=None,
                total_prompts=0,
                prompts_fresh_at_request=0,
                prompts_requested=0,
                timeout_at=timeout_at,
            )
            # Move directly to READY since nothing to wait for
            await self._repo.update_status(request.id, ReportRequestStatus.READY)
            return request

        # Get prompts for BrightData
        prompts_result = await self._prompts_session.execute(
            select(Prompt).where(Prompt.id.in_(prompt_ids))
        )
        prompts_map = {p.id: p.prompt_text for p in prompts_result.scalars().all()}

        # Get latest completed evaluations for each prompt
        evals_result = await self._evals_session.execute(
            select(PromptEvaluation)
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.assistant_id == assistant_id,
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
            )
            .order_by(PromptEvaluation.completed_at.desc())
        )
        all_evals = list(evals_result.scalars().all())

        # Get latest eval per prompt
        latest_eval_by_prompt: dict[int, PromptEvaluation] = {}
        for e in all_evals:
            if e.prompt_id not in latest_eval_by_prompt:
                latest_eval_by_prompt[e.prompt_id] = e

        # Categorize prompts
        fresh_selections: dict[int, int] = {}  # prompt_id -> eval_id
        stale_or_absent_prompt_ids: list[int] = []

        fresh_threshold = now - timedelta(hours=FRESH_THRESHOLD_HOURS)

        for prompt_id in prompt_ids:
            latest_eval = latest_eval_by_prompt.get(prompt_id)
            if latest_eval is None:
                # Absent
                stale_or_absent_prompt_ids.append(prompt_id)
            elif latest_eval.completed_at >= fresh_threshold:
                # Fresh
                fresh_selections[prompt_id] = latest_eval.id
            else:
                # Stale
                stale_or_absent_prompt_ids.append(prompt_id)

        # Trigger BrightData for stale/absent prompts (chunked)
        batch_ids: list[str] = []
        if stale_or_absent_prompt_ids and self._brightdata_service:
            prompts_to_trigger = {
                pid: prompts_map[pid]
                for pid in stale_or_absent_prompt_ids
                if pid in prompts_map
            }
            batch_ids = await self._brightdata_service.trigger_batches_chunked(
                prompts=prompts_to_trigger,
                user_id=user_id,
                country_id=country_id,
                country_iso_code=country_iso_code,
                assistant_id=assistant_id,
            )

        # Create request
        request = await self._repo.create(
            group_id=group_id,
            user_id=user_id,
            assistant_id=assistant_id,
            batch_ids=batch_ids,
            fresh_prompt_selections=fresh_selections if fresh_selections else None,
            total_prompts=len(prompt_ids),
            prompts_fresh_at_request=len(fresh_selections),
            prompts_requested=len(stale_or_absent_prompt_ids),
            timeout_at=timeout_at,
        )

        # If no BrightData triggered, move to READY
        if not batch_ids:
            await self._repo.update_status(request.id, ReportRequestStatus.READY)

        return request

    async def on_brightdata_completed(self, brightdata_batch_id: str) -> bool:
        """Called when a BrightData batch webhook is received.

        Checks if this batch is part of a report request and if all batches complete.

        Returns True if the request is now ready for report generation.
        """
        request = await self._repo.find_by_brightdata_id(brightdata_batch_id)
        if request is None:
            return False

        return await self._check_and_mark_ready(request.id)

    async def check_timed_out_requests(self) -> int:
        """Check for timed-out requests and mark them for report generation.

        Returns count of requests that timed out.
        """
        now = datetime.now(timezone.utc)
        timed_out = await self._repo.get_timed_out_requests(now)

        count = 0
        for request in timed_out:
            try:
                # Mark as timed out but still generate report
                await self._repo.update_status(
                    request.id,
                    ReportRequestStatus.TIMED_OUT,
                )
                # Generate report with available data
                await self._generate_report_for_request(request.id)
                count += 1
            except Exception:
                logger.exception(f"Failed to process timed-out request {request.id}")

        return count

    async def generate_ready_reports(self) -> int:
        """Generate reports for requests in READY status.

        Returns count of reports generated.
        """
        ready_requests = await self._repo.get_ready_requests()

        count = 0
        for request in ready_requests:
            try:
                await self._generate_report_for_request(request.id)
                count += 1
            except Exception:
                logger.exception(f"Failed to generate report for request {request.id}")

        return count

    async def _check_and_mark_ready(self, request_id: int) -> bool:
        """Check if request is ready and mark it if so."""
        request = await self._repo.get_by_id(request_id)
        if request is None or request.status != ReportRequestStatus.AWAITING:
            return False

        # Check if all BrightData batches are complete
        all_complete = await self._repo.are_all_brightdata_batches_complete(
            list(request.batch_ids)
        )

        if not all_complete:
            return False

        # Mark as ready
        await self._repo.update_status(request_id, ReportRequestStatus.READY)
        await self._evals_session.commit()

        logger.info(f"Report request {request_id} is ready for report generation")
        return True

    async def _generate_report_for_request(self, request_id: int) -> None:
        """Generate report for a request."""
        if self._report_service is None:
            logger.warning("Report service not configured, skipping report generation")
            return

        request = await self._repo.get_by_id(request_id)
        if request is None:
            return

        # Mark as generating
        await self._repo.update_status(request_id, ReportRequestStatus.GENERATING)
        await self._evals_session.commit()

        try:
            # Get the group for brand/competitors snapshot
            from src.database.models import PromptGroup
            group_result = await self._prompts_session.execute(
                select(PromptGroup).where(PromptGroup.id == request.group_id)
            )
            group = group_result.scalar_one_or_none()

            # Build selections from fresh + newly completed evaluations
            selections = await self._build_final_selections(request)

            # Generate report
            report = await self._report_service.generate_report_with_selections(
                group_id=request.group_id,
                user_id=request.user_id,
                selections=selections,
                title=None,  # Auto-generated
                brand_snapshot=group.brand if group else None,
                competitors_snapshot=group.competitors if group else None,
                assistant_id=request.assistant_id,
            )

            # Mark as completed
            await self._repo.update_status(
                request_id,
                ReportRequestStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
                report_id=report.id,
            )
            await self._evals_session.commit()
            await self._prompts_session.commit()

            logger.info(f"Generated report {report.id} for request {request_id}")

        except DuplicateReportError:
            # Report would be identical to the latest - mark as completed without new report
            logger.info(
                f"Report request {request_id} skipped: would be duplicate of latest report"
            )
            await self._repo.update_status(
                request_id,
                ReportRequestStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
                report_id=None,  # No new report created
            )
            await self._evals_session.commit()

        except Exception:
            logger.exception(f"Failed to generate report for request {request_id}")
            # Revert to READY so it can be retried
            await self._repo.update_status(request_id, ReportRequestStatus.READY)
            await self._evals_session.commit()
            raise

    async def _build_final_selections(
        self,
        request: ReportRequest,
    ) -> list[PromptSelection]:
        """Build final selections combining fresh prompts and newly completed ones."""
        # Get all prompt IDs in group
        bindings_result = await self._prompts_session.execute(
            select(PromptGroupBinding.prompt_id)
            .where(PromptGroupBinding.group_id == request.group_id)
        )
        prompt_ids = list(bindings_result.scalars().all())

        # Start with fresh selections from request time
        selection_map: dict[int, int | None] = {}
        if request.fresh_prompt_selections:
            for prompt_id_str, eval_id in request.fresh_prompt_selections.items():
                selection_map[int(prompt_id_str)] = eval_id

        # Get latest evaluations for prompts that weren't fresh
        prompts_needing_eval = [pid for pid in prompt_ids if pid not in selection_map]

        if prompts_needing_eval:
            evals_result = await self._evals_session.execute(
                select(PromptEvaluation)
                .where(
                    PromptEvaluation.prompt_id.in_(prompts_needing_eval),
                    PromptEvaluation.assistant_id == request.assistant_id,
                    PromptEvaluation.status == EvaluationStatus.COMPLETED,
                )
                .order_by(PromptEvaluation.completed_at.desc())
            )
            all_evals = list(evals_result.scalars().all())

            # Get latest eval per prompt
            for e in all_evals:
                if e.prompt_id not in selection_map:
                    selection_map[e.prompt_id] = e.id

        # Build final selections
        selections: list[PromptSelection] = []
        for prompt_id in prompt_ids:
            eval_id = selection_map.get(prompt_id)
            selections.append(PromptSelection(
                prompt_id=prompt_id,
                evaluation_id=eval_id,
            ))

        return selections

    async def get_pending_request(
        self,
        group_id: int,
        user_id: str,
    ) -> ReportRequest | None:
        """Get the pending report request for a group, if any."""
        return await self._repo.get_pending_for_group(group_id, user_id)

    async def cancel_request(self, request_id: int, user_id: str) -> bool:
        """Cancel a pending report request.

        Returns True if cancelled, False if not found or already completed.
        """
        request = await self._repo.get_by_id(request_id)
        if request is None or request.user_id != user_id:
            return False

        return await self._repo.cancel_request(request_id)
