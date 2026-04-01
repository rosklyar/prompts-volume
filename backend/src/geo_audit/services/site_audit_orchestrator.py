"""Orchestrator for multi-page site audit (background job)."""

import asyncio
import logging
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.geo_audit.models.domain_models import (
    AuditScore,
    ExtractionResult,
    GeoReadinessResult,
    PageAuditReport,
    ScoreBreakdown,
)
from src.geo_audit.services.geo_audit_orchestrator import GeoAuditOrchestrator
from src.geo_audit.services.html_fetcher import HtmlFetcher
from src.geo_audit.services.page_discoverer import PageDiscoverer
from src.geo_audit.services.template_generator import TemplateGenerator

logger = logging.getLogger(__name__)

_HOMEPAGE_WEIGHT = 2.0
_DEFAULT_WEIGHT = 1.0


def _rating(total: float) -> str:
    if total <= 20:
        return "Critical"
    if total <= 40:
        return "Poor"
    if total <= 60:
        return "Fair"
    if total <= 80:
        return "Good"
    return "Excellent"


class SiteAuditOrchestrator:
    """Coordinates multi-page site audit as a background job."""

    def __init__(
        self,
        *,
        session_maker: async_sessionmaker[AsyncSession],
        page_discoverer: PageDiscoverer,
        page_orchestrator: GeoAuditOrchestrator,
        html_fetcher: HtmlFetcher,
        template_generator: TemplateGenerator,
        max_concurrent: int = 5,
    ):
        self._session_maker = session_maker
        self._page_discoverer = page_discoverer
        self._page_orchestrator = page_orchestrator
        self._html_fetcher = html_fetcher
        self._template_generator = template_generator
        self._max_concurrent = max_concurrent

    async def run(self, *, audit_id: int, base_url: str) -> None:
        """Background job: discover pages, audit each, aggregate, persist."""
        try:
            await self._run_inner(audit_id=audit_id, base_url=base_url)
        except Exception:
            logger.exception("Site audit %d failed", audit_id)
            await self._update_status(audit_id, status="failed", error_message="Internal error during audit")

    async def _run_inner(self, *, audit_id: int, base_url: str) -> None:
        # Step 1: Discover pages
        await self._update_status(audit_id, status="discovering")

        discovery = await self._page_discoverer.discover(base_url)
        if not discovery.urls:
            await self._update_status(audit_id, status="failed", error_message="No pages discovered")
            return

        await self._update_status(
            audit_id,
            status="auditing",
            pages_discovered=len(discovery.urls),
            pages_total=len(discovery.urls),
        )

        # Step 2: Audit pages in parallel
        semaphore = asyncio.Semaphore(self._max_concurrent)
        page_reports: list[PageAuditReport] = []
        crawl_delay = discovery.robots.crawl_delay

        async def audit_one(url: str) -> PageAuditReport | None:
            async with semaphore:
                try:
                    html = await self._html_fetcher.fetch(url)
                    report = self._page_orchestrator.audit_page(html, url)
                    await self._save_page_result(audit_id, report)
                    await self._increment_pages_audited(audit_id)
                    return report
                except Exception:
                    logger.warning("Failed to audit page %s", url, exc_info=True)
                    await self._increment_pages_audited(audit_id)
                    return None
                finally:
                    await asyncio.sleep(crawl_delay)

        tasks = [audit_one(url) for url in discovery.urls]
        results = await asyncio.gather(*tasks)
        page_reports = [r for r in results if r is not None]

        if not page_reports:
            await self._update_status(audit_id, status="failed", error_message="All pages failed to audit")
            return

        # Step 3: Generate templates once for the whole site
        combined_extraction = self._aggregate_extractions(page_reports)
        combined_readiness = self._aggregate_readiness(page_reports)

        templates = await self._template_generator.generate(
            url=base_url,
            extraction=combined_extraction,
            geo_readiness=combined_readiness,
        )

        # Step 4: Compute weighted site score
        site_score = self._compute_site_score(page_reports, homepage_url=discovery.urls[0])

        # Step 5: Build site-level result_json and persist
        site_result = {
            "url": base_url,
            "site_score": {
                "total": site_score.total,
                "rating": site_score.rating,
                "breakdown": [asdict(b) for b in site_score.breakdown],
            },
            "pages": [
                {"url": r.url, "score_total": r.score.total, "score_rating": r.score.rating}
                for r in page_reports
            ],
            "recommended_templates": [
                {"schema_type": t.schema_type, "json_ld": t.json_ld, "rationale": t.rationale}
                for t in templates
            ],
        }

        await self._update_status(
            audit_id,
            status="completed",
            score_total=site_score.total,
            score_rating=site_score.rating,
            result_json=site_result,
        )

        logger.info(
            "Site audit %d complete: %d/%d pages, score %.1f",
            audit_id, len(page_reports), len(discovery.urls), site_score.total,
        )

    def _compute_site_score(
        self, page_reports: list[PageAuditReport], *, homepage_url: str,
    ) -> AuditScore:
        """Weighted average: homepage gets 2x weight, others 1x."""
        total_weight = 0.0
        weighted_total = 0.0
        component_weighted: dict[str, tuple[float, float]] = {}  # component -> (weighted_earned, weighted_max)

        for report in page_reports:
            normalized_url = report.url.rstrip("/")
            normalized_home = homepage_url.rstrip("/")
            weight = _HOMEPAGE_WEIGHT if normalized_url == normalized_home else _DEFAULT_WEIGHT

            total_weight += weight
            weighted_total += report.score.total * weight

            for b in report.score.breakdown:
                earned, max_pts = component_weighted.get(b.component, (0.0, 0.0))
                component_weighted[b.component] = (
                    earned + b.earned_points * weight,
                    max_pts + b.max_points * weight,
                )

        if total_weight == 0:
            return AuditScore(total=0, rating="Critical")

        avg_total = min(weighted_total / total_weight, 100)
        breakdown = [
            ScoreBreakdown(
                component=comp,
                max_points=round(max_pts / total_weight, 1),
                earned_points=round(earned / total_weight, 1),
            )
            for comp, (earned, max_pts) in component_weighted.items()
        ]

        return AuditScore(total=round(avg_total, 1), rating=_rating(avg_total), breakdown=breakdown)

    def _aggregate_extractions(self, page_reports: list[PageAuditReport]) -> ExtractionResult:
        """Merge extraction results across all pages for template generation."""
        all_schemas = []
        all_types: set[str] = set()
        all_formats: set[str] = set()

        for report in page_reports:
            all_schemas.extend(report.extraction.schemas)
            all_types.update(report.extraction.schema_types_found)
            all_formats.update(report.extraction.formats_found)

        return ExtractionResult(
            schemas=all_schemas,
            total_blocks=len(all_schemas),
            formats_found=sorted(all_formats),
            schema_types_found=sorted(all_types),
        )

    def _aggregate_readiness(self, page_reports: list[PageAuditReport]) -> GeoReadinessResult:
        """Take the best readiness result (highest overall_readiness) across pages."""
        if not page_reports:
            return GeoReadinessResult()
        return max(page_reports, key=lambda r: r.geo_readiness.overall_readiness).geo_readiness

    async def _update_status(self, audit_id: int, *, status: str, **fields: object) -> None:
        from src.database.users_models import GeoAuditResult

        async with self._session_maker() as session:
            result = await session.get(GeoAuditResult, audit_id)
            if result is None:
                logger.error("Audit %d not found for status update", audit_id)
                return
            result.status = status
            for key, value in fields.items():
                setattr(result, key, value)
            await session.commit()

    async def _increment_pages_audited(self, audit_id: int) -> None:
        from src.database.users_models import GeoAuditResult

        async with self._session_maker() as session:
            result = await session.get(GeoAuditResult, audit_id)
            if result is not None:
                result.pages_audited = (result.pages_audited or 0) + 1
                await session.commit()

    async def _save_page_result(self, audit_id: int, report: PageAuditReport) -> None:
        from src.database.users_models import GeoAuditPageResult
        from src.geo_audit.models.api_models import PageAuditResponse

        page_response = self._to_page_response(report)

        async with self._session_maker() as session:
            row = GeoAuditPageResult(
                audit_id=audit_id,
                url=report.url,
                score_total=report.score.total,
                score_rating=report.score.rating,
                result_json=page_response.model_dump(mode="json"),
            )
            session.add(row)
            await session.commit()

    def _to_page_response(self, report: PageAuditReport) -> "PageAuditResponse":
        from src.geo_audit.models.api_models import (
            AuditScoreResponse,
            DeprecatedSchemaResponse,
            DetectedSchemaResponse,
            ExtractionResponse,
            GeoReadinessResponse,
            GeoSignalResponse,
            JsRenderingWarningResponse,
            PageAuditResponse,
            RichResultCheckResponse,
            RichResultGapResponse,
            SameAsLinkResponse,
            ScoreBreakdownResponse,
            ValidationIssueResponse,
            ValidationResponse,
        )

        return PageAuditResponse(
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
                        platform=link.platform,
                        linked=link.linked,
                        url=link.url,
                    )
                    for link in report.geo_readiness.same_as_links
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
