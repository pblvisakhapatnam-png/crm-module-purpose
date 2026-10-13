"""platform foundation tables

Revision ID: 20260629_0001
Revises:
Create Date: 2026-06-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260629_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_app_user_public_id"),
    )

    # Login compares usernames case-insensitively (see app/modules/identity/repository.py), so
    # uniqueness must be enforced on the same basis. A plain UNIQUE(username) would permit both
    # "sales1" and "SALES1" to exist and make that lookup ambiguous. PostgreSQL enforces this with
    # a unique expression index; citext is deliberately not used, because it would add an extension
    # dependency for a single column. This index subsumes plain username uniqueness: if lower() is
    # unique, the raw value is necessarily unique too.
    op.create_index(
        "ux_app_user_username_lower",
        "app_user",
        [sa.text("lower(username)")],
        unique=True,
    )

    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("role_code", sa.String(length=50), nullable=False),
        sa.Column("role_name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_role_public_id"),
        sa.UniqueConstraint("role_code", name="uq_role_role_code"),
        sa.UniqueConstraint("role_name", name="uq_role_role_name"),
    )

    op.create_table(
        "user_role",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role_user_role"),
    )

    op.create_table(
        "workflow_status",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("module", sa.String(length=100), nullable=False),
        sa.Column("status_code", sa.String(length=100), nullable=False),
        sa.Column("status_name", sa.String(length=150), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_workflow_status_public_id"),
        sa.UniqueConstraint("module", "status_code", name="uq_workflow_status_module_code"),
    )

    op.create_table(
        "business_event",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("event_name", sa.String(length=150), nullable=False),
        sa.Column("source_module", sa.String(length=100), nullable=False),
        sa.Column("record_type", sa.String(length=100), nullable=True),
        sa.Column("record_public_id", sa.String(length=36), nullable=True),
        sa.Column("user_public_id", sa.String(length=36), nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("status_before", sa.String(length=100), nullable=True),
        sa.Column("status_after", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("remarks", sa.String(length=1000), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("event_payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_business_event_public_id"),
    )

    op.create_table(
        "document_metadata",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_public_id", sa.String(length=36), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=False),
        sa.Column("linked_record_type", sa.String(length=100), nullable=True),
        sa.Column("linked_record_public_id", sa.String(length=36), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("original_file_name", sa.String(length=255), nullable=True),
        sa.Column("storage_mode", sa.String(length=50), nullable=False),
        sa.Column("storage_path_or_url", sa.String(length=1000), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="Uploaded"),
        sa.Column("uploaded_by", sa.String(length=36), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("remarks", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_public_id", name="uq_document_metadata_public_id"),
    )

    role_table = sa.table(
        "role",
        sa.column("public_id", sa.String),
        sa.column("role_code", sa.String),
        sa.column("role_name", sa.String),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        role_table,
        [
            {"public_id": "00000000-0000-0000-0000-000000000101", "role_code": "ADMIN", "role_name": "Admin", "is_active": True},
            {"public_id": "00000000-0000-0000-0000-000000000102", "role_code": "SALES_USER", "role_name": "Sales User", "is_active": True},
            {"public_id": "00000000-0000-0000-0000-000000000103", "role_code": "SALES_MANAGER", "role_name": "Sales Manager", "is_active": True},
            {"public_id": "00000000-0000-0000-0000-000000000104", "role_code": "FINANCE_USER", "role_name": "Finance User", "is_active": True},
            {"public_id": "00000000-0000-0000-0000-000000000105", "role_code": "OPERATIONS_USER", "role_name": "Operations User", "is_active": True},
            {"public_id": "00000000-0000-0000-0000-000000000106", "role_code": "MANAGEMENT_READ_ONLY", "role_name": "Management / Read Only", "is_active": True},
        ],
    )


def downgrade() -> None:
    op.drop_table("document_metadata")
    op.drop_table("business_event")
    op.drop_table("workflow_status")
    op.drop_table("user_role")
    op.drop_table("role")
    op.drop_index("ux_app_user_username_lower", table_name="app_user")
    op.drop_table("app_user")