"""TE-7 - the Hiring user test's practice data (`hiring-uat-seeded`), and its cleanup.

The user guide and the testers' sheets (docs/uat-hiring/) name these records and say what each shows, so these tests
pin what they say: each machine's answer at the central-government refinery line in Gujarat, the only 250 t crawler
left for a new job, the kit a second crawler may take, how far each "not yet recorded" reminder has escalated, who is
reached by none, and each site's central-government answer. Cleanup must leave every table the run wrote as it found
it. The second Plum report the Fleet Admin uploads is the file in docs/uat-hiring/, byte for byte.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import uuid4
from typing import Any

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal
from tests.test_accounts_api import cleanup_test_accounts, create_test_account
from tests.test_commercial_offers_api import auth_headers, client
from tooling.smoke_data.cleanup import cleanup_manifest
from tooling.smoke_data.hiring_uat import SECOND_REPORT_FILE, second_plum_report
from tooling.smoke_data.scenarios import run_scenario
from tooling.smoke_data.status import check_manifest_status

# Reference data and the accounts: not the run's to write or to remove. The run's business events are its own, and
# cleanup removes them by record type and id (cleanup._EVENT_RECORD_TYPES), so business_event is counted too.
NOT_THE_RUNS = {
    "alembic_version", "app_user", "authz_permission", "authz_role_permission", "role", "user_role", "workflow_status",
    "tc_clause_library", "eligibility_alert_band", "eligibility_alert_setting", "eligibility_alert_step",
    "eligibility_certificate_kind", "eligibility_jurisdiction", "eligibility_rule", "equipment_capability",
    "equipment_class", "equipment_class_business_line", "equipment_class_capability", "equipment_reference_state",
    "equipment_source_category_rule", "equipment_taxonomy_version", "equipment_term_alias", "equipment_type",
}  # fmt: skip

DOCS = Path(os.environ.get("PBL_DOCS_DIR") or Path(__file__).resolve().parents[2] / "docs")

# Signed in once, before the rows are counted: each sign-in records a business event of its own, which is the
# test's, not the run's (independent review, TE-7 round 1).
HEADERS: dict[str, dict[str, str]] = {}


def _sign_in(*usernames: str) -> None:
    for username in usernames:
        HEADERS[username] = auth_headers(username)


def _snapshot() -> dict[str, str]:
    """Every in-scope table's whole contents - its row count and a digest of every row's every value, in a stable
    order - and the document store's files with their digests. A cleanup that left a row or a file, or changed or
    removed one it did not make, differs here (independent review, TE-7 round 4)."""
    with SessionLocal() as db:
        tables = db.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")
        ).scalars().all()
        snapshot = {
            table: str(
                db.execute(
                    text(f"""SELECT COUNT(*) || ':' || COALESCE(md5(string_agg(t::text, '|' ORDER BY t::text)), '') FROM "{table}" t""")
                ).scalar_one()
            )
            for table in tables
            if table not in NOT_THE_RUNS
        }
    store = Path(get_settings().document_storage_root)
    files = sorted(path for path in store.rglob("*") if path.is_file()) if store.is_dir() else []
    snapshot["document store files"] = "|".join(
        f"{path.relative_to(store).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}" for path in files
    )
    return snapshot


def _public_id(table: str, id_column: str, code_column: str, code: str) -> str:
    with SessionLocal() as db:
        return str(db.execute(text(f"SELECT CAST({id_column} AS text) FROM {table} WHERE {code_column} = :code"), {"code": code}).scalar_one())


def _ok(response) -> Any:
    assert response.status_code == 200, response.text
    return response.json()


def _not_valid(answer: dict | None) -> set[tuple[str, str]]:
    return {(result["kind_code"], result["outcome_code"]) for result in (answer or {}).get("results", []) if result["outcome_code"] not in ("VALID", "NOT_APPLICABLE", "NOT_REQUIRED")}


def _machines_for(requirement_reference: str) -> dict[str, tuple[bool, str | None, set[tuple[str, str]]]]:
    requirement = _public_id("resource_requirement", "requirement_public_id", "requirement_reference", requirement_reference)
    body = _ok(client.get("/api/resource-assignments/candidates", params={"requirement_public_id": requirement, "unit_number": 1}, headers=HEADERS["ops1"]))
    return {
        item["machine"]["machine_number"]: (item["available"], (item["answer"] or {}).get("overall_code"), _not_valid(item["answer"]))
        for item in body["candidates"]
    }


def _not_yet_recorded(username: str, numbers: set[str]) -> set[str]:
    items = _ok(client.get("/api/eligibility/alerts", params={"limit": 500}, headers=HEADERS[username]))["items"]
    return {item["asset"]["machine_number"] for item in items if item["reminder_kind_code"] == "NOT_YET_RECORDED"} & numbers


def _central_answers(work_order_code: str) -> list[bool | None]:
    with SessionLocal() as db:
        return list(
            db.execute(
                text(
                    "SELECT d.site_central_government FROM crm_work_order_line_detail d "
                    "JOIN crm_work_order_line l ON l.id = d.work_order_line_id JOIN crm_work_order w ON w.id = l.work_order_id "
                    "WHERE w.work_order_code = :code ORDER BY l.line_number"
                ),
                {"code": work_order_code},
            ).scalars()
        )


def test_the_practice_data_shows_what_the_guide_says_and_cleanup_leaves_every_table_as_it_was() -> None:
    _sign_in("ops1", "admin1", "readonly1", "sales1", "finance1")
    # Sentinels the run did not make, which cleanup must leave exactly as they are: an Account (with its own business
    # event) and a stored file. The sign-ins' events above are such rows too.
    sentinel = create_test_account()
    sentinel_file = Path(get_settings().document_storage_root) / "te7-sentinel" / f"{uuid4()}.txt"
    sentinel_file.parent.mkdir(parents=True, exist_ok=True)
    sentinel_file.write_bytes(b"not the practice data's")
    try:
        _check_the_practice_data_and_its_cleanup()
    finally:
        sentinel_file.unlink(missing_ok=True)
        if not any(sentinel_file.parent.iterdir()):
            sentinel_file.parent.rmdir()
        cleanup_test_accounts([str(sentinel["public_id"])])


def _check_the_practice_data_and_its_cleanup() -> None:
    before = _snapshot()
    manifest = run_scenario("hiring-uat-seeded")
    demo = manifest["records"]["hiring_demo"]
    try:
        # Guide 4.2, 4.3, 4.6 - every answer at the central-government refinery line in Gujarat (Sheet 1, Part B).
        refinery = _machines_for(demo["hu1"]["requirements"]["shutdown_open"])
        assert {number: overall for number, (_, overall, _) in refinery.items()} == {
            "UAT-AC100-01": "ELIGIBLE", "UAT-AC100-03": "ELIGIBLE",
            "UAT-AC100-06": "WARNING", "UAT-AC100-07": "WARNING",
            "UAT-AC100-02": "BLOCKED", "UAT-AC100-04": "BLOCKED", "UAT-AC100-05": "BLOCKED",
            "UAT-AC100-08": "BLOCKED", "UAT-AC100-09": "BLOCKED",
        }  # fmt: skip
        assert all(available for available, _, _ in refinery.values())
        assert refinery["UAT-AC100-02"][2] == {("PERMIT", "MISSING")}
        assert refinery["UAT-AC100-04"][2] == {("FITNESS", "MISSING"), ("PERMIT", "MISSING")}
        assert refinery["UAT-AC100-05"][2] == {("INSURANCE", "COPY_MISSING")}
        assert refinery["UAT-AC100-06"][2] == {("POLLUTION_UNDER_CONTROL", "RUNS_OUT_IN_PERIOD")}
        assert refinery["UAT-AC100-07"][2] == {("INSURANCE", "RUNS_OUT_IN_PERIOD")}

        # Operations 2's Part D: of the 250 t crawlers, only UAT-CC250-04 is free, and only with a warning; a
        # registration saying transport wins over UAT-CC250-05's marks (4.3).
        crawlers = _machines_for(demo["hu2"]["requirements"]["expansion"])
        assert {number for number, (available, _, _) in crawlers.items() if not available} == {"UAT-CC250-01", "UAT-CC250-02", "UAT-CC250-03"}
        assert crawlers["UAT-CC250-04"][1:] == ("WARNING", {("THOROUGH_EXAMINATION", "RUNS_OUT_IN_PERIOD")})
        assert crawlers["UAT-CC250-05"][1:] == ("BLOCKED", {("FITNESS", "MISSING"), ("PERMIT", "MISSING")})
        assert crawlers["UAT-CC250-06"][1] == "BLOCKED"

        # Operations 1's Part C (guide 4.7): the second crawler's first trip. Eight of the twelve counterweights travel
        # with the first; of two pieces examined 7 months ago, the hook block (12 months) goes, the sling (6) cannot.
        second = _public_id("resource_assignment", "assignment_public_id", "assignment_reference", demo["hu1"]["allocations"]["crawler_with_warning"])
        kit = {item["piece"]["asset_reference"]: item for item in _ok(client.get(f"/api/resource-assignments/{second}/kit-options", params={"trip_number": 1}, headers=HEADERS["ops1"]))["pieces"]}
        references = demo["machines"]["kit_references"]
        assert kit[references["counterweights"]]["quantity_free"] == 4
        assert kit[references["hook_blocks"][1]]["answer"]["overall_code"] == "ELIGIBLE"
        assert kit[references["slings_20t"][1]]["answer"]["overall_code"] == "BLOCKED"
        assert not kit[references["hook_blocks"][0]]["available"] and not kit[references["slings_20t"][0]]["available"]

        # Guide, Step 9: "not yet recorded" reaches Admin at once, Operations after 7 days, Management after 14. The
        # three machines with nothing recorded were added 15 days ago, 8 days ago and today. Sales and Accounts are on
        # no path at all.
        nothing = {"UAT-CC250-06", "UAT-AC100-08", "UAT-AC100-09"}
        assert _not_yet_recorded("admin1", nothing) == nothing
        assert _not_yet_recorded("ops1", nothing) == {"UAT-CC250-06", "UAT-AC100-08"}
        assert _not_yet_recorded("readonly1", nothing) == {"UAT-CC250-06"}
        for username in ("sales1", "finance1"):
            assert _ok(client.get("/api/eligibility/alerts", headers=HEADERS[username]))["items"] == []

        # Guide 4.5: the refinery and the major port are central-government sites, and so are the metro works; Dahej
        # (not a major port) and the private yard, refinery and terminal are not. The metro's hourly line has no site.
        assert _central_answers(demo["hu1"]["work_order_code"]) == [False, False, True]
        assert _central_answers(demo["hu2"]["work_order_code"]) == [False, False, True]
        assert _central_answers(demo["hu3"]["work_order_code"]) == [True, True, True, None]

        # The Sales tester's offer waits for the customer.
        with SessionLocal() as db:
            status = db.execute(text("SELECT offer_status_code FROM crm_commercial_offer WHERE offer_code = :code"), {"code": demo["hu4_offer_code"]}).scalar_one()
        assert status == "SUBMITTED"
    finally:
        cleanup_manifest(manifest)
    assert check_manifest_status(manifest)["residue_clear"] is True
    after = _snapshot()
    assert {table: (before[table], after.get(table)) for table in before if after.get(table) != before[table]} == {}


@pytest.mark.skipif(
    not (DOCS / "uat-hiring").is_dir(),
    reason="docs/ is not mounted in the backend container; CI runs pytest from the checkout, where it is (or set PBL_DOCS_DIR)",
)
def test_the_report_file_the_fleet_admin_uploads_is_the_one_the_practice_data_expects() -> None:
    """Cleanup finds the uploaded report by the SHA-256 of `second_plum_report()`, so the file handed out must be that
    report exactly - with LF line endings, which .gitattributes pins."""
    assert (DOCS / "uat-hiring" / SECOND_REPORT_FILE).read_bytes() == second_plum_report().encode("utf-8")
