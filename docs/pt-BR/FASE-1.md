# Fase 1 — Fundação

## Implementado

- API FastAPI com health check, catálogo de agentes e ciclo de execuções.
- Orquestrador determinístico com IDs UUID, estados, eventos, limite de passos e cancelamento.
- Agentes de Software Engineering, DevOps, Kubernetes e Linux/SRE em modo diagnóstico.
- Modo demo explicitamente marcado como simulado.
- Governança Git em código, com bloqueio de escrita direta, merge automático e force push.
- Logs JSON, container sem root, filesystem somente leitura e CI.
- Configurações isoladas dos dois pilotos, sem credenciais.

## Deliberadamente planejado para fases posteriores

Persistência PostgreSQL, pgvector/RAG, LLMs, agentes adicionais, MCP, interface React,
OpenTelemetry e diagnósticos autenticados dos pilotos.

