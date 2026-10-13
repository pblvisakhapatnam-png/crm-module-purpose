"""8A core - the allocation record set of the TE-1 harness and its cleanup (TE-4 provenance).

The scenario `equipment-allocation` (and the core bundle's `allocation_target`) seeds a Work Order with a
requirement for two 250 t-class crawler cranes and the invented cranes and kit to fill it, and allocates nothing.
An allocation is the run's by the run's requirement it fills, whoever made it - the harness, a tester or a
Playwright test - and its trips, kit lines and stored decisions go with it. An allocation of a requirement the run
did not make that holds, or held, a run's machine makes cleanup refuse, deleting nothing.
"""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from tests.test_8a_equipment_allocation import crane_work_order
from tests.test_commercial_offers_api import auth_headers, client
from tooling.smoke_data.cleanup import CleanupValidationError, cleanup_manifest
from tooling.smoke_data.scenarios import run_scenario
from tooling.smoke_data.status import check_manifest_status

URL = "/api/resource-assignments"


def _ok(response, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


def _count(sql: str, **params) -> int:
    with SessionLocal() as db:
        return int(db.execute(text(sql), params).scalar_one())


def _allocate(requirement_public_id: str, machine_public_id: str, *, accept_warnings: bool = False) -> dict:
    requirement = _ok(client.get(f"/api/resource-requirements/{requirement_public_id}", headers=auth_headers("ops1")))
    body = {
        "create_request_key": str(uuid.uuid4()),
        "requirement_public_id": requirement_public_id,
        "unit_number": 1,
        "machine_public_id": machine_public_id,
        "planned_from": requirement["required_from"],
        "planned_to": None,
        "accept_warnings": accept_warnings,
    }
    return _ok(client.post(URL, json=body, headers=auth_headers("ops1")), 201)["assignment"]


def test_allocations_made_later_are_the_runs_and_cleanup_removes_them_with_their_kit_and_decisions() -> None:
    manifest = run_scenario("equipment-allocation")
    demo = manifest["records"]["allocation_target"]["allocation_demo"]
    machines = demo["machines"]
    requirement = demo["requirement_public_id"]
    try:
        seeded = _ok(client.get(f"/api/resource-requirements/{requirement}", headers=auth_headers("ops1")))
        assert (seeded["requirement_status_code"], seeded["units_covered"]) == ("OPEN", 0)

        # As the tester and the Playwright test do: the crane whose examination runs out during the job, with the
        # tick; the hook block on its first trip; then a breakdown, and another crane from the same first day.
        held = _allocate(requirement, machines["warns"], accept_warnings=True)
        assert held["decision"]["overall_code"] == "WARNING"
        options = _ok(client.get(f"{URL}/{held['assignment_public_id']}/kit-options", params={"trip_number": 1}, headers=auth_headers("ops1")))
        [hook] = [item for item in options["pieces"] if item["piece"]["asset_reference"] == demo["kit"]["hook"]]
        assert hook["available"] is True and hook["answer"]["overall_code"] == "ELIGIBLE"
        listed = client.post(
            f"{URL}/{held['assignment_public_id']}/kit",
            json={
                "create_request_key": str(uuid.uuid4()),
                "expected_assignment_version": held["assignment_version"],
                "trip_number": 1,
                "pieces": [{"piece_public_id": hook["piece"]["asset_public_id"], "quantity": 1}],
                "accept_warnings": False,
            },
            headers=auth_headers("ops1"),
        )
        assert listed.status_code == 201, listed.text
        replaced = _ok(
            client.post(
                f"{URL}/{held['assignment_public_id']}/replace",
                json={
                    "create_request_key": str(uuid.uuid4()),
                    "expected_assignment_version": listed.json()["assignment"]["assignment_version"],
                    "machine_public_id": machines["ok_1"],
                    "replace_from": held["planned_from"],
                    "reason_code": "BREAKDOWN",
                    "accept_warnings": False,
                },
                headers=auth_headers("ops1"),
            ),
            201,
        )["assignment"]
        assert replaced["replaces"]["assignment_public_id"] == held["assignment_public_id"]
        # The status moved with the allocations; a unit of two is covered.
        after = _ok(client.get(f"/api/resource-requirements/{requirement}", headers=auth_headers("ops1")))
        assert (after["requirement_status_code"], after["units_covered"], after["units_remaining"]) == ("PARTLY_FULFILLED", 1, 1)
        ids = [held["assignment_public_id"], replaced["assignment_public_id"]]
    finally:
        counts = cleanup_manifest(manifest)

    # The two made here, and ELG-2's reminder_target's held allocation with its sling on its first trip.
    assert counts["resource_assignments"] == 2 + 1
    assert counts["resource_assignment_trips"] == 2 + 1
    assert counts["resource_assignment_kit_lines"] == 1 + 1
    # Three request keys - the allocation, the kit and the replacement - go with the run's requirement (8A-R3-002), and
    # reminder_target's two with its own.
    assert counts["resource_assignment_requests"] == 3 + 2
    assert _count("SELECT COUNT(*) FROM resource_assignment_request WHERE resource_requirement_public_id = :r", r=requirement) == 0
    # Three stored decisions: each allocation's machine, and the hook block's; and reminder_target's crane and sling.
    assert counts["eligibility_decisions"] == 3 + 2
    assert _count("SELECT COUNT(*) FROM resource_assignment WHERE assignment_public_id = ANY(:ids)", ids=ids) == 0
    assert _count(
        "SELECT COUNT(*) FROM eligibility_decision WHERE requested_for_type LIKE 'resource_assignment%' "
        "AND requested_for_public_id = ANY(:ids)",
        ids=ids,
    ) == 0
    assert _count("SELECT COUNT(*) FROM business_event WHERE record_type = 'resource_assignment' AND record_public_id = ANY(:ids)", ids=ids) == 0
    status = check_manifest_status(manifest)
    assert status["all_absent"] is True and status["residue_clear"] is True


def test_cleanup_refuses_and_deletes_nothing_when_another_requirement_held_a_run_machine() -> None:
    manifest = run_scenario("equipment-allocation")
    machines = manifest["records"]["allocation_target"]["allocation_demo"]["machines"]
    try:
        with crane_work_order() as outside:
            # A person allocates one of the run's cranes to a Work Order the run did not make, then frees it: the
            # freed allocation keeps the crane on that Work Order's history.
            held = _allocate(outside["requirement"]["requirement_public_id"], machines["ok_2"])
            freed = client.post(
                f"{URL}/{held['assignment_public_id']}/release",
                json={"expected_assignment_version": held["assignment_version"], "last_day": None, "reason_code": "NOT_NEEDED"},
                headers=auth_headers("ops1"),
            )
            assert freed.status_code == 200, freed.text
            with pytest.raises(CleanupValidationError, match="Nothing was deleted"):
                cleanup_manifest(manifest)
            status = check_manifest_status(manifest)
            assert status["all_present"] is True
            assert _count("SELECT COUNT(*) FROM equipment_asset WHERE asset_public_id = :p", p=machines["ok_2"]) == 1
        # The outside Work Order and its allocation are gone: nothing holds the run's cranes any more.
    finally:
        counts = cleanup_manifest(manifest)
    # Only ELG-2's reminder_target's own held allocation, which the run made.
    assert counts["resource_assignments"] == 1
    status = check_manifest_status(manifest)
    assert status["all_absent"] is True and status["residue_clear"] is True


def test_the_harness_loads_the_allocation_module_itself_without_the_api() -> None:
    """The harness runs as `python -m tooling.smoke_data`, without app.main. Resource Requirements reads coverage
    through the port the allocation module registers when imported, and fails closed without it - which stopped
    the E2E suite's seeding before the harness loaded the module itself. A fresh interpreter proves it: this test
    session has app.main loaded already."""
    program = "; ".join(
        (
            "import tooling.smoke_data.scenarios",
            "from app.modules.resource_requirements.ports import assignment_port",
            "print(type(assignment_port()).__name__)",
        )
    )
    ran = subprocess.run(
        [sys.executable, "-c", program], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=120
    )
    assert ran.returncode == 0, ran.stderr
    assert ran.stdout.strip() == "_AssignmentPort"
