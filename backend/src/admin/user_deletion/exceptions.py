"""Exceptions for user deletion operations."""


class UserDeletionError(Exception):
    """Base exception for user deletion operations."""


class UserNotFoundError(UserDeletionError):
    """Raised when the user to delete cannot be found."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")


class CannotDeleteSuperuserError(UserDeletionError):
    """Raised when attempting to delete a superuser."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(f"Cannot delete superuser: {user_id}")


class CannotDeleteSelfError(UserDeletionError):
    """Raised when a user attempts to delete their own account."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(f"Cannot delete own account: {user_id}")
