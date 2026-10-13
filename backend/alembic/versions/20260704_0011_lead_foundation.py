"""lead foundation

Revision ID: 20260704_0011
Revises: 20260704_0010
Create Date: 2026-07-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260704_0011"
down_revision: Union[str, None] = "20260704_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEAD_STATUSES = [
    {
        "public_id": "00000000-0000-0000-0000-000000000401",
        "module": "lead",
        "status_code": "NEW",
        "status_name": "New",
        "is_active": True,
        "sort_order": 10,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000402",
        "module": "lead",
        "status_code": "REVIEW_PENDING",
        "status_name": "Review Pending",
        "is_active": True,
        "sort_order": 20,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000403",
        "module": "lead",
        "status_code": "QUALIFICATION_PENDING",
        "status_name": "Qualification Pending",
        "is_active": True,
        "sort_order": 30,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000404",
        "module": "lead",
        "status_code": "DISQUALIFIED",
        "status_name": "Disqualified",
        "is_active": True,
        "sort_order": 40,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000405",
        "module": "lead",
        "status_code": "CONVERTED",
        "status_name": "Converted",
        "is_active": True,
        "sort_order": 50,
    },
]


def upgrade() -> None:
    op.create_table(
        "crm_lead",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lead_public_id", sa.String(length=36), nullable=False),
        sa.Column("lead_source", sa.String(length=50), nullable=False),
        sa.Column("source_reference", sa.Unicode(length=255), nullable=True),
        sa.Column("company_name", sa.Unicode(length=255), nullable=False),
        sa.Column("contact_name", sa.Unicode(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("requirement_summary", sa.UnicodeText(), nullable=True),
        sa.Column("lead_status_code", sa.String(length=50), nullable=False, server_default="NEW"),
        sa.Column("assigned_to_user_public_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_public_id", name="uq_crm_lead_public_id"),
    )
    op.create_index("ix_crm_lead_status", "crm_lead", ["lead_status_code"], unique=False)
    op.create_index("ix_crm_lead_source", "crm_lead", ["lead_source"], unique=False)
    op.create_index("ix_crm_lead_assigned_to", "crm_lead", ["assigned_to_user_public_id"], unique=False)
    op.create_index("ix_crm_lead_created_at", "crm_lead", ["created_at"], unique=False)

    workflow_status = sa.table(
        "workflow_status",
        sa.column("public_id", sa.String),
        sa.column("module", sa.String),
        sa.column("status_code", sa.String),
        sa.column("status_name", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(workflow_status, LEAD_STATUSES)


def downgrade() -> None:
    status_codes = ", ".join(f"'{row['status_code']}'" for row in LEAD_STATUSES)
    op.execute(
        f"""
        DELETE FROM workflow_status
        WHERE module = 'lead'
          AND status_code IN ({status_codes})
        """
    )
    op.drop_index("ix_crm_lead_created_at", table_name="crm_lead")
    op.drop_index("ix_crm_lead_assigned_to", table_name="crm_lead")
    op.drop_index("ix_crm_lead_source", table_name="crm_lead")
    op.drop_index("ix_crm_lead_status", table_name="crm_lead")
    op.drop_table("crm_lead")
