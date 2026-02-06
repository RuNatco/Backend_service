from __future__ import annotations
from pathlib import Path
from db.connection import get_connection


def apply_migrations(db_path: Path, migrations_dir: Path) -> None:
    migrations = sorted(migrations_dir.glob("V*.sql"))
    if not migrations:
        return

    with get_connection(db_path) as conn:
        for migration in migrations:
            sql = migration.read_text()
            if sql.strip():
                conn.executescript(sql)
