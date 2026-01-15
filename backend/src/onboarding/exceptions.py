"""Domain exceptions for onboarding module."""

from fastapi import HTTPException, status


class OnboardingError(Exception):
    """Base exception for onboarding domain."""

    pass


class PreferencesNotFoundError(OnboardingError):
    """Raised when user has no preferences record."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"Preferences not found for user {user_id}")


class OnboardingAlreadyCompletedError(OnboardingError):
    """Raised when trying to complete onboarding that's already done."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"Onboarding already completed for user {user_id}")


def to_http_exception(error: OnboardingError) -> HTTPException:
    """Convert domain exception to HTTP exception."""
    if isinstance(error, PreferencesNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, OnboardingAlreadyCompletedError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
    )
