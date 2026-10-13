from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app
from app.modules.resource_assignments.repository import mark_service_write
from tests.offer_version_test_support import line_row_version, offer_row_version

client = TestClient(app)


def login(username: str = "admin1", password: str = "password") -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(username: str = "sales1") -> dict[str, str]:
    token = login(username, "password")
    return {"Authorization": f"Bearer {token}"}


def insert_legacy_open_revision(
    offer_public_id: str,
    *,
    reason: str = "CUSTOMER_CLARIFICATION",
    label: str = "Legacy open revision",
    source_evidence_public_id: str | None = None,
) -> dict[str, str]:
    """Insert a pre-9F OPEN revision so compatibility routes can be tested without starting a new legacy cycle."""
    revision_public_id = str(uuid4())
    with SessionLocal() as db:
        db.execute(
            text(
                """
                INSERT INTO commercial_offer_revision (
                    public_id, commercial_offer_id, revision_label, revision_reason,
                    revision_notes, revision_status, source_submission_evidence_id,
                    opened_at, created_at, updated_at
                )
                SELECT :revision_public_id, co.id, :label, :reason,
                       'Pre-Slice-9F compatibility record.', 'OPEN', evidence.id,
                       CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                FROM crm_commercial_offer co
                LEFT JOIN commercial_offer_submission_evidence evidence
                  ON evidence.commercial_offer_id = co.id
                 AND evidence.public_id = :source_evidence_public_id
                WHERE co.offer_public_id = :offer_public_id
                """
            ),
            {
                "revision_public_id": revision_public_id,
                "offer_public_id": offer_public_id,
                "source_evidence_public_id": source_evidence_public_id,
                "label": label,
                "reason": reason,
            },
        )
        db.commit()
    return {"public_id": revision_public_id, "revision_label": label, "revision_reason": reason}


def cleanup_test_records(
    *,
    opportunity_public_ids: list[str],
    offer_public_ids: list[str],
    account_public_ids: list[str] | None = None,
    lead_public_ids: list[str] | None = None,
) -> None:
    account_public_ids = account_public_ids or []
    lead_public_ids = lead_public_ids or []

    with SessionLocal() as db:
        for public_id in offer_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM commercial_offer_customer_response response
                    USING crm_commercial_offer co
                    WHERE co.id = response.commercial_offer_id
                      AND co.offer_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM commercial_offer_revision revision
                    USING crm_commercial_offer co
                    WHERE co.id = revision.commercial_offer_id
                      AND co.offer_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM commercial_offer_credit_review review
                    USING crm_commercial_offer co
                    WHERE co.id = review.commercial_offer_id
                      AND co.offer_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM commercial_offer_submission_evidence evidence
                    USING crm_commercial_offer co
                    WHERE co.id = evidence.commercial_offer_id
                      AND co.offer_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM commercial_offer_tc_clause attachment
                    USING crm_commercial_offer co
                    WHERE co.id = attachment.commercial_offer_id
                      AND co.offer_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM crm_commercial_offer_line_basis_choice choice
                    USING crm_commercial_offer_line line, crm_commercial_offer co
                    WHERE line.id = choice.commercial_offer_line_id
                      AND co.id = line.commercial_offer_id
                      AND co.offer_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM crm_commercial_offer_pricing_evidence pe
                    USING crm_commercial_offer co
                    WHERE co.id = pe.commercial_offer_id
                      AND co.offer_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM crm_commercial_offer_line line
                    USING crm_commercial_offer co
                    WHERE co.id = line.commercial_offer_id
                      AND co.offer_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'commercial_offer'
                      AND record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM crm_commercial_offer
                    WHERE offer_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )

        for public_id in opportunity_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'opportunity'
                      AND record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM crm_opportunity
                    WHERE opportunity_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )

        for public_id in account_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'business_party'
                      AND record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_party
                    WHERE business_party_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )

        for public_id in lead_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'lead'
                      AND record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM crm_lead
                    WHERE lead_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
        db.commit()


def create_test_opportunity() -> dict[str, object]:
    create_response = client.post(
        "/api/opportunities",
        headers=auth_headers("sales1"),
        json={
            "opportunity_name": f"Slice 4A Offer Opportunity {uuid4()}",
            "opportunity_source": "manual",
            "source_reference": "Commercial offer foundation test",
            "customer_requirement_summary": "Customer needs crane and transport quotation.",
            "opportunity_status_code": "NEW",
        },
    )
    assert create_response.status_code == 201
    opportunity = create_response.json()["opportunity"]

    update_response = client.put(
        f"/api/opportunities/{opportunity['public_id']}",
        headers=auth_headers("sales1"),
        json={"opportunity_status_code": "QUALIFIED"},
    )
    assert update_response.status_code == 200
    return update_response.json()["opportunity"]


def create_account_linked_test_opportunity() -> dict[str, dict[str, object]]:
    lead_response = client.post(
        "/api/leads",
        headers=auth_headers("sales1"),
        json={
            "lead_source": "manual",
            "source_reference": "Commercial offer Account traceability test",
            "company_name": f"Slice 6A1 Account Trace Lead {uuid4()}",
            "contact_name": "Slice 6A1 Contact",
            "contact_phone": "+91-9876543210",
            "contact_email": "slice6a1.trace@example.com",
            "requirement_summary": "Qualified enquiry for Commercial Offer Account traceability.",
            "lead_status_code": "NEW",
        },
    )
    assert lead_response.status_code == 201
    lead = lead_response.json()["lead"]

    qualification_response = client.post(
        f"/api/leads/{lead['public_id']}/qualification-decision",
        headers=auth_headers("sales1"),
        json={
            "decision_status_code": "QUALIFIED",
            "decision_notes": "Qualified so conversion can create Account traceability.",
            "reason": "Good fit",
        },
    )
    assert qualification_response.status_code == 200

    conversion_response = client.post(
        f"/api/leads/{lead['public_id']}/convert",
        headers=auth_headers("sales1"),
        json={"conversion_notes": "Create Qualified Prospect Account and Opportunity for traceability test."},
    )
    assert conversion_response.status_code == 201
    conversion = conversion_response.json()
    return {
        "lead": conversion["lead"],
        "account": conversion["account"],
        "opportunity": conversion["opportunity"],
    }


def create_test_commercial_offer(opportunity_public_id: str) -> dict[str, object]:
    response = client.post(
        "/api/commercial-offers",
        headers=auth_headers("sales1"),
        json={
            "opportunity_public_id": opportunity_public_id,
            "offer_title": "Slice 4A Commercial Offer",
            "offer_mode": "plum_generated",
            "offer_type": "budgetary",
            "offer_status_code": "DRAFT",
            "offer_value": "125000.00",
            "currency_code": "INR",
            "offer_date": "2026-08-01",
            "valid_until": "2026-08-15",
            "remarks": "Foundation offer only; no line items yet.",
        },
    )
    assert response.status_code == 201
    return response.json()["commercial_offer"]


def create_test_offer_line(commercial_offer_public_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/commercial-offers/{commercial_offer_public_id}/lines",
        headers=auth_headers("sales1"),
        json={
            "scope_description": "Slice 6J controlled submission line",
            "quantity": "1.00",
            "uom": "job",
        },
    )
    assert response.status_code == 201
    return response.json()["offer_line"]


def create_test_submission_evidence(commercial_offer_public_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
        headers=auth_headers("sales1"),
        json={
            "submission_reference": f"SUB-6J-{uuid4()}",
            "submission_channel": "EMAIL",
            "submitted_at": "2026-07-10T14:30:00Z",
            "recipient_summary": "Slice 6J controlled submission test contact",
        },
    )
    assert response.status_code == 201
    return response.json()["submission_evidence"]


def create_test_credit_review(
    commercial_offer_public_id: str,
    review_status: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/commercial-offers/{commercial_offer_public_id}/credit-review",
        headers=auth_headers("sales1"),
        json={
            "review_status": review_status,
            "review_reference": f"CREDIT-6J-{uuid4()}",
            "reviewed_at": "2026-07-10T14:15:00Z",
            "exposure_note": "Manual readiness evidence only; no exposure calculation.",
        },
    )
    assert response.status_code == 201
    return response.json()["credit_review"]


def mark_test_commercial_offer_submitted(commercial_offer_public_id: str) -> dict[str, object]:
    create_test_offer_line(commercial_offer_public_id)
    create_test_submission_evidence(commercial_offer_public_id)
    response = client.post(
        f"/api/commercial-offers/{commercial_offer_public_id}/mark-submitted",
        headers=auth_headers("sales1"),
    )
    assert response.status_code == 200
    return response.json()["commercial_offer"]


def count_offers_and_work_orders(commercial_offer_public_id: str) -> tuple[int, int]:
    with SessionLocal() as db:
        offer_count = int(
            db.execute(
                text("SELECT COUNT(*) FROM crm_commercial_offer WHERE offer_public_id = :public_id"),
                {"public_id": commercial_offer_public_id},
            ).scalar_one()
        )
        work_order_count = int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM crm_work_order wo
                    INNER JOIN crm_commercial_offer co ON co.id = wo.commercial_offer_id
                    WHERE co.offer_public_id = :public_id
                    """
                ),
                {"public_id": commercial_offer_public_id},
            ).scalar_one()
        )
    return offer_count, work_order_count


def get_seeded_tc_clause_public_id(clause_id: str) -> str:
    with SessionLocal() as db:
        value = db.execute(
            text("SELECT public_id FROM tc_clause_library WHERE clause_id = :clause_id"),
            {"clause_id": clause_id},
        ).scalar_one()
    return str(value)


def get_seeded_tc_clause_row(clause_id: str) -> dict[str, object]:
    with SessionLocal() as db:
        row = db.execute(
            text(
                """
                SELECT public_id, title, clause_text, active
                FROM tc_clause_library
                WHERE clause_id = :clause_id
                """
            ),
            {"clause_id": clause_id},
        ).first()
    assert row is not None
    return dict(row._mapping)


def count_commercial_offer_business_events(commercial_offer_public_id: str) -> int:
    with SessionLocal() as db:
        value = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM business_event
                WHERE record_type = 'commercial_offer'
                  AND record_public_id = :public_id
                """
            ),
            {"public_id": commercial_offer_public_id},
        ).scalar_one()
    return int(value)


def count_commercial_offer_business_events_by_name(commercial_offer_public_id: str, event_name: str) -> int:
    with SessionLocal() as db:
        value = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM business_event
                WHERE record_type = 'commercial_offer'
                  AND record_public_id = :public_id
                  AND event_name = :event_name
                """
            ),
            {"public_id": commercial_offer_public_id, "event_name": event_name},
        ).scalar_one()
    return int(value)


def count_active_commercial_offer_tc_attachments(commercial_offer_public_id: str) -> int:
    with SessionLocal() as db:
        value = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM commercial_offer_tc_clause attachment
                INNER JOIN crm_commercial_offer co ON co.id = attachment.commercial_offer_id
                WHERE co.offer_public_id = :public_id
                  AND attachment.active IS TRUE
                """
            ),
            {"public_id": commercial_offer_public_id},
        ).scalar_one()
    return int(value)


def repair_opportunity_with_minimal_account(opportunity_public_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/opportunities/{opportunity_public_id}/account-repair",
        headers=auth_headers("sales1"),
        json={
            "create_account": {
                "account_name": f"Slice 6B1 CO Repair Account {uuid4()}",
                "source_remarks": "Created so an existing Commercial Offer can regain Account traceability.",
            }
        },
    )
    assert response.status_code == 200
    return response.json()["account"]


def test_commercial_offers_require_authentication() -> None:
    response = client.get("/api/commercial-offers")

    assert response.status_code == 401


def test_sales_user_can_create_list_and_get_commercial_offer() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)

        create_response = client.post(
            "/api/commercial-offers",
            headers=auth_headers("sales1"),
            json={
                "opportunity_public_id": opportunity_public_id,
                "offer_title": "Slice 4A Commercial Offer",
                "offer_mode": "plum_generated",
                "offer_type": "budgetary",
                "offer_status_code": "DRAFT",
                "offer_value": "125000.00",
                "currency_code": "INR",
                "offer_date": "2026-08-01",
                "valid_until": "2026-08-15",
                "remarks": "Foundation commercial offer smoke test.",
            },
        )

        assert create_response.status_code == 201
        body = create_response.json()
        commercial_offer = body["commercial_offer"]
        offer_public_ids.append(commercial_offer["public_id"])
        assert commercial_offer["offer_code"].startswith("CO-")
        assert commercial_offer["opportunity_public_id"] == opportunity_public_id
        assert commercial_offer["offer_mode"] == "plum_generated"
        assert commercial_offer["offer_type"] == "budgetary"
        assert commercial_offer["offer_status_code"] == "DRAFT"
        assert body["event"]["event_name"] == "CommercialOfferCreated"
        assert body["event"]["record_type"] == "commercial_offer"
        assert body["event"]["record_public_id"] == commercial_offer["public_id"]
        assert "password" not in str(body).lower()

        list_response = client.get(
            "/api/commercial-offers?limit=10",
            headers=auth_headers("sales1"),
        )
        assert list_response.status_code == 200
        offers = list_response.json()
        assert any(offer["public_id"] == commercial_offer["public_id"] for offer in offers)

        filtered_response = client.get(
            f"/api/commercial-offers?opportunity_public_id={opportunity_public_id}",
            headers=auth_headers("sales1"),
        )
        assert filtered_response.status_code == 200
        assert any(offer["public_id"] == commercial_offer["public_id"] for offer in filtered_response.json())

        get_response = client.get(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("readonly1"),
        )
        assert get_response.status_code == 200
        assert get_response.json()["public_id"] == commercial_offer["public_id"]
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_finance_user_can_list_but_cannot_create_commercial_offer() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_ids.append(str(commercial_offer["public_id"]))

        list_response = client.get(
            "/api/commercial-offers?limit=5",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200

        get_response = client.get(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("finance1"),
        )
        assert get_response.status_code == 200

        create_response = client.post(
            "/api/commercial-offers",
            headers=auth_headers("finance1"),
            json={"opportunity_public_id": opportunity_public_id},
        )
        assert create_response.status_code == 403
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_create_commercial_offer_rejects_invalid_fields_and_missing_opportunity() -> None:
    opportunity_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)

        invalid_mode_response = client.post(
            "/api/commercial-offers",
            headers=auth_headers("sales1"),
            json={"opportunity_public_id": opportunity_public_id, "offer_mode": "unknown_mode"},
        )
        assert invalid_mode_response.status_code == 422

        invalid_status_response = client.post(
            "/api/commercial-offers",
            headers=auth_headers("sales1"),
            json={"opportunity_public_id": opportunity_public_id, "offer_status_code": "SUBMITTED"},
        )
        assert invalid_status_response.status_code == 422

        invalid_date_response = client.post(
            "/api/commercial-offers",
            headers=auth_headers("sales1"),
            json={
                "opportunity_public_id": opportunity_public_id,
                "offer_date": "2026-08-15",
                "valid_until": "2026-08-01",
            },
        )
        assert invalid_date_response.status_code == 422

        missing_opportunity_response = client.post(
            "/api/commercial-offers",
            headers=auth_headers("sales1"),
            json={"opportunity_public_id": str(uuid4())},
        )
        assert missing_opportunity_response.status_code == 404
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=[])


def test_get_missing_commercial_offer_returns_not_found() -> None:
    response = client.get(
        f"/api/commercial-offers/{uuid4()}",
        headers=auth_headers("sales1"),
    )

    assert response.status_code == 404


def test_sales_user_can_capture_commercial_offer_lifecycle_submission_and_outcome() -> None:
    lead_public_ids: list[str] = []
    account_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity = linked_context["opportunity"]
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_ids.append(str(commercial_offer["public_id"]))
        assert commercial_offer["account_public_id"] == linked_context["account"]["public_id"]

        line_response = client.post(
            f"/api/commercial-offers/{commercial_offer['public_id']}/lines",
            headers=auth_headers("sales1"),
            json={
                "scope_description": "Controlled submission test line",
                "quantity": "1.00",
                "uom": "job",
            },
        )
        assert line_response.status_code == 201

        evidence_response = client.post(
            f"/api/commercial-offers/{commercial_offer['public_id']}/submission-evidence",
            headers=auth_headers("sales1"),
            json={
                "submission_channel": "EMAIL",
                "submitted_at": "2026-08-05T10:30:00Z",
                "submission_reference": "EMAIL-SUB-001",
            },
        )
        assert evidence_response.status_code == 201

        submitted_response = client.post(
            f"/api/commercial-offers/{commercial_offer['public_id']}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert submitted_response.status_code == 200
        submitted_body = submitted_response.json()
        submitted_offer = submitted_body["commercial_offer"]
        assert submitted_offer["offer_status_code"] == "SUBMITTED"
        assert submitted_offer["submission_reference"] == "EMAIL-SUB-001"
        assert submitted_body["event"]["event_name"] == "CommercialOfferCommerciallyCommitted"
        assert submitted_body["event"]["event_payload"]["commercially_committed"] is True

        # Slice 6M.1 completion: general update can no longer move SUBMITTED -> ACCEPTED.
        # ACCEPTED must be established through the dedicated Customer Response action.
        blocked_accept_response = client.put(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("sales1"),
            json={
                "expected_row_version": offer_row_version(commercial_offer['public_id']),
                "offer_status_code": "ACCEPTED",
                "outcome_date": "2026-08-10",
                "outcome_remarks": "Customer accepted the Commercial Offer for Slice 4F test.",
            },
        )
        assert blocked_accept_response.status_code == 422
        assert "cannot be set to ACCEPTED" in blocked_accept_response.json()["detail"]

        response_result = client.post(
            f"/api/commercial-offers/{commercial_offer['public_id']}/customer-responses",
            headers=auth_headers("sales1"),
            json={
                "response_outcome": "ACCEPTED_AWARDED",
                "response_received_at": "2026-08-10T09:00:00Z",
                "response_channel": "EMAIL",
                "customer_response_notes": "Customer accepted the Commercial Offer for Slice 4F test.",
            },
        )
        assert response_result.status_code == 201
        accepted_body = response_result.json()
        accepted_offer = accepted_body["commercial_offer"]
        assert accepted_offer["offer_status_code"] == "ACCEPTED"
        assert accepted_offer["outcome_date"] == "2026-08-10"
        assert accepted_body["event"]["event_name"] == "CommercialOfferCustomerResponseRecorded"
        assert "password" not in str(accepted_body).lower()

        # A sent version remains immutable after the final outcome too.
        remarks_only_response = client.put(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(commercial_offer['public_id']), "remarks": "Follow-up note recorded after acceptance."},
        )
        assert remarks_only_response.status_code == 422
        assert "read-only" in remarks_only_response.json()["detail"]
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_commercial_offer_submit_and_accept_require_account_traceability() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_ids.append(str(commercial_offer["public_id"]))
        assert commercial_offer["account_public_id"] is None

        submitted_response = client.post(
            f"/api/commercial-offers/{commercial_offer['public_id']}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert submitted_response.status_code == 422
        assert "Account traceability" in submitted_response.json()["detail"]

        # Slice 6M.1 completion: general update can never enter ACCEPTED regardless of
        # Account traceability, so this now surfaces the entry-guard message rather than
        # the Account-traceability message. ACCEPTED is only reachable through the
        # dedicated Customer Response action, which itself requires a Submitted offer -
        # and mark-submitted is already blocked above by missing Account traceability, so
        # there is no reachable path to ACCEPTED for this offer at all.
        accepted_response = client.put(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("sales1"),
            json={
                "expected_row_version": offer_row_version(commercial_offer['public_id']),
                "offer_status_code": "ACCEPTED",
                "outcome_date": "2026-08-10",
                "outcome_remarks": "Should be blocked until Account is linked.",
            },
        )
        assert accepted_response.status_code == 422
        assert "cannot be set to ACCEPTED" in accepted_response.json()["detail"]

        get_response = client.get(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("sales1"),
        )
        assert get_response.status_code == 200
        assert get_response.json()["offer_status_code"] == "DRAFT"
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_create_commercial_offer_blocks_second_actionable_offer_for_opportunity() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_ids.append(str(commercial_offer["public_id"]))

        blocked_response = client.post(
            "/api/commercial-offers",
            headers=auth_headers("sales1"),
            json={
                "opportunity_public_id": opportunity_public_id,
                "offer_title": "Should route to existing offer instead",
            },
        )

        assert blocked_response.status_code == 422
        detail = blocked_response.json()["detail"]
        assert "active/actionable Commercial Offer already exists" in detail
        assert commercial_offer["offer_code"] in detail
        assert commercial_offer["public_id"] in detail
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_commercial_offer_lifecycle_succeeds_after_opportunity_account_repair() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_ids.append(str(commercial_offer["public_id"]))
        assert commercial_offer["account_public_id"] is None

        blocked_response = client.post(
            f"/api/commercial-offers/{commercial_offer['public_id']}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert blocked_response.status_code == 422

        account = repair_opportunity_with_minimal_account(opportunity_public_id)
        account_public_ids.append(str(account["public_id"]))

        refreshed_response = client.get(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("sales1"),
        )
        assert refreshed_response.status_code == 200
        assert refreshed_response.json()["account_public_id"] == account["public_id"]

        line_response = client.post(
            f"/api/commercial-offers/{commercial_offer['public_id']}/lines",
            headers=auth_headers("sales1"),
            json={
                "scope_description": "Submission after Account repair",
                "quantity": "1.00",
                "uom": "job",
            },
        )
        assert line_response.status_code == 201

        evidence_response = client.post(
            f"/api/commercial-offers/{commercial_offer['public_id']}/submission-evidence",
            headers=auth_headers("sales1"),
            json={
                "submission_channel": "EMAIL",
                "submitted_at": "2026-08-05T10:30:00Z",
                "submission_reference": "SUBMITTED-AFTER-REPAIR",
            },
        )
        assert evidence_response.status_code == 201

        submitted_response = client.post(
            f"/api/commercial-offers/{commercial_offer['public_id']}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert submitted_response.status_code == 200
        assert submitted_response.json()["commercial_offer"]["account_public_id"] == account["public_id"]
        assert submitted_response.json()["commercial_offer"]["offer_status_code"] == "SUBMITTED"

        # Slice 6M.1 completion: ACCEPTED is reached through the dedicated Customer
        # Response action, not through generic update.
        accepted_response = client.post(
            f"/api/commercial-offers/{commercial_offer['public_id']}/customer-responses",
            headers=auth_headers("sales1"),
            json={
                "response_outcome": "ACCEPTED_AWARDED",
                "response_received_at": "2026-08-10T09:00:00Z",
                "response_channel": "EMAIL",
            },
        )
        assert accepted_response.status_code == 201
        assert accepted_response.json()["commercial_offer"]["offer_status_code"] == "ACCEPTED"
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
        )


def test_sales_user_can_mark_eligible_commercial_offer_submitted_and_commercially_committed() -> None:
    lead_public_ids: list[str] = []
    account_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        create_test_offer_line(commercial_offer_public_id)
        evidence = create_test_submission_evidence(commercial_offer_public_id)
        credit_review = create_test_credit_review(
            commercial_offer_public_id,
            "WITHIN_LIMIT_AS_PER_MANUAL_REVIEW",
        )

        evidence_before = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
            headers=auth_headers("sales1"),
        ).json()
        work_orders_before = client.get(
            f"/api/work-orders?commercial_offer_public_id={commercial_offer_public_id}",
            headers=auth_headers("sales1"),
        ).json()

        response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["commercial_offer"]["offer_status_code"] == "SUBMITTED"
        assert body["commercial_offer"]["submitted_at"].startswith("2026-07-10T14:30:00")
        assert body["commercial_offer"]["submission_reference"] == evidence["submission_reference"]
        assert body["warnings"] == []
        assert body["event"]["event_name"] == "CommercialOfferCommerciallyCommitted"
        assert body["event"]["status_before"] == "DRAFT"
        assert body["event"]["status_after"] == "SUBMITTED"
        event_payload = body["event"]["event_payload"]
        assert event_payload["latest_submission_evidence_public_id"] == evidence["public_id"]
        assert event_payload["latest_credit_review_public_id"] == credit_review["public_id"]
        assert event_payload["latest_credit_review_status"] == "WITHIN_LIMIT_AS_PER_MANUAL_REVIEW"
        assert event_payload["commercially_committed"] is True
        assert event_payload["submission_evidence_created_by_action"] is False
        assert event_payload["exposure_calculated"] is False
        assert event_payload["work_order_created"] is False

        evidence_after = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
            headers=auth_headers("sales1"),
        ).json()
        assert len(evidence_after) == len(evidence_before) == 1

        readiness_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-readiness",
            headers=auth_headers("sales1"),
        )
        assert readiness_response.status_code == 200
        readiness_items = {item["code"]: item for item in readiness_response.json()["checklist_items"]}
        assert readiness_items["COMMERCIAL_COMMITMENT_STATUS"]["status"] == "PASS"
        assert readiness_items["COMMERCIAL_COMMITMENT_STATUS"]["evidence"]["commercially_committed"] is True

        work_orders_after = client.get(
            f"/api/work-orders?commercial_offer_public_id={commercial_offer_public_id}",
            headers=auth_headers("sales1"),
        ).json()
        assert work_orders_after == work_orders_before == []
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_mark_submitted_requires_permission_active_line_and_submission_evidence() -> None:
    lead_public_ids: list[str] = []
    account_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        missing_offer_response = client.post(
            f"/api/commercial-offers/{uuid4()}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert missing_offer_response.status_code == 404

        unauthorized_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/mark-submitted",
            headers=auth_headers("finance1"),
        )
        assert unauthorized_response.status_code == 403

        missing_line_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert missing_line_response.status_code == 422
        assert "active Commercial Offer line" in missing_line_response.json()["detail"]

        create_test_offer_line(commercial_offer_public_id)
        missing_evidence_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert missing_evidence_response.status_code == 422
        assert "Submission evidence metadata is required" in missing_evidence_response.json()["detail"]

        bypass_response = client.put(
            f"/api/commercial-offers/{commercial_offer_public_id}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(commercial_offer_public_id), "offer_status_code": "SUBMITTED"},
        )
        assert bypass_response.status_code == 422
        assert "Record as Submitted / Commercially Committed" in bypass_response.json()["detail"]
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_mark_submitted_status_credit_hold_and_warning_paths() -> None:
    lead_public_ids: list[str] = []
    account_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        for target_status in ("WITHDRAWN", "REJECTED", "CLOSED", "ACCEPTED"):
            linked_context = create_account_linked_test_opportunity()
            lead_public_ids.append(str(linked_context["lead"]["public_id"]))
            account_public_ids.append(str(linked_context["account"]["public_id"]))
            opportunity_public_id = str(linked_context["opportunity"]["public_id"])
            opportunity_public_ids.append(opportunity_public_id)
            offer = create_test_commercial_offer(opportunity_public_id)
            offer_public_id = str(offer["public_id"])
            offer_public_ids.append(offer_public_id)
            if target_status in ("REJECTED", "ACCEPTED"):
                # Slice 6M.1 completion: ACCEPTED and REJECTED can only be reached through
                # the dedicated Customer Response action, not through generic update.
                mark_test_commercial_offer_submitted(offer_public_id)
                outcome = "REJECTED_LOST" if target_status == "REJECTED" else "ACCEPTED_AWARDED"
                record_test_customer_response(offer_public_id, outcome, received_at="2026-07-12T09:00:00Z")
            else:
                update_response = client.put(
                    f"/api/commercial-offers/{offer_public_id}",
                    headers=auth_headers("sales1"),
                    json={"expected_row_version": offer_row_version(offer_public_id), "offer_status_code": target_status},
                )
                assert update_response.status_code == 200
            blocked_response = client.post(
                f"/api/commercial-offers/{offer_public_id}/mark-submitted",
                headers=auth_headers("sales1"),
            )
            assert blocked_response.status_code == 422
            assert f"Current status is {target_status}" in blocked_response.json()["detail"]

        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        held_offer = create_test_commercial_offer(opportunity_public_id)
        held_offer_public_id = str(held_offer["public_id"])
        offer_public_ids.append(held_offer_public_id)
        create_test_offer_line(held_offer_public_id)
        create_test_submission_evidence(held_offer_public_id)
        create_test_credit_review(held_offer_public_id, "REJECTED_OR_ON_HOLD")
        event_count_before = count_commercial_offer_business_events(held_offer_public_id)

        held_response = client.post(
            f"/api/commercial-offers/{held_offer_public_id}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert held_response.status_code == 422
        assert "Rejected or On Hold" in held_response.json()["detail"]
        assert count_commercial_offer_business_events(held_offer_public_id) == event_count_before

        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        warning_offer = create_test_commercial_offer(opportunity_public_id)
        warning_offer_public_id = str(warning_offer["public_id"])
        offer_public_ids.append(warning_offer_public_id)
        create_test_offer_line(warning_offer_public_id)
        create_test_submission_evidence(warning_offer_public_id)

        warning_response = client.post(
            f"/api/commercial-offers/{warning_offer_public_id}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert warning_response.status_code == 200
        assert warning_response.json()["commercial_offer"]["offer_status_code"] == "SUBMITTED"
        assert "has not been recorded" in warning_response.json()["warnings"][0]
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_sales_user_can_update_commercial_offer_and_status() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_ids.append(str(commercial_offer["public_id"]))

        update_response = client.put(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("sales1"),
            json={
                "expected_row_version": offer_row_version(commercial_offer['public_id']),
                "offer_title": "Slice 4C Updated Commercial Offer",
                "offer_mode": "customer_format",
                "offer_type": "firm",
                "offer_status_code": "READY_FOR_REVIEW",
                "offer_value": "175000.00",
                "currency_code": "INR",
                "offer_date": "2026-08-02",
                "valid_until": "2026-08-20",
                "remarks": "Updated through Slice 4C foundation.",
            },
        )

        assert update_response.status_code == 200
        body = update_response.json()
        updated_offer = body["commercial_offer"]
        assert updated_offer["public_id"] == commercial_offer["public_id"]
        assert updated_offer["offer_title"] == "Slice 4C Updated Commercial Offer"
        assert updated_offer["offer_mode"] == "customer_format"
        assert updated_offer["offer_type"] == "firm"
        assert updated_offer["offer_status_code"] == "READY_FOR_REVIEW"
        assert str(updated_offer["offer_value"]) in {"175000.00", "175000.0", "175000"}
        event_names = [event["event_name"] for event in body["events"]]
        assert "CommercialOfferUpdated" in event_names
        assert "CommercialOfferStatusChanged" in event_names
        assert "password" not in str(body).lower()
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_finance_user_can_view_but_cannot_update_commercial_offer() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_ids.append(str(commercial_offer["public_id"]))

        get_response = client.get(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("finance1"),
        )
        assert get_response.status_code == 200

        update_response = client.put(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("finance1"),
            json={"expected_row_version": offer_row_version(commercial_offer['public_id']), "offer_title": "Finance should not update"},
        )
        assert update_response.status_code == 403
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_update_commercial_offer_rejects_invalid_status_date_and_value() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_ids.append(str(commercial_offer["public_id"]))

        revised_response = client.put(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(commercial_offer['public_id']), "offer_status_code": "REVISED"},
        )
        assert revised_response.status_code == 422

        invalid_date_response = client.put(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(commercial_offer['public_id']), "offer_date": "2026-08-20", "valid_until": "2026-08-02"},
        )
        assert invalid_date_response.status_code == 422

        invalid_value_response = client.put(
            f"/api/commercial-offers/{commercial_offer['public_id']}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(commercial_offer['public_id']), "offer_value": "-1.00"},
        )
        assert invalid_value_response.status_code == 422
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


@pytest.mark.parametrize("starting_status", ["DRAFT", "READY_FOR_REVIEW"])
@pytest.mark.parametrize("history_status", ["REVISED", "ABANDONED"])
def test_general_update_never_moves_an_offer_into_version_history(starting_status: str, history_status: str) -> None:
    """REVISED and ABANDONED are entered only by sending a later version and by abandon-version (Slice 9F): both are
    inactive for the one-active-Base-Offer rule, so a general update reaching them would free the Opportunity for a
    second Base Offer with nothing replaced or abandoned. They are not in COMMERCIAL_OFFER_STATUS_UPDATE_ALLOWED_STATUSES."""
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity_public_id = str(create_test_opportunity()["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        offer_public_id = str(create_test_commercial_offer(opportunity_public_id)["public_id"])
        offer_public_ids.append(offer_public_id)
        if starting_status != "DRAFT":
            moved = client.put(
                f"/api/commercial-offers/{offer_public_id}",
                headers=auth_headers("sales1"),
                json={"expected_row_version": offer_row_version(offer_public_id), "offer_status_code": starting_status},
            )
            assert moved.status_code == 200, moved.text

        refused = client.put(
            f"/api/commercial-offers/{offer_public_id}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(offer_public_id), "offer_status_code": history_status},
        )

        assert refused.status_code == 422
        assert refused.json()["detail"] == f"Commercial Offer status cannot be set to {history_status}."
        current = client.get(f"/api/commercial-offers/{offer_public_id}", headers=auth_headers("sales1")).json()
        assert current["offer_status_code"] == starting_status
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_update_commercial_offer_blocks_transition_away_from_terminal_status() -> None:
    """Slice 6M.1 (fa09489 + completion): WITHDRAWN, REJECTED, CLOSED and ACCEPTED must all
    be final for general update - none of them can be left through PUT once reached."""
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []

    try:
        for terminal_status in ("WITHDRAWN", "REJECTED", "CLOSED", "ACCEPTED"):
            linked_context = create_account_linked_test_opportunity()
            lead_public_ids.append(str(linked_context["lead"]["public_id"]))
            account_public_ids.append(str(linked_context["account"]["public_id"]))
            opportunity_public_id = str(linked_context["opportunity"]["public_id"])
            opportunity_public_ids.append(opportunity_public_id)
            commercial_offer = create_test_commercial_offer(opportunity_public_id)
            commercial_offer_public_id = str(commercial_offer["public_id"])
            offer_public_ids.append(commercial_offer_public_id)

            if terminal_status in ("REJECTED", "ACCEPTED"):
                # ACCEPTED and REJECTED can only be reached through the dedicated Customer
                # Response action (Slice 6L), never through generic update.
                mark_test_commercial_offer_submitted(commercial_offer_public_id)
                outcome = "REJECTED_LOST" if terminal_status == "REJECTED" else "ACCEPTED_AWARDED"
                record_test_customer_response(commercial_offer_public_id, outcome, received_at="2026-07-12T09:00:00Z")
            else:
                to_terminal_response = client.put(
                    f"/api/commercial-offers/{commercial_offer_public_id}",
                    headers=auth_headers("sales1"),
                    json={"expected_row_version": offer_row_version(commercial_offer_public_id), "offer_status_code": terminal_status},
                )
                assert to_terminal_response.status_code == 200
                assert to_terminal_response.json()["commercial_offer"]["offer_status_code"] == terminal_status

            reopen_response = client.put(
                f"/api/commercial-offers/{commercial_offer_public_id}",
                headers=auth_headers("sales1"),
                json={"expected_row_version": offer_row_version(commercial_offer_public_id), "offer_status_code": "DRAFT"},
            )
            assert reopen_response.status_code == 422
            assert f"Commercial Offer status {terminal_status} is final" in reopen_response.json()["detail"]

            reconfirm_response = client.get(
                f"/api/commercial-offers/{commercial_offer_public_id}",
                headers=auth_headers("sales1"),
            )
            assert reconfirm_response.json()["offer_status_code"] == terminal_status

            # Terminal versions are fully read-only.
            remarks_response = client.put(
                f"/api/commercial-offers/{commercial_offer_public_id}",
                headers=auth_headers("sales1"),
                json={"expected_row_version": offer_row_version(commercial_offer_public_id), "remarks": f"Closed-out remarks after {terminal_status}."},
            )
            assert remarks_response.status_code == 422
            assert "read-only" in remarks_response.json()["detail"]

            # Repeating the same status with a commercial-field edit is also refused.
            same_status_response = client.put(
                f"/api/commercial-offers/{commercial_offer_public_id}",
                headers=auth_headers("sales1"),
                json={"expected_row_version": offer_row_version(commercial_offer_public_id), "offer_status_code": terminal_status, "remarks": "No-op status resubmission."},
            )
            assert same_status_response.status_code == 422
            assert "read-only" in same_status_response.json()["detail"]
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_a_submitted_offer_cannot_go_back_to_draft_or_ready_for_review_through_general_update() -> None:
    """TB-1 TB1-301 (4 October 2026): a submitted offer is commercially committed. General update
    refuses moving it back to Draft or Ready for Review and changes nothing; its commercial fields
    are immutable, while the explicit withdrawal outcome remains available."""
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []

    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer_public_id = str(create_test_commercial_offer(opportunity_public_id)["public_id"])
        offer_public_ids.append(commercial_offer_public_id)
        submitted = mark_test_commercial_offer_submitted(commercial_offer_public_id)
        assert submitted["offer_status_code"] == "SUBMITTED"
        events_before = count_commercial_offer_business_events(commercial_offer_public_id)

        for target_status in ("DRAFT", "READY_FOR_REVIEW"):
            refused = client.put(
                f"/api/commercial-offers/{commercial_offer_public_id}",
                headers=auth_headers("sales1"),
                json={"expected_row_version": offer_row_version(commercial_offer_public_id), "offer_status_code": target_status, "remarks": "Back to draft by mistake."},
            )
            assert refused.status_code == 422
            assert "cannot go back to Draft or Ready for Review" in refused.json()["detail"]

        unchanged = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}",
            headers=auth_headers("sales1"),
        ).json()
        assert unchanged["offer_status_code"] == "SUBMITTED"
        assert unchanged["submitted_at"] == submitted["submitted_at"]
        assert unchanged["remarks"] == submitted["remarks"]
        assert count_commercial_offer_business_events(commercial_offer_public_id) == events_before

        remarks_response = client.put(
            f"/api/commercial-offers/{commercial_offer_public_id}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(commercial_offer_public_id), "offer_status_code": "SUBMITTED", "remarks": "Customer asked for the site plan."},
        )
        assert remarks_response.status_code == 422
        assert "Make a new version" in remarks_response.json()["detail"]

        withdrawn = client.put(
            f"/api/commercial-offers/{commercial_offer_public_id}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(commercial_offer_public_id), "offer_status_code": "WITHDRAWN"},
        )
        assert withdrawn.status_code == 200
        assert withdrawn.json()["commercial_offer"]["offer_status_code"] == "WITHDRAWN"
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_a_final_offers_lines_prices_terms_and_evidence_can_no_longer_change() -> None:
    """TB-1 TB1-301 (b) (5 October 2026): once the customer's acceptance is recorded, the offer's lines, pricing
    evidence and basis rate, T&C clauses, credit reviews and submission evidence are refused (422), nothing changes and
    no event is recorded - an accepted offer's lines are what its Work Order copies. A submitted offer takes them only
    through an open revision (CS-05c, tests/test_cs05c_submitted_offer_lock.py), and a withdrawn one is refused too."""
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    market_rate = {
        "evidence_type": "market_rate",
        "source_name": "ABC Crane Vendor",
        "equipment_service_description": "80T crane day shift with operator",
        "rate_amount": "95000.00",
        "currency_code": "INR",
        "rate_basis": "per_day",
        "collected_by_name": "Operations User",
        "collected_at": "2026-08-03T10:30:00Z",
    }

    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        offer_public_id = str(create_test_commercial_offer(opportunity_public_id)["public_id"])
        offer_public_ids.append(offer_public_id)
        base = f"/api/commercial-offers/{offer_public_id}"

        rate_line = create_test_offer_line(offer_public_id)
        rate = client.post(
            f"{base}/pricing-evidence",
            headers=auth_headers("ops1"),
            json={**market_rate, "line_public_id": rate_line["public_id"]},
        )
        assert rate.status_code == 201
        rate_public_id = rate.json()["pricing_evidence"]["public_id"]
        attached = client.post(
            f"{base}/tc-clauses",
            headers=auth_headers("sales1"),
            json={"clause_public_ids": [get_seeded_tc_clause_public_id("TRANS-TC-001")]},
        )
        assert attached.status_code == 201
        attachment_public_id = attached.json()["tc_clauses"][0]["public_id"]
        line_public_id = create_test_offer_line(offer_public_id)["public_id"]
        assert mark_test_commercial_offer_submitted(offer_public_id)["offer_status_code"] == "SUBMITTED"

        record_test_customer_response(offer_public_id, "ACCEPTED_AWARDED", received_at="2026-07-12T09:00:00Z")
        lines_before = client.get(f"{base}/lines", headers=auth_headers("sales1")).json()
        evidence_before = client.get(f"{base}/pricing-evidence", headers=auth_headers("sales1")).json()
        events_before = count_commercial_offer_business_events(offer_public_id)
        attachments_before = count_active_commercial_offer_tc_attachments(offer_public_id)

        refused_writes = [
            ("post", f"{base}/lines", {"scope_description": "Added after the award", "quantity": "1.00", "uom": "job"}),
            ("put", f"{base}/lines/{line_public_id}", {"expected_row_version": line_row_version(line_public_id), "rate_amount": "99999.00"}),
            ("post", f"{base}/pricing-evidence", {**market_rate, "line_public_id": rate_line["public_id"]}),
            ("post", f"{base}/pricing-evidence/{rate_public_id}/select-basis", {"selection_reason": "After the award."}),
            ("post", f"{base}/tc-clauses", {"clause_public_ids": [get_seeded_tc_clause_public_id("TRANS-TC-001")]}),
            ("delete", f"{base}/tc-clauses/{attachment_public_id}", None),
            ("post", f"{base}/credit-review", {"review_status": "APPROVED", "reviewed_at": "2026-07-13T10:00:00Z"}),
            ("post", f"{base}/submission-evidence", {
                "submission_reference": f"SUB-AFTER-{uuid4()}",
                "submission_channel": "EMAIL",
                "submitted_at": "2026-07-13T10:00:00Z",
            }),
        ]
        for method, url, body in refused_writes:
            kwargs = {"headers": auth_headers("sales1")}
            if body is not None:
                kwargs["json"] = body
            refused = getattr(client, method)(url, **kwargs)
            assert refused.status_code == 422, (method, url, refused.status_code, refused.text)
            assert "can no longer change" in refused.json()["detail"], (method, url)

        assert client.get(f"{base}/lines", headers=auth_headers("sales1")).json() == lines_before
        assert client.get(f"{base}/pricing-evidence", headers=auth_headers("sales1")).json() == evidence_before
        assert count_active_commercial_offer_tc_attachments(offer_public_id) == attachments_before
        assert count_commercial_offer_business_events(offer_public_id) == events_before

        other_opportunity_public_id = str(create_test_opportunity()["public_id"])
        opportunity_public_ids.append(other_opportunity_public_id)
        withdrawn_offer_public_id = str(create_test_commercial_offer(other_opportunity_public_id)["public_id"])
        offer_public_ids.append(withdrawn_offer_public_id)
        withdrawn = client.put(
            f"/api/commercial-offers/{withdrawn_offer_public_id}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(withdrawn_offer_public_id), "offer_status_code": "WITHDRAWN"},
        )
        assert withdrawn.status_code == 200
        refused_line = client.post(
            f"/api/commercial-offers/{withdrawn_offer_public_id}/lines",
            headers=auth_headers("sales1"),
            json={"scope_description": "Added after withdrawal", "quantity": "1.00", "uom": "job"},
        )
        assert refused_line.status_code == 422
        assert "This Commercial Offer is Withdrawn" in refused_line.json()["detail"]
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_generic_update_cannot_enter_accepted_or_rejected_but_customer_response_still_can() -> None:
    """Slice 6M.1 completion: general update must reject SUBMITTED -> ACCEPTED and
    SUBMITTED -> REJECTED with no side effects, while the dedicated Slice 6L Customer
    Response action must still be able to record both outcomes, without auto-creating a
    Work Order, and the derived lifecycle guidance must reflect the real state."""
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []

    try:
        # --- ACCEPTED entry guard -------------------------------------------------
        accept_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(accept_context["lead"]["public_id"]))
        account_public_ids.append(str(accept_context["account"]["public_id"]))
        accept_opportunity_public_id = str(accept_context["opportunity"]["public_id"])
        opportunity_public_ids.append(accept_opportunity_public_id)
        accept_offer = create_test_commercial_offer(accept_opportunity_public_id)
        accept_offer_public_id = str(accept_offer["public_id"])
        offer_public_ids.append(accept_offer_public_id)
        mark_test_commercial_offer_submitted(accept_offer_public_id)

        events_before = count_commercial_offer_business_events(accept_offer_public_id)
        responses_before = client.get(
            f"/api/commercial-offers/{accept_offer_public_id}/customer-responses",
            headers=auth_headers("sales1"),
        ).json()
        assert responses_before == []

        blocked_accept = client.put(
            f"/api/commercial-offers/{accept_offer_public_id}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(accept_offer_public_id), "offer_status_code": "ACCEPTED"},
        )
        assert blocked_accept.status_code == 422
        assert "cannot be set to ACCEPTED" in blocked_accept.json()["detail"]
        assert "Customer Response" in blocked_accept.json()["detail"]

        # No side effects from the rejected generic update.
        assert count_commercial_offer_business_events(accept_offer_public_id) == events_before
        assert client.get(
            f"/api/commercial-offers/{accept_offer_public_id}/customer-responses",
            headers=auth_headers("sales1"),
        ).json() == []
        still_submitted = client.get(
            f"/api/commercial-offers/{accept_offer_public_id}",
            headers=auth_headers("sales1"),
        ).json()
        assert still_submitted["offer_status_code"] == "SUBMITTED"

        offer_count_before, work_order_count_before = count_offers_and_work_orders(accept_offer_public_id)
        assert work_order_count_before == 0

        # The dedicated Customer Response action still works.
        award_response = record_test_customer_response(
            accept_offer_public_id, "ACCEPTED_AWARDED", received_at="2026-07-12T09:00:00Z"
        )
        assert award_response["event"]["event_name"] == "CommercialOfferCustomerResponseRecorded"
        assert count_commercial_offer_business_events_by_name(
            accept_offer_public_id, "CommercialOfferCustomerResponseRecorded"
        ) == 1
        accepted_offer = client.get(
            f"/api/commercial-offers/{accept_offer_public_id}",
            headers=auth_headers("sales1"),
        ).json()
        assert accepted_offer["offer_status_code"] == "ACCEPTED"

        # Recording ACCEPTED_AWARDED must not auto-create a Work Order.
        offer_count_after, work_order_count_after = count_offers_and_work_orders(accept_offer_public_id)
        assert offer_count_after == offer_count_before
        assert work_order_count_after == 0

        # Once ACCEPTED, generic update cannot move it away either.
        blocked_leave = client.put(
            f"/api/commercial-offers/{accept_offer_public_id}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(accept_offer_public_id), "offer_status_code": "DRAFT"},
        )
        assert blocked_leave.status_code == 422
        assert "Commercial Offer status ACCEPTED is final" in blocked_leave.json()["detail"]

        # Derived lifecycle guidance reflects the real, correctly-reached state.
        accept_guidance = client.get(
            f"/api/commercial-offers/{accept_offer_public_id}/lifecycle-guidance",
            headers=auth_headers("sales1"),
        ).json()
        assert accept_guidance["lifecycle_state"] == "ACCEPTED_READY_FOR_HANDOFF"
        assert accept_guidance["work_order_handoff_available"] is True

        # --- REJECTED entry guard ---------------------------------------------------
        reject_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(reject_context["lead"]["public_id"]))
        account_public_ids.append(str(reject_context["account"]["public_id"]))
        reject_opportunity_public_id = str(reject_context["opportunity"]["public_id"])
        opportunity_public_ids.append(reject_opportunity_public_id)
        reject_offer = create_test_commercial_offer(reject_opportunity_public_id)
        reject_offer_public_id = str(reject_offer["public_id"])
        offer_public_ids.append(reject_offer_public_id)
        mark_test_commercial_offer_submitted(reject_offer_public_id)

        blocked_reject = client.put(
            f"/api/commercial-offers/{reject_offer_public_id}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(reject_offer_public_id), "offer_status_code": "REJECTED"},
        )
        assert blocked_reject.status_code == 422
        assert "cannot be set to REJECTED" in blocked_reject.json()["detail"]
        assert client.get(
            f"/api/commercial-offers/{reject_offer_public_id}/customer-responses",
            headers=auth_headers("sales1"),
        ).json() == []

        reject_response = record_test_customer_response(
            reject_offer_public_id, "REJECTED_LOST", received_at="2026-07-12T09:05:00Z"
        )
        assert reject_response["event"]["event_name"] == "CommercialOfferCustomerResponseRecorded"
        rejected_offer = client.get(
            f"/api/commercial-offers/{reject_offer_public_id}",
            headers=auth_headers("sales1"),
        ).json()
        assert rejected_offer["offer_status_code"] == "REJECTED"

        reject_guidance = client.get(
            f"/api/commercial-offers/{reject_offer_public_id}/lifecycle-guidance",
            headers=auth_headers("sales1"),
        ).json()
        assert reject_guidance["lifecycle_state"] == "REJECTED_CLOSED"
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_sales_and_operations_can_capture_pricing_evidence_and_select_basis() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        rate_line = create_test_offer_line(commercial_offer_public_id)
        market_rate_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/pricing-evidence",
            headers=auth_headers("ops1"),
            json={
                "line_public_id": rate_line["public_id"],
                "evidence_type": "market_rate",
                "source_name": "ABC Crane Vendor",
                "vendor_contact": "ops-rate-desk",
                "equipment_service_description": "80T crane day shift with operator",
                "rate_amount": "95000.00",
                "currency_code": "INR",
                "rate_basis": "per_day",
                "collected_by_name": "Operations User",
                "collected_at": "2026-08-03T10:30:00Z",
                "source_reference": "Phone quote",
                "comparison_notes": "Available within 24 hours.",
            },
        )
        assert market_rate_response.status_code == 201
        market_rate_body = market_rate_response.json()
        market_rate = market_rate_body["pricing_evidence"]
        assert market_rate["evidence_type"] == "market_rate"
        assert market_rate["is_selected_basis"] is False
        assert market_rate_body["events"][0]["event_name"] == "CommercialOfferMarketRateAdded"

        historical_rate_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/pricing-evidence",
            headers=auth_headers("sales1"),
            json={
                "line_public_id": rate_line["public_id"],
                "evidence_type": "historical_plum_rate",
                "source_name": "Plum historical extraction",
                "equipment_service_description": "Similar 80T crane requirement",
                "rate_amount": "89000.00",
                "currency_code": "INR",
                "rate_basis": "per_day",
                "source_reference": "PLUM-HIST-TEST",
                "comparison_notes": "Older job with different availability risk.",
            },
        )
        assert historical_rate_response.status_code == 201
        assert historical_rate_response.json()["events"][0]["event_name"] == "CommercialOfferHistoricalRateAdded"

        select_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/pricing-evidence/{market_rate['public_id']}/select-basis",
            headers=auth_headers("sales1"),
            json={"selection_reason": "Selected for availability and matching scope, not because it is the lowest rate."},
        )
        assert select_response.status_code == 200
        selected = select_response.json()["pricing_evidence"]
        assert selected["public_id"] == market_rate["public_id"]
        assert selected["is_selected_basis"] is True
        assert select_response.json()["event"]["event_name"] == "CommercialOfferBasisRateSelected"
        assert select_response.json()["event"]["event_payload"]["line_public_id"] == rate_line["public_id"]
        assert select_response.json()["event"]["event_payload"]["line_number"] == rate_line["line_number"]
        assert market_rate["line_public_id"] == rate_line["public_id"]
        assert market_rate_body["events"][0]["event_payload"]["line_public_id"] == rate_line["public_id"]

        list_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/pricing-evidence",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200
        evidence_rows = list_response.json()
        assert len(evidence_rows) == 2
        assert sum(1 for item in evidence_rows if item["is_selected_basis"] is True) == 1
        assert "password" not in str(evidence_rows).lower()
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_finance_user_can_view_but_cannot_add_pricing_evidence() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        list_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/pricing-evidence",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200

        create_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/pricing-evidence",
            headers=auth_headers("finance1"),
            json={
                "evidence_type": "market_rate",
                "equipment_service_description": "Finance should not add this",
                "rate_amount": "100.00",
                "currency_code": "INR",
                "rate_basis": "per_day",
            },
        )
        assert create_response.status_code == 403
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_pricing_evidence_rejects_invalid_type_amount_and_basis_selection() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        invalid_type_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/pricing-evidence",
            headers=auth_headers("sales1"),
            json={
                "evidence_type": "unknown",
                "equipment_service_description": "Invalid type",
                "rate_amount": "100.00",
                "currency_code": "INR",
                "rate_basis": "per_day",
            },
        )
        assert invalid_type_response.status_code == 422

        invalid_amount_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/pricing-evidence",
            headers=auth_headers("sales1"),
            json={
                "evidence_type": "market_rate",
                "equipment_service_description": "Invalid amount",
                "rate_amount": "-1.00",
                "currency_code": "INR",
                "rate_basis": "per_day",
            },
        )
        assert invalid_amount_response.status_code == 422

        selected_without_reason_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/pricing-evidence",
            headers=auth_headers("sales1"),
            json={
                "evidence_type": "market_rate",
                "equipment_service_description": "Selected without reason",
                "rate_amount": "100.00",
                "currency_code": "INR",
                "rate_basis": "per_day",
                "is_selected_basis": True,
            },
        )
        assert selected_without_reason_response.status_code == 422

        missing_evidence_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/pricing-evidence/{uuid4()}/select-basis",
            headers=auth_headers("sales1"),
            json={"selection_reason": "Missing record."},
        )
        assert missing_evidence_response.status_code == 404
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_sales_user_can_add_list_and_update_commercial_offer_lines() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        create_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines",
            headers=auth_headers("sales1"),
            json={
                "scope_description": "80T crane hiring for customer site",
                "equipment_service_category": "Crane hire",
                "quantity": "2.00",
                "uom": "day",
                "rate_amount": "95000.00",
                "currency_code": "INR",
                "remarks": "Foundation line only; no GST or T&C engine yet.",
            },
        )
        assert create_response.status_code == 201
        body = create_response.json()
        offer_line = body["offer_line"]
        assert offer_line["commercial_offer_public_id"] == commercial_offer_public_id
        assert offer_line["line_number"] == 1
        assert offer_line["line_status_code"] == "ACTIVE"
        assert str(offer_line["line_amount"]) in {"190000.00", "190000.0", "190000"}
        assert body["event"]["event_name"] == "CommercialOfferLineAdded"
        assert "password" not in str(body).lower()

        list_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200
        lines = list_response.json()
        assert any(line["public_id"] == offer_line["public_id"] for line in lines)

        update_response = client.put(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines/{offer_line['public_id']}",
            headers=auth_headers("sales1"),
            json={
                "expected_row_version": line_row_version(offer_line['public_id']),
                "scope_description": "80T crane hiring for customer site - revised scope",
                "quantity": "3.00",
                "rate_amount": "90000.00",
                "uom": "day",
                "remarks": "Updated by Slice 4E foundation test.",
            },
        )
        assert update_response.status_code == 200
        updated_line = update_response.json()["offer_line"]
        assert updated_line["scope_description"].endswith("revised scope")
        assert str(updated_line["line_amount"]) in {"270000.00", "270000.0", "270000"}
        assert update_response.json()["event"]["event_name"] == "CommercialOfferLineUpdated"
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_finance_user_can_view_but_cannot_add_or_update_commercial_offer_lines() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        create_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines",
            headers=auth_headers("sales1"),
            json={
                "scope_description": "Finance permission test line",
                "quantity": "1.00",
                "uom": "unit",
                "rate_amount": "100.00",
            },
        )
        assert create_response.status_code == 201
        offer_line = create_response.json()["offer_line"]

        list_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200

        blocked_create = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines",
            headers=auth_headers("finance1"),
            json={"scope_description": "Finance should not add", "quantity": "1.00", "uom": "unit"},
        )
        assert blocked_create.status_code == 403

        blocked_update = client.put(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines/{offer_line['public_id']}",
            headers=auth_headers("finance1"),
            json={"expected_row_version": line_row_version(offer_line['public_id']), "scope_description": "Finance should not update"},
        )
        assert blocked_update.status_code == 403
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_commercial_offer_line_rejects_invalid_inputs_and_missing_line() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        blank_scope = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines",
            headers=auth_headers("sales1"),
            json={"scope_description": "", "quantity": "1.00", "uom": "unit"},
        )
        assert blank_scope.status_code == 422

        negative_rate = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines",
            headers=auth_headers("sales1"),
            json={"scope_description": "Invalid rate", "quantity": "1.00", "uom": "unit", "rate_amount": "-1.00"},
        )
        assert negative_rate.status_code == 422

        zero_quantity = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines",
            headers=auth_headers("sales1"),
            json={"scope_description": "Invalid quantity", "quantity": "0.00", "uom": "unit"},
        )
        assert zero_quantity.status_code == 422

        missing_line = client.put(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines/{uuid4()}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": line_row_version(uuid4()), "scope_description": "Missing line"},
        )
        assert missing_line.status_code == 404
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_sales_user_can_attach_list_and_snapshot_commercial_offer_tc_clause() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    clause_public_id = get_seeded_tc_clause_public_id("TRANS-TC-001")
    original_title = ""
    original_text = ""

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        attach_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("sales1"),
            json={"clause_public_ids": [clause_public_id]},
        )
        assert attach_response.status_code == 201
        body = attach_response.json()
        attachments = body["tc_clauses"]
        assert len(attachments) == 1
        attachment = attachments[0]
        assert attachment["commercial_offer_public_id"] == commercial_offer_public_id
        assert attachment["tc_clause_public_id"] == clause_public_id
        assert attachment["clause_id_snapshot"] == "TRANS-TC-001"
        assert attachment["title_snapshot"] == "Transportation Charges And GST"
        assert "GST is extra" in attachment["clause_text_snapshot"]
        assert attachment["mandatory_default_snapshot"] is True
        assert attachment["applies_to_header_snapshot"] is True
        assert body["events"][0]["event_name"] == "CommercialOfferTcClauseAttached"
        assert body["events"][0]["record_public_id"] == commercial_offer_public_id

        with SessionLocal() as db:
            row = db.execute(
                text(
                    """
                    SELECT title, clause_text
                    FROM tc_clause_library
                    WHERE public_id = :public_id
                    """
                ),
                {"public_id": clause_public_id},
            ).first()
            assert row is not None
            original_title = row._mapping["title"]
            original_text = row._mapping["clause_text"]
            db.execute(
                text(
                    """
                    UPDATE tc_clause_library
                    SET title = :title,
                        clause_text = :clause_text,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE public_id = :public_id
                    """
                ),
                {
                    "public_id": clause_public_id,
                    "title": "Changed master title for snapshot test",
                    "clause_text": "Changed master text for snapshot test.",
                },
            )
            db.commit()

        list_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200
        listed = list_response.json()
        assert len(listed) == 1
        assert listed[0]["public_id"] == attachment["public_id"]
        assert listed[0]["title_snapshot"] == "Transportation Charges And GST"
        assert "GST is extra" in listed[0]["clause_text_snapshot"]
    finally:
        if original_title and original_text:
            with SessionLocal() as db:
                db.execute(
                    text(
                        """
                        UPDATE tc_clause_library
                        SET title = :title,
                            clause_text = :clause_text,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE public_id = :public_id
                        """
                    ),
                    {"public_id": clause_public_id, "title": original_title, "clause_text": original_text},
                )
                db.commit()
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_commercial_offer_tc_clause_duplicate_missing_inactive_and_unauthorized_paths() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    active_clause_public_id = get_seeded_tc_clause_public_id("TRANS-TC-004")
    inactive_clause_public_id = get_seeded_tc_clause_public_id("HIRE-TC-007")

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        finance_attach_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("finance1"),
            json={"clause_public_ids": [active_clause_public_id]},
        )
        assert finance_attach_response.status_code == 403

        attach_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("sales1"),
            json={"clause_public_ids": [active_clause_public_id]},
        )
        assert attach_response.status_code == 201
        attachment = attach_response.json()["tc_clauses"][0]

        duplicate_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("sales1"),
            json={"clause_public_ids": [active_clause_public_id]},
        )
        assert duplicate_response.status_code == 422
        assert "already attached" in duplicate_response.json()["detail"]

        missing_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("sales1"),
            json={"clause_public_ids": [str(uuid4())]},
        )
        assert missing_response.status_code == 404

        with SessionLocal() as db:
            db.execute(
                text("UPDATE tc_clause_library SET active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE public_id = :public_id"),
                {"public_id": inactive_clause_public_id},
            )
            db.commit()

        inactive_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("sales1"),
            json={"clause_public_ids": [inactive_clause_public_id]},
        )
        assert inactive_response.status_code == 422
        assert "Only active" in inactive_response.json()["detail"]

        finance_remove_response = client.delete(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses/{attachment['public_id']}",
            headers=auth_headers("finance1"),
        )
        assert finance_remove_response.status_code == 403

        remove_response = client.delete(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses/{attachment['public_id']}",
            headers=auth_headers("sales1"),
        )
        assert remove_response.status_code == 200
        assert remove_response.json()["tc_clause"]["active"] is False
        assert remove_response.json()["event"]["event_name"] == "CommercialOfferTcClauseRemoved"

        list_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("sales1"),
        )
        assert list_response.status_code == 200
        assert list_response.json() == []
    finally:
        with SessionLocal() as db:
            db.execute(
                text("UPDATE tc_clause_library SET active = TRUE, updated_at = CURRENT_TIMESTAMP WHERE public_id = :public_id"),
                {"public_id": inactive_clause_public_id},
            )
            db.commit()
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_commercial_offer_tc_clause_rejects_line_only_clause_for_header_attachment() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    line_only_clause_public_id = get_seeded_tc_clause_public_id("HIRE-TC-004")

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("sales1"),
            json={"clause_public_ids": [line_only_clause_public_id]},
        )
        assert response.status_code == 422
        assert "header-applicable" in response.json()["detail"]
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_commercial_offer_tc_readiness_lists_recommended_header_clauses_and_statuses() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    attached_clause_public_id = get_seeded_tc_clause_public_id("TRANS-TC-001")

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        no_auth_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clause-readiness?recommendation_basis=TRANSPORTATION"
        )
        assert no_auth_response.status_code == 401

        invalid_basis_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clause-readiness?recommendation_basis=LEGAL",
            headers=auth_headers("sales1"),
        )
        assert invalid_basis_response.status_code == 422

        initial_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clause-readiness?recommendation_basis=TRANSPORTATION",
            headers=auth_headers("finance1"),
        )
        assert initial_response.status_code == 200
        readiness = initial_response.json()
        recommended_ids = {clause["clause_id"] for clause in readiness["recommended_clauses"]}
        assert readiness["recommendation_basis"] == "TRANSPORTATION"
        assert readiness["total_recommended_count"] == len(readiness["recommended_clauses"])
        assert readiness["missing_recommended_count"] == readiness["total_recommended_count"]
        assert "TRANS-TC-001" in recommended_ids
        assert "TRANS-TC-003" not in recommended_ids
        assert "TRANS-TC-008" not in recommended_ids
        assert all(clause["business_line"] == "TRANSPORTATION" for clause in readiness["recommended_clauses"])
        assert all(clause["active"] is True for clause in readiness["recommended_clauses"])
        assert all(clause["applies_to_header"] is True for clause in readiness["recommended_clauses"])

        attach_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("sales1"),
            json={"clause_public_ids": [attached_clause_public_id]},
        )
        assert attach_response.status_code == 201

        updated_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clause-readiness?business_line=transportation",
            headers=auth_headers("sales1"),
        )
        assert updated_response.status_code == 200
        updated = updated_response.json()
        attached = [clause for clause in updated["recommended_clauses"] if clause["clause_id"] == "TRANS-TC-001"]
        missing = [clause for clause in updated["recommended_clauses"] if clause["clause_id"] != "TRANS-TC-001"]
        assert attached[0]["status"] == "ATTACHED"
        assert attached[0]["attachment_public_id"] is not None
        assert all(clause["status"] == "NOT_ATTACHED" for clause in missing)
        assert updated["attached_recommended_count"] == 1
        assert updated["missing_recommended_count"] == updated["total_recommended_count"] - 1
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_commercial_offer_tc_readiness_excludes_inactive_recommended_clauses() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    clause_row = get_seeded_tc_clause_row("TRANS-TC-004")
    clause_public_id = str(clause_row["public_id"])

    try:
        with SessionLocal() as db:
            db.execute(
                text("UPDATE tc_clause_library SET active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE public_id = :public_id"),
                {"public_id": clause_public_id},
            )
            db.commit()

        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clause-readiness?recommendation_basis=TRANSPORTATION",
            headers=auth_headers("sales1"),
        )
        assert response.status_code == 200
        recommended_ids = {clause["clause_id"] for clause in response.json()["recommended_clauses"]}
        assert "TRANS-TC-004" not in recommended_ids
    finally:
        with SessionLocal() as db:
            db.execute(
                text("UPDATE tc_clause_library SET active = :active, updated_at = CURRENT_TIMESTAMP WHERE public_id = :public_id"),
                {"public_id": clause_public_id, "active": bool(clause_row["active"])},
            )
            db.commit()
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_attach_recommended_commercial_offer_tc_clauses_is_idempotent_and_preserves_snapshots() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    clause_row = get_seeded_tc_clause_row("HIRE-TC-001")
    clause_public_id = str(clause_row["public_id"])

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        first_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses/attach-recommended",
            headers=auth_headers("sales1"),
            json={"recommendation_basis": "HIRING"},
        )
        assert first_response.status_code == 200
        first_body = first_response.json()
        assert first_body["attached_count"] == first_body["readiness"]["total_recommended_count"]
        assert first_body["attached_count"] > 0
        assert len(first_body["tc_clauses"]) == first_body["attached_count"]
        assert len(first_body["events"]) == first_body["attached_count"]
        assert all(event["event_name"] == "CommercialOfferTcClauseAttached" for event in first_body["events"])
        assert first_body["readiness"]["missing_recommended_count"] == 0
        assert first_body["readiness"]["attached_optional_count"] >= 1

        second_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses/attach-recommended",
            headers=auth_headers("sales1"),
            json={"recommendation_basis": "equipment hiring"},
        )
        assert second_response.status_code == 200
        second_body = second_response.json()
        assert second_body["attached_count"] == 0
        assert second_body["tc_clauses"] == []
        assert second_body["events"] == []

        list_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("sales1"),
        )
        assert list_response.status_code == 200
        listed = list_response.json()
        assert len(listed) == first_body["attached_count"]
        assert len({attachment["tc_clause_public_id"] for attachment in listed}) == len(listed)

        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    UPDATE tc_clause_library
                    SET title = :title,
                        clause_text = :clause_text,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE public_id = :public_id
                    """
                ),
                {
                    "public_id": clause_public_id,
                    "title": "Changed master title after recommended attach",
                    "clause_text": "Changed master text after recommended attach.",
                },
            )
            db.commit()

        snapshot_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses",
            headers=auth_headers("finance1"),
        )
        assert snapshot_response.status_code == 200
        snapshot = [
            attachment
            for attachment in snapshot_response.json()
            if attachment["tc_clause_public_id"] == clause_public_id
        ][0]
        assert snapshot["title_snapshot"] == clause_row["title"]
        assert snapshot["clause_text_snapshot"] == clause_row["clause_text"]
    finally:
        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    UPDATE tc_clause_library
                    SET title = :title,
                        clause_text = :clause_text,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE public_id = :public_id
                    """
                ),
                {
                    "public_id": clause_public_id,
                    "title": clause_row["title"],
                    "clause_text": clause_row["clause_text"],
                },
            )
            db.commit()
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_attach_recommended_commercial_offer_tc_clauses_rejects_unauthorized_and_missing_basis() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        finance_readiness_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clause-readiness?recommendation_basis=HIRING",
            headers=auth_headers("finance1"),
        )
        assert finance_readiness_response.status_code == 200

        finance_attach_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses/attach-recommended",
            headers=auth_headers("finance1"),
            json={"recommendation_basis": "HIRING"},
        )
        assert finance_attach_response.status_code == 403

        missing_basis_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/tc-clauses/attach-recommended",
            headers=auth_headers("sales1"),
            json={},
        )
        assert missing_basis_response.status_code == 422
        assert "Recommendation basis is required" in missing_basis_response.json()["detail"]
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_sales_user_can_create_and_list_commercial_offer_submission_evidence() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []

    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        event_count_before = count_commercial_offer_business_events_by_name(
            commercial_offer_public_id,
            "CommercialOfferSubmissionEvidenceRecorded",
        )

        create_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
            headers=auth_headers("sales1"),
            json={
                "submission_reference": "EMAIL-6I-001",
                "submission_channel": "EMAIL",
                "submitted_at": "2026-07-09T10:15:00Z",
                "recipient_summary": "procurement@example.test and project sponsor",
                "submitted_version_snapshot": "foundation-v1",
                "document_reference_label": "Customer email metadata",
                "document_reference_url_or_path": "Outlook reference MSG-6I-001",
                "evidence_notes": "Commercial Offer shared with the customer for Slice 6I evidence test.",
            },
        )

        assert create_response.status_code == 201
        body = create_response.json()
        evidence = body["submission_evidence"]
        assert body["event"]["event_name"] == "CommercialOfferSubmissionEvidenceRecorded"
        assert body["event"]["record_public_id"] == commercial_offer_public_id
        assert evidence["commercial_offer_public_id"] == commercial_offer_public_id
        assert evidence["submission_reference"] == "EMAIL-6I-001"
        assert evidence["submission_channel"] == "EMAIL"
        assert evidence["recipient_summary"] == "procurement@example.test and project sponsor"
        assert evidence["submitted_amount_snapshot"] == str(commercial_offer["offer_value"])
        assert evidence["submitted_currency_snapshot"] == commercial_offer["currency_code"]
        assert evidence["submitted_version_snapshot"] == "foundation-v1"
        assert evidence["document_reference_label"] == "Customer email metadata"
        assert evidence["document_reference_url_or_path"] == "Outlook reference MSG-6I-001"
        assert evidence["active"] is True
        assert count_commercial_offer_business_events_by_name(
            commercial_offer_public_id,
            "CommercialOfferSubmissionEvidenceRecorded",
        ) == event_count_before + 1

        second_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
            headers=auth_headers("sales1"),
            json={
                "submission_reference": "PORTAL-6I-002",
                "submission_channel": "TENDER_PORTAL",
                "submitted_at": "2026-07-09T11:30:00Z",
                "recipient_summary": "Tender portal submission metadata",
            },
        )
        assert second_response.status_code == 201

        read_event_count_before = count_commercial_offer_business_events(commercial_offer_public_id)
        list_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
            headers=auth_headers("readonly1"),
        )
        assert list_response.status_code == 200
        evidence_rows = list_response.json()
        assert len(evidence_rows) == 2
        assert evidence_rows[0]["submission_reference"] == "PORTAL-6I-002"
        assert evidence_rows[1]["submission_reference"] == "EMAIL-6I-001"
        assert count_commercial_offer_business_events(commercial_offer_public_id) == read_event_count_before
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_commercial_offer_submission_evidence_missing_and_permission_paths() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        list_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200
        assert list_response.json() == []

        finance_create_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
            headers=auth_headers("finance1"),
            json={
                "submission_channel": "EMAIL",
                "submitted_at": "2026-07-09T10:15:00Z",
            },
        )
        assert finance_create_response.status_code == 403

        missing_response = client.get(
            f"/api/commercial-offers/{uuid4()}/submission-evidence",
            headers=auth_headers("sales1"),
        )
        assert missing_response.status_code == 404

        invalid_channel_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
            headers=auth_headers("sales1"),
            json={
                "submission_channel": "FAX",
                "submitted_at": "2026-07-09T10:15:00Z",
            },
        )
        assert invalid_channel_response.status_code == 422
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_sales_user_can_create_list_and_supersede_commercial_offer_credit_reviews() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)
        original_status = commercial_offer["offer_status_code"]

        event_count_before = count_commercial_offer_business_events_by_name(
            commercial_offer_public_id,
            "CommercialOfferCreditReviewRecorded",
        )
        first_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/credit-review",
            headers=auth_headers("sales1"),
            json={
                "review_status": "APPROVAL_REQUIRED",
                "review_basis": "Manual Account and PAN-level profile review",
                "review_reference": "FIN-NOTE-6I2-001",
                "reviewed_at": "2026-07-10T10:15:00Z",
                "approved_amount_snapshot": "500000.00",
                "credit_days_snapshot": 30,
                "exposure_note": "Manual readiness evidence only; no exposure calculation performed.",
            },
        )
        assert first_response.status_code == 201
        first_body = first_response.json()
        first_review = first_body["credit_review"]
        assert first_body["event"]["event_name"] == "CommercialOfferCreditReviewRecorded"
        assert first_body["event"]["record_public_id"] == commercial_offer_public_id
        assert first_review["review_status"] == "APPROVAL_REQUIRED"
        assert first_review["review_reference"] == "FIN-NOTE-6I2-001"
        assert first_review["approved_amount_snapshot"] == "500000.00"
        assert first_review["credit_days_snapshot"] == 30
        assert first_review["active"] is True

        second_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/credit-review",
            headers=auth_headers("manager1"),
            json={
                "review_status": "APPROVED_WITH_REFERENCE",
                "review_basis": "Finance email approval",
                "review_reference": "FIN-EMAIL-6I2-002",
                "reviewed_at": "2026-07-10T11:30:00Z",
                "approved_amount_snapshot": "750000.00",
                "credit_days_snapshot": 45,
            },
        )
        assert second_response.status_code == 201
        assert count_commercial_offer_business_events_by_name(
            commercial_offer_public_id,
            "CommercialOfferCreditReviewRecorded",
        ) == event_count_before + 2

        read_event_count_before = count_commercial_offer_business_events(commercial_offer_public_id)
        list_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/credit-review",
            headers=auth_headers("readonly1"),
        )
        assert list_response.status_code == 200
        reviews = list_response.json()
        assert len(reviews) == 2
        assert reviews[0]["review_status"] == "APPROVED_WITH_REFERENCE"
        assert reviews[0]["active"] is True
        assert reviews[1]["review_status"] == "APPROVAL_REQUIRED"
        assert reviews[1]["active"] is False
        assert count_commercial_offer_business_events(commercial_offer_public_id) == read_event_count_before

        offer_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}",
            headers=auth_headers("sales1"),
        )
        assert offer_response.status_code == 200
        assert offer_response.json()["offer_status_code"] == original_status
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_commercial_offer_credit_review_missing_permission_and_validation_paths() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        empty_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/credit-review",
            headers=auth_headers("finance1"),
        )
        assert empty_response.status_code == 200
        assert empty_response.json() == []

        finance_create_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/credit-review",
            headers=auth_headers("finance1"),
            json={"review_status": "NOT_ASSESSED", "reviewed_at": "2026-07-10T10:15:00Z"},
        )
        assert finance_create_response.status_code == 403

        missing_response = client.get(
            f"/api/commercial-offers/{uuid4()}/credit-review",
            headers=auth_headers("sales1"),
        )
        assert missing_response.status_code == 404

        invalid_status_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/credit-review",
            headers=auth_headers("sales1"),
            json={"review_status": "CALCULATED", "reviewed_at": "2026-07-10T10:15:00Z"},
        )
        assert invalid_status_response.status_code == 422

        missing_reference_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/credit-review",
            headers=auth_headers("sales1"),
            json={"review_status": "APPROVED_WITH_REFERENCE", "reviewed_at": "2026-07-10T10:15:00Z"},
        )
        assert missing_reference_response.status_code == 422
        assert "Review reference is required" in missing_reference_response.json()["detail"]
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_latest_credit_review_drives_advisory_submission_readiness() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)
        original_status = commercial_offer["offer_status_code"]

        missing_readiness = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-readiness",
            headers=auth_headers("sales1"),
        )
        assert missing_readiness.status_code == 200
        missing_item = {
            item["code"]: item for item in missing_readiness.json()["checklist_items"]
        }["CREDIT_EXPOSURE_REVIEW"]
        assert missing_item["status"] == "ATTENTION_REQUIRED"
        assert missing_item["evidence"]["credit_review_public_id"] is None

        readiness_cases = (
            ("WITHIN_LIMIT_AS_PER_MANUAL_REVIEW", None, "PASS"),
            ("APPROVED_WITH_REFERENCE", "FIN-APPROVAL-6I2", "PASS"),
            ("APPROVAL_REQUIRED", "FIN-PENDING-6I2", "ATTENTION_REQUIRED"),
            ("REJECTED_OR_ON_HOLD", "FIN-HOLD-6I2", "BLOCKING"),
        )
        for index, (review_status, review_reference, expected_status) in enumerate(readiness_cases, start=1):
            create_response = client.post(
                f"/api/commercial-offers/{commercial_offer_public_id}/credit-review",
                headers=auth_headers("sales1"),
                json={
                    "review_status": review_status,
                    "review_reference": review_reference,
                    "reviewed_at": f"2026-07-10T{10 + index:02d}:00:00Z",
                    "exposure_note": "Manual readiness evidence; no calculated exposure.",
                },
            )
            assert create_response.status_code == 201

            readiness_response = client.get(
                f"/api/commercial-offers/{commercial_offer_public_id}/submission-readiness",
                headers=auth_headers("sales1"),
            )
            assert readiness_response.status_code == 200
            readiness_item = {
                item["code"]: item for item in readiness_response.json()["checklist_items"]
            }["CREDIT_EXPOSURE_REVIEW"]
            assert readiness_item["status"] == expected_status
            assert readiness_item["evidence"]["review_status"] == review_status
            assert readiness_item["evidence"]["manual_review_only"] is True
            assert readiness_item["evidence"]["exposure_calculation_implemented"] is False

        offer_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}",
            headers=auth_headers("sales1"),
        )
        assert offer_response.status_code == 200
        assert offer_response.json()["offer_status_code"] == original_status
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_sales_user_can_fetch_commercial_offer_submission_readiness_with_checklist() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []

    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        line_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/lines",
            headers=auth_headers("sales1"),
            json={
                "scope_description": "Submission readiness active line",
                "equipment_service_category": "Crane hire",
                "quantity": "1.00",
                "uom": "day",
                "rate_amount": "75000.00",
                "currency_code": "INR",
            },
        )
        assert line_response.status_code == 201

        pricing_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/pricing-evidence",
            headers=auth_headers("ops1"),
            json={
                "line_public_id": line_response.json()["offer_line"]["public_id"],
                "evidence_type": "market_rate",
                "equipment_service_description": "Submission readiness pricing evidence",
                "rate_amount": "75000.00",
                "currency_code": "INR",
                "rate_basis": "per_day",
                "is_selected_basis": True,
                "selection_reason": "The only quote, and the vendor confirmed availability.",
            },
        )
        assert pricing_response.status_code == 201

        evidence_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
            headers=auth_headers("sales1"),
            json={
                "submission_reference": "READINESS-6I-001",
                "submission_channel": "EMAIL",
                "submitted_at": "2026-07-09T10:15:00Z",
                "recipient_summary": "Customer commercial contact",
            },
        )
        assert evidence_response.status_code == 201

        event_count_before = count_commercial_offer_business_events(commercial_offer_public_id)
        tc_attachment_count_before = count_active_commercial_offer_tc_attachments(commercial_offer_public_id)

        response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-readiness?recommendation_basis=HIRING",
            headers=auth_headers("sales1"),
        )
        assert response.status_code == 200
        body = response.json()
        items = {item["code"]: item for item in body["checklist_items"]}

        assert body["commercial_offer_public_id"] == commercial_offer_public_id
        assert body["readiness_status"] == "ATTENTION_REQUIRED"
        assert body["summary"]["passed_count"] >= 5
        assert body["summary"]["warning_count"] >= 1
        # Slice 9E removed QUOTE_DOCUMENT_GENERATION from the deferred set (it now implements
        # quote document generation as a real, non-deferred checklist row) and added two new
        # advisory rows, QUOTATION_DOCUMENT and INTERACTION_LOG - see the assertions below.
        assert body["summary"]["deferred_count"] == 2
        assert items["COMMERCIAL_OFFER_ACTIONABLE"]["status"] == "PASS"
        assert items["ACCOUNT_TRACEABILITY"]["status"] == "PASS"
        assert items["ACCOUNT_TRACEABILITY"]["evidence"]["account_public_id"] == linked_context["account"]["public_id"]
        assert items["OPPORTUNITY_TRACEABILITY"]["status"] == "PASS"
        assert items["OPPORTUNITY_TRACEABILITY"]["evidence"]["opportunity_public_id"] == opportunity_public_id
        assert items["COMMERCIAL_OFFER_LINES"]["status"] == "PASS"
        assert items["COMMERCIAL_OFFER_LINES"]["evidence"]["active_line_count"] == 1
        assert items["PRICING_EVIDENCE"]["status"] == "PASS"
        assert items["PRICING_EVIDENCE"]["evidence"]["pricing_evidence_count"] == 1
        assert items["SUBMISSION_EVIDENCE"]["status"] == "PASS"
        assert items["SUBMISSION_EVIDENCE"]["evidence"]["submission_evidence_count"] == 1
        assert items["HEADER_TC_READINESS"]["status"] == "ATTENTION_REQUIRED"
        assert items["HEADER_TC_READINESS"]["evidence"]["recommendation_basis"] == "HIRING"
        assert items["HEADER_TC_READINESS"]["evidence"]["missing_recommended_count"] > 0
        assert items["CREDIT_EXPOSURE_REVIEW"]["status"] == "ATTENTION_REQUIRED"
        assert items["CREDIT_EXPOSURE_REVIEW"]["evidence"]["manual_review_only"] is True
        assert items["APPROVAL_WORKFLOW"]["deferred"] is True
        assert items["SUBMISSION_PROOF_UPLOAD"]["deferred"] is True
        # Slice 9E: no quote document has been generated in this scenario, so this is a real
        # advisory ATTENTION_REQUIRED row, not a deferred placeholder.
        assert items["QUOTATION_DOCUMENT"]["status"] == "ATTENTION_REQUIRED"
        assert items["QUOTATION_DOCUMENT"]["deferred"] is False
        assert items["INTERACTION_LOG"]["status"] == "ATTENTION_REQUIRED"

        assert count_commercial_offer_business_events(commercial_offer_public_id) == event_count_before
        assert count_active_commercial_offer_tc_attachments(commercial_offer_public_id) == tc_attachment_count_before
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_commercial_offer_submission_readiness_missing_basis_and_blocking_items() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-readiness",
            headers=auth_headers("finance1"),
        )
        assert response.status_code == 200
        body = response.json()
        items = {item["code"]: item for item in body["checklist_items"]}

        assert body["readiness_status"] == "NOT_READY"
        assert body["summary"]["blocking_count"] >= 2
        assert items["ACCOUNT_TRACEABILITY"]["status"] == "BLOCKING"
        assert "not linked to an Account" in items["ACCOUNT_TRACEABILITY"]["message"]
        assert items["OPPORTUNITY_TRACEABILITY"]["status"] == "PASS"
        assert items["COMMERCIAL_OFFER_LINES"]["status"] == "BLOCKING"
        assert items["SUBMISSION_EVIDENCE"]["status"] == "ATTENTION_REQUIRED"
        assert items["SUBMISSION_EVIDENCE"]["evidence"]["submission_evidence_count"] == 0
        assert items["HEADER_TC_READINESS"]["status"] == "ATTENTION_REQUIRED"
        assert items["HEADER_TC_READINESS"]["evidence"]["recommendation_basis"] is None
        assert "Select a recommendation basis" in items["HEADER_TC_READINESS"]["message"]
        assert items["CREDIT_EXPOSURE_REVIEW"]["status"] == "ATTENTION_REQUIRED"
        assert "has not yet been recorded" in items["CREDIT_EXPOSURE_REVIEW"]["message"]
        assert items["APPROVAL_WORKFLOW"]["status"] == "DEFERRED"
        assert items["SUBMISSION_PROOF_UPLOAD"]["status"] == "DEFERRED"
        # Slice 9E: real advisory rows, not deferred placeholders.
        assert items["QUOTATION_DOCUMENT"]["status"] == "ATTENTION_REQUIRED"
        assert items["INTERACTION_LOG"]["status"] == "ATTENTION_REQUIRED"
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_commercial_offer_submission_readiness_missing_unauthenticated_and_invalid_basis_paths() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity()
        opportunity_public_id = str(opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        unauthenticated_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-readiness"
        )
        assert unauthenticated_response.status_code == 401

        missing_response = client.get(
            f"/api/commercial-offers/{uuid4()}/submission-readiness",
            headers=auth_headers("sales1"),
        )
        assert missing_response.status_code == 404

        invalid_basis_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-readiness?recommendation_basis=LEGAL",
            headers=auth_headers("sales1"),
        )
        assert invalid_basis_response.status_code == 422
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


def test_new_revision_cycles_are_refused_but_existing_legacy_revisions_remain_readable() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []

    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)
        mark_test_commercial_offer_submitted(commercial_offer_public_id)
        source_evidence = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
            headers=auth_headers("sales1"),
        ).json()[0]

        offer_and_work_order_count_before = count_offers_and_work_orders(commercial_offer_public_id)
        create_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions",
            headers=auth_headers("sales1"),
            json={
                "revision_reason": "CUSTOMER_CLARIFICATION",
                "revision_notes": "Customer requested a clarification; traceability metadata only.",
                "source_submission_evidence_public_id": source_evidence["public_id"],
                "opened_at": "2026-07-11T10:00:00Z",
            },
        )
        assert create_response.status_code == 422
        assert "Make a new version" in create_response.json()["detail"]
        revision = insert_legacy_open_revision(
            commercial_offer_public_id,
            source_evidence_public_id=source_evidence["public_id"],
        )

        read_event_count_before = count_commercial_offer_business_events(commercial_offer_public_id)
        list_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions",
            headers=auth_headers("readonly1"),
        )
        assert list_response.status_code == 200
        listed_revision = list_response.json()[0]
        assert listed_revision["public_id"] == revision["public_id"]
        assert listed_revision["revision_status"] == "OPEN"
        assert listed_revision["source_submission_evidence_public_id"] == source_evidence["public_id"]
        assert count_commercial_offer_business_events(commercial_offer_public_id) == read_event_count_before

        readiness_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-readiness",
            headers=auth_headers("sales1"),
        )
        assert readiness_response.status_code == 200
        readiness_item = {
            item["code"]: item for item in readiness_response.json()["checklist_items"]
        }["REVISION_RESUBMISSION_TRACEABILITY"]
        assert readiness_item["status"] == "ATTENTION_REQUIRED"
        assert "in progress and has not been re-sent" in readiness_item["message"]
        assert readiness_item["evidence"]["hard_lifecycle_block"] is False

        offer_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}",
            headers=auth_headers("sales1"),
        )
        assert offer_response.json()["offer_status_code"] == "SUBMITTED"
        assert count_offers_and_work_orders(commercial_offer_public_id) == offer_and_work_order_count_before
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_revision_resubmission_requires_existing_evidence_and_is_single_transition() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []

    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)
        mark_test_commercial_offer_submitted(commercial_offer_public_id)

        revision_public_id = insert_legacy_open_revision(
            commercial_offer_public_id,
            reason="RATE_CORRECTION",
            label="Corrected bid",
        )["public_id"]

        second_open_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions",
            headers=auth_headers("sales1"),
            json={"revision_reason": "SCOPE_CHANGE"},
        )
        assert second_open_response.status_code == 422
        assert "Make a new version" in second_open_response.json()["detail"]

        finance_create_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions",
            headers=auth_headers("finance1"),
            json={"revision_label": "Forbidden", "revision_reason": "OTHER"},
        )
        assert finance_create_response.status_code == 403
        finance_resubmit_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions/{revision_public_id}/mark-resubmitted",
            headers=auth_headers("finance1"),
            json={"resubmission_evidence_public_id": str(uuid4())},
        )
        assert finance_resubmit_response.status_code == 403
        finance_cancel_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions/{revision_public_id}/cancel",
            headers=auth_headers("finance1"),
        )
        assert finance_cancel_response.status_code == 403

        missing_evidence_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions/{revision_public_id}/mark-resubmitted",
            headers=auth_headers("sales1"),
            json={"resubmission_evidence_public_id": str(uuid4())},
        )
        assert missing_evidence_response.status_code == 422
        assert "existing active submission evidence" in missing_evidence_response.json()["detail"]

        resubmission_evidence = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-evidence",
            headers=auth_headers("sales1"),
        ).json()[0]
        event_count_before = count_commercial_offer_business_events_by_name(
            commercial_offer_public_id,
            "CommercialOfferRevisionResubmitted",
        )
        resubmit_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions/{revision_public_id}/mark-resubmitted",
            headers=auth_headers("sales1"),
            json={"resubmission_evidence_public_id": resubmission_evidence["public_id"]},
        )
        assert resubmit_response.status_code == 200
        revision = resubmit_response.json()["revision"]
        assert revision["revision_status"] == "RESUBMITTED"
        assert revision["resubmission_evidence_public_id"] == resubmission_evidence["public_id"]
        assert revision["resubmitted_at"] is not None
        assert resubmit_response.json()["event"]["event_name"] == "CommercialOfferRevisionResubmitted"
        assert count_commercial_offer_business_events_by_name(
            commercial_offer_public_id,
            "CommercialOfferRevisionResubmitted",
        ) == event_count_before + 1

        repeated_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions/{revision_public_id}/mark-resubmitted",
            headers=auth_headers("sales1"),
            json={"resubmission_evidence_public_id": resubmission_evidence["public_id"]},
        )
        assert repeated_response.status_code == 422
        cancel_after_resubmit_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions/{revision_public_id}/cancel",
            headers=auth_headers("sales1"),
        )
        assert cancel_after_resubmit_response.status_code == 422

        readiness_response = client.get(
            f"/api/commercial-offers/{commercial_offer_public_id}/submission-readiness",
            headers=auth_headers("sales1"),
        )
        readiness_item = {
            item["code"]: item for item in readiness_response.json()["checklist_items"]
        }["REVISION_RESUBMISSION_TRACEABILITY"]
        assert readiness_item["status"] == "PASS"
        assert "has been re-sent, with evidence" in readiness_item["message"]

        next_revision_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions",
            headers=auth_headers("sales1"),
            json={"revision_reason": "SCOPE_CHANGE"},
        )
        assert next_revision_response.status_code == 422
        assert "Make a new version" in next_revision_response.json()["detail"]
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_revision_cancel_and_ineligible_status_paths() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []

    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        commercial_offer = create_test_commercial_offer(opportunity_public_id)
        commercial_offer_public_id = str(commercial_offer["public_id"])
        offer_public_ids.append(commercial_offer_public_id)

        draft_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions",
            headers=auth_headers("sales1"),
            json={"revision_label": "Too early", "revision_reason": "OTHER"},
        )
        assert draft_response.status_code == 422

        withdrawn_response = client.put(
            f"/api/commercial-offers/{commercial_offer_public_id}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(commercial_offer_public_id), "offer_status_code": "WITHDRAWN"},
        )
        assert withdrawn_response.status_code == 200
        final_status_response = client.post(
            f"/api/commercial-offers/{commercial_offer_public_id}/revisions",
            headers=auth_headers("sales1"),
            json={"revision_label": "Inactive offer", "revision_reason": "OTHER"},
        )
        assert final_status_response.status_code == 422

        missing_offer_response = client.get(
            f"/api/commercial-offers/{uuid4()}/revisions",
            headers=auth_headers("sales1"),
        )
        assert missing_offer_response.status_code == 404

        second_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(second_context["lead"]["public_id"]))
        account_public_ids.append(str(second_context["account"]["public_id"]))
        second_opportunity_public_id = str(second_context["opportunity"]["public_id"])
        opportunity_public_ids.append(second_opportunity_public_id)
        second_offer = create_test_commercial_offer(second_opportunity_public_id)
        second_offer_public_id = str(second_offer["public_id"])
        offer_public_ids.append(second_offer_public_id)
        mark_test_commercial_offer_submitted(second_offer_public_id)
        revision_public_id = insert_legacy_open_revision(
            second_offer_public_id,
            label="Clarification response 1",
        )["public_id"]

        event_count_before = count_commercial_offer_business_events_by_name(
            second_offer_public_id,
            "CommercialOfferRevisionCancelled",
        )
        cancel_response = client.post(
            f"/api/commercial-offers/{second_offer_public_id}/revisions/{revision_public_id}/cancel",
            headers=auth_headers("manager1"),
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["revision"]["revision_status"] == "CANCELLED"
        assert cancel_response.json()["revision"]["cancelled_at"] is not None
        assert cancel_response.json()["event"]["event_name"] == "CommercialOfferRevisionCancelled"
        assert count_commercial_offer_business_events_by_name(
            second_offer_public_id,
            "CommercialOfferRevisionCancelled",
        ) == event_count_before + 1

        repeated_cancel_response = client.post(
            f"/api/commercial-offers/{second_offer_public_id}/revisions/{revision_public_id}/cancel",
            headers=auth_headers("sales1"),
        )
        assert repeated_cancel_response.status_code == 422
        missing_revision_response = client.post(
            f"/api/commercial-offers/{second_offer_public_id}/revisions/{uuid4()}/cancel",
            headers=auth_headers("sales1"),
        )
        assert missing_revision_response.status_code == 404
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_customer_response_records_post_submission_traceability_without_work_order() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_id = str(offer["public_id"])
        offer_public_ids.append(offer_public_id)
        mark_test_commercial_offer_submitted(offer_public_id)
        evidence = client.get(
            f"/api/commercial-offers/{offer_public_id}/submission-evidence",
            headers=auth_headers("sales1"),
        ).json()[0]
        revision = insert_legacy_open_revision(offer_public_id)
        before_counts = count_offers_and_work_orders(offer_public_id)

        response = client.post(
            f"/api/commercial-offers/{offer_public_id}/customer-responses",
            headers=auth_headers("manager1"),
            json={
                "response_outcome": "CLARIFICATION_REQUESTED",
                "response_reference": "Customer email: clarify mobilisation",
                "response_received_at": "2026-07-12T10:30:00Z",
                "response_channel": "EMAIL",
                "received_from": "Procurement team",
                "linked_submission_evidence_public_id": evidence["public_id"],
                "linked_revision_public_id": revision["public_id"],
                "customer_response_notes": "Commercial status must remain Submitted.",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["customer_response"]["response_outcome"] == "CLARIFICATION_REQUESTED"
        assert body["customer_response"]["linked_submission_evidence_public_id"] == evidence["public_id"]
        assert body["customer_response"]["linked_revision_public_id"] == revision["public_id"]
        assert body["commercial_offer"]["offer_status_code"] == "SUBMITTED"
        assert body["event"]["event_name"] == "CommercialOfferCustomerResponseRecorded"
        assert body["event"]["event_payload"]["status_changed"] is False
        assert body["event"]["event_payload"]["work_order_created"] is False
        assert count_offers_and_work_orders(offer_public_id) == before_counts

        event_count = count_commercial_offer_business_events(offer_public_id)
        listed = client.get(
            f"/api/commercial-offers/{offer_public_id}/customer-responses",
            headers=auth_headers("readonly1"),
        )
        assert listed.status_code == 200
        assert listed.json()[0]["public_id"] == body["customer_response"]["public_id"]
        assert count_commercial_offer_business_events(offer_public_id) == event_count

        readiness = client.get(
            f"/api/commercial-offers/{offer_public_id}/submission-readiness",
            headers=auth_headers("sales1"),
        ).json()
        item = {item["code"]: item for item in readiness["checklist_items"]}[
            "CUSTOMER_RESPONSE_AWARD_OUTCOME"
        ]
        assert item["status"] == "ATTENTION_REQUIRED"
        assert item["message"] == "Customer requested revision/clarification."
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_customer_response_accepted_and_rejected_outcomes_align_offer_status() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        for outcome, expected_status in (("ACCEPTED_AWARDED", "ACCEPTED"), ("REJECTED_LOST", "REJECTED")):
            linked_context = create_account_linked_test_opportunity()
            lead_public_ids.append(str(linked_context["lead"]["public_id"]))
            account_public_ids.append(str(linked_context["account"]["public_id"]))
            opportunity_public_id = str(linked_context["opportunity"]["public_id"])
            opportunity_public_ids.append(opportunity_public_id)
            offer = create_test_commercial_offer(opportunity_public_id)
            offer_public_id = str(offer["public_id"])
            offer_public_ids.append(offer_public_id)
            mark_test_commercial_offer_submitted(offer_public_id)
            before_counts = count_offers_and_work_orders(offer_public_id)

            response = client.post(
                f"/api/commercial-offers/{offer_public_id}/customer-responses",
                headers=auth_headers("sales1"),
                json={
                    "response_outcome": outcome,
                    "response_reference": f"REF-{expected_status}",
                    "response_received_at": "2026-07-12T11:00:00Z",
                    "response_channel": "LETTER_OF_AWARD" if expected_status == "ACCEPTED" else "EMAIL",
                    "awarded_amount_snapshot": "125000.00" if expected_status == "ACCEPTED" else None,
                },
            )
            assert response.status_code == 201
            body = response.json()
            assert body["commercial_offer"]["offer_status_code"] == expected_status
            assert body["event"]["event_payload"]["previous_offer_status_code"] == "SUBMITTED"
            assert body["event"]["event_payload"]["new_offer_status_code"] == expected_status
            assert body["event"]["event_payload"]["status_changed"] is True
            assert body["event"]["event_payload"]["work_order_created"] is False
            if expected_status == "ACCEPTED":
                assert body["customer_response"]["awarded_currency_snapshot"] == "INR"
            assert count_offers_and_work_orders(offer_public_id) == before_counts
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_customer_response_validates_status_permissions_missing_offer_and_same_offer_links() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        contexts = [create_account_linked_test_opportunity(), create_account_linked_test_opportunity()]
        for context in contexts:
            lead_public_ids.append(str(context["lead"]["public_id"]))
            account_public_ids.append(str(context["account"]["public_id"]))
            opportunity_public_ids.append(str(context["opportunity"]["public_id"]))
        offers = [create_test_commercial_offer(public_id) for public_id in opportunity_public_ids]
        offer_public_ids.extend(str(offer["public_id"]) for offer in offers)
        base_payload = {
            "response_outcome": "ON_HOLD",
            "response_received_at": "2026-07-12T12:00:00Z",
            "response_channel": "MEETING",
        }

        draft_response = client.post(
            f"/api/commercial-offers/{offer_public_ids[0]}/customer-responses",
            headers=auth_headers("sales1"),
            json=base_payload,
        )
        assert draft_response.status_code == 422

        ready_update = client.put(
            f"/api/commercial-offers/{offer_public_ids[0]}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(offer_public_ids[0]), "offer_status_code": "READY_FOR_REVIEW"},
        )
        assert ready_update.status_code == 200
        ready_response = client.post(
            f"/api/commercial-offers/{offer_public_ids[0]}/customer-responses",
            headers=auth_headers("sales1"),
            json=base_payload,
        )
        assert ready_response.status_code == 422

        mark_test_commercial_offer_submitted(offer_public_ids[0])
        mark_test_commercial_offer_submitted(offer_public_ids[1])
        foreign_evidence = client.get(
            f"/api/commercial-offers/{offer_public_ids[1]}/submission-evidence",
            headers=auth_headers("sales1"),
        ).json()[0]
        cross_link_response = client.post(
            f"/api/commercial-offers/{offer_public_ids[0]}/customer-responses",
            headers=auth_headers("sales1"),
            json={**base_payload, "linked_submission_evidence_public_id": foreign_evidence["public_id"]},
        )
        assert cross_link_response.status_code == 422
        assert "for this Commercial Offer" in cross_link_response.json()["detail"]

        foreign_revision = insert_legacy_open_revision(offer_public_ids[1], reason="OTHER")
        cross_revision_response = client.post(
            f"/api/commercial-offers/{offer_public_ids[0]}/customer-responses",
            headers=auth_headers("sales1"),
            json={**base_payload, "linked_revision_public_id": foreign_revision["public_id"]},
        )
        assert cross_revision_response.status_code == 422
        assert "for this Commercial Offer" in cross_revision_response.json()["detail"]

        forbidden = client.post(
            f"/api/commercial-offers/{offer_public_ids[0]}/customer-responses",
            headers=auth_headers("readonly1"),
            json=base_payload,
        )
        assert forbidden.status_code == 403
        missing = client.post(
            f"/api/commercial-offers/{uuid4()}/customer-responses",
            headers=auth_headers("sales1"),
            json=base_payload,
        )
        assert missing.status_code == 404

        withdrawn = client.put(
            f"/api/commercial-offers/{offer_public_ids[0]}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": offer_row_version(offer_public_ids[0]), "offer_status_code": "WITHDRAWN"},
        )
        assert withdrawn.status_code == 200
        withdrawn_response = client.post(
            f"/api/commercial-offers/{offer_public_ids[0]}/customer-responses",
            headers=auth_headers("sales1"),
            json=base_payload,
        )
        assert withdrawn_response.status_code == 422
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def cleanup_test_work_orders(work_order_public_ids: list[str]) -> None:
    with SessionLocal() as db:
        for public_id in work_order_public_ids:
            # 8A core allocations reference the requirements: kit lines, trips, then the allocations -
            # a replacement's link to the one it replaced cleared first. They go with their requirements, marked as
            # the service's own write, which the database requires of any allocation write (8A-FA2-001).
            mark_service_write(db)
            for statement in (
                """
                DELETE FROM resource_assignment_kit k USING resource_assignment a
                WHERE a.id = k.resource_assignment_id AND a.work_order_public_id = :public_id
                """,
                """
                DELETE FROM resource_assignment_trip t USING resource_assignment a
                WHERE a.id = t.resource_assignment_id AND a.work_order_public_id = :public_id
                """,
                "UPDATE resource_assignment SET replaces_assignment_id = NULL WHERE work_order_public_id = :public_id",
                "DELETE FROM resource_assignment WHERE work_order_public_id = :public_id",
                """
                DELETE FROM resource_assignment_request q USING resource_requirement rr
                WHERE rr.requirement_public_id = q.resource_requirement_public_id AND rr.work_order_public_id = :public_id
                """,
            ):
                db.execute(text(statement), {"public_id": public_id})
            # WRR-001 resource requirements reference crm_work_order_line: capabilities, then items,
            # then the requirements, before the lines.
            for statement in (
                """
                DELETE FROM resource_requirement_item_capability c
                USING resource_requirement_item i, resource_requirement rr, crm_work_order_line wol,
                      crm_work_order wo
                WHERE i.id = c.resource_requirement_item_id AND rr.id = i.resource_requirement_id
                  AND wol.id = rr.work_order_line_id AND wo.id = wol.work_order_id
                  AND wo.work_order_public_id = :public_id
                """,
                """
                DELETE FROM resource_requirement_item i
                USING resource_requirement rr, crm_work_order_line wol, crm_work_order wo
                WHERE rr.id = i.resource_requirement_id AND wol.id = rr.work_order_line_id
                  AND wo.id = wol.work_order_id AND wo.work_order_public_id = :public_id
                """,
                """
                DELETE FROM resource_requirement rr
                USING crm_work_order_line wol, crm_work_order wo
                WHERE wol.id = rr.work_order_line_id AND wo.id = wol.work_order_id
                  AND wo.work_order_public_id = :public_id
                """,
            ):
                db.execute(text(statement), {"public_id": public_id})
            # Slice 7D billing terms and Slice 7C line details reference crm_work_order_line, so they go
            # first (7C review advisory).
            db.execute(
                text(
                    """
                    DELETE FROM crm_work_order_line_billing_term t
                    USING crm_work_order_line wol, crm_work_order wo
                    WHERE wol.id = t.work_order_line_id
                      AND wo.id = wol.work_order_id
                      AND wo.work_order_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM crm_work_order_line_detail d
                    USING crm_work_order_line wol, crm_work_order wo
                    WHERE wol.id = d.work_order_line_id
                      AND wo.id = wol.work_order_id
                      AND wo.work_order_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM crm_work_order_line wol
                    USING crm_work_order wo
                    WHERE wo.id = wol.work_order_id
                      AND wo.work_order_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            # Slice 7D Part 3: the contract period and its extensions reference crm_work_order
            # itself, so they go before it.
            for table in ("crm_work_order_contract_extension", "crm_work_order_contract_period"):
                db.execute(
                    text(
                        f"""
                        DELETE FROM {table} c
                        USING crm_work_order wo
                        WHERE wo.id = c.work_order_id
                          AND wo.work_order_public_id = :public_id
                        """
                    ),
                    {"public_id": public_id},
                )
            # Slice 7D Part 4: each holiday references its list, and the list the Work Order.
            db.execute(
                text(
                    """
                    DELETE FROM crm_work_order_holiday h
                    USING crm_work_order_holiday_list l, crm_work_order wo
                    WHERE l.id = h.work_order_holiday_list_id
                      AND wo.id = l.work_order_id
                      AND wo.work_order_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM crm_work_order_holiday_list l
                    USING crm_work_order wo
                    WHERE wo.id = l.work_order_id
                      AND wo.work_order_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'work_order'
                      AND record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text("DELETE FROM crm_work_order WHERE work_order_public_id = :public_id"),
                {"public_id": public_id},
            )
        db.commit()


def create_test_work_order(commercial_offer_public_id: str) -> dict[str, object]:
    response = client.post(
        "/api/work-orders/from-commercial-offer",
        headers=auth_headers("sales1"),
        json={"commercial_offer_public_id": commercial_offer_public_id, "customer_wo_reference": f"CUST-{uuid4()}"},
    )
    assert response.status_code == 201
    return response.json()["work_order"]


def create_test_supplementary_work_order(base_offer_public_id: str) -> tuple[str, dict[str, object]]:
    """Another Work Order on the same Account and Opportunity: from an accepted Supplementary Offer of the accepted
    base. Since CS-04 part 1 an offer line's quantity goes onto Work Orders once, so a test needing a second Work Order
    makes it this way rather than handing the same lines off again. Returns the Supplementary Offer's public id - clean
    it up before the base offer - and the handoff's body."""
    created = client.post(
        f"/api/commercial-offers/{base_offer_public_id}/related-offers",
        headers=auth_headers("sales1"),
        json={"offer_purpose": "SUPPLEMENTARY", "customer_request_summary": "Another Work Order, for a test."},
    )
    assert created.status_code == 201, created.text
    supplementary_public_id = str(created.json()["commercial_offer"]["public_id"])
    mark_test_commercial_offer_submitted(supplementary_public_id)
    record_test_customer_response(supplementary_public_id, "ACCEPTED_AWARDED", received_at="2026-09-14T11:00:00Z")
    response = client.post(
        "/api/work-orders/from-commercial-offer",
        headers=auth_headers("sales1"),
        json={"commercial_offer_public_id": supplementary_public_id, "customer_wo_reference": f"CUST-{uuid4()}"},
    )
    assert response.status_code == 201, response.text
    return supplementary_public_id, response.json()


def record_test_customer_response(commercial_offer_public_id: str, outcome: str, *, received_at: str) -> dict[str, object]:
    response = client.post(
        f"/api/commercial-offers/{commercial_offer_public_id}/customer-responses",
        headers=auth_headers("sales1"),
        json={
            "response_outcome": outcome,
            "response_received_at": received_at,
            "response_channel": "EMAIL",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_lifecycle_guidance_tracks_latest_customer_response_and_work_order_state() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    work_order_public_ids: list[str] = []
    try:
        linked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked_context["lead"]["public_id"]))
        account_public_ids.append(str(linked_context["account"]["public_id"]))
        opportunity_public_id = str(linked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_id = str(offer["public_id"])
        offer_public_ids.append(offer_public_id)
        mark_test_commercial_offer_submitted(offer_public_id)

        event_count_before_reads = count_commercial_offer_business_events(offer_public_id)

        guidance = client.get(
            f"/api/commercial-offers/{offer_public_id}/lifecycle-guidance",
            headers=auth_headers("sales1"),
        )
        assert guidance.status_code == 200
        body = guidance.json()
        assert body["lifecycle_state"] == "AWAITING_CUSTOMER_RESPONSE"
        assert body["latest_customer_response_outcome"] is None
        assert body["is_commercially_active"] is True
        assert body["can_open_revision"] is False
        assert body["can_make_new_version"] is True
        assert body["can_record_customer_response"] is True
        assert body["work_order_handoff_available"] is False
        assert body["linked_work_orders"] == []

        # readonly1 can also read guidance without creating an event.
        readonly_guidance = client.get(
            f"/api/commercial-offers/{offer_public_id}/lifecycle-guidance",
            headers=auth_headers("readonly1"),
        )
        assert readonly_guidance.status_code == 200
        assert count_commercial_offer_business_events(offer_public_id) == event_count_before_reads

        for outcome, expected_state in (
            ("REVISION_REQUESTED", "REVISION_REQUESTED_ACTIVE"),
            ("CLARIFICATION_REQUESTED", "CLARIFICATION_REQUESTED_ACTIVE"),
            ("ON_HOLD", "ON_HOLD_ACTIVE"),
            ("PENDING_CUSTOMER_DECISION", "PENDING_CUSTOMER_DECISION_ACTIVE"),
            ("OTHER", "OTHER_ACTIVE"),
        ):
            record_test_customer_response(offer_public_id, outcome, received_at="2026-07-13T09:00:00Z")
            guidance = client.get(
                f"/api/commercial-offers/{offer_public_id}/lifecycle-guidance",
                headers=auth_headers("sales1"),
            ).json()
            assert guidance["lifecycle_state"] == expected_state, outcome
            assert guidance["latest_customer_response_outcome"] == outcome
            assert guidance["work_order_handoff_available"] is False
            assert guidance["can_open_revision"] is False
            assert guidance["can_make_new_version"] is True
            assert guidance["can_record_customer_response"] is True

        offers_before, work_orders_before = count_offers_and_work_orders(offer_public_id)
        record_test_customer_response(offer_public_id, "ACCEPTED_AWARDED", received_at="2026-07-13T10:00:00Z")
        offers_after, work_orders_after = count_offers_and_work_orders(offer_public_id)
        assert (offers_before, work_orders_before) == (offers_after, work_orders_after)

        guidance = client.get(
            f"/api/commercial-offers/{offer_public_id}/lifecycle-guidance",
            headers=auth_headers("sales1"),
        ).json()
        assert guidance["lifecycle_state"] == "ACCEPTED_READY_FOR_HANDOFF"
        assert guidance["latest_customer_response_outcome"] == "ACCEPTED_AWARDED"
        assert guidance["is_commercially_active"] is True
        assert guidance["work_order_handoff_available"] is True
        assert guidance["work_order_handoff_blocked_reasons"] == []
        assert guidance["linked_work_orders"] == []

        work_order = create_test_work_order(offer_public_id)
        work_order_public_ids.append(str(work_order["public_id"]))

        guidance = client.get(
            f"/api/commercial-offers/{offer_public_id}/lifecycle-guidance",
            headers=auth_headers("sales1"),
        ).json()
        assert guidance["lifecycle_state"] == "ACCEPTED_WORK_ORDER_EXISTS"
        assert len(guidance["linked_work_orders"]) == 1
        assert guidance["linked_work_orders"][0]["public_id"] == work_order["public_id"]
        # The frozen contract allows one accepted offer to support additional Work Order shells for partial award, but
        # since CS-04 part 1 (its dated amendment of 8 October 2026) only for what is not on a Work Order yet: this
        # handoff took every line in full, so the view says no more can be created, as the endpoint would.
        assert guidance["work_order_handoff_available"] is False
        assert guidance["work_order_handoff_blocked_reasons"] == [
            "Every line of this offer is already on a Work Order in full."
        ]

        missing = client.get(
            f"/api/commercial-offers/{uuid4()}/lifecycle-guidance",
            headers=auth_headers("sales1"),
        )
        assert missing.status_code == 404

        unauthenticated = client.get(f"/api/commercial-offers/{offer_public_id}/lifecycle-guidance")
        assert unauthenticated.status_code == 401
    finally:
        cleanup_test_work_orders(work_order_public_ids)
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_lifecycle_guidance_rejected_closed_and_blocked_by_missing_active_lines() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        # Rejected/lost offer: closed, not commercially active, revision no longer allowed.
        rejected_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(rejected_context["lead"]["public_id"]))
        account_public_ids.append(str(rejected_context["account"]["public_id"]))
        rejected_opportunity_public_id = str(rejected_context["opportunity"]["public_id"])
        opportunity_public_ids.append(rejected_opportunity_public_id)
        rejected_offer = create_test_commercial_offer(rejected_opportunity_public_id)
        rejected_offer_public_id = str(rejected_offer["public_id"])
        offer_public_ids.append(rejected_offer_public_id)
        mark_test_commercial_offer_submitted(rejected_offer_public_id)
        record_test_customer_response(rejected_offer_public_id, "REJECTED_LOST", received_at="2026-07-13T11:00:00Z")

        rejected_guidance = client.get(
            f"/api/commercial-offers/{rejected_offer_public_id}/lifecycle-guidance",
            headers=auth_headers("sales1"),
        ).json()
        assert rejected_guidance["lifecycle_state"] == "REJECTED_CLOSED"
        assert rejected_guidance["is_commercially_active"] is False
        assert rejected_guidance["can_open_revision"] is False
        assert rejected_guidance["can_make_new_version"] is False
        # Slice 9B: a Rejected Commercial Offer is final. This asserted True until
        # 7 September 2026, which is exactly the reactivation gap that allowed a late
        # ACCEPTED_AWARDED response to drive a rejected offer back to ACCEPTED while a
        # replacement offer already existed for the same Opportunity.
        assert rejected_guidance["can_record_customer_response"] is False
        assert rejected_guidance["work_order_handoff_available"] is False

        revision_after_rejected = client.post(
            f"/api/commercial-offers/{rejected_offer_public_id}/revisions",
            headers=auth_headers("sales1"),
            json={"revision_reason": "OTHER"},
        )
        assert revision_after_rejected.status_code == 422

        work_order_after_rejected = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={"commercial_offer_public_id": rejected_offer_public_id},
        )
        assert work_order_after_rejected.status_code == 422

        # Accepted offer whose only active line is later cancelled: handoff blocked
        # even though the offer itself is Accepted, mirroring the real Work Order guard.
        # Since TB-1's TB1-301 (b) an accepted offer's lines can no longer be changed, so the
        # cancel is refused; an offer accepted before that fix may already be in this state,
        # so it is set directly and the guard is still checked.
        blocked_context = create_account_linked_test_opportunity()
        lead_public_ids.append(str(blocked_context["lead"]["public_id"]))
        account_public_ids.append(str(blocked_context["account"]["public_id"]))
        blocked_opportunity_public_id = str(blocked_context["opportunity"]["public_id"])
        opportunity_public_ids.append(blocked_opportunity_public_id)
        blocked_offer = create_test_commercial_offer(blocked_opportunity_public_id)
        blocked_offer_public_id = str(blocked_offer["public_id"])
        offer_public_ids.append(blocked_offer_public_id)
        mark_test_commercial_offer_submitted(blocked_offer_public_id)
        record_test_customer_response(blocked_offer_public_id, "ACCEPTED_AWARDED", received_at="2026-07-13T12:00:00Z")

        lines = client.get(
            f"/api/commercial-offers/{blocked_offer_public_id}/lines",
            headers=auth_headers("sales1"),
        ).json()
        assert len(lines) == 1
        cancel_line = client.put(
            f"/api/commercial-offers/{blocked_offer_public_id}/lines/{lines[0]['public_id']}",
            headers=auth_headers("sales1"),
            json={"expected_row_version": line_row_version(lines[0]['public_id']), "line_status_code": "CANCELLED"},
        )
        assert cancel_line.status_code == 422
        assert "can no longer change" in cancel_line.json()["detail"]
        with SessionLocal() as db:
            db.execute(
                text("UPDATE crm_commercial_offer_line SET line_status_code = 'CANCELLED' WHERE line_public_id = :lid"),
                {"lid": lines[0]["public_id"]},
            )
            db.commit()

        blocked_guidance = client.get(
            f"/api/commercial-offers/{blocked_offer_public_id}/lifecycle-guidance",
            headers=auth_headers("sales1"),
        ).json()
        assert blocked_guidance["lifecycle_state"] == "ACCEPTED_HANDOFF_BLOCKED"
        assert blocked_guidance["work_order_handoff_available"] is False
        assert any("at least one active line" in reason for reason in blocked_guidance["work_order_handoff_blocked_reasons"])

        work_order_blocked = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={"commercial_offer_public_id": blocked_offer_public_id},
        )
        assert work_order_blocked.status_code == 422
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )
