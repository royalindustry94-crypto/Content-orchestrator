"""Database engines and session dependencies.

Two separate connections, deliberately:

- `engine` / `AsyncSessionLocal` / `get_db` — the owner/migration
  connection (`DATABASE_URL`). Alembic uses this, and so does the health
  check (checking "is Postgres reachable" shouldn't depend on the
  app_runtime role also being correctly provisioned).
- `runtime_engine` — the `app_runtime` role connection
  (`APP_DATABASE_URL`). This is what every authenticated request handler
  actually uses, via `rls_scoped_session` in `app.core.security`. It's a
  non-owner role with no BYPASSRLS, so Row Level Security policies apply.

`get_db` deliberately takes no parameters — it's a FastAPI dependency,
and any parameter on it would be parsed as a query/body param on every
route that depends on it. The RLS-scoped runtime session is a separate
async context manager (`rls_scoped_session`), not a bare `Depends`
target, because it needs the verified user id from the JWT, which only
exists after `get_current_user` has already run.

See docs/milestone-2-identity-and-access.md §6 for how `app_runtime` is
provisioned in Docker/CI to mirror what's needed against real Supabase.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# Tests set ENVIRONMENT=test so each async session gets a fresh TCP connection
# (no connection pool). This prevents "Event loop is closed" errors that arise
# when pytest-asyncio creates a new event loop per test while SQLAlchemy's
# pool retains connections bound to the previous loop.
_is_test = os.getenv("ENVIRONMENT") == "test"


def pool_kwargs_for(*, is_test: bool, is_serverless: bool) -> dict:
    """Engine pooling arguments for this runtime.

    On a serverless runtime an in-process pool is worse than no pool: the
    instance is frozen immediately after the response, so a checked-out
    connection is never handed back and the server-side backend lingers until
    it times out. NullPool opens and closes per checkout instead.
    """
    if is_test or is_serverless:
        return {"poolclass": NullPool}
    return {"pool_pre_ping": True}


def connect_args_for(*, is_serverless: bool) -> dict:
    """DBAPI arguments for this runtime.

    A serverless deployment reaches Postgres through a transaction-mode
    connection pooler (Supabase's Supavisor, PgBouncer). Consecutive statements
    can land on different backends, which breaks asyncpg's prepared statements
    two ways: a cached statement handle is not valid on another backend, and
    asyncpg's default numeric statement names collide between clients sharing
    one. Disabling the cache and generating unique names is the documented fix —
    see "Prepared Statement Name with PGBouncer" in SQLAlchemy's asyncpg dialect
    docs. Both are DBAPI-level arguments, hence connect_args rather than
    engine kwargs.
    """
    if not is_serverless:
        return {}
    return {
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    }


_pool_kwargs = pool_kwargs_for(is_test=_is_test, is_serverless=settings.is_serverless)
_connect_args = connect_args_for(is_serverless=settings.is_serverless)


def _asyncpg_url(dsn: str) -> str:
    return dsn.replace("postgresql://", "postgresql+asyncpg://", 1)


# Owner/migration connection.
engine = create_async_engine(
    _asyncpg_url(str(settings.database_url)),
    echo=False,
    connect_args=_connect_args,
    **_pool_kwargs,
)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

# Runtime (RLS-enforced) connection.
runtime_engine = create_async_engine(
    _asyncpg_url(str(settings.app_database_url)),
    echo=False,
    connect_args=_connect_args,
    **_pool_kwargs,
)
RuntimeSessionLocal = async_sessionmaker(
    bind=runtime_engine, expire_on_commit=False, autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Owner-role session. Used by the health check. Not for
    request-scoped application data access — use `rls_scoped_session` via
    `app.core.security.get_current_session` for that.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def rls_scoped_session(user_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Runtime session with `request.jwt.claim.sub` set for this
    transaction only, so `app_current_user_id()` in RLS policies resolves
    to `user_id`. Uses `set_config(..., true)` (transaction-local, the
    `SET LOCAL` equivalent for a parameterized call) so the setting can
    never leak to a pooled connection's next borrower.
    """
    async with RuntimeSessionLocal() as session:
        try:
            await session.execute(
                text("SELECT set_config('request.jwt.claim.sub', :sub, true)"),
                {"sub": user_id},
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
