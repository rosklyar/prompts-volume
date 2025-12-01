"""Integration tests for TopicsProvider with real OpenAI API calls and DB."""

import os

import pytest
from dotenv import load_dotenv

from src.embeddings.embeddings_service import get_embeddings_service
from src.prompts.services.topics_provider import TopicsProvider

load_dotenv()


@pytest.mark.skip(reason="Integration test - requires OpenAI API key and DB. Run manually.")
@pytest.mark.asyncio
async def test_provide_ecommerce_topics(
    business_domain_service, country_service, topic_service
):
    """Test topics provision for e-commerce site with DB matching.

    To run: uv run pytest tests/test_topics_generation_integration.py::test_provide_ecommerce_topics -v -s

    Requires:
    - OPENAI_API_KEY environment variable
    - Database with seeded data
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")

    # Get e-commerce business domain and Ukraine country
    business_domain = await business_domain_service.get_by_name("e-comm")
    country = await country_service.get_by_iso_code("UA")

    assert business_domain is not None, "e-comm business domain not seeded"
    assert country is not None, "Ukraine not seeded"

    # Create TopicsProvider with real services
    embeddings_service = get_embeddings_service()
    provider = TopicsProvider(
        api_key=api_key,
        model="gpt-4o-mini",
        topic_service=topic_service,
        embeddings_service=embeddings_service
    )

    # Test provide() method
    match_result = await provider.provide(
        "rozetka.com.ua", business_domain, country
    )

    # Validate result structure
    assert match_result is not None
    assert hasattr(match_result, "matched_topics")
    assert hasattr(match_result, "unmatched_topics")

    # Should have 10 topics total (matched + unmatched)
    all_titles = match_result.all_topic_titles()
    assert len(all_titles) == 10
    assert all(isinstance(title, str) and len(title) > 0 for title in all_titles)
