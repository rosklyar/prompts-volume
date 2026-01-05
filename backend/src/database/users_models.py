"""SQLAlchemy ORM models for users_db tables."""

import enum
import uuid as uuid_module
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.users_session import UsersBase


class User(UsersBase):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid_module.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Email verification
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    email_verification_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete support
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Check if user is soft deleted."""
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', is_superuser={self.is_superuser})>"


class CreditSource(str, enum.Enum):
    """Source of credit grants."""
    SIGNUP_BONUS = "signup_bonus"
    PAYMENT = "payment"
    PROMO_CODE = "promo_code"
    REFERRAL = "referral"
    ADMIN_GRANT = "admin_grant"


class TransactionType(str, enum.Enum):
    """Type of balance transaction."""
    DEBIT = "debit"
    CREDIT = "credit"


class CreditGrant(UsersBase):
    """Individual credit grants with expiration tracking.

    Credits are consumed using FIFO (oldest expiring first).
    Signup credits expire, paid credits don't.
    """

    __tablename__ = "credit_grants"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )  # No FK - application-level integrity
    source: Mapped[CreditSource] = mapped_column(
        Enum(
            CreditSource,
            values_callable=lambda x: [e.value for e in x],
            name="creditsource",
        ),
        nullable=False,
    )
    original_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )
    remaining_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,  # NULL = never expires
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    def __repr__(self) -> str:
        return f"<CreditGrant(id={self.id}, user_id='{self.user_id}', source='{self.source.value}', remaining={self.remaining_amount})>"


class BalanceTransaction(UsersBase):
    """Audit log of all balance changes."""

    __tablename__ = "balance_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )  # No FK - application-level integrity
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(
            TransactionType,
            values_callable=lambda x: [e.value for e in x],
            name="transactiontype",
        ),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<BalanceTransaction(id={self.id}, user_id='{self.user_id}', type='{self.transaction_type.value}', amount={self.amount})>"
