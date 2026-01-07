"""Report export service - orchestrates export generation."""

from datetime import datetime, timezone
from typing import List, Optional

from src.reports.models.brand_models import (
    BrandMentionResultModel,
    DomainMentionResultModel,
)
from src.reports.models.citation_models import CitationLeaderboardModel
from src.reports.models.export_models import (
    ExportBrandConfig,
    ExportBrandInfo,
    ExportPromptItem,
    ExportReportMeta,
    ExportStatistics,
    LeaderboardItem,
    ReportJsonExport,
)
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


class ReportExportService:
    """
    Orchestrates report export generation.

    Single Responsibility: Coordinates data assembly and statistics calculation.
    Dependency Inversion: Depends on abstractions (calculators injected).
    """

    def __init__(
        self,
        visibility_calculator: BrandVisibilityCalculator,
        domain_mention_calculator: DomainMentionCalculator,
        citation_domain_calculator: CitationDomainCalculator,
    ):
        self._visibility_calc = visibility_calculator
        self._domain_mention_calc = domain_mention_calculator
        self._citation_domain_calc = citation_domain_calculator

    def build_export(
        self,
        report_meta: ExportReportMeta,
        items: List[ExportPromptItem],
        brand_mentions_per_item: List[Optional[List[BrandMentionResultModel]]],
        domain_mentions_per_item: List[Optional[List[DomainMentionResultModel]]],
        citation_leaderboard: CitationLeaderboardModel,
        brand_config: Optional[dict],
        competitors_config: Optional[List[dict]],
    ) -> ReportJsonExport:
        """
        Build complete export data structure.

        Args:
            report_meta: Report metadata
            items: List of prompt items with answers
            brand_mentions_per_item: Brand mentions parallel to items
            domain_mentions_per_item: Domain mentions parallel to items
            citation_leaderboard: Pre-computed citation leaderboard
            brand_config: Brand configuration dict
            competitors_config: Competitors configuration list

        Returns:
            Complete export data structure
        """
        # Build brand info section
        brand_info = self._build_brand_info(brand_config, competitors_config)

        # Build statistics
        statistics = self._calculate_statistics(
            items=items,
            brand_mentions_per_item=brand_mentions_per_item,
            domain_mentions_per_item=domain_mentions_per_item,
            citation_leaderboard=citation_leaderboard,
            brand_config=brand_config,
            competitors_config=competitors_config,
        )

        return ReportJsonExport(
            export_version="1.0",
            exported_at=datetime.now(timezone.utc),
            report=report_meta,
            brand_info=brand_info,
            prompts=items,
            statistics=statistics,
        )

    def _build_brand_info(
        self,
        brand_config: Optional[dict],
        competitors_config: Optional[List[dict]],
    ) -> ExportBrandConfig:
        """Build brand info section from configs."""
        brand = None
        if brand_config:
            brand = ExportBrandInfo(
                name=brand_config.get("name", ""),
                domain=brand_config.get("domain"),
                variations=brand_config.get("variations", []),
            )

        competitors = []
        if competitors_config:
            for c in competitors_config:
                competitors.append(
                    ExportBrandInfo(
                        name=c.get("name", ""),
                        domain=c.get("domain"),
                        variations=c.get("variations", []),
                    )
                )

        return ExportBrandConfig(brand=brand, competitors=competitors)

    def _calculate_statistics(
        self,
        items: List[ExportPromptItem],
        brand_mentions_per_item: List[Optional[List[BrandMentionResultModel]]],
        domain_mentions_per_item: List[Optional[List[DomainMentionResultModel]]],
        citation_leaderboard: CitationLeaderboardModel,
        brand_config: Optional[dict],
        competitors_config: Optional[List[dict]],
    ) -> ExportStatistics:
        """Calculate all statistics."""

        # Build brand configs for visibility calculation
        brands: List[BrandConfig] = []
        if brand_config:
            brands.append(BrandConfig(name=brand_config["name"], is_target=True))
        if competitors_config:
            for c in competitors_config:
                brands.append(BrandConfig(name=c["name"], is_target=False))

        # Calculate brand visibility
        visibility_scores = self._visibility_calc.calculate(
            brand_mentions_per_item=brand_mentions_per_item,
            brands=brands,
        )

        # Build domain configs for domain mention calculation
        domains: List[DomainConfig] = []
        if brand_config and brand_config.get("domain"):
            domains.append(
                DomainConfig(
                    name=brand_config["name"],
                    domain=brand_config["domain"],
                    is_target=True,
                )
            )
        if competitors_config:
            for c in competitors_config:
                if c.get("domain"):
                    domains.append(
                        DomainConfig(
                            name=c["name"],
                            domain=c["domain"],
                            is_target=False,
                        )
                    )

        # Calculate domain mentions
        domain_mention_stats = self._domain_mention_calc.calculate(
            domain_mentions_per_item=domain_mentions_per_item,
            domains=domains,
        )

        # Build brand domain configs for citation counting
        brand_domains: List[BrandDomainConfig] = []
        if brand_config and brand_config.get("domain"):
            brand_domains.append(
                BrandDomainConfig(
                    name=brand_config["name"],
                    domain=brand_config["domain"],
                    is_target=True,
                )
            )
        if competitors_config:
            for c in competitors_config:
                if c.get("domain"):
                    brand_domains.append(
                        BrandDomainConfig(
                            name=c["name"],
                            domain=c["domain"],
                            is_target=False,
                        )
                    )

        # Calculate citation domain counts
        citation_domain_stats = self._citation_domain_calc.calculate(
            items=items,
            brand_domains=brand_domains,
        )

        # Convert citation leaderboard to export format
        domain_sources = [
            LeaderboardItem(path=d.path, count=d.count, is_domain=d.is_domain)
            for d in citation_leaderboard.domains
        ]
        page_paths = [
            LeaderboardItem(path=s.path, count=s.count, is_domain=s.is_domain)
            for s in citation_leaderboard.subpaths
        ]

        return ExportStatistics(
            brand_visibility=visibility_scores,
            domain_mentions=domain_mention_stats,
            citation_domains=citation_domain_stats,
            domain_sources_leaderboard=domain_sources,
            page_paths_leaderboard=page_paths,
            total_citations=citation_leaderboard.total_citations,
        )
