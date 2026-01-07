"""Domain models for execution module."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class FreshnessCategory(str, Enum):
    """Category of evaluation freshness.

    Determines UI behavior:
    - FRESH: < 24h old, select most recent, hide "Ask for fresh"
    - STALE: 24-72h old, select most recent, show "Ask for fresh" option
    - VERY_STALE: > 72h old, auto-select "Ask for fresh"
    - NONE: no evaluations, auto-select "Ask for fresh"
    """

    FRESH = "fresh"
    STALE = "stale"
    VERY_STALE = "very_stale"
    NONE = "none"


@dataclass
class FreshnessInfo:
    """Freshness information for a prompt's latest evaluation."""

    category: FreshnessCategory
    hours_since_latest: float | None
    latest_evaluation_at: datetime | None

    # UI hints based on freshness
    default_evaluation_id: int | None
    show_ask_for_fresh: bool
    auto_ask_for_fresh: bool

    @classmethod
    def no_evaluations(cls) -> "FreshnessInfo":
        """Factory for prompts with no evaluations."""
        return cls(
            category=FreshnessCategory.NONE,
            hours_since_latest=None,
            latest_evaluation_at=None,
            default_evaluation_id=None,
            show_ask_for_fresh=True,
            auto_ask_for_fresh=True,
        )
