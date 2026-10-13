"""governed authority configuration lifecycle (PF-1A-E3)

Adds the two tables of the governed Configuration Change lifecycle:

    authz_authority_configuration_change      ONE governed record type spanning all four
        configurable object families and all three change types. ADR-033 correction C2-2 exists
        precisely to replace four inconsistent per-family workflows with one.

    authz_authority_configuration_evaluation  APPEND-ONLY recomputation evidence for the
        proposal, authorization, rejection and activation stages.

WHAT THIS MIGRATION DELIBERATELY DOES NOT DO:

    IT SEEDS NOTHING. Not a role, authority, rule, assignment, Configuration Change, bootstrap
        holder or protected meta-authority holder. Q-10 remains open and untouched;
        deterministic tests create their own synthetic state through a test-only path.
    IT ALTERS NO PF-1A-E2-B OBJECT. The twelve published-store tables, their columns, their
        constraint set and their index set are untouched. Adding a constraint there would move
        a PF-1A-E2-B verification fixture between classes; removing one would strip a proof.
    IT ADDS NO FOREIGN KEY INTO THE PUBLISHED STORE. A Configuration Change routinely names an
        object that does not exist yet - that is what CREATE means - so such a key would make
        the normal case unrepresentable. Referenced identities are proved to exist by the
        governed activation, before it publishes.

Revision ID: 20260906_0032
Revises: 20260904_0031
Create Date: 2026-09-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260906_0032"
down_revision: Union[str, None] = "20260904_0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Spelled out here rather than imported, so this revision stays a frozen historical snapshot
# even if the Python contract modules change later - the convention 20260904_0031 already
# follows.
CHANGE_TABLE = "authz_authority_configuration_change"
EVALUATION_TABLE = "authz_authority_configuration_evaluation"

OBJECT_FAMILY_DOMAIN = (
    "configuration_object_family IN ('BUSINESS_AUTHORITY', 'BUSINESS_AUTHORITY_ASSIGNMENT', "
    "'BUSINESS_AUTHORITY_ROLE', 'BUSINESS_AUTHORITY_RULE')"
)
CHANGE_TYPE_DOMAIN = "change_type IN ('CREATE', 'DEACTIVATE', 'UPDATE')"
LIFECYCLE_DOMAIN = "lifecycle_status IN ('ACTIVE', 'PENDING', 'REJECTED')"
STAGE_DOMAIN = "evaluation_stage IN ('ACTIVATION', 'AUTHORIZATION', 'PROPOSAL', 'REJECTION')"
OUTCOME_DOMAIN = "outcome IN ('PERMITTED', 'RECORDED', 'REFUSED')"
INTERVAL_SHAPE = "declared_effective_to IS NULL OR declared_effective_to > effective_from"

PUBLISHED_VERSION_TABLES = (
    "authz_business_authority_version",
    "authz_business_authority_role_version",
    "authz_business_authority_rule_version",
    "authz_business_authority_assignment_version",
)
CONFIGURATION_CHANGE_PROVENANCE = "CONFIGURATION_CHANGE"

# THE FIXED, DOCUMENTED LOCK ORDER FOR A DESTRUCTIVE DOWNGRADE.
#
# Every table a governed activation can write is locked BEFORE anything is counted, and the
# locks are held through the count and through the destructive DDL in the SAME transaction. The
# order is fixed and stated here so two concurrent downgrades acquire the same locks in the same
# sequence and cannot deadlock each other: the four published-version tables in object-family
# order, then the two governed lifecycle tables.
#
# The order is deliberately WIDER than "the tables this revision drops". A governed activation
# writes a published version row into a PF-1A-E2-B version table AND a lifecycle row into a
# PF-1A-E3 table in one transaction; locking only the latter would leave a writer free to commit
# a CONFIGURATION_CHANGE-provenance publication into the former between the count and the drop,
# and the downgrade would then destroy governed state it had just certified absent.
DOWNGRADE_LOCK_ORDER = PUBLISHED_VERSION_TABLES + (CHANGE_TABLE, EVALUATION_TABLE)


def lock_governed_state_for_downgrade(bind) -> None:
    """Block every governed writer, in the fixed order above, before anything is counted.

    ACCESS EXCLUSIVE is the strongest table lock and conflicts with every other lock mode,
    including the ROW EXCLUSIVE an INSERT takes. It is the correct choice here precisely because
    it is heavy: a destructive downgrade is a rare, deliberate, offline-by-intent operation, and
    the alternative to blocking writers is racing them.

    A PostgreSQL table lock is TRANSACTION-SCOPED and cannot be released early, so these locks
    survive until the migration transaction commits or rolls back - which is what closes the
    check-to-drop window rather than merely narrowing it. Alembic runs a PostgreSQL migration in
    one transaction; this function and the count and the DDL that follow it must stay in that
    same transaction.

    A concurrent writer holding a conflicting lock makes THIS statement wait rather than making
    the guard read a stale count. That is the intended behaviour: the downgrade waits, or the
    operator's own `lock_timeout` aborts it. Neither outcome can drop a populated table.
    """

    for table in DOWNGRADE_LOCK_ORDER:
        bind.execute(sa.text(f"LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE"))


def governed_state_counts(bind) -> dict:
    """How much governed / governed-published state this database holds.

    A READ. It takes no locks of its own, so a caller that needs the count to remain true - the
    downgrade guard - must establish that separately, before calling this.
    """

    counts = {}
    for table in (CHANGE_TABLE, EVALUATION_TABLE):
        counts[table] = int(bind.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
    published = 0
    for table in PUBLISHED_VERSION_TABLES:
        published += int(
            bind.execute(
                sa.text(
                    f"SELECT COUNT(*) FROM {table} "
                    "WHERE publication_reference_type = :provenance"
                ),
                {"provenance": CONFIGURATION_CHANGE_PROVENANCE},
            ).scalar_one()
        )
    counts["published_configuration_change_versions"] = published
    return counts


def assert_no_governed_state(bind) -> None:
    """Refuse a destructive downgrade once governed configuration exists.

    PF-1A-E2-B's own downgrade is destructive of published authority configuration by
    construction, and it recorded that this was acceptable only while nothing could publish
    real configuration into that store. This revision is what changes that fact, so it inherits
    the obligation to gate the downgrade: the guard runs FIRST, in the revision that sits ABOVE
    20260904_0031, so a `downgrade base` can never reach the destructive authority-store
    downgrade while governed or published configuration exists.

    THE LOCKS COME BEFORE THE COUNT, AND THAT ORDER IS THE WHOLE POINT. Counting first and
    locking later - which is what the DDL below would otherwise do on its own - leaves a window
    in which a concurrent governed activation commits after it was counted and before DROP
    acquires its lock, so a downgrade could certify "no governed state" and then destroy some.
    Taking the write-blocking locks first collapses that window to nothing.

    An EMPTY development database still downgrades cleanly and intentionally.
    """

    lock_governed_state_for_downgrade(bind)

    counts = governed_state_counts(bind)
    if any(value > 0 for value in counts.values()):
        rendered = ", ".join(f"{name}={counts[name]}" for name in sorted(counts))
        raise RuntimeError(
            "refusing to downgrade PF-1A-E3: governed authority configuration state exists "
            f"({rendered}). Downgrading would destroy governed Configuration Change records, "
            "their recomputation evidence, and - by allowing the PF-1A-E2-B downgrade beneath "
            "it to proceed - the published authority versions those records activated. Remove "
            "this data deliberately, with a recorded decision, before downgrading."
        )


def upgrade() -> None:
    op.create_table(
        CHANGE_TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("configuration_change_id", sa.Text(), nullable=False),
        # OPAQUE. No foreign key: a CREATE names an object that does not exist yet, which a
        # foreign key would make unrepresentable.
        sa.Column("configuration_object_family", sa.Text(), nullable=False),
        sa.Column("configuration_object_id", sa.Text(), nullable=False),
        sa.Column("change_type", sa.Text(), nullable=False),
        sa.Column("change_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("proposed_active_flag", sa.Boolean(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("declared_effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("previous_object_version_expected", sa.Text(), nullable=True),
        # PRELIMINARY / AUDIT ONLY. No code path reads these four columns to decide anything.
        sa.Column("proposal_time_is_self_affecting", sa.Boolean(), nullable=False),
        sa.Column(
            "proposal_time_affects_protected_meta_authority", sa.Boolean(), nullable=False
        ),
        sa.Column("proposal_time_privilege_increasing", sa.Boolean(), nullable=False),
        sa.Column("proposal_time_authorization_required", sa.Boolean(), nullable=False),
        sa.Column(
            "proposal_context_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("proposal_dependency_fingerprint", sa.Text(), nullable=False),
        sa.Column("initiated_by_person_id", sa.Text(), nullable=False),
        sa.Column("initiated_by_actor_user_public_id", sa.Text(), nullable=False),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authorized_by_person_id", sa.Text(), nullable=True),
        sa.Column("authorized_by_actor_user_public_id", sa.Text(), nullable=True),
        # The successful AUTHORIZATION evaluation the authorizer above is bound to. No foreign
        # key: the evaluation table already references this one, and a second key in the
        # opposite direction would make the pair mutually dependent for insertion and teardown.
        sa.Column("authorized_evaluation_id", sa.Text(), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by_person_id", sa.Text(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("lifecycle_status", sa.Text(), nullable=False),
        sa.Column("published_object_version", sa.Text(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "configuration_change_id", name="uq_authz_config_change_configuration_change_id"
        ),
        # At most one governed change may publish a given version of a given object. NULLs are
        # distinct in PostgreSQL, so PENDING and REJECTED changes coexist freely.
        sa.UniqueConstraint(
            "configuration_object_family",
            "configuration_object_id",
            "published_object_version",
            name="uq_authz_config_change_published_version",
        ),
        sa.CheckConstraint(OBJECT_FAMILY_DOMAIN, name="ck_authz_config_change_object_family"),
        sa.CheckConstraint(CHANGE_TYPE_DOMAIN, name="ck_authz_config_change_type"),
        sa.CheckConstraint(LIFECYCLE_DOMAIN, name="ck_authz_config_change_lifecycle_status"),
        sa.CheckConstraint(INTERVAL_SHAPE, name="ck_authz_config_change_interval"),
    )
    op.create_index(
        "ix_authz_config_change_object",
        CHANGE_TABLE,
        ["configuration_object_family", "configuration_object_id"],
    )
    op.create_index(
        "ix_authz_config_change_lifecycle_status", CHANGE_TABLE, ["lifecycle_status"]
    )

    op.create_table(
        EVALUATION_TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evaluation_id", sa.Text(), nullable=False),
        sa.Column("configuration_change_id", sa.Text(), nullable=False),
        sa.Column("evaluation_stage", sa.Text(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acting_person_id", sa.Text(), nullable=True),
        sa.Column("acting_actor_user_public_id", sa.Text(), nullable=True),
        sa.Column("recomputed_is_self_affecting", sa.Boolean(), nullable=False),
        sa.Column(
            "recomputed_affects_protected_meta_authority", sa.Boolean(), nullable=False
        ),
        sa.Column("recomputed_privilege_increasing", sa.Boolean(), nullable=False),
        sa.Column("recomputed_authorization_required", sa.Boolean(), nullable=False),
        sa.Column("authorizer_eligible", sa.Boolean(), nullable=False),
        sa.Column("authorizer_is_different_person", sa.Boolean(), nullable=False),
        sa.Column("dependencies_current", sa.Boolean(), nullable=False),
        sa.Column("authorization_satisfied", sa.Boolean(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("refusal_reason", sa.Text(), nullable=True),
        sa.Column("dependency_fingerprint", sa.Text(), nullable=False),
        sa.Column("context_reference", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risk_derivation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_id", name="uq_authz_config_evaluation_evaluation_id"),
        sa.ForeignKeyConstraint(
            ["configuration_change_id"],
            [f"{CHANGE_TABLE}.configuration_change_id"],
            name="fk_authz_config_evaluation_change",
        ),
        sa.CheckConstraint(STAGE_DOMAIN, name="ck_authz_config_evaluation_stage"),
        sa.CheckConstraint(OUTCOME_DOMAIN, name="ck_authz_config_evaluation_outcome"),
    )
    op.create_index(
        "ix_authz_config_evaluation_change", EVALUATION_TABLE, ["configuration_change_id"]
    )


def downgrade() -> None:
    """Drops exactly what `upgrade` created - unless governed state exists.

    THE DOWNGRADE DECISION, recorded explicitly. PF-1A-E2-B provided a destructive downgrade
    and said, in terms, that once PF-1A-E3 could publish real configuration a downgrade must be
    treated as data-destroying and gated accordingly. This is that gate, and it sits above
    PF-1A-E2-B's revision so it runs first.

    `assert_no_governed_state` acquires the write-blocking locks BEFORE it counts, and
    PostgreSQL holds them until this transaction ends, so the zero-state verdict below is still
    true when the DROPs execute. There is no check-to-drop window for a concurrent writer to
    commit into.
    """

    assert_no_governed_state(op.get_bind())

    op.drop_index("ix_authz_config_evaluation_change", table_name=EVALUATION_TABLE)
    op.drop_table(EVALUATION_TABLE)
    op.drop_index("ix_authz_config_change_lifecycle_status", table_name=CHANGE_TABLE)
    op.drop_index("ix_authz_config_change_object", table_name=CHANGE_TABLE)
    op.drop_table(CHANGE_TABLE)
