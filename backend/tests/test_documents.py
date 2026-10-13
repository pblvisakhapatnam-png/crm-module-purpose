from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app

client = TestClient(app)


def _delete_documents_for_linked_record(linked_record_public_id: str) -> None:
    """Remove only the `document_metadata` rows created against one linked-record id.

    The caller generates that id fresh per run, so this can never match a pre-existing
    document row. Deliberately narrow: it deletes by the test's own generated identity
    rather than by file name, document type or any other value real data could share.

    The `DocumentMetadataCreated` business event is not deleted here - the session-scoped
    fixture in `conftest.py` already removes events this test session created.
    """
    with SessionLocal() as db:
        db.execute(
            text(
                """
                DELETE FROM document_metadata
                WHERE linked_record_type = 'account'
                  AND linked_record_public_id = :linked_record_public_id
                """
            ),
            {"linked_record_public_id": linked_record_public_id},
        )
        db.commit()


def login(username: str = "admin1", password: str = "password") -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_document_types_require_authentication() -> None:
    response = client.get("/api/documents/types")
    assert response.status_code in (401, 403)


def test_document_types_load_for_authenticated_user() -> None:
    token = login("sales1", "password")
    response = client.get(
        "/api/documents/types",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    codes = [item["code"] for item in response.json()]
    assert "PAN" in codes
    assert "GST" in codes
    assert "OTHER" in codes


def test_create_and_list_document_metadata() -> None:
    token = login("admin1", "password")
    # Generated before the request so the finally block can always locate this test's row,
    # including when the request succeeds but a later assertion fails.
    linked_record_public_id = str(uuid4())

    try:
        create_response = client.post(
            "/api/documents/metadata",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "document_type": "KYC",
                "linked_record_type": "account",
                "linked_record_public_id": linked_record_public_id,
                "file_name": "sample-kyc.pdf",
                "original_file_name": "sample-kyc.pdf",
                "storage_mode": "external_link",
                "storage_path_or_url": "https://example.invalid/sample-kyc.pdf",
                "version_no": 1,
                "status": "Linked",
                "remarks": "Test document metadata only.",
            },
        )

        assert create_response.status_code == 201
        body = create_response.json()
        assert body["document"]["document_type"] == "KYC"
        assert body["document"]["linked_record_type"] == "account"
        assert body["event"]["event_name"] == "DocumentMetadataCreated"
        assert "password" not in str(body).lower()

        record_response = client.get(
            f"/api/documents/by-record/account/{linked_record_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert record_response.status_code == 200
        docs = record_response.json()
        assert any(doc["file_name"] == "sample-kyc.pdf" for doc in docs)
    finally:
        _delete_documents_for_linked_record(linked_record_public_id)


def test_invalid_document_storage_mode_is_rejected() -> None:
    token = login("admin1", "password")
    response = client.post(
        "/api/documents/metadata",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "document_type": "OTHER",
            "linked_record_type": "account",
            "linked_record_public_id": str(uuid4()),
            "file_name": "bad-storage.txt",
            "storage_mode": "unknown_storage",
            "status": "Linked",
        },
    )
    assert response.status_code == 422