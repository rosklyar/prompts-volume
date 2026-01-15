"""Domain exceptions for approval module."""

from fastapi import HTTPException, status


class ApprovalError(Exception):
    """Base exception for approval domain."""

    pass


class PromptNotFoundError(ApprovalError):
    """Raised when a prompt is not found."""

    def __init__(self, prompt_id: int):
        self.prompt_id = prompt_id
        super().__init__(f"Prompt with id {prompt_id} not found")


class PromptNotPendingError(ApprovalError):
    """Raised when trying to approve/reject a prompt that is not pending."""

    def __init__(self, prompt_id: int, current_status: str):
        self.prompt_id = prompt_id
        self.current_status = current_status
        super().__init__(
            f"Prompt {prompt_id} is not pending (current status: {current_status})"
        )


class TopicRequiredError(ApprovalError):
    """Raised when approving a prompt without topic requires topic_id."""

    def __init__(self, prompt_id: int):
        self.prompt_id = prompt_id
        super().__init__(
            f"Prompt {prompt_id} has no topic. Provide topic_id when approving."
        )


class TopicNotFoundError(ApprovalError):
    """Raised when specified topic does not exist."""

    def __init__(self, topic_id: int):
        self.topic_id = topic_id
        super().__init__(f"Topic with id {topic_id} not found")


def to_http_exception(error: ApprovalError) -> HTTPException:
    """Convert domain exception to HTTP exception."""
    if isinstance(error, PromptNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, PromptNotPendingError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, TopicRequiredError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    if isinstance(error, TopicNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
    )
