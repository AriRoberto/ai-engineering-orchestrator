#!/usr/bin/env bash
set -euo pipefail

api_url="${AIEO_LAB_API_URL:-http://localhost:8000}"
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
allowed = {"__builtins__": {}, "all": all, "any": any, "len": len}
if not eval(expression, allowed, {"data": payload}):
    raise SystemExit(f"Falha na validação: {expression}\nResposta: {payload}")
PY
}

printf '1/4 Iniciando a aplicação...\n'
docker compose up --build -d
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

printf '2/4 Coletando evidências públicas e executando especialistas...\n'
curl --fail --silent --show-error \
  -X POST "$api_url/v1/evidence/executions" \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "app-financas",
    "prompt": "Revise arquitetura, banco de dados, QA, segurança e documentação",
    "demo": true,
    "include_content": true
  }' -o "$temp_dir/execucao.json"
json_assert "$temp_dir/execucao.json" \
  'data["status"] == "COMPLETED" and data["request"]["context"]["evidence"]["provider"] == "github" and data["request"]["context"]["evidence"]["read_only"] is True and len(data["request"]["context"]["evidence"]["revision"]) == 40 and any(item["content_status"] in ("included", "redacted") and len(item["content_sha256"]) == 64 for item in data["request"]["context"]["evidence"]["files"]) and all(item.get("content") is None for item in data["request"]["context"]["evidence"]["files"] if item["content_status"] == "quarantined") and len(data["request"]["context"]["evidence_context"]) > 0 and all(item["citation"].startswith("[evidence:") and len(item["content_sha256"]) == 64 for item in data["request"]["context"]["evidence_context"]) and len(data["evidence_sources"]) == len(data["request"]["context"]["evidence_context"])'

execution_id="$(python3 - "$temp_dir/execucao.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    print(json.load(stream)["id"])
PY
)"

printf '3/4 Confirmando persistência da proveniência...\n'
curl --fail --silent --show-error \
  "$api_url/v1/executions/$execution_id?project_id=app-financas" \
  -o "$temp_dir/persistida.json"
json_assert "$temp_dir/persistida.json" \
  'data["id"] == data["id"] and data["request"]["context"]["evidence"]["total_bytes"] >= 0'
curl --fail --silent --show-error \
  "$api_url/v1/evidence/audits?project_id=app-financas" \
  -o "$temp_dir/auditoria-publica.json"
json_assert "$temp_dir/auditoria-publica.json" \
  'data[0]["status"] == "COMPLETED" and data[0]["execution_id"] is not None and len(data[0]["revision"]) == 40'

printf '4/4 Confirmando bloqueio do piloto privado...\n'
codigo_http="$(curl --silent --show-error -o "$temp_dir/privado.json" -w '%{http_code}' \
  -X POST "$api_url/v1/evidence/executions" \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"app-ams","prompt":"Revise a documentação","demo":true}')"
if [[ "$codigo_http" != "403" ]]; then
  printf 'Era esperado HTTP 403 para app-ams, mas a API retornou %s.\n' "$codigo_http"
  exit 1
fi
curl --fail --silent --show-error \
  "$api_url/v1/evidence/audits?project_id=app-ams" \
  -o "$temp_dir/auditoria-privada.json"
json_assert "$temp_dir/auditoria-privada.json" \
  'data[0]["status"] == "DENIED" and data[0]["authenticated"] is False'

printf '\n✓ Laboratório da Fase 4 concluído com sucesso.\n'
printf 'Execução: %s\n' "$execution_id"
printf 'Encerrar: make compose-down\n'
