"""lead conversion foundation

Revision ID: 20260705_0016
Revises: 20260705_0015
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260705_0016"
down_revision: Union[str, None] = "20260705_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UNIQUE_SOURCE_LEAD_INDEX = "ux_crm_opportunity_source_lead_id_not_null"


def upgrade() -> None:
    # One Lead may produce at most one conversion-created Opportunity. The SQL Server filtered
    # unique index becomes a PostgreSQL partial unique index with identical semantics: rows with
    # a NULL source_lead_id are excluded and remain unconstrained.
    op.create_index(
        UNIQUE_SOURCE_LEAD_INDEX,
        "crm_opportunity",
        ["source_lead_id"],
        unique=True,
        postgresql_where=sa.text("source_lead_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(UNIQUE_SOURCE_LEAD_INDEX, table_name="crm_opportunity")
