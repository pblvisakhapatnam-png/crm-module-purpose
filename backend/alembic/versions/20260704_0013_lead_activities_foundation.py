"""lead activities foundation

Revision ID: 20260704_0013
Revises: 20260704_0012
Create Date: 2026-07-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260704_0013"
down_revision: Union[str, None] = "20260704_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_lead_activity",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("activity_public_id", sa.String(length=36), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("activity_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.UnicodeText(), nullable=True),
        sa.Column("outcome", sa.Unicode(length=255), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_crm_lead_activity"),
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["crm_lead.id"],
            name="fk_crm_lead_activity_lead",
        ),
    )

    op.create_index(
        "ux_crm_lead_activity_public_id",
        "crm_lead_activity",
        ["activity_public_id"],
        unique=True,
    )
    op.create_index("ix_crm_lead_activity_lead_id", "crm_lead_activity", ["lead_id"], unique=False)
    op.create_index("ix_crm_lead_activity_type", "crm_lead_activity", ["activity_type"], unique=False)
    op.create_index("ix_crm_lead_activity_at", "crm_lead_activity", ["activity_at"], unique=False)
    op.create_index("ix_crm_lead_activity_next_follow_up", "crm_lead_activity", ["next_follow_up_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_crm_lead_activity_next_follow_up", table_name="crm_lead_activity")
    op.drop_index("ix_crm_lead_activity_at", table_name="crm_lead_activity")
    op.drop_index("ix_crm_lead_activity_type", table_name="crm_lead_activity")
    op.drop_index("ix_crm_lead_activity_lead_id", table_name="crm_lead_activity")
    op.drop_index("ux_crm_lead_activity_public_id", table_name="crm_lead_activity")
    op.drop_table("crm_lead_activity")
