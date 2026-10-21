#!/usr/bin/env bash
set -euo pipefail

cluster_name="${AIEO_LOCAL_CLUSTER_NAME:-aieo-local}"
context="kind-${cluster_name}"
namespace="ai-engineering-orchestrator"
image="ai-engineering-orchestrator:local"
token_file="${AIEO_GITHUB_PRIVATE_READ_TOKEN_FILE:-${HOME}/.config/aieo/github-app-ams-token}"
local_api_key_file="${AIEO_LOCAL_API_KEY_FILE:-${HOME}/.config/aieo/local-api-key}"
temp_dir="$(mktemp -d)"
port_forward_pid=""
github_secret_created="false"

cleanup() {
  if [[ -n "${port_forward_pid}" ]]; then
    kill "${port_forward_pid}" >/dev/null 2>&1 || true
    wait "${port_forward_pid}" >/dev/null 2>&1 || true
  fi
  rm -rf "${temp_dir}"
}
trap cleanup EXIT

for command in docker kind kubectl curl openssl shasum; do
  command -v "${command}" >/dev/null || {
    echo "Comando obrigatório ausente: ${command}" >&2
    exit 1
  }
done

echo "1/10 Preparando cluster kind isolado ${cluster_name}..."
if ! kind get clusters | grep -Fxq "${cluster_name}"; then
  kind create cluster --name "${cluster_name}" --wait 120s
fi
kubectl config use-context "${context}" >/dev/null
kubectl wait --for=condition=Ready nodes --all --timeout=120s

echo "2/10 Construindo e carregando a imagem local..."
docker build -t "${image}" .
kind load docker-image "${image}" --name "${cluster_name}"

echo "3/10 Criando secrets efêmeros sem versionar valores..."
kubectl create namespace "${namespace}" --dry-run=client -o yaml | kubectl apply -f -
database_password="$(openssl rand -hex 24)"
operator_key="$(openssl rand -hex 24)"
operator_hash="$(printf '%s' "${operator_key}" | shasum -a 256 | awk '{print $1}')"
mkdir -p "$(dirname "${local_api_key_file}")"
umask 077
printf '%s' "${operator_key}" >"${local_api_key_file}"
chmod 600 "${local_api_key_file}"
printf '%s\n' "{\"keys\":[{\"key_id\":\"operator-local\",\"key_sha256\":\"${operator_hash}\",\"role\":\"operator\",\"projects\":[\"laboratorio-fase2\",\"app-financas\",\"app-ams\"],\"requests_per_minute\":120}]}" >"${temp_dir}/api-keys.json"
kubectl -n "${namespace}" create secret generic postgres-credentials \
  --from-literal=database=aieo --from-literal=username=aieo \
  --from-literal=password="${database_password}" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "${namespace}" create secret generic orchestrator-runtime \
  --from-literal=database-url="postgresql+psycopg://aieo:${database_password}@postgres:5432/aieo" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "${namespace}" create secret generic orchestrator-api-keys \
  --from-file=api-keys.json="${temp_dir}/api-keys.json" --dry-run=client -o yaml | kubectl apply -f -
unset database_password operator_hash

if [[ -s "${token_file}" ]] && grep -Eq '^github_pat_[[:alnum:]_]+$' "${token_file}"; then
  kubectl -n "${namespace}" create secret generic orchestrator-github-private-read \
    --from-file=token="${token_file}" --dry-run=client -o yaml | kubectl apply -f -
  github_secret_created="true"
else
  kubectl -n "${namespace}" delete secret orchestrator-github-private-read \
    --ignore-not-found >/dev/null
fi

echo "4/10 Iniciando PostgreSQL/pgvector e aguardando prontidão..."
kubectl -n "${namespace}" delete statefulset postgres --ignore-not-found --wait=true >/dev/null
kubectl -n "${namespace}" apply -f k8s/overlays/local/postgres.yaml
kubectl -n "${namespace}" rollout status statefulset/postgres --timeout=180s

echo "5/10 Aplicando migração e API com controles restritos..."
kubectl -n "${namespace}" delete deployment orchestrator-api --ignore-not-found --wait=true >/dev/null
kubectl -n "${namespace}" delete job orchestrator-migrations --ignore-not-found >/dev/null
kubectl apply -k k8s/overlays/local
kubectl -n "${namespace}" wait --for=condition=complete job/orchestrator-migrations --timeout=180s
kubectl -n "${namespace}" rollout status deployment/orchestrator-api --timeout=180s

echo "6/10 Validando saúde, prontidão, autenticação e interface..."
kubectl -n "${namespace}" port-forward service/orchestrator-api 18080:80 \
  >"${temp_dir}/port-forward.log" 2>&1 &
port_forward_pid=$!
for _ in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:18080/ready >/dev/null; then
    break
  fi
  sleep 2
done
curl --fail --silent http://127.0.0.1:18080/health >/dev/null
curl --fail --silent http://127.0.0.1:18080/ready >/dev/null
curl --fail --silent http://127.0.0.1:18080/ui/ | grep -q 'AI Engineering Orchestrator'
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  http://127.0.0.1:18080/v1/agents)" = "401"
curl --fail --silent -H "X-API-Key: ${operator_key}" \
  http://127.0.0.1:18080/v1/agents >/dev/null

echo "7/10 Executando piloto público dentro do cluster..."
public_response="$(curl --fail --silent -X POST \
  -H "X-API-Key: ${operator_key}" -H 'Content-Type: application/json' \
  -d '{"project_id":"app-financas","prompt":"Validação integrada no cluster local","demo":true,"include_content":false}' \
  http://127.0.0.1:18080/v1/evidence/executions)"
printf '%s' "${public_response}" | grep -q '"visibility":"public"'
printf '%s' "${public_response}" | grep -q '"status":"COMPLETED"'

echo "8/10 Executando piloto privado quando a credencial temporária está disponível..."
if [[ "${github_secret_created}" == "true" ]]; then
  private_response="$(curl --fail --silent -X POST \
    -H "X-API-Key: ${operator_key}" -H 'Content-Type: application/json' \
    -d '{"project_id":"app-ams","prompt":"Validação privada no cluster local","demo":true,"include_content":false}' \
    http://127.0.0.1:18080/v1/evidence/executions)"
  printf '%s' "${private_response}" | grep -q '"visibility":"private"'
  printf '%s' "${private_response}" | grep -q '"authenticated":true'
  printf '%s' "${private_response}" | grep -q '"status":"COMPLETED"'
  if printf '%s' "${private_response}" | grep -q 'github_pat_'; then
    echo "A resposta privada expôs um marcador de credencial." >&2
    exit 1
  fi
else
  echo "Credencial privada ausente; etapa privada registrada como não executada."
fi
unset public_response private_response operator_key

echo "9/10 Validando rollout e rollback da API..."
kubectl -n "${namespace}" rollout restart deployment/orchestrator-api
kubectl -n "${namespace}" rollout status deployment/orchestrator-api --timeout=180s
kubectl -n "${namespace}" rollout undo deployment/orchestrator-api
kubectl -n "${namespace}" rollout status deployment/orchestrator-api --timeout=180s

echo "10/10 Removendo a credencial GitHub do cluster e preservando o ambiente..."
if [[ "${github_secret_created}" == "true" ]]; then
  kubectl -n "${namespace}" delete secret orchestrator-github-private-read
  kubectl -n "${namespace}" rollout restart deployment/orchestrator-api
  kubectl -n "${namespace}" rollout status deployment/orchestrator-api --timeout=180s
fi
kubectl -n "${namespace}" get pods,services,jobs

echo ""
echo "✓ Cluster local validado com migração, probes, autenticação, pilotos e rollback."
echo "Contexto: ${context}"
echo "O cluster foi mantido ativo; a credencial GitHub temporária foi removida do Kubernetes."
echo "API key local protegida em: ${local_api_key_file}"
