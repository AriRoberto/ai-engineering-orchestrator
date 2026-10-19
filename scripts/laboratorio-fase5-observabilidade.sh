#!/usr/bin/env bash
set -euo pipefail

base_url="${AIEO_BASE_URL:-http://localhost:8000}"
prometheus_url="${AIEO_PROMETHEUS_URL:-http://localhost:9090}"

echo "1/4 Iniciando API, PostgreSQL e Prometheus..."
docker compose -f compose.yaml -f compose.observability.yaml up --build -d

echo "2/4 Aguardando serviços..."
for _ in $(seq 1 30); do
  if curl --fail --silent "${base_url}/health" >/dev/null \
    && curl --fail --silent "${prometheus_url}/-/ready" >/dev/null; then
    break
  fi
  sleep 2
done
curl --fail --silent "${base_url}/health" >/dev/null
curl --fail --silent "${prometheus_url}/-/ready" >/dev/null

echo "3/4 Gerando uma execução correlacionada..."
curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"laboratorio-fase5","prompt":"Analise observabilidade e operação","demo":true}' \
  "${base_url}/v1/executions" >/dev/null

echo "4/4 Validando métricas locais e coleta Prometheus..."
curl --fail --silent "${base_url}/metrics" | grep -q 'aieo_executions_total'
for _ in $(seq 1 10); do
  if curl --fail --silent --get \
    --data-urlencode 'query=up{job="ai-engineering-orchestrator"}' \
    "${prometheus_url}/api/v1/query" | grep -q '"value".*"1"'; then
    echo ""
    echo "✓ Laboratório de observabilidade concluído com sucesso."
    echo "Prometheus: ${prometheus_url}"
    echo "Encerrar: docker compose -f compose.yaml -f compose.observability.yaml down"
    exit 0
  fi
  sleep 2
done

echo "Prometheus não confirmou o target da API." >&2
exit 1
