#!/usr/bin/env bash
set -euo pipefail

scope="${1:---local}"
started_at="$(date +%s)"
completed=0
python_bin="${AIEO_PYTHON_BIN:-}"

usage() {
  cat <<'EOF'
Uso: ./scripts/gate-regressao.sh [--static|--local|--full]

  --static  valida manifests Kubernetes e artefatos da release
  --local   executa os laboratórios locais sem credenciais privadas (padrão)
  --full    adiciona piloto privado e validação em cluster kind
EOF
}

cleanup() {
  docker compose -f compose.yaml -f compose.observability.yaml down >/dev/null 2>&1 || true
  docker compose -f compose.yaml -f compose.access.yaml down >/dev/null 2>&1 || true
  docker compose down >/dev/null 2>&1 || true
}

run_step() {
  local label="$1"
  shift
  completed=$((completed + 1))
  printf '\n==> [%s] %s\n' "${completed}" "${label}"
  "$@"
}

case "${scope}" in
  --static | --local | --full) ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

required_commands=(kubectl)
if [[ "${scope}" != "--static" ]]; then
  required_commands+=(docker curl)
fi
for command in "${required_commands[@]}"; do
  command -v "${command}" >/dev/null || {
    printf 'Comando obrigatório ausente: %s\n' "${command}" >&2
    exit 1
  }
done

if [[ -z "${python_bin}" ]]; then
  for candidate in .venv/bin/python python3.12 python python3; do
    if command -v "${candidate}" >/dev/null \
      && "${candidate}" -c 'import sys; raise SystemExit(sys.version_info < (3, 12))'; then
      python_bin="${candidate}"
      break
    fi
  done
fi
if [[ -z "${python_bin}" ]] || ! command -v "${python_bin}" >/dev/null \
  || ! "${python_bin}" -c 'import sys; raise SystemExit(sys.version_info < (3, 12))'; then
  printf 'Python 3.12+ é obrigatório. Defina AIEO_PYTHON_BIN se necessário.\n' >&2
  exit 1
fi

if [[ "${scope}" == "--full" ]]; then
  if [[ -z "${AIEO_GITHUB_PRIVATE_READ_TOKEN_FILE:-}" ]]; then
    printf 'AIEO_GITHUB_PRIVATE_READ_TOKEN_FILE é obrigatório no escopo --full.\n' >&2
    exit 1
  fi
  for command in kind openssl shasum; do
    command -v "${command}" >/dev/null || {
      printf 'Comando obrigatório ausente no escopo --full: %s\n' "${command}" >&2
      exit 1
    }
  done
fi

if [[ "${scope}" != "--static" ]]; then
  trap cleanup EXIT
  run_step "Fundação de conhecimento e MCP" ./scripts/laboratorio-fase2.sh
  run_step "Especialistas da Fase 3" ./scripts/laboratorio-fase3.sh
  run_step "Evidências públicas da Fase 4" ./scripts/laboratorio-fase4.sh
  run_step "Observabilidade da Fase 5" ./scripts/laboratorio-fase5-observabilidade.sh
  run_step "Acesso governado da Fase 5" ./scripts/laboratorio-fase5-acesso.sh
fi

run_step "Manifests Kubernetes" ./scripts/laboratorio-fase5-kubernetes.sh
run_step "Perfil Kubernetes de homologação" ./scripts/laboratorio-homologacao.sh
run_step "Artefatos da release" "${python_bin}" scripts/validar-release.py

if [[ "${scope}" == "--full" ]]; then
  run_step "Piloto privado da Fase 4" ./scripts/laboratorio-fase4-privado.sh
  run_step "Cluster Kubernetes local" ./scripts/laboratorio-kubernetes-local.sh
fi

elapsed=$(( $(date +%s) - started_at ))
printf '\n✓ Gate de regressão %s concluído: %s etapas em %ss.\n' \
  "${scope#--}" "${completed}" "${elapsed}"
