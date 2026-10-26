#!/usr/bin/env python3
import json
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.2.0"


def fail(message: str) -> None:
    raise SystemExit(f"Falha no gate de release: {message}")


def validate_versions() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    web = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "web/package-lock.json").read_text(encoding="utf-8"))
    versions = {
        project["project"]["version"],
        web["version"],
        lock["version"],
        lock["packages"][""]["version"],
    }
    if versions != {EXPECTED_VERSION}:
        fail(f"versões divergentes: {sorted(versions)}")

    api = (ROOT / "apps/api/main.py").read_text(encoding="utf-8")
    if f'version="{EXPECTED_VERSION}"' not in api:
        fail("versão da API divergente")
    for manifest in ("deployment.yaml", "migration-job.yaml"):
        content = (ROOT / "k8s/base" / manifest).read_text(encoding="utf-8")
        if f":{EXPECTED_VERSION}" not in content:
            fail(f"imagem sem versão esperada em {manifest}")


def validate_structured_files() -> None:
    json.loads(
        (ROOT / "observability/grafana/dashboards/aieo-overview.json").read_text(
            encoding="utf-8"
        )
    )
    for directory in (ROOT / "k8s", ROOT / "observability/rules"):
        for path in directory.rglob("*.y*ml"):
            list(yaml.safe_load_all(path.read_text(encoding="utf-8")))


def validate_markdown_links() -> None:
    pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")
    missing: list[str] = []
    for document in [ROOT / "README.md", ROOT / "SECURITY.md", *(ROOT / "docs").rglob("*.md")]:
        for target in pattern.findall(document.read_text(encoding="utf-8")):
            clean_target = target.split("#", 1)[0]
            external = "://" in clean_target or clean_target.startswith(("mailto:", "/"))
            if not clean_target or external:
                continue
            if not (document.parent / clean_target).resolve().exists():
                missing.append(f"{document.relative_to(ROOT)} -> {target}")
    if missing:
        fail("links locais ausentes:\n" + "\n".join(missing))


def main() -> None:
    required = (
        "docs/pt-BR/documentacao-oficial.md",
        "docs/pt-BR/release-0.2.0.md",
        "docs/pt-BR/slo.md",
        "docs/pt-BR/runbooks/README.md",
    )
    for relative_path in required:
        if not (ROOT / relative_path).is_file():
            fail(f"documento obrigatório ausente: {relative_path}")
    validate_versions()
    validate_structured_files()
    validate_markdown_links()
    print(f"✓ Gate documental e estrutural da versão {EXPECTED_VERSION} aprovado.")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, json.JSONDecodeError, tomllib.TOMLDecodeError, yaml.YAMLError) as exc:
        fail(str(exc))
