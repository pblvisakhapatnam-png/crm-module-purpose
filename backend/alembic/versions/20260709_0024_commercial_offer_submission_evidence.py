"""commercial offer submission evidence foundation

Revision ID: 20260709_0024
Revises: 20260709_0023
Create Date: 2026-07-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260709_0024"
down_revision: Union[str, None] = "20260709_0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_offer_submission_evidence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("commercial_offer_id", sa.Integer(), nullable=False),
        sa.Column("submission_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("submission_channel", sa.String(length=50), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_by", sa.String(length=36), nullable=True),
        sa.Column("recipient_summary", sa.Unicode(length=1000), nullable=True),
        sa.Column("submitted_amount_snapshot", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("submitted_currency_snapshot", sa.String(length=3), nullable=True),
        sa.Column("submitted_version_snapshot", sa.Unicode(length=50), nullable=True),
        sa.Column("document_reference_label", sa.Unicode(length=255), nullable=True),
        sa.Column("document_reference_url_or_path", sa.Unicode(length=1000), nullable=True),
        sa.Column("evidence_notes", sa.UnicodeText(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_commercial_offer_submission_evidence"),
        sa.UniqueConstraint("public_id", name="uq_commercial_offer_submission_evidence_public_id"),
        sa.ForeignKeyConstraint(
            ["commercial_offer_id"],
            ["crm_commercial_offer.id"],
            name="fk_commercial_offer_submission_evidence_offer",
        ),
    )

    for index_name, columns in (
        ("ix_commercial_offer_submission_evidence_offer", ["commercial_offer_id"]),
        ("ix_commercial_offer_submission_evidence_submitted_at", ["submitted_at"]),
        ("ix_commercial_offer_submission_evidence_active", ["active"]),
    ):
        op.create_index(index_name, "commercial_offer_submission_evidence", columns, unique=False)


def downgrade() -> None:
    op.drop_table("commercial_offer_submission_evidence")
