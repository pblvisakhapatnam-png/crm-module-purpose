from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_INITIAL_PURPOSE,
    COMMERCIAL_OFFER_INITIAL_STATUS,
    COMMERCIAL_OFFER_MODE_PLUM_GENERATED,
    COMMERCIAL_OFFER_TYPE_BUDGETARY,
)
from app.shared.zoned_datetime import ZonedDateTime


class CommercialOfferCreate(BaseModel):
    opportunity_public_id: UUID
    offer_title: str | None = Field(default=None, max_length=255)
    offer_mode: str = Field(default=COMMERCIAL_OFFER_MODE_PLUM_GENERATED, max_length=50)
    offer_type: str = Field(default=COMMERCIAL_OFFER_TYPE_BUDGETARY, max_length=50)
    offer_status_code: str = Field(default=COMMERCIAL_OFFER_INITIAL_STATUS, max_length=50)
    offer_value: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    currency_code: str = Field(default="INR", min_length=3, max_length=3)
    offer_date: date | None = None
    valid_until: date | None = None
    remarks: str | None = Field(default=None, max_length=4000)


class CommercialOfferUpdate(BaseModel):
    """A change to the offer's own details. `expected_row_version` is the `row_version` the screen loaded: a save
    against any other is refused with 409, so a stale form cannot overwrite someone else's save (CS-05a). Send only
    the fields being changed; a field left out keeps what is recorded."""

    expected_row_version: int = Field(ge=1)
    offer_title: str | None = Field(default=None, max_length=255)
    offer_mode: str | None = Field(default=None, max_length=50)
    offer_type: str | None = Field(default=None, max_length=50)
    offer_status_code: str | None = Field(default=None, max_length=50)
    offer_value: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    offer_date: date | None = None
    valid_until: date | None = None
    submitted_at: ZonedDateTime | None = None
    submission_reference: str | None = Field(default=None, max_length=255)
    submission_proof_note: str | None = Field(default=None, max_length=4000)
    outcome_date: date | None = None
    outcome_remarks: str | None = Field(default=None, max_length=4000)
    remarks: str | None = Field(default=None, max_length=4000)


class CommercialOfferResponse(BaseModel):
    public_id: UUID
    offer_code: str
    opportunity_public_id: UUID
    account_public_id: UUID | None = None
    offer_title: str | None = None
    offer_mode: str
    offer_type: str
    offer_status_code: str
    offer_value: Decimal | None = None
    currency_code: str
    offer_date: date | None = None
    valid_until: date | None = None
    submitted_at: datetime | None = None
    submission_reference: str | None = None
    submission_proof_note: str | None = None
    outcome_date: date | None = None
    outcome_remarks: str | None = None
    remarks: str | None = None
    offer_purpose: str = COMMERCIAL_OFFER_INITIAL_PURPOSE
    base_offer_public_id: UUID | None = None
    base_offer_code: str | None = None
    related_work_order_public_id: UUID | None = None
    related_work_order_code: str | None = None
    customer_request_reference: str | None = None
    customer_request_received_date: date | None = None
    customer_request_summary: str | None = None
    version_number: int = 1
    previous_version_offer_public_id: UUID | None = None
    version_reason: str | None = None
    version_note: str | None = None
    replaced_by_offer_public_id: UUID | None = None
    replaced_by_version_number: int | None = None
    created_by: UUID | None = None
    # Read-only, resolved from app_user.display_name; None when created_by is null or matches no
    # user (UI cleanup package, September 2026).
    created_by_display_name: str | None = None
    created_at: datetime
    updated_at: datetime
    # CS-05a: 1 when made, raised by every write of the offer's row; an edit sends back the one it loaded.
    row_version: int


class CommercialOfferCreatedResponse(BaseModel):
    commercial_offer: CommercialOfferResponse
    event: dict[str, Any]


class CommercialOfferRelatedOfferCreate(BaseModel):
    offer_purpose: str = Field(max_length=50)
    related_work_order_public_id: UUID | None = None
    customer_request_reference: str | None = Field(default=None, max_length=255)
    customer_request_received_date: date | None = None
    customer_request_summary: str = Field(max_length=2000)
    offer_title: str | None = Field(default=None, max_length=255)
    offer_mode: str = Field(default=COMMERCIAL_OFFER_MODE_PLUM_GENERATED, max_length=50)
    offer_type: str = Field(default=COMMERCIAL_OFFER_TYPE_BUDGETARY, max_length=50)
    offer_value: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    currency_code: str = Field(default="INR", min_length=3, max_length=3)
    offer_date: date | None = None
    valid_until: date | None = None
    remarks: str | None = Field(default=None, max_length=4000)


class CommercialOfferRelatedOfferCreatedResponse(BaseModel):
    commercial_offer: CommercialOfferResponse
    event: dict[str, Any]


class CommercialOfferUpdatedResponse(BaseModel):
    commercial_offer: CommercialOfferResponse
    events: list[dict[str, Any]]


class CommercialOfferMarkedSubmittedResponse(BaseModel):
    commercial_offer: CommercialOfferResponse
    event: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


class CommercialOfferVersionCreate(BaseModel):
    version_reason: str = Field(max_length=50)
    version_note: str | None = Field(default=None, max_length=4000)


class CommercialOfferVersionActionResponse(BaseModel):
    commercial_offer: CommercialOfferResponse
    event: dict[str, Any]


class CommercialOfferPricingEvidenceCreate(BaseModel):
    """A market or historical rate for one line of the offer (Slice 4G). `line_public_id` names an active line of the
    same offer; `quote_copy_rate_public_id` names another rate of the offer whose attached document also holds this
    rate's quote."""

    line_public_id: UUID
    quote_copy_rate_public_id: UUID | None = None
    evidence_type: str = Field(default="market_rate", max_length=50)
    source_name: str | None = Field(default=None, max_length=255)
    vendor_contact: str | None = Field(default=None, max_length=255)
    equipment_service_description: str = Field(min_length=1, max_length=1000)
    rate_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    currency_code: str = Field(default="INR", min_length=3, max_length=3)
    rate_basis: str = Field(min_length=1, max_length=100)
    collected_by_name: str | None = Field(default=None, max_length=255)
    collected_at: ZonedDateTime | None = None
    source_reference: str | None = Field(default=None, max_length=255)
    is_selected_basis: bool = False
    selection_reason: str | None = Field(default=None, max_length=1000)
    comparison_notes: str | None = Field(default=None, max_length=2000)


class CommercialOfferPricingEvidenceBasisSelection(BaseModel):
    """Choosing a rate as its line's basis needs a reason (Slice 4G); a blank one is refused by the service."""

    selection_reason: str = Field(max_length=1000)


class CommercialOfferMarketRateQuoteCopy(BaseModel):
    """A document holding a rate's quote: attached to the rate itself, or to the rate it refers to (Slice 4G)."""

    document_public_id: UUID
    file_name: str
    uploaded_at: str | None = None
    attached_to_rate_public_id: UUID
    attached_to_line_number: int | None = None
    attached_to_offer_version_number: int
    attached_here: bool


class CommercialOfferLineBasisChoiceResponse(BaseModel):
    """One choice of a rate as its line's basis (Slice 4G). `ended_at` is empty while it is the current choice."""

    public_id: UUID
    pricing_evidence_public_id: UUID
    selection_reason: str
    chosen_by: UUID | None = None
    chosen_by_display_name: str | None = None
    chosen_at: datetime
    ended_by: UUID | None = None
    ended_by_display_name: str | None = None
    ended_at: datetime | None = None
    is_current: bool
    carried_over_from_version_number: int | None = None


class CommercialOfferPricingEvidenceResponse(BaseModel):
    public_id: UUID
    commercial_offer_public_id: UUID
    line_public_id: UUID | None = None
    line_number: int | None = None
    line_status_code: str | None = None
    recorded_for_whole_offer: bool = False
    quote_copy_rate_public_id: UUID | None = None
    quote_copies: list[CommercialOfferMarketRateQuoteCopy] = Field(default_factory=list)
    basis_history: list[CommercialOfferLineBasisChoiceResponse] = Field(default_factory=list)
    evidence_type: str
    source_name: str | None = None
    vendor_contact: str | None = None
    equipment_service_description: str
    rate_amount: Decimal
    currency_code: str
    rate_basis: str
    collected_by_name: str | None = None
    collected_at: datetime | None = None
    source_reference: str | None = None
    is_selected_basis: bool
    selection_reason: str | None = None
    comparison_notes: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class CommercialOfferPricingEvidenceCreatedResponse(BaseModel):
    pricing_evidence: CommercialOfferPricingEvidenceResponse
    events: list[dict[str, Any]]


class CommercialOfferPricingEvidenceSelectedResponse(BaseModel):
    pricing_evidence: CommercialOfferPricingEvidenceResponse
    previous_basis_rate_public_id: UUID | None = None
    event: dict[str, Any]


class CommercialOfferLineCreate(BaseModel):
    line_number: int | None = Field(default=None, ge=1)
    scope_description: str = Field(min_length=1, max_length=1000)
    equipment_service_category: str | None = Field(default=None, max_length=255)
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0, max_digits=18, decimal_places=2)
    uom: str = Field(default="unit", min_length=1, max_length=50)
    rate_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    currency_code: str = Field(default="INR", min_length=3, max_length=3)
    remarks: str | None = Field(default=None, max_length=2000)


class CommercialOfferLineUpdate(BaseModel):
    """A change to one offer line. `expected_row_version` is the line's `row_version` the screen loaded: a save
    against any other is refused with 409 (CS-05a). Send only the fields being changed."""

    expected_row_version: int = Field(ge=1)
    line_number: int | None = Field(default=None, ge=1)
    line_status_code: str | None = Field(default=None, max_length=50)
    scope_description: str | None = Field(default=None, min_length=1, max_length=1000)
    equipment_service_category: str | None = Field(default=None, max_length=255)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    uom: str | None = Field(default=None, min_length=1, max_length=50)
    rate_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    remarks: str | None = Field(default=None, max_length=2000)


class CommercialOfferLineResponse(BaseModel):
    public_id: UUID
    commercial_offer_public_id: UUID
    line_number: int
    line_status_code: str
    scope_description: str
    equipment_service_category: str | None = None
    quantity: Decimal
    uom: str
    rate_amount: Decimal | None = None
    currency_code: str
    line_amount: Decimal | None = None
    remarks: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    # CS-05a: 1 when made, raised by every write of the line's row; an edit sends back the one it loaded.
    row_version: int


class CommercialOfferLineCreatedResponse(BaseModel):
    offer_line: CommercialOfferLineResponse
    event: dict[str, Any]


class CommercialOfferLineUpdatedResponse(BaseModel):
    offer_line: CommercialOfferLineResponse
    event: dict[str, Any]


class CommercialOfferTcClauseAttachRequest(BaseModel):
    clause_public_ids: list[UUID] = Field(min_length=1, max_length=50)


class CommercialOfferTcClauseAttachRecommendedRequest(BaseModel):
    recommendation_basis: str | None = Field(default=None, max_length=50)
    business_line: str | None = Field(default=None, max_length=50)


class CommercialOfferTcClauseResponse(BaseModel):
    public_id: UUID
    commercial_offer_public_id: UUID
    tc_clause_public_id: UUID
    clause_id_snapshot: str
    title_snapshot: str
    clause_text_snapshot: str
    business_line_snapshot: str
    clause_category_snapshot: str
    source_clause_number_snapshot: str | None = None
    source_reference_snapshot: str | None = None
    mandatory_default_snapshot: bool
    risk_category_snapshot: str | None = None
    applies_to_header_snapshot: bool
    applies_to_line_snapshot: bool
    requires_approval_if_omitted_snapshot: bool
    requires_approval_if_modified_snapshot: bool
    sort_order: int
    active: bool
    attached_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class CommercialOfferTcClauseAttachedResponse(BaseModel):
    tc_clauses: list[CommercialOfferTcClauseResponse]
    events: list[dict[str, Any]]


class CommercialOfferTcClauseReadinessClauseResponse(BaseModel):
    tc_clause_public_id: UUID
    clause_id: str
    title: str
    clause_text: str
    business_line: str
    clause_category: str
    source_clause_number: str | None = None
    mandatory_default: bool
    risk_category: str | None = None
    applies_to_header: bool
    applies_to_line: bool
    requires_approval_if_omitted: bool
    requires_approval_if_modified: bool
    active: bool
    source_reference: str | None = None
    status: str
    attachment_public_id: UUID | None = None


class CommercialOfferTcClauseReadinessResponse(BaseModel):
    commercial_offer_public_id: UUID
    recommendation_basis: str | None = None
    total_recommended_count: int
    attached_recommended_count: int
    missing_recommended_count: int
    attached_optional_count: int
    status_text: str
    deferral_notes: list[str]
    recommended_clauses: list[CommercialOfferTcClauseReadinessClauseResponse]


class CommercialOfferTcClauseAttachRecommendedResponse(BaseModel):
    readiness: CommercialOfferTcClauseReadinessResponse
    tc_clauses: list[CommercialOfferTcClauseResponse]
    events: list[dict[str, Any]]
    attached_count: int
    status_text: str


class CommercialOfferSubmissionEvidenceCreate(BaseModel):
    submission_reference: str | None = Field(default=None, max_length=255)
    submission_channel: str = Field(max_length=50)
    submitted_at: ZonedDateTime
    recipient_summary: str | None = Field(default=None, max_length=1000)
    submitted_version_snapshot: str | None = Field(default=None, max_length=50)
    document_reference_label: str | None = Field(default=None, max_length=255)
    document_reference_url_or_path: str | None = Field(default=None, max_length=1000)
    evidence_notes: str | None = Field(default=None, max_length=4000)


class CommercialOfferSubmissionEvidenceResponse(BaseModel):
    public_id: UUID
    commercial_offer_public_id: UUID
    submission_reference: str | None = None
    submission_channel: str
    submitted_at: datetime
    submitted_by: UUID | None = None
    recipient_summary: str | None = None
    submitted_amount_snapshot: Decimal | None = None
    submitted_currency_snapshot: str | None = None
    submitted_version_snapshot: str | None = None
    document_reference_label: str | None = None
    document_reference_url_or_path: str | None = None
    evidence_notes: str | None = None
    active: bool
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class CommercialOfferSubmissionEvidenceCreatedResponse(BaseModel):
    submission_evidence: CommercialOfferSubmissionEvidenceResponse
    event: dict[str, Any]


class CommercialOfferCreditReviewCreate(BaseModel):
    review_status: str = Field(max_length=50)
    review_basis: str | None = Field(default=None, max_length=255)
    review_reference: str | None = Field(default=None, max_length=255)
    reviewed_at: ZonedDateTime
    approved_amount_snapshot: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    credit_days_snapshot: int | None = Field(default=None, ge=0, le=3650)
    exposure_note: str | None = Field(default=None, max_length=4000)


class CommercialOfferCreditReviewResponse(BaseModel):
    public_id: UUID
    commercial_offer_public_id: UUID
    review_status: str
    review_basis: str | None = None
    review_reference: str | None = None
    reviewed_at: datetime
    reviewed_by: UUID | None = None
    approved_amount_snapshot: Decimal | None = None
    credit_days_snapshot: int | None = None
    exposure_note: str | None = None
    active: bool
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class CommercialOfferCreditReviewCreatedResponse(BaseModel):
    credit_review: CommercialOfferCreditReviewResponse
    event: dict[str, Any]


class CommercialOfferRevisionCreate(BaseModel):
    revision_label: str | None = Field(default=None, max_length=100)
    revision_reason: str = Field(max_length=50)
    revision_notes: str | None = Field(default=None, max_length=4000)
    source_submission_evidence_public_id: UUID | None = None
    opened_at: ZonedDateTime | None = None


class CommercialOfferRevisionMarkResubmitted(BaseModel):
    resubmission_evidence_public_id: UUID


class CommercialOfferRevisionResponse(BaseModel):
    public_id: UUID
    commercial_offer_public_id: UUID
    revision_label: str
    revision_reason: str
    revision_notes: str | None = None
    revision_status: str
    source_submission_evidence_public_id: UUID | None = None
    resubmission_evidence_public_id: UUID | None = None
    opened_at: datetime
    opened_by: UUID | None = None
    resubmitted_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class CommercialOfferRevisionActionResponse(BaseModel):
    revision: CommercialOfferRevisionResponse
    event: dict[str, Any]


class CommercialOfferCustomerResponseCreate(BaseModel):
    response_outcome: str = Field(max_length=50)
    response_reference: str | None = Field(default=None, max_length=255)
    response_received_at: ZonedDateTime
    response_channel: str = Field(max_length=50)
    received_from: str | None = Field(default=None, max_length=255)
    awarded_amount_snapshot: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    awarded_currency_snapshot: str | None = Field(default=None, min_length=3, max_length=3)
    awarded_version_snapshot: str | None = Field(default=None, max_length=100)
    customer_po_or_wo_reference: str | None = Field(default=None, max_length=255)
    customer_response_notes: str | None = Field(default=None, max_length=4000)
    linked_submission_evidence_public_id: UUID | None = None
    linked_revision_public_id: UUID | None = None


class CommercialOfferCustomerResponseResponse(BaseModel):
    public_id: UUID
    commercial_offer_public_id: UUID
    response_outcome: str
    response_reference: str | None = None
    response_received_at: datetime
    response_channel: str
    received_from: str | None = None
    awarded_amount_snapshot: Decimal | None = None
    awarded_currency_snapshot: str | None = None
    awarded_version_snapshot: str | None = None
    customer_po_or_wo_reference: str | None = None
    customer_response_notes: str | None = None
    linked_submission_evidence_public_id: UUID | None = None
    linked_revision_public_id: UUID | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class CommercialOfferCustomerResponseCreatedResponse(BaseModel):
    customer_response: CommercialOfferCustomerResponseResponse
    commercial_offer: CommercialOfferResponse
    event: dict[str, Any]


class CommercialOfferSubmissionReadinessItemResponse(BaseModel):
    code: str
    label: str
    status: str
    severity: str
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    deferred: bool = False


class CommercialOfferSubmissionReadinessSummaryResponse(BaseModel):
    passed_count: int
    warning_count: int
    blocking_count: int
    deferred_count: int


class CommercialOfferSubmissionReadinessResponse(BaseModel):
    commercial_offer_public_id: UUID
    readiness_status: str
    summary: CommercialOfferSubmissionReadinessSummaryResponse
    checklist_items: list[CommercialOfferSubmissionReadinessItemResponse]


class CommercialOfferTcClauseRemovedResponse(BaseModel):
    tc_clause: CommercialOfferTcClauseResponse
    event: dict[str, Any]


class CommercialOfferLinkedWorkOrderSummary(BaseModel):
    public_id: UUID
    work_order_code: str
    work_order_status_code: str


class CommercialOfferLineHandoffWorkOrder(BaseModel):
    """One Work Order line holding part or all of an offer line (CS-04 part 1)."""

    work_order_public_id: UUID
    work_order_code: str | None = None
    quantity: Decimal


class CommercialOfferLineHandoff(BaseModel):
    """An active offer line's quantity, how much of it Work Orders hold, and what is left to hand off (CS-04 part 1:
    an offer line's quantity goes onto Work Orders once, whole or in parts). Counted in one statement on the server, so
    the Create Work Order page does no arithmetic of its own beyond checking what is typed against `quantity_left`."""

    offer_line_public_id: UUID
    line_number: int
    quantity: Decimal
    quantity_on_work_orders: Decimal
    quantity_left: Decimal
    work_orders: list[CommercialOfferLineHandoffWorkOrder] = Field(default_factory=list)


class CommercialOfferLifecycleGuidanceResponse(BaseModel):
    commercial_offer_public_id: UUID
    offer_status_code: str
    latest_customer_response_outcome: str | None = None
    latest_customer_response_public_id: UUID | None = None
    latest_customer_response_received_at: datetime | None = None
    lifecycle_state: str
    lifecycle_state_label: str
    is_commercially_active: bool
    advisory_message: str
    recommended_next_action: str
    can_open_revision: bool
    can_make_new_version: bool
    has_open_revision_awaiting_resubmission: bool
    can_record_customer_response: bool
    work_order_handoff_available: bool
    work_order_handoff_blocked_reasons: list[str] = Field(default_factory=list)
    linked_work_orders: list[CommercialOfferLinkedWorkOrderSummary] = Field(default_factory=list)
    line_handoff: list[CommercialOfferLineHandoff] = Field(default_factory=list)


# --- Slice 9E: Quotation Generation ------------------------------------------------------------


class CommercialOfferQuoteDocumentResponse(BaseModel):
    public_id: UUID
    commercial_offer_public_id: UUID
    version_no: int
    quote_reference: str
    document_public_id: UUID
    quote_status_code: str
    generated_by: UUID | None = None
    # Resolved for display so the normal application can show WHO prepared and approved a
    # version, not only an opaque identifier. None where the actor no longer resolves (for
    # example a removed user); the version still lists (independent review, correction pass 1,
    # finding 4).
    generated_by_display_name: str | None = None
    generated_at: datetime
    approved_by: UUID | None = None
    approved_by_display_name: str | None = None
    approved_at: datetime | None = None
    approval_note: str | None = None
    superseded_at: datetime | None = None
    # NOT a stored column. Computed at read time by comparing this version's stored
    # source_fingerprint against a freshly recomputed one - see
    # docs/agent/slices/slice-9e-quotation-generation.md, "Snapshot and staleness". Advisory
    # only: the stored bytes are immutable regardless of this flag's value.
    is_stale: bool
    # NOT a stored column. Why this version could not be approved for issue in the state this
    # response was read from, or None when an approval would then succeed for a caller holding
    # COMMERCIAL_OFFER_QUOTE_APPROVE. Produced by the same function the approval precondition
    # uses. Advisory for the Approve button: approval re-checks under its locks, so a change made
    # after this response can still be refused (UI cleanup package, September 2026).
    approval_blocked_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class CommercialOfferQuoteDocumentGeneratedResponse(BaseModel):
    quote_document: CommercialOfferQuoteDocumentResponse
    event: dict[str, Any]


class CommercialOfferQuoteDocumentApproveRequest(BaseModel):
    approval_note: str | None = Field(default=None, max_length=1000)


class CommercialOfferQuoteDocumentApprovedResponse(BaseModel):
    quote_document: CommercialOfferQuoteDocumentResponse
    event: dict[str, Any]
