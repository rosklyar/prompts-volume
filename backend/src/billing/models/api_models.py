"""Pydantic models for billing API endpoints."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BalanceResponse(BaseModel):
    """Response for balance inquiry."""

    available_balance: Decimal
    expiring_soon_amount: Decimal
    expiring_soon_at: datetime | None


class ChargeRequest(BaseModel):
    """Request to charge for evaluations."""

    evaluation_ids: list[int] = Field(..., min_length=1, max_length=100)


class ChargeResponse(BaseModel):
    """Response from charge operation."""

    charged_evaluation_ids: list[int]
    skipped_evaluation_ids: list[int]
    total_charged: Decimal
    remaining_balance: Decimal
    fully_charged: bool


class TopUpRequest(BaseModel):
    """Request to add credits (for admin/payment webhook)."""

    amount: Decimal = Field(..., gt=0)
    source: str = Field(
        ..., description="Source: 'payment', 'promo_code', 'admin_grant'"
    )
    expires_at: datetime | None = Field(
        None, description="When credits expire (null = never)"
    )
    reference_id: str | None = Field(
        None, description="External reference (e.g., payment ID)"
    )


class TopUpResponse(BaseModel):
    """Response from top-up operation."""

    transaction_id: int
    new_balance: Decimal
    amount_added: Decimal
    expires_at: datetime | None


class TransactionResponse(BaseModel):
    """Response for a single transaction."""

    id: int
    transaction_type: str
    amount: Decimal
    balance_after: Decimal
    reason: str
    reference_type: str | None
    reference_id: str | None
    created_at: datetime


class TransactionListResponse(BaseModel):
    """Response for transaction list."""

    transactions: list[TransactionResponse]
    total: int
