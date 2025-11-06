from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.main import app
from src.topics.service import DataForSEOService, get_dataforseo_service

client = TestClient(app)

def test_get_topics_with_valid_iso_code():
    """Test topics endpoint with valid ISO code."""
    # Create mock service
    mock_service = DataForSEOService()
    mock_service.get_keywords_for_site = AsyncMock(
        return_value=["us keyword 1", "us keyword 2"]
    )

    # Override the dependency
    app.dependency_overrides[get_dataforseo_service] = lambda: mock_service

    try:
        response = client.get("/prompts/api/v1/topics?url=tryprofound.com&iso_code=US")

        assert response.status_code == 200
        keywords = response.json()
        assert keywords == ["us keyword 1", "us keyword 2"]

        # Verify service was called with United States as location and English as language
        mock_service.get_keywords_for_site.assert_called_once()
        call_args = mock_service.get_keywords_for_site.call_args
        assert call_args[0][1] == "United States"
        assert call_args[0][2] == "English"  # First preferred language for US
    finally:
        # Clean up override
        app.dependency_overrides.clear()


def test_get_topics_with_lowercase_iso_code():
    """Test that lowercase ISO codes are handled correctly."""
    # Create mock service
    mock_service = DataForSEOService()
    mock_service.get_keywords_for_site = AsyncMock(
        return_value=["ukraine keyword"]
    )

    # Override the dependency
    app.dependency_overrides[get_dataforseo_service] = lambda: mock_service

    try:
        response = client.get("/prompts/api/v1/topics?url=tryprofound.com&iso_code=ua")

        assert response.status_code == 200
        keywords = response.json()
        assert keywords == ["ukraine keyword"]

        # Verify Ukraine location and Ukrainian language were used
        call_args = mock_service.get_keywords_for_site.call_args
        assert call_args[0][1] == "Ukraine"
        assert call_args[0][2] == "Ukrainian"  # First preferred language for Ukraine
    finally:
        # Clean up override
        app.dependency_overrides.clear()


def test_get_topics_with_invalid_iso_code():
    """Test topics endpoint with invalid ISO code."""
    response = client.get("/prompts/api/v1/topics?url=tryprofound.com&iso_code=XX")

    assert response.status_code == 400
    assert "Invalid ISO country code" in response.json()["detail"]
