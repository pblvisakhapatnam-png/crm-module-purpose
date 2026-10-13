"""Slice 7D Part 4 - extra kilometres, crew, and the monthly minimum-guarantee message.

Each test maps to an item in the "Test plan" of
docs/agent/slices/slice-7d-part-4-remaining-billing-terms.md. The owner's answers the rules come from
are 22, 23 and 26 of 17-18 September 2026, and decision 28 of 24 September 2026.

The three-line chain fixture is Part 3's and the request helpers are Part 1's, imported rather than
rebuilt: these terms are the same records, the same routes and the same conflict rules, with two more
groups of columns. The holiday list is tested in test_slice_7d_part_4_holidays.py.

Business events need no explicit cleanup: conftest removes every event created by the session.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.work_orders.contract import WORK_ORDER_LINE_TERMS_MISSING_ORDER
from tests.test_slice_7d_part_3_contract_period import (  # noqa: F401  (chain is a fixture)
    _billing_terms,
    _copy,
    chain,
)
from tests.test_slice_7d_work_order_line_billing_terms import (
    HOUR_TERMS,
    MONTH_OT_NORMAL_CUMULATIVE,
    PART_2_FIRST_PERIOD_ONLY,
    PART_4_EVERY_PERIOD,
    PART_5_CREW_UPKEEP_NONE,
    PART_5_CREW_UPKEEP_NONE_OPERATORS_ONLY,
    SHIFT_TERMS,
    _add,
    _insert_term_directly,
    _line_terms,
    _put,
)

# The two Part 4 groups, for a term set as it stood before Part 4.
_PART_4_PREFIXES = ("extra_km", "crew", "extra_crew")

EXTRA_KM_PER_DAY = {
    "extra_km_allowance_code": "KM_PER_DAY",
    "extra_km_included_km": "100.00",
    "extra_km_rate_amount": "45.00",
}
CREW_WITH_EXTRA_RATES = {
    "crew_code": "STATED",
    "crew_operators_per_unit": 2,
    "crew_helpers_per_unit": 2,
    "extra_crew_charge_code": "RATE_PER_PERSON",
    "extra_crew_operator_rate_amount": "1800.00",
    "extra_crew_helper_rate_amount": "900.00",
}
# A shift line with every Part 4 term answered in full - and, since Part 5, its crew's upkeep answered.
FULL_PART_4_SHIFT_TERMS = {
    **SHIFT_TERMS,
    **PART_2_FIRST_PERIOD_ONLY,
    **EXTRA_KM_PER_DAY,
    **CREW_WITH_EXTRA_RATES,
    **PART_5_CREW_UPKEEP_NONE,
}


def _before_part_4(terms: dict) -> dict:
    return {key: value for key, value in terms.items() if not key.startswith(_PART_4_PREFIXES)}


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


# --- Terms the API refuses -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [
        # Unknown codes in each new domain.
        {"extra_km_allowance_code": "KM_PER_WEEK"},
        {"crew_code": "YES"},
        {"crew_code": "STATED", "extra_crew_charge_code": "PER_SHIFT"},
        # Kilometres and a rate belong to an included allowance.
        {"extra_km_allowance_code": "NONE", "extra_km_included_km": "100.00"},
        {"extra_km_allowance_code": "NONE", "extra_km_rate_amount": "45.00"},
        {"extra_km_allowance_code": None, "extra_km_included_km": "100.00"},
        # Numbers and an extra-crew charge belong to a Work Order that states its crew.
        {"crew_code": "NONE", "crew_operators_per_unit": 2},
        {"crew_code": None, "crew_helpers_per_unit": 1},
        {"crew_code": "NONE", "extra_crew_charge_code": "NONE"},
        # No operators and no helpers is equipment only (owner decision 28).
        {"crew_code": "STATED", "crew_operators_per_unit": 0, "crew_helpers_per_unit": 0},
        # The extra-crew rates belong to a charge per extra person.
        {"crew_code": "STATED", "extra_crew_charge_code": "NONE", "extra_crew_operator_rate_amount": "1800.00"},
        {"crew_code": "STATED", "extra_crew_helper_rate_amount": "900.00"},
        # Values that are not positive, or not whole numbers of people.
        {**EXTRA_KM_PER_DAY, "extra_km_included_km": "0"},
        {**EXTRA_KM_PER_DAY, "extra_km_rate_amount": "-1"},
        {**CREW_WITH_EXTRA_RATES, "extra_crew_operator_rate_amount": "0"},
        {**CREW_WITH_EXTRA_RATES, "crew_operators_per_unit": -1},
        {**CREW_WITH_EXTRA_RATES, "crew_helpers_per_unit": 1.5},
        # An unknown field is refused rather than ignored, as in Parts 1 and 2.
        {"extra_km_rate": "45.00"},
    ],
)
def test_a_part_4_term_that_breaks_its_own_rule_is_refused(chain, change: dict) -> None:
    assert _add(chain, {**SHIFT_TERMS, **change}).status_code == 422
    assert _line_terms(chain)["periods"] == []


def test_both_numbers_zero_is_refused_with_a_message_that_says_what_to_record_instead(chain) -> None:
    response = _add(chain, {**SHIFT_TERMS, "crew_code": "STATED", "crew_operators_per_unit": 0, "crew_helpers_per_unit": 0})
    assert response.status_code == 422
    assert "equipment only" in response.json()["detail"]


def test_a_part_4_term_before_the_billing_basis_is_refused(chain) -> None:
    for change in ({"extra_km_allowance_code": "NONE"}, {"crew_code": "NONE"}):
        assert _add(chain, change).status_code == 422, change
    assert _line_terms(chain)["periods"] == []


def test_the_api_refuses_a_non_finite_number(chain) -> None:
    for value in ("NaN", "Infinity", "-Infinity"):
        refused = _add(chain, {**SHIFT_TERMS, **EXTRA_KM_PER_DAY, "extra_km_rate_amount": value})
        assert refused.status_code == 422, (value, refused.text)
    assert _line_terms(chain)["periods"] == []


# --- What is recorded ----------------------------------------------------------------------------


def test_a_full_part_4_term_set_is_recorded_and_complete(chain) -> None:
    response = _add(chain, FULL_PART_4_SHIFT_TERMS)
    assert response.status_code == 201, response.text
    period = response.json()["line_billing_terms"]["periods"][0]
    assert period["extra_km_allowance_code"] == "KM_PER_DAY"
    assert period["extra_km_included_km"] == "100.00"
    assert period["extra_km_rate_amount"] == "45.00"
    assert period["crew_code"] == "STATED"
    assert period["crew_operators_per_unit"] == 2
    assert period["crew_helpers_per_unit"] == 2
    assert period["extra_crew_charge_code"] == "RATE_PER_PERSON"
    assert period["extra_crew_operator_rate_amount"] == "1800.00"
    assert period["extra_crew_helper_rate_amount"] == "900.00"
    assert period["is_complete"] is True, period["missing_items"]


def test_one_of_the_two_numbers_may_be_zero(chain) -> None:
    """ "2 operators, no helpers" is a real answer (owner decision 28)."""
    terms = {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, **CREW_WITH_EXTRA_RATES, "crew_helpers_per_unit": 0}
    response = _add(chain, terms)
    assert response.status_code == 201, response.text
    period = response.json()["line_billing_terms"]["periods"][0]
    assert period["crew_helpers_per_unit"] == 0
    assert "CREW" not in period["missing_items"]


@pytest.mark.parametrize("helpers", [2_147_483_647, 1, None])
def test_the_largest_number_the_api_accepts_is_stored_not_a_server_error(chain, helpers) -> None:
    """The not-both-zero CHECK once added the two numbers, which overflowed an integer at the largest value
    the schema accepts and turned a valid save into a 500 (review round 1, finding F-01). It is now written
    without arithmetic. A missing helpers number still leaves crew reported missing, not refused."""
    terms = {**SHIFT_TERMS, "crew_code": "STATED", "crew_operators_per_unit": 2_147_483_647, "crew_helpers_per_unit": helpers}
    response = _add(chain, terms)
    assert response.status_code == 201, response.text
    period = response.json()["line_billing_terms"]["periods"][0]
    assert period["crew_operators_per_unit"] == 2_147_483_647
    assert period["crew_helpers_per_unit"] == helpers


def test_a_number_beyond_what_the_database_can_hold_is_refused_as_a_validation_error(chain) -> None:
    response = _add(chain, {**SHIFT_TERMS, "crew_code": "STATED", "crew_operators_per_unit": 2_147_483_648})
    assert response.status_code == 422
    assert _line_terms(chain)["periods"] == []


@pytest.mark.parametrize(
    "terms",
    [
        {
            **HOUR_TERMS,
            "crew_code": "STATED",
            "crew_operators_per_unit": 1,
            "crew_helpers_per_unit": 0,
            "extra_crew_charge_code": "NONE",
            **PART_5_CREW_UPKEEP_NONE_OPERATORS_ONLY,
        },
        {**MONTH_OT_NORMAL_CUMULATIVE, "extra_km_allowance_code": "KM_PER_MONTH", "extra_km_included_km": "3000.00", "extra_km_rate_amount": "40.00"},
    ],
)
def test_both_terms_apply_to_every_basis_hourly_and_monthly_included(chain, terms: dict) -> None:
    """Extra kilometres and crew are counted per billing unit of the line, whatever the unit is."""
    response = _add(chain, {**terms, **PART_2_FIRST_PERIOD_ONLY})
    assert response.status_code == 201, response.text
    assert response.json()["line_billing_terms"]["periods"][0]["is_complete"] is True


def test_not_in_the_work_order_counts_as_recorded_for_both_part_4_terms(chain) -> None:
    response = _add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY})
    assert response.status_code == 201, response.text
    period = response.json()["line_billing_terms"]["periods"][0]
    assert period["extra_km_allowance_code"] == "NONE"
    assert period["crew_code"] == "NONE"
    assert period["is_complete"] is True, period["missing_items"]


# --- What is reported missing --------------------------------------------------------------------


def test_a_period_saved_before_part_4_reports_just_the_two_new_terms_missing(chain) -> None:
    """Rows written before Part 4 hold neither term, so their lines report both missing - correct,
    because they were never recorded. The migration adds the columns as NULL."""
    response = _add(chain, _before_part_4({**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY}))
    assert response.status_code == 201, response.text
    period = response.json()["line_billing_terms"]["periods"][0]
    assert period["extra_km_allowance_code"] is None
    assert period["crew_code"] is None
    assert period["missing_items"] == ["EXTRA_KILOMETRES", "CREW"]


@pytest.mark.parametrize(
    "terms, expected",
    [
        ({"extra_km_allowance_code": "KM_PER_DAY"}, "EXTRA_KILOMETRES"),
        ({"extra_km_allowance_code": "KM_PER_MONTH", "extra_km_included_km": "3000.00"}, "EXTRA_KILOMETRES"),
        ({"extra_km_allowance_code": "KM_PER_DAY", "extra_km_rate_amount": "45.00"}, "EXTRA_KILOMETRES"),
        ({"crew_code": "STATED"}, "CREW"),
        ({"crew_code": "STATED", "crew_operators_per_unit": 2}, "CREW"),
        ({"crew_code": "STATED", "crew_operators_per_unit": 2, "crew_helpers_per_unit": 1}, "CREW"),
        ({**CREW_WITH_EXTRA_RATES, "extra_crew_helper_rate_amount": None}, "CREW"),
        ({**CREW_WITH_EXTRA_RATES, "extra_crew_operator_rate_amount": None}, "CREW"),
    ],
)
def test_a_choice_recorded_without_the_value_it_needs_is_reported_missing(chain, terms: dict, expected: str) -> None:
    """A value a recorded choice still needs is reported missing rather than refused, so a period can be
    filled in over several saves - the Part 2 rule."""
    response = _add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, **terms})
    assert response.status_code == 201, response.text
    period = response.json()["line_billing_terms"]["periods"][0]
    assert expected in period["missing_items"], period["missing_items"]
    assert period["is_complete"] is False


def test_the_two_new_items_are_reported_last_in_the_agreed_order(chain) -> None:
    # Part 5 added the crew's upkeep after them; it is asked only once the crew is stated.
    assert WORK_ORDER_LINE_TERMS_MISSING_ORDER[-3:] == ("EXTRA_KILOMETRES", "CREW", "CREW_UPKEEP")
    response = _add(chain, {"billing_uom_code": "SHIFT"})
    assert response.status_code == 201, response.text
    line = response.json()["line_billing_terms"]
    assert line["line_missing_items"][-2:] == ["EXTRA_KILOMETRES", "CREW"]
    assert line["line_missing_items"] == [item for item in WORK_ORDER_LINE_TERMS_MISSING_ORDER if item in line["line_missing_items"]]


# --- Answer 26: the monthly minimum-guarantee message ----------------------------------------------


def test_a_monthly_line_still_refuses_a_minimum_guarantee_with_the_corrected_reason(chain) -> None:
    """A monthly shortfall is charged pro rata with no minimum (owner, answer 26). The rule is unchanged;
    only the refusal's reason is corrected - it used to say the monthly rate covered the month."""
    response = _add(chain, {**MONTH_OT_NORMAL_CUMULATIVE, "minimum_guarantee_code": "NONE"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "pro rata, with no minimum" in detail
    assert "already covers" not in detail
    assert _line_terms(chain)["periods"] == []


# --- Events --------------------------------------------------------------------------------------


def test_no_part_4_value_reaches_an_event_payload(chain) -> None:
    response = _add(chain, FULL_PART_4_SHIFT_TERMS)
    assert response.status_code == 201, response.text
    payloads = _event_payloads(chain["work_order_public_id"], "WorkOrderLineBillingTermsPeriodAdded")
    assert payloads, "the added event was not recorded"
    for payload in payloads:
        text_of_payload = json.dumps(payload)
        for forbidden in ("100.00", "45.00", "1800.00", "900.00"):
            assert forbidden not in text_of_payload, forbidden
        for field in ("extra_km_allowance_code", "crew_code", "extra_crew_charge_code"):
            assert field in payload["changed_fields"]
        # The crew numbers are values too, even though they are small integers.
        assert 2 not in payload.values()


def test_changing_only_the_crew_names_just_the_crew_terms(chain) -> None:
    first = _add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY})
    assert first.status_code == 201, first.text
    period = first.json()["line_billing_terms"]["periods"][0]
    updated = _put(
        chain,
        period["term_public_id"],
        {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, **CREW_WITH_EXTRA_RATES},
        expected_term_revision=period["term_revision"],
    )
    assert updated.status_code == 200, updated.text
    changed = _event_payloads(chain["work_order_public_id"], "WorkOrderLineBillingTermsPeriodUpdated")[-1]["changed_fields"]
    assert set(changed) == {
        "crew_code",
        "crew_operators_per_unit",
        "crew_helpers_per_unit",
        "extra_crew_charge_code",
        "extra_crew_operator_rate_amount",
        "extra_crew_helper_rate_amount",
    }


# --- Copying terms between lines carries Part 4 with the rest ---------------------------------------


def test_applying_terms_to_other_lines_copies_the_part_4_terms_too(chain) -> None:
    assert _add(chain, FULL_PART_4_SHIFT_TERMS).status_code == 201
    response = _copy(chain, target_indexes=(1,))
    assert response.status_code == 200, response.text
    target = next(
        item for item in _billing_terms(chain) if item["work_order_line_public_id"] == chain["line_public_ids"][1]
    )
    period = target["periods"][0]
    assert period["extra_km_included_km"] == "100.00"
    assert period["crew_operators_per_unit"] == 2
    assert period["extra_crew_helper_rate_amount"] == "900.00"
    assert target["terms_complete"] is True


# --- What the database itself refuses ------------------------------------------------------------


@pytest.mark.parametrize(
    "columns, constraint",
    [
        ({"billing_uom_code": "SHIFT", "extra_km_allowance_code": "KM_PER_WEEK"}, "ck_wol_term_extra_km_code"),
        ({"billing_uom_code": "SHIFT", "crew_code": "YES"}, "ck_wol_term_crew_code"),
        (
            {"billing_uom_code": "SHIFT", "crew_code": "STATED", "extra_crew_charge_code": "PER_SHIFT"},
            "ck_wol_term_extra_crew_charge_code",
        ),
        (
            {"billing_uom_code": "SHIFT", "extra_km_allowance_code": "KM_PER_DAY", "extra_km_included_km": Decimal("0")},
            "ck_wol_term_p4_positive_values",
        ),
        (
            {"billing_uom_code": "SHIFT", "extra_km_allowance_code": "KM_PER_DAY", "extra_km_rate_amount": Decimal("NaN")},
            "ck_wol_term_p4_positive_values",
        ),
        (
            {
                "billing_uom_code": "SHIFT",
                "crew_code": "STATED",
                "extra_crew_charge_code": "RATE_PER_PERSON",
                "extra_crew_operator_rate_amount": Decimal("NaN"),
            },
            "ck_wol_term_p4_positive_values",
        ),
        (
            {"billing_uom_code": "SHIFT", "crew_code": "STATED", "crew_operators_per_unit": 0, "crew_helpers_per_unit": 0},
            "ck_wol_term_crew_counts",
        ),
        (
            {"billing_uom_code": "SHIFT", "crew_code": "STATED", "crew_operators_per_unit": -1},
            "ck_wol_term_crew_counts",
        ),
        (
            {"billing_uom_code": "SHIFT", "crew_code": "STATED", "crew_operators_per_unit": 3, "crew_helpers_per_unit": -1},
            "ck_wol_term_crew_counts",
        ),
        # A value without its own choice. Each row is otherwise legal, so the named constraint is the one
        # that fires - a test accepting any refusal would pass with the rule removed (the Part 2 lesson).
        ({"billing_uom_code": "SHIFT", "extra_km_included_km": Decimal("100")}, "ck_wol_term_extra_km_values"),
        (
            {"billing_uom_code": "SHIFT", "extra_km_allowance_code": "NONE", "extra_km_rate_amount": Decimal("45")},
            "ck_wol_term_extra_km_values",
        ),
        ({"billing_uom_code": "SHIFT", "crew_operators_per_unit": 2}, "ck_wol_term_crew_values"),
        ({"billing_uom_code": "SHIFT", "crew_code": "NONE", "extra_crew_charge_code": "NONE"}, "ck_wol_term_crew_values"),
        (
            {"billing_uom_code": "SHIFT", "crew_code": "STATED", "extra_crew_helper_rate_amount": Decimal("900")},
            "ck_wol_term_extra_crew_values",
        ),
        (
            {
                "billing_uom_code": "SHIFT",
                "crew_code": "STATED",
                "extra_crew_charge_code": "NONE",
                "extra_crew_operator_rate_amount": Decimal("1800"),
            },
            "ck_wol_term_extra_crew_values",
        ),
        # Neither term before the basis.
        ({"extra_km_allowance_code": "NONE"}, "ck_wol_term_p4_basis_chosen_first"),
        ({"crew_code": "NONE"}, "ck_wol_term_p4_basis_chosen_first"),
    ],
)
def test_the_database_refuses_a_part_4_term_written_directly(chain, columns: dict, constraint: str) -> None:
    with pytest.raises(IntegrityError) as refusal:
        _insert_term_directly(chain["line_public_ids"][0], **columns)
    assert constraint in str(refusal.value)
    assert _line_terms(chain)["periods"] == []


def test_the_database_accepts_every_legal_part_4_shape_written_directly(chain) -> None:
    """The mirror of the refusals: every rule written to be TRUE or FALSE, never NULL, must still let a
    genuine row through - including a half-entered crew, which is missing rather than illegal."""
    legal_rows = [
        {
            "billing_uom_code": "SHIFT",
            "extra_km_allowance_code": "KM_PER_MONTH",
            "extra_km_included_km": Decimal("3000"),
            "extra_km_rate_amount": Decimal("40"),
            "crew_code": "STATED",
            "crew_operators_per_unit": 2,
            "crew_helpers_per_unit": 0,
            "extra_crew_charge_code": "RATE_PER_PERSON",
            "extra_crew_operator_rate_amount": Decimal("1800"),
            "extra_crew_helper_rate_amount": Decimal("900"),
        },
        {"billing_uom_code": "HOUR", "extra_km_allowance_code": "NONE", "crew_code": "NONE"},
        {"billing_uom_code": "DAY", "crew_code": "STATED", "crew_operators_per_unit": 0},
        {"billing_uom_code": "DAY", "crew_code": "STATED", "crew_helpers_per_unit": 0},
        {"billing_uom_code": "DAY", "extra_km_allowance_code": "KM_PER_DAY"},
        # The largest integer on both sides: no arithmetic in the CHECK to overflow (finding F-01).
        {
            "billing_uom_code": "DAY",
            "crew_code": "STATED",
            "crew_operators_per_unit": 2_147_483_647,
            "crew_helpers_per_unit": 2_147_483_647,
        },
    ]
    for columns in legal_rows:
        _insert_term_directly(chain["line_public_ids"][0], **columns)
        assert len(_line_terms(chain)["periods"]) == 1, columns
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


def test_part_4_every_period_is_the_set_the_other_test_modules_use() -> None:
    """The constant the Part 1 test module merges into its complete term sets answers both new terms."""
    assert PART_4_EVERY_PERIOD == {"extra_km_allowance_code": "NONE", "crew_code": "NONE"}
