import { useEffect, useState } from "react";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { offerVersionLabel } from "../../components/offerVersion";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";

const PAGE_SIZE = 20;
const COMMERCIAL_OFFER_LIST_FETCH_LIMIT = PAGE_SIZE + 1;
const COMMERCIAL_OFFER_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];
const SESSION_CHANGED_EVENT = "pbl-session-changed";

type CommercialOffer = {
  public_id: string;
  offer_code: string;
  opportunity_public_id: string;
  account_public_id?: string | null;
  offer_title?: string | null;
  offer_mode: string;
  offer_type: string;
  offer_status_code: string;
  offer_value?: string | number | null;
  currency_code: string;
  offer_date?: string | null;
  valid_until?: string | null;
  remarks?: string | null;
  offer_purpose: string;
  version_number: number;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

const COMMERCIAL_OFFER_PURPOSE_LABELS: Record<string, string> = {
  BASE: "Base Offer",
  SUPPLEMENTARY: "Supplementary Offer",
  CHANGE_QUOTATION: "Change Quotation",
};

function offerPurposeLabel(offerPurpose: string): string {
  return COMMERCIAL_OFFER_PURPOSE_LABELS[offerPurpose] || offerPurpose;
}

type TokenPayload = {
  role_codes?: unknown;
  exp?: unknown;
};

type CreateAccessStatus = "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token";

type CreateAccess = {
  status: CreateAccessStatus;
  roleCodes: string[];
};

function buildCommercialOfferListPath(offset: number): string {
  const params = new URLSearchParams({
    limit: String(COMMERCIAL_OFFER_LIST_FETCH_LIMIT),
    offset: String(offset),
  });
  return `/api/commercial-offers?${params.toString()}`;
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

  const allowed = roleCodes.some((role) => COMMERCIAL_OFFER_CREATE_ROLES.includes(role));
  return { status: allowed ? "allowed" : "denied", roleCodes };
}

function createAccessMessage(status: CreateAccessStatus): string {
  if (status === "no_token") return "Sign in as a Sales or Admin user to create Commercial Offers.";
  if (status === "expired") return "Sign in again to create Commercial Offers because the current session has expired.";
  if (status === "invalid_token") return "Sign in again to create Commercial Offers because the current session is invalid.";
  if (status === "denied") return "Your role can view Commercial Offers but cannot create them.";
  return "";
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
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function commercialOfferLoadErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to view Commercial Offers.";
  if (status === 404) return "The Commercial Offer service is not available right now. Please try again shortly.";
  return `Could not load Commercial Offers. HTTP ${status}.`;
}

export default function CommercialOffersPage() {
  const [commercialOffers, setCommercialOffers] = useState<CommercialOffer[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [hasLoaded, setHasLoaded] = useState(false);
  const [createAccess, setCreateAccess] = useState<CreateAccess>({ status: "checking", roleCodes: [] });
  const [currentOffset, setCurrentOffset] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);

  async function loadCommercialOffers(requestedOffset = currentOffset) {
    const nextOffset = Math.max(0, requestedOffset);
    setError("");
    setMessage("");

    const token = getToken();
    if (!token) {
      setCommercialOffers([]);
      setHasLoaded(false);
      setHasNextPage(false);
      setCurrentOffset(0);
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);

    let response: Response;
    try {
      response = await fetch(buildCommercialOfferListPath(nextOffset), {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setCommercialOffers([]);
      setError("Network error while loading Commercial Offers. Check that the backend and frontend services are running.");
      setLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setCommercialOffers([]);
      setHasLoaded(false);
      setHasNextPage(false);
      setError(commercialOfferLoadErrorMessage(response.status));
      setLoading(false);
      return;
    }

    const data = (await response.json()) as CommercialOffer[];
    const visibleOffers = data.slice(0, PAGE_SIZE);
    setCommercialOffers(visibleOffers);
    setHasLoaded(true);
    setCurrentOffset(nextOffset);
    setHasNextPage(data.length > PAGE_SIZE);

    if (visibleOffers.length === 0) {
      setMessage(nextOffset === 0 ? "No Commercial Offer records found." : "No Commercial Offer records found on this page.");
    } else {
      const start = nextOffset + 1;
      const end = nextOffset + visibleOffers.length;
      setMessage(`Loaded Commercial Offer records ${start}-${end}.`);
    }

    setLoading(false);
  }

  useEffect(() => {
    function refreshSessionDrivenState() {
      setCreateAccess(getCreateAccess());
    }

    refreshSessionDrivenState();
    void loadCommercialOffers(0);

    window.addEventListener(SESSION_CHANGED_EVENT, refreshSessionDrivenState);
    window.addEventListener("storage", refreshSessionDrivenState);
    window.addEventListener("focus", refreshSessionDrivenState);

    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, refreshSessionDrivenState);
      window.removeEventListener("storage", refreshSessionDrivenState);
      window.removeEventListener("focus", refreshSessionDrivenState);
    };
  }, []);

  const canCreateCommercialOffer = createAccess.status === "allowed";

  return (
    <section>
      <h2>Commercial Offers</h2>
      <p>
        Commercial Offers are the quotes and tender bids for an Opportunity, linked to its Account. You can add
        lines and pricing evidence, submit the offer, record the customer's answer and create a Work Order.
        Line-level T&amp;C, approval workflows other than approving a quotation for issue, and automatic
        credit exposure limits are not built yet.
      </p>

      <div className="page-actions">
        <button type="button" onClick={() => loadCommercialOffers(currentOffset)} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>
        {canCreateCommercialOffer ? (
          <a className="button-link" href="/commercial-offers/new">
            Create Commercial Offer
          </a>
        ) : null}
      </div>

      {createAccess.status !== "allowed" && createAccess.status !== "checking" ? (
        <p style={{ color: "#6b7280" }}>{createAccessMessage(createAccess.status)}</p>
      ) : null}

      {message ? <p className="text-success">{message}</p> : null}
      {error ? <p className="text-danger">{error}</p> : null}

      {hasLoaded && commercialOffers.length > 0 ? (
        <div className="data-table-wrap">
          <table className="data-table data-table-wide">
            <thead>
              <tr>
                <th>Offer</th>
                <th>Purpose</th>
                <th>Mode / type</th>
                <th>Status</th>
                <th>Value</th>
                <th>Offer date</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {commercialOffers.map((offer) => (
                <tr key={offer.public_id}>
                  <td>
                    <a
                      href={`/commercial-offers/${offer.public_id}`}
                      style={{ color: "#1d4ed8", fontWeight: 700, textDecoration: "underline" }}
                    >
                      {offerVersionLabel(offer.offer_code, offer.version_number)}
                    </a>
                    <div style={{ color: "#6b7280" }}>{offer.offer_title || "-"}</div>
                  </td>
                  <td>
                    <span className="status-badge">{offerPurposeLabel(offer.offer_purpose)}</span>
                  </td>
                  <td>
                    {formatStatusLabel(offer.offer_mode)} / {formatStatusLabel(offer.offer_type)}
                  </td>
                  <td>
                    <span className="status-badge">{formatStatusLabel(offer.offer_status_code)}</span>
                  </td>
                  <td>{formatMoney(offer.offer_value, offer.currency_code)}</td>
                  <td>{formatDateOnly(offer.offer_date)}</td>
                  <td>{formatDateTime(offer.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {hasLoaded && !loading && !error && commercialOffers.length === 0 ? (
        <div className="empty-state">
          No Commercial Offers are available for this page. Create an offer from an Opportunity.
        </div>
      ) : null}

      <div className="pagination-row">
        <button type="button" onClick={() => loadCommercialOffers(Math.max(0, currentOffset - PAGE_SIZE))} disabled={loading || currentOffset === 0}>
          Previous
        </button>
        <span>Offset: {currentOffset}</span>
        <button type="button" onClick={() => loadCommercialOffers(currentOffset + PAGE_SIZE)} disabled={loading || !hasNextPage}>
          Next
        </button>
      </div>
    </section>
  );
}
