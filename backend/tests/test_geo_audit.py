"""Tests for GEO schema audit endpoint."""

from unittest.mock import AsyncMock, patch

import pytest

from src.config.settings import settings
from src.geo_audit.models.domain_models import (
    GeneratedTemplate,
    PageDiscoveryResult,
    RobotsResult,
)
from src.geo_audit.services import get_geo_audit_orchestrator, get_geo_audit_service, get_site_audit_orchestrator
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
from src.main import app
from src.database.users_session import get_users_session, get_users_session_maker


# --- Sample HTML with JSON-LD for mocked test ---
SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Example Corp",
    "url": "https://example.com",
    "logo": "https://example.com/logo.png",
    "description": "A sample organization for testing",
    "sameAs": [
        "https://www.linkedin.com/company/example",
        "https://www.youtube.com/c/example",
        "https://twitter.com/example",
        "https://en.wikipedia.org/wiki/Example",
        "https://www.wikidata.org/wiki/Q123456"
    ]
}
</script>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "Test Article",
    "author": {
        "@type": "Person",
        "name": "John Doe",
        "url": "https://example.com/authors/john",
        "jobTitle": "Senior Writer"
    },
    "datePublished": "2025-01-15",
    "dateModified": "2025-02-01",
    "publisher": {
        "@type": "Organization",
        "name": "Example Corp"
    },
    "image": "https://example.com/article.jpg",
    "description": "A test article for GEO audit"
}
</script>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
        {
            "@type": "ListItem",
            "position": 1,
            "name": "Home",
            "item": "https://example.com"
        }
    ]
}
</script>
</head>
<body><h1>Hello</h1></body>
</html>"""


MOCK_TEMPLATES = [
    GeneratedTemplate(
        schema_type="WebSite",
        json_ld='{"@context":"https://schema.org","@type":"WebSite","name":"[REPLACE]","url":"[REPLACE]"}',
        rationale="WebSite schema with SearchAction enables sitelinks search box.",
    ),
]


def _make_mocked_orchestrator():
    """Create a GeoAuditOrchestrator with mocked fetcher and template generator."""
    mock_fetcher = HtmlFetcher()
    mock_fetcher.fetch = AsyncMock(return_value=SAMPLE_HTML)

    mock_template_gen = AsyncMock(spec=TemplateGenerator)
    mock_template_gen.generate = AsyncMock(return_value=MOCK_TEMPLATES)

    return GeoAuditOrchestrator(
        html_fetcher=mock_fetcher,
        extractor=StructuredDataExtractor(),
        validator=SchemaValidator(),
        rich_result_checker=RichResultChecker(),
        geo_readiness_evaluator=GeoReadinessEvaluator(),
        deprecation_checker=DeprecationChecker(),
        js_rendering_detector=JsRenderingDetector(),
        template_generator=mock_template_gen,
        scorer=AuditScorer(),
    )


def _make_mocked_site_orchestrator():
    """Create a SiteAuditOrchestrator that immediately completes with mocked data."""
    orchestrator = _make_mocked_orchestrator()
    mock_discoverer = AsyncMock(spec=PageDiscoverer)
    mock_discoverer.discover = AsyncMock(return_value=PageDiscoveryResult(
        urls=["https://example.com/"],
        robots=RobotsResult(crawl_delay=0.0),
        sitemap_page_count=0,
        crawled_page_count=0,
    ))

    mock_template_gen = AsyncMock(spec=TemplateGenerator)
    mock_template_gen.generate = AsyncMock(return_value=MOCK_TEMPLATES)

    mock_fetcher = HtmlFetcher()
    mock_fetcher.fetch = AsyncMock(return_value=SAMPLE_HTML)

    return SiteAuditOrchestrator(
        session_maker=get_users_session_maker(),
        page_discoverer=mock_discoverer,
        page_orchestrator=orchestrator,
        html_fetcher=mock_fetcher,
        template_generator=mock_template_gen,
        max_concurrent=1,
    )


@pytest.fixture
def _override_orchestrator(client):
    """Override both orchestrator dependencies with mocked versions."""
    app.dependency_overrides[get_geo_audit_orchestrator] = _make_mocked_orchestrator
    app.dependency_overrides[get_site_audit_orchestrator] = _make_mocked_site_orchestrator
    yield
    app.dependency_overrides.pop(get_geo_audit_orchestrator, None)
    app.dependency_overrides.pop(get_site_audit_orchestrator, None)


# ---- Mocked tests ----

def test_post_audit_returns_progress(client, auth_headers, _override_orchestrator):
    """POST returns immediately with a progress response (pending status)."""
    response = client.post(
        "/api/v1/geo-audit",
        json={"url": "https://example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert "id" in data
    assert data["status"] == "pending"
    assert data["url"] == "https://example.com/"
    assert data["pages_discovered"] == 0
    assert data["pages_audited"] == 0
    assert data["pages_total"] == 0


def test_get_audit_returns_404_when_empty(client, auth_headers, _override_orchestrator):
    """GET returns 404 when user has no prior audits."""
    response = client.get("/api/v1/geo-audit", headers=auth_headers)
    assert response.status_code == 404
    assert "No audit results found" in response.json()["detail"]


def test_get_progress_returns_audit_status(client, auth_headers, _override_orchestrator):
    """GET progress endpoint returns audit status."""
    # Create a pending audit
    post_resp = client.post(
        "/api/v1/geo-audit",
        json={"url": "https://example.com"},
        headers=auth_headers,
    )
    assert post_resp.status_code == 200
    audit_id = post_resp.json()["id"]

    # Check progress
    progress_resp = client.get(
        f"/api/v1/geo-audit/{audit_id}/progress",
        headers=auth_headers,
    )
    assert progress_resp.status_code == 200
    data = progress_resp.json()
    assert data["id"] == audit_id
    assert data["status"] in ("pending", "discovering", "auditing", "completed", "failed")


def test_post_audit_cooldown_returns_429(client, auth_headers, _override_orchestrator):
    """Second POST within cooldown returns 429."""
    from fastapi import Depends

    def _get_long_cooldown_service(session=Depends(get_users_session)):
        return GeoAuditService(session, cooldown_hours=999)

    app.dependency_overrides[get_geo_audit_service] = _get_long_cooldown_service

    try:
        # First POST succeeds
        resp1 = client.post(
            "/api/v1/geo-audit",
            json={"url": "https://example.com"},
            headers=auth_headers,
        )
        assert resp1.status_code == 200

        # Second POST hits cooldown
        resp2 = client.post(
            "/api/v1/geo-audit",
            json={"url": "https://example.com"},
            headers=auth_headers,
        )
        assert resp2.status_code == 429
        assert "Retry-After" in resp2.headers
        assert "cooldown" in resp2.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_geo_audit_service, None)


def test_post_audit_no_url_no_brand_returns_400(client, auth_headers, _override_orchestrator):
    """POST with no URL and no brand preferences returns 400."""
    response = client.post(
        "/api/v1/geo-audit",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "No URL provided" in response.json()["detail"]


def test_get_pages_returns_empty_for_pending_audit(client, auth_headers, _override_orchestrator):
    """GET pages returns empty list for a pending audit."""
    post_resp = client.post(
        "/api/v1/geo-audit",
        json={"url": "https://example.com"},
        headers=auth_headers,
    )
    audit_id = post_resp.json()["id"]

    pages_resp = client.get(
        f"/api/v1/geo-audit/{audit_id}/pages",
        headers=auth_headers,
    )
    assert pages_resp.status_code == 200
    assert pages_resp.json() == []


# ---- Unit tests for new services ----

def test_robots_parser_parse_text():
    """RobotsParser correctly extracts sitemaps, disallow, and crawl-delay."""
    parser = RobotsParser()
    text = """
User-agent: *
Disallow: /admin/
Disallow: /private/
Crawl-delay: 2

User-agent: GeoAuditBot
Disallow: /secret/

Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap2.xml
"""
    result = parser._parse_text(text)

    assert set(result.sitemap_urls) == {
        "https://example.com/sitemap.xml",
        "https://example.com/sitemap2.xml",
    }
    # Disallow rules from * and GeoAuditBot
    assert "/admin/" in result.disallow_rules
    assert "/private/" in result.disallow_rules
    assert "/secret/" in result.disallow_rules
    assert result.crawl_delay == 2.0


def test_robots_parser_missing_crawl_delay():
    """Default crawl-delay is used when not specified in robots.txt."""
    parser = RobotsParser(default_crawl_delay=0.5)
    text = """
User-agent: *
Disallow: /
"""
    result = parser._parse_text(text)
    assert result.crawl_delay == 0.5


def test_sitemap_parser_urlset():
    """SitemapParser correctly extracts URLs from a urlset."""
    parser = SitemapParser()
    urls = parser._parse_urlset(__import__("xml.etree.ElementTree", fromlist=["ElementTree"]).fromstring("""
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
</urlset>
"""))
    assert urls == ["https://example.com/page1", "https://example.com/page2"]


def test_page_discoverer_disallow_filter():
    """PageDiscoverer correctly filters disallowed URLs."""
    discoverer = PageDiscoverer(
        robots_parser=RobotsParser(),
        sitemap_parser=SitemapParser(),
    )
    robots = RobotsResult(disallow_rules=["/admin/", "/private/"])

    assert discoverer._is_disallowed("https://example.com/admin/settings", robots)
    assert discoverer._is_disallowed("https://example.com/private/data", robots)
    assert not discoverer._is_disallowed("https://example.com/public/page", robots)


def test_page_discoverer_same_domain_check():
    """PageDiscoverer correctly checks same-domain URLs."""
    discoverer = PageDiscoverer(
        robots_parser=RobotsParser(),
        sitemap_parser=SitemapParser(),
    )
    assert discoverer._is_same_domain("https://example.com/page", "example.com")
    assert not discoverer._is_same_domain("https://other.com/page", "example.com")
    assert not discoverer._is_same_domain("https://sub.example.com/page", "example.com")


def test_page_discoverer_normalize_url():
    """PageDiscoverer normalizes URLs consistently."""
    discoverer = PageDiscoverer(
        robots_parser=RobotsParser(),
        sitemap_parser=SitemapParser(),
    )
    assert discoverer._normalize("https://Example.COM/page/") == "https://example.com/page"
    assert discoverer._normalize("https://example.com/") == "https://example.com/"
    assert discoverer._normalize("https://example.com") == "https://example.com/"


def test_orchestrator_audit_page():
    """GeoAuditOrchestrator.audit_page runs the per-page pipeline."""
    orchestrator = _make_mocked_orchestrator()
    report = orchestrator.audit_page(SAMPLE_HTML, "https://example.com")

    assert report.url == "https://example.com"
    assert report.extraction.total_blocks >= 3
    assert "Organization" in report.extraction.schema_types_found
    assert 0 <= report.score.total <= 100
    assert len(report.score.breakdown) == 10


def test_site_score_weighted_average():
    """SiteAuditOrchestrator computes weighted average with homepage 2x."""
    from src.geo_audit.models.domain_models import (
        AuditScore,
        ExtractionResult,
        GeoReadinessResult,
        PageAuditReport,
        RichResultCheckResult,
        ScoreBreakdown,
        ValidationResult,
    )

    def _make_report(url: str, score: float) -> PageAuditReport:
        return PageAuditReport(
            url=url,
            extraction=ExtractionResult(),
            validation=ValidationResult(),
            rich_results=RichResultCheckResult(),
            geo_readiness=GeoReadinessResult(),
            deprecated_schemas=[],
            js_rendering_warnings=[],
            score=AuditScore(
                total=score,
                rating="Good",
                breakdown=[ScoreBreakdown("test", 100, score)],
            ),
        )

    orchestrator = _make_mocked_site_orchestrator()

    reports = [
        _make_report("https://example.com/", 80),  # homepage, weight=2
        _make_report("https://example.com/about", 60),  # weight=1
    ]

    site_score = orchestrator._compute_site_score(reports, homepage_url="https://example.com/")

    # (80*2 + 60*1) / (2+1) = 220/3 ≈ 73.3
    assert abs(site_score.total - 73.3) < 0.5
