"""Slice 9C - Document Storage Foundation regression tests.

Each test below maps to one numbered item in the "Test plan" section of
docs/agent/slices/slice-9c-document-storage-foundation.md, written to fail first against the
pre-9C code before the corresponding fix existed. Item 10 (route inventory guard / frozen
31-110-76 counts) is covered by test_authorization_route_migration_guard.py and
test_authorization_post_baseline_catalogue.py directly; this file adds one redundant explicit
check for this slice's own visibility, run alongside the others.
"""

from __future__ import annotations

import contextlib
import json
import tempfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.modules.authorization.contract import EFFECTIVE_ROLE_PERMISSION_MATRIX
from app.modules.documents.contract import MAX_UPLOAD_BYTES
from app.modules.documents.schemas import DocumentMetadataCreate
from app.modules.documents.service import (
    DocumentAccessDeniedError,
    DocumentUploadTooLargeError,
    DocumentValidationError,
    _SizeLimitingReader,
    create_document_metadata,
    list_documents_for_record_for_caller,
    upload_document,
)
from app.modules.documents.storage import get_storage_provider, get_storage_provider_by_code
from app.modules.documents.storage.base import StorageKeyError, UnknownStorageProviderError
from app.modules.documents.storage.local import LocalFilesystemStorageProvider
from app.modules.identity.schemas import AuthUser

client = TestClient(app)


def login(username: str = "admin1", password: str = "password") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_headers(username: str, password: str = "password") -> dict[str, str]:
    return {"Authorization": f"Bearer {login(username, password)}"}


def _purge_stored_objects(where_clause: str, params: dict[str, str]) -> None:
    """Delete the stored bytes for the matching rows, BEFORE the rows themselves are removed.

    Order matters: once the row is gone, `storage_key` is gone with it and the object can no
    longer be located, which is exactly how the pre-correction helpers leaked a file for every
    successful-upload test (independent review, correction pass 2).

    An unresolvable `storage_provider_code` falls back to the configured provider rather than
    giving up. That is deliberate and is test-environment reasoning, not production behaviour:
    `test_content_download_resolves_the_provider_recorded_on_the_row` *deliberately* rewrites a
    row's provider code to an unregistered value to prove the read path fails closed, but the
    bytes it wrote are still physically held by the local provider. Refusing to clean those up
    would leak the very object that test creates.
    """
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT storage_provider_code, storage_key FROM document_metadata "
                f"WHERE {where_clause} AND storage_key IS NOT NULL"
            ),
            params,
        ).fetchall()

    for provider_code, storage_key in rows:
        try:
            provider = get_storage_provider_by_code(provider_code) if provider_code else get_storage_provider()
        except UnknownStorageProviderError:
            provider = get_storage_provider()
        with contextlib.suppress(Exception):
            provider.delete(storage_key=storage_key)


def _delete_document(public_id: str) -> None:
    _purge_stored_objects("document_public_id = :public_id", {"public_id": public_id})
    with SessionLocal() as db:
        db.execute(text("DELETE FROM document_metadata WHERE document_public_id = :public_id"), {"public_id": public_id})
        db.commit()


def _delete_documents_for_linked_record(linked_record_public_id: str) -> None:
    _purge_stored_objects(
        "linked_record_public_id = :public_id", {"public_id": linked_record_public_id}
    )
    with SessionLocal() as db:
        db.execute(
            text("DELETE FROM document_metadata WHERE linked_record_public_id = :public_id"),
            {"public_id": linked_record_public_id},
        )
        db.commit()


def _stored_file_count() -> int:
    """How many files the configured local storage root currently holds.

    Used to prove a rejected upload leaves no stored bytes behind, and to police the module as a
    whole (see the autouse fixture below). Counts through the real configured root rather than a
    temp directory, because the point is the behaviour of the actual upload path, not of an
    isolated provider instance.
    """
    root = Path(get_settings().document_storage_root)
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file())


@pytest.fixture(scope="module", autouse=True)
def _no_stored_object_is_leaked_by_this_module():
    """Fail the module if it finishes holding more stored objects than it started with.

    The structural half of correction pass 2's fix. Repairing the cleanup helpers stops the two
    known leaks; this stops the NEXT one, because a future test that uploads a file and forgets
    to clean it up fails here instead of quietly leaving an object behind on every run - which
    is exactly how the original leak survived a full-suite run, a targeted file run, and a
    manual volume inspection without being noticed.
    """
    before = _stored_file_count()
    yield
    after = _stored_file_count()
    assert after == before, (
        f"this module leaked {after - before} stored object(s) into "
        f"{get_settings().document_storage_root} (started with {before}, ended with {after}). "
        "A test that uploads a file must clean it up through _delete_document / "
        "_delete_documents_for_linked_record, which delete the stored bytes as well as the row."
    )


# =============================================================================================
# Item 1: a direct INSERT of storage_mode='local_upload' without bytes is refused by the
# database CHECK constraint, bypassing the API entirely.
# =============================================================================================


def test_direct_insert_of_local_upload_without_bytes_is_rejected_by_the_database() -> None:
    with SessionLocal() as db:
        with pytest.raises(IntegrityError) as exc:
            db.execute(
                text(
                    """
                    INSERT INTO document_metadata (
                        document_public_id, document_type, linked_record_type,
                        linked_record_public_id, file_name, storage_mode, version_no, status
                    ) VALUES (
                        :public_id, 'OTHER', 'account', :linked_id, 'sneaky.pdf',
                        'local_upload', 1, 'Uploaded'
                    )
                    """
                ),
                {"public_id": str(uuid4()), "linked_id": str(uuid4())},
            )
            db.commit()
        assert "ck_document_metadata_local_upload_has_bytes" in str(exc.value)
        db.rollback()


def test_direct_insert_of_local_upload_with_all_four_columns_populated_succeeds() -> None:
    """The constraint's other side: it does not block a genuinely complete local_upload row -
    only one missing evidence of actually-stored bytes."""
    public_id = str(uuid4())
    linked_id = str(uuid4())
    try:
        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    INSERT INTO document_metadata (
                        document_public_id, document_type, linked_record_type,
                        linked_record_public_id, file_name, storage_mode, version_no, status,
                        storage_provider_code, storage_key, byte_size, checksum_sha256
                    ) VALUES (
                        :public_id, 'OTHER', 'account', :linked_id, 'real.pdf', 'local_upload',
                        1, 'Uploaded', 'local', 'ab/cd/real.pdf', 10, :checksum
                    )
                    """
                ),
                {"public_id": public_id, "linked_id": linked_id, "checksum": "a" * 64},
            )
            db.commit()
    finally:
        _delete_document(public_id)


# =============================================================================================
# Item 2: POST /api/documents/metadata rejects storage_mode=local_upload.
# =============================================================================================


def test_metadata_route_rejects_local_upload_storage_mode() -> None:
    response = client.post(
        "/api/documents/metadata",
        headers=_auth_headers("admin1"),
        json={
            "document_type": "OTHER",
            "linked_record_type": "account",
            "linked_record_public_id": str(uuid4()),
            "file_name": "fake.pdf",
            "storage_mode": "local_upload",
            "status": "Uploaded",
        },
    )
    assert response.status_code == 422
    assert "local_upload" in response.json()["detail"]


def test_create_document_metadata_service_rejects_local_upload_directly() -> None:
    with SessionLocal() as db:
        with pytest.raises(DocumentValidationError, match="local_upload"):
            create_document_metadata(
                db,
                payload=DocumentMetadataCreate(
                    document_type="OTHER",
                    linked_record_type="account",
                    linked_record_public_id=uuid4(),
                    file_name="fake.pdf",
                    storage_mode="local_upload",
                    status="Uploaded",
                ),
                current_user_public_id=None,
            )


# =============================================================================================
# Item 3: download denies when the caller lacks the linked record's own read permission.
#
# Every real seeded role currently holds every base link-read permission
# (ACCOUNT_READ/LEAD_READ/OPPORTUNITY_READ/COMMERCIAL_OFFER_READ/WORK_ORDER_READ/
# INTERACTION_READ are all granted to all six roles), so this cannot be demonstrated through a
# live HTTP login today. It is proven at the service level instead, with a caller holding no
# granted role at all - a genuine, realistic case (a deactivated account, or a service identity
# with no role assignment) that the fail-closed check must still refuse.
# =============================================================================================


def test_service_denies_record_scoped_read_for_a_caller_with_no_granted_role() -> None:
    roleless_user = AuthUser(
        public_id=str(uuid4()), username="no-roles", display_name="No Roles", roles=[], role_codes=[]
    )
    with SessionLocal() as db:
        with pytest.raises(DocumentAccessDeniedError):
            list_documents_for_record_for_caller(
                db,
                linked_record_type="account",
                linked_record_public_id=str(uuid4()),
                current_user=roleless_user,
            )


# =============================================================================================
# Item 4: download of an interaction-attached document denies without INTERACTION_CONTENT_READ.
#
# finance1 (FINANCE_USER) holds INTERACTION_READ but NOT INTERACTION_CONTENT_READ (a Slice 9D
# grant, deliberately excluding Finance from customer message content) - a genuine, real,
# HTTP-testable case.
# =============================================================================================


def test_download_of_interaction_linked_document_denies_finance_which_lacks_content_read() -> None:
    linked_id = str(uuid4())
    create_response = client.post(
        "/api/documents/metadata",
        headers=_auth_headers("admin1"),
        json={
            "document_type": "OTHER",
            "linked_record_type": "interaction",
            "linked_record_public_id": linked_id,
            "file_name": "customer-email.pdf",
            "storage_mode": "external_link",
            "storage_path_or_url": "https://example.invalid/customer-email.pdf",
            "status": "Linked",
        },
    )
    assert create_response.status_code == 201
    document_public_id = create_response.json()["document"]["public_id"]

    try:
        # Finance can see the document exists (INTERACTION_READ) ...
        list_response = client.get(
            f"/api/documents/by-record/interaction/{linked_id}",
            headers=_auth_headers("finance1"),
        )
        assert list_response.status_code == 200
        assert any(doc["public_id"] == document_public_id for doc in list_response.json())

        # ... but may not download its content (lacks INTERACTION_CONTENT_READ).
        download_response = client.get(
            f"/api/documents/{document_public_id}/content",
            headers=_auth_headers("finance1"),
        )
        assert download_response.status_code == 403
    finally:
        _delete_document(document_public_id)


# =============================================================================================
# Item 5: an unknown linked_record_type denies - fail-closed.
# =============================================================================================


def test_by_record_listing_denies_for_an_unmapped_linked_record_type() -> None:
    response = client.get(
        f"/api/documents/by-record/totally_unmapped_type/{uuid4()}",
        headers=_auth_headers("admin1"),
    )
    assert response.status_code == 403


def _record_a_document_linked_to_an_unmapped_type(file_name: str) -> str:
    """Create a document row linked to a type no map knows, through the service directly.

    These tests used to create the row through POST /api/documents/metadata. That route now
    refuses an unmapped type outright - the attach check added on 11 September 2026 is fail-closed
    like the read check - so such a row can no longer be created over HTTP. It can still exist:
    linked_record_type is unconstrained VARCHAR, and rows written before that check, or by an
    in-process caller, may carry any value. That is what the read-side assertions below guard
    against, so they need the row and are unchanged. The row itself is the same shape the route
    used to write.
    """
    with SessionLocal() as db:
        created = create_document_metadata(
            db,
            payload=DocumentMetadataCreate(
                document_type="OTHER",
                linked_record_type="totally_unmapped_type",
                linked_record_public_id=uuid4(),
                file_name=file_name,
                storage_mode="external_link",
                storage_path_or_url=f"https://example.invalid/{file_name}",
                status="Linked",
            ),
            current_user_public_id=None,
        )
    return str(created.document.public_id)


def test_content_download_denies_for_a_document_linked_to_an_unmapped_type() -> None:
    document_public_id = _record_a_document_linked_to_an_unmapped_type("orphan.pdf")
    try:
        response = client.get(
            f"/api/documents/{document_public_id}/content",
            headers=_auth_headers("admin1"),
        )
        assert response.status_code == 403
    finally:
        _delete_document(document_public_id)


# =============================================================================================
# Item 6: GET /api/documents/recent omits rows whose linked record the caller may not read.
# =============================================================================================


def test_recent_documents_omits_a_row_linked_to_an_unmapped_record_type() -> None:
    document_public_id = _record_a_document_linked_to_an_unmapped_type("should-not-list.pdf")

    try:
        recent_response = client.get(
            "/api/documents/recent?limit=100",
            headers=_auth_headers("admin1"),
        )
        assert recent_response.status_code == 200
        visible_ids = {doc["public_id"] for doc in recent_response.json()}
        assert document_public_id not in visible_ids
    finally:
        _delete_document(document_public_id)


# =============================================================================================
# Item 7: the storage provider refuses a traversal-shaped storage_key.
# =============================================================================================


def test_local_storage_provider_refuses_a_path_traversal_storage_key() -> None:
    with tempfile.TemporaryDirectory() as root:
        provider = LocalFilesystemStorageProvider(root=root)
        before = sorted(Path(root).rglob("*"))
        with pytest.raises(StorageKeyError):
            provider.save(
                storage_key="../../etc/passwd",
                stream=BytesIO(b"malicious"),
                content_type="text/plain",
            )
        # Refused before writing anything - nothing new appeared inside the provider's own
        # root either. (The escaped target itself, a real system path, is deliberately never
        # inspected here - a test must not assert on or depend on unrelated host filesystem
        # state such as /etc/passwd.)
        assert sorted(Path(root).rglob("*")) == before


def test_local_storage_provider_refuses_an_absolute_path_storage_key() -> None:
    with tempfile.TemporaryDirectory() as root:
        provider = LocalFilesystemStorageProvider(root=root)
        with pytest.raises(StorageKeyError):
            provider.save(storage_key="/etc/passwd", stream=BytesIO(b"x"), content_type="text/plain")


def test_local_storage_provider_reports_an_unusable_root_with_an_actionable_message() -> None:
    """An unwritable/uncreatable root must name the setting to change.

    Added after CI: the default root is a container-absolute path (`/app/document-store`,
    matching the Compose volume). The backend-regression job runs pytest on the runner rather
    than in the container, so provider construction failed with a bare
    `PermissionError: '/app'` from inside pathlib - accurate, and useless for working out what
    to configure.
    """
    from app.modules.documents.storage.base import DocumentStorageError

    with tempfile.TemporaryDirectory() as parent:
        blocked = Path(parent) / "not-a-directory"
        blocked.write_text("this is a file, so a directory cannot be created beneath it")

        with pytest.raises(DocumentStorageError) as exc:
            LocalFilesystemStorageProvider(root=str(blocked / "storage"))

        message = str(exc.value)
        assert "DOCUMENT_STORAGE_ROOT" in message, "the error must name the setting to change"
        assert str(blocked / "storage") in message or "storage" in message


def test_local_storage_provider_accepts_a_genuine_nested_key() -> None:
    with tempfile.TemporaryDirectory() as root:
        provider = LocalFilesystemStorageProvider(root=root)
        stored = provider.save(
            storage_key="ab/cd/real-file.pdf", stream=BytesIO(b"hello world"), content_type="application/pdf"
        )
        assert stored.byte_size == 11
        assert provider.exists(storage_key="ab/cd/real-file.pdf")
        provider.delete(storage_key="ab/cd/real-file.pdf")
        assert not provider.exists(storage_key="ab/cd/real-file.pdf")


# =============================================================================================
# Item 8: an oversize upload is rejected by streamed byte count, tested both at the true HTTP
# boundary and directly against the byte-counting mechanism, never against a declared header.
# =============================================================================================


# A valid PDF header, so the content check (added by the upload package) does not refuse these
# bodies as "not a PDF" before their size is counted. The bodies stay exactly one byte over the
# limit, so a relaxation of even a single byte still fails these tests.
_PDF_HEADER = b"%PDF-1.4\n"
_ONE_OVER_LIMIT_PDF = _PDF_HEADER + b"x" * (MAX_UPLOAD_BYTES - len(_PDF_HEADER) + 1)


def test_upload_route_rejects_a_file_larger_than_the_configured_limit() -> None:
    assert len(_ONE_OVER_LIMIT_PDF) == MAX_UPLOAD_BYTES + 1
    oversized_body = _ONE_OVER_LIMIT_PDF
    response = client.post(
        "/api/documents/upload",
        headers=_auth_headers("admin1"),
        data={
            "linked_record_type": "account",
            "linked_record_public_id": str(uuid4()),
            "document_type": "OTHER",
        },
        files={"file": ("too-big.pdf", oversized_body, "application/pdf")},
    )
    assert response.status_code == 413


def test_service_size_limit_is_enforced_by_counting_bytes_never_by_a_declared_size_hint() -> None:
    """Direct proof of the mechanism itself: a stream that yields more bytes than any declared
    size would suggest is still caught, because nothing in the code path consults a declared
    size at all - only what actually crosses the reader's own .read() calls.
    """
    with SessionLocal() as db:
        with pytest.raises(DocumentUploadTooLargeError):
            upload_document(
                db,
                linked_record_type="account",
                linked_record_public_id=uuid4(),
                document_type="OTHER",
                file_name="huge.pdf",
                declared_content_type="application/pdf",
                # A PDF header first, for the same reason as the HTTP test above, and exactly one
                # byte over the limit so a single-byte relaxation still fails here.
                stream=BytesIO(_ONE_OVER_LIMIT_PDF),
                remarks=None,
                current_user_public_id=None,
            )


def test_the_size_limit_accepts_exactly_the_limit_and_rejects_one_byte_more() -> None:
    """The exact boundary, proven against the counting mechanism itself: a stream of exactly
    MAX_UPLOAD_BYTES is read in full without raising, and one byte more raises. This pins the limit
    from both sides, so neither a one-byte relaxation nor a one-byte tightening passes unnoticed.
    """

    def read_all(reader: _SizeLimitingReader) -> int:
        total = 0
        while True:
            chunk = reader.read(1 << 20)
            if not chunk:
                return total
            total += len(chunk)

    at_limit = _SizeLimitingReader(BytesIO(b"x" * MAX_UPLOAD_BYTES), max_bytes=MAX_UPLOAD_BYTES)
    assert read_all(at_limit) == MAX_UPLOAD_BYTES

    one_over = _SizeLimitingReader(BytesIO(b"x" * (MAX_UPLOAD_BYTES + 1)), max_bytes=MAX_UPLOAD_BYTES)
    with pytest.raises(DocumentUploadTooLargeError):
        read_all(one_over)


def test_documents_module_never_reads_a_content_length_style_header_value() -> None:
    """Structural guard: the size limit must never be implemented by trusting a
    caller-declared header or form field. Deliberately narrower than a blunt substring search
    for "content-length" - this module's own docstrings legitimately discuss why that header is
    NOT consulted, which a naive text search cannot distinguish from actually reading one. This
    checks for the concrete access patterns that would constitute reading it instead:
    `.headers[`, `.headers.get(`, or a FastAPI `Header(...)` parameter declaration - none of
    which either module has any legitimate reason to contain, since neither declares a route
    parameter sourced from a request header.
    """
    import app.modules.documents.routes as routes_module
    import app.modules.documents.service as service_module

    for module in (service_module, routes_module):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert ".headers[" not in source
        assert ".headers.get(" not in source
        assert "Header(" not in source, f"{module.__name__} declares a Header(...) parameter"


# =============================================================================================
# Item 9: a document_type containing a double quote produces valid, unforged event JSON.
# =============================================================================================


def test_document_type_with_a_double_quote_produces_valid_unforged_event_payload() -> None:
    malicious_document_type = 'OTHER" , "linked_record_type":"business_party'
    linked_id = str(uuid4())
    response = client.post(
        "/api/documents/metadata",
        headers=_auth_headers("admin1"),
        json={
            "document_type": malicious_document_type,
            "linked_record_type": "account",
            "linked_record_public_id": linked_id,
            "file_name": "quote-test.pdf",
            "storage_mode": "external_link",
            "storage_path_or_url": "https://example.invalid/quote-test.pdf",
            "status": "Linked",
        },
    )
    assert response.status_code == 201
    body = response.json()
    document_public_id = body["document"]["public_id"]

    try:
        # The response's own parsed event_payload must carry the exact injected string, not a
        # truncated or corrupted one.
        assert body["event"]["event_payload"]["document_type"] == malicious_document_type
        assert body["event"]["event_payload"]["linked_record_type"] == "account", (
            "the malicious document_type must not have forged a second linked_record_type field"
        )

        # And the raw stored JSON must itself parse - proof the encoding is structurally sound,
        # not merely that this one field happened to survive.
        with SessionLocal() as db:
            row = db.execute(
                text(
                    "SELECT event_payload_json FROM business_event "
                    "WHERE record_public_id = :public_id AND event_name = 'DocumentMetadataCreated'"
                ),
                {"public_id": document_public_id},
            ).first()
        assert row is not None
        parsed = json.loads(row[0])
        assert parsed["document_type"] == malicious_document_type
    finally:
        _delete_document(document_public_id)


# =============================================================================================
# Item 10: the route inventory guard passes, and the frozen 31/110/76 counts are unchanged.
# Redundant explicit check for this slice's visibility; the authoritative proof is
# test_authorization_route_migration_guard.py and test_authorization_post_baseline_catalogue.py.
# =============================================================================================


def test_frozen_baseline_counts_are_unchanged_and_new_document_permissions_are_additive() -> None:
    from app.modules.authorization.contract import ROLE_PERMISSION_COMPATIBILITY_MATRIX
    from tests.fixtures.pf_1a_e1_baseline_authorization import BASELINE_ROUTE_PERMISSION_INVENTORY

    assert len(ROLE_PERMISSION_COMPATIBILITY_MATRIX) == 31
    assert sum(len(roles) for roles in ROLE_PERMISSION_COMPATIBILITY_MATRIX.values()) == 110
    assert len(BASELINE_ROUTE_PERMISSION_INVENTORY) == 76

    for code in ("DOCUMENT_READ", "DOCUMENT_UPLOAD", "DOCUMENT_CONTENT_READ"):
        assert code in EFFECTIVE_ROLE_PERMISSION_MATRIX
        assert code not in ROLE_PERMISSION_COMPATIBILITY_MATRIX


# =============================================================================================
# The tightening mechanism itself (POST_BASELINE_TIGHTENED_ROUTES), driven with synthetic input
# - a guard never shown to fail is an assertion of intent, not a control.
# =============================================================================================


def test_tightened_routes_guard_accepts_a_route_the_baseline_actually_recorded_as_ungated() -> None:
    from tests.fixtures.post_baseline_tightened_routes import assert_tightened_routes_were_baseline_ungated

    assert_tightened_routes_were_baseline_ungated(
        {("GET", "/api/fake"): "FAKE_PERMISSION"},
        frozenset({("GET", "/api/fake")}),
    )


def test_tightened_routes_guard_rejects_a_route_the_baseline_did_not_record_as_ungated() -> None:
    from tests.fixtures.post_baseline_tightened_routes import assert_tightened_routes_were_baseline_ungated

    with pytest.raises(RuntimeError, match="did not record as ungated"):
        assert_tightened_routes_were_baseline_ungated(
            {("GET", "/api/never-was-ungated"): "FAKE_PERMISSION"},
            frozenset({("GET", "/api/something-else")}),
        )


def test_post_baseline_tightened_routes_is_wired_into_module_import() -> None:
    """Proves the guard is not merely defined - if the real POST_BASELINE_TIGHTENED_ROUTES ever
    named a route the baseline did not record as ungated, importing the fixture must fail."""
    from tests.fixtures import post_baseline_tightened_routes as fixture_module

    source = Path(fixture_module.__file__).read_text(encoding="utf-8")
    assert "assert_tightened_routes_were_baseline_ungated(POST_BASELINE_TIGHTENED_ROUTES" in source, (
        "the tightened-routes guard is defined but no longer invoked at module import time"
    )


def test_all_four_tightened_documents_routes_were_genuinely_baseline_ungated() -> None:
    from tests.fixtures.pf_1a_e1_baseline_authorization import (
        BASELINE_ROUTE_PERMISSION_INVENTORY,
        BASELINE_UNGATED_ROUTES,
    )
    from tests.fixtures.post_baseline_tightened_routes import POST_BASELINE_TIGHTENED_ROUTES

    assert len(POST_BASELINE_TIGHTENED_ROUTES) == 4
    assert set(POST_BASELINE_TIGHTENED_ROUTES).issubset(BASELINE_UNGATED_ROUTES)
    assert set(POST_BASELINE_TIGHTENED_ROUTES).isdisjoint(BASELINE_ROUTE_PERMISSION_INVENTORY)


# =============================================================================================
# Correction pass 1 (independent review, 8 September 2026). Five material findings; every test
# below was written first and confirmed failing against the pre-correction code.
# =============================================================================================


# --- Finding 1: an upload with no declared content type was accepted -------------------------


def test_upload_with_no_declared_content_type_is_rejected() -> None:
    """The frozen specification requires validation on BOTH the extension and the declared
    content type. The pre-correction check read `if declared_content_type and ... != ...`, whose
    `and` short-circuited on a missing/empty type - so a multipart part carrying no MIME type at
    all skipped content-type validation entirely and returned 201. Reproduced with a real
    request against the running backend before this test existed.
    """
    linked_id = str(uuid4())
    response = client.post(
        "/api/documents/upload",
        headers=_auth_headers("admin1"),
        data={
            "linked_record_type": "account",
            "linked_record_public_id": linked_id,
            "document_type": "OTHER",
        },
        files={"file": ("no-type.pdf", b"%PDF-1.4 fake", "")},
    )
    try:
        assert response.status_code == 422, (
            f"expected 422 for a missing declared content type, got {response.status_code}"
        )
    finally:
        _delete_documents_for_linked_record(linked_id)


def test_upload_with_a_mismatched_declared_content_type_is_still_rejected() -> None:
    """The other half of the same check, so the fix cannot regress into accepting anything."""
    linked_id = str(uuid4())
    response = client.post(
        "/api/documents/upload",
        headers=_auth_headers("admin1"),
        data={
            "linked_record_type": "account",
            "linked_record_public_id": linked_id,
            "document_type": "OTHER",
        },
        files={"file": ("real.pdf", b"%PDF-1.4 fake", "application/x-msdownload")},
    )
    try:
        assert response.status_code == 422
    finally:
        _delete_documents_for_linked_record(linked_id)


# --- Finding 2: a Unicode filename broke the download response -------------------------------


def test_download_of_a_document_with_a_unicode_filename_succeeds() -> None:
    """`Content-Disposition` is encoded latin-1 by the ASGI layer. The pre-correction header
    interpolated the raw filename, so an ordinary Unicode name raised UnicodeEncodeError and the
    download failed outright.
    """
    linked_id = str(uuid4())
    unicode_name = "quotation-报价.pdf"
    upload = client.post(
        "/api/documents/upload",
        headers=_auth_headers("admin1"),
        data={
            "linked_record_type": "account",
            "linked_record_public_id": linked_id,
            "document_type": "OTHER",
        },
        files={"file": (unicode_name, b"%PDF-1.4 unicode name", "application/pdf")},
    )
    assert upload.status_code == 201
    public_id = upload.json()["document"]["public_id"]

    try:
        response = client.get(f"/api/documents/{public_id}/content", headers=_auth_headers("admin1"))
        assert response.status_code == 200
        assert response.content == b"%PDF-1.4 unicode name"

        disposition = response.headers["content-disposition"]
        # RFC 5987: an ASCII-safe fallback plus the real UTF-8 name, so a client that understands
        # filename* recovers the original and one that does not still gets a usable name rather
        # than a failed response.
        assert disposition.startswith("attachment;")
        assert "filename*=UTF-8''" in disposition
        assert disposition.isascii(), "the header itself must be ASCII-safe"
        assert "%E6%8A%A5%E4%BB%B7" in disposition, "the UTF-8 name must be percent-encoded"
    finally:
        _delete_documents_for_linked_record(linked_id)


def test_content_disposition_helper_handles_quotes_and_non_ascii() -> None:
    """Unit-level proof for the header builder itself, including the injection-shaped input a
    filename could carry - a quote must never terminate the quoted-string early."""
    from app.modules.documents.routes import _content_disposition

    header = _content_disposition('evil";rm -rf.pdf')
    assert header.isascii()
    assert header.count('"') == 2, f"filename quoting was broken by the input: {header}"

    assert _content_disposition("").startswith("attachment;")
    assert _content_disposition("报价.pdf").isascii()


# --- Finding 3: content was opened through the configured provider, not the stored one -------


def test_content_download_resolves_the_provider_recorded_on_the_row() -> None:
    """The row's `storage_provider_code` exists precisely so a stored object can be resolved back
    to the provider that holds it after a provider swap. The pre-correction code called
    `get_storage_provider()` - the currently *configured* provider - and ignored the column
    entirely, which would resolve content through the wrong backend after a swap.
    """
    linked_id = str(uuid4())
    upload = client.post(
        "/api/documents/upload",
        headers=_auth_headers("admin1"),
        data={
            "linked_record_type": "account",
            "linked_record_public_id": linked_id,
            "document_type": "OTHER",
        },
        files={"file": ("provider-check.pdf", b"%PDF-1.4 provider", "application/pdf")},
    )
    assert upload.status_code == 201
    public_id = upload.json()["document"]["public_id"]

    try:
        # Rewrite the stored provider code to one no registry knows. The bytes are still on disk
        # and the configured provider could still open them - so if the row's own code is being
        # ignored, this download wrongly succeeds.
        with SessionLocal() as db:
            db.execute(
                text(
                    "UPDATE document_metadata SET storage_provider_code = 'sharepoint_future' "
                    "WHERE document_public_id = :public_id"
                ),
                {"public_id": public_id},
            )
            db.commit()

        response = client.get(f"/api/documents/{public_id}/content", headers=_auth_headers("admin1"))
        assert response.status_code == 409, (
            "a row naming a provider this deployment cannot resolve must fail closed, not fall "
            f"back to the configured provider; got {response.status_code}"
        )
    finally:
        _delete_documents_for_linked_record(linked_id)


def test_storage_provider_lookup_by_code_fails_closed_for_an_unknown_code() -> None:
    from app.modules.documents.storage import get_storage_provider_by_code
    from app.modules.documents.storage.base import UnknownStorageProviderError

    with pytest.raises(UnknownStorageProviderError):
        get_storage_provider_by_code("no_such_provider")


def test_storage_provider_lookup_by_code_returns_the_local_provider() -> None:
    from app.modules.documents.contract import STORAGE_PROVIDER_LOCAL
    from app.modules.documents.storage import get_storage_provider_by_code

    provider = get_storage_provider_by_code(STORAGE_PROVIDER_LOCAL)
    assert provider.provider_code == STORAGE_PROVIDER_LOCAL


# --- Finding 4: multipart form fields bypassed length validation ------------------------------


def test_upload_with_an_over_length_linked_record_type_is_rejected_before_storing_bytes() -> None:
    """`linked_record_type` is VARCHAR(100). The pre-correction upload route declared it as a
    bare `Form(...)` with no length bound, so a 101-character value reached PostgreSQL and
    surfaced as a 500 rather than a 422. Reproduced against the running backend.
    """
    linked_id = str(uuid4())
    files_before = _stored_file_count()

    response = client.post(
        "/api/documents/upload",
        headers=_auth_headers("admin1"),
        data={
            "linked_record_type": "a" * 101,
            "linked_record_public_id": linked_id,
            "document_type": "OTHER",
        },
        files={"file": ("over-length.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 422, (
        f"expected 422 for an over-length linked_record_type, got {response.status_code}"
    )
    # And the rejection must leave nothing behind: no row, no event, no stored bytes.
    with SessionLocal() as db:
        row_count = db.execute(
            text("SELECT count(*) FROM document_metadata WHERE linked_record_public_id = :id"),
            {"id": linked_id},
        ).scalar_one()
        event_count = db.execute(
            text(
                "SELECT count(*) FROM business_event WHERE source_module = 'documents' "
                "AND event_payload_json LIKE :pattern"
            ),
            {"pattern": f"%{linked_id}%"},
        ).scalar_one()
    assert row_count == 0, "a rejected upload must not leave a document_metadata row"
    assert event_count == 0, "a rejected upload must not leave a business event"
    assert _stored_file_count() == files_before, "a rejected upload must not leave stored bytes"


def test_upload_with_an_over_length_file_name_is_rejected() -> None:
    linked_id = str(uuid4())
    response = client.post(
        "/api/documents/upload",
        headers=_auth_headers("admin1"),
        data={
            "linked_record_type": "account",
            "linked_record_public_id": linked_id,
            "document_type": "OTHER",
        },
        files={"file": (("n" * 260) + ".pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    try:
        assert response.status_code == 422
    finally:
        _delete_documents_for_linked_record(linked_id)


def test_upload_with_an_over_length_remarks_value_is_rejected() -> None:
    linked_id = str(uuid4())
    response = client.post(
        "/api/documents/upload",
        headers=_auth_headers("admin1"),
        data={
            "linked_record_type": "account",
            "linked_record_public_id": linked_id,
            "document_type": "OTHER",
            "remarks": "r" * 1001,
        },
        files={"file": ("remarks.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    try:
        assert response.status_code == 422
    finally:
        _delete_documents_for_linked_record(linked_id)


def test_upload_with_a_blank_linked_record_type_is_rejected() -> None:
    linked_id = str(uuid4())
    response = client.post(
        "/api/documents/upload",
        headers=_auth_headers("admin1"),
        data={
            "linked_record_type": "   ",
            "linked_record_public_id": linked_id,
            "document_type": "OTHER",
        },
        files={"file": ("blank.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    try:
        assert response.status_code == 422
    finally:
        _delete_documents_for_linked_record(linked_id)


# --- Finding 5: the two new routes were not pinned to their exact permissions -----------------


def test_the_two_new_document_routes_are_pinned_to_their_exact_permissions() -> None:
    """The guard's fallback branch only required a new route to carry SOME permission. Upload and
    content-download were therefore never pinned to DOCUMENT_UPLOAD / DOCUMENT_CONTENT_READ, so
    swapping one for the other - or for any other registered permission - would have passed.

    Filtered to /api/documents/* entries, not asserted as the whole POST_BASELINE_NEW_ROUTES
    dict: that dict is shared, growing fixture state across every slice that adds a new route
    (Slice 9E added three quote-document routes to the same dict), so an exact-equality
    assertion against the whole thing would break the first time any later slice touched it -
    exactly what happened here. This mirrors the /api/documents path filter the neighbouring
    test below already applies.
    """
    from tests.fixtures.post_baseline_tightened_routes import POST_BASELINE_NEW_ROUTES

    document_routes = {key: value for key, value in POST_BASELINE_NEW_ROUTES.items() if key[1].startswith("/api/documents")}
    assert document_routes == {
        ("POST", "/api/documents/upload"): "DOCUMENT_UPLOAD",
        ("GET", "/api/documents/{public_id}/content"): "DOCUMENT_CONTENT_READ",
    }


def test_every_document_route_requests_exactly_the_permission_the_fixtures_pin() -> None:
    """Introspective proof against the live app, independent of the guard test file: each of the
    six document routes carries exactly one permission dependency, and it is exactly the one the
    post-baseline fixtures name.

    Filtered to /api/documents/* entries from the two shared fixture dicts, not their full
    contents: both dicts accumulate entries from every later slice that adds or tightens a
    route anywhere in the app (Slice 9E added three quote-document entries to
    POST_BASELINE_NEW_ROUTES), so this module's own test must scope itself to the routes it
    actually owns rather than asserting a fixed total across the whole shared fixture.
    """
    from fastapi.routing import APIRoute

    from tests.fixtures.post_baseline_tightened_routes import (
        POST_BASELINE_NEW_ROUTES,
        POST_BASELINE_TIGHTENED_ROUTES,
    )

    expected = {
        key: value
        for key, value in {**POST_BASELINE_TIGHTENED_ROUTES, **POST_BASELINE_NEW_ROUTES}.items()
        if key[1].startswith("/api/documents")
    }
    assert len(expected) == 6

    seen: dict[tuple[str, str], list[str]] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/documents"):
            continue
        for method in route.methods or []:
            codes: list[str] = []
            stack = list(route.dependant.dependencies)
            while stack:
                dependency = stack.pop()
                code = getattr(dependency.call, "required_permission_code", None)
                if code is not None:
                    codes.append(str(code))
                stack.extend(dependency.dependencies or [])
            seen[(method, route.path)] = codes

    assert set(seen) == set(expected), f"document route set drifted: {sorted(set(seen) ^ set(expected))}"
    for key, expected_code in expected.items():
        assert seen[key] == [expected_code], (
            f"{key[0]} {key[1]} should request exactly ['{expected_code}'], got {seen[key]}"
        )


def test_new_routes_guard_rejects_a_route_the_baseline_already_knew_about() -> None:
    from tests.fixtures.post_baseline_tightened_routes import assert_new_routes_are_genuinely_new

    with pytest.raises(RuntimeError, match="not new"):
        assert_new_routes_are_genuinely_new(
            {("GET", "/api/accounts"): "ACCOUNT_READ"},
            frozenset({("GET", "/api/documents/types")}),
            {("GET", "/api/accounts"): "ACCOUNT_READ"},
        )


def test_new_routes_guard_accepts_a_genuinely_new_route() -> None:
    from tests.fixtures.post_baseline_tightened_routes import assert_new_routes_are_genuinely_new

    assert_new_routes_are_genuinely_new(
        {("POST", "/api/brand-new"): "SOME_PERMISSION"},
        frozenset({("GET", "/api/documents/types")}),
        {("GET", "/api/accounts"): "ACCOUNT_READ"},
    )


# =============================================================================================
# Correction pass 2 (independent review, 8 September 2026): the cleanup helpers deleted only
# `document_metadata` rows, so every successful-upload test leaked its stored object. Four
# orphaned files had accumulated in the configured storage root - two per full-suite run - while
# the database showed no corresponding rows at all.
# =============================================================================================


def test_cleanup_of_a_successfully_uploaded_document_removes_its_stored_bytes() -> None:
    """The helper must leave the storage root exactly as it found it.

    Written first and confirmed failing against the pre-correction helpers, which removed the
    row and left the object behind - and, because they deleted the row first, destroyed the
    `storage_key` needed to find it afterwards.
    """
    before = _stored_file_count()
    linked_id = str(uuid4())

    upload = client.post(
        "/api/documents/upload",
        headers=_auth_headers("admin1"),
        data={
            "linked_record_type": "account",
            "linked_record_public_id": linked_id,
            "document_type": "OTHER",
        },
        files={"file": ("cleanup-check.pdf", b"%PDF-1.4 cleanup", "application/pdf")},
    )
    assert upload.status_code == 201
    assert _stored_file_count() == before + 1, "the upload should have stored exactly one object"

    _delete_documents_for_linked_record(linked_id)

    assert _stored_file_count() == before, (
        "cleanup must delete the stored object, not only the document_metadata row"
    )
    with SessionLocal() as db:
        remaining = db.execute(
            text("SELECT count(*) FROM document_metadata WHERE linked_record_public_id = :id"),
            {"id": linked_id},
        ).scalar_one()
    assert remaining == 0


def test_cleanup_removes_stored_bytes_even_when_the_row_names_an_unresolvable_provider() -> None:
    """The awkward case the recorded-provider test creates deliberately.

    That test rewrites a row's `storage_provider_code` to an unregistered value to prove the
    read path fails closed. Cleanup must still remove the object, because the bytes are
    physically held by the local provider whatever the row now claims - otherwise proving the
    fail-closed behaviour would itself leak a file every run.
    """
    before = _stored_file_count()
    linked_id = str(uuid4())

    upload = client.post(
        "/api/documents/upload",
        headers=_auth_headers("admin1"),
        data={
            "linked_record_type": "account",
            "linked_record_public_id": linked_id,
            "document_type": "OTHER",
        },
        files={"file": ("unresolvable.pdf", b"%PDF-1.4 unresolvable", "application/pdf")},
    )
    assert upload.status_code == 201
    public_id = upload.json()["document"]["public_id"]

    with SessionLocal() as db:
        db.execute(
            text(
                "UPDATE document_metadata SET storage_provider_code = 'sharepoint_future' "
                "WHERE document_public_id = :public_id"
            ),
            {"public_id": public_id},
        )
        db.commit()

    _delete_documents_for_linked_record(linked_id)

    assert _stored_file_count() == before, (
        "cleanup must fall back to the configured provider when the row's recorded provider "
        "cannot be resolved, or the fail-closed test leaks its own object"
    )
