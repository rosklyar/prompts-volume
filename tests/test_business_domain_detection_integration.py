"""Integration tests for BusinessDomainDetectionService with real OpenAI API calls."""

import os

import pytest
from dotenv import load_dotenv

from src.businessdomain.services import BusinessDomainDetectionService

load_dotenv()


@pytest.mark.skip(reason="Integration test - requires OpenAI API key and database. Run manually.")
@pytest.mark.asyncio
async def test_detect_ecommerce(business_domain_service):
    """Test business domain detection for e-commerce site with language-specific brand variations.

    To run: uv run pytest tests/test_business_domain_detection_integration.py::test_detect_ecommerce -v -s

    Note: Requires database session fixture from conftest.py
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")

    service = BusinessDomainDetectionService(
        api_key=api_key,
        business_domain_service=business_domain_service,
        model="gpt-4o-mini"
    )
    languages = ["English", "Ukrainian", "Russian"]
    business_domain, brand_variations = await service.detect("rozetka.com.ua", languages)

    assert business_domain is not None, "Should detect a business domain"
    assert business_domain.name == "e-comm", "Should classify as e-commerce"
    assert len(brand_variations) > 0
    assert any("rozetka" in v.lower() or "розетка" in v.lower() for v in brand_variations)
