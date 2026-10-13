import { useEffect, useState } from "react";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";

const PAGE_SIZE = 20;
const OPPORTUNITY_LIST_FETCH_LIMIT = PAGE_SIZE + 1;
const OPPORTUNITY_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const VIEWED_OPPORTUNITY_IDS_KEY = "pbl_viewed_opportunity_ids_this_session";
const OPPORTUNITY_VIEWED_EVENT = "pbl-opportunity-viewed";

function buildOpportunityListPath(offset: number): string {
  const params = new URLSearchParams({
    limit: String(OPPORTUNITY_LIST_FETCH_LIMIT),
    offset: String(offset),
  });
  return `/api/opportunities?${params.toString()}`;
}

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
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

type TokenPayload = {
  role_codes?: unknown;
  exp?: unknown;
};

type CreateAccessStatus = "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token";

type CreateAccess = {
  status: CreateAccessStatus;
  roleCodes: string[];
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
    return { status: "expired", roleCodes: [] };
  }

  const roleCodes = Array.isArray(payload.role_codes)
    ? payload.role_codes.filter((role): role is string => typeof role === "string")
    : [];

  const allowed = roleCodes.some((role) => OPPORTUNITY_CREATE_ROLES.includes(role));
  return { status: allowed ? "allowed" : "denied", roleCodes };
}

function createAccessMessage(status: CreateAccessStatus): string {
  if (status === "no_token") return "Sign in as a Sales or Admin user to create Opportunities.";
  if (status === "expired") return "Sign in again to create Opportunities because the current session has expired.";
  if (status === "invalid_token") return "Sign in again to create Opportunities because the current session is invalid.";
  if (status === "denied") return "Your role can view Opportunities but cannot create or update Opportunities.";
  return "";
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

function storeViewedOpportunityIds(opportunityIds: string[]) {
  if (typeof window === "undefined") return;
  const uniqueOpportunityIds = Array.from(new Set(opportunityIds));
  window.sessionStorage.setItem(VIEWED_OPPORTUNITY_IDS_KEY, JSON.stringify(uniqueOpportunityIds));
}

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "-";
}

function formatStatusLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return numeric.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function opportunityLoadErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to view Opportunities.";
  if (status === 404) return "The Opportunity service is not available right now. Please try again shortly.";
  return `Could not load Opportunities. HTTP ${status}.`;
}

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [hasLoaded, setHasLoaded] = useState(false);
  const [createAccess, setCreateAccess] = useState<CreateAccess>({ status: "checking", roleCodes: [] });
  const [currentOffset, setCurrentOffset] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [viewedOpportunityIds, setViewedOpportunityIds] = useState<string[]>([]);

  async function loadOpportunities(requestedOffset = currentOffset) {
    const nextOffset = Math.max(0, requestedOffset);
    setError("");
    setMessage("");

    const token = getToken();
    if (!token) {
      setOpportunities([]);
      setHasLoaded(false);
      setHasNextPage(false);
      setCurrentOffset(0);
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);

    let response: Response;
    try {
      response = await fetch(buildOpportunityListPath(nextOffset), {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setOpportunities([]);
      setError("Network error while loading Opportunities. Please check your connection and try again.");
      setLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setOpportunities([]);
      setHasLoaded(false);
      setHasNextPage(false);
      setError(opportunityLoadErrorMessage(response.status));
      setLoading(false);
      return;
    }

    const data = (await response.json()) as Opportunity[];
    const visibleOpportunities = data.slice(0, PAGE_SIZE);
    setOpportunities(visibleOpportunities);
    setHasLoaded(true);
    setCurrentOffset(nextOffset);
    setHasNextPage(data.length > PAGE_SIZE);

    if (visibleOpportunities.length === 0) {
      setMessage(nextOffset === 0 ? "No Opportunity records found." : "No Opportunity records found on this page.");
    } else {
      const start = nextOffset + 1;
      const end = nextOffset + visibleOpportunities.length;
      setMessage(`Loaded Opportunity records ${start}-${end}.`);
    }

    setLoading(false);
  }

  useEffect(() => {
    function refreshSessionDrivenState() {
      setCreateAccess(getCreateAccess());
      setViewedOpportunityIds(readViewedOpportunityIds());
    }

    refreshSessionDrivenState();
    void loadOpportunities(0);

    window.addEventListener(SESSION_CHANGED_EVENT, refreshSessionDrivenState);
    window.addEventListener(OPPORTUNITY_VIEWED_EVENT, refreshSessionDrivenState);
    window.addEventListener("storage", refreshSessionDrivenState);
    window.addEventListener("focus", refreshSessionDrivenState);

    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, refreshSessionDrivenState);
      window.removeEventListener(OPPORTUNITY_VIEWED_EVENT, refreshSessionDrivenState);
      window.removeEventListener("storage", refreshSessionDrivenState);
      window.removeEventListener("focus", refreshSessionDrivenState);
    };
  }, []);

  function markOpportunityViewed(publicId: string) {
    const nextViewedOpportunityIds = Array.from(new Set([...viewedOpportunityIds, publicId]));
    setViewedOpportunityIds(nextViewedOpportunityIds);
    storeViewedOpportunityIds(nextViewedOpportunityIds);
    window.dispatchEvent(new Event(OPPORTUNITY_VIEWED_EVENT));
  }

  function isViewedThisSession(publicId: string): boolean {
    return viewedOpportunityIds.includes(publicId);
  }

  const canCreateOpportunity = createAccess.status === "allowed";

  return (
    <section>
      <h2>Opportunities</h2>
      <p>
        An Opportunity is a specific customer requirement you are pursuing, such as an RFQ, enquiry or tender. It comes
        from converting a qualified Lead or is created directly, and Commercial Offers are prepared from it.
      </p>

      <div className="page-actions">
        {canCreateOpportunity ? (
          <a className="button-link" href="/opportunities/new">
            Create Opportunity
          </a>
        ) : null}
        <button type="button" onClick={() => void loadOpportunities(currentOffset)} disabled={loading}>
          {loading ? "Loading..." : "Refresh current page"}
        </button>
      </div>

      {!canCreateOpportunity && createAccess.status !== "checking" ? (
        <p style={{ color: "#6b7280" }}>{createAccessMessage(createAccess.status)}</p>
      ) : null}

      <p style={{ color: "#6b7280", marginTop: "12px" }}>
        Opened Opportunity links are highlighted for this session and reset when you sign out or sign in again.
      </p>

      {message ? <p className="text-success">{message}</p> : null}
      {error ? <p className="text-danger">{error}</p> : null}

      <div className="pagination-row">
        <button
          type="button"
          onClick={() => void loadOpportunities(Math.max(0, currentOffset - PAGE_SIZE))}
          disabled={loading || currentOffset === 0}
        >
          Previous
        </button>
        <span>Page {Math.floor(currentOffset / PAGE_SIZE) + 1}</span>
        <button
          type="button"
          onClick={() => void loadOpportunities(currentOffset + PAGE_SIZE)}
          disabled={loading || !hasNextPage}
        >
          Next
        </button>
      </div>

      {hasLoaded && opportunities.length > 0 ? (
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Opportunity</th>
                <th>Source</th>
                <th>Status</th>
                <th>Estimated value</th>
                <th>Expected close</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {opportunities.map((opportunity) => {
                const viewedThisSession = isViewedThisSession(opportunity.public_id);

                return (
                  <tr key={opportunity.public_id}>
                    <td>
                      <a
                        href={`/opportunities/${opportunity.public_id}`}
                        onClick={() => markOpportunityViewed(opportunity.public_id)}
                        style={{
                          color: viewedThisSession ? "#551a8b" : "#0000ee",
                          fontWeight: 700,
                          textDecoration: "underline",
                        }}
                      >
                        {opportunity.opportunity_name}
                      </a>
                      {viewedThisSession ? (
                        <span style={{ color: "#6b7280", fontSize: "12px", marginLeft: "8px" }}>
                          Viewed this session
                        </span>
                      ) : null}
                    </td>
                    <td>{opportunity.opportunity_source}</td>
                    <td>
                      <span className="status-badge">{formatStatusLabel(opportunity.opportunity_status_code)}</span>
                    </td>
                    <td>{formatMoney(opportunity.estimated_value)}</td>
                    <td>{displayValue(opportunity.expected_close_date)}</td>
                    <td>{formatDateTime(opportunity.updated_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {hasLoaded && !loading && !error && opportunities.length === 0 ? (
        <div className="empty-state">
          No Opportunities found on this page. Convert a qualified Lead or create an Opportunity to add one.
        </div>
      ) : null}
    </section>
  );
}
