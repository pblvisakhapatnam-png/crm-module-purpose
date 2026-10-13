import { FormEvent, useEffect, useMemo, useState } from "react";

import { formatWorkOrderStatusLabel } from "../../components/PageLayout";
import DateInput from "../../components/DateInput";
import { readErrorDetail } from "../../components/errorDetail";
import { offerVersionLabel } from "../../components/offerVersion";
import { SIGN_IN_FIRST } from "../../components/signInMessages";
import {
  describeHoldings,
  formatHundredths,
  hundredthsLeft,
  LineHandoff,
  quantityProblem,
  startingChoice,
} from "./handoffQuantities";

const TOKEN_KEY = "pbl_auth_token";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const WORK_ORDER_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER", "OPERATIONS_USER"];

type CommercialOffer = {
  public_id: string;
  offer_code: string;
  version_number?: number | null;
  opportunity_public_id: string;
  account_public_id?: string | null;
  offer_title?: string | null;
  offer_mode: string;
  offer_type: string;
  offer_date?: string | null;
  offer_status_code: string;
  offer_value?: string | number | null;
  currency_code: string;
};

type LinkedWorkOrderSummary = {
  public_id: string;
  work_order_code: string;
  work_order_status_code: string;
};

// The offer's own view of whether a Work Order may be created, and why not (Slice 6M; CS-04 part 1 made it say what
// the server refuses - a Change Quotation, a latest customer response that is not the acceptance, nothing left - and
// gave it every Work Order of the offer and what each line has left, counted in one statement on the server).
type HandoffGuidance = {
  work_order_handoff_available: boolean;
  work_order_handoff_blocked_reasons: string[];
  linked_work_orders: LinkedWorkOrderSummary[];
  line_handoff: LineHandoff[];
};

type OfferLine = {
  public_id: string;
  line_number: number;
  line_status_code: string;
  scope_description: string;
  equipment_service_category?: string | null;
  quantity: string | number;
  uom: string;
  rate_amount?: string | number | null;
  currency_code: string;
  line_amount?: string | number | null;
};

type WorkOrderCreatedResponse = {
  work_order: {
    public_id: string;
    work_order_code: string;
    work_order_status_code: string;
  };
  lines: { public_id: string }[];
  events: { event_name?: string | null }[];
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
  const allowed = roleCodes.some((role) => WORK_ORDER_CREATE_ROLES.includes(role));
  return { status: allowed ? "allowed" : "denied", roleCodes };
}

function accessMessage(access: AccessState): string {
  if (access.status === "checking") return "Checking your session...";
  if (access.status === "allowed") return "You can create a Work Order from an Accepted Commercial Offer.";
  if (access.status === "no_token") return "Sign in as Sales, Operations or Admin to create a Work Order.";
  if (access.status === "expired") return "Sign in again because your session has expired.";
  if (access.status === "invalid_token") return "Sign in again because the current session token is not readable.";
  return "Your role can view Work Orders but cannot create one.";
}

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "-";
}

function formatMoney(value: string | number | null | undefined, currencyCode = "INR"): string {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return `${currencyCode} ${numeric.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function formatStatusLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value.split("_").filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()).join(" ");
}

function formatDateOnly(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "2-digit" });
}

function hasAccountTraceability(commercialOffer: CommercialOffer | null): boolean {
  const accountPublicId = commercialOffer?.account_public_id;
  return Boolean(accountPublicId && accountPublicId.trim().length > 0);
}

function accountTraceabilityBlockMessage(): string {
  return "A Work Order cannot be created until this Opportunity is linked to an Account.";
}

function hrefWithReturnTarget(href: string, returnTo: string, returnLabel: string): string {
  const separator = href.includes("?") ? "&" : "?";
  return `${href}${separator}returnTo=${encodeURIComponent(returnTo)}&returnLabel=${encodeURIComponent(returnLabel)}`;
}

export default function NewWorkOrderFromCommercialOfferPage() {
  const [commercialOfferId, setCommercialOfferId] = useState("");
  const [access, setAccess] = useState<AccessState>({ status: "checking", roleCodes: [] });
  const [commercialOffer, setCommercialOffer] = useState<CommercialOffer | null>(null);
  const [offerLines, setOfferLines] = useState<OfferLine[]>([]);
  const [selectedLineIds, setSelectedLineIds] = useState<string[]>([]);
  const [customerWoReference, setCustomerWoReference] = useState("");
  const [receivedDate, setReceivedDate] = useState("");
  const [remarks, setRemarks] = useState("");
  const [createdWorkOrder, setCreatedWorkOrder] = useState<WorkOrderCreatedResponse | null>(null);
  const [existingLinkedWorkOrders, setExistingLinkedWorkOrders] = useState<LinkedWorkOrderSummary[]>([]);
  const [lineHandoffById, setLineHandoffById] = useState<Record<string, LineHandoff>>({});
  const [lineQuantities, setLineQuantities] = useState<Record<string, string>>({});
  const [guidance, setGuidance] = useState<HandoffGuidance | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [createError, setCreateError] = useState("");

  const activeLines = useMemo(() => offerLines.filter((line) => line.line_status_code === "ACTIVE"), [offerLines]);

  async function loadSourceOffer(explicitCommercialOfferId?: string, keepCreatedResult = false) {
    const sourceCommercialOfferId = explicitCommercialOfferId ?? commercialOfferId;
    const currentAccess = readAccess();
    setAccess(currentAccess);
    setError("");
    setCreateError("");
    if (!keepCreatedResult) {
      setMessage("");
      setCreatedWorkOrder(null);
    }

    if (!sourceCommercialOfferId) {
      setError("Open this page from an Accepted Commercial Offer so the source offer can be identified.");
      return;
    }

    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);
    try {
      const offerResponse = await fetch(`/api/commercial-offers/${encodeURIComponent(sourceCommercialOfferId)}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!offerResponse.ok) {
        if (offerResponse.status === 401) clearPrototypeSession();
        setError("Could not load the selected Commercial Offer. Please refresh and try again.");
        setLoading(false);
        return;
      }
      const loadedOffer = (await offerResponse.json()) as CommercialOffer;
      setCommercialOffer(loadedOffer);

      const linesResponse = await fetch(`/api/commercial-offers/${encodeURIComponent(sourceCommercialOfferId)}/lines`, { headers: { Authorization: `Bearer ${token}` } });
      if (!linesResponse.ok) {
        setError("Commercial Offer loaded, but its lines could not be loaded. Please refresh and try again.");
        setLoading(false);
        return;
      }
      const loadedLines = (await linesResponse.json()) as OfferLine[];
      setOfferLines(loadedLines);

      // What each line has left and every Work Order of the offer, from the server's one count (review round 2).
      const guidanceResponse = await fetch(`/api/commercial-offers/${encodeURIComponent(sourceCommercialOfferId)}/lifecycle-guidance`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!guidanceResponse.ok) {
        setGuidance(null);
        setError("Could not load what is already on Work Orders for this offer. Please refresh and try again.");
        setLoading(false);
        return;
      }
      const loadedGuidance = (await guidanceResponse.json()) as HandoffGuidance;
      setGuidance(loadedGuidance);
      setExistingLinkedWorkOrders(loadedGuidance.linked_work_orders);
      setLineHandoffById(Object.fromEntries(loadedGuidance.line_handoff.map((entry) => [entry.offer_line_public_id, entry])));
      const choice = startingChoice(
        loadedLines.filter((line) => line.line_status_code === "ACTIVE").map((line) => line.public_id),
        loadedGuidance.line_handoff,
      );
      setSelectedLineIds(choice.selected);
      setLineQuantities(choice.quantities);

      if (!keepCreatedResult) setMessage("Commercial Offer and active lines loaded.");
    } catch {
      setError("Network error while loading the Commercial Offer.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sourceId = params.get("commercialOfferId") || "";
    setCommercialOfferId(sourceId);
    void loadSourceOffer(sourceId);
  }, []);

  function toggleLine(publicId: string) {
    setSelectedLineIds((current) => current.includes(publicId) ? current.filter((item) => item !== publicId) : [...current, publicId]);
  }

  function firstQuantityProblem(): string {
    for (const line of activeLines) {
      if (!selectedLineIds.includes(line.public_id)) continue;
      const problem = quantityProblem(line.line_number, lineQuantities[line.public_id] ?? "", lineHandoffById[line.public_id]);
      if (problem) return problem;
    }
    return "";
  }

  async function handleCreateWorkOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateError("");
    setMessage("");
    setCreatedWorkOrder(null);

    const currentAccess = readAccess();
    setAccess(currentAccess);
    if (currentAccess.status !== "allowed") {
      setCreateError(accessMessage(currentAccess));
      return;
    }

    if (!commercialOffer) {
      setCreateError("Load an Accepted Commercial Offer before creating the Work Order.");
      return;
    }

    if (commercialOffer.offer_status_code !== "ACCEPTED") {
      setCreateError("A Work Order can be created only from an Accepted Commercial Offer.");
      return;
    }

    if (!hasAccountTraceability(commercialOffer)) {
      setCreateError(accountTraceabilityBlockMessage());
      return;
    }

    // One customer order makes one Work Order (CS-04 part 1): its reference is required, and the server refuses one
    // already on a Work Order of this offer.
    if (!customerWoReference.trim()) {
      setCreateError("Enter the customer's Work Order reference - their order number, or the Letter of Intent's.");
      return;
    }

    if (selectedLineIds.length === 0) {
      setCreateError("Select at least one active Commercial Offer line for the Work Order.");
      return;
    }

    const problem = firstQuantityProblem();
    if (problem) {
      setCreateError(problem);
      return;
    }

    const token = getToken();
    if (!token) {
      setCreateError(SIGN_IN_FIRST);
      return;
    }

    setSaving(true);
    try {
      const response = await fetch("/api/work-orders/from-commercial-offer", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          commercial_offer_public_id: commercialOffer.public_id,
          selected_offer_line_public_ids: selectedLineIds,
          selected_offer_line_quantities: selectedLineIds.map((lineId) => ({
            offer_line_public_id: lineId,
            quantity: lineQuantities[lineId],
          })),
          customer_wo_reference: customerWoReference.trim() || null,
          received_date: receivedDate || null,
          remarks: remarks.trim() || null,
        }),
      });
      if (!response.ok) {
        if (response.status === 401) clearPrototypeSession();
        setCreateError(await readErrorDetail(response, "Could not create the Work Order. Please check the form and try again."));
        setSaving(false);
        return;
      }
      const data = (await response.json()) as WorkOrderCreatedResponse;
      setCreatedWorkOrder(data);
      setMessage("Work Order created.");
      // What is left of each line changed: read the offer's Work Orders again, keeping this result on screen.
      await loadSourceOffer(commercialOffer.public_id, true);
    } catch {
      setCreateError("Network error while creating the Work Order.");
    } finally {
      setSaving(false);
    }
  }

  const accountTraceabilityAvailable = hasAccountTraceability(commercialOffer);

  return (
    <section>
      <h2>Create a Work Order from an accepted Commercial Offer</h2>
      <p>
        This creates the Work Order from the accepted offer. Customer Master approval, release to Ops, equipment
        and crew allocation, log sheets, billing and execution are not built yet.
      </p>
      <p style={{ color: "#6b7280" }}>{accessMessage(access)}</p>

      <div className="page-actions">
        <a className="button-link-secondary" href="/work-orders">Back to Work Orders</a>
        {commercialOffer ? <a className="button-link-secondary" href={`/commercial-offers/${commercialOffer.public_id}`}>Back to Commercial Offer</a> : null}
        <button type="button" onClick={() => void loadSourceOffer()} disabled={loading}>{loading ? "Loading..." : "Reload source offer"}</button>
      </div>

      {message ? <p style={{ color: "#065f46" }}>{message}</p> : null}
      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}

      {commercialOffer ? (
        <div className="content-card" style={{ background: "#f9fafb", maxWidth: "960px" }}>
          <h3 style={{ marginTop: 0 }}>Source Commercial Offer</h3>
          <p><strong>{offerVersionLabel(commercialOffer.offer_code, commercialOffer.version_number)}</strong> - {displayValue(commercialOffer.offer_title)}</p>
          <p>Status: <strong>{formatStatusLabel(commercialOffer.offer_status_code)}</strong></p>
          <p>Offer mode / type: {formatStatusLabel(commercialOffer.offer_mode)} / {formatStatusLabel(commercialOffer.offer_type)}</p>
          <p>Offer date: {formatDateOnly(commercialOffer.offer_date)}</p>
          <p>Value: {formatMoney(commercialOffer.offer_value, commercialOffer.currency_code)}</p>
          <p>Opportunity: <a href={`/opportunities/${commercialOffer.opportunity_public_id}`}>{commercialOffer.opportunity_public_id}</a></p>
          {commercialOffer.account_public_id ? (
            <p>Account: <a href={`/accounts/${commercialOffer.account_public_id}`}>{commercialOffer.account_public_id}</a></p>
          ) : (
            <div style={{ marginTop: "12px", padding: "12px", border: "1px solid #f59e0b", background: "#fffbeb", color: "#92400e" }}>
              <p style={{ marginTop: 0 }}>
                <strong>Blocked:</strong> {accountTraceabilityBlockMessage()}
              </p>
              <a href={`/opportunities/${commercialOffer.opportunity_public_id}`} style={{ color: "#1d4ed8", fontWeight: 700 }}>
                Open Opportunity context
              </a>
            </div>
          )}
          {existingLinkedWorkOrders.length === 0 ? (
            <p style={{ margin: "10px 0 0 0", color: "#6b7280" }}>
              No Work Order has been created yet from this Commercial Offer. Submitting the form below creates the
              Work Order; it does not release, post, execute, assign or bill anything.
            </p>
          ) : (
            <div style={{ marginTop: "10px", padding: "12px", border: "1px solid #ddd", background: "#ffffff" }}>
              <p style={{ margin: 0 }}>
                <strong>{existingLinkedWorkOrders.length} Work Order(s) already exist</strong> for this Commercial Offer.
                A second Work Order from the same offer is only for work the customer awarded in parts, and takes only what
                is not on a Work Order yet.
              </p>
              <ul style={{ margin: "8px 0 0 0", paddingLeft: "20px" }}>
                {existingLinkedWorkOrders.map((workOrder) => (
                  <li key={workOrder.public_id}>
                    <a href={`/work-orders/${workOrder.public_id}`} style={{ color: "#1d4ed8", fontWeight: 700 }}>
                      {workOrder.work_order_code}
                    </a>{" "}
                    - {formatWorkOrderStatusLabel(workOrder.work_order_status_code)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : null}

      {commercialOffer ? (
        <form onSubmit={handleCreateWorkOrder} className="form-card" style={{ maxWidth: "960px", borderColor: "#bfdbfe", background: "#eff6ff" }}>
          <h3 style={{ marginTop: 0 }}>Work Order details</h3>
          <div className="form-grid">
            <label className="field-stack">
              Customer WO reference (required - their order number, or the Letter of Intent&apos;s)
              <input
                value={customerWoReference}
                onChange={(event) => {
                  setCustomerWoReference(event.target.value);
                  setCreateError("");
                }}
                maxLength={255}
                required
              />
            </label>
            <label className="field-stack">
              Received date
              <DateInput value={receivedDate} onChange={(event) => setReceivedDate(event.target.value)} />
            </label>
          </div>
          <label className="field-stack">
            Remarks
            <textarea value={remarks} onChange={(event) => setRemarks(event.target.value)} rows={4} maxLength={4000} />
          </label>

          <div>
            <h4>Select accepted offer lines for the Work Order</h4>
            <p className="helper-text">
              A line awarded in parts can be split: enter how much of its quantity this Work Order takes. A line&apos;s
              quantity goes onto Work Orders once, never more in all.
            </p>
            {activeLines.length > 0 ? (
              <div style={{ display: "grid", gap: "10px" }}>
                {activeLines.map((line) => {
                  const entry = lineHandoffById[line.public_id];
                  const left = hundredthsLeft(entry);
                  const selected = selectedLineIds.includes(line.public_id);
                  return (
                    <div key={line.public_id}>
                      <label style={{ display: "grid", gridTemplateColumns: "24px 1fr", gap: "8px", padding: "10px", border: "1px solid #ddd", background: "#fff" }}>
                        <input type="checkbox" checked={selected} disabled={left <= BigInt(0)} onChange={() => toggleLine(line.public_id)} />
                        <span>
                          <strong>Line {line.line_number}: {line.scope_description}</strong><br />
                          <span style={{ color: "#6b7280" }}>
                            {displayValue(line.equipment_service_category)} | {line.quantity} {line.uom} | {formatMoney(line.line_amount, line.currency_code)}
                          </span>
                          {left <= BigInt(0) ? (
                            <span className="helper-text"><br />Already on a Work Order in full: {describeHoldings(entry)}</span>
                          ) : entry && entry.work_orders.length > 0 ? (
                            <span className="helper-text"><br />On a Work Order: {describeHoldings(entry)}. Left: {formatHundredths(left)} {line.uom}</span>
                          ) : null}
                        </span>
                      </label>
                      {selected && left > BigInt(0) ? (
                        <label className="field-stack">
                          Quantity for this Work Order (up to {formatHundredths(left)} {line.uom})
                          <input
                            type="number"
                            min="0.01"
                            step="0.01"
                            max={formatHundredths(left)}
                            value={lineQuantities[line.public_id] ?? ""}
                            onChange={(event) => {
                              setLineQuantities((current) => ({ ...current, [line.public_id]: event.target.value }));
                              setCreateError("");
                            }}
                          />
                        </label>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            ) : <p>No active Commercial Offer lines are available.</p>}
          </div>

          <button
            type="submit"
            disabled={
              saving ||
              access.status !== "allowed" ||
              commercialOffer.offer_status_code !== "ACCEPTED" ||
              selectedLineIds.length === 0 ||
              !accountTraceabilityAvailable ||
              guidance?.work_order_handoff_available === false
            }
          >
            {saving ? "Creating..." : "Create Work Order"}
          </button>
          {createError ? <p className="action-feedback text-danger">{createError}</p> : null}
          {guidance && !guidance.work_order_handoff_available && guidance.work_order_handoff_blocked_reasons.length > 0 ? (
            <p className="action-feedback text-warning">
              <strong>A Work Order cannot be created:</strong> {guidance.work_order_handoff_blocked_reasons.join(" ")}
            </p>
          ) : !accountTraceabilityAvailable ? (
            <p style={{ color: "#92400e", margin: 0 }}>{accountTraceabilityBlockMessage()}</p>
          ) : null}
        </form>
      ) : null}

      {createdWorkOrder ? (
        <div className="content-card" style={{ borderColor: "#bbf7d0", background: "#f0fdf4", maxWidth: "960px" }}>
          <h3 style={{ marginTop: 0 }}>Work Order created</h3>
          <p>
            <a
              href={
                commercialOffer
                  ? hrefWithReturnTarget(
                      `/work-orders/${createdWorkOrder.work_order.public_id}`,
                      `/commercial-offers/${commercialOffer.public_id}`,
                      "Back to Commercial Offer",
                    )
                  : `/work-orders/${createdWorkOrder.work_order.public_id}`
              }
              style={{ color: "#1d4ed8", fontWeight: 700 }}
            >
              Open {createdWorkOrder.work_order.work_order_code}
            </a>
          </p>
          <p>Lines copied: {createdWorkOrder.lines.length}</p>
        </div>
      ) : null}
    </section>
  );
}
