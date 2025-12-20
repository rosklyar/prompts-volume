"""Results enricher orchestrator service."""

from typing import List, Optional

from fastapi import Depends

from src.evaluations.models.api_models import EvaluationResultItem
from src.evaluations.models.brand_models import (
    BrandMentionResultModel,
    MentionPositionModel,
)
from src.evaluations.models.citation_models import (
    CitationCountItemModel,
    CitationLeaderboardModel,
)
from src.evaluations.models.enriched_models import (
    EnrichedEvaluationResultModel,
    EnrichedResultsResponse,
)
from src.evaluations.services.brand_mention_detector import (
    BrandInput,
    BrandMentionDetector,
    get_brand_mention_detector,
)
from src.evaluations.services.citation_leaderboard_builder import (
    CitationInput,
    CitationLeaderboardBuilder,
    get_citation_leaderboard_builder,
)


class ResultsEnricher:
    """Orchestrates enrichment of evaluation results."""

    def __init__(
        self,
        brand_detector: BrandMentionDetector,
        citation_builder: CitationLeaderboardBuilder,
    ):
        self.brand_detector = brand_detector
        self.citation_builder = citation_builder

    def enrich(
        self,
        results: List[EvaluationResultItem],
        brands: Optional[List[BrandInput]] = None,
    ) -> EnrichedResultsResponse:
        """
        Enrich evaluation results with brand mentions and citation leaderboard.

        Args:
            results: Raw evaluation results
            brands: Optional list of brands to detect (if None, skip brand detection)

        Returns:
            EnrichedResultsResponse with brand mentions per result and citation leaderboard
        """
        # Collect all citations for leaderboard
        all_citations: List[CitationInput] = []

        # Enrich each result
        enriched_results = []
        for result in results:
            brand_mentions = None

            # Extract response text and citations from answer
            response_text = None

            if result.answer:
                response_text = result.answer.get("response")
                raw_citations = result.answer.get("citations", [])
                for c in raw_citations:
                    if isinstance(c, dict) and "url" in c:
                        all_citations.append(
                            CitationInput(url=c["url"], text=c.get("text", ""))
                        )

            # Detect brand mentions if brands provided and response exists
            if brands and response_text:
                detected = self.brand_detector.detect(response_text, brands)
                brand_mentions = [
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

            enriched_results.append(
                EnrichedEvaluationResultModel(
                    prompt_id=result.prompt_id,
                    prompt_text=result.prompt_text,
                    evaluation_id=result.evaluation_id,
                    status=result.status,
                    answer=result.answer,
                    completed_at=result.completed_at,
                    brand_mentions=brand_mentions,
                )
            )

        # Build citation leaderboard from all citations
        leaderboard = self.citation_builder.aggregate(all_citations)
        leaderboard_model = CitationLeaderboardModel(
            items=[
                CitationCountItemModel(
                    path=item.path,
                    count=item.count,
                    is_domain=item.is_domain,
                )
                for item in leaderboard.items
            ],
            total_citations=leaderboard.total_citations,
        )

        return EnrichedResultsResponse(
            results=enriched_results,
            citation_leaderboard=leaderboard_model,
        )


def get_results_enricher(
    brand_detector: BrandMentionDetector = Depends(get_brand_mention_detector),
    citation_builder: CitationLeaderboardBuilder = Depends(
        get_citation_leaderboard_builder
    ),
) -> ResultsEnricher:
    """Dependency injection for ResultsEnricher."""
    return ResultsEnricher(
        brand_detector=brand_detector,
        citation_builder=citation_builder,
    )
