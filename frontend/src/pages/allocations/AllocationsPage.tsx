import { useEffect, useRef, useState } from "react";

import DateInput from "../../components/DateInput";
import { PageHeader } from "../../components/PageLayout";
import { createQueryController, initialQueryView, queryView, type QueryView } from "../equipment/certificatesState";
import { getToken, SESSION_CHANGED_EVENT } from "../resource-requirements/pageSession";
import { fetchAssignments } from "./allocationRequests";
import { todayIso, type Assignment } from "./allocationState";
import AllocationsTable from "./AllocationsTable";

// Every allocation, held ones first (design section 7, screen 7). Its preset, "Starting in the next 15 days", is the
// check before the planned start: each row carries today's answer for its site (design section 6.4).

type Filters = { status: string; from: string; to: string };

const STATUS_FILTERS = [
  { code: "HELD", label: "Held" },
  { code: "", label: "All, with the history" },
  { code: "REPLACED", label: "Replaced" },
  { code: "RELEASED", label: "Freed" },
];

function params(filters: Filters): URLSearchParams {
  const query = new URLSearchParams();
  if (filters.status) query.set("status_code", filters.status);
  if (filters.from) query.set("starts_from", filters.from);
  if (filters.to) query.set("starts_to", filters.to);
  return query;
}

export default function AllocationsPage() {
  const [filters, setFilters] = useState<Filters>({ status: "HELD", from: "", to: "" });
  const [view, setView] = useState<QueryView<Assignment[]>>(initialQueryView<Assignment[]>());
  const controller = useRef(
    createQueryController<Filters, Assignment[]>({
      initialQuery: filters,
      getToken,
      fetchAnswer: (token, asked) => fetchAssignments(token, params(asked)),
      show: (update) => setView((current) => queryView(current, update)),
      failure: "The allocations could not be loaded.",
    }),
  );

  useEffect(() => {
    void controller.current.refresh();
    const reload = () => void controller.current.refresh();
    window.addEventListener(SESSION_CHANGED_EVENT, reload);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, reload);
  }, []);

  function apply(next: Filters) {
    setFilters(next);
    void controller.current.setQuery(next);
  }

  return (
    <section>
      <PageHeader
        eyebrow="Resource planning"
        title="Allocations"
        subtitle="Machines held for Work Orders, and the history of those replaced or freed. Today's answer is worked out for each allocation's site as it now is."
      >
        {view.error ? <p className="text-danger">{view.error}</p> : null}
      </PageHeader>
      <div className="page-sections">
        <div className="form-grid">
          <label className="field-stack">
            Status
            <select value={filters.status} onChange={(event) => apply({ ...filters, status: event.target.value })}>
              {STATUS_FILTERS.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack">
            Starting from
            <DateInput value={filters.from} onChange={(event) => apply({ ...filters, from: event.target.value })} />
          </label>
          <label className="field-stack">
            Starting by
            <DateInput value={filters.to} onChange={(event) => apply({ ...filters, to: event.target.value })} />
          </label>
          <div className="form-actions">
            <button type="button" onClick={() => apply({ status: "HELD", from: todayIso(), to: todayIso(15) })}>
              Starting in the next 15 days
            </button>
            <button type="button" onClick={() => apply({ status: "HELD", from: "", to: "" })}>
              Clear
            </button>
          </div>
        </div>
        {view.loading ? <p className="helper-text">Loading the allocations...</p> : null}
        {view.answer && view.answer.length === 0 ? <p className="empty-state">No allocation matches.</p> : null}
        {view.answer && view.answer.length > 0 ? <AllocationsTable assignments={view.answer} returnTo={{ href: "/resource-assignments", label: "Back to allocations" }} /> : null}
      </div>
    </section>
  );
}
