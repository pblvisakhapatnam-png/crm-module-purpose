"""work order line billing terms, part 2 (Slice 7D Part 2)

Adds the remaining `WBT-001` terms to `crm_work_order_line_billing_term`, in the same pattern as
Part 1: night / second shift, mobilisation, demobilisation and fuel. No table is created and nothing
in Part 1 changes.

Owner decisions of 15 September 2026:

- Night shift and fuel belong to each period, because an amendment can change a night rate or a fuel
  average from a date. Mobilisation and demobilisation are recorded once for the line - the machine
  arrives once and leaves once - so they live on period 1 only, and a CHECK keeps every later period
  free of them (decision 8).
- "Credited after N months" and "waived after N months" are their own codes rather than a number left
  beside CHARGED, so "charged, with no credit back" is a recorded answer and a forgotten month count
  is missing. N is a whole number of months; how the months are counted belongs to billing (9).
- A night shift has its own rate, its own contracted hours, and on a monthly line its own working days
  per month. Everything else - overtime, breakdown, idle time, off days, holiday work - follows the
  line's day-shift terms (10).
- Fuel supplied and charged by PBL is charged at an agreed rate per litre or at actual cost (11).
- Customer-supplied fuel records the agreed litres per working hour, and per travel hour where the
  Work Order gives one. Measuring the excess belongs to log sheets and billing (12).

Every new column is nullable. NULL means "not recorded yet" and is reported as missing; the code
`NONE` means "not in the Work Order", a recorded answer. Missing terms are never guessed (WBT-001).

Existing Part 1 rows get NULL for every new term, so their lines report the new items as missing.
That is correct: those terms were never recorded.

The new constraints are separate named CHECKs rather than edits to Part 1's, so this revision adds and
its downgrade removes exactly its own rules. Each is written to be TRUE or FALSE when the other column
is empty, because a CHECK whose expression is NULL passes; each numeric also requires a finite value,
because PostgreSQL `numeric` accepts NaN and Infinity and both compare greater than zero.

Downgrade drops the constraints and the columns, so Part 2 values are lost. That is acceptable for a
downgrade and is stated here rather than discovered.

Spelled out rather than imported from the application, so this revision stays a frozen historical
snapshot (the 20260908_0033 to 0037 convention).

Revision ID: 20260908_0038
Revises: 20260908_0037
Create Date: 2026-09-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0038"
down_revision: Union[str, None] = "20260908_0037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BILLING_TERM_TABLE = "crm_work_order_line_billing_term"

NIGHT_SHIFT_CHARGED_METHODS = ("RATE_PER_SHIFT", "RATE_PER_HOUR", "PERCENT_OF_NORMAL")
NIGHT_SHIFT_AMOUNT_METHODS = ("RATE_PER_SHIFT", "RATE_PER_HOUR")
MOBILISATION_CHARGED_CODES = ("CHARGED", "CHARGED_CREDITED_AFTER_MONTHS")
DEMOBILISATION_CHARGED_CODES = ("CHARGED", "CHARGED_WAIVED_AFTER_MONTHS")

NEW_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("night_shift_rate_method_code", sa.String(length=50)),
    ("night_shift_rate_amount", sa.Numeric(precision=18, scale=2)),
    ("night_shift_rate_percent", sa.Numeric(precision=7, scale=2)),
    ("night_shift_contracted_hours", sa.Numeric(precision=9, scale=2)),
    ("night_shift_working_days_per_month", sa.Numeric(precision=5, scale=2)),
    ("mobilisation_charge_code", sa.String(length=50)),
    ("mobilisation_charge_amount", sa.Numeric(precision=18, scale=2)),
    ("mobilisation_credit_after_months", sa.Integer()),
    ("demobilisation_charge_code", sa.String(length=50)),
    ("demobilisation_charge_amount", sa.Numeric(precision=18, scale=2)),
    ("demobilisation_waived_after_months", sa.Integer()),
    ("fuel_treatment_code", sa.String(length=50)),
    ("fuel_charge_method_code", sa.String(length=50)),
    ("fuel_rate_per_litre_amount", sa.Numeric(precision=18, scale=2)),
    ("fuel_litres_per_working_hour", sa.Numeric(precision=9, scale=2)),
    ("fuel_travel_allowance_code", sa.String(length=50)),
    ("fuel_litres_per_travel_hour", sa.Numeric(precision=9, scale=2)),
)

# The terms only period 1 may hold, because they describe the whole line.
FIRST_PERIOD_ONLY_COLUMNS = (
    "mobilisation_charge_code",
    "mobilisation_charge_amount",
    "mobilisation_credit_after_months",
    "demobilisation_charge_code",
    "demobilisation_charge_amount",
    "demobilisation_waived_after_months",
)
# Meaningless before a billing basis is chosen: the terms the user picks directly. A value belonging to
# one of them cannot appear before its own choice either, so listing the choices is enough.
BASIS_DEPENDENT_COLUMNS = (
    "night_shift_rate_method_code",
    "mobilisation_charge_code",
    "demobilisation_charge_code",
    "fuel_treatment_code",
)
# A night shift is a shift, so an hourly line - which bills the hours it worked, whenever they were
# worked (WBT-001) - carries none of it.
NOT_HOUR_COLUMNS = (
    "night_shift_rate_method_code",
    "night_shift_rate_amount",
    "night_shift_rate_percent",
    "night_shift_contracted_hours",
    "night_shift_working_days_per_month",
)
MONTH_ONLY_COLUMNS = ("night_shift_working_days_per_month",)
POSITIVE_COLUMNS = (
    "night_shift_rate_amount",
    "night_shift_rate_percent",
    "night_shift_contracted_hours",
    "night_shift_working_days_per_month",
    "mobilisation_charge_amount",
    "demobilisation_charge_amount",
    "fuel_rate_per_litre_amount",
    "fuel_litres_per_working_hour",
    "fuel_litres_per_travel_hour",
)
WHOLE_MONTH_COUNTS = ("mobilisation_credit_after_months", "demobilisation_waived_after_months")


def _quoted(codes: tuple[str, ...]) -> str:
    return ", ".join(f"'{code}'" for code in codes)


def _in(column: str, codes: tuple[str, ...]) -> str:
    """The column is empty or holds one of the codes."""
    return f"{column} IS NULL OR {column} IN ({_quoted(codes)})"


# A CHECK whose expression is NULL passes, so every comparison against a column that may be NULL is
# written to yield TRUE or FALSE: an empty column matches nothing.
def _is(column: str, code: str) -> str:
    return f"{column} IS NOT DISTINCT FROM '{code}'"


def _one_of(column: str, codes: tuple[str, ...]) -> str:
    return f"COALESCE({column}, '') IN ({_quoted(codes)})"


def _all_null(columns: tuple[str, ...]) -> str:
    return " AND ".join(f"{column} IS NULL" for column in columns)


def _part_2_checks() -> list[tuple[str, str]]:
    return [
        # Code domains.
        ("ck_wol_term_night_shift_method", _in("night_shift_rate_method_code", ("NONE", *NIGHT_SHIFT_CHARGED_METHODS))),
        ("ck_wol_term_mobilisation_code", _in("mobilisation_charge_code", ("NONE", *MOBILISATION_CHARGED_CODES))),
        ("ck_wol_term_demobilisation_code", _in("demobilisation_charge_code", ("NONE", *DEMOBILISATION_CHARGED_CODES))),
        (
            "ck_wol_term_fuel_treatment",
            _in(
                "fuel_treatment_code",
                ("NONE", "PBL_SUPPLIED_INCLUDED", "PBL_SUPPLIED_CHARGED", "CUSTOMER_SUPPLIED"),
            ),
        ),
        ("ck_wol_term_fuel_charge_method", _in("fuel_charge_method_code", ("AGREED_RATE_PER_LITRE", "ACTUAL_COST"))),
        ("ck_wol_term_fuel_travel_code", _in("fuel_travel_allowance_code", ("NONE", "LITRES_PER_TRAVEL_HOUR"))),
        # Positive and finite.
        (
            "ck_wol_term_p2_positive_values",
            " AND ".join(
                f"({column} IS NULL OR ({column} > 0 AND {column} <> 'NaN'::numeric AND {column} <> 'Infinity'::numeric))"
                for column in POSITIVE_COLUMNS
            ),
        ),
        # A whole number of months, at least one.
        ("ck_wol_term_p2_month_counts", " AND ".join(f"({column} IS NULL OR {column} >= 1)" for column in WHOLE_MONTH_COUNTS)),
        # The night-shift rate: one value, the one its method asks for.
        (
            "ck_wol_term_night_shift_value",
            f"({_one_of('night_shift_rate_method_code', ('', 'NONE'))} "
            "AND night_shift_rate_amount IS NULL AND night_shift_rate_percent IS NULL)"
            f" OR ({_one_of('night_shift_rate_method_code', NIGHT_SHIFT_AMOUNT_METHODS)} "
            "AND night_shift_rate_amount IS NOT NULL AND night_shift_rate_percent IS NULL)"
            f" OR ({_is('night_shift_rate_method_code', 'PERCENT_OF_NORMAL')} "
            "AND night_shift_rate_percent IS NOT NULL AND night_shift_rate_amount IS NULL)",
        ),
        # Its hours and working days belong to a charged night shift. Absent while charged is missing,
        # not refused, so a period can be filled in over several saves.
        (
            "ck_wol_term_night_shift_hours_need_charge",
            "(night_shift_contracted_hours IS NULL AND night_shift_working_days_per_month IS NULL)"
            f" OR {_one_of('night_shift_rate_method_code', NIGHT_SHIFT_CHARGED_METHODS)}",
        ),
        # Mobilisation and demobilisation: a charge only when charged, a month count only where the code
        # names one.
        (
            "ck_wol_term_mobilisation_values",
            f"(mobilisation_charge_amount IS NULL OR {_one_of('mobilisation_charge_code', MOBILISATION_CHARGED_CODES)})"
            " AND (mobilisation_credit_after_months IS NULL OR "
            f"{_is('mobilisation_charge_code', 'CHARGED_CREDITED_AFTER_MONTHS')})",
        ),
        (
            "ck_wol_term_demobilisation_values",
            f"(demobilisation_charge_amount IS NULL OR {_one_of('demobilisation_charge_code', DEMOBILISATION_CHARGED_CODES)})"
            " AND (demobilisation_waived_after_months IS NULL OR "
            f"{_is('demobilisation_charge_code', 'CHARGED_WAIVED_AFTER_MONTHS')})",
        ),
        # Only the line's first period holds them.
        (
            "ck_wol_term_first_period_only_terms",
            f"period_number = 1 OR ({_all_null(FIRST_PERIOD_ONLY_COLUMNS)})",
        ),
        # Fuel: each value present only where its own choice asks for it.
        (
            "ck_wol_term_fuel_values",
            f"(fuel_charge_method_code IS NULL OR {_is('fuel_treatment_code', 'PBL_SUPPLIED_CHARGED')})"
            " AND (fuel_rate_per_litre_amount IS NULL OR "
            f"{_is('fuel_charge_method_code', 'AGREED_RATE_PER_LITRE')})"
            " AND ((fuel_litres_per_working_hour IS NULL AND fuel_travel_allowance_code IS NULL) OR "
            f"{_is('fuel_treatment_code', 'CUSTOMER_SUPPLIED')})"
            " AND (fuel_litres_per_travel_hour IS NULL OR "
            f"{_is('fuel_travel_allowance_code', 'LITRES_PER_TRAVEL_HOUR')})",
        ),
        # Which of them apply to which basis.
        (
            "ck_wol_term_p2_basis_chosen_first",
            f"billing_uom_code IS NOT NULL OR ({_all_null(BASIS_DEPENDENT_COLUMNS)})",
        ),
        (
            "ck_wol_term_p2_not_hourly",
            f"billing_uom_code IS DISTINCT FROM 'HOUR' OR ({_all_null(NOT_HOUR_COLUMNS)})",
        ),
        (
            "ck_wol_term_p2_month_only",
            f"{_is('billing_uom_code', 'MONTH')} OR ({_all_null(MONTH_ONLY_COLUMNS)})",
        ),
    ]


def upgrade() -> None:
    for column_name, column_type in NEW_COLUMNS:
        op.add_column(BILLING_TERM_TABLE, sa.Column(column_name, column_type, nullable=True))
    for name, sql in _part_2_checks():
        op.create_check_constraint(name, BILLING_TERM_TABLE, sa.text(sql))


def downgrade() -> None:
    for name, _sql in _part_2_checks():
        op.drop_constraint(name, BILLING_TERM_TABLE, type_="check")
    for column_name, _column_type in NEW_COLUMNS:
        op.drop_column(BILLING_TERM_TABLE, column_name)
