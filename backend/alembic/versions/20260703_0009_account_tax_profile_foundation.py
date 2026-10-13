"""account tax profile foundation

Revision ID: 20260703_0009
Revises: 20260702_0008
Create Date: 2026-07-03

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260703_0009"
down_revision: Union[str, None] = "20260702_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_party_tax_profile",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tax_profile_public_id", sa.String(length=36), nullable=False),
        sa.Column("business_party_id", sa.Integer(), nullable=False),
        sa.Column("pan", sa.String(length=10), nullable=True),
        sa.Column("pan_verification_state_code", sa.String(length=50), nullable=False, server_default=sa.text("'NOT_AVAILABLE'")),
        sa.Column("pan_legal_name", sa.Unicode(length=255), nullable=True),
        sa.Column("remarks", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_business_party_tax_profile"),
        sa.ForeignKeyConstraint(
            ["business_party_id"],
            ["business_party.id"],
            name="fk_business_party_tax_profile_business_party",
        ),
    )

    op.create_index(
        "ux_business_party_tax_profile_public_id",
        "business_party_tax_profile",
        ["tax_profile_public_id"],
        unique=True,
    )
    op.create_index(
        "ux_business_party_tax_profile_business_party_id",
        "business_party_tax_profile",
        ["business_party_id"],
        unique=True,
    )
    op.create_index(
        "ix_business_party_tax_profile_pan",
        "business_party_tax_profile",
        ["pan"],
        unique=False,
    )

    op.create_table(
        "business_party_gstin",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gstin_public_id", sa.String(length=36), nullable=False),
        sa.Column("business_party_id", sa.Integer(), nullable=False),
        sa.Column("gstin", sa.String(length=15), nullable=False),
        sa.Column("gstin_verification_state_code", sa.String(length=50), nullable=False, server_default=sa.text("'ENTERED_NOT_VERIFIED'")),
        sa.Column("state_code", sa.String(length=2), nullable=False),
        sa.Column("state_name", sa.Unicode(length=150), nullable=True),
        sa.Column("legal_name", sa.Unicode(length=255), nullable=True),
        sa.Column("trade_name", sa.Unicode(length=255), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("remarks", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_business_party_gstin"),
        sa.ForeignKeyConstraint(
            ["business_party_id"],
            ["business_party.id"],
            name="fk_business_party_gstin_business_party",
        ),
    )

    op.create_index("ux_business_party_gstin_public_id", "business_party_gstin", ["gstin_public_id"], unique=True)
    op.create_index("ux_business_party_gstin", "business_party_gstin", ["gstin"], unique=True)
    op.create_index("ix_business_party_gstin_business_party_id", "business_party_gstin", ["business_party_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_business_party_gstin_business_party_id", table_name="business_party_gstin")
    op.drop_index("ux_business_party_gstin", table_name="business_party_gstin")
    op.drop_index("ux_business_party_gstin_public_id", table_name="business_party_gstin")
    op.drop_table("business_party_gstin")

    op.drop_index("ix_business_party_tax_profile_pan", table_name="business_party_tax_profile")
    op.drop_index("ux_business_party_tax_profile_business_party_id", table_name="business_party_tax_profile")
    op.drop_index("ux_business_party_tax_profile_public_id", table_name="business_party_tax_profile")
    op.drop_table("business_party_tax_profile")
