// Slice 7D Part 2, item 1: what the Work Order detail page shows, decided in one pure reducer so the
// ordering rules can be tested without a browser - the frontend has no component-test capability yet.
//
// The defect this closes (Part 1 review round 5): the page loaded its parts with no single page-load
// generation. The Work Order and lines requests had no check at all, and a finished save restarted the
// line-detail or billing-terms load gate, so going to another Work Order while one was loading could
// show the first one's parts under the second, and pressing Refresh while a save was in flight could
// leave the forms read-only until the next reload.
//
// The rule here: every load of the page takes a new generation, every result carries the generation it
// started in, and a result from any other generation is ignored. Applying a save NEVER starts a new
// generation - that was the bug - so a save cannot cut off a newer load, and a save started before a
// newer load is discarded rather than applied over it.

import type { WorkOrderLineDetail } from "./WorkOrderLineDetailsSection";
import type { LineBillingTerms } from "./workOrderBillingTermsState";
import type { ContractPeriod } from "./workOrderContractPeriodState";
import type { HolidayList } from "./workOrderHolidaysState";
import { EMPTY_LOADED_LIST, type LoadedList, listLoadFailed, listLoaded, listWhileLoading, upsertLineDetail } from "./workOrderLineDetailState";

export type WorkOrder = {
  public_id: string;
  work_order_code: string;
  work_order_title?: string | null;
  work_order_status_code: string;
  commercial_offer_public_id: string;
  commercial_offer_code?: string | null;
  commercial_offer_version_number?: number | null;
  opportunity_public_id: string;
  account_public_id?: string | null;
  customer_wo_reference?: string | null;
  received_date?: string | null;
  source_offer_status_code: string;
  remarks?: string | null;
  created_by?: string | null;
  created_by_display_name?: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkOrderLine = {
  public_id: string;
  work_order_public_id: string;
  source_offer_line_public_id?: string | null;
  source_offer_line_number?: number | null;
  line_number: number;
  line_status_code: string;
  scope_description: string;
  equipment_service_category?: string | null;
  quantity: string | number;
  uom: string;
  rate_amount?: string | number | null;
  currency_code: string;
  line_amount?: string | number | null;
  remarks?: string | null;
  created_at: string;
  updated_at: string;
};

export type BusinessEventSummary = {
  public_id: string;
  event_name: string;
  source_module: string;
  record_type: string | null;
  record_public_id: string | null;
  user_public_id: string | null;
  event_timestamp: string;
  status_before: string | null;
  status_after: string | null;
  reason: string | null;
  remarks: string | null;
  correlation_id: string | null;
  event_payload: Record<string, unknown> | null;
};

export type RelatedOfferSummary = {
  public_id: string;
  offer_code: string;
  offer_purpose: string;
  offer_status_code: string;
  base_offer_public_id?: string | null;
  base_offer_code?: string | null;
  customer_request_summary?: string | null;
  created_at: string;
};

export type WorkOrderAmendmentSummary = {
  public_id: string;
  work_order_public_id: string;
  work_order_code: string;
  amendment_sequence_no: number;
  amendment_type_code: string;
  amendment_status_code: string;
  customer_amendment_reference?: string | null;
  customer_amendment_date?: string | null;
  received_date: string;
  effective_date?: string | null;
  amendment_reason: string;
  related_commercial_offer_public_id?: string | null;
  related_commercial_offer_code?: string | null;
  related_commercial_offer_purpose?: string | null;
  related_commercial_offer_status_code?: string | null;
  created_at: string;
};

/** A side list that only shows: its entries, whether it is loading, and its own error. */
export type SideList<T> = { entries: T[]; loading: boolean; error: string };

const EMPTY_SIDE_LIST: SideList<never> = { entries: [], loading: false, error: "" };

/** What a list request has reported. The same three shapes for every list on the page. */
export type ListResult<T> = { status: "loading" } | { status: "loaded"; entries: T[] } | { status: "failed"; error: string };

export type WorkOrderPageState = {
  /** The newest page load. A result from any other generation is ignored. */
  generation: number;
  /** The Work Order that generation is loading, so a result cannot be applied to another one. */
  workOrderPublicId: string | null;
  workOrder: WorkOrder | null;
  lines: WorkOrderLine[];
  lineDetails: LoadedList<WorkOrderLineDetail>;
  lineDetailsError: string;
  billingTerms: LoadedList<LineBillingTerms>;
  billingTermsError: string;
  /** Slice 7D Part 3. One record rather than a list, so it is held directly with its own load flag. */
  contractPeriod: ContractPeriod | null;
  contractPeriodLoaded: boolean;
  contractPeriodError: string;
  /** Slice 7D Part 4. The Work Order's holiday list: one record, held like the contract period. */
  holidays: HolidayList | null;
  holidaysLoaded: boolean;
  holidaysError: string;
  relatedOffers: SideList<RelatedOfferSummary>;
  amendments: SideList<WorkOrderAmendmentSummary>;
  handoffEvents: SideList<BusinessEventSummary>;
  loading: boolean;
  error: string;
};

export const INITIAL_WORK_ORDER_PAGE_STATE: WorkOrderPageState = {
  generation: 0,
  workOrderPublicId: null,
  workOrder: null,
  lines: [],
  lineDetails: EMPTY_LOADED_LIST,
  lineDetailsError: "",
  billingTerms: EMPTY_LOADED_LIST,
  billingTermsError: "",
  contractPeriod: null,
  contractPeriodLoaded: false,
  contractPeriodError: "",
  holidays: null,
  holidaysLoaded: false,
  holidaysError: "",
  relatedOffers: EMPTY_SIDE_LIST,
  amendments: EMPTY_SIDE_LIST,
  handoffEvents: EMPTY_SIDE_LIST,
  loading: false,
  error: "",
};

export type WorkOrderPageAction =
  /** A new load begins: it takes the next generation and clears everything the old one showed. */
  | { type: "load-started"; generation: number; workOrderPublicId: string }
  /** The Work Order itself could not be loaded. */
  | { type: "load-failed"; generation: number; error: string }
  | { type: "work-order-loaded"; generation: number; workOrder: WorkOrder }
  /** The lines could not be loaded, so the Work Order shows without them. */
  | { type: "lines-failed"; generation: number; error: string }
  | { type: "lines-loaded"; generation: number; lines: WorkOrderLine[] }
  /** The Work Order and its lines are in; the page is no longer busy. */
  | { type: "load-finished"; generation: number }
  | { type: "line-details"; generation: number; result: ListResult<WorkOrderLineDetail> }
  | { type: "billing-terms"; generation: number; result: ListResult<LineBillingTerms> }
  /** A save answered. It is applied only while its own generation is still current. */
  | { type: "line-detail-saved"; generation: number; detail: WorkOrderLineDetail }
  | { type: "billing-terms-applied"; generation: number; entry: LineBillingTerms }
  /** Copying terms between lines changes several lines at once, so the whole list is replaced. */
  | { type: "billing-terms-replaced"; generation: number; entries: LineBillingTerms[] }
  | { type: "contract-period"; generation: number; result: ListResult<ContractPeriod> }
  /** A contract-period save answered. Applied only while its own generation is still current. */
  | { type: "contract-period-applied"; generation: number; period: ContractPeriod }
  | { type: "holidays"; generation: number; result: ListResult<HolidayList> }
  /** A holiday-list save answered. Applied only while its own generation is still current. */
  | { type: "holidays-applied"; generation: number; holidays: HolidayList }
  | { type: "related-offers"; generation: number; result: ListResult<RelatedOfferSummary> }
  | { type: "amendments"; generation: number; result: ListResult<WorkOrderAmendmentSummary> }
  | { type: "handoff-events"; generation: number; result: ListResult<BusinessEventSummary> };

function sideList<T>(result: ListResult<T>): SideList<T> {
  if (result.status === "loading") return { entries: [], loading: true, error: "" };
  if (result.status === "failed") return { entries: [], loading: false, error: result.error };
  return { entries: result.entries, loading: false, error: "" };
}

function loadedList<T>(
  current: LoadedList<T>,
  workOrderPublicId: string | null,
  result: ListResult<T>,
): { list: LoadedList<T>; error: string } {
  if (result.status === "loading") return { list: listWhileLoading(current), error: "" };
  // A failed load drops its entries rather than leaving them on screen as if current, so no form is
  // editable from a load known to have failed (Part 1 review round 3).
  if (result.status === "failed") return { list: listLoadFailed(), error: result.error };
  return { list: listLoaded(workOrderPublicId ?? "", result.entries), error: "" };
}

export function workOrderPageReducer(state: WorkOrderPageState, action: WorkOrderPageAction): WorkOrderPageState {
  if (action.type === "load-started") {
    // Nothing from an earlier load stays on screen: the lines, the line details and the billing terms
    // are cleared, so no form is editable and nothing from another Work Order shows beneath this one.
    return {
      ...INITIAL_WORK_ORDER_PAGE_STATE,
      generation: action.generation,
      workOrderPublicId: action.workOrderPublicId,
      loading: true,
    };
  }
  // Everything else belongs to one load. A result from an older (or unknown) generation is ignored.
  if (action.generation !== state.generation) return state;

  switch (action.type) {
    case "load-failed":
      return { ...state, workOrder: null, lines: [], loading: false, error: action.error };
    case "work-order-loaded":
      return { ...state, workOrder: action.workOrder };
    case "lines-failed":
      return { ...state, lines: [], loading: false, error: action.error };
    case "lines-loaded":
      return { ...state, lines: action.lines };
    case "load-finished":
      return { ...state, loading: false };
    case "line-details": {
      const { list, error } = loadedList(state.lineDetails, state.workOrderPublicId, action.result);
      return { ...state, lineDetails: list, lineDetailsError: error };
    }
    case "billing-terms": {
      const { list, error } = loadedList(state.billingTerms, state.workOrderPublicId, action.result);
      return { ...state, billingTerms: list, billingTermsError: error };
    }
    case "line-detail-saved":
      // The save's own result replaces that line's entry. The generation is untouched, so the load
      // this generation already made stays valid.
      return { ...state, lineDetails: { ...state.lineDetails, entries: upsertLineDetail(state.lineDetails.entries, action.detail) } };
    case "billing-terms-applied":
      return { ...state, billingTerms: { ...state.billingTerms, entries: upsertLineDetail(state.billingTerms.entries, action.entry) } };
    case "billing-terms-replaced":
      // The write returned every line's terms, so they replace the list wholesale rather than one
      // entry at a time. The generation is untouched, as for every other save.
      return { ...state, billingTerms: { ...state.billingTerms, entries: action.entries } };
    case "contract-period": {
      if (action.result.status === "loading") return { ...state, contractPeriodLoaded: false, contractPeriodError: "" };
      if (action.result.status === "failed") {
        // A failed load drops the record rather than leaving it on screen as if current, so no form
        // is editable from a load known to have failed (the Part 1 review round-3 rule).
        return { ...state, contractPeriod: null, contractPeriodLoaded: false, contractPeriodError: action.result.error };
      }
      return { ...state, contractPeriod: action.result.entries[0] ?? null, contractPeriodLoaded: true, contractPeriodError: "" };
    }
    case "contract-period-applied":
      return { ...state, contractPeriod: action.period };
    case "holidays": {
      if (action.result.status === "loading") return { ...state, holidaysLoaded: false, holidaysError: "" };
      if (action.result.status === "failed") {
        // Dropped rather than left on screen as if current, as the contract period is.
        return { ...state, holidays: null, holidaysLoaded: false, holidaysError: action.result.error };
      }
      return { ...state, holidays: action.result.entries[0] ?? null, holidaysLoaded: true, holidaysError: "" };
    }
    case "holidays-applied":
      return { ...state, holidays: action.holidays };
    case "related-offers":
      return { ...state, relatedOffers: sideList(action.result) };
    case "amendments":
      return { ...state, amendments: sideList(action.result) };
    case "handoff-events":
      return { ...state, handoffEvents: sideList(action.result) };
    default:
      return state;
  }
}
