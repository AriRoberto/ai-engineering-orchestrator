#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZERO_DIGEST = "sha256:" + "0" * 64
PINNED_APP_DIGEST = (
    "sha256:423c6262623e3940fe4fd3211586a03edd37777d4716c68b2ec1478a2942d19c"
)
PINNED_POSTGRES_DIGEST = (
    "sha256:ac08538c6f8b9904c33c8224c5e5706dbe760aca29db1d096972b4052c22a75d"
)
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
DNS_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
NAME_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?$")


def fail(message: str) -> None:
    raise SystemExit(f"Falha na preparação da homologação: {message}")


def validate_inputs(args: argparse.Namespace) -> None:
    if not DNS_PATTERN.fullmatch(args.hostname):
        fail("hostname inválido")
    if args.hostname.endswith(".example.com"):
        fail("substitua o hostname de exemplo por um domínio real")
    for label, digest in (
        ("digest da aplicação", args.app_digest),
        ("digest do PostgreSQL", args.postgres_digest),
    ):
        if not DIGEST_PATTERN.fullmatch(digest) or digest == ZERO_DIGEST:
            fail(f"{label} deve ser sha256 real com 64 caracteres hexadecimais")
    for label, value in (
        ("ClusterSecretStore", args.secret_store),
        ("ClusterIssuer", args.cluster_issuer),
    ):
        if not NAME_PATTERN.fullmatch(value):
            fail(f"{label} inválido")
    if args.storage_class and not NAME_PATTERN.fullmatch(args.storage_class):
        fail("StorageClass inválida")


def replace_exact(path: Path, old: str, new: str, expected: int) -> None:
    content = path.read_text(encoding="utf-8")
    if content.count(old) != expected:
        fail(f"template inesperado em {path.relative_to(path.parents[3])}: {old!r}")
    path.write_text(content.replace(old, new), encoding="utf-8")


def prepare_tree(args: argparse.Namespace, destination: Path) -> Path:
    target = destination / "k8s"
    shutil.copytree(ROOT / "k8s", target)
    overlay = target / "overlays/staging"
    kustomization = overlay / "kustomization.yaml"
    content = kustomization.read_text(encoding="utf-8")
    app_block = (
        "  - name: ghcr.io/ariroberto/ai-engineering-orchestrator\n"
        "    newName: ghcr.io/ariroberto/ai-engineering-orchestrator\n"
        f"    digest: {PINNED_APP_DIGEST}"
    )
    postgres_block = (
        "  - name: pgvector/pgvector\n"
        "    newName: pgvector/pgvector\n"
        f"    digest: {PINNED_POSTGRES_DIGEST}"
    )
    if content.count(app_block) != 1 or content.count(postgres_block) != 1:
        fail("blocos de imagem do template não correspondem ao contrato esperado")
    content = content.replace(app_block, app_block.replace(PINNED_APP_DIGEST, args.app_digest))
    content = content.replace(
        postgres_block, postgres_block.replace(PINNED_POSTGRES_DIGEST, args.postgres_digest)
    )
    kustomization.write_text(content, encoding="utf-8")
    replace_exact(
        overlay / "ingress.yaml",
        "orchestrator.staging.example.com",
        args.hostname,
        2,
    )
    replace_exact(
        overlay / "certificate.yaml",
        "orchestrator.staging.example.com",
        args.hostname,
        1,
    )
    replace_exact(
        overlay / "external-secrets.yaml",
        "name: staging-secret-store",
        f"name: {args.secret_store}",
        4,
    )
    replace_exact(
        overlay / "ingress.yaml",
        "cert-manager.io/cluster-issuer: letsencrypt-staging",
        f"cert-manager.io/cluster-issuer: {args.cluster_issuer}",
        1,
    )
    replace_exact(
        overlay / "certificate.yaml",
        "name: letsencrypt-staging",
        f"name: {args.cluster_issuer}",
        1,
    )
    if args.storage_class:
        replace_exact(
            overlay / "postgres.yaml",
            '        accessModes: ["ReadWriteOnce"]',
            '        accessModes: ["ReadWriteOnce"]\n'
            f"        storageClassName: {args.storage_class}",
            1,
        )
    return overlay


def run(command: list[str], *, capture: bool = True) -> str:
    result = subprocess.run(  # noqa: S603 - arguments are validated and no shell is used
        command, check=False, text=True, capture_output=capture
    )
    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        fail(f"comando falhou ({' '.join(command)}): {details}")
    return result.stdout


def kubectl(args: argparse.Namespace, *arguments: str) -> str:
    return run(["kubectl", "--context", args.context, *arguments])


def check_cluster(args: argparse.Namespace) -> None:
    if not args.context:
        fail("--context é obrigatório com --check-cluster")
    if args.context.startswith("kind-") or args.context in {"docker-desktop", "minikube"}:
        fail("o preflight externo não aceita contexto de cluster local")
    kubectl(args, "cluster-info")
    for resource in (
        "customresourcedefinition/externalsecrets.external-secrets.io",
        "customresourcedefinition/clustersecretstores.external-secrets.io",
        "customresourcedefinition/certificates.cert-manager.io",
    ):
        kubectl(args, "get", resource)
    kubectl(args, "get", "clustersecretstore", args.secret_store)
    kubectl(args, "get", "clusterissuer", args.cluster_issuer)
    kubectl(args, "get", "ingressclass", "nginx")
    if args.storage_class:
        kubectl(args, "get", "storageclass", args.storage_class)
    else:
        payload = json.loads(kubectl(args, "get", "storageclass", "-o", "json"))
        annotations = (
            "storageclass.kubernetes.io/is-default-class",
            "storageclass.beta.kubernetes.io/is-default-class",
        )
        if not any(
            any(
                item.get("metadata", {}).get("annotations", {}).get(key) == "true"
                for key in annotations
            )
            for item in payload.get("items", [])
        ):
            fail("o cluster não possui StorageClass padrão; use --storage-class")
    try:
        socket.getaddrinfo(args.hostname, 443)
    except socket.gaierror as exc:
        fail(f"DNS ainda não resolve {args.hostname}: {exc}")
    for image in (
        f"ghcr.io/ariroberto/ai-engineering-orchestrator@{args.app_digest}",
        f"pgvector/pgvector@{args.postgres_digest}",
    ):
        run(["docker", "buildx", "imagetools", "inspect", image])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Renderiza o perfil imutável de homologação.")
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--app-digest", default=PINNED_APP_DIGEST)
    parser.add_argument("--postgres-digest", default=PINNED_POSTGRES_DIGEST)
    parser.add_argument("--secret-store", required=True)
    parser.add_argument("--cluster-issuer", required=True)
    parser.add_argument("--storage-class")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context")
    parser.add_argument("--check-cluster", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_inputs(args)
    if not shutil.which("kubectl"):
        fail("kubectl não encontrado")
    if args.check_cluster:
        check_cluster(args)
    with tempfile.TemporaryDirectory(prefix="aieo-staging-") as temp_dir:
        overlay = prepare_tree(args, Path(temp_dir))
        rendered = run(["kubectl", "kustomize", str(overlay)])
    if ZERO_DIGEST in rendered or "orchestrator.staging.example.com" in rendered:
        fail("a renderização ainda contém placeholders")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"✓ Manifest de homologação renderizado em {args.output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, json.JSONDecodeError) as exc:
        fail(str(exc))
