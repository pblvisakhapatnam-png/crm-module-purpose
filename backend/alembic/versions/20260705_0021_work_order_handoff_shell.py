"""work order handoff shell

Revision ID: 20260705_0021
Revises: 20260705_0020
Create Date: 2026-07-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260705_0021"
down_revision: Union[str, None] = "20260705_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


WORK_ORDER_STATUSES = [
    {
        "public_id": "00000000-0000-0000-0000-000000000701",
        "module": "work_order",
        "status_code": "DRAFT",
        "status_name": "Draft",
        "sort_order": 10,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000702",
        "module": "work_order",
        "status_code": "HANDOFF_CREATED",
        "status_name": "Handoff Created",
        "sort_order": 20,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000703",
        "module": "work_order",
        "status_code": "EXECUTION_DEFERRED",
        "status_name": "Execution Deferred",
        "sort_order": 30,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000704",
        "module": "work_order",
        "status_code": "CLOSED",
        "status_name": "Closed",
        "sort_order": 90,
    },
]


INSERT_STATUS_IF_ABSENT = sa.text(
    """
    INSERT INTO workflow_status (
        public_id, module, status_code, status_name, is_active, sort_order
    )
    -- :module and :status_code are also used in the WHERE EXISTS below. Without an explicit
    -- cast PostgreSQL deduces "text" for the SELECT-list occurrence and "character varying"
    -- for the comparison, and rejects the statement as an ambiguous parameter.
    SELECT :public_id, CAST(:module AS VARCHAR), CAST(:status_code AS VARCHAR), :status_name, TRUE, :sort_order
    WHERE NOT EXISTS (
        SELECT 1
        FROM workflow_status
        WHERE module = :module
          AND status_code = :status_code
    )
    """
)


def upgrade() -> None:
    op.create_table(
        "crm_work_order",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_order_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_code", sa.Unicode(length=50), nullable=True),
        sa.Column("commercial_offer_id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("business_party_id", sa.Integer(), nullable=True),
        sa.Column("work_order_title", sa.Unicode(length=255), nullable=True),
        sa.Column(
            "work_order_status_code",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'HANDOFF_CREATED'"),
        ),
        sa.Column("customer_wo_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("source_offer_status_code", sa.String(length=50), nullable=False),
        sa.Column("remarks", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_crm_work_order"),
        sa.UniqueConstraint("work_order_public_id", name="uq_crm_work_order_public_id"),
        sa.ForeignKeyConstraint(
            ["commercial_offer_id"],
            ["crm_commercial_offer.id"],
            name="fk_crm_work_order_commercial_offer",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["crm_opportunity.id"],
            name="fk_crm_work_order_opportunity",
        ),
        sa.ForeignKeyConstraint(
            ["business_party_id"],
            ["business_party.id"],
            name="fk_crm_work_order_business_party",
        ),
    )

    op.create_table(
        "crm_work_order_line",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_order_line_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("commercial_offer_line_id", sa.Integer(), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column(
            "line_status_code",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'HANDOFF_CREATED'"),
        ),
        sa.Column("scope_description", sa.Unicode(length=1000), nullable=False),
        sa.Column("equipment_service_category", sa.Unicode(length=255), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("uom", sa.String(length=50), nullable=False),
        sa.Column("rate_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'INR'")),
        sa.Column("line_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("remarks", sa.UnicodeText(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_crm_work_order_line"),
        sa.UniqueConstraint("work_order_line_public_id", name="uq_crm_work_order_line_public_id"),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["crm_work_order.id"],
            name="fk_crm_work_order_line_work_order",
        ),
        sa.ForeignKeyConstraint(
            ["commercial_offer_line_id"],
            ["crm_commercial_offer_line.id"],
            name="fk_crm_work_order_line_offer_line",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_crm_work_order_line_quantity"),
        sa.CheckConstraint(
            "rate_amount IS NULL OR rate_amount >= 0",
            name="ck_crm_work_order_line_rate",
        ),
        sa.CheckConstraint(
            "line_amount IS NULL OR line_amount >= 0",
            name="ck_crm_work_order_line_amount",
        ),
    )

    for index_name, table_name, columns in (
        ("ix_crm_work_order_offer", "crm_work_order", ["commercial_offer_id"]),
        ("ix_crm_work_order_opportunity", "crm_work_order", ["opportunity_id"]),
        ("ix_crm_work_order_account", "crm_work_order", ["business_party_id"]),
        ("ix_crm_work_order_status", "crm_work_order", ["work_order_status_code"]),
        ("ix_crm_work_order_created_at", "crm_work_order", ["created_at"]),
        ("ix_crm_work_order_line_work_order", "crm_work_order_line", ["work_order_id"]),
        ("ix_crm_work_order_line_offer_line", "crm_work_order_line", ["commercial_offer_line_id"]),
        ("ix_crm_work_order_line_number", "crm_work_order_line", ["work_order_id", "line_number"]),
    ):
        op.create_index(index_name, table_name, columns, unique=False)

    # Work Order codes are unique when present; unnumbered shells stay unconstrained.
    op.create_index(
        "ux_crm_work_order_code_not_null",
        "crm_work_order",
        ["work_order_code"],
        unique=True,
        postgresql_where=sa.text("work_order_code IS NOT NULL"),
    )

    connection = op.get_bind()
    for row in WORK_ORDER_STATUSES:
        connection.execute(INSERT_STATUS_IF_ABSENT, row)


def downgrade() -> None:
    status_codes = ", ".join(f"'{row['status_code']}'" for row in WORK_ORDER_STATUSES)
    op.execute(
        f"""
        DELETE FROM workflow_status
        WHERE module = 'work_order'
          AND status_code IN ({status_codes})
        """
    )
    op.drop_table("crm_work_order_line")
    op.drop_table("crm_work_order")
