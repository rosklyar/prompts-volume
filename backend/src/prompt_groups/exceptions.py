"""Domain exceptions for prompt groups module."""

from fastapi import HTTPException, status


class PromptGroupError(Exception):
    """Base exception for prompt group domain."""

    pass


class GroupNotFoundError(PromptGroupError):
    """Raised when a group is not found."""

    def __init__(self, group_id: int):
        self.group_id = group_id
        super().__init__(f"Group with id {group_id} not found")


class GroupAccessDeniedError(PromptGroupError):
    """Raised when user tries to access a group they don't own."""

    def __init__(self, group_id: int, user_id: str):
        self.group_id = group_id
        self.user_id = user_id
        super().__init__(f"User {user_id} does not have access to group {group_id}")


class DuplicateGroupTitleError(PromptGroupError):
    """Raised when a group with the same title already exists."""

    def __init__(self, title: str):
        self.title = title
        super().__init__(f"Group with title '{title}' already exists")


class PromptNotFoundError(PromptGroupError):
    """Raised when a prompt is not found."""

    def __init__(self, prompt_id: int):
        self.prompt_id = prompt_id
        super().__init__(f"Prompt with id {prompt_id} not found")


def to_http_exception(error: PromptGroupError) -> HTTPException:
    """Convert domain exception to HTTP exception."""
    if isinstance(error, GroupNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, GroupAccessDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, DuplicateGroupTitleError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, PromptNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
    )
