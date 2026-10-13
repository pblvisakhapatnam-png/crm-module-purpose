"""Pure rules for the Work Order contract period (Slice 7D Part 3).

No database, no clock, no I/O: every function here takes the dates it needs and returns an answer,
so the rules can be tested exhaustively and reused. Owner decision 17 of 17 September 2026 asks for
exactly that - "the rule behind them is built and tested now, for log sheets, release and billing to
use later".

Two things live here, and they are deliberately separate:

- `classify_date_against_contract` answers "is this date inside the contract?" and nothing else.
  That is the reusable core. A log sheet asking whether a working day falls inside the contract
  (FRS 2.5.1), Work Order release asking whether it may release, and billing asking whether a
  billed day is covered, all want the classification - not a sentence written for one screen.
- The message builders phrase that answer for the one place it is refused, because owner decision 17
  also asks that "every refusal says why", naming the dates. Keeping the wording beside the rule
  rather than scattered through the service is what keeps those messages consistent.

`NOT_DETERMINED` matters more than it looks. When the contract has no start date recorded, whether a
date falls inside it is not knowable - and answering `WITHIN` would be a guess. WBT-001's rule that a
missing term is never guessed applies to a missing date for the same reason: a later caller that
treats "we do not know" as "yes" would bill or release against a contract nobody has recorded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# --- What a date's position against the contract can be -------------------------------------------

CONTRACT_DATE_WITHIN = "WITHIN"
CONTRACT_DATE_BEFORE_START = "BEFORE_START"
CONTRACT_DATE_AFTER_END = "AFTER_END"
# Neither bound is broken, but at least one is not recorded, so "inside the contract" is not knowable.
CONTRACT_DATE_NOT_DETERMINED = "NOT_DETERMINED"
# Between an end date and an extension that starts later than the day after it: no contract runs
# (owner's clarification, 22 September 2026).
CONTRACT_DATE_IN_GAP = "IN_GAP"

CONTRACT_DATE_OUTCOMES = (
    CONTRACT_DATE_WITHIN,
    CONTRACT_DATE_BEFORE_START,
    CONTRACT_DATE_AFTER_END,
    CONTRACT_DATE_NOT_DETERMINED,
    CONTRACT_DATE_IN_GAP,
)
# The outcomes that mean the date is definitely outside the contract. A caller that must refuse
# should test membership of this, never equality with WITHIN - NOT_DETERMINED is not a refusal.
CONTRACT_DATE_OUTSIDE_OUTCOMES = (CONTRACT_DATE_BEFORE_START, CONTRACT_DATE_AFTER_END, CONTRACT_DATE_IN_GAP)


# --- Gaps between an end date and a later extension --------------------------------------------------
#
# An extension normally starts the day after the end it follows, so the contract runs on without a
# break. The owner allows a later start, confirmed by the user (22 September 2026), and decided that
# the days in between are outside the contract: no log sheet or bill may fall on them. A gap is always
# after the contract's original end, because extensions only move the end later.


@dataclass(frozen=True)
class ContractGap:
    """Days no contract runs on: from the day after an end date to the day before an extension starts.

    Both days are inclusive. `extension_sequence_no` names the extension that starts after it."""

    first_day: date
    last_day: date
    extension_sequence_no: int


def day_after(value: date) -> date:
    return value + timedelta(days=1)


def gap_before_extension(
    *, previous_end: date | None, extension_start: date | None, extension_sequence_no: int
) -> ContractGap | None:
    """The gap an extension leaves, or None when it runs straight on - or when there was no fixed end
    for it to follow, in which case there is nothing to leave a gap after."""
    if previous_end is None or extension_start is None:
        return None
    if extension_start <= day_after(previous_end):
        return None
    return ContractGap(
        first_day=day_after(previous_end),
        last_day=extension_start - timedelta(days=1),
        extension_sequence_no=extension_sequence_no,
    )


def gap_containing(value: date, gaps: tuple[ContractGap, ...] | list[ContractGap]) -> ContractGap | None:
    for gap in gaps:
        if gap.first_day <= value <= gap.last_day:
            return gap
    return None


def classify_date_against_contract(
    value: date,
    *,
    contract_start: date | None,
    contract_end: date | None,
    gaps: tuple[ContractGap, ...] | list[ContractGap] = (),
) -> str:
    """Where one date sits against a contract period. The reusable rule (owner decision 17).

    Both bounds are inclusive: work on the contract's first and last day is inside it.

    A bound that is not recorded cannot be broken, so it is not treated as broken. When neither
    recorded bound is broken but one is missing, the answer is NOT_DETERMINED rather than WITHIN,
    because the question was not answerable. A date inside a gap is IN_GAP whether or not the start is
    recorded: a gap is made only of recorded dates, so it is always knowable.
    """
    if contract_start is not None and value < contract_start:
        return CONTRACT_DATE_BEFORE_START
    if contract_end is not None and value > contract_end:
        return CONTRACT_DATE_AFTER_END
    if gap_containing(value, gaps) is not None:
        return CONTRACT_DATE_IN_GAP
    if contract_start is None or contract_end is None:
        return CONTRACT_DATE_NOT_DETERMINED
    return CONTRACT_DATE_WITHIN


def date_is_outside_contract(
    value: date,
    *,
    contract_start: date | None,
    contract_end: date | None,
    gaps: tuple[ContractGap, ...] | list[ContractGap] = (),
) -> bool:
    """True only when the date is definitely outside. An unrecorded bound never makes this true."""
    return (
        classify_date_against_contract(
            value, contract_start=contract_start, contract_end=contract_end, gaps=gaps
        )
        in CONTRACT_DATE_OUTSIDE_OUTCOMES
    )


# --- Wording ---------------------------------------------------------------------------------------


def format_contract_date(value: date) -> str:
    """"1 May 2027" - the form owner decision 17's own example messages use.

    Built from the parts rather than with a `%-d`/`%#d` format code, because that code differs
    between platforms and this runs on Linux in Docker and on Windows in a developer's tests.
    """
    return f"{value.day} {value:%B %Y}"


def describe_contract_period(contract_start: date | None, contract_end: date | None) -> str:
    """The contract's own dates, for a message that has to name them."""
    if contract_start is not None and contract_end is not None:
        return f"{format_contract_date(contract_start)} to {format_contract_date(contract_end)}"
    if contract_start is not None:
        return f"from {format_contract_date(contract_start)}"
    if contract_end is not None:
        return f"until {format_contract_date(contract_end)}"
    return "not recorded"


def gap_message(value: date, gap: ContractGap, *, subject: str) -> str:
    """Why a date in a gap is outside the contract, naming the end before it and the start after it."""
    return (
        f"{subject} {format_contract_date(value)}, when no contract runs: the contract ended on "
        f"{format_contract_date(gap.first_day - timedelta(days=1))}, and extension "
        f"{gap.extension_sequence_no} starts on {format_contract_date(day_after(gap.last_day))}."
    )


def date_outside_contract_message(
    value: date,
    *,
    contract_start: date | None,
    contract_end: date | None,
    subject: str,
    gaps: tuple[ContractGap, ...] | list[ContractGap] = (),
) -> str | None:
    """Why `value` is outside the contract, naming both dates, or None when it is not outside.

    `subject` names what the date belongs to, as the sentence's opening - for example
    "This period starts on" or "Line 2 starts on" - so the message reads as one sentence.
    """
    outcome = classify_date_against_contract(
        value, contract_start=contract_start, contract_end=contract_end, gaps=gaps
    )
    if outcome == CONTRACT_DATE_IN_GAP:
        gap = gap_containing(value, gaps)
        assert gap is not None  # IN_GAP is only returned when a gap contains the date
        return gap_message(value, gap, subject=subject)
    if outcome == CONTRACT_DATE_BEFORE_START and contract_start is not None:
        return (
            f"{subject} {format_contract_date(value)}, "
            f"before the contract starts on {format_contract_date(contract_start)}."
        )
    if outcome == CONTRACT_DATE_AFTER_END and contract_end is not None:
        return (
            f"{subject} {format_contract_date(value)}, "
            f"after the contract ends on {format_contract_date(contract_end)}."
        )
    return None


def contract_start_conflict_message(new_start: date, *, blocking_date: date, blocking_subject: str) -> str:
    """The contract start cannot move past something already recorded earlier (owner decision 17)."""
    return (
        f"The contract cannot start on {format_contract_date(new_start)}, "
        f"because {blocking_subject} {format_contract_date(blocking_date)}."
    )


def contract_end_conflict_message(new_end: date, *, blocking_date: date, blocking_subject: str) -> str:
    """The contract end cannot move before something already recorded later (owner decision 17).

    The example the owner gave: "The contract cannot end on 1 February 2027, because this line has
    terms starting 1 March 2027" - with the line named, so the user knows which one to look at.
    """
    return (
        f"The contract cannot end on {format_contract_date(new_end)}, "
        f"because {blocking_subject} {format_contract_date(blocking_date)}."
    )


# --- The contract's current state --------------------------------------------------------------------

CONTRACT_STATE_NOT_RECORDED = "NOT_RECORDED"
CONTRACT_STATE_NOT_STARTED = "NOT_STARTED"
CONTRACT_STATE_ACTIVE = "ACTIVE"
CONTRACT_STATE_ENDED = "ENDED"
# Today falls in a gap before an extension (owner's clarification, 22 September 2026).
CONTRACT_STATE_BETWEEN_EXTENSIONS = "BETWEEN_EXTENSIONS"
CONTRACT_STATE_CODES = (
    CONTRACT_STATE_NOT_RECORDED,
    CONTRACT_STATE_NOT_STARTED,
    CONTRACT_STATE_ACTIVE,
    CONTRACT_STATE_ENDED,
    CONTRACT_STATE_BETWEEN_EXTENSIONS,
)

# How the end date was answered. Null means not answered yet and is reported missing; UNTIL_WORK_COMPLETE
# is a recorded answer, exactly as NONE is for a billing term (owner decision 14).
CONTRACT_END_BASIS_FIXED_DATE = "FIXED_DATE"
CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE = "UNTIL_WORK_COMPLETE"
CONTRACT_END_BASIS_CODES = (CONTRACT_END_BASIS_FIXED_DATE, CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE)


@dataclass(frozen=True)
class ContractState:
    state_code: str
    state_label: str
    days_until_start: int | None
    days_until_end: int | None


def _days_away(value: date, today: date) -> str:
    days = (value - today).days
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    return f"in {days} days"


def contract_state(
    *,
    contract_start: date | None,
    contract_end: date | None,
    contract_end_basis_code: str | None,
    today: date,
    gaps: tuple[ContractGap, ...] | list[ContractGap] = (),
) -> ContractState:
    """Not started, active, ends in N days, or ended (owner decision 17), with the days it is away.

    Where the start date is not recorded the state is NOT_RECORDED even if an end date is - whether
    the contract has begun is not knowable, and saying "Active" would be a guess. The one exception
    is an end date already in the past: that contract is over whatever its start was.

    A day in a gap before an extension is BETWEEN_EXTENSIONS, not ACTIVE: no contract runs that day.
    """
    if contract_start is None and contract_end is None and contract_end_basis_code is None:
        return ContractState(CONTRACT_STATE_NOT_RECORDED, "Contract dates not recorded", None, None)

    if contract_end is not None and contract_end < today:
        return ContractState(
            CONTRACT_STATE_ENDED,
            f"Ended on {format_contract_date(contract_end)}",
            None if contract_start is None else (contract_start - today).days,
            (contract_end - today).days,
        )

    if contract_start is None:
        return ContractState(
            CONTRACT_STATE_NOT_RECORDED,
            "Contract start date not recorded",
            None,
            None if contract_end is None else (contract_end - today).days,
        )

    days_until_start = (contract_start - today).days
    days_until_end = None if contract_end is None else (contract_end - today).days

    if contract_start > today:
        return ContractState(
            CONTRACT_STATE_NOT_STARTED,
            f"Starts {_days_away(contract_start, today)}, on {format_contract_date(contract_start)}",
            days_until_start,
            days_until_end,
        )

    gap = gap_containing(today, gaps)
    if gap is not None:
        resumes = day_after(gap.last_day)
        return ContractState(
            CONTRACT_STATE_BETWEEN_EXTENSIONS,
            f"Not running: extension {gap.extension_sequence_no} starts {_days_away(resumes, today)}, "
            f"on {format_contract_date(resumes)}",
            days_until_start,
            days_until_end,
        )

    if contract_end is not None:
        return ContractState(
            CONTRACT_STATE_ACTIVE,
            f"Active, ends {_days_away(contract_end, today)}, on {format_contract_date(contract_end)}",
            days_until_start,
            days_until_end,
        )
    if contract_end_basis_code == CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE:
        return ContractState(
            CONTRACT_STATE_ACTIVE, "Active, until the work is complete", days_until_start, None
        )
    return ContractState(CONTRACT_STATE_ACTIVE, "Active, no end date recorded", days_until_start, None)
