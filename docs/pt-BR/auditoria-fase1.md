# Auditoria da Fase 1

Data da auditoria: 13/10/2026.

## Estado do GitHub

- Repositório público: `AriRoberto/ai-engineering-orchestrator`.
- Branch padrão: `main`.
- Branches remotas: `main` e `develop`, ambas no commit `81698ae` no momento da auditoria.
- Os 33 arquivos da entrega inicial estavam presentes no remoto.
- GitHub Actions inicial: dois runs de CI falharam porque `pytest` não importava `apps.api.main`.
- Correção aplicada na branch de auditoria: uso de `python -m pytest` e empacotamento explícito de
  `apps`.
- GitHub Actions corrigido e validado remotamente: Ruff, 14 testes e build Docker aprovados.
- Proteção remota confirmada em `main` e `develop`: check `test`, branch atualizada, uma aprovação,
  conversas resolvidas, histórico linear e bloqueio de force push/exclusão.

## Inventário

| Componente | Arquivo responsável | Função | Status | Testes existentes | Limitações |
|---|---|---|---|---|---|
| API FastAPI | `apps/api/main.py` | Health, catálogo, criar/listar/consultar/cancelar execuções | Funcional | `tests/integration/test_api.py` | Estado global em memória; sem autenticação; cancelamento não interrompe thread já em curso |
| Modelos de domínio | `src/ai_engineering/domain/models.py` | Validação, estados, eventos, UUID e resultados | Funcional | Cobertos indiretamente por API/orquestrador | Sem modelos de custo, aprovação persistente ou dependências entre tarefas |
| Orquestrador | `src/ai_engineering/orchestrator/service.py` | Planejar, rotear, executar, retry, timeout e consolidar | Funcional | `tests/unit/test_orchestrator.py` | Sequencial; regras fixas; timeout não mata uma thread Python já iniciada |
| Contrato de agente | `src/ai_engineering/agents/base.py` | Interface comum `execute()` | Funcional | Exercitado por agentes e doubles | Sem contrato assíncrono, ferramentas, custos ou permissões por agente |
| Agente de Engenharia de Software | `src/ai_engineering/agents/specialists.py` | Detectar stack por nomes de manifestos fornecidos | Simulado | Teste de detecção de Python e JS/TS | Não lê nem analisa código ou dependências reais |
| Agente DevOps | `src/ai_engineering/agents/specialists.py` | Detectar nomes de Dockerfile e workflow fornecidos | Simulado | Exercitado no teste de integração | Não valida Docker, CI/CD, Git ou releases reais |
| Agente Kubernetes | `src/ai_engineering/agents/specialists.py` | Contar nomes com `k8s`, `helm` ou `Chart.yaml` | Simulado | Roteamento multiagente | Não interpreta YAML nem consulta cluster |
| Agente Linux/SRE | `src/ai_engineering/agents/specialists.py` | Retornar diagnóstico seguro baseado em evidência | Simulado | Roteamento disponível sem teste dedicado | Não coleta métricas, logs ou estado do host |
| Repositório de execuções | `src/ai_engineering/application/repository.py` | Armazenar cópias profundas com lock | Funcional | `tests/unit/test_isolation.py` | Volátil, processo único, sem paginação |
| Governança Git | `src/ai_engineering/governance/git.py` | Validar branch/operação e exigir aprovação | Parcial | `tests/unit/test_git_governance.py` | Não conectado a operações Git/GitHub reais; proteção remota ausente |
| Configuração runtime | `src/ai_engineering/infrastructure/settings.py`, `.env.example` | Ler `AIEO_*`, limites e modo demo | Funcional | Carregada nos testes da API | Compose sobrescreve apenas parte das variáveis; sem validação de produção |
| Logs estruturados | `src/ai_engineering/infrastructure/logging.py` | Emitir JSON com nível e timestamp | Funcional | Evidenciado pela execução Docker | Só evento final da execução; Uvicorn não unificado; sem OpenTelemetry |
| Docker runtime | `Dockerfile` | Python 3.12, usuário sem root e health check | Funcional | Build e execução manual | Dependências não travadas por lockfile; install ocorre como root no build |
| Docker Compose | `compose.yaml` | Subir API endurecida localmente | Funcional | `docker compose config`, API e health check manuais | Serviço único; sem banco/volumes; porta fixa 8000 |
| Automação local | `Makefile` | Atalhos de instalação, execução, teste e Compose | Funcional | Comandos equivalentes executados manualmente | Requer Python 3.12 para alvos locais |
| CI | `.github/workflows/ci.yml` | Lint, teste e build no GitHub Actions | Funcional | Runs local e remoto verdes | Atualizações futuras das actions devem ser avaliadas periodicamente |
| Política declarativa | `configs/policies/git-governance.yaml` | Documentar branches e operações proibidas | Parcial | Consistência conceitual coberta pelos testes Python | YAML não é carregado pelo serviço |
| Configuração app-financas | `configs/projects/app-financas.yaml` | Metadados isolados e somente leitura | Planejado | Nenhum | Não é carregada; nenhum diagnóstico real executado nesta auditoria |
| Configuração app-ams | `configs/projects/app-ams.yaml` | Metadados isolados e somente leitura | Planejado | Nenhum | Requer acesso autenticado; não é carregada; piloto não foi tocado |
| ADR de orquestração | `docs/architecture/ADR-001-orchestration-framework.md` | Registrar decisão determinística/SDK futuro | Funcional (documentação) | Não aplicável | Adaptador do SDK pertence à Fase 2 |
| Documentação geral | `README.md`, `docs/pt-BR/FASE-1.md`, `docs/en/PHASE-1.md` | Instalação, status e roadmap | Funcional (documentação) | Revisão manual | Inglês ainda resumido; precisa acompanhar a evolução do código |
| Segurança/contribuição/licença | `SECURITY.md`, `CONTRIBUTING.md`, `LICENSE`, `CHANGELOG.md` | Políticas do repositório | Funcional (documentação) | Não aplicável | Vulnerability reporting e branch protection dependem de configuração GitHub |
| Agentic RAG/LLM/MCP/PostgreSQL/pgvector | Não existem na Fase 1 | Inteligência, recuperação e integrações futuras | Planejado | Nenhum | Fase 2; não deve ser apresentado como implementado |
| Database/QA/Security/Documentation Agents | Não existem na Fase 1 | Especialistas futuros | Planejado | Nenhum | Fase 3 |
| Interface React/OpenTelemetry/Kubernetes | Não existem na Fase 1 | Produto e observabilidade futuros | Planejado | Nenhum | Fase 5 |

## O que pode ser testado agora

- health check e Swagger;
- roteamento determinístico para quatro agentes;
- execução demo com UUID, plano, eventos e resultados;
- timeout, retry, espera por aprovação e governança Git em unidade;
- build e runtime endurecido via Docker Compose.

Os exercícios reproduzíveis estão em `laboratorio-fase1.md`.

