"""Date range resolution utility for reports endpoints."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

PresetPeriod = Literal["1d", "7d", "30d"]

_PRESET_DAYS: dict[PresetPeriod, int] = {
    "1d": 1,
    "7d": 7,
    "30d": 30,
}


@dataclass(frozen=True, slots=True)
class ResolvedDateRange:
    """Resolved date range with metadata about how it was resolved."""

    from_date: datetime
    to_date: datetime
    preset_used: PresetPeriod | None


class DateRangeValidationError(ValueError):
    """Raised when date range parameters are invalid."""


def resolve_date_range(
    *,
    period: PresetPeriod | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    default_days: int = 30,
) -> ResolvedDateRange:
    """Resolve date range from preset period or explicit dates.

    Validation rules:
    - If period provided -> from_date/to_date must be None
    - If custom dates provided -> period must be None
    - If nothing provided -> default to last `default_days` days
    - from_date must be before to_date

    Args:
        period: Preset period literal ("1d", "7d", "30d")
        from_date: Custom start date (inclusive)
        to_date: Custom end date (exclusive)
        default_days: Days to use when nothing is provided (default: 30)

    Returns:
        ResolvedDateRange with from_date, to_date, and preset_used

    Raises:
        DateRangeValidationError: If parameters violate mutual exclusivity rules
            or if from_date >= to_date
    """
    now = datetime.now(timezone.utc)

    # Check mutual exclusivity
    has_custom_dates = from_date is not None or to_date is not None
    has_preset = period is not None

    if has_preset and has_custom_dates:
        raise DateRangeValidationError(
            "Cannot specify both period and custom date range. "
            "Use either period OR from_date/to_date."
        )

    # Case 1: Preset period provided
    if has_preset:
        days = _PRESET_DAYS[period]
        return ResolvedDateRange(
            from_date=now - timedelta(days=days),
            to_date=now,
            preset_used=period,
        )

    # Case 2: Custom date range provided
    if has_custom_dates:
        if from_date is None or to_date is None:
            raise DateRangeValidationError(
                "Both from_date and to_date must be provided for custom date range."
            )

        # Ensure dates are timezone-aware
        if from_date.tzinfo is None:
            from_date = from_date.replace(tzinfo=timezone.utc)
        if to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=timezone.utc)

        if from_date >= to_date:
            raise DateRangeValidationError(
                "from_date must be before to_date."
            )

        return ResolvedDateRange(
            from_date=from_date,
            to_date=to_date,
            preset_used=None,
        )

    # Case 3: Nothing provided -> use default
    return ResolvedDateRange(
        from_date=now - timedelta(days=default_days),
        to_date=now,
        preset_used="30d" if default_days == 30 else None,
    )
