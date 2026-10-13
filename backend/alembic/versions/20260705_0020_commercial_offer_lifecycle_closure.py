"""commercial offer lifecycle closure fields

Revision ID: 20260705_0020
Revises: 20260705_0019
Create Date: 2026-07-05
"""

import sqlalchemy as sa
from alembic import op


revision = "20260705_0020"
down_revision = "20260705_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("crm_commercial_offer", sa.Column("submitted_at", sa.DateTime(), nullable=True))
    op.add_column(
        "crm_commercial_offer",
        sa.Column("submission_reference", sa.Unicode(length=255), nullable=True),
    )
    op.add_column(
        "crm_commercial_offer",
        sa.Column("submission_proof_note", sa.UnicodeText(), nullable=True),
    )
    op.add_column("crm_commercial_offer", sa.Column("outcome_date", sa.Date(), nullable=True))
    op.add_column("crm_commercial_offer", sa.Column("outcome_remarks", sa.UnicodeText(), nullable=True))


def downgrade() -> None:
    op.drop_column("crm_commercial_offer", "outcome_remarks")
    op.drop_column("crm_commercial_offer", "outcome_date")
    op.drop_column("crm_commercial_offer", "submission_proof_note")
    op.drop_column("crm_commercial_offer", "submission_reference")
    op.drop_column("crm_commercial_offer", "submitted_at")
