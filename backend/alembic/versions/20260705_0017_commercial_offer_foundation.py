"""commercial offer foundation

Revision ID: 20260705_0017
Revises: 20260705_0016
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260705_0017"
down_revision: Union[str, None] = "20260705_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COMMERCIAL_OFFER_STATUSES = [
    {
        "public_id": "00000000-0000-0000-0000-000000000601",
        "module": "commercial_offer",
        "status_code": "DRAFT",
        "status_name": "Draft",
        "sort_order": 10,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000602",
        "module": "commercial_offer",
        "status_code": "READY_FOR_REVIEW",
        "status_name": "Ready for Review",
        "sort_order": 20,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000603",
        "module": "commercial_offer",
        "status_code": "SUBMITTED",
        "status_name": "Submitted",
        "sort_order": 30,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000604",
        "module": "commercial_offer",
        "status_code": "REVISED",
        "status_name": "Revised",
        "sort_order": 40,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000605",
        "module": "commercial_offer",
        "status_code": "WITHDRAWN",
        "status_name": "Withdrawn",
        "sort_order": 70,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000606",
        "module": "commercial_offer",
        "status_code": "ACCEPTED",
        "status_name": "Accepted",
        "sort_order": 80,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000607",
        "module": "commercial_offer",
        "status_code": "REJECTED",
        "status_name": "Rejected",
        "sort_order": 90,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000608",
        "module": "commercial_offer",
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
        "crm_commercial_offer",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("offer_public_id", sa.String(length=36), nullable=False),
        sa.Column("offer_code", sa.Unicode(length=50), nullable=True),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("business_party_id", sa.Integer(), nullable=True),
        sa.Column("offer_title", sa.Unicode(length=255), nullable=True),
        sa.Column("offer_mode", sa.String(length=50), nullable=False, server_default=sa.text("'plum_generated'")),
        sa.Column("offer_type", sa.String(length=50), nullable=False, server_default=sa.text("'budgetary'")),
        sa.Column("offer_status_code", sa.String(length=50), nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("offer_value", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'INR'")),
        sa.Column("offer_date", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("remarks", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_crm_commercial_offer"),
        sa.UniqueConstraint("offer_public_id", name="uq_crm_commercial_offer_public_id"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["crm_opportunity.id"],
            name="fk_crm_commercial_offer_opportunity",
        ),
        sa.ForeignKeyConstraint(
            ["business_party_id"],
            ["business_party.id"],
            name="fk_crm_commercial_offer_business_party",
        ),
    )

    for index_name, columns in (
        ("ix_crm_commercial_offer_opportunity", ["opportunity_id"]),
        ("ix_crm_commercial_offer_business_party", ["business_party_id"]),
        ("ix_crm_commercial_offer_status", ["offer_status_code"]),
        ("ix_crm_commercial_offer_mode", ["offer_mode"]),
        ("ix_crm_commercial_offer_created_at", ["created_at"]),
    ):
        op.create_index(index_name, "crm_commercial_offer", columns, unique=False)

    # Offer codes are unique when present; unnumbered drafts stay unconstrained.
    op.create_index(
        "ux_crm_commercial_offer_code_not_null",
        "crm_commercial_offer",
        ["offer_code"],
        unique=True,
        postgresql_where=sa.text("offer_code IS NOT NULL"),
    )

    connection = op.get_bind()
    for row in COMMERCIAL_OFFER_STATUSES:
        connection.execute(INSERT_STATUS_IF_ABSENT, row)


def downgrade() -> None:
    status_codes = ", ".join(f"'{row['status_code']}'" for row in COMMERCIAL_OFFER_STATUSES)
    op.execute(
        f"""
        DELETE FROM workflow_status
        WHERE module = 'commercial_offer'
          AND status_code IN ({status_codes})
        """
    )
    op.drop_table("crm_commercial_offer")
