#!/usr/bin/env bash
set -euo pipefail

falhas=0

verificar() {
  local nome="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf '✓ %s\n' "$nome"
  else
    printf '✗ %s\n' "$nome"
    falhas=$((falhas + 1))
  fi
}

printf 'Verificando ambiente do AI Engineering Orchestrator...\n'
verificar "Docker" docker --version
verificar "Docker Compose" docker compose version
verificar "curl" curl --version
verificar "Python 3" python3 --version

if ! docker info >/dev/null 2>&1; then
  printf '✗ O Docker Desktop não está em execução.\n'
  falhas=$((falhas + 1))
else
  printf '✓ Docker Desktop está em execução\n'
fi

if ((falhas > 0)); then
  printf '\nAmbiente incompleto: %d verificação(ões) falharam.\n' "$falhas"
  exit 1
fi

printf '\nAmbiente pronto para o laboratório da Fase 2.\n'
