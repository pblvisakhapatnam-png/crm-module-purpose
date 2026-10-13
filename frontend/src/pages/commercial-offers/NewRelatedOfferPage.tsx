import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { formatWorkOrderStatusLabel } from "../../components/PageLayout";
import DateInput from "../../components/DateInput";
import { amountProblem } from "../../components/amounts";
import { readErrorDetail } from "../../components/errorDetail";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

const TOKEN_KEY = "pbl_auth_token";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const RELATED_OFFER_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];

const PURPOSE_OPTIONS = [
  { value: "SUPPLEMENTARY", label: "Supplementary Offer" },
  { value: "CHANGE_QUOTATION", label: "Change Quotation" },
] as const;

type BaseCommercialOffer = {
  public_id: string;
  offer_code: string;
  offer_title?: string | null;
  offer_mode: string;
  offer_type: string;
  offer_status_code: string;
  offer_purpose: string;
  offer_value?: string | number | null;
  currency_code: string;
  offer_date?: string | null;
  valid_until?: string | null;
  opportunity_public_id: string;
  account_public_id?: string | null;
};

type LinkedWorkOrderSummary = {
  public_id: string;
  work_order_code: string;
  work_order_status_code: string;
};

type RelatedOfferCreatedResponse = {
  commercial_offer: {
    public_id: string;
    offer_code: string;
    offer_purpose: string;
  };
  event: { event_name?: string | null };
};

type TokenPayload = { role_codes?: unknown; exp?: unknown };
type AccessState = { status: "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token"; roleCodes: string[] };

function clearPrototypeSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
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
  const token = window.localStorage.getItem(TOKEN_KEY);
  if (!token) return null;
  const payload = decodeTokenPayload(token);
  const exp = typeof payload?.exp === "number" ? payload.exp : Number(payload?.exp ?? 0);
  if (!payload || !exp || exp * 1000 <= Date.now()) {
    clearPrototypeSession();
    return null;
  }
  return token;
}

function readAccess(): AccessState {
  const token = getToken();
  if (!token) return { status: "no_token", roleCodes: [] };
  const payload = decodeTokenPayload(token);
  if (!payload) return { status: "invalid_token", roleCodes: [] };
  const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp ?? 0);
  if (exp > 0 && exp * 1000 < Date.now()) return { status: "expired", roleCodes: [] };
  const roleCodes = Array.isArray(payload.role_codes) ? payload.role_codes.filter((role): role is string => typeof role === "string") : [];
  const allowed = roleCodes.some((role) => RELATED_OFFER_CREATE_ROLES.includes(role));
  return { status: allowed ? "allowed" : "denied", roleCodes };
}

function accessMessage(access: AccessState): string {
  if (access.status === "checking") return "Checking your session...";
  if (access.status === "allowed") return "You can create a Supplementary Offer or Change Quotation from this Base Offer.";
  if (access.status === "no_token") return "Sign in as Sales or Admin to create a related Commercial Offer.";
  if (access.status === "expired") return "Sign in again because your session has expired.";
  if (access.status === "invalid_token") return "Sign in again because the current session token is not readable.";
  return "Your role can view Commercial Offers but cannot create a related offer.";
}

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "-";
}

function formatStatusLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value.split("_").filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()).join(" ");
}

export default function NewRelatedCommercialOfferPage() {
  const params = useParams();
  const baseOfferId = typeof params?.commercialOfferId === "string" ? params.commercialOfferId : "";

  const [access, setAccess] = useState<AccessState>({ status: "checking", roleCodes: [] });
  const [baseOffer, setBaseOffer] = useState<BaseCommercialOffer | null>(null);
  const [linkedWorkOrders, setLinkedWorkOrders] = useState<LinkedWorkOrderSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [created, setCreated] = useState<RelatedOfferCreatedResponse | null>(null);

  const [offerPurpose, setOfferPurpose] = useState<string>("SUPPLEMENTARY");
  const [relatedWorkOrderPublicId, setRelatedWorkOrderPublicId] = useState("");
  const [customerRequestReference, setCustomerRequestReference] = useState("");
  const [customerRequestReceivedDate, setCustomerRequestReceivedDate] = useState("");
  const [customerRequestSummary, setCustomerRequestSummary] = useState("");
  const [offerTitle, setOfferTitle] = useState("");
  const [offerValue, setOfferValue] = useState("");
  const [offerDate, setOfferDate] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const [remarks, setRemarks] = useState("");

  async function loadBaseOffer() {
    const currentAccess = readAccess();
    setAccess(currentAccess);
    setError("");
    setMessage("");
    setCreated(null);

    if (!baseOfferId) {
      setError("Open this page from an Accepted Base Commercial Offer so the Base Offer can be identified.");
      return;
    }

    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);
    try {
      const offerResponse = await fetch(`/api/commercial-offers/${encodeURIComponent(baseOfferId)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!offerResponse.ok) {
        if (offerResponse.status === 401) clearPrototypeSession();
        setError("Could not load the Base Commercial Offer. Please refresh and try again.");
        setLoading(false);
        return;
      }
      const loadedOffer = (await offerResponse.json()) as BaseCommercialOffer;
      setBaseOffer(loadedOffer);
      setOfferTitle("");

      const linkedResponse = await fetch(
        `/api/work-orders?commercial_offer_public_id=${encodeURIComponent(baseOfferId)}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (linkedResponse.ok) {
        setLinkedWorkOrders((await linkedResponse.json()) as LinkedWorkOrderSummary[]);
      } else {
        setLinkedWorkOrders([]);
      }

      setMessage("Base Commercial Offer loaded.");
    } catch {
      setError("Network error while loading the Base Commercial Offer.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const params2 = new URLSearchParams(window.location.search);
    const requestedPurpose = params2.get("purpose");
    if (requestedPurpose === "SUPPLEMENTARY" || requestedPurpose === "CHANGE_QUOTATION") {
      setOfferPurpose(requestedPurpose);
    }
    void loadBaseOffer();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseOfferId]);

  useEffect(() => {
    if (offerPurpose === "CHANGE_QUOTATION" && linkedWorkOrders.length === 1 && !relatedWorkOrderPublicId) {
      setRelatedWorkOrderPublicId(linkedWorkOrders[0].public_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offerPurpose, linkedWorkOrders]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setCreated(null);

    const currentAccess = readAccess();
    setAccess(currentAccess);
    if (currentAccess.status !== "allowed") {
      setError(accessMessage(currentAccess));
      return;
    }

    if (!baseOffer) {
      setError("Load an Accepted Base Commercial Offer before creating a related offer.");
      return;
    }

    if (!customerRequestSummary.trim()) {
      setError("Request / change summary is required.");
      return;
    }

    if (offerPurpose === "CHANGE_QUOTATION" && !relatedWorkOrderPublicId) {
      setError("A Change Quotation must be linked to an existing Work Order.");
      return;
    }

    // The server's limit for an offer value: 0 or more, 16 whole digits, 2 decimals (TB-1 finding TB1-801).
    const offerValueProblem = amountProblem("Offer value", offerValue, 16, true);
    if (offerValueProblem) {
      setError(offerValueProblem);
      return;
    }

    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`/api/commercial-offers/${encodeURIComponent(baseOffer.public_id)}/related-offers`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          offer_purpose: offerPurpose,
          related_work_order_public_id: relatedWorkOrderPublicId || null,
          customer_request_reference: customerRequestReference.trim() || null,
          customer_request_received_date: customerRequestReceivedDate || null,
          customer_request_summary: customerRequestSummary.trim(),
          offer_title: offerTitle.trim() || null,
          offer_value: offerValue.trim() || null,
          offer_date: offerDate || null,
          valid_until: validUntil || null,
          remarks: remarks.trim() || null,
        }),
      });
      if (!response.ok) {
        if (response.status === 401) clearPrototypeSession();
        setError(await readErrorDetail(response, "Could not create the related Commercial Offer. Please check the form and try again."));
        setSaving(false);
        return;
      }
      const data = (await response.json()) as RelatedOfferCreatedResponse;
      setCreated(data);
      setMessage(`${data.commercial_offer.offer_code} created successfully.`);
    } catch {
      setError("Network error while creating the related Commercial Offer.");
    } finally {
      setSaving(false);
    }
  }

  const purposeLabel = PURPOSE_OPTIONS.find((option) => option.value === offerPurpose)?.label || offerPurpose;

  return (
    <section>
      <h2>Create {purposeLabel}</h2>
      <p>
        A Supplementary Offer or Change Quotation is a separate Commercial Offer series linked to its Base Offer, not
        a revision of it. It has its own independent lines, pricing, terms and lifecycle. Creating it does not copy
        lines, prices or terms from the Base Offer, and does not create or amend any Work Order automatically. A
        change to a Work Order is recorded separately as a Work Order Amendment.
      </p>
      <p style={{ color: "#6b7280" }}>{accessMessage(access)}</p>

      <div className="page-actions">
        {baseOffer ? (
          <a className="button-link-secondary" href={`/commercial-offers/${baseOffer.public_id}`}>
            Back to Base Commercial Offer
          </a>
        ) : null}
        <button type="button" onClick={() => void loadBaseOffer()} disabled={loading}>
          {loading ? "Loading..." : "Reload Base Offer"}
        </button>
      </div>

      {message ? <p style={{ color: "#065f46" }}>{message}</p> : null}
      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}

      {baseOffer ? (
        <div className="content-card" style={{ background: "#f9fafb", maxWidth: "960px" }}>
          <h3 style={{ marginTop: 0 }}>Base Commercial Offer context (locked)</h3>
          <p><strong>{baseOffer.offer_code}</strong> - {displayValue(baseOffer.offer_title)}</p>
          <p>Status: <strong>{formatStatusLabel(baseOffer.offer_status_code)}</strong></p>
          <p>Opportunity: <a href={`/opportunities/${baseOffer.opportunity_public_id}`}>{baseOffer.opportunity_public_id}</a></p>
          {baseOffer.account_public_id ? (
            <p>Account: <a href={`/accounts/${baseOffer.account_public_id}`}>{baseOffer.account_public_id}</a></p>
          ) : (
            <p style={{ color: "#92400e" }}>This Base Offer is not linked to an Account.</p>
          )}
          {baseOffer.offer_status_code !== "ACCEPTED" ? (
            <p style={{ color: "crimson" }}>
              The Base Offer must currently be Accepted / awarded before a related offer can be created.
            </p>
          ) : null}
        </div>
      ) : null}

      {baseOffer ? (
        <form onSubmit={handleCreate} className="form-card" style={{ maxWidth: "960px", borderColor: "#bfdbfe", background: "#eff6ff" }}>
          <h3 style={{ marginTop: 0 }}>Related offer details</h3>
          <div className="form-grid">
            <label className="field-stack">
              Purpose
              <select value={offerPurpose} onChange={(event) => setOfferPurpose(event.target.value)}>
                {PURPOSE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-stack">
              Linked Work Order {offerPurpose === "CHANGE_QUOTATION" ? "(required)" : "(optional)"}
              <select value={relatedWorkOrderPublicId} onChange={(event) => setRelatedWorkOrderPublicId(event.target.value)}>
                <option value="">-- none --</option>
                {linkedWorkOrders.map((workOrder) => (
                  <option key={workOrder.public_id} value={workOrder.public_id}>
                    {workOrder.work_order_code} ({formatWorkOrderStatusLabel(workOrder.work_order_status_code)})
                  </option>
                ))}
              </select>
            </label>
          </div>
          {offerPurpose === "CHANGE_QUOTATION" && linkedWorkOrders.length === 0 ? (
            <p style={{ color: "crimson" }}>
              No Work Order is linked to this Base Offer yet. A Change Quotation requires an existing Work Order.
            </p>
          ) : null}

          <div className="form-grid">
            <label className="field-stack">
              Customer request reference
              <input value={customerRequestReference} onChange={(event) => setCustomerRequestReference(event.target.value)} maxLength={255} />
            </label>
            <label className="field-stack">
              Customer request received date
              <DateInput value={customerRequestReceivedDate} onChange={(event) => setCustomerRequestReceivedDate(event.target.value)} />
            </label>
          </div>
          <label className="field-stack">
            Request / change summary (required)
            <textarea
              value={customerRequestSummary}
              onChange={(event) => setCustomerRequestSummary(event.target.value)}
              rows={3}
              maxLength={2000}
              required
            />
          </label>

          <div className="form-grid">
            <label className="field-stack">
              Offer title (optional)
              <input value={offerTitle} onChange={(event) => setOfferTitle(event.target.value)} maxLength={255} />
            </label>
            <label className="field-stack">
              Offer value (optional)
              <input value={offerValue} onChange={(event) => setOfferValue(event.target.value)} inputMode="decimal" />
            </label>
            <label className="field-stack">
              Offer date
              <DateInput value={offerDate} onChange={(event) => setOfferDate(event.target.value)} />
            </label>
            <label className="field-stack">
              Valid until
              <DateInput value={validUntil} onChange={(event) => setValidUntil(event.target.value)} />
            </label>
          </div>
          <label className="field-stack">
            Remarks
            <textarea value={remarks} onChange={(event) => setRemarks(event.target.value)} rows={3} maxLength={4000} />
          </label>

          <button
            type="submit"
            disabled={
              saving ||
              access.status !== "allowed" ||
              baseOffer.offer_status_code !== "ACCEPTED" ||
              !customerRequestSummary.trim() ||
              (offerPurpose === "CHANGE_QUOTATION" && !relatedWorkOrderPublicId)
            }
          >
            {saving ? "Creating..." : `Create ${purposeLabel}`}
          </button>
        </form>
      ) : null}

      {created ? (
        <div className="content-card" style={{ borderColor: "#bbf7d0", background: "#f0fdf4", maxWidth: "960px" }}>
          <h3 style={{ marginTop: 0 }}>{purposeLabel} created</h3>
          <p>
            <a href={`/commercial-offers/${created.commercial_offer.public_id}`} style={{ color: "#1d4ed8", fontWeight: 700 }}>
              Open {created.commercial_offer.offer_code}
            </a>
          </p>
        </div>
      ) : null}
    </section>
  );
}
