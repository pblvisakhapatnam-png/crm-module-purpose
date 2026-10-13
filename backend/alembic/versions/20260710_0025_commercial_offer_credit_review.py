"""commercial offer manual credit review foundation

Revision ID: 20260710_0025
Revises: 20260709_0024
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260710_0025"
down_revision: Union[str, None] = "20260709_0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_offer_credit_review",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("commercial_offer_id", sa.Integer(), nullable=False),
        sa.Column("review_status", sa.String(length=50), nullable=False),
        sa.Column("review_basis", sa.Unicode(length=255), nullable=True),
        sa.Column("review_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=36), nullable=True),
        sa.Column("approved_amount_snapshot", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("credit_days_snapshot", sa.Integer(), nullable=True),
        sa.Column("exposure_note", sa.UnicodeText(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_commercial_offer_credit_review"),
        sa.UniqueConstraint("public_id", name="uq_commercial_offer_credit_review_public_id"),
        sa.CheckConstraint(
            """
            review_status IN (
                'NOT_ASSESSED',
                'WITHIN_LIMIT_AS_PER_MANUAL_REVIEW',
                'APPROVAL_REQUIRED',
                'APPROVED_WITH_REFERENCE',
                'REJECTED_OR_ON_HOLD'
            )
            """,
            name="ck_commercial_offer_credit_review_status",
        ),
        sa.CheckConstraint(
            "approved_amount_snapshot IS NULL OR approved_amount_snapshot >= 0",
            name="ck_commercial_offer_credit_review_amount",
        ),
        sa.CheckConstraint(
            "credit_days_snapshot IS NULL OR credit_days_snapshot BETWEEN 0 AND 3650",
            name="ck_commercial_offer_credit_review_days",
        ),
        sa.ForeignKeyConstraint(
            ["commercial_offer_id"],
            ["crm_commercial_offer.id"],
            name="fk_commercial_offer_credit_review_offer",
        ),
    )

    for index_name, columns in (
        ("ix_commercial_offer_credit_review_offer", ["commercial_offer_id"]),
        ("ix_commercial_offer_credit_review_reviewed_at", ["reviewed_at"]),
        ("ix_commercial_offer_credit_review_active", ["active"]),
    ):
        op.create_index(index_name, "commercial_offer_credit_review", columns, unique=False)

    # Reviews are append-only: at most one current (active) review per Commercial Offer, with any
    # number of superseded (inactive) rows retained as history.
    op.create_index(
        "ux_commercial_offer_credit_review_current",
        "commercial_offer_credit_review",
        ["commercial_offer_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )


def downgrade() -> None:
    op.drop_table("commercial_offer_credit_review")
