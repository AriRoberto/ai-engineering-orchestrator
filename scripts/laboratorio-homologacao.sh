#!/usr/bin/env bash
set -euo pipefail

rendered="$(mktemp)"
promoted="$(mktemp)"
cleanup() {
  rm -f "${rendered}" "${promoted}"
}
trap cleanup EXIT

echo "1/6 Renderizando o overlay de homologação..."
kubectl kustomize k8s/overlays/staging >"${rendered}"

echo "2/6 Validando registry imutável e controles de workload..."
test "$(grep -c 'image: ghcr.io/ariroberto/ai-engineering-orchestrator@sha256:' "${rendered}")" = "2"
grep -q 'image: pgvector/pgvector@sha256:' "${rendered}"
grep -q 'image: pgvector/pgvector@sha256:ac08538c6f8b9904c33c8224c5e5706dbe760aca29db1d096972b4052c22a75d' "${rendered}"
grep -q 'sha256:0000000000000000000000000000000000000000000000000000000000000000' "${rendered}"
grep -q 'name: orchestrator-registry' "${rendered}"
grep -q 'runAsNonRoot: true' "${rendered}"
grep -q 'readOnlyRootFilesystem: true' "${rendered}"

echo "3/6 Validando persistência do PostgreSQL..."
grep -q '^kind: StatefulSet$' "${rendered}"
grep -q 'storage: 20Gi' "${rendered}"
grep -q 'accessModes:' "${rendered}"
if grep -A4 'name: data' "${rendered}" | grep -q 'emptyDir'; then
  echo "O volume de dados da homologação não pode usar emptyDir." >&2
  exit 1
fi

echo "4/6 Validando Ingress, TLS e secret manager..."
grep -q '^kind: Ingress$' "${rendered}"
grep -q '^kind: Certificate$' "${rendered}"
grep -q 'secretName: orchestrator-staging-tls' "${rendered}"
test "$(grep -c '^kind: ExternalSecret$' "${rendered}")" = "4"
grep -q 'name: staging-secret-store' "${rendered}"
if grep -q '^kind: Secret$' "${rendered}"; then
  echo "Segredos Kubernetes não podem ser versionados no overlay." >&2
  exit 1
fi

echo "5/6 Validando políticas de rede e falha segura dos placeholders..."
for port in 53 443 4318 5432 8000; do
  grep -q "port: ${port}" "${rendered}"
done
grep -q 'orchestrator.staging.example.com' "${rendered}"

echo "6/6 Validando renderização parametrizada sem alterar o template..."
python_bin="${AIEO_PYTHON_BIN:-python3}"
"${python_bin}" scripts/renderizar-homologacao.py \
  --hostname staging.aieo.invalid \
  --app-digest "sha256:$(printf '1%.0s' $(seq 1 64))" \
  --secret-store aieo-staging \
  --cluster-issuer aieo-staging \
  --storage-class encrypted-rwo \
  --output "${promoted}"
grep -q 'host: staging.aieo.invalid' "${promoted}"
grep -q 'storageClassName: encrypted-rwo' "${promoted}"
if grep -qE '0000000000000000000000000000000000000000000000000000000000000000|example\.com' "${promoted}"; then
  echo "A renderização parametrizada ainda contém placeholders." >&2
  exit 1
fi

echo ""
echo "✓ Perfil de homologação validado estaticamente."
echo "Substitua hostname, ClusterSecretStore e os digests antes de aplicar no cluster."
