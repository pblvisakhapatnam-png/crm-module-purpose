"""commercial offer line foundation

Revision ID: 20260705_0019
Revises: 20260705_0018
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260705_0019"
down_revision: Union[str, None] = "20260705_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_commercial_offer_line",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("line_public_id", sa.String(length=36), nullable=False),
        sa.Column("commercial_offer_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("line_status_code", sa.String(length=50), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("scope_description", sa.Unicode(length=1000), nullable=False),
        sa.Column("equipment_service_category", sa.Unicode(length=255), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("1")),
        sa.Column("uom", sa.String(length=50), nullable=False, server_default=sa.text("'unit'")),
        sa.Column("rate_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default=sa.text("'INR'")),
        sa.Column("line_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("remarks", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_crm_commercial_offer_line"),
        sa.UniqueConstraint("line_public_id", name="uq_crm_commercial_offer_line_public_id"),
        sa.ForeignKeyConstraint(
            ["commercial_offer_id"],
            ["crm_commercial_offer.id"],
            name="fk_crm_commercial_offer_line_offer",
        ),
        sa.CheckConstraint(
            "line_status_code IN ('ACTIVE', 'CANCELLED')",
            name="ck_crm_commercial_offer_line_status",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_crm_commercial_offer_line_quantity"),
        sa.CheckConstraint(
            "rate_amount IS NULL OR rate_amount >= 0",
            name="ck_crm_commercial_offer_line_rate",
        ),
        sa.CheckConstraint(
            "line_amount IS NULL OR line_amount >= 0",
            name="ck_crm_commercial_offer_line_amount",
        ),
    )

    for index_name, columns in (
        ("ix_crm_commercial_offer_line_offer", ["commercial_offer_id"]),
        ("ix_crm_commercial_offer_line_offer_line_number", ["commercial_offer_id", "line_number"]),
        ("ix_crm_commercial_offer_line_status", ["line_status_code"]),
        ("ix_crm_commercial_offer_line_created_at", ["created_at"]),
    ):
        op.create_index(index_name, "crm_commercial_offer_line", columns, unique=False)


def downgrade() -> None:
    op.drop_table("crm_commercial_offer_line")
