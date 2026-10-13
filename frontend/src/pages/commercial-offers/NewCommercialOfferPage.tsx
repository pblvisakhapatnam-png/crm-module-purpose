import { FormEvent, useEffect, useState } from "react";
import CurrencySelect from "../../components/CurrencySelect";
import DateInput from "../../components/DateInput";
import { isOperatingCurrency, UNSUPPORTED_CURRENCY_MESSAGE } from "../../components/currency";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const COMMERCIAL_OFFER_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];
const INACTIVE_FOR_NEW_OFFER_STATUSES = ["WITHDRAWN", "REJECTED", "CLOSED"];

const OFFER_MODE_OPTIONS = [
  { value: "plum_generated", label: "Plum-generated quote" },
  { value: "external_tender", label: "External / tender response" },
  { value: "customer_format", label: "Customer format" },
  { value: "budgetary_response", label: "Budgetary response" },
  { value: "other", label: "Other" },
] as const;

const OFFER_TYPE_OPTIONS = [
  { value: "budgetary", label: "Budgetary" },
  { value: "firm", label: "Firm" },
  { value: "tender_response", label: "Tender response" },
  { value: "revision", label: "Revision" },
  { value: "other", label: "Other" },
] as const;

type Opportunity = {
  public_id: string;
  opportunity_name: string;
  opportunity_status_code: string;
  account_public_id?: string | null;
};

type CommercialOffer = {
  public_id: string;
  offer_code: string;
  opportunity_public_id: string;
  offer_title?: string | null;
  offer_mode: string;
  offer_type: string;
  offer_status_code: string;
};

type CommercialOfferCreatedResponse = {
  commercial_offer: CommercialOffer;
  event: { event_name?: string | null };
};

type TokenPayload = {
  role_codes?: unknown;
  exp?: unknown;
};

type PageAccessStatus = "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token";

type PageAccess = {
  status: PageAccessStatus;
  roleCodes: string[];
  canCreate: boolean;
};

type FormState = {
  opportunity_public_id: string;
  offer_title: string;
  offer_mode: string;
  offer_type: string;
  offer_value: string;
  currency_code: string;
  offer_date: string;
  valid_until: string;
  remarks: string;
};

function emptyForm(prefilledOpportunityId = ""): FormState {
  return {
    opportunity_public_id: prefilledOpportunityId,
    offer_title: "",
    offer_mode: "plum_generated",
    offer_type: "budgetary",
    offer_value: "",
    currency_code: "INR",
    offer_date: "",
    valid_until: "",
    remarks: "",
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
  if (!token) return { status: "no_token", roleCodes: [], canCreate: false };

  const payload = decodeTokenPayload(token);
  if (!payload) return { status: "invalid_token", roleCodes: [], canCreate: false };

  const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp ?? 0);
  if (exp > 0 && exp * 1000 < Date.now()) {
    clearPrototypeSession();
    return { status: "expired", roleCodes: [], canCreate: false };
  }

  const roleCodes = Array.isArray(payload.role_codes)
    ? payload.role_codes.filter((role): role is string => typeof role === "string")
    : [];
  const canCreate = hasAnyRole(roleCodes, COMMERCIAL_OFFER_CREATE_ROLES);
  return { status: canCreate ? "allowed" : "denied", roleCodes, canCreate };
}

function normalizeOptional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function isValidFourDigitYearDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;

  const [yearPart, monthPart, dayPart] = value.split("-");
  const year = Number(yearPart);
  const month = Number(monthPart);
  const day = Number(dayPart);
  if (year < 1000 || month < 1 || month > 12 || day < 1 || day > 31) return false;

  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

function isActionableCommercialOffer(offer: CommercialOffer): boolean {
  return !INACTIVE_FOR_NEW_OFFER_STATUSES.includes(offer.offer_status_code);
}

function formatStatusLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function createAccessMessage(access: PageAccess): string {
  if (access.status === "checking") return "Checking Commercial Offer create access...";
  if (access.status === "no_token") return "Sign in as a Sales or Admin user to create Commercial Offers.";
  if (access.status === "expired") return "Sign in again because the current session has expired.";
  if (access.status === "invalid_token") return "Sign in again because the current session token is not readable.";
  if (!access.canCreate) return "Your role can view Commercial Offers but cannot create them.";
  return "You can create a Commercial Offer for an existing Opportunity.";
}

async function commercialOfferCreateErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role cannot create Commercial Offers.";
  if (response.status === 404) return "The selected Opportunity could not be found.";
  if (response.status === 422) return "The Commercial Offer could not be created. Check the highlighted form values and try again.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return "Could not create Commercial Offer. Please try again.";
}

export default function NewCommercialOfferPage() {
  const [form, setForm] = useState<FormState>(emptyForm());
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loadingOpportunities, setLoadingOpportunities] = useState(false);
  const [checkingExistingOffer, setCheckingExistingOffer] = useState(false);
  const [existingActionableOffer, setExistingActionableOffer] = useState<CommercialOffer | null>(null);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [createdOffer, setCreatedOffer] = useState<CommercialOffer | null>(null);
  const [pageAccess, setPageAccess] = useState<PageAccess>({ status: "checking", roleCodes: [], canCreate: false });

  async function loadOpportunities() {
    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoadingOpportunities(true);
    let response: Response;
    try {
      response = await fetch("/api/opportunities?limit=100", {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setError("Network error while loading Opportunities. Check that the backend and frontend services are running.");
      setLoadingOpportunities(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setError("Could not load Opportunities for offer creation. Please refresh and try again.");
      setLoadingOpportunities(false);
      return;
    }

    const data = (await response.json()) as Opportunity[];
    setOpportunities(data);
    setLoadingOpportunities(false);
  }

  async function checkExistingActionableOffer(opportunityPublicId: string) {
    const trimmedOpportunityId = opportunityPublicId.trim();
    setExistingActionableOffer(null);
    if (!trimmedOpportunityId) return;

    const token = getToken();
    if (!token) return;

    setCheckingExistingOffer(true);
    let response: Response;
    try {
      response = await fetch(`/api/commercial-offers?limit=20&opportunity_public_id=${encodeURIComponent(trimmedOpportunityId)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setCheckingExistingOffer(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setCheckingExistingOffer(false);
      return;
    }

    const data = (await response.json()) as CommercialOffer[];
    setExistingActionableOffer(data.find(isActionableCommercialOffer) ?? null);
    setCheckingExistingOffer(false);
  }

  useEffect(() => {
    const initialOpportunityId = new URLSearchParams(window.location.search).get("opportunityId") ?? "";
    if (initialOpportunityId) {
      setForm((current) => ({
        ...current,
        opportunity_public_id: current.opportunity_public_id || initialOpportunityId,
      }));
      void checkExistingActionableOffer(initialOpportunityId);
    }

    function refreshAccess() {
      setPageAccess(readPageAccess());
    }

    refreshAccess();
    void loadOpportunities();

    window.addEventListener(SESSION_CHANGED_EVENT, refreshAccess);
    window.addEventListener("storage", refreshAccess);
    window.addEventListener("focus", refreshAccess);

    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, refreshAccess);
      window.removeEventListener("storage", refreshAccess);
      window.removeEventListener("focus", refreshAccess);
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setError("");
    setCreatedOffer(null);

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canCreate) {
      setError("Your role cannot create Commercial Offers.");
      return;
    }

    if (!form.opportunity_public_id.trim()) {
      setError("Select an Opportunity before creating a Commercial Offer.");
      return;
    }

    if (existingActionableOffer) {
      setMessage(`Opening existing active/actionable Commercial Offer ${existingActionableOffer.offer_code}.`);
      window.location.href = `/commercial-offers/${existingActionableOffer.public_id}`;
      return;
    }

    const offerValue = form.offer_value.trim();
    if (offerValue.length > 0 && Number(offerValue) < 0) {
      setError("Offer value cannot be negative.");
      return;
    }

    const currencyCode = form.currency_code.trim().toUpperCase();
    if (!isOperatingCurrency(currencyCode)) {
      setError(UNSUPPORTED_CURRENCY_MESSAGE);
      return;
    }

    if (form.offer_date && !isValidFourDigitYearDate(form.offer_date)) {
      setError("Offer date must be a valid date with a four-digit year.");
      return;
    }

    if (form.valid_until && !isValidFourDigitYearDate(form.valid_until)) {
      setError("Valid until date must be a valid date with a four-digit year.");
      return;
    }

    if (form.offer_date && form.valid_until && form.valid_until < form.offer_date) {
      setError("Valid until date cannot be earlier than offer date.");
      return;
    }

    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setCreating(true);

    const payload = {
      opportunity_public_id: form.opportunity_public_id,
      offer_title: normalizeOptional(form.offer_title),
      offer_mode: form.offer_mode,
      offer_type: form.offer_type,
      offer_status_code: "DRAFT",
      offer_value: normalizeOptional(form.offer_value),
      currency_code: currencyCode,
      offer_date: normalizeOptional(form.offer_date),
      valid_until: normalizeOptional(form.valid_until),
      remarks: normalizeOptional(form.remarks),
    };

    let response: Response;
    try {
      response = await fetch("/api/commercial-offers", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setError("Network error while creating Commercial Offer. Check that the backend and frontend services are running.");
      setCreating(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setError(await commercialOfferCreateErrorMessage(response));
      setCreating(false);
      return;
    }

    const data = (await response.json()) as CommercialOfferCreatedResponse;
    setCreatedOffer(data.commercial_offer);
    setMessage(`Commercial Offer ${data.commercial_offer.offer_code} created.`);
    setCreating(false);
  }

  return (
    <section>
      <h2>Create Commercial Offer</h2>
      <p>
        Create a Commercial Offer for an existing Opportunity. Its lines, rates, terms and quotation are added on
        the offer's own page once it has been created.
      </p>

      <div className="page-actions">
        <a className="button-link-secondary" href="/commercial-offers">
          Back to Commercial Offers
        </a>
        <button type="button" onClick={loadOpportunities} disabled={loadingOpportunities}>
          {loadingOpportunities ? "Loading Opportunities..." : "Refresh Opportunities"}
        </button>
      </div>

      <p style={{ color: "#6b7280" }}>{createAccessMessage(pageAccess)}</p>

      {checkingExistingOffer ? (
        <p style={{ color: "#6b7280" }}>Checking whether this Opportunity already has an active Commercial Offer...</p>
      ) : null}

      {existingActionableOffer ? (
        <div className="content-card" style={{ borderColor: "#f59e0b", background: "#fffbeb", color: "#92400e" }}>
          <strong>Existing active/actionable Commercial Offer:</strong>{" "}
          <a
            href={`/commercial-offers/${existingActionableOffer.public_id}`}
            style={{ color: "#1d4ed8", fontWeight: 700, textDecoration: "underline" }}
          >
            Open {existingActionableOffer.offer_code}
          </a>{" "}
          ({formatStatusLabel(existingActionableOffer.offer_status_code)}). Open this offer and use Make a new version when its latest sent version needs a change.
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="form-card">
        <label className="field-stack">
          Opportunity <span style={{ color: "crimson" }}>*</span>
          <select
            value={form.opportunity_public_id}
            onChange={(event) => {
              setForm((current) => ({ ...current, opportunity_public_id: event.target.value }));
              setMessage("");
              setError("");
              setCreatedOffer(null);
              void checkExistingActionableOffer(event.target.value);
            }}
            required
            disabled={!pageAccess.canCreate}
          >
            <option value="">Select Opportunity</option>
            {opportunities.map((opportunity) => (
              <option key={opportunity.public_id} value={opportunity.public_id}>
                {opportunity.opportunity_name} - {opportunity.opportunity_status_code}
              </option>
            ))}
          </select>
        </label>

        <label className="field-stack">
          Offer title
          <input
            value={form.offer_title}
            onChange={(event) => setForm((current) => ({ ...current, offer_title: event.target.value }))}
            maxLength={255}
            disabled={!pageAccess.canCreate}
          />
        </label>

        <div className="form-grid">
          <label className="field-stack">
            Offer mode
            <select
              value={form.offer_mode}
              onChange={(event) => setForm((current) => ({ ...current, offer_mode: event.target.value }))}
              disabled={!pageAccess.canCreate}
            >
              {OFFER_MODE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          <label className="field-stack">
            Offer type
            <select
              value={form.offer_type}
              onChange={(event) => setForm((current) => ({ ...current, offer_type: event.target.value }))}
              disabled={!pageAccess.canCreate}
            >
              {OFFER_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          <label className="field-stack">
            Status
            <input value="DRAFT" readOnly disabled />
          </label>
        </div>

        <div className="form-grid-compact">
          <label className="field-stack">
            Offer value
            <input
              value={form.offer_value}
              onChange={(event) => setForm((current) => ({ ...current, offer_value: event.target.value }))}
              type="number"
              min="0"
              step="0.01"
              disabled={!pageAccess.canCreate}
            />
          </label>

          <label className="field-stack">
            Currency
            <CurrencySelect
              value={form.currency_code}
              onChange={(currencyCode) => setForm((current) => ({ ...current, currency_code: currencyCode }))}
              disabled={!pageAccess.canCreate}
            />
          </label>

          <label className="field-stack">
            Offer date
            <DateInput
              value={form.offer_date}
              onChange={(event) => setForm((current) => ({ ...current, offer_date: event.target.value }))}
              disabled={!pageAccess.canCreate}
            />
          </label>

          <label className="field-stack">
            Valid until
            <DateInput
              value={form.valid_until}
              onChange={(event) => setForm((current) => ({ ...current, valid_until: event.target.value }))}
              disabled={!pageAccess.canCreate}
            />
          </label>
        </div>

        <label className="field-stack">
          Remarks
          <textarea
            value={form.remarks}
            onChange={(event) => setForm((current) => ({ ...current, remarks: event.target.value }))}
            maxLength={4000}
            rows={4}
            disabled={!pageAccess.canCreate}
          />
        </label>

        <div>
          <button type="submit" disabled={creating || !pageAccess.canCreate}>
            {creating ? "Creating..." : existingActionableOffer ? "Open existing Commercial Offer" : "Create Commercial Offer"}
          </button>
          {message ? <p className="action-feedback" style={{ color: "#065f46" }}>{message}</p> : null}
          {error ? <p className="action-feedback" style={{ color: "crimson" }}>{error}</p> : null}
        </div>
      </form>

      {createdOffer ? (
        <div className="content-card" style={{ borderColor: "#bbf7d0", background: "#f0fdf4" }}>
          <h3 style={{ marginTop: 0 }}>Created Commercial Offer</h3>
          <p>
            <a href={`/commercial-offers/${createdOffer.public_id}`} style={{ color: "#1d4ed8", fontWeight: 700, textDecoration: "underline" }}>
              Open {createdOffer.offer_code}
            </a>
          </p>
          <p>
            <a href={`/opportunities/${createdOffer.opportunity_public_id}`} style={{ color: "#1d4ed8", fontWeight: 700, textDecoration: "underline" }}>
              Return to linked Opportunity
            </a>
          </p>
        </div>
      ) : null}
    </section>
  );
}
