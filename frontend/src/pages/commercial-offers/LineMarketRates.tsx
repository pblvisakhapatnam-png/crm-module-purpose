// One offer line's market rates (Slice 4G): its rates and their quote copies, the form to add a rate, Select as basis
// with a reason, and the line's basis history. Messages appear beside the button that made them.

import type { FormEvent } from "react";
import { useState } from "react";
import CurrencySelect from "../../components/CurrencySelect";
import DateInput from "../../components/DateInput";
import DocumentsPanel, { DocumentFileAction, VENDOR_QUOTE_DOCUMENT_TYPES } from "../../components/DocumentsPanel";
import { DEFAULT_CURRENCY } from "../../components/currency";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { enteredIndiaTimeToUtc } from "../../components/enteredDateTime";
import { readErrorDetail } from "../../components/errorDetail";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";
import {
  RATE_TYPE_LABELS,
  basisChoiceText,
  lineBasisHistory,
  nearestPanelIndex,
  quoteCopyChoices,
  quoteCopyPlace,
  rateSummary,
  type MarketRate,
} from "./lineMarketRatesState";

type Line = { public_id: string; line_number: number; line_status_code: string; scope_description: string };

type Props = {
  /** The page's Jump to target, given to the first line's panel. */
  anchorId?: string;
  offerPublicId: string;
  offerVersionNumber: number | null | undefined;
  line: Line;
  lineRates: MarketRate[];
  offerRates: MarketRate[];
  /** Whether this role may add rates and choose the basis: a usability aid; the server decides. */
  canWork: boolean;
  /** The offer is sent, revised or abandoned: its rates can no longer change. The lines card says so once, above. */
  locked: boolean;
  getToken: () => string | null;
  onChanged: () => Promise<void> | void;
  /** The server refused a change: the offer may have been sent or the line cancelled, so read it all again. */
  onRefused: () => Promise<void> | void;
};

type RateForm = {
  evidence_type: string;
  source_name: string;
  vendor_contact: string;
  equipment_service_description: string;
  rate_amount: string;
  currency_code: string;
  rate_basis: string;
  collected_by_name: string;
  collected_at: string;
  source_reference: string;
  quote_copy_rate_public_id: string;
  comparison_notes: string;
  is_selected_basis: boolean;
  selection_reason: string;
};

function emptyForm(line: Line): RateForm {
  return {
    evidence_type: "market_rate",
    source_name: "",
    vendor_contact: "",
    equipment_service_description: line.scope_description,
    rate_amount: "",
    currency_code: DEFAULT_CURRENCY,
    rate_basis: "",
    collected_by_name: "",
    collected_at: "",
    source_reference: "",
    quote_copy_rate_public_id: "",
    comparison_notes: "",
    is_selected_basis: false,
    selection_reason: "",
  };
}

function optional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

const BASE_PATH = "/api/commercial-offers";

/** The line's market-rate panel nearest what is on screen, unfolded, for the page's Jump to (owner's screen check). */
export function nearestLineMarketRatesPanel(): HTMLElement | null {
  const panels = Array.from(document.querySelectorAll<HTMLDetailsElement>("details[data-line-market-rates]"));
  const index = nearestPanelIndex(
    panels.map((panel) => panel.getBoundingClientRect()),
    window.innerHeight,
  );
  const panel = index >= 0 ? panels[index] : null;
  if (panel) panel.open = true;
  return panel;
}

export default function LineMarketRates({
  anchorId,
  offerPublicId,
  offerVersionNumber,
  line,
  lineRates,
  offerRates,
  canWork,
  locked,
  getToken,
  onChanged,
  onRefused,
}: Props) {
  const cancelled = line.line_status_code !== "ACTIVE";
  const canChange = canWork && !locked && !cancelled;
  const [form, setForm] = useState<RateForm>(() => emptyForm(line));
  const [saving, setSaving] = useState(false);
  const [addMessage, setAddMessage] = useState("");
  const [addError, setAddError] = useState("");
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [choosing, setChoosing] = useState("");
  const [choiceMessages, setChoiceMessages] = useState<Record<string, { ok: boolean; text: string }>>({});
  const [attachingTo, setAttachingTo] = useState("");
  const basis = lineRates.find((rate) => rate.is_selected_basis);
  const history = lineBasisHistory(lineRates);

  function edit(patch: Partial<RateForm>) {
    setForm((current) => ({ ...current, ...patch }));
    setAddMessage("");
    setAddError("");
  }

  // `answered`: the server replied, so what is on screen may be out of date and is reloaded (review 4G-R1-005).
  async function post(
    path: string,
    body: unknown,
  ): Promise<{ ok: true } | { ok: false; message: string; answered: boolean }> {
    const token = getToken();
    if (!token) return { ok: false, message: SIGN_IN_FIRST, answered: false };
    let response: Response;
    try {
      response = await fetch(`${BASE_PATH}/${encodeURIComponent(offerPublicId)}${path}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch {
      return { ok: false, message: "Could not reach the server. Nothing was saved. Please try again.", answered: false };
    }
    if (response.ok) return { ok: true };
    if (response.status === 401) return { ok: false, message: SIGN_IN_AGAIN, answered: false };
    if (response.status === 403) {
      return { ok: false, message: "Your role can view market rates but cannot add or choose them.", answered: false };
    }
    return {
      ok: false,
      message: await readErrorDetail(response, `Not saved (error ${response.status}). Please try again.`),
      answered: true,
    };
  }

  async function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAddMessage("");
    setAddError("");
    if (!form.rate_amount.trim() || Number(form.rate_amount) < 0) return setAddError("Enter the rate amount; it cannot be negative.");
    if (!form.equipment_service_description.trim()) return setAddError("Equipment / service description is required.");
    if (!form.rate_basis.trim()) return setAddError("Rate basis is required, for example per day or per month.");
    if (form.is_selected_basis && !form.selection_reason.trim()) {
      return setAddError("Give the reason for choosing this rate as the line's basis.");
    }
    setSaving(true);
    const result = await post("/pricing-evidence", {
      line_public_id: line.public_id,
      evidence_type: form.evidence_type,
      source_name: optional(form.source_name),
      vendor_contact: optional(form.vendor_contact),
      equipment_service_description: form.equipment_service_description.trim(),
      rate_amount: form.rate_amount.trim(),
      currency_code: form.currency_code,
      rate_basis: form.rate_basis.trim(),
      collected_by_name: optional(form.collected_by_name),
      collected_at: enteredIndiaTimeToUtc(form.collected_at),
      source_reference: optional(form.source_reference),
      quote_copy_rate_public_id: optional(form.quote_copy_rate_public_id),
      comparison_notes: optional(form.comparison_notes),
      is_selected_basis: form.is_selected_basis,
      selection_reason: form.is_selected_basis ? form.selection_reason.trim() : null,
    });
    setSaving(false);
    if (!result.ok) {
      setAddError(result.message);
      // Refused by the server - the line was cancelled or the offer sent, say: show what holds now (review 4G-R2-002).
      if (result.answered) await onRefused();
      return;
    }
    setForm(emptyForm(line));
    setChoiceMessages({});
    setAddMessage(`Rate saved on line ${line.line_number}.`);
    await onChanged();
  }

  async function handleChoose(rate: MarketRate) {
    const reason = (reasons[rate.public_id] ?? "").trim();
    if (!reason) {
      setChoiceMessages((current) => ({ ...current, [rate.public_id]: { ok: false, text: "Give the reason for choosing this rate." } }));
      return;
    }
    setChoosing(rate.public_id);
    const result = await post(`/pricing-evidence/${encodeURIComponent(rate.public_id)}/select-basis`, { selection_reason: reason });
    setChoosing("");
    if (result.ok) {
      // Only this rate's message stays: an earlier "Now the basis rate" beside another rate would no longer be true.
      setChoiceMessages({ [rate.public_id]: { ok: true, text: `Now the basis rate for line ${line.line_number}.` } });
      setAddMessage("");
      setAddError("");
      setReasons((current) => ({ ...current, [rate.public_id]: "" }));
      await onChanged();
      return;
    }
    setChoiceMessages({ [rate.public_id]: { ok: false, text: result.message } });
    // Refused by the server - someone chose at the same time, say: show what holds now, keeping the message.
    if (result.answered) await onRefused();
  }

  return (
    <details id={anchorId} data-line-market-rates className="secondary-disclosure line-market-rates" open={lineRates.length > 0 || undefined}>
      <summary>
        Market rates for line {line.line_number}: {lineRates.length} rate(s);{" "}
        {basis ? `basis ${rateSummary(basis)}` : "no basis rate chosen"}
      </summary>
      {cancelled ? <p className="helper-text">This line is cancelled; its rates are kept as history.</p> : null}
      {lineRates.length === 0 ? <p className="helper-text">No market rate is recorded for this line yet.</p> : null}

      {lineRates.length > 0 ? (
        <ul className="compact-list">
          {lineRates.map((rate) => {
            const current = rate.basis_history.find((choice) => choice.is_current);
            const choiceMessage = choiceMessages[rate.public_id];
            return (
              <li key={rate.public_id} className="divided-item">
                <strong>{rateSummary(rate)}</strong>{" "}
                {rate.is_selected_basis ? <span className="status-badge status-badge--success">Basis rate</span> : null}
                <div className="helper-text">
                  {RATE_TYPE_LABELS[rate.evidence_type] ?? rate.evidence_type} - {rate.equipment_service_description}
                  {rate.vendor_contact ? ` - Contact: ${rate.vendor_contact}` : ""}
                  {rate.collected_by_name || rate.collected_at
                    ? ` - Collected by ${rate.collected_by_name || "-"} on ${formatDateTime(rate.collected_at)}`
                    : ""}
                  {rate.source_reference ? ` - Reference: ${rate.source_reference}` : ""}
                </div>
                {rate.comparison_notes ? <div className="helper-text text-pre-wrap">Notes: {rate.comparison_notes}</div> : null}
                {current ? <p className="text-success">{basisChoiceText(current)}</p> : null}

                {rate.quote_copies.length > 0 ? (
                  <ul className="compact-list">
                    {rate.quote_copies.map((copy) => (
                      <li key={`${copy.attached_to_rate_public_id}-${copy.document_public_id}`}>
                        Quote copy: {copy.file_name}
                        {copy.attached_here ? "" : ` (${quoteCopyPlace(copy, offerVersionNumber)})`}{" "}
                        <DocumentFileAction
                          row={{
                            public_id: copy.document_public_id,
                            document_type: "VENDOR_QUOTE",
                            linked_record_type: "commercial_offer_market_rate",
                            linked_record_public_id: copy.attached_to_rate_public_id,
                            file_name: copy.file_name,
                            storage_mode: "local_upload",
                            uploaded_at: copy.uploaded_at,
                          }}
                        />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="helper-text">No quote copy attached.</div>
                )}

                {canChange && !rate.is_selected_basis ? (
                  <div className="section-form">
                    <label className="field-stack">
                      Reason for choosing this rate as the basis
                      <textarea
                        value={reasons[rate.public_id] ?? ""}
                        onChange={(event) => {
                          setReasons((current) => ({ ...current, [rate.public_id]: event.target.value }));
                          setChoiceMessages((current) => ({ ...current, [rate.public_id]: { ok: true, text: "" } }));
                        }}
                        rows={2}
                        maxLength={1000}
                      />
                    </label>
                    <div className="form-actions action-feedback">
                      <button type="button" onClick={() => void handleChoose(rate)} disabled={choosing === rate.public_id}>
                        {choosing === rate.public_id ? "Saving..." : "Select as basis"}
                      </button>
                    </div>
                  </div>
                ) : null}
                {choiceMessage?.text ? (
                  <p className={`action-feedback ${choiceMessage.ok ? "text-success" : "text-danger"}`}>{choiceMessage.text}</p>
                ) : null}

                {canChange ? (
                  <div className="form-actions action-feedback">
                    <button type="button" onClick={() => setAttachingTo(attachingTo === rate.public_id ? "" : rate.public_id)}>
                      {attachingTo === rate.public_id ? "Close" : "Attach the quote"}
                    </button>
                  </div>
                ) : null}
                {canChange && attachingTo === rate.public_id ? (
                  <DocumentsPanel
                    linkedRecordType="commercial_offer_market_rate"
                    linkedRecordPublicId={rate.public_id}
                    canUpload
                    documentTypes={VENDOR_QUOTE_DOCUMENT_TYPES}
                    onUploaded={() => void onChanged()}
                    onUploadRefused={(message) => {
                      // Kept beside the rate: the reload below may close the upload panel (review 4G-R4-004).
                      setChoiceMessages({ [rate.public_id]: { ok: false, text: message } });
                      void onRefused();
                    }}
                  />
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}

      {history.length > 0 ? (
        <>
          <h4>Basis history for line {line.line_number}</h4>
          <ul className="compact-list">
            {history.map(({ rate, choice }) => (
              <li key={choice.public_id}>
                {rateSummary(rate)}. {basisChoiceText(choice)}
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {canChange ? (
        <form onSubmit={handleAdd} className="section-form">
          <h4>Add a rate for line {line.line_number}</h4>
          <div className="form-grid">
            <label className="field-stack">
              Rate type
              <select value={form.evidence_type} onChange={(event) => edit({ evidence_type: event.target.value })}>
                <option value="market_rate">Market rate</option>
                <option value="historical_plum_rate">Historical Plum rate</option>
              </select>
            </label>
            <label className="field-stack">
              Source / vendor
              <input value={form.source_name} onChange={(event) => edit({ source_name: event.target.value })} maxLength={255} />
            </label>
            <label className="field-stack">
              Vendor contact
              <input value={form.vendor_contact} onChange={(event) => edit({ vendor_contact: event.target.value })} maxLength={255} />
            </label>
            <label className="field-stack">
              Rate amount
              <input
                value={form.rate_amount}
                onChange={(event) => edit({ rate_amount: event.target.value })}
                type="number"
                min="0"
                step="0.01"
              />
            </label>
            <label className="field-stack">
              Currency
              <CurrencySelect value={form.currency_code} onChange={(currencyCode) => edit({ currency_code: currencyCode })} />
            </label>
            <label className="field-stack">
              Rate basis
              <input
                value={form.rate_basis}
                onChange={(event) => edit({ rate_basis: event.target.value })}
                maxLength={100}
                placeholder="per day, per month"
              />
            </label>
            <label className="field-stack">
              Collected by
              <input value={form.collected_by_name} onChange={(event) => edit({ collected_by_name: event.target.value })} maxLength={255} />
            </label>
            <label className="field-stack">
              Collected at
              <DateInput withTime value={form.collected_at} onChange={(event) => edit({ collected_at: event.target.value })} />
            </label>
            <label className="field-stack">
              Source reference
              <input value={form.source_reference} onChange={(event) => edit({ source_reference: event.target.value })} maxLength={255} />
            </label>
            <label className="field-stack">
              Quote copy attached to another rate
              <select value={form.quote_copy_rate_public_id} onChange={(event) => edit({ quote_copy_rate_public_id: event.target.value })}>
                <option value="">None - attach this rate's own quote after saving</option>
                {quoteCopyChoices(offerRates).map((choice) => (
                  <option key={choice.value} value={choice.value}>
                    {choice.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="field-stack">
            Equipment / service description
            <textarea
              value={form.equipment_service_description}
              onChange={(event) => edit({ equipment_service_description: event.target.value })}
              rows={2}
              maxLength={1000}
            />
          </label>
          <label className="field-stack">
            Comparison notes
            <textarea value={form.comparison_notes} onChange={(event) => edit({ comparison_notes: event.target.value })} rows={2} maxLength={2000} />
          </label>
          <label className="tick-row">
            <input
              type="checkbox"
              checked={form.is_selected_basis}
              onChange={(event) => edit({ is_selected_basis: event.target.checked })}
            />
            Choose this rate as the line's basis now
          </label>
          {form.is_selected_basis ? (
            <label className="field-stack">
              Reason for choosing it
              <textarea value={form.selection_reason} onChange={(event) => edit({ selection_reason: event.target.value })} rows={2} maxLength={1000} />
            </label>
          ) : null}
          <div className="form-actions action-feedback">
            <button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save rate"}
            </button>
          </div>
          {addMessage ? <p className="action-feedback text-success">{addMessage}</p> : null}
          {addError ? <p className="action-feedback text-danger">{addError}</p> : null}
        </form>
      ) : null}
    </details>
  );
}
