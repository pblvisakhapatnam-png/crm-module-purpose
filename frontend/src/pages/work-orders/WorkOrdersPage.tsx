import { useEffect, useState } from "react";

import { formatWorkOrderStatusLabel } from "../../components/PageLayout";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { offerVersionLabel } from "../../components/offerVersion";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";

const PAGE_SIZE = 20;
const WORK_ORDER_LIST_FETCH_LIMIT = PAGE_SIZE + 1;
const TOKEN_KEY = "pbl_auth_token";
const SESSION_CHANGED_EVENT = "pbl-session-changed";

type WorkOrder = {
  public_id: string;
  work_order_code: string;
  work_order_title?: string | null;
  work_order_status_code: string;
  commercial_offer_public_id: string;
  commercial_offer_code?: string | null;
  commercial_offer_version_number?: number | null;
  opportunity_public_id: string;
  account_public_id?: string | null;
  customer_wo_reference?: string | null;
  received_date?: string | null;
  source_offer_status_code: string;
  remarks?: string | null;
  created_at: string;
  updated_at: string;
};

type TokenPayload = { role_codes?: unknown; exp?: unknown };

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

function buildWorkOrderListPath(offset: number): string {
  const params = new URLSearchParams({ limit: String(WORK_ORDER_LIST_FETCH_LIMIT), offset: String(offset) });
  return `/api/work-orders?${params.toString()}`;
}

function formatDateOnly(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "2-digit" });
}

function workOrderLoadError(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to view Work Orders.";
  if (status === 404) return "The Work Order service is not available right now. Please try again shortly.";
  return `Could not load Work Orders. HTTP ${status}.`;
}

export default function WorkOrdersPage() {
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [currentOffset, setCurrentOffset] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);

  async function loadWorkOrders(requestedOffset = currentOffset) {
    const token = getToken();
    const nextOffset = Math.max(0, requestedOffset);
    setError("");
    setMessage("");

    if (!token) {
      setWorkOrders([]);
      setHasNextPage(false);
      setCurrentOffset(0);
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);
    let response: Response;
    try {
      response = await fetch(buildWorkOrderListPath(nextOffset), { headers: { Authorization: `Bearer ${token}` } });
    } catch {
      setError("Network error while loading Work Orders. Check that the backend and frontend services are running.");
      setLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setWorkOrders([]);
      setError(workOrderLoadError(response.status));
      setLoading(false);
      return;
    }

    const data = (await response.json()) as WorkOrder[];
    setWorkOrders(data.slice(0, PAGE_SIZE));
    setHasNextPage(data.length > PAGE_SIZE);
    setCurrentOffset(nextOffset);
    setMessage(data.length > 0 ? "Work Orders loaded." : "No Work Orders found yet.");
    setLoading(false);
  }

  useEffect(() => {
    void loadWorkOrders(0);
    function refreshOnSessionChange() {
      void loadWorkOrders(0);
    }
    window.addEventListener(SESSION_CHANGED_EVENT, refreshOnSessionChange);
    window.addEventListener("storage", refreshOnSessionChange);
    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, refreshOnSessionChange);
      window.removeEventListener("storage", refreshOnSessionChange);
    };
  }, []);

  return (
    <section>
      <h2>Work Orders</h2>
      <p>
        Work Orders created from accepted Commercial Offers. PBL's own machines are allocated from each line's
        resource requirement. Customer Master approval, release to Ops, hired machines, crew, log sheets and billing
        are not built yet.
      </p>

      <div className="page-actions">
        <button type="button" onClick={() => void loadWorkOrders(currentOffset)} disabled={loading}>
          {loading ? "Loading..." : "Refresh Work Orders"}
        </button>
      </div>

      {message ? <p style={{ color: "#065f46" }}>{message}</p> : null}
      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}

      <div className="record-list">
        {workOrders.map((workOrder) => (
          <article key={workOrder.public_id} className="record-card">
            <h3 style={{ marginTop: 0 }}>
              <a href={`/work-orders/${workOrder.public_id}`} style={{ color: "#1d4ed8", fontWeight: 700 }}>
                {workOrder.work_order_code}
              </a>
            </h3>
            <p style={{ margin: "4px 0" }}>{workOrder.work_order_title || "Work Order"}</p>
            <p style={{ color: "#6b7280", margin: "4px 0" }}>
              Status: <span className="status-badge">{formatWorkOrderStatusLabel(workOrder.work_order_status_code)}</span> | Source CO:{" "}
              {workOrder.commercial_offer_code
                ? offerVersionLabel(workOrder.commercial_offer_code, workOrder.commercial_offer_version_number)
                : workOrder.commercial_offer_public_id}
            </p>
            <p style={{ color: "#6b7280", margin: "4px 0" }}>
              Customer WO ref: {workOrder.customer_wo_reference || "-"} | Received: {formatDateOnly(workOrder.received_date)} | Created: {formatDateTime(workOrder.created_at)}
            </p>
          </article>
        ))}
      </div>

      {!loading && !error && workOrders.length === 0 ? (
        <div className="empty-state">
          No Work Orders yet. They are created from accepted Commercial Offers only.
        </div>
      ) : null}

      <div className="pagination-row">
        <button type="button" disabled={loading || currentOffset === 0} onClick={() => void loadWorkOrders(Math.max(0, currentOffset - PAGE_SIZE))}>
          Previous
        </button>
        <button type="button" disabled={loading || !hasNextPage} onClick={() => void loadWorkOrders(currentOffset + PAGE_SIZE)}>
          Next
        </button>
      </div>
    </section>
  );
}
