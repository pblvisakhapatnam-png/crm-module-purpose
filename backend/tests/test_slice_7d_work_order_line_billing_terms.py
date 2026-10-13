"""Slice 7D Part 1 - Work Order line billing terms tests.

Each test maps to an item in the "Test plan" section of
docs/agent/slices/slice-7d-work-order-line-billing-terms.md. The fixture builds a real chain through
the existing API helpers (Lead -> Account -> Opportunity -> accepted Commercial Offer -> Work Order).

The billing basis and contracted hours moved here from the Slice 7C line detail; the rules that used
to be tested in test_slice_7c_work_order_line_detail.py are tested below.

Business events need no explicit cleanup: conftest removes every event created by the session.
"""

from __future__ import annotations

import json
import threading
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.work_orders import service as work_orders_service
from app.modules.work_orders.contract import WORK_ORDER_LINE_UPKEEP_CELLS
from app.modules.work_orders.schemas import (
    WorkOrderLineBillingTermsPeriodCreate,
    WorkOrderLineBillingTermsPeriodUpdate,
)

# The writes look their repository functions up in the module they are defined in, so a test that
# swaps one must patch it there; patching the re-exporting service module changes nothing (TE-6).
from app.modules.work_orders.services import billing_terms as billing_terms_service
from tests.business_day_test_support import TODAY, held_to_the_test_day
from tests.test_commercial_offers_api import (
    auth_headers,
    cleanup_test_records,
    cleanup_test_work_orders,
    client,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    create_test_offer_line,
    create_test_supplementary_work_order,
    mark_test_commercial_offer_submitted,
    record_test_customer_response,
)


# Slice 7D Part 2 added four more terms. The Annexure-10 examples state none of them - their
# night-shift rows are zero and they say nothing about mobilisation, demobilisation or fuel - so a term
# set built from those examples answers each with "not in the Work Order", and only then is it the
# complete set its calculation reads.
#
# They divide in two, because they are recorded in different places. Night shift and fuel belong to every
# period, so the term-set constants below carry them - the night shift, since Slice 7D Part 5, as the shift
# pattern "not in the Work Order" (no shifts stated). A stored Part 2 night shift "not in the Work Order" is not mapped
# to it: the migration asks for the shift pattern again and keeps that answer on the period. Mobilisation and demobilisation belong to the
# line's first period only - a later period carrying them is refused - so they are merged in separately,
# wherever a test asserts a complete first period.
PART_2_EVERY_PERIOD = {
    "shift_pattern_code": "NONE",
    "fuel_treatment_code": "NONE",
}
# An hourly line has no shift pattern at all, so it must not carry even a "not in the Work Order" answer.
PART_2_EVERY_PERIOD_HOURLY = {
    key: value for key, value in PART_2_EVERY_PERIOD.items() if key != "shift_pattern_code"
}
PART_2_FIRST_PERIOD_ONLY = {
    "mobilisation_charge_code": "NONE",
    "demobilisation_charge_code": "NONE",
}
# The Part 2 groups, for a test that needs a term set as Part 1 would have written it.
_PART_1_ONLY_PREFIXES = ("shift_", "mobilisation", "demobilisation", "fuel")

# Slice 7D Part 4 added two more terms that every period answers on every basis, hourly included:
# extra kilometres and crew. The Annexure-10 examples state neither, so a complete term set built from
# them answers both with "not in the Work Order", exactly as Part 2's terms are answered above.
PART_4_EVERY_PERIOD = {
    "extra_km_allowance_code": "NONE",
    "crew_code": "NONE",
}

# Slice 7D Part 5 asks, once the Work Order states its crew, about the crew's food, accommodation and travel
# for operators and for helpers. A term set that states its crew answers each with "not in the Work Order";
# the sets above record equipment only, which is asked nothing.
PART_5_CREW_UPKEEP_NONE = {str(cell["code"]): "NONE" for cell in WORK_ORDER_LINE_UPKEEP_CELLS}
PART_5_CREW_UPKEEP_NONE_OPERATORS_ONLY = {
    str(cell["code"]): "NONE" for cell in WORK_ORDER_LINE_UPKEEP_CELLS if cell["role"] == "operator"
}

# The six Annexure-10 worked examples, each recorded as the complete term set its calculation reads.
HOUR_TERMS = {
    "billing_uom_code": "HOUR",
    "normal_rate_amount": "1500.00",
    "customer_idle_treatment_code": "AS_WORKING_HOURS",
    "minimum_guarantee_code": "NONE",
    **PART_2_EVERY_PERIOD_HOURLY,
    **PART_4_EVERY_PERIOD,
}
SHIFT_TERMS = {
    "billing_uom_code": "SHIFT",
    "contracted_hours_per_billing_unit": "8.00",
    "normal_rate_amount": "12000.00",
    "weekly_off_day_codes": ["SUN"],
    "off_day_work_treatment_code": "OVERTIME_RATE",
    "overtime_rate_method_code": "RATE_PER_HOUR",
    "overtime_rate_amount": "1800.00",
    "breakdown_treatment_code": "REDUCE_BILLED_HOURS",
    "customer_idle_treatment_code": "AS_WORKING_HOURS",
    "minimum_guarantee_code": "NONE",
    **PART_2_EVERY_PERIOD,
    **PART_4_EVERY_PERIOD,
}
DAY_TERMS = {**SHIFT_TERMS, "billing_uom_code": "DAY", "contracted_hours_per_billing_unit": "12.00"}
MONTH_OT_NORMAL_CUMULATIVE = {
    "billing_uom_code": "MONTH",
    "contracted_hours_per_billing_unit": "260.00",
    "contracted_working_days_per_month": "26.00",
    "normal_rate_amount": "100000.00",
    "weekly_off_day_codes": ["SUN"],
    "off_day_work_treatment_code": "OVERTIME_RATE",
    "overtime_rate_method_code": "PERCENT_OF_NORMAL",
    "overtime_rate_percent": "125.00",
    "month_overtime_hours_basis_code": "AVAILABLE_HOURS",
    "month_overtime_counting_code": "WHOLE_MONTH",
    "breakdown_treatment_code": "REDUCE_BILLED_HOURS",
    "customer_idle_treatment_code": "AS_WORKING_HOURS",
    "part_month_basis_code": "CALENDAR_DAYS",
    **PART_2_EVERY_PERIOD,
    **PART_4_EVERY_PERIOD,
}
MONTH_OT_ENGINE_CUMULATIVE = {**MONTH_OT_NORMAL_CUMULATIVE, "month_overtime_hours_basis_code": "ENGINE_HOURS"}
MONTH_NON_CUMULATIVE = {
    **MONTH_OT_NORMAL_CUMULATIVE,
    "month_overtime_counting_code": "DAY_BY_DAY",
    "breakdown_treatment_code": "DEDUCT_AT_BREAKDOWN_RATE",
    "breakdown_rate_method_code": "RATE_PER_HOUR",
    "breakdown_rate_amount": "385.00",
}
ANNEXURE_10_TERM_SETS = {
    "hour-wise": HOUR_TERMS,
    "shift-wise": SHIFT_TERMS,
    "day-wise": DAY_TERMS,
    "month cumulative OT normal hours": MONTH_OT_NORMAL_CUMULATIVE,
    "month cumulative OT engine hours": MONTH_OT_ENGINE_CUMULATIVE,
    "month non-cumulative": MONTH_NON_CUMULATIVE,
}
EVENT_PAYLOAD_KEYS = {
    "work_order_line_public_id",
    "term_public_id",
    "period_number",
    "effective_from",
    "term_revision",
    "billing_uom_code",
    "changed_fields",
}


@pytest.fixture(scope="module", autouse=True)
def _on_the_test_day():
    with held_to_the_test_day():
        yield


@pytest.fixture
def chain():
    """An accepted Work Order with its lines copied from the offer."""
    record: dict[str, object] = {"work_order_public_ids": [], "supplementary_offer_public_ids": []}
    linked = create_account_linked_test_opportunity()
    record.update(
        lead_public_id=str(linked["lead"]["public_id"]),
        account_public_id=str(linked["account"]["public_id"]),
        opportunity_public_id=str(linked["opportunity"]["public_id"]),
    )
    try:
        offer = create_test_commercial_offer(record["opportunity_public_id"])
        record["offer_public_id"] = str(offer["public_id"])
        create_test_offer_line(record["offer_public_id"])
        mark_test_commercial_offer_submitted(record["offer_public_id"])
        record_test_customer_response(record["offer_public_id"], "ACCEPTED_AWARDED", received_at="2026-09-14T10:00:00Z")
        handoff = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={"commercial_offer_public_id": record["offer_public_id"], "customer_wo_reference": f"CUST-{uuid4()}"},
        )
        assert handoff.status_code == 201, handoff.text
        work_order_public_id = str(handoff.json()["work_order"]["public_id"])
        record["work_order_public_id"] = work_order_public_id
        record["work_order_public_ids"].append(work_order_public_id)
        record["line_public_ids"] = [str(line["public_id"]) for line in handoff.json()["lines"]]
        yield record
    finally:
        cleanup_test_work_orders(record["work_order_public_ids"])
        cleanup_test_records(
            opportunity_public_ids=[record["opportunity_public_id"]],
            offer_public_ids=[*record["supplementary_offer_public_ids"], record["offer_public_id"]]
            if "offer_public_id" in record
            else [],
            account_public_ids=[record["account_public_id"]],
            lead_public_ids=[record["lead_public_id"]],
        )


def _terms_url(chain, line_index: int = 0, term_public_id: str | None = None, work_order_public_id: str | None = None) -> str:
    work_order = work_order_public_id or chain["work_order_public_id"]
    url = f"/api/work-orders/{work_order}/lines/{chain['line_public_ids'][line_index]}/billing-terms"
    return f"{url}/{term_public_id}" if term_public_id else url


def _add(
    chain,
    terms: dict,
    *,
    expected_period_count: int = 0,
    expected_latest_term_revision: int | None = None,
    effective_from: str | None = None,
    username: str = "sales1",
    line_index: int = 0,
):
    # Unless told otherwise, the caller last saw the latest period at revision 1.
    if expected_latest_term_revision is None and expected_period_count > 0:
        expected_latest_term_revision = 1
    body = {
        "expected_period_count": expected_period_count,
        "expected_latest_term_revision": expected_latest_term_revision,
        "effective_from": effective_from,
        **terms,
    }
    return client.post(_terms_url(chain, line_index), headers=auth_headers(username), json=body)


def _put(chain, term_public_id: str, terms: dict, *, expected_term_revision: int, effective_from: str | None = None, username: str = "sales1"):
    body = {"expected_term_revision": expected_term_revision, "effective_from": effective_from, **terms}
    return client.put(_terms_url(chain, 0, term_public_id), headers=auth_headers(username), json=body)


def _remove(chain, term_public_id: str, *, expected_term_revision: int, username: str = "sales1"):
    return client.delete(
        _terms_url(chain, 0, term_public_id),
        headers=auth_headers(username),
        params={"expected_term_revision": expected_term_revision},
    )


def _line_terms(chain, username: str = "sales1", line_index: int = 0) -> dict:
    response = client.get(f"/api/work-orders/{chain['work_order_public_id']}/billing-terms", headers=auth_headers(username))
    assert response.status_code == 200, response.text
    return response.json()[line_index]


def _event_count(work_order_public_id: str, event_name: str) -> int:
    with SessionLocal() as db:
        return int(
            db.execute(
                text(
                    "SELECT COUNT(*) FROM business_event WHERE record_type = 'work_order' "
                    "AND record_public_id = :id AND event_name = :name"
                ),
                {"id": work_order_public_id, "name": event_name},
            ).scalar_one()
        )


def _three_periods(chain, second_from: str, third_from: str) -> list[dict]:
    first = _add(chain, SHIFT_TERMS)
    assert first.status_code == 201, first.text
    second = _add(chain, SHIFT_TERMS, expected_period_count=1, effective_from=second_from)
    assert second.status_code == 201, second.text
    third = _add(chain, SHIFT_TERMS, expected_period_count=2, effective_from=third_from)
    assert third.status_code == 201, third.text
    return third.json()["line_billing_terms"]["periods"]


# --- Periods ---------------------------------------------------------------------------------


def test_a_first_period_is_period_one_at_revision_one_and_records_the_added_event(chain) -> None:
    response = _add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY})
    assert response.status_code == 201, response.text
    body = response.json()
    entry = body["line_billing_terms"]
    assert len(entry["periods"]) == 1
    period = entry["periods"][0]
    assert (period["period_number"], period["term_revision"], period["effective_from"]) == (1, 1, None)
    assert period["currency_code"] == "INR"
    assert Decimal(period["contracted_hours_per_billing_unit"]) == Decimal("8.00")
    assert period["updated_by_display_name"]
    assert entry["terms_complete"] is True
    assert entry["current_period_number"] == 1
    assert body["event"]["event_name"] == "WorkOrderLineBillingTermsPeriodAdded"
    assert _event_count(chain["work_order_public_id"], "WorkOrderLineBillingTermsPeriodAdded") == 1


def test_a_first_period_with_a_date_and_a_later_period_without_one_are_refused(chain) -> None:
    dated_first = _add(chain, SHIFT_TERMS, effective_from="2027-01-01")
    assert dated_first.status_code == 422
    assert "starts with the contract" in dated_first.json()["detail"]
    assert _add(chain, SHIFT_TERMS).status_code == 201
    undated_later = _add(chain, SHIFT_TERMS, expected_period_count=1)
    assert undated_later.status_code == 422
    assert "date it starts from" in undated_later.json()["detail"]


def test_a_later_period_must_start_after_the_previous_one_and_before_the_next(chain) -> None:
    assert _add(chain, SHIFT_TERMS).status_code == 201
    assert _add(chain, SHIFT_TERMS, expected_period_count=1, effective_from="2027-03-01").status_code == 201
    assert _add(chain, SHIFT_TERMS, expected_period_count=2, effective_from="2027-03-01").status_code == 422
    assert _add(chain, SHIFT_TERMS, expected_period_count=2, effective_from="2027-02-01").status_code == 422
    third = _add(chain, SHIFT_TERMS, expected_period_count=2, effective_from="2027-06-01")
    assert third.status_code == 201
    second = third.json()["line_billing_terms"]["periods"][1]
    moved_past_next = _put(chain, second["term_public_id"], SHIFT_TERMS, expected_term_revision=1, effective_from="2027-06-01")
    assert moved_past_next.status_code == 422
    assert "before the next period" in moved_past_next.json()["detail"]
    assert _put(chain, second["term_public_id"], SHIFT_TERMS, expected_term_revision=1, effective_from="2027-05-31").status_code == 200


def test_adding_a_period_from_a_latest_period_someone_has_since_changed_is_a_conflict(chain) -> None:
    """Review round 2: the count alone does not change when the latest period is edited, so a period
    copied from what the caller saw is refused once the latest revision has moved."""
    first = _add(chain, SHIFT_TERMS).json()["line_billing_terms"]["periods"][0]
    assert _put(chain, first["term_public_id"], {**SHIFT_TERMS, "normal_rate_amount": "9000.00"}, expected_term_revision=1).status_code == 200
    stale = _add(chain, SHIFT_TERMS, expected_period_count=1, expected_latest_term_revision=1, effective_from="2027-03-01")
    assert stale.status_code == 409
    assert len(_line_terms(chain)["periods"]) == 1
    assert _event_count(chain["work_order_public_id"], "WorkOrderLineBillingTermsPeriodAdded") == 1
    current = _add(chain, SHIFT_TERMS, expected_period_count=1, expected_latest_term_revision=2, effective_from="2027-03-01")
    assert current.status_code == 201, current.text


def test_a_latest_revision_given_before_any_period_exists_is_a_conflict(chain) -> None:
    response = client.post(
        _terms_url(chain), headers=auth_headers("sales1"),
        json={"expected_period_count": 0, "expected_latest_term_revision": 1, **SHIFT_TERMS},
    )
    assert response.status_code == 409


def test_a_later_period_on_the_first_calendar_date_is_refused_not_an_error(chain) -> None:
    assert _add(chain, SHIFT_TERMS).status_code == 201
    response = _add(chain, SHIFT_TERMS, expected_period_count=1, effective_from="0001-01-01")
    assert response.status_code == 422
    assert "real date" in response.json()["detail"]
    assert _add(chain, SHIFT_TERMS, expected_period_count=1, effective_from="0001-01-02").status_code == 201


def test_a_stale_period_count_is_a_conflict_and_writes_nothing(chain) -> None:
    assert _add(chain, SHIFT_TERMS).status_code == 201
    stale = _add(chain, SHIFT_TERMS, expected_period_count=0)
    assert stale.status_code == 409
    assert "Reload" in stale.json()["detail"]
    assert len(_line_terms(chain)["periods"]) == 1


def test_a_changing_update_moves_to_the_next_revision_and_names_the_changed_fields(chain) -> None:
    term = _add(chain, SHIFT_TERMS).json()["line_billing_terms"]["periods"][0]
    response = _put(chain, term["term_public_id"], {**SHIFT_TERMS, "normal_rate_amount": "13000.00"}, expected_term_revision=1)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["line_billing_terms"]["periods"][0]["term_revision"] == 2
    assert Decimal(body["line_billing_terms"]["periods"][0]["normal_rate_amount"]) == Decimal("13000.00")
    assert body["event"]["event_name"] == "WorkOrderLineBillingTermsPeriodUpdated"
    assert body["event"]["event_payload"]["changed_fields"] == ["normal_rate_amount"]
    assert body["event"]["event_payload"]["term_revision"] == 2


def test_an_identical_update_records_nothing_and_keeps_the_revision(chain) -> None:
    term = _add(chain, SHIFT_TERMS).json()["line_billing_terms"]["periods"][0]
    # The same values written differently: a plain number for hours and a lower-case repeated day.
    same = {**SHIFT_TERMS, "contracted_hours_per_billing_unit": "8", "weekly_off_day_codes": ["sun", "SUN"]}
    response = _put(chain, term["term_public_id"], same, expected_term_revision=1)
    assert response.status_code == 200, response.text
    assert response.json()["event"] is None
    assert response.json()["line_billing_terms"]["periods"][0]["term_revision"] == 1
    assert _event_count(chain["work_order_public_id"], "WorkOrderLineBillingTermsPeriodUpdated") == 0


def test_a_stale_revision_is_refused_on_update_and_on_remove(chain) -> None:
    first = _add(chain, SHIFT_TERMS).json()["line_billing_terms"]["periods"][0]
    second = _add(chain, SHIFT_TERMS, expected_period_count=1, effective_from="2027-03-01").json()["line_billing_terms"]["periods"][1]
    assert _put(chain, first["term_public_id"], {**SHIFT_TERMS, "normal_rate_amount": "9000.00"}, expected_term_revision=1).status_code == 200

    stale_update = _put(chain, first["term_public_id"], {**SHIFT_TERMS, "normal_rate_amount": "9500.00"}, expected_term_revision=1)
    assert stale_update.status_code == 409
    assert Decimal(_line_terms(chain)["periods"][0]["normal_rate_amount"]) == Decimal("9000.00")

    assert _put(chain, second["term_public_id"], {**SHIFT_TERMS, "normal_rate_amount": "8000.00"}, expected_term_revision=1, effective_from="2027-03-01").status_code == 200
    stale_remove = _remove(chain, second["term_public_id"], expected_term_revision=1)
    assert stale_remove.status_code == 409
    assert len(_line_terms(chain)["periods"]) == 2


def test_only_the_latest_period_can_be_removed_and_never_the_first(chain) -> None:
    first = _add(chain, SHIFT_TERMS).json()["line_billing_terms"]["periods"][0]
    alone = _remove(chain, first["term_public_id"], expected_term_revision=1)
    assert alone.status_code == 422
    assert "first period cannot be removed" in alone.json()["detail"]
    assert _add(chain, SHIFT_TERMS, expected_period_count=1, effective_from="2027-03-01").status_code == 201
    not_latest = _remove(chain, first["term_public_id"], expected_term_revision=1)
    assert not_latest.status_code == 422
    assert "latest period" in not_latest.json()["detail"]


def test_removing_the_latest_period_records_the_removed_event(chain) -> None:
    assert _add(chain, SHIFT_TERMS).status_code == 201
    second = _add(chain, DAY_TERMS, expected_period_count=1, effective_from="2027-03-01").json()["line_billing_terms"]["periods"][1]
    response = _remove(chain, second["term_public_id"], expected_term_revision=1)
    assert response.status_code == 200, response.text
    body = response.json()
    assert [period["period_number"] for period in body["line_billing_terms"]["periods"]] == [1]
    assert body["event"]["event_name"] == "WorkOrderLineBillingTermsPeriodRemoved"
    assert body["event"]["event_payload"]["period_number"] == 2
    assert body["event"]["event_payload"]["billing_uom_code"] == "DAY"


def test_effective_to_and_the_current_period_follow_today(chain) -> None:
    today = TODAY
    second_from, third_from = today - timedelta(days=10), today + timedelta(days=20)
    periods = _three_periods(chain, second_from.isoformat(), third_from.isoformat())
    assert periods[0]["effective_to"] == (second_from - timedelta(days=1)).isoformat()
    assert periods[1]["effective_to"] == (third_from - timedelta(days=1)).isoformat()
    assert periods[2]["effective_to"] is None
    assert _line_terms(chain)["current_period_number"] == 2


def test_the_returned_entry_is_the_revision_its_event_records(chain) -> None:
    first = _add(chain, SHIFT_TERMS).json()
    assert first["line_billing_terms"]["periods"][0]["term_revision"] == first["event"]["event_payload"]["term_revision"] == 1
    term_public_id = first["line_billing_terms"]["periods"][0]["term_public_id"]
    second = _put(chain, term_public_id, {**SHIFT_TERMS, "normal_rate_amount": "1.00"}, expected_term_revision=1).json()
    assert second["line_billing_terms"]["periods"][0]["term_revision"] == second["event"]["event_payload"]["term_revision"] == 2


def test_a_failure_building_the_response_leaves_nothing_written(chain, monkeypatch) -> None:
    """The response is read inside the transaction, before commit. If building it fails, the new
    period and its event roll back with it."""

    def failing_read(*args, **kwargs):
        raise RuntimeError("simulated failure reading the saved terms")

    monkeypatch.setattr(billing_terms_service, "list_work_order_billing_term_rows", failing_read)
    with SessionLocal() as db:
        with pytest.raises(RuntimeError):
            work_orders_service.add_work_order_line_billing_terms_period(
                db,
                work_order_public_id=chain["work_order_public_id"],
                line_public_id=chain["line_public_ids"][0],
                payload=WorkOrderLineBillingTermsPeriodCreate(expected_period_count=0, **SHIFT_TERMS),
                current_user_public_id=None,
            )
    monkeypatch.undo()
    assert _line_terms(chain)["periods"] == []
    assert _event_count(chain["work_order_public_id"], "WorkOrderLineBillingTermsPeriodAdded") == 0


def test_a_concurrent_update_cannot_change_the_revision_another_update_reports(chain, monkeypatch) -> None:
    """Two sessions, interleaved deterministically. Update A pauses at the moment it reads the saved
    terms back for its response; update B, for the same period, starts meanwhile. If A read after its
    commit, B would not be blocked and A would report B's revision beside an event for its own. Because
    A reads before commit, under the Work Order lock, B waits and each reports exactly what it wrote."""
    term_public_id = _add(chain, SHIFT_TERMS).json()["line_billing_terms"]["periods"][0]["term_public_id"]
    real_read = billing_terms_service.list_work_order_billing_term_rows
    a_is_paused = threading.Event()
    b_finished = threading.Event()
    thread_a_name = "slice-7d-update-a"
    results: dict[str, object] = {}

    def pausing_read(*args, **kwargs):
        if threading.current_thread().name == thread_a_name and not a_is_paused.is_set():
            a_is_paused.set()
            b_finished.wait(timeout=3)
        return real_read(*args, **kwargs)

    monkeypatch.setattr(billing_terms_service, "list_work_order_billing_term_rows", pausing_read)

    def update(name: str, revision: int, rate: str) -> None:
        try:
            with SessionLocal() as db:
                results[name] = work_orders_service.update_work_order_line_billing_terms_period(
                    db,
                    work_order_public_id=chain["work_order_public_id"],
                    line_public_id=chain["line_public_ids"][0],
                    term_public_id=term_public_id,
                    payload=WorkOrderLineBillingTermsPeriodUpdate(
                        expected_term_revision=revision, **{**SHIFT_TERMS, "normal_rate_amount": rate}
                    ),
                    current_user_public_id=None,
                )
        except Exception as exc:  # recorded, asserted below
            results[name] = exc
        finally:
            if name == "b":
                b_finished.set()

    thread_a = threading.Thread(target=update, args=("a", 1, "11111.00"), name=thread_a_name)
    thread_a.start()
    assert a_is_paused.wait(timeout=30), "update A never reached its response read"
    thread_b = threading.Thread(target=update, args=("b", 2, "22222.00"))
    thread_b.start()
    thread_a.join(timeout=60)
    thread_b.join(timeout=60)
    monkeypatch.undo()

    a, b = results["a"], results["b"]
    assert not isinstance(a, Exception), a
    assert not isinstance(b, Exception), b
    a_period, b_period = a.line_billing_terms.periods[0], b.line_billing_terms.periods[0]
    assert a_period.term_revision == a.event["event_payload"]["term_revision"] == 2
    assert a_period.normal_rate_amount == Decimal("11111.00")
    assert b_period.term_revision == b.event["event_payload"]["term_revision"] == 3
    assert b_period.normal_rate_amount == Decimal("22222.00")


# --- Terms -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "term",
    [
        {"contracted_hours_per_billing_unit": "8.00"},
        {"weekly_off_day_codes": ["SUN"]},
        {"off_day_work_treatment_code": "OVERTIME_RATE"},
        {"overtime_rate_method_code": "NONE"},
        {"breakdown_treatment_code": "NONE"},
    ],
)
def test_hour_billing_refuses_time_terms(chain, term: dict) -> None:
    response = _add(chain, {**HOUR_TERMS, **term})
    assert response.status_code == 422
    assert "actual hours worked" in response.json()["detail"]


@pytest.mark.parametrize(
    "term",
    [
        {"contracted_working_days_per_month": "26.00"},
        {"part_month_basis_code": "CALENDAR_DAYS"},
        {"month_overtime_hours_basis_code": "ENGINE_HOURS"},
        {"month_overtime_counting_code": "WHOLE_MONTH"},
    ],
)
def test_month_only_terms_are_refused_on_shift_billing(chain, term: dict) -> None:
    response = _add(chain, {**SHIFT_TERMS, **term})
    assert response.status_code == 422
    assert "only to Month billing" in response.json()["detail"]


def test_a_minimum_guarantee_is_refused_on_month_billing(chain) -> None:
    response = _add(chain, {**MONTH_OT_NORMAL_CUMULATIVE, "minimum_guarantee_code": "NONE"})
    assert response.status_code == 422
    assert "Month billing" in response.json()["detail"]


@pytest.mark.parametrize("term", [{"normal_rate_amount": "1000.00"}, {"customer_idle_treatment_code": "AS_WORKING_HOURS"}])
def test_terms_need_a_billing_basis_first(chain, term: dict) -> None:
    """Idle time too (review round 1): no term is stored before a basis is chosen."""
    response = _add(chain, term)
    assert response.status_code == 422
    assert "billing basis" in response.json()["detail"]


def test_switching_a_recorded_period_back_to_no_basis_is_refused_while_terms_remain(chain) -> None:
    term_public_id = _add(chain, HOUR_TERMS).json()["line_billing_terms"]["periods"][0]["term_public_id"]
    response = _put(chain, term_public_id, {"customer_idle_treatment_code": "AS_WORKING_HOURS"}, expected_term_revision=1)
    assert response.status_code == 422
    assert _put(chain, term_public_id, {}, expected_term_revision=1).status_code == 200


def test_off_day_work_at_the_overtime_rate_needs_overtime_in_the_work_order(chain) -> None:
    """Review round 1: "charged at the overtime rate" with overtime "not in the Work Order" cannot be
    priced, so it is refused rather than reported complete."""
    response = _add(chain, {**SHIFT_TERMS, "overtime_rate_method_code": "NONE", "overtime_rate_amount": None})
    assert response.status_code == 422
    assert "overtime rate" in response.json()["detail"]


def test_hour_billing_refuses_a_part_month_term(chain) -> None:
    response = _add(chain, {**HOUR_TERMS, "part_month_basis_code": "CALENDAR_DAYS"})
    assert response.status_code == 422
    assert "only to Month billing" in response.json()["detail"]


@pytest.mark.parametrize(
    "change, message",
    [
        ({"overtime_rate_method_code": "RATE_PER_HOUR", "overtime_rate_amount": None}, "per hour"),
        ({"overtime_rate_percent": "120.00"}, "no percentage"),
        ({"overtime_rate_method_code": "PERCENT_OF_NORMAL", "overtime_rate_amount": None, "overtime_rate_percent": None}, "percentage of the normal rate"),
        ({"overtime_rate_method_code": "PERCENT_OF_NORMAL", "overtime_rate_percent": "120.00"}, "no amount"),
        ({"overtime_rate_method_code": "NONE"}, "remove its amount"),
        ({"overtime_rate_method_code": "DOUBLE"}, "per hour or as a percentage"),
    ],
)
def test_each_rate_carries_exactly_the_value_its_method_asks_for(chain, change: dict, message: str) -> None:
    response = _add(chain, {**SHIFT_TERMS, **change})
    assert response.status_code == 422
    assert message in response.json()["detail"]


@pytest.mark.parametrize(
    "change, message",
    [
        ({"holiday_rate_method_code": "RATE_PER_HOUR", "holiday_rate_amount": "2000.00"}, "holiday rate applies only"),
        ({"breakdown_rate_method_code": "RATE_PER_HOUR", "breakdown_rate_amount": "300.00"}, "breakdown rate applies only"),
        ({"standby_rate_method_code": "PERCENT_OF_NORMAL", "standby_rate_percent": "50.00"}, "standby rate applies only"),
        ({"minimum_billing_units_per_month": "200.00"}, "monthly minimum guarantee"),
        ({"minimum_guarantee_code": "UNITS_PER_MONTH"}, "minimum number of billing units"),
        (
            {"breakdown_offset_by_same_day_overtime": True, "overtime_rate_method_code": "NONE", "overtime_rate_amount": None, "off_day_work_treatment_code": "NONE"},
            "offset breakdown",
        ),
    ],
)
def test_a_dependent_value_is_accepted_only_with_the_choice_that_asks_for_it(chain, change: dict, message: str) -> None:
    response = _add(chain, {**SHIFT_TERMS, **change})
    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_monthly_overtime_counting_needs_overtime_charged(chain) -> None:
    response = _add(
        chain,
        {**MONTH_OT_NORMAL_CUMULATIVE, "overtime_rate_method_code": "NONE", "overtime_rate_percent": None, "off_day_work_treatment_code": "NORMAL_RATE"},
    )
    assert response.status_code == 422
    assert "only when overtime is charged" in response.json()["detail"]


@pytest.mark.parametrize(
    "change",
    [
        {"billing_uom_code": "WEEK"},
        {"off_day_work_treatment_code": "DOUBLE_TIME"},
        {"breakdown_treatment_code": "IGNORE"},
        {"customer_idle_treatment_code": "HALF"},
        {"minimum_guarantee_code": "UNITS_PER_YEAR"},
        {"weekly_off_day_codes": ["FUNDAY"]},
        {"weekly_off_day_codes": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]},
        {"normal_rate_amount": "0"},
        {"normal_rate_amount": "-5"},
        {"overtime_rate_amount": "0"},
        {"overtime_rate_method_code": "PERCENT_OF_NORMAL", "overtime_rate_amount": None, "overtime_rate_percent": "0"},
        {"contracted_hours_per_billing_unit": "0"},
        {"contracted_hours_per_billing_unit": "-8"},
        {"minimum_guarantee_code": "UNITS_PER_MONTH", "minimum_billing_units_per_month": "0"},
        {"currency_code": "USD"},
        {"term_revision": 5},
    ],
)
def test_unknown_codes_non_positive_values_and_unknown_fields_are_refused(chain, change: dict) -> None:
    assert _add(chain, {**SHIFT_TERMS, **change}).status_code == 422
    assert _line_terms(chain)["periods"] == []


# --- Completeness ----------------------------------------------------------------------------


def test_a_line_with_no_periods_reports_no_terms(chain) -> None:
    entry = _line_terms(chain)
    assert entry["periods"] == []
    assert entry["current_period_number"] is None
    assert entry["terms_complete"] is False
    assert entry["line_missing_items"] == ["NO_TERMS"]


def test_each_basis_lists_exactly_its_own_missing_items(chain) -> None:
    term = _add(chain, {}).json()["line_billing_terms"]["periods"][0]
    assert term["missing_items"] == [
        "BILLING_BASIS",
        "NORMAL_RATE",
        "IDLE_TIME",
        # Part 2: fuel, mobilisation and demobilisation apply to every basis, so an empty first period
        # reports them too. A shift pattern needs a basis that has shifts.
        "MOBILISATION",
        "DEMOBILISATION",
        "FUEL",
        # Part 4: extra kilometres and crew apply to every basis too.
        "EXTRA_KILOMETRES",
        "CREW",
    ]
    expectations = [
        (
            "SHIFT",
            ["CONTRACTED_HOURS", "NORMAL_RATE", "WEEKLY_OFF_DAYS", "OFF_DAY_WORK", "OVERTIME", "BREAKDOWN", "IDLE_TIME", "MINIMUM_GUARANTEE", "SHIFTS", "MOBILISATION", "DEMOBILISATION", "FUEL", "EXTRA_KILOMETRES", "CREW"],
        ),
        # An hourly line lists nothing about shifts: it has none.
        ("HOUR", ["NORMAL_RATE", "IDLE_TIME", "MINIMUM_GUARANTEE", "MOBILISATION", "DEMOBILISATION", "FUEL", "EXTRA_KILOMETRES", "CREW"]),
        (
            "MONTH",
            ["CONTRACTED_HOURS", "CONTRACTED_WORKING_DAYS", "NORMAL_RATE", "WEEKLY_OFF_DAYS", "OFF_DAY_WORK", "OVERTIME", "BREAKDOWN", "IDLE_TIME", "PART_MONTH", "SHIFTS", "MOBILISATION", "DEMOBILISATION", "FUEL", "EXTRA_KILOMETRES", "CREW"],
        ),
    ]
    for revision, (basis, missing) in enumerate(expectations, start=1):
        response = _put(chain, term["term_public_id"], {"billing_uom_code": basis}, expected_term_revision=revision)
        assert response.status_code == 200, response.text
        assert response.json()["line_billing_terms"]["periods"][0]["missing_items"] == missing, basis


def test_not_in_the_work_order_counts_as_recorded_but_a_chosen_rate_without_its_method_does_not(chain) -> None:
    nothing_in_work_order = {
        **SHIFT_TERMS,
        **PART_2_FIRST_PERIOD_ONLY,
        "off_day_work_treatment_code": "NONE",
        "overtime_rate_method_code": "NONE",
        "overtime_rate_amount": None,
        "breakdown_treatment_code": "NONE",
        "customer_idle_treatment_code": "NONE",
    }
    term = _add(chain, nothing_in_work_order).json()["line_billing_terms"]["periods"][0]
    assert term["missing_items"] == []
    rates_without_methods = {
        **SHIFT_TERMS,
        **PART_2_FIRST_PERIOD_ONLY,
        "off_day_work_treatment_code": "HOLIDAY_RATE",
        "breakdown_treatment_code": "DEDUCT_AT_BREAKDOWN_RATE",
        "customer_idle_treatment_code": "STANDBY_RATE",
    }
    response = _put(chain, term["term_public_id"], rates_without_methods, expected_term_revision=1)
    # SHIFT_TERMS answers the Part 2 terms with "not in the Work Order", so none of them is missing here.
    assert response.json()["line_billing_terms"]["periods"][0]["missing_items"] == [
        "OFF_DAY_WORK",
        "BREAKDOWN",
        "IDLE_TIME",
    ]


def test_off_day_work_at_the_overtime_rate_is_missing_while_overtime_is_not_recorded(chain) -> None:
    terms = {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "overtime_rate_method_code": None, "overtime_rate_amount": None}
    period = _add(chain, terms).json()["line_billing_terms"]["periods"][0]
    assert period["missing_items"] == ["OFF_DAY_WORK", "OVERTIME"]


def test_zero_working_days_are_refused_on_month_billing(chain) -> None:
    assert _add(chain, {**MONTH_OT_NORMAL_CUMULATIVE, "contracted_working_days_per_month": "0"}).status_code == 422
    assert _line_terms(chain)["periods"] == []


def test_monthly_overtime_charged_without_its_counting_method_is_missing(chain) -> None:
    terms = {**MONTH_OT_NORMAL_CUMULATIVE, **PART_2_FIRST_PERIOD_ONLY, "month_overtime_counting_code": None}
    period = _add(chain, terms).json()["line_billing_terms"]["periods"][0]
    assert period["missing_items"] == ["MONTH_OVERTIME_METHOD"]


def test_an_empty_off_day_list_is_a_seven_day_week_and_complete_while_no_list_is_missing(chain) -> None:
    seven_day_week = _add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "weekly_off_day_codes": []}).json()["line_billing_terms"]["periods"][0]
    assert seven_day_week["missing_items"] == []
    assert seven_day_week["weekly_off_day_codes"] == []
    not_recorded = _put(
        chain,
        seven_day_week["term_public_id"],
        {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "weekly_off_day_codes": None},
        expected_term_revision=1,
    )
    assert not_recorded.json()["line_billing_terms"]["periods"][0]["missing_items"] == ["WEEKLY_OFF_DAYS"]


@pytest.mark.parametrize("example", list(ANNEXURE_10_TERM_SETS))
def test_each_annexure_10_example_records_as_a_complete_term_set(chain, example: str) -> None:
    # A first period, so the line-once terms are answered here too.
    response = _add(chain, {**ANNEXURE_10_TERM_SETS[example], **PART_2_FIRST_PERIOD_ONLY})
    assert response.status_code == 201, response.text
    entry = response.json()["line_billing_terms"]
    assert entry["terms_complete"] is True, entry["line_missing_items"]
    if ANNEXURE_10_TERM_SETS[example]["billing_uom_code"] == "MONTH":
        # Annexure-10: 10 hours a day x 26 days = 260 hours a month.
        assert Decimal(entry["periods"][0]["derived_hours_per_working_day"]) == Decimal("10.00")


def test_a_lines_missing_items_are_the_union_across_its_periods(chain) -> None:
    assert _add(chain, {**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY}).status_code == 201
    second = _add(chain, {**SHIFT_TERMS, "overtime_rate_method_code": None, "overtime_rate_amount": None}, expected_period_count=1, effective_from="2027-03-01")
    entry = second.json()["line_billing_terms"]
    assert entry["periods"][0]["is_complete"] is True
    assert entry["terms_complete"] is False
    # Off-day work is charged at the overtime rate, so it is missing too while overtime is unrecorded.
    assert entry["line_missing_items"] == ["OFF_DAY_WORK", "OVERTIME"]


# --- Permissions -----------------------------------------------------------------------------


@pytest.mark.parametrize("username", ["sales1", "manager1", "ops1", "admin1"])
def test_the_four_writing_roles_may_add_update_and_remove(chain, username: str) -> None:
    first = _add(chain, SHIFT_TERMS, username=username)
    assert first.status_code == 201, first.text
    term_public_id = first.json()["line_billing_terms"]["periods"][0]["term_public_id"]
    assert _put(chain, term_public_id, DAY_TERMS, expected_term_revision=1, username=username).status_code == 200
    second = _add(chain, SHIFT_TERMS, expected_period_count=1, expected_latest_term_revision=2, effective_from="2027-03-01", username=username)
    assert second.status_code == 201, second.text
    second_public_id = second.json()["line_billing_terms"]["periods"][1]["term_public_id"]
    assert _remove(chain, second_public_id, expected_term_revision=1, username=username).status_code == 200


@pytest.mark.parametrize("username", ["finance1", "readonly1"])
def test_finance_and_management_may_read_but_not_write(chain, username: str) -> None:
    term_public_id = _add(chain, SHIFT_TERMS).json()["line_billing_terms"]["periods"][0]["term_public_id"]
    assert _add(chain, SHIFT_TERMS, expected_period_count=1, effective_from="2027-03-01", username=username).status_code == 403
    assert _put(chain, term_public_id, DAY_TERMS, expected_term_revision=1, username=username).status_code == 403
    assert _remove(chain, term_public_id, expected_term_revision=1, username=username).status_code == 403
    assert len(_line_terms(chain, username=username)["periods"]) == 1


def test_unauthenticated_callers_are_refused(chain) -> None:
    term_public_id = str(uuid4())
    assert client.get(f"/api/work-orders/{chain['work_order_public_id']}/billing-terms").status_code == 401
    assert client.post(_terms_url(chain), json={"expected_period_count": 0}).status_code == 401
    assert client.put(_terms_url(chain, 0, term_public_id), json={"expected_term_revision": 1}).status_code == 401
    assert client.delete(_terms_url(chain, 0, term_public_id), params={"expected_term_revision": 1}).status_code == 401


# --- Not found, closed, and the work_orders boundary -----------------------------------------


def test_unknown_work_order_line_and_period_are_not_found(chain) -> None:
    unknown = str(uuid4())
    assert client.get(f"/api/work-orders/{unknown}/billing-terms", headers=auth_headers("sales1")).status_code == 404
    assert client.post(
        _terms_url(chain, 0, work_order_public_id=unknown), headers=auth_headers("sales1"), json={"expected_period_count": 0}
    ).status_code == 404
    supplementary_public_id, handoff = create_test_supplementary_work_order(chain["offer_public_id"])
    chain["supplementary_offer_public_ids"].append(supplementary_public_id)
    second = handoff["work_order"]
    chain["work_order_public_ids"].append(str(second["public_id"]))
    other_work_order = client.post(
        _terms_url(chain, 0, work_order_public_id=str(second["public_id"])),
        headers=auth_headers("sales1"),
        json={"expected_period_count": 0, **SHIFT_TERMS},
    )
    assert other_work_order.status_code == 404
    assert _put(chain, unknown, SHIFT_TERMS, expected_term_revision=1).status_code == 404
    assert _remove(chain, unknown, expected_term_revision=1).status_code == 404


def test_a_closed_work_order_refuses_every_change(chain) -> None:
    first = _add(chain, SHIFT_TERMS).json()["line_billing_terms"]["periods"][0]
    second = _add(chain, SHIFT_TERMS, expected_period_count=1, effective_from="2027-03-01").json()["line_billing_terms"]["periods"][1]
    with SessionLocal() as db:
        db.execute(
            text("UPDATE crm_work_order SET work_order_status_code = 'CLOSED' WHERE work_order_public_id = :id"),
            {"id": chain["work_order_public_id"]},
        )
        db.commit()
    for response in (
        _add(chain, SHIFT_TERMS, expected_period_count=2, effective_from="2027-06-01"),
        _put(chain, first["term_public_id"], DAY_TERMS, expected_term_revision=1),
        _remove(chain, second["term_public_id"], expected_term_revision=1),
    ):
        assert response.status_code == 422
        assert "closed" in response.json()["detail"]


def test_the_handoff_records_no_billing_terms(chain) -> None:
    with SessionLocal() as db:
        count = db.execute(
            text(
                """
                SELECT COUNT(*) FROM crm_work_order_line_billing_term t
                INNER JOIN crm_work_order_line wol ON wol.id = t.work_order_line_id
                INNER JOIN crm_work_order wo ON wo.id = wol.work_order_id
                WHERE wo.work_order_public_id = :id
                """
            ),
            {"id": chain["work_order_public_id"]},
        ).scalar_one()
    assert int(count) == 0


def test_recording_terms_leaves_the_work_order_and_its_lines_unchanged(chain) -> None:
    headers = auth_headers("readonly1")
    before_work_order = client.get(f"/api/work-orders/{chain['work_order_public_id']}", headers=headers).json()
    before_lines = client.get(f"/api/work-orders/{chain['work_order_public_id']}/lines", headers=headers).json()
    term_public_id = _add(chain, SHIFT_TERMS).json()["line_billing_terms"]["periods"][0]["term_public_id"]
    assert _put(chain, term_public_id, DAY_TERMS, expected_term_revision=1).status_code == 200
    assert client.get(f"/api/work-orders/{chain['work_order_public_id']}", headers=headers).json() == before_work_order
    assert client.get(f"/api/work-orders/{chain['work_order_public_id']}/lines", headers=headers).json() == before_lines


def test_the_quoted_unit_and_rate_are_shown_beside_the_work_order_rate(chain) -> None:
    lines = client.get(f"/api/work-orders/{chain['work_order_public_id']}/lines", headers=auth_headers("sales1")).json()
    entry = _line_terms(chain)
    assert entry["quoted_uom"] == lines[0]["uom"]
    assert entry["quoted_rate_amount"] == lines[0]["rate_amount"]


def test_no_event_payload_carries_an_amount_rate_or_percentage(chain) -> None:
    added = _add(chain, MONTH_NON_CUMULATIVE).json()
    term_public_id = added["line_billing_terms"]["periods"][0]["term_public_id"]
    updated = _put(chain, term_public_id, {**MONTH_NON_CUMULATIVE, "normal_rate_amount": "123456.00"}, expected_term_revision=1).json()
    second = _add(chain, MONTH_NON_CUMULATIVE, expected_period_count=1, expected_latest_term_revision=2, effective_from="2027-03-01").json()
    removed = _remove(chain, second["line_billing_terms"]["periods"][1]["term_public_id"], expected_term_revision=1).json()
    for body in (added, updated, second, removed):
        payload = body["event"]["event_payload"]
        assert set(payload) == EVENT_PAYLOAD_KEYS
        # Identifiers and the date are random or fixed text that could contain these digits by chance
        # (review round 3), so only the fields that could carry a value are searched.
        assert isinstance(payload["term_revision"], int) and isinstance(payload["period_number"], int)
        assert all(isinstance(field, str) and field.isidentifier() for field in payload["changed_fields"])
        searched = json.dumps({key: payload[key] for key in ("billing_uom_code", "changed_fields")})
        for value in ("100000", "123456", "385", "125", "260", "26.00"):
            assert value not in searched


# --- Database constraints --------------------------------------------------------------------


def _insert_term_directly(line_public_id: str, **columns: object) -> None:
    columns = {"period_number": 1, **columns}
    names = ", ".join(columns)
    binds = ", ".join(f":{name}" for name in columns)
    with SessionLocal() as db:
        try:
            db.execute(
                text(
                    f"""
                    INSERT INTO crm_work_order_line_billing_term (work_order_line_billing_term_public_id, work_order_line_id, {names})
                    SELECT :public_id, wol.id, {binds}
                    FROM crm_work_order_line wol WHERE wol.work_order_line_public_id = :line_public_id
                    """
                ),
                {"public_id": str(uuid4()), "line_public_id": line_public_id, **columns},
            )
            db.commit()
        finally:
            db.rollback()


@pytest.mark.parametrize(
    "columns",
    [
        {"effective_from": date(2027, 1, 1)},
        {"period_number": 2},
        {"period_number": 2, "effective_from": date(1, 1, 1)},
        {"period_number": 0},
        {"term_revision": 0},
        {"currency_code": "USD"},
        {"billing_uom_code": "WEEK"},
        {"normal_rate_amount": Decimal("100")},
        {"billing_uom_code": "HOUR", "normal_rate_amount": Decimal("0")},
        {"billing_uom_code": "HOUR", "contracted_hours_per_billing_unit": Decimal("8")},
        {"billing_uom_code": "SHIFT", "contracted_working_days_per_month": Decimal("26")},
        {"billing_uom_code": "MONTH", "minimum_guarantee_code": "NONE"},
        {"billing_uom_code": "SHIFT", "weekly_off_day_codes": ["FUN"]},
        {"billing_uom_code": "SHIFT", "weekly_off_day_codes": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]},
        {"billing_uom_code": "SHIFT", "contracted_hours_per_billing_unit": Decimal("0")},
        {"billing_uom_code": "MONTH", "contracted_working_days_per_month": Decimal("0")},
        {"billing_uom_code": "SHIFT", "overtime_rate_method_code": "PERCENT_OF_NORMAL", "overtime_rate_percent": Decimal("0")},
        {"billing_uom_code": "SHIFT", "off_day_work_treatment_code": "OVERTIME_RATE", "overtime_rate_method_code": "NONE"},
        {"billing_uom_code": "SHIFT", "overtime_rate_method_code": "RATE_PER_HOUR"},
        {"billing_uom_code": "SHIFT", "overtime_rate_method_code": "NONE", "overtime_rate_amount": Decimal("100")},
        # The cases below have a NULL on the other side of the rule: a CHECK that evaluates to NULL
        # passes in PostgreSQL, so each is written to yield TRUE or FALSE.
        {"billing_uom_code": "SHIFT", "overtime_rate_amount": Decimal("100")},
        {"billing_uom_code": "SHIFT", "holiday_rate_method_code": "RATE_PER_HOUR", "holiday_rate_amount": Decimal("1")},
        {"billing_uom_code": "HOUR", "standby_rate_method_code": "PERCENT_OF_NORMAL", "standby_rate_percent": Decimal("50")},
        {"billing_uom_code": "SHIFT", "minimum_billing_units_per_month": Decimal("10")},
        {"billing_uom_code": "SHIFT", "breakdown_offset_by_same_day_overtime": True},
        {"billing_uom_code": "MONTH", "month_overtime_hours_basis_code": "ENGINE_HOURS"},
        {"billing_uom_code": None, "part_month_basis_code": "CALENDAR_DAYS"},
        {"billing_uom_code": None, "customer_idle_treatment_code": "AS_WORKING_HOURS"},
        # Review round 4: NaN compares greater than zero in PostgreSQL, and array containment ignores shape.
        {"billing_uom_code": "HOUR", "normal_rate_amount": Decimal("NaN")},
        {"billing_uom_code": "SHIFT", "contracted_hours_per_billing_unit": Decimal("NaN")},
        {"billing_uom_code": "SHIFT", "overtime_rate_method_code": "PERCENT_OF_NORMAL", "overtime_rate_percent": Decimal("NaN")},
        {"billing_uom_code": "SHIFT", "weekly_off_day_codes": [["MON", "TUE"]]},
    ],
)
def test_the_database_refuses_a_direct_insert_that_breaks_a_rule(chain, columns: dict[str, object]) -> None:
    with pytest.raises(IntegrityError):
        _insert_term_directly(chain["line_public_ids"][0], **columns)


def test_the_database_accepts_a_later_period_from_the_second_calendar_date(chain) -> None:
    """Review round 5: the date rule refuses only 0001-01-01, and the line stays readable."""
    _insert_term_directly(chain["line_public_ids"][0], billing_uom_code="SHIFT")
    _insert_term_directly(chain["line_public_ids"][0], period_number=2, effective_from=date(1, 1, 2), billing_uom_code="SHIFT")
    periods = _line_terms(chain)["periods"]
    assert periods[0]["effective_to"] == "0001-01-01"


def test_the_database_still_accepts_an_empty_off_day_list_and_a_single_off_day(chain) -> None:
    """The one-dimensional rule must not refuse the empty array that records a 7-day week."""
    _insert_term_directly(chain["line_public_ids"][0], billing_uom_code="SHIFT", weekly_off_day_codes=[])
    _insert_term_directly(
        chain["line_public_ids"][0], period_number=2, effective_from=date(2027, 3, 1), billing_uom_code="SHIFT",
        weekly_off_day_codes=["SUN"],
    )
    periods = _line_terms(chain)["periods"]
    assert [period["weekly_off_day_codes"] for period in periods] == [[], ["SUN"]]


def test_the_database_refuses_a_second_row_for_the_same_period(chain) -> None:
    _insert_term_directly(chain["line_public_ids"][0])
    with pytest.raises(IntegrityError):
        _insert_term_directly(chain["line_public_ids"][0])
