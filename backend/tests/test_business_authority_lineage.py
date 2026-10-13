"""PF-1A-E2-A section 18: TEMPORAL, LINEAGE AND CLOSURE, and ACTIVE STATE.

Covers the VALID-SHAPE parity scenarios V-01 to V-07, the class A lineage
contradictions A-01, A-02, A-04 to A-07, and non-store scenario NS-RS-01.

THE CLASSIFICATION NOTE OF SECTION 18 (F-10.3a) APPLIES THROUGHOUT. The
branches of the 11.4 asserted-interval rule do NOT all carry the same label:
the four VALID branches are valid-shape parity scenarios carrying NO class
label, and only the two CONTRADICTORY branches are class A negative fixtures.
Describing a valid closure, adjacency, gap or reactivation shape as "class A"
is the F-10.3a defect.
"""

from __future__ import annotations

from app.modules.authorization.business_authority.contract import (
    ASSIGNMENT_NOT_ACTIVE,
    ASSIGNMENT_NOT_EFFECTIVE,
    AUTHORITY_CODE_NOT_CONFIGURED,
    AUTHORITY_LINEAGE_CONTRADICTORY,
    AUTHORITY_NOT_ACTIVE,
    NO_CANDIDATE_ASSIGNMENT,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    PUBLICATION_PROVENANCE_INVALID,
    ROLE_NOT_ACTIVE,
    ROLE_NOT_EFFECTIVE,
    RULE_NOT_ACTIVE,
    RULE_NOT_EFFECTIVE,
    STATUS_FAIL_CLOSED,
    STATUS_RESOLVED,
)
from tests.fixtures.pf_1a_e2_a_corpus import covers
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    RECORDED_AT,
    T0,
    T1,
    T2,
    T3,
    TICK,
    assignment_payload,
    authority_payload,
    retraction,
    role_payload,
    rule_payload,
    version,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    V1,
    V2,
    assignment_material,
    authority_material,
    role_material,
    rule_material,
    run,
    world,
)


def _resolved_authority_version(result) -> str | None:
    reference = result.established_state.requested_authority
    return reference.object_version if reference is not None else None


def _partial_reasons(result) -> set[str]:
    return {partial.reason_code for partial in result.partial_evaluations}


# ===========================================================================
# V-01  null-end successor closure
# ===========================================================================


@covers("V-01")
def test_a_successor_closes_a_null_ended_predecessor_without_mutating_it() -> None:
    """V1 [t0, null) with V2 from t2 -> V1 asserted end = t2, DERIVED not stored.

    The successor closes the open-ended predecessor BY EXISTING, with no
    mutation of any published row. That is what makes the model fully
    append-only while still letting a later version bound an earlier one
    (11.3, 11.4).
    """

    versions = (
        version(V1, T0, payload=authority_payload()),
        version(V2, T2, payload=authority_payload()),
    )
    authority = authority_material(versions=versions)

    before = run(world(authority=authority), as_of=T1)
    assert before.outcome == OUTCOME_ALLOW
    assert _resolved_authority_version(before) == V1

    at_and_after = run(world(authority=authority), as_of=T2)
    assert _resolved_authority_version(at_and_after) == V2

    # V1's published row is untouched: its declared_effective_to is still None.
    # The asserted end is DERIVED, never stored (11.4).
    assert authority.versions[0].declared_effective_to is None


# ===========================================================================
# V-02  explicit adjacency
# ===========================================================================


@covers("V-02")
def test_explicit_adjacency_has_no_gap_and_no_overlap() -> None:
    """V1 [t0, t2), V2 from t2 -> the intervals meet exactly at a half-open boundary."""

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(), declared_effective_to=T2),
            version(V2, T2, payload=authority_payload()),
        )
    )

    assert _resolved_authority_version(run(world(authority=authority), as_of=T2 - TICK)) == V1
    # Exactly at t2 ONLY V2 is effective.
    assert _resolved_authority_version(run(world(authority=authority), as_of=T2)) == V2


# ===========================================================================
# V-03 / V-04  the VALID GAP, per family, and reactivation after it
# ===========================================================================


def _gapped(payload_factory, family_material):
    """V1 [t0, t1), V2 from t3 - a valid gap covering t2."""

    return family_material(
        versions=(
            version(V1, T0, payload=payload_factory(), declared_effective_to=T1),
            version(V2, T3, payload=payload_factory()),
        )
    )


@covers("V-03")
def test_a_declared_end_before_the_successor_start_is_a_valid_gap_not_a_truncation() -> None:
    authority = _gapped(authority_payload, authority_material)

    # Inside the gap [t1, t3): NO version of the object is effective. The
    # asserted end is neither truncated to something else nor extended to t3.
    inside = run(world(authority=authority), as_of=T2)
    assert inside.resolution_status == STATUS_FAIL_CLOSED
    assert inside.result_level_reason == AUTHORITY_CODE_NOT_CONFIGURED

    assert _resolved_authority_version(run(world(authority=authority), as_of=T1 - TICK)) == V1


@covers("V-03")
def test_gap_behaviour_for_assignment_rule_and_role_is_normal_nonqualification() -> None:
    """The three families that describe an ABSENT GRANT (11.5).

    None of these is corruption and none fails closed. A gap is also never
    reported as overlap or as a dangling reference.
    """

    # Built explicitly rather than through the shared helper, so each family's
    # gap carries its own correctly typed payload.
    gapped_assignment = assignment_material(
        versions=(
            version(V1, T0, payload=assignment_payload(), declared_effective_to=T1),
            version(V2, T3, payload=assignment_payload()),
        )
    )
    result = run(world(assignment=gapped_assignment), as_of=T2)
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert ASSIGNMENT_NOT_EFFECTIVE in _partial_reasons(result)

    gapped_rule = rule_material(
        versions=(
            version(V1, T0, payload=rule_payload(), declared_effective_to=T1),
            version(V2, T3, payload=rule_payload()),
        )
    )
    result = run(world(rule=gapped_rule), as_of=T2)
    assert result.resolution_status == STATUS_RESOLVED
    assert RULE_NOT_EFFECTIVE in _partial_reasons(result)

    gapped_role = _gapped(role_payload, role_material)
    result = run(world(role=gapped_role), as_of=T2)
    assert result.resolution_status == STATUS_RESOLVED
    assert ROLE_NOT_EFFECTIVE in _partial_reasons(result)


@covers("V-03")
def test_a_gap_is_never_reported_as_overlap_or_as_a_dangling_reference() -> None:
    """Reintroducing the cycle-1 F-05 defect would show up exactly here."""

    gapped_role = _gapped(role_payload, role_material)
    result = run(world(role=gapped_role), as_of=T2)
    assert result.result_level_reason != AUTHORITY_LINEAGE_CONTRADICTORY
    assert result.result_level_reason != "AUTHORITY_REFERENCE_DANGLING"


@covers("V-04")
def test_a_later_valid_version_after_a_gap_is_reactivation_and_does_grant() -> None:
    """A LATER VALID VERSION AFTER A GAP IS REACTIVATION, NOT CORRUPTION."""

    authority = _gapped(authority_payload, authority_material)
    reactivated = run(world(authority=authority), as_of=T3)
    assert reactivated.outcome == OUTCOME_ALLOW
    assert _resolved_authority_version(reactivated) == V2


# ===========================================================================
# NS-RS-01  the REQUESTED authority's deliberate asymmetry
# ===========================================================================


@covers("NS-RS-01")
def test_requested_authority_with_no_grant_eligible_version_fails_closed() -> None:
    """NS-RS-01, which replaces the withdrawn fixture A-12.

    EVERY STORED ROW IS VALID. What is under test is the RESOLVER's deliberate
    asymmetry at an as_of (11.5): the other three families describe an ABSENT
    GRANT, while an unestablished REQUESTED authority describes an UNKNOWN
    QUESTION and therefore fails closed.

    Three shapes: lineage not started, lineage ended, and an as_of inside a
    VALID GAP.
    """

    not_started = authority_material(versions=(version(V1, T3, payload=authority_payload()),))
    ended = authority_material(
        versions=(version(V1, T0, payload=authority_payload(), declared_effective_to=T1),)
    )
    gapped = _gapped(authority_payload, authority_material)

    for authority in (not_started, ended, gapped):
        result = run(world(authority=authority), as_of=T2)
        assert result.outcome == OUTCOME_DENY
        assert result.resolution_status == STATUS_FAIL_CLOSED
        assert result.result_level_reason == AUTHORITY_CODE_NOT_CONFIGURED
        # Ordinary 16.4 evidence, and never an ordinary nonqualification.
        assert result.partial_evaluations
        assert result.partial_evaluations[0].reason_code == AUTHORITY_CODE_NOT_CONFIGURED


# ===========================================================================
# A-01  EXPLICIT OVERLAP - and proof the rejected min() formula is absent
# ===========================================================================


@covers("A-01")
def test_an_explicit_end_after_the_successor_start_fails_closed() -> None:
    """A-01: V1 [t0, t3), V2 from t2, t0 < t2 < t3 -> CONTRADICTORY OVERLAP.

    This is attack surface 17a's direct probe. The rejected formula
    min(declared_effective_to, next_start) would silently resolve V1 as
    [t0, t2) and make explicit-overlap detection unreachable, so the test
    asserts BOTH that the overlap fails closed AND that an instant inside the
    would-be-truncated window still fails closed rather than resolving V1.
    """

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(), declared_effective_to=T3),
            version(V2, T2, payload=authority_payload()),
        )
    )

    at_overlap = run(world(authority=authority), as_of=T2)
    assert at_overlap.resolution_status == STATUS_FAIL_CLOSED
    assert at_overlap.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY

    # THE REGRESSION PROBE. Under the rejected min(...) formula this instant
    # would fall inside a normalized V1 [t0, t2) and resolve cleanly.
    inside_would_be_truncation = run(world(authority=authority), as_of=T1)
    assert inside_would_be_truncation.resolution_status == STATUS_FAIL_CLOSED
    assert inside_would_be_truncation.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY
    assert _resolved_authority_version(inside_would_be_truncation) is None


# ===========================================================================
# A-02  DUPLICATE START
# ===========================================================================


@covers("A-02")
def test_two_versions_sharing_one_effective_from_fail_closed_with_no_tie_break() -> None:
    """A-02. Closure is NOT derived and NO tie-break is attempted.

    This shape must remain STORABLE in any persisted store: no uniqueness
    constraint on (stable_object_id, effective_from) may be introduced to
    pre-empt it, because this contract requires its classification and its
    provider parity.
    """

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T0, payload=authority_payload()),
        )
    )
    result = run(world(authority=authority), as_of=T1)
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY
    # Neither version was preferred.
    assert _resolved_authority_version(result) is None


# ===========================================================================
# V-07  exact half-open boundary instants
# ===========================================================================


@covers("V-07")
def test_every_half_open_boundary_instant_resolves_as_the_contract_states() -> None:
    """effective_from INCLUSIVE; asserted_effective_to EXCLUSIVE."""

    authority = authority_material(
        versions=(version(V1, T1, payload=authority_payload(), declared_effective_to=T3),)
    )

    # exactly at effective_from -> effective
    assert run(world(authority=authority), as_of=T1).outcome == OUTCOME_ALLOW
    # one tick before effective_from -> NOT effective
    assert run(world(authority=authority), as_of=T1 - TICK).result_level_reason == (
        AUTHORITY_CODE_NOT_CONFIGURED
    )
    # one tick before asserted_effective_to -> effective
    assert run(world(authority=authority), as_of=T3 - TICK).outcome == OUTCOME_ALLOW
    # exactly at asserted_effective_to -> NOT effective
    assert run(world(authority=authority), as_of=T3).result_level_reason == (
        AUTHORITY_CODE_NOT_CONFIGURED
    )


@covers("V-07")
def test_boundary_instants_around_a_valid_gap() -> None:
    authority = _gapped(authority_payload, authority_material)

    # exactly at the gap start -> inside the gap
    assert run(world(authority=authority), as_of=T1).result_level_reason == (
        AUTHORITY_CODE_NOT_CONFIGURED
    )
    # one tick inside the gap
    assert run(world(authority=authority), as_of=T1 + TICK).result_level_reason == (
        AUTHORITY_CODE_NOT_CONFIGURED
    )
    # one tick before the gap end -> still inside
    assert run(world(authority=authority), as_of=T3 - TICK).result_level_reason == (
        AUTHORITY_CODE_NOT_CONFIGURED
    )
    # exactly at the gap end -> reactivated
    assert run(world(authority=authority), as_of=T3).outcome == OUTCOME_ALLOW


@covers("V-07")
def test_a_future_dated_version_confers_nothing_before_its_effective_from() -> None:
    """Applied to every family, per section 18 TEMPORAL."""

    future_authority = authority_material(versions=(version(V1, T3, payload=authority_payload()),))
    assert run(world(authority=future_authority), as_of=T1).resolution_status == STATUS_FAIL_CLOSED

    future_assignment = assignment_material(
        versions=(version(V1, T3, payload=assignment_payload()),)
    )
    result = run(world(assignment=future_assignment), as_of=T1)
    assert result.resolution_status == STATUS_RESOLVED
    assert ASSIGNMENT_NOT_EFFECTIVE in _partial_reasons(result)

    future_rule = rule_material(versions=(version(V1, T3, payload=rule_payload()),))
    result = run(world(rule=future_rule), as_of=T1)
    assert RULE_NOT_EFFECTIVE in _partial_reasons(result)

    future_role = role_material(versions=(version(V1, T3, payload=role_payload()),))
    result = run(world(role=future_role), as_of=T1)
    assert ROLE_NOT_EFFECTIVE in _partial_reasons(result)


# ===========================================================================
# V-05 / V-06  ACTIVE STATE, for each family independently
# ===========================================================================


@covers("V-05")
def test_an_inactive_but_effective_version_never_fails_closed_in_any_family() -> None:
    """An unambiguously INACTIVE effective version is a deliberate, known
    configuration state, not corruption, and produces deterministic
    NONQUALIFICATION with the family's own *_NOT_ACTIVE reason (8.2)."""

    inactive_assignment = assignment_material(
        versions=(version(V1, T0, payload=assignment_payload(), active_flag=False),)
    )
    result = run(world(assignment=inactive_assignment))
    assert result.resolution_status == STATUS_RESOLVED
    assert ASSIGNMENT_NOT_ACTIVE in _partial_reasons(result)

    inactive_rule = rule_material(
        versions=(version(V1, T0, payload=rule_payload(), active_flag=False),)
    )
    result = run(world(rule=inactive_rule))
    assert result.resolution_status == STATUS_RESOLVED
    assert RULE_NOT_ACTIVE in _partial_reasons(result)

    inactive_role = role_material(
        versions=(version(V1, T0, payload=role_payload(), active_flag=False),)
    )
    result = run(world(role=inactive_role))
    assert result.resolution_status == STATUS_RESOLVED
    assert ROLE_NOT_ACTIVE in _partial_reasons(result)


@covers("V-05")
def test_an_inactive_requested_authority_short_circuits_to_deny_resolved() -> None:
    """AUTHORITY_NOT_ACTIVE is the 15.3 branch 3a short-circuit."""

    inactive_authority = authority_material(
        versions=(version(V1, T0, payload=authority_payload(), active_flag=False),)
    )
    result = run(world(authority=inactive_authority))
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason == AUTHORITY_NOT_ACTIVE
    # Inactivity and unresolvability are different answers and are never merged.
    assert result.result_level_reason != AUTHORITY_CODE_NOT_CONFIGURED


@covers("V-06")
def test_an_inactive_version_still_closes_its_predecessor_in_derived_closure() -> None:
    """Publishing an INACTIVE version is exactly how an object is deactivated
    without a successor, and that version legitimately closes its predecessor.

    Excluding inactive versions from lineage would silently RE-OPEN a
    deactivated predecessor - the blocking defect 8.2 names. If that happened
    here, V1 would still be open at t3 and the result would wrongly be ALLOW.
    """

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T2, payload=authority_payload(), active_flag=False),
        )
    )
    result = run(world(authority=authority), as_of=T3)
    assert result.outcome == OUTCOME_DENY
    assert result.result_level_reason == AUTHORITY_NOT_ACTIVE
    assert _resolved_authority_version(result) == V2


@covers("V-05")
def test_active_flag_and_effective_time_are_never_inferred_from_one_another() -> None:
    """A version that is inactive but effective, and one that is active but not
    yet effective, produce DIFFERENT reason codes (section 18 ACTIVE STATE)."""

    inactive_effective = authority_material(
        versions=(version(V1, T0, payload=authority_payload(), active_flag=False),)
    )
    active_not_yet_effective = authority_material(
        versions=(version(V1, T3, payload=authority_payload(), active_flag=True),)
    )

    assert run(world(authority=inactive_effective), as_of=T2).result_level_reason == (
        AUTHORITY_NOT_ACTIVE
    )
    assert run(world(authority=active_not_yet_effective), as_of=T2).result_level_reason == (
        AUTHORITY_CODE_NOT_CONFIGURED
    )


# ===========================================================================
# A-04 to A-07  retraction and correction contradictions
# ===========================================================================


@covers("A-04")
def test_a_retraction_targeting_a_version_that_does_not_exist_fails_closed() -> None:
    authority = authority_material(
        versions=(version(V1, T0, payload=authority_payload()),),
        retractions=(retraction("r1", "9999"),),
    )
    result = run(world(authority=authority))
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


@covers("A-05")
def test_two_retraction_assertions_for_one_version_fail_closed() -> None:
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T2, payload=authority_payload()),
        ),
        retractions=(retraction("r1", V1), retraction("r2", V1)),
    )
    result = run(world(authority=authority))
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


@covers("A-06")
def test_a_correcting_version_whose_target_is_not_retracted_fails_closed() -> None:
    """Correction is RETRACT-then-republish (11.6). A correcting version whose
    target exists but was never retracted is broken correction lineage."""

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T2, payload=authority_payload(), corrects_object_version=V1),
        )
    )
    result = run(world(authority=authority))
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


@covers("A-07")
def test_a_correcting_version_whose_target_does_not_exist_fails_closed() -> None:
    authority = authority_material(
        versions=(version(V2, T2, payload=authority_payload(), corrects_object_version="9999"),)
    )
    result = run(world(authority=authority))
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


def test_a_valid_correction_retracts_and_replaces_and_still_grants() -> None:
    """The positive control for A-06/A-07: a WELL-FORMED correction resolves.

    Without this, the two negative tests above could pass against an
    implementation that simply rejected every `corrects_object_version`.
    """

    later = RECORDED_AT.replace(hour=13)
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(
                V2,
                T0,
                payload=authority_payload(),
                corrects_object_version=V1,
                published_at=later,
            ),
        ),
        retractions=(retraction("r1", V1),),
    )
    result = run(world(authority=authority), as_of=T1)
    assert result.outcome == OUTCOME_ALLOW
    assert _resolved_authority_version(result) == V2


# ===========================================================================
# A-08 to A-10  impossible RECORDED provenance (11.8.3)
# ===========================================================================


@covers("A-08")
def test_a_retraction_recorded_before_its_target_was_published_fails_closed() -> None:
    earlier = RECORDED_AT.replace(hour=11)
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T2, payload=authority_payload()),
        ),
        retractions=(retraction("r1", V1, retracted_at=earlier),),
    )
    result = run(world(authority=authority))
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID


@covers("A-09")
def test_a_correction_recorded_before_its_target_was_retracted_fails_closed() -> None:
    retracted_later = RECORDED_AT.replace(hour=14)
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(
                V2,
                T2,
                payload=authority_payload(),
                corrects_object_version=V1,
                published_at=RECORDED_AT,
            ),
        ),
        retractions=(retraction("r1", V1, retracted_at=retracted_later),),
    )
    result = run(world(authority=authority))
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID


@covers("A-10")
def test_published_at_decreasing_across_increasing_object_version_fails_closed() -> None:
    """Version numbers are assigned in PUBLICATION order, so a higher
    object_version whose published_at precedes a lower one is contradictory."""

    earlier = RECORDED_AT.replace(hour=11)
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(), published_at=RECORDED_AT),
            version(V2, T2, payload=authority_payload(), published_at=earlier),
        )
    )
    result = run(world(authority=authority))
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID


def test_equal_recorded_timestamps_are_permitted_and_a_backdated_publication_is_valid() -> None:
    """Simultaneity is not by itself a defect, and NOTHING ties published_at to
    effective_from: a version published today may assert any business-effective
    interval, past or future, because a backdated correction is normal (11.8.3)."""

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(), published_at=RECORDED_AT),
            version(V2, T2, payload=authority_payload(), published_at=RECORDED_AT),
        )
    )
    assert run(world(authority=authority), as_of=T3).outcome == OUTCOME_ALLOW

    # A version published long AFTER the business interval it asserts.
    much_later = RECORDED_AT.replace(year=2027)
    backdated = authority_material(
        versions=(version(V1, T0, payload=authority_payload(), published_at=much_later),)
    )
    assert run(world(authority=backdated), as_of=T1).outcome == OUTCOME_ALLOW


# ===========================================================================
# NO_CANDIDATE_ASSIGNMENT, which 14.2 defines against an established rule/role
# ===========================================================================


def test_no_candidate_assignment_requires_the_authority_rules_and_roles_established() -> None:
    """14.2: NO_CANDIDATE_ASSIGNMENT means the authority and its rules/roles WERE
    established and no assignment candidate targeted this person at all."""

    result = run([authority_material(), role_material(), rule_material()])
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason == NO_CANDIDATE_ASSIGNMENT
    assert result.established_state.rules_discovered == 1
    assert result.established_state.roles_referenced == 1
    assert result.established_state.assignments_discovered == 0
