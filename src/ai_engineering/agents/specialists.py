from __future__ import annotations

from ai_engineering.agents.base import EngineeringAgent
from ai_engineering.agents.phase3 import DatabaseAgent, DocumentationAgent, QAAgent, SecurityAgent
from ai_engineering.domain.models import AgentKind, AgentResult, TaskRequest


class SoftwareEngineeringAgent(EngineeringAgent):
    kind = AgentKind.SOFTWARE_ENGINEER
    description = "Detecção de stack e análise de código e arquitetura"
    signatures = {
        "pyproject.toml": "Python",
        "requirements.txt": "Python",
        "package.json": "JavaScript/TypeScript",
        "pom.xml": "Java/Maven",
        "build.gradle": "Java/Gradle",
        "go.mod": "Go",
        "Cargo.toml": "Rust",
        "composer.json": "PHP",
        "Gemfile": "Ruby",
    }

    def execute(self, request: TaskRequest) -> AgentResult:
        files = [str(item) for item in request.context.get("files", [])]
        stacks = sorted({stack for name, stack in self.signatures.items() if name in files})
        findings = [f"Stack detectada: {stack}" for stack in stacks]
        if not findings:
            findings = ["Stack não determinada pelas evidências fornecidas"]
        return AgentResult(
            agent=self.kind,
            summary="Diagnóstico de engenharia de software somente leitura concluído",
            findings=findings,
            evidence=[f"manifest:{name}" for name in files if name in self.signatures],
            simulated=request.demo,
        )


class DevOpsAgent(EngineeringAgent):
    kind = AgentKind.DEVOPS
    description = "Diagnósticos de Git, CI/CD, containers e releases"

    def execute(self, request: TaskRequest) -> AgentResult:
        files = set(map(str, request.context.get("files", [])))
        findings = []
        findings.append(
            "Definição de container encontrada"
            if "Dockerfile" in files
            else "Nenhuma evidência de Dockerfile"
        )
        findings.append(
            "Workflow do GitHub Actions encontrado"
            if any(name.startswith(".github/workflows/") for name in files)
            else "Nenhuma evidência de workflow de CI"
        )
        return AgentResult(
            agent=self.kind,
            summary="Diagnóstico DevOps concluído",
            findings=findings,
            simulated=request.demo,
        )


class KubernetesAgent(EngineeringAgent):
    kind = AgentKind.KUBERNETES
    description = "Diagnósticos de manifestos e entrega Kubernetes"

    def execute(self, request: TaskRequest) -> AgentResult:
        files = list(map(str, request.context.get("files", [])))
        manifests = [
            name for name in files if "k8s" in name or "helm" in name or name == "Chart.yaml"
        ]
        return AgentResult(
            agent=self.kind,
            summary="Diagnóstico Kubernetes concluído",
            findings=[f"{len(manifests)} evidência(s) de Kubernetes/Helm fornecida(s)"],
            evidence=manifests,
            simulated=request.demo,
        )


class LinuxSREAgent(EngineeringAgent):
    kind = AgentKind.LINUX_SRE
    description = "Diagnósticos de Linux, confiabilidade e incidentes"

    def execute(self, request: TaskRequest) -> AgentResult:
        return AgentResult(
            agent=self.kind,
            summary="Diagnóstico Linux/SRE concluído",
            findings=[
                "Nenhum comando executado no host; por política, a análise usa apenas evidências"
            ],
            simulated=request.demo,
        )


def default_agents() -> dict[AgentKind, EngineeringAgent]:
    agents: list[EngineeringAgent] = [
        SoftwareEngineeringAgent(),
        DevOpsAgent(),
        KubernetesAgent(),
        LinuxSREAgent(),
        DatabaseAgent(),
        QAAgent(),
        SecurityAgent(),
        DocumentationAgent(),
    ]
    return {agent.kind: agent for agent in agents}
