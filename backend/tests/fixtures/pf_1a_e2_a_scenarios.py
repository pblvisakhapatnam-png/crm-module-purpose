"""Declarative scenario helpers for the PF-1A-E2-A conformance corpus. TEST-ONLY.

Builds a minimal, entirely VALID four-object world that resolves to
ALLOW + RESOLVED, which every negative scenario then perturbs in exactly one
place. Keeping one baseline makes each fixture's SUBJECT unambiguous - which
is the property the 9.7.0 entry test turns on.

Synthetic bootstrap provenance throughout. Not a production bootstrap, not a
resolution of Q-10, and not a choice of any real authority holder.
"""

from __future__ import annotations

from datetime import datetime

from app.modules.authorization.business_authority.contract import (
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
    EVALUATOR_NONE,
    SCOPE_GLOBAL,
)
from app.modules.authorization.business_authority.domain import (
    AuthenticatedActor,
    AuthorityResolutionRequest,
    BusinessContext,
)
from app.modules.authorization.business_authority.evidence import AuthorityResolutionResult
from app.modules.authorization.business_authority.kernel import resolve
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    ACTOR_ID,
    AUTHORITY_CODE,
    PERSON_ID,
    T0,
    T2,
    ReferenceActorPersonProvider,
    ReferenceAuthorityConfigurationProvider,
    ReferenceHrProvider,
    assignment_payload,
    authority_payload,
    material,
    role_payload,
    rule_payload,
    version,
)

# Sentinel distinguishing "the caller said nothing, use the reference provider"
# from "the caller explicitly wants this port UNBOUND", which is what the
# NS-AP-03 / NS-HR-01 provider-not-configured scenarios need.
_DEFAULT = object()

AUTHORITY_ID = "authority-1"
ROLE_ID = "role-1"
RULE_ID = "rule-1"
ASSIGNMENT_ID = "assignment-1"
V1 = "0001"
V2 = "0002"


def authority_material(*, versions=None, retractions=(), object_id: str = AUTHORITY_ID):
    if versions is None:
        versions = (version(V1, T0, payload=authority_payload()),)
    return material(BUSINESS_AUTHORITY, object_id, versions, retractions)


def role_material(*, versions=None, retractions=(), object_id: str = ROLE_ID):
    if versions is None:
        versions = (version(V1, T0, payload=role_payload()),)
    return material(BUSINESS_AUTHORITY_ROLE, object_id, versions, retractions)


def rule_material(*, versions=None, retractions=(), object_id: str = RULE_ID, **payload_kwargs):
    if versions is None:
        versions = (
            version(
                V1,
                T0,
                payload=rule_payload(
                    role_id=payload_kwargs.pop("role_id", ROLE_ID),
                    authority_id=payload_kwargs.pop("authority_id", AUTHORITY_ID),
                    scope_type=payload_kwargs.pop("scope_type", SCOPE_GLOBAL),
                    scope_id=payload_kwargs.pop("scope_id", None),
                    evaluator_type=payload_kwargs.pop("evaluator_type", EVALUATOR_NONE),
                    parameter_payload=payload_kwargs.pop("parameter_payload", None),
                ),
            ),
        )
    return material(BUSINESS_AUTHORITY_RULE, object_id, versions, retractions)


def assignment_material(
    *, versions=None, retractions=(), object_id: str = ASSIGNMENT_ID, **payload_kwargs
):
    if versions is None:
        versions = (
            version(
                V1,
                T0,
                payload=assignment_payload(
                    role_id=payload_kwargs.pop("role_id", ROLE_ID),
                    person_id=payload_kwargs.pop("person_id", PERSON_ID),
                    position_id=payload_kwargs.pop("position_id", None),
                    scope_type=payload_kwargs.pop("scope_type", SCOPE_GLOBAL),
                    scope_id=payload_kwargs.pop("scope_id", None),
                ),
            ),
        )
    return material(BUSINESS_AUTHORITY_ASSIGNMENT, object_id, versions, retractions)


def world(
    *,
    authority=None,
    role=None,
    rule=None,
    assignment=None,
    extra=(),
) -> list:
    """The four-object baseline world, with any object replaceable."""

    return [
        authority if authority is not None else authority_material(),
        role if role is not None else role_material(),
        rule if rule is not None else rule_material(),
        assignment if assignment is not None else assignment_material(),
        *extra,
    ]


def run(
    materials,
    *,
    as_of: datetime = T2,
    authority_code: str = AUTHORITY_CODE,
    actor_id: str = ACTOR_ID,
    business_context: BusinessContext | None = None,
    actor_person_port=_DEFAULT,
    hr_reference_port=_DEFAULT,
    authority_configuration_port=_DEFAULT,
    order: str = "contract",
    seed: int = 0,
    hr_staleness_threshold_seconds: int | None = None,
) -> AuthorityResolutionResult:
    """Resolve against the pure kernel at ONE explicit business-effective instant.

    Tests drive the kernel directly rather than `resolve_current_authority`,
    because a deterministic temporal corpus needs an explicit instant. That is
    exactly the split section 10.3 defines: the kernel takes an explicit
    instant, and only the live entry point may obtain one from a clock.
    """

    port = authority_configuration_port
    if port is _DEFAULT:
        port = None
    if port is None and materials is not None:
        port = ReferenceAuthorityConfigurationProvider(materials, order=order, seed=seed)

    request = AuthorityResolutionRequest(
        authenticated_actor=AuthenticatedActor(actor_user_public_id=actor_id),
        authority_code=authority_code,
        business_context=business_context or BusinessContext(),
        hr_staleness_threshold_seconds=hr_staleness_threshold_seconds,
    )

    return resolve(
        request=request,
        as_of=as_of,
        authority_configuration_port=port,
        actor_person_port=(
            ReferenceActorPersonProvider()
            if actor_person_port is _DEFAULT
            else actor_person_port
        ),
        hr_reference_port=(
            ReferenceHrProvider() if hr_reference_port is _DEFAULT else hr_reference_port
        ),
    )
