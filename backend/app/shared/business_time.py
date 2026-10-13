"""Today's date where PBL works (TB-1 TB1-605, corrective package CS-12).

The servers' clocks run on UTC, 5.5 hours behind India, so "today" is asked of this module, never of the clock. Call
it through the module - `business_time.india_today()` - so a test that fixes the date patches one name.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

BUSINESS_TIME_ZONE = ZoneInfo("Asia/Kolkata")


def india_today() -> date:
    """Today in Asia/Kolkata."""
    return datetime.now(BUSINESS_TIME_ZONE).date()


def india_date(moment: datetime) -> date:
    """The date a moment falls on in Asia/Kolkata."""
    return moment.astimezone(BUSINESS_TIME_ZONE).date()
