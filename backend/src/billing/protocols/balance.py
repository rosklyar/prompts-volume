"""Balance management protocols."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from src.billing.models.domain import BalanceInfo, TransactionRecord


class BalanceReader(Protocol):
    """Protocol for reading balance information."""

    async def get_balance(self, user_id: str) -> BalanceInfo:
        """Get current balance information for a user.

        Returns:
            BalanceInfo containing available_balance, reserved_balance,
            and credit expiration information.
        """
        ...

    async def can_afford(self, user_id: str, amount: Decimal) -> bool:
        """Check if user can afford a charge of the given amount.

        Uses available (non-expired, non-reserved) balance.
        """
        ...


class BalanceModifier(Protocol):
    """Protocol for modifying balance."""

    async def debit(
        self,
        user_id: str,
        amount: Decimal,
        reason: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
    ) -> TransactionRecord:
        """Deduct amount from user's balance.

        Args:
            user_id: User to debit
            amount: Positive amount to deduct
            reason: Human-readable reason for the transaction
            reference_type: Type of related entity (e.g., "evaluation")
            reference_id: ID of related entity

        Returns:
            TransactionRecord with details of the completed transaction.

        Raises:
            InsufficientBalanceError: If user cannot afford the debit.
        """
        ...

    async def credit(
        self,
        user_id: str,
        amount: Decimal,
        reason: str,
        source: str = "payment",
        expires_at: datetime | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
    ) -> TransactionRecord:
        """Add amount to user's balance.

        Args:
            user_id: User to credit
            amount: Positive amount to add
            reason: Human-readable reason
            source: Source of the credit (payment, promo_code, etc.)
            expires_at: When this credit expires (None = never)
            reference_type: Type of related entity (e.g., "payment", "promo")
            reference_id: ID of related entity

        Returns:
            TransactionRecord with details.
        """
        ...
