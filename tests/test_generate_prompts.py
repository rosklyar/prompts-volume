import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

@pytest.mark.skip(reason="Integration test - requires OpenAI API. Run manually.")
@pytest.mark.asyncio
async def test_prompts_generation():
    """
    End-to-end test: GET /generate with mocked DataForSEO.

    Pipeline tested:
    1. URL validation and domain extraction
    2. Country/language lookup
    3. Keyword fetching (mocked with sample data)
    4. Keyword filtering (word count, brand exclusion, dedupe)
    5. Embedding generation
    6. HDBSCAN clustering
    7. Topic relevance filtering
    8. E-commerce prompt generation (Ukrainian)

    To run:
    uv run pytest tests/test_generate_prompts.py::test_prompts_generation -v -s

    Requires: OPENAI_API_KEY in .env
    """
    # Load sample keywords from JSON
    sample_file = (
        Path(__file__).parent.parent / "samples" / "moyo_ukr_keyword.json"
    )
    with open(sample_file) as f:
        data = json.load(f)
        sample_keywords = data["keywords"]

    # Mock DataForSEO service to return sample keywords
    with patch(
        "src.prompts.data_for_seo_service.DataForSEOService.get_all_keywords_for_site"
    ) as mock_get_keywords:
        mock_get_keywords.return_value = sample_keywords
        # Call the API endpoint
        response = client.get(
            "/prompts/api/v1/generate",
            params={"company_url": "moyo.ua", "iso_country_code": "UA"},
        )

    # Assert response status
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.text}"

    # Parse response
    result = response.json()

    # Validate response structure
    assert "topics" in result
    assert isinstance(result["topics"], list)
    assert len(result["topics"]) > 0, "Expected at least one topic"
