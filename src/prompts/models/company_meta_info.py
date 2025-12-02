"""Company metadata dataclass for internal use."""

from dataclasses import dataclass
from typing import List, Optional

from src.database import BusinessDomain
from src.prompts.models.topic_match_result import TopicMatchResult


@dataclass
class CompanyMetaInfo:
    """Company metadata for prompts generation."""

    business_domain: Optional[BusinessDomain]  # Business domain ORM object, or None if not classified
    topics: TopicMatchResult  # Matched DB topics + unmatched generated topics
    brand_variations: List[str]  # Brand name variations to filter
