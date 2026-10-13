"""Slice 7D Part 3 - the contract period, extensions, line dates, and copying terms between lines.

Each test maps to an item in the "Test plan" of
docs/agent/slices/slice-7d-part-3-contract-period.md. The fixture builds a real chain through the
existing API helpers (Lead -> Account -> Opportunity -> accepted Commercial Offer -> Work Order) with
three lines, so copying one line's terms onto others has somewhere to go.

The rules themselves are tested without a database in test_slice_7d_part_3_contract_rules.py; what is
tested here is that the routes apply them, that the writes are guarded, and that the events say what
happened.

Business events need no explicit cleanup: conftest removes every event created by the session.
"""

from __future__ import annotations

import json
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.work_orders import repository as work_orders_repository
from tests.business_day_test_support import TODAY, held_to_the_test_day
from tests.test_commercial_offers_api import (
    auth_headers,
    cleanup_test_records,
    cleanup_test_work_orders,
    client,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    create_test_offer_line,
    mark_test_commercial_offer_submitted,
    record_test_customer_response,
)
from tests.test_slice_7d_work_order_line_billing_terms import (
    PART_2_FIRST_PERIOD_ONLY,
    SHIFT_TERMS,
)

READ_ROLES = ("admin1", "sales1", "manager1", "finance1", "ops1", "readonly1")
WRITE_ROLES = ("admin1", "sales1", "manager1", "ops1")
NON_WRITE_ROLES = ("finance1", "readonly1")

PERIOD_KEYS = {
    "work_order_public_id",
    "period_public_id",
    "period_version",
    "contract_start_date",
    "contract_end_basis_code",
    "contract_end_date",
    "contract_notes",
    "contract_state_code",
    "contract_state_label",
    "days_until_start",
    "days_until_end",
    "needs_firm_end_date",
    "is_complete",
    "missing_items",
    "extensions",
    "gaps",
    "updated_by",
    "updated_by_display_name",
    "updated_at",
}
EXTENSION_KEYS = {
    "extension_public_id",
    "extension_sequence_no",
    "previous_end_basis_code",
    "previous_end_date",
    "new_end_date",
    "extension_start_date",
    "customer_reference",
    "received_date",
    "extension_notes",
    "created_by",
    "created_by_display_name",
    "created_at",
}
COPY_RESULT_KEYS = {
    "work_order_line_public_id",
    "line_number",
    "outcome",
    "periods_copied",
    "replaced_period_count",
    "message",
}

START = "2027-01-01"
END = "2027-03-31"


@pytest.fixture(scope="module", autouse=True)
def _on_the_test_day():
    with held_to_the_test_day():
        yield


@pytest.fixture
def chain():
    """An accepted Work Order with three lines copied from the offer."""
    record: dict[str, object] = {"work_order_public_ids": []}
    linked = create_account_linked_test_opportunity()
    record.update(
        lead_public_id=str(linked["lead"]["public_id"]),
        account_public_id=str(linked["account"]["public_id"]),
        opportunity_public_id=str(linked["opportunity"]["public_id"]),
    )
    try:
        offer = create_test_commercial_offer(record["opportunity_public_id"])
        record["offer_public_id"] = str(offer["public_id"])
        # create_test_commercial_offer already leaves the offer with one line; two more make three.
        for _ in range(2):
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
        assert len(record["line_public_ids"]) == 3
        yield record
    finally:
        cleanup_test_work_orders(record["work_order_public_ids"])
        cleanup_test_records(
            opportunity_public_ids=[record["opportunity_public_id"]],
            offer_public_ids=[record["offer_public_id"]] if "offer_public_id" in record else [],
            account_public_ids=[record["account_public_id"]],
            lead_public_ids=[record["lead_public_id"]],
        )


def _period_url(chain) -> str:
    return f"/api/work-orders/{chain['work_order_public_id']}/contract-period"


def _get_period(chain, username: str = "sales1"):
    return client.get(_period_url(chain), headers=auth_headers(username))


def _save_period(
    chain,
    *,
    expected_period_version: int | None = None,
    contract_start_date: str | None = START,
    contract_end_basis_code: str | None = "FIXED_DATE",
    contract_end_date: str | None = END,
    contract_notes: str | None = None,
    username: str = "sales1",
):
    return client.put(
        _period_url(chain),
        headers=auth_headers(username),
        json={
            "expected_period_version": expected_period_version,
            "contract_start_date": contract_start_date,
            "contract_end_basis_code": contract_end_basis_code,
            "contract_end_date": contract_end_date,
            "contract_notes": contract_notes,
        },
    )


def _extend(
    chain,
    *,
    new_end_date: str,
    received_date: str = "2027-03-01",
    customer_reference: str | None = "EXT/2027/01",
    extension_notes: str | None = None,
    username: str = "sales1",
    **extra,
):
    return client.post(
        f"/api/work-orders/{chain['work_order_public_id']}/contract-extensions",
        headers=auth_headers(username),
        json={
            "new_end_date": new_end_date,
            "received_date": received_date,
            "customer_reference": customer_reference,
            "extension_notes": extension_notes,
            **extra,
        },
    )


def _terms_url(chain, line_index: int = 0) -> str:
    return (
        f"/api/work-orders/{chain['work_order_public_id']}"
        f"/lines/{chain['line_public_ids'][line_index]}/billing-terms"
    )


def _add_terms(chain, *, line_index: int = 0, effective_from: str | None = None, expected_period_count: int = 0, terms=None):
    body = {
        "expected_period_count": expected_period_count,
        "expected_latest_term_revision": 1 if expected_period_count else None,
        "effective_from": effective_from,
        **(terms if terms is not None else {**SHIFT_TERMS, **(PART_2_FIRST_PERIOD_ONLY if not effective_from else {})}),
    }
    return client.post(_terms_url(chain, line_index), headers=auth_headers("sales1"), json=body)


def _save_line_detail(
    chain,
    *,
    line_index: int = 0,
    expected_detail_version: int | None = None,
    line_start_date: str | None = None,
    line_end_date: str | None = None,
    username: str = "sales1",
):
    return client.put(
        f"/api/work-orders/{chain['work_order_public_id']}/lines/{chain['line_public_ids'][line_index]}/detail",
        headers=auth_headers(username),
        json={
            "expected_detail_version": expected_detail_version,
            "customer_line_reference": "CUST-LINE-1",
            "line_start_date": line_start_date,
            "line_end_date": line_end_date,
        },
    )


def _observed(chain, public_id: str) -> list[dict]:
    """Every period the screen would have seen of one line - the same shape the source sends.

    A count plus the latest revision is not enough: neither changes when an EARLIER period is
    edited, so a concurrent edit would be deleted by the replacement (review round 2, finding F-07).
    """
    entry = next(
        (item for item in _billing_terms(chain) if item["work_order_line_public_id"] == public_id), None
    )
    return [
        {"term_public_id": period["term_public_id"], "term_revision": period["term_revision"]}
        for period in (entry["periods"] if entry else [])
    ]


def _source_periods(chain, source_index: int = 0) -> list[dict]:
    entry = next(
        item
        for item in _billing_terms(chain)
        if item["work_order_line_public_id"] == chain["line_public_ids"][source_index]
    )
    return [
        {"term_public_id": period["term_public_id"], "term_revision": period["term_revision"]}
        for period in entry["periods"]
    ]


def _copy(
    chain,
    *,
    source_index: int = 0,
    target_indexes: tuple[int, ...] = (1, 2),
    replace_existing_terms: bool = False,
    username: str = "sales1",
    target_ids: list[str] | None = None,
    targets: list[dict] | None = None,
    source_periods: list[dict] | None = None,
):
    """Post the copy. Everything is read live by default, so a test states only what it varies."""
    if targets is None:
        ids = (
            target_ids
            if target_ids is not None
            else [chain["line_public_ids"][index] for index in target_indexes]
        )
        targets = []
        for public_id in ids:
            observed = _observed(chain, public_id)
            targets.append(
                {
                    "work_order_line_public_id": public_id,
                    "observed_periods": observed,
                    # The screen confirms per line; a line with no terms is never asked about.
                    "replace_confirmed": replace_existing_terms and bool(observed),
                }
            )
    return client.post(
        f"{_terms_url(chain, source_index)}/apply-to-lines",
        headers=auth_headers(username),
        json={
            "targets": targets,
            "source_periods": (
                source_periods if source_periods is not None else _source_periods(chain, source_index)
            ),
        },
    )


def _billing_terms(chain, username: str = "sales1") -> list[dict]:
    response = client.get(
        f"/api/work-orders/{chain['work_order_public_id']}/billing-terms", headers=auth_headers(username)
    )
    assert response.status_code == 200, response.text
    return response.json()


def _events(work_order_public_id: str, event_name: str) -> list[dict]:
    """The stored payloads of one event name, read straight from the row rather than from a response,
    so what a later reader of the audit trail would see is what is asserted."""
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT event_payload_json FROM business_event WHERE record_type = 'work_order' "
                "AND record_public_id = :id AND event_name = :name ORDER BY id ASC"
            ),
            {"id": work_order_public_id, "name": event_name},
        ).fetchall()
    return [json.loads(row[0]) if row[0] else {} for row in rows]


# --- Recording the contract period ------------------------------------------------------------


def test_a_work_order_with_no_contract_period_reports_both_dates_missing(chain) -> None:
    response = _get_period(chain)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == PERIOD_KEYS
    assert body["period_public_id"] is None and body["period_version"] is None
    assert body["contract_state_code"] == "NOT_RECORDED"
    assert body["is_complete"] is False
    assert body["missing_items"] == ["CONTRACT_START", "CONTRACT_END"]
    assert body["extensions"] == []
    assert body["needs_firm_end_date"] is False


def test_recording_the_dates_starts_at_version_one_and_records_the_event(chain) -> None:
    response = _save_period(chain)
    assert response.status_code == 200, response.text
    body = response.json()
    period = body["contract_period"]
    assert period["period_version"] == 1
    assert period["contract_start_date"] == START and period["contract_end_date"] == END
    assert period["is_complete"] is True and period["missing_items"] == []
    assert body["event"]["event_name"] == "WorkOrderContractPeriodRecorded"
    payload = body["event"]["event_payload"]
    assert payload["contract_start_date"] == START and payload["contract_end_date"] == END
    assert set(payload["changed_fields"]) == {"contract_start_date", "contract_end_basis_code", "contract_end_date"}


def test_changing_the_dates_moves_the_version_and_records_the_changed_event(chain) -> None:
    _save_period(chain)
    response = _save_period(chain, expected_period_version=1, contract_end_date="2027-06-30")
    assert response.status_code == 200, response.text
    assert response.json()["contract_period"]["period_version"] == 2
    assert response.json()["event"]["event_name"] == "WorkOrderContractPeriodUpdated"
    assert response.json()["event"]["event_payload"]["changed_fields"] == ["contract_end_date"]


def test_an_identical_save_is_not_an_edit(chain) -> None:
    """No version bump and no event, as everywhere else in this module."""
    _save_period(chain)
    response = _save_period(chain, expected_period_version=1)
    assert response.status_code == 200, response.text
    assert response.json()["contract_period"]["period_version"] == 1
    assert response.json()["event"] is None


def test_a_save_against_a_version_someone_else_moved_is_refused(chain) -> None:
    _save_period(chain)
    response = _save_period(chain, expected_period_version=None, contract_end_date="2027-06-30")
    assert response.status_code == 409, response.text
    assert "Reload" in response.json()["detail"]


def test_the_state_reads_as_the_owner_asked(chain) -> None:
    """Not started, active, ends in N days, ended (owner decision 17)."""
    today = TODAY
    future = _save_period(
        chain,
        contract_start_date=(today + timedelta(days=10)).isoformat(),
        contract_end_date=(today + timedelta(days=40)).isoformat(),
    ).json()["contract_period"]
    assert future["contract_state_code"] == "NOT_STARTED"
    assert future["days_until_start"] == 10

    running = _save_period(
        chain,
        expected_period_version=1,
        contract_start_date=(today - timedelta(days=5)).isoformat(),
        contract_end_date=(today + timedelta(days=12)).isoformat(),
    ).json()["contract_period"]
    assert running["contract_state_code"] == "ACTIVE"
    assert running["contract_state_label"].startswith("Active, ends in 12 days")

    over = _save_period(
        chain,
        expected_period_version=2,
        contract_start_date=(today - timedelta(days=50)).isoformat(),
        contract_end_date=(today - timedelta(days=1)).isoformat(),
    ).json()["contract_period"]
    assert over["contract_state_code"] == "ENDED"


# --- "Until the work is complete" (owner decision 14) -------------------------------------------


def test_until_the_work_is_complete_is_a_recorded_answer_not_a_missing_one(chain) -> None:
    response = _save_period(chain, contract_end_basis_code="UNTIL_WORK_COMPLETE", contract_end_date=None)
    assert response.status_code == 200, response.text
    period = response.json()["contract_period"]
    assert period["contract_end_basis_code"] == "UNTIL_WORK_COMPLETE"
    assert period["contract_end_date"] is None
    assert period["missing_items"] == [] and period["is_complete"] is True
    # ...but the Work Order still cannot be closed, which the screen says in those words.
    assert period["needs_firm_end_date"] is True


def test_leaving_the_end_blank_is_different_from_recording_until_the_work_is_complete(chain) -> None:
    """Owner decision 14's whole point: one is an answer, the other is not."""
    response = _save_period(
        chain,
        contract_start_date=(TODAY - timedelta(days=5)).isoformat(),
        contract_end_basis_code=None,
        contract_end_date=None,
    )
    assert response.status_code == 200, response.text
    period = response.json()["contract_period"]
    assert period["missing_items"] == ["CONTRACT_END"]
    assert period["needs_firm_end_date"] is False
    assert period["contract_state_label"] == "Active, no end date recorded"


def test_a_fixed_end_needs_a_date_and_until_work_complete_refuses_one(chain) -> None:
    missing = _save_period(chain, contract_end_basis_code="FIXED_DATE", contract_end_date=None)
    assert missing.status_code == 422
    assert "until the work is complete" in missing.json()["detail"]

    both = _save_period(chain, contract_end_basis_code="UNTIL_WORK_COMPLETE", contract_end_date=END)
    assert both.status_code == 422
    assert "has no end date" in both.json()["detail"]


def test_an_end_date_with_no_answer_beside_it_is_refused(chain) -> None:
    response = _save_period(chain, contract_end_basis_code=None, contract_end_date=END)
    assert response.status_code == 422
    assert "fixed date or runs until the work is complete" in response.json()["detail"]


def test_an_unknown_end_basis_is_refused(chain) -> None:
    assert _save_period(chain, contract_end_basis_code="WHENEVER").status_code == 422


def test_the_contract_cannot_end_before_it_starts(chain) -> None:
    response = _save_period(chain, contract_start_date="2027-03-31", contract_end_date="2027-01-01")
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The contract cannot end on 1 January 2027, before it starts on 31 March 2027."
    )


# --- Extensions (owner decisions 15 and 16) -----------------------------------------------------


def test_an_extension_moves_the_end_date_and_keeps_what_it_was_before(chain) -> None:
    _save_period(chain)
    response = _extend(chain, new_end_date="2027-06-30")
    assert response.status_code == 201, response.text
    period = response.json()["contract_period"]
    assert period["contract_end_date"] == "2027-06-30"
    assert len(period["extensions"]) == 1
    extension = period["extensions"][0]
    assert set(extension) == EXTENSION_KEYS
    assert extension["extension_sequence_no"] == 1
    assert extension["previous_end_date"] == END
    assert extension["previous_end_basis_code"] == "FIXED_DATE"
    assert extension["new_end_date"] == "2027-06-30"
    assert extension["customer_reference"] == "EXT/2027/01"
    assert extension["received_date"] == "2027-03-01"
    assert extension["created_by_display_name"]
    assert response.json()["event"]["event_name"] == "WorkOrderContractExtensionRecorded"


def test_earlier_end_dates_stay_as_history_and_are_never_overwritten(chain) -> None:
    """Owner decision 15: what the contract said at any time is always recoverable."""
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30", customer_reference="EXT/1")
    response = _extend(chain, new_end_date="2027-09-30", customer_reference="EXT/2")
    assert response.status_code == 201, response.text
    extensions = response.json()["contract_period"]["extensions"]
    assert [item["extension_sequence_no"] for item in extensions] == [1, 2]
    assert [item["previous_end_date"] for item in extensions] == [END, "2027-06-30"]
    assert [item["new_end_date"] for item in extensions] == ["2027-06-30", "2027-09-30"]


@pytest.mark.parametrize(
    ("new_end_date", "named"),
    [(END, "31 March 2027"), ("2027-03-15", "15 March 2027")],
)
def test_an_extension_must_move_the_end_later(chain, new_end_date, named) -> None:
    """Owner, 22 September 2026, replacing the 17 September rule that any other date was accepted:
    a mistake is now put right by removing the extension, so an extension only ever extends."""
    _save_period(chain)
    response = _extend(chain, new_end_date=new_end_date)
    assert response.status_code == 422
    assert response.json()["detail"] == (
        f"An extension must move the end date later. The contract currently ends on 31 March 2027, "
        f"so {named} would not extend it. To correct an extension recorded in error, remove it instead."
    )


# --- The end date moves only through extensions, and the latest can be removed (22 September) ----


def _remove_extension(chain, extension_public_id: str, username: str = "sales1"):
    return client.delete(
        f"/api/work-orders/{chain['work_order_public_id']}/contract-extensions/{extension_public_id}",
        headers=auth_headers(username),
    )


def _extension_ids(chain) -> list[str]:
    return [item["extension_public_id"] for item in _get_period(chain).json()["extensions"]]


_END_LOCKED = (
    "Once an extension has been recorded, the contract end date changes only through extensions. "
    "Record another extension, or remove the latest one."
)


def test_once_an_extension_exists_the_form_cannot_change_the_end_date(chain) -> None:
    """The owner's screen check found a form save silently undoing two extensions. It cannot now."""
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30")
    for changes in (
        {"contract_end_date": "2027-12-31"},
        {"contract_end_date": "2027-05-31"},
        {"contract_end_basis_code": "UNTIL_WORK_COMPLETE", "contract_end_date": None},
        {"contract_end_basis_code": None, "contract_end_date": None},
    ):
        response = _save_period(chain, expected_period_version=2, **changes)
        assert response.status_code == 422, changes
        assert response.json()["detail"] == _END_LOCKED
    assert _get_period(chain).json()["contract_end_date"] == "2027-06-30"


def test_the_start_and_the_notes_stay_editable_after_an_extension(chain) -> None:
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30")
    response = _save_period(
        chain,
        expected_period_version=2,
        contract_start_date="2027-01-15",
        contract_end_date="2027-06-30",
        contract_notes="Start agreed later",
    )
    assert response.status_code == 200, response.text
    period = response.json()["contract_period"]
    assert period["contract_start_date"] == "2027-01-15"
    assert period["contract_end_date"] == "2027-06-30"
    assert period["contract_notes"] == "Start agreed later"


def test_removing_the_latest_extension_puts_the_end_back(chain) -> None:
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30", customer_reference="EXT/1")
    _extend(chain, new_end_date="2027-09-30", customer_reference="EXT/2")
    first, second = _extension_ids(chain)

    response = _remove_extension(chain, second)
    assert response.status_code == 200, response.text
    period = response.json()["contract_period"]
    assert period["contract_end_date"] == "2027-06-30"
    assert [item["extension_public_id"] for item in period["extensions"]] == [first]
    assert response.json()["event"]["event_name"] == "WorkOrderContractExtensionRemoved"

    response = _remove_extension(chain, first)
    assert response.status_code == 200, response.text
    period = response.json()["contract_period"]
    assert period["contract_end_date"] == END
    assert period["contract_end_basis_code"] == "FIXED_DATE"
    assert period["extensions"] == []


def test_with_every_extension_removed_the_end_date_is_editable_again(chain) -> None:
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30")
    _remove_extension(chain, _extension_ids(chain)[0])
    version = _get_period(chain).json()["period_version"]
    response = _save_period(chain, expected_period_version=version, contract_end_date="2027-04-30")
    assert response.status_code == 200, response.text
    assert response.json()["contract_period"]["contract_end_date"] == "2027-04-30"


def test_a_mistyped_extension_is_put_right_by_removing_it(chain) -> None:
    """The case the 17 September rule existed for: a typed 2037 is still never a dead end."""
    _save_period(chain)
    assert _extend(chain, new_end_date="2037-06-30").status_code == 201
    assert _remove_extension(chain, _extension_ids(chain)[0]).status_code == 200
    corrected = _extend(chain, new_end_date="2027-06-30", customer_reference="EXT/1 corrected")
    assert corrected.status_code == 201, corrected.text
    period = corrected.json()["contract_period"]
    assert [item["new_end_date"] for item in period["extensions"]] == ["2027-06-30"]
    assert period["extensions"][0]["extension_sequence_no"] == 1
    assert period["extensions"][0]["previous_end_date"] == END


def test_the_removal_is_kept_in_the_audit_trail(chain) -> None:
    """The row goes; the event is what keeps the fact that it existed, and what it said."""
    _save_period(chain)
    _extend(chain, new_end_date="2037-06-30", customer_reference="EXT/SECRET/9")
    _remove_extension(chain, _extension_ids(chain)[0])
    recorded = _events(chain["work_order_public_id"], "WorkOrderContractExtensionRecorded")
    removed = _events(chain["work_order_public_id"], "WorkOrderContractExtensionRemoved")
    assert len(recorded) == 1 and len(removed) == 1
    assert removed[0]["extension_public_id"] == recorded[0]["extension_public_id"]
    assert removed[0]["extension_sequence_no"] == 1
    assert removed[0]["removed_new_end_date"] == "2037-06-30"
    assert removed[0]["restored_end_basis_code"] == "FIXED_DATE"
    assert removed[0]["restored_end_date"] == END
    assert "EXT/SECRET/9" not in str(removed[0])


def test_only_the_latest_extension_can_be_removed(chain) -> None:
    """Exactly as only the latest billing-terms period can: a gap in the middle of the chain would no
    longer explain how the current end was reached."""
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30")
    _extend(chain, new_end_date="2027-09-30")
    first, _ = _extension_ids(chain)
    response = _remove_extension(chain, first)
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Only the most recent extension can be removed. Extension 2 is the most recent; "
        "reload if you did not expect that."
    )
    assert len(_extension_ids(chain)) == 2


def test_an_extension_already_removed_or_unknown_is_not_found(chain) -> None:
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30")
    only = _extension_ids(chain)[0]
    assert _remove_extension(chain, only).status_code == 200
    assert _remove_extension(chain, only).status_code == 404
    assert _remove_extension(chain, str(uuid4())).status_code == 404


def test_removing_an_extension_restores_an_open_ended_contract(chain) -> None:
    _save_period(chain, contract_end_basis_code="UNTIL_WORK_COMPLETE", contract_end_date=None)
    _extend(chain, new_end_date="2027-06-30")
    response = _remove_extension(chain, _extension_ids(chain)[0])
    assert response.status_code == 200, response.text
    period = response.json()["contract_period"]
    assert period["contract_end_basis_code"] == "UNTIL_WORK_COMPLETE"
    assert period["contract_end_date"] is None
    assert period["needs_firm_end_date"] is True


def test_removing_the_only_extension_of_an_undated_contract_leaves_the_end_unanswered(chain) -> None:
    _extend(chain, new_end_date="2027-06-30")
    response = _remove_extension(chain, _extension_ids(chain)[0])
    assert response.status_code == 200, response.text
    period = response.json()["contract_period"]
    assert period["contract_end_basis_code"] is None
    assert period["contract_end_date"] is None
    assert "CONTRACT_END" in period["missing_items"]


def test_an_extension_cannot_be_removed_when_the_old_end_would_exclude_a_period(chain) -> None:
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30")
    _add_terms(chain)
    _add_terms(chain, effective_from="2027-05-01", expected_period_count=1)
    response = _remove_extension(chain, _extension_ids(chain)[0])
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "This extension cannot be removed. The contract cannot end on 31 March 2027, "
        "because line 1 has terms starting 1 May 2027."
    )
    assert _get_period(chain).json()["contract_end_date"] == "2027-06-30"


def test_an_extension_cannot_be_removed_when_the_old_end_is_before_a_later_start(chain) -> None:
    """Removal's own backstop. Moving the start past the end an extension continued from is now refused
    at the start (see test_the_contract_start_cannot_move_past_the_end_an_extension_continued_from), so
    this state is set directly, as data written before that rule could hold it."""
    _save_period(chain)
    _extend(chain, new_end_date="2027-12-31", received_date="2027-07-01")
    with SessionLocal() as db:
        db.execute(
            text(
                "UPDATE crm_work_order_contract_period SET contract_start_date = DATE '2027-06-01' "
                "WHERE work_order_id = (SELECT id FROM crm_work_order WHERE work_order_public_id = :id)"
            ),
            {"id": chain["work_order_public_id"]},
        )
        db.commit()
    response = _remove_extension(chain, _extension_ids(chain)[0])
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "This extension cannot be removed. The contract would end on 31 March 2027, "
        "before it starts on 1 June 2027."
    )


# --- An extension's own start date, and the gap a later one leaves (22 September 2026) ----------


def test_an_extension_starts_the_day_after_the_end_it_follows_unless_told_otherwise(chain) -> None:
    """Owner: generally the extension start date is a day after the Work Order's close date."""
    _save_period(chain)
    response = _extend(chain, new_end_date="2027-06-30")
    assert response.status_code == 201, response.text
    period = response.json()["contract_period"]
    assert period["extensions"][0]["extension_start_date"] == "2027-04-01"
    assert period["gaps"] == []
    payload = _events(chain["work_order_public_id"], "WorkOrderContractExtensionRecorded")[0]
    assert payload["extension_start_date"] == "2027-04-01"
    assert payload["starts_after_a_gap"] is False


def test_the_day_after_given_explicitly_needs_no_confirmation(chain) -> None:
    _save_period(chain)
    assert _extend(chain, new_end_date="2027-06-30", extension_start_date="2027-04-01").status_code == 201


@pytest.mark.parametrize("start", [END, "2027-03-15"])
def test_an_extension_cannot_start_on_or_before_the_current_end(chain, start) -> None:
    _save_period(chain)
    response = _extend(chain, new_end_date="2027-06-30", extension_start_date=start)
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "An extension must start after the contract's current end date, 31 March 2027. "
        "It normally starts the day after, on 1 April 2027."
    )


def test_a_later_start_is_refused_until_the_user_confirms_it(chain) -> None:
    """Owner: a later start needs confirmation, else it can be recorded."""
    _save_period(chain)
    response = _extend(chain, new_end_date="2027-06-30", extension_start_date="2027-04-15")
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "This extension starts on 15 April 2027, not on 1 April 2027, the day after the contract ends. "
        "The days from 1 April 2027 to 14 April 2027 would be outside the contract. Confirm that to record it."
    )
    assert _get_period(chain).json()["extensions"] == []


def test_a_confirmed_later_start_is_recorded_with_its_gap(chain) -> None:
    _save_period(chain)
    response = _extend(chain, new_end_date="2027-06-30", extension_start_date="2027-04-15", gap_confirmed_from="2027-04-01")
    assert response.status_code == 201, response.text
    period = response.json()["contract_period"]
    assert period["extensions"][0]["extension_start_date"] == "2027-04-15"
    assert period["contract_end_date"] == "2027-06-30"
    assert period["gaps"] == [{"first_day": "2027-04-01", "last_day": "2027-04-14", "extension_sequence_no": 1}]
    payload = _events(chain["work_order_public_id"], "WorkOrderContractExtensionRecorded")[0]
    assert payload["starts_after_a_gap"] is True


def test_a_confirmation_given_for_other_days_is_refused_as_out_of_date(chain) -> None:
    """The screen sends the first day of the gap it showed. If another user's extension has moved the
    end since, the gap is a different one, and the user did not agree to it."""
    _save_period(chain)
    # The page was read when the contract ended on 31 March; meanwhile someone extends it to 10 April.
    assert _extend(chain, new_end_date="2027-04-10").status_code == 201
    response = _extend(
        chain, new_end_date="2027-06-30", extension_start_date="2027-04-15", gap_confirmed_from="2027-04-01"
    )
    assert response.status_code == 409
    assert response.json()["detail"].startswith("The contract end date changed after you opened this page")
    assert len(_get_period(chain).json()["extensions"]) == 1


def test_a_confirmation_is_ignored_when_the_extension_runs_straight_on(chain) -> None:
    _save_period(chain)
    response = _extend(
        chain, new_end_date="2027-06-30", extension_start_date="2027-04-01", gap_confirmed_from="2027-04-01"
    )
    assert response.status_code == 201, response.text
    assert response.json()["contract_period"]["gaps"] == []


def test_an_extension_cannot_start_after_its_own_end(chain) -> None:
    _save_period(chain)
    response = _extend(chain, new_end_date="2027-06-30", extension_start_date="2027-07-01", gap_confirmed_from="2027-04-01")
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The extension cannot start on 1 July 2027, after its own end date of 30 June 2027."
    )


@pytest.mark.parametrize("recorded", ["until_complete", "nothing"])
def test_a_start_date_is_refused_where_there_is_no_fixed_end_to_follow(chain, recorded) -> None:
    if recorded == "until_complete":
        _save_period(chain, contract_end_basis_code="UNTIL_WORK_COMPLETE", contract_end_date=None)
    response = _extend(chain, new_end_date="2027-06-30", extension_start_date="2027-04-01")
    assert response.status_code == 422
    assert response.json()["detail"].startswith(
        "An extension start date applies only when the contract has a fixed end date to continue from."
    )


def test_a_period_cannot_start_in_a_gap(chain) -> None:
    """Owner: the days in between are outside the contract."""
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30", extension_start_date="2027-04-15", gap_confirmed_from="2027-04-01")
    _add_terms(chain)
    response = _add_terms(chain, effective_from="2027-04-05", expected_period_count=1)
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "This period starts on 5 April 2027, when no contract runs: the contract ended on 31 March 2027, "
        "and extension 1 starts on 15 April 2027."
    )
    assert _add_terms(chain, effective_from="2027-04-15", expected_period_count=1).status_code == 201


def test_a_lines_own_dates_cannot_fall_in_a_gap_but_may_span_one(chain) -> None:
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30", extension_start_date="2027-04-15", gap_confirmed_from="2027-04-01")
    response = _save_line_detail(chain, line_start_date="2027-02-01", line_end_date="2027-04-10")
    assert response.status_code == 422
    assert response.json()["detail"].startswith("This line ends on 10 April 2027, when no contract runs")
    assert _save_line_detail(chain, line_start_date="2027-02-01", line_end_date="2027-05-31").status_code == 200


def test_today_in_a_gap_reads_as_not_running(chain) -> None:
    today = TODAY
    _save_period(
        chain,
        contract_start_date=(today - timedelta(days=60)).isoformat(),
        contract_end_date=(today - timedelta(days=5)).isoformat(),
    )
    response = _extend(
        chain,
        new_end_date=(today + timedelta(days=90)).isoformat(),
        received_date=today.isoformat(),
        extension_start_date=(today + timedelta(days=3)).isoformat(),
        gap_confirmed_from=(today - timedelta(days=4)).isoformat(),
    )
    assert response.status_code == 201, response.text
    period = response.json()["contract_period"]
    assert period["contract_state_code"] == "BETWEEN_EXTENSIONS"
    assert period["contract_state_label"].startswith("Not running: extension 1 starts in 3 days")


def test_removing_an_extension_removes_its_gap(chain) -> None:
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30", extension_start_date="2027-04-15", gap_confirmed_from="2027-04-01")
    response = _remove_extension(chain, _extension_ids(chain)[0])
    assert response.status_code == 200, response.text
    assert response.json()["contract_period"]["gaps"] == []
    assert response.json()["contract_period"]["contract_end_date"] == END


def test_the_contract_start_cannot_move_past_the_end_an_extension_continued_from(chain) -> None:
    """Found while working the owner's clarification through, and closed with it. A late order - one
    received after the contract ended - is recorded normally, so its received date does not stop the
    start moving; this does. Otherwise the contract would start after the end it was extended from."""
    _save_period(chain)
    assert _extend(chain, new_end_date="2027-12-31", received_date="2027-05-01").status_code == 201
    response = _save_period(
        chain, expected_period_version=2, contract_start_date="2027-04-15", contract_end_date="2027-12-31"
    )
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The contract cannot start on 15 April 2027, because extension 1 continues from an end date of 31 March 2027."
    )


@pytest.mark.parametrize(
    "basis, previous_date, start, new_end",
    [
        ("FIXED_DATE", "2027-03-31", None, "2028-01-01"),
        ("FIXED_DATE", "2027-03-31", "2027-03-31", "2028-01-01"),
        ("FIXED_DATE", "2027-03-31", "2028-02-01", "2028-01-01"),
        (None, None, "2027-04-01", "2028-01-01"),
    ],
)
def test_the_database_refuses_an_extension_start_that_does_not_follow_its_previous_end(
    chain, basis, previous_date, start, new_end
) -> None:
    """A start is required after a fixed end, falls after it and not after the new end, and is absent
    where there was no fixed end. Each row satisfies every other constraint."""
    from sqlalchemy.exc import IntegrityError

    with SessionLocal() as db:
        work_order_id = db.execute(
            text("SELECT id FROM crm_work_order WHERE work_order_public_id = :id"),
            {"id": chain["work_order_public_id"]},
        ).scalar_one()
        with pytest.raises(IntegrityError) as excinfo:
            db.execute(
                text(
                    """
                    INSERT INTO crm_work_order_contract_extension (
                        work_order_contract_extension_public_id, work_order_id, extension_sequence_no,
                        previous_end_basis_code, previous_end_date, new_end_date, received_date,
                        extension_start_date
                    ) VALUES (:pid, :wo, 99, :basis, :prev, :new_end, DATE '2027-01-01', :start)
                    """
                ),
                {
                    "pid": str(uuid4()),
                    "wo": work_order_id,
                    "basis": basis,
                    "prev": previous_date,
                    "start": start,
                    "new_end": new_end,
                },
            )
        assert "ck_wo_contract_extension_start_follows_previous_end" in str(excinfo.value)
        db.rollback()


# --- When an extension order may have been received (22 September 2026) -----------------------


def test_an_order_received_after_the_contract_ended_is_recorded_normally(chain) -> None:
    """Owner: a verbal commitment may come first and the order arrive after the Work Order's last
    date; it is entered on the day it arrives, and the extension still starts the day after."""
    _save_period(chain)
    response = _extend(chain, new_end_date="2027-06-30", received_date="2027-04-06")
    assert response.status_code == 201, response.text
    extension = response.json()["contract_period"]["extensions"][0]
    assert extension["received_date"] == "2027-04-06"
    assert extension["extension_start_date"] == "2027-04-01"


def test_an_extension_order_dated_before_the_contract_starts_is_refused(chain) -> None:
    _save_period(chain)
    response = _extend(chain, new_end_date="2027-06-30", received_date="2026-12-15")
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "This extension order is dated 15 December 2026, before the contract starts on 1 January 2027."
    )


@pytest.mark.parametrize("received_date", [START, "2027-05-01", "2027-12-31"])
def test_an_extension_order_may_carry_any_other_date(chain, received_date) -> None:
    """Owner: "any date but not before the contract start date". An order dated long ago is only
    warned about on the screen; the server does not refuse it."""
    _save_period(chain)
    response = _extend(chain, new_end_date="2027-06-30", received_date=received_date)
    assert response.status_code == 201, response.text


def test_an_order_date_is_not_refused_while_the_contract_has_no_start(chain) -> None:
    _save_period(chain, contract_start_date=None)
    assert _extend(chain, new_end_date="2027-06-30", received_date="2020-01-01").status_code == 201


def test_the_contract_start_cannot_move_past_an_extension_orders_date(chain) -> None:
    """The same rule read from the other side, naming the extension."""
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30", received_date="2027-03-01")
    response = _save_period(
        chain, expected_period_version=2, contract_start_date="2027-04-01", contract_end_date="2027-06-30"
    )
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The contract cannot start on 1 April 2027, because extension 1's order was received on 1 March 2027."
    )


def test_an_extension_cannot_end_the_contract_before_it_starts(chain) -> None:
    """Against a fixed end this is refused first as not extending it; against an open-ended contract
    there is no current end to compare with, so the start is what refuses it."""
    _save_period(chain, contract_end_basis_code="UNTIL_WORK_COMPLETE", contract_end_date=None)
    response = _extend(chain, new_end_date="2026-12-01")
    assert response.status_code == 422
    assert "before it starts on 1 January 2027" in response.json()["detail"]


def test_an_extension_against_an_open_ended_contract_records_no_previous_end(chain) -> None:
    _save_period(chain, contract_end_basis_code="UNTIL_WORK_COMPLETE", contract_end_date=None)
    response = _extend(chain, new_end_date="2027-06-30")
    assert response.status_code == 201, response.text
    period = response.json()["contract_period"]
    assert period["contract_end_basis_code"] == "FIXED_DATE"
    assert period["needs_firm_end_date"] is False
    extension = period["extensions"][0]
    assert extension["previous_end_basis_code"] == "UNTIL_WORK_COMPLETE"
    assert extension["previous_end_date"] is None


def test_an_extension_before_any_contract_dates_records_the_end_date_it_gives(chain) -> None:
    """Truthful rather than tidy: the customer did send an end date."""
    response = _extend(chain, new_end_date="2027-06-30")
    assert response.status_code == 201, response.text
    period = response.json()["contract_period"]
    assert period["contract_end_date"] == "2027-06-30"
    assert period["contract_start_date"] is None
    assert period["extensions"][0]["previous_end_date"] is None
    assert period["extensions"][0]["previous_end_basis_code"] is None


def test_the_extension_event_carries_no_customer_reference_text(chain) -> None:
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30", customer_reference="EXT/SECRET/9")
    payloads = _events(chain["work_order_public_id"], "WorkOrderContractExtensionRecorded")
    assert len(payloads) == 1
    assert payloads[0]["has_customer_reference"] is True
    assert "EXT/SECRET/9" not in str(payloads[0])


# --- A period cannot start outside the contract (owner decision 17) ----------------------------


def test_a_later_period_starting_after_the_contract_ends_is_refused(chain) -> None:
    _save_period(chain)
    _add_terms(chain)
    response = _add_terms(chain, effective_from="2027-05-01", expected_period_count=1)
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "This period starts on 1 May 2027, after the contract ends on 31 March 2027."
    )


def test_every_period_ordering_refusal_names_the_dates(chain) -> None:
    """Owner decision 17: every refusal says why, naming the dates. All four ordering refusals in
    _check_period_start are exercised here, each with an entered date DISTINCT from the one it clashes
    with, so the assertion shows both dates are named rather than one date that happens to be both.

    Round 1 left one refusal generic, which round 2 caught (F-06). Round 2's version of this test then
    claimed to walk all four refusals and walked three - the on-or-after-the-next-period branch was
    never reached, and its "previous period" case used the same date on both sides - which round 3
    caught (F-10)."""
    _add_terms(chain)
    # 1. The first calendar date has no day before it, so it is refused - by name, like the rest.
    lowest = _add_terms(chain, effective_from="0001-01-01", expected_period_count=1)
    assert lowest.status_code == 422
    assert "1 January 1" in lowest.json()["detail"]

    added = _add_terms(chain, effective_from="2027-06-01", expected_period_count=1)
    assert added.status_code == 201, added.text

    # 2. On or before the period before it.
    clash = _add_terms(chain, effective_from="2027-05-01", expected_period_count=2)
    assert clash.status_code == 422
    detail = clash.json()["detail"]
    assert "1 May 2027" in detail and "1 June 2027" in detail
    assert "previous period" in detail

    # 3. On or after the period after it. Only a MIDDLE period has a period after it, so this needs
    #    three periods, then the middle one moved past the third.
    third = _add_terms(chain, effective_from="2027-09-01", expected_period_count=2)
    assert third.status_code == 201, third.text
    periods = third.json()["line_billing_terms"]["periods"]
    assert [period["period_number"] for period in periods] == [1, 2, 3]
    middle = periods[1]
    moved = client.put(
        f"{_terms_url(chain)}/{middle['term_public_id']}",
        headers=auth_headers("sales1"),
        json={
            "expected_term_revision": middle["term_revision"],
            "effective_from": "2027-10-01",
            **SHIFT_TERMS,
        },
    )
    assert moved.status_code == 422
    detail = moved.json()["detail"]
    assert "1 October 2027" in detail and "1 September 2027" in detail
    assert "next period" in detail

    # 4. Period 1 has no date of its own, and the refusal says which date to remove.
    first = periods[0]
    dated_first = client.put(
        f"{_terms_url(chain)}/{first['term_public_id']}",
        headers=auth_headers("sales1"),
        json={
            "expected_term_revision": first["term_revision"],
            "effective_from": "2027-03-01",
            **{**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY},
        },
    )
    assert dated_first.status_code == 422
    assert "1 March 2027" in dated_first.json()["detail"]


def test_a_later_period_starting_before_the_contract_starts_is_refused(chain) -> None:
    """The same rule read the other way: dates are often entered before the contract is."""
    _save_period(chain)
    _add_terms(chain)
    response = _add_terms(chain, effective_from="2026-12-01", expected_period_count=1)
    assert response.status_code == 422
    assert "before the contract starts on 1 January 2027" in response.json()["detail"]


def test_a_period_inside_the_contract_is_accepted(chain) -> None:
    _save_period(chain)
    _add_terms(chain)
    assert _add_terms(chain, effective_from="2027-02-01", expected_period_count=1).status_code == 201


def test_a_period_is_not_refused_while_the_contract_has_no_dates(chain) -> None:
    """NOT_DETERMINED is not a refusal: nothing is known to be broken."""
    _add_terms(chain)
    assert _add_terms(chain, effective_from="2030-05-01", expected_period_count=1).status_code == 201


def test_changing_a_period_is_checked_against_the_contract_too(chain) -> None:
    _save_period(chain)
    _add_terms(chain)
    added = _add_terms(chain, effective_from="2027-02-01", expected_period_count=1)
    term_public_id = added.json()["line_billing_terms"]["periods"][-1]["term_public_id"]
    response = client.put(
        f"{_terms_url(chain)}/{term_public_id}",
        headers=auth_headers("sales1"),
        json={"expected_term_revision": 1, "effective_from": "2027-05-01", **SHIFT_TERMS},
    )
    assert response.status_code == 422
    assert "after the contract ends on 31 March 2027" in response.json()["detail"]


# --- The contract cannot move to exclude what is already recorded ------------------------------


def test_the_contract_end_cannot_move_before_a_period_that_starts_later(chain) -> None:
    """Owner decision 17's own example, with the line named."""
    _save_period(chain)
    _add_terms(chain)
    _add_terms(chain, effective_from="2027-03-01", expected_period_count=1)
    response = _save_period(chain, expected_period_version=1, contract_end_date="2027-02-01")
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The contract cannot end on 1 February 2027, because line 1 has terms starting 1 March 2027."
    )


def test_the_contract_start_cannot_move_past_a_period_that_starts_earlier(chain) -> None:
    _save_period(chain)
    _add_terms(chain)
    _add_terms(chain, effective_from="2027-02-01", expected_period_count=1)
    response = _save_period(chain, expected_period_version=1, contract_start_date="2027-03-01")
    assert response.status_code == 422
    assert "because line 1 has terms starting 1 February 2027" in response.json()["detail"]


def test_an_extension_cannot_move_the_end_before_a_period_that_starts_later(chain) -> None:
    """Reachable only from an open-ended contract now: from a fixed end, an earlier date is refused as
    not extending it before this check is reached."""
    _save_period(chain, contract_end_basis_code="UNTIL_WORK_COMPLETE", contract_end_date=None)
    _add_terms(chain)
    _add_terms(chain, effective_from="2027-06-01", expected_period_count=1)
    response = _extend(chain, new_end_date="2027-04-30")
    assert response.status_code == 422
    assert "because line 1 has terms starting 1 June 2027" in response.json()["detail"]


def test_the_contract_cannot_move_to_exclude_a_lines_own_dates(chain) -> None:
    _save_period(chain)
    assert _save_line_detail(chain, line_start_date="2027-02-01", line_end_date="2027-03-15").status_code == 200
    response = _save_period(chain, expected_period_version=1, contract_end_date="2027-02-28")
    assert response.status_code == 422
    assert "because line 1 ends on 15 March 2027" in response.json()["detail"]


# --- A line's own dates (owner decision 13) ----------------------------------------------------


def test_a_line_may_carry_its_own_dates_inside_the_contract(chain) -> None:
    _save_period(chain)
    response = _save_line_detail(chain, line_start_date="2027-02-01", line_end_date="2027-03-01")
    assert response.status_code == 200, response.text
    detail = response.json()["line_detail"]
    assert detail["line_start_date"] == "2027-02-01" and detail["line_end_date"] == "2027-03-01"
    payload = response.json()["event"]["event_payload"]
    assert payload["line_start_date"] == "2027-02-01" and payload["line_end_date"] == "2027-03-01"


def test_a_line_left_blank_follows_the_work_order_and_is_never_reported_missing(chain) -> None:
    _save_period(chain)
    response = _save_line_detail(chain)
    assert response.status_code == 200, response.text
    detail = response.json()["line_detail"]
    assert detail["line_start_date"] is None and detail["line_end_date"] is None
    assert "LINE_START_DATE" not in detail["missing_items"]
    assert "LINE_DATES" not in detail["missing_items"]


@pytest.mark.parametrize(
    "line_start, line_end, fragment",
    [
        ("2026-12-01", None, "before the contract starts on 1 January 2027"),
        (None, "2027-05-01", "after the contract ends on 31 March 2027"),
        ("2027-04-01", "2027-05-01", "after the contract ends on 31 March 2027"),
    ],
)
def test_a_lines_dates_outside_the_contract_are_refused(chain, line_start, line_end, fragment) -> None:
    _save_period(chain)
    response = _save_line_detail(chain, line_start_date=line_start, line_end_date=line_end)
    assert response.status_code == 422
    assert fragment in response.json()["detail"]


def test_a_line_cannot_end_before_it_starts(chain) -> None:
    _save_period(chain)
    response = _save_line_detail(chain, line_start_date="2027-03-01", line_end_date="2027-02-01")
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "This line cannot end on 1 February 2027, before it starts on 1 March 2027."
    )


def test_a_lines_dates_are_not_refused_while_the_contract_has_no_dates(chain) -> None:
    assert _save_line_detail(chain, line_start_date="2030-01-01", line_end_date="2030-06-30").status_code == 200


def test_a_caller_that_omits_the_date_fields_does_not_clear_them(chain) -> None:
    """Independent review round 1, finding F-03. The line-detail route is a whole replacement, so
    adding two fields to it made every caller written against the earlier shape - the smoke-data
    harness's own set_work_order_line_detail among them - silently erase dates nobody touched."""
    _save_period(chain)
    saved = _save_line_detail(chain, line_start_date="2027-02-01", line_end_date="2027-03-01")
    assert saved.status_code == 200, saved.text
    version = saved.json()["line_detail"]["detail_version"]

    # Exactly the payload a pre-Part-3 client sends: every field it knows about, neither date field.
    response = client.put(
        f"/api/work-orders/{chain['work_order_public_id']}/lines/{chain['line_public_ids'][0]}/detail",
        headers=auth_headers("sales1"),
        json={"expected_detail_version": version, "customer_line_reference": "CHANGED-BY-OLD-CLIENT"},
    )
    assert response.status_code == 200, response.text
    detail = response.json()["line_detail"]
    assert detail["customer_line_reference"] == "CHANGED-BY-OLD-CLIENT"
    assert detail["line_start_date"] == "2027-02-01"
    assert detail["line_end_date"] == "2027-03-01"


def test_an_explicit_null_still_clears_a_line_date(chain) -> None:
    """Omitting keeps; sending null clears. Both have to work, or a date could never be removed."""
    _save_period(chain)
    saved = _save_line_detail(chain, line_start_date="2027-02-01", line_end_date="2027-03-01")
    version = saved.json()["line_detail"]["detail_version"]
    response = _save_line_detail(
        chain, expected_detail_version=version, line_start_date=None, line_end_date=None
    )
    assert response.status_code == 200, response.text
    assert response.json()["line_detail"]["line_start_date"] is None
    assert response.json()["line_detail"]["line_end_date"] is None


def test_the_smoke_data_builder_does_not_clear_line_dates(chain) -> None:
    """The in-repo caller that finding F-03 names. It omits both fields by design."""
    from tooling.smoke_data.builders import set_work_order_line_detail

    _save_period(chain)
    saved = _save_line_detail(chain, line_start_date="2027-02-01", line_end_date="2027-03-01")
    version = saved.json()["line_detail"]["detail_version"]
    with SessionLocal() as db:
        actor = db.execute(text("SELECT public_id FROM app_user WHERE username = 'sales1'")).scalar_one()
    set_work_order_line_detail(
        actor_public_id=str(actor),
        work_order_public_id=chain["work_order_public_id"],
        line_public_id=chain["line_public_ids"][0],
        customer_line_reference="VIA-HARNESS",
        expected_detail_version=version,
    )
    listed = client.get(
        f"/api/work-orders/{chain['work_order_public_id']}/line-details", headers=auth_headers("sales1")
    ).json()
    entry = next(item for item in listed if item["work_order_line_public_id"] == chain["line_public_ids"][0])
    assert entry["customer_line_reference"] == "VIA-HARNESS"
    assert entry["line_start_date"] == "2027-02-01"


@pytest.mark.parametrize(
    "basis, end_date",
    [("FIXED_DATE", None), ("UNTIL_WORK_COMPLETE", "2027-03-31"), (None, "2027-03-31")],
)
def test_the_database_refuses_a_contradictory_contract_period(chain, basis, end_date) -> None:
    """The period's own backstop, tested for the same three shapes as the extension's.

    The third case is the one that matters. Both constraints were first written as a chain of ORs,
    which a CHECK ADMITS when the expression is NULL - and `NULL = 'FIXED_DATE'` is NULL, so an end
    date recorded with no basis beside it passed the very constraint written to refuse it. The
    contract and the review packet both claimed it as a guarantee; only running the case showed
    otherwise. Both are CASE expressions now."""
    from sqlalchemy.exc import IntegrityError

    with SessionLocal() as db:
        work_order_id = db.execute(
            text("SELECT id FROM crm_work_order WHERE work_order_public_id = :id"),
            {"id": chain["work_order_public_id"]},
        ).scalar_one()
        with pytest.raises(IntegrityError) as excinfo:
            db.execute(
                text(
                    """
                    INSERT INTO crm_work_order_contract_period (
                        work_order_contract_period_public_id, work_order_id,
                        contract_start_date, contract_end_basis_code, contract_end_date
                    ) VALUES (:pid, :wo, DATE '2027-01-01', :basis, :end_date)
                    """
                ),
                {"pid": str(uuid4()), "wo": work_order_id, "basis": basis, "end_date": end_date},
            )
        assert "ck_wo_contract_end_basis_is_answered" in str(excinfo.value)
        db.rollback()


@pytest.mark.parametrize(
    "basis, previous_date, start",
    [("FIXED_DATE", None, None), ("UNTIL_WORK_COMPLETE", "2027-03-31", "2027-04-01"), (None, "2027-03-31", "2027-04-01")],
)
def test_the_database_refuses_contradictory_extension_history(chain, basis, previous_date, start) -> None:
    """Independent review round 1, finding F-05. The service never writes these shapes; the CHECK
    makes that a database guarantee rather than a convention, as it already is for the period.

    Each row carries a start date that satisfies the extension-start constraint, so this one is the
    only rule it breaks - a row breaking two rules proves nothing about either."""
    from sqlalchemy.exc import IntegrityError

    with SessionLocal() as db:
        work_order_id = db.execute(
            text("SELECT id FROM crm_work_order WHERE work_order_public_id = :id"),
            {"id": chain["work_order_public_id"]},
        ).scalar_one()
        with pytest.raises(IntegrityError) as excinfo:
            db.execute(
                text(
                    """
                    INSERT INTO crm_work_order_contract_extension (
                        work_order_contract_extension_public_id, work_order_id, extension_sequence_no,
                        previous_end_basis_code, previous_end_date, new_end_date, received_date,
                        extension_start_date
                    ) VALUES (:pid, :wo, 99, :basis, :prev, DATE '2028-01-01', DATE '2027-01-01', :start)
                    """
                ),
                {"pid": str(uuid4()), "wo": work_order_id, "basis": basis, "prev": previous_date, "start": start},
            )
        assert "ck_wo_contract_extension_previous_is_answered" in str(excinfo.value)
        db.rollback()


# --- Copying one line's terms onto other lines (owner decision 20) -----------------------------


def test_copying_gives_every_other_chosen_line_the_sources_terms(chain) -> None:
    _add_terms(chain)
    response = _copy(chain)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source_line_number"] == 1
    assert {result["outcome"] for result in body["results"]} == {"COPIED"}
    assert all(set(result) == COPY_RESULT_KEYS for result in body["results"])
    assert [result["line_number"] for result in body["results"]] == [2, 3]
    for entry in body["billing_terms"]:
        assert entry["terms_complete"] is True
        assert entry["periods"][0]["billing_uom_code"] == "SHIFT"


def test_every_period_is_copied_not_only_the_current_one(chain) -> None:
    """Owner decision 20c: a rate that changes on a date carries across with the rest."""
    _save_period(chain)
    _add_terms(chain)
    _add_terms(chain, effective_from="2027-02-01", expected_period_count=1)
    response = _copy(chain, target_indexes=(1,))
    assert response.status_code == 200, response.text
    assert response.json()["results"][0]["periods_copied"] == 2
    target = next(
        entry for entry in response.json()["billing_terms"] if entry["line_number"] == 2
    )
    assert [period["period_number"] for period in target["periods"]] == [1, 2]
    assert [period["effective_from"] for period in target["periods"]] == [None, "2027-02-01"]


def test_mobilisation_and_demobilisation_are_copied_with_the_rest(chain) -> None:
    """Owner decision 20d. They live on period 1 only, so copying by period number carries them."""
    _add_terms(chain)
    response = _copy(chain, target_indexes=(1,))
    assert response.status_code == 200, response.text
    target = next(entry for entry in response.json()["billing_terms"] if entry["line_number"] == 2)
    assert target["periods"][0]["mobilisation_charge_code"] == "NONE"
    assert target["periods"][0]["demobilisation_charge_code"] == "NONE"


def test_a_receiving_line_stays_editable_afterwards(chain) -> None:
    """Owner decision 20d: each receiving line can then be edited where its own charge differs."""
    _add_terms(chain)
    _copy(chain, target_indexes=(1,))
    target = next(entry for entry in _billing_terms(chain) if entry["line_number"] == 2)
    period = target["periods"][0]
    assert period["term_revision"] == 1
    response = client.put(
        f"{_terms_url(chain, 1)}/{period['term_public_id']}",
        headers=auth_headers("sales1"),
        json={
            "expected_term_revision": 1,
            "effective_from": None,
            **{**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "normal_rate_amount": "9999.00"},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["line_billing_terms"]["periods"][0]["normal_rate_amount"] == "9999.00"


def test_each_receiving_line_records_its_own_event(chain) -> None:
    """Owner decision 20: the trail reads as one change per line, not a single bulk action."""
    _add_terms(chain)
    response = _copy(chain)
    assert len(response.json()["events"]) == 2
    payloads = _events(chain["work_order_public_id"], "WorkOrderLineBillingTermsCopied")
    assert len(payloads) == 2
    assert {payload["source_work_order_line_public_id"] for payload in payloads} == {
        chain["line_public_ids"][0]
    }
    assert {payload["work_order_line_public_id"] for payload in payloads} == set(chain["line_public_ids"][1:])
    assert all(payload["periods_copied"] == 1 for payload in payloads)
    assert "normal_rate_amount" not in str(payloads)


def test_a_line_that_already_has_terms_is_not_replaced_without_confirmation(chain) -> None:
    """Owner decision 20b: the only case where something recorded is replaced is confirmed first."""
    _add_terms(chain)
    _add_terms(chain, line_index=1)
    response = _copy(chain, target_indexes=(1, 2))
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "These lines already have billing terms: line 2. Confirm that you want to replace them before copying."
    )
    # Nothing was written: line 3 is untouched too.
    assert next(entry for entry in _billing_terms(chain) if entry["line_number"] == 3)["periods"] == []


def test_a_confirmed_replacement_replaces_and_says_so(chain) -> None:
    _add_terms(chain, terms={**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "normal_rate_amount": "5555.00"})
    _add_terms(chain, line_index=1)
    response = _copy(chain, target_indexes=(1,), replace_existing_terms=True)
    assert response.status_code == 200, response.text
    result = response.json()["results"][0]
    assert result["outcome"] == "REPLACED"
    assert result["replaced_period_count"] == 1
    target = next(entry for entry in response.json()["billing_terms"] if entry["line_number"] == 2)
    assert len(target["periods"]) == 1
    assert target["periods"][0]["normal_rate_amount"] == "5555.00"


def test_a_line_left_out_keeps_its_own_terms(chain) -> None:
    """Owner decision 20b: unticking never removes terms from a line."""
    _add_terms(chain, terms={**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "normal_rate_amount": "5555.00"})
    _add_terms(chain, line_index=2, terms={**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "normal_rate_amount": "7777.00"})
    response = _copy(chain, target_indexes=(1,))
    assert response.status_code == 200, response.text
    untouched = next(entry for entry in response.json()["billing_terms"] if entry["line_number"] == 3)
    assert untouched["periods"][0]["normal_rate_amount"] == "7777.00"


def test_the_source_line_cannot_also_be_a_target(chain) -> None:
    _add_terms(chain)
    response = _copy(chain, target_indexes=(0, 1))
    assert response.status_code == 422
    assert "cannot also be one of the lines they are copied to" in response.json()["detail"]


def test_the_same_line_chosen_twice_is_refused(chain) -> None:
    _add_terms(chain)
    response = _copy(chain, target_ids=[chain["line_public_ids"][1], chain["line_public_ids"][1]])
    assert response.status_code == 422
    assert "more than once" in response.json()["detail"]


def test_a_line_from_another_work_order_is_not_found(chain) -> None:
    _add_terms(chain)
    response = _copy(chain, target_ids=[str(uuid4())])
    assert response.status_code == 404


def test_a_source_line_with_no_terms_has_nothing_to_copy(chain) -> None:
    response = _copy(chain, source_periods=[{"term_public_id": str(uuid4()), "term_revision": 1}])
    assert response.status_code == 422
    assert "no billing terms to copy" in response.json()["detail"]


def test_terms_changed_underneath_the_screen_are_not_copied(chain) -> None:
    _add_terms(chain)
    seen = _source_periods(chain)
    _add_terms(chain, effective_from="2027-02-01", expected_period_count=1)
    response = _copy(chain, target_indexes=(1,), source_periods=seen)
    assert response.status_code == 409
    assert "Reload" in response.json()["detail"]


def test_a_change_to_an_earlier_source_period_is_detected(chain) -> None:
    """Independent review round 1, finding F-01: a count plus the latest revision leaves a change to
    an EARLIER period invisible, so a period the user never reviewed could have been copied."""
    _add_terms(chain)
    _add_terms(chain, effective_from="2027-02-01", expected_period_count=1)
    seen = _source_periods(chain)
    assert len(seen) == 2
    first = seen[0]
    edit = client.put(
        f"{_terms_url(chain)}/{first['term_public_id']}",
        headers=auth_headers("sales1"),
        json={
            "expected_term_revision": first["term_revision"],
            "effective_from": None,
            **{**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "normal_rate_amount": "4242.00"},
        },
    )
    assert edit.status_code == 200, edit.text
    after = _source_periods(chain)
    # The two things the old check looked at are both unchanged by that edit.
    assert len(after) == len(seen)
    assert after[-1]["term_revision"] == seen[-1]["term_revision"]

    response = _copy(chain, target_indexes=(1,), source_periods=seen)
    assert response.status_code == 409
    assert "Reload" in response.json()["detail"]


def test_a_line_that_gained_terms_after_the_screen_was_read_is_refused_by_name(chain) -> None:
    """Independent review round 1, finding F-02: one request-wide replace flag could authorize
    replacing a line whose name never appeared in the user's confirmation."""
    _add_terms(chain)
    _add_terms(chain, line_index=1)
    # The screen saw line 3 with no terms, so it was ticked without any confirmation being asked.
    stale_target = {
        "work_order_line_public_id": chain["line_public_ids"][2],
        "observed_periods": [],
        "replace_confirmed": False,
    }
    _add_terms(chain, line_index=2)
    response = _copy(
        chain,
        targets=[
            {
                "work_order_line_public_id": chain["line_public_ids"][1],
                "observed_periods": _observed(chain, chain["line_public_ids"][1]),
                "replace_confirmed": True,
            },
            stale_target,
        ],
    )
    assert response.status_code == 409
    assert "Line 3" in response.json()["detail"]
    # Nothing was written at all: line 3 keeps exactly the terms it gained.
    assert len(next(e for e in _billing_terms(chain) if e["line_number"] == 3)["periods"]) == 1


def test_a_populated_line_still_needs_its_own_confirmation(chain) -> None:
    _add_terms(chain)
    _add_terms(chain, line_index=1)
    response = _copy(
        chain,
        targets=[
            {
                "work_order_line_public_id": chain["line_public_ids"][1],
                "observed_periods": _observed(chain, chain["line_public_ids"][1]),
                "replace_confirmed": False,
            }
        ],
    )
    assert response.status_code == 422
    assert "line 2" in response.json()["detail"]


def test_a_change_to_an_earlier_period_of_a_target_is_detected(chain) -> None:
    """Independent review round 2, finding F-07 - the same hole as F-01, on the other side.

    A target's period count and its latest period's revision are both unchanged by an edit to an
    EARLIER period, so a replacement would have silently deleted that edit."""
    _add_terms(chain)
    # Line 2 gets two periods, and the screen reads them.
    _add_terms(chain, line_index=1)
    second = client.post(
        _terms_url(chain, 1),
        headers=auth_headers("sales1"),
        json={
            "expected_period_count": 1,
            "expected_latest_term_revision": 1,
            "effective_from": "2027-02-01",
            **SHIFT_TERMS,
        },
    )
    assert second.status_code == 201, second.text
    seen = _observed(chain, chain["line_public_ids"][1])
    assert len(seen) == 2

    # Only line 2's FIRST period changes.
    edit = client.put(
        f"{_terms_url(chain, 1)}/{seen[0]['term_public_id']}",
        headers=auth_headers("sales1"),
        json={
            "expected_term_revision": seen[0]["term_revision"],
            "effective_from": None,
            **{**SHIFT_TERMS, **PART_2_FIRST_PERIOD_ONLY, "normal_rate_amount": "3131.00"},
        },
    )
    assert edit.status_code == 200, edit.text
    after = _observed(chain, chain["line_public_ids"][1])
    # What the old check compared is identical before and after that edit.
    assert len(after) == len(seen)
    assert after[-1]["term_revision"] == seen[-1]["term_revision"]

    response = _copy(
        chain,
        targets=[
            {
                "work_order_line_public_id": chain["line_public_ids"][1],
                "observed_periods": seen,
                "replace_confirmed": True,
            }
        ],
    )
    assert response.status_code == 409
    assert "Line 2" in response.json()["detail"]
    # The concurrent edit survives untouched.
    live = next(e for e in _billing_terms(chain) if e["line_number"] == 2)
    assert live["periods"][0]["normal_rate_amount"] == "3131.00"


def test_one_line_that_cannot_be_written_is_named_without_stopping_the_others(chain, monkeypatch) -> None:
    """Owner decision 20b's guard path. With the Work Order locked for the whole operation nothing
    can change a line underneath this call, so the failure is injected rather than pretended: the
    point is that one line failing leaves the others written and reports which one failed."""
    _add_terms(chain)
    failing_line_id: dict[str, int] = {}
    real_insert = work_orders_repository.insert_billing_term

    def _fail_for_the_second_line(db, **kwargs):
        if not failing_line_id:
            failing_line_id["id"] = kwargs["work_order_line_id"]
        if kwargs["work_order_line_id"] == failing_line_id["id"]:
            raise RuntimeError("deliberate failure for one line")
        return real_insert(db, **kwargs)

    monkeypatch.setattr(
        # Patched where the copy looks it up: the module it is defined in, not the re-export (TE-6).
        "app.modules.work_orders.services.billing_terms.insert_billing_term", _fail_for_the_second_line
    )
    response = _copy(chain)
    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert results[0]["outcome"] == "FAILED"
    assert "Line 2 could not be written" in results[0]["message"]
    assert results[1]["outcome"] == "COPIED"
    # The failed line rolled back alone: no terms and no event for it, and line 3 kept its copy.
    terms = {entry["line_number"]: entry for entry in response.json()["billing_terms"]}
    assert terms[2]["periods"] == []
    assert len(terms[3]["periods"]) == 1
    assert len(_events(chain["work_order_public_id"], "WorkOrderLineBillingTermsCopied")) == 1


# --- Authorization and locking ------------------------------------------------------------------


@pytest.mark.parametrize("username", READ_ROLES)
def test_every_role_that_can_read_a_work_order_can_read_its_contract_period(chain, username) -> None:
    assert _get_period(chain, username=username).status_code == 200


@pytest.mark.parametrize("username", WRITE_ROLES)
def test_the_four_writing_roles_can_record_the_dates(chain, username) -> None:
    """Owner decision 18: the same four roles as the rest of the line's details."""
    response = _save_period(chain, contract_notes=f"recorded by {username}")
    assert response.status_code == 200, response.text
    assert _extend(chain, new_end_date="2027-06-30", username=username).status_code == 201


@pytest.mark.parametrize("username", WRITE_ROLES)
def test_the_four_writing_roles_can_remove_an_extension(chain, username) -> None:
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30")
    assert _remove_extension(chain, _extension_ids(chain)[0], username=username).status_code == 200


@pytest.mark.parametrize("username", NON_WRITE_ROLES)
def test_finance_and_read_only_cannot_record_the_dates_or_an_extension(chain, username) -> None:
    assert _save_period(chain, username=username).status_code == 403
    assert _extend(chain, new_end_date="2027-06-30", username=username).status_code == 403


@pytest.mark.parametrize("username", NON_WRITE_ROLES)
def test_finance_and_read_only_cannot_remove_an_extension(chain, username) -> None:
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30")
    assert _remove_extension(chain, _extension_ids(chain)[0], username=username).status_code == 403
    assert len(_extension_ids(chain)) == 1


@pytest.mark.parametrize("username", NON_WRITE_ROLES)
def test_finance_and_read_only_cannot_copy_terms_between_lines(chain, username) -> None:
    assert _copy(chain, username=username).status_code == 403


def test_a_closed_work_order_refuses_every_part_three_write(chain) -> None:
    _add_terms(chain)
    with SessionLocal() as db:
        db.execute(
            text("UPDATE crm_work_order SET work_order_status_code = 'CLOSED' WHERE work_order_public_id = :id"),
            {"id": chain["work_order_public_id"]},
        )
        db.commit()
    assert _save_period(chain).status_code == 422
    assert _extend(chain, new_end_date="2027-06-30").status_code == 422
    assert _copy(chain).status_code == 422


def test_a_closed_work_order_refuses_removing_an_extension(chain) -> None:
    _save_period(chain)
    _extend(chain, new_end_date="2027-06-30")
    extension = _extension_ids(chain)[0]
    with SessionLocal() as db:
        db.execute(
            text("UPDATE crm_work_order SET work_order_status_code = 'CLOSED' WHERE work_order_public_id = :id"),
            {"id": chain["work_order_public_id"]},
        )
        db.commit()
    response = _remove_extension(chain, extension)
    assert response.status_code == 422
    assert "closed" in response.json()["detail"]


def test_an_unknown_work_order_is_not_found(chain) -> None:
    missing = str(uuid4())
    assert client.get(f"/api/work-orders/{missing}/contract-period", headers=auth_headers("sales1")).status_code == 404
    assert (
        client.put(
            f"/api/work-orders/{missing}/contract-period",
            headers=auth_headers("sales1"),
            json={"expected_period_version": None, "contract_start_date": START},
        ).status_code
        == 404
    )


def test_an_unknown_field_is_refused_rather_than_ignored(chain) -> None:
    """The Slice 7D convention: a caller sending something that is not saved here learns so."""
    response = client.put(
        _period_url(chain),
        headers=auth_headers("sales1"),
        json={"expected_period_version": None, "contract_start_date": START, "renewal_terms": "yearly"},
    )
    assert response.status_code == 422


# --- The frozen handoff is untouched ------------------------------------------------------------


def test_the_handoff_output_carries_no_part_three_field(chain) -> None:
    """Nothing Part 3 adds may appear in what the frozen handoff returns."""
    response = client.get(
        f"/api/work-orders/{chain['work_order_public_id']}", headers=auth_headers("sales1")
    )
    assert response.status_code == 200
    body = response.json()
    for field in ("contract_start_date", "contract_end_date", "contract_end_basis_code", "contract_state_code"):
        assert field not in body

    lines = client.get(
        f"/api/work-orders/{chain['work_order_public_id']}/lines", headers=auth_headers("sales1")
    ).json()
    for line in lines:
        assert "line_start_date" not in line and "line_end_date" not in line
