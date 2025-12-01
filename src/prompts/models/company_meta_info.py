"""Company metadata dataclass for internal use."""

from dataclasses import dataclass
from typing import List, Optional

from src.database import BusinessDomain


@dataclass
class CompanyMetaInfo:
    """Company metadata for prompts generation."""

    business_domain: Optional[BusinessDomain]  # Business domain ORM object, or None if not classified
    top_topics: List[str]  # Top 10 topics/products company sells
    brand_variations: List[str]  # Brand name variations to filter
