"""Slice 7D Part 2 - night shift, mobilisation, demobilisation and fuel tests.

Each test maps to an item in the "Part 2" test plan of
docs/agent/slices/slice-7d-work-order-line-billing-terms.md. Slice 7D Part 5 turned the night shift into
the shift pattern; its rules are tested in test_slice_7d_part_5_upkeep_and_shifts.py, and the term sets
here record a second shift at its own rate where they recorded a charged night shift.

The chain fixture and the request helpers are Part 1's, imported rather than rebuilt: these terms are
the same records, the same routes and the same conflict rules, with four more groups of columns. The
owner decisions the rules come from are 8 to 12 of 15 September 2026.

Business events need no explicit cleanup: conftest removes every event created by the session.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError

from app.core.database import SessionLocal
from tests.test_slice_7d_work_order_line_billing_terms import (  # noqa: F401  (chain is a fixture)
    PART_2_FIRST_PERIOD_ONLY,
    SHIFT_TERMS,
    _PART_1_ONLY_PREFIXES,
    _add,
    _insert_term_directly,
    _line_terms,
    _put,
    chain,
)

def _event_payloads(work_order_public_id: str, event_name: str) -> list[dict]:
    """Every payload that event recorded for this Work Order, oldest first."""
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT event_payload_json FROM business_event WHERE record_type = 'work_order' "
                "AND record_public_id = :id AND event_name = :name ORDER BY id ASC"
            ),
            {"id": work_order_public_id, "name": event_name},
        ).fetchall()
    return [row[0] if isinstance(row[0], dict) else json.loads(row[0]) for row in rows]


# A second shift charged per shift, with each shift's hours - Part 2's night shift, as Part 5 records it.
# Overtime is charged on these lines, so with two shifts the Work Order also says how it is counted.
SECOND_SHIFT_PER_SHIFT = {
    "shift_pattern_code": "TWO_SHIFTS",
    "shift_1_hours": "8.00",
    "shift_2_hours": "8.00",
    "shift_rate_code": "PER_SHIFT",
    "shift_2_rate_method_code": "RATE_PER_SHIFT",
    "shift_2_rate_amount": "9000.00",
    "overtime_counted_per_code": "PER_SHIFT",
}
MOBILISATION_CREDITED = {
    "mobilisation_charge_code": "CHARGED_CREDITED_AFTER_MONTHS",
    "mobilisation_charge_amount": "150000.00",
    "mobilisation_credit_after_months": 12,
}
DEMOBILISATION_WAIVED = {
    "demobilisation_charge_code": "CHARGED_WAIVED_AFTER_MONTHS",
    "demobilisation_charge_amount": "120000.00",
    "demobilisation_waived_after_months": 12,
}
FUEL_CUSTOMER = {
    "fuel_treatment_code": "CUSTOMER_SUPPLIED",
    "fuel_litres_per_working_hour": "12.00",
    "fuel_travel_allowance_code": "LITRES_PER_TRAVEL_HOUR",
    "fuel_litres_per_travel_hour": "8.00",
}
# The Annexure-7 hiring T&C, recorded in full: a shift line with a second shift charged per shift, a mobilisation
# charge credited back after a year, demobilisation waived after a year, and customer-supplied diesel.
ANNEXURE_7_SHIFT_TERMS = {
    **SHIFT_TERMS,
    **SECOND_SHIFT_PER_SHIFT,
    **MOBILISATION_CREDITED,
    **DEMOBILISATION_WAIVED,
    **FUEL_CUSTOMER,
}


# --- Terms the API refuses -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [
        # Unknown codes in each new domain.
        {"mobilisation_charge_code": "FREE"},
        {"demobilisation_charge_code": "FREE"},
        {"fuel_treatment_code": "SUPPLIED"},
        {"fuel_treatment_code": "PBL_SUPPLIED_CHARGED", "fuel_charge_method_code": "AT_COST"},
        {**FUEL_CUSTOMER, "fuel_travel_allowance_code": "LITRES_PER_KM"},
        # A mobilisation charge and its months belong to the choices that name them.
        {"mobilisation_charge_code": "NONE", "mobilisation_charge_amount": "150000.00"},
        {"mobilisation_charge_amount": "150000.00"},
        {"mobilisation_charge_code": "CHARGED", "mobilisation_charge_amount": "150000.00", "mobilisation_credit_after_months": 12},
        {"demobilisation_charge_code": "NONE", "demobilisation_charge_amount": "120000.00"},
        {"demobilisation_charge_code": "CHARGED", "demobilisation_charge_amount": "120000.00", "demobilisation_waived_after_months": 12},
        # Fuel values belong to their own choice.
        {"fuel_treatment_code": "PBL_SUPPLIED_INCLUDED", "fuel_charge_method_code": "ACTUAL_COST"},
        {"fuel_treatment_code": "PBL_SUPPLIED_CHARGED", "fuel_charge_method_code": "ACTUAL_COST", "fuel_rate_per_litre_amount": "95.50"},
        {"fuel_treatment_code": "PBL_SUPPLIED_INCLUDED", "fuel_litres_per_working_hour": "12.00"},
        {"fuel_treatment_code": "PBL_SUPPLIED_CHARGED", "fuel_charge_method_code": "ACTUAL_COST", "fuel_travel_allowance_code": "NONE"},
        {**FUEL_CUSTOMER, "fuel_travel_allowance_code": "NONE"},
        # Values that are not positive whole or decimal numbers.
        {"mobilisation_charge_code": "CHARGED", "mobilisation_charge_amount": "0"},
        {**MOBILISATION_CREDITED, "mobilisation_credit_after_months": 0},
        {**DEMOBILISATION_WAIVED, "demobilisation_waived_after_months": -1},
        {**FUEL_CUSTOMER, "fuel_litres_per_working_hour": "0"},
        {**FUEL_CUSTOMER, "fuel_litres_per_travel_hour": "0"},
        # An unknown field is refused rather than ignored, as in Part 1 - Part 2's night-shift fields
        # included, since Part 5 replaced them with the shift pattern.
        {"night_shift_rate": "9000.00"},
        {"night_shift_rate_method_code": "NONE"},
        {"night_shift_contracted_hours": "8.00"},
    ],
)
def test_a_part_2_term_that_breaks_its_own_rule_is_refused(chain, change: dict) -> None:
    assert _add(chain, {**SHIFT_TERMS, **change}).status_code == 422
    assert _line_terms(chain)["periods"] == []


def test_a_term_before_the_billing_basis_is_refused(chain) -> None:
    for change in (
        {"mobilisation_charge_code": "NONE"},
        {"demobilisation_charge_code": "NONE"},
        {"fuel_treatment_code": "NONE"},
    ):
        assert _add(chain, change).status_code == 422, change
    assert _line_terms(chain)["periods"] == []


# --- Mobilisation and demobilisation belong to the line's first period ---------------------------


def test_mobilisation_is_recorded_on_the_first_period(chain) -> None:
    response = _add(chain, ANNEXURE_7_SHIFT_TERMS)
    assert response.status_code == 201, response.text
    period = response.json()["line_billing_terms"]["periods"][0]
    assert period["mobilisation_charge_code"] == "CHARGED_CREDITED_AFTER_MONTHS"
    assert period["mobilisation_charge_amount"] == "150000.00"
    assert period["mobilisation_credit_after_months"] == 12
    assert period["demobilisation_waived_after_months"] == 12
    assert period["fuel_litres_per_travel_hour"] == "8.00"


def test_a_later_period_cannot_carry_mobilisation_or_demobilisation(chain) -> None:
    first = _add(chain, ANNEXURE_7_SHIFT_TERMS)
    assert first.status_code == 201, first.text

    refused = _add(
        chain,
        {**SHIFT_TERMS, **MOBILISATION_CREDITED},
        expected_period_count=1,
        effective_from="2027-03-01",
    )
    assert refused.status_code == 422
    assert "first period" in refused.json()["detail"]
    assert len(_line_terms(chain)["periods"]) == 1

    # Without them, the later period is accepted and reports nothing missing about them.
    accepted = _add(chain, SHIFT_TERMS, expected_period_count=1, effective_from="2027-03-01")
    assert accepted.status_code == 201, accepted.text
    later = accepted.json()["line_billing_terms"]["periods"][1]
    assert later["mobilisation_charge_code"] is None
    assert "MOBILISATION" not in later["missing_items"]
    assert "DEMOBILISATION" not in later["missing_items"]


def test_editing_a_later_period_cannot_add_mobilisation(chain) -> None:
    assert _add(chain, ANNEXURE_7_SHIFT_TERMS).status_code == 201
    added = _add(chain, SHIFT_TERMS, expected_period_count=1, effective_from="2027-03-01")
    assert added.status_code == 201, added.text
    second = added.json()["line_billing_terms"]["periods"][1]

    refused = _put(
        chain,
        second["term_public_id"],
        {**SHIFT_TERMS, "mobilisation_charge_code": "CHARGED", "mobilisation_charge_amount": "150000.00"},
        expected_term_revision=second["term_revision"],
        effective_from="2027-03-01",
    )
    assert refused.status_code == 422
    assert "first period" in refused.json()["detail"]


def test_the_first_period_keeps_its_own_mobilisation_when_a_later_period_is_added(chain) -> None:
    assert _add(chain, ANNEXURE_7_SHIFT_TERMS).status_code == 201
    added = _add(chain, SHIFT_TERMS, expected_period_count=1, effective_from="2027-03-01")
    assert added.status_code == 201, added.text
    periods = added.json()["line_billing_terms"]["periods"]
    assert periods[0]["mobilisation_charge_amount"] == "150000.00"
    assert periods[1]["mobilisation_charge_amount"] is None


# --- Completeness -------------------------------------------------------------------------------


def test_the_annexure_7_hiring_terms_record_and_report_complete(chain) -> None:
    response = _add(chain, ANNEXURE_7_SHIFT_TERMS)
    assert response.status_code == 201, response.text
    entry = response.json()["line_billing_terms"]
    assert entry["terms_complete"] is True, entry["line_missing_items"]


@pytest.mark.parametrize(
    ("terms", "expected"),
    [
        # Charged mobilisation still needs its amount.
        ({"mobilisation_charge_code": "CHARGED"}, "MOBILISATION"),
        # Credited mobilisation still needs the months.
        ({"mobilisation_charge_code": "CHARGED_CREDITED_AFTER_MONTHS", "mobilisation_charge_amount": "150000.00"}, "MOBILISATION"),
        ({"demobilisation_charge_code": "CHARGED"}, "DEMOBILISATION"),
        (
            {"demobilisation_charge_code": "CHARGED_WAIVED_AFTER_MONTHS", "demobilisation_charge_amount": "120000.00"},
            "DEMOBILISATION",
        ),
        # Fuel charged by PBL still needs how, and an agreed rate still needs the rate.
        ({"fuel_treatment_code": "PBL_SUPPLIED_CHARGED"}, "FUEL"),
        ({"fuel_treatment_code": "PBL_SUPPLIED_CHARGED", "fuel_charge_method_code": "AGREED_RATE_PER_LITRE"}, "FUEL"),
        # Customer-supplied fuel needs the litres and an answer about travelling.
        ({"fuel_treatment_code": "CUSTOMER_SUPPLIED", "fuel_travel_allowance_code": "NONE"}, "FUEL"),
        ({"fuel_treatment_code": "CUSTOMER_SUPPLIED", "fuel_litres_per_working_hour": "12.00"}, "FUEL"),
        (
            {
                "fuel_treatment_code": "CUSTOMER_SUPPLIED",
                "fuel_litres_per_working_hour": "12.00",
                "fuel_travel_allowance_code": "LITRES_PER_TRAVEL_HOUR",
            },
            "FUEL",
        ),
    ],
)
def test_a_choice_recorded_without_the_value_it_needs_is_reported_missing(chain, terms: dict, expected: str) -> None:
    # Start from the complete set with the group under test emptied, then record it half-filled.
    prefix = expected.lower()
    emptied = {key: (None if key.startswith(prefix) else value) for key, value in ANNEXURE_7_SHIFT_TERMS.items()}
    response = _add(chain, {**emptied, **terms})
    assert response.status_code == 201, response.text
    period = response.json()["line_billing_terms"]["periods"][0]
    assert expected in period["missing_items"], period["missing_items"]
    assert period["is_complete"] is False


def test_not_in_the_work_order_counts_as_recorded_for_every_part_2_term(chain) -> None:
    response = _add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY})
    assert response.status_code == 201, response.text
    period = response.json()["line_billing_terms"]["periods"][0]
    for item in ("SHIFTS", "MOBILISATION", "DEMOBILISATION", "FUEL"):
        assert item not in period["missing_items"]
    assert period["is_complete"] is True, period["missing_items"]


def test_a_part_1_era_period_reports_the_new_terms_as_missing(chain) -> None:
    """Rows written before Part 2 hold no Part 2 term, so their lines report them missing - correct,
    because those terms were never recorded. The migration adds the columns as NULL."""
    part_1_only = {key: value for key, value in SHIFT_TERMS.items() if not key.startswith(_PART_1_ONLY_PREFIXES)}
    response = _add(chain, part_1_only)
    assert response.status_code == 201, response.text
    period = response.json()["line_billing_terms"]["periods"][0]
    assert period["shift_pattern_code"] is None
    assert period["fuel_treatment_code"] is None
    assert period["missing_items"] == ["SHIFTS", "MOBILISATION", "DEMOBILISATION", "FUEL"]


# --- Events -------------------------------------------------------------------------------------


def test_no_part_2_value_reaches_an_event_payload(chain) -> None:
    response = _add(chain, ANNEXURE_7_SHIFT_TERMS)
    assert response.status_code == 201, response.text
    payloads = _event_payloads(chain["work_order_public_id"], "WorkOrderLineBillingTermsPeriodAdded")
    assert payloads, "the added event was not recorded"
    for payload in payloads:
        # The values themselves are commercial data and never leave the record.
        for forbidden in ("9000.00", "150000.00", "120000.00", "12.00", "8.00", "130.00"):
            assert forbidden not in json.dumps(payload), forbidden
        assert payload["changed_fields"], "changed_fields should name what was recorded"
        for field in ("shift_2_rate_method_code", "mobilisation_charge_code", "fuel_treatment_code"):
            assert field in payload["changed_fields"]
        # The month counts are values too, even though they are small integers.
        assert 12 not in payload.values()


def test_changing_only_a_part_2_term_names_just_that_term(chain) -> None:
    first = _add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY})
    assert first.status_code == 201, first.text
    period = first.json()["line_billing_terms"]["periods"][0]

    updated = _put(
        chain,
        period["term_public_id"],
        {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, **FUEL_CUSTOMER},
        expected_term_revision=period["term_revision"],
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["event"]["event_name"] == "WorkOrderLineBillingTermsPeriodUpdated"
    changed = _event_payloads(chain["work_order_public_id"], "WorkOrderLineBillingTermsPeriodUpdated")[-1]["changed_fields"]
    assert set(changed) == {
        "fuel_treatment_code",
        "fuel_litres_per_working_hour",
        "fuel_travel_allowance_code",
        "fuel_litres_per_travel_hour",
    }


# --- What the database itself refuses ------------------------------------------------------------


@pytest.mark.parametrize(
    "columns",
    [
        # Code domains.
        {"billing_uom_code": "SHIFT", "mobilisation_charge_code": "FREE"},
        {"billing_uom_code": "SHIFT", "demobilisation_charge_code": "FREE"},
        {"billing_uom_code": "SHIFT", "fuel_treatment_code": "SUPPLIED"},
        {"billing_uom_code": "SHIFT", "fuel_treatment_code": "PBL_SUPPLIED_CHARGED", "fuel_charge_method_code": "AT_COST"},
        {"billing_uom_code": "SHIFT", "fuel_treatment_code": "CUSTOMER_SUPPLIED", "fuel_travel_allowance_code": "PER_KM"},
        # Mobilisation and demobilisation values without the choice that names them.
        {"billing_uom_code": "SHIFT", "mobilisation_charge_amount": Decimal("150000")},
        {"billing_uom_code": "SHIFT", "mobilisation_charge_code": "CHARGED", "mobilisation_credit_after_months": 12},
        {"billing_uom_code": "SHIFT", "demobilisation_charge_amount": Decimal("120000")},
        {"billing_uom_code": "SHIFT", "demobilisation_charge_code": "CHARGED", "demobilisation_waived_after_months": 12},
        # A month count must be at least one whole month.
        {
            "billing_uom_code": "SHIFT",
            "mobilisation_charge_code": "CHARGED_CREDITED_AFTER_MONTHS",
            "mobilisation_charge_amount": Decimal("150000"),
            "mobilisation_credit_after_months": 0,
        },
        # Fuel values without their own choice.
        {"billing_uom_code": "SHIFT", "fuel_charge_method_code": "ACTUAL_COST"},
        {"billing_uom_code": "SHIFT", "fuel_treatment_code": "PBL_SUPPLIED_CHARGED", "fuel_charge_method_code": "ACTUAL_COST", "fuel_rate_per_litre_amount": Decimal("95.50")},
        {"billing_uom_code": "SHIFT", "fuel_litres_per_working_hour": Decimal("12")},
        {"billing_uom_code": "SHIFT", "fuel_treatment_code": "PBL_SUPPLIED_INCLUDED", "fuel_travel_allowance_code": "NONE"},
        {"billing_uom_code": "SHIFT", "fuel_treatment_code": "CUSTOMER_SUPPLIED", "fuel_travel_allowance_code": "NONE", "fuel_litres_per_travel_hour": Decimal("8")},
        # A term before the basis.
        {"fuel_treatment_code": "NONE"},
        {"mobilisation_charge_code": "NONE"},
        # Mobilisation on a later period. The date is a real one: a later period with no date is already
        # refused by Part 1's own CHECK, so an undated row here would pass this test even with Part 2's
        # first-period-only CHECK removed. The test below names the constraint, for the same reason.
        {"period_number": 2, "effective_from": date(2027, 3, 1), "billing_uom_code": "SHIFT", "mobilisation_charge_code": "NONE"},
        # NaN and Infinity, which are numeric values greater than zero as far as `> 0` is concerned.
        # NaN, which a numeric column does store and which compares greater than every number, so only
            # the CHECK refuses it. (Infinity is refused earlier, by the column's own precision - see the
            # test below.)
        {"billing_uom_code": "SHIFT", "mobilisation_charge_code": "CHARGED", "mobilisation_charge_amount": Decimal("NaN")},
        {
            "billing_uom_code": "SHIFT",
            "fuel_treatment_code": "PBL_SUPPLIED_CHARGED",
            "fuel_charge_method_code": "AGREED_RATE_PER_LITRE",
            "fuel_rate_per_litre_amount": Decimal("NaN"),
        },
        {"billing_uom_code": "SHIFT", "fuel_treatment_code": "CUSTOMER_SUPPLIED", "fuel_litres_per_working_hour": Decimal("NaN")},
    ],
)
def test_the_database_refuses_a_part_2_term_written_directly(chain, columns: dict) -> None:
    with pytest.raises(IntegrityError):
        _insert_term_directly(chain["line_public_ids"][0], **columns)
    assert _line_terms(chain)["periods"] == []


def test_the_first_period_only_check_is_the_one_that_refuses_a_later_period(chain) -> None:
    """Names the constraint rather than accepting any IntegrityError. A row breaking a line-once rule
    usually breaks a Part 1 rule too - a later period must be dated, for one - so a test that accepts any
    refusal would still pass with this CHECK dropped, and the rule could be removed unnoticed."""
    with pytest.raises(IntegrityError) as refusal:
        _insert_term_directly(
            chain["line_public_ids"][0],
            period_number=2,
            effective_from=date(2027, 3, 1),
            billing_uom_code="SHIFT",
            demobilisation_charge_code="NONE",
        )
    assert "ck_wol_term_first_period_only_terms" in str(refusal.value)
    assert _line_terms(chain)["periods"] == []


@pytest.mark.parametrize(
    "columns",
    [
        {"billing_uom_code": "SHIFT", "demobilisation_charge_code": "CHARGED", "demobilisation_charge_amount": Decimal("Infinity")},
        {
            "billing_uom_code": "SHIFT",
            "fuel_treatment_code": "CUSTOMER_SUPPLIED",
            "fuel_litres_per_working_hour": Decimal("12"),
            "fuel_travel_allowance_code": "LITRES_PER_TRAVEL_HOUR",
            "fuel_litres_per_travel_hour": Decimal("Infinity"),
        },
    ],
)
def test_the_database_refuses_an_infinite_value_written_directly(chain, columns: dict) -> None:
    """Each of these columns is a numeric with a declared precision, and such a column cannot hold
    +/-Infinity at all: PostgreSQL refuses it as out of range (a DataError) before any CHECK is
    evaluated. The CHECKs still exclude Infinity, so the rule holds if a later column is ever declared
    without a precision; this test records which refusal actually fires today."""
    with pytest.raises((DataError, IntegrityError)):
        _insert_term_directly(chain["line_public_ids"][0], **columns)
    assert _line_terms(chain)["periods"] == []


def test_the_api_refuses_a_non_finite_number(chain) -> None:
    """Through the API the schema refuses NaN and Infinity alike, before the database sees either."""
    for value in ("NaN", "Infinity", "-Infinity"):
        refused = _add(chain, {**SHIFT_TERMS, **SECOND_SHIFT_PER_SHIFT, "shift_2_rate_amount": value})
        assert refused.status_code == 422, (value, refused.text)
    assert _line_terms(chain)["periods"] == []


def test_the_database_accepts_the_full_annexure_7_term_set_written_directly(chain) -> None:
    """The mirror of the refusals above: every rule written to be TRUE or FALSE, never NULL, must still
    let a genuine complete row through."""
    _insert_term_directly(
        chain["line_public_ids"][0],
        billing_uom_code="SHIFT",
        contracted_hours_per_billing_unit=Decimal("8"),
        normal_rate_amount=Decimal("12000"),
        shift_pattern_code="TWO_SHIFTS",
        shift_1_hours=Decimal("8"),
        shift_2_hours=Decimal("8"),
        shift_rate_code="PER_SHIFT",
        shift_2_rate_method_code="RATE_PER_SHIFT",
        shift_2_rate_amount=Decimal("9000"),
        mobilisation_charge_code="CHARGED_CREDITED_AFTER_MONTHS",
        mobilisation_charge_amount=Decimal("150000"),
        mobilisation_credit_after_months=12,
        demobilisation_charge_code="CHARGED_WAIVED_AFTER_MONTHS",
        demobilisation_charge_amount=Decimal("120000"),
        demobilisation_waived_after_months=12,
        fuel_treatment_code="CUSTOMER_SUPPLIED",
        fuel_litres_per_working_hour=Decimal("12"),
        fuel_travel_allowance_code="LITRES_PER_TRAVEL_HOUR",
        fuel_litres_per_travel_hour=Decimal("8"),
    )
    period = _line_terms(chain)["periods"][0]
    assert period["shift_2_rate_amount"] == "9000.00"
    assert period["mobilisation_credit_after_months"] == 12
    _delete_terms(chain["line_public_ids"][0])


def _delete_terms(line_public_id: str) -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                """
                DELETE FROM crm_work_order_line_billing_term
                WHERE work_order_line_id IN (
                    SELECT id FROM crm_work_order_line WHERE work_order_line_public_id = :line_public_id
                )
                """
            ),
            {"line_public_id": line_public_id},
        )
        db.commit()


# --- The work_orders boundary --------------------------------------------------------------------


def test_the_handoff_still_writes_no_billing_term_row(chain) -> None:
    """The frozen handoff creates the Work Order and its lines and nothing else - Part 1 proves this for
    its own columns; this proves Part 2 added no write to that path."""
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT COUNT(*) FROM crm_work_order_line_billing_term t
                INNER JOIN crm_work_order_line wol ON wol.id = t.work_order_line_id
                INNER JOIN crm_work_order wo ON wo.id = wol.work_order_id
                WHERE wo.work_order_public_id = :work_order_public_id
                """
            ),
            {"work_order_public_id": chain["work_order_public_id"]},
        ).scalar_one()
    assert rows == 0
