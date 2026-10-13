"""interaction foundation (Slice 9D)

Adds the shared, channel-agnostic conversation log and its participants:

    interaction              ONE record per communication - call, email, WhatsApp message,
        meeting, site visit - attached polymorphically to Lead, Account, Opportunity,
        Commercial Offer or Work Order, reusing the document_metadata linked_record_type /
        linked_record_public_id pattern rather than five nullable foreign keys.

    interaction_participant  The people on that communication. A child table rather than a JSON
        column, because "every conversation involving this contact" is a query the pilot wants.

Also seeds the five new permission codes and their role grants, following the convention
20260831_0030 established: the seed is spelled out here rather than imported from
app.modules.authorization.contract, so this revision stays a frozen historical snapshot even if
the Python contract changes later.

WHAT THIS MIGRATION DELIBERATELY DOES NOT DO:

    IT CREATES NO FOREIGN KEY ON THE POLYMORPHIC LINK. linked_record_public_id addresses five
        different tables; a foreign key cannot express that. The owning service validates the
        target exists, exactly as document_metadata already does for the same pattern.
    IT CREATES NO FOREIGN KEY ON contact_public_id OR app_user_public_id. A participant may be
        an external person absent from business_party_contact entirely, and a resolved link must
        survive that contact being deactivated. display_name and address_or_number remain the
        evidence of record.
    IT TOUCHES crm_lead_activity NOT AT ALL. Slice 2D Lead activities keep working unchanged.
        Whether they should eventually fold into this table is an open question with a data
        migration behind it; see docs/agent/slices/slice-9d-interaction-foundation.md.
    IT ADDS NO RETENTION OR PURGE MECHANISM. Retention is an unset policy parameter under the
        ADR-015 precedent. body_stored = false with body_text = NULL is already the shape a
        future purge writes, so no schema change is needed when the period is set.

DATA CLASSIFICATION: body_text and interaction_participant.address_or_number are Restricted
personal/statutory under docs/agent/architecture/DATA_CLASSIFICATION_AND_HANDLING.md. Reading
them requires INTERACTION_CONTENT_READ, separately from INTERACTION_READ. Business events emitted
against these tables carry metadata only and must never carry the body, the subject or a
participant address.

Revision ID: 20260908_0033
Revises: 20260906_0032
Create Date: 2026-09-08
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0033"
down_revision: Union[str, None] = "20260906_0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INTERACTION_TABLE = "interaction"
INTERACTION_PARTICIPANT_TABLE = "interaction_participant"

# Spelled out here rather than imported, so this revision stays a frozen historical snapshot.
# Mirrors app.modules.authorization.contract at the time of writing; a later contract change
# does not rewrite history, it adds its own revision.
ROLE_ADMIN = "ADMIN"
ROLE_SALES_USER = "SALES_USER"
ROLE_SALES_MANAGER = "SALES_MANAGER"
ROLE_FINANCE_USER = "FINANCE_USER"
ROLE_OPERATIONS_USER = "OPERATIONS_USER"
ROLE_MANAGEMENT_READ_ONLY = "MANAGEMENT_READ_ONLY"

PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    "INTERACTION_READ": (
        "View recorded conversations: who, when, which channel, subject and outcome.",
        (
            ROLE_ADMIN,
            ROLE_SALES_USER,
            ROLE_SALES_MANAGER,
            ROLE_FINANCE_USER,
            ROLE_OPERATIONS_USER,
            ROLE_MANAGEMENT_READ_ONLY,
        ),
    ),
    "INTERACTION_CONTENT_READ": (
        "Read the stored message content and participant email addresses or phone numbers.",
        (
            ROLE_ADMIN,
            ROLE_SALES_USER,
            ROLE_SALES_MANAGER,
            ROLE_OPERATIONS_USER,
            ROLE_MANAGEMENT_READ_ONLY,
        ),
    ),
    "INTERACTION_CREATE": (
        "Record a conversation against a Lead, Account, Opportunity, Commercial Offer or Work Order.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "INTERACTION_UPDATE": (
        "Correct the outcome or follow-up date on a recorded conversation.",
        (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ),
    "INTERACTION_DELETE": (
        "Soft-delete a conversation recorded in error.",
        (ROLE_ADMIN, ROLE_SALES_MANAGER),
    ),
}


def upgrade() -> None:
    op.create_table(
        INTERACTION_TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("interaction_public_id", sa.String(length=36), nullable=False),
        sa.Column("linked_record_type", sa.String(length=100), nullable=False),
        sa.Column("linked_record_public_id", sa.String(length=36), nullable=False),
        sa.Column("channel_code", sa.String(length=50), nullable=False),
        sa.Column("direction_code", sa.String(length=20), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subject", sa.Unicode(length=500), nullable=True),
        sa.Column("body_text", sa.UnicodeText(), nullable=True),
        sa.Column("body_stored", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("external_system", sa.String(length=50), nullable=True),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        # SHA-256 of the normalized create command. An idempotent retry must prove it is the
        # SAME command before it may replay an existing row; without this, reusing a key with a
        # different payload silently returned somebody else's record as though it were the
        # caller's own. See the interaction contract, "Idempotency key scope".
        sa.Column("request_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("external_reference_url", sa.String(length=1000), nullable=True),
        sa.Column("geo_latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("geo_longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("outcome", sa.Unicode(length=255), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id", name="pk_interaction"),
        sa.UniqueConstraint("interaction_public_id", name="uq_interaction_public_id"),
        # Coordinate integrity at the database, not only in the API schema. Pydantic validation
        # protects the HTTP path; it does nothing for a direct SQL insert, a future ingestion
        # job writing through another path, or a data-repair script. A latitude of 999 was
        # accepted by direct insert during review.
        sa.CheckConstraint(
            "(geo_latitude IS NULL) = (geo_longitude IS NULL)",
            name="ck_interaction_geo_paired",
        ),
        sa.CheckConstraint(
            "geo_latitude IS NULL OR (geo_latitude >= -90 AND geo_latitude <= 90)",
            name="ck_interaction_geo_latitude_range",
        ),
        sa.CheckConstraint(
            "geo_longitude IS NULL OR (geo_longitude >= -180 AND geo_longitude <= 180)",
            name="ck_interaction_geo_longitude_range",
        ),
    )

    op.create_index(
        "ix_interaction_linked_record",
        INTERACTION_TABLE,
        ["linked_record_type", "linked_record_public_id"],
        unique=False,
    )
    op.create_index("ix_interaction_occurred_at", INTERACTION_TABLE, ["occurred_at"], unique=False)
    op.create_index(
        "ix_interaction_next_follow_up",
        INTERACTION_TABLE,
        ["next_follow_up_at"],
        unique=False,
        postgresql_where=sa.text("next_follow_up_at IS NOT NULL"),
    )

    # The two build-ahead constraints. Nothing populates these columns yet; a future ingestion
    # job will, and it will eventually run concurrently with itself. A service-layer duplicate
    # check would not survive that, so re-sync safety is a database constraint from day one -
    # adding it later would mean a migration against a populated table of customer messages.
    op.create_index(
        "ux_interaction_external_message",
        INTERACTION_TABLE,
        ["external_system", "external_message_id"],
        unique=True,
        postgresql_where=sa.text("external_system IS NOT NULL AND external_message_id IS NOT NULL"),
    )
    op.create_index(
        "ux_interaction_idempotency_key",
        INTERACTION_TABLE,
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        INTERACTION_PARTICIPANT_TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("participant_public_id", sa.String(length=36), nullable=False),
        sa.Column("interaction_id", sa.Integer(), nullable=False),
        sa.Column("party_role_code", sa.String(length=20), nullable=False),
        sa.Column("contact_public_id", sa.String(length=36), nullable=True),
        sa.Column("app_user_public_id", sa.String(length=36), nullable=True),
        sa.Column("display_name", sa.Unicode(length=255), nullable=True),
        sa.Column("address_or_number", sa.Unicode(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_interaction_participant"),
        sa.UniqueConstraint("participant_public_id", name="uq_interaction_participant_public_id"),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            [f"{INTERACTION_TABLE}.id"],
            name="fk_interaction_participant_interaction",
        ),
    )

    op.create_index(
        "ix_interaction_participant_interaction",
        INTERACTION_PARTICIPANT_TABLE,
        ["interaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_interaction_participant_contact",
        INTERACTION_PARTICIPANT_TABLE,
        ["contact_public_id"],
        unique=False,
        postgresql_where=sa.text("contact_public_id IS NOT NULL"),
    )

    _seed_permissions()


def _seed_permissions() -> None:
    """Insert the five permission rows and their role grants.

    Mirrors the insert pattern 20260831_0030 established, against the same two tables it created:
    `authz_permission`, and `authz_role_permission` which links by `role_code` rather than by a
    role id. That link is a real foreign key to `role.role_code`, so a missing or misspelled role
    fails the migration loudly - which is what should happen. Granting nothing silently would
    produce a permission that exists but authorizes no one, and that reads as a deliberate
    restriction rather than the bug it would be.
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

    op.drop_index("ix_interaction_participant_contact", table_name=INTERACTION_PARTICIPANT_TABLE)
    op.drop_index("ix_interaction_participant_interaction", table_name=INTERACTION_PARTICIPANT_TABLE)
    op.drop_table(INTERACTION_PARTICIPANT_TABLE)

    op.drop_index("ux_interaction_idempotency_key", table_name=INTERACTION_TABLE)
    op.drop_index("ux_interaction_external_message", table_name=INTERACTION_TABLE)
    op.drop_index("ix_interaction_next_follow_up", table_name=INTERACTION_TABLE)
    op.drop_index("ix_interaction_occurred_at", table_name=INTERACTION_TABLE)
    op.drop_index("ix_interaction_linked_record", table_name=INTERACTION_TABLE)
    op.drop_table(INTERACTION_TABLE)
