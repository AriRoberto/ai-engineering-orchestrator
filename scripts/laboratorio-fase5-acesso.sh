#!/usr/bin/env bash
set -euo pipefail

base_url="${AIEO_BASE_URL:-http://localhost:8000}"
secret_dir="$(mktemp -d)"
keys_file="${secret_dir}/api-keys.json"
operator_key="$(openssl rand -hex 24)"
viewer_key="$(openssl rand -hex 24)"
quota_key="$(openssl rand -hex 24)"

cleanup() {
  docker compose -f compose.yaml -f compose.access.yaml down >/dev/null 2>&1 || true
  rm -rf "${secret_dir}"
}
trap cleanup EXIT

operator_hash="$(printf '%s' "${operator_key}" | shasum -a 256 | awk '{print $1}')"
viewer_hash="$(printf '%s' "${viewer_key}" | shasum -a 256 | awk '{print $1}')"
quota_hash="$(printf '%s' "${quota_key}" | shasum -a 256 | awk '{print $1}')"

umask 077
printf '%s\n' "{\"keys\":[
  {\"key_id\":\"operator-lab\",\"key_sha256\":\"${operator_hash}\",\"role\":\"operator\",\"projects\":[\"laboratorio-fase2\"],\"requests_per_minute\":20},
  {\"key_id\":\"viewer-lab\",\"key_sha256\":\"${viewer_hash}\",\"role\":\"viewer\",\"projects\":[\"laboratorio-fase2\"],\"requests_per_minute\":20},
  {\"key_id\":\"quota-lab\",\"key_sha256\":\"${quota_hash}\",\"role\":\"operator\",\"projects\":[\"laboratorio-fase2\"],\"requests_per_minute\":1}
]}" >"${keys_file}"
export AIEO_API_KEYS_FILE_HOST="${keys_file}"

echo "1/6 Iniciando API com autenticação obrigatória e interface..."
docker compose -f compose.yaml -f compose.access.yaml up --build -d

echo "2/6 Confirmando endpoints públicos e autenticação..."
for _ in $(seq 1 30); do
  if curl --fail --silent "${base_url}/health" >/dev/null; then
    break
  fi
  sleep 2
done
curl --fail --silent "${base_url}/health" >/dev/null
test "$(curl --silent --output /dev/null --write-out '%{http_code}' "${base_url}/v1/agents")" = "401"

echo "3/6 Confirmando autorização por papel e projeto..."
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  -X POST -H "X-API-Key: ${viewer_key}" -H 'Content-Type: application/json' \
  -d '{"project_id":"laboratorio-fase2","prompt":"Teste de papel","demo":true}' \
  "${base_url}/v1/executions")" = "403"
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  -H "X-API-Key: ${operator_key}" \
  "${base_url}/v1/executions?project_id=projeto-nao-autorizado")" = "403"
curl --fail --silent -H "X-API-Key: ${operator_key}" \
  "${base_url}/v1/executions?project_id=laboratorio-fase2" >/dev/null

echo "4/6 Confirmando quota por identidade..."
curl --fail --silent -H "X-API-Key: ${quota_key}" "${base_url}/v1/agents" >/dev/null
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  -H "X-API-Key: ${quota_key}" "${base_url}/v1/agents")" = "429"

echo "5/6 Confirmando fluxo de aprovação e interface operacional..."
pending="$(curl --fail --silent -H "X-API-Key: ${operator_key}" \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"laboratorio-fase2","server":"project-catalog","tool":"publish_change","arguments":{"branch":"agents/devops/feat-ui-lab"}}' \
  "${base_url}/v1/mcp/invocations")"
pending_id="$(printf '%s' "${pending}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
approved="$(curl --fail --silent -H "X-API-Key: ${operator_key}" \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"laboratorio-fase2","approved_by":"laboratorio@example.test"}' \
  "${base_url}/v1/mcp/invocations/${pending_id}/approve")"
printf '%s' "${approved}" | grep -q '"status":"COMPLETED"'
curl --fail --silent --location "${base_url}/ui/" | grep -q 'AI Engineering Orchestrator'

echo "6/6 Confirmando ausência de segredos nas respostas..."
response="$(curl --silent -H "X-API-Key: ${operator_key}" "${base_url}/v1/agents")"
if printf '%s' "${response}" | grep -qE "${operator_key}|${viewer_key}|${quota_key}"; then
  echo "Uma credencial foi exposta na resposta." >&2
  exit 1
fi

echo ""
echo "✓ Laboratório de acesso da Fase 5 concluído com sucesso."
