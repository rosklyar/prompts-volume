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
    CreateReportRequestBody,
    EnhancedComparisonResponse,
    GenerateReportRequest,
    PromptSelection,
    ReportItemResponse,
    ReportListResponse,
    ReportRequestResponse,
    ReportRequestStatusResponse,
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
    ReportRequestService,
    ReportService,
    SelectionAnalyzerService,
    SelectionPricingService,
    SelectionValidatorService,
    get_comparison_service,
    get_freshness_analyzer,
    get_report_enricher,
    get_report_request_service,
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
from src.brightdata.services.batch_service import BrightDataBatchService
from src.execution.models.api_models import (
    PromptReportData,
    PromptStatus,
    ReportDataResponse,
)

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
ReportRequestServiceDep = Annotated[ReportRequestService, Depends(get_report_request_service)]

# 24-hour freshness threshold
FRESH_THRESHOLD_HOURS = 24


@router.get("/groups/{group_id}/report-data", response_model=ReportDataResponse)
async def get_report_data(
    group_id: int,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
    evals_session: AsyncSession = Depends(get_evals_session),
    prompts_session: AsyncSession = Depends(get_async_session),
    assistant_id: int = Query(default=1, description="AI Assistant ID to filter evaluations"),
):
    """Get simplified report data for report generation UI.

    Returns all prompts in the group with:
    - Latest evaluation (answer) only, not all historical evaluations
    - Simple 3-state status: fresh (<=24h), stale (>24h), absent (no data)
    - Queue status for pending executions (via BrightData batches)
    """
    from datetime import timezone

    from src.database.evals_models import (
        PromptEvaluation,
        EvaluationStatus,
    )
    from src.database.models import Prompt, PromptGroupBinding

    # Verify user owns the group
    try:
        await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception:
        raise to_http_exception(GroupNotFoundError(group_id))

    # Get all prompt IDs in the group
    bindings_result = await prompts_session.execute(
        select(PromptGroupBinding.prompt_id)
        .where(PromptGroupBinding.group_id == group_id)
    )
    prompt_ids = list(bindings_result.scalars().all())

    if not prompt_ids:
        return ReportDataResponse(
            group_id=group_id,
            prompts=[],
            total_prompts=0,
            prompts_fresh=0,
            prompts_stale=0,
            prompts_absent=0,
            prompts_pending_execution=0,
            global_queue_size=0,
        )

    # Get prompts
    prompts_result = await prompts_session.execute(
        select(Prompt).where(Prompt.id.in_(prompt_ids))
    )
    prompts_map = {p.id: p for p in prompts_result.scalars().all()}

    # Get all completed evaluations for these prompts filtered by assistant
    # Ordered by completed_at DESC so first in each group is the latest
    evals_result = await evals_session.execute(
        select(PromptEvaluation)
        .where(
            PromptEvaluation.prompt_id.in_(prompt_ids),
            PromptEvaluation.assistant_id == assistant_id,
            PromptEvaluation.status == EvaluationStatus.COMPLETED,
        )
        .order_by(PromptEvaluation.completed_at.desc())
    )
    all_evals = list(evals_result.scalars().all())

    # Get only the latest evaluation per prompt
    latest_eval_by_prompt: dict[int, PromptEvaluation] = {}
    for e in all_evals:
        if e.prompt_id not in latest_eval_by_prompt:
            latest_eval_by_prompt[e.prompt_id] = e

    # Get pending prompt IDs from BrightData batches
    batch_service = BrightDataBatchService(evals_session)
    pending_prompt_ids = await batch_service.get_pending_prompt_ids(prompt_ids)

    # Calculate estimated wait time for pending prompts
    pending_count = len(pending_prompt_ids)
    wait_str = None
    if pending_count > 0:
        wait_seconds = pending_count * settings.brightdata_seconds_per_prompt
        if wait_seconds < 60:
            wait_str = f"~{int(wait_seconds)}s"
        elif wait_seconds < 3600:
            wait_str = f"~{int(wait_seconds / 60)}m"
        else:
            wait_str = f"~{int(wait_seconds / 3600)}h"

    # Build response with simplified 3-state status
    prompts_data: list[PromptReportData] = []
    counts = {
        "fresh": 0,
        "stale": 0,
        "absent": 0,
        "pending": 0,
    }

    from datetime import datetime
    now = datetime.now(timezone.utc)

    for prompt_id in prompt_ids:
        prompt = prompts_map.get(prompt_id)
        if not prompt:
            continue

        latest_eval = latest_eval_by_prompt.get(prompt_id)
        is_pending = prompt_id in pending_prompt_ids

        # Calculate simple 3-state status
        status: PromptStatus
        if latest_eval is None:
            status = "absent"
            counts["absent"] += 1
        else:
            # Calculate age in hours
            age = now - latest_eval.completed_at
            hours_old = age.total_seconds() / 3600
            if hours_old <= FRESH_THRESHOLD_HOURS:
                status = "fresh"
                counts["fresh"] += 1
            else:
                status = "stale"
                counts["stale"] += 1

        if is_pending:
            counts["pending"] += 1

        prompts_data.append(
            PromptReportData(
                prompt_id=prompt_id,
                prompt_text=prompt.prompt_text,
                latest_evaluation_id=latest_eval.id if latest_eval else None,
                latest_evaluation_at=latest_eval.completed_at if latest_eval else None,
                status=status,
                pending_execution=is_pending,
                estimated_wait=wait_str if is_pending else None,
            )
        )

    return ReportDataResponse(
        group_id=group_id,
        prompts=prompts_data,
        total_prompts=len(prompts_data),
        prompts_fresh=counts["fresh"],
        prompts_stale=counts["stale"],
        prompts_absent=counts["absent"],
        prompts_pending_execution=counts["pending"],
        global_queue_size=pending_count,
    )


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
                    ExportCitation(url=c.get("url") or "", text=c.get("text") or "")
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
                ExportCitation(url=c.get("url") or "", text=c.get("text") or "")
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
                ExportCitation(url=c.get("url") or "", text=c.get("text") or "")
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
    brand_name = group.brand["name"] if group.brand else "report"
    safe_brand_name = "".join(
        c if c.isalnum() or c in ("-", "_", " ") else "_" for c in brand_name
    ).strip().replace(" ", "_")
    datetime_str = report.created_at.strftime("%Y-%m-%d_%H-%M")
    filename = f"{safe_brand_name}_{datetime_str}.json"
    return Response(
        content=json_bytes,
        media_type=json_formatter.content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# Report Request endpoints (unified manual/scheduled)
# =============================================================================


def _request_to_response(request) -> ReportRequestResponse:
    """Convert ReportRequest model to API response."""
    return ReportRequestResponse(
        id=request.id,
        group_id=request.group_id,
        status=request.status.value,
        assistant_id=request.assistant_id,
        total_prompts=request.total_prompts,
        prompts_fresh_at_request=request.prompts_fresh_at_request,
        prompts_requested=request.prompts_requested,
        report_id=request.report_id,
        created_at=request.created_at,
        timeout_at=request.timeout_at,
        completed_at=request.completed_at,
    )


@router.post("/groups/{group_id}/request", response_model=ReportRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_report_request(
    group_id: int,
    request_body: CreateReportRequestBody,
    current_user: CurrentUser,
    request_service: ReportRequestServiceDep,
    group_service: PromptGroupServiceDep,
):
    """Create a new report request for a group.

    This triggers BrightData for stale/absent prompts and waits for completion.
    The report is auto-generated when all data is ready (or on 6-hour timeout).

    Returns 409 if there's already a pending request for this group.
    """
    # Verify user owns the group
    try:
        await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception:
        raise to_http_exception(GroupNotFoundError(group_id))

    # Check for existing pending request
    existing = await request_service.get_pending_request(group_id, current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "A report request is already pending for this group",
                "existing_request_id": existing.id,
                "existing_status": existing.status.value,
            },
        )

    # Create new request
    report_request = await request_service.create_request(
        group_id=group_id,
        user_id=current_user.id,
        assistant_id=request_body.assistant_id,
    )

    return _request_to_response(report_request)


@router.get("/groups/{group_id}/request-status", response_model=ReportRequestStatusResponse)
async def get_report_request_status(
    group_id: int,
    current_user: CurrentUser,
    request_service: ReportRequestServiceDep,
    group_service: PromptGroupServiceDep,
):
    """Get the status of any pending report request for this group.

    Used by the frontend to show badge on GroupCard.
    """
    # Verify user owns the group
    try:
        await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception:
        raise to_http_exception(GroupNotFoundError(group_id))

    pending = await request_service.get_pending_request(group_id, current_user.id)

    if pending is None:
        return ReportRequestStatusResponse(has_pending=False)

    return ReportRequestStatusResponse(
        has_pending=True,
        request=_request_to_response(pending),
    )


@router.delete("/groups/{group_id}/request", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_report_request(
    group_id: int,
    current_user: CurrentUser,
    request_service: ReportRequestServiceDep,
    group_service: PromptGroupServiceDep,
):
    """Cancel a pending report request for this group.

    Returns 404 if no pending request exists.
    """
    # Verify user owns the group
    try:
        await group_service.get_by_id_for_user(group_id, current_user.id)
    except Exception:
        raise to_http_exception(GroupNotFoundError(group_id))

    pending = await request_service.get_pending_request(group_id, current_user.id)
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending report request for this group",
        )

    cancelled = await request_service.cancel_request(pending.id, current_user.id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Request could not be cancelled (already completed or failed)",
        )
