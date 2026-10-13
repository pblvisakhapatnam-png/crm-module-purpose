"""HOL-1 test support: a year of PBL's holiday calendar that a test owns, removed when it ends.

The calendar is shared by everyone, so a test never saves a year anyone might really use: it takes a year in the
2090s, clears whatever a killed earlier run left in it, and removes it - its holidays, their states and the year -
when it ends. Business events need no cleanup: conftest removes every event the session creates.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text

from app.core.database import SessionLocal

# Years nobody keeps a real calendar for. Each call takes the next, so tests in one session never share one.
_TEST_YEARS = itertools.cycle(range(2090, 2093))


def remove_calendar_years(years: list[int]) -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                "DELETE FROM holiday_calendar_holiday_state WHERE holiday_id IN (SELECT h.id FROM holiday_calendar_holiday h "
                "JOIN holiday_calendar_year y ON y.id = h.year_id WHERE y.calendar_year = ANY(:years))"
            ),
            {"years": years},
        )
        db.execute(
            text(
                "DELETE FROM holiday_calendar_holiday WHERE year_id IN "
                "(SELECT id FROM holiday_calendar_year WHERE calendar_year = ANY(:years))"
            ),
            {"years": years},
        )
        db.execute(text("DELETE FROM holiday_calendar_year WHERE calendar_year = ANY(:years)"), {"years": years})
        db.commit()


@contextmanager
def calendar_test_years(count: int = 1) -> Iterator[list[int]]:
    years = [next(_TEST_YEARS) for _ in range(count)]
    remove_calendar_years(years)
    try:
        yield years
    finally:
        remove_calendar_years(years)
