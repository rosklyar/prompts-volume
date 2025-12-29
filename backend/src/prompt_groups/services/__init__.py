"""Services for prompt groups module."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database.evals_session import get_evals_session
from src.database.session import get_async_session
from src.embeddings.embeddings_service import EmbeddingsService, get_embeddings_service
from src.prompt_groups.services.batch_upload_service import BatchUploadService
from src.prompt_groups.services.prompt_group_binding_service import (
    PromptGroupBindingService,
)
from src.prompt_groups.services.prompt_group_service import PromptGroupService


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


def get_batch_upload_service(
    prompts_session: AsyncSession = Depends(get_async_session),
    evals_session: AsyncSession = Depends(get_evals_session),
    embeddings_service: EmbeddingsService = Depends(get_embeddings_service),
) -> BatchUploadService:
    """Dependency injection for BatchUploadService."""
    return BatchUploadService(
        prompts_session=prompts_session,
        evals_session=evals_session,
        embeddings_service=embeddings_service,
        similarity_threshold=settings.batch_upload_similarity_threshold,
        match_limit=settings.batch_upload_match_limit,
        max_prompts_per_batch=settings.batch_upload_max_prompts,
    )


__all__ = [
    "PromptGroupService",
    "PromptGroupBindingService",
    "BatchUploadService",
    "get_prompt_group_service",
    "get_prompt_group_binding_service",
    "get_batch_upload_service",
]
