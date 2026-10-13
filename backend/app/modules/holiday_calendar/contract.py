"""Holiday calendar codes (HOL-1).

docs/agent/slices/hol-1-holiday-calendar.md, sections 5.1 and 10; the API is
docs/agent/contracts/holiday-calendar-api-contract.md.
"""

from __future__ import annotations

from typing import Final

HOLIDAY_CALENDAR_MODULE_NAME: Final = "holiday_calendar"
RECORD_TYPE_YEAR: Final = "holiday_calendar_year"

# The words of the states' National and Festival Holidays Acts. The kind only describes the day: it does not decide
# where a holiday applies - a state may count its own day among its national holidays (1.2, point 2).
KIND_NATIONAL: Final = "NATIONAL"
KIND_FESTIVAL: Final = "FESTIVAL"
KIND_CODES: Final = (KIND_NATIONAL, KIND_FESTIVAL)
KIND_LABELS: Final = {KIND_NATIONAL: "National holiday", KIND_FESTIVAL: "Festival holiday"}

APPLIES_ALL_INDIA: Final = "ALL_INDIA"
APPLIES_STATES: Final = "STATES"
APPLIES_TO_CODES: Final = (APPLIES_ALL_INDIA, APPLIES_STATES)

# A year is any year from 2000 to 2100 (section 5.1); the migration's CHECK holds the same range.
FIRST_YEAR: Final = 2000
LAST_YEAR: Final = 2100

NAME_MAX_LENGTH: Final = 255
# Far more than any year holds - a holiday for each state on every festival - so only a request far beyond it is
# refused by the schema.
MAX_HOLIDAYS_PER_YEAR: Final = 1000

EVENT_YEAR_RECORDED: Final = "HOLIDAY_CALENDAR_YEAR_RECORDED"
EVENT_YEAR_CHANGED: Final = "HOLIDAY_CALENDAR_YEAR_CHANGED"
