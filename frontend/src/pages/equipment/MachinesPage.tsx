import { useEffect, useRef, useState } from "react";

import { PageHeader, StatusBadge } from "../../components/PageLayout";
import { SESSION_CHANGED_EVENT, clearSession, getToken, readErrorDetail, readSafeReturnTarget } from "../resource-requirements/pageSession";
import { EquipmentNav } from "./EquipmentParts";
import {
  type ListUpdate,
  type MachineFilters,
  type MachineSummary,
  type Structure,
  assetName,
  capabilityText,
  createListController,
  detailsMissingText,
  flagCodeLabel,
  initialListView,
  listView,
  machineFiltersFromSearch,
  machineKindText,
  machineQuery,
  quantityText,
  statusLabel,
} from "./equipmentState";

// The machines the platform holds, built from Plum's confirmed reports (ERT-1), and the detachable kit
// recorded for their models (ERT-2). Everyone who may see Work Orders may see them; changing anything is on
// a record's own page, for Admin.

const PAGE_SIZE = 25;

export default function MachinesPage() {
  // A machine's kit section links here for one kit model's pieces, or all the kit held for a model.
  const [firstFilters] = useState(() => machineFiltersFromSearch(typeof window === "undefined" ? "" : window.location.search));
  // The page such a link came from - the Models page or a machine's - so the list offers the way back.
  const [returnTarget] = useState(() => readSafeReturnTarget("", ""));
  const [structure, setStructure] = useState<Structure | null>(null);
  const [filters, setFilterState] = useState<MachineFilters>(firstFilters);
  const [view, setView] = useState(initialListView<MachineSummary>());
  const { rows, offset, hasNextPage, loading, error } = view;

  const controller = useRef(
    createListController<MachineFilters, MachineSummary>({
      initialFilters: firstFilters,
      getToken,
      failure: "The machines could not be loaded.",
      fetchRows: async (token, current, pageOffset) => {
        const response = await fetch(`/api/equipment-reference/machines?${machineQuery(current, pageOffset, PAGE_SIZE)}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.status === 401) clearSession();
        if (!response.ok) throw new Error(await readErrorDetail(response, "The machines could not be loaded."));
        return (await response.json()) as MachineSummary[];
      },
      show: (update: ListUpdate<MachineSummary>) => setView((current) => listView(current, update, PAGE_SIZE)),
    }),
  );

  function changeFilters(next: Partial<MachineFilters>) {
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
          if (response.ok) setStructure((await response.json()) as Structure);
        } catch {
          // The kind filter is a convenience; the list works without it.
        }
      })();
    }
    const refresh = () => void controller.current.load(0);
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
  }, []);

  const classes = (structure?.classes ?? []).filter((item) => item.class_kind_code === (filters.kindCode || "MACHINE") || !filters.kindCode);

  return (
    <section>
      <PageHeader
        eyebrow="Equipment"
        title="Machines"
        subtitle="Machines and their fitted parts, brought in from Plum's vehicle report and described in the platform's own terms, and the detachable kit recorded for their models. Plum's facts are as of the report shown; facts Plum does not hold are entered here."
        back={returnTarget.href ? returnTarget : undefined}
      >
        {error ? <p className="text-danger">{error}</p> : null}
      </PageHeader>
      <EquipmentNav current="/equipment" />

      {filters.kitModelPublicId || filters.fitsModelPublicId ? (
        <p className="helper-text">
          {filters.kitModelPublicId ? "Showing the pieces of one kit model." : "Showing the kit held for one machine model."}{" "}
          <button type="button" onClick={() => changeFilters({ kitModelPublicId: "", fitsModelPublicId: "" })}>
            Show everything
          </button>
        </p>
      ) : null}

      <div className="page-actions actions-with-fields">
        <label className="field-stack">
          Show
          <select value={filters.kindCode} onChange={(event) => changeFilters({ kindCode: event.target.value, classCode: "" })}>
            <option value="MACHINE">Machines</option>
            <option value="PART">Parts and kit</option>
            <option value="">Machines, parts and kit</option>
          </select>
        </label>
        <label className="field-stack">
          Kind
          <select value={filters.classCode} onChange={(event) => changeFilters({ classCode: event.target.value })}>
            <option value="">Every kind</option>
            {classes.map((item) => (
              <option key={item.class_code} value={item.class_code}>
                {item.class_label}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack">
          Status
          <select value={filters.statusCode} onChange={(event) => changeFilters({ statusCode: event.target.value })}>
            <option value="ACTIVE">Active</option>
            <option value="RETIRED">Retired</option>
            <option value="">All</option>
          </select>
        </label>
        <label className="field-stack">
          Machine number or reference, or a piece's own number
          <input value={filters.search} onChange={(event) => changeFilters({ search: event.target.value })} maxLength={100} />
        </label>
        <label>
          <input type="checkbox" checked={filters.flaggedOnly} onChange={(event) => changeFilters({ flaggedOnly: event.target.checked })} /> Flagged only
        </label>
        <label>
          <input type="checkbox" checked={filters.detailsToComplete} onChange={(event) => changeFilters({ detailsToComplete: event.target.checked })} /> Details to complete
        </label>
        <button type="button" onClick={() => void controller.current.load(offset)} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {rows.length > 0 ? (
        <div className="data-table-wrap">
          <table className="data-table data-table-wide">
            <thead>
              <tr>
                <th>Reference</th>
                <th>Machine number or kit</th>
                <th>Kind and model</th>
                <th>Key capability</th>
                <th>Status</th>
                <th>Needs attention</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((machine) => (
                <tr key={machine.asset_public_id}>
                  <td>
                    <a href={`/equipment/machines/${machine.asset_public_id}`}>
                      {machine.asset_reference}
                    </a>
                  </td>
                  <td>{machine.machine_number ?? `Kit${quantityText(machine.quantity) ? `, ${quantityText(machine.quantity)}` : ""}`}</td>
                  <td>{machine.machine_number ? machineKindText(machine) : assetName(machine)}</td>
                  <td>{capabilityText(machine.key_capability)}</td>
                  <td>
                    <StatusBadge code={machine.asset_status_code} label={statusLabel(machine.asset_status_code)} />
                  </td>
                  <td>
                    {machine.flag_codes.length || machine.details_missing ? (
                      <ul className="compact-list">
                        {machine.flag_codes.map((code) => (
                          <li key={code}>{flagCodeLabel(code)}</li>
                        ))}
                        {machine.details_missing ? <li>{detailsMissingText(machine)}</li> : null}
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

      {!loading && !error && rows.length === 0 ? (
        <div className="empty-state">No machines match. Machines come in when Admin confirms Plum's vehicle report.</div>
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
