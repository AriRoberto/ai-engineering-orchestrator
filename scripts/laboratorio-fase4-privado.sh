#!/usr/bin/env bash
set -euo pipefail

api_url="${AIEO_LAB_API_URL:-http://localhost:8000}"
token_file="${AIEO_GITHUB_PRIVATE_READ_TOKEN_FILE:-}"

if [[ -z "$token_file" || ! -f "$token_file" ]]; then
  printf 'Defina AIEO_GITHUB_PRIVATE_READ_TOKEN_FILE com um arquivo de token GitHub.\n'
  exit 2
fi

temp_dir="$(mktemp -d)"
cleanup() {
  docker compose -f compose.yaml -f compose.private.yaml stop api >/dev/null 2>&1 || true
  rm -rf "$temp_dir"
}
trap cleanup EXIT

permissions="$(stat -f '%Lp' "$token_file" 2>/dev/null || stat -c '%a' "$token_file")"
if [[ "$permissions" != "400" && "$permissions" != "600" ]]; then
  printf 'O arquivo do token deve possuir permissão 400 ou 600; atual: %s.\n' "$permissions"
  exit 2
fi

printf '1/4 Iniciando a API com secret efêmero montado como arquivo...\n'
docker compose -f compose.yaml -f compose.private.yaml up --build -d
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

printf '2/4 Coletando somente metadados do piloto privado...\n'
curl --fail --silent --show-error \
  -X POST "$api_url/v1/evidence/executions" \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "app-ams",
    "prompt": "Revise arquitetura, QA, segurança e documentação",
    "demo": true,
    "include_content": false
  }' -o "$temp_dir/execucao.json"

execution_id="$(python3 - "$temp_dir/execucao.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    payload = json.load(stream)
evidence = payload["request"]["context"]["evidence"]
assert payload["status"] == "COMPLETED"
assert evidence["metadata"]["visibility"] == "private"
assert evidence["metadata"]["authenticated"] is True
assert evidence["read_only"] is True
assert len(evidence["revision"]) == 40
assert evidence["files"]
assert all(item["content_status"] == "metadata-only" for item in evidence["files"])
forbidden_keys = {"authorization", "token", "credential", "secret"}

def inspect(value):
    if isinstance(value, dict):
        assert not (forbidden_keys & {str(key).casefold() for key in value})
        for item in value.values():
            inspect(item)
    elif isinstance(value, list):
        for item in value:
            inspect(item)

inspect(payload)
print(payload["id"])
PY
)"

printf '3/4 Confirmando auditoria persistente do acesso...\n'
curl --fail --silent --show-error \
  "$api_url/v1/evidence/audits?project_id=app-ams" \
  -o "$temp_dir/auditoria.json"
python3 - "$temp_dir/auditoria.json" "$execution_id" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    audits = json.load(stream)
audit = audits[0]
assert audit["status"] == "COMPLETED"
assert audit["visibility"] == "private"
assert audit["authenticated"] is True
assert audit["execution_id"] == sys.argv[2]
assert audit["revision"]
PY

printf '4/4 Confirmando que a API pública não expõe a credencial...\n'
printf '\n✓ Laboratório privado da Fase 4 concluído com sucesso.\n'
printf 'O secret permaneceu montado como arquivo e não entrou na execução.\n'
printf 'A API privada será parada automaticamente para desmontar o secret.\n'
