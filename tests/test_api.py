"""Basic smoke tests for the FastAPI app.

Note: these will download the HF models on first run of a /translate test,
so they're slow the first time. The health check test doesn't require that.
"""

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_translate_requires_text():
    response = client.post(
        "/translate", json={"text": "", "direction": "en2cop", "dialect": "bohairic"}
    )
    assert response.status_code == 422


def test_translate_rejects_bad_direction():
    response = client.post(
        "/translate",
        json={"text": "hello", "direction": "sideways", "dialect": "bohairic"},
    )
    assert response.status_code == 422
