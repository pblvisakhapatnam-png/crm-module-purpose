"""Stopping repeated wrong passwords for one username (TB-1 TB1-204 part a).

The owner's decision, 7 October 2026: five failed sign-ins for one username within fifteen minutes, with no
successful sign-in among them, stop that username for fifteen minutes; an admin can lift it early with the account
tool's `unlock`. The numbers are fixed below, not settings, so no configuration can weaken the stop (review round 9);
a stop is never shorter than the window, so when it runs out the attempts that made it have left the window. The window rolls: the attempts counted are those of the last fifteen minutes, whenever
they began, so no boundary lets more than five through.

Counted per typed username, not per network address: on the hosted pilots every request reaches the backend from
nginx, which forwards no client address, so counting by address would stop everyone together. Counted whether or
not an account has the name, so being stopped never shows which usernames exist. Held as the SHA-256 of the
lower-cased name (PostgreSQL's `lower()`, the one the sign-in lookup uses, so every spelling that reaches an account
shares its count), never as text: what someone types in the username box is sometimes their password.

How it stays right under concurrency:

- Each attempt is one row of `sign_in_attempt`, numbered by a database sequence, so a number is never used twice -
  not even after old rows are pruned. A stop is one row of `sign_in_stop`.
- Everything that reads or writes one name's rows first takes that name's advisory lock, in its own transaction, and
  touches no other name's rows. Attempts for one name are therefore taken one at a time, and attempts for two names
  never wait for each other.
- An attempt is counted before its password is checked, and the caller commits at once, so a burst of parallel
  guesses gets no more than the limit checked, and no lock is held while a password is hashed. The attempt that
  reaches the limit stops the name in that same transaction, and the caller records the stop's event there too, so a
  stop never exists without its record.
- A successful sign-in removes only its own attempt and those numbered before it: one that came after it, still
  being checked or already failed, keeps counting. It lifts a stop in force only when fewer than the limit of attempts
  remain in the window.
- Old rows are pruned in a transaction of their own that skips any row another transaction holds, so it never waits,
  and only rows a minute past the window or stop, so it never removes one a concurrent attempt still counts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session


# Pruning leaves rows this long past their window or stop, so it never races an attempt whose clock read a moment
# earlier than the pruning one's.
# The owner's decision, 7 October 2026.
ATTEMPT_LIMIT = 5
ATTEMPT_WINDOW = timedelta(minutes=15)
STOP_LENGTH = timedelta(minutes=15)
assert STOP_LENGTH >= ATTEMPT_WINDOW, "a stop is never shorter than the window"

PRUNE_MARGIN = timedelta(minutes=1)
# At most this many rows of each table per pruning, so one sign-in never carries a large cleanup.
PRUNE_BATCH = 1000


@dataclass(frozen=True)
class Attempt:
    """One counted sign-in attempt."""

    username_digest: str
    # The attempt's number from the database sequence; None when it was refused without being counted.
    number: int | None
    # Set when the name was already stopped: the attempt is refused without checking its password.
    stopped_until: datetime | None
    # Set when this attempt reached the limit: the name is stopped until then unless a success lifts it.
    stops_until: datetime | None


def username_digest(db: Session, username: str) -> str:
    return str(
        db.execute(
            text("SELECT encode(sha256(convert_to(lower(CAST(:username AS VARCHAR)), 'UTF8')), 'hex')"),
            {"username": username},
        ).scalar_one()
    )


def _lock_name(db: Session, digest: str) -> None:
    """This name's attempts and stop, one transaction at a time, until the transaction ends."""
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"identity.sign_in:{digest}"})


def _stop_in_force(db: Session, digest: str, now: datetime) -> datetime | None:
    locked_until = db.execute(
        text("SELECT locked_until FROM sign_in_stop WHERE username_digest = :digest"), {"digest": digest}
    ).scalar()
    return locked_until if locked_until is not None and locked_until > now else None


def _attempts_in_window(db: Session, digest: str, now: datetime) -> int:
    window_start = now - ATTEMPT_WINDOW
    return int(
        db.execute(
            text(
                "SELECT count(*) FROM sign_in_attempt WHERE username_digest = :digest AND attempted_at > :window_start"
            ),
            {"digest": digest, "window_start": window_start},
        ).scalar_one()
    )


def prune(db: Session, now: datetime) -> None:
    """Remove attempts and stops long past; the caller commits at once, in a transaction of its own."""
    db.execute(
        text(
            "DELETE FROM sign_in_attempt WHERE id IN (SELECT id FROM sign_in_attempt WHERE attempted_at <= :cutoff "
            "ORDER BY id LIMIT :batch FOR UPDATE SKIP LOCKED)"
        ),
        {"cutoff": now - ATTEMPT_WINDOW - PRUNE_MARGIN, "batch": PRUNE_BATCH},
    )
    db.execute(
        text(
            "DELETE FROM sign_in_stop WHERE username_digest IN (SELECT username_digest FROM sign_in_stop "
            "WHERE locked_until <= :cutoff LIMIT :batch FOR UPDATE SKIP LOCKED)"
        ),
        {"cutoff": now - PRUNE_MARGIN, "batch": PRUNE_BATCH},
    )


def register_attempt(db: Session, username: str, now: datetime) -> Attempt:
    """Count one attempt for `username` at `now`. The caller commits before checking the password."""
    digest = username_digest(db, username)
    _lock_name(db, digest)

    stopped_until = _stop_in_force(db, digest, now)
    if stopped_until is not None:
        return Attempt(username_digest=digest, number=None, stopped_until=stopped_until, stops_until=None)

    earlier = _attempts_in_window(db, digest, now)
    number = int(
        db.execute(
            text(
                "INSERT INTO sign_in_attempt (username_digest, attempted_at) VALUES (:digest, :now) RETURNING id"
            ),
            {"digest": digest, "now": now},
        ).scalar_one()
    )
    stops_until = None
    if earlier + 1 >= ATTEMPT_LIMIT:
        stops_until = now + STOP_LENGTH
        # Any row there is a stop that has run out (one in force returned above).
        db.execute(
            text(
                "INSERT INTO sign_in_stop (username_digest, locked_until) VALUES (:digest, :locked_until) "
                "ON CONFLICT (username_digest) DO UPDATE SET locked_until = EXCLUDED.locked_until"
            ),
            {"digest": digest, "locked_until": stops_until},
        )
    return Attempt(username_digest=digest, number=number, stopped_until=None, stops_until=stops_until)


def clear_attempts(db: Session, attempt: Attempt, now: datetime) -> bool:
    """A successful sign-in, `attempt`: its own attempt and those before it go; later ones keep counting.

    A stop in force stands only if the limit's worth of attempts remain in the window; otherwise it is lifted.
    Returns True when this lifted a stop in force - the caller records it.
    """
    if attempt.number is None:
        return False
    _lock_name(db, attempt.username_digest)
    db.execute(
        text("DELETE FROM sign_in_attempt WHERE username_digest = :digest AND id <= :number"),
        {"digest": attempt.username_digest, "number": attempt.number},
    )
    if _stop_in_force(db, attempt.username_digest, now) is None:
        return False
    if _attempts_in_window(db, attempt.username_digest, now) >= ATTEMPT_LIMIT:
        return False
    db.execute(text("DELETE FROM sign_in_stop WHERE username_digest = :digest"), {"digest": attempt.username_digest})
    return True


def unlock(db: Session, username: str, now: datetime) -> bool:
    """Lift a stop on `username` early, with its count. True if it was stopped; a name not stopped keeps its count."""
    digest = username_digest(db, username)
    _lock_name(db, digest)
    lifted = db.execute(
        text(
            "DELETE FROM sign_in_stop WHERE username_digest = :digest AND locked_until > :now RETURNING username_digest"
        ),
        {"digest": digest, "now": now},
    ).scalar()
    if lifted is None:
        return False
    db.execute(text("DELETE FROM sign_in_attempt WHERE username_digest = :digest"), {"digest": digest})
    return True
