"""APScheduler configuration for daily scheduled report jobs."""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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

    from src.brightdata.services.brightdata_service import get_brightdata_service
    from src.database import get_session_maker
    from src.database.evals_session import get_evals_session_maker
    from src.daily_scheduling.services.daily_batch_orchestrator import DailyBatchOrchestrator

    prompts_session_maker = get_session_maker()
    evals_session_maker = get_evals_session_maker()

    async with prompts_session_maker() as prompts_session:
        async with evals_session_maker() as evals_session:
            brightdata_service = get_brightdata_service(evals_session)

            orchestrator = DailyBatchOrchestrator(
                prompts_session,
                evals_session,
                brightdata_service=brightdata_service,
            )

            try:
                batch_id = await orchestrator.start_daily_batch()
                if batch_id:
                    logger.info(f"Daily batch {batch_id} started successfully")
                else:
                    logger.info("No groups to process in daily batch")
            except Exception:
                logger.exception("Failed to start daily batch")


async def _check_batch_timeouts_job() -> None:
    """Job to check for timed-out batches.

    Runs every 5 minutes.
    """
    from src.database.evals_session import get_evals_session_maker
    from src.daily_scheduling.services.batch_completion_service import BatchCompletionService

    evals_session_maker = get_evals_session_maker()

    async with evals_session_maker() as evals_session:
        completion_service = BatchCompletionService(evals_session)

        try:
            count = await completion_service.check_timed_out_batches()
            if count > 0:
                logger.info(f"Triggered report generation for {count} timed-out batches")
                await evals_session.commit()
        except Exception:
            logger.exception("Failed to check timed-out batches")


async def _generate_reports_job() -> None:
    """Job to generate reports for batches in GENERATING status.

    Runs every 5 minutes.
    """
    from src.database import get_session_maker
    from src.database.evals_session import get_evals_session_maker
    from src.daily_scheduling.repositories.daily_batch_repo import DailyBatchRepository
    from src.daily_scheduling.services.batch_report_generator import BatchReportGenerator
    from src.database.evals_models import DailyBatchStatus

    prompts_session_maker = get_session_maker()
    evals_session_maker = get_evals_session_maker()

    async with prompts_session_maker() as prompts_session:
        async with evals_session_maker() as evals_session:
            from sqlalchemy import select
            from src.database.evals_models import DailyScheduleBatch

            # Find batches in GENERATING status
            query = (
                select(DailyScheduleBatch)
                .where(DailyScheduleBatch.status == DailyBatchStatus.GENERATING)
            )
            result = await evals_session.execute(query)
            batches = result.scalars().all()

            if not batches:
                return

            report_generator = BatchReportGenerator(prompts_session, evals_session)

            for batch in batches:
                try:
                    count = await report_generator.generate_all_reports(batch.id)
                    logger.info(f"Generated {count} reports for batch {batch.id}")
                    await evals_session.commit()
                    await prompts_session.commit()
                except Exception:
                    logger.exception(f"Failed to generate reports for batch {batch.id}")
                    await evals_session.rollback()
                    await prompts_session.rollback()


async def _check_report_request_timeouts_job() -> None:
    """Job to check for timed-out manual report requests.

    Runs every 5 minutes. Generates reports with available data for requests
    that have exceeded their 6-hour timeout.
    """
    from src.database import get_session_maker
    from src.database.evals_session import get_evals_session_maker
    from src.daily_scheduling.services.batch_report_generator import NoOpChargeService
    from src.reports.services.report_service import ReportService
    from src.reports.services.report_request_service import ReportRequestService

    prompts_session_maker = get_session_maker()
    evals_session_maker = get_evals_session_maker()

    async with prompts_session_maker() as prompts_session:
        async with evals_session_maker() as evals_session:
            charge_service = NoOpChargeService()
            report_service = ReportService(prompts_session, evals_session, charge_service)

            request_service = ReportRequestService(
                prompts_session,
                evals_session,
                report_service=report_service,
            )

            try:
                count = await request_service.check_timed_out_requests()
                if count > 0:
                    logger.info(f"Processed {count} timed-out report requests")
                    await evals_session.commit()
                    await prompts_session.commit()
            except Exception:
                logger.exception("Failed to check timed-out report requests")
                await evals_session.rollback()
                await prompts_session.rollback()


async def _generate_ready_reports_job() -> None:
    """Job to generate reports for requests in READY status.

    Runs every 2 minutes. Generates reports for requests where all
    BrightData batches have completed.
    """
    from src.database import get_session_maker
    from src.database.evals_session import get_evals_session_maker
    from src.daily_scheduling.services.batch_report_generator import NoOpChargeService
    from src.reports.services.report_service import ReportService
    from src.reports.services.report_request_service import ReportRequestService

    prompts_session_maker = get_session_maker()
    evals_session_maker = get_evals_session_maker()

    async with prompts_session_maker() as prompts_session:
        async with evals_session_maker() as evals_session:
            charge_service = NoOpChargeService()
            report_service = ReportService(prompts_session, evals_session, charge_service)

            request_service = ReportRequestService(
                prompts_session,
                evals_session,
                report_service=report_service,
            )

            try:
                count = await request_service.generate_ready_reports()
                if count > 0:
                    logger.info(f"Generated {count} reports for ready requests")
                    await evals_session.commit()
                    await prompts_session.commit()
            except Exception:
                logger.exception("Failed to generate ready reports")
                await evals_session.rollback()
                await prompts_session.rollback()


async def trigger_daily_batch_manually() -> int | None:
    """Manually trigger daily batch processing.

    Used for testing or manual intervention.

    Returns the batch ID if created, None if no groups to process.
    """
    from src.brightdata.services.brightdata_service import get_brightdata_service
    from src.database import get_session_maker
    from src.database.evals_session import get_evals_session_maker
    from src.daily_scheduling.services.daily_batch_orchestrator import DailyBatchOrchestrator

    prompts_session_maker = get_session_maker()
    evals_session_maker = get_evals_session_maker()

    async with prompts_session_maker() as prompts_session:
        async with evals_session_maker() as evals_session:
            brightdata_service = get_brightdata_service(evals_session)

            orchestrator = DailyBatchOrchestrator(
                prompts_session,
                evals_session,
                brightdata_service=brightdata_service,
            )

            return await orchestrator.start_daily_batch()
