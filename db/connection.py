from __future__ import annotations

import psycopg2
from psycopg2.extras import RealDictCursor

DB_DSN = "postgresql://backend_user:backend_pass@127.0.0.1:5433/backend_hw"


def get_connection(dsn: str | None = None) -> psycopg2.extensions.connection:
    return psycopg2.connect(dsn or DB_DSN, cursor_factory=RealDictCursor)
