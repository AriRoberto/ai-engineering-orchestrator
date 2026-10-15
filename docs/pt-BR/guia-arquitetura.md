# Guia de arquitetura — estado atual

Este guia descreve a arquitetura implementada até o primeiro incremento da Fase 3. O histórico das
decisões permanece nos ADRs e nos documentos de cada fase.

## Visão geral

```mermaid
flowchart LR
    C[Cliente HTTP] --> API[FastAPI]
    API --> O[AIEngineeringOrchestrator]
    O --> A[Agentes especializados]
    O --> K[KnowledgeService]
    O --> L[LLMProvider]
    O --> E[(Execuções PostgreSQL)]
    K --> V[(PostgreSQL + pgvector)]
    API --> M[MCPGateway]
    M --> P[Política do projeto]
    M --> S[MCPClient]
    M --> AU[(Auditoria MCP)]
    S --> D[Servidor simulado]
```

A API valida contratos com Pydantic. O orquestrador mantém roteamento e limites determinísticos,
recupera conhecimento isolado, executa especialistas e pode pedir ao provedor de LLM uma
consolidação consultiva. Permissões nunca são concedidas pelo modelo.

## Fluxo de uma execução

```mermaid
sequenceDiagram
    participant U as Cliente
    participant A as API
    participant O as Orquestrador
    participant K as Conhecimento
    participant G as Agentes
    participant L as LLM
    participant P as PostgreSQL

    U->>A: POST /v1/executions
    A->>O: TaskRequest
    O->>K: busca híbrida por project_id
    K-->>O: trechos e fontes autorizadas
    O->>G: diagnósticos com timeout/retry
    G-->>O: resultados estruturados
    O->>L: consolidação limitada
    L-->>O: resultado e uso estimado
    O->>P: execução e linha do tempo completas
    O-->>A: Execution
```

Estados: `PENDING → PLANNING → RUNNING → COMPLETED`, com desvios explícitos para
`WAITING_APPROVAL`, `FAILED` e `CANCELLED`. Consultas e cancelamentos exigem `project_id`, aplicado
também pelo repositório.

## Agentes e orquestração

`AIEngineeringOrchestrator` recebe contratos para agentes, repositório, conhecimento e LLM. O
roteamento por palavras-chave continua determinístico. Os agentes de Engenharia de Software,
DevOps, Kubernetes, Linux/SRE, Banco de Dados, QA, Segurança e Documentação trabalham sobre
evidências fornecidas; timeout, retry e limite de passos são impostos pelo orquestrador.

O provedor simulado é o padrão. O adaptador OpenAI Agents SDK é opcional e não altera a autoridade
das políticas. Tokens são estimados explicitamente; custo oficial ainda não é calculado.

## Conhecimento e RAG

`KnowledgeService` fragmenta documentos, aplica defesa conservadora contra prompt injection e usa
busca textual e vetorial. O namespace do projeto é obrigatório. Conteúdo compartilhado somente
entra na recuperação quando a autorização foi gravada explicitamente.

O embedding determinístico de 16 dimensões existe para laboratório, não como embedding semântico de
produção. Documentos, fragmentos e feedback ficam no PostgreSQL/pgvector.

## Execuções persistentes

`ExecutionRepository` é uma porta da aplicação. Com `AIEO_DATABASE_URL`,
`PostgresExecutionRepository` guarda o payload completo e campos indexados de projeto, estado e
datas. Sem banco, `InMemoryExecutionRepository` serve como fallback explícito para testes e
desenvolvimento mínimo.

## Gateway MCP governado

```mermaid
flowchart TD
    R[Solicitação de ferramenta] --> C{Projeto configurado?}
    C -- não --> X[DENIED + auditoria]
    C -- sim --> W{Está na allowlist?}
    W -- não --> X
    W -- sim --> I[Validar input schema]
    I --> K{Risco}
    K -- destructive --> X
    K -- write em read-only --> X
    K -- write sem aprovação --> H[WAITING_APPROVAL + auditoria]
    K -- read/aprovada --> T[MCPClient.call_tool]
    T --> O[Validar output schema]
    O --> Q[COMPLETED + auditoria]
```

O catálogo é filtrado antes da exposição. A política usa nomes `servidor:ferramenta`, e o
`project_id` é injetado pelo gateway em vez de ser aceito nos argumentos controláveis pelo chamador.
O cliente atual, `SimulatedProjectMCPClient`, não usa rede nem credenciais. A porta `MCPClient`
permite adicionar Streamable HTTP ou stdio posteriormente sem retirar os controles do gateway.

Chamadas MCP são persistidas em `mcp_invocations`, inclusive negações, falhas de schema e
interrupções para aprovação. A identidade declarada em `approved_by` ainda não tem autenticação
forte; por isso integrações com efeitos reais permanecem desabilitadas.

## Governança e segurança

- leitura é o padrão;
- escrita Git em branches protegidas, merge automático e force push são bloqueados;
- ferramentas MCP fora da allowlist falham fechadas;
- schemas são verificados antes e depois de chamadas MCP;
- conteúdo RAG é tratado como dado não confiável;
- credenciais não são incluídas na imagem nem no repositório;
- containers executam sem root, sem capabilities e com filesystem somente leitura.

## Configuração e migrações

| Componente | Fonte |
|---|---|
| Limites da aplicação | `.env.example` e `infrastructure/settings.py` |
| Política Git | `configs/policies/git-governance.yaml` |
| Escopo e allowlist MCP | `configs/projects/*.yaml` |
| Conhecimento | `migrations/001_phase2_knowledge.sql` |
| Execuções | `migrations/002_phase2_executions.sql` |
| Auditoria MCP | `migrations/003_phase2_mcp_audit.sql` |

As tabelas incrementais também são criadas idempotentemente pelos repositórios para atualizar um
volume local existente sem exigir sua remoção.

## Rastreabilidade

- [ADR-001 — núcleo determinístico](../architecture/ADR-001-orchestration-framework.md)
- [ADR-002 — gateway MCP governado](../architecture/ADR-002-governed-mcp-gateway.md)
- [Fundação da Fase 2](fase-2-fundacao.md)
- [Laboratório da Fase 2](laboratorio-fase2.md)
- [Especialização da Fase 3](fase-3-especializacao.md)
- [Laboratório da Fase 3](laboratorio-fase3.md)
- [Política de segurança](../../SECURITY.md)

## Próximos limites arquiteturais

Antes de habilitar servidores MCP reais serão necessários autenticação do aprovador, retomada
durável de chamadas interrompidas, armazenamento seguro de credenciais, timeouts/retries de
transporte, proteção contra SSRF e observabilidade distribuída. Embeddings de produção e medição
oficial de custos também permanecem pendentes.
