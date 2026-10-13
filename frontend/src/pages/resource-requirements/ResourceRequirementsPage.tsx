import { useEffect, useRef, useState } from "react";

import { PageHeader, StatusBadge } from "../../components/PageLayout";
import { SESSION_CHANGED_EVENT, clearSession, getToken, hrefWithReturnTarget, readErrorDetail } from "./pageSession";
import {
  type EquipmentStructure,
  INITIAL_PLANNING_LIST_VIEW,
  type PlanningFilters,
  type PlanningListUpdate,
  type ResourceRequirement,
  createPlanningListController,
  hiringClasses,
  planningListView,
  priorityLabel,
  requirementDatesText,
  requirementSummary,
  statusLabel,
  warningLabel,
} from "./resourceRequirementState";

// The planning list (WRR-001): requirements across every Work Order, urgent first, then the earliest start,
// filterable by kind of machine. By default those that still need machines - open and partly allocated (8A core).
// Read-only: a requirement is recorded from its Work Order line.

const PAGE_SIZE = 25;
const STATUS_FILTERS = [
  { code: "NEEDS_MACHINES", label: "Needs machines" },
  { code: "OPEN", label: "Open (no machine yet)" },
  { code: "PARTLY_FULFILLED", label: "Partly allocated" },
  { code: "FULFILLED", label: "Allocated" },
  { code: "CANCELLED", label: "Cancelled" },
  { code: "", label: "All" },
];

export default function ResourceRequirementsPage() {
  const [structure, setStructure] = useState<EquipmentStructure | null>(null);
  const [filters, setFilterState] = useState<PlanningFilters>({ statusCode: "NEEDS_MACHINES", classCode: "" });
  // What the table shows follows planningListView: rows only as the answer to the request now awaited.
  const [view, setView] = useState(INITIAL_PLANNING_LIST_VIEW);
  const { rows: requirements, offset, hasNextPage, loading, error } = view;

  function show(update: PlanningListUpdate) {
    setView((current) => planningListView(current, update, PAGE_SIZE));
  }

  // The loading rules - the filters asked for, and only the latest answer shown - live in the tested
  // controller (review rounds 2 and 3, F-10 and F-14). `show` only puts its updates on the screen.
  const controller = useRef(
    createPlanningListController({
      getToken,
      fetchRows: async (token, current, pageOffset) => {
        const params = new URLSearchParams({ limit: String(PAGE_SIZE + 1), offset: String(pageOffset) });
        if (current.statusCode) params.set("status_code", current.statusCode);
        if (current.classCode) params.set("equipment_class_code", current.classCode);
        const response = await fetch(`/api/resource-requirements?${params.toString()}`, { headers: { Authorization: `Bearer ${token}` } });
        if (response.status === 401) clearSession();
        if (!response.ok) throw new Error(await readErrorDetail(response, "The requirements could not be loaded."));
        return (await response.json()) as ResourceRequirement[];
      },
      show: (update) => show(update),
    }),
  );

  function changeFilters(next: Partial<PlanningFilters>) {
    setFilterState((current) => ({ ...current, ...next }));
    void controller.current.setFilters(next);
  }

  useEffect(() => {
    void controller.current.load(0);
    const token = getToken();
    if (token) {
      void (async () => {
        try {
          const response = await fetch("/api/equipment-reference/structure", { headers: { Authorization: `Bearer ${token}` } });
          if (response.ok) setStructure((await response.json()) as EquipmentStructure);
        } catch {
          // The class filter is a convenience; the list works without it.
        }
      })();
    }
    // A session change reloads with the filters the controls show, which the controller holds.
    const refresh = () => void controller.current.load(0);
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
  }, []);

  return (
    <section>
      <PageHeader
        eyebrow="Resource planning"
        title="Resources needed"
        subtitle="What Work Order lines need on site, urgent first, then the earliest start. Requirements are recorded from each line on its Work Order page. PBL's own machines are allocated from a requirement's own page (Allocate a machine); this list itself holds nothing."
      >
        {error ? <p className="text-danger">{error}</p> : null}
      </PageHeader>

      <div className="page-actions" style={{ marginTop: "16px", alignItems: "end" }}>
        <label className="field-stack">
          Status
          <select value={filters.statusCode} onChange={(event) => changeFilters({ statusCode: event.target.value })}>
            {STATUS_FILTERS.map((option) => (
              <option key={option.label} value={option.code}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack">
          Kind of machine
          <select value={filters.classCode} onChange={(event) => changeFilters({ classCode: event.target.value })}>
            <option value="">Every kind</option>
            {hiringClasses(structure).map((item) => (
              <option key={item.class_code} value={item.class_code}>
                {item.class_label}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => void controller.current.load(offset)} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {requirements.length > 0 ? (
        <div className="data-table-wrap">
          <table className="data-table data-table-wide">
            <thead>
              <tr>
                <th>Requirement</th>
                <th>What is needed</th>
                <th>When</th>
                <th>Work Order line</th>
                <th>Priority and status</th>
                <th>Needs attention</th>
              </tr>
            </thead>
            <tbody>
              {requirements.map((requirement) => (
                <tr key={requirement.requirement_public_id}>
                  <td>
                    <a
                      href={hrefWithReturnTarget(`/resource-requirements/${requirement.requirement_public_id}`, "/resource-requirements", "Back to resource planning")}
                      style={{ color: "#1d4ed8", fontWeight: 700 }}
                    >
                      {requirement.requirement_reference}
                    </a>
                  </td>
                  <td>{requirementSummary(requirement)}</td>
                  <td>{requirementDatesText(requirement)}</td>
                  <td>
                    <a
                      href={hrefWithReturnTarget(`/work-orders/${requirement.work_order_public_id}`, "/resource-requirements", "Back to resource planning")}
                      style={{ color: "#1d4ed8" }}
                    >
                      {requirement.work_order_code}
                    </a>
                    , line {requirement.work_order_line_number}
                    <div style={{ color: "#6b7280" }}>{requirement.line.site?.city ?? "No site yet"}</div>
                  </td>
                  <td>
                    <div>{priorityLabel(requirement.priority_code)}</div>
                    <StatusBadge code={requirement.requirement_status_code} label={statusLabel(requirement.requirement_status_code)} />
                    {requirement.units_remaining ? <div className="helper-text">{requirement.units_remaining} still to allocate</div> : null}
                  </td>
                  <td>
                    {requirement.warnings.length > 0 ? (
                      <ul className="compact-list">
                        {requirement.warnings.map((warning) => (
                          <li key={warning}>{warningLabel(warning)}</li>
                        ))}
                      </ul>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {!loading && !error && requirements.length === 0 ? (
        <div className="empty-state">No requirements match. They are recorded from each line on its Work Order page.</div>
      ) : null}

      <div className="pagination-row">
        <button type="button" disabled={loading || offset === 0} onClick={() => void controller.current.load(Math.max(0, offset - PAGE_SIZE))}>
          Previous
        </button>
        <button type="button" disabled={loading || !hasNextPage} onClick={() => void controller.current.load(offset + PAGE_SIZE)}>
          Next
        </button>
      </div>
    </section>
  );
}
