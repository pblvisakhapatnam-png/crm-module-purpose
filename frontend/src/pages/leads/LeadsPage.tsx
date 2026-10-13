import { useEffect, useState } from "react";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";

const PAGE_SIZE = 20;
const LEAD_LIST_FETCH_LIMIT = PAGE_SIZE + 1;
const LEAD_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];
const SESSION_CHANGED_EVENT = "pbl-session-changed";

function buildLeadListPath(offset: number): string {
  const params = new URLSearchParams({
    limit: String(LEAD_LIST_FETCH_LIMIT),
    offset: String(offset),
  });
  return `/api/leads?${params.toString()}`;
}

type Lead = {
  public_id: string;
  lead_source: string;
  source_reference?: string | null;
  company_name: string;
  contact_name?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  requirement_summary?: string | null;
  lead_status_code: string;
  assigned_to_user_public_id?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

type TokenPayload = {
  role_codes?: unknown;
  exp?: unknown;
};

type LeadCreateAccessStatus = "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token";

type LeadCreateAccess = {
  status: LeadCreateAccessStatus;
  roleCodes: string[];
};

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
  if (status === "no_token") return "Sign in as a Sales or Admin user to create Leads.";
  if (status === "expired") return "Sign in again to create Leads because the current session has expired.";
  if (status === "invalid_token") return "Sign in again to create Leads because the current session is invalid.";
  if (status === "denied") return "Your role can view Leads but cannot create new Leads.";
  return "";
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

function leadLoadErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to view Leads.";
  if (status === 404) return "The Lead service is not available right now. Please try again shortly.";
  return `Could not load Leads. HTTP ${status}.`;
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [hasLoaded, setHasLoaded] = useState(false);
  const [createAccess, setCreateAccess] = useState<LeadCreateAccess>({ status: "checking", roleCodes: [] });
  const [currentOffset, setCurrentOffset] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);

  async function loadLeads(requestedOffset = currentOffset) {
    const nextOffset = Math.max(0, requestedOffset);
    setError("");
    setMessage("");

    const token = getToken();
    if (!token) {
      setLeads([]);
      setHasLoaded(false);
      setHasNextPage(false);
      setCurrentOffset(0);
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);

    let response: Response;
    try {
      response = await fetch(buildLeadListPath(nextOffset), {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setLeads([]);
      setError("Network error while loading Leads. Please check your connection and try again.");
      setLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setLeads([]);
      setHasLoaded(false);
      setHasNextPage(false);
      setError(leadLoadErrorMessage(response.status));
      setLoading(false);
      return;
    }

    const data = (await response.json()) as Lead[];
    const visibleLeads = data.slice(0, PAGE_SIZE);
    setLeads(visibleLeads);
    setHasLoaded(true);
    setCurrentOffset(nextOffset);
    setHasNextPage(data.length > PAGE_SIZE);

    if (visibleLeads.length === 0) {
      setMessage(nextOffset === 0 ? "No Lead records found." : "No Lead records found on this page.");
    } else {
      const start = nextOffset + 1;
      const end = nextOffset + visibleLeads.length;
      setMessage(`Loaded Lead records ${start}-${end}.`);
    }

    setLoading(false);
  }

  useEffect(() => {
    function refreshCreateAccess() {
      setCreateAccess(getLeadCreateAccess());
    }

    refreshCreateAccess();
    void loadLeads(0);

    window.addEventListener(SESSION_CHANGED_EVENT, refreshCreateAccess);
    window.addEventListener("storage", refreshCreateAccess);
    window.addEventListener("focus", refreshCreateAccess);

    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, refreshCreateAccess);
      window.removeEventListener("storage", refreshCreateAccess);
      window.removeEventListener("focus", refreshCreateAccess);
    };
  }, []);

  const canCreateLead = createAccess.status === "allowed";

  return (
    <section>
      <h2>Leads</h2>
      <p>
        Leads are early sales enquiries. Sales and Admin users can qualify a Lead and convert it into an Account and an
        Opportunity. Duplicate checks and automatic import of enquiries are not built yet.
      </p>

      <div className="page-actions">
        {canCreateLead ? <a className="button-link" href="/leads/new">Create Lead</a> : null}
        <button type="button" onClick={() => void loadLeads(currentOffset)} disabled={loading}>
          {loading ? "Loading..." : "Refresh current page"}
        </button>
      </div>

      {!canCreateLead && createAccess.status !== "checking" ? (
        <p style={{ color: "#6b7280" }}>{leadCreateAccessMessage(createAccess.status)}</p>
      ) : null}

      {message ? <p className="text-success">{message}</p> : null}
      {error ? <p className="text-danger">{error}</p> : null}

      <div className="pagination-row">
        <button
          type="button"
          onClick={() => void loadLeads(Math.max(0, currentOffset - PAGE_SIZE))}
          disabled={loading || currentOffset === 0}
        >
          Previous
        </button>
        <span>Page {Math.floor(currentOffset / PAGE_SIZE) + 1}</span>
        <button
          type="button"
          onClick={() => void loadLeads(currentOffset + PAGE_SIZE)}
          disabled={loading || !hasNextPage}
        >
          Next
        </button>
      </div>

      {hasLoaded && leads.length > 0 ? (
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Source</th>
                <th>Status</th>
                <th>Contact</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.public_id}>
                  <td>
                    <a href={`/leads/${lead.public_id}`} style={{ color: "#1d4ed8", fontWeight: 700, textDecoration: "underline" }}>
                      {lead.company_name}
                    </a>
                    <div style={{ color: "#6b7280", fontSize: "12px" }}>{lead.public_id}</div>
                  </td>
                  <td>{lead.lead_source}</td>
                  <td>
                    <span className="status-badge">{formatStatusLabel(lead.lead_status_code)}</span>
                  </td>
                  <td>
                    {displayValue(lead.contact_name)}
                    <div style={{ color: "#6b7280", fontSize: "12px" }}>{displayValue(lead.contact_phone)}</div>
                  </td>
                  <td>{formatDateTime(lead.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {hasLoaded && !loading && !error && leads.length === 0 ? (
        <div className="empty-state">
          No Leads found on this page.
        </div>
      ) : null}
    </section>
  );
}
