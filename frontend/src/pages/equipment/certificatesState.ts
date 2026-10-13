// Pure rules for the machine eligibility screens (ELG-1), kept out of the components so they can be tested
// without a browser DOM. The backend re-checks everything and words every refusal; these keep a form from
// sending what it can already tell is incomplete, and word what the screens show.
//
// The Fleet Admin (Admin, for now) records each machine's certificates with a copy, and marks one "not
// applicable" only where a rule says the law is unclear. Eligibility answers whether a machine - with its
// fitted parts - or a piece of kit may work at a site over a period. Certificates due is the renewal list.

import type { StatusTone } from "../../components/PageLayout";
import { createLatestOnly, isCompleteIsoDate } from "../resource-requirements/resourceRequirementState";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

// --- What the API returns ------------------------------------------------------------------------------

export type AssetSummary = {
  asset_public_id: string;
  asset_reference: string;
  asset_kind_code: string;
  origin_code: string;
  class_code: string;
  class_label: string;
  type_code: string | null;
  type_label: string | null;
  machine_number: string | null;
  serial_number: string | null;
  asset_status_code: string;
};

export type Certificate = {
  certificate_public_id: string;
  asset_public_id: string;
  asset_reference: string;
  kind_code: string;
  kind_label: string;
  number: string | null;
  number_withheld: boolean;
  issued_by: string;
  issued_on: string;
  valid_from: string;
  valid_until: string | null;
  valid_in_code: string | null;
  valid_in_label: string | null;
  registered_as_code: string | null;
  certificate_status_code: string;
  has_copy: boolean;
  in_force: boolean;
  recorded_by_display_name: string | null;
  recorded_at: string;
  withdrawn_reason: string | null;
  withdrawn_by_display_name: string | null;
  withdrawn_at: string | null;
};

export type Mark = {
  mark_public_id: string;
  asset_public_id: string;
  asset_reference: string;
  kind_code: string;
  kind_label: string;
  /** Withheld (null) with the numbers: free text may repeat one. */
  reason: string | null;
  reason_withheld: boolean;
  until_date: string | null;
  recorded_on: string;
  mark_status_code: string;
  allowed_by_rule_public_id: string;
  recorded_by_display_name: string | null;
  recorded_at: string;
  withdrawn_reason: string | null;
  withdrawn_by_display_name: string | null;
  withdrawn_at: string | null;
};

export type RuleSummary = {
  rule_public_id: string;
  jurisdiction_code: string | null;
  basis_code: string;
  lapse_code: string;
  renew_every_months: number | null;
  not_applicable_code: string;
  not_applicable_max_months: number | null;
  source: string;
  note: string | null;
};

export type KindStatus = {
  kind_code: string;
  kind_label: string;
  required: boolean;
  rule: RuleSummary | null;
  outcome_code: string | null;
  cover_ends_on: string | null;
  certificate: Certificate | null;
  mark: Mark | null;
};

export type MarkableKind = { kind_code: string; kind_label: string; rule: RuleSummary; latest_until: string | null };

export type AssetCertificates = {
  asset: AssetSummary;
  fitted_to: AssetSummary | null;
  fitted_parts: AssetSummary[];
  numbers_withheld: boolean;
  statuses: KindStatus[];
  certificates: Certificate[];
  marks: Mark[];
  recordable_kind_codes: string[];
  markable_kinds: MarkableKind[];
};

export type CertificateAction = {
  certificates: AssetCertificates;
  certificate_public_id: string | null;
  mark_public_id: string | null;
  replayed: boolean;
  event: unknown;
};

export type CheckResult = {
  asset_public_id: string;
  asset_reference: string;
  kind_code: string | null;
  kind_label: string | null;
  outcome_code: string;
  effect_code: string;
  lapse_code: string | null;
  basis_code: string | null;
  rule_public_id: string | null;
  rule_jurisdiction_code: string | null;
  certificate_public_id: string | null;
  certificate_asset_reference: string | null;
  mark_public_id: string | null;
  cover_ends_on: string | null;
};

export type EligibilityCheck = {
  asset: AssetSummary;
  site_state_code: string;
  site_state_label: string;
  central_government_site: boolean;
  period_from: string;
  period_to: string | null;
  evaluated_on: string;
  overall_code: string;
  valid_until: string | null;
  outcome_counts: Record<string, number>;
  results: CheckResult[];
};

export type DueItem = {
  asset: AssetSummary;
  kind_code: string;
  kind_label: string;
  band_code: string;
  outcome_code: string;
  cover_ends_on: string | null;
  certificate_public_id: string | null;
  certificate_asset_reference: string | null;
  mark_public_id: string | null;
};

export type CertificatesDue = { today: string; band_counts: Record<string, number>; total: number; limit: number; offset: number; items: DueItem[] };

export type Jurisdiction = { jurisdiction_code: string; jurisdiction_label: string; jurisdiction_kind_code: string; gst_state_code: string | null };

export type CertificateKind = {
  kind_code: string;
  kind_label: string;
  end_date_optional: boolean;
  valid_in_required: boolean;
  is_examination: boolean;
  states_registration: boolean;
};

export type EligibilityRule = RuleSummary & {
  kind_code: string;
  kind_label: string;
  class_code: string;
  class_label: string;
  type_code: string | null;
  type_label: string | null;
  applies_when_code: string;
  jurisdiction_label: string | null;
  effective_from: string;
  effective_to: string | null;
  state_code: string;
  recorded_by_display_name: string | null;
  recorded_at: string;
  ended_by_display_name: string | null;
  ended_at: string | null;
  end_reason: string | null;
};

// --- Loading one answer (the list controller's rules, for a page showing one answer) --------------------------

export type QueryUpdate<Answer> =
  | { kind: "loading" }
  | { kind: "answer"; answer: Answer }
  | { kind: "failed"; message: string }
  | { kind: "signed-out" };

export type QueryView<Answer> = { answer: Answer | null; loading: boolean; error: string };

export function initialQueryView<Answer>(): QueryView<Answer> {
  return { answer: null, loading: false, error: "" };
}

/** What a page shows: an answer only as the answer to the request now awaited. The moment a new request starts -
 *  another filter, page, asset or a reload - the previous answer is no longer shown, so a page never shows one
 *  query's answer under another's controls (as the machines list, equipmentState.ts's listView). */
export function queryView<Answer>(view: QueryView<Answer>, update: QueryUpdate<Answer>): QueryView<Answer> {
  switch (update.kind) {
    case "loading":
      return { answer: null, loading: true, error: "" };
    case "answer":
      return { answer: update.answer, loading: false, error: "" };
    case "failed":
      return { answer: null, loading: false, error: update.message };
    case "signed-out":
      return { ...initialQueryView<Answer>(), error: SIGN_IN_FIRST };
    default:
      return view;
  }
}

/** As queryView, except that reading again the query whose answer is shown keeps that answer on screen until the new
 *  one arrives: a page read again after a save does not empty, and so does not jump back to its top (8A, owner's
 *  screen check). Another query still clears it, as queryView does. */
export function queryViewKeeping<Answer>(
  view: QueryView<Answer>,
  update: QueryUpdate<Answer>,
  isShownQuery: (answer: Answer) => boolean,
): QueryView<Answer> {
  if (update.kind === "loading" && view.answer !== null && isShownQuery(view.answer)) return { ...view, loading: true, error: "" };
  return queryView(view, update);
}

/**
 * One answer's loading, kept out of the component (equipmentState.ts's createListController, for one answer
 * rather than rows). It holds the query itself, so every load - a reload after a session change or a save
 * included - asks for the query the controls show; and every load takes a ticket first, so an older answer is
 * never shown after a newer request. `refreshIf` reloads only while the query is still the one a save was made
 * under: a save that returns after the page moved to another asset changes nothing on it.
 */
export function createQueryController<Query, Answer>(deps: {
  initialQuery: Query;
  getToken: () => string | null;
  fetchAnswer: (token: string, query: Query) => Promise<Answer>;
  show: (update: QueryUpdate<Answer>) => void;
  failure: string;
}) {
  let query = deps.initialQuery;
  const latest = createLatestOnly();
  const same = (a: Query, b: Query) => JSON.stringify(a) === JSON.stringify(b);

  async function load(): Promise<void> {
    const ticket = latest.begin();
    const asked = query;
    const token = deps.getToken();
    if (!token) {
      deps.show({ kind: "signed-out" });
      return;
    }
    deps.show({ kind: "loading" });
    try {
      const answer = await deps.fetchAnswer(token, asked);
      if (latest.isLatest(ticket)) deps.show({ kind: "answer", answer });
    } catch (error) {
      if (latest.isLatest(ticket)) deps.show({ kind: "failed", message: error instanceof Error ? error.message : deps.failure });
    }
  }

  return {
    query: (): Query => query,
    setQuery: (next: Query): Promise<void> => {
      query = next;
      return load();
    },
    refresh: load,
    /** Show an answer already in hand - a write's response carries the record as it now stands - for the query
     *  now asked; a read still in flight is dropped, so it cannot replace it (8A-FB-007). */
    answered: (answer: Answer): void => {
      latest.begin();
      deps.show({ kind: "answer", answer });
    },
    isCurrent: (asked: Query): boolean => same(query, asked),
    refreshIf: (asked: Query): Promise<void> | null => (same(query, asked) ? load() : null),
  };
}

// --- Who may do what (a usability aid: the server decides) -------------------------------------------------

/** Adding and ending rules: ELIGIBILITY_RULE_MANAGE, Admin for now (owner, Q7). */
export function canManageRules(roleCodes: readonly string[]): boolean {
  return roleCodes.includes("ADMIN");
}

// --- Words -------------------------------------------------------------------------------------------------

/** A whole date as the screens show it: "12 March 2027". The API sends it as "2027-03-12". */
export function formatDay(iso: string | null | undefined): string {
  if (!iso || !isCompleteIsoDate(iso)) return iso ?? "-";
  const [year, month, day] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(Date.UTC(year, month - 1, day)));
}

/** Whole days from one date to another, both as the API sends them. */
export function daysBetween(fromIso: string, toIso: string): number {
  const [a, b] = [fromIso, toIso].map((iso) => {
    const [year, month, day] = iso.split("-").map(Number);
    return Date.UTC(year, month - 1, day);
  });
  return Math.round((b - a) / 86_400_000);
}

export const ANSWER_LABELS: Record<string, string> = {
  ELIGIBLE: "Can be allocated",
  WARNING: "Can be allocated, with a warning",
  BLOCKED: "Cannot be allocated",
  OVERRIDE_REQUIRED: "Needs approval",
};

const ANSWER_TONES: Record<string, StatusTone> = { ELIGIBLE: "success", WARNING: "warning", BLOCKED: "danger", OVERRIDE_REQUIRED: "warning" };

export function answerTone(code: string): StatusTone {
  return ANSWER_TONES[code] ?? "neutral";
}

const OUTCOME_TONES: Record<string, StatusTone> = {
  VALID: "success",
  RUNS_OUT_SOON: "warning",
  RUNS_OUT_IN_PERIOD: "warning",
  RUNS_OUT_BEFORE_START: "warning",
  RUN_OUT: "danger",
  MISSING: "danger",
  COPY_MISSING: "danger",
  NOT_APPLICABLE: "muted",
  RETIRED: "danger",
};

export function outcomeTone(code: string | null): StatusTone {
  return (code && OUTCOME_TONES[code]) || "neutral";
}

/** What a certificate's line says on a machine's page: "valid until 12 March 2027", "runs out in 12 days",
 *  "ran out on 3 September 2026", "missing", "copy missing" or "not applicable: <reason>". */
export function statusText(status: Pick<KindStatus, "outcome_code" | "cover_ends_on" | "mark" | "certificate">, today: string): string {
  const until = status.cover_ends_on;
  if (status.mark) {
    // A mark counted today; one ending within 15 days says so (independent review, round 3).
    const ends = status.mark.until_date ? ` (until ${formatDay(status.mark.until_date)})` : "";
    const soon = status.outcome_code === "RUNS_OUT_SOON" && until ? `; ends in ${Math.max(daysBetween(today, until), 0)} days` : "";
    return `not applicable${markReason(status.mark)}${ends}${soon}`;
  }
  switch (status.outcome_code) {
    case "VALID":
      return until ? `valid until ${formatDay(until)}` : "valid, with no end date";
    case "RUNS_OUT_SOON": {
      const days = until ? daysBetween(today, until) : 0;
      return days <= 0 ? "runs out today" : `runs out in ${days} day${days === 1 ? "" : "s"}`;
    }
    case "RUN_OUT":
      return `ran out on ${formatDay(until)}`;
    case "MISSING":
      return "missing";
    case "COPY_MISSING":
      return "copy missing";
    case "NOT_APPLICABLE":
      // A mark's line is written above; without its mark there is nothing more to say.
      return "not applicable";
    default:
      // Not required of this asset: recorded here for the machine it is fitted to.
      if (!status.certificate) return "no certificate in force";
      return until ? `recorded here; valid until ${formatDay(until)}` : "recorded here";
  }
}

/** What one result of a check says, in words. The answer as a whole is ANSWER_LABELS'. */
/** A mark's reason as a line shows it: ": <reason>", or a note that it is shown only to those who see numbers. */
export function markReason(mark: { reason: string | null }): string {
  return mark.reason ? `: ${mark.reason}` : " (reason shown to Admin only)";
}

export function resultText(result: Pick<CheckResult, "outcome_code" | "cover_ends_on" | "mark_public_id">): string {
  const day = formatDay(result.cover_ends_on);
  if (result.mark_public_id && result.outcome_code !== "NOT_APPLICABLE") {
    // A mark counted today that ends before or during the job (independent review, round 3, ELG1-R3-001).
    const when = result.outcome_code === "RUNS_OUT_BEFORE_START" ? "before the job starts" : result.outcome_code === "RUNS_OUT_IN_PERIOD" ? "during the period" : "within 15 days";
    return `not applicable until ${day}, ${when} - the certificate is needed after that`;
  }
  switch (result.outcome_code) {
    case "VALID":
      return result.cover_ends_on ? `valid until ${day}` : "valid, with no end date";
    case "RUNS_OUT_SOON":
      return `runs out on ${day}, within 15 days - renew it`;
    case "RUNS_OUT_IN_PERIOD":
      return `runs out on ${day}, during the period - renew it`;
    case "RUNS_OUT_BEFORE_START":
      return `runs out on ${day}, before the job starts - renew it`;
    case "RUN_OUT":
      return `ran out on ${day}`;
    case "MISSING":
      return "missing";
    case "COPY_MISSING":
      return "its copy is missing";
    case "NOT_APPLICABLE":
      return result.cover_ends_on ? `not applicable, until ${day}` : "not applicable";
    case "RETIRED":
      return "retired";
    default:
      return result.outcome_code;
  }
}

export const EFFECT_LABELS: Record<string, string> = { BLOCK: "Stops it", OVERRIDE: "Needs approval", WARNING: "Warning", NONE: "-" };

export const BAND_LABELS: Record<string, string> = {
  MISSING: "Missing",
  COPY_MISSING: "Copy missing",
  RUN_OUT: "Run out",
  WITHIN_15: "Within 15 days",
  WITHIN_30: "Within 30 days",
  WITHIN_60: "Within 60 days",
};
export const BAND_CODES = Object.keys(BAND_LABELS);

const BAND_TONES: Record<string, StatusTone> = {
  MISSING: "danger",
  COPY_MISSING: "danger",
  RUN_OUT: "danger",
  WITHIN_15: "warning",
  WITHIN_30: "warning",
  WITHIN_60: "info",
};

export function bandTone(code: string): StatusTone {
  return BAND_TONES[code] ?? "neutral";
}

export const REGISTERED_AS_LABELS: Record<string, string> = { TRANSPORT: "transport vehicle", NON_TRANSPORT: "non-transport vehicle" };

/** A certificate's own facts in one line: "No. X, by Y; 1 January 2026 to 31 December 2026; registered as ...". */
export function certificateText(certificate: Certificate): string {
  const number = certificate.number_withheld ? "number shown to Admin only" : `No. ${certificate.number}`;
  const dates = certificate.valid_until
    ? `${formatDay(certificate.valid_from)} to ${formatDay(certificate.valid_until)}`
    : `from ${formatDay(certificate.valid_from)}, no end date`;
  const extra = [
    certificate.registered_as_code ? `registered as a ${REGISTERED_AS_LABELS[certificate.registered_as_code] ?? certificate.registered_as_code}` : "",
    certificate.valid_in_label ? `valid in ${certificate.valid_in_code === "IN" ? "all India" : certificate.valid_in_label}` : "",
  ].filter(Boolean);
  return [`${number}, by ${certificate.issued_by}`, dates, ...extra].join("; ");
}

/** The certificates and marks a page shows outside its status rows: every one once. `live` - a certificate still
 *  recorded, a mark still in force - keeps its Withdraw; `history` holds what was withdrawn. */
export function otherRecords(view: Pick<AssetCertificates, "statuses" | "certificates" | "marks">): {
  liveCertificates: Certificate[];
  liveMarks: Mark[];
  historyCertificates: Certificate[];
  historyMarks: Mark[];
} {
  const inRows = new Set<string>();
  for (const status of view.statuses) {
    if (status.certificate) inRows.add(status.certificate.certificate_public_id);
    if (status.mark) inRows.add(status.mark.mark_public_id);
  }
  const certificates = view.certificates.filter((item) => !inRows.has(item.certificate_public_id));
  const marks = view.marks.filter((item) => !inRows.has(item.mark_public_id));
  return {
    liveCertificates: certificates.filter((item) => item.certificate_status_code === "RECORDED"),
    liveMarks: marks.filter((item) => item.mark_status_code === "IN_FORCE"),
    historyCertificates: certificates.filter((item) => item.certificate_status_code !== "RECORDED"),
    historyMarks: marks.filter((item) => item.mark_status_code !== "IN_FORCE"),
  };
}

/** Why a certificate still recorded is not in a status row: it starts later, a later one took over, or its kind
 *  is not required of this asset today. */
export function otherCertificateText(certificate: Pick<Certificate, "in_force" | "valid_from">, today: string): string {
  if (certificate.valid_from > today) return `takes over on ${formatDay(certificate.valid_from)}`;
  if (certificate.in_force) return "in force, not required of it today";
  return "replaced by a later one";
}

/** Why a mark still in force is not counted: it has ended, or the rule chosen here does not allow it. */
/** Why a mark still in force is not in a status row. `registrationStands`: the registration's row shows a
 *  registration in force, which wins over the mark (owner, 28 September 2026). */
export function otherMarkText(mark: Pick<Mark, "until_date" | "kind_code">, today: string, registrationStands = false): string {
  if (mark.until_date && mark.until_date < today) return `ended on ${formatDay(mark.until_date)}; withdraw it before marking again`;
  if (mark.kind_code === "REGISTRATION" && registrationStands) return "not counted while a registration is in force";
  return "not counted by the rule in force here";
}

/** How a piece of tackle or a hook block is matched to its certificate (ERT-2, Q5): its own number, or the
 *  platform's reference stencilled on it. */
export function pieceMarkText(asset: Pick<AssetSummary, "serial_number" | "asset_reference">): string {
  return asset.serial_number ? `its own number ${asset.serial_number}` : `stencil ${asset.asset_reference} on it`;
}

/** Whether the tackle or hook block needs its mark shown on the form. */
export function needsPieceMark(asset: Pick<AssetSummary, "origin_code" | "class_code">): boolean {
  return asset.origin_code === "PLATFORM" && (asset.class_code === "HOOK_BLOCK" || asset.class_code === "LIFTING_TACKLE");
}

export function ruleText(rule: Pick<RuleSummary, "renew_every_months" | "lapse_code" | "basis_code" | "not_applicable_code" | "not_applicable_max_months">): string {
  const parts = [
    rule.renew_every_months ? `every ${rule.renew_every_months} months` : "",
    rule.lapse_code === "BLOCK" ? "a lapse stops the machine" : rule.lapse_code === "OVERRIDE" ? "a lapse needs approval" : rule.lapse_code === "WARN" ? "a lapse warns" : "not required",
    rule.basis_code === "STATUTORY" ? "the law" : "PBL's own rule",
    rule.not_applicable_code === "ALLOWED"
      ? `may be marked not applicable${rule.not_applicable_max_months ? ` for at most ${rule.not_applicable_max_months} months` : ""}`
      : "",
  ];
  return parts.filter(Boolean).join("; ");
}

// --- Recording a certificate -------------------------------------------------------------------------------

export type CertificateForm = {
  kindCode: string;
  number: string;
  issuedBy: string;
  issuedOn: string;
  validFrom: string;
  validUntil: string;
  validIn: string;
  registeredAs: string;
};

export const EMPTY_CERTIFICATE_FORM: CertificateForm = {
  kindCode: "",
  number: "",
  issuedBy: "",
  issuedOn: "",
  validFrom: "",
  validUntil: "",
  validIn: "",
  registeredAs: "",
};

export function certificateFormProblem(form: CertificateForm, kind: CertificateKind | undefined, today: string): string | null {
  if (!kind) return "Choose the kind of certificate.";
  if (!form.number.trim()) return "Give the certificate's number, as printed.";
  if (!form.issuedBy.trim()) return "Give who issued it.";
  if (!isCompleteIsoDate(form.issuedOn)) return "Give the day it was issued.";
  if (form.issuedOn > today) return "The day it was issued cannot be in the future.";
  if (!isCompleteIsoDate(form.validFrom)) return "Give the day it is valid from.";
  if (form.validUntil) {
    if (!isCompleteIsoDate(form.validUntil)) return "Give the day it runs until as a whole date.";
    if (form.validUntil < form.validFrom) return "It cannot run out before it starts.";
  } else if (!kind.end_date_optional) {
    return `Give the day the ${kind.kind_label.toLowerCase()} runs until.`;
  }
  if (kind.valid_in_required && !form.validIn) return "Give where the permit is valid.";
  if (kind.states_registration && !form.registeredAs) return "Say whether it is registered as a transport or a non-transport vehicle.";
  return null;
}

export function certificatePayload(form: CertificateForm, kind: CertificateKind, requestKey: string): Record<string, unknown> {
  return {
    create_request_key: requestKey,
    kind_code: kind.kind_code,
    number: form.number.trim(),
    issued_by: form.issuedBy.trim(),
    issued_on: form.issuedOn,
    valid_from: form.validFrom,
    valid_until: form.validUntil || null,
    valid_in_code: kind.valid_in_required ? form.validIn : null,
    registered_as_code: kind.states_registration ? form.registeredAs : null,
  };
}

// --- "Not applicable" --------------------------------------------------------------------------------------

export type MarkForm = { kindCode: string; reason: string; until: string };

export const EMPTY_MARK_FORM: MarkForm = { kindCode: "", reason: "", until: "" };

export function markFormProblem(form: MarkForm, markable: MarkableKind | undefined, today: string): string | null {
  if (!markable) return "Choose a certificate the rules allow to be marked not applicable.";
  if (!form.reason.trim()) return "Give the reason it does not apply.";
  if (form.until && !isCompleteIsoDate(form.until)) return "Give the end as a whole date.";
  if (form.until && form.until < today) return "The day it stops applying cannot be in the past.";
  if (markable.latest_until) {
    if (!form.until) return `Give the day it stops applying, no later than ${formatDay(markable.latest_until)}.`;
    if (form.until > markable.latest_until) return `It may run for at most ${markable.rule.not_applicable_max_months} months: no later than ${formatDay(markable.latest_until)}.`;
  }
  return null;
}

export function markPayload(form: MarkForm, requestKey: string): Record<string, unknown> {
  return { create_request_key: requestKey, kind_code: form.kindCode, reason: form.reason.trim(), until: form.until || null };
}

// --- The check ------------------------------------------------------------------------------------------

export type CheckForm = { stateCode: string; central: boolean; from: string; to: string };

export function checkFormProblem(form: CheckForm): string | null {
  if (!form.stateCode) return "Choose the site's state or union territory.";
  if (!isCompleteIsoDate(form.from)) return "Give the day the job starts.";
  if (form.to && !isCompleteIsoDate(form.to)) return "Give the day it ends as a whole date, or leave it empty.";
  if (form.to && form.to < form.from) return "The period cannot end before it starts.";
  return null;
}

export function checkQuery(form: CheckForm): string {
  const params = new URLSearchParams({ state_code: form.stateCode, period_from: form.from, central_government_site: String(form.central) });
  if (form.to) params.set("period_to", form.to);
  return params.toString();
}

/** The states and union territories a site can be in: every jurisdiction but the central government's. */
export function siteStates(jurisdictions: Jurisdiction[]): Jurisdiction[] {
  return jurisdictions.filter((item) => item.jurisdiction_kind_code !== "CENTRAL");
}

// --- Certificates due ---------------------------------------------------------------------------------------

export type DueFilters = { band: string; classCode: string; kindCode: string; search: string };

export const INITIAL_DUE_FILTERS: DueFilters = { band: "", classCode: "", kindCode: "", search: "" };

export function dueQuery(filters: DueFilters, offset: number, pageSize: number): string {
  const params = new URLSearchParams({ limit: String(pageSize), offset: String(offset) });
  if (filters.band) params.set("band", filters.band);
  if (filters.classCode) params.set("class_code", filters.classCode);
  if (filters.kindCode) params.set("kind_code", filters.kindCode);
  if (filters.search.trim()) params.set("search", filters.search.trim());
  return params.toString();
}

/** What a due line says: "ran out on 3 September 2026", "runs out on 10 October 2026", "missing". */
export function dueText(item: Pick<DueItem, "band_code" | "cover_ends_on" | "mark_public_id">): string {
  if (item.band_code === "MISSING") return "missing";
  if (item.band_code === "COPY_MISSING") return "copy missing";
  if (item.band_code === "RUN_OUT") return `ran out on ${formatDay(item.cover_ends_on)}`;
  return item.mark_public_id ? `"not applicable" ends on ${formatDay(item.cover_ends_on)}` : `runs out on ${formatDay(item.cover_ends_on)}`;
}

// --- Rules ---------------------------------------------------------------------------------------------------

export type RuleForm = {
  kindCode: string;
  classCode: string;
  typeCode: string;
  appliesWhen: string;
  jurisdictionCode: string;
  effectiveFrom: string;
  renewEvery: string;
  basis: string;
  lapse: string;
  notApplicable: string;
  maxMonths: string;
  source: string;
  note: string;
};

export const EMPTY_RULE_FORM: RuleForm = {
  kindCode: "",
  classCode: "",
  typeCode: "",
  appliesWhen: "ALWAYS",
  jurisdictionCode: "",
  effectiveFrom: "",
  renewEvery: "",
  basis: "STATUTORY",
  lapse: "BLOCK",
  notApplicable: "NOT_ALLOWED",
  maxMonths: "",
  source: "",
  note: "",
};

/** The server's bounds (eligibility/contract.py): an examination's interval, and how long a mark may run. */
export const MAX_RENEW_EVERY_MONTHS = 240;
export const MAX_NOT_APPLICABLE_MONTHS = 120;

function wholeBetween(value: string, low: number, high: number): boolean {
  const text = value.trim();
  return /^\d{1,4}$/.test(text) && Number(text) >= low && Number(text) <= high;
}

/** The central government's sites, as a rule's "where". Only the examinations have rules of their own there; road
 *  papers follow the site's state (evaluation.py, rule_jurisdiction). */
export const CENTRAL_SITES = "IN";

/** Where a rule for this certificate may apply: all of India and every state, and the central government's sites
 *  only for an examination (independent review, round 5, ELG1-R5-003). */
export function ruleJurisdictionChoices(jurisdictions: Jurisdiction[], kind: CertificateKind | undefined): Jurisdiction[] {
  return kind?.is_examination ? jurisdictions : siteStates(jurisdictions);
}

/** A rule form once its certificate changes: nothing kept that the new certificate cannot have - an interval on a
 *  kind that states its own end, "transport vehicles only" on the registration, which decides it, or the central
 *  government's sites for a road paper (independent review, round 5). */
export function fitRuleToKind(form: RuleForm, kind: CertificateKind | undefined): RuleForm {
  return {
    ...form,
    renewEvery: kind?.is_examination ? form.renewEvery : "",
    appliesWhen: kind?.states_registration ? "ALWAYS" : form.appliesWhen,
    jurisdictionCode: form.jurisdictionCode === CENTRAL_SITES && !kind?.is_examination ? "" : form.jurisdictionCode,
  };
}

export function ruleFormProblem(form: RuleForm, kind: CertificateKind | undefined): string | null {
  if (!kind) return "Choose the certificate the rule requires.";
  if (!form.classCode) return "Choose the kind of machine, part or kit.";
  if (!isCompleteIsoDate(form.effectiveFrom)) return "Give the day the rule takes effect.";
  if (form.basis === "STATUTORY" && !["BLOCK", "NOT_REQUIRED"].includes(form.lapse)) {
    return "The law always stops the machine when it lapses: a statutory rule blocks, or says it is not required.";
  }
  if (form.renewEvery && !wholeBetween(form.renewEvery, 1, MAX_RENEW_EVERY_MONTHS)) return `Give how often in whole months, 1 to ${MAX_RENEW_EVERY_MONTHS}.`;
  if (form.renewEvery && !kind.is_examination) return `A ${kind.kind_label.toLowerCase()} states its own end, so the rule sets no interval.`;
  if (kind.is_examination && form.lapse !== "NOT_REQUIRED" && !form.renewEvery) return `Give how often the ${kind.kind_label.toLowerCase()} must be renewed, in months.`;
  if (form.appliesWhen === "TRANSPORT_ONLY" && kind.states_registration) return "The registration decides whether a machine is a transport vehicle, so its rule applies always.";
  if (form.jurisdictionCode === CENTRAL_SITES && !kind.is_examination) {
    return `At central government sites only the examinations have rules of their own; a ${kind.kind_label.toLowerCase()} follows the site's state.`;
  }
  if (form.lapse === "NOT_REQUIRED" && form.notApplicable === "ALLOWED") return "Nothing is required, so there is nothing to mark not applicable.";
  if (form.maxMonths && form.notApplicable !== "ALLOWED") return "A limit on how long a mark runs needs 'not applicable' to be allowed.";
  if (form.maxMonths && !wholeBetween(form.maxMonths, 1, MAX_NOT_APPLICABLE_MONTHS)) return `Give the limit in whole months, 1 to ${MAX_NOT_APPLICABLE_MONTHS}.`;
  if (!form.source.trim()) return "Give the rule's source: the Act, rule, form and notification, or PBL's decision and its date.";
  return null;
}

export function rulePayload(form: RuleForm, requestKey: string): Record<string, unknown> {
  return {
    create_request_key: requestKey,
    kind_code: form.kindCode,
    class_code: form.classCode,
    type_code: form.typeCode || null,
    applies_when_code: form.appliesWhen,
    jurisdiction_code: form.jurisdictionCode || null,
    effective_from: form.effectiveFrom,
    renew_every_months: form.renewEvery ? Number(form.renewEvery) : null,
    basis_code: form.basis,
    lapse_code: form.lapse,
    not_applicable_code: form.notApplicable,
    not_applicable_max_months: form.maxMonths ? Number(form.maxMonths) : null,
    source: form.source.trim(),
    note: form.note.trim() || null,
  };
}

export const RULE_STATE_LABELS: Record<string, string> = { IN_EFFECT: "In effect", NOT_YET: "Not yet in effect", ENDED: "Ended" };
