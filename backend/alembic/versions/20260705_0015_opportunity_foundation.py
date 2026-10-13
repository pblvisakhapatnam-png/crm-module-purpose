"""opportunity foundation

Revision ID: 20260705_0015
Revises: 20260705_0014
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260705_0015"
down_revision: Union[str, None] = "20260705_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OPPORTUNITY_STATUSES = [
    {
        "public_id": "00000000-0000-0000-0000-000000000501",
        "module": "opportunity",
        "status_code": "NEW",
        "status_name": "New",
        "sort_order": 10,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000502",
        "module": "opportunity",
        "status_code": "NEEDS_REVIEW",
        "status_name": "Needs Review",
        "sort_order": 20,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000503",
        "module": "opportunity",
        "status_code": "QUALIFIED",
        "status_name": "Qualified",
        "sort_order": 30,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000504",
        "module": "opportunity",
        "status_code": "QUOTE_PENDING",
        "status_name": "Quote Pending",
        "sort_order": 40,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000505",
        "module": "opportunity",
        "status_code": "ON_HOLD",
        "status_name": "On Hold",
        "sort_order": 50,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000506",
        "module": "opportunity",
        "status_code": "WON",
        "status_name": "Won",
        "sort_order": 80,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000507",
        "module": "opportunity",
        "status_code": "LOST",
        "status_name": "Lost",
        "sort_order": 90,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000508",
        "module": "opportunity",
        "status_code": "CLOSED",
        "status_name": "Closed",
        "sort_order": 95,
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
        "crm_opportunity",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("opportunity_public_id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_name", sa.Unicode(length=255), nullable=False),
        sa.Column("opportunity_source", sa.String(length=50), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("source_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("business_party_id", sa.Integer(), nullable=True),
        sa.Column("source_lead_id", sa.Integer(), nullable=True),
        sa.Column("customer_requirement_summary", sa.UnicodeText(), nullable=True),
        sa.Column("estimated_value", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("opportunity_status_code", sa.String(length=50), nullable=False, server_default=sa.text("'NEW'")),
        sa.Column("owner_user_public_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_crm_opportunity"),
        sa.UniqueConstraint("opportunity_public_id", name="uq_crm_opportunity_public_id"),
        sa.ForeignKeyConstraint(
            ["business_party_id"],
            ["business_party.id"],
            name="fk_crm_opportunity_business_party",
        ),
        sa.ForeignKeyConstraint(
            ["source_lead_id"],
            ["crm_lead.id"],
            name="fk_crm_opportunity_source_lead",
        ),
    )

    for index_name, columns in (
        ("ix_crm_opportunity_status", ["opportunity_status_code"]),
        ("ix_crm_opportunity_source", ["opportunity_source"]),
        ("ix_crm_opportunity_owner", ["owner_user_public_id"]),
        ("ix_crm_opportunity_business_party", ["business_party_id"]),
        ("ix_crm_opportunity_source_lead", ["source_lead_id"]),
        ("ix_crm_opportunity_created_at", ["created_at"]),
    ):
        op.create_index(index_name, "crm_opportunity", columns, unique=False)

    connection = op.get_bind()
    for row in OPPORTUNITY_STATUSES:
        connection.execute(INSERT_STATUS_IF_ABSENT, row)


def downgrade() -> None:
    status_codes = ", ".join(f"'{row['status_code']}'" for row in OPPORTUNITY_STATUSES)
    op.execute(
        f"""
        DELETE FROM workflow_status
        WHERE module = 'opportunity'
          AND status_code IN ({status_codes})
        """
    )
    op.drop_table("crm_opportunity")
