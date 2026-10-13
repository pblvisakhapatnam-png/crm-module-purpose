"""commercial offer supplementary / change quotation related-offer foundation

Slice 6O.1 adds an explicit offer_purpose (BASE / SUPPLEMENTARY / CHANGE_QUOTATION),
a direct self-referencing link from a related offer back to its Base Offer, an
optional link to an existing Work Order, and a thin customer-request context.
Every pre-existing Commercial Offer becomes BASE via the NOT NULL DEFAULT backfill.

Revision ID: 20260712_0028
Revises: 20260712_0027
Create Date: 2026-07-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260712_0028"
down_revision: Union[str, None] = "20260712_0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOT NULL with a server default backfills every existing row to 'BASE' in one statement.
    op.add_column(
        "crm_commercial_offer",
        sa.Column(
            "offer_purpose",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'BASE'"),
        ),
    )
    op.add_column("crm_commercial_offer", sa.Column("base_offer_id", sa.Integer(), nullable=True))
    op.add_column(
        "crm_commercial_offer",
        sa.Column("related_work_order_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "crm_commercial_offer",
        sa.Column("customer_request_reference", sa.Unicode(length=255), nullable=True),
    )
    op.add_column(
        "crm_commercial_offer",
        sa.Column("customer_request_received_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "crm_commercial_offer",
        sa.Column("customer_request_summary", sa.Unicode(length=2000), nullable=True),
    )

    op.create_foreign_key(
        "fk_crm_commercial_offer_base_offer",
        "crm_commercial_offer",
        "crm_commercial_offer",
        ["base_offer_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_crm_commercial_offer_related_work_order",
        "crm_commercial_offer",
        "crm_work_order",
        ["related_work_order_id"],
        ["id"],
    )

    op.create_check_constraint(
        "ck_crm_commercial_offer_purpose",
        "crm_commercial_offer",
        "offer_purpose IN ('BASE', 'SUPPLEMENTARY', 'CHANGE_QUOTATION')",
    )
    op.create_check_constraint(
        "ck_crm_commercial_offer_purpose_base_offer_link",
        "crm_commercial_offer",
        """
        (offer_purpose = 'BASE' AND base_offer_id IS NULL)
        OR (offer_purpose IN ('SUPPLEMENTARY', 'CHANGE_QUOTATION') AND base_offer_id IS NOT NULL)
        """,
    )

    for index_name, columns in (
        ("ix_crm_commercial_offer_purpose", ["offer_purpose"]),
        ("ix_crm_commercial_offer_base_offer", ["base_offer_id"]),
        ("ix_crm_commercial_offer_related_work_order", ["related_work_order_id"]),
    ):
        op.create_index(index_name, "crm_commercial_offer", columns, unique=False)


def downgrade() -> None:
    for index_name in (
        "ix_crm_commercial_offer_related_work_order",
        "ix_crm_commercial_offer_base_offer",
        "ix_crm_commercial_offer_purpose",
    ):
        op.drop_index(index_name, table_name="crm_commercial_offer")

    op.drop_constraint(
        "ck_crm_commercial_offer_purpose_base_offer_link",
        "crm_commercial_offer",
        type_="check",
    )
    op.drop_constraint("ck_crm_commercial_offer_purpose", "crm_commercial_offer", type_="check")
    op.drop_constraint(
        "fk_crm_commercial_offer_related_work_order",
        "crm_commercial_offer",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_crm_commercial_offer_base_offer",
        "crm_commercial_offer",
        type_="foreignkey",
    )

    # PostgreSQL attaches a column default to the column itself rather than to a separately named
    # constraint object, so dropping the column removes the default with it. The SQL Server chain
    # needed an explicit df_crm_commercial_offer_purpose drop here; PostgreSQL does not.
    for column in (
        "customer_request_summary",
        "customer_request_received_date",
        "customer_request_reference",
        "related_work_order_id",
        "base_offer_id",
        "offer_purpose",
    ):
        op.drop_column("crm_commercial_offer", column)
