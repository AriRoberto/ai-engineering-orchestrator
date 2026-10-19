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

echo "1/5 Iniciando API com autenticação obrigatória..."
docker compose -f compose.yaml -f compose.access.yaml up --build -d

echo "2/5 Confirmando endpoints públicos e autenticação..."
for _ in $(seq 1 30); do
  if curl --fail --silent "${base_url}/health" >/dev/null; then
    break
  fi
  sleep 2
done
curl --fail --silent "${base_url}/health" >/dev/null
test "$(curl --silent --output /dev/null --write-out '%{http_code}' "${base_url}/v1/agents")" = "401"

echo "3/5 Confirmando autorização por papel e projeto..."
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  -X POST -H "X-API-Key: ${viewer_key}" -H 'Content-Type: application/json' \
  -d '{"project_id":"laboratorio-fase2","prompt":"Teste de papel","demo":true}' \
  "${base_url}/v1/executions")" = "403"
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  -H "X-API-Key: ${operator_key}" \
  "${base_url}/v1/executions?project_id=projeto-nao-autorizado")" = "403"
curl --fail --silent -H "X-API-Key: ${operator_key}" \
  "${base_url}/v1/executions?project_id=laboratorio-fase2" >/dev/null

echo "4/5 Confirmando quota por identidade..."
curl --fail --silent -H "X-API-Key: ${quota_key}" "${base_url}/v1/agents" >/dev/null
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  -H "X-API-Key: ${quota_key}" "${base_url}/v1/agents")" = "429"

echo "5/5 Confirmando ausência de segredos nas respostas..."
response="$(curl --silent -H "X-API-Key: ${operator_key}" "${base_url}/v1/agents")"
if printf '%s' "${response}" | grep -qE "${operator_key}|${viewer_key}|${quota_key}"; then
  echo "Uma credencial foi exposta na resposta." >&2
  exit 1
fi

echo ""
echo "✓ Laboratório de acesso da Fase 5 concluído com sucesso."
