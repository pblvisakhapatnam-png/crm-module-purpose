import { FormEvent, ReactNode, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import InteractionLog from "../../components/InteractionLog";
import { PageHeader, ReferenceText, SectionCard, SectionGroup, SectionIndex, StatusBadge } from "../../components/PageLayout";
import DateInput from "../../components/DateInput";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { readSafeReturnTarget, type ReturnTarget } from "../../components/returnTarget";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";

const OPPORTUNITY_DETAIL_BASE_PATH = "/api/opportunities";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const VIEWED_OPPORTUNITY_IDS_KEY = "pbl_viewed_opportunity_ids_this_session";
const OPPORTUNITY_VIEWED_EVENT = "pbl-opportunity-viewed";
const EVENT_VIEW_ROLES = ["ADMIN", "MANAGEMENT_READ_ONLY"];
const OPPORTUNITY_WORK_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];

const OPPORTUNITY_STAGE_FLOW = [
  "NEW",
  "NEEDS_REVIEW",
  "QUALIFIED",
  "QUOTE_PENDING",
  "ON_HOLD",
  "WON",
  "LOST",
  "CLOSED",
] as const;

const OPPORTUNITY_STAGE_UPDATE_OPTIONS = [
  "NEW",
  "NEEDS_REVIEW",
  "QUALIFIED",
  "QUOTE_PENDING",
  "ON_HOLD",
  "LOST",
] as const;

const OPPORTUNITY_SOURCE_OPTIONS = [
  { value: "manual", label: "Manual" },
  { value: "rfq", label: "RFQ" },
  { value: "tender", label: "Tender" },
  { value: "repeat_enquiry", label: "Repeat enquiry" },
  { value: "account_review", label: "Account review" },
  { value: "external_intelligence", label: "Reviewed external intelligence" },
  { value: "other", label: "Other" },
] as const;

const SOURCE_LABELS: Record<string, string> = {
  manual: "Manual",
  lead_conversion: "Lead conversion",
  rfq: "RFQ",
  tender: "Tender",
  repeat_enquiry: "Repeat enquiry",
  account_review: "Account review",
  external_intelligence: "Reviewed external intelligence",
  other: "Other",
};

type Opportunity = {
  public_id: string;
  opportunity_name: string;
  opportunity_source: string;
  source_reference?: string | null;
  account_public_id?: string | null;
  source_lead_public_id?: string | null;
  customer_requirement_summary?: string | null;
  estimated_value?: string | number | null;
  expected_close_date?: string | null;
  opportunity_status_code: string;
  owner_user_public_id?: string | null;
  owner_display_name?: string | null;
  created_by?: string | null;
  created_by_display_name?: string | null;
  created_at: string;
  updated_at: string;
};

type Account = {
  public_id: string;
  account_name: string;
  legal_name?: string | null;
  account_status_code: string;
  qualification_source?: string | null;
};

type OpportunityCommercialOfferSummary = {
  public_id: string;
  offer_code: string;
  offer_title?: string | null;
  offer_status_code: string;
  offer_purpose: string;
  base_offer_public_id?: string | null;
  base_offer_code?: string | null;
};

const COMMERCIAL_OFFER_PURPOSE_LABELS: Record<string, string> = {
  BASE: "Base Offer",
  SUPPLEMENTARY: "Supplementary Offer",
  CHANGE_QUOTATION: "Change Quotation",
};

function offerPurposeLabel(offerPurpose: string): string {
  return COMMERCIAL_OFFER_PURPOSE_LABELS[offerPurpose] || offerPurpose;
}

type OpportunityEvent = {
  public_id?: string | null;
  event_name?: string | null;
  record_type?: string | null;
  record_public_id?: string | null;
};

type OpportunityUpdatedResponse = {
  opportunity: Opportunity;
  events: OpportunityEvent[];
};

type OpportunityAccountRepairResponse = {
  opportunity: Opportunity;
  account: Account;
  events: OpportunityEvent[];
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
  canWorkOpportunity: boolean;
};

type EditForm = {
  opportunity_name: string;
  opportunity_source: string;
  source_reference: string;
  customer_requirement_summary: string;
  estimated_value: string;
  expected_close_date: string;
  opportunity_status_code: string;
};

type MinimalAccountForm = {
  account_name: string;
  legal_name: string;
  segment: string;
  industry: string;
  source_remarks: string;
};

function emptyEditForm(): EditForm {
  return {
    opportunity_name: "",
    opportunity_source: "manual",
    source_reference: "",
    customer_requirement_summary: "",
    estimated_value: "",
    expected_close_date: "",
    opportunity_status_code: "NEW",
  };
}

function emptyMinimalAccountForm(opportunityName = ""): MinimalAccountForm {
  return {
    account_name: opportunityName,
    legal_name: "",
    segment: "",
    industry: "",
    source_remarks: "Created as a minimal/provisional Account for Opportunity Account repair.",
  };
}

function formFromOpportunity(opportunity: Opportunity): EditForm {
  return {
    opportunity_name: opportunity.opportunity_name ?? "",
    opportunity_source: opportunity.opportunity_source ?? "manual",
    source_reference: opportunity.source_reference ?? "",
    customer_requirement_summary: opportunity.customer_requirement_summary ?? "",
    estimated_value: opportunity.estimated_value === null || opportunity.estimated_value === undefined ? "" : String(opportunity.estimated_value),
    expected_close_date: opportunity.expected_close_date ?? "",
    opportunity_status_code: OPPORTUNITY_STAGE_UPDATE_OPTIONS.includes(opportunity.opportunity_status_code as typeof OPPORTUNITY_STAGE_UPDATE_OPTIONS[number])
      ? opportunity.opportunity_status_code
      : "NEW",
  };
}

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

function hasAnyRole(roleCodes: string[], allowedRoles: string[]): boolean {
  return roleCodes.some((role) => allowedRoles.includes(role));
}

function readPageAccess(): PageAccess {
  const token = getToken();
  if (!token) {
    return { status: "no_token", roleCodes: [], canViewEvents: false, canWorkOpportunity: false };
  }

  const payload = decodeTokenPayload(token);
  if (!payload) {
    return { status: "invalid_token", roleCodes: [], canViewEvents: false, canWorkOpportunity: false };
  }

  const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp ?? 0);
  if (exp > 0 && exp * 1000 < Date.now()) {
    clearPrototypeSession();
    return { status: "expired", roleCodes: [], canViewEvents: false, canWorkOpportunity: false };
  }

  const roleCodes = Array.isArray(payload.role_codes)
    ? payload.role_codes.filter((role): role is string => typeof role === "string")
    : [];

  return {
    status: "allowed",
    roleCodes,
    canViewEvents: hasAnyRole(roleCodes, EVENT_VIEW_ROLES),
    canWorkOpportunity: hasAnyRole(roleCodes, OPPORTUNITY_WORK_ROLES),
  };
}

function readViewedOpportunityIds(): string[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.sessionStorage.getItem(VIEWED_OPPORTUNITY_IDS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : [];
  } catch {
    return [];
  }
}

function markOpportunityViewed(publicId: string) {
  if (typeof window === "undefined") return;

  const viewed = new Set(readViewedOpportunityIds());
  viewed.add(publicId);
  window.sessionStorage.setItem(VIEWED_OPPORTUNITY_IDS_KEY, JSON.stringify(Array.from(viewed)));
  window.dispatchEvent(new Event(OPPORTUNITY_VIEWED_EVENT));
}

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "-";
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
  return date.toLocaleDateString("en-IN", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return numeric.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatStatusLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function formatSourceLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return SOURCE_LABELS[value] ?? formatStatusLabel(value);
}

function opportunityDetailErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to view this Opportunity.";
  if (status === 404) return "Opportunity not found.";
  return `Could not load Opportunity. HTTP ${status}.`;
}

async function opportunityUpdateErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role can view this Opportunity but cannot update it.";
  if (response.status === 404) return "Opportunity not found.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return `Could not update Opportunity. HTTP ${response.status}.`;
}

async function opportunityAccountRepairErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "Your role can view this Opportunity but cannot link an Account.";
  if (response.status === 404) return "Opportunity or selected Account not found.";

  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Use generic message below.
  }

  return "Could not link the Account. Please check the form and try again.";
}

function accessMessage(access: PageAccess): string {
  if (access.status === "checking") return "Checking your access...";
  if (access.status === "no_token") return "Sign in to view this Opportunity.";
  if (access.status === "expired") return "Sign in again because the current session has expired.";
  if (access.status === "invalid_token") return "Sign in again because your session could not be read.";
  if (access.canWorkOpportunity) {
    return "You can update this Opportunity and move it through its early stages.";
  }
  return "You can view this Opportunity, but your role cannot change it.";
}

function hasLinkedAccount(opportunity: Opportunity): boolean {
  return Boolean(opportunity.account_public_id && opportunity.account_public_id.trim().length > 0);
}

function hasSourceLead(opportunity: Opportunity): boolean {
  return Boolean(opportunity.source_lead_public_id && opportunity.source_lead_public_id.trim().length > 0);
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

const REPAIR_FORM_STYLE = {
  display: "grid",
  gap: "8px",
  padding: "12px",
  border: "1px solid #d8e0e8",
  borderRadius: "8px",
  background: "#ffffff",
} as const;

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt style={{ color: "#6b7280", fontWeight: 700 }}>{label}</dt>
      <dd style={{ margin: 0, minWidth: 0, overflowWrap: "anywhere", wordBreak: "break-word" }}>{children}</dd>
    </>
  );
}

export default function OpportunityDetailPage() {
  const params = useParams<{ opportunityId: string }>();
  const opportunityId = params?.opportunityId;
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [repairingAccount, setRepairingAccount] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<EditForm>(emptyEditForm());
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [selectedAccountPublicId, setSelectedAccountPublicId] = useState("");
  const [minimalAccountForm, setMinimalAccountForm] = useState<MinimalAccountForm>(emptyMinimalAccountForm());
  const [linkAccountMessage, setLinkAccountMessage] = useState("");
  const [linkAccountError, setLinkAccountError] = useState("");
  const [minimalAccountMessage, setMinimalAccountMessage] = useState("");
  const [minimalAccountError, setMinimalAccountError] = useState("");
  const [lastEvents, setLastEvents] = useState<OpportunityEvent[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [pageAccess, setPageAccess] = useState<PageAccess>({
    status: "checking",
    roleCodes: [],
    canViewEvents: false,
    canWorkOpportunity: false,
  });
  const [returnTarget, setReturnTarget] = useState<ReturnTarget>({
    href: "/opportunities",
    label: "Back to Opportunities",
  });
  const [commercialOffers, setCommercialOffers] = useState<OpportunityCommercialOfferSummary[]>([]);
  const [commercialOffersLoading, setCommercialOffersLoading] = useState(false);
  const [commercialOffersError, setCommercialOffersError] = useState("");

  async function loadAccountsForRepair() {
    const token = getToken();
    if (!token) {
      setLinkAccountError(SIGN_IN_FIRST);
      setMinimalAccountError(SIGN_IN_FIRST);
      return;
    }

    setLoadingAccounts(true);
    setLinkAccountError("");
    setMinimalAccountError("");

    let response: Response;
    try {
      response = await fetch("/api/accounts?limit=100", {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setLinkAccountError("Network error while loading Accounts. Please check your connection and try again.");
      setLoadingAccounts(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setLinkAccountError("Could not load Accounts. Please use Refresh Accounts and try again.");
      setLoadingAccounts(false);
      return;
    }

    const data = (await response.json()) as Account[];
    setAccounts(data);
    setLoadingAccounts(false);
  }

  async function loadCommercialOffersForOpportunity(publicId: string, tokenOverride?: string) {
    setCommercialOffersError("");
    const token = tokenOverride ?? getToken();
    if (!token) {
      setCommercialOffers([]);
      return;
    }

    setCommercialOffersLoading(true);
    let response: Response;
    try {
      response = await fetch(`/api/commercial-offers?limit=100&opportunity_public_id=${encodeURIComponent(publicId)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setCommercialOffers([]);
      setCommercialOffersError("Network error while loading Commercial Offers for this Opportunity.");
      setCommercialOffersLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setCommercialOffers([]);
      setCommercialOffersError(`Commercial Offers could not be loaded. HTTP ${response.status}.`);
      setCommercialOffersLoading(false);
      return;
    }

    const data = (await response.json()) as OpportunityCommercialOfferSummary[];
    setCommercialOffers(data);
    setCommercialOffersLoading(false);
  }

  async function loadOpportunity(publicId: string) {
    setMessage("");
    setError("");

    const access = readPageAccess();
    setPageAccess(access);

    const token = getToken();
    if (!token) {
      setOpportunity(null);
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);

    let response: Response;
    try {
      response = await fetch(`${OPPORTUNITY_DETAIL_BASE_PATH}/${encodeURIComponent(publicId)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setOpportunity(null);
      setError("Network error while loading this Opportunity. Please check your connection and try again.");
      setLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setOpportunity(null);
      setError(opportunityDetailErrorMessage(response.status));
      setLoading(false);
      return;
    }

    const data = (await response.json()) as Opportunity;
    setOpportunity(data);
    setEditForm(formFromOpportunity(data));
    setMinimalAccountForm(emptyMinimalAccountForm(data.opportunity_name));
    markOpportunityViewed(data.public_id);
    setMessage("Opportunity profile loaded.");
    if (!hasLinkedAccount(data) && access.canWorkOpportunity) {
      void loadAccountsForRepair();
    }
    await loadCommercialOffersForOpportunity(data.public_id, token);
    setLoading(false);
  }

  useEffect(() => {
    function refreshAccess() {
      setPageAccess(readPageAccess());
    }

    setReturnTarget(readSafeReturnTarget("/opportunities", "Back to Opportunities"));
    refreshAccess();

    if (typeof opportunityId === "string" && opportunityId.trim().length > 0) {
      void loadOpportunity(opportunityId);
    }

    window.addEventListener(SESSION_CHANGED_EVENT, refreshAccess);
    window.addEventListener("storage", refreshAccess);
    window.addEventListener("focus", refreshAccess);

    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, refreshAccess);
      window.removeEventListener("storage", refreshAccess);
      window.removeEventListener("focus", refreshAccess);
    };
  }, [opportunityId]);

  function startEditing() {
    if (!opportunity) return;
    setEditForm(formFromOpportunity(opportunity));
    setLastEvents([]);
    setMessage("");
    setError("");
    setIsEditing(true);
  }

  function cancelEditing() {
    if (opportunity) setEditForm(formFromOpportunity(opportunity));
    setIsEditing(false);
    setError("");
  }

  async function handleUpdateSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setError("");
    setLastEvents([]);

    if (!opportunity) {
      setError("Load an Opportunity before updating it.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkOpportunity) {
      setError("Your role can view this Opportunity but cannot update it.");
      return;
    }

    const opportunityName = editForm.opportunity_name.trim();
    if (!opportunityName) {
      setError("Opportunity name is required.");
      return;
    }

    const estimatedValue = editForm.estimated_value.trim();
    if (estimatedValue.length > 0 && Number(estimatedValue) < 0) {
      setError("Estimated value cannot be negative.");
      return;
    }

    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setUpdating(true);

    const payload = {
      opportunity_name: opportunityName,
      opportunity_source: editForm.opportunity_source,
      source_reference: normalizeOptional(editForm.source_reference),
      customer_requirement_summary: normalizeOptional(editForm.customer_requirement_summary),
      estimated_value: normalizeOptional(editForm.estimated_value),
      expected_close_date: normalizeOptional(editForm.expected_close_date),
      opportunity_status_code: editForm.opportunity_status_code,
    };

    let response: Response;
    try {
      response = await fetch(`${OPPORTUNITY_DETAIL_BASE_PATH}/${encodeURIComponent(opportunity.public_id)}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setError("Network error while updating this Opportunity. Please check your connection and try again.");
      setUpdating(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setError(await opportunityUpdateErrorMessage(response));
      setUpdating(false);
      return;
    }

    const data = (await response.json()) as OpportunityUpdatedResponse;
    setOpportunity(data.opportunity);
    setEditForm(formFromOpportunity(data.opportunity));
    setLastEvents(data.events ?? []);
    setMessage("Opportunity updated successfully.");
    setIsEditing(false);
    setUpdating(false);
  }

  async function submitAccountRepair(
    payload: object,
    successPrefix: string,
    setLocalMessage: (value: string) => void,
    setLocalError: (value: string) => void,
  ) {
    if (!opportunity) {
      setLocalError("Load an Opportunity before linking an Account.");
      return;
    }

    const access = readPageAccess();
    setPageAccess(access);
    if (!access.canWorkOpportunity) {
      setLocalError("Your role can view this Opportunity but cannot link an Account.");
      return;
    }

    const token = getToken();
    if (!token) {
      setLocalError(SIGN_IN_FIRST);
      return;
    }

    setRepairingAccount(true);
    setLocalMessage("");
    setLocalError("");
    setLastEvents([]);

    let response: Response;
    try {
      response = await fetch(`${OPPORTUNITY_DETAIL_BASE_PATH}/${encodeURIComponent(opportunity.public_id)}/account-repair`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setLocalError("Network error while linking the Account. Please check your connection and try again.");
      setRepairingAccount(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setLocalError(await opportunityAccountRepairErrorMessage(response));
      setRepairingAccount(false);
      return;
    }

    const data = (await response.json()) as OpportunityAccountRepairResponse;
    setOpportunity(data.opportunity);
    setEditForm(formFromOpportunity(data.opportunity));
    setLastEvents(data.events ?? []);
    setLocalMessage(`${successPrefix}: ${data.account.account_name}. This Opportunity is now linked to it.`);
    setSelectedAccountPublicId("");
    setMinimalAccountForm(emptyMinimalAccountForm(data.opportunity.opportunity_name));
    setRepairingAccount(false);
  }

  async function handleLinkExistingAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLinkAccountMessage("");
    setLinkAccountError("");

    if (!selectedAccountPublicId.trim()) {
      setLinkAccountError("Select an existing Account before linking.");
      return;
    }

    await submitAccountRepair(
      { account_public_id: selectedAccountPublicId },
      "Linked existing Account",
      setLinkAccountMessage,
      setLinkAccountError,
    );
  }

  async function handleCreateMinimalAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMinimalAccountMessage("");
    setMinimalAccountError("");

    const accountName = minimalAccountForm.account_name.trim();
    if (!accountName) {
      setMinimalAccountError("Account name is required.");
      return;
    }

    await submitAccountRepair(
      {
        create_account: {
          account_name: accountName,
          legal_name: normalizeOptional(minimalAccountForm.legal_name),
          segment: normalizeOptional(minimalAccountForm.segment),
          industry: normalizeOptional(minimalAccountForm.industry),
          source_remarks: normalizeOptional(minimalAccountForm.source_remarks),
        },
      },
      "Created and linked a new Account",
      setMinimalAccountMessage,
      setMinimalAccountError,
    );
  }

  const stageStatusIsDeferred = opportunity?.opportunity_status_code === "WON" || opportunity?.opportunity_status_code === "CLOSED";
  const opportunityReturnTo = opportunity ? `/opportunities/${opportunity.public_id}` : "";

  return (
    <section>
      <PageHeader
        eyebrow="Opportunity"
        back={{ href: returnTarget.href, label: returnTarget.label }}
        title={opportunity ? opportunity.opportunity_name : "Opportunity"}
        badges={
          opportunity ? (
            <StatusBadge
              code={opportunity.opportunity_status_code}
              label={formatStatusLabel(opportunity.opportunity_status_code)}
            />
          ) : null
        }
        actions={
          <>
            <button
              type="button"
              onClick={() => {
                if (typeof opportunityId === "string") void loadOpportunity(opportunityId);
              }}
              disabled={loading || typeof opportunityId !== "string"}
            >
              {loading ? "Loading..." : "Refresh profile"}
            </button>
            {pageAccess.canWorkOpportunity && opportunity ? (
              <button type="button" onClick={startEditing} disabled={loading || updating || isEditing}>
                Edit Opportunity / Stage
              </button>
            ) : null}
            {pageAccess.canWorkOpportunity && opportunity ? (
              <button
                type="button"
                onClick={() => {
                  window.location.href = `/commercial-offers/new?opportunityId=${encodeURIComponent(opportunity.public_id)}`;
                }}
                disabled={loading || updating}
              >
                Create Commercial Offer
              </button>
            ) : null}
          </>
        }
      >
        {pageAccess.canWorkOpportunity ? null : <p className="helper-text">{accessMessage(pageAccess)}</p>}
        {message ? <p className="text-success">{message}</p> : null}
        {error ? <p className="text-danger">{error}</p> : null}
      </PageHeader>

      {lastEvents.length > 0 ? (
        <div style={{ marginTop: "12px", padding: "12px", border: "1px solid #bbf7d0", borderRadius: "8px", background: "#f0fdf4" }}>
          Saved. This change is recorded in the audit trail.
        </div>
      ) : null}

      {opportunity ? (
        <>
          <SectionIndex
            items={[
              { id: "opportunity-summary", label: "The opportunity" },
              { id: "opportunity-customer", label: "Customer and source" },
              { id: "opportunity-offers", label: "Commercial Offers" },
              { id: "opportunity-follow-up", label: "Follow-up" },
              { id: "opportunity-record", label: "Record details" },
            ]}
          />

          <SectionGroup
            id="opportunity-summary"
            title="The opportunity"
            tone="blue"
            description="What the customer needs and where this Opportunity stands."
          >
            {isEditing ? (
              <SectionCard title="Edit Opportunity and stage">
                <form onSubmit={handleUpdateSubmit} style={{ display: "grid", gap: "14px", maxWidth: "760px" }}>
                  <p style={{ color: "#374151", margin: 0 }}>
                    Won and Closed are not set here. They will be recorded once the award and closure steps are built.
                  </p>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Opportunity name <span className="text-danger">*</span>
                    <input
                      value={editForm.opportunity_name}
                      onChange={(event) => setEditForm((current) => ({ ...current, opportunity_name: event.target.value }))}
                      maxLength={255}
                      required
                      style={{ padding: "8px" }}
                    />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Opportunity source
                    <select
                      value={editForm.opportunity_source}
                      onChange={(event) => setEditForm((current) => ({ ...current, opportunity_source: event.target.value }))}
                      style={{ padding: "8px" }}
                    >
                      {OPPORTUNITY_SOURCE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Source reference
                    <input
                      value={editForm.source_reference}
                      onChange={(event) => setEditForm((current) => ({ ...current, source_reference: event.target.value }))}
                      maxLength={255}
                      style={{ padding: "8px" }}
                    />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Customer requirement summary
                    <textarea
                      value={editForm.customer_requirement_summary}
                      onChange={(event) => setEditForm((current) => ({ ...current, customer_requirement_summary: event.target.value }))}
                      maxLength={4000}
                      rows={5}
                      style={{ padding: "8px" }}
                    />
                  </label>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Estimated value
                      <input
                        value={editForm.estimated_value}
                        onChange={(event) => setEditForm((current) => ({ ...current, estimated_value: event.target.value }))}
                        type="number"
                        min="0"
                        step="0.01"
                        style={{ padding: "8px" }}
                      />
                    </label>

                    <label style={{ display: "grid", gap: "4px" }}>
                      Expected close date
                      <DateInput
                        value={editForm.expected_close_date}
                        onChange={(event) => setEditForm((current) => ({ ...current, expected_close_date: event.target.value }))}
                        style={{ padding: "8px" }}
                      />
                    </label>

                    <label style={{ display: "grid", gap: "4px" }}>
                      Opportunity stage/status
                      <select
                        value={editForm.opportunity_status_code}
                        onChange={(event) => setEditForm((current) => ({ ...current, opportunity_status_code: event.target.value }))}
                        style={{ padding: "8px" }}
                      >
                        {OPPORTUNITY_STAGE_UPDATE_OPTIONS.map((status) => (
                          <option key={status} value={status}>{formatStatusLabel(status)}</option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                    <button type="submit" disabled={updating}>{updating ? "Saving..." : "Save Opportunity"}</button>
                    <button type="button" onClick={cancelEditing} disabled={updating}>Cancel</button>
                  </div>
                </form>
              </SectionCard>
            ) : null}

            <SectionCard title="Summary">
              <dl style={DETAIL_GRID_STYLE}>
                <DetailRow label="Opportunity name">{opportunity.opportunity_name}</DetailRow>
                <DetailRow label="Status">
                  <StatusBadge
                    code={opportunity.opportunity_status_code}
                    label={formatStatusLabel(opportunity.opportunity_status_code)}
                  />
                </DetailRow>
                <DetailRow label="Owner">
                  {displayValue(opportunity.owner_display_name ?? opportunity.owner_user_public_id)}
                </DetailRow>
                <DetailRow label="Source">{formatSourceLabel(opportunity.opportunity_source)}</DetailRow>
                <DetailRow label="Estimated value">{formatMoney(opportunity.estimated_value)}</DetailRow>
                <DetailRow label="Expected close date">{formatDateOnly(opportunity.expected_close_date)}</DetailRow>
              </dl>
            </SectionCard>

            <SectionCard title="Stage path">
              <p style={{ color: "#6b7280" }}>
                The stages an Opportunity moves through. Won and Closed will be recorded once the award and closure steps
                are built.
              </p>
              {stageStatusIsDeferred ? (
                <p className="text-warning">
                  This Opportunity is {formatStatusLabel(opportunity.opportunity_status_code)}. Won and Closed are not
                  managed from this page yet.
                </p>
              ) : null}
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {OPPORTUNITY_STAGE_FLOW.map((status) => {
                  const isCurrent = status === opportunity.opportunity_status_code;
                  const selectableNow = OPPORTUNITY_STAGE_UPDATE_OPTIONS.includes(status as typeof OPPORTUNITY_STAGE_UPDATE_OPTIONS[number]);
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
                      {formatStatusLabel(status)}{isCurrent ? " - current" : ""}{selectableNow ? "" : " - later"}
                    </span>
                  );
                })}
              </div>
            </SectionCard>

            <SectionCard title="Customer requirement">
              <p style={{ whiteSpace: "pre-wrap" }}>{displayValue(opportunity.customer_requirement_summary)}</p>
            </SectionCard>
          </SectionGroup>

          <SectionGroup
            id="opportunity-customer"
            title="Customer and source"
            tone="teal"
            description="The Account this Opportunity belongs to, and where the enquiry came from."
          >
            <div className="opportunity-context-grid">
              <SectionCard title="Customer (Account)">
                {hasLinkedAccount(opportunity) ? (
                  <dl style={COMPACT_DETAIL_GRID_STYLE}>
                    <DetailRow label="Linked Account">
                      <a
                        href={hrefWithReturnTarget(
                          `/accounts/${opportunity.account_public_id}`,
                          opportunityReturnTo,
                          "Back to Opportunity",
                        )}
                        style={LINK_STYLE}
                      >
                        Open Account
                      </a>
                    </DetailRow>
                    <DetailRow label="Reference">
                      <ReferenceText>{opportunity.account_public_id}</ReferenceText>
                    </DetailRow>
                  </dl>
                ) : (
                  <div className="opportunity-account-repair" style={{ display: "grid", gap: "12px" }}>
                    <div
                      className="opportunity-account-warning text-warning"
                      style={{ padding: "12px", border: "1px solid #f59e0b", borderRadius: "8px", background: "#fffbeb" }}
                    >
                      <strong>No Account linked yet.</strong> Link this Opportunity to the customer&apos;s Account. Until then,
                      its Commercial Offers cannot be submitted or accepted, and no Work Order can be created.
                    </div>

                    {pageAccess.canWorkOpportunity ? (
                      <>
                        <div className="opportunity-account-action-row">
                          <button type="button" onClick={loadAccountsForRepair} disabled={loadingAccounts || repairingAccount}>
                            {loadingAccounts ? "Loading Accounts..." : "Refresh Accounts"}
                          </button>
                          <span style={{ color: "#6b7280" }}>
                            Here an Account is a qualified prospect, not yet an active customer in Finance.
                          </span>
                        </div>

                        <form onSubmit={handleLinkExistingAccount} style={REPAIR_FORM_STYLE}>
                          <strong>Link existing Account</strong>
                          <select
                            value={selectedAccountPublicId}
                            onChange={(event) => {
                              setSelectedAccountPublicId(event.target.value);
                              setLinkAccountMessage("");
                              setLinkAccountError("");
                            }}
                            disabled={repairingAccount || loadingAccounts}
                            style={{ padding: "8px" }}
                          >
                            <option value="">Select Account</option>
                            {accounts.map((account) => (
                              <option key={account.public_id} value={account.public_id}>
                                {account.account_name} - {formatStatusLabel(account.account_status_code)}
                              </option>
                            ))}
                          </select>
                          <div style={{ display: "grid", gap: "8px", justifyItems: "start" }}>
                            <button type="submit" disabled={repairingAccount || !selectedAccountPublicId}>
                              {repairingAccount ? "Repairing..." : "Link Account"}
                            </button>
                            {linkAccountMessage ? <p className="text-success" style={{ marginBottom: 0 }}>{linkAccountMessage}</p> : null}
                            {linkAccountError ? <p className="text-danger" style={{ marginBottom: 0 }}>{linkAccountError}</p> : null}
                          </div>
                        </form>

                        <form onSubmit={handleCreateMinimalAccount} style={REPAIR_FORM_STYLE}>
                          <strong>Create a new Account (qualified prospect)</strong>
                          <label style={{ display: "grid", gap: "4px" }}>
                            Account name <span className="text-danger">*</span>
                            <input
                              value={minimalAccountForm.account_name}
                              onChange={(event) => {
                                setMinimalAccountForm((current) => ({ ...current, account_name: event.target.value }));
                                setMinimalAccountMessage("");
                                setMinimalAccountError("");
                              }}
                              maxLength={255}
                              disabled={repairingAccount}
                              style={{ padding: "8px" }}
                            />
                          </label>
                          <label style={{ display: "grid", gap: "4px" }}>
                            Legal name
                            <input
                              value={minimalAccountForm.legal_name}
                              onChange={(event) => {
                                setMinimalAccountForm((current) => ({ ...current, legal_name: event.target.value }));
                                setMinimalAccountMessage("");
                                setMinimalAccountError("");
                              }}
                              maxLength={255}
                              disabled={repairingAccount}
                              style={{ padding: "8px" }}
                            />
                          </label>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "8px" }}>
                            <label style={{ display: "grid", gap: "4px" }}>
                              Segment
                              <input
                                value={minimalAccountForm.segment}
                                onChange={(event) => {
                                  setMinimalAccountForm((current) => ({ ...current, segment: event.target.value }));
                                  setMinimalAccountMessage("");
                                  setMinimalAccountError("");
                                }}
                                maxLength={100}
                                disabled={repairingAccount}
                                style={{ padding: "8px" }}
                              />
                            </label>
                            <label style={{ display: "grid", gap: "4px" }}>
                              Industry
                              <input
                                value={minimalAccountForm.industry}
                                onChange={(event) => {
                                  setMinimalAccountForm((current) => ({ ...current, industry: event.target.value }));
                                  setMinimalAccountMessage("");
                                  setMinimalAccountError("");
                                }}
                                maxLength={100}
                                disabled={repairingAccount}
                                style={{ padding: "8px" }}
                              />
                            </label>
                          </div>
                          <label style={{ display: "grid", gap: "4px" }}>
                            Source remarks
                            <textarea
                              value={minimalAccountForm.source_remarks}
                              onChange={(event) => {
                                setMinimalAccountForm((current) => ({ ...current, source_remarks: event.target.value }));
                                setMinimalAccountMessage("");
                                setMinimalAccountError("");
                              }}
                              maxLength={4000}
                              rows={3}
                              disabled={repairingAccount}
                              style={{ padding: "8px" }}
                            />
                          </label>
                          <div style={{ display: "grid", gap: "8px", justifyItems: "start" }}>
                            <button type="submit" disabled={repairingAccount || minimalAccountForm.account_name.trim().length === 0}>
                              {repairingAccount ? "Repairing..." : "Create and link Account"}
                            </button>
                            {minimalAccountMessage ? <p className="text-success" style={{ marginBottom: 0 }}>{minimalAccountMessage}</p> : null}
                            {minimalAccountError ? <p className="text-danger" style={{ marginBottom: 0 }}>{minimalAccountError}</p> : null}
                          </div>
                        </form>
                      </>
                    ) : (
                      <p style={{ color: "#6b7280" }}>Only Sales and Admin users can link an Account.</p>
                    )}
                  </div>
                )}
                <p style={{ color: "#6b7280" }}>
                  The Account is the customer this Opportunity belongs to. Becoming an active customer in Finance is a
                  later, separate step.
                </p>
              </SectionCard>

              <SectionCard title="Where it came from">
                <dl className="opportunity-context-list" style={{ display: "grid", gap: "8px 12px" }}>
                  <DetailRow label="Source">{formatSourceLabel(opportunity.opportunity_source)}</DetailRow>
                  <DetailRow label="Source reference">{displayValue(opportunity.source_reference)}</DetailRow>
                  <DetailRow label="Source Lead">
                    {hasSourceLead(opportunity) ? (
                      <>
                        <a href={`/leads/${opportunity.source_lead_public_id}`} style={LINK_STYLE}>
                          Open Lead
                        </a>{" "}
                        <ReferenceText>{opportunity.source_lead_public_id}</ReferenceText>
                      </>
                    ) : (
                      "-"
                    )}
                  </DetailRow>
                </dl>
              </SectionCard>
            </div>
          </SectionGroup>

          <SectionGroup
            id="opportunity-offers"
            title="Commercial Offers"
            tone="amber"
            description="Offers prepared for this Opportunity."
          >
            <SectionCard title="Offers for this Opportunity">
              <p style={{ color: "#6b7280" }}>
                Supplementary Offers and Change Quotations are separate offers linked to their Base Offer, not revisions of it.
              </p>
              {commercialOffersError ? <p className="text-danger">{commercialOffersError}</p> : null}
              {commercialOffersLoading ? <p>Loading Commercial Offers...</p> : null}
              {commercialOffers.length > 0 ? (
                <div className="data-table-wrap" style={{ marginTop: "12px" }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Offer</th>
                        <th>Purpose</th>
                        <th>Status</th>
                        <th>Base Offer</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {commercialOffers.map((offer) => (
                        <tr key={offer.public_id} data-testid={`commercial-offer-row-${offer.public_id}`}>
                          <td>
                            {offer.offer_code}
                            <div style={{ color: "#6b7280" }}>{displayValue(offer.offer_title)}</div>
                          </td>
                          <td>
                            <span className="status-badge">{offerPurposeLabel(offer.offer_purpose)}</span>
                          </td>
                          <td>
                            <StatusBadge code={offer.offer_status_code} label={formatStatusLabel(offer.offer_status_code)} />
                          </td>
                          <td>{displayValue(offer.base_offer_code)}</td>
                          <td>
                            <a
                              href={hrefWithReturnTarget(`/commercial-offers/${offer.public_id}`, opportunityReturnTo, "Back to Opportunity")}
                              style={{ color: "#1d4ed8", fontWeight: 700 }}
                            >
                              Open
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                !commercialOffersLoading && <p>No Commercial Offer has been created for this Opportunity yet.</p>
              )}
            </SectionCard>

            <SectionCard title="Commercial readiness">
              <ul>
                <li>Estimated value: {formatMoney(opportunity.estimated_value)}</li>
                <li>Expected close date: {formatDateOnly(opportunity.expected_close_date)}</li>
                <li>Credit-limit checks: not built yet</li>
              </ul>
              {pageAccess.canWorkOpportunity ? (
                <p style={{ marginTop: "12px" }}>
                  <a href={`/commercial-offers/new?opportunityId=${opportunity.public_id}`} style={LINK_STYLE}>
                    Create Commercial Offer for this Opportunity
                  </a>
                </p>
              ) : null}
            </SectionCard>
          </SectionGroup>

          <SectionGroup
            id="opportunity-follow-up"
            title="Follow-up"
            tone="violet"
            description="Calls, emails and meetings about this Opportunity."
          >
            <InteractionLog linkedRecordType="opportunity" linkedRecordPublicId={opportunity.public_id} supportsInheritance />
          </SectionGroup>

          <SectionGroup
            id="opportunity-record"
            title="Record details"
            tone="slate"
            description="Reference, history and what is not built yet."
          >
            <div style={TWO_COLUMN_STYLE}>
              <SectionCard title="Reference and history">
                <p style={{ color: "#6b7280" }}>Times are shown in India time.</p>
                <dl style={COMPACT_DETAIL_GRID_STYLE}>
                  <DetailRow label="Reference">
                    <ReferenceText>{opportunity.public_id}</ReferenceText>
                  </DetailRow>
                  <DetailRow label="Created by">
                    {displayValue(opportunity.created_by_display_name ?? opportunity.created_by)}
                  </DetailRow>
                  <DetailRow label="Created">{formatDateTime(opportunity.created_at)}</DetailRow>
                  <DetailRow label="Updated">{formatDateTime(opportunity.updated_at)}</DetailRow>
                </dl>
                {pageAccess.canViewEvents ? (
                  <p>
                    <a
                      href={`/events?returnTo=${encodeURIComponent(`/opportunities/${opportunity.public_id}`)}&returnLabel=${encodeURIComponent("Back to Opportunity")}`}
                      style={LINK_STYLE}
                    >
                      View recent business events
                    </a>
                  </p>
                ) : (
                  <p style={{ color: "#6b7280" }}>Only Admin and Management Read Only users can view business events.</p>
                )}
              </SectionCard>

              <SectionCard title="Not built yet">
                <ul>
                  <li>Recording Won and Closed outcomes</li>
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
