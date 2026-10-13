"""Slice 7D Work Order line billing terms (Parts 1, 2, 4 and 5), and copying one line's terms onto others
(Part 3, owner decision 20). Part 4's holiday list belongs to the Work Order, not a line, and lives in
services/holidays.py.

The terms the customer's Work Order sets for a line, one row per period, in
crm_work_order_line_billing_term. Nothing here writes to crm_work_order or crm_work_order_line, and
nothing is reachable from the handoff. No calculation happens here: these are the recorded inputs a
later billing slice reads. Missing terms are reported, never guessed (WBT-001).

Copying terms lives here rather than with the contract period, although both arrived in Part 3: it is
a write of billing terms, under the billing-terms permission, and it is built on this module's own
read-back and conflict message.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.work_orders.contract_period_rules import (
    ContractGap,
    date_outside_contract_message,
    format_contract_date,
)
from app.modules.work_orders.contract import (
    WORK_ORDER_LINE_BASES_WITH_MINIMUM_GUARANTEE,
    WORK_ORDER_LINE_BASES_WITH_TIME_TERMS,
    WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_COPIED,
    WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_FAILED,
    WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_REPLACED,
    WORK_ORDER_LINE_BILLING_TERMS_EVENT_COPIED,
    WORK_ORDER_LINE_BILLING_TERMS_EVENT_PERIOD_ADDED,
    WORK_ORDER_LINE_BILLING_TERMS_EVENT_PERIOD_REMOVED,
    WORK_ORDER_LINE_BILLING_TERMS_EVENT_PERIOD_UPDATED,
    WORK_ORDER_LINE_BILLING_TERMS_LOCKED_WORK_ORDER_STATUSES,
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_BILLING_UOM_CODES,
    WORK_ORDER_LINE_BILLING_UOM_HOUR,
    WORK_ORDER_LINE_BILLING_UOM_MONTH,
    WORK_ORDER_LINE_BILLING_WEEKDAY_CODES,
    WORK_ORDER_LINE_BREAKDOWN_CODES,
    WORK_ORDER_LINE_BREAKDOWN_DEDUCT_AT_RATE,
    WORK_ORDER_LINE_CREW_CODES,
    WORK_ORDER_LINE_CREW_STATED,
    WORK_ORDER_LINE_DEMOBILISATION_CHARGED_CODES,
    WORK_ORDER_LINE_DEMOBILISATION_CHARGED_WAIVED,
    WORK_ORDER_LINE_DEMOBILISATION_CODES,
    WORK_ORDER_LINE_EXTRA_CREW_CHARGE_CODES,
    WORK_ORDER_LINE_EXTRA_CREW_RATE_PER_PERSON,
    WORK_ORDER_LINE_EXTRA_KM_CODES,
    WORK_ORDER_LINE_EXTRA_KM_INCLUDED_CODES,
    WORK_ORDER_LINE_FIRST_PERIOD_ONLY_TERMS,
    WORK_ORDER_LINE_FUEL_AGREED_RATE_PER_LITRE,
    WORK_ORDER_LINE_FUEL_CHARGE_METHOD_CODES,
    WORK_ORDER_LINE_FUEL_CUSTOMER_SUPPLIED,
    WORK_ORDER_LINE_FUEL_PBL_CHARGED,
    WORK_ORDER_LINE_FUEL_TRAVEL_CODES,
    WORK_ORDER_LINE_FUEL_TRAVEL_LITRES_PER_HOUR,
    WORK_ORDER_LINE_FUEL_TREATMENT_CODES,
    WORK_ORDER_LINE_IDLE_CODES,
    WORK_ORDER_LINE_IDLE_STANDBY_RATE,
    WORK_ORDER_LINE_LATER_SHIFTS,
    WORK_ORDER_LINE_MINIMUM_GUARANTEE_CODES,
    WORK_ORDER_LINE_MINIMUM_UNITS_PER_MONTH,
    WORK_ORDER_LINE_MOBILISATION_CHARGED_CODES,
    WORK_ORDER_LINE_MOBILISATION_CHARGED_CREDITED,
    WORK_ORDER_LINE_MOBILISATION_CODES,
    WORK_ORDER_LINE_MONTH_OT_COUNTING_CODES,
    WORK_ORDER_LINE_MONTH_OT_HOURS_BASIS_CODES,
    WORK_ORDER_LINE_OFF_DAY_HOLIDAY_RATE,
    WORK_ORDER_LINE_OFF_DAY_OVERTIME_RATE,
    WORK_ORDER_LINE_OFF_DAY_WORK_CODES,
    WORK_ORDER_LINE_OVERTIME_COUNTED_PER_CODES,
    WORK_ORDER_LINE_OVERTIME_METHOD_CODES,
    WORK_ORDER_LINE_PART_MONTH_CODES,
    WORK_ORDER_LINE_RATE_METHOD_CODES,
    WORK_ORDER_LINE_RATE_PER_HOUR,
    WORK_ORDER_LINE_SHIFT_HOURS_IN_A_DAY,
    WORK_ORDER_LINE_SHIFT_PATTERN_CODES,
    WORK_ORDER_LINE_SHIFT_PATTERN_THREE,
    WORK_ORDER_LINE_SHIFT_PATTERNS_SEVERAL,
    WORK_ORDER_LINE_SHIFT_RATE_AMOUNT_METHODS,
    WORK_ORDER_LINE_SHIFT_RATE_CODES,
    WORK_ORDER_LINE_SHIFT_RATE_METHOD_CODES,
    WORK_ORDER_LINE_SHIFT_RATE_PER_SHIFT,
    WORK_ORDER_LINE_SHIFTS_PER_DAY,
    WORK_ORDER_LINE_TERMS_MISSING_BILLING_BASIS,
    WORK_ORDER_LINE_TERMS_MISSING_BREAKDOWN,
    WORK_ORDER_LINE_TERMS_MISSING_CONTRACTED_HOURS,
    WORK_ORDER_LINE_TERMS_MISSING_CONTRACTED_WORKING_DAYS,
    WORK_ORDER_LINE_TERMS_MISSING_CREW,
    WORK_ORDER_LINE_TERMS_MISSING_CREW_UPKEEP,
    WORK_ORDER_LINE_TERMS_MISSING_DEMOBILISATION,
    WORK_ORDER_LINE_TERMS_MISSING_EXTRA_KILOMETRES,
    WORK_ORDER_LINE_TERMS_MISSING_FUEL,
    WORK_ORDER_LINE_TERMS_MISSING_IDLE_TIME,
    WORK_ORDER_LINE_TERMS_MISSING_MINIMUM_GUARANTEE,
    WORK_ORDER_LINE_TERMS_MISSING_MOBILISATION,
    WORK_ORDER_LINE_TERMS_MISSING_MONTH_OVERTIME_METHOD,
    WORK_ORDER_LINE_TERMS_MISSING_NORMAL_RATE,
    WORK_ORDER_LINE_TERMS_MISSING_NO_TERMS,
    WORK_ORDER_LINE_TERMS_MISSING_OFF_DAY_WORK,
    WORK_ORDER_LINE_TERMS_MISSING_ORDER,
    WORK_ORDER_LINE_TERMS_MISSING_OVERTIME,
    WORK_ORDER_LINE_TERMS_MISSING_PART_MONTH,
    WORK_ORDER_LINE_TERMS_MISSING_SHIFTS,
    WORK_ORDER_LINE_TERMS_MISSING_WEEKLY_OFF_DAYS,
    WORK_ORDER_LINE_UPKEEP_CELLS,
    WORK_ORDER_LINE_UPKEEP_CODES,
    WORK_ORDER_LINE_UPKEEP_PROVIDED_AT_COST,
    WORK_ORDER_LINE_UPKEEP_RECOVERY_CODES,
)
from app.modules.work_orders.repository import (
    WORK_ORDER_LINE_BILLING_TERM_COLUMNS,
    delete_billing_term,
    delete_billing_terms_for_line,
    get_work_order_line_context,
    insert_billing_term,
    list_billing_term_rows_for_line,
    list_work_order_billing_term_lines,
    list_work_order_billing_term_rows,
    list_work_order_line_ids,
    update_billing_term,
)
from app.modules.work_orders.schemas import (
    WorkOrderLineBillingTermPeriodResponse,
    WorkOrderLineBillingTermsActionResponse,
    WorkOrderLineBillingTermsCopyRequest,
    WorkOrderLineBillingTermsCopyResponse,
    WorkOrderLineBillingTermsCopyResult,
    WorkOrderLineBillingTermsFields,
    WorkOrderLineBillingTermsPeriodCreate,
    WorkOrderLineBillingTermsPeriodUpdate,
    WorkOrderLineBillingTermsResponse,
    WorkOrderResponse,
)
from app.modules.work_orders.services.common import (
    WorkOrderLineBillingTermNotFoundError,
    WorkOrderLineBillingTermsConflictError,
    WorkOrderLineNotFoundError,
    WorkOrderValidationError,
    _clean_optional,
    _get_work_order_and_id,
    _lock_work_order_for_contract_period,
    _record_billing_terms_event,
    _same_value,
    _term_code,
    contract_bounds_for_work_order,
    contract_gaps_for_work_order,
)
from app.shared import business_time
from app.shared.transactions import rollback_on_error


_CHARGED_RATE_METHODS = WORK_ORDER_LINE_RATE_METHOD_CODES


_DEDUCTING_BREAKDOWN = tuple(code for code in WORK_ORDER_LINE_BREAKDOWN_CODES if code != WORK_ORDER_LINE_BILLING_TERM_NONE)


# Every stored term except the start date, which the period response carries separately.
_BILLING_TERM_RESPONSE_COLUMNS = tuple(
    column for column in WORK_ORDER_LINE_BILLING_TERM_COLUMNS if column != "effective_from"
)


# Terms that mean nothing until a billing basis is chosen. Each entry is a term the user chooses
# directly; a value that belongs to one of them (an amount, a percentage, a month count) is governed by
# its own rule below and so cannot appear before its parent choice either.
_BASIS_DEPENDENT_TERMS = (
    "contracted_hours_per_billing_unit",
    "contracted_working_days_per_month",
    "normal_rate_amount",
    "weekly_off_day_codes",
    "off_day_work_treatment_code",
    "overtime_rate_method_code",
    "breakdown_treatment_code",
    "minimum_guarantee_code",
    "part_month_basis_code",
    "customer_idle_treatment_code",
    # Part 2: mobilisation, demobilisation and fuel are terms like the others.
    "mobilisation_charge_code",
    "demobilisation_charge_code",
    "fuel_treatment_code",
    # Part 4: so are extra kilometres and crew.
    "extra_km_allowance_code",
    "crew_code",
    # Part 5: and the shift pattern. The crew's upkeep needs the crew stated, which needs the basis.
    "shift_pattern_code",
)


# Hour-based billing uses actual working hours only (WBT-001). The shift pattern is refused on an hourly
# line by Part 5's own rule, with its own message.
_NOT_HOURLY_TERMS = (
    "contracted_hours_per_billing_unit",
    "weekly_off_day_codes",
    "off_day_work_treatment_code",
    "overtime_rate_method_code",
    "breakdown_treatment_code",
)


_MONTH_ONLY_TERMS = (
    "contracted_working_days_per_month",
    "month_overtime_hours_basis_code",
    "month_overtime_counting_code",
    "part_month_basis_code",
)


# Slice 7D Part 5: every shift-pattern column. All of them belong to shift, day and month lines only: an
# hourly line bills the hours it worked, whenever they were worked, as it had no night shift before.
_SHIFT_TERMS = (
    "shift_pattern_code",
    "shift_1_hours",
    "shift_2_hours",
    "shift_3_hours",
    "shift_rate_code",
    "shift_2_rate_method_code",
    "shift_2_rate_amount",
    "shift_2_rate_percent",
    "shift_2_working_days_per_month",
    "shift_3_rate_method_code",
    "shift_3_rate_amount",
    "shift_3_rate_percent",
    "shift_3_working_days_per_month",
    "overtime_counted_per_code",
)


def _later_shift_terms(shift: int) -> tuple[str, ...]:
    return (
        f"shift_{shift}_rate_method_code",
        f"shift_{shift}_rate_amount",
        f"shift_{shift}_rate_percent",
        f"shift_{shift}_working_days_per_month",
    )


_UPKEEP_ITEM_LABELS = {
    "food": "food",
    "accommodation": "accommodation",
    "job_travel": "travel to and from the job",
    "daily_travel": "daily travel to site",
}
_UPKEEP_UNIT_LABELS = {
    "PER_PERSON_PER_DAY": "per person per day",
    "PER_PERSON_PER_MONTH": "per person per month",
    "PER_PERSON_PER_TRIP": "per person per trip",
    "PER_TRIP": "per trip, whatever the number of people",
    "PER_DAY": "per day, whatever the number of people",
}


_TERMS_CONFLICT_MESSAGE = "Someone else changed these billing terms after you opened them. Reload to see their version."


def _weekly_off_days(value: list[str] | None) -> list[str] | None:
    """Days of the week in Monday-first order, without repeats. An empty list is a 7-day week."""
    if value is None:
        return None
    codes = {code.strip().upper() for code in value}
    if not codes <= set(WORK_ORDER_LINE_BILLING_WEEKDAY_CODES):
        raise WorkOrderValidationError("Weekly off days must be days of the week, MON to SUN.")
    if len(codes) == len(WORK_ORDER_LINE_BILLING_WEEKDAY_CODES):
        raise WorkOrderValidationError("A line cannot have every day of the week off.")
    return [code for code in WORK_ORDER_LINE_BILLING_WEEKDAY_CODES if code in codes]


def _rate_values(
    values: dict[str, Any],
    payload: WorkOrderLineBillingTermsFields,
    *,
    prefix: str,
    label: str,
    allowed_methods: tuple[str, ...],
) -> None:
    """One rate: how it is given (per hour, or a percentage of the normal rate) and exactly that value."""
    method = _term_code(
        getattr(payload, f"{prefix}_method_code"),
        allowed_methods,
        f"The {label} must be given per hour or as a percentage of the normal rate.",
    )
    amount = getattr(payload, f"{prefix}_amount")
    percent = getattr(payload, f"{prefix}_percent")
    if method in (None, WORK_ORDER_LINE_BILLING_TERM_NONE):
        if amount is not None or percent is not None:
            raise WorkOrderValidationError(f"Choose how the {label} is given, or remove its amount.")
    elif method == WORK_ORDER_LINE_RATE_PER_HOUR:
        if amount is None:
            raise WorkOrderValidationError(f"Enter the {label} per hour.")
        if percent is not None:
            raise WorkOrderValidationError(f"The {label} is given per hour, so it has no percentage.")
    else:
        if percent is None:
            raise WorkOrderValidationError(f"Enter the {label} as a percentage of the normal rate.")
        if amount is not None:
            raise WorkOrderValidationError(f"The {label} is given as a percentage, so it has no amount per hour.")
    values[f"{prefix}_method_code"] = method
    values[f"{prefix}_amount"] = amount
    values[f"{prefix}_percent"] = percent


def _later_shift_rate_values(values: dict[str, Any], payload: WorkOrderLineBillingTermsFields, shift: int) -> None:
    """A later shift's own rate (Slice 7D Part 5, extending Part 2's night shift): how it is given - per
    shift, per hour or as a percentage of the Work Order rate - and exactly the one value that choice asks
    for, in the same save, as Part 2 required of the night shift."""
    method = _term_code(
        getattr(payload, f"shift_{shift}_rate_method_code"),
        WORK_ORDER_LINE_SHIFT_RATE_METHOD_CODES,
        f"Shift {shift} must be charged per shift, per hour or as a percentage of the Work Order rate.",
    )
    amount = getattr(payload, f"shift_{shift}_rate_amount")
    percent = getattr(payload, f"shift_{shift}_rate_percent")
    if method is None:
        if amount is not None or percent is not None:
            raise WorkOrderValidationError(f"Choose how shift {shift} is charged, or remove its rate.")
    elif method in WORK_ORDER_LINE_SHIFT_RATE_AMOUNT_METHODS:
        if amount is None:
            raise WorkOrderValidationError(f"Enter shift {shift}'s rate.")
        if percent is not None:
            raise WorkOrderValidationError(f"Shift {shift}'s rate is given as an amount, so it has no percentage.")
    else:
        if percent is None:
            raise WorkOrderValidationError(f"Enter shift {shift}'s rate as a percentage of the Work Order rate.")
        if amount is not None:
            raise WorkOrderValidationError(f"Shift {shift}'s rate is given as a percentage, so it has no amount.")
    values[f"shift_{shift}_rate_method_code"] = method
    values[f"shift_{shift}_rate_amount"] = amount
    values[f"shift_{shift}_rate_percent"] = percent
    values[f"shift_{shift}_working_days_per_month"] = getattr(payload, f"shift_{shift}_working_days_per_month")


def _check_part_2_terms(values: dict[str, Any], *, period_number: int) -> None:
    """The Part 2 rules: a value may be present only where its own choice asks for it. A value a
    recorded choice still needs is reported as missing rather than refused, as Part 1 does for a
    breakdown or holiday rate - the user fills a period in over several saves. Part 2's night shift
    became Part 5's shift pattern."""
    # Mobilisation and demobilisation describe the whole line, so only the first period holds them.
    if period_number != 1 and any(values[term] is not None for term in WORK_ORDER_LINE_FIRST_PERIOD_ONLY_TERMS):
        raise WorkOrderValidationError(
            "Mobilisation and demobilisation are recorded once for the line, in its first period. "
            "A later period does not change them."
        )
    mobilisation = values["mobilisation_charge_code"]
    if mobilisation not in WORK_ORDER_LINE_MOBILISATION_CHARGED_CODES and values["mobilisation_charge_amount"] is not None:
        raise WorkOrderValidationError("A mobilisation charge applies only when mobilisation is charged.")
    if mobilisation != WORK_ORDER_LINE_MOBILISATION_CHARGED_CREDITED and values["mobilisation_credit_after_months"] is not None:
        raise WorkOrderValidationError(
            "The number of months applies only when the mobilisation charge is credited back after a time."
        )
    demobilisation = values["demobilisation_charge_code"]
    if (
        demobilisation not in WORK_ORDER_LINE_DEMOBILISATION_CHARGED_CODES
        and values["demobilisation_charge_amount"] is not None
    ):
        raise WorkOrderValidationError("A demobilisation charge applies only when demobilisation is charged.")
    if (
        demobilisation != WORK_ORDER_LINE_DEMOBILISATION_CHARGED_WAIVED
        and values["demobilisation_waived_after_months"] is not None
    ):
        raise WorkOrderValidationError(
            "The number of months applies only when the demobilisation charge is not charged after a time."
        )

    # Fuel: how a PBL-supplied charge is stated, and what a customer-supplied allowance records.
    fuel = values["fuel_treatment_code"]
    if fuel != WORK_ORDER_LINE_FUEL_PBL_CHARGED and values["fuel_charge_method_code"] is not None:
        raise WorkOrderValidationError("How fuel is charged applies only when PBL supplies the fuel and charges for it.")
    if values["fuel_charge_method_code"] != WORK_ORDER_LINE_FUEL_AGREED_RATE_PER_LITRE and values["fuel_rate_per_litre_amount"] is not None:
        raise WorkOrderValidationError("A rate per litre applies only when the fuel is charged at an agreed rate per litre.")
    if fuel != WORK_ORDER_LINE_FUEL_CUSTOMER_SUPPLIED and (
        values["fuel_litres_per_working_hour"] is not None or values["fuel_travel_allowance_code"] is not None
    ):
        raise WorkOrderValidationError(
            "The agreed litres per hour and the travel allowance apply only when the customer supplies the fuel."
        )
    if (
        values["fuel_travel_allowance_code"] != WORK_ORDER_LINE_FUEL_TRAVEL_LITRES_PER_HOUR
        and values["fuel_litres_per_travel_hour"] is not None
    ):
        raise WorkOrderValidationError(
            "The litres per travel hour apply only when the Work Order gives a travel allowance."
        )


def _part_1_term_values(payload: WorkOrderLineBillingTermsFields) -> dict[str, Any]:
    """The Part 1 terms, each read and checked on its own, in the order they have always been read."""
    return {
        "effective_from": payload.effective_from,
        "billing_uom_code": _term_code(
            payload.billing_uom_code, WORK_ORDER_LINE_BILLING_UOM_CODES, "Billing basis must be Hour, Shift, Day or Month."
        ),
        "contracted_hours_per_billing_unit": payload.contracted_hours_per_billing_unit,
        "contracted_working_days_per_month": payload.contracted_working_days_per_month,
        "normal_rate_amount": payload.normal_rate_amount,
        "weekly_off_day_codes": _weekly_off_days(payload.weekly_off_day_codes),
        "off_day_work_treatment_code": _term_code(
            payload.off_day_work_treatment_code,
            WORK_ORDER_LINE_OFF_DAY_WORK_CODES,
            "Work on an off day or holiday must be not in the Work Order, or charged at the overtime, holiday or normal rate.",
        ),
        "month_overtime_hours_basis_code": _term_code(
            payload.month_overtime_hours_basis_code,
            WORK_ORDER_LINE_MONTH_OT_HOURS_BASIS_CODES,
            "Monthly overtime must count the hours available or the hours actually worked.",
        ),
        "month_overtime_counting_code": _term_code(
            payload.month_overtime_counting_code,
            WORK_ORDER_LINE_MONTH_OT_COUNTING_CODES,
            "Monthly overtime must be counted over the whole month or day by day.",
        ),
        "breakdown_treatment_code": _term_code(
            payload.breakdown_treatment_code,
            WORK_ORDER_LINE_BREAKDOWN_CODES,
            "Breakdown must be not in the Work Order, reduce the billed hours, or be deducted at a breakdown rate.",
        ),
        "breakdown_offset_by_same_day_overtime": bool(payload.breakdown_offset_by_same_day_overtime),
        "customer_idle_treatment_code": _term_code(
            payload.customer_idle_treatment_code,
            WORK_ORDER_LINE_IDLE_CODES,
            "Idle time must be not in the Work Order, paid as working hours, or paid at a standby rate.",
        ),
        "minimum_guarantee_code": _term_code(
            payload.minimum_guarantee_code,
            WORK_ORDER_LINE_MINIMUM_GUARANTEE_CODES,
            "Minimum guarantee must be not in the Work Order, or a number of billing units per month.",
        ),
        "minimum_billing_units_per_month": payload.minimum_billing_units_per_month,
        "part_month_basis_code": _term_code(
            payload.part_month_basis_code,
            WORK_ORDER_LINE_PART_MONTH_CODES,
            "A part month must be divided by calendar days, contracted working days or 30 days.",
        ),
    }


def _part_2_term_values(payload: WorkOrderLineBillingTermsFields) -> dict[str, Any]:
    """The Part 2 terms - mobilisation, demobilisation and fuel - read the same way."""
    return {
        "mobilisation_charge_code": _term_code(
            payload.mobilisation_charge_code,
            WORK_ORDER_LINE_MOBILISATION_CODES,
            "Mobilisation must be not in the Work Order, charged, or charged and credited back after a number of months.",
        ),
        "mobilisation_charge_amount": payload.mobilisation_charge_amount,
        "mobilisation_credit_after_months": payload.mobilisation_credit_after_months,
        "demobilisation_charge_code": _term_code(
            payload.demobilisation_charge_code,
            WORK_ORDER_LINE_DEMOBILISATION_CODES,
            "Demobilisation must be not in the Work Order, charged, or not charged if the machine stays beyond a number of months.",
        ),
        "demobilisation_charge_amount": payload.demobilisation_charge_amount,
        "demobilisation_waived_after_months": payload.demobilisation_waived_after_months,
        "fuel_treatment_code": _term_code(
            payload.fuel_treatment_code,
            WORK_ORDER_LINE_FUEL_TREATMENT_CODES,
            "Fuel must be not in the Work Order, supplied by PBL and included, supplied by PBL and charged, or supplied by the customer.",
        ),
        "fuel_charge_method_code": _term_code(
            payload.fuel_charge_method_code,
            WORK_ORDER_LINE_FUEL_CHARGE_METHOD_CODES,
            "Fuel charged by PBL must be at an agreed rate per litre or at actual cost.",
        ),
        "fuel_rate_per_litre_amount": payload.fuel_rate_per_litre_amount,
        "fuel_litres_per_working_hour": payload.fuel_litres_per_working_hour,
        "fuel_travel_allowance_code": _term_code(
            payload.fuel_travel_allowance_code,
            WORK_ORDER_LINE_FUEL_TRAVEL_CODES,
            "A travel allowance must be not in the Work Order, or a number of litres per travel hour.",
        ),
        "fuel_litres_per_travel_hour": payload.fuel_litres_per_travel_hour,
    }


def _part_4_term_values(payload: WorkOrderLineBillingTermsFields) -> dict[str, Any]:
    """The Part 4 terms - extra kilometres and crew - read the same way (owner answers 22 and 23)."""
    return {
        "extra_km_allowance_code": _term_code(
            payload.extra_km_allowance_code,
            WORK_ORDER_LINE_EXTRA_KM_CODES,
            "Extra kilometres must be not in the Work Order, or a number of kilometres included per day or per month.",
        ),
        "extra_km_included_km": payload.extra_km_included_km,
        "extra_km_rate_amount": payload.extra_km_rate_amount,
        "crew_code": _term_code(
            payload.crew_code,
            WORK_ORDER_LINE_CREW_CODES,
            "Crew must be not part of the Work Order (equipment only), or the number of operators and helpers it states.",
        ),
        "crew_operators_per_unit": payload.crew_operators_per_unit,
        "crew_helpers_per_unit": payload.crew_helpers_per_unit,
        "extra_crew_charge_code": _term_code(
            payload.extra_crew_charge_code,
            WORK_ORDER_LINE_EXTRA_CREW_CHARGE_CODES,
            "Extra crew must be not in the Work Order, or charged at a rate for each extra operator and helper.",
        ),
        "extra_crew_operator_rate_amount": payload.extra_crew_operator_rate_amount,
        "extra_crew_helper_rate_amount": payload.extra_crew_helper_rate_amount,
    }


def _check_part_1_terms(values: dict[str, Any]) -> None:
    """The Part 1 rules between terms: what the billing basis allows, and a value only where its own
    choice asks for it."""
    basis = values["billing_uom_code"]
    if basis is None and any(values[term] is not None for term in _BASIS_DEPENDENT_TERMS):
        raise WorkOrderValidationError("Choose the billing basis before entering the rate and the other terms.")
    if basis == WORK_ORDER_LINE_BILLING_UOM_HOUR and any(values[term] is not None for term in _NOT_HOURLY_TERMS):
        raise WorkOrderValidationError(
            "Hour billing uses the actual hours worked, so it has no contracted hours, off days, overtime or breakdown terms."
        )
    if basis != WORK_ORDER_LINE_BILLING_UOM_MONTH and any(values[term] is not None for term in _MONTH_ONLY_TERMS):
        raise WorkOrderValidationError(
            "Working days per month, how monthly overtime is counted and part-month charging apply only to Month billing."
        )
    if basis == WORK_ORDER_LINE_BILLING_UOM_MONTH and values["minimum_guarantee_code"] is not None:
        # A month short of its contracted hours is charged pro rata, with no minimum (owner, answer 26 of
        # Slice 7D Part 4). The refusal said the monthly rate "already covers the contracted month" until
        # then, which contradicted that rule; the rule itself is unchanged.
        raise WorkOrderValidationError(
            "A minimum guarantee does not apply to Month billing: a month short of the contracted hours "
            "is charged pro rata, with no minimum."
        )

    if (
        values["holiday_rate_method_code"] is not None
        and values["off_day_work_treatment_code"] != WORK_ORDER_LINE_OFF_DAY_HOLIDAY_RATE
    ):
        raise WorkOrderValidationError("A holiday rate applies only when off-day work is charged at a holiday rate.")
    if (
        values["breakdown_rate_method_code"] is not None
        and values["breakdown_treatment_code"] != WORK_ORDER_LINE_BREAKDOWN_DEDUCT_AT_RATE
    ):
        raise WorkOrderValidationError("A breakdown rate applies only when breakdown is deducted at a breakdown rate.")
    if (
        values["standby_rate_method_code"] is not None
        and values["customer_idle_treatment_code"] != WORK_ORDER_LINE_IDLE_STANDBY_RATE
    ):
        raise WorkOrderValidationError("A standby rate applies only when idle time is paid at a standby rate.")

    is_units_guarantee = values["minimum_guarantee_code"] == WORK_ORDER_LINE_MINIMUM_UNITS_PER_MONTH
    if is_units_guarantee and values["minimum_billing_units_per_month"] is None:
        raise WorkOrderValidationError("Enter the minimum number of billing units per month.")
    if not is_units_guarantee and values["minimum_billing_units_per_month"] is not None:
        raise WorkOrderValidationError("A minimum number of units applies only with a monthly minimum guarantee.")

    if (
        values["off_day_work_treatment_code"] == WORK_ORDER_LINE_OFF_DAY_OVERTIME_RATE
        and values["overtime_rate_method_code"] == WORK_ORDER_LINE_BILLING_TERM_NONE
    ):
        raise WorkOrderValidationError(
            "Off-day work cannot be charged at the overtime rate when overtime is not in the Work Order. "
            "Record the overtime rate, or choose another charge for off-day work."
        )

    overtime_charged = values["overtime_rate_method_code"] in _CHARGED_RATE_METHODS
    if not overtime_charged and (
        values["month_overtime_hours_basis_code"] is not None or values["month_overtime_counting_code"] is not None
    ):
        raise WorkOrderValidationError("How monthly overtime is counted applies only when overtime is charged.")
    if values["breakdown_offset_by_same_day_overtime"] and not (
        overtime_charged and values["breakdown_treatment_code"] in _DEDUCTING_BREAKDOWN
    ):
        raise WorkOrderValidationError(
            "Same-day overtime can offset breakdown only when breakdown is deducted and overtime is charged."
        )


def _check_part_4_terms(values: dict[str, Any]) -> None:
    """The Part 4 rules: a value only where its own choice asks for it, as Part 2's are. A value a
    recorded choice still needs is reported missing rather than refused. Neither group depends on the
    billing basis beyond needing one; Part 1's rule already refuses either before the basis is chosen."""
    if values["extra_km_allowance_code"] not in WORK_ORDER_LINE_EXTRA_KM_INCLUDED_CODES and (
        values["extra_km_included_km"] is not None or values["extra_km_rate_amount"] is not None
    ):
        raise WorkOrderValidationError(
            "The kilometres included and the rate per extra kilometre apply only when the Work Order "
            "includes a number of kilometres per day or per month."
        )

    crew_stated = values["crew_code"] == WORK_ORDER_LINE_CREW_STATED
    if not crew_stated and (
        values["crew_operators_per_unit"] is not None
        or values["crew_helpers_per_unit"] is not None
        or values["extra_crew_charge_code"] is not None
    ):
        raise WorkOrderValidationError(
            "The number of operators and helpers, and how extra crew is charged, apply only when the Work "
            "Order states its crew."
        )
    # One of the two numbers may be zero - "2 operators, no helpers" - but not both (owner decision 28).
    if values["crew_operators_per_unit"] == 0 and values["crew_helpers_per_unit"] == 0:
        raise WorkOrderValidationError(
            "A Work Order with no operators and no helpers has no crew. Record it as equipment only instead."
        )
    if values["extra_crew_charge_code"] != WORK_ORDER_LINE_EXTRA_CREW_RATE_PER_PERSON and (
        values["extra_crew_operator_rate_amount"] is not None or values["extra_crew_helper_rate_amount"] is not None
    ):
        raise WorkOrderValidationError(
            "A rate for an extra operator or helper applies only when extra crew is charged per person."
        )


def _part_5_term_values(payload: WorkOrderLineBillingTermsFields) -> dict[str, Any]:
    """The Part 5 terms - the shift pattern and the crew's food, accommodation and travel - read the same
    way (owner's answers of 9 October 2026)."""
    values: dict[str, Any] = {
        "shift_pattern_code": _term_code(
            payload.shift_pattern_code,
            WORK_ORDER_LINE_SHIFT_PATTERN_CODES,
            "Shifts must be not in the Work Order, or one, two or three shifts.",
        ),
        "shift_1_hours": payload.shift_1_hours,
        "shift_2_hours": payload.shift_2_hours,
        "shift_3_hours": payload.shift_3_hours,
        "shift_rate_code": _term_code(
            payload.shift_rate_code,
            WORK_ORDER_LINE_SHIFT_RATE_CODES,
            "The shifts must be charged at one rate for every shift, or each shift at its own rate.",
        ),
    }
    for shift in WORK_ORDER_LINE_LATER_SHIFTS:
        _later_shift_rate_values(values, payload, shift)
    values["overtime_counted_per_code"] = _term_code(
        payload.overtime_counted_per_code,
        WORK_ORDER_LINE_OVERTIME_COUNTED_PER_CODES,
        "Overtime must be counted per shift or for the whole day.",
    )
    for cell in WORK_ORDER_LINE_UPKEEP_CELLS:
        item = _UPKEEP_ITEM_LABELS[str(cell["item"])]
        role = f"{cell['role']}s"
        values[str(cell["code"])] = _term_code(
            getattr(payload, str(cell["code"])),
            WORK_ORDER_LINE_UPKEEP_CODES,
            f"The {item} for {role} must be not in the Work Order, provided by the customer, or provided at a cost.",
        )
        values[str(cell["amount"])] = getattr(payload, str(cell["amount"]))
        values[str(cell["unit"])] = _term_code(
            getattr(payload, str(cell["unit"])),
            cell["units"],
            f"The cost of {item} for {role} must be "
            + " or ".join(_UPKEEP_UNIT_LABELS[unit] for unit in cell["units"])
            + ".",
        )
        values[str(cell["recovery"])] = _term_code(
            getattr(payload, str(cell["recovery"])),
            WORK_ORDER_LINE_UPKEEP_RECOVERY_CODES,
            f"The cost of {item} for {role} must be deducted from PBL's invoice or billed to PBL separately.",
        )
    return values


def _check_part_5_shifts(values: dict[str, Any]) -> None:
    """The shift pattern's rules (owner's answers 4 and 5): a value only where its own choice asks for it,
    as Parts 2 and 4 do; a value a recorded choice still needs is reported missing, not refused."""
    basis = values["billing_uom_code"]
    if basis == WORK_ORDER_LINE_BILLING_UOM_HOUR and any(values[term] is not None for term in _SHIFT_TERMS):
        raise WorkOrderValidationError("Hour billing uses the actual hours worked, so it has no shift pattern.")
    pattern = values["shift_pattern_code"]
    if pattern not in WORK_ORDER_LINE_SHIFTS_PER_DAY and any(
        values[term] is not None for term in _SHIFT_TERMS if term != "shift_pattern_code"
    ):
        raise WorkOrderValidationError(
            "A shift's hours, and how shifts are charged and overtime counted on them, apply only when the Work "
            "Order states its shifts."
        )
    if pattern not in WORK_ORDER_LINE_SHIFT_PATTERNS_SEVERAL and any(
        values[term] is not None for term in _SHIFT_TERMS if term not in ("shift_pattern_code", "shift_1_hours")
    ):
        raise WorkOrderValidationError(
            "A second shift's hours, how the shifts are charged and how overtime is counted on them apply only "
            "when the Work Order states two or three shifts."
        )
    if pattern != WORK_ORDER_LINE_SHIFT_PATTERN_THREE and any(
        values[term] is not None for term in ("shift_3_hours", *_later_shift_terms(3))
    ):
        raise WorkOrderValidationError("A third shift's hours and rate apply only when the Work Order states three shifts.")
    if values["shift_rate_code"] != WORK_ORDER_LINE_SHIFT_RATE_PER_SHIFT and any(
        values[term] is not None for shift in WORK_ORDER_LINE_LATER_SHIFTS for term in _later_shift_terms(shift)
    ):
        raise WorkOrderValidationError(
            "A later shift's own rate and working days apply only when each shift is charged at its own rate."
        )
    if basis != WORK_ORDER_LINE_BILLING_UOM_MONTH and any(
        values[f"shift_{shift}_working_days_per_month"] is not None for shift in WORK_ORDER_LINE_LATER_SHIFTS
    ):
        raise WorkOrderValidationError("A shift's working days per month apply only to Month billing.")
    total = sum((values[f"shift_{shift}_hours"] or Decimal(0) for shift in (1, 2, 3)), Decimal(0))
    if total > WORK_ORDER_LINE_SHIFT_HOURS_IN_A_DAY:
        raise WorkOrderValidationError(
            f"The shifts of one day add up to {total.normalize():f} hours, more than the "
            f"{WORK_ORDER_LINE_SHIFT_HOURS_IN_A_DAY} hours in a day."
        )
    if values["overtime_counted_per_code"] is not None and not _asks_overtime_counted_per(values):
        raise WorkOrderValidationError(
            "Whether overtime is counted per shift or for the whole day applies only when overtime is charged "
            "on two or three shifts."
        )


def _asks_overtime_counted_per(row: dict[str, Any]) -> bool:
    """Whether "per shift or for the whole day" is asked (owner's answer 5, assumption A12 of Part 5): wherever
    overtime is charged on two or three shifts, on every basis that has shifts - a monthly line's whole-month
    counting included, since the answer was not limited (review round 1, finding 7D5-R1-001)."""
    return (
        row.get("overtime_rate_method_code") in _CHARGED_RATE_METHODS
        and row.get("shift_pattern_code") in WORK_ORDER_LINE_SHIFT_PATTERNS_SEVERAL
    )


def _upkeep_cell_applies(row: dict[str, Any], cell: dict[str, Any]) -> bool:
    """A cell is asked while the Work Order states its crew and does not state 0 of that role
    (assumptions A4 and A5 of Part 5)."""
    return row.get("crew_code") == WORK_ORDER_LINE_CREW_STATED and row.get(str(cell["count_column"])) != 0


def _upkeep_cell_columns(cell: dict[str, Any]) -> tuple[str, ...]:
    """The cell's columns, its choice first."""
    return (str(cell["code"]), str(cell["amount"]), str(cell["unit"]), str(cell["recovery"]))


def _check_part_5_upkeep(values: dict[str, Any]) -> None:
    """The crew's food, accommodation and travel (owner's answers 1 to 3)."""
    if values["crew_code"] != WORK_ORDER_LINE_CREW_STATED and any(
        values[column] is not None for cell in WORK_ORDER_LINE_UPKEEP_CELLS for column in _upkeep_cell_columns(cell)
    ):
        raise WorkOrderValidationError(
            "The crew's food, accommodation and travel apply only when the Work Order states its crew."
        )
    for cell in WORK_ORDER_LINE_UPKEEP_CELLS:
        columns = _upkeep_cell_columns(cell)
        if not _upkeep_cell_applies(values, cell) and any(values[column] is not None for column in columns):
            raise WorkOrderValidationError(
                f"The Work Order states no {cell['role']}s, so nothing is recorded for their food, "
                "accommodation or travel."
            )
        if values[columns[0]] != WORK_ORDER_LINE_UPKEEP_PROVIDED_AT_COST and any(
            values[column] is not None for column in columns[1:]
        ):
            raise WorkOrderValidationError(
                "A cost, and how it is counted and recovered, apply only when "
                f"{_UPKEEP_ITEM_LABELS[str(cell['item'])]} for {cell['role']}s is provided at a cost."
            )


def _normalize_billing_terms(payload: WorkOrderLineBillingTermsFields, *, period_number: int) -> dict[str, Any]:
    """Validate one period's terms and return storable values, keyed exactly as the table's columns.
    Mirrors the table's CHECK constraints, with messages a user can act on.

    The terms are read part by part, then the rates, then each part's rules between terms. That order
    is behaviour, not layout: it decides which refusal a request with two faults receives, and the
    order of changed_fields in every event. A later part adds its own _part_N_term_values and
    _check_part_N_terms after the existing ones."""
    values: dict[str, Any] = {
        **_part_1_term_values(payload),
        **_part_2_term_values(payload),
        **_part_4_term_values(payload),
        **_part_5_term_values(payload),
        "term_notes": _clean_optional(payload.term_notes),
    }
    _rate_values(values, payload, prefix="holiday_rate", label="holiday rate", allowed_methods=WORK_ORDER_LINE_RATE_METHOD_CODES)
    _rate_values(values, payload, prefix="overtime_rate", label="overtime rate", allowed_methods=WORK_ORDER_LINE_OVERTIME_METHOD_CODES)
    _rate_values(values, payload, prefix="breakdown_rate", label="breakdown rate", allowed_methods=WORK_ORDER_LINE_RATE_METHOD_CODES)
    _rate_values(values, payload, prefix="standby_rate", label="standby rate", allowed_methods=WORK_ORDER_LINE_RATE_METHOD_CODES)
    _check_part_1_terms(values)
    _check_part_2_terms(values, period_number=period_number)
    _check_part_4_terms(values)
    _check_part_5_shifts(values)
    _check_part_5_upkeep(values)
    return values


def _period_missing_items(row: dict[str, Any]) -> list[str]:
    """What this period still needs before a billing slice could use it. NONE counts as recorded.

    Each part reports its own items; they are returned in WORK_ORDER_LINE_TERMS_MISSING_ORDER, once each,
    because Part 5 puts SHIFTS in the place of Part 2's night shift and adds a reason for OVERTIME. A later
    part adds its own _part_N_missing_items."""
    found = {
        *_part_1_missing_items(row),
        *_part_2_missing_items(row),
        *_part_4_missing_items(row),
        *_part_5_missing_items(row),
    }
    return [item for item in WORK_ORDER_LINE_TERMS_MISSING_ORDER if item in found]


def _part_1_missing_items(row: dict[str, Any]) -> list[str]:
    """Part 1: the basis, the contracted time and rate, off days, overtime, breakdown, idle time, the
    minimum guarantee and part months."""
    basis = row.get("billing_uom_code")
    has_time_terms = basis in WORK_ORDER_LINE_BASES_WITH_TIME_TERMS
    is_month = basis == WORK_ORDER_LINE_BILLING_UOM_MONTH
    missing: list[str] = []
    if basis is None:
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_BILLING_BASIS)
    if has_time_terms and row.get("contracted_hours_per_billing_unit") is None:
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_CONTRACTED_HOURS)
    if is_month and row.get("contracted_working_days_per_month") is None:
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_CONTRACTED_WORKING_DAYS)
    if row.get("normal_rate_amount") is None:
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_NORMAL_RATE)
    if has_time_terms and row.get("weekly_off_day_codes") is None:
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_WEEKLY_OFF_DAYS)
    off_day = row.get("off_day_work_treatment_code")
    if has_time_terms and (
        off_day is None
        or (off_day == WORK_ORDER_LINE_OFF_DAY_HOLIDAY_RATE and row.get("holiday_rate_method_code") is None)
        # Charged at the overtime rate, which is not recorded yet.
        or (off_day == WORK_ORDER_LINE_OFF_DAY_OVERTIME_RATE and row.get("overtime_rate_method_code") is None)
    ):
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_OFF_DAY_WORK)
    overtime = row.get("overtime_rate_method_code")
    if has_time_terms and overtime is None:
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_OVERTIME)
    if is_month and overtime in _CHARGED_RATE_METHODS and (
        row.get("month_overtime_hours_basis_code") is None or row.get("month_overtime_counting_code") is None
    ):
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_MONTH_OVERTIME_METHOD)
    breakdown = row.get("breakdown_treatment_code")
    if has_time_terms and (
        breakdown is None
        or (breakdown == WORK_ORDER_LINE_BREAKDOWN_DEDUCT_AT_RATE and row.get("breakdown_rate_method_code") is None)
    ):
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_BREAKDOWN)
    idle = row.get("customer_idle_treatment_code")
    if idle is None or (idle == WORK_ORDER_LINE_IDLE_STANDBY_RATE and row.get("standby_rate_method_code") is None):
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_IDLE_TIME)
    if basis in WORK_ORDER_LINE_BASES_WITH_MINIMUM_GUARANTEE and row.get("minimum_guarantee_code") is None:
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_MINIMUM_GUARANTEE)
    if is_month and row.get("part_month_basis_code") is None:
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_PART_MONTH)
    return missing


def _part_2_missing_items(row: dict[str, Any]) -> list[str]:
    """Part 2: mobilisation and demobilisation (reported on the first period only), and fuel."""
    missing: list[str] = []
    # Mobilisation and demobilisation are the line's, recorded in its first period, so only that period
    # reports them - a later period holding nothing is not missing them (owner decision 8).
    if row.get("period_number") == 1:
        mobilisation = row.get("mobilisation_charge_code")
        if mobilisation is None or (
            mobilisation in WORK_ORDER_LINE_MOBILISATION_CHARGED_CODES
            and (
                row.get("mobilisation_charge_amount") is None
                or (
                    mobilisation == WORK_ORDER_LINE_MOBILISATION_CHARGED_CREDITED
                    and row.get("mobilisation_credit_after_months") is None
                )
            )
        ):
            missing.append(WORK_ORDER_LINE_TERMS_MISSING_MOBILISATION)
        demobilisation = row.get("demobilisation_charge_code")
        if demobilisation is None or (
            demobilisation in WORK_ORDER_LINE_DEMOBILISATION_CHARGED_CODES
            and (
                row.get("demobilisation_charge_amount") is None
                or (
                    demobilisation == WORK_ORDER_LINE_DEMOBILISATION_CHARGED_WAIVED
                    and row.get("demobilisation_waived_after_months") is None
                )
            )
        ):
            missing.append(WORK_ORDER_LINE_TERMS_MISSING_DEMOBILISATION)
    fuel = row.get("fuel_treatment_code")
    if (
        fuel is None
        or (
            fuel == WORK_ORDER_LINE_FUEL_PBL_CHARGED
            and (
                row.get("fuel_charge_method_code") is None
                or (
                    row.get("fuel_charge_method_code") == WORK_ORDER_LINE_FUEL_AGREED_RATE_PER_LITRE
                    and row.get("fuel_rate_per_litre_amount") is None
                )
            )
        )
        or (
            fuel == WORK_ORDER_LINE_FUEL_CUSTOMER_SUPPLIED
            and (
                row.get("fuel_litres_per_working_hour") is None
                or row.get("fuel_travel_allowance_code") is None
                or (
                    row.get("fuel_travel_allowance_code") == WORK_ORDER_LINE_FUEL_TRAVEL_LITRES_PER_HOUR
                    and row.get("fuel_litres_per_travel_hour") is None
                )
            )
        )
    ):
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_FUEL)
    return missing


def _part_4_missing_items(row: dict[str, Any]) -> list[str]:
    """Part 4: extra kilometres, and crew with how extra crew is charged. Both apply to every basis, so
    - like fuel - each is reported until answered, "not in the Work Order" being an answer."""
    missing: list[str] = []
    extra_km = row.get("extra_km_allowance_code")
    if extra_km is None or (
        extra_km in WORK_ORDER_LINE_EXTRA_KM_INCLUDED_CODES
        and (row.get("extra_km_included_km") is None or row.get("extra_km_rate_amount") is None)
    ):
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_EXTRA_KILOMETRES)
    crew = row.get("crew_code")
    extra_crew = row.get("extra_crew_charge_code")
    if crew is None or (
        crew == WORK_ORDER_LINE_CREW_STATED
        and (
            row.get("crew_operators_per_unit") is None
            or row.get("crew_helpers_per_unit") is None
            or extra_crew is None
            or (
                extra_crew == WORK_ORDER_LINE_EXTRA_CREW_RATE_PER_PERSON
                and (
                    row.get("extra_crew_operator_rate_amount") is None
                    or row.get("extra_crew_helper_rate_amount") is None
                )
            )
        )
    ):
        missing.append(WORK_ORDER_LINE_TERMS_MISSING_CREW)
    return missing


def _shift_details_missing(row: dict[str, Any]) -> bool:
    """Stated shifts still need each shift's hours; two or three also how they are charged, and each shift at
    its own rate every later shift's rate and, on a monthly line, its working days."""
    shifts = WORK_ORDER_LINE_SHIFTS_PER_DAY[row["shift_pattern_code"]]
    if any(row.get(f"shift_{shift}_hours") is None for shift in range(1, shifts + 1)):
        return True
    if shifts == 1:
        return False
    if row.get("shift_rate_code") is None:
        return True
    if row.get("shift_rate_code") != WORK_ORDER_LINE_SHIFT_RATE_PER_SHIFT:
        return False
    is_month = row.get("billing_uom_code") == WORK_ORDER_LINE_BILLING_UOM_MONTH
    return any(
        row.get(f"shift_{shift}_rate_method_code") is None
        or (is_month and row.get(f"shift_{shift}_working_days_per_month") is None)
        for shift in range(2, shifts + 1)
    )


def _part_5_missing_items(row: dict[str, Any]) -> list[str]:
    """Part 5: the shift pattern (in Part 2's night-shift place), how overtime is counted on several
    shifts (reported as OVERTIME, the card that asks it), and the crew's food, accommodation and travel."""
    missing: list[str] = []
    if row.get("billing_uom_code") in WORK_ORDER_LINE_BASES_WITH_TIME_TERMS:
        pattern = row.get("shift_pattern_code")
        if pattern is None or (pattern in WORK_ORDER_LINE_SHIFTS_PER_DAY and _shift_details_missing(row)):
            missing.append(WORK_ORDER_LINE_TERMS_MISSING_SHIFTS)
        if _asks_overtime_counted_per(row) and row.get("overtime_counted_per_code") is None:
            missing.append(WORK_ORDER_LINE_TERMS_MISSING_OVERTIME)
    for cell in WORK_ORDER_LINE_UPKEEP_CELLS:
        if not _upkeep_cell_applies(row, cell):
            continue
        columns = _upkeep_cell_columns(cell)
        code = row.get(columns[0])
        if code is None or (
            code == WORK_ORDER_LINE_UPKEEP_PROVIDED_AT_COST and any(row.get(column) is None for column in columns[1:])
        ):
            missing.append(WORK_ORDER_LINE_TERMS_MISSING_CREW_UPKEEP)
            break
    return missing


def _build_billing_term_period(
    row: dict[str, Any], next_effective_from: date | None
) -> WorkOrderLineBillingTermPeriodResponse:
    missing = _period_missing_items(row)
    hours = row.get("contracted_hours_per_billing_unit")
    days = row.get("contracted_working_days_per_month")
    derived_hours_per_day = (
        (Decimal(str(hours)) / Decimal(str(days))).quantize(Decimal("0.01"))
        if row.get("billing_uom_code") == WORK_ORDER_LINE_BILLING_UOM_MONTH and hours is not None and days is not None
        else None
    )
    return WorkOrderLineBillingTermPeriodResponse(
        term_public_id=row["term_public_id"],
        period_number=row["period_number"],
        effective_from=row.get("effective_from"),
        effective_to=(next_effective_from - timedelta(days=1)) if next_effective_from is not None else None,
        term_revision=row["term_revision"],
        currency_code=row["currency_code"],
        derived_hours_per_working_day=derived_hours_per_day,
        is_complete=not missing,
        missing_items=missing,
        updated_by=row.get("updated_by"),
        updated_by_display_name=row.get("updated_by_display_name"),
        updated_at=row["updated_at"],
        legacy_night_shift_not_in_work_order=bool(row.get("legacy_night_shift_not_in_work_order")),
        **{column: row.get(column) for column in _BILLING_TERM_RESPONSE_COLUMNS},
    )


def _build_line_billing_terms(
    line: dict[str, Any], periods: list[dict[str, Any]], *, today: date
) -> WorkOrderLineBillingTermsResponse:
    period_responses = [
        _build_billing_term_period(row, periods[index + 1]["effective_from"] if index + 1 < len(periods) else None)
        for index, row in enumerate(periods)
    ]
    current_period_number: int | None = None
    for period in period_responses:
        if period.effective_from is None or period.effective_from <= today:
            current_period_number = period.period_number
    if period_responses:
        found = {item for period in period_responses for item in period.missing_items}
        line_missing = [item for item in WORK_ORDER_LINE_TERMS_MISSING_ORDER if item in found]
    else:
        line_missing = [WORK_ORDER_LINE_TERMS_MISSING_NO_TERMS]
    return WorkOrderLineBillingTermsResponse(
        work_order_line_public_id=line["work_order_line_public_id"],
        line_number=line["line_number"],
        source_offer_line_public_id=line.get("source_offer_line_public_id"),
        quoted_uom=line["quoted_uom"],
        quoted_rate_amount=line.get("quoted_rate_amount"),
        current_period_number=current_period_number,
        periods=period_responses,
        terms_complete=not line_missing,
        line_missing_items=line_missing,
    )


def _work_order_billing_terms(
    db: Session, *, work_order_id: int, today: date
) -> list[WorkOrderLineBillingTermsResponse]:
    periods_by_line: dict[int, list[dict[str, Any]]] = {}
    for row in list_work_order_billing_term_rows(db, work_order_id=work_order_id):
        periods_by_line.setdefault(int(row["work_order_line_id"]), []).append(row)
    return [
        _build_line_billing_terms(line, periods_by_line.get(int(line["work_order_line_id"]), []), today=today)
        for line in list_work_order_billing_term_lines(db, work_order_id=work_order_id)
    ]


def list_work_order_billing_terms(
    db: Session, work_order_public_id: UUID, *, today: date | None = None
) -> list[WorkOrderLineBillingTermsResponse]:
    _, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    return _work_order_billing_terms(db, work_order_id=work_order_id, today=today or business_time.india_today())


def _check_period_start(
    period_number: int,
    effective_from: date | None,
    previous_from: date | None,
    next_from: date | None,
    *,
    contract_start: date | None = None,
) -> None:
    """Where a period may start, relative to the periods either side of it.

    Every refusal names the dates it is refusing over (owner decision 17, Slice 7D Part 3). These
    messages were generic until then; the rule they enforce is unchanged.
    """
    if period_number == 1:
        if effective_from is not None:
            with_contract = (
                f", on {format_contract_date(contract_start)}" if contract_start is not None else ""
            )
            raise WorkOrderValidationError(
                f"The first period starts with the contract{with_contract}, so it has no start date of its own. "
                f"Remove {format_contract_date(effective_from)} and leave the date empty."
            )
        return
    if effective_from is None:
        raise WorkOrderValidationError("A later period needs the date it starts from.")
    # The period before it ends the day before, and the first calendar date has no day before
    # (Part 1 review round 2). It names the date like every other refusal here (round 2, finding F-06).
    if effective_from <= date.min:
        raise WorkOrderValidationError(
            f"A period cannot start on {format_contract_date(effective_from)}. "
            "Enter the real date the later period starts from."
        )
    if previous_from is not None and effective_from <= previous_from:
        raise WorkOrderValidationError(
            f"This period starts on {format_contract_date(effective_from)}, "
            f"which is not after the previous period's start of {format_contract_date(previous_from)}."
        )
    if next_from is not None and effective_from >= next_from:
        raise WorkOrderValidationError(
            f"This period starts on {format_contract_date(effective_from)}, "
            f"which is not before the next period's start of {format_contract_date(next_from)}."
        )


def _check_period_start_against_contract(
    effective_from: date | None,
    *,
    contract_start: date | None,
    contract_end: date | None,
    contract_gaps: tuple[ContractGap, ...] = (),
) -> None:
    """Slice 7D Part 3: a later period cannot start outside the contract (owner decision 17).

    Period 1 has no date - it starts with the contract - so it can never be outside it and is not
    checked. The message names both dates: "This period starts on 1 May 2027, after the contract ends
    on 31 March 2027".
    """
    if effective_from is None:
        return
    message = date_outside_contract_message(
        effective_from,
        contract_start=contract_start,
        contract_end=contract_end,
        subject="This period starts on",
        gaps=contract_gaps,
    )
    if message is not None:
        raise WorkOrderValidationError(message)


def _changed_billing_term_fields(current: dict[str, Any] | None, values: dict[str, Any]) -> list[str]:
    """Terms whose stored value would change. For a new period, every term given a value."""
    baseline = current or {"breakdown_offset_by_same_day_overtime": False}
    return [column for column, new_value in values.items() if not _same_value(baseline.get(column), new_value)]


def _billing_terms_event_payload(
    *,
    line_public_id: UUID,
    term_public_id: str,
    period_number: int,
    effective_from: date | None,
    term_revision: int,
    billing_uom_code: str | None,
    changed_fields: list[str],
) -> dict[str, object]:
    # Codes, a date and public ids only: never an amount, rate or percentage.
    return {
        "work_order_line_public_id": str(line_public_id),
        "term_public_id": term_public_id,
        "period_number": period_number,
        "effective_from": effective_from.isoformat() if effective_from is not None else None,
        "term_revision": term_revision,
        "billing_uom_code": billing_uom_code,
        "changed_fields": changed_fields,
    }


def _lock_line_for_billing_terms(
    db: Session, *, work_order_public_id: UUID, line_public_id: UUID
) -> tuple[WorkOrderResponse, int, int]:
    """Lock the Work Order - serializing every change to any of its lines' terms - and resolve the line."""
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id, for_update=True)
    line_context = get_work_order_line_context(db, work_order_id=work_order_id, line_public_id=str(line_public_id))
    if line_context is None:
        raise WorkOrderLineNotFoundError("Work Order line not found on this Work Order.")
    if work_order.work_order_status_code in WORK_ORDER_LINE_BILLING_TERMS_LOCKED_WORK_ORDER_STATUSES:
        raise WorkOrderValidationError("This Work Order is closed. Its billing terms can no longer be changed.")
    return work_order, work_order_id, int(line_context["work_order_line_id"])


def _find_period(periods: list[dict[str, Any]], term_public_id: UUID) -> int:
    for index, row in enumerate(periods):
        if str(row["term_public_id"]) == str(term_public_id):
            return index
    raise WorkOrderLineBillingTermNotFoundError("Billing terms period not found on this Work Order line.")


def _captured_billing_terms_response(
    db: Session, *, work_order_id: int, line_public_id: UUID, event: dict[str, object] | None
) -> WorkOrderLineBillingTermsActionResponse:
    """The write response, read inside the caller's still-open transaction and under its lock, so it
    is exactly what this write produced and nothing that can fail runs after the write is permanent
    (the Slice 7C review round-1 lesson)."""
    lines = _work_order_billing_terms(db, work_order_id=work_order_id, today=business_time.india_today())
    entry = next(item for item in lines if str(item.work_order_line_public_id) == str(line_public_id))
    return WorkOrderLineBillingTermsActionResponse(line_billing_terms=entry, event=event)


def add_work_order_line_billing_terms_period(
    db: Session,
    *,
    work_order_public_id: UUID,
    line_public_id: UUID,
    payload: WorkOrderLineBillingTermsPeriodCreate,
    current_user_public_id: str | None,
) -> WorkOrderLineBillingTermsActionResponse:
    with rollback_on_error(db):
        work_order, work_order_id, work_order_line_id = _lock_line_for_billing_terms(
            db, work_order_public_id=work_order_public_id, line_public_id=line_public_id
        )
        periods = list_billing_term_rows_for_line(db, work_order_line_id=work_order_line_id)
        latest_revision = int(periods[-1]["term_revision"]) if periods else None
        if (
            payload.expected_period_count != len(periods)
            or payload.expected_latest_term_revision != latest_revision
        ):
            raise WorkOrderLineBillingTermsConflictError(_TERMS_CONFLICT_MESSAGE)
        period_number = len(periods) + 1
        contract_start, contract_end = contract_bounds_for_work_order(db, work_order_id=work_order_id)
        _check_period_start(
            period_number,
            payload.effective_from,
            periods[-1]["effective_from"] if periods else None,
            None,
            contract_start=contract_start,
        )
        _check_period_start_against_contract(
            payload.effective_from,
            contract_start=contract_start,
            contract_end=contract_end,
            contract_gaps=contract_gaps_for_work_order(db, work_order_id=work_order_id),
        )
        values = _normalize_billing_terms(payload, period_number=period_number)
        term_public_id = str(uuid4())
        insert_billing_term(
            db,
            public_id=term_public_id,
            work_order_line_id=work_order_line_id,
            period_number=period_number,
            values=values,
            current_user_public_id=current_user_public_id,
        )
        event = _record_billing_terms_event(
            db,
            work_order=work_order,
            event_name=WORK_ORDER_LINE_BILLING_TERMS_EVENT_PERIOD_ADDED,
            reason="Billing terms period added for a Work Order line.",
            current_user_public_id=current_user_public_id,
            payload=_billing_terms_event_payload(
                line_public_id=line_public_id,
                term_public_id=term_public_id,
                period_number=period_number,
                effective_from=values["effective_from"],
                term_revision=1,
                billing_uom_code=values["billing_uom_code"],
                changed_fields=_changed_billing_term_fields(None, values),
            ),
        )
        response = _captured_billing_terms_response(
            db, work_order_id=work_order_id, line_public_id=line_public_id, event=event
        )
        db.commit()
    return response


def update_work_order_line_billing_terms_period(
    db: Session,
    *,
    work_order_public_id: UUID,
    line_public_id: UUID,
    term_public_id: UUID,
    payload: WorkOrderLineBillingTermsPeriodUpdate,
    current_user_public_id: str | None,
) -> WorkOrderLineBillingTermsActionResponse:
    with rollback_on_error(db):
        work_order, work_order_id, work_order_line_id = _lock_line_for_billing_terms(
            db, work_order_public_id=work_order_public_id, line_public_id=line_public_id
        )
        periods = list_billing_term_rows_for_line(db, work_order_line_id=work_order_line_id)
        index = _find_period(periods, term_public_id)
        current = periods[index]
        if payload.expected_term_revision != int(current["term_revision"]):
            raise WorkOrderLineBillingTermsConflictError(_TERMS_CONFLICT_MESSAGE)
        contract_start, contract_end = contract_bounds_for_work_order(db, work_order_id=work_order_id)
        _check_period_start(
            int(current["period_number"]),
            payload.effective_from,
            periods[index - 1]["effective_from"] if index > 0 else None,
            periods[index + 1]["effective_from"] if index + 1 < len(periods) else None,
            contract_start=contract_start,
        )
        _check_period_start_against_contract(
            payload.effective_from,
            contract_start=contract_start,
            contract_end=contract_end,
            contract_gaps=contract_gaps_for_work_order(db, work_order_id=work_order_id),
        )
        values = _normalize_billing_terms(payload, period_number=int(current["period_number"]))
        changed_fields = _changed_billing_term_fields(current, values)

        if not changed_fields:
            # An identical save is not an edit: no revision bump and no event.
            response = _captured_billing_terms_response(
                db, work_order_id=work_order_id, line_public_id=line_public_id, event=None
            )
            db.rollback()
            return response

        updated = update_billing_term(
            db,
            term_id=int(current["term_id"]),
            expected_term_revision=int(current["term_revision"]),
            values=values,
            current_user_public_id=current_user_public_id,
        )
        if updated != 1:
            raise WorkOrderLineBillingTermsConflictError(_TERMS_CONFLICT_MESSAGE)
        event = _record_billing_terms_event(
            db,
            work_order=work_order,
            event_name=WORK_ORDER_LINE_BILLING_TERMS_EVENT_PERIOD_UPDATED,
            reason="Billing terms period changed for a Work Order line.",
            current_user_public_id=current_user_public_id,
            payload=_billing_terms_event_payload(
                line_public_id=line_public_id,
                term_public_id=str(current["term_public_id"]),
                period_number=int(current["period_number"]),
                effective_from=values["effective_from"],
                term_revision=int(current["term_revision"]) + 1,
                billing_uom_code=values["billing_uom_code"],
                changed_fields=changed_fields,
            ),
        )
        response = _captured_billing_terms_response(
            db, work_order_id=work_order_id, line_public_id=line_public_id, event=event
        )
        db.commit()
    return response


def remove_work_order_line_billing_terms_period(
    db: Session,
    *,
    work_order_public_id: UUID,
    line_public_id: UUID,
    term_public_id: UUID,
    expected_term_revision: int,
    current_user_public_id: str | None,
) -> WorkOrderLineBillingTermsActionResponse:
    with rollback_on_error(db):
        work_order, work_order_id, work_order_line_id = _lock_line_for_billing_terms(
            db, work_order_public_id=work_order_public_id, line_public_id=line_public_id
        )
        periods = list_billing_term_rows_for_line(db, work_order_line_id=work_order_line_id)
        index = _find_period(periods, term_public_id)
        current = periods[index]
        if len(periods) == 1:
            raise WorkOrderValidationError("A line's first period cannot be removed. Correct it instead.")
        if index != len(periods) - 1:
            raise WorkOrderValidationError("Only the latest period can be removed.")
        if expected_term_revision != int(current["term_revision"]):
            raise WorkOrderLineBillingTermsConflictError(_TERMS_CONFLICT_MESSAGE)
        deleted = delete_billing_term(
            db, term_id=int(current["term_id"]), expected_term_revision=int(current["term_revision"])
        )
        if deleted != 1:
            raise WorkOrderLineBillingTermsConflictError(_TERMS_CONFLICT_MESSAGE)
        event = _record_billing_terms_event(
            db,
            work_order=work_order,
            event_name=WORK_ORDER_LINE_BILLING_TERMS_EVENT_PERIOD_REMOVED,
            reason="Billing terms period removed from a Work Order line.",
            current_user_public_id=current_user_public_id,
            payload=_billing_terms_event_payload(
                line_public_id=line_public_id,
                term_public_id=str(current["term_public_id"]),
                period_number=int(current["period_number"]),
                effective_from=current.get("effective_from"),
                term_revision=int(current["term_revision"]),
                billing_uom_code=current.get("billing_uom_code"),
                changed_fields=[],
            ),
        )
        response = _captured_billing_terms_response(
            db, work_order_id=work_order_id, line_public_id=line_public_id, event=event
        )
        db.commit()
    return response


def _copy_result(
    *, line: dict[str, Any], outcome: str, periods_copied: int, replaced: int, message: str | None = None
) -> WorkOrderLineBillingTermsCopyResult:
    return WorkOrderLineBillingTermsCopyResult(
        work_order_line_public_id=line["work_order_line_public_id"],
        line_number=int(line["line_number"]),
        outcome=outcome,
        periods_copied=periods_copied,
        replaced_period_count=replaced,
        message=message,
    )


def _copy_source_line(
    by_public_id: dict[str, dict[str, Any]],
    *,
    line_public_id: UUID,
    payload: WorkOrderLineBillingTermsCopyRequest,
) -> tuple[dict[str, Any], list[str]]:
    """The line the terms come from, and the ids of the lines chosen to receive them, once the choice
    makes sense: each line chosen once, the source not among them, and every one on this Work Order."""
    source = by_public_id.get(str(line_public_id))
    if source is None:
        raise WorkOrderLineNotFoundError("Work Order line not found on this Work Order.")

    target_ids = [str(item.work_order_line_public_id) for item in payload.targets]
    if len(set(target_ids)) != len(target_ids):
        raise WorkOrderValidationError("A line was chosen more than once. Choose each line once.")
    if str(line_public_id) in target_ids:
        raise WorkOrderValidationError(
            "These terms come from this line, so it cannot also be one of the lines they are copied to."
        )
    unknown = [value for value in target_ids if value not in by_public_id]
    if unknown:
        raise WorkOrderLineNotFoundError("One of the chosen lines is not on this Work Order.")
    return source, target_ids


def _copy_source_periods(
    db: Session, *, source: dict[str, Any], payload: WorkOrderLineBillingTermsCopyRequest
) -> list[dict[str, Any]]:
    """The source line's periods, refused unless they are exactly the periods the caller saw."""
    source_periods = list_billing_term_rows_for_line(db, work_order_line_id=int(source["work_order_line_id"]))
    if not source_periods:
        raise WorkOrderValidationError(
            "This line has no billing terms to copy. Record its terms first, then copy them to other lines."
        )
    # EVERY source period is compared, not only a count and the latest revision: a change to an
    # earlier period leaves both of those identical, so the user could otherwise copy a version
    # they never saw (review round 1, finding F-01). The Work Order lock serializes writes but
    # cannot see a change that committed before this request took the lock - only this can.
    seen_source = [(str(item.term_public_id), item.term_revision) for item in payload.source_periods]
    live_source = [(str(row["term_public_id"]), int(row["term_revision"])) for row in source_periods]
    if seen_source != live_source:
        raise WorkOrderLineBillingTermsConflictError(_TERMS_CONFLICT_MESSAGE)
    return source_periods


def _copy_target_lines(
    db: Session,
    *,
    by_public_id: dict[str, dict[str, Any]],
    target_ids: list[str],
    payload: WorkOrderLineBillingTermsCopyRequest,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """The receiving lines and how many periods each holds now. Refused unless every line is exactly
    as the caller saw it, and unless every line that already has terms was confirmed for
    replacing."""
    targets = [by_public_id[value] for value in target_ids]
    live_target_periods = {
        str(target["work_order_line_public_id"]): list_billing_term_rows_for_line(
            db, work_order_line_id=int(target["work_order_line_id"])
        )
        for target in targets
    }
    existing_counts = {key: len(rows) for key, rows in live_target_periods.items()}

    # Each target is checked against what the caller actually saw of it, period by period - the
    # same comparison the source gets, and for the same reason. A count plus the latest revision
    # was the first design here, and it cannot see a change to an EARLIER period of a target, so
    # a concurrent edit would have been deleted by the replacement (round 1 fixed this on the
    # source and missed it here; round 2, finding F-07). A line that gained or lost terms is
    # caught by the same comparison, which is also what stops a line the user was never asked
    # about being replaced on the strength of another line's confirmation (finding F-02).
    for item in payload.targets:
        key = str(item.work_order_line_public_id)
        rows = live_target_periods[key]
        seen = [(str(period.term_public_id), period.term_revision) for period in item.observed_periods]
        live = [(str(row["term_public_id"]), int(row["term_revision"])) for row in rows]
        if seen != live:
            line_number = int(by_public_id[key]["line_number"])
            raise WorkOrderLineBillingTermsConflictError(
                f"Line {line_number}'s billing terms changed after you opened this page. "
                "Reload to see their version."
            )

    already_with_terms = [
        by_public_id[str(item.work_order_line_public_id)]
        for item in payload.targets
        if existing_counts[str(item.work_order_line_public_id)] and not item.replace_confirmed
    ]
    if already_with_terms:
        named = ", ".join(f"line {int(target['line_number'])}" for target in already_with_terms)
        raise WorkOrderValidationError(
            f"These lines already have billing terms: {named}. "
            "Confirm that you want to replace them before copying."
        )
    return targets, existing_counts


def _copy_terms_to_line(
    db: Session,
    *,
    work_order: WorkOrderResponse,
    target: dict[str, Any],
    replaced: int,
    source_periods: list[dict[str, Any]],
    source_line_public_id: UUID,
    current_user_public_id: str | None,
) -> tuple[WorkOrderLineBillingTermsCopyResult, dict[str, object] | None]:
    """Write every source period onto one receiving line, with the line's own event, in its own
    savepoint. Returns the line's result and its event; a line that could not be written returns no
    event, having rolled back alone, and the lines already copied stay."""
    target_line_id = int(target["work_order_line_id"])
    try:
        # One savepoint per line, so a line that cannot be written rolls back alone - its
        # rows and its event with it - and the lines already copied stay.
        with db.begin_nested():
            if replaced:
                delete_billing_terms_for_line(db, work_order_line_id=target_line_id)
            for period in source_periods:
                insert_billing_term(
                    db,
                    public_id=str(uuid4()),
                    work_order_line_id=target_line_id,
                    period_number=int(period["period_number"]),
                    # Copied column by column from a row that already passed every term rule,
                    # so nothing is re-derived and nothing can drift from the source.
                    values={column: period.get(column) for column in WORK_ORDER_LINE_BILLING_TERM_COLUMNS},
                    current_user_public_id=current_user_public_id,
                )
            line_event = _record_billing_terms_event(
                db,
                work_order=work_order,
                event_name=WORK_ORDER_LINE_BILLING_TERMS_EVENT_COPIED,
                reason="Billing terms copied to a Work Order line from another line.",
                current_user_public_id=current_user_public_id,
                payload={
                    "work_order_line_public_id": str(target["work_order_line_public_id"]),
                    "source_work_order_line_public_id": str(source_line_public_id),
                    "periods_copied": len(source_periods),
                    "replaced_period_count": replaced,
                    "billing_uom_code": source_periods[0].get("billing_uom_code"),
                },
            )
    except Exception as exc:  # noqa: BLE001 - one line's failure must not stop the others
        # A validation error's message is written for the user and is safe to show. Anything
        # else - a database error above all - is not: its text carries SQL and table names,
        # and CODING_STANDARDS.md forbids putting that in an API response. The line is still
        # named, so the user knows which one to look at.
        detail = str(exc) if isinstance(exc, WorkOrderValidationError) else "an unexpected error"
        return (
            _copy_result(
                line=target,
                outcome=WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_FAILED,
                periods_copied=0,
                replaced=0,
                message=f"Line {int(target['line_number'])} could not be written: {detail}",
            ),
            None,
        )
    return (
        _copy_result(
            line=target,
            outcome=(
                WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_REPLACED
                if replaced
                else WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_COPIED
            ),
            periods_copied=len(source_periods),
            replaced=replaced,
        ),
        line_event,
    )


def copy_work_order_line_billing_terms(
    db: Session,
    *,
    work_order_public_id: UUID,
    line_public_id: UUID,
    payload: WorkOrderLineBillingTermsCopyRequest,
    current_user_public_id: str | None,
) -> WorkOrderLineBillingTermsCopyResponse:
    """Copy every period of the source line's terms onto the chosen other lines of the same Work Order.

    The source is the line the user is standing on, so the source is chosen as freely as copying line
    by line would have been (owner decision 20). Every period is copied, not just the current one,
    because a rate that changes on a date should carry across with the rest (20c), and mobilisation
    and demobilisation - which period 1 alone holds - come with them (20d). Each receiving line stays
    editable afterwards.

    Ticking chooses; this is the write. A line left out is simply not touched, and its terms are never
    removed by leaving it out (20b). A line that already has terms is replaced only when the screen
    named it in its confirmation and the user agreed, which arrives as that target's own
    `replace_confirmed`; a populated target without it refuses the whole request and names those
    lines, so nothing recorded is replaced unasked.

    Every list the caller sends is compared period by period under the lock - the source's, and each
    target's. A count plus the latest revision is not enough for either: it cannot see a change to an
    earlier period, so a version the user never reviewed could be copied, or a concurrent edit to a
    target silently deleted (review rounds 1 and 2, findings F-01 and F-07).

    Each receiving line is written inside its own savepoint and records its own business event, so
    the trail reads as one change per line and a line that cannot be written is named in the result
    without stopping the others. With the Work Order locked for the whole operation no line can be
    changed underneath this call, so that per-line path is a guard rather than a common outcome; it
    is proved by a test that makes one line's write fail deliberately.
    """
    with rollback_on_error(db):
        work_order, work_order_id = _lock_work_order_for_contract_period(
            db, work_order_public_id, what_is_locked="Its billing terms"
        )
        lines = list_work_order_line_ids(db, work_order_id=work_order_id)
        by_public_id = {str(line["work_order_line_public_id"]): line for line in lines}
        source, target_ids = _copy_source_line(by_public_id, line_public_id=line_public_id, payload=payload)
        source_periods = _copy_source_periods(db, source=source, payload=payload)
        targets, existing_counts = _copy_target_lines(
            db, by_public_id=by_public_id, target_ids=target_ids, payload=payload
        )

        results: list[WorkOrderLineBillingTermsCopyResult] = []
        events: list[dict[str, Any]] = []
        for target in targets:
            result, line_event = _copy_terms_to_line(
                db,
                work_order=work_order,
                target=target,
                replaced=existing_counts[str(target["work_order_line_public_id"])],
                source_periods=source_periods,
                source_line_public_id=line_public_id,
                current_user_public_id=current_user_public_id,
            )
            if line_event is not None:
                events.append(line_event)
            results.append(result)

        # Read inside the still-open transaction and under the lock, so what comes back is exactly
        # what this operation produced (the Slice 7C review round-1 lesson).
        billing_terms = _work_order_billing_terms(db, work_order_id=work_order_id, today=business_time.india_today())
        response = WorkOrderLineBillingTermsCopyResponse(
            source_line_public_id=source["work_order_line_public_id"],
            source_line_number=int(source["line_number"]),
            results=results,
            billing_terms=billing_terms,
            events=events,
        )
        db.commit()
    return response
