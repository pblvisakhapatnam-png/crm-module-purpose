from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app

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


def cleanup_test_leads(public_ids: list[str]) -> None:
    if not public_ids:
        return

    with SessionLocal() as db:
        for public_id in public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'lead_activity'
                      AND record_public_id IN (
                        SELECT a.activity_public_id
                        FROM crm_lead_activity a
                        INNER JOIN crm_lead l ON l.id = a.lead_id
                        WHERE l.lead_public_id = :public_id
                      )
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM crm_lead_activity a
                    USING crm_lead l
                    WHERE l.id = a.lead_id
                      AND l.lead_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
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


def create_test_lead(company_name: str | None = None) -> dict[str, object]:
    response = client.post(
        "/api/leads",
        headers=auth_headers("sales1"),
        json={
            "lead_source": "manual",
            "source_reference": "Manual test enquiry",
            "company_name": company_name or f"Slice 2 Lead Company {uuid4()}",
            "contact_name": "Slice 2 Contact",
            "contact_phone": "+91-9876543210",
            "contact_email": "slice2.lead@example.com",
            "requirement_summary": "Need crane and trailer movement discussion.",
            "lead_status_code": "NEW",
        },
    )
    assert response.status_code == 201
    return response.json()["lead"]


def test_leads_require_authentication() -> None:
    response = client.get("/api/leads")

    assert response.status_code == 401


def test_sales_user_can_create_list_and_get_lead() -> None:
    created_public_ids: list[str] = []
    company_name = f"Slice 2A Lead Company {uuid4()}"

    try:
        create_response = client.post(
            "/api/leads",
            headers=auth_headers("sales1"),
            json={
                "lead_source": "manual",
                "source_reference": "Manual walk-in enquiry",
                "company_name": company_name,
                "contact_name": "Slice 2A Contact",
                "contact_phone": "+91-9876543210",
                "contact_email": "slice2a.lead@example.com",
                "requirement_summary": "Need crane and trailer movement discussion.",
                "lead_status_code": "NEW",
            },
        )

        assert create_response.status_code == 201
        body = create_response.json()
        created_public_ids.append(body["lead"]["public_id"])
        assert body["lead"]["company_name"] == company_name
        assert body["lead"]["lead_source"] == "manual"
        assert body["lead"]["lead_status_code"] == "NEW"
        assert body["event"]["event_name"] == "LeadCreated"
        assert body["event"]["record_type"] == "lead"
        assert body["event"]["record_public_id"] == body["lead"]["public_id"]
        assert "password" not in str(body).lower()

        list_response = client.get(
            "/api/leads?limit=10",
            headers=auth_headers("sales1"),
        )
        assert list_response.status_code == 200
        leads = list_response.json()
        assert any(lead["public_id"] == body["lead"]["public_id"] for lead in leads)

        get_response = client.get(
            f"/api/leads/{body['lead']['public_id']}",
            headers=auth_headers("readonly1"),
        )
        assert get_response.status_code == 200
        assert get_response.json()["public_id"] == body["lead"]["public_id"]
    finally:
        cleanup_test_leads(created_public_ids)


def test_sales_user_can_update_lead_details_fields() -> None:
    created_public_ids: list[str] = []
    try:
        lead = create_test_lead()
        lead_public_id = str(lead["public_id"])
        created_public_ids.append(lead_public_id)
        assigned_to = str(uuid4())

        update_response = client.put(
            f"/api/leads/{lead_public_id}",
            headers=auth_headers("sales1"),
            json={
                "lead_source": "phone",
                "source_reference": "Follow-up call",
                "company_name": "Updated Slice 2C Lead Company",
                "contact_name": "Updated Lead Contact",
                "contact_phone": "+91-9999999999",
                "contact_email": "updated.slice2c@example.com",
                "requirement_summary": "Updated early Lead details requirement summary.",
                "lead_status_code": "CONTACTED",
                "assigned_to_user_public_id": assigned_to,
            },
        )

        assert update_response.status_code == 200
        body = update_response.json()
        assert body["lead"]["public_id"] == lead_public_id
        assert body["lead"]["company_name"] == "Updated Slice 2C Lead Company"
        assert body["lead"]["lead_source"] == "phone"
        assert body["lead"]["lead_status_code"] == "CONTACTED"
        assert body["lead"]["assigned_to_user_public_id"] == assigned_to

        event_names = {event["event_name"] for event in body["events"]}
        assert "LeadUpdated" in event_names
        assert "LeadStatusChanged" in event_names
        assert "LeadAssigned" in event_names

        get_response = client.get(
            f"/api/leads/{lead_public_id}",
            headers=auth_headers("sales1"),
        )
        assert get_response.status_code == 200
        assert get_response.json()["lead_status_code"] == "CONTACTED"
    finally:
        cleanup_test_leads(created_public_ids)


def test_sales_user_can_record_and_list_lead_activity() -> None:
    created_public_ids: list[str] = []
    try:
        lead = create_test_lead()
        lead_public_id = str(lead["public_id"])
        created_public_ids.append(lead_public_id)

        create_response = client.post(
            f"/api/leads/{lead_public_id}/activities",
            headers=auth_headers("sales1"),
            json={
                "activity_type": "CALL",
                "notes": "Spoke to customer and collected initial requirement details.",
                "outcome": "Customer will send dimensions.",
                "next_follow_up_at": "2026-07-05T10:30:00Z",
            },
        )

        assert create_response.status_code == 201
        body = create_response.json()
        assert body["activity"]["lead_public_id"] == lead_public_id
        assert body["activity"]["activity_type"] == "CALL"
        assert body["activity"]["notes"] == "Spoke to customer and collected initial requirement details."
        assert body["event"]["event_name"] == "LeadActivityRecorded"
        assert body["event"]["record_type"] == "lead_activity"
        assert body["event"]["record_public_id"] == body["activity"]["public_id"]

        list_response = client.get(
            f"/api/leads/{lead_public_id}/activities",
            headers=auth_headers("readonly1"),
        )
        assert list_response.status_code == 200
        activities = list_response.json()
        assert any(activity["public_id"] == body["activity"]["public_id"] for activity in activities)
    finally:
        cleanup_test_leads(created_public_ids)


def test_sales_user_can_record_lead_qualification_decision() -> None:
    created_public_ids: list[str] = []
    try:
        lead = create_test_lead()
        lead_public_id = str(lead["public_id"])
        created_public_ids.append(lead_public_id)

        decision_response = client.post(
            f"/api/leads/{lead_public_id}/qualification-decision",
            headers=auth_headers("sales1"),
            json={
                "decision_status_code": "QUALIFIED",
                "decision_notes": "Requirement is clear and worth pursuing.",
                "reason": "Good fit",
            },
        )

        assert decision_response.status_code == 200
        body = decision_response.json()
        assert body["lead"]["public_id"] == lead_public_id
        assert body["lead"]["lead_status_code"] == "QUALIFIED"
        assert body["lead"]["qualification_decision_notes"] == "Requirement is clear and worth pursuing."
        assert body["lead"]["qualification_reason"] == "Good fit"
        assert body["lead"]["qualification_decided_by"] is not None
        assert body["lead"]["qualification_decided_at"] is not None
        assert body["event"]["event_name"] == "LeadQualified"
        assert body["event"]["record_type"] == "lead"
        assert body["event"]["record_public_id"] == lead_public_id

        get_response = client.get(
            f"/api/leads/{lead_public_id}",
            headers=auth_headers("readonly1"),
        )
        assert get_response.status_code == 200
        assert get_response.json()["lead_status_code"] == "QUALIFIED"
        assert get_response.json()["qualification_reason"] == "Good fit"
    finally:
        cleanup_test_leads(created_public_ids)


def test_lead_qualification_decision_requires_reason_for_unqualified_or_closed() -> None:
    created_public_ids: list[str] = []
    try:
        lead = create_test_lead()
        lead_public_id = str(lead["public_id"])
        created_public_ids.append(lead_public_id)

        missing_reason_response = client.post(
            f"/api/leads/{lead_public_id}/qualification-decision",
            headers=auth_headers("sales1"),
            json={
                "decision_status_code": "UNQUALIFIED",
                "decision_notes": "Not worth pursuing.",
            },
        )
        assert missing_reason_response.status_code == 422

        closed_response = client.post(
            f"/api/leads/{lead_public_id}/qualification-decision",
            headers=auth_headers("sales1"),
            json={
                "decision_status_code": "CLOSED",
                "decision_notes": "Customer said requirement is cancelled.",
                "reason": "Requirement cancelled",
            },
        )
        assert closed_response.status_code == 200
        assert closed_response.json()["lead"]["lead_status_code"] == "CLOSED"
        assert closed_response.json()["event"]["event_name"] == "LeadClosed"
    finally:
        cleanup_test_leads(created_public_ids)


def test_finance_user_cannot_record_lead_qualification_decision() -> None:
    created_public_ids: list[str] = []
    try:
        lead = create_test_lead()
        lead_public_id = str(lead["public_id"])
        created_public_ids.append(lead_public_id)

        decision_response = client.post(
            f"/api/leads/{lead_public_id}/qualification-decision",
            headers=auth_headers("finance1"),
            json={
                "decision_status_code": "QUALIFIED",
                "decision_notes": "Finance should not be allowed to decide this.",
            },
        )
        assert decision_response.status_code == 403
    finally:
        cleanup_test_leads(created_public_ids)


def test_finance_user_can_list_but_cannot_create_or_update_lead() -> None:
    created_public_ids: list[str] = []
    try:
        lead = create_test_lead()
        created_public_ids.append(str(lead["public_id"]))

        list_response = client.get(
            "/api/leads?limit=5",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200

        create_response = client.post(
            "/api/leads",
            headers=auth_headers("finance1"),
            json={"company_name": f"Finance Should Not Create Lead {uuid4()}"},
        )
        assert create_response.status_code == 403

        update_response = client.put(
            f"/api/leads/{lead['public_id']}",
            headers=auth_headers("finance1"),
            json={"lead_status_code": "CONTACTED"},
        )
        assert update_response.status_code == 403

        list_activity_response = client.get(
            f"/api/leads/{lead['public_id']}/activities",
            headers=auth_headers("finance1"),
        )
        assert list_activity_response.status_code == 200

        create_activity_response = client.post(
            f"/api/leads/{lead['public_id']}/activities",
            headers=auth_headers("finance1"),
            json={"activity_type": "NOTE", "notes": "Finance should not create this."},
        )
        assert create_activity_response.status_code == 403
    finally:
        cleanup_test_leads(created_public_ids)


def test_create_lead_rejects_invalid_source_status_and_email() -> None:
    invalid_source_response = client.post(
        "/api/leads",
        headers=auth_headers("sales1"),
        json={
            "company_name": f"Invalid Source Lead {uuid4()}",
            "lead_source": "unknown_source",
        },
    )
    assert invalid_source_response.status_code == 422

    invalid_status_response = client.post(
        "/api/leads",
        headers=auth_headers("sales1"),
        json={
            "company_name": f"Invalid Status Lead {uuid4()}",
            "lead_status_code": "CONVERTED",
        },
    )
    assert invalid_status_response.status_code == 422

    invalid_email_response = client.post(
        "/api/leads",
        headers=auth_headers("sales1"),
        json={
            "company_name": f"Invalid Email Lead {uuid4()}",
            "contact_email": "not-an-email",
        },
    )
    assert invalid_email_response.status_code == 422


def test_update_lead_rejects_invalid_details_status_and_email() -> None:
    created_public_ids: list[str] = []
    try:
        lead = create_test_lead()
        created_public_ids.append(str(lead["public_id"]))

        invalid_status_response = client.put(
            f"/api/leads/{lead['public_id']}",
            headers=auth_headers("sales1"),
            json={"lead_status_code": "CONVERTED"},
        )
        assert invalid_status_response.status_code == 422

        invalid_email_response = client.put(
            f"/api/leads/{lead['public_id']}",
            headers=auth_headers("sales1"),
            json={"contact_email": "not-an-email"},
        )
        assert invalid_email_response.status_code == 422
    finally:
        cleanup_test_leads(created_public_ids)


def test_lead_qualification_decision_rejects_invalid_status_and_missing_lead() -> None:
    created_public_ids: list[str] = []
    try:
        lead = create_test_lead()
        lead_public_id = str(lead["public_id"])
        created_public_ids.append(lead_public_id)

        invalid_status_response = client.post(
            f"/api/leads/{lead_public_id}/qualification-decision",
            headers=auth_headers("sales1"),
            json={"decision_status_code": "CONVERTED"},
        )
        assert invalid_status_response.status_code == 422

        missing_lead_response = client.post(
            f"/api/leads/{uuid4()}/qualification-decision",
            headers=auth_headers("sales1"),
            json={"decision_status_code": "QUALIFIED"},
        )
        assert missing_lead_response.status_code == 404
    finally:
        cleanup_test_leads(created_public_ids)


def test_create_lead_activity_rejects_invalid_type_and_missing_lead() -> None:
    created_public_ids: list[str] = []
    try:
        lead = create_test_lead()
        created_public_ids.append(str(lead["public_id"]))

        invalid_type_response = client.post(
            f"/api/leads/{lead['public_id']}/activities",
            headers=auth_headers("sales1"),
            json={"activity_type": "UNKNOWN", "notes": "Invalid activity type."},
        )
        assert invalid_type_response.status_code == 422

        missing_lead_response = client.post(
            f"/api/leads/{uuid4()}/activities",
            headers=auth_headers("sales1"),
            json={"activity_type": "NOTE", "notes": "Missing lead."},
        )
        assert missing_lead_response.status_code == 404
    finally:
        cleanup_test_leads(created_public_ids)


def test_get_missing_lead_returns_not_found() -> None:
    response = client.get(
        f"/api/leads/{uuid4()}",
        headers=auth_headers("sales1"),
    )

    assert response.status_code == 404


def test_update_missing_lead_returns_not_found() -> None:
    response = client.put(
        f"/api/leads/{uuid4()}",
        headers=auth_headers("sales1"),
        json={"lead_status_code": "CONTACTED"},
    )

    assert response.status_code == 404


def cleanup_test_conversion_records(
    *,
    lead_public_ids: list[str],
    account_public_ids: list[str],
    opportunity_public_ids: list[str],
) -> None:
    record_public_ids = [*lead_public_ids, *account_public_ids, *opportunity_public_ids]

    with SessionLocal() as db:
        for public_id in record_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )

        for public_id in opportunity_public_ids:
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
                    DELETE FROM crm_lead
                    WHERE lead_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
        db.commit()


def qualify_test_lead(lead_public_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/leads/{lead_public_id}/qualification-decision",
        headers=auth_headers("sales1"),
        json={
            "decision_status_code": "QUALIFIED",
            "decision_notes": "Qualified for Slice 3D conversion test.",
            "reason": "Good fit",
        },
    )
    assert response.status_code == 200
    return response.json()["lead"]


def test_sales_user_can_convert_qualified_lead_to_account_and_opportunity() -> None:
    lead_public_ids: list[str] = []
    account_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []

    try:
        lead = create_test_lead(f"Slice 3D Conversion Lead {uuid4()}")
        lead_public_id = str(lead["public_id"])
        lead_public_ids.append(lead_public_id)
        qualify_test_lead(lead_public_id)

        convert_response = client.post(
            f"/api/leads/{lead_public_id}/convert",
            headers=auth_headers("sales1"),
            json={"conversion_notes": "Customer requirement is ready for Opportunity tracking."},
        )

        assert convert_response.status_code == 201
        body = convert_response.json()
        account_public_ids.append(body["account"]["public_id"])
        opportunity_public_ids.append(body["opportunity"]["public_id"])

        assert body["lead"]["public_id"] == lead_public_id
        assert body["lead"]["lead_status_code"] == "CONVERTED"
        assert body["lead"]["converted_account_public_id"] == body["account"]["public_id"]
        assert body["lead"]["converted_opportunity_public_id"] == body["opportunity"]["public_id"]
        assert body["account"]["account_status_code"] == "QUALIFIED_PROSPECT"
        assert body["opportunity"]["opportunity_source"] == "lead_conversion"
        assert body["opportunity"]["opportunity_status_code"] == "QUALIFIED"
        assert body["opportunity"]["account_public_id"] == body["account"]["public_id"]
        assert body["opportunity"]["source_lead_public_id"] == lead_public_id

        event_names = {event["event_name"] for event in body["events"]}
        assert {"AccountCreated", "OpportunityCreated", "LeadConverted"}.issubset(event_names)
        assert "password" not in str(body).lower()

        get_lead_response = client.get(
            f"/api/leads/{lead_public_id}",
            headers=auth_headers("sales1"),
        )
        assert get_lead_response.status_code == 200
        assert get_lead_response.json()["lead_status_code"] == "CONVERTED"
        assert get_lead_response.json()["converted_opportunity_public_id"] == body["opportunity"]["public_id"]

        get_opportunity_response = client.get(
            f"/api/opportunities/{body['opportunity']['public_id']}",
            headers=auth_headers("sales1"),
        )
        assert get_opportunity_response.status_code == 200
        assert get_opportunity_response.json()["source_lead_public_id"] == lead_public_id

        duplicate_response = client.post(
            f"/api/leads/{lead_public_id}/convert",
            headers=auth_headers("sales1"),
            json={},
        )
        assert duplicate_response.status_code == 422
    finally:
        cleanup_test_conversion_records(
            lead_public_ids=lead_public_ids,
            account_public_ids=account_public_ids,
            opportunity_public_ids=opportunity_public_ids,
        )


def test_a_converted_lead_can_no_longer_be_edited_or_decided() -> None:
    """TB-1 TB1-302 (4 October 2026): CONVERTED is final. Neither the Lead details update nor a qualification decision
    may change a converted Lead - not its status, not its details - and a refusal records nothing."""
    lead_public_ids: list[str] = []
    account_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []

    try:
        lead = create_test_lead(f"TB1-302 Converted Lead {uuid4()}")
        lead_public_id = str(lead["public_id"])
        lead_public_ids.append(lead_public_id)
        qualify_test_lead(lead_public_id)
        converted = client.post(
            f"/api/leads/{lead_public_id}/convert",
            headers=auth_headers("sales1"),
            json={},
        )
        assert converted.status_code == 201
        account_public_ids.append(converted.json()["account"]["public_id"])
        opportunity_public_ids.append(converted.json()["opportunity"]["public_id"])
        before = client.get(f"/api/leads/{lead_public_id}", headers=auth_headers("sales1")).json()

        def lead_event_count() -> int:
            with SessionLocal() as db:
                return int(
                    db.execute(
                        text("SELECT COUNT(*) FROM business_event WHERE record_public_id = :public_id"),
                        {"public_id": lead_public_id},
                    ).scalar_one()
                )

        events_before = lead_event_count()
        refusals = [
            client.put(f"/api/leads/{lead_public_id}", headers=auth_headers("sales1"), json={"lead_status_code": "NEW"}),
            client.put(f"/api/leads/{lead_public_id}", headers=auth_headers("sales1"), json={"contact_name": "Renamed"}),
        ] + [
            client.post(
                f"/api/leads/{lead_public_id}/qualification-decision",
                headers=auth_headers("sales1"),
                json={"decision_status_code": status, "reason": "Changed my mind."},
            )
            for status in ("QUALIFIED", "UNQUALIFIED", "CLOSED", "QUALIFICATION_READY")
        ]
        for refused in refusals:
            assert refused.status_code == 422
            assert "has been converted" in refused.json()["detail"]

        after = client.get(f"/api/leads/{lead_public_id}", headers=auth_headers("sales1")).json()
        assert after == before
        assert after["lead_status_code"] == "CONVERTED"
        assert lead_event_count() == events_before
    finally:
        cleanup_test_conversion_records(
            lead_public_ids=lead_public_ids,
            account_public_ids=account_public_ids,
            opportunity_public_ids=opportunity_public_ids,
        )


def test_lead_conversion_requires_sales_role_and_qualified_status() -> None:
    created_public_ids: list[str] = []
    try:
        draft_lead = create_test_lead(f"Slice 3D Draft Conversion Reject {uuid4()}")
        draft_lead_public_id = str(draft_lead["public_id"])
        created_public_ids.append(draft_lead_public_id)

        draft_convert_response = client.post(
            f"/api/leads/{draft_lead_public_id}/convert",
            headers=auth_headers("sales1"),
            json={},
        )
        assert draft_convert_response.status_code == 422

        qualified_lead = create_test_lead(f"Slice 3D Finance Conversion Reject {uuid4()}")
        qualified_lead_public_id = str(qualified_lead["public_id"])
        created_public_ids.append(qualified_lead_public_id)
        qualify_test_lead(qualified_lead_public_id)

        finance_convert_response = client.post(
            f"/api/leads/{qualified_lead_public_id}/convert",
            headers=auth_headers("finance1"),
            json={},
        )
        assert finance_convert_response.status_code == 403

        missing_response = client.post(
            f"/api/leads/{uuid4()}/convert",
            headers=auth_headers("sales1"),
            json={},
        )
        assert missing_response.status_code == 404
    finally:
        cleanup_test_leads(created_public_ids)
