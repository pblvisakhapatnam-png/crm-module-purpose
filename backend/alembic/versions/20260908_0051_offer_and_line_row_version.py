"""A stale form can no longer overwrite an offer or an offer line (TB-1 finding TB1-303, the offer part; CS-05a)

Record: docs/continuity/CS_05A_OFFER_STALE_SAVE_PROTECTION.md.

Until now two people with the same Commercial Offer, or the same offer line, open saved over each other without a
word: the second save replaced every field the first had changed, the offer's status and prices included. The two
edit routes now carry the version the screen loaded and are refused when the record has moved on - the version check
the Hiring modules already make (`detail_version` on a Work Order line's detail, migration `20260908_0036`).

1. `row_version` on `crm_commercial_offer` and on `crm_commercial_offer_line`: 1 when the row is made, raised by one
   on every write of the row the application makes (the offer's edit, marking it submitted, a customer response that
   sets its status; a line's edit). Never below 1. Existing rows start at 1. A page loaded before the upgrade sends no
   version, so its save is refused (422) until the page is reloaded.

Downgrade drops both columns and their checks: the code from before this revision reads neither.

Revision ID: 20260908_0051
Revises: 20260908_0050
Create Date: 2026-10-09
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0051"
down_revision: Union[str, None] = "20260908_0050"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = {
    "crm_commercial_offer": "ck_crm_commercial_offer_row_version",
    "crm_commercial_offer_line": "ck_crm_commercial_offer_line_row_version",
}


def upgrade() -> None:
    for table, check in TABLES.items():
        op.add_column(table, sa.Column("row_version", sa.Integer(), nullable=False, server_default=sa.text("1")))
        op.create_check_constraint(check, table, "row_version >= 1")


def downgrade() -> None:
    for table, check in TABLES.items():
        op.drop_constraint(check, table, type_="check")
        op.drop_column(table, "row_version")
