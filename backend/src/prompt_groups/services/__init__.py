"""Services for prompt groups module."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.prompt_groups.services.prompt_group_binding_service import (
    PromptGroupBindingService,
)
from src.prompt_groups.services.prompt_group_service import PromptGroupService
from src.prompt_groups.services.topic_resolution_service import TopicResolutionService


def get_prompt_group_service(
    session: AsyncSession = Depends(get_async_session),
) -> PromptGroupService:
    """Dependency injection for PromptGroupService."""
    return PromptGroupService(session)


def get_prompt_group_binding_service(
    session: AsyncSession = Depends(get_async_session),
) -> PromptGroupBindingService:
    """Dependency injection for PromptGroupBindingService."""
    return PromptGroupBindingService(session)


def get_topic_resolution_service(
    session: AsyncSession = Depends(get_async_session),
) -> TopicResolutionService:
    """Dependency injection for TopicResolutionService."""
    return TopicResolutionService(session)


# Note: BatchUploadService has been moved to src.prompts.batch.service.BatchPromptsService

__all__ = [
    "PromptGroupService",
    "PromptGroupBindingService",
    "TopicResolutionService",
    "get_prompt_group_service",
    "get_prompt_group_binding_service",
    "get_topic_resolution_service",
]
