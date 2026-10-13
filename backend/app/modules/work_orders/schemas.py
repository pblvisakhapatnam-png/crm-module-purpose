from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, create_model

from app.modules.work_orders.contract import WORK_ORDER_LINE_UPKEEP_CELLS


class WorkOrderHandoffLineQuantity(BaseModel):
    """How much of one selected offer line's quantity the Work Order takes, when the customer awarded it in parts
    (CS-04 part 1). A selected line not named here takes all of its quantity not yet on a Work Order."""

    offer_line_public_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class WorkOrderCreateFromCommercialOffer(BaseModel):
    commercial_offer_public_id: UUID
    selected_offer_line_public_ids: list[UUID] | None = None
    selected_offer_line_quantities: list[WorkOrderHandoffLineQuantity] | None = None
    customer_wo_reference: str | None = Field(default=None, max_length=255)
    received_date: date | None = None
    remarks: str | None = Field(default=None, max_length=4000)


class WorkOrderResponse(BaseModel):
    public_id: UUID
    work_order_code: str
    work_order_title: str | None = None
    work_order_status_code: str
    commercial_offer_public_id: UUID
    commercial_offer_code: str | None = None
    # The source offer's version (Slice 9F: versions share offer_code). Part of the handoff output since the frozen
    # contract's amendment of 12 October 2026 (CS-04 part 2, item d).
    commercial_offer_version_number: int | None = None
    opportunity_public_id: UUID
    account_public_id: UUID | None = None
    customer_wo_reference: str | None = None
    received_date: date | None = None
    source_offer_status_code: str
    remarks: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class WorkOrderReadResponse(WorkOrderResponse):
    """WorkOrderResponse plus read-only display fields, for the list and detail routes only.

    The Accepted Offer -> Work Order shell handoff returns WorkOrderResponse, and that output is
    frozen (docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md). Display-only
    additions therefore live on this subclass, never on the model the handoff returns. Pydantic
    serializes a field by its declared type, so a WorkOrderReadResponse placed in the handoff's
    WorkOrderResponse field is emitted without these extra fields (UI cleanup package,
    September 2026).
    """

    # Resolved from app_user.display_name; None when created_by is null or matches no user.
    created_by_display_name: str | None = None


class WorkOrderLineResponse(BaseModel):
    public_id: UUID
    work_order_public_id: UUID
    source_offer_line_public_id: UUID | None = None
    # The source Commercial Offer line's own number, so a screen can say "offer line 2" instead of
    # showing only a UUID. Read-only and additive; null when the source line no longer resolves.
    source_offer_line_number: int | None = None
    line_number: int
    line_status_code: str
    scope_description: str
    equipment_service_category: str | None = None
    quantity: Decimal
    uom: str
    rate_amount: Decimal | None = None
    currency_code: str
    line_amount: Decimal | None = None
    remarks: str | None = None
    created_at: datetime
    updated_at: datetime


class WorkOrderLineReference(BaseModel):
    """One line and the Work Order it belongs to, for another module that holds only the line's public id
    (WRR-001). Never returned by a Work Order route.

    Only what that consumer uses: the identity and traceability it copies once, the Work Order's status
    for the Closed check, and the line's category text for suggesting an equipment class. Everything else
    about the line it reads through `list_work_order_lines`. `work_order_line_id` is the line's internal
    id, given out for one purpose: a foreign key that guarantees the line exists. It is never shown or
    sent anywhere."""

    work_order_line_id: int
    work_order_line_public_id: UUID
    line_number: int
    equipment_service_category: str | None = None
    source_offer_line_public_id: UUID | None = None
    work_order_public_id: UUID
    work_order_code: str
    work_order_status_code: str
    account_public_id: UUID | None = None


class WorkOrderCreatedResponse(BaseModel):
    work_order: WorkOrderResponse
    lines: list[WorkOrderLineResponse]
    events: list[dict[str, Any]]


class WorkOrderRelatedOfferSummary(BaseModel):
    """Slice 6O.1 read-only summary of a Supplementary Offer / Change Quotation linked to
    this Work Order. This is traceability only; it does not imply the Work Order has been
    amended, released, posted or otherwise changed by the related offer."""

    public_id: UUID
    offer_code: str
    offer_purpose: str
    offer_status_code: str
    base_offer_public_id: UUID | None = None
    base_offer_code: str | None = None
    customer_request_summary: str | None = None
    created_at: datetime


# Slice 6O.2 Work Order Amendment intake foundation. These records are intake/review
# only - see contract.py module docstring note. Nothing here is ever applied to
# WorkOrderResponse / WorkOrderLineResponse above.


class WorkOrderAmendmentCreate(BaseModel):
    amendment_type_code: str = Field(max_length=50)
    customer_amendment_reference: str | None = Field(default=None, max_length=255)
    customer_amendment_date: date | None = None
    received_date: date
    effective_date: date | None = None
    amendment_reason: str = Field(max_length=2000)
    administrative_change_summary: str | None = Field(default=None, max_length=2000)
    commercial_change_summary: str | None = Field(default=None, max_length=2000)
    related_commercial_offer_public_id: UUID | None = None
    customer_document_reference: str | None = Field(default=None, max_length=255)
    remarks: str | None = Field(default=None, max_length=4000)


class WorkOrderAmendmentUpdate(BaseModel):
    """Header edit while status is RECEIVED or UNDER_REVIEW only. amendment_type_code and
    amendment_status_code are deliberately absent: type reclassification and status
    transitions are not available through generic edit (use the dedicated decision
    action for status)."""

    customer_amendment_reference: str | None = Field(default=None, max_length=255)
    customer_amendment_date: date | None = None
    received_date: date | None = None
    effective_date: date | None = None
    amendment_reason: str | None = Field(default=None, max_length=2000)
    administrative_change_summary: str | None = Field(default=None, max_length=2000)
    commercial_change_summary: str | None = Field(default=None, max_length=2000)
    related_commercial_offer_public_id: UUID | None = None
    customer_document_reference: str | None = Field(default=None, max_length=255)
    remarks: str | None = Field(default=None, max_length=4000)


class WorkOrderAmendmentDecision(BaseModel):
    target_status_code: str = Field(max_length=50)
    notes: str | None = Field(default=None, max_length=2000)
    reason: str | None = Field(default=None, max_length=2000)


class WorkOrderAmendmentResponse(BaseModel):
    public_id: UUID
    work_order_public_id: UUID
    work_order_code: str
    amendment_sequence_no: int
    amendment_type_code: str
    amendment_status_code: str
    customer_amendment_reference: str | None = None
    customer_amendment_date: date | None = None
    received_date: date
    effective_date: date | None = None
    amendment_reason: str
    administrative_change_summary: str | None = None
    commercial_change_summary: str | None = None
    related_commercial_offer_public_id: UUID | None = None
    related_commercial_offer_code: str | None = None
    related_commercial_offer_purpose: str | None = None
    related_commercial_offer_status_code: str | None = None
    customer_document_reference: str | None = None
    decision_notes: str | None = None
    reviewed_at: datetime | None = None
    validated_at: datetime | None = None
    rejected_at: datetime | None = None
    cancelled_at: datetime | None = None
    decided_by: UUID | None = None
    remarks: str | None = None
    created_by: UUID | None = None
    # Read-only, resolved from app_user.display_name; None when created_by is null or matches no
    # user (UI cleanup package, September 2026).
    created_by_display_name: str | None = None
    created_at: datetime
    updated_at: datetime


class WorkOrderAmendmentActionResponse(BaseModel):
    amendment: WorkOrderAmendmentResponse
    event: dict[str, Any]


class WorkOrderAmendmentLineCreate(BaseModel):
    action_code: str = Field(max_length=20)
    source_work_order_line_public_id: UUID | None = None
    change_summary: str | None = Field(default=None, max_length=2000)
    proposed_scope_description: str | None = Field(default=None, max_length=1000)
    proposed_equipment_service_category: str | None = Field(default=None, max_length=255)
    proposed_quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    proposed_uom: str | None = Field(default=None, max_length=50)
    proposed_rate_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    proposed_currency_code: str | None = Field(default=None, min_length=3, max_length=3)


class WorkOrderAmendmentLineUpdate(BaseModel):
    """action_code and source_work_order_line_public_id are immutable after creation;
    delete and recreate the line if the wrong action/source was chosen."""

    change_summary: str | None = Field(default=None, max_length=2000)
    proposed_scope_description: str | None = Field(default=None, max_length=1000)
    proposed_equipment_service_category: str | None = Field(default=None, max_length=255)
    proposed_quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    proposed_uom: str | None = Field(default=None, max_length=50)
    proposed_rate_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    proposed_currency_code: str | None = Field(default=None, min_length=3, max_length=3)


class WorkOrderAmendmentLineResponse(BaseModel):
    public_id: UUID
    amendment_public_id: UUID
    line_number: int
    action_code: str
    source_work_order_line_public_id: UUID | None = None
    change_summary: str | None = None
    proposed_scope_description: str | None = None
    proposed_equipment_service_category: str | None = None
    proposed_quantity: Decimal | None = None
    proposed_uom: str | None = None
    proposed_rate_amount: Decimal | None = None
    proposed_currency_code: str | None = None
    proposed_amount: Decimal | None = None
    original_scope_description: str | None = None
    original_equipment_service_category: str | None = None
    original_quantity: Decimal | None = None
    original_uom: str | None = None
    original_rate_amount: Decimal | None = None
    original_currency_code: str | None = None
    original_amount: Decimal | None = None
    original_source_offer_line_public_id: UUID | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class WorkOrderAmendmentLineActionResponse(BaseModel):
    amendment_line: WorkOrderAmendmentLineResponse
    event: dict[str, Any]


class WorkOrderAmendmentReadinessResponse(BaseModel):
    """Read-only derived view. Nothing here is persisted; every mutation endpoint still
    validates its own preconditions independently rather than trusting this snapshot."""

    amendment_public_id: UUID
    amendment_type_code: str
    amendment_status_code: str
    is_editable: bool
    has_required_header_info: bool
    commercial_basis_required: bool
    related_offer_linked: bool
    related_offer_accepted: bool
    has_required_change_detail: bool
    can_move_to_under_review: bool
    can_move_to_validated: bool
    blocking_reasons: list[str]
    advisory_message: str
    applied_to_work_order: bool = False


# Slice 7C Work Order line operational detail. Deliberately separate models: nothing here is added
# to WorkOrderLineResponse, which the frozen Accepted Offer -> Work Order handoff returns.


class WorkOrderLineDetailUpdate(BaseModel):
    """Whole replacement of one line's detail. `expected_detail_version` is the version the caller
    last read: null when no detail has been recorded yet. A mismatch is refused with 409, so two
    people editing the same line cannot silently overwrite each other.

    The billing basis and contracted hours moved to the line's billing terms in Slice 7D. Unknown
    fields are refused rather than ignored, so a caller still sending them learns they were not
    saved here."""

    model_config = ConfigDict(extra="forbid")

    expected_detail_version: int | None = Field(default=None, ge=1)
    site_address_public_id: UUID | None = None
    billing_gstin_public_id: UUID | None = None
    billing_address_public_id: UUID | None = None
    customer_line_reference: str | None = Field(default=None, max_length=255)
    operational_notes: str | None = Field(default=None, max_length=4000)
    # Slice 7D Part 3: the line's own dates inside the Work Order's contract period. Both blank means
    # the line follows the Work Order (owner decision 13).
    line_start_date: date | None = None
    line_end_date: date | None = None
    # 8A core: whether the line's site is a central-government site - a central public sector plant, a
    # railway or metro, a major port, an oil field or a mine (ELG-1 Q8). Null is not answered. Omitted, it
    # keeps what is recorded, as the line's dates do.
    site_central_government: bool | None = None


class WorkOrderLineDetailAddress(BaseModel):
    public_id: UUID
    address_type_code: str
    address_line1: str
    city: str
    state: str
    postal_code: str | None = None


class WorkOrderLineDetailGstin(BaseModel):
    public_id: UUID
    gstin: str
    state_code: str
    verification_state_code: str


class WorkOrderLineDetailResponse(BaseModel):
    """One Work Order line's operational detail, resolved for display.

    A reference whose Account record is no longer active is returned as its bare public id with the
    resolved object null, and listed in `missing_items` - the line still shows what was picked,
    without presenting it as usable."""

    work_order_line_public_id: UUID
    line_number: int
    source_offer_line_public_id: UUID | None = None
    detail_public_id: UUID | None = None
    detail_version: int | None = None
    site_address_public_id: UUID | None = None
    site_address: WorkOrderLineDetailAddress | None = None
    billing_gstin_public_id: UUID | None = None
    billing_gstin: WorkOrderLineDetailGstin | None = None
    billing_address_public_id: UUID | None = None
    billing_address: WorkOrderLineDetailAddress | None = None
    customer_line_reference: str | None = None
    operational_notes: str | None = None
    line_start_date: date | None = None
    line_end_date: date | None = None
    # 8A core: null until answered. Not a missing item: release (7B) decides what it needs.
    site_central_government: bool | None = None
    is_complete: bool
    missing_items: list[str]
    updated_by: UUID | None = None
    updated_by_display_name: str | None = None
    updated_at: datetime | None = None


class WorkOrderLineDetailActionResponse(BaseModel):
    line_detail: WorkOrderLineDetailResponse
    # None when the save changed nothing: no event is recorded for an identical save.
    event: dict[str, Any] | None = None


# Slice 7D Work Order line billing terms (Part 1). Separate models again: nothing here is added to
# WorkOrderLineResponse, which the frozen handoff returns.

_RATE = {"gt": 0, "max_digits": 18, "decimal_places": 2}
_PERCENT = {"gt": 0, "max_digits": 7, "decimal_places": 2}
# Part 2's month counts are whole months of at least one, with no business maximum: how they are counted
# is the billing slice's to define (owner decision 9). The one upper bound is the integer column's own
# range, stated here so a nonsense number is refused as a readable 422 instead of failing at the database.
_MONTHS = {"ge": 1, "le": 2_147_483_647}
# Part 4's crew numbers are whole numbers of people, and zero is a real answer for one of the two ("2
# operators, no helpers"); that both may not be zero is a rule between the two, which the service and a
# CHECK own (owner decision 28). The upper bound is again only the integer column's own range.
_PEOPLE = {"ge": 0, "le": 2_147_483_647}
_SHIFT_HOURS = {"gt": 0, "max_digits": 4, "decimal_places": 2}
_DAYS = {"gt": 0, "max_digits": 5, "decimal_places": 2}


def _crew_upkeep_fields(*, request: bool) -> dict[str, Any]:
    """Slice 7D Part 5: the crew's food, accommodation and travel, generated from the one specification in
    contract.py (WORK_ORDER_LINE_UPKEEP_CELLS) so the eight cells - four items for operators and for
    helpers - cannot drift apart. A request field is refused when it breaks its own bounds; a response
    field is the stored value."""
    fields: dict[str, Any] = {}
    for cell in WORK_ORDER_LINE_UPKEEP_CELLS:
        for key in ("code", "amount", "unit", "recovery"):
            column = cell[key]
            if column is None:
                continue
            kind = Decimal if key == "amount" else str
            if request:
                limits = _RATE if key == "amount" else {"max_length": 50}
                fields[column] = (kind | None, Field(default=None, **limits))
            else:
                fields[column] = (kind | None, None)
    return fields


_CrewUpkeepRequestFields = create_model(
    "_CrewUpkeepRequestFields", __config__=ConfigDict(extra="forbid"), **_crew_upkeep_fields(request=True)
)
_CrewUpkeepResponseFields = create_model("_CrewUpkeepResponseFields", **_crew_upkeep_fields(request=False))


class WorkOrderLineBillingTermsFields(_CrewUpkeepRequestFields):
    """Every term of one period. Every field may be empty: an empty term is reported as missing,
    and the code NONE records that the Work Order does not mention it. Unknown fields are refused."""

    model_config = ConfigDict(extra="forbid")

    effective_from: date | None = None
    billing_uom_code: str | None = Field(default=None, max_length=50)
    contracted_hours_per_billing_unit: Decimal | None = Field(default=None, gt=0, max_digits=9, decimal_places=2)
    contracted_working_days_per_month: Decimal | None = Field(default=None, gt=0, max_digits=5, decimal_places=2)
    normal_rate_amount: Decimal | None = Field(default=None, **_RATE)
    weekly_off_day_codes: list[str] | None = Field(default=None, max_length=7)
    off_day_work_treatment_code: str | None = Field(default=None, max_length=50)
    holiday_rate_method_code: str | None = Field(default=None, max_length=50)
    holiday_rate_amount: Decimal | None = Field(default=None, **_RATE)
    holiday_rate_percent: Decimal | None = Field(default=None, **_PERCENT)
    overtime_rate_method_code: str | None = Field(default=None, max_length=50)
    overtime_rate_amount: Decimal | None = Field(default=None, **_RATE)
    overtime_rate_percent: Decimal | None = Field(default=None, **_PERCENT)
    month_overtime_hours_basis_code: str | None = Field(default=None, max_length=50)
    month_overtime_counting_code: str | None = Field(default=None, max_length=50)
    breakdown_treatment_code: str | None = Field(default=None, max_length=50)
    breakdown_rate_method_code: str | None = Field(default=None, max_length=50)
    breakdown_rate_amount: Decimal | None = Field(default=None, **_RATE)
    breakdown_rate_percent: Decimal | None = Field(default=None, **_PERCENT)
    breakdown_offset_by_same_day_overtime: bool = False
    customer_idle_treatment_code: str | None = Field(default=None, max_length=50)
    standby_rate_method_code: str | None = Field(default=None, max_length=50)
    standby_rate_amount: Decimal | None = Field(default=None, **_RATE)
    standby_rate_percent: Decimal | None = Field(default=None, **_PERCENT)
    minimum_guarantee_code: str | None = Field(default=None, max_length=50)
    minimum_billing_units_per_month: Decimal | None = Field(default=None, gt=0, max_digits=9, decimal_places=2)
    part_month_basis_code: str | None = Field(default=None, max_length=50)
    # Slice 7D Part 2: night shift and fuel per period; mobilisation and demobilisation on period 1
    # only, which the service refuses to accept on any later period (owner decision 8).
    # Slice 7D Part 5: the shift pattern, which took the place of Part 2's night shift. The crew's food,
    # accommodation and travel come from _CrewUpkeepRequestFields.
    shift_pattern_code: str | None = Field(default=None, max_length=50)
    shift_1_hours: Decimal | None = Field(default=None, **_SHIFT_HOURS)
    shift_2_hours: Decimal | None = Field(default=None, **_SHIFT_HOURS)
    shift_3_hours: Decimal | None = Field(default=None, **_SHIFT_HOURS)
    shift_rate_code: str | None = Field(default=None, max_length=50)
    shift_2_rate_method_code: str | None = Field(default=None, max_length=50)
    shift_2_rate_amount: Decimal | None = Field(default=None, **_RATE)
    shift_2_rate_percent: Decimal | None = Field(default=None, **_PERCENT)
    shift_2_working_days_per_month: Decimal | None = Field(default=None, **_DAYS)
    shift_3_rate_method_code: str | None = Field(default=None, max_length=50)
    shift_3_rate_amount: Decimal | None = Field(default=None, **_RATE)
    shift_3_rate_percent: Decimal | None = Field(default=None, **_PERCENT)
    shift_3_working_days_per_month: Decimal | None = Field(default=None, **_DAYS)
    overtime_counted_per_code: str | None = Field(default=None, max_length=50)
    mobilisation_charge_code: str | None = Field(default=None, max_length=50)
    mobilisation_charge_amount: Decimal | None = Field(default=None, **_RATE)
    mobilisation_credit_after_months: int | None = Field(default=None, **_MONTHS)
    demobilisation_charge_code: str | None = Field(default=None, max_length=50)
    demobilisation_charge_amount: Decimal | None = Field(default=None, **_RATE)
    demobilisation_waived_after_months: int | None = Field(default=None, **_MONTHS)
    fuel_treatment_code: str | None = Field(default=None, max_length=50)
    fuel_charge_method_code: str | None = Field(default=None, max_length=50)
    fuel_rate_per_litre_amount: Decimal | None = Field(default=None, **_RATE)
    fuel_litres_per_working_hour: Decimal | None = Field(default=None, gt=0, max_digits=9, decimal_places=2)
    fuel_travel_allowance_code: str | None = Field(default=None, max_length=50)
    fuel_litres_per_travel_hour: Decimal | None = Field(default=None, gt=0, max_digits=9, decimal_places=2)
    # Slice 7D Part 4: extra kilometres and crew, per period, on every billing basis.
    extra_km_allowance_code: str | None = Field(default=None, max_length=50)
    extra_km_included_km: Decimal | None = Field(default=None, gt=0, max_digits=9, decimal_places=2)
    extra_km_rate_amount: Decimal | None = Field(default=None, **_RATE)
    crew_code: str | None = Field(default=None, max_length=50)
    crew_operators_per_unit: int | None = Field(default=None, **_PEOPLE)
    crew_helpers_per_unit: int | None = Field(default=None, **_PEOPLE)
    extra_crew_charge_code: str | None = Field(default=None, max_length=50)
    extra_crew_operator_rate_amount: Decimal | None = Field(default=None, **_RATE)
    extra_crew_helper_rate_amount: Decimal | None = Field(default=None, **_RATE)
    term_notes: str | None = Field(default=None, max_length=4000)


class WorkOrderLineBillingTermsPeriodCreate(WorkOrderLineBillingTermsFields):
    """Add the next period to a line. `expected_period_count` is the number of periods the caller
    saw, and `expected_latest_term_revision` the revision of the latest one (null when there is none).
    Either differing is refused with 409, so two people cannot both add "period 2", and a period copied
    from the latest one cannot be built from terms someone has since changed (review round 2)."""

    expected_period_count: int = Field(ge=0)
    expected_latest_term_revision: int | None = Field(default=None, ge=1)


class WorkOrderLineBillingTermsPeriodUpdate(WorkOrderLineBillingTermsFields):
    """Whole replacement of one period, guarded by the revision the caller last read."""

    expected_term_revision: int = Field(ge=1)


class WorkOrderLineBillingTermPeriodResponse(_CrewUpkeepResponseFields):
    term_public_id: UUID
    period_number: int
    # Slice 7D Part 5: true where Part 2 recorded this period's night shift as "not in the Work Order". The migration
    # kept that answer here when it asked for the shift pattern again; no request can set or change it.
    legacy_night_shift_not_in_work_order: bool = False
    effective_from: date | None = None
    # Derived: the day before the next period starts, or null for the latest period.
    effective_to: date | None = None
    term_revision: int
    currency_code: str
    billing_uom_code: str | None = None
    contracted_hours_per_billing_unit: Decimal | None = None
    contracted_working_days_per_month: Decimal | None = None
    # Derived for a monthly line: contracted hours per month divided by working days per month.
    derived_hours_per_working_day: Decimal | None = None
    normal_rate_amount: Decimal | None = None
    weekly_off_day_codes: list[str] | None = None
    off_day_work_treatment_code: str | None = None
    holiday_rate_method_code: str | None = None
    holiday_rate_amount: Decimal | None = None
    holiday_rate_percent: Decimal | None = None
    overtime_rate_method_code: str | None = None
    overtime_rate_amount: Decimal | None = None
    overtime_rate_percent: Decimal | None = None
    month_overtime_hours_basis_code: str | None = None
    month_overtime_counting_code: str | None = None
    breakdown_treatment_code: str | None = None
    breakdown_rate_method_code: str | None = None
    breakdown_rate_amount: Decimal | None = None
    breakdown_rate_percent: Decimal | None = None
    breakdown_offset_by_same_day_overtime: bool
    customer_idle_treatment_code: str | None = None
    standby_rate_method_code: str | None = None
    standby_rate_amount: Decimal | None = None
    standby_rate_percent: Decimal | None = None
    minimum_guarantee_code: str | None = None
    minimum_billing_units_per_month: Decimal | None = None
    part_month_basis_code: str | None = None
    # Part 5: the shift pattern (the crew's upkeep comes from _CrewUpkeepResponseFields).
    shift_pattern_code: str | None = None
    shift_1_hours: Decimal | None = None
    shift_2_hours: Decimal | None = None
    shift_3_hours: Decimal | None = None
    shift_rate_code: str | None = None
    shift_2_rate_method_code: str | None = None
    shift_2_rate_amount: Decimal | None = None
    shift_2_rate_percent: Decimal | None = None
    shift_2_working_days_per_month: Decimal | None = None
    shift_3_rate_method_code: str | None = None
    shift_3_rate_amount: Decimal | None = None
    shift_3_rate_percent: Decimal | None = None
    shift_3_working_days_per_month: Decimal | None = None
    overtime_counted_per_code: str | None = None
    # Period 1 only: these describe the whole line, not the period (owner decision 8).
    mobilisation_charge_code: str | None = None
    mobilisation_charge_amount: Decimal | None = None
    mobilisation_credit_after_months: int | None = None
    demobilisation_charge_code: str | None = None
    demobilisation_charge_amount: Decimal | None = None
    demobilisation_waived_after_months: int | None = None
    fuel_treatment_code: str | None = None
    fuel_charge_method_code: str | None = None
    fuel_rate_per_litre_amount: Decimal | None = None
    fuel_litres_per_working_hour: Decimal | None = None
    fuel_travel_allowance_code: str | None = None
    fuel_litres_per_travel_hour: Decimal | None = None
    # Part 4.
    extra_km_allowance_code: str | None = None
    extra_km_included_km: Decimal | None = None
    extra_km_rate_amount: Decimal | None = None
    crew_code: str | None = None
    crew_operators_per_unit: int | None = None
    crew_helpers_per_unit: int | None = None
    extra_crew_charge_code: str | None = None
    extra_crew_operator_rate_amount: Decimal | None = None
    extra_crew_helper_rate_amount: Decimal | None = None
    term_notes: str | None = None
    is_complete: bool
    missing_items: list[str]
    updated_by: UUID | None = None
    updated_by_display_name: str | None = None
    updated_at: datetime


class WorkOrderLineBillingTermsResponse(BaseModel):
    """One Work Order line's billing terms, every period in order, with advisory completeness."""

    work_order_line_public_id: UUID
    line_number: int
    source_offer_line_public_id: UUID | None = None
    # The quoted unit and rate the handoff copied from the accepted offer, read-only and kept for
    # history; the Work Order rate is recorded per period.
    quoted_uom: str
    quoted_rate_amount: Decimal | None = None
    # The latest period whose start is on or before today in India time, else 1; null with no periods.
    current_period_number: int | None = None
    periods: list[WorkOrderLineBillingTermPeriodResponse]
    terms_complete: bool
    line_missing_items: list[str]


class WorkOrderLineBillingTermsActionResponse(BaseModel):
    line_billing_terms: WorkOrderLineBillingTermsResponse
    # None when a save changed nothing.
    event: dict[str, Any] | None = None


# --- Slice 7D Part 3: the contract period, extensions and copying terms between lines --------------
# Separate models again: nothing here is added to WorkOrderResponse or WorkOrderLineResponse, which
# the frozen Accepted Offer -> Work Order handoff returns.


class WorkOrderContractPeriodUpdate(BaseModel):
    """Whole replacement of the Work Order's contract period. `expected_period_version` is the
    version the caller last read: null when nothing has been recorded yet. A mismatch is refused with
    409, so two people editing the same Work Order cannot silently overwrite each other.

    `contract_end_basis_code` is how the end date was answered, not a formatting choice:

    - null, with no end date - not answered yet, and reported missing;
    - FIXED_DATE with `contract_end_date` - the contract ends on that day;
    - UNTIL_WORK_COMPLETE with no end date - a recorded answer (owner decision 14), after which the
      screen says the Work Order cannot be closed until a firm end date is recorded.

    An extension is the way to move the end date, and is recorded through its own route. Editing the
    end date here is still allowed today; owner decision 19 locks it at mobilisation, which does not
    exist yet.
    """

    model_config = ConfigDict(extra="forbid")

    expected_period_version: int | None = Field(default=None, ge=1)
    contract_start_date: date | None = None
    contract_end_basis_code: str | None = Field(default=None, max_length=50)
    contract_end_date: date | None = None
    contract_notes: str | None = Field(default=None, max_length=4000)


class WorkOrderContractExtensionCreate(BaseModel):
    """One extension: the new end date, the customer's reference, the date it was received and,
    through `created_by`, who recorded it (owner decision 15).

    The customer's reference is optional, following the Slice 6O.2 amendment intake, which makes
    `customer_amendment_reference` optional for the same reason: a customer may extend by email or
    on a call, and requiring a reference number would invite an invented one.
    """

    model_config = ConfigDict(extra="forbid")

    new_end_date: date
    received_date: date
    customer_reference: str | None = Field(default=None, max_length=255)
    extension_notes: str | None = Field(default=None, max_length=4000)
    # The day the extension starts (owner, 22 September 2026). Left out, it is the day after the
    # current fixed end, which is the normal case. A later day leaves days no contract runs on, and is
    # recorded only with `gap_confirmed_from`: the first of those days, as the screen showed them when
    # the user agreed. It is a date rather than a yes, so a confirmation given against one end date
    # cannot authorize a gap that another user's change has since moved.
    extension_start_date: date | None = None
    gap_confirmed_from: date | None = None


class WorkOrderContractExtensionResponse(BaseModel):
    extension_public_id: UUID
    extension_sequence_no: int
    # What the contract said before this extension. Both null where no end date had been recorded.
    previous_end_basis_code: str | None = None
    previous_end_date: date | None = None
    new_end_date: date
    # Null exactly when there was no fixed end for the extension to follow.
    extension_start_date: date | None = None
    customer_reference: str | None = None
    received_date: date
    extension_notes: str | None = None
    created_by: UUID | None = None
    created_by_display_name: str | None = None
    created_at: datetime


class WorkOrderContractGapResponse(BaseModel):
    """Days no contract runs on, left by an extension that starts later than the day after the end it
    follows (owner, 22 September 2026). Both days inclusive."""

    first_day: date
    last_day: date
    extension_sequence_no: int


class WorkOrderContractPeriodResponse(BaseModel):
    """The Work Order's contract period, its state today, and every extension that moved its end.

    `contract_state_code` and `contract_state_label` are computed on read against India's date, never
    stored: "not started", "active, ends in N days", "ended" (owner decision 17). `missing_items` is
    advisory in the same way 7C's and 7D's are - nothing blocks on it in this package; Work Order
    release (7B) and closure (8E) will.
    """

    work_order_public_id: UUID
    period_public_id: UUID | None = None
    period_version: int | None = None
    contract_start_date: date | None = None
    contract_end_basis_code: str | None = None
    contract_end_date: date | None = None
    contract_notes: str | None = None
    contract_state_code: str
    contract_state_label: str
    days_until_start: int | None = None
    days_until_end: int | None = None
    # True only while the end is "until the work is complete": a recorded answer that still leaves the
    # Work Order un-closable, which the screen says in those words (owner decision 14).
    needs_firm_end_date: bool
    is_complete: bool
    missing_items: list[str]
    extensions: list[WorkOrderContractExtensionResponse]
    # Days inside the overall span that no contract runs on, oldest first. Empty when every extension
    # runs straight on from the end it follows.
    gaps: list[WorkOrderContractGapResponse] = []
    updated_by: UUID | None = None
    updated_by_display_name: str | None = None
    updated_at: datetime | None = None


class WorkOrderContractPeriodActionResponse(BaseModel):
    contract_period: WorkOrderContractPeriodResponse
    # None when the save changed nothing: no event is recorded for an identical save.
    event: dict[str, Any] | None = None


class WorkOrderLineBillingTermsCopySourcePeriod(BaseModel):
    """One period of the source line as the caller saw it."""

    model_config = ConfigDict(extra="forbid")

    term_public_id: UUID
    term_revision: int = Field(ge=1)


class WorkOrderLineBillingTermsCopyTarget(BaseModel):
    """One line the terms are copied to, carrying what the caller saw of it and whether the user was
    asked about replacing it.

    `replace_confirmed` is per line, not per request. A single request-wide flag was the first
    design, and independent review showed it could authorize replacing a line the user was never
    asked about: the screen names line 2 in its confirmation, line 3 gains terms before the request
    takes the Work Order lock, and one global flag replaces both (round 1, finding F-02).
    """

    model_config = ConfigDict(extra="forbid")

    work_order_line_public_id: UUID
    # Every period the caller saw of THIS line, in order - the same shape as `source_periods`, and
    # for the same reason. A count plus the latest revision was the first design here too, and it
    # cannot see a change to an earlier period: exactly the hole that was fixed on the source side
    # and left open on this one (independent review round 1 finding F-01, then round 2 finding F-07).
    # Empty means the caller saw a line with no terms at all.
    observed_periods: list[WorkOrderLineBillingTermsCopySourcePeriod] = Field(default_factory=list)
    replace_confirmed: bool = False


class WorkOrderLineBillingTermsCopyRequest(BaseModel):
    """Copy the terms of the line the user is standing on onto other lines of the same Work Order
    (owner decision 20). The source is the line in the route path; the targets are named here.

    Every source period is carried, not merely a count and the latest revision. Those two alone left
    a change to an EARLIER source period undetectable, so a period the user never reviewed could be
    copied (independent review round 1, finding F-01).

    A line simply left out of `targets` is not touched, and leaving it out never removes its terms.
    """

    model_config = ConfigDict(extra="forbid")

    targets: list[WorkOrderLineBillingTermsCopyTarget] = Field(min_length=1)
    source_periods: list[WorkOrderLineBillingTermsCopySourcePeriod] = Field(min_length=1)


class WorkOrderLineBillingTermsCopyResult(BaseModel):
    """What happened to one receiving line. Reported line by line, so a line that could not be
    written is named without stopping the others (owner decision 20b)."""

    work_order_line_public_id: UUID
    line_number: int
    outcome: str
    periods_copied: int
    replaced_period_count: int
    # Why this line failed, in the user's words. None for a line that succeeded.
    message: str | None = None


class WorkOrderLineBillingTermsCopyResponse(BaseModel):
    source_line_public_id: UUID
    source_line_number: int
    results: list[WorkOrderLineBillingTermsCopyResult]
    # Every line's terms as they now stand, so the page refreshes in one go rather than re-reading.
    billing_terms: list["WorkOrderLineBillingTermsResponse"]
    # One event per receiving line that was written, so the trail reads as one change per line.
    events: list[dict[str, Any]]


# --- Slice 7D Part 4: the holidays a Work Order names; since HOL-1 its changes to PBL's calendar -------------------
# Separate models again: nothing here is added to WorkOrderResponse, which the frozen handoff returns.


class WorkOrderHolidayChangeInput(BaseModel):
    """One of the Work Order's changes to PBL's calendar (HOL-1, Q4): a holiday added - with its kind, national or
    festival - or a calendar holiday made a working day - with its rate, normal or overtime. The description is an
    added holiday's own words, or a working day's note; optional for both."""

    model_config = ConfigDict(extra="forbid")

    # Only the date is required here. A code left out, null or not known, or a description or note too long, is refused
    # by the service in words that name the date; a check here would answer first, with no date (independent review,
    # HOL1-R3-001 and HOL1-R4-002).
    change_code: str | None = None
    holiday_date: date
    holiday_kind_code: str | None = None
    working_day_rate_code: str | None = None
    description: str | None = None


class WorkOrderHolidayListUpdate(BaseModel):
    """Whole replacement of the Work Order's changes to PBL's calendar, guarded by the version the caller last read:
    null when nothing has been recorded yet. A mismatch is refused with 409.

    `holidays_answer_code` is what tells "the Work Order follows PBL's calendar unchanged" (CALENDAR_UNCHANGED) from a
    list not entered yet, which is simply no answer recorded (owner decision 29). CALENDAR_UNCHANGED carries no
    changes; CALENDAR_CHANGED carries them, and is still reported missing until at least one is entered.
    """

    model_config = ConfigDict(extra="forbid")

    expected_list_version: int | None = Field(default=None, ge=1)
    # Checked by the service, in words, as the changes' codes are - left out or null included (HOL1-R4-002).
    holidays_answer_code: str | None = None
    changes: list[WorkOrderHolidayChangeInput] = Field(default_factory=list)


class WorkOrderHolidayChangeResponse(BaseModel):
    change_public_id: UUID
    change_code: str
    holiday_date: date
    holiday_kind_code: str | None = None
    working_day_rate_code: str | None = None
    description: str | None = None


class WorkOrderHolidayListResponse(BaseModel):
    """The Work Order's changes to PBL's calendar, in date order, with advisory completeness. Every field but the Work
    Order's id is null, and the list empty, until the answer is first recorded."""

    work_order_public_id: UUID
    holiday_list_public_id: UUID | None = None
    list_version: int | None = None
    holidays_answer_code: str | None = None
    changes: list[WorkOrderHolidayChangeResponse]
    is_complete: bool
    missing_items: list[str]
    updated_by: UUID | None = None
    updated_by_display_name: str | None = None
    updated_at: datetime | None = None


# --- HOL-1: the holidays that apply (section 5.3) -----------------------------------------------------------------


class WorkOrderCalendarHolidayEntry(BaseModel):
    """One holiday of PBL's calendar on a date: its name and kind, and where it applies."""

    holiday_name: str
    holiday_kind_code: str
    applies_to_code: str
    state_codes: list[str]
    state_labels: list[str]


class WorkOrderCalendarDay(BaseModel):
    """A date PBL's calendar holds as a holiday for at least one of the Work Order's sites, inside the contract: what
    the form offers the choice "Holiday", "Working day, normal rate" or "Working day, overtime rate" beside."""

    holiday_date: date
    entries: list[WorkOrderCalendarHolidayEntry]
    # The lines whose site it is a holiday for.
    line_numbers: list[int]


class WorkOrderResultingDay(BaseModel):
    holiday_date: date
    day_code: str
    source_code: str
    holiday_kind_code: str | None = None
    # The calendar holiday's name, or an added holiday's description.
    name: str | None = None
    working_day_rate_code: str | None = None
    note: str | None = None
    # For a working day at the overtime rate: the group's lines whose billing terms record no overtime rate that day.
    lines_without_overtime_rate: list[int] = Field(default_factory=list)


class WorkOrderHolidayGroup(BaseModel):
    """The lines whose sites are in one state - or whose state is not known, with what to put right - and their days."""

    state_code: str | None = None
    state_label: str | None = None
    problem_code: str | None = None
    problem_message: str | None = None
    line_numbers: list[int]
    days: list[WorkOrderResultingDay]


class WorkOrderHolidayChangeNote(BaseModel):
    holiday_date: date
    change_code: str
    note_code: str
    message: str


class WorkOrderResultingHolidaysResponse(BaseModel):
    """PBL's calendar as the Work Order changes it, for each state's lines, over the contract (HOL-1, section 5.3). A
    read: it never writes."""

    work_order_public_id: UUID
    holidays_answer_code: str | None = None
    list_version: int | None = None
    # The days shown; both null with no contract start recorded.
    period_from: date | None = None
    period_to: date | None = None
    period_note_code: str | None = None
    period_message: str | None = None
    calendar_days: list[WorkOrderCalendarDay]
    groups: list[WorkOrderHolidayGroup]
    # The years in the period whose calendar Admin has not marked complete (Q2).
    years_not_complete: list[int]
    change_notes: list[WorkOrderHolidayChangeNote]


class WorkOrderHolidayListActionResponse(BaseModel):
    holiday_list: WorkOrderHolidayListResponse
    # None when the save changed nothing: no event is recorded for an identical save.
    event: dict[str, Any] | None = None
