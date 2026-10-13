"""Slice 9F: immutable Commercial Offer versions."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app
from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_CODE_VERSION_INDEX,
    COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES,
    COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX,
    COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES,
)
from app.modules.commercial_offers.repository import insert_commercial_offer_revision
from app.modules.commercial_offers.schemas import CommercialOfferVersionCreate
from app.modules.commercial_offers.service import create_commercial_offer_version
from app.modules.commercial_offers.services.common import CommercialOfferValidationError
from app.modules.documents.storage import get_storage_provider_by_code
from tests.offer_version_test_support import offer_row_version
from tests.test_commercial_offers_api import (
    auth_headers,
    cleanup_test_work_orders,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    get_seeded_tc_clause_public_id,
    record_test_customer_response,
)
from tooling.smoke_data.actors import resolve_actor


client = TestClient(app)


class _Records:
    def __init__(self) -> None:
        self.offers: list[str] = []
        self.opportunities: list[str] = []
        self.accounts: list[str] = []
        self.leads: list[str] = []

    def clean(self) -> None:
        for public_id in reversed(self.offers):
            with SessionLocal() as db:
                stored_objects = db.execute(
                    text(
                        "SELECT storage_provider_code, storage_key FROM document_metadata "
                        "WHERE linked_record_type = 'commercial_offer' "
                        "AND linked_record_public_id = :public_id AND storage_key IS NOT NULL"
                    ),
                    {"public_id": public_id},
                ).fetchall()
            for provider_code, storage_key in stored_objects:
                try:
                    get_storage_provider_by_code(provider_code).delete(storage_key=storage_key)
                except Exception:
                    pass

        with SessionLocal() as db:
            for public_id in reversed(self.offers):
                db.execute(
                    text(
                        "DELETE FROM document_metadata WHERE linked_record_type = 'commercial_offer' "
                        "AND linked_record_public_id = :public_id"
                    ),
                    {"public_id": public_id},
                )
                db.execute(
                    text(
                        "DELETE FROM crm_commercial_offer_line_basis_choice WHERE commercial_offer_line_id IN "
                        "(SELECT line.id FROM crm_commercial_offer_line line JOIN crm_commercial_offer co "
                        "ON co.id = line.commercial_offer_id WHERE co.offer_public_id = :public_id)"
                    ),
                    {"public_id": public_id},
                )
                for table in (
                    "commercial_offer_customer_response",
                    "commercial_offer_revision",
                    "commercial_offer_credit_review",
                    "commercial_offer_submission_evidence",
                    "commercial_offer_tc_clause",
                    "crm_commercial_offer_pricing_evidence",
                    "crm_commercial_offer_line",
                    "crm_commercial_offer_quote_document",
                ):
                    db.execute(
                        text(
                            f"DELETE FROM {table} WHERE commercial_offer_id IN "
                            "(SELECT id FROM crm_commercial_offer WHERE offer_public_id = :public_id)"
                        ),
                        {"public_id": public_id},
                    )
                db.execute(
                    text(
                        "DELETE FROM business_event WHERE record_type = 'commercial_offer' "
                        "AND record_public_id = :public_id"
                    ),
                    {"public_id": public_id},
                )
                db.execute(
                    text("DELETE FROM crm_commercial_offer WHERE offer_public_id = :public_id"),
                    {"public_id": public_id},
                )
            for public_id in self.opportunities:
                db.execute(
                    text("DELETE FROM business_event WHERE record_type = 'opportunity' AND record_public_id = :public_id"),
                    {"public_id": public_id},
                )
                db.execute(
                    text("DELETE FROM crm_opportunity WHERE opportunity_public_id = :public_id"),
                    {"public_id": public_id},
                )
            for public_id in self.accounts:
                db.execute(
                    text("DELETE FROM business_event WHERE record_type = 'business_party' AND record_public_id = :public_id"),
                    {"public_id": public_id},
                )
                db.execute(
                    text("DELETE FROM business_party WHERE business_party_public_id = :public_id"),
                    {"public_id": public_id},
                )
            for public_id in self.leads:
                db.execute(
                    text("DELETE FROM business_event WHERE record_type = 'lead' AND record_public_id = :public_id"),
                    {"public_id": public_id},
                )
                db.execute(text("DELETE FROM crm_lead WHERE lead_public_id = :public_id"), {"public_id": public_id})
            db.commit()


@pytest.fixture
def records():
    created = _Records()
    try:
        yield created
    finally:
        created.clean()


def _new_linked_offer(records: _Records) -> dict[str, object]:
    linked = create_account_linked_test_opportunity()
    records.leads.append(str(linked["lead"]["public_id"]))
    records.accounts.append(str(linked["account"]["public_id"]))
    opportunity_public_id = str(linked["opportunity"]["public_id"])
    records.opportunities.append(opportunity_public_id)
    offer = create_test_commercial_offer(opportunity_public_id)
    records.offers.append(str(offer["public_id"]))
    return offer


def _actor_public_id(username: str = "sales1") -> str:
    with SessionLocal() as db:
        return str(resolve_actor(db, username)["public_id"])


def _prepare_submitted_offer(records: _Records) -> dict[str, object]:
    offer = _new_linked_offer(records)
    public_id = str(offer["public_id"])
    base = f"/api/commercial-offers/{public_id}"

    line = client.post(
        f"{base}/lines",
        headers=auth_headers("sales1"),
        json={
            "scope_description": "80T crane with operator",
            "equipment_service_category": "Crane",
            "quantity": "2.00",
            "uom": "day",
            "rate_amount": "95000.00",
            "currency_code": "INR",
            "remarks": "Mobilisation excluded",
        },
    )
    assert line.status_code == 201, line.text

    pricing = client.post(
        f"{base}/pricing-evidence",
        headers=auth_headers("ops1"),
        json={
            "line_public_id": line.json()["offer_line"]["public_id"],
            "evidence_type": "market_rate",
            "source_name": "Slice 9F market source",
            "equipment_service_description": "80T crane with operator",
            "rate_amount": "90000.00",
            "currency_code": "INR",
            "rate_basis": "per_day",
            "is_selected_basis": True,
            "selection_reason": "Best available matching machine",
        },
    )
    assert pricing.status_code == 201, pricing.text

    clause = client.post(
        f"{base}/tc-clauses",
        headers=auth_headers("sales1"),
        json={"clause_public_ids": [get_seeded_tc_clause_public_id("TRANS-TC-001")]},
    )
    assert clause.status_code == 201, clause.text

    review = client.post(
        f"{base}/credit-review",
        headers=auth_headers("sales1"),
        json={
            "review_status": "WITHIN_LIMIT_AS_PER_MANUAL_REVIEW",
            "review_basis": "Current Account credit profile",
            "review_reference": f"SLICE-9F-{uuid4()}",
            "reviewed_at": "2026-10-10T09:00:00Z",
            "approved_amount_snapshot": "500000.00",
            "credit_days_snapshot": 30,
        },
    )
    assert review.status_code == 201, review.text

    evidence = client.post(
        f"{base}/submission-evidence",
        headers=auth_headers("sales1"),
        json={
            "submission_reference": f"SLICE-9F-SENT-{uuid4()}",
            "submission_channel": "EMAIL",
            "submitted_at": "2026-10-10T09:30:00Z",
        },
    )
    assert evidence.status_code == 201, evidence.text

    submitted = client.post(f"{base}/mark-submitted", headers=auth_headers("sales1"))
    assert submitted.status_code == 200, submitted.text
    return submitted.json()["commercial_offer"]


def _make_version(source_public_id: str, *, reason: str = "SCOPE_CHANGE", note: str = "Customer changed scope"):
    return client.post(
        f"/api/commercial-offers/{source_public_id}/versions",
        headers=auth_headers("sales1"),
        json={"version_reason": reason, "version_note": note},
    )


def _list(path: str, username: str = "sales1") -> list[dict[str, object]]:
    response = client.get(path, headers=auth_headers(username))
    assert response.status_code == 200, response.text
    return response.json()


def test_migration_seeds_abandoned_and_indexes_the_version_rules() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    migration = ScriptDirectory.from_config(Config("alembic.ini")).get_revision("20260908_0054").module
    assert migration.revision == "20260908_0054"
    assert migration.down_revision == "20260908_0053"
    assert migration.INACTIVE_STATUSES == COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES
    assert migration.PREPARATION_STATUSES == COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES
    assert migration.OFFER_CODE_VERSION_INDEX == COMMERCIAL_OFFER_CODE_VERSION_INDEX
    assert migration.ACTIVE_BASE_INDEX == COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX

    with SessionLocal() as db:
        status = db.execute(
            text(
                "SELECT is_active FROM workflow_status "
                "WHERE module = 'commercial_offer' AND status_code = 'ABANDONED'"
            )
        ).scalar_one()
        indexes = {
            name: definition
            for name, definition in db.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE tablename = 'crm_commercial_offer' "
                    "AND indexname IN (:code_index, :active_index)"
                ),
                {"code_index": COMMERCIAL_OFFER_CODE_VERSION_INDEX, "active_index": COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX},
            ).fetchall()
        }
    assert status is True
    assert "offer_code, version_number" in indexes[COMMERCIAL_OFFER_CODE_VERSION_INDEX]
    assert "previous_version_offer_id IS NULL" in indexes[COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX]
    assert "ABANDONED" in indexes[COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX]


def test_migration_downgrade_refuses_to_discard_offer_version_history(records: _Records) -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    migration = ScriptDirectory.from_config(Config("alembic.ini")).get_revision("20260908_0054").module
    source = _prepare_submitted_offer(records)
    source_id = str(source["public_id"])
    # Counted before and after, so practice data already holding versions does not change the answer.
    with SessionLocal() as db:
        before = migration.version_history_count(db.connection())
    made = _make_version(source_id)
    assert made.status_code == 201, made.text
    records.offers.append(str(made.json()["commercial_offer"]["public_id"]))

    with SessionLocal() as db:
        assert migration.version_history_count(db.connection()) == before + 1
        with pytest.raises(RuntimeError, match="cannot be downgraded"):
            migration.assert_no_version_history(db.connection())


def test_new_version_copies_current_commercial_content_but_not_submission_history(records: _Records) -> None:
    source = _prepare_submitted_offer(records)
    source_id = str(source["public_id"])

    created = _make_version(source_id)
    assert created.status_code == 201, created.text
    body = created.json()
    version = body["commercial_offer"]
    version_id = str(version["public_id"])
    records.offers.append(version_id)

    assert version["offer_code"] == source["offer_code"]
    assert version["version_number"] == 2
    assert version["previous_version_offer_public_id"] == source_id
    assert version["offer_status_code"] == "DRAFT"
    for field in ("offer_title", "offer_mode", "offer_type", "offer_value", "currency_code", "offer_date", "valid_until", "remarks"):
        assert version[field] == source[field]
    assert version["submitted_at"] is None
    assert version["submission_reference"] is None
    assert body["event"]["event_name"] == "CommercialOfferVersionCreated"
    assert body["event"]["status_before"] is None
    assert body["event"]["status_after"] == "DRAFT"
    assert body["event"]["event_payload"]["copied"] == {
        "lines": 1,
        "pricing_evidence": 1,
        "tc_clauses": 1,
        "credit_reviews": 1,
    }

    source_lines = _list(f"/api/commercial-offers/{source_id}/lines")
    copied_lines = _list(f"/api/commercial-offers/{version_id}/lines")
    assert len(copied_lines) == 1
    assert copied_lines[0]["public_id"] != source_lines[0]["public_id"]
    assert copied_lines[0]["scope_description"] == source_lines[0]["scope_description"]
    assert copied_lines[0]["rate_amount"] == source_lines[0]["rate_amount"]

    source_pricing = _list(f"/api/commercial-offers/{source_id}/pricing-evidence")
    copied_pricing = _list(f"/api/commercial-offers/{version_id}/pricing-evidence")
    assert len(copied_pricing) == 1 and copied_pricing[0]["public_id"] != source_pricing[0]["public_id"]
    assert copied_pricing[0]["is_selected_basis"] is True
    # Slice 4G: the rate goes to the matching copied line and its basis choice is carried over from version 1. It has
    # no quote, so it refers to none (review 4G-R2-001); a quoted rate's copy is tested in test_slice_4g_....
    assert copied_pricing[0]["line_public_id"] == copied_lines[0]["public_id"]
    assert copied_pricing[0]["line_number"] == copied_lines[0]["line_number"]
    assert copied_pricing[0]["quote_copy_rate_public_id"] is None and copied_pricing[0]["quote_copies"] == []
    assert copied_pricing[0]["selection_reason"] == "Best available matching machine"
    [carried] = copied_pricing[0]["basis_history"]
    assert carried["is_current"] is True and carried["carried_over_from_version_number"] == 1
    assert carried["chosen_at"] == source_pricing[0]["basis_history"][0]["chosen_at"]
    assert carried["selection_reason"] == source_pricing[0]["basis_history"][0]["selection_reason"]
    assert source_pricing[0]["basis_history"][0]["is_current"] is True

    source_terms = _list(f"/api/commercial-offers/{source_id}/tc-clauses")
    copied_terms = _list(f"/api/commercial-offers/{version_id}/tc-clauses")
    assert len(copied_terms) == 1 and copied_terms[0]["public_id"] != source_terms[0]["public_id"]

    source_reviews = _list(f"/api/commercial-offers/{source_id}/credit-review")
    copied_reviews = _list(f"/api/commercial-offers/{version_id}/credit-review")
    assert len(copied_reviews) == 1 and copied_reviews[0]["public_id"] != source_reviews[0]["public_id"]
    assert copied_reviews[0]["active"] is True

    assert len(_list(f"/api/commercial-offers/{source_id}/submission-evidence")) == 1
    assert _list(f"/api/commercial-offers/{version_id}/submission-evidence") == []
    assert _list(f"/api/commercial-offers/{version_id}/quote-documents") == []
    assert _list(f"/api/commercial-offers/{version_id}/customer-responses") == []
    assert _list(f"/api/commercial-offers/{version_id}/revisions") == []

    history = _list(f"/api/commercial-offers/{source_id}/versions", username="finance1")
    assert [(item["version_number"], item["offer_status_code"]) for item in history] == [(1, "SUBMITTED"), (2, "DRAFT")]


def test_a_new_offer_version_uses_the_offer_version_in_its_quote_reference(records: _Records) -> None:
    source = _prepare_submitted_offer(records)
    source_id = str(source["public_id"])
    made = _make_version(source_id)
    assert made.status_code == 201, made.text
    version = made.json()["commercial_offer"]
    version_id = str(version["public_id"])
    records.offers.append(version_id)

    generated = client.post(
        f"/api/commercial-offers/{version_id}/quote-documents",
        headers=auth_headers("sales1"),
    )
    assert generated.status_code == 201, generated.text
    assert generated.json()["quote_document"]["quote_reference"] == f"{source['offer_code']} v2/V1"


def test_reports_count_only_the_commercially_live_offer_version(records: _Records) -> None:
    before = client.get("/api/reports/open-offers", headers=auth_headers("sales1")).json()
    source = _prepare_submitted_offer(records)
    source_id = str(source["public_id"])
    after_source = client.get("/api/reports/open-offers", headers=auth_headers("sales1")).json()
    assert after_source["open_offer_total"] == before["open_offer_total"] + 1

    made = _make_version(source_id)
    assert made.status_code == 201, made.text
    version = made.json()["commercial_offer"]
    version_id = str(version["public_id"])
    records.offers.append(version_id)
    while_preparing = client.get("/api/reports/open-offers", headers=auth_headers("sales1")).json()
    assert while_preparing["open_offer_total"] == after_source["open_offer_total"]

    evidence = client.post(
        f"/api/commercial-offers/{version_id}/submission-evidence",
        headers=auth_headers("sales1"),
        json={
            "submission_reference": f"SLICE-9F-REPORT-{uuid4()}",
            "submission_channel": "EMAIL",
            "submitted_at": "2026-10-10T11:30:00Z",
        },
    )
    assert evidence.status_code == 201, evidence.text
    sent = client.post(f"/api/commercial-offers/{version_id}/mark-submitted", headers=auth_headers("sales1"))
    assert sent.status_code == 200, sent.text

    after_replacement = client.get("/api/reports/open-offers", headers=auth_headers("sales1")).json()
    assert after_replacement["open_offer_total"] == after_source["open_offer_total"]
    assert client.get(
        f"/api/commercial-offers/{source_id}", headers=auth_headers("sales1")
    ).json()["offer_status_code"] == "REVISED"
    replaced_guidance = client.get(
        f"/api/commercial-offers/{source_id}/lifecycle-guidance",
        headers=auth_headers("sales1"),
    ).json()
    assert replaced_guidance["lifecycle_state"] == "REPLACED_HISTORY"
    assert replaced_guidance["is_commercially_active"] is False
    assert replaced_guidance["can_record_customer_response"] is False
    assert replaced_guidance["can_make_new_version"] is False


def test_one_preparation_version_can_be_abandoned_and_the_next_number_is_not_reused(records: _Records) -> None:
    source = _prepare_submitted_offer(records)
    source_id = str(source["public_id"])
    v2_response = _make_version(source_id)
    assert v2_response.status_code == 201, v2_response.text
    v2 = v2_response.json()["commercial_offer"]
    records.offers.append(str(v2["public_id"]))

    generated_v2_quote = client.post(
        f"/api/commercial-offers/{v2['public_id']}/quote-documents",
        headers=auth_headers("sales1"),
    )
    assert generated_v2_quote.status_code == 201, generated_v2_quote.text
    v2_quote_id = generated_v2_quote.json()["quote_document"]["public_id"]

    refused_manual_submission = client.put(
        f"/api/commercial-offers/{v2['public_id']}",
        headers=auth_headers("sales1"),
        json={
            "expected_row_version": v2["row_version"],
            "submitted_at": "2026-10-10T10:30:00Z",
            "submission_reference": "MUST-NOT-BECOME-SENT",
            "submission_proof_note": "Use controlled evidence instead",
        },
    )
    assert refused_manual_submission.status_code == 422
    assert "submission evidence" in refused_manual_submission.json()["detail"]
    assert client.get(
        f"/api/commercial-offers/{source_id}", headers=auth_headers("sales1")
    ).json()["replaced_by_offer_public_id"] is None

    duplicate = _make_version(source_id)
    assert duplicate.status_code == 422
    assert "Only one" in duplicate.json()["detail"]

    guidance_while_preparing = client.get(
        f"/api/commercial-offers/{source_id}/lifecycle-guidance",
        headers=auth_headers("sales1"),
    )
    assert guidance_while_preparing.status_code == 200
    assert guidance_while_preparing.json()["can_record_customer_response"] is False
    assert "send that version or abandon it" in guidance_while_preparing.json()["advisory_message"].lower()

    refused_withdrawal = client.put(
        f"/api/commercial-offers/{v2['public_id']}",
        headers=auth_headers("sales1"),
        json={"expected_row_version": v2["row_version"], "offer_status_code": "WITHDRAWN"},
    )
    assert refused_withdrawal.status_code == 422
    assert "Abandon this version" in refused_withdrawal.json()["detail"]

    ready = client.put(
        f"/api/commercial-offers/{v2['public_id']}",
        headers=auth_headers("sales1"),
        json={"expected_row_version": v2["row_version"], "offer_status_code": "READY_FOR_REVIEW"},
    )
    assert ready.status_code == 200, ready.text
    refused_closure = client.put(
        f"/api/commercial-offers/{v2['public_id']}",
        headers=auth_headers("sales1"),
        json={
            "expected_row_version": ready.json()["commercial_offer"]["row_version"],
            "offer_status_code": "CLOSED",
        },
    )
    assert refused_closure.status_code == 422
    assert "Abandon this version" in refused_closure.json()["detail"]

    source_before_abandon = client.get(
        f"/api/commercial-offers/{source_id}", headers=auth_headers("sales1")
    ).json()
    assert source_before_abandon["offer_status_code"] == "SUBMITTED"
    assert source_before_abandon["replaced_by_offer_public_id"] is None

    abandoned = client.post(
        f"/api/commercial-offers/{v2['public_id']}/abandon-version",
        headers=auth_headers("sales1"),
    )
    assert abandoned.status_code == 200, abandoned.text
    assert abandoned.json()["commercial_offer"]["offer_status_code"] == "ABANDONED"
    assert abandoned.json()["event"]["event_name"] == "CommercialOfferVersionAbandoned"

    abandoned_guidance = client.get(
        f"/api/commercial-offers/{v2['public_id']}/lifecycle-guidance",
        headers=auth_headers("sales1"),
    ).json()
    assert abandoned_guidance["lifecycle_state"] == "ABANDONED_HISTORY"
    assert abandoned_guidance["is_commercially_active"] is False
    assert abandoned_guidance["can_record_customer_response"] is False
    assert abandoned_guidance["can_make_new_version"] is False

    abandoned_quotes = _list(f"/api/commercial-offers/{v2['public_id']}/quote-documents")
    abandoned_quote = next(item for item in abandoned_quotes if item["public_id"] == v2_quote_id)
    assert "ABANDONED" in abandoned_quote["approval_blocked_reason"]
    refused_abandoned_quote_approval = client.post(
        f"/api/commercial-offers/{v2['public_id']}/quote-documents/{v2_quote_id}/approve",
        headers=auth_headers("manager1"),
        json={},
    )
    assert refused_abandoned_quote_approval.status_code == 422
    assert "ABANDONED" in refused_abandoned_quote_approval.json()["detail"]

    abandoned_row_version = abandoned.json()["commercial_offer"]["row_version"]
    refused_abandoned_outcome = client.put(
        f"/api/commercial-offers/{v2['public_id']}",
        headers=auth_headers("sales1"),
        json={
            "expected_row_version": abandoned_row_version,
            "outcome_date": "2026-10-10",
            "outcome_remarks": "Must remain immutable",
        },
    )
    assert refused_abandoned_outcome.status_code == 422
    assert "read-only history" in refused_abandoned_outcome.json()["detail"]
    assert offer_row_version(str(v2["public_id"])) == abandoned_row_version

    guidance_after_abandon = client.get(
        f"/api/commercial-offers/{source_id}/lifecycle-guidance",
        headers=auth_headers("sales1"),
    ).json()
    assert guidance_after_abandon["can_record_customer_response"] is True
    assert guidance_after_abandon["can_make_new_version"] is True

    v3_response = _make_version(source_id, reason="RATE_CORRECTION", note="Second preparation")
    assert v3_response.status_code == 201, v3_response.text
    v3 = v3_response.json()["commercial_offer"]
    records.offers.append(str(v3["public_id"]))
    assert v3["version_number"] == 3
    assert v3["previous_version_offer_public_id"] == source_id

    history = _list(f"/api/commercial-offers/{v3['public_id']}/versions")
    assert [(item["version_number"], item["offer_status_code"]) for item in history] == [
        (1, "SUBMITTED"),
        (2, "ABANDONED"),
        (3, "DRAFT"),
    ]

    refused_edit = client.put(
        f"/api/commercial-offers/{v2['public_id']}",
        headers=auth_headers("sales1"),
        json={"expected_row_version": abandoned.json()["commercial_offer"]["row_version"], "offer_title": "No"},
    )
    assert refused_edit.status_code == 422
    assert "read-only" in refused_edit.json()["detail"]


def test_sending_a_version_retires_its_predecessor_and_only_latest_takes_the_outcome(records: _Records) -> None:
    source = _prepare_submitted_offer(records)
    source_id = str(source["public_id"])
    revision_requested = client.post(
        f"/api/commercial-offers/{source_id}/customer-responses",
        headers=auth_headers("sales1"),
        json={
            "response_outcome": "REVISION_REQUESTED",
            "response_received_at": "2026-10-10T09:45:00Z",
            "response_channel": "EMAIL",
        },
    )
    assert revision_requested.status_code == 201, revision_requested.text
    generated_source_quote = client.post(
        f"/api/commercial-offers/{source_id}/quote-documents",
        headers=auth_headers("sales1"),
    )
    assert generated_source_quote.status_code == 201, generated_source_quote.text
    source_quote_id = generated_source_quote.json()["quote_document"]["public_id"]
    made = _make_version(source_id)
    assert made.status_code == 201, made.text
    version = made.json()["commercial_offer"]
    version_id = str(version["public_id"])
    records.offers.append(version_id)

    blocked_response = client.post(
        f"/api/commercial-offers/{source_id}/customer-responses",
        headers=auth_headers("sales1"),
        json={
            "response_outcome": "PENDING_CUSTOMER_DECISION",
            "response_received_at": "2026-10-10T10:00:00Z",
            "response_channel": "EMAIL",
        },
    )
    assert blocked_response.status_code == 422
    assert "newer Commercial Offer version" in blocked_response.json()["detail"]

    blocked_withdrawal = client.put(
        f"/api/commercial-offers/{source_id}",
        headers=auth_headers("sales1"),
        json={"expected_row_version": offer_row_version(source_id), "offer_status_code": "WITHDRAWN"},
    )
    assert blocked_withdrawal.status_code == 422
    assert "newer Commercial Offer version" in blocked_withdrawal.json()["detail"]

    evidence = client.post(
        f"/api/commercial-offers/{version_id}/submission-evidence",
        headers=auth_headers("sales1"),
        json={
            "submission_reference": f"SLICE-9F-V2-{uuid4()}",
            "submission_channel": "EMAIL",
            "submitted_at": "2026-10-10T11:00:00Z",
        },
    )
    assert evidence.status_code == 201, evidence.text
    sent = client.post(f"/api/commercial-offers/{version_id}/mark-submitted", headers=auth_headers("sales1"))
    assert sent.status_code == 200, sent.text
    assert sent.json()["commercial_offer"]["offer_status_code"] == "SUBMITTED"
    assert sent.json()["event"]["event_payload"]["previous_version_status_after"] == "REVISED"

    with SessionLocal() as db:
        replacement_event = db.execute(
            text(
                "SELECT event_name, status_before, status_after, event_payload_json "
                "FROM business_event WHERE record_type = 'commercial_offer' "
                "AND record_public_id = :public_id AND event_name = 'CommercialOfferVersionReplaced'"
            ),
            {"public_id": source_id},
        ).one()
    replacement_payload = replacement_event.event_payload_json
    if isinstance(replacement_payload, str):
        replacement_payload = json.loads(replacement_payload)
    assert replacement_event.event_name == "CommercialOfferVersionReplaced"
    assert replacement_event.status_before == "SUBMITTED"
    assert replacement_event.status_after == "REVISED"
    assert replacement_payload["replacement_offer_public_id"] == version_id
    assert replacement_payload["replacement_version_number"] == 2

    old = client.get(f"/api/commercial-offers/{source_id}", headers=auth_headers("sales1")).json()
    assert old["offer_status_code"] == "REVISED"
    assert old["replaced_by_offer_public_id"] == version_id
    assert old["replaced_by_version_number"] == 2
    old_guidance = client.get(
        f"/api/commercial-offers/{source_id}/lifecycle-guidance",
        headers=auth_headers("sales1"),
    ).json()
    assert old_guidance["lifecycle_state"] == "REPLACED_HISTORY"
    assert old_guidance["is_commercially_active"] is False
    assert old_guidance["can_record_customer_response"] is False
    assert old_guidance["can_make_new_version"] is False
    assert "replaced by v2" in old_guidance["advisory_message"]

    revised_quotes = _list(f"/api/commercial-offers/{source_id}/quote-documents")
    revised_quote = next(item for item in revised_quotes if item["public_id"] == source_quote_id)
    assert "REVISED" in revised_quote["approval_blocked_reason"]
    refused_revised_quote_approval = client.post(
        f"/api/commercial-offers/{source_id}/quote-documents/{source_quote_id}/approve",
        headers=auth_headers("manager1"),
        json={},
    )
    assert refused_revised_quote_approval.status_code == 422
    assert "REVISED" in refused_revised_quote_approval.json()["detail"]

    revised_row_version = old["row_version"]
    refused_revised_outcome = client.put(
        f"/api/commercial-offers/{source_id}",
        headers=auth_headers("sales1"),
        json={
            "expected_row_version": revised_row_version,
            "outcome_date": "2026-10-10",
            "outcome_remarks": "Must stay on the live version",
        },
    )
    assert refused_revised_outcome.status_code == 422
    assert "read-only history" in refused_revised_outcome.json()["detail"]
    assert offer_row_version(source_id) == revised_row_version

    old_outcome = client.post(
        f"/api/commercial-offers/{source_id}/customer-responses",
        headers=auth_headers("sales1"),
        json={
            "response_outcome": "ACCEPTED_AWARDED",
            "response_received_at": "2026-10-10T12:00:00Z",
            "response_channel": "EMAIL",
        },
    )
    assert old_outcome.status_code == 422

    accepted = client.post(
        f"/api/commercial-offers/{version_id}/customer-responses",
        headers=auth_headers("sales1"),
        json={
            "response_outcome": "ACCEPTED_AWARDED",
            "response_received_at": "2026-10-10T12:00:00Z",
            "response_channel": "EMAIL",
            "awarded_version_snapshot": f"{source['offer_code']} v2",
        },
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["commercial_offer"]["offer_status_code"] == "ACCEPTED"


def test_submitted_rows_are_immutable_and_new_legacy_revision_cycles_are_refused(records: _Records) -> None:
    source = _prepare_submitted_offer(records)
    source_id = str(source["public_id"])

    same_status_with_outcome = client.put(
        f"/api/commercial-offers/{source_id}",
        headers=auth_headers("sales1"),
        json={
            "expected_row_version": offer_row_version(source_id),
            "offer_status_code": "SUBMITTED",
            "outcome_remarks": "Customer review still in progress",
        },
    )
    assert same_status_with_outcome.status_code == 200, same_status_with_outcome.text

    edit = client.put(
        f"/api/commercial-offers/{source_id}",
        headers=auth_headers("sales1"),
        json={"expected_row_version": offer_row_version(source_id), "offer_title": "Changed in place"},
    )
    assert edit.status_code == 422
    assert "Make a new version" in edit.json()["detail"]

    open_revision = client.post(
        f"/api/commercial-offers/{source_id}/revisions",
        headers=auth_headers("sales1"),
        json={"revision_reason": "SCOPE_CHANGE"},
    )
    assert open_revision.status_code == 422
    assert "Make a new version" in open_revision.json()["detail"]

    actor = _actor_public_id()
    revision_public_id = str(uuid4())
    with SessionLocal() as db:
        offer_id = int(
            db.execute(
                text("SELECT id FROM crm_commercial_offer WHERE offer_public_id = :public_id"),
                {"public_id": source_id},
            ).scalar_one()
        )
        insert_commercial_offer_revision(
            db,
            public_id=revision_public_id,
            commercial_offer_id=offer_id,
            values={
                "revision_label": "Legacy open revision",
                "revision_reason": "SCOPE_CHANGE",
                "revision_notes": "Created as a pre-Slice-9F compatibility record.",
                "revision_status": "OPEN",
                "source_submission_evidence_id": None,
                "opened_at": datetime(2026, 10, 10, 9, 45),
                "opened_by": actor,
                "created_by": actor,
            },
        )
        db.commit()

    still_locked = client.post(
        f"/api/commercial-offers/{source_id}/lines",
        headers=auth_headers("sales1"),
        json={"scope_description": "Must not land", "quantity": "1", "uom": "job"},
    )
    assert still_locked.status_code == 422
    assert "Make a new version" in still_locked.json()["detail"]

    cancelled = client.post(
        f"/api/commercial-offers/{source_id}/revisions/{revision_public_id}/cancel",
        headers=auth_headers("sales1"),
        json={"cancellation_notes": "Close legacy record"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["revision"]["revision_status"] == "CANCELLED"


def test_version_routes_enforce_permissions_and_concurrent_creation_makes_one_version(records: _Records) -> None:
    source = _prepare_submitted_offer(records)
    source_id = str(source["public_id"])

    assert _make_version(source_id).status_code == 201
    first_history = _list(f"/api/commercial-offers/{source_id}/versions")
    version_id = str(first_history[-1]["public_id"])
    records.offers.append(version_id)
    abandoned = client.post(
        f"/api/commercial-offers/{version_id}/abandon-version",
        headers=auth_headers("sales1"),
    )
    assert abandoned.status_code == 200

    for username in ("finance1", "ops1", "readonly1"):
        denied = client.post(
            f"/api/commercial-offers/{source_id}/versions",
            headers=auth_headers(username),
            json={"version_reason": "SCOPE_CHANGE"},
        )
        assert denied.status_code == 403

    actor = _actor_public_id()
    gate = threading.Barrier(2)
    outcomes: list[str] = []

    def worker() -> None:
        with SessionLocal() as db:
            gate.wait()
            try:
                result = create_commercial_offer_version(
                    db,
                    public_id=UUID(source_id),
                    payload=CommercialOfferVersionCreate(version_reason="SCOPE_CHANGE"),
                    current_user_public_id=actor,
                )
                outcomes.append(f"made:{result.commercial_offer.public_id}")
            except CommercialOfferValidationError as exc:
                outcomes.append(f"refused:{exc}")

    threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads)
    assert len([outcome for outcome in outcomes if outcome.startswith("made:")]) == 1
    assert len([outcome for outcome in outcomes if outcome.startswith("refused:")]) == 1
    made_id = next(outcome.split(":", 1)[1] for outcome in outcomes if outcome.startswith("made:"))
    records.offers.append(made_id)
    assert _list(f"/api/commercial-offers/{source_id}/versions")[-1]["version_number"] == 3


def test_predecessor_change_makes_version_submission_fail_without_partial_status_change(records: _Records) -> None:
    source = _prepare_submitted_offer(records)
    source_id = str(source["public_id"])
    made = _make_version(source_id)
    assert made.status_code == 201, made.text
    version = made.json()["commercial_offer"]
    version_id = str(version["public_id"])
    records.offers.append(version_id)

    evidence = client.post(
        f"/api/commercial-offers/{version_id}/submission-evidence",
        headers=auth_headers("sales1"),
        json={
            "submission_reference": f"SLICE-9F-ATOMIC-{uuid4()}",
            "submission_channel": "EMAIL",
            "submitted_at": "2026-10-10T13:00:00Z",
        },
    )
    assert evidence.status_code == 201
    with SessionLocal() as db:
        db.execute(
            text(
                "UPDATE crm_commercial_offer SET offer_status_code = 'WITHDRAWN' "
                "WHERE offer_public_id = :public_id"
            ),
            {"public_id": source_id},
        )
        db.commit()

    refused = client.post(f"/api/commercial-offers/{version_id}/mark-submitted", headers=auth_headers("sales1"))
    assert refused.status_code == 422
    assert "previous version is no longer Submitted" in refused.json()["detail"]
    assert client.get(f"/api/commercial-offers/{source_id}", headers=auth_headers("sales1")).json()["offer_status_code"] == "WITHDRAWN"
    assert client.get(f"/api/commercial-offers/{version_id}", headers=auth_headers("sales1")).json()["offer_status_code"] == "DRAFT"


def test_a_work_order_from_a_later_version_names_that_version_and_the_replaced_one_gives_none(records: _Records) -> None:
    """CS-04 part 2, item d (the frozen handoff contract's amendment of 12 October 2026): versions share the offer code,
    so the Work Order, its response and both handoff events carry the version number, and the title names "v2". The
    version a sent v2 replaced is REVISED and is refused."""
    source = _prepare_submitted_offer(records)
    source_id = str(source["public_id"])
    made = _make_version(source_id)
    assert made.status_code == 201, made.text
    version = made.json()["commercial_offer"]
    version_id = str(version["public_id"])
    records.offers.append(version_id)
    evidence = client.post(
        f"/api/commercial-offers/{version_id}/submission-evidence",
        headers=auth_headers("sales1"),
        json={"submission_reference": f"SLICE-9F-V2-{uuid4()}", "submission_channel": "EMAIL", "submitted_at": "2026-10-10T11:00:00Z"},
    )
    assert evidence.status_code == 201, evidence.text
    sent = client.post(f"/api/commercial-offers/{version_id}/mark-submitted", headers=auth_headers("sales1"))
    assert sent.status_code == 200, sent.text
    record_test_customer_response(version_id, "ACCEPTED_AWARDED", received_at="2026-10-11T09:00:00Z")
    version_lines = {line["public_id"] for line in _list(f"/api/commercial-offers/{version_id}/lines")}

    work_order_ids: list[str] = []
    try:
        handed_off = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={"commercial_offer_public_id": version_id, "customer_wo_reference": f"CUST-{uuid4()}"},
        )
        assert handed_off.status_code == 201, handed_off.text
        work_order = handed_off.json()["work_order"]
        work_order_ids.append(work_order["public_id"])
        assert work_order["commercial_offer_version_number"] == 2
        assert work_order["work_order_title"] == f"Work Order from {source['offer_code']} v2"
        events = {event["event_name"]: event["event_payload"] for event in handed_off.json()["events"]}
        assert events["WorkOrderCreated"]["commercial_offer_version_number"] == 2
        converted = events["CommercialOfferConvertedToWorkOrder"]
        assert converted["commercial_offer_version_number"] == 2
        assert [line["offer_line_public_id"] for line in converted["lines"]] == [
            line["source_offer_line_public_id"] for line in handed_off.json()["lines"]
        ]
        assert {line["offer_line_public_id"] for line in converted["lines"]} == version_lines
        detail = client.get(f"/api/work-orders/{work_order['public_id']}", headers=auth_headers("sales1")).json()
        assert detail["commercial_offer_version_number"] == 2
        listed = client.get(
            "/api/work-orders", headers=auth_headers("sales1"), params={"commercial_offer_public_id": version_id}
        )
        assert listed.status_code == 200, listed.text
        assert [(item["public_id"], item["commercial_offer_version_number"]) for item in listed.json()] == [
            (work_order["public_id"], 2)
        ]

        replaced = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={"commercial_offer_public_id": source_id, "customer_wo_reference": f"CUST-{uuid4()}"},
        )
        assert replaced.status_code == 422
        assert "only from an accepted Commercial Offer" in replaced.json()["detail"]
    finally:
        cleanup_test_work_orders(work_order_ids)


def test_a_later_version_abandoned_before_it_was_sent_leaves_the_earlier_one_live_to_hand_off(records: _Records) -> None:
    """The amendment of 12 October 2026, item 1: the handoff takes the accepted version, the latest live one. A v2
    abandoned before it was sent replaces nothing, so v1 stays Submitted, may be accepted and is handed off as v1."""
    source = _prepare_submitted_offer(records)
    source_id = str(source["public_id"])
    made = _make_version(source_id)
    assert made.status_code == 201, made.text
    version_id = str(made.json()["commercial_offer"]["public_id"])
    records.offers.append(version_id)
    abandoned = client.post(f"/api/commercial-offers/{version_id}/abandon-version", headers=auth_headers("sales1"))
    assert abandoned.status_code == 200, abandoned.text
    record_test_customer_response(source_id, "ACCEPTED_AWARDED", received_at="2026-10-11T09:00:00Z")

    work_order_ids: list[str] = []
    try:
        handed_off = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={"commercial_offer_public_id": source_id, "customer_wo_reference": f"CUST-{uuid4()}"},
        )
        assert handed_off.status_code == 201, handed_off.text
        work_order = handed_off.json()["work_order"]
        work_order_ids.append(work_order["public_id"])
        assert work_order["commercial_offer_version_number"] == 1
        assert work_order["work_order_title"] == f"Work Order from {source['offer_code']}"

        abandoned_handoff = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={"commercial_offer_public_id": version_id, "customer_wo_reference": f"CUST-{uuid4()}"},
        )
        assert abandoned_handoff.status_code == 422
    finally:
        cleanup_test_work_orders(work_order_ids)
