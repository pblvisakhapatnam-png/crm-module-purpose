"""WRR-001 - Resource Requirements: what a Work Order line needs on site.

Each test maps to an item in section 18 of docs/agent/slices/wrr-001-resource-requirement-foundation.md.
The rules are the owner's answers of 24 September 2026 (Q1-Q17). The fixture builds a real chain
through the API (Lead -> Account -> Opportunity -> accepted Commercial Offer -> Work Order) with a
"Crane" line and a "Hydra" line, and a site address on the Account for a line to pick.

Business events need no explicit cleanup: conftest removes every event created by the session. The
requirement rows go with the Work Order (cleanup_test_work_orders).
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app
from app.modules.equipment_reference.service import get_equipment_structure
from app.modules.resource_requirements import service as requirements_service
from app.modules.resource_requirements.schemas import ResourceRequirementCapabilityInput, ResourceRequirementCreate
from app.shared.request_keys import request_fingerprint
from tests.request_key_test_support import as_made_before_fingerprints, run_at_once, stored_fingerprints, user_public_id
from tests.test_commercial_offers_api import (
    auth_headers,
    cleanup_test_records,
    cleanup_test_work_orders,
    client,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    create_test_supplementary_work_order,
    mark_test_commercial_offer_submitted,
    record_test_customer_response,
)
from tests.test_slice_7c_work_order_line_detail import (
    HANDOFF_LINE_KEYS,
    HANDOFF_WORK_ORDER_KEYS,
    _add_address,
    _delete_account_records,
)
from tests.test_slice_7d_part_3_contract_period import _extend, _save_period
from tests.test_slice_7d_work_order_line_billing_terms import PART_2_FIRST_PERIOD_ONLY, SHIFT_TERMS

URL = "/api/resource-requirements"
READ_ROLES = ("admin1", "sales1", "manager1", "finance1", "ops1", "readonly1")
WRITE_ROLES = ("admin1", "ops1")
NON_WRITE_ROLES = ("sales1", "manager1", "finance1", "readonly1")

REQUIREMENT_KEYS = {
    "requirement_public_id",
    "requirement_reference",
    "work_order_public_id",
    "work_order_code",
    "work_order_line_public_id",
    "work_order_line_number",
    "source_offer_line_public_id",
    "account_public_id",
    "units_required",
    "required_from",
    "required_to",
    "crew_operators_required",
    "crew_helpers_required",
    "crew_notes",
    "priority_code",
    "planning_notes",
    "requirement_status_code",
    "requirement_version",
    "taxonomy_version",
    # 8A core: how many units the allocations cover, worked out on every read.
    "units_covered",
    "units_remaining",
    "covered_unit_numbers",
    "items",
    "warnings",
    "line",
    "cancellation_reason",
    "cancelled_by",
    "cancelled_by_display_name",
    "cancelled_at",
    "created_by",
    "created_by_display_name",
    "created_at",
    "updated_by",
    "updated_by_display_name",
    "updated_at",
}
EVENT_PAYLOAD_KEYS = {
    "requirement_reference",
    "work_order_public_id",
    "work_order_line_public_id",
    "source_offer_line_public_id",
    "site_address_public_id",
    "requirement_version",
    "requirement_status_code",
    "units_required",
    "required_from",
    "required_to",
    "crew_operators_required",
    "crew_helpers_required",
    "priority_code",
    "taxonomy_version",
    "items",
    "changed_fields",
}
CRAWLER_220 = {
    "equipment_class_code": "CRANE",
    "equipment_type_code": "CRAWLER",
    "equipment_specification": "Luffing fly jib, 60 m",
    "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "220"}],
}


def _add_offer_line(offer_public_id: str, *, scope: str, category: str | None, quantity: str, uom: str) -> None:
    response = client.post(
        f"/api/commercial-offers/{offer_public_id}/lines",
        headers=auth_headers("sales1"),
        json={"scope_description": scope, "equipment_service_category": category, "quantity": quantity, "uom": uom},
    )
    assert response.status_code == 201, response.text


def _hand_off(offer_public_id: str) -> dict:
    mark_test_commercial_offer_submitted(offer_public_id)
    record_test_customer_response(offer_public_id, "ACCEPTED_AWARDED", received_at="2026-09-14T10:00:00Z")
    handoff = client.post(
        "/api/work-orders/from-commercial-offer",
        headers=auth_headers("sales1"),
        json={"commercial_offer_public_id": offer_public_id, "customer_wo_reference": f"CUST-{uuid4()}"},
    )
    assert handoff.status_code == 201, handoff.text
    return handoff.json()


@pytest.fixture
def wo():
    """An accepted Work Order with a "Crane" line and a "Hydra" line, and a site on its Account."""
    record: dict[str, object] = {"work_order_public_ids": [], "offer_public_ids": []}
    linked = create_account_linked_test_opportunity()
    account_public_id = str(linked["account"]["public_id"])
    record.update(
        lead_public_id=str(linked["lead"]["public_id"]),
        account_public_id=account_public_id,
        opportunity_public_id=str(linked["opportunity"]["public_id"]),
    )
    try:
        offer = create_test_commercial_offer(record["opportunity_public_id"])
        offer_public_id = str(offer["public_id"])
        record["offer_public_ids"].append(offer_public_id)
        _add_offer_line(offer_public_id, scope="Hiring of 250mt crane", category="Crane", quantity="8.00", uom="Days")
        _add_offer_line(offer_public_id, scope="Pick-and-carry crane", category="Hydra", quantity="3.00", uom="Mon")
        handoff = _hand_off(offer_public_id)
        record["handoff_body"] = handoff
        work_order_public_id = str(handoff["work_order"]["public_id"])
        record["work_order_public_id"] = work_order_public_id
        record["work_order_code"] = handoff["work_order"]["work_order_code"]
        record["work_order_public_ids"].append(work_order_public_id)
        record["line_public_ids"] = [str(line["public_id"]) for line in handoff["lines"]]
        by_category = {line["equipment_service_category"]: line for line in handoff["lines"]}
        record["crane_line"] = str(by_category["Crane"]["public_id"])
        record["crane_line_number"] = by_category["Crane"]["line_number"]
        record["crane_line_index"] = record["line_public_ids"].index(record["crane_line"])
        record["hydra_line"] = str(by_category["Hydra"]["public_id"])
        record["site"] = _add_address(account_public_id, "SITE", "Berth 4, Fishing Harbour")
        yield record
    finally:
        cleanup_test_work_orders(record["work_order_public_ids"])
        _delete_account_records([account_public_id])
        cleanup_test_records(
            opportunity_public_ids=[record["opportunity_public_id"]],
            offer_public_ids=record["offer_public_ids"],
            account_public_ids=[account_public_id],
            lead_public_ids=[record["lead_public_id"]],
        )


def _body(wo, *, line: str = "crane_line", **overrides) -> dict:
    body = {
        "work_order_public_id": wo["work_order_public_id"],
        "work_order_line_public_id": wo[line],
        "create_request_key": str(uuid4()),
        "units_required": 2,
        "required_from": "2027-01-10",
        "required_to": None,
        "crew_operators_required": 1,
        "crew_helpers_required": 1,
        "crew_notes": "Operator with a valid crane licence",
        "priority_code": "NORMAL",
        "planning_notes": "Tide allows about 8 working hours a day",
        "items": [CRAWLER_220],
    }
    body.update(overrides)
    return body


def _create(wo, username: str = "ops1", **overrides):
    return client.post(URL, headers=auth_headers(username), json=_body(wo, **overrides))


def _created(wo, **overrides) -> dict:
    response = _create(wo, **overrides)
    assert response.status_code == 201, response.text
    return response.json()["resource_requirement"]


def _update_body(requirement: dict, **overrides) -> dict:
    body = {
        "expected_requirement_version": requirement["requirement_version"],
        "units_required": requirement["units_required"],
        "required_from": requirement["required_from"],
        "required_to": requirement["required_to"],
        "crew_operators_required": requirement["crew_operators_required"],
        "crew_helpers_required": requirement["crew_helpers_required"],
        "crew_notes": requirement["crew_notes"],
        "priority_code": requirement["priority_code"],
        "planning_notes": requirement["planning_notes"],
        "items": [
            {
                "equipment_class_code": item["equipment_class_code"],
                "equipment_type_code": item["equipment_type_code"],
                "equipment_specification": item["equipment_specification"],
                "capabilities": [
                    {
                        "capability_code": capability["capability_code"],
                        "minimum_value": capability["minimum_value"],
                        "choice_value": capability["choice_value"],
                    }
                    for capability in item["capabilities"]
                ],
            }
            for item in requirement["items"]
        ],
    }
    body.update(overrides)
    return body


def _update(requirement: dict, username: str = "ops1", **overrides):
    return client.put(
        f"{URL}/{requirement['requirement_public_id']}",
        headers=auth_headers(username),
        json=_update_body(requirement, **overrides),
    )


def _cancel(requirement: dict, *, reason: str = "Customer will use its own crane", version: int | None = None, username: str = "ops1"):
    return client.post(
        f"{URL}/{requirement['requirement_public_id']}/cancel",
        headers=auth_headers(username),
        json={
            "expected_requirement_version": version or requirement["requirement_version"],
            "cancellation_reason": reason,
        },
    )


def _get(requirement: dict, username: str = "sales1") -> dict:
    response = client.get(f"{URL}/{requirement['requirement_public_id']}", headers=auth_headers(username))
    assert response.status_code == 200, response.text
    return response.json()


def _defaults(wo, line: str = "crane_line", **params) -> dict:
    response = client.get(
        f"{URL}/defaults", headers=auth_headers("ops1"), params={"work_order_line_public_id": wo[line], **params}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _events(requirement_public_id: str) -> list[tuple[str, dict]]:
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT event_name, event_payload_json FROM business_event WHERE record_type = 'resource_requirement' "
                "AND record_public_id = :id ORDER BY id"
            ),
            {"id": requirement_public_id},
        ).fetchall()
    return [(row[0], json.loads(row[1]) if row[1] else {}) for row in rows]


def _set_site(wo, line: str = "crane_line", site_public_id: str | None = "site") -> None:
    response = client.put(
        f"/api/work-orders/{wo['work_order_public_id']}/lines/{wo[line]}/detail",
        headers=auth_headers("sales1"),
        json={
            "expected_detail_version": _detail_version(wo, line),
            "site_address_public_id": wo["site"]["public_id"] if site_public_id == "site" else site_public_id,
        },
    )
    assert response.status_code == 200, response.text


def _set_line_dates(wo, *, start: str | None, end: str | None, line: str = "crane_line") -> None:
    response = client.put(
        f"/api/work-orders/{wo['work_order_public_id']}/lines/{wo[line]}/detail",
        headers=auth_headers("sales1"),
        json={"expected_detail_version": _detail_version(wo, line), "line_start_date": start, "line_end_date": end},
    )
    assert response.status_code == 200, response.text


def _detail_version(wo, line: str) -> int | None:
    details = client.get(f"/api/work-orders/{wo['work_order_public_id']}/line-details", headers=auth_headers("sales1"))
    assert details.status_code == 200, details.text
    detail = next(item for item in details.json() if item["work_order_line_public_id"] == wo[line])
    return detail["detail_version"]


def _add_terms(wo, *, line: str = "crane_line", effective_from: str | None = None, expected_period_count: int = 0, **terms):
    body = {
        "expected_period_count": expected_period_count,
        "expected_latest_term_revision": 1 if expected_period_count else None,
        "effective_from": effective_from,
        **SHIFT_TERMS,
        **({} if effective_from else PART_2_FIRST_PERIOD_ONLY),
        **terms,
    }
    response = client.post(
        f"/api/work-orders/{wo['work_order_public_id']}/lines/{wo[line]}/billing-terms",
        headers=auth_headers("sales1"),
        json=body,
    )
    assert response.status_code == 201, response.text


CREW_2_AND_1 = {"crew_code": "STATED", "crew_operators_per_unit": 2, "crew_helpers_per_unit": 1, "extra_crew_charge_code": "NONE"}


# --- Nothing automatic, and the frozen handoff untouched --------------------------------------------


def test_the_handoff_creates_no_requirement_and_keeps_its_pinned_shape(wo) -> None:
    """Q1: nothing is created automatically. The handoff's output is frozen."""
    body = wo["handoff_body"]
    assert set(body["work_order"]) == HANDOFF_WORK_ORDER_KEYS
    for line in body["lines"]:
        assert set(line) == HANDOFF_LINE_KEYS
    listed = client.get(URL, headers=auth_headers("sales1"), params={"work_order_public_id": wo["work_order_public_id"]})
    assert listed.status_code == 200
    assert listed.json() == []


# --- Suggested values -------------------------------------------------------------------------------


def test_the_defaults_suggest_a_class_from_the_lines_category(wo) -> None:
    body = _defaults(wo)
    assert body["work_order_public_id"] == wo["work_order_public_id"]
    assert body["work_order_code"] == wo["work_order_code"]
    assert body["work_order_line_number"] == wo["crane_line_number"]
    assert body["suggested"]["equipment_class_code"] == "CRANE"
    assert body["suggested"]["equipment_type_code"] is None
    assert body["suggested"]["units_required"] == 1
    assert body["suggested"]["priority_code"] == "NORMAL"
    # The line's quantity counts billing units, shown for reference only (Q2).
    assert Decimal(body["line"]["quantity"]) == Decimal("8")
    assert body["line"]["uom"] == "Days"
    # Nothing recorded on the Work Order yet, so no dates and no crew to start from.
    assert body["suggested"]["required_from"] is None
    assert body["suggested"]["crew_operators_required"] is None
    assert body["existing_requirement_count"] == 0
    # The structure version in force: 3 since ERT-2 added the kinds of kit.
    assert body["taxonomy_version"] == 3


def test_a_trade_word_in_the_category_suggests_a_type_too(wo) -> None:
    body = _defaults(wo, "hydra_line")
    assert (body["suggested"]["equipment_class_code"], body["suggested"]["equipment_type_code"]) == (
        "CRANE",
        "PICK_AND_CARRY",
    )
    assert body["suggested"]["equipment_class_matched_term"] == "Hydra"


def test_the_defaults_start_from_the_contract_and_the_crew_in_force(wo) -> None:
    """Q4: crew starts from the Work Order's Part 4 numbers in force when the requirement starts."""
    assert _save_period(wo).status_code == 200
    _add_terms(wo, **CREW_2_AND_1)
    _add_terms(
        wo,
        effective_from="2027-02-01",
        expected_period_count=1,
        **{
            **CREW_2_AND_1,
            "crew_operators_per_unit": 3,
            "billing_uom_code": "DAY",
            "contracted_hours_per_billing_unit": "12.00",
            # Slice 7D Part 5: the line's facts say how many shifts a day the Work Order states.
            "shift_pattern_code": "TWO_SHIFTS",
        },
    )
    body = _defaults(wo)
    assert body["suggested"]["required_from"] == "2027-01-01"
    assert (body["suggested"]["crew_operators_required"], body["suggested"]["crew_helpers_required"]) == (2, 1)
    assert body["line"]["billing_uom_code"] == "SHIFT"
    assert body["line"]["billing_terms_period_number"] == 1
    # The first period answers "not in the Work Order" for shifts: it states none, so there is no count (round 2).
    assert body["line"]["shifts_per_day"] is None
    later = _defaults(wo, required_from="2027-02-10")
    assert (later["suggested"]["crew_operators_required"], later["suggested"]["crew_helpers_required"]) == (3, 1)
    assert later["line"]["billing_uom_code"] == "DAY"
    assert later["line"]["shifts_per_day"] == 2
    assert "night_shift_charged" not in later["line"]
    # No rate or amount is given: commercial terms are referenced, not copied (WRR-001).
    assert not any("rate" in key or "amount" in key for key in body["line"])


def test_equipment_only_starts_the_crew_at_zero(wo) -> None:
    _add_terms(wo)  # SHIFT_TERMS answer crew as NONE: equipment only
    body = _defaults(wo)
    assert (body["suggested"]["crew_operators_required"], body["suggested"]["crew_helpers_required"]) == (0, 0)


def test_the_defaults_refuse_an_unknown_line() -> None:
    response = client.get(f"{URL}/defaults", headers=auth_headers("ops1"), params={"work_order_line_public_id": str(uuid4())})
    assert response.status_code == 404


# --- Creating ---------------------------------------------------------------------------------------


def test_a_requirement_is_recorded_with_its_reference_item_and_event(wo) -> None:
    response = _create(wo)
    assert response.status_code == 201, response.text
    body = response.json()
    requirement = body["resource_requirement"]
    assert set(requirement) == REQUIREMENT_KEYS
    assert re.fullmatch(r"RR-\d{6,}", requirement["requirement_reference"])
    assert requirement["requirement_status_code"] == "OPEN"
    assert requirement["requirement_version"] == 1
    assert requirement["taxonomy_version"] == 3
    assert requirement["work_order_code"] == wo["work_order_code"]
    assert requirement["work_order_line_public_id"] == wo["crane_line"]
    assert requirement["account_public_id"] == wo["account_public_id"]
    item = requirement["items"][0]
    assert (item["item_number"], item["equipment_class_label"], item["equipment_type_label"]) == (1, "Crane", "Crawler")
    capability = item["capabilities"][0]
    assert (capability["capability_code"], capability["unit_symbol"], capability["is_key"]) == ("RATED_CAPACITY", "t", True)
    assert Decimal(capability["minimum_value"]) == Decimal("220")
    assert body["event"]["event_name"] == "ResourceRequirementCreated"
    assert _events(requirement["requirement_public_id"])[0][0] == "ResourceRequirementCreated"


def test_the_event_payload_carries_codes_and_ids_but_no_free_text_or_amount(wo) -> None:
    _set_site(wo)
    requirement = _created(wo)
    ((name, payload),) = _events(requirement["requirement_public_id"])
    assert name == "ResourceRequirementCreated"
    assert set(payload) == EVENT_PAYLOAD_KEYS
    assert payload["site_address_public_id"] == wo["site"]["public_id"]
    assert payload["items"] == [
        {
            "item_number": 1,
            "equipment_class_code": "CRANE",
            "equipment_type_code": "CRAWLER",
            "capabilities": [{"capability_code": "RATED_CAPACITY", "value": "220.000"}],
        }
    ]
    stored = json.dumps(payload)
    for free_text in ("Luffing fly jib", "valid crane licence", "Tide allows"):
        assert free_text not in stored
    assert not any("amount" in key or "rate" in key for key in payload)


def test_a_line_may_have_several_requirements(wo) -> None:
    """Q7: each with its own kind of machine, capability, number and dates."""
    first = _created(wo)
    second = _created(
        wo,
        units_required=1,
        required_from="2027-02-01",
        items=[{"equipment_class_code": "FORKLIFT", "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "5"}]}],
    )
    assert first["requirement_reference"] != second["requirement_reference"]
    listed = client.get(URL, headers=auth_headers("sales1"), params={"work_order_line_public_id": wo["crane_line"]})
    assert {item["requirement_public_id"] for item in listed.json()} == {
        first["requirement_public_id"],
        second["requirement_public_id"],
    }
    assert _defaults(wo)["existing_requirement_count"] == 2


def test_a_repeated_request_key_returns_the_first_requirement(wo) -> None:
    """The very same request again - a reply lost on the way, then Save pressed again - is answered with the first
    requirement, flagged `replayed`, and records nothing (TB-1 TB1-102 part b, 8A's rule)."""
    body = _body(wo)
    first = client.post(URL, headers=auth_headers("ops1"), json=body)
    again = client.post(URL, headers=auth_headers("ops1"), json=body)
    assert first.status_code == 201 and again.status_code == 201, again.text
    assert first.json()["replayed"] is False and again.json()["replayed"] is True
    assert again.json()["resource_requirement"] == first.json()["resource_requirement"]
    assert again.json()["event"] is None
    listed = client.get(URL, headers=auth_headers("sales1"), params={"work_order_public_id": wo["work_order_public_id"]})
    assert len(listed.json()) == 1
    assert _rows_with_key(body["create_request_key"]) == 1
    assert len(_events(first.json()["resource_requirement"]["requirement_public_id"])) == 1


def test_a_used_request_key_with_a_changed_request_is_refused(wo) -> None:
    """The defect TB-1 found (TB1-305): a form whose first save was recorded but whose reply was lost, then edited
    and saved again, got the FIRST requirement back with 201 and the edit was dropped silently. Now the changed
    request is refused (409), saying the form already recorded one, and nothing changes."""
    body = _body(wo)
    first = client.post(URL, headers=auth_headers("ops1"), json=body).json()["resource_requirement"]
    for changed in ({"units_required": 5}, {"priority_code": "URGENT"}, {"crew_notes": None}, {"required_to": "2027-01-20"}):
        refused = client.post(URL, headers=auth_headers("ops1"), json={**body, **changed})
        assert refused.status_code == 409, (changed, refused.text)
        assert refused.json()["detail"] == requirements_service.REQUIREMENT_KEY_USED
    # A field left out is not the same request as the field sent empty: the request as sent is what counts.
    left_out = {name: value for name, value in body.items() if name != "required_to"}
    assert client.post(URL, headers=auth_headers("ops1"), json=left_out).status_code == 409
    stored = client.get(f"{URL}/{first['requirement_public_id']}", headers=auth_headers("sales1")).json()
    assert stored == first
    assert _rows_with_key(body["create_request_key"]) == 1
    assert len(_events(first["requirement_public_id"])) == 1


def test_a_request_key_reused_for_another_line_is_refused(wo) -> None:
    body = _body(wo)
    assert client.post(URL, headers=auth_headers("ops1"), json=body).status_code == 201
    other = client.post(URL, headers=auth_headers("ops1"), json={**body, "work_order_line_public_id": wo["hydra_line"]})
    assert other.status_code == 409
    assert other.json()["detail"] == requirements_service.REQUIREMENT_KEY_USED
    assert _rows_with_key(body["create_request_key"]) == 1


def test_a_requirement_keeps_the_fingerprint_of_the_request_that_made_it(wo) -> None:
    body = _body(wo)
    assert client.post(URL, headers=auth_headers("ops1"), json=body).status_code == 201
    assert stored_fingerprints("resource_requirement", body["create_request_key"]) == [
        request_fingerprint(ResourceRequirementCreate(**body))
    ]


def test_a_key_recorded_before_fingerprints_is_refused_never_replayed(wo) -> None:
    """A requirement made before migration 0050 has no fingerprint: the request that made it cannot be known, so its
    key is refused even with the same body, rather than taken for a request it may not have been."""
    body = _body(wo)
    first = client.post(URL, headers=auth_headers("ops1"), json=body).json()["resource_requirement"]
    as_made_before_fingerprints("resource_requirement", body["create_request_key"])
    again = client.post(URL, headers=auth_headers("ops1"), json=body)
    assert again.status_code == 409, again.text
    assert again.json()["detail"] == requirements_service.REQUIREMENT_KEY_USED
    assert _rows_with_key(body["create_request_key"]) == 1
    assert len(_events(first["requirement_public_id"])) == 1


def _race_creates(monkeypatch, bodies: list[dict]) -> list[tuple[str, object]]:
    """Run creates at once, as two browser tabs submitting a form would: the loser's second lookup, after the
    unique index refuses its insert, is the path under test."""
    actor = user_public_id("ops1")
    return run_at_once(
        monkeypatch,
        requirements_service,
        "find_requirement_by_create_request_key",
        [
            lambda db, body=body: requirements_service.create_resource_requirement(
                db, payload=ResourceRequirementCreate(**body), current_user_public_id=actor
            )
            for body in bodies
        ],
    )


def _rows_with_key(key: str) -> int:
    with SessionLocal() as db:
        return int(
            db.execute(
                text("SELECT COUNT(*) FROM resource_requirement WHERE create_request_key = :key"), {"key": key}
            ).scalar_one()
        )


def test_two_simultaneous_creates_with_one_key_record_one_requirement(wo, monkeypatch) -> None:
    """ADR-023: the second of two racing submissions replays the first instead of failing."""
    body = _body(wo)
    results = _race_creates(monkeypatch, [body, dict(body)])
    assert [outcome for outcome, _ in results] == ["ok", "ok"], results
    responses = [response for _, response in results]
    assert responses[0].resource_requirement.requirement_public_id == responses[1].resource_requirement.requirement_public_id
    assert sorted(response.event is None for response in responses) == [False, True]
    assert sorted(response.replayed for response in responses) == [False, True]
    assert _rows_with_key(body["create_request_key"]) == 1
    assert len(_events(str(responses[0].resource_requirement.requirement_public_id))) == 1


def test_two_simultaneous_creates_with_one_key_on_different_lines_record_one(wo, monkeypatch) -> None:
    body = _body(wo)
    results = _race_creates(monkeypatch, [body, {**body, "work_order_line_public_id": wo["hydra_line"]}])
    outcomes = sorted(outcome for outcome, _ in results)
    assert outcomes == ["error", "ok"], results
    refused = next(value for outcome, value in results if outcome == "error")
    assert isinstance(refused, requirements_service.ResourceRequirementConflictError)
    assert _rows_with_key(body["create_request_key"]) == 1


def test_two_simultaneous_creates_with_one_key_and_different_requests_record_one(wo, monkeypatch) -> None:
    """Two requests at once with one key on the same line but asking for different things: one is recorded, the
    other refused - never both, and never the loser answered with the winner's requirement."""
    body = _body(wo)
    results = _race_creates(monkeypatch, [body, {**body, "units_required": 7}])
    assert sorted(outcome for outcome, _ in results) == ["error", "ok"], results
    refused = next(value for outcome, value in results if outcome == "error")
    assert isinstance(refused, requirements_service.ResourceRequirementConflictError)
    assert str(refused) == requirements_service.REQUIREMENT_KEY_USED
    assert _rows_with_key(body["create_request_key"]) == 1


def test_an_unknown_line_is_not_found(wo) -> None:
    assert _create(wo, work_order_line_public_id=str(uuid4())).status_code == 404


def test_a_line_of_another_work_order_is_not_found(wo) -> None:
    # Another Work Order on the same Account: since CS-04 part 1 an offer line goes onto Work Orders once, so it comes
    # from a Supplementary Offer of the same accepted offer.
    supplementary_public_id, other = create_test_supplementary_work_order(wo["offer_public_ids"][-1])
    wo["offer_public_ids"].insert(0, supplementary_public_id)
    wo["work_order_public_ids"].append(str(other["work_order"]["public_id"]))
    response = _create(wo, work_order_line_public_id=str(other["lines"][0]["public_id"]))
    assert response.status_code == 404
    assert response.json()["detail"] == "Work Order line not found on this Work Order."


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"units_required": 0}, None),
        ({"units_required": 2_147_483_648}, None),
        ({"crew_operators_required": -1}, None),
        ({"items": []}, "Say what equipment is needed"),
        ({"items": [CRAWLER_220, CRAWLER_220]}, "one kind of equipment"),
        ({"items": [{"equipment_class_code": "PRIME_MOVER"}]}, "Prime Mover is not equipment Hiring provides"),
        ({"items": [{"equipment_class_code": "GENERATOR"}]}, "Generator is not equipment Hiring provides"),
        ({"items": [{"equipment_class_code": "TOWER_LIGHT"}]}, "TOWER_LIGHT is not an equipment class"),
        ({"items": [{"equipment_class_code": "CRANE", "equipment_type_code": "SCISSOR"}]}, "SCISSOR is not a type of Crane"),
        (
            {"items": [{"equipment_class_code": "CRANE", "capabilities": [{"capability_code": "WORKING_HEIGHT", "minimum_value": "30"}]}]},
            "does not describe a Crane",
        ),
        (
            {
                "items": [
                    {
                        "equipment_class_code": "CRANE",
                        "capabilities": [
                            {"capability_code": "RATED_CAPACITY", "minimum_value": "100"},
                            {"capability_code": "RATED_CAPACITY", "minimum_value": "200"},
                        ],
                    }
                ]
            },
            "Rated capacity is given twice",
        ),
        (
            {"items": [{"equipment_class_code": "CRANE", "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "220", "unit_code": "KILOGRAM"}]}]},
            None,
        ),
        ({"items": [{"equipment_class_code": "CRANE", "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "0"}]}]}, None),
        ({"items": [{"equipment_class_code": "CRANE", "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "-5"}]}]}, None),
        ({"items": [{"equipment_class_code": "CRANE", "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "NaN"}]}]}, None),
        # numeric(12,3) holds nine digits before the point: a larger value is a 422, never a 500.
        ({"items": [{"equipment_class_code": "CRANE", "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "1234567890"}]}]}, None),
        ({"items": [{"equipment_class_code": "CRANE", "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "1e10"}]}]}, None),
        ({"items": [{"equipment_class_code": "CRANE", "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "1.2345"}]}]}, None),
        (
            {"items": [{"equipment_class_code": "CRANE", "capabilities": [{"capability_code": "RATED_CAPACITY", "choice_value": "BIG"}]}]},
            "Give the least rated capacity in t",
        ),
        ({"required_from": "2027-01-10", "required_to": "2027-01-09"}, "cannot end on 9 January 2027, before it starts on 10 January 2027"),
        ({"priority_code": "CRITICAL"}, "Priority must be Normal or Urgent"),
        ({"deployment_pattern_code": "ON_CALL"}, None),
    ],
)
def test_a_requirement_that_breaks_a_rule_is_refused(wo, overrides, expected) -> None:
    response = _create(wo, **overrides)
    assert response.status_code == 422, response.text
    if expected is not None:
        assert expected in response.json()["detail"]
    listed = client.get(URL, headers=auth_headers("sales1"), params={"work_order_public_id": wo["work_order_public_id"]})
    assert listed.json() == []


def test_a_count_capability_takes_whole_numbers_only() -> None:
    """No Hiring class has a count capability in version 1, so the rule is checked on a trailer's axles."""
    with SessionLocal() as db:
        structure = get_equipment_structure(db)
    trailer = next(item for item in structure.classes if item.class_code == "TRAILER")
    with pytest.raises(requirements_service.ResourceRequirementValidationError, match="Axles is counted in whole numbers"):
        requirements_service._normalize_capability(
            ResourceRequirementCapabilityInput(capability_code="AXLE_COUNT", minimum_value=Decimal("4.5")),
            trailer,
            kept_codes=set(),
        )
    whole = requirements_service._normalize_capability(
        ResourceRequirementCapabilityInput(capability_code="AXLE_COUNT", minimum_value=Decimal("4")), trailer, kept_codes=set()
    )
    assert whole.minimum_value == Decimal("4")


def test_a_fixed_list_capability_takes_one_of_its_values() -> None:
    with SessionLocal() as db:
        structure = get_equipment_structure(db)
    prime_mover = next(item for item in structure.classes if item.class_code == "PRIME_MOVER")
    chosen = requirements_service._normalize_capability(
        ResourceRequirementCapabilityInput(capability_code="AXLE_CONFIGURATION", choice_value="6x4"), prime_mover, kept_codes=set()
    )
    assert chosen.choice_value == "6X4"
    with pytest.raises(requirements_service.ResourceRequirementValidationError, match="must be one of 4X2"):
        requirements_service._normalize_capability(
            ResourceRequirementCapabilityInput(capability_code="AXLE_CONFIGURATION", choice_value="10X10"),
            prime_mover,
            kept_codes=set(),
        )


# --- Dates against the contract and the line (Q8) ----------------------------------------------------


def test_with_no_contract_recorded_any_dates_are_accepted(wo) -> None:
    """A bound not recorded is never treated as broken."""
    assert _create(wo, required_from="2020-01-01", required_to="2040-12-31").status_code == 201


@pytest.mark.parametrize(
    ("dates", "message"),
    [
        (
            {"required_from": "2026-12-31"},
            "This requirement starts on 31 December 2026, before the contract starts on 1 January 2027.",
        ),
        (
            {"required_from": "2027-01-10", "required_to": "2027-04-01"},
            "This requirement ends on 1 April 2027, after the contract ends on 31 March 2027.",
        ),
    ],
)
def test_dates_outside_the_contract_are_refused_naming_the_dates(wo, dates, message) -> None:
    assert _save_period(wo).status_code == 200
    response = _create(wo, **dates)
    assert response.status_code == 422
    assert response.json()["detail"] == message


def test_a_date_in_a_gap_between_extensions_is_refused(wo) -> None:
    assert _save_period(wo).status_code == 200
    extended = _extend(wo, new_end_date="2027-06-30", extension_start_date="2027-04-15", gap_confirmed_from="2027-04-01")
    assert extended.status_code == 201, extended.text
    response = _create(wo, required_from="2027-04-05")
    assert response.status_code == 422
    assert "when no contract runs" in response.json()["detail"]
    # Spanning the gap is allowed, as a line's own dates may (Slice 7D Part 3).
    assert _create(wo, required_from="2027-03-01", required_to="2027-05-31").status_code == 201


def test_dates_outside_the_lines_own_dates_are_refused(wo) -> None:
    _set_line_dates(wo, start="2027-02-01", end="2027-02-28")
    number = wo["crane_line_number"]
    before = _create(wo, required_from="2027-01-31")
    assert before.status_code == 422
    assert before.json()["detail"] == f"This requirement starts on 31 January 2027, before line {number} starts on 1 February 2027."
    after = _create(wo, required_from="2027-02-10", required_to="2027-03-01")
    assert after.json()["detail"] == f"This requirement ends on 1 March 2027, after line {number} ends on 28 February 2027."
    late = _create(wo, required_from="2027-03-01")
    assert late.json()["detail"] == f"This requirement starts on 1 March 2027, after line {number} ends on 28 February 2027."
    # Blank end means until the line ends.
    assert _create(wo, required_from="2027-02-10", required_to=None).status_code == 201


# --- Permissions (Q6) -------------------------------------------------------------------------------


@pytest.mark.parametrize("username", WRITE_ROLES)
def test_operations_and_admin_may_record_a_requirement(wo, username: str) -> None:
    assert _create(wo, username=username).status_code == 201


@pytest.mark.parametrize("username", NON_WRITE_ROLES)
def test_every_other_role_is_refused_every_write(wo, username: str) -> None:
    assert _create(wo, username=username).status_code == 403
    requirement = _created(wo)
    assert _update(requirement, username=username, units_required=3).status_code == 403
    assert _cancel(requirement, username=username).status_code == 403
    assert _get(requirement)["requirement_version"] == 1


@pytest.mark.parametrize("username", READ_ROLES)
def test_every_role_that_can_view_work_orders_can_read_requirements(wo, username: str) -> None:
    requirement = _created(wo)
    assert _get(requirement, username=username)["requirement_public_id"] == requirement["requirement_public_id"]
    assert client.get(URL, headers=auth_headers(username)).status_code == 200
    assert (
        client.get(f"{URL}/defaults", headers=auth_headers(username), params={"work_order_line_public_id": wo["crane_line"]}).status_code
        == 200
    )


def test_an_unauthenticated_caller_is_refused(wo) -> None:
    assert client.get(URL).status_code == 401
    assert client.post(URL, json=_body(wo)).status_code == 401


def test_the_six_requirement_routes_are_the_only_ones_and_there_is_no_uncancel() -> None:
    routes = {
        (method, route.path)
        for route in app.routes
        if getattr(route, "path", "").startswith(URL)
        for method in getattr(route, "methods", set())
    }
    assert routes == {
        ("GET", URL),
        ("POST", URL),
        ("GET", f"{URL}/defaults"),
        ("GET", f"{URL}/{{public_id}}"),
        ("PUT", f"{URL}/{{public_id}}"),
        ("POST", f"{URL}/{{public_id}}/cancel"),
    }


# --- Changing ---------------------------------------------------------------------------------------


def test_a_change_replaces_the_requirement_and_names_what_changed(wo) -> None:
    requirement = _created(wo)
    response = _update(
        requirement,
        units_required=3,
        priority_code="urgent",
        items=[{"equipment_class_code": "CRANE", "equipment_type_code": "ALL_TERRAIN", "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "250"}]}],
    )
    assert response.status_code == 200, response.text
    changed = response.json()["resource_requirement"]
    assert changed["requirement_version"] == 2
    assert changed["units_required"] == 3
    assert changed["priority_code"] == "URGENT"
    assert changed["items"][0]["equipment_type_code"] == "ALL_TERRAIN"
    assert changed["items"][0]["equipment_specification"] is None
    assert response.json()["event"]["event_name"] == "ResourceRequirementUpdated"
    name, payload = _events(requirement["requirement_public_id"])[-1]
    assert name == "ResourceRequirementUpdated"
    assert payload["changed_fields"] == ["units_required", "priority_code", "items"]
    assert payload["requirement_version"] == 2


def test_an_identical_save_records_nothing(wo) -> None:
    requirement = _created(wo)
    response = _update(requirement)
    assert response.status_code == 200, response.text
    assert response.json()["event"] is None
    assert response.json()["resource_requirement"]["requirement_version"] == 1
    assert len(_events(requirement["requirement_public_id"])) == 1


def test_a_change_against_a_version_someone_else_moved_is_refused(wo) -> None:
    requirement = _created(wo)
    assert _update(requirement, units_required=3).status_code == 200
    stale = _update(requirement, units_required=4)
    assert stale.status_code == 409
    assert _get(requirement)["units_required"] == 3


def test_a_change_is_checked_as_a_new_requirement_is(wo) -> None:
    assert _save_period(wo).status_code == 200
    requirement = _created(wo)
    assert _update(requirement, required_from="2026-12-01").status_code == 422
    assert _update(requirement, items=[{"equipment_class_code": "PRIME_MOVER"}]).status_code == 422
    assert _update(requirement, unit_code="TONNE").status_code == 422
    assert _get(requirement)["requirement_version"] == 1


def test_an_unknown_requirement_is_not_found() -> None:
    fake = {"requirement_public_id": str(uuid4()), "requirement_version": 1}
    assert client.get(f"{URL}/{fake['requirement_public_id']}", headers=auth_headers("sales1")).status_code == 404
    assert _cancel(fake).status_code == 404


# --- Cancelling -------------------------------------------------------------------------------------


def test_cancelling_needs_a_reason_and_is_final(wo) -> None:
    requirement = _created(wo)
    blank = _cancel(requirement, reason="   ")
    assert blank.status_code == 422
    assert "reason" in blank.json()["detail"]
    response = _cancel(requirement)
    assert response.status_code == 200, response.text
    cancelled = response.json()["resource_requirement"]
    assert cancelled["requirement_status_code"] == "CANCELLED"
    assert cancelled["requirement_version"] == 2
    assert cancelled["cancellation_reason"] == "Customer will use its own crane"
    assert cancelled["cancelled_at"] is not None
    assert cancelled["warnings"] == []
    # Final: neither cancelled again nor changed, and still readable.
    assert _cancel(cancelled).status_code == 422
    assert _update(cancelled, units_required=4).status_code == 422
    assert _get(requirement)["requirement_status_code"] == "CANCELLED"
    name, payload = _events(requirement["requirement_public_id"])[-1]
    assert name == "ResourceRequirementCancelled"
    assert payload["changed_fields"] == ["requirement_status_code"]
    assert "Customer will use its own crane" not in json.dumps(payload)


def test_cancelling_against_a_moved_version_is_refused(wo) -> None:
    requirement = _created(wo)
    assert _update(requirement, units_required=3).status_code == 200
    assert _cancel(requirement, version=1).status_code == 409
    assert _get(requirement)["requirement_status_code"] == "OPEN"


def test_a_closed_work_order_refuses_every_write(wo) -> None:
    requirement = _created(wo)
    with SessionLocal() as db:
        db.execute(
            text("UPDATE crm_work_order SET work_order_status_code = 'CLOSED' WHERE work_order_public_id = :id"),
            {"id": wo["work_order_public_id"]},
        )
        db.commit()
    for response in (_create(wo), _update(requirement, units_required=3), _cancel(requirement)):
        assert response.status_code == 422
        assert "This Work Order is closed" in response.json()["detail"]
    assert _get(requirement)["requirement_version"] == 1


# --- Warnings: computed on every read, never a refusal ------------------------------------------------


def test_the_site_warning_appears_and_clears(wo) -> None:
    requirement = _created(wo)
    assert "SITE_NOT_RECORDED" in _get(requirement)["warnings"]
    _set_site(wo)
    read = _get(requirement)
    assert "SITE_NOT_RECORDED" not in read["warnings"]
    assert read["line"]["site"]["public_id"] == wo["site"]["public_id"]


def test_a_contract_change_after_saving_warns_rather_than_blocks(wo) -> None:
    """Q8: the contract change is not blocked; the requirement is warned."""
    requirement = _created(wo, required_from="2026-12-15")
    assert "OUTSIDE_CONTRACT" not in _get(requirement)["warnings"]
    assert _save_period(wo).status_code == 200  # contract from 1 January 2027
    assert "OUTSIDE_CONTRACT" in _get(requirement)["warnings"]
    assert _save_period(wo, expected_period_version=1, contract_start_date="2026-12-01").status_code == 200
    assert "OUTSIDE_CONTRACT" not in _get(requirement)["warnings"]


def test_a_line_date_change_after_saving_warns(wo) -> None:
    requirement = _created(wo, required_from="2027-01-10")
    _set_line_dates(wo, start="2027-02-01", end=None)
    assert "OUTSIDE_CONTRACT" in _get(requirement)["warnings"]


def test_the_crew_warning_follows_the_work_orders_numbers(wo) -> None:
    _add_terms(wo, **CREW_2_AND_1)
    requirement = _created(wo, crew_operators_required=1, crew_helpers_required=1)
    read = _get(requirement)
    assert "CREW_DIFFERS_FROM_WORK_ORDER" in read["warnings"]
    assert (read["line"]["work_order_crew_operators"], read["line"]["work_order_crew_helpers"]) == (2, 1)
    changed = _update(read, crew_operators_required=2).json()["resource_requirement"]
    assert "CREW_DIFFERS_FROM_WORK_ORDER" not in changed["warnings"]


def test_no_crew_warning_while_the_work_orders_crew_is_unanswered(wo) -> None:
    requirement = _created(wo, crew_operators_required=4, crew_helpers_required=4)
    assert "CREW_DIFFERS_FROM_WORK_ORDER" not in _get(requirement)["warnings"]


def test_a_stated_crew_with_a_number_still_blank_is_not_read_as_zero(wo) -> None:
    """Part 4 lets a stated crew be saved with a number missing, and reports it missing. A blank is not
    an answer, so it suggests nothing and raises no crew warning - it is never taken as zero."""
    _add_terms(wo, crew_code="STATED", crew_operators_per_unit=2, extra_crew_charge_code="NONE")
    suggested = _defaults(wo)["suggested"]
    assert (suggested["crew_operators_required"], suggested["crew_helpers_required"]) == (None, None)
    requirement = _created(wo, crew_operators_required=2, crew_helpers_required=5)
    assert "CREW_DIFFERS_FROM_WORK_ORDER" not in _get(requirement)["warnings"]


def test_the_key_capability_warning_appears_and_clears(wo) -> None:
    requirement = _created(wo, items=[{"equipment_class_code": "CRANE", "capabilities": [{"capability_code": "MAIN_BOOM_LENGTH", "minimum_value": "60"}]}])
    assert "KEY_CAPABILITY_NOT_STATED" in _get(requirement)["warnings"]
    changed = _update(requirement, items=[CRAWLER_220]).json()["resource_requirement"]
    assert "KEY_CAPABILITY_NOT_STATED" not in changed["warnings"]


# --- The planning list ------------------------------------------------------------------------------


def test_the_planning_list_puts_urgent_first_then_the_earliest_start(wo) -> None:
    late_normal = _created(wo, required_from="2027-03-01")
    early_normal = _created(wo, required_from="2027-01-05")
    late_urgent = _created(wo, required_from="2027-02-01", priority_code="URGENT")
    listed = client.get(URL, headers=auth_headers("sales1"), params={"work_order_public_id": wo["work_order_public_id"]})
    assert [item["requirement_public_id"] for item in listed.json()] == [
        late_urgent["requirement_public_id"],
        early_normal["requirement_public_id"],
        late_normal["requirement_public_id"],
    ]


def test_the_planning_list_filters_by_status_and_class(wo) -> None:
    crane = _created(wo)
    forklift = _created(wo, items=[{"equipment_class_code": "FORKLIFT"}])
    assert _cancel(crane).status_code == 200
    params = {"work_order_public_id": wo["work_order_public_id"]}
    open_only = client.get(URL, headers=auth_headers("sales1"), params={**params, "status_code": "OPEN"}).json()
    assert [item["requirement_public_id"] for item in open_only] == [forklift["requirement_public_id"]]
    cranes = client.get(URL, headers=auth_headers("sales1"), params={**params, "equipment_class_code": "crane"}).json()
    assert [item["requirement_public_id"] for item in cranes] == [crane["requirement_public_id"]]
    assert client.get(URL, headers=auth_headers("sales1"), params={"status_code": "DONE"}).status_code == 422


# --- Retired codes: anything saved with them keeps them -----------------------------------------------


def test_a_retired_type_cannot_be_chosen_but_a_requirement_saved_with_it_keeps_it(wo) -> None:
    """Codes never change and nothing is deleted: a retired type stays on what was saved with it, and is
    offered to nothing new (design section 4). A test-only type and version keep the real ones untouched."""
    with SessionLocal() as db:
        db.execute(
            text(
                "INSERT INTO equipment_type (type_code, class_code, type_label, display_order, introduced_in_version) "
                "VALUES ('TEST_WRR_RETIRING', 'CRANE', 'Test retiring type', 999, 1)"
            )
        )
        db.commit()
    try:
        requirement = _created(wo, items=[{"equipment_class_code": "CRANE", "equipment_type_code": "TEST_WRR_RETIRING"}])
        with SessionLocal() as db:
            db.execute(
                text(
                    "INSERT INTO equipment_taxonomy_version (version_number, version_label, source_note, component_depth) "
                    "VALUES (999, 'Test version', 'Created and removed by a WRR-001 test.', 3)"
                )
            )
            db.execute(text("UPDATE equipment_type SET retired_in_version = 999 WHERE type_code = 'TEST_WRR_RETIRING'"))
            db.commit()

        refused = _create(wo, items=[{"equipment_class_code": "CRANE", "equipment_type_code": "TEST_WRR_RETIRING"}])
        assert refused.status_code == 422
        assert "has been retired" in refused.json()["detail"]
        kept = _update(requirement, units_required=3)
        assert kept.status_code == 200, kept.text
        assert kept.json()["resource_requirement"]["items"][0]["equipment_type_label"] == "Test retiring type"
        assert kept.json()["resource_requirement"]["taxonomy_version"] == 999
    finally:
        # This Work Order's requirements go first - one of them names the test type and version 999 -
        # then the test type and version. Nothing outside this Work Order and these two rows is touched.
        _delete_requirements_of(wo["work_order_public_id"])
        with SessionLocal() as db:
            db.execute(text("DELETE FROM equipment_type WHERE type_code = 'TEST_WRR_RETIRING'"))
            db.execute(text("DELETE FROM equipment_taxonomy_version WHERE version_number = 999"))
            db.commit()


def _delete_requirements_of(work_order_public_id: str) -> None:
    with SessionLocal() as db:
        for statement in (
            """
            DELETE FROM resource_requirement_item_capability c
            USING resource_requirement_item i, resource_requirement rr
            WHERE i.id = c.resource_requirement_item_id AND rr.id = i.resource_requirement_id
              AND rr.work_order_public_id = :id
            """,
            """
            DELETE FROM resource_requirement_item i USING resource_requirement rr
            WHERE rr.id = i.resource_requirement_id AND rr.work_order_public_id = :id
            """,
            "DELETE FROM resource_requirement WHERE work_order_public_id = :id",
        ):
            db.execute(text(statement), {"id": work_order_public_id})
        db.commit()


# --- The database's own backstop ------------------------------------------------------------------


def _item_id(requirement: dict) -> int:
    with SessionLocal() as db:
        return int(
            db.execute(
                text(
                    "SELECT i.id FROM resource_requirement_item i JOIN resource_requirement rr "
                    "ON rr.id = i.resource_requirement_id WHERE rr.requirement_public_id = :id"
                ),
                {"id": requirement["requirement_public_id"]},
            ).scalar_one()
        )


def _refused_in_database(statements: list[tuple[str, dict]], constraint: str) -> None:
    """Run the statements in one transaction, expect the last to be refused under `constraint`, and roll
    everything back so the shared data is untouched."""
    from sqlalchemy.exc import IntegrityError

    with SessionLocal() as db:
        try:
            for sql, params in statements[:-1]:
                db.execute(text(sql), params)
            with pytest.raises(IntegrityError) as refused:
                db.execute(text(statements[-1][0]), statements[-1][1])
            # The constraint named in the error itself, which a trigger's refusal carries here and not in
            # its message; for a CHECK it is the same name the message quotes.
            assert refused.value.orig.diag.constraint_name == constraint
        finally:
            db.rollback()


def _item_as(item_id: int, class_code: str) -> list[tuple[str, dict]]:
    """Turn the requirement's one item into an item of another class, its capabilities removed."""
    return [
        ("DELETE FROM resource_requirement_item_capability WHERE resource_requirement_item_id = :id", {"id": item_id}),
        (
            "UPDATE resource_requirement_item SET equipment_class_code = :class, equipment_type_code = NULL WHERE id = :id",
            {"id": item_id, "class": class_code},
        ),
    ]


def _capability_insert(item_id: int, class_code: str, capability: str, minimum, choice) -> tuple[str, dict]:
    return (
        "INSERT INTO resource_requirement_item_capability "
        "(resource_requirement_item_id, equipment_class_code, capability_code, minimum_value, choice_value) "
        "VALUES (:id, :class, :capability, :minimum, :choice)",
        {"id": item_id, "class": class_code, "capability": capability, "minimum": minimum, "choice": choice},
    )


@pytest.mark.parametrize(
    ("class_code", "capability", "minimum", "choice"),
    [
        ("CRANE", "MAIN_BOOM_LENGTH", None, "LONG"),  # a choice for a measured capability
        ("PRIME_MOVER", "AXLE_CONFIGURATION", Decimal("1"), None),  # a least value for a fixed list
        ("PRIME_MOVER", "AXLE_CONFIGURATION", None, "10X10"),  # a choice not on the list
        ("TRAILER", "AXLE_COUNT", Decimal("4.5"), None),  # a fraction of a count
    ],
)
def test_the_database_refuses_a_value_that_does_not_fit_its_capability(wo, class_code, capability, minimum, choice) -> None:
    item_id = _item_id(_created(wo))
    _refused_in_database(
        [*_item_as(item_id, class_code), _capability_insert(item_id, class_code, capability, minimum, choice)],
        "ck_rr_item_capability_matches_kind",
    )


def test_the_database_accepts_values_that_fit_their_capability(wo) -> None:
    """The counterpart: the trigger refuses only what does not fit."""
    item_id = _item_id(_created(wo))
    with SessionLocal() as db:
        try:
            for sql, params in [
                *_item_as(item_id, "PRIME_MOVER"),
                _capability_insert(item_id, "PRIME_MOVER", "AXLE_CONFIGURATION", None, "6X4"),
                _capability_insert(item_id, "PRIME_MOVER", "GROSS_COMBINATION_WEIGHT", Decimal("55.5"), None),
            ]:
                db.execute(text(sql), params)
            for sql, params in [
                *_item_as(item_id, "TRAILER"),
                _capability_insert(item_id, "TRAILER", "AXLE_COUNT", Decimal("4"), None),
            ]:
                db.execute(text(sql), params)
        finally:
            db.rollback()


@pytest.mark.parametrize(
    ("cancelled_by", "constraint"),
    [
        (None, "ck_resource_requirement_cancellation"),
        ("", "fk_resource_requirement_cancelled_by"),
        ("00000000-0000-0000-0000-00000000dead", "fk_resource_requirement_cancelled_by"),
    ],
)
def test_the_database_refuses_a_cancellation_without_a_real_canceller(wo, cancelled_by, constraint) -> None:
    """No one, a blank, or an id that is no user: each leaves the cancellation unattributed."""
    requirement = _created(wo)
    _refused_in_database(
        [
            (
                "UPDATE resource_requirement SET requirement_status_code = 'CANCELLED', cancellation_reason = 'test', "
                "cancelled_at = CURRENT_TIMESTAMP, cancelled_by = :by WHERE requirement_public_id = :id",
                {"id": requirement["requirement_public_id"], "by": cancelled_by},
            )
        ],
        constraint,
    )


def test_a_cancellation_records_who_cancelled(wo) -> None:
    requirement = _created(wo)
    cancelled = _cancel(requirement).json()["resource_requirement"]
    with SessionLocal() as db:
        ops1 = str(db.execute(text("SELECT public_id FROM app_user WHERE username = 'ops1'")).scalar_one())
    assert cancelled["cancelled_by"] == ops1
    with pytest.raises(requirements_service.ResourceRequirementValidationError, match="could not be identified"):
        with SessionLocal() as db:
            requirements_service.cancel_resource_requirement(
                db,
                public_id=requirement["requirement_public_id"],
                payload=requirements_service.ResourceRequirementCancel(expected_requirement_version=2, cancellation_reason="x"),
                current_user_public_id=None,
            )
