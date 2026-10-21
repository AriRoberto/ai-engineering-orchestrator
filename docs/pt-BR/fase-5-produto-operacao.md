# Fase 5 — Produto e operação

Esta fase transforma a fundação técnica e os pilotos governados em um serviço operável. Cada
incremento preserva o modo seguro, a rastreabilidade e a possibilidade de execução local.

## Incremento 1 — Correlação e traces

Estado: concluído.

Entregas:

- instrumentação automática da API FastAPI com OpenTelemetry;
- recursos de trace identificados por serviço e ambiente;
- exportação opcional por OTLP/HTTP;
- `X-Request-ID` validado e propagado em todas as respostas;
- `X-Trace-ID` para correlação com o backend de observabilidade;
- logs de execução correlacionados com requisição, trace e execução;
- testes de propagação e substituição de identificadores inválidos.

O exporter não é ativado sem `AIEO_OTEL_EXPORTER_OTLP_ENDPOINT`. Nenhum prompt, conteúdo de
evidência ou segredo é adicionado aos atributos de trace.

## Incremento 2 — Métricas e coletor local

Estado: concluído.

Entregas:

- contador de requisições por método, rota normalizada e status;
- histograma de duração HTTP;
- contador de execuções por origem e estado final;
- endpoint Prometheus em `GET /metrics`;
- overlay Compose com Prometheus e retenção efêmera de 24 horas;
- laboratório reproduzível em `make lab-fase5-observabilidade`.

Os rótulos não incluem `project_id`, prompt, URL recebida, conteúdo, UUID ou credencial. Essa escolha
mantém baixa cardinalidade e reduz exposição de dados operacionais.

Em 19/10/2026, o laboratório confirmou a geração das métricas pela API, a descoberta do target pelo
Prometheus e o resultado `up=1` consultado pela API do coletor.

## Incremento 3 — Dashboard e alertas

Estado: concluído.

Entregas:

- dashboard Grafana provisionado como código, sem configuração manual;
- painéis para requisições, erros 5xx, latência p95, execuções e disponibilidade;
- alerta crítico quando a API fica indisponível por um minuto;
- alertas de aviso para taxa de erros acima de 5% e p95 acima de dois segundos;
- validação das regras com `promtool` e consulta das APIs do Prometheus e Grafana no laboratório;
- Grafana local somente leitura e com acesso anônimo limitado a `Viewer`.

O acesso anônimo existe exclusivamente no overlay local de laboratório. Uma implantação externa
deve usar autenticação, TLS, persistência e canal de notificação gerenciado.

Em 19/10/2026, o laboratório validou as três regras com `promtool`, confirmou seu carregamento pela
API do Prometheus e localizou o dashboard `aieo-overview` provisionado pela API do Grafana.

## Incremento 4 — Autenticação, autorização e quotas

Estado: concluído.

Entregas:

- API key obrigatória para `/v1` quando `AIEO_API_AUTH_ENABLED=true`;
- arquivo secreto externo contendo apenas hashes SHA-256, nunca chaves em texto aberto;
- papéis `viewer` e `operator`;
- allowlist de projetos por identidade;
- quota por minuto com resposta HTTP 429 e `Retry-After`;
- falha de inicialização quando autenticação é ativada sem configuração válida;
- laboratório reproduzível em `make lab-fase5-acesso`.

O arquivo secreto contém `key_id`, `key_sha256`, `role`, `projects` e `requests_per_minute`. Gere o
hash com `printf '%s' "$API_KEY" | shasum -a 256`, sem gravar a chave no repositório. O overlay
`compose.access.yaml` monta o arquivo somente leitura. `/health`, `/metrics` e a documentação
OpenAPI permanecem públicos; todos os endpoints `/v1` são protegidos.

Em 19/10/2026, o laboratório confirmou health público, HTTP 401 sem credencial, HTTP 403 para papel
ou projeto não autorizado, HTTP 429 após exceder a quota e ausência das chaves nas respostas. O
contrato OpenAPI declara `X-API-Key` para as operações `/v1` quando o controle está habilitado.

## Incremento 5 — Interface operacional

Estado: concluído.

Entregas:

- aplicação React compilada e servida em `/ui/` pela mesma imagem da API;
- histórico e detalhes de execuções;
- fontes de evidência e auditorias por projeto;
- fila de aprovações MCP;
- aprovação por ID, vinculada por `approval_of` e protegida contra repetição;
- API key mantida somente na sessão da aba;
- layout responsivo e link para o dashboard Grafana.

A interface não decide permissões: toda leitura e aprovação passa novamente pela autenticação,
papel, escopo de projeto e quota do backend. A chave em `sessionStorage` é uma solução de laboratório;
identidade federada e sessão segura continuam necessárias antes de exposição pública.

Em 19/10/2026, o laboratório compilou a interface com Vite, confirmou sua publicação em `/ui/`,
aprovou uma invocação MCP pendente e validou o vínculo `approval_of`, o estado final `COMPLETED` e
a rejeição de uma segunda aprovação. A suíte completa registrou 74 testes aprovados e 91% de
cobertura.

## Incremento 6 — Implantação Kubernetes

Estado: concluído localmente; implantação em cluster pendente.

Entregas:

- base Kustomize independente de provedor;
- Deployment com duas réplicas, recursos, três probes e filesystem somente leitura;
- endpoint `/ready` que verifica a conexão com o PostgreSQL;
- ServiceAccount sem token automático e namespace com Pod Security `restricted`;
- Service interno, PodDisruptionBudget e NetworkPolicy;
- segredos referenciados, nunca materializados nos manifests;
- Job idempotente de migração usando a mesma imagem da aplicação;
- laboratório estático reproduzível em `make lab-fase5-kubernetes`.

Em 19/10/2026, o laboratório renderizou oito recursos, confirmou os controles de menor privilégio,
as referências externas de segredos, as probes, os limites e o Job de migração. A implantação real
permanece dependente de cluster, registry, PostgreSQL, TLS e overlays da plataforma.

## Incremento 7 — SLOs e resposta a incidentes

Estado: concluído localmente; calibração com tráfego real pendente.

Entregas:

- SLO de 99,5% de disponibilidade e 95% das respostas em até dois segundos;
- SLIs de cinco minutos a 30 dias como recording rules Prometheus;
- alertas multi-janela para consumo rápido e sustentado do orçamento de erro;
- buckets explícitos de latência adequados ao limiar de dois segundos;
- painéis de disponibilidade e orçamento restante no Grafana;
- runbooks de disponibilidade, erros 5xx e latência;
- processo comum de severidade, comunicação, evidências, mitigação e encerramento;
- URLs de runbook incorporadas em todos os alertas.

Em 19/10/2026, o `promtool` validou onze regras, o dashboard passou pela validação JSON e o
laboratório foi ampliado para verificar o carregamento dos SLIs e alertas de burn rate. Os objetivos
são internos e deverão ser calibrados após histórico de homologação.

## Incremento 8 — Documentação oficial e release

Estado: concluído e promovido para `main`.

Entregas:

- versão 0.2.0 consistente no pacote Python, API, UI e manifests;
- documentação oficial consolidada com operação, segurança e limites;
- checklist de promoção com evidências e pendências externas explícitas;
- gate automatizado de versões, arquivos estruturados e links Markdown;
- gate executado pelo CI e disponível em `make validar-release`;
- estratégia de promoção única de `develop` para `main`.

## Próximos incrementos

1. métricas de dependências, notificação gerenciada, identidade federada e quotas distribuídas;
2. validar Kubernetes, SLOs e piloto privado nos ambientes externos correspondentes;
3. definir o escopo da próxima versão somente após registrar os resultados locais e externos.

Decisões arquiteturais: [ADR-007](../architecture/ADR-007-opentelemetry-observability.md),
[ADR-008](../architecture/ADR-008-api-access-control.md) e
[ADR-009](../architecture/ADR-009-operations-ui.md) e
[ADR-010](../architecture/ADR-010-kubernetes-deployment.md) e
[ADR-011](../architecture/ADR-011-slo-incident-response.md).
