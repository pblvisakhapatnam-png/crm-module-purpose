"""account addresses foundation

Revision ID: 20260702_0008
Revises: 20260702_0007
Create Date: 2026-07-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260702_0008"
down_revision: Union[str, None] = "20260702_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_party_address",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("address_public_id", sa.String(length=36), nullable=False),
        sa.Column("business_party_id", sa.Integer(), nullable=False),
        sa.Column("address_type_code", sa.String(length=50), nullable=False),
        sa.Column("address_line1", sa.Unicode(length=255), nullable=False),
        sa.Column("address_line2", sa.Unicode(length=255), nullable=True),
        sa.Column("city", sa.Unicode(length=150), nullable=False),
        sa.Column("district", sa.Unicode(length=150), nullable=True),
        sa.Column("state", sa.Unicode(length=150), nullable=False),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default=sa.text("'IN'")),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("remarks", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_business_party_address"),
        sa.ForeignKeyConstraint(
            ["business_party_id"],
            ["business_party.id"],
            name="fk_business_party_address_business_party",
        ),
    )

    op.create_index(
        "ux_business_party_address_public_id",
        "business_party_address",
        ["address_public_id"],
        unique=True,
    )
    op.create_index(
        "ix_business_party_address_business_party_id",
        "business_party_address",
        ["business_party_id"],
        unique=False,
    )
    op.create_index(
        "ix_business_party_address_type",
        "business_party_address",
        ["address_type_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_business_party_address_type", table_name="business_party_address")
    op.drop_index("ix_business_party_address_business_party_id", table_name="business_party_address")
    op.drop_index("ux_business_party_address_public_id", table_name="business_party_address")
    op.drop_table("business_party_address")
