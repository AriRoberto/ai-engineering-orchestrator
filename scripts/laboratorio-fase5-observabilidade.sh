#!/usr/bin/env bash
set -euo pipefail

base_url="${AIEO_BASE_URL:-http://localhost:8000}"
prometheus_url="${AIEO_PROMETHEUS_URL:-http://localhost:9090}"
grafana_url="${AIEO_GRAFANA_URL:-http://localhost:3300}"
alertmanager_url="${AIEO_ALERTMANAGER_URL:-http://localhost:9093}"

echo "1/7 Validando configurações Prometheus e Alertmanager..."
docker run --rm --entrypoint promtool \
  -v "${PWD}/observability/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  -v "${PWD}/observability/rules:/etc/prometheus/rules:ro" \
  prom/prometheus:v3.7.1 \
  check config /etc/prometheus/prometheus.yml
docker run --rm --entrypoint promtool \
  -v "${PWD}/observability/rules:/etc/prometheus/rules:ro" \
  prom/prometheus:v3.7.1 \
  check rules /etc/prometheus/rules/aieo-alerts.yml
docker run --rm --entrypoint promtool \
  -v "${PWD}/observability/rules:/etc/prometheus/rules:ro" \
  prom/prometheus:v3.7.1 \
  check rules /etc/prometheus/rules/aieo-slos.yml
docker run --rm --entrypoint amtool \
  -v "${PWD}/observability/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro" \
  -v "${PWD}/observability/notification-webhook-url.example:/run/secrets/notification_webhook_url:ro" \
  prom/alertmanager:v0.30.1 \
  check-config /etc/alertmanager/alertmanager.yml

echo "2/7 Iniciando API, PostgreSQL e stack de observabilidade..."
docker compose -f compose.yaml -f compose.observability.yaml up --build -d

echo "3/7 Aguardando serviços..."
for _ in $(seq 1 30); do
  if curl --fail --silent "${base_url}/health" >/dev/null \
    && curl --fail --silent "${prometheus_url}/-/ready" >/dev/null \
    && curl --fail --silent "${alertmanager_url}/-/ready" >/dev/null \
    && curl --fail --silent "${grafana_url}/api/health" >/dev/null; then
    break
  fi
  sleep 2
done
curl --fail --silent "${base_url}/health" >/dev/null
curl --fail --silent "${prometheus_url}/-/ready" >/dev/null
curl --fail --silent "${alertmanager_url}/-/ready" >/dev/null
curl --fail --silent "${grafana_url}/api/health" >/dev/null

echo "4/7 Gerando uma execução correlacionada..."
curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"laboratorio-fase5","prompt":"Analise observabilidade e operação","demo":true}' \
  "${base_url}/v1/executions" >/dev/null

echo "5/7 Validando métricas, regras e dashboard provisionado..."
curl --fail --silent "${base_url}/metrics" | grep -q 'aieo_executions_total'
curl --fail --silent "${prometheus_url}/api/v1/rules" | grep -q 'AIEOApiUnavailable'
curl --fail --silent "${prometheus_url}/api/v1/rules" | grep -q 'AIEOHighErrorRate'
curl --fail --silent "${prometheus_url}/api/v1/rules" | grep -q 'AIEOHighP95Latency'
curl --fail --silent "${prometheus_url}/api/v1/rules" | grep -q 'AIEOAvailabilityBudgetFastBurn'
curl --fail --silent "${prometheus_url}/api/v1/rules" | grep -q 'aieo:sli_availability:ratio_rate30d'
curl --fail --silent "${grafana_url}/api/search?query=AI%20Engineering%20Orchestrator" \
  | grep -q 'aieo-overview'

echo "6/7 Validando descoberta do Alertmanager..."
for _ in $(seq 1 15); do
  if curl --fail --silent "${prometheus_url}/api/v1/alertmanagers" \
    | grep -q 'alertmanager:9093'; then
    break
  fi
  sleep 1
done
curl --fail --silent "${prometheus_url}/api/v1/alertmanagers" \
  | grep -q 'alertmanager:9093'

echo "7/7 Enviando alerta sintético ao destino gerenciado..."
curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  -d '[{"labels":{"alertname":"AIEONotificationLab","service":"ai-engineering-orchestrator","severity":"warning"},"annotations":{"summary":"Validação do roteamento de alertas"},"generatorURL":"http://prometheus:9090/graph"}]' \
  "${alertmanager_url}/api/v2/alerts"
for _ in $(seq 1 15); do
  if docker compose -f compose.yaml -f compose.observability.yaml logs notification-sink \
    | grep -q 'AIEONotificationLab'; then
    break
  fi
  sleep 1
done
docker compose -f compose.yaml -f compose.observability.yaml logs notification-sink \
  | grep -q 'AIEONotificationLab'
for _ in $(seq 1 10); do
  if curl --fail --silent --get \
    --data-urlencode 'query=up{job="ai-engineering-orchestrator"}' \
    "${prometheus_url}/api/v1/query" | grep -q '"value".*"1"'; then
    echo ""
    echo "✓ Laboratório de observabilidade concluído com sucesso."
    echo "Prometheus: ${prometheus_url}"
    echo "Alertmanager: ${alertmanager_url}"
    echo "Grafana: ${grafana_url}/d/aieo-overview"
    echo "Encerrar: docker compose -f compose.yaml -f compose.observability.yaml down"
    exit 0
  fi
  sleep 2
done

echo "Prometheus não confirmou o target da API." >&2
exit 1
