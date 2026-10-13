from __future__ import annotations

from ai_engineering.agents.base import EngineeringAgent
from ai_engineering.domain.models import AgentKind, AgentResult, TaskRequest


class SoftwareEngineeringAgent(EngineeringAgent):
    kind = AgentKind.SOFTWARE_ENGINEER
    description = "Stack detection, code and architecture analysis"
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
        findings = [f"Detected stack: {stack}" for stack in stacks]
        if not findings:
            findings = ["Stack not determined from the supplied evidence"]
        return AgentResult(
            agent=self.kind,
            summary="Read-only software engineering diagnostic completed",
            findings=findings,
            evidence=[f"manifest:{name}" for name in files if name in self.signatures],
            simulated=request.demo,
        )


class DevOpsAgent(EngineeringAgent):
    kind = AgentKind.DEVOPS
    description = "Git, CI/CD, containers and release diagnostics"

    def execute(self, request: TaskRequest) -> AgentResult:
        files = set(map(str, request.context.get("files", [])))
        findings = []
        findings.append(
            "Container definition found" if "Dockerfile" in files else "No Dockerfile evidence"
        )
        findings.append(
            "GitHub Actions workflow found"
            if any(name.startswith(".github/workflows/") for name in files)
            else "No CI workflow evidence"
        )
        return AgentResult(
            agent=self.kind,
            summary="DevOps diagnostic completed",
            findings=findings,
            simulated=request.demo,
        )


class KubernetesAgent(EngineeringAgent):
    kind = AgentKind.KUBERNETES
    description = "Kubernetes manifest and delivery diagnostics"

    def execute(self, request: TaskRequest) -> AgentResult:
        files = list(map(str, request.context.get("files", [])))
        manifests = [
            name for name in files if "k8s" in name or "helm" in name or name == "Chart.yaml"
        ]
        return AgentResult(
            agent=self.kind,
            summary="Kubernetes diagnostic completed",
            findings=[f"{len(manifests)} Kubernetes/Helm evidence item(s) supplied"],
            evidence=manifests,
            simulated=request.demo,
        )


class LinuxSREAgent(EngineeringAgent):
    kind = AgentKind.LINUX_SRE
    description = "Linux, reliability and incident diagnostics"

    def execute(self, request: TaskRequest) -> AgentResult:
        return AgentResult(
            agent=self.kind,
            summary="Linux/SRE diagnostic completed",
            findings=["No host command executed; analysis is evidence-only by policy"],
            simulated=request.demo,
        )


def default_agents() -> dict[AgentKind, EngineeringAgent]:
    agents: list[EngineeringAgent] = [
        SoftwareEngineeringAgent(),
        DevOpsAgent(),
        KubernetesAgent(),
        LinuxSREAgent(),
    ]
    return {agent.kind: agent for agent in agents}
