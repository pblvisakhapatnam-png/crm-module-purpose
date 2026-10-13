// The requirement page's state as one reducer (WRR-001), so what each event does to it can be tested
// without a browser DOM - the frontend has no component tests yet.
//
// Three rules matter most, each found by independent review:
//
// - A freshly loaded requirement replaces every draft made against the one it replaces - the change form,
//   the Work Order facts for a date being tried, the cancellation reason and its half-given confirmation,
//   and their messages. A draft kept across a reload would be sent with the new version number and
//   silently undo whatever the other person changed (rounds 1 and 2, F-01 and F-09).
// - Only the latest load may install a requirement. Loads are numbered; an older answer arriving last is
//   ignored, and a save or cancellation - which installs a newer version itself - makes every load still in
//   flight stale (round 3, F-13).
// - A change may be saved only once the Work Order's facts for the date on the form are in: while they
//   are being read, or after reading them failed, the facts shown are another date's (rounds 2 and 3,
//   F-07 and F-12).

import {
  DATE_FACTS_CURRENT,
  type DateFacts,
  type LineFacts,
  type RequirementForm,
  type ResourceRequirement,
  dateFactsAnswered,
  dateFactsAsked,
  formFromRequirement,
} from "./resourceRequirementState";

export type Feedback = { kind: "success" | "error"; text: string } | null;

export type DetailState = {
  requirement: ResourceRequirement | null;
  // The load whose answer may install a requirement; null when none is awaited.
  latestLoad: number | null;
  loadError: string;
  // The change form, while a change is being made.
  form: RequirementForm | null;
  // The Work Order line's facts on the date the form now says, when that differs from the saved one.
  editLine: LineFacts | null;
  // Whether those facts are in for the date on the form.
  dateFacts: DateFacts;
  saveFeedback: Feedback;
  reason: string;
  confirmingCancel: boolean;
  cancelFeedback: Feedback;
};

export const INITIAL_DETAIL_STATE: DetailState = {
  requirement: null,
  latestLoad: null,
  loadError: "",
  form: null,
  editLine: null,
  dateFacts: DATE_FACTS_CURRENT,
  saveFeedback: null,
  reason: "",
  confirmingCancel: false,
  cancelFeedback: null,
};

export type DetailAction =
  | { type: "load-started"; ticket: number }
  | { type: "loaded"; ticket: number; requirement: ResourceRequirement }
  | { type: "load-failed"; ticket: number; text: string }
  | { type: "change-started" }
  | { type: "form-changed"; form: RequirementForm }
  | { type: "edit-date-changed"; ticket: number; date: string }
  | { type: "edit-line-loaded"; ticket: number; line: LineFacts }
  | { type: "edit-line-failed"; ticket: number }
  | { type: "change-discarded" }
  | { type: "change-saved"; requirement: ResourceRequirement; recorded: boolean }
  | { type: "change-refused"; text: string }
  | { type: "reason-changed"; reason: string }
  | { type: "cancel-asked" }
  | { type: "cancel-withdrawn" }
  | { type: "cancelled"; requirement: ResourceRequirement }
  | { type: "cancel-refused"; text: string };

export const MISSING_REASON = "Give the reason the requirement is being cancelled.";

// What a newly installed requirement starts with: nothing half done against the one before it, and no
// load awaited - any still in flight was asked before this version existed.
function installed(requirement: ResourceRequirement): DetailState {
  return { ...INITIAL_DETAIL_STATE, requirement };
}

export function detailReducer(state: DetailState, action: DetailAction): DetailState {
  switch (action.type) {
    case "load-started":
      return { ...state, latestLoad: action.ticket, loadError: "" };
    case "loaded":
      // Only the load awaited may install; its drafts start again.
      return action.ticket === state.latestLoad ? installed(action.requirement) : state;
    case "load-failed":
      return action.ticket === state.latestLoad ? { ...state, latestLoad: null, loadError: action.text } : state;
    case "change-started":
      return state.requirement
        ? { ...state, form: formFromRequirement(state.requirement), editLine: null, dateFacts: DATE_FACTS_CURRENT, saveFeedback: null }
        : state;
    case "form-changed":
      // The user's own edit clears a stale message.
      return state.form ? { ...state, form: action.form, saveFeedback: null } : state;
    case "edit-date-changed":
      // A new read - a new date, or trying the same one again - starts without an earlier message.
      return state.form ? { ...state, dateFacts: dateFactsAsked(action.ticket, action.date), saveFeedback: null } : state;
    case "edit-line-loaded":
      if (!state.form || action.ticket !== state.dateFacts.ticket || state.dateFacts.status !== "loading") return state;
      return { ...state, editLine: action.line, dateFacts: dateFactsAnswered(state.dateFacts, action.ticket, true) };
    case "edit-line-failed":
      return state.form ? { ...state, dateFacts: dateFactsAnswered(state.dateFacts, action.ticket, false) } : state;
    case "change-discarded":
      return { ...state, form: null, editLine: null, dateFacts: DATE_FACTS_CURRENT, saveFeedback: null };
    case "change-saved":
      // The saved version is newer than any load still in flight, so none of them may install it back.
      return {
        ...installed(action.requirement),
        saveFeedback: { kind: "success", text: action.recorded ? "Changes saved." : "Nothing changed, so nothing was saved." },
      };
    case "change-refused":
      return { ...state, saveFeedback: { kind: "error", text: action.text } };
    case "reason-changed":
      // A reason changed after confirming must be confirmed again.
      return { ...state, reason: action.reason, confirmingCancel: false, cancelFeedback: null };
    case "cancel-asked":
      return state.reason.trim()
        ? { ...state, confirmingCancel: true, cancelFeedback: null }
        : { ...state, cancelFeedback: { kind: "error", text: MISSING_REASON } };
    case "cancel-withdrawn":
      return { ...state, confirmingCancel: false };
    case "cancelled":
      return { ...installed(action.requirement), cancelFeedback: { kind: "success", text: "Requirement cancelled." } };
    case "cancel-refused":
      return { ...state, confirmingCancel: false, cancelFeedback: { kind: "error", text: action.text } };
    default:
      return state;
  }
}
