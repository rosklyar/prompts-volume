"""Results enricher orchestrator service for reports."""

from typing import List, Optional

from fastapi import Depends

from src.reports.models.brand_models import (
    BrandMentionResultModel,
    MentionPositionModel,
)
from src.reports.models.citation_models import (
    CitationCountItemModel,
    CitationLeaderboardModel,
)
from src.reports.services.brand_mention_detector import (
    BrandInput,
    BrandMentionDetector,
    get_brand_mention_detector,
)
from src.reports.services.citation_leaderboard_builder import (
    CitationInput,
    CitationLeaderboardBuilder,
    get_citation_leaderboard_builder,
)


class ReportEnricher:
    """Enriches report items with brand mentions and builds citation leaderboard."""

    def __init__(
        self,
        brand_detector: BrandMentionDetector,
        citation_builder: CitationLeaderboardBuilder,
    ):
        self.brand_detector = brand_detector
        self.citation_builder = citation_builder

    def detect_brand_mentions(
        self,
        response_text: str,
        brands: List[BrandInput],
    ) -> List[BrandMentionResultModel]:
        """
        Detect brand mentions in response text.

        Args:
            response_text: The response text to search
            brands: List of brands to detect

        Returns:
            List of brand mention results
        """
        if not response_text or not brands:
            return []

        detected = self.brand_detector.detect(response_text, brands)
        return [
            BrandMentionResultModel(
                brand_name=d.brand_name,
                mentions=[
                    MentionPositionModel(
                        start=m.start,
                        end=m.end,
                        matched_text=m.matched_text,
                        variation=m.variation,
                    )
                    for m in d.mentions
                ],
            )
            for d in detected
        ]

    def build_citation_leaderboard(
        self,
        answers: List[Optional[dict]],
    ) -> CitationLeaderboardModel:
        """
        Build citation leaderboard from all answers.

        Args:
            answers: List of answer dicts, each may have 'citations' key

        Returns:
            CitationLeaderboardModel with domains and subpaths separated
        """
        all_citations: List[CitationInput] = []

        for answer in answers:
            if not answer:
                continue
            raw_citations = answer.get("citations", [])
            for c in raw_citations:
                if isinstance(c, dict) and "url" in c:
                    all_citations.append(
                        CitationInput(url=c["url"], text=c.get("text", ""))
                    )

        leaderboard = self.citation_builder.aggregate(all_citations)

        return CitationLeaderboardModel(
            domains=[
                CitationCountItemModel(
                    path=item.path,
                    count=item.count,
                    is_domain=item.is_domain,
                )
                for item in leaderboard.domains
            ],
            subpaths=[
                CitationCountItemModel(
                    path=item.path,
                    count=item.count,
                    is_domain=item.is_domain,
                )
                for item in leaderboard.subpaths
            ],
            total_citations=leaderboard.total_citations,
        )


def get_report_enricher(
    brand_detector: BrandMentionDetector = Depends(get_brand_mention_detector),
    citation_builder: CitationLeaderboardBuilder = Depends(
        get_citation_leaderboard_builder
    ),
) -> ReportEnricher:
    """Dependency injection for ReportEnricher."""
    return ReportEnricher(
        brand_detector=brand_detector,
        citation_builder=citation_builder,
    )
