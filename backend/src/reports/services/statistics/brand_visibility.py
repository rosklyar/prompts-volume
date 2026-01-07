"""Brand visibility calculator."""

from dataclasses import dataclass
from typing import List, Optional

from src.reports.models.brand_models import BrandMentionResultModel
from src.reports.models.export_models import BrandVisibilityScore


@dataclass
class BrandConfig:
    """Brand configuration for visibility calculation."""

    name: str
    is_target: bool


class BrandVisibilityCalculator:
    """
    Calculates brand visibility scores.

    Visibility = (prompts with at least one brand mention / total prompts with answers) * 100

    Single Responsibility: Only calculates brand visibility percentages.
    """

    def calculate(
        self,
        brand_mentions_per_item: List[Optional[List[BrandMentionResultModel]]],
        brands: List[BrandConfig],
    ) -> List[BrandVisibilityScore]:
        """
        Calculate visibility scores for each brand.

        Args:
            brand_mentions_per_item: Brand mentions for each item (parallel to items).
                                     None means the item had no answer.
            brands: List of brand configs (target + competitors)

        Returns:
            List of visibility scores per brand
        """
        # Only count items that have brand mentions data (means they had answers)
        items_with_answers = [m for m in brand_mentions_per_item if m is not None]
        total_prompts = len(items_with_answers)

        if total_prompts == 0:
            return [
                BrandVisibilityScore(
                    brand_name=brand.name,
                    is_target_brand=brand.is_target,
                    prompts_with_mentions=0,
                    total_prompts=0,
                    visibility_percentage=0.0,
                )
                for brand in brands
            ]

        results = []
        for brand in brands:
            prompts_with_mentions = 0

            for mentions in items_with_answers:
                if not mentions:
                    continue

                brand_mention = next(
                    (m for m in mentions if m.brand_name == brand.name),
                    None,
                )
                if brand_mention and len(brand_mention.mentions) > 0:
                    prompts_with_mentions += 1

            visibility = (
                (prompts_with_mentions / total_prompts) * 100
                if total_prompts > 0
                else 0.0
            )

            results.append(
                BrandVisibilityScore(
                    brand_name=brand.name,
                    is_target_brand=brand.is_target,
                    prompts_with_mentions=prompts_with_mentions,
                    total_prompts=total_prompts,
                    visibility_percentage=round(visibility, 2),
                )
            )

        return results
