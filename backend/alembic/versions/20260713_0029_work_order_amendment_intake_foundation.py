"""work order amendment intake foundation

Slice 6O.2 adds crm_work_order_amendment (header) and
crm_work_order_amendment_line (proposed line-level deltas). These are intake
and review records only - they are never applied to crm_work_order or
crm_work_order_line, and neither of those tables (nor crm_commercial_offer)
gains a column here. The frozen Slice 6D.1 handoff contract and the Slice
6O.1 related-offer contract are unaffected.

Revision ID: 20260713_0029
Revises: 20260712_0028
Create Date: 2026-07-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260713_0029"
down_revision: Union[str, None] = "20260712_0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_work_order_amendment",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("amendment_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("amendment_sequence_no", sa.Integer(), nullable=False),
        sa.Column("amendment_type_code", sa.String(length=50), nullable=False),
        sa.Column(
            "amendment_status_code",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'RECEIVED'"),
        ),
        sa.Column("customer_amendment_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("customer_amendment_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("amendment_reason", sa.Unicode(length=2000), nullable=False),
        sa.Column("administrative_change_summary", sa.Unicode(length=2000), nullable=True),
        sa.Column("commercial_change_summary", sa.Unicode(length=2000), nullable=True),
        sa.Column("related_commercial_offer_id", sa.Integer(), nullable=True),
        sa.Column("customer_document_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("decision_notes", sa.Unicode(length=2000), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("validated_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("decided_by", sa.String(length=36), nullable=True),
        sa.Column("remarks", sa.UnicodeText(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_crm_work_order_amendment"),
        sa.UniqueConstraint("amendment_public_id", name="uq_crm_work_order_amendment_public_id"),
        sa.UniqueConstraint(
            "work_order_id",
            "amendment_sequence_no",
            name="uq_crm_work_order_amendment_wo_sequence",
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["crm_work_order.id"],
            name="fk_crm_work_order_amendment_work_order",
        ),
        sa.ForeignKeyConstraint(
            ["related_commercial_offer_id"],
            ["crm_commercial_offer.id"],
            name="fk_crm_work_order_amendment_related_offer",
        ),
        sa.CheckConstraint(
            "amendment_type_code IN ('ADMINISTRATIVE', 'COMMERCIAL', 'MIXED')",
            name="ck_crm_work_order_amendment_type",
        ),
        sa.CheckConstraint(
            """
            amendment_status_code IN (
                'RECEIVED', 'UNDER_REVIEW', 'VALIDATED', 'REJECTED', 'CANCELLED'
            )
            """,
            name="ck_crm_work_order_amendment_status",
        ),
        sa.CheckConstraint(
            "amendment_type_code = 'ADMINISTRATIVE' OR commercial_change_summary IS NOT NULL",
            name="ck_crm_work_order_amendment_commercial_summary",
        ),
    )

    # A customer amendment reference is unique per Work Order when supplied; amendments recorded
    # without a customer reference are excluded from the constraint.
    op.create_index(
        "ux_crm_work_order_amendment_customer_reference",
        "crm_work_order_amendment",
        ["work_order_id", "customer_amendment_reference"],
        unique=True,
        postgresql_where=sa.text("customer_amendment_reference IS NOT NULL"),
    )

    for index_name, columns in (
        ("ix_crm_work_order_amendment_work_order", ["work_order_id"]),
        ("ix_crm_work_order_amendment_status", ["amendment_status_code"]),
        ("ix_crm_work_order_amendment_related_offer", ["related_commercial_offer_id"]),
        ("ix_crm_work_order_amendment_created_at", ["created_at"]),
    ):
        op.create_index(index_name, "crm_work_order_amendment", columns, unique=False)

    op.create_table(
        "crm_work_order_amendment_line",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("amendment_line_public_id", sa.String(length=36), nullable=False),
        sa.Column("amendment_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("action_code", sa.String(length=20), nullable=False),
        sa.Column("source_work_order_line_id", sa.Integer(), nullable=True),
        sa.Column("change_summary", sa.Unicode(length=2000), nullable=True),
        sa.Column("proposed_scope_description", sa.Unicode(length=1000), nullable=True),
        sa.Column("proposed_equipment_service_category", sa.Unicode(length=255), nullable=True),
        sa.Column("proposed_quantity", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("proposed_uom", sa.String(length=50), nullable=True),
        sa.Column("proposed_rate_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("proposed_currency_code", sa.String(length=3), nullable=True),
        sa.Column("proposed_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("original_scope_description", sa.Unicode(length=1000), nullable=True),
        sa.Column("original_equipment_service_category", sa.Unicode(length=255), nullable=True),
        sa.Column("original_quantity", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("original_uom", sa.String(length=50), nullable=True),
        sa.Column("original_rate_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("original_currency_code", sa.String(length=3), nullable=True),
        sa.Column("original_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("original_source_offer_line_public_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_crm_work_order_amendment_line"),
        sa.UniqueConstraint(
            "amendment_line_public_id",
            name="uq_crm_work_order_amendment_line_public_id",
        ),
        sa.UniqueConstraint(
            "amendment_id",
            "line_number",
            name="uq_crm_work_order_amendment_line_number",
        ),
        sa.ForeignKeyConstraint(
            ["amendment_id"],
            ["crm_work_order_amendment.id"],
            name="fk_crm_work_order_amendment_line_amendment",
        ),
        sa.ForeignKeyConstraint(
            ["source_work_order_line_id"],
            ["crm_work_order_line.id"],
            name="fk_crm_work_order_amendment_line_source",
        ),
        sa.CheckConstraint(
            "action_code IN ('ADD_LINE', 'CHANGE_LINE', 'CANCEL_LINE')",
            name="ck_crm_work_order_amendment_line_action",
        ),
        sa.CheckConstraint(
            """
            (action_code = 'ADD_LINE' AND source_work_order_line_id IS NULL)
            OR (action_code IN ('CHANGE_LINE', 'CANCEL_LINE') AND source_work_order_line_id IS NOT NULL)
            """,
            name="ck_crm_work_order_amendment_line_source_required",
        ),
        sa.CheckConstraint(
            "proposed_quantity IS NULL OR proposed_quantity > 0",
            name="ck_crm_work_order_amendment_line_qty",
        ),
        sa.CheckConstraint(
            "proposed_rate_amount IS NULL OR proposed_rate_amount >= 0",
            name="ck_crm_work_order_amendment_line_rate",
        ),
        sa.CheckConstraint(
            "proposed_amount IS NULL OR proposed_amount >= 0",
            name="ck_crm_work_order_amendment_line_amount",
        ),
    )

    for index_name, columns in (
        ("ix_crm_work_order_amendment_line_amendment", ["amendment_id"]),
        ("ix_crm_work_order_amendment_line_source", ["source_work_order_line_id"]),
    ):
        op.create_index(index_name, "crm_work_order_amendment_line", columns, unique=False)


def downgrade() -> None:
    op.drop_table("crm_work_order_amendment_line")
    op.drop_table("crm_work_order_amendment")
