"""seed workflow statuses

Revision ID: 20260629_0003
Revises: 20260629_0002
Create Date: 2026-06-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260629_0003"
down_revision = "20260629_0002"
branch_labels = None
depends_on = None


BUSINESS_PARTY_STATUSES = [
    {
        "public_id": "00000000-0000-0000-0000-000000000301",
        "module": "business_party",
        "status_code": "DRAFT",
        "status_name": "Draft",
        "is_active": True,
        "sort_order": 10,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000302",
        "module": "business_party",
        "status_code": "LEAD_LINKED",
        "status_name": "Lead Linked",
        "is_active": True,
        "sort_order": 20,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000303",
        "module": "business_party",
        "status_code": "QUALIFIED_PROSPECT",
        "status_name": "Qualified Prospect",
        "is_active": True,
        "sort_order": 30,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000304",
        "module": "business_party",
        "status_code": "ACTIVE_PROSPECT",
        "status_name": "Active Prospect",
        "is_active": True,
        "sort_order": 40,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000305",
        "module": "business_party",
        "status_code": "DORMANT",
        "status_name": "Dormant",
        "is_active": True,
        "sort_order": 50,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000306",
        "module": "business_party",
        "status_code": "ON_HOLD",
        "status_name": "On Hold",
        "is_active": True,
        "sort_order": 60,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000307",
        "module": "business_party",
        "status_code": "BLOCKED",
        "status_name": "Blocked",
        "is_active": True,
        "sort_order": 70,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000308",
        "module": "business_party",
        "status_code": "CUSTOMER_ACTIVATION_PENDING",
        "status_name": "Customer Activation Pending",
        "is_active": True,
        "sort_order": 80,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000309",
        "module": "business_party",
        "status_code": "CUSTOMER_ACTIVE",
        "status_name": "Customer Active",
        "is_active": True,
        "sort_order": 90,
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000310",
        "module": "business_party",
        "status_code": "BLACKLISTED",
        "status_name": "Blacklisted",
        "is_active": True,
        "sort_order": 100,
    },
]


def upgrade() -> None:
    workflow_status = sa.table(
        "workflow_status",
        sa.column("public_id", sa.String),
        sa.column("module", sa.String),
        sa.column("status_code", sa.String),
        sa.column("status_name", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )

    op.bulk_insert(workflow_status, BUSINESS_PARTY_STATUSES)


def downgrade() -> None:
    codes = ", ".join(f"'{row['status_code']}'" for row in BUSINESS_PARTY_STATUSES)
    op.execute(
        f"""
        DELETE FROM workflow_status
        WHERE module = 'business_party'
          AND status_code IN ({codes})
        """
    )