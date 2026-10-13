"""Write plumbing the Hiring modules share (TB-1 TB1-605, corrective package CS-12).

Five modules had their own copy of the rollback-on-error block and four their own advisory-lock statement. One
definition now, so a change to either is made once (CODING_STANDARDS.md, section 1).
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy import text
from sqlalchemy.orm import Session


class rollback_on_error:
    """Roll the transaction back if the block raises, then let the error continue.

    `with rollback_on_error(db):` is exactly

        except Exception:
            db.rollback()
            raise

    Only an Exception rolls back, and the error is never suppressed. The commit stays an explicit statement in each
    write, as the block's last, so a reader sees what is inside the transaction and where it becomes permanent. A class
    rather than @contextmanager, so no generator sits between the error and the rollback.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def __enter__(self) -> None:
        return None

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> bool:
        if exc_type is not None and issubclass(exc_type, Exception):
            self._db.rollback()
        return False


def take_advisory_lock(db: Session, key: str | int) -> None:
    """Wait for a transaction-level advisory lock; it is held until the transaction ends.

    A text key is hashed by PostgreSQL (`hashtextextended(key, 0)`); a number is the lock itself. Resource Assignments'
    key is a number because migration 20260908_0045's trigger takes the same lock by that number.
    """
    if isinstance(key, int):
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
    else:
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key})
