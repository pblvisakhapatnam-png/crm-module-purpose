import { FormEvent, ReactNode, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import InteractionLog from "../../components/InteractionLog";
import { PageHeader, ReferenceText, SectionCard, SectionGroup, SectionIndex, StatusBadge } from "../../components/PageLayout";
import DateInput from "../../components/DateInput";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { enteredIndiaTimeToUtc } from "../../components/enteredDateTime";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";
import { CONVERTED_LEAD_NOTE, leadCanBeChanged } from "./leadStatus";

const LEAD_DETAIL_BASE_PATH = "/api/leads";
const LEAD_UPDATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];
const SESSION_CHANGED_EVENT = "pbl-session-changed";

const LEAD_SOURCE_OPTIONS = [
  { value: "manual", label: "Manual" },
  { value: "email", label: "Email" },
  { value: "phone", label: "Phone" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "rfq", label: "RFQ" },
  { value: "tender", label: "Tender" },
  { value: "external_intelligence", label: "Reviewed external intelligence" },
  { value: "referral", label: "Referral" },
  { value: "website", label: "Website" },
  { value: "other", label: "Other" },
];

const LEAD_DETAILS_STATUS_OPTIONS = [
  { value: "NEW", label: "New" },
  { value: "CONTACTED", label: "Contacted" },
  { value: "REVIEW_PENDING", label: "Review Pending" },
  { value: "UNDER_REVIEW", label: "Under Review" },
  { value: "UNQUALIFIED", label: "Unqualified" },
];

const LEAD_QUALIFICATION_STATUS_OPTIONS = [
  { value: "QUALIFICATION_READY", label: "Ready for Qualification" },
  { value: "QUALIFIED", label: "Qualified" },
  { value: "UNQUALIFIED", label: "Unqualified" },
  { value: "CLOSED", label: "Closed" },
];

const LEAD_ACTIVITY_TYPE_OPTIONS = [
  { value: "CALL", label: "Call" },
  { value: "EMAIL", label: "Email" },
  { value: "WHATSAPP", label: "WhatsApp" },
  { value: "MEETING", label: "Meeting" },
  { value: "NOTE", label: "Note" },
  { value: "OTHER", label: "Other" },
];

type Lead = {
  public_id: string;
  lead_source: string;
  source_reference?: string | null;
  company_name: string;
  contact_name?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  requirement_summary?: string | null;
  lead_status_code: string;
  assigned_to_user_public_id?: string | null;
  assigned_to_display_name?: string | null;
  qualification_decision_notes?: string | null;
  qualification_reason?: string | null;
  qualification_decided_by?: string | null;
  qualification_decided_at?: string | null;
  converted_account_public_id?: string | null;
  converted_opportunity_public_id?: string | null;
  created_by?: string | null;
  created_by_display_name?: string | null;
  created_at: string;
  updated_at: string;
};

type LeadActivity = {
  public_id: string;
  lead_public_id: string;
  activity_type: string;
  activity_at: string;
  notes?: string | null;
  outcome?: string | null;
  next_follow_up_at?: string | null;
  created_by?: string | null;
  created_at: string;
};

type LeadUpdateResponse = {
  lead: Lead;
  events: Array<{
    public_id: string;
    event_name: string;
    record_type: string;
    record_public_id: string;
  }>;
};

type LeadActivityCreatedResponse = {
  activity: LeadActivity;
  event: {
    public_id: string;
    event_name: string;
    record_type: string;
    record_public_id: string;
  };
};

type LeadQualificationDecisionResponse = {
  lead: Lead;
  event: {
    public_id: string;
    event_name: string;
    record_type: string;
    record_public_id: string;
  };
};

type AccountSummary = {
  public_id: string;
  account_name: string;
  account_status_code: string;
};

type OpportunitySummary = {
  public_id: string;
  opportunity_name: string;
  opportunity_source: string;
  opportunity_status_code: string;
  account_public_id?: string | null;
  source_lead_public_id?: string | null;
};

type LeadConversionResponse = {
  lead: Lead;
  account: AccountSummary;
  opportunity: OpportunitySummary;
  events: Array<{
    public_id: string;
    event_name: string;
    record_type: string;
    record_public_id: string;
  }>;
};

type ValidationErrorDetail =
  | string
  | Array<{
      msg?: string;
      loc?: Array<string | number>;
    }>;

type TokenPayload = {
  role_codes?: unknown;
  exp?: unknown;
};

type AccessStatus = "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token";

type Access = {
  status: AccessStatus;
  roleCodes: string[];
};

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

function getLeadUpdateAccess(): Access {
  const token = getToken();
  if (!token) return { status: "no_token", roleCodes: [] };

  const payload = decodeTokenPayload(token);
  if (!payload) return { status: "invalid_token", roleCodes: [] };

  const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp ?? 0);
  if (exp > 0 && exp * 1000 < Date.now()) {
    return { status: "expired", roleCodes: [] };
  }

  const roleCodes = Array.isArray(payload.role_codes)
    ? payload.role_codes.filter((role): role is string => typeof role === "string")
    : [];

  const allowed = roleCodes.some((role) => LEAD_UPDATE_ROLES.includes(role));
  return { status: allowed ? "allowed" : "denied", roleCodes };
}

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "-";
}

function formValue(value: string | null | undefined): string {
  return value ?? "";
}

function normalizeOptional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

// Status wording matches the choices offered in the Lead forms, so a status reads the same
// everywhere on this page.
const LEAD_STATUS_LABELS: Record<string, string> = Object.fromEntries(
  [...LEAD_DETAILS_STATUS_OPTIONS, ...LEAD_QUALIFICATION_STATUS_OPTIONS].map((option) => [option.value, option.label]),
);

function formatStatusLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return (
    LEAD_STATUS_LABELS[value] ??
    value
      .split("_")
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
      .join(" ")
  );
}

function optionLabel(options: Array<{ value: string; label: string }>, value: string | null | undefined): string {
  if (!value) return "-";
  return options.find((option) => option.value === value)?.label ?? value;
}

function leadDetailsStatusOptions(currentStatus: string) {
  if (LEAD_DETAILS_STATUS_OPTIONS.some((option) => option.value === currentStatus)) {
    return LEAD_DETAILS_STATUS_OPTIONS;
  }

  return [
    ...LEAD_DETAILS_STATUS_OPTIONS,
    { value: currentStatus, label: `${formatStatusLabel(currentStatus)} (current decision status)` },
  ];
}

const LINK_STYLE = { color: "#1d4ed8", fontWeight: 700, textDecoration: "underline" } as const;

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

const TWO_COLUMN_STYLE = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: "14px",
} as const;

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt style={{ color: "#6b7280", fontWeight: 700 }}>{label}</dt>
      <dd style={{ margin: 0, minWidth: 0, overflowWrap: "anywhere", wordBreak: "break-word" }}>{children}</dd>
    </>
  );
}

function validationDetailToMessage(detail: ValidationErrorDetail | undefined): string {
  if (!detail) return "The request could not be completed. Check the form and try again.";
  if (typeof detail === "string") return detail;

  const messages = detail
    .map((item) => item.msg)
    .filter((value): value is string => Boolean(value));

  if (messages.length === 0) return "The request could not be completed. Check the form and try again.";
  return messages.join(" ");
}

function leadDetailErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to view this Lead.";
  if (status === 404) return "Lead not found.";
  return `Could not load Lead. HTTP ${status}.`;
}

async function responseErrorMessage(response: Response, fallback: string): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "You do not have permission for this action.";
  if (response.status === 404) return "Lead not found.";

  if (response.status === 422) {
    try {
      const body = (await response.json()) as { detail?: ValidationErrorDetail };
      return validationDetailToMessage(body.detail);
    } catch {
      return fallback;
    }
  }

  return `${fallback} HTTP ${response.status}.`;
}

function updateAccessMessage(access: Access): string {
  if (access.status === "checking") return "Checking your access...";
  if (access.status === "allowed") return "You can update this Lead and record follow-up activities.";
  if (access.status === "no_token") return "Sign in to update Lead details or record Lead activities.";
  if (access.status === "expired") return "Sign in again to update Lead details or record Lead activities.";
  if (access.status === "invalid_token") return "Sign in again because your session could not be read.";
  return "You can view this Lead, but your role cannot change it.";
}

export default function LeadDetailPage() {
  const params = useParams<{ leadId: string }>();
  const leadId = params?.leadId;
  const [lead, setLead] = useState<Lead | null>(null);
  const [activities, setActivities] = useState<LeadActivity[]>([]);
  const [loading, setLoading] = useState(false);
  const [activityLoading, setActivityLoading] = useState(false);
  const [pageMessage, setPageMessage] = useState("");
  const [pageError, setPageError] = useState("");
  const [updateMessage, setUpdateMessage] = useState("");
  const [updateError, setUpdateError] = useState("");
  const [activityMessage, setActivityMessage] = useState("");
  const [activityError, setActivityError] = useState("");
  const [qualificationMessage, setQualificationMessage] = useState("");
  const [qualificationError, setQualificationError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [activitySubmitting, setActivitySubmitting] = useState(false);
  const [qualificationSubmitting, setQualificationSubmitting] = useState(false);
  const [conversionSubmitting, setConversionSubmitting] = useState(false);
  const [conversionMessage, setConversionMessage] = useState("");
  const [conversionError, setConversionError] = useState("");
  const [lastConversion, setLastConversion] = useState<LeadConversionResponse | null>(null);
  const [access, setAccess] = useState<Access>({ status: "checking", roleCodes: [] });

  const [leadSource, setLeadSource] = useState("manual");
  const [sourceReference, setSourceReference] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [requirementSummary, setRequirementSummary] = useState("");
  const [leadStatusCode, setLeadStatusCode] = useState("NEW");
  const [assignedToUserPublicId, setAssignedToUserPublicId] = useState("");

  const [activityType, setActivityType] = useState("CALL");
  const [activityAt, setActivityAt] = useState("");
  const [activityNotes, setActivityNotes] = useState("");
  const [activityOutcome, setActivityOutcome] = useState("");
  const [nextFollowUpAt, setNextFollowUpAt] = useState("");

  const [qualificationStatusCode, setQualificationStatusCode] = useState("QUALIFICATION_READY");
  const [qualificationReason, setQualificationReason] = useState("");
  const [qualificationDecisionNotes, setQualificationDecisionNotes] = useState("");
  const [conversionNotes, setConversionNotes] = useState("");

  function populateForm(nextLead: Lead) {
    setLeadSource(nextLead.lead_source || "manual");
    setSourceReference(formValue(nextLead.source_reference));
    setCompanyName(nextLead.company_name);
    setContactName(formValue(nextLead.contact_name));
    setContactPhone(formValue(nextLead.contact_phone));
    setContactEmail(formValue(nextLead.contact_email));
    setRequirementSummary(formValue(nextLead.requirement_summary));
    setLeadStatusCode(nextLead.lead_status_code || "NEW");
    setAssignedToUserPublicId(formValue(nextLead.assigned_to_user_public_id));
    setQualificationStatusCode(
      LEAD_QUALIFICATION_STATUS_OPTIONS.some((option) => option.value === nextLead.lead_status_code)
        ? nextLead.lead_status_code
        : "QUALIFICATION_READY",
    );
    setQualificationReason(formValue(nextLead.qualification_reason));
    setQualificationDecisionNotes(formValue(nextLead.qualification_decision_notes));
  }

  async function loadActivities(publicId: string) {
    setActivityError("");

    const token = getToken();
    if (!token) {
      setActivities([]);
      setActivityError(SIGN_IN_FIRST);
      return;
    }

    setActivityLoading(true);

    let response: Response;
    try {
      response = await fetch(`${LEAD_DETAIL_BASE_PATH}/${publicId}/activities?limit=20`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setActivities([]);
      setActivityError("Network error while loading Lead activities. Please check your connection and try again.");
      setActivityLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setActivities([]);
      setActivityError(await responseErrorMessage(response, "Could not load Lead activities."));
      setActivityLoading(false);
      return;
    }

    const data = (await response.json()) as LeadActivity[];
    setActivities(data);
    setActivityLoading(false);
  }

  async function loadLead(publicId: string) {
    setPageMessage("");
    setPageError("");

    const token = getToken();
    if (!token) {
      setLead(null);
      setPageError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);

    let response: Response;
    try {
      response = await fetch(`${LEAD_DETAIL_BASE_PATH}/${publicId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setLead(null);
      setPageError("Network error while loading this Lead. Please check your connection and try again.");
      setLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setLead(null);
      setPageError(leadDetailErrorMessage(response.status));
      setLoading(false);
      return;
    }

    const data = (await response.json()) as Lead;
    setLead(data);
    populateForm(data);
    setLastConversion(null);
    setPageMessage("Lead profile loaded.");
    setLoading(false);
    void loadActivities(data.public_id);
  }

  useEffect(() => {
    function refreshAccess() {
      setAccess(getLeadUpdateAccess());
    }

    refreshAccess();
    if (typeof leadId === "string" && leadId.trim().length > 0) {
      void loadLead(leadId);
    }

    window.addEventListener(SESSION_CHANGED_EVENT, refreshAccess);
    window.addEventListener("storage", refreshAccess);
    window.addEventListener("focus", refreshAccess);

    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, refreshAccess);
      window.removeEventListener("storage", refreshAccess);
      window.removeEventListener("focus", refreshAccess);
    };
  }, [leadId]);

  async function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUpdateMessage("");
    setUpdateError("");

    const nextAccess = getLeadUpdateAccess();
    setAccess(nextAccess);
    if (nextAccess.status !== "allowed") {
      setUpdateError(updateAccessMessage(nextAccess));
      return;
    }

    if (!lead) {
      setUpdateError("Load a Lead before updating it.");
      return;
    }

    if (companyName.trim().length === 0) {
      setUpdateError("Company name is required.");
      return;
    }

    const token = getToken();
    if (!token) {
      setUpdateError(SIGN_IN_FIRST);
      return;
    }

    setSubmitting(true);

    const payload: Record<string, string | null> = {
      lead_source: leadSource,
      source_reference: normalizeOptional(sourceReference),
      company_name: companyName.trim(),
      contact_name: normalizeOptional(contactName),
      contact_phone: normalizeOptional(contactPhone),
      contact_email: normalizeOptional(contactEmail),
      requirement_summary: normalizeOptional(requirementSummary),
      assigned_to_user_public_id: normalizeOptional(assignedToUserPublicId),
    };

    if (leadStatusCode !== lead.lead_status_code) {
      payload.lead_status_code = leadStatusCode;
    }

    let response: Response;
    try {
      response = await fetch(`${LEAD_DETAIL_BASE_PATH}/${lead.public_id}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setUpdateError("Network error while updating this Lead. Please check your connection and try again.");
      setSubmitting(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setUpdateError(await responseErrorMessage(response, "The Lead could not be updated."));
      setSubmitting(false);
      return;
    }

    const data = (await response.json()) as LeadUpdateResponse;
    setLead(data.lead);
    populateForm(data.lead);
    setUpdateMessage("Lead details updated.");
    setSubmitting(false);
  }

  async function handleCreateActivity(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActivityMessage("");
    setActivityError("");

    const nextAccess = getLeadUpdateAccess();
    setAccess(nextAccess);
    if (nextAccess.status !== "allowed") {
      setActivityError(updateAccessMessage(nextAccess));
      return;
    }

    if (!lead) {
      setActivityError("Load a Lead before recording an activity.");
      return;
    }

    const token = getToken();
    if (!token) {
      setActivityError(SIGN_IN_FIRST);
      return;
    }

    setActivitySubmitting(true);

    const payload = {
      activity_type: activityType,
      activity_at: enteredIndiaTimeToUtc(activityAt),
      notes: normalizeOptional(activityNotes),
      outcome: normalizeOptional(activityOutcome),
      next_follow_up_at: enteredIndiaTimeToUtc(nextFollowUpAt),
    };

    let response: Response;
    try {
      response = await fetch(`${LEAD_DETAIL_BASE_PATH}/${lead.public_id}/activities`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setActivityError("Network error while recording Lead activity. Please check your connection and try again.");
      setActivitySubmitting(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setActivityError(await responseErrorMessage(response, "The Lead activity could not be recorded."));
      setActivitySubmitting(false);
      return;
    }

    const data = (await response.json()) as LeadActivityCreatedResponse;
    setActivities((current) => [data.activity, ...current]);
    setActivityMessage("Lead activity recorded.");
    setActivityNotes("");
    setActivityOutcome("");
    setNextFollowUpAt("");
    setActivitySubmitting(false);
  }

  async function handleQualificationDecision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setQualificationMessage("");
    setQualificationError("");

    const nextAccess = getLeadUpdateAccess();
    setAccess(nextAccess);
    if (nextAccess.status !== "allowed") {
      setQualificationError(updateAccessMessage(nextAccess));
      return;
    }

    if (!lead) {
      setQualificationError("Load a Lead before recording a qualification decision.");
      return;
    }

    const normalizedReason = normalizeOptional(qualificationReason);
    if ((qualificationStatusCode === "UNQUALIFIED" || qualificationStatusCode === "CLOSED") && !normalizedReason) {
      setQualificationError("Reason is required when a Lead is unqualified or closed.");
      return;
    }

    const token = getToken();
    if (!token) {
      setQualificationError(SIGN_IN_FIRST);
      return;
    }

    setQualificationSubmitting(true);

    const payload = {
      decision_status_code: qualificationStatusCode,
      reason: normalizedReason,
      decision_notes: normalizeOptional(qualificationDecisionNotes),
    };

    let response: Response;
    try {
      response = await fetch(`${LEAD_DETAIL_BASE_PATH}/${lead.public_id}/qualification-decision`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setQualificationError("Network error while saving Lead qualification decision. Please check your connection and try again.");
      setQualificationSubmitting(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setQualificationError(await responseErrorMessage(response, "The Lead qualification decision could not be saved."));
      setQualificationSubmitting(false);
      return;
    }

    const data = (await response.json()) as LeadQualificationDecisionResponse;
    setLead(data.lead);
    populateForm(data.lead);
    setQualificationMessage("Lead qualification decision saved.");
    setQualificationSubmitting(false);
  }

  async function handleLeadConversion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setConversionMessage("");
    setConversionError("");
    setLastConversion(null);

    const nextAccess = getLeadUpdateAccess();
    setAccess(nextAccess);
    if (nextAccess.status !== "allowed") {
      setConversionError(updateAccessMessage(nextAccess));
      return;
    }

    if (!lead) {
      setConversionError("Load a Lead before converting it.");
      return;
    }

    if (lead.lead_status_code !== "QUALIFIED") {
      setConversionError("Only a qualified Lead can be converted.");
      return;
    }

    const token = getToken();
    if (!token) {
      setConversionError(SIGN_IN_FIRST);
      return;
    }

    setConversionSubmitting(true);

    let response: Response;
    try {
      response = await fetch(`${LEAD_DETAIL_BASE_PATH}/${lead.public_id}/convert`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ conversion_notes: normalizeOptional(conversionNotes) }),
      });
    } catch {
      setConversionError("Network error while converting this Lead. Please check your connection and try again.");
      setConversionSubmitting(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setConversionError(await responseErrorMessage(response, "The Lead could not be converted."));
      setConversionSubmitting(false);
      return;
    }

    const data = (await response.json()) as LeadConversionResponse;
    setLead(data.lead);
    populateForm(data.lead);
    setLastConversion(data);
    setConversionNotes("");
    setConversionMessage("Lead converted to Account and Opportunity.");
    setConversionSubmitting(false);
  }

  return (
    <section>
      <PageHeader
        eyebrow="Lead"
        back={{ href: "/leads", label: "Back to Leads" }}
        title={lead ? lead.company_name : "Lead"}
        badges={lead ? <StatusBadge code={lead.lead_status_code} label={formatStatusLabel(lead.lead_status_code)} /> : null}
      >
        {access.status === "allowed" ? null : <p className="helper-text">{updateAccessMessage(access)}</p>}
        {loading ? <p>Loading Lead...</p> : null}
        {pageMessage ? <p className="text-success">{pageMessage}</p> : null}
        {pageError ? <p className="text-danger">{pageError}</p> : null}
      </PageHeader>

      {lead ? (
        <>
          <SectionIndex
            items={[
              { id: "lead-enquiry", label: "The enquiry" },
              { id: "lead-follow-up", label: "Follow-up" },
              { id: "lead-decision", label: "Decision and conversion" },
              { id: "lead-record", label: "Record details" },
            ]}
          />

          <SectionGroup
            id="lead-enquiry"
            title="The enquiry"
            tone="blue"
            description="Who is asking, how to reach them and what they need."
          >
            <SectionCard title="Summary">
              <dl style={DETAIL_GRID_STYLE}>
                <DetailRow label="Company">{lead.company_name}</DetailRow>
                <DetailRow label="Status">
                  <StatusBadge code={lead.lead_status_code} label={formatStatusLabel(lead.lead_status_code)} />
                </DetailRow>
                <DetailRow label="Lead source">{optionLabel(LEAD_SOURCE_OPTIONS, lead.lead_source)}</DetailRow>
                <DetailRow label="Source reference">{displayValue(lead.source_reference)}</DetailRow>
                <DetailRow label="Assigned to">
                  {displayValue(lead.assigned_to_display_name ?? lead.assigned_to_user_public_id)}
                </DetailRow>
                <DetailRow label="Qualification reason">{displayValue(lead.qualification_reason)}</DetailRow>
                <DetailRow label="Converted Account">
                  {lead.converted_account_public_id ? (
                    <>
                      <a href={`/accounts/${lead.converted_account_public_id}`} style={LINK_STYLE}>
                        Open Account
                      </a>{" "}
                      <ReferenceText>{lead.converted_account_public_id}</ReferenceText>
                    </>
                  ) : (
                    "-"
                  )}
                </DetailRow>
                <DetailRow label="Converted Opportunity">
                  {lead.converted_opportunity_public_id ? (
                    <>
                      <a href={`/opportunities/${lead.converted_opportunity_public_id}`} style={LINK_STYLE}>
                        Open Opportunity
                      </a>{" "}
                      <ReferenceText>{lead.converted_opportunity_public_id}</ReferenceText>
                    </>
                  ) : (
                    "-"
                  )}
                </DetailRow>
              </dl>
            </SectionCard>

            <div style={TWO_COLUMN_STYLE}>
              <SectionCard title="Contact">
                <dl style={COMPACT_DETAIL_GRID_STYLE}>
                  <DetailRow label="Contact name">{displayValue(lead.contact_name)}</DetailRow>
                  <DetailRow label="Contact phone">{displayValue(lead.contact_phone)}</DetailRow>
                  <DetailRow label="Contact email">{displayValue(lead.contact_email)}</DetailRow>
                </dl>
              </SectionCard>

              <SectionCard title="Requirement">
                <p style={{ whiteSpace: "pre-wrap" }}>{displayValue(lead.requirement_summary)}</p>
              </SectionCard>
            </div>

            {access.status === "allowed" && !leadCanBeChanged(lead.lead_status_code) ? (
              <SectionCard title="Update Lead details">
                <p className="text-warning">{CONVERTED_LEAD_NOTE}</p>
              </SectionCard>
            ) : access.status === "allowed" ? (
              <SectionCard title="Update Lead details">
                <form onSubmit={handleUpdate} style={{ display: "grid", gap: "12px", maxWidth: "760px" }}>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Lead source
                    <select value={leadSource} onChange={(event) => { setLeadSource(event.target.value); setUpdateMessage(""); setUpdateError(""); }} style={{ padding: "8px" }}>
                      {LEAD_SOURCE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Source reference
                    <input value={sourceReference} onChange={(event) => { setSourceReference(event.target.value); setUpdateMessage(""); setUpdateError(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Company name
                    <input value={companyName} onChange={(event) => { setCompanyName(event.target.value); setUpdateMessage(""); setUpdateError(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Contact name
                    <input value={contactName} onChange={(event) => { setContactName(event.target.value); setUpdateMessage(""); setUpdateError(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Contact phone
                    <input value={contactPhone} onChange={(event) => { setContactPhone(event.target.value); setUpdateMessage(""); setUpdateError(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Contact email
                    <input value={contactEmail} onChange={(event) => { setContactEmail(event.target.value); setUpdateMessage(""); setUpdateError(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Lead status
                    <select value={leadStatusCode} onChange={(event) => { setLeadStatusCode(event.target.value); setUpdateMessage(""); setUpdateError(""); }} style={{ padding: "8px" }}>
                      {leadDetailsStatusOptions(lead.lead_status_code).map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Assigned to (user ID)
                    <input value={assignedToUserPublicId} onChange={(event) => { setAssignedToUserPublicId(event.target.value); setUpdateMessage(""); setUpdateError(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Requirement summary
                    <textarea value={requirementSummary} onChange={(event) => { setRequirementSummary(event.target.value); setUpdateMessage(""); setUpdateError(""); }} rows={4} style={{ padding: "8px" }} />
                  </label>

                  <div>
                    <button type="submit" disabled={submitting} style={{ padding: "8px 12px" }}>
                      {submitting ? "Saving..." : "Save Lead Details"}
                    </button>
                    {updateMessage ? <p className="text-success" style={{ marginBottom: 0 }}>{updateMessage}</p> : null}
                    {updateError ? <p className="text-danger" style={{ marginBottom: 0 }}>{updateError}</p> : null}
                  </div>
                </form>
              </SectionCard>
            ) : null}
          </SectionGroup>

          <SectionGroup
            id="lead-follow-up"
            title="Follow-up"
            tone="teal"
            description="Calls, messages and meetings with this company."
          >
            <SectionCard title="Follow-up activities">
              <p>
                Record each call, email, WhatsApp message, meeting or note with this company. Times are shown in India
                time (IST).
              </p>

              {access.status === "allowed" ? (
                <form onSubmit={handleCreateActivity} style={{ display: "grid", gap: "12px", maxWidth: "760px", marginBottom: "16px" }}>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Activity type
                    <select value={activityType} onChange={(event) => { setActivityType(event.target.value); setActivityMessage(""); setActivityError(""); }} style={{ padding: "8px" }}>
                      {LEAD_ACTIVITY_TYPE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Activity date/time (IST)
                    <DateInput withTime value={activityAt} onChange={(event) => { setActivityAt(event.target.value); setActivityMessage(""); setActivityError(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Notes
                    <textarea value={activityNotes} onChange={(event) => { setActivityNotes(event.target.value); setActivityMessage(""); setActivityError(""); }} rows={3} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Outcome
                    <input value={activityOutcome} onChange={(event) => { setActivityOutcome(event.target.value); setActivityMessage(""); setActivityError(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Next follow-up date/time (IST)
                    <DateInput withTime value={nextFollowUpAt} onChange={(event) => { setNextFollowUpAt(event.target.value); setActivityMessage(""); setActivityError(""); }} style={{ padding: "8px" }} />
                  </label>

                  <div>
                    <button type="submit" disabled={activitySubmitting} style={{ padding: "8px 12px" }}>
                      {activitySubmitting ? "Recording..." : "Record Lead Activity"}
                    </button>
                    {activityMessage ? <p className="text-success" style={{ marginBottom: 0 }}>{activityMessage}</p> : null}
                    {activityError ? <p className="text-danger" style={{ marginBottom: 0 }}>{activityError}</p> : null}
                  </div>
                </form>
              ) : (
                <p style={{ color: "#6b7280" }}>Only Sales and Admin users can record follow-up activities.</p>
              )}

              {activityLoading ? <p>Loading follow-up activities...</p> : null}
              {activityError && access.status !== "allowed" ? <p className="text-danger">{activityError}</p> : null}

              {activities.length === 0 ? (
                <p>No follow-up activities recorded yet.</p>
              ) : (
                <div className="data-table-wrap" style={{ marginTop: "12px" }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>When</th>
                        <th>Type</th>
                        <th>Notes / Outcome</th>
                        <th>Next follow-up</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activities.map((activity) => (
                        <tr key={activity.public_id}>
                          <td>{formatDateTime(activity.activity_at)}</td>
                          <td>
                            {optionLabel(LEAD_ACTIVITY_TYPE_OPTIONS, activity.activity_type)}
                          </td>
                          <td>
                            <div style={{ whiteSpace: "pre-wrap" }}>{displayValue(activity.notes)}</div>
                            <div style={{ color: "#6b7280", fontSize: "12px" }}>Outcome: {displayValue(activity.outcome)}</div>
                          </td>
                          <td>{formatDateTime(activity.next_follow_up_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>

            <InteractionLog linkedRecordType="lead" linkedRecordPublicId={lead.public_id} />
          </SectionGroup>

          <SectionGroup
            id="lead-decision"
            title="Decision and conversion"
            tone="violet"
            description="Decide whether to pursue this Lead, then convert it."
          >
            <SectionCard title="Qualification decision">
              <p>
                Record whether this Lead is ready for qualification, qualified, unqualified or closed. A qualified Lead can
                then be converted below.
              </p>

              {access.status === "allowed" && !leadCanBeChanged(lead.lead_status_code) ? (
                <p className="text-warning">{CONVERTED_LEAD_NOTE}</p>
              ) : access.status === "allowed" ? (
                <form onSubmit={handleQualificationDecision} style={{ display: "grid", gap: "12px", maxWidth: "760px" }}>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Decision
                    <select value={qualificationStatusCode} onChange={(event) => { setQualificationStatusCode(event.target.value); setQualificationMessage(""); setQualificationError(""); }} style={{ padding: "8px" }}>
                      {LEAD_QUALIFICATION_STATUS_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Reason
                    <input value={qualificationReason} onChange={(event) => { setQualificationReason(event.target.value); setQualificationMessage(""); setQualificationError(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Decision notes
                    <textarea value={qualificationDecisionNotes} onChange={(event) => { setQualificationDecisionNotes(event.target.value); setQualificationMessage(""); setQualificationError(""); }} rows={3} style={{ padding: "8px" }} />
                  </label>

                  <div>
                    <button type="submit" disabled={qualificationSubmitting} style={{ padding: "8px 12px" }}>
                      {qualificationSubmitting ? "Saving..." : "Save Qualification Decision"}
                    </button>
                    {qualificationMessage ? <p className="text-success" style={{ marginBottom: 0 }}>{qualificationMessage}</p> : null}
                    {qualificationError ? <p className="text-danger" style={{ marginBottom: 0 }}>{qualificationError}</p> : null}
                  </div>
                </form>
              ) : (
                <p style={{ color: "#6b7280" }}>Only Sales and Admin users can record a qualification or closure decision.</p>
              )}

              <dl style={{ ...DETAIL_GRID_STYLE, marginTop: "16px", marginBottom: 0 }}>
                <DetailRow label="Current status">
                  <StatusBadge code={lead.lead_status_code} label={formatStatusLabel(lead.lead_status_code)} />
                </DetailRow>
                <DetailRow label="Reason">{displayValue(lead.qualification_reason)}</DetailRow>
                <DetailRow label="Decision notes">
                  <span style={{ whiteSpace: "pre-wrap" }}>{displayValue(lead.qualification_decision_notes)}</span>
                </DetailRow>
                <DetailRow label="Decided by">
                  {lead.qualification_decided_by ? <ReferenceText>{lead.qualification_decided_by}</ReferenceText> : "-"}
                </DetailRow>
                <DetailRow label="Decided at">{formatDateTime(lead.qualification_decided_at)}</DetailRow>
              </dl>
            </SectionCard>

            <SectionCard title="Convert to Account and Opportunity">
              <p>
                Converting a qualified Lead creates an Account (as a qualified prospect) and a linked Opportunity, then
                marks this Lead as Converted.
              </p>

              {access.status === "allowed" && lead.lead_status_code === "QUALIFIED" ? (
                <form onSubmit={handleLeadConversion} style={{ display: "grid", gap: "12px", maxWidth: "760px" }}>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Conversion notes
                    <textarea value={conversionNotes} onChange={(event) => { setConversionNotes(event.target.value); setConversionMessage(""); setConversionError(""); }} rows={3} style={{ padding: "8px" }} />
                  </label>

                  <div>
                    <button type="submit" disabled={conversionSubmitting} style={{ padding: "8px 12px" }}>
                      {conversionSubmitting ? "Converting..." : "Convert Lead"}
                    </button>
                    {conversionMessage ? <p className="text-success" style={{ marginBottom: 0 }}>{conversionMessage}</p> : null}
                    {conversionError ? <p className="text-danger" style={{ marginBottom: 0 }}>{conversionError}</p> : null}
                  </div>
                </form>
              ) : (
                <p style={{ color: "#6b7280" }}>
                  Conversion is available to Sales and Admin users once the Lead is Qualified. Current status:{" "}
                  {formatStatusLabel(lead.lead_status_code)}.
                </p>
              )}

              {lastConversion ? (
                <div style={{ marginTop: "16px", padding: "12px", border: "1px solid #bbf7d0", borderRadius: "8px", background: "#f0fdf4" }}>
                  <strong>Created by conversion:</strong>
                  <ul style={{ marginBottom: 0 }}>
                    <li><a href={`/accounts/${lastConversion.account.public_id}`} style={LINK_STYLE}>Account: {lastConversion.account.account_name}</a></li>
                    <li><a href={`/opportunities/${lastConversion.opportunity.public_id}`} style={LINK_STYLE}>Opportunity: {lastConversion.opportunity.opportunity_name}</a></li>
                  </ul>
                </div>
              ) : null}
            </SectionCard>
          </SectionGroup>

          <SectionGroup
            id="lead-record"
            title="Record details"
            tone="slate"
            description="Reference, history and what is not built yet."
          >
            <div style={TWO_COLUMN_STYLE}>
              <SectionCard title="Reference and history">
                <p style={{ color: "#6b7280" }}>Times are shown in India time.</p>
                <dl style={COMPACT_DETAIL_GRID_STYLE}>
                  <DetailRow label="Reference">
                    <ReferenceText>{lead.public_id}</ReferenceText>
                  </DetailRow>
                  <DetailRow label="Created by">{displayValue(lead.created_by_display_name ?? lead.created_by)}</DetailRow>
                  <DetailRow label="Created">{formatDateTime(lead.created_at)}</DetailRow>
                  <DetailRow label="Updated">{formatDateTime(lead.updated_at)}</DetailRow>
                </dl>
              </SectionCard>

              <SectionCard title="Not built yet">
                <ul>
                  <li>Checking whether this company is already recorded as a Lead or an Account</li>
                  <li>Assigning follow-up tasks and sending reminders</li>
                </ul>
              </SectionCard>
            </div>
          </SectionGroup>
        </>
      ) : null}
    </section>
  );
}

