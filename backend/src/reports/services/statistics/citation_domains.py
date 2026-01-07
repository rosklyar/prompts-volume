"""Citation domain counter for brand/competitor domains."""

from dataclasses import dataclass
from typing import List, Optional

from src.reports.models.export_models import CitationDomainStat, ExportPromptItem


@dataclass
class BrandDomainConfig:
    """Brand domain config for citation counting."""

    name: str
    domain: str
    is_target: bool


class CitationDomainCalculator:
    """
    Counts how many times each brand's domain appears in citations.

    Single Responsibility: Only counts brand domains in citation URLs.
    """

    def calculate(
        self,
        items: List[ExportPromptItem],
        brand_domains: List[BrandDomainConfig],
    ) -> List[CitationDomainStat]:
        """
        Count brand domain occurrences in citations.

        Args:
            items: Report prompt items with answers
            brand_domains: List of brand/competitor domain configs

        Returns:
            Citation counts per brand domain, sorted target first then by count
        """
        # Initialize counts
        counts: dict[str, int] = {bd.domain: 0 for bd in brand_domains}

        for item in items:
            if not item.answer or not item.answer.citations:
                continue

            for citation in item.answer.citations:
                url = citation.url.lower()
                for bd in brand_domains:
                    if bd.domain.lower() in url:
                        counts[bd.domain] += 1

        # Build results
        results = [
            CitationDomainStat(
                name=bd.name,
                domain=bd.domain,
                is_target_brand=bd.is_target,
                citation_count=counts[bd.domain],
            )
            for bd in brand_domains
        ]

        # Sort: target first, then by count descending
        results.sort(key=lambda x: (not x.is_target_brand, -x.citation_count))

        return results
