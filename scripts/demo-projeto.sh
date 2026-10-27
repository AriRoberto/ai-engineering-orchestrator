#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repository="AriRoberto/app-financas"
project_id=""
branch=""
prompt="Revise arquitetura, banco de dados, qualidade, segurança, documentação e operação. Cite as evidências e priorize os riscos encontrados."
include_content=true
open_browser=false
private_repository=false
token_file=""
openai_key_file=""
openai_model=""
base_url="${AIEO_DEMO_BASE_URL:-http://localhost:8000}"
compose=(docker compose --project-directory "${root}" -f "${root}/compose.yaml" -f "${root}/compose.demo.yaml")

usage() {
  cat <<'EOF'
Uso: ./scripts/demo-projeto.sh [opções]

  --repository OWNER/REPO  Repositório público do GitHub (padrão: AriRoberto/app-financas)
  --project-id ID          ID local; por padrão deriva do nome do repositório
  --branch BRANCH          Branch; por padrão usa a default_branch informada pelo GitHub
  --prompt TEXTO           Pedido da análise
  --metadata-only          Não baixa conteúdo textual dos arquivos
  --private                Trata o repositório como privado e força somente metadados
  --token-file CAMINHO     Token GitHub fine-grained somente leitura (exigido com --private)
  --openai-key-file ARQ    Ativa o LLM real com a chave OpenAI lida deste arquivo
  --model MODELO           Modelo OpenAI (obrigatório com --openai-key-file)
  --open-browser           Abre a interface no navegador ao concluir (macOS)
  -h, --help               Mostra esta ajuda
EOF
}

while (($#)); do
  case "$1" in
    --repository) repository="${2:-}"; shift 2 ;;
    --project-id) project_id="${2:-}"; shift 2 ;;
    --branch) branch="${2:-}"; shift 2 ;;
    --prompt) prompt="${2:-}"; shift 2 ;;
    --metadata-only) include_content=false; shift ;;
    --private) private_repository=true; include_content=false; shift ;;
    --token-file) token_file="${2:-}"; shift 2 ;;
    --openai-key-file) openai_key_file="${2:-}"; shift 2 ;;
    --model) openai_model="${2:-}"; shift 2 ;;
    --open-browser) open_browser=true; shift ;;
    -h | --help) usage; exit 0 ;;
    *) printf 'Opção desconhecida: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

cd "${root}"
for command in docker curl python3; do
  command -v "${command}" >/dev/null || {
    printf 'Comando obrigatório ausente: %s\n' "${command}" >&2
    exit 1
  }
done
docker info >/dev/null 2>&1 || {
  printf 'Docker não está disponível. Abra o Docker Desktop e tente novamente.\n' >&2
  exit 1
}

if [[ ! "${repository}" =~ ^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}$ ]]; then
  printf 'Repositório inválido; use OWNER/REPO.\n' >&2
  exit 2
fi

real_llm=false
if [[ -n "${openai_key_file}" ]]; then
  real_llm=true
  if [[ ! -f "${openai_key_file}" || -z "${openai_model}" ]]; then
    printf -- '--openai-key-file deve existir e --model é obrigatório no modo real.\n' >&2
    exit 2
  fi
  permissions="$(stat -f '%Lp' "${openai_key_file}" 2>/dev/null || stat -c '%a' "${openai_key_file}")"
  if [[ "${permissions}" != "400" && "${permissions}" != "600" ]]; then
    printf 'O arquivo da chave OpenAI deve possuir permissão 400 ou 600; atual: %s.\n' \
      "${permissions}" >&2
    exit 2
  fi
  if [[ ! "${openai_model}" =~ ^[A-Za-z0-9._-]{2,100}$ ]]; then
    printf 'Nome de modelo OpenAI inválido.\n' >&2
    exit 2
  fi
  export AIEO_DEMO_OPENAI_API_KEY_FILE="${openai_key_file}"
  export AIEO_DEMO_OPENAI_MODEL="${openai_model}"
  compose+=(-f "${root}/compose.demo.openai.yaml")
elif [[ -n "${openai_model}" ]]; then
  printf -- '--model só pode ser usado com --openai-key-file.\n' >&2
  exit 2
fi
owner="${repository%%/*}"
repo="${repository#*/}"
if [[ -z "${project_id}" ]]; then
  project_id="$(printf '%s' "${repo}" | tr '[:upper:]_' '[:lower:]-' | sed 's/[^a-z0-9-]//g')"
fi
if [[ ! "${project_id}" =~ ^[a-z0-9][a-z0-9-]{1,62}$ ]]; then
  printf 'project-id inválido: use 2 a 63 caracteres minúsculos, números ou hífen.\n' >&2
  exit 2
fi
if ((${#prompt} < 3 || ${#prompt} > 10000)); then
  printf 'O prompt deve ter entre 3 e 10000 caracteres.\n' >&2
  exit 2
fi

visibility="public"
if [[ "${private_repository}" == true ]]; then
  visibility="private"
  if [[ -z "${token_file}" || ! -f "${token_file}" ]]; then
    printf -- '--token-file deve apontar para um arquivo existente no modo privado.\n' >&2
    exit 2
  fi
  permissions="$(stat -f '%Lp' "${token_file}" 2>/dev/null || stat -c '%a' "${token_file}")"
  if [[ "${permissions}" != "400" && "${permissions}" != "600" ]]; then
    printf 'O arquivo do token deve possuir permissão 400 ou 600; atual: %s.\n' \
      "${permissions}" >&2
    exit 2
  fi
  export AIEO_DEMO_PRIVATE_REPOSITORY="${repository}"
  export AIEO_DEMO_GITHUB_TOKEN_FILE="${token_file}"
  compose+=(-f "${root}/compose.demo.private.yaml")
fi

temp_dir="$(mktemp -d)"
trap 'rm -rf "${temp_dir}"' EXIT
if [[ "${private_repository}" == false ]]; then
  printf '1/7 Validando o repositório público %s...\n' "${repository}"
  curl --fail --silent --show-error \
    -H 'Accept: application/vnd.github+json' \
    "https://api.github.com/repos/${repository}" >"${temp_dir}/repository.json"
  readarray_values="$({ python3 - "${temp_dir}/repository.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    payload = json.load(stream)
if payload.get("private"):
    raise SystemExit("Este comando de demo aceita somente repositórios públicos.")
print(payload["owner"]["login"])
print(payload["default_branch"])
PY
} )"
  actual_owner="$(printf '%s\n' "${readarray_values}" | sed -n '1p')"
  default_branch="$(printf '%s\n' "${readarray_values}" | sed -n '2p')"
  branch="${branch:-${default_branch}}"
else
  printf '1/7 Preparando acesso privado de escopo único para %s...\n' "${repository}"
  actual_owner="${owner}"
  branch="${branch:-main}"
fi
if [[ ! "${branch}" =~ ^[A-Za-z0-9._/-]{1,255}$ || "${branch}" == *..* ]]; then
  printf 'Branch inválida.\n' >&2
  exit 2
fi

printf '2/7 Preparando configuração local e descartável...\n'
mkdir -p .aieo-demo/projects
cp configs/projects/*.yaml .aieo-demo/projects/
config_file=".aieo-demo/projects/${project_id}.yaml"
printf '%s\n' \
  "id: ${project_id}" \
  "owner: ${actual_owner}" \
  "repository: https://github.com/${repository}" \
  "default_branch: ${branch}" \
  "visibility: ${visibility}" \
  "mode: read-only" \
  "knowledge_namespace: project/${project_id}" \
  "mcp:" \
  "  allowed_tools:" \
  "    - project-catalog:project_summary" >"${config_file}"
if [[ "${private_repository}" == true ]]; then
  printf 'authenticated_read_only: true\n' >>"${config_file}"
fi

printf '3/7 Subindo PostgreSQL e Orquestrador a partir de %s...\n' "${root}"
port_owner="$(docker ps --filter publish=8000 --format '{{.Label "com.docker.compose.project"}}' | head -1)"
if [[ "${port_owner}" == "ai-engineering-orchestrator" ]]; then
  printf 'Encerrando a stack de desenvolvimento anterior para liberar a porta 8000...\n'
  docker compose --project-directory "${root}" -f "${root}/compose.yaml" down
elif [[ -n "${port_owner}" && "${port_owner}" != "aieo-demo" ]]; then
  printf 'A porta 8000 está ocupada pelo projeto Docker %s. Encerre-o antes da demo.\n' \
    "${port_owner}" >&2
  exit 1
fi
"${compose[@]}" up --build -d

printf '4/7 Aguardando prontidão...\n'
for attempt in $(seq 1 60); do
  if curl --fail --silent "${base_url}/ready" >/dev/null; then break; fi
  if [[ "${attempt}" == "60" ]]; then
    "${compose[@]}" logs --tail=200 api postgres >&2
    printf 'A stack não ficou pronta.\n' >&2
    exit 1
  fi
  sleep 2
done

printf '5/7 Confirmando versão e interface...\n'
curl --fail --silent "${base_url}/openapi.json" >"${temp_dir}/openapi.json"
python3 - "${temp_dir}/openapi.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    version = json.load(stream)["info"]["version"]
if version != "0.2.0":
    raise SystemExit(f"Versão inesperada da API: {version}; esperado 0.2.0")
PY
curl --fail --silent "${base_url}/ui/" | grep -q '<div id="root"></div>'

printf '6/7 Executando análise técnica...\n'
python3 - "${project_id}" "${prompt}" "${include_content}" >"${temp_dir}/request.json" <<'PY'
import json
import sys

print(json.dumps({
    "project_id": sys.argv[1],
    "prompt": sys.argv[2],
    "demo": True,
    "include_content": sys.argv[3] == "true",
    "preferred_agents": [],
}))
PY
curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  --data-binary "@${temp_dir}/request.json" \
  "${base_url}/v1/evidence/executions" >"${temp_dir}/execution.json"

printf '7/7 Validando resultado e proveniência...\n'
summary="$(python3 - "${temp_dir}/execution.json" "${project_id}" "${visibility}" "${real_llm}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    execution = json.load(stream)
if execution.get("status") != "COMPLETED":
    raise SystemExit(f"Execução não concluída: {execution.get('status')}")
if execution.get("request", {}).get("project_id") != sys.argv[2]:
    raise SystemExit("Projeto divergente na resposta")
evidence = execution.get("request", {}).get("context", {}).get("evidence", {})
revision = evidence.get("revision", "")
if len(revision) != 40 or not evidence.get("read_only"):
    raise SystemExit("Proveniência Git ou modo somente leitura inválido")
expected_visibility = sys.argv[3]
metadata = evidence.get("metadata", {})
if metadata.get("visibility") != expected_visibility:
    raise SystemExit("Visibilidade divergente na evidência")
if expected_visibility == "private" and metadata.get("authenticated") is not True:
    raise SystemExit("A coleta privada não confirmou autenticação")
if expected_visibility == "private" and any(
    item.get("content_status") != "metadata-only" for item in evidence.get("files", [])
):
    raise SystemExit("A demo privada deve coletar somente metadados")
usage = execution.get("llm_usage") or {}
real_llm = sys.argv[4] == "true"
if real_llm and (usage.get("provider") != "openai-agents" or usage.get("estimated") is not False):
    raise SystemExit("A execução não confirmou consumo real do OpenAI Agents SDK")
if not real_llm and usage.get("provider") != "simulated":
    raise SystemExit("A demo segura deveria usar o provedor simulado")
print(execution["id"])
print(revision)
print(len(execution.get("results", [])))
print(len(execution.get("evidence_sources", [])))
print(usage.get("provider", "desconhecido"))
print(usage.get("input_tokens", 0) + usage.get("output_tokens", 0))
PY
)"
execution_id="$(printf '%s\n' "${summary}" | sed -n '1p')"
revision="$(printf '%s\n' "${summary}" | sed -n '2p')"
agents="$(printf '%s\n' "${summary}" | sed -n '3p')"
sources="$(printf '%s\n' "${summary}" | sed -n '4p')"
llm_provider="$(printf '%s\n' "${summary}" | sed -n '5p')"
llm_tokens="$(printf '%s\n' "${summary}" | sed -n '6p')"

if [[ "${private_repository}" == true ]]; then
  printf 'Desmontando a credencial e preservando o relatório...\n'
  public_compose=(
    docker compose --project-directory "${root}"
    -f "${root}/compose.yaml" -f "${root}/compose.demo.yaml"
  )
  if [[ "${real_llm}" == true ]]; then
    public_compose+=(-f "${root}/compose.demo.openai.yaml")
  fi
  "${public_compose[@]}" up -d --no-deps --force-recreate api >/dev/null
  for attempt in $(seq 1 30); do
    if curl --fail --silent "${base_url}/ready" >/dev/null; then break; fi
    if [[ "${attempt}" == "30" ]]; then
      printf 'A API não voltou sem a credencial montada.\n' >&2
      exit 1
    fi
    sleep 1
  done
  if docker inspect aieo-demo-api-1 \
    --format '{{range .Mounts}}{{println .Destination}}{{end}}' \
    | grep -q '/run/secrets/github_private_read_token'; then
    printf 'A credencial privada permaneceu montada após a coleta.\n' >&2
    exit 1
  fi
fi

printf '\n✓ Demonstração pronta.\n'
printf 'Projeto: %s (%s)\n' "${project_id}" "${repository}"
printf 'Visibilidade: %s | Conteúdo textual: %s\n' "${visibility}" "${include_content}"
printf 'Revisão: %s\n' "${revision}"
printf 'Execução: %s\n' "${execution_id}"
printf 'Especialistas: %s | Fontes: %s\n' "${agents}" "${sources}"
printf 'LLM: %s | Tokens contabilizados: %s\n' "${llm_provider}" "${llm_tokens}"
printf 'UI: %s/ui/\n' "${base_url}"
printf 'Relatório: %s/ui/?project=%s&section=report\n' "${base_url}" "${project_id}"
if [[ "${real_llm}" == true ]]; then
  printf 'Encerrar: docker compose -p aieo-demo -f compose.yaml -f compose.demo.yaml -f compose.demo.openai.yaml down\n'
else
  printf 'Encerrar: docker compose -p aieo-demo -f compose.yaml -f compose.demo.yaml down\n'
fi

if [[ "${open_browser}" == true ]]; then
  open "${base_url}/ui/?project=${project_id}&section=report"
fi
