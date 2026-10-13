"""Commercial Offer / Quote contract constants.

Slice 4A establishes Commercial Offer as its own foundation object linked to
Opportunity. The UI may use Commercial Offer and Quote together, but the API
route and record type use commercial-offer terminology to preserve a single
object for Plum-generated quotes and external/tender commercial responses.
"""

COMMERCIAL_OFFER_MODULE_NAME = "commercial_offers"
COMMERCIAL_OFFER_TABLE = "crm_commercial_offer"
COMMERCIAL_OFFER_RECORD_TYPE = "commercial_offer"
COMMERCIAL_OFFER_WORKFLOW_MODULE = "commercial_offer"

COMMERCIAL_OFFER_MODE_PLUM_GENERATED = "plum_generated"
COMMERCIAL_OFFER_MODE_EXTERNAL_TENDER = "external_tender"
COMMERCIAL_OFFER_MODE_CUSTOMER_FORMAT = "customer_format"
COMMERCIAL_OFFER_MODE_BUDGETARY_RESPONSE = "budgetary_response"
COMMERCIAL_OFFER_MODE_OTHER = "other"

COMMERCIAL_OFFER_ALLOWED_MODES = (
    COMMERCIAL_OFFER_MODE_PLUM_GENERATED,
    COMMERCIAL_OFFER_MODE_EXTERNAL_TENDER,
    COMMERCIAL_OFFER_MODE_CUSTOMER_FORMAT,
    COMMERCIAL_OFFER_MODE_BUDGETARY_RESPONSE,
    COMMERCIAL_OFFER_MODE_OTHER,
)

COMMERCIAL_OFFER_TYPE_BUDGETARY = "budgetary"
COMMERCIAL_OFFER_TYPE_FIRM = "firm"
COMMERCIAL_OFFER_TYPE_TENDER_RESPONSE = "tender_response"
COMMERCIAL_OFFER_TYPE_REVISION = "revision"
COMMERCIAL_OFFER_TYPE_OTHER = "other"

COMMERCIAL_OFFER_ALLOWED_TYPES = (
    COMMERCIAL_OFFER_TYPE_BUDGETARY,
    COMMERCIAL_OFFER_TYPE_FIRM,
    COMMERCIAL_OFFER_TYPE_TENDER_RESPONSE,
    COMMERCIAL_OFFER_TYPE_REVISION,
    COMMERCIAL_OFFER_TYPE_OTHER,
)

COMMERCIAL_OFFER_STATUS_DRAFT = "DRAFT"
COMMERCIAL_OFFER_STATUS_READY_FOR_REVIEW = "READY_FOR_REVIEW"
COMMERCIAL_OFFER_STATUS_SUBMITTED = "SUBMITTED"
COMMERCIAL_OFFER_STATUS_REVISED = "REVISED"
COMMERCIAL_OFFER_STATUS_ABANDONED = "ABANDONED"
COMMERCIAL_OFFER_STATUS_WITHDRAWN = "WITHDRAWN"
COMMERCIAL_OFFER_STATUS_ACCEPTED = "ACCEPTED"
COMMERCIAL_OFFER_STATUS_REJECTED = "REJECTED"
COMMERCIAL_OFFER_STATUS_CLOSED = "CLOSED"

COMMERCIAL_OFFER_INITIAL_STATUS = COMMERCIAL_OFFER_STATUS_DRAFT

# Slice 4A creates foundation records only. Submission, approval, award and
# closure transitions are deliberately deferred.
COMMERCIAL_OFFER_CREATE_ALLOWED_STATUSES = (COMMERCIAL_OFFER_STATUS_DRAFT,)

# Slice 4F introduced thin lifecycle closure movement. Later slices added document generation
# and immutable versions without changing which statuses the general update route accepts.
COMMERCIAL_OFFER_STATUS_UPDATE_ALLOWED_STATUSES = (
    COMMERCIAL_OFFER_STATUS_DRAFT,
    COMMERCIAL_OFFER_STATUS_READY_FOR_REVIEW,
    COMMERCIAL_OFFER_STATUS_SUBMITTED,
    COMMERCIAL_OFFER_STATUS_WITHDRAWN,
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
    COMMERCIAL_OFFER_STATUS_REJECTED,
    COMMERCIAL_OFFER_STATUS_CLOSED,
)

# Slice 6M.1 controlled terminal status transition guard for the general update route
# (PUT /api/commercial-offers/{id}). Two distinct concepts are tracked separately because
# they do not share the same membership - do not collapse them into one constant:
#
# 1. COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES - once the offer's *current*
#    status is one of these, the general update route must not change it to any other
#    status. ACCEPTED, WITHDRAWN, REJECTED and CLOSED are all final from this route's
#    point of view. (fa09489 originally covered WITHDRAWN/REJECTED/CLOSED only; the 6M.1
#    completion adds ACCEPTED so an already-accepted offer cannot be silently reopened
#    through general update either.)
# 2. COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES - the general update route must
#    never set offer_status_code to one of these values, regardless of the offer's current
#    status. ACCEPTED and REJECTED may only be established through the dedicated Slice 6L
#    customer-response action (ACCEPTED_AWARDED / REJECTED_LOST), which records response
#    evidence and writes offer_status_code through the repository layer directly, bypassing
#    this guard by design. WITHDRAWN and CLOSED are NOT in this set: they remain legitimately
#    settable through general update, unchanged from Slice 4C/4F.
#
# Same-status payloads (target == current) are never a "transition" under either rule, so
# resubmitting the current status (optionally alongside other field edits) remains allowed.
COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES = (
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
    COMMERCIAL_OFFER_STATUS_WITHDRAWN,
    COMMERCIAL_OFFER_STATUS_REJECTED,
    COMMERCIAL_OFFER_STATUS_CLOSED,
    COMMERCIAL_OFFER_STATUS_REVISED,
    COMMERCIAL_OFFER_STATUS_ABANDONED,
)

COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES = (
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
    COMMERCIAL_OFFER_STATUS_REJECTED,
)

# 3. A SUBMITTED offer is commercially committed, so the general update route must not move it
#    back to one of these pre-submission statuses (TB-1 finding TB1-301, 4 October 2026). It may
#    still be withdrawn or closed, and ACCEPTED/REJECTED still come only from a customer response.
#    SUBMITTED is deliberately not cannot-leave: the reports module derives "open" offers from
#    that set, and a submitted offer is open.
COMMERCIAL_OFFER_PRE_SUBMISSION_STATUSES = (
    COMMERCIAL_OFFER_STATUS_DRAFT,
    COMMERCIAL_OFFER_STATUS_READY_FOR_REVIEW,
)

# Slice 6B.1 keeps only one active/actionable sent Base Offer per Opportunity. Slice 9F makes a
# Draft/Ready later version an explicit exception: it is preparation for the same series, not a second actionable
# offer. A new unrelated offer may still be created only after the previous series is clearly inactive/final.
# This is intentionally its own independent tuple, not an alias of the general-update
# "cannot leave" set above: ACCEPTED is final for general update (Slice 6M.1) but is
# still active/actionable for the Slice 6B.1 one-offer-per-Opportunity rule, so it must
# NOT appear here.
COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES = (
    COMMERCIAL_OFFER_STATUS_WITHDRAWN,
    COMMERCIAL_OFFER_STATUS_REJECTED,
    COMMERCIAL_OFFER_STATUS_CLOSED,
    COMMERCIAL_OFFER_STATUS_REVISED,
    COMMERCIAL_OFFER_STATUS_ABANDONED,
)

COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES = (
    COMMERCIAL_OFFER_STATUS_DRAFT,
    COMMERCIAL_OFFER_STATUS_READY_FOR_REVIEW,
)

COMMERCIAL_OFFER_VERSION_HISTORY_STATUSES = (
    COMMERCIAL_OFFER_STATUS_REVISED,
    COMMERCIAL_OFFER_STATUS_ABANDONED,
)

# A version counts as sent from its controlled lifecycle status, not from editable header metadata.
# Legacy sent rows can have incomplete submitted_at data, while a preparation row must never become
# commercially effective merely because somebody supplied a date through general update.
COMMERCIAL_OFFER_VERSION_UNSENT_STATUSES = (
    *COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES,
    COMMERCIAL_OFFER_STATUS_ABANDONED,
)

# The database rules that refuse a duplicate two requests made at once (TB-1 finding TB1-304; CS-05c). Each command
# checks first under the offer's row lock - or, for a new Base Offer, the Opportunity's - so these are the backstop;
# the module answers them with its own message, never a server error. The first is migration 20260908_0053's partial
# unique index over the status rule above plus Slice 9F's preparation-version exception.
COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX = "ux_crm_commercial_offer_one_active_base_per_opportunity"
COMMERCIAL_OFFER_CODE_VERSION_INDEX = "ux_crm_commercial_offer_code_version_not_null"
# Slice 4G (migration 20260908_0055): a line's basis rate is its one open choice in the line's basis history.
COMMERCIAL_OFFER_ONE_OPEN_BASIS_CHOICE_INDEX = "ux_crm_commercial_offer_line_basis_choice_one_open"
COMMERCIAL_OFFER_ACTIVE_TC_CLAUSE_INDEX = "uq_commercial_offer_tc_clause_active_clause"
COMMERCIAL_OFFER_CURRENT_CREDIT_REVIEW_INDEX = "ux_commercial_offer_credit_review_current"

COMMERCIAL_OFFER_EVENT_CREATED = "CommercialOfferCreated"
COMMERCIAL_OFFER_EVENT_UPDATED = "CommercialOfferUpdated"
COMMERCIAL_OFFER_EVENT_STATUS_CHANGED = "CommercialOfferStatusChanged"
COMMERCIAL_OFFER_EVENT_SUBMITTED = "CommercialOfferSubmitted"
COMMERCIAL_OFFER_EVENT_COMMERCIALLY_COMMITTED = "CommercialOfferCommerciallyCommitted"
COMMERCIAL_OFFER_EVENT_ACCEPTED = "CommercialOfferAccepted"
COMMERCIAL_OFFER_EVENT_REJECTED = "CommercialOfferRejected"
COMMERCIAL_OFFER_EVENT_WITHDRAWN = "CommercialOfferWithdrawn"
COMMERCIAL_OFFER_EVENT_CLOSED = "CommercialOfferClosed"
COMMERCIAL_OFFER_EVENT_VERSION_CREATED = "CommercialOfferVersionCreated"
COMMERCIAL_OFFER_EVENT_VERSION_ABANDONED = "CommercialOfferVersionAbandoned"
COMMERCIAL_OFFER_EVENT_VERSION_REPLACED = "CommercialOfferVersionReplaced"


# Slice 4D pricing evidence foundation.
COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE = "crm_commercial_offer_pricing_evidence"
COMMERCIAL_OFFER_LINE_BASIS_CHOICE_TABLE = "crm_commercial_offer_line_basis_choice"
# A market rate's quote copy is a document linked to the rate (Slice 4G), of this one document type.
COMMERCIAL_OFFER_MARKET_RATE_RECORD_TYPE = "commercial_offer_market_rate"
COMMERCIAL_OFFER_MARKET_RATE_DOCUMENT_TYPE = "VENDOR_QUOTE"

COMMERCIAL_OFFER_PRICING_EVIDENCE_TYPE_MARKET_RATE = "market_rate"
COMMERCIAL_OFFER_PRICING_EVIDENCE_TYPE_HISTORICAL_PLUM_RATE = "historical_plum_rate"
COMMERCIAL_OFFER_ALLOWED_PRICING_EVIDENCE_TYPES = (
    COMMERCIAL_OFFER_PRICING_EVIDENCE_TYPE_MARKET_RATE,
    COMMERCIAL_OFFER_PRICING_EVIDENCE_TYPE_HISTORICAL_PLUM_RATE,
)

COMMERCIAL_OFFER_EVENT_MARKET_RATE_ADDED = "CommercialOfferMarketRateAdded"
COMMERCIAL_OFFER_EVENT_HISTORICAL_RATE_ADDED = "CommercialOfferHistoricalRateAdded"
COMMERCIAL_OFFER_EVENT_BASIS_RATE_SELECTED = "CommercialOfferBasisRateSelected"

# Slice 4E Commercial Offer line/scope foundation.
COMMERCIAL_OFFER_LINE_TABLE = "crm_commercial_offer_line"

COMMERCIAL_OFFER_LINE_STATUS_ACTIVE = "ACTIVE"
COMMERCIAL_OFFER_LINE_STATUS_CANCELLED = "CANCELLED"
COMMERCIAL_OFFER_ALLOWED_LINE_STATUSES = (
    COMMERCIAL_OFFER_LINE_STATUS_ACTIVE,
    COMMERCIAL_OFFER_LINE_STATUS_CANCELLED,
)
COMMERCIAL_OFFER_LINE_INITIAL_STATUS = COMMERCIAL_OFFER_LINE_STATUS_ACTIVE

COMMERCIAL_OFFER_EVENT_LINE_ADDED = "CommercialOfferLineAdded"
COMMERCIAL_OFFER_EVENT_LINE_UPDATED = "CommercialOfferLineUpdated"

# Slice 6F Commercial Offer header T&C attachment foundation.
COMMERCIAL_OFFER_TC_CLAUSE_TABLE = "commercial_offer_tc_clause"

COMMERCIAL_OFFER_TC_CLAUSE_RECORD_TYPE = "commercial_offer_tc_clause"
COMMERCIAL_OFFER_EVENT_TC_CLAUSE_ATTACHED = "CommercialOfferTcClauseAttached"
COMMERCIAL_OFFER_EVENT_TC_CLAUSE_REMOVED = "CommercialOfferTcClauseRemoved"

# Slice 6I Commercial Offer submission evidence foundation.
COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_TABLE = "commercial_offer_submission_evidence"
COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_RECORD_TYPE = "commercial_offer_submission_evidence"

COMMERCIAL_OFFER_SUBMISSION_CHANNEL_EMAIL = "EMAIL"
COMMERCIAL_OFFER_SUBMISSION_CHANNEL_PORTAL = "PORTAL"
COMMERCIAL_OFFER_SUBMISSION_CHANNEL_HAND_DELIVERY = "HAND_DELIVERY"
COMMERCIAL_OFFER_SUBMISSION_CHANNEL_CUSTOMER_FORMAT_UPLOAD = "CUSTOMER_FORMAT_UPLOAD"
COMMERCIAL_OFFER_SUBMISSION_CHANNEL_TENDER_PORTAL = "TENDER_PORTAL"
COMMERCIAL_OFFER_SUBMISSION_CHANNEL_OTHER = "OTHER"
COMMERCIAL_OFFER_ALLOWED_SUBMISSION_CHANNELS = (
    COMMERCIAL_OFFER_SUBMISSION_CHANNEL_EMAIL,
    COMMERCIAL_OFFER_SUBMISSION_CHANNEL_PORTAL,
    COMMERCIAL_OFFER_SUBMISSION_CHANNEL_HAND_DELIVERY,
    COMMERCIAL_OFFER_SUBMISSION_CHANNEL_CUSTOMER_FORMAT_UPLOAD,
    COMMERCIAL_OFFER_SUBMISSION_CHANNEL_TENDER_PORTAL,
    COMMERCIAL_OFFER_SUBMISSION_CHANNEL_OTHER,
)

COMMERCIAL_OFFER_EVENT_SUBMISSION_EVIDENCE_RECORDED = "CommercialOfferSubmissionEvidenceRecorded"

# Slice 6I.2 Commercial Offer manual credit/exposure review foundation.
COMMERCIAL_OFFER_CREDIT_REVIEW_TABLE = "commercial_offer_credit_review"
COMMERCIAL_OFFER_CREDIT_REVIEW_RECORD_TYPE = "commercial_offer_credit_review"

COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_NOT_ASSESSED = "NOT_ASSESSED"
COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_WITHIN_LIMIT = "WITHIN_LIMIT_AS_PER_MANUAL_REVIEW"
COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVED = "APPROVED_WITH_REFERENCE"
COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_REJECTED_OR_ON_HOLD = "REJECTED_OR_ON_HOLD"
COMMERCIAL_OFFER_ALLOWED_CREDIT_REVIEW_STATUSES = (
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_NOT_ASSESSED,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_WITHIN_LIMIT,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVAL_REQUIRED,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVED,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_REJECTED_OR_ON_HOLD,
)

COMMERCIAL_OFFER_EVENT_CREDIT_REVIEW_RECORDED = "CommercialOfferCreditReviewRecorded"

# Slice 6J controlled submission lifecycle action.
COMMERCIAL_OFFER_MARK_SUBMITTED_ALLOWED_STATUSES = (
    COMMERCIAL_OFFER_STATUS_DRAFT,
    COMMERCIAL_OFFER_STATUS_READY_FOR_REVIEW,
)

# Slice 6K Commercial Offer in-place revision/resubmission traceability foundation. Slice 9F
# retires creation of new records through this mechanism, but these constants and routes remain
# for listing and safely closing legacy OPEN records created before 9F.
COMMERCIAL_OFFER_REVISION_TABLE = "commercial_offer_revision"
COMMERCIAL_OFFER_REVISION_RECORD_TYPE = "commercial_offer_revision"

COMMERCIAL_OFFER_REVISION_STATUS_OPEN = "OPEN"
COMMERCIAL_OFFER_REVISION_STATUS_RESUBMITTED = "RESUBMITTED"
COMMERCIAL_OFFER_REVISION_STATUS_CANCELLED = "CANCELLED"

COMMERCIAL_OFFER_REVISION_REASON_CUSTOMER_CLARIFICATION = "CUSTOMER_CLARIFICATION"
COMMERCIAL_OFFER_REVISION_REASON_RATE_CORRECTION = "RATE_CORRECTION"
COMMERCIAL_OFFER_REVISION_REASON_SCOPE_CHANGE = "SCOPE_CHANGE"
COMMERCIAL_OFFER_REVISION_REASON_TENDER_CORRIGENDUM = "TENDER_CORRIGENDUM"
COMMERCIAL_OFFER_REVISION_REASON_INTERNAL_CORRECTION = "INTERNAL_CORRECTION"
COMMERCIAL_OFFER_REVISION_REASON_OTHER = "OTHER"
COMMERCIAL_OFFER_ALLOWED_REVISION_REASONS = (
    COMMERCIAL_OFFER_REVISION_REASON_CUSTOMER_CLARIFICATION,
    COMMERCIAL_OFFER_REVISION_REASON_RATE_CORRECTION,
    COMMERCIAL_OFFER_REVISION_REASON_SCOPE_CHANGE,
    COMMERCIAL_OFFER_REVISION_REASON_TENDER_CORRIGENDUM,
    COMMERCIAL_OFFER_REVISION_REASON_INTERNAL_CORRECTION,
    COMMERCIAL_OFFER_REVISION_REASON_OTHER,
)

# Historical compatibility rule for pre-9F revision rows. New commercial changes use an immutable
# Commercial Offer version row instead of changing the submitted row in place.
COMMERCIAL_OFFER_REVISION_OPEN_ALLOWED_STATUSES = (COMMERCIAL_OFFER_STATUS_SUBMITTED,)

COMMERCIAL_OFFER_EVENT_REVISION_OPENED = "CommercialOfferRevisionOpened"
COMMERCIAL_OFFER_EVENT_REVISION_RESUBMITTED = "CommercialOfferRevisionResubmitted"
COMMERCIAL_OFFER_EVENT_REVISION_CANCELLED = "CommercialOfferRevisionCancelled"

# Slice 6L customer response / award outcome traceability foundation.
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_TABLE = "commercial_offer_customer_response"
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_RECORD_TYPE = "commercial_offer_customer_response"
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ACCEPTED_AWARDED = "ACCEPTED_AWARDED"
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REJECTED_LOST = "REJECTED_LOST"
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REVISION_REQUESTED = "REVISION_REQUESTED"
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ON_HOLD = "ON_HOLD"
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_PENDING = "PENDING_CUSTOMER_DECISION"
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_OTHER = "OTHER"
COMMERCIAL_OFFER_ALLOWED_CUSTOMER_RESPONSE_OUTCOMES = (
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ACCEPTED_AWARDED,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REJECTED_LOST,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REVISION_REQUESTED,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_CLARIFICATION_REQUESTED,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ON_HOLD,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_PENDING,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_OTHER,
)


def latest_response_not_accepted_reason(outcome: str) -> str:
    """Why an accepted offer whose latest customer response is `outcome`, not the acceptance, makes no Work Order
    (CS-04 part 1): the handoff's refusal and the lifecycle view's reason, in the same words."""
    label = outcome.replace("_", " ").capitalize()
    return (
        f"The customer's latest response is {label}. Record the customer's acceptance or award first, then create the "
        "Work Order."
    )


COMMERCIAL_OFFER_ALLOWED_CUSTOMER_RESPONSE_CHANNELS = (
    "EMAIL",
    "TENDER_PORTAL",
    "CUSTOMER_PO",
    "LETTER_OF_AWARD",
    "PHONE_OR_VERBAL",
    "MEETING",
    "OTHER",
)
# A Rejected Commercial Offer is final: no further customer response may be recorded
# against it, and Sales must record any later award against the replacement offer instead.
#
# REJECTED was previously included here. Because a rejected offer is also treated as inactive
# for the Slice 6B.1 one-active-Base-Offer guard, a replacement offer could already exist for
# the same Opportunity; a late ACCEPTED_AWARDED response against the rejected offer then drove
# it back to ACCEPTED, leaving two live offers for one enquiry. Recorded as a known gap in
# `docs/agent/DEFERRED_REQUIREMENTS.md` ("Commercial Offer lifecycle reactivation") and closed
# here by explicit business decision, 7 September 2026.
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES = (
    COMMERCIAL_OFFER_STATUS_SUBMITTED,
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
)
COMMERCIAL_OFFER_EVENT_CUSTOMER_RESPONSE_RECORDED = "CommercialOfferCustomerResponseRecorded"

# Slice 6M post-response lifecycle/readiness cleanup.
# These codes describe a derived, read-only interpretation of the existing
# Slice 6H/6I/6J/6K/6L records. They do not introduce a new persisted state
# machine; the underlying source of truth remains offer_status_code, the
# customer-response history, immutable offer versions and any legacy revision history.
COMMERCIAL_OFFER_LIFECYCLE_STATE_NOT_YET_SUBMITTED = "NOT_YET_SUBMITTED"
COMMERCIAL_OFFER_LIFECYCLE_STATE_AWAITING_CUSTOMER_RESPONSE = "AWAITING_CUSTOMER_RESPONSE"
COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_READY_FOR_HANDOFF = "ACCEPTED_READY_FOR_HANDOFF"
COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_HANDOFF_BLOCKED = "ACCEPTED_HANDOFF_BLOCKED"
COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_WORK_ORDER_EXISTS = "ACCEPTED_WORK_ORDER_EXISTS"
COMMERCIAL_OFFER_LIFECYCLE_STATE_REJECTED_CLOSED = "REJECTED_CLOSED"
COMMERCIAL_OFFER_LIFECYCLE_STATE_REPLACED_HISTORY = "REPLACED_HISTORY"
COMMERCIAL_OFFER_LIFECYCLE_STATE_ABANDONED_HISTORY = "ABANDONED_HISTORY"
COMMERCIAL_OFFER_LIFECYCLE_STATE_REVISION_REQUESTED_ACTIVE = "REVISION_REQUESTED_ACTIVE"
COMMERCIAL_OFFER_LIFECYCLE_STATE_CLARIFICATION_REQUESTED_ACTIVE = "CLARIFICATION_REQUESTED_ACTIVE"
COMMERCIAL_OFFER_LIFECYCLE_STATE_ON_HOLD_ACTIVE = "ON_HOLD_ACTIVE"
COMMERCIAL_OFFER_LIFECYCLE_STATE_PENDING_CUSTOMER_DECISION_ACTIVE = "PENDING_CUSTOMER_DECISION_ACTIVE"
COMMERCIAL_OFFER_LIFECYCLE_STATE_OTHER_ACTIVE = "OTHER_ACTIVE"

# Slice 6O.1 Supplementary / Change Quotation related-offer foundation.
# A related offer is a SEPARATE Commercial Offer series under the same Opportunity, not a later
# version of the Base Offer. Legacy commercial_offer_revision rows remain scoped inside one
# historical offer record; do not conflate any of these mechanisms.
COMMERCIAL_OFFER_PURPOSE_BASE = "BASE"
COMMERCIAL_OFFER_PURPOSE_SUPPLEMENTARY = "SUPPLEMENTARY"
COMMERCIAL_OFFER_PURPOSE_CHANGE_QUOTATION = "CHANGE_QUOTATION"
COMMERCIAL_OFFER_ALLOWED_PURPOSES = (
    COMMERCIAL_OFFER_PURPOSE_BASE,
    COMMERCIAL_OFFER_PURPOSE_SUPPLEMENTARY,
    COMMERCIAL_OFFER_PURPOSE_CHANGE_QUOTATION,
)
# The related-offer creation action accepts only these two purposes. BASE offers are
# created only through the ordinary POST /api/commercial-offers route.
COMMERCIAL_OFFER_RELATED_OFFER_ALLOWED_PURPOSES = (
    COMMERCIAL_OFFER_PURPOSE_SUPPLEMENTARY,
    COMMERCIAL_OFFER_PURPOSE_CHANGE_QUOTATION,
)
COMMERCIAL_OFFER_INITIAL_PURPOSE = COMMERCIAL_OFFER_PURPOSE_BASE
COMMERCIAL_OFFER_PURPOSE_LABELS: dict[str, str] = {
    COMMERCIAL_OFFER_PURPOSE_BASE: "Base Offer",
    COMMERCIAL_OFFER_PURPOSE_SUPPLEMENTARY: "Supplementary Offer",
    COMMERCIAL_OFFER_PURPOSE_CHANGE_QUOTATION: "Change Quotation",
}

# A Base Offer is eligible to father a related offer only while it currently carries
# an accepted/awarded basis.
#
# ACCEPTED is NOT immutable. Slice 6M.1 stops *generic update* leaving it, but the dedicated
# Slice 6L customer-response route writes offer_status_code directly and can move an accepted
# offer to REJECTED. An earlier version of this comment called ACCEPTED a "cannot-leave terminal
# status" and therefore a "stable" rule; that was wrong, and it is precisely why the missing row
# lock on related-offer creation looked unnecessary through three review rounds (Slice 9B).
#
# Every caller that reads this eligibility and then inserts must take
# `lock_commercial_offer_row` on the Base Offer first. Creation still does not reopen, mutate or
# reinterpret the Base Offer.
COMMERCIAL_OFFER_RELATED_OFFER_BASE_ELIGIBLE_STATUSES = (COMMERCIAL_OFFER_STATUS_ACCEPTED,)

COMMERCIAL_OFFER_EVENT_RELATED_OFFER_CREATED = "CommercialOfferRelatedOfferCreated"

# Slice 9E Quotation Generation foundation.
COMMERCIAL_OFFER_QUOTE_DOCUMENT_TABLE = "crm_commercial_offer_quote_document"
COMMERCIAL_OFFER_QUOTE_DOCUMENT_RECORD_TYPE = "commercial_offer_quote_document"

COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT = "DRAFT"
COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_APPROVED_FOR_ISSUE = "APPROVED_FOR_ISSUE"
COMMERCIAL_OFFER_ALLOWED_QUOTE_DOCUMENT_STATUSES = (
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT,
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_APPROVED_FOR_ISSUE,
)

# A customer-facing quotation is meaningful only while the offer is still in an active
# preparation/submission phase. ACCEPTED, REJECTED, WITHDRAWN and CLOSED are all excluded: a
# concluded offer has no further quote to generate. This is intentionally its own tuple, not an
# alias of any existing status set - it does not share membership with
# COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES (which excludes only WITHDRAWN/REJECTED/
# CLOSED, keeping ACCEPTED eligible for a related-offer) or with any generic-update guard tuple.
COMMERCIAL_OFFER_QUOTE_DOCUMENT_GENERATE_ALLOWED_STATUSES = (
    COMMERCIAL_OFFER_STATUS_DRAFT,
    COMMERCIAL_OFFER_STATUS_READY_FOR_REVIEW,
    COMMERCIAL_OFFER_STATUS_SUBMITTED,
)

# A quotation may not be approved FOR ISSUE once the Commercial Offer itself has concluded
# (owner decision, 9 September 2026, on independent review's recommendation). "Approved for
# Issue" is a present authorisation to send the document to a customer; applying it after the
# offer is Accepted, Rejected, Withdrawn or Closed asserts an authorisation that no longer means
# anything. If retrospective confirmation of which version was actually sent is wanted later,
# that needs its own archival action rather than reusing this one.
#
# Deliberately its own tuple even though it currently shares membership with
# COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES. This module has been bitten before by
# collapsing two same-looking sets into one alias (see the Slice 6M.1 comment above): they answer
# different questions and are free to diverge.
COMMERCIAL_OFFER_QUOTE_DOCUMENT_APPROVE_BLOCKED_OFFER_STATUSES = (
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
    COMMERCIAL_OFFER_STATUS_REJECTED,
    COMMERCIAL_OFFER_STATUS_WITHDRAWN,
    COMMERCIAL_OFFER_STATUS_CLOSED,
    COMMERCIAL_OFFER_STATUS_REVISED,
    COMMERCIAL_OFFER_STATUS_ABANDONED,
)

COMMERCIAL_OFFER_EVENT_QUOTE_DOCUMENT_GENERATED = "CommercialOfferQuoteDocumentGenerated"
COMMERCIAL_OFFER_EVENT_QUOTE_DOCUMENT_APPROVED_FOR_ISSUE = "CommercialOfferQuoteDocumentApprovedForIssue"

COMMERCIAL_OFFER_LIFECYCLE_STATE_LABELS: dict[str, str] = {
    COMMERCIAL_OFFER_LIFECYCLE_STATE_NOT_YET_SUBMITTED: "Not yet submitted",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_AWAITING_CUSTOMER_RESPONSE: "Submitted - awaiting customer response",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_READY_FOR_HANDOFF: "Accepted / awarded - ready to create the Work Order",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_HANDOFF_BLOCKED: "Accepted / awarded - Work Order cannot be created yet",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_WORK_ORDER_EXISTS: "Accepted / awarded - Work Order already created",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_REJECTED_CLOSED: "Rejected / lost - closed",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_REPLACED_HISTORY: "Replaced version - history",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_ABANDONED_HISTORY: "Abandoned version - history",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_REVISION_REQUESTED_ACTIVE: "Customer requested revision",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_CLARIFICATION_REQUESTED_ACTIVE: "Customer requested clarification",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_ON_HOLD_ACTIVE: "On hold",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_PENDING_CUSTOMER_DECISION_ACTIVE: "Pending customer decision",
    COMMERCIAL_OFFER_LIFECYCLE_STATE_OTHER_ACTIVE: "Other customer response recorded",
}
