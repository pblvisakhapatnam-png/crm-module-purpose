"""Provider-neutral domain objects, payloads and request/context shapes.

PF-1A-E2-A sections 8.1, 9.3.2, 9.3.4 and 12.

THE MOST IMPORTANT PROPERTY OF THIS MODULE IS WHAT IT DOES *NOT* DO.

Section 9.3.4 fixes the material DTO's required/optional shape as part of the
contract, precisely so that every class B1 malformed shape is constructible at
the boundary named for it. Consequently:

    NO dataclass here validates identity uniqueness, the person/position XOR,
    interval sanity, provenance presence, provenance enum membership or any
    referential relationship at construction time.

A "convenience validator" that helpfully enforced any of those would silently
destroy the direct E2-A malformed-input coverage that class B1 depends on, and
is called out as a blocking defect by section 9.3.4 and attack surface 17b.
The DTO-OPTIONAL fields below are values the KERNEL classifies, not values the
DTO may reject.

ABSENCE CONVENTION. `None` means the field is ABSENT. For the DTO-OPTIONAL
provenance and assignment-target fields that is a malformed state the kernel
must classify; for `declared_effective_to` it is the legitimate "no known end"
value. `publication_reference_type` is carried as an OPEN string, never as a
language-level closed enum, so that BOTH an ABSENT type and an UNKNOWN type
are constructible and reach the kernel (9.3.4, 11.7).

DTO-REQUIRED fields (`object_version`, `effective_from`, `active_flag`,
`payload`; `retraction_id`, `object_version`) also default to `None` so their
absence is CONSTRUCTIBLE - but their absence is a WELL-FORMEDNESS failure
rejected at the DTO/port boundary by `material.check_material_well_formed`,
never a semantic classification. This document defines no reason code for "a
version with no effective_from", and inventing one to mirror a NOT NULL
constraint is prohibited (9.7 class B2 discipline).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.modules.authorization.business_authority.contract import COMPLETENESS_COMPLETE

# ---------------------------------------------------------------------------
# 8.1  Family-specific published payloads
# ---------------------------------------------------------------------------
# Each payload carries the published BUSINESS MEANING of one version. Rule and
# Assignment reference their Business Authority Role / Business Authority by
# STABLE identity, never by version (invariant I-5).


@dataclass(frozen=True)
class BusinessAuthorityRolePayload:
    """Published meaning of one Business Authority Role version.

    NOT an Application/Login Role. Its code space is entirely separate from
    the six transitional `role` table codes (PF_1A_E2_A section 4, concept 3).
    """

    role_code: str
    role_name: str = ""
    description: str = ""


@dataclass(frozen=True)
class BusinessAuthorityPayload:
    """Published meaning of one Business Authority version.

    `is_protected_meta_authority` is an EXPLICIT, DATA-DRIVEN classification
    field (ADR-033). It is never a hard-coded comparison against a literal
    code string such as AUTHORITY_CONFIGURATION_ADMIN.
    """

    authority_code: str
    authority_name: str = ""
    description: str = ""
    is_protected_meta_authority: bool = False


@dataclass(frozen=True)
class BusinessAuthorityRulePayload:
    """Published meaning of one Rule version: Role -> Authority, scoped and parameterised."""

    business_authority_role_id: str | None = None
    business_authority_id: str | None = None
    scope_type: str | None = None
    scope_id: str | None = None
    parameter_evaluator_type: str | None = None
    parameter_payload: Any = None


@dataclass(frozen=True)
class BusinessAuthorityAssignmentPayload:
    """Published meaning of one Assignment version: Person XOR Position -> Role.

    `person_id` and `position_id` are BOTH DTO-optional. The XOR is a SEMANTIC
    rule the kernel enforces at stage S7 (invariant I-4, reason code
    ASSIGNMENT_TARGET_INVALID), which is exactly why neither may be enforced
    here: doing so would make B1-02 and B1-03 unconstructible.
    """

    business_authority_role_id: str | None = None
    person_id: str | None = None
    position_id: str | None = None
    scope_type: str | None = None
    scope_id: str | None = None


# ---------------------------------------------------------------------------
# 9.3.2  Published version and retraction assertion
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PublishedObjectVersion:
    """One immutable published version of one stable object.

    A published version is immutable (invariant I-2): its content - including
    `active_flag`, `effective_from`, `declared_effective_to`, provenance and
    `published_at` - never changes after publication, for any reason,
    including correction. `frozen=True` is that invariant in code.

    `active_flag` is an IMMUTABLE PUBLISHED VALUE, not temporal effectiveness
    and not a derived projection (8.2, invariant I-8). Deactivating an object
    means publishing a NEW version whose `active_flag` is false.
    """

    # DTO-REQUIRED (9.3.4). Absence is ill-formed material, rejected at the
    # DTO/port boundary as AUTHORITY_CONFIGURATION_UNAVAILABLE.
    object_version: str | None = None
    effective_from: datetime | None = None
    active_flag: bool | None = None
    payload: Any = None

    # DTO-OPTIONAL, KERNEL-VALIDATED (9.3.4). Each already has a semantic
    # classification in this contract, so the DTO must not reject any of them.
    declared_effective_to: datetime | None = None
    corrects_object_version: str | None = None
    publication_reference_type: str | None = None
    publication_reference_id: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True)
class RetractionAssertion:
    """An append-only assertion that one published version was recorded in error.

    A retraction NEVER edits the retracted version, which remains fully
    dereferenceable through `get_published_version` forever (9.3.2). An
    INVALID retraction never removes its target: it fails the whole resolution
    closed (11.3), so a retraction can never be a shortcut for making an
    inconvenient version disappear.
    """

    # DTO-REQUIRED (9.3.4).
    retraction_id: str | None = None
    object_version: str | None = None

    # DTO-OPTIONAL, KERNEL-VALIDATED (9.3.4).
    retracted_at: datetime | None = None
    publication_reference_type: str | None = None
    publication_reference_id: str | None = None


@dataclass(frozen=True)
class LineageMaterial:
    """COMPLETE lineage material for one stable object (9.3.2).

    `versions` means EVERY published version of this object - including
    future-dated versions, versions the provider believes are superseded,
    inactive versions and retracted versions. The kernel needs all of them to
    derive closure, to detect duplicate starts, explicit overlap, dangling
    retractions and unretracted correction targets, and to establish that a
    valid gap is a gap rather than corruption.

    `object_id` lives on this CONTAINER, and versions/retractions are grouped
    UNDER it. That is why a version or a retraction cannot be
    provider-neutrally orphaned from its object, and therefore why the
    corresponding store foreign keys are class B2 rather than class B1 (9.7).

    An object identity the provider holds nothing for returns COMPLETE
    material with an EMPTY `versions` and an EMPTY `retraction_assertions`.
    That is a truthful answer the kernel classifies (as
    AUTHORITY_REFERENCE_DANGLING), never an error and never a "no such object"
    signal.
    """

    object_family: str | None = None
    object_id: str | None = None
    versions: tuple[PublishedObjectVersion, ...] = ()
    retraction_assertions: tuple[RetractionAssertion, ...] = ()
    completeness: str | None = COMPLETENESS_COMPLETE


# ---------------------------------------------------------------------------
# 12  Request, actor and business context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthenticatedActor:
    """The authenticated application actor, as the server knows it.

    Deliberately carries ONLY the application-user public identifier. There is
    no `person_id` field, and none may be added: the actor is never trusted to
    state who it is canonically, and a client-supplied person identity is
    never accepted as the identity being authorized (7.1, 9.1, acceptance
    criterion B).

    There is also deliberately no `role_codes` field. A Business Authority is
    never derived, defaulted or inferred from an Application/Login Role,
    including ADMIN (section 6), so the kernel has no legitimate use for one.
    """

    actor_user_public_id: str


@dataclass(frozen=True)
class BusinessContext:
    """The authoritative business context a resolution is evaluated against.

    `scope_type` / `scope_id` are CANONICAL scope identities (for example a
    canonical `org_unit_id`). A raw provider identifier is never a scope_id
    (12.3).

    `declared_facts` are the business facts named by a rule's evaluator
    payload. A required fact that is absent, of the wrong type, or supplied in
    a unit/currency/basis incompatible with the payload's declared one is
    MALFORMED EVALUATOR INPUT and fails closed with EVALUATOR_FACTS_INVALID -
    never EVALUATOR_CONDITION_NOT_SATISFIED (section 13).
    """

    scope_type: str | None = None
    scope_id: str | None = None
    declared_facts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuthorityResolutionRequest:
    """One authority-resolution question.

    Business consumers request a Business Authority BY `authority_code` and by
    nothing else - never by a person's name, an employee code, a designation,
    a job title, an Application/Login Role code, or a Business Authority Role
    name (section 4, acceptance criterion A).
    """

    authenticated_actor: AuthenticatedActor
    authority_code: str
    business_context: BusinessContext = field(default_factory=BusinessContext)
    # A CONFIGURED canonical-snapshot staleness threshold, in seconds. It is a
    # deferred POLICY PARAMETER (section 7, section 23): the kernel accepts a
    # supplied value and invents NO default. `None` means no threshold was
    # configured, in which case staleness is whatever the HR provider itself
    # reports explicitly - never a value this kernel made up.
    hr_staleness_threshold_seconds: int | None = None


# ---------------------------------------------------------------------------
# Canonical object/version reference, used throughout the evidence contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ObjectVersionRef:
    """A canonical (object_family, object_id, object_version) reference.

    This is an ESTABLISHED-IDENTITY reference. Evidence may only ever cite
    identities that were actually established; a partial evaluation names what
    does not exist rather than emitting placeholder or null-filled pairs
    (16.4).
    """

    object_family: str
    object_id: str
    object_version: str
