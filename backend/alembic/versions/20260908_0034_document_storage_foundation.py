"""document storage foundation (Slice 9C)

Adds real file storage to `document_metadata`, closing the metadata lie the pre-9C module
allowed: `storage_mode = 'local_upload'` was accepted by the API although no file upload existed
anywhere in the backend, so the metadata asserted a file that was never stored. Verified against
the live database before this migration was written: 2 existing rows, both
linked_record_type = 'account', zero rows with storage_mode = 'local_upload' - closing the hole
breaks no existing data.

New nullable columns:

    storage_provider_code   which storage provider holds the bytes (e.g. "local")
    storage_key             opaque provider key - never a caller-supplied path, never exposed
                             outside app.modules.documents.storage
    content_type            declared/validated MIME type of the stored file
    byte_size                actual byte count, counted while streaming - never trusted from a
                             caller-declared Content-Length
    checksum_sha256          integrity evidence, and lets a future migration verify a copy
    retention_due_at         SHAPE ONLY. Owner decision 4 (8 September 2026): retention is not
                             decided now, following the ADR-015 precedent of leaving evidence-
                             retention policy as an explicit deferred parameter rather than
                             inventing a default. This column is never set by this slice's code
                             and nothing purges against it.

The single most important line in this migration is the CHECK constraint below: a row cannot
claim storage_mode = 'local_upload' unless the four columns proving bytes were actually stored
are all populated. This holds even against a direct INSERT that bypasses the API entirely -
Slice 9D's own lesson ("Pydantic validation is not a database constraint - a direct insert
bypassed it") applied to this slice's own central invariant.

Also seeds three new permission codes and their role grants, following the convention
20260831_0030 and 20260908_0033 established: the seed is spelled out here rather than imported
from app.modules.authorization.contract, so this revision stays a frozen historical snapshot
even if the Python contract changes later.

WHAT THIS MIGRATION DELIBERATELY DOES NOT DO:

    IT DOES NOT BACKFILL storage_provider_code/storage_key/content_type/byte_size/
        checksum_sha256 for the 2 pre-existing rows. Both predate file upload entirely
        (storage_mode = 'external_link'), so there is nothing to backfill; the CHECK constraint
        only requires those columns when storage_mode = 'local_upload', which neither row is.
    IT DOES NOT ADD A FOREIGN KEY FROM storage_provider_code TO A PROVIDER CATALOGUE TABLE. One
        provider ("local") exists today; a small closed set of string values does not yet
        justify a lookup table, consistent with this codebase's existing reference-data
        pattern (see CODING_STANDARDS.md section 5) of introducing a lookup table only once
        values are genuinely admin-configurable.
    IT SETS retention_due_at ON NO ROW. See the column note above.

Revision ID: 20260908_0034
Revises: 20260908_0033
Create Date: 2026-09-08
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0034"
down_revision: Union[str, None] = "20260908_0033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DOCUMENT_METADATA_TABLE = "document_metadata"

# Spelled out here rather than imported, so this revision stays a frozen historical snapshot.
# Mirrors app.modules.authorization.contract at the time of writing; a later contract change
# does not rewrite history, it adds its own revision.
ROLE_ADMIN = "ADMIN"
ROLE_SALES_USER = "SALES_USER"
ROLE_SALES_MANAGER = "SALES_MANAGER"
ROLE_FINANCE_USER = "FINANCE_USER"
ROLE_OPERATIONS_USER = "OPERATIONS_USER"
ROLE_MANAGEMENT_READ_ONLY = "MANAGEMENT_READ_ONLY"

_ALL_SIX_ROLES = (
    ROLE_ADMIN,
    ROLE_SALES_USER,
    ROLE_SALES_MANAGER,
    ROLE_FINANCE_USER,
    ROLE_OPERATIONS_USER,
    ROLE_MANAGEMENT_READ_ONLY,
)

PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    "DOCUMENT_READ": (
        "Use the documents API and see document metadata for records you may read.",
        _ALL_SIX_ROLES,
    ),
    "DOCUMENT_UPLOAD": (
        "Upload a file, or record document metadata pointing at an external file.",
        _ALL_SIX_ROLES,
    ),
    "DOCUMENT_CONTENT_READ": (
        "Download the stored bytes of an uploaded document.",
        _ALL_SIX_ROLES,
    ),
}


def upgrade() -> None:
    op.add_column(DOCUMENT_METADATA_TABLE, sa.Column("storage_provider_code", sa.String(length=50), nullable=True))
    op.add_column(DOCUMENT_METADATA_TABLE, sa.Column("storage_key", sa.String(length=500), nullable=True))
    op.add_column(DOCUMENT_METADATA_TABLE, sa.Column("content_type", sa.String(length=255), nullable=True))
    op.add_column(DOCUMENT_METADATA_TABLE, sa.Column("byte_size", sa.BigInteger(), nullable=True))
    op.add_column(DOCUMENT_METADATA_TABLE, sa.Column("checksum_sha256", sa.CHAR(length=64), nullable=True))
    op.add_column(DOCUMENT_METADATA_TABLE, sa.Column("retention_due_at", sa.DateTime(timezone=True), nullable=True))

    # The single most important constraint in this slice. See the module docstring.
    op.create_check_constraint(
        "ck_document_metadata_local_upload_has_bytes",
        DOCUMENT_METADATA_TABLE,
        "storage_mode <> 'local_upload' OR ("
        "storage_provider_code IS NOT NULL AND "
        "storage_key IS NOT NULL AND "
        "byte_size IS NOT NULL AND "
        "checksum_sha256 IS NOT NULL"
        ")",
    )

    # A given provider's storage_key is unique to it - two documents cannot claim the same
    # bytes under the same provider. Partial: only meaningful once a provider is set.
    op.create_index(
        "ux_document_metadata_storage_provider_key",
        DOCUMENT_METADATA_TABLE,
        ["storage_provider_code", "storage_key"],
        unique=True,
        postgresql_where=sa.text("storage_provider_code IS NOT NULL AND storage_key IS NOT NULL"),
    )

    _seed_permissions()


def _seed_permissions() -> None:
    """Insert the three permission rows and their role grants.

    Mirrors the insert pattern 20260831_0030 and 20260908_0033 established, against the same
    two tables they created: authz_permission, and authz_role_permission which links by
    role_code (a real foreign key to role.role_code, so a missing/misspelled role fails the
    migration loudly rather than silently granting nothing).
    """
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
    connection = op.get_bind()
    codes = list(PERMISSION_SEED)
    connection.execute(
        sa.text(
            "DELETE FROM authz_role_permission WHERE permission_id IN "
            "(SELECT id FROM authz_permission WHERE permission_code = ANY(:codes))"
        ),
        {"codes": codes},
    )
    connection.execute(
        sa.text("DELETE FROM authz_permission WHERE permission_code = ANY(:codes)"),
        {"codes": codes},
    )

    op.drop_index("ux_document_metadata_storage_provider_key", table_name=DOCUMENT_METADATA_TABLE)
    op.drop_constraint("ck_document_metadata_local_upload_has_bytes", DOCUMENT_METADATA_TABLE, type_="check")
    op.drop_column(DOCUMENT_METADATA_TABLE, "retention_due_at")
    op.drop_column(DOCUMENT_METADATA_TABLE, "checksum_sha256")
    op.drop_column(DOCUMENT_METADATA_TABLE, "byte_size")
    op.drop_column(DOCUMENT_METADATA_TABLE, "content_type")
    op.drop_column(DOCUMENT_METADATA_TABLE, "storage_key")
    op.drop_column(DOCUMENT_METADATA_TABLE, "storage_provider_code")
