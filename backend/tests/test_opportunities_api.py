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


def cleanup_test_records(*, opportunity_public_ids: list[str], account_public_ids: list[str] | None = None) -> None:
    account_public_ids = account_public_ids or []
    if not opportunity_public_ids and not account_public_ids:
        return

    with SessionLocal() as db:
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
        db.commit()


def cleanup_test_opportunities(public_ids: list[str]) -> None:
    cleanup_test_records(opportunity_public_ids=public_ids)


def create_test_opportunity(opportunity_name: str | None = None) -> dict[str, object]:
    response = client.post(
        "/api/opportunities",
        headers=auth_headers("sales1"),
        json={
            "opportunity_name": opportunity_name or f"Slice 3A Opportunity {uuid4()}",
            "opportunity_source": "manual",
            "source_reference": "Manual opportunity smoke test",
            "customer_requirement_summary": "Need crane and trailer solution discussion.",
            "opportunity_status_code": "NEW",
        },
    )
    assert response.status_code == 201
    return response.json()["opportunity"]


def create_test_account(account_name: str | None = None) -> dict[str, object]:
    response = client.post(
        "/api/accounts",
        headers=auth_headers("sales1"),
        json={
            "party_type": "organization",
            "account_name": account_name or f"Slice 6B1 Repair Account {uuid4()}",
            "account_status_code": "QUALIFIED_PROSPECT",
            "qualification_source": "manual",
            "source_remarks": "Created for Opportunity Account repair test.",
        },
    )
    assert response.status_code == 201
    return response.json()["account"]


def test_opportunities_require_authentication() -> None:
    response = client.get("/api/opportunities")

    assert response.status_code == 401


def test_sales_user_can_create_list_and_get_opportunity() -> None:
    created_public_ids: list[str] = []
    opportunity_name = f"Slice 3A Opportunity Company {uuid4()}"

    try:
        create_response = client.post(
            "/api/opportunities",
            headers=auth_headers("sales1"),
            json={
                "opportunity_name": opportunity_name,
                "opportunity_source": "manual",
                "source_reference": "Initial customer requirement",
                "customer_requirement_summary": "Customer needs lifting and transport support.",
                "estimated_value": "125000.00",
                "expected_close_date": "2026-08-15",
                "opportunity_status_code": "NEW",
            },
        )

        assert create_response.status_code == 201
        body = create_response.json()
        created_public_ids.append(body["opportunity"]["public_id"])
        assert body["opportunity"]["opportunity_name"] == opportunity_name
        assert body["opportunity"]["opportunity_source"] == "manual"
        assert body["opportunity"]["opportunity_status_code"] == "NEW"
        assert body["opportunity"]["account_public_id"] is None
        assert body["opportunity"]["source_lead_public_id"] is None
        assert body["event"]["event_name"] == "OpportunityCreated"
        assert body["event"]["record_type"] == "opportunity"
        assert body["event"]["record_public_id"] == body["opportunity"]["public_id"]
        assert "password" not in str(body).lower()

        list_response = client.get(
            "/api/opportunities?limit=10",
            headers=auth_headers("sales1"),
        )
        assert list_response.status_code == 200
        opportunities = list_response.json()
        assert any(opportunity["public_id"] == body["opportunity"]["public_id"] for opportunity in opportunities)

        get_response = client.get(
            f"/api/opportunities/{body['opportunity']['public_id']}",
            headers=auth_headers("readonly1"),
        )
        assert get_response.status_code == 200
        assert get_response.json()["public_id"] == body["opportunity"]["public_id"]
    finally:
        cleanup_test_opportunities(created_public_ids)


def test_sales_user_can_update_foundation_fields_and_stage() -> None:
    created_public_ids: list[str] = []
    try:
        opportunity = create_test_opportunity(f"Slice 3C Update Source {uuid4()}")
        public_id = str(opportunity["public_id"])
        created_public_ids.append(public_id)

        update_response = client.put(
            f"/api/opportunities/{public_id}",
            headers=auth_headers("sales1"),
            json={
                "opportunity_name": "Slice 3C Updated Opportunity",
                "opportunity_source": "rfq",
                "source_reference": "RFQ-3C-001",
                "customer_requirement_summary": "Updated crane and transport requirement.",
                "estimated_value": "250000.00",
                "expected_close_date": "2026-09-30",
                "opportunity_status_code": "QUALIFIED",
            },
        )

        assert update_response.status_code == 200
        body = update_response.json()
        assert body["opportunity"]["public_id"] == public_id
        assert body["opportunity"]["opportunity_name"] == "Slice 3C Updated Opportunity"
        assert body["opportunity"]["opportunity_source"] == "rfq"
        assert body["opportunity"]["source_reference"] == "RFQ-3C-001"
        assert body["opportunity"]["opportunity_status_code"] == "QUALIFIED"
        event_names = {event["event_name"] for event in body["events"]}
        assert "OpportunityUpdated" in event_names
        assert "OpportunityStageChanged" in event_names
        assert "password" not in str(body).lower()
    finally:
        cleanup_test_opportunities(created_public_ids)


def test_finance_user_can_list_but_cannot_create_or_update_opportunity() -> None:
    created_public_ids: list[str] = []
    try:
        opportunity = create_test_opportunity()
        created_public_ids.append(str(opportunity["public_id"]))

        list_response = client.get(
            "/api/opportunities?limit=5",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200

        get_response = client.get(
            f"/api/opportunities/{opportunity['public_id']}",
            headers=auth_headers("finance1"),
        )
        assert get_response.status_code == 200

        create_response = client.post(
            "/api/opportunities",
            headers=auth_headers("finance1"),
            json={"opportunity_name": f"Finance Should Not Create Opportunity {uuid4()}"},
        )
        assert create_response.status_code == 403

        update_response = client.put(
            f"/api/opportunities/{opportunity['public_id']}",
            headers=auth_headers("finance1"),
            json={"opportunity_name": "Finance Should Not Update Opportunity"},
        )
        assert update_response.status_code == 403
    finally:
        cleanup_test_opportunities(created_public_ids)


def test_sales_user_can_link_existing_account_to_unlinked_opportunity() -> None:
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity(f"Slice 6B1 Existing Account Repair {uuid4()}")
        opportunity_public_ids.append(str(opportunity["public_id"]))
        account = create_test_account()
        account_public_ids.append(str(account["public_id"]))

        response = client.post(
            f"/api/opportunities/{opportunity['public_id']}/account-repair",
            headers=auth_headers("sales1"),
            json={"account_public_id": account["public_id"]},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["opportunity"]["public_id"] == opportunity["public_id"]
        assert body["opportunity"]["account_public_id"] == account["public_id"]
        assert body["account"]["public_id"] == account["public_id"]
        event_names = {event["event_name"] for event in body["events"]}
        assert event_names == {"OpportunityAccountRepaired"}

        get_response = client.get(
            f"/api/opportunities/{opportunity['public_id']}",
            headers=auth_headers("sales1"),
        )
        assert get_response.status_code == 200
        assert get_response.json()["account_public_id"] == account["public_id"]
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, account_public_ids=account_public_ids)


def test_sales_user_can_create_minimal_account_and_link_to_opportunity() -> None:
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity(f"Slice 6B1 Minimal Account Repair {uuid4()}")
        opportunity_public_ids.append(str(opportunity["public_id"]))

        response = client.post(
            f"/api/opportunities/{opportunity['public_id']}/account-repair",
            headers=auth_headers("sales1"),
            json={
                "create_account": {
                    "account_name": f"Slice 6B1 Minimal Qualified Prospect {uuid4()}",
                    "legal_name": "Slice 6B1 Minimal Legal Name",
                    "source_remarks": "Repair missing Account traceability for a manual Opportunity.",
                }
            },
        )

        assert response.status_code == 200
        body = response.json()
        account = body["account"]
        account_public_ids.append(str(account["public_id"]))
        assert account["account_status_code"] == "QUALIFIED_PROSPECT"
        assert body["opportunity"]["account_public_id"] == account["public_id"]
        event_names = [event["event_name"] for event in body["events"]]
        assert event_names == ["AccountCreated", "OpportunityAccountRepaired"]
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, account_public_ids=account_public_ids)


def test_unauthorized_account_repair_is_rejected() -> None:
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity(f"Slice 6B1 Unauthorized Repair {uuid4()}")
        opportunity_public_ids.append(str(opportunity["public_id"]))
        account = create_test_account()
        account_public_ids.append(str(account["public_id"]))

        response = client.post(
            f"/api/opportunities/{opportunity['public_id']}/account-repair",
            headers=auth_headers("finance1"),
            json={"account_public_id": account["public_id"]},
        )

        assert response.status_code == 403

        get_response = client.get(
            f"/api/opportunities/{opportunity['public_id']}",
            headers=auth_headers("sales1"),
        )
        assert get_response.status_code == 200
        assert get_response.json()["account_public_id"] is None
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, account_public_ids=account_public_ids)


def test_already_linked_opportunity_cannot_be_silently_relinked() -> None:
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []

    try:
        opportunity = create_test_opportunity(f"Slice 6B1 Relink Rejection {uuid4()}")
        opportunity_public_ids.append(str(opportunity["public_id"]))
        first_account = create_test_account(f"Slice 6B1 First Account {uuid4()}")
        second_account = create_test_account(f"Slice 6B1 Second Account {uuid4()}")
        account_public_ids.extend([str(first_account["public_id"]), str(second_account["public_id"])])

        first_response = client.post(
            f"/api/opportunities/{opportunity['public_id']}/account-repair",
            headers=auth_headers("sales1"),
            json={"account_public_id": first_account["public_id"]},
        )
        assert first_response.status_code == 200

        second_response = client.post(
            f"/api/opportunities/{opportunity['public_id']}/account-repair",
            headers=auth_headers("sales1"),
            json={"account_public_id": second_account["public_id"]},
        )

        assert second_response.status_code == 422
        assert "already has a linked Account" in second_response.json()["detail"]

        get_response = client.get(
            f"/api/opportunities/{opportunity['public_id']}",
            headers=auth_headers("sales1"),
        )
        assert get_response.status_code == 200
        assert get_response.json()["account_public_id"] == first_account["public_id"]
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, account_public_ids=account_public_ids)


def test_create_opportunity_rejects_invalid_source_status_and_value() -> None:
    invalid_source_response = client.post(
        "/api/opportunities",
        headers=auth_headers("sales1"),
        json={
            "opportunity_name": f"Invalid Source Opportunity {uuid4()}",
            "opportunity_source": "unknown_source",
        },
    )
    assert invalid_source_response.status_code == 422

    invalid_status_response = client.post(
        "/api/opportunities",
        headers=auth_headers("sales1"),
        json={
            "opportunity_name": f"Invalid Status Opportunity {uuid4()}",
            "opportunity_status_code": "WON",
        },
    )
    assert invalid_status_response.status_code == 422

    invalid_value_response = client.post(
        "/api/opportunities",
        headers=auth_headers("sales1"),
        json={
            "opportunity_name": f"Invalid Value Opportunity {uuid4()}",
            "estimated_value": "-1.00",
        },
    )
    assert invalid_value_response.status_code == 422


def test_update_opportunity_rejects_blank_name_and_deferred_won_status() -> None:
    created_public_ids: list[str] = []
    try:
        opportunity = create_test_opportunity(f"Slice 3C Validation Source {uuid4()}")
        public_id = str(opportunity["public_id"])
        created_public_ids.append(public_id)

        blank_name_response = client.put(
            f"/api/opportunities/{public_id}",
            headers=auth_headers("sales1"),
            json={"opportunity_name": "   "},
        )
        assert blank_name_response.status_code == 422

        won_status_response = client.put(
            f"/api/opportunities/{public_id}",
            headers=auth_headers("sales1"),
            json={"opportunity_status_code": "WON"},
        )
        assert won_status_response.status_code == 422
    finally:
        cleanup_test_opportunities(created_public_ids)


def test_get_missing_opportunity_returns_not_found() -> None:
    response = client.get(
        f"/api/opportunities/{uuid4()}",
        headers=auth_headers("sales1"),
    )

    assert response.status_code == 404


def test_update_missing_opportunity_returns_not_found() -> None:
    response = client.put(
        f"/api/opportunities/{uuid4()}",
        headers=auth_headers("sales1"),
        json={"opportunity_name": "Missing Opportunity"},
    )

    assert response.status_code == 404
