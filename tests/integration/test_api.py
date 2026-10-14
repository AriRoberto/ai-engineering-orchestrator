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


def test_knowledge_and_simulated_llm_endpoints() -> None:
    ingested = client.post(
        "/v1/knowledge/documents",
        json={
            "project_id": "demo-project",
            "title": "Runbook fictício",
            "content": "Reinicie o serviço fictício e valide o health check.",
            "source": "demo://runbook",
        },
    )
    assert ingested.status_code == 201
    searched = client.post(
        "/v1/knowledge/search",
        json={"project_id": "demo-project", "query": "health check"},
    )
    assert searched.status_code == 200
    assert searched.json()[0]["source"] == "demo://runbook"
    llm = client.post("/v1/llm/generate", json={"prompt": "Explique o diagnóstico"})
    assert llm.status_code == 200
    assert llm.json()["simulated"] is True
