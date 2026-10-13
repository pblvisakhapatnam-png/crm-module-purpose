"""Commercial Offer versions (Slice 9F).

Revision ID: 20260908_0054
Revises: 20260908_0053
Create Date: 2026-10-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260908_0054"
down_revision: Union[str, None] = "20260908_0053"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OFFER_CODE_INDEX = "ux_crm_commercial_offer_code_not_null"
OFFER_CODE_VERSION_INDEX = "ux_crm_commercial_offer_code_version_not_null"
ACTIVE_BASE_INDEX = "ux_crm_commercial_offer_one_active_base_per_opportunity"
PREVIOUS_VERSION_INDEX = "ix_crm_commercial_offer_previous_version"
INACTIVE_STATUSES = ("WITHDRAWN", "REJECTED", "CLOSED", "REVISED", "ABANDONED")
PREPARATION_STATUSES = ("DRAFT", "READY_FOR_REVIEW")
ACTIVE_BASE_OFFER = (
    "offer_purpose = 'BASE' AND offer_status_code NOT IN ("
    + ", ".join(f"'{status}'" for status in INACTIVE_STATUSES)
    + ") AND (previous_version_offer_id IS NULL OR offer_status_code NOT IN ("
    + ", ".join(f"'{status}'" for status in PREPARATION_STATUSES)
    + "))"
)


def version_history_count(bind) -> int:
    """Return rows that the pre-9F schema cannot represent."""
    return int(
        bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM crm_commercial_offer
                WHERE version_number <> 1 OR previous_version_offer_id IS NOT NULL
                """
            )
        ).scalar_one()
    )


def assert_no_version_history(bind) -> None:
    if version_history_count(bind):
        raise RuntimeError(
            "20260908_0054 cannot be downgraded while Commercial Offer version rows exist. "
            "They cannot be represented by the earlier unique offer-code and active-offer rules."
        )


def upgrade() -> None:
    op.add_column(
        "crm_commercial_offer",
        sa.Column("version_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "crm_commercial_offer",
        sa.Column("previous_version_offer_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "crm_commercial_offer",
        sa.Column("version_reason", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "crm_commercial_offer",
        sa.Column("version_note", sa.UnicodeText(), nullable=True),
    )
    op.create_check_constraint(
        "ck_crm_commercial_offer_version_number",
        "crm_commercial_offer",
        "version_number >= 1",
    )
    op.create_foreign_key(
        "fk_crm_commercial_offer_previous_version",
        "crm_commercial_offer",
        "crm_commercial_offer",
        ["previous_version_offer_id"],
        ["id"],
    )
    op.create_index(PREVIOUS_VERSION_INDEX, "crm_commercial_offer", ["previous_version_offer_id"])

    op.drop_index(OFFER_CODE_INDEX, table_name="crm_commercial_offer")
    op.create_index(
        OFFER_CODE_VERSION_INDEX,
        "crm_commercial_offer",
        ["offer_code", "version_number"],
        unique=True,
        postgresql_where=sa.text("offer_code IS NOT NULL"),
    )

    op.drop_index(ACTIVE_BASE_INDEX, table_name="crm_commercial_offer")
    op.create_index(
        ACTIVE_BASE_INDEX,
        "crm_commercial_offer",
        ["opportunity_id"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_BASE_OFFER),
    )

    op.execute(
        """
        INSERT INTO workflow_status (
            public_id, module, status_code, status_name, is_active, sort_order
        )
        SELECT '00000000-0000-0000-0000-000000000609', 'commercial_offer',
               'ABANDONED', 'Abandoned', TRUE, 45
        WHERE NOT EXISTS (
            SELECT 1 FROM workflow_status
            WHERE module = 'commercial_offer' AND status_code = 'ABANDONED'
        )
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    assert_no_version_history(bind)

    op.drop_index(ACTIVE_BASE_INDEX, table_name="crm_commercial_offer")
    old_active = "offer_purpose = 'BASE' AND offer_status_code NOT IN ('WITHDRAWN', 'REJECTED', 'CLOSED')"
    op.create_index(
        ACTIVE_BASE_INDEX,
        "crm_commercial_offer",
        ["opportunity_id"],
        unique=True,
        postgresql_where=sa.text(old_active),
    )

    op.drop_index(OFFER_CODE_VERSION_INDEX, table_name="crm_commercial_offer")
    op.create_index(
        OFFER_CODE_INDEX,
        "crm_commercial_offer",
        ["offer_code"],
        unique=True,
        postgresql_where=sa.text("offer_code IS NOT NULL"),
    )
    op.drop_index(PREVIOUS_VERSION_INDEX, table_name="crm_commercial_offer")
    op.drop_constraint("fk_crm_commercial_offer_previous_version", "crm_commercial_offer", type_="foreignkey")
    op.drop_constraint("ck_crm_commercial_offer_version_number", "crm_commercial_offer", type_="check")
    op.drop_column("crm_commercial_offer", "version_note")
    op.drop_column("crm_commercial_offer", "version_reason")
    op.drop_column("crm_commercial_offer", "previous_version_offer_id")
    op.drop_column("crm_commercial_offer", "version_number")
    op.execute(
        """
        DELETE FROM workflow_status
        WHERE public_id = '00000000-0000-0000-0000-000000000609'
          AND module = 'commercial_offer'
          AND status_code = 'ABANDONED'
        """
    )
