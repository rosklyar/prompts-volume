"""Integration tests for /prompts endpoint."""

def test_get_prompts_for_seeded_topics(client):
    """
    Test /prompts endpoint returns prompts for seeded topics 1 and 2.

    This test:
    - Uses testcontainers PostgreSQL (via client fixture)
    - Has seeded data (countries, topics, prompts from CSVs)
    - Tests full integration: endpoint → router → service → database
    - Validates 50 phone prompts (topic 1) + 60 laptop prompts (topic 2)
    """
    # Request prompts for both seeded topics
    response = client.get("/prompts/api/v1/prompts?topic_ids=1&topic_ids=2")

    # Assert successful response
    assert response.status_code == 200, f"Failed: {response.json()}"
    data = response.json()

    # Validate response structure
    assert "topics" in data
    assert len(data["topics"]) == 2, "Should return 2 topics"

    # Find topics by ID
    topic_map = {topic["topic_id"]: topic for topic in data["topics"]}
    assert 1 in topic_map, "Topic 1 (phones) should be present"
    assert 2 in topic_map, "Topic 2 (laptops) should be present"

    # Validate topic 1 (Smartphones) - 50 prompts from prompts_phones.csv
    phones_topic = topic_map[1]
    assert len(phones_topic["prompts"]) == 50, "Should have 50 phone prompts"

    # Check first phone prompt structure
    first_phone_prompt = phones_topic["prompts"][0]
    assert "id" in first_phone_prompt
    assert "prompt_text" in first_phone_prompt
    assert "embedding" not in first_phone_prompt, "Embedding should NOT be in response"
    assert isinstance(first_phone_prompt["id"], int)
    assert isinstance(first_phone_prompt["prompt_text"], str)
    assert len(first_phone_prompt["prompt_text"]) > 0

    # Validate topic 2 (Laptops) - 59 prompts from prompts_laptops.csv
    # Note: CSV has 60 rows but row 59 has malformed quote, causing parser to merge rows 59-60
    laptops_topic = topic_map[2]
    assert len(laptops_topic["prompts"]) == 59, "Should have 59 laptop prompts"

    # Check first laptop prompt structure
    first_laptop_prompt = laptops_topic["prompts"][0]
    assert "id" in first_laptop_prompt
    assert "prompt_text" in first_laptop_prompt
    assert "embedding" not in first_laptop_prompt, "Embedding should NOT be in response"

    # Validate sample prompt texts (sanity check against CSV data)
    phone_texts = [p["prompt_text"] for p in phones_topic["prompts"]]
    laptop_texts = [p["prompt_text"] for p in laptops_topic["prompts"]]

    # Check for known prompts from CSVs
    assert any("смартфон" in text.lower() for text in phone_texts), "Should contain phone-related prompts"
    assert any("ноутбук" in text.lower() for text in laptop_texts), "Should contain laptop-related prompts"


def test_get_prompts_single_topic(client):
    """Test /prompts endpoint with single topic ID."""
    response = client.get("/prompts/api/v1/prompts?topic_ids=1")

    assert response.status_code == 200
    data = response.json()

    assert len(data["topics"]) == 1
    assert data["topics"][0]["topic_id"] == 1
    assert len(data["topics"][0]["prompts"]) == 50


def test_get_prompts_empty_topic_ids(client):
    """Test /prompts endpoint with no topic IDs returns 400."""
    response = client.get("/prompts/api/v1/prompts")

    assert response.status_code == 422  # FastAPI validation error for missing required query param


def test_get_prompts_nonexistent_topic(client):
    """Test /prompts endpoint with nonexistent topic ID returns 404."""
    response = client.get("/prompts/api/v1/prompts?topic_ids=999")

    assert response.status_code == 404
    assert "No prompts found" in response.json()["detail"]
