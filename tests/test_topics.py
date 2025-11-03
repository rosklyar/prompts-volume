from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_get_topics_with_valid_url():
    response = client.get("/prompts/api/v1/topics?url=tryprofound.com")
    assert response.status_code == 200
    assert response.json() == ["GEO", "AI search", "Brand monitoring"]
