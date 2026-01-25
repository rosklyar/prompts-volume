"""Service for aggregating prompts and checking freshness."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.daily_scheduling.models.domain import GroupPromptAnalysis, PromptFreshnessInfo
from src.daily_scheduling.repositories.evaluation_query import EvaluationQueryRepository
from src.execution.models.domain import FreshnessCategory
from src.execution.services.freshness_service import FreshnessService


class PromptAggregatorService:
    """Aggregates prompts and classifies them by freshness.

    Single Responsibility: Determine which prompts need refresh.
    """

    def __init__(
        self,
        evals_session: AsyncSession,
        *,
        freshness_service: FreshnessService | None = None,
        evaluation_query: EvaluationQueryRepository | None = None,
    ) -> None:
        self._session = evals_session
        self._evaluation_query = evaluation_query or EvaluationQueryRepository(
            evals_session
        )
        # Use tighter threshold for scheduled batches: fresh_threshold - batch_timeout
        # This ensures prompts are refreshed before they become stale after batch completes
        scheduled_threshold = (
            settings.freshness_fresh_threshold_hours
            - settings.scheduled_batch_timeout_hours
        )
        self._freshness = freshness_service or FreshnessService(
            fresh_threshold_hours=scheduled_threshold,
        )

    async def analyze_group_prompts(
        self,
        group_id: int,
        user_id: str,
        prompts: list[dict],
        *,
        assistant_id: int = 1,
    ) -> GroupPromptAnalysis:
        """Analyze prompts in a group for freshness.

        Args:
            group_id: The group ID
            user_id: The user ID
            prompts: List of {prompt_id, prompt_text}
            assistant_id: The AI assistant ID to filter evaluations

        Returns:
            GroupPromptAnalysis with prompts_needing_refresh and fresh_prompt_selections
        """
        if not prompts:
            return GroupPromptAnalysis(
                group_id=group_id,
                user_id=user_id,
                prompts_needing_refresh=[],
                fresh_prompt_selections={},
            )

        prompt_ids = [p["prompt_id"] for p in prompts]
        freshness_map = await self._get_freshness_for_prompts(
            prompt_ids, assistant_id=assistant_id
        )

        prompts_needing_refresh: list[int] = []
        fresh_prompt_selections: dict[int, int] = {}

        for p in prompts:
            prompt_id = p["prompt_id"]
            freshness = freshness_map.get(prompt_id)

            if freshness is None or freshness.needs_refresh:
                prompts_needing_refresh.append(prompt_id)
            else:
                # Fresh prompt - record the evaluation ID for later use
                if freshness.latest_evaluation_id is not None:
                    fresh_prompt_selections[prompt_id] = freshness.latest_evaluation_id

        return GroupPromptAnalysis(
            group_id=group_id,
            user_id=user_id,
            prompts_needing_refresh=prompts_needing_refresh,
            fresh_prompt_selections=fresh_prompt_selections,
        )

    async def _get_freshness_for_prompts(
        self,
        prompt_ids: list[int],
        *,
        assistant_id: int = 1,
    ) -> dict[int, PromptFreshnessInfo]:
        """Get freshness info for multiple prompts.

        Args:
            prompt_ids: List of prompt IDs to check
            assistant_id: The AI assistant ID to filter evaluations

        Returns dict mapping prompt_id -> PromptFreshnessInfo.
        """
        if not prompt_ids:
            return {}

        # Get latest completed evaluation for each prompt
        latest_evals = await self._evaluation_query.get_latest_evaluations_with_timestamp(
            prompt_ids, assistant_id=assistant_id
        )

        now = datetime.now(timezone.utc)
        result: dict[int, PromptFreshnessInfo] = {}

        for prompt_id in prompt_ids:
            eval_info = latest_evals.get(prompt_id)
            if eval_info is None:
                result[prompt_id] = PromptFreshnessInfo(
                    prompt_id=prompt_id,
                    prompt_text="",  # Not needed for freshness check
                    needs_refresh=True,
                    latest_evaluation_id=None,
                )
            else:
                freshness = self._freshness.categorize(
                    eval_info["completed_at"],
                    eval_info["id"],
                    now,
                )
                result[prompt_id] = PromptFreshnessInfo(
                    prompt_id=prompt_id,
                    prompt_text="",
                    needs_refresh=freshness.category != FreshnessCategory.FRESH,
                    latest_evaluation_id=eval_info["id"],
                )

        return result

    def get_unique_prompts_needing_refresh(
        self,
        group_analyses: list[GroupPromptAnalysis],
    ) -> set[int]:
        """Get unique set of prompt IDs needing refresh across all groups.

        Used for deduplication when same prompt is in multiple groups.
        """
        unique_prompts: set[int] = set()
        for analysis in group_analyses:
            unique_prompts.update(analysis.prompts_needing_refresh)
        return unique_prompts
