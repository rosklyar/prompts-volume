"""API router for dashboard operations."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.deps import CurrentUser
from src.database.evals_session import get_evals_session
from src.database.session import get_async_session
from src.prompt_groups.exceptions import GroupNotFoundError, to_http_exception
from src.prompt_groups.services import PromptGroupService, get_prompt_group_service
from src.reports.models.dashboard_models import DashboardResponse, PeriodLiteral
from src.reports.services.dashboard_service import DashboardService
from src.reports.services.results_enricher import ReportEnricher, get_report_enricher

router = APIRouter(prefix="/reports/api/v1", tags=["dashboard"])

PromptGroupServiceDep = Annotated[
    PromptGroupService, Depends(get_prompt_group_service)
]
ReportEnricherDep = Annotated[ReportEnricher, Depends(get_report_enricher)]


def get_dashboard_service(
    prompts_session: AsyncSession = Depends(get_async_session),
    evals_session: AsyncSession = Depends(get_evals_session),
    enricher: ReportEnricher = Depends(get_report_enricher),
) -> DashboardService:
    """Per-request service: requires database sessions."""
    return DashboardService(prompts_session, evals_session, enricher)


DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]


@router.get("/groups/{group_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    group_id: int,
    current_user: CurrentUser,
    dashboard_service: DashboardServiceDep,
    group_service: PromptGroupServiceDep,
    assistant_id: int = Query(..., description="AI Assistant ID to filter reports"),
    period: PeriodLiteral = Query(default="7d", description="Time period (1d, 7d, 30d)"),
):
    """Get dashboard analytics aggregated across reports in a time period.

    Returns brand visibility metrics, competitor rankings, citation sources,
    and prompt gaps aggregated from all reports within the specified time period.

    Args:
        group_id: The prompt group ID
        assistant_id: The AI assistant ID (required)
        period: Time period to aggregate (1d, 7d, 30d) - defaults to 7d

    Returns:
        DashboardResponse with:
        - reports_included: Number of reports aggregated
        - brand_visibility_percent: Target brand's visibility percentage
        - competitors: All brands ranked by visibility
        - sources: Citation domain leaderboard
        - prompt_gaps: Prompts where target brand is NEVER mentioned in period
    """
    # Verify user owns the group
    try:
        await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception:
        raise to_http_exception(GroupNotFoundError(group_id))

    return await dashboard_service.get_dashboard_data(
        group_id=group_id,
        user_id=current_user.id,
        assistant_id=assistant_id,
        period=period,
    )
