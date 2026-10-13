import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../components/signInMessages";

const TOKEN_KEY = "pbl_auth_token";
const SESSION_CHANGED_EVENT = "pbl-session-changed";

type TcClause = {
  public_id: string;
  clause_id: string;
  business_line: string;
  clause_category: string;
  source_clause_number?: string | null;
  title: string;
  clause_text: string;
  mandatory_default: boolean;
  risk_category?: string | null;
  applies_to_header: boolean;
  applies_to_line: boolean;
  requires_approval_if_omitted: boolean;
  requires_approval_if_modified: boolean;
  active: boolean;
  source_reference?: string | null;
  created_at: string;
  updated_at: string;
};

type TokenPayload = {
  exp?: unknown;
};

const topPanelGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))",
  gap: "18px",
  alignItems: "start",
  minWidth: 0,
};

const topPanelStyle: CSSProperties = {
  minWidth: 0,
  maxWidth: "100%",
};

const detailCardStyle: CSSProperties = {
  marginTop: "24px",
  minWidth: 0,
  maxWidth: "100%",
  overflow: "hidden",
};

const detailListStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "minmax(120px, 160px) minmax(0, 1fr)",
  gap: "8px",
  minWidth: 0,
};

const detailValueStyle: CSSProperties = {
  minWidth: 0,
  maxWidth: "100%",
  overflowWrap: "anywhere",
  wordBreak: "break-word",
  whiteSpace: "pre-wrap",
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

function formatLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function booleanLabel(value: boolean): string {
  return value ? "Yes" : "No";
}

function buildClauseListPath(filters: {
  businessLine: string;
  clauseCategory: string;
  activeOnly: boolean;
  appliesToHeader: boolean;
  appliesToLine: boolean;
  search: string;
}): string {
  const params = new URLSearchParams({ limit: "100", offset: "0" });

  if (filters.businessLine) params.set("business_line", filters.businessLine);
  if (filters.clauseCategory) params.set("clause_category", filters.clauseCategory);
  if (filters.activeOnly) params.set("active", "true");
  if (filters.appliesToHeader) params.set("applies_to_header", "true");
  if (filters.appliesToLine) params.set("applies_to_line", "true");
  if (filters.search.trim()) params.set("search", filters.search.trim());

  return `/api/tc-clauses?${params.toString()}`;
}

function loadErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to view the T&C Clause Library.";
  if (status === 404) return "The T&C Clause Library is not available right now. Please try again shortly.";
  return `Could not load T&C clauses. HTTP ${status}.`;
}

export default function TermsAndConditionsPage() {
  const [clauses, setClauses] = useState<TcClause[]>([]);
  const [selectedClause, setSelectedClause] = useState<TcClause | null>(null);
  const [businessLine, setBusinessLine] = useState("");
  const [clauseCategory, setClauseCategory] = useState("");
  const [activeOnly, setActiveOnly] = useState(true);
  const [appliesToHeader, setAppliesToHeader] = useState(false);
  const [appliesToLine, setAppliesToLine] = useState(false);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const categories = useMemo(() => {
    return Array.from(new Set(clauses.map((clause) => clause.clause_category))).sort();
  }, [clauses]);

  async function loadClauses() {
    setError("");
    setMessage("");

    const token = getToken();
    if (!token) {
      setClauses([]);
      setSelectedClause(null);
      setError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);

    let response: Response;
    try {
      response = await fetch(
        buildClauseListPath({
          businessLine,
          clauseCategory,
          activeOnly,
          appliesToHeader,
          appliesToLine,
          search,
        }),
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );
    } catch {
      setClauses([]);
      setSelectedClause(null);
      setError("Network error while loading T&C clauses. Check that the backend and frontend services are running.");
      setLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setClauses([]);
      setSelectedClause(null);
      setError(loadErrorMessage(response.status));
      setLoading(false);
      return;
    }

    const data = (await response.json()) as TcClause[];
    setClauses(data);
    setSelectedClause(data[0] ?? null);
    setError("");
    setMessage(data.length === 0 ? "No T&C clauses matched the current filters." : `Loaded ${data.length} T&C clause record(s).`);
    setLoading(false);
  }

  useEffect(() => {
    void loadClauses();
  }, []);

  return (
    <section>
      <h2>T&amp;C Clause Library</h2>
      <p>
        Browse the Terms and Conditions clauses used to prepare Commercial Offers.
        These are reference clauses only and are not final legal-approved wording.
      </p>

      <div className="dashboard-demo-note">
        Clauses can be attached to a Commercial Offer. Choosing clauses per line, approving changed clauses and
        legal versioning are not built yet.
      </div>

      <div style={topPanelGridStyle}>
        <div className="form-card" aria-label="T&C clause filters" style={topPanelStyle}>
          <div className="form-grid-compact">
            <label className="field-stack">
              <span>Business line</span>
              <select value={businessLine} onChange={(event) => setBusinessLine(event.target.value)}>
                <option value="">All</option>
                <option value="TRANSPORTATION">Transportation</option>
                <option value="HIRING">Equipment Hiring</option>
              </select>
            </label>

            <label className="field-stack">
              <span>Category</span>
              <select value={clauseCategory} onChange={(event) => setClauseCategory(event.target.value)}>
                <option value="">All</option>
                {categories.map((category) => (
                  <option key={category} value={category}>
                    {formatLabel(category)}
                  </option>
                ))}
              </select>
            </label>

            <label className="field-stack">
              <span>Search</span>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Clause ID, title or text"
              />
            </label>
          </div>

          <div className="page-actions">
            <label>
              <input type="checkbox" checked={activeOnly} onChange={(event) => setActiveOnly(event.target.checked)} /> Active only
            </label>
            <label>
              <input type="checkbox" checked={appliesToHeader} onChange={(event) => setAppliesToHeader(event.target.checked)} /> Header
            </label>
            <label>
              <input type="checkbox" checked={appliesToLine} onChange={(event) => setAppliesToLine(event.target.checked)} /> Line
            </label>
            <button type="button" onClick={loadClauses} disabled={loading}>
              {loading ? "Loading..." : "Apply Filters"}
            </button>
          </div>

          {message ? <p className="action-feedback text-success">{message}</p> : null}
          {error ? <p className="action-feedback text-danger">{error}</p> : null}
        </div>

        <article className="content-card" style={detailCardStyle}>
          {selectedClause ? (
            <>
              <h3>{selectedClause.clause_id}: {selectedClause.title}</h3>
              <p className="helper-text">
                Reference clause from the source document. Check it against that document before legal use.
              </p>
              <dl className="opportunity-context-list" style={detailListStyle}>
                <dt>Business line</dt>
                <dd style={detailValueStyle}>{formatLabel(selectedClause.business_line)}</dd>
                <dt>Source clause</dt>
                <dd style={detailValueStyle}>{selectedClause.source_clause_number || "-"}</dd>
                <dt>Risk category</dt>
                <dd style={detailValueStyle}>{formatLabel(selectedClause.risk_category)}</dd>
                <dt>Approval flags</dt>
                <dd style={detailValueStyle}>
                  Omit approval: {booleanLabel(selectedClause.requires_approval_if_omitted)}; modify approval:{" "}
                  {booleanLabel(selectedClause.requires_approval_if_modified)}
                </dd>
                <dt>Clause text</dt>
                <dd style={detailValueStyle}>{selectedClause.clause_text}</dd>
                <dt>Source reference</dt>
                <dd style={detailValueStyle}>{selectedClause.source_reference || "-"}</dd>
              </dl>
            </>
          ) : (
            <>
              <h3>Selected Clause Detail</h3>
              <div className="empty-state">
                Select a clause from the list to view source, applicability and approval flags.
              </div>
            </>
          )}
        </article>
      </div>

      {clauses.length > 0 ? (
        <div className="data-table-wrap">
          <table className="data-table data-table-wide">
            <thead>
              <tr>
                <th>Clause</th>
                <th>Business line</th>
                <th>Category</th>
                <th>Defaults</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {clauses.map((clause) => (
                <tr key={clause.public_id}>
                  <td>
                    <strong>{clause.clause_id}</strong>
                    <div className="helper-text">{clause.title}</div>
                  </td>
                  <td>{formatLabel(clause.business_line)}</td>
                  <td>{formatLabel(clause.clause_category)}</td>
                  <td>
                    Mandatory: {booleanLabel(clause.mandatory_default)}
                    <br />
                    Header: {booleanLabel(clause.applies_to_header)} / Line: {booleanLabel(clause.applies_to_line)}
                  </td>
                  <td>
                    <span className="status-badge">{clause.active ? "Active" : "Inactive"}</span>
                  </td>
                  <td>
                    <button type="button" onClick={() => setSelectedClause(clause)}>
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {!loading && !error && clauses.length === 0 ? (
        <div className="empty-state">No T&amp;C clauses are available for the current filters.</div>
      ) : null}

    </section>
  );
}
