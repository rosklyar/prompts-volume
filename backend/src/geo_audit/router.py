"""API router for GEO schema audit."""

import asyncio
import math

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.auth.deps import CurrentUser
from src.database.users_models import GeoAuditPageResult, GeoAuditResult
from src.geo_audit.exceptions import FetchError
from src.geo_audit.models.api_models import (
    AuditScoreResponse,
    DeprecatedSchemaResponse,
    DetectedSchemaResponse,
    ExtractionResponse,
    GeoAuditProgressResponse,
    GeoAuditRequest,
    GeoAuditResponse,
    GeoAuditStoredResponse,
    GeoReadinessResponse,
    GeoSignalResponse,
    GeneratedTemplateResponse,
    JsRenderingWarningResponse,
    PageAuditResponse,
    PageAuditStoredResponse,
    RichResultCheckResponse,
    RichResultGapResponse,
    SameAsLinkResponse,
    ScoreBreakdownResponse,
    SiteAuditResponse,
    SiteAuditStoredResponse,
    PageSummaryResponse,
    ValidationIssueResponse,
    ValidationResponse,
)
from src.geo_audit.models.domain_models import GeoAuditReport
from src.geo_audit.services import GeoAuditOrchestratorDep, GeoAuditServiceDep, SiteAuditOrchestratorDep
from src.onboarding.services import PreferencesServiceDep

router = APIRouter(prefix="/api/v1", tags=["geo-audit"])


@router.get("/geo-audit", response_model=SiteAuditStoredResponse)
async def get_latest_audit(
    current_user: CurrentUser,
    audit_service: GeoAuditServiceDep,
) -> SiteAuditStoredResponse:
    result = await audit_service.get_latest(current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="No audit results found")
    return _to_site_stored_response(result)


@router.post("/geo-audit", response_model=GeoAuditProgressResponse)
async def run_geo_audit(
    current_user: CurrentUser,
    site_orchestrator: SiteAuditOrchestratorDep,
    audit_service: GeoAuditServiceDep,
    preferences_service: PreferencesServiceDep,
    body: GeoAuditRequest | None = None,
) -> GeoAuditProgressResponse:
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

    # 3. Create pending audit and launch background job
    pending = await audit_service.create_pending(user_id=current_user.id, url=url)
    asyncio.create_task(site_orchestrator.run(audit_id=pending.id, base_url=url))

    return GeoAuditProgressResponse(
        id=pending.id,
        status="pending",
        url=url,
        pages_discovered=0,
        pages_audited=0,
        pages_total=0,
        error_message=None,
    )


@router.get("/geo-audit/{audit_id}/progress", response_model=GeoAuditProgressResponse)
async def get_audit_progress(
    audit_id: int,
    current_user: CurrentUser,
    audit_service: GeoAuditServiceDep,
) -> GeoAuditProgressResponse:
    result = await audit_service.get_by_id(audit_id)
    if result is None or result.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Audit not found")

    return GeoAuditProgressResponse(
        id=result.id,
        status=result.status,
        url=result.url,
        pages_discovered=result.pages_discovered,
        pages_audited=result.pages_audited,
        pages_total=result.pages_total,
        error_message=result.error_message,
    )


@router.get("/geo-audit/{audit_id}/pages", response_model=list[PageAuditStoredResponse])
async def get_audit_pages(
    audit_id: int,
    current_user: CurrentUser,
    audit_service: GeoAuditServiceDep,
) -> list[PageAuditStoredResponse]:
    audit = await audit_service.get_by_id(audit_id)
    if audit is None or audit.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Audit not found")

    pages = await audit_service.get_page_results(audit_id)
    return [_to_page_stored_response(p) for p in pages]


@router.get("/geo-audit/{audit_id}/pages/{page_id}", response_model=PageAuditStoredResponse)
async def get_audit_page(
    audit_id: int,
    page_id: int,
    current_user: CurrentUser,
    audit_service: GeoAuditServiceDep,
) -> PageAuditStoredResponse:
    audit = await audit_service.get_by_id(audit_id)
    if audit is None or audit.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Audit not found")

    page = await audit_service.get_page_result(page_id)
    if page is None or page.audit_id != audit_id:
        raise HTTPException(status_code=404, detail="Page result not found")

    return _to_page_stored_response(page)


def _resolve_url(body: GeoAuditRequest | None) -> str | None:
    if body is None or body.url is None:
        return None
    return str(body.url)


def _to_site_stored_response(row: GeoAuditResult) -> SiteAuditStoredResponse:
    site_result = None
    if row.status == "completed" and row.result_json is not None:
        site_result = SiteAuditResponse(
            url=row.url,
            site_score=AuditScoreResponse(**row.result_json["site_score"]),
            pages=[PageSummaryResponse(**p) for p in row.result_json.get("pages", [])],
            recommended_templates=[
                GeneratedTemplateResponse(**t)
                for t in row.result_json.get("recommended_templates", [])
            ],
        )

    return SiteAuditStoredResponse(
        id=row.id,
        url=row.url,
        status=row.status,
        score_total=row.score_total,
        score_rating=row.score_rating,
        pages_discovered=row.pages_discovered,
        pages_audited=row.pages_audited,
        pages_total=row.pages_total,
        result=site_result,
        error_message=row.error_message,
        created_at=row.created_at,
    )


def _to_page_stored_response(row: GeoAuditPageResult) -> PageAuditStoredResponse:
    return PageAuditStoredResponse(
        id=row.id,
        audit_id=row.audit_id,
        url=row.url,
        score_total=float(row.score_total),
        score_rating=row.score_rating,
        result=PageAuditResponse(**row.result_json),
        created_at=row.created_at,
    )
