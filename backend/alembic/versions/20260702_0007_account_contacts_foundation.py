"""account contacts foundation

Revision ID: 20260702_0007
Revises: 20260630_0006
Create Date: 2026-07-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260702_0007"
down_revision: Union[str, None] = "20260630_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_party_contact",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contact_public_id", sa.String(length=36), nullable=False),
        sa.Column("business_party_id", sa.Integer(), nullable=False),
        sa.Column("contact_name", sa.Unicode(length=255), nullable=False),
        sa.Column("designation", sa.Unicode(length=150), nullable=True),
        sa.Column("department", sa.Unicode(length=150), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("remarks", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_business_party_contact"),
        sa.ForeignKeyConstraint(
            ["business_party_id"],
            ["business_party.id"],
            name="fk_business_party_contact_business_party",
        ),
    )

    op.create_index(
        "ux_business_party_contact_public_id",
        "business_party_contact",
        ["contact_public_id"],
        unique=True,
    )
    op.create_index(
        "ix_business_party_contact_business_party_id",
        "business_party_contact",
        ["business_party_id"],
        unique=False,
    )
    op.create_index(
        "ix_business_party_contact_email",
        "business_party_contact",
        ["email"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_business_party_contact_email", table_name="business_party_contact")
    op.drop_index("ix_business_party_contact_business_party_id", table_name="business_party_contact")
    op.drop_index("ux_business_party_contact_public_id", table_name="business_party_contact")
    op.drop_table("business_party_contact")