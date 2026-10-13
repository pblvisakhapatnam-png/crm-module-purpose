import { Fragment, type ReactNode, useEffect, useId, useMemo, useRef, useState } from "react";

import { SectionCard } from "../../components/PageLayout";
import { isUserToggle, lineCardOpen } from "./workOrderLineDetailState";
import {
  BILLING_BASIS_OPTIONS,
  type BillingTermPeriod,
  type LineBillingTerms,
  type RateForm,
  type TermChapter,
  type TermGroupKey,
  type TermsForm,
  ADD_PERIOD_WRITER,
  CREW_COUNT_MAX,
  CREW_STATED,
  DEMOBILISATION_CHARGED_CODES,
  EXTRA_CREW_RATE_PER_PERSON,
  EXTRA_KM_INCLUDED_CODES,
  FUEL_AGREED_RATE_PER_LITRE,
  FUEL_CUSTOMER_SUPPLIED,
  FUEL_PBL_CHARGED,
  FUEL_TRAVEL_LITRES_PER_HOUR,
  MOBILISATION_CHARGED_CODES,
  SHIFT_PATTERNS_SEVERAL,
  SHIFT_RATE_METHOD_PER_SHIFT,
  SHIFT_RATE_PER_SHIFT,
  UPKEEP_AT_COST,
  UPKEEP_CELLS,
  UPKEEP_CHOICES,
  UPKEEP_ITEMS,
  UPKEEP_RECOVERIES,
  UPKEEP_ROLES,
  type UpkeepCellForm,
  WEEKDAYS,
  asksOvertimeCountedPer,
  billingBasisLabel,
  crewOfPeriod,
  createLineWriteGuard,
  feedbackIsStale,
  formAfterBasisChange,
  formForNewPeriod,
  formFromPeriod,
  legacyNightShiftNote,
  missingTermsText,
  periodLabel,
  periodOpen,
  periodSummary,
  showsLineOnceTerms,
  shiftsPerDay,
  showsMonthOvertimeRows,
  termGroupStatus,
  termsFormProblem,
  termsPayloadFromForm,
  upkeepAnswerText,
  upkeepRoleApplies,
  upkeepWithHelpersAsOperators,
  visibleTermChapters,
  visibleTermGroups,
} from "./workOrderBillingTermsState";
import {
  type ContractPeriod,
  type CopyResult,
  confirmationText,
  copyButtonLabel,
  copyHadFailures,
  copyResultText,
  copyTargetRows,
  initialCopySelection,
  rowsNeedingConfirmation,
  toggleCopySelection,
} from "./workOrderContractPeriodState";
import DateInput from "../../components/DateInput";

// Slice 7D Part 1: the billing terms the customer's Work Order sets for each line, in periods. The
// first period starts with the contract; a later period starts on its own date. "Not in the Work
// Order" is a recorded answer; a term left unchosen shows as missing. The backend re-checks every
// rule; hiding the form from read-only roles is a convenience, not the control.

type LineSummary = { public_id: string; line_number: number; scope_description: string; uom: string };
type Feedback = { kind: "success" | "error"; text: string } | null;
type ExpandRequest = { open: boolean; seq: number };
type Option = { code: string; label: string };

const NOT_IN_WORK_ORDER = { code: "NONE", label: "Not in the Work Order" };
const RATE_METHODS: Option[] = [
  { code: "RATE_PER_HOUR", label: "Rate per hour" },
  { code: "PERCENT_OF_NORMAL", label: "% of the normal rate" },
];
const OFF_DAY_WORK: Option[] = [
  NOT_IN_WORK_ORDER,
  { code: "OVERTIME_RATE", label: "Overtime rate" },
  { code: "HOLIDAY_RATE", label: "A holiday rate" },
  { code: "NORMAL_RATE", label: "Normal rate" },
];
const MONTH_OT_HOURS: Option[] = [
  { code: "AVAILABLE_HOURS", label: "Hours the machine was available" },
  { code: "ENGINE_HOURS", label: "Hours it actually worked (hour meter)" },
];
const MONTH_OT_COUNTING: Option[] = [
  { code: "WHOLE_MONTH", label: "Over the whole month, after contracted hours" },
  { code: "DAY_BY_DAY", label: "Day by day" },
];
const BREAKDOWN: Option[] = [
  NOT_IN_WORK_ORDER,
  { code: "REDUCE_BILLED_HOURS", label: "Reduce the billed hours pro rata" },
  { code: "DEDUCT_AT_BREAKDOWN_RATE", label: "A separate deduction at a breakdown rate" },
];
const IDLE: Option[] = [
  { code: "NONE", label: "Not in the Work Order (not paid)" },
  { code: "AS_WORKING_HOURS", label: "Paid as working hours" },
  { code: "STANDBY_RATE", label: "Paid at a standby rate" },
];
const MINIMUM: Option[] = [NOT_IN_WORK_ORDER, { code: "UNITS_PER_MONTH", label: "At least a number of units a month" }];
// Part 5 choices (owner's answers of 9 October 2026). "Not in the Work Order" states no shifts (review round 2).
const SHIFT_PATTERNS: Option[] = [
  NOT_IN_WORK_ORDER,
  { code: "ONE_SHIFT", label: "One shift" },
  { code: "TWO_SHIFTS", label: "Two shifts" },
  { code: "THREE_SHIFTS", label: "Three shifts" },
];
const SHIFT_RATES: Option[] = [
  // The owner's words (answer 4). How billing counts each is assumption A9, for the owner to confirm (review round 5).
  { code: "SAME_FOR_ALL_SHIFTS", label: "The same rate for every shift" },
  { code: SHIFT_RATE_PER_SHIFT, label: "A rate set for each later shift (shift 1 at the Work Order rate)" },
];
const SHIFT_RATE_METHODS: Option[] = [
  { code: SHIFT_RATE_METHOD_PER_SHIFT, label: "Rate per shift" },
  { code: "RATE_PER_HOUR", label: "Rate per hour" },
  // Part 2's "% of the normal rate", unchanged: the Work Order rate, which the first (day) shift is charged at -
  // what the owner called "the day rate" (review round 1, 7D5-R1-002; assumption A15).
  { code: "PERCENT_OF_NORMAL", label: "% of the first shift's rate (the Work Order rate)" },
];
const OVERTIME_COUNTED_PER: Option[] = [
  { code: "PER_SHIFT", label: "Per shift, beyond each shift's hours" },
  { code: "PER_DAY", label: "For the whole day, beyond the day's hours" },
];
// Part 2 choices. "Not in the Work Order" is a recorded answer throughout (owner decision 4).
const MOBILISATION: Option[] = [
  NOT_IN_WORK_ORDER,
  { code: "CHARGED", label: "Charged" },
  { code: "CHARGED_CREDITED_AFTER_MONTHS", label: "Charged, credited back if the machine stays beyond a number of months" },
];
const DEMOBILISATION: Option[] = [
  NOT_IN_WORK_ORDER,
  { code: "CHARGED", label: "Charged" },
  { code: "CHARGED_WAIVED_AFTER_MONTHS", label: "Not charged if the machine stays beyond a number of months" },
];
const FUEL: Option[] = [
  NOT_IN_WORK_ORDER,
  { code: "PBL_SUPPLIED_INCLUDED", label: "Supplied by PBL, included in the rate" },
  { code: FUEL_PBL_CHARGED, label: "Supplied by PBL and charged" },
  { code: FUEL_CUSTOMER_SUPPLIED, label: "Supplied by the customer" },
];
const FUEL_CHARGE_METHODS: Option[] = [
  { code: FUEL_AGREED_RATE_PER_LITRE, label: "At an agreed rate per litre" },
  { code: "ACTUAL_COST", label: "At actual cost" },
];
const FUEL_TRAVEL: Option[] = [
  NOT_IN_WORK_ORDER,
  { code: FUEL_TRAVEL_LITRES_PER_HOUR, label: "A number of litres per travel hour" },
];
// Part 4 choices (owner answers 22 and 23, decision 28).
const EXTRA_KM: Option[] = [
  NOT_IN_WORK_ORDER,
  { code: "KM_PER_DAY", label: "A number of kilometres included per day" },
  { code: "KM_PER_MONTH", label: "A number of kilometres included per month" },
];
const CREW: Option[] = [
  { code: "NONE", label: "Not part of the Work Order (equipment only)" },
  { code: CREW_STATED, label: "The Work Order states the operators and helpers" },
];
const EXTRA_CREW: Option[] = [
  NOT_IN_WORK_ORDER,
  { code: EXTRA_CREW_RATE_PER_PERSON, label: "A rate for each extra operator and each extra helper" },
];
const PART_MONTH: Option[] = [
  { code: "CALENDAR_DAYS", label: "Calendar days in that month" },
  { code: "CONTRACTED_WORKING_DAYS", label: "Contracted working days" },
  { code: "THIRTY_DAYS", label: "30 days" },
];
const HOURS_LABELS: Record<string, string> = {
  SHIFT: "Contracted hours per shift",
  DAY: "Contracted hours per day",
  MONTH: "Contracted hours per month",
};
// A field fills its column; the card's grid decides the width (Slice 7D.1).
// The writer key the copy panel uses, so its message is cleared when another action on the line
// starts, exactly as every other control on the card does.
const COPY_WRITER = "copy-to-lines";

const FIELD_STYLE = { width: "100%" } as const;

const GROUP_TITLES: Record<TermGroupKey, string> = {
  basis: "Basis and rate",
  offDays: "Working days and off days",
  overtime: "Overtime",
  breakdown: "Breakdown",
  idle: "Idle time and minimums",
  shifts: "Shifts",
  fuel: "Fuel",
  extraKm: "Extra kilometres",
  crew: "Crew",
  upkeep: "Crew food, accommodation and travel",
  lineOnce: "Mobilisation and demobilisation (for the whole line)",
};

/** One line under a card's title saying what the group covers. */
function groupDescription(group: TermGroupKey, basis: string): string {
  switch (group) {
    case "basis":
      return "How the Work Order charges this line";
    case "offDays":
      return "The working week, and how work on an off day or holiday is charged";
    case "overtime":
      return "Hours worked beyond the contracted hours";
    case "breakdown":
      return "Hours lost when the machine cannot work";
    case "idle":
      return basis === "MONTH" ? "Idle time caused by the customer, and part months" : "Idle time caused by the customer, and any minimum guarantee";
    case "shifts":
      return "How many shifts a day, their hours, and how they are charged. Overtime, breakdown, idle time and off days follow the terms here for every shift";
    case "fuel":
      return "Who supplies the fuel, and how it is charged";
    case "extraKm":
      return "Kilometres included in the rate, and the charge for each kilometre beyond them";
    case "crew": {
      const unit = billingBasisLabel(basis)?.toLowerCase() ?? "billing unit";
      return `Operators and helpers per ${unit}, as the customer is charged for them, and any extra crew`;
    }
    case "upkeep":
      return "What the customer provides, or provides at a cost it recovers from PBL. Nothing is paid to the crew";
    case "lineOnce":
      return "The machine arrives once and leaves once, so these are recorded here and a later period does not change them";
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return "Check the values entered: one of them is not accepted.";
  } catch {
    // fall through
  }
  return `The billing terms could not be saved. HTTP ${response.status}.`;
}

type Props = {
  workOrderPublicId: string;
  lines: LineSummary[];
  terms: LineBillingTerms[];
  termsLoaded: boolean;
  termsError: string;
  canEdit: boolean;
  isClosed: boolean;
  token: string | null;
  // The page-load generation this section was rendered for. Every write hands it back, so a save that
  // finishes after a newer page load has started is discarded instead of applied over it.
  loadGeneration: number;
  // Receives the line's terms from each write response, so the page applies them at once.
  onApplied: (entry: LineBillingTerms, loadGeneration: number) => void;
  // Slice 7D Part 3. The contract period, so period 1 can show the contract's own start date instead
  // of "From contract start"; and every line's terms at once, because copying terms between lines
  // changes more than one line's terms in a single write.
  contractPeriod: ContractPeriod | null;
  onAllApplied: (entries: LineBillingTerms[], loadGeneration: number) => void;
};

export default function WorkOrderBillingTermsSection(props: Props) {
  const [expandRequest, setExpandRequest] = useState<ExpandRequest>({ open: false, seq: 0 });
  return (
    <SectionCard title="Billing terms">
      <p style={{ marginTop: 0 }}>
        For each line, the terms the customer's Work Order sets: the billing basis, the rate, working days, shifts,
        overtime, breakdown, idle time, minimum guarantee, fuel, extra kilometres, crew and their food, accommodation
        and travel, and mobilisation and demobilisation for the whole line. If a term is not in the Work Order, choose "Not in the Work Order" -
        nothing that is not written there is ever charged. If the terms change on a date, add a later period. Missing terms
        do not block anything yet; they will block releasing the Work Order to Ops.
      </p>
      {props.isClosed ? <p style={{ color: "#6b7280" }}>This Work Order is closed, so its billing terms can no longer be changed.</p> : null}
      {props.termsError ? <p style={{ color: "crimson" }}>{props.termsError}</p> : null}
      {props.canEdit && !props.termsLoaded && !props.termsError ? <p className="helper-text">Loading the billing terms...</p> : null}
      {props.lines.length > 1 ? (
        <p style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button type="button" onClick={() => setExpandRequest((current) => ({ open: true, seq: current.seq + 1 }))}>
            Show terms for all lines
          </button>
          <button type="button" onClick={() => setExpandRequest((current) => ({ open: false, seq: current.seq + 1 }))}>
            Hide terms for all lines
          </button>
        </p>
      ) : null}
      <div style={{ display: "grid", gap: "12px" }}>
        {props.lines.map((line) => (
          <LineTermsCard
            key={line.public_id}
            workOrderPublicId={props.workOrderPublicId}
            line={line}
            entry={props.terms.find((item) => item.work_order_line_public_id === line.public_id)}
            editable={props.canEdit && !props.isClosed && props.termsLoaded}
            token={props.token}
            loadGeneration={props.loadGeneration}
            onApplied={props.onApplied}
            expandRequest={expandRequest}
            allLines={props.lines}
            allTerms={props.terms}
            contractStartDate={props.contractPeriod?.contract_start_date ?? null}
            onAllApplied={props.onAllApplied}
          />
        ))}
      </div>
    </SectionCard>
  );
}

type CardProps = {
  workOrderPublicId: string;
  line: LineSummary;
  entry: LineBillingTerms | undefined;
  editable: boolean;
  token: string | null;
  loadGeneration: number;
  onApplied: (entry: LineBillingTerms, loadGeneration: number) => void;
  expandRequest: ExpandRequest;
  // Slice 7D Part 3.
  allLines: LineSummary[];
  allTerms: LineBillingTerms[];
  contractStartDate: string | null;
  onAllApplied: (entries: LineBillingTerms[], loadGeneration: number) => void;
};

function LineTermsCard({ workOrderPublicId, line, entry, editable, token, loadGeneration, onApplied, expandRequest, allLines, allTerms, contractStartDate, onAllApplied }: CardProps) {
  const [userOpen, setUserOpen] = useState<boolean | null>(null);
  const [newPeriodDate, setNewPeriodDate] = useState("");
  const [adding, setAdding] = useState(false);
  const [addFeedback, setAddFeedback] = useState<Feedback>(null);
  // Every write for this line - start, add, save, remove - goes through one guard, so only one is in
  // flight and responses cannot arrive out of order (review round 2). While one runs, every action on
  // the line is disabled.
  const writeGuard = useRef(createLineWriteGuard());
  const [lineBusy, setLineBusy] = useState(false);
  // The control that started the latest write on this line. Starting a write clears every other
  // control's message on the line, so no message outlives a later action (owner screen check).
  const [lastWriter, setLastWriter] = useState<string | null>(null);

  async function runLineWrite(writer: string, write: () => Promise<void>) {
    if (!writeGuard.current.tryBegin()) return;
    setLastWriter(writer);
    setAddFeedback(null);
    setListFeedback(null);
    setLineBusy(true);
    try {
      await write();
    } finally {
      writeGuard.current.end();
      setLineBusy(false);
    }
  }
  // Start and Remove change the list itself - the Start button disappears, a removed period's form
  // unmounts - so their result is shown in this slot, below the periods, where those buttons were.
  const [listFeedback, setListFeedback] = useState<Feedback>(null);

  useEffect(() => {
    if (expandRequest.seq > 0) setUserOpen(expandRequest.open);
  }, [expandRequest.seq, expandRequest.open]);

  const periods = entry?.periods ?? [];
  const latest = periods[periods.length - 1];
  const current = periods.find((period) => period.period_number === entry?.current_period_number);
  const isOpen = lineCardOpen(userOpen, entry?.terms_complete);
  const baseUrl = `/api/work-orders/${encodeURIComponent(workOrderPublicId)}/lines/${encodeURIComponent(line.public_id)}/billing-terms`;
  const summary = periodSummary(current);

  async function addPeriod(form: TermsForm, isFirst: boolean) {
    await runLineWrite(ADD_PERIOD_WRITER, () => sendAddPeriod(form, isFirst));
  }

  async function sendAddPeriod(form: TermsForm, isFirst: boolean) {
    const setFeedback = isFirst ? setListFeedback : setAddFeedback;
    const problem = termsFormProblem(form);
    if (problem) {
      setFeedback({ kind: "error", text: problem });
      return;
    }
    if (!token) {
      setFeedback({ kind: "error", text: "Your session has ended. Sign in again, then add the period." });
      return;
    }
    setAdding(true);
    setAddFeedback(null);
    setListFeedback(null);
    try {
      const response = await fetch(baseUrl, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          // The period this request will create: the first one, or the one after those on screen.
          ...termsPayloadFromForm(form, isFirst ? 1 : periods.length + 1),
          effective_from: isFirst ? null : form.effective_from || null,
          expected_period_count: periods.length,
          expected_latest_term_revision: latest?.term_revision ?? null,
        }),
      });
      if (response.status === 409) {
        setFeedback({ kind: "error", text: "These terms have changed since the page loaded. Reload to see the latest version." });
        return;
      }
      if (!response.ok) {
        setFeedback({ kind: "error", text: await readErrorDetail(response) });
        return;
      }
      const body = (await response.json()) as { line_billing_terms: LineBillingTerms };
      onApplied(body.line_billing_terms, loadGeneration);
      setNewPeriodDate("");
      setFeedback({ kind: "success", text: isFirst ? "Billing terms started for this line." : "Later period added." });
    } catch {
      setFeedback({ kind: "error", text: "Network error while adding the period. Try again." });
    } finally {
      setAdding(false);
    }
  }

  return (
    <details
      open={isOpen}
      onToggle={(event) => {
        const nowOpen = (event.currentTarget as HTMLDetailsElement).open;
        if (isUserToggle(nowOpen, isOpen)) setUserOpen(nowOpen);
      }}
      style={{ padding: "12px", border: "1px solid #ddd", background: "#fff" }}
    >
      <summary style={{ cursor: "pointer", listStylePosition: "outside" }}>
        <span style={{ display: "inline-flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap", width: "calc(100% - 24px)" }}>
          <span>
            <strong>
              Line {line.line_number} - {line.scope_description}
            </strong>
            {summary ? <span style={{ color: "#6b7280" }}> ({summary})</span> : null}
          </span>
          <span className="status-badge">{missingTermsText(entry)}</span>
        </span>
      </summary>
      <p style={{ margin: "8px 0", color: "#6b7280" }}>
        Quoted on the offer: {entry?.quoted_rate_amount ? `INR ${entry.quoted_rate_amount}` : "no rate"} per {line.uom}
      </p>

      {periods.map((period) => (
        <PeriodForm
          key={period.term_public_id}
          period={period}
          isLatest={period === latest}
          isCurrent={periods.length > 1 && period === current}
          canRemove={periods.length > 1 && period === latest}
          baseUrl={baseUrl}
          editable={editable}
          token={token}
          quotedRate={entry?.quoted_rate_amount ?? null}
          contractStartDate={contractStartDate}
          lineBusy={lineBusy}
          lastWriter={lastWriter}
          runLineWrite={runLineWrite}
          loadGeneration={loadGeneration}
          onApplied={onApplied}
          onRemoved={(text) => {
            setAddFeedback(null);
            setListFeedback({ kind: "success", text });
          }}
        />
      ))}

      {!entry ? (
        <p style={{ color: "#6b7280" }}>The billing terms for this line have not loaded.</p>
      ) : periods.length === 0 ? (
        editable ? (
          <div>
            <p style={{ margin: "8px 0" }}>No billing terms have been recorded for this line yet.</p>
            <button type="button" disabled={lineBusy} onClick={() => void addPeriod(formForNewPeriod(undefined), true)} style={{ padding: "8px 12px", fontWeight: 700 }}>
              {adding ? "Starting..." : "Start billing terms"}
            </button>
          </div>
        ) : (
          <p style={{ color: "#6b7280" }}>No billing terms have been recorded for this line yet.</p>
        )
      ) : null}
      {listFeedback ? (
        <p style={{ color: listFeedback.kind === "success" ? "#065f46" : "crimson", margin: "6px 0 0 0" }}>{listFeedback.text}</p>
      ) : null}

      {periods.length > 0 && editable && latest ? (
        <CopyTermsPanel
          baseUrl={baseUrl}
          sourceLine={line}
          sourcePeriods={periods}
          allLines={allLines}
          allTerms={allTerms}
          lineBusy={lineBusy}
          token={token}
          loadGeneration={loadGeneration}
          onAllApplied={onAllApplied}
          runLineWrite={runLineWrite}
          lastWriter={lastWriter}
        />
      ) : null}

      {periods.length > 0 && editable ? (
        <div className="terms-secondary-box">
          <label className="field-stack">
            A later period starts on
            <DateInput value={newPeriodDate} onChange={(event) => { setAddFeedback(null); setNewPeriodDate(event.target.value); }} style={FIELD_STYLE} />
          </label>
          <span className="helper-text">The new period starts with a copy of the latest period's terms.</span>
          <div>
            <button type="button" disabled={lineBusy} onClick={() => void addPeriod({ ...formForNewPeriod(latest), effective_from: newPeriodDate }, false)} style={{ padding: "8px 12px", fontWeight: 700 }}>
              {adding ? "Adding..." : "Add a later period"}
            </button>
            {addFeedback ? <p style={{ color: addFeedback.kind === "success" ? "#065f46" : "crimson", margin: "6px 0 0 0" }}>{addFeedback.text}</p> : null}
          </div>
        </div>
      ) : null}
    </details>
  );
}

// --- Slice 7D Part 3: "Apply these terms to other lines" (owner decision 20) ----------------------

type CopyPanelProps = {
  baseUrl: string;
  sourceLine: LineSummary;
  sourcePeriods: BillingTermPeriod[];
  allLines: LineSummary[];
  allTerms: LineBillingTerms[];
  lineBusy: boolean;
  token: string | null;
  loadGeneration: number;
  onAllApplied: (entries: LineBillingTerms[], loadGeneration: number) => void;
  runLineWrite: (writer: string, write: () => Promise<void>) => Promise<void>;
  lastWriter: string | null;
};

/**
 * Copies this line's saved terms onto other lines of the same Work Order. The source is the line the
 * user is standing on, so the list is of the lines being GIVEN the terms - the source is not in its
 * own list (owner decision 20).
 *
 * Ticking only chooses; nothing is written until the button is pressed, and the button says how many
 * lines it will change. Unticking a line simply leaves it alone and never removes its terms. Where a
 * ticked line already has terms, pressing the button asks first and names those lines - the only case
 * where something recorded is replaced (20b).
 */
function CopyTermsPanel({
  baseUrl,
  sourceLine,
  sourcePeriods,
  allLines,
  allTerms,
  lineBusy,
  token,
  loadGeneration,
  onAllApplied,
  runLineWrite,
  lastWriter,
}: CopyPanelProps) {
  const rows = useMemo(
    () => copyTargetRows(allLines, allTerms, sourceLine.public_id),
    [allLines, allTerms, sourceLine.public_id],
  );
  const [selected, setSelected] = useState<string[]>(() => initialCopySelection(rows));
  const [open, setOpen] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [copying, setCopying] = useState(false);

  // A newer set of lines - a page load, or a copy that has just landed - reconsiders which lines start
  // ticked, because which lines now have terms has changed.
  const rowsKey = rows.map((row) => `${row.public_id}:${row.hasTerms}`).join("|");
  useEffect(() => {
    setSelected(initialCopySelection(rows));
  }, [rowsKey]);

  useEffect(() => {
    if (feedbackIsStale(lastWriter, `${COPY_WRITER}:${sourceLine.public_id}`)) setFeedback(null);
  }, [lastWriter, sourceLine.public_id]);

  if (rows.length === 0) return null;

  const needConfirmation = rowsNeedingConfirmation(rows, selected);

  async function apply() {
    if (needConfirmation.length > 0 && !window.confirm(confirmationText(needConfirmation))) return;
    await runLineWrite(`${COPY_WRITER}:${sourceLine.public_id}`, send);
  }

  async function send() {
    if (!token) {
      setFeedback({ kind: "error", text: "Your session has ended. Sign in again, then apply the terms." });
      return;
    }
    setCopying(true);
    setFeedback(null);
    try {
      const response = await fetch(`${baseUrl}/apply-to-lines`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          // Each chosen line carries what this screen saw of it, and whether the user was asked
          // about replacing THIS line. A single request-wide flag could authorize replacing a line
          // the confirmation never named (independent review round 1, finding F-02).
          targets: selected.map((publicId) => {
            const entry = allTerms.find((item) => item.work_order_line_public_id === publicId);
            return {
              work_order_line_public_id: publicId,
              // Every period this screen saw of the line, not a count and the latest revision: those
              // two are unchanged by an edit to an earlier period, so a concurrent edit would be
              // deleted by the replacement (review round 2, finding F-07).
              observed_periods: (entry?.periods ?? []).map((period) => ({
                term_public_id: period.term_public_id,
                term_revision: period.term_revision,
              })),
              replace_confirmed: needConfirmation.some((row) => row.public_id === publicId),
            };
          }),
          // Every source period, so a change to an earlier one cannot pass unseen (finding F-01).
          source_periods: sourcePeriods.map((period) => ({
            term_public_id: period.term_public_id,
            term_revision: period.term_revision,
          })),
        }),
      });
      if (!response.ok) {
        // A 409 here names the line whose terms changed, which is the only way the user can tell
        // which of several chosen lines caused the refusal. Showing a generic sentence instead threw
        // that away and contradicted what this package promised (review round 2, finding F-08).
        // readErrorDetail already falls back to a safe generic message when there is no detail.
        setFeedback({ kind: "error", text: await readErrorDetail(response) });
        return;
      }
      const body = (await response.json()) as { results: CopyResult[]; billing_terms: LineBillingTerms[] };
      onAllApplied(body.billing_terms, loadGeneration);
      setFeedback({ kind: copyHadFailures(body.results) ? "error" : "success", text: copyResultText(body.results) });
    } catch {
      setFeedback({ kind: "error", text: "Network error while applying the terms. Try again." });
    } finally {
      setCopying(false);
    }
  }

  return (
    <div className="terms-secondary-box" style={{ maxWidth: "640px" }}>
      <button type="button" onClick={() => setOpen((current) => !current)} style={{ justifySelf: "start" }}>
        {open ? "Hide" : "Apply these terms to other lines"}
      </button>
      {open ? (
        <>
          <p className="helper-text" style={{ margin: 0 }}>
            Every period of line {sourceLine.line_number}'s terms is copied, mobilisation and demobilisation included.
            Each line you choose can still be edited afterwards. Lines with no terms yet are already ticked; a line you
            leave unticked is not touched, and keeps whatever terms it has.
          </p>
          <div style={{ display: "grid", gap: "6px" }}>
            {rows.map((row) => (
              <label key={row.public_id} style={{ display: "flex", gap: "8px", alignItems: "baseline" }}>
                <input
                  type="checkbox"
                  checked={selected.includes(row.public_id)}
                  onChange={() => {
                    setFeedback(null);
                    setSelected((current) => toggleCopySelection(current, row.public_id));
                  }}
                />
                <span>
                  <strong>
                    Line {row.line_number} - {row.scope_description}
                  </strong>
                  <span style={{ color: "#6b7280" }}> ({row.existingSummary})</span>
                </span>
              </label>
            ))}
          </div>
          {needConfirmation.length > 0 ? (
            <p style={{ margin: 0, color: "#92400e" }}>
              {confirmationText(needConfirmation)} You will be asked to confirm before anything is replaced.
            </p>
          ) : null}
          <div>
            <button
              type="button"
              disabled={lineBusy || copying || selected.length === 0}
              onClick={() => void apply()}
              style={{ padding: "8px 12px", fontWeight: 700 }}
            >
              {copying ? "Applying..." : copyButtonLabel(selected.length)}
            </button>
            {feedback ? (
              <p style={{ color: feedback.kind === "success" ? "#065f46" : "crimson", margin: "6px 0 0 0" }}>
                {feedback.text}
              </p>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  );
}


type PeriodProps = {
  period: BillingTermPeriod;
  isLatest: boolean;
  // The period in force today, marked only when the line has more than one.
  isCurrent: boolean;
  canRemove: boolean;
  baseUrl: string;
  editable: boolean;
  token: string | null;
  quotedRate: string | null;
  // Slice 7D Part 3: once the contract start is recorded, period 1 shows that date instead of
  // "From contract start".
  contractStartDate: string | null;
  // True while any write for this line is in flight; every action here is disabled meanwhile.
  lineBusy: boolean;
  lastWriter: string | null;
  runLineWrite: (writer: string, write: () => Promise<void>) => Promise<void>;
  loadGeneration: number;
  onApplied: (entry: LineBillingTerms, loadGeneration: number) => void;
  // A successful removal unmounts this form, so its confirmation is reported to the card.
  onRemoved: (text: string) => void;
};

function PeriodForm({ period, isLatest, isCurrent, canRemove, baseUrl, editable, token, quotedRate, contractStartDate, lineBusy, lastWriter, runLineWrite, loadGeneration, onApplied, onRemoved }: PeriodProps) {
  const [form, setForm] = useState<TermsForm>(() => formFromPeriod(period));
  // The write this form started, so only its own button changes its label.
  const [busy, setBusy] = useState<"PUT" | "DELETE" | null>(null);
  const [saveFeedback, setSaveFeedback] = useState<Feedback>(null);
  const [removeFeedback, setRemoveFeedback] = useState<Feedback>(null);
  // Slice 7D.1: each period opens and closes. Null until the user opens, closes or edits it.
  const [userOpen, setUserOpen] = useState<boolean | null>(null);
  const isOpen = periodOpen(userOpen, period, isLatest);

  // Reload the form whenever a newer revision arrives. Inputs are disabled while a write is in
  // flight, so this cannot overwrite anything typed during it.
  useEffect(() => {
    setForm(formFromPeriod(period));
  }, [period.term_public_id, period.term_revision]);

  // Another control on this line started a write, so this form's message no longer applies.
  useEffect(() => {
    if (feedbackIsStale(lastWriter, period.term_public_id)) {
      setSaveFeedback(null);
      setRemoveFeedback(null);
    }
  }, [lastWriter, period.term_public_id]);

  const groups = visibleTermGroups(form.billing_uom_code);
  const overtimeCharged = ["RATE_PER_HOUR", "PERCENT_OF_NORMAL"].includes(form.overtime_rate.method);
  const breakdownDeducts = ["REDUCE_BILLED_HOURS", "DEDUCT_AT_BREAKDOWN_RATE"].includes(form.breakdown_treatment_code);
  const shiftCount = groups.shifts ? shiftsPerDay(form.shift_pattern_code) : 0;
  const severalShifts = shiftCount >= 2;

  function update<K extends keyof TermsForm>(field: K, value: TermsForm[K]) {
    setUserOpen((current) => current ?? true);
    setSaveFeedback(null);
    setRemoveFeedback(null);
    setForm((currentForm) => ({ ...currentForm, [field]: value }));
  }

  async function write(method: "PUT" | "DELETE", setFeedback: (feedback: Feedback) => void, successText: string) {
    await runLineWrite(period.term_public_id, () => sendWrite(method, setFeedback, successText));
  }

  async function sendWrite(method: "PUT" | "DELETE", setFeedback: (feedback: Feedback) => void, successText: string) {
    const problem = method === "PUT" ? termsFormProblem(form) : null;
    if (problem) {
      setFeedback({ kind: "error", text: problem });
      return;
    }
    if (!token) {
      setFeedback({ kind: "error", text: "Your session has ended. Sign in again, then try again." });
      return;
    }
    setBusy(method);
    setFeedback(null);
    try {
      const url = `${baseUrl}/${encodeURIComponent(period.term_public_id)}`;
      const response =
        method === "PUT"
          ? await fetch(url, {
              method: "PUT",
              headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
              body: JSON.stringify({
                ...termsPayloadFromForm(form, period.period_number),
                effective_from: period.period_number === 1 ? null : form.effective_from || null,
                expected_term_revision: period.term_revision,
              }),
            })
          : await fetch(`${url}?expected_term_revision=${period.term_revision}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
      if (response.status === 409) {
        setFeedback({ kind: "error", text: "These terms have changed since the page loaded. Reload to see the latest version." });
        return;
      }
      if (!response.ok) {
        setFeedback({ kind: "error", text: await readErrorDetail(response) });
        return;
      }
      const body = (await response.json()) as { line_billing_terms: LineBillingTerms; event: unknown };
      if (method === "DELETE") {
        onRemoved(successText);
        onApplied(body.line_billing_terms, loadGeneration);
        return;
      }
      onApplied(body.line_billing_terms, loadGeneration);
      setFeedback({ kind: "success", text: body.event ? successText : "Nothing changed, so nothing was saved." });
    } catch {
      setFeedback({ kind: "error", text: "Network error. Try again." });
    } finally {
      setBusy(null);
    }
  }

  const summaryText = periodSummary(period);
  function disclosure(body: ReactNode) {
    return (
      <details
        className="terms-period"
        open={isOpen}
        onToggle={(event) => {
          const nowOpen = (event.currentTarget as HTMLDetailsElement).open;
          if (isUserToggle(nowOpen, isOpen)) setUserOpen(nowOpen);
        }}
      >
        <summary className="terms-period-band">
          <span className="terms-period-title">
            <span className="terms-period-chevron" aria-hidden="true">&#9654;</span>
            <span>{periodLabel(period, contractStartDate)}</span>
            {summaryText ? <span className="terms-period-meta">{summaryText}</span> : null}
            {isCurrent ? <span className="status-badge status-badge--info">In force now</span> : null}
          </span>
          <span className={`status-badge ${period.is_complete ? "status-badge--success" : "status-badge--warning"}`}>
            {period.is_complete ? "Complete" : `${period.missing_items.length} missing`}
          </span>
        </summary>
        <div className="terms-period-body">{body}</div>
      </details>
    );
  }

  if (!editable) {
    return disclosure(<ReadOnlyPeriod period={period} />);
  }

  const basis = form.billing_uom_code;
  const basisUnit = billingBasisLabel(basis)?.toLowerCase();
  // Each group's fields. Which groups show, and the chapter each sits in, is decided once by
  // visibleTermChapters, so a card appears exactly when its chapter lists it.
  const bodies: Record<TermGroupKey, ReactNode> = {
    basis: (
      <>
        <label className="field-stack">
          Billing basis
          <select
            value={basis}
            onChange={(event) => {
              const nextBasis = event.target.value;
              setUserOpen((current) => current ?? true);
              setSaveFeedback(null);
              setRemoveFeedback(null);
              setForm((currentForm) => formAfterBasisChange(currentForm, nextBasis, quotedRate));
            }}
            style={FIELD_STYLE}
          >
            <option value="">Not chosen</option>
            {BILLING_BASIS_OPTIONS.map((option) => (
              <option key={option.code} value={option.code}>{option.label}</option>
            ))}
          </select>
        </label>
        {groups.rate ? (
          <NumberField label={`Work Order rate per ${basisUnit} (INR)`} value={form.normal_rate_amount} onChange={(value) => update("normal_rate_amount", value)} />
        ) : null}
        {groups.rate && period.normal_rate_amount == null && form.normal_rate_amount !== "" && form.normal_rate_amount === quotedRate ? (
          <span className="helper-text terms-wide">
            Filled in from the quoted rate. Check it is the rate per {basisUnit} on the customer's Work Order, then save.
          </span>
        ) : null}
        {groups.contractedHours ? (
          <NumberField label={HOURS_LABELS[basis]} value={form.contracted_hours_per_billing_unit} onChange={(value) => update("contracted_hours_per_billing_unit", value)} />
        ) : null}
        {groups.workingDays ? (
          <NumberField label="Working days per month" value={form.contracted_working_days_per_month} onChange={(value) => update("contracted_working_days_per_month", value)} />
        ) : null}
        {groups.workingDays && period.derived_hours_per_working_day ? (
          <span className="helper-text terms-wide">That is {period.derived_hours_per_working_day} hours a working day, as last saved.</span>
        ) : null}
      </>
    ),
    offDays: (
      <>
        <label className="terms-wide" style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          <input type="checkbox" checked={form.off_days_recorded} onChange={(event) => update("off_days_recorded", event.target.checked)} />
          The Work Order states the weekly off days
        </label>
        {form.off_days_recorded ? (
          <div className="terms-wide">
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              {WEEKDAYS.map((day) => (
                <label key={day.code} style={{ display: "flex", gap: "4px", alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={form.weekly_off_day_codes.includes(day.code)}
                    onChange={(event) =>
                      update(
                        "weekly_off_day_codes",
                        event.target.checked ? [...form.weekly_off_day_codes, day.code] : form.weekly_off_day_codes.filter((code) => code !== day.code),
                      )
                    }
                  />
                  {day.label}
                </label>
              ))}
            </div>
            <span className="helper-text">Leave every day unticked for a 7-day week.</span>
          </div>
        ) : null}
        <ChoiceField label="Work on an off day or holiday is charged at" value={form.off_day_work_treatment_code} options={OFF_DAY_WORK} onChange={(value) => update("off_day_work_treatment_code", value)} />
        {form.off_day_work_treatment_code === "HOLIDAY_RATE" ? (
          <RateField label="Holiday rate" rate={form.holiday_rate} methods={RATE_METHODS} onChange={(rate) => update("holiday_rate", rate)} />
        ) : null}
      </>
    ),
    overtime: (
      <>
        <RateField label="Overtime" rate={form.overtime_rate} methods={[NOT_IN_WORK_ORDER, ...RATE_METHODS]} onChange={(rate) => update("overtime_rate", rate)} />
        {groups.monthOvertime && overtimeCharged ? (
          <>
            <ChoiceField label="Overtime hours counted" value={form.month_overtime_hours_basis_code} options={MONTH_OT_HOURS} onChange={(value) => update("month_overtime_hours_basis_code", value)} />
            <ChoiceField label="Overtime counted" value={form.month_overtime_counting_code} options={MONTH_OT_COUNTING} onChange={(value) => update("month_overtime_counting_code", value)} />
          </>
        ) : null}
        {asksOvertimeCountedPer(form) ? (
          <ChoiceField label="On these shifts, overtime is counted" value={form.overtime_counted_per_code} options={OVERTIME_COUNTED_PER} onChange={(value) => update("overtime_counted_per_code", value)} />
        ) : null}
      </>
    ),
    breakdown: (
      <>
        <ChoiceField label="Breakdown hours" value={form.breakdown_treatment_code} options={BREAKDOWN} onChange={(value) => update("breakdown_treatment_code", value)} />
        {form.breakdown_treatment_code === "DEDUCT_AT_BREAKDOWN_RATE" ? (
          <RateField label="Breakdown rate" rate={form.breakdown_rate} methods={RATE_METHODS} onChange={(rate) => update("breakdown_rate", rate)} />
        ) : null}
        {breakdownDeducts && overtimeCharged ? (
          <label className="terms-wide" style={{ display: "flex", gap: "6px", alignItems: "center" }}>
            <input type="checkbox" checked={form.breakdown_offset_by_same_day_overtime} onChange={(event) => update("breakdown_offset_by_same_day_overtime", event.target.checked)} />
            Overtime on the same day offsets breakdown hours
          </label>
        ) : null}
      </>
    ),
    idle: (
      <>
        <div className="terms-wide terms-subgrid">
          <ChoiceField label="Idle time caused by the customer is" value={form.customer_idle_treatment_code} options={IDLE} onChange={(value) => update("customer_idle_treatment_code", value)} />
          {form.customer_idle_treatment_code === "STANDBY_RATE" ? (
            <RateField label="Standby rate" rate={form.standby_rate} methods={RATE_METHODS} onChange={(rate) => update("standby_rate", rate)} />
          ) : null}
        </div>
        {groups.minimumGuarantee || groups.partMonth ? (
          <div className="terms-wide terms-subgrid">
            {groups.minimumGuarantee ? (
              <ChoiceField label="Minimum guarantee" value={form.minimum_guarantee_code} options={MINIMUM} onChange={(value) => update("minimum_guarantee_code", value)} />
            ) : null}
            {groups.minimumGuarantee && form.minimum_guarantee_code === "UNITS_PER_MONTH" ? (
              <NumberField
                label={`Minimum ${basisUnit}s a month`}
                value={form.minimum_billing_units_per_month}
                onChange={(value) => update("minimum_billing_units_per_month", value)}
              />
            ) : null}
            {groups.partMonth ? (
              <ChoiceField label="A part month is divided by" value={form.part_month_basis_code} options={PART_MONTH} onChange={(value) => update("part_month_basis_code", value)} />
            ) : null}
          </div>
        ) : null}
      </>
    ),
    shifts: (
      <>
        {legacyNightShiftNote(period) ? <span className="helper-text terms-wide">{legacyNightShiftNote(period)}</span> : null}
        <ChoiceField label="Shifts a day" value={form.shift_pattern_code} options={SHIFT_PATTERNS} onChange={(value) => update("shift_pattern_code", value)} />
        {severalShifts ? (
          <ChoiceField label="The shifts are charged" value={form.shift_rate_code} options={SHIFT_RATES} onChange={(value) => update("shift_rate_code", value)} />
        ) : null}
        {shiftCount > 0 ? (
          <div className="terms-wide terms-subgrid">
            {[1, 2, 3].slice(0, shiftCount).map((shift) => (
              <NumberField
                key={shift}
                label={`Shift ${shift} hours`}
                value={form[`shift_${shift}_hours` as "shift_1_hours"]}
                onChange={(value) => update(`shift_${shift}_hours` as "shift_1_hours", value)}
              />
            ))}
          </div>
        ) : null}
        {severalShifts && form.shift_rate_code === SHIFT_RATE_PER_SHIFT
          ? [2, 3].slice(0, shiftCount - 1).map((shift) => {
              const rateField = `shift_${shift}_rate` as "shift_2_rate";
              const daysField = `shift_${shift}_working_days_per_month` as "shift_2_working_days_per_month";
              return (
                <div key={shift} className="terms-wide terms-subgrid">
                  <ShiftRateField shift={shift} rate={form[rateField]} onChange={(rate) => update(rateField, rate)} />
                  {groups.shiftWorkingDays ? (
                    <NumberField label={`Shift ${shift} working days per month`} value={form[daysField]} onChange={(value) => update(daysField, value)} />
                  ) : null}
                </div>
              );
            })
          : null}
        {shiftCount > 0 ? (
          <span className="helper-text terms-wide">
            Each shift's hours in a day, as the Work Order states them; together no more than 24. Enter the contracted hours
            above as the Work Order states them too.
          </span>
        ) : null}
      </>
    ),
    fuel: (
      <>
        <ChoiceField label="Fuel is" value={form.fuel_treatment_code} options={FUEL} onChange={(value) => update("fuel_treatment_code", value)} />
        {form.fuel_treatment_code === FUEL_PBL_CHARGED ? (
          <ChoiceField label="Charged" value={form.fuel_charge_method_code} options={FUEL_CHARGE_METHODS} onChange={(value) => update("fuel_charge_method_code", value)} />
        ) : null}
        {form.fuel_treatment_code === FUEL_PBL_CHARGED && form.fuel_charge_method_code === FUEL_AGREED_RATE_PER_LITRE ? (
          <NumberField label="Agreed rate per litre (INR)" value={form.fuel_rate_per_litre_amount} onChange={(value) => update("fuel_rate_per_litre_amount", value)} />
        ) : null}
        {form.fuel_treatment_code === FUEL_CUSTOMER_SUPPLIED ? (
          <>
            <NumberField label="Agreed litres per working hour" value={form.fuel_litres_per_working_hour} onChange={(value) => update("fuel_litres_per_working_hour", value)} />
            <ChoiceField label="While travelling" value={form.fuel_travel_allowance_code} options={FUEL_TRAVEL} onChange={(value) => update("fuel_travel_allowance_code", value)} />
            {form.fuel_travel_allowance_code === FUEL_TRAVEL_LITRES_PER_HOUR ? (
              <NumberField label="Agreed litres per travel hour" value={form.fuel_litres_per_travel_hour} onChange={(value) => update("fuel_litres_per_travel_hour", value)} />
            ) : null}
            <span className="helper-text terms-wide">
              Use above the agreed litres is recovered as a debit note. The check against actual use happens with the log sheets.
            </span>
          </>
        ) : null}
      </>
    ),
    extraKm: (
      <>
        <ChoiceField label="Kilometres in the rate" value={form.extra_km_allowance_code} options={EXTRA_KM} onChange={(value) => update("extra_km_allowance_code", value)} />
        {EXTRA_KM_INCLUDED_CODES.includes(form.extra_km_allowance_code) ? (
          <>
            <NumberField
              label={form.extra_km_allowance_code === "KM_PER_MONTH" ? "Kilometres included per month" : "Kilometres included per day"}
              value={form.extra_km_included_km}
              onChange={(value) => update("extra_km_included_km", value)}
            />
            <NumberField label="Rate per extra kilometre (INR)" value={form.extra_km_rate_amount} onChange={(value) => update("extra_km_rate_amount", value)} />
          </>
        ) : null}
      </>
    ),
    crew: (
      <>
        <div className="terms-wide terms-subgrid">
          <ChoiceField label="Crew" value={form.crew_code} options={CREW} onChange={(value) => update("crew_code", value)} />
          {form.crew_code === CREW_STATED ? (
            <>
              <WholeNumberField label={`Operators per ${basisUnit}`} value={form.crew_operators_per_unit} onChange={(value) => update("crew_operators_per_unit", value)} />
              <WholeNumberField label={`Helpers per ${basisUnit}`} value={form.crew_helpers_per_unit} onChange={(value) => update("crew_helpers_per_unit", value)} />
            </>
          ) : null}
        </div>
        {form.crew_code === CREW_STATED ? (
          <div className="terms-wide terms-subgrid">
            <ChoiceField label="Crew beyond these numbers" value={form.extra_crew_charge_code} options={EXTRA_CREW} onChange={(value) => update("extra_crew_charge_code", value)} />
            {form.extra_crew_charge_code === EXTRA_CREW_RATE_PER_PERSON ? (
              <>
                <NumberField label={`Each extra operator, per ${basisUnit} (INR)`} value={form.extra_crew_operator_rate_amount} onChange={(value) => update("extra_crew_operator_rate_amount", value)} />
                <NumberField label={`Each extra helper, per ${basisUnit} (INR)`} value={form.extra_crew_helper_rate_amount} onChange={(value) => update("extra_crew_helper_rate_amount", value)} />
              </>
            ) : null}
          </div>
        ) : null}
        {form.crew_code === CREW_STATED ? (
          <span className="helper-text terms-wide">
            Enter 0 where the Work Order has none, for example no helpers. These are the numbers the customer is charged for; what the crew are paid comes from PBL's own terms.
          </span>
        ) : null}
      </>
    ),
    upkeep: (
      <>
        {upkeepRoleApplies(form, UPKEEP_ROLES[0]) && upkeepRoleApplies(form, UPKEEP_ROLES[1]) ? (
          <div className="terms-wide terms-action-row">
            <button type="button" onClick={() => update("upkeep", upkeepWithHelpersAsOperators(form.upkeep))}>
              Same as for operators
            </button>
            <span className="helper-text">Copies the operators' answers below to the helpers. Change any that differ.</span>
          </div>
        ) : null}
        {UPKEEP_ITEMS.map((item) => (
          <div key={item.key} className="terms-wide terms-subgrid">
            <p className="terms-upkeep-item">{item.label}</p>
            {UPKEEP_CELLS.filter((cell) => cell.item.key === item.key && upkeepRoleApplies(form, cell.role)).map((cell) => (
              <UpkeepCellFields
                key={cell.key}
                label={cell.role.label}
                units={cell.item.units}
                answer={form.upkeep[cell.key]}
                onChange={(answer) => update("upkeep", { ...form.upkeep, [cell.key]: answer })}
              />
            ))}
          </div>
        ))}
        <span className="helper-text terms-wide">
          Choose "Provided by the customer" when the Work Order gives it free, for example a site camp or mess. A cost says
          what it is for: per person, or for a trip or a day whatever the number of people.
        </span>
      </>
    ),
    lineOnce: (
      <>
        <div className="terms-wide terms-subgrid">
          <ChoiceField label="Mobilisation is" value={form.mobilisation_charge_code} options={MOBILISATION} onChange={(value) => update("mobilisation_charge_code", value)} />
          {MOBILISATION_CHARGED_CODES.includes(form.mobilisation_charge_code) ? (
            <NumberField label="Mobilisation charge (INR)" value={form.mobilisation_charge_amount} onChange={(value) => update("mobilisation_charge_amount", value)} />
          ) : null}
          {form.mobilisation_charge_code === "CHARGED_CREDITED_AFTER_MONTHS" ? (
            <MonthsField label="Credited back if the machine stays beyond (months)" value={form.mobilisation_credit_after_months} onChange={(value) => update("mobilisation_credit_after_months", value)} />
          ) : null}
        </div>
        <div className="terms-wide terms-subgrid">
          <ChoiceField label="Demobilisation is" value={form.demobilisation_charge_code} options={DEMOBILISATION} onChange={(value) => update("demobilisation_charge_code", value)} />
          {DEMOBILISATION_CHARGED_CODES.includes(form.demobilisation_charge_code) ? (
            <NumberField label="Demobilisation charge (INR)" value={form.demobilisation_charge_amount} onChange={(value) => update("demobilisation_charge_amount", value)} />
          ) : null}
          {form.demobilisation_charge_code === "CHARGED_WAIVED_AFTER_MONTHS" ? (
            <MonthsField label="Not charged if the machine stays beyond (months)" value={form.demobilisation_waived_after_months} onChange={(value) => update("demobilisation_waived_after_months", value)} />
          ) : null}
        </div>
      </>
    ),
  };

  return disclosure(
    <fieldset disabled={lineBusy} className="terms-form">
        {period.period_number > 1 ? (
          <label className="field-stack" style={{ maxWidth: "260px" }}>
            Starts on
            <DateInput value={form.effective_from} onChange={(event) => update("effective_from", event.target.value)} style={FIELD_STYLE} />
          </label>
        ) : null}

        {visibleTermChapters(basis, period.period_number, form.crew_code).map((chapter) => (
          <Fragment key={chapter.key}>
            <TermChapterHeading chapter={chapter} />
            {chapter.groups.map((group) => (
              <TermGroupCard
                key={group}
                title={GROUP_TITLES[group]}
                description={groupDescription(group, basis)}
                tone={chapter.tone}
                status={termGroupStatus(group, period, basis)}
              >
                {bodies[group]}
              </TermGroupCard>
            ))}
          </Fragment>
        ))}

        <div className="terms-action-bar">
          <label className="field-stack" style={{ maxWidth: "720px" }}>
            Notes on these terms
            <textarea value={form.term_notes} onChange={(event) => update("term_notes", event.target.value)} rows={2} maxLength={4000} />
          </label>
          <div className="terms-action-row">
            <button type="button" onClick={() => void write("PUT", setSaveFeedback, "Terms saved.")} disabled={lineBusy} style={{ padding: "8px 14px", fontWeight: 700 }}>
              {busy === "PUT" ? "Saving..." : "Save terms"}
            </button>
            {saveFeedback ? <p style={{ color: saveFeedback.kind === "success" ? "#065f46" : "crimson" }}>{saveFeedback.text}</p> : null}
          </div>
          {canRemove && isLatest ? (
            <div className="terms-action-row">
              <button type="button" onClick={() => void write("DELETE", setRemoveFeedback, "Period removed.")} disabled={lineBusy} style={{ padding: "6px 10px" }}>
                {busy === "DELETE" ? "Removing..." : "Remove this period"}
              </button>
              {removeFeedback ? <p style={{ color: removeFeedback.kind === "success" ? "#065f46" : "crimson" }}>{removeFeedback.text}</p> : null}
            </div>
          ) : null}
        </div>
      </fieldset>,
  );
}

/** A chapter's heading: its title and a short line on what it covers, in the chapter's tone. */
function TermChapterHeading({ chapter }: { chapter: TermChapter }) {
  return (
    <div className={`terms-chapter section-card--${chapter.tone}`}>
      <h5 className="terms-chapter-title">{chapter.title}</h5>
      <p className="terms-chapter-description">{chapter.description}</p>
    </div>
  );
}

type TermGroupCardProps = {
  title: string;
  description: string;
  tone: TermChapter["tone"];
  status: "answered" | "missing" | null;
  children: ReactNode;
};

/** One group of terms as a card: title, what it covers, whether its saved answers are complete. */
function TermGroupCard({ title, description, tone, status, children }: TermGroupCardProps) {
  const titleId = useId();
  return (
    <section className={`terms-group section-card--${tone}`} aria-labelledby={titleId}>
      <div className="terms-group-header">
        <div>
          <h6 id={titleId} className="terms-group-title">{title}</h6>
          <p className="terms-group-description">{description}</p>
        </div>
        {status ? (
          <span className={`status-badge ${status === "missing" ? "status-badge--warning" : "status-badge--success"}`}>
            {status === "missing" ? "Still needed" : "Answered"}
          </span>
        ) : null}
      </div>
      <div className="terms-group-body">{children}</div>
    </section>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="field-stack">
      {label}
      <input type="number" min="0.01" step="0.01" value={value} onChange={(event) => onChange(event.target.value)} style={FIELD_STYLE} />
    </label>
  );
}

/** A whole number of people, zero allowed: "2 operators, no helpers" is a real answer (decision 28). */
function WholeNumberField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="field-stack">
      {label}
      <input type="number" min="0" max={CREW_COUNT_MAX} step="1" value={value} onChange={(event) => onChange(event.target.value)} style={FIELD_STYLE} />
    </label>
  );
}

/** A whole number of months, at least one: how the months are counted belongs to billing. */
function MonthsField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="field-stack">
      {label}
      <input type="number" min="1" step="1" value={value} onChange={(event) => onChange(event.target.value)} style={FIELD_STYLE} />
    </label>
  );
}

/** A later shift's own rate, which unlike the other rates may also be a rate per shift (Part 2's night shift). */
function ShiftRateField({ shift, rate, onChange }: { shift: number; rate: RateForm; onChange: (rate: RateForm) => void }) {
  const valueLabel =
    rate.method === SHIFT_RATE_METHOD_PER_SHIFT
      ? `Shift ${shift} rate per shift (INR)`
      : rate.method === "RATE_PER_HOUR"
        ? `Shift ${shift} rate per hour (INR)`
        : `Shift ${shift} rate as % of the first shift's rate`;
  return (
    <>
      <ChoiceField
        label={`Shift ${shift} is charged at`}
        value={rate.method}
        options={SHIFT_RATE_METHODS}
        onChange={(method) => onChange({ method, value: method === rate.method ? rate.value : "" })}
      />
      {rate.method ? <NumberField label={valueLabel} value={rate.value} onChange={(value) => onChange({ ...rate, value })} /> : null}
    </>
  );
}

/** One upkeep answer for operators or helpers: the choice, and at a cost its amount, unit and recovery. */
function UpkeepCellFields({ label, units, answer, onChange }: { label: string; units: readonly Option[]; answer: UpkeepCellForm; onChange: (answer: UpkeepCellForm) => void }) {
  return (
    <div className="terms-upkeep-cell">
      <ChoiceField label={label} value={answer.code} options={UPKEEP_CHOICES} onChange={(code) => onChange({ ...answer, code })} />
      {answer.code === UPKEEP_AT_COST ? (
        <>
          <NumberField label="Cost (INR)" value={answer.amount} onChange={(amount) => onChange({ ...answer, amount })} />
          <ChoiceField label="The cost is" value={answer.unit} options={[...units]} onChange={(unit) => onChange({ ...answer, unit })} />
          <ChoiceField label="The customer recovers it" value={answer.recovery} options={UPKEEP_RECOVERIES} onChange={(recovery) => onChange({ ...answer, recovery })} />
        </>
      ) : null}
    </div>
  );
}

function ChoiceField({ label, value, options, onChange }: { label: string; value: string; options: Option[]; onChange: (value: string) => void }) {
  return (
    <label className="field-stack">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)} style={FIELD_STYLE}>
        <option value="">Not chosen</option>
        {options.map((option) => (
          <option key={option.code} value={option.code}>{option.label}</option>
        ))}
      </select>
    </label>
  );
}

function RateField({ label, rate, methods, onChange }: { label: string; rate: RateForm; methods: Option[]; onChange: (rate: RateForm) => void }) {
  const needsValue = rate.method === "RATE_PER_HOUR" || rate.method === "PERCENT_OF_NORMAL";
  return (
    <>
      <ChoiceField label={label} value={rate.method} options={methods} onChange={(method) => onChange({ method, value: method === rate.method ? rate.value : "" })} />
      {needsValue ? (
        <NumberField
          label={rate.method === "RATE_PER_HOUR" ? `${label} per hour (INR)` : `${label} as % of the normal rate`}
          value={rate.value}
          onChange={(value) => onChange({ ...rate, value })}
        />
      ) : null}
    </>
  );
}

const OPTION_LABELS: Record<string, string> = Object.fromEntries(
  [
    ...OFF_DAY_WORK,
    ...MONTH_OT_HOURS,
    ...MONTH_OT_COUNTING,
    ...BREAKDOWN,
    ...IDLE,
    ...MINIMUM,
    ...PART_MONTH,
    ...FUEL,
    ...FUEL_CHARGE_METHODS,
    ...FUEL_TRAVEL,
    // Mobilisation and demobilisation share the code CHARGED with the same label, and their
    // "after a number of months" codes differ, so merging both lists is unambiguous.
    ...MOBILISATION,
    ...DEMOBILISATION,
    // Part 4. Both label NONE "Not in the Work Order", as the lists above do. The crew choice is not
    // merged: its NONE reads "equipment only", which would relabel every other term's NONE.
    ...EXTRA_KM,
    ...EXTRA_CREW,
  ].map((option) => [option.code, option.label]),
);

/** The crew choice as read back: its NONE means equipment only, not "not in the Work Order". */
function crewText(code: string | null): string {
  return CREW.find((option) => option.code === code)?.label ?? "-";
}

/** A later shift's rate as one line of text, whichever way it is given. */
function shiftRateText(period: BillingTermPeriod, shift: 2 | 3): string {
  const method = period[`shift_${shift}_rate_method_code`];
  const amount = period[`shift_${shift}_rate_amount`];
  if (method === SHIFT_RATE_METHOD_PER_SHIFT) return `INR ${amount} per shift`;
  if (method === "RATE_PER_HOUR") return `INR ${amount} per hour`;
  if (method === "PERCENT_OF_NORMAL") return `${period[`shift_${shift}_rate_percent`]}% of the first shift's rate (the Work Order rate)`;
  return "-";
}

function optionLabel(options: Option[], code: string | null): string {
  return options.find((option) => option.code === code)?.label ?? "-";
}

function rateText(method: string | null, amount: string | null, percent: string | null): string {
  if (method === "RATE_PER_HOUR") return `INR ${amount} per hour`;
  if (method === "PERCENT_OF_NORMAL") return `${percent}% of the normal rate`;
  if (method === "NONE") return "Not in the Work Order";
  return "-";
}

function ReadOnlyPeriod({ period }: { period: BillingTermPeriod }) {
  const basis = period.billing_uom_code ?? "";
  const groups = visibleTermGroups(basis);
  const label = (code: string | null) => (code ? OPTION_LABELS[code] ?? code : "-");
  // Each row goes to the card of the group it belongs to; the cards and chapters are the same as the form's.
  const rows: Record<TermGroupKey, [string, string][]> = {
    basis: [], offDays: [], shifts: [], overtime: [], breakdown: [], idle: [], fuel: [], extraKm: [], crew: [], upkeep: [], lineOnce: [],
  };
  rows.basis.push(["Billing basis", billingBasisLabel(period.billing_uom_code) ?? "-"]);
  if (groups.rate) rows.basis.push(["Work Order rate", period.normal_rate_amount ? `INR ${period.normal_rate_amount}` : "-"]);
  if (groups.contractedHours) rows.basis.push([HOURS_LABELS[basis] ?? "Contracted hours", period.contracted_hours_per_billing_unit ?? "-"]);
  if (groups.workingDays) rows.basis.push(["Working days per month", period.contracted_working_days_per_month ?? "-"]);
  if (groups.offDays) {
    rows.offDays.push(["Weekly off days", period.weekly_off_day_codes == null ? "-" : period.weekly_off_day_codes.length === 0 ? "None (7-day week)" : period.weekly_off_day_codes.join(", ")]);
    rows.offDays.push(["Off-day work charged at", label(period.off_day_work_treatment_code)]);
    if (period.off_day_work_treatment_code === "HOLIDAY_RATE") rows.offDays.push(["Holiday rate", rateText(period.holiday_rate_method_code, period.holiday_rate_amount, period.holiday_rate_percent)]);
  }
  if (groups.overtime) rows.overtime.push(["Overtime", rateText(period.overtime_rate_method_code, period.overtime_rate_amount, period.overtime_rate_percent)]);
  if (showsMonthOvertimeRows(period)) {
    rows.overtime.push(["Overtime hours counted", label(period.month_overtime_hours_basis_code)]);
    rows.overtime.push(["Overtime counted", label(period.month_overtime_counting_code)]);
  }
  const overtimeAsked = {
    billing_uom_code: basis,
    overtime_rate: { method: period.overtime_rate_method_code ?? "", value: "" },
    shift_pattern_code: period.shift_pattern_code ?? "",
  };
  if (asksOvertimeCountedPer(overtimeAsked)) {
    rows.overtime.push(["On these shifts, overtime is counted", optionLabel(OVERTIME_COUNTED_PER, period.overtime_counted_per_code)]);
  }
  if (groups.breakdown) {
    rows.breakdown.push(["Breakdown hours", label(period.breakdown_treatment_code)]);
    if (period.breakdown_treatment_code === "DEDUCT_AT_BREAKDOWN_RATE") rows.breakdown.push(["Breakdown rate", rateText(period.breakdown_rate_method_code, period.breakdown_rate_amount, period.breakdown_rate_percent)]);
    if (period.breakdown_offset_by_same_day_overtime) rows.breakdown.push(["Same-day overtime", "Offsets breakdown hours"]);
  }
  if (groups.rate) {
    rows.idle.push(["Idle time", label(period.customer_idle_treatment_code)]);
    if (period.customer_idle_treatment_code === "STANDBY_RATE") rows.idle.push(["Standby rate", rateText(period.standby_rate_method_code, period.standby_rate_amount, period.standby_rate_percent)]);
  }
  if (groups.minimumGuarantee) {
    rows.idle.push(["Minimum guarantee", period.minimum_guarantee_code === "UNITS_PER_MONTH" ? `${period.minimum_billing_units_per_month} a month` : label(period.minimum_guarantee_code)]);
  }
  if (groups.partMonth) rows.idle.push(["Part month divided by", label(period.part_month_basis_code)]);
  if (groups.shifts) {
    rows.shifts.push(["Shifts a day", optionLabel(SHIFT_PATTERNS, period.shift_pattern_code)]);
    const legacy = legacyNightShiftNote(period);
    if (legacy) rows.shifts.push(["Before 10 October 2026", legacy]);
    // Each stated shift's hours, and with two or three what they are charged, each with "-" for a gap, so a
    // half-recorded choice is visible rather than hidden (the Part 1 round-3 lesson about the monthly overtime rows).
    const count = shiftsPerDay(period.shift_pattern_code);
    for (const shift of [1, 2, 3].slice(0, count)) {
      const hours = period[`shift_${shift}_hours` as "shift_1_hours"];
      rows.shifts.push([`Shift ${shift} hours`, hours ?? "-"]);
    }
    if (SHIFT_PATTERNS_SEVERAL.includes(period.shift_pattern_code ?? "")) {
      rows.shifts.push(["The shifts are charged", optionLabel(SHIFT_RATES, period.shift_rate_code)]);
      if (period.shift_rate_code === SHIFT_RATE_PER_SHIFT) {
        for (const shift of ([2, 3] as const).slice(0, count - 1)) {
          rows.shifts.push([`Shift ${shift} rate`, shiftRateText(period, shift)]);
          if (groups.shiftWorkingDays) rows.shifts.push([`Shift ${shift} working days per month`, period[`shift_${shift}_working_days_per_month`] ?? "-"]);
        }
      }
    }
  }
  if (groups.fuel) {
    rows.fuel.push(["Fuel", label(period.fuel_treatment_code)]);
    if (period.fuel_treatment_code === FUEL_PBL_CHARGED) {
      rows.fuel.push(["Fuel charged", label(period.fuel_charge_method_code)]);
      if (period.fuel_charge_method_code === FUEL_AGREED_RATE_PER_LITRE) {
        rows.fuel.push(["Rate per litre", period.fuel_rate_per_litre_amount ? `INR ${period.fuel_rate_per_litre_amount}` : "-"]);
      }
    }
    if (period.fuel_treatment_code === FUEL_CUSTOMER_SUPPLIED) {
      rows.fuel.push(["Agreed litres per working hour", period.fuel_litres_per_working_hour ?? "-"]);
      rows.fuel.push(["While travelling", label(period.fuel_travel_allowance_code)]);
      if (period.fuel_travel_allowance_code === FUEL_TRAVEL_LITRES_PER_HOUR) {
        rows.fuel.push(["Agreed litres per travel hour", period.fuel_litres_per_travel_hour ?? "-"]);
      }
    }
  }
  if (groups.extraKm) {
    rows.extraKm.push(["Kilometres in the rate", label(period.extra_km_allowance_code)]);
    // Shown whenever an allowance is chosen, each with "-" for a gap, so a half-recorded choice is visible.
    if (EXTRA_KM_INCLUDED_CODES.includes(period.extra_km_allowance_code ?? "")) {
      rows.extraKm.push([
        period.extra_km_allowance_code === "KM_PER_MONTH" ? "Kilometres included per month" : "Kilometres included per day",
        period.extra_km_included_km ?? "-",
      ]);
      rows.extraKm.push(["Rate per extra kilometre", period.extra_km_rate_amount ? `INR ${period.extra_km_rate_amount}` : "-"]);
    }
  }
  if (groups.crew) {
    const unit = billingBasisLabel(basis)?.toLowerCase() ?? "billing unit";
    rows.crew.push(["Crew", crewText(period.crew_code)]);
    if (period.crew_code === CREW_STATED) {
      rows.crew.push([`Operators per ${unit}`, period.crew_operators_per_unit != null ? String(period.crew_operators_per_unit) : "-"]);
      rows.crew.push([`Helpers per ${unit}`, period.crew_helpers_per_unit != null ? String(period.crew_helpers_per_unit) : "-"]);
      rows.crew.push(["Crew beyond these numbers", label(period.extra_crew_charge_code)]);
      if (period.extra_crew_charge_code === EXTRA_CREW_RATE_PER_PERSON) {
        rows.crew.push([`Each extra operator, per ${unit}`, period.extra_crew_operator_rate_amount ? `INR ${period.extra_crew_operator_rate_amount}` : "-"]);
        rows.crew.push([`Each extra helper, per ${unit}`, period.extra_crew_helper_rate_amount ? `INR ${period.extra_crew_helper_rate_amount}` : "-"]);
      }
    }
  }
  for (const cell of UPKEEP_CELLS) {
    if (upkeepRoleApplies(crewOfPeriod(period), cell.role)) {
      rows.upkeep.push([`${cell.item.label}, ${cell.role.label.toLowerCase()}`, upkeepAnswerText(cell, period)]);
    }
  }
  if (showsLineOnceTerms(period.period_number) && groups.fuel) {
    rows.lineOnce.push(["Mobilisation", label(period.mobilisation_charge_code)]);
    if (MOBILISATION_CHARGED_CODES.includes(period.mobilisation_charge_code ?? "")) {
      rows.lineOnce.push(["Mobilisation charge", period.mobilisation_charge_amount ? `INR ${period.mobilisation_charge_amount}` : "-"]);
    }
    if (period.mobilisation_charge_code === "CHARGED_CREDITED_AFTER_MONTHS") {
      rows.lineOnce.push(["Credited back after", period.mobilisation_credit_after_months != null ? `${period.mobilisation_credit_after_months} months` : "-"]);
    }
    rows.lineOnce.push(["Demobilisation", label(period.demobilisation_charge_code)]);
    if (DEMOBILISATION_CHARGED_CODES.includes(period.demobilisation_charge_code ?? "")) {
      rows.lineOnce.push(["Demobilisation charge", period.demobilisation_charge_amount ? `INR ${period.demobilisation_charge_amount}` : "-"]);
    }
    if (period.demobilisation_charge_code === "CHARGED_WAIVED_AFTER_MONTHS") {
      rows.lineOnce.push(["Not charged after", period.demobilisation_waived_after_months != null ? `${period.demobilisation_waived_after_months} months` : "-"]);
    }
  }
  return (
    <div className="terms-form">
      {visibleTermChapters(basis, period.period_number, period.crew_code ?? "").map((chapter) => (
        <Fragment key={chapter.key}>
          <TermChapterHeading chapter={chapter} />
          {chapter.groups.map((group) => (
            <TermGroupCard
              key={group}
              title={GROUP_TITLES[group]}
              description={groupDescription(group, basis)}
              tone={chapter.tone}
              status={termGroupStatus(group, period, basis)}
            >
              <ReadOnlyRows rows={rows[group]} />
            </TermGroupCard>
          ))}
        </Fragment>
      ))}
      <ReadOnlyRows rows={[["Notes", period.term_notes || "-"]]} />
    </div>
  );
}

function ReadOnlyRows({ rows }: { rows: [string, string][] }) {
  return (
    <dl className="terms-readonly-list terms-wide">
      {rows.map(([term, value]) => (
        <div key={term} style={{ display: "contents" }}>
          <dt>{term}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
