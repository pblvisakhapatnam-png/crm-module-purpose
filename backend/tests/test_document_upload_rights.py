"""Upload rights: only people who can change a record may attach a file to it.

Owner decision, 11 September 2026. Before it, POST /api/documents/upload and
POST /api/documents/metadata were gated only by DOCUMENT_UPLOAD, which all six roles hold, and
nothing checked the caller's rights on the record the document was linked to - or even that its
type was known. A View-only user could attach a file to any Account or Commercial Offer. These
tests prove the record-scoped attach check (DOCUMENT_LINK_WRITE_PERMISSION, applied in
documents/service.py) on both routes, and the second defect closed alongside it: a caller could
label their own file QUOTATION, the type reserved for quotations the system generates (Slice 9E).

Who may attach is written out below from the owner's decision, as data - not read from
documents/contract.py or the permission matrix. An expectation derived from the code under test
agrees with any mistake in it.

Linked record ids are fresh uuid4 values rather than real records, as in the Slice 9C tests: the
check is by record type, and the service reads nothing about the record itself.
test_smoke_data_harness.py uploads to real seeded records.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.modules.documents.contract import (
    DOCUMENT_LINK_READ_PERMISSION,
    DOCUMENT_LINK_WRITE_PERMISSION,
    DOCUMENT_TYPE_CODES,
    UPLOADABLE_DOCUMENT_TYPE_CODES,
)
from app.modules.documents.service import (
    DocumentAccessDeniedError,
    store_generated_document,
    upload_document_for_caller,
)
from app.modules.documents.storage import get_storage_provider_by_code
from app.modules.identity.schemas import AuthUser

client = TestClient(app)

ALL_USERS = ("admin1", "sales1", "manager1", "finance1", "ops1", "readonly1")

# The owner's decision, 11 September 2026, as written.
OWNER_DECISION_ATTACHERS: dict[str, frozenset[str]] = {
    "business_party": frozenset({"admin1", "sales1", "manager1", "finance1"}),
    # The spelling existing document rows use for the same Account link; it follows the same rule.
    "account": frozenset({"admin1", "sales1", "manager1", "finance1"}),
    "commercial_offer": frozenset({"admin1", "sales1", "manager1", "ops1"}),
}

# The same rule - those who can change the record - applied to the other linkable types. Leads,
# Opportunities and conversations are changed by Sales; Operations also creates and amends Work
# Orders.
OTHER_TYPE_ATTACHERS: dict[str, frozenset[str]] = {
    "lead": frozenset({"admin1", "sales1", "manager1"}),
    "opportunity": frozenset({"admin1", "sales1", "manager1"}),
    "work_order": frozenset({"admin1", "sales1", "manager1", "ops1"}),
    "interaction": frozenset({"admin1", "sales1", "manager1"}),
}

# Every document type a user may still choose. Written out rather than taken from
# UPLOADABLE_DOCUMENT_TYPE_CODES, so a change that quietly narrows the list fails here. CERTIFICATE
# (ELG-1) is a machine certificate's copy; who may attach one to a certificate is pinned, with the
# certificate a copy needs, in test_elg1_machine_eligibility_api.py. VENDOR_QUOTE (Slice 4G) is a market rate's quote
# copy; who may attach one, and to which rate, is pinned in test_slice_4g_market_rates_per_line.py.
USER_DOCUMENT_TYPES = ("PAN", "GST", "KYC", "RFQ", "COMMERCIAL", "OTHER", "CERTIFICATE", "VENDOR_QUOTE")

CREATED_EVENT = {"upload": "DocumentUploaded", "metadata": "DocumentMetadataCreated"}

_tokens: dict[str, str] = {}


def _headers(username: str) -> dict[str, str]:
    """One login per user per module: the matrices below make about ninety requests."""
    if username not in _tokens:
        response = client.post("/api/auth/login", json={"username": username, "password": "password"})
        assert response.status_code == 200, response.text
        _tokens[username] = response.json()["access_token"]
    return {"Authorization": f"Bearer {_tokens[username]}"}


def _upload(
    username: str,
    linked_record_type: str,
    linked_record_public_id: str,
    *,
    document_type: str = "OTHER",
    file_name: str = "rights-check.pdf",
    content_type: str = "application/pdf",
    body: bytes = b"%PDF-1.4 rights check",
):
    return client.post(
        "/api/documents/upload",
        headers=_headers(username),
        data={
            "linked_record_type": linked_record_type,
            "linked_record_public_id": linked_record_public_id,
            "document_type": document_type,
        },
        files={"file": (file_name, body, content_type)},
    )


def _record_metadata(
    username: str,
    linked_record_type: str,
    linked_record_public_id: str,
    *,
    document_type: str = "OTHER",
):
    return client.post(
        "/api/documents/metadata",
        headers=_headers(username),
        json={
            "document_type": document_type,
            "linked_record_type": linked_record_type,
            "linked_record_public_id": linked_record_public_id,
            "file_name": "rights-check.pdf",
            "storage_mode": "external_link",
            "storage_path_or_url": "https://example.invalid/rights-check.pdf",
            "status": "Linked",
        },
    )


ROUTES = {"upload": _upload, "metadata": _record_metadata}


def _stored_file_count() -> int:
    root = Path(get_settings().document_storage_root)
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file())


def _documents_linked_to(linked_record_public_id: str) -> int:
    with SessionLocal() as db:
        return db.execute(
            text("SELECT count(*) FROM document_metadata WHERE linked_record_public_id = :id"),
            {"id": linked_record_public_id},
        ).scalar_one()


def _document_events_naming(linked_record_public_id: str) -> int:
    with SessionLocal() as db:
        return db.execute(
            text(
                "SELECT count(*) FROM business_event WHERE source_module = 'documents' "
                "AND event_payload_json LIKE :pattern"
            ),
            {"pattern": f"%{linked_record_public_id}%"},
        ).scalar_one()


def _delete_documents_linked_to(linked_record_public_id: str) -> None:
    """Stored bytes first, then rows: once a row is gone, so is the storage_key that finds them."""
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT storage_provider_code, storage_key FROM document_metadata "
                "WHERE linked_record_public_id = :id AND storage_key IS NOT NULL"
            ),
            {"id": linked_record_public_id},
        ).fetchall()
    for provider_code, storage_key in rows:
        with contextlib.suppress(Exception):
            get_storage_provider_by_code(provider_code).delete(storage_key=storage_key)
    with SessionLocal() as db:
        db.execute(
            text("DELETE FROM document_metadata WHERE linked_record_public_id = :id"),
            {"id": linked_record_public_id},
        )
        db.commit()


def _assert_nothing_was_written(linked_record_public_id: str, files_before: int) -> None:
    assert _documents_linked_to(linked_record_public_id) == 0, "a refused request inserted a document row"
    assert _document_events_naming(linked_record_public_id) == 0, "a refused request recorded a business event"
    assert _stored_file_count() == files_before, "a refused request stored bytes"


@pytest.fixture(scope="module", autouse=True)
def _no_stored_object_is_leaked_by_this_module():
    """The module uploads a few dozen files; it must end holding exactly as many as it started."""
    before = _stored_file_count()
    yield
    after = _stored_file_count()
    assert after == before, (
        f"this module leaked {after - before} stored object(s) into "
        f"{get_settings().document_storage_root} (started with {before}, ended with {after})."
    )


# =============================================================================================
# The owner's decision: Account and Commercial Offer, every role, both routes.
# =============================================================================================


@pytest.mark.parametrize("username", ALL_USERS)
@pytest.mark.parametrize("linked_record_type", sorted(OWNER_DECISION_ATTACHERS))
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_only_people_who_can_change_an_account_or_offer_may_attach_to_it(
    route: str, linked_record_type: str, username: str
) -> None:
    linked_id = str(uuid4())
    files_before = _stored_file_count()
    try:
        response = ROUTES[route](username, linked_record_type, linked_id)
        if username in OWNER_DECISION_ATTACHERS[linked_record_type]:
            assert response.status_code == 201, response.text
            body = response.json()
            assert body["document"]["linked_record_type"] == linked_record_type
            assert body["event"]["event_name"] == CREATED_EVENT[route]
            assert _documents_linked_to(linked_id) == 1
        else:
            assert response.status_code == 403, response.text
            _assert_nothing_was_written(linked_id, files_before)
    finally:
        _delete_documents_linked_to(linked_id)


@pytest.mark.parametrize("username", ALL_USERS)
@pytest.mark.parametrize("linked_record_type", sorted(OTHER_TYPE_ATTACHERS))
def test_the_same_rule_governs_the_other_linkable_record_types(linked_record_type: str, username: str) -> None:
    """Through the metadata route only. Both routes run the same check, and the matrix above
    already proves the upload route applies it."""
    linked_id = str(uuid4())
    try:
        response = _record_metadata(username, linked_record_type, linked_id)
        if username in OTHER_TYPE_ATTACHERS[linked_record_type]:
            assert response.status_code == 201, response.text
        else:
            assert response.status_code == 403, response.text
            assert _documents_linked_to(linked_id) == 0
            assert _document_events_naming(linked_id) == 0
    finally:
        _delete_documents_linked_to(linked_id)


@pytest.mark.parametrize("linked_record_type", ["totally_unmapped_type", "customer", "Business_Party"])
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_a_record_type_no_rule_names_is_refused_even_to_admin(route: str, linked_record_type: str) -> None:
    """Fail-closed. linked_record_type is free text, so an unknown value - including a
    differently-cased spelling of a known one - denies rather than falls through. admin1 holds
    every permission the attach rules name, so a refusal here can only be the missing rule."""
    linked_id = str(uuid4())
    files_before = _stored_file_count()
    try:
        response = ROUTES[route]("admin1", linked_record_type, linked_id)
        assert response.status_code == 403, response.text
        _assert_nothing_was_written(linked_id, files_before)
    finally:
        _delete_documents_linked_to(linked_id)


@pytest.mark.parametrize(
    "linked_record_type", ["", "   ", "a" * 101], ids=["empty", "whitespace", "over-length"]
)
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_a_malformed_record_type_is_refused_as_invalid_before_rights_are_checked(
    route: str, linked_record_type: str
) -> None:
    """422, not 403, from readonly1 - who may attach to nothing, so a 403 here would mean the
    rights check had run before validation."""
    linked_id = str(uuid4())
    files_before = _stored_file_count()
    try:
        response = ROUTES[route]("readonly1", linked_record_type, linked_id)
        assert response.status_code == 422, response.text
        _assert_nothing_was_written(linked_id, files_before)
    finally:
        _delete_documents_linked_to(linked_id)


def test_a_refused_upload_never_reads_the_file_stream() -> None:
    """A refusal stores no bytes because it happens before a single byte is read - not because
    something written is cleaned up afterwards."""

    class _StreamThatMustNotBeRead:
        def read(self, size: int = -1) -> bytes:
            raise AssertionError("the upload stream was read before the rights check refused it")

    view_only = AuthUser(
        public_id=str(uuid4()),
        username="view-only-probe",
        display_name="View Only Probe",
        roles=[],
        role_codes=["MANAGEMENT_READ_ONLY"],
    )
    with SessionLocal() as db:
        with pytest.raises(DocumentAccessDeniedError):
            upload_document_for_caller(
                db,
                current_user=view_only,
                linked_record_type="commercial_offer",
                linked_record_public_id=uuid4(),
                document_type="OTHER",
                file_name="never-read.pdf",
                declared_content_type="application/pdf",
                stream=_StreamThatMustNotBeRead(),  # type: ignore[arg-type]
                remarks=None,
            )


def test_every_readable_record_type_has_an_attach_rule_and_nothing_else_does() -> None:
    """A type attachable but not readable would accept files nobody could then see. A type
    readable but not attachable only denies, but it means the two maps have drifted apart."""
    assert set(DOCUMENT_LINK_WRITE_PERMISSION) == set(DOCUMENT_LINK_READ_PERMISSION)


def test_the_documents_module_exposes_exactly_its_expected_routes_and_permissions() -> None:
    """This package adds no route and removes none; the two write routes keep the permissions
    Slice 9C gave them. The shared authorization guard
    (test_authorization_route_migration_guard.py) pins every protected route's exact permission and
    flags a new ungated route, but it bounds the total by a `>= 70` floor rather than an exact
    count and does not detect a removed *ungated* route. This test closes that gap for this
    module's own surface: the exact set of `/api/documents` routes and the permission each requires,
    read from the route's own `require_permission` dependency metadata, so adding, removing or
    re-gating any documents route fails here.
    """
    from fastapi.routing import APIRoute

    from app.main import app

    expected = {
        ("GET", "/api/documents/types"): "DOCUMENT_READ",
        ("GET", "/api/documents/recent"): "DOCUMENT_READ",
        ("GET", "/api/documents/by-record/{record_type}/{record_public_id}"): "DOCUMENT_READ",
        ("POST", "/api/documents/metadata"): "DOCUMENT_UPLOAD",
        ("POST", "/api/documents/upload"): "DOCUMENT_UPLOAD",
        ("GET", "/api/documents/{public_id}/content"): "DOCUMENT_CONTENT_READ",
    }

    def required_permission_codes(route: APIRoute) -> list[str]:
        codes = []
        for dependency in route.dependant.dependencies:
            code = getattr(dependency.call, "required_permission_code", None)
            if code is not None:
                codes.append(code)
        return codes

    live: dict[tuple[str, str], list[str]] = {}
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api/documents"):
            for method in route.methods:
                live[(method, route.path)] = required_permission_codes(route)

    assert set(live) == set(expected), (
        f"the documents route set changed: only here {set(live) - set(expected)}, "
        f"missing {set(expected) - set(live)}"
    )
    for key, permission in expected.items():
        assert live[key] == [permission], f"{key[0]} {key[1]} requires {live[key]!r}, expected [{permission!r}]"


# =============================================================================================
# QUOTATION is set only by the application.
# =============================================================================================


@pytest.mark.parametrize("document_type", ["QUOTATION", "quotation", " Quotation "])
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_quotation_is_refused_on_both_user_paths(route: str, document_type: str) -> None:
    """The upload route used to accept QUOTATION, because it checked the full DOCUMENT_TYPE_CODES
    list; the metadata route, which takes free text, accepted it in any spelling. sales1 may attach
    to a Commercial Offer, so the refusal here can only be the type."""
    linked_id = str(uuid4())
    files_before = _stored_file_count()
    try:
        response = ROUTES[route]("sales1", "commercial_offer", linked_id, document_type=document_type)
        assert response.status_code == 422, response.text
        assert "QUOTATION" in response.json()["detail"]
        _assert_nothing_was_written(linked_id, files_before)
    finally:
        _delete_documents_linked_to(linked_id)


def test_a_user_cannot_upload_an_html_file_dressed_as_a_generated_quotation() -> None:
    """What the reservation prevents: a hand-made HTML file, named like the system's own quotation
    files and typed QUOTATION, attached to an offer by someone allowed to attach to it. manager1
    may approve quotations for issue; that makes no difference.

    Refused twice over - by the reserved type and by the .html extension, which Slice 9C already
    refused - so this keeps holding if either refusal is ever loosened. It does not by itself tell
    the old code from the new; test_quotation_is_refused_on_both_user_paths does."""
    linked_id = str(uuid4())
    files_before = _stored_file_count()
    try:
        response = _upload(
            "manager1",
            "commercial_offer",
            linked_id,
            document_type="QUOTATION",
            file_name="Quotation-CO-000001-V1.html",
            content_type="text/html",
            body=b"<html><body>Approved for issue</body></html>",
        )
        assert response.status_code == 422, response.text
        _assert_nothing_was_written(linked_id, files_before)
    finally:
        _delete_documents_linked_to(linked_id)


# VENDOR_QUOTE goes on a market rate only (Slice 4G): refused on an offer, below; accepted on a rate in
# test_slice_4g_market_rates_per_line.py.
@pytest.mark.parametrize("document_type", [code for code in USER_DOCUMENT_TYPES if code != "VENDOR_QUOTE"])
def test_every_other_document_type_can_still_be_uploaded(document_type: str) -> None:
    linked_id = str(uuid4())
    try:
        response = _upload("sales1", "commercial_offer", linked_id, document_type=document_type)
        assert response.status_code == 201, response.text
        assert response.json()["document"]["document_type"] == document_type
    finally:
        _delete_documents_linked_to(linked_id)


def test_a_vendor_quote_is_refused_on_an_offer_itself() -> None:
    linked_id = str(uuid4())
    try:
        response = _upload("sales1", "commercial_offer", linked_id, document_type="VENDOR_QUOTE")
        assert response.status_code == 422, response.text
        assert _documents_linked_to(linked_id) == 0
    finally:
        _delete_documents_linked_to(linked_id)


def test_the_application_itself_can_still_store_a_quotation() -> None:
    """store_generated_document() is the one writer QUOTATION is reserved for, and it is untouched
    by the user-path refusal. Slice 9E's own tests prove it end to end; this pins it here, beside
    the refusal, so the two cannot be tightened into each other unnoticed."""
    linked_id = str(uuid4())
    try:
        with SessionLocal() as db:
            row = store_generated_document(
                db,
                linked_record_type="commercial_offer",
                linked_record_public_id=linked_id,
                document_type="QUOTATION",
                file_name="Quotation-rights-check-V1.html",
                content_type="text/html",
                content=b"<html><body>generated</body></html>",
                current_user_public_id=None,
            )
            db.commit()
        assert row["document_type"] == "QUOTATION"
        assert _documents_linked_to(linked_id) == 1
    finally:
        _delete_documents_linked_to(linked_id)


def test_quotation_is_the_only_type_a_user_may_not_choose() -> None:
    assert set(DOCUMENT_TYPE_CODES) - set(UPLOADABLE_DOCUMENT_TYPE_CODES) == {"QUOTATION"}
    assert set(UPLOADABLE_DOCUMENT_TYPE_CODES) == set(USER_DOCUMENT_TYPES)
