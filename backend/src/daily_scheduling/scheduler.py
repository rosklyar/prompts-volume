"""APScheduler configuration for daily scheduled report jobs."""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from src.database import get_session_maker
from src.database.evals_models import DailyBatchStatus, DailyScheduleBatch
from src.database.evals_session import get_evals_session_maker
from src.database.users_session import get_users_session_maker
from src.daily_scheduling.service_factory import (
    create_batch_completion_service,
    create_batch_report_generator,
    create_chunk_retry_service,
    create_daily_batch_orchestrator,
    create_report_request_service,
)
from src.daily_scheduling.session_context import multi_session_context

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def setup_scheduler() -> None:
    """Configure and start the scheduler.

    Called on application startup.
    """
    scheduler = get_scheduler()

    # Job 1: Daily batch trigger at 6 AM UTC
    scheduler.add_job(
        _start_daily_batch_job,
        trigger=CronTrigger(hour=6, minute=0, timezone="UTC"),
        id="daily_batch_trigger",
        replace_existing=True,
        name="Daily scheduled batch trigger",
    )

    # Job 2: Timeout checker every 5 minutes
    scheduler.add_job(
        _check_batch_timeouts_job,
        trigger=IntervalTrigger(minutes=5),
        id="batch_timeout_checker",
        replace_existing=True,
        name="Batch timeout checker",
    )

    # Job 3: Generate reports for completed batches every 5 minutes
    scheduler.add_job(
        _generate_reports_job,
        trigger=IntervalTrigger(minutes=5),
        id="batch_report_generator",
        replace_existing=True,
        name="Batch report generator",
    )

    # Job 4: Check for timed-out report requests every 5 minutes
    scheduler.add_job(
        _check_report_request_timeouts_job,
        trigger=IntervalTrigger(minutes=5),
        id="report_request_timeout_checker",
        replace_existing=True,
        name="Report request timeout checker",
    )

    # Job 5: Generate reports for ready requests every 2 minutes
    scheduler.add_job(
        _generate_ready_reports_job,
        trigger=IntervalTrigger(minutes=2),
        id="ready_reports_generator",
        replace_existing=True,
        name="Ready reports generator",
    )

    # Job 6: Check chunk timeouts and retry every 15 minutes
    scheduler.add_job(
        _check_chunk_timeouts_and_retry_job,
        trigger=IntervalTrigger(minutes=15),
        id="chunk_timeout_retry_checker",
        replace_existing=True,
        name="Chunk timeout and retry checker",
    )

    # Job 7: Clean up stale geo audits every 10 minutes
    scheduler.add_job(
        _cleanup_stale_geo_audits_job,
        trigger=IntervalTrigger(minutes=10),
        id="stale_geo_audit_cleanup",
        replace_existing=True,
        name="Stale GEO audit cleanup",
    )

    scheduler.start()
    logger.info("Daily scheduling jobs started")


async def shutdown_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    scheduler = get_scheduler()
    scheduler.shutdown(wait=True)
    logger.info("Daily scheduling jobs stopped")


async def _start_daily_batch_job() -> None:
    """Job to start daily batch processing.

    Runs at 6 AM UTC.
    """
    logger.info("Starting daily batch job...")

    async with multi_session_context(
        prompts_maker=get_session_maker(),
        evals_maker=get_evals_session_maker(),
        users_maker=get_users_session_maker(),
    ) as sessions:
        orchestrator = create_daily_batch_orchestrator(sessions)
        try:
            batch_id = await orchestrator.start_daily_batch()
            if batch_id:
                logger.info(f"Daily batch {batch_id} started successfully")
                await sessions.users.commit()
            else:
                logger.info("No groups to process in daily batch")
        except Exception:
            logger.exception("Failed to start daily batch")
            await sessions.users.rollback()


async def _check_batch_timeouts_job() -> None:
    """Job to check for timed-out batches.

    Runs every 5 minutes.
    """
    async with multi_session_context(
        prompts_maker=get_session_maker(),
        evals_maker=get_evals_session_maker(),
        users_maker=get_users_session_maker(),
    ) as sessions:
        completion_service = create_batch_completion_service(sessions)
        try:
            count = await completion_service.check_timed_out_batches()
            if count > 0:
                logger.info(f"Triggered report generation for {count} timed-out batches")
                await sessions.evals.commit()
        except Exception:
            logger.exception("Failed to check timed-out batches")


async def _generate_reports_job() -> None:
    """Job to generate reports for batches in GENERATING status.

    Runs every 5 minutes.
    """
    async with multi_session_context(
        prompts_maker=get_session_maker(),
        evals_maker=get_evals_session_maker(),
        users_maker=get_users_session_maker(),
    ) as sessions:
        # Find batches in GENERATING status
        query = select(DailyScheduleBatch).where(
            DailyScheduleBatch.status == DailyBatchStatus.GENERATING
        )
        result = await sessions.evals.execute(query)
        batches = result.scalars().all()

        if not batches:
            return

        report_generator = create_batch_report_generator(sessions)

        for batch in batches:
            try:
                count = await report_generator.generate_all_reports(batch.id)
                logger.info(f"Generated {count} reports for batch {batch.id}")
                await sessions.commit_all()
            except Exception:
                logger.exception(f"Failed to generate reports for batch {batch.id}")
                await sessions.rollback_all()


async def _check_report_request_timeouts_job() -> None:
    """Job to check for timed-out manual report requests.

    Runs every 5 minutes. Generates reports with available data for requests
    that have exceeded their 6-hour timeout.
    """
    async with multi_session_context(
        prompts_maker=get_session_maker(),
        evals_maker=get_evals_session_maker(),
        users_maker=get_users_session_maker(),
    ) as sessions:
        request_service = create_report_request_service(sessions)
        try:
            count = await request_service.check_timed_out_requests()
            if count > 0:
                logger.info(f"Processed {count} timed-out report requests")
                await sessions.commit_all()
        except Exception:
            logger.exception("Failed to check timed-out report requests")
            await sessions.rollback_all()


async def _generate_ready_reports_job() -> None:
    """Job to generate reports for requests in READY status.

    Runs every 2 minutes. Generates reports for requests where all
    BrightData batches have completed.
    """
    async with multi_session_context(
        prompts_maker=get_session_maker(),
        evals_maker=get_evals_session_maker(),
        users_maker=get_users_session_maker(),
    ) as sessions:
        request_service = create_report_request_service(sessions)
        try:
            count = await request_service.generate_ready_reports()
            if count > 0:
                logger.info(f"Generated {count} reports for ready requests")
                await sessions.commit_all()
        except Exception:
            logger.exception("Failed to generate ready reports")
            await sessions.rollback_all()


async def _check_chunk_timeouts_and_retry_job() -> None:
    """Job to check for timed-out chunks and retry them.

    Runs every 15 minutes. Checks for PENDING BrightData batches that have
    exceeded the chunk timeout (2 hours) and either retries them or marks
    them as FAILED if max retries exceeded.
    """
    async with multi_session_context(
        prompts_maker=get_session_maker(),
        evals_maker=get_evals_session_maker(),
        users_maker=get_users_session_maker(),
    ) as sessions:
        retry_service = create_chunk_retry_service(sessions)
        try:
            retried, failed = await retry_service.check_and_retry_timed_out_chunks()
            if retried > 0 or failed > 0:
                logger.info(
                    f"Chunk timeout check: {retried} retried, {failed} marked failed"
                )
        except Exception:
            logger.exception("Failed to check chunk timeouts")


async def _cleanup_stale_geo_audits_job() -> None:
    """Mark geo audits stuck in non-terminal status for >30 minutes as failed.

    Runs every 10 minutes.
    """
    from src.database.users_models import GeoAuditResult

    session_maker = get_users_session_maker()
    async with session_maker() as session:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
            stuck_statuses = ("pending", "discovering", "auditing")
            query = (
                select(GeoAuditResult)
                .where(
                    GeoAuditResult.status.in_(stuck_statuses),
                    GeoAuditResult.created_at < cutoff,
                )
            )
            result = await session.execute(query)
            stale = result.scalars().all()
            for audit in stale:
                audit.status = "failed"
                audit.error_message = "Audit timed out after 30 minutes"
            if stale:
                await session.commit()
                logger.info("Marked %d stale geo audits as failed", len(stale))
        except Exception:
            logger.exception("Failed to clean up stale geo audits")
            await session.rollback()


async def trigger_daily_batch_manually() -> int | None:
    """Manually trigger daily batch processing.

    Used for testing or manual intervention.

    Returns the batch ID if created, None if no groups to process.
    """
    async with multi_session_context(
        prompts_maker=get_session_maker(),
        evals_maker=get_evals_session_maker(),
        users_maker=get_users_session_maker(),
    ) as sessions:
        orchestrator = create_daily_batch_orchestrator(sessions)
        batch_id = await orchestrator.start_daily_batch()
        if batch_id:
            await sessions.users.commit()
        return batch_id
