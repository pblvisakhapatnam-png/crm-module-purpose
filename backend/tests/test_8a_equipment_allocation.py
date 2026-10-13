"""8A core - own machines allocated to the resource requirements, through the API and at the database.

docs/agent/slices/8a-core-equipment-allocation.md, section 15. The rules are the owner's answers of 28 September
2026 (Q1 hold before release, Q2 warnings and "needs approval", Q3 one package). Every machine, model and number is
invented and carries a run-unique token.

The fleet - invented cranes with their certificates, and kit held for their model - is made once for the module and
removed at its end. Each test makes its own Work Order, requirement and allocations, which the Work Order's cleanup
removes before the module's decisions and machines go.
"""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.resource_assignments import service as assignment_service
from app.modules.resource_assignments.errors import AssignmentForbiddenError, AssignmentValidationError
from app.modules.equipment_reference.service import hold_equipment_writes
from app.modules.resource_assignments.repository import mark_service_write, take_lock
from app.modules.resource_assignments.schemas import AssignmentCreate
from app.modules.resource_assignments.views import kit_window
from app.modules.resource_requirements import ports
from app.shared import business_time
from tests.business_day_test_support import TODAY, held_to_the_test_day
from tests.eligibility_test_support import eligibility_created_here
from tests.equipment_test_support import plum_report, plum_row, suffix
from tests.test_commercial_offers_api import (
    auth_headers,
    cleanup_test_records,
    cleanup_test_work_orders,
    client,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
)
from tests.test_elg1_machine_eligibility_api import _mark, _model, _map, _recorded
from tests.test_slice_7c_work_order_line_detail import _delete_account_records
from tests.test_slice_7d_part_3_contract_period import _extend, _remove_extension, _save_period
from tests.test_wrr001_resource_requirements import _add_offer_line, _hand_off

URL = "/api/resource-assignments"
EQUIPMENT = "/api/equipment-reference"
REQUIREMENTS = "/api/resource-requirements"
ADMIN = "admin1"
READ_ROLES = ("admin1", "sales1", "manager1", "finance1", "ops1", "readonly1")
NON_WRITE_ROLES = ("sales1", "manager1", "finance1", "readonly1")
ROAD_PAPERS = ("REGISTRATION", "INSURANCE", "POLLUTION_UNDER_CONTROL", "ROAD_TAX")
START = TODAY + timedelta(days=5)
END = TODAY + timedelta(days=60)


def _ok(response, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


def _detail(response, status: int = 422) -> str:
    assert response.status_code == status, response.text
    return response.json()["detail"]


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


@pytest.fixture(scope="module", autouse=True)
def _on_the_test_day():
    with held_to_the_test_day():
        yield


# --- The fleet, made once ------------------------------------------------------------------------------------


class Fleet:
    """Four crawler cranes of one model (250 t), a smaller crawler (100 t), an all-terrain crane, a crane whose model
    is not mapped, and kit held for the 250 t model: a hook block, a sling, a counted set of four counterweight
    blocks and a boom insert.

    Crawlers' road papers may be marked not applicable (ELG-1), so:
    - `ok` and `spare` can be allocated: road papers marked, both examinations recorded with copies;
    - `warns` can be allocated with a warning: its thorough examination runs out during the job;
    - `bare` cannot be allocated: nothing recorded.
    The hook block and the counterweight need nothing further (the hook block is examined); the sling is not examined,
    so it cannot go."""

    def __init__(self) -> None:
        self.sfx = s = suffix()
        rating = lambda value: [{"capability_code": "RATED_CAPACITY", "value": value}]  # noqa: E731
        big = _model("ACME", f"CC 250 {s}", "CRANE", type_code="CRAWLER", capabilities=rating("250"))
        small = _model("ACME", f"CC 100 {s}", "CRANE", type_code="CRAWLER", capabilities=rating("100"))
        all_terrain = _model("ACME", f"AT 250 {s}", "CRANE", type_code="ALL_TERRAIN", capabilities=rating("250"))
        names = {"big": f"{s} ACME CC 250", "small": f"{s} ACME CC 100", "at": f"{s} ACME AT 250"}
        _map(names["big"], big)
        _map(names["small"], small)
        _map(names["at"], all_terrain)
        n = self.number
        rows = [plum_row(number=n(label), schedule=names["big"], category="CRANES", capacity="250", year="2018") for label in ("OK", "SPARE", "WARNS", "BARE")]
        rows.append(plum_row(number=n("SMALL"), schedule=names["small"], category="CRANES", capacity="100", year="2018"))
        rows.append(plum_row(number=n("AT"), schedule=names["at"], category="CRANES", capacity="250", year="2018"))
        rows.append(plum_row(number=n("UNKNOWN"), schedule=f"{s} MYSTERY CRANE", category="CRANES", capacity="300", year="2012"))
        imported = _ok(
            client.post(
                f"{EQUIPMENT}/imports",
                data={"report_date": TODAY.isoformat()},
                files={"file": ("report.csv", plum_report(rows), "text/csv")},
                headers=auth_headers(ADMIN),
            ),
            201,
        )["equipment_import"]
        _ok(
            client.post(
                f"{EQUIPMENT}/imports/{imported['import_public_id']}/publish",
                json={"expected_preview_version": imported["preview_version"], "pairs": []},
                headers=auth_headers(ADMIN),
            )
        )
        found = _ok(client.get(f"{EQUIPMENT}/machines", params={"search": f"T{s}-", "limit": 50}, headers=auth_headers(ADMIN)))
        by_number = {item["machine_number"]: item["asset_public_id"] for item in found}
        self.ok, self.spare, self.warns, self.bare, self.small, self.all_terrain, self.unknown = (
            by_number[n(label)] for label in ("OK", "SPARE", "WARNS", "BARE", "SMALL", "AT", "UNKNOWN")
        )
        for crane in (self.ok, self.spare, self.warns):
            for kind in ROAD_PAPERS:
                _ok(_mark(crane, kind), 201)
            _recorded(crane, "LOAD_TEST")
        for crane in (self.ok, self.spare):
            _recorded(crane, "THOROUGH_EXAMINATION")
        # Examined 350 days ago under a 12-month rule: the cover ends about 15 days from today, during the job.
        examined = TODAY - timedelta(days=350)
        _recorded(self.warns, "THOROUGH_EXAMINATION", issued_on=examined, valid_from=examined)
        hook_model = _model("ACME", f"CC 250 hook {s}", "HOOK_BLOCK", type_code="HOOK_BLOCK", capabilities=rating("250"), fits=[big])
        sling_model = _model("ACME", f"Sling 20 t {s}", "LIFTING_TACKLE", type_code="SLING", capabilities=rating("20"), fits=[big])
        weight_model = _model(
            "ACME", f"CC 250 counterweight {s}", "COUNTERWEIGHT", type_code="UPPER_COUNTERWEIGHT",
            capabilities=[{"capability_code": "WEIGHT", "value": "10"}], fits=[big],
        )
        insert_model = _model(
            "ACME", f"CC 250 insert {s}", "BOOM_JIB_SECTION", type_code="MAIN_BOOM_INSERT",
            capabilities=[{"capability_code": "LENGTH", "value": "9"}], fits=[big],
        )
        self.hook = self._kit(hook_model, 1)
        self.sling = self._kit(sling_model, 1)
        self.weight_model = weight_model
        self.counterweight = self._kit(weight_model, 4)
        self.insert = self._kit(insert_model, 1)
        _recorded(self.hook, "THOROUGH_EXAMINATION")
        _recorded(self.hook, "LOAD_TEST")

    def number(self, label: str) -> str:
        return f"T{self.sfx}-{label}"

    def _kit(self, model: dict, count: int) -> str:
        machine = _ok(client.get(f"{EQUIPMENT}/machines/{self.ok}", headers=auth_headers(ADMIN)))
        body = {
            "create_request_key": str(uuid.uuid4()),
            "machine_public_id": self.ok,
            "kit_model_public_id": model["model_public_id"],
            "expected_model_version": model["model_version"],
            "expected_asset_version": machine["asset_version"],
            "count": count,
        }
        return _ok(client.post(f"{EQUIPMENT}/kit", json=body, headers=auth_headers(ADMIN)), 201)["pieces"][0]["asset_public_id"]


@pytest.fixture(scope="module")
def fleet():
    with eligibility_created_here():
        yield Fleet()


# --- A Work Order with a crane requirement, made for each test --------------------------------------------------


def _line_detail(work_order: dict, **fields) -> dict:
    """Save the line's details. The route replaces the site and billing fields whole, so the site recorded is sent
    again unless the test changes it."""
    details = _ok(client.get(f"/api/work-orders/{work_order['work_order_public_id']}/line-details", headers=auth_headers("sales1")))
    detail = next(item for item in details if item["work_order_line_public_id"] == work_order["line"])
    body = {"expected_detail_version": detail["detail_version"], "site_address_public_id": detail["site_address_public_id"], **fields}
    return _ok(
        client.put(
            f"/api/work-orders/{work_order['work_order_public_id']}/lines/{work_order['line']}/detail",
            headers=auth_headers("sales1"),
            json=body,
        )
    )["line_detail"]


def _add_site(account_public_id: str, state: str) -> dict:
    return _ok(
        client.post(
            f"/api/accounts/{account_public_id}/addresses",
            headers=auth_headers("sales1"),
            json={"address_type_code": "SITE", "address_line1": "Jetty 2, Invented Port", "city": "Mumbai", "state": state},
        ),
        201,
    )["address"]


@contextmanager
def crane_work_order() -> Iterator[dict[str, Any]]:
    """An accepted Work Order with one crane line, its site in Maharashtra (not a central-government site), and a
    requirement for two crawler cranes of at least 200 t from five days ahead for about two months; removed with its
    allocations at the end. The harness tests use it as a Work Order the run did not make."""
    record: dict[str, Any] = {"work_order_public_ids": [], "offer_public_ids": []}
    linked = create_account_linked_test_opportunity()
    account_public_id = str(linked["account"]["public_id"])
    record.update(
        lead_public_id=str(linked["lead"]["public_id"]),
        account_public_id=account_public_id,
        opportunity_public_id=str(linked["opportunity"]["public_id"]),
    )
    try:
        offer = create_test_commercial_offer(record["opportunity_public_id"])
        record["offer_public_ids"].append(str(offer["public_id"]))
        _add_offer_line(str(offer["public_id"]), scope="Hiring of 250mt crawler crane", category="Crane", quantity="2.00", uom="Mon")
        handoff = _hand_off(str(offer["public_id"]))
        record["work_order_public_id"] = str(handoff["work_order"]["public_id"])
        record["work_order_code"] = handoff["work_order"]["work_order_code"]
        record["work_order_public_ids"].append(record["work_order_public_id"])
        record["line"] = str(handoff["lines"][0]["public_id"])
        record["site"] = _add_site(account_public_id, "Maharashtra")
        _line_detail(record, site_address_public_id=record["site"]["public_id"], site_central_government=False)
        record["requirement"] = _requirement(record)
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


@pytest.fixture
def wo(fleet):
    with crane_work_order() as record:
        yield record


def _requirement(work_order: dict, *, units: int = 2, start: date = START, end: date | None = END) -> dict:
    return _ok(_requirement_response(work_order, units=units, start=start, end=end), 201)["resource_requirement"]


def _requirement_response(
    work_order: dict, *, units: int = 2, start: date = START, end: date | None = END, key: str | None = None
):
    body = {
        "work_order_public_id": work_order["work_order_public_id"],
        "work_order_line_public_id": work_order["line"],
        "create_request_key": key or str(uuid.uuid4()),
        "units_required": units,
        "required_from": start.isoformat(),
        "required_to": _iso(end),
        "crew_operators_required": 1,
        "crew_helpers_required": 1,
        "priority_code": "NORMAL",
        "items": [
            {
                "equipment_class_code": "CRANE",
                "equipment_type_code": "CRAWLER",
                "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "200"}],
            }
        ],
    }
    return client.post(REQUIREMENTS, json=body, headers=auth_headers("ops1"))


def _get_requirement(work_order: dict) -> dict:
    return _ok(client.get(f"{REQUIREMENTS}/{work_order['requirement']['requirement_public_id']}", headers=auth_headers("ops1")))


def _allocate(work_order: dict, machine: str, *, unit: int = 1, username: str = "ops1", key: str | None = None, **fields):
    body = {
        "create_request_key": key or str(uuid.uuid4()),
        "requirement_public_id": work_order["requirement"]["requirement_public_id"],
        "unit_number": unit,
        "machine_public_id": machine,
        "planned_from": START.isoformat(),
        "planned_to": END.isoformat(),
    }
    body.update({name: (value.isoformat() if isinstance(value, date) else value) for name, value in fields.items()})
    return client.post(URL, json=body, headers=auth_headers(username))


def _allocated(work_order: dict, machine: str, **fields) -> dict:
    return _ok(_allocate(work_order, machine, **fields), 201)["assignment"]


def _get(assignment: dict, username: str = "readonly1") -> dict:
    return _ok(client.get(f"{URL}/{assignment['assignment_public_id']}", headers=auth_headers(username)))


def _candidates(work_order: dict, *, unit: int = 1, username: str = "readonly1", **params) -> dict:
    query = {"requirement_public_id": work_order["requirement"]["requirement_public_id"], "unit_number": unit}
    query.update({name: (value.isoformat() if isinstance(value, date) else value) for name, value in params.items()})
    return _ok(client.get(f"{URL}/candidates", params=query, headers=auth_headers(username)))


def _post(assignment: dict, action: str, username: str = "ops1", **fields):
    body = {"expected_assignment_version": assignment["assignment_version"]}
    body.update({name: (value.isoformat() if isinstance(value, date) else value) for name, value in fields.items()})
    return client.post(f"{URL}/{assignment['assignment_public_id']}/{action}", json=body, headers=auth_headers(username))


def _put(assignment: dict, action: str, username: str = "ops1", **fields):
    body = {"expected_assignment_version": assignment["assignment_version"]}
    body.update({name: (value.isoformat() if isinstance(value, date) else value) for name, value in fields.items()})
    return client.put(f"{URL}/{assignment['assignment_public_id']}/{action}", json=body, headers=auth_headers(username))


def _events(record_public_id: str) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT event_name, reason, status_before, status_after, event_payload_json FROM business_event WHERE record_public_id = :id ORDER BY id"),
            {"id": record_public_id},
        ).fetchall()
    events = []
    for row in rows:
        event = dict(row._mapping)
        value = event.pop("event_payload_json")
        event["event_payload"] = json.loads(value) if isinstance(value, str) else value
        events.append(event)
    return events


def _decision_rows(requested_for_public_id: str) -> list[dict]:
    with SessionLocal() as db:
        return [
            dict(row._mapping)
            for row in db.execute(
                text("SELECT decision_public_id, overall_code, requested_for_type FROM eligibility_decision WHERE requested_for_public_id = :id ORDER BY id"),
                {"id": requested_for_public_id},
            ).fetchall()
        ]


# --- The site's central-government answer (7C's line details) ---------------------------------------------------


def test_the_central_government_answer_is_kept_when_left_out_cleared_when_empty_and_in_the_event(wo) -> None:
    detail = _line_detail(wo, customer_line_reference="PO-1")
    assert detail["site_central_government"] is False
    detail = _line_detail(wo, site_central_government=True)
    assert detail["site_central_government"] is True
    assert _get_requirement(wo)["line"]["site_central_government"] is True
    detail = _line_detail(wo, site_central_government=None)
    assert detail["site_central_government"] is None
    with SessionLocal() as db:
        payload = db.execute(
            text(
                "SELECT event_payload_json FROM business_event WHERE event_name = 'WorkOrderLineDetailUpdated' "
                "AND record_public_id = :id ORDER BY id DESC LIMIT 1"
            ),
            {"id": wo["work_order_public_id"]},
        ).scalar_one()
    assert json.loads(payload)["site_central_government"] is None


# --- Finding machines (6.2) -------------------------------------------------------------------------------------


def test_the_finder_offers_only_machines_that_meet_the_requirement_with_todays_answer(wo, fleet) -> None:
    body = _candidates(wo)
    assert body["period_from"] == START.isoformat() and body["period_to"] == END.isoformat()
    assert body["site"]["state_code"] == "IN-MH" and body["site"]["central_government_site"] is False
    assert body["site"]["problem_code"] is None
    offered = {item["machine"]["asset_public_id"]: item for item in body["candidates"]}
    assert {fleet.ok, fleet.spare, fleet.warns, fleet.bare} <= set(offered)
    # Below 200 t, another type, and a type not known are not offered; the unknown and the smaller are counted.
    assert not {fleet.small, fleet.all_terrain, fleet.unknown} & set(offered)
    assert body["left_out"]["BELOW_REQUIREMENT"] >= 1 and body["left_out"]["TYPE_UNKNOWN"] >= 1
    assert offered[fleet.ok]["answer"]["overall_code"] == "ELIGIBLE"
    assert offered[fleet.warns]["answer"]["overall_code"] == "WARNING"
    assert offered[fleet.bare]["answer"]["overall_code"] == "BLOCKED"
    order = [item["machine"]["asset_public_id"] for item in body["candidates"] if item["machine"]["asset_public_id"] in offered]
    assert order.index(fleet.ok) < order.index(fleet.warns) < order.index(fleet.bare)
    # Nothing is stored by finding.
    assert _decision_rows(fleet.ok) == []


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"site_address_public_id": None}, "SITE_NOT_RECORDED"),
        ({"site_central_government": None}, "CENTRAL_NOT_ANSWERED"),
    ],
)
def test_the_finder_names_what_is_missing_about_the_site_and_gives_no_answer(wo, fleet, change, problem) -> None:
    _line_detail(wo, **change)
    body = _candidates(wo)
    assert body["site"]["problem_code"] == problem
    assert all(item["answer"] is None for item in body["candidates"])
    assert problem.split("_")[0].lower() in body["site"]["problem_message"].lower() or "site" in body["site"]["problem_message"]
    assert "line" in _detail(_allocate(wo, fleet.ok))


def test_a_site_state_the_platform_does_not_know_is_refused_asking_for_the_address_to_be_corrected(wo, fleet) -> None:
    site = _add_site(wo["account_public_id"], "Guj.")
    _line_detail(wo, site_address_public_id=site["public_id"])
    body = _candidates(wo)
    assert body["site"]["problem_code"] == "STATE_NOT_RECOGNISED"
    assert "'Guj.'" in _detail(_allocate(wo, fleet.ok))


# --- Allocating (6.3) -------------------------------------------------------------------------------------------


def test_allocating_holds_the_machine_on_a_stored_decision_and_the_requirement_follows(wo, fleet) -> None:
    response = _ok(_allocate(wo, fleet.ok), 201)
    held = response["assignment"]
    assert held["assignment_status_code"] == "HELD" and held["assignment_reference"].startswith("AL-")
    assert held["unit_number"] == 1 and held["machine"]["asset_public_id"] == fleet.ok
    assert held["allocated_machine_number"] == fleet.number("OK")
    assert held["decision"]["overall_code"] == "ELIGIBLE" and held["today"]["overall_code"] == "ELIGIBLE"
    assert held["compliance_state_code"] == "CLEAR"
    assert [trip["trip_number"] for trip in held["trips"]] == [1]
    assert held["trips"][0]["goes_on"] == START.isoformat()
    assert held["warnings"] == ["BILLING_CYCLE_NOT_STATED"]
    [decision] = _decision_rows(held["assignment_public_id"])
    assert decision["decision_public_id"] == held["decision"]["decision_public_id"]
    assert decision["requested_for_type"] == "resource_assignment"
    requirement = _get_requirement(wo)
    assert requirement["requirement_status_code"] == "PARTLY_FULFILLED"
    assert (requirement["units_covered"], requirement["units_remaining"]) == (1, 1)
    [event] = response["events"]
    assert event["event_name"] == "RESOURCE_ASSIGNMENT_HELD"
    assert fleet.number("OK") not in json.dumps(_events(held["assignment_public_id"]))
    changed = [item for item in _events(wo["requirement"]["requirement_public_id"]) if item["event_name"] == "ResourceRequirementFulfilmentChanged"]
    assert [(item["status_before"], item["status_after"]) for item in changed] == [("OPEN", "PARTLY_FULFILLED")]
    _ok(_allocate(wo, fleet.spare, unit=2), 201)
    requirement = _get_requirement(wo)
    assert requirement["requirement_status_code"] == "FULFILLED" and requirement["units_remaining"] == 0


def test_a_machine_is_never_held_twice_on_a_common_day_and_a_unit_never_filled_twice(wo, fleet) -> None:
    first = _allocated(wo, fleet.ok)
    message = _detail(_allocate(wo, fleet.ok, unit=2, planned_from=END - timedelta(days=3), planned_to=END + timedelta(days=0)), 409)
    assert first["assignment_reference"] in message and "Choose another machine" in message
    message = _detail(_allocate(wo, fleet.spare, unit=1, planned_from=END - timedelta(days=3)), 409)
    assert "Unit 1" in message
    # The finder shows the held machine busy, with where it is.
    busy = next(item for item in _candidates(wo, unit=2)["candidates"] if item["machine"]["asset_public_id"] == fleet.ok)
    assert busy["available"] is False and busy["conflicts"][0]["assignment_reference"] == first["assignment_reference"]


def test_a_machine_that_cannot_be_allocated_is_refused_and_nothing_is_stored(wo, fleet) -> None:
    message = _detail(_allocate(wo, fleet.bare))
    assert "cannot be allocated" in message and "is missing" in message
    assert _decision_rows(fleet.bare) == [] and _get_requirement(wo)["requirement_status_code"] == "OPEN"
    with SessionLocal() as db:
        assert db.execute(text("SELECT COUNT(*) FROM eligibility_decision WHERE equipment_asset_public_id = :id"), {"id": fleet.bare}).scalar_one() == 0


def test_a_warning_is_allocated_only_once_the_user_has_seen_it(wo, fleet) -> None:
    message = _detail(_allocate(wo, fleet.warns), 409)
    assert "only with a warning" in message and "I have seen these warnings" in message
    held = _allocated(wo, fleet.warns, accept_warnings=True)
    assert held["decision"]["overall_code"] == "WARNING" and held["compliance_state_code"] == "WARNING"


def test_needs_approval_is_refused_while_no_approval_can_be_given(wo, fleet) -> None:
    """Q2: a PBL rule whose lapse needs approval gives "needs approval"; nobody can approve yet, so it is refused."""
    rule = _ok(
        client.post(
            "/api/eligibility/rules",
            json={
                "create_request_key": str(uuid.uuid4()),
                "kind_code": "FITNESS",
                "class_code": "CRANE",
                "type_code": "CRAWLER",
                "applies_when_code": "ALWAYS",
                "jurisdiction_code": "IN-MH",
                "effective_from": TODAY.isoformat(),
                "renew_every_months": None,
                "basis_code": "PBL_RULE",
                "lapse_code": "OVERRIDE",
                "not_applicable_code": "NOT_ALLOWED",
                "not_applicable_max_months": None,
                "source": "Invented test rule needing approval.",
                "note": None,
            },
            headers=auth_headers(ADMIN),
        ),
        201,
    )
    try:
        message = _detail(_allocate(wo, fleet.ok))
        assert "cannot be allocated" in message and "needs an approval" in message
    finally:
        _ok(
            client.post(
                f"/api/eligibility/rules/{rule['rule']['rule_public_id']}/end",
                json={"effective_to": TODAY.isoformat(), "reason": "Test over."},
                headers=auth_headers(ADMIN),
            )
        )


@pytest.mark.parametrize(
    ("fields", "status", "message"),
    [
        ({"unit": 3}, 422, "unit 3 is not one of them"),
        ({"planned_from": START - timedelta(days=1)}, 422, "before"),
        ({"planned_to": END + timedelta(days=1)}, 422, "after"),
        ({"planned_from": START + timedelta(days=10), "planned_to": START + timedelta(days=9)}, 422, "before it starts"),
        ({"billing_cycle_code": "DAILY"}, 422, "Weekly or Monthly"),
        ({"notes": "   "}, 201, None),
    ],
)
def test_an_allocation_that_breaks_a_rule_is_refused(wo, fleet, fields, status, message) -> None:
    unit = fields.pop("unit", 1)
    response = _allocate(wo, fleet.ok, unit=unit, **fields)
    if message is None:
        assert _ok(response, status)["assignment"]["notes"] is None
    else:
        assert message in _detail(response, status)


def test_only_a_machine_that_meets_the_requirement_can_be_allocated(wo, fleet) -> None:
    assert "does not meet a capability" in _detail(_allocate(wo, fleet.small))
    assert "not of the type" in _detail(_allocate(wo, fleet.all_terrain))
    assert "type is not known" in _detail(_allocate(wo, fleet.unknown))
    assert "not a machine" in _detail(_allocate(wo, fleet.hook))
    assert _detail(_allocate(wo, str(uuid.uuid4())), 404) == "Machine not found."


def test_an_empty_end_means_until_the_requirement_ends(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok, planned_to=None)
    assert held["planned_to"] == END.isoformat()


def test_the_same_request_again_returns_the_first_allocation_and_another_use_of_its_key_is_refused(wo, fleet) -> None:
    key = str(uuid.uuid4())
    first = _ok(_allocate(wo, fleet.ok, key=key), 201)
    again = _ok(_allocate(wo, fleet.ok, key=key), 201)
    assert again["replayed"] is True and again["events"] == []
    assert again["assignment"]["assignment_public_id"] == first["assignment"]["assignment_public_id"]
    assert "already used" in _detail(_allocate(wo, fleet.spare, key=key), 409)


def test_setting_the_billing_cycle_needs_the_permission_to_change_billing_terms() -> None:
    """Admin and Operations hold both permissions today; a role allowed to allocate but not to change billing terms
    is refused the cycle - the rule the route applies."""
    payload = AssignmentCreate(
        create_request_key=str(uuid.uuid4()),
        requirement_public_id=uuid.uuid4(),
        unit_number=1,
        machine_public_id=uuid.uuid4(),
        planned_from=START,
        billing_cycle_code="MONTHLY",
    )
    with SessionLocal() as db, pytest.raises(AssignmentForbiddenError):
        assignment_service.create_assignment(db, payload=payload, user_public_id="someone", may_set_billing_cycle=False)


@pytest.mark.parametrize("username", NON_WRITE_ROLES)
def test_every_role_but_operations_and_admin_is_refused_every_write(wo, fleet, username) -> None:
    assert _allocate(wo, fleet.ok, username=username).status_code == 403


@pytest.mark.parametrize("username", READ_ROLES)
def test_every_role_that_reads_work_orders_reads_allocations(wo, fleet, username) -> None:
    held = _allocated(wo, fleet.ok)
    assert _get(held, username)["assignment_public_id"] == held["assignment_public_id"]
    listed = _ok(client.get(URL, params={"work_order_public_id": wo["work_order_public_id"]}, headers=auth_headers(username)))
    assert [item["assignment_public_id"] for item in listed] == [held["assignment_public_id"]]


# --- Replacing (6.6) ------------------------------------------------------------------------------------------


def test_a_replacement_ends_the_old_machine_the_day_before_and_keeps_both_on_the_history(wo, fleet) -> None:
    old = _allocated(wo, fleet.ok, billing_cycle_code="MONTHLY")
    replace_from = START + timedelta(days=10)
    response = _ok(
        _post(old, "replace", create_request_key=str(uuid.uuid4()), machine_public_id=fleet.spare, replace_from=replace_from, reason_code="BREAKDOWN"),
        201,
    )
    new, replaced = response["assignment"], response["replaced"]
    assert replaced["assignment_status_code"] == "REPLACED" and replaced["ended_on"] == (replace_from - timedelta(days=1)).isoformat()
    assert replaced["end_reason_code"] == "BREAKDOWN" and replaced["replaced_by"]["assignment_public_id"] == new["assignment_public_id"]
    assert new["replaces"]["assignment_public_id"] == old["assignment_public_id"]
    assert (new["unit_number"], new["planned_from"], new["planned_to"]) == (1, replace_from.isoformat(), END.isoformat())
    # The customer's invoice cycle for the position does not change with the machine.
    assert new["billing_cycle_code"] == "MONTHLY"
    assert [event["event_name"] for event in response["events"]] == ["RESOURCE_ASSIGNMENT_REPLACED", "RESOURCE_ASSIGNMENT_HELD"]
    history = _ok(client.get(URL, params={"work_order_public_id": wo["work_order_public_id"]}, headers=auth_headers("readonly1")))
    assert {item["assignment_public_id"]: item["assignment_status_code"] for item in history} == {
        new["assignment_public_id"]: "HELD",
        old["assignment_public_id"]: "REPLACED",
    }
    # The unit stays covered across the hand-over, and the old machine is free from the replacement's first day.
    assert _get_requirement(wo)["units_covered"] == 1
    _allocated(wo, fleet.ok, unit=2, planned_from=replace_from)


def test_a_replacement_before_the_job_starts_leaves_the_old_allocation_with_no_days(wo, fleet) -> None:
    old = _allocated(wo, fleet.ok)
    response = _ok(_post(old, "replace", create_request_key=str(uuid.uuid4()), machine_public_id=fleet.spare, replace_from=START, reason_code="PLANNING"), 201)
    assert response["replaced"]["effective_to"] == (START - timedelta(days=1)).isoformat()
    _allocated(wo, fleet.ok, unit=2)


@pytest.mark.parametrize(
    ("fields", "status", "message"),
    [
        ({"machine": "ok"}, 422, "cannot be the same machine"),
        ({"replace_from": START - timedelta(days=1)}, 422, "must start on a day of"),
        ({"machine": "bare"}, 422, "cannot be allocated"),
        ({"reason_code": "WHIM"}, 422, "Choose why"),
        ({"reason_code": "OTHER"}, 422, "Say what the other reason is"),
        ({"expected_assignment_version": 99}, 409, "Someone else changed this allocation"),
    ],
)
def test_a_replacement_that_breaks_a_rule_is_refused_and_changes_nothing(wo, fleet, fields, status, message) -> None:
    old = _allocated(wo, fleet.ok)
    machine = getattr(fleet, fields.pop("machine", "spare"))
    body = {"create_request_key": str(uuid.uuid4()), "machine_public_id": machine, "replace_from": START + timedelta(days=3), "reason_code": "BREAKDOWN", **fields}
    assert message in _detail(_post(old, "replace", **body), status)
    assert _get(old)["assignment_status_code"] == "HELD"


# --- Freeing (6.7) and changing dates (6.8) --------------------------------------------------------------------


def test_freeing_a_machine_that_never_goes_leaves_it_no_days_and_the_requirement_follows(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    freed = _ok(_post(held, "release", reason_code="NOT_NEEDED"))["assignment"]
    assert freed["assignment_status_code"] == "RELEASED" and freed["effective_to"] == (START - timedelta(days=1)).isoformat()
    assert freed["compliance_state_code"] is None and freed["warnings"] == []
    assert _get_requirement(wo)["requirement_status_code"] == "OPEN"
    _allocated(wo, fleet.ok, unit=2)
    assert "was freed" in _detail(_post(freed, "release", reason_code="NOT_NEEDED"))


def test_freeing_from_a_last_day_keeps_the_days_it_held(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    last = START + timedelta(days=9)
    freed = _ok(_post(held, "release", reason_code="MACHINE_UNAVAILABLE", last_day=last))["assignment"]
    assert freed["effective_to"] == last.isoformat()
    assert "is allocated to" in _detail(_allocate(wo, fleet.ok, unit=2, planned_from=last, planned_to=last + timedelta(days=1)), 409)
    _allocated(wo, fleet.ok, unit=2, planned_from=last + timedelta(days=1))
    after = _allocated(wo, fleet.spare, planned_from=last + timedelta(days=1))
    assert "must be a day of" in _detail(_post(after, "release", reason_code="NOT_NEEDED", last_day=END + timedelta(days=1)))
    # The freed machine's days still covered unit 1, and the next machine covers the rest: unit 1 is covered. Unit 2
    # starts only after the last day, so it is not.
    assert _get_requirement(wo)["units_covered"] == 1


@pytest.fixture
def started(monkeypatch) -> None:
    """The allocations' first day, START, has come (India date)."""
    monkeypatch.setattr(business_time, "india_today", lambda: START)


@pytest.mark.parametrize("reason", ["NOT_NEEDED", "MACHINE_UNAVAILABLE", "OTHER"])
def test_a_started_allocation_is_not_freed_without_a_last_day_unless_recorded_by_mistake(wo, fleet, started, reason) -> None:
    """Owner, 1 October 2026: once its first day has come, an allocation's days stay on the record."""
    held = _allocated(wo, fleet.ok)
    message = _detail(_post(held, "release", reason_code=reason, note="Customer postponed"))
    assert "give its last day on the job" in message and "recorded by mistake" in message
    assert _get(held)["assignment_status_code"] == "HELD"
    # A last day keeps the days it held.
    freed = _ok(_post(held, "release", reason_code=reason, note="Customer postponed", last_day=START))["assignment"]
    assert freed["effective_to"] == START.isoformat()


def test_a_started_allocation_recorded_by_mistake_is_freed_with_no_days(wo, fleet, started) -> None:
    held = _allocated(wo, fleet.ok)
    freed = _ok(_post(held, "release", reason_code="RECORDED_BY_MISTAKE"))["assignment"]
    assert freed["effective_to"] == (START - timedelta(days=1)).isoformat()
    assert freed["end_reason_code"] == "RECORDED_BY_MISTAKE"


def test_a_started_allocation_is_replaced_only_from_a_later_day(wo, fleet, started) -> None:
    old = _allocated(wo, fleet.ok)
    body = {"machine_public_id": fleet.spare, "reason_code": "BREAKDOWN"}
    message = _detail(_post(old, "replace", create_request_key=str(uuid.uuid4()), replace_from=START, **body))
    assert "must start after its first day" in message and "Recorded by mistake" in message
    assert _get(old)["assignment_status_code"] == "HELD"
    replaced = _ok(_post(old, "replace", create_request_key=str(uuid.uuid4()), replace_from=START + timedelta(days=1), **body), 201)["replaced"]
    assert replaced["effective_to"] == START.isoformat()


def test_a_started_allocations_replacement_finder_starts_after_its_first_day(wo, fleet, started) -> None:
    held = _allocated(wo, fleet.ok)
    found = _candidates(wo, replacing_assignment_public_id=held["assignment_public_id"])
    assert found["period_from"] == (START + timedelta(days=1)).isoformat()


def test_a_replacement_finder_never_offers_the_first_day_of_a_held_allocation_whose_end_has_passed(wo, fleet, monkeypatch) -> None:
    """Independent review of PR #81: still held after its last day, the allocation has started all the same, so the
    default is a day the server takes - here its last day - never its first."""
    held = _allocated(wo, fleet.ok, planned_to=START + timedelta(days=10))
    later = START + timedelta(days=20)
    monkeypatch.setattr(business_time, "india_today", lambda: later)
    found = _candidates(wo, replacing_assignment_public_id=held["assignment_public_id"])
    assert found["period_from"] == (START + timedelta(days=10)).isoformat()
    # The server takes that day.
    body = {"create_request_key": str(uuid.uuid4()), "machine_public_id": fleet.spare, "reason_code": "BREAKDOWN"}
    _ok(_post(held, "replace", replace_from=found["period_from"], **body), 201)


def test_a_started_allocations_first_day_cannot_change_but_its_last_day_can(wo, fleet, started) -> None:
    """Owner, 1 October 2026, applied to a date change (TB-1 finding TB1-306, 4 October 2026): moving the first day of
    a started allocation would drop days it held, as freeing or replacing from its first day would."""
    held = _allocated(wo, fleet.ok, planned_to=START + timedelta(days=20))
    for first in (START + timedelta(days=1), START - timedelta(days=1)):
        message = _detail(_put(held, "dates", planned_from=first, planned_to=START + timedelta(days=20)))
        assert "its first day cannot change" in message and "Recorded by mistake" in message
    unchanged = _get(held)
    assert unchanged["planned_from"] == START.isoformat() and unchanged["assignment_version"] == held["assignment_version"]
    moved = _ok(_put(held, "dates", planned_from=START, planned_to=START + timedelta(days=24)))["assignment"]
    assert moved["planned_from"] == START.isoformat() and moved["planned_to"] == (START + timedelta(days=24)).isoformat()


def test_changing_dates_checks_again_and_refuses_days_the_unit_is_filled(wo, fleet) -> None:
    first = _allocated(wo, fleet.ok, planned_to=START + timedelta(days=20))
    moved = _ok(_put(first, "dates", planned_from=START + timedelta(days=1), planned_to=START + timedelta(days=24)))["assignment"]
    assert moved["planned_from"] == (START + timedelta(days=1)).isoformat()
    assert moved["decision"]["decision_public_id"] != first["decision"]["decision_public_id"]
    assert len(_decision_rows(first["assignment_public_id"])) == 2
    _allocated(wo, fleet.spare, planned_from=START + timedelta(days=25))
    message = _detail(_put(moved, "dates", planned_from=START + timedelta(days=1), planned_to=START + timedelta(days=26)), 409)
    assert "Unit 1" in message


# --- Checking again (6.4) --------------------------------------------------------------------------------------


def test_a_lapse_shows_on_the_allocation_when_read_and_check_again_stores_it_without_freeing(wo, fleet) -> None:
    held = _allocated(wo, fleet.spare)
    certificates = _ok(client.get(f"/api/eligibility/assets/{fleet.spare}/certificates", headers=auth_headers(ADMIN)))["certificates"]
    exam = next(item for item in certificates if item["kind_code"] == "THOROUGH_EXAMINATION" and item["in_force"])
    _ok(client.post(f"/api/eligibility/certificates/{exam['certificate_public_id']}/withdraw", json={"reason": "Recorded by mistake"}, headers=auth_headers(ADMIN)))
    try:
        read = _get(held)
        assert read["today"]["overall_code"] == "BLOCKED" and read["compliance_state_code"] == "BLOCKED"
        assert "ANSWER_CHANGED" in read["warnings"]
        checked = _ok(_post(read, "check"))["assignment"]
        assert checked["assignment_status_code"] == "HELD" and checked["decision"]["overall_code"] == "BLOCKED"
        assert "ANSWER_CHANGED" not in checked["warnings"]
    finally:
        _recorded(fleet.spare, "THOROUGH_EXAMINATION")


def test_a_changed_site_answer_is_shown_until_checked_again(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    _line_detail(wo, site_central_government=True)
    read = _get(held)
    assert "SITE_CHANGED" in read["warnings"]
    checked = _ok(_post(read, "check"))["assignment"]
    assert checked["decision"]["central_government_site"] is True and "SITE_CHANGED" not in checked["warnings"]


def test_the_allocations_list_filters_those_starting_soon(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    soon = _ok(
        client.get(
            URL,
            params={"status_code": "HELD", "starts_from": TODAY.isoformat(), "starts_to": (TODAY + timedelta(days=15)).isoformat(), "limit": 200},
            headers=auth_headers("ops1"),
        )
    )
    assert held["assignment_public_id"] in {item["assignment_public_id"] for item in soon}
    later = _ok(
        client.get(
            URL,
            params={"starts_from": (START + timedelta(days=1)).isoformat(), "requirement_public_id": wo["requirement"]["requirement_public_id"]},
            headers=auth_headers("ops1"),
        )
    )
    assert later == []
    assert "Held, Replaced or Freed" in _detail(client.get(URL, params={"status_code": "GONE"}, headers=auth_headers("ops1")))


# --- The billing cycle (6.9) -----------------------------------------------------------------------------------


def test_the_billing_cycle_is_set_by_those_who_change_billing_terms_and_the_same_value_records_nothing(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    weekly = _ok(_put(held, "billing-cycle", username="sales1", billing_cycle_code="weekly"))
    assert weekly["assignment"]["billing_cycle_code"] == "WEEKLY" and weekly["events"][0]["event_name"] == "RESOURCE_ASSIGNMENT_BILLING_CYCLE_SET"
    assert "BILLING_CYCLE_NOT_STATED" not in weekly["assignment"]["warnings"]
    same = _ok(_put(weekly["assignment"], "billing-cycle", billing_cycle_code="WEEKLY"))
    assert same["events"] == [] and same["assignment"]["assignment_version"] == weekly["assignment"]["assignment_version"]
    cleared = _ok(_put(weekly["assignment"], "billing-cycle", billing_cycle_code=None))["assignment"]
    assert cleared["billing_cycle_code"] is None
    for username in ("finance1", "readonly1"):
        assert _put(cleared, "billing-cycle", username=username, billing_cycle_code="MONTHLY").status_code == 403


# --- The requirement and its machines (6.5) ---------------------------------------------------------------------


def test_cancelling_a_requirement_frees_its_machines_in_the_same_transaction(wo, fleet) -> None:
    first = _allocated(wo, fleet.ok)
    _allocated(wo, fleet.spare, unit=2)
    requirement = _get_requirement(wo)
    cancelled = _ok(
        client.post(
            f"{REQUIREMENTS}/{requirement['requirement_public_id']}/cancel",
            json={"expected_requirement_version": requirement["requirement_version"], "cancellation_reason": "Customer cancelled"},
            headers=auth_headers("ops1"),
        )
    )
    assert cancelled["machines_freed"] == 2 and cancelled["resource_requirement"]["requirement_status_code"] == "CANCELLED"
    freed = _get(first)
    assert freed["assignment_status_code"] == "RELEASED" and freed["end_reason_code"] == "REQUIREMENT_CANCELLED"
    assert freed["effective_to"] == (START - timedelta(days=1)).isoformat()
    assert "cancelled" in _detail(_allocate(wo, fleet.ok))


def test_without_the_assignment_port_a_requirement_is_not_read(wo, monkeypatch) -> None:
    """Fail closed: never read as having no machines merely because Assignment was not loaded."""
    monkeypatch.setattr(ports, "_registered", [])
    with pytest.raises(RuntimeError, match="not loaded"):
        client.get(f"{REQUIREMENTS}/{wo['requirement']['requirement_public_id']}", headers=auth_headers("ops1"))


def test_a_requirement_change_is_never_refused_and_an_allocation_that_no_longer_fits_says_so(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok, unit=2)
    requirement = _get_requirement(wo)
    body = {
        "expected_requirement_version": requirement["requirement_version"],
        "units_required": 1,
        "required_from": requirement["required_from"],
        "required_to": requirement["required_to"],
        "crew_operators_required": 1,
        "crew_helpers_required": 1,
        "priority_code": "NORMAL",
        "items": [
            {
                "equipment_class_code": "CRANE",
                "equipment_type_code": "CRAWLER",
                "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "300"}],
            }
        ],
    }
    changed = _ok(client.put(f"{REQUIREMENTS}/{requirement['requirement_public_id']}", json=body, headers=auth_headers("ops1")))["resource_requirement"]
    # Unit 2 is above the one now required, so it counts for nothing.
    assert changed["requirement_status_code"] == "OPEN" and changed["units_covered"] == 0
    warnings = _get(held)["warnings"]
    assert "UNIT_NOT_REQUIRED" in warnings and "NO_LONGER_MATCHES" in warnings


def test_the_planning_list_shows_what_still_needs_machines(wo, fleet) -> None:
    params = {"work_order_public_id": wo["work_order_public_id"], "status_code": "NEEDS_MACHINES"}
    assert len(_ok(client.get(REQUIREMENTS, params=params, headers=auth_headers("ops1")))) == 1
    _allocated(wo, fleet.ok)
    _allocated(wo, fleet.spare, unit=2)
    assert _ok(client.get(REQUIREMENTS, params=params, headers=auth_headers("ops1"))) == []
    fulfilled = _ok(client.get(REQUIREMENTS, params={**params, "status_code": "FULFILLED"}, headers=auth_headers("ops1")))
    assert [item["units_remaining"] for item in fulfilled] == [0]


# --- The kit going to site (6.10) ----------------------------------------------------------------------------


def _kit_options(assignment: dict, trip: int = 1) -> dict:
    return _ok(client.get(f"{URL}/{assignment['assignment_public_id']}/kit-options", params={"trip_number": trip}, headers=auth_headers("readonly1")))


def _add_kit(assignment: dict, pieces: list[tuple[str, int]], *, trip: int = 1, key: str | None = None, **fields):
    body = {
        "create_request_key": key or str(uuid.uuid4()),
        "trip_number": trip,
        "pieces": [{"piece_public_id": piece, "quantity": quantity} for piece, quantity in pieces],
        **fields,
    }
    return _post(assignment, "kit", **body)


def test_kit_is_picked_from_the_kit_held_for_the_machines_model_each_piece_checked(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    options = {item["piece"]["asset_public_id"]: item for item in _kit_options(held)["pieces"]}
    assert {fleet.hook, fleet.sling, fleet.counterweight, fleet.insert} <= set(options)
    assert options[fleet.counterweight]["quantity_free"] == 4
    assert options[fleet.hook]["answer"]["overall_code"] == "ELIGIBLE" and options[fleet.sling]["answer"]["overall_code"] == "BLOCKED"
    listed = _ok(_add_kit(held, [(fleet.hook, 1), (fleet.counterweight, 3), (fleet.insert, 1)]), 201)
    kit = listed["assignment"]["trips"][0]["kit"]
    assert [(line["piece_public_id"], line["quantity"]) for line in kit] == [(fleet.hook, 1), (fleet.counterweight, 3), (fleet.insert, 1)]
    assert all(line["decision"]["decision_public_id"] and line["fits_machine"] for line in kit)
    assert listed["assignment"]["kit_pieces_listed"] == 5
    assert listed["events"][0]["event_name"] == "RESOURCE_ASSIGNMENT_KIT_LISTED"
    assert _decision_rows(kit[0]["kit_line_public_id"])[0]["requested_for_type"] == "resource_assignment_kit"
    # The sling's examination is missing: it cannot go.
    assert "cannot be allocated" in _detail(_add_kit(listed["assignment"], [(fleet.sling, 1)]))


def test_a_piece_is_never_on_two_jobs_at_once_and_a_counted_set_never_over_its_count(wo, fleet) -> None:
    first = _allocated(wo, fleet.ok)
    _ok(_add_kit(first, [(fleet.hook, 1), (fleet.counterweight, 3)]), 201)
    second = _allocated(wo, fleet.spare, unit=2)
    assert "is allocated to" in _detail(_add_kit(second, [(fleet.hook, 1)]), 409)
    assert "Only 1 of" in _detail(_add_kit(second, [(fleet.counterweight, 2)]), 409)
    options = {item["piece"]["asset_public_id"]: item for item in _kit_options(second)["pieces"]}
    assert options[fleet.hook]["available"] is False and options[fleet.counterweight]["quantity_free"] == 1
    _ok(_add_kit(second, [(fleet.counterweight, 1)]), 201)


def test_a_counted_set_cannot_shrink_below_what_its_trips_list_from_today(wo, fleet) -> None:
    """TB-1 TB1-307 (4 October 2026): retiring pieces of a counted set is refused, changing nothing, when fewer would
    remain than its trips list at once from today on; retiring fewer is allowed. A set of its own, so the shared one
    keeps its four."""
    weights = fleet._kit(fleet.weight_model, 4)
    held = _allocated(wo, fleet.ok)
    _ok(_add_kit(held, [(weights, 3)]), 201)

    def machine() -> dict:
        return _ok(client.get(f"{EQUIPMENT}/machines/{weights}", headers=auth_headers(ADMIN)))

    def retire(count: int, version: int):
        body = {"expected_asset_version": version, "reason_code": "SCRAPPED", "retired_on": TODAY.isoformat(), "note": None, "count": count}
        return client.post(f"{EQUIPMENT}/machines/{weights}/retire", json=body, headers=auth_headers(ADMIN))

    before = machine()
    message = _detail(retire(2, before["asset_version"]))
    assert "Trips list 3 of this set at once from today" in message and "cannot go down to 2" in message
    assert held["assignment_reference"] in message
    after = machine()
    assert (after["quantity"], after["asset_version"], after["asset_status_code"]) == (4, before["asset_version"], "ACTIVE")
    shrunk = _ok(retire(1, before["asset_version"]))
    assert shrunk["machine"]["quantity"] == 3 and shrunk["machine"]["asset_status_code"] == "ACTIVE"


def test_retiring_kit_takes_the_allocation_lock_before_the_equipment_lock(fleet) -> None:
    """TB-1 TB1-307: retirement takes Resource Assignments' lock, then the Equipment Reference's - the order Eligibility's
    "seen" marks take - so the two cannot deadlock. While another transaction holds Resource Assignments' lock, a
    retirement waits for it holding nothing of the Equipment Reference's, so a third transaction can still take that."""
    weights = fleet._kit(fleet.weight_model, 2)
    version = _ok(client.get(f"{EQUIPMENT}/machines/{weights}", headers=auth_headers(ADMIN)))["asset_version"]
    body = {"expected_asset_version": version, "reason_code": "SCRAPPED", "retired_on": TODAY.isoformat(), "note": None, "count": 1}
    result: dict[str, Any] = {}
    holder = SessionLocal()
    try:
        take_lock(holder)
        worker = threading.Thread(
            target=lambda: result.setdefault(
                "response", client.post(f"{EQUIPMENT}/machines/{weights}/retire", json=body, headers=auth_headers(ADMIN))
            )
        )
        worker.start()
        worker.join(timeout=3)
        assert worker.is_alive(), "the retirement did not wait for Resource Assignments' lock"
        with SessionLocal() as probe:
            # Refused after three seconds if the waiting retirement held the Equipment Reference's lock.
            probe.execute(text("SET LOCAL lock_timeout = '3s'"))
            hold_equipment_writes(probe)
            probe.rollback()
        holder.rollback()
    finally:
        holder.close()
    worker.join(timeout=60)
    assert result["response"].status_code == 200, result["response"].text


@pytest.mark.parametrize(
    ("pieces", "status", "message"),
    [
        ([("hook", 2)], 422, "is one piece"),
        ([("hook", 1), ("hook", 1)], 422, "listed twice"),
        ([("counterweight", 5)], 409, "Only 4 of"),
        ([("small", 1)], 422, "cannot go with this machine"),
    ],
)
def test_kit_that_breaks_a_rule_is_refused(wo, fleet, pieces, status, message) -> None:
    held = _allocated(wo, fleet.ok)
    assert message in _detail(_add_kit(held, [(getattr(fleet, name), quantity) for name, quantity in pieces]), status)


def test_a_later_trip_goes_on_a_day_of_the_allocation_and_its_kit_is_busy_from_then(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    assert "A Trip (Own Load) goes on a day of" in _detail(_post(held, "trips", goes_on=END + timedelta(days=1)), 422)
    trip_day = START + timedelta(days=20)
    with_trip = _ok(_post(held, "trips", goes_on=trip_day, note="Extra inserts for the second lift"), 201)["assignment"]
    assert [(trip["trip_number"], trip["goes_on"]) for trip in with_trip["trips"]] == [(1, START.isoformat()), (2, trip_day.isoformat())]
    listed = _ok(_add_kit(with_trip, [(fleet.insert, 1)], trip=2), 201)["assignment"]
    line = listed["trips"][1]["kit"][0]
    assert (line["busy_from"], line["busy_to"]) == (trip_day.isoformat(), END.isoformat())
    # Moving the allocation's start past a trip that carries kit is refused.
    assert "Trip (Own Load) 2 goes on" in _detail(_put(listed, "dates", planned_from=trip_day + timedelta(days=1), planned_to=END))


def test_a_removed_piece_is_free_again_and_removing_it_twice_changes_nothing(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    listed = _ok(_add_kit(held, [(fleet.hook, 1)]), 201)["assignment"]
    line = listed["trips"][0]["kit"][0]
    remove_url = f"{URL}/{held['assignment_public_id']}/kit/{line['kit_line_public_id']}/remove"
    removed = _ok(client.post(remove_url, json={"expected_assignment_version": listed["assignment_version"]}, headers=auth_headers("ops1")))
    assert removed["assignment"]["trips"][0]["kit"][0]["line_status_code"] == "REMOVED" and removed["assignment"]["kit_pieces_listed"] == 0
    again = _ok(client.post(remove_url, json={"expected_assignment_version": removed["assignment"]["assignment_version"]}, headers=auth_headers("ops1")))
    assert again["events"] == []
    second = _allocated(wo, fleet.spare, unit=2)
    _ok(_add_kit(second, [(fleet.hook, 1)]), 201)


def test_a_replacement_cuts_the_old_machines_kit_so_the_pieces_can_go_with_the_new_one(wo, fleet) -> None:
    old = _allocated(wo, fleet.ok)
    listed = _ok(_add_kit(old, [(fleet.hook, 1)]), 201)["assignment"]
    replace_from = START + timedelta(days=10)
    new = _ok(
        _post(listed, "replace", create_request_key=str(uuid.uuid4()), machine_public_id=fleet.spare, replace_from=replace_from, reason_code="BREAKDOWN"),
        201,
    )["assignment"]
    old_line = _get(old)["trips"][0]["kit"][0]
    assert old_line["busy_to"] == (replace_from - timedelta(days=1)).isoformat()
    _ok(_add_kit(new, [(fleet.hook, 1)]), 201)


# --- Independent review, round 1 ---------------------------------------------------------------------------------


def _close(work_order: dict) -> None:
    with SessionLocal() as db:
        db.execute(
            text("UPDATE crm_work_order SET work_order_status_code = 'CLOSED' WHERE work_order_public_id = :id"),
            {"id": work_order["work_order_public_id"]},
        )
        db.commit()


def _needs_machines(work_order: dict) -> list[str]:
    params = {"work_order_public_id": work_order["work_order_public_id"], "status_code": "NEEDS_MACHINES"}
    return [item["requirement_public_id"] for item in _ok(client.get(REQUIREMENTS, params=params, headers=auth_headers("ops1")))]


def test_a_requirement_without_its_own_end_follows_the_contract_and_line_ends_as_they_move(wo, fleet) -> None:
    """8A-R1-001: the stored status is worked out again when the end a requirement runs to moves."""
    _ok(_save_period(wo, contract_start_date=TODAY.isoformat(), contract_end_date=END.isoformat()))
    record = {**wo, "requirement": _requirement(wo, units=1, end=None)}
    _allocated(record, fleet.ok, planned_to=None)
    assert _get_requirement(record)["requirement_status_code"] == "FULFILLED"

    _ok(_save_period(wo, expected_period_version=1, contract_start_date=TODAY.isoformat(), contract_end_date=(END + timedelta(days=10)).isoformat()))
    later = _get_requirement(record)
    assert (later["requirement_status_code"], later["units_covered"], later["requirement_version"]) == ("PARTLY_FULFILLED", 0, 1)
    assert record["requirement"]["requirement_public_id"] in _needs_machines(record)
    changed = [event for event in _events(record["requirement"]["requirement_public_id"]) if event["event_name"] == "ResourceRequirementFulfilmentChanged"]
    assert (changed[-1]["status_before"], changed[-1]["status_after"]) == ("FULFILLED", "PARTLY_FULFILLED")

    _ok(_save_period(wo, expected_period_version=2, contract_start_date=TODAY.isoformat(), contract_end_date=END.isoformat()))
    assert _get_requirement(record)["requirement_status_code"] == "FULFILLED"
    assert record["requirement"]["requirement_public_id"] not in _needs_machines(record)

    extension = _ok(_extend(wo, new_end_date=(END + timedelta(days=20)).isoformat(), received_date=TODAY.isoformat()), 201)
    assert _get_requirement(record)["requirement_status_code"] == "PARTLY_FULFILLED"
    # The line's own end, earlier than the contract's, is the one the requirement runs to.
    _line_detail(wo, line_start_date=TODAY.isoformat(), line_end_date=END.isoformat())
    assert _get_requirement(record)["requirement_status_code"] == "FULFILLED"
    _line_detail(wo, line_start_date=None, line_end_date=None)
    assert _get_requirement(record)["requirement_status_code"] == "PARTLY_FULFILLED"
    extension_id = extension["contract_period"]["extensions"][-1]["extension_public_id"]
    _ok(_remove_extension(wo, extension_id))
    assert _get_requirement(record)["requirement_status_code"] == "FULFILLED"


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ({"billing_cycle_code": "MONTHLY", "notes": "A note"}, {"billing_cycle_code": "WEEKLY", "notes": "A note"}),
        ({"billing_cycle_code": "MONTHLY", "notes": "A note"}, {"notes": "A note"}),
        ({"billing_cycle_code": "MONTHLY", "notes": "A note"}, {"billing_cycle_code": "MONTHLY", "notes": "Another note"}),
        ({}, {"accept_warnings": True}),
        ({}, {"planned_to": END - timedelta(days=1)}),
    ],
)
def test_a_request_key_replays_only_the_same_request(wo, fleet, first, second) -> None:
    """8A-R1-002: any field sent differently - or left out where it was sent - is another use of the key."""
    key = str(uuid.uuid4())
    made = _ok(_allocate(wo, fleet.ok, key=key, **first), 201)
    again = _ok(_allocate(wo, fleet.ok, key=key, **first), 201)
    assert again["replayed"] is True and again["assignment"]["assignment_public_id"] == made["assignment"]["assignment_public_id"]
    assert "already used" in _detail(_allocate(wo, fleet.ok, key=key, **second), 409)


def test_a_replacement_or_kit_key_replays_only_the_same_request(wo, fleet) -> None:
    old = _allocated(wo, fleet.ok)
    body = {"create_request_key": str(uuid.uuid4()), "machine_public_id": fleet.spare, "replace_from": START + timedelta(days=3), "reason_code": "BREAKDOWN"}
    new = _ok(_post(old, "replace", **body), 201)["assignment"]
    assert _ok(_post(old, "replace", **body), 201)["replayed"] is True
    for changed in ({"reason_code": "PLANNING"}, {"note": "Crane went down"}, {"planned_to": END - timedelta(days=1)}, {"billing_cycle_code": "WEEKLY"}, {"accept_warnings": True}):
        assert "already used" in _detail(_post(old, "replace", **{**body, **changed}), 409)
    # The replacement's key cannot make an allocation either.
    assert "already used" in _detail(_allocate(wo, fleet.ok, key=body["create_request_key"]), 409)

    key = str(uuid.uuid4())
    _ok(_add_kit(new, [(fleet.hook, 1)], key=key), 201)
    assert _ok(_add_kit(new, [(fleet.hook, 1)], key=key), 201)["replayed"] is True
    assert "already used" in _detail(_add_kit(new, [(fleet.hook, 1)], key=key, accept_warnings=True), 409)
    assert "already used" in _detail(_add_kit(new, [(fleet.counterweight, 2)], key=key), 409)


def test_a_closed_work_order_refuses_every_write_on_its_allocations(wo, fleet) -> None:
    """8A-R1-003: every write, one that would change nothing included."""
    held = _ok(_add_kit(_allocated(wo, fleet.ok, billing_cycle_code="MONTHLY"), [(fleet.hook, 1)]), 201)["assignment"]
    line = held["trips"][0]["kit"][0]
    _close(wo)
    attempts = [
        _post(held, "check"),
        _put(held, "billing-cycle", billing_cycle_code="MONTHLY"),
        _put(held, "billing-cycle", billing_cycle_code="WEEKLY"),
        _post(held, "trips", goes_on=START + timedelta(days=5)),
        _put(held, "trips/1/note", note="Crawlers"),
        _add_kit(held, [(fleet.counterweight, 1)]),
        _post(held, f"kit/{line['kit_line_public_id']}/remove"),
        _put(held, "dates", planned_from=START, planned_to=END - timedelta(days=1)),
        _post(held, "release", reason_code="NOT_NEEDED"),
        _post(held, "replace", create_request_key=str(uuid.uuid4()), machine_public_id=fleet.spare, replace_from=START + timedelta(days=3), reason_code="BREAKDOWN"),
        _allocate(wo, fleet.spare, unit=2),
    ]
    for response in attempts:
        assert "This Work Order is closed" in _detail(response)
    assert _get(held)["assignment_version"] == held["assignment_version"]


def test_a_date_change_keeps_every_later_trip_within_the_allocation_with_kit_or_without(wo, fleet) -> None:
    """8A-R1-004."""
    held = _allocated(wo, fleet.ok)
    with_trip = _ok(_post(held, "trips", goes_on=START + timedelta(days=20)), 201)["assignment"]
    message = _detail(_put(with_trip, "dates", planned_from=START, planned_to=START + timedelta(days=10)))
    assert "Trip (Own Load) 2 goes on" in message and "outside the new" in message
    assert _get(with_trip)["planned_to"] == END.isoformat()
    # Freed before trip 2's day: kit options for it are refused clearly, never read as an inverted range.
    freed = _ok(_post(with_trip, "release", last_day=START + timedelta(days=10), reason_code="NOT_NEEDED"))["assignment"]
    response = client.get(f"{URL}/{freed['assignment_public_id']}/kit-options", params={"trip_number": 2}, headers=auth_headers("readonly1"))
    assert "has ended" in _detail(response)
    # The kit window itself refuses a trip after the allocation's last day, whatever calls it.
    with pytest.raises(AssignmentValidationError, match="no kit can be listed on it"):
        kit_window(
            {"planned_from": START, "planned_to": END, "ended_on": START + timedelta(days=10), "assignment_reference": "AL-1"},
            {"trip_number": 2, "goes_on": START + timedelta(days=20)},
        )


def test_lists_judge_an_allocation_by_its_listed_kit_as_the_page_does(wo, fleet) -> None:
    """8A-R1-005: a blocked piece of kit makes the allocation blocked in every list, not only on its page."""
    held = _ok(_add_kit(_allocated(wo, fleet.ok), [(fleet.hook, 1)]), 201)["assignment"]
    certificates = _ok(client.get(f"/api/eligibility/assets/{fleet.hook}/certificates", headers=auth_headers(ADMIN)))["certificates"]
    exam = next(item for item in certificates if item["kind_code"] == "THOROUGH_EXAMINATION" and item["in_force"])
    _ok(client.post(f"/api/eligibility/certificates/{exam['certificate_public_id']}/withdraw", json={"reason": "Recorded by mistake"}, headers=auth_headers(ADMIN)))
    try:
        assert _get(held)["compliance_state_code"] == "BLOCKED"
        for params in (
            {"work_order_public_id": wo["work_order_public_id"]},
            {"machine_public_id": fleet.ok},
            {"requirement_public_id": wo["requirement"]["requirement_public_id"], "status_code": "HELD"},
        ):
            listed = _ok(client.get(URL, params=params, headers=auth_headers("readonly1")))
            [row] = [item for item in listed if item["assignment_public_id"] == held["assignment_public_id"]]
            assert (row["today"]["overall_code"], row["compliance_state_code"]) == ("ELIGIBLE", "BLOCKED")
    finally:
        _recorded(fleet.hook, "THOROUGH_EXAMINATION")


# --- Independent review, round 2 ---------------------------------------------------------------------------------


def test_a_request_replayed_after_the_work_order_closes_is_refused(wo, fleet) -> None:
    """8A-R2-001: the closed Work Order is checked before a replay, as before any write."""
    key = str(uuid.uuid4())
    held = _ok(_allocate(wo, fleet.ok, key=key), 201)["assignment"]
    replace = {"create_request_key": str(uuid.uuid4()), "machine_public_id": fleet.spare, "replace_from": START + timedelta(days=3), "reason_code": "BREAKDOWN"}
    new = _ok(_post(held, "replace", **replace), 201)["assignment"]
    kit_key = str(uuid.uuid4())
    _ok(_add_kit(new, [(fleet.hook, 1)], key=kit_key), 201)
    _close(wo)
    for response in (_allocate(wo, fleet.ok, key=key), _post(held, "replace", **replace), _add_kit(new, [(fleet.hook, 1)], key=kit_key)):
        assert "This Work Order is closed" in _detail(response)


def test_an_allocation_write_waits_for_a_work_order_change_and_sees_a_closure(wo, fleet) -> None:
    """8A-R2-001: every write takes the Work Order's row, shared, first. A change holding the row's update lock - a
    closure here - makes the write wait, and the write then sees it."""
    held = _allocated(wo, fleet.ok)
    assert "This Work Order is closed" in _detail(_while_the_work_order_closes(wo, lambda: _post(held, "check")))
    assert _get(held)["assignment_version"] == held["assignment_version"]


def test_a_request_key_is_one_request_across_allocating_replacing_and_listing_kit(wo, fleet) -> None:
    """8A-R2-002: a key made by one kind of request is refused by the others, both ways, and the database holds each
    key once across the three."""
    key = str(uuid.uuid4())
    held = _ok(_allocate(wo, fleet.ok, key=key), 201)["assignment"]
    assert "already used" in _detail(_add_kit(held, [(fleet.hook, 1)], key=key), 409)
    kit_key = str(uuid.uuid4())
    listed = _ok(_add_kit(held, [(fleet.hook, 1)], key=kit_key), 201)["assignment"]
    assert "already used" in _detail(_allocate(wo, fleet.spare, unit=2, key=kit_key), 409)
    replace = {"create_request_key": kit_key, "machine_public_id": fleet.spare, "replace_from": START + timedelta(days=3), "reason_code": "BREAKDOWN"}
    assert "already used" in _detail(_post(listed, "replace", **replace), 409)
    with pytest.raises(IntegrityError, match="uq_resource_assignment_request_key"):
        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    INSERT INTO resource_assignment_request (
                        create_request_key, request_kind_code, resource_requirement_public_id, request_fingerprint, created_by
                    )
                    SELECT create_request_key, 'ALLOCATE', resource_requirement_public_id, request_fingerprint, created_by
                    FROM resource_assignment_request WHERE create_request_key = :key
                    """
                ),
                {"key": kit_key},
            )
            db.commit()


def test_a_requirement_edit_that_moves_its_status_records_the_move_once(wo, fleet) -> None:
    """8A-R2-003: the move is ResourceRequirementFulfilmentChanged's; the edit's own event moves nothing."""
    record = {**wo, "requirement": _requirement(wo, units=1)}
    _allocated(record, fleet.ok)
    requirement = _get_requirement(record)
    assert requirement["requirement_status_code"] == "FULFILLED"
    body = {
        "expected_requirement_version": requirement["requirement_version"],
        "units_required": 2,
        "required_from": requirement["required_from"],
        "required_to": requirement["required_to"],
        "crew_operators_required": 1,
        "crew_helpers_required": 1,
        "priority_code": "NORMAL",
        "items": [
            {
                "equipment_class_code": "CRANE",
                "equipment_type_code": "CRAWLER",
                "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "200"}],
            }
        ],
    }
    before = len(_events(requirement["requirement_public_id"]))
    _ok(client.put(f"{REQUIREMENTS}/{requirement['requirement_public_id']}", json=body, headers=auth_headers("ops1")))
    recorded = [(event["event_name"], event["status_before"], event["status_after"]) for event in _events(requirement["requirement_public_id"])[before:]]
    assert recorded == [
        ("ResourceRequirementFulfilmentChanged", "FULFILLED", "PARTLY_FULFILLED"),
        ("ResourceRequirementUpdated", "PARTLY_FULFILLED", "PARTLY_FULFILLED"),
    ]


def test_the_database_refuses_a_kit_line_on_another_allocations_trip(wo, fleet) -> None:
    """8A-R2-004: a kit line's trip is a trip of its own allocation (a composite foreign key)."""
    first = _ok(_add_kit(_allocated(wo, fleet.ok), [(fleet.hook, 1)]), 201)["assignment"]
    second = _allocated(wo, fleet.spare, unit=2)
    line = first["trips"][0]["kit"][0]
    with pytest.raises(IntegrityError, match="fk_resource_assignment_kit_trip"):
        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    UPDATE resource_assignment_kit SET resource_assignment_trip_id = (
                        SELECT t.id FROM resource_assignment_trip t INNER JOIN resource_assignment a ON a.id = t.resource_assignment_id
                        WHERE a.assignment_public_id = :other AND t.trip_number = 1
                    )
                    WHERE kit_line_public_id = :line
                    """
                ),
                {"other": second["assignment_public_id"], "line": line["kit_line_public_id"]},
            )
            db.commit()


# --- Independent review, round 3 ---------------------------------------------------------------------------------


def _requirement_body(requirement: dict, **changes) -> dict:
    body = {
        "expected_requirement_version": requirement["requirement_version"],
        "units_required": requirement["units_required"],
        "required_from": requirement["required_from"],
        "required_to": requirement["required_to"],
        "crew_operators_required": 1,
        "crew_helpers_required": 1,
        "priority_code": "NORMAL",
        "items": [
            {
                "equipment_class_code": "CRANE",
                "equipment_type_code": "CRAWLER",
                "capabilities": [{"capability_code": "RATED_CAPACITY", "minimum_value": "200"}],
            }
        ],
    }
    body.update(changes)
    return body


def _while_the_work_order_closes(work_order: dict, write) -> object:
    """Run `write` while another transaction holds the Work Order's row and closes it: the write must wait for the
    closure's commit, then see it."""
    return _while_the_work_order_changes(
        work_order, ["UPDATE crm_work_order SET work_order_status_code = 'CLOSED' WHERE work_order_public_id = :id"], write
    )


def _while_the_work_order_changes(work_order: dict, statements: list[str], write, **params) -> object:
    """Run `write` while another transaction holds the Work Order's row - as every Work Order write does - and makes a
    change: the write must wait for the change's commit, then see it."""
    result: dict = {}
    with SessionLocal() as closing:
        closing.execute(
            text("SELECT id FROM crm_work_order WHERE work_order_public_id = :id FOR UPDATE"),
            {"id": work_order["work_order_public_id"]},
        )
        for statement in statements:
            closing.execute(text(statement), {"id": work_order["work_order_public_id"], **params})
        worker = threading.Thread(target=lambda: result.setdefault("response", write()))
        worker.start()
        worker.join(timeout=3)
        assert worker.is_alive(), "the write did not wait for the Work Order's row"
        closing.commit()
    worker.join(timeout=60)
    return result["response"]


def test_a_requirement_cancellation_waits_for_a_work_order_closure_and_frees_nothing(wo, fleet) -> None:
    """8A-R3-001: cancelling or changing a requirement takes the Work Order's row first too, so neither lands after a
    closure - a cancellation would otherwise free machines on a closed Work Order."""
    held = _allocated(wo, fleet.ok)
    requirement = _get_requirement(wo)
    url = f"{REQUIREMENTS}/{requirement['requirement_public_id']}"
    cancelled = _while_the_work_order_closes(
        wo,
        lambda: client.post(
            f"{url}/cancel",
            json={"expected_requirement_version": requirement["requirement_version"], "cancellation_reason": "Not needed"},
            headers=auth_headers("ops1"),
        ),
    )
    assert "This Work Order is closed" in _detail(cancelled)
    assert _get(held)["assignment_status_code"] == "HELD"
    assert _get_requirement(wo)["requirement_status_code"] != "CANCELLED"


def test_a_requirement_change_waits_for_a_work_order_closure(wo, fleet) -> None:
    requirement = _get_requirement(wo)
    changed = _while_the_work_order_closes(
        wo, lambda: client.put(f"{REQUIREMENTS}/{requirement['requirement_public_id']}", json=_requirement_body(requirement, units_required=3), headers=auth_headers("ops1"))
    )
    assert "This Work Order is closed" in _detail(changed)
    assert _get_requirement(wo)["units_required"] == requirement["units_required"]


def test_the_billing_cycle_waits_for_a_work_order_closure(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    response = _while_the_work_order_closes(wo, lambda: _put(held, "billing-cycle", billing_cycle_code="WEEKLY"))
    assert "This Work Order is closed" in _detail(response)


def test_a_replacements_finder_defaults_to_the_replaced_allocations_own_days(wo, fleet) -> None:
    """8A-R3-003: not the requirement's period, which would start before the allocation or run past its end."""
    held = _allocated(wo, fleet.ok, planned_from=START + timedelta(days=5), planned_to=END - timedelta(days=10))
    found = _candidates(wo, replacing_assignment_public_id=held["assignment_public_id"])
    assert (found["period_from"], found["period_to"]) == ((START + timedelta(days=5)).isoformat(), (END - timedelta(days=10)).isoformat())
    # Its own days do not count against the unit.
    assert found["unit_conflicts"] == []


def test_the_database_refuses_a_kit_line_that_misstates_its_pieces_tracking(wo, fleet) -> None:
    """8A-R3-005: a piece tracked one by one cannot be written as a counted set to slip past the exclusion
    constraint."""
    held = _ok(_add_kit(_allocated(wo, fleet.ok), [(fleet.hook, 1)]), 201)["assignment"]
    line = held["trips"][0]["kit"][0]
    with pytest.raises(IntegrityError, match="A kit line carries its piece's tracking"):
        with SessionLocal() as db:
            db.execute(
                text("UPDATE resource_assignment_kit SET tracking_code = 'COUNTED' WHERE kit_line_public_id = :line"),
                {"line": line["kit_line_public_id"]},
            )
            db.commit()
    with pytest.raises(IntegrityError, match="A kit line carries its piece's tracking"):
        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    INSERT INTO resource_assignment_kit (kit_line_public_id, resource_assignment_id, resource_assignment_trip_id,
                        equipment_asset_public_id, tracking_code, quantity, decision_public_id, busy_from, busy_to,
                        create_request_key, create_request_position, created_by)
                    SELECT :public_id, resource_assignment_id, resource_assignment_trip_id, equipment_asset_public_id,
                        'COUNTED', 1, decision_public_id, busy_from, busy_to, :key, 1, created_by
                    FROM resource_assignment_kit WHERE kit_line_public_id = :line
                    """
                ),
                {"public_id": str(uuid.uuid4()), "key": str(uuid.uuid4()), "line": line["kit_line_public_id"]},
            )
            db.commit()


# --- Independent review, round 4 ---------------------------------------------------------------------------------


def test_a_requirement_create_replayed_after_the_work_order_closes_is_refused(wo, fleet) -> None:
    """8A-R4-001: the replay comes after the Work Order's lock and its closure check."""
    key = str(uuid.uuid4())
    assert _requirement_response(wo, key=key).status_code == 201
    assert _requirement_response(wo, key=key).json()["event"] is None
    _close(wo)
    assert "This Work Order is closed" in _detail(_requirement_response(wo, key=key))


def test_a_requirement_create_checks_its_dates_against_the_work_order_as_it_stands_after_waiting(wo, fleet) -> None:
    """8A-R4-001: a contract shortened while the create waits for the Work Order's row is the one it checks against."""
    _ok(_save_period(wo, contract_start_date=TODAY.isoformat(), contract_end_date=(END + timedelta(days=30)).isoformat()))
    shorten = (
        "UPDATE crm_work_order_contract_period SET contract_end_date = :end "
        "WHERE work_order_id = (SELECT id FROM crm_work_order WHERE work_order_public_id = :id)"
    )
    response = _while_the_work_order_changes(
        wo, [shorten], lambda: _requirement_response(wo, units=1, end=END), end=END - timedelta(days=20)
    )
    assert response.status_code == 422, response.text


def test_the_replacement_finder_names_a_held_allocation_on_the_unit_shown(wo, fleet) -> None:
    """8A-R4-002: never a machine for unit 2 that would replace unit 1's, nor one for an allocation already ended."""
    held = _allocated(wo, fleet.ok)
    params = {"requirement_public_id": wo["requirement"]["requirement_public_id"], "replacing_assignment_public_id": held["assignment_public_id"]}
    other_unit = client.get(f"{URL}/candidates", params={**params, "unit_number": 2}, headers=auth_headers("ops1"))
    assert "is on unit 1, not unit 2" in _detail(other_unit)
    _ok(_post(held, "release", reason_code="NOT_NEEDED"))
    ended = client.get(f"{URL}/candidates", params={**params, "unit_number": 1}, headers=auth_headers("ops1"))
    assert "no longer held" in _detail(ended)


def _kit_days(kit_line_public_id: str) -> tuple[str, str | None]:
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT busy_from, busy_to FROM resource_assignment_kit WHERE kit_line_public_id = :line"), {"line": kit_line_public_id}
        ).one()
    return row[0].isoformat(), row[1].isoformat() if row[1] else None


def test_the_database_keeps_a_kit_lines_days_to_its_trip_and_allocation(wo, fleet) -> None:
    """8A-R4-003: days written untrue are put back, so the one-piece rule cannot be dodged, and a line moves with its
    allocation."""
    first = _ok(_add_kit(_allocated(wo, fleet.ok), [(fleet.hook, 1)]), 201)["assignment"]
    line = first["trips"][0]["kit"][0]["kit_line_public_id"]
    far = END + timedelta(days=400)
    with SessionLocal() as db:
        db.execute(
            text("UPDATE resource_assignment_kit SET busy_from = :far, busy_to = :far WHERE kit_line_public_id = :line"),
            {"far": far, "line": line},
        )
        db.commit()
    assert _kit_days(line) == (START.isoformat(), END.isoformat())
    second = _allocated(wo, fleet.spare, unit=2)
    assert _add_kit(second, [(fleet.hook, 1)]).status_code == 409
    with SessionLocal() as db:
        mark_service_write(db)
        db.execute(
            text("UPDATE resource_assignment SET planned_to = :end WHERE assignment_public_id = :a"),
            {"end": END - timedelta(days=10), "a": first["assignment_public_id"]},
        )
        db.commit()
    assert _kit_days(line) == (START.isoformat(), (END - timedelta(days=10)).isoformat())


# --- Independent review, round 5 ---------------------------------------------------------------------------------


def _execute(sql: str, **params) -> None:
    """A direct statement, marked as the service's own write: the tests of the database's own rules reach them past
    the guard that refuses an unmarked allocation write (8A-FA2-001, tested on its own below)."""
    with SessionLocal() as db:
        mark_service_write(db)
        db.execute(text(sql), params)
        db.commit()


def test_the_database_keeps_every_later_trip_within_its_allocations_planned_period(wo, fleet) -> None:
    """8A-R5-001: a trip written or moved outside the period, or a period moved off a trip, is refused - so a kit
    line's derived days are never longer than the allocation's."""
    held = _ok(_post(_allocated(wo, fleet.ok), "trips", goes_on=START + timedelta(days=20)), 201)["assignment"]
    trip = next(item for item in held["trips"] if item["trip_number"] == 2)
    refused = "trip goes on a day|keeps every later trip"
    for sql, params in (
        ("UPDATE resource_assignment SET planned_to = :d WHERE assignment_public_id = :a", {"d": START + timedelta(days=10)}),
        ("UPDATE resource_assignment SET planned_from = :d WHERE assignment_public_id = :a", {"d": START + timedelta(days=25)}),
        ("UPDATE resource_assignment_trip SET goes_on = :d WHERE trip_public_id = :t", {"d": START - timedelta(days=1)}),
        ("UPDATE resource_assignment_trip SET goes_on = :d WHERE trip_public_id = :t", {"d": END + timedelta(days=1)}),
        (
            "INSERT INTO resource_assignment_trip (trip_public_id, resource_assignment_id, trip_number, goes_on, created_by) "
            "SELECT :new, resource_assignment_id, 3, :d, created_by FROM resource_assignment_trip WHERE trip_public_id = :t",
            {"d": END + timedelta(days=5), "new": str(uuid.uuid4())},
        ),
    ):
        with pytest.raises(IntegrityError, match=refused):
            _execute(sql, a=held["assignment_public_id"], t=trip["trip_public_id"], **params)
    # Within the period, a trip may move, and the period may change around it.
    _execute("UPDATE resource_assignment_trip SET goes_on = :d WHERE trip_public_id = :t", d=START + timedelta(days=15), t=trip["trip_public_id"])
    _execute("UPDATE resource_assignment SET planned_to = :d WHERE assignment_public_id = :a", d=START + timedelta(days=30), a=held["assignment_public_id"])


def test_a_later_trip_cut_off_by_freeing_carries_no_days_so_its_piece_can_go_elsewhere(wo, fleet) -> None:
    """8A-R5-001: ending an allocation before a later trip's day is the history, not an error: that trip's kit has no
    days, and the piece is free for another allocation over them."""
    held = _ok(_post(_allocated(wo, fleet.ok), "trips", goes_on=START + timedelta(days=20)), 201)["assignment"]
    listed = _ok(_add_kit(held, [(fleet.hook, 1)], trip=2), 201)["assignment"]
    line = next(item for item in listed["trips"] if item["trip_number"] == 2)["kit"][0]["kit_line_public_id"]
    _ok(_post(listed, "release", last_day=START + timedelta(days=10), reason_code="NOT_NEEDED"))
    busy_from, busy_to = _kit_days(line)
    assert busy_to < busy_from
    other = _allocated(wo, fleet.spare, unit=2, planned_from=START + timedelta(days=15))
    assert _add_kit(other, [(fleet.hook, 1)]).status_code == 201


# --- Independent review, round 6 ---------------------------------------------------------------------------------


def _meanwhile(first_sql: str, first_params: dict, second, *, wait: float = 3):
    """Hold `first_sql` uncommitted in one session while `second` runs in another: `second` must wait for the first
    to commit (the triggers' lock), then see it. Returns what `second` returned or raised."""
    result: dict = {}

    def run() -> None:
        try:
            result["value"] = second()
        except Exception as exc:  # noqa: BLE001 - handed back to the test
            result["error"] = exc

    with SessionLocal() as first:
        mark_service_write(first)
        first.execute(text(first_sql), first_params)
        worker = threading.Thread(target=run)
        worker.start()
        worker.join(timeout=wait)
        assert worker.is_alive(), "the second write did not wait for the first"
        first.commit()
    worker.join(timeout=60)
    return result


def test_a_period_shortened_while_a_later_trip_is_being_added_waits_and_is_refused(wo, fleet) -> None:
    """8A-R6-001: the trigger checking the period reads the trips only after the first transaction commits."""
    held = _allocated(wo, fleet.ok)
    result = _meanwhile(
        "INSERT INTO resource_assignment_trip (trip_public_id, resource_assignment_id, trip_number, goes_on, created_by) "
        "SELECT :new, id, 2, :day, created_by FROM resource_assignment WHERE assignment_public_id = :a",
        {"new": str(uuid.uuid4()), "day": START + timedelta(days=20), "a": held["assignment_public_id"]},
        lambda: _execute(
            "UPDATE resource_assignment SET planned_to = :d WHERE assignment_public_id = :a",
            d=START + timedelta(days=10),
            a=held["assignment_public_id"],
        ),
    )
    assert isinstance(result.get("error"), IntegrityError) and "keeps every later trip" in str(result["error"])
    assert _get(held)["planned_to"] == END.isoformat()


def test_an_allocation_extended_while_a_kit_line_is_being_listed_moves_that_line_too(wo, fleet) -> None:
    """8A-R6-001: the follower moving an allocation's kit waits for a line being written, then moves it as well."""
    held = _ok(_add_kit(_allocated(wo, fleet.ok, planned_to=START + timedelta(days=10)), [(fleet.hook, 1)]), 201)["assignment"]
    hook_line = held["trips"][0]["kit"][0]["kit_line_public_id"]
    new_line = str(uuid.uuid4())
    result = _meanwhile(
        """
        INSERT INTO resource_assignment_kit (kit_line_public_id, resource_assignment_id, resource_assignment_trip_id,
            equipment_asset_public_id, tracking_code, quantity, decision_public_id, busy_from, busy_to,
            create_request_key, create_request_position, created_by)
        SELECT :new, resource_assignment_id, resource_assignment_trip_id, :piece, 'COUNTED', 1, decision_public_id,
            busy_from, busy_to, :key, 1, created_by
        FROM resource_assignment_kit WHERE kit_line_public_id = :line
        """,
        {"new": new_line, "piece": fleet.counterweight, "key": str(uuid.uuid4()), "line": hook_line},
        lambda: _execute(
            "UPDATE resource_assignment SET planned_to = :d WHERE assignment_public_id = :a",
            d=START + timedelta(days=30),
            a=held["assignment_public_id"],
        ),
    )
    assert "error" not in result, result.get("error")
    assert _kit_days(new_line) == (START.isoformat(), (START + timedelta(days=30)).isoformat())
    assert _kit_days(hook_line) == (START.isoformat(), (START + timedelta(days=30)).isoformat())


def test_a_trip_added_while_the_period_is_being_shortened_waits_and_is_refused(wo, fleet) -> None:
    """8A-R6-001, the other order: the trip's trigger reads the period only after the shortening commits - without
    the lock it would read the old period, pass, and wait only for its foreign key."""
    held = _allocated(wo, fleet.ok)
    result = _meanwhile(
        "UPDATE resource_assignment SET planned_to = :d WHERE assignment_public_id = :a",
        {"d": START + timedelta(days=10), "a": held["assignment_public_id"]},
        lambda: _execute(
            "INSERT INTO resource_assignment_trip (trip_public_id, resource_assignment_id, trip_number, goes_on, created_by) "
            "SELECT :new, id, 2, :day, created_by FROM resource_assignment WHERE assignment_public_id = :a",
            new=str(uuid.uuid4()),
            day=START + timedelta(days=20),
            a=held["assignment_public_id"],
        ),
    )
    assert isinstance(result.get("error"), IntegrityError) and "trip goes on a day" in str(result["error"])


def test_a_kit_line_written_while_the_allocation_is_being_extended_takes_the_extended_end(wo, fleet) -> None:
    """8A-R6-001, the other order: the kit line's trigger derives its days only after the extension commits."""
    held = _ok(_add_kit(_allocated(wo, fleet.ok, planned_to=START + timedelta(days=10)), [(fleet.hook, 1)]), 201)["assignment"]
    hook_line = held["trips"][0]["kit"][0]["kit_line_public_id"]
    new_line = str(uuid.uuid4())
    result = _meanwhile(
        "UPDATE resource_assignment SET planned_to = :d WHERE assignment_public_id = :a",
        {"d": START + timedelta(days=30), "a": held["assignment_public_id"]},
        lambda: _execute(
            """
            INSERT INTO resource_assignment_kit (kit_line_public_id, resource_assignment_id, resource_assignment_trip_id,
                equipment_asset_public_id, tracking_code, quantity, decision_public_id, busy_from, busy_to,
                create_request_key, create_request_position, created_by)
            SELECT :new, resource_assignment_id, resource_assignment_trip_id, :piece, 'COUNTED', 1, decision_public_id,
                busy_from, busy_to, :key, 1, created_by
            FROM resource_assignment_kit WHERE kit_line_public_id = :line
            """,
            new=new_line,
            piece=fleet.counterweight,
            key=str(uuid.uuid4()),
            line=hook_line,
        ),
    )
    assert "error" not in result, result.get("error")
    assert _kit_days(new_line) == (START.isoformat(), (START + timedelta(days=30)).isoformat())


def test_a_direct_delete_of_a_kit_line_or_trip_waits_for_the_lock_before_its_row(wo, fleet) -> None:
    """8A-R8-001: a delete, like an insert or update, takes the module's lock before locking the row, so it cannot hold
    a kit line or trip a service write holding the lock is about to lock."""
    held = _ok(_add_kit(_allocated(wo, fleet.ok), [(fleet.hook, 1)]), 201)["assignment"]
    line = held["trips"][0]["kit"][0]["kit_line_public_id"]
    result = _service_holds_the_lock_then_locks(
        "SELECT id FROM resource_assignment_kit WHERE kit_line_public_id = :line FOR UPDATE",
        "DELETE FROM resource_assignment_kit WHERE kit_line_public_id = :line",
        line=line,
    )
    assert result == {"service": "committed", "direct": "done"}
    with_trip = _ok(_post(_get(held), "trips", goes_on=START + timedelta(days=20)), 201)["assignment"]
    trip = next(item for item in with_trip["trips"] if item["trip_number"] == 2)["trip_public_id"]
    result = _service_holds_the_lock_then_locks(
        "SELECT id FROM resource_assignment_trip WHERE trip_public_id = :trip FOR UPDATE",
        "DELETE FROM resource_assignment_trip WHERE trip_public_id = :trip",
        trip=trip,
    )
    assert result == {"service": "committed", "direct": "done"}


def test_a_requirement_says_which_units_are_covered(wo, fleet) -> None:
    """8A-R8-002: unit 1 covered on every day, unit 2 only on some - allocation is offered on unit 2 alone."""
    _allocated(wo, fleet.ok)
    _allocated(wo, fleet.spare, unit=2, planned_to=START + timedelta(days=10))
    requirement = _get_requirement(wo)
    assert (requirement["covered_unit_numbers"], requirement["units_covered"]) == ([1], 1)


def test_the_triggers_take_the_lock_the_service_takes_once_per_statement() -> None:
    """The key the statement triggers lock with is the service's own (8A-R6-001), taken per statement on the three
    tables (8A-R7-001) and nowhere per row."""
    from app.modules.resource_assignments.repository import WRITE_LOCK_KEY

    with SessionLocal() as db:
        locking = {
            name
            for (name,) in db.execute(
                text("SELECT proname FROM pg_proc WHERE proname LIKE 'resource_assignment%' AND prosrc LIKE :lock"),
                {"lock": f"%pg_advisory_xact_lock({WRITE_LOCK_KEY})%"},
            ).all()
        }
        per_statement = {
            (table, name)
            for table, name in db.execute(
                text(
                    "SELECT c.relname, t.tgname FROM pg_trigger t INNER JOIN pg_class c ON c.oid = t.tgrelid "
                    "INNER JOIN pg_proc p ON p.oid = t.tgfoid "
                    "WHERE p.proname = 'resource_assignment_serialize' AND (t.tgtype & 1) = 0 AND (t.tgtype & 2) = 2"
                )
            ).all()
        }
    assert locking == {"resource_assignment_serialize"}
    assert {table for table, _name in per_statement} == {"resource_assignment", "resource_assignment_trip", "resource_assignment_kit"}
    # INSERT (4), DELETE (8) and UPDATE (16) of trips and kit, UPDATE and DELETE of allocations - not adding one
    # (8A-R9-001) - and on every column: no column list (8A-R9-002).
    with SessionLocal() as db:
        events = {
            table: (mask, columns)
            for table, mask, columns in db.execute(
                text(
                    "SELECT c.relname, t.tgtype & 28, t.tgattr::text FROM pg_trigger t INNER JOIN pg_class c ON c.oid = t.tgrelid "
                    "WHERE t.tgname LIKE 'resource_assignment_serialize%'"
                )
            ).all()
        }
    assert events == {"resource_assignment": (24, ""), "resource_assignment_trip": (28, ""), "resource_assignment_kit": (28, "")}


# --- Independent review, round 7 ---------------------------------------------------------------------------------


def _service_holds_the_lock_then_locks(row_sql: str, direct_sql: str, **params) -> dict:
    """A transaction written as the service writes - the module's lock, then the row - while a direct statement on
    that row starts in between: the direct statement must wait before locking the row, so the first gets it at once
    and commits, and no transaction is chosen as a deadlock victim (8A-R7-001)."""
    from app.modules.resource_assignments.repository import WRITE_LOCK_KEY

    result: dict = {}

    def direct() -> None:
        try:
            _execute(direct_sql, **params)
            result["direct"] = "done"
        except Exception as exc:  # noqa: BLE001 - handed back to the test
            result["direct"] = exc

    with SessionLocal() as service:
        service.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": WRITE_LOCK_KEY})
        worker = threading.Thread(target=direct)
        worker.start()
        worker.join(timeout=2)
        assert worker.is_alive(), "the direct statement did not wait for the module's lock"
        service.execute(text("SET LOCAL lock_timeout = '10s'"))
        service.execute(text(row_sql), params)
        service.commit()
        result["service"] = "committed"
    worker.join(timeout=60)
    return result


def test_a_direct_date_change_never_deadlocks_with_a_service_write_on_the_same_allocation(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    result = _service_holds_the_lock_then_locks(
        "SELECT id FROM resource_assignment WHERE assignment_public_id = :a FOR UPDATE",
        "UPDATE resource_assignment SET planned_to = :d WHERE assignment_public_id = :a",
        a=held["assignment_public_id"],
        d=END - timedelta(days=1),
    )
    assert result == {"service": "committed", "direct": "done"}


def test_a_direct_kit_change_never_deadlocks_with_a_service_write_on_the_same_line(wo, fleet) -> None:
    held = _ok(_add_kit(_allocated(wo, fleet.ok), [(fleet.hook, 1)]), 201)["assignment"]
    line = held["trips"][0]["kit"][0]["kit_line_public_id"]
    result = _service_holds_the_lock_then_locks(
        "SELECT id FROM resource_assignment_kit WHERE kit_line_public_id = :line FOR UPDATE",
        "UPDATE resource_assignment_kit SET decision_public_id = decision_public_id WHERE kit_line_public_id = :line",
        line=line,
    )
    assert result == {"service": "committed", "direct": "done"}


def test_an_allocation_spanning_a_contract_gap_is_warned_though_both_its_ends_are_inside(wo, fleet) -> None:
    """8A-R7-002: a gap between extensions wholly inside the allocation is outside the contract."""
    _ok(_save_period(wo, contract_start_date=TODAY.isoformat(), contract_end_date=(START + timedelta(days=10)).isoformat()))
    _ok(
        _extend(
            wo,
            new_end_date=END.isoformat(),
            received_date=TODAY.isoformat(),
            extension_start_date=(START + timedelta(days=20)).isoformat(),
            # A gap is recorded only once confirmed, from its first day (Slice 7D Part 3).
            gap_confirmed_from=(START + timedelta(days=11)).isoformat(),
        ),
        201,
    )
    held = _allocated(wo, fleet.ok)
    assert "OUTSIDE_CONTRACT" in _get(held)["warnings"]
    within = _allocated(wo, fleet.spare, unit=2, planned_to=START + timedelta(days=10))
    assert "OUTSIDE_CONTRACT" not in _get(within)["warnings"]


# --- Independent review, round 9 ---------------------------------------------------------------------------------


def test_a_direct_allocation_insert_waits_on_its_requirement_without_the_lock(wo, fleet) -> None:
    """8A-R9-001: a service write holding the requirement's row and then taking the module's lock is never blocked by
    a direct insert holding that lock while it waits for the requirement - the insert takes no part in the lock."""
    from app.modules.resource_assignments.repository import WRITE_LOCK_KEY

    held = _allocated(wo, fleet.ok)
    columns = _COPY_COLUMNS.replace("unit_number, ", "")
    result: dict = {}

    def direct() -> None:
        try:
            _execute(
                f"""
                INSERT INTO resource_assignment (assignment_public_id, create_request_key, equipment_asset_public_id,
                    allocated_asset_version, unit_number, {columns})
                SELECT :public_id, :key, :machine, 1, 2, {columns} FROM resource_assignment WHERE assignment_public_id = :source
                """,
                public_id=str(uuid.uuid4()),
                key=str(uuid.uuid4()),
                machine=fleet.spare,
                source=held["assignment_public_id"],
            )
            result["direct"] = "done"
        except Exception as exc:  # noqa: BLE001 - handed back to the test
            result["direct"] = exc

    with SessionLocal() as service:
        service.execute(
            text("SELECT id FROM resource_requirement WHERE requirement_public_id = :r FOR UPDATE"),
            {"r": wo["requirement"]["requirement_public_id"]},
        )
        worker = threading.Thread(target=direct)
        worker.start()
        worker.join(timeout=2)
        assert worker.is_alive(), "the direct insert did not wait for the requirement's row"
        service.execute(text("SET LOCAL lock_timeout = '10s'"))
        service.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": WRITE_LOCK_KEY})
        service.commit()
    worker.join(timeout=60)
    assert result == {"direct": "done"}


@pytest.mark.parametrize(
    ("row_sql", "direct_sql"),
    [
        (
            "SELECT id FROM resource_assignment WHERE assignment_public_id = :a FOR UPDATE",
            "UPDATE resource_assignment SET billing_cycle_code = billing_cycle_code WHERE assignment_public_id = :a",
        ),
        (
            "SELECT id FROM resource_assignment_trip WHERE resource_assignment_id = (SELECT id FROM resource_assignment WHERE assignment_public_id = :a) FOR UPDATE",
            "UPDATE resource_assignment_trip SET note = note WHERE resource_assignment_id = (SELECT id FROM resource_assignment WHERE assignment_public_id = :a)",
        ),
    ],
)
def test_an_update_of_any_column_waits_for_the_lock_before_its_row(wo, fleet, row_sql, direct_sql) -> None:
    """8A-R9-002: not only the date columns - any update of an allocation or trip."""
    held = _allocated(wo, fleet.ok)
    result = _service_holds_the_lock_then_locks(row_sql, direct_sql, a=held["assignment_public_id"])
    assert result == {"service": "committed", "direct": "done"}


def test_the_requirement_an_allocation_fills_never_changes(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    other = _requirement(wo, units=1)
    with pytest.raises(IntegrityError, match="never changes"):
        _execute(
            "UPDATE resource_assignment SET resource_requirement_public_id = :r WHERE assignment_public_id = :a",
            r=other["requirement_public_id"],
            a=held["assignment_public_id"],
        )


# --- The database refuses on its own -----------------------------------------------------------------------------

_COPY_COLUMNS = (
    "resource_requirement_public_id, unit_number, work_order_public_id, work_order_code, work_order_line_public_id, "
    "work_order_line_number, allocated_class_code, planned_from, planned_to, assignment_status_code, decision_public_id, "
    "created_by, updated_by"
)


def _insert_copy(source: str, *, machine: str, version: int) -> None:
    with SessionLocal() as db:
        # Marked as the service's own write, so the constraint under test is reached past the guard (8A-FA2-001).
        mark_service_write(db)
        db.execute(
            text(
                f"""
                INSERT INTO resource_assignment (assignment_public_id, create_request_key, equipment_asset_public_id,
                    allocated_asset_version, {_COPY_COLUMNS})
                SELECT :public_id, :key, :machine, :version, {_COPY_COLUMNS}
                FROM resource_assignment WHERE assignment_public_id = :source
                """
            ),
            {"public_id": str(uuid.uuid4()), "key": str(uuid.uuid4()), "machine": machine, "version": version, "source": source},
        )
        db.commit()


def test_the_database_refuses_a_machine_on_two_allocations_or_a_unit_filled_twice_on_a_common_day(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    with pytest.raises(IntegrityError, match="ex_resource_assignment_machine_overlap"):
        _insert_copy(held["assignment_public_id"], machine=fleet.ok, version=held["allocated_asset_version"])
    with pytest.raises(IntegrityError, match="ex_resource_assignment_unit_overlap"):
        _insert_copy(held["assignment_public_id"], machine=fleet.spare, version=1)


def test_the_database_refuses_a_piece_on_two_listed_lines_on_a_common_day(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    listed = _ok(_add_kit(held, [(fleet.hook, 1)]), 201)["assignment"]
    line = listed["trips"][0]["kit"][0]
    with pytest.raises(IntegrityError, match="ex_resource_assignment_kit_piece_overlap"):
        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    INSERT INTO resource_assignment_kit (kit_line_public_id, resource_assignment_id, resource_assignment_trip_id,
                        equipment_asset_public_id, tracking_code, quantity, decision_public_id, busy_from, busy_to,
                        create_request_key, create_request_position, created_by)
                    SELECT :public_id, resource_assignment_id, resource_assignment_trip_id, equipment_asset_public_id,
                        tracking_code, quantity, decision_public_id, busy_from, busy_to, :key, 1, created_by
                    FROM resource_assignment_kit WHERE kit_line_public_id = :source
                    """
                ),
                {"public_id": str(uuid.uuid4()), "key": str(uuid.uuid4()), "source": line["kit_line_public_id"]},
            )
            db.commit()


# --- Events and routes -----------------------------------------------------------------------------------------


def test_event_payloads_carry_no_registration_note_or_reason_text(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok, notes="Call Ravi at the gate, 98450 00000")
    _ok(_post(held, "release", reason_code="OTHER", note="Customer postponed; see email of 3 October"))
    text_of_events = json.dumps(_events(held["assignment_public_id"]))
    for secret in (fleet.number("OK"), "Ravi", "98450", "postponed"):
        assert secret not in text_of_events


# --- Trips (Own Load): a crane in several loads (owner, 29 September 2026) --------------------------------------


def test_a_crane_goes_in_several_loads_each_saying_what_it_carries(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    loads = ["Base and carbody", "Crawlers, left and right", "Boom butt and inserts"]
    # Loads 2 and 3 go on the allocation's first day, with load 1.
    for note in loads[1:]:
        held = _ok(_post(held, "trips", goes_on=START, note=note), 201)["assignment"]
    said = _ok(_put(held, "trips/1/note", note=f"  {loads[0]}  "))
    assert [event["event_name"] for event in said["events"]] == ["RESOURCE_ASSIGNMENT_TRIP_NOTE_CHANGED"]
    trips = said["assignment"]["trips"]
    assert [(trip["trip_number"], trip["goes_on"], trip["note"]) for trip in trips] == [
        (number, START.isoformat(), note) for number, note in enumerate(loads, start=1)
    ]
    assert said["assignment"]["assignment_version"] == held["assignment_version"] + 1
    # The same note again records nothing; clearing it is a change.
    same = _ok(_put(said["assignment"], "trips/1/note", note=loads[0]))
    assert same["events"] == [] and same["assignment"]["assignment_version"] == said["assignment"]["assignment_version"]
    cleared = _ok(_put(said["assignment"], "trips/1/note", note="   "))["assignment"]
    assert cleared["trips"][0]["note"] is None
    # The note is not put in the event, as an allocation's notes are not.
    assert "Base and carbody" not in json.dumps(_events(held["assignment_public_id"]))


def test_saying_what_a_load_carries_leaves_its_day_and_kit_days_alone(wo, fleet) -> None:
    held = _ok(_add_kit(_allocated(wo, fleet.ok), [(fleet.hook, 1)]), 201)["assignment"]
    before = _kit_days(held["trips"][0]["kit"][0]["kit_line_public_id"])
    said = _ok(_put(held, "trips/1/note", note="Upper works"))["assignment"]
    assert said["trips"][0]["goes_on"] == held["trips"][0]["goes_on"]
    assert _kit_days(held["trips"][0]["kit"][0]["kit_line_public_id"]) == before


def test_saying_what_a_load_carries_is_refused_where_writes_are(wo, fleet) -> None:
    held = _allocated(wo, fleet.ok)
    assert _put(held, "trips/7/note", note="Crawlers").status_code == 404
    assert _put(held, "trips/1/note", note="x" * 501).status_code == 422
    for username in ("sales1", "readonly1"):
        assert _put(held, "trips/1/note", username=username, note="Crawlers").status_code == 403
    stale = dict(held, assignment_version=held["assignment_version"] + 5)
    assert _put(stale, "trips/1/note", note="Crawlers").status_code == 409
    freed = _ok(_post(held, "release", reason_code="NOT_NEEDED"))["assignment"]
    assert "was freed" in _detail(_put(freed, "trips/1/note", note="Crawlers"))


# --- Full review (30 September 2026) ------------------------------------------------------------------------------


def _extend_directly_meanwhile(allocation: dict, second) -> dict:
    """An allocation's end moved by a direct statement - it takes Resource Assignment's lock through the statement
    trigger, not the requirement's - held uncommitted while `second` changes the requirement's end another way."""
    return _meanwhile(
        "UPDATE resource_assignment SET planned_to = :d WHERE assignment_public_id = :a",
        {"d": END + timedelta(days=10), "a": allocation["assignment_public_id"]},
        second,
    )


def test_a_status_worked_out_as_the_contract_end_moves_waits_for_an_allocation_being_written(wo, fleet) -> None:
    """8A-FA-001: the end-dates listener reads coverage only after taking Resource Assignment's lock, so a stored
    status is never worked out from an allocation's days a transaction is still changing."""
    _ok(_save_period(wo, contract_start_date=TODAY.isoformat(), contract_end_date=END.isoformat()))
    record = {**wo, "requirement": _requirement(wo, units=1, end=None)}
    held = _allocated(record, fleet.ok)
    assert _get_requirement(record)["requirement_status_code"] == "FULFILLED"
    result = _extend_directly_meanwhile(
        held,
        lambda: _save_period(
            wo, expected_period_version=1, contract_start_date=TODAY.isoformat(), contract_end_date=(END + timedelta(days=10)).isoformat()
        ),
    )
    assert result["value"].status_code == 200, result
    # The contract now runs ten days longer, and so does the allocation: every day is covered.
    assert _get_requirement(record)["requirement_status_code"] == "FULFILLED"


def test_a_status_worked_out_as_a_requirement_changes_waits_for_an_allocation_being_written(wo, fleet) -> None:
    """8A-FA-001: a requirement's own change reads coverage only after taking Resource Assignment's lock."""
    record = {**wo, "requirement": _requirement(wo, units=1)}
    held = _allocated(record, fleet.ok)
    requirement = _get_requirement(record)
    assert requirement["requirement_status_code"] == "FULFILLED"
    body = _requirement_body(requirement, required_to=(END + timedelta(days=10)).isoformat())
    result = _extend_directly_meanwhile(
        held,
        lambda: client.put(f"{REQUIREMENTS}/{requirement['requirement_public_id']}", json=body, headers=auth_headers("ops1")),
    )
    assert result["value"].status_code == 200, result
    assert _get_requirement(record)["requirement_status_code"] == "FULFILLED"


def _listed(work_order: dict, **params) -> list[str]:
    rows = _ok(client.get(URL, params={"requirement_public_id": work_order["requirement"]["requirement_public_id"], **params}, headers=auth_headers("readonly1")))
    return [row["assignment_reference"] for row in rows]


def test_lists_come_in_the_order_recorded_and_page_after_a_given_allocation(wo, fleet) -> None:
    """8A-FB-004: the order no later write changes, and `after` the last row read - so a row leaving the list between
    two pages makes no other skipped or read twice."""
    first = _allocated(wo, fleet.ok)
    second = _allocated(wo, fleet.spare, unit=2)
    _ok(_post(first, "release", reason_code="NOT_NEEDED"))
    # Recorded order, not held first.
    assert _listed(wo) == [first["assignment_reference"], second["assignment_reference"]]
    assert _listed(wo, after=first["assignment_public_id"]) == [second["assignment_reference"]]
    assert _listed(wo, after=second["assignment_public_id"]) == []
    assert "no such allocation" in _detail(client.get(URL, params={"after": str(uuid.uuid4())}, headers=auth_headers("readonly1")))


def test_a_row_leaving_a_filtered_list_between_pages_skips_no_other(wo, fleet) -> None:
    """8A-FB-004: the held list, one row a page. The first row is freed after the first page: skipping one row would
    now skip the second; reading after the first does not."""
    first = _allocated(wo, fleet.ok)
    second = _allocated(wo, fleet.spare, unit=2)
    assert _listed(wo, status_code="HELD", limit=1) == [first["assignment_reference"]]
    _ok(_post(first, "release", reason_code="NOT_NEEDED"))
    assert _listed(wo, status_code="HELD", limit=1, offset=1) == []
    assert _listed(wo, status_code="HELD", limit=1, after=first["assignment_public_id"]) == [second["assignment_reference"]]


# --- Full review, round 2 (30 September 2026) ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("before", "sql"),
    [
        (None, "UPDATE resource_assignment SET planned_to = :d WHERE assignment_public_id = :a"),
        # Its trips first, in the same transaction, so nothing but the guard could stop the delete (8A-F3-002).
        (
            "DELETE FROM resource_assignment_trip WHERE resource_assignment_id = "
            "(SELECT id FROM resource_assignment WHERE assignment_public_id = :a)",
            "DELETE FROM resource_assignment WHERE assignment_public_id = :a",
        ),
        # No row: the statement is refused before any row is considered.
        (None, "INSERT INTO resource_assignment (assignment_public_id) SELECT assignment_public_id FROM resource_assignment WHERE false"),
    ],
)
def test_an_allocation_written_around_the_service_is_refused(wo, fleet, before, sql) -> None:
    """8A-FA2-001: the service keeps the requirement's stored status in step with its allocations; a statement
    written around it could not, so the database refuses it - adding, changing or removing."""
    record = {**wo, "requirement": _requirement(wo, units=1)}
    held = _allocated(record, fleet.ok)
    assert _get_requirement(record)["requirement_status_code"] == "FULFILLED"
    params = {"d": END - timedelta(days=1), "a": held["assignment_public_id"]}
    with SessionLocal() as db, pytest.raises(IntegrityError, match="written only by the Resource Assignments service"):
        if before:
            db.execute(text(before), params)
        db.execute(text(sql), params)
    after = _get_requirement(record)
    assert (after["requirement_status_code"], after["units_covered"]) == ("FULFILLED", 1)
    assert _get(held)["planned_to"] == END.isoformat()


def test_the_ports_hold_takes_the_lock_without_marking_an_allocation_write(wo, fleet) -> None:
    """8A-F3-003: Resource Requirements reads coverage under the lock and writes no allocation, so its transaction is
    not marked: an allocation statement in it is refused."""
    held = _allocated(wo, fleet.ok)
    with SessionLocal() as db:
        ports.assignment_port().hold(db)
        with pytest.raises(IntegrityError, match="written only by the Resource Assignments service"):
            db.execute(text("UPDATE resource_assignment SET notes = notes WHERE assignment_public_id = :a"), {"a": held["assignment_public_id"]})


def test_the_service_mark_lasts_one_transaction(wo, fleet) -> None:
    """8A-FA2-001: the mark is transaction-local - a session that wrote as the service writes around it next time."""
    held = _allocated(wo, fleet.ok)
    with SessionLocal() as db:
        mark_service_write(db)
        db.execute(text("UPDATE resource_assignment SET notes = notes WHERE assignment_public_id = :a"), {"a": held["assignment_public_id"]})
        db.commit()
        with pytest.raises(IntegrityError, match="written only by the Resource Assignments service"):
            db.execute(text("UPDATE resource_assignment SET notes = notes WHERE assignment_public_id = :a"), {"a": held["assignment_public_id"]})


def test_kit_options_name_the_allocation_version_they_answer_for(wo, fleet) -> None:
    """8A-FB2-003: the screen shows kit options only under the allocation version they were worked out for."""
    held = _allocated(wo, fleet.ok)
    first = _ok(client.get(f"{URL}/{held['assignment_public_id']}/kit-options", params={"trip_number": 1}, headers=auth_headers("ops1")))
    assert first["assignment_version"] == held["assignment_version"]
    moved = _ok(_put(held, "billing-cycle", billing_cycle_code="WEEKLY"))["assignment"]
    again = _ok(client.get(f"{URL}/{held['assignment_public_id']}/kit-options", params={"trip_number": 1}, headers=auth_headers("ops1")))
    assert again["assignment_version"] == moved["assignment_version"] == held["assignment_version"] + 1


def test_the_fourteen_routes_are_pinned_with_their_permissions() -> None:
    from tests.fixtures.post_baseline_tightened_routes import POST_BASELINE_NEW_ROUTES

    pinned = {key: permission for key, permission in POST_BASELINE_NEW_ROUTES.items() if key[1].startswith(URL)}
    assert pinned == {
        ("GET", URL): "RESOURCE_ASSIGNMENT_READ",
        ("GET", f"{URL}/candidates"): "RESOURCE_ASSIGNMENT_READ",
        ("GET", f"{URL}/{{public_id}}"): "RESOURCE_ASSIGNMENT_READ",
        ("POST", URL): "RESOURCE_ASSIGNMENT_WRITE",
        ("POST", f"{URL}/{{public_id}}/replace"): "RESOURCE_ASSIGNMENT_WRITE",
        ("POST", f"{URL}/{{public_id}}/release"): "RESOURCE_ASSIGNMENT_WRITE",
        ("PUT", f"{URL}/{{public_id}}/dates"): "RESOURCE_ASSIGNMENT_WRITE",
        ("POST", f"{URL}/{{public_id}}/check"): "RESOURCE_ASSIGNMENT_WRITE",
        ("PUT", f"{URL}/{{public_id}}/billing-cycle"): "WORK_ORDER_LINE_BILLING_TERMS_WRITE",
        ("GET", f"{URL}/{{public_id}}/kit-options"): "RESOURCE_ASSIGNMENT_READ",
        ("POST", f"{URL}/{{public_id}}/trips"): "RESOURCE_ASSIGNMENT_WRITE",
        ("PUT", f"{URL}/{{public_id}}/trips/{{trip_number}}/note"): "RESOURCE_ASSIGNMENT_WRITE",
        ("POST", f"{URL}/{{public_id}}/kit"): "RESOURCE_ASSIGNMENT_WRITE",
        ("POST", f"{URL}/{{public_id}}/kit/{{kit_line_public_id}}/remove"): "RESOURCE_ASSIGNMENT_WRITE",
    }
