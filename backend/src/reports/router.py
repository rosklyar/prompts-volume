"""API router for report operations."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.auth.deps import CurrentUser
from src.config.settings import settings
from src.prompt_groups.exceptions import GroupNotFoundError, to_http_exception
from src.prompt_groups.services import PromptGroupService, get_prompt_group_service
from src.reports.models.api_models import (
    ComparisonResponse,
    GenerateReportRequest,
    ReportItemResponse,
    ReportListResponse,
    ReportPreviewResponse,
    ReportResponse,
    ReportSummaryResponse,
)
from src.reports.services import (
    ComparisonService,
    ReportService,
    get_comparison_service,
    get_report_service,
)

router = APIRouter(prefix="/reports/api/v1", tags=["reports"])

ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
ComparisonServiceDep = Annotated[ComparisonService, Depends(get_comparison_service)]
PromptGroupServiceDep = Annotated[PromptGroupService, Depends(get_prompt_group_service)]


@router.get("/groups/{group_id}/preview", response_model=ReportPreviewResponse)
async def preview_report(
    group_id: int,
    current_user: CurrentUser,
    report_service: ReportServiceDep,
    group_service: PromptGroupServiceDep,
):
    """Preview what generating a report would cost.

    Shows how many evaluations are available, how many are fresh (chargeable),
    and whether the user has sufficient balance.
    """
    # Verify user owns the group
    try:
        await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception as e:
        raise to_http_exception(GroupNotFoundError(group_id))

    preview = await report_service.preview_report(
        group_id=group_id,
        user_id=current_user.id,
        price_per_evaluation=Decimal(str(settings.billing_price_per_evaluation)),
    )

    return ReportPreviewResponse(**preview)


@router.post("/groups/{group_id}/generate", response_model=ReportResponse)
async def generate_report(
    group_id: int,
    request: GenerateReportRequest,
    current_user: CurrentUser,
    report_service: ReportServiceDep,
    group_service: PromptGroupServiceDep,
):
    """Generate a report for a prompt group.

    Charges for fresh (not previously consumed) evaluations.
    Already-consumed evaluations are included for free.
    """
    # Verify user owns the group
    try:
        await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception as e:
        raise to_http_exception(GroupNotFoundError(group_id))

    report = await report_service.generate_report(
        group_id=group_id,
        user_id=current_user.id,
        title=request.title,
        include_previous=request.include_previous,
    )

    # Get full report with items
    full_report = await report_service.get_report(report.id, current_user.id)

    items = []
    if full_report and full_report.items:
        for item in full_report.items:
            items.append(
                ReportItemResponse(
                    prompt_id=item.prompt_id,
                    prompt_text=item.prompt.prompt_text if item.prompt else "",
                    evaluation_id=item.evaluation_id,
                    status=item.status.value,
                    is_fresh=item.is_fresh,
                    amount_charged=item.amount_charged,
                    answer=item.evaluation.answer if item.evaluation else None,
                )
            )

    return ReportResponse(
        id=report.id,
        group_id=report.group_id,
        title=report.title,
        created_at=report.created_at,
        total_prompts=report.total_prompts,
        prompts_with_data=report.prompts_with_data,
        prompts_awaiting=report.prompts_awaiting,
        total_evaluations_loaded=report.total_evaluations_loaded,
        total_cost=report.total_cost,
        items=items,
    )


@router.get("/groups/{group_id}/reports", response_model=ReportListResponse)
async def list_reports(
    group_id: int,
    current_user: CurrentUser,
    report_service: ReportServiceDep,
    group_service: PromptGroupServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all reports for a prompt group."""
    # Verify user owns the group
    try:
        await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception as e:
        raise to_http_exception(GroupNotFoundError(group_id))

    reports, total = await report_service.list_reports(
        group_id=group_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    return ReportListResponse(
        reports=[
            ReportSummaryResponse(
                id=r.id,
                group_id=r.group_id,
                title=r.title,
                created_at=r.created_at,
                total_prompts=r.total_prompts,
                prompts_with_data=r.prompts_with_data,
                prompts_awaiting=r.prompts_awaiting,
                total_cost=r.total_cost,
            )
            for r in reports
        ],
        total=total,
    )


@router.get("/groups/{group_id}/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    group_id: int,
    report_id: int,
    current_user: CurrentUser,
    report_service: ReportServiceDep,
    group_service: PromptGroupServiceDep,
):
    """Get a specific report with all items."""
    # Verify user owns the group
    try:
        await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception as e:
        raise to_http_exception(GroupNotFoundError(group_id))

    report = await report_service.get_report(report_id, current_user.id)
    if not report or report.group_id != group_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    items = []
    for item in report.items:
        items.append(
            ReportItemResponse(
                prompt_id=item.prompt_id,
                prompt_text=item.prompt.prompt_text if item.prompt else "",
                evaluation_id=item.evaluation_id,
                status=item.status.value,
                is_fresh=item.is_fresh,
                amount_charged=item.amount_charged,
                answer=item.evaluation.answer if item.evaluation else None,
            )
        )

    return ReportResponse(
        id=report.id,
        group_id=report.group_id,
        title=report.title,
        created_at=report.created_at,
        total_prompts=report.total_prompts,
        prompts_with_data=report.prompts_with_data,
        prompts_awaiting=report.prompts_awaiting,
        total_evaluations_loaded=report.total_evaluations_loaded,
        total_cost=report.total_cost,
        items=items,
    )


@router.get("/groups/{group_id}/compare", response_model=ComparisonResponse)
async def compare_with_latest_report(
    group_id: int,
    current_user: CurrentUser,
    report_service: ReportServiceDep,
    comparison_service: ComparisonServiceDep,
    group_service: PromptGroupServiceDep,
):
    """Compare current data with the latest report.

    Shows how much new data is available since the last report.
    """
    # Verify user owns the group
    try:
        await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception as e:
        raise to_http_exception(GroupNotFoundError(group_id))

    # Get latest report
    latest_report = await report_service.get_latest_report(group_id, current_user.id)

    # Get current state
    prompt_ids = await comparison_service.get_prompt_ids_in_group(group_id)
    evaluation_ids = await comparison_service.get_evaluation_ids_for_prompts(prompt_ids)
    consumed_ids = await comparison_service.get_consumed_evaluation_ids(
        current_user.id, evaluation_ids
    )

    fresh_count = len(evaluation_ids) - len(consumed_ids)
    price_per = Decimal(str(settings.billing_price_per_evaluation))
    estimated_cost = price_per * fresh_count

    # Get user balance
    preview = await report_service.preview_report(
        group_id=group_id,
        user_id=current_user.id,
        price_per_evaluation=price_per,
    )

    return ComparisonResponse(
        group_id=group_id,
        last_report_at=latest_report.created_at if latest_report else None,
        current_prompts_count=len(prompt_ids),
        current_evaluations_count=len(evaluation_ids),
        new_prompts_added=(
            len(prompt_ids) - latest_report.total_prompts
            if latest_report
            else len(prompt_ids)
        ),
        new_evaluations_available=fresh_count,
        fresh_data_count=fresh_count,
        estimated_cost=estimated_cost,
        user_balance=preview["user_balance"],
        affordable_count=preview["affordable_count"],
        needs_top_up=preview["needs_top_up"],
    )
