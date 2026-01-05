"""Service for calculating price of selected evaluations."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.evals_models import ConsumedEvaluation


@dataclass
class PricingResult:
    """Result of price calculation for selected evaluations."""

    total_cost: Decimal
    fresh_count: int
    already_consumed_count: int
    # evaluation_id -> price (0 if consumed)
    selection_prices: dict[int, Decimal]


class SelectionPricingService:
    """Calculates pricing for selected evaluations."""

    def __init__(
        self,
        evals_session: AsyncSession,
        price_per_evaluation: Decimal,
    ):
        self._evals_session = evals_session
        self._price_per_evaluation = price_per_evaluation

    async def calculate_price(
        self,
        user_id: str,
        evaluation_ids: list[int],
    ) -> PricingResult:
        """Calculate total price for selected evaluations.

        Fresh (not consumed) evaluations cost price_per_evaluation.
        Already consumed evaluations are free.
        """
        if not evaluation_ids:
            return PricingResult(
                total_cost=Decimal("0"),
                fresh_count=0,
                already_consumed_count=0,
                selection_prices={},
            )

        # Get consumed evaluation IDs
        consumed_ids = await self._get_consumed_evaluation_ids(user_id, evaluation_ids)

        # Calculate prices
        selection_prices: dict[int, Decimal] = {}
        fresh_count = 0
        already_consumed_count = 0

        for eval_id in evaluation_ids:
            if eval_id in consumed_ids:
                selection_prices[eval_id] = Decimal("0")
                already_consumed_count += 1
            else:
                selection_prices[eval_id] = self._price_per_evaluation
                fresh_count += 1

        total_cost = self._price_per_evaluation * fresh_count

        return PricingResult(
            total_cost=total_cost,
            fresh_count=fresh_count,
            already_consumed_count=already_consumed_count,
            selection_prices=selection_prices,
        )

    async def _get_consumed_evaluation_ids(
        self, user_id: str, evaluation_ids: list[int]
    ) -> set[int]:
        """Get which evaluations the user has already paid for."""
        query = select(ConsumedEvaluation.evaluation_id).where(
            ConsumedEvaluation.user_id == user_id,
            ConsumedEvaluation.evaluation_id.in_(evaluation_ids),
        )
        result = await self._evals_session.execute(query)
        return set(result.scalars().all())
