from typing import Protocol

from ai_engineering.integrations.mcp.models import MCPToolDefinition, MCPToolRisk


class MCPClient(Protocol):
    server_name: str

    def list_tools(self) -> list[MCPToolDefinition]: ...

    def call_tool(
        self, name: str, arguments: dict[str, object], *, project_id: str
    ) -> dict[str, object]: ...


class SimulatedProjectMCPClient:
    """Servidor determinístico, sem rede ou efeitos externos, para laboratório e testes."""

    server_name = "project-catalog"

    def __init__(self) -> None:
        object_schema = {"type": "object", "additionalProperties": False}
        self._tools = {
            "project_summary": MCPToolDefinition(
                server=self.server_name,
                name="project_summary",
                description="Retorna um resumo simulado e somente leitura do projeto.",
                risk=MCPToolRisk.READ,
                input_schema={
                    **object_schema,
                    "properties": {},
                },
                output_schema={
                    **object_schema,
                    "properties": {
                        "project_id": {"type": "string"},
                        "summary": {"type": "string"},
                        "simulated": {"type": "boolean"},
                    },
                    "required": ["project_id", "summary", "simulated"],
                },
            ),
            "publish_change": MCPToolDefinition(
                server=self.server_name,
                name="publish_change",
                description="Simula uma publicação para exercitar aprovação humana.",
                risk=MCPToolRisk.WRITE,
                input_schema={
                    **object_schema,
                    "properties": {"branch": {"type": "string", "minLength": 3}},
                    "required": ["branch"],
                },
                output_schema={
                    **object_schema,
                    "properties": {
                        "published": {"type": "boolean"},
                        "simulated": {"type": "boolean"},
                    },
                    "required": ["published", "simulated"],
                },
            ),
        }

    def list_tools(self) -> list[MCPToolDefinition]:
        return list(self._tools.values())

    def call_tool(
        self, name: str, arguments: dict[str, object], *, project_id: str
    ) -> dict[str, object]:
        if name == "project_summary":
            return {
                "project_id": project_id,
                "summary": f"Resumo MCP simulado e isolado para {project_id}",
                "simulated": True,
            }
        if name == "publish_change":
            return {"published": False, "simulated": True}
        raise KeyError(name)
