"""Reports services with dependency injection."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.evals_session import get_evals_session
from src.database.session import get_async_session
from src.billing.services import get_charge_service, ChargeService
from src.reports.services.report_service import ReportService
from src.reports.services.comparison_service import ComparisonService
from src.reports.services.brand_mention_detector import (
    BrandMentionDetector,
    BrandInput,
    get_brand_mention_detector,
)
from src.reports.services.citation_leaderboard_builder import (
    CitationLeaderboardBuilder,
    get_citation_leaderboard_builder,
)
from src.reports.services.results_enricher import (
    ReportEnricher,
    get_report_enricher,
)


def get_report_service(
    prompts_session: AsyncSession = Depends(get_async_session),
    evals_session: AsyncSession = Depends(get_evals_session),
    charge_service: ChargeService = Depends(get_charge_service),
) -> ReportService:
    """Dependency injection for ReportService."""
    return ReportService(prompts_session, evals_session, charge_service)


def get_comparison_service(
    prompts_session: AsyncSession = Depends(get_async_session),
    evals_session: AsyncSession = Depends(get_evals_session),
) -> ComparisonService:
    """Dependency injection for ComparisonService."""
    return ComparisonService(prompts_session, evals_session)


__all__ = [
    "ReportService",
    "ComparisonService",
    "get_report_service",
    "get_comparison_service",
    "BrandMentionDetector",
    "BrandInput",
    "get_brand_mention_detector",
    "CitationLeaderboardBuilder",
    "get_citation_leaderboard_builder",
    "ReportEnricher",
    "get_report_enricher",
]
