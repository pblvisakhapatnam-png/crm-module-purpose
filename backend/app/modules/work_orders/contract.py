"""Work Order handoff shell contract constants.

Slice 5A creates a thin Work Order shell from an Accepted Commercial Offer.
It preserves upstream Commercial Offer and line identities for later Equipment
Hiring, billing, GST/site, Customer Master, and release-control slices.
"""

from typing import Any

from app.modules.accounts.contract import (
    ADDRESS_TYPE_BILLING_DRAFT,
    ADDRESS_TYPE_REGISTERED_OFFICE,
    ADDRESS_TYPE_SITE,
    TAX_VERIFICATION_STATE_REJECTED_INCORRECT,
)
from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ACCEPTED_AWARDED,
    COMMERCIAL_OFFER_PURPOSE_BASE,
    COMMERCIAL_OFFER_PURPOSE_SUPPLEMENTARY,
)
from app.modules.work_orders.contract_period_rules import (
    CONTRACT_END_BASIS_CODES,
    CONTRACT_END_BASIS_FIXED_DATE,
    CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE,
)

WORK_ORDER_MODULE_NAME = "work_orders"
WORK_ORDER_TABLE = "crm_work_order"
WORK_ORDER_LINE_TABLE = "crm_work_order_line"
WORK_ORDER_RECORD_TYPE = "work_order"
WORK_ORDER_WORKFLOW_MODULE = "work_order"

WORK_ORDER_STATUS_DRAFT = "DRAFT"
WORK_ORDER_STATUS_HANDOFF_CREATED = "HANDOFF_CREATED"
WORK_ORDER_STATUS_EXECUTION_DEFERRED = "EXECUTION_DEFERRED"
WORK_ORDER_STATUS_CLOSED = "CLOSED"

WORK_ORDER_INITIAL_STATUS = WORK_ORDER_STATUS_HANDOFF_CREATED
WORK_ORDER_ALLOWED_STATUSES = (
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_STATUS_HANDOFF_CREATED,
    WORK_ORDER_STATUS_EXECUTION_DEFERRED,
    WORK_ORDER_STATUS_CLOSED,
)

WORK_ORDER_EVENT_CREATED = "WorkOrderCreated"
WORK_ORDER_EVENT_CREATED_FROM_COMMERCIAL_OFFER = "CommercialOfferConvertedToWorkOrder"

# CS-04 part 1 (HOF-2; the owner's decisions of 8 October 2026, recorded in the dated amendment of the frozen handoff
# contract). A Work Order is made from a Base Offer or a Supplementary Offer - never a Change Quotation, which is cited
# on a Work Order amendment - whose latest customer response is the acceptance or award. An offer line's quantity goes
# onto Work Orders once, whole or in parts; migration 20260908_0049's trigger holds the total under concurrent writes.
WORK_ORDER_HANDOFF_OFFER_PURPOSES = (COMMERCIAL_OFFER_PURPOSE_BASE, COMMERCIAL_OFFER_PURPOSE_SUPPLEMENTARY)
WORK_ORDER_HANDOFF_RESPONSE_OUTCOME = COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ACCEPTED_AWARDED
WORK_ORDER_LINE_QUANTITY_RULE = "ck_crm_work_order_line_within_offer_quantity"
# One customer order makes one Work Order: the customer's reference is required and used once per offer, compared
# without case or surrounding whitespace (the owner, 8 October 2026, after review round 3; the same migration's index).
# The whitespace is what the handoff's strip() removes - every character Python's str.isspace() accepts - as a
# PostgreSQL regular-expression class; migration 20260908_0049 holds the same class (review round 5: btrim() removes
# spaces only), and a test checks the two agree and cover str.isspace() exactly.
WORK_ORDER_REFERENCE_SPACE = r"\t\n\v\f\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000"
WORK_ORDER_CUSTOMER_REFERENCE_INDEX = "ux_crm_work_order_customer_reference"

# Slice 7C Work Order line operational detail. Recorded after handoff, in its own table, so the
# frozen handoff (docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md) neither
# writes nor returns any of it. See docs/agent/slices/slice-7c-work-order-line-operational-detail.md.
WORK_ORDER_LINE_DETAIL_TABLE = "crm_work_order_line_detail"

# The four billing bases WBT-001 settles. Hour-based billing uses actual hours, so a contracted-hours
# figure is refused on an HOUR line rather than stored where a billing engine could read it. Since
# Slice 7D the basis and contracted hours live in the line's billing terms, not in its 7C detail.
WORK_ORDER_LINE_BILLING_UOM_HOUR = "HOUR"
WORK_ORDER_LINE_BILLING_UOM_SHIFT = "SHIFT"
WORK_ORDER_LINE_BILLING_UOM_DAY = "DAY"
WORK_ORDER_LINE_BILLING_UOM_MONTH = "MONTH"
WORK_ORDER_LINE_BILLING_UOM_CODES = (
    WORK_ORDER_LINE_BILLING_UOM_HOUR,
    WORK_ORDER_LINE_BILLING_UOM_SHIFT,
    WORK_ORDER_LINE_BILLING_UOM_DAY,
    WORK_ORDER_LINE_BILLING_UOM_MONTH,
)
WORK_ORDER_LINE_BILLING_UOMS_WITH_CONTRACTED_HOURS = (
    WORK_ORDER_LINE_BILLING_UOM_SHIFT,
    WORK_ORDER_LINE_BILLING_UOM_DAY,
    WORK_ORDER_LINE_BILLING_UOM_MONTH,
)

# Account address types each reference may point at (owner decision 1: picked from the Account).
# Spelled with the Account module's own constants so a rename there cannot silently drift here.
WORK_ORDER_LINE_SITE_ADDRESS_TYPES = (ADDRESS_TYPE_SITE,)
WORK_ORDER_LINE_BILLING_ADDRESS_TYPES = (ADDRESS_TYPE_REGISTERED_OFFICE, ADDRESS_TYPE_BILLING_DRAFT)
WORK_ORDER_LINE_BILLING_GSTIN_EXCLUDED_STATES = (TAX_VERIFICATION_STATE_REJECTED_INCORRECT,)

# Changes are refused on a Closed Work Order: it has been completed and billed (owner, 14 Sep 2026).
# The mobilisation and e-invoice locks are later slices' to add.
WORK_ORDER_LINE_DETAIL_LOCKED_WORK_ORDER_STATUSES = (WORK_ORDER_STATUS_CLOSED,)

# Advisory completeness items, computed on every read and never stored. Nothing blocks on them in
# this slice; Work Order release (7B) will.
WORK_ORDER_LINE_DETAIL_MISSING_SITE_ADDRESS = "SITE_ADDRESS"
WORK_ORDER_LINE_DETAIL_MISSING_BILLING_GSTIN = "BILLING_GSTIN"
WORK_ORDER_LINE_DETAIL_MISSING_BILLING_ADDRESS = "BILLING_ADDRESS"

WORK_ORDER_LINE_DETAIL_EVENT_RECORDED = "WorkOrderLineDetailRecorded"
WORK_ORDER_LINE_DETAIL_EVENT_UPDATED = "WorkOrderLineDetailUpdated"

# Slice 7D Work Order line billing terms (Part 1). One row per period of one line, in its own table,
# so the frozen handoff neither writes nor returns any of it. Period 1 starts with the contract and
# has no date; each later period starts on its own date. See
# docs/agent/slices/slice-7d-work-order-line-billing-terms.md.
#
# Every term may be empty, meaning "not recorded yet" and reported as missing. The code NONE means
# "not in the Work Order": a recorded answer, never charged or deducted. Nothing is guessed (WBT-001).
WORK_ORDER_LINE_BILLING_TERM_TABLE = "crm_work_order_line_billing_term"
WORK_ORDER_LINE_BILLING_TERM_CURRENCY = "INR"

WORK_ORDER_LINE_BILLING_TERM_NONE = "NONE"
WORK_ORDER_LINE_BILLING_WEEKDAY_CODES = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")

WORK_ORDER_LINE_RATE_PER_HOUR = "RATE_PER_HOUR"
WORK_ORDER_LINE_RATE_PERCENT_OF_NORMAL = "PERCENT_OF_NORMAL"
WORK_ORDER_LINE_RATE_METHOD_CODES = (WORK_ORDER_LINE_RATE_PER_HOUR, WORK_ORDER_LINE_RATE_PERCENT_OF_NORMAL)
# Overtime has no separate treatment choice, so "not in the Work Order" is one of its methods.
WORK_ORDER_LINE_OVERTIME_METHOD_CODES = (WORK_ORDER_LINE_BILLING_TERM_NONE, *WORK_ORDER_LINE_RATE_METHOD_CODES)

WORK_ORDER_LINE_OFF_DAY_OVERTIME_RATE = "OVERTIME_RATE"
WORK_ORDER_LINE_OFF_DAY_HOLIDAY_RATE = "HOLIDAY_RATE"
WORK_ORDER_LINE_OFF_DAY_NORMAL_RATE = "NORMAL_RATE"
WORK_ORDER_LINE_OFF_DAY_WORK_CODES = (
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_OFF_DAY_OVERTIME_RATE,
    WORK_ORDER_LINE_OFF_DAY_HOLIDAY_RATE,
    WORK_ORDER_LINE_OFF_DAY_NORMAL_RATE,
)

WORK_ORDER_LINE_MONTH_OT_HOURS_BASIS_CODES = ("AVAILABLE_HOURS", "ENGINE_HOURS")
WORK_ORDER_LINE_MONTH_OT_COUNTING_CODES = ("WHOLE_MONTH", "DAY_BY_DAY")

WORK_ORDER_LINE_BREAKDOWN_REDUCE_BILLED_HOURS = "REDUCE_BILLED_HOURS"
WORK_ORDER_LINE_BREAKDOWN_DEDUCT_AT_RATE = "DEDUCT_AT_BREAKDOWN_RATE"
WORK_ORDER_LINE_BREAKDOWN_CODES = (
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_BREAKDOWN_REDUCE_BILLED_HOURS,
    WORK_ORDER_LINE_BREAKDOWN_DEDUCT_AT_RATE,
)

WORK_ORDER_LINE_IDLE_AS_WORKING_HOURS = "AS_WORKING_HOURS"
WORK_ORDER_LINE_IDLE_STANDBY_RATE = "STANDBY_RATE"
WORK_ORDER_LINE_IDLE_CODES = (
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_IDLE_AS_WORKING_HOURS,
    WORK_ORDER_LINE_IDLE_STANDBY_RATE,
)

WORK_ORDER_LINE_MINIMUM_UNITS_PER_MONTH = "UNITS_PER_MONTH"
WORK_ORDER_LINE_MINIMUM_GUARANTEE_CODES = (WORK_ORDER_LINE_BILLING_TERM_NONE, WORK_ORDER_LINE_MINIMUM_UNITS_PER_MONTH)

WORK_ORDER_LINE_PART_MONTH_CONTRACTED_WORKING_DAYS = "CONTRACTED_WORKING_DAYS"
WORK_ORDER_LINE_PART_MONTH_CODES = ("CALENDAR_DAYS", WORK_ORDER_LINE_PART_MONTH_CONTRACTED_WORKING_DAYS, "THIRTY_DAYS")

# Slice 7D Part 2 terms (owner decisions 8-12, 15 September 2026). Part 2's night shift became Part 5's
# shift pattern (below): a night shift was a second shift with a rate of its own.
#
# Mobilisation and demobilisation happen once for the line - the machine arrives once and leaves once -
# so they are recorded on period 1 only and a later period never carries or changes them (decision 8).
# "Credited after N months" and "waived after N months" are their own codes rather than a number left
# beside CHARGED, so "charged, with no credit back" is a recorded answer and a forgotten month count is
# missing. N is a whole number of months; how the months are counted belongs to billing (decision 9).
WORK_ORDER_LINE_MOBILISATION_CHARGED = "CHARGED"
WORK_ORDER_LINE_MOBILISATION_CHARGED_CREDITED = "CHARGED_CREDITED_AFTER_MONTHS"
WORK_ORDER_LINE_MOBILISATION_CODES = (
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_MOBILISATION_CHARGED,
    WORK_ORDER_LINE_MOBILISATION_CHARGED_CREDITED,
)
WORK_ORDER_LINE_MOBILISATION_CHARGED_CODES = (
    WORK_ORDER_LINE_MOBILISATION_CHARGED,
    WORK_ORDER_LINE_MOBILISATION_CHARGED_CREDITED,
)
WORK_ORDER_LINE_DEMOBILISATION_CHARGED = "CHARGED"
WORK_ORDER_LINE_DEMOBILISATION_CHARGED_WAIVED = "CHARGED_WAIVED_AFTER_MONTHS"
WORK_ORDER_LINE_DEMOBILISATION_CODES = (
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_DEMOBILISATION_CHARGED,
    WORK_ORDER_LINE_DEMOBILISATION_CHARGED_WAIVED,
)
WORK_ORDER_LINE_DEMOBILISATION_CHARGED_CODES = (
    WORK_ORDER_LINE_DEMOBILISATION_CHARGED,
    WORK_ORDER_LINE_DEMOBILISATION_CHARGED_WAIVED,
)
# The columns only period 1 may hold, because they describe the whole line (decision 8).
WORK_ORDER_LINE_FIRST_PERIOD_ONLY_TERMS = (
    "mobilisation_charge_code",
    "mobilisation_charge_amount",
    "mobilisation_credit_after_months",
    "demobilisation_charge_code",
    "demobilisation_charge_amount",
    "demobilisation_waived_after_months",
)

# Fuel. Where PBL supplies and charges for fuel, the charge is either at an agreed rate per litre or at
# actual cost (decision 11). Where the customer supplies it, the agreed litres per working hour - and
# per travel hour where the Work Order gives one - are recorded; measuring the excess belongs to log
# sheets and billing (decision 12).
WORK_ORDER_LINE_FUEL_PBL_INCLUDED = "PBL_SUPPLIED_INCLUDED"
WORK_ORDER_LINE_FUEL_PBL_CHARGED = "PBL_SUPPLIED_CHARGED"
WORK_ORDER_LINE_FUEL_CUSTOMER_SUPPLIED = "CUSTOMER_SUPPLIED"
WORK_ORDER_LINE_FUEL_TREATMENT_CODES = (
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_FUEL_PBL_INCLUDED,
    WORK_ORDER_LINE_FUEL_PBL_CHARGED,
    WORK_ORDER_LINE_FUEL_CUSTOMER_SUPPLIED,
)
WORK_ORDER_LINE_FUEL_AGREED_RATE_PER_LITRE = "AGREED_RATE_PER_LITRE"
WORK_ORDER_LINE_FUEL_ACTUAL_COST = "ACTUAL_COST"
WORK_ORDER_LINE_FUEL_CHARGE_METHOD_CODES = (
    WORK_ORDER_LINE_FUEL_AGREED_RATE_PER_LITRE,
    WORK_ORDER_LINE_FUEL_ACTUAL_COST,
)
WORK_ORDER_LINE_FUEL_TRAVEL_LITRES_PER_HOUR = "LITRES_PER_TRAVEL_HOUR"
WORK_ORDER_LINE_FUEL_TRAVEL_CODES = (
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_FUEL_TRAVEL_LITRES_PER_HOUR,
)

# Slice 7D Part 4 terms (owner answers 22 and 23 of 17-18 September 2026, decision 28 of 24 September).
# Both belong to each period and apply to every billing basis.
#
# Extra kilometres: not in the Work Order, or a number of kilometres included per day or per month,
# with a rate per extra kilometre. A period records one allowance, per day or per month.
WORK_ORDER_LINE_EXTRA_KM_PER_DAY = "KM_PER_DAY"
WORK_ORDER_LINE_EXTRA_KM_PER_MONTH = "KM_PER_MONTH"
WORK_ORDER_LINE_EXTRA_KM_INCLUDED_CODES = (WORK_ORDER_LINE_EXTRA_KM_PER_DAY, WORK_ORDER_LINE_EXTRA_KM_PER_MONTH)
WORK_ORDER_LINE_EXTRA_KM_CODES = (WORK_ORDER_LINE_BILLING_TERM_NONE, *WORK_ORDER_LINE_EXTRA_KM_INCLUDED_CODES)
# Crew: operators and helpers counted in numbers per billing unit of the line - the line's own basis is
# the unit. "Not part of the Work Order" is equipment only. The numbers are whole, and one of the two may
# be zero but not both; crew beyond them is charged at a rate for each extra operator and each extra
# helper, per billing unit, or is not in the Work Order. What the customer is charged for crew never
# sets what the crew are paid: that comes from PBL's HR terms (the standing rule recorded against 8B).
WORK_ORDER_LINE_CREW_STATED = "STATED"
WORK_ORDER_LINE_CREW_CODES = (WORK_ORDER_LINE_BILLING_TERM_NONE, WORK_ORDER_LINE_CREW_STATED)
WORK_ORDER_LINE_EXTRA_CREW_RATE_PER_PERSON = "RATE_PER_PERSON"
WORK_ORDER_LINE_EXTRA_CREW_CHARGE_CODES = (
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_EXTRA_CREW_RATE_PER_PERSON,
)

# Slice 7D Part 5 terms (owner's answers of 9 October 2026; slice-7d-part-5-crew-upkeep-and-shifts.md).
#
# The shift pattern, on shift, day and month lines: "not in the Work Order" (NONE) states no shifts at all; one,
# two or three shifts each state their hours in a day (review round 2, 7D5-R2-002: NONE is never read as a
# shift count). Several shifts are charged at one rate covering every shift, counted in the line's own billing
# unit, or each later shift at a rate of its own - per shift, per hour or as a percentage of the Work Order rate
# (Part 2's "% of normal", owner decision 7 of 14 September 2026) - with its own working days on a monthly line,
# as Part 2's night shift had (decision 10). The shifts of one day add up to no more than 24 hours.
WORK_ORDER_LINE_SHIFT_PATTERN_ONE = "ONE_SHIFT"
WORK_ORDER_LINE_SHIFT_PATTERN_TWO = "TWO_SHIFTS"
WORK_ORDER_LINE_SHIFT_PATTERN_THREE = "THREE_SHIFTS"
WORK_ORDER_LINE_SHIFT_PATTERN_CODES = (
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_SHIFT_PATTERN_ONE,
    WORK_ORDER_LINE_SHIFT_PATTERN_TWO,
    WORK_ORDER_LINE_SHIFT_PATTERN_THREE,
)
# The shifts a stated pattern has a day; NONE states none, so it has no entry.
WORK_ORDER_LINE_SHIFTS_PER_DAY = {
    WORK_ORDER_LINE_SHIFT_PATTERN_ONE: 1,
    WORK_ORDER_LINE_SHIFT_PATTERN_TWO: 2,
    WORK_ORDER_LINE_SHIFT_PATTERN_THREE: 3,
}
# Patterns with more than one shift: the rate choice and "per shift or per day" belong to them alone.
WORK_ORDER_LINE_SHIFT_PATTERNS_SEVERAL = (WORK_ORDER_LINE_SHIFT_PATTERN_TWO, WORK_ORDER_LINE_SHIFT_PATTERN_THREE)
WORK_ORDER_LINE_SHIFT_RATE_SAME_FOR_ALL = "SAME_FOR_ALL_SHIFTS"
WORK_ORDER_LINE_SHIFT_RATE_PER_SHIFT = "PER_SHIFT"
WORK_ORDER_LINE_SHIFT_RATE_CODES = (WORK_ORDER_LINE_SHIFT_RATE_SAME_FOR_ALL, WORK_ORDER_LINE_SHIFT_RATE_PER_SHIFT)
# A later shift's own rate: per shift, per hour or a percentage of the Work Order rate (Part 2's choices).
WORK_ORDER_LINE_SHIFT_RATE_METHOD_PER_SHIFT = "RATE_PER_SHIFT"
WORK_ORDER_LINE_SHIFT_RATE_METHOD_CODES = (
    WORK_ORDER_LINE_SHIFT_RATE_METHOD_PER_SHIFT,
    WORK_ORDER_LINE_RATE_PER_HOUR,
    WORK_ORDER_LINE_RATE_PERCENT_OF_NORMAL,
)
WORK_ORDER_LINE_SHIFT_RATE_AMOUNT_METHODS = (WORK_ORDER_LINE_SHIFT_RATE_METHOD_PER_SHIFT, WORK_ORDER_LINE_RATE_PER_HOUR)
WORK_ORDER_LINE_SHIFT_HOURS_IN_A_DAY = 24
# The later shifts that can have a rate of their own; shift 1 is always at the Work Order rate.
WORK_ORDER_LINE_LATER_SHIFTS = (2, 3)
# Overtime counted per shift or for the whole day, wherever the Work Order charges overtime on several shifts.
WORK_ORDER_LINE_OVERTIME_COUNTED_PER_CODES = ("PER_SHIFT", "PER_DAY")

# Crew food, accommodation and travel ("upkeep"), for operators and helpers separately, while the Work
# Order states its crew. Each is not in the Work Order, provided by the customer, or provided at a cost
# that the customer deducts from PBL's invoice or bills PBL for separately. Nothing is ever paid
# to the worker. Every cost records its basis, so no unit is assumed: food and accommodation per person per
# day or per month (the owner's answer); travel to and from the job per person per trip or per trip whatever
# the number of people; daily travel per person per day or per day whatever the number. The columns are
# upkeep_<item>_<role>_<field>.
WORK_ORDER_LINE_UPKEEP_PROVIDED = "PROVIDED"
WORK_ORDER_LINE_UPKEEP_PROVIDED_AT_COST = "PROVIDED_AT_COST"
WORK_ORDER_LINE_UPKEEP_CODES = (
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_UPKEEP_PROVIDED,
    WORK_ORDER_LINE_UPKEEP_PROVIDED_AT_COST,
)
WORK_ORDER_LINE_UPKEEP_RECOVERY_CODES = ("DEDUCTED_FROM_INVOICE", "BILLED_SEPARATELY")
# (item, the bases its cost may be stated on).
WORK_ORDER_LINE_UPKEEP_ITEMS = (
    ("food", ("PER_PERSON_PER_DAY", "PER_PERSON_PER_MONTH")),
    ("accommodation", ("PER_PERSON_PER_DAY", "PER_PERSON_PER_MONTH")),
    ("job_travel", ("PER_PERSON_PER_TRIP", "PER_TRIP")),
    ("daily_travel", ("PER_PERSON_PER_DAY", "PER_DAY")),
)
# (role, the crew-number column that says how many of them the Work Order states).
WORK_ORDER_LINE_UPKEEP_ROLES = (("operator", "crew_operators_per_unit"), ("helper", "crew_helpers_per_unit"))


def work_order_line_upkeep_cells() -> tuple[dict[str, Any], ...]:
    """One entry per item and role: the columns of that cell, and the bases its cost may be stated on."""
    cells = []
    for item, units in WORK_ORDER_LINE_UPKEEP_ITEMS:
        for role, count_column in WORK_ORDER_LINE_UPKEEP_ROLES:
            prefix = f"upkeep_{item}_{role}"
            cells.append(
                {
                    "item": item,
                    "role": role,
                    "count_column": count_column,
                    "units": units,
                    "code": f"{prefix}_code",
                    "amount": f"{prefix}_amount",
                    "unit": f"{prefix}_unit_code",
                    "recovery": f"{prefix}_recovery_code",
                }
            )
    return tuple(cells)


WORK_ORDER_LINE_UPKEEP_CELLS = work_order_line_upkeep_cells()
WORK_ORDER_LINE_UPKEEP_COLUMNS = tuple(
    column
    for cell in WORK_ORDER_LINE_UPKEEP_CELLS
    for column in (cell["code"], cell["amount"], cell["unit"], cell["recovery"])
)

# Which bases each group of terms applies to. Hour-based billing uses actual working hours only
# (WBT-001), so it has no overtime, breakdown, off-day or part-month terms. A monthly line records no
# minimum guarantee: a month short of its contracted hours is charged pro rata, with no minimum (owner,
# answer 26 of Slice 7D Part 4). Until then this comment said the monthly rate "already covers the
# contracted month", which contradicted that rule.
WORK_ORDER_LINE_BASES_WITH_TIME_TERMS = WORK_ORDER_LINE_BILLING_UOMS_WITH_CONTRACTED_HOURS
WORK_ORDER_LINE_BASES_WITH_MINIMUM_GUARANTEE = (
    WORK_ORDER_LINE_BILLING_UOM_HOUR,
    WORK_ORDER_LINE_BILLING_UOM_SHIFT,
    WORK_ORDER_LINE_BILLING_UOM_DAY,
)

# Advisory completeness items, in the order they are reported. Computed on read, never stored.
WORK_ORDER_LINE_TERMS_MISSING_NO_TERMS = "NO_TERMS"
WORK_ORDER_LINE_TERMS_MISSING_BILLING_BASIS = "BILLING_BASIS"
WORK_ORDER_LINE_TERMS_MISSING_CONTRACTED_HOURS = "CONTRACTED_HOURS"
WORK_ORDER_LINE_TERMS_MISSING_CONTRACTED_WORKING_DAYS = "CONTRACTED_WORKING_DAYS"
WORK_ORDER_LINE_TERMS_MISSING_NORMAL_RATE = "NORMAL_RATE"
WORK_ORDER_LINE_TERMS_MISSING_WEEKLY_OFF_DAYS = "WEEKLY_OFF_DAYS"
WORK_ORDER_LINE_TERMS_MISSING_OFF_DAY_WORK = "OFF_DAY_WORK"
WORK_ORDER_LINE_TERMS_MISSING_OVERTIME = "OVERTIME"
WORK_ORDER_LINE_TERMS_MISSING_MONTH_OVERTIME_METHOD = "MONTH_OVERTIME_METHOD"
WORK_ORDER_LINE_TERMS_MISSING_BREAKDOWN = "BREAKDOWN"
WORK_ORDER_LINE_TERMS_MISSING_IDLE_TIME = "IDLE_TIME"
WORK_ORDER_LINE_TERMS_MISSING_MINIMUM_GUARANTEE = "MINIMUM_GUARANTEE"
WORK_ORDER_LINE_TERMS_MISSING_PART_MONTH = "PART_MONTH"
# Part 2 items. Mobilisation and demobilisation are reported against period 1, the only period that
# holds them. SHIFTS took the place of Part 2's NIGHT_SHIFT in Part 5.
WORK_ORDER_LINE_TERMS_MISSING_SHIFTS = "SHIFTS"
WORK_ORDER_LINE_TERMS_MISSING_MOBILISATION = "MOBILISATION"
WORK_ORDER_LINE_TERMS_MISSING_DEMOBILISATION = "DEMOBILISATION"
WORK_ORDER_LINE_TERMS_MISSING_FUEL = "FUEL"
# Part 4 items.
WORK_ORDER_LINE_TERMS_MISSING_EXTRA_KILOMETRES = "EXTRA_KILOMETRES"
WORK_ORDER_LINE_TERMS_MISSING_CREW = "CREW"
# Part 5 item.
WORK_ORDER_LINE_TERMS_MISSING_CREW_UPKEEP = "CREW_UPKEEP"
WORK_ORDER_LINE_TERMS_MISSING_ORDER = (
    WORK_ORDER_LINE_TERMS_MISSING_NO_TERMS,
    WORK_ORDER_LINE_TERMS_MISSING_BILLING_BASIS,
    WORK_ORDER_LINE_TERMS_MISSING_CONTRACTED_HOURS,
    WORK_ORDER_LINE_TERMS_MISSING_CONTRACTED_WORKING_DAYS,
    WORK_ORDER_LINE_TERMS_MISSING_NORMAL_RATE,
    WORK_ORDER_LINE_TERMS_MISSING_WEEKLY_OFF_DAYS,
    WORK_ORDER_LINE_TERMS_MISSING_OFF_DAY_WORK,
    WORK_ORDER_LINE_TERMS_MISSING_OVERTIME,
    WORK_ORDER_LINE_TERMS_MISSING_MONTH_OVERTIME_METHOD,
    WORK_ORDER_LINE_TERMS_MISSING_BREAKDOWN,
    WORK_ORDER_LINE_TERMS_MISSING_IDLE_TIME,
    WORK_ORDER_LINE_TERMS_MISSING_MINIMUM_GUARANTEE,
    WORK_ORDER_LINE_TERMS_MISSING_PART_MONTH,
    WORK_ORDER_LINE_TERMS_MISSING_SHIFTS,
    WORK_ORDER_LINE_TERMS_MISSING_MOBILISATION,
    WORK_ORDER_LINE_TERMS_MISSING_DEMOBILISATION,
    WORK_ORDER_LINE_TERMS_MISSING_FUEL,
    WORK_ORDER_LINE_TERMS_MISSING_EXTRA_KILOMETRES,
    WORK_ORDER_LINE_TERMS_MISSING_CREW,
    WORK_ORDER_LINE_TERMS_MISSING_CREW_UPKEEP,
)

# Terms are refused on a Closed Work Order, as the 7C detail is. Locking at mobilisation and once
# billed belongs to those slices (owner decision 6).
WORK_ORDER_LINE_BILLING_TERMS_LOCKED_WORK_ORDER_STATUSES = (WORK_ORDER_STATUS_CLOSED,)

WORK_ORDER_LINE_BILLING_TERMS_EVENT_PERIOD_ADDED = "WorkOrderLineBillingTermsPeriodAdded"
WORK_ORDER_LINE_BILLING_TERMS_EVENT_PERIOD_UPDATED = "WorkOrderLineBillingTermsPeriodUpdated"
WORK_ORDER_LINE_BILLING_TERMS_EVENT_PERIOD_REMOVED = "WorkOrderLineBillingTermsPeriodRemoved"

# Slice 6O.2 Work Order Amendment intake foundation. An amendment is an intake/review
# record only - it is never applied to crm_work_order or crm_work_order_line by this
# foundation. Events for amendment actions use record_type=WORK_ORDER_RECORD_TYPE and the
# parent Work Order's own public_id, mirroring the existing subordinate-metadata event
# pattern used by commercial_offer_revision / commercial_offer_customer_response (see
# commercial_offers/service.py) rather than inventing a new event record_type.
WORK_ORDER_AMENDMENT_TABLE = "crm_work_order_amendment"
WORK_ORDER_AMENDMENT_LINE_TABLE = "crm_work_order_amendment_line"

WORK_ORDER_AMENDMENT_TYPE_ADMINISTRATIVE = "ADMINISTRATIVE"
WORK_ORDER_AMENDMENT_TYPE_COMMERCIAL = "COMMERCIAL"
WORK_ORDER_AMENDMENT_TYPE_MIXED = "MIXED"
WORK_ORDER_AMENDMENT_ALLOWED_TYPES = (
    WORK_ORDER_AMENDMENT_TYPE_ADMINISTRATIVE,
    WORK_ORDER_AMENDMENT_TYPE_COMMERCIAL,
    WORK_ORDER_AMENDMENT_TYPE_MIXED,
)
# Types that require an accepted commercial basis (a linked Supplementary Offer /
# Change Quotation) before the amendment can be moved to VALIDATED.
WORK_ORDER_AMENDMENT_COMMERCIAL_BASIS_REQUIRED_TYPES = (
    WORK_ORDER_AMENDMENT_TYPE_COMMERCIAL,
    WORK_ORDER_AMENDMENT_TYPE_MIXED,
)

WORK_ORDER_AMENDMENT_STATUS_RECEIVED = "RECEIVED"
WORK_ORDER_AMENDMENT_STATUS_UNDER_REVIEW = "UNDER_REVIEW"
WORK_ORDER_AMENDMENT_STATUS_VALIDATED = "VALIDATED"
WORK_ORDER_AMENDMENT_STATUS_REJECTED = "REJECTED"
WORK_ORDER_AMENDMENT_STATUS_CANCELLED = "CANCELLED"
WORK_ORDER_AMENDMENT_ALLOWED_STATUSES = (
    WORK_ORDER_AMENDMENT_STATUS_RECEIVED,
    WORK_ORDER_AMENDMENT_STATUS_UNDER_REVIEW,
    WORK_ORDER_AMENDMENT_STATUS_VALIDATED,
    WORK_ORDER_AMENDMENT_STATUS_REJECTED,
    WORK_ORDER_AMENDMENT_STATUS_CANCELLED,
)
WORK_ORDER_AMENDMENT_INITIAL_STATUS = WORK_ORDER_AMENDMENT_STATUS_RECEIVED
WORK_ORDER_AMENDMENT_TERMINAL_STATUSES = (
    WORK_ORDER_AMENDMENT_STATUS_VALIDATED,
    WORK_ORDER_AMENDMENT_STATUS_REJECTED,
    WORK_ORDER_AMENDMENT_STATUS_CANCELLED,
)
WORK_ORDER_AMENDMENT_EDITABLE_STATUSES = (
    WORK_ORDER_AMENDMENT_STATUS_RECEIVED,
    WORK_ORDER_AMENDMENT_STATUS_UNDER_REVIEW,
)
# Guarded transition matrix for POST .../amendments/{id}/decision. VALIDATED/REJECTED/
# CANCELLED are terminal for this foundation - no reopening or supersession workflow.
WORK_ORDER_AMENDMENT_ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    WORK_ORDER_AMENDMENT_STATUS_RECEIVED: (
        WORK_ORDER_AMENDMENT_STATUS_UNDER_REVIEW,
        WORK_ORDER_AMENDMENT_STATUS_REJECTED,
        WORK_ORDER_AMENDMENT_STATUS_CANCELLED,
    ),
    WORK_ORDER_AMENDMENT_STATUS_UNDER_REVIEW: (
        WORK_ORDER_AMENDMENT_STATUS_VALIDATED,
        WORK_ORDER_AMENDMENT_STATUS_REJECTED,
        WORK_ORDER_AMENDMENT_STATUS_CANCELLED,
    ),
}
# A reason is required when the decision moves the amendment to one of these statuses.
WORK_ORDER_AMENDMENT_DECISION_REASON_REQUIRED_STATUSES = (
    WORK_ORDER_AMENDMENT_STATUS_REJECTED,
    WORK_ORDER_AMENDMENT_STATUS_CANCELLED,
)

WORK_ORDER_AMENDMENT_LINE_ACTION_ADD = "ADD_LINE"
WORK_ORDER_AMENDMENT_LINE_ACTION_CHANGE = "CHANGE_LINE"
WORK_ORDER_AMENDMENT_LINE_ACTION_CANCEL = "CANCEL_LINE"
WORK_ORDER_AMENDMENT_LINE_ALLOWED_ACTIONS = (
    WORK_ORDER_AMENDMENT_LINE_ACTION_ADD,
    WORK_ORDER_AMENDMENT_LINE_ACTION_CHANGE,
    WORK_ORDER_AMENDMENT_LINE_ACTION_CANCEL,
)
# Actions that must reference an existing Work Order line (and therefore capture an
# original-value snapshot); ADD_LINE must not reference one.
WORK_ORDER_AMENDMENT_LINE_ACTIONS_REQUIRING_SOURCE_LINE = (
    WORK_ORDER_AMENDMENT_LINE_ACTION_CHANGE,
    WORK_ORDER_AMENDMENT_LINE_ACTION_CANCEL,
)

# A related Commercial Offer may be cited as an amendment's commercial basis only if it
# is a Slice 6O.1 related offer (never a Base Offer) and is currently Accepted. Accepted
# status is re-checked live at VALIDATED-transition time, not cached from intake time.
WORK_ORDER_AMENDMENT_SOURCE_OFFER_ELIGIBLE_PURPOSES = ("SUPPLEMENTARY", "CHANGE_QUOTATION")
WORK_ORDER_AMENDMENT_SOURCE_OFFER_ACCEPTED_STATUS = "ACCEPTED"

WORK_ORDER_AMENDMENT_EVENT_RECORDED = "WorkOrderAmendmentRecorded"
WORK_ORDER_AMENDMENT_EVENT_UPDATED = "WorkOrderAmendmentUpdated"
WORK_ORDER_AMENDMENT_EVENT_MOVED_UNDER_REVIEW = "WorkOrderAmendmentMovedUnderReview"
WORK_ORDER_AMENDMENT_EVENT_VALIDATED = "WorkOrderAmendmentValidated"
WORK_ORDER_AMENDMENT_EVENT_REJECTED = "WorkOrderAmendmentRejected"
WORK_ORDER_AMENDMENT_EVENT_CANCELLED = "WorkOrderAmendmentCancelled"
WORK_ORDER_AMENDMENT_EVENT_LINE_ADDED = "WorkOrderAmendmentLineAdded"
WORK_ORDER_AMENDMENT_EVENT_LINE_UPDATED = "WorkOrderAmendmentLineUpdated"
WORK_ORDER_AMENDMENT_EVENT_LINE_REMOVED = "WorkOrderAmendmentLineRemoved"

WORK_ORDER_AMENDMENT_DECISION_EVENTS: dict[str, str] = {
    WORK_ORDER_AMENDMENT_STATUS_UNDER_REVIEW: WORK_ORDER_AMENDMENT_EVENT_MOVED_UNDER_REVIEW,
    WORK_ORDER_AMENDMENT_STATUS_VALIDATED: WORK_ORDER_AMENDMENT_EVENT_VALIDATED,
    WORK_ORDER_AMENDMENT_STATUS_REJECTED: WORK_ORDER_AMENDMENT_EVENT_REJECTED,
    WORK_ORDER_AMENDMENT_STATUS_CANCELLED: WORK_ORDER_AMENDMENT_EVENT_CANCELLED,
}

# --- Slice 7D Part 3: the contract period, extensions and line dates -------------------------------
#
# The Work Order holds the contract start and end dates; a line may carry its own dates inside that
# period, and a line left blank follows the Work Order (owner decision 13, 17 September 2026). Both
# live outside crm_work_order and crm_work_order_line, exactly as 7C's detail and 7D's terms do, so
# the frozen Accepted Offer -> Work Order handoff neither writes nor returns any of it.
#
# When equipment actually arrives and leaves is a different thing, and comes later from mobilisation
# and log sheets. Nothing here is that.
WORK_ORDER_CONTRACT_PERIOD_TABLE = "crm_work_order_contract_period"
WORK_ORDER_CONTRACT_EXTENSION_TABLE = "crm_work_order_contract_extension"

# How the end date was answered. Null is "not recorded yet" and is reported missing; UNTIL_WORK_COMPLETE
# is a recorded answer and is not, exactly as NONE is for a billing term (owner decision 14). The codes
# themselves live in contract_period_rules.py with the rules that read them, and are re-exported here so
# a reader of this contract file sees the whole term set in one place.
WORK_ORDER_CONTRACT_END_BASIS_FIXED_DATE = CONTRACT_END_BASIS_FIXED_DATE
WORK_ORDER_CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE = CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE
WORK_ORDER_CONTRACT_END_BASIS_CODES = CONTRACT_END_BASIS_CODES

# Advisory completeness, computed on read and never stored, as everywhere else in this module.
# "Until the work is complete" is a recorded answer, so CONTRACT_END is not missing for it - but the
# Work Order still cannot be closed until a firm date exists, which the response reports separately
# through needs_firm_end_date and the screen says in those words (owner decision 14). Refusing the
# closure itself belongs to the closure slice (8E) and is recorded there.
WORK_ORDER_CONTRACT_PERIOD_MISSING_START = "CONTRACT_START"
WORK_ORDER_CONTRACT_PERIOD_MISSING_END = "CONTRACT_END"
WORK_ORDER_CONTRACT_PERIOD_MISSING_ORDER = (
    WORK_ORDER_CONTRACT_PERIOD_MISSING_START,
    WORK_ORDER_CONTRACT_PERIOD_MISSING_END,
)

# Changes are refused on a Closed Work Order, as the 7C detail and 7D terms are. The contract start
# additionally locks at mobilisation, after which the end date moves only through an extension record
# (owner decision 19) - recorded, not enforced, because mobilisation does not exist yet.
WORK_ORDER_CONTRACT_PERIOD_LOCKED_WORK_ORDER_STATUSES = (WORK_ORDER_STATUS_CLOSED,)

WORK_ORDER_CONTRACT_PERIOD_EVENT_RECORDED = "WorkOrderContractPeriodRecorded"
WORK_ORDER_CONTRACT_PERIOD_EVENT_UPDATED = "WorkOrderContractPeriodUpdated"
WORK_ORDER_CONTRACT_EXTENSION_EVENT_RECORDED = "WorkOrderContractExtensionRecorded"
# The latest extension removed, putting the end back to what it was before (owner, 22 September
# 2026). The row goes; this event is what keeps the fact that it existed.
WORK_ORDER_CONTRACT_EXTENSION_EVENT_REMOVED = "WorkOrderContractExtensionRemoved"

# Copying one line's saved terms onto other lines of the same Work Order (owner decision 20). One
# event per receiving line, so the audit trail reads as one change per line rather than a single bulk
# action; a line that could not be written is named in the result without stopping the others.
WORK_ORDER_LINE_BILLING_TERMS_EVENT_COPIED = "WorkOrderLineBillingTermsCopied"

WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_COPIED = "COPIED"
WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_REPLACED = "REPLACED"
WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_FAILED = "FAILED"
WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOMES = (
    WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_COPIED,
    WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_REPLACED,
    WORK_ORDER_LINE_BILLING_TERMS_COPY_OUTCOME_FAILED,
)

# --- Slice 7D Part 4: the holidays a Work Order names, and since HOL-1 its changes to PBL's calendar --------------
#
# Slice 7D Part 4 recorded the national and festival holidays the customer's Work Order states, as one list on the
# Work Order for every line (decision 27). Since HOL-1 (owner, 2 October 2026) every Work Order inherits PBL's holiday
# calendar for each line's site state, and the list holds the Work Order's changes to it: a holiday added, or a
# calendar holiday made a working day, charged at the normal or the overtime rate (Q4). Weekly off days are recorded
# per billing-terms period (Part 1) and are not repeated here. A holiday is charged as each line's off-day choice says
# (answer 24).
#
# The answer beside the list is what tells "the Work Order follows PBL's calendar unchanged" from "not entered yet"
# (no answer recorded), which an empty list could not (decision 29). CALENDAR_CHANGED with no change entered is still
# missing. Advisory, like every other completeness report here: Work Order release (7B) will block on it.
WORK_ORDER_HOLIDAY_LIST_TABLE = "crm_work_order_holiday_list"
WORK_ORDER_HOLIDAY_TABLE = "crm_work_order_holiday"

WORK_ORDER_HOLIDAYS_CALENDAR_UNCHANGED = "CALENDAR_UNCHANGED"
WORK_ORDER_HOLIDAYS_CALENDAR_CHANGED = "CALENDAR_CHANGED"
WORK_ORDER_HOLIDAYS_ANSWER_CODES = (WORK_ORDER_HOLIDAYS_CALENDAR_UNCHANGED, WORK_ORDER_HOLIDAYS_CALENDAR_CHANGED)

WORK_ORDER_HOLIDAY_CHANGE_ADDED = "HOLIDAY_ADDED"
WORK_ORDER_HOLIDAY_CHANGE_WORKING_DAY = "WORKING_DAY"
WORK_ORDER_HOLIDAY_CHANGE_CODES = (WORK_ORDER_HOLIDAY_CHANGE_ADDED, WORK_ORDER_HOLIDAY_CHANGE_WORKING_DAY)

WORK_ORDER_HOLIDAY_KIND_NATIONAL = "NATIONAL"
WORK_ORDER_HOLIDAY_KIND_FESTIVAL = "FESTIVAL"
WORK_ORDER_HOLIDAY_KIND_CODES = (WORK_ORDER_HOLIDAY_KIND_NATIONAL, WORK_ORDER_HOLIDAY_KIND_FESTIVAL)

# How a calendar holiday the Work Order works is charged (Q4): as a normal day, or every hour at the line's own
# overtime rate (the owner's point 2, 2 October 2026).
WORK_ORDER_WORKING_DAY_NORMAL_RATE = "NORMAL_RATE"
WORK_ORDER_WORKING_DAY_OVERTIME_RATE = "OVERTIME_RATE"
WORK_ORDER_WORKING_DAY_RATE_CODES = (WORK_ORDER_WORKING_DAY_NORMAL_RATE, WORK_ORDER_WORKING_DAY_OVERTIME_RATE)

# A holiday added's description, or a working day's note: the column's length, checked by the service so the refusal
# names the date (HOL1-R3-001).
WORK_ORDER_HOLIDAY_DESCRIPTION_MAX_LENGTH = 255

WORK_ORDER_HOLIDAYS_MISSING = "HOLIDAYS"

WORK_ORDER_HOLIDAYS_EVENT_RECORDED = "WorkOrderHolidaysRecorded"
WORK_ORDER_HOLIDAYS_EVENT_UPDATED = "WorkOrderHolidaysUpdated"

# --- HOL-1: the holidays that apply (section 5.3) ----------------------------------------------------------------
WORK_ORDER_DAY_HOLIDAY = "HOLIDAY"
WORK_ORDER_DAY_WORKING = "WORKING_DAY"
WORK_ORDER_DAY_SOURCE_CALENDAR = "CALENDAR"
WORK_ORDER_DAY_SOURCE_WORK_ORDER = "WORK_ORDER"

# Why "the holidays that apply" cover what they do (1.2, point 9).
WORK_ORDER_HOLIDAY_PERIOD_NO_START = "NO_CONTRACT_START"
WORK_ORDER_HOLIDAY_PERIOD_OPEN_END = "OPEN_END"

# A line whose site state is not known shows the all-India holidays only (1.2, point 8).
WORK_ORDER_SITE_NOT_RECORDED = "SITE_NOT_RECORDED"
WORK_ORDER_SITE_STATE_NOT_RECOGNISED = "SITE_STATE_NOT_RECOGNISED"

# What a change does, where it does nothing more than the calendar (1.2, point 6).
WORK_ORDER_CHANGE_DOES_NOTHING = "DOES_NOTHING"
WORK_ORDER_CHANGE_ALREADY_IN_CALENDAR = "ALREADY_IN_CALENDAR"
