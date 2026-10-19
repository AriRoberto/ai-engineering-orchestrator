# Objetivos de nível de serviço

## Escopo e janela

Os SLOs iniciais cobrem a API do AI Engineering Orchestrator em janela móvel de 30 dias. São
objetivos operacionais internos, não um SLA contratual. Antes da homologação, os valores servem para
validar telemetria, alertas e processo de resposta.

| Indicador | Objetivo | Orçamento em 30 dias | Fonte |
|---|---:|---:|---|
| Disponibilidade HTTP | 99,5% sem respostas 5xx | 0,5% | `aieo_http_server_requests_total` |
| Latência | 95% das respostas em até 2 s | 5% | `aieo_http_server_duration_seconds` |

Respostas 4xx representam rejeições válidas de cliente e não consomem o orçamento de
disponibilidade. `/metrics` e tráfego interno ainda participam dos indicadores porque a métrica não
possui uma dimensão pública/interna; separar esses fluxos é uma evolução antes de um SLA externo.
Períodos sem requisições não geram série e não devem ser interpretados como indisponibilidade.

## Política de orçamento

O orçamento de disponibilidade é `1 - 0,995 = 0,005`. Alertas multi-janela detectam consumo rápido
(14,4 vezes o orçamento em 1 h e 5 min) e sustentado (6 vezes em 6 h e 30 min). Um alerta crítico
interrompe mudanças não relacionadas até estabilização. Um alerta de aviso exige triagem no mesmo
dia útil e registro da decisão.

O painel exibe o SLI de 30 dias e o orçamento restante. Mudanças nos objetivos, janelas ou exclusões
exigem evidência histórica e atualização conjunta das regras, dashboard, runbooks e deste documento.
O Prometheus local retém apenas 24 horas e valida o encadeamento técnico; homologação e produção
precisam reter mais de 30 dias para avaliar integralmente a janela definida.
