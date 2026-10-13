import { FormEvent, useEffect, useState } from "react";
import DateInput from "../../components/DateInput";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";

const OPPORTUNITY_CREATE_PATH = "/api/opportunities";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const VIEWED_OPPORTUNITY_IDS_KEY = "pbl_viewed_opportunity_ids_this_session";
const OPPORTUNITY_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];

const OPPORTUNITY_SOURCE_OPTIONS = [
  { value: "manual", label: "Manual" },
  { value: "rfq", label: "RFQ" },
  { value: "tender", label: "Tender" },
  { value: "repeat_enquiry", label: "Repeat enquiry" },
  { value: "account_review", label: "Account review" },
  { value: "external_intelligence", label: "Reviewed external intelligence" },
  { value: "other", label: "Other" },
] as const;

const OPPORTUNITY_CREATE_STATUS_OPTIONS = [
  { value: "NEW", label: "New" },
  { value: "NEEDS_REVIEW", label: "Needs Review" },
] as const;

type TokenPayload = {
  role_codes?: unknown;
  exp?: unknown;
};

type CreateAccessStatus = "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token";

type CreateAccess = {
  status: CreateAccessStatus;
  roleCodes: string[];
};

type CreatedOpportunity = {
  public_id: string;
  opportunity_name: string;
  opportunity_source: string;
  opportunity_status_code: string;
};

type CreateResponse = {
  opportunity: CreatedOpportunity;
  event: {
    event_name?: string | null;
    record_public_id?: string | null;
  };
};

function clearPrototypeSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("pbl_auth_token");
  window.sessionStorage.removeItem(VIEWED_OPPORTUNITY_IDS_KEY);
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

function getCreateAccess(): CreateAccess {
  const token = getToken();
  if (!token) return { status: "no_token", roleCodes: [] };

  const payload = decodeTokenPayload(token);
  if (!payload) return { status: "invalid_token", roleCodes: [] };

  const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp ?? 0);
  if (exp > 0 && exp * 1000 < Date.now()) {
    clearPrototypeSession();
    return { status: "expired", roleCodes: [] };
  }

  const roleCodes = Array.isArray(payload.role_codes)
    ? payload.role_codes.filter((role): role is string => typeof role === "string")
    : [];

  const allowed = roleCodes.some((role) => OPPORTUNITY_CREATE_ROLES.includes(role));
  return { status: allowed ? "allowed" : "denied", roleCodes };
}

function createAccessMessage(status: CreateAccessStatus): string {
  if (status === "checking") return "Checking Opportunity create access...";
  if (status === "no_token") return "Sign in as a Sales or Admin user to create Opportunities.";
  if (status === "expired") return "Sign in again because the current session has expired.";
  if (status === "invalid_token") return "Sign in again because your session could not be read.";
  if (status === "denied") return "Your role can view Opportunities but cannot create Opportunities.";
  return "";
}

function normalizeOptional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

async function createErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role cannot create Opportunities.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return "Could not create Opportunity. Please try again.";
}

export default function NewOpportunityPage() {
  const [opportunityName, setOpportunityName] = useState("");
  const [opportunitySource, setOpportunitySource] = useState("manual");
  const [sourceReference, setSourceReference] = useState("");
  const [customerRequirementSummary, setCustomerRequirementSummary] = useState("");
  const [estimatedValue, setEstimatedValue] = useState("");
  const [expectedCloseDate, setExpectedCloseDate] = useState("");
  const [opportunityStatusCode, setOpportunityStatusCode] = useState("NEW");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [created, setCreated] = useState<CreateResponse | null>(null);
  const [createAccess, setCreateAccess] = useState<CreateAccess>({ status: "checking", roleCodes: [] });

  useEffect(() => {
    function refreshCreateAccess() {
      setCreateAccess(getCreateAccess());
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

    const access = getCreateAccess();
    setCreateAccess(access);
    if (access.status !== "allowed") {
      setError(createAccessMessage(access.status));
      return;
    }

    if (opportunityName.trim().length === 0) {
      setError("Opportunity name is required.");
      return;
    }

    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setSubmitting(true);

    const payload = {
      opportunity_name: opportunityName.trim(),
      opportunity_source: opportunitySource,
      source_reference: normalizeOptional(sourceReference),
      customer_requirement_summary: normalizeOptional(customerRequirementSummary),
      estimated_value: normalizeOptional(estimatedValue),
      expected_close_date: normalizeOptional(expectedCloseDate),
      opportunity_status_code: opportunityStatusCode,
    };

    let response: Response;
    try {
      response = await fetch(OPPORTUNITY_CREATE_PATH, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setError("Network error while creating the Opportunity. Please check your connection and try again.");
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
    setMessage("Opportunity created successfully.");
    setOpportunityName("");
    setOpportunitySource("manual");
    setSourceReference("");
    setCustomerRequirementSummary("");
    setEstimatedValue("");
    setExpectedCloseDate("");
    setOpportunityStatusCode("NEW");
    setSubmitting(false);
  }

  return (
    <section>
      <h2>Create Opportunity</h2>
      <p>
        Record a new customer requirement you are pursuing. After saving, you can link it to the customer&apos;s Account
        and prepare Commercial Offers from the Opportunity page.
      </p>

      <div className="page-actions">
        <a className="button-link-secondary" href="/opportunities">
          Back to Opportunities
        </a>
      </div>

      {createAccess.status === "checking" ? (
        <p style={{ marginTop: "24px" }}>Checking Opportunity create access...</p>
      ) : createAccess.status !== "allowed" ? (
        <div className="content-card">
          <h3>Opportunity creation not available</h3>
          <p style={{ color: "crimson" }}>{createAccessMessage(createAccess.status)}</p>
          <p>Only Admin, Sales User and Sales Manager roles can create Opportunities.</p>
          <p>
            <a href="/login" style={{ color: "#1d4ed8", fontWeight: 700, textDecoration: "underline" }}>
              Go to Sign in
            </a>
          </p>
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
          className="form-card"
        >
          <label className="field-stack">
            Opportunity name <span style={{ color: "crimson" }}>*</span>
            <input
              value={opportunityName}
              onChange={(event) => setOpportunityName(event.target.value)}
              maxLength={255}
              required
            />
          </label>

          <label className="field-stack">
            Opportunity source
            <select value={opportunitySource} onChange={(event) => setOpportunitySource(event.target.value)}>
              {OPPORTUNITY_SOURCE_OPTIONS.map((option) => (
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
              placeholder="RFQ/tender/enquiry reference, if any"
            />
          </label>

          <label className="field-stack">
            Customer requirement summary
            <textarea
              value={customerRequirementSummary}
              onChange={(event) => setCustomerRequirementSummary(event.target.value)}
              maxLength={4000}
              rows={5}
            />
          </label>

          <div className="form-grid">
            <label className="field-stack">
              Estimated value
              <input
                value={estimatedValue}
                onChange={(event) => setEstimatedValue(event.target.value)}
                type="number"
                min="0"
                step="0.01"
              />
            </label>

            <label className="field-stack">
              Expected close date
              <DateInput
                value={expectedCloseDate}
                onChange={(event) => setExpectedCloseDate(event.target.value)}
              />
            </label>

            <label className="field-stack">
              Initial status
              <select value={opportunityStatusCode} onChange={(event) => setOpportunityStatusCode(event.target.value)}>
                {OPPORTUNITY_CREATE_STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <button type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create Opportunity"}
            </button>
            {message ? <p className="action-feedback" style={{ color: "#065f46" }}>{message}</p> : null}
            {error ? <p className="action-feedback" style={{ color: "crimson" }}>{error}</p> : null}
          </div>
        </form>
      )}

      {created ? (
        <div className="content-card">
          <h3>Created Opportunity</h3>
          <p><strong>Name:</strong> {created.opportunity.opportunity_name}</p>
          <p><strong>Source:</strong> {created.opportunity.opportunity_source}</p>
          <p><strong>Status:</strong> {created.opportunity.opportunity_status_code}</p>
          <p>
            <a href={`/opportunities/${created.opportunity.public_id}`} style={{ color: "#1d4ed8", fontWeight: 700, textDecoration: "underline" }}>
              Open Opportunity profile
            </a>
          </p>
        </div>
      ) : null}
    </section>
  );
}
