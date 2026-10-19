#!/usr/bin/env bash
set -euo pipefail

api_url="${AIEO_LAB_API_URL:-http://localhost:8000}"
project_id="laboratorio-fase2"
temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT

json_assert() {
  local arquivo="$1"
  local expressao="$2"
  python3 - "$arquivo" "$expressao" <<'PY'
import json
import sys

path, expression = sys.argv[1:]
with open(path, encoding="utf-8") as stream:
    payload = json.load(stream)
if not eval(
    expression,
    {"__builtins__": {}, "all": all, "len": len, "set": set},
    {"data": payload},
):
    raise SystemExit(f"Falha na validação: {expression}\nResposta: {payload}")
PY
}

printf '1/5 Iniciando a aplicação completa...\n'
docker compose up --build -d

printf '2/5 Aguardando o health check...\n'
for tentativa in $(seq 1 30); do
  if curl --fail --silent "$api_url/health" -o "$temp_dir/health.json"; then
    break
  fi
  if [[ "$tentativa" == "30" ]]; then
    printf 'A API não ficou disponível. Consulte: make logs\n'
    exit 1
  fi
  sleep 1
done

printf '3/5 Confirmando o catálogo com oito especialistas...\n'
curl --fail --silent --show-error "$api_url/v1/agents" -o "$temp_dir/agentes.json"
json_assert "$temp_dir/agentes.json" \
  'len(data) == 8 and {"database", "qa", "security", "documentation"} <= set(item["id"] for item in data)'

printf '4/5 Executando o diagnóstico especializado da Fase 3...\n'
curl --fail --silent --show-error \
  -X POST "$api_url/v1/executions" \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "laboratorio-fase2",
    "prompt": "Revise banco de dados, QA, segurança e documentação",
    "demo": true,
    "context": {
      "files": [
        "migrations/001_schema.sql",
        "tests/test_api.py",
        ".github/workflows/ci.yml",
        "SECURITY.md",
        "README.md",
        "CHANGELOG.md"
      ]
    }
  }' -o "$temp_dir/execucao.json"
json_assert "$temp_dir/execucao.json" \
  'data["status"] == "COMPLETED" and set(item["agent"] for item in data["results"]) == {"database", "qa", "security", "documentation"} and all(len(item["findings"]) >= 2 for item in data["results"])'

execution_id="$(python3 - "$temp_dir/execucao.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    print(json.load(stream)["id"])
PY
)"

printf '5/5 Confirmando persistência e isolamento da execução...\n'
curl --fail --silent --show-error \
  "$api_url/v1/executions/$execution_id?project_id=$project_id" \
  -o "$temp_dir/persistida.json"
json_assert "$temp_dir/persistida.json" \
  'data["id"] == data["id"] and len(data["results"]) == 4'
codigo_http="$(curl --silent -o /dev/null -w '%{http_code}' \
  "$api_url/v1/executions/$execution_id?project_id=projeto-isolado")"
if [[ "$codigo_http" != "404" ]]; then
  printf 'Era esperado HTTP 404 para outro projeto, mas a API retornou %s.\n' "$codigo_http"
  exit 1
fi

printf '\n✓ Laboratório da Fase 3 concluído com sucesso.\n'
printf 'Execução: %s\n' "$execution_id"
printf 'Swagger: %s/docs\n' "$api_url"
printf 'Encerrar: make compose-down\n'
