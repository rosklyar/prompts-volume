"""Integration tests for topics endpoint with real DataForSEO API calls."""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


#@pytest.mark.skip(reason="Integration test - uncomment to run manually with real DataForSEO API")
def test_get_topics_real_dataforseo():
    """
    Integration test that calls real DataForSEO API.

    This test requires valid DATAFORSEO_USERNAME and DATAFORSEO_PASSWORD
    in your .env file.

    To run: Uncomment the @pytest.mark.skip decorator above and run:
    uv run pytest tests/test_topics_integration.py::test_get_topics_real_dataforseo
    """
    response = client.get("/prompts/api/v1/topics?url=moyo.ua&iso_code=UA")

    assert response.status_code == 200

    # Validate response structure
    keywords = response.json()
    assert isinstance(keywords, list)
    assert len(keywords) > 0

    # Each keyword should be a string
    for keyword in keywords:
        assert isinstance(keyword, str)
        assert len(keyword) > 0
