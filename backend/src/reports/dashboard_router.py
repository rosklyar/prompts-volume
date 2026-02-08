"""API router for dashboard operations."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.deps import CurrentUser
from src.database.evals_session import get_evals_session
from src.database.session import get_async_session
from src.prompt_groups.exceptions import GroupNotFoundError, to_http_exception
from src.prompt_groups.services import PromptGroupService, get_prompt_group_service
from src.reports.models.dashboard_models import DashboardResponse
from src.reports.services.dashboard_service import DashboardService
from src.reports.services.results_enricher import ReportEnricher, get_report_enricher
from src.reports.utils.date_range import (
    DateRangeValidationError,
    resolve_date_range,
)

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
    period: Literal["1d", "7d", "30d"] | None = Query(
        default=None, description="Preset time period (1d, 7d, 30d)"
    ),
    from_date: datetime | None = Query(
        default=None, description="Custom start date (ISO 8601, inclusive)"
    ),
    to_date: datetime | None = Query(
        default=None, description="Custom end date (ISO 8601, exclusive)"
    ),
):
    """Get dashboard analytics aggregated across reports in a time period.

    Returns brand visibility metrics, competitor rankings, citation sources,
    and prompt gaps aggregated from all reports within the specified time period.

    Supports two modes:
    - Preset period: Use `period` parameter (1d, 7d, 30d)
    - Custom date range: Use `from_date` and `to_date` parameters
    - Default: Last 30 days if no parameters provided

    Cannot mix period with from_date/to_date.

    Args:
        group_id: The prompt group ID
        assistant_id: The AI assistant ID (required)
        period: Preset time period (mutually exclusive with from_date/to_date)
        from_date: Custom start date (requires to_date)
        to_date: Custom end date (requires from_date)

    Returns:
        DashboardResponse with:
        - from_date/to_date: The resolved date range
        - preset_used: Which preset was used, if any
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

    # Resolve date range from parameters
    try:
        date_range = resolve_date_range(
            period=period,
            from_date=from_date,
            to_date=to_date,
            default_days=30,
        )
    except DateRangeValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return await dashboard_service.get_dashboard_data(
        group_id=group_id,
        user_id=current_user.id,
        assistant_id=assistant_id,
        from_date=date_range.from_date,
        to_date=date_range.to_date,
        preset_used=date_range.preset_used,
    )
