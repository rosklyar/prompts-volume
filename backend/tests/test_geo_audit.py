"""Tests for GEO schema audit endpoint."""

from unittest.mock import AsyncMock

import pytest

from src.config.settings import settings
from src.geo_audit.models.domain_models import GeneratedTemplate
from src.geo_audit.services import get_geo_audit_orchestrator, get_geo_audit_service
from src.geo_audit.services.audit_scorer import AuditScorer
from src.geo_audit.services.deprecation_checker import DeprecationChecker
from src.geo_audit.services.geo_audit_orchestrator import GeoAuditOrchestrator
from src.geo_audit.services.geo_audit_service import GeoAuditService
from src.geo_audit.services.geo_readiness_evaluator import GeoReadinessEvaluator
from src.geo_audit.services.html_fetcher import HtmlFetcher
from src.geo_audit.services.js_rendering_detector import JsRenderingDetector
from src.geo_audit.services.rich_result_checker import RichResultChecker
from src.geo_audit.services.schema_validator import SchemaValidator
from src.geo_audit.services.structured_data_extractor import StructuredDataExtractor
from src.geo_audit.services.template_generator import TemplateGenerator
from src.main import app
from src.database.users_session import get_users_session


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


@pytest.fixture
def _override_orchestrator(client):
    """Override the orchestrator dependency with mocked version.

    Note: client fixture already overrides all DB engines globally,
    so get_geo_audit_service and get_preferences_service will auto-use test DB.
    """
    app.dependency_overrides[get_geo_audit_orchestrator] = _make_mocked_orchestrator
    yield
    app.dependency_overrides.pop(get_geo_audit_orchestrator, None)


# ---- Live integration test (requires API key) ----

@pytest.mark.skipif(not settings.openai_api_key, reason="OPENAI_API_KEY required")
def test_geo_audit_logitech(client, auth_headers):
    """Integration test against live logitech.com.ua — requires network + OpenAI key."""
    response = client.post(
        "/api/v1/geo-audit",
        json={"url": "https://logitech.com.ua/"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert "result" in data
    result = data["result"]
    assert "extraction" in result
    assert "validation" in result
    assert "geo_readiness" in result
    assert "score" in result
    assert 0 <= data["score_total"] <= 100
    assert data["score_rating"] in ("Critical", "Poor", "Fair", "Good", "Excellent")


# ---- Mocked tests ----

def test_post_audit_with_url(client, auth_headers, _override_orchestrator):
    """POST with explicit URL — mocked pipeline, persists to DB."""
    response = client.post(
        "/api/v1/geo-audit",
        json={"url": "https://example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Stored response wrapper
    assert "id" in data
    assert "created_at" in data
    assert data["url"] == "https://example.com/"
    assert 0 <= data["score_total"] <= 100

    # Nested result
    result = data["result"]
    extraction = result["extraction"]
    assert extraction["total_blocks"] >= 3
    assert "json-ld" in extraction["formats_found"]
    assert "Organization" in extraction["schema_types_found"]

    # GEO signals
    signal_names = {s["name"] for s in result["geo_readiness"]["signals"]}
    assert {"Organization", "Person", "Article", "speakable", "WebSite+SearchAction"} <= signal_names

    # Score breakdown
    assert len(result["score"]["breakdown"]) == 10

    # Templates from mock
    assert len(result["recommended_templates"]) == 1


def test_get_audit_returns_404_when_empty(client, auth_headers, _override_orchestrator):
    """GET returns 404 when user has no prior audits."""
    response = client.get("/api/v1/geo-audit", headers=auth_headers)
    assert response.status_code == 404
    assert "No audit results found" in response.json()["detail"]


def test_post_then_get_returns_stored_result(client, auth_headers, _override_orchestrator):
    """POST persists audit, GET retrieves it."""
    # POST to create
    post_resp = client.post(
        "/api/v1/geo-audit",
        json={"url": "https://example.com"},
        headers=auth_headers,
    )
    assert post_resp.status_code == 200
    post_data = post_resp.json()

    # GET to retrieve
    get_resp = client.get("/api/v1/geo-audit", headers=auth_headers)
    assert get_resp.status_code == 200
    get_data = get_resp.json()

    # Same result
    assert get_data["id"] == post_data["id"]
    assert get_data["url"] == post_data["url"]
    assert get_data["score_total"] == post_data["score_total"]


def test_post_audit_cooldown_returns_429(client, auth_headers, _override_orchestrator):
    """Second POST within cooldown returns 429."""
    # Override service with very long cooldown
    app.dependency_overrides[get_geo_audit_service] = lambda: None  # placeholder

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


def test_post_audit_uses_brand_domain(client, auth_headers, _override_orchestrator, test_user):
    """POST without URL uses brand domain from preferences."""
    import asyncio
    from src.database.users_models import UserPreferences
    from src.database.users_session import get_users_session_maker

    # Create preferences with brand domain for the test user
    async def _create_prefs():
        session_maker = get_users_session_maker()
        async with session_maker() as s:
            prefs = UserPreferences(
                user_id=test_user.id,
                default_brand={"name": "Example Corp", "domain": "example.com", "variations": []},
            )
            s.add(prefs)
            await s.commit()

    asyncio.get_event_loop().run_until_complete(_create_prefs())

    # Override cooldown to 0 so it always allows
    from fastapi import Depends as _Depends

    def _get_no_cooldown_service(session=_Depends(get_users_session)):
        return GeoAuditService(session, cooldown_hours=0)

    app.dependency_overrides[get_geo_audit_service] = _get_no_cooldown_service

    try:
        response = client.post(
            "/api/v1/geo-audit",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://example.com"  # no trailing slash — constructed from domain
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
