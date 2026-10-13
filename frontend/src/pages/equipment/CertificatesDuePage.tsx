import { useEffect, useState } from "react";

import { PageHeader, StatusBadge } from "../../components/PageLayout";
import { SESSION_CHANGED_EVENT, clearSession, getToken, readErrorDetail } from "../resource-requirements/pageSession";
import { EquipmentNav } from "./EquipmentParts";
import {
  BAND_CODES,
  BAND_LABELS,
  INITIAL_DUE_FILTERS,
  type CertificateKind,
  type CertificatesDue,
  type DueFilters,
  bandTone,
  createQueryController,
  initialQueryView,
  queryView,
  dueQuery,
  dueText,
  formatDay,
} from "./certificatesState";
import type { Structure } from "./equipmentState";

// Certificates due (ELG-1, section 7): the Fleet Admin's renewal list. Everything missing, without its copy, run
// out, or running out within 60, 30 or 15 days by the baseline rules, and every "not applicable" mark ending
// within them. Worked out when read: nothing is stored and nothing is sent.

const PAGE_SIZE = 50;

export default function CertificatesDuePage() {
  const [filters, setFilters] = useState<DueFilters>(INITIAL_DUE_FILTERS);
  const [offset, setOffset] = useState(0);
  const [view, setView] = useState(initialQueryView<CertificatesDue>());
  const [structure, setStructure] = useState<Structure | null>(null);
  const [kinds, setKinds] = useState<CertificateKind[]>([]);
  const due = view.answer;
  const { loading, error } = view;

  // The list's loading: its query is the filters and page the controls show, and an answer is shown only for the
  // latest request (certificatesState.ts, createQueryController).
  const [controller] = useState(() =>
    createQueryController<{ filters: DueFilters; offset: number }, CertificatesDue>({
      initialQuery: { filters: INITIAL_DUE_FILTERS, offset: 0 },
      getToken,
      failure: "Network error: certificates due could not be loaded.",
      fetchAnswer: async (token, query) => {
        const response = await fetch(`/api/eligibility/certificates-due?${dueQuery(query.filters, query.offset, PAGE_SIZE)}`, { headers: { Authorization: `Bearer ${token}` } });
        if (response.status === 401) clearSession();
        if (!response.ok) throw new Error(await readErrorDetail(response, "Certificates due could not be loaded."));
        return (await response.json()) as CertificatesDue;
      },
      show: (update) => setView((current) => queryView(current, update)),
    }),
  );

  function change(next: Partial<DueFilters>) {
    const merged = { ...filters, ...next };
    setFilters(merged);
    setOffset(0);
    void controller.setQuery({ filters: merged, offset: 0 });
  }

  function page(nextOffset: number) {
    setOffset(nextOffset);
    void controller.setQuery({ filters, offset: nextOffset });
  }

  useEffect(() => {
    void controller.refresh();
    const token = getToken();
    if (token) {
      void (async () => {
        try {
          const headers = { Authorization: `Bearer ${token}` };
          const [structureResponse, kindsResponse] = await Promise.all([fetch("/api/equipment-reference/structure", { headers }), fetch("/api/eligibility/certificate-kinds", { headers })]);
          if (structureResponse.ok) setStructure((await structureResponse.json()) as Structure);
          if (kindsResponse.ok) setKinds((await kindsResponse.json()) as CertificateKind[]);
        } catch {
          // The filters are a convenience; the list works without them.
        }
      })();
    }
    // After a session change, the same filters and page the controls show.
    const refresh = () => void controller.refresh();
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const items = due?.items ?? [];
  const hasNextPage = due ? offset + items.length < due.total : false;

  return (
    <section>
      <PageHeader
        eyebrow="Equipment"
        title="Certificates due"
        subtitle="Every certificate missing, without its copy, run out, or running out within 60 days, by the rules for all of India - and every 'not applicable' mark ending within them. A state's shorter interval shows when a machine is checked for a site there."
      >
        {error ? <p className="text-danger">{error}</p> : null}
      </PageHeader>
      <EquipmentNav current="/equipment/certificates" />

      <div className="page-actions" role="group" aria-label="Bands">
        <button type="button" aria-pressed={filters.band === ""} onClick={() => change({ band: "" })}>
          All ({due ? Object.values(due.band_counts).reduce((sum, count) => sum + count, 0) : 0})
        </button>
        {BAND_CODES.map((band) => (
          <button key={band} type="button" aria-pressed={filters.band === band} onClick={() => change({ band })}>
            {BAND_LABELS[band]} ({due?.band_counts[band] ?? 0})
          </button>
        ))}
      </div>

      <div className="page-actions actions-with-fields">
        <label className="field-stack">
          Kind
          <select value={filters.classCode} onChange={(event) => change({ classCode: event.target.value })}>
            <option value="">Every kind</option>
            {(structure?.classes ?? []).map((item) => (
              <option key={item.class_code} value={item.class_code}>
                {item.class_label}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack">
          Certificate
          <select value={filters.kindCode} onChange={(event) => change({ kindCode: event.target.value })}>
            <option value="">Every certificate</option>
            {kinds.map((item) => (
              <option key={item.kind_code} value={item.kind_code}>
                {item.kind_label}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack">
          Machine number or reference
          <input value={filters.search} onChange={(event) => change({ search: event.target.value })} maxLength={100} />
        </label>
        <button type="button" onClick={() => void controller.refresh()} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {items.length > 0 ? (
        <div className="data-table-wrap">
          <table className="data-table data-table-wide">
            <thead>
              <tr>
                <th>Due</th>
                <th>Machine, part or kit</th>
                <th>Certificate</th>
                <th>What is due</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={`${item.asset.asset_public_id}-${item.kind_code}`}>
                  <td>
                    <StatusBadge code={item.band_code} tone={bandTone(item.band_code)} label={BAND_LABELS[item.band_code] ?? item.band_code} />
                  </td>
                  <td>
                    <a href={`/equipment/machines/${item.asset.asset_public_id}`}>{item.asset.asset_reference}</a> {item.asset.machine_number ?? item.asset.serial_number ?? ""}
                    <div className="helper-text">
                      {item.asset.type_label ? `${item.asset.type_label} ${item.asset.class_label.toLowerCase()}` : item.asset.class_label}
                    </div>
                  </td>
                  <td>
                    {item.kind_label}
                    {item.certificate_asset_reference ? <div className="helper-text">On its fitted part {item.certificate_asset_reference}</div> : null}
                  </td>
                  <td>{dueText(item)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {!loading && !error && due && items.length === 0 ? (
        <div className="empty-state">Nothing is due{filters.band || filters.classCode || filters.kindCode || filters.search ? " among these" : ""}. Worked out on {formatDay(due.today)}.</div>
      ) : null}

      <div className="pagination-row">
        <button type="button" disabled={loading || offset === 0} onClick={() => page(Math.max(0, offset - PAGE_SIZE))}>
          Previous
        </button>
        <button type="button" disabled={loading || !hasNextPage} onClick={() => page(offset + PAGE_SIZE)}>
          Next
        </button>
      </div>
    </section>
  );
}
