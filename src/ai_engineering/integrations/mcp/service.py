from jsonschema import ValidationError, validate

from ai_engineering.integrations.mcp.client import MCPClient
from ai_engineering.integrations.mcp.models import (
    MCPInvocation,
    MCPInvocationRequest,
    MCPInvocationStatus,
    MCPToolDefinition,
    MCPToolRisk,
)
from ai_engineering.integrations.mcp.policy import MCPPolicyStore


class MCPGateway:
    def __init__(self, clients: list[MCPClient], policies: MCPPolicyStore, audit) -> None:
        self.clients = {client.server_name: client for client in clients}
        self.policies = policies
        self.audit = audit

    def list_tools(self, project_id: str) -> list[MCPToolDefinition]:
        policy = self.policies.get(project_id)
        if not policy:
            return []
        return [
            tool
            for client in self.clients.values()
            for tool in client.list_tools()
            if tool.qualified_name in policy.allowed_tools
        ]

    def invoke(self, request: MCPInvocationRequest) -> MCPInvocation:
        policy = self.policies.get(request.project_id)
        client = self.clients.get(request.server)
        tool = next(
            (item for item in client.list_tools() if item.name == request.tool),
            None,
        ) if client else None
        qualified_name = f"{request.server}:{request.tool}"
        if not policy or not tool or qualified_name not in policy.allowed_tools:
            return self._record(
                request, tool, MCPInvocationStatus.DENIED, "Ferramenta não autorizada"
            )
        if tool.risk == MCPToolRisk.DESTRUCTIVE:
            return self._record(
                request, tool, MCPInvocationStatus.DENIED, "Ação destrutiva bloqueada"
            )
        if tool.risk == MCPToolRisk.WRITE and policy.mode == "read-only":
            return self._record(
                request, tool, MCPInvocationStatus.DENIED, "Projeto somente leitura"
            )
        if tool.risk == MCPToolRisk.WRITE and not request.approved:
            return self._record(
                request, tool, MCPInvocationStatus.WAITING_APPROVAL, "Aprovação humana necessária"
            )
        try:
            validate(request.arguments, tool.input_schema)
            result = client.call_tool(
                tool.name, request.arguments, project_id=request.project_id
            )
            validate(result, tool.output_schema)
        except (ValidationError, KeyError):
            return self._record(request, tool, MCPInvocationStatus.FAILED, "Schema MCP inválido")
        return self._record(
            request, tool, MCPInvocationStatus.COMPLETED, "Ferramenta executada", result
        )

    def _record(self, request, tool, status, reason, result=None) -> MCPInvocation:
        invocation = MCPInvocation(
            project_id=request.project_id,
            server=request.server,
            tool=request.tool,
            risk=tool.risk if tool else MCPToolRisk.DESTRUCTIVE,
            status=status,
            arguments=request.arguments,
            result=result,
            reason=reason,
            approved_by=request.approved_by,
        )
        self.audit.add(invocation)
        return invocation
