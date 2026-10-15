# Fase 2 — Fundação de inteligência e conhecimento

Este incremento adiciona uma base funcional e segura para evoluir o sistema sem apresentar
simulações como resultados reais.

## Implementado neste incremento

- contrato de provedores de LLM;
- provedor simulado determinístico como padrão;
- adaptador opcional para o OpenAI Agents SDK;
- PostgreSQL 17 com extensão pgvector no Docker Compose;
- ingestão, fragmentação, embeddings locais explícitos e busca híbrida;
- isolamento obrigatório por `project_id`;
- compartilhamento somente com autorização explícita;
- proteção conservadora contra padrões comuns de prompt injection;
- exclusão de documentos e registro de feedback humano;
- endpoints Swagger para conhecimento, feedback e LLM.

## Segundo incremento: RAG no fluxo do orquestrador

O orquestrador agora consulta até três fragmentos autorizados antes da execução, registra as fontes
na própria execução e entrega o contexto recuperado junto com os resultados dos agentes ao provedor
de LLM. A saída consolidada é consultiva: o roteamento, os limites e as permissões continuam sob
controle determinístico.

Cada execução registra uma estimativa explícita de tokens de entrada e saída. A estimativa não é
apresentada como medição oficial do provedor e o custo permanece `null` até que haja uma tabela de
preços configurada e validada. O limite de entrada é verificado antes da chamada e o limite de saída
é enviado ao provedor e verificado novamente na resposta.

Configurações:

- `AIEO_LLM_PLANNING_ENABLED`: habilita a consolidação;
- `AIEO_MAX_LLM_INPUT_TOKENS`: teto estimado de entrada por execução;
- `AIEO_MAX_LLM_OUTPUT_TOKENS`: teto de saída por execução.

## Terceiro incremento: memória persistente de execuções

Quando `AIEO_DATABASE_URL` está configurada, cada execução passa a ser gravada no PostgreSQL com a
solicitação, estado, plano, resultados, fontes de conhecimento, uso de LLM e linha do tempo completa.
Os endpoints de consulta usam o mesmo repositório, portanto as execuções continuam disponíveis após
reiniciar a API. Sem banco configurado, o repositório em memória permanece como fallback explícito
para testes unitários e desenvolvimento mínimo.

Listagem, consulta individual e cancelamento exigem `project_id`; o repositório aplica esse filtro
na leitura para impedir que uma execução persistida seja exposta por outro projeto.

A migração `002_phase2_executions.sql` cria a tabela e os índices operacionais. A aplicação também
faz a criação idempotente dessa tabela ao conectar, permitindo atualizar volumes do Compose criados
antes deste incremento sem apagar os dados de conhecimento existentes.

## Quarto incremento: gateway MCP governado

O gateway MCP expõe somente ferramentas presentes na allowlist do projeto. Cada ferramenta possui
nome qualificado, nível de risco e schemas JSON de entrada e saída. A política é aplicada antes da
chamada, o resultado é validado antes de chegar ao consumidor e todas as decisões — inclusive
negações e interrupções — são registradas em `mcp_invocations`.

O laboratório usa o servidor determinístico `project-catalog`, que não acessa rede nem produz
efeitos reais. `project_summary` demonstra leitura isolada; `publish_change` demonstra a interrupção
`WAITING_APPROVAL`. Projetos em modo `read-only` negam escrita mesmo quando a requisição declara
aprovação. A identidade do aprovador ainda não é autenticada, portanto efeitos externos permanecem
desabilitados neste incremento.

Endpoints adicionados:

- `GET /v1/mcp/tools?project_id=...`;
- `POST /v1/mcp/invocations`;
- `GET /v1/mcp/invocations?project_id=...`.

A decisão e seus limites estão no
[ADR-002](../architecture/ADR-002-governed-mcp-gateway.md).

## Limites intencionais

O embedding determinístico de 16 dimensões existe para testes e demonstração local. Ele não é
apresentado como modelo semântico de produção. O provedor OpenAI somente é ativado com
`AIEO_LLM_PROVIDER=openai-agents` e credencial fornecida fora do repositório. O padrão permanece
`simulated` e não realiza chamadas pagas.

A medição oficial de uso/custo, embeddings de produção, transporte para servidores MCP reais e
autenticação de aprovadores permanecem pendentes. O payload completo em
JSON preserva a auditoria, mas consultas analíticas detalhadas por evento ainda exigirão projeções
específicas em um incremento futuro.

## Endpoints

- `POST /v1/knowledge/documents`
- `POST /v1/knowledge/search`
- `DELETE /v1/knowledge/documents/{id}?project_id=...`
- `POST /v1/feedback`
- `POST /v1/llm/generate`

## Referências oficiais

- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)
- [Quickstart do Agents SDK](https://developers.openai.com/api/docs/guides/agents/quickstart?lang=python)
- [Guardrails e revisão humana](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals)
