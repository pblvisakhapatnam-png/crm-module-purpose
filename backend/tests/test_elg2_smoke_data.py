"""ELG-2 - the certificate reminders' records in the TE-1 harness, and their cleanup (TE-4 provenance).

The scenario `equipment-allocation` (and the core bundle) seeds two invented 80 t crawlers: one whose papers run out
in 20, 10 and 5 days with a load test run out, and one held on reminder_target's job, whose insurance runs out before
the job starts, with a sling whose examination runs out during it. A "seen" mark is about the run's asset, allocation
or kit line, whoever made it, and goes with the run.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.core.database import SessionLocal
from tests.test_commercial_offers_api import auth_headers, client
from tooling.smoke_data.cleanup import cleanup_manifest
from tooling.smoke_data.scenarios import run_scenario
from tooling.smoke_data.status import check_manifest_status

ALERTS = "/api/eligibility/alerts"


def _ok(response, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


def _items(username: str, search: str) -> list[dict]:
    return _ok(client.get(ALERTS, params={"search": search, "limit": 500}, headers=auth_headers(username)))["items"]


def _seen_marks(public_ids: list[str]) -> int:
    with SessionLocal() as db:
        return int(
            db.execute(
                text(
                    "SELECT COUNT(*) FROM eligibility_alert_acknowledgement "
                    "WHERE equipment_asset_public_id = ANY(:ids) OR subject_public_id = ANY(:ids)"
                ),
                {"ids": public_ids},
            ).scalar_one()
        )


def test_the_seeded_reminders_reach_whom_they_should_and_cleanup_removes_every_seen_mark_on_them() -> None:
    manifest = run_scenario("equipment-allocation")
    demo = manifest["records"]["reminder_target"]["reminder_demo"]
    machines = demo["machines"]
    try:
        operations = {item["kind_code"]: item for item in _items("ops1", demo["machine_numbers"]["running_out"])}
        assert set(operations) == {"POLLUTION_UNDER_CONTROL", "THOROUGH_EXAMINATION", "LOAD_TEST"}
        management = {item["kind_code"] for item in _items("readonly1", demo["machine_numbers"]["running_out"])}
        assert management == {"THOROUGH_EXAMINATION", "LOAD_TEST"}

        job = _items("ops1", demo["assignment_reference"])
        kinds = {(item["reminder_kind_code"], item["kind_code"], item["allocation"]["kit_line_public_id"]) for item in job}
        assert kinds == {
            ("BEFORE_JOB_STARTS", "INSURANCE", None),
            ("DURING_JOB", "THOROUGH_EXAMINATION", demo["kit_line_public_id"]),
        }
        # Management is reached 7 days before: the insurance (6 days), not the sling (25).
        assert {item["kind_code"] for item in _items("readonly1", demo["assignment_reference"])} == {"INSURANCE"}

        # A tester marks one on the renewal list and one on the job as seen.
        pairs = [operations["LOAD_TEST"], next(item for item in job if item["allocation"]["kit_line_public_id"])]
        body = {"items": [{"reminder_key": item["reminder_key"], "reminder_on": item["reminder_on"]} for item in pairs]}
        assert _ok(client.post(f"{ALERTS}/seen", json=body, headers=auth_headers("ops1")))["marked"] == 2
        assert _seen_marks([machines["running_out"], demo["kit_line_public_id"]]) == 2
    finally:
        counts = cleanup_manifest(manifest)
    assert counts["eligibility_alert_acknowledgements"] == 2
    assert _seen_marks([machines["running_out"], machines["on_job"], demo["kit_line_public_id"], demo["assignment_public_id"]]) == 0
    status = check_manifest_status(manifest)
    assert status["all_absent"] is True and status["residue_clear"] is True
