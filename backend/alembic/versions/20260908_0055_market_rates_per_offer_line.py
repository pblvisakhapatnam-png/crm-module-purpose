"""Market rates per offer line, with each line's basis history (Slice 4G).

Revision ID: 20260908_0055
Revises: 20260908_0054
Create Date: 2026-10-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260908_0055"
down_revision: Union[str, None] = "20260908_0054"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LINE_TABLE = "crm_commercial_offer_line"
EVIDENCE_TABLE = "crm_commercial_offer_pricing_evidence"
CHOICE_TABLE = "crm_commercial_offer_line_basis_choice"

LINE_OFFER_UNIQUE = "uq_crm_commercial_offer_line_id_offer"
EVIDENCE_LINE_UNIQUE = "uq_crm_commercial_offer_pricing_evidence_id_line"
EVIDENCE_LINE_FK = "fk_crm_commercial_offer_pricing_evidence_line"
EVIDENCE_QUOTE_COPY_FK = "fk_crm_commercial_offer_pricing_evidence_quote_copy"
EVIDENCE_WHOLE_OFFER_CHECK = "ck_crm_commercial_offer_pricing_evidence_line_or_whole_offer"
EVIDENCE_QUOTE_COPY_EARLIER_CHECK = "ck_crm_commercial_offer_pricing_evidence_quote_copy_earlier"
EVIDENCE_OFFER_UNIQUE = "uq_crm_commercial_offer_pricing_evidence_id_offer"
OFFER_PREVIOUS_UNIQUE = "uq_crm_commercial_offer_id_previous_version"
EVIDENCE_COPIED_FROM_FK = "fk_crm_commercial_offer_pricing_evidence_copied_from"
EVIDENCE_COPIED_FROM_LINEAGE_FK = "fk_crm_commercial_offer_pricing_evidence_copied_from_lineage"
EVIDENCE_COPIED_FROM_PAIR_CHECK = "ck_crm_commercial_offer_pricing_evidence_copied_from_pair"
EVIDENCE_COPIED_FROM_EARLIER_CHECK = "ck_crm_commercial_offer_pricing_evidence_copied_from_earlier"
EVIDENCE_ONE_LINK_CHECK = "ck_crm_commercial_offer_pricing_evidence_one_quote_link"
EVIDENCE_LINE_INDEX = "ix_crm_commercial_offer_pricing_evidence_line"
OLD_ONE_SELECTED_INDEX = "ux_crm_commercial_offer_pricing_evidence_one_selected"
LINE_RATE_MARKER_CHECK = "ck_crm_commercial_offer_pricing_evidence_line_basis_in_history"
ONE_WHOLE_OFFER_BASIS_INDEX = "ux_crm_commercial_offer_pricing_evidence_one_whole_offer_basis"
ONE_OPEN_CHOICE_INDEX = "ux_crm_commercial_offer_line_basis_choice_one_open"


def assert_no_per_line_rates(bind) -> None:
    """Refuse to go back while any rate names a line: the earlier schema cannot hold it."""
    count = int(
        bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {EVIDENCE_TABLE} WHERE commercial_offer_line_id IS NOT NULL")
        ).scalar_one()
    )
    if count:
        raise RuntimeError(
            f"{count} market rate(s) belong to an offer line; the schema before 20260908_0055 cannot hold them. "
            "Restore the backup taken before the upgrade instead."
        )


def upgrade() -> None:
    # A rate's line must be a line of the rate's own offer, so the line table offers (id, offer) as a key.
    op.create_unique_constraint(LINE_OFFER_UNIQUE, LINE_TABLE, ["id", "commercial_offer_id"])

    op.add_column(EVIDENCE_TABLE, sa.Column("commercial_offer_line_id", sa.Integer(), nullable=True))
    op.add_column(
        EVIDENCE_TABLE,
        sa.Column("recorded_for_whole_offer", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(EVIDENCE_TABLE, sa.Column("quote_copy_evidence_id", sa.Integer(), nullable=True))
    op.add_column(EVIDENCE_TABLE, sa.Column("copied_from_evidence_id", sa.Integer(), nullable=True))
    op.add_column(EVIDENCE_TABLE, sa.Column("copied_from_offer_id", sa.Integer(), nullable=True))

    # Every rate recorded before this change belongs to the whole offer. It keeps no line: none is guessed.
    op.execute(f"UPDATE {EVIDENCE_TABLE} SET recorded_for_whole_offer = TRUE")

    op.create_check_constraint(
        EVIDENCE_WHOLE_OFFER_CHECK,
        EVIDENCE_TABLE,
        "(commercial_offer_line_id IS NULL) = recorded_for_whole_offer",
    )
    op.create_foreign_key(
        EVIDENCE_LINE_FK,
        EVIDENCE_TABLE,
        LINE_TABLE,
        ["commercial_offer_line_id", "commercial_offer_id"],
        ["id", "commercial_offer_id"],
    )
    # Two kinds of quote link, each held by the database to where it may point (review 4G-R4-005): a user's reference
    # to another rate of the same offer, and a new version's rate's link to the rate it was copied from, on the offer
    # its own offer was made from. A rate has at most one of them.
    op.create_unique_constraint(EVIDENCE_OFFER_UNIQUE, EVIDENCE_TABLE, ["id", "commercial_offer_id"])
    op.create_unique_constraint(OFFER_PREVIOUS_UNIQUE, "crm_commercial_offer", ["id", "previous_version_offer_id"])
    op.create_foreign_key(
        EVIDENCE_QUOTE_COPY_FK,
        EVIDENCE_TABLE,
        EVIDENCE_TABLE,
        ["quote_copy_evidence_id", "commercial_offer_id"],
        ["id", "commercial_offer_id"],
    )
    op.create_foreign_key(
        EVIDENCE_COPIED_FROM_FK,
        EVIDENCE_TABLE,
        EVIDENCE_TABLE,
        ["copied_from_evidence_id", "copied_from_offer_id"],
        ["id", "commercial_offer_id"],
    )
    op.create_foreign_key(
        EVIDENCE_COPIED_FROM_LINEAGE_FK,
        EVIDENCE_TABLE,
        "crm_commercial_offer",
        ["commercial_offer_id", "copied_from_offer_id"],
        ["id", "previous_version_offer_id"],
    )
    op.create_check_constraint(
        EVIDENCE_COPIED_FROM_PAIR_CHECK,
        EVIDENCE_TABLE,
        "(copied_from_evidence_id IS NULL) = (copied_from_offer_id IS NULL)",
    )
    op.create_check_constraint(
        EVIDENCE_ONE_LINK_CHECK,
        EVIDENCE_TABLE,
        "quote_copy_evidence_id IS NULL OR copied_from_evidence_id IS NULL",
    )
    op.create_check_constraint(
        EVIDENCE_COPIED_FROM_EARLIER_CHECK,
        EVIDENCE_TABLE,
        "copied_from_evidence_id IS NULL OR copied_from_evidence_id < id",
    )
    # A rate refers only to a rate entered before it (a smaller id), never to itself or a later one, so a chain of
    # quote references always ends and cannot loop (review 4G-R3-001).
    op.create_check_constraint(
        EVIDENCE_QUOTE_COPY_EARLIER_CHECK,
        EVIDENCE_TABLE,
        "quote_copy_evidence_id IS NULL OR quote_copy_evidence_id < id",
    )
    op.create_unique_constraint(EVIDENCE_LINE_UNIQUE, EVIDENCE_TABLE, ["id", "commercial_offer_line_id"])
    op.create_index(EVIDENCE_LINE_INDEX, EVIDENCE_TABLE, ["commercial_offer_line_id"], unique=False)

    # A line's basis is its open choice in the history below, one per line (review 4G-R1-002): one record, so the two
    # cannot disagree. is_selected_basis stays only for rates recorded for the whole offer, which keep one per offer.
    op.drop_index(OLD_ONE_SELECTED_INDEX, table_name=EVIDENCE_TABLE)
    op.create_check_constraint(
        LINE_RATE_MARKER_CHECK,
        EVIDENCE_TABLE,
        "recorded_for_whole_offer OR NOT is_selected_basis",
    )
    op.create_index(
        ONE_WHOLE_OFFER_BASIS_INDEX,
        EVIDENCE_TABLE,
        ["commercial_offer_id"],
        unique=True,
        postgresql_where=sa.text("is_selected_basis AND commercial_offer_line_id IS NULL"),
    )

    # Each line's basis history. A choice is ended, never rewritten or deleted.
    op.create_table(
        CHOICE_TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("choice_public_id", sa.String(length=36), nullable=False),
        sa.Column("commercial_offer_line_id", sa.Integer(), nullable=False),
        sa.Column("pricing_evidence_id", sa.Integer(), nullable=False),
        sa.Column("selection_reason", sa.UnicodeText(), nullable=False),
        sa.Column("chosen_by", sa.String(length=36), nullable=True),
        sa.Column("chosen_at", sa.DateTime(), nullable=False),
        sa.Column("ended_by", sa.String(length=36), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("carried_from_choice_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_crm_commercial_offer_line_basis_choice"),
        sa.UniqueConstraint("choice_public_id", name="uq_crm_commercial_offer_line_basis_choice_public_id"),
        sa.ForeignKeyConstraint(
            ["pricing_evidence_id", "commercial_offer_line_id"],
            [f"{EVIDENCE_TABLE}.id", f"{EVIDENCE_TABLE}.commercial_offer_line_id"],
            name="fk_crm_commercial_offer_line_basis_choice_rate_on_line",
        ),
        sa.ForeignKeyConstraint(
            ["commercial_offer_line_id"],
            [f"{LINE_TABLE}.id"],
            name="fk_crm_commercial_offer_line_basis_choice_line",
        ),
        sa.ForeignKeyConstraint(
            ["carried_from_choice_id"],
            [f"{CHOICE_TABLE}.id"],
            name="fk_crm_commercial_offer_line_basis_choice_carried_from",
        ),
        sa.CheckConstraint(
            "length(btrim(selection_reason)) > 0",
            name="ck_crm_commercial_offer_line_basis_choice_reason",
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= chosen_at",
            name="ck_crm_commercial_offer_line_basis_choice_ended_after_chosen",
        ),
    )
    op.create_index(
        "ix_crm_commercial_offer_line_basis_choice_line",
        CHOICE_TABLE,
        ["commercial_offer_line_id", "chosen_at"],
        unique=False,
    )
    op.create_index(
        "ix_crm_commercial_offer_line_basis_choice_rate",
        CHOICE_TABLE,
        ["pricing_evidence_id"],
        unique=False,
    )
    op.create_index(
        ONE_OPEN_CHOICE_INDEX,
        CHOICE_TABLE,
        ["commercial_offer_line_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )


def downgrade() -> None:
    assert_no_per_line_rates(op.get_bind())

    op.drop_table(CHOICE_TABLE)
    op.drop_index(ONE_WHOLE_OFFER_BASIS_INDEX, table_name=EVIDENCE_TABLE)
    op.drop_constraint(LINE_RATE_MARKER_CHECK, EVIDENCE_TABLE, type_="check")
    op.create_index(
        OLD_ONE_SELECTED_INDEX,
        EVIDENCE_TABLE,
        ["commercial_offer_id"],
        unique=True,
        postgresql_where=sa.text("is_selected_basis"),
    )
    op.drop_index(EVIDENCE_LINE_INDEX, table_name=EVIDENCE_TABLE)
    op.drop_constraint(EVIDENCE_LINE_UNIQUE, EVIDENCE_TABLE, type_="unique")
    op.drop_constraint(EVIDENCE_QUOTE_COPY_EARLIER_CHECK, EVIDENCE_TABLE, type_="check")
    op.drop_constraint(EVIDENCE_COPIED_FROM_EARLIER_CHECK, EVIDENCE_TABLE, type_="check")
    op.drop_constraint(EVIDENCE_ONE_LINK_CHECK, EVIDENCE_TABLE, type_="check")
    op.drop_constraint(EVIDENCE_COPIED_FROM_PAIR_CHECK, EVIDENCE_TABLE, type_="check")
    op.drop_constraint(EVIDENCE_COPIED_FROM_LINEAGE_FK, EVIDENCE_TABLE, type_="foreignkey")
    op.drop_constraint(EVIDENCE_COPIED_FROM_FK, EVIDENCE_TABLE, type_="foreignkey")
    op.drop_constraint(EVIDENCE_QUOTE_COPY_FK, EVIDENCE_TABLE, type_="foreignkey")
    op.drop_constraint(OFFER_PREVIOUS_UNIQUE, "crm_commercial_offer", type_="unique")
    op.drop_constraint(EVIDENCE_OFFER_UNIQUE, EVIDENCE_TABLE, type_="unique")
    op.drop_column(EVIDENCE_TABLE, "copied_from_offer_id")
    op.drop_column(EVIDENCE_TABLE, "copied_from_evidence_id")
    op.drop_constraint(EVIDENCE_LINE_FK, EVIDENCE_TABLE, type_="foreignkey")
    op.drop_constraint(EVIDENCE_WHOLE_OFFER_CHECK, EVIDENCE_TABLE, type_="check")
    op.drop_column(EVIDENCE_TABLE, "quote_copy_evidence_id")
    op.drop_column(EVIDENCE_TABLE, "recorded_for_whole_offer")
    op.drop_column(EVIDENCE_TABLE, "commercial_offer_line_id")
    op.drop_constraint(LINE_OFFER_UNIQUE, LINE_TABLE, type_="unique")
