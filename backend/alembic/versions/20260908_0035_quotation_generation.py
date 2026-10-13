"""quotation generation (Slice 9E)

Adds `crm_commercial_offer_quote_document`, the frozen/versioned quotation-document record for a
Commercial Offer. The bytes themselves live in `document_metadata` (Slice 9C's storage
abstraction, `storage_mode = 'local_upload'`, linked_record_type = 'commercial_offer'); this
table holds only what is quote-specific: the version number, the derived quote reference, the
one-step Draft -> Approved for Issue gate, and the source-data fingerprint used to detect
staleness against the live offer.

The single most important constraint in this migration is `ck_quote_document_approval_is_complete`
below: a row cannot claim `quote_status_code = 'APPROVED_FOR_ISSUE'` without recording who
approved it and when, and a row cannot claim `DRAFT` while carrying approval facts. This holds
even against a direct INSERT that bypasses the API entirely - the same shape as Slice 9C's
`ck_document_metadata_local_upload_has_bytes`, and for the same reason: the invariant that gives
the approval gate its meaning is the one that must survive the API being bypassed. See
docs/agent/slices/slice-9e-quotation-generation.md, "Records".

`superseded_at` is a separate, independent column, not folded into `quote_status_code` as a
third value: generating version N+1 must not erase the fact that version N was approved and
issued - that is the record of what was actually sent to the customer. Status and supersession
are two independent facts and are stored as two.

Also seeds two new permission codes and their role grants, following the same convention
20260908_0033 and 20260908_0034 established: the seed is spelled out here rather than imported
from app.modules.authorization.contract, so this revision stays a frozen historical snapshot
even if the Python contract changes later.

WHAT THIS MIGRATION DELIBERATELY DOES NOT DO:

    IT DOES NOT ADD A FOREIGN KEY FROM document_public_id TO document_metadata.document_public_id.
        document_metadata.document_public_id already carries a UNIQUE constraint (Slice 9C), so
        a FK is possible; it is deliberately omitted here for the same reason the existing
        commercial_offers subordinate tables (commercial_offer_submission_evidence,
        commercial_offer_credit_review, ...) reference crm_commercial_offer only by plain integer
        id rather than a declared FK - this codebase's established pattern for these tables is
        application-enforced referential integrity via the repository layer's INNER JOINs, not a
        declared FK, and this table follows that existing convention rather than introducing a
        new one for itself alone.
    IT DOES NOT BACKFILL ANYTHING. This is a brand-new table; there is no pre-existing data.

Revision ID: 20260908_0035
Revises: 20260908_0034
Create Date: 2026-09-08
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0035"
down_revision: Union[str, None] = "20260908_0034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


QUOTE_DOCUMENT_TABLE = "crm_commercial_offer_quote_document"

# Spelled out here rather than imported, so this revision stays a frozen historical snapshot.
# Mirrors app.modules.authorization.contract at the time of writing; a later contract change
# does not rewrite history, it adds its own revision.
ROLE_ADMIN = "ADMIN"
ROLE_SALES_USER = "SALES_USER"
ROLE_SALES_MANAGER = "SALES_MANAGER"

PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    "COMMERCIAL_OFFER_QUOTE_GENERATE": (
        "Generate a frozen quotation document version from a Commercial Offer.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "COMMERCIAL_OFFER_QUOTE_APPROVE": (
        "Approve a generated quotation document version for issue to the customer.",
        (ROLE_ADMIN, ROLE_SALES_MANAGER),
    ),
}


def upgrade() -> None:
    op.create_table(
        QUOTE_DOCUMENT_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quote_document_public_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("commercial_offer_id", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("quote_reference", sa.Unicode(length=100), nullable=False),
        sa.Column("document_public_id", sa.String(length=36), nullable=False),
        sa.Column("source_fingerprint", sa.CHAR(length=64), nullable=False),
        sa.Column("quote_status_code", sa.String(length=50), nullable=False),
        sa.Column("generated_by", sa.String(length=36), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("approved_by", sa.String(length=36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_note", sa.Unicode(length=1000), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_unique_constraint(
        "ux_quote_document_offer_version",
        QUOTE_DOCUMENT_TABLE,
        ["commercial_offer_id", "version_no"],
    )

    op.create_index(
        "ix_quote_document_commercial_offer_id",
        QUOTE_DOCUMENT_TABLE,
        ["commercial_offer_id"],
    )

    op.create_check_constraint(
        "ck_quote_document_status",
        QUOTE_DOCUMENT_TABLE,
        "quote_status_code IN ('DRAFT', 'APPROVED_FOR_ISSUE')",
    )

    # The single most important constraint in this migration. See the module docstring.
    op.create_check_constraint(
        "ck_quote_document_approval_is_complete",
        QUOTE_DOCUMENT_TABLE,
        "(quote_status_code = 'DRAFT' AND approved_by IS NULL AND approved_at IS NULL) "
        "OR (quote_status_code = 'APPROVED_FOR_ISSUE' AND approved_by IS NOT NULL AND approved_at IS NOT NULL)",
    )

    _seed_permissions()


def _seed_permissions() -> None:
    """Insert the two permission rows and their role grants.

    Mirrors the insert pattern 20260908_0033 and 20260908_0034 established, against the same two
    tables they created: authz_permission, and authz_role_permission which links by role_code (a
    real foreign key to role.role_code, so a missing/misspelled role fails the migration loudly
    rather than silently granting nothing).
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

    op.drop_table(QUOTE_DOCUMENT_TABLE)
