"""Domain mention aggregator."""

from dataclasses import dataclass
from typing import List, Optional

from src.reports.models.brand_models import DomainMentionResultModel
from src.reports.models.export_models import DomainMentionStat


@dataclass
class DomainConfig:
    """Domain configuration for aggregation."""

    name: str
    domain: str
    is_target: bool


class DomainMentionCalculator:
    """
    Aggregates domain mentions across all report items.

    Single Responsibility: Only aggregates domain mention counts.
    """

    def calculate(
        self,
        domain_mentions_per_item: List[Optional[List[DomainMentionResultModel]]],
        domains: List[DomainConfig],
    ) -> List[DomainMentionStat]:
        """
        Aggregate domain mentions.

        Args:
            domain_mentions_per_item: Domain mentions per item (parallel to items).
                                      None means the item had no answer.
            domains: List of domain configs

        Returns:
            Aggregated domain mention stats, sorted by target first then by count
        """
        # Initialize stats for all domains
        stats: dict[str, DomainMentionStat] = {
            d.domain: DomainMentionStat(
                name=d.name,
                domain=d.domain,
                is_target_brand=d.is_target,
                total_mentions=0,
                prompts_with_mentions=0,
            )
            for d in domains
        }

        for mentions in domain_mentions_per_item:
            if not mentions:
                continue

            for dm in mentions:
                if dm.domain not in stats:
                    continue

                mention_count = len(dm.mentions)
                current = stats[dm.domain]
                stats[dm.domain] = DomainMentionStat(
                    name=current.name,
                    domain=current.domain,
                    is_target_brand=current.is_target_brand,
                    total_mentions=current.total_mentions + mention_count,
                    prompts_with_mentions=current.prompts_with_mentions
                    + (1 if mention_count > 0 else 0),
                )

        # Convert to list and sort: target brand first, then by total_mentions descending
        result = list(stats.values())
        result.sort(key=lambda x: (not x.is_target_brand, -x.total_mentions))

        return result
