"""ELG-2 - certificate reminders and escalation, pure (backend/app/modules/eligibility/reminders.py).

docs/agent/slices/elg-2-certificate-reminders.md, sections 5 and 14's first list: the reminder days a schedule
gives, the day a reminder began and the flag at once, the steps of a path reached, each date and reason, which
reminder an outcome raises, and every refusal of a setting. No database: every record is built in the test.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.modules.eligibility import evaluation as ev
from app.modules.eligibility import reminders as rm
from app.modules.eligibility.contract import (
    OUTCOME_COPY_MISSING,
    OUTCOME_MISSING,
    OUTCOME_NOT_APPLICABLE,
    OUTCOME_RUN_OUT,
    OUTCOME_RUNS_OUT_BEFORE_START,
    OUTCOME_RUNS_OUT_IN_PERIOD,
    OUTCOME_RUNS_OUT_SOON,
    OUTCOME_VALID,
    REASON_ADDED,
    REASON_COPY_MISSING,
    REASON_MARK_ENDS,
    REASON_MARK_WITHDRAWN,
    REASON_RULE,
    REASON_RUNS_OUT,
    REASON_TRANSPORT,
    REMINDER_BEFORE_JOB,
    REMINDER_DURING_JOB,
    REMINDER_NOT_YET_RECORDED,
    REMINDER_RUNNING_OUT,
)
from tests.test_elg1_evaluation import CRAWLER, FIRST_DAY, cert, crane_unit, evidence, mark, rule

D = date(2026, 11, 30)
LONG_AGO = date(2025, 1, 1)
STANDARD = rm.ordered_bands([rm.Band(60, 30), rm.Band(15, 7), rm.Band(7, 1), rm.Band(0, 1)])
NOT_YET = (rm.Band(0, 1),)
ROLES = {"ADMIN", "OPERATIONS_USER", "MANAGEMENT_READ_ONLY", "SALES_USER", "FINANCE_USER", "SALES_MANAGER"}


def step(role: str, days: int | None = None) -> rm.Step:
    if days is None:
        return rm.Step(role, "FIRST_REMINDER", None, ("SCREEN",))
    return rm.Step(role, "DAYS_BEFORE", days, ("SCREEN",))


RUNNING_OUT_PATH = (step("ADMIN"), step("OPERATIONS_USER", 15), step("MANAGEMENT_READ_ONLY", 7))
ALLOCATION_PATH = (step("ADMIN"), step("OPERATIONS_USER"), step("MANAGEMENT_READ_ONLY", 7))
NOT_YET_PATH = (step("ADMIN"), step("OPERATIONS_USER", -7), step("MANAGEMENT_READ_ONLY", -14))


def reminder_days_seen(bands, *, date_on: date, began_on: date, days: range) -> list[int]:
    """The days-before on which a new reminder day came, walking today across `days` (days-before, descending)."""
    seen = []
    for before in days:
        today = date_on - timedelta(days=before)
        found = rm.reminder_days(bands, date_on=date_on, began_on=began_on, today=today)
        if found is not None and found.current_on == today:
            seen.append(before)
    return seen


# --- Reminder days (section 5.3) -------------------------------------------------------------------------------


def test_the_standard_schedule_reminds_60_30_15_8_then_daily_and_after():
    assert reminder_days_seen(STANDARD, date_on=D, began_on=LONG_AGO, days=range(70, -4, -1)) == [
        60, 30, 15, 8, 7, 6, 5, 4, 3, 2, 1, 0, -1, -2, -3,
    ]


def test_nothing_is_shown_before_the_first_reminder_day():
    assert rm.reminder_days(STANDARD, date_on=D, began_on=LONG_AGO, today=D - timedelta(days=61)) is None


@pytest.mark.parametrize(
    "before, so_far, current_before",
    [(60, 1, 60), (31, 1, 60), (30, 2, 30), (16, 2, 30), (15, 3, 15), (8, 4, 8), (7, 5, 7), (1, 11, 1), (0, 12, 0), (-10, 22, -10)],
)
def test_the_current_reminder_day_and_how_many_so_far(before, so_far, current_before):
    found = rm.reminder_days(STANDARD, date_on=D, began_on=LONG_AGO, today=D - timedelta(days=before))
    assert found is not None
    assert found.so_far == so_far
    assert found.current_on == D - timedelta(days=current_before)
    assert found.first_on == D - timedelta(days=60)


def test_a_reminder_beginning_inside_the_schedule_is_flagged_that_day_and_earlier_days_do_not_count():
    began = D - timedelta(days=20)
    on_the_day = rm.reminder_days(STANDARD, date_on=D, began_on=began, today=began)
    assert on_the_day == rm.Days(first_on=began, current_on=began, so_far=1)
    # 60 and 30 days before came before it began: only the flag, then 15, 8, 7 ...
    later = rm.reminder_days(STANDARD, date_on=D, began_on=began, today=D - timedelta(days=7))
    assert later == rm.Days(first_on=began, current_on=D - timedelta(days=7), so_far=4)


def test_a_reminder_beginning_on_a_reminder_day_is_counted_once():
    began = D - timedelta(days=15)
    assert rm.reminder_days(STANDARD, date_on=D, began_on=began, today=began) == rm.Days(began, began, 1)


def test_a_reminder_beginning_before_the_schedule_is_not_flagged():
    began = D - timedelta(days=100)
    assert rm.reminder_days(STANDARD, date_on=D, began_on=began, today=began) is None
    first = rm.reminder_days(STANDARD, date_on=D, began_on=began, today=D - timedelta(days=60))
    assert first == rm.Days(D - timedelta(days=60), D - timedelta(days=60), 1)


def test_a_reminder_dated_before_it_began_starts_on_the_day_it_began_and_runs_on():
    # A certificate run out before the allocation was recorded: flagged the day it is allocated, then every day.
    began = D + timedelta(days=10)
    assert rm.reminder_days(STANDARD, date_on=D, began_on=began, today=began) == rm.Days(began, began, 1)
    assert rm.reminder_days(STANDARD, date_on=D, began_on=began, today=began + timedelta(days=3)) == rm.Days(began, began + timedelta(days=3), 4)


def test_a_weekly_last_band_keeps_its_rhythm_after_the_date():
    bands = rm.ordered_bands([rm.Band(30, 10), rm.Band(0, 7)])
    assert reminder_days_seen(bands, date_on=D, began_on=LONG_AGO, days=range(35, -16, -1)) == [30, 20, 10, 0, -7, -14]


def test_a_band_may_start_after_the_date():
    bands = rm.ordered_bands([rm.Band(10, 5), rm.Band(-5, 1)])
    assert reminder_days_seen(bands, date_on=D, began_on=LONG_AGO, days=range(12, -8, -1)) == [10, 5, 0, -5, -6, -7]
    assert rm.reminder_days(bands, date_on=D, began_on=LONG_AGO, today=D + timedelta(days=4)).current_on == D


def test_not_yet_recorded_reminds_every_day_from_the_day_it_became_needed():
    added = date(2026, 10, 3)
    assert rm.reminder_days(NOT_YET, date_on=added, began_on=added, today=added - timedelta(days=1)) is None
    assert rm.reminder_days(NOT_YET, date_on=added, began_on=added, today=added) == rm.Days(added, added, 1)
    assert rm.reminder_days(NOT_YET, date_on=added, began_on=added, today=added + timedelta(days=9)).so_far == 10


# --- The path (section 5.4) ------------------------------------------------------------------------------------


def roles_reached(steps, *, first_on, date_on, today) -> dict[str, date]:
    return {item.step.role_code: item.reached_on for item in rm.reached_steps(steps, first_on=first_on, date_on=date_on, today=today)}


def test_the_running_out_path_reaches_more_people_as_the_date_comes_nearer():
    first = D - timedelta(days=60)
    assert roles_reached(RUNNING_OUT_PATH, first_on=first, date_on=D, today=D - timedelta(days=20)) == {"ADMIN": first}
    assert roles_reached(RUNNING_OUT_PATH, first_on=first, date_on=D, today=D - timedelta(days=15)) == {
        "ADMIN": first,
        "OPERATIONS_USER": D - timedelta(days=15),
    }
    assert set(roles_reached(RUNNING_OUT_PATH, first_on=first, date_on=D, today=D - timedelta(days=7))) == {
        "ADMIN", "OPERATIONS_USER", "MANAGEMENT_READ_ONLY",
    }
    # Nobody drops off after the date.
    assert set(roles_reached(RUNNING_OUT_PATH, first_on=first, date_on=D, today=D + timedelta(days=30))) == {
        "ADMIN", "OPERATIONS_USER", "MANAGEMENT_READ_ONLY",
    }


def test_a_step_is_reached_no_earlier_than_the_first_reminder():
    # Allocated 10 days before: Operations "from 15 days before" is reached the day the reminder began.
    first = D - timedelta(days=10)
    assert roles_reached(RUNNING_OUT_PATH, first_on=first, date_on=D, today=first) == {"ADMIN": first, "OPERATIONS_USER": first}


def test_operations_is_reached_at_once_on_an_allocation_reminder():
    first = D - timedelta(days=20)
    assert roles_reached(ALLOCATION_PATH, first_on=first, date_on=D, today=first) == {"ADMIN": first, "OPERATIONS_USER": first}


def test_papers_not_yet_entered_reach_operations_after_7_days_and_management_after_14():
    added = date(2026, 10, 3)
    assert roles_reached(NOT_YET_PATH, first_on=added, date_on=added, today=added) == {"ADMIN": added}
    assert roles_reached(NOT_YET_PATH, first_on=added, date_on=added, today=added + timedelta(days=6)) == {"ADMIN": added}
    assert roles_reached(NOT_YET_PATH, first_on=added, date_on=added, today=added + timedelta(days=7)) == {
        "ADMIN": added,
        "OPERATIONS_USER": added + timedelta(days=7),
    }
    assert roles_reached(NOT_YET_PATH, first_on=added, date_on=added, today=added + timedelta(days=14))["MANAGEMENT_READ_ONLY"] == added + timedelta(days=14)


# --- A reminder's date and reason (section 5.2) ----------------------------------------------------------------


def missing(kind: str, the_rule: ev.Rule, *, certificate: ev.Certificate | None = None, outcome: str = OUTCOME_MISSING) -> ev.Result:
    return ev.Result("crane", kind, the_rule, certificate, None, outcome, "BLOCK", None)


def date_of(result: ev.Result, rules, *, certificates=(), marks=(), added: date = date(2026, 3, 1), today: date = date(2026, 10, 1)):
    return rm.reminder_date(result, evidence(rules, certificates, marks), assets=("crane", "carrier"), added_on=added, today=today)


def test_a_cover_running_out_is_dated_by_its_last_day():
    insurance = rule("INSURANCE")
    result = ev.Result("crane", "INSURANCE", insurance, cert("INSURANCE"), None, OUTCOME_VALID, "NONE", D)
    assert date_of(result, [insurance]) == rm.Dated(D, REASON_RUNS_OUT)


def test_a_mark_ending_is_dated_by_its_last_day():
    road_tax = rule("ROAD_TAX", not_applicable="ALLOWED")
    result = ev.Result("crane", "ROAD_TAX", road_tax, None, mark("ROAD_TAX", until=D), OUTCOME_NOT_APPLICABLE, "NONE", D)
    assert date_of(result, [road_tax]) == rm.Dated(D, REASON_MARK_ENDS)


def test_a_certificate_with_no_end_has_no_reminder():
    road_tax = rule("ROAD_TAX")
    result = ev.Result("crane", "ROAD_TAX", road_tax, cert("ROAD_TAX", until=None), None, OUTCOME_VALID, "NONE", None)
    assert date_of(result, [road_tax]) is None


def test_never_recorded_on_a_machine_added_after_the_rule_is_dated_by_the_day_it_was_added():
    insurance = rule("INSURANCE")
    assert date_of(missing("INSURANCE", insurance), [insurance], added=date(2026, 9, 3)) == rm.Dated(date(2026, 9, 3), REASON_ADDED)


def test_never_recorded_because_a_rule_took_effect_later_is_dated_by_the_rules_start_even_before_it_was_entered():
    new_rule = rule("INSURANCE", start=date(2026, 6, 1))
    assert date_of(missing("INSURANCE", new_rule), [new_rule], added=date(2026, 3, 1)) == rm.Dated(date(2026, 6, 1), REASON_RULE)


def test_a_rule_replaced_by_its_successor_does_not_make_the_certificate_newly_needed():
    first = rule("INSURANCE", start=FIRST_DAY, end=date(2026, 5, 31))
    second = rule("INSURANCE", start=date(2026, 6, 1))
    assert rm.requirement_began(second, [first, second]) == FIRST_DAY
    assert date_of(missing("INSURANCE", second), [first, second], added=date(2026, 3, 1)) == rm.Dated(date(2026, 3, 1), REASON_ADDED)
    # A gap between them is a new start.
    gapped = rule("INSURANCE", start=date(2026, 6, 10))
    assert rm.requirement_began(gapped, [first, gapped]) == date(2026, 6, 10)


def test_fitness_for_a_job_is_dated_by_a_transport_registration_taking_effect_by_the_jobs_rule_day():
    # ELG2-R2-003: a registration saying transport takes effect on 1 November; the job's rules are chosen for 15
    # November, so fitness is needed for it, from 1 November - as the check decides it.
    fitness = rule("FITNESS", applies="TRANSPORT_ONLY")
    registration = cert("REGISTRATION", asset="carrier", start=date(2026, 11, 1), until=date(2030, 1, 1), registered_as="TRANSPORT")
    result = missing("FITNESS", fitness)
    proof = evidence([fitness], [registration])
    for_job = rm.reminder_date(result, proof, assets=("crane", "carrier"), added_on=date(2026, 3, 1), today=date(2026, 10, 1), rule_day=date(2026, 11, 15))
    assert for_job == rm.Dated(date(2026, 11, 1), REASON_TRANSPORT)
    # Today alone, the registration is not yet in force: the date comes from the machine being added.
    assert rm.reminder_date(result, proof, assets=("crane", "carrier"), added_on=date(2026, 3, 1), today=date(2026, 10, 1)) == rm.Dated(date(2026, 3, 1), REASON_ADDED)


def test_fitness_needed_under_a_transport_registration_that_has_run_out_is_dated_by_that_registration():
    # A transport registration run out still says the machine is a transport vehicle (the owner's rule, 1 October
    # 2026): fitness never recorded is dated by its start. A non-transport one standing decides instead.
    fitness = rule("FITNESS", applies="TRANSPORT_ONLY")
    ran_out = cert("REGISTRATION", asset="carrier", start=date(2026, 5, 1), until=date(2026, 9, 1), registered_as="TRANSPORT")
    assert date_of(missing("FITNESS", fitness), [fitness], certificates=[ran_out]) == rm.Dated(date(2026, 5, 1), REASON_TRANSPORT)
    plain = cert("REGISTRATION", asset="carrier", start=date(2026, 9, 2), until=date(2031, 9, 1), registered_as="NON_TRANSPORT")
    assert rm.transport_since(evidence([fitness], [ran_out, plain]), ("crane", "carrier"), (date(2026, 10, 1),)) is None


def test_fitness_never_recorded_is_dated_by_the_transport_registration():
    fitness = rule("FITNESS", applies="TRANSPORT_ONLY")
    registration = cert("REGISTRATION", asset="carrier", start=date(2026, 7, 1), until=date(2030, 1, 1), registered_as="TRANSPORT")
    assert date_of(missing("FITNESS", fitness), [fitness], certificates=[registration]) == rm.Dated(date(2026, 7, 1), REASON_TRANSPORT)


def test_a_mark_that_ended_dates_the_certificate_needed_again_by_its_last_day():
    road_tax = rule("ROAD_TAX", not_applicable="ALLOWED")
    ended = mark("ROAD_TAX", until=date(2026, 9, 20), recorded=date(2026, 4, 1))
    assert date_of(missing("ROAD_TAX", road_tax), [road_tax], marks=[ended]) == rm.Dated(date(2026, 9, 20), REASON_MARK_ENDS)


def test_a_mark_withdrawn_dates_the_certificate_needed_again_by_the_day_it_was_withdrawn():
    road_tax = rule("ROAD_TAX", not_applicable="ALLOWED")
    withdrawn = ev.Mark(9001, "mark-9001", "crane", "ROAD_TAX", None, date(2026, 4, 1), True, date(2026, 9, 25))
    assert date_of(missing("ROAD_TAX", road_tax), [road_tax], marks=[withdrawn]) == rm.Dated(date(2026, 9, 25), REASON_MARK_WITHDRAWN)


def test_a_baseline_mark_never_dates_a_certificate_a_states_rule_allowing_no_mark_needs():
    # ELG2-R3-002: road tax marked not applicable under the baseline, which allows it, until 20 September. At a site
    # whose state's rule allows no mark, the mark never covered the job's requirement: its end is not the date.
    baseline = rule("ROAD_TAX", not_applicable="ALLOWED")
    state = rule("ROAD_TAX", jurisdiction="IN-GJ")
    ended = mark("ROAD_TAX", until=date(2026, 9, 20), recorded=date(2026, 4, 1))
    assert date_of(missing("ROAD_TAX", baseline), [baseline, state], marks=[ended]) == rm.Dated(date(2026, 9, 20), REASON_MARK_ENDS)
    assert date_of(missing("ROAD_TAX", state), [baseline, state], marks=[ended]) == rm.Dated(date(2026, 3, 1), REASON_ADDED)


def test_a_mark_longer_than_the_rule_lets_one_stand_never_dates_a_certificate():
    # Marks may stand for six months at most: one recorded for a year never stood; one within the six months did.
    limited = rule("ROAD_TAX", not_applicable="ALLOWED", max_months=6)
    too_long = mark("ROAD_TAX", until=date(2026, 9, 20), recorded=date(2025, 9, 1))
    within = mark("ROAD_TAX", until=date(2026, 9, 10), recorded=date(2026, 4, 1))
    assert date_of(missing("ROAD_TAX", limited), [limited], marks=[too_long]) == rm.Dated(date(2026, 3, 1), REASON_ADDED)
    assert date_of(missing("ROAD_TAX", limited), [limited], marks=[too_long, within]) == rm.Dated(date(2026, 9, 10), REASON_MARK_ENDS)


def test_a_mark_is_judged_by_the_rule_in_force_on_the_day_it_stopped():
    # No mark allowed until 31 May; from 1 June, a successor allowing one. A mark that ended in May never stood; one
    # that ended in September did.
    before = rule("ROAD_TAX", end=date(2026, 5, 31))
    after = rule("ROAD_TAX", start=date(2026, 6, 1), not_applicable="ALLOWED")
    in_may = mark("ROAD_TAX", until=date(2026, 5, 20), recorded=date(2026, 4, 1))
    in_september = mark("ROAD_TAX", until=date(2026, 9, 20), recorded=date(2026, 6, 5))
    assert date_of(missing("ROAD_TAX", after), [before, after], marks=[in_may]) == rm.Dated(date(2026, 3, 1), REASON_ADDED)
    assert date_of(missing("ROAD_TAX", after), [before, after], marks=[in_may, in_september]) == rm.Dated(date(2026, 9, 20), REASON_MARK_ENDS)


def test_a_certificate_without_its_copy_on_an_existing_machine_is_running_out_from_the_day_before_it_took_over():
    insurance = rule("INSURANCE")
    renewal = cert("INSURANCE", start=date(2026, 9, 1), copy=False)
    dated = date_of(missing("INSURANCE", insurance, certificate=renewal, outcome=OUTCOME_COPY_MISSING), [insurance], certificates=[renewal])
    # Nothing covered before it: dated by the day before it took over, as a cover ending then would be.
    assert dated == rm.Dated(date(2026, 8, 31), REASON_COPY_MISSING)
    assert rm.asset_reminder_kind(dated) == REMINDER_RUNNING_OUT


def test_a_certificate_without_its_copy_on_a_machine_just_added_is_not_yet_recorded():
    insurance = rule("INSURANCE")
    issued_earlier = cert("INSURANCE", start=date(2026, 4, 1), copy=False)
    dated = date_of(
        missing("INSURANCE", insurance, certificate=issued_earlier, outcome=OUTCOME_COPY_MISSING),
        [insurance],
        certificates=[issued_earlier],
        added=date(2026, 9, 28),
    )
    assert dated == rm.Dated(date(2026, 9, 28), REASON_ADDED)
    assert rm.asset_reminder_kind(dated) == REMINDER_NOT_YET_RECORDED


def test_on_a_tie_the_running_out_reason_wins():
    insurance = rule("INSURANCE")
    # Taking over on 29 September: dated 28 September, the day the machine was added.
    same_day = cert("INSURANCE", start=date(2026, 9, 29), copy=False)
    dated = date_of(
        missing("INSURANCE", insurance, certificate=same_day, outcome=OUTCOME_COPY_MISSING),
        [insurance],
        certificates=[same_day],
        added=date(2026, 9, 28),
    )
    assert dated == rm.Dated(date(2026, 9, 28), REASON_COPY_MISSING)


def test_a_mark_ending_keeps_the_same_reminder_before_and_after_its_end():
    # A crawler crane's road tax, marked not applicable until 5 October, judged by the baseline before and after.
    road_tax = rule("ROAD_TAX", type_code=None, not_applicable="ALLOWED")
    until = date(2026, 10, 5)
    marked = mark("ROAD_TAX", until=until, recorded=date(2026, 4, 1))
    proof = evidence([road_tax], [], [marked])
    unit = crane_unit(CRAWLER, carrier=False)
    keys = []
    for today in (until - timedelta(days=3), until + timedelta(days=2)):
        (result,) = [item for item in ev.baseline_results(unit, proof, today=today) if item.kind_code == "ROAD_TAX"]
        dated = rm.reminder_date(result, proof, assets=("crane",), added_on=date(2026, 3, 1), today=today)
        keys.append((rm.asset_reminder_kind(dated), dated.on, result.outcome_code))
    assert keys[0][:2] == keys[1][:2] == (REMINDER_RUNNING_OUT, until)
    assert keys[1][2] == OUTCOME_MISSING


def test_a_result_with_no_rule_or_kind_raises_nothing():
    assert date_of(ev.Result("crane", None, None, None, None, "RETIRED", "BLOCK", None), []) is None


# --- Which allocation reminder (section 5.1) ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "outcome, first_day, expected",
    [
        (OUTCOME_RUNS_OUT_BEFORE_START, D, REMINDER_BEFORE_JOB),
        (OUTCOME_RUNS_OUT_IN_PERIOD, D, REMINDER_DURING_JOB),
        (OUTCOME_RUN_OUT, D + timedelta(days=1), REMINDER_BEFORE_JOB),
        (OUTCOME_MISSING, D + timedelta(days=1), REMINDER_BEFORE_JOB),
        (OUTCOME_COPY_MISSING, D + timedelta(days=1), REMINDER_BEFORE_JOB),
        (OUTCOME_RUN_OUT, D, REMINDER_DURING_JOB),
        (OUTCOME_MISSING, D - timedelta(days=3), REMINDER_DURING_JOB),
        (OUTCOME_RUNS_OUT_SOON, D, None),
        (OUTCOME_VALID, D, None),
        (OUTCOME_NOT_APPLICABLE, D, None),
        ("RETIRED", D, None),
    ],
)
def test_each_outcome_raises_its_allocation_reminder(outcome, first_day, expected):
    assert rm.allocation_reminder_kind(outcome, first_day=first_day, today=D) == expected


def test_a_reminder_key_names_what_it_is_about_and_its_date():
    assert rm.reminder_key("DURING_JOB", "resource_assignment", "al-1", "crane", "INSURANCE", D) == (
        "DURING_JOB|resource_assignment|al-1|crane|INSURANCE|2026-11-30"
    )


# --- Settings (section 5.6) ------------------------------------------------------------------------------------


def problem(bands, steps=RUNNING_OUT_PATH) -> str | None:
    return rm.setting_problem(tuple(bands), tuple(steps), active_roles=ROLES)


def test_the_standard_settings_are_accepted():
    assert problem(STANDARD) is None
    assert problem(STANDARD, ALLOCATION_PATH) is None
    assert problem(NOT_YET, NOT_YET_PATH) is None


@pytest.mark.parametrize(
    "bands, steps, words",
    [
        ([], RUNNING_OUT_PATH, "at least one band"),
        ([rm.Band(n, 1) for n in range(0, -11, -1)], RUNNING_OUT_PATH, "no more than 10"),
        ([rm.Band(366, 1), rm.Band(0, 1)], RUNNING_OUT_PATH, "between 365 days before"),
        ([rm.Band(0, 0)], RUNNING_OUT_PATH, "every 1 to 365 days"),
        ([rm.Band(0, 366)], RUNNING_OUT_PATH, "every 1 to 365 days"),
        ([rm.Band(10, 1), rm.Band(10, 2), rm.Band(0, 1)], RUNNING_OUT_PATH, "same day"),
        ([rm.Band(60, 30), rm.Band(7, 1)], RUNNING_OUT_PATH, "never left without reminders"),
        (STANDARD, [], "at least one step"),
        (STANDARD, [step("NOBODY")], "role from the list"),
        (STANDARD, [step("ADMIN"), step("ADMIN", 7)], "one step only"),
        (STANDARD, [step("ADMIN", 15), step("OPERATIONS_USER")], "first step must start at the first reminder"),
        (STANDARD, [step("ADMIN"), rm.Step("OPERATIONS_USER", "DAYS_BEFORE", None, ("SCREEN",))], "Give the days"),
        (STANDARD, [step("ADMIN"), rm.Step("OPERATIONS_USER", "FIRST_REMINDER", 5, ("SCREEN",))], "Give the days"),
        (STANDARD, [step("ADMIN"), rm.Step("OPERATIONS_USER", "SOMETIMES", None, ("SCREEN",))], "first reminder, or a number of days"),
        (STANDARD, [step("ADMIN"), step("OPERATIONS_USER", 61)], "before the first reminder"),
        (STANDARD, [step("ADMIN"), step("OPERATIONS_USER", -366)], "no more than 365 days after"),
        (STANDARD, [rm.Step("ADMIN", "FIRST_REMINDER", None, ("EMAIL",))], "Only the screen"),
        (STANDARD, [rm.Step("ADMIN", "FIRST_REMINDER", None, ())], "Only the screen"),
        (STANDARD, [rm.Step("ADMIN", "FIRST_REMINDER", None, ("SCREEN", "SCREEN"))], "each channel once"),
    ],
)
def test_each_refusal_of_a_setting(bands, steps, words):
    found = problem(bands, steps)
    assert found is not None and words in found, found


def test_bands_given_in_any_order_are_ordered_and_judged_alike():
    shuffled = [rm.Band(0, 1), rm.Band(60, 30), rm.Band(7, 1), rm.Band(15, 7)]
    assert rm.ordered_bands(shuffled) == STANDARD
    assert problem(shuffled) is None


# --- A renewal recorded ahead without its copy (independent review, ELG2-R1-001) ---------------------------------


def _insurance_today(certificates, today: date) -> tuple[ev.Result, ev.Evidence]:
    insurance = rule("INSURANCE")
    unit = crane_unit(CRAWLER, carrier=False)
    (result,) = [item for item in ev.baseline_results(unit, evidence([insurance], certificates), today=today) if item.kind_code == "INSURANCE"]
    return result, evidence([insurance], certificates)


def test_a_renewal_recorded_ahead_without_its_copy_changes_the_reason_not_the_date_before_and_after_it_takes_over():
    current = cert("INSURANCE", start=date(2026, 1, 1), until=date(2026, 10, 31))
    renewal = cert("INSURANCE", start=date(2026, 11, 1), until=date(2027, 10, 31), copy=False)
    result, proof = _insurance_today([current], date(2026, 10, 1))
    plain = rm.reminder_date(result, proof, assets=("crane",), added_on=date(2026, 3, 1), today=date(2026, 10, 1))
    assert plain == rm.Dated(date(2026, 10, 31), REASON_RUNS_OUT)
    dates = []
    for today in (date(2026, 10, 1), date(2026, 11, 2)):
        result, proof = _insurance_today([current, renewal], today)
        dates.append(rm.reminder_date(result, proof, assets=("crane",), added_on=date(2026, 3, 1), today=today))
    # The cover ends on 31 October either way: the renewal's missing copy is the reason, before and after it takes
    # over, and the date - so the reminder, and whom it has reached - stays (ELG2-R2-002).
    assert dates == [rm.Dated(date(2026, 10, 31), REASON_COPY_MISSING)] * 2


def test_a_renewal_with_its_copy_or_after_a_gap_leaves_the_reminder_about_the_cover():
    current = cert("INSURANCE", start=date(2026, 1, 1), until=date(2026, 10, 31))
    copied = cert("INSURANCE", start=date(2026, 11, 1), until=date(2026, 11, 20))
    result, proof = _insurance_today([current, copied], date(2026, 10, 1))
    assert rm.reminder_date(result, proof, assets=("crane",), added_on=date(2026, 3, 1), today=date(2026, 10, 1)) == rm.Dated(date(2026, 11, 20), REASON_RUNS_OUT)
    after_gap = cert("INSURANCE", start=date(2026, 11, 5), until=date(2027, 10, 31), copy=False)
    result, proof = _insurance_today([current, after_gap], date(2026, 10, 1))
    assert rm.reminder_date(result, proof, assets=("crane",), added_on=date(2026, 3, 1), today=date(2026, 10, 1)) == rm.Dated(date(2026, 10, 31), REASON_RUNS_OUT)


def test_further_certificates_without_their_copies_leave_the_date_where_the_cover_ended():
    # ELG2-R4-001: covered with its copy until 30 September; from 1 October a renewal without its copy; from 1 November
    # another without its copy; on 1 November a same-day replacement of that one, also without. The cover ended once,
    # on 30 September: every one of them is the same reminder.
    covered = cert("INSURANCE", start=date(2025, 10, 1), until=date(2026, 9, 30))
    first = cert("INSURANCE", start=date(2026, 10, 1), until=date(2027, 9, 30), copy=False)
    second = cert("INSURANCE", start=date(2026, 11, 1), until=date(2027, 10, 31), copy=False)
    replacing = cert("INSURANCE", start=date(2026, 11, 1), until=date(2027, 10, 31), copy=False)
    for certificates, today in (
        ([covered, first], date(2026, 10, 15)),
        ([covered, first, second], date(2026, 10, 15)),
        ([covered, first, second], date(2026, 11, 5)),
        ([covered, first, second, replacing], date(2026, 11, 5)),
    ):
        result, proof = _insurance_today(certificates, today)
        assert rm.reminder_date(result, proof, assets=("crane",), added_on=date(2026, 3, 1), today=today) == rm.Dated(date(2026, 9, 30), REASON_COPY_MISSING)
    # With no certificate with its copy before them: the day before the first of them took over.
    result, proof = _insurance_today([first, second], date(2026, 11, 5))
    assert rm.reminder_date(result, proof, assets=("crane",), added_on=date(2026, 3, 1), today=date(2026, 11, 5)) == rm.Dated(date(2026, 9, 30), REASON_COPY_MISSING)
    # A certificate with its copy between them restores the cover: the next one without its copy is a new date.
    restored = cert("INSURANCE", start=date(2026, 10, 10), until=date(2026, 10, 31))
    result, proof = _insurance_today([covered, first, restored, second], date(2026, 11, 5))
    assert rm.reminder_date(result, proof, assets=("crane",), added_on=date(2026, 3, 1), today=date(2026, 11, 5)) == rm.Dated(date(2026, 10, 31), REASON_COPY_MISSING)


def test_a_renewal_without_its_copy_taking_over_before_the_current_one_ends_is_dated_by_the_day_before():
    current = cert("INSURANCE", start=date(2026, 1, 1), until=date(2026, 12, 31))
    early = cert("INSURANCE", start=date(2026, 10, 20), until=date(2027, 10, 19), copy=False)
    for today in (date(2026, 10, 1), date(2026, 10, 25)):
        result, proof = _insurance_today([current, early], today)
        assert rm.reminder_date(result, proof, assets=("crane",), added_on=date(2026, 3, 1), today=today) == rm.Dated(date(2026, 10, 19), REASON_COPY_MISSING)


# --- Dates at the ends (independent review, ELG2-R1-005) ------------------------------------------------------------


def test_reminder_days_and_steps_hold_at_the_first_and_last_day_a_date_can_be():
    today = date(2026, 10, 1)
    first = rm.reminder_days(STANDARD, date_on=date.min, began_on=date.min, today=today)
    assert first is not None and first.first_on == date.min and first.current_on == today
    assert set(roles_reached(RUNNING_OUT_PATH, first_on=date.min, date_on=date.min, today=today)) == {"ADMIN", "OPERATIONS_USER", "MANAGEMENT_READ_ONLY"}
    assert rm.reminder_days(STANDARD, date_on=date.max, began_on=today, today=today) is None
    assert roles_reached(RUNNING_OUT_PATH, first_on=today, date_on=date.max, today=today) == {"ADMIN": today}
    assert rm.reminder_days(NOT_YET, date_on=date.min, began_on=today, today=today) == rm.Days(today, today, 1)


def test_a_requirement_beginning_on_the_first_day_a_date_can_be():
    earliest = rule("INSURANCE", start=date.min)
    assert rm.requirement_began(earliest, [earliest]) == date.min
    result = ev.Result("crane", "INSURANCE", rule("INSURANCE"), cert("INSURANCE", start=date(2026, 1, 1), until=date.max), None, OUTCOME_VALID, "NONE", date.max)
    assert rm.uncopied_takeover(result, evidence([earliest], [result.certificate])) is None


def test_management_reached_seven_days_before_stays_reached_when_a_renewal_without_its_copy_is_recorded():
    # ELG2-R2-002: the insurance runs out on 8 October; on 1 October Management has been reached. A renewal from 9
    # October is then recorded without its copy: same date, same reminder, same people.
    current = cert("INSURANCE", start=date(2026, 1, 1), until=date(2026, 10, 8))
    renewal = cert("INSURANCE", start=date(2026, 10, 9), until=date(2027, 10, 8), copy=False)
    reached = []
    for certificates in ([current], [current, renewal]):
        result, proof = _insurance_today(certificates, date(2026, 10, 1))
        dated = rm.reminder_date(result, proof, assets=("crane",), added_on=date(2026, 3, 1), today=date(2026, 10, 1))
        days = rm.reminder_days(STANDARD, date_on=dated.on, began_on=LONG_AGO, today=date(2026, 10, 1))
        reached.append((dated.on, set(roles_reached(RUNNING_OUT_PATH, first_on=days.first_on, date_on=dated.on, today=date(2026, 10, 1)))))
    assert reached[0] == reached[1] == (date(2026, 10, 8), {"ADMIN", "OPERATIONS_USER", "MANAGEMENT_READ_ONLY"})


def test_a_renewal_without_its_copy_after_a_gap_keeps_the_date_the_cover_ended():
    current = cert("INSURANCE", start=date(2026, 1, 1), until=date(2026, 10, 10))
    late = cert("INSURANCE", start=date(2026, 10, 20), until=date(2027, 10, 19), copy=False)
    before, proof = _insurance_today([current, late], date(2026, 10, 15))
    assert rm.reminder_date(before, proof, assets=("crane",), added_on=date(2026, 3, 1), today=date(2026, 10, 15)) == rm.Dated(date(2026, 10, 10), REASON_RUNS_OUT)
    after, proof = _insurance_today([current, late], date(2026, 10, 21))
    assert rm.reminder_date(after, proof, assets=("crane",), added_on=date(2026, 3, 1), today=date(2026, 10, 21)) == rm.Dated(date(2026, 10, 10), REASON_COPY_MISSING)
