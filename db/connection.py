from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg

DB_DSN = os.getenv(
    "DB_DSN",
    "postgresql://backend_user:backend_pass@127.0.0.1:5433/backend_hw",
)
DB_POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
DB_POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "10"))

_pool: Optional[asyncpg.Pool] = None
_pool_dsn: Optional[str] = None
_pool_loop: Optional[asyncio.AbstractEventLoop] = None


async def init_pg_pool(dsn: str | None = None) -> asyncpg.Pool:
    global _pool
    global _pool_dsn
    global _pool_loop

    target_dsn = dsn or DB_DSN
    current_loop = asyncio.get_running_loop()

    if (
        _pool is not None
        and _pool_dsn == target_dsn
        and _pool_loop is current_loop
    ):
        return _pool

    if _pool is not None:
        
        if _pool_loop is current_loop:
            try:
                await _pool.close()
            except Exception:
                pass

    _pool = await asyncpg.create_pool(
        dsn=target_dsn,
        min_size=DB_POOL_MIN_SIZE,
        max_size=DB_POOL_MAX_SIZE,
    )
    _pool_dsn = target_dsn
    _pool_loop = current_loop
    return _pool


async def close_pg_pool() -> None:
    global _pool
    global _pool_dsn
    global _pool_loop

    if _pool is not None:
        current_loop = asyncio.get_running_loop()
        if _pool_loop is current_loop:
            await _pool.close()
    _pool = None
    _pool_dsn = None
    _pool_loop = None


@asynccontextmanager
async def get_connection(
    dsn: str | None = None,
) -> AsyncGenerator[asyncpg.Connection, None]:
    pool = await init_pg_pool(dsn)
    async with pool.acquire() as connection:
        yield connection


@asynccontextmanager
async def get_transaction(
    dsn: str | None = None,
) -> AsyncGenerator[asyncpg.Connection, None]:
    async with get_connection(dsn) as connection:
        async with connection.transaction():
            yield connection
