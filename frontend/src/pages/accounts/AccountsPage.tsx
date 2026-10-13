import { useEffect, useState } from "react";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";

const PAGE_SIZE = 20;
const ACCOUNT_LIST_FETCH_LIMIT = PAGE_SIZE + 1;
const ACCOUNT_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];
const VIEWED_ACCOUNT_IDS_KEY = "pbl_viewed_account_ids_this_session";
const ACCOUNT_VIEWED_EVENT = "pbl-account-viewed";
const SESSION_CHANGED_EVENT = "pbl-session-changed";

function buildAccountListPath(offset: number): string {
  const params = new URLSearchParams({
    limit: String(ACCOUNT_LIST_FETCH_LIMIT),
    offset: String(offset),
  });
  return `/api/accounts?${params.toString()}`;
}

type Account = {
  public_id: string;
  party_type: string;
  account_name: string;
  legal_name?: string | null;
  pan?: string | null;
  gstin?: string | null;
  account_status_code: string;
  qualification_source?: string | null;
  account_owner_user_public_id?: string | null;
  account_owner_display_name?: string | null;
  segment?: string | null;
  industry?: string | null;
  source_remarks?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

type TokenPayload = {
  role_codes?: unknown;
  exp?: unknown;
};

type AccountCreateAccessStatus = "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token";

type AccountCreateAccess = {
  status: AccountCreateAccessStatus;
  roleCodes: string[];
};

function clearPrototypeSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("pbl_auth_token");
  window.sessionStorage.removeItem(VIEWED_ACCOUNT_IDS_KEY);
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
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

function getAccountCreateAccess(): AccountCreateAccess {
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

  const allowed = roleCodes.some((role) => ACCOUNT_CREATE_ROLES.includes(role));
  return { status: allowed ? "allowed" : "denied", roleCodes };
}

function accountCreateAccessMessage(status: AccountCreateAccessStatus): string {
  if (status === "no_token") return "Sign in as a Sales or Admin user to create Accounts.";
  if (status === "expired") return "Sign in again to create Accounts because the current session has expired.";
  if (status === "invalid_token") return "Sign in again to create Accounts because the current session is invalid.";
  if (status === "denied") return "Your role can view Accounts but cannot create new Accounts.";
  return "";
}

function readViewedAccountIds(): string[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.sessionStorage.getItem(VIEWED_ACCOUNT_IDS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : [];
  } catch {
    return [];
  }
}

function storeViewedAccountIds(accountIds: string[]) {
  if (typeof window === "undefined") return;
  const uniqueAccountIds = Array.from(new Set(accountIds));
  window.sessionStorage.setItem(VIEWED_ACCOUNT_IDS_KEY, JSON.stringify(uniqueAccountIds));
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

function accountLoadErrorMessage(status: number): string {
  if (status === 401) {
    return SIGN_IN_AGAIN;
  }

  if (status === 403) {
    return "You do not have permission to view Accounts.";
  }

  if (status === 404) {
    return "The Account service is not available right now. Please try again shortly.";
  }

  return `Could not load Accounts (error ${status}). Please try again shortly.`;
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [hasLoaded, setHasLoaded] = useState(false);
  const [createAccess, setCreateAccess] = useState<AccountCreateAccess>({ status: "checking", roleCodes: [] });
  const [currentOffset, setCurrentOffset] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [viewedAccountIds, setViewedAccountIds] = useState<string[]>([]);

  async function loadAccounts(requestedOffset = currentOffset) {
    const nextOffset = Math.max(0, requestedOffset);
    setError("");
    setMessage("");

    const token = getToken();
    if (!token) {
      setAccounts([]);
      setHasLoaded(false);
      setHasNextPage(false);
      setCurrentOffset(0);
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);

    let response: Response;
    try {
      response = await fetch(buildAccountListPath(nextOffset), {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setAccounts([]);
      setError("Could not reach the server while loading Accounts. Please try again shortly.");
      setLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) {
        clearPrototypeSession();
      }

      setAccounts([]);
      setHasLoaded(false);
      setHasNextPage(false);
      setError(accountLoadErrorMessage(response.status));
      setLoading(false);
      return;
    }

    const data = (await response.json()) as Account[];
    const visibleAccounts = data.slice(0, PAGE_SIZE);
    setAccounts(visibleAccounts);
    setHasLoaded(true);
    setCurrentOffset(nextOffset);
    setHasNextPage(data.length > PAGE_SIZE);

    if (visibleAccounts.length === 0) {
      setMessage(nextOffset === 0 ? "No Account records found." : "No Account records found on this page.");
    } else {
      const start = nextOffset + 1;
      const end = nextOffset + visibleAccounts.length;
      setMessage(`Loaded Account records ${start}-${end}.`);
    }

    setLoading(false);
  }

  useEffect(() => {
    function refreshViewedAccountIds() {
      setViewedAccountIds(readViewedAccountIds());
    }

    setCreateAccess(getAccountCreateAccess());
    refreshViewedAccountIds();
    void loadAccounts(0);

    window.addEventListener(ACCOUNT_VIEWED_EVENT, refreshViewedAccountIds);
    window.addEventListener("focus", refreshViewedAccountIds);

    return () => {
      window.removeEventListener(ACCOUNT_VIEWED_EVENT, refreshViewedAccountIds);
      window.removeEventListener("focus", refreshViewedAccountIds);
    };
    // Run once on page open. Pagination and refresh actions call loadAccounts explicitly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function clearList() {
    setAccounts([]);
    setHasLoaded(false);
    setHasNextPage(false);
    setCurrentOffset(0);
    setMessage("");
    setError("");
  }

  function markAccountViewed(publicId: string) {
    const nextViewedAccountIds = Array.from(new Set([...viewedAccountIds, publicId]));
    setViewedAccountIds(nextViewedAccountIds);
    storeViewedAccountIds(nextViewedAccountIds);
    window.dispatchEvent(new Event(ACCOUNT_VIEWED_EVENT));
  }

  function isViewedThisSession(publicId: string): boolean {
    return viewedAccountIds.includes(publicId);
  }

  return (
    <section>
      <h2>Accounts</h2>
      <p>
        Accounts and Qualified Prospects known to PBL. Open an Account to see and update its contacts,
        addresses, PAN / GST, documents and conversations.
      </p>

      <div className="page-actions">
        {createAccess.status === "allowed" ? (
          <a
            className="button-link"
            href="/accounts/new"
          >
            Create Account
          </a>
        ) : createAccess.status !== "checking" ? (
          <span style={{ color: "#555" }}>{accountCreateAccessMessage(createAccess.status)}</span>
        ) : null}
      </div>

      <div className="list-card">
        <h3>Account list</h3>
        <p>
          View recently created Accounts and Qualified Prospects. The list loads automatically for
          the current page and can be refreshed when records are added or changed.
        </p>

        <div className="page-actions">
          <button
            onClick={() => loadAccounts(currentOffset)}
            disabled={loading}
          >
            {loading ? "Loading Accounts..." : "Refresh current page"}
          </button>
          <button
            onClick={() => loadAccounts(Math.max(0, currentOffset - PAGE_SIZE))}
            disabled={loading || currentOffset === 0}
          >
            Previous
          </button>
          <button
            onClick={() => loadAccounts(currentOffset + PAGE_SIZE)}
            disabled={loading || !hasNextPage}
          >
            Next
          </button>
          <button onClick={clearList} disabled={loading}>
            Clear
          </button>
        </div>

        <p style={{ color: "#555", marginTop: "12px" }}>
          Page size: {PAGE_SIZE}. Opened Account links are highlighted for this session and reset when you sign out or sign in again.
        </p>

        {message && <p className="text-success" style={{ marginTop: "16px" }}>{message}</p>}
        {error && <p className="text-danger" style={{ marginTop: "16px" }}>{error}</p>}

        {loading && <p style={{ marginTop: "16px" }}>Loading Accounts...</p>}

        {!loading && !error && hasLoaded && accounts.length === 0 ? (
          <div className="empty-state">
            No Accounts found yet.
          </div>
        ) : null}

        {!loading && !error && !hasLoaded && accounts.length === 0 ? (
          <div className="empty-state">Accounts load automatically when you are signed in.</div>
        ) : null}

        {!loading && accounts.length > 0 ? (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>
                    Account
                  </th>
                  <th>
                    Status
                  </th>
                  <th>
                    Qualification source
                  </th>
                  <th>
                    Segment / Industry
                  </th>
                  <th>
                    Owner
                  </th>
                  <th>
                    Created
                  </th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => {
                  const viewedThisSession = isViewedThisSession(account.public_id);

                  return (
                    <tr key={account.public_id}>
                      <td>
                        <a
                          href={`/accounts/${account.public_id}`}
                          onClick={() => markAccountViewed(account.public_id)}
                          style={{
                            fontWeight: 700,
                            color: viewedThisSession ? "#551a8b" : "#0000ee",
                          }}
                        >
                          {account.account_name}
                        </a>
                        {viewedThisSession ? (
                          <span style={{ color: "#6b7280", fontSize: "12px", marginLeft: "8px" }}>
                            Viewed this session
                          </span>
                        ) : null}
                        <div style={{ color: "#555", fontSize: "12px", marginTop: "4px" }}>
                          {displayValue(account.legal_name)}
                        </div>
                        <div style={{ color: "#777", fontSize: "12px", marginTop: "4px" }}>
                          {account.public_id}
                        </div>
                      </td>
                      <td>
                        <span className="status-badge">{formatStatusLabel(account.account_status_code)}</span>
                      </td>
                      <td>
                        {displayValue(account.qualification_source)}
                      </td>
                      <td>
                        {displayValue(account.segment)} / {displayValue(account.industry)}
                      </td>
                      <td>
                        {displayValue(account.account_owner_display_name ?? account.account_owner_user_public_id)}
                      </td>
                      <td>
                        {formatDateTime(account.created_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <div className="content-card">
        <h3>Not in this version yet</h3>
        <ul>
          <li>Searching and filtering the Account list</li>
          <li>Editing an Account's name, legal name or status</li>
          <li>Checking for duplicate Accounts</li>
        </ul>
      </div>
    </section>
  );
}


