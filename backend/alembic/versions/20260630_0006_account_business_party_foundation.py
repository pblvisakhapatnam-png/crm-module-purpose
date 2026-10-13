"""account business party foundation

Revision ID: 20260630_0006
Revises: 20260629_0005
Create Date: 2026-06-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_0006"
down_revision: Union[str, None] = "20260629_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_party",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("business_party_public_id", sa.String(length=36), nullable=False),
        sa.Column("party_type", sa.String(length=50), nullable=False, server_default="organization"),
        sa.Column("account_name", sa.Unicode(length=255), nullable=False),
        sa.Column("legal_name", sa.Unicode(length=255), nullable=True),
        sa.Column("pan", sa.String(length=10), nullable=True),
        sa.Column("gstin", sa.String(length=15), nullable=True),
        sa.Column("account_status_code", sa.String(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("qualification_source", sa.String(length=50), nullable=True),
        sa.Column("account_owner_user_public_id", sa.String(length=36), nullable=True),
        sa.Column("segment", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("source_remarks", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_business_party"),
    )

    op.create_index(
        "ux_business_party_public_id",
        "business_party",
        ["business_party_public_id"],
        unique=True,
    )
    op.create_index(
        "ix_business_party_account_status_code",
        "business_party",
        ["account_status_code"],
        unique=False,
    )
    op.create_index(
        "ix_business_party_pan",
        "business_party",
        ["pan"],
        unique=False,
    )
    op.create_index(
        "ix_business_party_account_name",
        "business_party",
        ["account_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_business_party_account_name", table_name="business_party")
    op.drop_index("ix_business_party_pan", table_name="business_party")
    op.drop_index("ix_business_party_account_status_code", table_name="business_party")
    op.drop_index("ux_business_party_public_id", table_name="business_party")
    op.drop_table("business_party")