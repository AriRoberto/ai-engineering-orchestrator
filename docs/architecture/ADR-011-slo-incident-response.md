# ADR-011 — SLOs e resposta a incidentes

## Contexto

Alertas por limiar isolado detectam sintomas, mas não expressam confiabilidade ao longo do tempo
nem orientam prioridade operacional. O projeto precisa relacionar telemetria, orçamento de erro e
ações humanas reproduzíveis antes de operar um piloto externo.

## Decisão

Adotar janela móvel de 30 dias, SLO inicial de 99,5% de disponibilidade HTTP sem 5xx e objetivo de
95% das respostas em até dois segundos. Regras Prometheus versionadas calculam SLIs e alertam por
burn rate em duas janelas. Cada alerta referencia um runbook; severidade, evidências mínimas,
mitigação, encerramento e pós-incidente seguem um processo comum.

Respostas 4xx não consomem o orçamento de disponibilidade. Esses objetivos são internos até haver
tráfego e histórico de homologação suficientes para revisão.

## Consequências

- decisões operacionais passam a considerar orçamento, não apenas eventos isolados;
- buckets explícitos tornam o limiar de dois segundos mensurável;
- alertas rápidos congelam mudanças não relacionadas durante mitigação;
- métricas ainda precisam separar tráfego interno e externo antes de um SLA público;
- canal gerenciado de notificação e gestão formal de plantão permanecem dependentes da plataforma.
