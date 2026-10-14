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

## Limites intencionais

O embedding determinístico de 16 dimensões existe para testes e demonstração local. Ele não é
apresentado como modelo semântico de produção. O provedor OpenAI somente é ativado com
`AIEO_LLM_PROVIDER=openai-agents` e credencial fornecida fora do repositório. O padrão permanece
`simulated` e não realiza chamadas pagas.

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
