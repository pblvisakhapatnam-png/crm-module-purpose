from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app

client = TestClient(app)


def login(username: str = "admin1", password: str = "password") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(username: str = "sales1") -> dict[str, str]:
    token = login(username, "password")
    return {"Authorization": f"Bearer {token}"}


def cleanup_records(*, opportunity_public_ids: list[str], offer_public_ids: list[str], work_order_public_ids: list[str]) -> None:
    with SessionLocal() as db:
        account_public_ids: set[str] = set()
        lead_public_ids: set[str] = set()
        for public_id in opportunity_public_ids:
            row = db.execute(
                text(
                    """
                    SELECT
                        bp.business_party_public_id AS account_public_id,
                        l.lead_public_id AS source_lead_public_id
                    FROM crm_opportunity o
                    LEFT JOIN business_party bp ON bp.id = o.business_party_id
                    LEFT JOIN crm_lead l ON l.id = o.source_lead_id
                    WHERE o.opportunity_public_id = :public_id
                    LIMIT 1
                    """
                ),
                {"public_id": public_id},
            ).first()
            if row:
                data = row._mapping
                if data.get("account_public_id"):
                    account_public_ids.add(str(data["account_public_id"]))
                if data.get("source_lead_public_id"):
                    lead_public_ids.add(str(data["source_lead_public_id"]))

        for public_id in work_order_public_ids:
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
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_public_id = :public_id
                       OR (NULLIF(event_payload_json, '')::json ->> 'work_order_public_id') = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(text("DELETE FROM crm_work_order WHERE work_order_public_id = :public_id"), {"public_id": public_id})

        for public_id in offer_public_ids:
            # Slice 6M.1 completion: create_test_offer_with_line(accepted=True) now records a
            # real Customer Response and submission evidence, so both must be cleared before
            # the offer row itself, matching the FK-safe order in test_commercial_offers_api.py.
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
                    DELETE FROM crm_commercial_offer_pricing_evidence pe
                    USING crm_commercial_offer co
                    WHERE co.id = pe.commercial_offer_id
                      AND co.offer_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text("DELETE FROM business_event WHERE record_type = 'commercial_offer' AND record_public_id = :public_id"),
                {"public_id": public_id},
            )
            db.execute(text("DELETE FROM crm_commercial_offer WHERE offer_public_id = :public_id"), {"public_id": public_id})

        for public_id in opportunity_public_ids:
            db.execute(
                text("DELETE FROM business_event WHERE record_type = 'opportunity' AND record_public_id = :public_id"),
                {"public_id": public_id},
            )
            db.execute(text("DELETE FROM crm_opportunity WHERE opportunity_public_id = :public_id"), {"public_id": public_id})

        for public_id in account_public_ids:
            db.execute(
                text("DELETE FROM business_event WHERE record_type = 'business_party' AND record_public_id = :public_id"),
                {"public_id": public_id},
            )
            db.execute(text("DELETE FROM business_party WHERE business_party_public_id = :public_id"), {"public_id": public_id})

        for public_id in lead_public_ids:
            db.execute(
                text("DELETE FROM business_event WHERE record_type = 'lead' AND record_public_id = :public_id"),
                {"public_id": public_id},
            )
            db.execute(text("DELETE FROM crm_lead WHERE lead_public_id = :public_id"), {"public_id": public_id})
        db.commit()


def create_test_opportunity() -> dict[str, object]:
    response = client.post(
        "/api/opportunities",
        headers=auth_headers("sales1"),
        json={
            "opportunity_name": f"Slice 5A Work Order Opportunity {uuid4()}",
            "opportunity_source": "manual",
            "source_reference": "Work Order shell test",
            "customer_requirement_summary": "Customer accepted quotation for crane hiring.",
            "opportunity_status_code": "NEW",
        },
    )
    assert response.status_code == 201
    opportunity = response.json()["opportunity"]
    update_response = client.put(
        f"/api/opportunities/{opportunity['public_id']}",
        headers=auth_headers("sales1"),
        json={"opportunity_status_code": "QUALIFIED"},
    )
    assert update_response.status_code == 200
    return update_response.json()["opportunity"]


def create_account_linked_test_opportunity() -> dict[str, object]:
    lead_response = client.post(
        "/api/leads",
        headers=auth_headers("sales1"),
        json={
            "lead_source": "manual",
            "source_reference": "Work Order Account traceability test",
            "company_name": f"Slice 6A1 Work Order Trace Lead {uuid4()}",
            "contact_name": "Slice 6A1 Contact",
            "contact_phone": "+91-9876543210",
            "contact_email": "slice6a1.wo@example.com",
            "requirement_summary": "Qualified enquiry for Work Order Account traceability.",
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
        json={"conversion_notes": "Create Account-linked Opportunity for Work Order handoff test."},
    )
    assert conversion_response.status_code == 201
    return conversion_response.json()["opportunity"]


def create_test_offer_with_line(
    *,
    accepted: bool = True,
    account_linked: bool = True,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    opportunity = create_account_linked_test_opportunity() if account_linked else create_test_opportunity()
    offer_response = client.post(
        "/api/commercial-offers",
        headers=auth_headers("sales1"),
        json={
            "opportunity_public_id": opportunity["public_id"],
            "offer_title": "Slice 5A Accepted Commercial Offer",
            "offer_mode": "plum_generated",
            "offer_type": "firm",
            "offer_status_code": "DRAFT",
            "offer_value": "250000.00",
            "currency_code": "INR",
            "offer_date": "2026-08-01",
            "valid_until": "2026-08-31",
            "remarks": "Offer for Work Order handoff shell.",
        },
    )
    assert offer_response.status_code == 201
    offer = offer_response.json()["commercial_offer"]

    line_response = client.post(
        f"/api/commercial-offers/{offer['public_id']}/lines",
        headers=auth_headers("sales1"),
        json={
            "scope_description": "Provide 80T crane with operator for site work.",
            "equipment_service_category": "Crane",
            "quantity": "10.00",
            "uom": "day",
            "rate_amount": "25000.00",
            "currency_code": "INR",
            "remarks": "Foundation line only.",
        },
    )
    assert line_response.status_code == 201
    line = line_response.json()["offer_line"]

    if accepted:
        evidence_response = client.post(
            f"/api/commercial-offers/{offer['public_id']}/submission-evidence",
            headers=auth_headers("sales1"),
            json={
                "submission_channel": "EMAIL",
                "submitted_at": "2026-08-04T10:00:00Z",
                "submission_reference": "SUB-5A-WO-TEST",
            },
        )
        assert evidence_response.status_code == 201

        submitted_response = client.post(
            f"/api/commercial-offers/{offer['public_id']}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert submitted_response.status_code == 200

        # Slice 6M.1 completion: ACCEPTED is reached only through the dedicated Customer
        # Response action (Slice 6L), not through generic update.
        response_result = client.post(
            f"/api/commercial-offers/{offer['public_id']}/customer-responses",
            headers=auth_headers("sales1"),
            json={
                "response_outcome": "ACCEPTED_AWARDED",
                "response_received_at": "2026-08-05T09:00:00Z",
                "response_channel": "EMAIL",
                "customer_response_notes": "Accepted for Work Order shell test.",
            },
        )
        assert response_result.status_code == 201
        offer = response_result.json()["commercial_offer"]

    return opportunity, offer, line


def force_offer_status_for_legacy_test(offer_public_id: str, status_code: str) -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                """
                UPDATE crm_commercial_offer
                SET offer_status_code = :status_code,
                    updated_at = CURRENT_TIMESTAMP
                WHERE offer_public_id = :offer_public_id
                """
            ),
            {"offer_public_id": offer_public_id, "status_code": status_code},
        )
        db.commit()


def test_sales_user_can_create_work_order_shell_from_accepted_offer() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    work_order_public_ids: list[str] = []

    try:
        opportunity, offer, line = create_test_offer_with_line(accepted=True)
        opportunity_public_ids.append(str(opportunity["public_id"]))
        offer_public_ids.append(str(offer["public_id"]))

        response = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={
                "commercial_offer_public_id": offer["public_id"],
                "selected_offer_line_public_ids": [line["public_id"]],
                "customer_wo_reference": "Customer WO 5A-001",
                "received_date": "2026-08-06",
                "remarks": "Thin Work Order shell only.",
            },
        )

        assert response.status_code == 201
        body = response.json()
        work_order = body["work_order"]
        work_order_public_ids.append(work_order["public_id"])
        assert work_order["work_order_code"].startswith("WO-")
        assert work_order["commercial_offer_public_id"] == offer["public_id"]
        assert work_order["opportunity_public_id"] == opportunity["public_id"]
        assert work_order["account_public_id"] == opportunity["account_public_id"]
        assert work_order["work_order_status_code"] == "HANDOFF_CREATED"
        assert body["lines"][0]["source_offer_line_public_id"] == line["public_id"]
        assert body["events"][0]["event_name"] == "WorkOrderCreated"

        list_response = client.get("/api/work-orders", headers=auth_headers("sales1"))
        assert list_response.status_code == 200
        assert any(item["public_id"] == work_order["public_id"] for item in list_response.json())

        filtered_list_response = client.get(
            f"/api/work-orders?commercial_offer_public_id={offer['public_id']}",
            headers=auth_headers("sales1"),
        )
        assert filtered_list_response.status_code == 200
        filtered_work_orders = filtered_list_response.json()
        assert any(item["public_id"] == work_order["public_id"] for item in filtered_work_orders)
        assert all(item["commercial_offer_public_id"] == offer["public_id"] for item in filtered_work_orders)

        get_response = client.get(f"/api/work-orders/{work_order['public_id']}", headers=auth_headers("readonly1"))
        assert get_response.status_code == 200
        assert get_response.json()["public_id"] == work_order["public_id"]

        lines_response = client.get(f"/api/work-orders/{work_order['public_id']}/lines", headers=auth_headers("readonly1"))
        assert lines_response.status_code == 200
        assert len(lines_response.json()) == 1
    finally:
        cleanup_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            work_order_public_ids=work_order_public_ids,
        )


def test_work_order_shell_requires_accepted_offer() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity, offer, _line = create_test_offer_with_line(accepted=False)
        opportunity_public_ids.append(str(opportunity["public_id"]))
        offer_public_ids.append(str(offer["public_id"]))

        response = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={"commercial_offer_public_id": offer["public_id"]},
        )

        assert response.status_code == 422
        assert "accepted Commercial Offer" in response.json()["detail"]
    finally:
        cleanup_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            work_order_public_ids=[],
        )


def test_work_order_shell_requires_account_traceability_on_source_offer() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []

    try:
        opportunity, offer, _line = create_test_offer_with_line(accepted=False, account_linked=False)
        opportunity_public_ids.append(str(opportunity["public_id"]))
        offer_public_ids.append(str(offer["public_id"]))
        assert offer["account_public_id"] is None

        force_offer_status_for_legacy_test(str(offer["public_id"]), "ACCEPTED")

        response = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={"commercial_offer_public_id": offer["public_id"]},
        )

        assert response.status_code == 422
        assert "linked to an Account" in response.json()["detail"]
    finally:
        cleanup_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            work_order_public_ids=[],
        )


def test_work_order_detail_traceability_and_read_creates_no_event() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    work_order_public_ids: list[str] = []

    try:
        opportunity, offer, line = create_test_offer_with_line(accepted=True)
        opportunity_public_ids.append(str(opportunity["public_id"]))
        offer_public_ids.append(str(offer["public_id"]))

        create_response = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={
                "commercial_offer_public_id": offer["public_id"],
                "selected_offer_line_public_ids": [line["public_id"]],
                "customer_wo_reference": f"CUST-{uuid4()}",
            },
        )
        assert create_response.status_code == 201
        work_order = create_response.json()["work_order"]
        work_order_public_ids.append(work_order["public_id"])

        # Traceability: Work Order detail resolves the linked Commercial Offer, Opportunity and Account.
        detail_response = client.get(f"/api/work-orders/{work_order['public_id']}", headers=auth_headers("readonly1"))
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["commercial_offer_public_id"] == offer["public_id"]
        assert detail["opportunity_public_id"] == opportunity["public_id"]
        assert detail["account_public_id"] == opportunity["account_public_id"]
        assert detail["created_by"] is not None
        assert detail["updated_at"] is not None

        # Source Commercial Offer line identity is preserved on the copied Work Order line.
        lines_response = client.get(f"/api/work-orders/{work_order['public_id']}/lines", headers=auth_headers("readonly1"))
        assert lines_response.status_code == 200
        lines = lines_response.json()
        assert len(lines) == 1
        assert lines[0]["source_offer_line_public_id"] == line["public_id"]
        assert lines[0]["scope_description"] == line["scope_description"]

        # The handoff event is discoverable through the new narrow record filter and stays singular.
        events_response = client.get(
            f"/api/events/recent?record_type=work_order&record_public_id={work_order['public_id']}",
            headers=auth_headers("admin1"),
        )
        assert events_response.status_code == 200
        events = events_response.json()
        assert len(events) == 1
        assert events[0]["event_name"] == "WorkOrderCreated"
        assert events[0]["event_payload"]["commercial_offer_public_id"] == offer["public_id"]

        # Reading the Work Order detail again must not create a duplicate business event.
        second_detail_response = client.get(f"/api/work-orders/{work_order['public_id']}", headers=auth_headers("readonly1"))
        assert second_detail_response.status_code == 200
        repeat_events_response = client.get(
            f"/api/events/recent?record_type=work_order&record_public_id={work_order['public_id']}",
            headers=auth_headers("admin1"),
        )
        assert repeat_events_response.status_code == 200
        assert len(repeat_events_response.json()) == 1
    finally:
        cleanup_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            work_order_public_ids=work_order_public_ids,
        )


def test_work_order_multiple_lines_remain_traceable() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    work_order_public_ids: list[str] = []

    try:
        opportunity, offer, first_line = create_test_offer_with_line(accepted=False, account_linked=True)
        opportunity_public_ids.append(str(opportunity["public_id"]))
        offer_public_ids.append(str(offer["public_id"]))

        second_line_response = client.post(
            f"/api/commercial-offers/{offer['public_id']}/lines",
            headers=auth_headers("sales1"),
            json={
                "scope_description": "Provide flatbed trailer for equipment transport.",
                "equipment_service_category": "Trailer",
                "quantity": "4.00",
                "uom": "trip",
                "rate_amount": "8000.00",
                "currency_code": "INR",
            },
        )
        assert second_line_response.status_code == 201
        second_line = second_line_response.json()["offer_line"]

        evidence_response = client.post(
            f"/api/commercial-offers/{offer['public_id']}/submission-evidence",
            headers=auth_headers("sales1"),
            json={"submission_channel": "EMAIL", "submitted_at": "2026-08-04T10:00:00Z", "submission_reference": "SUB-6O-MULTI"},
        )
        assert evidence_response.status_code == 201
        submitted_response = client.post(f"/api/commercial-offers/{offer['public_id']}/mark-submitted", headers=auth_headers("sales1"))
        assert submitted_response.status_code == 200
        accepted_response = client.post(
            f"/api/commercial-offers/{offer['public_id']}/customer-responses",
            headers=auth_headers("sales1"),
            json={"response_outcome": "ACCEPTED_AWARDED", "response_received_at": "2026-08-05T09:00:00Z", "response_channel": "EMAIL"},
        )
        assert accepted_response.status_code == 201

        create_response = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("sales1"),
            json={"commercial_offer_public_id": offer["public_id"], "customer_wo_reference": f"CUST-{uuid4()}"},
        )
        assert create_response.status_code == 201
        work_order = create_response.json()["work_order"]
        work_order_public_ids.append(work_order["public_id"])

        lines_response = client.get(f"/api/work-orders/{work_order['public_id']}/lines", headers=auth_headers("sales1"))
        assert lines_response.status_code == 200
        lines = lines_response.json()
        assert len(lines) == 2
        source_ids = {item["source_offer_line_public_id"] for item in lines}
        assert source_ids == {first_line["public_id"], second_line["public_id"]}
    finally:
        cleanup_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            work_order_public_ids=work_order_public_ids,
        )


def test_work_order_partial_award_allows_additional_shell_for_what_is_left() -> None:
    """The frozen contract allows more than one Work Order per accepted offer for a partial award; since CS-04 part 1
    (its dated amendment of 8 October 2026) each takes only what is not on a Work Order yet, and each carries its own
    customer order reference. The same request again - which this test used to expect to succeed - is refused, naming
    the Work Order that has it; a second customer order of the same size goes through."""
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    work_order_public_ids: list[str] = []

    try:
        opportunity, offer, line = create_test_offer_with_line(accepted=True)
        opportunity_public_ids.append(str(opportunity["public_id"]))
        offer_public_ids.append(str(offer["public_id"]))

        def part_request(reference: str) -> dict[str, object]:
            return {
                "commercial_offer_public_id": offer["public_id"],
                "selected_offer_line_public_ids": [line["public_id"]],
                "selected_offer_line_quantities": [{"offer_line_public_id": line["public_id"], "quantity": "4.00"}],
                "customer_wo_reference": reference,
            }

        def post(body: dict[str, object]):
            return client.post("/api/work-orders/from-commercial-offer", headers=auth_headers("sales1"), json=body)

        first_response = post(part_request("PO-5A-1"))
        assert first_response.status_code == 201
        first_work_order = first_response.json()["work_order"]
        work_order_public_ids.append(first_work_order["public_id"])

        # The same request again - a Create pressed after a timeout - carries the same customer order: refused.
        repeated = post(part_request(" po-5a-1 "))
        assert repeated.status_code == 409
        assert "is already on " + first_work_order["work_order_code"] in repeated.json()["detail"]

        # A second customer order for the same 4 is a second award.
        second_award = post(part_request("PO-5A-2"))
        assert second_award.status_code == 201
        work_order_public_ids.append(second_award.json()["work_order"]["public_id"])
        over = post(part_request("PO-5A-3"))
        assert over.status_code == 409
        assert "Line 1 has 2 of 10 left to hand off" in over.json()["detail"]
        assert first_work_order["work_order_code"] in over.json()["detail"]

        second_response = post(
            {"commercial_offer_public_id": offer["public_id"], "selected_offer_line_public_ids": [line["public_id"]],
             "customer_wo_reference": "PO-5A-4"}
        )
        assert second_response.status_code == 201
        second_work_order = second_response.json()["work_order"]
        work_order_public_ids.append(second_work_order["public_id"])
        assert second_work_order["public_id"] != first_work_order["public_id"]
        assert second_response.json()["lines"][0]["quantity"] == "2.00"

        whole_again = post(
            {"commercial_offer_public_id": offer["public_id"], "selected_offer_line_public_ids": [line["public_id"]],
             "customer_wo_reference": "PO-5A-5"}
        )
        assert whole_again.status_code == 409
        assert "Line 1 is already on a Work Order in full" in whole_again.json()["detail"]

        filtered_list_response = client.get(
            f"/api/work-orders?commercial_offer_public_id={offer['public_id']}",
            headers=auth_headers("sales1"),
        )
        assert filtered_list_response.status_code == 200
        filtered_public_ids = {item["public_id"] for item in filtered_list_response.json()}
        assert {first_work_order["public_id"], second_work_order["public_id"]}.issubset(filtered_public_ids)
    finally:
        cleanup_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            work_order_public_ids=work_order_public_ids,
        )


def test_events_recent_filter_still_rejects_sales_user() -> None:
    response = client.get(
        "/api/events/recent?record_type=work_order&record_public_id=00000000-0000-0000-0000-000000000000",
        headers=auth_headers("sales1"),
    )
    assert response.status_code == 403


def test_finance_user_can_view_but_cannot_create_work_order_shell() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    work_order_public_ids: list[str] = []

    try:
        opportunity, offer, _line = create_test_offer_with_line(accepted=True)
        opportunity_public_ids.append(str(opportunity["public_id"]))
        offer_public_ids.append(str(offer["public_id"]))

        denied_response = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("finance1"),
            json={"commercial_offer_public_id": offer["public_id"]},
        )
        assert denied_response.status_code == 403

        allowed_response = client.post(
            "/api/work-orders/from-commercial-offer",
            headers=auth_headers("ops1"),
            json={"commercial_offer_public_id": offer["public_id"], "customer_wo_reference": f"CUST-{uuid4()}"},
        )
        assert allowed_response.status_code == 201
        work_order_public_ids.append(allowed_response.json()["work_order"]["public_id"])

        finance_list = client.get("/api/work-orders", headers=auth_headers("finance1"))
        assert finance_list.status_code == 200
    finally:
        cleanup_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            work_order_public_ids=work_order_public_ids,
        )
