# Plano de implementação do AI Engineering Orchestrator

Este documento é a fonte oficial para fases, incrementos, critérios de conclusão e próximos passos
do projeto. O README apresenta apenas o resumo executivo; documentos de fase, ADRs, laboratórios e
CHANGELOG preservam os detalhes e as evidências de cada entrega.

## Definição de concluído

Um incremento somente é considerado concluído quando possui:

- implementação funcional integrada ao fluxo principal;
- controles de segurança proporcionais à capacidade adicionada;
- testes automatizados e lint aprovados;
- laboratório reproduzível quando houver integração externa;
- documentação de operação, arquitetura e limitações atualizada;
- registro no CHANGELOG e ADR quando existir nova decisão arquitetural.

## Estado das fases

| Fase | Objetivo | Estado | Entregas principais |
|---|---|---|---|
| 1 — Fundação | API, orquestração e governança básica | Concluída | FastAPI, oito estados, agentes iniciais, Docker, CI e governança Git |
| 2 — Inteligência | Conhecimento, memória e integrações governadas | Concluída na fundação | PostgreSQL/pgvector, RAG, LLM, execuções persistentes e MCP governado |
| 3 — Especialização | Diagnósticos por domínio | Concluída no escopo inicial | Database, QA, Security e Documentation Agents |
| 4 — Pilotos | Evidência real com menor privilégio | Em andamento | Piloto público, conteúdo protegido e contexto com citações |
| 5 — Produto | Experiência, observabilidade e operação | Concluída no escopo local | OpenTelemetry, UI, Kubernetes, SLOs, release e documentação oficial |

## Fase 1 — Fundação

Concluída com API, orquestrador determinístico, execução somente leitura por padrão, governança Git,
testes, container e documentação inicial. Evidências: [FASE-1.md](FASE-1.md),
[auditoria-fase1.md](auditoria-fase1.md) e [laboratorio-fase1.md](laboratorio-fase1.md).

## Fase 2 — Inteligência e conhecimento

Concluída no escopo de fundação: persistência PostgreSQL/pgvector, ingestão e busca híbrida isolada,
feedback, contrato de LLM, RAG integrado, memória de execuções e gateway MCP governado. Permanecem
evoluções de produção como embeddings semânticos, custos oficiais, identidade forte de aprovador e
transportes MCP reais. Evidências: [fase-2-fundacao.md](fase-2-fundacao.md) e
[laboratorio-fase2.md](laboratorio-fase2.md).

## Fase 3 — Especialização

Concluída no escopo inicial com agentes de Banco de Dados, QA, Segurança e Documentação. Os agentes
continuam determinísticos e não executam código externo. Evidências:
[fase-3-especializacao.md](fase-3-especializacao.md) e
[laboratorio-fase3.md](laboratorio-fase3.md).

## Fase 4 — Pilotos

Estado: em andamento.

Incrementos:

1. **Inventário público governado — concluído.** Metadados GitHub com revisão, SHA, origem, limites
   e bloqueio do piloto privado.
2. **Conteúdo textual controlado — concluído.** Coleta opt-in, UTF-8, SHA-256, redaction, quarentena
   e exclusão de dependências vendorizadas.
3. **Contexto citado para especialistas — concluído.** Orçamento determinístico,
   citações `[evidence:caminho]`, fontes persistidas e instrução explícita para tratar texto externo
   como dado não confiável.
4. **Avaliação adversarial — concluída no corpus inicial.** Prompt injection, evasões simples,
   redaction, integridade de citações e limiar de aprovação reproduzível.
5. **Piloto privado somente leitura — implementação integrada; validação externa pendente.**
   Provedor de credencial em arquivo, escopo por repositório, transporte autenticado e laboratório
   Compose; falta executar contra o GitHub com credencial real de escopo mínimo.

Critério de saída da Fase 4: os dois pilotos produzem diagnósticos rastreáveis sem escrita, com
fontes, limites, identidade de acesso e testes adversariais documentados.

## Fase 5 — Produto e operação

Concluída no escopo local, sem declarar encerrada a Fase 4:

1. **OpenTelemetry e correlação — implementado localmente.** Traces HTTP, exportação OTLP opcional,
   IDs de requisição validados e correlação com execução;
2. **Métricas e coletor local — implementado.** Métricas HTTP e de execuções, endpoint Prometheus,
   overlay Compose e laboratório reproduzível;
3. **Dashboard e alertas — implementado localmente.** Grafana provisionado, painéis operacionais,
   regras de disponibilidade, erros e latência, com validação por laboratório;
4. **API com acesso governado — implementado localmente.** API keys por arquivo secreto, papéis,
   escopo de projetos e quota por identidade;
5. **Interface operacional React — implementada localmente.** Histórico, fontes, auditorias e
   aprovações MCP integradas à API governada;
6. **Implantação Kubernetes — implementada localmente.** Base Kustomize, probes, recursos,
   políticas, migração e referências externas de segredos; validação em cluster pendente;
7. **SLOs e resposta a incidentes — implementados localmente.** Recording rules, burn rate,
   dashboard, severidades e runbooks; calibração em homologação pendente;
8. **Documentação oficial e release — concluídas.** Versão 0.2.0, documento consolidado,
   checklist e gate automatizado promovidos para `main`; tag `v0.2.0` publicada.

## Ordem imediata

1. configurar uma credencial GitHub de curta duração e escopo mínimo para `app-ams`;
2. executar o laboratório privado e registrar a validação sem persistir nem compartilhar a credencial;
3. encerrar a Fase 4 somente após confirmar os critérios de saída dos dois pilotos;
4. provisionar homologação e validar imagem, migração, rede, probes e rollback no cluster;
5. configurar identidade federada, quotas distribuídas e notificação gerenciada;
6. definir o próximo ciclo após consolidar as evidências dos testes locais e externos.

## Rastreabilidade

- [Guia de arquitetura](guia-arquitetura.md)
- [Fase 4 — piloto público](fase-4-piloto-publico.md)
- [Laboratório da Fase 4](laboratorio-fase4.md)
- [Avaliação adversarial da Fase 4](avaliacao-adversarial-fase4.md)
- [Laboratório privado da Fase 4](laboratorio-fase4-privado.md)
- [Fase 5 — produto e operação](fase-5-produto-operacao.md)
- [Documentação oficial 0.2.0](documentacao-oficial.md)
- [Checklist da release 0.2.0](release-0.2.0.md)
- [ADRs](../architecture/)
- [Histórico de alterações](../../CHANGELOG.md)
- [Política de segurança](../../SECURITY.md)
