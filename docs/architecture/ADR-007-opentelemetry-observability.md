# ADR-007 — Observabilidade com OpenTelemetry

- Estado: aceito
- Data: 19/10/2026

## Contexto

A Fase 5 exige correlação entre chamadas HTTP, logs e execuções sem acoplar a aplicação a um
fornecedor de observabilidade. Também é necessário evitar que valores arbitrários fornecidos pelo
cliente contaminem logs e atributos de telemetria.

## Decisão

Usar OpenTelemetry para instrumentar a API FastAPI e exportar traces por OTLP/HTTP quando um
endpoint for configurado. Cada requisição recebe um UUID validado em `X-Request-ID`; valores
ausentes ou inválidos são substituídos. A resposta expõe o identificador e, quando a telemetria está
ativa, `X-Trace-ID`. Logs de execução incluem `request_id`, `trace_id` e `execution_id`.

Métricas OpenTelemetry são expostas em formato Prometheus: volume e duração HTTP usam apenas rota
normalizada, método e status; execuções usam origem e estado. Identificadores, projetos e conteúdos
não são rótulos. Um overlay Compose oferece Prometheus local sem torná-lo dependência da API.

O mesmo overlay provisiona um dashboard Grafana imutável e regras Prometheus versionadas. Os
limiares iniciais cobrem disponibilidade, taxa de erros e latência p95. O laboratório usa acesso
anônimo `Viewer`; essa configuração não é autorizada para ambientes externos.

O exporter é opcional: desenvolvimento e testes não dependem de um coletor externo. A configuração
fica em variáveis `AIEO_TELEMETRY_*` e `AIEO_OTEL_*`, sem credenciais na imagem ou no repositório.

## Consequências

- traces seguem um padrão aberto e podem ser enviados a coletores compatíveis;
- suporte pode correlacionar uma resposta com logs e uma execução;
- traces, métricas, dashboard, alertas e SLIs ficam disponíveis; notificações gerenciadas continuam
  incrementais;
- atributos devem permanecer técnicos e não incluir prompts, conteúdos ou credenciais.
