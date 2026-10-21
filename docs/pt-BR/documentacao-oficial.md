# AI Engineering Orchestrator — documentação oficial 0.2.0

Estado da edição: publicada como `v0.2.0` em 20/10/2026.

## Visão do produto

O AI Engineering Orchestrator recebe uma solicitação de engenharia, cria um plano limitado,
seleciona especialistas e preserva execução, evidências, fontes e decisões. O núcleo é determinístico:
LLMs podem sugerir conteúdo, mas não concedem permissões nem ignoram políticas.

A versão 0.2.0 consolida a fundação das fases 1 a 3, os pilotos governados da Fase 4 e o escopo local
de produto e operação da Fase 5. O piloto privado foi validado após a publicação da tag, com
credencial temporária somente leitura; identidade federada e homologação em Kubernetes continuam
dependentes de infraestrutura adicional.

## Capacidades entregues

- API FastAPI, oito agentes especializados e estados auditáveis;
- PostgreSQL/pgvector, conhecimento isolado, RAG e memória de execuções;
- gateway MCP com allowlist, schemas, aprovação e auditoria;
- coleta GitHub somente leitura, conteúdo controlado, citações e avaliação adversarial;
- OpenTelemetry, métricas Prometheus, dashboard Grafana, alertas, SLOs e runbooks;
- API keys com papéis, projetos e quotas locais;
- interface React para execuções, fontes, auditorias e aprovações;
- base Kubernetes/Kustomize com menor privilégio, probes e migrações.

## Primeira execução

Pré-requisitos: Docker com Compose e portas 8000, 5432, 9090 e 3300 disponíveis quando os overlays
de observabilidade forem usados.

```bash
cp .env.example .env
docker compose up --build -d
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/ready
```

API: `http://localhost:8000/docs`. Interface: `http://localhost:8000/ui/`. Encerre com
`docker compose down`. O modo Compose é de desenvolvimento; não exponha suas credenciais, banco ou
painéis diretamente à internet.

## Arquitetura e dados

A API coordena domínio, agentes, conhecimento, evidências, LLM e MCP por contratos explícitos.
PostgreSQL preserva conhecimento, execuções e auditorias; nenhum projeto consulta dados privados de
outro projeto. Migrações SQL idempotentes ficam em `migrations/` e o Job Kubernetes as executa antes
da aplicação. A visão detalhada está no [guia de arquitetura](guia-arquitetura.md) e as decisões nos
[ADRs](../architecture/).

## Segurança

Leitura é o padrão. Escrita exige política e aprovação, operações destrutivas são bloqueadas e texto
externo é dado não confiável. Segredos não pertencem ao Git, à imagem, aos logs, aos traces nem às
métricas. Consulte [SECURITY.md](../../SECURITY.md), especialmente antes de ativar acesso privado,
LLM real, MCP real, autenticação ou implantação Kubernetes.

## Operação

- saúde do processo: `/health`;
- prontidão com PostgreSQL: `/ready`;
- métricas: `/metrics`;
- [objetivos de nível de serviço](slo.md);
- [runbooks e resposta a incidentes](runbooks/README.md);
- [implantação Kubernetes](../../k8s/README.md);
- laboratório de observabilidade: `make lab-fase5-observabilidade`;
- laboratório de acesso: `make lab-fase5-acesso`;
- laboratório Kubernetes: `make lab-fase5-kubernetes`.

## Governança da entrega

Cada incremento exige implementação, segurança proporcional, testes, laboratório, documentação e
CHANGELOG. `develop` recebe incrementos aprovados; `main` recebe somente promoções de release após o
gate completo. Branches temporárias são apagadas depois do merge.

## Limites conhecidos

- novas execuções do piloto privado requerem uma credencial GitHub temporária, escopada e somente
  leitura; a validação operacional inicial foi concluída em 20/10/2026;
- API keys e quotas são locais por réplica; produção requer identidade federada e quota distribuída;
- o Prometheus local retém 24 horas, menos que a janela de SLO de 30 dias;
- o Kubernetes base não inclui cluster, registry, PostgreSQL, Ingress, TLS ou secret manager;
- LLM, MCP e embeddings reais exigem adaptadores, custos, credenciais e avaliações adicionais;
- não há SLA público, certificação de segurança ou garantia de operação produtiva nesta versão.

## Rastreabilidade

- [Plano de implementação](plano-de-implementacao.md)
- [Fase 5 — produto e operação](fase-5-produto-operacao.md)
- [CHANGELOG](../../CHANGELOG.md)
- [Política de contribuição](../../CONTRIBUTING.md)
- [Licença](../../LICENSE)
