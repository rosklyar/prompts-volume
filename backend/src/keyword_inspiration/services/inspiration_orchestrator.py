"""Generate prompt previews and create confirmed prompt groups."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.geography.services.country_resolver import CountryResolution
from src.keyword_inspiration.models.api_models import (
    ClusterPrompts,
    ConfirmGroupsRequest,
    CreateGroupsResponse,
    CreatedGroupInfo,
    GeneratePromptsRequest,
    GeneratePromptsResponse,
    GeneratedPromptItem,
)
from src.prompt_groups.services.prompt_group_binding_service import (
    PromptGroupBindingService,
)
from src.prompt_groups.services.prompt_group_service import PromptGroupService
from src.prompts.services.prompt_service import PromptService
from src.keyword_inspiration.services.prompts_generator_service import PromptsGeneratorService

logger = logging.getLogger(__name__)


class InspirationOrchestrator:
    """Generates prompt previews and creates confirmed prompt groups."""

    def __init__(
        self,
        session: AsyncSession,
        prompts_generator: PromptsGeneratorService,
        prompt_service: PromptService,
        group_service: PromptGroupService,
        binding_service: PromptGroupBindingService,
    ):
        self.session = session
        self.prompts_generator = prompts_generator
        self.prompt_service = prompt_service
        self.group_service = group_service
        self.binding_service = binding_service

    async def generate_prompts_preview(
        self,
        request: GeneratePromptsRequest,
        *,
        business_domain_name: str,
    ) -> GeneratePromptsResponse:
        """Generate prompt previews for selected clusters. No DB writes."""
        cluster_results: list[ClusterPrompts] = []
        total_prompts = 0

        for cluster in request.clusters:
            generated = await self.prompts_generator.generate_prompts_from_keywords(
                keywords=cluster.keywords,
                business_domain=business_domain_name,
                language=request.language,
                session=self.session,
            )

            prompts = [
                GeneratedPromptItem(prompt_text=prompt_text, source_keyword=source_kw)
                for prompt_text, source_kw in generated
            ]

            cluster_results.append(ClusterPrompts(
                cluster_id=cluster.cluster_id,
                title=cluster.title,
                prompts=prompts,
            ))
            total_prompts += len(prompts)

        return GeneratePromptsResponse(
            clusters=cluster_results,
            total_prompts=total_prompts,
        )

    async def confirm_and_create_groups(
        self,
        request: ConfirmGroupsRequest,
        user_id: str,
    ) -> CreateGroupsResponse:
        """Create groups with only the user-confirmed prompts."""
        brand_data = request.brand.model_dump()
        competitors_data = (
            [c.model_dump() for c in request.competitors] if request.competitors else None
        )

        country_resolution = CountryResolution(
            country_id=request.country_id,
            is_locked=False,
            source="explicit",
        )

        groups: list[CreatedGroupInfo] = []
        total_prompts = 0

        for cluster in request.clusters:
            prompt_ids: list[int] = []
            for prompt_text in cluster.prompts:
                prompt = await self.prompt_service.add_prompt(
                    prompt_text=prompt_text,
                    user_id=user_id,
                    is_admin=False,
                )
                prompt_ids.append(prompt.id)

            group = await self.group_service.create_group(
                user_id=user_id,
                title=cluster.title,
                brand=brand_data,
                country_resolution=country_resolution,
                competitors=competitors_data,
            )

            if prompt_ids:
                await self.binding_service.add_prompts_to_group(group, prompt_ids)

            groups.append(CreatedGroupInfo(
                group_id=group.id,
                title=cluster.title,
                prompts_count=len(prompt_ids),
            ))
            total_prompts += len(prompt_ids)

            logger.info(
                f"Created group '{cluster.title}' with {len(prompt_ids)} prompts"
            )

        return CreateGroupsResponse(groups=groups, total_prompts=total_prompts)
