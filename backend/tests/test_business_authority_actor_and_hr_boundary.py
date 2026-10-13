"""PF-1A-E2-A section 18: ACTOR BOUNDARY, POSITION ASSIGNMENT and TEMPORAL.

Covers non-store scenarios NS-AP-01 to NS-AP-04, NS-HR-01 to NS-HR-09,
NS-RS-02 and NS-RS-03.

THE TRUST BOUNDARY (7.1, 9.1). The input to actor-person resolution is ALWAYS
the authenticated actor's own application-user public identifier, taken from
the server-side authenticated context. A client-supplied person_id, employee
code, username or display name is NEVER accepted as the identity being
authorized, and no caller may reach across that boundary.

THE BOUNDARY BETWEEN STORE AND HR (5.7A note on NS-HR-08/09). A position
ASSIGNMENT VERSION is authority-store data, and its malformed target shapes
are class B1 (B1-02, B1-03). The INCUMBENCY answer about that position is
HR-supplied and non-store. The two must not be conflated.
"""

from __future__ import annotations

import inspect

from app.modules.authorization.business_authority import resolver
from app.modules.authorization.business_authority.contract import (
    ACTOR_PERSON_MAPPING_AMBIGUOUS,
    ACTOR_PERSON_MAPPING_MISSING,
    ACTOR_PERSON_PROVIDER_NOT_CONFIGURED,
    ASSIGNMENT_TARGET_NOT_THIS_PERSON,
    EMPLOYMENT_NOT_ACTIVE,
    EMPLOYMENT_STATE_AMBIGUOUS,
    EMPLOYMENT_STATE_MISSING,
    HR_REFERENCE_PROVIDER_NOT_CONFIGURED,
    HR_REFERENCE_STALE,
    HR_REFERENCE_UNAVAILABLE,
    INCUMBENCY_AMBIGUOUS,
    INCUMBENCY_MISSING,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    POSITION_STATE_AMBIGUOUS,
    POSITION_STATE_MISSING,
    STAGE_S1_PERSON,
    STAGE_S2_EMPLOYMENT,
    STATUS_FAIL_CLOSED,
    STATUS_RESOLVED,
)
from app.modules.authorization.business_authority.domain import (
    AuthenticatedActor,
    BusinessContext,
)
from app.modules.hr_reference.contract import (
    EMPLOYMENT_INACTIVE,
    EMPLOYMENT_LEFT,
    EMPLOYMENT_ON_LEAVE,
)
from tests.fixtures.pf_1a_e2_a_corpus import covers
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    ACTOR_ID,
    OTHER_PERSON_ID,
    PERSON_ID,
    POSITION_ID,
    T2,
    ReferenceActorPersonProvider,
    ReferenceAuthorityConfigurationProvider,
    ReferenceHrProvider,
)
from tests.fixtures.pf_1a_e2_a_scenarios import assignment_material, run, world


def _position_world():
    return world(
        assignment=assignment_material(person_id=None, position_id=POSITION_ID)
    )


# ===========================================================================
# NS-AP-01 to NS-AP-03  the actor -> canonical person seam
# ===========================================================================


@covers("NS-AP-01")
def test_no_actor_person_mapping_fails_closed_at_stage_s1() -> None:
    result = run(
        world(), actor_person_port=ReferenceActorPersonProvider(status="MISSING")
    )
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == ACTOR_PERSON_MAPPING_MISSING
    assert result.ordered_defects[0].stage == STAGE_S1_PERSON
    # 16.4 partial evidence: no fabricated object/version pairs.
    assert result.partial_evaluations[0].established == ()


@covers("NS-AP-02")
def test_more_than_one_actor_person_mapping_fails_closed_and_never_picks_one() -> None:
    result = run(
        world(), actor_person_port=ReferenceActorPersonProvider(status="AMBIGUOUS")
    )
    assert result.result_level_reason == ACTOR_PERSON_MAPPING_AMBIGUOUS
    assert result.established_state.person_id is None, "no canonical person may be selected"


@covers("NS-AP-03")
def test_an_unbound_actor_person_provider_fails_closed() -> None:
    result = run(world(), actor_person_port=None)
    assert result.result_level_reason == ACTOR_PERSON_PROVIDER_NOT_CONFIGURED
    assert result.resolution_status == STATUS_FAIL_CLOSED


# ===========================================================================
# NS-AP-04  the identity TRUST BOUNDARY
# ===========================================================================


@covers("NS-AP-04")
def test_no_client_controlled_identity_hint_can_influence_the_identity_authorized() -> None:
    """The supplied value influences NOTHING: identity comes only from the
    authenticated actor, through the port.

    The business context is the one caller-controlled structure the kernel
    consumes, so this drives an identity hint through it and asserts the
    resolved canonical person is unchanged.
    """

    hostile_context = BusinessContext(
        declared_facts={
            "person_id": OTHER_PERSON_ID,
            "employee_code": "EMP-9999",
            "username": "someone-else",
            "actor_user_public_id": "actor-9999",
        }
    )
    result = run(world(), business_context=hostile_context)

    assert result.outcome == OUTCOME_ALLOW
    assert result.established_state.person_id == PERSON_ID
    assert result.actor_user_public_id == ACTOR_ID


@covers("NS-AP-04")
def test_neither_entry_point_accepts_a_person_identity_parameter() -> None:
    """Asserted against the entry-point SURFACE, because wiring is exactly
    where such a parameter could be reintroduced."""

    current = inspect.signature(resolver.resolve_current_authority)
    assert "person_id" not in current.parameters
    assert "canonical_person" not in current.parameters

    # The actor parameter's own type carries no person identity either.
    actor_fields = set(AuthenticatedActor.__dataclass_fields__)
    assert actor_fields == {"actor_user_public_id"}


# ===========================================================================
# NS-HR-01 to NS-HR-05  the canonical HR reference seam, before S3
# ===========================================================================


@covers("NS-HR-01")
def test_an_unbound_hr_provider_fails_closed() -> None:
    result = run(world(), hr_reference_port=None)
    assert result.result_level_reason == HR_REFERENCE_PROVIDER_NOT_CONFIGURED
    assert result.ordered_defects[0].stage == STAGE_S2_EMPLOYMENT


@covers("NS-HR-02")
def test_an_unavailable_hr_reference_fails_closed() -> None:
    result = run(world(), hr_reference_port=ReferenceHrProvider(employment_result="UNAVAILABLE"))
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE


@covers("NS-HR-03")
def test_a_stale_canonical_snapshot_fails_closed_against_a_SUPPLIED_threshold() -> None:
    """The staleness threshold VALUE remains a deferred policy parameter: the
    test SUPPLIES one, and the kernel invents no default (section 7, 23)."""

    fresh_actor = ReferenceActorPersonProvider(snapshot_at=T2)
    stale_hr = ReferenceHrProvider(snapshot_at=T2.replace(year=2025))

    stale = run(
        world(),
        actor_person_port=fresh_actor,
        hr_reference_port=stale_hr,
        hr_staleness_threshold_seconds=3600,
    )
    assert stale.resolution_status == STATUS_FAIL_CLOSED
    assert stale.result_level_reason == HR_REFERENCE_STALE

    # WITH NO THRESHOLD CONFIGURED the kernel applies none and invents none.
    # The identical snapshot now resolves, which is what proves no default
    # value was quietly assumed.
    without_threshold = run(
        world(), actor_person_port=fresh_actor, hr_reference_port=stale_hr
    )
    assert without_threshold.outcome == OUTCOME_ALLOW


@covers("NS-HR-03")
def test_a_provider_reported_stale_answer_fails_closed_without_any_threshold() -> None:
    result = run(world(), hr_reference_port=ReferenceHrProvider(employment_result="STALE"))
    assert result.result_level_reason == HR_REFERENCE_STALE


@covers("NS-HR-04")
def test_a_missing_employment_state_fails_closed() -> None:
    result = run(world(), hr_reference_port=ReferenceHrProvider(employment_result="MISSING"))
    assert result.result_level_reason == EMPLOYMENT_STATE_MISSING


@covers("NS-HR-05")
def test_an_ambiguous_employment_state_fails_closed() -> None:
    result = run(world(), hr_reference_port=ReferenceHrProvider(employment_result="AMBIGUOUS"))
    assert result.result_level_reason == EMPLOYMENT_STATE_AMBIGUOUS


def test_an_unambiguously_non_active_employment_state_is_resolved_not_fail_closed() -> None:
    """Distinction 1 of 14.4: KNOWN-AND-NO versus NOT-KNOWN.

    The difference is whether the system knows the answer, not whether the
    answer is unfavourable. A resolved non-active status is a normal
    DENY + RESOLVED short-circuit; a missing or ambiguous one fails closed.
    """

    for status in (EMPLOYMENT_INACTIVE, EMPLOYMENT_ON_LEAVE, EMPLOYMENT_LEFT):
        result = run(world(), hr_reference_port=ReferenceHrProvider(employment_status=status))
        assert result.outcome == OUTCOME_DENY, status
        assert result.resolution_status == STATUS_RESOLVED, status
        assert result.result_level_reason == EMPLOYMENT_NOT_ACTIVE, status


# ===========================================================================
# NS-HR-06 to NS-HR-09  position and incumbency, at stage S7
# ===========================================================================


@covers("NS-HR-06")
def test_a_missing_position_state_fails_closed() -> None:
    result = run(_position_world(), hr_reference_port=ReferenceHrProvider(position_result="MISSING"))
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == POSITION_STATE_MISSING


@covers("NS-HR-07")
def test_an_ambiguous_position_state_fails_closed() -> None:
    result = run(
        _position_world(), hr_reference_port=ReferenceHrProvider(position_result="AMBIGUOUS")
    )
    assert result.result_level_reason == POSITION_STATE_AMBIGUOUS


@covers("NS-HR-08")
def test_no_incumbent_at_as_of_fails_closed() -> None:
    """Also the shape a FUTURE or EXPIRED incumbency takes at this boundary:
    the canonical port answers about the instant it was asked about, so an
    incumbency that has not started, or has ended, is simply not effective at
    `as_of` and the port reports MISSING."""

    result = run(
        _position_world(), hr_reference_port=ReferenceHrProvider(incumbency_result="MISSING")
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == INCUMBENCY_MISSING


@covers("NS-HR-09")
def test_more_than_one_incumbent_at_as_of_fails_closed() -> None:
    result = run(
        _position_world(), hr_reference_port=ReferenceHrProvider(incumbency_result="AMBIGUOUS")
    )
    assert result.result_level_reason == INCUMBENCY_AMBIGUOUS


def test_a_position_assignment_grants_only_to_the_current_incumbent() -> None:
    """A position assignment NEVER confers authority on a former incumbent:
    incumbency is RE-RESOLVED at the same instant every time, never inferred
    from history (12.1, attack surface 20)."""

    granted = run(_position_world())
    assert granted.outcome == OUTCOME_ALLOW
    path = granted.qualifying_paths[0]
    assert path.hr_evidence.incumbency_id == f"incumbency-{POSITION_ID}"
    assert path.hr_evidence.position_version_id == f"position-version-{POSITION_ID}"

    someone_else = run(
        _position_world(),
        hr_reference_port=ReferenceHrProvider(incumbent_person_id=OTHER_PERSON_ID),
    )
    # A DIFFERENT incumbent is ordinary nonqualification, not a defect.
    assert someone_else.outcome == OUTCOME_DENY
    assert someone_else.resolution_status == STATUS_RESOLVED
    assert ASSIGNMENT_TARGET_NOT_THIS_PERSON in {
        partial.reason_code for partial in someone_else.partial_evaluations
    }


def test_a_person_assignment_to_someone_else_is_ordinary_nonqualification() -> None:
    materials = world(assignment=assignment_material(person_id=OTHER_PERSON_ID))
    result = run(materials)
    assert result.resolution_status == STATUS_RESOLVED
    assert ASSIGNMENT_TARGET_NOT_THIS_PERSON in {
        partial.reason_code for partial in result.partial_evaluations
    }


# ===========================================================================
# NS-RS-02  ONE server-captured instant governs the whole live resolution
# ===========================================================================


@covers("NS-RS-02")
def test_one_live_resolution_captures_exactly_one_instant_and_uses_it_everywhere(
    monkeypatch,
) -> None:
    """11.1: no component may call its own clock or resolve against a different
    instant. A second clock read would be observable here as a differing
    instant reaching one of the ports."""

    reads: list[int] = []
    instants = [T2, T2.replace(year=2030), T2.replace(year=2031)]

    def counting_now():
        reads.append(len(reads))
        return instants[min(len(reads) - 1, len(instants) - 1)]

    monkeypatch.setattr(resolver, "_now", counting_now)

    actor_port = ReferenceActorPersonProvider()
    hr_port = ReferenceHrProvider()
    configuration_port = ReferenceAuthorityConfigurationProvider(_position_world())

    result = resolver.resolve_current_authority(
        AuthenticatedActor(actor_user_public_id=ACTOR_ID),
        "CREDIT_ASSESSOR",
        authority_configuration_port=configuration_port,
        actor_person_port=actor_port,
        hr_reference_port=hr_port,
    )

    assert result.outcome == OUTCOME_ALLOW
    assert len(reads) == 1, "the live resolution read a clock more than once"

    observed = set(actor_port.observed_as_of) | set(hr_port.observed_as_of)
    assert observed == {T2}, "a component resolved against a different instant"
    assert result.as_of == T2


# ===========================================================================
# NS-RS-03  the two entry points' parameter surfaces
# ===========================================================================


@covers("NS-RS-03")
def test_the_current_authorization_entry_point_exposes_no_as_of() -> None:
    """A client must not be able to re-acquire authority it used to hold."""

    parameters = inspect.signature(resolver.resolve_current_authority).parameters
    assert "as_of" not in parameters
    # No **kwargs through which one could be smuggled.
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    )


@covers("NS-RS-03")
def test_neither_entry_point_exposes_a_recorded_time_cutoff() -> None:
    """Offering a caller-selected published_at cutoff would be a backdating
    attack under a different name (11.8.2). POINT-IN-TIME RECORDED-KNOWLEDGE
    REPLAY is explicitly NOT the E2 historical resolver contract."""

    forbidden = {
        "published_at",
        "published_before",
        "as_known_at",
        "known_at",
        "recorded_at",
        "recorded_before",
        "retracted_at",
        "knowledge_cutoff",
    }
    for entry_point in (resolver.resolve_current_authority, resolver.resolve_authority_as_of):
        parameters = set(inspect.signature(entry_point).parameters)
        assert not (parameters & forbidden), entry_point.__name__


@covers("NS-RS-03")
def test_the_historical_resolver_is_a_separate_named_entry_point() -> None:
    """The separation is STRUCTURAL, not merely documented: separate entry
    points, separate naming, separate signatures. The historical resolver must
    never authorize a new current business action, and it is reached only by
    supplying an explicit business-effective instant."""

    historical = inspect.signature(resolver.resolve_authority_as_of).parameters
    assert "as_of" in historical
    assert resolver.resolve_authority_as_of is not resolver.resolve_current_authority

    # And the historical resolver does not read the clock at all.
    source = inspect.getsource(resolver.resolve_authority_as_of)
    assert "_now(" not in source


def test_the_historical_resolver_reconstructs_at_the_supplied_business_instant() -> None:
    """A positive control for the entry point itself, so the surface assertions
    above are not the only thing exercising it."""

    from tests.fixtures.pf_1a_e2_a_reference_providers import RECORDED_AT, T0
    from app.modules.hr_reference.contract import ActorPersonReference

    reference = ActorPersonReference(
        actor_user_public_id=ACTOR_ID,
        person_id=PERSON_ID,
        canonical_snapshot_at=RECORDED_AT,
        reference_evidence="synthetic-actor-person-link",
    )
    result = resolver.resolve_authority_as_of(
        reference,
        "CREDIT_ASSESSOR",
        None,
        T2,
        authority_configuration_port=ReferenceAuthorityConfigurationProvider(world()),
        hr_reference_port=ReferenceHrProvider(),
    )
    assert result.outcome == OUTCOME_ALLOW
    assert result.as_of == T2

    # Before the configuration was ever effective, the same question
    # reconstructs a different answer.
    earlier = resolver.resolve_authority_as_of(
        reference,
        "CREDIT_ASSESSOR",
        None,
        T0.replace(year=2020),
        authority_configuration_port=ReferenceAuthorityConfigurationProvider(world()),
        hr_reference_port=ReferenceHrProvider(),
    )
    assert earlier.outcome == OUTCOME_DENY
