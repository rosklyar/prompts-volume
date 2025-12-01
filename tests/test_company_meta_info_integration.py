"""Integration tests for /meta-info endpoint with real OpenAI API calls."""

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from src.main import app

load_dotenv()


@pytest.mark.skip(reason="Integration test - requires OpenAI API key. Run manually.")
def test_meta_info_endpoint():
    """Test /meta-info endpoint with real API call and language-specific brand variations.

    To run: uv run pytest tests/test_company_meta_info_integration.py::test_meta_info_endpoint -v -s
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")

    client = TestClient(app)
    response = client.get("/prompts/api/v1/meta-info?company_url=comfy.ua&iso_country_code=UA")

    assert response.status_code == 200
    data = response.json()

    assert data["business_domain"] == "e-comm"
    assert len(data["top_topics"]) == 10
    assert len(data["brand_variations"]) > 0
