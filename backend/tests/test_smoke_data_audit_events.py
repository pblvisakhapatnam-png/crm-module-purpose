"""Tests for the E2E login-audit-event cleanup helper (tooling/smoke_data/audit_events.py).

These exercise tooling, not a CRM business rule, so they live alongside the other harness
tests rather than in a module suite.

Every test inserts its own probe rows with generated identities, asserts against those rows
only, and deletes them in a `finally` block. The shared development database is left exactly
as each test found it, including when an assertion fails. Nothing here relies on the table
being empty, and nothing deletes by a broad predicate.

The actor names are generated per test rather than reusing the real seed usernames. An earlier
version passed `("sales1",)` as the allowlist and asserted exact counts such as `deleted == 2`.
Because `delete_login_events_after` is global above its boundary, any concurrent `sales1` login -
another test, an E2E run, a developer clicking through the UI - both broke the count and was
itself deleted. The allowlist is the isolation boundary, so each test now owns a private actor
and can neither see nor delete anything but its own probes. The real `DEFAULT_E2E_ACTORS` tuple
is still exercised, but only by the argument-validation tests, which touch no rows.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from tooling.smoke_data.audit_events import (
    AuditEventCleanupError,
    DEFAULT_E2E_ACTORS,
    capture_business_event_boundary,
    delete_login_events_after,
    find_unlisted_login_events_after,
)


def _probe_actor() -> str:
    """A unique, valid actor username owned by exactly one test.

    Must satisfy the helper's own identifier rule (alphanumerics plus underscores), so a plain
    hex suffix is used rather than a UUID with hyphens.
    """
    return "s9baudit_" + uuid4().hex[:12]


def _insert_event(
    *,
    event_name: str,
    source_module: str = "identity",
    username: str | None = None,
    record_type: str = "app_user",
) -> tuple[int, str]:
    """Insert one probe business_event row. Returns (id, public_id)."""
    public_id = str(uuid4())
    payload = json.dumps({"username": username}) if username is not None else None
    with SessionLocal() as db:
        row = db.execute(
            text(
                """
                INSERT INTO business_event
                    (public_id, event_name, source_module, record_type, record_public_id,
                     event_payload_json)
                VALUES
                    (:public_id, :event_name, :source_module, :record_type, :record_public_id,
                     :event_payload_json)
                RETURNING id
                """
            ),
            {
                "public_id": public_id,
                "event_name": event_name,
                "source_module": source_module,
                "record_type": record_type,
                "record_public_id": str(uuid4()),
                "event_payload_json": payload,
            },
        ).one()
        db.commit()
        return int(row._mapping["id"]), public_id


def _delete_events(public_ids: list[str]) -> None:
    """Remove probe rows by their generated public ids only."""
    if not public_ids:
        return
    with SessionLocal() as db:
        for public_id in public_ids:
            db.execute(
                text("DELETE FROM business_event WHERE public_id = :public_id"),
                {"public_id": public_id},
            )
        db.commit()


def _event_exists(public_id: str) -> bool:
    with SessionLocal() as db:
        return (
            db.execute(
                text("SELECT count(*) FROM business_event WHERE public_id = :public_id"),
                {"public_id": public_id},
            ).scalar_one()
            > 0
        )


def test_allowlisted_login_events_above_the_boundary_are_deleted() -> None:
    """Both login event names are removed for an allowlisted actor."""
    probes: list[str] = []
    actor = _probe_actor()
    try:
        boundary = capture_business_event_boundary()
        _, succeeded_id = _insert_event(event_name="UserLoginSucceeded", username=actor)
        _, failed_id = _insert_event(
            event_name="UserLoginFailed", username=actor, record_type="auth_login"
        )
        probes.extend([succeeded_id, failed_id])

        # Scoped to this test's own actor, so the exact count cannot be disturbed by - and the
        # deletion cannot reach - a login event created concurrently by anything else.
        deleted = delete_login_events_after(boundary, (actor,))

        assert deleted == 2
        assert not _event_exists(succeeded_id)
        assert not _event_exists(failed_id)
    finally:
        _delete_events(probes)


def test_login_events_at_or_below_the_boundary_are_preserved() -> None:
    """The boundary is exclusive: pre-existing rows must survive.

    This is the property that makes the whole helper safe to run against a shared database,
    so it is asserted directly rather than inferred from counts.
    """
    probes: list[str] = []
    actor = _probe_actor()
    try:
        _, pre_existing_id = _insert_event(event_name="UserLoginSucceeded", username=actor)
        probes.append(pre_existing_id)

        # Boundary captured AFTER the row exists, so that row is pre-existing.
        boundary = capture_business_event_boundary()
        _, after_id = _insert_event(event_name="UserLoginSucceeded", username=actor)
        probes.append(after_id)

        deleted = delete_login_events_after(boundary, (actor,))

        assert deleted == 1
        assert _event_exists(pre_existing_id), "a pre-boundary login event must never be deleted"
        assert not _event_exists(after_id)
    finally:
        _delete_events(probes)


def test_non_login_business_events_above_the_boundary_are_preserved() -> None:
    """Only the two login event names are eligible; business events are never touched."""
    probes: list[str] = []
    actor = _probe_actor()
    try:
        boundary = capture_business_event_boundary()
        _, account_event_id = _insert_event(
            event_name="AccountCreated", source_module="accounts", username=actor
        )
        _, login_event_id = _insert_event(event_name="UserLoginSucceeded", username=actor)
        probes.extend([account_event_id, login_event_id])

        deleted = delete_login_events_after(boundary, (actor,))

        assert deleted == 1
        assert _event_exists(account_event_id), "a business event must never be deleted"
        assert not _event_exists(login_event_id)
    finally:
        _delete_events(probes)


def test_cleanup_only_touches_the_identity_source_module() -> None:
    """A row carrying a login event name from another module is not this helper's to remove."""
    probes: list[str] = []
    actor = _probe_actor()
    try:
        boundary = capture_business_event_boundary()
        _, foreign_module_id = _insert_event(
            event_name="UserLoginSucceeded", source_module="accounts", username=actor
        )
        probes.append(foreign_module_id)

        deleted = delete_login_events_after(boundary, (actor,))

        assert deleted == 0
        assert _event_exists(foreign_module_id)
    finally:
        _delete_events(probes)


def test_unlisted_actor_login_events_are_preserved_and_reported_as_residual() -> None:
    """Drift detection: a login by an actor outside the allowlist survives and is reported.

    This is the fail-loud path. A future spec logging in as a seed user missing from
    DEFAULT_E2E_ACTORS must not have its events silently deleted, and must not be silently
    ignored either.
    """
    probes: list[str] = []
    listed_actor = _probe_actor()
    unlisted_actor = _probe_actor()
    try:
        boundary = capture_business_event_boundary()
        _, listed_id = _insert_event(event_name="UserLoginSucceeded", username=listed_actor)
        _, unlisted_id = _insert_event(event_name="UserLoginSucceeded", username=unlisted_actor)
        probes.extend([listed_id, unlisted_id])

        deleted = delete_login_events_after(boundary, (listed_actor,))
        residual = find_unlisted_login_events_after(boundary, (listed_actor,))

        assert deleted == 1
        assert _event_exists(unlisted_id), "an unlisted actor's login event must be preserved"

        usernames = [row["payload_username"] for row in residual]
        assert unlisted_actor in usernames
        assert all(row["event_name"] in ("UserLoginSucceeded", "UserLoginFailed") for row in residual)
        assert all(isinstance(row["id"], int) for row in residual)
    finally:
        _delete_events(probes)


def test_residual_check_is_empty_once_every_actor_is_listed() -> None:
    """The drift check must not produce false positives for genuinely allowlisted actors."""
    probes: list[str] = []
    actors = tuple(_probe_actor() for _ in DEFAULT_E2E_ACTORS)
    try:
        boundary = capture_business_event_boundary()
        for actor in actors:
            _, public_id = _insert_event(event_name="UserLoginSucceeded", username=actor)
            probes.append(public_id)

        delete_login_events_after(boundary, actors)
        residual = find_unlisted_login_events_after(boundary, actors)

        # Asserted against this test's own actors rather than `residual == []`. The residual view
        # is global above the boundary, so an unrelated concurrent login would legitimately appear
        # there; what must never appear is an actor that *is* on the allowlist.
        reported = [row["payload_username"] for row in residual]
        assert [name for name in reported if name in actors] == []
    finally:
        _delete_events(probes)


def test_residual_check_reports_a_login_event_with_no_payload_username() -> None:
    """A login event without a usable username cannot be attributed, so it is not deleted."""
    probes: list[str] = []
    actor = _probe_actor()
    try:
        boundary = capture_business_event_boundary()
        no_payload_row_id, no_payload_id = _insert_event(
            event_name="UserLoginSucceeded", username=None
        )
        probes.append(no_payload_id)

        deleted = delete_login_events_after(boundary, (actor,))
        residual = find_unlisted_login_events_after(boundary, (actor,))

        assert deleted == 0
        assert _event_exists(no_payload_id)
        # The specific unattributable row must be reported, not merely "something was".
        assert no_payload_row_id in [row["id"] for row in residual]
    finally:
        _delete_events(probes)


@pytest.mark.parametrize(
    "actors",
    [
        (),
        ("",),
        ("sales1", ""),
        ("bad'; DROP TABLE business_event; --",),
        ("sales 1",),
        ("sales-1",),
    ],
)
def test_invalid_actor_arguments_are_rejected(actors: tuple[str, ...]) -> None:
    """Empty or non-identifier actor values must never reach the database."""
    with pytest.raises(AuditEventCleanupError):
        delete_login_events_after(0, actors)
    with pytest.raises(AuditEventCleanupError):
        find_unlisted_login_events_after(0, actors)


@pytest.mark.parametrize("boundary_id", [-1, -100])
def test_negative_boundary_is_rejected(boundary_id: int) -> None:
    with pytest.raises(AuditEventCleanupError):
        delete_login_events_after(boundary_id, DEFAULT_E2E_ACTORS)
    with pytest.raises(AuditEventCleanupError):
        find_unlisted_login_events_after(boundary_id, DEFAULT_E2E_ACTORS)


@pytest.mark.parametrize("boundary_id", ["0", None, 1.5, True])
def test_non_integer_boundary_is_rejected(boundary_id: object) -> None:
    """Guards against a string boundary from a CLI/PowerShell path reaching the query."""
    with pytest.raises(AuditEventCleanupError):
        delete_login_events_after(boundary_id, DEFAULT_E2E_ACTORS)  # type: ignore[arg-type]


def test_capture_boundary_returns_a_non_negative_int_and_tracks_new_rows() -> None:
    probes: list[str] = []
    try:
        first = capture_business_event_boundary()
        assert isinstance(first, int)
        assert first >= 0

        _, public_id = _insert_event(event_name="UserLoginSucceeded", username=_probe_actor())
        probes.append(public_id)

        assert capture_business_event_boundary() > first
    finally:
        _delete_events(probes)
