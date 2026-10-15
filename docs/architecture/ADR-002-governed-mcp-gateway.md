# ADR-002: Gateway MCP governado e isolado por projeto

- Status: aceito para a Fase 2
- Data: 15/10/2026

## Contexto

Servidores MCP ampliam as capacidades dos agentes, mas também criam uma fronteira de confiança:
catálogos podem mudar, argumentos são influenciados por modelos e algumas ferramentas produzem
efeitos externos. O sistema precisa manter autorização, validação e aprovação fora do LLM.

## Decisão

Toda ferramenta MCP passa por um gateway determinístico antes de ser exposta ou executada. O
gateway carrega a política do projeto, aplica allowlist pelo nome qualificado `servidor:ferramenta`,
classifica o risco, valida entrada e saída por JSON Schema e registra cada decisão. Ferramentas de
escrita interrompem sem aprovação; ações destrutivas são bloqueadas. O identificador do projeto é
injetado pelo gateway e não pode ser escolhido nos argumentos da ferramenta.

O transporte é uma porta interna (`MCPClient`). O incremento atual usa um cliente determinístico
simulado, sem rede ou efeitos externos, para validar governança e auditoria antes da conexão com
servidores MCP reais.

## Consequências

- projetos sem configuração têm catálogo vazio;
- ferramentas não permitidas falham fechadas e deixam auditoria;
- projetos `read-only` não executam escrita, mesmo com aprovação declarada;
- uma futura conexão MCP real reutilizará o gateway e não poderá contornar suas políticas;
- autenticação forte do aprovador e retomada de chamadas pausadas ainda são necessárias antes de
  habilitar efeitos reais.

## Referências

- [Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)
- [Guardrails e revisão humana](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals)
