"""The tests' business day (`business_day_test_support.py`): the server, a service's clock and the rows PostgreSQL stamps
are held to it when a run has gone past midnight in India - here made to by setting the tests' day back - and left as
they are when it has not.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import text

from app.core.database import SessionLocal
from app.shared import business_time
from tests import business_day_test_support as support

# 00:02 on 9 October 2026 in India, as GitHub Actions run 37824561035 reached it.
AFTER_MIDNIGHT = datetime(2026, 10, 8, 18, 32, tzinfo=timezone.utc)


def _clock() -> SimpleNamespace:
    return SimpleNamespace(now=lambda: AFTER_MIDNIGHT)


def test_a_run_past_midnight_has_the_servers_today_and_a_named_clock_held_to_the_test_day(monkeypatch) -> None:
    monkeypatch.setattr(support, "_clock_today", lambda: date(2026, 10, 9))
    monkeypatch.setattr(support, "TODAY", date(2026, 10, 8))
    real_today, clock = business_time.india_today, _clock()
    with support.held_to_the_test_day((clock, "now")):
        assert business_time.india_today() == date(2026, 10, 8)
        # Moved back a whole day: 00:02 on 8 October in India.
        assert clock.now() == AFTER_MIDNIGHT - timedelta(days=1)
        assert business_time.india_date(clock.now()) == date(2026, 10, 8)
    assert business_time.india_today is real_today
    assert clock.now() == AFTER_MIDNIGHT


def test_a_run_still_on_the_test_day_leaves_the_clock_as_it_is(monkeypatch) -> None:
    monkeypatch.setattr(support, "_clock_today", lambda: date(2026, 10, 9))
    monkeypatch.setattr(support, "TODAY", date(2026, 10, 9))
    clock = _clock()
    with support.held_to_the_test_day((clock, "now")):
        assert business_time.india_today() == date(2026, 10, 9)
        assert clock.now() == AFTER_MIDNIGHT


def _event() -> int:
    with SessionLocal() as db:
        row_id = db.execute(
            text(
                "INSERT INTO business_event (public_id, event_name, source_module) "
                "VALUES (:public_id, 'BUSINESS_DAY_TEST', 'tests') RETURNING id"
            ),
            {"public_id": str(uuid.uuid4())},
        ).scalar_one()
        db.commit()
    return int(row_id)


def _stamped(row_id: int) -> datetime:
    with SessionLocal() as db:
        return db.execute(text("SELECT created_at FROM business_event WHERE id = :id"), {"id": row_id}).scalar_one()


def test_rows_made_in_the_block_are_moved_back_to_the_test_day_and_no_other(monkeypatch) -> None:
    # PostgreSQL's clock cannot be moved, so the tests' day is set a day behind it.
    monkeypatch.setattr(support, "TODAY", support._clock_today() - timedelta(days=1))
    before_the_block = _event()
    try:
        with support.dated_on_the_test_day("business_event"):
            made = _event()
            stamped = _stamped(made)
        moved = _stamped(made)
        days = (business_time.india_date(stamped) - support.TODAY).days
        assert days >= 1
        assert moved == stamped - timedelta(days=days)
        assert business_time.india_date(moved) == support.TODAY
        assert business_time.india_date(_stamped(before_the_block)) > support.TODAY
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM business_event WHERE event_name = 'BUSINESS_DAY_TEST'"))
            db.commit()
