"""GEO audit services with dependency injection."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database.users_session import get_users_session, get_users_session_maker
from src.geo_audit.services.audit_scorer import AuditScorer
from src.geo_audit.services.deprecation_checker import DeprecationChecker
from src.geo_audit.services.geo_audit_orchestrator import GeoAuditOrchestrator
from src.geo_audit.services.geo_audit_service import GeoAuditService
from src.geo_audit.services.geo_readiness_evaluator import GeoReadinessEvaluator
from src.geo_audit.services.html_fetcher import HtmlFetcher
from src.geo_audit.services.js_rendering_detector import JsRenderingDetector
from src.geo_audit.services.page_discoverer import PageDiscoverer
from src.geo_audit.services.rich_result_checker import RichResultChecker
from src.geo_audit.services.robots_parser import RobotsParser
from src.geo_audit.services.schema_validator import SchemaValidator
from src.geo_audit.services.site_audit_orchestrator import SiteAuditOrchestrator
from src.geo_audit.services.sitemap_parser import SitemapParser
from src.geo_audit.services.structured_data_extractor import StructuredDataExtractor
from src.geo_audit.services.template_generator import TemplateGenerator


def get_geo_audit_orchestrator() -> GeoAuditOrchestrator:
    return GeoAuditOrchestrator(
        html_fetcher=HtmlFetcher(),
        extractor=StructuredDataExtractor(),
        validator=SchemaValidator(),
        rich_result_checker=RichResultChecker(),
        geo_readiness_evaluator=GeoReadinessEvaluator(),
        deprecation_checker=DeprecationChecker(),
        js_rendering_detector=JsRenderingDetector(),
        template_generator=TemplateGenerator(
            api_key=settings.openai_api_key,
            model=settings.geo_audit_model,
        ),
        scorer=AuditScorer(),
    )


def get_site_audit_orchestrator() -> SiteAuditOrchestrator:
    return SiteAuditOrchestrator(
        session_maker=get_users_session_maker(),
        page_discoverer=PageDiscoverer(
            robots_parser=RobotsParser(default_crawl_delay=settings.geo_audit_default_crawl_delay),
            sitemap_parser=SitemapParser(),
            max_pages=settings.geo_audit_max_pages,
            max_concurrent=settings.geo_audit_max_concurrent_pages,
        ),
        page_orchestrator=get_geo_audit_orchestrator(),
        html_fetcher=HtmlFetcher(),
        template_generator=TemplateGenerator(
            api_key=settings.openai_api_key,
            model=settings.geo_audit_model,
        ),
        max_concurrent=settings.geo_audit_max_concurrent_pages,
    )


def get_geo_audit_service(
    session: AsyncSession = Depends(get_users_session),
) -> GeoAuditService:
    return GeoAuditService(session, cooldown_hours=settings.geo_audit_cooldown_hours)


GeoAuditOrchestratorDep = Annotated[
    GeoAuditOrchestrator, Depends(get_geo_audit_orchestrator)
]

SiteAuditOrchestratorDep = Annotated[
    SiteAuditOrchestrator, Depends(get_site_audit_orchestrator)
]

GeoAuditServiceDep = Annotated[
    GeoAuditService, Depends(get_geo_audit_service)
]
