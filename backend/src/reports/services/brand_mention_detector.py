"""Brand mention detection service."""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class BrandInput:
    """Input brand specification (internal use)."""

    name: str
    variations: List[str]


@dataclass
class MentionPosition:
    """Position of a brand mention in text."""

    start: int
    end: int
    matched_text: str
    variation: str


@dataclass
class BrandMentionResult:
    """All mentions of a single brand in text."""

    brand_name: str
    mentions: List[MentionPosition]


class BrandMentionDetector:
    """Detects brand mentions using regex-based matching."""

    def detect(
        self, text: str, brands: List[BrandInput]
    ) -> List[BrandMentionResult]:
        """
        Detect all brand mentions in the given text.

        Uses compiled regex for O(n) performance where n = text length.
        All brand variations are searched in a single pass per brand.

        Args:
            text: The text to search for brand mentions
            brands: List of brands with their variations to search for

        Returns:
            List of BrandMentionResult, one per brand that has at least one mention
        """
        if not text or not brands:
            return []

        results = []
        for brand in brands:
            mentions = self._find_brand_mentions(text, brand)
            if mentions:
                results.append(
                    BrandMentionResult(brand_name=brand.name, mentions=mentions)
                )
        return results

    def _find_brand_mentions(
        self, text: str, brand: BrandInput
    ) -> List[MentionPosition]:
        """Find all mentions of a single brand's variations."""
        mentions = []

        for variation in brand.variations:
            # Escape special regex characters in variation
            pattern = re.escape(variation)
            # Case-insensitive and Unicode-aware matching
            regex = re.compile(pattern, re.IGNORECASE | re.UNICODE)

            for match in regex.finditer(text):
                mentions.append(
                    MentionPosition(
                        start=match.start(),
                        end=match.end(),
                        matched_text=match.group(),
                        variation=variation,
                    )
                )

        # Sort by position for consistent ordering
        mentions.sort(key=lambda m: m.start)
        return mentions


def get_brand_mention_detector() -> BrandMentionDetector:
    """Dependency injection for BrandMentionDetector."""
    return BrandMentionDetector()
