# Histórico de alterações

## Não lançado

- Consolidado e validado um gate de regressão único com escopos estático, local e completo, limpeza
  segura de serviços Compose e integração ao workflow de CI.
- Concluída a Fase 4 após validação real do piloto privado `app-ams` com token fine-grained
  temporário e somente leitura, coleta exclusiva de metadados, auditoria persistente e confirmação
  de que a credencial não integra a resposta pública.
- Adicionado ambiente Kubernetes local reproduzível com kind, PostgreSQL/pgvector efêmero, secrets
  externos, migração, probes, autenticação, pilotos público e privado, rollout e rollback; a
  validação real corrigiu a identidade numérica não-root e as permissões dos volumes de Secret.

## [0.2.0] - 2026-10-20

- Consolida a documentação oficial, o checklist e o gate automatizado da release 0.2.0.

- Primeiro incremento da Fase 5 com instrumentação OpenTelemetry da API, exportação OTLP/HTTP
  opcional, IDs de requisição validados e correlação entre resposta, trace, logs e execução.
- Segundo incremento da Fase 5 com métricas HTTP e de execuções, endpoint Prometheus, coletor local
  em overlay Compose e laboratório reproduzível com rótulos de baixa cardinalidade.
- Terceiro incremento da Fase 5 com dashboard Grafana provisionado, regras Prometheus para
  disponibilidade, erros e latência, além de validação automatizada por `promtool` e APIs locais.
- Quarto incremento da Fase 5 com API keys armazenadas por hash, papéis de acesso, allowlist de
  projetos, quotas por identidade e laboratório sem persistência de credenciais.
- Quinto incremento da Fase 5 com interface React para histórico, fontes, auditorias e aprovações
  MCP vinculadas, compilada e servida pela mesma imagem da API.
- Sexto incremento da Fase 5 com base Kustomize segura, prontidão dependente do PostgreSQL, Job de
  migração e laboratório reproduzível.
- Sétimo incremento da Fase 5 com SLIs, SLOs, alertas multi-janela de burn rate, dashboard de
  orçamento de erro e runbooks de resposta a incidentes.

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
  escopo por repositório, falha fechada e laboratório Compose.
- Auditoria persistente de acessos a evidências, incluindo conclusões, negações e falhas isoladas
  por projeto, sem armazenamento de credenciais.

## 0.1.0 - 2026-10-13

- Fundação inicial da Fase 1: API, orquestrador determinístico, quatro agentes, modo demonstração,
  governança Git, testes, Docker, CI e documentação da fundação.
