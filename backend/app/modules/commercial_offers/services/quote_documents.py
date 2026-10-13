"""Slice 9E - Quotation Generation.

The quotation document: the snapshot of the offer it is generated from, generating and listing its
versions, and approving one for issue.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_LINE_STATUS_ACTIVE,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_RECORD_TYPE,
    COMMERCIAL_OFFER_EVENT_QUOTE_DOCUMENT_APPROVED_FOR_ISSUE,
    COMMERCIAL_OFFER_EVENT_QUOTE_DOCUMENT_GENERATED,
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_APPROVE_BLOCKED_OFFER_STATUSES,
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_GENERATE_ALLOWED_STATUSES,
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_RECORD_TYPE,
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_APPROVED_FOR_ISSUE,
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT,
)
from app.modules.commercial_offers.repository import (
    get_commercial_offer_context_by_public_id,
    lock_commercial_offer_row,
    list_commercial_offer_lines_for_offer,
    list_commercial_offer_tc_clauses_for_offer,
    get_next_quote_document_version_no,
    get_user_display_name,
    get_quote_document_row_by_public_id,
    get_quote_snapshot_source_context,
    insert_commercial_offer_quote_document,
    list_commercial_offer_quote_documents_for_offer,
    lock_commercial_offer_quote_document_row,
    single_instant_read_session,
    mark_quote_document_approved_for_issue,
    supersede_earlier_quote_documents,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferQuoteDocumentApproveRequest,
    CommercialOfferQuoteDocumentApprovedResponse,
    CommercialOfferQuoteDocumentGeneratedResponse,
    CommercialOfferQuoteDocumentResponse,
)
from app.modules.events.service import record_business_event

# Slice 9E reads Account identity (name, legal name, addresses, GSTINs) for quote rendering.
# Read-only cross-module repository calls, following the same established pattern this module
# already uses for crm_opportunity/business_party (raw joins in commercial_offers/repository.py)
# and for crm_work_order (get_work_order_lineage_context) - never writing to another module's
# tables, only reading through its own repository functions rather than reaching past them.
from app.modules.accounts.contract import (
    ADDRESS_TYPE_COMMUNICATION,
    ADDRESS_TYPE_REGISTERED_OFFICE,
    TAX_VERIFICATION_STATE_REJECTED_INCORRECT,
)
from app.modules.accounts.repository import list_business_party_addresses, list_business_party_gstins

# Slice 9E stores the generated quotation document through Slice 9C's storage abstraction.
from app.modules.documents.contract import GENERATED_CONTENT_TYPES
from app.modules.documents.service import delete_stored_document_object, store_generated_document

from app.modules.commercial_offers.quote_render import count_unpriced_lines, render_quote_html
from app.shared.currency import currency_code_key

from app.modules.commercial_offers.services.common import (
    CommercialOfferNotFoundError,
    CommercialOfferQuoteDocumentNotFoundError,
    CommercialOfferValidationError,
    _clean_optional,
    _event_dict,
)


QUOTE_SNAPSHOT_SCHEMA_VERSION = "1.0"


INDIA_DISPLAY_TIME_ZONE = ZoneInfo("Asia/Kolkata")


# Only these Account address types may be frozen into a customer-facing quotation.
#
# SITE, BILLING_DRAFT and OTHER are deliberately excluded (independent review, correction pass 1,
# finding 3). A site address is operational, not the customer's identity; BILLING_DRAFT is
# explicitly "draft CRM information only and is not Finance-approved billing master data" per the
# Account contract; OTHER is by definition unclassified. Because the artifact is frozen, an
# unrelated address captured into a version cannot be repaired by later correcting the Account -
# it can only be superseded by generating a new version.
QUOTE_DOCUMENT_ALLOWED_ADDRESS_TYPES = (ADDRESS_TYPE_REGISTERED_OFFICE, ADDRESS_TYPE_COMMUNICATION)


QUOTE_DOCUMENT_ADDRESS_TYPE_LABELS: dict[str, str] = {
    ADDRESS_TYPE_REGISTERED_OFFICE: "Registered office",
    ADDRESS_TYPE_COMMUNICATION: "Communication",
}


def _format_address_line(address: Any) -> str:
    """One readable, labelled line from an AccountAddressResponse.

    The type label is kept so a reader can distinguish a registered office from a communication
    address on the printed quotation, rather than seeing two unattributed addresses.
    """
    label = QUOTE_DOCUMENT_ADDRESS_TYPE_LABELS.get(address.address_type_code)
    parts = [address.address_line1]
    if address.address_line2:
        parts.append(address.address_line2)
    city_state = address.city
    if address.state:
        city_state = f"{city_state}, {address.state}"
    parts.append(city_state)
    if address.postal_code:
        parts.append(address.postal_code)
    formatted = ", ".join(part for part in parts if part)
    return f"{label}: {formatted}" if label else formatted


def _format_business_datetime(value: datetime) -> str:
    """Business timestamps display in Asia/Kolkata for PBL users (AGENTS.md, "Date/time display
    rule"). A generated quotation is a business/customer-facing document, not only an internal
    API response, so it follows the same convention rather than showing a bare UTC timestamp."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    localized = value.astimezone(INDIA_DISPLAY_TIME_ZONE)
    return localized.strftime("%d %b %Y, %H:%M IST")


def _snapshot_line(line: Any, *, offer_currency_key: str) -> dict[str, Any]:
    snapshot_line = {
        "line_number": line.line_number,
        "scope_description": line.scope_description,
        "equipment_service_category": line.equipment_service_category,
        "quantity": str(line.quantity) if line.quantity is not None else None,
        "uom": line.uom,
        "rate_amount": str(line.rate_amount) if line.rate_amount is not None else None,
        "line_amount": str(line.line_amount) if line.line_amount is not None else None,
    }
    if currency_code_key(line.currency_code) != offer_currency_key:
        snapshot_line["currency_code"] = currency_code_key(line.currency_code)
    return snapshot_line


def build_quote_snapshot(db: Session, *, commercial_offer_id: int) -> dict[str, Any]:
    """Gathers the offer header, Account identity, ACTIVE offer lines and active header T&C
    clause snapshots into one canonical, JSON-serializable dict.

    This SAME dict is what compute_source_fingerprint() hashes AND what
    quote_render.render_quote_html() renders directly - deliberately one shape, not two
    independently maintained ones. See quote_render.py's module docstring for why that matters.

    Deliberately never raises for a BUSINESS reason (zero active lines, no Account traceability,
    ...): this is a pure data-gathering function. A generation caller decides what is required
    and raises accordingly; a listing/staleness caller must be able to call this against an
    offer whose data has since changed - possibly to something incomplete - without it raising.
    Only a genuinely missing Commercial Offer (the id itself does not resolve) raises here,
    because there is no snapshot at all to return in that case.
    """
    context = get_quote_snapshot_source_context(db, commercial_offer_id=commercial_offer_id)
    if context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    lines = list_commercial_offer_lines_for_offer(db, commercial_offer_id=commercial_offer_id)
    active_lines = [line for line in lines if line.line_status_code == COMMERCIAL_OFFER_LINE_STATUS_ACTIVE]
    tc_clauses = list_commercial_offer_tc_clauses_for_offer(db, commercial_offer_id=commercial_offer_id)

    account_addresses: list[str] = []
    account_gstins: list[str] = []
    account_public_id = context.get("account_public_id")
    if account_public_id:
        # Filtered, not merely gathered. See QUOTE_DOCUMENT_ALLOWED_ADDRESS_TYPES above for why
        # a site/draft-billing/other address must never reach a customer-facing quotation.
        account_addresses = [
            _format_address_line(address)
            for address in list_business_party_addresses(db, account_public_id=str(account_public_id))
            if address.address_type_code in QUOTE_DOCUMENT_ALLOWED_ADDRESS_TYPES
        ]
        # A GSTIN the business has already determined to be wrong must never be printed on a
        # customer document. Every other verification state is still legitimately quotable: an
        # unverified or pending GSTIN is the customer's stated number and is exactly what a
        # prototype-stage quotation carries today (independent review, correction pass 1,
        # finding 3).
        account_gstins = [
            gstin.gstin
            for gstin in list_business_party_gstins(db, account_public_id=str(account_public_id))
            if gstin.gstin_verification_state_code != TAX_VERIFICATION_STATE_REJECTED_INCORRECT
        ]

    offer_currency_code = context.get("currency_code") or "INR"
    offer_currency_key = currency_code_key(offer_currency_code)
    # Amounts in different currencies are never added together (AGENTS.md, "Currency"): the total
    # is of the lines in the offer's own currency, and a line in another currency is totalled
    # apart by the renderer. A line names its currency only when it differs from the offer's -
    # compared as stored codes are, so a code saved in another case is the same currency - and a
    # single-currency offer's snapshot, with every fingerprint stored for one, is unchanged.
    total_amount = sum(
        (
            line.line_amount
            for line in active_lines
            if line.line_amount is not None and currency_code_key(line.currency_code) == offer_currency_key
        ),
        start=Decimal("0.00"),
    )

    return {
        "schema_version": QUOTE_SNAPSHOT_SCHEMA_VERSION,
        "offer_code": context.get("offer_code"),
        "offer_date": context["offer_date"].isoformat() if context.get("offer_date") else None,
        "valid_until": context["valid_until"].isoformat() if context.get("valid_until") else None,
        "customer_request_reference": context.get("customer_request_reference"),
        "currency_code": offer_currency_code,
        "account_name": context.get("account_name"),
        "account_legal_name": context.get("account_legal_name"),
        "account_addresses": account_addresses,
        "account_gstins": account_gstins,
        "lines": [_snapshot_line(line, offer_currency_key=offer_currency_key) for line in active_lines],
        "total_amount": str(total_amount),
        # Excludes pricing evidence, the selected basis rate, its selection rationale and credit
        # review outcomes by construction - none of those are gathered here at all, not merely
        # omitted from this dict after the fact. Those are internal commercial records; a
        # document rendered for a customer must not carry them (owner-approved design, see
        # docs/agent/slices/slice-9e-quotation-generation.md, "What the document contains").
        "tc_clauses": [
            {
                "clause_id_snapshot": clause.clause_id_snapshot,
                "title_snapshot": clause.title_snapshot,
                "clause_text_snapshot": clause.clause_text_snapshot,
            }
            for clause in tc_clauses
        ],
    }


def build_quote_snapshot_at_one_instant(db: Session, *, commercial_offer_id: int) -> dict[str, Any]:
    """build_quote_snapshot, with every part read at one instant.

    build_quote_snapshot reads the header, lines, T&C clauses, addresses and GSTINs in separate
    statements. Line, clause and Account writers do not take the offer lock, so under READ
    COMMITTED those parts can come from different moments and combine into a snapshot the offer
    never had - one that can match a frozen version the offer matched at no instant (independent
    review, round 2). Generation and approval therefore read their snapshot here, in one read-only
    REPEATABLE READ transaction; the listing reads the offer, its versions and the snapshot together
    in one such transaction of its own.

    Generation and approval call this after taking their row locks, so the instant falls inside
    the locked window, where the offer's status and the quotation row cannot change. The read sees
    committed data only, which is sufficient because every caller reads before it writes.
    """
    with single_instant_read_session(db) as read_db:
        return build_quote_snapshot(read_db, commercial_offer_id=commercial_offer_id)


def compute_source_fingerprint(snapshot: dict[str, Any]) -> str:
    """sha256 over a canonical JSON encoding of the source-data snapshot: sorted keys, no
    whitespace, so the same logical content always produces the same fingerprint regardless of
    Python dict insertion order. Amounts are already strings in the snapshot (see
    build_quote_snapshot), so no Decimal/float ever reaches json.dumps here.
    """
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def quote_document_approval_blocked_reason(
    *,
    offer_status_code: str,
    row: dict[str, Any],
    snapshot: dict[str, Any],
    current_fingerprint: str,
) -> str | None:
    """Why this quotation version cannot be approved for issue right now, or None if it can.

    The single source for both the approval precondition and the approval_blocked_reason field
    that drives the Approve button, so the screen and the server give the same reason for the
    same state. The field is advisory: approval re-checks under its locks, so a change made after
    the screen was loaded can still be refused. Who may approve is deliberately not considered:
    that is the route's permission (COMMERCIAL_OFFER_QUOTE_APPROVE), not a property of the record.

    The last two checks are owner decisions of 9 and 11 September 2026, and they only work as a
    pair. If the version still matches the offer and every active line on the offer is priced,
    then every line in the frozen document is priced too. Checking the offer's current lines
    alone would not be enough: a version frozen reading "Not fully priced" would become
    approvable the moment the missing rate was filled in on the offer.
    """
    if offer_status_code in COMMERCIAL_OFFER_QUOTE_DOCUMENT_APPROVE_BLOCKED_OFFER_STATUSES:
        return (
            "This Commercial Offer has concluded, so a quotation can no longer be approved for "
            f"issue against it. Current status is {offer_status_code}."
        )
    if row.get("superseded_at") is not None:
        return (
            "This quotation document version has been superseded by a later version and can no "
            "longer be approved. Approve the current version instead."
        )
    if row["quote_status_code"] != COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT:
        return "This quotation document version is already approved for issue."
    unpriced = count_unpriced_lines(snapshot["lines"])
    if unpriced:
        lines_have = "line has" if unpriced == 1 else "lines have"
        return (
            f"{unpriced} active {lines_have} no rate. Every active line must be priced before a "
            "quotation can be approved for issue."
        )
    if row["source_fingerprint"] != current_fingerprint:
        return (
            "The offer has changed since this version was generated, so this version no longer "
            "matches it. Generate a new version and approve that one instead."
        )
    return None


def _quote_document_row_to_response(
    row: dict[str, Any],
    *,
    offer_status_code: str,
    snapshot: dict[str, Any],
    current_fingerprint: str,
) -> CommercialOfferQuoteDocumentResponse:
    return CommercialOfferQuoteDocumentResponse(
        public_id=row["public_id"],
        commercial_offer_public_id=row["commercial_offer_public_id"],
        version_no=row["version_no"],
        quote_reference=row["quote_reference"],
        document_public_id=row["document_public_id"],
        quote_status_code=row["quote_status_code"],
        generated_by=row.get("generated_by"),
        generated_by_display_name=row.get("generated_by_display_name"),
        generated_at=row["generated_at"],
        approved_by=row.get("approved_by"),
        approved_by_display_name=row.get("approved_by_display_name"),
        approved_at=row.get("approved_at"),
        approval_note=row.get("approval_note"),
        superseded_at=row.get("superseded_at"),
        is_stale=row["source_fingerprint"] != current_fingerprint,
        approval_blocked_reason=quote_document_approval_blocked_reason(
            offer_status_code=offer_status_code,
            row=row,
            snapshot=snapshot,
            current_fingerprint=current_fingerprint,
        ),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def generate_commercial_offer_quote_document(
    db: Session,
    *,
    public_id: UUID,
    current_user_public_id: str | None,
) -> CommercialOfferQuoteDocumentGeneratedResponse:
    """Generates a new, frozen, versioned quotation document for a Commercial Offer.

    Reads offer_status_code (to validate it is eligible) and then inserts a dependent record -
    the shape the Slice 9B contract requires locking before reading. The Slice 9B discovery
    guard (EXPECTED_STATUS_WRITING_FUNCTIONS in test_slice_9b_pilot_hardening.py) only detects
    functions that WRITE offer_status_code; this function only reads it, so that guard does not
    cover this path - Slice 9E's own AST ordering test does instead. See
    docs/agent/slices/slice-9e-quotation-generation.md, "Preconditions, and the row lock".
    """
    if lock_commercial_offer_row(db, public_id=str(public_id)) is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    offer_status_code = commercial_offer_context["offer_status_code"]
    if offer_status_code not in COMMERCIAL_OFFER_QUOTE_DOCUMENT_GENERATE_ALLOWED_STATUSES:
        raise CommercialOfferValidationError(
            "A quotation document can be generated only while the Commercial Offer is Draft, "
            f"Ready for Review or Submitted. Current status is {offer_status_code}."
        )

    if not commercial_offer_context.get("account_public_id"):
        raise CommercialOfferValidationError(
            "This Commercial Offer's Opportunity is not linked to an Account. Link it to an "
            "Account from the Opportunity page before "
            "generating a quotation document."
        )

    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])
    offer_code = commercial_offer_context["offer_code"]
    offer_version_number = int(commercial_offer_context["version_number"])

    snapshot = build_quote_snapshot_at_one_instant(db, commercial_offer_id=commercial_offer_id)
    if not snapshot["lines"]:
        raise CommercialOfferValidationError(
            "This Commercial Offer has no active lines. Add at least one active line before "
            "generating a quotation document."
        )

    fingerprint = compute_source_fingerprint(snapshot)
    version_no = get_next_quote_document_version_no(db, commercial_offer_id=commercial_offer_id)
    offer_version_reference = offer_code if offer_version_number == 1 else f"{offer_code} v{offer_version_number}"
    quote_reference = f"{offer_version_reference}/V{version_no}"
    # ONE timestamp, used for both the printed document and the stored row. Previously the
    # document rendered a Python clock reading while the row took the database's CURRENT_TIMESTAMP
    # - two sources for one fact, which can disagree whenever the application and database clocks
    # differ, leaving an audit record that contradicts the document it describes. Found during
    # this correction pass, not raised by review.
    generated_at = datetime.now(timezone.utc)
    generated_at_display = _format_business_datetime(generated_at)
    prepared_by_display = get_user_display_name(db, public_id=current_user_public_id) or "PBL"
    # Deliberately excludes the customer name: Slice 9C established that a file name alone
    # leaks ("Acme-PAN-card.pdf discloses both the customer and the nature of the document"),
    # and the generic documents list is visible more widely than this one offer.
    offer_version_file_part = offer_code if offer_version_number == 1 else f"{offer_code}-v{offer_version_number}"
    file_name = f"Quotation-{offer_version_file_part}-V{version_no}.html"

    html_content = render_quote_html(
        snapshot,
        quote_reference=quote_reference,
        version_no=version_no,
        generated_at_display=generated_at_display,
        prepared_by_display=prepared_by_display,
    )

    document_row: dict[str, Any] | None = None
    try:
        document_row = store_generated_document(
            db,
            linked_record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            linked_record_public_id=str(public_id),
            document_type="QUOTATION",
            file_name=file_name,
            content_type=next(iter(GENERATED_CONTENT_TYPES)),
            content=html_content.encode("utf-8"),
            current_user_public_id=current_user_public_id,
        )

        # Generating version N+1 supersedes every earlier version in the SAME transaction, so a
        # reader never observes two simultaneously non-superseded versions for one offer.
        supersede_earlier_quote_documents(db, commercial_offer_id=commercial_offer_id)

        quote_document_public_id = str(uuid4())
        values = {
            "version_no": version_no,
            "quote_reference": quote_reference,
            "document_public_id": document_row["document_public_id"],
            "source_fingerprint": fingerprint,
            "quote_status_code": COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT,
            "generated_by": current_user_public_id,
            "generated_at": generated_at,
        }
        row = insert_commercial_offer_quote_document(
            db,
            public_id=quote_document_public_id,
            commercial_offer_id=commercial_offer_id,
            values=values,
        )

        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_QUOTE_DOCUMENT_GENERATED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_QUOTE_DOCUMENT_RECORD_TYPE,
            record_public_id=quote_document_public_id,
            user_public_id=current_user_public_id,
            status_after=COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT,
            reason=f"Quotation document {quote_reference} generated.",
            event_payload={
                "offer_code": offer_code,
                "version_no": version_no,
                "quote_reference": quote_reference,
                "source_fingerprint": fingerprint,
                "document_public_id": document_row["document_public_id"],
                "byte_size": document_row.get("byte_size"),
                # Never the rendered document itself, never its content - metadata only.
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        # One shared compensation path with documents.upload_document - see
        # documents.service.delete_stored_document_object for why this cannot live inside
        # _persist_stored_document alone.
        delete_stored_document_object(document_row)
        raise

    return CommercialOfferQuoteDocumentGeneratedResponse(
        quote_document=_quote_document_row_to_response(
            row,
            offer_status_code=offer_status_code,
            snapshot=snapshot,
            current_fingerprint=fingerprint,
        ),
        event=_event_dict(event),
    )


def list_commercial_offer_quote_documents(
    db: Session, public_id: UUID
) -> list[CommercialOfferQuoteDocumentResponse]:
    # The offer, its versions and the snapshot are all read in ONE single-instant transaction, so
    # every row's is_stale and approval_blocked_reason describe the same real state of the offer:
    # one snapshot and one fingerprint for the whole list, not one per row (independent review,
    # round 3).
    with single_instant_read_session(db) as read_db:
        commercial_offer_context = get_commercial_offer_context_by_public_id(read_db, str(public_id))
        if commercial_offer_context is None:
            raise CommercialOfferNotFoundError("Commercial Offer not found.")

        commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])
        rows = list_commercial_offer_quote_documents_for_offer(read_db, commercial_offer_id=commercial_offer_id)
        if not rows:
            return []

        snapshot = build_quote_snapshot(read_db, commercial_offer_id=commercial_offer_id)
    current_fingerprint = compute_source_fingerprint(snapshot)
    offer_status_code = commercial_offer_context["offer_status_code"]
    return [
        _quote_document_row_to_response(
            row,
            offer_status_code=offer_status_code,
            snapshot=snapshot,
            current_fingerprint=current_fingerprint,
        )
        for row in rows
    ]


def approve_commercial_offer_quote_document(
    db: Session,
    *,
    public_id: UUID,
    quote_document_public_id: UUID,
    payload: CommercialOfferQuoteDocumentApproveRequest | None,
    current_user_public_id: str | None,
) -> CommercialOfferQuoteDocumentApprovedResponse:
    """Owner decision 3: a one-step attested issue gate. Records who approved this specific
    version and when; does not itself control who may download it - see
    docs/agent/slices/slice-9e-quotation-generation.md, "Decision 3, and what the gate does and
    does not do".

    TWO row locks, taken in this order: the parent Commercial Offer first, then the quotation
    row. The order matters and must not be swapped - generation also locks the offer first and
    then touches quotation rows through supersede_earlier_quote_documents, so taking them in the
    same order here is what keeps the two paths from deadlocking against each other.

    The offer lock exists because of the owner decision of 9 September 2026 that a quotation may
    not be approved for issue once the offer has concluded: that turns approval into a
    read-then-write against offer_status_code, the exact shape the Slice 9B contract requires a
    lock for. Without it, approval could read a live status and commit an authorisation to issue
    a quotation for an offer rejected in the same instant.

    Every refusal reason comes from quote_document_approval_blocked_reason, which also fills the
    listing's approval_blocked_reason. That includes the pricing and staleness preconditions
    added by the UI cleanup package (owner decisions of 9 and 11 September 2026): an unpriced
    active line, or a version the offer has changed since, cannot be approved for issue.

    The staleness check is taken at one instant: build_quote_snapshot_at_one_instant reads the
    whole snapshot in one read-only REPEATABLE READ transaction, opened here after both locks are
    held. Line, T&C clause and Account writers do not take the offer lock, so a change that commits
    after that instant leaves the version stale a moment later, just as a change committed a minute
    after approval does; either way the approved document itself is fully priced. What approval
    can no longer do is pass a version against parts read at different moments - a combination the
    offer never had (independent review, round 2). The Commercial Offer contract's Slice 9E section
    records why those writers are not serialized against approval.
    """
    if lock_commercial_offer_row(db, public_id=str(public_id)) is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])

    offer_status_code = commercial_offer_context["offer_status_code"]

    # A distinct row from the parent Commercial Offer, so lock_commercial_offer_row does not
    # cover it - a separate lock is required, not a reuse. See
    # lock_commercial_offer_quote_document_row's docstring for the race this closes.
    if lock_commercial_offer_quote_document_row(db, public_id=str(quote_document_public_id)) is None:
        raise CommercialOfferQuoteDocumentNotFoundError("Quotation document not found.")

    existing = get_quote_document_row_by_public_id(
        db,
        commercial_offer_id=commercial_offer_id,
        public_id=str(quote_document_public_id),
    )
    if existing is None:
        raise CommercialOfferQuoteDocumentNotFoundError(
            "Quotation document not found for this Commercial Offer."
        )

    # One snapshot, read while both rows are locked, decides the approval and builds the
    # response. Approval itself changes no snapshot data, so reusing it afterwards is exact.
    snapshot = build_quote_snapshot_at_one_instant(db, commercial_offer_id=commercial_offer_id)
    current_fingerprint = compute_source_fingerprint(snapshot)
    blocked_reason = quote_document_approval_blocked_reason(
        offer_status_code=offer_status_code,
        row=existing,
        snapshot=snapshot,
        current_fingerprint=current_fingerprint,
    )
    if blocked_reason is not None:
        raise CommercialOfferValidationError(blocked_reason)

    approval_note = _clean_optional(payload.approval_note) if payload is not None else None

    try:
        mark_quote_document_approved_for_issue(
            db,
            quote_document_public_id=str(quote_document_public_id),
            approved_by=current_user_public_id,
            approval_note=approval_note,
        )
        updated_row = get_quote_document_row_by_public_id(
            db,
            commercial_offer_id=commercial_offer_id,
            public_id=str(quote_document_public_id),
        )
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_QUOTE_DOCUMENT_APPROVED_FOR_ISSUE,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_QUOTE_DOCUMENT_RECORD_TYPE,
            record_public_id=str(quote_document_public_id),
            user_public_id=current_user_public_id,
            status_before=COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT,
            status_after=COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_APPROVED_FOR_ISSUE,
            reason=f"Quotation document {existing['quote_reference']} approved for issue.",
            remarks=approval_note,
            event_payload={
                "offer_code": commercial_offer_context["offer_code"],
                "version_no": existing["version_no"],
                "quote_reference": existing["quote_reference"],
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return CommercialOfferQuoteDocumentApprovedResponse(
        quote_document=_quote_document_row_to_response(
            updated_row,
            offer_status_code=offer_status_code,
            snapshot=snapshot,
            current_fingerprint=current_fingerprint,
        ),
        event=_event_dict(event),
    )
