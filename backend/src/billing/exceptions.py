"""Domain exceptions for billing module."""

from decimal import Decimal

from fastapi import HTTPException, status


class BillingError(Exception):
    """Base exception for billing domain."""

    pass


class InsufficientBalanceError(BillingError):
    """Raised when user cannot afford a charge."""

    def __init__(self, user_id: str, required: Decimal, available: Decimal):
        self.user_id = user_id
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient balance for user {user_id}: "
            f"required {required}, available {available}"
        )


class DuplicateConsumptionError(BillingError):
    """Raised when trying to consume an already-consumed evaluation."""

    def __init__(self, user_id: str, evaluation_id: int):
        self.user_id = user_id
        self.evaluation_id = evaluation_id
        super().__init__(
            f"Evaluation {evaluation_id} already consumed by user {user_id}"
        )


class CreditGrantNotFoundError(BillingError):
    """Raised when a credit grant is not found."""

    def __init__(self, grant_id: int):
        self.grant_id = grant_id
        super().__init__(f"Credit grant {grant_id} not found")


def to_http_exception(error: BillingError) -> HTTPException:
    """Convert domain exception to HTTP exception."""
    if isinstance(error, InsufficientBalanceError):
        return HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": str(error),
                "required": str(error.required),
                "available": str(error.available),
            },
        )
    if isinstance(error, DuplicateConsumptionError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(error),
    )
