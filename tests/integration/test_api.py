from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_demo_execution() -> None:
    response = client.post(
        "/v1/executions",
        json={
            "project_id": "demo-project",
            "prompt": "Analise o código e o pipeline",
            "demo": True,
            "context": {"files": ["pyproject.toml", ".github/workflows/ci.yml"]},
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert all(result["simulated"] for result in payload["results"])
