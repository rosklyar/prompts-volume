"""Integration tests for /generate endpoint with mocked DataForSEO."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.skip(reason="Integration test - requires OpenAI API key. Run manually with: uv run pytest tests/test_generate_prompts.py::test_prompts_generation -v -s")
def test_prompts_generation(client):
    """
    End-to-end test: GET /generate with mocked DataForSEO, real OpenAI.

    Pipeline tested:
    1. URL validation and domain extraction
    2. Country lookup (uses seeded data from testcontainers)
    3. Keyword fetching (mocked with 11,471 keywords from samples/moyo_ukr_keyword.json)
    4. Keyword filtering (word count ≥3, brand exclusion, dedupe)
    5. Embedding generation (paraphrase-multilingual-MiniLM-L12-v2)
    6. HDBSCAN clustering
    7. Topic relevance filtering
    8. E-commerce prompt generation (OpenAI gpt-4o-mini, Ukrainian)

    Uses:
    - testcontainers PostgreSQL (via client fixture)
    - Seeded database (countries, topics via seed_initial_data)
    - Mocked DataForSEOService.get_all_keywords_for_site()
    - Real OpenAI API (requires OPENAI_API_KEY in .env)

    To run:
    uv run pytest tests/test_generate_prompts.py::test_prompts_generation -v -s
    """
    # Load sample keywords from JSON
    sample_file = Path(__file__).parent.parent / "samples" / "moyo_ukr_keyword.json"
    with open(sample_file) as f:
        data = json.load(f)
        sample_keywords = data["keywords"]

    print(f"\n✓ Loaded {len(sample_keywords)} keywords from sample file")

    # Mock DataForSEO service to return sample keywords
    with patch(
        "src.prompts.services.data_for_seo_service.DataForSEOService.get_all_keywords_for_site",
        new_callable=AsyncMock,
    ) as mock_get_keywords:
        mock_get_keywords.return_value = sample_keywords

        # Call the API endpoint with required parameters
        response = client.get(
            "/prompts/api/v1/generate",
            params={
                "company_url": "moyo.ua",
                "iso_country_code": "UA",
                "topics": ["Смартфони і телефони", "Ноутбуки та персональні комп'ютери"],
                "brand_variations": ["moyo", "мойо"],
            },
        )

    # Assert response status
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # Parse response
    result = response.json()

    # Validate response structure
    assert "topics" in result, "Response should have 'topics' key"
    assert isinstance(result["topics"], list), "Topics should be a list"
    assert len(result["topics"]) > 0, "Expected at least one topic with prompts"

    # Validate topic structure (GeneratedPrompts → Topic → ClusterPrompts)
    for topic in result["topics"]:
        assert "topic" in topic, "Each topic should have 'topic' name"
        assert "clusters" in topic, "Each topic should have 'clusters'"
        assert isinstance(topic["clusters"], list), "Clusters should be a list"
        assert len(topic["clusters"]) > 0, "Each topic should have at least one cluster"

        # Validate cluster structure
        for cluster in topic["clusters"]:
            assert "cluster_id" in cluster
            assert "keywords" in cluster
            assert "prompts" in cluster
            assert isinstance(cluster["prompts"], list)
            assert len(cluster["prompts"]) > 0, "Each cluster should have prompts"

            # Validate prompts are strings
            for prompt in cluster["prompts"]:
                assert isinstance(prompt, str)
                assert len(prompt) > 0

    # Log results for manual inspection
    print(f"\n✓ Generated prompts for {len(result['topics'])} topics")
    for topic in result["topics"]:
        total_prompts = sum(len(c["prompts"]) for c in topic["clusters"])
        print(f"  - {topic['topic']}: {len(topic['clusters'])} clusters, {total_prompts} total prompts")
