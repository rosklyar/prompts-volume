"""Reports services with dependency injection."""

from decimal import Decimal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database.evals_session import get_evals_session
from src.database.session import get_async_session
from src.billing.services import get_charge_service, ChargeService
from src.reports.services.report_service import ReportService
from src.reports.services.comparison_service import ComparisonService
from src.reports.services.freshness_analyzer import FreshnessAnalyzerService
from src.reports.services.selection_analyzer import (
    SelectionAnalyzerService,
    MostRecentSelectionStrategy,
)
from src.reports.services.selection_pricing import SelectionPricingService
from src.reports.services.selection_validator import SelectionValidatorService
from src.reports.services.brand_mention_detector import (
    BrandMentionDetector,
    BrandInput,
    get_brand_mention_detector,
)
from src.reports.services.citation_leaderboard_builder import (
    CitationLeaderboardBuilder,
    get_citation_leaderboard_builder,
)
from src.reports.services.domain_mention_detector import (
    DomainInput,
    DomainMentionDetector,
    get_domain_mention_detector,
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


def get_freshness_analyzer(
    prompts_session: AsyncSession = Depends(get_async_session),
    evals_session: AsyncSession = Depends(get_evals_session),
) -> FreshnessAnalyzerService:
    """Dependency injection for FreshnessAnalyzerService."""
    return FreshnessAnalyzerService(
        prompts_session,
        evals_session,
        in_progress_estimate=settings.comparison_in_progress_estimate,
        next_refresh_estimate=settings.comparison_next_refresh_estimate,
    )


def get_selection_analyzer(
    prompts_session: AsyncSession = Depends(get_async_session),
    evals_session: AsyncSession = Depends(get_evals_session),
) -> SelectionAnalyzerService:
    """Dependency injection for SelectionAnalyzerService."""
    return SelectionAnalyzerService(
        prompts_session,
        evals_session,
        price_per_evaluation=Decimal(str(settings.billing_price_per_evaluation)),
        selection_strategy=MostRecentSelectionStrategy(),
    )


def get_selection_pricing(
    evals_session: AsyncSession = Depends(get_evals_session),
) -> SelectionPricingService:
    """Dependency injection for SelectionPricingService."""
    return SelectionPricingService(
        evals_session,
        price_per_evaluation=Decimal(str(settings.billing_price_per_evaluation)),
    )


def get_selection_validator() -> SelectionValidatorService:
    """Dependency injection for SelectionValidatorService."""
    return SelectionValidatorService()


__all__ = [
    "ReportService",
    "ComparisonService",
    "FreshnessAnalyzerService",
    "SelectionAnalyzerService",
    "SelectionPricingService",
    "SelectionValidatorService",
    "get_report_service",
    "get_comparison_service",
    "get_freshness_analyzer",
    "get_selection_analyzer",
    "get_selection_pricing",
    "get_selection_validator",
    "BrandMentionDetector",
    "BrandInput",
    "get_brand_mention_detector",
    "CitationLeaderboardBuilder",
    "get_citation_leaderboard_builder",
    "DomainInput",
    "DomainMentionDetector",
    "get_domain_mention_detector",
    "ReportEnricher",
    "get_report_enricher",
]
