from __future__ import annotations
from pathlib import Path
import os
import sqlite3

DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).resolve().parent / "app.db"))


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
