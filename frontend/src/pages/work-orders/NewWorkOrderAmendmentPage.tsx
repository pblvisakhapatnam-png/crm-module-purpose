import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { formatWorkOrderStatusLabel } from "../../components/PageLayout";
import DateInput from "../../components/DateInput";
import { readErrorDetail } from "../../components/errorDetail";
import { readSafeReturnTarget, type ReturnTarget } from "../../components/returnTarget";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

const TOKEN_KEY = "pbl_auth_token";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const WORK_ORDER_AMENDMENT_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER", "OPERATIONS_USER"];

const AMENDMENT_TYPE_OPTIONS = [
  { value: "ADMINISTRATIVE", label: "Administrative (no commercial basis required)" },
  { value: "COMMERCIAL", label: "Commercial (requires an accepted commercial basis to validate)" },
  { value: "MIXED", label: "Mixed - Administrative + Commercial (requires an accepted commercial basis to validate)" },
] as const;

type WorkOrder = {
  public_id: string;
  work_order_code: string;
  work_order_title?: string | null;
  work_order_status_code: string;
  commercial_offer_public_id: string;
  commercial_offer_code?: string | null;
  opportunity_public_id: string;
  account_public_id?: string | null;
};

type RelatedOfferOption = {
  public_id: string;
  offer_code: string;
  offer_purpose: string;
  offer_status_code: string;
};

type AmendmentCreatedResponse = {
  amendment: {
    public_id: string;
    work_order_public_id: string;
    amendment_sequence_no: number;
    amendment_type_code: string;
    amendment_status_code: string;
  };
  event: { event_name?: string | null };
};

type TokenPayload = { role_codes?: unknown; exp?: unknown };
type AccessState = { status: "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token"; roleCodes: string[] };

function hrefWithReturnTarget(href: string, returnTo: string, returnLabel: string): string {
  const separator = href.includes("?") ? "&" : "?";
  return `${href}${separator}returnTo=${encodeURIComponent(returnTo)}&returnLabel=${encodeURIComponent(returnLabel)}`;
}

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
  const allowed = roleCodes.some((role) => WORK_ORDER_AMENDMENT_CREATE_ROLES.includes(role));
  return { status: allowed ? "allowed" : "denied", roleCodes };
}

function accessMessage(access: AccessState): string {
  if (access.status === "checking") return "Checking your session...";
  if (access.status === "allowed") return "You can record a Work Order Amendment intake for this Work Order.";
  if (access.status === "no_token") return "Sign in as Sales, Operations or Admin to record a Work Order Amendment.";
  if (access.status === "expired") return "Sign in again because your session has expired.";
  if (access.status === "invalid_token") return "Sign in again because the current session token is not readable.";
  return "Your role can view Work Order Amendments but cannot record one.";
}

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "-";
}

function formatStatusLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value.split("_").filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()).join(" ");
}

const COMMERCIAL_OFFER_PURPOSE_LABELS: Record<string, string> = {
  SUPPLEMENTARY: "Supplementary Offer",
  CHANGE_QUOTATION: "Change Quotation",
};

function offerPurposeLabel(offerPurpose: string): string {
  return COMMERCIAL_OFFER_PURPOSE_LABELS[offerPurpose] || offerPurpose;
}

export default function NewWorkOrderAmendmentPage() {
  const params = useParams();
  const workOrderId = typeof params?.workOrderId === "string" ? params.workOrderId : "";

  const [access, setAccess] = useState<AccessState>({ status: "checking", roleCodes: [] });
  const [workOrder, setWorkOrder] = useState<WorkOrder | null>(null);
  const [relatedOffers, setRelatedOffers] = useState<RelatedOfferOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [created, setCreated] = useState<AmendmentCreatedResponse | null>(null);

  const [amendmentTypeCode, setAmendmentTypeCode] = useState<string>("ADMINISTRATIVE");
  const [customerAmendmentReference, setCustomerAmendmentReference] = useState("");
  const [customerAmendmentDate, setCustomerAmendmentDate] = useState("");
  const [receivedDate, setReceivedDate] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [amendmentReason, setAmendmentReason] = useState("");
  const [administrativeChangeSummary, setAdministrativeChangeSummary] = useState("");
  const [commercialChangeSummary, setCommercialChangeSummary] = useState("");
  const [relatedCommercialOfferPublicId, setRelatedCommercialOfferPublicId] = useState("");
  const [customerDocumentReference, setCustomerDocumentReference] = useState("");
  const [remarks, setRemarks] = useState("");
  const [returnTarget, setReturnTarget] = useState<ReturnTarget>({
    href: workOrderId ? `/work-orders/${workOrderId}` : "/work-orders",
    label: "Back to Work Order",
  });

  async function loadWorkOrderContext() {
    const currentAccess = readAccess();
    setAccess(currentAccess);
    setError("");
    setMessage("");
    setCreated(null);

    if (!workOrderId) {
      setError("Open this page from a Work Order so the Work Order can be identified.");
      return;
    }

    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);
    try {
      const workOrderResponse = await fetch(`/api/work-orders/${encodeURIComponent(workOrderId)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!workOrderResponse.ok) {
        if (workOrderResponse.status === 401) clearPrototypeSession();
        setError("Could not load the Work Order. Please refresh and try again.");
        setLoading(false);
        return;
      }
      const loadedWorkOrder = (await workOrderResponse.json()) as WorkOrder;
      setWorkOrder(loadedWorkOrder);

      const relatedResponse = await fetch(`/api/work-orders/${encodeURIComponent(workOrderId)}/related-offers`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (relatedResponse.ok) {
        setRelatedOffers((await relatedResponse.json()) as RelatedOfferOption[]);
      } else {
        setRelatedOffers([]);
      }

      setMessage("Work Order context loaded.");
    } catch {
      setError("Network error while loading the Work Order.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const preselectedOfferId = searchParams.get("relatedOfferId");
    if (preselectedOfferId) {
      setRelatedCommercialOfferPublicId(preselectedOfferId);
      setAmendmentTypeCode("COMMERCIAL");
    }
    setReturnTarget(readSafeReturnTarget(`/work-orders/${workOrderId}`, "Back to Work Order"));
    void loadWorkOrderContext();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workOrderId]);

  const commercialBasisRequired = amendmentTypeCode !== "ADMINISTRATIVE";

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

    if (!workOrder) {
      setError("Load the Work Order before recording an amendment.");
      return;
    }

    if (!receivedDate) {
      setError("Received date is required.");
      return;
    }

    if (!amendmentReason.trim()) {
      setError("Amendment reason / summary is required.");
      return;
    }

    if (commercialBasisRequired && !commercialChangeSummary.trim()) {
      setError("Commercial change summary is required for Commercial and Mixed amendments.");
      return;
    }

    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`/api/work-orders/${encodeURIComponent(workOrder.public_id)}/amendments`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          amendment_type_code: amendmentTypeCode,
          customer_amendment_reference: customerAmendmentReference.trim() || null,
          customer_amendment_date: customerAmendmentDate || null,
          received_date: receivedDate,
          effective_date: effectiveDate || null,
          amendment_reason: amendmentReason.trim(),
          administrative_change_summary: administrativeChangeSummary.trim() || null,
          commercial_change_summary: commercialChangeSummary.trim() || null,
          related_commercial_offer_public_id: relatedCommercialOfferPublicId || null,
          customer_document_reference: customerDocumentReference.trim() || null,
          remarks: remarks.trim() || null,
        }),
      });
      if (!response.ok) {
        if (response.status === 401) clearPrototypeSession();
        setError(await readErrorDetail(response, "Could not record the Work Order Amendment. Please check the form and try again."));
        setSaving(false);
        return;
      }
      const data = (await response.json()) as AmendmentCreatedResponse;
      setCreated(data);
      setMessage(`Amendment #${data.amendment.amendment_sequence_no} recorded successfully.`);
    } catch {
      setError("Network error while recording the Work Order Amendment.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section>
      <h2>Record Work Order Amendment</h2>
      <p>
        This records a customer-requested administrative or commercial change as an intake/review record only.
        Recording an amendment does <strong>not</strong> change this Work Order or any of its lines. Commercial and
        Mixed amendments require an accepted Supplementary Offer or Change Quotation as their commercial basis
        before they can be validated. Applying an amendment to the Work Order is not built yet.
      </p>
      <p style={{ color: "#6b7280" }}>{accessMessage(access)}</p>

      <div className="page-actions">
        <a className="button-link-secondary" href={returnTarget.href}>
          {returnTarget.label}
        </a>
        <button type="button" onClick={() => void loadWorkOrderContext()} disabled={loading}>
          {loading ? "Loading..." : "Reload Work Order"}
        </button>
      </div>

      {message ? <p style={{ color: "#065f46" }}>{message}</p> : null}
      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}

      {workOrder ? (
        <div className="content-card" style={{ background: "#f9fafb", maxWidth: "960px" }}>
          <h3 style={{ marginTop: 0 }}>Work Order context (locked)</h3>
          <p><strong>{workOrder.work_order_code}</strong> - {displayValue(workOrder.work_order_title)}</p>
          <p>Status: <strong>{formatWorkOrderStatusLabel(workOrder.work_order_status_code)}</strong></p>
          <p>Base Commercial Offer: <a href={`/commercial-offers/${workOrder.commercial_offer_public_id}`}>{displayValue(workOrder.commercial_offer_code)}</a></p>
          <p>Opportunity: <a href={`/opportunities/${workOrder.opportunity_public_id}`}>{workOrder.opportunity_public_id}</a></p>
          {workOrder.account_public_id ? (
            <p>Account: <a href={`/accounts/${workOrder.account_public_id}`}>{workOrder.account_public_id}</a></p>
          ) : (
            <p style={{ color: "#92400e" }}>This Work Order is not linked to an Account.</p>
          )}
        </div>
      ) : null}

      {workOrder ? (
        <form onSubmit={handleCreate} className="form-card" style={{ maxWidth: "960px", borderColor: "#bfdbfe", background: "#eff6ff" }}>
          <h3 style={{ marginTop: 0 }}>Amendment intake details</h3>
          <div className="form-grid">
            <label className="field-stack">
              Amendment type
              <select value={amendmentTypeCode} onChange={(event) => setAmendmentTypeCode(event.target.value)}>
                {AMENDMENT_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-stack">
              Commercial basis (Supplementary Offer / Change Quotation) {commercialBasisRequired ? "(required to validate)" : "(optional)"}
              <select value={relatedCommercialOfferPublicId} onChange={(event) => setRelatedCommercialOfferPublicId(event.target.value)}>
                <option value="">-- none --</option>
                {relatedOffers.map((offer) => (
                  <option key={offer.public_id} value={offer.public_id}>
                    {offer.offer_code} - {offerPurposeLabel(offer.offer_purpose)} ({formatStatusLabel(offer.offer_status_code)})
                  </option>
                ))}
              </select>
            </label>
          </div>
          {commercialBasisRequired && relatedOffers.length === 0 ? (
            <p style={{ color: "#92400e" }}>
              No Supplementary Offer or Change Quotation is linked to this Work Order yet. You can still record this
              amendment now and link the commercial basis later while it remains editable (Received or Under
              Review), but it cannot be validated until an accepted commercial basis is linked.
            </p>
          ) : null}

          <div className="form-grid">
            <label className="field-stack">
              Customer amendment reference
              <input value={customerAmendmentReference} onChange={(event) => setCustomerAmendmentReference(event.target.value)} maxLength={255} />
            </label>
            <label className="field-stack">
              Customer amendment date
              <DateInput value={customerAmendmentDate} onChange={(event) => setCustomerAmendmentDate(event.target.value)} />
            </label>
            <label className="field-stack">
              Received date (required)
              <DateInput value={receivedDate} onChange={(event) => setReceivedDate(event.target.value)} required />
            </label>
            <label className="field-stack">
              Effective date (optional)
              <DateInput value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} />
            </label>
          </div>

          <label className="field-stack">
            Amendment reason / summary (required)
            <textarea
              value={amendmentReason}
              onChange={(event) => setAmendmentReason(event.target.value)}
              rows={3}
              maxLength={2000}
              required
            />
          </label>

          <label className="field-stack">
            Administrative change summary {amendmentTypeCode === "ADMINISTRATIVE" ? "" : "(optional)"}
            <textarea value={administrativeChangeSummary} onChange={(event) => setAdministrativeChangeSummary(event.target.value)} rows={2} maxLength={2000} />
          </label>

          <label className="field-stack">
            Commercial change summary {commercialBasisRequired ? "(required)" : "(not applicable to Administrative amendments)"}
            <textarea
              value={commercialChangeSummary}
              onChange={(event) => setCommercialChangeSummary(event.target.value)}
              rows={2}
              maxLength={2000}
              disabled={!commercialBasisRequired}
            />
          </label>

          <label className="field-stack">
            Customer document reference (optional)
            <input value={customerDocumentReference} onChange={(event) => setCustomerDocumentReference(event.target.value)} maxLength={255} />
          </label>

          <label className="field-stack">
            Remarks
            <textarea value={remarks} onChange={(event) => setRemarks(event.target.value)} rows={3} maxLength={4000} />
          </label>

          <button
            type="submit"
            disabled={
              saving ||
              access.status !== "allowed" ||
              !receivedDate ||
              !amendmentReason.trim() ||
              (commercialBasisRequired && !commercialChangeSummary.trim())
            }
          >
            {saving ? "Recording..." : "Record amendment"}
          </button>
        </form>
      ) : null}

      {created ? (
        <div className="content-card" style={{ borderColor: "#bbf7d0", background: "#f0fdf4", maxWidth: "960px" }}>
          <h3 style={{ marginTop: 0 }}>Amendment recorded</h3>
          <p>
            <a
              href={hrefWithReturnTarget(
                `/work-orders/${created.amendment.work_order_public_id}/amendments/${created.amendment.public_id}`,
                returnTarget.href,
                returnTarget.label,
              )}
              style={{ color: "#1d4ed8", fontWeight: 700 }}
            >
              Open Amendment #{created.amendment.amendment_sequence_no}
            </a>
          </p>
        </div>
      ) : null}
    </section>
  );
}
