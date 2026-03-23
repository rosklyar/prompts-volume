"""API router for GEO schema audit."""

import math

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.auth.deps import CurrentUser
from src.database.users_models import GeoAuditResult
from src.geo_audit.exceptions import FetchError
from src.geo_audit.models.api_models import (
    AuditScoreResponse,
    DeprecatedSchemaResponse,
    DetectedSchemaResponse,
    ExtractionResponse,
    GeoAuditRequest,
    GeoAuditResponse,
    GeoAuditStoredResponse,
    GeoReadinessResponse,
    GeoSignalResponse,
    GeneratedTemplateResponse,
    JsRenderingWarningResponse,
    RichResultCheckResponse,
    RichResultGapResponse,
    SameAsLinkResponse,
    ScoreBreakdownResponse,
    ValidationIssueResponse,
    ValidationResponse,
)
from src.geo_audit.models.domain_models import GeoAuditReport
from src.geo_audit.services import GeoAuditOrchestratorDep, GeoAuditServiceDep
from src.onboarding.services import PreferencesServiceDep

router = APIRouter(prefix="/api/v1", tags=["geo-audit"])


@router.get("/geo-audit", response_model=GeoAuditStoredResponse)
async def get_latest_audit(
    current_user: CurrentUser,
    audit_service: GeoAuditServiceDep,
) -> GeoAuditStoredResponse:
    result = await audit_service.get_latest(current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="No audit results found")
    return _to_stored_response(result)


@router.post("/geo-audit", response_model=GeoAuditStoredResponse)
async def run_geo_audit(
    current_user: CurrentUser,
    orchestrator: GeoAuditOrchestratorDep,
    audit_service: GeoAuditServiceDep,
    preferences_service: PreferencesServiceDep,
    body: GeoAuditRequest | None = None,
) -> GeoAuditStoredResponse:
    # 1. Resolve URL
    url = _resolve_url(body)
    if url is None:
        prefs = await preferences_service.get_preferences(current_user.id)
        domain = prefs.default_brand.get("domain") if prefs and prefs.default_brand else None
        if not domain:
            raise HTTPException(
                status_code=400,
                detail="No URL provided and no brand domain found in preferences",
            )
        url = f"https://{domain}"

    # 2. Check cooldown
    retry_after = await audit_service.check_cooldown(current_user.id)
    if retry_after is not None:
        from datetime import datetime, timezone
        seconds = math.ceil((retry_after - datetime.now(timezone.utc)).total_seconds())
        return JSONResponse(
            status_code=429,
            content={"detail": f"Audit cooldown active. Try again in {seconds} seconds."},
            headers={"Retry-After": str(seconds)},
        )

    # 3. Run audit
    try:
        report = await orchestrator.audit(url)
    except FetchError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 4. Convert and persist
    response = _to_response(report)
    stored = await audit_service.save(
        user_id=current_user.id,
        url=url,
        result=response,
    )

    return _to_stored_response(stored)


def _resolve_url(body: GeoAuditRequest | None) -> str | None:
    if body is None or body.url is None:
        return None
    return str(body.url)


def _to_stored_response(row: GeoAuditResult) -> GeoAuditStoredResponse:
    return GeoAuditStoredResponse(
        id=row.id,
        url=row.url,
        score_total=float(row.score_total),
        score_rating=row.score_rating,
        result=GeoAuditResponse(**row.result_json),
        created_at=row.created_at,
    )


def _to_response(report: GeoAuditReport) -> GeoAuditResponse:
    return GeoAuditResponse(
        url=report.url,
        extraction=ExtractionResponse(
            total_blocks=report.extraction.total_blocks,
            formats_found=report.extraction.formats_found,
            schema_types_found=report.extraction.schema_types_found,
            schemas=[
                DetectedSchemaResponse(
                    format=s.format,
                    schema_type=s.schema_type,
                    properties=s.properties,
                )
                for s in report.extraction.schemas
            ],
        ),
        validation=ValidationResponse(
            valid_count=report.validation.valid_count,
            invalid_count=report.validation.invalid_count,
            issues=[
                ValidationIssueResponse(
                    schema_type=i.schema_type,
                    severity=i.severity,
                    field=i.field,
                    message=i.message,
                )
                for i in report.validation.issues
            ],
        ),
        rich_results=RichResultCheckResponse(
            eligible=report.rich_results.eligible,
            gaps=[
                RichResultGapResponse(
                    schema_type=g.schema_type,
                    status=g.status,
                    missing_required=g.missing_required,
                    missing_recommended=g.missing_recommended,
                )
                for g in report.rich_results.gaps
            ],
        ),
        geo_readiness=GeoReadinessResponse(
            signals=[
                GeoSignalResponse(
                    name=s.name,
                    present=s.present,
                    completeness=s.completeness,
                    details=s.details,
                )
                for s in report.geo_readiness.signals
            ],
            same_as_links=[
                SameAsLinkResponse(
                    platform=l.platform,
                    linked=l.linked,
                    url=l.url,
                )
                for l in report.geo_readiness.same_as_links
            ],
            overall_readiness=report.geo_readiness.overall_readiness,
        ),
        deprecated_schemas=[
            DeprecatedSchemaResponse(
                schema_type=d.schema_type,
                status=d.status,
                message=d.message,
            )
            for d in report.deprecated_schemas
        ],
        js_rendering_warnings=[
            JsRenderingWarningResponse(
                framework=w.framework,
                confidence=w.confidence,
                message=w.message,
            )
            for w in report.js_rendering_warnings
        ],
        recommended_templates=[
            GeneratedTemplateResponse(
                schema_type=t.schema_type,
                json_ld=t.json_ld,
                rationale=t.rationale,
            )
            for t in report.recommended_templates
        ],
        score=AuditScoreResponse(
            total=report.score.total,
            rating=report.score.rating,
            breakdown=[
                ScoreBreakdownResponse(
                    component=b.component,
                    max_points=b.max_points,
                    earned_points=b.earned_points,
                )
                for b in report.score.breakdown
            ],
        ),
    )
