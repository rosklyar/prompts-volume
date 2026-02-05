"""Domain models for competitor discovery."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RawCompetitor:
    """Raw competitor data from search."""

    name: str
    domain: Optional[str]


@dataclass
class DiscoveredCompetitor:
    """Discovered competitor with variations."""

    brand_name: str
    domain: Optional[str]
    variations: List[str]
