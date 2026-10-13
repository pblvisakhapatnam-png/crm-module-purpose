"""ERT-2 - detachable kit, held for the crane models it fits, through the API and at the database.

docs/agent/slices/ert-2-detachable-kit.md, sections 5 to 11 and the owner's answers of 26 September 2026:
kit is shared by the crane models it fits (Q6, Q12), counterweight is counted and the rest tracked one by
one (Q1, Q3), every kind is measured by its weight (Q13), a piece is retired with the day and the reason
(Q8, Q14), and the depth setting of 3 governs fitted parts (Q9). Every machine, model and number here is
invented and carries a run-unique token; each test removes what it created.
"""

from __future__ import annotations

import importlib.util
import json
import uuid
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import app
from app.core.database import SessionLocal
from app.modules.equipment_reference import repository as equipment_repository
from app.modules.equipment_reference.schemas import KitAddInput
from app.modules.equipment_reference.services import machines as equipment_machines
from app.modules.equipment_reference.services.common import EquipmentConflictError
from app.modules.equipment_reference.services.machines import KIT_KEY_USED
from app.shared.request_keys import request_fingerprint
from tests.business_day_test_support import TODAY, held_to_the_test_day
from tests.equipment_test_support import equipment_created_here, plum_report, plum_row, suffix
from tests.request_key_test_support import as_made_before_fingerprints, run_at_once, stored_fingerprints, user_public_id
from tests.test_commercial_offers_api import auth_headers, client

BASE = "/api/equipment-reference"
ADMIN = "admin1"
NON_ADMIN_ROLES = ("sales1", "manager1", "finance1", "ops1", "readonly1")
READ_ROLES = ("admin1",) + NON_ADMIN_ROLES
KIT_CLASSES = {
    # class: (tracking, key capability)
    "BOOM_JIB_SECTION": ("SINGLE", "LENGTH"),
    "COUNTERWEIGHT": ("COUNTED", "WEIGHT"),
    "HOOK_BLOCK": ("SINGLE", "RATED_CAPACITY"),
    "LIFTING_TACKLE": ("SINGLE", "RATED_CAPACITY"),
}


@pytest.fixture(scope="module", autouse=True)
def _on_the_test_day():
    with held_to_the_test_day():
        yield


@pytest.fixture(autouse=True)
def _remove_what_each_test_created():
    with equipment_created_here():
        yield


# --- Helpers ---------------------------------------------------------------------------------------


def _ok(response, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


def _detail(response, status: int = 422) -> str:
    assert response.status_code == status, response.text
    return response.json()["detail"]


def _structure() -> dict:
    return _ok(client.get(f"{BASE}/structure", headers=auth_headers("sales1")))


def _create_model(body: dict, username: str = ADMIN):
    return client.post(f"{BASE}/models", json={"create_request_key": str(uuid.uuid4()), "capabilities": [], **body}, headers=auth_headers(username))


def _model(maker: str, name: str, class_code: str, *, type_code: str | None = None, capabilities: list | None = None, fits: list | None = None, **extra) -> dict:
    body = {"maker": maker, "model_name": name, "class_code": class_code, "type_code": type_code, "capabilities": capabilities or [], **extra}
    if fits is not None:
        body["fits_model_public_ids"] = [item["model_public_id"] for item in fits]
    return _ok(_create_model(body), 201)["model"]


def _get_model(model: dict) -> dict:
    models = _ok(client.get(f"{BASE}/models", headers=auth_headers("readonly1")))
    return next(item for item in models if item["model_public_id"] == model["model_public_id"])


def _update_model(model: dict, **changes):
    current = _get_model(model)
    body = {
        "maker": current["maker"],
        "model_name": current["model_name"],
        "class_code": current["class_code"],
        "type_code": current["type_code"],
        "maker_part_number": current["maker_part_number"],
        "capabilities": [
            {"capability_code": item["capability_code"], "value": item["value"], "choice_value": item["choice_value"]}
            for item in current["capabilities"]
        ],
        "fits_model_public_ids": [item["model_public_id"] for item in current["fits_models"]],
        "is_retired": current["is_retired"],
        "expected_model_version": current["model_version"],
        **changes,
    }
    return client.put(f"{BASE}/models/{model['model_public_id']}", json=body, headers=auth_headers(ADMIN))


def _map(source_name: str, model_public_id: str | None):
    return client.put(
        f"{BASE}/model-mappings", json={"source_name": source_name, "model_public_id": model_public_id}, headers=auth_headers(ADMIN)
    )


def _upload(content: bytes, *, report_date: date = TODAY) -> dict:
    return _ok(
        client.post(
            f"{BASE}/imports",
            data={"report_date": report_date.isoformat()},
            files={"file": ("report.csv", content, "text/csv")},
            headers=auth_headers(ADMIN),
        ),
        201,
    )["equipment_import"]


def _publish(equipment_import: dict, pairs: list | None = None) -> dict:
    return _ok(
        client.post(
            f"{BASE}/imports/{equipment_import['import_public_id']}/publish",
            json={"expected_preview_version": equipment_import["preview_version"], "pairs": pairs or []},
            headers=auth_headers(ADMIN),
        )
    )


def _import(public_id: str) -> dict:
    return _ok(client.get(f"{BASE}/imports/{public_id}", headers=auth_headers(ADMIN)))


def _machine(public_id: str, username: str = ADMIN) -> dict:
    return _ok(client.get(f"{BASE}/machines/{public_id}", headers=auth_headers(username)))


def _list(**params) -> list[dict]:
    return _ok(client.get(f"{BASE}/machines", params={"limit": 200, **params}, headers=auth_headers("readonly1")))


# The cranes of the latest KitFleet, by their model: kit is added from the page of a crane its model fits.
_CRANES_BY_MODEL: dict[str, dict] = {}


def _add_kit(model: dict, count: int, *, machine: dict | None = None, key: str | None = None, username: str = ADMIN, **extra):
    """Add kit as a machine's page would, at the versions it would show (ERT2-R1-001) - by default the page
    of a crane of a model the kit model fits. `extra` overrides any field, stale versions included."""
    return _post_kit(_kit_body(model, count, machine=machine, key=key, **extra), username=username)


def _post_kit(body: dict, *, username: str = ADMIN):
    return client.post(f"{BASE}/kit", json=body, headers=auth_headers(username))


def _kit_body(model: dict, count: int, *, machine: dict | None = None, key: str | None = None, **extra) -> dict:
    """The request a machine's page would send to add kit, so a test can send the very same request again."""
    current = next((item for item in _ok(client.get(f"{BASE}/models", headers=auth_headers("readonly1"))) if item["model_public_id"] == model["model_public_id"]), None)
    if machine is None:
        fits = [fit["model_public_id"] for fit in (current or {}).get("fits_models", [])]
        machine = next((_CRANES_BY_MODEL[fit] for fit in fits if fit in _CRANES_BY_MODEL), next(iter(_CRANES_BY_MODEL.values())))
    body = {
        "create_request_key": key or str(uuid.uuid4()),
        "machine_public_id": machine["asset_public_id"],
        "kit_model_public_id": model["model_public_id"],
        "expected_model_version": current["model_version"] if current else 1,
        "count": count,
        **extra,
    }
    if "expected_asset_version" not in body:
        body["expected_asset_version"] = _machine(machine["asset_public_id"])["asset_version"]
    return body


def _added(model: dict, count: int, **extra) -> list[dict]:
    return _ok(_add_kit(model, count, **extra), 201)["pieces"]


def _retire(piece: dict, reason_code: str, *, retired_on: date = TODAY, note: str | None = None, count: int | None = None, version: int | None = None, username: str = ADMIN):
    body: dict[str, Any] = {
        "expected_asset_version": version if version is not None else _machine(piece["asset_public_id"])["asset_version"],
        "reason_code": reason_code,
        "retired_on": retired_on.isoformat(),
        "note": note,
    }
    if count is not None:
        body["count"] = count
    return client.post(f"{BASE}/machines/{piece['asset_public_id']}/retire", json=body, headers=auth_headers(username))


def _details(piece: dict, **values):
    current = _machine(piece["asset_public_id"])
    body = {
        "expected_asset_version": current["asset_version"],
        "serial_number": current["serial_number"],
        "year_of_manufacture": current["year_of_manufacture"],
        **values,
    }
    return client.put(f"{BASE}/machines/{piece['asset_public_id']}/details", json=body, headers=auth_headers(ADMIN))


def _events(record_public_id: str) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT event_name, event_payload_json, reason FROM business_event WHERE record_public_id = :id ORDER BY id"),
            {"id": record_public_id},
        ).fetchall()
    return [dict(row._mapping) for row in rows]


def _payload(event: dict) -> dict:
    value = event["event_payload_json"]
    return json.loads(value) if isinstance(value, str) else value


@contextmanager
def _rolled_back() -> Iterator[Any]:
    """A session whose every change is discarded, for writes a constraint must refuse."""
    with SessionLocal() as db:
        try:
            yield db
        finally:
            db.rollback()


class KitFleet:
    """Three invented cranes of two crane models - two of the first, which share its kit, and one of the
    second - with a boom insert model and a hook block model for the first, and a counterweight model that
    fits both (Q12)."""

    def __init__(self) -> None:
        self.sfx = s = suffix()
        self.crane_model = _model(
            "ACME", f"CC 100 {s}", "CRANE", type_code="CRAWLER", capabilities=[{"capability_code": "RATED_CAPACITY", "value": "100"}]
        )
        self.other_crane_model = _model(
            "ACME", f"CC 120 {s}", "CRANE", type_code="CRAWLER", capabilities=[{"capability_code": "RATED_CAPACITY", "value": "120"}]
        )
        self.crane_name, self.other_crane_name = f"{s} ACME CC 100", f"{s} ACME CC 120"
        _ok(_map(self.crane_name, self.crane_model["model_public_id"]))
        _ok(_map(self.other_crane_name, self.other_crane_model["model_public_id"]))
        _publish(_upload(plum_report(self.report_rows())))
        by_number = {item["machine_number"]: item for item in _list(search=f"T{s}-")}
        self.crane_1, self.crane_2, self.crane_3 = (by_number[self.number(label)] for label in ("CR1", "CR2", "CR3"))
        _CRANES_BY_MODEL.clear()
        _CRANES_BY_MODEL.update({self.crane_model["model_public_id"]: self.crane_1, self.other_crane_model["model_public_id"]: self.crane_3})
        self.insert_model = _model(
            "ACME",
            f"CC 100 insert 9 m {s}",
            "BOOM_JIB_SECTION",
            type_code="MAIN_BOOM_INSERT",
            capabilities=[{"capability_code": "LENGTH", "value": "9"}, {"capability_code": "WEIGHT", "value": "1.0"}],
            fits=[self.crane_model],
            maker_part_number=f"PN-{s}",
        )
        self.hook_model = _model(
            "ACME",
            f"CC 100 hook block {s}",
            "HOOK_BLOCK",
            type_code="HOOK_BLOCK",
            capabilities=[{"capability_code": "RATED_CAPACITY", "value": "100"}, {"capability_code": "WEIGHT", "value": "1.2"}],
            fits=[self.crane_model],
        )
        self.counterweight_model = _model(
            "ACME",
            f"CC block 3.9 t {s}",
            "COUNTERWEIGHT",
            type_code="UPPER_COUNTERWEIGHT",
            capabilities=[{"capability_code": "WEIGHT", "value": "3.9"}],
            fits=[self.crane_model, self.other_crane_model],
        )

    def number(self, label: str) -> str:
        return f"T{self.sfx}-{label}"

    def report_rows(self, *, cr3_status: str = "Active") -> list[dict[str, str]]:
        n = self.number
        return [
            plum_row(number=n("CR1"), schedule=self.crane_name, category="CRANES", capacity="100", year="2015"),
            plum_row(number=n("CR2"), schedule=self.crane_name, category="CRANES", capacity="100", year="2016"),
            plum_row(number=n("CR3"), schedule=self.other_crane_name, category="CRANES", capacity="120", year="2017", status=cr3_status),
        ]


# --- Structure version 3 ---------------------------------------------------------------------------


def test_version_3_adds_four_kinds_of_kit_offered_to_no_business_line() -> None:
    body = _structure()
    assert body["taxonomy_version"] == 3
    assert body["component_depth"] == 3
    assert [(item["version_number"], item["component_depth"]) for item in body["versions"]] == [(1, 1), (2, 2), (3, 3)]
    classes = {item["class_code"]: item for item in body["classes"]}
    added = [code for code, item in classes.items() if item["introduced_in_version"] == 3]
    assert added == list(KIT_CLASSES)
    for class_code, (tracking, key) in KIT_CLASSES.items():
        kind = classes[class_code]
        assert kind["class_kind_code"] == "PART"
        assert kind["business_line_codes"] == []
        assert kind["kit_for_class_codes"] == ["CRANE"]
        assert kind["fits_class_codes"] == []
        assert kind["tracking_code"] == tracking
        capabilities = {item["capability_code"]: item for item in kind["capabilities"]}
        # Every kind of kit is measured by its weight (owner, Q13).
        assert "WEIGHT" in capabilities
        assert [code for code, item in capabilities.items() if item["is_key"]] == [key]
    carrier = classes["CRANE_CARRIER"]
    assert (carrier["fits_class_codes"], carrier["kit_for_class_codes"], carrier["tracking_code"]) == (["CRANE"], [], "SINGLE")
    assert all(item["tracking_code"] == "SINGLE" for item in classes.values() if item["class_kind_code"] == "MACHINE")
    capabilities = {item["capability_code"]: item for item in body["capabilities"]}
    assert (capabilities["LENGTH"]["unit_code"], capabilities["WEIGHT"]["unit_code"]) == ("METRE", "TONNE")


_MIGRATION = Path(app.__file__).resolve().parents[1] / "alembic" / "versions" / "20260908_0043_equipment_detachable_kit.py"


def _check_the_structure(db: Any) -> None:
    """Run the migration's own structure check on this session's connection."""
    spec = importlib.util.spec_from_file_location("ert2_migration", _MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(db.connection())):
        module._check_the_structure()


def test_the_part_fits_hold_no_loop_and_no_chain_deeper_than_the_setting() -> None:
    """The migration's own check passes on the database as it stands, and refuses a chain of open links
    deeper than the setting - four machines fitted one below the other, made and discarded here."""
    fleet = KitFleet()
    piece = _added(fleet.insert_model, 1)[0]

    def link(db: Any, chain: list[dict]) -> None:
        for parent, child in zip(chain, chain[1:]):
            db.execute(
                text(
                    "INSERT INTO equipment_asset_link (link_public_id, parent_asset_id, child_asset_id, link_kind_code, "
                    "fitted_on, fitted_by, fitted_at) SELECT :l, p.id, c.id, 'FITTED', CURRENT_DATE, u.public_id, "
                    "CURRENT_TIMESTAMP FROM equipment_asset p, equipment_asset c, app_user u "
                    "WHERE p.asset_public_id = :p AND c.asset_public_id = :c AND u.username = 'admin1'"
                ),
                {"l": str(uuid.uuid4()), "p": parent["asset_public_id"], "c": child["asset_public_id"]},
            )

    with _rolled_back() as db:
        _check_the_structure(db)
        link(db, [fleet.crane_1, fleet.crane_2, fleet.crane_3, piece])
        with pytest.raises(RuntimeError, match="Open fitted links reach 4 levels, deeper than the depth setting of 3"):
            _check_the_structure(db)
    # A loop with no top: every machine in it is fitted below another (independent review, ERT2-R1-005).
    with _rolled_back() as db:
        link(db, [fleet.crane_1, fleet.crane_2, fleet.crane_1])
        with pytest.raises(RuntimeError, match="Open fitted links loop"):
            _check_the_structure(db)
    # A Plum record of a kind of kit, made with the row guard held off as a later structure version could leave
    # one: the check finds it (ERT2-R4-002).
    with _rolled_back() as db:
        db.execute(text("ALTER TABLE equipment_asset DISABLE TRIGGER trg_equipment_asset_matches_tracking"))
        db.execute(
            text(
                "INSERT INTO equipment_asset (asset_public_id, asset_kind_code, origin_code, class_code, machine_number, asset_status_code) "
                "VALUES (:p, 'PART', 'PLUM', 'HOOK_BLOCK', :n, 'ACTIVE')"
            ),
            {"p": str(uuid.uuid4()), "n": f"T{fleet.sfx}-HB"},
        )
        with pytest.raises(RuntimeError, match="1 record\\(s\\) disagree with the structure"):
            _check_the_structure(db)


# --- Kit models and the crane models they fit ------------------------------------------------------


def test_a_kit_model_names_the_crane_models_it_fits_and_the_makers_part_number() -> None:
    fleet = KitFleet()
    insert = _get_model(fleet.insert_model)
    assert insert["is_kit"] is True
    assert [item["model_public_id"] for item in insert["fits_models"]] == [fleet.crane_model["model_public_id"]]
    assert insert["maker_part_number"] == f"PN-{fleet.sfx}"
    assert insert["pieces_held"] == 0 and insert["fits_no_active_crane"] is False
    counterweight = _get_model(fleet.counterweight_model)
    assert {item["model_public_id"] for item in counterweight["fits_models"]} == {
        fleet.crane_model["model_public_id"],
        fleet.other_crane_model["model_public_id"],
    }
    crane = _get_model(fleet.crane_model)
    assert crane["is_kit"] is False and crane["active_unit_count"] == 2
    assert crane["maker_part_number"] is None
    # The part number is optional, and kept on any model.
    changed = _ok(_update_model(fleet.crane_model, maker_part_number=f"CRANE-PN-{fleet.sfx}"))
    assert changed["model"]["maker_part_number"] == f"CRANE-PN-{fleet.sfx}"
    assert changed["event"]["event_payload"]["changed_fields"] == ["maker_part_number"]


def test_a_kit_model_needs_crane_models_it_can_fit_and_no_other_model_takes_any() -> None:
    fleet = KitFleet()
    s = fleet.sfx
    forklift = _model("LIFTCO", f"FL 3 {s}", "FORKLIFT", capabilities=[{"capability_code": "RATED_CAPACITY", "value": "3"}])
    base = {"maker": "ACME", "class_code": "HOOK_BLOCK", "type_code": "HOOK_BLOCK"}
    assert "at least one" in _detail(_create_model({**base, "model_name": f"no fits {s}"}))
    assert "is not a model" in _detail(_create_model({**base, "model_name": f"forklift {s}", "fits_model_public_ids": [forklift["model_public_id"]]}))
    twice = [fleet.crane_model["model_public_id"]] * 2
    assert "twice" in _detail(_create_model({**base, "model_name": f"twice {s}", "fits_model_public_ids": twice}))
    assert _create_model({**base, "model_name": f"nowhere {s}", "fits_model_public_ids": [str(uuid.uuid4())]}).status_code == 404
    # A machine model fits nothing.
    assert "Only a model of a kind of kit" in _detail(
        _create_model({"maker": "ACME", "model_name": f"crane {s}", "class_code": "CRANE", "fits_model_public_ids": [fleet.crane_model["model_public_id"]]})
    )
    # A retired crane model is not newly chosen, but a kit model already fitting it keeps it.
    _ok(_update_model(fleet.other_crane_model, is_retired=True))
    assert "retired" in _detail(_create_model({**base, "model_name": f"late {s}", "fits_model_public_ids": [fleet.other_crane_model["model_public_id"]]}))
    kept = _ok(_update_model(fleet.counterweight_model, maker_part_number=f"KEPT-{s}"))
    assert len(kept["model"]["fits_models"]) == 2


def test_a_model_plum_names_are_mapped_to_does_not_become_a_kind_of_kit() -> None:
    """No Plum model name is mapped to a kit model, so a mapped model - even one no record uses yet - is not
    changed into one (independent review, round 3, ERT2-R3-001). An unmapped one may be."""
    fleet = KitFleet()
    hook_block = {"class_code": "HOOK_BLOCK", "type_code": "HOOK_BLOCK", "capabilities": [], "fits_model_public_ids": [fleet.crane_model["model_public_id"]]}
    mapped = _model("ACME", f"Spare {fleet.sfx}", "CRANE", type_code="CRAWLER")
    _ok(_map(f"{fleet.sfx} ACME SPARE", mapped["model_public_id"]))
    assert "cannot become a kind of kit" in _detail(_update_model(mapped, **hook_block))
    assert _get_model(mapped)["class_code"] == "CRANE"
    unmapped = _model("ACME", f"Unused {fleet.sfx}", "CRANE", type_code="CRAWLER")
    assert _ok(_update_model(unmapped, **hook_block))["model"]["is_kit"] is True


def test_a_kit_model_fits_only_where_its_kind_is_kit_for_the_crane_models_class_at_the_database() -> None:
    fleet = KitFleet()
    with _rolled_back() as db:
        insert_id = db.execute(text("SELECT id FROM equipment_model WHERE model_public_id = :p"), {"p": fleet.insert_model["model_public_id"]}).scalar_one()
        hook_id = db.execute(text("SELECT id FROM equipment_model WHERE model_public_id = :p"), {"p": fleet.hook_model["model_public_id"]}).scalar_one()
        with pytest.raises(IntegrityError, match="fk_equipment_model_fit_part_fit"):
            db.execute(
                text(
                    "INSERT INTO equipment_model_fit (kit_model_id, kit_class_code, crane_model_id, crane_class_code) "
                    "VALUES (:kit, 'BOOM_JIB_SECTION', :crane, 'HOOK_BLOCK')"
                ),
                {"kit": insert_id, "crane": hook_id},
            )


def test_a_crane_model_that_kit_fits_cannot_change_class() -> None:
    fleet = KitFleet()
    s = fleet.sfx
    spare = _model("ACME", f"CC 150 {s}", "CRANE", type_code="CRAWLER")
    _model("ACME", f"CC 150 jib {s}", "BOOM_JIB_SECTION", type_code="LUFFING_JIB_SECTION", fits=[spare])
    assert "Kit is recorded as fitting this model" in _detail(_update_model(spare, class_code="FORKLIFT", type_code=None))
    with _rolled_back() as db, pytest.raises(IntegrityError, match="fk_equipment_model_fit_crane_model"):
        db.execute(text("UPDATE equipment_model SET class_code = 'FORKLIFT', type_code = NULL WHERE model_public_id = :p"), {"p": spare["model_public_id"]})


def test_no_plum_name_is_mapped_to_a_kit_model_and_no_machine_is_corrected_to_one() -> None:
    fleet = KitFleet()
    assert "Kit is recorded on the platform" in _detail(_map(f"{fleet.sfx} SOME INSERT", fleet.insert_model["model_public_id"]))
    crane = _machine(fleet.crane_1["asset_public_id"])
    refused = client.post(
        f"{BASE}/machines/{crane['asset_public_id']}/corrections",
        json={
            "expected_asset_version": crane["asset_version"],
            "field_code": "MODEL",
            "corrected_value": fleet.insert_model["model_public_id"],
            "reason": "Testing a kit model as a correction.",
        },
        headers=auth_headers(ADMIN),
    )
    assert "kit model" in _detail(refused)


# --- Adding pieces ---------------------------------------------------------------------------------


def test_several_alike_make_that_many_records_and_a_counted_set_one() -> None:
    fleet = KitFleet()
    inserts = _added(fleet.insert_model, 3, year_of_manufacture=2015)
    assert len(inserts) == 3
    assert {(item["origin_code"], item["machine_number"], item["quantity"], item["asset_kind_code"]) for item in inserts} == {("PLATFORM", None, 1, "PART")}
    assert all(item["class_code"] == "BOOM_JIB_SECTION" and item["type_code"] == "MAIN_BOOM_INSERT" for item in inserts)
    assert inserts[0]["key_capability"]["capability_code"] == "LENGTH"
    assert len({item["asset_reference"] for item in inserts}) == 3
    blocks = _added(fleet.counterweight_model, 6)
    assert len(blocks) == 1 and blocks[0]["quantity"] == 6
    piece = _machine(inserts[0]["asset_public_id"])
    assert piece["year_of_manufacture"] == 2015 and piece["serial_number"] is None
    assert piece["plum"] is None and piece["corrections"] == [] and piece["flags"] == []
    assert [item["model_public_id"] for item in piece["fits_models"]] == [fleet.crane_model["model_public_id"]]
    hook = _added(fleet.hook_model, 1, serial_number=f"HB-{fleet.sfx}")
    assert _machine(hook[0]["asset_public_id"])["serial_number"] == f"HB-{fleet.sfx}"


def test_a_number_goes_to_one_piece_at_a_time_and_never_to_a_counted_set() -> None:
    fleet = KitFleet()
    assert "one piece at a time" in _detail(_add_kit(fleet.insert_model, 2, serial_number="SN-1"))
    assert "one piece at a time" in _detail(_add_kit(fleet.counterweight_model, 1, serial_number="SN-2"))
    assert _add_kit(fleet.insert_model, 0).status_code == 422
    assert _add_kit(fleet.insert_model, 51).status_code == 422
    # Not made in a year still to come - next year included (owner's screen check, 27 September 2026); this
    # year is fine.
    assert f"cannot be later than {TODAY.year}" in _detail(_add_kit(fleet.insert_model, 1, year_of_manufacture=TODAY.year + 1))
    crane = _machine(fleet.crane_1["asset_public_id"])
    next_year = client.put(
        f"{BASE}/machines/{crane['asset_public_id']}/details",
        json={"expected_asset_version": crane["asset_version"], "serial_number": None, "year_of_manufacture": TODAY.year + 1},
        headers=auth_headers(ADMIN),
    )
    assert f"cannot be later than {TODAY.year}" in _detail(next_year)
    this_year = _added(fleet.insert_model, 1, year_of_manufacture=TODAY.year)[0]
    assert _machine(this_year["asset_public_id"])["year_of_manufacture"] == TODAY.year


def test_the_database_holds_tracking_and_origin_whatever_the_service_does() -> None:
    fleet = KitFleet()
    insert = _added(fleet.insert_model, 1)[0]
    block = _added(fleet.counterweight_model, 4)[0]
    # The trigger's refusals (equipment_asset_matches_tracking) are known by their words.
    with _rolled_back() as db, pytest.raises(IntegrityError, match="is tracked one by one, so a record holds one piece"):
        db.execute(text("UPDATE equipment_asset SET quantity = 2 WHERE asset_public_id = :p"), {"p": insert["asset_public_id"]})
    with _rolled_back() as db, pytest.raises(IntegrityError, match="is counted, so a record carries no number"):
        db.execute(text("UPDATE equipment_asset SET serial_number = 'X' WHERE asset_public_id = :p"), {"p": block["asset_public_id"]})
    with _rolled_back() as db, pytest.raises(IntegrityError, match="ck_equipment_asset_origin"):
        db.execute(text("UPDATE equipment_asset SET machine_number = 'X' WHERE asset_public_id = :p"), {"p": insert["asset_public_id"]})
    # A Plum record made with a request key (an update is refused sooner: the request that made a record never
    # changes, ERT2-R2-001).
    with _rolled_back() as db, pytest.raises(IntegrityError, match="ck_equipment_asset_origin"):
        db.execute(
            text(
                "INSERT INTO equipment_asset (asset_public_id, asset_kind_code, origin_code, class_code, machine_number, "
                "asset_status_code, create_request_key, create_request_position) "
                "VALUES (:p, 'MACHINE', 'PLUM', 'CRANE', :n, 'ACTIVE', :k, 1)"
            ),
            {"p": str(uuid.uuid4()), "n": f"T{fleet.sfx}-X1", "k": str(uuid.uuid4())},
        )
    # Only kit is made on the platform: a platform record of a crane carrier is refused.
    carrier_model = _model("ACME", f"CC 100 {fleet.sfx}", "CRANE_CARRIER")
    with _rolled_back() as db, pytest.raises(IntegrityError, match="Only kit is recorded on the platform"):
        db.execute(
            text(
                "INSERT INTO equipment_asset (asset_public_id, asset_kind_code, origin_code, class_code, equipment_model_id, "
                "asset_status_code, create_request_key, create_request_position) "
                "SELECT :p, 'PART', 'PLATFORM', 'CRANE_CARRIER', id, 'ACTIVE', :k, 1 FROM equipment_model WHERE model_public_id = :m"
            ),
            {"p": str(uuid.uuid4()), "k": str(uuid.uuid4()), "m": carrier_model["model_public_id"]},
        )
    # And from the class's side: a kind's tracking cannot change under records it would no longer fit.
    with _rolled_back() as db, pytest.raises(IntegrityError, match="do not fit tracking SINGLE"):
        db.execute(text("UPDATE equipment_class SET tracking_code = 'SINGLE' WHERE class_code = 'COUNTERWEIGHT'"))
    _ok(_details(insert, serial_number=f"INS-{fleet.sfx}"))
    with _rolled_back() as db, pytest.raises(IntegrityError, match="do not fit tracking COUNTED"):
        db.execute(text("UPDATE equipment_class SET tracking_code = 'COUNTED' WHERE class_code = 'BOOM_JIB_SECTION'"))
    # A retired piece carries its reason: NULL is refused, not let through as a CHECK passes NULL (ERT2-R4-001).
    with _rolled_back() as db, pytest.raises(IntegrityError, match="ck_equipment_asset_retirement"):
        db.execute(
            text("UPDATE equipment_asset SET asset_status_code = 'RETIRED', retired_on = CURRENT_DATE WHERE asset_public_id = :p"),
            {"p": insert["asset_public_id"]},
        )
    # Kit is never read from Plum: a Plum record of a kind of kit is refused (ERT2-R4-002).
    with _rolled_back() as db, pytest.raises(IntegrityError, match="is a kind of kit: kit is recorded on the platform, never read from Plum"):
        db.execute(
            text(
                "INSERT INTO equipment_asset (asset_public_id, asset_kind_code, origin_code, class_code, machine_number, asset_status_code) "
                "VALUES (:p, 'PART', 'PLUM', 'HOOK_BLOCK', :n, 'ACTIVE')"
            ),
            {"p": str(uuid.uuid4()), "n": f"T{fleet.sfx}-HB"},
        )


def test_kit_is_added_only_on_the_premise_its_page_showed() -> None:
    """Kit is added from a machine's page: refused when the machine or the kit model changed since the page read
    them, or when the kit model does not fit the machine's model (independent review, round 1, ERT2-R1-001)."""
    fleet = KitFleet()
    crane = _machine(fleet.crane_1["asset_public_id"])
    hook = _get_model(fleet.hook_model)
    stale_crane = _add_kit(fleet.hook_model, 1, machine=fleet.crane_1, expected_asset_version=crane["asset_version"] + 1)
    assert "changed this machine" in _detail(stale_crane, 409)
    stale_model = _add_kit(fleet.hook_model, 1, machine=fleet.crane_1, expected_model_version=hook["model_version"] + 1)
    assert "changed this kit model" in _detail(stale_model, 409)
    # The hook block fits the first crane model only; the counterweight fits both.
    assert "does not fit this machine's model" in _detail(_add_kit(fleet.hook_model, 1, machine=fleet.crane_3))
    assert _list(kit_model_public_id=fleet.hook_model["model_public_id"]) == []
    _added(fleet.counterweight_model, 2, machine=fleet.crane_3)
    unknown = _add_kit(fleet.hook_model, 1, machine={"asset_public_id": str(uuid.uuid4())}, expected_asset_version=1)
    assert unknown.status_code == 404


def test_only_a_live_kit_model_takes_pieces() -> None:
    fleet = KitFleet()
    assert "not a kit model" in _detail(_add_kit(fleet.crane_model, 1))
    _ok(_update_model(fleet.hook_model, is_retired=True))
    assert "retired" in _detail(_add_kit(fleet.hook_model, 1))
    assert _add_kit({"model_public_id": str(uuid.uuid4())}, 1).status_code == 404


def test_the_same_request_twice_adds_once() -> None:
    fleet = KitFleet()
    key = str(uuid.uuid4())
    body = _kit_body(fleet.insert_model, 2, key=key)
    first = _ok(_post_kit(body), 201)
    again = _ok(_post_kit(body), 201)
    assert first["replayed"] is False
    assert again["replayed"] is True and again["events"] == []
    assert [item["asset_public_id"] for item in again["pieces"]] == [item["asset_public_id"] for item in first["pieces"]]
    assert len(first["events"]) == 2
    assert len(_list(kit_model_public_id=fleet.insert_model["model_public_id"])) == 2
    # The same key for another kit model is refused, not answered with the first lot.
    assert _detail(_add_kit(fleet.hook_model, 1, key=key), 409) == KIT_KEY_USED
    assert stored_fingerprints("equipment_asset", key) == [request_fingerprint(KitAddInput(**body))] * 2


def test_a_used_key_with_a_changed_request_adds_nothing() -> None:
    """The defect TB-1 found (TB1-305): a key was judged by its kit model alone, so a form whose first save was
    recorded but whose reply was lost, then changed - another count, a piece's own number, its year - and saved
    again, got the FIRST lot back and the change was dropped silently. Now any change is refused (409)."""
    fleet = KitFleet()
    key = str(uuid.uuid4())
    body = _kit_body(fleet.hook_model, 1, key=key)
    first = _ok(_post_kit(body), 201)["pieces"]
    for changed in ({"count": 3}, {"serial_number": f"HB-{fleet.sfx}"}, {"year_of_manufacture": 2020}):
        assert _detail(_post_kit({**body, **changed}), 409) == KIT_KEY_USED, changed
    held = _list(kit_model_public_id=fleet.hook_model["model_public_id"])
    assert [item["asset_public_id"] for item in held] == [item["asset_public_id"] for item in first]
    assert _machine(first[0]["asset_public_id"])["serial_number"] is None


def test_a_repeated_request_is_judged_by_the_request_as_sent() -> None:
    """A piece's model may change later; the request that made it may not, so a repeat is still judged by the
    request as first sent - its kit model included (independent review, round 2, ERT2-R2-001) - and the very same
    request still replays (TB-1 TB1-102 part b)."""
    fleet = KitFleet()
    other_insert = _model(
        "ACME", f"CC 100 insert 6 m {fleet.sfx}", "BOOM_JIB_SECTION", type_code="MAIN_BOOM_INSERT", fits=[fleet.crane_model]
    )
    key = str(uuid.uuid4())
    body = _kit_body(fleet.insert_model, 2, key=key)
    first = _ok(_post_kit(body), 201)["pieces"]
    _ok(_details(first[0], model_public_id=other_insert["model_public_id"]))
    again = _ok(_post_kit(body), 201)
    assert again["replayed"] is True
    assert [item["asset_public_id"] for item in again["pieces"]] == [item["asset_public_id"] for item in first]
    # Another count with the model first asked for is another request.
    assert _detail(_post_kit({**body, "count": 5}), 409) == KIT_KEY_USED
    # The model a piece has moved to is not what the request asked for.
    assert _detail(_add_kit(other_insert, 2, key=key), 409) == KIT_KEY_USED
    assert len(_list(kit_model_public_id=fleet.insert_model["model_public_id"])) == 1
    # The database keeps the request as made: its key, place, model asked for and fingerprint.
    for column, value in (
        ("create_request_key", "'x'"),
        ("create_request_position", "9"),
        ("create_request_model_id", "NULL"),
        ("create_request_fingerprint", f"'{'0' * 64}'"),
        ("create_request_fingerprint", "NULL"),
    ):
        with _rolled_back() as db, pytest.raises(IntegrityError, match="The request that made a record never changes"):
            db.execute(text(f"UPDATE equipment_asset SET {column} = {value} WHERE asset_public_id = :p"), {"p": first[1]["asset_public_id"]})
    assert _list(kit_model_public_id=fleet.hook_model["model_public_id"]) == []


def test_a_lot_recorded_before_fingerprints_is_refused_never_replayed() -> None:
    """A lot made before migration 0050 has no fingerprint, so the request that made it cannot be known: its key is
    refused even with the same body, never taken for a request it may not have been."""
    fleet = KitFleet()
    key = str(uuid.uuid4())
    body = _kit_body(fleet.insert_model, 2, key=key)
    _ok(_post_kit(body), 201)
    as_made_before_fingerprints("equipment_asset", key)
    assert _detail(_post_kit(body), 409) == KIT_KEY_USED
    assert len(_list(kit_model_public_id=fleet.insert_model["model_public_id"])) == 2


def _kit_at_once(monkeypatch, bodies: list[dict]) -> list[tuple[str, Any]]:
    actor = user_public_id(ADMIN)
    return run_at_once(
        monkeypatch,
        equipment_repository,
        "list_assets_by_create_request_key",
        [lambda db, body=body: equipment_machines.add_kit(db, payload=KitAddInput(**body), user_public_id=actor) for body in bodies],
    )


def test_two_adds_at_once_with_one_key_record_one_lot(monkeypatch) -> None:
    """Two tabs sending the same request at once: one lot, recorded once; the other is answered with it."""
    fleet = KitFleet()
    body = _kit_body(fleet.insert_model, 2)
    results = _kit_at_once(monkeypatch, [body, dict(body)])
    assert [outcome for outcome, _ in results] == ["ok", "ok"], results
    answers = [answer for _, answer in results]
    assert sorted(answer.replayed for answer in answers) == [False, True]
    assert [piece.asset_public_id for piece in answers[0].pieces] == [piece.asset_public_id for piece in answers[1].pieces]
    assert len(stored_fingerprints("equipment_asset", body["create_request_key"])) == 2


def test_two_adds_at_once_with_one_key_and_different_requests_record_one(monkeypatch) -> None:
    fleet = KitFleet()
    body = _kit_body(fleet.insert_model, 2)
    results = _kit_at_once(monkeypatch, [body, {**body, "count": 4}])
    assert sorted(outcome for outcome, _ in results) == ["error", "ok"], results
    refused = next(value for outcome, value in results if outcome == "error")
    assert isinstance(refused, EquipmentConflictError) and str(refused) == KIT_KEY_USED
    made = next(value for outcome, value in results if outcome == "ok")
    assert len(stored_fingerprints("equipment_asset", body["create_request_key"])) == len(made.pieces)


# --- The kit held for a crane model, shared by its cranes ------------------------------------------


def _kit_of(machine: dict) -> dict[str, dict]:
    return {item["kit_model_public_id"]: item for item in _machine(machine["asset_public_id"], "readonly1")["kit"]}


def test_every_crane_of_a_model_shows_the_same_kit() -> None:
    fleet = KitFleet()
    _added(fleet.insert_model, 4)
    _added(fleet.counterweight_model, 6)
    one, two = _machine(fleet.crane_1["asset_public_id"]), _machine(fleet.crane_2["asset_public_id"])
    assert one["model_active_unit_count"] == two["model_active_unit_count"] == 2
    assert one["kit"] == two["kit"]
    kit = _kit_of(fleet.crane_1)
    insert = kit[fleet.insert_model["model_public_id"]]
    assert (insert["pieces_held"], insert["records_held"], insert["tracking_code"]) == (4, 4, "SINGLE")
    assert insert["key_capability"]["capability_code"] == "LENGTH"
    blocks = kit[fleet.counterweight_model["model_public_id"]]
    assert (blocks["pieces_held"], blocks["records_held"], blocks["tracking_code"]) == (6, 1, "COUNTED")
    # A kit model with nothing held yet is listed too.
    assert kit[fleet.hook_model["model_public_id"]]["pieces_held"] == 0
    # The counterweight fits the second crane model as well, and shows there; the inserts do not.
    other = _kit_of(fleet.crane_3)
    assert set(other) == {fleet.counterweight_model["model_public_id"]}
    assert other[fleet.counterweight_model["model_public_id"]]["pieces_held"] == 6
    assert _machine(fleet.crane_3["asset_public_id"])["model_active_unit_count"] == 1
    # The list filters: one kit model's pieces, and the kit held for one crane model.
    assert len(_list(kit_model_public_id=fleet.insert_model["model_public_id"])) == 4
    held = _list(fits_model_public_id=fleet.other_crane_model["model_public_id"])
    assert [item["quantity"] for item in held] == [6]


def test_kit_left_with_no_active_crane_of_its_models_is_marked() -> None:
    fleet = KitFleet()
    jib = _model("ACME", f"CC 120 jib {fleet.sfx}", "BOOM_JIB_SECTION", type_code="FIXED_JIB_SECTION", fits=[fleet.other_crane_model])
    _added(jib, 1)
    assert _get_model(jib)["fits_no_active_crane"] is False
    _publish(_upload(plum_report(fleet.report_rows(cr3_status="Inactive"))))
    assert _get_model(jib)["fits_no_active_crane"] is True
    # The counterweight also fits the first crane model, whose cranes are active: not left behind.
    assert _get_model(fleet.counterweight_model)["fits_no_active_crane"] is False
    _publish(_upload(plum_report(fleet.report_rows() + [plum_row(number=fleet.number("CR9"), schedule=fleet.crane_name, category="CRANES", capacity="100")])))
    assert _get_model(jib)["fits_no_active_crane"] is False


# --- Retiring --------------------------------------------------------------------------------------


def test_retiring_a_piece_records_the_day_and_the_reason_and_keeps_it() -> None:
    fleet = KitFleet()
    hook = _added(fleet.hook_model, 1, serial_number=f"HB-{fleet.sfx}")[0]
    retired = _ok(_retire(hook, "SCRAPPED", retired_on=TODAY - timedelta(days=2), note=f"Failed its examination {fleet.sfx}"))
    piece = retired["machine"]
    assert piece["asset_status_code"] == "RETIRED"
    assert (piece["retired_on"], piece["retirement_reason_code"]) == ((TODAY - timedelta(days=2)).isoformat(), "SCRAPPED")
    assert piece["retirement_note"] == f"Failed its examination {fleet.sfx}"
    event = _events(hook["asset_public_id"])[-1]
    payload = _payload(event)
    assert event["event_name"] == "EQUIPMENT_ASSET_RETIRED"
    assert (payload["reason_code"], payload["quantity_retired"], payload["quantity_after"], payload["whole"]) == ("SCRAPPED", 1, 0, True)
    # The note is the event's reason, never its payload; the piece's number is in neither.
    assert fleet.sfx not in json.dumps(payload) and event["reason"] == f"Failed its examination {fleet.sfx}"
    # Retiring again returns it unchanged, whatever version is sent.
    again = _ok(_retire(hook, "LOST", version=1))
    assert again["event"] is None and again["machine"]["retirement_reason_code"] == "SCRAPPED"
    # A retired piece is not held, but is still there.
    assert _kit_of(fleet.crane_1)[fleet.hook_model["model_public_id"]]["pieces_held"] == 0
    assert _machine(hook["asset_public_id"])["asset_reference"] == hook["asset_reference"]


def test_retiring_needs_a_known_reason_a_note_with_other_and_no_future_day() -> None:
    fleet = KitFleet()
    insert = _added(fleet.insert_model, 1)[0]
    assert "Choose why" in _detail(_retire(insert, "BROKEN"))
    assert "required with Other" in _detail(_retire(insert, "OTHER"))
    assert "future" in _detail(_retire(insert, "LOST", retired_on=TODAY + timedelta(days=1)))
    assert _retire(insert, "SOLD", version=99).status_code == 409
    other = _ok(_retire(insert, "OTHER", note="Returned to the supplier."))
    assert other["machine"]["retirement_reason_code"] == "OTHER"


def test_plum_machines_retire_only_by_plum_report() -> None:
    fleet = KitFleet()
    assert "Plum retires this machine" in _detail(_retire(fleet.crane_1, "SOLD"))


def test_a_counted_set_shrinks_only_by_retiring_pieces_with_the_reason() -> None:
    fleet = KitFleet()
    block = _added(fleet.counterweight_model, 6)[0]
    assert "Use Retire" in _detail(_details(block, quantity=5))
    partial = _ok(_retire(block, "LOST", count=2))
    assert partial["machine"]["asset_status_code"] == "ACTIVE" and partial["machine"]["quantity"] == 4
    payload = _payload(_events(block["asset_public_id"])[-1])
    assert (payload["quantity_retired"], payload["quantity_after"], payload["whole"]) == (2, 4, False)
    assert "between 1 and 4" in _detail(_retire(block, "LOST", count=5))
    # A count recorded too low is raised in the details.
    raised = _ok(_details(block, quantity=7))
    assert raised["machine"]["quantity"] == 7
    said = raised["event"]["event_payload"]
    assert (said["changed_fields"], said["quantity_before"], said["quantity_after"]) == (["quantity"], 4, 7)
    whole = _ok(_retire(block, "SOLD"))
    assert whole["machine"]["asset_status_code"] == "RETIRED"
    assert "retired" in _detail(_details(block, quantity=8))


# --- Details and own ratings -----------------------------------------------------------------------


def test_a_pieces_number_model_and_details_to_complete() -> None:
    fleet = KitFleet()
    insert = _added(fleet.insert_model, 1)[0]
    block = _added(fleet.counterweight_model, 3)[0]
    assert insert["details_missing"] is True and block["details_missing"] is False
    to_complete = {item["asset_public_id"] for item in _list(details_to_complete=True, kit_model_public_id=fleet.insert_model["model_public_id"])}
    assert insert["asset_public_id"] in to_complete
    numbered = _ok(_details(insert, serial_number=f"INS-{fleet.sfx}"))["machine"]
    assert numbered["details_missing"] is False
    assert [item["asset_public_id"] for item in _list(search=f"INS-{fleet.sfx}")] == [insert["asset_public_id"]]
    assert "has no number of its own" in _detail(_details(block, serial_number="CW-1"))
    # Another model of the same kind; never one of another kind.
    longer = _model("ACME", f"CC 100 insert 12 m {fleet.sfx}", "BOOM_JIB_SECTION", type_code="MAIN_BOOM_INSERT", fits=[fleet.crane_model])
    moved = _ok(_details(insert, model_public_id=longer["model_public_id"]))["machine"]
    assert moved["model_public_id"] == longer["model_public_id"]
    assert "keeps its kind" in _detail(_details(insert, model_public_id=fleet.hook_model["model_public_id"]))
    # A Plum machine has no count or model of its own here.
    crane = _machine(fleet.crane_1["asset_public_id"])
    refused = client.put(
        f"{BASE}/machines/{crane['asset_public_id']}/details",
        json={"expected_asset_version": crane["asset_version"], "quantity": 2},
        headers=auth_headers(ADMIN),
    )
    assert "Only a piece of kit" in _detail(refused)


def test_a_piece_may_hold_its_own_rating_where_its_kind_has_one() -> None:
    fleet = KitFleet()
    hook = _added(fleet.hook_model, 1)[0]
    current = _machine(hook["asset_public_id"])
    derated = _ok(
        client.put(
            f"{BASE}/machines/{hook['asset_public_id']}/capabilities",
            json={
                "expected_asset_version": current["asset_version"],
                "capabilities": [{"capability_code": "RATED_CAPACITY", "value": "80", "reason": "De-rated after its examination."}],
            },
            headers=auth_headers(ADMIN),
        )
    )["machine"]
    rated = {item["capability_code"]: item for item in derated["capabilities"]}
    assert rated["RATED_CAPACITY"]["source_code"] == "OWN" and Decimal(rated["RATED_CAPACITY"]["value"]) == 80
    assert rated["WEIGHT"]["source_code"] == "MODEL"


# --- Fitted parts and the depth setting ------------------------------------------------------------


def _insert_plum_part(class_code: str, number: str) -> dict:
    with SessionLocal() as db:
        public_id = str(uuid.uuid4())
        db.execute(
            text(
                "INSERT INTO equipment_asset (asset_public_id, asset_kind_code, class_code, machine_number, asset_status_code) "
                "VALUES (:p, 'PART', :c, :n, 'ACTIVE')"
            ),
            {"p": public_id, "c": class_code, "n": number},
        )
        db.commit()
    return {"asset_public_id": public_id}


def _fit(parent: dict, part: dict):
    parent_now, part_now = _machine(parent["asset_public_id"]), _machine(part["asset_public_id"])
    return client.post(
        f"{BASE}/machines/{parent['asset_public_id']}/fitted-parts",
        json={
            "expected_asset_version": parent_now["asset_version"],
            "part_public_id": part["asset_public_id"],
            "expected_part_version": part_now["asset_version"],
            "fitted_on": TODAY.isoformat(),
        },
        headers=auth_headers(ADMIN),
    )


def _remove(parent: dict, part: dict):
    parent_now, part_now = _machine(parent["asset_public_id"]), _machine(part["asset_public_id"])
    return client.post(
        f"{BASE}/machines/{parent['asset_public_id']}/fitted-parts/{part['asset_public_id']}/remove",
        json={"expected_asset_version": parent_now["asset_version"], "expected_part_version": part_now["asset_version"], "removed_on": TODAY.isoformat()},
        headers=auth_headers(ADMIN),
    )


@contextmanager
def _part_classes_under_the_carrier() -> Iterator[tuple[str, str]]:
    """Two part classes for the depth rule - A fitted to Crane carrier, B fitted to A. Version 3 has no fit
    under a part (Q9), so they are made for the test and removed after it, with every record of them."""
    s = suffix()
    a, b = f"TEST_LEVEL_A_{s}", f"TEST_LEVEL_B_{s}"
    with SessionLocal() as db:
        db.execute(
            text(
                "INSERT INTO equipment_class (class_code, class_label, display_order, introduced_in_version, class_kind_code) "
                "VALUES (:a, 'Test level A', 900, 3, 'PART'), (:b, 'Test level B', 910, 3, 'PART')"
            ),
            {"a": a, "b": b},
        )
        db.execute(
            text(
                "INSERT INTO equipment_part_fit (part_class_code, parent_class_code, parent_class_kind_code, introduced_in_version) "
                "VALUES (:a, 'CRANE_CARRIER', 'PART', 3), (:b, :a, 'PART', 3)"
            ),
            {"a": a, "b": b},
        )
        db.commit()
    try:
        yield a, b
    finally:
        with SessionLocal() as db:
            assets = "SELECT id FROM equipment_asset WHERE class_code IN (:a, :b)"
            db.execute(text(f"DELETE FROM equipment_asset_link WHERE parent_asset_id IN ({assets}) OR child_asset_id IN ({assets})"), {"a": a, "b": b})
            db.execute(text(f"DELETE FROM equipment_asset_flag WHERE equipment_asset_id IN ({assets})"), {"a": a, "b": b})
            db.execute(text("DELETE FROM equipment_asset WHERE class_code IN (:a, :b)"), {"a": a, "b": b})
            db.execute(text("DELETE FROM equipment_part_fit WHERE part_class_code IN (:a, :b)"), {"a": a, "b": b})
            db.execute(text("DELETE FROM equipment_class WHERE class_code IN (:a, :b)"), {"a": a, "b": b})
            db.commit()


def test_kit_is_never_fitted_to_a_machine() -> None:
    fleet = KitFleet()
    insert = _added(fleet.insert_model, 1)[0]
    assert "Kit is not fitted" in _detail(_fit(fleet.crane_1, insert))


def test_parts_nest_no_deeper_than_the_setting_counting_what_hangs_below() -> None:
    fleet = KitFleet()
    with _part_classes_under_the_carrier() as (a_class, b_class):
        carrier = _insert_plum_part("CRANE_CARRIER", fleet.number("CAR"))
        a = _insert_plum_part(a_class, fleet.number("A"))
        b = _insert_plum_part(b_class, fleet.number("B"))
        _ok(_fit(fleet.crane_1, carrier), 201)  # levels 1 and 2
        _ok(_fit(a, b), 201)  # A, on nothing, carries B: 2 levels
        # A with B below it, on the carrier at level 2, would reach level 4.
        assert "at most 3 levels" in _detail(_fit(carrier, a))
        _ok(_remove(a, b))
        _ok(_fit(carrier, a), 201)  # level 3
        assert "at most 3 levels" in _detail(_fit(a, b))


def test_belongs_to_no_machine_is_never_raised_on_kit() -> None:
    fleet = KitFleet()
    pieces = _added(fleet.insert_model, 2) + _added(fleet.counterweight_model, 3)
    # A confirmed report recomputes the flag for every part.
    _publish(_upload(plum_report(fleet.report_rows() + [plum_row(number=fleet.number("CR8"), schedule=fleet.crane_name, category="CRANES", capacity="100")])))
    for piece in pieces:
        assert _machine(piece["asset_public_id"])["flags"] == []


# --- With the import --------------------------------------------------------------------------------


def test_a_report_neither_sees_nor_changes_kit() -> None:
    fleet = KitFleet()
    piece = _added(fleet.hook_model, 1)[0]
    waiting = _upload(plum_report(fleet.report_rows()[:2]))
    assert piece["asset_reference"] not in json.dumps(waiting["preview"])
    before = _machine(piece["asset_public_id"])
    _publish(waiting)
    after = _machine(piece["asset_public_id"])
    assert (after["asset_version"], after["asset_status_code"], after["flags"]) == (before["asset_version"], "ACTIVE", [])


def test_adding_and_retiring_kit_leaves_a_waiting_preview_current_and_a_kit_model_change_does_not() -> None:
    fleet = KitFleet()
    waiting = _upload(plum_report(fleet.report_rows() + [plum_row(number=fleet.number("CR7"), schedule=fleet.crane_name, category="CRANES", capacity="100")]))
    assert waiting["is_current"] is True
    piece = _added(fleet.insert_model, 1)[0]
    _ok(_details(piece, serial_number=f"S-{fleet.sfx}"))
    _ok(_retire(piece, "LOST"))
    assert _import(waiting["import_public_id"])["is_current"] is True
    _ok(_update_model(fleet.insert_model, maker_part_number=f"NEW-{fleet.sfx}"))
    assert _import(waiting["import_public_id"])["is_current"] is False


# --- Reads, permissions, events --------------------------------------------------------------------


def test_plum_machines_read_as_before_with_their_origin() -> None:
    fleet = KitFleet()
    crane = _machine(fleet.crane_1["asset_public_id"])
    assert (crane["origin_code"], crane["quantity"], crane["machine_number"]) == ("PLUM", 1, fleet.number("CR1"))
    assert crane["fits_models"] == [] and crane["retired_on"] is None


@pytest.mark.parametrize("username", READ_ROLES)
def test_every_read_role_reads_kit(username: str) -> None:
    fleet = KitFleet()
    piece = _added(fleet.insert_model, 1)[0]
    assert _machine(piece["asset_public_id"], username)["origin_code"] == "PLATFORM"
    assert _machine(fleet.crane_1["asset_public_id"], username)["kit"]


@pytest.mark.parametrize("username", NON_ADMIN_ROLES)
def test_every_kit_write_is_admins_only(username: str) -> None:
    fleet = KitFleet()
    piece = _added(fleet.insert_model, 1)[0]
    assert _add_kit(fleet.insert_model, 1, username=username).status_code == 403
    assert _retire(piece, "LOST", username=username).status_code == 403
    body = {"maker": "ACME", "model_name": f"x {fleet.sfx}", "class_code": "HOOK_BLOCK", "fits_model_public_ids": [fleet.crane_model["model_public_id"]]}
    assert _create_model(body, username=username).status_code == 403


def test_event_payloads_carry_no_piece_number_and_no_free_text() -> None:
    fleet = KitFleet()
    piece = _added(fleet.hook_model, 1, serial_number=f"HB-{fleet.sfx}")[0]
    registered = _events(piece["asset_public_id"])[0]
    payload = _payload(registered)
    assert registered["event_name"] == "EQUIPMENT_ASSET_REGISTERED"
    assert (payload["origin_code"], payload["class_code"], payload["model_public_id"], payload["quantity"]) == (
        "PLATFORM",
        "HOOK_BLOCK",
        fleet.hook_model["model_public_id"],
        1,
    )
    assert fleet.sfx not in json.dumps(payload)
    model_events = _events(fleet.counterweight_model["model_public_id"])
    recorded = _payload(model_events[0])
    assert set(recorded["fits_model_public_ids"]) == {fleet.crane_model["model_public_id"], fleet.other_crane_model["model_public_id"]}
