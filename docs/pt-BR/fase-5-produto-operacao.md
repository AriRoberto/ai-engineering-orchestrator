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

## Próximos incrementos

1. métricas de dependências e canal de notificação;
2. autenticação, autorização e quotas da API;
3. interface para histórico, fontes e aprovações;
4. Kubernetes, SLOs e runbooks.

Decisão arquitetural: [ADR-007](../architecture/ADR-007-opentelemetry-observability.md).
