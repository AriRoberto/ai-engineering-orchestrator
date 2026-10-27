import pytest
import yaml

from ai_engineering.evidence.catalog import ProjectCatalog, PublicProjectCreate


def public_metadata() -> dict[str, object]:
    return {
        "private": False,
        "name": "sample_app",
        "default_branch": "main",
        "owner": {"login": "ExampleOrg"},
    }


def test_registers_public_project_as_persistent_read_only_config(tmp_path, monkeypatch) -> None:
    catalog = ProjectCatalog(str(tmp_path))
    monkeypatch.setattr(catalog, "_fetch_public_metadata", lambda owner, repo: public_metadata())

    project = catalog.register_public(PublicProjectCreate(repository="ExampleOrg/sample_app"))

    assert project.id == "sample-app"
    assert project.mode == "read-only"
    config = yaml.safe_load((tmp_path / "sample-app.yaml").read_text(encoding="utf-8"))
    assert config["visibility"] == "public"
    assert config["knowledge_namespace"] == "project/sample-app"
    assert catalog.list() == [project]


def test_rejects_private_duplicate_and_invalid_catalog_entries(tmp_path, monkeypatch) -> None:
    catalog = ProjectCatalog(str(tmp_path))
    private = public_metadata() | {"private": True}
    monkeypatch.setattr(catalog, "_fetch_public_metadata", lambda owner, repo: private)
    with pytest.raises(ValueError, match="Somente repositórios públicos"):
        catalog.register_public(PublicProjectCreate(repository="ExampleOrg/sample_app"))

    monkeypatch.setattr(catalog, "_fetch_public_metadata", lambda owner, repo: public_metadata())
    catalog.register_public(PublicProjectCreate(repository="ExampleOrg/sample_app"))
    with pytest.raises(FileExistsError, match="Já existe"):
        catalog.register_public(PublicProjectCreate(repository="ExampleOrg/sample_app"))

    (tmp_path / "invalid.yaml").write_text("unexpected: true\n", encoding="utf-8")
    assert [item.id for item in catalog.list()] == ["sample-app"]


def test_reports_unwritable_catalog_without_leaking_details(tmp_path, monkeypatch) -> None:
    catalog_path = tmp_path / "projects"
    catalog_path.write_text("not a directory", encoding="utf-8")
    catalog = ProjectCatalog(str(catalog_path))
    monkeypatch.setattr(catalog, "_fetch_public_metadata", lambda owner, repo: public_metadata())

    with pytest.raises((FileExistsError, RuntimeError, OSError)):
        catalog.register_public(PublicProjectCreate(repository="ExampleOrg/sample_app"))
