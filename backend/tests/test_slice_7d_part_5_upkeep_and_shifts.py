"""Slice 7D Part 5 - the shift pattern, and the crew's food, accommodation and travel.

Each test maps to an item in the "Test plan" of docs/agent/slices/slice-7d-part-5-crew-upkeep-and-shifts.md.
The owner's answers the rules come from are those of 9 October 2026; where they left a point open, the
reading taken is the slice document's assumption of that number (A1 to A15).

The three-line chain fixture is Part 3's and the request helpers are Part 1's, imported rather than rebuilt:
these terms are the same records, the same routes and the same conflict rules, with two more groups of
columns. Part 2's night shift became the shift pattern; the migration that converts it is checked by script
(the slice's continuity note), as every billing-terms migration has been.

Business events need no explicit cleanup: conftest removes every event created by the session.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.work_orders.contract import WORK_ORDER_LINE_TERMS_MISSING_ORDER, WORK_ORDER_LINE_UPKEEP_CELLS
from tests.test_slice_7d_part_3_contract_period import (  # noqa: F401  (chain is a fixture)
    _billing_terms,
    _copy,
    chain,
)
from tests.test_slice_7d_work_order_line_billing_terms import (
    DAY_TERMS,
    HOUR_TERMS,
    MONTH_OT_NORMAL_CUMULATIVE,
    PART_2_FIRST_PERIOD_ONLY,
    PART_5_CREW_UPKEEP_NONE,
    SHIFT_TERMS,
    _add,
    _insert_term_directly,
    _line_terms,
    _put,
)

# --- Term sets -------------------------------------------------------------------------------------

# A 12-hour first shift and an 8-hour second shift (the owner's example), one rate for both; overtime is
# charged on SHIFT_TERMS, so with two shifts the Work Order says how it is counted.
TWO_SHIFTS_SAME_RATE = {
    "shift_pattern_code": "TWO_SHIFTS",
    "shift_1_hours": "12.00",
    "shift_2_hours": "8.00",
    "shift_rate_code": "SAME_FOR_ALL_SHIFTS",
    "overtime_counted_per_code": "PER_SHIFT",
}
# Three 8-hour shifts on a monthly line, each later shift at its own rate and working days, overtime
# counted day by day and then for the whole day.
THREE_SHIFTS_PER_SHIFT_MONTH = {
    **MONTH_OT_NORMAL_CUMULATIVE,
    "month_overtime_counting_code": "DAY_BY_DAY",
    "shift_pattern_code": "THREE_SHIFTS",
    "shift_1_hours": "8.00",
    "shift_2_hours": "8.00",
    "shift_3_hours": "8.00",
    "shift_rate_code": "PER_SHIFT",
    "shift_2_rate_method_code": "PERCENT_OF_NORMAL",
    "shift_2_rate_percent": "90.00",
    "shift_2_working_days_per_month": "26.00",
    "shift_3_rate_method_code": "RATE_PER_SHIFT",
    "shift_3_rate_amount": "4500.00",
    "shift_3_working_days_per_month": "24.00",
    "overtime_counted_per_code": "PER_DAY",
}

CREW_2_AND_1 = {"crew_code": "STATED", "crew_operators_per_unit": 2, "crew_helpers_per_unit": 1, "extra_crew_charge_code": "NONE"}


def _upkeep(item: str, role: str, **fields: object) -> dict:
    """One cell's answers by field name - code, amount, unit, recovery."""
    prefix = f"upkeep_{item}_{role}"
    names = {"code": f"{prefix}_code", "amount": f"{prefix}_amount", "unit": f"{prefix}_unit_code", "recovery": f"{prefix}_recovery_code"}
    return {names[key]: value for key, value in fields.items()}


# The owner's examples: food provided by the customer's mess; accommodation at Rs 150 a day for each
# operator, deducted from PBL's invoice, and Rs 3,000 a month for each helper, billed separately; the trip to
# and from the job at Rs 2,500 a trip for each operator, and Rs 4,000 a trip for the helpers whatever their
# number, deducted; daily travel not in the Work Order. Every cost states its basis (review round 1, 7D5-R1-003).
UPKEEP_ANSWERED = {
    **PART_5_CREW_UPKEEP_NONE,
    **_upkeep("food", "operator", code="PROVIDED"),
    **_upkeep("food", "helper", code="PROVIDED"),
    **_upkeep("accommodation", "operator", code="PROVIDED_AT_COST", amount="150.00", unit="PER_PERSON_PER_DAY", recovery="DEDUCTED_FROM_INVOICE"),
    **_upkeep("accommodation", "helper", code="PROVIDED_AT_COST", amount="3000.00", unit="PER_PERSON_PER_MONTH", recovery="BILLED_SEPARATELY"),
    **_upkeep("job_travel", "operator", code="PROVIDED_AT_COST", amount="2500.00", unit="PER_PERSON_PER_TRIP", recovery="DEDUCTED_FROM_INVOICE"),
    **_upkeep("job_travel", "helper", code="PROVIDED_AT_COST", amount="4000.00", unit="PER_TRIP", recovery="DEDUCTED_FROM_INVOICE"),
}
SHIFT_LINE_WITH_CREW = {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, **CREW_2_AND_1}


def _period(response) -> dict:
    assert response.status_code in (200, 201), response.text
    return response.json()["line_billing_terms"]["periods"][0]


def _event_payloads(work_order_public_id: str, event_name: str) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT event_payload_json FROM business_event WHERE record_type = 'work_order' "
                "AND record_public_id = :id AND event_name = :name ORDER BY id ASC"
            ),
            {"id": work_order_public_id, "name": event_name},
        ).fetchall()
    return [row[0] if isinstance(row[0], dict) else json.loads(row[0]) for row in rows]


# --- The shift pattern: what the API refuses --------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "says"),
    [
        ({"shift_pattern_code": "FOUR_SHIFTS"}, "one, two or three shifts"),
        # A shift's hours only where the Work Order states its shifts; NONE states none (A7, round 2).
        ({"shift_pattern_code": "NONE", "shift_1_hours": "10.00"}, "states its shifts"),
        ({"shift_pattern_code": "NONE", "shift_rate_code": "SAME_FOR_ALL_SHIFTS"}, "states its shifts"),
        ({"shift_pattern_code": None, "shift_2_hours": "8.00"}, "states its shifts"),
        ({"shift_pattern_code": "NONE", "overtime_counted_per_code": "PER_SHIFT"}, "states its shifts"),
        # One shift has its hours and nothing a second shift brings (A8).
        ({"shift_pattern_code": "ONE_SHIFT", "shift_1_hours": "10.00", "shift_2_hours": "8.00"}, "two or three shifts"),
        ({"shift_pattern_code": "ONE_SHIFT", "shift_1_hours": "10.00", "shift_rate_code": "SAME_FOR_ALL_SHIFTS"}, "two or three shifts"),
        ({"shift_pattern_code": "ONE_SHIFT", "shift_1_hours": "10.00", "overtime_counted_per_code": "PER_DAY"}, "two or three shifts"),
        ({"shift_pattern_code": "ONE_SHIFT", "shift_1_hours": "25.00"}, "25 hours"),
        # A third shift only with three.
        ({**TWO_SHIFTS_SAME_RATE, "shift_3_hours": "4.00"}, "third shift"),
        # A later shift's own rate only when each shift has its own rate.
        ({**TWO_SHIFTS_SAME_RATE, "shift_2_rate_method_code": "RATE_PER_HOUR", "shift_2_rate_amount": "900.00"}, "its own rate"),
        ({**TWO_SHIFTS_SAME_RATE, "shift_rate_code": None, "shift_2_rate_method_code": "RATE_PER_HOUR", "shift_2_rate_amount": "900.00"}, "its own rate"),
        # The rate's one value, given with its method (Part 2's night-shift rule).
        ({**TWO_SHIFTS_SAME_RATE, "shift_rate_code": "PER_SHIFT", "shift_2_rate_method_code": "RATE_PER_SHIFT"}, "Enter shift 2's rate"),
        ({**TWO_SHIFTS_SAME_RATE, "shift_rate_code": "PER_SHIFT", "shift_2_rate_method_code": "PERCENT_OF_NORMAL"}, "percentage"),
        ({**TWO_SHIFTS_SAME_RATE, "shift_rate_code": "PER_SHIFT", "shift_2_rate_method_code": "RATE_PER_SHIFT", "shift_2_rate_amount": "9000.00", "shift_2_rate_percent": "90.00"}, "no percentage"),
        ({**TWO_SHIFTS_SAME_RATE, "shift_rate_code": "PER_SHIFT", "shift_2_rate_amount": "9000.00"}, "Choose how shift 2 is charged"),
        # A later shift is charged: "not in the Work Order" is not one of its choices.
        ({**TWO_SHIFTS_SAME_RATE, "shift_rate_code": "PER_SHIFT", "shift_2_rate_method_code": "NONE"}, "per shift, per hour"),
        ({**TWO_SHIFTS_SAME_RATE, "shift_rate_code": "EACH_ITS_OWN"}, "one rate for every shift"),
        # Working days per month on a monthly line only.
        ({**TWO_SHIFTS_SAME_RATE, "shift_rate_code": "PER_SHIFT", "shift_2_rate_method_code": "RATE_PER_HOUR", "shift_2_rate_amount": "900.00", "shift_2_working_days_per_month": "26.00"}, "Month billing"),
        # A day has 24 hours (A11).
        ({**TWO_SHIFTS_SAME_RATE, "shift_1_hours": "16.00", "shift_2_hours": "8.50"}, "24.5 hours"),
        # Not a positive number.
        ({**TWO_SHIFTS_SAME_RATE, "shift_1_hours": "0"}, None),
        ({**TWO_SHIFTS_SAME_RATE, "shift_2_hours": "-8"}, None),
        ({**TWO_SHIFTS_SAME_RATE, "shift_1_hours": "100.00"}, None),
        ({**TWO_SHIFTS_SAME_RATE, "overtime_counted_per_code": "PER_WEEK"}, "per shift or for the whole day"),
        # Per shift or per day only where overtime is charged on several shifts (A12).
        ({**TWO_SHIFTS_SAME_RATE, "overtime_rate_method_code": "NONE", "overtime_rate_amount": None, "off_day_work_treatment_code": "NORMAL_RATE"}, "applies only when overtime is charged"),
    ],
)
def test_a_shift_term_that_breaks_its_own_rule_is_refused(chain, change: dict, says: str | None) -> None:
    response = _add(chain, {**SHIFT_TERMS, **change})
    assert response.status_code == 422, response.text
    if says is not None:
        assert says in response.json()["detail"], response.json()["detail"]
    assert _line_terms(chain)["periods"] == []


def test_a_monthly_line_counted_over_the_whole_month_is_asked_per_shift_or_per_day_too(chain) -> None:
    """The owner's answer 5 is not limited to day-by-day counting, so a whole-month line records it and reports
    it missing until answered (A12; review round 1, finding 7D5-R1-001)."""
    terms = {**THREE_SHIFTS_PER_SHIFT_MONTH, **PART_2_FIRST_PERIOD_ONLY, "month_overtime_counting_code": "WHOLE_MONTH"}
    period = _period(_add(chain, {**terms, "overtime_counted_per_code": None}))
    assert period["missing_items"] == ["OVERTIME"]
    recorded = _period(_add(chain, terms, line_index=1))
    assert recorded["overtime_counted_per_code"] == "PER_DAY"
    assert recorded["is_complete"] is True, recorded["missing_items"]


@pytest.mark.parametrize("change", [{"shift_pattern_code": "NONE"}, TWO_SHIFTS_SAME_RATE])
def test_an_hourly_line_has_no_shift_pattern(chain, change: dict) -> None:
    """Hourly billing uses the hours actually worked (WBT-001), as it had no night shift (A13)."""
    response = _add(chain, {**HOUR_TERMS, **change})
    assert response.status_code == 422
    assert "no shift pattern" in response.json()["detail"]
    assert _line_terms(chain)["periods"] == []


def test_the_shift_pattern_is_not_a_term_before_the_billing_basis(chain) -> None:
    response = _add(chain, {"shift_pattern_code": "NONE"})
    assert response.status_code == 422
    assert "billing basis" in response.json()["detail"]


# --- The shift pattern: what is recorded --------------------------------------------------------------


def test_two_shifts_at_one_rate_are_recorded_as_written_and_complete(chain) -> None:
    period = _period(_add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, **TWO_SHIFTS_SAME_RATE}))
    assert (period["shift_pattern_code"], period["shift_1_hours"], period["shift_2_hours"]) == ("TWO_SHIFTS", "12.00", "8.00")
    assert period["shift_rate_code"] == "SAME_FOR_ALL_SHIFTS"
    assert period["shift_3_hours"] is None
    assert period["overtime_counted_per_code"] == "PER_SHIFT"
    assert period["is_complete"] is True, period["missing_items"]


def test_three_shifts_each_at_its_own_rate_on_a_monthly_line(chain) -> None:
    period = _period(_add(chain, {**THREE_SHIFTS_PER_SHIFT_MONTH, **PART_2_FIRST_PERIOD_ONLY}))
    assert period["shift_2_rate_percent"] == "90.00"
    assert period["shift_3_rate_amount"] == "4500.00"
    assert (period["shift_2_working_days_per_month"], period["shift_3_working_days_per_month"]) == ("26.00", "24.00")
    assert period["overtime_counted_per_code"] == "PER_DAY"
    assert period["is_complete"] is True, period["missing_items"]


def test_shifts_filling_the_whole_day_are_accepted(chain) -> None:
    terms = {**DAY_TERMS, **TWO_SHIFTS_SAME_RATE, "shift_1_hours": "16.00", "shift_2_hours": "8.00"}
    assert _period(_add(chain, terms))["shift_1_hours"] == "16.00"


def test_not_in_the_work_order_is_an_answer_that_states_no_shifts(chain) -> None:
    """"Not in the Work Order" is an answer - the period is complete - and states no shifts at all, so it asks for
    no hours and gives no shift count (A7; review round 2, 7D5-R2-002)."""
    period = _period(_add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY}))
    assert period["shift_pattern_code"] == "NONE"
    assert "SHIFTS" not in period["missing_items"]
    assert period["is_complete"] is True, period["missing_items"]


def test_one_stated_shift_records_its_hours_and_is_reported_missing_without_them(chain) -> None:
    """A Work Order that states one shift - "one shift of 10 hours" - records it as written (A8; round 2)."""
    missing = _period(_add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "shift_pattern_code": "ONE_SHIFT"}))
    assert missing["missing_items"] == ["SHIFTS"]
    recorded = _period(
        _add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "shift_pattern_code": "ONE_SHIFT", "shift_1_hours": "10.00"}, line_index=1)
    )
    assert (recorded["shift_pattern_code"], recorded["shift_1_hours"]) == ("ONE_SHIFT", "10.00")
    assert recorded["is_complete"] is True, recorded["missing_items"]
    # Overtime is charged on SHIFT_TERMS, but with one shift "per shift or per day" does not arise.
    assert "OVERTIME" not in recorded["missing_items"]


@pytest.mark.parametrize(
    "change",
    [
        {"shift_pattern_code": None},
        {**TWO_SHIFTS_SAME_RATE, "shift_2_hours": None},
        {**TWO_SHIFTS_SAME_RATE, "shift_rate_code": None},
        {**TWO_SHIFTS_SAME_RATE, "shift_pattern_code": "THREE_SHIFTS"},
        {**TWO_SHIFTS_SAME_RATE, "shift_rate_code": "PER_SHIFT"},
    ],
)
def test_a_shift_choice_recorded_without_what_it_needs_is_reported_missing(chain, change: dict) -> None:
    period = _period(_add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, **change}))
    assert "SHIFTS" in period["missing_items"], period["missing_items"]
    assert period["is_complete"] is False


def test_a_later_shift_on_a_monthly_line_still_needs_its_working_days(chain) -> None:
    terms = {**THREE_SHIFTS_PER_SHIFT_MONTH, **PART_2_FIRST_PERIOD_ONLY, "shift_3_working_days_per_month": None}
    assert "SHIFTS" in _period(_add(chain, terms))["missing_items"]


def test_overtime_on_several_shifts_still_needs_how_it_is_counted(chain) -> None:
    period = _period(_add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, **TWO_SHIFTS_SAME_RATE, "overtime_counted_per_code": None}))
    assert period["missing_items"] == ["OVERTIME"]
    monthly = {**THREE_SHIFTS_PER_SHIFT_MONTH, **PART_2_FIRST_PERIOD_ONLY, "overtime_counted_per_code": None}
    assert _period(_add(chain, monthly, line_index=1))["missing_items"] == ["OVERTIME"]


def test_a_kept_legacy_night_shift_answer_is_read_and_never_changed_by_a_save(chain) -> None:
    """The migration keeps a Part 2 night shift "not in the Work Order" on its period and asks for the shift pattern
    again (review round 4, 7D5-R4-001). Written here as the migration leaves it: the marker reads back, the period
    reports SHIFTS missing, and a save answering the shifts leaves the marker as it was - no request can set it."""
    _insert_term_directly(
        chain["line_public_ids"][0],
        billing_uom_code="SHIFT",
        legacy_night_shift_not_in_work_order=True,
    )
    try:
        period = _line_terms(chain)["periods"][0]
        assert period["legacy_night_shift_not_in_work_order"] is True
        assert "SHIFTS" in period["missing_items"]
        saved = _put(
            chain,
            period["term_public_id"],
            {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "shift_pattern_code": "ONE_SHIFT", "shift_1_hours": "8.00"},
            expected_term_revision=period["term_revision"],
        )
        after = _period(saved)
        assert after["legacy_night_shift_not_in_work_order"] is True
        assert "SHIFTS" not in after["missing_items"]
        assert _add(chain, {**SHIFT_TERMS, "legacy_night_shift_not_in_work_order": False}, expected_period_count=1, effective_from="2027-03-01").status_code == 422
    finally:
        with SessionLocal() as db:
            db.execute(
                text(
                    "DELETE FROM crm_work_order_line_billing_term WHERE work_order_line_id IN "
                    "(SELECT id FROM crm_work_order_line WHERE work_order_line_public_id = :line)"
                ),
                {"line": chain["line_public_ids"][0]},
            )
            db.commit()


def test_copying_terms_does_not_carry_the_legacy_marker(chain) -> None:
    """The marker is the source period's history, not a term: copying its terms to another line leaves the source
    marked and the copy unmarked (review round 5, 7D5-R5-002). It would fail if the marker joined the copied
    columns or were otherwise propagated."""
    _insert_term_directly(chain["line_public_ids"][0], billing_uom_code="SHIFT", legacy_night_shift_not_in_work_order=True)
    try:
        response = _copy(chain, target_indexes=(1,))
        assert response.status_code == 200, response.text
        by_line = {item["work_order_line_public_id"]: item for item in _billing_terms(chain)}
        assert by_line[chain["line_public_ids"][0]]["periods"][0]["legacy_night_shift_not_in_work_order"] is True
        copied = by_line[chain["line_public_ids"][1]]["periods"]
        assert copied and all(period["legacy_night_shift_not_in_work_order"] is False for period in copied)
    finally:
        with SessionLocal() as db:
            db.execute(
                text(
                    "DELETE FROM crm_work_order_line_billing_term WHERE work_order_line_id IN "
                    "(SELECT id FROM crm_work_order_line WHERE work_order_line_public_id = ANY(:lines))"
                ),
                {"lines": list(chain["line_public_ids"][:2])},
            )
            db.commit()


def test_a_new_period_carries_no_legacy_marker(chain) -> None:
    assert _period(_add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY}))["legacy_night_shift_not_in_work_order"] is False


def test_shifts_are_reported_where_the_night_shift_was(chain) -> None:
    assert WORK_ORDER_LINE_TERMS_MISSING_ORDER.index("SHIFTS") == WORK_ORDER_LINE_TERMS_MISSING_ORDER.index("PART_MONTH") + 1
    assert "NIGHT_SHIFT" not in WORK_ORDER_LINE_TERMS_MISSING_ORDER


def test_the_night_shift_fields_are_gone(chain) -> None:
    """Part 5 replaced them; a caller still sending one is refused rather than silently ignored."""
    response = _add(chain, {**SHIFT_TERMS, "night_shift_rate_method_code": "RATE_PER_SHIFT", "night_shift_rate_amount": "9000.00"})
    assert response.status_code == 422
    period = _period(_add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY}))
    assert not any(key.startswith("night_shift") for key in period)


# --- The crew's food, accommodation and travel: what the API refuses ----------------------------------


@pytest.mark.parametrize(
    ("change", "says"),
    [
        # Only while the Work Order states its crew (A4).
        ({"crew_code": "NONE", **_upkeep("food", "operator", code="PROVIDED")}, "states its crew"),
        ({"crew_code": None, "crew_operators_per_unit": None, "crew_helpers_per_unit": None, "extra_crew_charge_code": None, **_upkeep("food", "operator", code="PROVIDED")}, "states its crew"),
        # Nothing for people it states none of (A5).
        ({"crew_helpers_per_unit": 0, **_upkeep("daily_travel", "helper", code="NONE")}, "states no helpers"),
        ({"crew_operators_per_unit": 0, **_upkeep("accommodation", "operator", code="PROVIDED")}, "states no operators"),
        # A cost's values only "at a cost".
        (_upkeep("food", "operator", code="PROVIDED", amount="120.00"), "provided at a cost"),
        (_upkeep("accommodation", "helper", code="NONE", unit="PER_PERSON_PER_DAY"), "provided at a cost"),
        (_upkeep("job_travel", "operator", recovery="BILLED_SEPARATELY"), "provided at a cost"),
        # Codes.
        (_upkeep("food", "operator", code="FREE"), "provided by the customer"),
        (_upkeep("food", "operator", code="PROVIDED_AT_COST", amount="120.00", unit="PER_WEEK"), "per person per day or per person per month"),
        # Each item takes its own bases: a trip is not costed per month, nor food per trip.
        (_upkeep("job_travel", "operator", code="PROVIDED_AT_COST", amount="2500.00", unit="PER_PERSON_PER_MONTH"), "per person per trip or per trip"),
        (_upkeep("food", "helper", code="PROVIDED_AT_COST", amount="120.00", unit="PER_TRIP"), "per person per day or per person per month"),
        (_upkeep("daily_travel", "helper", code="PROVIDED_AT_COST", amount="80.00", recovery="PAID_TO_WORKER"), "deducted from PBL's invoice"),
        # Not a positive number.
        (_upkeep("food", "operator", code="PROVIDED_AT_COST", amount="0"), None),
        (_upkeep("food", "operator", code="PROVIDED_AT_COST", amount="-5"), None),
        (_upkeep("food", "operator", code="PROVIDED_AT_COST", amount="NaN"), None),
        # A basis without a cost.
        (_upkeep("daily_travel", "operator", code="PROVIDED", unit="PER_DAY"), "provided at a cost"),
    ],
)
def test_an_upkeep_term_that_breaks_its_own_rule_is_refused(chain, change: dict, says: str | None) -> None:
    response = _add(chain, {**SHIFT_LINE_WITH_CREW, **change})
    assert response.status_code == 422, response.text
    if says is not None:
        assert says in response.json()["detail"], response.json()["detail"]
    assert _line_terms(chain)["periods"] == []


# --- The crew's upkeep: what is recorded ---------------------------------------------------------------


def test_the_owners_examples_are_recorded_and_complete(chain) -> None:
    period = _period(_add(chain, {**SHIFT_LINE_WITH_CREW, **UPKEEP_ANSWERED}))
    assert period["upkeep_food_operator_code"] == "PROVIDED"
    assert period["upkeep_accommodation_operator_amount"] == "150.00"
    assert period["upkeep_accommodation_operator_unit_code"] == "PER_PERSON_PER_DAY"
    assert period["upkeep_accommodation_operator_recovery_code"] == "DEDUCTED_FROM_INVOICE"
    assert period["upkeep_accommodation_helper_unit_code"] == "PER_PERSON_PER_MONTH"
    assert (period["upkeep_job_travel_operator_unit_code"], period["upkeep_job_travel_helper_unit_code"]) == ("PER_PERSON_PER_TRIP", "PER_TRIP")
    assert period["upkeep_accommodation_helper_recovery_code"] == "BILLED_SEPARATELY"
    assert period["upkeep_job_travel_helper_amount"] == "4000.00"
    assert period["upkeep_daily_travel_operator_code"] == "NONE"
    assert period["is_complete"] is True, period["missing_items"]


@pytest.mark.parametrize("terms", [HOUR_TERMS, MONTH_OT_NORMAL_CUMULATIVE])
def test_upkeep_applies_to_every_basis(chain, terms: dict) -> None:
    period = _period(_add(chain, {**terms, **PART_2_FIRST_PERIOD_ONLY, **CREW_2_AND_1, **UPKEEP_ANSWERED}))
    assert period["is_complete"] is True, period["missing_items"]


def test_equipment_only_is_asked_nothing_about_upkeep(chain) -> None:
    period = _period(_add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY}))
    assert period["crew_code"] == "NONE"
    assert "CREW_UPKEEP" not in period["missing_items"]


def test_a_stated_crew_without_upkeep_reports_it_missing(chain) -> None:
    """A period saved before Part 5 with its crew stated reports this - correct, it was never recorded."""
    period = _period(_add(chain, SHIFT_LINE_WITH_CREW))
    assert period["missing_items"] == ["CREW_UPKEEP"]


def test_no_helpers_means_no_helper_upkeep_is_asked(chain) -> None:
    operators_only = {str(cell["code"]): "NONE" for cell in WORK_ORDER_LINE_UPKEEP_CELLS if cell["role"] == "operator"}
    period = _period(_add(chain, {**SHIFT_LINE_WITH_CREW, "crew_helpers_per_unit": 0, **operators_only}))
    assert period["is_complete"] is True, period["missing_items"]


@pytest.mark.parametrize(
    "missing_field",
    [
        "upkeep_accommodation_operator_amount",
        "upkeep_accommodation_operator_unit_code",
        "upkeep_accommodation_operator_recovery_code",
        "upkeep_job_travel_helper_amount",
        "upkeep_job_travel_helper_unit_code",
        "upkeep_food_helper_code",
    ],
)
def test_an_upkeep_answer_without_what_it_needs_is_reported_missing(chain, missing_field: str) -> None:
    period = _period(_add(chain, {**SHIFT_LINE_WITH_CREW, **UPKEEP_ANSWERED, missing_field: None}))
    assert period["missing_items"] == ["CREW_UPKEEP"]


# --- Events and copying ----------------------------------------------------------------------------


def test_no_part_5_value_reaches_an_event_payload(chain) -> None:
    terms = {**SHIFT_LINE_WITH_CREW, **UPKEEP_ANSWERED, **TWO_SHIFTS_SAME_RATE}
    _period(_add(chain, terms))
    payloads = _event_payloads(chain["work_order_public_id"], "WorkOrderLineBillingTermsPeriodAdded")
    assert payloads, "the added event was not recorded"
    for payload in payloads:
        text_of_payload = json.dumps(payload)
        for forbidden in ("150.00", "3000.00", "2500.00", "4000.00", "12.00"):
            assert forbidden not in text_of_payload, forbidden
        for field in ("shift_pattern_code", "shift_1_hours", "upkeep_accommodation_operator_amount"):
            assert field in payload["changed_fields"]


def test_changing_only_one_upkeep_answer_names_just_its_columns(chain) -> None:
    period = _period(_add(chain, {**SHIFT_LINE_WITH_CREW, **UPKEEP_ANSWERED}))
    changed = {**UPKEEP_ANSWERED, **_upkeep("daily_travel", "operator", code="PROVIDED_AT_COST", amount="60.00", unit="PER_DAY", recovery="BILLED_SEPARATELY")}
    updated = _put(chain, period["term_public_id"], {**SHIFT_LINE_WITH_CREW, **changed}, expected_term_revision=period["term_revision"])
    assert updated.status_code == 200, updated.text
    names = _event_payloads(chain["work_order_public_id"], "WorkOrderLineBillingTermsPeriodUpdated")[-1]["changed_fields"]
    assert set(names) == {
        "upkeep_daily_travel_operator_code",
        "upkeep_daily_travel_operator_amount",
        "upkeep_daily_travel_operator_unit_code",
        "upkeep_daily_travel_operator_recovery_code",
    }


def test_applying_terms_to_other_lines_copies_the_part_5_terms_too(chain) -> None:
    _period(_add(chain, {**SHIFT_LINE_WITH_CREW, **UPKEEP_ANSWERED, **TWO_SHIFTS_SAME_RATE}))
    response = _copy(chain, target_indexes=(1,))
    assert response.status_code == 200, response.text
    target = next(item for item in _billing_terms(chain) if item["work_order_line_public_id"] == chain["line_public_ids"][1])
    period = target["periods"][0]
    assert (period["shift_1_hours"], period["shift_2_hours"]) == ("12.00", "8.00")
    assert period["upkeep_accommodation_helper_amount"] == "3000.00"
    assert target["terms_complete"] is True


# --- What the database itself refuses ---------------------------------------------------------------

_SHIFT = {"billing_uom_code": "SHIFT"}
_TWO = {**_SHIFT, "shift_pattern_code": "TWO_SHIFTS"}
_PER_SHIFT = {**_TWO, "shift_rate_code": "PER_SHIFT"}
_STATED = {**_SHIFT, "crew_code": "STATED"}


@pytest.mark.parametrize(
    ("columns", "constraint"),
    [
        ({**_SHIFT, "shift_pattern_code": "FOUR_SHIFTS"}, "ck_wol_term_shift_codes"),
        ({**_TWO, "shift_rate_code": "EACH"}, "ck_wol_term_shift_codes"),
        ({**_PER_SHIFT, "shift_2_rate_method_code": "NONE"}, "ck_wol_term_shift_codes"),
        # Overtime charged, so the row passes ck_wol_term_overtime_counted_per, which PostgreSQL checks first
        # (CHECKs are tested in alphabetical order of their names).
        (
            {**_TWO, "overtime_rate_method_code": "RATE_PER_HOUR", "overtime_rate_amount": Decimal("900"), "overtime_counted_per_code": "PER_WEEK"},
            "ck_wol_term_shift_codes",
        ),
        ({**_TWO, "shift_1_hours": Decimal("0")}, "ck_wol_term_shift_positive_values"),
        # NaN compares greater than every number, so shift hours stored as NaN fail the day's 24 hours first.
        ({**_TWO, "shift_1_hours": Decimal("NaN")}, "ck_wol_term_shift_hours_in_a_day"),
        ({**_PER_SHIFT, "shift_2_rate_method_code": "RATE_PER_SHIFT", "shift_2_rate_amount": Decimal("NaN")}, "ck_wol_term_shift_positive_values"),
        ({**_PER_SHIFT, "shift_2_rate_method_code": "RATE_PER_SHIFT", "shift_2_rate_amount": Decimal("-1")}, "ck_wol_term_shift_positive_values"),
        # NULL shifts add nothing; the hours given are counted.
        ({**_TWO, "shift_1_hours": Decimal("20"), "shift_2_hours": Decimal("8")}, "ck_wol_term_shift_hours_in_a_day"),
        ({**_TWO, "shift_pattern_code": "THREE_SHIFTS", "shift_2_hours": Decimal("20"), "shift_3_hours": Decimal("8")}, "ck_wol_term_shift_hours_in_a_day"),
        # Each value only with its parent - including a parent that is NULL, not just a different code.
        ({**_SHIFT, "shift_1_hours": Decimal("8")}, "ck_wol_term_shift_values"),
        ({**_SHIFT, "shift_pattern_code": "NONE", "shift_rate_code": "PER_SHIFT"}, "ck_wol_term_shift_values"),
        ({**_SHIFT, "shift_pattern_code": "NONE", "shift_1_hours": Decimal("10")}, "ck_wol_term_shift_values"),
        ({**_SHIFT, "shift_pattern_code": "ONE_SHIFT", "shift_1_hours": Decimal("10"), "shift_2_hours": Decimal("8")}, "ck_wol_term_shift_values"),
        ({**_SHIFT, "shift_pattern_code": "ONE_SHIFT", "shift_rate_code": "SAME_FOR_ALL_SHIFTS"}, "ck_wol_term_shift_values"),
        ({**_TWO, "shift_3_hours": Decimal("4")}, "ck_wol_term_shift_values"),
        ({**_TWO, "shift_2_rate_method_code": "RATE_PER_HOUR", "shift_2_rate_amount": Decimal("900")}, "ck_wol_term_shift_values"),
        ({**_PER_SHIFT, "shift_3_rate_method_code": "RATE_PER_HOUR", "shift_3_rate_amount": Decimal("900")}, "ck_wol_term_shift_values"),
        # A later shift's rate carries exactly its value; days only on a monthly line.
        ({**_PER_SHIFT, "shift_2_rate_method_code": "RATE_PER_SHIFT"}, "ck_wol_term_shift_rates"),
        ({**_PER_SHIFT, "shift_2_rate_method_code": "PERCENT_OF_NORMAL", "shift_2_rate_amount": Decimal("900")}, "ck_wol_term_shift_rates"),
        ({**_PER_SHIFT, "shift_2_rate_percent": Decimal("90")}, "ck_wol_term_shift_rates"),
        ({**_PER_SHIFT, "shift_2_rate_method_code": "RATE_PER_HOUR", "shift_2_rate_amount": Decimal("900"), "shift_2_working_days_per_month": Decimal("26")}, "ck_wol_term_shift_rates"),
        # No shift pattern on an hourly line, or before the basis.
        ({"billing_uom_code": "HOUR", "shift_pattern_code": "NONE"}, "ck_wol_term_shift_not_hourly"),
        ({"shift_pattern_code": "NONE"}, "ck_wol_term_shift_not_hourly"),
        # Per shift or per day: overtime not recorded, or not in the Work Order, is not charged; one shift is
        # not several.
        ({**_TWO, "overtime_counted_per_code": "PER_SHIFT"}, "ck_wol_term_overtime_counted_per"),
        ({**_TWO, "overtime_rate_method_code": "NONE", "overtime_counted_per_code": "PER_DAY"}, "ck_wol_term_overtime_counted_per"),
        (
            {**_SHIFT, "shift_pattern_code": "NONE", "overtime_rate_method_code": "RATE_PER_HOUR", "overtime_rate_amount": Decimal("900"), "overtime_counted_per_code": "PER_DAY"},
            "ck_wol_term_overtime_counted_per",
        ),
        (
            {**_SHIFT, "shift_pattern_code": "ONE_SHIFT", "overtime_rate_method_code": "RATE_PER_HOUR", "overtime_rate_amount": Decimal("900"), "overtime_counted_per_code": "PER_DAY"},
            "ck_wol_term_overtime_counted_per",
        ),
        # The crew's upkeep.
        ({**_STATED, "upkeep_food_operator_code": "FREE"}, "ck_wol_term_upkeep_codes"),
        ({**_STATED, "upkeep_food_operator_code": "PROVIDED_AT_COST", "upkeep_food_operator_unit_code": "PER_WEEK"}, "ck_wol_term_upkeep_codes"),
        ({**_STATED, "upkeep_job_travel_helper_code": "PROVIDED_AT_COST", "upkeep_job_travel_helper_unit_code": "PER_PERSON_PER_DAY"}, "ck_wol_term_upkeep_codes"),
        ({**_STATED, "upkeep_daily_travel_helper_code": "PROVIDED_AT_COST", "upkeep_daily_travel_helper_recovery_code": "PAID_TO_WORKER"}, "ck_wol_term_upkeep_codes"),
        ({**_STATED, "upkeep_food_operator_code": "PROVIDED_AT_COST", "upkeep_food_operator_amount": Decimal("0")}, "ck_wol_term_upkeep_positive_values"),
        ({**_STATED, "upkeep_food_operator_code": "PROVIDED_AT_COST", "upkeep_food_operator_amount": Decimal("NaN")}, "ck_wol_term_upkeep_positive_values"),
        ({**_STATED, "upkeep_food_operator_amount": Decimal("120")}, "ck_wol_term_upkeep_cost_values"),
        ({**_STATED, "upkeep_accommodation_helper_code": "PROVIDED", "upkeep_accommodation_helper_unit_code": "PER_PERSON_PER_DAY"}, "ck_wol_term_upkeep_cost_values"),
        ({**_STATED, "upkeep_daily_travel_operator_code": "NONE", "upkeep_daily_travel_operator_unit_code": "PER_DAY"}, "ck_wol_term_upkeep_cost_values"),
        ({**_STATED, "upkeep_job_travel_operator_code": "NONE", "upkeep_job_travel_operator_recovery_code": "BILLED_SEPARATELY"}, "ck_wol_term_upkeep_cost_values"),
        ({**_SHIFT, "upkeep_food_operator_code": "PROVIDED"}, "ck_wol_term_upkeep_needs_crew"),
        ({**_SHIFT, "crew_code": "NONE", "upkeep_food_helper_code": "NONE"}, "ck_wol_term_upkeep_needs_crew"),
        ({**_STATED, "crew_helpers_per_unit": 0, "upkeep_food_helper_code": "NONE"}, "ck_wol_term_upkeep_role_present"),
        ({**_STATED, "crew_operators_per_unit": 0, "crew_helpers_per_unit": 1, "upkeep_daily_travel_operator_code": "PROVIDED"}, "ck_wol_term_upkeep_role_present"),
    ],
)
def test_the_database_refuses_a_part_5_term_written_directly(chain, columns: dict, constraint: str) -> None:
    """Each case names its constraint: a row breaking one rule often breaks another too, and a test that
    accepted any refusal would still pass with this one removed (Part 2's lesson)."""
    with pytest.raises(IntegrityError) as refusal:
        _insert_term_directly(chain["line_public_ids"][0], **columns)
    assert constraint in str(refusal.value)
    assert _line_terms(chain)["periods"] == []


@pytest.mark.parametrize(
    "columns",
    [
        {**_SHIFT, "shift_pattern_code": "NONE"},
        {**_SHIFT, "shift_pattern_code": "ONE_SHIFT", "shift_1_hours": Decimal("10")},
        {**_SHIFT, "shift_pattern_code": "ONE_SHIFT"},
        {**_TWO, "shift_1_hours": Decimal("16"), "shift_2_hours": Decimal("8"), "shift_rate_code": "SAME_FOR_ALL_SHIFTS"},
        {
            **_PER_SHIFT,
            "billing_uom_code": "MONTH",
            "shift_pattern_code": "THREE_SHIFTS",
            "shift_2_rate_method_code": "PERCENT_OF_NORMAL",
            "shift_2_rate_percent": Decimal("90"),
            "shift_2_working_days_per_month": Decimal("26"),
            "shift_3_rate_method_code": "RATE_PER_SHIFT",
            "shift_3_rate_amount": Decimal("4500"),
            "overtime_rate_method_code": "RATE_PER_HOUR",
            "overtime_rate_amount": Decimal("900"),
            "month_overtime_counting_code": "DAY_BY_DAY",
            "overtime_counted_per_code": "PER_DAY",
        },
        # Per shift or per day on a monthly line counted over the whole month (review round 1, 7D5-R1-001).
        {
            **_TWO,
            "billing_uom_code": "MONTH",
            "overtime_rate_method_code": "RATE_PER_HOUR",
            "overtime_rate_amount": Decimal("900"),
            "month_overtime_counting_code": "WHOLE_MONTH",
            "overtime_counted_per_code": "PER_SHIFT",
        },
        # Half-entered shapes are legal; they are reported missing, not refused.
        {**_TWO},
        {**_PER_SHIFT},
        {**_STATED, "crew_operators_per_unit": 2, "crew_helpers_per_unit": 0, "upkeep_food_operator_code": "PROVIDED"},
        {
            **_STATED,
            "upkeep_accommodation_operator_code": "PROVIDED_AT_COST",
            "upkeep_accommodation_operator_amount": Decimal("150"),
            "upkeep_accommodation_operator_unit_code": "PER_PERSON_PER_DAY",
            "upkeep_daily_travel_helper_code": "PROVIDED_AT_COST",
            "upkeep_daily_travel_helper_amount": Decimal("900"),
            "upkeep_daily_travel_helper_unit_code": "PER_DAY",
            "upkeep_daily_travel_helper_recovery_code": "BILLED_SEPARATELY",
            "upkeep_accommodation_operator_recovery_code": "DEDUCTED_FROM_INVOICE",
            "upkeep_job_travel_helper_code": "PROVIDED_AT_COST",
        },
    ],
)
def test_the_database_accepts_every_legal_part_5_shape_written_directly(chain, columns: dict) -> None:
    """The mirror of the refusals: every rule written to be TRUE or FALSE, never NULL, still lets a genuine
    row through, and the API reads it."""
    _insert_term_directly(chain["line_public_ids"][0], **columns)
    try:
        period = _line_terms(chain)["periods"][0]
        assert period["shift_pattern_code"] == columns.get("shift_pattern_code")
    finally:
        with SessionLocal() as db:
            db.execute(
                text(
                    "DELETE FROM crm_work_order_line_billing_term WHERE work_order_line_id IN "
                    "(SELECT id FROM crm_work_order_line WHERE work_order_line_public_id = :line)"
                ),
                {"line": chain["line_public_ids"][0]},
            )
            db.commit()
