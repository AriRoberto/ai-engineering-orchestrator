#!/usr/bin/env bash
set -euo pipefail

rendered="$(mktemp)"
cleanup() {
  rm -f "${rendered}"
}
trap cleanup EXIT

echo "1/5 Renderizando o overlay de homologação..."
kubectl kustomize k8s/overlays/staging >"${rendered}"

echo "2/5 Validando registry imutável e controles de workload..."
test "$(grep -c 'image: ghcr.io/ariroberto/ai-engineering-orchestrator@sha256:' "${rendered}")" = "2"
grep -q 'image: pgvector/pgvector@sha256:' "${rendered}"
grep -q 'sha256:0000000000000000000000000000000000000000000000000000000000000000' "${rendered}"
grep -q 'name: orchestrator-registry' "${rendered}"
grep -q 'runAsNonRoot: true' "${rendered}"
grep -q 'readOnlyRootFilesystem: true' "${rendered}"

echo "3/5 Validando persistência do PostgreSQL..."
grep -q '^kind: StatefulSet$' "${rendered}"
grep -q 'storage: 20Gi' "${rendered}"
grep -q 'accessModes:' "${rendered}"
if grep -A4 'name: data' "${rendered}" | grep -q 'emptyDir'; then
  echo "O volume de dados da homologação não pode usar emptyDir." >&2
  exit 1
fi

echo "4/5 Validando Ingress, TLS e secret manager..."
grep -q '^kind: Ingress$' "${rendered}"
grep -q '^kind: Certificate$' "${rendered}"
grep -q 'secretName: orchestrator-staging-tls' "${rendered}"
test "$(grep -c '^kind: ExternalSecret$' "${rendered}")" = "4"
grep -q 'name: staging-secret-store' "${rendered}"
if grep -q '^kind: Secret$' "${rendered}"; then
  echo "Segredos Kubernetes não podem ser versionados no overlay." >&2
  exit 1
fi

echo "5/5 Validando políticas de rede e falha segura dos placeholders..."
for port in 53 443 4318 5432 8000; do
  grep -q "port: ${port}" "${rendered}"
done
grep -q 'orchestrator.staging.example.com' "${rendered}"

echo ""
echo "✓ Perfil de homologação validado estaticamente."
echo "Substitua hostname, ClusterSecretStore e os digests antes de aplicar no cluster."
