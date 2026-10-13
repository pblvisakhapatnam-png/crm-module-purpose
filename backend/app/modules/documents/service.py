"""Document Storage Foundation service layer (Slice 9C).

Business rules enforced here, not in routes.py - the same split Slice 9D established and for
the same two reasons: the route-permission guard
(tests/test_authorization_route_migration_guard.py) permits at most one
require_permission(...) dependency per route, and forbids reading `.role_codes` inside a route
module outside two narrowly pinned pre-existing exceptions in other modules. A record-scoped
authorization decision - "may this caller see documents linked to THIS record", or "may they
attach one to it" - therefore has to live here, resolved through has_permission(...) against the
caller's full role_codes, exactly as interactions/service.py does for its own content-redaction
check.

- linked_record_type -> read permission is a closed map (DOCUMENT_LINK_READ_PERMISSION in
  contract.py). An unmapped type DENIES; it never falls through to allowed. This is the
  guard against the exact vocabulary mismatch this module has with Slice 9D (this table's
  existing rows say "account"; Slice 9D's canonical value is "business_party") ever becoming
  a silent bypass.
- Downloading the bytes of a document linked to an interaction requires a SECOND permission
  (INTERACTION_CONTENT_READ) beyond the base link-read permission, so a document attached to a
  customer conversation cannot be used as a pointer around Slice 9D's content redaction.
- Attaching is record-scoped the same way (owner decision, 11 September 2026): only a caller who
  may change a record may upload a file to it or record document metadata against it, through a
  second closed, fail-closed map (DOCUMENT_LINK_WRITE_PERMISSION). The HTTP routes call the
  *_for_caller functions, which check it. upload_document() and create_document_metadata()
  perform no authorization at all and serve trusted in-process callers only.
- document_type QUOTATION is set only by store_generated_document(). Both user paths refuse it.
- storage_mode = "local_upload" is reachable ONLY through upload_document(), which is the only
  function that actually stores bytes and populates the columns the database CHECK constraint
  requires. create_document_metadata() rejects it outright.
- Upload size is enforced by counting bytes as they are actually read from the incoming stream,
  never by trusting the caller-declared Content-Length or a form field. See
  _SizeLimitingReader. routes.py caps each whole request the same way, before its body is parsed.
- An uploaded file's opening bytes must match its extension's format (_check_upload_content):
  the extension and the declared content type are both only the caller's claim. These are
  format checks, not a malware scan.
"""

from __future__ import annotations

import io
import os
import zipfile
from dataclasses import dataclass
from typing import Any, BinaryIO, Callable, ContextManager, Iterator
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.authorization.service import has_permission
from app.modules.documents.contract import (
    ALLOWED_STATUSES,
    ALLOWED_UPLOAD_EXTENSIONS,
    DOCUMENT_LINK_EXTRA_CONTENT_PERMISSION,
    DOCUMENT_LINK_READ_PERMISSION,
    DOCUMENT_LINK_TYPES_WITH_ATTACH_CHECK,
    DOCUMENT_TYPE_ONLY_FOR_LINK_TYPE,
    DOCUMENT_LINK_WRITE_PERMISSION,
    DOCUMENT_MODULE_NAME,
    DOCUMENT_RECORD_TYPE,
    GENERATED_CONTENT_TYPES,
    MAX_DOCUMENT_TYPE_LENGTH,
    MAX_FILE_NAME_LENGTH,
    MAX_LINKED_RECORD_TYPE_LENGTH,
    MAX_REMARKS_LENGTH,
    MAX_UPLOAD_BYTES,
    METADATA_ROUTE_ALLOWED_STORAGE_MODES,
    STORAGE_MODE_LOCAL_UPLOAD,
    SYSTEM_GENERATED_DOCUMENT_TYPE_CODES,
    UPLOADABLE_DOCUMENT_TYPE_CODES,
)
from app.modules.documents.repository import (
    get_document_by_public_id,
    insert_document_metadata,
    list_documents_for_record,
    list_documents_linked_to_records,
    list_linked_record_ids_with_documents,
    list_recent_documents,
)
from app.modules.documents.schemas import (
    DocumentMetadataCreate,
    DocumentMetadataCreatedResponse,
    DocumentMetadataResponse,
    DocumentUploadedResponse,
)
from app.modules.documents.storage import get_storage_provider, get_storage_provider_by_code
from app.modules.documents.storage.base import (
    StorageObjectNotFoundError,
    UnknownStorageProviderError,
)
from app.modules.events.service import record_business_event
from app.modules.identity.schemas import AuthUser

DOCUMENT_EVENT_METADATA_CREATED = "DocumentMetadataCreated"
DOCUMENT_EVENT_UPLOADED = "DocumentUploaded"
# Slice 9E: recorded when store_generated_document() stores a document THIS APPLICATION
# generated (currently: a Commercial Offer quotation). Deliberately a distinct event name from
# DOCUMENT_EVENT_UPLOADED - reusing the upload event would record that a user uploaded a file
# they never uploaded, the same class of small lie Slice 9C existed to remove.
DOCUMENT_EVENT_GENERATED = "DocumentGenerated"
DOCUMENT_EVENT_SCHEMA_VERSION = "1.0"

# Rows fetched from the database per "recent documents" request, before the record-scoped
# permission filter is applied and the result is trimmed to the caller's requested limit. A
# caller who may read only some linked record types would otherwise see fewer than `limit`
# results purely because unreadable rows were filtered out AFTER an already-small fetch; this
# mirrors the bounded-oversampling shape Slice 9D uses for its own inherited-history merge
# (_INHERITED_MERGE_FETCH_CAP), generous for a pilot's current document volume.
_RECENT_DOCUMENTS_FETCH_CAP = 500


class DocumentNotFoundError(Exception):
    pass


class DocumentValidationError(Exception):
    pass


class DocumentAccessDeniedError(Exception):
    """Raised when the caller may not read documents linked to a given record, or may not attach
    one to it.

    Covers both an unmapped linked_record_type (fail-closed - see the module docstring) and a
    mapped type the caller's role_codes do not currently grant.
    """


class DocumentContentUnavailableError(Exception):
    """Raised when a document has no application-managed bytes to download.

    Covers a document recorded as external_link/future_sharepoint (its content, if any, lives
    outside this application) and the narrower internal-consistency case of a local_upload row
    whose stored object cannot be found - which the database CHECK constraint makes impossible
    to create in the first place, but a provider-level failure (e.g. the volume was reset) is a
    distinct, later-arising fact this exception also carries.
    """


class DocumentUploadTooLargeError(Exception):
    pass


class DocumentUploadTypeError(Exception):
    pass


def _user_public_id(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


def _may_read_link(db: Session, current_user: AuthUser, linked_record_type: str) -> bool:
    """Fail-closed: an unmapped linked_record_type is never readable."""
    permission_code = DOCUMENT_LINK_READ_PERMISSION.get(linked_record_type)
    if permission_code is None:
        return False
    return has_permission(db, current_user.role_codes, permission_code)


def _may_read_content(db: Session, current_user: AuthUser, linked_record_type: str) -> bool:
    """The base link-read permission, AND any extra content-specific permission the link type
    requires (currently: interaction -> INTERACTION_CONTENT_READ, protecting a document
    attached to a customer conversation from being used as a pointer around Slice 9D's
    redaction).
    """
    if not _may_read_link(db, current_user, linked_record_type):
        return False
    extra_permission_code = DOCUMENT_LINK_EXTRA_CONTENT_PERMISSION.get(linked_record_type)
    if extra_permission_code is None:
        return True
    return has_permission(db, current_user.role_codes, extra_permission_code)


def _may_write_link(db: Session, current_user: AuthUser, linked_record_type: str) -> bool:
    """Fail-closed like _may_read_link: an unmapped linked_record_type is never attachable."""
    permission_code = DOCUMENT_LINK_WRITE_PERMISSION.get(linked_record_type)
    if permission_code is None:
        return False
    return has_permission(db, current_user.role_codes, permission_code)


def _ensure_may_write_link(db: Session, current_user: AuthUser, linked_record_type: str) -> None:
    if not _may_write_link(db, current_user, linked_record_type):
        raise DocumentAccessDeniedError("You do not have permission to attach documents to this record.")


@dataclass(frozen=True)
class AttachRequest:
    """What an owning module is told about a file about to be attached to one of its records."""

    linked_record_public_id: str
    document_type: str
    storage_mode: str


# linked_record_type -> the owning module's check on one attachment: the reason it refuses it, or None.
_ATTACH_CHECKS: dict[str, Callable[[Session, AttachRequest], str | None]] = {}


def register_attach_check(linked_record_type: str, check: Callable[[Session, AttachRequest], str | None]) -> None:
    """Called by a module that owns records of `linked_record_type`, when it is imported, so the documents
    module need not import it. ELG-1's certificates take only an uploaded CERTIFICATE copy, and none once
    withdrawn."""
    _ATTACH_CHECKS[linked_record_type] = check


def _ensure_record_takes_documents(db: Session, linked_record_type: str, request: AttachRequest) -> None:
    """The owning module's say on attaching this file to this one record. Fail-closed: a type that needs a
    check and has none registered refuses."""
    # Matched after trimming, so a padded type - which no read map grants - still meets its owner's check rather than
    # skipping it (Slice 4G, review 4G-R4-002).
    owner_type = linked_record_type.strip()
    if owner_type not in DOCUMENT_LINK_TYPES_WITH_ATTACH_CHECK:
        return
    check = _ATTACH_CHECKS.get(owner_type)
    if check is None:
        raise DocumentAccessDeniedError(f"Files cannot be attached to a {linked_record_type!r} record here.")
    refusal = check(db, request)
    if refusal:
        raise DocumentValidationError(refusal)


def linked_record_ids_with_documents(
    db: Session,
    *,
    linked_record_type: str,
    linked_record_public_ids: list[str],
    document_type: str | None = None,
    storage_mode: str | None = None,
) -> set[str]:
    """Which of these records have a document attached - of this type and storage mode, where given, and not
    rejected or archived. Trusted in-process callers only: it reads no rights, and says only whether such a file
    exists, never what it is (ELG-1: a certificate counts only with its uploaded copy, and everyone who sees it
    may know whether the copy is there)."""
    return list_linked_record_ids_with_documents(
        db,
        linked_record_type=linked_record_type,
        linked_record_public_ids=linked_record_public_ids,
        document_type=document_type,
        storage_mode=storage_mode,
    )


def documents_linked_to_records(
    db: Session,
    *,
    linked_record_type: str,
    linked_record_public_ids: list[str],
    document_type: str,
) -> list[dict[str, Any]]:
    """The file name and id of each document of this type linked to these records, not rejected or archived. Trusted
    in-process callers only: it reads no rights. The caller shows them only to whoever may read the records; the
    download route checks the link's read right again (Slice 4G: a market rate's quote copies, which need
    COMMERCIAL_OFFER_READ, as reading the rate does)."""
    return list_documents_linked_to_records(
        db,
        linked_record_type=linked_record_type,
        linked_record_public_ids=linked_record_public_ids,
        document_type=document_type,
    )


def _reject_document_type_on_another_link(document_type: str, linked_record_type: str) -> None:
    """Refuse a document type kept for one linked record type when it is filed against another (Slice 4G): a vendor
    quote goes on a market rate only. Compared after trimming and upper-casing, as the metadata route takes free text."""
    only_for = DOCUMENT_TYPE_ONLY_FOR_LINK_TYPE.get(document_type.strip().upper())
    if only_for is not None and linked_record_type != only_for:
        raise DocumentValidationError(
            f"A {document_type.strip().upper()} document is attached to a {only_for} record only."
        )


def _reject_system_generated_document_type(document_type: str) -> None:
    """Refuse a document type only the application may set (see
    SYSTEM_GENERATED_DOCUMENT_TYPE_CODES in contract.py).

    Compared after trimming and upper-casing: the metadata route accepts free-text types, so
    "quotation" would otherwise be stored as typed and read on screen as the reserved type.
    """
    if document_type.strip().upper() in SYSTEM_GENERATED_DOCUMENT_TYPE_CODES:
        raise DocumentValidationError(
            "The document type QUOTATION is used only for quotations the system generates. "
            "Choose another document type."
        )


def _row_to_response(row: dict[str, Any]) -> DocumentMetadataResponse:
    uploaded_at = row.get("uploaded_at")
    retention_due_at = row.get("retention_due_at")
    return DocumentMetadataResponse(
        public_id=row["document_public_id"],
        document_type=row["document_type"],
        linked_record_type=row["linked_record_type"],
        linked_record_public_id=row["linked_record_public_id"],
        file_name=row["file_name"],
        original_file_name=row.get("original_file_name"),
        storage_mode=row["storage_mode"],
        storage_path_or_url=row.get("storage_path_or_url"),
        version_no=row["version_no"],
        status=row["status"],
        content_type=row.get("content_type"),
        byte_size=row.get("byte_size"),
        checksum_sha256=row.get("checksum_sha256"),
        retention_due_at=retention_due_at.isoformat() if retention_due_at else None,
        uploaded_by=row.get("uploaded_by"),
        uploaded_at=uploaded_at.isoformat() if uploaded_at else None,
        remarks=row.get("remarks"),
    )


def list_recent_documents_for_caller(
    db: Session, *, limit: int, current_user: AuthUser
) -> list[DocumentMetadataResponse]:
    """The most recent documents the caller may actually read, fail-closed per row.

    Closes the second defect this slice exists for: at baseline this route returned every
    document in the system to any authenticated caller, so a MANAGEMENT_READ_ONLY user could
    enumerate every document's file name regardless of what it was attached to.
    """
    fetched = list_recent_documents(db, limit=_RECENT_DOCUMENTS_FETCH_CAP)
    visible = [row for row in fetched if _may_read_link(db, current_user, row["linked_record_type"])]
    return [_row_to_response(row) for row in visible[:limit]]


def list_documents_for_record_for_caller(
    db: Session,
    *,
    linked_record_type: str,
    linked_record_public_id: str,
    current_user: AuthUser,
) -> list[DocumentMetadataResponse]:
    if not _may_read_link(db, current_user, linked_record_type):
        raise DocumentAccessDeniedError(
            f"You do not have permission to view documents linked to a {linked_record_type!r} record."
        )
    rows = list_documents_for_record(
        db, linked_record_type=linked_record_type, linked_record_public_id=linked_record_public_id
    )
    return [_row_to_response(row) for row in rows]


def _validate_metadata_payload(payload: DocumentMetadataCreate) -> None:
    """The checks a metadata record must pass beyond the length bounds DocumentMetadataCreate
    itself enforces.

    Runs before the rights check in create_document_metadata_for_caller(), so a malformed request
    is a 422 whoever sends it - the same order the upload path uses.
    """
    if payload.storage_mode not in METADATA_ROUTE_ALLOWED_STORAGE_MODES:
        if payload.storage_mode == STORAGE_MODE_LOCAL_UPLOAD:
            raise DocumentValidationError(
                "storage_mode 'local_upload' may only be set by actually uploading a file "
                "through POST /api/documents/upload."
            )
        raise DocumentValidationError(f"Invalid storage mode: {payload.storage_mode}")

    if payload.status not in ALLOWED_STATUSES:
        raise DocumentValidationError(f"Invalid document status: {payload.status}")

    # DocumentMetadataCreate enforces min_length=1, which a whitespace-only value passes. The
    # upload path has always refused one; this keeps the two routes consistent.
    if not payload.linked_record_type.strip():
        raise DocumentValidationError("linked_record_type is required.")

    _reject_system_generated_document_type(payload.document_type)
    _reject_document_type_on_another_link(payload.document_type, payload.linked_record_type)


def create_document_metadata(
    db: Session,
    *,
    payload: DocumentMetadataCreate,
    current_user_public_id: str | None,
) -> DocumentMetadataCreatedResponse:
    """Record a pointer to bytes stored elsewhere (external_link/future_sharepoint).

    Performs NO authorization. POST /api/documents/metadata calls
    create_document_metadata_for_caller(), which checks the caller may attach to the linked
    record; this function is for trusted in-process callers such as the smoke-data harness and
    tests.

    Never local_upload: this function stores no bytes and populates none of the columns the
    database CHECK constraint (ck_document_metadata_local_upload_has_bytes) requires for that
    mode. Rejecting it here at the API layer is the first line of defense; the CHECK constraint
    is the one that holds even if this function is bypassed entirely (a direct INSERT, or a
    future code path that forgets this check).
    """
    _validate_metadata_payload(payload)
    _ensure_record_takes_documents(
        db,
        payload.linked_record_type,
        AttachRequest(str(payload.linked_record_public_id), payload.document_type, payload.storage_mode),
    )

    document_public_id = str(uuid4())
    values = {
        "document_type": payload.document_type,
        "linked_record_type": payload.linked_record_type,
        "linked_record_public_id": str(payload.linked_record_public_id),
        "file_name": payload.file_name,
        "original_file_name": payload.original_file_name or payload.file_name,
        "storage_mode": payload.storage_mode,
        "storage_path_or_url": payload.storage_path_or_url,
        "version_no": payload.version_no,
        "status": payload.status,
        "storage_provider_code": None,
        "storage_key": None,
        "content_type": None,
        "byte_size": None,
        "checksum_sha256": None,
        "retention_due_at": None,
        "uploaded_by": current_user_public_id,
        "remarks": payload.remarks,
    }

    try:
        row = insert_document_metadata(db, public_id=document_public_id, values=values)

        # Structured payload via record_business_event, not hand-built JSON. The pre-9C
        # version of this route built the payload with raw f-string interpolation; a
        # document_type containing a double quote forged or corrupted the stored JSON.
        # record_business_event's own JSON encoding closes that.
        event = record_business_event(
            db,
            event_name=DOCUMENT_EVENT_METADATA_CREATED,
            source_module=DOCUMENT_MODULE_NAME,
            record_type=DOCUMENT_RECORD_TYPE,
            record_public_id=document_public_id,
            user_public_id=current_user_public_id,
            status_after=payload.status,
            reason="Document metadata linked.",
            remarks=payload.remarks,
            event_payload={
                "schema_version": DOCUMENT_EVENT_SCHEMA_VERSION,
                "document_type": payload.document_type,
                "linked_record_type": payload.linked_record_type,
                "linked_record_public_id": str(payload.linked_record_public_id),
                "storage_mode": payload.storage_mode,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return DocumentMetadataCreatedResponse(document=_row_to_response(row), event=event.model_dump())


def create_document_metadata_for_caller(
    db: Session, *, payload: DocumentMetadataCreate, current_user: AuthUser
) -> DocumentMetadataCreatedResponse:
    """POST /api/documents/metadata: validate, check the caller may attach to the linked record,
    then record it.

    Nothing is written before the rights check, so a refused request inserts no row and records
    no event. Validation runs again inside create_document_metadata(); that costs nothing and
    keeps the trusted function safe to call on its own.
    """
    _validate_metadata_payload(payload)
    _ensure_may_write_link(db, current_user, payload.linked_record_type)
    return create_document_metadata(db, payload=payload, current_user_public_id=_user_public_id(current_user))


class _SizeLimitingReader:
    """Wraps a binary stream, raising DocumentUploadTooLargeError once more bytes have been
    read than `max_bytes` allows.

    Reads happen in whatever chunk size the caller of .read() requests, so the whole file is
    never buffered in memory here - only a running total is tracked. Deliberately never
    consults Content-Length or any other caller-declared size: a header can understate the real
    size of the body that follows, so only what actually crosses this wrapper's .read() counts.
    """

    def __init__(self, source: BinaryIO, *, max_bytes: int) -> None:
        self._source = source
        self._max_bytes = max_bytes
        self._read_so_far = 0

    def read(self, size: int = -1) -> bytes:
        chunk = self._source.read(size)
        self._read_so_far += len(chunk)
        if self._read_so_far > self._max_bytes:
            raise DocumentUploadTooLargeError(
                f"File exceeds the maximum allowed size of {self._max_bytes} bytes."
            )
        return chunk


def _validate_upload_fields(
    *,
    linked_record_type: str,
    document_type: str,
    file_name: str,
    remarks: str | None,
) -> None:
    """Apply the column-width and non-blank bounds to the multipart form fields.

    The JSON metadata route gets these from `DocumentMetadataCreate`'s Pydantic `max_length`
    constraints; multipart form parts have no such model, so the same bounds are applied here
    instead of being silently skipped. Runs before any bytes are stored, so a rejection leaves
    no orphaned file.
    """
    if not linked_record_type or not linked_record_type.strip():
        raise DocumentValidationError("linked_record_type is required.")
    if len(linked_record_type) > MAX_LINKED_RECORD_TYPE_LENGTH:
        raise DocumentValidationError(
            f"linked_record_type must be at most {MAX_LINKED_RECORD_TYPE_LENGTH} characters."
        )

    if len(document_type) > MAX_DOCUMENT_TYPE_LENGTH:
        raise DocumentValidationError(
            f"document_type must be at most {MAX_DOCUMENT_TYPE_LENGTH} characters."
        )
    _reject_system_generated_document_type(document_type)
    _reject_document_type_on_another_link(document_type, linked_record_type)
    if document_type not in UPLOADABLE_DOCUMENT_TYPE_CODES:
        raise DocumentValidationError(f"Invalid document type: {document_type}")

    if not file_name or not file_name.strip():
        raise DocumentValidationError("The uploaded file must have a file name.")
    if len(file_name) > MAX_FILE_NAME_LENGTH:
        raise DocumentValidationError(
            f"file_name must be at most {MAX_FILE_NAME_LENGTH} characters."
        )

    if remarks is not None and len(remarks) > MAX_REMARKS_LENGTH:
        raise DocumentValidationError(f"remarks must be at most {MAX_REMARKS_LENGTH} characters.")


def _validate_upload_filename(filename: str) -> str:
    """Return the declared content type an accepted extension requires, or raise.

    Validated on both the extension and the caller-declared content type: a file named
    "invoice.exe" is rejected regardless of what content type accompanies it, and a file
    declaring an unexpected content type for its extension is rejected even if the extension
    alone would have been accepted - neither half is trusted alone.
    """
    _, extension = os.path.splitext(filename.lower())
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise DocumentUploadTypeError(
            f"File type {extension or '(none)'!r} is not accepted. Allowed types: "
            f"{', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}."
        )
    return ALLOWED_UPLOAD_EXTENSIONS[extension]


def _validate_upload_request(
    *,
    linked_record_type: str,
    document_type: str,
    file_name: str,
    declared_content_type: str | None,
    remarks: str | None,
) -> str:
    """Every check an upload must pass before a byte is stored; returns the content type the
    file's extension requires.

    Shared by upload_document() and upload_document_for_caller(), so the second can refuse a
    malformed request with 422 before it asks whether the caller may attach to the record.
    """
    # The multipart form parts carry no Pydantic model, so the column-width bounds
    # DocumentMetadataCreate applies to the JSON route have to be applied explicitly here
    # (independent review, correction pass 1, finding 4).
    _validate_upload_fields(
        linked_record_type=linked_record_type,
        document_type=document_type,
        file_name=file_name,
        remarks=remarks,
    )

    expected_content_type = _validate_upload_filename(file_name)
    # A missing declared content type is a rejection, not a skipped check. The earlier
    # `if declared_content_type and ...` short-circuited on an absent type, so a multipart part
    # with no MIME type bypassed content-type validation entirely and was accepted (independent
    # review, correction pass 1, finding 1). The specification requires BOTH halves.
    if not declared_content_type or not declared_content_type.strip():
        raise DocumentUploadTypeError(
            "The uploaded file must declare a content type. Expected "
            f"{expected_content_type!r} for this file's extension."
        )
    if declared_content_type != expected_content_type:
        raise DocumentUploadTypeError(
            f"Declared content type {declared_content_type!r} does not match the expected "
            f"content type {expected_content_type!r} for this file's extension."
        )
    return expected_content_type


# --- file content checks ----------------------------------------------------------------------
# The extension and the declared content type are both chosen by the caller, and the frontend
# declares the type its extension requires, so together they say only what the caller claims the
# file is (independent review of the upload package, round 1). Before a byte is stored, the file's
# own opening bytes must match its extension's format too.
_CONTENT_HEAD_BYTES = 8192
_PDF_SIGNATURE = b"%PDF-"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"
# Word and Excel 97-2003 files (.doc, .xls) are compound files: a small file system inside one
# file. So are PowerPoint decks, Outlook messages and Windows installers. What makes one a Word
# document or an Excel workbook is the stream its directory lists (independent review, round 2).
_OLE2_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_COMPOUND_FILE_REQUIRED_STREAMS: dict[str, frozenset[str]] = {
    ".doc": frozenset({"WordDocument"}),
    # "Workbook" since Excel 97; "Book" in Excel 5 and 95 files, which are also saved as .xls.
    ".xls": frozenset({"Workbook", "Book"}),
}
_CFB_HEADER_BYTES = 512
_CFB_FREE_SECTOR = 0xFFFFFFFF
_CFB_END_OF_CHAIN = 0xFFFFFFFE
# A directory entry's "no sibling" or "no child" value.
_CFB_NO_ENTRY = 0xFFFFFFFF
_CFB_DIRECTORY_ENTRY_BYTES = 128
_CFB_STORAGE_OBJECT = 1
_CFB_STREAM_OBJECT = 2
_CFB_ROOT_OBJECT = 5
_ZIP_SIGNATURE = b"PK\x03\x04"
# A .docx or .xlsx is a ZIP archive; these parts are what make it one and not the other.
_OOXML_REQUIRED_PARTS: dict[str, frozenset[str]] = {
    ".docx": frozenset({"[Content_Types].xml", "word/document.xml"}),
    ".xlsx": frozenset({"[Content_Types].xml", "xl/workbook.xml"}),
}
# A macro-enabled document or workbook (.docm, .xlsm) renamed .docx or .xlsx carries this part.
_OOXML_MACRO_PARTS: dict[str, str] = {".docx": "word/vbaProject.bin", ".xlsx": "xl/vbaProject.bin"}
# A ZIP archive's end record, a central-directory entry, and the ZIP64 locator that would override
# the sizes the end record states.
_ZIP_END_RECORD_SIGNATURE = b"PK\x05\x06"
_ZIP_CENTRAL_ENTRY_SIGNATURE = b"PK\x01\x02"
_ZIP64_LOCATOR_SIGNATURE = b"PK\x06\x07"
_ZIP_END_RECORD_BYTES = 22
_ZIP_MAX_COMMENT_BYTES = 65535
# Far more parts than a Word or Excel file within the upload limit holds, and a directory far
# larger than theirs, yet small enough that the objects zipfile builds per entry stay well below
# the size of the upload itself (independent review, round 5).
_ZIP_MAX_ENTRIES = 10_000
_ZIP_MAX_DIRECTORY_BYTES = 1024 * 1024
_UTF16_BYTE_ORDER_MARKS = (b"\xff\xfe", b"\xfe\xff")
_CONTENT_DESCRIPTIONS: dict[str, str] = {
    ".pdf": "a PDF",
    ".doc": "a Word document",
    ".docx": "a Word document",
    ".xls": "an Excel workbook",
    ".xlsx": "an Excel workbook",
    ".png": "a PNG image",
    ".jpg": "a JPG image",
    ".jpeg": "a JPG image",
    ".txt": "text",
    ".csv": "text",
}


def _zip_directory_is_bounded(stream: BinaryIO) -> bool:
    """True when a ZIP archive's end record describes a directory small enough to read: on one
    disk, with no ZIP64 extension, of at most _ZIP_MAX_ENTRIES entries and _ZIP_MAX_DIRECTORY_BYTES
    bytes, and lying inside the file.

    zipfile builds an object for every directory entry as it opens an archive, so the directory's
    size is checked first, from the one record that states it (independent review, round 5). The
    record is found the way zipfile finds it - the last occurrence of its signature in the file's
    final 22 + 65,535 bytes - so both judge the same record. Leaves the stream where it found it.
    """
    start = stream.tell()
    try:
        stream.seek(0, io.SEEK_END)
        file_size = stream.tell() - start
        tail_size = min(file_size, _ZIP_END_RECORD_BYTES + _ZIP_MAX_COMMENT_BYTES)
        stream.seek(start + file_size - tail_size)
        tail = stream.read(tail_size)
        position = tail.rfind(_ZIP_END_RECORD_SIGNATURE)
        if position < 0 or len(tail) - position < _ZIP_END_RECORD_BYTES:
            return False
        record_offset = file_size - tail_size + position
        # A ZIP64 locator just before the end record would make zipfile take the sizes from
        # ZIP64 records instead, which no Word or Excel file within the upload limit needs.
        if record_offset >= 20:
            stream.seek(start + record_offset - 20)
            if stream.read(4) == _ZIP64_LOCATOR_SIGNATURE:
                return False
        record = tail[position : position + _ZIP_END_RECORD_BYTES]

        def field(offset: int, width: int) -> int:
            return int.from_bytes(record[offset : offset + width], "little")

        if field(4, 2) or field(6, 2) or field(8, 2) != field(10, 2):
            return False  # spread over more than one disk
        entries, directory_size, directory_offset = field(10, 2), field(12, 4), field(16, 4)
        # The directory must end exactly where the end record begins. This rejects an archive with
        # data prepended before its first entry: there, the stored directory offset is relative to
        # the embedded archive while the end record sits further along, so the two differ by the
        # prefix length. Without this, the offset would be read here as absolute and a small decoy
        # directory validated, while zipfile - which computes a concatenation offset for prepended
        # data - would open the real, larger directory instead (independent review, round 7). Word
        # and Excel write no such prefix. This also implies the directory lies inside the file.
        if not (
            1 <= entries <= _ZIP_MAX_ENTRIES
            and directory_size <= _ZIP_MAX_DIRECTORY_BYTES
            and directory_offset + directory_size == record_offset
        ):
            return False
        # The end record's entry count is only a claim, and zipfile reads the directory to its end
        # regardless of it. So walk the directory itself, over the bytes the size above already
        # bounds, count the real entries and cross-check the claim (independent review, round 6:
        # a forged small count let a directory of hundreds of thousands of entries through).
        stream.seek(start + directory_offset)
        directory = stream.read(directory_size)
        if len(directory) != directory_size:
            return False
        position = 0
        counted = 0
        while position + 46 <= directory_size:
            if directory[position : position + 4] != _ZIP_CENTRAL_ENTRY_SIGNATURE:
                return False
            name_length = int.from_bytes(directory[position + 28 : position + 30], "little")
            extra_length = int.from_bytes(directory[position + 30 : position + 32], "little")
            comment_length = int.from_bytes(directory[position + 32 : position + 34], "little")
            position += 46 + name_length + extra_length + comment_length
            counted += 1
            if counted > _ZIP_MAX_ENTRIES:
                return False
        return position == directory_size and counted == entries
    except Exception:
        return False
    finally:
        stream.seek(start)


def _zip_holds(stream: BinaryIO, required: frozenset[str], forbidden: str) -> bool:
    """True when the archive's directory lists every required part and not the forbidden one.

    Called only after _zip_directory_is_bounded. Reads only the directory - it never decompresses
    a member - and looks names up in zipfile's own index rather than copying them. Leaves the
    stream where it found it; ZipFile does not close a file object it was handed.
    """
    start = stream.tell()
    try:
        with zipfile.ZipFile(stream) as archive:
            index = archive.NameToInfo
            return all(part in index for part in required) and forbidden not in index
    except Exception:
        # Any failure while reading the directory - a damaged archive, a part name that cannot be
        # decoded - means this is not an archive the check can vouch for: refuse the file rather
        # than let the error escape as a server error (independent review, round 4).
        return False
    finally:
        stream.seek(start)


def _compound_file_root_stream_names(stream: BinaryIO) -> set[str]:
    """The names of the streams at the top level of a compound file, or an empty set if the file
    cannot be read as one.

    Follows the [MS-CFB] layout: reads the header, the allocation table's sector list and the
    directory chain, then walks the directory tree from the root entry. Never reads a stream's
    content. The header's allocation-table counts must match what it lists, no table sector may be
    listed twice, and there may be no more table sectors than the file's size needs; table entries
    are read only as the directory chain needs them. Every sector index is checked against the
    file's length, every entry ID against the directory's size, every reached entry's name must be
    well formed, and every chain and the tree walk are guarded against loops - so a malformed file
    is refused rather than read without end, or at a cost out of proportion to its size. Leaves the
    stream where it found it.
    """
    start = stream.tell()
    try:
        stream.seek(0, io.SEEK_END)
        file_size = stream.tell() - start
        stream.seek(start)
        header = stream.read(_CFB_HEADER_BYTES)
        if len(header) < _CFB_HEADER_BYTES or not header.startswith(_OLE2_SIGNATURE):
            return set()
        if header[0x1C:0x1E] != b"\xfe\xff":  # byte order: little-endian
            return set()
        sector_shift = int.from_bytes(header[0x1E:0x20], "little")
        if sector_shift not in (9, 12):  # 512- or 4096-byte sectors
            return set()
        sector_size = 1 << sector_shift
        ids_per_sector = sector_size // 4
        # The header fills the first sector; sector n starts at (n + 1) * sector_size.
        sector_count = file_size // sector_size - 1

        def uint32(data: bytes, offset: int) -> int:
            return int.from_bytes(data[offset : offset + 4], "little")

        def read_sector(index: int) -> bytes | None:
            if not 0 <= index < sector_count:
                return None
            stream.seek(start + (index + 1) * sector_size)
            data = stream.read(sector_size)
            return data if len(data) == sector_size else None

        # The allocation table's own sectors: the header lists the first 109, and a chain of list
        # (DIFAT) sectors any more. The header states how many of each there are. The list count
        # must equal exactly the number those 109 header slots and each list sector's
        # (ids_per_sector - 1) slots need for the table count, so a crafted large count cannot
        # drive the loop; no list or table sector may be read twice; and the table may be no larger
        # than the file needs. Together these bound the work to the file's own size (independent
        # review, rounds 4 and 6 - round 6 found the list count was attacker-controlled and a list
        # sector could point back at itself).
        header_table_slots = (_CFB_HEADER_BYTES - 0x4C) // 4  # 109 for a 512-byte sector
        table_sector_count = uint32(header, 0x2C)
        list_sector_count = uint32(header, 0x48)
        if not 1 <= table_sector_count <= -(-sector_count // ids_per_sector):
            return set()
        extra_table_sectors = max(0, table_sector_count - header_table_slots)
        needed_list_sectors = -(-extra_table_sectors // (ids_per_sector - 1))
        if list_sector_count != needed_list_sectors:
            return set()
        table_sectors = [uint32(header, offset) for offset in range(0x4C, _CFB_HEADER_BYTES, 4)]
        table_sectors = [index for index in table_sectors if index != _CFB_FREE_SECTOR]
        list_sector = uint32(header, 0x44)
        visited_lists: set[int] = set()
        while list_sector not in (_CFB_END_OF_CHAIN, _CFB_FREE_SECTOR):
            data = read_sector(list_sector)
            if data is None or list_sector in visited_lists or len(visited_lists) >= needed_list_sectors:
                return set()
            visited_lists.add(list_sector)
            for offset in range(0, sector_size - 4, 4):
                index = uint32(data, offset)
                if index != _CFB_FREE_SECTOR:
                    table_sectors.append(index)
            if len(table_sectors) > table_sector_count:
                return set()
            list_sector = uint32(data, sector_size - 4)
        if (
            len(visited_lists) != needed_list_sectors
            or len(table_sectors) != table_sector_count
            or len(set(table_sectors)) != table_sector_count
        ):
            return set()

        table_cache: dict[int, bytes] = {}

        def next_sector(index: int) -> int | None:
            """The allocation table's entry for sector `index` - the next sector in its chain - or
            None if the table does not cover it."""
            position = index // ids_per_sector
            if not 0 <= index < sector_count or position >= table_sector_count:
                return None
            if position not in table_cache:
                data = read_sector(table_sectors[position])
                if data is None:
                    return None
                table_cache[position] = data
            return uint32(table_cache[position], (index % ids_per_sector) * 4)

        def entry_name(entry: bytes) -> str | None:
            """The entry's name, or None unless it is a well-formed [MS-CFB] name: 1 to 31 UTF-16
            characters, strictly encoded, closed by a NUL and holding no other NUL."""
            length = int.from_bytes(entry[0x40:0x42], "little")
            if length % 2 or not 4 <= length <= 64 or entry[length - 2 : length] != b"\x00\x00":
                return None
            try:
                name = entry[: length - 2].decode("utf-16-le")
            except UnicodeDecodeError:
                return None
            return None if "\x00" in name else name

        # Every directory entry, in the order the directory chain holds them: an entry's ID is its
        # position here.
        entries: list[bytes] = []
        directory_sector = uint32(header, 0x30)
        visited: set[int] = set()
        while directory_sector != _CFB_END_OF_CHAIN:
            data = read_sector(directory_sector)
            following = next_sector(directory_sector)
            if data is None or following is None or directory_sector in visited:
                return set()
            visited.add(directory_sector)
            entries.extend(
                data[offset : offset + _CFB_DIRECTORY_ENTRY_BYTES]
                for offset in range(0, sector_size, _CFB_DIRECTORY_ENTRY_BYTES)
            )
            directory_sector = following
        if not entries or entries[0][0x42] != _CFB_ROOT_OBJECT or entry_name(entries[0]) is None:
            return set()

        # The top-level streams are the root entry's children: a tree reached through the root's
        # child link, then each entry's left and right sibling links. A name no link reaches is
        # never counted, and a sub-storage's own children are not followed (independent review,
        # round 3).
        names: set[str] = set()
        pending = [uint32(entries[0], 0x4C)]
        reached: set[int] = set()
        while pending:
            entry_id = pending.pop()
            if entry_id == _CFB_NO_ENTRY:
                continue
            if entry_id == 0 or entry_id >= len(entries) or entry_id in reached:
                return set()
            reached.add(entry_id)
            entry = entries[entry_id]
            name = entry_name(entry)
            if entry[0x42] not in (_CFB_STORAGE_OBJECT, _CFB_STREAM_OBJECT) or name is None:
                return set()
            if entry[0x42] == _CFB_STREAM_OBJECT:
                names.add(name)
            pending.extend((uint32(entry, 0x44), uint32(entry, 0x48)))
        return names
    except Exception:
        # Any other failure while reading the structure means this is not a compound file the
        # check can vouch for: refuse it rather than let the error escape as a server error.
        return set()
    finally:
        stream.seek(start)


def _content_matches_extension(extension: str, head: bytes, stream: BinaryIO) -> bool:
    if extension == ".pdf":
        return head.startswith(_PDF_SIGNATURE)
    if extension == ".png":
        return head.startswith(_PNG_SIGNATURE)
    if extension in (".jpg", ".jpeg"):
        return head.startswith(_JPEG_SIGNATURE)
    if extension in _COMPOUND_FILE_REQUIRED_STREAMS:
        if not head.startswith(_OLE2_SIGNATURE):
            return False
        return bool(_compound_file_root_stream_names(stream) & _COMPOUND_FILE_REQUIRED_STREAMS[extension])
    if extension in _OOXML_REQUIRED_PARTS:
        if not head.startswith(_ZIP_SIGNATURE) or not _zip_directory_is_bounded(stream):
            return False
        return _zip_holds(stream, _OOXML_REQUIRED_PARTS[extension], _OOXML_MACRO_PARTS[extension])
    if extension in (".txt", ".csv"):
        # Text has no signature. A NUL byte marks a binary file - an executable, an image, an
        # archive - unless the text is UTF-16, which a byte-order mark announces.
        return head.startswith(_UTF16_BYTE_ORDER_MARKS) or b"\x00" not in head
    # An accepted extension with no rule here is refused: adding one to ALLOWED_UPLOAD_EXTENSIONS
    # without a content rule fails closed.
    return False


def _check_upload_content(file_name: str, stream: BinaryIO) -> None:
    """Refuse (422) a file whose opening bytes do not match its extension's format.

    Reads at most _CONTENT_HEAD_BYTES, plus the directory of a .docx or .xlsx archive or of a .doc
    or .xls compound file, and puts the stream back where it started, so the storage write that
    follows still counts every byte against the size limit. The stream must be seekable; FastAPI's UploadFile.file and io.BytesIO
    both are. Text and CSV are checked only to be text: a text file is not interpreted.
    """
    _, extension = os.path.splitext(file_name.lower())
    if not stream.seekable():
        raise DocumentUploadTypeError("The file could not be checked. Please try again.")
    start = stream.tell()
    head = stream.read(_CONTENT_HEAD_BYTES)
    stream.seek(start)
    if not _content_matches_extension(extension, head, stream):
        description = _CONTENT_DESCRIPTIONS.get(extension, "the type its name says")
        raise DocumentUploadTypeError(
            f"This file is named {extension} but its content is not {description}. "
            "Choose the right file, or save it again in that format."
        )


def delete_stored_document_object(row: dict[str, Any] | None) -> None:
    """Best-effort deletion of bytes already written for a document whose enclosing transaction
    did not commit.

    `_persist_stored_document` compensates for failures INSIDE itself. This function covers the
    gap that cannot: a failure after it has already returned - most importantly a failing
    `db.commit()`. Rolling the transaction back removes the `document_metadata` row but never the
    object the storage provider has already written, so without this the file survives with
    nothing referencing it, unreachable through the application and invisible to any cleanup that
    works from rows.

    Slice 9C guaranteed exactly this for uploads by keeping `db.commit()` inside its compensating
    try block. Slice 9E's refactor moved the commit out and lost it for the commit-failure path;
    independent review reproduced the leak by fault injection. Both call sites now share this one
    helper rather than each re-deriving the compensation.

    Deliberately best-effort: a secondary failure while cleaning up must not mask the original
    exception the caller is already handling.
    """
    if not row:
        return
    provider_code = row.get("storage_provider_code")
    storage_key = row.get("storage_key")
    if not provider_code or not storage_key:
        return
    try:
        get_storage_provider_by_code(provider_code).delete(storage_key=storage_key)
    except Exception:
        pass


def _persist_stored_document(
    db: Session,
    *,
    linked_record_type: str,
    linked_record_public_id: str,
    document_type: str,
    file_name: str,
    content_type: str,
    stream: BinaryIO,
    max_bytes: int,
    event_name: str,
    reason: str,
    remarks: str | None,
    current_user_public_id: str | None,
) -> tuple[dict[str, Any], Any]:
    """Shared storage-key generation, provider.save, document_metadata insert and event
    recording, used by BOTH `upload_document` (a real user upload) and
    `store_generated_document` (Slice 9E, a document THIS APPLICATION generated).

    Deliberately shared rather than duplicated: the rollback-and-delete compensation on failure
    below was a build-time correction in Slice 9C ("the first draft ... deleted the orphaned
    file on an insert failure but never rolled back the session"), and re-deriving it a second
    time for a second call site would risk re-introducing exactly that bug rather than reusing
    the already-corrected one.

    Does NOT commit. The caller owns the transaction: `upload_document` commits immediately
    after (a document upload is one atomic action), while `store_generated_document`'s caller
    (commercial_offers.service) must land its own quote-document row in the SAME transaction, so
    the document row and the quote-document row that references it are never observed apart.
    """
    _, extension = os.path.splitext(file_name.lower())
    document_public_id = str(uuid4())
    # Opaque to the provider's own internal layout - a filesystem path today, potentially a
    # SharePoint drive item id after a provider swap. Never derived from the caller-supplied
    # file name, which stays only in file_name/original_file_name for display.
    storage_key = f"{document_public_id[:4]}/{document_public_id[4:8]}/{document_public_id}{extension}"

    provider = get_storage_provider()
    bounded_stream = _SizeLimitingReader(stream, max_bytes=max_bytes)
    stored = provider.save(storage_key=storage_key, stream=bounded_stream, content_type=content_type)

    values = {
        "document_type": document_type,
        "linked_record_type": linked_record_type,
        "linked_record_public_id": linked_record_public_id,
        "file_name": file_name,
        "original_file_name": file_name,
        "storage_mode": STORAGE_MODE_LOCAL_UPLOAD,
        "storage_path_or_url": None,
        "version_no": 1,
        # "Uploaded" is reused rather than inventing a "Generated" status: from this module's
        # own vocabulary, the status describes whether bytes are stored in this application,
        # which is equally true whether a human uploaded them or the system generated them. The
        # distinguishing fact - that this row was generated, not uploaded - is already carried
        # by document_type ("QUOTATION") and by the event name (DocumentGenerated, not
        # DocumentUploaded), so a parallel status value would duplicate information without
        # adding any.
        "status": "Uploaded",
        "storage_provider_code": provider.provider_code,
        "storage_key": stored.storage_key,
        "content_type": content_type,
        "byte_size": stored.byte_size,
        "checksum_sha256": stored.checksum_sha256,
        "retention_due_at": None,
        "uploaded_by": current_user_public_id,
        "remarks": remarks,
    }

    try:
        row = insert_document_metadata(db, public_id=document_public_id, values=values)

        event = record_business_event(
            db,
            event_name=event_name,
            source_module=DOCUMENT_MODULE_NAME,
            record_type=DOCUMENT_RECORD_TYPE,
            record_public_id=document_public_id,
            user_public_id=current_user_public_id,
            status_after="Uploaded",
            reason=reason,
            remarks=remarks,
            event_payload={
                "schema_version": DOCUMENT_EVENT_SCHEMA_VERSION,
                "document_type": document_type,
                "linked_record_type": linked_record_type,
                "linked_record_public_id": linked_record_public_id,
                "content_type": content_type,
                "byte_size": stored.byte_size,
                # Never the bytes themselves, never the checksum's preimage - only enough to
                # prove what was recorded without carrying the file's content into the audit
                # trail.
            },
        )
    except Exception:
        # Whether the metadata insert or the event step failed, bytes were already written
        # before either ran - do not leave an orphaned file behind that no row references, and
        # do not leave the session in a failed transaction state for whatever the caller does
        # next.
        db.rollback()
        provider.delete(storage_key=storage_key)
        raise

    return row, event


def upload_document(
    db: Session,
    *,
    linked_record_type: str,
    linked_record_public_id: UUID,
    document_type: str,
    file_name: str,
    declared_content_type: str | None,
    stream: BinaryIO,
    remarks: str | None,
    current_user_public_id: str | None,
) -> DocumentUploadedResponse:
    """Store an uploaded file and record its document_metadata row.

    Performs NO authorization. POST /api/documents/upload calls upload_document_for_caller(),
    which checks the caller may attach to the linked record. This function stays caller-free on
    purpose, for trusted in-process callers: the smoke-data harness's upload_customer_document()
    and tests. It still refuses QUOTATION, so no caller of it can pass a file off as a generated
    quotation, and it refuses a file whose content does not match its extension.
    """
    # Every field is validated BEFORE a single byte is stored, so a rejected upload can never
    # leave an orphaned file behind.
    expected_content_type = _validate_upload_request(
        linked_record_type=linked_record_type,
        document_type=document_type,
        file_name=file_name,
        declared_content_type=declared_content_type,
        remarks=remarks,
    )
    # The owning module's say on this one record (ELG-1: a withdrawn certificate takes no copy). Before the
    # stream is read, like every other refusal.
    _ensure_record_takes_documents(
        db, linked_record_type, AttachRequest(str(linked_record_public_id), document_type, STORAGE_MODE_LOCAL_UPLOAD)
    )
    # After every request check and, on the HTTP path, after the rights check in
    # upload_document_for_caller(), so a refused upload's stream is still never read.
    _check_upload_content(file_name, stream)

    row: dict[str, Any] | None = None
    try:
        row, event = _persist_stored_document(
            db,
            linked_record_type=linked_record_type,
            linked_record_public_id=str(linked_record_public_id),
            document_type=document_type,
            file_name=file_name,
            content_type=expected_content_type,
            stream=stream,
            max_bytes=MAX_UPLOAD_BYTES,
            event_name=DOCUMENT_EVENT_UPLOADED,
            reason="Document uploaded.",
            remarks=remarks,
            current_user_public_id=current_user_public_id,
        )
        db.commit()
    except Exception:
        # Two distinct failure shapes reach here, and only one of them is already compensated:
        #
        #   - a failure INSIDE _persist_stored_document, which has already rolled back and
        #     deleted its own object. `row` is still None, so the cleanup below is a no-op and
        #     the file is not double-deleted.
        #   - a failure in db.commit(), which runs AFTER that function returned successfully.
        #     Here the bytes are on disk and the row is about to be rolled away, so the object
        #     must be deleted explicitly or it is orphaned forever.
        #
        # The earlier version of this block only rolled back, and its comment claimed to cover
        # the commit case while the code did not - the exact "asserted, not implemented" shape
        # independent review reproduced by fault injection.
        db.rollback()
        delete_stored_document_object(row)
        raise

    return DocumentUploadedResponse(document=_row_to_response(row), event=event.model_dump())


def upload_document_for_caller(
    db: Session,
    *,
    current_user: AuthUser,
    linked_record_type: str,
    linked_record_public_id: UUID,
    document_type: str,
    file_name: str,
    declared_content_type: str | None,
    stream: BinaryIO,
    remarks: str | None,
) -> DocumentUploadedResponse:
    """POST /api/documents/upload: validate, check the caller may attach to the linked record,
    then store.

    The rights check runs before this service reads the stream, so a refused upload stores no
    bytes, inserts no row and records no event. The web framework has already received the
    request body by then - FastAPI parses every form before any dependency runs - so routes.py
    caps each request at MAX_DOCUMENTS_REQUEST_BYTES as it arrives. Validation runs again inside
    upload_document(); that is cheap and keeps the trusted function safe to call on its own.
    """
    _validate_upload_request(
        linked_record_type=linked_record_type,
        document_type=document_type,
        file_name=file_name,
        declared_content_type=declared_content_type,
        remarks=remarks,
    )
    _ensure_may_write_link(db, current_user, linked_record_type)
    return upload_document(
        db,
        linked_record_type=linked_record_type,
        linked_record_public_id=linked_record_public_id,
        document_type=document_type,
        file_name=file_name,
        declared_content_type=declared_content_type,
        stream=stream,
        remarks=remarks,
        current_user_public_id=_user_public_id(current_user),
    )


def store_generated_document(
    db: Session,
    *,
    linked_record_type: str,
    linked_record_public_id: str,
    document_type: str,
    file_name: str,
    content_type: str,
    content: bytes,
    current_user_public_id: str | None,
) -> dict[str, Any]:
    """Store a document generated BY THIS APPLICATION - never a user upload - and record its
    document_metadata row (Slice 9E).

    NOT reachable from any HTTP route, by construction rather than by convention: `content_type`
    must be a key of GENERATED_CONTENT_TYPES, which is a closed map deliberately separate from
    ALLOWED_UPLOAD_EXTENSIONS. POST /api/documents/upload validates against
    ALLOWED_UPLOAD_EXTENSIONS only and has no ".html" entry there, so a caller cannot reach this
    code path by uploading a file with a spoofed content type.

    Does NOT commit - the caller owns the transaction. See _persist_stored_document's docstring
    for why: the quote-document row this document backs must land in the same transaction as
    this document_metadata row, or not at all.

    The event recorded is DocumentGenerated, never DocumentUploaded.
    """
    if content_type not in GENERATED_CONTENT_TYPES:
        raise DocumentValidationError(f"Unsupported generated document content type: {content_type!r}.")

    stream = io.BytesIO(content)
    row, _event = _persist_stored_document(
        db,
        linked_record_type=linked_record_type,
        linked_record_public_id=linked_record_public_id,
        document_type=document_type,
        file_name=file_name,
        content_type=content_type,
        stream=stream,
        max_bytes=len(content),
        event_name=DOCUMENT_EVENT_GENERATED,
        reason="Document generated by the application.",
        remarks=None,
        current_user_public_id=current_user_public_id,
    )
    return row


def get_document_content_for_caller(
    db: Session, *, public_id: UUID, current_user: AuthUser
) -> tuple[dict[str, Any], ContextManager[BinaryIO]]:
    """Resolve a document's row and an open, readable stream for its bytes.

    Record-scoped and fail-closed exactly like list_documents_for_record_for_caller, plus the
    extra interaction-content check via _may_read_content - see the module docstring.
    """
    row = get_document_by_public_id(db, str(public_id))
    if row is None:
        raise DocumentNotFoundError("Document not found.")

    if not _may_read_content(db, current_user, row["linked_record_type"]):
        raise DocumentAccessDeniedError("You do not have permission to download this document.")

    if row["storage_mode"] != STORAGE_MODE_LOCAL_UPLOAD or not row.get("storage_key"):
        raise DocumentContentUnavailableError(
            "This document's content is not stored by this application. "
            "See storage_path_or_url for its external location, if any."
        )

    # Resolved from the provider recorded ON THIS ROW, never from whatever this deployment
    # happens to be configured with now. That column exists so an object can be resolved back to
    # the provider holding it after a provider swap; using the configured provider instead would
    # silently resolve content through the wrong backend (independent review, correction pass 1,
    # finding 3). An unresolvable code fails closed.
    provider_code = row.get("storage_provider_code")
    if not provider_code:
        raise DocumentContentUnavailableError(
            "This document is recorded as uploaded but names no storage provider, so its "
            "content cannot be resolved."
        )
    try:
        provider = get_storage_provider_by_code(provider_code)
    except UnknownStorageProviderError as exc:
        raise DocumentContentUnavailableError(
            f"This document's content is held by storage provider {provider_code!r}, which this "
            "deployment cannot resolve."
        ) from exc

    try:
        stream_context = provider.open(storage_key=row["storage_key"])
    except StorageObjectNotFoundError as exc:
        raise DocumentContentUnavailableError(
            "This document is recorded as uploaded, but its stored file could not be found."
        ) from exc

    return row, stream_context


_CONTENT_READ_CHUNK_BYTES = 65536


def iter_document_content(stream_context: ContextManager[BinaryIO]) -> Iterator[bytes]:
    """Turn the open-stream context manager from get_document_content_for_caller into a plain
    byte iterator suitable for a StreamingResponse, closing the underlying stream when
    exhausted or when the caller stops iterating early.
    """
    with stream_context as handle:
        while True:
            chunk = handle.read(_CONTENT_READ_CHUNK_BYTES)
            if not chunk:
                break
            yield chunk
