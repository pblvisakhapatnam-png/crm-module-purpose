"""The two resolution entry points, deliberately separated.

PF-1A-E2-A sections 10.1, 10.2, 11.8.2 and 9.6.

    resolve_current_authority   captures ONE server-controlled, timezone-aware
                                current instant and uses it for the ENTIRE
                                evaluation. It accepts NO caller-supplied
                                as_of and exposes NO recorded-time cutoff.
    resolve_authority_as_of     accepts an explicit BUSINESS-EFFECTIVE instant
                                for audit, reconstruction, reconciliation and
                                deterministic tests. It must NEVER be used to
                                authorize a new current business action.

THE SEPARATION IS STRUCTURAL, NOT MERELY DOCUMENTED. The two are separate
entry points with separate names and separate signatures, and a test proves
the current-authorization path exposes neither an `as_of` parameter nor any
recorded-time bound such as a `published_at` cutoff, through any signature,
DTO field or keyword pass-through. Offering a caller-selected `published_at`
cutoff would be a backdating attack under a different name (11.8.2).

WHAT THE HISTORICAL RESOLVER IS, AND IS NOT (11.8.1). It performs CORRECTED
BUSINESS-EFFECTIVE RECONSTRUCTION under the complete authoritative
publication/correction lineage known AT INVOCATION TIME. A version published
today that asserts a business-effective interval containing an older `as_of`
DOES participate in reconstructing that older instant, and a retraction
recorded today DOES remove its target from that reconstruction. POINT-IN-TIME
RECORDED-KNOWLEDGE REPLAY - "reconstruct using only the publications known by
recorded time T" - is explicitly NOT this contract, is not implemented here,
and must not be approximated by filtering on `published_at`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.authorization.business_authority.domain import (
    AuthenticatedActor,
    AuthorityResolutionRequest,
    BusinessContext,
)
from app.modules.authorization.business_authority.evidence import AuthorityResolutionResult
from app.modules.authorization.business_authority.kernel import resolve
from app.modules.authorization.business_authority.ports import AuthorityConfigurationPort
from app.modules.hr_reference.contract import ActorPersonReference, HrLookup, ok
from app.modules.hr_reference.ports import ActorPersonPort, CanonicalHrReferencePort


class ProductionCompositionUnavailableError(RuntimeError):
    """A production composition was attempted without authoritative providers.

    Section 9.6 permits exactly two behaviours for a production composition
    that lacks an authoritative actor-person or HR/organisation provider:
    (a) REFUSE TO COMPOSE at all, so no resolver object exists; or (b) if a
    resolver object exists, deterministically return DENY + FAIL_CLOSED with
    ACTOR_PERSON_PROVIDER_NOT_CONFIGURED / HR_REFERENCE_PROVIDER_NOT_CONFIGURED
    on every call.

    THIS PACKAGE CHOOSES (a), because no authoritative provider exists yet and
    refusing to compose makes the absence impossible to overlook. Silent
    substitution of a synthetic provider is a blocking defect and is
    structurally prevented: the reference/synthetic providers live under
    `backend/tests/`, so no production module can import one.

    WHERE THE SEAM ITSELF LIVES, and why not here (independent review finding
    F4). There is exactly ONE production composition implementation:
    `production_composition.build_production_business_authority_resolver`. It
    lives there rather than here because the canonical seam must BIND the
    authority configuration provider E2-B supplies, and that provider is
    persistence-bound while this module is deliberately not. Until PF-1A-E2-B
    this module also carried a `build_production_resolver()` that bound
    nothing and raised its own separately authored refusal; two successor-
    facing seams can drift apart the moment a later package adds the
    actor-person and HR providers to one of them, so the phase-local one was
    withdrawn rather than left as a second binding point. Nothing it
    guaranteed was weakened: the seam still takes no environment variable,
    settings flag, feature toggle or provider argument, still reaches no
    synthetic provider, still exposes no `as_of` or recorded-time cutoff, and
    still refuses to compose. This type remains the ONE refusal signal, raised
    from the ONE seam.
    """


def _now() -> datetime:
    """The ONE server-controlled clock read permitted in this package.

    It is a module-level function purely so a deterministic test can prove it
    is consulted EXACTLY ONCE per live resolution and that no component
    consults a second clock (11.1, NS-RS-02).
    """

    return datetime.now(timezone.utc)


def resolve_current_authority(
    authenticated_actor: AuthenticatedActor,
    authority_code: str,
    business_context: BusinessContext | None = None,
    *,
    authority_configuration_port: AuthorityConfigurationPort | None,
    actor_person_port: ActorPersonPort | None,
    hr_reference_port: CanonicalHrReferencePort | None,
    hr_staleness_threshold_seconds: int | None = None,
) -> AuthorityResolutionResult:
    """Authorize a CURRENT business action.

    The single instant is captured HERE and governs every stage of the
    evaluation: actor-person mapping, employment state, position version,
    incumbency, organisation unit versions, authority versions, role versions,
    rules, assignments, scope resolution and parameter evaluation. No
    component calls a clock of its own.

    There is deliberately no `as_of` parameter and no recorded-time bound. A
    client must not be able to re-acquire authority it used to hold.
    """

    as_of = _now()

    request = AuthorityResolutionRequest(
        authenticated_actor=authenticated_actor,
        authority_code=authority_code,
        business_context=business_context or BusinessContext(),
        hr_staleness_threshold_seconds=hr_staleness_threshold_seconds,
    )

    return resolve(
        request=request,
        as_of=as_of,
        authority_configuration_port=authority_configuration_port,
        actor_person_port=actor_person_port,
        hr_reference_port=hr_reference_port,
    )


class _FixedActorPersonReference:
    """Echoes an ALREADY-AUTHORITATIVE person reference supplied by the caller.

    This is not a provider and not a synthetic HR source: the historical
    resolver's own contract (10.2) takes the canonical person reference as an
    input, and this adapter is only what lets the ONE pure kernel be reused
    unchanged for both entry points.
    """

    def __init__(self, reference: ActorPersonReference) -> None:
        self._reference = reference

    def resolve_actor_person(self, actor_user_public_id: str, as_of: datetime) -> HrLookup:
        return ok(self._reference)


def resolve_authority_as_of(
    actor_person_reference: ActorPersonReference,
    authority_code: str,
    business_context: BusinessContext | None,
    as_of: datetime,
    *,
    authority_configuration_port: AuthorityConfigurationPort | None,
    hr_reference_port: CanonicalHrReferencePort | None,
    hr_staleness_threshold_seconds: int | None = None,
) -> AuthorityResolutionResult:
    """Reconstruct what was business-effective at an explicit historical instant.

    FOR AUDIT, RECONSTRUCTION, RECONCILIATION AND DETERMINISTIC TESTS ONLY.
    This must never authorize a new current business action.

    `as_of` is a BUSINESS-EFFECTIVE instant. It is never a recorded time, and
    this function exposes no recorded-time cutoff or as-known-at parameter.
    """

    request = AuthorityResolutionRequest(
        authenticated_actor=AuthenticatedActor(
            actor_user_public_id=actor_person_reference.actor_user_public_id
        ),
        authority_code=authority_code,
        business_context=business_context or BusinessContext(),
        hr_staleness_threshold_seconds=hr_staleness_threshold_seconds,
    )

    return resolve(
        request=request,
        as_of=as_of,
        authority_configuration_port=authority_configuration_port,
        actor_person_port=_FixedActorPersonReference(actor_person_reference),
        hr_reference_port=hr_reference_port,
    )
