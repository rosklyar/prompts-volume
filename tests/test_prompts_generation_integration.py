"""Integration tests for prompts generation endpoint with real OpenAI API calls."""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

@pytest.mark.skip(reason="Integration test - uncomment to run manually with real OpenAI API")
def test_generate_prompts_real_openai():
    """
    Integration test that calls real OpenAI API.

    This test requires valid OPENAI_API_KEY in your .env file.

    To run: Remove the @pytest.mark.skip decorator above and run:
    uv run pytest tests/test_prompts_generation_integration.py::test_generate_prompts_real_openai
    """
    request_data = {
        "topics": ["телевізори", "смартфони", "ноутбуки"],
        "brand_name": "Moyo",
        "business_domain": "electronics e-commerce",
        "country": "Ukraine",
        "language": "Ukrainian",
        "business_description": "Moyo is a leading Ukrainian electronics retailer selling TVs, smartphones, laptops, home appliances, and accessories online and in retail stores across Ukraine.",
        "prompts_per_topic": 5,
    }

    response = client.post("/prompts/api/v1/generate", json=request_data)

    assert response.status_code == 200

    # Validate response structure
    data = response.json()
    assert "topics" in data
    assert isinstance(data["topics"], list)
    assert len(data["topics"]) == 3  # We requested 3 topics

    # Validate each topic
    for topic_data in data["topics"]:
        assert "topic" in topic_data
        assert "prompts" in topic_data
        assert isinstance(topic_data["topic"], str)
        assert len(topic_data["topic"]) > 0
        assert isinstance(topic_data["prompts"], list)
        assert len(topic_data["prompts"]) == 5  # We requested 5 prompts per topic

        # Validate each prompt
        for prompt in topic_data["prompts"]:
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            # Prompts should not contain the brand name
            assert "moyo" not in prompt.lower()
