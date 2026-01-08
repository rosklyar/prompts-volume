"""API router for report operations."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.deps import CurrentUser
from src.config.settings import settings
from src.database.evals_session import get_evals_session
from src.database.session import get_async_session
from src.prompt_groups.exceptions import GroupNotFoundError, to_http_exception
from src.prompt_groups.services import PromptGroupService, get_prompt_group_service
from src.reports.models.api_models import (
    ComparisonResponse,
    EnhancedComparisonResponse,
    GenerateReportRequest,
    PromptSelection,
    ReportItemResponse,
    ReportListResponse,
    ReportPreviewResponse,
    ReportResponse,
    ReportStatistics,
    ReportSummaryResponse,
    SelectableComparisonResponse,
    SelectiveGenerateReportRequest,
)
from src.reports.models.export_models import (
    ExportAnswer,
    ExportCitation,
    ExportPromptItem,
    ExportReportMeta,
)
from src.reports.services import (
    BrandInput,
    ComparisonService,
    DomainInput,
    FreshnessAnalyzerService,
    ReportEnricher,
    ReportService,
    SelectionAnalyzerService,
    SelectionPricingService,
    SelectionValidatorService,
    get_comparison_service,
    get_freshness_analyzer,
    get_report_enricher,
    get_report_service,
    get_selection_analyzer,
    get_selection_pricing,
    get_selection_validator,
)
from src.reports.services.export import (
    JsonExportFormatter,
    ReportExportService,
    get_json_formatter,
    get_report_export_service,
)
from src.execution.models.api_models import (
    EvaluationOption,
    PromptReportData,
    ReportDataResponse,
)
from src.execution.models.domain import FreshnessCategory
from src.execution.services.execution_queue_service import ExecutionQueueService
from src.execution.services.freshness_service import FreshnessService

router = APIRouter(prefix="/reports/api/v1", tags=["reports"])

ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
ComparisonServiceDep = Annotated[ComparisonService, Depends(get_comparison_service)]
PromptGroupServiceDep = Annotated[PromptGroupService, Depends(get_prompt_group_service)]
ReportEnricherDep = Annotated[ReportEnricher, Depends(get_report_enricher)]
FreshnessAnalyzerDep = Annotated[FreshnessAnalyzerService, Depends(get_freshness_analyzer)]
SelectionAnalyzerDep = Annotated[SelectionAnalyzerService, Depends(get_selection_analyzer)]
SelectionPricingDep = Annotated[SelectionPricingService, Depends(get_selection_pricing)]
SelectionValidatorDep = Annotated[SelectionValidatorService, Depends(get_selection_validator)]
ReportExportServiceDep = Annotated[ReportExportService, Depends(get_report_export_service)]
JsonFormatterDep = Annotated[JsonExportFormatter, Depends(get_json_formatter)]


def get_execution_queue_service(
    evals_session=Depends(lambda: None),  # Will be injected in endpoint
    prompts_session=Depends(lambda: None),
) -> ExecutionQueueService:
    """Dependency will be created in endpoint with proper sessions."""
    raise NotImplementedError("Use in endpoint")


def get_freshness_service() -> FreshnessService:
    """Dependency injection for FreshnessService."""
    return FreshnessService(
        fresh_threshold_hours=settings.freshness_fresh_threshold_hours,
        stale_threshold_hours=settings.freshness_stale_threshold_hours,
    )


FreshnessServiceDep = Annotated[FreshnessService, Depends(get_freshness_service)]


@router.get("/groups/{group_id}/report-data", response_model=ReportDataResponse)
async def get_report_data(
    group_id: int,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
    freshness_service: FreshnessServiceDep,
    evals_session: AsyncSession = Depends(get_evals_session),
    prompts_session: AsyncSession = Depends(get_async_session),
):
    """Get report data for the new report generation UI.

    Returns all prompts in the group with:
    - Available evaluations (answers) with timestamps
    - Freshness category and default selection logic
    - Queue status for pending executions
    - Billing info (whether user already paid for each evaluation)
    """
    from src.database.evals_models import (
        ConsumedEvaluation,
        ExecutionQueue,
        ExecutionQueueStatus,
        PromptEvaluation,
        EvaluationStatus,
    )
    from src.database.models import Prompt, PromptGroupBinding

    # Verify user owns the group
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception:
        raise to_http_exception(GroupNotFoundError(group_id))

    user_id = str(current_user.id)

    # Get all prompt IDs in the group
    bindings_result = await prompts_session.execute(
        select(PromptGroupBinding.prompt_id)
        .where(PromptGroupBinding.group_id == group_id)
    )
    prompt_ids = list(bindings_result.scalars().all())

    if not prompt_ids:
        queue_service = ExecutionQueueService(
            evals_session, prompts_session, settings.evaluation_timeout_hours
        )
        global_queue_size = await queue_service.get_pending_count()
        return ReportDataResponse(
            group_id=group_id,
            prompts=[],
            total_prompts=0,
            prompts_with_data=0,
            prompts_fresh=0,
            prompts_stale=0,
            prompts_very_stale=0,
            prompts_no_data=0,
            prompts_pending_execution=0,
            global_queue_size=global_queue_size,
        )

    # Get prompts
    prompts_result = await prompts_session.execute(
        select(Prompt).where(Prompt.id.in_(prompt_ids))
    )
    prompts_map = {p.id: p for p in prompts_result.scalars().all()}

    # Get all completed evaluations for these prompts
    evals_result = await evals_session.execute(
        select(PromptEvaluation)
        .where(
            PromptEvaluation.prompt_id.in_(prompt_ids),
            PromptEvaluation.status == EvaluationStatus.COMPLETED,
        )
        .order_by(PromptEvaluation.completed_at.desc())
    )
    all_evals = list(evals_result.scalars().all())

    # Group evaluations by prompt_id
    evals_by_prompt: dict[int, list[PromptEvaluation]] = {}
    for e in all_evals:
        if e.prompt_id not in evals_by_prompt:
            evals_by_prompt[e.prompt_id] = []
        evals_by_prompt[e.prompt_id].append(e)

    # Get consumed evaluations for this user
    consumed_result = await evals_session.execute(
        select(ConsumedEvaluation.evaluation_id)
        .where(ConsumedEvaluation.user_id == user_id)
    )
    consumed_eval_ids = set(consumed_result.scalars().all())

    # Get pending/in_progress queue entries for these prompts
    queue_result = await evals_session.execute(
        select(ExecutionQueue.prompt_id)
        .where(
            ExecutionQueue.prompt_id.in_(prompt_ids),
            ExecutionQueue.status.in_([
                ExecutionQueueStatus.PENDING,
                ExecutionQueueStatus.IN_PROGRESS,
            ]),
        )
    )
    pending_prompt_ids = set(queue_result.scalars().all())

    # Get global queue size
    queue_service = ExecutionQueueService(
        evals_session, prompts_session, settings.evaluation_timeout_hours
    )
    global_queue_size = await queue_service.get_pending_count()
    wait_str = freshness_service.format_wait_time(
        freshness_service.estimate_wait_time_seconds(global_queue_size)
    )

    # Build response
    prompts_data: list[PromptReportData] = []
    counts = {
        "fresh": 0,
        "stale": 0,
        "very_stale": 0,
        "none": 0,
        "with_data": 0,
        "pending": 0,
    }

    for prompt_id in prompt_ids:
        prompt = prompts_map.get(prompt_id)
        if not prompt:
            continue

        prompt_evals = evals_by_prompt.get(prompt_id, [])
        is_pending = prompt_id in pending_prompt_ids

        # Build evaluation options
        eval_options = [
            EvaluationOption(
                evaluation_id=e.id,
                completed_at=e.completed_at,
                is_consumed=e.id in consumed_eval_ids,
            )
            for e in prompt_evals
        ]

        # Get freshness info
        latest_eval = prompt_evals[0] if prompt_evals else None
        freshness_info = freshness_service.categorize(
            latest_evaluation_at=latest_eval.completed_at if latest_eval else None,
            latest_evaluation_id=latest_eval.id if latest_eval else None,
        )

        # Update counts
        if freshness_info.category == FreshnessCategory.FRESH:
            counts["fresh"] += 1
            counts["with_data"] += 1
        elif freshness_info.category == FreshnessCategory.STALE:
            counts["stale"] += 1
            counts["with_data"] += 1
        elif freshness_info.category == FreshnessCategory.VERY_STALE:
            counts["very_stale"] += 1
            counts["with_data"] += 1
        else:
            counts["none"] += 1

        if is_pending:
            counts["pending"] += 1

        # Check if latest is consumed
        is_consumed = latest_eval.id in consumed_eval_ids if latest_eval else False

        prompts_data.append(
            PromptReportData(
                prompt_id=prompt_id,
                prompt_text=prompt.prompt_text,
                evaluations=eval_options,
                freshness_category=freshness_info.category,
                hours_since_latest=freshness_info.hours_since_latest,
                default_evaluation_id=freshness_info.default_evaluation_id,
                show_ask_for_fresh=freshness_info.show_ask_for_fresh,
                auto_ask_for_fresh=freshness_info.auto_ask_for_fresh,
                pending_execution=is_pending,
                estimated_wait=wait_str if is_pending else None,
                is_consumed=is_consumed,
            )
        )

    return ReportDataResponse(
        group_id=group_id,
        prompts=prompts_data,
        total_prompts=len(prompts_data),
        prompts_with_data=counts["with_data"],
        prompts_fresh=counts["fresh"],
        prompts_stale=counts["stale"],
        prompts_very_stale=counts["very_stale"],
        prompts_no_data=counts["none"],
        prompts_pending_execution=counts["pending"],
        global_queue_size=global_queue_size,
    )


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
    request: SelectiveGenerateReportRequest,
    current_user: CurrentUser,
    report_service: ReportServiceDep,
    group_service: PromptGroupServiceDep,
    selection_analyzer: SelectionAnalyzerDep,
    selection_validator: SelectionValidatorDep,
    enricher: ReportEnricherDep,
    export_service: ReportExportServiceDep,
):
    """Generate a report with explicit evaluation selections.

    Accepts user's selections of which evaluation to include per prompt.
    Charges only for fresh (not previously consumed) selected evaluations.
    Returns enriched data with brand mentions and citation leaderboard.
    """
    # Verify user owns the group and get group data for brands
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception as e:
        raise to_http_exception(GroupNotFoundError(group_id))

    # Get latest report for validation
    latest_report = await report_service.get_latest_report(group_id, current_user.id)

    # Get available options for validation
    prompt_selection_info = await selection_analyzer.analyze_selections(
        group_id=group_id,
        user_id=current_user.id,
        last_report=latest_report,
    )

    # Validate user's selections
    validation = selection_validator.validate_selections(
        selections=request.selections,
        prompt_selection_info=prompt_selection_info,
        use_defaults_for_unspecified=request.use_defaults_for_unspecified,
    )

    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": validation.errors},
        )

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

    # Generate report with validated selections
    report = await report_service.generate_report_with_selections(
        group_id=group_id,
        user_id=current_user.id,
        selections=validation.normalized_selections,
        title=request.title,
        brand_snapshot=group.brand,
        competitors_snapshot=group.competitors,
    )

    # Get full report with items
    result = await report_service.get_report(report.id, current_user.id)

    items = []
    all_answers = []
    brand_mentions_per_item = []
    domain_mentions_per_item = []
    export_items = []

    if result:
        full_report = result["report"]
        prompts_map = result["prompts_map"]
        for item in full_report.items:
            answer = item.evaluation.answer if item.evaluation else None
            all_answers.append(answer)

            # Get response text for detection
            response_text = answer.get("response") if answer else None

            # Detect brand mentions if we have brands and response text
            # None = no answer, [] = answer but no mentions (important for visibility calc)
            brand_mentions = None
            if brands and response_text:
                brand_mentions = enricher.detect_brand_mentions(response_text, brands)

            # Detect domain mentions if we have domains and response text
            domain_mentions = None
            if domains and response_text:
                domain_mentions = enricher.detect_domain_mentions(response_text, domains)

            # Collect for statistics calculation
            brand_mentions_per_item.append(brand_mentions)
            domain_mentions_per_item.append(domain_mentions)

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

            # Build export item for statistics calculation
            export_answer = None
            if answer:
                citations = [
                    ExportCitation(url=c.get("url", ""), text=c.get("text", ""))
                    for c in answer.get("citations", [])
                    if isinstance(c, dict)
                ]
                export_answer = ExportAnswer(
                    response=answer.get("response", ""),
                    citations=citations,
                )
            export_items.append(
                ExportPromptItem(
                    prompt_id=item.prompt_id,
                    prompt_text=prompt.prompt_text if prompt else "",
                    answer=export_answer,
                    status=item.status.value,
                )
            )

    # Build citation leaderboard from all answers
    citation_leaderboard = enricher.build_citation_leaderboard(all_answers)

    # Calculate statistics
    stats_result = export_service._calculate_statistics(
        items=export_items,
        brand_mentions_per_item=brand_mentions_per_item,
        domain_mentions_per_item=domain_mentions_per_item,
        citation_leaderboard=citation_leaderboard,
        brand_config=group.brand,
        competitors_config=group.competitors,
    )

    statistics = ReportStatistics(
        brand_visibility=stats_result.brand_visibility,
        domain_mentions=stats_result.domain_mentions,
        citation_domains=stats_result.citation_domains,
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
        citation_leaderboard=citation_leaderboard,
        statistics=statistics,
        brand_snapshot=report.brand_snapshot,
        competitors_snapshot=report.competitors_snapshot,
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
    export_service: ReportExportServiceDep,
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
    brand_mentions_per_item = []
    domain_mentions_per_item = []
    export_items = []

    for item in report.items:
        answer = item.evaluation.answer if item.evaluation else None
        all_answers.append(answer)

        # Get response text for detection
        response_text = answer.get("response") if answer else None

        # Detect brand mentions if we have brands and response text
        # None = no answer, [] = answer but no mentions (important for visibility calc)
        brand_mentions = None
        if brands and response_text:
            brand_mentions = enricher.detect_brand_mentions(response_text, brands)

        # Detect domain mentions if we have domains and response text
        domain_mentions = None
        if domains and response_text:
            domain_mentions = enricher.detect_domain_mentions(response_text, domains)

        # Collect for statistics calculation
        brand_mentions_per_item.append(brand_mentions)
        domain_mentions_per_item.append(domain_mentions)

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

        # Build export item for statistics calculation
        export_answer = None
        if answer:
            citations = [
                ExportCitation(url=c.get("url", ""), text=c.get("text", ""))
                for c in answer.get("citations", [])
                if isinstance(c, dict)
            ]
            export_answer = ExportAnswer(
                response=answer.get("response", ""),
                citations=citations,
            )
        export_items.append(
            ExportPromptItem(
                prompt_id=item.prompt_id,
                prompt_text=prompt.prompt_text if prompt else "",
                answer=export_answer,
                status=item.status.value,
            )
        )

    # Build citation leaderboard from all answers
    citation_leaderboard = enricher.build_citation_leaderboard(all_answers)

    # Calculate statistics
    stats_result = export_service._calculate_statistics(
        items=export_items,
        brand_mentions_per_item=brand_mentions_per_item,
        domain_mentions_per_item=domain_mentions_per_item,
        citation_leaderboard=citation_leaderboard,
        brand_config=group.brand,
        competitors_config=group.competitors,
    )

    statistics = ReportStatistics(
        brand_visibility=stats_result.brand_visibility,
        domain_mentions=stats_result.domain_mentions,
        citation_domains=stats_result.citation_domains,
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
        citation_leaderboard=citation_leaderboard,
        statistics=statistics,
        brand_snapshot=report.brand_snapshot,
        competitors_snapshot=report.competitors_snapshot,
    )


@router.get("/groups/{group_id}/compare", response_model=SelectableComparisonResponse)
async def compare_with_latest_report(
    group_id: int,
    current_user: CurrentUser,
    report_service: ReportServiceDep,
    group_service: PromptGroupServiceDep,
    selection_analyzer: SelectionAnalyzerDep,
    selection_pricing: SelectionPricingDep,
):
    """Get selectable evaluation options for report preview.

    Returns per-prompt selection info with:
    - Available fresher evaluations for each prompt (with assistant info and dates)
    - Default selection (most recent fresher evaluation)
    - Pricing based on default selections
    - Brand change detection
    - Generation button state
    """
    # Get group with brand/competitors
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception as e:
        raise to_http_exception(GroupNotFoundError(group_id))

    # Get latest report
    latest_report = await report_service.get_latest_report(group_id, current_user.id)

    # Analyze selections for all prompts
    prompt_selections = await selection_analyzer.analyze_selections(
        group_id=group_id,
        user_id=current_user.id,
        last_report=latest_report,
    )

    # Calculate stats
    total_prompts = len(prompt_selections)
    prompts_with_options = sum(
        1 for ps in prompt_selections if ps.available_options
    )
    prompts_awaiting = total_prompts - prompts_with_options

    # Get default selections (non-None)
    default_eval_ids = [
        ps.default_selection
        for ps in prompt_selections
        if ps.default_selection is not None
    ]

    # Calculate pricing for default selections
    pricing_result = await selection_pricing.calculate_price(
        user_id=current_user.id,
        evaluation_ids=default_eval_ids,
    )

    # Get user balance via preview
    price_per = Decimal(str(settings.billing_price_per_evaluation))
    preview = await report_service.preview_report(
        group_id=group_id,
        user_id=current_user.id,
        price_per_evaluation=price_per,
    )

    # Detect brand/competitors changes
    brand_changes = report_service.detect_brand_changes(
        current_brand=group.brand,
        current_competitors=group.competitors,
        last_report=latest_report,
    )

    # Determine if generation should be enabled
    # Enable only if there's fresh evaluation data
    # Brand/competitor changes don't require new reports - statistics are recalculated on-the-fly
    can_generate = pricing_result.fresh_count > 0
    generation_disabled_reason = None if can_generate else "no_new_data"

    return SelectableComparisonResponse(
        group_id=group_id,
        last_report_at=latest_report.created_at if latest_report else None,
        prompt_selections=prompt_selections,
        total_prompts=total_prompts,
        prompts_with_options=prompts_with_options,
        prompts_awaiting=prompts_awaiting,
        brand_changes=brand_changes,
        default_selection_count=len(default_eval_ids),
        default_fresh_count=pricing_result.fresh_count,
        default_estimated_cost=pricing_result.total_cost,
        user_balance=preview["user_balance"],
        price_per_evaluation=price_per,
        can_generate=can_generate,
        generation_disabled_reason=generation_disabled_reason,
    )


@router.get(
    "/groups/{group_id}/reports/{report_id}/export/json",
    response_class=Response,
    responses={
        200: {
            "content": {"application/json": {}},
            "description": "JSON export of the report with all statistics",
        }
    },
)
async def export_report_json(
    group_id: int,
    report_id: int,
    current_user: CurrentUser,
    report_service: ReportServiceDep,
    group_service: PromptGroupServiceDep,
    enricher: ReportEnricherDep,
    export_service: ReportExportServiceDep,
    json_formatter: JsonFormatterDep,
):
    """
    Export a report as JSON with all statistics calculated.

    Returns a downloadable JSON file containing:
    - Report metadata
    - Brand/competitor configuration
    - All prompts with answers and citations
    - Calculated statistics (visibility, mentions, citation domains)
    - Citation leaderboards
    """
    # Verify user owns the group and get group data for brands
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception:
        raise to_http_exception(GroupNotFoundError(group_id))

    # Get report with items
    result = await report_service.get_report(report_id, current_user.id)
    if not result or result["report"].group_id != group_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    report = result["report"]
    prompts_map = result["prompts_map"]

    # Extract brand and competitors from group for detection
    brands = None
    domains = []
    if group.brand:
        brands = [
            BrandInput(
                name=group.brand["name"], variations=group.brand.get("variations", [])
            )
        ]
        if group.brand.get("domain"):
            domains.append(
                DomainInput(
                    name=group.brand["name"],
                    domain=group.brand["domain"],
                    is_brand=True,
                )
            )
        if group.competitors:
            brands.extend(
                BrandInput(name=c["name"], variations=c.get("variations", []))
                for c in group.competitors
            )
            for c in group.competitors:
                if c.get("domain"):
                    domains.append(
                        DomainInput(
                            name=c["name"],
                            domain=c["domain"],
                            is_brand=False,
                        )
                    )

    # Build export items and collect mentions
    export_items = []
    brand_mentions_per_item = []
    domain_mentions_per_item = []
    all_answers = []

    for item in report.items:
        answer = item.evaluation.answer if item.evaluation else None
        all_answers.append(answer)
        response_text = answer.get("response") if answer else None

        # Build export answer
        export_answer = None
        if answer:
            citations = [
                ExportCitation(url=c.get("url", ""), text=c.get("text", ""))
                for c in answer.get("citations", [])
                if isinstance(c, dict)
            ]
            export_answer = ExportAnswer(
                response=answer.get("response", ""),
                citations=citations,
            )

        # Detect brand mentions
        # None = no answer, [] = answer but no mentions (important for visibility calc)
        brand_mentions = None
        if brands and response_text:
            brand_mentions = enricher.detect_brand_mentions(response_text, brands)
        brand_mentions_per_item.append(brand_mentions)

        # Detect domain mentions
        domain_mentions = None
        if domains and response_text:
            domain_mentions = enricher.detect_domain_mentions(response_text, domains)
        domain_mentions_per_item.append(domain_mentions)

        prompt = prompts_map.get(item.prompt_id)
        export_items.append(
            ExportPromptItem(
                prompt_id=item.prompt_id,
                prompt_text=prompt.prompt_text if prompt else "",
                answer=export_answer,
                status=item.status.value,
            )
        )

    # Build citation leaderboard from all answers
    citation_leaderboard = enricher.build_citation_leaderboard(all_answers)

    # Build report metadata
    report_meta = ExportReportMeta(
        id=report.id,
        title=report.title,
        created_at=report.created_at,
        group_id=report.group_id,
        total_prompts=report.total_prompts,
        prompts_with_data=report.prompts_with_data,
        prompts_awaiting=report.prompts_awaiting,
        total_cost=report.total_cost,
    )

    # Build export
    export_data = export_service.build_export(
        report_meta=report_meta,
        items=export_items,
        brand_mentions_per_item=brand_mentions_per_item,
        domain_mentions_per_item=domain_mentions_per_item,
        citation_leaderboard=citation_leaderboard,
        brand_config=group.brand,
        competitors_config=group.competitors,
    )

    # Format as JSON
    json_bytes = json_formatter.format(export_data)

    # Return as downloadable file
    filename = f"report_{report_id}_{report.created_at.strftime('%Y%m%d')}.json"
    return Response(
        content=json_bytes,
        media_type=json_formatter.content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
