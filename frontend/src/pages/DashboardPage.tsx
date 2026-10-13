import { useEffect, useState } from "react";

import OperationalReports from "../components/OperationalReports";

const TOKEN_KEY = "pbl_auth_token";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const SALES_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];

type TokenPayload = {
  role_codes?: unknown;
  exp?: unknown;
};

type CreateAccessStatus = "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token";

type CreateAccess = {
  status: CreateAccessStatus;
  roleCodes: string[];
};

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
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

  if (roleCodes.some((role) => SALES_CREATE_ROLES.includes(role))) {
    return { status: "allowed", roleCodes };
  }

  return { status: "denied", roleCodes };
}

function createAccessMessage(access: CreateAccess): string {
  if (access.status === "checking") return "Checking your session...";
  if (access.status === "allowed") return "You can create Accounts, Leads, Opportunities and Commercial Offers from this dashboard.";
  if (access.status === "no_token") return "Sign in to see actions available to your role.";
  if (access.status === "expired") return "Sign in again to see actions available to your role.";
  if (access.status === "invalid_token") return "Sign in again because the current session token is not readable.";
  return "Create shortcuts are hidden because your role does not allow Sales create actions.";
}

export default function HomePage() {
  const [createAccess, setCreateAccess] = useState<CreateAccess>({ status: "checking", roleCodes: [] });

  useEffect(() => {
    function refreshCreateAccess() {
      setCreateAccess(getCreateAccess());
    }

    refreshCreateAccess();

    window.addEventListener(SESSION_CHANGED_EVENT, refreshCreateAccess);
    window.addEventListener("storage", refreshCreateAccess);
    window.addEventListener("focus", refreshCreateAccess);

    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, refreshCreateAccess);
      window.removeEventListener("storage", refreshCreateAccess);
      window.removeEventListener("focus", refreshCreateAccess);
    };
  }, []);

  const canCreate = createAccess.status === "allowed";

  return (
    <section>
      <h2>Dashboard</h2>
      <p>
        Follow a sale from Lead to Account, Opportunity, Commercial Offer and Work Order. Each record stays linked to the one before it.
      </p>

      <p className="helper-text">{createAccessMessage(createAccess)}</p>


      <OperationalReports />

      <div className="dashboard-demo-note">
        Built so far: Lead intake and qualification, conversion to Account and Opportunity, Commercial Offers through to the customer's answer, and Work Order creation.
        Not built yet: Customer Master activation, Work Order release to Ops, equipment and crew assignment, log sheets, billing, approval workflows other than approving a quotation for issue, and locking a submitted version against change.
      </div>

      <div className="dashboard-grid">
        <article className="dashboard-card">
          <h3>Lead</h3>
          <span className="status-badge">Enquiry intake</span>
          <p>Capture early enquiries, record follow-ups and qualify before conversion.</p>
          <div className="dashboard-actions">
            <a className="dashboard-action" href="/leads">View Leads</a>
            {canCreate ? <a className="dashboard-action-secondary" href="/leads/new">Create Lead</a> : null}
          </div>
        </article>

        <article className="dashboard-card">
          <h3>Account</h3>
          <span className="status-badge">Qualified Prospect</span>
          <p>An Account can start as a Qualified Prospect. That is not Customer Master activation, which Finance does later.</p>
          <div className="dashboard-actions">
            <a className="dashboard-action" href="/accounts">View Accounts</a>
            {canCreate ? <a className="dashboard-action-secondary" href="/accounts/new">Create Account</a> : null}
          </div>
        </article>

        <article className="dashboard-card">
          <h3>Opportunity</h3>
          <span className="status-badge">Pursuit record</span>
          <p>Track the requirement after a Lead is worth pursuing or an Account has a clear enquiry.</p>
          <div className="dashboard-actions">
            <a className="dashboard-action" href="/opportunities">View Opportunities</a>
            {canCreate ? <a className="dashboard-action-secondary" href="/opportunities/new">Create Opportunity</a> : null}
          </div>
        </article>

        <article className="dashboard-card">
          <h3>Commercial Offer</h3>
          <span className="status-badge">Quote control</span>
          <p>Prepare, submit and close offers, linked to their Account and Opportunity.</p>
          <div className="dashboard-actions">
            <a className="dashboard-action" href="/commercial-offers">View Offers</a>
            {canCreate ? <a className="dashboard-action-secondary" href="/commercial-offers/new">Create Offer</a> : null}
          </div>
        </article>

        <article className="dashboard-card">
          <h3>T&amp;C Clause Library</h3>
          <span className="status-badge">Reference clauses</span>
          <p>Browse the T&amp;C clauses you can attach to a Commercial Offer. Clause approvals are not built yet.</p>
          <div className="dashboard-actions">
            <a className="dashboard-action" href="/terms-and-conditions">View T&amp;C Clauses</a>
          </div>
        </article>

        <article className="dashboard-card">
          <h3>Work Orders</h3>
          <span className="status-badge">Awaiting release to Ops</span>
          <p>Review Work Orders created from accepted Commercial Offers. Release to Ops, hired machines, crew, log sheets and billing are not built yet.</p>
          <div className="dashboard-actions">
            <a className="dashboard-action" href="/work-orders">View Work Orders</a>
          </div>
        </article>

        <article className="dashboard-card">
          <h3>Linked Account check</h3>
          <span className="status-badge">Active</span>
          <p>Submitting or accepting a Commercial Offer, and creating a Work Order, need a linked Account.</p>
          <div className="dashboard-actions">
            <a className="dashboard-action-secondary" href="/commercial-offers">Check Offers</a>
          </div>
        </article>
      </div>
    </section>
  );
}
