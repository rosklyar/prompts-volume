"""Factory functions for creating daily scheduling services.

Centralizes service creation with proper dependency injection.
All imports are at the top of the file for clarity and performance.
"""

from src.billing.services import build_charge_service
from src.brightdata.service_factory import create_brightdata_service
from src.daily_scheduling.services.batch_completion_service import BatchCompletionService
from src.daily_scheduling.services.batch_report_generator import BatchReportGenerator
from src.daily_scheduling.services.daily_batch_orchestrator import DailyBatchOrchestrator
from src.daily_scheduling.session_context import SessionSet
from src.reports.services.report_request_service import ReportRequestService
from src.reports.services.report_service import ReportService


def create_daily_batch_orchestrator(sessions: SessionSet) -> DailyBatchOrchestrator:
    """Create orchestrator with all dependencies."""
    charge_service = build_charge_service(sessions.evals, sessions.users)
    brightdata_service = create_brightdata_service(sessions.evals)
    return DailyBatchOrchestrator(
        sessions.prompts,
        sessions.evals,
        charge_service=charge_service,
        brightdata_service=brightdata_service,
    )


def create_batch_completion_service(sessions: SessionSet) -> BatchCompletionService:
    """Create batch completion service."""
    return BatchCompletionService(sessions.evals)


def create_batch_report_generator(sessions: SessionSet) -> BatchReportGenerator:
    """Create batch report generator with all dependencies."""
    charge_service = build_charge_service(sessions.evals, sessions.users)
    return BatchReportGenerator(
        sessions.prompts,
        sessions.evals,
        charge_service=charge_service,
    )


def create_report_request_service(sessions: SessionSet) -> ReportRequestService:
    """Create report request service with all dependencies."""
    charge_service = build_charge_service(sessions.evals, sessions.users)
    report_service = ReportService(sessions.prompts, sessions.evals, charge_service)
    return ReportRequestService(
        sessions.prompts,
        sessions.evals,
        report_service=report_service,
    )
