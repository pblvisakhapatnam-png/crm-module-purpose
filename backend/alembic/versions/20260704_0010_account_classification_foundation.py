"""account classification foundation

Revision ID: 20260704_0010
Revises: 20260703_0009
Create Date: 2026-07-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260704_0010"
down_revision: Union[str, None] = "20260703_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "business_party",
        sa.Column("is_strategic_account", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "business_party",
        sa.Column("classification_notes", sa.UnicodeText(), nullable=True),
    )
    op.create_index(
        "ix_business_party_owner",
        "business_party",
        ["account_owner_user_public_id"],
        unique=False,
    )
    op.create_index(
        "ix_business_party_segment",
        "business_party",
        ["segment"],
        unique=False,
    )
    op.create_index(
        "ix_business_party_industry",
        "business_party",
        ["industry"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_business_party_industry", table_name="business_party")
    op.drop_index("ix_business_party_segment", table_name="business_party")
    op.drop_index("ix_business_party_owner", table_name="business_party")
    op.drop_column("business_party", "classification_notes")
    op.drop_column("business_party", "is_strategic_account")
