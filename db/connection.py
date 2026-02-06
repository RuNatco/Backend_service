from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_DSN = os.getenv(
    "DB_DSN",
    "postgresql://backend_user:backend_pass@localhost:5432/backend_hw",
)


def get_connection(dsn: str | None = None) -> psycopg2.extensions.connection:
    return psycopg2.connect(dsn or DB_DSN, cursor_factory=RealDictCursor)
