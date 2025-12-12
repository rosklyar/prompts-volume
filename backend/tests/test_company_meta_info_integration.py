"""Integration tests for /meta-info endpoint with real OpenAI API calls."""
import pytest
from dotenv import load_dotenv

load_dotenv()

@pytest.mark.skip(reason="Integration test - requires OpenAI API key. Run manually.")
def test_meta_info_endpoint(client):
    """Test /meta-info endpoint with real API call and testcontainers database.

    This test:
    - Uses testcontainers PostgreSQL (via client fixture)
    - Has seeded data (countries, business domains, topics)
    - Makes real OpenAI API call (requires OPENAI_API_KEY)
    - Tests full integration: endpoint → services → database → OpenAI

    To run: uv run pytest tests/test_company_meta_info_integration.py::test_meta_info_endpoint -v -s
    """
    # Make request (client already has DB overridden via fixture)
    response = client.get(
        "/prompts/api/v1/meta-info?company_url=comfy.ua&iso_country_code=UA"
    )

    # Assert response
    assert response.status_code == 200, f"Failed: {response.json()}"
    data = response.json()

    # Check business domain
    assert data["business_domain"] == "e-comm"

    # Check topics structure (new format: matched_topics + unmatched_topics)
    assert "topics" in data
    assert "matched_topics" in data["topics"]
    assert "unmatched_topics" in data["topics"]

    # Should have 10 topics total (matched + unmatched)
    matched = data["topics"]["matched_topics"]
    unmatched = data["topics"]["unmatched_topics"]
    total_topics = len(matched) + len(unmatched)

    assert total_topics == 10, (
        f"Expected 10 topics total, got {total_topics} "
        f"(matched: {len(matched)}, unmatched: {len(unmatched)})"
    )

    # Check matched topics have DB fields
    if matched:
        assert "id" in matched[0], "Matched topics should have 'id' field"
        assert "title" in matched[0], "Matched topics should have 'title' field"
        assert "description" in matched[0], "Matched topics should have 'description' field"

    # Check unmatched topics have correct structure
    if unmatched:
        assert "title" in unmatched[0], "Unmatched topics should have 'title' field"
        assert "source" in unmatched[0], "Unmatched topics should have 'source' field"
        assert unmatched[0]["source"] == "generated", "Unmatched topics source should be 'generated'"

    # Check brand variations
    assert len(data["brand_variations"]) > 0, "Should have at least one brand variation"
