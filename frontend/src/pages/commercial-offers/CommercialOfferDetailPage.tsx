import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import DocumentsPanel from "../../components/DocumentsPanel";
import { PageHeader, ReferenceText, SectionCard, SectionGroup, SectionIndex, StatusBadge, formatWorkOrderStatusLabel } from "../../components/PageLayout";
import CurrencySelect from "../../components/CurrencySelect";
import DateInput from "../../components/DateInput";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { apiDateTimeToIndiaInput, enteredIndiaTimeToUtc } from "../../components/enteredDateTime";
import { DEFAULT_CURRENCY, isOperatingCurrency, UNSUPPORTED_CURRENCY_MESSAGE } from "../../components/currency";
import { offerVersionLabel as formatOfferVersion } from "../../components/offerVersion";
import { readSafeReturnTarget, type ReturnTarget } from "../../components/returnTarget";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";
import {
  COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS,
  contentLockedNote,
  offerContentLocked,
  statusUpdateOptions,
} from "./offerStatus";
import { createWorkOrderLabel, existingWorkOrdersNote } from "./workOrderActions";
import LineMarketRates, { nearestLineMarketRatesPanel } from "./LineMarketRates";
import { rateSummary, ratesForLine, wholeOfferRates, type MarketRate } from "./lineMarketRatesState";
import { NOTHING_CHANGED_MESSAGE, changedFields, updateRequest } from "./offerEditState";

const COMMERCIAL_OFFER_DETAIL_BASE_PATH = "/api/commercial-offers";
const COMMERCIAL_OFFER_PRICING_EVIDENCE_BASE_PATH = "/api/commercial-offers";
const COMMERCIAL_OFFER_LINES_BASE_PATH = "/api/commercial-offers";
const COMMERCIAL_OFFER_TC_CLAUSES_BASE_PATH = "/api/commercial-offers";
const COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_BASE_PATH = "/api/commercial-offers";
const COMMERCIAL_OFFER_CREDIT_REVIEW_BASE_PATH = "/api/commercial-offers";
const COMMERCIAL_OFFER_VERSION_BASE_PATH = "/api/commercial-offers";
const COMMERCIAL_OFFER_REVISION_BASE_PATH = "/api/commercial-offers";
const COMMERCIAL_OFFER_CUSTOMER_RESPONSE_BASE_PATH = "/api/commercial-offers";
const COMMERCIAL_OFFER_LIFECYCLE_GUIDANCE_BASE_PATH = "/api/commercial-offers";
const COMMERCIAL_OFFER_QUOTE_DOCUMENTS_BASE_PATH = "/api/commercial-offers";
const DOCUMENTS_CONTENT_BASE_PATH = "/api/documents";
const TC_CLAUSE_LIBRARY_BASE_PATH = "/api/tc-clauses";
const WORK_ORDER_LIST_BASE_PATH = "/api/work-orders";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const EVENT_VIEW_ROLES = ["ADMIN", "MANAGEMENT_READ_ONLY"];
const COMMERCIAL_OFFER_WORK_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];
const COMMERCIAL_OFFER_PRICING_EVIDENCE_WORK_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER", "OPERATIONS_USER"];
const COMMERCIAL_OFFER_LINE_WORK_ROLES = COMMERCIAL_OFFER_WORK_ROLES;
const COMMERCIAL_OFFER_TC_CLAUSE_WORK_ROLES = COMMERCIAL_OFFER_WORK_ROLES;
const COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WORK_ROLES = COMMERCIAL_OFFER_WORK_ROLES;
const COMMERCIAL_OFFER_CREDIT_REVIEW_WORK_ROLES = COMMERCIAL_OFFER_WORK_ROLES;
const COMMERCIAL_OFFER_REVISION_WORK_ROLES = COMMERCIAL_OFFER_WORK_ROLES;
const COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WORK_ROLES = COMMERCIAL_OFFER_WORK_ROLES;
// Generating a quote matches the existing Commercial Offer create/manage role set. Approving one
// for issue is deliberately narrower - Sales User may generate but not approve (owner decision 4,
// 8 September 2026) - so this is its own distinct role list, not COMMERCIAL_OFFER_WORK_ROLES.
const COMMERCIAL_OFFER_QUOTE_GENERATE_ROLES = COMMERCIAL_OFFER_WORK_ROLES;
const COMMERCIAL_OFFER_QUOTE_APPROVE_ROLES = ["ADMIN", "SALES_MANAGER"];
// Who may add files to an offer (owner decision, 11 September 2026). A usability aid only: the
// server refuses anyone else. It grants offer uploads through the pricing-evidence write
// permission (documents/contract.py DOCUMENT_LINK_WRITE_PERMISSION), so if that permission's roles
// change, change this list with them. Kept as its own list so the upload rule stays visible here.
const COMMERCIAL_OFFER_DOCUMENT_UPLOAD_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER", "OPERATIONS_USER"];
const WORK_ORDER_HANDOFF_ROLES = [
  "ADMIN",
  "SALES_USER",
  "SALES_MANAGER",
  "OPERATIONS_USER",
];
const TC_RECOMMENDATION_BASIS_OPTIONS = [
  { value: "", label: "Select recommendation basis" },
  { value: "HIRING", label: "Equipment Hiring" },
  { value: "TRANSPORTATION", label: "Transportation" },
] as const;

const SUBMISSION_CHANNEL_OPTIONS = [
  { value: "EMAIL", label: "Email" },
  { value: "PORTAL", label: "Portal" },
  { value: "HAND_DELIVERY", label: "Hand delivery" },
  { value: "CUSTOMER_FORMAT_UPLOAD", label: "Customer format upload" },
  { value: "TENDER_PORTAL", label: "Tender portal" },
  { value: "OTHER", label: "Other" },
] as const;

const CREDIT_REVIEW_STATUS_OPTIONS = [
  { value: "NOT_ASSESSED", label: "Not assessed" },
  { value: "WITHIN_LIMIT_AS_PER_MANUAL_REVIEW", label: "Within limit as per manual review" },
  { value: "APPROVAL_REQUIRED", label: "Approval required" },
  { value: "APPROVED_WITH_REFERENCE", label: "Approved with reference" },
  { value: "REJECTED_OR_ON_HOLD", label: "Rejected or on hold" },
] as const;

const REVISION_REASON_OPTIONS = [
  { value: "CUSTOMER_CLARIFICATION", label: "Customer clarification" },
  { value: "RATE_CORRECTION", label: "Rate correction" },
  { value: "SCOPE_CHANGE", label: "Scope change" },
  { value: "TENDER_CORRIGENDUM", label: "Tender corrigendum" },
  { value: "INTERNAL_CORRECTION", label: "Internal correction" },
  { value: "OTHER", label: "Other" },
] as const;

const CUSTOMER_RESPONSE_OUTCOME_OPTIONS = [
  { value: "ACCEPTED_AWARDED", label: "Accepted / awarded" },
  { value: "REJECTED_LOST", label: "Rejected / lost" },
  { value: "REVISION_REQUESTED", label: "Revision requested" },
  { value: "CLARIFICATION_REQUESTED", label: "Clarification requested" },
  { value: "ON_HOLD", label: "On hold" },
  { value: "PENDING_CUSTOMER_DECISION", label: "Pending customer decision" },
  { value: "OTHER", label: "Other" },
] as const;

const CUSTOMER_RESPONSE_CHANNEL_OPTIONS = [
  { value: "EMAIL", label: "Email" },
  { value: "TENDER_PORTAL", label: "Tender portal" },
  { value: "CUSTOMER_PO", label: "Customer PO" },
  { value: "LETTER_OF_AWARD", label: "Letter of award" },
  { value: "PHONE_OR_VERBAL", label: "Phone / verbal" },
  { value: "MEETING", label: "Meeting" },
  { value: "OTHER", label: "Other" },
] as const;

const COMMERCIAL_OFFER_DETAIL_TABS = [
  { id: "overview", label: "Overview" },
  { id: "lines-pricing", label: "Lines & Pricing" },
  { id: "terms", label: "Terms & Conditions" },
  { id: "submission", label: "Submission" },
  { id: "traceability", label: "Traceability" },
] as const;

type CommercialOfferDetailTab = typeof COMMERCIAL_OFFER_DETAIL_TABS[number]["id"];

const COMMERCIAL_OFFER_STATUS_FLOW = [
  "DRAFT",
  "READY_FOR_REVIEW",
  "SUBMITTED",
  "REVISED",
  "ABANDONED",
  "WITHDRAWN",
  "ACCEPTED",
  "REJECTED",
  "CLOSED",
] as const;

// COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS and statusUpdateOptions (./offerStatus) hold the statuses
// the edit form can set; ACCEPTED and REJECTED are never among them (Slice 6M.1).
const COMMERCIAL_OFFER_MARK_SUBMITTED_STATUSES = ["DRAFT", "READY_FOR_REVIEW"] as const;
// Matches backend COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES (Slice 6M.1 fa09489 +
// completion). Once an offer reaches one of these statuses, the general update route blocks
// any further status change away from it. This is a different concept from
// COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS above (which statuses can be *entered*) - ACCEPTED
// is cannot-leave but not a selectable entry target, so it appears here but not there.
const COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES = ["WITHDRAWN", "REJECTED", "CLOSED", "ACCEPTED"] as const;
// Matches backend COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES. Shown in the
// Workflow position badges to explain why ACCEPTED/REJECTED are not offered in the edit form.
const COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES = ["ACCEPTED", "REJECTED"] as const;
const ACCOUNT_TRACEABILITY_ACTION_STATUSES = ["SUBMITTED", "ACCEPTED"] as const;

const COMMERCIAL_OFFER_MODE_OPTIONS = [
  { value: "plum_generated", label: "Plum generated" },
  { value: "external_tender", label: "External tender" },
  { value: "customer_format", label: "Customer format" },
  { value: "budgetary_response", label: "Budgetary response" },
  { value: "other", label: "Other" },
] as const;

const COMMERCIAL_OFFER_TYPE_OPTIONS = [
  { value: "budgetary", label: "Budgetary" },
  { value: "firm", label: "Firm" },
  { value: "tender_response", label: "Tender response" },
  { value: "revision", label: "Revision" },
  { value: "other", label: "Other" },
] as const;

const BUTTON_STYLE = {
  display: "inline-block",
  padding: "10px 12px",
  border: "1px solid #1d4ed8",
  background: "#ffffff",
  color: "#1d4ed8",
  fontWeight: 700,
  textDecoration: "none",
  cursor: "pointer",
} as const;

const MUTED_BUTTON_STYLE = {
  display: "inline-block",
  padding: "10px 12px",
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#374151",
  fontWeight: 700,
  textDecoration: "none",
  cursor: "pointer",
} as const;

const DETAIL_GRID_STYLE = {
  display: "grid",
  gridTemplateColumns: "220px 1fr",
  gap: "8px 12px",
} as const;

const COMPACT_DETAIL_GRID_STYLE = {
  display: "grid",
  gridTemplateColumns: "160px 1fr",
  gap: "8px 12px",
} as const;

const REVISION_FORM_CONTROL_STYLE = {
  width: "100%",
  maxWidth: "100%",
  minWidth: 0,
  boxSizing: "border-box",
  padding: "8px",
} as const;

const SAFE_LONG_TEXT_STYLE = {
  minWidth: 0,
  maxWidth: "100%",
  overflowWrap: "anywhere",
  wordBreak: "break-word",
} as const;

type CommercialOffer = {
  public_id: string;
  offer_code: string;
  opportunity_public_id: string;
  account_public_id?: string | null;
  offer_title?: string | null;
  offer_mode: string;
  offer_type: string;
  offer_status_code: string;
  offer_value?: string | number | null;
  currency_code: string;
  offer_date?: string | null;
  valid_until?: string | null;
  submitted_at?: string | null;
  submission_reference?: string | null;
  submission_proof_note?: string | null;
  outcome_date?: string | null;
  outcome_remarks?: string | null;
  remarks?: string | null;
  offer_purpose: string;
  base_offer_public_id?: string | null;
  base_offer_code?: string | null;
  related_work_order_public_id?: string | null;
  related_work_order_code?: string | null;
  customer_request_reference?: string | null;
  customer_request_received_date?: string | null;
  customer_request_summary?: string | null;
  version_number: number;
  previous_version_offer_public_id?: string | null;
  version_reason?: string | null;
  version_note?: string | null;
  replaced_by_offer_public_id?: string | null;
  replaced_by_version_number?: number | null;
  created_by?: string | null;
  created_by_display_name?: string | null;
  created_at: string;
  updated_at: string;
  // CS-05a: the version an edit of the offer sends back.
  row_version: number;
};

type WorkOrderAmendmentSummary = {
  public_id: string;
  work_order_public_id: string;
  work_order_code: string;
  amendment_sequence_no: number;
  amendment_type_code: string;
  amendment_status_code: string;
  amendment_reason: string;
  related_commercial_offer_public_id?: string | null;
};

const COMMERCIAL_OFFER_PURPOSE_LABELS: Record<string, string> = {
  BASE: "Base Offer",
  SUPPLEMENTARY: "Supplementary Offer",
  CHANGE_QUOTATION: "Change Quotation",
};

function offerPurposeLabel(offerPurpose: string): string {
  return COMMERCIAL_OFFER_PURPOSE_LABELS[offerPurpose] || offerPurpose;
}

const AMENDMENT_TYPE_LABELS: Record<string, string> = {
  ADMINISTRATIVE: "Administrative",
  COMMERCIAL: "Commercial",
  MIXED: "Mixed (Administrative + Commercial)",
};

function amendmentTypeLabel(typeCode: string): string {
  return AMENDMENT_TYPE_LABELS[typeCode] || typeCode;
}

type CommercialOfferEvent = {
  public_id?: string | null;
  event_name?: string | null;
  record_type?: string | null;
  record_public_id?: string | null;
};

type CommercialOfferUpdatedResponse = {
  commercial_offer: CommercialOffer;
  events: CommercialOfferEvent[];
};

type CommercialOfferMarkedSubmittedResponse = {
  commercial_offer: CommercialOffer;
  event: CommercialOfferEvent;
  warnings: string[];
};

type TokenPayload = {
  role_codes?: unknown;
  exp?: unknown;
};

type AccessStatus = "checking" | "allowed" | "no_token" | "expired" | "invalid_token";

type PageAccess = {
  status: AccessStatus;
  roleCodes: string[];
  canViewEvents: boolean;
  canWorkCommercialOffer: boolean;
  canWorkPricingEvidence: boolean;
  canWorkOfferLines: boolean;
  canWorkTcClauses: boolean;
  canWorkSubmissionEvidence: boolean;
  canWorkCreditReview: boolean;
  canWorkRevisions: boolean;
  canWorkCustomerResponses: boolean;
  canCreateWorkOrder: boolean;
  canGenerateQuoteDocument: boolean;
  canApproveQuoteDocument: boolean;
};

type PricingEvidence = MarketRate;


type CommercialOfferLine = {
  public_id: string;
  commercial_offer_public_id: string;
  line_number: number;
  line_status_code: string;
  scope_description: string;
  equipment_service_category?: string | null;
  quantity: string | number;
  uom: string;
  rate_amount?: string | number | null;
  currency_code: string;
  line_amount?: string | number | null;
  remarks?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  // CS-05a: the version an edit of the line sends back.
  row_version: number;
};

type CommercialOfferLineCreatedResponse = {
  offer_line: CommercialOfferLine;
  event: CommercialOfferEvent;
};

type CommercialOfferLineUpdatedResponse = {
  offer_line: CommercialOfferLine;
  event: CommercialOfferEvent;
};

type TcClauseLibraryOption = {
  public_id: string;
  clause_id: string;
  business_line: string;
  clause_category: string;
  source_clause_number?: string | null;
  title: string;
  clause_text: string;
  mandatory_default: boolean;
  risk_category?: string | null;
  applies_to_header: boolean;
  applies_to_line: boolean;
  requires_approval_if_omitted: boolean;
  requires_approval_if_modified: boolean;
  active: boolean;
  source_reference?: string | null;
  created_at: string;
  updated_at: string;
};

type CommercialOfferTcClause = {
  public_id: string;
  commercial_offer_public_id: string;
  tc_clause_public_id: string;
  clause_id_snapshot: string;
  title_snapshot: string;
  clause_text_snapshot: string;
  business_line_snapshot: string;
  clause_category_snapshot: string;
  source_clause_number_snapshot?: string | null;
  source_reference_snapshot?: string | null;
  mandatory_default_snapshot: boolean;
  risk_category_snapshot?: string | null;
  applies_to_header_snapshot: boolean;
  applies_to_line_snapshot: boolean;
  requires_approval_if_omitted_snapshot: boolean;
  requires_approval_if_modified_snapshot: boolean;
  sort_order: number;
  active: boolean;
  attached_by?: string | null;
  created_at: string;
  updated_at: string;
};

type CommercialOfferTcClauseAttachedResponse = {
  tc_clauses: CommercialOfferTcClause[];
  events: CommercialOfferEvent[];
};

type CommercialOfferTcClauseRemovedResponse = {
  tc_clause: CommercialOfferTcClause;
  event: CommercialOfferEvent;
};

type CommercialOfferTcClauseReadinessClause = {
  tc_clause_public_id: string;
  clause_id: string;
  title: string;
  clause_text: string;
  business_line: string;
  clause_category: string;
  source_clause_number?: string | null;
  mandatory_default: boolean;
  risk_category?: string | null;
  applies_to_header: boolean;
  applies_to_line: boolean;
  requires_approval_if_omitted: boolean;
  requires_approval_if_modified: boolean;
  active: boolean;
  source_reference?: string | null;
  status: "ATTACHED" | "NOT_ATTACHED";
  attachment_public_id?: string | null;
};

type CommercialOfferTcClauseReadiness = {
  commercial_offer_public_id: string;
  recommendation_basis?: string | null;
  total_recommended_count: number;
  attached_recommended_count: number;
  missing_recommended_count: number;
  attached_optional_count: number;
  status_text: string;
  deferral_notes: string[];
  recommended_clauses: CommercialOfferTcClauseReadinessClause[];
};

type CommercialOfferTcClauseAttachRecommendedResponse = {
  readiness: CommercialOfferTcClauseReadiness;
  tc_clauses: CommercialOfferTcClause[];
  events: CommercialOfferEvent[];
  attached_count: number;
  status_text: string;
};

type CommercialOfferSubmissionEvidence = {
  public_id: string;
  commercial_offer_public_id: string;
  submission_reference?: string | null;
  submission_channel: string;
  submitted_at: string;
  submitted_by?: string | null;
  recipient_summary?: string | null;
  submitted_amount_snapshot?: string | number | null;
  submitted_currency_snapshot?: string | null;
  submitted_version_snapshot?: string | null;
  document_reference_label?: string | null;
  document_reference_url_or_path?: string | null;
  evidence_notes?: string | null;
  active: boolean;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

type CommercialOfferSubmissionEvidenceCreatedResponse = {
  submission_evidence: CommercialOfferSubmissionEvidence;
  event: CommercialOfferEvent;
};

type CommercialOfferCreditReview = {
  public_id: string;
  commercial_offer_public_id: string;
  review_status: string;
  review_basis?: string | null;
  review_reference?: string | null;
  reviewed_at: string;
  reviewed_by?: string | null;
  approved_amount_snapshot?: string | number | null;
  credit_days_snapshot?: number | null;
  exposure_note?: string | null;
  active: boolean;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

type CommercialOfferCreditReviewCreatedResponse = {
  credit_review: CommercialOfferCreditReview;
  event: CommercialOfferEvent;
};

type CommercialOfferRevision = {
  public_id: string;
  commercial_offer_public_id: string;
  revision_label: string;
  revision_reason: string;
  revision_notes?: string | null;
  revision_status: "OPEN" | "RESUBMITTED" | "CANCELLED";
  source_submission_evidence_public_id?: string | null;
  resubmission_evidence_public_id?: string | null;
  opened_at: string;
  opened_by?: string | null;
  resubmitted_at?: string | null;
  cancelled_at?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

type CommercialOfferRevisionActionResponse = {
  revision: CommercialOfferRevision;
  event: CommercialOfferEvent;
};

type CommercialOfferVersionActionResponse = {
  commercial_offer: CommercialOffer;
  event: CommercialOfferEvent;
};

type CommercialOfferCustomerResponse = {
  public_id: string;
  commercial_offer_public_id: string;
  response_outcome: string;
  response_reference?: string | null;
  response_received_at: string;
  response_channel: string;
  received_from?: string | null;
  awarded_amount_snapshot?: string | number | null;
  awarded_currency_snapshot?: string | null;
  awarded_version_snapshot?: string | null;
  customer_po_or_wo_reference?: string | null;
  customer_response_notes?: string | null;
  linked_submission_evidence_public_id?: string | null;
  linked_revision_public_id?: string | null;
  created_at: string;
};

type CommercialOfferCustomerResponseCreatedResponse = {
  customer_response: CommercialOfferCustomerResponse;
  commercial_offer: CommercialOffer;
  event: CommercialOfferEvent;
};

type SubmissionReadinessItem = {
  code: string;
  label: string;
  status: "PASS" | "ATTENTION_REQUIRED" | "BLOCKING" | "DEFERRED";
  severity: "INFO" | "WARNING" | "BLOCKING" | "DEFERRED";
  message: string;
  evidence: Record<string, unknown>;
  deferred: boolean;
};

type SubmissionReadiness = {
  commercial_offer_public_id: string;
  readiness_status: "READY" | "ATTENTION_REQUIRED" | "NOT_READY";
  summary: {
    passed_count: number;
    warning_count: number;
    blocking_count: number;
    deferred_count: number;
  };
  checklist_items: SubmissionReadinessItem[];
};

type CommercialOfferLinkedWorkOrderSummary = {
  public_id: string;
  work_order_code: string;
  work_order_status_code: string;
};

type CommercialOfferLifecycleGuidance = {
  commercial_offer_public_id: string;
  offer_status_code: string;
  latest_customer_response_outcome: string | null;
  latest_customer_response_public_id: string | null;
  latest_customer_response_received_at: string | null;
  lifecycle_state: string;
  lifecycle_state_label: string;
  is_commercially_active: boolean;
  advisory_message: string;
  recommended_next_action: string;
  can_open_revision: boolean;
  can_make_new_version: boolean;
  has_open_revision_awaiting_resubmission: boolean;
  can_record_customer_response: boolean;
  work_order_handoff_available: boolean;
  work_order_handoff_blocked_reasons: string[];
  linked_work_orders: CommercialOfferLinkedWorkOrderSummary[];
};

type CommercialOfferQuoteDocument = {
  public_id: string;
  commercial_offer_public_id: string;
  version_no: number;
  quote_reference: string;
  document_public_id: string;
  quote_status_code: string;
  generated_by?: string | null;
  generated_by_display_name?: string | null;
  generated_at: string;
  approved_by?: string | null;
  approved_by_display_name?: string | null;
  approved_at?: string | null;
  approval_note?: string | null;
  superseded_at?: string | null;
  is_stale: boolean;
  // Why this version could not be approved for issue when this response was read; null when it
  // could. Computed by the backend function that refuses the approval, never re-derived here.
  approval_blocked_reason?: string | null;
  created_at: string;
  updated_at: string;
};

type CommercialOfferQuoteDocumentGeneratedResponse = {
  quote_document: CommercialOfferQuoteDocument;
  event: CommercialOfferEvent;
};

type CommercialOfferQuoteDocumentApprovedResponse = {
  quote_document: CommercialOfferQuoteDocument;
  event: CommercialOfferEvent;
};

type WorkOrder = {
  public_id: string;
  work_order_code: string;
  work_order_title?: string | null;
  work_order_status_code: string;
  commercial_offer_public_id: string;
  commercial_offer_code?: string | null;
  opportunity_public_id: string;
  account_public_id?: string | null;
  customer_wo_reference?: string | null;
  received_date?: string | null;
  source_offer_status_code: string;
  remarks?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

type OfferLineForm = {
  line_number: string;
  line_status_code: string;
  scope_description: string;
  equipment_service_category: string;
  quantity: string;
  uom: string;
  rate_amount: string;
  currency_code: string;
  remarks: string;
};


type SubmissionEvidenceForm = {
  submission_reference: string;
  submission_channel: string;
  submitted_at: string;
  recipient_summary: string;
  submitted_version_snapshot: string;
  document_reference_label: string;
  document_reference_url_or_path: string;
  evidence_notes: string;
};

type CreditReviewForm = {
  review_status: string;
  review_basis: string;
  review_reference: string;
  reviewed_at: string;
  approved_amount_snapshot: string;
  credit_days_snapshot: string;
  exposure_note: string;
};

type VersionForm = {
  version_reason: string;
  version_note: string;
};

type CustomerResponseForm = {
  response_outcome: string;
  response_reference: string;
  response_received_at: string;
  response_channel: string;
  received_from: string;
  awarded_amount_snapshot: string;
  awarded_currency_snapshot: string;
  awarded_version_snapshot: string;
  customer_po_or_wo_reference: string;
  customer_response_notes: string;
  linked_submission_evidence_public_id: string;
  linked_revision_public_id: string;
};

type EditForm = {
  offer_title: string;
  offer_mode: string;
  offer_type: string;
  offer_status_code: string;
  offer_value: string;
  currency_code: string;
  offer_date: string;
  valid_until: string;
  submitted_at: string;
  submission_reference: string;
  submission_proof_note: string;
  outcome_date: string;
  outcome_remarks: string;
  remarks: string;
};


function emptySubmissionEvidenceForm(): SubmissionEvidenceForm {
  return {
    submission_reference: "",
    submission_channel: "EMAIL",
    submitted_at: "",
    recipient_summary: "",
    submitted_version_snapshot: "",
    document_reference_label: "",
    document_reference_url_or_path: "",
    evidence_notes: "",
  };
}

function emptyCreditReviewForm(): CreditReviewForm {
  return {
    review_status: "NOT_ASSESSED",
    review_basis: "",
    review_reference: "",
    reviewed_at: "",
    approved_amount_snapshot: "",
    credit_days_snapshot: "",
    exposure_note: "",
  };
}

function emptyVersionForm(): VersionForm {
  return { version_reason: "CUSTOMER_CLARIFICATION", version_note: "" };
}

function offerVersionLabel(offer: Pick<CommercialOffer, "offer_code" | "version_number">): string {
  return formatOfferVersion(offer.offer_code, offer.version_number);
}

function emptyCustomerResponseForm(): CustomerResponseForm {
  return {
    response_outcome: "PENDING_CUSTOMER_DECISION",
    response_reference: "",
    response_received_at: "",
    response_channel: "EMAIL",
    received_from: "",
    awarded_amount_snapshot: "",
    awarded_currency_snapshot: "INR",
    awarded_version_snapshot: "",
    customer_po_or_wo_reference: "",
    customer_response_notes: "",
    linked_submission_evidence_public_id: "",
    linked_revision_public_id: "",
  };
}

function emptyOfferLineForm(): OfferLineForm {
  return {
    line_number: "",
    line_status_code: "ACTIVE",
    scope_description: "",
    equipment_service_category: "",
    quantity: "1",
    uom: "day",
    rate_amount: "",
    currency_code: "INR",
    remarks: "",
  };
}

function formFromOfferLine(line: CommercialOfferLine): OfferLineForm {
  return {
    line_number: String(line.line_number ?? ""),
    line_status_code: line.line_status_code ?? "ACTIVE",
    scope_description: line.scope_description ?? "",
    equipment_service_category: line.equipment_service_category ?? "",
    quantity: line.quantity === null || line.quantity === undefined ? "" : String(line.quantity),
    uom: line.uom ?? "day",
    rate_amount: line.rate_amount === null || line.rate_amount === undefined ? "" : String(line.rate_amount),
    currency_code: line.currency_code ?? "INR",
    remarks: line.remarks ?? "",
  };
}

function emptyEditForm(): EditForm {
  return {
    offer_title: "",
    offer_mode: "plum_generated",
    offer_type: "budgetary",
    offer_status_code: "DRAFT",
    offer_value: "",
    currency_code: "INR",
    offer_date: "",
    valid_until: "",
    submitted_at: "",
    submission_reference: "",
    submission_proof_note: "",
    outcome_date: "",
    outcome_remarks: "",
    remarks: "",
  };
}

function formFromCommercialOffer(commercialOffer: CommercialOffer): EditForm {
  return {
    offer_title: commercialOffer.offer_title ?? "",
    offer_mode: commercialOffer.offer_mode ?? "plum_generated",
    offer_type: commercialOffer.offer_type ?? "budgetary",
    offer_status_code: commercialOffer.offer_status_code,
    offer_value: commercialOffer.offer_value === null || commercialOffer.offer_value === undefined ? "" : String(commercialOffer.offer_value),
    currency_code: commercialOffer.currency_code ?? "INR",
    offer_date: commercialOffer.offer_date ?? "",
    valid_until: commercialOffer.valid_until ?? "",
    submitted_at: apiDateTimeToIndiaInput(commercialOffer.submitted_at),
    submission_reference: commercialOffer.submission_reference ?? "",
    submission_proof_note: commercialOffer.submission_proof_note ?? "",
    outcome_date: commercialOffer.outcome_date ?? "",
    outcome_remarks: commercialOffer.outcome_remarks ?? "",
    remarks: commercialOffer.remarks ?? "",
  };
}

function clearPrototypeSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("pbl_auth_token");
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}

function decodeTokenPayload(token: string): TokenPayload | null {
  const parts = token.split(".");
  if (parts.length !== 3 || !parts[1]) return null;

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    return JSON.parse(window.atob(padded)) as TokenPayload;
  } catch {
    return null;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;

  const token = window.localStorage.getItem("pbl_auth_token");
  if (!token) return null;

  const payload = decodeTokenPayload(token);
  const exp = typeof payload?.exp === "number" ? payload.exp : Number(payload?.exp ?? 0);

  if (!payload || !exp || exp * 1000 <= Date.now()) {
    clearPrototypeSession();
    return null;
  }

  return token;
}

function hasAnyRole(roleCodes: string[], allowedRoles: string[]): boolean {
  return roleCodes.some((role) => allowedRoles.includes(role));
}

function readPageAccess(): PageAccess {
  const token = getToken();
  if (!token) {
    return { status: "no_token", roleCodes: [], canViewEvents: false, canWorkCommercialOffer: false, canWorkPricingEvidence: false, canWorkOfferLines: false, canWorkTcClauses: false, canWorkSubmissionEvidence: false, canWorkCreditReview: false, canWorkRevisions: false, canWorkCustomerResponses: false, canCreateWorkOrder: false, canGenerateQuoteDocument: false, canApproveQuoteDocument: false };
  }

  const payload = decodeTokenPayload(token);
  if (!payload) {
    return { status: "invalid_token", roleCodes: [], canViewEvents: false, canWorkCommercialOffer: false, canWorkPricingEvidence: false, canWorkOfferLines: false, canWorkTcClauses: false, canWorkSubmissionEvidence: false, canWorkCreditReview: false, canWorkRevisions: false, canWorkCustomerResponses: false, canCreateWorkOrder: false, canGenerateQuoteDocument: false, canApproveQuoteDocument: false };
  }

  const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp ?? 0);
  if (exp > 0 && exp * 1000 < Date.now()) {
    clearPrototypeSession();
    return { status: "expired", roleCodes: [], canViewEvents: false, canWorkCommercialOffer: false, canWorkPricingEvidence: false, canWorkOfferLines: false, canWorkTcClauses: false, canWorkSubmissionEvidence: false, canWorkCreditReview: false, canWorkRevisions: false, canWorkCustomerResponses: false, canCreateWorkOrder: false, canGenerateQuoteDocument: false, canApproveQuoteDocument: false };
  }

  const roleCodes = Array.isArray(payload.role_codes)
    ? payload.role_codes.filter((role): role is string => typeof role === "string")
    : [];

  return {
    status: "allowed",
    roleCodes,
    canViewEvents: hasAnyRole(roleCodes, EVENT_VIEW_ROLES),
    canWorkCommercialOffer: hasAnyRole(roleCodes, COMMERCIAL_OFFER_WORK_ROLES),
    canWorkPricingEvidence: hasAnyRole(roleCodes, COMMERCIAL_OFFER_PRICING_EVIDENCE_WORK_ROLES),
    canWorkOfferLines: hasAnyRole(roleCodes, COMMERCIAL_OFFER_LINE_WORK_ROLES),
    canWorkTcClauses: hasAnyRole(roleCodes, COMMERCIAL_OFFER_TC_CLAUSE_WORK_ROLES),
    canWorkSubmissionEvidence: hasAnyRole(roleCodes, COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WORK_ROLES),
    canWorkCreditReview: hasAnyRole(roleCodes, COMMERCIAL_OFFER_CREDIT_REVIEW_WORK_ROLES),
    canWorkRevisions: hasAnyRole(roleCodes, COMMERCIAL_OFFER_REVISION_WORK_ROLES),
    canWorkCustomerResponses: hasAnyRole(roleCodes, COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WORK_ROLES),
    canCreateWorkOrder: hasAnyRole(roleCodes, WORK_ORDER_HANDOFF_ROLES),
    canGenerateQuoteDocument: hasAnyRole(roleCodes, COMMERCIAL_OFFER_QUOTE_GENERATE_ROLES),
    canApproveQuoteDocument: hasAnyRole(roleCodes, COMMERCIAL_OFFER_QUOTE_APPROVE_ROLES),
  };
}

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "-";
}

function formatSubmissionEvidenceOptionLabel(evidence: CommercialOfferSubmissionEvidence): string {
  const reference = displayValue(evidence.submission_reference);
  const formattedDateTime = formatDateTime(evidence.submitted_at);
  const shortDate = formattedDateTime.split(",")[0] || formattedDateTime;
  return `${reference} · ${shortDate}`;
}

function formatSubmissionEvidenceDetail(evidence: CommercialOfferSubmissionEvidence | null | undefined): string {
  if (!evidence) return "";

  const parts = [
    displayValue(evidence.submission_reference),
    formatStatusLabel(evidence.submission_channel),
    formatDateTime(evidence.submitted_at),
    evidence.submitted_version_snapshot ? `Version/revision: ${evidence.submitted_version_snapshot}` : "",
    evidence.document_reference_label ? `Document: ${evidence.document_reference_label}` : "",
    evidence.document_reference_url_or_path ? `Reference: ${evidence.document_reference_url_or_path}` : "",
  ].filter((part) => part && part !== "-");

  return parts.join(" · ");
}

function normalizeOptional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function hrefWithReturnTarget(href: string, returnTo: string, returnLabel: string): string {
  const separator = href.includes("?") ? "&" : "?";
  return `${href}${separator}returnTo=${encodeURIComponent(returnTo)}&returnLabel=${encodeURIComponent(returnLabel)}`;
}

function formatDateOnly(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "2-digit" });
}

function formatMoney(value: string | number | null | undefined, currencyCode = "INR"): string {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return `${currencyCode} ${numeric.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

// A revised offer is either still in progress or has been sent to the customer again.
function formatRevisionStatusLabel(value: string | null | undefined): string {
  if (value === "OPEN") return "In progress";
  if (value === "RESUBMITTED") return "Re-sent";
  return formatStatusLabel(value);
}

function formatStatusLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function commercialOfferDetailErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to view this Commercial Offer.";
  if (status === 404) return "Commercial Offer not found.";
  return `Could not load Commercial Offer. HTTP ${status}.`;
}

async function pricingEvidenceErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role can view pricing evidence but cannot add or select it.";
  if (response.status === 404) return "Commercial Offer or pricing evidence record not found.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return `Could not save pricing evidence. HTTP ${response.status}.`;
}

async function offerLineErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role can view Commercial Offer lines but cannot add or update them.";
  if (response.status === 404) return "Commercial Offer or Commercial Offer line not found.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return `Could not save Commercial Offer line. HTTP ${response.status}.`;
}

async function tcClauseAttachmentErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role can view Commercial Offer T&C clauses but cannot attach or remove them.";
  if (response.status === 404) return "Commercial Offer or T&C clause attachment not found.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return `Could not save Commercial Offer T&C clause attachment. HTTP ${response.status}.`;
}

async function submissionReadinessErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role cannot view Commercial Offer submission readiness.";
  if (response.status === 404) return "Commercial Offer not found.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return `Could not load Commercial Offer submission readiness. HTTP ${response.status}.`;
}

async function submissionEvidenceErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role can view submission evidence but cannot add it.";
  if (response.status === 404) return "Commercial Offer not found.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return `Could not save submission evidence. HTTP ${response.status}.`;
}

async function creditReviewErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role can view manual credit/exposure reviews but cannot add them.";
  if (response.status === 404) return "Commercial Offer not found.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return `Could not save manual credit/exposure review. HTTP ${response.status}.`;
}

async function revisionErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role can view revision history but cannot manage revisions.";
  if (response.status === 404) return "Commercial Offer or revision record not found.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return `Could not save the revised offer. HTTP ${response.status}.`;
}

async function versionErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role can view offer versions but cannot make or abandon them.";
  if (response.status === 404) return "Commercial Offer version not found.";
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }
  return `Could not update Commercial Offer versions. HTTP ${response.status}.`;
}

async function customerResponseErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role can view customer responses but cannot record them.";
  if (response.status === 404) return "Commercial Offer not found.";
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }
  return `Could not save customer response / award outcome. HTTP ${response.status}.`;
}

async function markSubmittedErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role cannot record this Commercial Offer as submitted.";
  if (response.status === 404) return "Commercial Offer not found.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return `Could not record the Commercial Offer as submitted. HTTP ${response.status}.`;
}

function readinessStatusStyle(status: SubmissionReadiness["readiness_status"] | SubmissionReadinessItem["status"]) {
  if (status === "READY" || status === "PASS") return { color: "#065f46", background: "#ecfdf5", borderColor: "#a7f3d0" };
  if (status === "NOT_READY" || status === "BLOCKING") return { color: "#991b1b", background: "#fef2f2", borderColor: "#fecaca" };
  if (status === "DEFERRED") return { color: "#374151", background: "#f9fafb", borderColor: "#d1d5db" };
  return { color: "#92400e", background: "#fffbeb", borderColor: "#fde68a" };
}

async function commercialOfferUpdateErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role can view this Commercial Offer but cannot update it.";
  if (response.status === 404) return "Commercial Offer not found.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return `Could not update Commercial Offer. HTTP ${response.status}.`;
}

function accessMessage(access: PageAccess): string {
  if (access.status === "checking") return "Checking Commercial Offer profile access...";
  if (access.status === "no_token") return "Sign in to view this Commercial Offer profile.";
  if (access.status === "expired") return "Sign in again because the current session has expired.";
  if (access.status === "invalid_token") return "Sign in again because the current session token is not readable.";
  if (access.canWorkCommercialOffer) {
    return "You can update this offer and record its progress.";
  }
  return "You can view this offer. Your role cannot change it.";
}

function validityMessage(commercialOffer: CommercialOffer): string {
  if (!commercialOffer.valid_until) return "Validity date has not been captured yet.";

  const validUntil = new Date(`${commercialOffer.valid_until}T23:59:59`);
  if (Number.isNaN(validUntil.getTime())) return "Validity date is captured but could not be interpreted by the browser.";

  return validUntil < new Date()
    ? "The valid-until date has passed."
    : "The offer is still within its valid-until date.";
}

function hasAccountTraceability(commercialOffer: CommercialOffer | null): boolean {
  const accountPublicId = commercialOffer?.account_public_id;
  return Boolean(accountPublicId && accountPublicId.trim().length > 0);
}

function statusRequiresAccountTraceability(statusCode: string): boolean {
  return ACCOUNT_TRACEABILITY_ACTION_STATUSES.includes(statusCode as typeof ACCOUNT_TRACEABILITY_ACTION_STATUSES[number]);
}

function accountTraceabilityBlockMessage(): string {
  return "This offer's Opportunity is not linked to an Account yet. Submitting, accepting and creating a Work Order are blocked until it is.";
}

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt style={{ color: "#6b7280", fontWeight: 700 }}>{label}</dt>
      <dd style={{ margin: 0, minWidth: 0, overflowWrap: "anywhere", wordBreak: "break-word" }}>{children}</dd>
    </>
  );
}

export default function CommercialOfferDetailPage() {
  const params = useParams<{ commercialOfferId: string }>();
  const commercialOfferId = params?.commercialOfferId;
  const [commercialOffer, setCommercialOffer] = useState<CommercialOffer | null>(null);
  // Names for the linked Opportunity and Account, read through their own existing routes so the
  // page shows a customer name rather than a UUID. Display only: if a lookup fails, the
  // reference number is still shown and the link still works.
  const [linkedNames, setLinkedNames] = useState<{ opportunity: string | null; account: string | null }>({
    opportunity: null,
    account: null,
  });
  const linkedOpportunityPublicId = commercialOffer?.opportunity_public_id ?? null;
  const linkedAccountPublicId = commercialOffer?.account_public_id ?? null;
  useEffect(() => {
    let cancelled = false;
    setLinkedNames({ opportunity: null, account: null });
    const token = getToken();
    if (!token) return undefined;
    const authToken = token;
    async function readName(path: string, field: string): Promise<string | null> {
      try {
        const response = await fetch(path, { headers: { Authorization: `Bearer ${authToken}` } });
        if (!response.ok) return null;
        const body = (await response.json()) as Record<string, unknown>;
        return typeof body[field] === "string" ? (body[field] as string) : null;
      } catch {
        return null;
      }
    }
    void (async () => {
      const [opportunity, account] = await Promise.all([
        linkedOpportunityPublicId
          ? readName(`/api/opportunities/${linkedOpportunityPublicId}`, "opportunity_name")
          : Promise.resolve(null),
        linkedAccountPublicId ? readName(`/api/accounts/${linkedAccountPublicId}`, "account_name") : Promise.resolve(null),
      ]);
      if (!cancelled) setLinkedNames({ opportunity, account });
    })();
    return () => {
      cancelled = true;
    };
  }, [linkedOpportunityPublicId, linkedAccountPublicId]);
  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<CommercialOfferDetailTab>("overview");
  const [editForm, setEditForm] = useState<EditForm>(emptyEditForm());
  // CS-05a: the offer the edit form was opened from - its version and its values are what a save is judged against.
  const [editBaseline, setEditBaseline] = useState<CommercialOffer | null>(null);
  const [lastEvents, setLastEvents] = useState<CommercialOfferEvent[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [actionError, setActionError] = useState("");
  const [pageAccess, setPageAccess] = useState<PageAccess>({
    status: "checking",
    roleCodes: [],
    canViewEvents: false,
    canWorkCommercialOffer: false,
    canWorkPricingEvidence: false,
    canWorkOfferLines: false,
    canWorkTcClauses: false,
    canWorkSubmissionEvidence: false,
    canWorkCreditReview: false,
    canWorkRevisions: false,
    canWorkCustomerResponses: false,
    canCreateWorkOrder: false,
    canGenerateQuoteDocument: false,
    canApproveQuoteDocument: false,
  });
  const [pricingEvidence, setPricingEvidence] = useState<PricingEvidence[]>([]);
  const [pricingEvidenceLoading, setPricingEvidenceLoading] = useState(false);
  const [pricingEvidenceError, setPricingEvidenceError] = useState("");
  const [offerLines, setOfferLines] = useState<CommercialOfferLine[]>([]);
  const [offerLinesLoading, setOfferLinesLoading] = useState(false);
  const [offerLineSaving, setOfferLineSaving] = useState(false);
  const [offerLineForm, setOfferLineForm] = useState<OfferLineForm>(emptyOfferLineForm());
  const [editingOfferLineId, setEditingOfferLineId] = useState<string | null>(null);
  const [offerLineEditForm, setOfferLineEditForm] = useState<OfferLineForm>(emptyOfferLineForm());
  // CS-05a: the line the edit form was opened from, and the edit's own message beside its Save button.
  const [offerLineEditBaseline, setOfferLineEditBaseline] = useState<CommercialOfferLine | null>(null);
  const [offerLineEditError, setOfferLineEditError] = useState("");
  const [offerLineMessage, setOfferLineMessage] = useState("");
  const [offerLineError, setOfferLineError] = useState("");
  const [tcClauses, setTcClauses] = useState<CommercialOfferTcClause[]>([]);
  const [tcClausesLoading, setTcClausesLoading] = useState(false);
  const [tcClauseSaving, setTcClauseSaving] = useState(false);
  const [tcClauseLibraryOptions, setTcClauseLibraryOptions] = useState<TcClauseLibraryOption[]>([]);
  const [selectedTcClauseId, setSelectedTcClauseId] = useState("");
  const [tcRecommendationBasis, setTcRecommendationBasis] = useState("");
  const [tcClauseReadiness, setTcClauseReadiness] = useState<CommercialOfferTcClauseReadiness | null>(null);
  const [tcClauseReadinessLoading, setTcClauseReadinessLoading] = useState(false);
  const [tcAttachRecommendedSaving, setTcAttachRecommendedSaving] = useState(false);
  const [submissionReadiness, setSubmissionReadiness] = useState<SubmissionReadiness | null>(null);
  const [submissionReadinessLoading, setSubmissionReadinessLoading] = useState(false);
  const [submissionReadinessError, setSubmissionReadinessError] = useState("");
  const [markSubmittedSaving, setMarkSubmittedSaving] = useState(false);
  const [markSubmittedMessage, setMarkSubmittedMessage] = useState("");
  const [markSubmittedWarning, setMarkSubmittedWarning] = useState("");
  const [markSubmittedError, setMarkSubmittedError] = useState("");
  const [submissionEvidence, setSubmissionEvidence] = useState<CommercialOfferSubmissionEvidence[]>([]);
  const [submissionEvidenceLoading, setSubmissionEvidenceLoading] = useState(false);
  const [submissionEvidenceSaving, setSubmissionEvidenceSaving] = useState(false);
  const [submissionEvidenceForm, setSubmissionEvidenceForm] = useState<SubmissionEvidenceForm>(emptySubmissionEvidenceForm());
  const [submissionEvidenceMessage, setSubmissionEvidenceMessage] = useState("");
  const [submissionEvidenceError, setSubmissionEvidenceError] = useState("");
  const [creditReviews, setCreditReviews] = useState<CommercialOfferCreditReview[]>([]);
  const [creditReviewLoading, setCreditReviewLoading] = useState(false);
  const [creditReviewSaving, setCreditReviewSaving] = useState(false);
  const [creditReviewForm, setCreditReviewForm] = useState<CreditReviewForm>(emptyCreditReviewForm());
  const [creditReviewMessage, setCreditReviewMessage] = useState("");
  const [creditReviewError, setCreditReviewError] = useState("");
  const [offerVersions, setOfferVersions] = useState<CommercialOffer[]>([]);
  const [offerVersionsLoading, setOfferVersionsLoading] = useState(false);
  const [offerVersionsError, setOfferVersionsError] = useState("");
  const [versionForm, setVersionForm] = useState<VersionForm>(emptyVersionForm());
  const [versionCreating, setVersionCreating] = useState(false);
  const [versionCreateMessage, setVersionCreateMessage] = useState("");
  const [versionCreateError, setVersionCreateError] = useState("");
  const [createdVersionPublicId, setCreatedVersionPublicId] = useState<string | null>(null);
  const [versionAbandoningId, setVersionAbandoningId] = useState<string | null>(null);
  const [versionActionMessages, setVersionActionMessages] = useState<Record<string, string>>({});
  const [versionActionErrors, setVersionActionErrors] = useState<Record<string, string>>({});
  const [revisions, setRevisions] = useState<CommercialOfferRevision[]>([]);
  const [revisionsLoading, setRevisionsLoading] = useState(false);
  const [revisionActionSavingId, setRevisionActionSavingId] = useState<string | null>(null);
  const [revisionLoadError, setRevisionLoadError] = useState("");
  const [revisionActionMessages, setRevisionActionMessages] = useState<Record<string, string>>({});
  const [revisionActionErrors, setRevisionActionErrors] = useState<Record<string, string>>({});
  const [revisionResubmissionEvidenceIds, setRevisionResubmissionEvidenceIds] = useState<Record<string, string>>({});
  const [customerResponses, setCustomerResponses] = useState<CommercialOfferCustomerResponse[]>([]);
  const [customerResponsesLoading, setCustomerResponsesLoading] = useState(false);
  const [customerResponseSaving, setCustomerResponseSaving] = useState(false);
  const [customerResponseForm, setCustomerResponseForm] = useState<CustomerResponseForm>(emptyCustomerResponseForm());
  const [customerResponseMessage, setCustomerResponseMessage] = useState("");
  const [customerResponseError, setCustomerResponseError] = useState("");
  const [lifecycleGuidance, setLifecycleGuidance] = useState<CommercialOfferLifecycleGuidance | null>(null);
  const [lifecycleGuidanceLoading, setLifecycleGuidanceLoading] = useState(false);
  const [lifecycleGuidanceError, setLifecycleGuidanceError] = useState("");
  const [quoteDocuments, setQuoteDocuments] = useState<CommercialOfferQuoteDocument[]>([]);
  const [quoteDocumentsLoading, setQuoteDocumentsLoading] = useState(false);
  const [quoteDocumentsError, setQuoteDocumentsError] = useState("");
  const [quoteDocumentGenerating, setQuoteDocumentGenerating] = useState(false);
  const [quoteDocumentGenerateMessage, setQuoteDocumentGenerateMessage] = useState("");
  const [quoteDocumentGenerateError, setQuoteDocumentGenerateError] = useState("");
  const [quoteDocumentApprovingId, setQuoteDocumentApprovingId] = useState<string | null>(null);
  const [quoteDocumentApproveMessages, setQuoteDocumentApproveMessages] = useState<Record<string, string>>({});
  const [quoteDocumentApproveErrors, setQuoteDocumentApproveErrors] = useState<Record<string, string>>({});
  const [quoteDocumentDownloadErrors, setQuoteDocumentDownloadErrors] = useState<Record<string, string>>({});
  const [expandedTcClauseId, setExpandedTcClauseId] = useState<string | null>(null);
  const [tcClauseMessage, setTcClauseMessage] = useState("");
  const [tcClauseError, setTcClauseError] = useState("");
  const [tcRecommendedMessage, setTcRecommendedMessage] = useState("");
  const [tcRecommendedError, setTcRecommendedError] = useState("");
  const [linkedWorkOrders, setLinkedWorkOrders] = useState<WorkOrder[]>([]);
  const [linkedWorkOrdersLoading, setLinkedWorkOrdersLoading] = useState(false);
  const [linkedWorkOrderError, setLinkedWorkOrderError] = useState("");
  const [relatedOffers, setRelatedOffers] = useState<CommercialOffer[]>([]);
  const [relatedOffersLoading, setRelatedOffersLoading] = useState(false);
  const [relatedOffersError, setRelatedOffersError] = useState("");
  const [linkedAmendments, setLinkedAmendments] = useState<WorkOrderAmendmentSummary[]>([]);
  const [linkedAmendmentsLoading, setLinkedAmendmentsLoading] = useState(false);
  const [linkedAmendmentsError, setLinkedAmendmentsError] = useState("");
  const [returnTarget, setReturnTarget] = useState<ReturnTarget>({
    href: "/commercial-offers",
    label: "Back to Commercial Offers",
  });
  const currentOpenRevision = useMemo(
    () => revisions.find((revision) => revision.revision_status === "OPEN") ?? null,
    [revisions],
  );
  const latestCustomerResponse = customerResponses[0] ?? null;
  // Slice 9B: whether another customer response may be recorded is decided by the backend
  // (`can_record_customer_response`), never by a status list duplicated here - the list that
  // used to live in this file had already drifted from the contract.
  //
  // Four states, because lifecycleGuidance being null means two different things. While it is
  // still loading, showing an enabled form would offer to record a response against an offer
  // that may be final. Once the request has failed, saying "checking..." misreports a finished
  // failure as still in progress and offers no way to recover. Both block the form - failing
  // closed is right - but they must say different things.
  const customerResponseCapability: "loading" | "failed" | "allowed" | "blocked" =
    lifecycleGuidance !== null
      ? lifecycleGuidance.can_record_customer_response
        ? "allowed"
        : "blocked"
      : lifecycleGuidanceLoading || !lifecycleGuidanceError
        ? "loading"
        : "failed";
  const selectedCustomerResponseEvidence = submissionEvidence.find(
    (item) => item.public_id === customerResponseForm.linked_submission_evidence_public_id,
  ) ?? null;
  const selectedCustomerResponseRevision = revisions.find(
    (item) => item.public_id === customerResponseForm.linked_revision_public_id,
  ) ?? null;

  async function loadTcClauses(publicId: string, tokenOverride?: string) {
    setTcClauseMessage("");
    setTcClauseError("");
    setTcRecommendedMessage("");
    setTcRecommendedError("");

    const token = tokenOverride ?? getToken();
    if (!token) {
      setTcClauses([]);
      return;
    }

    setTcClausesLoading(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_TC_CLAUSES_BASE_PATH}/${encodeURIComponent(publicId)}/tc-clauses`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setTcClauses([]);
      setTcClauseError("Network error while loading Commercial Offer T&C clauses.");
      setTcClausesLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setTcClauses([]);
      setTcClauseError(await tcClauseAttachmentErrorMessage(response));
      setTcClausesLoading(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferTcClause[];
    setTcClauses(data);
    setTcClausesLoading(false);
  }

  async function loadTcClauseReadiness(publicId: string, tokenOverride?: string, basisOverride?: string) {
    setTcRecommendedError("");

    const token = tokenOverride ?? getToken();
    if (!token) {
      setTcClauseReadiness(null);
      return;
    }

    const basis = basisOverride ?? tcRecommendationBasis;
    const query = basis ? `?recommendation_basis=${encodeURIComponent(basis)}` : "";
    setTcClauseReadinessLoading(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_TC_CLAUSES_BASE_PATH}/${encodeURIComponent(publicId)}/tc-clause-readiness${query}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setTcClauseReadiness(null);
      setTcRecommendedError("Network error while loading Commercial Offer T&C readiness.");
      setTcClauseReadinessLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setTcClauseReadiness(null);
      setTcRecommendedError(await tcClauseAttachmentErrorMessage(response));
      setTcClauseReadinessLoading(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferTcClauseReadiness;
    setTcClauseReadiness(data);
    setTcClauseReadinessLoading(false);
  }

  async function loadSubmissionReadiness(publicId: string, tokenOverride?: string, basisOverride?: string) {
    setSubmissionReadinessError("");

    const token = tokenOverride ?? getToken();
    if (!token) {
      setSubmissionReadiness(null);
      return;
    }

    const basis = basisOverride ?? tcRecommendationBasis;
    const query = basis ? `?recommendation_basis=${encodeURIComponent(basis)}` : "";
    setSubmissionReadinessLoading(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_DETAIL_BASE_PATH}/${encodeURIComponent(publicId)}/submission-readiness${query}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setSubmissionReadiness(null);
      setSubmissionReadinessError("Network error while loading Commercial Offer submission readiness.");
      setSubmissionReadinessLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setSubmissionReadiness(null);
      setSubmissionReadinessError(await submissionReadinessErrorMessage(response));
      setSubmissionReadinessLoading(false);
      return;
    }

    const data = (await response.json()) as SubmissionReadiness;
    setSubmissionReadiness(data);
    setSubmissionReadinessLoading(false);
  }

  async function loadSubmissionEvidence(publicId: string, tokenOverride?: string) {
    setSubmissionEvidenceMessage("");
    setSubmissionEvidenceError("");
    setRevisionLoadError("");
    setRevisionActionMessages({});
    setRevisionActionErrors({});
    setCreditReviewMessage("");
    setCreditReviewError("");

    const token = tokenOverride ?? getToken();
    if (!token) {
      setSubmissionEvidence([]);
      setRevisions([]);
      setCreditReviews([]);
      return;
    }

    setSubmissionEvidenceLoading(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_BASE_PATH}/${encodeURIComponent(publicId)}/submission-evidence`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setSubmissionEvidence([]);
      setRevisions([]);
      setCreditReviews([]);
      setSubmissionEvidenceError("Network error while loading submission evidence.");
      setSubmissionEvidenceLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setSubmissionEvidence([]);
      setSubmissionEvidenceError(await submissionEvidenceErrorMessage(response));
      setSubmissionEvidenceLoading(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferSubmissionEvidence[];
    setSubmissionEvidence(data);
    setSubmissionEvidenceLoading(false);
  }

  async function loadCreditReviews(publicId: string, tokenOverride?: string) {
    setCreditReviewMessage("");
    setCreditReviewError("");

    const token = tokenOverride ?? getToken();
    if (!token) {
      setCreditReviews([]);
      return;
    }

    setCreditReviewLoading(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_CREDIT_REVIEW_BASE_PATH}/${encodeURIComponent(publicId)}/credit-review`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setCreditReviews([]);
      setCreditReviewError("Network error while loading manual credit/exposure reviews.");
      setCreditReviewLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setCreditReviews([]);
      setCreditReviewError(await creditReviewErrorMessage(response));
      setCreditReviewLoading(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferCreditReview[];
    setCreditReviews(data);
    setCreditReviewLoading(false);
  }

  async function loadOfferVersions(publicId: string, tokenOverride?: string) {
    setOfferVersionsError("");
    const token = tokenOverride ?? getToken();
    if (!token) {
      setOfferVersions([]);
      return;
    }
    setOfferVersionsLoading(true);
    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_VERSION_BASE_PATH}/${encodeURIComponent(publicId)}/versions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setOfferVersions([]);
      setOfferVersionsError("Network error while loading Commercial Offer versions.");
      setOfferVersionsLoading(false);
      return;
    }
    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setOfferVersions([]);
      setOfferVersionsError(await versionErrorMessage(response));
      setOfferVersionsLoading(false);
      return;
    }
    setOfferVersions((await response.json()) as CommercialOffer[]);
    setOfferVersionsLoading(false);
  }

  async function loadRevisions(publicId: string, tokenOverride?: string) {
    setRevisionLoadError("");

    const token = tokenOverride ?? getToken();
    if (!token) {
      setRevisions([]);
      return;
    }

    setRevisionsLoading(true);
    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_REVISION_BASE_PATH}/${encodeURIComponent(publicId)}/revisions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setRevisions([]);
      setRevisionLoadError("Network error while loading revised offers.");
      setRevisionsLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setRevisions([]);
      setRevisionLoadError(await revisionErrorMessage(response));
      setRevisionsLoading(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferRevision[];
    setRevisions(data);
    setRevisionResubmissionEvidenceIds((current) => {
      const next = { ...current };
      for (const revision of data) {
        if (!next[revision.public_id] && submissionEvidence[0]?.public_id) {
          next[revision.public_id] = submissionEvidence[0].public_id;
        }
      }
      return next;
    });
    setRevisionsLoading(false);
  }

  async function loadCustomerResponses(publicId: string, tokenOverride?: string) {
    setCustomerResponseError("");
    const token = tokenOverride ?? getToken();
    if (!token) {
      setCustomerResponses([]);
      return;
    }
    setCustomerResponsesLoading(true);
    let response: Response;
    try {
      response = await fetch(
        `${COMMERCIAL_OFFER_CUSTOMER_RESPONSE_BASE_PATH}/${encodeURIComponent(publicId)}/customer-responses`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
    } catch {
      setCustomerResponses([]);
      setCustomerResponseError("Network error while loading customer response / award outcome history.");
      setCustomerResponsesLoading(false);
      return;
    }
    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setCustomerResponses([]);
      setCustomerResponseError(await customerResponseErrorMessage(response));
      setCustomerResponsesLoading(false);
      return;
    }
    setCustomerResponses((await response.json()) as CommercialOfferCustomerResponse[]);
    setCustomerResponsesLoading(false);
  }

  async function loadLifecycleGuidance(publicId: string, tokenOverride?: string) {
    // Every exit path must leave the capability in a state the UI can render. Two used not to:
    // the no-token branch cleared the error and returned, and JSON decoding on the success path
    // sat outside the try, so a malformed body threw before the loading flag was cleared. Either
    // left the Customer Response section saying "Checking..." forever with no way to recover.
    setLifecycleGuidanceError("");
    const token = tokenOverride ?? getToken();
    if (!token) {
      setLifecycleGuidance(null);
      setLifecycleGuidanceLoading(false);
      setLifecycleGuidanceError("Your session has ended. Sign in again to load lifecycle guidance.");
      return;
    }
    setLifecycleGuidanceLoading(true);
    try {
      const response = await fetch(
        `${COMMERCIAL_OFFER_LIFECYCLE_GUIDANCE_BASE_PATH}/${encodeURIComponent(publicId)}/lifecycle-guidance`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!response.ok) {
        if (response.status === 401) clearPrototypeSession();
        setLifecycleGuidance(null);
        setLifecycleGuidanceError(`Post-response lifecycle guidance could not be loaded. HTTP ${response.status}.`);
        return;
      }
      // Inside the try on purpose: an empty or malformed body throws here.
      setLifecycleGuidance((await response.json()) as CommercialOfferLifecycleGuidance);
    } catch {
      setLifecycleGuidance(null);
      setLifecycleGuidanceError(
        "Post-response lifecycle guidance could not be loaded. The request failed or returned an unreadable response.",
      );
    } finally {
      setLifecycleGuidanceLoading(false);
    }
  }

  async function loadQuoteDocuments(publicId: string, tokenOverride?: string) {
    setQuoteDocumentsError("");
    const token = tokenOverride ?? getToken();
    if (!token) {
      setQuoteDocuments([]);
      return;
    }
    setQuoteDocumentsLoading(true);
    try {
      const response = await fetch(
        `${COMMERCIAL_OFFER_QUOTE_DOCUMENTS_BASE_PATH}/${encodeURIComponent(publicId)}/quote-documents`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!response.ok) {
        if (response.status === 401) clearPrototypeSession();
        setQuoteDocuments([]);
        setQuoteDocumentsError(`Quotation documents could not be loaded. HTTP ${response.status}.`);
        return;
      }
      setQuoteDocuments((await response.json()) as CommercialOfferQuoteDocument[]);
    } catch {
      setQuoteDocuments([]);
      setQuoteDocumentsError("Network error while loading quotation documents.");
    } finally {
      setQuoteDocumentsLoading(false);
    }
  }

  async function handleGenerateQuoteDocument() {
    setQuoteDocumentGenerateMessage("");
    setQuoteDocumentGenerateError("");
    setLastEvents([]);

    if (!commercialOffer) {
      setQuoteDocumentGenerateError("Load a Commercial Offer before generating a quotation document.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canGenerateQuoteDocument) {
      setQuoteDocumentGenerateError("Your role can view quotation documents but cannot generate one.");
      return;
    }

    const token = getToken();
    if (!token) {
      setQuoteDocumentGenerateError(SIGN_IN_FIRST);
      return;
    }

    setQuoteDocumentGenerating(true);

    let response: Response;
    try {
      response = await fetch(
        `${COMMERCIAL_OFFER_QUOTE_DOCUMENTS_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/quote-documents`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      );
    } catch {
      setQuoteDocumentGenerateError("Network error while generating the quotation document.");
      setQuoteDocumentGenerating(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      const text = await response.text();
      setQuoteDocumentGenerateError(`Could not generate quotation document. HTTP ${response.status}. ${text}`);
      setQuoteDocumentGenerating(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferQuoteDocumentGeneratedResponse;
    setLastEvents(data.event ? [data.event] : []);
    setQuoteDocumentGenerateMessage(`Quotation document ${data.quote_document.quote_reference} generated as Draft.`);
    setQuoteDocumentGenerating(false);
    await loadQuoteDocuments(commercialOffer.public_id, token);
    await loadSubmissionReadiness(commercialOffer.public_id, token);
  }

  async function handleApproveQuoteDocument(quoteDocumentPublicId: string) {
    setQuoteDocumentApproveMessages((prev) => ({ ...prev, [quoteDocumentPublicId]: "" }));
    setQuoteDocumentApproveErrors((prev) => ({ ...prev, [quoteDocumentPublicId]: "" }));
    setLastEvents([]);

    if (!commercialOffer) {
      setQuoteDocumentApproveErrors((prev) => ({
        ...prev,
        [quoteDocumentPublicId]: "Load a Commercial Offer before approving a quotation document.",
      }));
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canApproveQuoteDocument) {
      setQuoteDocumentApproveErrors((prev) => ({
        ...prev,
        [quoteDocumentPublicId]: "Your role can view quotation documents but cannot approve one for issue.",
      }));
      return;
    }

    const token = getToken();
    if (!token) {
      setQuoteDocumentApproveErrors((prev) => ({
        ...prev,
        [quoteDocumentPublicId]: SIGN_IN_FIRST,
      }));
      return;
    }

    setQuoteDocumentApprovingId(quoteDocumentPublicId);

    let response: Response;
    try {
      response = await fetch(
        `${COMMERCIAL_OFFER_QUOTE_DOCUMENTS_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/quote-documents/${encodeURIComponent(quoteDocumentPublicId)}/approve`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({}),
        },
      );
    } catch {
      setQuoteDocumentApproveErrors((prev) => ({
        ...prev,
        [quoteDocumentPublicId]: "Network error while approving the quotation document.",
      }));
      setQuoteDocumentApprovingId(null);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      const text = await response.text();
      setQuoteDocumentApproveErrors((prev) => ({
        ...prev,
        [quoteDocumentPublicId]: `Could not approve. HTTP ${response.status}. ${text}`,
      }));
      setQuoteDocumentApprovingId(null);
      return;
    }

    const data = (await response.json()) as CommercialOfferQuoteDocumentApprovedResponse;
    setLastEvents(data.event ? [data.event] : []);
    setQuoteDocumentApproveMessages((prev) => ({
      ...prev,
      [quoteDocumentPublicId]: `Approved for issue: ${data.quote_document.quote_reference}.`,
    }));
    setQuoteDocumentApprovingId(null);
    await loadQuoteDocuments(commercialOffer.public_id, token);
    await loadSubmissionReadiness(commercialOffer.public_id, token);
  }

  async function downloadQuoteDocument(quoteDocument: CommercialOfferQuoteDocument) {
    setQuoteDocumentDownloadErrors((prev) => ({ ...prev, [quoteDocument.public_id]: "" }));
    const token = getToken();
    if (!token) {
      setQuoteDocumentDownloadErrors((prev) => ({
        ...prev,
        [quoteDocument.public_id]: SIGN_IN_FIRST,
      }));
      return;
    }

    let response: Response;
    try {
      response = await fetch(`${DOCUMENTS_CONTENT_BASE_PATH}/${quoteDocument.document_public_id}/content`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (error) {
      setQuoteDocumentDownloadErrors((prev) => ({ ...prev, [quoteDocument.public_id]: `Network error: ${error}` }));
      return;
    }

    if (!response.ok) {
      const text = await response.text();
      setQuoteDocumentDownloadErrors((prev) => ({
        ...prev,
        [quoteDocument.public_id]: `Could not download. HTTP ${response.status}. ${text}`,
      }));
      return;
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = `${quoteDocument.quote_reference.replace(/\//g, "-")}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(objectUrl);
  }

  async function loadTcClauseLibraryOptions(tokenOverride?: string) {
    setTcClauseError("");

    const token = tokenOverride ?? getToken();
    if (!token) {
      setTcClauseLibraryOptions([]);
      return;
    }

    let response: Response;
    try {
      response = await fetch(`${TC_CLAUSE_LIBRARY_BASE_PATH}?limit=100&active=true&applies_to_header=true`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setTcClauseLibraryOptions([]);
      setTcClauseError("Network error while loading attachable T&C library clauses.");
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setTcClauseLibraryOptions([]);
      setTcClauseError(`Attachable T&C library clauses could not be loaded. HTTP ${response.status}.`);
      return;
    }

    const data = (await response.json()) as TcClauseLibraryOption[];
    setTcClauseLibraryOptions(data);
    setSelectedTcClauseId((current) => current || data[0]?.public_id || "");
  }

  async function loadOfferLines(publicId: string, tokenOverride?: string) {
    setOfferLineMessage("");
    setOfferLineError("");

    const token = tokenOverride ?? getToken();
    if (!token) {
      setOfferLines([]);
      return;
    }

    setOfferLinesLoading(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_LINES_BASE_PATH}/${encodeURIComponent(publicId)}/lines`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setOfferLines([]);
      setOfferLineError("Network error while loading Commercial Offer lines.");
      setOfferLinesLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setOfferLines([]);
      setOfferLineError(await offerLineErrorMessage(response));
      setOfferLinesLoading(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferLine[];
    setOfferLines(data);
    setOfferLinesLoading(false);
  }

  async function loadLinkedWorkOrders(publicId: string, tokenOverride?: string) {
    setLinkedWorkOrderError("");

    const token = tokenOverride ?? getToken();
    if (!token) {
      setLinkedWorkOrders([]);
      return;
    }

    setLinkedWorkOrdersLoading(true);

    let response: Response;
    try {
      response = await fetch(`${WORK_ORDER_LIST_BASE_PATH}?limit=100&commercial_offer_public_id=${encodeURIComponent(publicId)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setLinkedWorkOrders([]);
      setLinkedWorkOrderError("Network error while loading this offer's Work Orders.");
      setLinkedWorkOrdersLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setLinkedWorkOrders([]);
      setLinkedWorkOrderError(`This offer's Work Orders could not be loaded. HTTP ${response.status}.`);
      setLinkedWorkOrdersLoading(false);
      return;
    }

    const data = (await response.json()) as WorkOrder[];
    setLinkedWorkOrders(data);
    setLinkedWorkOrdersLoading(false);
  }

  async function loadRelatedOffers(publicId: string, tokenOverride?: string) {
    setRelatedOffersError("");

    const token = tokenOverride ?? getToken();
    if (!token) {
      setRelatedOffers([]);
      return;
    }

    setRelatedOffersLoading(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_DETAIL_BASE_PATH}/${encodeURIComponent(publicId)}/related-offers`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setRelatedOffers([]);
      setRelatedOffersError("Network error while loading related Commercial Offers.");
      setRelatedOffersLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setRelatedOffers([]);
      setRelatedOffersError(`Related Commercial Offers could not be loaded. HTTP ${response.status}.`);
      setRelatedOffersLoading(false);
      return;
    }

    const data = (await response.json()) as CommercialOffer[];
    setRelatedOffers(data);
    setRelatedOffersLoading(false);
  }

  async function loadLinkedAmendments(offer: CommercialOffer, tokenOverride?: string) {
    setLinkedAmendmentsError("");
    setLinkedAmendments([]);

    if (offer.offer_purpose === "BASE" || !offer.related_work_order_public_id) {
      return;
    }

    const token = tokenOverride ?? getToken();
    if (!token) return;

    setLinkedAmendmentsLoading(true);
    try {
      const response = await fetch(
        `${WORK_ORDER_LIST_BASE_PATH}/${encodeURIComponent(offer.related_work_order_public_id)}/amendments`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!response.ok) {
        if (response.status === 401) clearPrototypeSession();
        setLinkedAmendmentsError(`Linked Work Order Amendments could not be loaded. HTTP ${response.status}.`);
        return;
      }
      const data = (await response.json()) as WorkOrderAmendmentSummary[];
      setLinkedAmendments(data.filter((amendment) => amendment.related_commercial_offer_public_id === offer.public_id));
    } catch {
      setLinkedAmendmentsError("Network error while loading linked Work Order Amendments.");
    } finally {
      setLinkedAmendmentsLoading(false);
    }
  }

  async function loadPricingEvidence(publicId: string, tokenOverride?: string) {
    setPricingEvidenceError("");
    setOfferLineMessage("");
    setOfferLineError("");

    const token = tokenOverride ?? getToken();
    if (!token) {
      setPricingEvidence([]);
      return;
    }

    setPricingEvidenceLoading(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_PRICING_EVIDENCE_BASE_PATH}/${encodeURIComponent(publicId)}/pricing-evidence`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setPricingEvidence([]);
      setPricingEvidenceError("Network error while loading pricing evidence.");
      setPricingEvidenceLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setPricingEvidence([]);
      setPricingEvidenceError(await pricingEvidenceErrorMessage(response));
      setPricingEvidenceLoading(false);
      return;
    }

    const data = (await response.json()) as PricingEvidence[];
    setPricingEvidence(data);
    setPricingEvidenceLoading(false);
  }

  // After the server refuses a market-rate change (Slice 4G, review 4G-R3-002) the offer may have been sent or a line
  // cancelled meanwhile: read the offer's status and lines again, with its rates and readiness, keeping the page's
  // messages.
  async function refreshOfferContent(publicId: string) {
    const token = getToken();
    if (!token) return;
    try {
      const response = await fetch(`${COMMERCIAL_OFFER_DETAIL_BASE_PATH}/${encodeURIComponent(publicId)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) setCommercialOffer((await response.json()) as CommercialOffer);
    } catch {
      // The offer stays as shown; the reloads below still run.
    }
    await loadOfferLines(publicId, token);
    await loadPricingEvidence(publicId, token);
    await loadSubmissionReadiness(publicId, token);
  }

  async function loadCommercialOffer(publicId: string) {
    setMessage("");
    setError("");
    // Quotation-document feedback is per offer. Without this, generating or approving on one
    // offer left its confirmation visible after navigating to a different offer - the stale
    // action-feedback problem UI_UX_CARRY_FORWARD.md already calls out. Cleared here, at the
    // start of loading an offer, rather than inside loadQuoteDocuments, because the approve and
    // generate handlers reload the list immediately after setting their success message and
    // clearing there would wipe the confirmation the user needs to see.
    setQuoteDocumentGenerateMessage("");
    setQuoteDocumentGenerateError("");
    setQuoteDocumentApproveMessages({});
    setQuoteDocumentApproveErrors({});
    setQuoteDocumentDownloadErrors({});
    setActionMessage("");
    setActionError("");
    setPricingEvidenceError("");
    setTcClauseMessage("");
    setTcClauseError("");
    setTcRecommendedMessage("");
    setTcRecommendedError("");
    setSubmissionReadinessError("");
    setSubmissionEvidenceMessage("");
    setSubmissionEvidenceError("");
    setMarkSubmittedMessage("");
    setMarkSubmittedWarning("");
    setMarkSubmittedError("");
    setLinkedWorkOrderError("");

    const access = readPageAccess();
    setPageAccess(access);

    const token = getToken();
    if (!token) {
      setCommercialOffer(null);
      setPricingEvidence([]);
      setOfferLines([]);
      setTcClauses([]);
      setTcClauseReadiness(null);
      setSubmissionReadiness(null);
      setSubmissionEvidence([]);
      setCustomerResponses([]);
      setLifecycleGuidance(null);
      setOfferVersions([]);
      setQuoteDocuments([]);
      setLinkedWorkOrders([]);
      setRelatedOffers([]);
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_DETAIL_BASE_PATH}/${encodeURIComponent(publicId)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setCommercialOffer(null);
      setError("Network error while loading this Commercial Offer. Check that the backend and frontend services are running.");
      setLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setCommercialOffer(null);
      setPricingEvidence([]);
      setOfferLines([]);
      setTcClauses([]);
      setTcClauseReadiness(null);
      setSubmissionReadiness(null);
      setSubmissionEvidence([]);
      setCustomerResponses([]);
      setLifecycleGuidance(null);
      setOfferVersions([]);
      setQuoteDocuments([]);
      setLinkedWorkOrders([]);
      setRelatedOffers([]);
      setLinkedAmendments([]);
      setError(commercialOfferDetailErrorMessage(response.status));
      setLoading(false);
      return;
    }

    const data = (await response.json()) as CommercialOffer;
    setCommercialOffer(data);
    setEditFormFrom(data);
    await loadOfferLines(data.public_id, token);
    await loadTcClauses(data.public_id, token);
    await loadTcClauseReadiness(data.public_id, token);
    await loadSubmissionReadiness(data.public_id, token);
    await loadSubmissionEvidence(data.public_id, token);
    await loadCreditReviews(data.public_id, token);
    await loadOfferVersions(data.public_id, token);
    await loadRevisions(data.public_id, token);
    await loadCustomerResponses(data.public_id, token);
    await loadLifecycleGuidance(data.public_id, token);
    await loadQuoteDocuments(data.public_id, token);
    await loadTcClauseLibraryOptions(token);
    await loadPricingEvidence(data.public_id, token);
    await loadLinkedWorkOrders(data.public_id, token);
    await loadRelatedOffers(data.public_id, token);
    await loadLinkedAmendments(data, token);
    setLoading(false);
  }

  useEffect(() => {
    function refreshAccess() {
      setPageAccess(readPageAccess());
    }

    setReturnTarget(readSafeReturnTarget("/commercial-offers", "Back to Commercial Offers"));
    refreshAccess();

    if (typeof commercialOfferId === "string" && commercialOfferId.trim().length > 0) {
      void loadCommercialOffer(commercialOfferId);
    }

    window.addEventListener(SESSION_CHANGED_EVENT, refreshAccess);
    window.addEventListener("storage", refreshAccess);
    window.addEventListener("focus", refreshAccess);

    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, refreshAccess);
      window.removeEventListener("storage", refreshAccess);
      window.removeEventListener("focus", refreshAccess);
    };
  }, [commercialOfferId]);

  async function handleAttachTcClause(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTcClauseMessage("");
    setTcClauseError("");
    setTcRecommendedMessage("");
    setTcRecommendedError("");
    setLastEvents([]);

    if (!commercialOffer) {
      setTcClauseError("Load a Commercial Offer before attaching T&C clauses.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkTcClauses) {
      setTcClauseError("Your role can view Commercial Offer T&C clauses but cannot attach or remove them.");
      return;
    }

    if (!selectedTcClauseId) {
      setTcClauseError("Select a T&C library clause to attach.");
      return;
    }

    const token = getToken();
    if (!token) {
      setTcClauseError(SIGN_IN_FIRST);
      return;
    }

    setTcClauseSaving(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_TC_CLAUSES_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/tc-clauses`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ clause_public_ids: [selectedTcClauseId] }),
      });
    } catch {
      setTcClauseError("Network error while attaching the T&C clause.");
      setTcClauseSaving(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setTcClauseError(await tcClauseAttachmentErrorMessage(response));
      setTcClauseSaving(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferTcClauseAttachedResponse;
    setLastEvents(data.events ?? []);
    await loadTcClauses(commercialOffer.public_id, token);
    await loadTcClauseReadiness(commercialOffer.public_id, token);
    await loadSubmissionReadiness(commercialOffer.public_id, token);
    setTcClauseMessage("T&C clause attached. The snapshot is preserved on this Commercial Offer.");
    setTcClauseSaving(false);
  }

  async function handleAttachRecommendedTcClauses() {
    setTcRecommendedMessage("");
    setTcRecommendedError("");
    setLastEvents([]);

    if (!commercialOffer) {
      setTcRecommendedError("Load a Commercial Offer before attaching recommended T&C clauses.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkTcClauses) {
      setTcRecommendedError("Your role can view Commercial Offer T&C clauses but cannot attach or remove them.");
      return;
    }

    if (!tcRecommendationBasis) {
      setTcRecommendedError("Select a recommendation basis before attaching recommended clauses.");
      return;
    }

    const token = getToken();
    if (!token) {
      setTcRecommendedError(SIGN_IN_FIRST);
      return;
    }

    setTcAttachRecommendedSaving(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_TC_CLAUSES_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/tc-clauses/attach-recommended`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ recommendation_basis: tcRecommendationBasis }),
      });
    } catch {
      setTcRecommendedError("Network error while attaching recommended T&C clauses.");
      setTcAttachRecommendedSaving(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setTcRecommendedError(await tcClauseAttachmentErrorMessage(response));
      setTcAttachRecommendedSaving(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferTcClauseAttachRecommendedResponse;
    setLastEvents(data.events ?? []);
    setTcClauseReadiness(data.readiness);
    await loadTcClauses(commercialOffer.public_id, token);
    await loadSubmissionReadiness(commercialOffer.public_id, token);
    setTcRecommendedMessage(data.status_text);
    setTcAttachRecommendedSaving(false);
  }

  async function handleRemoveTcClause(attachment: CommercialOfferTcClause) {
    setTcClauseMessage("");
    setTcClauseError("");
    setTcRecommendedMessage("");
    setTcRecommendedError("");
    setLastEvents([]);

    if (!commercialOffer) {
      setTcClauseError("Load a Commercial Offer before removing T&C clauses.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkTcClauses) {
      setTcClauseError("Your role can view Commercial Offer T&C clauses but cannot attach or remove them.");
      return;
    }

    const token = getToken();
    if (!token) {
      setTcClauseError(SIGN_IN_FIRST);
      return;
    }

    setTcClauseSaving(true);

    let response: Response;
    try {
      response = await fetch(
        `${COMMERCIAL_OFFER_TC_CLAUSES_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/tc-clauses/${encodeURIComponent(attachment.public_id)}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        },
      );
    } catch {
      setTcClauseError("Network error while removing the T&C clause.");
      setTcClauseSaving(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setTcClauseError(await tcClauseAttachmentErrorMessage(response));
      setTcClauseSaving(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferTcClauseRemovedResponse;
    setLastEvents(data.event ? [data.event] : []);
    setExpandedTcClauseId((current) => (current === attachment.public_id ? null : current));
    await loadTcClauses(commercialOffer.public_id, token);
    await loadTcClauseReadiness(commercialOffer.public_id, token);
    await loadSubmissionReadiness(commercialOffer.public_id, token);
    setTcClauseMessage("T&C clause removed from the active Commercial Offer attachment list.");
    setTcClauseSaving(false);
  }

  async function handleAddOfferLine(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOfferLineMessage("");
    setOfferLineError("");
    setLastEvents([]);

    if (!commercialOffer) {
      setOfferLineError("Load a Commercial Offer before adding a line.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkOfferLines) {
      setOfferLineError("Your role can view Commercial Offer lines but cannot add or update them.");
      return;
    }

    if (!offerLineForm.scope_description.trim()) {
      setOfferLineError("Scope / service description is required.");
      return;
    }

    const quantity = offerLineForm.quantity.trim();
    if (!quantity || Number(quantity) <= 0) {
      setOfferLineError("Quantity is required and must be greater than zero.");
      return;
    }

    const rateAmount = offerLineForm.rate_amount.trim();
    if (rateAmount.length > 0 && Number(rateAmount) < 0) {
      setOfferLineError("Rate amount cannot be negative.");
      return;
    }

    if (!offerLineForm.uom.trim()) {
      setOfferLineError("UOM is required.");
      return;
    }

    const currencyCode = offerLineForm.currency_code.trim().toUpperCase();
    if (!isOperatingCurrency(currencyCode)) {
      setOfferLineError(UNSUPPORTED_CURRENCY_MESSAGE);
      return;
    }

    const token = getToken();
    if (!token) {
      setOfferLineError(SIGN_IN_FIRST);
      return;
    }

    setOfferLineSaving(true);

    const payload = {
      line_number: offerLineForm.line_number.trim() ? Number(offerLineForm.line_number.trim()) : null,
      scope_description: offerLineForm.scope_description.trim(),
      equipment_service_category: normalizeOptional(offerLineForm.equipment_service_category),
      quantity,
      uom: offerLineForm.uom.trim(),
      rate_amount: normalizeOptional(offerLineForm.rate_amount),
      currency_code: currencyCode,
      remarks: normalizeOptional(offerLineForm.remarks),
    };

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_LINES_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/lines`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setOfferLineError("Network error while adding the Commercial Offer line.");
      setOfferLineSaving(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setOfferLineError(await offerLineErrorMessage(response));
      setOfferLineSaving(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferLineCreatedResponse;
    setLastEvents(data.event ? [data.event] : []);
    setOfferLineForm(emptyOfferLineForm());
    setOfferLineMessage("Commercial Offer line saved. The list below has been refreshed.");
    await loadOfferLines(commercialOffer.public_id, token);
    await loadSubmissionReadiness(commercialOffer.public_id, token);
    setOfferLineSaving(false);
  }

  function startEditingOfferLine(line: CommercialOfferLine) {
    setEditingOfferLineId(line.public_id);
    setOfferLineEditForm(formFromOfferLine(line));
    setOfferLineEditBaseline(line);
    setOfferLineEditError("");
    setOfferLineMessage("");
    setOfferLineError("");
    setLastEvents([]);
  }

  function cancelEditingOfferLine() {
    setEditingOfferLineId(null);
    setOfferLineEditForm(emptyOfferLineForm());
    setOfferLineEditBaseline(null);
    setOfferLineEditError("");
    setOfferLineError("");
  }

  async function handleUpdateOfferLine(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOfferLineMessage("");
    setOfferLineError("");
    setOfferLineEditError("");
    setLastEvents([]);

    if (!commercialOffer || !editingOfferLineId || !offerLineEditBaseline) {
      setOfferLineEditError("Select a Commercial Offer line before updating it.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkOfferLines) {
      setOfferLineEditError("Your role can view Commercial Offer lines but cannot add or update them.");
      return;
    }

    if (!offerLineEditForm.scope_description.trim()) {
      setOfferLineEditError("Scope / service description is required.");
      return;
    }

    const quantity = offerLineEditForm.quantity.trim();
    if (!quantity || Number(quantity) <= 0) {
      setOfferLineEditError("Quantity is required and must be greater than zero.");
      return;
    }

    const rateAmount = offerLineEditForm.rate_amount.trim();
    if (rateAmount.length > 0 && Number(rateAmount) < 0) {
      setOfferLineEditError("Rate amount cannot be negative.");
      return;
    }

    const currencyCode = offerLineEditForm.currency_code.trim().toUpperCase();
    if (!isOperatingCurrency(currencyCode)) {
      setOfferLineEditError(UNSUPPORTED_CURRENCY_MESSAGE);
      return;
    }

    // CS-05a: only what the user changed since the form was opened, with the line's version then.
    const changed = changedFields(formFromOfferLine(offerLineEditBaseline), offerLineEditForm);
    if (changed.length === 0) {
      setOfferLineEditError(NOTHING_CHANGED_MESSAGE);
      return;
    }

    const token = getToken();
    if (!token) {
      setOfferLineEditError(SIGN_IN_FIRST);
      return;
    }

    setOfferLineSaving(true);

    const values = {
      line_number: offerLineEditForm.line_number.trim() ? Number(offerLineEditForm.line_number.trim()) : null,
      line_status_code: offerLineEditForm.line_status_code,
      scope_description: offerLineEditForm.scope_description.trim(),
      equipment_service_category: normalizeOptional(offerLineEditForm.equipment_service_category),
      quantity,
      uom: offerLineEditForm.uom.trim(),
      rate_amount: normalizeOptional(offerLineEditForm.rate_amount),
      currency_code: currencyCode,
      remarks: normalizeOptional(offerLineEditForm.remarks),
    };
    const payload = updateRequest(offerLineEditBaseline.row_version, values, changed);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_LINES_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/lines/${encodeURIComponent(editingOfferLineId)}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setOfferLineEditError("Network error while updating the Commercial Offer line.");
      setOfferLineSaving(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setOfferLineEditError(await offerLineErrorMessage(response));
      setOfferLineSaving(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferLineUpdatedResponse;
    setLastEvents(data.event ? [data.event] : []);
    setEditingOfferLineId(null);
    setOfferLineEditForm(emptyOfferLineForm());
    setOfferLineEditBaseline(null);
    await loadOfferLines(commercialOffer.public_id, token);
    // After the refresh, which clears the lines' messages as it starts.
    setOfferLineMessage("Commercial Offer line updated. The list below has been refreshed.");
    await loadSubmissionReadiness(commercialOffer.public_id, token);
    setOfferLineSaving(false);
  }

  async function handleAddSubmissionEvidence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmissionEvidenceMessage("");
    setSubmissionEvidenceError("");
    setLastEvents([]);

    if (!commercialOffer) {
      setSubmissionEvidenceError("Load a Commercial Offer before recording submission evidence.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkSubmissionEvidence) {
      setSubmissionEvidenceError("Your role can view submission evidence but cannot add it.");
      return;
    }

    if (!submissionEvidenceForm.submitted_at.trim()) {
      setSubmissionEvidenceError("Submitted date/time is required.");
      return;
    }

    if (!submissionEvidenceForm.submission_channel.trim()) {
      setSubmissionEvidenceError("Submission channel is required.");
      return;
    }

    const token = getToken();
    if (!token) {
      setSubmissionEvidenceError(SIGN_IN_FIRST);
      return;
    }

    setSubmissionEvidenceSaving(true);

    const payload = {
      submission_reference: normalizeOptional(submissionEvidenceForm.submission_reference),
      submission_channel: submissionEvidenceForm.submission_channel,
      submitted_at: enteredIndiaTimeToUtc(submissionEvidenceForm.submitted_at),
      recipient_summary: normalizeOptional(submissionEvidenceForm.recipient_summary),
      submitted_version_snapshot: normalizeOptional(submissionEvidenceForm.submitted_version_snapshot),
      document_reference_label: normalizeOptional(submissionEvidenceForm.document_reference_label),
      document_reference_url_or_path: normalizeOptional(submissionEvidenceForm.document_reference_url_or_path),
      evidence_notes: normalizeOptional(submissionEvidenceForm.evidence_notes),
    };

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/submission-evidence`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setSubmissionEvidenceError("Network error while recording submission evidence.");
      setSubmissionEvidenceSaving(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setSubmissionEvidenceError(await submissionEvidenceErrorMessage(response));
      setSubmissionEvidenceSaving(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferSubmissionEvidenceCreatedResponse;
    setLastEvents(data.event ? [data.event] : []);
    setSubmissionEvidenceForm(emptySubmissionEvidenceForm());
    await loadSubmissionEvidence(commercialOffer.public_id, token);
    await loadSubmissionReadiness(commercialOffer.public_id, token);
    setSubmissionEvidenceMessage("Submission evidence recorded.");
    setSubmissionEvidenceSaving(false);
  }

  async function handleAddCreditReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreditReviewMessage("");
    setCreditReviewError("");
    setLastEvents([]);

    if (!commercialOffer) {
      setCreditReviewError("Load a Commercial Offer before recording a manual credit/exposure review.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkCreditReview) {
      setCreditReviewError("Your role can view manual credit/exposure reviews but cannot add them.");
      return;
    }

    if (!creditReviewForm.reviewed_at.trim()) {
      setCreditReviewError("Reviewed date/time is required.");
      return;
    }

    if (creditReviewForm.review_status === "APPROVED_WITH_REFERENCE" && !creditReviewForm.review_reference.trim()) {
      setCreditReviewError("Review reference is required for Approved With Reference status.");
      return;
    }

    const token = getToken();
    if (!token) {
      setCreditReviewError(SIGN_IN_FIRST);
      return;
    }

    setCreditReviewSaving(true);
    const payload = {
      review_status: creditReviewForm.review_status,
      review_basis: normalizeOptional(creditReviewForm.review_basis),
      review_reference: normalizeOptional(creditReviewForm.review_reference),
      reviewed_at: enteredIndiaTimeToUtc(creditReviewForm.reviewed_at),
      approved_amount_snapshot: normalizeOptional(creditReviewForm.approved_amount_snapshot),
      credit_days_snapshot: creditReviewForm.credit_days_snapshot.trim()
        ? Number(creditReviewForm.credit_days_snapshot)
        : null,
      exposure_note: normalizeOptional(creditReviewForm.exposure_note),
    };

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_CREDIT_REVIEW_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/credit-review`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setCreditReviewError("Network error while recording the manual credit/exposure review.");
      setCreditReviewSaving(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setCreditReviewError(await creditReviewErrorMessage(response));
      setCreditReviewSaving(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferCreditReviewCreatedResponse;
    setLastEvents(data.event ? [data.event] : []);
    setCreditReviewForm(emptyCreditReviewForm());
    await loadCreditReviews(commercialOffer.public_id, token);
    await loadSubmissionReadiness(commercialOffer.public_id, token);
    setCreditReviewMessage("Manual credit/exposure review recorded. Submission readiness now reflects the latest review.");
    setCreditReviewSaving(false);
  }

  async function handleMakeVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setVersionCreateMessage("");
    setVersionCreateError("");
    setCreatedVersionPublicId(null);
    setLastEvents([]);
    if (!commercialOffer) return;
    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkRevisions) {
      setVersionCreateError("Your role can view offer versions but cannot make a new one.");
      return;
    }
    const token = getToken();
    if (!token) {
      setVersionCreateError(SIGN_IN_FIRST);
      return;
    }
    setVersionCreating(true);
    let response: Response;
    try {
      response = await fetch(
        `${COMMERCIAL_OFFER_VERSION_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/versions`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({
            version_reason: versionForm.version_reason,
            version_note: normalizeOptional(versionForm.version_note),
          }),
        },
      );
    } catch {
      setVersionCreateError("Network error while making the new Commercial Offer version.");
      setVersionCreating(false);
      return;
    }
    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setVersionCreateError(await versionErrorMessage(response));
      setVersionCreating(false);
      return;
    }
    const data = (await response.json()) as CommercialOfferVersionActionResponse;
    setLastEvents(data.event ? [data.event] : []);
    setCreatedVersionPublicId(data.commercial_offer.public_id);
    setVersionForm(emptyVersionForm());
    await loadOfferVersions(commercialOffer.public_id, token);
    await loadLifecycleGuidance(commercialOffer.public_id, token);
    setVersionCreateMessage(
      `${offerVersionLabel(data.commercial_offer)} made as an editable Draft. Lines, prices, T&C and the current credit review were copied; submission evidence and quotation documents were not.`,
    );
    setVersionCreating(false);
  }

  async function handleAbandonVersion(version: CommercialOffer) {
    setVersionActionMessages((current) => ({ ...current, [version.public_id]: "" }));
    setVersionActionErrors((current) => ({ ...current, [version.public_id]: "" }));
    const token = getToken();
    if (!token) {
      setVersionActionErrors((current) => ({ ...current, [version.public_id]: SIGN_IN_FIRST }));
      return;
    }
    setVersionAbandoningId(version.public_id);
    let response: Response;
    try {
      response = await fetch(
        `${COMMERCIAL_OFFER_VERSION_BASE_PATH}/${encodeURIComponent(version.public_id)}/abandon-version`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      );
    } catch {
      setVersionActionErrors((current) => ({ ...current, [version.public_id]: "Network error while abandoning this version." }));
      setVersionAbandoningId(null);
      return;
    }
    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setVersionActionErrors((current) => ({ ...current, [version.public_id]: "See the validation message below." }));
      const detail = await versionErrorMessage(response);
      setVersionActionErrors((current) => ({ ...current, [version.public_id]: detail }));
      setVersionAbandoningId(null);
      return;
    }
    const data = (await response.json()) as CommercialOfferVersionActionResponse;
    setLastEvents(data.event ? [data.event] : []);
    setVersionActionMessages((current) => ({
      ...current,
      [version.public_id]: `${offerVersionLabel(data.commercial_offer)} abandoned. The previously sent version is unchanged.`,
    }));
    await loadOfferVersions(version.public_id, token);
    if (commercialOffer?.public_id === version.public_id) {
      setCommercialOffer(data.commercial_offer);
      setEditFormFrom(data.commercial_offer);
    }
    if (commercialOffer) await loadLifecycleGuidance(commercialOffer.public_id, token);
    setVersionAbandoningId(null);
  }

  async function handleRevisionAction(revision: CommercialOfferRevision, action: "mark-resubmitted" | "cancel") {
    setRevisionActionMessages((current) => ({ ...current, [revision.public_id]: "" }));
    setRevisionActionErrors((current) => ({ ...current, [revision.public_id]: "" }));
    setLastEvents([]);

    if (!commercialOffer) return;
    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkRevisions) {
      setRevisionActionErrors((current) => ({ ...current, [revision.public_id]: "Your role cannot manage revisions." }));
      return;
    }

    const token = getToken();
    if (!token) {
      setRevisionActionErrors((current) => ({ ...current, [revision.public_id]: SIGN_IN_FIRST }));
      return;
    }

    const selectedEvidenceId = revisionResubmissionEvidenceIds[revision.public_id] || submissionEvidence[0]?.public_id || "";
    if (action === "mark-resubmitted" && !selectedEvidenceId) {
      setRevisionActionErrors((current) => ({
        ...current,
        [revision.public_id]: "Record submission evidence first, then select it as the evidence that the revised offer was re-sent.",
      }));
      return;
    }

    setRevisionActionSavingId(revision.public_id);
    let response: Response;
    try {
      response = await fetch(
        `${COMMERCIAL_OFFER_REVISION_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/revisions/${encodeURIComponent(revision.public_id)}/${action}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            ...(action === "mark-resubmitted" ? { "Content-Type": "application/json" } : {}),
          },
          body: action === "mark-resubmitted"
            ? JSON.stringify({ resubmission_evidence_public_id: selectedEvidenceId })
            : undefined,
        },
      );
    } catch {
      setRevisionActionErrors((current) => ({ ...current, [revision.public_id]: "Network error while updating the revision." }));
      setRevisionActionSavingId(null);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setRevisionActionErrors((current) => ({ ...current, [revision.public_id]: "Updating revision failed. See the latest validation message." }));
      const detail = await revisionErrorMessage(response);
      setRevisionActionErrors((current) => ({ ...current, [revision.public_id]: detail }));
      setRevisionActionSavingId(null);
      return;
    }

    const data = (await response.json()) as CommercialOfferRevisionActionResponse;
    setLastEvents(data.event ? [data.event] : []);
    await loadRevisions(commercialOffer.public_id, token);
    await loadSubmissionReadiness(commercialOffer.public_id, token);
    await loadLifecycleGuidance(commercialOffer.public_id, token);
    setRevisionActionMessages((current) => ({
      ...current,
      [revision.public_id]: action === "mark-resubmitted"
        ? "Revised offer marked as re-sent, using the selected submission evidence."
        : "Revision cancelled. Its history remains visible.",
    }));
    setRevisionActionSavingId(null);
  }

  async function handleRecordCustomerResponse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCustomerResponseMessage("");
    setCustomerResponseError("");
    setLastEvents([]);
    if (!commercialOffer) return;
    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkCustomerResponses) {
      setCustomerResponseError("Your role can view customer responses but cannot record them.");
      return;
    }
    if (!customerResponseForm.response_received_at) {
      setCustomerResponseError("Response received date/time is required.");
      return;
    }
    const token = getToken();
    if (!token) {
      setCustomerResponseError(SIGN_IN_FIRST);
      return;
    }
    setCustomerResponseSaving(true);
    const payload = {
      response_outcome: customerResponseForm.response_outcome,
      response_reference: normalizeOptional(customerResponseForm.response_reference),
      response_received_at: enteredIndiaTimeToUtc(customerResponseForm.response_received_at),
      response_channel: customerResponseForm.response_channel,
      received_from: normalizeOptional(customerResponseForm.received_from),
      awarded_amount_snapshot: normalizeOptional(customerResponseForm.awarded_amount_snapshot),
      awarded_currency_snapshot: customerResponseForm.awarded_amount_snapshot.trim()
        ? customerResponseForm.awarded_currency_snapshot || DEFAULT_CURRENCY
        : null,
      awarded_version_snapshot: normalizeOptional(customerResponseForm.awarded_version_snapshot),
      customer_po_or_wo_reference: normalizeOptional(customerResponseForm.customer_po_or_wo_reference),
      customer_response_notes: normalizeOptional(customerResponseForm.customer_response_notes),
      linked_submission_evidence_public_id: normalizeOptional(customerResponseForm.linked_submission_evidence_public_id),
      linked_revision_public_id: normalizeOptional(customerResponseForm.linked_revision_public_id),
    };
    let response: Response;
    try {
      response = await fetch(
        `${COMMERCIAL_OFFER_CUSTOMER_RESPONSE_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/customer-responses`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
    } catch {
      setCustomerResponseError("Network error while recording customer response / award outcome.");
      setCustomerResponseSaving(false);
      return;
    }
    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setCustomerResponseError(await customerResponseErrorMessage(response));
      setCustomerResponseSaving(false);
      return;
    }
    // The response has been recorded on the server from here on. Everything below is display
    // work, and no failure in it may leave the user without confirmation of a committed action.
    let data: CommercialOfferCustomerResponseCreatedResponse;
    try {
      data = (await response.json()) as CommercialOfferCustomerResponseCreatedResponse;
    } catch {
      setCustomerResponseMessage(
        "Customer response recorded, but the confirmation could not be read. Reload the page to see the current status.",
      );
      setCustomerResponseSaving(false);
      return;
    }

    // Confirmation first, before any refresh. Recording a rejection replaces the form with the
    // finality panel, so the message must already be set and must live outside the form; and a
    // refresh that throws must not be able to swallow the confirmation of a committed write.
    setCustomerResponseMessage(
      `${formatStatusLabel(data.customer_response.response_outcome)} recorded. No Work Order was created automatically.`,
    );
    setCustomerResponseSaving(false);

    setCommercialOffer(data.commercial_offer);
    setEditFormFrom(data.commercial_offer);
    setLastEvents(data.event ? [data.event] : []);
    setCustomerResponseForm(emptyCustomerResponseForm());

    // allSettled, not sequential awaits: a failing refresh must not prevent the other two from
    // running, and must not propagate out of an action that has already succeeded.
    await Promise.allSettled([
      loadCustomerResponses(commercialOffer.public_id, token),
      loadSubmissionReadiness(commercialOffer.public_id, token),
      loadLifecycleGuidance(commercialOffer.public_id, token),
    ]);
  }

  async function handleMarkSubmitted() {
    setMarkSubmittedMessage("");
    setMarkSubmittedWarning("");
    setMarkSubmittedError("");
    setLastEvents([]);

    if (!commercialOffer) {
      setMarkSubmittedError("Load a Commercial Offer before recording submission.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkCommercialOffer) {
      setMarkSubmittedError("Your role cannot record this Commercial Offer as submitted.");
      return;
    }

    const token = getToken();
    if (!token) {
      setMarkSubmittedError(SIGN_IN_FIRST);
      return;
    }

    setMarkSubmittedSaving(true);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_DETAIL_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}/mark-submitted`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setMarkSubmittedError("Network error while recording the Commercial Offer as submitted.");
      setMarkSubmittedSaving(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setMarkSubmittedError(await markSubmittedErrorMessage(response));
      setMarkSubmittedSaving(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferMarkedSubmittedResponse;
    setCommercialOffer(data.commercial_offer);
    setEditFormFrom(data.commercial_offer);
    setLastEvents(data.event ? [data.event] : []);
    await Promise.all([
      loadSubmissionReadiness(data.commercial_offer.public_id, token),
      loadOfferVersions(data.commercial_offer.public_id, token),
      loadLifecycleGuidance(data.commercial_offer.public_id, token),
    ]);
    setMarkSubmittedMessage(
      "Commercial Offer recorded as submitted. It is now commercially committed.",
    );
    setMarkSubmittedWarning(data.warnings.join(" "));
    setMarkSubmittedSaving(false);
  }

  // CS-05a: the edit form and the offer it was opened from change together, so a save sends that offer's version
  // and only what the user changed since.
  function setEditFormFrom(offer: CommercialOffer) {
    setEditForm(formFromCommercialOffer(offer));
    setEditBaseline(offer);
  }

  function startEditing() {
    if (!commercialOffer) return;
    setEditFormFrom(commercialOffer);
    setLastEvents([]);
    setMessage("");
    setError("");
    setActionMessage("");
    setActionError("");
    setPricingEvidenceError("");
    setTcClauseMessage("");
    setTcClauseError("");
    setSubmissionEvidenceMessage("");
    setSubmissionEvidenceError("");
    setIsEditing(true);
  }

  function cancelEditing() {
    if (commercialOffer) setEditFormFrom(commercialOffer);
    setIsEditing(false);
    setError("");
    setActionMessage("");
    setActionError("");
    setPricingEvidenceError("");
    setTcClauseMessage("");
    setTcClauseError("");
    setSubmissionEvidenceMessage("");
    setSubmissionEvidenceError("");
  }

  async function handleUpdateSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setError("");
    setActionMessage("");
    setActionError("");
    setPricingEvidenceError("");
    setTcClauseMessage("");
    setTcClauseError("");
    setLastEvents([]);

    if (!commercialOffer) {
      setActionError("Load a Commercial Offer before updating it.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkCommercialOffer) {
      setActionError("Your role can view this Commercial Offer but cannot update it.");
      return;
    }

    const offerValue = editForm.offer_value.trim();
    if (offerValue.length > 0 && Number(offerValue) < 0) {
      setActionError("Offer value cannot be negative.");
      return;
    }

    const currencyCode = editForm.currency_code.trim().toUpperCase();
    if (!isOperatingCurrency(currencyCode)) {
      setActionError(UNSUPPORTED_CURRENCY_MESSAGE);
      return;
    }

    if (editForm.offer_date && editForm.valid_until && editForm.valid_until < editForm.offer_date) {
      setActionError("Valid until date cannot be earlier than offer date.");
      return;
    }

    if (statusRequiresAccountTraceability(editForm.offer_status_code) && !hasAccountTraceability(commercialOffer)) {
      setActionError(accountTraceabilityBlockMessage());
      return;
    }

    // CS-05a: only what the user changed since the form was opened, with the offer's version then.
    const opened = editBaseline ?? commercialOffer;
    const changed = changedFields(formFromCommercialOffer(opened), editForm);
    if (changed.length === 0) {
      setActionError(NOTHING_CHANGED_MESSAGE);
      return;
    }

    const token = getToken();
    if (!token) {
      setActionError(SIGN_IN_FIRST);
      return;
    }

    setUpdating(true);

    const values = {
      offer_title: normalizeOptional(editForm.offer_title),
      offer_mode: editForm.offer_mode,
      offer_type: editForm.offer_type,
      offer_status_code: editForm.offer_status_code,
      offer_value: normalizeOptional(editForm.offer_value),
      currency_code: currencyCode,
      offer_date: normalizeOptional(editForm.offer_date),
      valid_until: normalizeOptional(editForm.valid_until),
      submitted_at: enteredIndiaTimeToUtc(editForm.submitted_at),
      submission_reference: normalizeOptional(editForm.submission_reference),
      submission_proof_note: normalizeOptional(editForm.submission_proof_note),
      outcome_date: normalizeOptional(editForm.outcome_date),
      outcome_remarks: normalizeOptional(editForm.outcome_remarks),
      remarks: normalizeOptional(editForm.remarks),
    };
    const payload = updateRequest(opened.row_version, values, changed);

    let response: Response;
    try {
      response = await fetch(`${COMMERCIAL_OFFER_DETAIL_BASE_PATH}/${encodeURIComponent(commercialOffer.public_id)}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setActionError("Network error while updating this Commercial Offer. Check that the backend and frontend services are running.");
      setUpdating(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setActionError(await commercialOfferUpdateErrorMessage(response));
      setUpdating(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferUpdatedResponse;
    setCommercialOffer(data.commercial_offer);
    setEditFormFrom(data.commercial_offer);
    setLastEvents(data.events ?? []);
    setActionMessage("Commercial Offer updated successfully. The refreshed profile below reflects the saved values.");
    await loadSubmissionReadiness(data.commercial_offer.public_id, token);
    setUpdating(false);
  }

  const eventHref = useMemo(() => {
    if (!commercialOffer) return "";
    const returnTo = `/commercial-offers/${commercialOffer.public_id}`;
    return `/events?returnTo=${encodeURIComponent(returnTo)}&returnLabel=${encodeURIComponent("Back to Commercial Offer")}`;
  }, [commercialOffer]);

  const commercialOfferReturnTo = commercialOffer ? `/commercial-offers/${commercialOffer.public_id}` : "";
  const accountTraceabilityAvailable = hasAccountTraceability(commercialOffer);
  const selectedStatusNeedsAccountTraceability = statusRequiresAccountTraceability(editForm.offer_status_code);
  // Prefer the backend-derived Slice 6M readiness flag once it has loaded so the header,
  // Traceability tab and Lifecycle Guidance panel never disagree about handoff eligibility.
  // Fall back to the pre-6M status+Account check only while guidance has not loaded yet.
  const workOrderHandoffAvailable = lifecycleGuidance
    ? lifecycleGuidance.work_order_handoff_available
    : commercialOffer?.offer_status_code === "ACCEPTED" && accountTraceabilityAvailable;
  // The frozen handoff contract allows an additional Work Order for a partial award. Slice 6M offered "Create" only
  // while none existed, because nothing then stopped the same lines being handed off twice. Since CS-04 part 1 the
  // server refuses anything already on a Work Order and the guidance says when nothing is left, so "Create" is offered
  // whenever the guidance allows it - after the first, as "Create another Work Order" - and "Open" for every one.
  const existingLinkedWorkOrderCount = lifecycleGuidance ? lifecycleGuidance.linked_work_orders.length : linkedWorkOrders.length;
  const canOfferCreateWorkOrderAction = workOrderHandoffAvailable;
  const createWorkOrderActionLabel = createWorkOrderLabel(existingLinkedWorkOrderCount);
  // Slice 6O: a compact review snapshot for the handoff panel. Active line count/summary are
  // derived from the already-loaded offer lines; nothing new is fetched for this.
  const activeOfferLinesForHandoff = useMemo(
    () => offerLines.filter((offerLine) => offerLine.line_status_code === "ACTIVE"),
    [offerLines],
  );

  const statusIsDeferredForEditing = commercialOffer
    ? !COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS.includes(
        commercialOffer.offer_status_code as typeof COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS[number],
      )
    : false;
  // Slice 6M.1 (fa09489 + completion): once the offer is in a status the backend cannot
  // leave through general update (WITHDRAWN, REJECTED, CLOSED, ACCEPTED), the status
  // select is locked to the current value. This is checked separately from
  // statusIsDeferredForEditing above because ACCEPTED/REJECTED are also never offered as
  // entry targets, so both flags are true for them - the terminal message below takes
  // precedence to avoid showing two overlapping notices.
  const statusIsTerminalForEditing = commercialOffer
    ? COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES.includes(
        commercialOffer.offer_status_code as typeof COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES[number],
      )
    : false;
  // Slice 9F: commercial content changes only on Draft and Ready for Review versions.
  const offerContentIsLocked = commercialOffer
    ? offerContentLocked(commercialOffer.offer_status_code)
    : false;
  const isPreparationVersion = Boolean(
    commercialOffer?.previous_version_offer_public_id
      && ["DRAFT", "READY_FOR_REVIEW"].includes(commercialOffer.offer_status_code),
  );
  // Submitted versions may be withdrawn/closed and all current concluded versions retain the
  // established outcome-date/remarks correction path. REVISED/ABANDONED history never reaches
  // this form because it is content-locked without either condition.
  const canEditOfferStatusOrOutcome = commercialOffer
    ? commercialOffer.offer_status_code === "SUBMITTED" || statusIsTerminalForEditing
    : false;
  const lockedContentNote = commercialOffer ? contentLockedNote(commercialOffer.offer_status_code) : "";

  return (
    <section>
      <PageHeader
        eyebrow="Commercial Offer"
        back={{ href: returnTarget.href, label: returnTarget.label }}
        title={
          commercialOffer
            ? commercialOffer.offer_title
              ? `${offerVersionLabel(commercialOffer)} - ${commercialOffer.offer_title}`
              : offerVersionLabel(commercialOffer)
            : "Commercial Offer"
        }
        badges={
          commercialOffer ? (
            <>
              <StatusBadge code={commercialOffer.offer_status_code} label={formatStatusLabel(commercialOffer.offer_status_code)} />
              <span className="status-badge status-badge--info">{offerPurposeLabel(commercialOffer.offer_purpose)}</span>
            </>
          ) : null
        }
        actions={
          <>
            <button
              type="button"
              onClick={() => {
                if (typeof commercialOfferId === "string") void loadCommercialOffer(commercialOfferId);
              }}
              disabled={loading || typeof commercialOfferId !== "string"}
              style={MUTED_BUTTON_STYLE}
            >
              {loading ? "Loading..." : "Refresh"}
            </button>
            {pageAccess.canWorkCommercialOffer && commercialOffer ? (
              <button
                type="button"
                onClick={startEditing}
                disabled={loading || updating || isEditing || (offerContentIsLocked && !canEditOfferStatusOrOutcome)}
                style={BUTTON_STYLE}
              >
                Edit Commercial Offer / Status
              </button>
            ) : null}
            {pageAccess.canCreateWorkOrder && commercialOffer && canOfferCreateWorkOrderAction ? (
              <a href={`/work-orders/new?commercialOfferId=${encodeURIComponent(commercialOffer.public_id)}`} style={BUTTON_STYLE}>
                {createWorkOrderActionLabel}
              </a>
            ) : null}
          </>
        }
      >
        {pageAccess.canWorkCommercialOffer ? null : <p className="helper-text">{accessMessage(pageAccess)}</p>}
        {message ? <p style={{ color: "#065f46" }}>{message}</p> : null}
        {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
        {commercialOffer?.replaced_by_version_number ? (
          <p style={{ color: "#374151", padding: "8px 10px", border: "1px solid #bfdbfe", background: "#eff6ff" }}>
            Replaced by v{commercialOffer.replaced_by_version_number}. This version remains read-only history.
          </p>
        ) : null}
      </PageHeader>

      {commercialOffer ? (
        <div
          role="tablist"
          aria-label="Commercial Offer detail sections"
          className="detail-tabs"
        >
          {COMMERCIAL_OFFER_DETAIL_TABS.map((tab) => {
            const selected = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`commercial-offer-tab-${tab.id}`}
                type="button"
                role="tab"
                aria-selected={selected}
                aria-controls="commercial-offer-tabpanel"
                onClick={() => setActiveTab(tab.id)}
                className="detail-tab"
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      ) : null}

      {lastEvents.length > 0 ? (
        <div style={{ marginTop: "12px", padding: "12px", border: "1px solid #bbf7d0", background: "#f0fdf4" }}>
          Saved. This change is recorded in the audit trail.
        </div>
      ) : null}

      {commercialOffer && isEditing ? (
        <form
          onSubmit={handleUpdateSubmit}
          style={{
            display: "grid",
            gap: "14px",
            maxWidth: "820px",
            marginTop: "24px",
            padding: "16px",
            border: "1px solid #bfdbfe",
            background: "#eff6ff",
          }}
        >
          <h3 style={{ marginTop: 0 }}>Edit offer details and status</h3>
          <p style={{ color: "#374151", marginTop: 0 }}>
            Use this form for the offer's own details. Submission, customer responses and revisions have their own actions on the Submission tab.
          </p>
          {offerContentIsLocked && commercialOffer.offer_status_code === "SUBMITTED" ? (
            <p className="helper-text">
              Commercial details are read-only after submission. You may only withdraw or close this version, or add its outcome date and remarks.
            </p>
          ) : null}
          {statusIsDeferredForEditing && !statusIsTerminalForEditing && commercialOffer.offer_status_code === "SUBMITTED" ? (
            <p className="text-warning">
              This Commercial Offer has been submitted, so it cannot go back to Draft or Ready for Review. This form can
              withdraw or close it; record the customer's response in the Submission tab.
            </p>
          ) : statusIsDeferredForEditing && !statusIsTerminalForEditing ? (
            <p style={{ color: "#92400e", marginTop: 0 }}>
              This Commercial Offer is currently in {formatStatusLabel(commercialOffer.offer_status_code)}. General edit options can save Draft, Ready for Review, Withdrawn or Closed. Use the controlled action in the Submission tab to enter Submitted status.
            </p>
          ) : null}
          {statusIsTerminalForEditing ? (
            <p style={{ color: "#92400e", marginTop: 0 }}>
              This Commercial Offer version is {formatStatusLabel(commercialOffer.offer_status_code)}. Its status and
              commercial details are read-only; only its outcome date and outcome remarks may be updated here.
            </p>
          ) : null}
          {!accountTraceabilityAvailable && selectedStatusNeedsAccountTraceability ? (
            <div style={{ padding: "12px", border: "1px solid #f59e0b", background: "#fffbeb", color: "#92400e" }}>
              <strong>Blocked:</strong> {accountTraceabilityBlockMessage()}{" "}
              <a
                href={hrefWithReturnTarget(
                  `/opportunities/${commercialOffer.opportunity_public_id}`,
                  commercialOfferReturnTo,
                  "Back to Commercial Offer",
                )}
                style={{ color: "#1d4ed8", fontWeight: 700 }}
              >
                Open Opportunity context
              </a>
            </div>
          ) : null}

          <label style={{ display: "grid", gap: "4px" }}>
            Offer title
            <input
              value={editForm.offer_title}
              onChange={(event) => setEditForm((current) => ({ ...current, offer_title: event.target.value }))}
              disabled={offerContentIsLocked}
              maxLength={255}
              style={{ padding: "8px" }}
            />
          </label>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" }}>
            <label style={{ display: "grid", gap: "4px" }}>
              Offer mode
              <select
                value={editForm.offer_mode}
                onChange={(event) => setEditForm((current) => ({ ...current, offer_mode: event.target.value }))}
                disabled={offerContentIsLocked}
                style={{ padding: "8px" }}
              >
                {COMMERCIAL_OFFER_MODE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>

            <label style={{ display: "grid", gap: "4px" }}>
              Offer type
              <select
                value={editForm.offer_type}
                onChange={(event) => setEditForm((current) => ({ ...current, offer_type: event.target.value }))}
                disabled={offerContentIsLocked}
                style={{ padding: "8px" }}
              >
                {COMMERCIAL_OFFER_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>

            <label style={{ display: "grid", gap: "4px" }}>
              Offer status
              <select
                value={editForm.offer_status_code}
                onChange={(event) => {
                  setEditForm((current) => ({ ...current, offer_status_code: event.target.value }));
                  setActionMessage("");
                  setActionError("");
                }}
                disabled={statusIsTerminalForEditing}
                style={{ padding: "8px" }}
              >
                {statusIsTerminalForEditing ? (
                  <option value={editForm.offer_status_code}>
                    {formatStatusLabel(editForm.offer_status_code)} (final status, cannot be changed here)
                  </option>
                ) : null}
                {!statusIsTerminalForEditing && !COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS.includes(
                  editForm.offer_status_code as typeof COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS[number],
                ) ? (
                  <option value={editForm.offer_status_code} disabled>
                    {formatStatusLabel(editForm.offer_status_code)} (current status)
                  </option>
                ) : null}
                {statusIsTerminalForEditing ? null : statusUpdateOptions(commercialOffer.offer_status_code, isPreparationVersion).map((status) => (
                  <option key={status} value={status}>{formatStatusLabel(status)}</option>
                ))}
              </select>
            </label>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "14px" }}>
            <label style={{ display: "grid", gap: "4px" }}>
              Offer value
              <input
                value={editForm.offer_value}
                onChange={(event) => setEditForm((current) => ({ ...current, offer_value: event.target.value }))}
                disabled={offerContentIsLocked}
                type="number"
                min="0"
                step="0.01"
                style={{ padding: "8px" }}
              />
            </label>

            <label style={{ display: "grid", gap: "4px" }}>
              Currency
              <CurrencySelect
                value={editForm.currency_code}
                onChange={(currencyCode) => setEditForm((current) => ({ ...current, currency_code: currencyCode }))}
                disabled={offerContentIsLocked}
                style={{ padding: "8px" }}
              />
            </label>

            <label style={{ display: "grid", gap: "4px" }}>
              Offer date
              <DateInput
                value={editForm.offer_date}
                onChange={(event) => setEditForm((current) => ({ ...current, offer_date: event.target.value }))}
                disabled={offerContentIsLocked}
                style={{ padding: "8px" }}
              />
            </label>

            <label style={{ display: "grid", gap: "4px" }}>
              Valid until
              <DateInput
                value={editForm.valid_until}
                onChange={(event) => setEditForm((current) => ({ ...current, valid_until: event.target.value }))}
                disabled={offerContentIsLocked}
                style={{ padding: "8px" }}
              />
            </label>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" }}>
            <label style={{ display: "grid", gap: "4px" }}>
              Submitted at
              <DateInput
                withTime
                value={editForm.submitted_at}
                onChange={(event) => setEditForm((current) => ({ ...current, submitted_at: event.target.value }))}
                disabled={offerContentIsLocked || isPreparationVersion}
                style={{ padding: "8px" }}
              />
            </label>
            <label style={{ display: "grid", gap: "4px" }}>
              Submission reference
              <input
                value={editForm.submission_reference}
                onChange={(event) => setEditForm((current) => ({ ...current, submission_reference: event.target.value }))}
                disabled={offerContentIsLocked || isPreparationVersion}
                maxLength={255}
                style={{ padding: "8px" }}
              />
            </label>
            <label style={{ display: "grid", gap: "4px" }}>
              Outcome date
              <DateInput
                value={editForm.outcome_date}
                onChange={(event) => setEditForm((current) => ({ ...current, outcome_date: event.target.value }))}
                disabled={offerContentIsLocked && !canEditOfferStatusOrOutcome}
                style={{ padding: "8px" }}
              />
            </label>
          </div>

          <label style={{ display: "grid", gap: "4px" }}>
            Submission proof note
            <textarea
              value={editForm.submission_proof_note}
              onChange={(event) => setEditForm((current) => ({ ...current, submission_proof_note: event.target.value }))}
              disabled={offerContentIsLocked || isPreparationVersion}
              rows={3}
              maxLength={4000}
              style={{ padding: "8px" }}
            />
          </label>

          <label style={{ display: "grid", gap: "4px" }}>
            Outcome remarks
            <textarea
              value={editForm.outcome_remarks}
              onChange={(event) => setEditForm((current) => ({ ...current, outcome_remarks: event.target.value }))}
              disabled={offerContentIsLocked && !canEditOfferStatusOrOutcome}
              rows={3}
              maxLength={4000}
              style={{ padding: "8px" }}
            />
          </label>

          <label style={{ display: "grid", gap: "4px" }}>
            Remarks / requirement notes
            <textarea
              value={editForm.remarks}
              onChange={(event) => setEditForm((current) => ({ ...current, remarks: event.target.value }))}
              disabled={offerContentIsLocked}
              maxLength={4000}
              rows={5}
              style={{ padding: "8px" }}
            />
          </label>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <button type="submit" disabled={updating || (offerContentIsLocked && !canEditOfferStatusOrOutcome) || (!accountTraceabilityAvailable && selectedStatusNeedsAccountTraceability)}>
              {updating ? "Saving..." : "Save Commercial Offer"}
            </button>
            <button type="button" onClick={cancelEditing} disabled={updating}>Cancel</button>
          </div>
          {actionMessage ? <p style={{ color: "#065f46", marginTop: 0 }}>{actionMessage}</p> : null}
          {actionError ? <p style={{ color: "crimson", marginTop: 0 }}>{actionError}</p> : null}
        </form>
      ) : null}

      {commercialOffer ? (
        <div
          id="commercial-offer-tabpanel"
          role="tabpanel"
          aria-labelledby={`commercial-offer-tab-${activeTab}`}
          style={{ marginTop: "24px", display: "grid", gap: "16px", maxWidth: "1120px" }}
        >
          {activeTab === "submission" ? (
            <>
            <SectionIndex
              items={[
                { id: "co-submission-status", label: "Where it stands" },
                { id: "co-submission-prepare", label: "Prepare" },
                { id: "co-submission-quote", label: "Quotation and submission" },
                { id: "co-submission-outcome", label: "Customer response" },
              ]}
            />

            <SectionGroup id="co-submission-status" title="Where this offer stands" tone="blue" description="What has happened to this offer and what can happen next.">
              <SectionCard title="Lifecycle Guidance" soft>
                <p style={{ marginTop: 0 }}>
                  Where this offer stands and what can happen next, worked out from its submission, version and
                  customer-response records. This is guidance only: every action still makes its own check when you
                  use it.
                </p>

                {commercialOffer.offer_status_code === "ACCEPTED" ? (
                  <article style={{ padding: "12px", border: "1px solid #ddd", background: "#ffffff", marginBottom: "12px", minWidth: 0 }}>
                    <strong>Before you create the Work Order</strong>
                    <p style={{ margin: "6px 0 10px 0", color: "#6b7280" }}>
                      Check the accepted offer here before you create its Work Order. Nothing on this panel
                      creates a Work Order by itself.
                    </p>
                    <dl style={COMPACT_DETAIL_GRID_STYLE}>
                      <DetailRow label="Commercial Offer">{offerVersionLabel(commercialOffer)}</DetailRow>
                      <DetailRow label="Status">{formatStatusLabel(commercialOffer.offer_status_code)}</DetailRow>
                      <DetailRow label="Offer mode / type">
                        {formatStatusLabel(commercialOffer.offer_mode)} / {formatStatusLabel(commercialOffer.offer_type)}
                      </DetailRow>
                      <DetailRow label="Offer date">{formatDateOnly(commercialOffer.offer_date)}</DetailRow>
                      <DetailRow label="Offer value">{formatMoney(commercialOffer.offer_value, commercialOffer.currency_code)}</DetailRow>
                      <DetailRow label="Account">
                        {commercialOffer.account_public_id ? (
                          <a
                            href={hrefWithReturnTarget(`/accounts/${commercialOffer.account_public_id}`, commercialOfferReturnTo, "Back to Commercial Offer")}
                            style={{ color: "#1d4ed8", fontWeight: 700 }}
                          >
                            {linkedNames.account ?? "Open Account"}
                          </a>
                        ) : "-"}
                        {commercialOffer.account_public_id ? (
                          <div>
                            <ReferenceText>{commercialOffer.account_public_id}</ReferenceText>
                          </div>
                        ) : null}
                      </DetailRow>
                      <DetailRow label="Opportunity">
                        <a
                          href={hrefWithReturnTarget(`/opportunities/${commercialOffer.opportunity_public_id}`, commercialOfferReturnTo, "Back to Commercial Offer")}
                          style={{ color: "#1d4ed8", fontWeight: 700 }}
                        >
                          {linkedNames.opportunity ?? "Open Opportunity"}
                        </a>
                        <div>
                          <ReferenceText>{commercialOffer.opportunity_public_id}</ReferenceText>
                        </div>
                      </DetailRow>
                      <DetailRow label="Active Commercial Offer lines">{activeOfferLinesForHandoff.length}</DetailRow>
                    </dl>
                    {activeOfferLinesForHandoff.length > 0 ? (
                      <ul style={{ margin: "10px 0 0 0", paddingLeft: "20px", color: "#6b7280" }}>
                        {activeOfferLinesForHandoff.slice(0, 5).map((offerLine) => (
                          <li key={offerLine.public_id} style={SAFE_LONG_TEXT_STYLE}>
                            Line {offerLine.line_number}: {offerLine.scope_description} ({offerLine.quantity} {offerLine.uom})
                          </li>
                        ))}
                        {activeOfferLinesForHandoff.length > 5 ? (
                          <li>...and {activeOfferLinesForHandoff.length - 5} more active line(s).</li>
                        ) : null}
                      </ul>
                    ) : null}
                    <p style={{ margin: "10px 0 0 0", ...SAFE_LONG_TEXT_STYLE }}>
                      {existingLinkedWorkOrderCount === 0
                        ? "No Work Order has been created yet from this Commercial Offer. Creating one hands the award over to Ops; by itself it does not release, execute, assign or bill anything."
                        : `${existingLinkedWorkOrderCount} Work Order(s) already exist for this Commercial Offer. See "Work Orders from this offer" below.`}
                    </p>
                  </article>
                ) : null}

                {lifecycleGuidanceError ? <p style={{ color: "crimson" }}>{lifecycleGuidanceError}</p> : null}
                {lifecycleGuidanceLoading ? <p>Loading lifecycle guidance...</p> : null}
                {lifecycleGuidance ? (
                  <>
                    <article style={{ padding: "12px", border: "1px solid #93c5fd", background: "#eff6ff", marginBottom: "12px", minWidth: 0 }}>
                      <strong>{lifecycleGuidance.lifecycle_state_label}</strong>
                      <p style={{ margin: "6px 0 0 0", ...SAFE_LONG_TEXT_STYLE }}>{lifecycleGuidance.advisory_message}</p>
                      <p style={{ margin: "6px 0 0 0", fontStyle: "italic", ...SAFE_LONG_TEXT_STYLE }}>
                        Recommended next action: {lifecycleGuidance.recommended_next_action}
                      </p>
                    </article>

                    <dl style={COMPACT_DETAIL_GRID_STYLE}>
                      <DetailRow label="Commercially active">{lifecycleGuidance.is_commercially_active ? "Yes" : "No"}</DetailRow>
                      <DetailRow label="Can make a new version">{lifecycleGuidance.can_make_new_version ? "Yes" : "No"}</DetailRow>
                      {lifecycleGuidance.has_open_revision_awaiting_resubmission ? (
                        <DetailRow label="Legacy revision awaiting closure">Yes</DetailRow>
                      ) : null}
                      <DetailRow label="Can record a customer response">{lifecycleGuidance.can_record_customer_response ? "Yes" : "No"}</DetailRow>
                      <DetailRow label="Ready to create the Work Order">
                        {lifecycleGuidance.linked_work_orders.length > 0
                          ? lifecycleGuidance.work_order_handoff_available
                            ? "Yes, for what is not on a Work Order yet"
                            : "Already created"
                          : lifecycleGuidance.work_order_handoff_available
                            ? "Yes"
                            : "No"}
                      </DetailRow>
                    </dl>

                    {lifecycleGuidance.work_order_handoff_blocked_reasons.length > 0 ? (
                      <div style={{ marginTop: "12px", padding: "12px", border: "1px solid #f59e0b", background: "#fffbeb", color: "#92400e", minWidth: 0 }}>
                        <strong>A Work Order cannot be created:</strong>
                        <ul style={{ margin: "6px 0 0 0", paddingLeft: "20px" }}>
                          {lifecycleGuidance.work_order_handoff_blocked_reasons.map((reason) => (
                            <li key={reason} style={SAFE_LONG_TEXT_STYLE}>{reason}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    {lifecycleGuidance.linked_work_orders.length > 0 ? (
                      <div style={{ marginTop: "12px" }}>
                        <strong>Work Orders from this offer:</strong>
                        <div style={{ display: "grid", gap: "8px", marginTop: "8px" }}>
                          {lifecycleGuidance.linked_work_orders.map((workOrder) => (
                            <div
                              key={workOrder.public_id}
                              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap", padding: "8px 12px", border: "1px solid #ddd", background: "#ffffff", minWidth: 0 }}
                            >
                              <span style={SAFE_LONG_TEXT_STYLE}>{workOrder.work_order_code} · {formatWorkOrderStatusLabel(workOrder.work_order_status_code)}</span>
                              <a
                                href={hrefWithReturnTarget(`/work-orders/${workOrder.public_id}`, commercialOfferReturnTo, "Back to Commercial Offer")}
                                style={BUTTON_STYLE}
                              >
                                Open Work Order
                              </a>
                            </div>
                          ))}
                        </div>
                        <p style={{ margin: "8px 0 0 0", color: "#6b7280" }}>
                          {existingWorkOrdersNote(canOfferCreateWorkOrderAction && pageAccess.canCreateWorkOrder)}
                        </p>
                      </div>
                    ) : null}

                    {canOfferCreateWorkOrderAction && pageAccess.canCreateWorkOrder ? (
                      <p style={{ marginTop: "12px" }}>
                        <a href={`/work-orders/new?commercialOfferId=${encodeURIComponent(commercialOffer.public_id)}`} style={BUTTON_STYLE}>
                          {createWorkOrderActionLabel}
                        </a>
                      </p>
                    ) : null}
                  </>
                ) : !lifecycleGuidanceLoading ? <p>Lifecycle guidance is not available yet.</p> : null}
              </SectionCard>
            </SectionGroup>

            <SectionGroup id="co-submission-prepare" title="Prepare" tone="teal" description="Check the offer is ready, and record the credit review.">
              <SectionCard title="Submission Readiness" soft>
            <p style={{ marginTop: 0 }}>
              A checklist to help judge whether this offer is ready to send to the customer. It is advice only: it does not
              approve wording or credit, and it does not stop any action.
            </p>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap" }}>
              <div>
                {submissionReadiness ? (
                  <span
                    style={{
                      display: "inline-block",
                      padding: "6px 10px",
                      border: `1px solid ${readinessStatusStyle(submissionReadiness.readiness_status).borderColor}`,
                      background: readinessStatusStyle(submissionReadiness.readiness_status).background,
                      color: readinessStatusStyle(submissionReadiness.readiness_status).color,
                      fontWeight: 700,
                    }}
                  >
                    {formatStatusLabel(submissionReadiness.readiness_status)}
                  </span>
                ) : (
                  <span style={{ color: "#6b7280" }}>Submission readiness not loaded yet.</span>
                )}
                {submissionReadiness ? (
                  <div style={{ marginTop: "8px", display: "flex", gap: "10px", flexWrap: "wrap", color: "#6b7280" }}>
                    <span>Passed: {submissionReadiness.summary.passed_count}</span>
                    <span>Warnings: {submissionReadiness.summary.warning_count}</span>
                    <span>Blocking: {submissionReadiness.summary.blocking_count}</span>
                    <span>Not built yet: {submissionReadiness.summary.deferred_count}</span>
                  </div>
                ) : null}
              </div>
              <div style={{ display: "flex", gap: "10px", alignItems: "flex-end", flexWrap: "wrap" }}>
                <label style={{ display: "grid", gap: "4px", minWidth: "220px" }}>
                  T&amp;C recommendation basis
                  <select
                    value={tcRecommendationBasis}
                    onChange={(event) => {
                      const nextBasis = event.target.value;
                      setTcRecommendationBasis(nextBasis);
                      setTcRecommendedMessage("");
                      setTcRecommendedError("");
                      setSubmissionReadinessError("");
                      const token = getToken();
                      if (token) {
                        void loadTcClauseReadiness(commercialOffer.public_id, token, nextBasis);
                        void loadSubmissionReadiness(commercialOffer.public_id, token, nextBasis);
                      }
                    }}
                    style={{ padding: "8px" }}
                  >
                    {TC_RECOMMENDATION_BASIS_OPTIONS.map((option) => (
                      <option key={option.value || "none"} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  onClick={() => {
                    const token = getToken();
                    if (token) void loadSubmissionReadiness(commercialOffer.public_id, token);
                  }}
                  disabled={submissionReadinessLoading}
                  style={MUTED_BUTTON_STYLE}
                >
                  {submissionReadinessLoading ? "Checking..." : "Refresh readiness"}
                </button>
              </div>
            </div>

            {submissionReadinessError ? <p style={{ color: "crimson" }}>{submissionReadinessError}</p> : null}
            {submissionReadinessLoading ? <p>Loading submission readiness...</p> : null}

            {submissionReadiness ? (
              <div style={{ display: "grid", gap: "10px", marginTop: "14px" }}>
                {submissionReadiness.checklist_items.map((item) => {
                  const itemStyle = readinessStatusStyle(item.status);
                  return (
                    <article key={item.code} style={{ padding: "10px", border: "1px solid #e5e7eb", background: "#ffffff", minWidth: 0 }}>
                      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", alignItems: "start", gap: "10px" }}>
                        <div style={{ minWidth: 0 }}>
                          <strong>{item.label}</strong>
                          <p style={{ margin: "4px 0 0", color: "#374151", overflowWrap: "anywhere" }}>{item.message}</p>
                        </div>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "4px 8px",
                            border: `1px solid ${itemStyle.borderColor}`,
                            background: itemStyle.background,
                            color: itemStyle.color,
                            fontWeight: 700,
                            justifySelf: "end",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {item.status === "DEFERRED" ? "Not built yet" : formatStatusLabel(item.status)}
                        </span>
                      </div>
                      {item.deferred ? (
                        <p style={{ margin: "8px 0 0", color: "#6b7280" }}>Not built yet - listed so you know it is planned.</p>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            ) : null}
              </SectionCard>

              <SectionCard title="Credit / Exposure Review" soft>
                <p style={{ marginTop: 0 }}>
                  Record manual credit/exposure readiness evidence for this Commercial Offer. This does not calculate exposure, consume an Account/PAN credit limit,
                  run Finance approval workflow or block lifecycle actions.
                </p>
                <p style={{ color: "#6b7280" }}>
                  PAN-level exposure, overdue/WIP/open-offer/open-Work-Order aggregation and ledger integration remain future controls.
                </p>

                {creditReviewLoading ? <p>Loading manual credit/exposure reviews...</p> : null}

                {creditReviews.length > 0 ? (
                  <>
                    <div style={{ padding: "12px", border: "1px solid #bfdbfe", background: "#eff6ff", marginBottom: "12px" }}>
                      <strong>Current review: {formatStatusLabel(creditReviews[0].review_status)}</strong>
                      <dl style={{ ...COMPACT_DETAIL_GRID_STYLE, margin: "10px 0 0" }}>
                        <DetailRow label="Reviewed at">{formatDateTime(creditReviews[0].reviewed_at)}</DetailRow>
                        <DetailRow label="Review basis">{displayValue(creditReviews[0].review_basis)}</DetailRow>
                        <DetailRow label="Review reference">{displayValue(creditReviews[0].review_reference)}</DetailRow>
                        <DetailRow label="Approved amount snapshot">
                          {formatMoney(creditReviews[0].approved_amount_snapshot, commercialOffer.currency_code)}
                        </DetailRow>
                        <DetailRow label="Credit days snapshot">
                          {creditReviews[0].credit_days_snapshot ?? "-"}
                        </DetailRow>
                      </dl>
                    </div>

                    <div style={{ display: "grid", gap: "10px" }}>
                      {creditReviews.map((review) => (
                        <article key={review.public_id} style={{ padding: "12px", border: "1px solid #e5e7eb", background: "#ffffff", minWidth: 0 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "10px", flexWrap: "wrap" }}>
                            <strong>{formatStatusLabel(review.review_status)}</strong>
                            <span style={{ color: review.active ? "#065f46" : "#6b7280", fontWeight: 700 }}>
                              {review.active ? "Current" : "Superseded"}
                            </span>
                          </div>
                          <dl style={{ ...COMPACT_DETAIL_GRID_STYLE, marginTop: "10px" }}>
                            <DetailRow label="Reviewed at">{formatDateTime(review.reviewed_at)}</DetailRow>
                            <DetailRow label="Basis">{displayValue(review.review_basis)}</DetailRow>
                            <DetailRow label="Reference">{displayValue(review.review_reference)}</DetailRow>
                            <DetailRow label="Exposure note">
                              <span style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{displayValue(review.exposure_note)}</span>
                            </DetailRow>
                          </dl>
                        </article>
                      ))}
                    </div>
                  </>
                ) : (
                  <p>No manual credit/exposure review evidence has been recorded yet.</p>
                )}

                {pageAccess.canWorkCreditReview && !offerContentIsLocked ? (
                  <form onSubmit={handleAddCreditReview} style={{ display: "grid", gap: "12px", marginTop: "16px", padding: "12px", border: "1px solid #bfdbfe", background: "#ffffff" }}>
                    <h4 style={{ margin: 0 }}>Record manual credit/exposure review</h4>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
                      <label style={{ display: "grid", gap: "4px" }}>
                        Review status
                        <select
                          value={creditReviewForm.review_status}
                          onChange={(event) => {
                            setCreditReviewForm((current) => ({ ...current, review_status: event.target.value }));
                            setCreditReviewMessage("");
                            setCreditReviewError("");
                          }}
                          style={{ padding: "8px" }}
                        >
                          {CREDIT_REVIEW_STATUS_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </label>
                      <label style={{ display: "grid", gap: "4px" }}>
                        Reviewed date/time
                        <DateInput
                          withTime
                          value={creditReviewForm.reviewed_at}
                          onChange={(event) => {
                            setCreditReviewForm((current) => ({ ...current, reviewed_at: event.target.value }));
                            setCreditReviewMessage("");
                            setCreditReviewError("");
                          }}
                          style={{ padding: "8px" }}
                        />
                      </label>
                      <label style={{ display: "grid", gap: "4px" }}>
                        Review basis
                        <input
                          value={creditReviewForm.review_basis}
                          onChange={(event) => {
                            setCreditReviewForm((current) => ({ ...current, review_basis: event.target.value }));
                            setCreditReviewMessage("");
                            setCreditReviewError("");
                          }}
                          placeholder="Manual review, Finance note, PAN-level review"
                          maxLength={255}
                          style={{ padding: "8px" }}
                        />
                      </label>
                      <label style={{ display: "grid", gap: "4px" }}>
                        Review reference
                        <input
                          value={creditReviewForm.review_reference}
                          onChange={(event) => {
                            setCreditReviewForm((current) => ({ ...current, review_reference: event.target.value }));
                            setCreditReviewMessage("");
                            setCreditReviewError("");
                          }}
                          placeholder="Finance note or approval email reference"
                          maxLength={255}
                          style={{ padding: "8px" }}
                        />
                      </label>
                      <label style={{ display: "grid", gap: "4px" }}>
                        Approved amount snapshot
                        <input
                          value={creditReviewForm.approved_amount_snapshot}
                          onChange={(event) => {
                            setCreditReviewForm((current) => ({ ...current, approved_amount_snapshot: event.target.value }));
                            setCreditReviewMessage("");
                            setCreditReviewError("");
                          }}
                          type="number"
                          min="0"
                          step="0.01"
                          style={{ padding: "8px" }}
                        />
                      </label>
                      <label style={{ display: "grid", gap: "4px" }}>
                        Credit days snapshot
                        <input
                          value={creditReviewForm.credit_days_snapshot}
                          onChange={(event) => {
                            setCreditReviewForm((current) => ({ ...current, credit_days_snapshot: event.target.value }));
                            setCreditReviewMessage("");
                            setCreditReviewError("");
                          }}
                          type="number"
                          min="0"
                          max="3650"
                          step="1"
                          style={{ padding: "8px" }}
                        />
                      </label>
                    </div>

                    <label style={{ display: "grid", gap: "4px" }}>
                      Exposure note
                      <textarea
                        value={creditReviewForm.exposure_note}
                        onChange={(event) => {
                          setCreditReviewForm((current) => ({ ...current, exposure_note: event.target.value }));
                          setCreditReviewMessage("");
                          setCreditReviewError("");
                        }}
                        rows={3}
                        maxLength={4000}
                        style={{ padding: "8px" }}
                      />
                    </label>

                    <div>
                      <button type="submit" disabled={creditReviewSaving}>
                        {creditReviewSaving ? "Recording..." : "Record manual credit/exposure review"}
                      </button>
                    </div>
                    {creditReviewMessage ? <p style={{ color: "#065f46", margin: 0 }}>{creditReviewMessage}</p> : null}
                    {creditReviewError ? <p style={{ color: "crimson", margin: 0 }}>{creditReviewError}</p> : null}
                  </form>
                ) : offerContentIsLocked ? (
                  <p className="helper-text">{lockedContentNote}</p>
                ) : (
                  <p style={{ color: "#6b7280" }}>Manual credit/exposure review capture is restricted to Sales and Admin roles. Read-only roles can view review history.</p>
                )}
              </SectionCard>
            </SectionGroup>

            <SectionGroup id="co-submission-quote" title="Quotation and submission" tone="amber" description="Generate and approve the quotation, record how it was sent, then mark the offer as submitted.">
              <SectionCard title="Quotation Document" soft>
                <p style={{ marginTop: 0 }}>
                  Generate a versioned quotation document from this offer's current lines and attached header T&amp;C
                  clauses. The document is a web page - print it to PDF from the browser's Print dialog to
                  produce the file to send. Generating a new version supersedes any earlier version; a superseded version
                  keeps its own approval history and can still be downloaded.
                </p>
                <p style={{ color: "#6b7280" }}>
                  Only a version <strong>Approved for Issue</strong> should be shared with the customer. Approval records who
                  approved it and when - it does not itself change who can open this Draft, since anyone who can read this
                  offer can already see every figure on this page.
                </p>

                {quoteDocumentsLoading ? <p>Loading quotation documents...</p> : null}
                {quoteDocumentsError ? <p style={{ color: "crimson" }}>{quoteDocumentsError}</p> : null}

                {quoteDocuments.length > 0 ? (
                  <div style={{ display: "grid", gap: "12px" }}>
                    {quoteDocuments.map((doc) => {
                      const isApproved = doc.quote_status_code === "APPROVED_FOR_ISSUE";
                      const isSuperseded = Boolean(doc.superseded_at);
                      return (
                        <article
                          key={doc.public_id}
                          style={{ padding: "12px", border: "1px solid #ddd", background: isSuperseded ? "#f9fafb" : "#ffffff", minWidth: 0 }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap" }}>
                            <div style={{ minWidth: 0 }}>
                              <strong>{doc.quote_reference}</strong>
                              {isSuperseded ? (
                                <span style={{ marginLeft: "8px", color: "#6b7280", fontWeight: 400 }}>(superseded)</span>
                              ) : null}
                            </div>
                            <span style={{ fontWeight: 700, color: isApproved ? "#065f46" : "#92400e" }}>
                              {isApproved ? "Approved for Issue" : "Draft"}
                            </span>
                          </div>
                          {doc.is_stale ? (
                            <p style={{ margin: "8px 0 0", color: "#92400e" }}>
                              The offer has changed since this version was generated. Consider generating a new version
                              before issuing this one.
                            </p>
                          ) : null}
                          <dl style={{ ...COMPACT_DETAIL_GRID_STYLE, marginTop: "10px" }}>
                            <DetailRow label="Generated at">{formatDateTime(doc.generated_at)}</DetailRow>
                            <DetailRow label="Prepared by">{displayValue(doc.generated_by_display_name ?? doc.generated_by)}</DetailRow>
                            <DetailRow label="Approved at">{formatDateTime(doc.approved_at)}</DetailRow>
                            <DetailRow label="Approved by">{displayValue(doc.approved_by_display_name ?? doc.approved_by)}</DetailRow>
                            <DetailRow label="Approval note">{displayValue(doc.approval_note)}</DetailRow>
                          </dl>
                          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "10px", alignItems: "center" }}>
                            {/* The frozen document no longer states its own approval status - it
                                cannot, because generation always precedes approval. The button is
                                therefore where an unapproved version is called what it is, so a
                                Draft is not downloaded and sent believing it was approved. */}
                            <button type="button" onClick={() => downloadQuoteDocument(doc)}>
                              {isApproved ? "Download" : "Download draft (not approved for issue)"}
                            </button>
                            {/* Offered only while the backend reports no reason this version cannot
                                be approved. The reason comes from the same backend function that
                                refuses the approval, so the button no longer appears on a version
                                that could not be approved when the page loaded (a concluded offer,
                                an unpriced line, an outdated version). The server still re-checks. */}
                            {!isApproved && !isSuperseded && !doc.approval_blocked_reason && pageAccess.canApproveQuoteDocument ? (
                              <button
                                type="button"
                                onClick={() => handleApproveQuoteDocument(doc.public_id)}
                                disabled={quoteDocumentApprovingId === doc.public_id}
                              >
                                {quoteDocumentApprovingId === doc.public_id ? "Approving..." : "Approve for Issue"}
                              </button>
                            ) : null}
                          </div>
                          {!isApproved && !isSuperseded && doc.approval_blocked_reason ? (
                            <p style={{ margin: "6px 0 0", color: "#92400e" }}>
                              Cannot be approved for issue: {doc.approval_blocked_reason}
                            </p>
                          ) : null}
                          {quoteDocumentDownloadErrors[doc.public_id] ? (
                            <p style={{ color: "crimson", margin: "6px 0 0" }}>{quoteDocumentDownloadErrors[doc.public_id]}</p>
                          ) : null}
                          {quoteDocumentApproveMessages[doc.public_id] ? (
                            <p style={{ color: "#065f46", margin: "6px 0 0" }}>{quoteDocumentApproveMessages[doc.public_id]}</p>
                          ) : null}
                          {quoteDocumentApproveErrors[doc.public_id] ? (
                            <p style={{ color: "crimson", margin: "6px 0 0" }}>{quoteDocumentApproveErrors[doc.public_id]}</p>
                          ) : null}
                        </article>
                      );
                    })}
                  </div>
                ) : (
                  <p>No quotation document has been generated yet.</p>
                )}

                {pageAccess.canGenerateQuoteDocument ? (
                  <div style={{ marginTop: "16px", padding: "12px", border: "1px solid #bfdbfe", background: "#ffffff" }}>
                    <button type="button" onClick={handleGenerateQuoteDocument} disabled={quoteDocumentGenerating}>
                      {quoteDocumentGenerating ? "Generating..." : "Generate quotation document"}
                    </button>
                    {quoteDocumentGenerateMessage ? (
                      <p style={{ color: "#065f46", margin: "8px 0 0" }}>{quoteDocumentGenerateMessage}</p>
                    ) : null}
                    {quoteDocumentGenerateError ? (
                      <p style={{ color: "crimson", margin: "8px 0 0" }}>{quoteDocumentGenerateError}</p>
                    ) : null}
                  </div>
                ) : (
                  <p style={{ color: "#6b7280" }}>Generating a quotation document is restricted to Sales and Admin roles.</p>
                )}
              </SectionCard>

              <SectionCard title="Submission Evidence" soft>
            <p style={{ marginTop: 0 }}>
              Record metadata showing that the Commercial Offer, customer-format quote or tender bid was submitted or shared with the customer.
              This does not generate the quote document, upload or store files, run SharePoint automation, approve T&amp;C wording or calculate credit exposure.
            </p>
            <p style={{ color: "#6b7280" }}>
              Use the document reference fields only for external metadata such as email subject, tender portal reference or SharePoint path kept outside this system.
            </p>

            {submissionEvidenceLoading ? <p>Loading submission evidence...</p> : null}

            {submissionEvidence.length > 0 ? (
              <div style={{ display: "grid", gap: "12px" }}>
                {submissionEvidence.map((evidence) => (
                  <article key={evidence.public_id} style={{ padding: "12px", border: "1px solid #ddd", background: "#ffffff", minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap" }}>
                      <div style={{ minWidth: 0 }}>
                        <strong>{formatStatusLabel(evidence.submission_channel)}</strong>
                        <div style={{ color: "#6b7280", overflowWrap: "anywhere" }}>
                          {displayValue(evidence.submission_reference)}
                        </div>
                      </div>
                      <span style={{ fontWeight: 700, color: "#065f46" }}>Recorded</span>
                    </div>
                    <dl style={{ ...COMPACT_DETAIL_GRID_STYLE, marginTop: "10px" }}>
                      <DetailRow label="Submitted at">{formatDateTime(evidence.submitted_at)}</DetailRow>
                      <DetailRow label="Recipient summary">
                        <span style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{displayValue(evidence.recipient_summary)}</span>
                      </DetailRow>
                      <DetailRow label="Amount snapshot">
                        {formatMoney(evidence.submitted_amount_snapshot, evidence.submitted_currency_snapshot || commercialOffer.currency_code)}
                      </DetailRow>
                      <DetailRow label="Submitted version / revision">{displayValue(evidence.submitted_version_snapshot)}</DetailRow>
                      <DetailRow label="Document label">{displayValue(evidence.document_reference_label)}</DetailRow>
                      <DetailRow label="Document reference">
                        <span style={{ overflowWrap: "anywhere" }}>{displayValue(evidence.document_reference_url_or_path)}</span>
                      </DetailRow>
                      <DetailRow label="Evidence notes">
                        <span style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{displayValue(evidence.evidence_notes)}</span>
                      </DetailRow>
                      <DetailRow label="Recorded at">{formatDateTime(evidence.created_at)}</DetailRow>
                    </dl>
                  </article>
                ))}
              </div>
            ) : (
              <p>No submission evidence metadata has been recorded yet.</p>
            )}

            {pageAccess.canWorkSubmissionEvidence && !offerContentIsLocked ? (
              <form onSubmit={handleAddSubmissionEvidence} style={{ display: "grid", gap: "12px", marginTop: "16px", padding: "12px", border: "1px solid #bfdbfe", background: "#ffffff" }}>
                <h4 style={{ margin: 0 }}>Record submission evidence metadata</h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Channel
                    <select
                      value={submissionEvidenceForm.submission_channel}
                      onChange={(event) => {
                        setSubmissionEvidenceForm((current) => ({ ...current, submission_channel: event.target.value }));
                        setSubmissionEvidenceMessage("");
                        setSubmissionEvidenceError("");
                      }}
                      style={{ padding: "8px" }}
                    >
                      {SUBMISSION_CHANNEL_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Submitted date/time
                    <DateInput
                      withTime
                      value={submissionEvidenceForm.submitted_at}
                      onChange={(event) => {
                        setSubmissionEvidenceForm((current) => ({ ...current, submitted_at: event.target.value }));
                        setSubmissionEvidenceMessage("");
                        setSubmissionEvidenceError("");
                      }}
                      style={{ padding: "8px" }}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Submission reference
                    <input
                      value={submissionEvidenceForm.submission_reference}
                      onChange={(event) => {
                        setSubmissionEvidenceForm((current) => ({ ...current, submission_reference: event.target.value }));
                        setSubmissionEvidenceMessage("");
                        setSubmissionEvidenceError("");
                      }}
                      maxLength={255}
                      placeholder="Portal, email or customer reference"
                      title="Record the customer, tender, email or portal reference proving that the offer was submitted."
                      style={{ padding: "8px" }}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Submitted version / revision
                    <input
                      value={submissionEvidenceForm.submitted_version_snapshot}
                      onChange={(event) => {
                        setSubmissionEvidenceForm((current) => ({ ...current, submitted_version_snapshot: event.target.value }));
                        setSubmissionEvidenceMessage("");
                        setSubmissionEvidenceError("");
                      }}
                      maxLength={50}
                      placeholder="Rev 1, V2, corrected bid"
                      title="Optional: record the offer version, revision, or bid version submitted to the customer."
                      style={{ padding: "8px" }}
                    />
                  </label>
                </div>

                <label style={{ display: "grid", gap: "4px" }}>
                  Recipient summary
                  <textarea
                    value={submissionEvidenceForm.recipient_summary}
                    onChange={(event) => {
                      setSubmissionEvidenceForm((current) => ({ ...current, recipient_summary: event.target.value }));
                      setSubmissionEvidenceMessage("");
                      setSubmissionEvidenceError("");
                    }}
                    rows={3}
                    maxLength={1000}
                    style={{ padding: "8px" }}
                  />
                </label>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Document reference label
                    <input
                      value={submissionEvidenceForm.document_reference_label}
                      onChange={(event) => {
                        setSubmissionEvidenceForm((current) => ({ ...current, document_reference_label: event.target.value }));
                        setSubmissionEvidenceMessage("");
                        setSubmissionEvidenceError("");
                      }}
                      maxLength={255}
                      style={{ padding: "8px" }}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Document URL/path/reference
                    <input
                      value={submissionEvidenceForm.document_reference_url_or_path}
                      onChange={(event) => {
                        setSubmissionEvidenceForm((current) => ({ ...current, document_reference_url_or_path: event.target.value }));
                        setSubmissionEvidenceMessage("");
                        setSubmissionEvidenceError("");
                      }}
                      maxLength={1000}
                      style={{ padding: "8px" }}
                    />
                  </label>
                </div>

                <label style={{ display: "grid", gap: "4px" }}>
                  Evidence notes
                  <textarea
                    value={submissionEvidenceForm.evidence_notes}
                    onChange={(event) => {
                      setSubmissionEvidenceForm((current) => ({ ...current, evidence_notes: event.target.value }));
                      setSubmissionEvidenceMessage("");
                      setSubmissionEvidenceError("");
                    }}
                    rows={3}
                    maxLength={4000}
                    style={{ padding: "8px" }}
                  />
                </label>

                <div>
                  <button type="submit" disabled={submissionEvidenceSaving}>
                    {submissionEvidenceSaving ? "Recording..." : "Record submission evidence"}
                  </button>
                </div>
              </form>
            ) : offerContentIsLocked ? (
              <p className="helper-text">{lockedContentNote}</p>
            ) : (
              <p style={{ color: "#6b7280" }}>Submission evidence capture is restricted to Sales and Admin roles. Read-only roles can view existing evidence.</p>
            )}
            {submissionEvidenceMessage ? <p style={{ color: "#065f46" }}>{submissionEvidenceMessage}</p> : null}
            {submissionEvidenceError ? <p style={{ color: "crimson" }}>{submissionEvidenceError}</p> : null}
              </SectionCard>

              <SectionCard title="Record as Submitted / Commercially Committed" soft>
                <p style={{ marginTop: 0 }}>
                  Recording as submitted means this Commercial Offer has been shared with the customer and is now commercially committed.
                </p>
                <p style={{ color: "#6b7280" }}>
                  This action does not generate or send a quote/PDF, upload or store files, run SharePoint automation, calculate exposure,
                  complete Finance approval workflow or create/release a Work Order.
                </p>
                <dl style={COMPACT_DETAIL_GRID_STYLE}>
                  <DetailRow label="Current status">{formatStatusLabel(commercialOffer.offer_status_code)}</DetailRow>
                  <DetailRow label="Submission evidence">
                    {submissionEvidence.length > 0 ? `${submissionEvidence.length} record(s) available` : "Not recorded"}
                  </DetailRow>
                  <DetailRow label="Latest credit review">
                    {creditReviews.length > 0 ? formatStatusLabel(creditReviews[0].review_status) : "Not recorded (readiness warning only)"}
                  </DetailRow>
                </dl>

                {pageAccess.canWorkCommercialOffer && COMMERCIAL_OFFER_MARK_SUBMITTED_STATUSES.includes(
                  commercialOffer.offer_status_code as typeof COMMERCIAL_OFFER_MARK_SUBMITTED_STATUSES[number],
                ) ? (
                  <div style={{ marginTop: "12px" }}>
                    <button type="button" onClick={() => void handleMarkSubmitted()} disabled={markSubmittedSaving}>
                      {markSubmittedSaving ? "Recording submission..." : "Record as Submitted / Commercially Committed"}
                    </button>
                  </div>
                ) : pageAccess.canWorkCommercialOffer ? (
                  <p style={{ color: "#6b7280" }}>
                    This controlled action is available only while the Commercial Offer is Draft or Ready for Review.
                  </p>
                ) : (
                  <p style={{ color: "#6b7280" }}>Your role can view submission lifecycle status but cannot record this action.</p>
                )}

                {markSubmittedMessage ? <p style={{ color: "#065f46" }}>{markSubmittedMessage}</p> : null}
                {markSubmittedWarning ? <p style={{ color: "#92400e" }}>{markSubmittedWarning}</p> : null}
                {markSubmittedError ? <p style={{ color: "crimson" }}>{markSubmittedError}</p> : null}
              </SectionCard>
            </SectionGroup>

            <SectionGroup id="co-submission-outcome" title="Customer response" tone="violet" description="Record what the customer said, and any revision they asked for.">
              <SectionCard title="Customer Response / Award Outcome" soft>
                <p style={{ marginTop: 0 }}>
                  Record the customer&apos;s post-submission response. Accepted / awarded may move this Commercial Offer to Accepted;
                  rejected / lost may move it to Rejected. Other outcomes preserve the current lifecycle status.
                </p>
                <p style={{ color: "#374151" }}>
                  Recording a response never creates a Work Order by itself. Once the offer is accepted, create the Work Order separately.
                </p>
                {customerResponsesLoading ? <p>Loading customer response history...</p> : null}

                {latestCustomerResponse ? (
                  <article style={{ padding: "12px", border: "1px solid #86efac", background: "#f0fdf4", marginBottom: "12px", minWidth: 0 }}>
                    <strong>Latest / current interpretation: {formatStatusLabel(latestCustomerResponse.response_outcome)}</strong>
                    <div style={{ color: "#4b5563", marginTop: "4px", ...SAFE_LONG_TEXT_STYLE }}>
                      {displayValue(latestCustomerResponse.response_reference)} · {formatDateTime(latestCustomerResponse.response_received_at)}
                    </div>
                  </article>
                ) : <p>No customer response / award outcome has been recorded.</p>}

                {customerResponses.length > 0 ? (
                  <div style={{ display: "grid", gap: "12px", marginBottom: "16px" }}>
                    {customerResponses.map((item, index) => {
                      const linkedEvidence = submissionEvidence.find((evidence) => evidence.public_id === item.linked_submission_evidence_public_id);
                      const linkedRevision = revisions.find((revision) => revision.public_id === item.linked_revision_public_id);
                      return (
                        <article key={item.public_id} style={{ padding: "12px", border: "1px solid #d1d5db", background: "#ffffff", minWidth: 0, overflowWrap: "anywhere" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                            <strong>{formatStatusLabel(item.response_outcome)}</strong>
                            {index === 0 ? <span style={{ color: "#065f46", fontWeight: 700 }}>Latest</span> : null}
                          </div>
                          <dl style={{ ...COMPACT_DETAIL_GRID_STYLE, marginTop: "10px" }}>
                            <DetailRow label="Response reference"><span style={SAFE_LONG_TEXT_STYLE}>{displayValue(item.response_reference)}</span></DetailRow>
                            <DetailRow label="Received at">{formatDateTime(item.response_received_at)}</DetailRow>
                            <DetailRow label="Channel">{formatStatusLabel(item.response_channel)}</DetailRow>
                            <DetailRow label="Received from"><span style={SAFE_LONG_TEXT_STYLE}>{displayValue(item.received_from)}</span></DetailRow>
                            {item.awarded_amount_snapshot !== null && item.awarded_amount_snapshot !== undefined ? (
                              <DetailRow label="Awarded amount">{formatMoney(item.awarded_amount_snapshot, item.awarded_currency_snapshot ?? "INR")}</DetailRow>
                            ) : null}
                            {item.awarded_version_snapshot ? <DetailRow label="Awarded version"><span style={SAFE_LONG_TEXT_STYLE}>{item.awarded_version_snapshot}</span></DetailRow> : null}
                            {item.customer_po_or_wo_reference ? <DetailRow label="Customer PO / WO reference"><span style={SAFE_LONG_TEXT_STYLE}>{item.customer_po_or_wo_reference}</span></DetailRow> : null}
                            {item.linked_submission_evidence_public_id ? <DetailRow label="Linked submission evidence"><span style={SAFE_LONG_TEXT_STYLE}>{linkedEvidence ? formatSubmissionEvidenceDetail(linkedEvidence) : item.linked_submission_evidence_public_id}</span></DetailRow> : null}
                            {item.linked_revision_public_id ? <DetailRow label="Linked revision"><span style={SAFE_LONG_TEXT_STYLE}>{linkedRevision ? `${linkedRevision.revision_label} · ${formatStatusLabel(linkedRevision.revision_status)} · ${formatDateTime(linkedRevision.opened_at)}` : item.linked_revision_public_id}</span></DetailRow> : null}
                            {item.customer_response_notes ? <DetailRow label="Notes"><span style={{ whiteSpace: "pre-wrap", ...SAFE_LONG_TEXT_STYLE }}>{item.customer_response_notes}</span></DetailRow> : null}
                          </dl>
                        </article>
                      );
                    })}
                  </div>
                ) : null}

                {pageAccess.canWorkCustomerResponses && customerResponseCapability === "allowed" ? (
                  <form onSubmit={handleRecordCustomerResponse} style={{ display: "grid", gap: "12px", padding: "12px", border: "1px solid #bfdbfe", background: "#ffffff", minWidth: 0 }}>
                    <h4 style={{ margin: 0 }}>Record new customer response</h4>
                    <p style={{ margin: 0, color: "#374151" }}>
                      Available after submission. Current Commercial Offer status: {formatStatusLabel(commercialOffer.offer_status_code)}.
                    </p>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))", gap: "12px", minWidth: 0 }}>
                      <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Outcome
                        <select value={customerResponseForm.response_outcome} onChange={(event) => { setCustomerResponseForm((current) => ({ ...current, response_outcome: event.target.value })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={REVISION_FORM_CONTROL_STYLE}>
                          {CUSTOMER_RESPONSE_OUTCOME_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                        </select>
                      </label>
                      <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Response received at
                        <DateInput withTime required value={customerResponseForm.response_received_at} onChange={(event) => { setCustomerResponseForm((current) => ({ ...current, response_received_at: event.target.value })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={REVISION_FORM_CONTROL_STYLE} />
                      </label>
                      <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Channel
                        <select value={customerResponseForm.response_channel} onChange={(event) => { setCustomerResponseForm((current) => ({ ...current, response_channel: event.target.value })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={REVISION_FORM_CONTROL_STYLE}>
                          {CUSTOMER_RESPONSE_CHANNEL_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                        </select>
                      </label>
                      <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Response reference
                        <input maxLength={255} value={customerResponseForm.response_reference} onChange={(event) => { setCustomerResponseForm((current) => ({ ...current, response_reference: event.target.value })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={REVISION_FORM_CONTROL_STYLE} />
                      </label>
                      <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Received from
                        <input maxLength={255} value={customerResponseForm.received_from} onChange={(event) => { setCustomerResponseForm((current) => ({ ...current, received_from: event.target.value })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={REVISION_FORM_CONTROL_STYLE} />
                      </label>
                      <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Awarded amount
                        <input type="number" min="0" step="0.01" value={customerResponseForm.awarded_amount_snapshot} onChange={(event) => { setCustomerResponseForm((current) => ({ ...current, awarded_amount_snapshot: event.target.value })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={REVISION_FORM_CONTROL_STYLE} />
                      </label>
                      <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Awarded currency
                        <CurrencySelect value={customerResponseForm.awarded_currency_snapshot} onChange={(currencyCode) => { setCustomerResponseForm((current) => ({ ...current, awarded_currency_snapshot: currencyCode })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={REVISION_FORM_CONTROL_STYLE} />
                      </label>
                      <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Awarded version
                        <input maxLength={100} value={customerResponseForm.awarded_version_snapshot} onChange={(event) => { setCustomerResponseForm((current) => ({ ...current, awarded_version_snapshot: event.target.value })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={REVISION_FORM_CONTROL_STYLE} />
                      </label>
                      <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Customer PO / WO reference
                        <input maxLength={255} value={customerResponseForm.customer_po_or_wo_reference} onChange={(event) => { setCustomerResponseForm((current) => ({ ...current, customer_po_or_wo_reference: event.target.value })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={REVISION_FORM_CONTROL_STYLE} />
                      </label>
                      <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Linked submission evidence
                        <select value={customerResponseForm.linked_submission_evidence_public_id} onChange={(event) => { setCustomerResponseForm((current) => ({ ...current, linked_submission_evidence_public_id: event.target.value })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={{ ...REVISION_FORM_CONTROL_STYLE, textOverflow: "ellipsis" }}>
                          <option value="">No evidence link</option>
                          {submissionEvidence.map((item) => <option key={item.public_id} value={item.public_id} title={formatSubmissionEvidenceDetail(item)}>{formatSubmissionEvidenceOptionLabel(item)}</option>)}
                        </select>
                      </label>
                      <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Linked revision
                        <select value={customerResponseForm.linked_revision_public_id} onChange={(event) => { setCustomerResponseForm((current) => ({ ...current, linked_revision_public_id: event.target.value })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={{ ...REVISION_FORM_CONTROL_STYLE, textOverflow: "ellipsis" }}>
                          <option value="">No revision link</option>
                          {revisions.map((item) => <option key={item.public_id} value={item.public_id} title={`${item.revision_label} · ${formatStatusLabel(item.revision_reason)} · ${formatDateTime(item.opened_at)}`}>{item.revision_label} · {formatStatusLabel(item.revision_status)}</option>)}
                        </select>
                      </label>
                    </div>
                    {selectedCustomerResponseEvidence ? <p style={{ margin: 0, color: "#6b7280", ...SAFE_LONG_TEXT_STYLE }}>Selected evidence: {formatSubmissionEvidenceDetail(selectedCustomerResponseEvidence)}</p> : null}
                    {selectedCustomerResponseRevision ? <p style={{ margin: 0, color: "#6b7280", ...SAFE_LONG_TEXT_STYLE }}>Selected revision: {selectedCustomerResponseRevision.revision_label} · {formatStatusLabel(selectedCustomerResponseRevision.revision_reason)} · {formatDateTime(selectedCustomerResponseRevision.opened_at)}</p> : null}
                    <label style={{ display: "grid", gap: "4px", minWidth: 0 }}>Customer response notes
                      <textarea rows={3} maxLength={4000} value={customerResponseForm.customer_response_notes} onChange={(event) => { setCustomerResponseForm((current) => ({ ...current, customer_response_notes: event.target.value })); setCustomerResponseMessage(""); setCustomerResponseError(""); }} style={REVISION_FORM_CONTROL_STYLE} />
                    </label>
                    <div><button type="submit" disabled={customerResponseSaving}>{customerResponseSaving ? "Recording..." : "Record customer response"}</button></div>
                  </form>
                ) : pageAccess.canWorkCustomerResponses && customerResponseCapability === "loading" ? (
                  <p style={{ margin: 0, color: "#6b7280" }}>Checking whether a customer response can be recorded...</p>
                ) : pageAccess.canWorkCustomerResponses && customerResponseCapability === "failed" ? (
                  <div style={{ margin: 0, padding: "12px", border: "1px solid #fecaca", background: "#fef2f2", color: "#991b1b" }}>
                    <p style={{ margin: 0 }}>
                      {lifecycleGuidanceError || "Post-response lifecycle guidance could not be loaded."} Recording a
                      customer response is unavailable until it loads, because whether this Commercial Offer still
                      accepts one is decided by the backend.
                    </p>
                    <button
                      type="button"
                      style={{ marginTop: "8px" }}
                      onClick={() => { void loadLifecycleGuidance(commercialOffer.public_id); }}
                    >
                      Retry
                    </button>
                  </div>
                ) : pageAccess.canWorkCustomerResponses ? (
                  <p style={{ margin: 0, padding: "12px", border: "1px solid #fde68a", background: "#fffbeb", color: "#92400e" }}>
                    {commercialOffer.offer_status_code === "REJECTED"
                      ? "This Commercial Offer was rejected and is final. No further customer response can be recorded against it. If the customer has since awarded this enquiry, record the outcome against the replacement Commercial Offer for this Opportunity."
                      : ["WITHDRAWN", "CLOSED"].includes(commercialOffer.offer_status_code)
                        ? `This Commercial Offer is ${formatStatusLabel(commercialOffer.offer_status_code)}. No further customer response can be recorded against it.`
                        : `A customer response can be recorded only after the Commercial Offer has been submitted. Current status: ${formatStatusLabel(commercialOffer.offer_status_code)}.`}
                  </p>
                ) : <p style={{ color: "#6b7280" }}>Customer response history is visible to your role. Recording is restricted to Sales and Admin roles.</p>}

                {/* Action feedback lives outside the form on purpose. Recording REJECTED_LOST
                    makes the offer final, which unmounts the form - if the success message were
                    inside it, the user would never see confirmation that the response saved. */}
                {customerResponseMessage ? <p style={{ color: "#065f46", margin: "8px 0 0" }}>{customerResponseMessage}</p> : null}
                {customerResponseError ? <p style={{ color: "crimson", margin: "8px 0 0" }}>{customerResponseError}</p> : null}
              </SectionCard>

              <SectionCard title="Offer versions" soft>
                <p style={{ marginTop: 0 }}>
                  Each sent version stays exactly as it was sent. Make a new version to copy its offer details, active lines, T&amp;C,
                  market rates and current credit review into a new editable Draft.
                </p>
                <p style={{ color: "#6b7280" }}>
                  Submission evidence and quotation documents are not copied. Record and generate them afresh before sending the new version.
                </p>

                {offerVersionsLoading ? <p>Loading offer versions...</p> : null}
                {offerVersionsError ? <p style={{ color: "crimson" }}>{offerVersionsError}</p> : null}
                {offerVersions.length > 0 ? (
                  <div style={{ display: "grid", gap: "10px", marginBottom: "16px" }}>
                    {offerVersions.map((version) => {
                      const isCurrent = version.public_id === commercialOffer.public_id;
                      const canAbandon = Boolean(version.previous_version_offer_public_id)
                        && ["DRAFT", "READY_FOR_REVIEW"].includes(version.offer_status_code);
                      return (
                        <article key={version.public_id} style={{ padding: "12px", border: isCurrent ? "2px solid #2563eb" : "1px solid #d1d5db", background: "#ffffff" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                            <div>
                              <a href={`/commercial-offers/${encodeURIComponent(version.public_id)}`} style={{ fontWeight: 700 }}>
                                {offerVersionLabel(version)}
                              </a>
                              {isCurrent ? <span style={{ marginLeft: "8px", color: "#1d4ed8" }}>(open)</span> : null}
                              <div style={{ color: "#6b7280" }}>
                                {formatStatusLabel(version.offer_status_code)}
                                {version.version_reason ? ` - ${formatStatusLabel(version.version_reason)}` : ""}
                              </div>
                            </div>
                            {version.replaced_by_version_number ? (
                              <span style={{ color: "#374151" }}>Replaced by v{version.replaced_by_version_number}</span>
                            ) : null}
                          </div>
                          {version.version_note ? <p style={{ margin: "8px 0 0", whiteSpace: "pre-wrap" }}>{version.version_note}</p> : null}
                          {canAbandon && pageAccess.canWorkRevisions ? (
                            <button
                              type="button"
                              style={{ ...MUTED_BUTTON_STYLE, marginTop: "10px" }}
                              disabled={versionAbandoningId === version.public_id}
                              onClick={() => void handleAbandonVersion(version)}
                            >
                              {versionAbandoningId === version.public_id ? "Abandoning..." : "Abandon this version"}
                            </button>
                          ) : null}
                          {versionActionMessages[version.public_id] ? <p style={{ color: "#065f46", margin: "8px 0 0" }}>{versionActionMessages[version.public_id]}</p> : null}
                          {versionActionErrors[version.public_id] ? <p style={{ color: "crimson", margin: "8px 0 0" }}>{versionActionErrors[version.public_id]}</p> : null}
                        </article>
                      );
                    })}
                  </div>
                ) : null}

                {pageAccess.canWorkRevisions ? (
                  <form onSubmit={handleMakeVersion} style={{ display: "grid", gap: "12px", padding: "12px", border: "1px solid #bfdbfe", background: "#ffffff" }}>
                    <h4 style={{ margin: 0 }}>Make a new version</h4>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Reason
                      <select
                        value={versionForm.version_reason}
                        onChange={(event) => {
                          setVersionForm((current) => ({ ...current, version_reason: event.target.value }));
                          setVersionCreateMessage("");
                          setVersionCreateError("");
                          setCreatedVersionPublicId(null);
                        }}
                        style={REVISION_FORM_CONTROL_STYLE}
                      >
                        {REVISION_REASON_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                      </select>
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Note (optional)
                      <textarea
                        value={versionForm.version_note}
                        onChange={(event) => {
                          setVersionForm((current) => ({ ...current, version_note: event.target.value }));
                          setVersionCreateMessage("");
                          setVersionCreateError("");
                          setCreatedVersionPublicId(null);
                        }}
                        rows={3}
                        maxLength={4000}
                        style={REVISION_FORM_CONTROL_STYLE}
                      />
                    </label>
                    <div>
                      <button type="submit" disabled={versionCreating || lifecycleGuidance?.can_make_new_version !== true}>
                        {versionCreating ? "Making version..." : "Make a new version"}
                      </button>
                    </div>
                    {lifecycleGuidance?.can_make_new_version !== true ? (
                      <p style={{ color: "#6b7280", margin: 0 }}>Available only on the latest Submitted version when no later version is being prepared.</p>
                    ) : null}
                    {versionCreateMessage ? <p style={{ color: "#065f46", margin: 0 }}>{versionCreateMessage}</p> : null}
                    {createdVersionPublicId ? (
                      <p style={{ margin: 0 }}><a href={`/commercial-offers/${encodeURIComponent(createdVersionPublicId)}`}>Open the new version</a></p>
                    ) : null}
                    {versionCreateError ? <p style={{ color: "crimson", margin: 0 }}>{versionCreateError}</p> : null}
                  </form>
                ) : <p style={{ color: "#6b7280" }}>Version history is visible to your role. Version actions are restricted to Sales and Admin roles.</p>}

                {revisions.length > 0 ? <h4>Legacy revision history</h4> : null}

                {revisionsLoading ? <p>Loading revised offers...</p> : null}
                {revisionLoadError ? <p style={{ color: "crimson" }}>{revisionLoadError}</p> : null}

                {revisions.length > 0 ? (
                  <div style={{ display: "grid", gap: "12px", minWidth: 0 }}>
                    {revisions.map((revision) => {
                      const sourceEvidence = submissionEvidence.find((item) => item.public_id === revision.source_submission_evidence_public_id);
                      const resubmissionEvidence = submissionEvidence.find((item) => item.public_id === revision.resubmission_evidence_public_id);
                      const selectedEvidenceId = revisionResubmissionEvidenceIds[revision.public_id] || submissionEvidence[0]?.public_id || "";
                      const selectedResubmissionEvidence =
                        submissionEvidence.find((item) => item.public_id === selectedEvidenceId) ?? null;
                      const isOpen = revision.revision_status === "OPEN";
                      return (
                        <article key={revision.public_id} style={{ padding: "12px", border: "1px solid #d1d5db", background: "#ffffff", minWidth: 0, maxWidth: "100%", overflowWrap: "anywhere", wordBreak: "break-word" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap" }}>
                            <div style={{ minWidth: 0, flex: "1 1 220px" }}>
                              <strong style={SAFE_LONG_TEXT_STYLE}>Revised offer: {revision.revision_label}</strong>
                              <div style={{ color: "#6b7280" }}>{formatStatusLabel(revision.revision_reason)}</div>
                            </div>
                            <span style={{ marginLeft: "auto", padding: "4px 8px", border: "1px solid #d1d5db", background: "#f9fafb", fontWeight: 700, color: revision.revision_status === "OPEN" ? "#92400e" : revision.revision_status === "RESUBMITTED" ? "#065f46" : "#6b7280" }}>
                              {formatRevisionStatusLabel(revision.revision_status)}
                            </span>
                          </div>
                          <dl style={{ ...COMPACT_DETAIL_GRID_STYLE, marginTop: "10px" }}>
                            <DetailRow label="Opened at">{formatDateTime(revision.opened_at)}</DetailRow>
                            {revision.revision_notes ? <DetailRow label="Notes">
                              <span style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{displayValue(revision.revision_notes)}</span>
                            </DetailRow> : null}
                            {revision.source_submission_evidence_public_id ? <DetailRow label="Source submission evidence">
                              <span style={SAFE_LONG_TEXT_STYLE}>{sourceEvidence
                                ? `${displayValue(sourceEvidence.submission_reference)} · ${formatStatusLabel(sourceEvidence.submission_channel)} · ${formatDateTime(sourceEvidence.submitted_at)}`
                                : displayValue(revision.source_submission_evidence_public_id)}</span>
                            </DetailRow> : null}
                            {revision.resubmission_evidence_public_id ? <DetailRow label="Evidence it was re-sent">
                              <span style={SAFE_LONG_TEXT_STYLE}>{resubmissionEvidence
                                ? `${displayValue(resubmissionEvidence.submission_reference)} · ${formatStatusLabel(resubmissionEvidence.submission_channel)} · ${formatDateTime(resubmissionEvidence.submitted_at)}`
                                : displayValue(revision.resubmission_evidence_public_id)}</span>
                            </DetailRow> : null}
                            {revision.revision_status === "RESUBMITTED" && revision.resubmitted_at ? (
                              <DetailRow label="Re-sent at">{formatDateTime(revision.resubmitted_at)}</DetailRow>
                            ) : null}
                            {revision.revision_status === "CANCELLED" && revision.cancelled_at ? (
                              <DetailRow label="Cancelled at">{formatDateTime(revision.cancelled_at)}</DetailRow>
                            ) : null}
                          </dl>

                          {isOpen && pageAccess.canWorkRevisions ? (
                            <div style={{ display: "grid", gap: "10px", marginTop: "12px", paddingTop: "12px", borderTop: "1px solid #e5e7eb", minWidth: 0 }}>
                              <label style={{ display: "grid", gap: "4px", minWidth: 0, maxWidth: "100%" }}>
                                Evidence that it was re-sent
                                <select
                                  value={selectedEvidenceId}
                                  onChange={(event) => {
                                    setRevisionResubmissionEvidenceIds((current) => ({ ...current, [revision.public_id]: event.target.value }));
                                    setRevisionActionMessages((current) => ({ ...current, [revision.public_id]: "" }));
                                    setRevisionActionErrors((current) => ({ ...current, [revision.public_id]: "" }));
                                  }}
                                  style={{ ...REVISION_FORM_CONTROL_STYLE, textOverflow: "ellipsis" }}
                                >
                                  <option value="">Select submission evidence</option>
                                  {submissionEvidence.map((evidence) => (
                                    <option
                                      key={evidence.public_id}
                                      value={evidence.public_id}
                                      title={formatSubmissionEvidenceDetail(evidence)}
                                    >
                                      {formatSubmissionEvidenceOptionLabel(evidence)}
                                    </option>
                                  ))}
                                </select>
                                {selectedResubmissionEvidence ? (
                                  <span style={{ color: "#6b7280", fontSize: "0.9rem", ...SAFE_LONG_TEXT_STYLE }}>
                                    Selected evidence: {formatSubmissionEvidenceDetail(selectedResubmissionEvidence)}
                                  </span>
                                ) : null}
                              </label>
                              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                                <button
                                  type="button"
                                  disabled={revisionActionSavingId === revision.public_id || !selectedEvidenceId}
                                  onClick={() => void handleRevisionAction(revision, "mark-resubmitted")}
                                >
                                  {revisionActionSavingId === revision.public_id ? "Updating..." : "Mark as re-sent"}
                                </button>
                                <button
                                  type="button"
                                  disabled={revisionActionSavingId === revision.public_id}
                                  onClick={() => void handleRevisionAction(revision, "cancel")}
                                  style={MUTED_BUTTON_STYLE}
                                >
                                  Cancel revision
                                </button>
                              </div>
                            </div>
                          ) : null}
                          {revisionActionMessages[revision.public_id] ? <p style={{ color: "#065f46", margin: "10px 0 0" }}>{revisionActionMessages[revision.public_id]}</p> : null}
                          {revisionActionErrors[revision.public_id] ? <p style={{ color: "crimson", margin: "10px 0 0" }}>{revisionActionErrors[revision.public_id]}</p> : null}
                        </article>
                      );
                    })}
                  </div>
                ) : null}

              </SectionCard>
            </SectionGroup>
            </>
          ) : null}

          {activeTab === "overview" ? (
            <>
              <SectionGroup id="co-overview-offer" title="The offer" tone="blue">
              <SectionCard title="Offer snapshot">
            <dl style={DETAIL_GRID_STYLE}>
              <DetailRow label="Offer code / version">{offerVersionLabel(commercialOffer)}</DetailRow>
              <DetailRow label="Offer title">{displayValue(commercialOffer.offer_title)}</DetailRow>
              <DetailRow label="Status">
                <StatusBadge code={commercialOffer.offer_status_code} label={formatStatusLabel(commercialOffer.offer_status_code)} />
              </DetailRow>
              <DetailRow label="Mode / type">
                {formatStatusLabel(commercialOffer.offer_mode)} / {formatStatusLabel(commercialOffer.offer_type)}
              </DetailRow>
              <DetailRow label="Offer value">{formatMoney(commercialOffer.offer_value, commercialOffer.currency_code)}</DetailRow>
            </dl>
              </SectionCard>
              </SectionGroup>

              <SectionGroup id="co-overview-customer" title="Customer and enquiry" tone="teal">
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
            <SectionCard title="Enquiry (Opportunity)">
              <dl style={COMPACT_DETAIL_GRID_STYLE}>
                <DetailRow label="Linked Opportunity">
                  <a
                    href={hrefWithReturnTarget(
                      `/opportunities/${commercialOffer.opportunity_public_id}`,
                      commercialOfferReturnTo,
                      "Back to Commercial Offer",
                    )}
                    style={{ color: "#1d4ed8", fontWeight: 700, textDecoration: "underline" }}
                  >
                    {linkedNames.opportunity ?? "Open Opportunity"}
                  </a>
                </DetailRow>
                <DetailRow label="Reference">
                  <ReferenceText>{commercialOffer.opportunity_public_id}</ReferenceText>
                </DetailRow>
              </dl>
              <p style={{ color: "#6b7280" }}>The enquiry this offer answers.</p>
            </SectionCard>

            <SectionCard title="Customer (Account)">
              {commercialOffer.account_public_id ? (
                <>
                  <dl style={COMPACT_DETAIL_GRID_STYLE}>
                    <DetailRow label="Linked Account">
                      <a
                        href={hrefWithReturnTarget(
                          `/accounts/${commercialOffer.account_public_id}`,
                          commercialOfferReturnTo,
                          "Back to Commercial Offer",
                        )}
                        style={{ color: "#1d4ed8", fontWeight: 700, textDecoration: "underline" }}
                      >
                        {linkedNames.account ?? "Open Account"}
                      </a>
                    </DetailRow>
                    <DetailRow label="Reference">
                      <ReferenceText>{commercialOffer.account_public_id}</ReferenceText>
                    </DetailRow>
                  </dl>
                  <p style={{ color: "#6b7280" }}>
                    The customer this offer is for, taken from the enquiry. Becoming an active customer in Finance is a later, separate step.
                  </p>
                </>
              ) : (
                <div style={{ padding: "12px", border: "1px solid #f59e0b", background: "#fffbeb", color: "#92400e" }}>
                  <p style={{ marginTop: 0 }}>{accountTraceabilityBlockMessage()}</p>
                  <a
                    href={hrefWithReturnTarget(
                      `/opportunities/${commercialOffer.opportunity_public_id}`,
                      commercialOfferReturnTo,
                      "Back to Commercial Offer",
                    )}
                    style={{ color: "#1d4ed8", fontWeight: 700, textDecoration: "underline" }}
                  >
                    Open Opportunity context
                  </a>
                </div>
              )}
            </SectionCard>
          </div>
              </SectionGroup>

              <SectionGroup id="co-overview-dates" title="Dates, value and notes" tone="amber">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
            <SectionCard title="Commercial summary">
              <dl style={COMPACT_DETAIL_GRID_STYLE}>
                <DetailRow label="Offer date">{formatDateOnly(commercialOffer.offer_date)}</DetailRow>
                <DetailRow label="Valid until">{formatDateOnly(commercialOffer.valid_until)}</DetailRow>
                <DetailRow label="Submitted at">{formatDateTime(commercialOffer.submitted_at)}</DetailRow>
                <DetailRow label="Submission reference">{displayValue(commercialOffer.submission_reference)}</DetailRow>
                <DetailRow label="Outcome date">{formatDateOnly(commercialOffer.outcome_date)}</DetailRow>
                <DetailRow label="Currency">{commercialOffer.currency_code}</DetailRow>
                <DetailRow label="Value">{formatMoney(commercialOffer.offer_value, commercialOffer.currency_code)}</DetailRow>
                <DetailRow label="Validity note">{validityMessage(commercialOffer)}</DetailRow>
              </dl>
            </SectionCard>

            <SectionCard title="Submission and outcome notes">
              <dl style={COMPACT_DETAIL_GRID_STYLE}>
                <DetailRow label="Submission proof note">
                  <span style={{ whiteSpace: "pre-wrap" }}>{displayValue(commercialOffer.submission_proof_note)}</span>
                </DetailRow>
                <DetailRow label="Outcome remarks">
                  <span style={{ whiteSpace: "pre-wrap" }}>{displayValue(commercialOffer.outcome_remarks)}</span>
                </DetailRow>
                <DetailRow label="General remarks">
                  <span style={{ whiteSpace: "pre-wrap" }}>{displayValue(commercialOffer.remarks)}</span>
                </DetailRow>
              </dl>
            </SectionCard>
              </div>
              </SectionGroup>

              <SectionGroup
                id="co-overview-documents"
                title="Documents"
                tone="violet"
                description="Files for this offer, such as the customer's enquiry or work order. Quotations generated on the Submission tab are listed here too."
              >
                <SectionCard title="Files">
                  <DocumentsPanel
                    linkedRecordType="commercial_offer"
                    linkedRecordPublicId={commercialOffer.public_id}
                    canUpload={hasAnyRole(pageAccess.roleCodes, COMMERCIAL_OFFER_DOCUMENT_UPLOAD_ROLES)}
                  />
                </SectionCard>
              </SectionGroup>
            </>
          ) : null}

          {activeTab === "terms" ? (
            <SectionCard title="Offer terms and conditions" tone="violet">
            <p style={{ marginTop: 0 }}>
              Clauses from the T&C library attached to this offer. Each clause's wording is copied onto the offer when it is
              attached, so later library changes do not alter it. These are sample reference clauses, not final legal-approved wording.
            </p>
            <p style={{ color: "#6b7280" }}>
              Not built yet: choosing clauses for individual lines, editing clause wording, and approval of changed or omitted clauses.
              The mandatory and approval flags are shown for information only.
            </p>

            {tcClauseReadinessLoading ? <p>Loading recommended T&amp;C readiness...</p> : null}
            {tcClausesLoading ? <p>Loading attached T&amp;C clauses...</p> : null}

            <div style={{ display: "grid", gap: "12px", padding: "12px", border: "1px solid #d1d5db", background: "#ffffff", marginBottom: "16px", minWidth: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "flex-start", flexWrap: "wrap" }}>
                <div style={{ minWidth: 0 }}>
                  <h4 style={{ margin: 0 }}>Recommended header T&amp;C readiness</h4>
                  <p style={{ margin: "6px 0 0", color: "#6b7280" }}>
                    Choose the business line here, because the Commercial Offer does not store one yet.
                  </p>
                </div>
                <label style={{ display: "grid", gap: "4px", minWidth: "220px" }}>
                  Recommendation basis
                  <select
                    value={tcRecommendationBasis}
                    onChange={(event) => {
                      const nextBasis = event.target.value;
                      setTcRecommendationBasis(nextBasis);
                      setTcRecommendedMessage("");
                      setTcRecommendedError("");
                      if (commercialOffer) {
                        const token = getToken();
                        if (token) {
                          void loadTcClauseReadiness(commercialOffer.public_id, token, nextBasis);
                          void loadSubmissionReadiness(commercialOffer.public_id, token, nextBasis);
                        }
                      }
                    }}
                    style={{ padding: "8px" }}
                  >
                    {TC_RECOMMENDATION_BASIS_OPTIONS.map((option) => (
                      <option key={option.value || "none"} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {tcClauseReadiness ? (
                <>
                  <p style={{ margin: 0, color: tcClauseReadiness.missing_recommended_count > 0 ? "#92400e" : "#065f46" }}>
                    {tcClauseReadiness.status_text}
                  </p>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "8px" }}>
                    <div style={{ padding: "8px", border: "1px solid #e5e7eb", background: "#f9fafb" }}>
                      <strong>{tcClauseReadiness.total_recommended_count}</strong>
                      <div style={{ color: "#6b7280" }}>Recommended</div>
                    </div>
                    <div style={{ padding: "8px", border: "1px solid #e5e7eb", background: "#f9fafb" }}>
                      <strong>{tcClauseReadiness.attached_recommended_count}</strong>
                      <div style={{ color: "#6b7280" }}>Attached recommended</div>
                    </div>
                    <div style={{ padding: "8px", border: "1px solid #e5e7eb", background: "#f9fafb" }}>
                      <strong>{tcClauseReadiness.missing_recommended_count}</strong>
                      <div style={{ color: "#6b7280" }}>Not attached</div>
                    </div>
                    <div style={{ padding: "8px", border: "1px solid #e5e7eb", background: "#f9fafb" }}>
                      <strong>{tcClauseReadiness.attached_optional_count}</strong>
                      <div style={{ color: "#6b7280" }}>Attached optional</div>
                    </div>
                  </div>

                  {tcClauseReadiness.recommended_clauses.length > 0 ? (
                    <div style={{ display: "grid", gap: "8px" }}>
                      {tcClauseReadiness.recommended_clauses.map((clause) => (
                        <article key={clause.tc_clause_public_id} style={{ padding: "10px", border: "1px solid #e5e7eb", background: "#ffffff", minWidth: 0 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", gap: "10px", flexWrap: "wrap" }}>
                            <div style={{ minWidth: 0 }}>
                              <strong style={{ overflowWrap: "anywhere" }}>{clause.clause_id}: {clause.title}</strong>
                              <div style={{ color: "#6b7280", overflowWrap: "anywhere" }}>
                                {formatStatusLabel(clause.business_line)} / {formatStatusLabel(clause.clause_category)}
                              </div>
                            </div>
                            <span style={{ fontWeight: 700, color: clause.status === "ATTACHED" ? "#065f46" : "#92400e" }}>
                              {clause.status === "ATTACHED" ? "ATTACHED" : "NOT ATTACHED"}
                            </span>
                          </div>
                          <p style={{ margin: "8px 0 0", color: "#374151", whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                            {clause.clause_text}
                          </p>
                          <p style={{ margin: "8px 0 0", color: "#6b7280" }}>
                            {clause.mandatory_default ? "Mandatory default" : "Optional default"} / Omit approval:{" "}
                            {clause.requires_approval_if_omitted ? "Yes" : "No"} / Modify approval:{" "}
                            {clause.requires_approval_if_modified ? "Yes" : "No"}
                          </p>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p style={{ margin: 0 }}>No recommended clauses are listed until a basis with active header-level clauses is selected.</p>
                  )}

                  <ul style={{ margin: 0, paddingLeft: "18px", color: "#6b7280" }}>
                    {tcClauseReadiness.deferral_notes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p style={{ margin: 0 }}>Recommended T&amp;C readiness has not loaded yet.</p>
              )}

              {pageAccess.canWorkTcClauses && !offerContentIsLocked ? (
                <div>
                  <button
                    type="button"
                    onClick={() => void handleAttachRecommendedTcClauses()}
                    disabled={tcAttachRecommendedSaving || !tcRecommendationBasis}
                    style={BUTTON_STYLE}
                  >
                    {tcAttachRecommendedSaving ? "Attaching recommended..." : "Attach recommended clauses"}
                  </button>
                </div>
              ) : null}
              {tcRecommendedMessage ? <p style={{ margin: 0, color: "#065f46" }}>{tcRecommendedMessage}</p> : null}
              {tcRecommendedError ? <p style={{ margin: 0, color: "crimson" }}>{tcRecommendedError}</p> : null}
            </div>

            {tcClauses.length > 0 ? (
              <div style={{ display: "grid", gap: "12px" }}>
                {tcClauses.map((attachment) => {
                  const expanded = expandedTcClauseId === attachment.public_id;
                  return (
                    <article key={attachment.public_id} style={{ padding: "12px", border: "1px solid #ddd", background: "#ffffff", minWidth: 0 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap" }}>
                        <div style={{ minWidth: 0 }}>
                          <strong>{attachment.clause_id_snapshot}: {attachment.title_snapshot}</strong>
                          <div style={{ color: "#6b7280", overflowWrap: "anywhere" }}>
                            {formatStatusLabel(attachment.business_line_snapshot)} / {formatStatusLabel(attachment.clause_category_snapshot)}
                          </div>
                        </div>
                        <span style={{ fontWeight: 700, color: attachment.mandatory_default_snapshot ? "#92400e" : "#065f46" }}>
                          {attachment.mandatory_default_snapshot ? "Mandatory default" : "Optional default"}
                        </span>
                      </div>

                      <dl style={{ ...COMPACT_DETAIL_GRID_STYLE, marginTop: "10px" }}>
                        <DetailRow label="Source clause">{displayValue(attachment.source_clause_number_snapshot)}</DetailRow>
                        <DetailRow label="Risk category">{displayValue(formatStatusLabel(attachment.risk_category_snapshot))}</DetailRow>
                        <DetailRow label="Approval flags">
                          Omit: {attachment.requires_approval_if_omitted_snapshot ? "Yes" : "No"} / Modify:{" "}
                          {attachment.requires_approval_if_modified_snapshot ? "Yes" : "No"}
                        </DetailRow>
                        <DetailRow label="Attached">{formatDateTime(attachment.created_at)}</DetailRow>
                      </dl>

                      {expanded ? (
                        <div style={{ marginTop: "12px", padding: "12px", border: "1px solid #e5e7eb", background: "#f9fafb", minWidth: 0 }}>
                          <p style={{ marginTop: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{attachment.clause_text_snapshot}</p>
                          <dl style={COMPACT_DETAIL_GRID_STYLE}>
                            <DetailRow label="Attachment public id">{attachment.public_id}</DetailRow>
                            <DetailRow label="Library clause public id">{attachment.tc_clause_public_id}</DetailRow>
                            <DetailRow label="Source reference">
                              <span style={{ overflowWrap: "anywhere" }}>{displayValue(attachment.source_reference_snapshot)}</span>
                            </DetailRow>
                          </dl>
                        </div>
                      ) : null}

                      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "10px" }}>
                        <button
                          type="button"
                          onClick={() => setExpandedTcClauseId(expanded ? null : attachment.public_id)}
                          style={MUTED_BUTTON_STYLE}
                        >
                          {expanded ? "Hide clause detail" : "View clause detail"}
                        </button>
                        {pageAccess.canWorkTcClauses && !offerContentIsLocked ? (
                          <button
                            type="button"
                            onClick={() => void handleRemoveTcClause(attachment)}
                            disabled={tcClauseSaving}
                            style={MUTED_BUTTON_STYLE}
                          >
                            Remove
                          </button>
                        ) : null}
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <p>No header T&amp;C clauses are attached to this Commercial Offer yet.</p>
            )}

            {tcClauseMessage ? <p style={{ color: "#065f46" }}>{tcClauseMessage}</p> : null}
            {tcClauseError ? <p style={{ color: "crimson" }}>{tcClauseError}</p> : null}

            {pageAccess.canWorkTcClauses && !offerContentIsLocked ? (
              <form onSubmit={handleAttachTcClause} style={{ display: "grid", gap: "12px", marginTop: "16px", padding: "12px", border: "1px solid #bfdbfe", background: "#ffffff" }}>
                <h4 style={{ margin: 0 }}>Attach header T&amp;C clause</h4>
                <label style={{ display: "grid", gap: "4px" }}>
                  T&amp;C library clause
                  <select
                    value={selectedTcClauseId}
                    onChange={(event) => {
                      setSelectedTcClauseId(event.target.value);
                      setTcClauseMessage("");
                      setTcClauseError("");
                    }}
                    style={{ padding: "8px" }}
                  >
                    {tcClauseLibraryOptions.length === 0 ? <option value="">No active header clauses available</option> : null}
                    {tcClauseLibraryOptions.map((clause) => (
                      <option key={clause.public_id} value={clause.public_id}>
                        {clause.clause_id} - {clause.title}
                      </option>
                    ))}
                  </select>
                </label>
                <div>
                  <button type="submit" disabled={tcClauseSaving || !selectedTcClauseId}>
                    {tcClauseSaving ? "Attaching..." : "Attach T&C clause"}
                  </button>
                </div>
              </form>
            ) : offerContentIsLocked ? (
              <p className="helper-text">{lockedContentNote}</p>
            ) : (
              <p style={{ color: "#6b7280" }}>T&amp;C clause attachment is restricted to Sales and Admin roles.</p>
            )}
            </SectionCard>
          ) : null}

          {activeTab === "lines-pricing" ? (
            <SectionIndex
              items={[
                { id: "co-lines", label: "Offer lines" },
                // The market rates of the line nearest what is on screen: rates are kept per line (Slice 4G; owner's
                // screen check). The first line's panel carries the id, the link's address.
                { id: "co-line-rates", label: "Market rates", target: nearestLineMarketRatesPanel },
              ]}
            />
          ) : null}

          {activeTab === "lines-pricing" ? (
            <SectionCard id="co-lines" title="Offer lines" tone="teal">
            <p style={{ marginTop: 0 }}>
              Each line is one item being quoted. A line keeps its identity for life, so an accepted line carries through to the
              Work Order unchanged.
            </p>
            <p style={{ color: "#6b7280" }}>
              Line amounts are simply quantity times rate. GST and other taxes, a rate master, billing terms, mobilisation and
              demobilisation terms, customised T&C and margin approval are not built yet.
            </p>

            {offerLineMessage ? <p style={{ color: "#065f46" }}>{offerLineMessage}</p> : null}
            {offerLineError ? <p style={{ color: "crimson" }}>{offerLineError}</p> : null}
            {offerLinesLoading ? <p>Loading Commercial Offer lines...</p> : null}

            {offerLines.length > 0 ? (
              <div style={{ display: "grid", gap: "12px" }}>
                {offerLines.map((line, lineIndex) => (
                  <div key={line.public_id} style={{ padding: "12px", border: "1px solid #ddd", background: "#ffffff" }}>
                    {editingOfferLineId === line.public_id && !offerContentIsLocked ? (
                      <form onSubmit={handleUpdateOfferLine} style={{ display: "grid", gap: "12px" }}>
                        <h4 style={{ margin: 0 }}>Edit line {line.line_number}</h4>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
                          <label style={{ display: "grid", gap: "4px" }}>
                            Line number
                            <input
                              value={offerLineEditForm.line_number}
                              onChange={(event) => setOfferLineEditForm((current) => ({ ...current, line_number: event.target.value }))}
                              type="number"
                              min="1"
                              style={{ padding: "8px" }}
                            />
                          </label>
                          <label style={{ display: "grid", gap: "4px" }}>
                            Line status
                            <select
                              value={offerLineEditForm.line_status_code}
                              onChange={(event) => setOfferLineEditForm((current) => ({ ...current, line_status_code: event.target.value }))}
                              style={{ padding: "8px" }}
                            >
                              <option value="ACTIVE">Active</option>
                              <option value="CANCELLED">Cancelled</option>
                            </select>
                          </label>
                          <label style={{ display: "grid", gap: "4px" }}>
                            Quantity
                            <input
                              value={offerLineEditForm.quantity}
                              onChange={(event) => setOfferLineEditForm((current) => ({ ...current, quantity: event.target.value }))}
                              type="number"
                              min="0.01"
                              step="0.01"
                              style={{ padding: "8px" }}
                            />
                          </label>
                          <label style={{ display: "grid", gap: "4px" }}>
                            UOM
                            <input
                              value={offerLineEditForm.uom}
                              onChange={(event) => setOfferLineEditForm((current) => ({ ...current, uom: event.target.value }))}
                              maxLength={50}
                              style={{ padding: "8px" }}
                            />
                          </label>
                          <label style={{ display: "grid", gap: "4px" }}>
                            Rate amount
                            <input
                              value={offerLineEditForm.rate_amount}
                              onChange={(event) => setOfferLineEditForm((current) => ({ ...current, rate_amount: event.target.value }))}
                              type="number"
                              min="0"
                              step="0.01"
                              style={{ padding: "8px" }}
                            />
                          </label>
                          <label style={{ display: "grid", gap: "4px" }}>
                            Currency
                            <CurrencySelect
                              value={offerLineEditForm.currency_code}
                              onChange={(currencyCode) => setOfferLineEditForm((current) => ({ ...current, currency_code: currencyCode }))}
                              style={{ padding: "8px" }}
                            />
                          </label>
                        </div>
                        <label style={{ display: "grid", gap: "4px" }}>
                          Scope / service description
                          <textarea
                            value={offerLineEditForm.scope_description}
                            onChange={(event) => setOfferLineEditForm((current) => ({ ...current, scope_description: event.target.value }))}
                            rows={3}
                            maxLength={1000}
                            style={{ padding: "8px" }}
                          />
                        </label>
                        <label style={{ display: "grid", gap: "4px" }}>
                          Equipment / service category
                          <input
                            value={offerLineEditForm.equipment_service_category}
                            onChange={(event) => setOfferLineEditForm((current) => ({ ...current, equipment_service_category: event.target.value }))}
                            maxLength={255}
                            style={{ padding: "8px" }}
                          />
                        </label>
                        <label style={{ display: "grid", gap: "4px" }}>
                          Remarks
                          <textarea
                            value={offerLineEditForm.remarks}
                            onChange={(event) => setOfferLineEditForm((current) => ({ ...current, remarks: event.target.value }))}
                            rows={3}
                            maxLength={2000}
                            style={{ padding: "8px" }}
                          />
                        </label>
                        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                          <button type="submit" disabled={offerLineSaving}>{offerLineSaving ? "Saving..." : "Save line"}</button>
                          <button type="button" onClick={cancelEditingOfferLine} disabled={offerLineSaving}>Cancel</button>
                        </div>
                        {offerLineEditError ? <p className="action-feedback text-danger">{offerLineEditError}</p> : null}
                      </form>
                    ) : (
                      <>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                          <strong>Line {line.line_number}: {line.scope_description}</strong>
                          <span style={{ color: line.line_status_code === "ACTIVE" ? "#065f46" : "#92400e", fontWeight: 700 }}>{formatStatusLabel(line.line_status_code)}</span>
                        </div>
                        <dl style={{ ...DETAIL_GRID_STYLE, marginTop: "10px" }}>
                          <DetailRow label="Line public id">{line.public_id}</DetailRow>
                          <DetailRow label="Scope / service description">{displayValue(line.scope_description)}</DetailRow>
                          <DetailRow label="Equipment / service category">{displayValue(line.equipment_service_category)}</DetailRow>
                          <DetailRow label="Quantity / UOM">{line.quantity} {line.uom}</DetailRow>
                          <DetailRow label="Rate">{formatMoney(line.rate_amount, line.currency_code)}</DetailRow>
                          <DetailRow label="Line amount">{formatMoney(line.line_amount, line.currency_code)}</DetailRow>
                          <DetailRow label="Remarks">{displayValue(line.remarks)}</DetailRow>
                        </dl>
                        {pageAccess.canWorkOfferLines && !offerContentIsLocked ? (
                          <button type="button" onClick={() => startEditingOfferLine(line)} style={{ ...BUTTON_STYLE, marginTop: "10px" }}>
                            Edit line
                          </button>
                        ) : null}
                        <LineMarketRates
                          // A changed scope starts the add-rate form afresh from it (review 4G-R1-010).
                          key={`${line.public_id}-${line.scope_description}`}
                          anchorId={lineIndex === 0 ? "co-line-rates" : undefined}
                          offerPublicId={commercialOffer.public_id}
                          offerVersionNumber={commercialOffer.version_number}
                          line={line}
                          lineRates={ratesForLine(pricingEvidence, line.public_id)}
                          offerRates={pricingEvidence}
                          canWork={pageAccess.canWorkPricingEvidence}
                          locked={offerContentIsLocked}
                          getToken={getToken}
                          onChanged={async () => {
                            await loadPricingEvidence(commercialOffer.public_id);
                            await loadSubmissionReadiness(commercialOffer.public_id);
                          }}
                          onRefused={() => refreshOfferContent(commercialOffer.public_id)}
                        />
                      </>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p>No Commercial Offer lines have been captured yet.</p>
            )}

            {pageAccess.canWorkOfferLines && !offerContentIsLocked ? (
              <form onSubmit={handleAddOfferLine} style={{ display: "grid", gap: "12px", marginTop: "16px", padding: "12px", border: "1px solid #bfdbfe", background: "#ffffff" }}>
                <h4 style={{ margin: 0 }}>Add Commercial Offer line</h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Line number
                    <input
                      value={offerLineForm.line_number}
                      onChange={(event) => setOfferLineForm((current) => ({ ...current, line_number: event.target.value }))}
                      type="number"
                      min="1"
                      placeholder="Auto"
                      style={{ padding: "8px" }}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Quantity
                    <input
                      value={offerLineForm.quantity}
                      onChange={(event) => setOfferLineForm((current) => ({ ...current, quantity: event.target.value }))}
                      type="number"
                      min="0.01"
                      step="0.01"
                      style={{ padding: "8px" }}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "4px" }}>
                    UOM
                    <input
                      value={offerLineForm.uom}
                      onChange={(event) => setOfferLineForm((current) => ({ ...current, uom: event.target.value }))}
                      maxLength={50}
                      placeholder="day / month / trip / unit"
                      style={{ padding: "8px" }}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Rate amount
                    <input
                      value={offerLineForm.rate_amount}
                      onChange={(event) => setOfferLineForm((current) => ({ ...current, rate_amount: event.target.value }))}
                      type="number"
                      min="0"
                      step="0.01"
                      style={{ padding: "8px" }}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Currency
                    <CurrencySelect
                      value={offerLineForm.currency_code}
                      onChange={(currencyCode) => setOfferLineForm((current) => ({ ...current, currency_code: currencyCode }))}
                      style={{ padding: "8px" }}
                    />
                  </label>
                </div>
                <label style={{ display: "grid", gap: "4px" }}>
                  Scope / service description
                  <textarea
                    value={offerLineForm.scope_description}
                    onChange={(event) => setOfferLineForm((current) => ({ ...current, scope_description: event.target.value }))}
                    rows={3}
                    maxLength={1000}
                    style={{ padding: "8px" }}
                  />
                </label>
                <label style={{ display: "grid", gap: "4px" }}>
                  Equipment / service category
                  <input
                    value={offerLineForm.equipment_service_category}
                    onChange={(event) => setOfferLineForm((current) => ({ ...current, equipment_service_category: event.target.value }))}
                    maxLength={255}
                    style={{ padding: "8px" }}
                  />
                </label>
                <label style={{ display: "grid", gap: "4px" }}>
                  Remarks
                  <textarea
                    value={offerLineForm.remarks}
                    onChange={(event) => setOfferLineForm((current) => ({ ...current, remarks: event.target.value }))}
                    rows={3}
                    maxLength={2000}
                    style={{ padding: "8px" }}
                  />
                </label>
                <div>
                  <button type="submit" disabled={offerLineSaving}>{offerLineSaving ? "Saving..." : "Save Commercial Offer line"}</button>
                </div>
              </form>
            ) : offerContentIsLocked ? (
              <p className="helper-text">{lockedContentNote}</p>
            ) : (
              <p style={{ color: "#6b7280" }}>Only Sales and Admin roles can add or change lines.</p>
            )}
            </SectionCard>
          ) : null}

          {activeTab === "traceability" ? (
            <SectionCard title="Work Orders from this offer" tone="teal">
            <p style={{ marginTop: 0 }}>
              Work Orders created from this offer. Each is awaiting release to Ops; releasing it, activating the customer in
              Finance, execution and billing are not built yet.
            </p>

            {linkedWorkOrderError ? <p style={{ color: "crimson" }}>{linkedWorkOrderError}</p> : null}
            {linkedWorkOrdersLoading ? <p>Loading Work Orders...</p> : null}

            {linkedWorkOrders.length > 0 ? (
              <div style={{ display: "grid", gap: "12px" }}>
                {linkedWorkOrders.map((workOrder) => (
                  <article key={workOrder.public_id} style={{ padding: "12px", border: "1px solid #ddd", background: "#ffffff" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                      <strong>{workOrder.work_order_code}</strong>
                      <span style={{ fontWeight: 700 }}>{formatWorkOrderStatusLabel(workOrder.work_order_status_code)}</span>
                    </div>
                    <dl style={{ ...DETAIL_GRID_STYLE, marginTop: "10px" }}>
                      <DetailRow label="Work Order public id">{workOrder.public_id}</DetailRow>
                      <DetailRow label="Title">{displayValue(workOrder.work_order_title)}</DetailRow>
                      <DetailRow label="Customer WO reference">{displayValue(workOrder.customer_wo_reference)}</DetailRow>
                      <DetailRow label="Received date">{formatDateOnly(workOrder.received_date)}</DetailRow>
                      <DetailRow label="Source offer status">{formatStatusLabel(workOrder.source_offer_status_code)}</DetailRow>
                      <DetailRow label="Created">{formatDateTime(workOrder.created_at)}</DetailRow>
                    </dl>
                    <a
                      href={hrefWithReturnTarget(
                        `/work-orders/${workOrder.public_id}`,
                        commercialOfferReturnTo,
                        "Back to Commercial Offer",
                      )}
                      style={{ ...BUTTON_STYLE, marginTop: "10px" }}
                    >
                      Open Work Order
                    </a>
                  </article>
                ))}
              </div>
            ) : (
              <p>No Work Order has been created yet from this Commercial Offer.</p>
            )}

            {pageAccess.canCreateWorkOrder &&
            commercialOffer.offer_status_code === "ACCEPTED" &&
            !workOrderHandoffAvailable &&
            existingLinkedWorkOrderCount === 0 ? (
              <div style={{ marginTop: "12px", padding: "12px", border: "1px solid #f59e0b", background: "#fffbeb", color: "#92400e" }}>
                <p style={{ margin: 0 }}>
                  <strong>A Work Order cannot be created:</strong>{" "}
                  {lifecycleGuidance && lifecycleGuidance.work_order_handoff_blocked_reasons.length > 0
                    ? lifecycleGuidance.work_order_handoff_blocked_reasons.join(" ")
                    : accountTraceabilityBlockMessage()}{" "}
                  <a
                    href={hrefWithReturnTarget(
                      `/opportunities/${commercialOffer.opportunity_public_id}`,
                      commercialOfferReturnTo,
                      "Back to Commercial Offer",
                    )}
                    style={{ color: "#1d4ed8", fontWeight: 700 }}
                  >
                    Open Opportunity context
                  </a>
                </p>
              </div>
            ) : null}

            {pageAccess.canCreateWorkOrder && commercialOffer.offer_status_code === "ACCEPTED" && canOfferCreateWorkOrderAction ? (
              <p style={{ marginTop: "12px" }}>
                <a href={`/work-orders/new?commercialOfferId=${encodeURIComponent(commercialOffer.public_id)}`} style={BUTTON_STYLE}>
                  {createWorkOrderActionLabel}
                </a>
              </p>
            ) : null}
            </SectionCard>
          ) : null}

          {activeTab === "traceability" ? (
            <SectionCard title="Related Commercial Offers" tone="teal">
              <p style={{ marginTop: 0 }}>
                Supplementary Offers and Change Quotations are separate Commercial Offer series linked to their Base
                Offer, not revisions of it. Each has its own independent lines, pricing, terms and lifecycle. Accepting
                a related offer does not create a Work Order or change an existing one automatically; a change to a
                Work Order is recorded separately as a Work Order Amendment.
              </p>

              <dl style={DETAIL_GRID_STYLE}>
                <DetailRow label="Purpose">{offerPurposeLabel(commercialOffer.offer_purpose)}</DetailRow>
                {commercialOffer.offer_purpose !== "BASE" ? (
                  <>
                    <DetailRow label="Base Offer">
                      {commercialOffer.base_offer_public_id ? (
                        <a
                          href={hrefWithReturnTarget(
                            `/commercial-offers/${commercialOffer.base_offer_public_id}`,
                            commercialOfferReturnTo,
                            "Back to related Commercial Offer",
                          )}
                          style={{ color: "#1d4ed8", fontWeight: 700 }}
                        >
                          {displayValue(commercialOffer.base_offer_code)}
                        </a>
                      ) : (
                        "-"
                      )}
                    </DetailRow>
                    <DetailRow label="Linked Work Order">
                      {commercialOffer.related_work_order_public_id ? (
                        <a
                          href={hrefWithReturnTarget(
                            `/work-orders/${commercialOffer.related_work_order_public_id}`,
                            commercialOfferReturnTo,
                            "Back to related Commercial Offer",
                          )}
                          style={{ color: "#1d4ed8", fontWeight: 700 }}
                        >
                          {displayValue(commercialOffer.related_work_order_code)}
                        </a>
                      ) : (
                        "None"
                      )}
                    </DetailRow>
                    <DetailRow label="Customer request reference">{displayValue(commercialOffer.customer_request_reference)}</DetailRow>
                    <DetailRow label="Customer request received">{formatDateOnly(commercialOffer.customer_request_received_date)}</DetailRow>
                    <DetailRow label="Request / change summary">{displayValue(commercialOffer.customer_request_summary)}</DetailRow>
                  </>
                ) : null}
              </dl>

              {commercialOffer.offer_purpose !== "BASE" ? (
                <div style={{ marginTop: "16px", padding: "12px", border: "1px solid #ddd", background: "#ffffff" }}>
                  <h4 style={{ marginTop: 0 }}>Work Order Amendment</h4>
                  <p style={{ color: "#6b7280" }}>
                    A Work Order Amendment records the customer&apos;s requested change as an intake/review record
                    against the linked Work Order. Creating or accepting this Commercial Offer does not by itself
                    create or apply any amendment.
                  </p>
                  {linkedAmendmentsError ? <p style={{ color: "crimson" }}>{linkedAmendmentsError}</p> : null}
                  {linkedAmendmentsLoading ? <p>Loading linked Work Order Amendments...</p> : null}
                  {linkedAmendments.length > 0 ? (
                    <div style={{ display: "grid", gap: "10px" }}>
                      {linkedAmendments.map((amendment) => (
                        <article key={amendment.public_id} style={{ padding: "10px", border: "1px solid #ddd", background: "#f9fafb" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                            <strong>Amendment #{amendment.amendment_sequence_no} - {amendmentTypeLabel(amendment.amendment_type_code)}</strong>
                            <span className="status-badge">{formatStatusLabel(amendment.amendment_status_code)}</span>
                          </div>
                          <p style={{ margin: "6px 0 0 0", color: "#374151" }}>{amendment.amendment_reason}</p>
                          <a
                            href={hrefWithReturnTarget(
                              `/work-orders/${amendment.work_order_public_id}/amendments/${amendment.public_id}`,
                              commercialOfferReturnTo,
                              "Back to Commercial Offer",
                            )}
                            style={{ ...BUTTON_STYLE, marginTop: "8px" }}
                          >
                            Open
                          </a>
                        </article>
                      ))}
                    </div>
                  ) : (
                    !linkedAmendmentsLoading && <p>No Work Order Amendment is linked to this Commercial Offer yet.</p>
                  )}
                  {commercialOffer.offer_status_code === "ACCEPTED" &&
                  commercialOffer.related_work_order_public_id &&
                  pageAccess.canCreateWorkOrder ? (
                    <p style={{ marginTop: "12px" }}>
                      <a
                        href={hrefWithReturnTarget(
                          `/work-orders/${commercialOffer.related_work_order_public_id}/amendments/new?relatedOfferId=${encodeURIComponent(commercialOffer.public_id)}`,
                          commercialOfferReturnTo,
                          "Back to Commercial Offer",
                        )}
                        style={BUTTON_STYLE}
                      >
                        Record Work Order Amendment
                      </a>
                    </p>
                  ) : null}
                </div>
              ) : null}

              {relatedOffersError ? <p style={{ color: "crimson" }}>{relatedOffersError}</p> : null}
              {relatedOffersLoading ? <p>Loading related Commercial Offers...</p> : null}

              {relatedOffers.length > 0 ? (
                <div style={{ display: "grid", gap: "12px", marginTop: "12px" }}>
                  {relatedOffers.map((related) => (
                    <article key={related.public_id} style={{ padding: "12px", border: "1px solid #ddd", background: "#ffffff" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                        <strong>{offerVersionLabel(related)} - {offerPurposeLabel(related.offer_purpose)}</strong>
                        <span style={{ fontWeight: 700 }}>{formatStatusLabel(related.offer_status_code)}</span>
                      </div>
                      <dl style={{ ...DETAIL_GRID_STYLE, marginTop: "10px" }}>
                        <DetailRow label="Request / change summary">{displayValue(related.customer_request_summary)}</DetailRow>
                        <DetailRow label="Linked Work Order">{displayValue(related.related_work_order_code)}</DetailRow>
                      </dl>
                      <a
                        href={hrefWithReturnTarget(
                          `/commercial-offers/${related.public_id}`,
                          commercialOfferReturnTo,
                          "Back to Base Commercial Offer",
                        )}
                        style={{ ...BUTTON_STYLE, marginTop: "10px" }}
                      >
                        Open
                      </a>
                    </article>
                  ))}
                </div>
              ) : (
                <p>No Supplementary Offer or Change Quotation has been created from this Commercial Offer yet.</p>
              )}

              {commercialOffer.offer_purpose === "BASE" &&
              commercialOffer.offer_status_code === "ACCEPTED" &&
              pageAccess.canWorkCommercialOffer ? (
                <p style={{ marginTop: "12px", display: "flex", gap: "12px", flexWrap: "wrap" }}>
                  <a
                    href={`/commercial-offers/${encodeURIComponent(commercialOffer.public_id)}/related-offers/new?purpose=SUPPLEMENTARY`}
                    style={BUTTON_STYLE}
                  >
                    Create Supplementary Offer
                  </a>
                  {linkedWorkOrders.length > 0 ? (
                    <a
                      href={`/commercial-offers/${encodeURIComponent(commercialOffer.public_id)}/related-offers/new?purpose=CHANGE_QUOTATION`}
                      style={BUTTON_STYLE}
                    >
                      Create Change Quotation
                    </a>
                  ) : (
                    <span style={{ color: "#6b7280", alignSelf: "center" }}>
                      Create Change Quotation requires an existing linked Work Order.
                    </span>
                  )}
                </p>
              ) : null}
            </SectionCard>
          ) : null}

          {activeTab === "lines-pricing" ? (
            <SectionCard id="co-whole-offer-rates" title="Market rates" tone="amber">
            <p className="helper-text">
              Each line keeps its own market rates and its own basis rate, under the line above. The chosen rate need not be
              the lowest; the reason for choosing it is recorded, and an earlier choice stays in the line&apos;s basis history.
            </p>
            {pricingEvidenceError ? <p className="text-danger">{pricingEvidenceError}</p> : null}
            {pricingEvidenceLoading ? <p>Loading market rates...</p> : null}
            {wholeOfferRates(pricingEvidence).length > 0 ? (
              <>
                <h4>Rates recorded for the whole offer, before rates were kept per line</h4>
                <p className="helper-text">These belong to no line and can no longer be chosen; they are kept as they were.</p>
                <ul className="compact-list">
                  {wholeOfferRates(pricingEvidence).map((item) => (
                    <li key={item.public_id} className="divided-item">
                      <strong>{rateSummary(item)}</strong>
                      {item.is_selected_basis ? " - was chosen as the basis for the whole offer" : ""}
                      <div className="helper-text">
                        {item.equipment_service_description}
                        {item.selection_reason ? ` - Reason: ${item.selection_reason}` : ""}
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
            </SectionCard>
          ) : null}

          {activeTab === "overview" ? (
            <SectionGroup id="co-overview-status" title="Status path and what is not built yet" tone="slate">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
            <SectionCard title="Status path">
              <dl style={COMPACT_DETAIL_GRID_STYLE}>
                <DetailRow label="Current status">{formatStatusLabel(commercialOffer.offer_status_code)}</DetailRow>
              </dl>
              {statusIsDeferredForEditing ? (
                <p style={{ color: "#92400e" }}>
                  For this status, approval of the offer itself, automatic credit/exposure checks, document locking and Work Order controls are not built yet.
                </p>
              ) : null}
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "12px" }}>
                {COMMERCIAL_OFFER_STATUS_FLOW.map((status) => {
                  const isCurrent = status === commercialOffer.offer_status_code;
                  const selectableNow = statusUpdateOptions(commercialOffer.offer_status_code, isPreparationVersion).includes(status);
                  // Slice 6M.1 completion: ACCEPTED/REJECTED are never selectable through general
                  // edit at all (not merely deferred), so they get their own explanatory suffix
                  // pointing at the dedicated Customer Response action instead of "- deferred".
                  const isCustomerResponseOnly = COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES.includes(
                    status as typeof COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES[number],
                  );
                  const suffix = isCurrent
                    ? " - current"
                    : isCustomerResponseOnly
                      ? " - via Customer Response"
                      : selectableNow
                        ? ""
                        : " - not set here";
                  return (
                    <span
                      key={status}
                      style={{
                        padding: "8px 10px",
                        border: isCurrent ? "2px solid #1d4ed8" : "1px solid #ddd",
                        borderRadius: "999px",
                        fontWeight: isCurrent ? 700 : 400,
                        background: isCurrent ? "#eff6ff" : "white",
                        color: selectableNow ? "inherit" : "#6b7280",
                      }}
                    >
                      {formatStatusLabel(status)}{suffix}
                    </span>
                  );
                })}
              </div>
            </SectionCard>

            <SectionCard title="Not in this version yet">
              <ul>
                <li>Full quote calculation engine, rate master, automated Plum historical-rate import and advanced pricing analysis</li>
                <li>Line-level T&C selection, clause customization and approval/deviation workflow</li>
                <li>Approval for omitted mandatory clauses; server-side PDF generation (quotations are produced as a web page and printed to PDF from the browser)</li>
                <li>Advanced version comparison and approval workflow</li>
                <li>Formal tender/customer-format submission proof workflow</li>
                <li>Approval of the offer itself (a quotation version can already be approved for issue), and an automatic check of the offer against the customer's approved credit limit and credit days</li>
                <li>Releasing the Work Order to Ops, Customer Master approval, execution, log sheets and billing</li>
              </ul>
            </SectionCard>
            </div>
            </SectionGroup>
          ) : null}

          {activeTab === "traceability" ? (
            <SectionCard title="Record details" tone="slate">
            <p style={{ color: "#6b7280" }}>
              Times are shown in India time.
            </p>
            <dl style={DETAIL_GRID_STYLE}>
              <DetailRow label="Reference">
                <ReferenceText>{commercialOffer.public_id}</ReferenceText>
              </DetailRow>
              <DetailRow label="Created by">{displayValue(commercialOffer.created_by_display_name ?? commercialOffer.created_by)}</DetailRow>
              <DetailRow label="Created">{formatDateTime(commercialOffer.created_at)}</DetailRow>
              <DetailRow label="Updated">{formatDateTime(commercialOffer.updated_at)}</DetailRow>
            </dl>
            <div style={{ marginTop: "16px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <a
                href={hrefWithReturnTarget(
                  `/opportunities/${commercialOffer.opportunity_public_id}`,
                  commercialOfferReturnTo,
                  "Back to Commercial Offer",
                )}
                style={BUTTON_STYLE}
              >
                Open Opportunity
              </a>
              {commercialOffer.account_public_id ? (
                <a
                  href={hrefWithReturnTarget(
                    `/accounts/${commercialOffer.account_public_id}`,
                    commercialOfferReturnTo,
                    "Back to Commercial Offer",
                  )}
                  style={BUTTON_STYLE}
                >
                  Open Account
                </a>
              ) : null}
              {pageAccess.canViewEvents ? (
                <a href={eventHref} style={BUTTON_STYLE}>
                  View recent business events
                </a>
              ) : null}
            </div>
            {!pageAccess.canViewEvents ? (
              <p style={{ color: "#6b7280" }}>Only Admin and Management roles can view the audit events.</p>
            ) : null}
            </SectionCard>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
