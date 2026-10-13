"""explicit permission compatibility foundation (PF-1A-E1)

Adds `authz_permission` and `authz_role_permission`, the durable ORA-owned
explicit application-permission catalogue and role compatibility mapping
that PF-1A-E1 introduces to replace direct `require_roles(...)` role-tuple
checks in route guards.

This migration seeds the compatibility mapping exactly as it existed in the
route guards immediately before this change, so no access is silently
widened or narrowed. The seeded data is intentionally hardcoded here (not
imported from `app.modules.authorization.contract`) so this revision remains
a frozen historical snapshot even if the contract module's Python data
changes later, consistent with how `20260629_0002_auth_seed_users.py` embeds
its own seed data directly.

Revision ID: 20260831_0030
Revises: 20260713_0029
Create Date: 2026-08-31
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0030"
down_revision: Union[str, None] = "20260713_0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_ADMIN = "ADMIN"
ROLE_SALES_USER = "SALES_USER"
ROLE_SALES_MANAGER = "SALES_MANAGER"
ROLE_FINANCE_USER = "FINANCE_USER"
ROLE_OPERATIONS_USER = "OPERATIONS_USER"
ROLE_MANAGEMENT_READ_ONLY = "MANAGEMENT_READ_ONLY"

# permission_code -> (description, (granted role codes...))
# Mirrors app.modules.authorization.contract.ROLE_PERMISSION_COMPATIBILITY_MATRIX
# as it existed when this revision was authored.
PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    "ACCOUNT_CREATE": (
        "Create an Account / business_party, an Account Contact or an Account Address.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "ACCOUNT_READ": (
        "View Account / business_party records and their subordinate detail sections.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER, ROLE_OPERATIONS_USER, ROLE_MANAGEMENT_READ_ONLY),
    ),
    "ACCOUNT_CLASSIFICATION_MANAGE": (
        "Update Account ownership/classification (owner, segment, industry, strategic flag).",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "ACCOUNT_TAX_CAPTURE": (
        "Capture/update Account PAN/GST tax-profile and GSTIN entries.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER),
    ),
    "ACCOUNT_TAX_VERIFY": (
        "Set an Account PAN/GST verification state to a final state (VERIFIED / REJECTED_INCORRECT).",
        (ROLE_FINANCE_USER,),
    ),
    "ACCOUNT_DOCUMENT_CAPTURE": (
        "Record Account document metadata.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER),
    ),
    "COMMERCIAL_OFFER_CREATE": (
        "Create a Commercial Offer, including a related (Supplementary/Change Quotation) offer.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "COMMERCIAL_OFFER_READ": (
        "View Commercial Offers and their subordinate detail/readiness/history views.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER, ROLE_OPERATIONS_USER, ROLE_MANAGEMENT_READ_ONLY),
    ),
    "COMMERCIAL_OFFER_UPDATE": (
        "Update a Commercial Offer header or mark it submitted.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE": (
        "Add Commercial Offer pricing evidence or select the basis rate.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_OPERATIONS_USER),
    ),
    "COMMERCIAL_OFFER_LINE_WRITE": (
        "Add or update a Commercial Offer line.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "COMMERCIAL_OFFER_TC_CLAUSE_WRITE": (
        "Attach or remove Commercial Offer header T&C clauses.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE": (
        "Record Commercial Offer submission evidence.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE": (
        "Record a Commercial Offer manual credit/exposure review.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE": (
        "Record a Commercial Offer customer response / award outcome.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "COMMERCIAL_OFFER_REVISION_WRITE": (
        "Open, resubmit or cancel a Commercial Offer revision.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "LEAD_CREATE": (
        "Create a Lead.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "LEAD_READ": (
        "View Leads and their activities.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER, ROLE_OPERATIONS_USER, ROLE_MANAGEMENT_READ_ONLY),
    ),
    "LEAD_UPDATE": (
        "Update early Lead details.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "LEAD_QUALIFICATION_DECIDE": (
        "Record a Lead qualification/closure decision.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "LEAD_CONVERT": (
        "Convert a qualified Lead into an Account and Opportunity.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "LEAD_ACTIVITY_CREATE": (
        "Record a Lead activity/follow-up.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "OPPORTUNITY_CREATE": (
        "Create an Opportunity.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "OPPORTUNITY_READ": (
        "View Opportunities.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER, ROLE_OPERATIONS_USER, ROLE_MANAGEMENT_READ_ONLY),
    ),
    "OPPORTUNITY_UPDATE": (
        "Update an Opportunity.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "OPPORTUNITY_ACCOUNT_REPAIR": (
        "Repair a missing Opportunity-to-Account link.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "TC_CLAUSE_READ": (
        "View the Terms and Conditions clause library.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER, ROLE_OPERATIONS_USER, ROLE_MANAGEMENT_READ_ONLY),
    ),
    "WORK_ORDER_CREATE": (
        "Create a Work Order shell handoff, or create/update a Work Order Amendment.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_OPERATIONS_USER),
    ),
    "WORK_ORDER_READ": (
        "View Work Orders, their lines, related offers and amendments.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER, ROLE_OPERATIONS_USER, ROLE_MANAGEMENT_READ_ONLY),
    ),
    "EVENTS_READ": (
        "View recent business events.",
        (ROLE_ADMIN, ROLE_MANAGEMENT_READ_ONLY),
    ),
    "IDENTITY_ROLE_CATALOG_READ": (
        "View the application role catalogue.",
        (ROLE_ADMIN,),
    ),
}


def upgrade() -> None:
    op.create_table(
        "authz_permission",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("permission_code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_authz_permission"),
        sa.UniqueConstraint("public_id", name="uq_authz_permission_public_id"),
        sa.UniqueConstraint("permission_code", name="uq_authz_permission_code"),
    )

    op.create_table(
        "authz_role_permission",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("role_code", sa.String(length=50), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_authz_role_permission"),
        sa.UniqueConstraint("public_id", name="uq_authz_role_permission_public_id"),
        sa.UniqueConstraint("role_code", "permission_id", name="uq_authz_role_permission_role_permission"),
        sa.ForeignKeyConstraint(["role_code"], ["role.role_code"], name="fk_authz_role_permission_role"),
        sa.ForeignKeyConstraint(["permission_id"], ["authz_permission.id"], name="fk_authz_role_permission_permission"),
    )

    op.create_index(
        "ix_authz_role_permission_role_code",
        "authz_role_permission",
        ["role_code"],
        unique=False,
    )
    op.create_index(
        "ix_authz_role_permission_permission_id",
        "authz_role_permission",
        ["permission_id"],
        unique=False,
    )

    connection = op.get_bind()

    for permission_code, (description, granted_role_codes) in PERMISSION_SEED.items():
        connection.execute(
            sa.text(
                """
                INSERT INTO authz_permission (public_id, permission_code, description, is_active)
                VALUES (:public_id, :permission_code, :description, TRUE)
                """
            ),
            {
                "public_id": str(uuid4()),
                "permission_code": permission_code,
                "description": description,
            },
        )

        permission_id = connection.execute(
            sa.text("SELECT id FROM authz_permission WHERE permission_code = :permission_code"),
            {"permission_code": permission_code},
        ).scalar_one()

        for role_code in granted_role_codes:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO authz_role_permission (public_id, role_code, permission_id, is_active)
                    VALUES (:public_id, :role_code, :permission_id, TRUE)
                    """
                ),
                {
                    "public_id": str(uuid4()),
                    "role_code": role_code,
                    "permission_id": permission_id,
                },
            )


def downgrade() -> None:
    op.drop_index("ix_authz_role_permission_permission_id", table_name="authz_role_permission")
    op.drop_index("ix_authz_role_permission_role_code", table_name="authz_role_permission")
    op.drop_table("authz_role_permission")
    op.drop_table("authz_permission")
