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
grep -q 'image: ghcr.io/ariroberto/ai-engineering-orchestrator@sha256:423c6262623e3940fe4fd3211586a03edd37777d4716c68b2ec1478a2942d19c' "${rendered}"
grep -q 'image: pgvector/pgvector@sha256:' "${rendered}"
grep -q 'image: pgvector/pgvector@sha256:ac08538c6f8b9904c33c8224c5e5706dbe760aca29db1d096972b4052c22a75d' "${rendered}"
if grep -q 'sha256:0000000000000000000000000000000000000000000000000000000000000000' "${rendered}"; then
  echo "O overlay não pode conter digest zerado após a publicação oficial." >&2
  exit 1
fi
grep -q 'name: orchestrator-registry' "${rendered}"
grep -q 'runAsNonRoot: true' "${rendered}"
grep -q 'readOnlyRootFilesystem: true' "${rendered}"
grep -q 'AIEO_API_AUTH_MODE: oidc' "${rendered}"
grep -q 'name: AIEO_API_QUOTA_REDIS_URL' "${rendered}"

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
for port in 53 443 4318 5432 6379 8000; do
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
  --oidc-issuer https://login.aieo.invalid/ \
  --oidc-audience aieo-staging \
  --oidc-jwks-url https://login.aieo.invalid/jwks.json \
  --output "${promoted}"
grep -q 'host: staging.aieo.invalid' "${promoted}"
grep -q 'storageClassName: encrypted-rwo' "${promoted}"
if grep -qE '0000000000000000000000000000000000000000000000000000000000000000|example\.com' "${promoted}"; then
  echo "A renderização parametrizada ainda contém placeholders." >&2
  exit 1
fi

echo ""
echo "✓ Perfil de homologação validado estaticamente."
echo "Substitua hostname e recursos globais da plataforma antes de aplicar no cluster."
