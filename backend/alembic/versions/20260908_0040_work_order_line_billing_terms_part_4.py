"""work order line billing terms, part 4, and the holidays a Work Order names (Slice 7D Part 4)

Owner answers of 17-18 September 2026 (questions 21 to 26) and decisions 27 to 31 of 24 September
2026; see docs/agent/slices/slice-7d-part-4-remaining-billing-terms.md.

Two things, in the same pattern as Parts 2 and 3:

1. New columns on `crm_work_order_line_billing_term`, per period, because an amendment can change them
   from a date:

   - Extra kilometres (answer 22): not in the Work Order, or a number of kilometres included per day
     or per month, with a rate per extra kilometre.
   - Crew (answer 23, decision 28): not part of the Work Order (equipment only), or the number of
     operators and helpers per billing unit of the line - the line's own basis is the unit - and how
     crew beyond that number is charged: not in the Work Order, or a rate for each extra operator and
     a rate for each extra helper, per billing unit.

   The crew numbers are the one exception to "every number greater than zero": they are whole numbers,
   and one of the two may be zero ("2 operators, no helpers"), but not both, because a Work Order with
   no crew at all is recorded as equipment only (decision 28).

2. The holidays the Work Order names (answer 25, decisions 27 and 29), on the Work Order rather than a
   line: one list for every line. Two tables, because the answer and the dates are different things:

   - `crm_work_order_holiday_list`, one row per Work Order, holds the answer - "the Work Order names no
     holidays" (NONE) or "names these holidays" (LISTED). No row means not answered yet, which is
     reported missing; an empty list alone could not tell "none" from "not entered" (decision 29).
   - `crm_work_order_holiday`, one row per date, belongs to the list row. Its FK to the list means a
     date cannot exist without an answer beside it. That "names no holidays" holds no dates is a rule
     across the two tables, which a CHECK cannot see; the service owns it, as Part 3's service owns a
     line date being inside the contract.

   Weekly off days are not in the list: they are already recorded per period (Part 1). Work on any of
   these days is charged as each line's off-day choice says, which covers weekly offs and holidays
   alike (answer 24) - so there is no new rate here.

Nothing here is written by, or returned from, the frozen Accepted Offer -> Work Order handoff: the new
columns are on the billing-terms table and the holidays have their own tables, as 7C, 7D and Part 3
kept theirs.

Answers 21 and 26 add nothing to the database: billing frequency belongs to the equipment (8A, 8G), and
a monthly shortfall is deducted pro rata with no minimum - a rule for billing (8D), not a term.

Every new billing-term column is nullable. NULL means "not recorded yet" and is reported as missing;
NONE means "not in the Work Order", a recorded answer. Existing rows get NULL, so their lines report the
two new items as missing - correct, because those terms were never recorded.

Each CHECK is written to be TRUE or FALSE when a column it compares is empty, because a CHECK whose
expression is NULL passes (the Part 3 lesson: `NULL = 'X'` is NULL, not FALSE). Each numeric also
requires a finite value, because PostgreSQL `numeric` stores NaN and it compares greater than zero.

Also rewords WORK_ORDER_LINE_BILLING_TERMS_WRITE's description, which now governs the holiday list
too, and has since Part 2 and Part 3 governed more than its 0037 wording named. A permission description
must state what is actually enforced (Part 3 review round 1, finding F-04).

Downgrade drops the tables, the constraints and the columns, so Part 4 values are lost. That is
acceptable for a downgrade and is stated here rather than discovered.

Spelled out rather than imported from the application, so this revision stays a frozen historical
snapshot (the 20260908_0033 to 0039 convention).

Revision ID: 20260908_0040
Revises: 20260908_0039
Create Date: 2026-09-24
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0040"
down_revision: Union[str, None] = "20260908_0039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BILLING_TERM_TABLE = "crm_work_order_line_billing_term"
HOLIDAY_LIST_TABLE = "crm_work_order_holiday_list"
HOLIDAY_TABLE = "crm_work_order_holiday"

EXTRA_KM_INCLUDED_CODES = ("KM_PER_DAY", "KM_PER_MONTH")

NEW_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("extra_km_allowance_code", sa.String(length=50)),
    ("extra_km_included_km", sa.Numeric(precision=9, scale=2)),
    ("extra_km_rate_amount", sa.Numeric(precision=18, scale=2)),
    ("crew_code", sa.String(length=50)),
    ("crew_operators_per_unit", sa.Integer()),
    ("crew_helpers_per_unit", sa.Integer()),
    ("extra_crew_charge_code", sa.String(length=50)),
    ("extra_crew_operator_rate_amount", sa.Numeric(precision=18, scale=2)),
    ("extra_crew_helper_rate_amount", sa.Numeric(precision=18, scale=2)),
)

POSITIVE_COLUMNS = (
    "extra_km_included_km",
    "extra_km_rate_amount",
    "extra_crew_operator_rate_amount",
    "extra_crew_helper_rate_amount",
)
# Meaningless before a billing basis is chosen: the choices the user picks directly. A value belonging
# to one of them cannot appear before its own choice either, so listing the choices is enough.
BASIS_DEPENDENT_COLUMNS = ("extra_km_allowance_code", "crew_code")

BILLING_TERMS_PERMISSION_CODE = "WORK_ORDER_LINE_BILLING_TERMS_WRITE"
BILLING_TERMS_DESCRIPTION_BEFORE = (
    "Record or change a Work Order line's billing terms: rate, overtime, breakdown, idle time and periods."
)
BILLING_TERMS_DESCRIPTION_AFTER = (
    "Record or change a Work Order line's billing terms and their periods, copy them to other lines, "
    "and record the holidays the Work Order names."
)


def _quoted(codes: tuple[str, ...]) -> str:
    return ", ".join(f"'{code}'" for code in codes)


def _in(column: str, codes: tuple[str, ...]) -> str:
    """The column is empty or holds one of the codes."""
    return f"{column} IS NULL OR {column} IN ({_quoted(codes)})"


def _is(column: str, code: str) -> str:
    return f"{column} IS NOT DISTINCT FROM '{code}'"


def _one_of(column: str, codes: tuple[str, ...]) -> str:
    return f"COALESCE({column}, '') IN ({_quoted(codes)})"


def _all_null(columns: tuple[str, ...]) -> str:
    return " AND ".join(f"{column} IS NULL" for column in columns)


def _part_4_checks() -> list[tuple[str, str]]:
    return [
        # Code domains.
        ("ck_wol_term_extra_km_code", _in("extra_km_allowance_code", ("NONE", *EXTRA_KM_INCLUDED_CODES))),
        ("ck_wol_term_crew_code", _in("crew_code", ("NONE", "STATED"))),
        ("ck_wol_term_extra_crew_charge_code", _in("extra_crew_charge_code", ("NONE", "RATE_PER_PERSON"))),
        # Positive and finite.
        (
            "ck_wol_term_p4_positive_values",
            " AND ".join(
                f"({column} IS NULL OR ({column} > 0 AND {column} <> 'NaN'::numeric AND {column} <> 'Infinity'::numeric))"
                for column in POSITIVE_COLUMNS
            ),
        ),
        # Whole numbers of people, zero allowed for one of the two but not both (decision 28). Written
        # without arithmetic: adding the two overflowed an integer at the largest value the API accepts
        # (review round 1, finding F-01). "Not both zero" is "at least one is not recorded yet, or above
        # zero", which keeps a half-entered pair legal and is TRUE or FALSE, never NULL.
        (
            "ck_wol_term_crew_counts",
            "(crew_operators_per_unit IS NULL OR crew_operators_per_unit >= 0)"
            " AND (crew_helpers_per_unit IS NULL OR crew_helpers_per_unit >= 0)"
            " AND (crew_operators_per_unit IS NULL OR crew_operators_per_unit > 0"
            " OR crew_helpers_per_unit IS NULL OR crew_helpers_per_unit > 0)",
        ),
        # Extra kilometres: the kilometres included and the rate belong to an included allowance.
        # Absent while chosen is missing, not refused, so a period can be filled in over several saves.
        (
            "ck_wol_term_extra_km_values",
            f"(extra_km_included_km IS NULL AND extra_km_rate_amount IS NULL)"
            f" OR {_one_of('extra_km_allowance_code', EXTRA_KM_INCLUDED_CODES)}",
        ),
        # Crew: the numbers and how extra crew is charged belong to a Work Order that states its crew.
        (
            "ck_wol_term_crew_values",
            f"({_all_null(('crew_operators_per_unit', 'crew_helpers_per_unit', 'extra_crew_charge_code'))})"
            f" OR {_is('crew_code', 'STATED')}",
        ),
        # The two extra-crew rates belong to a charge per extra person.
        (
            "ck_wol_term_extra_crew_values",
            f"({_all_null(('extra_crew_operator_rate_amount', 'extra_crew_helper_rate_amount'))})"
            f" OR {_is('extra_crew_charge_code', 'RATE_PER_PERSON')}",
        ),
        # Neither is a term before the billing basis.
        (
            "ck_wol_term_p4_basis_chosen_first",
            f"billing_uom_code IS NOT NULL OR ({_all_null(BASIS_DEPENDENT_COLUMNS)})",
        ),
    ]


def upgrade() -> None:
    for column_name, column_type in NEW_COLUMNS:
        op.add_column(BILLING_TERM_TABLE, sa.Column(column_name, column_type, nullable=True))
    for name, sql in _part_4_checks():
        op.create_check_constraint(name, BILLING_TERM_TABLE, sa.text(sql))

    op.create_table(
        HOLIDAY_LIST_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("work_order_holiday_list_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        # NONE: the Work Order names no holidays. LISTED: it names the dates held below. Never null: a
        # Work Order whose answer is not recorded yet simply has no row (decision 29).
        sa.Column("holidays_answer_code", sa.String(length=50), nullable=False),
        sa.Column("list_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("work_order_holiday_list_public_id", name="uq_wo_holiday_list_public_id"),
        sa.UniqueConstraint("work_order_id", name="uq_wo_holiday_list_work_order"),
        sa.ForeignKeyConstraint(["work_order_id"], ["crm_work_order.id"], name="fk_wo_holiday_list_work_order"),
        sa.CheckConstraint("holidays_answer_code IN ('NONE', 'LISTED')", name="ck_wo_holiday_list_answer"),
        sa.CheckConstraint("list_version >= 1", name="ck_wo_holiday_list_version"),
    )

    op.create_table(
        HOLIDAY_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("work_order_holiday_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_holiday_list_id", sa.Integer(), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        # Weekly off days are recorded per period (Part 1), so the list holds the other two kinds.
        sa.Column("holiday_kind_code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Unicode(length=255), nullable=True),
        sa.UniqueConstraint("work_order_holiday_public_id", name="uq_wo_holiday_public_id"),
        # A date is a holiday once per Work Order: the list belongs to one Work Order.
        sa.UniqueConstraint("work_order_holiday_list_id", "holiday_date", name="uq_wo_holiday_date"),
        sa.ForeignKeyConstraint(
            ["work_order_holiday_list_id"], [f"{HOLIDAY_LIST_TABLE}.id"], name="fk_wo_holiday_list"
        ),
        sa.CheckConstraint("holiday_kind_code IN ('NATIONAL', 'FESTIVAL')", name="ck_wo_holiday_kind"),
    )

    op.get_bind().execute(
        sa.text("UPDATE authz_permission SET description = :description WHERE permission_code = :permission_code"),
        {"description": BILLING_TERMS_DESCRIPTION_AFTER, "permission_code": BILLING_TERMS_PERMISSION_CODE},
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("UPDATE authz_permission SET description = :description WHERE permission_code = :permission_code"),
        {"description": BILLING_TERMS_DESCRIPTION_BEFORE, "permission_code": BILLING_TERMS_PERMISSION_CODE},
    )
    op.drop_table(HOLIDAY_TABLE)
    op.drop_table(HOLIDAY_LIST_TABLE)
    for name, _sql in _part_4_checks():
        op.drop_constraint(name, BILLING_TERM_TABLE, type_="check")
    for column_name, _column_type in NEW_COLUMNS:
        op.drop_column(BILLING_TERM_TABLE, column_name)
