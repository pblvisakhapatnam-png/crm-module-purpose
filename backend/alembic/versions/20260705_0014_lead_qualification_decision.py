"""lead qualification decision foundation

Revision ID: 20260705_0014
Revises: 20260704_0013
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260705_0014"
down_revision: Union[str, None] = "20260704_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


QUALIFICATION_STATUSES = [
    {
        "public_id": "00000000-0000-0000-0000-000000000409",
        "module": "lead",
        "status_code": "QUALIFICATION_READY",
        "status_name": "Qualification Ready",
        "sort_order": 32,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000410",
        "module": "lead",
        "status_code": "QUALIFIED",
        "status_name": "Qualified",
        "sort_order": 35,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000411",
        "module": "lead",
        "status_code": "CLOSED",
        "status_name": "Closed",
        "sort_order": 95,
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
    # The original SQL Server implementation guarded every statement with COL_LENGTH/sys.indexes
    # checks because interrupted T-SQL DDL could partially survive a failed run. PostgreSQL runs
    # DDL transactionally, so a failed migration leaves nothing behind and plain operations are
    # both correct and clearer.
    op.add_column("crm_lead", sa.Column("qualification_decision_notes", sa.UnicodeText(), nullable=True))
    op.add_column("crm_lead", sa.Column("qualification_reason", sa.Unicode(length=255), nullable=True))
    op.add_column("crm_lead", sa.Column("qualification_decided_by", sa.String(length=36), nullable=True))
    op.add_column("crm_lead", sa.Column("qualification_decided_at", sa.DateTime(), nullable=True))

    op.create_index(
        "ix_crm_lead_qualification_decided_at",
        "crm_lead",
        ["qualification_decided_at"],
        unique=False,
    )

    connection = op.get_bind()
    for row in QUALIFICATION_STATUSES:
        connection.execute(INSERT_STATUS_IF_ABSENT, row)


def downgrade() -> None:
    status_codes = ", ".join(f"'{row['status_code']}'" for row in QUALIFICATION_STATUSES)
    op.execute(
        f"""
        DELETE FROM workflow_status
        WHERE module = 'lead'
          AND status_code IN ({status_codes})
        """
    )
    op.drop_index("ix_crm_lead_qualification_decided_at", table_name="crm_lead")
    op.drop_column("crm_lead", "qualification_decided_at")
    op.drop_column("crm_lead", "qualification_decided_by")
    op.drop_column("crm_lead", "qualification_reason")
    op.drop_column("crm_lead", "qualification_decision_notes")
