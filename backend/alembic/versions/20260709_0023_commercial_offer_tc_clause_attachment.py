"""commercial offer tc clause attachment foundation

Revision ID: 20260709_0023
Revises: 20260709_0022
Create Date: 2026-07-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260709_0023"
down_revision: Union[str, None] = "20260709_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_offer_tc_clause",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("commercial_offer_id", sa.Integer(), nullable=False),
        sa.Column("tc_clause_id", sa.Integer(), nullable=False),
        sa.Column("clause_id_snapshot", sa.Unicode(length=50), nullable=False),
        sa.Column("title_snapshot", sa.Unicode(length=255), nullable=False),
        sa.Column("clause_text_snapshot", sa.UnicodeText(), nullable=False),
        sa.Column("business_line_snapshot", sa.String(length=50), nullable=False),
        sa.Column("clause_category_snapshot", sa.Unicode(length=100), nullable=False),
        sa.Column("source_clause_number_snapshot", sa.Unicode(length=255), nullable=True),
        sa.Column("source_reference_snapshot", sa.Unicode(length=500), nullable=True),
        sa.Column(
            "mandatory_default_snapshot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("risk_category_snapshot", sa.Unicode(length=100), nullable=True),
        sa.Column(
            "applies_to_header_snapshot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "applies_to_line_snapshot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "requires_approval_if_omitted_snapshot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "requires_approval_if_modified_snapshot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("attached_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_commercial_offer_tc_clause"),
        sa.UniqueConstraint("public_id", name="uq_commercial_offer_tc_clause_public_id"),
        sa.ForeignKeyConstraint(
            ["commercial_offer_id"],
            ["crm_commercial_offer.id"],
            name="fk_commercial_offer_tc_clause_offer",
        ),
        sa.ForeignKeyConstraint(
            ["tc_clause_id"],
            ["tc_clause_library.id"],
            name="fk_commercial_offer_tc_clause_library",
        ),
    )

    for index_name, columns in (
        ("ix_commercial_offer_tc_clause_offer", ["commercial_offer_id"]),
        ("ix_commercial_offer_tc_clause_library", ["tc_clause_id"]),
        ("ix_commercial_offer_tc_clause_active", ["active"]),
    ):
        op.create_index(index_name, "commercial_offer_tc_clause", columns, unique=False)

    # A library clause may be attached to one Commercial Offer only once while active. Removed
    # (inactive) attachments are excluded, so the same clause can be re-attached after removal.
    op.create_index(
        "uq_commercial_offer_tc_clause_active_clause",
        "commercial_offer_tc_clause",
        ["commercial_offer_id", "tc_clause_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )


def downgrade() -> None:
    op.drop_table("commercial_offer_tc_clause")
