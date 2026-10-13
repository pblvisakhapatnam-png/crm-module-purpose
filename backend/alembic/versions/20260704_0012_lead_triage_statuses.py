"""lead triage statuses

Revision ID: 20260704_0012
Revises: 20260704_0011
Create Date: 2026-07-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260704_0012"
down_revision: Union[str, None] = "20260704_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TRIAGE_STATUSES = [
    {
        "public_id": "00000000-0000-0000-0000-000000000406",
        "module": "lead",
        "status_code": "CONTACTED",
        "status_name": "Contacted",
        "sort_order": 25,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000407",
        "module": "lead",
        "status_code": "UNDER_REVIEW",
        "status_name": "Under Review",
        "sort_order": 28,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000408",
        "module": "lead",
        "status_code": "UNQUALIFIED",
        "status_name": "Unqualified",
        "sort_order": 45,
    },
]


INSERT_STATUS_IF_ABSENT = sa.text(
    """
    INSERT INTO workflow_status (
        public_id, module, status_code, status_name, is_active, sort_order
    )
    -- :module and :status_code are also used in the WHERE EXISTS below. Without an explicit
    -- cast PostgreSQL deduces "text" for the SELECT-list occurrence and "character varying"
    -- for the comparison, and rejects the statement as an ambiguous parameter.
    SELECT :public_id, CAST(:module AS VARCHAR), CAST(:status_code AS VARCHAR), :status_name, TRUE, :sort_order
    WHERE NOT EXISTS (
        SELECT 1
        FROM workflow_status
        WHERE module = :module
          AND status_code = :status_code
    )
    """
)


def upgrade() -> None:
    connection = op.get_bind()

    for row in TRIAGE_STATUSES:
        connection.execute(INSERT_STATUS_IF_ABSENT, row)


def downgrade() -> None:
    status_codes = ", ".join(f"'{row['status_code']}'" for row in TRIAGE_STATUSES)
    op.execute(
        f"""
        DELETE FROM workflow_status
        WHERE module = 'lead'
          AND status_code IN ({status_codes})
        """
    )
