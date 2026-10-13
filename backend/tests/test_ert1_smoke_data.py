"""ERT-1 - the equipment record set of the TE-1 harness and its cleanup (TE-4 provenance).

The scenario records invented models, confirms an invented Plum report, and leaves a second invented
report in the manifest for someone to upload from the screen. Cleanup must remove everything the run made
- including what was made later from that second report: its import (by fingerprint), the machines it
brought in, the value rule recorded on its preview, the mapping to the run's model - and nothing another
run or a person made.
"""

from __future__ import annotations

import copy
import uuid

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.equipment_reference.contract import model_mapping_public_id
from tests.business_day_test_support import TODAY, held_to_the_test_day
from tests.equipment_test_support import equipment_created_here, plum_report, plum_row, suffix
from tests.test_commercial_offers_api import auth_headers, client
from tooling.smoke_data.builders import EquipmentSeedRefused
from tooling.smoke_data.cleanup import CleanupValidationError, cleanup_manifest
from tooling.smoke_data.scenarios import run_scenario
from tooling.smoke_data.status import check_manifest_status

BASE = "/api/equipment-reference"


@pytest.fixture(scope="module", autouse=True)
def _on_the_test_day():
    with held_to_the_test_day():
        yield


def _count(sql: str, **params) -> int:
    with SessionLocal() as db:
        return int(db.execute(text(sql), params).scalar_one())


def _token_rows(token: str) -> dict[str, int]:
    like = f"%{token}%"
    return {
        "assets": _count("SELECT COUNT(*) FROM equipment_asset WHERE machine_number ILIKE :like", like=like),
        # ERT-2: pieces of kit have no machine number; they are the run's by their model's name.
        "kit": _count(
            "SELECT COUNT(*) FROM equipment_asset a INNER JOIN equipment_model m ON m.id = a.equipment_model_id "
            "WHERE a.origin_code = 'PLATFORM' AND m.model_name ILIKE :like",
            like=like,
        ),
        "models": _count("SELECT COUNT(*) FROM equipment_model WHERE model_name ILIKE :like", like=like),
        "mappings": _count("SELECT COUNT(*) FROM equipment_model_source_key WHERE source_name ILIKE :like", like=like),
        "rules": _count("SELECT COUNT(*) FROM equipment_source_value_rule WHERE plum_value ILIKE :like", like=like),
        "import_rows": _count("SELECT COUNT(*) FROM equipment_source_import_row WHERE machine_number ILIKE :like", like=like),
    }


def _screen_flow(record: dict) -> dict:
    """What the tester does with the second report: upload, map the carrier's name, read the odd capacity,
    refresh, pair the carrier with its crane, confirm."""
    demo = record["equipment_demo"]
    admin = auth_headers("admin1")
    uploaded = client.post(
        f"{BASE}/imports",
        data={"report_date": TODAY.isoformat()},
        files={"file": (demo["second_report_file_name"], demo["second_report_csv"].encode("utf-8"), "text/csv")},
        headers=admin,
    )
    assert uploaded.status_code == 201, uploaded.text
    equipment_import = uploaded.json()["equipment_import"]
    assert client.put(
        f"{BASE}/model-mappings", json={"source_name": demo["chassis_model_name"], "model_public_id": demo["carrier_model_public_id"]}, headers=admin
    ).status_code == 200
    rule = client.put(
        f"{BASE}/value-rules",
        json={
            "column_code": "CAPACITY",
            "plum_value": demo["odd_capacity_value"],
            "action_code": "SPLIT_NUMBER_AND_UNIT",
            "result_number": "230",
            "result_unit_code": "KILOGRAM",
            "reason": "Kilograms, written with the unit.",
            "import_public_id": equipment_import["import_public_id"],
        },
        headers=admin,
    )
    assert rule.status_code == 200, rule.text
    refreshed = client.post(
        f"{BASE}/imports/{equipment_import['import_public_id']}/refresh", json={"expected_preview_version": equipment_import["preview_version"]}, headers=admin
    ).json()["equipment_import"]
    proposal = next(item for item in refreshed["preview"]["pair_proposals"] if item["part_machine_number"] == demo["carrier_machine_number"])
    assert proposal["proposed_machine_number"] == demo["crane_machine_number"]
    published = client.post(
        f"{BASE}/imports/{refreshed['import_public_id']}/publish",
        json={
            "expected_preview_version": refreshed["preview_version"],
            "pairs": [{"part_machine_number": demo["carrier_machine_number"], "machine_machine_number": demo["crane_machine_number"]}],
        },
        headers=admin,
    )
    assert published.status_code == 200, published.text
    return published.json()["equipment_import"]


def test_the_scenario_brings_invented_machines_in_and_cleanup_removes_all_it_made_even_later() -> None:
    manifest = run_scenario("equipment-plum-import")
    record = manifest["records"]["equipment_reference_target"]
    token = record["equipment_demo"]["token"]
    try:
        # ERT-1's three models, ERT-2's second crane model with its three kit models, ELG-1's wheeled crane
        # and carrier models and its sling model, 8A core's 250 t crawler model with its four kit models, and
        # ELG-2's 80 t crawler model with its sling model.
        assert len(record["equipment_models"]) == 17 and len(record["equipment_imports"]) == 1
        # Seven machines, 8A core's four crawlers and ELG-2's two; four pieces of kit, 8A core's five (a hook block,
        # a counted set of counterweight, two inserts and a sling) and ELG-2's sling.
        assert _token_rows(token)["assets"] == 7 + 4 + 2
        assert _token_rows(token)["kit"] == 4 + 5 + 1
        assert check_manifest_status(manifest)["all_present"] is True
        crane = client.get(f"{BASE}/machines", params={"search": record["equipment_demo"]["crane_machine_number"]}, headers=auth_headers("readonly1")).json()
        assert [item["model_label"] for item in crane] == [f"ACME AC 100 {token}"]

        published = _screen_flow(record)
        assert published["counts"]["NEW"] == 2
        assert _token_rows(token)["assets"] == 9 + 4 + 2
    finally:
        counts = cleanup_manifest(manifest)
    assert counts["equipment_models"] == 17
    assert counts["equipment_imports"] == 2
    # ELG-2 adds two crawlers and a sling, which fits their model, and the mapping of their model's name.
    assert counts["equipment_assets"] == 13 + 9 + 3
    assert counts["equipment_model_fits"] == 4 + 4 + 1
    assert counts["equipment_value_rules"] == 1
    assert counts["equipment_model_mappings"] == 6 + 1 + 1
    assert counts["equipment_asset_links"] == 2
    # ELG-1: seven certificates with their copies, and the second crawler's four marks; 8A core: eight certificates
    # on three of its crawlers and the hook block, and those crawlers' twelve marks; ELG-2: nine certificates on its two
    # crawlers and sling, and five marks. Nothing is allocated here.
    assert (counts["eligibility_certificates"], counts["eligibility_marks"], counts["eligibility_decisions"]) == (7 + 8 + 9, 4 + 12 + 5, 0)
    assert counts["business_events"] > 0
    assert _token_rows(token) == {"assets": 0, "kit": 0, "models": 0, "mappings": 0, "rules": 0, "import_rows": 0}
    assert _count(
        "SELECT COUNT(*) FROM business_event WHERE source_module = 'equipment_reference' AND record_public_id = :id",
        id=record["equipment_models"][0]["public_id"],
    ) == 0
    after = check_manifest_status(manifest)
    assert after["all_absent"] is True and after["residue_clear"] is True
    # Nothing left to delete is success, not failure.
    again = cleanup_manifest(manifest)
    assert all(count == 0 for key, count in again.items() if key.startswith("equipment_"))


def _written_rows() -> dict[str, int]:
    return {
        "models": _count("SELECT COUNT(*) FROM equipment_model"),
        "imports": _count("SELECT COUNT(*) FROM equipment_source_import"),
        "assets": _count("SELECT COUNT(*) FROM equipment_asset"),
        "offers": _count("SELECT COUNT(*) FROM crm_commercial_offer"),
        "accounts": _count("SELECT COUNT(*) FROM business_party"),
    }


@pytest.mark.parametrize("scenario", ["equipment-plum-import", "core-regression-bundle", "hiring-uat-seeded", "hiring-uat-fleet"])
def test_the_equipment_scenarios_refuse_to_seed_where_machines_are_held_or_a_preview_waits(scenario: str) -> None:
    """A confirmed report is the whole fleet: seeding over machines someone holds would flag them missing and
    discard their previews, which cleanup cannot undo (independent review, round 4). So the scenarios refuse,
    writing nothing - no CRM record either."""
    with equipment_created_here():
        sfx = suffix()
        waiting = client.post(
            f"{BASE}/imports",
            data={"report_date": TODAY.isoformat()},
            files={"file": ("held.csv", plum_report([plum_row(number=f"HELD-{sfx}", category="FORK LIFT", capacity="3")]), "text/csv")},
            headers=auth_headers("admin1"),
        ).json()["equipment_import"]
        before = _written_rows()
        _expect_refusal(scenario, "0 machine(s) are held and 1 Plum report preview")
        assert _written_rows() == before

        # Confirmed: a machine is held now, and no preview waits.
        assert client.post(
            f"{BASE}/imports/{waiting['import_public_id']}/publish",
            json={"expected_preview_version": waiting["preview_version"]},
            headers=auth_headers("admin1"),
        ).status_code == 200
        before = _written_rows()
        _expect_refusal(scenario, "1 machine(s) are held and 0 Plum report preview")
        assert _written_rows() == before


def _expect_refusal(scenario: str, words: str) -> None:
    """The scenario must refuse. Should it seed after all, what it seeded is removed before failing, so a
    broken refusal never leaves a run behind."""
    try:
        manifest = run_scenario(scenario)
    except EquipmentSeedRefused as refusal:
        assert words in str(refusal)
        return
    cleanup_manifest(manifest)
    pytest.fail(f"{scenario} seeded over machines someone holds.")


def test_cleanup_refuses_and_deletes_nothing_when_another_machine_uses_a_run_model() -> None:
    manifest = run_scenario("equipment-plum-import")
    record = manifest["records"]["equipment_reference_target"]
    crane_model = record["equipment_models"][0]["public_id"]
    try:
        with equipment_created_here():
            sfx = suffix()
            client.put(f"{BASE}/model-mappings", json={"source_name": f"{sfx} BORROWED", "model_public_id": crane_model}, headers=auth_headers("admin1"))
            borrowed = client.post(
                f"{BASE}/imports",
                data={"report_date": TODAY.isoformat()},
                files={"file": ("b.csv", plum_report([plum_row(number=f"BORROW-{sfx}", category="CRANES", schedule=f"{sfx} BORROWED", capacity="100")]), "text/csv")},
                headers=auth_headers("admin1"),
            ).json()["equipment_import"]
            assert client.post(f"{BASE}/imports/{borrowed['import_public_id']}/publish", json={"expected_preview_version": borrowed["preview_version"]}, headers=auth_headers("admin1")).status_code == 200
            with pytest.raises(CleanupValidationError, match="use its models"):
                cleanup_manifest(manifest)
            assert check_manifest_status(manifest)["all_present"] is True
    finally:
        cleanup_manifest(manifest)
    assert _token_rows(record["equipment_demo"]["token"])["models"] == 0


def test_kit_added_from_the_screen_later_is_the_runs_and_goes_with_it() -> None:
    """ERT-2: pieces of a run's kit model are the run's, whoever added them and when - found by their model,
    not by a name. The two cranes of the kit's crane model share it."""
    manifest = run_scenario("equipment-plum-import")
    record = manifest["records"]["equipment_reference_target"]
    kit = record["equipment_kit"]
    token = record["equipment_demo"]["token"]
    try:
        first, second = (_machine(number) for number in kit["crane_machine_numbers"])
        models = client.get(f"{BASE}/models", headers=auth_headers("admin1")).json()
        [hook] = [model for model in models if model["model_public_id"] == kit["hook_model_public_id"]]
        added = client.post(
            f"{BASE}/kit",
            json={
                "create_request_key": str(uuid.uuid4()),
                "machine_public_id": first["asset_public_id"],
                "expected_asset_version": first["asset_version"],
                "kit_model_public_id": hook["model_public_id"],
                "expected_model_version": hook["model_version"],
                "count": 2,
            },
            headers=auth_headers("admin1"),
        )
        assert added.status_code == 201, added.text
        assert _token_rows(token)["kit"] == 6 + 5 + 1
        held = client.get(f"{BASE}/machines/{first['asset_public_id']}", headers=auth_headers("readonly1")).json()
        assert held["model_active_unit_count"] == 2
        assert {item["label"]: item["pieces_held"] for item in held["kit"]} == {
            kit["insert_model_label"]: 2,
            kit["counterweight_model_label"]: 4,
            kit["hook_model_label"]: 2,
            f"LIFTCO Sling 10 t {token}": 1,
        }
        assert client.get(f"{BASE}/machines/{second['asset_public_id']}", headers=auth_headers("readonly1")).json()["kit"] == held["kit"]
    finally:
        counts = cleanup_manifest(manifest)
    # Seven machines from the first report, four pieces seeded and two added from the screen; 8A core's four
    # crawlers and five pieces; ELG-2's two crawlers and sling.
    assert counts["equipment_assets"] == 13 + 9 + 3
    assert _token_rows(token)["kit"] == 0
    assert check_manifest_status(manifest)["residue_clear"] is True


def test_cleanup_refuses_and_deletes_nothing_when_an_outside_kit_model_fits_a_run_crane_model() -> None:
    manifest = run_scenario("equipment-plum-import")
    record = manifest["records"]["equipment_reference_target"]
    crane_model = record["equipment_kit"]["crane_model_public_id"]
    outside = client.post(
        f"{BASE}/models",
        json={
            "maker": "OUTSIDE",
            "model_name": f"hook block {uuid.uuid4().hex[:8]}",
            "class_code": "HOOK_BLOCK",
            "capabilities": [],
            "fits_model_public_ids": [crane_model],
            "create_request_key": str(uuid.uuid4()),
        },
        headers=auth_headers("admin1"),
    ).json()["model"]
    try:
        with pytest.raises(CleanupValidationError, match="kit model\\(s\\) this run did not make fit its crane models"):
            cleanup_manifest(manifest)
        assert check_manifest_status(manifest)["all_present"] is True
    finally:
        with SessionLocal() as db:
            db.execute(
                text("DELETE FROM equipment_model_fit f USING equipment_model m WHERE m.id = f.kit_model_id AND m.model_public_id = :p"),
                {"p": outside["model_public_id"]},
            )
            db.execute(text("DELETE FROM equipment_model WHERE model_public_id = :p"), {"p": outside["model_public_id"]})
            db.commit()
        cleanup_manifest(manifest)
    assert _token_rows(record["equipment_demo"]["token"])["models"] == 0


def test_a_piece_is_the_runs_by_the_model_it_was_added_as_not_the_one_it_carries() -> None:
    """ERT-2 (independent review, round 3, ERT2-R3-002): cleanup judges a piece by the kit model its request
    asked for, which never changes. The run's piece moved to an outside model goes with the run; an outside
    piece moved onto a run's model makes cleanup refuse, and is kept."""
    manifest = run_scenario("equipment-plum-import")
    record = manifest["records"]["equipment_reference_target"]
    kit = record["equipment_kit"]
    admin = auth_headers("admin1")
    tag = uuid.uuid4().hex[:8]

    def new_model(**body) -> dict:
        response = client.post(f"{BASE}/models", json={"maker": "OUTSIDE", "capabilities": [], "create_request_key": str(uuid.uuid4()), **body}, headers=admin)
        assert response.status_code == 201, response.text
        return response.json()["model"]

    outside_crane = new_model(model_name=f"crane {tag}", class_code="CRANE")
    outside_insert = new_model(
        model_name=f"insert {tag}", class_code="BOOM_JIB_SECTION", type_code="MAIN_BOOM_INSERT",
        fits_model_public_ids=[outside_crane["model_public_id"]],
    )
    outside_piece = str(uuid.uuid4())
    try:
        [run_piece] = [
            item for item in client.get(f"{BASE}/machines", params={"search": kit["insert_references"][0]}, headers=admin).json()
            if item["asset_reference"] == kit["insert_references"][0]
        ]
        moved = client.put(
            f"{BASE}/machines/{run_piece['asset_public_id']}/details",
            json={"expected_asset_version": run_piece["asset_version"], "serial_number": None, "year_of_manufacture": None, "model_public_id": outside_insert["model_public_id"]},
            headers=admin,
        )
        assert moved.status_code == 200, moved.text
        # Someone else's piece, added as the outside model and moved onto the run's insert model since.
        with SessionLocal() as db:
            db.execute(
                text(
                    "INSERT INTO equipment_asset (asset_public_id, asset_kind_code, origin_code, class_code, type_code, "
                    "equipment_model_id, asset_status_code, create_request_key, create_request_position, create_request_model_id) "
                    "SELECT :p, 'PART', 'PLATFORM', 'BOOM_JIB_SECTION', 'MAIN_BOOM_INSERT', r.id, 'ACTIVE', :k, 1, o.id "
                    "FROM equipment_model r, equipment_model o WHERE r.model_public_id = :run AND o.model_public_id = :outside"
                ),
                {"p": outside_piece, "k": str(uuid.uuid4()), "run": _model_public_id(kit["insert_model_label"]), "outside": outside_insert["model_public_id"]},
            )
            db.commit()
        with pytest.raises(CleanupValidationError, match="use its models"):
            cleanup_manifest(manifest)
        assert check_manifest_status(manifest)["all_present"] is True
        with SessionLocal() as db:
            db.execute(text("DELETE FROM equipment_asset WHERE asset_public_id = :p"), {"p": outside_piece})
            db.commit()
        counts = cleanup_manifest(manifest)
        # Seven machines and four pieces - the one moved to the outside model among them - 8A core's four
        # crawlers and five pieces, and ELG-2's two crawlers and sling.
        assert counts["equipment_assets"] == 11 + 9 + 3
        assert _count("SELECT COUNT(*) FROM equipment_asset WHERE asset_public_id = :p", p=run_piece["asset_public_id"]) == 0
        assert _count("SELECT COUNT(*) FROM equipment_model WHERE model_name LIKE :like", like=f"% {tag}") == 2
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM equipment_asset WHERE asset_public_id = :p"), {"p": outside_piece})
            db.commit()
        cleanup_manifest(manifest)
        with SessionLocal() as db:
            for statement in (
                "DELETE FROM equipment_model_fit f USING equipment_model m WHERE m.id = f.kit_model_id AND m.model_public_id = :p",
                "DELETE FROM equipment_model_capability c USING equipment_model m WHERE m.id = c.equipment_model_id AND m.model_public_id = :p",
                "DELETE FROM equipment_model WHERE model_public_id = :p",
            ):
                for public_id in (outside_insert["model_public_id"], outside_crane["model_public_id"]):
                    db.execute(text(statement), {"p": public_id})
            db.commit()


def _model_public_id(label: str) -> str:
    [found] = [model for model in client.get(f"{BASE}/models", headers=auth_headers("admin1")).json() if model["label"] == label]
    return found["model_public_id"]


def _machine(number: str) -> dict:
    found = client.get(f"{BASE}/machines", params={"search": number, "limit": 50}, headers=auth_headers("admin1")).json()
    [summary] = [item for item in found if item["machine_number"] == number]
    return client.get(f"{BASE}/machines/{summary['asset_public_id']}", headers=auth_headers("admin1")).json()


def _fit(machine: dict, part: dict) -> None:
    response = client.post(
        f"{BASE}/machines/{machine['asset_public_id']}/fitted-parts",
        json={
            "expected_asset_version": machine["asset_version"],
            "part_public_id": part["asset_public_id"],
            "expected_part_version": part["asset_version"],
            "fitted_on": TODAY.isoformat(),
        },
        headers=auth_headers("admin1"),
    )
    assert response.status_code == 201, response.text


def _outside_fleet(sfx: str, *rows: dict) -> None:
    """Machines another run - or a person - brought in: an outside carrier model and its mapping, and a report."""
    carrier_model = client.post(
        f"{BASE}/models",
        json={"maker": "OUTSIDE", "model_name": f"OC {sfx}", "class_code": "CRANE_CARRIER", "capabilities": [], "create_request_key": str(uuid.uuid4())},
        headers=auth_headers("admin1"),
    ).json()["model"]
    client.put(f"{BASE}/model-mappings", json={"source_name": f"{sfx} OUTSIDE CHASSIS", "model_public_id": carrier_model["model_public_id"]}, headers=auth_headers("admin1"))
    uploaded = client.post(
        f"{BASE}/imports",
        data={"report_date": TODAY.isoformat()},
        files={"file": ("outside.csv", plum_report(list(rows)), "text/csv")},
        headers=auth_headers("admin1"),
    ).json()["equipment_import"]
    published = client.post(f"{BASE}/imports/{uploaded['import_public_id']}/publish", json={"expected_preview_version": uploaded["preview_version"]}, headers=auth_headers("admin1"))
    assert published.status_code == 200, published.text


def _run_state(record: dict, crane_public_id: str) -> tuple[dict[str, int], int]:
    events = _count("SELECT COUNT(*) FROM business_event WHERE record_public_id = :id", id=crane_public_id)
    return _token_rows(record["equipment_demo"]["token"]), events


def test_cleanup_refuses_and_deletes_nothing_when_an_outside_part_is_fitted_to_a_run_machine() -> None:
    manifest = run_scenario("equipment-plum-import")
    record = manifest["records"]["equipment_reference_target"]
    try:
        with equipment_created_here():
            sfx = suffix()
            _outside_fleet(sfx, plum_row(number=f"OUT-{sfx}-C", category="CRANES", schedule=f"{sfx} OUTSIDE CHASSIS"))
            crane = _machine(record["equipment_demo"]["crane_machine_number"])
            _fit(crane, _machine(f"OUT-{sfx}-C"))
            before = _run_state(record, crane["asset_public_id"])
            with pytest.raises(CleanupValidationError, match="fitted-part link"):
                cleanup_manifest(manifest)
            assert _run_state(record, crane["asset_public_id"]) == before
            assert check_manifest_status(manifest)["all_present"] is True
    finally:
        cleanup_manifest(manifest)
    assert _token_rows(record["equipment_demo"]["token"])["assets"] == 0


def test_cleanup_refuses_and_deletes_nothing_when_a_run_part_was_fitted_to_an_outside_machine() -> None:
    manifest = run_scenario("equipment-plum-import")
    record = manifest["records"]["equipment_reference_target"]
    demo = record["equipment_demo"]
    try:
        _screen_flow(record)
        with equipment_created_here():
            sfx = suffix()
            _outside_fleet(sfx, plum_row(number=f"OUT-{sfx}-M", category="CRANES", capacity="100"))
            crane, carrier = _machine(demo["crane_machine_number"]), _machine(demo["carrier_machine_number"])
            removed = client.post(
                f"{BASE}/machines/{crane['asset_public_id']}/fitted-parts/{carrier['asset_public_id']}/remove",
                json={"expected_asset_version": crane["asset_version"], "expected_part_version": carrier["asset_version"], "removed_on": TODAY.isoformat()},
                headers=auth_headers("admin1"),
            )
            assert removed.status_code == 200, removed.text
            # Removed as well as open: the link is history another record keeps, so it is not the run's to delete.
            outside = _machine(f"OUT-{sfx}-M")
            _fit(outside, _machine(demo["carrier_machine_number"]))
            before = _run_state(record, crane["asset_public_id"])
            with pytest.raises(CleanupValidationError, match="fitted-part link"):
                cleanup_manifest(manifest)
            assert _run_state(record, crane["asset_public_id"]) == before
            assert _count("SELECT COUNT(*) FROM equipment_asset WHERE machine_number = :number", number=f"OUT-{sfx}-M") == 1
    finally:
        cleanup_manifest(manifest)
    assert _token_rows(demo["token"])["assets"] == 0


def _mapping_count(source_name: str) -> int:
    return _count("SELECT COUNT(*) FROM equipment_model_source_key WHERE source_name = :name", name=source_name)


def test_cleanup_refuses_and_deletes_nothing_when_another_name_is_mapped_to_a_run_model() -> None:
    manifest = run_scenario("equipment-plum-import")
    record = manifest["records"]["equipment_reference_target"]
    crane_model = record["equipment_models"][0]["public_id"]
    sfx = suffix()
    try:
        # Someone maps a name of their own to the run's model; no machine uses it yet.
        client.put(f"{BASE}/model-mappings", json={"source_name": f"{sfx} REAL NAME", "model_public_id": crane_model}, headers=auth_headers("admin1"))
        before = _token_rows(record["equipment_demo"]["token"])
        with pytest.raises(CleanupValidationError, match="this run's reports do not carry"):
            cleanup_manifest(manifest)
        assert _mapping_count(f"{sfx} REAL NAME") == 1
        assert _token_rows(record["equipment_demo"]["token"]) == before
    finally:
        client.put(f"{BASE}/model-mappings", json={"source_name": f"{sfx} REAL NAME", "model_public_id": None}, headers=auth_headers("admin1"))
        cleanup_manifest(manifest)
    assert _token_rows(record["equipment_demo"]["token"])["models"] == 0


def test_cleanup_refuses_and_changes_nothing_when_another_preview_was_compared_with_a_run_import() -> None:
    manifest = run_scenario("equipment-plum-import")
    record = manifest["records"]["equipment_reference_target"]
    run_import = record["equipment_imports"][0]["public_id"]
    try:
        with equipment_created_here():
            sfx = suffix()
            waiting = client.post(
                f"{BASE}/imports",
                data={"report_date": TODAY.isoformat()},
                files={"file": ("w.csv", plum_report([plum_row(number=f"WAIT-{sfx}", category="CRANES", capacity="100")]), "text/csv")},
                headers=auth_headers("admin1"),
            ).json()["equipment_import"]
            assert waiting["based_on_import_public_id"] == run_import
            with pytest.raises(CleanupValidationError, match="compared with its imports"):
                cleanup_manifest(manifest)
            still = client.get(f"{BASE}/imports/{waiting['import_public_id']}", headers=auth_headers("admin1")).json()
            assert still["based_on_import_public_id"] == run_import
            assert check_manifest_status(manifest)["all_present"] is True
    finally:
        cleanup_manifest(manifest)
    assert _token_rows(record["equipment_demo"]["token"])["assets"] == 0


def test_cleanup_removes_a_mapping_of_a_run_name_whichever_model_it_points_at() -> None:
    manifest = run_scenario("equipment-plum-import")
    record = manifest["records"]["equipment_reference_target"]
    mystery = f"{record['equipment_demo']['token']} MYSTERY CRANE"
    # The run is cleaned up however the test ends: a failure before the cleanup under test must not leave it.
    try:
        _check_run_name_mapping_cleanup(manifest, mystery)
    finally:
        cleanup_manifest(manifest)


def _check_run_name_mapping_cleanup(manifest: dict, mystery: str) -> None:
    with equipment_created_here():
        sfx = suffix()
        outside = client.post(
            f"{BASE}/models",
            json={"maker": "OUTSIDE", "model_name": f"OM {sfx}", "class_code": "CRANE", "capabilities": [], "create_request_key": str(uuid.uuid4())},
            headers=auth_headers("admin1"),
        ).json()["model"]
        # A tester, on the screen, maps the run's unmapped name to a model that is not the run's.
        client.put(f"{BASE}/model-mappings", json={"source_name": mystery, "model_public_id": outside["model_public_id"]}, headers=auth_headers("admin1"))
        assert _mapping_count(mystery) == 1
        # The mapping's event is the mapping's own, not the outside model's (independent review, round 3).
        mapping_events = "SELECT COUNT(*) FROM business_event WHERE record_type = 'equipment_model_mapping' AND record_public_id = :id"
        mapping_id = model_mapping_public_id("PLUM", mystery)
        assert _count(mapping_events, id=mapping_id) == 1
        outside_events = _count("SELECT COUNT(*) FROM business_event WHERE record_public_id = :id", id=outside["model_public_id"])
        assert outside_events >= 1  # recorded when the model was
        cleanup_manifest(manifest)
        assert _mapping_count(mystery) == 0
        assert _count(mapping_events, id=mapping_id) == 0
        assert _count("SELECT COUNT(*) FROM equipment_model WHERE model_public_id = :id", id=outside["model_public_id"]) == 1
        assert _count("SELECT COUNT(*) FROM business_event WHERE record_public_id = :id", id=outside["model_public_id"]) == outside_events
        assert check_manifest_status(manifest)["residue_clear"] is True


def test_a_malformed_model_name_refuses_the_whole_manifest() -> None:
    manifest = run_scenario("equipment-plum-import")
    try:
        broken = copy.deepcopy(manifest)
        broken["records"]["equipment_reference_target"]["equipment_source_names"] = ["  "]
        with pytest.raises(CleanupValidationError, match="equipment_source_names"):
            cleanup_manifest(broken)
        assert check_manifest_status(manifest)["all_present"] is True
    finally:
        cleanup_manifest(manifest)


def test_a_malformed_fingerprint_refuses_the_whole_manifest() -> None:
    manifest = run_scenario("equipment-plum-import")
    try:
        broken = copy.deepcopy(manifest)
        broken["records"]["equipment_reference_target"]["equipment_report_fingerprints"] = ["not-a-fingerprint"]
        with pytest.raises(CleanupValidationError, match="SHA-256"):
            cleanup_manifest(broken)
        assert check_manifest_status(manifest)["all_present"] is True
    finally:
        cleanup_manifest(manifest)
