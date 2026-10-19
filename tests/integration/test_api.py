from uuid import UUID

from fastapi.testclient import TestClient

from apps.api import main as api_main
from apps.api.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert UUID(response.headers["X-Request-ID"])
    assert len(response.headers["X-Trace-ID"]) == 32


def test_request_id_is_propagated_only_when_valid() -> None:
    request_id = "fe744f62-3858-41db-a1a1-b8a32805db54"
    propagated = client.get("/health", headers={"X-Request-ID": request_id})
    replaced = client.get("/health", headers={"X-Request-ID": "unsafe-value"})

    assert propagated.headers["X-Request-ID"] == request_id
    assert replaced.headers["X-Request-ID"] != "unsafe-value"
    assert UUID(replaced.headers["X-Request-ID"])


def test_prometheus_metrics_include_http_and_execution_counters() -> None:
    client.post(
        "/v1/executions",
        json={"project_id": "metrics-test", "prompt": "Analise o código", "demo": True},
    )
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "aieo_http_server_requests_total" in response.text
    assert "aieo_http_server_duration_seconds" in response.text
    assert "aieo_executions_total" in response.text
    assert 'execution_source="direct"' in response.text


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
    assert payload["consolidated_result"].startswith("[SIMULAÇÃO]")
    assert payload["llm_usage"]["provider"] == "simulated"


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
    assert llm.json()["usage"]["estimated"] is True


def test_governed_mcp_endpoints() -> None:
    tools = client.get("/v1/mcp/tools", params={"project_id": "laboratorio-fase2"})
    assert tools.status_code == 200
    assert {tool["name"] for tool in tools.json()} == {"project_summary", "publish_change"}

    invoked = client.post(
        "/v1/mcp/invocations",
        json={
            "project_id": "laboratorio-fase2",
            "server": "project-catalog",
            "tool": "project_summary",
            "arguments": {},
        },
    )
    assert invoked.status_code == 200
    assert invoked.json()["status"] == "COMPLETED"
    assert invoked.json()["result"]["simulated"] is True

    pending = client.post(
        "/v1/mcp/invocations",
        json={
            "project_id": "laboratorio-fase2",
            "server": "project-catalog",
            "tool": "publish_change",
            "arguments": {"branch": "agents/devops/feat-demo-001"},
        },
    )
    assert pending.json()["status"] == "WAITING_APPROVAL"
    approved = client.post(
        f"/v1/mcp/invocations/{pending.json()['id']}/approve",
        json={"project_id": "laboratorio-fase2", "approved_by": "reviewer@example.test"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "COMPLETED"
    assert approved.json()["approval_of"] == pending.json()["id"]
    replay = client.post(
        f"/v1/mcp/invocations/{pending.json()['id']}/approve",
        json={"project_id": "laboratorio-fase2", "approved_by": "reviewer@example.test"},
    )
    assert replay.status_code == 409


def test_phase3_specialists_are_available_and_executable() -> None:
    agents = client.get("/v1/agents")
    assert agents.status_code == 200
    agent_ids = {item["id"] for item in agents.json()}
    assert {"database", "qa", "security", "documentation"} <= agent_ids

    execution = client.post(
        "/v1/executions",
        json={
            "project_id": "laboratorio-fase2",
            "prompt": "Revise banco de dados, QA, segurança e documentação",
            "demo": True,
            "context": {
                "files": [
                    "migrations/001_schema.sql",
                    "tests/test_api.py",
                    ".github/workflows/ci.yml",
                    "SECURITY.md",
                    "README.md",
                    "CHANGELOG.md",
                ]
            },
        },
    )
    assert execution.status_code == 201
    payload = execution.json()
    assert payload["status"] == "COMPLETED"
    assert {result["agent"] for result in payload["results"]} == {
        "database",
        "qa",
        "security",
        "documentation",
    }


def test_public_github_evidence_execution(monkeypatch) -> None:
    class FakeTransport:
        def get_tree(self, owner: str, repository: str, ref: str) -> dict[str, object]:
            assert (owner, repository, ref) == ("AriRoberto", "app-financas", "main")
            return {
                "sha": "a" * 40,
                "truncated": False,
                "tree": [
                    {"path": "README.md", "type": "blob", "size": 100, "sha": "b" * 40},
                    {
                        "path": "tests/test_financas.py",
                        "type": "blob",
                        "size": 200,
                        "sha": "c" * 40,
                    },
                ],
            }

        def get_content(
            self, owner: str, repository: str, path: str, ref: str, max_bytes: int
        ) -> bytes:
            contents = {
                "README.md": b"Public documentation",
                "tests/test_financas.py": b"def test_ok(): pass",
            }
            return contents[path]

    monkeypatch.setattr(api_main.evidence_execution_service.collector, "transport", FakeTransport())
    response = client.post(
        "/v1/evidence/executions",
        json={
            "project_id": "app-financas",
            "prompt": "Revise QA e documentação",
            "demo": True,
            "include_content": True,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["request"]["context"]["evidence"]["provider"] == "github"
    assert payload["request"]["context"]["evidence"]["read_only"] is True
    assert payload["request"]["context"]["evidence"]["files"][0]["content_status"] == "included"
    context = payload["request"]["context"]["evidence_context"]
    assert context[0]["citation"] == "[evidence:README.md]"
    assert context[0]["content"] == "Public documentation"
    assert payload["evidence_sources"] == [context[0]["source_url"], context[1]["source_url"]]


def test_private_project_evidence_is_denied() -> None:
    response = client.post(
        "/v1/evidence/executions",
        json={"project_id": "app-ams", "prompt": "Revise a documentação"},
    )
    assert response.status_code == 403
    audits = client.get("/v1/evidence/audits", params={"project_id": "app-ams"})
    assert audits.status_code == 200
    assert audits.json()[0]["status"] == "DENIED"
    assert audits.json()[0]["authenticated"] is False


def test_private_project_uses_authenticated_read_only_transport(monkeypatch) -> None:
    class AuthenticatedTransport:
        def has_credentials(self, owner: str, repository: str) -> bool:
            return (owner, repository) == ("AriRoberto", "app-ams")

        def get_tree(self, owner: str, repository: str, ref: str) -> dict[str, object]:
            assert (owner, repository, ref) == ("AriRoberto", "app-ams", "main")
            return {
                "sha": "a" * 40,
                "truncated": False,
                "tree": [
                    {"path": "README.md", "type": "blob", "size": 100, "sha": "b" * 40}
                ],
            }

        def get_content(
            self, owner: str, repository: str, path: str, ref: str, max_bytes: int
        ) -> bytes:
            raise AssertionError("Conteúdo não foi solicitado")

    monkeypatch.setattr(
        api_main.evidence_execution_service.collector,
        "transport",
        AuthenticatedTransport(),
    )
    response = client.post(
        "/v1/evidence/executions",
        json={"project_id": "app-ams", "prompt": "Revise a documentação", "demo": True},
    )

    assert response.status_code == 201
    payload = response.json()
    evidence = payload["request"]["context"]["evidence"]
    assert evidence["metadata"]["visibility"] == "private"
    assert evidence["metadata"]["authenticated"] is True
    assert "secret-token" not in response.text
