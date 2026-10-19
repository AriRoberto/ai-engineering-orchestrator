# Histórico de alterações

## Não lançado

- Primeiro incremento da Fase 5 com instrumentação OpenTelemetry da API, exportação OTLP/HTTP
  opcional, IDs de requisição validados e correlação entre resposta, trace, logs e execução.

- Fundação incremental da Fase 2: PostgreSQL/pgvector, ingestão documental, busca híbrida isolada
  por projeto, feedback persistente, provedor LLM simulado e adaptador opcional para OpenAI Agents SDK.
- Documentação integralmente em português e referências oficiais atualizadas.
- Recuperação de conhecimento integrada ao orquestrador, consolidação por LLM, fontes por execução
  e limites com contabilização explicitamente estimada de tokens.
- Persistência completa de execuções no PostgreSQL, incluindo plano, resultados, fontes, uso de LLM
  e linha do tempo, com validação de sobrevivência ao reinício da API no laboratório da Fase 2.
- Gateway MCP governado com allowlist por projeto, validação de schemas, classificação de risco,
  aprovação para escrita e auditoria persistente de chamadas e bloqueios.
- Primeiro incremento da Fase 3 com agentes de Banco de Dados, QA, Segurança e Documentação,
  roteamento determinístico, resultados estruturados e laboratório reproduzível dedicado.
- Primeiro incremento da Fase 4 com coleta governada do inventário GitHub público, proveniência por
  arquivo, limites contra abuso, integração à execução e bloqueio explícito do piloto privado.
- Segundo incremento da Fase 4 com coleta textual opt-in, limites independentes, validação UTF-8,
  SHA-256, redaction de possíveis segredos, quarentena de prompt injection e diagnóstico dos estados
  pelos agentes de Segurança e Documentação.
- Plano oficial de implementação com fases, critérios de conclusão, estado e ordem imediata.
- Terceiro incremento da Fase 4 com orçamento de contexto, citações por arquivo, fontes de evidência
  persistidas e separação explícita entre instruções confiáveis e dados externos.
- Quarto incremento da Fase 4 com corpus adversarial versionado, métricas por categoria, limiar de
  aprovação, normalização contra evasões simples e validação de citações, hashes, origem e orçamento.
- Implementação local do piloto privado somente leitura com credencial GitHub em arquivo secreto,
  escopo por repositório, falha fechada e laboratório Compose; validação contra o repositório real
  ainda pendente.
- Auditoria persistente de acessos a evidências, incluindo conclusões, negações e falhas isoladas
  por projeto, sem armazenamento de credenciais.

## 0.1.0 - 2026-10-13

- Fundação inicial da Fase 1: API, orquestrador determinístico, quatro agentes, modo demonstração,
  governança Git, testes, Docker, CI e documentação da fundação.
