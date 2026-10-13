import { useEffect, useState } from "react";

import { DEFAULT_CURRENCY, formatCurrencyAmount, formatCurrencyTotals } from "./currency";
import type { CurrencyTotal } from "./currency";
import { formatDateTime } from "./dateTimeDisplay";
import { formatWorkOrderStatusLabel } from "./PageLayout";

const TOKEN_KEY = "pbl_auth_token";
const SESSION_CHANGED_EVENT = "pbl-session-changed";

// Every amount comes as a list of totals, one per currency, INR first. Only INR is listed unless a record is in
// another currency; nothing is converted (owner's decision, 4 October 2026, TB1-600).
type StatusCount = {
  status_code: string;
  record_count: number;
  totals?: CurrencyTotal[] | null;
};

type LabelledCount = {
  label: string;
  record_count: number;
  totals?: CurrencyTotal[] | null;
};

type PipelineReport = {
  generated_at: string;
  lead_total: number;
  leads_by_status: StatusCount[];
  opportunity_total: number;
  opportunity_totals: CurrencyTotal[];
  opportunities_by_status: StatusCount[];
};

type OpenOffersReport = {
  generated_at: string;
  open_offer_total: number;
  open_offer_totals: CurrencyTotal[];
  offers_by_status: StatusCount[];
  ageing: LabelledCount[];
  awaiting_customer_response: number;
  expiry_horizon_days: number;
  expiring_within_horizon: number;
  already_expired: number;
  no_expiry_recorded: number;
};

type AcceptedOfferPurposeRow = {
  offer_purpose: string;
  record_count: number;
  totals: CurrencyTotal[];
  with_work_order_shell: number;
  awaiting_handoff: number;
};

type AcceptedOffersReport = {
  generated_at: string;
  accepted_total: number;
  accepted_totals: CurrencyTotal[];
  with_work_order_shell: number;
  awaiting_handoff: number;
  awaiting_handoff_totals: CurrencyTotal[];
  by_purpose: AcceptedOfferPurposeRow[];
};

type HandoffRow = {
  work_order_public_id: string;
  work_order_code: string;
  work_order_status_code: string;
  customer_wo_reference: string | null;
  received_date: string | null;
  created_at: string;
  source_offer_public_id: string;
  source_offer_code: string;
  source_offer_value: string | null;
  source_offer_currency_code: string;
  account_public_id: string | null;
};

type WorkOrderHandoffReport = {
  generated_at: string;
  work_order_total: number;
  work_orders_by_status: StatusCount[];
  source_offer_totals: CurrencyTotal[];
  recent_limit: number;
  recent: HandoffRow[];
};

type Reports = {
  pipeline: PipelineReport;
  openOffers: OpenOffersReport;
  acceptedOffers: AcceptedOffersReport;
  handoff: WorkOrderHandoffReport;
};

type LoadState =
  | { status: "loading" }
  | { status: "no_session" }
  | { status: "error"; message: string }
  | { status: "ready"; reports: Reports };

/** True when any amount in the reports is in a currency other than INR. */
function hasOtherCurrencies(reports: Reports): boolean {
  const { pipeline, openOffers, acceptedOffers, handoff } = reports;
  const lists: Array<CurrencyTotal[] | null | undefined> = [
    pipeline.opportunity_totals,
    openOffers.open_offer_totals,
    acceptedOffers.accepted_totals,
    acceptedOffers.awaiting_handoff_totals,
    handoff.source_offer_totals,
  ];
  return (
    lists.some((totals) => (totals ?? []).some((total) => total.currency_code !== DEFAULT_CURRENCY)) ||
    handoff.recent.some((row) => row.source_offer_currency_code !== DEFAULT_CURRENCY)
  );
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

async function fetchReport<T>(path: string, token: string): Promise<T> {
  const response = await fetch(path, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) {
    throw new Error(`Could not load ${path} (HTTP ${response.status}).`);
  }
  return (await response.json()) as T;
}

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <article className="report-kpi">
      <span className="report-kpi-label">{label}</span>
      <strong className="report-kpi-value">{value}</strong>
      {hint ? <span className="report-kpi-hint">{hint}</span> : null}
    </article>
  );
}

function formatCodeLabel(code: string): string {
  return code
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
    .join(" ");
}

function StatusTable({
  rows,
  firstColumnHeading = "Status",
  countHeading,
  showValue,
  emptyText,
  formatLabel = (value: string) => value,
}: {
  rows: Array<StatusCount | LabelledCount>;
  firstColumnHeading?: string;
  countHeading: string;
  showValue: boolean;
  emptyText: string;
  formatLabel?: (value: string) => string;
}) {
  if (rows.length === 0) {
    return <p className="empty-state">{emptyText}</p>;
  }

  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">{firstColumnHeading}</th>
            <th scope="col">{countHeading}</th>
            {showValue ? <th scope="col">Value</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const label = "status_code" in row ? row.status_code : row.label;
            return (
              <tr key={label}>
                <td>{formatLabel(label)}</td>
                <td>{row.record_count}</td>
                {showValue ? <td>{formatCurrencyTotals(row.totals)}</td> : null}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function OperationalReports() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const token = getToken();
      if (!token) {
        if (!cancelled) setState({ status: "no_session" });
        return;
      }

      setState({ status: "loading" });
      try {
        const [pipeline, openOffers, acceptedOffers, handoff] = await Promise.all([
          fetchReport<PipelineReport>("/api/reports/pipeline", token),
          fetchReport<OpenOffersReport>("/api/reports/open-offers", token),
          fetchReport<AcceptedOffersReport>("/api/reports/accepted-offers", token),
          fetchReport<WorkOrderHandoffReport>("/api/reports/work-order-handoff?limit=10", token),
        ]);
        if (!cancelled) {
          setState({ status: "ready", reports: { pipeline, openOffers, acceptedOffers, handoff } });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            status: "error",
            message: error instanceof Error ? error.message : "Could not load operational reports.",
          });
        }
      }
    }

    void load();

    function refresh() {
      setReloadToken((value) => value + 1);
    }
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    return () => {
      cancelled = true;
      window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
    };
  }, [reloadToken]);

  if (state.status === "loading") {
    return (
      <section className="content-card">
        <h3>Operational summary</h3>
        <p className="helper-text">Loading operational reports...</p>
      </section>
    );
  }

  if (state.status === "no_session") {
    return (
      <section className="content-card">
        <h3>Operational summary</h3>
        <p className="helper-text">Sign in to see live pipeline, offer and Work Order figures.</p>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section className="content-card">
        <h3>Operational summary</h3>
        <p className="action-feedback">{state.message}</p>
        <button type="button" className="button-link-secondary" onClick={() => setReloadToken((v) => v + 1)}>
          Try again
        </button>
      </section>
    );
  }

  const { pipeline, openOffers, acceptedOffers, handoff } = state.reports;

  return (
    <section className="content-card">
      <div className="page-actions">
        <h3>Operational summary</h3>
        <button type="button" className="button-link-secondary" onClick={() => setReloadToken((v) => v + 1)}>
          Refresh
        </button>
      </div>
      <p className="helper-text">
        Live figures as at {formatDateTime(pipeline.generated_at)}.{" "}
        {hasOtherCurrencies(state.reports)
          ? "Each currency is totalled separately; nothing is converted."
          : "All amounts in INR."}
      </p>

      <div className="report-kpi-grid">
        <Kpi
          label="Open opportunities"
          value={String(pipeline.opportunity_total)}
          hint={formatCurrencyTotals(pipeline.opportunity_totals)}
        />
        <Kpi
          label="Open offers"
          value={String(openOffers.open_offer_total)}
          hint={formatCurrencyTotals(openOffers.open_offer_totals)}
        />
        <Kpi
          label="Awaiting Work Order"
          value={String(acceptedOffers.awaiting_handoff)}
          hint={formatCurrencyTotals(acceptedOffers.awaiting_handoff_totals)}
        />
        <Kpi
          label="Work Orders"
          value={String(handoff.work_order_total)}
          hint={formatCurrencyTotals(handoff.source_offer_totals)}
        />
      </div>

      <h4>Pipeline</h4>
      <p className="helper-text">
        {pipeline.lead_total} Lead(s) and {pipeline.opportunity_total} Opportunity(ies) recorded.
      </p>
      <StatusTable
        rows={pipeline.opportunities_by_status}
        formatLabel={formatCodeLabel}
        countHeading="Opportunities"
        showValue
        emptyText="No Opportunities recorded yet."
      />
      <StatusTable
        rows={pipeline.leads_by_status}
        formatLabel={formatCodeLabel}
        countHeading="Leads"
        showValue={false}
        emptyText="No Leads recorded yet."
      />

      <h4>Open Commercial Offers</h4>
      <p className="helper-text">
        {openOffers.awaiting_customer_response} awaiting customer response.{" "}
        {openOffers.expiring_within_horizon} expiring within {openOffers.expiry_horizon_days} days.{" "}
        {openOffers.already_expired} already past validity. {openOffers.no_expiry_recorded} with no
        validity date recorded.
      </p>
      <StatusTable
        rows={openOffers.offers_by_status}
        formatLabel={formatCodeLabel}
        countHeading="Offers"
        showValue
        emptyText="No open Commercial Offers."
      />
      <StatusTable
        rows={openOffers.ageing}
        firstColumnHeading="Age"
        countHeading="Offers"
        showValue
        emptyText="No open Commercial Offers to age."
      />

      <h4>Accepted Commercial Offers</h4>
      <p className="helper-text">
        {acceptedOffers.accepted_total} accepted, worth {formatCurrencyTotals(acceptedOffers.accepted_totals)}.{" "}
        {acceptedOffers.with_work_order_shell} already have a Work Order;{" "}
        {acceptedOffers.awaiting_handoff} are awaiting a Work Order.
      </p>
      {acceptedOffers.by_purpose.length === 0 ? (
        <p className="empty-state">No accepted Commercial Offers yet.</p>
      ) : (
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Purpose</th>
                <th scope="col">Accepted</th>
                <th scope="col">Value</th>
                <th scope="col">With Work Order</th>
                <th scope="col">Awaiting Work Order</th>
              </tr>
            </thead>
            <tbody>
              {acceptedOffers.by_purpose.map((row) => (
                <tr key={row.offer_purpose}>
                  <td>{formatCodeLabel(row.offer_purpose)}</td>
                  <td>{row.record_count}</td>
                  <td>{formatCurrencyTotals(row.totals)}</td>
                  <td>{row.with_work_order_shell}</td>
                  <td>{row.awaiting_handoff}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h4>Work Orders created</h4>
      <StatusTable
        rows={handoff.work_orders_by_status}
        countHeading="Work Orders"
        showValue={false}
        emptyText="No Work Orders yet."
        formatLabel={formatWorkOrderStatusLabel}
      />
      {handoff.recent.length === 0 ? (
        <p className="empty-state">No Work Orders yet.</p>
      ) : (
        <div className="data-table-wrap">
          <table className="data-table data-table-wide">
            <thead>
              <tr>
                <th scope="col">Work Order</th>
                <th scope="col">Status</th>
                <th scope="col">Source Offer</th>
                <th scope="col">Offer value</th>
                <th scope="col">Created</th>
              </tr>
            </thead>
            <tbody>
              {handoff.recent.map((row) => (
                <tr key={row.work_order_public_id}>
                  <td>
                    <a href={`/work-orders/${row.work_order_public_id}`}>{row.work_order_code}</a>
                  </td>
                  <td>{formatWorkOrderStatusLabel(row.work_order_status_code)}</td>
                  <td>
                    <a href={`/commercial-offers/${row.source_offer_public_id}`}>
                      {row.source_offer_code}
                    </a>
                  </td>
                  <td>{formatCurrencyAmount(row.source_offer_value, row.source_offer_currency_code)}</td>
                  <td>{formatDateTime(row.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
