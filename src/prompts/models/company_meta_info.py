"""Company metadata dataclass for internal use."""

from dataclasses import dataclass
from typing import List

from src.prompts.models.business_domain import BusinessDomain


@dataclass
class CompanyMetaInfo:
    """Company metadata for prompts generation."""

    business_domain: BusinessDomain  # Business domain classification
    top_topics: List[str]  # Top 10 topics/products company sells
    brand_variations: List[str]  # Brand name variations to filter
