"""work order line operational detail (Slice 7C)

Adds `crm_work_order_line_detail`: one row per Work Order line holding what the handoff does not
carry - the site the work happens at, the GSTIN and address the customer is billed on, the
billing basis (Hour / Shift / Day / Month) and contracted hours, and the customer's own line
reference. Created on first save, after handoff.

A separate table rather than new columns on `crm_work_order_line`, deliberately: the Accepted
Offer -> Work Order shell handoff writes that table and its output is frozen
(docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md). Keeping this detail in its
own table means the handoff insert, the handoff response and the Slice 6O.2 amendment snapshot are
untouched by construction.

The three Account references are declared foreign keys onto the Account tables' unique public-id
columns (`ux_business_party_address_public_id`, `ux_business_party_gstin_public_id`), following
`crm_work_order`'s own declared key to `business_party`. Targeting the public ids means reads need
no join into Account tables; the Work Order module resolves display detail through the accounts
service. That the chosen address or GSTIN belongs to the Work Order's own Account, and is of the
right type, is checked by the service - a CHECK constraint cannot see another table.

`ck_wol_detail_hours_not_hourly` encodes WBT-001: hour-based billing uses actual working hours, so
a contracted-hours figure on an HOUR line is meaningless and must not be stored where a future
billing engine could read it.

Also seeds one permission, WORK_ORDER_LINE_DETAIL_WRITE, spelled out here rather than imported so
this revision stays a frozen historical snapshot (the 20260908_0033 to 0035 convention).

Revision ID: 20260908_0036
Revises: 20260908_0035
Create Date: 2026-09-14
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0036"
down_revision: Union[str, None] = "20260908_0035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LINE_DETAIL_TABLE = "crm_work_order_line_detail"

ROLE_ADMIN = "ADMIN"
ROLE_SALES_USER = "SALES_USER"
ROLE_SALES_MANAGER = "SALES_MANAGER"
ROLE_OPERATIONS_USER = "OPERATIONS_USER"

PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    "WORK_ORDER_LINE_DETAIL_WRITE": (
        "Record or change a Work Order line's site, billing GSTIN, billing address and billing basis.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_OPERATIONS_USER),
    ),
}


def upgrade() -> None:
    op.create_table(
        LINE_DETAIL_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("work_order_line_detail_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_line_id", sa.Integer(), nullable=False),
        sa.Column("site_address_public_id", sa.String(length=36), nullable=True),
        sa.Column("billing_gstin_public_id", sa.String(length=36), nullable=True),
        sa.Column("billing_address_public_id", sa.String(length=36), nullable=True),
        sa.Column("billing_uom_code", sa.String(length=50), nullable=True),
        sa.Column("contracted_hours_per_billing_unit", sa.Numeric(precision=9, scale=2), nullable=True),
        sa.Column("customer_line_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("operational_notes", sa.UnicodeText(), nullable=True),
        sa.Column("detail_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("work_order_line_detail_public_id", name="uq_wol_detail_public_id"),
        sa.UniqueConstraint("work_order_line_id", name="uq_wol_detail_work_order_line"),
        sa.ForeignKeyConstraint(
            ["work_order_line_id"], ["crm_work_order_line.id"], name="fk_wol_detail_work_order_line"
        ),
        sa.ForeignKeyConstraint(
            ["site_address_public_id"],
            ["business_party_address.address_public_id"],
            name="fk_wol_detail_site_address",
        ),
        sa.ForeignKeyConstraint(
            ["billing_gstin_public_id"],
            ["business_party_gstin.gstin_public_id"],
            name="fk_wol_detail_billing_gstin",
        ),
        sa.ForeignKeyConstraint(
            ["billing_address_public_id"],
            ["business_party_address.address_public_id"],
            name="fk_wol_detail_billing_address",
        ),
        sa.CheckConstraint(
            "billing_uom_code IS NULL OR billing_uom_code IN ('HOUR', 'SHIFT', 'DAY', 'MONTH')",
            name="ck_wol_detail_billing_uom",
        ),
        sa.CheckConstraint(
            "contracted_hours_per_billing_unit IS NULL OR contracted_hours_per_billing_unit > 0",
            name="ck_wol_detail_hours_positive",
        ),
        sa.CheckConstraint(
            "NOT (billing_uom_code = 'HOUR' AND contracted_hours_per_billing_unit IS NOT NULL)",
            name="ck_wol_detail_hours_not_hourly",
        ),
        sa.CheckConstraint("detail_version >= 1", name="ck_wol_detail_version"),
    )

    # Supports the reverse lookups an Account-side check would need ("which Work Order lines use
    # this GSTIN?") without a sequential scan.
    op.create_index("ix_wol_detail_site_address", LINE_DETAIL_TABLE, ["site_address_public_id"])
    op.create_index("ix_wol_detail_billing_gstin", LINE_DETAIL_TABLE, ["billing_gstin_public_id"])
    op.create_index("ix_wol_detail_billing_address", LINE_DETAIL_TABLE, ["billing_address_public_id"])

    _seed_permissions()


def _seed_permissions() -> None:
    """Insert the permission row and its role grants, as 20260908_0035 does."""
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

    op.drop_table(LINE_DETAIL_TABLE)
