"""Brand position calculator."""

from dataclasses import dataclass, field
from typing import List, Literal, Optional

from src.reports.models.brand_models import BrandMentionResultModel
from src.reports.models.export_models import BrandPositionScore, BrandVisibilityScore
from src.reports.services.statistics.brand_visibility import BrandConfig


class BrandPositionCalculator:
    """
    Calculates average brand mention rank across report items.

    For each answer, brands are ranked by first character position (1st mentioned = rank 1).
    Average is computed only over prompts where the brand IS mentioned.
    Reliability tier is derived from visibility percentage.

    Single Responsibility: Only calculates brand position averages.
    """

    def calculate(
        self,
        *,
        brand_mentions_per_item: List[Optional[List[BrandMentionResultModel]]],
        brands: List[BrandConfig],
        visibility_scores: List[BrandVisibilityScore],
    ) -> List[BrandPositionScore]:
        """
        Calculate average position scores for each brand.

        Args:
            brand_mentions_per_item: Brand mentions for each item (parallel to items).
                                     None means the item had no answer.
            brands: List of brand configs (target + competitors)
            visibility_scores: Pre-computed visibility scores for reliability derivation

        Returns:
            List of position scores per brand
        """
        items_with_answers = [m for m in brand_mentions_per_item if m is not None]
        total_prompts = len(items_with_answers)

        if total_prompts == 0 or not brands:
            return self._empty_results(brands, total_prompts)

        # Accumulate ranks per brand across all answers
        ranks_per_brand: dict[str, list[int]] = {b.name: [] for b in brands}

        for mentions in items_with_answers:
            if not mentions:
                continue
            item_ranks = self._rank_brands_in_item(mentions)
            for brand_name, rank in item_ranks.items():
                if brand_name in ranks_per_brand:
                    ranks_per_brand[brand_name].append(rank)

        # Build visibility lookup
        visibility_by_name = {v.brand_name: v.visibility_percentage for v in visibility_scores}

        results = []
        for brand in brands:
            ranks = ranks_per_brand[brand.name]
            visibility_pct = visibility_by_name.get(brand.name, 0.0)

            if ranks:
                avg_position = round(sum(ranks) / len(ranks), 1)
            else:
                avg_position = 0.0

            results.append(
                BrandPositionScore(
                    brand_name=brand.name,
                    is_target_brand=brand.is_target,
                    average_position=avg_position,
                    prompts_counted=len(ranks),
                    total_prompts=total_prompts,
                    visibility_percentage=visibility_pct,
                    reliability=self._derive_reliability(visibility_pct),
                )
            )

        return results

    @staticmethod
    def _rank_brands_in_item(
        mentions: List[BrandMentionResultModel],
    ) -> dict[str, int]:
        """Rank brands by first character position within a single answer.

        Returns:
            Dict of brand_name -> 1-indexed rank
        """
        brands_with_first_pos: list[tuple[str, int]] = []

        for brand_mention in mentions:
            if brand_mention.mentions:
                first_pos = min(m.start for m in brand_mention.mentions)
                brands_with_first_pos.append((brand_mention.brand_name, first_pos))

        brands_with_first_pos.sort(key=lambda x: x[1])

        return {name: rank for rank, (name, _) in enumerate(brands_with_first_pos, start=1)}

    @staticmethod
    def _derive_reliability(
        visibility_percentage: float,
    ) -> Literal["not_reliable", "low_reliability", "reliable", "high_reliability"]:
        """Derive reliability tier from visibility percentage."""
        if visibility_percentage > 60:
            return "high_reliability"
        if visibility_percentage > 30:
            return "reliable"
        if visibility_percentage >= 10:
            return "low_reliability"
        return "not_reliable"

    def _empty_results(
        self,
        brands: List[BrandConfig],
        total_prompts: int,
    ) -> List[BrandPositionScore]:
        return [
            BrandPositionScore(
                brand_name=brand.name,
                is_target_brand=brand.is_target,
                average_position=0.0,
                prompts_counted=0,
                total_prompts=total_prompts,
                visibility_percentage=0.0,
                reliability="not_reliable",
            )
            for brand in brands
        ]
