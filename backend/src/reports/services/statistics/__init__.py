"""Statistics calculators for report export."""

from src.reports.services.statistics.brand_visibility import (
    BrandConfig,
    BrandVisibilityCalculator,
)
from src.reports.services.statistics.citation_domains import (
    BrandDomainConfig,
    CitationDomainCalculator,
)
from src.reports.services.statistics.domain_mentions import (
    DomainConfig,
    DomainMentionCalculator,
)


# Singleton instances
_brand_visibility_calculator: BrandVisibilityCalculator | None = None
_domain_mention_calculator: DomainMentionCalculator | None = None
_citation_domain_calculator: CitationDomainCalculator | None = None


def get_brand_visibility_calculator() -> BrandVisibilityCalculator:
    """Get the singleton BrandVisibilityCalculator instance."""
    global _brand_visibility_calculator
    if _brand_visibility_calculator is None:
        _brand_visibility_calculator = BrandVisibilityCalculator()
    return _brand_visibility_calculator


def get_domain_mention_calculator() -> DomainMentionCalculator:
    """Get the singleton DomainMentionCalculator instance."""
    global _domain_mention_calculator
    if _domain_mention_calculator is None:
        _domain_mention_calculator = DomainMentionCalculator()
    return _domain_mention_calculator


def get_citation_domain_calculator() -> CitationDomainCalculator:
    """Get the singleton CitationDomainCalculator instance."""
    global _citation_domain_calculator
    if _citation_domain_calculator is None:
        _citation_domain_calculator = CitationDomainCalculator()
    return _citation_domain_calculator


__all__ = [
    "BrandConfig",
    "BrandVisibilityCalculator",
    "get_brand_visibility_calculator",
    "DomainConfig",
    "DomainMentionCalculator",
    "get_domain_mention_calculator",
    "BrandDomainConfig",
    "CitationDomainCalculator",
    "get_citation_domain_calculator",
]
