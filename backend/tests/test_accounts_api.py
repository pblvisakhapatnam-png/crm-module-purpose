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


def cleanup_test_records(
    *,
    account_public_ids: list[str] | None = None,
    contact_public_ids: list[str] | None = None,
    address_public_ids: list[str] | None = None,
    tax_profile_public_ids: list[str] | None = None,
    gstin_public_ids: list[str] | None = None,
    document_public_ids: list[str] | None = None,
) -> None:
    """Remove Account API test records from the shared development database.

    These tests run against the Docker development PostgreSQL database during the
    prototype stage. Tests must not keep adding business records to the Account
    list every time pytest is run.
    """
    account_public_ids = account_public_ids or []
    contact_public_ids = contact_public_ids or []
    address_public_ids = address_public_ids or []
    tax_profile_public_ids = tax_profile_public_ids or []
    gstin_public_ids = gstin_public_ids or []
    document_public_ids = document_public_ids or []

    if not account_public_ids and not contact_public_ids and not address_public_ids and not tax_profile_public_ids and not gstin_public_ids and not document_public_ids:
        return

    with SessionLocal() as db:
        for public_id in document_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'document_metadata'
                      AND record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM document_metadata
                    WHERE document_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )

        for public_id in gstin_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'business_party_gstin'
                      AND record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_party_gstin
                    WHERE gstin_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )

        for public_id in tax_profile_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'business_party_tax_profile'
                      AND record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_party_tax_profile
                    WHERE tax_profile_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )

        for public_id in address_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'business_party_address'
                      AND record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_party_address
                    WHERE address_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )

        for public_id in contact_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'business_party_contact'
                      AND record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_party_contact
                    WHERE contact_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )

        for public_id in account_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'document_metadata'
                      AND record_public_id IN (
                          SELECT document_public_id
                          FROM document_metadata
                          WHERE linked_record_type = 'business_party'
                            AND linked_record_public_id = :public_id
                      )
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM document_metadata
                    WHERE linked_record_type = 'business_party'
                      AND linked_record_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'business_party_address'
                      AND record_public_id IN (
                          SELECT address_public_id
                          FROM business_party_address
                          WHERE business_party_id IN (
                              SELECT id FROM business_party WHERE business_party_public_id = :public_id
                          )
                      )
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'business_party_contact'
                      AND record_public_id IN (
                          SELECT contact_public_id
                          FROM business_party_contact
                          WHERE business_party_id IN (
                              SELECT id FROM business_party WHERE business_party_public_id = :public_id
                          )
                      )
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'business_party_gstin'
                      AND record_public_id IN (
                          SELECT gstin_public_id
                          FROM business_party_gstin
                          WHERE business_party_id IN (
                              SELECT id FROM business_party WHERE business_party_public_id = :public_id
                          )
                      )
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_event
                    WHERE record_type = 'business_party_tax_profile'
                      AND record_public_id IN (
                          SELECT tax_profile_public_id
                          FROM business_party_tax_profile
                          WHERE business_party_id IN (
                              SELECT id FROM business_party WHERE business_party_public_id = :public_id
                          )
                      )
                    """
                ),
                {"public_id": public_id},
            )
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
                    DELETE FROM business_party_gstin
                    WHERE business_party_id IN (
                        SELECT id FROM business_party WHERE business_party_public_id = :public_id
                    )
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_party_tax_profile
                    WHERE business_party_id IN (
                        SELECT id FROM business_party WHERE business_party_public_id = :public_id
                    )
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_party_address
                    WHERE business_party_id IN (
                        SELECT id FROM business_party WHERE business_party_public_id = :public_id
                    )
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM business_party_contact
                    WHERE business_party_id IN (
                        SELECT id FROM business_party WHERE business_party_public_id = :public_id
                    )
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


def cleanup_test_accounts(public_ids: list[str]) -> None:
    cleanup_test_records(account_public_ids=public_ids)



def unique_pan() -> str:
    suffix_number = uuid4().int % 10000
    suffix_letter = chr(ord("A") + (uuid4().int % 26))
    return f"ABCDE{suffix_number:04d}{suffix_letter}"


def unique_gstin() -> str:
    alpha_numeric = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    checksum_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    pan = unique_pan()
    entity_code = alpha_numeric[uuid4().int % len(alpha_numeric)]
    checksum = checksum_chars[uuid4().int % len(checksum_chars)]
    return f"29{pan}{entity_code}Z{checksum}"

def create_test_account(username: str = "sales1") -> dict[str, object]:
    response = client.post(
        "/api/accounts",
        headers=auth_headers(username),
        json={
            "account_name": f"Slice Test Account {uuid4()}",
            "qualification_source": "manual",
        },
    )
    assert response.status_code == 201
    return response.json()["account"]


def test_accounts_require_authentication() -> None:
    response = client.get("/api/accounts")

    assert response.status_code == 401


def test_sales_user_can_create_draft_account_and_list_it() -> None:
    created_public_ids: list[str] = []
    unique_name = f"Slice 1B Draft Account {uuid4()}"

    try:
        create_response = client.post(
            "/api/accounts",
            headers=auth_headers("sales1"),
            json={
                "account_name": unique_name,
                "qualification_source": "enquiry",
                "source_remarks": "Created by Slice 1B API test.",
            },
        )

        assert create_response.status_code == 201
        body = create_response.json()
        created_public_ids.append(body["account"]["public_id"])
        assert body["account"]["account_name"] == unique_name
        assert body["account"]["party_type"] == "organization"
        assert body["account"]["account_status_code"] == "DRAFT"
        assert body["account"]["qualification_source"] == "enquiry"
        assert body["event"]["event_name"] == "AccountCreated"
        assert body["event"]["record_type"] == "business_party"
        assert body["event"]["record_public_id"] == body["account"]["public_id"]
        assert "password" not in str(body).lower()

        list_response = client.get(
            "/api/accounts?limit=10",
            headers=auth_headers("sales1"),
        )

        assert list_response.status_code == 200
        accounts = list_response.json()
        assert any(account["public_id"] == body["account"]["public_id"] for account in accounts)
    finally:
        cleanup_test_accounts(created_public_ids)


def test_sales_manager_can_create_qualified_prospect_account() -> None:
    created_public_ids: list[str] = []
    unique_name = f"Slice 1B Qualified Prospect {uuid4()}"

    try:
        response = client.post(
            "/api/accounts",
            headers=auth_headers("manager1"),
            json={
                "account_name": unique_name,
                "legal_name": f"{unique_name} Private Limited",
                "account_status_code": "QUALIFIED_PROSPECT",
                "qualification_source": "rfq",
                "segment": "Industrial",
                "industry": "Infrastructure",
            },
        )

        assert response.status_code == 201
        body = response.json()
        created_public_ids.append(body["account"]["public_id"])
        assert body["account"]["account_status_code"] == "QUALIFIED_PROSPECT"
        assert body["account"]["legal_name"].endswith("Private Limited")

        get_response = client.get(
            f"/api/accounts/{body['account']['public_id']}",
            headers=auth_headers("readonly1"),
        )

        assert get_response.status_code == 200
        assert get_response.json()["public_id"] == body["account"]["public_id"]
    finally:
        cleanup_test_accounts(created_public_ids)


def test_create_account_rejects_future_customer_status() -> None:
    response = client.post(
        "/api/accounts",
        headers=auth_headers("sales1"),
        json={
            "account_name": f"Slice 1B Invalid Status {uuid4()}",
            "account_status_code": "CUSTOMER_ACTIVE",
        },
    )

    assert response.status_code == 422


def test_create_account_rejects_invalid_pan() -> None:
    response = client.post(
        "/api/accounts",
        headers=auth_headers("sales1"),
        json={
            "account_name": f"Slice 1B Invalid PAN {uuid4()}",
            "pan": "bad-pan",
        },
    )

    assert response.status_code == 422


def test_finance_user_can_list_but_cannot_create_account() -> None:
    list_response = client.get(
        "/api/accounts?limit=5",
        headers=auth_headers("finance1"),
    )
    assert list_response.status_code == 200

    create_response = client.post(
        "/api/accounts",
        headers=auth_headers("finance1"),
        json={"account_name": f"Slice 1B Finance Create Block {uuid4()}"},
    )
    assert create_response.status_code == 403


def test_account_list_supports_limit_and_offset_pagination() -> None:
    created_public_ids: list[str] = []
    first_name = f"Slice 1F Pagination First {uuid4()}"
    second_name = f"Slice 1F Pagination Second {uuid4()}"

    try:
        first_response = client.post(
            "/api/accounts",
            headers=auth_headers("sales1"),
            json={"account_name": first_name, "qualification_source": "manual"},
        )
        assert first_response.status_code == 201
        first_account = first_response.json()["account"]
        created_public_ids.append(first_account["public_id"])

        second_response = client.post(
            "/api/accounts",
            headers=auth_headers("sales1"),
            json={"account_name": second_name, "qualification_source": "manual"},
        )
        assert second_response.status_code == 201
        second_account = second_response.json()["account"]
        created_public_ids.append(second_account["public_id"])

        first_page_response = client.get(
            "/api/accounts?limit=1&offset=0",
            headers=auth_headers("sales1"),
        )
        assert first_page_response.status_code == 200
        first_page = first_page_response.json()
        assert len(first_page) == 1
        assert first_page[0]["public_id"] == second_account["public_id"]

        second_page_response = client.get(
            "/api/accounts?limit=1&offset=1",
            headers=auth_headers("sales1"),
        )
        assert second_page_response.status_code == 200
        second_page = second_page_response.json()
        assert len(second_page) == 1
        assert second_page[0]["public_id"] == first_account["public_id"]
    finally:
        cleanup_test_accounts(created_public_ids)


def test_account_contacts_require_authentication() -> None:
    response = client.get(f"/api/accounts/{uuid4()}/contacts")

    assert response.status_code == 401


def test_sales_user_can_create_and_list_account_contact() -> None:
    created_account_public_ids: list[str] = []
    created_contact_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        create_response = client.post(
            f"/api/accounts/{account_public_id}/contacts",
            headers=auth_headers("sales1"),
            json={
                "contact_name": "Slice 1G Contact Person",
                "designation": "Procurement Manager",
                "department": "Commercial",
                "phone": "+91-9876543210",
                "email": "contact.slice1g@example.com",
                "is_primary": True,
                "remarks": "Created by Slice 1G API test.",
            },
        )

        assert create_response.status_code == 201
        body = create_response.json()
        created_contact_public_ids.append(body["contact"]["public_id"])
        assert body["contact"]["account_public_id"] == account_public_id
        assert body["contact"]["contact_name"] == "Slice 1G Contact Person"
        assert body["contact"]["email"] == "contact.slice1g@example.com"
        assert body["contact"]["is_primary"] is True
        assert body["event"]["event_name"] == "AccountContactCreated"
        assert body["event"]["record_type"] == "business_party_contact"
        assert body["event"]["record_public_id"] == body["contact"]["public_id"]
        assert "password" not in str(body).lower()

        list_response = client.get(
            f"/api/accounts/{account_public_id}/contacts",
            headers=auth_headers("readonly1"),
        )

        assert list_response.status_code == 200
        contacts = list_response.json()
        assert any(contact["public_id"] == body["contact"]["public_id"] for contact in contacts)
    finally:
        cleanup_test_records(
            account_public_ids=created_account_public_ids,
            contact_public_ids=created_contact_public_ids,
        )


def test_finance_user_can_view_but_cannot_create_account_contact() -> None:
    created_account_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        list_response = client.get(
            f"/api/accounts/{account_public_id}/contacts",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200

        create_response = client.post(
            f"/api/accounts/{account_public_id}/contacts",
            headers=auth_headers("finance1"),
            json={"contact_name": "Finance Should Not Create"},
        )
        assert create_response.status_code == 403
    finally:
        cleanup_test_records(account_public_ids=created_account_public_ids)


def test_create_account_contact_rejects_missing_account() -> None:
    response = client.post(
        f"/api/accounts/{uuid4()}/contacts",
        headers=auth_headers("sales1"),
        json={"contact_name": "Missing Account Contact"},
    )

    assert response.status_code == 404


def test_create_account_contact_rejects_invalid_email() -> None:
    created_account_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        response = client.post(
            f"/api/accounts/{account_public_id}/contacts",
            headers=auth_headers("sales1"),
            json={"contact_name": "Invalid Email Contact", "email": "not-an-email"},
        )

        assert response.status_code == 422
    finally:
        cleanup_test_records(account_public_ids=created_account_public_ids)


def test_account_addresses_require_authentication() -> None:
    response = client.get(f"/api/accounts/{uuid4()}/addresses")

    assert response.status_code == 401


def test_sales_user_can_create_and_list_account_address() -> None:
    created_account_public_ids: list[str] = []
    created_address_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        create_response = client.post(
            f"/api/accounts/{account_public_id}/addresses",
            headers=auth_headers("sales1"),
            json={
                "address_type_code": "COMMUNICATION",
                "address_line1": "Slice 1H Test Address Line 1",
                "address_line2": "Industrial Area",
                "city": "Bengaluru",
                "district": "Bengaluru Urban",
                "state": "Karnataka",
                "postal_code": "560001",
                "country_code": "IN",
                "is_primary": True,
                "remarks": "Created by Slice 1H API test.",
            },
        )

        assert create_response.status_code == 201
        body = create_response.json()
        created_address_public_ids.append(body["address"]["public_id"])
        assert body["address"]["account_public_id"] == account_public_id
        assert body["address"]["address_type_code"] == "COMMUNICATION"
        assert body["address"]["city"] == "Bengaluru"
        assert body["address"]["is_primary"] is True
        assert body["event"]["event_name"] == "AccountAddressCreated"
        assert body["event"]["record_type"] == "business_party_address"
        assert body["event"]["record_public_id"] == body["address"]["public_id"]
        assert "password" not in str(body).lower()

        list_response = client.get(
            f"/api/accounts/{account_public_id}/addresses",
            headers=auth_headers("readonly1"),
        )

        assert list_response.status_code == 200
        addresses = list_response.json()
        assert any(address["public_id"] == body["address"]["public_id"] for address in addresses)
    finally:
        cleanup_test_records(
            account_public_ids=created_account_public_ids,
            address_public_ids=created_address_public_ids,
        )


def test_finance_user_can_view_but_cannot_create_account_address() -> None:
    created_account_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        list_response = client.get(
            f"/api/accounts/{account_public_id}/addresses",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200

        create_response = client.post(
            f"/api/accounts/{account_public_id}/addresses",
            headers=auth_headers("finance1"),
            json={
                "address_type_code": "COMMUNICATION",
                "address_line1": "Finance Should Not Create",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        )
        assert create_response.status_code == 403
    finally:
        cleanup_test_records(account_public_ids=created_account_public_ids)


def test_create_account_address_rejects_missing_account() -> None:
    response = client.post(
        f"/api/accounts/{uuid4()}/addresses",
        headers=auth_headers("sales1"),
        json={
            "address_type_code": "COMMUNICATION",
            "address_line1": "Missing Account Address",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
    )

    assert response.status_code == 404


def test_create_account_address_rejects_invalid_type() -> None:
    created_account_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        response = client.post(
            f"/api/accounts/{account_public_id}/addresses",
            headers=auth_headers("sales1"),
            json={
                "address_type_code": "FINANCE_APPROVED_BILLING",
                "address_line1": "Invalid Type Address",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        )

        assert response.status_code == 422
    finally:
        cleanup_test_records(account_public_ids=created_account_public_ids)


def test_account_tax_profile_requires_authentication() -> None:
    response = client.get(f"/api/accounts/{uuid4()}/tax-profile")

    assert response.status_code == 401


def test_sales_user_can_upsert_tax_profile_and_create_gstin() -> None:
    created_account_public_ids: list[str] = []
    created_tax_profile_public_ids: list[str] = []
    created_gstin_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        profile_response = client.post(
            f"/api/accounts/{account_public_id}/tax-profile",
            headers=auth_headers("sales1"),
            json={
                "pan": unique_pan(),
                "pan_verification_state_code": "ENTERED_NOT_VERIFIED",
                "pan_legal_name": "Slice 1I Test Private Limited",
                "remarks": "Created by Slice 1I API test.",
            },
        )

        assert profile_response.status_code == 200
        profile_body = profile_response.json()
        created_tax_profile_public_ids.append(profile_body["tax_profile"]["public_id"])
        assert profile_body["tax_profile"]["account_public_id"] == account_public_id
        assert profile_body["tax_profile"]["pan"] is not None
        assert profile_body["tax_profile"]["pan_verification_state_code"] == "ENTERED_NOT_VERIFIED"
        assert profile_body["event"]["event_name"] == "AccountTaxProfileCaptured"
        assert profile_body["event"]["record_type"] == "business_party_tax_profile"

        gstin_response = client.post(
            f"/api/accounts/{account_public_id}/gstins",
            headers=auth_headers("sales1"),
            json={
                "gstin": unique_gstin(),
                "gstin_verification_state_code": "ENTERED_NOT_VERIFIED",
                "state_name": "Karnataka",
                "legal_name": "Slice 1I Test Private Limited",
                "trade_name": "Slice 1I Test",
                "is_primary": True,
                "remarks": "Created by Slice 1I API test.",
            },
        )

        assert gstin_response.status_code == 201
        gstin_body = gstin_response.json()
        created_gstin_public_ids.append(gstin_body["gstin"]["public_id"])
        assert gstin_body["gstin"]["account_public_id"] == account_public_id
        assert gstin_body["gstin"]["state_code"] == "29"
        assert gstin_body["gstin"]["is_primary"] is True
        assert gstin_body["event"]["event_name"] == "AccountGstinCaptured"
        assert gstin_body["event"]["record_type"] == "business_party_gstin"

        bundle_response = client.get(
            f"/api/accounts/{account_public_id}/tax-profile",
            headers=auth_headers("readonly1"),
        )
        assert bundle_response.status_code == 200
        bundle = bundle_response.json()
        assert bundle["tax_profile"]["public_id"] == profile_body["tax_profile"]["public_id"]
        assert any(gstin["public_id"] == gstin_body["gstin"]["public_id"] for gstin in bundle["gstins"])
        assert "password" not in str(bundle).lower()
    finally:
        cleanup_test_records(
            account_public_ids=created_account_public_ids,
            tax_profile_public_ids=created_tax_profile_public_ids,
            gstin_public_ids=created_gstin_public_ids,
        )


def test_finance_user_can_capture_and_verify_tax_profile_and_gstin() -> None:
    created_account_public_ids: list[str] = []
    created_tax_profile_public_ids: list[str] = []
    created_gstin_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        list_response = client.get(
            f"/api/accounts/{account_public_id}/tax-profile",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200

        profile_response = client.post(
            f"/api/accounts/{account_public_id}/tax-profile",
            headers=auth_headers("finance1"),
            json={
                "pan": unique_pan(),
                "pan_verification_state_code": "VERIFIED",
            },
        )
        assert profile_response.status_code == 200
        profile_body = profile_response.json()
        created_tax_profile_public_ids.append(profile_body["tax_profile"]["public_id"])
        assert profile_body["tax_profile"]["pan_verification_state_code"] == "VERIFIED"

        gstin_response = client.post(
            f"/api/accounts/{account_public_id}/gstins",
            headers=auth_headers("finance1"),
            json={
                "gstin": unique_gstin(),
                "gstin_verification_state_code": "VERIFIED",
            },
        )
        assert gstin_response.status_code == 201
        gstin_body = gstin_response.json()
        created_gstin_public_ids.append(gstin_body["gstin"]["public_id"])
        assert gstin_body["gstin"]["gstin_verification_state_code"] == "VERIFIED"
    finally:
        cleanup_test_records(
            account_public_ids=created_account_public_ids,
            tax_profile_public_ids=created_tax_profile_public_ids,
            gstin_public_ids=created_gstin_public_ids,
        )


def test_sales_user_cannot_set_verified_tax_states() -> None:
    created_account_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        profile_response = client.post(
            f"/api/accounts/{account_public_id}/tax-profile",
            headers=auth_headers("sales1"),
            json={
                "pan": unique_pan(),
                "pan_verification_state_code": "VERIFIED",
            },
        )
        assert profile_response.status_code == 403

        gstin_response = client.post(
            f"/api/accounts/{account_public_id}/gstins",
            headers=auth_headers("sales1"),
            json={
                "gstin": unique_gstin(),
                "gstin_verification_state_code": "VERIFIED",
            },
        )
        assert gstin_response.status_code == 403
    finally:
        cleanup_test_records(account_public_ids=created_account_public_ids)


def test_create_tax_profile_rejects_missing_account() -> None:
    response = client.post(
        f"/api/accounts/{uuid4()}/tax-profile",
        headers=auth_headers("sales1"),
        json={"pan": unique_pan()},
    )

    assert response.status_code == 404


def test_create_tax_profile_rejects_invalid_pan() -> None:
    created_account_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        response = client.post(
            f"/api/accounts/{account_public_id}/tax-profile",
            headers=auth_headers("sales1"),
            json={"pan": "BADPAN123"},
        )

        assert response.status_code == 422
    finally:
        cleanup_test_records(account_public_ids=created_account_public_ids)


def test_create_gstin_rejects_invalid_gstin() -> None:
    created_account_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        response = client.post(
            f"/api/accounts/{account_public_id}/gstins",
            headers=auth_headers("sales1"),
            json={"gstin": "BADGSTIN"},
        )

        assert response.status_code == 422
    finally:
        cleanup_test_records(account_public_ids=created_account_public_ids)


def test_account_documents_require_authentication() -> None:
    response = client.get(f"/api/accounts/{uuid4()}/documents")

    assert response.status_code == 401


def test_sales_user_can_record_and_list_account_document() -> None:
    created_account_public_ids: list[str] = []
    created_document_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        create_response = client.post(
            f"/api/accounts/{account_public_id}/documents",
            headers=auth_headers("sales1"),
            json={
                "document_type": "KYC",
                "file_name": "slice-1j-kyc.pdf",
                "original_file_name": "slice-1j-kyc-original.pdf",
                "storage_mode": "external_link",
                "storage_path_or_url": "https://example.invalid/slice-1j-kyc.pdf",
                "version_no": 1,
                "status": "Linked",
                "remarks": "Created by Slice 1J Account document API test.",
            },
        )

        assert create_response.status_code == 201
        body = create_response.json()
        created_document_public_ids.append(body["document"]["public_id"])
        assert body["document"]["account_public_id"] == account_public_id
        assert body["document"]["document_type"] == "KYC"
        assert body["document"]["file_name"] == "slice-1j-kyc.pdf"
        assert body["document"]["status"] == "Linked"
        assert body["event"]["event_name"] == "AccountDocumentRecorded"
        assert body["event"]["record_type"] == "document_metadata"
        assert body["event"]["record_public_id"] == body["document"]["public_id"]
        assert "password" not in str(body).lower()

        list_response = client.get(
            f"/api/accounts/{account_public_id}/documents",
            headers=auth_headers("readonly1"),
        )

        assert list_response.status_code == 200
        documents = list_response.json()
        assert any(document["public_id"] == body["document"]["public_id"] for document in documents)
    finally:
        cleanup_test_records(
            account_public_ids=created_account_public_ids,
            document_public_ids=created_document_public_ids,
        )


def test_finance_user_can_record_account_document_but_operations_cannot() -> None:
    created_account_public_ids: list[str] = []
    created_document_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        finance_response = client.post(
            f"/api/accounts/{account_public_id}/documents",
            headers=auth_headers("finance1"),
            json={
                "document_type": "PAN",
                "file_name": "slice-1j-pan.pdf",
                "storage_mode": "external_link",
                "status": "Linked",
            },
        )
        assert finance_response.status_code == 201
        created_document_public_ids.append(finance_response.json()["document"]["public_id"])

        ops_response = client.post(
            f"/api/accounts/{account_public_id}/documents",
            headers=auth_headers("ops1"),
            json={
                "document_type": "OTHER",
                "file_name": "ops-should-not-create.txt",
                "storage_mode": "external_link",
                "status": "Linked",
            },
        )
        assert ops_response.status_code == 403
    finally:
        cleanup_test_records(
            account_public_ids=created_account_public_ids,
            document_public_ids=created_document_public_ids,
        )


def test_create_account_document_rejects_missing_account() -> None:
    response = client.post(
        f"/api/accounts/{uuid4()}/documents",
        headers=auth_headers("sales1"),
        json={
            "document_type": "OTHER",
            "file_name": "missing-account-document.txt",
            "storage_mode": "external_link",
            "status": "Linked",
        },
    )

    assert response.status_code == 404


def test_create_account_document_rejects_invalid_type_and_status() -> None:
    created_account_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        invalid_type_response = client.post(
            f"/api/accounts/{account_public_id}/documents",
            headers=auth_headers("sales1"),
            json={
                "document_type": "UNAPPROVED_TYPE",
                "file_name": "invalid-type.txt",
                "storage_mode": "external_link",
                "status": "Linked",
            },
        )
        assert invalid_type_response.status_code == 422

        invalid_status_response = client.post(
            f"/api/accounts/{account_public_id}/documents",
            headers=auth_headers("sales1"),
            json={
                "document_type": "OTHER",
                "file_name": "invalid-status.txt",
                "storage_mode": "external_link",
                "status": "Verified",
            },
        )
        assert invalid_status_response.status_code == 422
    finally:
        cleanup_test_records(account_public_ids=created_account_public_ids)


def test_sales_user_can_update_and_view_account_classification() -> None:
    created_account_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        update_response = client.put(
            f"/api/accounts/{account_public_id}/classification",
            headers=auth_headers("sales1"),
            json={
                "segment": "Key Account",
                "industry": "Infrastructure",
                "is_strategic_account": True,
                "classification_notes": "Created by Slice 1K API test.",
            },
        )

        assert update_response.status_code == 200
        body = update_response.json()
        assert body["classification"]["account_public_id"] == account_public_id
        assert body["classification"]["segment"] == "Key Account"
        assert body["classification"]["industry"] == "Infrastructure"
        assert body["classification"]["is_strategic_account"] is True
        assert body["event"]["event_name"] == "AccountClassificationUpdated"
        assert body["event"]["record_type"] == "business_party"
        assert body["event"]["record_public_id"] == account_public_id
        assert "password" not in str(body).lower()

        get_response = client.get(
            f"/api/accounts/{account_public_id}/classification",
            headers=auth_headers("readonly1"),
        )
        assert get_response.status_code == 200
        classification = get_response.json()
        assert classification["account_public_id"] == account_public_id
        assert classification["segment"] == "Key Account"
        assert classification["is_strategic_account"] is True
    finally:
        cleanup_test_records(account_public_ids=created_account_public_ids)


def test_finance_user_can_view_but_cannot_update_account_classification() -> None:
    created_account_public_ids: list[str] = []

    try:
        account = create_test_account("sales1")
        account_public_id = str(account["public_id"])
        created_account_public_ids.append(account_public_id)

        list_response = client.get(
            f"/api/accounts/{account_public_id}/classification",
            headers=auth_headers("finance1"),
        )
        assert list_response.status_code == 200

        update_response = client.put(
            f"/api/accounts/{account_public_id}/classification",
            headers=auth_headers("finance1"),
            json={
                "segment": "Finance Should Not Update",
                "industry": "Blocked",
                "is_strategic_account": True,
            },
        )
        assert update_response.status_code == 403
    finally:
        cleanup_test_records(account_public_ids=created_account_public_ids)


def test_update_account_classification_rejects_missing_account() -> None:
    response = client.put(
        f"/api/accounts/{uuid4()}/classification",
        headers=auth_headers("sales1"),
        json={"segment": "Missing Account"},
    )

    assert response.status_code == 404
