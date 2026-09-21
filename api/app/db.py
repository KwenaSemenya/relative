"""Database engine and session handling.

The database is Neon, reached over the public internet with TLS, so the URL
needs two adjustments that a Fly-local Postgres would not have needed:
asyncpg does not understand libpq's `sslmode` query parameter, and Neon's
pooled endpoint runs pgbouncer in transaction mode, which cannot hold prepared
statements between queries.
"""

from collections.abc import AsyncIterator
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


def normalise_url(url: str) -> tuple[str, dict]:
    """Return an asyncpg-compatible URL and the connect_args it needs."""
    parts = urlsplit(url)

    scheme = "postgresql+asyncpg"
    query = parts.query.lower()
    # asyncpg takes ssl as a connect arg, not a URL parameter.
    wants_tls = "sslmode=require" in query or "sslmode=verify" in query
    clean = urlunsplit((scheme, parts.netloc, parts.path, "", ""))

    connect_args: dict = {}
    if wants_tls or ".neon.tech" in parts.netloc:
        connect_args["ssl"] = True
    if "-pooler." in parts.netloc or "pgbouncer" in parts.netloc:
        # pgbouncer in transaction mode hands each query a different backend,
        # so a cached prepared statement will not be there next time.
        connect_args["statement_cache_size"] = 0

    return clean, connect_args


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        url, connect_args = normalise_url(get_settings().database_url)
        _engine = create_async_engine(
            url,
            connect_args=connect_args,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def session() -> AsyncIterator[AsyncSession]:
    engine()
    assert _sessionmaker is not None
    async with _sessionmaker() as s:
        yield s
