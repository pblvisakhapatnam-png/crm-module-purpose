"""The tests' business day: today in India, read once, with the server held to it (9 October 2026).

A test dates what it sends, and what it expects back, from today, read once when the tests are collected. The server
reads today afresh at every request (`business_time.india_today()`, CODING_STANDARDS.md section 2), and its records are
stamped with the clock - a service's, or PostgreSQL's own. A run collected before midnight in India and still running
after it therefore expected yesterday while the server answered today: GitHub Actions run 37824561035 on PR #110,
collected at 23:52 on 8 October 2026 and running these tests from 00:02 on 9 October, failed eight Hiring tests so.

- `TODAY` is that one day, for every module that dates from it.
- `held_to_the_test_day()` holds the server to it: its today, and each clock named that a service stamps its records
  with, moved back by the whole days the run has gone past `TODAY` - so a record made after midnight is dated `TODAY`,
  as one made before it is. A module that dates from `TODAY` wraps itself in it, module-scoped and autouse, so that its
  module-scoped fixtures run on that day too. A test that moves the day itself
  (`monkeypatch.setattr(business_time, "india_today", ...)`) still can; its patch is undone back to `TODAY`.
- `dated_on_the_test_day(table)` does the same for rows PostgreSQL stamps itself, which no patch reaches: it moves
  the rows a block made back to `TODAY` afterwards.

Before midnight neither moves anything: the clocks and the rows are on `TODAY` already.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from app.shared import business_time

# The clock's today, kept before any test patches the name.
_clock_today = business_time.india_today
TODAY = _clock_today()


def _days_past_the_test_day() -> timedelta:
    return _clock_today() - TODAY


def _held(clock: Callable[[], datetime]) -> Callable[[], datetime]:
    return lambda: clock() - _days_past_the_test_day()


@contextmanager
def held_to_the_test_day(*clocks: tuple[object, str]) -> Iterator[None]:
    """The server's today held to `TODAY` inside the block, and each clock named as `(module, name)` held to it too."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(business_time, "india_today", lambda: TODAY)
        for owner, name in clocks:
            patch.setattr(owner, name, _held(getattr(owner, name)))
        yield


@contextmanager
def dated_on_the_test_day(table: str) -> Iterator[None]:
    """The rows of `table` made inside the block, whose `created_at` PostgreSQL stamps, dated `TODAY` in India: one
    stamped on a later day is moved back by whole days, keeping its time of day."""
    with SessionLocal() as db:
        last = int(db.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table}")).scalar_one())
    yield
    day = "CAST(created_at AT TIME ZONE :zone AS date)"
    with SessionLocal() as db:
        db.execute(
            text(
                f"UPDATE {table} SET created_at = created_at - make_interval(days => {day} - :today) "
                f"WHERE id > :last AND {day} > :today"
            ),
            {"zone": business_time.BUSINESS_TIME_ZONE.key, "today": TODAY, "last": last},
        )
        db.commit()
