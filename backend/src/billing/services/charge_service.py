"""Orchestrator service for charging users for evaluations."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models.domain import ChargeResult
from src.billing.protocols.balance import BalanceModifier, BalanceReader
from src.billing.protocols.consumption import ConsumptionTracker
from src.billing.protocols.pricing import PricingStrategy


class ChargeService:
    """Orchestrator service for charging users for evaluations.

    Coordinates between:
    - BalanceService (check and debit balance)
    - ConsumptionService (track what's been paid for)
    - PricingStrategy (determine prices)

    Supports partial loads: returns what user can afford.
    """

    def __init__(
        self,
        session: AsyncSession,
        balance_reader: BalanceReader,
        balance_modifier: BalanceModifier,
        consumption_tracker: ConsumptionTracker,
        pricing_strategy: PricingStrategy,
    ):
        self._session = session
        self._balance_reader = balance_reader
        self._balance_modifier = balance_modifier
        self._consumption_tracker = consumption_tracker
        self._pricing_strategy = pricing_strategy

    async def charge_for_evaluations(
        self,
        user_id: str,
        evaluation_ids: list[int],
    ) -> ChargeResult:
        """Charge user for loading evaluations.

        Atomic operation:
        1. Filter out already-consumed evaluations
        2. Calculate how many new ones user can afford
        3. Debit balance and record consumptions atomically

        Returns partial results if user cannot afford all.

        Uses database transaction for atomicity.
        """
        if not evaluation_ids:
            balance_info = await self._balance_reader.get_balance(user_id)
            return ChargeResult(
                charged_evaluation_ids=[],
                skipped_evaluation_ids=[],
                total_charged=Decimal("0"),
                remaining_balance=balance_info.available_balance,
            )

        # Step 1: Filter out already consumed
        already_consumed = await self._consumption_tracker.get_consumed_evaluation_ids(
            user_id, evaluation_ids
        )
        new_evaluation_ids = [
            eid for eid in evaluation_ids if eid not in already_consumed
        ]

        if not new_evaluation_ids:
            # All already consumed - no charge needed
            balance_info = await self._balance_reader.get_balance(user_id)
            return ChargeResult(
                charged_evaluation_ids=[],
                skipped_evaluation_ids=list(already_consumed),
                total_charged=Decimal("0"),
                remaining_balance=balance_info.available_balance,
            )

        # Step 2: Calculate how many user can afford
        balance_info = await self._balance_reader.get_balance(user_id)
        unit_price = self._pricing_strategy.get_unit_price(user_id)

        if unit_price > 0:
            affordable_count = int(balance_info.available_balance / unit_price)
        else:
            affordable_count = len(new_evaluation_ids)

        # Take what user can afford (preserve order for determinism)
        to_charge = new_evaluation_ids[:affordable_count]
        cannot_afford = new_evaluation_ids[affordable_count:]

        if not to_charge:
            # Cannot afford any
            return ChargeResult(
                charged_evaluation_ids=[],
                skipped_evaluation_ids=evaluation_ids,
                total_charged=Decimal("0"),
                remaining_balance=balance_info.available_balance,
            )

        # Step 3: Charge atomically
        total_amount = self._pricing_strategy.calculate_total(user_id, len(to_charge))

        # Debit balance
        transaction = await self._balance_modifier.debit(
            user_id=user_id,
            amount=total_amount,
            reason=f"Loaded {len(to_charge)} evaluations",
            reference_type="evaluation_batch",
            reference_id=",".join(str(eid) for eid in to_charge[:10]),  # First 10 IDs
        )

        # Record consumptions
        for eval_id in to_charge:
            await self._consumption_tracker.record_consumption(
                user_id=user_id,
                evaluation_id=eval_id,
                amount_charged=unit_price,
            )

        return ChargeResult(
            charged_evaluation_ids=to_charge,
            skipped_evaluation_ids=list(already_consumed) + cannot_afford,
            total_charged=total_amount,
            remaining_balance=transaction.balance_after,
        )

    async def preview_charge(
        self,
        user_id: str,
        evaluation_ids: list[int],
    ) -> dict:
        """Preview what a charge would look like without actually charging.

        Returns:
            Dict with:
            - fresh_count: Number of evaluations to charge for
            - already_consumed_count: Number already consumed
            - estimated_cost: Total cost for fresh evaluations
            - user_balance: Current user balance
            - affordable_count: How many user can afford
            - needs_top_up: Whether user needs to top up
        """
        if not evaluation_ids:
            balance_info = await self._balance_reader.get_balance(user_id)
            return {
                "fresh_count": 0,
                "already_consumed_count": 0,
                "estimated_cost": Decimal("0"),
                "user_balance": balance_info.available_balance,
                "affordable_count": 0,
                "needs_top_up": False,
            }

        # Get already consumed
        already_consumed = await self._consumption_tracker.get_consumed_evaluation_ids(
            user_id, evaluation_ids
        )
        fresh_count = len(evaluation_ids) - len(already_consumed)

        # Get balance and pricing
        balance_info = await self._balance_reader.get_balance(user_id)
        unit_price = self._pricing_strategy.get_unit_price(user_id)
        estimated_cost = self._pricing_strategy.calculate_total(user_id, fresh_count)

        if unit_price > 0:
            affordable_count = min(
                fresh_count, int(balance_info.available_balance / unit_price)
            )
        else:
            affordable_count = fresh_count

        return {
            "fresh_count": fresh_count,
            "already_consumed_count": len(already_consumed),
            "estimated_cost": estimated_cost,
            "user_balance": balance_info.available_balance,
            "affordable_count": affordable_count,
            "needs_top_up": fresh_count > affordable_count,
        }
