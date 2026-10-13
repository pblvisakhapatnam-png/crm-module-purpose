"""ELG-1 - machine eligibility through the API and at the database.

docs/agent/slices/elg-1-machine-eligibility.md, section 16: certificates, copies, "not applicable" marks, rules,
the check, Certificates due, permissions, events, the seeded rules and the decision 8A will store. Every machine,
model and number here is invented and carries a run-unique token; each test removes what it created.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.database import SessionLocal
from app.modules.documents.service import AttachRequest
from app.modules.eligibility import service as eligibility_service
from app.modules.eligibility.evaluation import months_after
from tests.business_day_test_support import TODAY, held_to_the_test_day
from tests.eligibility_test_support import eligibility_created_here
from tests.equipment_test_support import plum_report, plum_row, suffix
from tests.test_commercial_offers_api import auth_headers, client

EQUIPMENT = "/api/equipment-reference"
BASE = "/api/eligibility"
ADMIN = "admin1"
NON_ADMIN_ROLES = ("sales1", "manager1", "finance1", "ops1", "readonly1")
READ_ROLES = ("admin1",) + NON_ADMIN_ROLES
PDF = b"%PDF-1.4\n% invented certificate copy\n%%EOF\n"
ROAD_PAPERS = ("REGISTRATION", "INSURANCE", "POLLUTION_UNDER_CONTROL", "ROAD_TAX")


@pytest.fixture(scope="module", autouse=True)
def _on_the_test_day():
    with held_to_the_test_day():
        yield


@pytest.fixture(autouse=True)
def _remove_what_each_test_created():
    with eligibility_created_here():
        yield


# --- Helpers ---------------------------------------------------------------------------------------------


def _ok(response, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


def _detail(response, status: int = 422) -> str:
    assert response.status_code == status, response.text
    return response.json()["detail"]


def _model(maker: str, name: str, class_code: str, *, type_code: str | None = None, capabilities: list | None = None, fits: list | None = None) -> dict:
    body: dict[str, Any] = {
        "create_request_key": str(uuid.uuid4()),
        "maker": maker,
        "model_name": name,
        "class_code": class_code,
        "type_code": type_code,
        "capabilities": capabilities or [],
    }
    if fits is not None:
        body["fits_model_public_ids"] = [item["model_public_id"] for item in fits]
    return _ok(client.post(f"{EQUIPMENT}/models", json=body, headers=auth_headers(ADMIN)), 201)["model"]


def _map(source_name: str, model: dict) -> None:
    _ok(client.put(f"{EQUIPMENT}/model-mappings", json={"source_name": source_name, "model_public_id": model["model_public_id"]}, headers=auth_headers(ADMIN)))


def _machine(public_id: str) -> dict:
    return _ok(client.get(f"{EQUIPMENT}/machines/{public_id}", headers=auth_headers(ADMIN)))


class Fleet:
    """A wheeled crane held as superstructure and carrier, paired; a crawler crane; a crane whose model is not
    mapped; and, held for the crawler's model, a hook block and a sling."""

    def __init__(self) -> None:
        self.sfx = s = suffix()
        capacity = [{"capability_code": "RATED_CAPACITY", "value": "100"}]
        crane_model = _model("ACME", f"AC 200 {s}", "CRANE", type_code="ALL_TERRAIN", capabilities=capacity)
        carrier_model = _model("ACME", f"AC 200 {s}", "CRANE_CARRIER")
        crawler_model = _model("ACME", f"CC 200 {s}", "CRANE", type_code="CRAWLER", capabilities=capacity)
        super_name, chassis_name, crawler_name = f"{s} ACME AC 200 SUPER", f"{s} ACME AC 200 CHASSIS", f"{s} ACME CC 200"
        _map(super_name, crane_model)
        _map(chassis_name, carrier_model)
        _map(crawler_name, crawler_model)
        n = self.number
        rows = [
            plum_row(number=n("WC1"), schedule=super_name, category="CRANES", capacity="100", year="2016"),
            plum_row(number=n("WC1C"), schedule=chassis_name, category="CRANES", capacity="100", year="2016"),
            plum_row(number=n("CW1"), schedule=crawler_name, category="CRANES", capacity="100", year="2018"),
            plum_row(number=n("UC1"), schedule=f"{s} MYSTERY CRANE", category="CRANES", capacity="60", year="2012"),
        ]
        equipment_import = _ok(
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
                f"{EQUIPMENT}/imports/{equipment_import['import_public_id']}/publish",
                json={"expected_preview_version": equipment_import["preview_version"], "pairs": [{"part_machine_number": n("WC1C"), "machine_machine_number": n("WC1")}]},
                headers=auth_headers(ADMIN),
            )
        )
        found = _ok(client.get(f"{EQUIPMENT}/machines", params={"search": f"T{s}-", "limit": 50}, headers=auth_headers(ADMIN)))
        by_number = {item["machine_number"]: item["asset_public_id"] for item in found}
        parts = _ok(client.get(f"{EQUIPMENT}/machines", params={"search": f"T{s}-", "kind_code": "PART", "limit": 50}, headers=auth_headers(ADMIN)))
        by_number.update({item["machine_number"]: item["asset_public_id"] for item in parts})
        self.crane, self.carrier, self.crawler, self.unmapped = (by_number[n(label)] for label in ("WC1", "WC1C", "CW1", "UC1"))
        hook_model = _model("ACME", f"CC 200 hook {s}", "HOOK_BLOCK", type_code="HOOK_BLOCK", capabilities=capacity, fits=[crawler_model])
        sling_model = _model("ACME", f"Sling 10 t {s}", "LIFTING_TACKLE", type_code="SLING", capabilities=[{"capability_code": "RATED_CAPACITY", "value": "10"}], fits=[crawler_model])
        self.hook = self._kit(hook_model)
        self.sling = self._kit(sling_model)

    def number(self, label: str) -> str:
        return f"T{self.sfx}-{label}"

    def _kit(self, model: dict) -> str:
        body = {
            "create_request_key": str(uuid.uuid4()),
            "machine_public_id": self.crawler,
            "kit_model_public_id": model["model_public_id"],
            "expected_model_version": model["model_version"],
            "expected_asset_version": _machine(self.crawler)["asset_version"],
            "count": 1,
        }
        return _ok(client.post(f"{EQUIPMENT}/kit", json=body, headers=auth_headers(ADMIN)), 201)["pieces"][0]["asset_public_id"]


def _record(asset: str, kind: str, *, username: str = ADMIN, key: str | None = None, **fields) -> Any:
    body: dict[str, Any] = {
        "create_request_key": key or str(uuid.uuid4()),
        "kind_code": kind,
        "number": f"NO-{uuid.uuid4().hex[:6].upper()}",
        "issued_by": "Invented Authority",
        "issued_on": (TODAY - timedelta(days=30)).isoformat(),
        "valid_from": (TODAY - timedelta(days=30)).isoformat(),
        "valid_until": (TODAY + timedelta(days=335)).isoformat(),
    }
    if kind == "REGISTRATION":
        body["registered_as_code"] = "NON_TRANSPORT"
    if kind == "PERMIT":
        body["valid_in_code"] = "IN"
    if kind in ("ROAD_TAX", "THOROUGH_EXAMINATION", "LOAD_TEST"):
        body["valid_until"] = None
    body.update({key_: (value.isoformat() if isinstance(value, date) else value) for key_, value in fields.items()})
    return client.post(f"{BASE}/assets/{asset}/certificates", json=body, headers=auth_headers(username))


def _recorded(asset: str, kind: str, *, copy: bool = True, **fields) -> str:
    public_id = _ok(_record(asset, kind, **fields), 201)["certificate_public_id"]
    if copy:
        _ok(_attach(public_id), 201)
    return public_id


def _attach(certificate_public_id: str, *, username: str = ADMIN, document_type: str = "CERTIFICATE"):
    return client.post(
        "/api/documents/upload",
        data={"linked_record_type": "eligibility_certificate", "linked_record_public_id": certificate_public_id, "document_type": document_type},
        files={"file": ("copy.pdf", PDF, "application/pdf")},
        headers=auth_headers(username),
    )


def _certificates(asset: str, username: str = ADMIN) -> dict:
    return _ok(client.get(f"{BASE}/assets/{asset}/certificates", headers=auth_headers(username)))


def _status(asset: str, kind: str, username: str = ADMIN) -> dict:
    return next(item for item in _certificates(asset, username)["statuses"] if item["kind_code"] == kind)


def _mark(asset: str, kind: str, *, reason: str = "Tracked: not equipped to travel on public roads.", until: date | None = None, key: str | None = None, username: str = ADMIN):
    body = {"create_request_key": key or str(uuid.uuid4()), "kind_code": kind, "reason": reason, "until": until.isoformat() if until else None}
    return client.post(f"{BASE}/assets/{asset}/not-applicable", json=body, headers=auth_headers(username))


def _check(asset: str, *, state: str = "IN-GJ", start: date | None = None, end: date | None = None, central: bool = False, username: str = "readonly1"):
    start = start or TODAY + timedelta(days=3)
    params = {"state_code": state, "period_from": start.isoformat(), "central_government_site": str(central).lower()}
    params["period_to"] = (end or start + timedelta(days=30)).isoformat()
    return client.get(f"{BASE}/assets/{asset}/check", params=params, headers=auth_headers(username))


def _outcomes(check: dict) -> dict[str, str]:
    return {item["kind_code"]: item["outcome_code"] for item in check["results"] if item["kind_code"]}


def _certify_wheeled_crane(fleet: Fleet, *, examined_days_ago: int = 30) -> None:
    """Registration (non-transport), insurance, PUC and road tax on the carrier; the examinations on the crane."""
    for kind in ROAD_PAPERS:
        _recorded(fleet.carrier, kind)
    examined = TODAY - timedelta(days=examined_days_ago)
    _recorded(fleet.crane, "THOROUGH_EXAMINATION", issued_on=examined, valid_from=examined)
    _recorded(fleet.crane, "LOAD_TEST")


def _events(record_public_id: str) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT event_name, reason, event_payload_json FROM business_event WHERE record_public_id = :id ORDER BY id"),
            {"id": record_public_id},
        ).fetchall()
    events = []
    for row in rows:
        event = dict(row._mapping)
        value = event.pop("event_payload_json")
        event["event_payload"] = json.loads(value) if isinstance(value, str) else value
        events.append(event)
    return events


def _rule_body(**changes) -> dict:
    body = {
        "create_request_key": str(uuid.uuid4()),
        "kind_code": "THOROUGH_EXAMINATION",
        "class_code": "CRANE",
        "type_code": None,
        "applies_when_code": "ALWAYS",
        "jurisdiction_code": "IN-GJ",
        "effective_from": TODAY.isoformat(),
        "renew_every_months": 6,
        "basis_code": "PBL_RULE",
        "lapse_code": "BLOCK",
        "not_applicable_code": "NOT_ALLOWED",
        "not_applicable_max_months": None,
        "source": "Invented test rule for Gujarat.",
        "note": None,
    }
    body.update(changes)
    return body


# --- Reference data and the seeded rules --------------------------------------------------------------------


def test_the_jurisdictions_are_the_central_governments_sites_and_36_states_and_territories() -> None:
    body = _ok(client.get(f"{BASE}/jurisdictions", headers=auth_headers("readonly1")))
    assert len(body) == 37
    assert body[0] == {"jurisdiction_code": "IN", "jurisdiction_label": "Central government sites", "jurisdiction_kind_code": "CENTRAL", "gst_state_code": None}
    kinds = [item["jurisdiction_kind_code"] for item in body[1:]]
    assert kinds.count("STATE") == 28 and kinds.count("UNION_TERRITORY") == 8
    by_code = {item["jurisdiction_code"]: item for item in body}
    assert (by_code["IN-GJ"]["gst_state_code"], by_code["IN-MH"]["gst_state_code"], by_code["IN-DH"]["gst_state_code"]) == ("24", "27", "26")
    assert len({item["gst_state_code"] for item in body[1:]}) == 36


def test_the_eight_certificate_kinds() -> None:
    body = _ok(client.get(f"{BASE}/certificate-kinds", headers=auth_headers("readonly1")))
    assert [item["kind_code"] for item in body] == [*ROAD_PAPERS, "FITNESS", "PERMIT", "THOROUGH_EXAMINATION", "LOAD_TEST"]
    flags = {item["kind_code"]: (item["end_date_optional"], item["valid_in_required"], item["is_examination"], item["states_registration"]) for item in body}
    assert flags["ROAD_TAX"] == (True, False, False, False)
    assert flags["PERMIT"] == (False, True, False, False)
    assert flags["REGISTRATION"] == (False, False, False, True)
    assert flags["LOAD_TEST"] == (True, False, True, False)


def test_the_seeded_rules_allow_not_applicable_exactly_where_section_5_4_does() -> None:
    rules = [rule for rule in _ok(client.get(f"{BASE}/rules", params={"jurisdiction_code": "BASELINE"}, headers=auth_headers("readonly1"))) if rule["recorded_by_display_name"] is None]
    assert len(rules) == 43
    assert all(rule["effective_from"] == "2025-11-21" and rule["effective_to"] is None and rule["lapse_code"] == "BLOCK" for rule in rules)
    allowed = {(rule["kind_code"], rule["class_code"], rule["type_code"], rule["not_applicable_max_months"]) for rule in rules if rule["not_applicable_code"] == "ALLOWED"}
    expected = {("POLLUTION_UNDER_CONTROL", "CRANE", None, 12)}
    for kind in ROAD_PAPERS:
        expected |= {(kind, "CRANE", crane_type, None) for crane_type in ("CRAWLER", "DERRICK")}
        expected |= {(kind, class_code, None, None) for class_code in ("AERIAL_WORK_PLATFORM", "FORKLIFT", "EXCAVATOR")}
    assert allowed == expected
    # The law is clear for a wheeled crane: no "not applicable" for its registration, insurance or road tax.
    assert {(rule["kind_code"], rule["not_applicable_code"]) for rule in rules if rule["class_code"] == "CRANE" and rule["type_code"] is None and rule["kind_code"] in ROAD_PAPERS} == {
        ("REGISTRATION", "NOT_ALLOWED"), ("INSURANCE", "NOT_ALLOWED"), ("ROAD_TAX", "NOT_ALLOWED"), ("POLLUTION_UNDER_CONTROL", "ALLOWED")
    }
    intervals = {(rule["kind_code"], rule["class_code"], rule["type_code"]): rule["renew_every_months"] for rule in rules if rule["renew_every_months"]}
    assert intervals[("THOROUGH_EXAMINATION", "LIFTING_TACKLE", "SLING")] == 6
    assert intervals[("THOROUGH_EXAMINATION", "CRANE", None)] == 12 and intervals[("LOAD_TEST", "HOOK_BLOCK", None)] == 60
    assert {rule["basis_code"] for rule in rules if rule["kind_code"] in ("THOROUGH_EXAMINATION", "LOAD_TEST")} == {"PBL_RULE"}
    assert {(rule["kind_code"], rule["applies_when_code"]) for rule in rules if rule["kind_code"] in ("FITNESS", "PERMIT")} == {("FITNESS", "TRANSPORT_ONLY"), ("PERMIT", "TRANSPORT_ONLY")}


# --- Certificates ---------------------------------------------------------------------------------------------


def test_recording_a_certificate_and_the_same_request_twice_has_one_effect() -> None:
    fleet = Fleet()
    key = str(uuid.uuid4())
    first = _ok(_record(fleet.carrier, "INSURANCE", key=key, number="POLICY-SECRET-1", issued_by="Invented Insurer"), 201)
    assert first["replayed"] is False and first["event"]["event_name"] == "ELIGIBILITY_CERTIFICATE_RECORDED"
    again = _ok(_record(fleet.carrier, "INSURANCE", key=key, number="POLICY-SECRET-1", issued_by="Invented Insurer"), 201)
    assert again["replayed"] is True and again["event"] is None
    assert again["certificate_public_id"] == first["certificate_public_id"]
    assert len([item for item in again["certificates"]["certificates"] if item["kind_code"] == "INSURANCE"]) == 1
    # The same key for another asset, another kind, or any other field is another request: refused, not answered
    # with this one (independent review, round 1, ELG1-R1-003).
    assert "another certificate" in _detail(_record(fleet.crane, "INSURANCE", key=key), 409)
    assert "another certificate" in _detail(_record(fleet.carrier, "ROAD_TAX", key=key), 409)
    assert "another certificate" in _detail(_record(fleet.carrier, "INSURANCE", key=key, number="POLICY-SECRET-2", issued_by="Invented Insurer"), 409)
    assert "another certificate" in _detail(
        _record(fleet.carrier, "INSURANCE", key=key, number="POLICY-SECRET-1", issued_by="Invented Insurer", valid_until=TODAY + timedelta(days=10)), 409
    )
    # Events carry ids, codes and dates; never the number or the issuer.
    [event] = _events(first["certificate_public_id"])
    payload = str(event["event_payload"])
    assert "POLICY-SECRET-1" not in payload and "Invented Insurer" not in payload
    assert event["event_payload"]["kind_code"] == "INSURANCE" and event["event_payload"]["asset_public_id"] == fleet.carrier


@pytest.mark.parametrize(
    ("kind", "fields", "message"),
    [
        ("INSURANCE", {"valid_until": TODAY - timedelta(days=40)}, "cannot run out before it starts"),
        ("INSURANCE", {"valid_until": None}, "runs until"),
        ("PERMIT", {"valid_in_code": None}, "where the permit is valid"),
        ("INSURANCE", {"valid_in_code": "IN-GJ"}, "Only a permit"),
        ("REGISTRATION", {"registered_as_code": None}, "transport or a non-transport"),
        ("INSURANCE", {"registered_as_code": "TRANSPORT"}, "Only a registration"),
        ("INSURANCE", {"issued_on": TODAY + timedelta(days=1)}, "cannot be in the future"),
        ("INSURANCE", {"number": "   "}, "certificate's number"),
        ("INSURANCE", {"issued_by": ""}, "who issued it"),
        ("NOT_A_KIND", {}, "Choose a kind"),
    ],
    ids=["end-before-start", "end-missing", "permit-without-place", "place-on-insurance", "registration-without-as", "as-on-insurance", "issued-in-future", "blank-number", "blank-issuer", "unknown-kind"],
)
def test_a_certificate_is_refused(kind: str, fields: dict, message: str) -> None:
    fleet = Fleet()
    assert message in _detail(_record(fleet.carrier, kind, **fields))


def test_a_kind_no_rule_could_require_of_the_asset_is_refused() -> None:
    fleet = Fleet()
    assert "No rule requires a insurance of a hook block" in _detail(_record(fleet.hook, "INSURANCE"))
    # A carrier holds its crane's papers; a hook block holds its examinations.
    _ok(_record(fleet.carrier, "FITNESS"), 201)
    _ok(_record(fleet.hook, "LOAD_TEST"), 201)


def test_the_database_refuses_what_the_service_refuses() -> None:
    fleet = Fleet()
    columns = (
        "certificate_public_id, equipment_asset_public_id, kind_code, end_date_optional, valid_in_required, states_registration, "
        "certificate_number, issued_by, issued_on, valid_from, valid_until, valid_in_code, registered_as_code, create_request_key, "
        "recorded_by, recorded_at"
    )
    with SessionLocal() as db:
        admin = db.execute(text("SELECT public_id FROM app_user WHERE username = 'admin1'")).scalar_one()

    def insert(**changes) -> None:
        values = {
            "certificate_public_id": str(uuid.uuid4()), "equipment_asset_public_id": fleet.carrier, "kind_code": "INSURANCE",
            "end_date_optional": False, "valid_in_required": False, "states_registration": False, "certificate_number": "X",
            "issued_by": "Y", "issued_on": TODAY, "valid_from": TODAY, "valid_until": TODAY + timedelta(days=5), "valid_in_code": None,
            "registered_as_code": None, "create_request_key": str(uuid.uuid4()), "recorded_by": admin, "recorded_at": datetime.now(),
        }
        values.update(changes)
        with SessionLocal() as db:
            with pytest.raises(IntegrityError):
                db.execute(text(f"INSERT INTO eligibility_certificate ({columns}) VALUES ({', '.join(':' + name for name in values)})"), values)
            db.rollback()

    insert(valid_until=TODAY - timedelta(days=1))
    insert(valid_until=None)
    insert(valid_in_code="IN-GJ")
    insert(kind_code="REGISTRATION", states_registration=True)
    insert(kind_code="INSURANCE", end_date_optional=True, valid_until=None)
    insert(certificate_number="  ")
    with SessionLocal() as db:
        certificate = _recorded(fleet.carrier, "INSURANCE", copy=False)
        with pytest.raises(IntegrityError):
            db.execute(text("UPDATE eligibility_certificate SET certificate_status_code = 'WITHDRAWN' WHERE certificate_public_id = :id"), {"id": certificate})
        db.rollback()


def test_withdrawing_brings_the_one_before_back_and_twice_has_one_effect() -> None:
    fleet = Fleet()
    earlier = _recorded(fleet.carrier, "INSURANCE", valid_from=TODAY - timedelta(days=200), issued_on=TODAY - timedelta(days=200), valid_until=TODAY + timedelta(days=100))
    wrong = _recorded(fleet.carrier, "INSURANCE", valid_from=TODAY - timedelta(days=10), issued_on=TODAY - timedelta(days=10), valid_until=TODAY - timedelta(days=2))
    assert _status(fleet.crane, "INSURANCE")["outcome_code"] == "RUN_OUT"
    withdraw = lambda: client.post(f"{BASE}/certificates/{wrong}/withdraw", json={"reason": "Recorded by mistake: wrong dates."}, headers=auth_headers(ADMIN))
    first = _ok(withdraw())
    assert first["event"]["event_name"] == "ELIGIBILITY_CERTIFICATE_WITHDRAWN"
    # The response shows the asset the certificate is recorded on: here the carrier, which holds it for its crane.
    assert first["certificates"]["asset"]["asset_public_id"] == fleet.carrier
    status = _status(fleet.crane, "INSURANCE")
    assert status["outcome_code"] == "VALID" and status["certificate"]["certificate_public_id"] == earlier
    assert _ok(withdraw())["event"] is None
    assert [event["event_name"] for event in _events(wrong)] == ["ELIGIBILITY_CERTIFICATE_RECORDED", "ELIGIBILITY_CERTIFICATE_WITHDRAWN"]
    assert "Recorded by mistake" not in str(_events(wrong)[1]["event_payload"])
    assert "reason" in _detail(client.post(f"{BASE}/certificates/{earlier}/withdraw", json={"reason": " "}, headers=auth_headers(ADMIN)))
    assert _detail(client.post(f"{BASE}/certificates/{uuid.uuid4()}/withdraw", json={"reason": "x"}, headers=auth_headers(ADMIN)), 404)


# --- Copies ---------------------------------------------------------------------------------------------------


def test_a_certificate_counts_only_with_its_copy_which_only_the_fleet_admin_attaches() -> None:
    fleet = Fleet()
    certificate = _recorded(fleet.carrier, "INSURANCE", copy=False)
    assert _status(fleet.crane, "INSURANCE")["outcome_code"] == "COPY_MISSING"
    for username in NON_ADMIN_ROLES:
        assert _attach(certificate, username=username).status_code == 403
    _ok(_attach(certificate), 201)
    status = _status(fleet.crane, "INSURANCE")
    assert status["outcome_code"] == "VALID" and status["certificate"]["has_copy"] is True
    # Only those who may see the number may see or download the copy.
    for username in READ_ROLES:
        response = client.get(f"/api/documents/by-record/eligibility_certificate/{certificate}", headers=auth_headers(username))
        assert response.status_code == (200 if username == ADMIN else 403), username
    [copy] = _ok(client.get(f"/api/documents/by-record/eligibility_certificate/{certificate}", headers=auth_headers(ADMIN)))
    assert copy["document_type"] == "CERTIFICATE"
    assert client.get(f"/api/documents/{copy['public_id']}/content", headers=auth_headers(ADMIN)).status_code == 200
    assert client.get(f"/api/documents/{copy['public_id']}/content", headers=auth_headers("ops1")).status_code == 403


def test_only_an_uploaded_certificate_copy_is_attached_and_counts() -> None:
    """Independent review, round 1 (ELG1-R1-001): a file of another type, or a link to a file kept elsewhere, is
    refused; one that got there another way, or was archived, does not count."""
    fleet = Fleet()
    certificate = _recorded(fleet.carrier, "INSURANCE", copy=False)
    assert "document type Certificate" in _detail(_attach(certificate, document_type="OTHER"))
    link = client.post(
        "/api/documents/metadata",
        json={
            "linked_record_type": "eligibility_certificate",
            "linked_record_public_id": certificate,
            "document_type": "CERTIFICATE",
            "file_name": "copy.pdf",
            "storage_mode": "external_link",
            "storage_path_or_url": "https://example.invalid/copy.pdf",
            "status": "Linked",
        },
        headers=auth_headers(ADMIN),
    )
    assert "must be uploaded here" in _detail(link)
    assert _status(fleet.crane, "INSURANCE")["outcome_code"] == "COPY_MISSING"
    # A document of another type that reached the certificate by another way is no copy.
    with SessionLocal() as db:
        db.execute(
            text(
                "INSERT INTO document_metadata (document_public_id, document_type, linked_record_type, linked_record_public_id, "
                "file_name, original_file_name, storage_mode, storage_path_or_url, version_no, status) "
                "VALUES (:id, 'OTHER', 'eligibility_certificate', :certificate, 'x.pdf', 'x.pdf', 'external_link', 'https://example.invalid/x', 1, 'Linked')"
            ),
            {"id": str(uuid.uuid4()), "certificate": certificate},
        )
        db.commit()
    assert _status(fleet.crane, "INSURANCE")["outcome_code"] == "COPY_MISSING"
    _ok(_attach(certificate), 201)
    assert _status(fleet.crane, "INSURANCE")["outcome_code"] == "VALID"
    # Archived, it no longer counts.
    with SessionLocal() as db:
        db.execute(
            text("UPDATE document_metadata SET status = 'Archived' WHERE linked_record_public_id = :certificate AND document_type = 'CERTIFICATE'"),
            {"certificate": certificate},
        )
        db.commit()
    assert _status(fleet.crane, "INSURANCE")["outcome_code"] == "COPY_MISSING"


def test_attaching_a_copy_and_withdrawing_its_certificate_are_serialized() -> None:
    """Independent review, round 2 (ELG1-R2-001): the attach check holds the module's write lock until the
    documents module's transaction ends, so a withdrawal waits for the copy - or the copy for the withdrawal."""
    fleet = Fleet()
    certificate = _recorded(fleet.carrier, "INSURANCE", copy=False)
    lock = "SELECT pg_try_advisory_xact_lock(hashtextextended('eligibility.write', 0))"
    request = AttachRequest(certificate, "CERTIFICATE", "local_upload")
    with SessionLocal() as attaching, SessionLocal() as withdrawing:
        assert eligibility_service.certificate_copy_refusal(attaching, request) is None
        assert withdrawing.execute(text(lock)).scalar_one() is False
        withdrawing.rollback()
        attaching.rollback()
        # The other order: while a withdrawal holds the lock, the attach check waits for it and then sees it.
        assert withdrawing.execute(text(lock)).scalar_one() is True
        withdrawing.execute(
            text("UPDATE eligibility_certificate SET certificate_status_code = 'WITHDRAWN', withdrawn_reason = 'x', withdrawn_by = recorded_by, withdrawn_at = now() WHERE certificate_public_id = :id"),
            {"id": certificate},
        )
        attaching.execute(text("SET LOCAL lock_timeout = '500ms'"))
        with pytest.raises(OperationalError):
            eligibility_service.certificate_copy_refusal(attaching, request)
        attaching.rollback()
        withdrawing.commit()
        assert "withdrawn" in eligibility_service.certificate_copy_refusal(attaching, request)
        attaching.rollback()


def test_a_withdrawn_or_unknown_certificate_refuses_a_copy() -> None:
    fleet = Fleet()
    certificate = _recorded(fleet.carrier, "INSURANCE", copy=False)
    _ok(client.post(f"{BASE}/certificates/{certificate}/withdraw", json={"reason": "Wrong machine."}, headers=auth_headers(ADMIN)))
    assert "withdrawn" in _detail(_attach(certificate))
    assert "No certificate" in _detail(_attach(str(uuid.uuid4())))
    with SessionLocal() as db:
        assert db.execute(text("SELECT COUNT(*) FROM document_metadata WHERE linked_record_public_id = :id"), {"id": certificate}).scalar_one() == 0


# --- "Not applicable" -------------------------------------------------------------------------------------------


def test_a_crawler_cranes_road_papers_may_be_marked_not_applicable_and_a_wheeled_cranes_may_not() -> None:
    fleet = Fleet()
    view = _certificates(fleet.crawler)
    assert {item["kind_code"] for item in view["markable_kinds"]} == set(ROAD_PAPERS)
    for kind in ROAD_PAPERS:
        body = _ok(_mark(fleet.crawler, kind), 201)
        assert body["event"]["event_name"] == "ELIGIBILITY_NOT_APPLICABLE_RECORDED"
        assert "Tracked" not in str(body["event"]["event_payload"])
    statuses = {item["kind_code"]: item["outcome_code"] for item in _certificates(fleet.crawler)["statuses"]}
    assert all(statuses[kind] == "NOT_APPLICABLE" for kind in ROAD_PAPERS)
    # Not transport, so no fitness or permit; only the examinations stand in its way.
    assert "FITNESS" not in statuses and "PERMIT" not in statuses
    wheeled = _certificates(fleet.crane)
    assert [item["kind_code"] for item in wheeled["markable_kinds"]] == ["POLLUTION_UNDER_CONTROL"]
    for kind in ("REGISTRATION", "INSURANCE", "ROAD_TAX"):
        assert "law is clear" in _detail(_mark(fleet.crane, kind))
    # An unmapped crane is judged by the class rule: nothing but the first-year PUC.
    assert "law is clear" in _detail(_mark(fleet.unmapped, "REGISTRATION"))
    assert "already marked" in _detail(_mark(fleet.crawler, "INSURANCE"), 409)


def test_the_first_year_pollution_certificate_may_be_marked_for_at_most_twelve_months() -> None:
    fleet = Fleet()
    view = _certificates(fleet.crane)
    [puc] = view["markable_kinds"]
    limit = date.fromisoformat(puc["latest_until"])
    assert "at most 12 months" in _detail(_mark(fleet.crane, "POLLUTION_UNDER_CONTROL", reason="First year after registration."))
    assert "at most 12 months" in _detail(_mark(fleet.crane, "POLLUTION_UNDER_CONTROL", reason="First year.", until=limit + timedelta(days=1)))
    assert "past" in _detail(_mark(fleet.crane, "POLLUTION_UNDER_CONTROL", reason="First year.", until=TODAY - timedelta(days=1)))
    assert "reason" in _detail(_mark(fleet.crane, "POLLUTION_UNDER_CONTROL", reason="  ", until=limit))
    _ok(_mark(fleet.crane, "POLLUTION_UNDER_CONTROL", reason="First year after registration.", until=limit), 201)
    assert _status(fleet.crane, "POLLUTION_UNDER_CONTROL")["outcome_code"] == "NOT_APPLICABLE"


def test_withdrawing_a_mark_twice_has_one_effect_and_the_certificate_is_required_again() -> None:
    fleet = Fleet()
    key = str(uuid.uuid4())
    mark = _ok(_mark(fleet.crawler, "INSURANCE", key=key), 201)["mark_public_id"]
    assert _ok(_mark(fleet.crawler, "INSURANCE", key=key), 201)["replayed"] is True
    assert "another 'not applicable' mark" in _detail(_mark(fleet.crawler, "ROAD_TAX", key=key), 409)
    assert "another 'not applicable' mark" in _detail(_mark(fleet.crawler, "INSURANCE", key=key, reason="Another reason."), 409)
    # A kind already marked is not offered again (ELG1-R1-007).
    assert "INSURANCE" not in {item["kind_code"] for item in _certificates(fleet.crawler)["markable_kinds"]}
    withdraw = lambda: client.post(f"{BASE}/not-applicable/{mark}/withdraw", json={"reason": "It now travels on its own wheels."}, headers=auth_headers(ADMIN))
    assert _ok(withdraw())["event"]["event_name"] == "ELIGIBILITY_NOT_APPLICABLE_WITHDRAWN"
    assert _ok(withdraw())["event"] is None
    assert _status(fleet.crawler, "INSURANCE")["outcome_code"] == "MISSING"
    # A new mark may be recorded once the old one is withdrawn.
    _ok(_mark(fleet.crawler, "INSURANCE"), 201)


def test_the_database_holds_one_mark_in_force_and_its_reason() -> None:
    fleet = Fleet()
    _ok(_mark(fleet.crawler, "INSURANCE"), 201)
    with SessionLocal() as db:
        row = db.execute(text("SELECT allowed_by_rule_id, recorded_by FROM eligibility_not_applicable WHERE equipment_asset_public_id = :id"), {"id": fleet.crawler}).one()
        for reason in ("A second mark in force.", " "):
            with pytest.raises(IntegrityError):
                db.execute(
                    text(
                        "INSERT INTO eligibility_not_applicable (mark_public_id, equipment_asset_public_id, kind_code, allowed_by_rule_id, reason, "
                        "recorded_on, create_request_key, recorded_by, recorded_at) VALUES (:id, :asset, 'INSURANCE', :rule, :reason, :today, :key, :user, now())"
                    ),
                    {"id": str(uuid.uuid4()), "asset": fleet.crawler, "rule": row.allowed_by_rule_id, "reason": reason, "today": TODAY, "key": str(uuid.uuid4()), "user": row.recorded_by},
                )
            db.rollback()


# --- The check -------------------------------------------------------------------------------------------------


def test_a_wheeled_crane_is_blocked_until_its_papers_and_examinations_are_in_and_then_may_be_allocated() -> None:
    fleet = Fleet()
    blocked = _ok(_check(fleet.crane))
    assert blocked["overall_code"] == "BLOCKED" and blocked["valid_until"] is None
    # No registration yet: not a transport vehicle (the owner, 1 October 2026) - the missing registration blocks on its
    # own, and fitness and a permit are asked for once one saying transport is recorded.
    assert _outcomes(blocked) == {kind: "MISSING" for kind in (*ROAD_PAPERS, "THOROUGH_EXAMINATION", "LOAD_TEST")}
    _certify_wheeled_crane(fleet)
    allowed = _ok(_check(fleet.crane))
    assert allowed["overall_code"] == "ELIGIBLE", allowed
    assert set(_outcomes(allowed)) == {*ROAD_PAPERS, "THOROUGH_EXAMINATION", "LOAD_TEST"}
    registration = next(item for item in allowed["results"] if item["kind_code"] == "REGISTRATION")
    assert registration["asset_public_id"] == fleet.crane and registration["certificate_asset_reference"] is not None
    # The earliest end: the examination's 12 months, a day before the insurance runs out.
    assert allowed["valid_until"] == months_after(TODAY - timedelta(days=30), 12).isoformat()
    # Nothing is kept for the screen's check.
    with SessionLocal() as db:
        assert db.execute(text("SELECT COUNT(*) FROM eligibility_decision WHERE equipment_asset_public_id = :id"), {"id": fleet.crane}).scalar_one() == 0


def test_a_transport_registration_calls_for_fitness_and_a_permit_for_the_sites_state() -> None:
    fleet = Fleet()
    _certify_wheeled_crane(fleet)
    _recorded(fleet.carrier, "REGISTRATION", registered_as_code="TRANSPORT", valid_from=TODAY - timedelta(days=5), issued_on=TODAY - timedelta(days=5))
    _recorded(fleet.carrier, "FITNESS", valid_from=TODAY - timedelta(days=400), issued_on=TODAY - timedelta(days=400), valid_until=TODAY - timedelta(days=7))
    _recorded(fleet.carrier, "PERMIT", valid_in_code="IN-MH")
    check = _ok(_check(fleet.crane))
    assert check["overall_code"] == "BLOCKED"
    assert (_outcomes(check)["FITNESS"], _outcomes(check)["PERMIT"]) == ("RUN_OUT", "MISSING")
    assert _outcomes(_ok(_check(fleet.crane, state="IN-MH")))["PERMIT"] == "VALID"


def test_a_certificate_running_out_soon_or_before_or_during_the_job_warns() -> None:
    fleet = Fleet()
    _certify_wheeled_crane(fleet)
    _recorded(fleet.carrier, "INSURANCE", valid_from=TODAY, issued_on=TODAY, valid_until=TODAY + timedelta(days=10))
    soon = _ok(_check(fleet.crane, start=TODAY, end=TODAY + timedelta(days=5)))
    assert (soon["overall_code"], _outcomes(soon)["INSURANCE"]) == ("WARNING", "RUNS_OUT_SOON")
    during = _ok(_check(fleet.crane, start=TODAY + timedelta(days=5), end=TODAY + timedelta(days=40)))
    assert _outcomes(during)["INSURANCE"] == "RUNS_OUT_IN_PERIOD"
    before = _ok(_check(fleet.crane, start=TODAY + timedelta(days=20)))
    assert (before["overall_code"], _outcomes(before)["INSURANCE"]) == ("WARNING", "RUNS_OUT_BEFORE_START")
    assert before["valid_until"] == (TODAY + timedelta(days=10)).isoformat()


def test_a_crawler_marked_not_applicable_needs_only_its_examinations() -> None:
    fleet = Fleet()
    for kind in ROAD_PAPERS:
        _ok(_mark(fleet.crawler, kind), 201)
    blocked = _ok(_check(fleet.crawler))
    assert {kind: outcome for kind, outcome in _outcomes(blocked).items() if outcome != "NOT_APPLICABLE"} == {"THOROUGH_EXAMINATION": "MISSING", "LOAD_TEST": "MISSING"}
    _recorded(fleet.crawler, "THOROUGH_EXAMINATION")
    _recorded(fleet.crawler, "LOAD_TEST")
    assert _ok(_check(fleet.crawler))["overall_code"] == "ELIGIBLE"


def test_a_state_rule_is_used_at_its_sites_and_a_central_government_site_uses_in() -> None:
    fleet = Fleet()
    _certify_wheeled_crane(fleet, examined_days_ago=200)
    rule = _ok(client.post(f"{BASE}/rules", json=_rule_body(), headers=auth_headers(ADMIN)), 201)["rule"]
    gujarat = _ok(_check(fleet.crane))
    examination = next(item for item in gujarat["results"] if item["kind_code"] == "THOROUGH_EXAMINATION")
    assert (examination["rule_public_id"], examination["rule_jurisdiction_code"], examination["outcome_code"]) == (rule["rule_public_id"], "IN-GJ", "RUN_OUT")
    assert _ok(_check(fleet.crane, state="IN-MH"))["overall_code"] == "ELIGIBLE"
    # At a central-government site in Gujarat the examinations follow IN's rules, here the baseline.
    assert _ok(_check(fleet.crane, central=True))["overall_code"] == "ELIGIBLE"


def test_kit_is_checked_alone_a_retired_piece_is_blocked_and_a_carrier_is_checked_with_its_crane() -> None:
    fleet = Fleet()
    sling = _ok(_check(fleet.sling))
    assert set(_outcomes(sling)) == {"THOROUGH_EXAMINATION", "LOAD_TEST"} and sling["overall_code"] == "BLOCKED"
    _recorded(fleet.sling, "THOROUGH_EXAMINATION", issued_on=TODAY - timedelta(days=200), valid_from=TODAY - timedelta(days=200))
    _recorded(fleet.sling, "LOAD_TEST")
    # Six months for a sling, so an examination 200 days old has run out.
    assert _outcomes(_ok(_check(fleet.sling)))["THOROUGH_EXAMINATION"] == "RUN_OUT"
    piece = _machine(fleet.hook)
    _ok(client.post(f"{EQUIPMENT}/machines/{fleet.hook}/retire", json={"expected_asset_version": piece["asset_version"], "reason_code": "SCRAPPED", "retired_on": TODAY.isoformat(), "note": None}, headers=auth_headers(ADMIN)))
    retired = _ok(_check(fleet.hook))
    assert retired["overall_code"] == "BLOCKED" and retired["results"][0]["outcome_code"] == "RETIRED"
    assert "retired" in _detail(_record(fleet.hook, "LOAD_TEST"))
    assert "checked with the machine it is fitted to" in _detail(_check(fleet.carrier))


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"state_code": "IN"}, "state or union territory"),
        ({"state_code": "IN-XX"}, "state or union territory"),
        ({"period_to": (TODAY - timedelta(days=10)).isoformat()}, "cannot end before it starts"),
    ],
)
def test_a_check_is_refused(params: dict, message: str) -> None:
    fleet = Fleet()
    query = {"state_code": "IN-GJ", "period_from": TODAY.isoformat(), **params}
    assert message in _detail(client.get(f"{BASE}/assets/{fleet.crane}/check", params=query, headers=auth_headers("readonly1")))
    assert _detail(client.get(f"{BASE}/assets/{uuid.uuid4()}/check", params={"state_code": "IN-GJ", "period_from": TODAY.isoformat()}, headers=auth_headers("readonly1")), 404)


def test_an_open_ended_period_is_judged() -> None:
    fleet = Fleet()
    _certify_wheeled_crane(fleet)
    body = _ok(client.get(f"{BASE}/assets/{fleet.crane}/check", params={"state_code": "IN-GJ", "period_from": TODAY.isoformat()}, headers=auth_headers("readonly1")))
    assert body["period_to"] is None and body["overall_code"] == "WARNING"
    assert _outcomes(body)["INSURANCE"] == "RUNS_OUT_IN_PERIOD" and _outcomes(body)["ROAD_TAX"] == "VALID"


# --- The decision 8A stores -------------------------------------------------------------------------------------


def test_record_decision_stores_the_answer_its_results_and_one_event() -> None:
    fleet = Fleet()
    _certify_wheeled_crane(fleet)
    with SessionLocal() as db:
        admin = db.execute(text("SELECT public_id FROM app_user WHERE username = 'admin1'")).scalar_one()
        requirement = str(uuid.uuid4())
        decision_id, check = eligibility_service.record_decision(
            db,
            asset_public_id=fleet.crane,
            state_code="IN-GJ",
            central_government_site=False,
            period_from=TODAY + timedelta(days=3),
            period_to=TODAY + timedelta(days=33),
            requested_by=admin,
            requested_for_type="resource_requirement",
            requested_for_public_id=requirement,
        )
        db.commit()
    assert check.overall_code == "ELIGIBLE"
    with SessionLocal() as db:
        decision = db.execute(text("SELECT * FROM eligibility_decision WHERE decision_public_id = :id"), {"id": decision_id}).one()
        results = db.execute(text("SELECT * FROM eligibility_decision_result WHERE decision_id = :id ORDER BY result_number"), {"id": decision.id}).fetchall()
    assert (decision.overall_code, decision.requested_for_public_id, decision.site_state_code) == ("ELIGIBLE", requirement, "IN-GJ")
    assert len(results) == 6 and all(row.rule_id and row.certificate_id for row in results)
    [event] = _events(decision_id)
    assert event["event_name"] == "ELIGIBILITY_EVALUATED"
    assert event["event_payload"]["outcome_counts"] == {"VALID": 6}
    with SessionLocal() as db:
        with pytest.raises(eligibility_service.EligibilityValidationError):
            eligibility_service.record_decision(
                db, asset_public_id=fleet.crane, state_code="IN-GJ", central_government_site=False, period_from=TODAY, period_to=None,
                requested_by=admin, requested_for_type="resource_requirement",
            )


def test_record_decision_holds_the_write_lock_until_the_caller_ends_its_transaction() -> None:
    """Independent review, round 1 (ELG1-R1-004): no certificate, mark or rule changes between the evidence read and
    the decision stored on it."""
    fleet = Fleet()
    lock = "SELECT pg_try_advisory_xact_lock(hashtextextended('eligibility.write', 0))"
    with SessionLocal() as caller, SessionLocal() as other:
        admin = caller.execute(text("SELECT public_id FROM app_user WHERE username = 'admin1'")).scalar_one()
        eligibility_service.record_decision(
            caller, asset_public_id=fleet.crane, state_code="IN-GJ", central_government_site=False, period_from=TODAY, period_to=None, requested_by=admin
        )
        assert other.execute(text(lock)).scalar_one() is False
        other.rollback()
        caller.rollback()
        assert other.execute(text(lock)).scalar_one() is True
        other.rollback()


# --- Certificates due ------------------------------------------------------------------------------------------


def _due(**params) -> dict:
    return _ok(client.get(f"{BASE}/certificates-due", params={"limit": 500, **params}, headers=auth_headers("readonly1")))


def test_certificates_due_lists_every_band_with_counts_and_filters() -> None:
    fleet = Fleet()
    _certify_wheeled_crane(fleet, examined_days_ago=320)
    _recorded(fleet.carrier, "INSURANCE", valid_from=TODAY, issued_on=TODAY, valid_until=TODAY + timedelta(days=10))
    _recorded(fleet.carrier, "POLLUTION_UNDER_CONTROL", valid_from=TODAY, issued_on=TODAY, valid_until=TODAY + timedelta(days=25))
    _recorded(fleet.crawler, "LOAD_TEST", copy=False)
    _recorded(fleet.crawler, "THOROUGH_EXAMINATION", issued_on=TODAY - timedelta(days=400), valid_from=TODAY - timedelta(days=400))
    ending = TODAY + timedelta(days=12)
    _ok(_mark(fleet.crane, "POLLUTION_UNDER_CONTROL", reason="First year.", until=ending), 201)
    body = _due(search=f"T{fleet.sfx}-")
    mine = {(item["asset"]["asset_public_id"], item["kind_code"]): item for item in body["items"]}
    assert mine[(fleet.crane, "INSURANCE")]["band_code"] == "WITHIN_15"
    assert mine[(fleet.crane, "INSURANCE")]["certificate_asset_reference"] is not None
    # The mark ends before the certificate would: it is listed as it approaches.
    assert mine[(fleet.crane, "POLLUTION_UNDER_CONTROL")]["band_code"] == "WITHIN_15" and mine[(fleet.crane, "POLLUTION_UNDER_CONTROL")]["mark_public_id"]
    assert mine[(fleet.crane, "THOROUGH_EXAMINATION")]["band_code"] == "WITHIN_60"
    assert mine[(fleet.crawler, "LOAD_TEST")]["band_code"] == "COPY_MISSING"
    assert mine[(fleet.crawler, "THOROUGH_EXAMINATION")]["band_code"] == "RUN_OUT"
    assert mine[(fleet.crawler, "REGISTRATION")]["band_code"] == "MISSING"
    assert (fleet.crane, "LOAD_TEST") not in mine and (fleet.carrier, "INSURANCE") not in mine
    assert body["band_counts"]["MISSING"] >= 1 and sum(body["band_counts"].values()) == body["total"] == len(body["items"])
    only_run_out = _due(search=f"T{fleet.sfx}-", band="RUN_OUT")
    assert {item["band_code"] for item in only_run_out["items"]} == {"RUN_OUT"} and only_run_out["band_counts"] == body["band_counts"]
    assert {item["kind_code"] for item in _due(search=f"T{fleet.sfx}-", kind_code="LOAD_TEST")["items"]} == {"LOAD_TEST"}
    kit = _due(search=f"T{fleet.sfx}-", class_code="LIFTING_TACKLE")
    assert kit["items"] == []
    assert {item["asset"]["class_code"] for item in _due(class_code="LIFTING_TACKLE")["items"]} <= {"LIFTING_TACKLE"}
    assert "band" in _detail(client.get(f"{BASE}/certificates-due", params={"band": "SOMETIME"}, headers=auth_headers("readonly1")))
    paged = _due(search=f"T{fleet.sfx}-", limit=2, offset=1)
    assert paged["items"] == body["items"][1:3]


# --- Rules -------------------------------------------------------------------------------------------------------


def test_adding_and_ending_a_rule_and_an_overlap_refused() -> None:
    body = _rule_body()
    added = _ok(client.post(f"{BASE}/rules", json=body, headers=auth_headers(ADMIN)), 201)
    rule = added["rule"]
    assert (rule["state_code"], rule["jurisdiction_label"], added["event"]["event_name"]) == ("IN_EFFECT", "Gujarat", "ELIGIBILITY_RULE_RECORDED")
    assert "Invented test rule" not in str(added["event"]["event_payload"])
    assert _ok(client.post(f"{BASE}/rules", json=body, headers=auth_headers(ADMIN)), 201)["replayed"] is True
    for changed in ({"jurisdiction_code": "IN-MH"}, {"renew_every_months": 3}, {"source": "Another source."}, {"lapse_code": "OVERRIDE"}):
        assert "another rule" in _detail(client.post(f"{BASE}/rules", json={**body, **changed}, headers=auth_headers(ADMIN)), 409), changed
    clash = _rule_body(effective_from=(TODAY + timedelta(days=30)).isoformat())
    assert "End it first" in _detail(client.post(f"{BASE}/rules", json=clash, headers=auth_headers(ADMIN)), 409)
    end = {"effective_to": (TODAY + timedelta(days=29)).isoformat(), "reason": "Replaced by the state's final rules."}
    ended = _ok(client.post(f"{BASE}/rules/{rule['rule_public_id']}/end", json=end, headers=auth_headers(ADMIN)))
    assert ended["rule"]["effective_to"] == end["effective_to"] and ended["event"]["event_name"] == "ELIGIBILITY_RULE_ENDED"
    assert _ok(client.post(f"{BASE}/rules/{rule['rule_public_id']}/end", json=end, headers=auth_headers(ADMIN)))["replayed"] is True
    assert "already ended" in _detail(client.post(f"{BASE}/rules/{rule['rule_public_id']}/end", json={**end, "effective_to": TODAY.isoformat()}, headers=auth_headers(ADMIN)), 409)
    successor = _ok(client.post(f"{BASE}/rules", json=clash, headers=auth_headers(ADMIN)), 201)["rule"]
    assert successor["state_code"] == "NOT_YET"
    listed = _ok(client.get(f"{BASE}/rules", params={"jurisdiction_code": "IN-GJ"}, headers=auth_headers("readonly1")))
    assert {item["rule_public_id"] for item in listed} >= {rule["rule_public_id"], successor["rule_public_id"]}
    in_effect = _ok(client.get(f"{BASE}/rules", params={"jurisdiction_code": "IN-GJ", "in_effect_on": TODAY.isoformat()}, headers=auth_headers("readonly1")))
    assert rule["rule_public_id"] in {item["rule_public_id"] for item in in_effect} and successor["rule_public_id"] not in {item["rule_public_id"] for item in in_effect}


def test_the_database_refuses_overlapping_and_malformed_rules() -> None:
    with SessionLocal() as db:
        seeded = db.execute(text("SELECT * FROM eligibility_rule WHERE kind_code = 'INSURANCE' AND class_code = 'CRANE' AND type_code IS NULL AND jurisdiction_code IS NULL")).one()
    columns = "rule_public_id, kind_code, kind_is_examination, class_code, type_code, applies_when_code, jurisdiction_code, effective_from, renew_every_months, basis_code, lapse_code, not_applicable_code, not_applicable_max_months, source"

    def insert(**changes) -> None:
        values = {
            "rule_public_id": str(uuid.uuid4()), "kind_code": "INSURANCE", "kind_is_examination": False, "class_code": "CRANE", "type_code": None,
            "applies_when_code": "ALWAYS", "jurisdiction_code": None, "effective_from": date(2030, 1, 1), "renew_every_months": None,
            "basis_code": "STATUTORY", "lapse_code": "BLOCK", "not_applicable_code": "NOT_ALLOWED", "not_applicable_max_months": None, "source": "x",
        }
        values.update(changes)
        with SessionLocal() as db:
            with pytest.raises(IntegrityError):
                db.execute(text(f"INSERT INTO eligibility_rule ({columns}) VALUES ({', '.join(':' + name for name in values)})"), values)
            db.rollback()

    assert seeded.effective_to is None
    insert()  # overlaps the seeded baseline rule, which has no end
    insert(jurisdiction_code="IN-GJ", lapse_code="WARN")  # the law never only warns
    insert(jurisdiction_code="IN-GJ", source="  ")
    insert(jurisdiction_code="IN-GJ", renew_every_months=12)  # an interval on a kind that states its own end
    insert(jurisdiction_code="IN-GJ", kind_code="LOAD_TEST", kind_is_examination=True)  # an examination without one
    insert(jurisdiction_code="IN-GJ", not_applicable_max_months=12)  # a limit where no mark is allowed
    insert(jurisdiction_code="IN-GJ", kind_code="LOAD_TEST", kind_is_examination=False, renew_every_months=12)  # the kind's flag is its own
    insert(jurisdiction_code="IN-GJ", kind_code="REGISTRATION", applies_when_code="TRANSPORT_ONLY")  # a registration always applies
    insert(jurisdiction_code="IN")  # a road paper's rule for central government sites, which would never be used


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"basis_code": "STATUTORY", "lapse_code": "WARN"}, "The law always stops"),
        ({"source": " "}, "source"),
        ({"renew_every_months": None}, "how often"),
        ({"kind_code": "INSURANCE", "renew_every_months": 12}, "states its own end"),
        ({"lapse_code": "NOT_REQUIRED", "not_applicable_code": "ALLOWED"}, "Nothing is required"),
        ({"not_applicable_max_months": 6}, "needs 'not applicable'"),
        ({"type_code": "SLING"}, "type of crane"),
        ({"jurisdiction_code": "IN-XX"}, "Choose where the rule applies"),
        ({"class_code": "SPACESHIP"}, "kind of machine"),
        # The registration decides whether the transport rules apply (independent review, round 4).
        ({"kind_code": "REGISTRATION", "renew_every_months": None, "applies_when_code": "TRANSPORT_ONLY"}, "its rule applies always"),
        # Central government sites have rules of their own only for the examinations (independent review, round 5).
        ({"kind_code": "INSURANCE", "renew_every_months": None, "jurisdiction_code": "IN"}, "only the examinations have rules of their own"),
    ],
)
def test_a_rule_is_refused(changes: dict, message: str) -> None:
    assert message in _detail(client.post(f"{BASE}/rules", json=_rule_body(**changes), headers=auth_headers(ADMIN)))


def test_a_rule_cannot_end_before_it_starts() -> None:
    rule = _ok(client.post(f"{BASE}/rules", json=_rule_body(effective_from=(TODAY + timedelta(days=10)).isoformat()), headers=auth_headers(ADMIN)), 201)["rule"]
    assert "cannot end before it starts" in _detail(client.post(f"{BASE}/rules/{rule['rule_public_id']}/end", json={"effective_to": TODAY.isoformat(), "reason": "x"}, headers=auth_headers(ADMIN)))


# --- Permissions ----------------------------------------------------------------------------------------------------


def test_every_write_is_refused_to_every_role_but_admin_and_every_read_allowed() -> None:
    fleet = Fleet()
    certificate = _recorded(fleet.carrier, "INSURANCE", copy=False)
    mark = _ok(_mark(fleet.crawler, "INSURANCE"), 201)["mark_public_id"]
    rule = _ok(client.post(f"{BASE}/rules", json=_rule_body(), headers=auth_headers(ADMIN)), 201)["rule"]["rule_public_id"]
    for username in NON_ADMIN_ROLES:
        headers = auth_headers(username)
        assert _record(fleet.carrier, "ROAD_TAX", username=username).status_code == 403
        assert client.post(f"{BASE}/certificates/{certificate}/withdraw", json={"reason": "x"}, headers=headers).status_code == 403
        assert _mark(fleet.crawler, "ROAD_TAX", username=username).status_code == 403
        assert client.post(f"{BASE}/not-applicable/{mark}/withdraw", json={"reason": "x"}, headers=headers).status_code == 403
        assert client.post(f"{BASE}/rules", json=_rule_body(), headers=headers).status_code == 403
        assert client.post(f"{BASE}/rules/{rule}/end", json={"effective_to": TODAY.isoformat(), "reason": "x"}, headers=headers).status_code == 403
    for username in READ_ROLES:
        headers = auth_headers(username)
        for path in ("/jurisdictions", "/certificate-kinds", f"/assets/{fleet.crane}/certificates", "/certificates-due?limit=1", "/rules"):
            assert client.get(f"{BASE}{path}", headers=headers).status_code == 200, (username, path)
        assert _check(fleet.crane, username=username).status_code == 200
    assert client.get(f"{BASE}/rules").status_code == 401


def test_numbers_and_withdrawal_reasons_are_withheld_without_equipment_identity_read() -> None:
    fleet = Fleet()
    certificate = _recorded(fleet.carrier, "INSURANCE", number="POLICY-HIDDEN-9")
    _ok(client.post(f"{BASE}/certificates/{certificate}/withdraw", json={"reason": "Policy POLICY-HIDDEN-9 was the wrong one."}, headers=auth_headers(ADMIN)))
    # The event keeps a fixed reason: the Fleet Admin's may repeat the number (ELG1-R1-005).
    assert all("POLICY-HIDDEN-9" not in str(event) for event in _events(certificate))
    admin_view = _certificates(fleet.crane)
    [seen] = [item for item in admin_view["certificates"] if item["certificate_public_id"] == certificate]
    assert (seen["number"], seen["number_withheld"], admin_view["numbers_withheld"]) == ("POLICY-HIDDEN-9", False, False)
    assert "POLICY-HIDDEN-9" in seen["withdrawn_reason"]
    for username in NON_ADMIN_ROLES:
        view = _certificates(fleet.crane, username)
        [item] = [item for item in view["certificates"] if item["certificate_public_id"] == certificate]
        assert (item["number"], item["number_withheld"], item["withdrawn_reason"], view["numbers_withheld"]) == (None, True, None, True)
        assert item["issued_by"] == "Invented Authority" and item["has_copy"] is True
        assert "POLICY-HIDDEN-9" not in str(view)


# --- Independent review, round 6 --------------------------------------------------------------------------------------


def _count(sql: str) -> int:
    with SessionLocal() as db:
        return db.execute(text(sql)).scalar_one()


def test_a_blank_request_key_is_refused_before_anything_is_recorded() -> None:
    # ELG1-R6-002: a key of spaces passes the schema's length but not the database: refused with a message, for a
    # certificate, a mark and a rule alike, and nothing is written.
    fleet = Fleet()

    def counts() -> list[int]:
        tables = ("eligibility_certificate", "eligibility_not_applicable", "eligibility_rule")
        return [_count(f"SELECT count(*) FROM {table}") for table in tables] + [
            _count("SELECT count(*) FROM business_event WHERE source_module = 'eligibility'")
        ]

    before = counts()
    for response in (
        _record(fleet.carrier, "INSURANCE", key="   "),
        _mark(fleet.crawler, "INSURANCE", key=" "),
        client.post(f"{BASE}/rules", json=_rule_body(create_request_key="  "), headers=auth_headers(ADMIN)),
    ):
        assert "blank request key" in _detail(response)
    assert counts() == before


def test_a_marks_reasons_are_withheld_with_the_numbers_and_kept_out_of_its_events() -> None:
    # ELG1-R6-003: a reason is free text and may repeat a certificate number.
    fleet = Fleet()
    mark_id = _ok(_mark(fleet.crawler, "INSURANCE", reason="Registration RC-SECRET-42 was surrendered."), 201)["mark_public_id"]

    def mark_in(view: dict) -> dict:
        return next(item for item in view["marks"] if item["mark_public_id"] == mark_id)

    admin = mark_in(_certificates(fleet.crawler))
    assert (admin["reason"], admin["reason_withheld"]) == ("Registration RC-SECRET-42 was surrendered.", False)
    for username in NON_ADMIN_ROLES:
        view = _certificates(fleet.crawler, username)
        assert (mark_in(view)["reason"], mark_in(view)["reason_withheld"]) == (None, True)
        assert _status(fleet.crawler, "INSURANCE", username)["mark"]["reason"] is None
        assert "RC-SECRET-42" not in str(view)

    _ok(client.post(f"{BASE}/not-applicable/{mark_id}/withdraw", json={"reason": "RC-SECRET-42 is valid again."}, headers=auth_headers(ADMIN)))
    assert "RC-SECRET-42" in mark_in(_certificates(fleet.crawler))["withdrawn_reason"]
    for username in NON_ADMIN_ROLES:
        view = _certificates(fleet.crawler, username)
        assert mark_in(view)["withdrawn_reason"] is None
        assert "RC-SECRET-42" not in str(view)
    events = _events(mark_id)
    assert [event["event_name"] for event in events] == ["ELIGIBILITY_NOT_APPLICABLE_RECORDED", "ELIGIBILITY_NOT_APPLICABLE_WITHDRAWN"]
    assert all("RC-SECRET-42" not in str(event) for event in events)


def test_a_certificate_valid_until_9999_and_a_later_renewal_are_read_without_error() -> None:
    # ELG1-R7-001: 31 December 9999 is accepted and stored; a renewal taking over after today used to overflow.
    fleet = Fleet()
    _certify_wheeled_crane(fleet)
    _recorded(fleet.carrier, "INSURANCE", valid_from=TODAY - timedelta(days=10), valid_until=date(9999, 12, 31))
    # A renewal from five days ahead, its copy not yet attached: it takes over then, so the cover ends the day before.
    _ok(_record(fleet.carrier, "INSURANCE", valid_from=TODAY + timedelta(days=5), valid_until=TODAY + timedelta(days=370)), 201)
    status = _status(fleet.crane, "INSURANCE")
    assert (status["outcome_code"], status["cover_ends_on"]) == ("RUNS_OUT_SOON", (TODAY + timedelta(days=4)).isoformat())
    assert _outcomes(_ok(_check(fleet.crane)))["INSURANCE"] == "RUNS_OUT_IN_PERIOD"
    due = {(item["asset"]["asset_public_id"], item["kind_code"]): item for item in _due(search=f"T{fleet.sfx}-")["items"]}
    assert due[(fleet.crane, "INSURANCE")]["band_code"] == "WITHIN_15"


def test_a_registration_in_force_wins_over_its_mark_until_it_is_withdrawn() -> None:
    # ELG1-R7-002, the owner's decision of 28 September 2026: the check, the machine's page and Certificates due.
    fleet = Fleet()
    registration = _recorded(fleet.crawler, "REGISTRATION", registered_as_code="TRANSPORT")
    marked = _ok(_mark(fleet.crawler, "REGISTRATION", reason="Crawler: not equipped to travel on public roads."), 201)["mark_public_id"]
    outcomes = _outcomes(_ok(_check(fleet.crawler)))
    assert (outcomes["REGISTRATION"], outcomes["FITNESS"], outcomes["PERMIT"]) == ("VALID", "MISSING", "MISSING")
    row = _status(fleet.crawler, "REGISTRATION")
    assert (row["certificate"]["certificate_public_id"], row["mark"]) == (registration, None)
    assert any(item["mark_public_id"] == marked and item["mark_status_code"] == "IN_FORCE" for item in _certificates(fleet.crawler)["marks"])
    due = {(item["asset"]["asset_public_id"], item["kind_code"]): item for item in _due(search=f"T{fleet.sfx}-")["items"]}
    assert due[(fleet.crawler, "FITNESS")]["band_code"] == "MISSING"

    _ok(client.post(f"{BASE}/certificates/{registration}/withdraw", json={"reason": "Surrendered to the RTO."}, headers=auth_headers(ADMIN)))
    outcomes = _outcomes(_ok(_check(fleet.crawler)))
    assert outcomes["REGISTRATION"] == "NOT_APPLICABLE" and "FITNESS" not in outcomes and "PERMIT" not in outcomes
    assert _status(fleet.crawler, "REGISTRATION")["mark"]["mark_public_id"] == marked


def test_a_mark_may_run_as_long_as_a_states_rule_allows_and_counts_where_it_does() -> None:
    # ELG1-R8-001: all of India allows the first-year pollution certificate to be marked for 12 months; Gujarat,
    # here, for 18. An 18-month mark can be recorded, and counts in Gujarat but not in Maharashtra.
    fleet = Fleet()
    eighteen = TODAY + timedelta(days=500)
    assert "at most 12 months" in _detail(_mark(fleet.crane, "POLLUTION_UNDER_CONTROL", reason="First year.", until=eighteen))
    gujarat = _rule_body(
        kind_code="POLLUTION_UNDER_CONTROL", renew_every_months=None, basis_code="STATUTORY", not_applicable_code="ALLOWED",
        not_applicable_max_months=18, source="Invented test rule: Gujarat allows 18 months.",
    )
    rule = _ok(client.post(f"{BASE}/rules", json=gujarat, headers=auth_headers(ADMIN)), 201)["rule"]
    [puc] = _certificates(fleet.crane)["markable_kinds"]
    assert puc["rule"]["rule_public_id"] == rule["rule_public_id"]
    limit = date.fromisoformat(puc["latest_until"])
    assert limit > eighteen
    assert "at most 18 months" in _detail(_mark(fleet.crane, "POLLUTION_UNDER_CONTROL", reason="First year.", until=limit + timedelta(days=1)))
    _ok(_mark(fleet.crane, "POLLUTION_UNDER_CONTROL", reason="First year after registration.", until=eighteen), 201)
    assert _outcomes(_ok(_check(fleet.crane, state="IN-GJ")))["POLLUTION_UNDER_CONTROL"] == "NOT_APPLICABLE"
    assert _outcomes(_ok(_check(fleet.crane, state="IN-MH")))["POLLUTION_UNDER_CONTROL"] == "MISSING"
