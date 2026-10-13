"""Slice 7D Part 3 - the contract-period rules, tested without a database.

`app.modules.work_orders.contract_period_rules` has no database, no clock and no I/O, so every case
can be stated directly. That is why owner decision 17 asks for the rule to be "built and tested now,
for log sheets, release and billing to use later": those slices will call
`classify_date_against_contract`, and what it answers for a half-recorded contract has to be settled
before they do, not guessed at then.

The API tests that use these rules through real routes are in
test_slice_7d_part_3_contract_period.py.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.modules.work_orders.contract_period_rules import (
    CONTRACT_DATE_AFTER_END,
    CONTRACT_DATE_BEFORE_START,
    CONTRACT_DATE_IN_GAP,
    CONTRACT_DATE_NOT_DETERMINED,
    CONTRACT_DATE_OUTSIDE_OUTCOMES,
    CONTRACT_DATE_WITHIN,
    CONTRACT_END_BASIS_FIXED_DATE,
    CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE,
    CONTRACT_STATE_ACTIVE,
    CONTRACT_STATE_BETWEEN_EXTENSIONS,
    CONTRACT_STATE_ENDED,
    CONTRACT_STATE_NOT_RECORDED,
    CONTRACT_STATE_NOT_STARTED,
    classify_date_against_contract,
    contract_end_conflict_message,
    contract_start_conflict_message,
    contract_state,
    date_is_outside_contract,
    date_outside_contract_message,
    describe_contract_period,
    format_contract_date,
    gap_before_extension,
)

START = date(2027, 1, 1)
END = date(2027, 3, 31)


def _classify(value: date, start: date | None = START, end: date | None = END) -> str:
    return classify_date_against_contract(value, contract_start=start, contract_end=end)


# --- Is this date inside the contract? ------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        (date(2026, 12, 31), CONTRACT_DATE_BEFORE_START),
        (START, CONTRACT_DATE_WITHIN),
        (date(2027, 2, 14), CONTRACT_DATE_WITHIN),
        (END, CONTRACT_DATE_WITHIN),
        (date(2027, 4, 1), CONTRACT_DATE_AFTER_END),
    ],
)
def test_a_date_is_classified_against_a_fully_recorded_contract(value: date, expected: str) -> None:
    assert _classify(value) == expected


def test_both_bounds_are_inclusive_so_the_first_and_last_day_are_inside() -> None:
    """Work on the day the contract starts, and on the day it ends, is work under the contract."""
    assert _classify(START) == CONTRACT_DATE_WITHIN
    assert _classify(END) == CONTRACT_DATE_WITHIN


def test_a_date_before_a_known_start_is_outside_even_when_the_end_is_not_recorded() -> None:
    """A bound that is recorded can be broken whatever the other one says."""
    assert _classify(date(2026, 12, 31), end=None) == CONTRACT_DATE_BEFORE_START


def test_a_date_after_a_known_end_is_outside_even_when_the_start_is_not_recorded() -> None:
    assert _classify(date(2027, 4, 1), start=None) == CONTRACT_DATE_AFTER_END


@pytest.mark.parametrize(
    "start, end",
    [(None, END), (START, None), (None, None)],
)
def test_a_date_breaking_no_recorded_bound_is_not_determined_when_a_bound_is_missing(
    start: date | None, end: date | None
) -> None:
    """The heart of the rule: "we do not know" is not "yes".

    A later caller that read WITHIN here would bill or release a day against a contract nobody has
    recorded, which is the same mistake WBT-001 forbids for a missing term.
    """
    assert classify_date_against_contract(date(2027, 2, 14), contract_start=start, contract_end=end) == (
        CONTRACT_DATE_NOT_DETERMINED
    )


def test_not_determined_is_not_a_refusal() -> None:
    assert CONTRACT_DATE_NOT_DETERMINED not in CONTRACT_DATE_OUTSIDE_OUTCOMES
    assert CONTRACT_DATE_WITHIN not in CONTRACT_DATE_OUTSIDE_OUTCOMES
    assert not date_is_outside_contract(date(2027, 2, 14), contract_start=None, contract_end=None)
    assert date_is_outside_contract(date(2027, 4, 1), contract_start=START, contract_end=END)


def test_a_one_day_contract_contains_only_its_own_day() -> None:
    day = date(2027, 5, 5)
    assert classify_date_against_contract(day, contract_start=day, contract_end=day) == CONTRACT_DATE_WITHIN
    assert classify_date_against_contract(
        date(2027, 5, 6), contract_start=day, contract_end=day
    ) == CONTRACT_DATE_AFTER_END


# --- Wording --------------------------------------------------------------------------------------


def test_a_date_reads_the_way_the_owners_own_example_writes_it() -> None:
    """Owner decision 17's examples are "1 May 2027" and "31 March 2027" - no leading zero."""
    assert format_contract_date(date(2027, 5, 1)) == "1 May 2027"
    assert format_contract_date(date(2027, 3, 31)) == "31 March 2027"


def test_the_refusal_names_both_dates() -> None:
    message = date_outside_contract_message(
        date(2027, 5, 1), contract_start=START, contract_end=END, subject="This period starts on"
    )
    assert message == "This period starts on 1 May 2027, after the contract ends on 31 March 2027."


def test_the_refusal_names_the_start_when_the_date_falls_before_it() -> None:
    message = date_outside_contract_message(
        date(2026, 12, 1), contract_start=START, contract_end=END, subject="This line starts on"
    )
    assert message == "This line starts on 1 December 2026, before the contract starts on 1 January 2027."


def test_there_is_no_refusal_for_a_date_that_is_inside_or_not_determined() -> None:
    assert (
        date_outside_contract_message(
            date(2027, 2, 1), contract_start=START, contract_end=END, subject="This period starts on"
        )
        is None
    )
    assert (
        date_outside_contract_message(
            date(2027, 2, 1), contract_start=None, contract_end=None, subject="This period starts on"
        )
        is None
    )


def test_the_contract_side_refusals_read_as_the_owner_wrote_them() -> None:
    """Owner decision 17: "The contract cannot end on 1 February 2027, because this line has terms
    starting 1 March 2027" - with the line named, so the user knows which one to look at."""
    assert contract_end_conflict_message(
        date(2027, 2, 1), blocking_date=date(2027, 3, 1), blocking_subject="line 2 has terms starting"
    ) == "The contract cannot end on 1 February 2027, because line 2 has terms starting 1 March 2027."
    assert contract_start_conflict_message(
        date(2027, 2, 1), blocking_date=date(2027, 1, 1), blocking_subject="line 2 has terms starting"
    ) == "The contract cannot start on 1 February 2027, because line 2 has terms starting 1 January 2027."


@pytest.mark.parametrize(
    "start, end, expected",
    [
        (START, END, "1 January 2027 to 31 March 2027"),
        (START, None, "from 1 January 2027"),
        (None, END, "until 31 March 2027"),
        (None, None, "not recorded"),
    ],
)
def test_a_contract_period_describes_itself_by_what_is_recorded(
    start: date | None, end: date | None, expected: str
) -> None:
    assert describe_contract_period(start, end) == expected


# --- The contract's state today -------------------------------------------------------------------


def _state(start, end, basis, today=date(2027, 2, 1)):
    return contract_state(
        contract_start=start, contract_end=end, contract_end_basis_code=basis, today=today
    )


def test_nothing_recorded_reads_as_nothing_recorded() -> None:
    state = _state(None, None, None)
    assert state.state_code == CONTRACT_STATE_NOT_RECORDED
    assert state.state_label == "Contract dates not recorded"
    assert state.days_until_start is None and state.days_until_end is None


def test_a_contract_that_has_not_begun_says_when_it_starts() -> None:
    state = _state(date(2027, 3, 1), date(2027, 6, 30), CONTRACT_END_BASIS_FIXED_DATE)
    assert state.state_code == CONTRACT_STATE_NOT_STARTED
    assert state.state_label == "Starts in 28 days, on 1 March 2027"
    assert state.days_until_start == 28


def test_a_running_contract_says_how_far_off_its_end_is() -> None:
    """Owner decision 17's "ends in N days"."""
    state = _state(START, date(2027, 2, 13), CONTRACT_END_BASIS_FIXED_DATE)
    assert state.state_code == CONTRACT_STATE_ACTIVE
    assert state.state_label == "Active, ends in 12 days, on 13 February 2027"
    assert state.days_until_end == 12


@pytest.mark.parametrize(
    "end, expected",
    [
        (date(2027, 2, 1), "Active, ends today, on 1 February 2027"),
        (date(2027, 2, 2), "Active, ends tomorrow, on 2 February 2027"),
    ],
)
def test_the_last_day_and_the_day_before_it_read_as_words_not_as_a_count(end: date, expected: str) -> None:
    assert _state(START, end, CONTRACT_END_BASIS_FIXED_DATE).state_label == expected


def test_a_contract_still_running_on_its_last_day_has_not_ended() -> None:
    assert _state(START, date(2027, 2, 1), CONTRACT_END_BASIS_FIXED_DATE).state_code == CONTRACT_STATE_ACTIVE


def test_a_contract_whose_end_has_passed_reads_as_ended() -> None:
    state = _state(START, date(2027, 1, 31), CONTRACT_END_BASIS_FIXED_DATE)
    assert state.state_code == CONTRACT_STATE_ENDED
    assert state.state_label == "Ended on 31 January 2027"


def test_an_ended_contract_reads_as_ended_even_with_no_start_recorded() -> None:
    """An end date in the past settles it whatever the start was."""
    assert _state(None, date(2027, 1, 31), CONTRACT_END_BASIS_FIXED_DATE).state_code == CONTRACT_STATE_ENDED


def test_until_the_work_is_complete_is_active_and_says_so() -> None:
    state = _state(START, None, CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE)
    assert state.state_code == CONTRACT_STATE_ACTIVE
    assert state.state_label == "Active, until the work is complete"
    assert state.days_until_end is None


def test_a_start_with_no_end_answered_at_all_is_active_but_says_the_end_is_not_recorded() -> None:
    """Different from "until the work is complete", which is an answer (owner decision 14)."""
    state = _state(START, None, None)
    assert state.state_code == CONTRACT_STATE_ACTIVE
    assert state.state_label == "Active, no end date recorded"


def test_an_end_recorded_without_a_start_cannot_claim_the_contract_is_running() -> None:
    """Whether it has begun is not knowable, so it says what is missing rather than guessing."""
    state = _state(None, date(2027, 6, 30), CONTRACT_END_BASIS_FIXED_DATE)
    assert state.state_code == CONTRACT_STATE_NOT_RECORDED
    assert state.state_label == "Contract start date not recorded"


def test_a_contract_starting_today_is_active_not_pending() -> None:
    today = date(2027, 2, 1)
    assert _state(today, date(2027, 6, 30), CONTRACT_END_BASIS_FIXED_DATE, today=today).state_code == (
        CONTRACT_STATE_ACTIVE
    )


def test_a_contract_starting_tomorrow_says_tomorrow() -> None:
    state = _state(date(2027, 2, 2), None, CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE)
    assert state.state_code == CONTRACT_STATE_NOT_STARTED
    assert state.state_label == "Starts tomorrow, on 2 February 2027"


# --- An extension that starts later than the day after (owner, 22 September 2026) ---------------------

OLD_END = date(2027, 12, 31)
LATER_START = date(2028, 1, 15)
NEW_END = date(2028, 6, 30)


def _gap():
    return gap_before_extension(previous_end=OLD_END, extension_start=LATER_START, extension_sequence_no=1)


def test_an_extension_starting_the_day_after_leaves_no_gap() -> None:
    assert gap_before_extension(previous_end=OLD_END, extension_start=date(2028, 1, 1), extension_sequence_no=1) is None


def test_an_extension_with_no_fixed_end_to_follow_leaves_no_gap() -> None:
    assert gap_before_extension(previous_end=None, extension_start=None, extension_sequence_no=1) is None


def test_a_later_start_leaves_a_gap_from_the_day_after_to_the_day_before() -> None:
    gap = _gap()
    assert (gap.first_day, gap.last_day, gap.extension_sequence_no) == (date(2028, 1, 1), date(2028, 1, 14), 1)


@pytest.mark.parametrize(
    "value, expected",
    [
        (OLD_END, CONTRACT_DATE_WITHIN),
        (date(2028, 1, 1), CONTRACT_DATE_IN_GAP),
        (date(2028, 1, 14), CONTRACT_DATE_IN_GAP),
        (LATER_START, CONTRACT_DATE_WITHIN),
        (NEW_END, CONTRACT_DATE_WITHIN),
    ],
)
def test_a_gaps_days_are_outside_the_contract_and_both_its_edges_are_exact(value, expected) -> None:
    """Owner: the days in between are outside the contract."""
    assert (
        classify_date_against_contract(value, contract_start=START, contract_end=NEW_END, gaps=(_gap(),))
        == expected
    )


def test_a_gap_is_outside_even_while_the_start_is_not_recorded() -> None:
    """A gap is made only of recorded dates, so it is knowable when the start is not."""
    assert (
        classify_date_against_contract(date(2028, 1, 5), contract_start=None, contract_end=NEW_END, gaps=(_gap(),))
        == CONTRACT_DATE_IN_GAP
    )
    assert CONTRACT_DATE_IN_GAP in CONTRACT_DATE_OUTSIDE_OUTCOMES
    assert date_is_outside_contract(date(2028, 1, 5), contract_start=None, contract_end=NEW_END, gaps=(_gap(),))


def test_a_date_in_a_gap_is_refused_naming_the_end_before_it_and_the_start_after_it() -> None:
    assert date_outside_contract_message(
        date(2028, 1, 5), contract_start=START, contract_end=NEW_END, subject="This period starts on", gaps=(_gap(),)
    ) == (
        "This period starts on 5 January 2028, when no contract runs: the contract ended on 31 December 2027, "
        "and extension 1 starts on 15 January 2028."
    )


def test_a_day_in_a_gap_reads_as_not_running_rather_than_active() -> None:
    state = contract_state(
        contract_start=START,
        contract_end=NEW_END,
        contract_end_basis_code=CONTRACT_END_BASIS_FIXED_DATE,
        today=date(2028, 1, 5),
        gaps=(_gap(),),
    )
    assert state.state_code == CONTRACT_STATE_BETWEEN_EXTENSIONS
    assert state.state_label == "Not running: extension 1 starts in 10 days, on 15 January 2028"


def test_the_day_the_extension_starts_is_active_again() -> None:
    state = contract_state(
        contract_start=START,
        contract_end=NEW_END,
        contract_end_basis_code=CONTRACT_END_BASIS_FIXED_DATE,
        today=LATER_START,
        gaps=(_gap(),),
    )
    assert state.state_code == CONTRACT_STATE_ACTIVE
