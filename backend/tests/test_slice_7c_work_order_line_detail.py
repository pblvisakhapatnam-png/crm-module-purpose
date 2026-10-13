"""Slice 7C - Work Order line operational detail tests.

Each test maps to an item in the "Test plan" section of
docs/agent/slices/slice-7c-work-order-line-operational-detail.md. The fixtures build a real chain
through the existing API helpers (Lead -> Account -> Opportunity -> accepted Commercial Offer ->
Work Order shell), then add the Account records a line picks from.

Business events need no explicit cleanup: conftest removes every event created by the session.

Slice 7D moved the billing basis and contracted hours out of this detail into the line's billing
terms. The tests for those two fields moved with them, to test_slice_7d_work_order_line_billing_terms.py;
the version, conflict and no-op tests here now change the customer line reference instead.
"""

from __future__ import annotations

import json
import threading
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.work_orders import service as work_orders_service
from app.modules.work_orders.schemas import WorkOrderLineDetailUpdate

# The save looks its repository functions up in the module it is defined in, so a test that swaps one
# must patch it there; patching the re-exporting service module changes nothing the save sees (TE-6).
from app.modules.work_orders.services import line_detail as line_detail_service
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


# The handoff's response shape on main at 79983e2. Pinned here so a field added to (or dropped from)
# what the frozen Accepted Offer -> Work Order handoff returns fails this slice's suite. The one change
# since: `commercial_offer_version_number`, added by the frozen contract's dated amendment of 12 October
# 2026 (CS-04 part 2, item d), which the owner approved.
HANDOFF_WORK_ORDER_KEYS = {
    "public_id",
    "work_order_code",
    "work_order_title",
    "work_order_status_code",
    "commercial_offer_public_id",
    "commercial_offer_code",
    "commercial_offer_version_number",
    "opportunity_public_id",
    "account_public_id",
    "customer_wo_reference",
    "received_date",
    "source_offer_status_code",
    "remarks",
    "created_by",
    "created_at",
    "updated_at",
}
HANDOFF_LINE_KEYS = {
    "public_id",
    "work_order_public_id",
    "source_offer_line_public_id",
    "source_offer_line_number",
    "line_number",
    "line_status_code",
    "scope_description",
    "equipment_service_category",
    "quantity",
    "uom",
    "rate_amount",
    "currency_code",
    "line_amount",
    "remarks",
    "created_at",
    "updated_at",
}
# The billing basis and contracted hours are reported by the billing terms since Slice 7D.
ALL_MISSING = ["SITE_ADDRESS", "BILLING_GSTIN", "BILLING_ADDRESS"]
LINE_DETAIL_KEYS = {
    "work_order_line_public_id",
    "line_number",
    "source_offer_line_public_id",
    "detail_public_id",
    "detail_version",
    "site_address_public_id",
    "site_address",
    "billing_gstin_public_id",
    "billing_gstin",
    "billing_address_public_id",
    "billing_address",
    "customer_line_reference",
    "operational_notes",
    # Slice 7D Part 3: the line's own dates inside the contract period. Blank means the line follows
    # the Work Order (owner decision 13), so neither is ever reported missing.
    "line_start_date",
    "line_end_date",
    # 8A core: is the site a central-government site; null until answered, never a missing item.
    "site_central_government",
    "is_complete",
    "missing_items",
    "updated_by",
    "updated_by_display_name",
    "updated_at",
}
RESOLVED_ADDRESS_KEYS = {"public_id", "address_type_code", "address_line1", "city", "state", "postal_code"}
RESOLVED_GSTIN_KEYS = {"public_id", "gstin", "state_code", "verification_state_code"}


def _unique_gstin(state_code: str = "27") -> str:
    token = uuid4().int
    letters = "".join(chr(ord("A") + (token >> (5 * i)) % 26) for i in range(5))
    return f"{state_code}{letters}{token % 10000:04d}F1Z5"


def _add_address(account_public_id: str, address_type_code: str, line1: str) -> dict[str, object]:
    response = client.post(
        f"/api/accounts/{account_public_id}/addresses",
        headers=auth_headers("sales1"),
        json={"address_type_code": address_type_code, "address_line1": line1, "city": "Pune", "state": "Maharashtra"},
    )
    assert response.status_code == 201, response.text
    return response.json()["address"]


def _add_gstin(account_public_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/accounts/{account_public_id}/gstins",
        headers=auth_headers("sales1"),
        json={"gstin": _unique_gstin(), "state_name": "Maharashtra"},
    )
    assert response.status_code == 201, response.text
    return response.json()["gstin"]


def _delete_account_records(account_public_ids: list[str]) -> None:
    with SessionLocal() as db:
        for table in ("business_party_address", "business_party_gstin", "business_party_tax_profile"):
            db.execute(
                text(
                    f"DELETE FROM {table} t USING business_party bp "
                    "WHERE bp.id = t.business_party_id AND bp.business_party_public_id = ANY(:ids)"
                ),
                {"ids": account_public_ids},
            )
        db.commit()


def _delete_line_details(work_order_public_ids: list[str]) -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                """
                DELETE FROM crm_work_order_line_detail d
                USING crm_work_order_line wol, crm_work_order wo
                WHERE wol.id = d.work_order_line_id
                  AND wo.id = wol.work_order_id
                  AND wo.work_order_public_id = ANY(:ids)
                """
            ),
            {"ids": work_order_public_ids},
        )
        db.commit()


@pytest.fixture
def chain():
    """An accepted Work Order with two lines, and the Account records a line can pick from."""
    record: dict[str, object] = {
        "work_order_public_ids": [],
        "extra_account_public_ids": [],
        "supplementary_offer_public_ids": [],
    }
    linked = create_account_linked_test_opportunity()
    account_public_id = str(linked["account"]["public_id"])
    record.update(
        lead_public_id=str(linked["lead"]["public_id"]),
        account_public_id=account_public_id,
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
        record["handoff_body"] = handoff.json()
        work_order_public_id = str(handoff.json()["work_order"]["public_id"])
        record["work_order_public_id"] = work_order_public_id
        record["work_order_public_ids"].append(work_order_public_id)
        record["line_public_ids"] = [str(line["public_id"]) for line in handoff.json()["lines"]]

        record["site"] = _add_address(account_public_id, "SITE", "Plot 7, Chakan Yard")
        record["registered_office"] = _add_address(account_public_id, "REGISTERED_OFFICE", "1 Harbour House")
        record["billing_draft"] = _add_address(account_public_id, "BILLING_DRAFT", "Accounts Desk, Floor 3")
        record["communication"] = _add_address(account_public_id, "COMMUNICATION", "PO Box 12")
        record["gstin"] = _add_gstin(account_public_id)
        yield record
    finally:
        _delete_line_details(record["work_order_public_ids"])
        cleanup_test_work_orders(record["work_order_public_ids"])
        _delete_account_records([account_public_id, *record["extra_account_public_ids"]])
        cleanup_test_records(
            opportunity_public_ids=[record["opportunity_public_id"]],
            offer_public_ids=[*record["supplementary_offer_public_ids"], record["offer_public_id"]]
            if "offer_public_id" in record
            else [],
            account_public_ids=[account_public_id, *record["extra_account_public_ids"]],
            lead_public_ids=[record["lead_public_id"]],
        )


def _detail_url(chain: dict[str, object], line_index: int = 0, work_order_public_id: str | None = None) -> str:
    work_order = work_order_public_id or chain["work_order_public_id"]
    return f"/api/work-orders/{work_order}/lines/{chain['line_public_ids'][line_index]}/detail"


def _complete_payload(chain: dict[str, object], **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "expected_detail_version": None,
        "site_address_public_id": chain["site"]["public_id"],
        "billing_gstin_public_id": chain["gstin"]["public_id"],
        "billing_address_public_id": chain["registered_office"]["public_id"],
        "customer_line_reference": "PO-4471 item 10",
    }
    payload.update(overrides)
    return payload


def _save(chain: dict[str, object], payload: dict[str, object], username: str = "sales1", line_index: int = 0):
    return client.put(_detail_url(chain, line_index), headers=auth_headers(username), json=payload)


def _line_details(chain: dict[str, object], username: str = "sales1") -> list[dict[str, object]]:
    response = client.get(f"/api/work-orders/{chain['work_order_public_id']}/line-details", headers=auth_headers(username))
    assert response.status_code == 200, response.text
    return response.json()


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


# --- Save and read ---------------------------------------------------------------------------


def test_first_save_creates_version_one_and_records_the_detail_event(chain) -> None:
    response = _save(chain, _complete_payload(chain))
    assert response.status_code == 200, response.text
    body = response.json()
    detail = body["line_detail"]
    assert detail["detail_version"] == 1
    assert detail["is_complete"] is True
    assert detail["missing_items"] == []
    assert detail["site_address"]["city"] == "Pune"
    assert detail["billing_gstin"]["gstin"] == chain["gstin"]["gstin"]
    assert detail["billing_address"]["address_type_code"] == "REGISTERED_OFFICE"
    assert detail["updated_by_display_name"]
    assert body["event"]["event_name"] == "WorkOrderLineDetailRecorded"
    assert _event_count(chain["work_order_public_id"], "WorkOrderLineDetailRecorded") == 1


def test_a_changing_save_moves_to_version_two_and_names_the_changed_fields(chain) -> None:
    assert _save(chain, _complete_payload(chain)).status_code == 200
    response = _save(
        chain,
        _complete_payload(
            chain, expected_detail_version=1, billing_address_public_id=chain["billing_draft"]["public_id"]
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["line_detail"]["detail_version"] == 2
    assert body["event"]["event_name"] == "WorkOrderLineDetailUpdated"
    assert body["event"]["event_payload"]["changed_fields"] == ["billing_address_public_id"]
    assert body["event"]["event_payload"]["detail_version"] == 2


def test_an_identical_save_records_nothing_and_keeps_the_version(chain) -> None:
    assert _save(chain, _complete_payload(chain)).status_code == 200
    # Surrounding spaces are trimmed before comparing, so this is the same stored value.
    response = _save(chain, _complete_payload(chain, expected_detail_version=1, customer_line_reference="  PO-4471 item 10  "))
    assert response.status_code == 200, response.text
    assert response.json()["event"] is None
    assert response.json()["line_detail"]["detail_version"] == 1
    assert _event_count(chain["work_order_public_id"], "WorkOrderLineDetailUpdated") == 0


def test_a_stale_version_is_refused_with_conflict_and_writes_nothing(chain) -> None:
    assert _save(chain, _complete_payload(chain)).status_code == 200
    assert _save(chain, _complete_payload(chain, expected_detail_version=1, customer_line_reference="PO-2")).status_code == 200

    stale = _save(chain, _complete_payload(chain, expected_detail_version=1, customer_line_reference="PO-3"))
    assert stale.status_code == 409
    assert "Reload" in stale.json()["detail"]
    detail = _line_details(chain)[0]
    assert detail["customer_line_reference"] == "PO-2"
    assert detail["detail_version"] == 2


def test_expected_version_null_is_a_conflict_once_a_detail_exists(chain) -> None:
    assert _save(chain, _complete_payload(chain)).status_code == 200
    response = _save(chain, _complete_payload(chain, customer_line_reference="PO-2"))
    assert response.status_code == 409


def test_expected_version_given_before_any_detail_exists_is_a_conflict(chain) -> None:
    response = _save(chain, _complete_payload(chain, expected_detail_version=1))
    assert response.status_code == 409


def test_line_details_lists_every_line_in_order_with_null_detail_where_none_recorded(chain) -> None:
    assert _save(chain, _complete_payload(chain), line_index=1).status_code == 200
    details = _line_details(chain)
    assert [item["work_order_line_public_id"] for item in details] == chain["line_public_ids"]
    assert [item["line_number"] for item in details] == sorted(item["line_number"] for item in details)
    assert details[0]["detail_public_id"] is None
    assert details[0]["detail_version"] is None
    assert details[0]["missing_items"] == ALL_MISSING
    assert details[1]["detail_version"] == 1
    assert details[1]["source_offer_line_public_id"]


def test_the_response_entry_and_resolved_objects_have_exactly_the_contract_shape(chain) -> None:
    saved = _save(chain, _complete_payload(chain)).json()
    assert set(saved) == {"line_detail", "event"}
    listed = _line_details(chain)
    for entry in (saved["line_detail"], *listed):
        assert set(entry) == LINE_DETAIL_KEYS
    detail = saved["line_detail"]
    assert set(detail["site_address"]) == RESOLVED_ADDRESS_KEYS
    assert set(detail["billing_address"]) == RESOLVED_ADDRESS_KEYS
    assert set(detail["billing_gstin"]) == RESOLVED_GSTIN_KEYS


def test_the_returned_detail_is_the_version_the_event_records(chain) -> None:
    first = _save(chain, _complete_payload(chain)).json()
    assert first["line_detail"]["detail_version"] == first["event"]["event_payload"]["detail_version"] == 1
    second = _save(chain, _complete_payload(chain, expected_detail_version=1, customer_line_reference="PO-2")).json()
    assert second["line_detail"]["detail_version"] == second["event"]["event_payload"]["detail_version"] == 2
    assert second["line_detail"]["customer_line_reference"] == "PO-2"


def test_a_concurrent_save_cannot_change_the_version_another_save_reports(chain, monkeypatch) -> None:
    """Two sessions, interleaved deterministically (review round 2 advisory).

    Save A is paused at the moment it reads the saved detail back for its response. Save B, for the
    same line, is started while A is paused. If A's read happened after A's commit - the round-1
    defect - B would not be blocked, would write version 2, and A would report version 2 beside an
    event for version 1. Because A's read happens before commit, under the Work Order lock, B waits
    until A commits and A reports exactly the version it wrote."""
    real_read = line_detail_service.list_work_order_line_detail_rows
    a_is_paused = threading.Event()
    b_finished = threading.Event()
    thread_a_name = "slice-7c-save-a"
    results: dict[str, object] = {}

    def pausing_read(*args, **kwargs):
        if threading.current_thread().name == thread_a_name and not a_is_paused.is_set():
            a_is_paused.set()
            # B is blocked on the Work Order lock while A holds it; give B every chance to finish
            # anyway, so a lock that is not held shows up as B finishing inside this window.
            b_finished.wait(timeout=3)
        return real_read(*args, **kwargs)

    monkeypatch.setattr(line_detail_service, "list_work_order_line_detail_rows", pausing_read)

    def save(name: str, **overrides: object) -> None:
        try:
            with SessionLocal() as db:
                results[name] = work_orders_service.save_work_order_line_detail(
                    db,
                    work_order_public_id=chain["work_order_public_id"],
                    line_public_id=chain["line_public_ids"][0],
                    payload=WorkOrderLineDetailUpdate(**_complete_payload(chain, **overrides)),
                    current_user_public_id=None,
                )
        except Exception as exc:  # recorded, asserted below
            results[name] = exc
        finally:
            if name == "b":
                b_finished.set()

    thread_a = threading.Thread(target=save, args=("a",), name=thread_a_name)
    thread_a.start()
    assert a_is_paused.wait(timeout=30), "save A never reached its response read"
    thread_b = threading.Thread(target=save, args=("b",), kwargs={"expected_detail_version": 1, "customer_line_reference": "PO-B"})
    thread_b.start()
    thread_a.join(timeout=60)
    thread_b.join(timeout=60)
    monkeypatch.undo()

    a, b = results["a"], results["b"]
    assert not isinstance(a, Exception), a
    assert not isinstance(b, Exception), b
    assert a.line_detail.detail_version == a.event["event_payload"]["detail_version"] == 1
    assert a.line_detail.customer_line_reference == "PO-4471 item 10"
    assert b.line_detail.detail_version == b.event["event_payload"]["detail_version"] == 2
    assert b.line_detail.customer_line_reference == "PO-B"


def test_a_failure_building_the_response_leaves_nothing_written(chain, monkeypatch) -> None:
    """The response is read inside the transaction, before commit. If building it fails, the write
    and its event must roll back with it - never a committed change reported to the caller as an
    error, which a retry would then hit as a conflict."""

    def failing_read(*args, **kwargs):
        raise RuntimeError("simulated failure reading the saved detail")

    monkeypatch.setattr(line_detail_service, "list_work_order_line_detail_rows", failing_read)
    payload = WorkOrderLineDetailUpdate(**_complete_payload(chain))
    with SessionLocal() as db:
        with pytest.raises(RuntimeError):
            work_orders_service.save_work_order_line_detail(
                db,
                work_order_public_id=chain["work_order_public_id"],
                line_public_id=chain["line_public_ids"][0],
                payload=payload,
                current_user_public_id=None,
            )
    monkeypatch.undo()
    assert _line_details(chain)[0]["detail_public_id"] is None
    assert _event_count(chain["work_order_public_id"], "WorkOrderLineDetailRecorded") == 0


# --- Validation ------------------------------------------------------------------------------


def test_references_to_another_accounts_records_are_refused(chain) -> None:
    other = client.post("/api/accounts", headers=auth_headers("sales1"), json={"account_name": f"Other Account {uuid4()}"})
    assert other.status_code == 201, other.text
    other_public_id = str(other.json()["account"]["public_id"])
    chain["extra_account_public_ids"].append(other_public_id)
    other_site = _add_address(other_public_id, "SITE", "Other customer site")
    other_office = _add_address(other_public_id, "REGISTERED_OFFICE", "Other customer office")
    other_gstin = _add_gstin(other_public_id)

    for field, value in (
        ("site_address_public_id", other_site["public_id"]),
        ("billing_gstin_public_id", other_gstin["public_id"]),
        ("billing_address_public_id", other_office["public_id"]),
    ):
        response = _save(chain, _complete_payload(chain, **{field: value}))
        assert response.status_code == 422, field
        assert "Other" not in response.json()["detail"]
    assert _line_details(chain)[0]["detail_public_id"] is None


def test_addresses_of_the_wrong_type_are_refused(chain) -> None:
    assert _save(chain, _complete_payload(chain, site_address_public_id=chain["registered_office"]["public_id"])).status_code == 422
    assert _save(chain, _complete_payload(chain, billing_address_public_id=chain["site"]["public_id"])).status_code == 422
    assert _save(chain, _complete_payload(chain, billing_address_public_id=chain["communication"]["public_id"])).status_code == 422


def test_a_gstin_rejected_as_incorrect_cannot_be_picked(chain) -> None:
    with SessionLocal() as db:
        db.execute(
            text("UPDATE business_party_gstin SET gstin_verification_state_code = 'REJECTED_INCORRECT' WHERE gstin_public_id = :id"),
            {"id": chain["gstin"]["public_id"]},
        )
        db.commit()
    response = _save(chain, _complete_payload(chain))
    assert response.status_code == 422
    assert "rejected" in response.json()["detail"]


@pytest.mark.parametrize(
    "moved_field, value", [("billing_uom_code", "SHIFT"), ("contracted_hours_per_billing_unit", "8.00")]
)
def test_the_billing_basis_and_hours_are_refused_here_since_they_moved_to_billing_terms(
    chain, moved_field: str, value: str
) -> None:
    """Slice 7D: refused rather than silently ignored, so a caller still sending them learns they were
    not saved. Their own rules are tested in test_slice_7d_work_order_line_billing_terms.py."""
    response = _save(chain, _complete_payload(chain, **{moved_field: value}))
    assert response.status_code == 422
    assert _line_details(chain)[0]["detail_public_id"] is None


def test_a_line_from_another_work_order_is_not_found(chain) -> None:
    supplementary_public_id, handoff = create_test_supplementary_work_order(chain["offer_public_id"])
    chain["supplementary_offer_public_ids"].append(supplementary_public_id)
    second = handoff["work_order"]
    chain["work_order_public_ids"].append(str(second["public_id"]))
    response = client.put(
        _detail_url(chain, 0, work_order_public_id=str(second["public_id"])),
        headers=auth_headers("sales1"),
        json=_complete_payload(chain),
    )
    assert response.status_code == 404


def test_an_unknown_work_order_is_not_found(chain) -> None:
    unknown = str(uuid4())
    assert client.put(_detail_url(chain, 0, work_order_public_id=unknown), headers=auth_headers("sales1"), json=_complete_payload(chain)).status_code == 404
    assert client.get(f"/api/work-orders/{unknown}/line-details", headers=auth_headers("sales1")).status_code == 404


def test_a_closed_work_order_refuses_changes(chain) -> None:
    with SessionLocal() as db:
        db.execute(
            text("UPDATE crm_work_order SET work_order_status_code = 'CLOSED' WHERE work_order_public_id = :id"),
            {"id": chain["work_order_public_id"]},
        )
        db.commit()
    response = _save(chain, _complete_payload(chain))
    assert response.status_code == 422
    assert "closed" in response.json()["detail"]


# --- Completeness ----------------------------------------------------------------------------


def test_an_empty_detail_lists_the_three_missing_items(chain) -> None:
    response = _save(chain, {"expected_detail_version": None})
    assert response.status_code == 200, response.text
    assert response.json()["line_detail"]["missing_items"] == ALL_MISSING
    assert response.json()["line_detail"]["is_complete"] is False


def test_a_gstin_rejected_after_it_was_picked_reads_as_missing_again(chain) -> None:
    assert _save(chain, _complete_payload(chain)).json()["line_detail"]["is_complete"] is True
    with SessionLocal() as db:
        db.execute(
            text("UPDATE business_party_gstin SET gstin_verification_state_code = 'REJECTED_INCORRECT' WHERE gstin_public_id = :id"),
            {"id": chain["gstin"]["public_id"]},
        )
        db.commit()
    detail = _line_details(chain)[0]
    assert detail["missing_items"] == ["BILLING_GSTIN"]
    assert detail["billing_gstin"] is None
    assert detail["billing_gstin_public_id"] == chain["gstin"]["public_id"]


def test_an_address_no_longer_active_reads_as_missing_again(chain) -> None:
    assert _save(chain, _complete_payload(chain)).status_code == 200
    with SessionLocal() as db:
        db.execute(
            text("UPDATE business_party_address SET is_active = FALSE WHERE address_public_id = :id"),
            {"id": chain["site"]["public_id"]},
        )
        db.commit()
    assert _line_details(chain)[0]["missing_items"] == ["SITE_ADDRESS"]


# --- Permissions -----------------------------------------------------------------------------


@pytest.mark.parametrize("username", ["sales1", "manager1", "ops1", "admin1"])
def test_the_four_writing_roles_may_save(chain, username: str) -> None:
    response = _save(chain, _complete_payload(chain), username=username)
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("username", ["finance1", "readonly1"])
def test_finance_and_management_may_read_but_not_save(chain, username: str) -> None:
    assert _save(chain, _complete_payload(chain), username=username).status_code == 403
    assert len(_line_details(chain, username=username)) == 2


def test_unauthenticated_callers_are_refused(chain) -> None:
    assert client.put(_detail_url(chain), json=_complete_payload(chain)).status_code == 401
    assert client.get(f"/api/work-orders/{chain['work_order_public_id']}/line-details").status_code == 401


# --- The work_orders boundary ----------------------------------------------------------------


def test_the_handoff_response_shape_is_exactly_the_pinned_shape(chain) -> None:
    body = chain["handoff_body"]
    assert set(body) == {"work_order", "lines", "events"}
    assert set(body["work_order"]) == HANDOFF_WORK_ORDER_KEYS
    assert body["lines"]
    for line in body["lines"]:
        assert set(line) == HANDOFF_LINE_KEYS


def test_the_handoff_records_no_line_detail(chain) -> None:
    with SessionLocal() as db:
        count = db.execute(
            text(
                """
                SELECT COUNT(*) FROM crm_work_order_line_detail d
                INNER JOIN crm_work_order_line wol ON wol.id = d.work_order_line_id
                INNER JOIN crm_work_order wo ON wo.id = wol.work_order_id
                WHERE wo.work_order_public_id = :id
                """
            ),
            {"id": chain["work_order_public_id"]},
        ).scalar_one()
    assert int(count) == 0


def test_saving_detail_leaves_the_work_order_and_its_lines_unchanged(chain) -> None:
    headers = auth_headers("readonly1")
    before_work_order = client.get(f"/api/work-orders/{chain['work_order_public_id']}", headers=headers).json()
    before_lines = client.get(f"/api/work-orders/{chain['work_order_public_id']}/lines", headers=headers).json()
    assert _save(chain, _complete_payload(chain)).status_code == 200
    assert client.get(f"/api/work-orders/{chain['work_order_public_id']}", headers=headers).json() == before_work_order
    assert client.get(f"/api/work-orders/{chain['work_order_public_id']}/lines", headers=headers).json() == before_lines


def test_the_event_payload_carries_no_gstin_value_or_address_text(chain) -> None:
    event = _save(chain, _complete_payload(chain)).json()["event"]
    serialized = json.dumps(event)
    assert chain["gstin"]["gstin"] not in serialized
    for address in (chain["site"], chain["registered_office"]):
        assert address["address_line1"] not in serialized
    assert "PO-4471" not in serialized


def test_the_shared_work_order_cleanup_helper_removes_line_details_first(chain) -> None:
    """Slice 7C review round 4 advisory: a test that saves a line detail and then calls the shared
    cleanup_test_work_orders helper alone must not fail on fk_wol_detail_work_order_line."""
    assert _save(chain, _complete_payload(chain)).status_code == 200
    cleanup_test_work_orders([chain["work_order_public_id"]])
    with SessionLocal() as db:
        remaining = db.execute(
            text("SELECT COUNT(*) FROM crm_work_order WHERE work_order_public_id = :id"),
            {"id": chain["work_order_public_id"]},
        ).scalar_one()
    assert int(remaining) == 0


# --- Database constraints --------------------------------------------------------------------


def _insert_detail_directly(line_public_id: str, **columns: object) -> None:
    names = ", ".join(columns)
    binds = ", ".join(f":{name}" for name in columns)
    with SessionLocal() as db:
        try:
            db.execute(
                text(
                    f"""
                    INSERT INTO crm_work_order_line_detail (work_order_line_detail_public_id, work_order_line_id{', ' + names if names else ''})
                    SELECT :public_id, wol.id{', ' + binds if binds else ''}
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
        {"detail_version": 0},
        {"site_address_public_id": str(uuid4())},
    ],
)
def test_the_database_refuses_a_direct_insert_that_breaks_a_rule(chain, columns: dict[str, object]) -> None:
    with pytest.raises(IntegrityError):
        _insert_detail_directly(chain["line_public_ids"][0], **columns)


def test_the_database_refuses_a_second_detail_row_for_one_line(chain) -> None:
    _insert_detail_directly(chain["line_public_ids"][0])
    with pytest.raises(IntegrityError):
        _insert_detail_directly(chain["line_public_ids"][0])
