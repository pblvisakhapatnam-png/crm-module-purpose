import { useEffect, useState } from "react";

import { SectionCard } from "../../components/PageLayout";
import { formatTermDate } from "./workOrderBillingTermsState";
import {
  CONTRACT_END_FIXED_DATE,
  CONTRACT_END_OPTIONS,
  contractPeriodPayload,
  defaultExtensionStart,
  endDateLockedByExtensions,
  extensionOrderDateWarning,
  extensionSummary,
  formAfterEndBasisChange,
  formFromContractPeriod,
  gapBeforeStart,
  gapConfirmationText,
  gapText,
  indiaToday,
  latestExtension,
  missingContractDatesText,
  removeExtensionConfirmationText,
  type ContractPeriod,
  type ContractPeriodForm,
} from "./workOrderContractPeriodState";
import DateInput from "../../components/DateInput";

// Slice 7D Part 3: the Work Order's contract start and end dates, and the extensions that move the
// end. The dates are the Work Order's; a line may carry its own inside them, which is recorded with
// the line's site and billing details (owner decision 13). When equipment actually arrives and leaves
// is a different thing, and comes later from mobilisation and log sheets.
//
// The backend re-checks every rule and writes every refusal message shown here; hiding the form from
// a read-only role is a convenience, not the control.

type Feedback = { kind: "success" | "error"; text: string } | null;

const FIELD_STYLE = { width: "100%" } as const;
const SAVE_BUTTON_STYLE = { padding: "8px 12px", fontWeight: 700 } as const;

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return "Check the dates entered: one of them is not accepted.";
  } catch {
    // fall through
  }
  return `The contract dates could not be saved. HTTP ${response.status}.`;
}

function FeedbackLine({ feedback }: { feedback: Feedback }) {
  if (!feedback) return null;
  return (
    <p className={feedback.kind === "success" ? "text-success" : "text-danger"} style={{ margin: "6px 0 0 0" }}>
      {feedback.text}
    </p>
  );
}

type Props = {
  workOrderPublicId: string;
  period: ContractPeriod | null;
  periodLoaded: boolean;
  periodError: string;
  canEdit: boolean;
  isClosed: boolean;
  token: string | null;
  // The page-load generation this section was rendered for. Every write hands it back, so a save that
  // finishes after a newer page load has started is discarded instead of applied over it.
  loadGeneration: number;
  onApplied: (period: ContractPeriod, loadGeneration: number) => void;
};

export default function WorkOrderContractPeriodSection(props: Props) {
  const { period, canEdit, isClosed, periodLoaded } = props;
  const editable = canEdit && !isClosed && periodLoaded;

  return (
    <SectionCard title="Contract period">
      <p style={{ marginTop: 0 }}>
        The dates the customer's Work Order runs between. A line that runs to different dates carries its own,
        recorded with its site and billing details; a line left blank follows the Work Order. When equipment actually
        arrives on site and leaves is recorded later, from mobilisation and log sheets.
      </p>
      {isClosed ? (
        <p style={{ color: "#6b7280" }}>This Work Order is closed, so its contract dates can no longer be changed.</p>
      ) : null}
      {props.periodError ? <p className="text-danger">{props.periodError}</p> : null}
      {!periodLoaded && !props.periodError ? <p className="helper-text">Loading the contract dates...</p> : null}

      {period ? (
        <p style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap", margin: "0 0 12px 0" }}>
          <span className="status-badge">{period.contract_state_label}</span>
          <span className="status-badge">{missingContractDatesText(period)}</span>
        </p>
      ) : null}

      {period?.needs_firm_end_date ? (
        <p style={{ margin: "0 0 12px 0" }}>
          This Work Order runs until the work is complete. It cannot be closed until a firm end date is recorded -
          either by recording it below, or by recording the extension the customer sends.
        </p>
      ) : null}

      {period ? <ContractPeriodForm {...props} period={period} editable={editable} /> : null}
      {period ? <ExtensionHistory {...props} period={period} editable={editable} /> : null}
    </SectionCard>
  );
}

function ContractPeriodForm({
  workOrderPublicId,
  period,
  editable,
  token,
  loadGeneration,
  onApplied,
}: Props & { period: ContractPeriod; editable: boolean }) {
  const [form, setForm] = useState<ContractPeriodForm>(() => formFromContractPeriod(period));
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const endDateLocked = endDateLockedByExtensions(period);

  // A newer version from the server - this save's own, or another page load's - replaces the form.
  useEffect(() => {
    setForm(formFromContractPeriod(period));
  }, [period.period_version, period.work_order_public_id]);

  function change(next: ContractPeriodForm) {
    // The user's own edit clears a stale message; the post-save reset above does not, so the
    // confirmation survives it (the Slice 9D lesson, carried forward).
    setFeedback(null);
    setForm(next);
  }

  async function save() {
    if (!token) {
      setFeedback({ kind: "error", text: "Your session has ended. Sign in again, then save the dates." });
      return;
    }
    setSaving(true);
    setFeedback(null);
    try {
      const response = await fetch(`/api/work-orders/${encodeURIComponent(workOrderPublicId)}/contract-period`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(contractPeriodPayload(form, period.period_version)),
      });
      if (response.status === 409) {
        setFeedback({
          kind: "error",
          text: "These dates have changed since the page loaded. Reload to see the latest version.",
        });
        return;
      }
      if (!response.ok) {
        setFeedback({ kind: "error", text: await readErrorDetail(response) });
        return;
      }
      const body = (await response.json()) as { contract_period: ContractPeriod; event: unknown };
      onApplied(body.contract_period, loadGeneration);
      setFeedback({
        kind: "success",
        text: body.event ? "Contract dates saved." : "Nothing changed, so nothing was saved.",
      });
    } catch {
      setFeedback({ kind: "error", text: "Network error while saving the contract dates. Try again." });
    } finally {
      setSaving(false);
    }
  }

  if (!editable) {
    return (
      <dl style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: "8px 12px", margin: 0 }}>
        <dt style={{ color: "#6b7280", fontWeight: 700 }}>Contract starts</dt>
        <dd style={{ margin: 0 }}>
          {period.contract_start_date ? formatTermDate(period.contract_start_date) : "Not recorded"}
        </dd>
        <dt style={{ color: "#6b7280", fontWeight: 700 }}>Contract ends</dt>
        <dd style={{ margin: 0 }}>{endDateText(period)}</dd>
        {period.contract_notes ? (
          <>
            <dt style={{ color: "#6b7280", fontWeight: 700 }}>Notes</dt>
            <dd style={{ margin: 0 }}>{period.contract_notes}</dd>
          </>
        ) : null}
      </dl>
    );
  }

  return (
    <div className="terms-subgrid">
      <label className="field-stack">
        Contract starts on
        <DateInput
          value={form.contract_start_date}
          onChange={(event) => change({ ...form, contract_start_date: event.target.value })}
          style={FIELD_STYLE}
        />
      </label>
      {endDateLocked ? (
        // Once an extension exists the end moves only through extensions (owner, 22 September 2026);
        // the server refuses a save that changes it, so it is shown, not offered.
        <div className="field-stack">
          Contract ends on
          <strong>{endDateText(period)}</strong>
          <span className="helper-text">
            Set by the extensions below. To change it, record another extension, or remove the latest one.
          </span>
        </div>
      ) : (
        <>
          <label className="field-stack">
            Contract ends
            <select
              value={form.contract_end_basis_code}
              onChange={(event) => change(formAfterEndBasisChange(form, event.target.value))}
              style={FIELD_STYLE}
            >
              {CONTRACT_END_OPTIONS.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {form.contract_end_basis_code === CONTRACT_END_FIXED_DATE ? (
            <label className="field-stack">
              Contract ends on
              <DateInput
                value={form.contract_end_date}
                onChange={(event) => change({ ...form, contract_end_date: event.target.value })}
                style={FIELD_STYLE}
              />
            </label>
          ) : null}
        </>
      )}
      <label className="field-stack terms-wide">
        Notes about the contract period
        <textarea
          rows={2}
          value={form.contract_notes}
          onChange={(event) => change({ ...form, contract_notes: event.target.value })}
          style={FIELD_STYLE}
        />
      </label>
      <div className="terms-wide">
        <button type="button" disabled={saving} onClick={() => void save()} style={SAVE_BUTTON_STYLE}>
          {saving ? "Saving..." : "Save contract dates"}
        </button>
        <FeedbackLine feedback={feedback} />
      </div>
    </div>
  );
}

function endDateText(period: ContractPeriod): string {
  if (period.contract_end_date) return formatTermDate(period.contract_end_date);
  if (period.needs_firm_end_date) return "Until the work is complete";
  return "Not recorded";
}

function ExtensionHistory({
  workOrderPublicId,
  period,
  editable,
  token,
  loadGeneration,
  onApplied,
}: Props & { period: ContractPeriod; editable: boolean }) {
  const [newEndDate, setNewEndDate] = useState("");
  const [receivedDate, setReceivedDate] = useState("");
  const [customerReference, setCustomerReference] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [removing, setRemoving] = useState(false);
  const [removeFeedback, setRemoveFeedback] = useState<Feedback>(null);
  // Normally the day after the fixed end it follows (owner, 22 September 2026). Offered only when there
  // is a fixed end to follow; refilled whenever a newer version of the dates arrives.
  const normalStart = defaultExtensionStart(period);
  const [startDate, setStartDate] = useState(normalStart);
  useEffect(() => {
    setStartDate(defaultExtensionStart(period));
  }, [period.period_version, period.work_order_public_id]);
  const latest = latestExtension(period);
  const receivedDateWarning = receivedDate ? extensionOrderDateWarning(receivedDate, indiaToday()) : null;
  const startGap = normalStart ? gapBeforeStart(period, startDate) : null;

  async function removeLatest() {
    if (!latest) return;
    if (!token) {
      setRemoveFeedback({ kind: "error", text: "Your session has ended. Sign in again, then remove the extension." });
      return;
    }
    if (!window.confirm(removeExtensionConfirmationText(latest))) return;
    setRemoving(true);
    setRemoveFeedback(null);
    setFeedback(null);
    try {
      const response = await fetch(
        `/api/work-orders/${encodeURIComponent(workOrderPublicId)}/contract-extensions/${encodeURIComponent(latest.extension_public_id)}`,
        { method: "DELETE", headers: { Authorization: `Bearer ${token}` } },
      );
      if (response.status === 404) {
        setRemoveFeedback({
          kind: "error",
          text: "That extension has already been removed. Reload to see the latest version.",
        });
        return;
      }
      if (!response.ok) {
        setRemoveFeedback({ kind: "error", text: await readErrorDetail(response) });
        return;
      }
      const body = (await response.json()) as { contract_period: ContractPeriod };
      onApplied(body.contract_period, loadGeneration);
      setRemoveFeedback({ kind: "success", text: "Extension removed, and the contract end date put back." });
    } catch {
      setRemoveFeedback({ kind: "error", text: "Network error while removing the extension. Try again." });
    } finally {
      setRemoving(false);
    }
  }

  async function record() {
    if (!token) {
      setFeedback({ kind: "error", text: "Your session has ended. Sign in again, then record the extension." });
      return;
    }
    // A later start leaves days outside the contract, so it is recorded only once the user agrees
    // (owner: it needs confirmation, else it can be recorded). The server refuses it without this.
    if (startGap && !window.confirm(gapConfirmationText(period, startDate))) return;
    setSaving(true);
    setFeedback(null);
    setRemoveFeedback(null);
    try {
      const response = await fetch(`/api/work-orders/${encodeURIComponent(workOrderPublicId)}/contract-extensions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          new_end_date: newEndDate || null,
          received_date: receivedDate || null,
          extension_start_date: normalStart ? startDate || null : null,
          // The first day of the gap the user agreed to, so the server can tell if the end moved since.
          gap_confirmed_from: startGap ? startGap.first : null,
          customer_reference: customerReference.trim() ? customerReference : null,
          extension_notes: notes.trim() ? notes : null,
        }),
      });
      if (!response.ok) {
        setFeedback({ kind: "error", text: await readErrorDetail(response) });
        return;
      }
      const body = (await response.json()) as { contract_period: ContractPeriod };
      onApplied(body.contract_period, loadGeneration);
      setNewEndDate("");
      setReceivedDate("");
      setCustomerReference("");
      setNotes("");
      setFeedback({ kind: "success", text: "Extension recorded, and the contract end date moved to it." });
    } catch {
      setFeedback({ kind: "error", text: "Network error while recording the extension. Try again." });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ marginTop: "16px" }}>
      <h4 style={{ margin: "0 0 6px 0" }}>Extensions</h4>
      <p style={{ margin: "0 0 10px 0", color: "#6b7280" }}>
        Each extension the customer sends is recorded here, and moves the contract end date to a later one. Earlier end
        dates stay in this list, so what the contract said at any time can still be read. Once an extension is recorded,
        the end date changes only here. If an extension was recorded in error, remove it: only the most recent can be
        removed, the end date goes back to what it was before, and the removal is kept in the audit log. An
        extension normally starts the day after the contract ends; a later start leaves days outside the contract,
        and you are asked to confirm it.{" "}
        <strong>Approval step not yet added.</strong>
      </p>

      {period.extensions.length > 0 ? (
        <div className="data-table-wrap" style={{ marginTop: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>End date moved</th>
                <th>Customer reference</th>
                <th>Order received on</th>
                <th>Recorded by</th>
                {editable ? <th aria-label="Actions" /> : null}
              </tr>
            </thead>
            <tbody>
              {period.extensions.map((extension) => (
                <tr key={extension.extension_public_id}>
                  <td>{extension.extension_sequence_no}</td>
                  <td>
                    {extensionSummary(extension)}
                    {extension.extension_notes ? (
                      <div style={{ color: "#6b7280" }}>{extension.extension_notes}</div>
                    ) : null}
                  </td>
                  <td>{extension.customer_reference || "-"}</td>
                  <td>{formatTermDate(extension.received_date)}</td>
                  <td>{extension.created_by_display_name || "-"}</td>
                  {editable ? (
                    <td>
                      {latest && extension.extension_public_id === latest.extension_public_id ? (
                        <button type="button" disabled={removing || saving} onClick={() => void removeLatest()}>
                          {removing ? "Removing..." : "Remove"}
                        </button>
                      ) : null}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p style={{ color: "#6b7280" }}>No extension has been recorded for this Work Order.</p>
      )}
      {period.gaps.map((gap) => (
        <p key={gap.extension_sequence_no} className="text-warning" style={{ margin: "6px 0 0 0" }}>
          {gapText(gap)}
        </p>
      ))}
      {/* Outside the table, so the confirmation survives removing the last extension, which removes the table. */}
      <FeedbackLine feedback={removeFeedback} />

      {editable ? (
        <div className="terms-secondary-box" style={{ marginTop: "12px" }}>
          <div className="terms-subgrid">
            {normalStart ? (
              <label className="field-stack">
                The extension starts on
                <DateInput
                  value={startDate}
                  onChange={(event) => {
                    setFeedback(null);
                    setStartDate(event.target.value);
                  }}
                  style={FIELD_STYLE}
                />
                <span className="helper-text">Normally the day after the contract ends.</span>
                {startGap ? (
                  <span className="text-warning">
                    The days from {formatTermDate(startGap.first)} to {formatTermDate(startGap.last)} will be outside
                    the contract. You will be asked to confirm.
                  </span>
                ) : null}
              </label>
            ) : null}
            <label className="field-stack">
              The contract now ends on
              <DateInput
                value={newEndDate}
                onChange={(event) => {
                  setFeedback(null);
                  setNewEndDate(event.target.value);
                }}
                style={FIELD_STYLE}
              />
            </label>
            <label className="field-stack">
              Extension order received on
              <DateInput
                value={receivedDate}
                onChange={(event) => {
                  setFeedback(null);
                  setReceivedDate(event.target.value);
                }}
                style={FIELD_STYLE}
              />
              {receivedDateWarning ? <span className="text-warning">{receivedDateWarning}</span> : null}
            </label>
            <label className="field-stack">
              Customer's reference
              <input
                type="text"
                maxLength={255}
                value={customerReference}
                onChange={(event) => {
                  setFeedback(null);
                  setCustomerReference(event.target.value);
                }}
                style={FIELD_STYLE}
              />
            </label>
            <label className="field-stack terms-wide">
              Notes about this extension
              <textarea
                rows={2}
                value={notes}
                onChange={(event) => {
                  setFeedback(null);
                  setNotes(event.target.value);
                }}
                style={FIELD_STYLE}
              />
            </label>
          </div>
          <div>
            <button
              type="button"
              disabled={saving || removing || !newEndDate || !receivedDate}
              onClick={() => void record()}
              style={SAVE_BUTTON_STYLE}
            >
              {saving ? "Recording..." : "Record extension"}
            </button>
            <FeedbackLine feedback={feedback} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
