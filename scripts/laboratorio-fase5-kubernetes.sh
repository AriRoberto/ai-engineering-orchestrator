#!/usr/bin/env bash
set -euo pipefail

rendered="$(mktemp)"
cleanup() {
  rm -f "${rendered}"
}
trap cleanup EXIT

echo "1/3 Renderizando a base Kustomize..."
kubectl kustomize k8s/base >"${rendered}"

echo "2/3 Validando recursos e controles de segurança..."
for kind in Namespace ServiceAccount ConfigMap Service Deployment PodDisruptionBudget Job NetworkPolicy; do
  grep -q "kind: ${kind}" "${rendered}"
done
if grep -q '^kind: Secret$' "${rendered}"; then
  echo "Segredos não podem ser renderizados pela base." >&2
  exit 1
fi
grep -q 'replicas: 2' "${rendered}"
grep -q 'automountServiceAccountToken: false' "${rendered}"
grep -q 'runAsNonRoot: true' "${rendered}"
grep -q 'runAsUser: 999' "${rendered}"
grep -q 'runAsGroup: 999' "${rendered}"
grep -q 'fsGroup: 999' "${rendered}"
grep -q 'readOnlyRootFilesystem: true' "${rendered}"
grep -q 'allowPrivilegeEscalation: false' "${rendered}"
grep -q 'pod-security.kubernetes.io/enforce: restricted' "${rendered}"
grep -q 'name: orchestrator-runtime' "${rendered}"
grep -q 'requests:' "${rendered}"
grep -q 'limits:' "${rendered}"

echo "3/3 Confirmando endpoint de prontidão e migrações na imagem..."
grep -q 'path: /ready' "${rendered}"
grep -q 'ai_engineering.infrastructure.migrations' "${rendered}"

echo ""
echo "✓ Laboratório Kubernetes da Fase 5 concluído com sucesso."
