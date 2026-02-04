"""Cleaner for evals_db tables."""

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.user_deletion.protocol import CleanupResult
from src.database.evals_models import (
    BrightDataBatch,
    ConsumedEvaluation,
    DailyBatchGroupResult,
    GroupReport,
    ReportRequest,
)


class EvalsDbCleaner:
    """Cleans user data from evals_db.

    Note: PromptEvaluation (answers) are NOT deleted - they're reusable across users.
    """

    async def cleanup(self, user_id: str, session: AsyncSession) -> CleanupResult:
        """Delete all user-related data from evals_db.

        Deletes:
        - ConsumedEvaluation
        - GroupReport (cascades to group_report_items via FK)
        - ReportRequest
        - BrightDataBatch
        - DailyBatchGroupResult

        Keeps:
        - PromptEvaluation (shared answers)
        """
        deleted: dict[str, int] = {}

        # Delete consumed evaluations
        consumed_result = await session.execute(
            delete(ConsumedEvaluation).where(ConsumedEvaluation.user_id == user_id)
        )
        deleted["consumed_evaluations"] = consumed_result.rowcount

        # Delete group reports (items cascade automatically)
        reports_result = await session.execute(
            delete(GroupReport).where(GroupReport.user_id == user_id)
        )
        deleted["group_reports"] = reports_result.rowcount

        # Delete report requests
        requests_result = await session.execute(
            delete(ReportRequest).where(ReportRequest.user_id == user_id)
        )
        deleted["report_requests"] = requests_result.rowcount

        # Delete BrightData batches
        batches_result = await session.execute(
            delete(BrightDataBatch).where(BrightDataBatch.user_id == user_id)
        )
        deleted["brightdata_batches"] = batches_result.rowcount

        # Delete daily batch group results
        daily_results = await session.execute(
            delete(DailyBatchGroupResult).where(DailyBatchGroupResult.user_id == user_id)
        )
        deleted["daily_batch_group_results"] = daily_results.rowcount

        return CleanupResult(database="evals_db", deleted=deleted, orphaned={})
