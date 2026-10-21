#!/usr/bin/env bash
set -euo pipefail

cluster_name="${AIEO_LOCAL_CLUSTER_NAME:-aieo-local}"
local_api_key_file="${AIEO_LOCAL_API_KEY_FILE:-${HOME}/.config/aieo/local-api-key}"

if kind get clusters | grep -Fxq "${cluster_name}"; then
  kind delete cluster --name "${cluster_name}"
fi
rm -f "${local_api_key_file}"

echo "✓ Cluster ${cluster_name} e API key local removidos."
