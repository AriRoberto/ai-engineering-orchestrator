from pathlib import Path

import pytest

from ai_engineering.infrastructure import migrations


class FakeConnection:
    def __init__(self, statements: list[str]) -> None:
        self.statements = statements

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def exec_driver_sql(self, statement: str) -> None:
        self.statements.append(statement)


class FakeEngine:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.disposed = False

    def begin(self) -> FakeConnection:
        return FakeConnection(self.statements)

    def dispose(self) -> None:
        self.disposed = True


def test_apply_migrations_runs_sql_files_in_order(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "002_second.sql").write_text("SELECT 2", encoding="utf-8")
    (tmp_path / "001_first.sql").write_text("SELECT 1", encoding="utf-8")
    engine = FakeEngine()
    monkeypatch.setattr(migrations, "create_engine", lambda *_args, **_kwargs: engine)

    applied = migrations.apply_migrations("postgresql://unused", tmp_path)

    assert applied == ["001_first.sql", "002_second.sql"]
    assert engine.statements == ["SELECT 1", "SELECT 2"]
    assert engine.disposed is True


def test_apply_migrations_requires_sql_files(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Nenhuma migração"):
        migrations.apply_migrations("postgresql://unused", tmp_path)
