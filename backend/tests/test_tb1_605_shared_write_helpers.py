"""TB-1 TB1-605 (corrective package CS-12): one rollback-on-error helper, one advisory-lock call and one "today in India".

The Hiring modules each kept their own copy - the rollback block in five, the lock statement in four, "today" in three
definitions and nine inline conversions. They now import `app.shared.transactions` and `app.shared.business_time`. These
tests pin the shared helpers' behaviour. (Static guards against a module copying them again were tried in review and
dropped on the owner's decision, 8 October 2026: the register's test bar is the modules' own suites, and the date tests
patching one name.)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.resource_assignments.repository import WRITE_LOCK_KEY
from app.shared import business_time
from app.shared.transactions import rollback_on_error, take_advisory_lock

APP = Path(__file__).resolve().parents[1] / "app"


# --- rollback_on_error ------------------------------------------------------------------------------------------------


class _RecordingSession:
    def __init__(self) -> None:
        self.rollbacks = 0

    def rollback(self) -> None:
        self.rollbacks += 1


def test_an_error_rolls_back_and_continues() -> None:
    db = _RecordingSession()
    with pytest.raises(ValueError, match="refused"):
        with rollback_on_error(db):
            raise ValueError("refused")
    assert db.rollbacks == 1


def test_a_block_that_finishes_rolls_nothing_back() -> None:
    db = _RecordingSession()
    with rollback_on_error(db):
        pass
    assert db.rollbacks == 0


def test_only_an_exception_rolls_back() -> None:
    db = _RecordingSession()
    with pytest.raises(KeyboardInterrupt):
        with rollback_on_error(db):
            raise KeyboardInterrupt
    assert db.rollbacks == 0


# --- take_advisory_lock -----------------------------------------------------------------------------------------------


def _taken_elsewhere(statement: str) -> bool:
    with SessionLocal() as other:
        free = other.execute(text(statement)).scalar_one()
        other.rollback()
    return not free


@pytest.mark.parametrize(
    ("key", "probe"),
    [
        # Resource Assignments' key is a number because migration 20260908_0045's trigger takes the same lock by it.
        (WRITE_LOCK_KEY, "SELECT pg_try_advisory_xact_lock(80450001)"),
        ("eligibility.write", "SELECT pg_try_advisory_xact_lock(hashtextextended('eligibility.write', 0))"),
        ("equipment_reference.write", "SELECT pg_try_advisory_xact_lock(hashtextextended('equipment_reference.write', 0))"),
        ("holiday_calendar.write", "SELECT pg_try_advisory_xact_lock(hashtextextended('holiday_calendar.write', 0))"),
    ],
)
def test_the_lock_is_the_one_the_module_always_took_and_lasts_until_the_transaction_ends(key, probe) -> None:
    with SessionLocal() as db:
        take_advisory_lock(db, key)
        assert _taken_elsewhere(probe)
        db.rollback()
    assert not _taken_elsewhere(probe)


def test_resource_assignments_lock_number_is_the_migrations() -> None:
    migration = next((APP.parents[0] / "alembic" / "versions").glob("20260908_0045_*.py")).read_text(encoding="utf-8-sig")
    assert WRITE_LOCK_KEY == 80_450_001
    assert "WRITE_LOCK_KEY = 80_450_001" in migration


# --- business_time ----------------------------------------------------------------------------------------------------


def test_today_is_the_date_in_india() -> None:
    before = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    today = business_time.india_today()
    after = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    assert today in {before, after}


def test_a_moment_falls_on_its_india_date() -> None:
    # 19:00 UTC is 00:30 the next day in India; 18:29 UTC is still 23:59 the same day.
    assert business_time.india_date(datetime(2026, 10, 7, 19, 0, tzinfo=timezone.utc)) == date(2026, 10, 8)
    assert business_time.india_date(datetime(2026, 10, 7, 18, 29, tzinfo=timezone.utc)) == date(2026, 10, 7)
    assert business_time.india_date(datetime(2026, 10, 8, 0, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))) == date(2026, 10, 8)
