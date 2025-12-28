"""API router for billing operations."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.auth.deps import CurrentUser
from src.billing.exceptions import BillingError, to_http_exception
from src.billing.models.api_models import (
    BalanceResponse,
    ChargeRequest,
    ChargeResponse,
    TopUpRequest,
    TopUpResponse,
    TransactionListResponse,
    TransactionResponse,
)
from src.billing.services import (
    BalanceService,
    ChargeService,
    get_balance_service,
    get_charge_service,
)
from src.config.settings import settings

router = APIRouter(prefix="/billing/api/v1", tags=["billing"])

BalanceServiceDep = Annotated[BalanceService, Depends(get_balance_service)]
ChargeServiceDep = Annotated[ChargeService, Depends(get_charge_service)]


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user: CurrentUser,
    balance_service: BalanceServiceDep,
):
    """Get current balance for the authenticated user.

    Returns available balance and information about expiring credits.
    """
    try:
        balance_info = await balance_service.get_balance(current_user.id)
        return BalanceResponse(
            available_balance=balance_info.available_balance,
            expiring_soon_amount=balance_info.expiring_soon_amount,
            expiring_soon_at=balance_info.expiring_soon_at,
        )
    except BillingError as e:
        raise to_http_exception(e)


@router.post("/top-up", response_model=TopUpResponse)
async def top_up_balance(
    request: TopUpRequest,
    current_user: CurrentUser,
    balance_service: BalanceServiceDep,
):
    """Add credits to user's balance.

    For now this is a simple endpoint for testing/admin use.
    In production, this would be called by a payment webhook.
    """
    try:
        transaction = await balance_service.credit(
            user_id=current_user.id,
            amount=request.amount,
            reason=f"Top-up via {request.source}",
            source=request.source,
            expires_at=request.expires_at,
            reference_type=request.source,
            reference_id=request.reference_id,
        )

        # Get updated balance
        balance_info = await balance_service.get_balance(current_user.id)

        return TopUpResponse(
            transaction_id=transaction.id,
            new_balance=balance_info.available_balance,
            amount_added=request.amount,
            expires_at=request.expires_at,
        )
    except BillingError as e:
        raise to_http_exception(e)


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    current_user: CurrentUser,
    balance_service: BalanceServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Get transaction history for the authenticated user."""
    try:
        transactions, total = await balance_service.get_transactions(
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )

        return TransactionListResponse(
            transactions=[
                TransactionResponse(
                    id=t.id,
                    transaction_type=t.transaction_type.value,
                    amount=t.amount,
                    balance_after=t.balance_after,
                    reason=t.reason,
                    reference_type=t.reference_type,
                    reference_id=t.reference_id,
                    created_at=t.created_at,
                )
                for t in transactions
            ],
            total=total,
        )
    except BillingError as e:
        raise to_http_exception(e)


@router.post("/charge", response_model=ChargeResponse)
async def charge_for_evaluations(
    request: ChargeRequest,
    current_user: CurrentUser,
    charge_service: ChargeServiceDep,
):
    """Charge user for loading evaluations.

    Supports partial loads - returns what user can afford.
    Already-consumed evaluations are included for free.
    """
    try:
        result = await charge_service.charge_for_evaluations(
            user_id=current_user.id,
            evaluation_ids=request.evaluation_ids,
        )

        return ChargeResponse(
            charged_evaluation_ids=result.charged_evaluation_ids,
            skipped_evaluation_ids=result.skipped_evaluation_ids,
            total_charged=result.total_charged,
            remaining_balance=result.remaining_balance,
            fully_charged=result.fully_charged,
        )
    except BillingError as e:
        raise to_http_exception(e)


@router.post("/charge/preview")
async def preview_charge(
    request: ChargeRequest,
    current_user: CurrentUser,
    charge_service: ChargeServiceDep,
):
    """Preview what a charge would look like without actually charging.

    Use this to show the user what they will pay before confirming.
    """
    try:
        preview = await charge_service.preview_charge(
            user_id=current_user.id,
            evaluation_ids=request.evaluation_ids,
        )

        return preview
    except BillingError as e:
        raise to_http_exception(e)


@router.post("/grant-signup-credits", response_model=TopUpResponse)
async def grant_signup_credits(
    current_user: CurrentUser,
    balance_service: BalanceServiceDep,
):
    """Grant initial signup credits to a user.

    This is typically called automatically during signup.
    Credits expire after the configured number of days.
    """
    try:
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.billing_signup_credits_expiry_days
        )

        transaction = await balance_service.credit(
            user_id=current_user.id,
            amount=Decimal(str(settings.billing_signup_credits)),
            reason="Signup bonus credits",
            source="signup_bonus",
            expires_at=expires_at,
            reference_type="signup",
            reference_id=current_user.id,
        )

        return TopUpResponse(
            transaction_id=transaction.id,
            new_balance=transaction.balance_after,
            amount_added=Decimal(str(settings.billing_signup_credits)),
            expires_at=expires_at,
        )
    except BillingError as e:
        raise to_http_exception(e)
