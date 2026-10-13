"""commercial offer pricing evidence foundation

Revision ID: 20260705_0018
Revises: 20260705_0017
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260705_0018"
down_revision: Union[str, None] = "20260705_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_commercial_offer_pricing_evidence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evidence_public_id", sa.String(length=36), nullable=False),
        sa.Column("commercial_offer_id", sa.Integer(), nullable=False),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("source_name", sa.Unicode(length=255), nullable=True),
        sa.Column("vendor_contact", sa.Unicode(length=255), nullable=True),
        sa.Column("equipment_service_description", sa.Unicode(length=1000), nullable=False),
        sa.Column("rate_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'INR'")),
        sa.Column("rate_basis", sa.String(length=100), nullable=False),
        sa.Column("collected_by_name", sa.Unicode(length=255), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=True),
        sa.Column("source_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("is_selected_basis", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("selection_reason", sa.UnicodeText(), nullable=True),
        sa.Column("comparison_notes", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_crm_commercial_offer_pricing_evidence"),
        sa.UniqueConstraint(
            "evidence_public_id",
            name="uq_crm_commercial_offer_pricing_evidence_public_id",
        ),
        sa.ForeignKeyConstraint(
            ["commercial_offer_id"],
            ["crm_commercial_offer.id"],
            name="fk_crm_commercial_offer_pricing_evidence_offer",
        ),
        sa.CheckConstraint(
            "evidence_type IN ('market_rate', 'historical_plum_rate')",
            name="ck_crm_commercial_offer_pricing_evidence_type",
        ),
        sa.CheckConstraint(
            "rate_amount >= 0",
            name="ck_crm_commercial_offer_pricing_evidence_amount",
        ),
    )

    for index_name, columns in (
        ("ix_crm_commercial_offer_pricing_evidence_offer", ["commercial_offer_id"]),
        ("ix_crm_commercial_offer_pricing_evidence_type", ["evidence_type"]),
        ("ix_crm_commercial_offer_pricing_evidence_created_at", ["created_at"]),
    ):
        op.create_index(index_name, "crm_commercial_offer_pricing_evidence", columns, unique=False)

    # At most one selected basis rate per Commercial Offer. Unselected rows are excluded from the
    # partial index, so any number of them may coexist.
    op.create_index(
        "ux_crm_commercial_offer_pricing_evidence_one_selected",
        "crm_commercial_offer_pricing_evidence",
        ["commercial_offer_id"],
        unique=True,
        postgresql_where=sa.text("is_selected_basis"),
    )


def downgrade() -> None:
    op.drop_table("crm_commercial_offer_pricing_evidence")
