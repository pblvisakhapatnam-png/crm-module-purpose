from __future__ import annotations

import subprocess
import sys
import time

import uvicorn
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings, get_settings
from app.core.database import engine

# The account tool's command that gives development and CI their six demo users (TB-1 TB1-203).
SEED_DEMO_USERS_COMMAND = (sys.executable, "-m", "tooling.user_admin", "seed-demo-users")


def wait_for_database(max_attempts: int = 60, delay_seconds: float = 2) -> None:
    """Wait until the PostgreSQL server accepts a connection.

    The database itself is provisioned by the PostgreSQL container (POSTGRES_DB) or by the
    managed provider, so the application never creates it. Only reaching it is retried.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except SQLAlchemyError as exc:
            if attempt == max_attempts:
                raise
            print(f"Database not ready yet (attempt {attempt}/{max_attempts}): {exc}", flush=True)
            time.sleep(delay_seconds)


def apply_migrations() -> None:
    """Bring the schema to Alembic head, once.

    A failure is not retried (TB-1 TB1-405 item 1): the database has already answered, so the
    migration itself failed, and running it again would fail the same way. Alembic writes its own
    error to the log above this one; every migration runs in one transaction, so a failed upgrade
    has changed nothing.
    """
    result = subprocess.run(["alembic", "upgrade", "head"], check=False)
    if result.returncode != 0:
        raise SystemExit(
            f"The database migration failed (alembic exit status {result.returncode}); its error is above. "
            "The backend stops here and does not retry it."
        )
    print("Database is ready and migrations are applied.", flush=True)


def wait_for_database_and_prepare() -> None:
    """Wait for a reachable PostgreSQL database, then apply migrations."""
    wait_for_database()
    apply_migrations()


def seed_development_sign_ins(settings: Settings) -> None:
    """In development and CI only, make the six demo users sign in with the demo password.

    The migrations no longer create them (TB-1 TB1-203), so a new development or CI database would
    otherwise hold no user at all. A hosted or production backend skips this. The account tool's own
    command does the work, and checks APP_ENV again itself; the application never imports tooling.
    """
    if not settings.is_development_environment:
        return
    subprocess.run(list(SEED_DEMO_USERS_COMMAND), check=True)


if __name__ == "__main__":
    settings = get_settings()
    wait_for_database_and_prepare()
    seed_development_sign_ins(settings)
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.backend_port)
