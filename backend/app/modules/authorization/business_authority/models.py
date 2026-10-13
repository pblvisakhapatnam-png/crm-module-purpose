"""SQLAlchemy models for the persisted published Business Authority store.

PF-1A-E2-B sections 5.1, 5.5 and 5.6.

WHAT THESE MODELS DELIBERATELY DO NOT CARRY, and why each absence matters:

    NO UPDATE PATH.  Published version rows and retraction rows are
        append-only (5.6). There is no `updated_at`, no `onupdate`, no
        mutable status column and no soft-delete flag, because none of them
        could be honest here: deactivating an object means publishing a NEW
        version whose `active_flag` is false (8.2), never editing an old one.
    NO DERIVED CLOSURE.  There is no `asserted_effective_to`, no `is_current`
        and no materialised "effective" projection. Closure is DERIVED per
        resolution by the E2-A kernel (11.4); storing it would create a
        second source of truth that can disagree with the kernel.
    NO HR FOREIGN KEY.  `person_id`, `position_id` and every scope identifier
        are OPAQUE canonical platform values (ADR-026, ADR-032, RMR-001).
        PF-1A owns no Employee/Organisation/Position master, so there is no
        local mirror table and nothing to join to.
    NO LINK TO `role`.  A Business Authority Role is not an Application/Login
        Role. There is no foreign key, no shared code space and no join.

WHY ALMOST EVERY PAYLOAD COLUMN IS NULLABLE. Section 5.7 makes the structural
constraint set EXACTLY the list in section 5.6 - "no more, no less" - because
adding one silently moves a fixture out of the parity corpus and removes the
kernel's opportunity to classify the shape. The NOT NULL columns below are
precisely the ones 5.6 names (`effective_from`, `active_flag`, the two
provenance reference columns, `published_at`, `retracted_at`) plus the
identity columns those constraints are defined over. Everything else -
including `parameter_evaluator_type`, `scope_type`, `parameter_payload` and
every payload field - stays nullable so the kernel remains the thing that
classifies it.

TEXT rather than a bounded VARCHAR is deliberate for the opaque canonical
identifiers: their production length is owned by the canonical HR/organisation
reference capability, not by this store, and an invented length limit would be
an unclassified rejection shape.
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
from app.modules.authorization.business_authority.contract import (
    BOOTSTRAP_PROVENANCE,
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
    CONFIGURATION_CHANGE,
)
from app.modules.authorization.business_authority.store_contract import (
    BA_ASSIGNMENT_RETRACTION_TABLE,
    BA_ASSIGNMENT_TABLE,
    BA_ASSIGNMENT_VERSION_TABLE,
    BA_AUTHORITY_RETRACTION_TABLE,
    BA_AUTHORITY_TABLE,
    BA_AUTHORITY_VERSION_TABLE,
    BA_ROLE_RETRACTION_TABLE,
    BA_ROLE_TABLE,
    BA_ROLE_VERSION_TABLE,
    BA_RULE_RETRACTION_TABLE,
    BA_RULE_TABLE,
    BA_RULE_VERSION_TABLE,
    CK_ASSIGNMENT_TARGET_XOR,
    CK_INTERVAL,
    CK_PUBLICATION_REFERENCE_TYPE,
    FAMILY_SHORT_NAME,
    FK_ASSIGNMENT_ROLE_REFERENCE,
    FK_RETRACTION_PARENT,
    FK_RULE_AUTHORITY_REFERENCE,
    FK_RULE_ROLE_REFERENCE,
    FK_VERSION_PARENT,
    IX_ASSIGNMENT_ROLE_REFERENCE,
    IX_AUTHORITY_CODE,
    IX_RETRACTION_OBJECT_ID,
    IX_RULE_AUTHORITY_REFERENCE,
    UQ_STABLE_OBJECT_ID,
    UQ_VERSION_IDENTITY,
)

# The closed provenance domain of 11.7, rendered as the single CHECK section
# 5.6 permits. It is a CLOSED ENUM DOMAIN over a stored value, decidable from
# the row alone - never a semantic judgement.
_PROVENANCE_DOMAIN = (
    "publication_reference_type IN "
    f"('{BOOTSTRAP_PROVENANCE}', '{CONFIGURATION_CHANGE}')"
)

# The ONLY interval condition that is safe to enforce structurally (E2-A I-6,
# E2-B 5.6): a SINGLE-ROW interval-shape check. Every cross-row interval
# question - overlap, duplicate start, gaps, adjacency - is the kernel's and
# must remain storable here.
_INTERVAL_SHAPE = "declared_effective_to IS NULL OR declared_effective_to > effective_from"


def _short(family: str) -> str:
    return FAMILY_SHORT_NAME[family]


class _StableIdentity:
    """One stable object identity. NEVER versioned, never carrying meaning."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # The canonical, opaque, externally referenceable stable object identity -
    # this store's ADR-007 public identifier. It is the value the E2-A port
    # exchanges, and a UUID in production; a separate `public_id` column is
    # deliberately NOT added, because two external identities for one object
    # would be exactly the ambiguity ADR-007 exists to prevent.
    object_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class _PublishedVersion:
    """One IMMUTABLE published version. Append-only; there is no UPDATE path."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_version: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # ABSENT means "no known end" - a legitimate published value, not a defect.
    declared_effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # An IMMUTABLE PUBLISHED VALUE (8.2), never temporal effectiveness, never
    # computed, never on the stable-identity row, and never filtered out by
    # this store.
    active_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # DELIBERATELY carries no foreign key and no CHECK: a correcting version
    # whose target is missing or unretracted is class A (A-06, A-07) and the
    # KERNEL must be able to classify it.
    corrects_object_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_reference_type: Mapped[str] = mapped_column(Text, nullable=False)
    publication_reference_id: Mapped[str] = mapped_column(Text, nullable=False)
    # RECORDED time. Stored faithfully, never defaulted on read, never
    # rewritten, and never used as a filter or as a business-effective bound.
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class _RetractionAssertion:
    """An append-only assertion that one published version was recorded in error.

    It NEVER removes, hides or edits its target: the target row stays stored,
    discoverable, returnable in lineage material and dereferenceable forever
    (E2-A 9.3.2, 11.3). There is deliberately no foreign key to the VERSION
    row and no uniqueness constraint over (object_id, object_version): a
    dangling retraction (A-04) and a duplicated retraction (A-05) are class A
    shapes the kernel must be given the chance to classify.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    retraction_id: Mapped[str] = mapped_column(Text, nullable=False)
    object_version: Mapped[str] = mapped_column(Text, nullable=False)
    retracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    publication_reference_type: Mapped[str] = mapped_column(Text, nullable=False)
    publication_reference_id: Mapped[str] = mapped_column(Text, nullable=False)


def _stable_args(family: str) -> tuple:
    return (UniqueConstraint("object_id", name=UQ_STABLE_OBJECT_ID.format(short=_short(family))),)


def _version_args(family: str) -> tuple:
    short = _short(family)
    return (
        UniqueConstraint(
            "object_id",
            "object_version",
            name=UQ_VERSION_IDENTITY.format(short=short),
        ),
        CheckConstraint(_INTERVAL_SHAPE, name=CK_INTERVAL.format(short=short)),
        CheckConstraint(
            _PROVENANCE_DOMAIN, name=CK_PUBLICATION_REFERENCE_TYPE.format(short=short)
        ),
    )


def _retraction_args(family: str) -> tuple:
    short = _short(family)
    return (
        CheckConstraint(
            _PROVENANCE_DOMAIN,
            name=CK_PUBLICATION_REFERENCE_TYPE.format(short=short + "_retraction"),
        ),
        Index(IX_RETRACTION_OBJECT_ID.format(short=short), "object_id"),
    )


# ---------------------------------------------------------------------------
# Business Authority
# ---------------------------------------------------------------------------


class BusinessAuthorityObject(_StableIdentity, Base):
    __tablename__ = BA_AUTHORITY_TABLE
    __table_args__ = _stable_args(BUSINESS_AUTHORITY)


class BusinessAuthorityVersion(_PublishedVersion, Base):
    __tablename__ = BA_AUTHORITY_VERSION_TABLE
    __table_args__ = _version_args(BUSINESS_AUTHORITY) + (
        Index(IX_AUTHORITY_CODE, "authority_code"),
    )

    object_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(
            BA_AUTHORITY_TABLE + ".object_id",
            name=FK_VERSION_PARENT.format(short="authority"),
        ),
        nullable=False,
    )
    authority_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    authority_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_protected_meta_authority: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class BusinessAuthorityRetraction(_RetractionAssertion, Base):
    __tablename__ = BA_AUTHORITY_RETRACTION_TABLE
    __table_args__ = _retraction_args(BUSINESS_AUTHORITY)

    object_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(
            BA_AUTHORITY_TABLE + ".object_id",
            name=FK_RETRACTION_PARENT.format(short="authority"),
        ),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Business Authority Role  (NOT the Application/Login `role` table)
# ---------------------------------------------------------------------------


class BusinessAuthorityRoleObject(_StableIdentity, Base):
    __tablename__ = BA_ROLE_TABLE
    __table_args__ = _stable_args(BUSINESS_AUTHORITY_ROLE)


class BusinessAuthorityRoleVersion(_PublishedVersion, Base):
    __tablename__ = BA_ROLE_VERSION_TABLE
    __table_args__ = _version_args(BUSINESS_AUTHORITY_ROLE)

    object_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(BA_ROLE_TABLE + ".object_id", name=FK_VERSION_PARENT.format(short="role")),
        nullable=False,
    )
    role_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class BusinessAuthorityRoleRetraction(_RetractionAssertion, Base):
    __tablename__ = BA_ROLE_RETRACTION_TABLE
    __table_args__ = _retraction_args(BUSINESS_AUTHORITY_ROLE)

    object_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(BA_ROLE_TABLE + ".object_id", name=FK_RETRACTION_PARENT.format(short="role")),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Business Authority Rule
# ---------------------------------------------------------------------------


class BusinessAuthorityRuleObject(_StableIdentity, Base):
    __tablename__ = BA_RULE_TABLE
    __table_args__ = _stable_args(BUSINESS_AUTHORITY_RULE)


class BusinessAuthorityRuleVersion(_PublishedVersion, Base):
    __tablename__ = BA_RULE_VERSION_TABLE
    __table_args__ = _version_args(BUSINESS_AUTHORITY_RULE) + (
        Index(IX_RULE_AUTHORITY_REFERENCE, "business_authority_object_id"),
    )

    object_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(BA_RULE_TABLE + ".object_id", name=FK_VERSION_PARENT.format(short="rule")),
        nullable=False,
    )
    # References the STABLE identity, never a specific version - a
    # version-level reference would break correction (invariant I-5).
    business_authority_role_object_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey(BA_ROLE_TABLE + ".object_id", name=FK_RULE_ROLE_REFERENCE),
        nullable=True,
    )
    business_authority_object_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey(BA_AUTHORITY_TABLE + ".object_id", name=FK_RULE_AUTHORITY_REFERENCE),
        nullable=True,
    )
    scope_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Deliberately NOT constrained to the registered evaluator types: an
    # unknown type is class A fixture A-13 and the KERNEL must classify it.
    parameter_evaluator_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Declarative structured DATA only. Never code, an expression string, SQL
    # or a template (5.5). The DATABASE stores it; the KERNEL validates it, so
    # a malformed payload (A-14) stays storable and parity-testable.
    parameter_payload: Mapped[Any | None] = mapped_column(JSONB, nullable=True)


class BusinessAuthorityRuleRetraction(_RetractionAssertion, Base):
    __tablename__ = BA_RULE_RETRACTION_TABLE
    __table_args__ = _retraction_args(BUSINESS_AUTHORITY_RULE)

    object_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(BA_RULE_TABLE + ".object_id", name=FK_RETRACTION_PARENT.format(short="rule")),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Business Authority Assignment
# ---------------------------------------------------------------------------


class BusinessAuthorityAssignmentObject(_StableIdentity, Base):
    __tablename__ = BA_ASSIGNMENT_TABLE
    __table_args__ = _stable_args(BUSINESS_AUTHORITY_ASSIGNMENT)


class BusinessAuthorityAssignmentVersion(_PublishedVersion, Base):
    __tablename__ = BA_ASSIGNMENT_VERSION_TABLE
    __table_args__ = _version_args(BUSINESS_AUTHORITY_ASSIGNMENT) + (
        # Person XOR Position, exactly one non-null. A single-row shape check
        # of the kind 5.6 permits; both the BOTH and the NEITHER shapes are
        # therefore class B1 (B1-02, B1-03) and are proved directly against
        # the kernel by E2-A at stage S7, not through this store.
        CheckConstraint(
            "(person_id IS NOT NULL) <> (position_id IS NOT NULL)",
            name=CK_ASSIGNMENT_TARGET_XOR,
        ),
        Index(IX_ASSIGNMENT_ROLE_REFERENCE, "business_authority_role_object_id"),
    )

    object_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(
            BA_ASSIGNMENT_TABLE + ".object_id",
            name=FK_VERSION_PARENT.format(short="assignment"),
        ),
        nullable=False,
    )
    business_authority_role_object_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey(BA_ROLE_TABLE + ".object_id", name=FK_ASSIGNMENT_ROLE_REFERENCE),
        nullable=True,
    )
    # OPAQUE canonical platform identifiers. No local table, no foreign key,
    # no join target, and never a provider identifier or an employee name.
    person_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    position_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class BusinessAuthorityAssignmentRetraction(_RetractionAssertion, Base):
    __tablename__ = BA_ASSIGNMENT_RETRACTION_TABLE
    __table_args__ = _retraction_args(BUSINESS_AUTHORITY_ASSIGNMENT)

    object_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(
            BA_ASSIGNMENT_TABLE + ".object_id",
            name=FK_RETRACTION_PARENT.format(short="assignment"),
        ),
        nullable=False,
    )
