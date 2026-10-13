"""A date and time the API takes in: only with its zone, and held as UTC (the entered-time fix, October 2026).

A person types a date and time in India's time; the screen sends it as a UTC instant with its zone ("Z"), the CRM
tables store it in UTC, and the screen shows it in India's time again (ADR-028, "Timestamps"). A value with no zone
could be read two ways, and was: the offer page once sent the India time typed with no zone, the API stored it as if
it were UTC, and the screen showed it 5 hours 30 minutes late. So every date and time a request carries - in its body
or its query - is refused without a zone, and converted to UTC with one. `tests/test_entered_time_zone.py` walks every
route and fails on a date-and-time input that does not use this type.

Two checks, because Pydantic would otherwise make a moment out of a number: given 1791781200, or the text
"1791781200", it reads seconds since 1970 and hands back a time already in UTC, which the zone check could not tell
from one sent with "Z". So the request's own value is checked first - text in the ISO form with "Z" or an offset, or
a Python datetime from code - and the moment's zone second.

Times the server sets itself (created at, updated at, a decision's time) never pass through here, and the times the
API sends back are unchanged: the CRM tables' times are sent without a zone and are UTC (TB-1 TB1-401, TB1-604).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator

ZONELESS_DATETIME_MESSAGE = (
    "Give the date and time with its time zone, for example 2026-10-12T05:00:00Z or 2026-10-12T10:30:00+05:30."
)

# A date and a time to the minute or finer, then "Z" or an offset: 2026-10-12T05:00:00.000Z, 2026-10-12T10:30+05:30.
_DATE_TIME_TEXT_WITH_ZONE = re.compile(
    r"\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:[Zz]|[+-]\d{2}:?\d{2})"
)


def written_with_zone(value: object) -> object:
    """The request's value as it came: ISO text with its zone, or a datetime made in code. Anything else - a number,
    digits as text, text without a zone - is refused (ValueError, which a request answers with 422)."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and _DATE_TIME_TEXT_WITH_ZONE.fullmatch(value):
        return value
    raise ValueError(ZONELESS_DATETIME_MESSAGE)


def in_utc(value: datetime) -> datetime:
    """The same moment in UTC. Refuses a value with no zone (ValueError, which a request answers with 422)."""
    if value.utcoffset() is None:
        raise ValueError(ZONELESS_DATETIME_MESSAGE)
    return value.astimezone(timezone.utc)


ZonedDateTime = Annotated[datetime, BeforeValidator(written_with_zone), AfterValidator(in_utc)]
