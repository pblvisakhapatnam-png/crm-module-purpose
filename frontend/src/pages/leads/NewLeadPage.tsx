import { FormEvent, useEffect, useState } from "react";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";

const LEAD_CREATE_PATH = "/api/leads";
const LEAD_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];
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

const LEAD_STATUS_OPTIONS = [
  { value: "NEW", label: "New" },
  { value: "REVIEW_PENDING", label: "Review Pending" },
];

type CreatedLead = {
  public_id: string;
  lead_source: string;
  company_name: string;
  contact_name?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  requirement_summary?: string | null;
  lead_status_code: string;
  created_at: string;
};

type CreateResponse = {
  lead: CreatedLead;
  event: {
    public_id: string;
    event_name: string;
    record_type: string;
    record_public_id: string;
  };
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

type LeadCreateAccessStatus = "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token";

type LeadCreateAccess = {
  status: LeadCreateAccessStatus;
  roleCodes: string[];
};

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("pbl_auth_token");
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

function getLeadCreateAccess(): LeadCreateAccess {
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

  const allowed = roleCodes.some((role) => LEAD_CREATE_ROLES.includes(role));
  return { status: allowed ? "allowed" : "denied", roleCodes };
}

function leadCreateAccessMessage(status: LeadCreateAccessStatus): string {
  if (status === "no_token") return "Sign in first as a Sales or Admin user to create Leads.";
  if (status === "expired") return "Sign in again to create Leads because the current session has expired.";
  if (status === "invalid_token") return "Sign in again to create Leads because the current session is invalid.";
  if (status === "denied") return "Your role can view Leads but cannot create new Leads.";
  return "";
}

function normalizeOptional(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function validationDetailToMessage(detail: ValidationErrorDetail | undefined): string {
  if (!detail) return "The Lead could not be created. Check the form and try again.";

  if (typeof detail === "string") return detail;

  const messages = detail
    .map((item) => item.msg)
    .filter((value): value is string => Boolean(value));

  if (messages.length === 0) return "The Lead could not be created. Check the form and try again.";

  return messages.join(" ");
}

async function createErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "You do not have permission to create Leads.";
  if (response.status === 404) return "Lead creation is not available right now. Ask an administrator to check the service.";

  if (response.status === 422) {
    try {
      const body = (await response.json()) as { detail?: ValidationErrorDetail };
      return validationDetailToMessage(body.detail);
    } catch {
      return "The Lead could not be created because the form contains invalid values.";
    }
  }

  return "The Lead could not be created. Please try again.";
}

export default function NewLeadPage() {
  const [leadSource, setLeadSource] = useState("manual");
  const [sourceReference, setSourceReference] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [requirementSummary, setRequirementSummary] = useState("");
  const [leadStatusCode, setLeadStatusCode] = useState("NEW");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [created, setCreated] = useState<CreateResponse | null>(null);
  const [createAccess, setCreateAccess] = useState<LeadCreateAccess>({ status: "checking", roleCodes: [] });

  useEffect(() => {
    function refreshCreateAccess() {
      setCreateAccess(getLeadCreateAccess());
    }

    refreshCreateAccess();
    window.addEventListener(SESSION_CHANGED_EVENT, refreshCreateAccess);
    window.addEventListener("storage", refreshCreateAccess);
    window.addEventListener("focus", refreshCreateAccess);

    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, refreshCreateAccess);
      window.removeEventListener("storage", refreshCreateAccess);
      window.removeEventListener("focus", refreshCreateAccess);
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setError("");
    setCreated(null);

    const access = getLeadCreateAccess();
    setCreateAccess(access);
    if (access.status !== "allowed") {
      setError(leadCreateAccessMessage(access.status));
      return;
    }

    if (companyName.trim().length === 0) {
      setError("Company name is required.");
      return;
    }

    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setSubmitting(true);

    const payload = {
      lead_source: leadSource,
      source_reference: normalizeOptional(sourceReference),
      company_name: companyName.trim(),
      contact_name: normalizeOptional(contactName),
      contact_phone: normalizeOptional(contactPhone),
      contact_email: normalizeOptional(contactEmail),
      requirement_summary: normalizeOptional(requirementSummary),
      lead_status_code: leadStatusCode,
    };

    let response: Response;
    try {
      response = await fetch(LEAD_CREATE_PATH, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setError("Network error while creating the Lead. Please check your connection and try again.");
      setSubmitting(false);
      return;
    }

    if (!response.ok) {
      setError(await createErrorMessage(response));
      setSubmitting(false);
      return;
    }

    const data = (await response.json()) as CreateResponse;
    setCreated(data);
    setMessage("Lead created successfully.");
    setLeadSource("manual");
    setSourceReference("");
    setCompanyName("");
    setContactName("");
    setContactPhone("");
    setContactEmail("");
    setRequirementSummary("");
    setLeadStatusCode("NEW");
    setSubmitting(false);
  }

  return (
    <section>
      <h2>Create Lead</h2>
      <p>
        Record a new sales enquiry. After saving, you can qualify it and convert it into an Account and an
        Opportunity from the Lead page.
      </p>

      <div className="page-actions">
        <a className="button-link-secondary" href="/leads">Back to Leads</a>
      </div>

      {createAccess.status === "checking" ? (
        <p style={{ marginTop: "24px" }}>Checking Lead create access...</p>
      ) : createAccess.status !== "allowed" ? (
        <div className="content-card">
          <h3>Lead creation not available</h3>
          <p style={{ color: "crimson" }}>{leadCreateAccessMessage(createAccess.status)}</p>
          <p>Only Admin, Sales User and Sales Manager roles can create Leads.</p>
          <p><a href="/login">Go to Sign in</a></p>
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
          className="form-card"
        >
          <label className="field-stack">
            Lead source
            <select value={leadSource} onChange={(event) => setLeadSource(event.target.value)}>
              {LEAD_SOURCE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          <label className="field-stack">
            Source reference
            <input
              value={sourceReference}
              onChange={(event) => setSourceReference(event.target.value)}
              maxLength={255}
              placeholder="Email subject, WhatsApp note, tender ref, enquiry ref, etc."
            />
          </label>

          <label className="field-stack">
            Company name <span style={{ color: "crimson" }}>*</span>
            <input
              value={companyName}
              onChange={(event) => setCompanyName(event.target.value)}
              maxLength={255}
              required
            />
          </label>

          <label className="field-stack">
            Contact name
            <input value={contactName} onChange={(event) => setContactName(event.target.value)} maxLength={255} />
          </label>

          <label className="field-stack">
            Contact phone
            <input value={contactPhone} onChange={(event) => setContactPhone(event.target.value)} maxLength={50} />
          </label>

          <label className="field-stack">
            Contact email
            <input value={contactEmail} onChange={(event) => setContactEmail(event.target.value)} maxLength={255} />
          </label>

          <label className="field-stack">
            Requirement summary
            <textarea
              value={requirementSummary}
              onChange={(event) => setRequirementSummary(event.target.value)}
              maxLength={4000}
              rows={5}
            />
          </label>

          <label className="field-stack">
            Lead status
            <select value={leadStatusCode} onChange={(event) => setLeadStatusCode(event.target.value)}>
              {LEAD_STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          <div>
            <button type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create Lead"}
            </button>
            {message ? <p className="action-feedback" style={{ color: "#065f46" }}>{message}</p> : null}
            {error ? <p className="action-feedback" style={{ color: "crimson" }}>{error}</p> : null}
          </div>
        </form>
      )}

      {created ? (
        <div className="content-card">
          <h3>Created Lead</h3>
          <p><strong>Company:</strong> {created.lead.company_name}</p>
          <p><strong>Status:</strong> {created.lead.lead_status_code}</p>
          <p><strong>Reference:</strong> {created.lead.public_id}</p>
        </div>
      ) : null}
    </section>
  );
}
