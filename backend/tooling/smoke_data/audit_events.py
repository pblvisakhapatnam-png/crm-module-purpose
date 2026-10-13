"""Run-scoped cleanup of login audit events created by an E2E run.

The Playwright suite authenticates through the real `/login` form, so every spec that
logs in writes a genuine `UserLoginSucceeded` row. The TE-1 manifest cleanup removes the
seeded *business* records but has no way to know about those events - they belong to
`app_user`, not to any seeded record - so they accumulated on every run.

This module is the narrow counterpart to that: it removes only the login events one E2E
run produced. Three independent conditions must all hold before a row is deleted:

1. `id` is strictly above a boundary captured before the run, so nothing that already
   existed can be touched;
2. `event_name` is one of the two login events and `source_module` is `identity`, so no
   business event is ever removed;
3. the username in the event payload is on a narrow allowlist of E2E test actors, so a
   real person's login audit trail is never deleted.

There is deliberately no "delete all login events" mode and no table-clearing path.

Because the allowlist is narrow, a future spec that logs in as a seed user not on it would
leave its login events behind silently. `find_unlisted_login_events_after()` closes that
gap: after the allowlisted deletion, any identity login event still above the boundary is
reported rather than deleted, and the caller turns that into a non-zero exit. Unknown audit
rows are still never removed - the run just fails loudly instead of quietly leaking.

Testing/tooling code only. Never imported by `app.main` and not reachable through any
public API route.
"""

from __future__ import annotations

from sqlalchemy import bindparam, text

from app.core.database import SessionLocal

# The only event names this module will ever delete. Both are written by
# app/modules/identity/routes.py on the login path.
LOGIN_EVENT_NAMES = ("UserLoginSucceeded", "UserLoginFailed")

# The prototype seed users the Playwright specs log in as. Deliberately a hand-maintained
# allowlist rather than something derived by parsing spec source: parsing would silently
# widen the deletion scope whenever a spec changed, which is exactly the property this
# module must not have. Drift is caught instead by the residual check below, which fails
# the run when a login event by any other actor survives cleanup.
#
# This is not the only place the allowlist appears: scripts/run-e2e.ps1 mirrors the same
# narrow list explicitly in its own $e2eActors variable and passes it on the command line,
# so the operational value is visible at the call site rather than defaulted silently. The
# two locations are independent copies and must be updated together. Forgetting the script
# side is not silent - the residual check fails the run when a Playwright spec logs in as an
# actor missing from the list actually passed.
DEFAULT_E2E_ACTORS = ("admin1", "sales1", "readonly1")


class AuditEventCleanupError(RuntimeError):
    """Raised when the requested cleanup arguments are not safe to act on."""


def capture_business_event_boundary() -> int:
    """Return the current maximum `business_event` id.

    Every row at or below this id is pre-existing as far as the E2E run is concerned and
    is never eligible for deletion.
    """
    with SessionLocal() as db:
        return int(db.execute(text("SELECT COALESCE(MAX(id), 0) FROM business_event")).scalar_one())


def _validate_arguments(boundary_id: int, actors: tuple[str, ...]) -> None:
    """Reject argument shapes that would widen deletion beyond the intended scope."""
    if not isinstance(boundary_id, int) or isinstance(boundary_id, bool):
        raise AuditEventCleanupError(f"boundary_id must be an int, got {boundary_id!r}.")
    if boundary_id < 0:
        raise AuditEventCleanupError(f"boundary_id must be >= 0, got {boundary_id!r}.")
    if not actors:
        raise AuditEventCleanupError(
            "At least one actor username is required. Refusing to delete login events for "
            "an unrestricted set of users."
        )

    unknown = [actor for actor in actors if not actor or not actor.replace("_", "").isalnum()]
    if unknown:
        raise AuditEventCleanupError(f"Refusing to act on non-identifier actor value(s): {unknown!r}.")


def find_unlisted_login_events_after(
    boundary_id: int,
    actors: tuple[str, ...] = DEFAULT_E2E_ACTORS,
) -> list[dict[str, object]]:
    """Return identity login events above `boundary_id` whose actor is NOT on the allowlist.

    Read-only by design. These rows are reported so the run can fail, never deleted: an
    unrecognised actor may be a real user, and this module's whole safety property is that
    it only ever removes rows it can positively identify as E2E test noise.

    A non-empty result means either a spec started using a seed user missing from
    DEFAULT_E2E_ACTORS, or something other than the E2E suite was logging in concurrently.
    Both deserve a visible failure rather than a silent leak.
    """
    _validate_arguments(boundary_id, actors)

    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT id,
                       event_name,
                       (NULLIF(event_payload_json, '')::json ->> 'username') AS payload_username
                FROM business_event
                WHERE id > :boundary_id
                  AND source_module = 'identity'
                  AND event_name IN :event_names
                  AND (
                        (NULLIF(event_payload_json, '')::json ->> 'username') IS NULL
                        OR (NULLIF(event_payload_json, '')::json ->> 'username') NOT IN :actors
                      )
                ORDER BY id
                """
            ).bindparams(
                bindparam("event_names", expanding=True),
                bindparam("actors", expanding=True),
            ),
            {
                "boundary_id": boundary_id,
                "event_names": list(LOGIN_EVENT_NAMES),
                "actors": list(actors),
            },
        ).all()

    return [
        {
            "id": int(row._mapping["id"]),
            "event_name": str(row._mapping["event_name"]),
            "payload_username": row._mapping["payload_username"],
        }
        for row in rows
    ]


def delete_login_events_after(boundary_id: int, actors: tuple[str, ...] = DEFAULT_E2E_ACTORS) -> int:
    """Delete login events above `boundary_id` for the named actors. Returns the row count.

    `business_event` has no foreign key to any business table, so deleting these rows is
    FK-safe and cannot orphan or cascade into business records.
    """
    _validate_arguments(boundary_id, actors)

    with SessionLocal() as db:
        result = db.execute(
            text(
                """
                DELETE FROM business_event
                WHERE id > :boundary_id
                  AND source_module = 'identity'
                  AND event_name IN :event_names
                  AND (NULLIF(event_payload_json, '')::json ->> 'username') IN :actors
                """
            ).bindparams(
                # expanding=True renders these as real IN lists rather than a single bound
                # value, so the values stay parameterized instead of being interpolated.
                bindparam("event_names", expanding=True),
                bindparam("actors", expanding=True),
            ),
            {
                "boundary_id": boundary_id,
                "event_names": list(LOGIN_EVENT_NAMES),
                "actors": list(actors),
            },
        )
        db.commit()
        return int(result.rowcount or 0)
