"""Tests for the TE-1 smoke-data harness (backend/tooling/smoke_data).

These tests exercise the harness itself, not a CRM business rule, so they live
separately from the module-per-slice test files. They still run against the
real dockerized PostgreSQL like every other backend test in this repo, and
every test cleans up after itself using the harness's own cleanup path.
"""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app
from tooling.smoke_data.cleanup import CleanupValidationError, cleanup_manifest
from tooling.smoke_data.manifest import (
    ManifestValidationError,
    is_valid_run_id,
    validate_manifest_dict,
)
from tooling.smoke_data.scenarios import run_scenario
from tooling.smoke_data.store import manifest_path_for_run


def _offer_row(offer_public_id: str) -> dict[str, object] | None:
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT offer_status_code FROM crm_commercial_offer WHERE offer_public_id = :id"),
            {"id": offer_public_id},
        ).first()
        return dict(row._mapping) if row else None


def _count(sql: str, params: dict[str, object]) -> int:
    with SessionLocal() as db:
        return db.execute(text(sql), params).scalar() or 0


def _account_exists(account_public_id: str) -> bool:
    return (
        _count(
            "SELECT COUNT(*) FROM business_party WHERE business_party_public_id = :id",
            {"id": account_public_id},
        )
        > 0
    )


def test_seed_returns_valid_manifest_with_unique_run_ids() -> None:
    manifest_a = run_scenario("accepted-offer-no-work-order")
    manifest_b = run_scenario("accepted-offer-no-work-order")
    try:
        validate_manifest_dict(manifest_a)
        validate_manifest_dict(manifest_b)
        assert manifest_a["run_id"] != manifest_b["run_id"]
        assert is_valid_run_id(manifest_a["run_id"])
        assert manifest_a["manifest_version"] == 1
        assert "handoff_target" in manifest_a["records"]
    finally:
        cleanup_manifest(manifest_a)
        cleanup_manifest(manifest_b)


def test_seeded_records_are_visibly_tagged() -> None:
    manifest = run_scenario("accepted-offer-no-work-order")
    try:
        account_name = manifest["records"]["handoff_target"]["account"]["account_name"]
        assert manifest["run_id"] in account_name
        assert account_name.startswith("TE1-SMOKE-")
    finally:
        cleanup_manifest(manifest)


def test_accepted_scenario_uses_customer_response_action_not_a_status_bypass() -> None:
    manifest = run_scenario("accepted-offer-no-work-order")
    try:
        offer_public_id = manifest["records"]["handoff_target"]["commercial_offer"]["public_id"]
        row = _offer_row(offer_public_id)
        assert row is not None
        assert row["offer_status_code"] == "ACCEPTED"

        response_count = _count(
            """
            SELECT COUNT(*)
            FROM commercial_offer_customer_response r
            INNER JOIN crm_commercial_offer o ON o.id = r.commercial_offer_id
            WHERE o.offer_public_id = :id AND r.response_outcome = 'ACCEPTED_AWARDED'
            """,
            {"id": offer_public_id},
        )
        assert response_count == 1, "ACCEPTED must be reached via the Slice 6L Customer Response action"
    finally:
        cleanup_manifest(manifest)


def test_accepted_scenario_does_not_auto_create_a_work_order() -> None:
    manifest = run_scenario("accepted-offer-no-work-order")
    try:
        offer_public_id = manifest["records"]["handoff_target"]["commercial_offer"]["public_id"]
        assert manifest["records"]["handoff_target"]["work_orders"] == []
        work_order_count = _count(
            """
            SELECT COUNT(*)
            FROM crm_work_order wo
            INNER JOIN crm_commercial_offer o ON o.id = wo.commercial_offer_id
            WHERE o.offer_public_id = :id
            """,
            {"id": offer_public_id},
        )
        assert work_order_count == 0
    finally:
        cleanup_manifest(manifest)


def test_accepted_with_work_order_uses_explicit_frozen_handoff_and_preserves_line_traceability() -> None:
    manifest = run_scenario("accepted-offer-with-work-order")
    try:
        record = manifest["records"]["accepted_with_work_order"]
        assert len(record["work_orders"]) == 1
        offer_line_public_id = record["commercial_offer"]["line_public_id"]
        work_order_public_id = record["work_orders"][0]["public_id"]

        with SessionLocal() as db:
            row = db.execute(
                text(
                    """
                    SELECT ol.line_public_id AS source_line_public_id
                    FROM crm_work_order_line wol
                    INNER JOIN crm_work_order wo ON wo.id = wol.work_order_id
                    INNER JOIN crm_commercial_offer_line ol ON ol.id = wol.commercial_offer_line_id
                    WHERE wo.work_order_public_id = :wo_id
                    """
                ),
                {"wo_id": work_order_public_id},
            ).first()
        assert row is not None
        assert str(row._mapping["source_line_public_id"]) == offer_line_public_id
    finally:
        cleanup_manifest(manifest)


def test_cleanup_removes_work_order_line_detail_and_billing_terms_before_their_line_and_account_records() -> None:
    """Slice 7C: a line's operational detail carries declared FKs to crm_work_order_line and to the
    Account's address and GSTIN public ids. Slice 7D: its billing terms carry a declared FK to the line.
    Cleanup must delete both first, or the Work Order line delete - and later the Account sub-record
    deletes - fail on those keys."""
    from tooling.smoke_data.builders import (
        add_account_address,
        add_account_gstin,
        add_work_order_line_billing_terms_period,
        create_work_order,
        set_work_order_line_detail,
    )

    manifest = run_scenario("accepted-offer-no-work-order")
    record = manifest["records"]["handoff_target"]
    actor = manifest["actor"]["public_id"]
    account_public_id = record["account"]["public_id"]
    work_order = create_work_order(actor_public_id=actor, offer_public_id=record["commercial_offer"]["public_id"])
    site = add_account_address(
        actor_public_id=actor, account_public_id=account_public_id, address_type_code="SITE",
        address_line1="Plot 7, Harness Yard", city="Pune", state="Maharashtra",
    )
    billing = add_account_address(
        actor_public_id=actor, account_public_id=account_public_id, address_type_code="REGISTERED_OFFICE",
        address_line1="1 Harness House", city="Mumbai", state="Maharashtra",
    )
    # GSTINs are unique across all Accounts, so the PAN part is random rather than a fixed sample.
    token = uuid4().int
    pan_letters = "".join(chr(ord("A") + (token >> (5 * i)) % 26) for i in range(5))
    gstin = add_account_gstin(
        actor_public_id=actor, account_public_id=account_public_id,
        gstin=f"27{pan_letters}{token % 10000:04d}F1Z5", state_code="27", state_name="Maharashtra",
    )
    detail = set_work_order_line_detail(
        actor_public_id=actor,
        work_order_public_id=work_order["public_id"],
        line_public_id=work_order["line_public_ids"][0],
        site_address_public_id=site["public_id"],
        billing_gstin_public_id=gstin["public_id"],
        billing_address_public_id=billing["public_id"],
    )
    assert detail["is_complete"] is True
    terms = add_work_order_line_billing_terms_period(
        actor_public_id=actor,
        work_order_public_id=work_order["public_id"],
        line_public_id=work_order["line_public_ids"][0],
        billing_uom_code="HOUR",
        normal_rate_amount=Decimal("1500.00"),
        customer_idle_treatment_code="AS_WORKING_HOURS",
        minimum_guarantee_code="NONE",
        # Slice 7D Part 2's terms are answered too, so the period is genuinely complete. An hourly line
        # has no night shift at all, so it carries no answer for one.
        mobilisation_charge_code="NONE",
        demobilisation_charge_code="NONE",
        fuel_treatment_code="NONE",
        # Slice 7D Part 4's two terms apply to every basis, hourly included.
        extra_km_allowance_code="NONE",
        crew_code="NONE",
    )
    assert terms["terms_complete"] is True

    counts = cleanup_manifest(manifest)
    assert counts["work_order_line_details"] == 1
    assert counts["work_order_line_billing_terms"] == 1
    assert counts["work_order_lines"] == 1
    assert counts["work_orders"] == 1
    assert _count(
        "SELECT COUNT(*) FROM crm_work_order_line_detail WHERE work_order_line_detail_public_id = :id",
        {"id": detail["detail_public_id"]},
    ) == 0
    assert _count(
        "SELECT COUNT(*) FROM crm_work_order_line_billing_term WHERE work_order_line_billing_term_public_id = :id",
        {"id": terms["term_public_id"]},
    ) == 0
    assert not _account_exists(account_public_id)


def test_cleanup_removes_a_work_orders_contract_period_and_extensions_before_the_work_order() -> None:
    """Slice 7D Part 3: both tables carry a declared FK to crm_work_order itself, so cleanup must
    delete them before it. The scenario leaves the contract dates for a tester to record, which is
    exactly the case this covers: rows added after seeding still belong to the run that owns the
    Work Order."""
    from tooling.smoke_data.builders import (
        add_work_order_contract_extension,
        create_work_order,
        set_work_order_contract_period,
    )

    manifest = run_scenario("accepted-offer-no-work-order")
    record = manifest["records"]["handoff_target"]
    actor = manifest["actor"]["public_id"]
    work_order = create_work_order(actor_public_id=actor, offer_public_id=record["commercial_offer"]["public_id"])
    period = set_work_order_contract_period(
        actor_public_id=actor,
        work_order_public_id=work_order["public_id"],
        contract_start_date="2027-01-01",
        contract_end_basis_code="FIXED_DATE",
        contract_end_date="2027-03-31",
    )
    assert period["is_complete"] is True
    extension = add_work_order_contract_extension(
        actor_public_id=actor,
        work_order_public_id=work_order["public_id"],
        new_end_date="2027-06-30",
        received_date="2027-03-01",
        customer_reference="HARNESS/EXT/1",
    )
    assert extension["contract_end_date"] == "2027-06-30"

    counts = cleanup_manifest(manifest)
    assert counts["work_order_contract_extensions"] == 1
    assert counts["work_order_contract_periods"] == 1
    assert counts["work_orders"] == 1
    assert _count(
        "SELECT COUNT(*) FROM crm_work_order_contract_period WHERE work_order_contract_period_public_id = :id",
        {"id": period["period_public_id"]},
    ) == 0
    assert _count(
        "SELECT COUNT(*) FROM crm_work_order_contract_extension "
        "WHERE work_order_contract_extension_public_id = :id",
        {"id": extension["extension_public_id"]},
    ) == 0


def test_the_part_4_scenario_seeds_its_screen_check_and_cleanup_removes_holidays_added_afterwards() -> None:
    """Slice 7D Part 4: the scenario leaves the holiday list for the tester, so rows added after seeding
    are exactly the case cleanup must handle. Each date references its list and the list the Work Order,
    so both go before it - found by Work Order ownership, like Part 3's rows."""
    from app.modules.work_orders import service as work_orders_service
    from tooling.smoke_data.builders import set_work_order_holidays

    manifest = run_scenario("work-order-billing-terms-part-4")
    demo = manifest["records"]["billing_terms_part_4_target"]["billing_terms_part_4_demo"]
    work_order_public_id = demo["work_order_public_id"]

    with SessionLocal() as db:
        entries = work_orders_service.list_work_order_billing_terms(db, UUID(work_order_public_id))
    missing = {str(entry.work_order_line_public_id): entry.line_missing_items for entry in entries}
    # Line 1 reports exactly the two Part 4 terms missing; line 2 is complete; line 3 has none.
    assert missing[demo["line_without_part_4_terms"]] == ["EXTRA_KILOMETRES", "CREW"]
    assert missing[demo["line_with_part_4_terms"]] == []
    assert missing[demo["line_public_ids"][2]] == ["NO_TERMS"]

    # HOL-1: a holiday added and a calendar holiday made a working day, both rows of the same table.
    holidays = set_work_order_holidays(
        actor_public_id=manifest["actor"]["public_id"],
        work_order_public_id=work_order_public_id,
        holidays_answer_code="CALENDAR_CHANGED",
        holidays=[("2027-01-26", "NATIONAL", "Republic Day"), ("2027-03-22", "FESTIVAL", None)],
        working_days=[("2027-08-15", "OVERTIME_RATE", "Plant runs")],
    )
    assert (holidays["holiday_count"], holidays["working_day_count"]) == (2, 1)
    assert holidays["is_complete"] is True

    counts = cleanup_manifest(manifest)
    assert counts["work_order_holidays"] == 3
    assert counts["work_order_holiday_lists"] == 1
    assert counts["work_order_contract_periods"] == 1
    assert counts["work_orders"] == 1
    assert _count(
        "SELECT COUNT(*) FROM crm_work_order_holiday_list WHERE work_order_holiday_list_public_id = :id",
        {"id": holidays["holiday_list_public_id"]},
    ) == 0


def test_the_contract_period_scenario_seeds_the_part_5_screen_check_and_cleanup_removes_it() -> None:
    """Slice 7D Part 5 extended the Part 3 scenario: its monthly line records two shifts each at its own rate, then
    three at one rate from 1 July 2027, and its crew's food, accommodation and travel - every period complete. The
    Part 4 scenario's crew line answers the upkeep too, so it still reads complete (the test above)."""
    from app.modules.work_orders import service as work_orders_service

    manifest = run_scenario("work-order-contract-period")
    try:
        demo = manifest["records"]["contract_period_target"]["contract_period_demo"]
        with SessionLocal() as db:
            entries = work_orders_service.list_work_order_billing_terms(db, UUID(demo["work_order_public_id"]))
        line = next(entry for entry in entries if str(entry.work_order_line_public_id) == demo["part_5_line_public_id"])
        assert line.terms_complete is True, line.line_missing_items
        first, later = line.periods
        assert (first.shift_pattern_code, first.shift_rate_code, first.shift_2_rate_percent) == ("TWO_SHIFTS", "PER_SHIFT", Decimal("90.00"))
        assert (later.shift_pattern_code, later.shift_rate_code, later.overtime_counted_per_code) == ("THREE_SHIFTS", "SAME_FOR_ALL_SHIFTS", "PER_DAY")
        assert first.overtime_counted_per_code == "PER_SHIFT"
        assert first.upkeep_job_travel_operator_unit_code == "PER_PERSON_PER_TRIP"
        assert first.upkeep_accommodation_helper_recovery_code == "BILLED_SEPARATELY"
        assert later.upkeep_job_travel_operator_amount == Decimal("2500.00")
    finally:
        counts = cleanup_manifest(manifest)
    assert counts["work_order_line_billing_terms"] == 3
    assert counts["work_orders"] == 1


def test_the_resource_requirement_scenario_seeds_its_screen_check_and_cleanup_removes_what_was_added() -> None:
    """WRR-001: the scenario seeds two requirements on different lines. A requirement added afterwards -
    as the screen check and the Playwright test do - hangs off an owned Work Order line, so cleanup must
    find it through the line, delete capabilities, items and requirements before the lines, and delete
    every requirement's audit rows, which are keyed by the requirement's own public id."""
    from tooling.smoke_data.builders import create_resource_requirement
    from tooling.smoke_data.status import check_manifest_status

    manifest = run_scenario("work-order-resource-requirements")
    try:
        demo = manifest["records"]["resource_requirements_target"]["resource_requirement_demo"]
        assert demo["crane_requirement"]["warnings"] == []
        assert demo["manlift_requirement"]["warnings"] == ["SITE_NOT_RECORDED"]

        added = create_resource_requirement(
            actor_public_id=manifest["actor"]["public_id"],
            work_order_public_id=demo["work_order_public_id"],
            line_public_id=demo["forklift_line_public_id"],
            units_required=1,
            required_from="2026-12-01",
            equipment_class_code="FORKLIFT",
            capabilities=[("RATED_CAPACITY", Decimal("5"))],
        )
        requirement_ids = [
            demo["crane_requirement"]["public_id"],
            demo["manlift_requirement"]["public_id"],
            added["public_id"],
        ]
        events_sql = (
            "SELECT COUNT(*) FROM business_event WHERE record_type = 'resource_requirement' "
            "AND record_public_id = ANY(:ids)"
        )
        assert _count(events_sql, {"ids": requirement_ids}) == 3
        assert check_manifest_status(manifest)["residue"]["business_events"] > 0

        counts = cleanup_manifest(manifest)
        assert counts["resource_requirements"] == 3
        assert counts["resource_requirement_items"] == 3
        assert counts["resource_requirement_item_capabilities"] == 3
        assert counts["work_orders"] == 1
        assert _count(
            "SELECT COUNT(*) FROM resource_requirement WHERE requirement_public_id = ANY(:ids)",
            {"ids": requirement_ids},
        ) == 0
        assert _count(events_sql, {"ids": requirement_ids}) == 0
        # The structure is reference data and is never cleaned up.
        assert _count("SELECT COUNT(*) FROM equipment_class WHERE class_code = 'CRANE'", {}) == 1
    finally:
        cleanup_manifest(manifest)


def test_cleanup_discovers_a_work_order_created_after_seeding_and_not_recorded_in_the_manifest() -> None:
    """Regression test for a real bug found while running the Playwright suite: a test can
    trigger the live Work Order handoff through the UI for an offer seeded with
    work_orders=[] (e.g. 'accepted-offer-no-work-order'). That Work Order's public_id is not
    in the manifest, so cleanup must discover it by offer ownership rather than only by the
    manifest's own work_orders list, or the later offer_lines DELETE fails on the
    fk_crm_work_order_line_offer_line FK constraint."""
    from tooling.smoke_data.builders import create_work_order

    manifest = run_scenario("accepted-offer-no-work-order")
    record = manifest["records"]["handoff_target"]
    assert record["work_orders"] == []

    work_order = create_work_order(
        actor_public_id=manifest["actor"]["public_id"],
        offer_public_id=record["commercial_offer"]["public_id"],
    )

    counts = cleanup_manifest(manifest)
    assert counts["work_orders"] == 1
    assert counts["work_order_lines"] == 1
    assert counts["commercial_offers"] == 1

    with SessionLocal() as db:
        remaining = db.execute(
            text("SELECT COUNT(*) FROM crm_work_order WHERE work_order_public_id = :id"),
            {"id": work_order["public_id"]},
        ).scalar()
    assert remaining == 0


def test_rejected_scenario_is_non_actionable() -> None:
    manifest = run_scenario("rejected-offer")
    try:
        offer_public_id = manifest["records"]["rejected_offer"]["commercial_offer"]["public_id"]
        row = _offer_row(offer_public_id)
        assert row is not None
        assert row["offer_status_code"] == "REJECTED"
        assert manifest["records"]["rejected_offer"]["work_orders"] == []
    finally:
        cleanup_manifest(manifest)


def test_blocked_handoff_scenario_reports_a_genuine_blocker() -> None:
    manifest = run_scenario("blocked-handoff")
    try:
        record = manifest["records"]["blocked_handoff"]
        assert record["blocked_reason"], "blocked-handoff must record a non-empty genuine blocker reason"
        offer_public_id = record["commercial_offer"]["public_id"]
        row = _offer_row(offer_public_id)
        assert row is not None
        assert row["offer_status_code"] == "SUBMITTED"
        work_order_count = _count(
            """
            SELECT COUNT(*)
            FROM crm_work_order wo
            INNER JOIN crm_commercial_offer o ON o.id = wo.commercial_offer_id
            WHERE o.offer_public_id = :id
            """,
            {"id": offer_public_id},
        )
        assert work_order_count == 0
    finally:
        cleanup_manifest(manifest)


def test_two_seed_runs_remain_isolated_and_cleanup_only_removes_the_selected_run() -> None:
    manifest_a = run_scenario("rejected-offer")
    manifest_b = run_scenario("rejected-offer")
    account_a = manifest_a["records"]["rejected_offer"]["account"]["public_id"]
    account_b = manifest_b["records"]["rejected_offer"]["account"]["public_id"]

    assert manifest_a["run_id"] != manifest_b["run_id"]
    assert account_a != account_b

    cleanup_manifest(manifest_a)
    try:
        assert _account_exists(account_a) is False
        assert _account_exists(account_b) is True, "cleaning up run A must not touch run B's records"
    finally:
        cleanup_manifest(manifest_b)


def test_cleanup_is_idempotent() -> None:
    manifest = run_scenario("rejected-offer")
    first_counts = cleanup_manifest(manifest)
    assert sum(first_counts.values()) > 0

    second_counts = cleanup_manifest(manifest)
    assert all(count == 0 for count in second_counts.values())


def test_cleanup_rejects_malformed_manifest_and_run_id() -> None:
    with pytest.raises(ManifestValidationError):
        validate_manifest_dict({"not": "a manifest"})

    with pytest.raises(ManifestValidationError):
        cleanup_manifest({"manifest_version": 1, "run_id": "te1-deadbeef", "scenario": "x", "created_at": "x", "records": {}})

    with pytest.raises(ValueError):
        manifest_path_for_run("'; DROP TABLE business_party; --")

    with pytest.raises(ValueError):
        manifest_path_for_run("")


def test_cleanup_after_partial_setup_is_safe() -> None:
    """Simulates a seed run that failed after creating only an Account + Opportunity
    (no offer). Cleanup must still remove exactly those records without error."""
    from tooling.smoke_data.builders import create_account_linked_opportunity
    from tooling.smoke_data.manifest import Manifest, new_run_id, utc_now_iso

    run_id = new_run_id()
    with SessionLocal() as db:
        from tooling.smoke_data.actors import resolve_actor

        actor = resolve_actor(db)
    chain = create_account_linked_opportunity(run_id=run_id, actor_public_id=actor["public_id"], suffix="Partial")

    manifest = Manifest(
        manifest_version=1,
        run_id=run_id,
        scenario="partial-setup-test",
        created_at=utc_now_iso(),
        actor=actor,
        records={"partial": {"account": chain["account"], "opportunity": chain["opportunity"]}},
        urls={},
    ).to_dict()

    counts = cleanup_manifest(manifest)
    assert counts["accounts"] == 1
    assert counts["opportunities"] == 1
    assert counts["commercial_offers"] == 0
    assert _account_exists(chain["account"]["public_id"]) is False


def test_cleanup_rejects_unrecognizable_manifest_records() -> None:
    manifest = {
        "manifest_version": 1,
        "run_id": "te1-00000000",
        "scenario": "empty",
        "created_at": "2026-01-01T00:00:00+00:00",
        "records": {"nothing": {}},
    }
    with pytest.raises(CleanupValidationError):
        cleanup_manifest(manifest)


def test_supplementary_offer_draft_scenario_has_no_copied_data() -> None:
    manifest = run_scenario("supplementary-offer-draft")
    try:
        record = manifest["records"]["supplementary_offer_draft"]
        base_offer_public_id = record["commercial_offer"]["public_id"]
        related_offer = record["related_offers"][0]
        assert related_offer["offer_purpose"] == "SUPPLEMENTARY"
        assert related_offer["base_offer_public_id"] == base_offer_public_id
        assert related_offer["related_work_order_public_id"] is None

        related_row = _offer_row(related_offer["public_id"])
        assert related_row is not None
        assert related_row["offer_status_code"] == "DRAFT"

        base_row = _offer_row(base_offer_public_id)
        assert base_row is not None
        assert base_row["offer_status_code"] == "ACCEPTED"

        line_count = _count(
            "SELECT COUNT(*) FROM crm_commercial_offer_line l INNER JOIN crm_commercial_offer o ON o.id = l.commercial_offer_id WHERE o.offer_public_id = :id",
            {"id": related_offer["public_id"]},
        )
        assert line_count == 0

        event_count = _count(
            "SELECT COUNT(*) FROM business_event WHERE record_public_id = :id AND event_name = 'CommercialOfferRelatedOfferCreated'",
            {"id": related_offer["public_id"]},
        )
        assert event_count == 1
    finally:
        cleanup_manifest(manifest)


def test_change_quotation_draft_scenario_links_existing_work_order() -> None:
    manifest = run_scenario("change-quotation-draft")
    try:
        record = manifest["records"]["change_quotation_draft"]
        work_order_public_id = record["work_orders"][0]["public_id"]
        related_offer = record["related_offers"][0]
        assert related_offer["offer_purpose"] == "CHANGE_QUOTATION"
        assert related_offer["related_work_order_public_id"] == work_order_public_id

        with SessionLocal() as db:
            row = db.execute(
                text(
                    """
                    SELECT wo.work_order_status_code
                    FROM crm_commercial_offer co
                    INNER JOIN crm_work_order wo ON wo.id = co.related_work_order_id
                    WHERE co.offer_public_id = :id
                    """
                ),
                {"id": related_offer["public_id"]},
            ).first()
        assert row is not None, "related_work_order_id must resolve to the seeded Work Order"
    finally:
        cleanup_manifest(manifest)


def test_supplementary_offer_lifecycle_scenario_is_independent_of_base_offer() -> None:
    manifest = run_scenario("supplementary-offer-lifecycle")
    try:
        record = manifest["records"]["supplementary_offer_lifecycle"]
        base_offer_public_id = record["commercial_offer"]["public_id"]
        related_offer = record["related_offers"][0]

        related_row = _offer_row(related_offer["public_id"])
        assert related_row is not None
        assert related_row["offer_status_code"] == "ACCEPTED"

        base_row = _offer_row(base_offer_public_id)
        assert base_row is not None
        assert base_row["offer_status_code"] == "ACCEPTED"

        # Related offer's own acceptance must not have created a Work Order automatically.
        work_order_count = _count(
            """
            SELECT COUNT(*)
            FROM crm_work_order wo
            INNER JOIN crm_commercial_offer o ON o.id = wo.commercial_offer_id
            WHERE o.offer_public_id = :id
            """,
            {"id": related_offer["public_id"]},
        )
        assert work_order_count == 0
    finally:
        cleanup_manifest(manifest)


def test_related_offer_regression_bundle_shows_three_distinct_offer_purposes() -> None:
    manifest = run_scenario("related-offer-regression-bundle")
    try:
        record = manifest["records"]["multi_series_target"]
        base_offer_public_id = record["commercial_offer"]["public_id"]
        purposes = {related["offer_purpose"] for related in record["related_offers"]}
        assert purposes == {"SUPPLEMENTARY", "CHANGE_QUOTATION"}
        for related in record["related_offers"]:
            assert related["base_offer_public_id"] == base_offer_public_id

        supplementary_target = manifest["records"]["supplementary_offer_create_target"]
        assert supplementary_target["commercial_offer"]["public_id"] != base_offer_public_id

        change_quotation_target = manifest["records"]["change_quotation_create_target"]
        assert change_quotation_target["commercial_offer"]["public_id"] != base_offer_public_id
        assert change_quotation_target["work_orders"], "change_quotation_create_target must have an existing linked Work Order"
    finally:
        cleanup_manifest(manifest)


def test_cleanup_removes_related_offer_and_does_not_touch_unrelated_base_offer() -> None:
    """Two independent supplementary-offer-draft runs must remain isolated; cleaning one
    must not remove the other's Base Offer, Supplementary Offer or Account."""
    manifest_a = run_scenario("supplementary-offer-draft")
    manifest_b = run_scenario("supplementary-offer-draft")
    try:
        related_a = manifest_a["records"]["supplementary_offer_draft"]["related_offers"][0]["public_id"]
        related_b = manifest_b["records"]["supplementary_offer_draft"]["related_offers"][0]["public_id"]

        counts = cleanup_manifest(manifest_a)
        assert counts["commercial_offers"] == 2  # base + related offer for run A only

        assert _offer_row(related_a) is None
        assert _offer_row(related_b) is not None
    finally:
        cleanup_manifest(manifest_b)


def test_cleanup_discovers_a_related_offer_created_after_seeding_and_not_recorded_in_the_manifest() -> None:
    """Mirrors test_cleanup_discovers_a_work_order_created_after_seeding_and_not_recorded_in_the_manifest:
    a Playwright test can create a Supplementary Offer live through the UI against a seeded
    accepted Base Offer. Cleanup must discover it by base_offer_id ownership."""
    from tooling.smoke_data.builders import create_related_offer

    manifest = run_scenario("accepted-offer-no-work-order")
    record = manifest["records"]["handoff_target"]

    related_offer = create_related_offer(
        run_id=manifest["run_id"],
        actor_public_id=manifest["actor"]["public_id"],
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="SUPPLEMENTARY",
        related_work_order_public_id=None,
        customer_request_summary="Created after seeding, not in the manifest.",
    )

    counts = cleanup_manifest(manifest)
    assert counts["commercial_offers"] == 2  # base offer + the live-created related offer
    assert _offer_row(related_offer["public_id"]) is None


def test_cleanup_nulls_related_work_order_link_before_deleting_work_order() -> None:
    """If a Change Quotation links to a Work Order that this run also owns, cleanup must
    still succeed: the cross-table FK cycle (crm_work_order.commercial_offer_id ->
    crm_commercial_offer.id, and crm_commercial_offer.related_work_order_id ->
    crm_work_order.id) would otherwise block deleting the Work Order."""
    manifest = run_scenario("change-quotation-draft")
    record = manifest["records"]["change_quotation_draft"]
    work_order_public_id = record["work_orders"][0]["public_id"]

    counts = cleanup_manifest(manifest)
    assert counts["work_orders"] == 1
    assert counts["commercial_offers"] == 2  # base offer + change quotation

    with SessionLocal() as db:
        remaining = db.execute(
            text("SELECT COUNT(*) FROM crm_work_order WHERE work_order_public_id = :id"),
            {"id": work_order_public_id},
        ).scalar()
    assert remaining == 0


def _amendment_row(amendment_public_id: str) -> dict[str, object] | None:
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT amendment_status_code FROM crm_work_order_amendment WHERE amendment_public_id = :id"),
            {"id": amendment_public_id},
        ).first()
        return dict(row._mapping) if row else None


def test_work_order_amendment_received_scenario_leaves_work_order_unchanged() -> None:
    manifest = run_scenario("work-order-amendment-received")
    try:
        record = manifest["records"]["work_order_amendment_received"]
        work_order_public_id = record["work_orders"][0]["public_id"]
        amendment = record["amendments"][0]
        assert amendment["amendment_type_code"] == "ADMINISTRATIVE"
        assert amendment["amendment_status_code"] == "RECEIVED"

        amendment_row = _amendment_row(amendment["public_id"])
        assert amendment_row is not None
        assert amendment_row["amendment_status_code"] == "RECEIVED"

        with SessionLocal() as db:
            wo_status = db.execute(
                text("SELECT work_order_status_code FROM crm_work_order WHERE work_order_public_id = :id"),
                {"id": work_order_public_id},
            ).scalar()
        assert wo_status == "HANDOFF_CREATED"

        event_count = _count(
            "SELECT COUNT(*) FROM business_event WHERE record_type = 'work_order' AND record_public_id = :wo "
            "AND event_name = 'WorkOrderAmendmentRecorded'",
            {"wo": work_order_public_id},
        )
        assert event_count == 1
    finally:
        cleanup_manifest(manifest)


def test_commercial_amendment_with_change_quotation_scenario_reaches_validated_without_mutating_work_order() -> None:
    manifest = run_scenario("commercial-amendment-with-change-quotation")
    try:
        record = manifest["records"]["commercial_amendment_with_change_quotation"]
        work_order_public_id = record["work_orders"][0]["public_id"]
        change_quotation = record["related_offers"][0]
        amendment = record["amendments"][0]

        assert change_quotation["offer_purpose"] == "CHANGE_QUOTATION"
        change_quotation_row = _offer_row(change_quotation["public_id"])
        assert change_quotation_row is not None
        assert change_quotation_row["offer_status_code"] == "ACCEPTED"

        assert amendment["amendment_type_code"] == "COMMERCIAL"
        amendment_row = _amendment_row(amendment["public_id"])
        assert amendment_row is not None
        assert amendment_row["amendment_status_code"] == "VALIDATED"

        line_count = _count(
            "SELECT COUNT(*) FROM crm_work_order_amendment_line l INNER JOIN crm_work_order_amendment a ON "
            "a.id = l.amendment_id WHERE a.amendment_public_id = :id",
            {"id": amendment["public_id"]},
        )
        assert line_count == 1

        # The Work Order and its lines must remain exactly as originally handed off.
        with SessionLocal() as db:
            wo_line_count = db.execute(
                text(
                    "SELECT COUNT(*) FROM crm_work_order_line wol INNER JOIN crm_work_order wo ON wo.id = "
                    "wol.work_order_id WHERE wo.work_order_public_id = :id"
                ),
                {"id": work_order_public_id},
            ).scalar()
        assert wo_line_count == 1
    finally:
        cleanup_manifest(manifest)


def test_work_order_amendment_regression_bundle_has_five_independent_targets() -> None:
    manifest = run_scenario("work-order-amendment-regression-bundle")
    try:
        records = manifest["records"]
        expected_keys = {
            "administrative_amendment_create_target",
            "commercial_amendment_with_basis",
            "line_delta_target",
            "amendment_read_only_view",
            "terminal_amendment_display",
        }
        assert expected_keys.issubset(records.keys())

        work_order_public_ids = {
            records[key]["work_orders"][0]["public_id"] for key in expected_keys if records[key].get("work_orders")
        }
        assert len(work_order_public_ids) == len(expected_keys), "each target must use its own Work Order"

        assert records["administrative_amendment_create_target"].get("amendments", []) == []
        assert records["commercial_amendment_with_basis"]["amendments"][0]["amendment_status_code"] == "VALIDATED"
        assert records["line_delta_target"]["amendments"][0]["amendment_status_code"] == "RECEIVED"
        assert records["amendment_read_only_view"]["amendments"][0]["amendment_status_code"] == "RECEIVED"
        assert records["terminal_amendment_display"]["amendments"][0]["amendment_status_code"] == "REJECTED"
    finally:
        cleanup_manifest(manifest)


def test_cleanup_removes_amendment_and_does_not_touch_unrelated_work_order() -> None:
    """Two independent work-order-amendment-received runs must remain isolated; cleaning
    one must not remove the other's Work Order, amendment or Account."""
    manifest_a = run_scenario("work-order-amendment-received")
    manifest_b = run_scenario("work-order-amendment-received")
    try:
        amendment_a = manifest_a["records"]["work_order_amendment_received"]["amendments"][0]["public_id"]
        amendment_b = manifest_b["records"]["work_order_amendment_received"]["amendments"][0]["public_id"]

        counts = cleanup_manifest(manifest_a)
        assert counts["work_order_amendments"] == 1

        assert _amendment_row(amendment_a) is None
        assert _amendment_row(amendment_b) is not None
    finally:
        cleanup_manifest(manifest_b)


def test_cleanup_discovers_an_amendment_created_after_seeding_and_not_recorded_in_the_manifest() -> None:
    """Mirrors the Work Order / related-offer live-creation-discovery tests: a Playwright
    test can record a Work Order Amendment live through the UI against a seeded Work
    Order. Cleanup must discover it and its lines by Work Order ownership, not only from
    the seed-time manifest's own "amendments" list."""
    from tooling.smoke_data.builders import add_amendment_line, create_work_order_amendment

    manifest = run_scenario("accepted-offer-with-work-order")
    record = manifest["records"]["accepted_with_work_order"]
    work_order_public_id = record["work_orders"][0]["public_id"]

    amendment = create_work_order_amendment(
        run_id=manifest["run_id"],
        actor_public_id=manifest["actor"]["public_id"],
        work_order_public_id=work_order_public_id,
        amendment_type_code="COMMERCIAL",
        commercial_change_summary="Created after seeding, not in the manifest.",
    )
    add_amendment_line(
        actor_public_id=manifest["actor"]["public_id"],
        work_order_public_id=work_order_public_id,
        amendment_public_id=amendment["public_id"],
    )

    counts = cleanup_manifest(manifest)
    assert counts["work_order_amendments"] == 1
    assert counts["work_order_amendment_lines"] == 1
    assert _amendment_row(amendment["public_id"]) is None


def test_no_public_api_route_exposes_the_smoke_data_harness() -> None:
    for route in app.routes:
        path = getattr(route, "path", "")
        assert "smoke" not in path.lower()
        assert "seed" not in path.lower()
        assert "vendor-demo" not in path.lower()


# --- Slice 6P vendor-demo-bundle -------------------------------------------------------------
#
# These tests exercise the vendor-demo-bundle scenario added for Slice 6P. They follow the same
# real-service-layer, no-status-bypass pattern as every other scenario above; the only new
# concept is the additive, backward-compatible "demo_meta" manifest field and the harness's
# first-ever Lead builders.


def test_vendor_demo_bundle_produces_a_valid_manifest_with_all_tracks_present() -> None:
    manifest = run_scenario("vendor-demo-bundle")
    try:
        validate_manifest_dict(manifest)
        assert manifest["scenario"] == "vendor-demo-bundle"

        tracks_present = {
            record["demo_meta"]["track"] for record in manifest["records"].values() if "demo_meta" in record
        }
        assert tracks_present == {"A", "B", "C", "D", "E", "F"}, "vendor-demo-bundle must cover tracks A-F"
    finally:
        cleanup_manifest(manifest)


def test_vendor_demo_bundle_records_are_fictional_and_demo_meta_distinguishes_interactive_from_fallback() -> None:
    manifest = run_scenario("vendor-demo-bundle")
    try:
        records = manifest["records"]

        for key, record in records.items():
            demo_meta = record.get("demo_meta")
            assert demo_meta is not None, f"{key} is missing demo_meta"
            assert demo_meta["fictional_customer"], f"{key} demo_meta must name the fictional customer story"
            assert isinstance(demo_meta["interactive"], bool)

        # At least one interactive record per mutation-bearing track, and its fallback must
        # point back to it by key.
        assert records["lead_interactive"]["demo_meta"]["interactive"] is True
        assert records["lead_fallback_converted"]["demo_meta"]["fallback_of"] == "lead_interactive"
        assert records["offer_ready_to_submit"]["demo_meta"]["interactive"] is True
        assert records["offer_fallback_submitted"]["demo_meta"]["fallback_of"] == "offer_ready_to_submit"
        assert records["offer_accepted_no_wo"]["demo_meta"]["interactive"] is True
        assert records["offer_accepted_with_wo"]["demo_meta"]["fallback_of"] == "offer_accepted_no_wo"
        assert records["amendment_commercial_interactive"]["demo_meta"]["interactive"] is True
        assert (
            records["amendment_commercial_fallback_validated"]["demo_meta"]["fallback_of"]
            == "amendment_commercial_interactive"
        )

        # Every account/lead name must carry the harness's own visible tag - never a value that
        # could be mistaken for a real customer/company record.
        lead_company = records["lead_interactive"]["lead"]["company_name"]
        assert lead_company.startswith("TE1-SMOKE-")
        account_name = records["offer_ready_to_submit"]["account"]["account_name"]
        assert account_name.startswith("TE1-SMOKE-")
    finally:
        cleanup_manifest(manifest)


def test_vendor_demo_bundle_urls_are_well_formed_and_expected_statuses_match_created_data() -> None:
    manifest = run_scenario("vendor-demo-bundle")
    try:
        assert manifest["urls"], "vendor-demo-bundle must produce record URLs"
        for label, url in manifest["urls"].items():
            assert url.startswith("http://") or url.startswith("https://"), f"malformed URL for {label}: {url}"
            assert "/None" not in url, f"URL for {label} embeds a missing id: {url}"

        records = manifest["records"]
        assert records["offer_ready_to_submit"]["commercial_offer_status"] == "DRAFT"
        assert records["offer_fallback_submitted"]["commercial_offer_status"] == "SUBMITTED"
        assert records["offer_accepted_no_wo"]["commercial_offer_status"] == "ACCEPTED"
        assert records["offer_rejected"]["commercial_offer_status"] == "REJECTED"

        offer_ready_row = _offer_row(records["offer_ready_to_submit"]["commercial_offer"]["public_id"])
        assert offer_ready_row is not None
        assert offer_ready_row["offer_status_code"] == "DRAFT"
    finally:
        cleanup_manifest(manifest)


def test_vendor_demo_bundle_blocker_record_has_no_active_line_and_is_genuinely_not_ready() -> None:
    """The Track B blocker must be a real backend condition (zero active lines), never a
    scripted/fake UI-only message."""
    manifest = run_scenario("vendor-demo-bundle")
    try:
        record = manifest["records"]["offer_blocker_no_active_line"]
        offer_public_id = record["commercial_offer"]["public_id"]

        line_count = _count(
            "SELECT COUNT(*) FROM crm_commercial_offer_line l INNER JOIN crm_commercial_offer o "
            "ON o.id = l.commercial_offer_id WHERE o.offer_public_id = :id",
            {"id": offer_public_id},
        )
        assert line_count == 0

        from app.modules.commercial_offers.service import get_commercial_offer_submission_readiness

        with SessionLocal() as db:
            readiness = get_commercial_offer_submission_readiness(
                db, public_id=UUID(offer_public_id), recommendation_basis=None
            )
        assert readiness.readiness_status != "READY"
    finally:
        cleanup_manifest(manifest)


def test_vendor_demo_bundle_acceptance_never_auto_creates_a_work_order() -> None:
    manifest = run_scenario("vendor-demo-bundle")
    try:
        record = manifest["records"]["offer_accepted_no_wo"]
        assert record["work_orders"] == []
        work_order_count = _count(
            "SELECT COUNT(*) FROM crm_work_order wo INNER JOIN crm_commercial_offer o ON o.id = wo.commercial_offer_id "
            "WHERE o.offer_public_id = :id",
            {"id": record["commercial_offer"]["public_id"]},
        )
        assert work_order_count == 0
    finally:
        cleanup_manifest(manifest)


def test_vendor_demo_bundle_amendment_validation_never_alters_work_order_values() -> None:
    """Drives the interactive Track F amendment (left at UNDER_REVIEW by the scenario) the rest
    of the way to VALIDATED, then proves the Work Order and its lines are byte-for-byte
    unchanged - 'Validated' must never mean 'applied'."""
    from tooling.smoke_data.builders import decide_amendment

    manifest = run_scenario("vendor-demo-bundle")
    try:
        record = manifest["records"]["amendment_commercial_interactive"]
        work_order_public_id = record["work_orders"][0]["public_id"]
        amendment_public_id = record["amendments"][0]["public_id"]
        assert record["amendments"][0]["amendment_status_code"] == "UNDER_REVIEW"

        with SessionLocal() as db:
            before = db.execute(
                text(
                    "SELECT scope_description, quantity, rate_amount FROM crm_work_order_line wol "
                    "INNER JOIN crm_work_order wo ON wo.id = wol.work_order_id WHERE wo.work_order_public_id = :id"
                ),
                {"id": work_order_public_id},
            ).fetchall()

        decide_amendment(
            actor_public_id=manifest["actor"]["public_id"],
            work_order_public_id=work_order_public_id,
            amendment_public_id=amendment_public_id,
            target_status_code="VALIDATED",
        )

        assert _amendment_row(amendment_public_id)["amendment_status_code"] == "VALIDATED"

        with SessionLocal() as db:
            after = db.execute(
                text(
                    "SELECT scope_description, quantity, rate_amount FROM crm_work_order_line wol "
                    "INNER JOIN crm_work_order wo ON wo.id = wol.work_order_id WHERE wo.work_order_public_id = :id"
                ),
                {"id": work_order_public_id},
            ).fetchall()

        assert [dict(row._mapping) for row in before] == [dict(row._mapping) for row in after]
    finally:
        cleanup_manifest(manifest)


def test_vendor_demo_bundle_cleanup_discovers_a_lead_converted_live_and_not_in_the_manifest() -> None:
    """Regression test for a real bug found during the Slice 6P manual rehearsal: the
    interactive Track A Lead record ('lead_interactive') is seeded unconverted, exactly so a
    presenter can qualify and convert it live. That live conversion creates a new Opportunity
    (and Account) the seed-time manifest never knew about. Cleanup must discover the Opportunity
    by its source_lead_id ownership (and the Account it links to) before deleting the Lead, or
    the DELETE violates fk_crm_opportunity_source_lead."""
    from tooling.smoke_data.builders import convert_lead_to_account_opportunity, qualify_lead

    manifest = run_scenario("vendor-demo-bundle")
    record = manifest["records"]["lead_interactive"]
    assert "account" not in record and "opportunity" not in record
    lead_public_id = record["lead"]["public_id"]

    qualify_lead(actor_public_id=manifest["actor"]["public_id"], lead_public_id=lead_public_id)
    conversion = convert_lead_to_account_opportunity(
        actor_public_id=manifest["actor"]["public_id"], lead_public_id=lead_public_id
    )

    counts = cleanup_manifest(manifest)
    assert counts["leads"] == 2
    assert counts["opportunities"] >= 1
    assert counts["accounts"] >= 1

    assert _account_exists(conversion["account"]["public_id"]) is False
    with SessionLocal() as db:
        remaining_opportunity = db.execute(
            text("SELECT COUNT(*) FROM crm_opportunity WHERE opportunity_public_id = :id"),
            {"id": conversion["opportunity"]["public_id"]},
        ).scalar()
    assert remaining_opportunity == 0


def test_vendor_demo_bundle_cleanup_removes_the_entire_bundle_and_is_idempotent() -> None:
    manifest = run_scenario("vendor-demo-bundle")
    lead_public_id = manifest["records"]["lead_interactive"]["lead"]["public_id"]
    account_public_id = manifest["records"]["offer_ready_to_submit"]["account"]["public_id"]

    first_counts = cleanup_manifest(manifest)
    assert sum(first_counts.values()) > 0
    assert first_counts["leads"] == 2
    assert first_counts["lead_activities"] == 2

    with SessionLocal() as db:
        remaining_leads = db.execute(
            text("SELECT COUNT(*) FROM crm_lead WHERE lead_public_id = :id"), {"id": lead_public_id}
        ).scalar()
    assert remaining_leads == 0
    assert _account_exists(account_public_id) is False

    second_counts = cleanup_manifest(manifest)
    assert all(count == 0 for count in second_counts.values())


def test_vendor_demo_bundle_cleanup_does_not_touch_an_unrelated_run() -> None:
    demo_manifest = run_scenario("vendor-demo-bundle")
    other_manifest = run_scenario("rejected-offer")
    try:
        other_account = other_manifest["records"]["rejected_offer"]["account"]["public_id"]

        cleanup_manifest(demo_manifest)
        assert _account_exists(other_account) is True, "cleaning up vendor-demo-bundle must not touch an unrelated run"
    finally:
        cleanup_manifest(other_manifest)


def test_vendor_demo_bundle_cleanup_discovers_a_work_order_created_live_and_not_in_the_manifest() -> None:
    """Mirrors test_cleanup_discovers_a_work_order_created_after_seeding_and_not_recorded_in_the_manifest
    for the vendor-demo-bundle's own interactive Track C record."""
    from tooling.smoke_data.builders import create_work_order

    manifest = run_scenario("vendor-demo-bundle")
    record = manifest["records"]["offer_accepted_no_wo"]
    assert record["work_orders"] == []

    work_order = create_work_order(
        actor_public_id=manifest["actor"]["public_id"],
        offer_public_id=record["commercial_offer"]["public_id"],
    )

    counts = cleanup_manifest(manifest)
    assert counts["work_orders"] >= 1

    with SessionLocal() as db:
        remaining = db.execute(
            text("SELECT COUNT(*) FROM crm_work_order WHERE work_order_public_id = :id"),
            {"id": work_order["public_id"]},
        ).scalar()
    assert remaining == 0


def test_status_reports_all_present_then_missing_after_cleanup() -> None:
    from tooling.smoke_data.status import check_manifest_status

    manifest = run_scenario("rejected-offer")
    before = check_manifest_status(manifest)
    assert before["all_present"] is True
    assert before["found"]["accounts"] == 1

    cleanup_manifest(manifest)

    after = check_manifest_status(manifest)
    assert after["all_present"] is False
    assert after["found"]["accounts"] == 0


def test_prior_te1_scenarios_remain_compatible_after_lead_cleanup_extension() -> None:
    """Regression guard: extending _collect_ids/cleanup_manifest with lead_public_ids /
    lead_activity_public_ids (Slice 6P) must not change behavior for scenarios that have no
    Lead records at all."""
    manifest = run_scenario("core-regression-bundle")
    try:
        validate_manifest_dict(manifest)
        assert "handoff_target" in manifest["records"]
    finally:
        counts = cleanup_manifest(manifest)
        # Six record sets with one Account each: document_upload_target joined the bundle for upload rights
        # (11 September 2026), and resource_requirement_target for WRR-001 (24 September 2026). The seventh,
        # equipment_reference_target (ERT-1), has no Account: its models, import and machines are cleaned up
        # as tests/test_ert1_smoke_data.py checks. ERT-2 added a second crane model and three kit models; ELG-1 a
        # second wheeled crane with its carrier model and a sling model. 8A core added the eighth,
        # allocation_target, with its Account, and to the equipment a 250 t crawler model and its four kit models.
        # ELG-2 added the ninth, reminder_target, with its Account, and an 80 t crawler model and its sling model.
        # HOL-1 added the tenth, holiday_calendar_target, with its Account and a year of PBL's calendar far ahead.
        # CS-05a added the eleventh, stale_save_target, a draft offer with its Account; CS-05c the twelfth,
        # submitted_lock_target, a submitted offer with its Account.
        assert counts["accounts"] == 11
        assert counts["holiday_calendar_years"] == 1
        assert counts["equipment_models"] == 17 and counts["equipment_imports"] == 1
        assert counts.get("leads", 0) == 0
        assert counts.get("lead_activities", 0) == 0


def test_document_upload_target_is_a_draft_offer_and_cleanup_removes_files_uploaded_to_it() -> None:
    """The core bundle's document_upload_target is where the upload-rights Playwright spec
    attaches files: an Account, an Opportunity linked to it, and a DRAFT Commercial Offer with
    one active line.

    Those files arrive after seeding, through the real upload route, so the manifest never names
    them. Cleanup must still find them - by the (linked_record_type, public_id) pairs of the
    records it owns - and delete their stored bytes as well as their rows. The other document
    tests in this file cover a generated quotation and a metadata-only attachment; neither stores
    a user's file against an Account."""
    from fastapi.testclient import TestClient

    from app.modules.documents.storage import get_storage_provider_by_code

    manifest = run_scenario("core-regression-bundle")
    record = manifest["records"]["document_upload_target"]
    account_public_id = record["account"]["public_id"]
    offer_public_id = record["commercial_offer"]["public_id"]
    stored: list[tuple[str, str, str]] = []
    try:
        # The same shape as the other record sets, so cleanup, status and the E2E fixtures read
        # it without a special case.
        assert set(record) == {"account", "opportunity", "commercial_offer", "commercial_offer_status", "work_orders"}
        assert set(record["commercial_offer"]) == {"public_id", "offer_code", "line_public_id"}
        assert record["commercial_offer_status"] == "DRAFT"
        assert record["work_orders"] == []
        assert _offer_row(offer_public_id) == {"offer_status_code": "DRAFT"}

        with SessionLocal() as db:
            lines = db.execute(
                text(
                    """
                    SELECT line.line_public_id, line.line_status_code
                    FROM crm_commercial_offer_line line
                    INNER JOIN crm_commercial_offer co ON co.id = line.commercial_offer_id
                    WHERE co.offer_public_id = :id
                    """
                ),
                {"id": offer_public_id},
            ).fetchall()
            linked_account = db.execute(
                text(
                    """
                    SELECT bp.business_party_public_id
                    FROM crm_opportunity opp
                    INNER JOIN business_party bp ON bp.id = opp.business_party_id
                    WHERE opp.opportunity_public_id = :id
                    """
                ),
                {"id": record["opportunity"]["public_id"]},
            ).scalar()
        assert [(str(row[0]), row[1]) for row in lines] == [
            (record["commercial_offer"]["line_public_id"], "ACTIVE")
        ]
        assert str(linked_account) == account_public_id

        client = TestClient(app)
        login = client.post("/api/auth/login", json={"username": "sales1", "password": "password"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        # business_party is the Account spelling the documents API expects; cleanup also matches
        # the legacy "account" spelling, which the Slice 9C tests already exercise.
        for linked_record_type, linked_record_public_id in (
            ("business_party", account_public_id),
            ("commercial_offer", offer_public_id),
        ):
            response = client.post(
                "/api/documents/upload",
                headers=headers,
                data={
                    "linked_record_type": linked_record_type,
                    "linked_record_public_id": linked_record_public_id,
                    "document_type": "COMMERCIAL",
                },
                files={"file": (f"{linked_record_type}-attachment.pdf", b"%PDF-1.4 after seeding", "application/pdf")},
            )
            assert response.status_code == 201, response.text

        with SessionLocal() as db:
            stored = [
                (str(row[0]), str(row[1]), str(row[2]))
                for row in db.execute(
                    text(
                        "SELECT document_public_id, storage_provider_code, storage_key "
                        "FROM document_metadata WHERE linked_record_public_id IN (:account, :offer)"
                    ),
                    {"account": account_public_id, "offer": offer_public_id},
                ).fetchall()
            ]
        assert len(stored) == 2, "both uploads should have stored a document row with bytes"
    finally:
        counts = cleanup_manifest(manifest)

    # The two uploads here, and the certificate copies the bundle's equipment record set seeds: seven (ELG-1), eight
    # for the cranes and hook block allocation uses (8A core), and nine for the reminders' crawlers and sling (ELG-2).
    assert counts["documents"] == 2 + 7 + 8 + 9
    assert counts["documents_storage_deleted"] == 2 + 7 + 8 + 9
    for document_public_id, provider_code, storage_key in stored:
        assert (
            _count(
                "SELECT COUNT(*) FROM document_metadata WHERE document_public_id = :id",
                {"id": document_public_id},
            )
            == 0
        )
        assert not get_storage_provider_by_code(provider_code).exists(storage_key=storage_key), (
            f"cleanup left the stored bytes of {document_public_id} behind"
        )


# --- UAT data pack: cleanup must survive what a pilot user does ------------------------------
#
# The harness predates Slice 9C (documents), 9D (interactions) and 9E (quote documents), and has
# never created an account address, GSTIN or tax profile. Each of the three tests below drives a
# real service function against a seeded record - exactly what a PBL pilot user does through the
# screen - and then asserts the harness can still clean up after itself.
#
# This is the same bug class as
# test_cleanup_discovers_a_work_order_created_after_seeding_and_not_recorded_in_the_manifest
# above: a record the seed-time manifest never knew about, attached to a record it did. The fix
# is the same too - discover by ownership, not by trusting the manifest.


def test_cleanup_discovers_a_quote_document_generated_after_seeding() -> None:
    """The sharpest case, because it is the pilot's whole point. A user opens a seeded Commercial
    Offer and generates a quotation (Slice 9E). crm_commercial_offer_quote_document.commercial_offer_id
    is NOT NULL, so that quotation pins the offer: without ownership discovery the commercial_offers
    DELETE fails and the entire cleanup aborts. The better the pilot goes, the more reliably the
    reset breaks."""
    from uuid import UUID

    from app.modules.commercial_offers.service import generate_commercial_offer_quote_document

    # revision-requested leaves the offer SUBMITTED with an active line and Account traceability,
    # which is what generation requires; an ACCEPTED offer would be refused by its own precondition.
    manifest = run_scenario("revision-requested")
    record = manifest["records"]["revision_requested"]
    offer_public_id = record["commercial_offer"]["public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db,
            public_id=UUID(offer_public_id),
            current_user_public_id=manifest["actor"]["public_id"],
        )
    quote_document_public_id = str(generated.quote_document.public_id)
    stored_document_public_id = str(generated.quote_document.document_public_id)

    cleanup_manifest(manifest)

    assert (
        _count(
            "SELECT COUNT(*) FROM crm_commercial_offer_quote_document WHERE quote_document_public_id = :id",
            {"id": quote_document_public_id},
        )
        == 0
    )
    assert (
        _count(
            "SELECT COUNT(*) FROM document_metadata WHERE document_public_id = :id",
            {"id": stored_document_public_id},
        )
        == 0
    ), "the stored quotation document row must go too, or the offer delete would still be blocked"
    assert (
        _count(
            "SELECT COUNT(*) FROM crm_commercial_offer WHERE offer_public_id = :id",
            {"id": offer_public_id},
        )
        == 0
    )


def test_cleanup_removes_account_identity_records_attached_after_seeding() -> None:
    """A practice customer carrying a registered address, several GSTINs and a PAN is the whole
    point of the UAT dataset - and every one of those tables FKs to business_party with no
    ondelete, so the bare DELETE FROM business_party cannot proceed while they exist."""
    from uuid import UUID

    from app.modules.accounts.schemas import (
        AccountAddressCreate,
        AccountGstinCreate,
        AccountTaxProfileUpsert,
    )
    from app.modules.accounts.service import (
        create_account_address,
        create_account_gstin,
        upsert_account_tax_profile,
    )

    manifest = run_scenario("accepted-offer-no-work-order")
    record = manifest["records"]["handoff_target"]
    account_public_id = record["account"]["public_id"]
    # Format-valid but deliberately impossible, per the 9 September 2026 owner decision. PAN is
    # ^[A-Z]{5}[0-9]{4}[A-Z]$ and its 4th character encodes entity type (C/P/H/F/A/T/B/L/J/G), so
    # a ZZZZZ block satisfies the regex while naming no issuable entity - the screens and their
    # validation are exercised in full without risking a real business's statutory number.
    # The digits come from the run id so two runs cannot collide on the globally unique
    # ux_business_party_gstin index.
    digits = int(manifest["run_id"].split("-")[-1], 16) % 10000
    pan = f"ZZZZZ{digits:04d}Z"
    gstin = f"37{pan}1ZZ"

    with SessionLocal() as db:
        address = create_account_address(
            db,
            account_public_id=UUID(account_public_id),
            payload=AccountAddressCreate(
                address_type_code="SITE",
                address_line1="Alumina Refinery Expansion Site, Plot R-7, Phase III",
                address_line2="Near Weighbridge Gate No. 4, Lanjigarh Industrial Area",
                city="Lanjigarh",
                district="Kalahandi",
                state="Odisha",
                postal_code="766027",
            ),
            current_user_public_id=manifest["actor"]["public_id"],
        )
        gstin_row = create_account_gstin(
            db,
            account_public_id=UUID(account_public_id),
            payload=AccountGstinCreate(gstin=gstin, state_code="37", state_name="Andhra Pradesh"),
            current_user_public_id=manifest["actor"]["public_id"],
        )
        upsert_account_tax_profile(
            db,
            account_public_id=UUID(account_public_id),
            payload=AccountTaxProfileUpsert(pan=pan),
            current_user_public_id=manifest["actor"]["public_id"],
        )

    cleanup_manifest(manifest)

    assert not _account_exists(account_public_id)
    assert (
        _count(
            "SELECT COUNT(*) FROM business_party_address WHERE address_public_id = :id",
            {"id": str(address.address.public_id)},
        )
        == 0
    )
    assert (
        _count("SELECT COUNT(*) FROM business_party_gstin WHERE gstin = :g", {"g": gstin}) == 0
    ), "a surviving GSTIN would also collide with the next run, since the index is globally unique"
    assert (
        _count(
            "SELECT COUNT(*) FROM business_event WHERE record_public_id = :id",
            {"id": str(gstin_row.gstin.public_id)},
        )
        == 0
    ), "the GSTIN audit row is keyed by the GSTIN public id, so the event cleanup must cover it too"


def test_cleanup_discovers_an_interaction_logged_after_seeding() -> None:
    """A pilot user logging a call or email against a seeded Commercial Offer (Slice 9D). The
    interaction is keyed by linked_record_public_id, so cleanup must discover it from the records
    this run owns rather than from the manifest."""
    from datetime import datetime, timezone
    from uuid import UUID

    from app.modules.identity.schemas import AuthUser
    from app.modules.interactions.schemas import InteractionCreate
    from app.modules.interactions.service import create_interaction

    manifest = run_scenario("accepted-offer-no-work-order")
    record = manifest["records"]["handoff_target"]
    offer_public_id = record["commercial_offer"]["public_id"]

    actor = AuthUser(
        public_id=manifest["actor"]["public_id"],
        username=manifest["actor"]["username"],
        display_name=manifest["actor"]["username"],
        roles=["Sales User"],
        role_codes=["SALES_USER"],
    )
    with SessionLocal() as db:
        interaction = create_interaction(
            db,
            payload=InteractionCreate(
                linked_record_type="commercial_offer",
                linked_record_public_id=UUID(offer_public_id),
                channel_code="CALL",
                direction_code="OUTBOUND",
                occurred_at=datetime.now(timezone.utc),
                subject="Discussed 250mt crane availability for the erection window",
            ),
            current_user_public_id=manifest["actor"]["public_id"],
            current_user=actor,
        )

    cleanup_manifest(manifest)

    assert (
        _count(
            "SELECT COUNT(*) FROM interaction WHERE interaction_public_id = :id",
            {"id": str(interaction.interaction.public_id)},
        )
        == 0
    )
    assert (
        _count(
            "SELECT COUNT(*) FROM crm_commercial_offer WHERE offer_public_id = :id",
            {"id": offer_public_id},
        )
        == 0
    )


# --- UAT pilot dataset ------------------------------------------------------------------------


def _uat_html(document_public_id: str) -> str:
    from app.modules.documents.storage import get_storage_provider_by_code

    with SessionLocal() as db:
        row = db.execute(
            text(
                "SELECT storage_provider_code, storage_key FROM document_metadata "
                "WHERE document_public_id = :d"
            ),
            {"d": document_public_id},
        ).first()
    with get_storage_provider_by_code(row[0]).open(storage_key=row[1]) as handle:
        return handle.read().decode("utf-8")


def test_uat_pilot_seeded_spans_every_lifecycle_stage() -> None:
    """A pilot dataset that only contains happy-path records teaches the pilot nothing. This
    asserts the spread rather than the row count: offers in every reachable status, a superseded
    quotation version, and records deliberately WITHOUT a quotation or an interaction so the
    advisory readiness rows show both states."""
    manifest = run_scenario("uat-pilot-seeded")
    try:
        records = manifest["records"]
        assert len(records) == 13  # three leads plus ten customers

        with SessionLocal() as db:
            statuses = {
                key: db.execute(
                    text("SELECT offer_status_code FROM crm_commercial_offer WHERE offer_public_id = :o"),
                    {"o": record["commercial_offer"]["public_id"]},
                ).scalar()
                for key, record in records.items()
                if record.get("commercial_offer")
            }
        assert set(statuses.values()) == {"DRAFT", "SUBMITTED", "ACCEPTED", "REJECTED"}

        # One offer carries two versions, the earlier superseded but keeping its own history.
        versions = records["macdiarmid_offshore"]["quote_documents"]
        assert [v["version_no"] for v in versions] == [1, 2]

        # An offer with no quotation at all, so QUOTATION_DOCUMENT reads ATTENTION_REQUIRED while
        # INTERACTION_LOG reads PASS - the pilot needs to see a checklist that is not all green.
        assert records["harshita_projects"]["quote_documents"] == []
        assert records["harshita_projects"]["interactions"] != []
        # And the mirror image: an offer with a quotation but no interaction logged.
        assert records["godavari_paper"]["interactions"] == []

        assert sum(len(r["work_orders"]) for r in records.values()) == 3
        assert len(records["carson_two_bros"]["related_offers"]) == 2
    finally:
        cleanup_manifest(manifest)


def test_uat_pilot_seeded_carries_the_awkward_shapes_it_exists_to_test() -> None:
    """The dataset's purpose is to break layouts before PBL users do. Each assertion here stands
    for one shape that a tidy dataset would hide."""
    manifest = run_scenario("uat-pilot-seeded")
    try:
        records = manifest["records"]
        account_public_id = records["kakinada_steel"]["account"]["public_id"]

        with SessionLocal() as db:
            legal_name = db.execute(
                text("SELECT legal_name FROM business_party WHERE business_party_public_id = :a"),
                {"a": account_public_id},
            ).scalar()
            site = db.execute(
                text(
                    """
                    SELECT address_line1, address_line2, city, district, state
                    FROM business_party_address a
                    JOIN business_party bp ON bp.id = a.business_party_id
                    WHERE bp.business_party_public_id = :a AND a.address_type_code = 'SITE'
                    """
                ),
                {"a": records["vedansha_resources"]["account"]["public_id"]},
            ).first()
            gstins = [
                row[0]
                for row in db.execute(
                    text(
                        """
                        SELECT bg.gstin FROM business_party_gstin bg
                        JOIN business_party bp ON bp.id = bg.business_party_id
                        WHERE bp.business_party_public_id = :a ORDER BY bg.gstin
                        """
                    ),
                    {"a": account_public_id},
                ).fetchall()
            ]

        # A legal name long enough to break a table column or a document header.
        assert len(legal_name) > 200

        # A site address that genuinely needs its second line, and whose district differs from
        # its city - the case that exposes rendering which assumes one line and one place name.
        assert site is not None and site[1] and site[3] != site[2]

        # Several state registrations, all sharing one PAN, because that is how a real multi-state
        # entity is registered - GSTIN is state code + PAN + suffix.
        assert len(gstins) == 4
        assert len({g[2:12] for g in gstins}) == 1, "all GSTINs of one entity must share its PAN"
        assert len({g[:2] for g in gstins}) == 4, "and must be in four different states"
    finally:
        cleanup_manifest(manifest)


def test_uat_synthetic_pan_is_format_valid_but_could_never_be_issued() -> None:
    """The owner decision of 9 September 2026: exercise the PAN/GST screens in full without any
    chance of naming a real business. SurePass validation is deferred (ADR-015), so nothing checks
    these against the registry - the safety has to be structural."""
    import re

    from tooling.smoke_data.scenarios import _uat_gstin, _uat_pan

    pan = _uat_pan("te1-abcd1234", 0)
    assert re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan), "must satisfy the application's PAN format"
    # Fourth character is the entity type - C/P/H/F/A/T/B/L/J/G. 'Z' is not among them, so this
    # PAN cannot correspond to any entity the Income Tax Department could have issued.
    assert pan[3] == "Z" and pan[3] not in "CPHFATBLJG"
    assert re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", _uat_gstin("te1-abcd1234", 0, "37"))
    # Different runs must not collide on the globally unique GSTIN index.
    assert _uat_gstin("te1-abcd1234", 0, "37") != _uat_gstin("te1-99999999", 0, "37")


def test_uat_quotation_never_presents_a_partial_sum_as_a_total() -> None:
    """One practice offer deliberately carries an ACTIVE line with no rate, which is reachable in
    the application. Slice 9E shipped two wrong totals for this case before it was caught, so the
    dataset that exercises it keeps its own guard."""
    manifest = run_scenario("uat-pilot-seeded")
    try:
        record = manifest["records"]["saint_guilbert"]
        html = _uat_html(record["quote_documents"][0]["document_public_id"])

        # Anchor on the total row itself, not on the whole document. 952,000.00 IS legitimately
        # present as the priced line's own amount (14 trips x 68,000) and must stay visible; the
        # defect being guarded against is that same figure appearing as the TOTAL, where it would
        # be a partial sum wearing the label of a complete quotation. An earlier version of this
        # test searched the whole document and would have failed on the correct output.
        total_row_start = html.index('<tr class="total-row">')
        total_row = html[total_row_start : html.index("</tr>", total_row_start)]
        assert "Not fully priced" in total_row
        assert "952,000" not in total_row and "952000" not in total_row
        assert "952,000.00" in html, "the priced line's own amount must still be shown"
    finally:
        cleanup_manifest(manifest)


def test_uat_pilot_seeded_leaves_nothing_behind() -> None:
    """The load-bearing test of the whole pack. The pilot's synthetic basis is what allows the
    unresolved retention-purge and download-audit items to not block it, and that argument only
    holds if the data can actually be removed - including the quotations, stored files and logged
    conversations that pilot users generate on top of the seed."""
    manifest = run_scenario("uat-pilot-seeded")
    # Not every record has an Account or an offer: a lead closed as not worth pursuing never
    # produced either, and that is the point of including it.
    account_ids = [r["account"]["public_id"] for r in manifest["records"].values() if r.get("account")]
    offer_ids = [
        r["commercial_offer"]["public_id"]
        for r in manifest["records"].values()
        if r.get("commercial_offer")
    ]
    document_ids = [
        quote["document_public_id"]
        for record in manifest["records"].values()
        for quote in record.get("quote_documents", [])
    ]
    assert document_ids, "the dataset must generate quotations, or this test proves nothing"

    cleanup_manifest(manifest)

    for account_public_id in account_ids:
        assert not _account_exists(account_public_id)
    for table, column, ids in (
        ("crm_commercial_offer", "offer_public_id", offer_ids),
        ("document_metadata", "document_public_id", document_ids),
    ):
        for public_id in ids:
            assert (
                _count(f"SELECT COUNT(*) FROM {table} WHERE {column} = :id", {"id": public_id}) == 0
            ), f"{table} row {public_id} survived cleanup"
    # Nothing may remain attached to the offers either, whether or not it declared a foreign key.
    for offer_public_id in offer_ids:
        assert (
            _count(
                "SELECT COUNT(*) FROM interaction WHERE linked_record_public_id = :id",
                {"id": offer_public_id},
            )
            == 0
        )


def test_status_reports_attached_records_that_could_outlive_their_parent() -> None:
    """The status check used to look only at anchor records, on the stated grounds that
    subordinates are foreign-key bound to them. Quote documents, documents and interactions are
    not, so a reset could leave them behind and status would still have reported a clean result -
    the same silent-residue failure the cleanup corrections in this package fixed. The UAT runbook
    tells the pilot operator to use status to confirm a reset worked, so it has to be able to see
    them."""
    from tooling.smoke_data.status import check_manifest_status

    manifest = run_scenario("uat-pilot-seeded")
    try:
        seeded = check_manifest_status(manifest)
        assert seeded["all_present"] is True
        # While the dataset exists, every one of these must be visible to the status check.
        for key in ("quote_documents", "documents", "interactions", "account_addresses", "account_gstins"):
            assert seeded["residue"][key] > 0, f"status cannot see {key}"
        assert seeded["residue_clear"] is False
    finally:
        cleanup_manifest(manifest)

    cleaned = check_manifest_status(manifest)
    assert cleaned["all_absent"] is True
    assert cleaned["residue_clear"] is True, "a finished cleanup must leave nothing attached"
    assert all(count == 0 for count in cleaned["residue"].values())


# --- corrections from the deletion-path review ------------------------------------------------
#
# Three defects found by an adversarial read of the cleanup diff, each one a way for data to
# survive a reset that reported success. All are the same shape as the defects this package was
# written to fix, one level further down, which is why each gets its own regression test.


def test_cleanup_removes_a_document_attached_to_an_interaction() -> None:
    """`interaction` is a first-class document link type with its own extra content permission,
    so attaching a file to a logged call is ordinary use. That document hangs off the
    INTERACTION's public id, not the offer's - and the interaction itself is deleted by this
    cleanup. Without covering it, the reset would delete the parent conversation and leave the
    attachment behind with its bytes on disk."""
    from uuid import UUID

    from app.modules.documents.schemas import DocumentMetadataCreate
    from app.modules.documents.service import create_document_metadata
    from tooling.smoke_data.builders import log_interaction

    manifest = run_scenario("accepted-offer-no-work-order")
    record = manifest["records"]["handoff_target"]
    interaction = log_interaction(
        actor_public_id=manifest["actor"]["public_id"],
        actor_username=manifest["actor"]["username"],
        linked_record_type="commercial_offer",
        linked_record_public_id=record["commercial_offer"]["public_id"],
        channel_code="EMAIL",
        direction_code="INBOUND",
        subject="Customer sent the signed rate confirmation",
    )
    with SessionLocal() as db:
        attachment = create_document_metadata(
            db,
            payload=DocumentMetadataCreate(
                document_type="COMMERCIAL",
                linked_record_type="interaction",
                linked_record_public_id=UUID(interaction["public_id"]),
                file_name="rate-confirmation.pdf",
                storage_path_or_url="https://example.invalid/rate-confirmation.pdf",
            ),
            current_user_public_id=manifest["actor"]["public_id"],
        )
    attachment_public_id = str(attachment.document.public_id)

    cleanup_manifest(manifest)

    assert (
        _count(
            "SELECT COUNT(*) FROM document_metadata WHERE document_public_id = :id",
            {"id": attachment_public_id},
        )
        == 0
    ), "a document attached to a deleted interaction must not survive it"
    assert (
        _count(
            "SELECT COUNT(*) FROM interaction WHERE interaction_public_id = :id",
            {"id": interaction["public_id"]},
        )
        == 0
    )


def test_cleanup_removes_audit_rows_keyed_by_interaction_and_quote_document_ids() -> None:
    """Interactions and quote documents write their business_event with record_public_id set to
    their OWN public id, not the linked record's. The event cleanup unions the anchor ids, so
    without collecting these two the audit rows outlive their subject.

    The quote-document case additionally has to be collected BEFORE the delete: once the row is
    gone its public id cannot be recovered from the database, so a later corrective sweep could
    never find the orphaned event at all."""
    from tooling.smoke_data.builders import generate_quote_document, log_interaction

    manifest = run_scenario("revision-requested")
    record = manifest["records"]["revision_requested"]
    offer_public_id = record["commercial_offer"]["public_id"]

    quote = generate_quote_document(
        actor_public_id=manifest["actor"]["public_id"], offer_public_id=offer_public_id
    )
    interaction = log_interaction(
        actor_public_id=manifest["actor"]["public_id"],
        actor_username=manifest["actor"]["username"],
        linked_record_type="commercial_offer",
        linked_record_public_id=offer_public_id,
        channel_code="CALL",
        direction_code="OUTBOUND",
        subject="Walked the customer through the revised rate",
    )

    # Both must have written an audit row keyed by their own id, or this test proves nothing.
    for public_id in (quote["public_id"], interaction["public_id"]):
        assert (
            _count(
                "SELECT COUNT(*) FROM business_event WHERE record_public_id = :id",
                {"id": public_id},
            )
            > 0
        ), f"expected a business_event keyed by {public_id}"

    cleanup_manifest(manifest)

    for public_id in (quote["public_id"], interaction["public_id"]):
        assert (
            _count(
                "SELECT COUNT(*) FROM business_event WHERE record_public_id = :id",
                {"id": public_id},
            )
            == 0
        ), f"audit row for {public_id} outlived its subject"


def test_cleanup_reports_storage_deletion_failures_rather_than_swallowing_them() -> None:
    """delete_stored_document_object is deliberately silent about failure - correct for its
    original use as compensation for a rolled-back transaction, wrong here where it is the
    primary deletion path. A storage provider that is down would otherwise produce a clean
    "cleanup succeeded" with every file still on disk."""
    manifest = run_scenario("revision-requested")
    record = manifest["records"]["revision_requested"]
    from tooling.smoke_data.builders import generate_quote_document

    generate_quote_document(
        actor_public_id=manifest["actor"]["public_id"],
        offer_public_id=record["commercial_offer"]["public_id"],
    )

    counts = cleanup_manifest(manifest)

    assert counts["documents"] == 1
    # Reports what was actually removed rather than asserting it. The failure path is covered
    # separately by test_cleanup_raises_rather_than_reporting_success_when_bytes_cannot_be_deleted,
    # which is where a storage failure now surfaces: it raises with the orphaned keys named,
    # instead of returning a count that the CLI would print as "1 deleted" and exit 0 on.
    assert counts["documents_storage_deleted"] == 1


def test_uat_dataset_covers_the_work_before_the_offer() -> None:
    """The first version of this dataset started every customer at an Account with an Opportunity
    already attached - the middle of the story. A sales executive spends most of the day on the
    part before that: working an enquiry, deciding whether it is worth pursuing, getting rates from
    the market, choosing which one to quote on, and negotiating. Each assertion here stands for one
    of those, because a pilot that never shows them does not test the job."""
    manifest = run_scenario("uat-pilot-seeded")
    try:
        records = manifest["records"]

        # Leads at three different points of their life, reached through the real actions.
        with SessionLocal() as db:
            lead_statuses = {
                key: db.execute(
                    text("SELECT lead_status_code FROM crm_lead WHERE lead_public_id = :i"),
                    {"i": record["lead"]["public_id"]},
                ).scalar()
                for key, record in records.items()
                if record.get("lead")
            }
        assert lead_statuses == {
            "lead_converted": "CONVERTED",
            "lead_closed": "UNQUALIFIED",
            "lead_in_progress": "NEW",
        }
        # The manifest must agree with the database, or the runbook table built from it misleads.
        for key, expected in lead_statuses.items():
            assert records[key]["lead"]["lead_status_code"] == expected

        # A worked lead is a sequence of contacts, not one entry.
        assert len(records["lead_converted"]["activities"]) >= 3
        assert len(records["lead_closed"]["activities"]) >= 3

        # The converted lead really produced its Account, Opportunity and offer.
        converted = records["lead_converted"]
        assert converted["account"]["public_id"] and converted["opportunity"]["public_id"]
        assert converted["commercial_offer"]["line_public_ids"]

        # A closed lead must NOT have produced any of that.
        assert "account" not in records["lead_closed"]

        # Rate discovery: several quotes, and a choice that is visible because there is something
        # to choose between. Both outcomes must appear across the dataset - always taking the
        # lowest would hide the case the selection_reason field exists for.
        priced = [r for r in records.values() if r.get("pricing_evidence")]
        # Slice 4G: three quotes on every line the offer was made with, each line with its own basis rate.
        assert all(r["pricing_evidence"]["lines"] for r in priced)
        assert all(len(entry["quotes"]) == 3 for r in priced for entry in r["pricing_evidence"]["lines"])
        choices = {r["pricing_evidence"]["chose_lowest"] for r in priced}
        assert choices == {True, False}, "the dataset must show both the lowest and a dearer choice"

        with SessionLocal() as db:
            for record in priced:
                for entry in record["pricing_evidence"]["lines"]:
                    rates = [
                        row[0]
                        for row in db.execute(
                            text(
                                """
                                SELECT pe.rate_amount FROM crm_commercial_offer_pricing_evidence pe
                                JOIN crm_commercial_offer_line line ON line.id = pe.commercial_offer_line_id
                                WHERE line.line_public_id = :line ORDER BY pe.rate_amount
                                """
                            ),
                            {"line": entry["line_public_id"]},
                        ).fetchall()
                    ]
                    chosen = db.execute(
                        text(
                            """
                            SELECT pe.rate_amount, choice.selection_reason
                            FROM crm_commercial_offer_pricing_evidence pe
                            JOIN crm_commercial_offer_line line ON line.id = pe.commercial_offer_line_id
                            JOIN crm_commercial_offer_line_basis_choice choice
                                ON choice.pricing_evidence_id = pe.id AND choice.ended_at IS NULL
                            WHERE line.line_public_id = :line
                            """
                        ),
                        {"line": entry["line_public_id"]},
                    ).first()
                    assert len(rates) == 3
                    assert chosen is not None, "every line with quotes must have a chosen basis rate"
                    assert chosen[1], "a basis choice without a recorded reason is not defensible"
                    if not record["pricing_evidence"]["chose_lowest"]:
                        assert chosen[0] > rates[0], "the dearer-choice case must not be the lowest rate"

        # Negotiation is a conversation, so at least one customer must show a trail rather than a
        # single message.
        assert max(len(r.get("interactions", [])) for r in records.values()) >= 4

        # A real immutable version series, not merely a response asking for a revision.
        revised = [r for r in records.values() if r.get("offer_versions")]
        assert revised, "the dataset must contain a real Commercial Offer version series"
        with SessionLocal() as db:
            statuses = db.execute(
                text(
                    "SELECT version_number, offer_status_code FROM crm_commercial_offer "
                    "WHERE offer_code = :code ORDER BY version_number"
                ),
                {"code": revised[0]["commercial_offer"]["offer_code"]},
            ).fetchall()
        assert statuses == [(1, "REVISED"), (2, "SUBMITTED")]
        # Each immutable offer version carries its own quotation document.
        assert len(revised[0]["quote_documents"]) == 2
    finally:
        cleanup_manifest(manifest)


# --- corrections from the second independent review -------------------------------------------
#
# Six findings, five of them P1. The common cause was that ownership discovery followed each
# relationship one level and stopped, so every fix left another level behind it. Discovery is now
# a closure over the record graph rather than a fixed sequence of calls, and status runs the same
# closure so the two cannot drift apart. Each test below reproduces one reported failure.


def test_cleanup_removes_an_ordinary_offer_created_on_a_seeded_opportunity() -> None:
    """Reported as an FK rollback that aborted the whole cleanup. Discovery found RELATED offers
    from an owned offer, but never an ordinary offer raised on an owned Opportunity - which is
    exactly what a pilot user does when they quote a seeded enquiry themselves."""
    from decimal import Decimal

    from tooling.smoke_data.builders import add_offer_line, create_offer_no_line

    # A REJECTED offer counts as inactive for the Slice 6B.1 one-active-offer-per-Opportunity
    # guard, so a second offer on the same Opportunity is permitted - which is precisely the
    # situation being tested. Using an ACCEPTED scenario here is correctly refused by that guard.
    manifest = run_scenario("rejected-offer")
    record = manifest["records"]["rejected_offer"]

    live_offer = create_offer_no_line(
        run_id=manifest["run_id"],
        actor_public_id=manifest["actor"]["public_id"],
        opportunity_public_id=record["opportunity"]["public_id"],
        suffix="live",
        offer_title="Raised by a user against a seeded enquiry",
    )
    add_offer_line(
        actor_public_id=manifest["actor"]["public_id"],
        offer_public_id=live_offer["public_id"],
        quantity=Decimal("1"),
        rate_amount=Decimal("1000.00"),
    )

    cleanup_manifest(manifest)  # must not raise

    assert (
        _count(
            "SELECT COUNT(*) FROM crm_commercial_offer WHERE offer_public_id = :id",
            {"id": live_offer["public_id"]},
        )
        == 0
    )


def test_cleanup_removes_an_account_repaired_onto_a_seeded_opportunity() -> None:
    """Reported as surviving silently with its business_event. Discovery found Accounts only
    through Opportunities it had itself discovered from a Lead, so an Account reached any other
    way was never seen."""
    from uuid import UUID

    from app.modules.opportunities import service as opportunities_service
    from app.modules.opportunities.schemas import (
        OpportunityAccountRepairRequest,
        OpportunityCreate,
    )
    from tooling.smoke_data.builders import create_account

    manifest = run_scenario("accepted-offer-no-work-order")
    actor_public_id = manifest["actor"]["public_id"]

    live_account = create_account(
        run_id=manifest["run_id"], actor_public_id=actor_public_id, suffix="repaired"
    )
    with SessionLocal() as db:
        created = opportunities_service.create_opportunity(
            db,
            payload=OpportunityCreate(
                opportunity_name="Opportunity a user repaired onto a seeded Account",
                opportunity_source="manual",
            ),
            current_user_public_id=actor_public_id,
        )
        opportunity_public_id = created.opportunity.public_id
    with SessionLocal() as db:
        opportunities_service.repair_opportunity_account(
            db,
            public_id=opportunity_public_id,
            payload=OpportunityAccountRepairRequest(account_public_id=UUID(live_account["public_id"])),
            current_user_public_id=actor_public_id,
        )

    # The seeded manifest does not know about either record. Added as its OWN record rather than
    # replacing the seeded account, which would drop that account from the manifest and leak it.
    manifest["records"]["live_repair"] = {"account": live_account}
    cleanup_manifest(manifest)

    assert not _account_exists(live_account["public_id"])
    assert (
        _count(
            "SELECT COUNT(*) FROM crm_opportunity WHERE opportunity_public_id = :id",
            {"id": str(opportunity_public_id)},
        )
        == 0
    )
    assert (
        _count(
            "SELECT COUNT(*) FROM business_event WHERE record_public_id = :id",
            {"id": live_account["public_id"]},
        )
        == 0
    )


def test_cleanup_removes_the_audit_event_of_a_lead_activity_created_after_seeding() -> None:
    """Reported as leaving exactly one business_event behind. The activity itself was deleted by
    Lead ownership, but the event cleanup only knew activity ids recorded in the manifest."""
    from tooling.smoke_data.builders import add_lead_activity

    manifest = run_scenario("vendor-demo-bundle")
    lead_record = next(r for r in manifest["records"].values() if r.get("lead"))
    activity = add_lead_activity(
        actor_public_id=manifest["actor"]["public_id"],
        lead_public_id=lead_record["lead"]["public_id"],
    )
    assert (
        _count(
            "SELECT COUNT(*) FROM business_event WHERE record_public_id = :id",
            {"id": activity["public_id"]},
        )
        > 0
    ), "the activity must have written an event, or this test proves nothing"

    cleanup_manifest(manifest)

    assert (
        _count(
            "SELECT COUNT(*) FROM business_event WHERE record_public_id = :id",
            {"id": activity["public_id"]},
        )
        == 0
    )


def test_status_detects_an_orphaned_quote_document() -> None:
    """Reported as status certifying a failed reset as clean. The residue query joined through
    `crm_commercial_offer`, so once the offer was deleted the join matched nothing - and an
    orphaned quote document, the only case worth detecting, was invisible to the check written
    to detect it."""
    from tooling.smoke_data.status import check_manifest_status

    manifest = run_scenario("revision-requested")
    record = manifest["records"]["revision_requested"]
    from tooling.smoke_data.builders import generate_quote_document

    quote = generate_quote_document(
        actor_public_id=manifest["actor"]["public_id"],
        offer_public_id=record["commercial_offer"]["public_id"],
    )
    cleanup_manifest(manifest)
    assert check_manifest_status(manifest)["residue_clear"] is True

    orphan_public_id = str(uuid4())
    # Recreate exactly the state a silent cleanup failure leaves: a quote document whose offer
    # no longer exists. Status must see it even though nothing links it to this run any more.
    #
    # The ids are FRESH, and that is the point: this test's subject is an orphan nobody can trace.
    # An earlier version reused the deleted quotation's own public id, which made the orphan
    # attributable and no longer an example of what the test claims to check.
    with SessionLocal() as db:
        db.execute(
            text(
                """
                INSERT INTO crm_commercial_offer_quote_document
                    (quote_document_public_id, commercial_offer_id, version_no, quote_reference,
                     document_public_id, source_fingerprint, quote_status_code, generated_by,
                     generated_at, created_at, updated_at)
                VALUES (:q, -1, 1, 'ORPHAN/V1', :d, 'x', 'DRAFT', NULL,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"q": orphan_public_id, "d": str(uuid4())},
        )
        db.commit()
    try:
        after = check_manifest_status(manifest)
        # Visible, so an operator can act on it...
        assert after["residue"]["orphaned_quote_documents"] >= 1
        # ...but NOT counted against this run. An orphan cannot be traced to whoever created it,
        # so attributing it here would report every subsequent reset as having left it behind -
        # and a warning that fires every time is one an operator learns to ignore. An earlier
        # version of this test asserted the opposite and locked in that poisoning.
        assert after["residue_clear"] is True, (
            "an unattributable orphan must not condemn a run whose own records are all gone"
        )
    finally:
        with SessionLocal() as db:
            # By this test's OWN row id, never by `commercial_offer_id = -1`, which would erase
            # any orphan another run had left in this shared database. An earlier version did
            # exactly that: a destructive teardown, in a test file whose subject is not deleting
            # other people's records.
            db.execute(
                text(
                    "DELETE FROM crm_commercial_offer_quote_document "
                    "WHERE quote_document_public_id = :q"
                ),
                {"q": orphan_public_id},
            )
            db.commit()


def test_cleanup_raises_rather_than_reporting_success_when_bytes_cannot_be_deleted() -> None:
    """Reported twice over: the existence check could not distinguish a refused deletion from a
    successful one, and a detected failure was printed by the CLI as "1 deleted" with exit 0.

    A storage failure now raises, carrying the orphaned keys in the message - because by the time
    it is known the rows are already committed away, and nothing can rediscover those keys from
    the database afterwards. The message is the only surviving record of them."""
    import tooling.smoke_data.cleanup as cleanup_module
    from tooling.smoke_data.builders import generate_quote_document
    from tooling.smoke_data.cleanup import CleanupStorageError

    manifest = run_scenario("revision-requested")
    record = manifest["records"]["revision_requested"]
    quote = generate_quote_document(
        actor_public_id=manifest["actor"]["public_id"],
        offer_public_id=record["commercial_offer"]["public_id"],
    )
    # Captured before cleanup runs, because afterwards the row is gone and the key is
    # unrecoverable - which is the very property this test exists to demonstrate, and which makes
    # re-running cleanup useless as a way of tidying up after it.
    with SessionLocal() as db:
        real_key = db.execute(
            text("SELECT storage_key FROM document_metadata WHERE document_public_id = :d"),
            {"d": quote["document_public_id"]},
        ).scalar()

    real_resolver = cleanup_module.get_storage_provider_by_code

    class _RefusingProvider:
        """Accepts the delete call and does nothing - the shape of a provider that is down, or
        that rejects the key. Indistinguishable from success without a before-and-after check."""

        def __init__(self, wrapped: object) -> None:
            self._wrapped = wrapped

        def exists(self, *, storage_key: str) -> bool:
            return True

        def delete(self, *, storage_key: str) -> None:
            return None

    cleanup_module.get_storage_provider_by_code = lambda code: _RefusingProvider(real_resolver(code))
    try:
        with pytest.raises(CleanupStorageError) as raised:
            cleanup_manifest(manifest)
        assert "could not be deleted" in str(raised.value)
        assert "local:" in str(raised.value), "the orphaned key must be named, or it is lost"
    finally:
        cleanup_module.get_storage_provider_by_code = real_resolver
        # The database half committed before the storage failure, so the rows are already gone and
        # re-running cleanup would find nothing. The file has to be removed by its captured key.
        real_resolver("local").delete(storage_key=real_key)


def test_ownership_closure_settles_and_does_not_reach_unrelated_records() -> None:
    """The closure expands until nothing grows. Its boundary is that nothing is reached except
    through a real relationship to something the run owns - so a wholly unrelated Account, of the
    kind another test or another run created, must be untouched."""
    from tooling.smoke_data.builders import create_account

    manifest = run_scenario("accepted-offer-no-work-order")
    bystander = create_account(
        run_id="te1-bbbbbbbb", actor_public_id=manifest["actor"]["public_id"], suffix="bystander"
    )
    try:
        cleanup_manifest(manifest)
        assert _account_exists(bystander["public_id"]), "cleanup reached a record it does not own"
    finally:
        cleanup_manifest(
            {
                "manifest_version": 1,
                "run_id": "te1-bbbbbbbb",
                "scenario": "bystander",
                "created_at": "2026-09-10T00:00:00Z",
                "records": {"b": {"account": bystander}},
            }
        )


# --- corrections from the third independent review --------------------------------------------


def test_cleanup_does_not_delete_an_account_another_run_already_owned() -> None:
    """The most serious finding of the third review, and the one the previous test missed by
    testing the opposite direction.

    Run B owns only an Opportunity and repairs it onto run A's PRE-EXISTING Account. Cleaning up
    run B must not take run A's Account with it - an Account is a parent that several runs may
    point at, not a child of B's Opportunity, so being reachable from B is not the same as
    belonging to B.

    `test_cleanup_removes_an_account_repaired_onto_a_seeded_opportunity` starts from an Account
    already in the manifest, so it exercises manifest -> Opportunity and cannot catch this."""
    from uuid import UUID

    from app.modules.opportunities import service as opportunities_service
    from app.modules.opportunities.schemas import (
        OpportunityAccountRepairRequest,
        OpportunityCreate,
    )

    run_a = run_scenario("accepted-offer-no-work-order")
    run_a_account = run_a["records"]["handoff_target"]["account"]
    actor_public_id = run_a["actor"]["public_id"]

    # Run B: an Opportunity of its own, repaired onto run A's Account.
    with SessionLocal() as db:
        created = opportunities_service.create_opportunity(
            db,
            payload=OpportunityCreate(
                opportunity_name="Run B opportunity, later repaired onto run A's Account",
                opportunity_source="manual",
            ),
            current_user_public_id=actor_public_id,
        )
        run_b_opportunity_public_id = str(created.opportunity.public_id)
    with SessionLocal() as db:
        opportunities_service.repair_opportunity_account(
            db,
            public_id=UUID(run_b_opportunity_public_id),
            payload=OpportunityAccountRepairRequest(account_public_id=UUID(run_a_account["public_id"])),
            current_user_public_id=actor_public_id,
        )

    run_b = {
        "manifest_version": 1,
        "run_id": "te1-0b0b0b0b",
        "scenario": "run-b",
        "created_at": "2026-09-10T00:00:00Z",
        "records": {
            "only_an_opportunity": {
                "opportunity": {
                    "public_id": run_b_opportunity_public_id,
                    "opportunity_name": "Run B opportunity",
                }
            }
        },
    }
    try:
        cleanup_manifest(run_b)

        assert _account_exists(run_a_account["public_id"]), (
            "cleaning up run B deleted run A's Account - reachability was treated as ownership"
        )
        # And run A's own records must be untouched behind it.
        assert (
            _count(
                "SELECT COUNT(*) FROM crm_commercial_offer WHERE offer_public_id = :id",
                {"id": run_a["records"]["handoff_target"]["commercial_offer"]["public_id"]},
            )
            == 1
        )
        assert (
            _count(
                "SELECT COUNT(*) FROM crm_opportunity WHERE opportunity_public_id = :id",
                {"id": run_b_opportunity_public_id},
            )
            == 0
        ), "run B's own Opportunity should still have been removed"
    finally:
        cleanup_manifest(run_a)


def test_cleanup_raises_when_a_storage_key_is_invalid_rather_than_calling_it_deleted() -> None:
    """The third review pointed a document row at an invalid key backed by a real file. Cleanup
    exited successfully, reported the file deleted, and left it in place.

    The cause was an `exists()` pre-check reading False as "nothing here". The local provider
    catches StorageKeyError inside `exists` and returns False, but `delete` RAISES it - so the one
    method that can tell a refused key from an absent one was the one not being asked."""
    from uuid import uuid4

    from tooling.smoke_data.builders import generate_quote_document
    from tooling.smoke_data.cleanup import CleanupStorageError

    manifest = run_scenario("revision-requested")
    record = manifest["records"]["revision_requested"]
    quote = generate_quote_document(
        actor_public_id=manifest["actor"]["public_id"],
        offer_public_id=record["commercial_offer"]["public_id"],
    )

    # Repoint the stored document at a key the provider will refuse. The real file stays where it
    # is, and once the row is gone nothing references it - so this test has to remove it itself,
    # exactly the leak it is asserting cleanup now reports rather than hides.
    invalid_key = f"../../tmp/escaped-{uuid4().hex}.html"
    with SessionLocal() as db:
        real_key = db.execute(
            text("SELECT storage_key FROM document_metadata WHERE document_public_id = :d"),
            {"d": quote["document_public_id"]},
        ).scalar()
        db.execute(
            text("UPDATE document_metadata SET storage_key = :k WHERE document_public_id = :d"),
            {"k": invalid_key, "d": quote["document_public_id"]},
        )
        db.commit()

    try:
        with pytest.raises(CleanupStorageError) as raised:
            cleanup_manifest(manifest)
        assert invalid_key in str(raised.value), "the refused key must be named, or it is lost"
    finally:
        from app.modules.documents.storage import get_storage_provider_by_code

        get_storage_provider_by_code("local").delete(storage_key=real_key)


def test_cleanup_refuses_a_manifest_it_cannot_read_in_full() -> None:
    """A manifest with one good anchor and one damaged entry used to clean up its readable half
    and exit successfully. An incomplete cleanup reporting success is the failure this package
    exists to remove."""
    from tooling.smoke_data.cleanup import CleanupValidationError

    manifest = run_scenario("accepted-offer-no-work-order")
    try:
        damaged = {
            **manifest,
            "records": {
                **manifest["records"],
                "damaged": {"account": {"account_name": "no public_id here"}},
            },
        }
        with pytest.raises(CleanupValidationError, match="malformed"):
            cleanup_manifest(damaged)

        # Nothing may have been deleted by the refused attempt.
        assert _account_exists(manifest["records"]["handoff_target"]["account"]["public_id"])

        not_an_object = {**manifest, "records": {**manifest["records"], "damaged": "a string"}}
        with pytest.raises(CleanupValidationError):
            cleanup_manifest(not_an_object)
    finally:
        cleanup_manifest(manifest)


def test_status_counts_found_and_expected_against_the_same_record_set() -> None:
    """Reported as found=1, expected=2, all_present=False with both offers present. `found` was
    counted against the manifest's ids while `expected` used the post-closure set."""
    from decimal import Decimal

    from tooling.smoke_data.builders import add_offer_line, create_offer_no_line
    from tooling.smoke_data.status import check_manifest_status

    manifest = run_scenario("rejected-offer")
    record = manifest["records"]["rejected_offer"]
    try:
        live_offer = create_offer_no_line(
            run_id=manifest["run_id"],
            actor_public_id=manifest["actor"]["public_id"],
            opportunity_public_id=record["opportunity"]["public_id"],
            suffix="live",
            offer_title="Raised on a seeded enquiry after the manifest was written",
        )
        add_offer_line(
            actor_public_id=manifest["actor"]["public_id"],
            offer_public_id=live_offer["public_id"],
            quantity=Decimal("1"),
            rate_amount=Decimal("500.00"),
        )

        result = check_manifest_status(manifest)
        assert result["found"]["commercial_offers"] == result["expected"]["commercial_offers"] == 2
        assert result["all_present"] is True, "both offers exist, so the run is not incomplete"
    finally:
        cleanup_manifest(manifest)


def test_cleanup_removes_an_account_the_repair_flow_created_for_an_owned_opportunity() -> None:
    """Fourth review, P1. Discovery reached an Account created by LEAD CONVERSION but not one
    created by the Opportunity Account repair flow - the other route in this application that
    brings an Account into existence without anyone naming it. A probe deleted the owned
    Opportunity and left the Account, and its AccountCreated event, behind.

    This is the deliberate mirror of
    test_cleanup_does_not_delete_an_account_another_run_already_owned, and the two together draw
    the boundary: repairing onto an EXISTING Account gives us no claim on it; repairing by
    CREATING one does, because that Account had no prior existence and exists only because our
    Opportunity did. The repair's own business event records which of the two happened, so the
    distinction is drawn from provenance rather than from the Opportunity to Account edge the
    third review had to remove as unsafe."""
    from app.modules.opportunities import service as opportunities_service
    from app.modules.opportunities.schemas import (
        OpportunityAccountCreateRepair,
        OpportunityAccountRepairRequest,
        OpportunityCreate,
    )
    from tooling.smoke_data.actors import resolve_actor

    with SessionLocal() as db:
        actor_public_id = resolve_actor(db)["public_id"]

    with SessionLocal() as db:
        created = opportunities_service.create_opportunity(
            db,
            payload=OpportunityCreate(
                opportunity_name="TE1-SMOKE-te1-4a4a4a4a Opportunity awaiting Account repair",
                opportunity_source="manual",
            ),
            current_user_public_id=actor_public_id,
        )
        opportunity_public_id = str(created.opportunity.public_id)

    with SessionLocal() as db:
        repaired = opportunities_service.repair_opportunity_account(
            db,
            public_id=UUID(opportunity_public_id),
            payload=OpportunityAccountRepairRequest(
                create_account=OpportunityAccountCreateRepair(
                    account_name="TE1-SMOKE-te1-4a4a4a4a Account created by repair",
                )
            ),
            current_user_public_id=actor_public_id,
        )
        created_account_public_id = str(repaired.account.public_id)

    assert _account_exists(created_account_public_id), "the repair must have created an Account"
    assert (
        _count(
            "SELECT COUNT(*) FROM business_event WHERE record_public_id = :id",
            {"id": created_account_public_id},
        )
        > 0
    ), "the created Account must have written an event, or this test proves nothing"

    # The manifest names the Opportunity and nothing else. Nobody asked for the Account by name,
    # which is exactly the case that escaped.
    manifest = {
        "manifest_version": 1,
        "run_id": "te1-4a4a4a4a",
        "scenario": "repair-created-account",
        "created_at": "2026-09-10T00:00:00Z",
        "records": {
            "only_an_opportunity": {
                "opportunity": {
                    "public_id": opportunity_public_id,
                    "opportunity_name": "Opportunity awaiting Account repair",
                }
            }
        },
    }
    try:
        cleanup_manifest(manifest)

        assert not _account_exists(created_account_public_id), (
            "an Account the repair flow created for our own Opportunity survived cleanup"
        )
        assert (
            _count(
                "SELECT COUNT(*) FROM business_event WHERE record_public_id = :id",
                {"id": created_account_public_id},
            )
            == 0
        ), "the created Account's audit row survived its subject"
    finally:
        # Belt and braces: if an assertion above fails, do not leave rows in a shared development
        # database for the next test to trip over.
        with SessionLocal() as db:
            db.execute(
                text("DELETE FROM business_event WHERE record_public_id IN (:a, :o)"),
                {"a": created_account_public_id, "o": opportunity_public_id},
            )
            db.execute(
                text("DELETE FROM crm_opportunity WHERE opportunity_public_id = :o"),
                {"o": opportunity_public_id},
            )
            db.execute(
                text("DELETE FROM business_party WHERE business_party_public_id = :a"),
                {"a": created_account_public_id},
            )
            db.commit()


@pytest.mark.parametrize(
    ("collection_key", "damaged_entry"),
    [
        ("work_orders", {"work_order_code": "WO-000001"}),
        ("related_offers", "not-an-object-at-all"),
        ("activities", {"activity_type": "CALL"}),
    ],
)
def test_cleanup_refuses_a_manifest_whose_collections_it_cannot_read_in_full(
    collection_key: str, damaged_entry: object
) -> None:
    """Fourth review, P2. The third review's fix refused a malformed SINGULAR anchor but left the
    three collections - work_orders, related_offers, activities - silently skipping any entry
    that was not a dict or carried no public_id. A manifest pairing a good Account with damaged
    collection entries was accepted and quietly reduced to just the Account, which is the same
    partial-cleanup-reported-as-success that the singular check exists to prevent."""
    manifest = {
        "manifest_version": 1,
        "run_id": "te1-4c4c4c4c",
        "scenario": "damaged-collection",
        "created_at": "2026-09-10T00:00:00Z",
        "records": {
            "readable_half": {
                "account": {"public_id": str(uuid4()), "account_name": "Readable"},
                collection_key: [damaged_entry],
            }
        },
    }
    with pytest.raises(CleanupValidationError) as raised:
        cleanup_manifest(manifest)
    assert collection_key in str(raised.value)


def test_every_resolvable_storage_provider_conforms_to_the_delete_contract() -> None:
    """Fourth review, P2. Cleanup's storage step trusts `exists()` to answer truthfully: a
    provider returning False both before and after a deletion that did nothing yields a clean
    result with the file still in place. That is a contract violation rather than a cleanup bug,
    and nothing verified the contract - so it was an assertion, not a control.

    Providers are discovered from the STORAGE_PROVIDER_* constants in documents/contract.py,
    which is what get_storage_provider_by_code dispatches on, so a provider added later cannot
    quietly skip this.

    Note the one thing this cannot do: its own cleanup goes through `delete`, the method under
    test, so a provider that genuinely fails here leaks the object this test stored. That is
    accepted rather than worked around - reaching past the interface to tidy up would mean knowing
    a provider's storage, which is the coupling the interface exists to prevent - but it does mean
    a failure here leaves one small object behind alongside the report."""
    import io

    from app.modules.documents import contract as documents_contract
    from app.modules.documents.storage import get_storage_provider_by_code
    from app.modules.documents.storage.base import StorageKeyError

    provider_codes = sorted(
        value
        for name, value in vars(documents_contract).items()
        if name.startswith("STORAGE_PROVIDER_") and isinstance(value, str)
    )
    assert provider_codes, "no storage providers were discovered; this test would prove nothing"

    for provider_code in provider_codes:
        provider = get_storage_provider_by_code(provider_code)
        storage_key = f"te1-conformance/{uuid4().hex}.bin"
        try:
            provider.save(
                storage_key=storage_key,
                stream=io.BytesIO(b"conformance"),
                content_type="application/octet-stream",
            )
            assert provider.exists(storage_key=storage_key) is True, (
                f"{provider_code}: exists() denied an object it had just stored"
            )

            provider.delete(storage_key=storage_key)
            assert provider.exists(storage_key=storage_key) is False, (
                f"{provider_code}: exists() still reports an object after delete() removed it - "
                "cleanup would count the file deleted while leaking it"
            )

            # Deleting what is already gone is a no-op, not an error: cleanup calls delete
            # unconditionally, so a provider raising here would turn ordinary rows into reported
            # leaks.
            provider.delete(storage_key=storage_key)

            # A key that escapes the root must raise from delete(), because that exception is the
            # ONLY signal separating a refused deletion from a successful one - exists()
            # deliberately answers False for both.
            with pytest.raises(StorageKeyError):
                provider.delete(storage_key="../escaping-key.bin")
        finally:
            try:
                provider.delete(storage_key=storage_key)
            except StorageKeyError:
                pass


def test_status_reports_a_malformed_manifest_as_malformed_not_as_a_database_error(
    tmp_path, capsys
) -> None:
    """Fourth review, P3. _collect_ids raises CleanupValidationError, which _cmd_status did not
    catch - so a manifest carrying an id that is not a UUID was reported as a database error. The
    exit code was safe; the operator's diagnosis was not, and would send them to look at
    PostgreSQL for a fault in their own file."""
    from tooling.smoke_data.cli import main

    manifest_path = tmp_path / "damaged.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "run_id": "te1-4e4e4e4e",
                "scenario": "damaged",
                "created_at": "2026-09-10T00:00:00Z",
                "records": {"r": {"account": {"public_id": "definitely-not-a-uuid"}}},
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["status", "--manifest", str(manifest_path)])

    assert exit_code == 1
    stderr = capsys.readouterr().err
    assert "malformed or unsafe" in stderr
    assert "database error" not in stderr


def test_status_can_require_anchors_to_be_present() -> None:
    """Fifth review, P2. `status` exits 0 both when every anchor is present and when every anchor
    is gone - two opposite states, one code. scripts/vendor-demo.ps1 reads any zero as a
    successful preflight, so a run whose data had been cleaned up outside the wrapper passed
    preflight with nothing to demonstrate.

    --require-present makes the caller say which state it is asking about, rather than leaving the
    exit code to mean whichever one the reader had in mind."""
    from tooling.smoke_data.cli import main
    from tooling.smoke_data.store import save_manifest

    manifest = run_scenario("rejected-offer")
    save_manifest(manifest)
    run_id = manifest["run_id"]
    try:
        assert main(["status", "--run-id", run_id]) == 0
        assert main(["status", "--run-id", run_id, "--require-present"]) == 0

        cleanup_manifest(manifest)

        # Cleaned up: still a successful *reset*, so the plain form stays 0 ...
        assert main(["status", "--run-id", run_id]) == 0
        # ... but a caller that needs the data there is now told it is not.
        assert main(["status", "--run-id", run_id, "--require-present"]) != 0
    finally:
        cleanup_manifest(manifest)


def test_a_failing_exists_probe_does_not_prevent_the_delete() -> None:
    """`exists` is a counter, not a gate. A provider whose probe raises but whose delete works must
    still have its object removed."""
    import tooling.smoke_data.cleanup as cleanup_module
    from tooling.smoke_data.builders import generate_quote_document

    manifest = run_scenario("revision-requested")
    record = manifest["records"]["revision_requested"]
    quote = generate_quote_document(
        actor_public_id=manifest["actor"]["public_id"],
        offer_public_id=record["commercial_offer"]["public_id"],
    )
    with SessionLocal() as db:
        key = db.execute(
            text("SELECT storage_key FROM document_metadata WHERE document_public_id = :d"),
            {"d": quote["document_public_id"]},
        ).scalar()

    real_resolver = cleanup_module.get_storage_provider_by_code

    class _BlindProbe:
        """Cannot answer `exists`, but deletes perfectly well."""

        def __init__(self, wrapped):
            self._wrapped = wrapped
            self._probes = 0

        def exists(self, *, storage_key: str) -> bool:
            self._probes += 1
            if self._probes == 1:
                raise RuntimeError("probe unavailable")
            return self._wrapped.exists(storage_key=storage_key)

        def delete(self, *, storage_key: str) -> None:
            self._wrapped.delete(storage_key=storage_key)

    cleanup_module.get_storage_provider_by_code = lambda code: _BlindProbe(real_resolver(code))
    try:
        cleanup_manifest(manifest)
    finally:
        cleanup_module.get_storage_provider_by_code = real_resolver

    assert not real_resolver("local").exists(storage_key=key), (
        "a failing exists() probe skipped the delete and leaked the object"
    )


def test_audit_deletion_does_not_touch_another_record_types_event() -> None:
    """Ids are not unique across record types. Matching on the id alone deleted an unrelated
    event that happened to share an owned Account's id."""
    manifest = run_scenario("accepted-offer-no-work-order")
    bystander = str(uuid4())
    try:
        # Setup lives INSIDE the try: seeding before it meant a setup failure leaked the whole
        # scenario, which happened three times during this package's development.
        account_public_id = manifest["records"]["handoff_target"]["account"]["public_id"]
        with SessionLocal() as db:
            db.execute(
                text(
                    "INSERT INTO business_event "
                    "(public_id, event_name, source_module, record_type, record_public_id) "
                    "VALUES (:p, 'UnrelatedThing', 'somewhere_else', 'equipment', :r)"
                ),
                {"p": bystander, "r": account_public_id},
            )
            db.commit()

        cleanup_manifest(manifest)
        assert (
            _count("SELECT COUNT(*) FROM business_event WHERE public_id = :p", {"p": bystander}) == 1
        ), "cleanup deleted another record type's event that merely shared an id"
        assert (
            _count(
                "SELECT COUNT(*) FROM business_event WHERE record_public_id = :r "
                "AND record_type IN ('business_party', 'account')",
                {"r": account_public_id},
            )
            == 0
        ), "the run's own Account events should still be gone"

        # And status must agree. Checking only that cleanup behaved correctly missed the two
        # disagreeing about what residue is: status counted the surviving bystander as this run's
        # leftover because it matched on the id alone (independent review, seventh pass).
        from tooling.smoke_data.status import check_manifest_status

        result = check_manifest_status(manifest)
        assert result["residue"]["business_events"] == 0, (
            "status counted another record type's event as this run's residue"
        )
        assert result["residue_clear"] is True
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM business_event WHERE public_id = :p"), {"p": bystander})
            db.commit()


def test_status_refuses_a_manifest_that_names_nothing() -> None:
    """Cleanup refuses it; status reported every category 0/0 and called that success."""
    from tooling.smoke_data.status import check_manifest_status

    manifest = {
        "manifest_version": 1,
        "run_id": "te1-7a7a7a7a",
        "scenario": "names-nothing",
        "created_at": "2026-09-10T00:00:00Z",
        "records": {"nothing": {}},
    }
    with pytest.raises(CleanupValidationError):
        check_manifest_status(manifest)


def test_a_storage_failure_still_names_its_keys_and_fails_loudly() -> None:
    """The keys are not persisted, so this message is the only record of them - which is exactly
    what the E2E and runbook recovery instructions say."""
    import tooling.smoke_data.cleanup as cleanup_module
    from tooling.smoke_data.builders import generate_quote_document
    from tooling.smoke_data.cleanup import CleanupStorageError

    manifest = run_scenario("revision-requested")
    record = manifest["records"]["revision_requested"]
    quote = generate_quote_document(
        actor_public_id=manifest["actor"]["public_id"],
        offer_public_id=record["commercial_offer"]["public_id"],
    )
    with SessionLocal() as db:
        key = db.execute(
            text("SELECT storage_key FROM document_metadata WHERE document_public_id = :d"),
            {"d": quote["document_public_id"]},
        ).scalar()

    real_resolver = cleanup_module.get_storage_provider_by_code

    class _Refusing:
        def exists(self, *, storage_key: str) -> bool:
            return True

        def delete(self, *, storage_key: str) -> None:
            return None

    cleanup_module.get_storage_provider_by_code = lambda code: _Refusing()
    try:
        with pytest.raises(CleanupStorageError) as raised:
            cleanup_manifest(manifest)
        assert key in str(raised.value), "the key must be named, or it is lost"
    finally:
        cleanup_module.get_storage_provider_by_code = real_resolver
        real_resolver("local").delete(storage_key=key)


def test_audit_deletion_does_not_confuse_two_account_sub_record_types() -> None:
    """Address, GSTIN, tax-profile and contact ids were once pooled into one group and then paired
    with all four record types, which reproduced type-blind matching inside the fix for it. An
    unrelated GSTIN event sharing an owned address's id was deleted."""
    from tooling.smoke_data.builders import add_account_address

    manifest = run_scenario("accepted-offer-no-work-order")
    bystander = str(uuid4())
    try:
        # Setup inside the try, for the reason given in the sibling test above.
        address = add_account_address(
            actor_public_id=manifest["actor"]["public_id"],
            account_public_id=manifest["records"]["handoff_target"]["account"]["public_id"],
            address_type_code="COMMUNICATION",
            address_line1="1 Collision Test Road",
            city="Visakhapatnam",
            state="Andhra Pradesh",
        )
        with SessionLocal() as db:
            db.execute(
                text(
                    "INSERT INTO business_event "
                    "(public_id, event_name, source_module, record_type, record_public_id) "
                    "VALUES (:p, 'UnrelatedGstinThing', 'accounts', 'business_party_gstin', :r)"
                ),
                {"p": bystander, "r": address["public_id"]},
            )
            db.commit()

        cleanup_manifest(manifest)
        assert (
            _count("SELECT COUNT(*) FROM business_event WHERE public_id = :p", {"p": bystander}) == 1
        ), "an address id was matched against the GSTIN record type"
        assert (
            _count(
                "SELECT COUNT(*) FROM business_event WHERE record_public_id = :r "
                "AND record_type = 'business_party_address'",
                {"r": address["public_id"]},
            )
            == 0
        ), "the address's own audit row should be gone"
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM business_event WHERE public_id = :p"), {"p": bystander})
            db.commit()
        cleanup_manifest(manifest)  # idempotent; guarantees the scenario is gone either way


def test_a_manifest_naming_only_activities_deletes_them_and_is_refused_by_status() -> None:
    """Activity ids counted toward cleanup's "names something" guard, but activities were deleted
    only through their lead - so an activity-only manifest passed the guard, removed the activity's
    AUDIT EVENT, left the row, and reported success. Status then called zero anchors out of zero
    "all present"."""
    from tooling.smoke_data.actors import resolve_actor
    from tooling.smoke_data.builders import add_lead_activity, create_lead
    from tooling.smoke_data.status import check_manifest_status

    with SessionLocal() as db:
        actor = resolve_actor(db)["public_id"]
    lead = create_lead(run_id="te1-7d7d7d7d", actor_public_id=actor, suffix="activity-only")
    lead_manifest = {
        "manifest_version": 1,
        "run_id": "te1-7d7d7d7d",
        "scenario": "activity-only",
        "created_at": "2026-09-10T00:00:00Z",
        "records": {"r": {"lead": lead}},
    }
    try:
        activity = add_lead_activity(actor_public_id=actor, lead_public_id=lead["public_id"])
        activity_only = {
            **lead_manifest,
            "records": {"r": {"activities": [activity]}},
        }

        # Status must refuse it: its expected/found cover the five anchor groups only, so an
        # activity-only manifest would otherwise report 0/0 and call that "all present".
        with pytest.raises(CleanupValidationError):
            check_manifest_status(activity_only)

        cleanup_manifest(activity_only)
        assert (
            _count(
                "SELECT COUNT(*) FROM crm_lead_activity WHERE activity_public_id = :a",
                {"a": activity["public_id"]},
            )
            == 0
        ), "the activity named in the manifest was not deleted"
        assert (
            _count(
                "SELECT COUNT(*) FROM business_event WHERE record_public_id = :a",
                {"a": activity["public_id"]},
            )
            == 0
        )
    finally:
        cleanup_manifest(lead_manifest)


def test_the_holiday_calendar_scenario_seeds_its_screen_check_with_no_calendar() -> None:
    """HOL-1: the screen-check Work Order - contract 1 December 2026 to 30 November 2027, lines in Gujarat and
    Maharashtra and one with no site - with its holidays unanswered, and no calendar year started by the run: the
    tester sets up 2027. Cleanup removes what the tester adds to the Work Order, as for Part 4."""
    from app.modules.work_orders import service as work_orders_service
    from tooling.smoke_data.builders import set_work_order_holidays

    manifest = run_scenario("holiday-calendar")
    demo = manifest["records"]["holiday_target"]["holiday_demo"]
    try:
        assert "holiday_calendar_years" not in manifest["records"]["holiday_target"]
        with SessionLocal() as db:
            resulting = work_orders_service.get_work_order_resulting_holidays(db, UUID(demo["work_order_public_id"]))
        assert (str(resulting.period_from), str(resulting.period_to)) == ("2026-12-01", "2027-11-30")
        assert [(group.state_code, group.problem_code, group.line_numbers) for group in resulting.groups] == [
            ("IN-GJ", None, [1]),
            ("IN-MH", None, [2]),
            (None, "SITE_NOT_RECORDED", [3]),
        ]
        assert resulting.holidays_answer_code is None
        set_work_order_holidays(
            actor_public_id=manifest["actor"]["public_id"],
            work_order_public_id=demo["work_order_public_id"],
            holidays_answer_code="CALENDAR_CHANGED",
            working_days=[("2027-03-22", "OVERTIME_RATE", None)],
        )
    finally:
        counts = cleanup_manifest(manifest)
    assert counts["work_order_holidays"] == 1 and counts["work_orders"] == 1
    assert counts["holiday_calendar_years"] == 0


def test_the_core_bundles_calendar_year_is_the_runs_and_cleanup_removes_it_whoever_changed_it() -> None:
    """HOL-1: the core bundle starts a year of PBL's calendar in the harness's own years (2095 to 2099) - never one
    anyone keeps - and a Work Order over it. The year is the run's by provenance, so cleanup removes it with its
    holidays and their states even after someone else saved a new version of it, as the Playwright test does."""
    from app.modules.holiday_calendar import service as calendar_service
    from app.modules.holiday_calendar.schemas import HolidayCalendarYearInput

    manifest = run_scenario("core-regression-bundle")
    try:
        record = manifest["records"]["holiday_calendar_target"]
        year = record["holiday_calendar_years"][0]
        assert 2095 <= year["calendar_year"] <= 2099 and year["year_version"] == 1
        assert record["holiday_demo"]["calendar_year"] == year["calendar_year"]
        with SessionLocal() as db:
            current = calendar_service.get_year(db, year["calendar_year"])
            assert [holiday.holiday_name for holiday in current.holidays] == ["Republic Day", "Holi", "Gujarat Day", "Maharashtra Day"]
            calendar_service.save_year(
                db,
                calendar_year=year["calendar_year"],
                payload=HolidayCalendarYearInput(expected_version=1, is_complete=True, holidays=[]),
                user_public_id=manifest["actor"]["public_id"],
            )
    finally:
        counts = cleanup_manifest(manifest)
    assert counts["holiday_calendar_years"] == 1
    assert _count("SELECT COUNT(*) FROM holiday_calendar_year WHERE year_public_id = :id", {"id": year["public_id"]}) == 0
    assert _count(
        "SELECT COUNT(*) FROM business_event WHERE record_type = 'holiday_calendar_year' AND record_public_id = :id",
        {"id": year["public_id"]},
    ) == 0
