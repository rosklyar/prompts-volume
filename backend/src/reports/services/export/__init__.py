"""Export services with dependency injection."""

from fastapi import Depends

from src.reports.services.export.export_service import ReportExportService
from src.reports.services.export.json_formatter import JsonExportFormatter
from src.reports.services.statistics.brand_visibility import BrandVisibilityCalculator
from src.reports.services.statistics.citation_domains import CitationDomainCalculator
from src.reports.services.statistics.domain_mentions import DomainMentionCalculator


def get_brand_visibility_calculator() -> BrandVisibilityCalculator:
    return BrandVisibilityCalculator()


def get_domain_mention_calculator() -> DomainMentionCalculator:
    return DomainMentionCalculator()


def get_citation_domain_calculator() -> CitationDomainCalculator:
    return CitationDomainCalculator()


def get_report_export_service(
    visibility_calc: BrandVisibilityCalculator = Depends(
        get_brand_visibility_calculator
    ),
    domain_calc: DomainMentionCalculator = Depends(get_domain_mention_calculator),
    citation_calc: CitationDomainCalculator = Depends(get_citation_domain_calculator),
) -> ReportExportService:
    return ReportExportService(
        visibility_calculator=visibility_calc,
        domain_mention_calculator=domain_calc,
        citation_domain_calculator=citation_calc,
    )


def get_json_formatter() -> JsonExportFormatter:
    return JsonExportFormatter(indent=2)


__all__ = [
    "ReportExportService",
    "JsonExportFormatter",
    "get_report_export_service",
    "get_json_formatter",
]
