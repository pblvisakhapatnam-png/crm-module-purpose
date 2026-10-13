"""work order line billing terms, part 5: the shift pattern, and the crew's food, accommodation and travel
(Slice 7D Part 5)

The owner's answers of 9 October 2026; see docs/agent/slices/slice-7d-part-5-crew-upkeep-and-shifts.md. New
columns on `crm_work_order_line_billing_term`, per period, in the pattern of Parts 2 and 4. Recording only.

1. The shift pattern (shift, day and month lines). "Not in the Work Order" (NONE) states no shifts; one, two or
   three shifts each state their hours in a day; two or three are charged at one rate for every shift
   or each later shift at a rate of its own - per shift, per hour or a percentage of the Work Order rate (the
   rate the first, day shift is charged at: Part 2's PERCENT_OF_NORMAL, unchanged) with its own working days on
   a monthly line - and, where overtime is charged on them, whether it is counted per shift or for the whole
   day. The shifts of one day add up to no more than 24 hours.

   **These replace Part 2's night shift**, whose five columns are converted here and dropped. A night shift
   was a second shift with a rate of its own:

       night shift not recorded   -> shift pattern not recorded
       night shift NONE           -> shift pattern not recorded, asked again, and the old answer kept on the period
                                     as legacy_night_shift_not_in_work_order (see below)
       night shift charged        -> TWO_SHIFTS, PER_SHIFT: shift 2's rate method, value and working days carried;
                                     shift 2's hours from the night hours per billing unit (shift and day lines:
                                     the same; month lines: divided by the night working days); shift 1's hours
                                     from the contracted hours the same way

   The upgrade **refuses to run**, naming the periods, while a charged night shift on a monthly line holds
   hours with no working days, or hours that do not divide by them into an exact figure (two decimals), or
   would make two shifts longer than 24 hours. Shift 1's hours are filled in only where that division is
   exact, and left blank (reported missing) otherwise: the contracted hours themselves are unchanged, so
   nothing is lost.

   A night shift "not in the Work Order" said only that no second shift was charged. The new question is the whole
   pattern - none stated, or one, two or three shifts - and that answer cannot be read from it: the new NONE ("the
   Work Order states no shifts") would claim more than was recorded, and ONE_SHIFT more again (review round 3,
   7D5-R3-002). So the shift pattern is left not recorded: the period reports SHIFTS missing and the user answers the
   new question from the Work Order. The old answer is not lost: `legacy_night_shift_not_in_work_order` (boolean, false
   for every other row) keeps it on the period, the screen shows it beside the question, no write changes it, and
   downgrade restores NONE from it (review round 4, 7D5-R4-001). Nothing was charged under the old answer and nothing
   is under the new one. The upgrade also logs how many periods it re-asks, so the change is visible when it runs.

2. The crew's food, accommodation and travel - "upkeep" - for operators and for helpers, while the Work Order
   states its crew: each not in the Work Order, provided by the customer, or provided at a cost on a stated basis
   (food and accommodation per person per day or per month; travel to and from the job per person per trip or per
   trip; daily travel per person per day or per day), deducted from PBL's invoice or billed to PBL separately.
   Thirty-two columns, upkeep_<item>_<role>_<field>.

Every new column is nullable: NULL is "not recorded yet" and is reported missing; NONE is "not in the Work
Order", an answer. Existing rows get NULL for the upkeep, so a period whose crew is stated reports it missing -
correct, because it was never recorded.

Part 2's night-shift CHECKs are dropped. Two of them also covered other columns - `ck_wol_term_p2_positive_values`
(mobilisation and fuel amounts) and `ck_wol_term_p2_basis_chosen_first` (mobilisation, demobilisation, fuel) -
and PostgreSQL would drop each whole with a night column, silently losing those rules, so both are recreated
without the night columns first.

Each new CHECK is written to be TRUE or FALSE when a column it compares is empty, because a CHECK whose
expression is NULL passes; each numeric also requires a finite value, because PostgreSQL `numeric` stores NaN
and it compares greater than every number.

Downgrade converts back what Part 2 can hold - a night shift "not in the Work Order" from NONE, ONE_SHIFT (no second
shift) or the kept legacy answer while the pattern is still unanswered, and two shifts each at its own rate - and loses
three shifts, two at one rate, shift 1's hours, how overtime is counted on shifts and every upkeep term.
That is stated here rather than discovered.

Spelled out rather than imported from the application, so this revision stays a frozen historical snapshot
(the 20260908_0033 convention).

Revision ID: 20260908_0052
Revises: 20260908_0051
Create Date: 2026-10-09
"""

from __future__ import annotations

import logging
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0052"
down_revision: Union[str, None] = "20260908_0051"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BILLING_TERM_TABLE = "crm_work_order_line_billing_term"

SHIFT_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("shift_pattern_code", sa.String(length=50)),
    ("shift_1_hours", sa.Numeric(precision=4, scale=2)),
    ("shift_2_hours", sa.Numeric(precision=4, scale=2)),
    ("shift_3_hours", sa.Numeric(precision=4, scale=2)),
    ("shift_rate_code", sa.String(length=50)),
    ("shift_2_rate_method_code", sa.String(length=50)),
    ("shift_2_rate_amount", sa.Numeric(precision=18, scale=2)),
    ("shift_2_rate_percent", sa.Numeric(precision=7, scale=2)),
    ("shift_2_working_days_per_month", sa.Numeric(precision=5, scale=2)),
    ("shift_3_rate_method_code", sa.String(length=50)),
    ("shift_3_rate_amount", sa.Numeric(precision=18, scale=2)),
    ("shift_3_rate_percent", sa.Numeric(precision=7, scale=2)),
    ("shift_3_working_days_per_month", sa.Numeric(precision=5, scale=2)),
    ("overtime_counted_per_code", sa.String(length=50)),
)
SHIFT_COLUMN_NAMES = tuple(name for name, _type in SHIFT_COLUMNS)
# A Part 2 night shift "not in the Work Order", kept on the period it was recorded on (review round 4, 7D5-R4-001).
LEGACY_COLUMN = "legacy_night_shift_not_in_work_order"
SHIFT_RATE_METHODS = ("RATE_PER_SHIFT", "RATE_PER_HOUR", "PERCENT_OF_NORMAL")
SHIFT_AMOUNT_METHODS = ("RATE_PER_SHIFT", "RATE_PER_HOUR")
SHIFT_PATTERNS_STATED = ("ONE_SHIFT", "TWO_SHIFTS", "THREE_SHIFTS")
SHIFT_PATTERNS_SEVERAL = ("TWO_SHIFTS", "THREE_SHIFTS")
OVERTIME_CHARGED_METHODS = ("RATE_PER_HOUR", "PERCENT_OF_NORMAL")

# (item, the bases its cost may be stated on), (role, the crew number that says how many of them there are).
UPKEEP_ITEMS = (
    ("food", ("PER_PERSON_PER_DAY", "PER_PERSON_PER_MONTH")),
    ("accommodation", ("PER_PERSON_PER_DAY", "PER_PERSON_PER_MONTH")),
    ("job_travel", ("PER_PERSON_PER_TRIP", "PER_TRIP")),
    ("daily_travel", ("PER_PERSON_PER_DAY", "PER_DAY")),
)
UPKEEP_ROLES = (("operator", "crew_operators_per_unit"), ("helper", "crew_helpers_per_unit"))


def _upkeep_cells() -> list[dict[str, Any]]:
    cells = []
    for item, units in UPKEEP_ITEMS:
        for role, count_column in UPKEEP_ROLES:
            prefix = f"upkeep_{item}_{role}"
            cells.append(
                {
                    "count": count_column,
                    "units": units,
                    "code": f"{prefix}_code",
                    "amount": f"{prefix}_amount",
                    "unit": f"{prefix}_unit_code",
                    "recovery": f"{prefix}_recovery_code",
                }
            )
    return cells


UPKEEP_CELLS = _upkeep_cells()


def _upkeep_columns() -> list[tuple[str, sa.types.TypeEngine]]:
    columns: list[tuple[str, sa.types.TypeEngine]] = []
    for cell in UPKEEP_CELLS:
        columns.append((str(cell["code"]), sa.String(length=50)))
        columns.append((str(cell["amount"]), sa.Numeric(precision=18, scale=2)))
        columns.append((str(cell["unit"]), sa.String(length=50)))
        columns.append((str(cell["recovery"]), sa.String(length=50)))
    return columns


UPKEEP_COLUMNS = tuple(_upkeep_columns())
UPKEEP_COLUMN_NAMES = tuple(name for name, _type in UPKEEP_COLUMNS)

# Part 2's night shift, exactly as 20260908_0038 created it.
NIGHT_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("night_shift_rate_method_code", sa.String(length=50)),
    ("night_shift_rate_amount", sa.Numeric(precision=18, scale=2)),
    ("night_shift_rate_percent", sa.Numeric(precision=7, scale=2)),
    ("night_shift_contracted_hours", sa.Numeric(precision=9, scale=2)),
    ("night_shift_working_days_per_month", sa.Numeric(precision=5, scale=2)),
)
NIGHT_CHARGED_METHODS = ("RATE_PER_SHIFT", "RATE_PER_HOUR", "PERCENT_OF_NORMAL")
P2_POSITIVE_WITHOUT_NIGHT = (
    "mobilisation_charge_amount",
    "demobilisation_charge_amount",
    "fuel_rate_per_litre_amount",
    "fuel_litres_per_working_hour",
    "fuel_litres_per_travel_hour",
)
P2_POSITIVE_WITH_NIGHT = (
    "night_shift_rate_amount",
    "night_shift_rate_percent",
    "night_shift_contracted_hours",
    "night_shift_working_days_per_month",
    *P2_POSITIVE_WITHOUT_NIGHT,
)
P2_BASIS_DEPENDENT_WITHOUT_NIGHT = ("mobilisation_charge_code", "demobilisation_charge_code", "fuel_treatment_code")
P2_BASIS_DEPENDENT_WITH_NIGHT = ("night_shift_rate_method_code", *P2_BASIS_DEPENDENT_WITHOUT_NIGHT)
NIGHT_NOT_HOUR_COLUMNS = tuple(name for name, _type in NIGHT_COLUMNS)


def _quoted(codes: tuple[str, ...]) -> str:
    return ", ".join(f"'{code}'" for code in codes)


def _in(column: str, codes: tuple[str, ...]) -> str:
    """The column is empty or holds one of the codes."""
    return f"({column} IS NULL OR {column} IN ({_quoted(codes)}))"


def _is(column: str, code: str) -> str:
    return f"{column} IS NOT DISTINCT FROM '{code}'"


def _one_of(column: str, codes: tuple[str, ...]) -> str:
    return f"COALESCE({column}, '') IN ({_quoted(codes)})"


def _all_null(columns: tuple[str, ...]) -> str:
    return "(" + " AND ".join(f"{column} IS NULL" for column in columns) + ")"


def _positive(columns: tuple[str, ...]) -> str:
    return " AND ".join(
        f"({column} IS NULL OR ({column} > 0 AND {column} <> 'NaN'::numeric AND {column} <> 'Infinity'::numeric))"
        for column in columns
    )


def _later_shift(shift: int) -> tuple[str, ...]:
    return (
        f"shift_{shift}_rate_method_code",
        f"shift_{shift}_rate_amount",
        f"shift_{shift}_rate_percent",
        f"shift_{shift}_working_days_per_month",
    )


def _later_shift_value(shift: int) -> str:
    """A later shift's rate: one value, the one its method asks for, given with it."""
    method, amount, percent = f"shift_{shift}_rate_method_code", f"shift_{shift}_rate_amount", f"shift_{shift}_rate_percent"
    return (
        f"(({method} IS NULL AND {amount} IS NULL AND {percent} IS NULL)"
        f" OR ({_one_of(method, SHIFT_AMOUNT_METHODS)} AND {amount} IS NOT NULL AND {percent} IS NULL)"
        f" OR ({_is(method, 'PERCENT_OF_NORMAL')} AND {percent} IS NOT NULL AND {amount} IS NULL))"
    )


def _part_5_checks() -> list[tuple[str, str]]:
    upkeep_codes = " AND ".join(
        f"{_in(str(cell['code']), ('NONE', 'PROVIDED', 'PROVIDED_AT_COST'))}"
        f" AND {_in(str(cell['unit']), cell['units'])}"
        f" AND {_in(str(cell['recovery']), ('DEDUCTED_FROM_INVOICE', 'BILLED_SEPARATELY'))}"
        for cell in UPKEEP_CELLS
    )
    cost_values = " AND ".join(
        f"({_all_null((str(cell['amount']), str(cell['unit']), str(cell['recovery'])))}"
        f" OR {_is(str(cell['code']), 'PROVIDED_AT_COST')})"
        for cell in UPKEEP_CELLS
    )
    role_present = " AND ".join(
        f"({role_count} IS DISTINCT FROM 0 OR "
        + _all_null(
            tuple(
                str(c)
                for cell in UPKEEP_CELLS
                if cell["count"] == role_count
                for c in (cell["code"], cell["amount"], cell["unit"], cell["recovery"])
            )
        )
        + ")"
        for _role, role_count in UPKEEP_ROLES
    )
    return [
        # The shift pattern: code domains.
        (
            "ck_wol_term_shift_codes",
            " AND ".join(
                (
                    _in("shift_pattern_code", ("NONE", *SHIFT_PATTERNS_STATED)),
                    _in("shift_rate_code", ("SAME_FOR_ALL_SHIFTS", "PER_SHIFT")),
                    _in("shift_2_rate_method_code", SHIFT_RATE_METHODS),
                    _in("shift_3_rate_method_code", SHIFT_RATE_METHODS),
                    _in("overtime_counted_per_code", ("PER_SHIFT", "PER_DAY")),
                )
            ),
        ),
        # Positive and finite.
        (
            "ck_wol_term_shift_positive_values",
            _positive(
                (
                    "shift_1_hours",
                    "shift_2_hours",
                    "shift_3_hours",
                    "shift_2_rate_amount",
                    "shift_2_rate_percent",
                    "shift_2_working_days_per_month",
                    "shift_3_rate_amount",
                    "shift_3_rate_percent",
                    "shift_3_working_days_per_month",
                )
            ),
        ),
        # The shifts of one day fit in it. An empty shift adds nothing.
        (
            "ck_wol_term_shift_hours_in_a_day",
            "COALESCE(shift_1_hours, 0) + COALESCE(shift_2_hours, 0) + COALESCE(shift_3_hours, 0) <= 24",
        ),
        # Each shift value only with its parent choice. Absent while chosen is missing, not refused.
        (
            "ck_wol_term_shift_values",
            f"({_one_of('shift_pattern_code', SHIFT_PATTERNS_STATED)} OR "
            f"{_all_null(tuple(c for c in SHIFT_COLUMN_NAMES if c != 'shift_pattern_code'))})"
            f" AND ({_one_of('shift_pattern_code', SHIFT_PATTERNS_SEVERAL)} OR "
            f"{_all_null(tuple(c for c in SHIFT_COLUMN_NAMES if c not in ('shift_pattern_code', 'shift_1_hours')))})"
            f" AND ({_is('shift_pattern_code', 'THREE_SHIFTS')} OR {_all_null(('shift_3_hours', *_later_shift(3)))})"
            f" AND ({_is('shift_rate_code', 'PER_SHIFT')} OR {_all_null((*_later_shift(2), *_later_shift(3)))})",
        ),
        # A later shift's rate carries exactly its value; its working days belong to a monthly line.
        (
            "ck_wol_term_shift_rates",
            f"{_later_shift_value(2)} AND {_later_shift_value(3)}"
            f" AND ({_is('billing_uom_code', 'MONTH')} OR "
            f"{_all_null(('shift_2_working_days_per_month', 'shift_3_working_days_per_month'))})",
        ),
        # Shift, day and month lines only, and never before the basis.
        (
            "ck_wol_term_shift_not_hourly",
            f"({_one_of('billing_uom_code', ('SHIFT', 'DAY', 'MONTH'))} OR {_all_null(SHIFT_COLUMN_NAMES)})",
        ),
        # Per shift or for the whole day: wherever overtime is charged on two or three shifts.
        (
            "ck_wol_term_overtime_counted_per",
            "overtime_counted_per_code IS NULL OR ("
            f"{_one_of('overtime_rate_method_code', OVERTIME_CHARGED_METHODS)}"
            f" AND {_one_of('shift_pattern_code', SHIFT_PATTERNS_SEVERAL)})",
        ),
        # The crew's upkeep: code domains; positive, finite costs; the cost's values only "at a cost"; only
        # while the crew is stated; nothing for a role the Work Order states 0 of.
        ("ck_wol_term_upkeep_codes", upkeep_codes),
        (
            "ck_wol_term_upkeep_positive_values",
            _positive(tuple(str(cell["amount"]) for cell in UPKEEP_CELLS)),
        ),
        ("ck_wol_term_upkeep_cost_values", cost_values),
        (
            "ck_wol_term_upkeep_needs_crew",
            f"{_is('crew_code', 'STATED')} OR {_all_null(UPKEEP_COLUMN_NAMES)}",
        ),
        ("ck_wol_term_upkeep_role_present", role_present),
    ]


def _part_2_checks_with_night() -> list[tuple[str, str]]:
    """Part 2's night-shift CHECKs and the two shared ones, exactly as 20260908_0038 wrote them."""
    return [
        ("ck_wol_term_night_shift_method", f"night_shift_rate_method_code IS NULL OR night_shift_rate_method_code IN ({_quoted(('NONE', *NIGHT_CHARGED_METHODS))})"),
        ("ck_wol_term_p2_positive_values", _positive(P2_POSITIVE_WITH_NIGHT)),
        (
            "ck_wol_term_night_shift_value",
            f"({_one_of('night_shift_rate_method_code', ('', 'NONE'))} "
            "AND night_shift_rate_amount IS NULL AND night_shift_rate_percent IS NULL)"
            f" OR ({_one_of('night_shift_rate_method_code', ('RATE_PER_SHIFT', 'RATE_PER_HOUR'))} "
            "AND night_shift_rate_amount IS NOT NULL AND night_shift_rate_percent IS NULL)"
            f" OR ({_is('night_shift_rate_method_code', 'PERCENT_OF_NORMAL')} "
            "AND night_shift_rate_percent IS NOT NULL AND night_shift_rate_amount IS NULL)",
        ),
        (
            "ck_wol_term_night_shift_hours_need_charge",
            "(night_shift_contracted_hours IS NULL AND night_shift_working_days_per_month IS NULL)"
            f" OR {_one_of('night_shift_rate_method_code', NIGHT_CHARGED_METHODS)}",
        ),
        (
            "ck_wol_term_p2_basis_chosen_first",
            "billing_uom_code IS NOT NULL OR " + _all_null(P2_BASIS_DEPENDENT_WITH_NIGHT),
        ),
        (
            "ck_wol_term_p2_not_hourly",
            "billing_uom_code IS DISTINCT FROM 'HOUR' OR " + _all_null(NIGHT_NOT_HOUR_COLUMNS),
        ),
        (
            "ck_wol_term_p2_month_only",
            f"{_is('billing_uom_code', 'MONTH')} OR (night_shift_working_days_per_month IS NULL)",
        ),
    ]


def _part_2_checks_without_night() -> list[tuple[str, str]]:
    """The two shared Part 2 CHECKs, without the night columns."""
    return [
        ("ck_wol_term_p2_positive_values", _positive(P2_POSITIVE_WITHOUT_NIGHT)),
        (
            "ck_wol_term_p2_basis_chosen_first",
            "billing_uom_code IS NOT NULL OR " + _all_null(P2_BASIS_DEPENDENT_WITHOUT_NIGHT),
        ),
    ]


# A charged night shift's hours in one shift (a day), and the first shift's: shift and day lines count per
# billing unit, which is per shift or per day already; a monthly line counts per month, so divide by days.
NIGHT_PER_SHIFT = (
    "CASE WHEN t.billing_uom_code = 'MONTH' THEN ROUND(t.night_shift_contracted_hours / "
    "NULLIF(t.night_shift_working_days_per_month, 0), 2) ELSE t.night_shift_contracted_hours END"
)
FIRST_PER_SHIFT = (
    "CASE WHEN t.billing_uom_code = 'MONTH' THEN ROUND(t.contracted_hours_per_billing_unit / "
    "NULLIF(t.contracted_working_days_per_month, 0), 2) ELSE t.contracted_hours_per_billing_unit END"
)
FIRST_EXACT = (
    "(t.billing_uom_code <> 'MONTH' OR "
    f"({FIRST_PER_SHIFT}) * t.contracted_working_days_per_month = t.contracted_hours_per_billing_unit)"
)
NIGHT_CHARGED = f"t.night_shift_rate_method_code IN ({_quoted(NIGHT_CHARGED_METHODS)})"


def _refuse_unconvertible_night_shifts(connection: sa.engine.Connection) -> None:
    """Refuse, naming the periods, while a charged night shift cannot become a second shift exactly."""
    rows = connection.execute(
        sa.text(
            f"""
            SELECT wo.work_order_code, wol.line_number, t.period_number,
                   CASE
                     WHEN t.billing_uom_code = 'MONTH' AND t.night_shift_contracted_hours IS NOT NULL
                          AND t.night_shift_working_days_per_month IS NULL
                       THEN 'night-shift hours per month with no working days to divide them by'
                     WHEN t.billing_uom_code = 'MONTH' AND t.night_shift_contracted_hours IS NOT NULL
                          AND ({NIGHT_PER_SHIFT}) * t.night_shift_working_days_per_month <> t.night_shift_contracted_hours
                       THEN 'night-shift hours per month that do not divide by its working days into hours a day'
                     ELSE 'two shifts longer than 24 hours a day'
                   END AS reason
            FROM {BILLING_TERM_TABLE} t
            JOIN crm_work_order_line wol ON wol.id = t.work_order_line_id
            JOIN crm_work_order wo ON wo.id = wol.work_order_id
            WHERE {NIGHT_CHARGED}
              AND (
                (t.billing_uom_code = 'MONTH' AND t.night_shift_contracted_hours IS NOT NULL
                 AND (t.night_shift_working_days_per_month IS NULL
                      OR ({NIGHT_PER_SHIFT}) * t.night_shift_working_days_per_month <> t.night_shift_contracted_hours))
                OR COALESCE(({NIGHT_PER_SHIFT}), 0)
                   + COALESCE(CASE WHEN {FIRST_EXACT} THEN ({FIRST_PER_SHIFT}) END, 0) > 24
              )
            ORDER BY wo.work_order_code, wol.line_number, t.period_number
            """
        )
    ).all()
    if rows:
        named = "; ".join(
            f"{code or 'Work Order'} line {line} period {period}: {reason}" for code, line, period, reason in rows[:10]
        )
        more = f" (and {len(rows) - 10} more)" if len(rows) > 10 else ""
        raise RuntimeError(
            f"{len(rows)} billing-terms period(s) have a charged night shift that cannot become a second shift "
            f"exactly: {named}{more}. Correct the night-shift hours or working days on those periods, or record "
            "the night shift as not in the Work Order, then upgrade again."
        )


def upgrade() -> None:
    connection = op.get_bind()
    _refuse_unconvertible_night_shifts(connection)

    for name, column_type in (*SHIFT_COLUMNS, *UPKEEP_COLUMNS):
        op.add_column(BILLING_TERM_TABLE, sa.Column(name, column_type, nullable=True))
    op.add_column(
        BILLING_TERM_TABLE,
        sa.Column(LEGACY_COLUMN, sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    connection.execute(
        sa.text(f"UPDATE {BILLING_TERM_TABLE} SET {LEGACY_COLUMN} = TRUE WHERE night_shift_rate_method_code = 'NONE'")
    )

    re_asked = connection.execute(
        sa.text(f"SELECT COUNT(*) FROM {BILLING_TERM_TABLE} WHERE night_shift_rate_method_code = 'NONE'")
    ).scalar_one()
    if re_asked:
        logging.getLogger("alembic.runtime.migration").warning(
            "%s billing-terms period(s) recorded the night shift as not in the Work Order. Their shift pattern is now "
            "not recorded and reported missing - answer it from the Work Order; the old answer is kept on each period "
            "as legacy_night_shift_not_in_work_order (Slice 7D Part 5).",
            re_asked,
        )
    connection.execute(
        sa.text(
            f"""
            UPDATE {BILLING_TERM_TABLE} t SET
                shift_pattern_code = CASE WHEN {NIGHT_CHARGED} THEN 'TWO_SHIFTS' END,
                shift_rate_code = CASE WHEN {NIGHT_CHARGED} THEN 'PER_SHIFT' END,
                shift_1_hours = CASE WHEN {NIGHT_CHARGED} AND {FIRST_EXACT} THEN ({FIRST_PER_SHIFT}) END,
                shift_2_hours = CASE WHEN {NIGHT_CHARGED} THEN ({NIGHT_PER_SHIFT}) END,
                shift_2_rate_method_code = CASE WHEN {NIGHT_CHARGED} THEN t.night_shift_rate_method_code END,
                shift_2_rate_amount = t.night_shift_rate_amount,
                shift_2_rate_percent = t.night_shift_rate_percent,
                shift_2_working_days_per_month = t.night_shift_working_days_per_month
            WHERE {NIGHT_CHARGED}
            """
        )
    )

    for name, _sql in _part_2_checks_with_night():
        op.drop_constraint(name, BILLING_TERM_TABLE, type_="check")
    for name, sql in _part_2_checks_without_night():
        op.create_check_constraint(name, BILLING_TERM_TABLE, sa.text(sql))
    for name, _column_type in NIGHT_COLUMNS:
        op.drop_column(BILLING_TERM_TABLE, name)
    for name, sql in _part_5_checks():
        op.create_check_constraint(name, BILLING_TERM_TABLE, sa.text(sql))


def downgrade() -> None:
    connection = op.get_bind()
    for name, column_type in NIGHT_COLUMNS:
        op.add_column(BILLING_TERM_TABLE, sa.Column(name, column_type, nullable=True))

    # Back into Part 2's shape what it can hold: a night shift "not in the Work Order" from NONE, ONE_SHIFT or the kept
    # legacy answer while the pattern is unanswered, and two shifts each at its own rate. A monthly
    # line's night hours were per month; shift 2's hours without its working days cannot be, and are lost.
    connection.execute(
        sa.text(
            f"""
            UPDATE {BILLING_TERM_TABLE} t SET
                night_shift_rate_method_code = CASE
                    WHEN t.shift_pattern_code IN ('NONE', 'ONE_SHIFT') THEN 'NONE'
                    WHEN t.shift_pattern_code IS NULL THEN 'NONE'
                    ELSE t.shift_2_rate_method_code
                END,
                night_shift_rate_amount = t.shift_2_rate_amount,
                night_shift_rate_percent = t.shift_2_rate_percent,
                night_shift_contracted_hours = CASE
                    WHEN t.billing_uom_code = 'MONTH' THEN t.shift_2_hours * t.shift_2_working_days_per_month
                    ELSE t.shift_2_hours
                END,
                night_shift_working_days_per_month = t.shift_2_working_days_per_month
            WHERE t.shift_pattern_code IN ('NONE', 'ONE_SHIFT')
               OR (t.shift_pattern_code IS NULL AND t.{LEGACY_COLUMN} AND t.billing_uom_code IN ('SHIFT', 'DAY', 'MONTH'))
               OR (t.shift_pattern_code = 'TWO_SHIFTS' AND t.shift_rate_code = 'PER_SHIFT'
                   AND t.shift_2_rate_method_code IS NOT NULL)
            """
        )
    )

    for name, _sql in _part_5_checks():
        op.drop_constraint(name, BILLING_TERM_TABLE, type_="check")
    for name, _sql in _part_2_checks_without_night():
        op.drop_constraint(name, BILLING_TERM_TABLE, type_="check")
    for name, sql in _part_2_checks_with_night():
        op.create_check_constraint(name, BILLING_TERM_TABLE, sa.text(sql))
    for name, _column_type in (*SHIFT_COLUMNS, *UPKEEP_COLUMNS):
        op.drop_column(BILLING_TERM_TABLE, name)
    op.drop_column(BILLING_TERM_TABLE, LEGACY_COLUMN)
