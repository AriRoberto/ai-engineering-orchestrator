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

## Limites intencionais

O embedding determinístico de 16 dimensões existe para testes e demonstração local. Ele não é
apresentado como modelo semântico de produção. O provedor OpenAI somente é ativado com
`AIEO_LLM_PROVIDER=openai-agents` e credencial fornecida fora do repositório. O padrão permanece
`simulated` e não realiza chamadas pagas.

A memória de execuções ainda usa o repositório em memória da Fase 1. Persistência completa das
execuções, medição oficial de uso/custo e embeddings de produção permanecem pendentes.

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
