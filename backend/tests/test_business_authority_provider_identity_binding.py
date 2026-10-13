"""PF-1A-E2-A correction FU-1: a provider response must be bound to the
canonical identity that was REQUESTED.

C1 validated lookup status, value type and freshness. It did not check that the
object a provider RETURNED is the object that was ASKED ABOUT. The controller
reproduced fail-open ALLOW cases at several seams: a fresh, otherwise-valid
response describing a DIFFERENT canonical object was accepted as the requested
object's authoritative state.

    Every authoritative provider response used for authorization must be
    canonically bound back to the canonical identity requested.

Never rely on the provider being well behaved. Never merely validate a Python
type. Never substitute, coerce or repair a mismatched identity. And never treat
a mismatch as ordinary nonqualification: it means the requested authoritative
fact was NOT established, which is a provider-contract failure and takes an
existing FAIL_CLOSED code.
"""

from __future__ import annotations

from app.modules.authorization.business_authority.contract import (
    ACTOR_PERSON_MAPPING_MISSING,
    AUTHORITY_CONFIGURATION_UNAVAILABLE,
    BUSINESS_AUTHORITY_ROLE,
    EMPLOYMENT_STATE_MISSING,
    HR_REFERENCE_STALE,
    HR_REFERENCE_UNAVAILABLE,
    INCUMBENCY_MISSING,
    ORG_HIERARCHY_UNRESOLVABLE,
    ORG_UNIT_STATE_MISSING,
    OTHER_NONQUALIFICATION,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    POSITION_STATE_MISSING,
    SCOPE_ANCESTRY,
    STATUS_FAIL_CLOSED,
)
from app.modules.authorization.business_authority.domain import BusinessContext
from app.modules.authorization.business_authority.evidence import serialize_result
from app.modules.authorization.business_authority.scope import SCOPE_KIND_ORG_UNIT
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    ACTOR_ID,
    ORDER_REVERSED,
    ORDER_SHUFFLED,
    ORG_BRANCH,
    ORG_ROOT,
    OTHER_PERSON_ID,
    POSITION_ID,
    T2,
    ReferenceActorPersonProvider,
    ReferenceAuthorityConfigurationProvider,
    ReferenceHrProvider,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    assignment_material,
    rule_material,
    run,
    world,
)

OTHER_ACTOR_ID = "actor-9999"
OTHER_POSITION_ID = "position-9999"
OTHER_ORG_UNIT_ID = "org-9999"


def _position_world():
    return world(assignment=assignment_material(person_id=None, position_id=POSITION_ID))


def _ancestry_world():
    return world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_ROOT))


def _ancestry_context() -> BusinessContext:
    return BusinessContext(scope_type=SCOPE_KIND_ORG_UNIT, scope_id=ORG_BRANCH)


def _assert_fails_closed(result, reason: str) -> None:
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == reason
    # A provider-contract failure is NEVER ordinary nonqualification.
    assert result.result_level_reason != OTHER_NONQUALIFICATION
    assert result.qualifying_paths == ()


# ===========================================================================
# A — the actor -> canonical person boundary
# ===========================================================================


def test_a_response_for_a_different_authenticated_actor_cannot_authorize_this_one() -> None:
    """The most serious of the reproduced cases.

    The provider returns a fresh, otherwise-valid mapping whose own
    `actor_user_public_id` is a DIFFERENT actor, and whose person happens to
    hold the requested authority. Accepting it would authorize actor A using
    actor B's identity.
    """

    impersonating = ReferenceActorPersonProvider(returned_actor_id=OTHER_ACTOR_ID)
    result = run(world(), actor_person_port=impersonating)

    _assert_fails_closed(result, HR_REFERENCE_UNAVAILABLE)
    # NOT silently reported as an absent mapping.
    assert result.result_level_reason != ACTOR_PERSON_MAPPING_MISSING
    # No canonical person was established from the foreign response.
    assert result.established_state.person_id is None


def test_the_same_provider_still_authorizes_when_it_answers_about_the_actor_requested() -> None:
    """The negative control: identity binding must reject the WRONG response,
    not every response."""

    assert run(world(), actor_person_port=ReferenceActorPersonProvider()).outcome == OUTCOME_ALLOW


def test_the_foreign_actor_identity_is_not_echoed_into_evidence() -> None:
    """A response that failed identity binding is not about the requested
    object, so nothing from it is cited."""

    result = run(
        world(), actor_person_port=ReferenceActorPersonProvider(returned_actor_id=OTHER_ACTOR_ID)
    )
    serialized = serialize_result(result)
    assert OTHER_ACTOR_ID not in serialized
    assert ACTOR_ID in serialized


# ===========================================================================
# B — employment state
# ===========================================================================


def test_employment_state_for_a_different_person_cannot_authorize() -> None:
    mismatched = ReferenceHrProvider(returned_person_id=OTHER_PERSON_ID)
    result = run(world(), hr_reference_port=mismatched)

    _assert_fails_closed(result, HR_REFERENCE_UNAVAILABLE)
    assert result.result_level_reason != EMPLOYMENT_STATE_MISSING


# ===========================================================================
# C — Position
# ===========================================================================


def test_a_position_reference_identifying_a_different_position_cannot_be_used() -> None:
    mismatched = ReferenceHrProvider(returned_position_id=OTHER_POSITION_ID)
    result = run(_position_world(), hr_reference_port=mismatched)

    _assert_fails_closed(result, HR_REFERENCE_UNAVAILABLE)
    assert result.result_level_reason != POSITION_STATE_MISSING


# ===========================================================================
# D — Incumbency
# ===========================================================================


def test_an_incumbency_whose_canonical_position_differs_cannot_be_accepted() -> None:
    """The incumbency's own canonical position identity must be the position
    that was asked about - otherwise it describes who occupies some OTHER
    position."""

    mismatched = ReferenceHrProvider(returned_incumbency_position_id=OTHER_POSITION_ID)
    result = run(_position_world(), hr_reference_port=mismatched)

    _assert_fails_closed(result, HR_REFERENCE_UNAVAILABLE)
    assert result.result_level_reason != INCUMBENCY_MISSING


# ===========================================================================
# E — Organisation Unit ancestry
# ===========================================================================


def test_an_organisation_unit_reference_identifying_a_different_unit_cannot_traverse() -> None:
    """Following a foreign unit would walk a chain the request never asked
    about, and could satisfy an ancestry operand through an unrelated part of
    the hierarchy."""

    mismatched = ReferenceHrProvider(returned_org_unit_id=OTHER_ORG_UNIT_ID)
    result = run(
        _ancestry_world(),
        business_context=_ancestry_context(),
        hr_reference_port=mismatched,
    )

    _assert_fails_closed(result, HR_REFERENCE_UNAVAILABLE)
    assert result.result_level_reason != ORG_UNIT_STATE_MISSING
    assert result.result_level_reason != ORG_HIERARCHY_UNRESOLVABLE


def test_the_same_ancestry_still_resolves_when_each_hop_answers_about_itself() -> None:
    result = run(
        _ancestry_world(),
        business_context=_ancestry_context(),
        hr_reference_port=ReferenceHrProvider(),
    )
    assert result.outcome == OUTCOME_ALLOW


# ===========================================================================
# F — authority configuration lineage material
# ===========================================================================


def test_lineage_material_for_a_different_object_family_cannot_be_trusted() -> None:
    provider = ReferenceAuthorityConfigurationProvider(world()).with_failure(
        return_family_of=BUSINESS_AUTHORITY_ROLE
    )
    result = run(None, authority_configuration_port=provider)
    _assert_fails_closed(result, AUTHORITY_CONFIGURATION_UNAVAILABLE)


def test_lineage_material_for_a_different_object_id_cannot_be_trusted() -> None:
    provider = ReferenceAuthorityConfigurationProvider(world()).with_failure(
        return_object_id_of="some-other-object"
    )
    result = run(None, authority_configuration_port=provider)
    _assert_fails_closed(result, AUTHORITY_CONFIGURATION_UNAVAILABLE)


def test_conforming_lineage_material_still_resolves() -> None:
    provider = ReferenceAuthorityConfigurationProvider(world())
    assert run(None, authority_configuration_port=provider).outcome == OUTCOME_ALLOW


def test_the_resolution_path_never_calls_get_published_version() -> None:
    """The remaining canonical provider seam, audited (FU-1).

    `get_published_version` carries a requested (family, object_id,
    object_version) and could in principle return a different one. The kernel
    never calls it during resolution - dereference is an evidence/audit
    operation, not an authorization input - so there is no unbound seam here.
    This test pins that property: if a future change routes resolution through
    dereference, it must add the same identity binding, and this test fails
    until it does.
    """

    calls: list[tuple[str, str, str]] = []

    class _RecordingProvider(ReferenceAuthorityConfigurationProvider):
        def get_published_version(self, object_family, object_id, object_version):
            calls.append((object_family, object_id, object_version))
            return super().get_published_version(object_family, object_id, object_version)

    provider = _RecordingProvider(world())
    assert run(None, authority_configuration_port=provider).outcome == OUTCOME_ALLOW
    assert calls == []


# ===========================================================================
# Adversarial combinations
# ===========================================================================


def test_a_correct_identity_with_a_wrong_status_still_fails_closed() -> None:
    result = run(world(), hr_reference_port=ReferenceHrProvider(employment_status_override="BOGUS"))
    _assert_fails_closed(result, HR_REFERENCE_UNAVAILABLE)


def test_a_correct_identity_and_status_with_a_stale_snapshot_still_fails_closed() -> None:
    stale = ReferenceHrProvider(snapshot_at=T2.replace(year=2020))
    result = run(
        world(),
        actor_person_port=ReferenceActorPersonProvider(snapshot_at=T2),
        hr_reference_port=stale,
        hr_staleness_threshold_seconds=3600,
    )
    _assert_fails_closed(result, HR_REFERENCE_STALE)


def test_a_wrong_identity_and_a_stale_snapshot_reports_the_identity_failure() -> None:
    """Identity binding is checked BEFORE freshness, deliberately: a response
    that is not about the requested object at all has no meaningful freshness
    to assess."""

    both_wrong = ReferenceHrProvider(
        returned_person_id=OTHER_PERSON_ID, snapshot_at=T2.replace(year=2020)
    )
    result = run(
        world(),
        actor_person_port=ReferenceActorPersonProvider(snapshot_at=T2),
        hr_reference_port=both_wrong,
        hr_staleness_threshold_seconds=3600,
    )
    _assert_fails_closed(result, HR_REFERENCE_UNAVAILABLE)
    assert result.result_level_reason != HR_REFERENCE_STALE


def test_identity_binding_failures_are_deterministic_under_shuffling_and_repetition() -> None:
    def resolve(order, seed):
        return run(
            world(),
            hr_reference_port=ReferenceHrProvider(returned_person_id=OTHER_PERSON_ID),
            order=order,
            seed=seed,
        )

    baseline = serialize_result(resolve("contract", 0))
    assert serialize_result(resolve(ORDER_REVERSED, 0)) == baseline
    for seed in range(4):
        assert serialize_result(resolve(ORDER_SHUFFLED, seed)) == baseline
    for _ in range(3):
        assert serialize_result(resolve("contract", 0)) == baseline


def test_every_identity_mismatch_seam_produces_partial_evidence_without_fabrication() -> None:
    seams = (
        (world(), ReferenceActorPersonProvider(returned_actor_id=OTHER_ACTOR_ID), ReferenceHrProvider(), None),
        (world(), ReferenceActorPersonProvider(), ReferenceHrProvider(returned_person_id=OTHER_PERSON_ID), None),
        (_position_world(), ReferenceActorPersonProvider(), ReferenceHrProvider(returned_position_id=OTHER_POSITION_ID), None),
        (_position_world(), ReferenceActorPersonProvider(), ReferenceHrProvider(returned_incumbency_position_id=OTHER_POSITION_ID), None),
        (_ancestry_world(), ReferenceActorPersonProvider(), ReferenceHrProvider(returned_org_unit_id=OTHER_ORG_UNIT_ID), _ancestry_context()),
    )
    for materials, actor_port, hr_port, context in seams:
        result = run(
            materials,
            business_context=context,
            actor_person_port=actor_port,
            hr_reference_port=hr_port,
        )
        assert result.resolution_status == STATUS_FAIL_CLOSED
        assert result.partial_evaluations
        head = result.partial_evaluations[0]
        assert head.reason_code == result.result_level_reason
        for ref in head.established:
            assert ref.object_id and ref.object_version
