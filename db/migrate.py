from __future__ import annotations

from pathlib import Path
from db.connection import get_connection


async def apply_migrations(base_dir: Path, dsn: str | None = None) -> None:
    migrations_dir = base_dir / "migrations" if (base_dir / "migrations").is_dir() else base_dir
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        raise RuntimeError(f"No SQL migrations found in {migrations_dir}")

    async with get_connection(dsn) as conn:
        async with conn.transaction():
            for migration_file in migration_files:
                sql = migration_file.read_text(encoding="utf-8").strip()
                if sql:
                    await conn.execute(sql)
