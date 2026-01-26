"""Export services with dependency injection."""

from src.reports.services.export.export_service import ReportExportService
from src.reports.services.export.json_formatter import JsonExportFormatter
from src.reports.services.statistics import (
    get_brand_visibility_calculator,
    get_citation_domain_calculator,
    get_domain_mention_calculator,
)


# Singleton instances
_report_export_service: ReportExportService | None = None
_json_formatter: JsonExportFormatter | None = None


def get_report_export_service() -> ReportExportService:
    """Get the singleton ReportExportService instance."""
    global _report_export_service
    if _report_export_service is None:
        _report_export_service = ReportExportService(
            visibility_calculator=get_brand_visibility_calculator(),
            domain_mention_calculator=get_domain_mention_calculator(),
            citation_domain_calculator=get_citation_domain_calculator(),
        )
    return _report_export_service


def get_json_formatter() -> JsonExportFormatter:
    """Get the singleton JsonExportFormatter instance."""
    global _json_formatter
    if _json_formatter is None:
        _json_formatter = JsonExportFormatter(indent=2)
    return _json_formatter


__all__ = [
    "ReportExportService",
    "JsonExportFormatter",
    "get_report_export_service",
    "get_json_formatter",
]
