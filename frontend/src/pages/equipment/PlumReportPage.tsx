import { useEffect, useRef, useState } from "react";

import { PageHeader, SectionCard } from "../../components/PageLayout";
import { SESSION_CHANGED_EVENT, clearSession, formatDateTime, getToken, readErrorDetail, readRoleCodes } from "../resource-requirements/pageSession";
import { createLatestOnly } from "../resource-requirements/resourceRequirementState";
import { EquipmentNav, FeedbackLine } from "./EquipmentParts";
import {
  FIELD_LABELS,
  IMPORT_STATUS_LABELS,
  VALUE_RULE_ACTION_LABELS,
  type CorrectionToSend,
  type EquipmentImport,
  type Feedback,
  type ImportSummary,
  type ValueRule,
  WITHHELD_TEXT,
  canManageEquipment,
  correctionValuesText,
  outcomeLabel,
  plainNumber,
  reasonText,
} from "./equipmentState";
import DateInput from "../../components/DateInput";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

// Plum's vehicle report (ERT-1): Admin uploads it and gets a preview - nothing changes until it is
// confirmed. Past imports, and the list of corrections to send to Plum, are here too; the list is
// always current, since a correction Plum agrees with closes itself.

type CategoryRule = {
  category: string;
  class_label: string;
  check_code: string;
  capability_label: string | null;
  plum_unit_code: string | null;
  plausible_low: string | null;
  plausible_high: string | null;
};

const MAX_BYTES = 5 * 1024 * 1024;

function todayInIndia(): string {
  // The report's date defaults to today where PBL works.
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
}

function countsText(counts: Record<string, number>): string {
  const parts = ["NEW", "CHANGED", "RETIRED", "REACTIVATED", "SET_ASIDE", "MISSING"]
    .filter((code) => counts[code])
    .map((code) => `${outcomeLabel(code).toLowerCase()} ${counts[code]}`);
  return parts.join(", ") || "-";
}

function valueRuleText(rule: ValueRule): string {
  if (rule.action_code === "SPLIT_NUMBER_AND_UNIT") return `${plainNumber(rule.result_number)} ${rule.result_unit_code?.toLowerCase() ?? ""}`;
  if (rule.action_code === "REASSIGN_TO_TYPE") return `the type ${rule.result_type_code?.toLowerCase().replace(/_/g, " ") ?? ""}`;
  return VALUE_RULE_ACTION_LABELS[rule.action_code]?.toLowerCase() ?? rule.action_code;
}

export default function PlumReportPage() {
  const [canManage, setCanManage] = useState(false);
  const [imports, setImports] = useState<ImportSummary[]>([]);
  const [rules, setRules] = useState<ValueRule[]>([]);
  const [corrections, setCorrections] = useState<CorrectionToSend[]>([]);
  const [categoryRules, setCategoryRules] = useState<CategoryRule[]>([]);
  const [loadError, setLoadError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [reportDate, setReportDate] = useState(todayInIndia());
  const [uploading, setUploading] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState<Feedback>(null);
  const loads = useRef(createLatestOnly());

  async function load(manage: boolean) {
    const ticket = loads.current.begin();
    const token = getToken();
    if (!token) {
      setLoadError(SIGN_IN_FIRST);
      return;
    }
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [correctionsResponse, categoryResponse, importsResponse] = await Promise.all([
        fetch("/api/equipment-reference/corrections", { headers }),
        fetch("/api/equipment-reference/category-rules", { headers }),
        manage ? fetch("/api/equipment-reference/imports?limit=20", { headers }) : Promise.resolve(null),
      ]);
      if (correctionsResponse.status === 401) clearSession();
      if (!loads.current.isLatest(ticket)) return;
      if (!correctionsResponse.ok) {
        setLoadError(await readErrorDetail(correctionsResponse, "The corrections could not be loaded."));
        return;
      }
      setLoadError("");
      const sent = (await correctionsResponse.json()) as { value_rules: ValueRule[]; corrections: CorrectionToSend[] };
      setRules(sent.value_rules);
      setCorrections(sent.corrections);
      if (categoryResponse.ok) setCategoryRules((await categoryResponse.json()) as CategoryRule[]);
      if (importsResponse && importsResponse.ok) setImports((await importsResponse.json()) as ImportSummary[]);
    } catch {
      if (loads.current.isLatest(ticket)) setLoadError("Network error while loading.");
    }
  }

  useEffect(() => {
    const manage = canManageEquipment(readRoleCodes());
    setCanManage(manage);
    void load(manage);
    const refresh = () => void load(canManageEquipment(readRoleCodes()));
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
  }, []);

  async function upload() {
    const token = getToken();
    if (!token || !file) return;
    if (file.size > MAX_BYTES) {
      setUploadFeedback({ kind: "error", text: "This file is larger than the 5 MB limit." });
      return;
    }
    setUploading(true);
    setUploadFeedback(null);
    try {
      const form = new FormData();
      form.append("report_date", reportDate);
      form.append("file", file);
      const response = await fetch("/api/equipment-reference/imports", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
      if (response.status === 401) clearSession();
      if (!response.ok) {
        setUploadFeedback({ kind: "error", text: await readErrorDetail(response, "The report was not read.") });
        return;
      }
      const result = (await response.json()) as { equipment_import: EquipmentImport; replayed: boolean };
      window.location.href = `/equipment/plum-report/${result.equipment_import.import_public_id}${result.replayed ? "?waiting=1" : ""}`;
    } catch {
      setUploadFeedback({ kind: "error", text: "Network error: the report may not have been read." });
    } finally {
      setUploading(false);
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="Equipment"
        title="Plum report"
        subtitle="Upload Plum's Own Vehicle Complete Information Report as CSV. The platform shows what would change and every doubtful value; nothing changes until you confirm. The file itself is not kept."
      >
        {loadError ? <p className="text-danger">{loadError}</p> : null}
      </PageHeader>
      <EquipmentNav current="/equipment/plum-report" />

      {canManage ? (
        <SectionCard title="Upload a report">
          <div className="form-grid">
            <label className="field-stack">
              Report file (CSV, up to 5 MB)
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  setUploadFeedback(null);
                }}
              />
            </label>
            <label className="field-stack">
              Report date
              <DateInput value={reportDate} max={todayInIndia()} onChange={(event) => { setReportDate(event.target.value); setUploadFeedback(null); }} />
            </label>
          </div>
          <button type="button" disabled={uploading || !file || !reportDate} onClick={() => void upload()}>
            {uploading ? "Reading the report..." : "Upload and preview"}
          </button>
          <FeedbackLine feedback={uploadFeedback} />
        </SectionCard>
      ) : (
        <p className="helper-text">
          Only Admin uploads and confirms Plum's report.
        </p>
      )}

      {canManage ? (
        <SectionCard title="Reports uploaded">
          {imports.length === 0 ? <p className="helper-text">No report uploaded yet.</p> : null}
          {imports.length ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Report date</th>
                  <th>Status</th>
                  <th>Rows</th>
                  <th>What it does</th>
                  <th>Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {imports.map((item) => (
                  <tr key={item.import_public_id}>
                    <td>
                      <a href={`/equipment/plum-report/${item.import_public_id}`}>
                        {item.report_date}
                      </a>
                    </td>
                    <td>{IMPORT_STATUS_LABELS[item.import_status_code] ?? item.import_status_code}</td>
                    <td>{item.row_count}</td>
                    <td>{countsText(item.counts)}</td>
                    <td>
                      {item.uploaded_by_display_name ?? "-"}, {formatDateTime(item.uploaded_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </SectionCard>
      ) : null}

      <SectionCard title="Corrections to send to Plum">
        <p className="helper-text">Every open reading and correction: what to ask Plum to fix at source. A machine correction closes itself when a confirmed report carries the corrected value.</p>
        {rules.length === 0 && corrections.length === 0 ? <p className="helper-text">Nothing to send.</p> : null}
        {rules.length ? (
          <>
            <h4>Values read another way, wherever they appear</h4>
            <ul>
              {rules.map((rule) => (
                <li key={rule.rule_public_id}>
                  {FIELD_LABELS[rule.column_code] ?? rule.column_code}: {rule.value_withheld ? `(${WITHHELD_TEXT.toLowerCase()})` : `"${rule.plum_value}"`} is read as {valueRuleText(rule)}. {reasonText(rule.reason)}
                  {rule.rows_in_latest_report !== null ? ` (${rule.rows_in_latest_report} rows in the latest confirmed report)` : ""}
                </li>
              ))}
            </ul>
          </>
        ) : null}
        {corrections.length ? (
          <>
            <h4>One machine's value</h4>
            <ul>
              {corrections.map((correction) => (
                <li key={correction.correction_public_id}>
                  <a href={`/equipment/machines/${correction.asset_public_id}`}>
                    {correction.machine_number}
                  </a>{" "}
                  - {FIELD_LABELS[correction.field_code] ?? correction.field_code}: {correctionValuesText(correction)} {reasonText(correction.reason)}
                  {correction.plum_changed ? " Plum now holds yet another value." : ""}
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="What Plum's capacity figure is taken to mean">
        <p className="helper-text">Used only to check Plum's figure against the model; nothing is taken from it. Changed by a migration.</p>
        <table className="data-table">
          <thead>
            <tr>
              <th>Plum category</th>
              <th>Kind</th>
              <th>Figure is</th>
              <th>Plausible</th>
            </tr>
          </thead>
          <tbody>
            {categoryRules.map((rule) => (
              <tr key={rule.category}>
                <td>{rule.category}</td>
                <td>{rule.class_label}</td>
                <td>
                  {rule.check_code === "CHECKED" ? `${rule.capability_label}, in ${rule.plum_unit_code?.toLowerCase()}s` : rule.check_code === "UNIT_UNCLEAR" ? "Unclear: flagged" : "Not checked"}
                </td>
                <td>{rule.check_code === "CHECKED" ? `${plainNumber(rule.plausible_low)} to ${plainNumber(rule.plausible_high)}` : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionCard>
    </section>
  );
}
