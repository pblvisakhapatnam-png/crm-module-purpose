"""work order line billing terms (Slice 7D Part 1)

Adds `crm_work_order_line_billing_term`: the terms the customer's Work Order sets for one line, one
row per period. Period 1 starts with the contract and has no date of its own; each later period has
an `effective_from` date and replaces the previous one from that date (WBT-001 effective versions).

Part 1 of the term set, as agreed with the owner on 14 September 2026: billing basis and contracted
hours, contracted working days (monthly), the Work Order rate, weekly off days and work on an off
day or holiday, overtime and how monthly overtime is counted, breakdown and same-day offsetting,
customer-caused idle time, minimum guarantee and part-month charging. Night shift, mobilisation,
demobilisation and fuel are Part 2 and add columns in the same pattern.

Every term column is nullable. NULL means "not recorded yet" and is reported as missing; the code
`NONE` means "not in the Work Order", which is a recorded answer. Missing terms are never guessed
(WBT-001).

Slice 7C's `billing_uom_code` and `contracted_hours_per_billing_unit` move here. They are part of
the versioned term set in WBT-001, and a mid-contract amendment changes exactly them; on 7C's single
unversioned row they could not carry a start date. Upgrade copies each 7C row's values into period 1
of that line, then drops the columns and the three CHECK constraints that governed them.

One 0036 state cannot be carried: contracted hours with no billing basis. The 7C service never wrote
it, but 0036's CHECK allowed it (its expression is NULL there, and a NULL CHECK passes), and period 1
may hold no term before a basis is chosen. Rather than drop those hours silently, upgrade refuses to run
while such a row exists and names what to correct (review round 1). It refuses the same way for
contracted hours stored as NaN, which PostgreSQL numeric permits and 0036's `> 0` CHECK accepted,
because NaN compares greater than every number (review round 4).

Downgrade restores both columns from period 1 only, creating a 7C row where a line had terms but no
detail; later periods cannot fit a single row and are lost on downgrade.

Declared constraints mirror the service's rules so a direct INSERT cannot store a term a billing
engine would misread: code domains, positive values, INR only, the method/amount/percent rule of each
rate, the period-1-has-no-date rule, and which terms apply to which basis. Strictly increasing dates
across a line's periods need another row and are enforced by the service under the Work Order lock.

Also seeds WORK_ORDER_LINE_BILLING_TERMS_WRITE and rewords WORK_ORDER_LINE_DETAIL_WRITE, which no
longer governs the billing basis. Spelled out here rather than imported so this revision stays a
frozen historical snapshot (the 20260908_0033 to 0036 convention).

Revision ID: 20260908_0037
Revises: 20260908_0036
Create Date: 2026-09-14
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0037"
down_revision: Union[str, None] = "20260908_0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BILLING_TERM_TABLE = "crm_work_order_line_billing_term"
LINE_DETAIL_TABLE = "crm_work_order_line_detail"

ROLE_ADMIN = "ADMIN"
ROLE_SALES_USER = "SALES_USER"
ROLE_SALES_MANAGER = "SALES_MANAGER"
ROLE_OPERATIONS_USER = "OPERATIONS_USER"

PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    "WORK_ORDER_LINE_BILLING_TERMS_WRITE": (
        "Record or change a Work Order line's billing terms: rate, overtime, breakdown, idle time and periods.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_OPERATIONS_USER),
    ),
}
LINE_DETAIL_PERMISSION_CODE = "WORK_ORDER_LINE_DETAIL_WRITE"
LINE_DETAIL_DESCRIPTION_BEFORE = (
    "Record or change a Work Order line's site, billing GSTIN, billing address and billing basis."
)
LINE_DETAIL_DESCRIPTION_AFTER = (
    "Record or change a Work Order line's site, billing GSTIN, billing address and customer line reference."
)

# Which terms apply to which basis. "Not HOUR" terms are meaningless on hour-based billing, which uses
# actual working hours only (WBT-001); "MONTH only" terms describe a monthly contract.
NOT_HOUR_COLUMNS = (
    "contracted_hours_per_billing_unit",
    "weekly_off_day_codes",
    "off_day_work_treatment_code",
    "overtime_rate_method_code",
    "breakdown_treatment_code",
)
MONTH_ONLY_COLUMNS = (
    "contracted_working_days_per_month",
    "month_overtime_hours_basis_code",
    "month_overtime_counting_code",
    "part_month_basis_code",
)
# Every term that means nothing until a basis is chosen.
BASIS_DEPENDENT_COLUMNS = (
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
)
# (method column prefix, method codes that carry no value)
RATE_GROUPS = (
    ("holiday_rate", ()),
    ("overtime_rate", ("NONE",)),
    ("breakdown_rate", ()),
    ("standby_rate", ()),
)


def _quoted(codes: tuple[str, ...]) -> str:
    return ", ".join(f"'{code}'" for code in codes)


def _in(column: str, codes: tuple[str, ...]) -> str:
    """The column is empty or holds one of the codes."""
    return f"{column} IS NULL OR {column} IN ({_quoted(codes)})"


# A CHECK whose expression is NULL passes. Every comparison against a column that may be NULL is
# therefore written so it yields TRUE or FALSE, never NULL: `_is` and `_one_of` treat an empty
# column as matching nothing.
def _is(column: str, code: str) -> str:
    return f"{column} IS NOT DISTINCT FROM '{code}'"


def _one_of(column: str, codes: tuple[str, ...]) -> str:
    return f"COALESCE({column}, '') IN ({_quoted(codes)})"


CHARGED_OVERTIME = ("RATE_PER_HOUR", "PERCENT_OF_NORMAL")
DEDUCTING_BREAKDOWN = ("REDUCE_BILLED_HOURS", "DEDUCT_AT_BREAKDOWN_RATE")


def _check_constraints() -> list[sa.CheckConstraint]:
    checks: list[tuple[str, str]] = [
        ("ck_wol_term_period_number", "period_number >= 1"),
        ("ck_wol_term_revision", "term_revision >= 1"),
        (
            "ck_wol_term_first_period_has_no_date",
            # A later period never starts on the first calendar date: the period before it would have no
            # end date (review round 5; the service refuses the same date).
            "(period_number = 1 AND effective_from IS NULL) "
            "OR (period_number > 1 AND effective_from IS NOT NULL AND effective_from > DATE '0001-01-01')",
        ),
        ("ck_wol_term_currency_inr", "currency_code = 'INR'"),
        ("ck_wol_term_billing_uom", _in("billing_uom_code", ("HOUR", "SHIFT", "DAY", "MONTH"))),
        (
            "ck_wol_term_off_day_work",
            _in("off_day_work_treatment_code", ("NONE", "OVERTIME_RATE", "HOLIDAY_RATE", "NORMAL_RATE")),
        ),
        ("ck_wol_term_overtime_method", _in("overtime_rate_method_code", ("NONE", "RATE_PER_HOUR", "PERCENT_OF_NORMAL"))),
        ("ck_wol_term_holiday_method", _in("holiday_rate_method_code", ("RATE_PER_HOUR", "PERCENT_OF_NORMAL"))),
        ("ck_wol_term_breakdown_method", _in("breakdown_rate_method_code", ("RATE_PER_HOUR", "PERCENT_OF_NORMAL"))),
        ("ck_wol_term_standby_method", _in("standby_rate_method_code", ("RATE_PER_HOUR", "PERCENT_OF_NORMAL"))),
        ("ck_wol_term_month_ot_hours", _in("month_overtime_hours_basis_code", ("AVAILABLE_HOURS", "ENGINE_HOURS"))),
        ("ck_wol_term_month_ot_counting", _in("month_overtime_counting_code", ("WHOLE_MONTH", "DAY_BY_DAY"))),
        (
            "ck_wol_term_breakdown",
            _in("breakdown_treatment_code", ("NONE", "REDUCE_BILLED_HOURS", "DEDUCT_AT_BREAKDOWN_RATE")),
        ),
        ("ck_wol_term_idle", _in("customer_idle_treatment_code", ("NONE", "AS_WORKING_HOURS", "STANDBY_RATE"))),
        ("ck_wol_term_minimum_guarantee", _in("minimum_guarantee_code", ("NONE", "UNITS_PER_MONTH"))),
        (
            "ck_wol_term_part_month",
            _in("part_month_basis_code", ("CALENDAR_DAYS", "CONTRACTED_WORKING_DAYS", "THIRTY_DAYS")),
        ),
        # One-dimensional (containment ignores shape, review round 4); array_ndims is NULL for the empty
        # array that records a 7-day week, so it is written to accept that.
        (
            "ck_wol_term_off_days",
            "weekly_off_day_codes IS NULL OR ("
            "COALESCE(array_ndims(weekly_off_day_codes), 1) = 1 "
            "AND weekly_off_day_codes <@ ARRAY['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']::varchar[] "
            "AND NOT weekly_off_day_codes @> ARRAY['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']::varchar[])",
        ),
        # Off-day work "at the overtime rate" needs an overtime rate that is not "not in the Work Order".
        (
            "ck_wol_term_off_day_overtime_needs_overtime",
            f"NOT {_is('off_day_work_treatment_code', 'OVERTIME_RATE')} "
            f"OR NOT {_is('overtime_rate_method_code', 'NONE')}",
        ),
        # Positive and finite: PostgreSQL numeric can hold NaN and Infinity, and both compare greater than
        # zero (review round 4).
        (
            "ck_wol_term_positive_values",
            " AND ".join(
                f"({column} IS NULL OR ({column} > 0 AND {column} <> 'NaN'::numeric AND {column} <> 'Infinity'::numeric))"
                for column in (
                    "contracted_hours_per_billing_unit",
                    "contracted_working_days_per_month",
                    "normal_rate_amount",
                    "minimum_billing_units_per_month",
                    "holiday_rate_amount",
                    "holiday_rate_percent",
                    "overtime_rate_amount",
                    "overtime_rate_percent",
                    "breakdown_rate_amount",
                    "breakdown_rate_percent",
                    "standby_rate_amount",
                    "standby_rate_percent",
                )
            ),
        ),
        # A dependent value is present exactly when its choice asks for it.
        (
            "ck_wol_term_holiday_method_needs_holiday_rate",
            f"holiday_rate_method_code IS NULL OR {_is('off_day_work_treatment_code', 'HOLIDAY_RATE')}",
        ),
        (
            "ck_wol_term_breakdown_method_needs_deduction_rate",
            f"breakdown_rate_method_code IS NULL OR {_is('breakdown_treatment_code', 'DEDUCT_AT_BREAKDOWN_RATE')}",
        ),
        (
            "ck_wol_term_standby_method_needs_standby_rate",
            f"standby_rate_method_code IS NULL OR {_is('customer_idle_treatment_code', 'STANDBY_RATE')}",
        ),
        (
            "ck_wol_term_minimum_units",
            f"({_is('minimum_guarantee_code', 'UNITS_PER_MONTH')} AND minimum_billing_units_per_month IS NOT NULL)"
            f" OR (NOT {_is('minimum_guarantee_code', 'UNITS_PER_MONTH')} AND minimum_billing_units_per_month IS NULL)",
        ),
        (
            "ck_wol_term_month_ot_needs_overtime",
            "(month_overtime_hours_basis_code IS NULL AND month_overtime_counting_code IS NULL) "
            f"OR {_one_of('overtime_rate_method_code', CHARGED_OVERTIME)}",
        ),
        (
            "ck_wol_term_offset_needs_deduction_and_overtime",
            "breakdown_offset_by_same_day_overtime = FALSE OR ("
            f"{_one_of('breakdown_treatment_code', DEDUCTING_BREAKDOWN)} "
            f"AND {_one_of('overtime_rate_method_code', CHARGED_OVERTIME)})",
        ),
        (
            "ck_wol_term_basis_chosen_first",
            "billing_uom_code IS NOT NULL OR ("
            + " AND ".join(f"{column} IS NULL" for column in BASIS_DEPENDENT_COLUMNS)
            + ")",
        ),
        (
            "ck_wol_term_not_hourly",
            "billing_uom_code IS DISTINCT FROM 'HOUR' OR ("
            + " AND ".join(f"{column} IS NULL" for column in NOT_HOUR_COLUMNS)
            + ")",
        ),
        (
            "ck_wol_term_month_only",
            f"{_is('billing_uom_code', 'MONTH')} OR ("
            + " AND ".join(f"{column} IS NULL" for column in MONTH_ONLY_COLUMNS)
            + ")",
        ),
        ("ck_wol_term_no_minimum_on_month", "billing_uom_code IS DISTINCT FROM 'MONTH' OR minimum_guarantee_code IS NULL"),
    ]
    for prefix, valueless_codes in RATE_GROUPS:
        method, amount, percent = f"{prefix}_method_code", f"{prefix}_amount", f"{prefix}_percent"
        valueless = f" OR {_one_of(method, valueless_codes)}" if valueless_codes else ""
        checks.append(
            (
                f"ck_wol_term_{prefix}_value",
                f"(({method} IS NULL{valueless}) AND {amount} IS NULL AND {percent} IS NULL)"
                f" OR ({_is(method, 'RATE_PER_HOUR')} AND {amount} IS NOT NULL AND {percent} IS NULL)"
                f" OR ({_is(method, 'PERCENT_OF_NORMAL')} AND {percent} IS NOT NULL AND {amount} IS NULL)",
            )
        )
    return [sa.CheckConstraint(sql, name=name) for name, sql in checks]


def _rate_columns(prefix: str) -> list[sa.Column]:
    return [
        sa.Column(f"{prefix}_method_code", sa.String(length=50), nullable=True),
        sa.Column(f"{prefix}_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column(f"{prefix}_percent", sa.Numeric(precision=7, scale=2), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        BILLING_TERM_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("work_order_line_billing_term_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_line_id", sa.Integer(), nullable=False),
        sa.Column("period_number", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("term_revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'INR'")),
        sa.Column("billing_uom_code", sa.String(length=50), nullable=True),
        sa.Column("contracted_hours_per_billing_unit", sa.Numeric(precision=9, scale=2), nullable=True),
        sa.Column("contracted_working_days_per_month", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("normal_rate_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("weekly_off_day_codes", postgresql.ARRAY(sa.String(length=3)), nullable=True),
        sa.Column("off_day_work_treatment_code", sa.String(length=50), nullable=True),
        *_rate_columns("holiday_rate"),
        *_rate_columns("overtime_rate"),
        sa.Column("month_overtime_hours_basis_code", sa.String(length=50), nullable=True),
        sa.Column("month_overtime_counting_code", sa.String(length=50), nullable=True),
        sa.Column("breakdown_treatment_code", sa.String(length=50), nullable=True),
        *_rate_columns("breakdown_rate"),
        sa.Column(
            "breakdown_offset_by_same_day_overtime", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")
        ),
        sa.Column("customer_idle_treatment_code", sa.String(length=50), nullable=True),
        *_rate_columns("standby_rate"),
        sa.Column("minimum_guarantee_code", sa.String(length=50), nullable=True),
        sa.Column("minimum_billing_units_per_month", sa.Numeric(precision=9, scale=2), nullable=True),
        sa.Column("part_month_basis_code", sa.String(length=50), nullable=True),
        sa.Column("term_notes", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("work_order_line_billing_term_public_id", name="uq_wol_term_public_id"),
        sa.UniqueConstraint("work_order_line_id", "period_number", name="uq_wol_term_line_period"),
        sa.ForeignKeyConstraint(["work_order_line_id"], ["crm_work_order_line.id"], name="fk_wol_term_work_order_line"),
        *_check_constraints(),
    )

    _move_basis_and_hours_from_line_detail()
    _seed_permissions()


def _move_basis_and_hours_from_line_detail() -> None:
    connection = op.get_bind()
    stranded = connection.execute(
        sa.text(
            f"SELECT COUNT(*) FROM {LINE_DETAIL_TABLE} "
            "WHERE billing_uom_code IS NULL AND contracted_hours_per_billing_unit IS NOT NULL"
        )
    ).scalar_one()
    if stranded:
        raise RuntimeError(
            f"{stranded} crm_work_order_line_detail row(s) have contracted hours but no billing basis. "
            "Billing terms cannot hold hours before a basis is chosen, so this upgrade would lose them. "
            "Set billing_uom_code on those rows, or clear contracted_hours_per_billing_unit, then upgrade again."
        )
    not_a_number = connection.execute(
        sa.text(
            f"SELECT COUNT(*) FROM {LINE_DETAIL_TABLE} "
            "WHERE contracted_hours_per_billing_unit = 'NaN'::numeric"
        )
    ).scalar_one()
    if not_a_number:
        raise RuntimeError(
            f"{not_a_number} crm_work_order_line_detail row(s) have contracted hours stored as NaN, which is not a "
            "number of hours. Set contracted_hours_per_billing_unit to the real value, or clear it, then upgrade again."
        )
    connection.execute(
        sa.text(
            f"""
            INSERT INTO {BILLING_TERM_TABLE} (
                work_order_line_billing_term_public_id, work_order_line_id, period_number, effective_from,
                term_revision, currency_code, billing_uom_code, contracted_hours_per_billing_unit,
                created_by, created_at, updated_by, updated_at
            )
            SELECT
                gen_random_uuid()::text, d.work_order_line_id, 1, NULL,
                1, 'INR', d.billing_uom_code,
                CASE WHEN d.billing_uom_code IN ('SHIFT', 'DAY', 'MONTH') THEN d.contracted_hours_per_billing_unit END,
                d.updated_by, d.updated_at, d.updated_by, d.updated_at
            FROM {LINE_DETAIL_TABLE} d
            WHERE d.billing_uom_code IS NOT NULL
            """
        )
    )
    for name in ("ck_wol_detail_billing_uom", "ck_wol_detail_hours_positive", "ck_wol_detail_hours_not_hourly"):
        op.drop_constraint(name, LINE_DETAIL_TABLE, type_="check")
    op.drop_column(LINE_DETAIL_TABLE, "contracted_hours_per_billing_unit")
    op.drop_column(LINE_DETAIL_TABLE, "billing_uom_code")


def _seed_permissions() -> None:
    """Insert the permission row and its role grants, as 20260908_0035 and 0036 do."""
    connection = op.get_bind()

    for permission_code, (description, granted_role_codes) in PERMISSION_SEED.items():
        connection.execute(
            sa.text(
                """
                INSERT INTO authz_permission (public_id, permission_code, description, is_active)
                VALUES (:public_id, :permission_code, :description, TRUE)
                """
            ),
            {"public_id": str(uuid4()), "permission_code": permission_code, "description": description},
        )

        permission_id = connection.execute(
            sa.text("SELECT id FROM authz_permission WHERE permission_code = :permission_code"),
            {"permission_code": permission_code},
        ).scalar_one()

        for role_code in granted_role_codes:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO authz_role_permission (public_id, role_code, permission_id, is_active)
                    VALUES (:public_id, :role_code, :permission_id, TRUE)
                    """
                ),
                {"public_id": str(uuid4()), "role_code": role_code, "permission_id": permission_id},
            )

    connection.execute(
        sa.text("UPDATE authz_permission SET description = :description WHERE permission_code = :permission_code"),
        {"description": LINE_DETAIL_DESCRIPTION_AFTER, "permission_code": LINE_DETAIL_PERMISSION_CODE},
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE authz_permission SET description = :description WHERE permission_code = :permission_code"),
        {"description": LINE_DETAIL_DESCRIPTION_BEFORE, "permission_code": LINE_DETAIL_PERMISSION_CODE},
    )
    codes = list(PERMISSION_SEED)
    connection.execute(
        sa.text(
            "DELETE FROM authz_role_permission WHERE permission_id IN "
            "(SELECT id FROM authz_permission WHERE permission_code = ANY(:codes))"
        ),
        {"codes": codes},
    )
    connection.execute(
        sa.text("DELETE FROM authz_permission WHERE permission_code = ANY(:codes)"),
        {"codes": codes},
    )

    op.add_column(LINE_DETAIL_TABLE, sa.Column("billing_uom_code", sa.String(length=50), nullable=True))
    op.add_column(
        LINE_DETAIL_TABLE,
        sa.Column("contracted_hours_per_billing_unit", sa.Numeric(precision=9, scale=2), nullable=True),
    )
    # Period 1 back onto the 7C row; a line with terms but no detail row gets one.
    connection.execute(
        sa.text(
            f"""
            UPDATE {LINE_DETAIL_TABLE} d
            SET billing_uom_code = t.billing_uom_code,
                contracted_hours_per_billing_unit = t.contracted_hours_per_billing_unit
            FROM {BILLING_TERM_TABLE} t
            WHERE t.work_order_line_id = d.work_order_line_id
              AND t.period_number = 1
            """
        )
    )
    connection.execute(
        sa.text(
            f"""
            INSERT INTO {LINE_DETAIL_TABLE} (
                work_order_line_detail_public_id, work_order_line_id, billing_uom_code,
                contracted_hours_per_billing_unit, detail_version, created_by, created_at, updated_by, updated_at
            )
            SELECT gen_random_uuid()::text, t.work_order_line_id, t.billing_uom_code,
                   t.contracted_hours_per_billing_unit, 1, t.updated_by, t.updated_at, t.updated_by, t.updated_at
            FROM {BILLING_TERM_TABLE} t
            WHERE t.period_number = 1
              AND t.billing_uom_code IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM {LINE_DETAIL_TABLE} d WHERE d.work_order_line_id = t.work_order_line_id)
            """
        )
    )
    op.create_check_constraint(
        "ck_wol_detail_billing_uom",
        LINE_DETAIL_TABLE,
        "billing_uom_code IS NULL OR billing_uom_code IN ('HOUR', 'SHIFT', 'DAY', 'MONTH')",
    )
    op.create_check_constraint(
        "ck_wol_detail_hours_positive",
        LINE_DETAIL_TABLE,
        "contracted_hours_per_billing_unit IS NULL OR contracted_hours_per_billing_unit > 0",
    )
    op.create_check_constraint(
        "ck_wol_detail_hours_not_hourly",
        LINE_DETAIL_TABLE,
        "NOT (billing_uom_code = 'HOUR' AND contracted_hours_per_billing_unit IS NOT NULL)",
    )

    op.drop_table(BILLING_TERM_TABLE)
