"""Test support for creates that carry a request key (TB-1 TB1-102 part b): running requests at once, and a record
as it was made before migration 20260908_0050 kept the request's fingerprint."""

from __future__ import annotations

import threading
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal

KEYED_TABLES = ("equipment_model", "equipment_asset", "resource_requirement")


def run_at_once(monkeypatch, module: Any, lookup_name: str, calls: list[Callable[[Session], Any]]) -> list[tuple[str, Any]]:
    """Run the calls at once, each in its own session, held at a barrier until every one has looked for its request
    key and found nothing - so they genuinely race, as two browser tabs submitting one form would. Only each thread's
    first lookup waits: a later lookup (under the module's lock, or after the key's unique index refused an insert)
    is the path under test. Each result is ("ok", the answer) or ("error", what was raised)."""
    original = getattr(module, lookup_name)
    barrier = threading.Barrier(len(calls), timeout=30)
    first_lookup_done: set[int] = set()
    guard = threading.Lock()

    def lookup_then_wait(db, *, create_request_key):
        found = original(db, create_request_key=create_request_key)
        with guard:
            first = threading.get_ident() not in first_lookup_done
            first_lookup_done.add(threading.get_ident())
        if first:
            barrier.wait()
        return found

    monkeypatch.setattr(module, lookup_name, lookup_then_wait)
    results: list[tuple[str, Any]] = [("not run", None)] * len(calls)

    def run(index: int, call: Callable[[Session], Any]) -> None:
        with SessionLocal() as db:
            try:
                results[index] = ("ok", call(db))
            except Exception as exc:  # the caller's assertion names what was raised
                results[index] = ("error", exc)

    threads = [threading.Thread(target=run, args=(index, call)) for index, call in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    return results


def user_public_id(username: str) -> str:
    with SessionLocal() as db:
        return str(db.execute(text("SELECT public_id FROM app_user WHERE username = :u"), {"u": username}).scalar_one())


def stored_fingerprints(table: str, key: str) -> list[str | None]:
    """The fingerprint on each record a key made (a kit lot has several)."""
    assert table in KEYED_TABLES
    with SessionLocal() as db:
        return list(
            db.execute(
                text(f"SELECT create_request_fingerprint FROM {table} WHERE create_request_key = :key ORDER BY id"),
                {"key": key},
            ).scalars()
        )


def as_made_before_fingerprints(table: str, key: str) -> None:
    """Make the records a key made look as they would had they been made before migration 0050: no fingerprint. The
    database refuses that change (the request that made a record never changes), so its trigger is set aside for
    this one statement, inside the transaction."""
    assert table in KEYED_TABLES
    with SessionLocal() as db:
        db.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER trg_{table}_create_request_kept"))
        changed = db.execute(
            text(f"UPDATE {table} SET create_request_fingerprint = NULL WHERE create_request_key = :key"), {"key": key}
        ).rowcount
        db.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER trg_{table}_create_request_kept"))
        assert changed >= 1
        db.commit()
