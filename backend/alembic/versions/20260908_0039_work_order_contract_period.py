"""work order contract period, extensions and line dates (Slice 7D Part 3)

The Work Order's contract start and end dates, the extensions that move the end date, and each
line's own dates inside that period. Owner decisions 13 to 20d of 17 September 2026; see
docs/agent/slices/slice-7d-part-3-contract-period.md.

Two new tables rather than columns on `crm_work_order`, deliberately and for the same reason 7C and
7D used their own tables: the Accepted Offer -> Work Order shell handoff writes `crm_work_order` and
its output is frozen (docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md).
Keeping the contract period outside it means the handoff insert, the handoff response and the Slice
6O.2 amendment snapshot are untouched by construction.

Extensions are their own table, one row per extension, so "previous end dates stay as history and
are never overwritten" (owner decision 15) holds by construction rather than by care. The row records
what the contract said before as well as after, so the trail reads without having to replay every
earlier row.

The line's own start and end dates go on `crm_work_order_line_detail`, which is where a line's own
facts already live (7C). Both nullable: blank means the line follows the Work Order.

CHECK constraints encode what the service also checks, so a direct write cannot store a shape the
application would refuse:

- `ck_wo_contract_end_basis_is_answered` - a fixed end date needs the FIXED_DATE basis and vice
  versa, and "until the work is complete" carries no date. Without this a row could claim a firm end
  date while reporting itself as open-ended, or the reverse. It and its extension counterpart are
  written as a CASE rather than a chain of ORs, deliberately: a CHECK rejects a row only when its
  expression is FALSE, and `NULL = 'FIXED_DATE'` evaluates to NULL, so the OR form admitted the very
  shape it was written to refuse - an end date recorded with no basis beside it.
- `ck_wo_contract_dates_ordered` / `ck_wol_detail_line_dates_ordered` - an end before its own start.
- `ck_wo_contract_extension_start_follows_previous_end` - an extension continuing from a fixed end
  records the date it starts, after that end and not after its own new end; one with no fixed end to
  follow records none. Added at the owner's clarification of 22 September 2026, before this revision
  was ever merged or deployed, which is why it is amended in place rather than given a revision of its
  own. Same CASE form, for the same reason.
- What a date must be *relative to another table* - a line's dates inside the contract, a billing
  period's start inside it - a CHECK cannot see, so the service owns those; see
  `contract_period_rules.py`.

Also seeds two permissions. Two rather than one because owner decision 18 asks for the dates to be
recordable by the same four roles "under a permission of their own, so extensions can later be
narrowed to managers without touching code" - narrowing a single shared permission would also narrow
who may set the original dates, which is not what that asks for. Both are spelled out here rather
than imported so this revision stays a frozen historical snapshot (the 20260908_0033 to 0038
convention).

Revision ID: 20260908_0039
Revises: 20260908_0038
Create Date: 2026-09-17
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0039"
down_revision: Union[str, None] = "20260908_0038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONTRACT_PERIOD_TABLE = "crm_work_order_contract_period"
CONTRACT_EXTENSION_TABLE = "crm_work_order_contract_extension"
LINE_DETAIL_TABLE = "crm_work_order_line_detail"

ROLE_ADMIN = "ADMIN"
ROLE_SALES_USER = "SALES_USER"
ROLE_SALES_MANAGER = "SALES_MANAGER"
ROLE_OPERATIONS_USER = "OPERATIONS_USER"

FOUR_WRITING_ROLES = (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_OPERATIONS_USER)

PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    "WORK_ORDER_CONTRACT_PERIOD_WRITE": (
        "Record or change a Work Order's contract start and end dates.",
        FOUR_WRITING_ROLES,
    ),
    "WORK_ORDER_CONTRACT_EXTENSION_WRITE": (
        "Record an extension that moves a Work Order's contract end date.",
        FOUR_WRITING_ROLES,
    ),
}


def upgrade() -> None:
    op.create_table(
        CONTRACT_PERIOD_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("work_order_contract_period_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("contract_start_date", sa.Date(), nullable=True),
        # Null: not answered yet, and reported missing. FIXED_DATE carries a date; UNTIL_WORK_COMPLETE
        # is a recorded answer that carries none (owner decision 14).
        sa.Column("contract_end_basis_code", sa.String(length=50), nullable=True),
        sa.Column("contract_end_date", sa.Date(), nullable=True),
        sa.Column("contract_notes", sa.UnicodeText(), nullable=True),
        sa.Column("period_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("work_order_contract_period_public_id", name="uq_wo_contract_period_public_id"),
        sa.UniqueConstraint("work_order_id", name="uq_wo_contract_period_work_order"),
        sa.ForeignKeyConstraint(
            ["work_order_id"], ["crm_work_order.id"], name="fk_wo_contract_period_work_order"
        ),
        sa.CheckConstraint(
            "contract_end_basis_code IS NULL "
            "OR contract_end_basis_code IN ('FIXED_DATE', 'UNTIL_WORK_COMPLETE')",
            name="ck_wo_contract_end_basis",
        ),
        # Written as a CASE, not as a chain of ORs. A CHECK only rejects a row when its expression
        # is FALSE, and `NULL = 'FIXED_DATE'` is NULL, not FALSE - so the OR form silently ADMITTED
        # the one shape it most needed to refuse: no basis recorded beside a real end date. A CASE
        # on a NULL basis returns a definite boolean instead. Found by this package's own test
        # (the OR form was written first, and reasoning about intent missed it).
        sa.CheckConstraint(
            "CASE"
            " WHEN contract_end_basis_code IS NULL THEN contract_end_date IS NULL"
            " WHEN contract_end_basis_code = 'FIXED_DATE' THEN contract_end_date IS NOT NULL"
            " ELSE contract_end_date IS NULL"
            " END",
            name="ck_wo_contract_end_basis_is_answered",
        ),
        sa.CheckConstraint(
            "contract_start_date IS NULL OR contract_end_date IS NULL "
            "OR contract_end_date >= contract_start_date",
            name="ck_wo_contract_dates_ordered",
        ),
        sa.CheckConstraint("period_version >= 1", name="ck_wo_contract_period_version"),
    )

    op.create_table(
        CONTRACT_EXTENSION_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("work_order_contract_extension_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("extension_sequence_no", sa.Integer(), nullable=False),
        # What the contract said before this extension, kept on the row so the history reads without
        # replaying every earlier one. Both null where no end date had been recorded at all.
        sa.Column("previous_end_basis_code", sa.String(length=50), nullable=True),
        sa.Column("previous_end_date", sa.Date(), nullable=True),
        # An extension always records a firm new end date, later than a fixed end it follows. One
        # recorded in error is removed, not answered with another (owner, 22 Sep 2026).
        sa.Column("new_end_date", sa.Date(), nullable=False),
        # The day the extension starts: normally the day after the end it follows. A later start
        # leaves days no contract runs on, and is recorded only after the user confirms it (owner,
        # 22 Sep 2026). Null exactly when there was no fixed end to follow.
        sa.Column("extension_start_date", sa.Date(), nullable=True),
        sa.Column("customer_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("extension_notes", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint(
            "work_order_contract_extension_public_id", name="uq_wo_contract_extension_public_id"
        ),
        sa.UniqueConstraint(
            "work_order_id", "extension_sequence_no", name="uq_wo_contract_extension_sequence"
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"], ["crm_work_order.id"], name="fk_wo_contract_extension_work_order"
        ),
        sa.CheckConstraint(
            "previous_end_basis_code IS NULL "
            "OR previous_end_basis_code IN ('FIXED_DATE', 'UNTIL_WORK_COMPLETE')",
            name="ck_wo_contract_extension_previous_basis",
        ),
        # The previous end is constrained exactly as the current end is on the period table: the
        # service only ever writes (FIXED_DATE, a date), (UNTIL_WORK_COMPLETE, none) or (none, none),
        # so without this a direct write could record history saying the contract both ended on a
        # fixed date and had no date - leaving what the contract said before ambiguous.
        # Same CASE form, and for the same reason: see ck_wo_contract_end_basis_is_answered above.
        sa.CheckConstraint(
            "CASE"
            " WHEN previous_end_basis_code IS NULL THEN previous_end_date IS NULL"
            " WHEN previous_end_basis_code = 'FIXED_DATE' THEN previous_end_date IS NOT NULL"
            " ELSE previous_end_date IS NULL"
            " END",
            name="ck_wo_contract_extension_previous_is_answered",
        ),
        sa.CheckConstraint(
            "CASE"
            " WHEN previous_end_date IS NULL THEN extension_start_date IS NULL"
            " ELSE extension_start_date IS NOT NULL"
            " AND extension_start_date > previous_end_date"
            " AND extension_start_date <= new_end_date"
            " END",
            name="ck_wo_contract_extension_start_follows_previous_end",
        ),
        sa.CheckConstraint("extension_sequence_no >= 1", name="ck_wo_contract_extension_sequence_no"),
    )

    # A line's own dates inside the contract period. Blank means the line follows the Work Order
    # (owner decision 13). They sit with the line's other operational facts rather than in a third
    # table of their own.
    op.add_column(LINE_DETAIL_TABLE, sa.Column("line_start_date", sa.Date(), nullable=True))
    op.add_column(LINE_DETAIL_TABLE, sa.Column("line_end_date", sa.Date(), nullable=True))
    op.create_check_constraint(
        "ck_wol_detail_line_dates_ordered",
        LINE_DETAIL_TABLE,
        "line_start_date IS NULL OR line_end_date IS NULL OR line_end_date >= line_start_date",
    )

    _seed_permissions()


def _seed_permissions() -> None:
    """Insert each permission row and its role grants, as 20260908_0036 to 0038 do."""
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


def downgrade() -> None:
    connection = op.get_bind()
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

    op.drop_constraint("ck_wol_detail_line_dates_ordered", LINE_DETAIL_TABLE, type_="check")
    op.drop_column(LINE_DETAIL_TABLE, "line_end_date")
    op.drop_column(LINE_DETAIL_TABLE, "line_start_date")

    op.drop_table(CONTRACT_EXTENSION_TABLE)
    op.drop_table(CONTRACT_PERIOD_TABLE)
