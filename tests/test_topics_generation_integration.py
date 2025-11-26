"""Integration tests for TopicsGenerationService with real OpenAI API calls."""

import os

import pytest
from dotenv import load_dotenv

from src.prompts.models import BusinessDomain
from src.prompts.services.topics_generation_service import TopicsGenerationService

load_dotenv()


@pytest.mark.skip(reason="Integration test - requires OpenAI API key. Run manually.")
@pytest.mark.asyncio
async def test_generate_ecommerce_topics():
    """Test topics generation for e-commerce site.

    To run: uv run pytest tests/test_topics_generation_integration.py::test_generate_ecommerce_topics -v -s
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")

    service = TopicsGenerationService(api_key=api_key, model="gpt-4o-mini")
    topics = await service.generate_topics("rozetka.com.ua", BusinessDomain.E_COMMERCE, "Ukrainian")

    assert len(topics) == 10
    assert all(isinstance(topic, str) and len(topic) > 0 for topic in topics)
