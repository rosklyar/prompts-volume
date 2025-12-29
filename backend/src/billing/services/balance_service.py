"""Service for managing user balances."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.exceptions import InsufficientBalanceError
from src.billing.models.domain import BalanceInfo, TransactionRecord, TransactionType
from src.database.users_models import BalanceTransaction, CreditGrant, CreditSource


class BalanceService:
    """Service for managing user balances.

    Implements both BalanceReader and BalanceModifier protocols.

    Uses CreditGrant table for FIFO expiration handling:
    - Debits consume from oldest expiring grants first
    - Credits create new grants with appropriate expiration
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_balance(self, user_id: str) -> BalanceInfo:
        """Get current balance information for a user.

        Calculates available balance by summing remaining amounts
        from non-expired credit grants.
        """
        now = datetime.now(timezone.utc)
        expiring_threshold = now + timedelta(days=7)

        # Query for available balance (non-expired grants)
        available_query = select(
            func.coalesce(func.sum(CreditGrant.remaining_amount), Decimal("0"))
        ).where(
            CreditGrant.user_id == user_id,
            CreditGrant.remaining_amount > 0,
            (CreditGrant.expires_at.is_(None) | (CreditGrant.expires_at > now)),
        )
        available_result = await self._session.execute(available_query)
        available_balance = available_result.scalar() or Decimal("0")

        # Query for expiring soon amount
        expiring_query = select(
            func.coalesce(func.sum(CreditGrant.remaining_amount), Decimal("0")),
            func.min(CreditGrant.expires_at),
        ).where(
            CreditGrant.user_id == user_id,
            CreditGrant.remaining_amount > 0,
            CreditGrant.expires_at.is_not(None),
            CreditGrant.expires_at > now,
            CreditGrant.expires_at <= expiring_threshold,
        )
        expiring_result = await self._session.execute(expiring_query)
        expiring_row = expiring_result.one()
        expiring_amount = expiring_row[0] or Decimal("0")
        expiring_at = expiring_row[1]

        return BalanceInfo(
            user_id=user_id,
            total_balance=available_balance,  # For now, total = available
            available_balance=available_balance,
            expiring_soon_amount=expiring_amount,
            expiring_soon_at=expiring_at,
        )

    async def can_afford(self, user_id: str, amount: Decimal) -> bool:
        """Check if user can afford a charge."""
        balance_info = await self.get_balance(user_id)
        return balance_info.available_balance >= amount

    async def debit(
        self,
        user_id: str,
        amount: Decimal,
        reason: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
    ) -> TransactionRecord:
        """Deduct amount from user's balance using FIFO expiration.

        Consumes from oldest expiring grants first (FIFO).
        Uses SELECT FOR UPDATE to prevent race conditions.
        """
        if amount <= 0:
            raise ValueError("Debit amount must be positive")

        now = datetime.now(timezone.utc)

        # Get grants ordered by expiration (NULL last = never expires)
        # Use FOR UPDATE to lock rows during debit
        grants_query = (
            select(CreditGrant)
            .where(
                CreditGrant.user_id == user_id,
                CreditGrant.remaining_amount > 0,
                (CreditGrant.expires_at.is_(None) | (CreditGrant.expires_at > now)),
            )
            .order_by(
                CreditGrant.expires_at.asc().nulls_last(),
                CreditGrant.created_at.asc(),
            )
            .with_for_update()
        )

        result = await self._session.execute(grants_query)
        grants = list(result.scalars().all())

        # Calculate total available
        total_available = sum(g.remaining_amount for g in grants)
        if total_available < amount:
            raise InsufficientBalanceError(
                user_id=user_id,
                required=amount,
                available=total_available,
            )

        # Consume from grants in order (FIFO by expiration)
        remaining_to_debit = amount
        for grant in grants:
            if remaining_to_debit <= 0:
                break

            debit_from_grant = min(grant.remaining_amount, remaining_to_debit)
            grant.remaining_amount -= debit_from_grant
            remaining_to_debit -= debit_from_grant

        # Calculate new balance
        new_balance = total_available - amount

        # Create transaction record
        transaction = BalanceTransaction(
            user_id=user_id,
            transaction_type=TransactionType.DEBIT,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self._session.add(transaction)
        await self._session.flush()

        return TransactionRecord(
            id=transaction.id,
            user_id=user_id,
            transaction_type=TransactionType.DEBIT,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            created_at=transaction.created_at,
        )

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
        """Add amount to user's balance by creating a new credit grant."""
        if amount <= 0:
            raise ValueError("Credit amount must be positive")

        # Get current balance first
        balance_info = await self.get_balance(user_id)
        new_balance = balance_info.available_balance + amount

        # Convert source string to enum
        credit_source = CreditSource(source)

        # Create credit grant
        grant = CreditGrant(
            user_id=user_id,
            source=credit_source,
            original_amount=amount,
            remaining_amount=amount,
            expires_at=expires_at,
        )
        self._session.add(grant)

        # Create transaction record
        transaction = BalanceTransaction(
            user_id=user_id,
            transaction_type=TransactionType.CREDIT,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self._session.add(transaction)
        await self._session.flush()

        return TransactionRecord(
            id=transaction.id,
            user_id=user_id,
            transaction_type=TransactionType.CREDIT,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            created_at=transaction.created_at,
        )

    async def get_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TransactionRecord], int]:
        """Get transaction history for a user."""
        # Count total
        count_query = select(func.count(BalanceTransaction.id)).where(
            BalanceTransaction.user_id == user_id
        )
        count_result = await self._session.execute(count_query)
        total = count_result.scalar() or 0

        # Get transactions
        query = (
            select(BalanceTransaction)
            .where(BalanceTransaction.user_id == user_id)
            .order_by(BalanceTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        transactions = result.scalars().all()

        records = [
            TransactionRecord(
                id=t.id,
                user_id=t.user_id,
                transaction_type=TransactionType(t.transaction_type.value),
                amount=t.amount,
                balance_after=t.balance_after,
                reason=t.reason,
                reference_type=t.reference_type,
                reference_id=t.reference_id,
                created_at=t.created_at,
            )
            for t in transactions
        ]

        return records, total
