"""Service for tracking consumed evaluations."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.exceptions import DuplicateConsumptionError
from src.billing.models.domain import ConsumptionRecord
from src.database.evals_models import ConsumedEvaluation


class ConsumptionService:
    """Service for tracking consumed evaluations.

    Implements ConsumptionTracker protocol.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def is_consumed(
        self,
        user_id: str,
        evaluation_id: int,
    ) -> bool:
        """Check if user has already consumed this evaluation."""
        query = select(ConsumedEvaluation.id).where(
            ConsumedEvaluation.user_id == user_id,
            ConsumedEvaluation.evaluation_id == evaluation_id,
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none() is not None

    async def record_consumption(
        self,
        user_id: str,
        evaluation_id: int,
        amount_charged: Decimal,
    ) -> ConsumptionRecord:
        """Record that user has consumed an evaluation.

        Raises:
            DuplicateConsumptionError: If already consumed.
        """
        consumption = ConsumedEvaluation(
            user_id=user_id,
            evaluation_id=evaluation_id,
            amount_charged=amount_charged,
        )
        self._session.add(consumption)

        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise DuplicateConsumptionError(user_id, evaluation_id)

        return ConsumptionRecord(
            id=consumption.id,
            user_id=user_id,
            evaluation_id=evaluation_id,
            amount_charged=amount_charged,
            consumed_at=consumption.consumed_at,
        )

    async def get_consumed_evaluation_ids(
        self,
        user_id: str,
        evaluation_ids: list[int],
    ) -> set[int]:
        """Get which of the given evaluation IDs the user has consumed."""
        if not evaluation_ids:
            return set()

        query = select(ConsumedEvaluation.evaluation_id).where(
            ConsumedEvaluation.user_id == user_id,
            ConsumedEvaluation.evaluation_id.in_(evaluation_ids),
        )
        result = await self._session.execute(query)
        return set(result.scalars().all())

    async def get_consumption_count(self, user_id: str) -> int:
        """Get total number of evaluations consumed by user."""
        from sqlalchemy import func

        query = select(func.count(ConsumedEvaluation.id)).where(
            ConsumedEvaluation.user_id == user_id
        )
        result = await self._session.execute(query)
        return result.scalar() or 0
