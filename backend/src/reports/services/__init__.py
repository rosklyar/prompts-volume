"""Reports services with dependency injection."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.billing.services import get_charge_service, ChargeService
from src.reports.services.report_service import ReportService
from src.reports.services.comparison_service import ComparisonService


def get_report_service(
    session: AsyncSession = Depends(get_async_session),
    charge_service: ChargeService = Depends(get_charge_service),
) -> ReportService:
    """Dependency injection for ReportService."""
    return ReportService(session, charge_service)


def get_comparison_service(
    session: AsyncSession = Depends(get_async_session),
) -> ComparisonService:
    """Dependency injection for ComparisonService."""
    return ComparisonService(session)


__all__ = [
    "ReportService",
    "ComparisonService",
    "get_report_service",
    "get_comparison_service",
]
