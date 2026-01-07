"""API router for report operations."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from src.auth.deps import CurrentUser
from src.config.settings import settings
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
