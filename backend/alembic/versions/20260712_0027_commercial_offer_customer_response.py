"""commercial offer customer response award outcome foundation

Revision ID: 20260712_0027
Revises: 20260711_0026
Create Date: 2026-07-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260712_0027"
down_revision: Union[str, None] = "20260711_0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_offer_customer_response",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("commercial_offer_id", sa.Integer(), nullable=False),
        sa.Column("response_outcome", sa.String(length=50), nullable=False),
        sa.Column("response_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("response_received_at", sa.DateTime(), nullable=False),
        sa.Column("response_channel", sa.String(length=50), nullable=False),
        sa.Column("received_from", sa.Unicode(length=255), nullable=True),
        sa.Column("awarded_amount_snapshot", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("awarded_currency_snapshot", sa.String(length=3), nullable=True),
        sa.Column("awarded_version_snapshot", sa.Unicode(length=100), nullable=True),
        sa.Column("customer_po_or_wo_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("customer_response_notes", sa.UnicodeText(), nullable=True),
        sa.Column("linked_submission_evidence_id", sa.Integer(), nullable=True),
        sa.Column("linked_revision_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_commercial_offer_customer_response"),
        sa.UniqueConstraint("public_id", name="uq_commercial_offer_customer_response_public_id"),
        sa.CheckConstraint(
            """
            response_outcome IN (
                'ACCEPTED_AWARDED', 'REJECTED_LOST', 'REVISION_REQUESTED',
                'CLARIFICATION_REQUESTED', 'ON_HOLD', 'PENDING_CUSTOMER_DECISION', 'OTHER'
            )
            """,
            name="ck_commercial_offer_customer_response_outcome",
        ),
        sa.CheckConstraint(
            """
            response_channel IN (
                'EMAIL', 'TENDER_PORTAL', 'CUSTOMER_PO', 'LETTER_OF_AWARD',
                'PHONE_OR_VERBAL', 'MEETING', 'OTHER'
            )
            """,
            name="ck_commercial_offer_customer_response_channel",
        ),
        sa.CheckConstraint(
            "awarded_amount_snapshot IS NULL OR awarded_amount_snapshot >= 0",
            name="ck_commercial_offer_customer_response_amount",
        ),
        sa.ForeignKeyConstraint(
            ["commercial_offer_id"],
            ["crm_commercial_offer.id"],
            name="fk_commercial_offer_customer_response_offer",
        ),
        sa.ForeignKeyConstraint(
            ["linked_submission_evidence_id"],
            ["commercial_offer_submission_evidence.id"],
            name="fk_commercial_offer_customer_response_evidence",
        ),
        sa.ForeignKeyConstraint(
            ["linked_revision_id"],
            ["commercial_offer_revision.id"],
            name="fk_commercial_offer_customer_response_revision",
        ),
    )

    for index_name, columns in (
        ("ix_commercial_offer_customer_response_offer", ["commercial_offer_id"]),
        ("ix_commercial_offer_customer_response_received_at", ["response_received_at"]),
        ("ix_commercial_offer_customer_response_outcome", ["response_outcome"]),
        ("ix_commercial_offer_customer_response_evidence", ["linked_submission_evidence_id"]),
        ("ix_commercial_offer_customer_response_revision", ["linked_revision_id"]),
    ):
        op.create_index(index_name, "commercial_offer_customer_response", columns, unique=False)


def downgrade() -> None:
    op.drop_table("commercial_offer_customer_response")
