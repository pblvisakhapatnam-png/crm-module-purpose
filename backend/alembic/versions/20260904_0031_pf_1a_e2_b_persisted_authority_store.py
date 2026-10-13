"""persisted published Business Authority store (PF-1A-E2-B)

Adds the twelve tables of the published Business Authority store: for each of
the four PF-1A-E2-A object families, a stable identity table, an immutable
published version table and an append-only retraction assertion table.

WHAT THIS MIGRATION DELIBERATELY DOES NOT DO, because each absence is a
requirement rather than an omission (PF-1A-E2-B section 5.4, 5.6):

    IT SEEDS NOTHING. Not a catalogue, not a rule, not an assignment, not a
        bootstrap holder, not a meta-authority holder. Q-10 remains open and
        untouched, and deterministic tests create their own synthetic data.
    IT ALTERS NO EXISTING OBJECT. `role`, `app_user`, `user_role`,
        `authz_permission` and `authz_role_permission` are untouched, and
        there is no foreign key, join or shared code space between the
        Application/Login `role` table and any Business Authority Role table.
    IT ADDS NO CONSTRAINT BEYOND SECTION 5.6's LIST. Adding one would silently
        move a class A fixture into class B1/B2 and suppress a defect class
        the kernel owns; removing one would strip a rejection proof. In
        particular there is NO contiguity constraint, NO overlap-rejecting
        constraint or trigger, NO uniqueness or exclusion constraint on
        (object_id, effective_from), NO retraction-uniqueness constraint, NO
        foreign key from a retraction to a specific VERSION row, NO constraint
        on `corrects_object_version`, NO closed enum on
        `parameter_evaluator_type` or `scope_type`, NO cross-row
        recorded-timestamp constraint, and NO stored derived closure or
        `is_current` artefact.

The constraints it DOES create are exactly section 5.6's permitted list: an
immutable identity/version uniqueness key per family, the assignment
person/position XOR, the single-row interval-shape check, NOT NULL on
`effective_from` / `active_flag` / the provenance reference columns /
`published_at` / `retracted_at`, the closed `publication_reference_type`
domain, and foreign keys to STABLE identity rows only.

Revision ID: 20260904_0031
Revises: 20260831_0030
Create Date: 2026-09-04
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260904_0031"
down_revision: Union[str, None] = "20260831_0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Spelled out here rather than imported, so this revision stays a frozen
# historical snapshot even if the Python contract module changes later -
# the convention `20260831_0030` and `20260629_0002` already follow.
BA_AUTHORITY = "authz_business_authority"
BA_ROLE = "authz_business_authority_role"
BA_RULE = "authz_business_authority_rule"
BA_ASSIGNMENT = "authz_business_authority_assignment"

PROVENANCE_DOMAIN = (
    "publication_reference_type IN ('BOOTSTRAP_PROVENANCE', 'CONFIGURATION_CHANGE')"
)
INTERVAL_SHAPE = "declared_effective_to IS NULL OR declared_effective_to > effective_from"

# (short name used in constraint/index identifiers, stable table name)
FAMILIES = (
    ("authority", BA_AUTHORITY),
    ("role", BA_ROLE),
    ("rule", BA_RULE),
    ("assignment", BA_ASSIGNMENT),
)


def _stable_table(short: str, table: str) -> None:
    op.create_table(
        table,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # The canonical, opaque, externally referenceable stable identity.
        sa.Column("object_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_id", name=f"uq_ba_{short}_object_id"),
    )


def _version_columns(short: str, stable_table: str) -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("object_id", sa.Text(), nullable=False),
        sa.Column("object_version", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        # ABSENT means "no known end": a legitimate published value.
        sa.Column("declared_effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_flag", sa.Boolean(), nullable=False),
        # No foreign key and no CHECK: a missing or unretracted correction
        # target is a class A defect the KERNEL must classify.
        sa.Column("corrects_object_version", sa.Text(), nullable=True),
        sa.Column("publication_reference_type", sa.Text(), nullable=False),
        sa.Column("publication_reference_id", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _version_constraints(short: str, stable_table: str) -> list:
    return [
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["object_id"],
            [f"{stable_table}.object_id"],
            name=f"fk_ba_{short}_version_object_id",
        ),
        sa.UniqueConstraint(
            "object_id", "object_version", name=f"uq_ba_{short}_version_object_version"
        ),
        sa.CheckConstraint(INTERVAL_SHAPE, name=f"ck_ba_{short}_version_interval"),
        sa.CheckConstraint(
            PROVENANCE_DOMAIN, name=f"ck_ba_{short}_publication_reference_type"
        ),
    ]


def _retraction_table(short: str, stable_table: str) -> None:
    op.create_table(
        f"{stable_table}_retraction",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("object_id", sa.Text(), nullable=False),
        sa.Column("retraction_id", sa.Text(), nullable=False),
        sa.Column("object_version", sa.Text(), nullable=False),
        sa.Column("retracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("publication_reference_type", sa.Text(), nullable=False),
        sa.Column("publication_reference_id", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        # To the STABLE identity only. A foreign key to the specific VERSION
        # row would forbid a DANGLING retraction, which is class A fixture
        # A-04 and must remain storable. There is likewise no uniqueness
        # constraint here: a DUPLICATED retraction is class A fixture A-05.
        sa.ForeignKeyConstraint(
            ["object_id"],
            [f"{stable_table}.object_id"],
            name=f"fk_ba_{short}_retraction_object_id",
        ),
        sa.CheckConstraint(
            PROVENANCE_DOMAIN, name=f"ck_ba_{short}_retraction_publication_reference_type"
        ),
    )
    op.create_index(f"ix_ba_{short}_retraction_object_id", f"{stable_table}_retraction", ["object_id"])


def upgrade() -> None:
    # -- stable identity tables, created first so version/retraction foreign
    #    keys and the cross-family stable references have their targets ------
    for short, table in FAMILIES:
        _stable_table(short, table)

    # -- Business Authority version -----------------------------------------
    op.create_table(
        f"{BA_AUTHORITY}_version",
        *_version_columns("authority", BA_AUTHORITY),
        sa.Column("authority_code", sa.Text(), nullable=True),
        sa.Column("authority_name", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_protected_meta_authority", sa.Boolean(), nullable=True),
        *_version_constraints("authority", BA_AUTHORITY),
    )
    op.create_index(
        "ix_ba_authority_version_authority_code",
        f"{BA_AUTHORITY}_version",
        ["authority_code"],
    )

    # -- Business Authority Role version ------------------------------------
    op.create_table(
        f"{BA_ROLE}_version",
        *_version_columns("role", BA_ROLE),
        sa.Column("role_code", sa.Text(), nullable=True),
        sa.Column("role_name", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *_version_constraints("role", BA_ROLE),
    )

    # -- Business Authority Rule version ------------------------------------
    op.create_table(
        f"{BA_RULE}_version",
        *_version_columns("rule", BA_RULE),
        # STABLE references, never version-level: a version-level reference
        # would break correction (E2-A invariant I-5).
        sa.Column("business_authority_role_object_id", sa.Text(), nullable=True),
        sa.Column("business_authority_object_id", sa.Text(), nullable=True),
        sa.Column("scope_type", sa.Text(), nullable=True),
        sa.Column("scope_id", sa.Text(), nullable=True),
        sa.Column("parameter_evaluator_type", sa.Text(), nullable=True),
        # Declarative structured data. The DATABASE stores it; the KERNEL
        # validates it, so an unknown evaluator type and a malformed payload
        # both stay storable and parity-testable.
        sa.Column("parameter_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        *_version_constraints("rule", BA_RULE),
        sa.ForeignKeyConstraint(
            ["business_authority_role_object_id"],
            [f"{BA_ROLE}.object_id"],
            name="fk_ba_rule_version_role_reference",
        ),
        sa.ForeignKeyConstraint(
            ["business_authority_object_id"],
            [f"{BA_AUTHORITY}.object_id"],
            name="fk_ba_rule_version_authority_reference",
        ),
    )
    op.create_index(
        "ix_ba_rule_version_authority_reference",
        f"{BA_RULE}_version",
        ["business_authority_object_id"],
    )

    # -- Business Authority Assignment version -------------------------------
    op.create_table(
        f"{BA_ASSIGNMENT}_version",
        *_version_columns("assignment", BA_ASSIGNMENT),
        sa.Column("business_authority_role_object_id", sa.Text(), nullable=True),
        # OPAQUE canonical platform identifiers: no local HR table, no foreign
        # key and no join target (ADR-026, ADR-032, RMR-001).
        sa.Column("person_id", sa.Text(), nullable=True),
        sa.Column("position_id", sa.Text(), nullable=True),
        sa.Column("scope_type", sa.Text(), nullable=True),
        sa.Column("scope_id", sa.Text(), nullable=True),
        *_version_constraints("assignment", BA_ASSIGNMENT),
        sa.ForeignKeyConstraint(
            ["business_authority_role_object_id"],
            [f"{BA_ROLE}.object_id"],
            name="fk_ba_assignment_version_role_reference",
        ),
        sa.CheckConstraint(
            "(person_id IS NOT NULL) <> (position_id IS NOT NULL)",
            name="ck_ba_assignment_version_target_xor",
        ),
    )
    op.create_index(
        "ix_ba_assignment_version_role_reference",
        f"{BA_ASSIGNMENT}_version",
        ["business_authority_role_object_id"],
    )

    # -- retraction tables ---------------------------------------------------
    for short, table in FAMILIES:
        _retraction_table(short, table)


def downgrade() -> None:
    """Drops exactly what `upgrade` created, children before parents.

    THE DOWNGRADE DECISION, recorded as section 5.4 requires: a downgrade is
    provided and is DESTRUCTIVE of published authority configuration by
    construction, because the tables it drops are the only record of that
    configuration. It is intended for development and for an unreleased
    chain only. Since this store holds no seeded data and no production
    configuration exists (acceptance criterion S), running it today loses
    nothing; once PF-1A-E3 can publish real configuration, a downgrade must be
    treated as a data-destroying operation and gated accordingly.
    """

    for short, table in FAMILIES:
        op.drop_index(f"ix_ba_{short}_retraction_object_id", table_name=f"{table}_retraction")
        op.drop_table(f"{table}_retraction")

    op.drop_index("ix_ba_assignment_version_role_reference", table_name=f"{BA_ASSIGNMENT}_version")
    op.drop_table(f"{BA_ASSIGNMENT}_version")

    op.drop_index("ix_ba_rule_version_authority_reference", table_name=f"{BA_RULE}_version")
    op.drop_table(f"{BA_RULE}_version")

    op.drop_table(f"{BA_ROLE}_version")

    op.drop_index("ix_ba_authority_version_authority_code", table_name=f"{BA_AUTHORITY}_version")
    op.drop_table(f"{BA_AUTHORITY}_version")

    for _short, table in FAMILIES:
        op.drop_table(table)
