"""Orchestrator service for GEO schema audit."""

import logging

from src.geo_audit.models.domain_models import GeoAuditReport, PageAuditReport
from src.geo_audit.services.audit_scorer import AuditScorer
from src.geo_audit.services.deprecation_checker import DeprecationChecker
from src.geo_audit.services.geo_readiness_evaluator import GeoReadinessEvaluator
from src.geo_audit.services.html_fetcher import HtmlFetcher
from src.geo_audit.services.js_rendering_detector import JsRenderingDetector
from src.geo_audit.services.rich_result_checker import RichResultChecker
from src.geo_audit.services.schema_validator import SchemaValidator
from src.geo_audit.services.structured_data_extractor import StructuredDataExtractor
from src.geo_audit.services.template_generator import TemplateGenerator

logger = logging.getLogger(__name__)


class GeoAuditOrchestrator:
    """Coordinates all audit steps to produce a complete GEO audit report."""

    def __init__(
        self,
        *,
        html_fetcher: HtmlFetcher,
        extractor: StructuredDataExtractor,
        validator: SchemaValidator,
        rich_result_checker: RichResultChecker,
        geo_readiness_evaluator: GeoReadinessEvaluator,
        deprecation_checker: DeprecationChecker,
        js_rendering_detector: JsRenderingDetector,
        template_generator: TemplateGenerator,
        scorer: AuditScorer,
    ):
        self._html_fetcher = html_fetcher
        self._extractor = extractor
        self._validator = validator
        self._rich_result_checker = rich_result_checker
        self._geo_readiness_evaluator = geo_readiness_evaluator
        self._deprecation_checker = deprecation_checker
        self._js_rendering_detector = js_rendering_detector
        self._template_generator = template_generator
        self._scorer = scorer

    async def audit(self, url: str) -> GeoAuditReport:
        """Full single-page audit including HTML fetch and template generation."""
        logger.info("Starting GEO audit for %s", url)

        html = await self._html_fetcher.fetch(url)
        page_report = self.audit_page(html, url)

        templates = await self._template_generator.generate(
            url=url,
            extraction=page_report.extraction,
            geo_readiness=page_report.geo_readiness,
        )

        logger.info("GEO audit complete for %s — score: %s/100", url, page_report.score.total)

        return GeoAuditReport(
            url=url,
            extraction=page_report.extraction,
            validation=page_report.validation,
            rich_results=page_report.rich_results,
            geo_readiness=page_report.geo_readiness,
            deprecated_schemas=page_report.deprecated_schemas,
            js_rendering_warnings=page_report.js_rendering_warnings,
            recommended_templates=templates,
            score=page_report.score,
        )

    def audit_page(self, html: str, url: str) -> PageAuditReport:
        """Run steps 2-7 and 9 on already-fetched HTML. No templates."""
        extraction = self._extractor.extract(html)
        logger.info("Found %d schema blocks on %s", extraction.total_blocks, url)

        validation = self._validator.validate(extraction.schemas)
        rich_results = self._rich_result_checker.check(extraction.schemas)
        geo_readiness = self._geo_readiness_evaluator.evaluate(extraction.schemas)
        deprecated = self._deprecation_checker.check(extraction.schemas)
        js_warnings = self._js_rendering_detector.detect(html)

        score = self._scorer.score(
            extraction=extraction,
            validation=validation,
            geo_readiness=geo_readiness,
            deprecated=deprecated,
        )

        return PageAuditReport(
            url=url,
            extraction=extraction,
            validation=validation,
            rich_results=rich_results,
            geo_readiness=geo_readiness,
            deprecated_schemas=deprecated,
            js_rendering_warnings=js_warnings,
            score=score,
        )
