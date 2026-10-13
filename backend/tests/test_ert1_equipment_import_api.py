"""ERT-1 - Plum's machines into the Equipment Reference, through the API.

docs/agent/slices/ert-1-plum-machines-into-the-equipment-reference.md, sections 5 to 11. Every machine,
model name and odd value here is invented and carries a run-unique token, so the tests never meet the
owner's own records in the shared database; each test removes what it created.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.equipment_reference import repository as equipment_repository
from app.modules.equipment_reference.schemas import EquipmentModelCreate
from app.modules.equipment_reference.services import models as models_service
from app.modules.equipment_reference.services.common import EquipmentConflictError
from app.shared.request_keys import request_fingerprint
from tests.business_day_test_support import TODAY, held_to_the_test_day
from tests.equipment_test_support import equipment_created_here, plum_report, plum_row, suffix
from tests.request_key_test_support import as_made_before_fingerprints, run_at_once, stored_fingerprints, user_public_id
from tests.test_commercial_offers_api import auth_headers, client

BASE = "/api/equipment-reference"
ADMIN = "admin1"
NON_ADMIN_ROLES = ("sales1", "manager1", "finance1", "ops1", "readonly1")
READ_ROLES = ("admin1",) + NON_ADMIN_ROLES


@pytest.fixture(scope="module", autouse=True)
def _on_the_test_day():
    with held_to_the_test_day():
        yield


@pytest.fixture(autouse=True)
def _remove_what_each_test_created():
    with equipment_created_here():
        yield


# --- Helpers ---------------------------------------------------------------------------------------


def _ok(response, status: int = 200) -> dict[str, Any]:
    assert response.status_code == status, response.text
    return response.json()


def _model(maker: str, name: str, class_code: str, *, type_code: str | None = None, capabilities: list | None = None) -> dict:
    body = _ok(
        client.post(
            f"{BASE}/models",
            json={
                "maker": maker,
                "model_name": name,
                "class_code": class_code,
                "type_code": type_code,
                "capabilities": capabilities or [],
                "create_request_key": str(uuid.uuid4()),
            },
            headers=auth_headers(ADMIN),
        ),
        201,
    )
    return body["model"]


def _map(source_name: str, model_public_id: str | None) -> dict:
    return _ok(
        client.put(
            f"{BASE}/model-mappings",
            json={"source_name": source_name, "model_public_id": model_public_id},
            headers=auth_headers(ADMIN),
        )
    )


def _upload(content: bytes, *, report_date: date = TODAY, username: str = ADMIN):
    return client.post(
        f"{BASE}/imports",
        data={"report_date": report_date.isoformat()},
        files={"file": ("report.csv", content, "text/csv")},
        headers=auth_headers(username),
    )


def _uploaded(content: bytes, **kwargs) -> dict:
    return _ok(_upload(content, **kwargs), 201)["equipment_import"]


def _refresh(equipment_import: dict) -> dict:
    return _ok(
        client.post(
            f"{BASE}/imports/{equipment_import['import_public_id']}/refresh",
            json={"expected_preview_version": equipment_import["preview_version"]},
            headers=auth_headers(ADMIN),
        )
    )["equipment_import"]


def _publish(equipment_import: dict, *, pairs: list | None = None, status: int = 200) -> dict:
    return _ok(
        client.post(
            f"{BASE}/imports/{equipment_import['import_public_id']}/publish",
            json={"expected_preview_version": equipment_import["preview_version"], "pairs": pairs or []},
            headers=auth_headers(ADMIN),
        ),
        status,
    )


def _rows_by_number(equipment_import: dict) -> dict[str, dict]:
    return {row["machine_number"]: row for row in equipment_import["preview"]["rows"] if row["machine_number"]}


def _flags(row: dict) -> set[tuple[str, str]]:
    return {(flag["flag_code"], flag["subject_code"]) for flag in row["flags"]}


def _machines(search: str, **params) -> list[dict]:
    return _ok(client.get(f"{BASE}/machines", params={"search": search, "limit": 200, **params}, headers=auth_headers("readonly1")))


def _machine(public_id: str, username: str = ADMIN) -> dict:
    return _ok(client.get(f"{BASE}/machines/{public_id}", headers=auth_headers(username)))


def _machine_by_number(number: str) -> dict:
    found = [item for item in _machines(number) if item["machine_number"] == number]
    assert len(found) == 1, found
    return _machine(found[0]["asset_public_id"])


def _value_rule(
    column: str, value: str, action: str, *, import_public_id: str | None = None, reason: str = "Test reading.", **results
) -> dict:
    return _ok(
        client.put(
            f"{BASE}/value-rules",
            json={
                "column_code": column,
                "plum_value": value,
                "action_code": action,
                "reason": reason,
                "import_public_id": import_public_id,
                **results,
            },
            headers=auth_headers(ADMIN),
        )
    )


def _events(record_public_id: str) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT event_name, record_type, event_payload_json, reason FROM business_event "
                "WHERE record_public_id = :id ORDER BY id"
            ),
            {"id": record_public_id},
        ).fetchall()
    return [dict(row._mapping) for row in rows]


class Fleet:
    """An invented fleet: a crane held as superstructure and carrier, a manlift, a prime mover."""

    def __init__(self) -> None:
        self.sfx = suffix()
        s = self.sfx
        self.crane_model = _model(
            "ACME", f"AC 100 {s}", "CRANE", type_code="ALL_TERRAIN", capabilities=[{"capability_code": "RATED_CAPACITY", "value": "100"}]
        )
        self.carrier_model = _model("ACME", f"AC 100 {s}", "CRANE_CARRIER")
        self.manlift_model = _model(
            "LIFTCO",
            f"LX 18 {s}",
            "AERIAL_WORK_PLATFORM",
            type_code="SCISSOR",
            capabilities=[{"capability_code": "WORKING_HEIGHT", "value": "18"}, {"capability_code": "PLATFORM_CAPACITY", "value": "230"}],
        )
        self.super_name = f"{s} ACME AC 100 SUPER"
        self.chassis_name = f"{s} ACME AC 100 CHASSIS"
        self.manlift_name = f"{s} LIFTCO LX 18"
        _map(self.super_name, self.crane_model["model_public_id"])
        _map(self.chassis_name, self.carrier_model["model_public_id"])
        _map(self.manlift_name, self.manlift_model["model_public_id"])

    def number(self, label: str) -> str:
        return f"T{self.sfx}-{label}"

    def first_report_rows(self) -> list[dict[str, str]]:
        n = self.number
        return [
            plum_row(number=n("CR1"), schedule=self.super_name, category="CRANES", capacity="100", engine=f"E-{n('CR1')}", chassis=f"C-{n('CR1')}", year="2015"),
            plum_row(number=n("CR1C"), schedule=self.chassis_name, category="CRANES", capacity="100", engine=f"E-{n('CR1C')}", chassis=f"C-{n('CR1C')}", year="2015"),
            plum_row(number=n("ML1"), schedule=self.manlift_name, category="MAN LIFTS", capacity=f"230 KG {self.sfx}", year="2019"),
            plum_row(number=n("CR2"), schedule=f"{self.sfx} MYSTERY CRANE", category="CRANES", capacity="80000", year="2012"),
            plum_row(number=n("OLD"), schedule=self.super_name, category="CRANES", status="Inactive", capacity="100"),
            plum_row(number=n("BIKE"), category="TWO WHEELER", schedule="SCOOTER"),
            plum_row(number=n("UFO"), category="SPACESHIP"),
            plum_row(number=None, category="CRANES"),
            plum_row(number=n("DUP"), category="CRANES", schedule=self.super_name, capacity="100"),
            plum_row(number=n("DUP"), category="CRANES", schedule=self.super_name, capacity="100"),
            plum_row(number=n("PM1"), category="TRAILERS", schedule=f"{self.sfx} HAULER", capacity=f"PULLER {self.sfx}", year=f"0{self.sfx}"),
            plum_row(number=n("CR3"), schedule=self.super_name, category="CRANES", capacity="120", year="2016"),
        ]


# --- Structure version 2 ---------------------------------------------------------------------------


def test_structure_version_2_adds_the_crane_carrier_as_a_part_class_offered_to_no_business_line() -> None:
    body = _ok(client.get(f"{BASE}/structure", headers=auth_headers("sales1")))
    # Version 3 (ERT-2) adds the kinds of kit after it; tests/test_ert2_detachable_kit.py checks them.
    assert body["taxonomy_version"] == 3
    carrier = next(item for item in body["classes"] if item["class_code"] == "CRANE_CARRIER")
    assert carrier["class_kind_code"] == "PART"
    assert carrier["fits_class_codes"] == ["CRANE"]
    assert carrier["kit_for_class_codes"] == []
    assert carrier["business_line_codes"] == []
    assert all(
        item["class_kind_code"] == "MACHINE"
        for item in body["classes"]
        if item["class_code"] != "CRANE_CARRIER" and item["introduced_in_version"] <= 2
    )
    crane = next(item for item in body["classes"] if item["class_code"] == "CRANE")
    assert crane["fits_class_codes"] == []


def test_the_category_rules_are_section_6_of_the_design() -> None:
    rules = {item["category"]: item for item in _ok(client.get(f"{BASE}/category-rules", headers=auth_headers("readonly1")))}
    assert (rules["CRANES"]["capability_code"], rules["CRANES"]["plum_unit_code"]) == ("RATED_CAPACITY", "TONNE")
    assert (Decimal(rules["CRANES"]["plausible_low"]), Decimal(rules["CRANES"]["plausible_high"])) == (1, 1500)
    assert (rules["MAN LIFTS"]["capability_code"], rules["MAN LIFTS"]["plum_unit_code"]) == ("PLATFORM_CAPACITY", "KILOGRAM")
    assert rules["TRAILERS"]["class_code"] == "PRIME_MOVER"
    assert (rules["TRAILERS"]["capability_code"], rules["TRAILERS"]["plum_unit_code"]) == ("GROSS_COMBINATION_WEIGHT", "KILOGRAM")
    assert rules["Excavator"]["check_code"] == "UNIT_UNCLEAR"
    assert rules["Power Packs"]["check_code"] == "NOT_CHECKED"
    assert set(rules) == {"CRANES", "CRANE", "MAN LIFTS", "FORK LIFT", "Excavator", "TRAILERS", "TRAILER BED", "HYDRAULIC AXLES", "Power Packs", "TRUCKS"}


# --- Reading the file ------------------------------------------------------------------------------


def test_a_report_without_a_used_column_is_refused_and_names_the_column() -> None:
    content = plum_report([plum_row(number=f"T{suffix()}", category="CRANES")]).replace(b"VehCategory", b"Category")
    response = _upload(content)
    assert response.status_code == 422
    assert "VehCategory" in response.json()["detail"]


def test_a_file_that_is_not_a_report_is_refused() -> None:
    response = _upload(b"hello,world\n1,2\n")
    assert response.status_code == 422
    assert "not Plum's vehicle report" in response.json()["detail"]
    assert _upload(b"").status_code == 422


def test_the_title_line_and_a_byte_order_mark_are_read_past() -> None:
    number = f"T{suffix()}-BOM"
    equipment_import = _uploaded(plum_report([plum_row(number=number, category="CRANES", capacity="50")], bom=True))
    assert _rows_by_number(equipment_import)[number]["outcome_code"] == "NEW"
    # Line 1 is the title and line 2 the header: the first machine is line 3 of the file.
    assert _rows_by_number(equipment_import)[number]["row_number"] == 3


def test_an_upload_over_five_megabytes_is_refused() -> None:
    content = plum_report([plum_row(number="X", category="CRANES")]) + b"," * (5 * 1024 * 1024)
    response = _upload(content)
    assert response.status_code == 413


def test_a_report_date_in_the_future_is_refused() -> None:
    response = _upload(plum_report([plum_row(number=f"T{suffix()}", category="CRANES")]), report_date=TODAY + timedelta(days=2))
    assert response.status_code == 422


# --- The preview -------------------------------------------------------------------------------------


def test_the_preview_reads_every_row_and_changes_nothing() -> None:
    fleet = Fleet()
    equipment_import = _uploaded(plum_report(fleet.first_report_rows()))
    assert equipment_import["import_status_code"] == "PREVIEWED"
    assert equipment_import["is_current"] is True
    rows = _rows_by_number(equipment_import)
    n = fleet.number

    assert (rows[n("CR1")]["outcome_code"], rows[n("CR1")]["kind_code"], rows[n("CR1")]["class_code"]) == ("NEW", "MACHINE", "CRANE")
    assert rows[n("CR1")]["type_code"] == "ALL_TERRAIN"
    assert rows[n("CR1")]["model_public_id"] == fleet.crane_model["model_public_id"]
    assert _flags(rows[n("CR1")]) == set()
    # The carrier's model is a Crane-carrier model, so the record is a part, not a machine.
    assert (rows[n("CR1C")]["kind_code"], rows[n("CR1C")]["class_code"]) == ("PART", "CRANE_CARRIER")
    assert _flags(rows[n("ML1")]) == {("NOT_A_NUMBER", "PLATFORM_CAPACITY")}
    assert _flags(rows[n("CR2")]) == {("MODEL_NOT_MAPPED", ""), ("OUT_OF_PATTERN", "RATED_CAPACITY")}
    assert (rows[n("OLD")]["outcome_code"], rows[n("OLD")]["reason_code"]) == ("NOT_BROUGHT_IN", "INACTIVE_NOT_KNOWN")
    assert (rows[n("BIKE")]["outcome_code"], rows[n("BIKE")]["reason_code"]) == ("NOT_BROUGHT_IN", "CLASS_NOT_USED")
    assert (rows[n("UFO")]["outcome_code"], rows[n("UFO")]["reason_code"]) == ("SET_ASIDE", "CATEGORY_NOT_MAPPED")
    assert _flags(rows[n("PM1")]) == {
        ("MODEL_NOT_MAPPED", ""),
        ("NOT_A_NUMBER", "GROSS_COMBINATION_WEIGHT"),
        ("OUT_OF_PATTERN", "COMMENCED_YEAR"),
    }
    assert _flags(rows[n("CR3")]) == {("DIFFERS_FROM_MODEL", "RATED_CAPACITY")}
    blank = [row for row in equipment_import["preview"]["rows"] if not row["machine_number"]]
    assert [(row["outcome_code"], row["reason_code"]) for row in blank] == [("SET_ASIDE", "NO_MACHINE_NUMBER")]
    duplicates = [row for row in equipment_import["preview"]["rows"] if row["machine_number"] == n("DUP")]
    assert [(row["outcome_code"], row["reason_code"]) for row in duplicates] == [("SET_ASIDE", "DUPLICATE_SOURCE_KEY")] * 2

    counts = equipment_import["counts"]
    assert (counts["NEW"], counts["NOT_BROUGHT_IN"], counts["SET_ASIDE"]) == (6, 2, 4)
    unmapped = {item["source_name"]: item for item in equipment_import["preview"]["unmapped_model_names"]}
    assert set(unmapped) == {f"{fleet.sfx} MYSTERY CRANE", f"{fleet.sfx} HAULER"}
    assert unmapped[f"{fleet.sfx} MYSTERY CRANE"]["machine_count"] == 1
    # The carrier is proposed the crane of the same maker and model name - the only one - but not paired.
    proposal = next(item for item in equipment_import["preview"]["pair_proposals"] if item["part_machine_number"] == n("CR1C"))
    assert proposal["proposed_machine_number"] is None  # CR1 and CR3 are both that model: no guess
    assert {item["machine_number"] for item in proposal["candidates"]} >= {n("CR1"), n("CR3")}

    assert _machines(fleet.sfx) == []


def test_the_carrier_is_proposed_its_crane_only_when_exactly_one_crane_of_that_model_has_none() -> None:
    fleet = Fleet()
    n = fleet.number
    rows = [row for row in fleet.first_report_rows() if row["VehicleNo"] in (n("CR1"), n("CR1C"))]
    equipment_import = _uploaded(plum_report(rows))
    proposal = next(item for item in equipment_import["preview"]["pair_proposals"] if item["part_machine_number"] == n("CR1C"))
    assert proposal["proposed_machine_number"] == n("CR1")


def test_the_fleet_admins_rules_are_applied_on_refresh() -> None:
    fleet = Fleet()
    n = fleet.number
    equipment_import = _uploaded(plum_report(fleet.first_report_rows()))
    _value_rule(
        "CAPACITY",
        f"230 KG {fleet.sfx}",
        "SPLIT_NUMBER_AND_UNIT",
        import_public_id=equipment_import["import_public_id"],
        result_number="230",
        result_unit_code="KILOGRAM",
    )
    _value_rule("CAPACITY", f"PULLER {fleet.sfx}", "REASSIGN_TO_TYPE", result_class_code="PRIME_MOVER", result_type_code="BALLAST_TRACTOR")
    _value_rule("COMMENCED_YEAR", f"0{fleet.sfx}", "NOT_A_VALUE")
    # Recording rules changed what the preview is computed from: it must be refreshed before confirming.
    stale = _ok(client.get(f"{BASE}/imports/{equipment_import['import_public_id']}", headers=auth_headers(ADMIN)))
    assert stale["is_current"] is False
    assert "Refresh" in stale["stale_reason"]

    refreshed = _refresh(equipment_import)
    assert refreshed["preview_version"] == equipment_import["preview_version"] + 1
    assert refreshed["is_current"] is True
    rows = _rows_by_number(refreshed)
    # "230 KG" is 230 kg, which is the model's platform capacity: nothing to flag.
    assert _flags(rows[n("ML1")]) == set()
    assert rows[n("ML1")]["rules_applied"]
    # "PULLER" names a ballast tractor, and there is no figure to check.
    assert rows[n("PM1")]["type_code"] == "BALLAST_TRACTOR"
    assert _flags(rows[n("PM1")]) == {("MODEL_NOT_MAPPED", "")}


def test_mapping_a_name_then_refreshing_brings_the_machine_in_with_its_model() -> None:
    fleet = Fleet()
    n = fleet.number
    equipment_import = _uploaded(plum_report(fleet.first_report_rows()))
    _map(f"{fleet.sfx} MYSTERY CRANE", fleet.crane_model["model_public_id"])
    rows = _rows_by_number(_refresh(equipment_import))
    assert rows[n("CR2")]["model_public_id"] == fleet.crane_model["model_public_id"]
    assert ("MODEL_NOT_MAPPED", "") not in _flags(rows[n("CR2")])


def test_a_model_of_another_class_is_flagged_and_not_taken() -> None:
    fleet = Fleet()
    number = fleet.number("FL1")
    equipment_import = _uploaded(plum_report([plum_row(number=number, category="FORK LIFT", schedule=fleet.super_name, capacity="5")]))
    row = _rows_by_number(equipment_import)[number]
    assert (row["class_code"], row["model_public_id"]) == ("FORKLIFT", None)
    assert ("CLASS_DISAGREES", "") in _flags(row)


# --- Confirmation --------------------------------------------------------------------------------------


def _first_published(fleet: Fleet, *, pairs: bool = True) -> dict:
    n = fleet.number
    equipment_import = _uploaded(plum_report(fleet.first_report_rows()))
    body = _publish(equipment_import, pairs=[{"part_machine_number": n("CR1C"), "machine_machine_number": n("CR1")}] if pairs else [])
    return body


def test_confirming_brings_the_machines_in_and_fits_the_confirmed_pair() -> None:
    fleet = Fleet()
    n = fleet.number
    body = _first_published(fleet)
    equipment_import = body["equipment_import"]
    assert equipment_import["import_status_code"] == "PUBLISHED"
    assert body["event"]["event_name"] == "EQUIPMENT_IMPORT_PUBLISHED"

    crane = _machine_by_number(n("CR1"))
    assert crane["asset_reference"].startswith("EQ-")
    assert (crane["asset_kind_code"], crane["class_code"], crane["type_code"]) == ("MACHINE", "CRANE", "ALL_TERRAIN")
    assert crane["model_label"] == f"ACME AC 100 {fleet.sfx}"
    assert crane["key_capability"]["capability_code"] == "RATED_CAPACITY"
    assert Decimal(crane["key_capability"]["value"]) == 100
    assert crane["facts_report_date"] == TODAY.isoformat()
    assert (crane["engine_number"], crane["chassis_number"], crane["commenced_year"]) == (f"E-{n('CR1')}", f"C-{n('CR1')}", 2015)
    assert crane["owning_company"] == "TEST OWNER"
    assert crane["details_missing"] is True
    assert [part["part"]["machine_number"] for part in crane["fitted_parts"]] == [n("CR1C")]
    assert crane["fitted_parts"][0]["fitted_on"] == TODAY.isoformat()

    carrier = _machine(crane["fitted_parts"][0]["part"]["asset_public_id"])
    assert carrier["asset_kind_code"] == "PART"
    assert carrier["fitted_to"]["machine"]["machine_number"] == n("CR1")
    assert "PART_NOT_FITTED" not in carrier["flag_codes"]

    # The inactive machine never seen, the two-wheeler, and the set-aside rows did not come in.
    for label in ("OLD", "BIKE", "UFO", "DUP"):
        assert _machines(n(label)) == []
    unmapped = _machine_by_number(n("CR2"))
    assert "MODEL_NOT_MAPPED" in unmapped["flag_codes"]
    assert unmapped["model_public_id"] is None

    # A machine list of parts only, and of flagged machines only.
    assert [item["machine_number"] for item in _machines(fleet.sfx, kind_code="PART")] == [n("CR1C")]
    assert n("CR1") not in {item["machine_number"] for item in _machines(fleet.sfx, flagged_only=True)}


def test_an_unpaired_carrier_is_flagged_part_not_fitted() -> None:
    fleet = Fleet()
    _first_published(fleet, pairs=False)
    carrier = _machine_by_number(fleet.number("CR1C"))
    assert "PART_NOT_FITTED" in carrier["flag_codes"]


def test_a_second_click_publishes_nothing_twice() -> None:
    fleet = Fleet()
    equipment_import = _uploaded(plum_report(fleet.first_report_rows()[:1]))
    first = _publish(equipment_import)
    again = _publish(equipment_import)
    assert first["event"] is not None
    assert again["event"] is None and again["replayed"] is True
    assert len(_machines(fleet.number("CR1"))) == 1
    registered = [event for event in _events(_machine_by_number(fleet.number("CR1"))["asset_public_id"]) if event["event_name"] == "EQUIPMENT_ASSET_REGISTERED"]
    assert len(registered) == 1


def test_the_same_report_again_is_refused_once_confirmed_and_returned_while_waiting() -> None:
    fleet = Fleet()
    content = plum_report(fleet.first_report_rows()[:1])
    waiting = _uploaded(content)
    replay = _ok(_upload(content), 201)
    assert replay["replayed"] is True
    assert replay["equipment_import"]["import_public_id"] == waiting["import_public_id"]
    _publish(waiting)
    refused = _upload(content)
    assert refused.status_code == 409
    assert refused.json()["detail"].startswith("This report was already imported on ")


def test_a_report_confirmed_before_the_latest_one_is_refused_too() -> None:
    fleet = Fleet()
    first = plum_report(fleet.first_report_rows()[:1])
    _publish(_uploaded(first))
    _publish(_uploaded(plum_report(fleet.first_report_rows()[:2])))
    # Not only the latest confirmed report: any confirmed report, uploaded again, would take the fleet back.
    refused = _upload(first)
    assert refused.status_code == 409
    assert refused.json()["detail"].startswith("This report was already imported on ")


def test_a_preview_made_before_another_report_was_confirmed_is_refused() -> None:
    fleet = Fleet()
    older = _uploaded(plum_report(fleet.first_report_rows()[:1]))
    newer = _uploaded(plum_report(fleet.first_report_rows()[:2]))
    _publish(newer)
    refused = client.post(
        f"{BASE}/imports/{older['import_public_id']}/publish",
        json={"expected_preview_version": older["preview_version"], "pairs": []},
        headers=auth_headers(ADMIN),
    )
    # Confirming the newer one discarded the older preview.
    assert refused.status_code == 422
    assert _ok(client.get(f"{BASE}/imports/{older['import_public_id']}", headers=auth_headers(ADMIN)))["discard_reason_code"] == "SUPERSEDED"


def test_a_preview_computed_before_a_mapping_changed_must_be_refreshed() -> None:
    fleet = Fleet()
    equipment_import = _uploaded(plum_report(fleet.first_report_rows()))
    _map(f"{fleet.sfx} MYSTERY CRANE", fleet.crane_model["model_public_id"])
    refused = client.post(
        f"{BASE}/imports/{equipment_import['import_public_id']}/publish",
        json={"expected_preview_version": equipment_import["preview_version"], "pairs": []},
        headers=auth_headers(ADMIN),
    )
    assert refused.status_code == 409
    assert "Refresh" in refused.json()["detail"]
    _publish(_refresh(equipment_import))


def test_a_stale_preview_version_is_refused() -> None:
    fleet = Fleet()
    equipment_import = _uploaded(plum_report(fleet.first_report_rows()[:1]))
    _refresh(equipment_import)
    refused = client.post(
        f"{BASE}/imports/{equipment_import['import_public_id']}/refresh",
        json={"expected_preview_version": equipment_import["preview_version"]},
        headers=auth_headers(ADMIN),
    )
    assert refused.status_code == 409


def test_a_discarded_preview_cannot_be_confirmed() -> None:
    fleet = Fleet()
    equipment_import = _uploaded(plum_report(fleet.first_report_rows()[:1]))
    discarded = _ok(
        client.post(
            f"{BASE}/imports/{equipment_import['import_public_id']}/discard",
            json={"expected_preview_version": equipment_import["preview_version"]},
            headers=auth_headers(ADMIN),
        )
    )["equipment_import"]
    assert (discarded["import_status_code"], discarded["discard_reason_code"]) == ("DISCARDED", "BY_FLEET_ADMIN")
    assert _publish(equipment_import, status=422)


def test_a_pair_that_breaks_the_rules_refuses_the_whole_confirmation() -> None:
    fleet = Fleet()
    n = fleet.number
    equipment_import = _uploaded(plum_report(fleet.first_report_rows()))
    refused = client.post(
        f"{BASE}/imports/{equipment_import['import_public_id']}/publish",
        json={
            "expected_preview_version": equipment_import["preview_version"],
            "pairs": [{"part_machine_number": n("CR1C"), "machine_machine_number": n("ML1")}],
        },
        headers=auth_headers(ADMIN),
    )
    assert refused.status_code == 422
    assert refused.json()["detail"].startswith(f"{n('CR1C')} and {n('ML1')}: ")
    assert _machines(fleet.sfx) == []


# --- A later report --------------------------------------------------------------------------------


def test_a_later_report_retires_reactivates_flags_missing_and_suspects_renumbering() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    rows = fleet.first_report_rows()
    by_number = {row["VehicleNo"]: row for row in rows}
    # CR1 is now inactive; ML1 is missing from this report altogether.
    later = [{**by_number[n("CR1")], "Status": "Inactive"}, by_number[n("CR1C")], by_number[n("CR3")]]
    retire = _publish(_uploaded(plum_report(later)))
    rows_after = _rows_by_number(retire["equipment_import"])
    assert rows_after[n("CR1")]["outcome_code"] == "RETIRED"
    crane = _machine_by_number(n("CR1"))
    assert crane["asset_status_code"] == "RETIRED"
    missing = _machine_by_number(n("ML1"))
    assert missing["asset_status_code"] == "ACTIVE"
    assert "NOT_IN_LATEST_REPORT" in missing["flag_codes"]
    assert [event["event_name"] for event in _events(crane["asset_public_id"])].count("EQUIPMENT_ASSET_RETIRED") == 1

    back = _publish(_uploaded(plum_report([by_number[n("CR1")], by_number[n("ML1")]])))
    assert _rows_by_number(back["equipment_import"])[n("CR1")]["outcome_code"] == "REACTIVATED"
    assert _machine_by_number(n("CR1"))["asset_status_code"] == "ACTIVE"
    assert "NOT_IN_LATEST_REPORT" not in _machine_by_number(n("ML1"))["flag_codes"]


def _write_details(machine: dict, version: int) -> Any:
    return client.put(
        f"{BASE}/machines/{machine['asset_public_id']}/details",
        json={"expected_asset_version": version, "serial_number": "SN-STALE", "year_of_manufacture": None},
        headers=auth_headers(ADMIN),
    )


def test_confirming_moves_the_version_of_every_machine_it_changes_and_of_no_other() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    by_number = {row["VehicleNo"]: row for row in fleet.first_report_rows()}
    crane = _machine_by_number(n("CR1"))
    corrected = _correct(crane, "OWNING_COMPANY", f"RIGHT OWNER {fleet.sfx}")["machine"]
    manlift, same = _machine_by_number(n("ML1")), _machine_by_number(n("CR3"))

    # Plum now agrees with the correction - CR1's facts do not change, only its correction closes; ML1 is
    # left out, so only a flag is raised on it; CR3 comes again exactly as before.
    later = [{**by_number[n("CR1")], "Owner": f"RIGHT OWNER {fleet.sfx}"}, by_number[n("CR3")]]
    _publish(_uploaded(plum_report(later)))

    after_crane = _machine_by_number(n("CR1"))
    assert after_crane["owning_company"] == f"RIGHT OWNER {fleet.sfx}"
    assert after_crane["corrections"][0]["closed_reason_code"] == "PLUM_AGREES"
    assert after_crane["asset_version"] > corrected["asset_version"]
    after_manlift = _machine_by_number(n("ML1"))
    assert "NOT_IN_LATEST_REPORT" in after_manlift["flag_codes"]
    assert after_manlift["asset_version"] > manlift["asset_version"]
    # A draft made against the version before is refused, not saved over what the report changed.
    assert _write_details(after_crane, corrected["asset_version"]).status_code == 409
    assert _write_details(after_manlift, manlift["asset_version"]).status_code == 409
    # A machine the report left as it was keeps its version, so a draft on it is still good.
    assert _machine_by_number(n("CR3"))["asset_version"] == same["asset_version"]
    assert _write_details(same, same["asset_version"]).status_code == 200


def test_a_new_number_carrying_a_missing_machines_chassis_is_flagged_possibly_renumbered() -> None:
    fleet = Fleet()
    n = fleet.number
    first = [plum_row(number=n("A1"), category="CRANES", schedule=fleet.super_name, capacity="100", chassis=f"CH-{fleet.sfx}")]
    _publish(_uploaded(plum_report(first)))
    second = [plum_row(number=n("A2"), category="CRANES", schedule=fleet.super_name, capacity="100", chassis=f"CH-{fleet.sfx}")]
    preview = _uploaded(plum_report(second))
    assert ("POSSIBLY_RENUMBERED", "") in _flags(_rows_by_number(preview)[n("A2")])
    assert {item["machine_number"] for item in preview["preview"]["missing"]} >= {n("A1")}


# --- Corrections -----------------------------------------------------------------------------------


def _correct(
    machine: dict, field_code: str, value: str, status: int = 201, username: str = ADMIN, reason: str = "Test correction."
) -> Any:
    response = client.post(
        f"{BASE}/machines/{machine['asset_public_id']}/corrections",
        json={"expected_asset_version": machine["asset_version"], "field_code": field_code, "corrected_value": value, "reason": reason},
        headers=auth_headers(username),
    )
    assert response.status_code == status, response.text
    return response.json()


def test_a_correction_applies_at_once_and_on_every_import_until_plum_agrees() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    crane = _machine_by_number(n("CR1"))
    corrected = _correct(crane, "ENGINE_NUMBER", f"ENG-RIGHT-{fleet.sfx}")["machine"]
    assert corrected["engine_number"] == f"ENG-RIGHT-{fleet.sfx}"
    assert corrected["asset_version"] == crane["asset_version"] + 1
    open_correction = next(item for item in corrected["corrections"] if item["correction_status_code"] == "OPEN")
    assert open_correction["plum_value"] == f"E-{n('CR1')}"
    sent = _ok(client.get(f"{BASE}/corrections", headers=auth_headers("readonly1")))
    assert open_correction["correction_public_id"] in {item["correction_public_id"] for item in sent["corrections"]}

    base = {row["VehicleNo"]: row for row in fleet.first_report_rows()}[n("CR1")]
    # Plum unchanged: the correction still applies.
    unchanged = _publish(_uploaded(plum_report([{**base, "Capacity": "100.0"}])))["equipment_import"]
    assert _machine_by_number(n("CR1"))["engine_number"] == f"ENG-RIGHT-{fleet.sfx}"
    assert _rows_by_number(unchanged)[n("CR1")]["corrections"][0]["effect_code"] == "APPLIED"

    # Plum changes to a third value: still applied, and flagged for the Fleet Admin.
    third = _publish(_uploaded(plum_report([{**base, "EngineNo": f"E-THIRD-{fleet.sfx}"}])))["equipment_import"]
    assert ("PLUM_CHANGED_CORRECTED_VALUE", "ENGINE_NUMBER") in _flags(_rows_by_number(third)[n("CR1")])
    after_third = _machine_by_number(n("CR1"))
    assert after_third["engine_number"] == f"ENG-RIGHT-{fleet.sfx}"
    assert "PLUM_CHANGED_CORRECTED_VALUE" in after_third["flag_codes"]

    # Plum takes the corrected value: the correction closes itself.
    agrees = _publish(_uploaded(plum_report([{**base, "EngineNo": f"ENG-RIGHT-{fleet.sfx}"}])))
    assert agrees["event"]["event_payload"]["corrections_closed"] == 1
    closed = _machine_by_number(n("CR1"))
    assert closed["engine_number"] == f"ENG-RIGHT-{fleet.sfx}"
    assert all(item["correction_status_code"] == "CLOSED" for item in closed["corrections"])
    assert closed["corrections"][0]["closed_reason_code"] == "PLUM_AGREES"
    assert "PLUM_CHANGED_CORRECTED_VALUE" not in closed["flag_codes"]
    sent = _ok(client.get(f"{BASE}/corrections", headers=auth_headers("readonly1")))
    assert open_correction["correction_public_id"] not in {item["correction_public_id"] for item in sent["corrections"]}


def test_correcting_the_category_moves_the_machine_to_its_class_at_once() -> None:
    fleet = Fleet()
    n = fleet.number
    number = n("FL9")
    _publish(_uploaded(plum_report([plum_row(number=number, category="FORK LIFT", schedule=fleet.super_name, capacity="5")])))
    machine = _machine_by_number(number)
    assert "CLASS_DISAGREES" in machine["flag_codes"]
    corrected = _correct(machine, "CATEGORY", "CRANE")["machine"]
    assert (corrected["class_code"], corrected["model_public_id"]) == ("CRANE", fleet.crane_model["model_public_id"])
    assert "CLASS_DISAGREES" not in corrected["flag_codes"]


def test_the_preview_names_every_correction_and_reading_a_row_was_read_with_but_no_identity_number() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    crane = _machine_by_number(n("CR1"))
    crane = _correct(crane, "OWNING_COMPANY", f"RIGHT OWNER {fleet.sfx}")["machine"]
    _correct(crane, "ENGINE_NUMBER", f"ENG-RIGHT-{fleet.sfx}")
    _value_rule("CAPACITY", f"230 KG {fleet.sfx}", "SPLIT_NUMBER_AND_UNIT", result_number="230", result_unit_code="KILOGRAM")
    _value_rule("CHASSIS_NUMBER", f"NIL {fleet.sfx}", "NOT_A_VALUE")
    by_number = {row["VehicleNo"]: row for row in fleet.first_report_rows()}
    later = [by_number[n("CR1")], {**by_number[n("ML1")], "ChassisNo": f"NIL {fleet.sfx}"}]
    rows = _rows_by_number(_uploaded(plum_report(later)))

    crane_row = rows[n("CR1")]
    # Nothing about CR1 changes and no flag is left, yet it is shown: it is read with two corrections.
    assert (crane_row["outcome_code"], crane_row["flags"], crane_row["needs_attention"]) == ("UNCHANGED", [], True)
    corrections = {item["field_code"]: item for item in crane_row["corrections"]}
    assert (corrections["OWNING_COMPANY"]["effect_code"], corrections["OWNING_COMPANY"]["corrected_value_label"]) == (
        "APPLIED",
        f"RIGHT OWNER {fleet.sfx}",
    )
    assert (corrections["ENGINE_NUMBER"]["effect_code"], corrections["ENGINE_NUMBER"]["corrected_value_label"]) == ("APPLIED", None)

    manlift_row = rows[n("ML1")]
    assert manlift_row["needs_attention"] is True
    readings = {item["column_code"]: item for item in manlift_row["rules_applied"]}
    assert (readings["CAPACITY"]["action_code"], readings["CAPACITY"]["plum_value"]) == ("SPLIT_NUMBER_AND_UNIT", f"230 KG {fleet.sfx}")
    assert (Decimal(readings["CAPACITY"]["result_number"]), readings["CAPACITY"]["result_unit_code"]) == (230, "KILOGRAM")
    # A reading of a chassis number is named, but the value it reads is not repeated.
    assert (readings["CHASSIS_NUMBER"]["action_code"], readings["CHASSIS_NUMBER"]["plum_value"]) == ("NOT_A_VALUE", None)


def test_the_machine_number_cannot_be_corrected_and_an_unknown_field_is_refused() -> None:
    fleet = Fleet()
    _first_published(fleet)
    crane = _machine_by_number(fleet.number("CR1"))
    assert "machine number" in _correct(crane, "MACHINE_NUMBER", "X", status=422)["detail"]
    assert _correct(crane, "COMMENCED_YEAR", "15", status=422)
    assert _correct(crane, "STATUS", "Sold", status=422)
    assert _correct(crane, "CAPACITY", "a lot", status=422)
    assert _correct(crane, "MODEL", str(uuid.uuid4()), status=422)
    assert "already holds" in _correct(crane, "ENGINE_NUMBER", f"E-{fleet.number('CR1')}", status=422)["detail"]


def test_a_stale_version_is_refused_on_a_correction() -> None:
    fleet = Fleet()
    _first_published(fleet)
    crane = _machine_by_number(fleet.number("CR1"))
    _correct(crane, "OWNING_COMPANY", "TEST OWNER TWO")
    assert _correct(crane, "OWNING_COMPANY", "TEST OWNER THREE", status=409)


def test_closing_a_correction_reads_the_machine_as_plum_gives_it_again() -> None:
    fleet = Fleet()
    _first_published(fleet)
    crane = _machine_by_number(fleet.number("CR1"))
    corrected = _correct(crane, "COMMENCED_YEAR", "2014")["machine"]
    assert corrected["commenced_year"] == 2014
    correction = corrected["corrections"][0]
    reopened = _ok(
        client.post(
            f"{BASE}/machines/{crane['asset_public_id']}/corrections/{correction['correction_public_id']}/close",
            json={"expected_asset_version": corrected["asset_version"]},
            headers=auth_headers(ADMIN),
        )
    )["machine"]
    assert reopened["commenced_year"] == 2015
    assert reopened["corrections"][0]["closed_reason_code"] == "BY_FLEET_ADMIN"


# --- Details, own values, models -------------------------------------------------------------------


def test_details_plum_does_not_hold_are_the_platforms_and_survive_every_import() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    crane = _machine_by_number(n("CR1"))
    detailed = _ok(
        client.put(
            f"{BASE}/machines/{crane['asset_public_id']}/details",
            json={"expected_asset_version": crane["asset_version"], "serial_number": f"SN-{fleet.sfx}", "year_of_manufacture": 2014},
            headers=auth_headers(ADMIN),
        )
    )["machine"]
    assert (detailed["serial_number"], detailed["year_of_manufacture"], detailed["details_missing"]) == (f"SN-{fleet.sfx}", 2014, False)
    assert n("CR1") not in {item["machine_number"] for item in _machines(fleet.sfx, details_to_complete=True)}
    base = {row["VehicleNo"]: row for row in fleet.first_report_rows()}[n("CR1")]
    _publish(_uploaded(plum_report([{**base, "EngineNo": f"E2-{fleet.sfx}"}])))
    after = _machine_by_number(n("CR1"))
    assert (after["serial_number"], after["year_of_manufacture"]) == (f"SN-{fleet.sfx}", 2014)
    assert after["engine_number"] == f"E2-{fleet.sfx}"


def test_a_machines_own_value_overrides_its_model_and_is_what_plums_figure_is_checked_against() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    crane = _machine_by_number(n("CR3"))
    assert "DIFFERS_FROM_MODEL" in crane["flag_codes"]
    own = _ok(
        client.put(
            f"{BASE}/machines/{crane['asset_public_id']}/capabilities",
            json={
                "expected_asset_version": crane["asset_version"],
                "capabilities": [{"capability_code": "RATED_CAPACITY", "value": "120", "reason": "Re-rated after its test."}],
            },
            headers=auth_headers(ADMIN),
        )
    )["machine"]
    rated = next(item for item in own["capabilities"] if item["capability_code"] == "RATED_CAPACITY")
    assert (Decimal(rated["value"]), rated["source_code"], rated["reason"]) == (120, "OWN", "Re-rated after its test.")
    base = {row["VehicleNo"]: row for row in fleet.first_report_rows()}[n("CR3")]
    preview = _uploaded(plum_report([{**base, "EngineNo": "changed"}]))
    assert ("DIFFERS_FROM_MODEL", "RATED_CAPACITY") not in _flags(_rows_by_number(preview)[n("CR3")])
    missing_reason = client.put(
        f"{BASE}/machines/{crane['asset_public_id']}/capabilities",
        json={"expected_asset_version": own["asset_version"], "capabilities": [{"capability_code": "RATED_CAPACITY", "value": "90", "reason": " "}]},
        headers=auth_headers(ADMIN),
    )
    assert missing_reason.status_code == 422


def _set_own(machine: dict, value: str, version: int) -> dict:
    return _ok(
        client.put(
            f"{BASE}/machines/{machine['asset_public_id']}/capabilities",
            json={"expected_asset_version": version, "capabilities": [{"capability_code": "RATED_CAPACITY", "value": value, "reason": "Re-rated."}]},
            headers=auth_headers(ADMIN),
        )
    )["machine"]


def test_an_own_value_clears_or_raises_the_differs_flag_at_once() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    crane = _machine_by_number(n("CR3"))  # Plum says 120; its model is rated 100
    assert "DIFFERS_FROM_MODEL" in crane["flag_codes"]
    agrees = _set_own(crane, "120", crane["asset_version"])
    assert "DIFFERS_FROM_MODEL" not in agrees["flag_codes"]
    assert n("CR3") not in {item["machine_number"] for item in _machines(fleet.sfx, flagged_only=True)}
    differs = _set_own(agrees, "90", agrees["asset_version"])
    assert ("DIFFERS_FROM_MODEL", "RATED_CAPACITY") in {(flag["flag_code"], flag["subject_code"]) for flag in differs["flags"]}
    assert differs["asset_version"] == agrees["asset_version"] + 1


def test_changing_a_models_rating_or_type_re_reads_its_machines_at_once() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    model = fleet.crane_model
    cr1, cr3 = _machine_by_number(n("CR1")), _machine_by_number(n("CR3"))
    assert "DIFFERS_FROM_MODEL" not in cr1["flag_codes"] and "DIFFERS_FROM_MODEL" in cr3["flag_codes"]
    _ok(
        client.put(
            f"{BASE}/models/{model['model_public_id']}",
            json={
                "maker": "ACME",
                "model_name": model["model_name"],
                "class_code": "CRANE",
                "type_code": "CRAWLER",
                "capabilities": [{"capability_code": "RATED_CAPACITY", "value": "120"}],
                "expected_model_version": model["model_version"],
            },
            headers=auth_headers(ADMIN),
        )
    )
    # Plum's 100 for CR1 now differs from the rating; CR3's 120 now agrees. Both are crawlers now.
    after_cr1, after_cr3 = _machine_by_number(n("CR1")), _machine_by_number(n("CR3"))
    assert "DIFFERS_FROM_MODEL" in after_cr1["flag_codes"]
    assert "DIFFERS_FROM_MODEL" not in after_cr3["flag_codes"]
    assert (after_cr1["type_code"], after_cr3["type_code"]) == ("CRAWLER", "CRAWLER")
    assert after_cr1["asset_version"] > cr1["asset_version"] and after_cr3["asset_version"] > cr3["asset_version"]
    assert _write_details(after_cr1, cr1["asset_version"]).status_code == 409
    changed = [event for event in _events(cr1["asset_public_id"]) if event["event_name"] == "EQUIPMENT_ASSET_CHANGED"]
    assert changed and json.loads(changed[-1]["event_payload_json"])["changed_facts"] == ["type_code"]

    # A new name changes no fact and no flag, but every machine shows its model's name: each moves on.
    current = _ok(client.get(f"{BASE}/models", headers=auth_headers(ADMIN)))
    [model_now] = [item for item in current if item["model_public_id"] == model["model_public_id"]]
    _ok(
        client.put(
            f"{BASE}/models/{model['model_public_id']}",
            json={
                "maker": "ACME",
                "model_name": f"AC 100 NEW {fleet.sfx}",
                "class_code": "CRANE",
                "type_code": "CRAWLER",
                "capabilities": [{"capability_code": "RATED_CAPACITY", "value": "120"}],
                "expected_model_version": model_now["model_version"],
            },
            headers=auth_headers(ADMIN),
        )
    )
    renamed = _machine_by_number(n("CR3"))
    assert renamed["model_label"] == f"ACME AC 100 NEW {fleet.sfx}"
    assert renamed["flag_codes"] == after_cr3["flag_codes"]
    assert renamed["asset_version"] == after_cr3["asset_version"] + 1


def test_a_models_rating_is_read_by_its_machines_and_its_class_cannot_change_while_used() -> None:
    fleet = Fleet()
    _first_published(fleet)
    model = fleet.crane_model
    changed = _ok(
        client.put(
            f"{BASE}/models/{model['model_public_id']}",
            json={
                "maker": "ACME",
                "model_name": model["model_name"],
                "class_code": "CRANE",
                "type_code": "ALL_TERRAIN",
                "capabilities": [{"capability_code": "RATED_CAPACITY", "value": "110"}],
                "expected_model_version": model["model_version"],
            },
            headers=auth_headers(ADMIN),
        )
    )["model"]
    assert changed["model_version"] == model["model_version"] + 1
    assert Decimal(_machine_by_number(fleet.number("CR1"))["key_capability"]["value"]) == 110
    refused = client.put(
        f"{BASE}/models/{model['model_public_id']}",
        json={
            "maker": "ACME",
            "model_name": model["model_name"],
            "class_code": "FORKLIFT",
            "capabilities": [],
            "expected_model_version": changed["model_version"],
        },
        headers=auth_headers(ADMIN),
    )
    assert refused.status_code == 422
    assert "cannot change" in refused.json()["detail"]


def test_models_refuse_duplicates_wrong_capabilities_and_replay_a_request_key() -> None:
    sfx = suffix()
    key = str(uuid.uuid4())
    payload = {"maker": "ZED", "model_name": f"Z {sfx}", "class_code": "FORKLIFT", "capabilities": [{"capability_code": "RATED_CAPACITY", "value": "3"}], "create_request_key": key}
    first = _ok(client.post(f"{BASE}/models", json=payload, headers=auth_headers(ADMIN)), 201)
    replay = _ok(client.post(f"{BASE}/models", json=payload, headers=auth_headers(ADMIN)), 201)
    assert first["replayed"] is False and first["event"] is not None
    assert replay["event"] is None and replay["replayed"] is True
    assert replay["model"]["model_public_id"] == first["model"]["model_public_id"]
    duplicate = client.post(f"{BASE}/models", json={**payload, "maker": " zed ", "create_request_key": str(uuid.uuid4())}, headers=auth_headers(ADMIN))
    assert duplicate.status_code == 409
    wrong = client.post(
        f"{BASE}/models",
        json={**payload, "model_name": f"Y {sfx}", "create_request_key": str(uuid.uuid4()), "capabilities": [{"capability_code": "WORKING_HEIGHT", "value": "3"}]},
        headers=auth_headers(ADMIN),
    )
    assert wrong.status_code == 422
    with_unit = client.post(
        f"{BASE}/models",
        json={**payload, "create_request_key": str(uuid.uuid4()), "capabilities": [{"capability_code": "RATED_CAPACITY", "value": "3", "unit_code": "KILOGRAM"}]},
        headers=auth_headers(ADMIN),
    )
    assert with_unit.status_code == 422


def _models_with_key(key: str) -> list[dict]:
    with SessionLocal() as db:
        return [
            dict(row)
            for row in db.execute(
                text("SELECT model_public_id::text AS model_public_id, maker, model_name FROM equipment_model WHERE create_request_key = :key"), {"key": key}
            ).mappings()
        ]


def test_a_used_model_key_with_a_changed_request_is_refused() -> None:
    """The defect TB-1 found (TB1-305): a model form whose first save was recorded but whose reply was lost, then
    edited and saved again, got the FIRST model back with 201 - the screen said nothing changed and the edit was
    dropped. Now the changed request is refused (409), saying the form already recorded a model."""
    sfx = suffix()
    key = str(uuid.uuid4())
    payload = {"maker": "ZED", "model_name": f"Z {sfx}", "class_code": "FORKLIFT", "capabilities": [{"capability_code": "RATED_CAPACITY", "value": "3"}], "create_request_key": key}
    first = _ok(client.post(f"{BASE}/models", json=payload, headers=auth_headers(ADMIN)), 201)["model"]
    for changed in (
        {"model_name": f"Z {sfx} B"},
        {"capabilities": [{"capability_code": "RATED_CAPACITY", "value": "4"}]},
        {"maker_part_number": "PN-1"},
        {"type_code": None},
    ):
        refused = client.post(f"{BASE}/models", json={**payload, **changed}, headers=auth_headers(ADMIN))
        assert refused.status_code == 409, (changed, refused.text)
        assert refused.json()["detail"] == models_service.MODEL_KEY_USED
    assert _models_with_key(key) == [{"model_public_id": first["model_public_id"], "maker": "ZED", "model_name": f"Z {sfx}"}]
    assert stored_fingerprints("equipment_model", key) == [request_fingerprint(EquipmentModelCreate(**payload))]


def test_a_model_key_recorded_before_fingerprints_is_refused_never_replayed() -> None:
    """A model made before migration 0050 has no fingerprint: its key is refused even with the same body, never
    taken for a request it may not have been."""
    key = str(uuid.uuid4())
    payload = {"maker": "ZED", "model_name": f"Z {suffix()}", "class_code": "FORKLIFT", "capabilities": [], "create_request_key": key}
    _ok(client.post(f"{BASE}/models", json=payload, headers=auth_headers(ADMIN)), 201)
    as_made_before_fingerprints("equipment_model", key)
    again = client.post(f"{BASE}/models", json=payload, headers=auth_headers(ADMIN))
    assert again.status_code == 409, again.text
    assert again.json()["detail"] == models_service.MODEL_KEY_USED
    assert len(_models_with_key(key)) == 1


def _models_at_once(monkeypatch, payloads: list[dict]) -> list[tuple[str, Any]]:
    actor = user_public_id(ADMIN)
    return run_at_once(
        monkeypatch,
        equipment_repository,
        "find_model_by_create_request_key",
        [
            lambda db, payload=payload: models_service.create_model(db, payload=EquipmentModelCreate(**payload), user_public_id=actor)
            for payload in payloads
        ],
    )


def test_two_model_saves_at_once_with_one_key_record_one_model(monkeypatch) -> None:
    payload = {"maker": "ZED", "model_name": f"Z {suffix()}", "class_code": "FORKLIFT", "capabilities": [], "create_request_key": str(uuid.uuid4())}
    results = _models_at_once(monkeypatch, [payload, dict(payload)])
    assert [outcome for outcome, _ in results] == ["ok", "ok"], results
    answers = [answer for _, answer in results]
    assert answers[0].model.model_public_id == answers[1].model.model_public_id
    assert sorted(answer.replayed for answer in answers) == [False, True]
    assert sorted(answer.event is None for answer in answers) == [False, True]
    assert len(_models_with_key(payload["create_request_key"])) == 1


def test_two_model_saves_at_once_with_one_key_and_different_requests_record_one(monkeypatch) -> None:
    sfx = suffix()
    payload = {"maker": "ZED", "model_name": f"Z {sfx}", "class_code": "FORKLIFT", "capabilities": [], "create_request_key": str(uuid.uuid4())}
    results = _models_at_once(monkeypatch, [payload, {**payload, "model_name": f"Z {sfx} B"}])
    assert sorted(outcome for outcome, _ in results) == ["error", "ok"], results
    refused = next(value for outcome, value in results if outcome == "error")
    assert isinstance(refused, EquipmentConflictError) and str(refused) == models_service.MODEL_KEY_USED
    assert len(_models_with_key(payload["create_request_key"])) == 1


def test_a_retired_model_cannot_be_newly_mapped_and_a_mapping_can_be_removed() -> None:
    fleet = Fleet()
    model = fleet.manlift_model
    retired = _ok(
        client.put(
            f"{BASE}/models/{model['model_public_id']}",
            json={
                "maker": model["maker"],
                "model_name": model["model_name"],
                "class_code": model["class_code"],
                "type_code": model["type_code"],
                "capabilities": [{"capability_code": item["capability_code"], "value": item["value"]} for item in model["capabilities"]],
                "is_retired": True,
                "expected_model_version": model["model_version"],
            },
            headers=auth_headers(ADMIN),
        )
    )["model"]
    assert retired["is_retired"] is True
    refused = client.put(f"{BASE}/model-mappings", json={"source_name": f"{fleet.sfx} OTHER", "model_public_id": model["model_public_id"]}, headers=auth_headers(ADMIN))
    assert refused.status_code == 422
    removed = _map(fleet.manlift_name, None)
    assert removed["model_public_id"] is None and removed["event"]["event_name"] == "EQUIPMENT_MODEL_MAPPED"
    assert _map(fleet.manlift_name, None)["event"] is None


# --- Parts ---------------------------------------------------------------------------------------------


def test_a_part_is_fitted_to_one_machine_at_a_time_and_a_removed_link_keeps_its_history() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet, pairs=False)
    crane, carrier = _machine_by_number(n("CR1")), _machine_by_number(n("CR1C"))
    fitted = _ok(
        client.post(
            f"{BASE}/machines/{crane['asset_public_id']}/fitted-parts",
            json={"expected_asset_version": crane["asset_version"], "part_public_id": carrier["asset_public_id"], "expected_part_version": carrier["asset_version"], "fitted_on": TODAY.isoformat()},
            headers=auth_headers(ADMIN),
        ),
        201,
    )["machine"]
    assert [item["part"]["asset_public_id"] for item in fitted["fitted_parts"]] == [carrier["asset_public_id"]]
    assert "PART_NOT_FITTED" not in _machine(carrier["asset_public_id"])["flag_codes"]
    other = _machine_by_number(n("CR3"))
    twice = client.post(
        f"{BASE}/machines/{other['asset_public_id']}/fitted-parts",
        json={"expected_asset_version": other["asset_version"], "part_public_id": carrier["asset_public_id"], "expected_part_version": carrier["asset_version"] + 1, "fitted_on": TODAY.isoformat()},
        headers=auth_headers(ADMIN),
    )
    assert twice.status_code == 422
    removed = _ok(
        client.post(
            f"{BASE}/machines/{crane['asset_public_id']}/fitted-parts/{carrier['asset_public_id']}/remove",
            json={"expected_asset_version": fitted["asset_version"], "expected_part_version": fitted["fitted_parts"][0]["part"]["asset_version"], "removed_on": TODAY.isoformat()},
            headers=auth_headers(ADMIN),
        )
    )["machine"]
    assert removed["fitted_parts"] == []
    assert [item["removed_on"] for item in removed["link_history"]] == [TODAY.isoformat()]
    assert "PART_NOT_FITTED" in _machine(carrier["asset_public_id"])["flag_codes"]
    machine_to_machine = client.post(
        f"{BASE}/machines/{crane['asset_public_id']}/fitted-parts",
        json={"expected_asset_version": removed["asset_version"], "part_public_id": other["asset_public_id"], "expected_part_version": other["asset_version"], "fitted_on": TODAY.isoformat()},
        headers=auth_headers(ADMIN),
    )
    assert machine_to_machine.status_code == 422


def _fit(machine: dict, part: dict, *, part_version: int) -> Any:
    return client.post(
        f"{BASE}/machines/{machine['asset_public_id']}/fitted-parts",
        json={
            "expected_asset_version": machine["asset_version"],
            "part_public_id": part["asset_public_id"],
            "expected_part_version": part_version,
            "fitted_on": TODAY.isoformat(),
        },
        headers=auth_headers(ADMIN),
    )


def _remove(machine: dict, part: dict, *, part_version: int) -> Any:
    return client.post(
        f"{BASE}/machines/{machine['asset_public_id']}/fitted-parts/{part['asset_public_id']}/remove",
        json={"expected_asset_version": machine["asset_version"], "expected_part_version": part_version, "removed_on": TODAY.isoformat()},
        headers=auth_headers(ADMIN),
    )


def test_a_part_changed_since_it_was_read_or_retired_is_not_fitted_or_removed_unseen() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet, pairs=False)
    crane, carrier = _machine_by_number(n("CR1")), _machine_by_number(n("CR1C"))
    changed = _correct(carrier, "OWNING_COMPANY", f"OTHER OWNER {fleet.sfx}")["machine"]
    assert _fit(crane, carrier, part_version=carrier["asset_version"]).status_code == 409
    assert _machine(crane["asset_public_id"])["fitted_parts"] == []

    fitted = _ok(_fit(crane, changed, part_version=changed["asset_version"]), 201)["machine"]
    part_now = fitted["fitted_parts"][0]["part"]
    assert part_now["asset_version"] == changed["asset_version"] + 1
    assert _remove(fitted, carrier, part_version=changed["asset_version"]).status_code == 409
    removed = _ok(_remove(fitted, carrier, part_version=part_now["asset_version"]))["machine"]
    assert removed["fitted_parts"] == []

    # The part is retired - here by a correction of its status - and is not fitted anew.
    retired = _correct(_machine(carrier["asset_public_id"]), "STATUS", "INACTIVE")["machine"]
    assert retired["asset_status_code"] == "RETIRED"
    refused = _fit(removed, retired, part_version=retired["asset_version"])
    assert refused.status_code == 422
    assert "retired" in refused.json()["detail"]


def test_a_correction_that_changes_a_machines_class_removes_a_part_that_no_longer_fits_it() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    crane, carrier = _machine_by_number(n("CR1")), _machine_by_number(n("CR1C"))
    assert [item["part"]["machine_number"] for item in crane["fitted_parts"]] == [n("CR1C")]
    # Still a machine, but a forklift now: a crane carrier is not fitted to a forklift.
    forklift = _correct(crane, "CATEGORY", "FORKLIFT")["machine"]
    assert (forklift["asset_kind_code"], forklift["class_code"]) == ("MACHINE", "FORKLIFT")
    assert forklift["fitted_parts"] == []
    assert [(item["part"]["machine_number"], item["removed_on"]) for item in forklift["link_history"]] == [(n("CR1C"), TODAY.isoformat())]
    unfitted = _machine(carrier["asset_public_id"])
    assert "PART_NOT_FITTED" in unfitted["flag_codes"] and unfitted["fitted_to"] is None
    assert unfitted["asset_version"] > carrier["asset_version"]
    removed = [event for event in _events(crane["asset_public_id"]) if event["event_name"] == "EQUIPMENT_PART_REMOVED"]
    assert json.loads(removed[-1]["event_payload_json"])["because"] == "CLASS_CHANGED"


def test_a_correction_that_makes_a_machine_a_part_leaves_its_links_and_flags_both_parts_at_once() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    crane, carrier = _machine_by_number(n("CR1")), _machine_by_number(n("CR1C"))
    # Its model is corrected to the carrier's: the record is a crane carrier, a part, not a machine.
    now_part = _correct(crane, "MODEL", fleet.carrier_model["model_public_id"])["machine"]
    assert (now_part["asset_kind_code"], now_part["class_code"]) == ("PART", "CRANE_CARRIER")
    assert "PART_NOT_FITTED" in now_part["flag_codes"]
    other = _machine(carrier["asset_public_id"])
    assert "PART_NOT_FITTED" in other["flag_codes"] and other["fitted_to"] is None
    assert other["asset_version"] > carrier["asset_version"]
    # Both are offered for pairing again: the machine page lists unfitted parts by that flag.
    unfitted = {item["machine_number"] for item in _machines(fleet.sfx, kind_code="PART", flagged_only=True) if "PART_NOT_FITTED" in item["flag_codes"]}
    assert unfitted >= {n("CR1"), n("CR1C")}


def test_the_preview_shows_a_part_a_report_will_unfit_and_confirmation_closes_exactly_that() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    by_number = {row["VehicleNo"]: row for row in fleet.first_report_rows()}
    # Plum now calls the crane a forklift: its carrier will no longer fit it.
    later = [{**by_number[n("CR1")], "VehCategory": "FORK LIFT"}, by_number[n("CR1C")], by_number[n("CR3")]]
    preview = _uploaded(plum_report(later))
    rows = _rows_by_number(preview)
    closing = {"machine_machine_number": n("CR1"), "part_machine_number": n("CR1C"), "because": "CLASS_CHANGED"}
    assert [{key: item[key] for key in closing} for item in preview["preview"]["closing_links"]] == [closing]
    assert [{key: item[key] for key in closing} for item in rows[n("CR1")]["closing_links"]] == [closing]
    carrier_row = rows[n("CR1C")]
    assert carrier_row["outcome_code"] == "UNCHANGED" and carrier_row["needs_attention"] is True
    assert ("PART_NOT_FITTED", "") in _flags(carrier_row)
    # Pairing starts again from the state confirmation will leave: CR3 is the one crane of its model free.
    proposal = next(item for item in preview["preview"]["pair_proposals"] if item["part_machine_number"] == n("CR1C"))
    assert proposal["proposed_machine_number"] == n("CR3")
    assert n("CR1") not in {item["machine_number"] for item in proposal["candidates"]}

    _publish(preview)
    forklift = _machine_by_number(n("CR1"))
    assert forklift["class_code"] == "FORKLIFT" and forklift["fitted_parts"] == []
    assert [(item["part"]["machine_number"], item["removed_on"]) for item in forklift["link_history"]] == [(n("CR1C"), TODAY.isoformat())]
    assert "PART_NOT_FITTED" in _machine_by_number(n("CR1C"))["flag_codes"]
    removed = [event for event in _events(forklift["asset_public_id"]) if event["event_name"] == "EQUIPMENT_PART_REMOVED"]
    assert [json.loads(event["event_payload_json"])["because"] for event in removed] == ["CLASS_CHANGED"]


def test_an_older_report_closes_a_later_fitted_link_on_the_day_it_was_fitted_not_before() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet, pairs=False)
    crane, carrier = _machine_by_number(n("CR1")), _machine_by_number(n("CR1C"))
    _ok(_fit(crane, carrier, part_version=carrier["asset_version"]), 201)
    by_number = {row["VehicleNo"]: row for row in fleet.first_report_rows()}
    # A report dated before the fitting, in which the crane is a forklift.
    older = _uploaded(plum_report([{**by_number[n("CR1")], "VehCategory": "FORK LIFT"}, by_number[n("CR1C")]]), report_date=TODAY - timedelta(days=3))
    _publish(older)
    forklift = _machine_by_number(n("CR1"))
    assert [(item["part"]["machine_number"], item["fitted_on"], item["removed_on"]) for item in forklift["link_history"]] == [
        (n("CR1C"), TODAY.isoformat(), TODAY.isoformat())
    ]


def test_a_row_set_aside_takes_no_corrections_lifecycle_in() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    by_number = {row["VehicleNo"]: row for row in fleet.first_report_rows()}
    agrees = _correct(_machine_by_number(n("CR1")), "ENGINE_NUMBER", f"ENG-RIGHT-{fleet.sfx}")["machine"]
    third = _correct(_machine_by_number(n("CR3")), "OWNING_COMPANY", f"RIGHT OWNER {fleet.sfx}")["machine"]
    # Plum now holds the corrected engine number for CR1, and a third owner for CR3 - but both rows carry a
    # category nobody knows, so both are set aside and nothing about them is taken in.
    later = [
        {**by_number[n("CR1")], "EngineNo": f"ENG-RIGHT-{fleet.sfx}", "VehCategory": "SPACESHIP"},
        {**by_number[n("CR3")], "Owner": f"THIRD OWNER {fleet.sfx}", "VehCategory": "SPACESHIP"},
    ]
    preview = _uploaded(plum_report(later))
    rows = _rows_by_number(preview)
    for number in (n("CR1"), n("CR3")):
        assert (rows[number]["outcome_code"], rows[number]["reason_code"]) == ("SET_ASIDE", "CATEGORY_NOT_MAPPED")
        # The preview promises no closing and no flag the confirmation would not keep.
        assert rows[number]["corrections"] == []
        assert ("PLUM_CHANGED_CORRECTED_VALUE", "OWNING_COMPANY") not in _flags(rows[number])
    _publish(preview)
    after_agrees, after_third = _machine_by_number(n("CR1")), _machine_by_number(n("CR3"))
    assert [item["correction_status_code"] for item in after_agrees["corrections"]] == ["OPEN"]
    assert "PLUM_CHANGED_CORRECTED_VALUE" not in after_third["flag_codes"]
    assert (after_agrees["engine_number"], after_third["owning_company"]) == (agrees["engine_number"], third["owning_company"])


def test_a_part_is_never_fitted_before_it_was_last_removed_on_the_page_or_by_a_report() -> None:
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet, pairs=False)
    crane, carrier, other = _machine_by_number(n("CR1")), _machine_by_number(n("CR1C")), _machine_by_number(n("CR3"))
    fitted = _ok(_fit(crane, carrier, part_version=carrier["asset_version"]), 201)["machine"]
    part = fitted["fitted_parts"][0]["part"]
    removed = _ok(_remove(fitted, carrier, part_version=part["asset_version"]))["machine"]
    carrier = _machine(carrier["asset_public_id"])
    # On the page: fitted to CR3 the day before it came off CR1 - refused; the same day - fitted.
    yesterday = client.post(
        f"{BASE}/machines/{other['asset_public_id']}/fitted-parts",
        json={
            "expected_asset_version": other["asset_version"],
            "part_public_id": carrier["asset_public_id"],
            "expected_part_version": carrier["asset_version"],
            "fitted_on": (TODAY - timedelta(days=1)).isoformat(),
        },
        headers=auth_headers(ADMIN),
    )
    assert yesterday.status_code == 422
    assert TODAY.isoformat() in yesterday.json()["detail"]
    assert removed["fitted_parts"] == []

    # By a report: an older report ends CR1's fit and pairs the carrier with CR3 - dated no earlier than
    # the day it came off CR1, not the report's date.
    fleet2 = Fleet()
    m = fleet2.number
    _first_published(fleet2, pairs=False)
    crane2, carrier2 = _machine_by_number(m("CR1")), _machine_by_number(m("CR1C"))
    _ok(_fit(crane2, carrier2, part_version=carrier2["asset_version"]), 201)
    rows2 = {row["VehicleNo"]: row for row in fleet2.first_report_rows()}
    older = _uploaded(
        plum_report([{**rows2[m("CR1")], "VehCategory": "FORK LIFT"}, rows2[m("CR1C")], rows2[m("CR3")]]),
        report_date=TODAY - timedelta(days=3),
    )
    _publish(older, pairs=[{"part_machine_number": m("CR1C"), "machine_machine_number": m("CR3")}])
    re_paired = _machine_by_number(m("CR3"))
    assert [(item["part"]["machine_number"], item["fitted_on"]) for item in re_paired["fitted_parts"]] == [(m("CR1C"), TODAY.isoformat())]
    history = _machine_by_number(m("CR1"))["link_history"]
    assert [(item["part"]["machine_number"], item["removed_on"]) for item in history] == [(m("CR1C"), TODAY.isoformat())]


# --- Value rules ---------------------------------------------------------------------------------------


def test_value_rules_refuse_what_their_action_cannot_carry_and_list_only_open_ones_to_send() -> None:
    sfx = suffix()
    split_on_year = client.put(
        f"{BASE}/value-rules",
        json={"column_code": "COMMENCED_YEAR", "plum_value": f"X{sfx}", "action_code": "SPLIT_NUMBER_AND_UNIT", "result_number": "1", "result_unit_code": "TONNE", "reason": "r"},
        headers=auth_headers(ADMIN),
    )
    assert split_on_year.status_code == 422
    no_unit = client.put(
        f"{BASE}/value-rules",
        json={"column_code": "CAPACITY", "plum_value": f"X{sfx}", "action_code": "SPLIT_NUMBER_AND_UNIT", "result_number": "1", "reason": "r"},
        headers=auth_headers(ADMIN),
    )
    assert no_unit.status_code == 422
    wrong_type = client.put(
        f"{BASE}/value-rules",
        json={"column_code": "CAPACITY", "plum_value": f"X{sfx}", "action_code": "REASSIGN_TO_TYPE", "result_class_code": "CRANE", "result_type_code": "SCISSOR", "reason": "r"},
        headers=auth_headers(ADMIN),
    )
    assert wrong_type.status_code == 422
    first = _value_rule("CAPACITY", f"X{sfx}", "NOT_A_VALUE")
    replaced = _value_rule("CAPACITY", f"  x{sfx} ", "SPLIT_NUMBER_AND_UNIT", result_number="2", result_unit_code="TONNE")
    assert replaced["event"]["event_payload"]["superseded_rule_public_id"] == first["rule"]["rule_public_id"]
    sent = _ok(client.get(f"{BASE}/corrections", headers=auth_headers("readonly1")))
    open_ids = {item["rule_public_id"] for item in sent["value_rules"]}
    assert replaced["rule"]["rule_public_id"] in open_ids and first["rule"]["rule_public_id"] not in open_ids
    closed = _ok(client.post(f"{BASE}/value-rules/{replaced['rule']['rule_public_id']}/close", headers=auth_headers(ADMIN)))
    assert closed["rule"]["rule_status_code"] == "CLOSED"
    sent = _ok(client.get(f"{BASE}/corrections", headers=auth_headers("readonly1")))
    assert replaced["rule"]["rule_public_id"] not in {item["rule_public_id"] for item in sent["value_rules"]}


# --- Permissions and events -----------------------------------------------------------------------------


@pytest.mark.parametrize("username", READ_ROLES)
def test_every_read_role_can_read_machines_models_and_corrections(username: str) -> None:
    for path in ("/machines", "/models", "/corrections", "/value-rules", "/category-rules", "/structure"):
        assert client.get(f"{BASE}{path}", headers=auth_headers(username)).status_code == 200, path


@pytest.mark.parametrize("username", NON_ADMIN_ROLES)
def test_every_write_and_the_import_screens_are_refused_to_every_role_but_admin(username: str) -> None:
    some_id = str(uuid.uuid4())
    headers = auth_headers(username)
    calls = [
        client.post(f"{BASE}/imports", data={"report_date": TODAY.isoformat()}, files={"file": ("r.csv", b"x", "text/csv")}, headers=headers),
        client.get(f"{BASE}/imports", headers=headers),
        client.get(f"{BASE}/imports/{some_id}", headers=headers),
        client.post(f"{BASE}/imports/{some_id}/refresh", json={"expected_preview_version": 1}, headers=headers),
        client.post(f"{BASE}/imports/{some_id}/publish", json={"expected_preview_version": 1}, headers=headers),
        client.post(f"{BASE}/imports/{some_id}/discard", json={"expected_preview_version": 1}, headers=headers),
        client.post(f"{BASE}/models", json={}, headers=headers),
        client.put(f"{BASE}/models/{some_id}", json={}, headers=headers),
        client.put(f"{BASE}/model-mappings", json={}, headers=headers),
        client.put(f"{BASE}/value-rules", json={}, headers=headers),
        client.post(f"{BASE}/value-rules/{some_id}/close", headers=headers),
        client.put(f"{BASE}/machines/{some_id}/details", json={}, headers=headers),
        client.put(f"{BASE}/machines/{some_id}/capabilities", json={}, headers=headers),
        client.post(f"{BASE}/machines/{some_id}/corrections", json={}, headers=headers),
        client.post(f"{BASE}/machines/{some_id}/corrections/{some_id}/close", json={}, headers=headers),
        client.post(f"{BASE}/machines/{some_id}/fitted-parts", json={}, headers=headers),
        client.post(f"{BASE}/machines/{some_id}/fitted-parts/{some_id}/remove", json={}, headers=headers),
    ]
    assert [response.status_code for response in calls] == [403] * len(calls)


@pytest.mark.parametrize("username", NON_ADMIN_ROLES)
def test_engine_and_chassis_numbers_are_withheld_from_every_role_but_admin(username: str) -> None:
    """Owner, 25 September 2026: engine and chassis numbers are confidential - Admin only for now. Withheld
    on the machine, and in any correction or value rule that carries one - its reason included, which may
    repeat the numbers (independent review, round 2); everything else still reads."""
    fleet = Fleet()
    n = fleet.number
    _first_published(fleet)
    crane_id = _machine_by_number(n("CR1"))["asset_public_id"]
    why = f"Plum has C-{n('CR1')}; the plate reads CHS-RIGHT-{fleet.sfx}."
    corrected = _correct(_machine(crane_id), "CHASSIS_NUMBER", f"CHS-RIGHT-{fleet.sfx}", reason=why)["machine"]
    assert corrected["chassis_number"] == f"CHS-RIGHT-{fleet.sfx}" and corrected["identity_numbers_withheld"] is False
    engine_rule = _value_rule("ENGINE_NUMBER", f"NIL-{fleet.sfx}", "NOT_A_VALUE", reason=f"NIL-{fleet.sfx} means none.")["rule"]
    assert engine_rule["plum_value"] == f"NIL-{fleet.sfx}" and engine_rule["value_withheld"] is False

    seen = _machine(crane_id, username)
    assert (seen["engine_number"], seen["chassis_number"], seen["identity_numbers_withheld"]) == (None, None, True)
    assert seen["machine_number"] == n("CR1") and seen["commenced_year"] == 2015
    correction = next(item for item in seen["corrections"] if item["field_code"] == "CHASSIS_NUMBER")
    assert (correction["plum_value"], correction["corrected_value"], correction["corrected_value_label"]) == (None, None, None)
    assert correction["values_withheld"] is True and correction["reason"] is None

    sent = _ok(client.get(f"{BASE}/corrections", headers=auth_headers(username)))
    to_send = next(item for item in sent["corrections"] if item["correction_public_id"] == correction["correction_public_id"])
    assert (to_send["plum_value"], to_send["corrected_value"], to_send["values_withheld"], to_send["reason"]) == (None, None, True, None)
    rule = next(item for item in sent["value_rules"] if item["rule_public_id"] == engine_rule["rule_public_id"])
    assert (rule["plum_value"], rule["value_withheld"], rule["reason"]) == (None, True, None)
    listed = _ok(client.get(f"{BASE}/value-rules", headers=auth_headers(username)))
    assert next(item for item in listed if item["rule_public_id"] == engine_rule["rule_public_id"])["plum_value"] is None
    # Nothing in any of these responses carries the numbers.
    for body in (seen, sent, listed):
        assert f"C-{n('CR1')}" not in str(body) and f"E-{n('CR1')}" not in str(body)
        assert f"CHS-RIGHT-{fleet.sfx}" not in str(body) and f"NIL-{fleet.sfx}" not in str(body)

    # Admin sees them in the same places.
    admin_sent = _ok(client.get(f"{BASE}/corrections", headers=auth_headers(ADMIN)))
    admin_to_send = next(item for item in admin_sent["corrections"] if item["correction_public_id"] == correction["correction_public_id"])
    assert (admin_to_send["plum_value"], admin_to_send["corrected_value"], admin_to_send["reason"]) == (f"C-{n('CR1')}", f"CHS-RIGHT-{fleet.sfx}", why)
    admin_rule = next(item for item in admin_sent["value_rules"] if item["rule_public_id"] == engine_rule["rule_public_id"])
    assert admin_rule["reason"] == f"NIL-{fleet.sfx} means none."
    # A correction of any other field keeps its reason for every read role.
    other = _correct(_machine(crane_id), "OWNING_COMPANY", f"OWNER {fleet.sfx}", reason="The deed says so.")["machine"]
    owner_correction = next(item for item in _machine(crane_id, username)["corrections"] if item["field_code"] == "OWNING_COMPANY")
    assert (owner_correction["reason"], owner_correction["values_withheld"]) == ("The deed says so.", False)
    assert other["asset_version"] > corrected["asset_version"]


def test_an_unauthenticated_caller_is_refused() -> None:
    assert client.get(f"{BASE}/machines").status_code == 401
    assert client.post(f"{BASE}/imports", data={"report_date": TODAY.isoformat()}, files={"file": ("r.csv", b"x", "text/csv")}).status_code == 401


def test_event_payloads_carry_no_identity_number_plum_value_or_reason_text() -> None:
    fleet = Fleet()
    n = fleet.number
    body = _first_published(fleet)
    crane = _machine_by_number(n("CR1"))
    _correct(crane, "CHASSIS_NUMBER", f"CHS-SECRET-{fleet.sfx}")
    rule = _value_rule("CAPACITY", f"ODD VALUE {fleet.sfx}", "NOT_A_VALUE")
    payload_texts = []
    for record in (crane["asset_public_id"], body["equipment_import"]["import_public_id"], rule["rule"]["rule_public_id"], fleet.crane_model["model_public_id"]):
        for event in _events(record):
            payload_texts.append(event["event_payload_json"] or "")
    assert payload_texts
    for forbidden in (n("CR1"), f"E-{n('CR1')}", f"C-{n('CR1')}", f"CHS-SECRET-{fleet.sfx}", f"ODD VALUE {fleet.sfx}", "Test correction.", "Test reading.", fleet.super_name, "TEST OWNER"):
        assert not any(forbidden in payload for payload in payload_texts), forbidden


def test_the_uploaded_file_is_not_kept_only_its_used_values() -> None:
    fleet = Fleet()
    equipment_import = _uploaded(plum_report(fleet.first_report_rows()[:1]))
    with SessionLocal() as db:
        columns = {row[0] for row in db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'equipment_source_import_row'"))}
        stored = db.execute(
            text(
                "SELECT r.* FROM equipment_source_import_row r JOIN equipment_source_import i ON i.id = r.equipment_source_import_id "
                "WHERE i.import_public_id = :id"
            ),
            {"id": equipment_import["import_public_id"]},
        ).fetchall()
    assert not {"pan", "ins_policy_no", "insurance_co", "invoice_no", "gps"} & columns
    assert all("AAAAA0000A" not in str(tuple(row)) for row in stored)
    assert "AAAAA0000A" not in str(equipment_import["preview"])
