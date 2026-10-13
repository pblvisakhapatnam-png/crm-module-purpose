import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import {
  PageHeader,
  ReferenceText,
  SectionCard,
  SectionGroup,
  SectionIndex,
  StatusBadge,
  formatWorkOrderStatusLabel,
} from "../../components/PageLayout";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { offerVersionLabel } from "../../components/offerVersion";
import WorkOrderBillingTermsSection from "./WorkOrderBillingTermsSection";
import WorkOrderContractPeriodSection from "./WorkOrderContractPeriodSection";
import WorkOrderHolidaysSection from "./WorkOrderHolidaysSection";
import WorkOrderLineDetailsSection, { type WorkOrderLineDetail, missingItemsText } from "./WorkOrderLineDetailsSection";
import WorkOrderResourceRequirementsSection from "./WorkOrderResourceRequirementsSection";
import AllocationsSection from "../allocations/AllocationsSection";
import { canWriteRequirements } from "../resource-requirements/resourceRequirementState";
import { type LineBillingTerms, billingBasisLabel, missingTermsText } from "./workOrderBillingTermsState";
import { type ContractPeriod } from "./workOrderContractPeriodState";
import { type HolidayList, resultingRefreshKey } from "./workOrderHolidaysState";
import {
  INITIAL_WORK_ORDER_PAGE_STATE,
  type BusinessEventSummary,
  type ListResult,
  type RelatedOfferSummary,
  type WorkOrder,
  type WorkOrderAmendmentSummary,
  type WorkOrderLine,
  workOrderPageReducer,
} from "./workOrderPageState";
import { readSafeReturnTarget, type ReturnTarget } from "../../components/returnTarget";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

const TOKEN_KEY = "pbl_auth_token";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const EVENT_VIEW_ROLES = ["ADMIN", "MANAGEMENT_READ_ONLY"];
const RELATED_OFFER_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];
const WORK_ORDER_AMENDMENT_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER", "OPERATIONS_USER"];
const WORK_ORDER_LINE_DETAIL_WRITE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER", "OPERATIONS_USER"];
// Slice 7D: its own permission on the backend, holding the same four roles today.
const WORK_ORDER_LINE_BILLING_TERMS_WRITE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER", "OPERATIONS_USER"];
// Slice 7D Part 3: two permissions on the backend - the dates and the extensions - so extensions can
// later be narrowed to managers without a code change. Both hold the same four roles today.
const WORK_ORDER_CONTRACT_PERIOD_WRITE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER", "OPERATIONS_USER"];

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

const DETAIL_GRID_STYLE = { display: "grid", gridTemplateColumns: "220px 1fr", gap: "8px 12px" } as const;
const COMPACT_DETAIL_GRID_STYLE = { display: "grid", gridTemplateColumns: "180px 1fr", gap: "8px 12px" } as const;

// The page's record types moved to workOrderPageState.ts with the reducer that decides what shows.
type TokenPayload = { role_codes?: unknown; exp?: unknown };
type AccessState = {
  status: "checking" | "allowed" | "no_token" | "expired" | "invalid_token";
  roleCodes: string[];
  canViewEvents: boolean;
  canCreateRelatedOffer: boolean;
  canCreateAmendment: boolean;
  canEditLineDetails: boolean;
  canEditBillingTerms: boolean;
  canEditContractPeriod: boolean;
  // WRR-001: Operations and Admin record what each line needs on site.
  canWriteRequirements: boolean;
};

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
  if (!token) return { status: "no_token", roleCodes: [], canViewEvents: false, canCreateRelatedOffer: false, canCreateAmendment: false, canEditLineDetails: false, canEditBillingTerms: false, canEditContractPeriod: false, canWriteRequirements: false };
  const payload = decodeTokenPayload(token);
  if (!payload) return { status: "invalid_token", roleCodes: [], canViewEvents: false, canCreateRelatedOffer: false, canCreateAmendment: false, canEditLineDetails: false, canEditBillingTerms: false, canEditContractPeriod: false, canWriteRequirements: false };
  const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp ?? 0);
  if (exp > 0 && exp * 1000 < Date.now()) return { status: "expired", roleCodes: [], canViewEvents: false, canCreateRelatedOffer: false, canCreateAmendment: false, canEditLineDetails: false, canEditBillingTerms: false, canEditContractPeriod: false, canWriteRequirements: false };
  const roleCodes = Array.isArray(payload.role_codes) ? payload.role_codes.filter((role): role is string => typeof role === "string") : [];
  return {
    status: "allowed",
    roleCodes,
    canViewEvents: roleCodes.some((role) => EVENT_VIEW_ROLES.includes(role)),
    canCreateRelatedOffer: roleCodes.some((role) => RELATED_OFFER_CREATE_ROLES.includes(role)),
    canCreateAmendment: roleCodes.some((role) => WORK_ORDER_AMENDMENT_CREATE_ROLES.includes(role)),
    canEditLineDetails: roleCodes.some((role) => WORK_ORDER_LINE_DETAIL_WRITE_ROLES.includes(role)),
    canEditBillingTerms: roleCodes.some((role) => WORK_ORDER_LINE_BILLING_TERMS_WRITE_ROLES.includes(role)),
    canEditContractPeriod: roleCodes.some((role) => WORK_ORDER_CONTRACT_PERIOD_WRITE_ROLES.includes(role)),
    canWriteRequirements: canWriteRequirements(roleCodes),
  };
}

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "-";
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

function formatStatusLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value.split("_").filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()).join(" ");
}

function accessMessage(access: AccessState): string {
  if (access.status === "checking") return "Checking your session...";
  if (access.status === "no_token") return "Sign in first to view Work Orders.";
  if (access.status === "expired") return "Sign in again because your session has expired.";
  if (access.status === "invalid_token") return "Sign in again because the current session token is not readable.";
  return "Release to Ops, hired machines, crew, log sheets and billing are not built yet.";
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <dt style={{ color: "#6b7280", fontWeight: 700 }}>{label}</dt>
      <dd style={{ margin: 0 }}>{children}</dd>
    </>
  );
}

export default function WorkOrderDetailPage() {
  const params = useParams();
  const workOrderId = params?.workOrderId;
  // One page-load generation decides what the page shows; see workOrderPageState.ts.
  const [page, dispatch] = useReducer(workOrderPageReducer, INITIAL_WORK_ORDER_PAGE_STATE);
  // The generation counter itself is a ref, so a load knows its own number synchronously, before
  // React has re-rendered with it.
  const generationCounter = useRef(0);
  const { workOrder, lines, lineDetails, billingTerms, loading, error } = page;
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
  const [access, setAccess] = useState<AccessState>({ status: "checking", roleCodes: [], canViewEvents: false, canCreateRelatedOffer: false, canCreateAmendment: false, canEditLineDetails: false, canEditBillingTerms: false, canEditContractPeriod: false, canWriteRequirements: false });
  const [returnTarget, setReturnTarget] = useState<ReturnTarget>({
    href: "/work-orders",
    label: "Back to Work Orders",
  });

  async function loadWorkOrder(publicId: string) {
    const currentAccess = readAccess();
    setAccess(currentAccess);
    // This load takes the next generation. Everything the previous one showed is cleared, and every
    // result still on its way - a load or a save - now belongs to an older generation and is ignored.
    const generation = (generationCounter.current += 1);
    dispatch({ type: "load-started", generation, workOrderPublicId: publicId });

    const token = getToken();
    if (!token) {
      dispatch({ type: "load-failed", generation, error: SIGN_IN_FIRST });
      return;
    }

    let workOrderResponse: Response;
    try {
      workOrderResponse = await fetch(`/api/work-orders/${encodeURIComponent(publicId)}`, { headers: { Authorization: `Bearer ${token}` } });
    } catch {
      dispatch({ type: "load-failed", generation, error: "Network error while loading this Work Order." });
      return;
    }

    if (!workOrderResponse.ok) {
      if (workOrderResponse.status === 401) clearPrototypeSession();
      dispatch({ type: "load-failed", generation, error: `Could not load Work Order. HTTP ${workOrderResponse.status}.` });
      return;
    }

    dispatch({ type: "work-order-loaded", generation, workOrder: (await workOrderResponse.json()) as WorkOrder });

    let linesResponse: Response;
    try {
      linesResponse = await fetch(`/api/work-orders/${encodeURIComponent(publicId)}/lines`, { headers: { Authorization: `Bearer ${token}` } });
    } catch {
      dispatch({ type: "lines-failed", generation, error: "Work Order loaded, but line loading failed due to a network error." });
      return;
    }

    if (!linesResponse.ok) {
      dispatch({
        type: "lines-failed",
        generation,
        error: `Work Order loaded, but lines could not be loaded. HTTP ${linesResponse.status}.`,
      });
      return;
    }

    dispatch({ type: "lines-loaded", generation, lines: (await linesResponse.json()) as WorkOrderLine[] });
    void loadRelatedOffers(publicId, token, generation);
    void loadAmendments(publicId, token, generation);
    void loadLineDetails(publicId, token, generation);
    void loadBillingTerms(publicId, token, generation);
    void loadContractPeriod(publicId, token, generation);
    void loadHolidays(publicId, token, generation);
    dispatch({ type: "load-finished", generation });

    if (currentAccess.canViewEvents) {
      void loadHandoffEvents(publicId, token, generation);
    } else {
      dispatch({ type: "handoff-events", generation, result: { status: "loaded", entries: [] } });
    }
  }

  /**
   * One list request. `apply` dispatches the result for its own list, carrying the generation this
   * request started in, so a result that arrives after a newer page load is ignored.
   */
  async function loadList<T>(
    path: string,
    token: string,
    apply: (result: ListResult<T>) => void,
    httpError: (status: number) => string,
    networkError: string,
    // A route that returns one record rather than a list passes a reader that wraps it, so it goes
    // through the same generation handling as everything else on the page.
    readEntries: (body: unknown) => T[] = (body) => body as T[],
  ) {
    apply({ status: "loading" });
    try {
      const response = await fetch(path, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) {
        apply({ status: "failed", error: httpError(response.status) });
        return;
      }
      apply({ status: "loaded", entries: readEntries(await response.json()) });
    } catch {
      apply({ status: "failed", error: networkError });
    }
  }

  async function loadRelatedOffers(publicId: string, token: string, generation: number) {
    await loadList<RelatedOfferSummary>(
      `/api/work-orders/${encodeURIComponent(publicId)}/related-offers`,
      token,
      (result) => dispatch({ type: "related-offers", generation, result }),
      (status) => `Related Commercial Offers could not be loaded. HTTP ${status}.`,
      "Network error while loading related Commercial Offers.",
    );
  }

  async function loadAmendments(publicId: string, token: string, generation: number) {
    await loadList<WorkOrderAmendmentSummary>(
      `/api/work-orders/${encodeURIComponent(publicId)}/amendments`,
      token,
      (result) => dispatch({ type: "amendments", generation, result }),
      (status) => `Work Order Amendments could not be loaded. HTTP ${status}.`,
      "Network error while loading Work Order Amendments.",
    );
  }

  async function loadLineDetails(publicId: string, token: string, generation: number) {
    await loadList<WorkOrderLineDetail>(
      `/api/work-orders/${encodeURIComponent(publicId)}/line-details`,
      token,
      (result) => dispatch({ type: "line-details", generation, result }),
      (status) => `Site and billing details could not be loaded. HTTP ${status}.`,
      "Network error while loading site and billing details.",
    );
  }

  async function loadBillingTerms(publicId: string, token: string, generation: number) {
    await loadList<LineBillingTerms>(
      `/api/work-orders/${encodeURIComponent(publicId)}/billing-terms`,
      token,
      (result) => dispatch({ type: "billing-terms", generation, result }),
      (status) => `Billing terms could not be loaded. HTTP ${status}.`,
      "Network error while loading billing terms.",
    );
  }

  async function loadContractPeriod(publicId: string, token: string, generation: number) {
    // One record, not a list, so it is carried as a one-entry result through the same loadList shape
    // every other part of the page uses - and so it obeys the same generation rule.
    await loadList<ContractPeriod>(
      `/api/work-orders/${encodeURIComponent(publicId)}/contract-period`,
      token,
      (result) => dispatch({ type: "contract-period", generation, result }),
      (status) => `The contract dates could not be loaded. HTTP ${status}.`,
      "Network error while loading the contract dates.",
      (body) => [body as ContractPeriod],
    );
  }

  async function loadHolidays(publicId: string, token: string, generation: number) {
    // One record, carried as a one-entry result exactly as the contract period is (Slice 7D Part 4).
    await loadList<HolidayList>(
      `/api/work-orders/${encodeURIComponent(publicId)}/holidays`,
      token,
      (result) => dispatch({ type: "holidays", generation, result }),
      (status) => `The holidays could not be loaded. HTTP ${status}.`,
      "Network error while loading the holidays.",
      (body) => [body as HolidayList],
    );
  }

  async function loadHandoffEvents(publicId: string, token: string, generation: number) {
    await loadList<BusinessEventSummary>(
      `/api/events/recent?record_type=work_order&record_public_id=${encodeURIComponent(publicId)}&limit=10`,
      token,
      (result) => dispatch({ type: "handoff-events", generation, result }),
      (status) => `Business event history could not be loaded. HTTP ${status}.`,
      "Network error while loading business event history.",
    );
  }

  useEffect(() => {
    setReturnTarget(readSafeReturnTarget("/work-orders", "Back to Work Orders"));
    if (typeof workOrderId === "string") void loadWorkOrder(workOrderId);
  }, [workOrderId]);

  const eventHref = useMemo(() => {
    if (!workOrder) return "";
    const returnTo = `/work-orders/${workOrder.public_id}`;
    return `/events?returnTo=${encodeURIComponent(returnTo)}&returnLabel=${encodeURIComponent("Back to Work Order")}`;
  }, [workOrder]);

  const workOrderReturnTo = workOrder ? `/work-orders/${workOrder.public_id}` : "";

  return (
    <section>
      <PageHeader
        eyebrow="Work Order"
        back={{ href: returnTarget.href, label: returnTarget.label }}
        title={
          workOrder
            ? workOrder.work_order_title
              ? `${workOrder.work_order_code} - ${workOrder.work_order_title}`
              : workOrder.work_order_code
            : "Work Order"
        }
        badges={
          workOrder ? (
            <StatusBadge code={workOrder.work_order_status_code} label={formatWorkOrderStatusLabel(workOrder.work_order_status_code)} />
          ) : null
        }
        subtitle="Created from an accepted Commercial Offer. It holds everything the customer awarded, and each line's site, billing details and billing terms. The Hiring or Transportation module will later add the customer's Finance setup, the release to Ops, equipment and crew, log sheets, and the billing that works the terms out."
        actions={
          <>
            <button type="button" onClick={() => { if (typeof workOrderId === "string") void loadWorkOrder(workOrderId); }} disabled={loading || typeof workOrderId !== "string"} style={BUTTON_STYLE}>
              {loading ? "Loading..." : "Refresh"}
            </button>
            {access.canViewEvents && workOrder ? <a href={eventHref} style={BUTTON_STYLE}>View recent business events</a> : null}
          </>
        }
      >
        <p className="helper-text">{accessMessage(access)}</p>
        {error ? <p className="text-danger">{error}</p> : null}
      </PageHeader>

      {workOrder ? (
        <div style={{ marginTop: "24px", display: "grid", gap: "16px", maxWidth: "1120px" }}>
          <SectionIndex
            items={[
              { id: "wo-summary", label: "The Work Order" },
              { id: "wo-origin", label: "Where it came from" },
              { id: "wo-lines", label: "Lines" },
              { id: "wo-resources", label: "Resources needed" },
              { id: "wo-machines", label: "Machines allocated" },
              { id: "wo-changes", label: "Changes after award" },
              { id: "wo-later", label: "Not built yet" },
            ]}
          />
          <SectionGroup id="wo-summary" title="The Work Order" tone="blue">
          <SectionCard title="Work Order snapshot">
            <dl style={DETAIL_GRID_STYLE}>
              <DetailRow label="Work Order code">{workOrder.work_order_code}</DetailRow>
              <DetailRow label="Title">{displayValue(workOrder.work_order_title)}</DetailRow>
              <DetailRow label="Status">{formatWorkOrderStatusLabel(workOrder.work_order_status_code)}</DetailRow>
              <DetailRow label="Customer WO reference">{displayValue(workOrder.customer_wo_reference)}</DetailRow>
              <DetailRow label="Received date">{formatDateOnly(workOrder.received_date)}</DetailRow>
              <DetailRow label="Created at">{formatDateTime(workOrder.created_at)}</DetailRow>
              <DetailRow label="Last updated">{formatDateTime(workOrder.updated_at)}</DetailRow>
              <DetailRow label="Created by">{displayValue(workOrder.created_by_display_name ?? workOrder.created_by)}</DetailRow>
            </dl>
          </SectionCard>
          <WorkOrderContractPeriodSection
            workOrderPublicId={workOrder.public_id}
            period={page.contractPeriod}
            periodLoaded={page.contractPeriodLoaded}
            periodError={page.contractPeriodError}
            canEdit={access.canEditContractPeriod}
            isClosed={workOrder.work_order_status_code === "CLOSED"}
            token={getToken()}
            loadGeneration={page.generation}
            onApplied={(period, generation) => dispatch({ type: "contract-period-applied", generation, period })}
          />
          <WorkOrderHolidaysSection
            workOrderPublicId={workOrder.public_id}
            holidays={page.holidays}
            holidaysLoaded={page.holidaysLoaded}
            holidaysError={page.holidaysError}
            canEdit={access.canEditBillingTerms}
            isClosed={workOrder.work_order_status_code === "CLOSED"}
            token={getToken()}
            loadGeneration={page.generation}
            onApplied={(holidays, generation) => dispatch({ type: "holidays-applied", generation, holidays })}
            // HOL-1: the holidays that apply are read again whenever what they are worked out from changes on the page.
            resultingKey={resultingRefreshKey({
              workOrderPublicId: workOrder.public_id,
              contractVersion: page.contractPeriod?.period_version,
              extensionCount: page.contractPeriod?.extensions.length,
              lineDetailVersions: page.lineDetails.entries.map((detail) => detail.detail_version),
              billingTermRevisions: page.billingTerms.entries.flatMap((line) => line.periods.map((period) => period.term_revision)),
              holidayListVersion: page.holidays?.list_version,
            })}
          />
          </SectionGroup>

          <SectionGroup id="wo-origin" title="Where it came from" tone="teal" description="The accepted offer, the customer and the enquiry behind this Work Order.">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
            <SectionCard title="Source Commercial Offer">
              <dl style={COMPACT_DETAIL_GRID_STYLE}>
                <DetailRow label="Commercial Offer">
                  <a
                    href={hrefWithReturnTarget(
                      `/commercial-offers/${workOrder.commercial_offer_public_id}`,
                      workOrderReturnTo,
                      "Back to Work Order",
                    )}
                    style={{ color: "#1d4ed8", fontWeight: 700 }}
                  >
                    {workOrder.commercial_offer_code
                      ? offerVersionLabel(workOrder.commercial_offer_code, workOrder.commercial_offer_version_number)
                      : workOrder.commercial_offer_public_id}
                  </a>
                </DetailRow>
                <DetailRow label="Source offer status">{formatStatusLabel(workOrder.source_offer_status_code)}</DetailRow>
              </dl>
              <p style={{ color: "#6b7280", marginBottom: 0 }}>
                {workOrder.source_offer_status_code === "ACCEPTED"
                  ? "The source Commercial Offer was Accepted / awarded when this Work Order was created."
                  : `When this Work Order was created, the source Commercial Offer status was ${formatStatusLabel(workOrder.source_offer_status_code)}.`}
              </p>
            </SectionCard>

            <SectionCard title="Customer and enquiry">
              <dl style={COMPACT_DETAIL_GRID_STYLE}>
                <DetailRow label="Opportunity">
                  <a
                    href={hrefWithReturnTarget(
                      `/opportunities/${workOrder.opportunity_public_id}`,
                      workOrderReturnTo,
                      "Back to Work Order",
                    )}
                    style={{ color: "#1d4ed8", fontWeight: 700 }}
                  >
                    {linkedNames.opportunity ?? "Open Opportunity"}
                  </a>
                  <div>
                    <ReferenceText>{workOrder.opportunity_public_id}</ReferenceText>
                  </div>
                </DetailRow>
                <DetailRow label="Account">
                  {workOrder.account_public_id ? (
                    <a
                      href={hrefWithReturnTarget(
                        `/accounts/${workOrder.account_public_id}`,
                        workOrderReturnTo,
                        "Back to Work Order",
                      )}
                      style={{ color: "#1d4ed8", fontWeight: 700 }}
                    >
                      {linkedNames.account ?? "Open Account"}
                    </a>
                  ) : "-"}
                  {workOrder.account_public_id ? (
                    <div>
                      <ReferenceText>{workOrder.account_public_id}</ReferenceText>
                    </div>
                  ) : null}
                </DetailRow>
              </dl>
            </SectionCard>
          </div>

          <SectionCard title="How this Work Order was created">
            <p style={{ marginTop: 0 }}>
              This Work Order was created once, on purpose, from the accepted Commercial Offer. A Work Order is never
              created automatically.
            </p>
            <dl style={COMPACT_DETAIL_GRID_STYLE}>
              <DetailRow label="Created at">{formatDateTime(workOrder.created_at)}</DetailRow>
              <DetailRow label="Created by">{displayValue(workOrder.created_by_display_name ?? workOrder.created_by)}</DetailRow>
            </dl>
            {access.canViewEvents ? (
              <>
                {page.handoffEvents.error ? <p className="text-danger">{page.handoffEvents.error}</p> : null}
                {page.handoffEvents.loading ? <p>Loading business event history...</p> : null}
                {!page.handoffEvents.loading && page.handoffEvents.entries.length > 0 ? (
                  <div style={{ display: "grid", gap: "8px", marginTop: "10px" }}>
                    {page.handoffEvents.entries.map((event) => (
                      <article key={event.public_id} style={{ padding: "10px 12px", border: "1px solid #ddd", background: "#fff" }}>
                        <strong>{event.event_name}</strong>
                        <div style={{ color: "#6b7280" }}>{formatDateTime(event.event_timestamp)}</div>
                        {event.reason ? <p style={{ margin: "6px 0 0 0" }}>{event.reason}</p> : null}
                      </article>
                    ))}
                  </div>
                ) : null}
                {!page.handoffEvents.loading && !page.handoffEvents.error && page.handoffEvents.entries.length === 0 ? (
                  <p style={{ color: "#6b7280" }}>No business event history was found for this Work Order.</p>
                ) : null}
              </>
            ) : (
              <p style={{ color: "#6b7280" }}>
                The full audit history is visible to Admin and Management roles only. Everyone who can see this
                Work Order can see when it was created and by whom.
              </p>
            )}
          </SectionCard>
          </SectionGroup>

          <SectionGroup id="wo-lines" title="Lines" tone="amber">
          <SectionCard title="Work Order lines">
            <p style={{ marginTop: 0 }}>
              These lines were copied from the accepted offer's lines when the Work Order was created. Each keeps a link to the offer
              line it came from, shown in the last column.
            </p>
            {lines.length > 0 ? (
              <div className="data-table-wrap" style={{ marginTop: 0 }}>
                <table className="data-table data-table-wide">
                  <thead>
                    <tr>
                      <th>Line</th>
                      <th>Scope / description</th>
                      <th>Category</th>
                      <th>Qty / UOM</th>
                      <th>Rate</th>
                      <th>Amount</th>
                      <th>Source Commercial Offer line</th>
                      <th>Site and billing</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lines.map((line) => (
                      <tr key={line.public_id}>
                        <td>{line.line_number}</td>
                        <td>{line.scope_description}</td>
                        <td>{displayValue(line.equipment_service_category)}</td>
                        <td>{line.quantity} {line.uom}</td>
                        <td>{formatMoney(line.rate_amount, line.currency_code)}</td>
                        <td>{formatMoney(line.line_amount, line.currency_code)}</td>
                        <td>
                          {line.source_offer_line_public_id ? (
                            <>
                              <div>
                                {workOrder.commercial_offer_code
                                  ? `${offerVersionLabel(workOrder.commercial_offer_code, workOrder.commercial_offer_version_number)} `
                                  : ""}
                                {line.source_offer_line_number != null
                                  ? `line ${line.source_offer_line_number}`
                                  : "line (number unavailable)"}
                              </div>
                              <ReferenceText>{line.source_offer_line_public_id}</ReferenceText>
                            </>
                          ) : "-"}
                        </td>
                        <td>
                          {(() => {
                            const detail = lineDetails.entries.find((item) => item.work_order_line_public_id === line.public_id);
                            const terms = billingTerms.entries.find((item) => item.work_order_line_public_id === line.public_id);
                            const currentBasis = billingBasisLabel(
                              terms?.periods.find((period) => period.period_number === terms.current_period_number)?.billing_uom_code,
                            );
                            return (
                              <>
                                {detail?.site_address ? <div>{detail.site_address.city}</div> : null}
                                {currentBasis ? <div>Billed by {currentBasis.toLowerCase()}</div> : null}
                                <span className="status-badge">{missingItemsText(detail)}</span>
                                <div style={{ marginTop: "4px" }}>
                                  <span className="status-badge">{missingTermsText(terms)}</span>
                                </div>
                              </>
                            );
                          })()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p>No Work Order lines were found.</p>}
          </SectionCard>
          {lines.length > 0 ? (
            <WorkOrderLineDetailsSection
              workOrderPublicId={workOrder.public_id}
              accountPublicId={workOrder.account_public_id ?? null}
              accountHref={
                workOrder.account_public_id
                  ? hrefWithReturnTarget(`/accounts/${workOrder.account_public_id}`, workOrderReturnTo, "Back to Work Order")
                  : null
              }
              lines={lines}
              details={lineDetails.entries}
              detailsLoaded={lineDetails.loadedFor === workOrder.public_id}
              detailsError={page.lineDetailsError}
              canEdit={access.canEditLineDetails}
              isClosed={workOrder.work_order_status_code === "CLOSED"}
              token={getToken()}
              loadGeneration={page.generation}
              onSaved={(saved, generation) => dispatch({ type: "line-detail-saved", generation, detail: saved })}
            />
          ) : null}
          {lines.length > 0 ? (
            <WorkOrderBillingTermsSection
              workOrderPublicId={workOrder.public_id}
              lines={lines}
              terms={billingTerms.entries}
              termsLoaded={billingTerms.loadedFor === workOrder.public_id}
              termsError={page.billingTermsError}
              canEdit={access.canEditBillingTerms}
              isClosed={workOrder.work_order_status_code === "CLOSED"}
              token={getToken()}
              loadGeneration={page.generation}
              onApplied={(entry, generation) => dispatch({ type: "billing-terms-applied", generation, entry })}
              contractPeriod={page.contractPeriod}
              onAllApplied={(entries, generation) => dispatch({ type: "billing-terms-replaced", generation, entries })}
            />
          ) : null}
          </SectionGroup>

          <SectionGroup id="wo-resources" title="Resources needed" tone="teal" description="The machines and crew each line needs on site.">
            <WorkOrderResourceRequirementsSection
              workOrderPublicId={workOrder.public_id}
              lines={lines}
              canWrite={access.canWriteRequirements}
              isClosed={workOrder.work_order_status_code === "CLOSED"}
              token={getToken()}
              loadGeneration={page.generation}
            />
          </SectionGroup>

          <SectionGroup
            id="wo-machines"
            title="Machines allocated"
            tone="teal"
            description="Every machine allocated to this Work Order, and what became of it: its allocation history. Before release, allocated machines are held for it."
          >
            <AllocationsSection
              title="Allocations"
              filter="work_order_public_id"
              recordPublicId={workOrder.public_id}
              hide={["work-order"]}
              returnTo={{ href: `/work-orders/${workOrder.public_id}`, label: "Back to the Work Order" }}
              empty="No machine has been allocated to this Work Order yet. Allocate one from a line's requirement."
            />
          </SectionGroup>

          <SectionGroup id="wo-changes" title="Changes after award" tone="violet" description="Extra or changed work the customer asked for after the award.">
          <SectionCard title="Related Commercial Offers">
            <p style={{ marginTop: 0 }}>
              Supplementary Offers and Change Quotations linked to this Work Order are separate Commercial Offer
              series with their own independent lifecycle. Creating or accepting one does <strong>not</strong> mean
              this Work Order has been changed; a change to the Work Order is recorded as a Work Order Amendment.
            </p>
            {page.relatedOffers.error ? <p className="text-danger">{page.relatedOffers.error}</p> : null}
            {page.relatedOffers.loading ? <p>Loading related Commercial Offers...</p> : null}
            {page.relatedOffers.entries.length > 0 ? (
              <div style={{ display: "grid", gap: "10px" }}>
                {page.relatedOffers.entries.map((related) => (
                  <article key={related.public_id} style={{ padding: "10px 12px", border: "1px solid #ddd", background: "#fff" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                      <strong>{related.offer_code} - {offerPurposeLabel(related.offer_purpose)}</strong>
                      <span style={{ fontWeight: 700 }}>{formatStatusLabel(related.offer_status_code)}</span>
                    </div>
                    <p style={{ margin: "6px 0 0 0", color: "#6b7280" }}>{displayValue(related.customer_request_summary)}</p>
                    <a
                      href={hrefWithReturnTarget(`/commercial-offers/${related.public_id}`, workOrderReturnTo, "Back to Work Order")}
                      style={{ ...BUTTON_STYLE, marginTop: "8px" }}
                    >
                      Open
                    </a>
                  </article>
                ))}
              </div>
            ) : (
              !page.relatedOffers.loading && <p>No Supplementary Offer or Change Quotation is linked to this Work Order yet.</p>
            )}
            {access.canCreateRelatedOffer ? (
              <p style={{ marginTop: "12px", display: "flex", gap: "12px", flexWrap: "wrap" }}>
                <a
                  href={`/commercial-offers/${workOrder.commercial_offer_public_id}/related-offers/new?purpose=SUPPLEMENTARY`}
                  style={BUTTON_STYLE}
                >
                  Create Supplementary Offer
                </a>
                <a
                  href={`/commercial-offers/${workOrder.commercial_offer_public_id}/related-offers/new?purpose=CHANGE_QUOTATION`}
                  style={BUTTON_STYLE}
                >
                  Create Change Quotation
                </a>
              </p>
            ) : null}
          </SectionCard>

          <SectionCard title="Work Order Amendments">
            <p style={{ marginTop: 0 }}>
              A Work Order Amendment records a customer-requested administrative or commercial change as an
              intake/review record only. Recording, reviewing or validating an amendment does <strong>not</strong>{" "}
              change this Work Order or any of its lines above. Applying an amendment to the Work Order is not built
              yet.
            </p>
            {page.amendments.error ? <p className="text-danger">{page.amendments.error}</p> : null}
            {page.amendments.loading ? <p>Loading Work Order Amendments...</p> : null}
            {page.amendments.entries.length > 0 ? (
              <div style={{ display: "grid", gap: "10px" }}>
                {page.amendments.entries.map((amendment) => (
                  <article key={amendment.public_id} style={{ padding: "10px 12px", border: "1px solid #ddd", background: "#fff" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                      <strong>
                        Amendment #{amendment.amendment_sequence_no} - {amendmentTypeLabel(amendment.amendment_type_code)}
                      </strong>
                      <span className="status-badge">{formatStatusLabel(amendment.amendment_status_code)}</span>
                    </div>
                    <dl style={{ ...COMPACT_DETAIL_GRID_STYLE, marginTop: "8px" }}>
                      <DetailRow label="Customer amendment reference">{displayValue(amendment.customer_amendment_reference)}</DetailRow>
                      <DetailRow label="Received date">{formatDateOnly(amendment.received_date)}</DetailRow>
                      <DetailRow label="Effective date">{formatDateOnly(amendment.effective_date)}</DetailRow>
                      {amendment.related_commercial_offer_code ? (
                        <DetailRow label="Commercial basis">
                          {amendment.related_commercial_offer_code} ({offerPurposeLabel(amendment.related_commercial_offer_purpose || "")},{" "}
                          {formatStatusLabel(amendment.related_commercial_offer_status_code)})
                        </DetailRow>
                      ) : null}
                    </dl>
                    <p style={{ margin: "8px 0 0 0", color: "#374151" }}>{amendment.amendment_reason}</p>
                    <a
                      href={hrefWithReturnTarget(
                        `/work-orders/${workOrder.public_id}/amendments/${amendment.public_id}`,
                        workOrderReturnTo,
                        "Back to Work Order",
                      )}
                      style={{ ...BUTTON_STYLE, marginTop: "10px" }}
                    >
                      Open
                    </a>
                  </article>
                ))}
              </div>
            ) : (
              !page.amendments.loading && <p>No Work Order Amendment has been recorded yet.</p>
            )}
            {access.canCreateAmendment ? (
              <p style={{ marginTop: "12px" }}>
                <a href={`/work-orders/${workOrder.public_id}/amendments/new`} style={BUTTON_STYLE}>
                  Record Work Order Amendment
                </a>
              </p>
            ) : null}
          </SectionCard>
          </SectionGroup>

          <SectionGroup id="wo-later" title="Not in this version yet" tone="slate">
          <SectionCard title="Later steps">
            <p style={{ marginTop: 0, color: "#6b7280" }}>
              The Hiring or Transportation module will add these steps. None of them are built yet:
            </p>
            <ul>
              <li>Setting the customer up in Finance, with Finance approval.</li>
              <li>The document checklist for each line.</li>
              <li>Releasing the Work Order to Ops.</li>
              <li>Hired machines and vendors, crew, gate passes, fuel and logistics, and running the work. PBL's own machines are already allocated from each line's requirement (Machines allocated, above).</li>
              <li>Log sheets, billing, invoice support and profitability.</li>
            </ul>
          </SectionCard>
          </SectionGroup>
        </div>
      ) : null}
    </section>
  );
}
