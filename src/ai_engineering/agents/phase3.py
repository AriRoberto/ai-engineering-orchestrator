from pathlib import PurePosixPath

from ai_engineering.agents.base import EngineeringAgent
from ai_engineering.domain.models import AgentKind, AgentResult, TaskRequest


def evidence_files(request: TaskRequest) -> list[str]:
    return list(dict.fromkeys(str(item) for item in request.context.get("files", [])))


class DatabaseAgent(EngineeringAgent):
    kind = AgentKind.DATABASE
    description = "Diagnósticos de schema, migrações, persistência e bancos de dados"

    def execute(self, request: TaskRequest) -> AgentResult:
        files = evidence_files(request)
        database_files = [
            name
            for name in files
            if "migration" in name.casefold()
            or "schema" in name.casefold()
            or PurePosixPath(name).suffix.casefold() == ".sql"
        ]
        findings = [f"{len(database_files)} evidência(s) de schema ou migração identificada(s)"]
        findings.append(
            "Migrações versionadas foram fornecidas"
            if any("migration" in name.casefold() for name in database_files)
            else "Nenhuma evidência de diretório de migrações foi fornecida"
        )
        return AgentResult(
            agent=self.kind,
            summary="Diagnóstico de banco de dados concluído",
            findings=findings,
            evidence=database_files,
            simulated=request.demo,
        )


class QAAgent(EngineeringAgent):
    kind = AgentKind.QA
    description = "Diagnósticos de testes, qualidade e critérios de validação"

    def execute(self, request: TaskRequest) -> AgentResult:
        files = evidence_files(request)
        tests = [name for name in files if "test" in PurePosixPath(name).name.casefold()]
        ci = [name for name in files if name.startswith(".github/workflows/")]
        findings = [f"{len(tests)} arquivo(s) de teste fornecido(s) como evidência"]
        findings.append(
            "Evidência de automação de CI fornecida"
            if ci
            else "Nenhuma evidência de CI fornecida para execução dos testes"
        )
        return AgentResult(
            agent=self.kind,
            summary="Diagnóstico de qualidade concluído",
            findings=findings,
            evidence=[*tests, *ci],
            simulated=request.demo,
        )


class SecurityAgent(EngineeringAgent):
    kind = AgentKind.SECURITY
    description = "Diagnósticos de controles, segredos, dependências e superfície de ataque"
    sensitive_names = {".env", "id_rsa", "credentials", "secrets.yaml"}

    def execute(self, request: TaskRequest) -> AgentResult:
        files = evidence_files(request)
        collected = request.context.get("evidence", {}).get("files", [])
        quarantined = sum(
            1 for item in collected if item.get("content_status") == "quarantined"
        )
        redacted = sum(1 for item in collected if item.get("content_status") == "redacted")
        sensitive = [
            name for name in files if PurePosixPath(name).name.casefold() in self.sensitive_names
        ]
        controls = [
            name
            for name in files
            if PurePosixPath(name).name in {"SECURITY.md", ".gitignore", "Dockerfile"}
        ]
        findings = [
            f"{len(controls)} evidência(s) de controle de segurança fornecida(s)",
            (
                f"Revisão necessária para {len(sensitive)} possível(is) arquivo(s) sensível(is)"
                if sensitive
                else "Nenhum nome de arquivo sensível foi fornecido"
            ),
        ]
        if collected:
            findings.append(
                f"Conteúdo controlado: {redacted} arquivo(s) com redaction e "
                f"{quarantined} em quarentena"
            )
        return AgentResult(
            agent=self.kind,
            summary="Diagnóstico de segurança concluído",
            findings=findings,
            evidence=[*controls, *sensitive],
            simulated=request.demo,
        )


class DocumentationAgent(EngineeringAgent):
    kind = AgentKind.DOCUMENTATION
    description = "Diagnósticos de documentação técnica, operação e rastreabilidade"

    def execute(self, request: TaskRequest) -> AgentResult:
        files = evidence_files(request)
        collected = request.context.get("evidence", {}).get("files", [])
        docs = [name for name in files if PurePosixPath(name).suffix.casefold() == ".md"]
        required = {"README.md", "CHANGELOG.md", "SECURITY.md"}
        present = {PurePosixPath(name).name for name in docs}
        missing = sorted(required - present)
        findings = [f"{len(docs)} documento(s) Markdown fornecido(s) como evidência"]
        findings.append(
            "Documentos essenciais presentes"
            if not missing
            else f"Documentos essenciais não evidenciados: {', '.join(missing)}"
        )
        if collected:
            available = sum(
                1
                for item in collected
                if item.get("content_status") in {"included", "redacted"}
            )
            findings.append(f"{available} conteúdo(s) textual(is) seguro(s) disponível(is)")
        return AgentResult(
            agent=self.kind,
            summary="Diagnóstico de documentação concluído",
            findings=findings,
            evidence=docs,
            simulated=request.demo,
        )
