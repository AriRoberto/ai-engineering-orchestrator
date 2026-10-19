import os
from pathlib import Path

import structlog
from sqlalchemy import create_engine

logger = structlog.get_logger()


def apply_migrations(database_url: str, directory: Path) -> list[str]:
    migration_files = sorted(directory.glob("*.sql"))
    if not migration_files:
        raise RuntimeError(f"Nenhuma migração SQL encontrada em {directory}")

    engine = create_engine(database_url, pool_pre_ping=True)
    applied = []
    try:
        for migration_file in migration_files:
            statement = migration_file.read_text(encoding="utf-8")
            with engine.begin() as connection:
                connection.exec_driver_sql(statement)
            applied.append(migration_file.name)
            logger.info("database_migration_applied", migration=migration_file.name)
    finally:
        engine.dispose()
    return applied


def main() -> None:
    database_url = os.environ.get("AIEO_DATABASE_URL")
    if not database_url:
        raise RuntimeError("AIEO_DATABASE_URL é obrigatória para executar migrações")
    migration_dir = Path(os.environ.get("AIEO_MIGRATIONS_DIR", "/app/migrations"))
    apply_migrations(database_url, migration_dir)


if __name__ == "__main__":
    main()
