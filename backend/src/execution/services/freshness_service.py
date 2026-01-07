"""Service for evaluating prompt freshness."""

from datetime import datetime, timezone

from src.execution.models.domain import FreshnessCategory, FreshnessInfo


class FreshnessService:
    """Service for categorizing evaluation freshness.

    Freshness thresholds:
    - FRESH: < 24 hours
    - STALE: 24-72 hours
    - VERY_STALE: > 72 hours
    - NONE: no evaluations
    """

    def __init__(
        self,
        fresh_threshold_hours: int = 24,
        stale_threshold_hours: int = 72,
    ):
        """Initialize with configurable thresholds.

        Args:
            fresh_threshold_hours: Hours below which evaluation is fresh (default 24)
            stale_threshold_hours: Hours above which evaluation is very stale (default 72)
        """
        self._fresh_threshold = fresh_threshold_hours
        self._stale_threshold = stale_threshold_hours

    def categorize(
        self,
        latest_evaluation_at: datetime | None,
        latest_evaluation_id: int | None = None,
        now: datetime | None = None,
    ) -> FreshnessInfo:
        """Categorize freshness of an evaluation.

        Args:
            latest_evaluation_at: Timestamp of latest evaluation (None if no evaluations)
            latest_evaluation_id: ID of latest evaluation (for default selection)
            now: Current time (defaults to utcnow)

        Returns:
            FreshnessInfo with category and UI hints
        """
        if latest_evaluation_at is None:
            return FreshnessInfo.no_evaluations()

        now = now or datetime.now(timezone.utc)

        # Ensure timezone-aware comparison
        if latest_evaluation_at.tzinfo is None:
            latest_evaluation_at = latest_evaluation_at.replace(tzinfo=timezone.utc)

        age = now - latest_evaluation_at
        hours = age.total_seconds() / 3600

        if hours < self._fresh_threshold:
            # Fresh: select most recent, hide "Ask for fresh"
            return FreshnessInfo(
                category=FreshnessCategory.FRESH,
                hours_since_latest=hours,
                latest_evaluation_at=latest_evaluation_at,
                default_evaluation_id=latest_evaluation_id,
                show_ask_for_fresh=False,
                auto_ask_for_fresh=False,
            )
        elif hours < self._stale_threshold:
            # Stale: select most recent, show "Ask for fresh" option
            return FreshnessInfo(
                category=FreshnessCategory.STALE,
                hours_since_latest=hours,
                latest_evaluation_at=latest_evaluation_at,
                default_evaluation_id=latest_evaluation_id,
                show_ask_for_fresh=True,
                auto_ask_for_fresh=False,
            )
        else:
            # Very stale: auto-select "Ask for fresh"
            return FreshnessInfo(
                category=FreshnessCategory.VERY_STALE,
                hours_since_latest=hours,
                latest_evaluation_at=latest_evaluation_at,
                default_evaluation_id=None,
                show_ask_for_fresh=True,
                auto_ask_for_fresh=True,
            )

    def estimate_wait_time_seconds(self, queue_size: int) -> int:
        """Estimate wait time based on queue size.

        Simple formula: queue_size * 30 seconds.

        Args:
            queue_size: Number of items in queue

        Returns:
            Estimated wait time in seconds
        """
        return queue_size * 30

    def format_wait_time(self, seconds: int) -> str:
        """Format wait time as human-readable string.

        Args:
            seconds: Wait time in seconds

        Returns:
            Formatted string like "~5 minutes" or "~1 hour"
        """
        if seconds < 60:
            return f"~{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"~{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = seconds // 3600
            return f"~{hours} hour{'s' if hours != 1 else ''}"
