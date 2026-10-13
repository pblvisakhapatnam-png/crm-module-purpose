"""ELG-1 - the certificates of the TE-1 harness's equipment record set, and their cleanup (TE-4 provenance).

`equipment-plum-import` and the core bundle's seventh record set seed a wheeled crane with its fitted carrier -
road papers on the carrier, the thorough examination on the crane, each with a copy, but no load test - the
second crawler crane's road papers marked not applicable, and a sling's examinations. A certificate, a mark and
a stored decision are the run's by the asset they are on, whoever recorded them; cleanup removes them with
their copies, and refuses, deleting nothing, when a decision about a machine the run did not bring in used one
of the run's assets.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal
from tests.business_day_test_support import TODAY, held_to_the_test_day
from tests.test_commercial_offers_api import auth_headers, client
from tooling.smoke_data.cleanup import CleanupValidationError, cleanup_manifest
from tooling.smoke_data.scenarios import run_scenario
from tooling.smoke_data.status import check_manifest_status

BASE = "/api/eligibility"
PDF = b"%PDF-1.4\n% invented copy\n%%EOF\n"


@pytest.fixture(scope="module", autouse=True)
def _on_the_test_day():
    with held_to_the_test_day():
        yield


def _count(sql: str, **params) -> int:
    with SessionLocal() as db:
        return int(db.execute(text(sql), params).scalar_one())


def _stored_file_count() -> int:
    root = Path(get_settings().document_storage_root)
    return sum(1 for path in root.rglob("*") if path.is_file()) if root.exists() else 0


def _asset(machine_number: str) -> str:
    with SessionLocal() as db:
        return str(db.execute(text("SELECT asset_public_id FROM equipment_asset WHERE machine_number = :n"), {"n": machine_number}).scalar_one())


def _check(asset: str) -> dict:
    params = {"state_code": "IN-GJ", "period_from": (TODAY + timedelta(days=2)).isoformat(), "period_to": (TODAY + timedelta(days=20)).isoformat()}
    response = client.get(f"{BASE}/assets/{asset}/check", params=params, headers=auth_headers("readonly1"))
    assert response.status_code == 200, response.text
    return response.json()


def _record_with_copy(asset: str, kind: str) -> str:
    body = {
        "create_request_key": str(uuid.uuid4()),
        "kind_code": kind,
        "number": "LT-ON-SCREEN",
        "issued_by": "Invented Competent Person",
        "issued_on": TODAY.isoformat(),
        "valid_from": TODAY.isoformat(),
        "valid_until": None,
    }
    response = client.post(f"{BASE}/assets/{asset}/certificates", json=body, headers=auth_headers("admin1"))
    assert response.status_code == 201, response.text
    certificate = response.json()["certificate_public_id"]
    upload = client.post(
        "/api/documents/upload",
        data={"linked_record_type": "eligibility_certificate", "linked_record_public_id": certificate, "document_type": "CERTIFICATE"},
        files={"file": ("load-test.pdf", PDF, "application/pdf")},
        headers=auth_headers("admin1"),
    )
    assert upload.status_code == 201, upload.text
    return certificate


def test_the_seeded_crane_waits_only_for_its_load_test_and_cleanup_removes_every_certificate_mark_and_copy() -> None:
    files_before = _stored_file_count()
    manifest = run_scenario("equipment-plum-import")
    record = manifest["records"]["equipment_reference_target"]
    seeded = record["equipment_eligibility"]
    try:
        crane = seeded["crane_public_id"]
        blocked = _check(crane)
        assert blocked["overall_code"] == "BLOCKED"
        assert {item["kind_code"]: item["outcome_code"] for item in blocked["results"] if item["outcome_code"] != "VALID"} == {"LOAD_TEST": "MISSING"}
        # The road papers are the carrier's, and count for its crane.
        registration = next(item for item in blocked["results"] if item["kind_code"] == "REGISTRATION")
        assert registration["certificate_asset_reference"] is not None
        marked = _check(seeded["marked_crawler_public_id"])
        assert {item["kind_code"] for item in marked["results"] if item["outcome_code"] == "NOT_APPLICABLE"} == {
            "REGISTRATION", "INSURANCE", "POLLUTION_UNDER_CONTROL", "ROAD_TAX"
        }
        due = client.get(f"{BASE}/certificates-due", params={"search": seeded["sling_reference"]}, headers=auth_headers("readonly1")).json()
        assert [(item["kind_code"], item["band_code"]) for item in due["items"]] == [("THOROUGH_EXAMINATION", "WITHIN_60")]

        # As the Playwright test and the tester do: a load test with its copy, and a mark on the other crawler.
        on_screen = _record_with_copy(crane, "LOAD_TEST")
        assert _check(crane)["overall_code"] == "ELIGIBLE"
        open_crawler = _asset(seeded["open_crawler_machine_number"])
        mark = client.post(
            f"{BASE}/assets/{open_crawler}/not-applicable",
            json={"create_request_key": str(uuid.uuid4()), "kind_code": "INSURANCE", "reason": "Tracked.", "until": None},
            headers=auth_headers("admin1"),
        )
        assert mark.status_code == 201, mark.text
        # Seven seeded copies and the one added here, the eight copies of the certificates 8A core's cranes and
        # hook block carry, and the nine of ELG-2's crawlers and sling.
        assert _stored_file_count() == files_before + 8 + 8 + 9
    finally:
        counts = cleanup_manifest(manifest)
    # 8A core adds eight certificates (two examinations on each of three cranes, two on the hook block) and twelve
    # marks (the four road papers of each of those cranes); ELG-2 nine certificates (four on its first crawler, three
    # on its second, two on its sling) and five marks.
    assert (counts["eligibility_certificates"], counts["eligibility_marks"]) == (8 + 8 + 9, 5 + 12 + 5)
    assert _count("SELECT COUNT(*) FROM eligibility_certificate WHERE certificate_public_id = :id", id=on_screen) == 0
    assert _count("SELECT COUNT(*) FROM document_metadata WHERE linked_record_type = 'eligibility_certificate' AND linked_record_public_id = :id", id=on_screen) == 0
    assert _count("SELECT COUNT(*) FROM business_event WHERE record_type LIKE 'eligibility_%' AND record_public_id = :id", id=on_screen) == 0
    assert _stored_file_count() == files_before
    after = check_manifest_status(manifest)
    assert after["all_absent"] is True and after["residue_clear"] is True


@pytest.mark.parametrize("shape", ["result-about-the-run-part", "result-met-by-the-run-certificate"])
def test_cleanup_refuses_and_deletes_nothing_when_another_machines_decision_used_a_run_asset(shape: str) -> None:
    """Both shapes record_decision stores (independent review, round 3, ELG1-R3-004): a result about a part of the
    unit - the run's carrier fitted to an outside machine when it was judged - and a result about the outside
    machine itself whose requirement was met by a certificate on the run's carrier."""
    manifest = run_scenario("equipment-plum-import")
    seeded = manifest["records"]["equipment_reference_target"]["equipment_eligibility"]
    outside = str(uuid.uuid4())
    try:
        with SessionLocal() as db:
            admin = db.execute(text("SELECT public_id FROM app_user WHERE username = 'admin1'")).scalar_one()
            db.execute(
                text(
                    "INSERT INTO equipment_asset (asset_public_id, asset_kind_code, origin_code, class_code, machine_number, asset_status_code) "
                    "VALUES (:p, 'MACHINE', 'PLUM', 'CRANE', :n, 'ACTIVE')"
                ),
                {"p": outside, "n": f"OUTSIDE-{outside[:8]}"},
            )
            decision_id = db.execute(
                text(
                    "INSERT INTO eligibility_decision (decision_public_id, equipment_asset_public_id, asset_version, site_state_code, "
                    "central_government_site, period_from, evaluated_on, evaluated_at, requested_by, overall_code) "
                    "VALUES (:d, :p, 1, 'IN-GJ', FALSE, :today, :today, now(), :admin, 'BLOCKED') RETURNING id"
                ),
                {"d": str(uuid.uuid4()), "p": outside, "today": TODAY, "admin": admin},
            ).scalar_one()
            rule_id = db.execute(text("SELECT id FROM eligibility_rule WHERE kind_code = 'INSURANCE' AND class_code = 'CRANE' AND type_code IS NULL AND jurisdiction_code IS NULL")).scalar_one()
            if shape == "result-about-the-run-part":
                db.execute(
                    text(
                        "INSERT INTO eligibility_decision_result (decision_id, result_number, equipment_asset_public_id, kind_code, rule_id, "
                        "outcome_code, lapse_code, effect_code) VALUES (:d, 1, :carrier, 'INSURANCE', :rule, 'MISSING', 'BLOCK', 'BLOCK')"
                    ),
                    {"d": decision_id, "carrier": seeded["carrier_public_id"], "rule": rule_id},
                )
            else:
                certificate_id = db.execute(
                    text("SELECT id FROM eligibility_certificate WHERE equipment_asset_public_id = :carrier AND kind_code = 'INSURANCE'"),
                    {"carrier": seeded["carrier_public_id"]},
                ).scalar_one()
                db.execute(
                    text(
                        "INSERT INTO eligibility_decision_result (decision_id, result_number, equipment_asset_public_id, kind_code, rule_id, "
                        "certificate_id, outcome_code, lapse_code, effect_code, cover_ends_on) "
                        "VALUES (:d, 1, :outside, 'INSURANCE', :rule, :certificate, 'VALID', 'BLOCK', 'NONE', :today)"
                    ),
                    {"d": decision_id, "outside": outside, "rule": rule_id, "certificate": certificate_id, "today": TODAY},
                )
            db.commit()
        certificates_before = _count("SELECT COUNT(*) FROM eligibility_certificate")
        with pytest.raises(CleanupValidationError, match="eligibility decision"):
            cleanup_manifest(manifest)
        assert _count("SELECT COUNT(*) FROM eligibility_certificate") == certificates_before
        assert check_manifest_status(manifest)["all_present"] is True
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM eligibility_decision_result r USING eligibility_decision d WHERE d.id = r.decision_id AND d.equipment_asset_public_id = :p"), {"p": outside})
            db.execute(text("DELETE FROM eligibility_decision WHERE equipment_asset_public_id = :p"), {"p": outside})
            db.execute(text("DELETE FROM equipment_asset WHERE asset_public_id = :p"), {"p": outside})
            db.commit()
        cleanup_manifest(manifest)
    assert check_manifest_status(manifest)["all_absent"] is True
