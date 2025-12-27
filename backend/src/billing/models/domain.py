"""Billing domain models (value objects and entities)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class TransactionType(str, Enum):
    """Type of balance transaction."""

    DEBIT = "debit"
    CREDIT = "credit"


class CreditSource(str, Enum):
    """Source of credit grants."""

    SIGNUP_BONUS = "signup_bonus"
    PAYMENT = "payment"
    PROMO_CODE = "promo_code"
    REFERRAL = "referral"
    ADMIN_GRANT = "admin_grant"


@dataclass(frozen=True)
class BalanceInfo:
    """Immutable snapshot of user's balance state."""

    user_id: str
    total_balance: Decimal
    available_balance: Decimal  # Excludes expired credits
    expiring_soon_amount: Decimal  # Credits expiring in next 7 days
    expiring_soon_at: datetime | None


@dataclass(frozen=True)
class TransactionRecord:
    """Record of a balance transaction for audit trail."""

    id: int
    user_id: str
    transaction_type: TransactionType
    amount: Decimal
    balance_after: Decimal
    reason: str
    reference_type: str | None
    reference_id: str | None
    created_at: datetime


@dataclass(frozen=True)
class ConsumptionRecord:
    """Record of an evaluation consumption."""

    id: int
    user_id: str
    evaluation_id: int
    amount_charged: Decimal
    consumed_at: datetime


@dataclass(frozen=True)
class ChargeResult:
    """Result of a charge operation.

    Supports partial charges when user cannot afford full batch.
    """

    charged_evaluation_ids: list[int]
    skipped_evaluation_ids: list[int]  # Not charged (already consumed or no balance)
    total_charged: Decimal
    remaining_balance: Decimal

    @property
    def fully_charged(self) -> bool:
        """True if all requested evaluations were charged."""
        return len(self.skipped_evaluation_ids) == 0


@dataclass(frozen=True)
class CreditGrantInfo:
    """Information about a credit grant."""

    id: int
    user_id: str
    source: CreditSource
    original_amount: Decimal
    remaining_amount: Decimal
    expires_at: datetime | None
    created_at: datetime
