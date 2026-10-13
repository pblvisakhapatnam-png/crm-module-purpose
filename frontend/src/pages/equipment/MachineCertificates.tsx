import { useEffect, useLayoutEffect, useRef, useState } from "react";

import DocumentsPanel, { CERTIFICATE_DOCUMENT_TYPES } from "../../components/DocumentsPanel";
import { SectionCard, StatusBadge } from "../../components/PageLayout";
import { SESSION_CHANGED_EVENT, clearSession, getToken, readErrorDetail, readRoleCodes } from "../resource-requirements/pageSession";
import { createLatestOnly } from "../resource-requirements/resourceRequirementState";
import { FeedbackLine } from "./EquipmentParts";
import {
  ANSWER_LABELS,
  EFFECT_LABELS,
  EMPTY_CERTIFICATE_FORM,
  EMPTY_MARK_FORM,
  type AssetCertificates,
  type CertificateAction,
  type CertificateForm,
  type CertificateKind,
  type CheckForm,
  type EligibilityCheck,
  type Jurisdiction,
  type KindStatus,
  type MarkForm,
  answerTone,
  createQueryController,
  initialQueryView,
  otherCertificateText,
  otherMarkText,
  otherRecords,
  queryView,
  certificateFormProblem,
  certificatePayload,
  certificateText,
  checkFormProblem,
  checkQuery,
  formatDay,
  markFormProblem,
  markReason,
  markPayload,
  needsPieceMark,
  outcomeTone,
  pieceMarkText,
  resultText,
  ruleText,
  siteStates,
  statusText,
} from "./certificatesState";
import { type Feedback, canManageEquipment, newRequestKey } from "./equipmentState";
import DateInput from "../../components/DateInput";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

// A machine's certificates, and whether it may work at a site (ELG-1): on every asset's page - machine, fitted
// part or piece of kit. The Fleet Admin (Admin, for now) records certificates, attaches their copies, marks one
// "not applicable" where a rule allows it, and withdraws what was recorded by mistake. Everyone who sees
// machines sees each certificate's kind, issuer, dates and status; numbers and copies only Admin (Q6).

const BASE = "/api/eligibility";
const TODAY = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());

function addDays(iso: string, days: number): string {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);
}

type Withdrawing = { path: string; label: string } | null;

export default function MachineCertificates({ assetPublicId }: { assetPublicId: string }) {
  // Who may record and withdraw follows the session this component sees, not the page's first render.
  const [canManage, setCanManage] = useState(() => canManageEquipment(readRoleCodes()));
  const [loaded, setLoaded] = useState(initialQueryView<AssetCertificates>());
  const view = loaded.answer;
  const loadError = loaded.error;
  const [kinds, setKinds] = useState<CertificateKind[]>([]);
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [openForm, setOpenForm] = useState<"certificate" | "mark" | null>(null);
  // The certificate whose copies are shown, with the form to attach one.
  const [copyFor, setCopyFor] = useState<string | null>(null);
  const [withdrawing, setWithdrawing] = useState<Withdrawing>(null);
  const [feedback, setFeedback] = useState<Record<string, Feedback>>({});
  const [busy, setBusy] = useState(false);
  // Counts the changes made to the records from this page; a site check's answer goes with each (ELG1-R4-002).
  const [evidence, setEvidence] = useState(0);
  const evidenceChanged = () => setEvidence((count) => count + 1);

  // The asset's certificates: its query is the asset the page shows, and an answer is shown only for the latest
  // request (certificatesState.ts, createQueryController). Reloading the same asset keeps what is shown until the
  // answer comes, so an open copy panel and the messages beside the buttons stay; moving to another asset clears it.
  const [controller] = useState(() =>
    createQueryController<string, AssetCertificates>({
      initialQuery: assetPublicId,
      getToken,
      failure: "Network error: the certificates could not be loaded.",
      fetchAnswer: async (token, publicId) => {
        const response = await fetch(`${BASE}/assets/${encodeURIComponent(publicId)}/certificates`, { headers: { Authorization: `Bearer ${token}` } });
        if (response.status === 401) clearSession();
        if (!response.ok) throw new Error(await readErrorDetail(response, "The certificates could not be loaded."));
        return (await response.json()) as AssetCertificates;
      },
      show: (update) => setLoaded((current) => (update.kind === "loading" && current.answer ? current : queryView(current, update))),
    }),
  );
  const reload = () => void controller.refreshIf(assetPublicId);

  /** Everything shown for the asset goes at once: on moving to another asset, and on a session change - a new
   *  session may not see numbers or copies, so nothing loaded under the old one stays on screen while the page
   *  reads the asset again (independent review, round 3, ELG1-R3-002). */
  function forget() {
    setLoaded(initialQueryView<AssetCertificates>());
    setCopyFor(null);
    setOpenForm(null);
    setWithdrawing(null);
    setFeedback({});
    setBusy(false);
  }

  useEffect(() => {
    const changed = () => {
      forget();
      setCanManage(canManageEquipment(readRoleCodes()));
      void controller.refresh();
    };
    window.addEventListener(SESSION_CHANGED_EVENT, changed);
    window.addEventListener("storage", changed);
    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, changed);
      window.removeEventListener("storage", changed);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    forget();
    void controller.setQuery(assetPublicId);
    const token = getToken();
    if (!token) return;
    void (async () => {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const [kindsResponse, jurisdictionsResponse] = await Promise.all([fetch(`${BASE}/certificate-kinds`, { headers }), fetch(`${BASE}/jurisdictions`, { headers })]);
        if (kindsResponse.ok) setKinds((await kindsResponse.json()) as CertificateKind[]);
        if (jurisdictionsResponse.ok) setJurisdictions((await jurisdictionsResponse.json()) as Jurisdiction[]);
      } catch {
        // Labels and choices only: the certificates still show without them.
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetPublicId]);

  /** Send one of Admin's changes, then read this asset's certificates again - the answer's own view may be of
   *  another asset (a carrier's certificate withdrawn from its crane's page). An answer that comes after the page
   *  moved to another asset changes nothing on it: no message, no reload (independent review, round 2). */
  async function send(key: string, path: string, body: Record<string, unknown>, success: (result: CertificateAction) => string): Promise<CertificateAction | null> {
    const asked = assetPublicId;
    const token = getToken();
    if (!token) {
      setFeedback({ [key]: { kind: "error", text: SIGN_IN_FIRST } });
      return null;
    }
    setBusy(true);
    evidenceChanged();
    let message: Feedback;
    let result: CertificateAction | null = null;
    try {
      const response = await fetch(`${BASE}${path}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (response.status === 401) clearSession();
      if (response.ok) {
        result = (await response.json()) as CertificateAction;
        message = { kind: "success", text: success(result) };
      } else {
        message = { kind: "error", text: await readErrorDetail(response, "Nothing was saved.") };
      }
    } catch {
      message = { kind: "error", text: "Network error: the change may not have been saved. Reload to see." };
    }
    if (!controller.isCurrent(asked)) return null;
    evidenceChanged();
    setBusy(false);
    setFeedback({ [key]: message });
    if (result) void controller.refreshIf(asked);
    return result;
  }

  if (!view) {
    return (
      <SectionCard title="Certificates">
        {loadError ? <p className="text-danger">{loadError}</p> : <p className="helper-text">Loading the certificates...</p>}
      </SectionCard>
    );
  }

  const today = TODAY();
  const asset = view.asset;
  const isKit = asset.origin_code === "PLATFORM";
  const isPlumPart = asset.asset_kind_code === "PART" && !isKit;
  const kindsByCode = Object.fromEntries(kinds.map((kind) => [kind.kind_code, kind]));
  const others = otherRecords(view);
  const copyCertificate = view.certificates.find((item) => item.certificate_public_id === copyFor) ?? null;

  return (
    <>
      <SectionCard title="Certificates">
        {isPlumPart && view.fitted_to ? (
          <p className="helper-text">
            Its certificates count for the machine it is fitted to, <a href={`/equipment/machines/${view.fitted_to.asset_public_id}`}>{view.fitted_to.asset_reference}</a>.
          </p>
        ) : null}
        {view.fitted_parts.length ? <p className="helper-text">Certificates recorded on its fitted parts count for it, and show here marked with the part.</p> : null}
        {needsPieceMark(asset) ? <p className="helper-text">Match each certificate to this piece by its mark: {pieceMarkText(asset)}.</p> : null}
        {loadError ? <p className="text-danger">{loadError}</p> : null}

        {view.statuses.length === 0 ? (
          <p className="helper-text">No certificate is required of it by the rules.</p>
        ) : (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Certificate</th>
                  <th>Status</th>
                  <th>The paper</th>
                  <th>Copy</th>
                  {canManage ? <th>Change</th> : null}
                </tr>
              </thead>
              <tbody>
                {view.statuses.map((status) => (
                  <StatusRow
                    key={status.kind_code}
                    status={status}
                    today={today}
                    assetPublicId={assetPublicId}
                    fittedTo={view.fitted_to?.asset_reference ?? null}
                    canManage={canManage}
                    showCopies={!view.numbers_withheld}
                    copyOpen={copyFor === status.certificate?.certificate_public_id}
                    onCopies={(certificatePublicId) => setCopyFor(copyFor === certificatePublicId ? null : certificatePublicId)}
                    onWithdraw={setWithdrawing}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {withdrawing && canManage ? (
          <WithdrawForm
            label={withdrawing.label}
            busy={busy}
            onCancel={() => setWithdrawing(null)}
            onWithdraw={async (reason) => {
              const result = await send("withdraw", withdrawing.path, { reason }, (answer) => (answer.event ? "Withdrawn. The one before it, if any, is in force again." : "Already withdrawn: nothing changed."));
              if (result) setWithdrawing(null);
            }}
          />
        ) : null}
        <FeedbackLine feedback={feedback.withdraw} />

        {copyCertificate ? (
          <div className="section-form">
            <h5>
              Copies of the {copyCertificate.kind_label.toLowerCase()} on {copyCertificate.asset_reference}
            </h5>
            <DocumentsPanel
              linkedRecordType="eligibility_certificate"
              linkedRecordPublicId={copyCertificate.certificate_public_id}
              canUpload={canManage && copyCertificate.certificate_status_code === "RECORDED"}
              documentTypes={CERTIFICATE_DOCUMENT_TYPES}
              onUploaded={() => {
                evidenceChanged();
                reload();
              }}
            />
          </div>
        ) : null}

        {others.liveCertificates.length || others.liveMarks.length ? (
          <div className="section-form">
            <h5>Also recorded</h5>
            <ul className="compact-list">
              {others.liveCertificates.map((item) => (
                <li key={item.certificate_public_id}>
                  {item.kind_label} on {item.asset_reference}: {certificateText(item)} - {otherCertificateText(item, today)}; copy{" "}
                  {item.has_copy ? "attached" : "missing"}.{" "}
                  {!view.numbers_withheld ? (
                    <button type="button" onClick={() => setCopyFor(copyFor === item.certificate_public_id ? null : item.certificate_public_id)}>
                      {copyFor === item.certificate_public_id ? "Hide copies" : canManage && !item.has_copy ? "Attach its copy" : "Copies"}
                    </button>
                  ) : null}{" "}
                  {canManage ? (
                    <button type="button" onClick={() => setWithdrawing({ path: `/certificates/${item.certificate_public_id}/withdraw`, label: `the ${item.kind_label.toLowerCase()} on ${item.asset_reference}` })}>
                      Withdraw
                    </button>
                  ) : null}
                </li>
              ))}
              {others.liveMarks.map((item) => (
                <li key={item.mark_public_id}>
                  {item.kind_label} marked not applicable on {formatDay(item.recorded_on)}
                  {markReason(item)} -{" "}
                  {otherMarkText(item, today, view.statuses.some((status) => status.kind_code === item.kind_code && status.certificate !== null))}.{" "}
                  {canManage ? (
                    <button type="button" onClick={() => setWithdrawing({ path: `/not-applicable/${item.mark_public_id}/withdraw`, label: `the "not applicable" mark on the ${item.kind_label.toLowerCase()}` })}>
                      Withdraw mark
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {others.historyCertificates.length || others.historyMarks.length ? (
          <details className="secondary-disclosure">
            <summary>Earlier ({others.historyCertificates.length + others.historyMarks.length})</summary>
            <ul className="compact-list">
              {others.historyCertificates.map((item) => (
                <li key={item.certificate_public_id}>
                  {item.kind_label} on {item.asset_reference}: {certificateText(item)}. Withdrawn by {item.withdrawn_by_display_name ?? "-"}
                  {item.withdrawn_reason ? `: ${item.withdrawn_reason}` : ""}.{" "}
                  {!view.numbers_withheld ? (
                    <button type="button" onClick={() => setCopyFor(copyFor === item.certificate_public_id ? null : item.certificate_public_id)}>
                      {copyFor === item.certificate_public_id ? "Hide copies" : "Copies"}
                    </button>
                  ) : null}
                </li>
              ))}
              {others.historyMarks.map((item) => (
                <li key={item.mark_public_id}>
                  {item.kind_label} marked not applicable on {formatDay(item.recorded_on)}
                  {markReason(item)}. Withdrawn by {item.withdrawn_by_display_name ?? "-"}
                  {item.withdrawn_reason ? `: ${item.withdrawn_reason}` : ""}.
                </li>
              ))}
            </ul>
          </details>
        ) : null}

        {canManage && asset.asset_status_code === "ACTIVE" ? (
          <div className="section-form">
            {openForm === "certificate" ? (
              <CertificateFormFields
                choices={view.recordable_kind_codes.map((code) => kindsByCode[code]).filter(Boolean)}
                jurisdictions={jurisdictions}
                busy={busy}
                today={today}
                onCancel={() => setOpenForm(null)}
                onSave={async (body) => {
                  const result = await send("certificate", `/assets/${assetPublicId}/certificates`, body, (answer) =>
                    answer.replayed ? "Already recorded: nothing more was saved." : "Certificate recorded. Attach its copy below: it counts only with its copy.",
                  );
                  if (result) {
                    setOpenForm(null);
                    setCopyFor(result.certificate_public_id);
                  }
                }}
              />
            ) : openForm === "mark" ? (
              <MarkFormFields
                markable={view.markable_kinds}
                busy={busy}
                today={today}
                onCancel={() => setOpenForm(null)}
                onSave={async (body) => {
                  const result = await send("mark", `/assets/${assetPublicId}/not-applicable`, body, (answer) => (answer.replayed ? "Already marked: nothing more was saved." : "Marked not applicable."));
                  if (result) setOpenForm(null);
                }}
              />
            ) : (
              <div className="page-actions">
                {view.recordable_kind_codes.length ? (
                  <button type="button" onClick={() => setOpenForm("certificate")}>
                    Record a certificate
                  </button>
                ) : null}
                {view.markable_kinds.length ? (
                  <button type="button" onClick={() => setOpenForm("mark")}>
                    Mark not applicable
                  </button>
                ) : null}
              </div>
            )}
            <FeedbackLine feedback={feedback.certificate} />
            <FeedbackLine feedback={feedback.mark} />
          </div>
        ) : null}
      </SectionCard>

      <CheckSection view={view} jurisdictions={jurisdictions} evidence={evidence} />
    </>
  );
}

function StatusRow({
  status,
  today,
  assetPublicId,
  fittedTo,
  canManage,
  showCopies,
  copyOpen,
  onCopies,
  onWithdraw,
}: {
  status: KindStatus;
  today: string;
  assetPublicId: string;
  fittedTo: string | null;
  canManage: boolean;
  showCopies: boolean;
  copyOpen: boolean;
  onCopies: (certificatePublicId: string) => void;
  onWithdraw: (target: Withdrawing) => void;
}) {
  const { certificate, mark } = status;
  const elsewhere = certificate && certificate.asset_public_id !== assetPublicId ? certificate.asset_reference : null;
  return (
    <tr>
      <td>
        {status.kind_label}
        {status.required ? null : <div className="helper-text">{fittedTo ? `Counts for the machine it is fitted to, ${fittedTo}` : "Not required of it today"}</div>}
        {status.rule ? <div className="helper-text">{ruleText(status.rule)}</div> : null}
      </td>
      <td>
        {status.required ? <StatusBadge code={status.outcome_code} tone={outcomeTone(status.outcome_code)} label={statusText(status, today)} /> : statusText(status, today)}
      </td>
      <td className="text-break-anywhere">
        {certificate ? (
          <>
            {certificateText(certificate)}
            {elsewhere ? <div className="helper-text">On its fitted part {elsewhere}</div> : null}
          </>
        ) : mark ? (
          `Marked by ${mark.recorded_by_display_name ?? "-"} on ${formatDay(mark.recorded_on)}`
        ) : (
          "-"
        )}
      </td>
      <td className="cell-actions">
        {certificate ? (
          <>
            {certificate.has_copy ? "Attached" : "Missing"}
            {showCopies ? (
              <>
                {" "}
                <button type="button" onClick={() => onCopies(certificate.certificate_public_id)}>
                  {copyOpen ? "Hide copies" : canManage && !certificate.has_copy ? "Attach its copy" : "Copies"}
                </button>
              </>
            ) : null}
          </>
        ) : (
          "-"
        )}
      </td>
      {canManage ? (
        <td className="cell-actions">
          {certificate ? (
            <button type="button" onClick={() => onWithdraw({ path: `/certificates/${certificate.certificate_public_id}/withdraw`, label: `the ${certificate.kind_label.toLowerCase()} on ${certificate.asset_reference}` })}>
              Withdraw
            </button>
          ) : mark ? (
            <button type="button" onClick={() => onWithdraw({ path: `/not-applicable/${mark.mark_public_id}/withdraw`, label: `the "not applicable" mark on the ${mark.kind_label.toLowerCase()}` })}>
              Withdraw mark
            </button>
          ) : null}
        </td>
      ) : null}
    </tr>
  );
}

function WithdrawForm({ label, busy, onCancel, onWithdraw }: { label: string; busy: boolean; onCancel: () => void; onWithdraw: (reason: string) => void }) {
  const [reason, setReason] = useState("");
  return (
    <div className="form-grid section-form">
      <label className="field-stack">
        Why withdraw {label}? It stays in the history.
        <input value={reason} onChange={(event) => setReason(event.target.value)} maxLength={1000} />
      </label>
      <div className="form-actions">
        <button type="button" disabled={busy || !reason.trim()} onClick={() => onWithdraw(reason.trim())}>
          Withdraw
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function CertificateFormFields({
  choices,
  jurisdictions,
  busy,
  today,
  onSave,
  onCancel,
}: {
  choices: CertificateKind[];
  jurisdictions: Jurisdiction[];
  busy: boolean;
  today: string;
  onSave: (body: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<CertificateForm>(EMPTY_CERTIFICATE_FORM);
  // The form's own request key: a double click records once.
  const [requestKey] = useState(newRequestKey);
  const kind = choices.find((item) => item.kind_code === form.kindCode);
  const problem = certificateFormProblem(form, kind, today);
  const edit = (next: Partial<CertificateForm>) => setForm({ ...form, ...next });
  return (
    <div className="form-grid">
      <label className="field-stack">
        Certificate
        <select value={form.kindCode} onChange={(event) => edit({ kindCode: event.target.value, validIn: "", registeredAs: "" })}>
          <option value="">Choose a certificate</option>
          {choices.map((item) => (
            <option key={item.kind_code} value={item.kind_code}>
              {item.kind_label}
            </option>
          ))}
        </select>
      </label>
      <label className="field-stack">
        Number, as printed
        <input value={form.number} onChange={(event) => edit({ number: event.target.value })} maxLength={200} />
      </label>
      <label className="field-stack">
        Issued by
        <input value={form.issuedBy} onChange={(event) => edit({ issuedBy: event.target.value })} maxLength={200} placeholder="Insurer, RTO, or competent person and recognition number" />
      </label>
      <label className="field-stack">
        Issued on (the examination's day)
        <DateInput value={form.issuedOn} onChange={(event) => edit({ issuedOn: event.target.value })} />
      </label>
      <label className="field-stack">
        Valid from
        <DateInput value={form.validFrom} onChange={(event) => edit({ validFrom: event.target.value })} />
      </label>
      <label className="field-stack">
        Valid until{kind?.end_date_optional ? " (optional)" : ""}
        <DateInput value={form.validUntil} onChange={(event) => edit({ validUntil: event.target.value })} />
      </label>
      {kind?.valid_in_required ? (
        <label className="field-stack">
          Valid in
          <select value={form.validIn} onChange={(event) => edit({ validIn: event.target.value })}>
            <option value="">Choose where</option>
            <option value="IN">All India (a national permit)</option>
            {siteStates(jurisdictions).map((item) => (
              <option key={item.jurisdiction_code} value={item.jurisdiction_code}>
                {item.jurisdiction_label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {kind?.states_registration ? (
        <label className="field-stack">
          Registered as
          <select value={form.registeredAs} onChange={(event) => edit({ registeredAs: event.target.value })}>
            <option value="">As the certificate says</option>
            <option value="NON_TRANSPORT">Non-transport vehicle</option>
            <option value="TRANSPORT">Transport vehicle</option>
          </select>
        </label>
      ) : null}
      <div className="form-actions">
        <button type="button" disabled={busy || Boolean(problem)} onClick={() => kind && onSave(certificatePayload(form, kind, requestKey))}>
          Record certificate
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
        {kind?.end_date_optional ? <p className="helper-text">Leave "valid until" empty for a one-time road tax, or an examination the rules' interval sets.</p> : null}
        {form.kindCode && problem ? <p className="helper-text">{problem}</p> : null}
      </div>
    </div>
  );
}

function MarkFormFields({
  markable,
  busy,
  today,
  onSave,
  onCancel,
}: {
  markable: AssetCertificates["markable_kinds"];
  busy: boolean;
  today: string;
  onSave: (body: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<MarkForm>(EMPTY_MARK_FORM);
  const [requestKey] = useState(newRequestKey);
  const chosen = markable.find((item) => item.kind_code === form.kindCode);
  const problem = markFormProblem(form, chosen, today);
  const edit = (next: Partial<MarkForm>) => setForm({ ...form, ...next });
  return (
    <div className="form-grid">
      <label className="field-stack">
        Certificate that does not apply
        <select value={form.kindCode} onChange={(event) => edit({ kindCode: event.target.value })}>
          <option value="">Choose a certificate</option>
          {markable.map((item) => (
            <option key={item.kind_code} value={item.kind_code}>
              {item.kind_label}
            </option>
          ))}
        </select>
      </label>
      <label className="field-stack">
        Why it does not apply
        <input value={form.reason} onChange={(event) => edit({ reason: event.target.value })} maxLength={1000} />
      </label>
      <label className="field-stack">
        Until{chosen?.latest_until ? ` (no later than ${formatDay(chosen.latest_until)})` : " (optional)"}
        <DateInput value={form.until} onChange={(event) => edit({ until: event.target.value })} />
      </label>
      <div className="form-actions">
        <button type="button" disabled={busy || Boolean(problem)} onClick={() => onSave(markPayload(form, requestKey))}>
          Mark not applicable
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
        {chosen?.rule.note ? <p className="helper-text">{chosen.rule.note}</p> : null}
        {form.kindCode && problem ? <p className="helper-text">{problem}</p> : null}
      </div>
    </div>
  );
}

function CheckSection({ view, jurisdictions, evidence }: { view: AssetCertificates; jurisdictions: Jurisdiction[]; evidence: number }) {
  const asset = view.asset;
  const isKit = asset.origin_code === "PLATFORM";
  const [form, setForm] = useState<CheckForm>(() => ({ stateCode: "", central: false, from: TODAY(), to: addDays(TODAY(), 30) }));
  const [answer, setAnswer] = useState<EligibilityCheck | null>(null);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [busy, setBusy] = useState(false);
  // Only the latest check's answer is shown, and only while the form still says what it was asked for.
  const checks = useRef(createLatestOnly());
  const problem = checkFormProblem(form);
  const labels = Object.fromEntries(jurisdictions.map((item) => [item.jurisdiction_code, item.jurisdiction_label]));
  /** No answer is shown, and none on its way will be. */
  const forgetAnswer = () => {
    checks.current.begin();
    setAnswer(null);
    setFeedback(null);
    setBusy(false);
  };
  const edit = (next: Partial<CheckForm>) => {
    forgetAnswer();
    setForm({ ...form, ...next });
  };
  // An answer is about the records as they stood when asked. A change made here - a certificate or mark recorded or
  // withdrawn, a copy attached - or the certificates read again takes it away before the screen shows the new
  // records, and a check still on its way is not shown (independent review, round 4, ELG1-R4-002).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useLayoutEffect(() => forgetAnswer(), [evidence, view]);

  if (asset.asset_kind_code === "PART" && !isKit) {
    return (
      <SectionCard title="Check for a site">
        <p className="helper-text">
          A fitted part is checked with the machine it is fitted to
          {view.fitted_to ? (
            <>
              : <a href={`/equipment/machines/${view.fitted_to.asset_public_id}`}>{view.fitted_to.asset_reference}</a>
            </>
          ) : null}
          .
        </p>
      </SectionCard>
    );
  }

  async function check() {
    const token = getToken();
    if (!token) {
      setFeedback({ kind: "error", text: SIGN_IN_FIRST });
      return;
    }
    const ticket = checks.current.begin();
    const asked = checkQuery(form);
    setAnswer(null);
    setBusy(true);
    try {
      const response = await fetch(`${BASE}/assets/${asset.asset_public_id}/check?${asked}`, { headers: { Authorization: `Bearer ${token}` } });
      if (response.status === 401) clearSession();
      const failure = response.ok ? "" : await readErrorDetail(response, "The check could not be made.");
      const body = response.ok ? ((await response.json()) as EligibilityCheck) : null;
      if (!checks.current.isLatest(ticket)) return;
      setAnswer(body);
      setFeedback(failure ? { kind: "error", text: failure } : null);
    } catch {
      if (checks.current.isLatest(ticket)) setFeedback({ kind: "error", text: "Network error: the check could not be made." });
    } finally {
      if (checks.current.isLatest(ticket)) setBusy(false);
    }
  }

  return (
    <SectionCard title={isKit ? "Check for a Trip (Own Load)" : "Check for a site"}>
      <p className="helper-text">
        {isKit ? "Whether this piece may go to a site over a period. Kit is checked piece by piece." : "Whether it may work at a site over a period, with its fitted parts."} Nothing is kept.
      </p>
      <div className="form-grid">
        <label className="field-stack">
          The site's state
          <select value={form.stateCode} onChange={(event) => edit({ stateCode: event.target.value })}>
            <option value="">Choose a state or union territory</option>
            {siteStates(jurisdictions).map((item) => (
              <option key={item.jurisdiction_code} value={item.jurisdiction_code}>
                {item.jurisdiction_label}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack">
          From
          <DateInput value={form.from} onChange={(event) => edit({ from: event.target.value })} />
        </label>
        <label className="field-stack">
          To (empty: open-ended)
          <DateInput value={form.to} onChange={(event) => edit({ to: event.target.value })} />
        </label>
        <label>
          <input type="checkbox" checked={form.central} onChange={(event) => edit({ central: event.target.checked })} /> A central government site: a central public
          sector plant, a railway or metro, a major port, an oil field or a mine
        </label>
        <div className="form-actions">
          <button type="button" disabled={busy || Boolean(problem)} onClick={() => void check()}>
            {busy ? "Checking..." : "Check"}
          </button>
          {form.stateCode && problem ? <p className="helper-text">{problem}</p> : null}
        </div>
      </div>
      <FeedbackLine feedback={feedback} />

      {answer ? (
        <div className="section-form" aria-live="polite">
          <p>
            <StatusBadge code={answer.overall_code} tone={answerTone(answer.overall_code)} label={ANSWER_LABELS[answer.overall_code] ?? answer.overall_code} /> at a site in{" "}
            {answer.site_state_label}
            {answer.central_government_site ? " (a central government site)" : ""}, from {formatDay(answer.period_from)}
            {answer.period_to ? ` to ${formatDay(answer.period_to)}` : ", open-ended"}.
            {answer.valid_until ? ` The answer holds until ${formatDay(answer.valid_until)}.` : ""}
          </p>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>For</th>
                  <th>Certificate</th>
                  <th>Found</th>
                  <th>What it does</th>
                </tr>
              </thead>
              <tbody>
                {answer.results.map((result, index) => (
                  <tr key={`${result.asset_public_id}-${result.kind_code ?? "asset"}-${index}`}>
                    <td>{result.asset_reference}</td>
                    <td>
                      {result.kind_label ?? "The asset itself"}
                      {result.rule_jurisdiction_code ? <div className="helper-text">{labels[result.rule_jurisdiction_code] ?? result.rule_jurisdiction_code}'s rule</div> : null}
                    </td>
                    <td>
                      <StatusBadge code={result.outcome_code} tone={outcomeTone(result.outcome_code)} label={resultText(result)} />
                      {result.certificate_asset_reference && result.certificate_asset_reference !== result.asset_reference ? (
                        <div className="helper-text">On its fitted part {result.certificate_asset_reference}</div>
                      ) : null}
                    </td>
                    <td>{EFFECT_LABELS[result.effect_code] ?? result.effect_code}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </SectionCard>
  );
}
