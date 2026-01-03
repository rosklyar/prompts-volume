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
    EnhancedComparisonResponse,
    GenerateReportRequest,
    ReportItemResponse,
    ReportListResponse,
    ReportPreviewResponse,
    ReportResponse,
    ReportSummaryResponse,
)
from src.reports.services import (
    BrandInput,
    ComparisonService,
    DomainInput,
    FreshnessAnalyzerService,
    ReportEnricher,
    ReportService,
    get_comparison_service,
    get_freshness_analyzer,
    get_report_enricher,
    get_report_service,
)

router = APIRouter(prefix="/reports/api/v1", tags=["reports"])

ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
ComparisonServiceDep = Annotated[ComparisonService, Depends(get_comparison_service)]
PromptGroupServiceDep = Annotated[PromptGroupService, Depends(get_prompt_group_service)]
ReportEnricherDep = Annotated[ReportEnricher, Depends(get_report_enricher)]
FreshnessAnalyzerDep = Annotated[FreshnessAnalyzerService, Depends(get_freshness_analyzer)]


@router.get(
    "/groups/{group_id}/preview",
    response_model=ReportPreviewResponse,
    deprecated=True,
)
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
    enricher: ReportEnricherDep,
):
    """Generate a report for a prompt group.

    Charges for fresh (not previously consumed) evaluations.
    Already-consumed evaluations are included for free.
    Returns enriched data with brand mentions and citation leaderboard.
    """
    # Verify user owns the group and get group data for brands
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception as e:
        raise to_http_exception(GroupNotFoundError(group_id))

    # Extract brand and competitors from group for brand mention detection
    brands = None
    domains = []
    if group.brand:
        brands = [BrandInput(name=group.brand["name"], variations=group.brand.get("variations", []))]
        if group.brand.get("domain"):
            domains.append(DomainInput(
                name=group.brand["name"],
                domain=group.brand["domain"],
                is_brand=True,
            ))
        if group.competitors:
            brands.extend(
                BrandInput(name=c["name"], variations=c.get("variations", []))
                for c in group.competitors
            )
            for c in group.competitors:
                if c.get("domain"):
                    domains.append(DomainInput(
                        name=c["name"],
                        domain=c["domain"],
                        is_brand=False,
                    ))

    report = await report_service.generate_report(
        group_id=group_id,
        user_id=current_user.id,
        title=request.title,
        include_previous=request.include_previous,
        brand_snapshot=group.brand,
        competitors_snapshot=group.competitors,
    )

    # Get full report with items
    result = await report_service.get_report(report.id, current_user.id)

    items = []
    all_answers = []
    if result:
        full_report = result["report"]
        prompts_map = result["prompts_map"]
        for item in full_report.items:
            answer = item.evaluation.answer if item.evaluation else None
            all_answers.append(answer)

            # Get response text for detection
            response_text = answer.get("response") if answer else None

            # Detect brand mentions if we have brands and response text
            brand_mentions = None
            if brands and response_text:
                brand_mentions = enricher.detect_brand_mentions(response_text, brands)
                if not brand_mentions:
                    brand_mentions = None

            # Detect domain mentions if we have domains and response text
            domain_mentions = None
            if domains and response_text:
                domain_mentions = enricher.detect_domain_mentions(response_text, domains)
                if not domain_mentions:
                    domain_mentions = None

            prompt = prompts_map.get(item.prompt_id)
            items.append(
                ReportItemResponse(
                    prompt_id=item.prompt_id,
                    prompt_text=prompt.prompt_text if prompt else "",
                    evaluation_id=item.evaluation_id,
                    status=item.status.value,
                    is_fresh=item.is_fresh,
                    amount_charged=item.amount_charged,
                    answer=answer,
                    brand_mentions=brand_mentions,
                    domain_mentions=domain_mentions,
                )
            )

    # Build citation leaderboard from all answers
    citation_leaderboard = enricher.build_citation_leaderboard(all_answers)

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
        citation_leaderboard=citation_leaderboard,
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
    enricher: ReportEnricherDep,
):
    """Get a specific report with all items, enriched with brand mentions and citations."""
    # Verify user owns the group and get group data for brands
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception as e:
        raise to_http_exception(GroupNotFoundError(group_id))

    result = await report_service.get_report(report_id, current_user.id)
    if not result or result["report"].group_id != group_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    report = result["report"]
    prompts_map = result["prompts_map"]

    # Extract brand and competitors from group for brand mention detection
    brands = None
    domains = []
    if group.brand:
        brands = [BrandInput(name=group.brand["name"], variations=group.brand.get("variations", []))]
        if group.brand.get("domain"):
            domains.append(DomainInput(
                name=group.brand["name"],
                domain=group.brand["domain"],
                is_brand=True,
            ))
        if group.competitors:
            brands.extend(
                BrandInput(name=c["name"], variations=c.get("variations", []))
                for c in group.competitors
            )
            for c in group.competitors:
                if c.get("domain"):
                    domains.append(DomainInput(
                        name=c["name"],
                        domain=c["domain"],
                        is_brand=False,
                    ))

    items = []
    all_answers = []
    for item in report.items:
        answer = item.evaluation.answer if item.evaluation else None
        all_answers.append(answer)

        # Get response text for detection
        response_text = answer.get("response") if answer else None

        # Detect brand mentions if we have brands and response text
        brand_mentions = None
        if brands and response_text:
            brand_mentions = enricher.detect_brand_mentions(response_text, brands)
            if not brand_mentions:
                brand_mentions = None

        # Detect domain mentions if we have domains and response text
        domain_mentions = None
        if domains and response_text:
            domain_mentions = enricher.detect_domain_mentions(response_text, domains)
            if not domain_mentions:
                domain_mentions = None

        prompt = prompts_map.get(item.prompt_id)
        items.append(
            ReportItemResponse(
                prompt_id=item.prompt_id,
                prompt_text=prompt.prompt_text if prompt else "",
                evaluation_id=item.evaluation_id,
                status=item.status.value,
                is_fresh=item.is_fresh,
                amount_charged=item.amount_charged,
                answer=answer,
                brand_mentions=brand_mentions,
                domain_mentions=domain_mentions,
            )
        )

    # Build citation leaderboard from all answers
    citation_leaderboard = enricher.build_citation_leaderboard(all_answers)

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
        citation_leaderboard=citation_leaderboard,
    )


@router.get("/groups/{group_id}/compare", response_model=EnhancedComparisonResponse)
async def compare_with_latest_report(
    group_id: int,
    current_user: CurrentUser,
    report_service: ReportServiceDep,
    comparison_service: ComparisonServiceDep,
    group_service: PromptGroupServiceDep,
    freshness_analyzer: FreshnessAnalyzerDep,
):
    """Enhanced comparison with per-prompt freshness and brand change detection.

    Returns detailed information about:
    - Per-prompt freshness (which prompts have newer answers than last report)
    - Brand/competitors change detection
    - Cost estimation
    - Whether generation should be enabled
    """
    # Get group with brand/competitors
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)
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

    # Calculate fresh evaluations (not consumed)
    fresh_count = len(evaluation_ids) - len(consumed_ids)
    price_per = Decimal(str(settings.billing_price_per_evaluation))
    estimated_cost = price_per * fresh_count

    # Get user balance via preview
    preview = await report_service.preview_report(
        group_id=group_id,
        user_id=current_user.id,
        price_per_evaluation=price_per,
    )

    # Analyze per-prompt freshness
    prompt_freshness = await freshness_analyzer.analyze_freshness(
        group_id=group_id,
        last_report=latest_report,
    )
    prompts_with_fresher_answers = sum(
        1 for pf in prompt_freshness if pf.has_fresher_answer
    )

    # Detect brand/competitors changes
    brand_changes = report_service.detect_brand_changes(
        current_brand=group.brand,
        current_competitors=group.competitors,
        last_report=latest_report,
    )

    # Determine if generation should be enabled
    can_generate = (
        prompts_with_fresher_answers > 0
        or fresh_count > 0
        or brand_changes.brand_changed
        or brand_changes.competitors_changed
    )
    generation_disabled_reason = None if can_generate else "no_new_data_or_changes"

    return EnhancedComparisonResponse(
        group_id=group_id,
        last_report_at=latest_report.created_at if latest_report else None,
        current_prompts_count=len(prompt_ids),
        current_evaluations_count=len(evaluation_ids),
        new_prompts_added=(
            len(prompt_ids) - latest_report.total_prompts
            if latest_report
            else len(prompt_ids)
        ),
        prompts_with_fresher_answers=prompts_with_fresher_answers,
        prompt_freshness=prompt_freshness,
        brand_changes=brand_changes,
        fresh_evaluations=fresh_count,
        already_consumed=len(consumed_ids),
        estimated_cost=estimated_cost,
        user_balance=preview["user_balance"],
        affordable_count=preview["affordable_count"],
        needs_top_up=preview["needs_top_up"],
        can_generate=can_generate,
        generation_disabled_reason=generation_disabled_reason,
    )
