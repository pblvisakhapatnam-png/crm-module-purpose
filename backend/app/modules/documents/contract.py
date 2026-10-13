"""Document Storage Foundation contract constants (Slice 9C).

Provider-neutral document metadata plus one local storage provider behind an abstraction, so a
later SharePoint move is a provider swap plus a file migration rather than a rewrite. See
docs/agent/slices/slice-9c-document-storage-foundation.md for the full design and the two
defects this slice closes.
"""

from __future__ import annotations

from app.modules.authorization.contract import (
    ACCOUNT_DOCUMENT_CAPTURE,
    ACCOUNT_READ,
    COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE,
    COMMERCIAL_OFFER_READ,
    EQUIPMENT_IDENTITY_READ,
    EQUIPMENT_REFERENCE_MANAGE,
    INTERACTION_CONTENT_READ,
    INTERACTION_CREATE,
    INTERACTION_READ,
    LEAD_READ,
    LEAD_UPDATE,
    OPPORTUNITY_READ,
    OPPORTUNITY_UPDATE,
    WORK_ORDER_CREATE,
    WORK_ORDER_READ,
)

DOCUMENT_MODULE_NAME = "documents"
DOCUMENT_METADATA_TABLE = "document_metadata"
DOCUMENT_RECORD_TYPE = "document_metadata"

# --- storage_mode ---------------------------------------------------------------------------
# "local_upload" is reachable ONLY through POST /api/documents/upload, which actually stores
# bytes. POST /api/documents/metadata (no bytes involved) may use only the other two.
STORAGE_MODE_LOCAL_UPLOAD = "local_upload"
STORAGE_MODE_EXTERNAL_LINK = "external_link"
STORAGE_MODE_FUTURE_SHAREPOINT = "future_sharepoint"

# POST /api/documents/metadata records a pointer to bytes stored elsewhere; it never stores
# bytes itself, so it may not claim local_upload. That mode is reachable only through the
# dedicated upload route, which populates the columns the database CHECK constraint requires.
METADATA_ROUTE_ALLOWED_STORAGE_MODES = (STORAGE_MODE_EXTERNAL_LINK, STORAGE_MODE_FUTURE_SHAREPOINT)

ALLOWED_STATUSES = ("Draft", "Uploaded", "Linked", "Verified", "Rejected", "Archived")

# --- field length bounds -----------------------------------------------------------------------
# These mirror the `document_metadata` column widths exactly. The upload route receives its
# fields as multipart form parts, which carry no Pydantic model and therefore none of
# DocumentMetadataCreate's `max_length` validation - so the bounds have to be applied explicitly
# in the service layer, BEFORE any bytes are stored. Without them an over-length value reached
# PostgreSQL and surfaced as a 500 rather than a 422 (independent review, correction pass 1).
MAX_LINKED_RECORD_TYPE_LENGTH = 100
MAX_FILE_NAME_LENGTH = 255
MAX_DOCUMENT_TYPE_LENGTH = 100
MAX_REMARKS_LENGTH = 1000

# --- storage provider -----------------------------------------------------------------------
STORAGE_PROVIDER_LOCAL = "local"

# --- upload limits (owner decision 3, 8 September 2026: up to 25 MB; business documents and
# images only) --------------------------------------------------------------------------------
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

# The most any documents request body may carry: one file at the upload limit plus 1 MB for the
# form's other fields and its multipart framing. routes.py counts every documents request's body
# against it as the bytes arrive - before the body is parsed, and so before authentication or any
# rights check (independent review of the upload package, round 1).
MAX_DOCUMENTS_REQUEST_BYTES = MAX_UPLOAD_BYTES + 1024 * 1024

# Maps an accepted file extension (lowercase, with leading dot) to the exact content type it
# must be declared as. Validated on BOTH sides deliberately: a caller declaring
# "application/pdf" for a file named "invoice.exe" is rejected just as surely as one declaring
# "application/x-msdownload" for "invoice.pdf" - neither half is trusted alone.
ALLOWED_UPLOAD_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
    ".csv": "text/csv",
}

# --- document_type -----------------------------------------------------------------------
# QUOTATION added by Slice 9E: a generated quotation document is distinguishable from any other
# commercial document type. It is set only by store_generated_document() in service.py, never
# by a caller through either metadata route.
# CERTIFICATE added by ELG-1: the copy of a machine's certificate - its registration, insurance, pollution
# certificate, road tax, fitness, permit, thorough examination or load test.
DOCUMENT_TYPE_CODES = ("PAN", "GST", "KYC", "RFQ", "COMMERCIAL", "OTHER", "QUOTATION", "CERTIFICATE", "VENDOR_QUOTE")

# The types only the application itself may set. A row carrying QUOTATION presents, in every
# document list, as a quotation this application generated from a Commercial Offer (Slice 9E); a
# file a user uploaded under that type would pass for one. store_generated_document() is the only
# writer, and it is reachable from no HTTP route.
SYSTEM_GENERATED_DOCUMENT_TYPE_CODES = ("QUOTATION",)

# What a caller may choose when uploading a file: every type except the system-generated ones.
# Both user paths refuse the system-generated types; the metadata route, which accepts free-text
# types, refuses only those.
UPLOADABLE_DOCUMENT_TYPE_CODES = tuple(
    code for code in DOCUMENT_TYPE_CODES if code not in SYSTEM_GENERATED_DOCUMENT_TYPE_CODES
)

# --- system-generated documents (Slice 9E) ----------------------------------------------------
# A CLOSED, SEPARATE map from ALLOWED_UPLOAD_EXTENSIONS above, deliberately not merged into it.
# ".html" must never become an accepted upload extension: letting a caller upload arbitrary HTML
# through POST /api/documents/upload would put attacker-controlled markup into the store, which
# this slice must not buy its own convenience with. This map is consulted only by
# store_generated_document() in service.py, which is not reachable from any HTTP route - the
# generated bytes always come from commercial_offers.quote_render.render_quote_html(), never
# from a caller-supplied stream.
GENERATED_CONTENT_TYPES: dict[str, str] = {
    "text/html": ".html",
}

# --- record-scoped download/read authorization, fail-closed ---------------------------------
#
# A caller may see a document's metadata, or download its bytes, only if they may read the
# record the document is linked to. This is checked in service.py (not routes.py) via
# has_permission(...) directly, exactly as Slice 9D placed its content-redaction check there:
# the route-permission guard (test_authorization_route_migration_guard.py) permits at most one
# require_permission(...) dependency per route and forbids reading `.role_codes` inside a route
# module outside two narrowly pinned pre-existing exceptions, neither of which is this module.
#
# A linked_record_type absent from this map DENIES. It never allows. This is deliberate and is
# the single most important line in this file: linked_record_type is free-text VARCHAR(100)
# with no database constraint, and the two modules already disagree on vocabulary for the same
# concept - existing document_metadata rows say "account" while Slice 9D's canonical Account
# link type is "business_party". Both are mapped below for exactly that reason, and an unmapped
# value must never silently fall through to "allowed".
DOCUMENT_LINK_READ_PERMISSION: dict[str, str] = {
    "account": ACCOUNT_READ,
    "business_party": ACCOUNT_READ,
    "lead": LEAD_READ,
    "opportunity": OPPORTUNITY_READ,
    "commercial_offer": COMMERCIAL_OFFER_READ,
    "work_order": WORK_ORDER_READ,
    "interaction": INTERACTION_READ,
    # ELG-1: a machine's certificate. Its copy shows the certificate's number and often the engine and chassis
    # numbers, so reading it needs what seeing those numbers needs (owner, 27 September 2026, Q6).
    "eligibility_certificate": EQUIPMENT_IDENTITY_READ,
    # Slice 4G: a market rate's quote copy (a broker's screenshot, email or document). Whoever reads the offer's
    # rates reads it.
    "commercial_offer_market_rate": COMMERCIAL_OFFER_READ,
}

# A document attached to a customer conversation inherits that conversation's sensitivity.
# Downloading it requires this SECOND, additional permission on top of the base link-read
# permission above - the same grant that already controls who may read the message body
# (Slice 9D). Without this, a download route would reopen exactly the leak Slice 9D closed:
# the same "redaction defeated by a pointer" shape, with a file attachment as the pointer.
DOCUMENT_LINK_EXTRA_CONTENT_PERMISSION: dict[str, str] = {
    "interaction": INTERACTION_CONTENT_READ,
}

# --- record-scoped upload/record authorization, fail-closed ---------------------------------
#
# Owner decision, 11 September 2026: only people who can change a record may attach a file to it
# (POST /api/documents/upload) or record document metadata against it (POST
# /api/documents/metadata). DOCUMENT_UPLOAD, which all six roles hold, only admits a caller to
# those two routes; this map decides what they may attach to. Checked in service.py for the same
# reasons as the read map above, and fail-closed the same way: an unmapped linked_record_type
# denies. Its keys mirror DOCUMENT_LINK_READ_PERMISSION's exactly - pinned by
# tests/test_document_upload_rights.py - so nothing can be attachable without also being readable.
#
# The owner named two sets:
#   Account            ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER
#   Commercial Offer   ADMIN, SALES_USER, SALES_MANAGER, OPERATIONS_USER
# Account uses ACCOUNT_DOCUMENT_CAPTURE, the grant POST /api/accounts/{public_id}/documents has
# carried since Slice 1J, so both ways of attaching to an Account now admit the same people. The
# other four types apply the same rule - "those who can change it" - through each module's
# existing change permission.
#
# Commercial Offer reuses COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE rather than a dedicated code. It
# grants exactly the owner's set - Operations holds it because Operations collects the market
# rates behind an offer (Slice 4D) - whereas a dedicated code needs its own seed migration,
# because has_permission() reads authz_role_permission, not this contract. The cost is coupling:
# changing who may record pricing evidence now changes who may attach files to an offer. Splitting
# them later takes one post-baseline code, its seed migration, and a change to this entry.
DOCUMENT_LINK_WRITE_PERMISSION: dict[str, str] = {
    "account": ACCOUNT_DOCUMENT_CAPTURE,
    "business_party": ACCOUNT_DOCUMENT_CAPTURE,
    "lead": LEAD_UPDATE,
    "opportunity": OPPORTUNITY_UPDATE,
    "commercial_offer": COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE,
    "work_order": WORK_ORDER_CREATE,
    "interaction": INTERACTION_CREATE,
    # ELG-1: whoever records certificates attaches their copies - the Fleet Admin (Admin, for now).
    "eligibility_certificate": EQUIPMENT_REFERENCE_MANAGE,
    # Slice 4G: whoever records the offer's market rates attaches their quote copies.
    "commercial_offer_market_rate": COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE,
}

# --- what the owning module says about attaching to one record (ELG-1) -------------------------
#
# For these linked record types, the module that owns the record decides whether a file may be
# attached to one particular record - a withdrawn certificate refuses a copy - through a check it
# registers with the documents service (register_attach_check). Fail-closed like the maps above: a
# type listed here with no check registered refuses every attachment.
DOCUMENT_LINK_TYPES_WITH_ATTACH_CHECK = frozenset({"eligibility_certificate", "commercial_offer_market_rate"})

# A document type that belongs to one linked record type only, refused on any other by both routes before the
# rights check (Slice 4G, review 4G-R1-001): a vendor quote filed on an offer or an Account would skip the market
# rate's own check - its line, and whether the offer can still change.
DOCUMENT_TYPE_ONLY_FOR_LINK_TYPE: dict[str, str] = {"VENDOR_QUOTE": "commercial_offer_market_rate"}
