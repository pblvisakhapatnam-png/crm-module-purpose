"""SQLAlchemy models for the governed configuration lifecycle records (PF-1A-E3).

TWO TABLES, AND DELIBERATELY NO MORE. ONE governed Configuration Change record spans all four
configurable object families and all three change types - four ad-hoc per-family workflows is
precisely the defect ADR-033 correction C2-2 removes - plus APPEND-ONLY recomputation evidence.

WHAT THESE MODELS DELIBERATELY DO NOT CARRY:

    NO FOREIGN KEY INTO THE PUBLISHED STORE. A Configuration Change routinely names an object
        that does not exist yet (that is what CREATE means), so a foreign key to a stable
        identity row would make the normal case unrepresentable. The governed activation proves
        referenced identities exist before it publishes.
    NO STORED RISK VERDICT THAT ANYTHING TRUSTS. The `proposal_time_*` columns are audit
        history of what was believed when the change was raised; authorization and activation
        recompute and never read them.
    NO SHADOW OF PUBLISHED CONTENT. Publication happens in the PF-1A-E2-B store, whose version
        rows remain immutable and append-only.

The Configuration Change row itself IS mutable while PENDING - its authorization, rejection and
activation fields are filled in as the lifecycle progresses. ADR-033 explicitly permits that,
and it is not published content.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.authorization.business_authority.configuration_contract import (
    CHANGE_TYPES,
    CONFIGURATION_CHANGE_TABLE,
    CONFIGURATION_EVALUATION_TABLE,
    EVALUATION_OUTCOMES,
    EVALUATION_STAGES,
    LIFECYCLE_STATUSES,
    OBJECT_FAMILIES,
)

_QUOTE = chr(39)


def _domain(column: str, values: tuple[str, ...]) -> str:
    rendered = ", ".join(f"{_QUOTE}{value}{_QUOTE}" for value in sorted(values))
    return f"{column} IN ({rendered})"


_INTERVAL = "declared_effective_to IS NULL OR declared_effective_to > effective_from"


class AuthorityConfigurationChange(Base):
    """One governed proposal to publish one version of one configuration object."""

    __tablename__ = CONFIGURATION_CHANGE_TABLE
    __table_args__ = (
        UniqueConstraint(
            "configuration_change_id", name="uq_authz_config_change_configuration_change_id"
        ),
        # At most one governed change may publish a given version of a given object. NULLs are
        # distinct in PostgreSQL, so every PENDING and REJECTED change - which publishes
        # nothing - coexists freely.
        UniqueConstraint(
            "configuration_object_family",
            "configuration_object_id",
            "published_object_version",
            name="uq_authz_config_change_published_version",
        ),
        CheckConstraint(
            _domain("configuration_object_family", OBJECT_FAMILIES),
            name="ck_authz_config_change_object_family",
        ),
        CheckConstraint(_domain("change_type", CHANGE_TYPES), name="ck_authz_config_change_type"),
        CheckConstraint(
            _domain("lifecycle_status", LIFECYCLE_STATUSES),
            name="ck_authz_config_change_lifecycle_status",
        ),
        CheckConstraint(_INTERVAL, name="ck_authz_config_change_interval"),
        Index(
            "ix_authz_config_change_object",
            "configuration_object_family",
            "configuration_object_id",
        ),
        Index("ix_authz_config_change_lifecycle_status", "lifecycle_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    configuration_change_id: Mapped[str] = mapped_column(Text, nullable=False)
    configuration_object_family: Mapped[str] = mapped_column(Text, nullable=False)
    configuration_object_id: Mapped[str] = mapped_column(Text, nullable=False)
    change_type: Mapped[str] = mapped_column(Text, nullable=False)
    change_payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    proposed_active_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    declared_effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    previous_object_version_expected: Mapped[str | None] = mapped_column(Text, nullable=True)

    # PRELIMINARY / AUDIT ONLY. Nothing reads these four to decide anything.
    proposal_time_is_self_affecting: Mapped[bool] = mapped_column(Boolean, nullable=False)
    proposal_time_affects_protected_meta_authority: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )
    proposal_time_privilege_increasing: Mapped[bool] = mapped_column(Boolean, nullable=False)
    proposal_time_authorization_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    proposal_context_snapshot: Mapped[Any] = mapped_column(JSONB, nullable=False)
    proposal_dependency_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)

    initiated_by_person_id: Mapped[str] = mapped_column(Text, nullable=False)
    initiated_by_actor_user_public_id: Mapped[str] = mapped_column(Text, nullable=False)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # The authorizer identity and the SUCCESSFUL AUTHORIZATION evaluation that established it,
    # written together or not at all. Activation reads the bound evaluation and no other, so a
    # later refused attempt cannot lend its freshly-recomputed risk verdict and dependency
    # fingerprint to an approver who never saw that context.
    #
    # No foreign key to the evaluation table, deliberately: the evaluation table already carries
    # one to this table, and a second key in the opposite direction would make the two tables
    # mutually dependent for insertion and teardown. The binding is enforced where it is
    # actually used - `configuration_repository.load_bound_evaluation` resolves it by evaluation
    # identity AND owning change identity together, and the service then verifies its stage,
    # outcome, satisfaction and acting identities before it counts as an authorization.
    authorized_by_person_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    authorized_by_actor_user_public_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    authorized_evaluation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rejected_by_person_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    lifecycle_status: Mapped[str] = mapped_column(Text, nullable=False)
    published_object_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuthorityConfigurationEvaluation(Base):
    """One APPEND-ONLY recomputation record. There is no update path."""

    __tablename__ = CONFIGURATION_EVALUATION_TABLE
    __table_args__ = (
        UniqueConstraint("evaluation_id", name="uq_authz_config_evaluation_evaluation_id"),
        CheckConstraint(
            _domain("evaluation_stage", EVALUATION_STAGES),
            name="ck_authz_config_evaluation_stage",
        ),
        CheckConstraint(
            _domain("outcome", EVALUATION_OUTCOMES), name="ck_authz_config_evaluation_outcome"
        ),
        Index("ix_authz_config_evaluation_change", "configuration_change_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[str] = mapped_column(Text, nullable=False)
    configuration_change_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(
            CONFIGURATION_CHANGE_TABLE + ".configuration_change_id",
            name="fk_authz_config_evaluation_change",
        ),
        nullable=False,
    )
    evaluation_stage: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acting_person_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    acting_actor_user_public_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    recomputed_is_self_affecting: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recomputed_affects_protected_meta_authority: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )
    recomputed_privilege_increasing: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recomputed_authorization_required: Mapped[bool] = mapped_column(Boolean, nullable=False)

    authorizer_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    authorizer_is_different_person: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dependencies_current: Mapped[bool] = mapped_column(Boolean, nullable=False)
    authorization_satisfied: Mapped[bool] = mapped_column(Boolean, nullable=False)

    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    refusal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    dependency_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    context_reference: Mapped[Any] = mapped_column(JSONB, nullable=False)
    risk_derivation: Mapped[Any] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
