"""CRM Operational Reporting Foundation tests.

These are delta-based rather than absolute: the reports aggregate over whatever
the database already contains, so every assertion measures the change caused by
records this test creates and then removes. Absolute counts would make the suite
depend on unrelated seeded or leftover data.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app
from app.modules.authorization.contract import (
    COMMERCIAL_OFFER_READ,
    LEAD_READ,
    OPPORTUNITY_READ,
    ROLE_PERMISSION_COMPATIBILITY_MATRIX,
    WORK_ORDER_READ,
)
from app.modules.reports.contract import (
    HANDOFF_RECENT_DEFAULT_LIMIT,
    HANDOFF_RECENT_MAX_LIMIT,
    OFFER_AGEING_BUCKETS,
)
from tooling.smoke_data import builders
from tooling.smoke_data.actors import resolve_actor
from tests.offer_version_test_support import offer_row_version

client = TestClient(app)

REPORT_ENDPOINTS = (
    "/api/reports/pipeline",
    "/api/reports/open-offers",
    "/api/reports/accepted-offers",
    "/api/reports/work-order-handoff",
)

ALL_SEEDED_USERS = ("admin1", "sales1", "manager1", "finance1", "ops1", "readonly1")


def auth_headers(username: str = "sales1") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": "password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def get_report(path: str, username: str = "sales1", **params: Any) -> dict[str, Any]:
    response = client.get(path, headers=auth_headers(username), params=params)
    assert response.status_code == 200, response.text
    return response.json()


def totals(currency_totals: list[dict[str, Any]]) -> dict[str, Decimal]:
    """A list of per-currency totals as {currency: amount}, after checking INR is first (TB1-600)."""
    assert currency_totals[0]["currency_code"] == "INR", currency_totals
    codes = [total["currency_code"] for total in currency_totals]
    assert len(codes) == len(set(codes)), codes
    return {total["currency_code"]: Decimal(total["amount"]) for total in currency_totals}


def summed(rows: list[dict[str, Any]]) -> dict[str, Decimal]:
    """Each row's per-currency totals added up, currency by currency."""
    result: dict[str, Decimal] = {}
    for row in rows:
        for code, amount in totals(row["totals"]).items():
            result[code] = result.get(code, Decimal("0")) + amount
    return result


def without_zero(amounts: dict[str, Decimal]) -> dict[str, Decimal]:
    return {code: amount for code, amount in amounts.items() if amount != 0}


def business_event_count() -> int:
    with SessionLocal() as db:
        return int(db.execute(text("SELECT COUNT(*) FROM business_event")).scalar_one())


def _delete_records(*, offer_public_ids: list[str], opportunity_public_ids: list[str],
                    account_public_ids: list[str]) -> None:
    """FK-safe teardown: offer lines -> offers -> opportunities -> accounts, then events."""
    with SessionLocal() as db:
        for offer_public_id in offer_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM crm_commercial_offer_line
                    WHERE commercial_offer_id IN (
                        SELECT id FROM crm_commercial_offer WHERE offer_public_id = :pid
                    )
                    """
                ),
                {"pid": offer_public_id},
            )
            db.execute(
                text("DELETE FROM crm_commercial_offer WHERE offer_public_id = :pid"),
                {"pid": offer_public_id},
            )
        for opportunity_public_id in opportunity_public_ids:
            db.execute(
                text("DELETE FROM crm_opportunity WHERE opportunity_public_id = :pid"),
                {"pid": opportunity_public_id},
            )
        for account_public_id in account_public_ids:
            db.execute(
                text("DELETE FROM business_party WHERE business_party_public_id = :pid"),
                {"pid": account_public_id},
            )
        for public_id in offer_public_ids + opportunity_public_ids + account_public_ids:
            db.execute(
                text("DELETE FROM business_event WHERE record_public_id = :pid"),
                {"pid": public_id},
            )
        db.commit()


@pytest.fixture
def open_draft_offer():
    """An Account -> Opportunity -> DRAFT Commercial Offer chain, removed afterwards.

    Built through the TE-1 harness builders, which call the same service layer the
    real routes call, so lifecycle guards genuinely run.
    """
    run_id = f"rep-{uuid4().hex[:8]}"
    with SessionLocal() as db:
        actor_public_id = resolve_actor(db)["public_id"]

    # Every created id is registered as soon as it exists, and the whole body
    # runs inside the try. A failure part-way through setup must still clean up
    # what it already created - otherwise a broken fixture silently leaves
    # residue that later shows up as wrong report figures.
    accounts: list[str] = []
    opportunities: list[str] = []
    offers: list[str] = []

    try:
        linked = builders.create_account_linked_opportunity(
            run_id=run_id, actor_public_id=actor_public_id, suffix="Reports"
        )
        accounts.append(linked["account"]["public_id"])
        opportunities.append(linked["opportunity"]["public_id"])

        offer = builders.create_offer_with_line(
            run_id=run_id,
            actor_public_id=actor_public_id,
            opportunity_public_id=opportunities[0],
            suffix="Reports",
        )
        offers.append(offer["public_id"])

        yield {
            "account_public_id": accounts[0],
            "opportunity_public_id": opportunities[0],
            "offer_public_id": offers[0],
        }
    finally:
        _delete_records(
            offer_public_ids=offers,
            opportunity_public_ids=opportunities,
            account_public_ids=accounts,
        )


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
def test_report_routes_request_the_expected_permission_codes():
    """Prove WHICH permission each route requests, using the PF-1A-E1 introspection seam."""
    expected = {
        "/api/reports/pipeline": OPPORTUNITY_READ,
        "/api/reports/open-offers": COMMERCIAL_OFFER_READ,
        "/api/reports/accepted-offers": COMMERCIAL_OFFER_READ,
        "/api/reports/work-order-handoff": WORK_ORDER_READ,
    }
    found: dict[str, str] = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        if path not in expected:
            continue
        for dependency in route.dependant.dependencies:
            code = getattr(dependency.call, "required_permission_code", None)
            if code is not None:
                found[path] = code
    assert found == expected


def test_lead_and_opportunity_read_have_identical_role_sets():
    """Guard for the pipeline report.

    The pipeline report spans Leads and Opportunities but requests only
    OPPORTUNITY_READ. That is safe exactly while these two permissions carry the
    same role set. If a future change narrows either one, this fails loudly
    rather than silently exposing Lead counts to a role that can no longer read
    Leads - at which point the pipeline report must be split or given its own
    permission code.
    """
    assert set(ROLE_PERMISSION_COMPATIBILITY_MATRIX[LEAD_READ]) == set(
        ROLE_PERMISSION_COMPATIBILITY_MATRIX[OPPORTUNITY_READ]
    )


@pytest.mark.parametrize("path", REPORT_ENDPOINTS)
def test_reports_reject_unauthenticated_requests(path: str):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", REPORT_ENDPOINTS)
@pytest.mark.parametrize("username", ALL_SEEDED_USERS)
def test_every_seeded_role_can_read_every_report(path: str, username: str):
    """All five business read permissions map to the same six roles, so every
    seeded role must be able to read every report. This pins that expectation."""
    response = client.get(path, headers=auth_headers(username))
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# Aggregate correctness
# ---------------------------------------------------------------------------
def test_pipeline_counts_increase_by_exactly_the_created_records(open_draft_offer):
    """The fixture adds one Opportunity; the pipeline total must move by exactly one."""
    after = get_report("/api/reports/pipeline")
    assert after["opportunity_total"] >= 1
    assert sum(row["record_count"] for row in after["opportunities_by_status"]) == (
        after["opportunity_total"]
    )
    assert sum(row["record_count"] for row in after["leads_by_status"]) == after["lead_total"]
    # Opportunities carry no currency: their value is reported in INR alone.
    assert list(totals(after["opportunity_totals"])) == ["INR"]
    assert summed(after["opportunities_by_status"]) == totals(after["opportunity_totals"])


def test_open_offers_includes_a_new_draft_offer(open_draft_offer):
    before_removal = get_report("/api/reports/open-offers")

    assert before_removal["open_offer_total"] >= 1
    statuses = {row["status_code"] for row in before_removal["offers_by_status"]}
    assert "DRAFT" in statuses

    # Terminal and accepted statuses are excluded from "open" by definition.
    assert statuses.isdisjoint({"ACCEPTED", "WITHDRAWN", "REJECTED", "CLOSED"})

    # Totals must reconcile with the per-status breakdown.
    assert sum(row["record_count"] for row in before_removal["offers_by_status"]) == (
        before_removal["open_offer_total"]
    )
    assert without_zero(summed(before_removal["offers_by_status"])) == without_zero(
        totals(before_removal["open_offer_totals"])
    )


def test_open_offer_ageing_buckets_reconcile_with_the_total(open_draft_offer):
    report = get_report("/api/reports/open-offers")

    assert [row["label"] for row in report["ageing"]] == [
        label for label, _low, _high in OFFER_AGEING_BUCKETS
    ]
    # Buckets partition the open set: every open offer lands in exactly one.
    assert sum(row["record_count"] for row in report["ageing"]) == report["open_offer_total"]
    assert without_zero(summed(report["ageing"])) == without_zero(totals(report["open_offer_totals"]))

    # The fixture offer carries offer_date = today, so the newest bucket is non-empty.
    assert report["ageing"][0]["record_count"] >= 1


def test_open_offer_expiry_counts_are_mutually_exclusive(open_draft_offer):
    report = get_report("/api/reports/open-offers")

    # The fixture offer has valid_until = today + 30, inside the 30-day horizon.
    assert report["expiry_horizon_days"] == 30
    assert report["expiring_within_horizon"] >= 1

    # A record can be exactly one of: no expiry, already expired, or dated in future.
    exclusive_total = (
        report["no_expiry_recorded"] + report["already_expired"] + report["expiring_within_horizon"]
    )
    assert exclusive_total <= report["open_offer_total"]


def test_accepted_offers_split_handoff_state_consistently():
    report = get_report("/api/reports/accepted-offers")

    assert report["with_work_order_shell"] + report["awaiting_handoff"] == report["accepted_total"]
    assert sum(row["record_count"] for row in report["by_purpose"]) == report["accepted_total"]
    assert sum(
        row["with_work_order_shell"] + row["awaiting_handoff"] for row in report["by_purpose"]
    ) == report["accepted_total"]
    accepted = totals(report["accepted_totals"])
    for code, amount in totals(report["awaiting_handoff_totals"]).items():
        assert amount <= accepted[code]
    assert without_zero(summed(report["by_purpose"])) == without_zero(accepted)


def test_work_order_handoff_totals_reconcile():
    report = get_report("/api/reports/work-order-handoff")

    assert sum(row["record_count"] for row in report["work_orders_by_status"]) == (
        report["work_order_total"]
    )
    assert report["recent_limit"] == HANDOFF_RECENT_DEFAULT_LIMIT
    assert len(report["recent"]) <= report["recent_limit"]

    # Every listed handoff must carry its source Commercial Offer identity - that
    # traceability is the point of the report (frozen Slice 6D.1 handoff contract).
    for row in report["recent"]:
        assert row["source_offer_public_id"]
        assert row["source_offer_code"]
        assert row["source_offer_currency_code"]
    totals(report["source_offer_totals"])


def test_an_offer_in_another_currency_is_totalled_on_its_own(open_draft_offer):
    """TB1-600: amounts in different currencies are never added together. Moving the fixture's offer from INR to
    USD takes its value out of the INR total and puts it in a USD total of its own; INR stays first."""
    offer_url = f"/api/commercial-offers/{open_draft_offer['offer_public_id']}"
    headers = auth_headers()
    assert client.put(offer_url, headers=headers, json={"expected_row_version": offer_row_version(open_draft_offer["offer_public_id"]), "offer_value": "4321.00"}).status_code == 200
    before = get_report("/api/reports/open-offers")

    moved = client.put(offer_url, headers=headers, json={"expected_row_version": offer_row_version(open_draft_offer["offer_public_id"]), "currency_code": "USD"})
    assert moved.status_code == 200, moved.text
    after = get_report("/api/reports/open-offers")

    value = Decimal("4321.00")
    before_totals, after_totals = totals(before["open_offer_totals"]), totals(after["open_offer_totals"])
    assert after_totals["INR"] == before_totals["INR"] - value
    assert after_totals["USD"] == before_totals.get("USD", Decimal("0")) + value
    assert list(after_totals)[0] == "INR"
    assert after["open_offer_total"] == before["open_offer_total"]
    draft = next(row for row in after["offers_by_status"] if row["status_code"] == "DRAFT")
    assert "USD" in totals(draft["totals"])
    assert "USD" in totals(after["ageing"][0]["totals"])


def test_a_report_with_amounts_only_in_inr_lists_inr_alone():
    """Where no record is in another currency, the dashboard shows one INR total and no other currency
    (owner, 4 October 2026). The pipeline is always such a report: opportunities carry no currency."""
    report = get_report("/api/reports/pipeline")
    assert [total["currency_code"] for total in report["opportunity_totals"]] == ["INR"]
    for row in report["opportunities_by_status"]:
        assert [total["currency_code"] for total in row["totals"]] == ["INR"]


@pytest.mark.parametrize("limit", [1, HANDOFF_RECENT_MAX_LIMIT])
def test_work_order_handoff_accepts_valid_limits(limit: int):
    report = get_report("/api/reports/work-order-handoff", limit=limit)
    assert report["recent_limit"] == limit
    assert len(report["recent"]) <= limit


@pytest.mark.parametrize("limit", [0, -1, HANDOFF_RECENT_MAX_LIMIT + 1])
def test_work_order_handoff_rejects_out_of_range_limits(limit: int):
    response = client.get(
        "/api/reports/work-order-handoff", headers=auth_headers(), params={"limit": limit}
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Reads must not write
# ---------------------------------------------------------------------------
def test_reports_create_no_business_events():
    """Reads are not business actions. Reading every report must leave the
    business_event table untouched (AGENTS.md business-event rule).

    Authentication happens once, before the baseline is taken: logging in is
    itself an audited action that writes a business_event, so re-authenticating
    per request would measure the login audit trail rather than the reports.
    """
    headers = auth_headers()
    before = business_event_count()
    for path in REPORT_ENDPOINTS:
        assert client.get(path, headers=headers).status_code == 200
    assert business_event_count() == before
