"""Integration tests for similar prompts endpoint."""


def test_find_similar_prompts_success(client):
    """Test finding similar prompts with query similar to seeded phone prompts."""
    # Query text similar to seeded prompts like:
    # - "Купити смартфон в Україні з швидкою доставкою"
    # - "Де купити смартфон Україна"
    query_text = "купити смартфон в Україні"

    response = client.get(
        "/prompts/api/v1/similar",
        params={"text": query_text, "k": 3, "min_similarity": 0.8},
    )

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert data["query_text"] == query_text
    assert "prompts" in data
    assert "total_found" in data
    assert data["total_found"] == len(data["prompts"])
    assert data["total_found"] <= 3  # k=3 limit

    # Validate prompts structure and ordering
    for i, prompt in enumerate(data["prompts"]):
        assert "id" in prompt
        assert "prompt_text" in prompt
        assert "similarity" in prompt
        assert prompt["similarity"] >= 0.8  # min_similarity threshold

        # Verify sorted by similarity descending
        if i > 0:
            assert prompt["similarity"] <= data["prompts"][i - 1]["similarity"]
