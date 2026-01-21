"""Services for prompt groups module."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.database.users_session import get_users_session
from src.geography.services.country_resolver import CountryResolver
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


def get_country_resolver(
    prompts_session: AsyncSession = Depends(get_async_session),
    users_session: AsyncSession = Depends(get_users_session),
) -> CountryResolver:
    """Dependency injection for CountryResolver.

    Requires both prompts_db and users_db sessions for cross-database resolution.
    """
    return CountryResolver(prompts_session, users_session)


# Note: BatchUploadService has been moved to src.prompts.batch.service.BatchPromptsService

__all__ = [
    "PromptGroupService",
    "PromptGroupBindingService",
    "TopicResolutionService",
    "CountryResolver",
    "get_prompt_group_service",
    "get_prompt_group_binding_service",
    "get_topic_resolution_service",
    "get_country_resolver",
]
