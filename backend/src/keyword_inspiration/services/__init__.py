"""Services for keyword inspiration module."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.approval.policies import get_approval_policy
from src.config.settings import settings
from src.database.session import get_async_session
from src.embeddings.clustering_service import get_clustering_service
from src.embeddings.embeddings_service import get_embeddings_service
from src.keyword_inspiration.services.cluster_scoring_service import (
    ClusterScoringService,
)
from src.keyword_inspiration.services.data_for_seo_service import (
    DataForSEOService,
    get_dataforseo_service,
)
from src.keyword_inspiration.services.inspiration_orchestrator import (
    InspirationOrchestrator,
)
from src.keyword_inspiration.services.keyword_fetch_service import KeywordFetchService
from src.keyword_inspiration.services.prompts_generator_service import (
    PromptsGeneratorService,
    get_prompts_generator_service,
)
from src.prompt_groups.services.prompt_group_binding_service import (
    PromptGroupBindingService,
)
from src.prompt_groups.services.prompt_group_service import PromptGroupService
from src.prompts.services.prompt_service import PromptService


def _get_keyword_fetch_service(
    session: AsyncSession,
) -> KeywordFetchService:
    return KeywordFetchService(
        session=session,
        dataforseo_service=get_dataforseo_service(),
        cache_ttl_days=settings.keyword_inspiration_cache_ttl_days,
    )


def get_cluster_scoring_service(
    session: AsyncSession = Depends(get_async_session),
) -> ClusterScoringService:
    return ClusterScoringService(
        session=session,
        embeddings_service=get_embeddings_service(),
        clustering_service=get_clustering_service(),
        keyword_fetch_service=_get_keyword_fetch_service(session),
        cache_ttl_days=settings.keyword_inspiration_cache_ttl_days,
        top_clusters=settings.keyword_inspiration_top_clusters,
    )


def get_inspiration_orchestrator(
    session: AsyncSession = Depends(get_async_session),
) -> InspirationOrchestrator:
    return InspirationOrchestrator(
        session=session,
        prompts_generator=get_prompts_generator_service(),
        prompt_service=PromptService(
            session=session,
            embeddings_service=get_embeddings_service(),
            approval_policy=get_approval_policy(),
        ),
        group_service=PromptGroupService(session),
        binding_service=PromptGroupBindingService(session),
    )


__all__ = [
    "ClusterScoringService",
    "DataForSEOService",
    "InspirationOrchestrator",
    "KeywordFetchService",
    "PromptsGeneratorService",
    "get_cluster_scoring_service",
    "get_dataforseo_service",
    "get_inspiration_orchestrator",
    "get_prompts_generator_service",
]
