"""commercial offer revision resubmission foundation

Revision ID: 20260711_0026
Revises: 20260710_0025
Create Date: 2026-07-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260711_0026"
down_revision: Union[str, None] = "20260710_0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_offer_revision",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("commercial_offer_id", sa.Integer(), nullable=False),
        sa.Column("revision_label", sa.Unicode(length=100), nullable=False),
        sa.Column("revision_reason", sa.String(length=50), nullable=False),
        sa.Column("revision_notes", sa.UnicodeText(), nullable=True),
        sa.Column("revision_status", sa.String(length=50), nullable=False),
        sa.Column("source_submission_evidence_id", sa.Integer(), nullable=True),
        sa.Column("resubmission_evidence_id", sa.Integer(), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("opened_by", sa.String(length=36), nullable=True),
        sa.Column("resubmitted_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_commercial_offer_revision"),
        sa.UniqueConstraint("public_id", name="uq_commercial_offer_revision_public_id"),
        sa.CheckConstraint(
            "revision_status IN ('OPEN', 'RESUBMITTED', 'CANCELLED')",
            name="ck_commercial_offer_revision_status",
        ),
        sa.CheckConstraint(
            """
            revision_reason IN (
                'CUSTOMER_CLARIFICATION',
                'RATE_CORRECTION',
                'SCOPE_CHANGE',
                'TENDER_CORRIGENDUM',
                'INTERNAL_CORRECTION',
                'OTHER'
            )
            """,
            name="ck_commercial_offer_revision_reason",
        ),
        sa.ForeignKeyConstraint(
            ["commercial_offer_id"],
            ["crm_commercial_offer.id"],
            name="fk_commercial_offer_revision_offer",
        ),
        sa.ForeignKeyConstraint(
            ["source_submission_evidence_id"],
            ["commercial_offer_submission_evidence.id"],
            name="fk_commercial_offer_revision_source_evidence",
        ),
        sa.ForeignKeyConstraint(
            ["resubmission_evidence_id"],
            ["commercial_offer_submission_evidence.id"],
            name="fk_commercial_offer_revision_resubmission_evidence",
        ),
    )

    for index_name, columns in (
        ("ix_commercial_offer_revision_offer", ["commercial_offer_id"]),
        ("ix_commercial_offer_revision_status", ["revision_status"]),
        ("ix_commercial_offer_revision_opened_at", ["opened_at"]),
        ("ix_commercial_offer_revision_source_evidence", ["source_submission_evidence_id"]),
        ("ix_commercial_offer_revision_resubmission_evidence", ["resubmission_evidence_id"]),
    ):
        op.create_index(index_name, "commercial_offer_revision", columns, unique=False)


def downgrade() -> None:
    op.drop_table("commercial_offer_revision")
