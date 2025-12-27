"""Consumption tracking protocols."""

from decimal import Decimal
from typing import Protocol

from src.billing.models.domain import ConsumptionRecord


class ConsumptionTracker(Protocol):
    """Protocol for tracking consumed resources."""

    async def is_consumed(
        self,
        user_id: str,
        evaluation_id: int,
    ) -> bool:
        """Check if user has already consumed (paid for) this evaluation."""
        ...

    async def record_consumption(
        self,
        user_id: str,
        evaluation_id: int,
        amount_charged: Decimal,
    ) -> ConsumptionRecord:
        """Record that user has consumed an evaluation.

        This should be called atomically with the balance debit.

        Raises:
            DuplicateConsumptionError: If already consumed.
        """
        ...

    async def get_consumed_evaluation_ids(
        self,
        user_id: str,
        evaluation_ids: list[int],
    ) -> set[int]:
        """Given a list of evaluation IDs, return which ones the user has consumed.

        Useful for filtering out already-paid evaluations from a batch.
        """
        ...
