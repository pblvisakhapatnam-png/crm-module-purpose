import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader, ReferenceText, SectionCard, SectionGroup, SectionIndex, StatusBadge } from "../../components/PageLayout";
import CurrencySelect from "../../components/CurrencySelect";
import { amountProblem } from "../../components/amounts";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { readErrorDetail } from "../../components/errorDetail";
import { readSafeReturnTarget, type ReturnTarget } from "../../components/returnTarget";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

const TOKEN_KEY = "pbl_auth_token";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const WORK_ORDER_AMENDMENT_WORK_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER", "OPERATIONS_USER"];

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

const DANGER_BUTTON_STYLE = { ...BUTTON_STYLE, border: "1px solid #b91c1c", color: "#b91c1c" } as const;
const DETAIL_GRID_STYLE = { display: "grid", gridTemplateColumns: "220px 1fr", gap: "8px 12px" } as const;
const COMPACT_DETAIL_GRID_STYLE = { display: "grid", gridTemplateColumns: "180px 1fr", gap: "8px 12px" } as const;

const AMENDMENT_TYPE_LABELS: Record<string, string> = {
  ADMINISTRATIVE: "Administrative",
  COMMERCIAL: "Commercial",
  MIXED: "Mixed (Administrative + Commercial)",
};

const AMENDMENT_LINE_ACTION_LABELS: Record<string, string> = {
  ADD_LINE: "Add Line",
  CHANGE_LINE: "Change Line",
  CANCEL_LINE: "Cancel Line",
};

const COMMERCIAL_OFFER_PURPOSE_LABELS: Record<string, string> = {
  SUPPLEMENTARY: "Supplementary Offer",
  CHANGE_QUOTATION: "Change Quotation",
};

function amendmentTypeLabel(value: string): string {
  return AMENDMENT_TYPE_LABELS[value] || value;
}

function amendmentLineActionLabel(value: string): string {
  return AMENDMENT_LINE_ACTION_LABELS[value] || value;
}

function offerPurposeLabel(value: string): string {
  return COMMERCIAL_OFFER_PURPOSE_LABELS[value] || value;
}

type WorkOrder = {
  public_id: string;
  work_order_code: string;
  work_order_title?: string | null;
  commercial_offer_public_id: string;
  commercial_offer_code?: string | null;
  opportunity_public_id: string;
  account_public_id?: string | null;
};

type WorkOrderLineOption = {
  public_id: string;
  line_number: number;
  scope_description: string;
  quantity: string | number;
  uom: string;
  rate_amount?: string | number | null;
  currency_code: string;
  line_amount?: string | number | null;
};

type Amendment = {
  public_id: string;
  work_order_public_id: string;
  work_order_code: string;
  amendment_sequence_no: number;
  amendment_type_code: string;
  amendment_status_code: string;
  customer_amendment_reference?: string | null;
  customer_amendment_date?: string | null;
  received_date: string;
  effective_date?: string | null;
  amendment_reason: string;
  administrative_change_summary?: string | null;
  commercial_change_summary?: string | null;
  related_commercial_offer_public_id?: string | null;
  related_commercial_offer_code?: string | null;
  related_commercial_offer_purpose?: string | null;
  related_commercial_offer_status_code?: string | null;
  customer_document_reference?: string | null;
  decision_notes?: string | null;
  reviewed_at?: string | null;
  validated_at?: string | null;
  rejected_at?: string | null;
  cancelled_at?: string | null;
  decided_by?: string | null;
  remarks?: string | null;
  created_by?: string | null;
  created_by_display_name?: string | null;
  created_at: string;
  updated_at: string;
};

type Readiness = {
  amendment_status_code: string;
  is_editable: boolean;
  commercial_basis_required: boolean;
  related_offer_linked: boolean;
  related_offer_accepted: boolean;
  has_required_change_detail: boolean;
  can_move_to_under_review: boolean;
  can_move_to_validated: boolean;
  blocking_reasons: string[];
  advisory_message: string;
  applied_to_work_order: boolean;
};

type AmendmentLine = {
  public_id: string;
  amendment_public_id: string;
  line_number: number;
  action_code: string;
  source_work_order_line_public_id?: string | null;
  change_summary?: string | null;
  proposed_scope_description?: string | null;
  proposed_equipment_service_category?: string | null;
  proposed_quantity?: string | number | null;
  proposed_uom?: string | null;
  proposed_rate_amount?: string | number | null;
  proposed_currency_code?: string | null;
  proposed_amount?: string | number | null;
  original_scope_description?: string | null;
  original_equipment_service_category?: string | null;
  original_quantity?: string | number | null;
  original_uom?: string | null;
  original_rate_amount?: string | number | null;
  original_currency_code?: string | null;
  original_amount?: string | number | null;
  original_source_offer_line_public_id?: string | null;
  created_at: string;
};

type TokenPayload = { role_codes?: unknown; exp?: unknown };
type AccessState = { status: "checking" | "allowed" | "no_token" | "expired" | "invalid_token"; roleCodes: string[]; canWork: boolean };

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
  if (!token) return { status: "no_token", roleCodes: [], canWork: false };
  const payload = decodeTokenPayload(token);
  if (!payload) return { status: "invalid_token", roleCodes: [], canWork: false };
  const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp ?? 0);
  if (exp > 0 && exp * 1000 < Date.now()) return { status: "expired", roleCodes: [], canWork: false };
  const roleCodes = Array.isArray(payload.role_codes) ? payload.role_codes.filter((role): role is string => typeof role === "string") : [];
  return { status: "allowed", roleCodes, canWork: roleCodes.some((role) => WORK_ORDER_AMENDMENT_WORK_ROLES.includes(role)) };
}

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "-";
}

function formatStatusLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value.split("_").filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()).join(" ");
}

function formatMoney(value: string | number | null | undefined, currencyCode = "INR"): string {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return `${currencyCode} ${numeric.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function formatDateOnly(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "2-digit" });
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <dt style={{ color: "#6b7280", fontWeight: 700 }}>{label}</dt>
      <dd style={{ margin: 0 }}>{children}</dd>
    </>
  );
}

const LINE_ACTION_OPTIONS = [
  { value: "ADD_LINE", label: "Add Line (new proposed line, no source)" },
  { value: "CHANGE_LINE", label: "Change Line (revise an existing Work Order line)" },
  { value: "CANCEL_LINE", label: "Cancel Line (propose cancelling an existing Work Order line)" },
] as const;

export default function WorkOrderAmendmentDetailPage() {
  const params = useParams();
  const workOrderId = typeof params?.workOrderId === "string" ? params.workOrderId : "";
  const amendmentId = typeof params?.amendmentId === "string" ? params.amendmentId : "";

  const [access, setAccess] = useState<AccessState>({ status: "checking", roleCodes: [], canWork: false });
  const [workOrder, setWorkOrder] = useState<WorkOrder | null>(null);
  // Names for the linked Opportunity and Account, read through their own existing routes so the
  // page shows a customer name rather than a UUID. Display only: if a lookup fails, the
  // reference number is still shown and the link still works.
  const [linkedNames, setLinkedNames] = useState<{ opportunity: string | null; account: string | null }>({
    opportunity: null,
    account: null,
  });
  const linkedOpportunityPublicId = workOrder?.opportunity_public_id ?? null;
  const linkedAccountPublicId = workOrder?.account_public_id ?? null;
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
  const [workOrderLines, setWorkOrderLines] = useState<WorkOrderLineOption[]>([]);
  const [amendment, setAmendment] = useState<Amendment | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [amendmentLines, setAmendmentLines] = useState<AmendmentLine[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [returnTarget, setReturnTarget] = useState<ReturnTarget>({ href: "/work-orders", label: "Back to Work Orders" });

  // Lifecycle decision state
  const [decisionSaving, setDecisionSaving] = useState(false);
  const [decisionMessage, setDecisionMessage] = useState("");
  const [decisionError, setDecisionError] = useState("");
  const [pendingDecision, setPendingDecision] = useState<string | null>(null);
  const [decisionReason, setDecisionReason] = useState("");

  // Add-line form state
  const [lineActionCode, setLineActionCode] = useState<string>("ADD_LINE");
  const [sourceLinePublicId, setSourceLinePublicId] = useState("");
  const [lineChangeSummary, setLineChangeSummary] = useState("");
  const [proposedScopeDescription, setProposedScopeDescription] = useState("");
  const [proposedCategory, setProposedCategory] = useState("");
  const [proposedQuantity, setProposedQuantity] = useState("");
  const [proposedUom, setProposedUom] = useState("");
  const [proposedRateAmount, setProposedRateAmount] = useState("");
  const [proposedCurrencyCode, setProposedCurrencyCode] = useState("");
  const [lineSaving, setLineSaving] = useState(false);
  const [lineMessage, setLineMessage] = useState("");
  const [lineError, setLineError] = useState("");
  const [lineActionInFlight, setLineActionInFlight] = useState<string | null>(null);

  async function loadAll() {
    const currentAccess = readAccess();
    setAccess(currentAccess);
    setError("");
    setMessage("");

    if (!workOrderId || !amendmentId) {
      setError("Open this page from a Work Order Amendment so both the Work Order and amendment can be identified.");
      return;
    }

    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);
    try {
      const [workOrderResponse, amendmentResponse, readinessResponse, linesResponse, woLinesResponse] = await Promise.all([
        fetch(`/api/work-orders/${encodeURIComponent(workOrderId)}`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`/api/work-orders/${encodeURIComponent(workOrderId)}/amendments/${encodeURIComponent(amendmentId)}`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`/api/work-orders/${encodeURIComponent(workOrderId)}/amendments/${encodeURIComponent(amendmentId)}/readiness`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`/api/work-orders/${encodeURIComponent(workOrderId)}/amendments/${encodeURIComponent(amendmentId)}/lines`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`/api/work-orders/${encodeURIComponent(workOrderId)}/lines`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);

      if (!amendmentResponse.ok) {
        if (amendmentResponse.status === 401) clearPrototypeSession();
        setError(`Could not load this Work Order Amendment. HTTP ${amendmentResponse.status}.`);
        setLoading(false);
        return;
      }

      if (workOrderResponse.ok) setWorkOrder((await workOrderResponse.json()) as WorkOrder);
      setAmendment((await amendmentResponse.json()) as Amendment);
      if (readinessResponse.ok) setReadiness((await readinessResponse.json()) as Readiness);
      if (linesResponse.ok) setAmendmentLines((await linesResponse.json()) as AmendmentLine[]);
      if (woLinesResponse.ok) setWorkOrderLines((await woLinesResponse.json()) as WorkOrderLineOption[]);

    } catch {
      setError("Network error while loading this Work Order Amendment.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setReturnTarget(readSafeReturnTarget(workOrderId ? `/work-orders/${workOrderId}` : "/work-orders", "Back to Work Order"));
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workOrderId, amendmentId]);

  async function handleDecision(targetStatusCode: string, reason?: string) {
    if (!workOrder || !amendment) return;
    setDecisionError("");
    setDecisionMessage("");
    const token = getToken();
    if (!token) {
      setDecisionError(SIGN_IN_FIRST);
      return;
    }
    setDecisionSaving(true);
    try {
      const response = await fetch(
        `/api/work-orders/${encodeURIComponent(workOrder.public_id)}/amendments/${encodeURIComponent(amendment.public_id)}/decision`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ target_status_code: targetStatusCode, reason: reason?.trim() || null }),
        },
      );
      if (!response.ok) {
        if (response.status === 401) clearPrototypeSession();
        setDecisionError(await readErrorDetail(response, "Could not update the amendment status. Please try again."));
        setDecisionSaving(false);
        return;
      }
      setDecisionMessage(`Amendment status updated to ${formatStatusLabel(targetStatusCode)}.`);
      setPendingDecision(null);
      setDecisionReason("");
      await loadAll();
    } catch {
      setDecisionError("Network error while updating the amendment status.");
    } finally {
      setDecisionSaving(false);
    }
  }

  async function handleAddLine(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLineError("");
    setLineMessage("");
    if (!workOrder || !amendment) return;

    const requiresSource = lineActionCode !== "ADD_LINE";
    if (requiresSource && !sourceLinePublicId) {
      setLineError(`${amendmentLineActionLabel(lineActionCode)} requires a source Work Order line.`);
      return;
    }
    if (requiresSource && !lineChangeSummary.trim()) {
      setLineError(`A change summary is required for ${amendmentLineActionLabel(lineActionCode)}.`);
      return;
    }
    if (!requiresSource && !proposedScopeDescription.trim()) {
      setLineError("A proposed description / scope is required for Add Line.");
      return;
    }
    // The server's limits: a quantity above 0 and a rate of 0 or more, 16 whole digits, 2 decimals (TB-1 finding TB1-801).
    const numberProblem =
      amountProblem("Proposed quantity", proposedQuantity, 16) ?? amountProblem("Proposed rate amount", proposedRateAmount, 16, true);
    if (numberProblem) {
      setLineError(numberProblem);
      return;
    }

    const token = getToken();
    if (!token) {
      setLineError(SIGN_IN_FIRST);
      return;
    }

    setLineSaving(true);
    try {
      const response = await fetch(
        `/api/work-orders/${encodeURIComponent(workOrder.public_id)}/amendments/${encodeURIComponent(amendment.public_id)}/lines`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({
            action_code: lineActionCode,
            source_work_order_line_public_id: requiresSource ? sourceLinePublicId : null,
            change_summary: lineChangeSummary.trim() || null,
            proposed_scope_description: proposedScopeDescription.trim() || null,
            proposed_equipment_service_category: proposedCategory.trim() || null,
            proposed_quantity: proposedQuantity.trim() || null,
            proposed_uom: proposedUom.trim() || null,
            proposed_rate_amount: proposedRateAmount.trim() || null,
            proposed_currency_code: proposedCurrencyCode || null,
          }),
        },
      );
      if (!response.ok) {
        if (response.status === 401) clearPrototypeSession();
        setLineError(await readErrorDetail(response, "Could not add the amendment line. Please check the form and try again."));
        setLineSaving(false);
        return;
      }
      setLineMessage("Amendment line proposal recorded.");
      setSourceLinePublicId("");
      setLineChangeSummary("");
      setProposedScopeDescription("");
      setProposedCategory("");
      setProposedQuantity("");
      setProposedUom("");
      setProposedRateAmount("");
      setProposedCurrencyCode("");
      await loadAll();
    } catch {
      setLineError("Network error while adding the amendment line.");
    } finally {
      setLineSaving(false);
    }
  }

  async function handleDeleteLine(linePublicId: string) {
    if (!workOrder || !amendment) return;
    setLineError("");
    setLineMessage("");
    const token = getToken();
    if (!token) {
      setLineError(SIGN_IN_FIRST);
      return;
    }
    setLineActionInFlight(linePublicId);
    try {
      const response = await fetch(
        `/api/work-orders/${encodeURIComponent(workOrder.public_id)}/amendments/${encodeURIComponent(amendment.public_id)}/lines/${encodeURIComponent(linePublicId)}`,
        { method: "DELETE", headers: { Authorization: `Bearer ${token}` } },
      );
      if (!response.ok) {
        if (response.status === 401) clearPrototypeSession();
        setLineError(await readErrorDetail(response, "Could not remove the amendment line. Please try again."));
        setLineActionInFlight(null);
        return;
      }
      setLineMessage("Amendment line proposal removed.");
      await loadAll();
    } catch {
      setLineError("Network error while removing the amendment line.");
    } finally {
      setLineActionInFlight(null);
    }
  }

  const isEditable = readiness?.is_editable ?? (amendment ? ["RECEIVED", "UNDER_REVIEW"].includes(amendment.amendment_status_code) : false);
  const isTerminal = amendment ? !isEditable : false;

  return (
    <section>
      <PageHeader
        eyebrow="Work Order Amendment"
        back={{ href: returnTarget.href, label: returnTarget.label }}
        title={
          amendment
            ? `Amendment #${amendment.amendment_sequence_no} - ${amendmentTypeLabel(amendment.amendment_type_code)}`
            : "Work Order Amendment"
        }
        badges={
          amendment ? (
            <>
              <StatusBadge code={amendment.amendment_status_code} label={formatStatusLabel(amendment.amendment_status_code)} />
              <span className="status-badge status-badge--info">{amendmentTypeLabel(amendment.amendment_type_code)}</span>
            </>
          ) : null
        }
        subtitle="A change the customer asked for, recorded for review. It does not change the Work Order or any of its lines, and validating it does not apply it."
        actions={
          <button type="button" onClick={() => void loadAll()} disabled={loading} style={BUTTON_STYLE}>
            {loading ? "Loading..." : "Refresh"}
          </button>
        }
      >
        {message ? <p className="text-success">{message}</p> : null}
        {error ? <p className="text-danger">{error}</p> : null}
      </PageHeader>

      {amendment ? (
        <div style={{ marginTop: "24px", display: "grid", gap: "16px", maxWidth: "1120px" }}>
          <SectionIndex
            items={[
              { id: "amd-details", label: "The amendment" },
              { id: "amd-context", label: "What it relates to" },
              { id: "amd-change", label: "The change requested" },
              { id: "amd-review", label: "Review and decision" },
              { id: "amd-lines", label: "Line changes" },
            ]}
          />
          <SectionGroup id="amd-details" title="The amendment" tone="blue">
          <SectionCard title="Amendment details">
            <dl style={DETAIL_GRID_STYLE}>
              <DetailRow label="Amendment">#{amendment.amendment_sequence_no} - {amendmentTypeLabel(amendment.amendment_type_code)}</DetailRow>
              <DetailRow label="Status">{formatStatusLabel(amendment.amendment_status_code)}</DetailRow>
              <DetailRow label="Customer amendment reference">{displayValue(amendment.customer_amendment_reference)}</DetailRow>
              <DetailRow label="Customer amendment date">{formatDateOnly(amendment.customer_amendment_date)}</DetailRow>
              <DetailRow label="Received date">{formatDateOnly(amendment.received_date)}</DetailRow>
              <DetailRow label="Effective date">{formatDateOnly(amendment.effective_date)}</DetailRow>
              <DetailRow label="Created at">{formatDateTime(amendment.created_at)}</DetailRow>
              <DetailRow label="Last updated">{formatDateTime(amendment.updated_at)}</DetailRow>
              <DetailRow label="Created by">{displayValue(amendment.created_by_display_name ?? amendment.created_by)}</DetailRow>
              {amendment.decided_by ? <DetailRow label="Last decided by">{displayValue(amendment.decided_by)}</DetailRow> : null}
            </dl>
          </SectionCard>
          </SectionGroup>

          <SectionGroup id="amd-context" title="What it relates to" tone="teal" description="The Work Order, customer and any offer this change is based on.">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
            <SectionCard title="Work Order and customer">
              <dl style={COMPACT_DETAIL_GRID_STYLE}>
                <DetailRow label="Work Order">
                  {workOrder ? (
                    <a href={`/work-orders/${workOrder.public_id}`} style={{ color: "#1d4ed8", fontWeight: 700 }}>
                      {workOrder.work_order_code}
                    </a>
                  ) : displayValue(amendment.work_order_code)}
                </DetailRow>
                {workOrder ? (
                  <>
                    <DetailRow label="Base Commercial Offer">
                      <a href={`/commercial-offers/${workOrder.commercial_offer_public_id}`} style={{ color: "#1d4ed8", fontWeight: 700 }}>
                        {displayValue(workOrder.commercial_offer_code)}
                      </a>
                    </DetailRow>
                    <DetailRow label="Opportunity">
                      <a href={`/opportunities/${workOrder.opportunity_public_id}`} style={{ color: "#1d4ed8", fontWeight: 700 }}>
                        {linkedNames.opportunity ?? "Open Opportunity"}
                      </a>
                      <div>
                        <ReferenceText>{workOrder.opportunity_public_id}</ReferenceText>
                      </div>
                    </DetailRow>
                    <DetailRow label="Account">
                      {workOrder.account_public_id ? (
                        <a href={`/accounts/${workOrder.account_public_id}`} style={{ color: "#1d4ed8", fontWeight: 700 }}>
                          {linkedNames.account ?? "Open Account"}
                        </a>
                      ) : "-"}
                      {workOrder.account_public_id ? (
                        <div>
                          <ReferenceText>{workOrder.account_public_id}</ReferenceText>
                        </div>
                      ) : null}
                    </DetailRow>
                  </>
                ) : null}
              </dl>
            </SectionCard>

            <SectionCard title="Commercial basis (Supplementary Offer / Change Quotation)">
              {amendment.related_commercial_offer_public_id ? (
                <dl style={COMPACT_DETAIL_GRID_STYLE}>
                  <DetailRow label="Linked offer">
                    <a href={`/commercial-offers/${amendment.related_commercial_offer_public_id}`} style={{ color: "#1d4ed8", fontWeight: 700 }}>
                      {displayValue(amendment.related_commercial_offer_code)}
                    </a>
                  </DetailRow>
                  <DetailRow label="Purpose">{offerPurposeLabel(amendment.related_commercial_offer_purpose || "")}</DetailRow>
                  <DetailRow label="Status">{formatStatusLabel(amendment.related_commercial_offer_status_code)}</DetailRow>
                </dl>
              ) : (
                <p style={{ marginTop: 0, color: "#6b7280" }}>
                  No commercial basis is linked yet. Commercial and Mixed amendments require an accepted
                  Supplementary Offer or Change Quotation before they can be validated.
                </p>
              )}
            </SectionCard>
          </div>
          </SectionGroup>

          <SectionGroup id="amd-change" title="The change requested" tone="amber">
          <SectionCard title="What the customer asked for">
            <dl style={DETAIL_GRID_STYLE}>
              <DetailRow label="Amendment reason / summary">{amendment.amendment_reason}</DetailRow>
              <DetailRow label="Administrative change summary">{displayValue(amendment.administrative_change_summary)}</DetailRow>
              <DetailRow label="Commercial change summary">{displayValue(amendment.commercial_change_summary)}</DetailRow>
              <DetailRow label="Customer document reference">{displayValue(amendment.customer_document_reference)}</DetailRow>
              <DetailRow label="Remarks">{displayValue(amendment.remarks)}</DetailRow>
              <DetailRow label="Decision notes">{displayValue(amendment.decision_notes)}</DetailRow>
            </dl>
          </SectionCard>
          </SectionGroup>

          <SectionGroup id="amd-review" title="Review and decision" tone="violet">
          <SectionCard title="Review status and decision">
            {readiness ? (
              <p style={{ marginTop: 0 }}>{readiness.advisory_message}</p>
            ) : isTerminal ? (
              <p style={{ marginTop: 0 }}>
                This amendment is {formatStatusLabel(amendment.amendment_status_code)} and is read-only. It has not
                been applied to the Work Order.
              </p>
            ) : null}
            {readiness && readiness.blocking_reasons.length > 0 ? (
              <ul className="text-warning">
                {readiness.blocking_reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : null}
            {decisionMessage ? <p className="text-success">{decisionMessage}</p> : null}
            {decisionError ? <p className="text-danger">{decisionError}</p> : null}

            {access.canWork && !isTerminal ? (
              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "10px" }}>
                {amendment.amendment_status_code === "RECEIVED" ? (
                  <button
                    type="button"
                    onClick={() => void handleDecision("UNDER_REVIEW")}
                    disabled={decisionSaving || !(readiness ? readiness.can_move_to_under_review : true)}
                    style={BUTTON_STYLE}
                  >
                    {decisionSaving ? "Saving..." : "Start Review"}
                  </button>
                ) : null}
                {amendment.amendment_status_code === "UNDER_REVIEW" ? (
                  <button
                    type="button"
                    onClick={() => void handleDecision("VALIDATED")}
                    disabled={decisionSaving || !(readiness?.can_move_to_validated ?? false)}
                    style={BUTTON_STYLE}
                    title={!(readiness?.can_move_to_validated ?? false) ? "Blocked - see reasons above." : undefined}
                  >
                    {decisionSaving ? "Saving..." : "Validate"}
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => setPendingDecision(pendingDecision === "REJECTED" ? null : "REJECTED")}
                  disabled={decisionSaving}
                  style={DANGER_BUTTON_STYLE}
                >
                  Reject
                </button>
                <button
                  type="button"
                  onClick={() => setPendingDecision(pendingDecision === "CANCELLED" ? null : "CANCELLED")}
                  disabled={decisionSaving}
                  style={DANGER_BUTTON_STYLE}
                >
                  Cancel
                </button>
              </div>
            ) : null}

            {pendingDecision ? (
              <div style={{ marginTop: "10px", padding: "12px", border: "1px solid #ddd", background: "#fff" }}>
                <label className="field-stack">
                  Reason (required to {pendingDecision === "REJECTED" ? "reject" : "cancel"} this amendment)
                  <textarea value={decisionReason} onChange={(event) => setDecisionReason(event.target.value)} rows={2} maxLength={2000} />
                </label>
                <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
                  <button
                    type="button"
                    onClick={() => void handleDecision(pendingDecision, decisionReason)}
                    disabled={decisionSaving || !decisionReason.trim()}
                    style={DANGER_BUTTON_STYLE}
                  >
                    {decisionSaving ? "Saving..." : `Confirm ${pendingDecision === "REJECTED" ? "Reject" : "Cancel"}`}
                  </button>
                  <button type="button" onClick={() => { setPendingDecision(null); setDecisionReason(""); }} style={BUTTON_STYLE}>
                    Dismiss
                  </button>
                </div>
              </div>
            ) : null}

          </SectionCard>
          </SectionGroup>

          <SectionGroup id="amd-lines" title="Line changes" tone="teal" description="Proposed changes to individual Work Order lines.">
          <SectionCard title="Amendment lines">
            <p style={{ marginTop: 0 }}>
              Each row proposes a change against this amendment only. Original values are the Work Order line's
              values captured at the time the proposal was made; proposed values are the customer's requested
              change. Neither column reflects the Work Order's current state after this amendment.
            </p>
            {amendmentLines.length > 0 ? (
              <div className="data-table-wrap" style={{ marginTop: 0 }}>
                <table className="data-table data-table-wide">
                  <thead>
                    <tr>
                      <th>Line</th>
                      <th>Action</th>
                      <th>Original (source line snapshot)</th>
                      <th>Proposed</th>
                      <th>Change summary</th>
                      <th>Source offer line</th>
                      {isEditable && access.canWork ? <th>Actions</th> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {amendmentLines.map((line) => (
                      <tr key={line.public_id}>
                        <td>{line.line_number}</td>
                        <td>{amendmentLineActionLabel(line.action_code)}</td>
                        <td>
                          {line.action_code === "ADD_LINE" ? (
                            <span style={{ color: "#6b7280" }}>Not applicable (new line)</span>
                          ) : (
                            <>
                              {displayValue(line.original_scope_description)}<br />
                              <span style={{ color: "#6b7280" }}>
                                {displayValue(line.original_quantity != null ? String(line.original_quantity) : null)} {line.original_uom || ""} @{" "}
                                {formatMoney(line.original_rate_amount, line.original_currency_code || "INR")}
                              </span>
                            </>
                          )}
                        </td>
                        <td>
                          {line.action_code === "CANCEL_LINE" ? (
                            <span className="text-danger">Proposed cancellation</span>
                          ) : (
                            <>
                              {displayValue(line.proposed_scope_description)}<br />
                              <span style={{ color: "#6b7280" }}>
                                {displayValue(line.proposed_quantity != null ? String(line.proposed_quantity) : null)} {line.proposed_uom || ""} @{" "}
                                {formatMoney(line.proposed_rate_amount, line.proposed_currency_code || "INR")}
                              </span>
                            </>
                          )}
                        </td>
                        <td>{displayValue(line.change_summary)}</td>
                        <td>{displayValue(line.original_source_offer_line_public_id)}</td>
                        {isEditable && access.canWork ? (
                          <td>
                            <button
                              type="button"
                              onClick={() => void handleDeleteLine(line.public_id)}
                              disabled={lineActionInFlight === line.public_id}
                              style={DANGER_BUTTON_STYLE}
                            >
                              {lineActionInFlight === line.public_id ? "Removing..." : "Remove"}
                            </button>
                          </td>
                        ) : null}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p>No amendment line has been proposed yet.</p>}

            {lineMessage ? <p className="text-success">{lineMessage}</p> : null}
            {lineError ? <p className="text-danger">{lineError}</p> : null}

            {isEditable && access.canWork ? (
              <form onSubmit={handleAddLine} className="form-card" style={{ marginTop: "16px", borderColor: "#bfdbfe", background: "#eff6ff" }}>
                <h4 style={{ marginTop: 0 }}>Propose a line change</h4>
                <div className="form-grid">
                  <label className="field-stack">
                    Action
                    <select value={lineActionCode} onChange={(event) => { setLineActionCode(event.target.value); setSourceLinePublicId(""); }}>
                      {LINE_ACTION_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>
                  {lineActionCode !== "ADD_LINE" ? (
                    <label className="field-stack">
                      Source Work Order line (required)
                      <select value={sourceLinePublicId} onChange={(event) => setSourceLinePublicId(event.target.value)}>
                        <option value="">-- select a Work Order line --</option>
                        {workOrderLines.map((line) => (
                          <option key={line.public_id} value={line.public_id}>
                            Line {line.line_number}: {line.scope_description}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                </div>

                {lineActionCode !== "ADD_LINE" && sourceLinePublicId ? (
                  (() => {
                    const selected = workOrderLines.find((line) => line.public_id === sourceLinePublicId);
                    if (!selected) return null;
                    return (
                      <p style={{ color: "#6b7280" }}>
                        Original values: {selected.scope_description} - {selected.quantity} {selected.uom} @{" "}
                        {formatMoney(selected.rate_amount, selected.currency_code)}
                      </p>
                    );
                  })()
                ) : null}

                {lineActionCode !== "ADD_LINE" ? (
                  <label className="field-stack">
                    Change summary (required)
                    <textarea value={lineChangeSummary} onChange={(event) => setLineChangeSummary(event.target.value)} rows={2} maxLength={2000} required />
                  </label>
                ) : null}

                {lineActionCode !== "CANCEL_LINE" ? (
                  <>
                    <label className="field-stack">
                      Proposed description / scope {lineActionCode === "ADD_LINE" ? "(required)" : "(optional - leave blank to keep unchanged)"}
                      <textarea value={proposedScopeDescription} onChange={(event) => setProposedScopeDescription(event.target.value)} rows={2} maxLength={1000} />
                    </label>
                    <div className="form-grid">
                      <label className="field-stack">
                        Proposed category
                        <input value={proposedCategory} onChange={(event) => setProposedCategory(event.target.value)} maxLength={255} />
                      </label>
                      <label className="field-stack">
                        Proposed quantity
                        <input value={proposedQuantity} onChange={(event) => setProposedQuantity(event.target.value)} inputMode="decimal" />
                      </label>
                      <label className="field-stack">
                        Proposed UOM
                        <input value={proposedUom} onChange={(event) => setProposedUom(event.target.value)} maxLength={50} />
                      </label>
                      <label className="field-stack">
                        Proposed rate amount
                        <input value={proposedRateAmount} onChange={(event) => setProposedRateAmount(event.target.value)} inputMode="decimal" />
                      </label>
                      <label className="field-stack">
                        Proposed currency
                        <CurrencySelect value={proposedCurrencyCode} onChange={setProposedCurrencyCode} blankLabel="None proposed" />
                      </label>
                    </div>
                  </>
                ) : null}

                <button type="submit" disabled={lineSaving}>
                  {lineSaving ? "Saving..." : `Record ${amendmentLineActionLabel(lineActionCode)}`}
                </button>
              </form>
            ) : (
              <p style={{ marginTop: "12px", color: "#6b7280" }}>
                {isTerminal
                  ? "Amendment lines cannot be changed while this amendment is read-only."
                  : "Your role can view amendment lines but cannot add or remove them."}
              </p>
            )}
          </SectionCard>
          </SectionGroup>
        </div>
      ) : null}
    </section>
  );
}
