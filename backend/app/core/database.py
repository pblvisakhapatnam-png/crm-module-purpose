from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


# PostgreSQL is the only supported runtime (ADR-028). `postgresql+psycopg` is the canonical
# SQLAlchemy dialect. A hosted or legacy provider URL may use the bare `postgresql://` scheme or
# the deprecated `postgres://` alias; both are normalized to Psycopg 3. Any other dialect is
# rejected rather than silently accepted, so a stale SQL Server URL fails loudly at startup.
CANONICAL_DRIVERNAME = "postgresql+psycopg"
_NORMALIZABLE_DRIVERNAMES = frozenset({"postgresql", "postgres", "postgresql+psycopg"})

# Force session time zone to UTC. Business timestamps are stored and transmitted in UTC; the UI
# converts them to Asia/Kolkata for display.
CONNECT_ARGS: dict[str, str] = {"options": "-c timezone=UTC"}


def normalize_database_url(raw_url: str) -> URL:
    """Parse a configured database URL and return it on the canonical Psycopg 3 dialect."""
    url = make_url(raw_url)

    if url.drivername not in _NORMALIZABLE_DRIVERNAMES:
        raise ValueError(
            f"Unsupported database URL dialect '{url.drivername}'. "
            f"This application supports PostgreSQL only; use '{CANONICAL_DRIVERNAME}://'."
        )

    return url.set(drivername=CANONICAL_DRIVERNAME)


def build_sqlalchemy_url() -> URL:
    settings = get_settings()

    if settings.database_url:
        return normalize_database_url(settings.database_url)

    return URL.create(
        CANONICAL_DRIVERNAME,
        username=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )


# `hide_parameters` keeps a failed statement's bound values out of the error's text, so they never
# reach a log or a traceback (TB-1 TB1-503). It does not touch PostgreSQL's own DETAIL line, which
# can repeat a duplicated key or a whole failing row; app/core/errors.py logs a database error that
# escapes a request without the error's text for that reason.
engine: Engine = create_engine(
    build_sqlalchemy_url(),
    pool_pre_ping=True,
    connect_args=CONNECT_ARGS,
    future=True,
    hide_parameters=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_database_settings_summary() -> dict[str, str | int | None]:
    """Non-sensitive connection identity. The password is never included."""
    url = build_sqlalchemy_url()
    return {
        "dialect": url.drivername,
        "host": url.host,
        "port": url.port,
        "database": url.database,
        "user": url.username,
    }


def verify_database_connection() -> dict[str, object]:
    with engine.connect() as connection:
        select_one = connection.execute(text("SELECT 1")).scalar_one()
        database_name = connection.execute(text("SELECT current_database()")).scalar_one()

    return {
        "status": "ok",
        "select_1": select_one,
        "database": database_name,
    }


def get_foundation_table_status() -> dict[str, bool]:
    expected_tables = [
        "app_user",
        "role",
        "user_role",
        "workflow_status",
        "business_event",
        "document_metadata",
        "alembic_version",
    ]

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_type = 'BASE TABLE'
                  AND table_schema = current_schema()
                """
            )
        ).scalars().all()

    present = set(rows)
    return {table: table in present for table in expected_tables}
