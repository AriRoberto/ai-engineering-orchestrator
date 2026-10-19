# Fase 5 — Produto e operação

Esta fase transforma a fundação técnica e os pilotos governados em um serviço operável. Cada
incremento preserva o modo seguro, a rastreabilidade e a possibilidade de execução local.

## Incremento 1 — Correlação e traces

Estado: implementado localmente; validação em andamento.

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

## Próximos incrementos

1. métricas de latência, erros, execuções e dependências;
2. coletor local e laboratório reproduzível de observabilidade;
3. autenticação, autorização e quotas da API;
4. interface para histórico, fontes e aprovações;
5. Kubernetes, SLOs, alertas e runbooks.

Decisão arquitetural: [ADR-007](../architecture/ADR-007-opentelemetry-observability.md).
