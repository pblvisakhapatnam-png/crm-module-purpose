"""PF-1A-E2-A correction C1-1: raw superset discovery must not grant through a
HISTORICAL parent reference.

TWO FAIL-OPEN DEFECTS, both reproduced by controller inspection:

    CASE A   Rule V1 -> Business Authority A, current Rule V2 -> Authority B.
             The Rule is still legitimately DISCOVERED for A, because discovery
             is deliberately a SUPERSET over RAW published facts (9.3.1). Its
             CURRENT EFFECTIVE version belongs to B and must not participate in
             a grant path for A.
    CASE B   Assignment V1 -> Role R, current Assignment V2 -> Role R2. Same
             rule, one level down.

THE FIX IS NOT TO NARROW DISCOVERY. Discovery stays raw and superset, complete
lineage is still validated before any semantic interpretation, historical rows
are not discarded, and a malformed historical retraction or correction still
surfaces its own fail-closed defect. The mismatch is evaluated ONLY after
authoritative lineage has been successfully established, and it is ordinary
nonqualification - not corruption.

It is reported as the ONE bounded fallback, OTHER_NONQUALIFICATION, with a
deterministic kernel-generated explanation. No RULE_* or ASSIGNMENT_* mismatch
reason code is invented.
"""

from __future__ import annotations

from app.modules.authorization.business_authority.contract import (
    ASSIGNMENT_NOT_EFFECTIVE,
    AUTHORITY_LINEAGE_CONTRADICTORY,
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
    OTHER_NONQUALIFICATION,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    RULE_NOT_ACTIVE,
    STATUS_FAIL_CLOSED,
    STATUS_RESOLVED,
)
from app.modules.authorization.business_authority.evidence import serialize_result
from tests.fixtures.pf_1a_e2_a_corpus import covers
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    AUTHORITY_CODE,
    ORDER_REVERSED,
    ORDER_SHUFFLED,
    T0,
    T1,
    T2,
    T3,
    ReferenceAuthorityConfigurationProvider,
    assignment_payload,
    authority_payload,
    retraction,
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
)

AUTHORITY_A = "authority-a"
AUTHORITY_B = "authority-b"
CODE_B = "SOME_OTHER_AUTHORITY"
ROLE_R = "role-r"
ROLE_R2 = "role-r2"
RULE_ID = "rule-1"
ASSIGNMENT_ID = "assignment-1"


# ===========================================================================
# CASE A — the Rule's parent Business Authority changed
# ===========================================================================


def _rule_reparented(*, active_flag: bool = True, retractions=()):
    """Rule V1 [t0, t1) -> Authority A; current Rule V2 from t1 -> Authority B."""

    return rule_material(
        object_id=RULE_ID,
        versions=(
            version(
                V1,
                T0,
                payload=rule_payload(role_id=ROLE_R, authority_id=AUTHORITY_A),
                declared_effective_to=T1,
            ),
            version(
                V2,
                T1,
                payload=rule_payload(role_id=ROLE_R, authority_id=AUTHORITY_B),
                active_flag=active_flag,
            ),
        ),
        retractions=retractions,
    )


def _case_a_world(**kwargs):
    return [
        authority_material(object_id=AUTHORITY_A),
        authority_material(
            object_id=AUTHORITY_B,
            versions=(version(V1, T0, payload=authority_payload(CODE_B)),),
        ),
        role_material(object_id=ROLE_R),
        _rule_reparented(**kwargs),
        assignment_material(object_id=ASSIGNMENT_ID, role_id=ROLE_R),
    ]


def test_a_historical_rule_reference_cannot_grant_the_authority_it_no_longer_carries() -> None:
    """PROOF 1. Authority A must NOT be granted through a Rule whose current
    effective version belongs to Authority B."""

    result = run(_case_a_world(), as_of=T2, authority_code=AUTHORITY_CODE)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.qualifying_paths == ()

    reasons = {partial.reason_code for partial in result.partial_evaluations}
    assert reasons == {OTHER_NONQUALIFICATION}
    # Ordinary nonqualification, never corruption.
    assert result.ordered_defects == ()


def test_the_same_current_rule_still_grants_the_authority_it_does_carry() -> None:
    """PROOF 2. The correction denies the WRONG path, not the right one.

    Without this, a fix that simply rejected the Rule outright would pass
    proof 1 while breaking every legitimate grant.
    """

    result = run(_case_a_world(), as_of=T2, authority_code=CODE_B)

    assert result.outcome == OUTCOME_ALLOW
    assert result.resolution_status == STATUS_RESOLVED
    path = result.qualifying_paths[0]
    assert path.business_authority.ref.object_id == AUTHORITY_B
    assert path.business_authority_rule.ref.object_version == V2


def test_before_the_reparenting_the_historical_rule_version_still_grants_authority_a() -> None:
    """The historical row is not discarded: at an as_of where V1 IS the current
    effective version, it grants Authority A exactly as it always did."""

    result = run(_case_a_world(), as_of=T0, authority_code=AUTHORITY_CODE)
    assert result.outcome == OUTCOME_ALLOW
    assert result.qualifying_paths[0].business_authority_rule.ref.object_version == V1


# ===========================================================================
# CASE B — the Assignment's parent Business Authority Role changed
# ===========================================================================


def _assignment_reparented():
    """Assignment V1 [t0, t1) -> Role R; current Assignment V2 from t1 -> Role R2."""

    return assignment_material(
        object_id=ASSIGNMENT_ID,
        versions=(
            version(
                V1,
                T0,
                payload=assignment_payload(role_id=ROLE_R),
                declared_effective_to=T1,
            ),
            version(V2, T1, payload=assignment_payload(role_id=ROLE_R2)),
        ),
    )


def _case_b_world(*, through_role: str):
    """Only ONE rule, so exactly one role path is offered."""

    role_id = through_role
    return [
        authority_material(),
        role_material(object_id=role_id),
        rule_material(object_id=RULE_ID, role_id=role_id),
        _assignment_reparented(),
    ]


def test_a_historical_assignment_reference_cannot_grant_through_the_role_it_left() -> None:
    """PROOF 3."""

    result = run(_case_b_world(through_role=ROLE_R), as_of=T2)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.qualifying_paths == ()
    assert {p.reason_code for p in result.partial_evaluations} == {OTHER_NONQUALIFICATION}
    assert result.ordered_defects == ()


def test_the_same_current_assignment_still_grants_through_its_current_role() -> None:
    """PROOF 4."""

    result = run(_case_b_world(through_role=ROLE_R2), as_of=T2)

    assert result.outcome == OUTCOME_ALLOW
    path = result.qualifying_paths[0]
    assert path.business_authority_role.ref.object_id == ROLE_R2
    assert path.business_authority_assignment.ref.object_version == V2


# ===========================================================================
# PROOF 5 — discovery is still RAW and still a SUPERSET
# ===========================================================================


@covers("V-08")
def test_raw_discovery_still_returns_both_objects_from_their_historical_references() -> None:
    """THE CORRECTION MUST NOT HAVE NARROWED DISCOVERY.

    If a later change "fixed" the fail-open by filtering discovery, this test
    fails - which is the whole point of asserting it separately from the
    resolution outcome.
    """

    provider = ReferenceAuthorityConfigurationProvider(_case_a_world())
    assert list(provider.find_rule_ids_for_authority(AUTHORITY_A)) == [RULE_ID]
    assert list(provider.find_rule_ids_for_authority(AUTHORITY_B)) == [RULE_ID]

    provider_b = ReferenceAuthorityConfigurationProvider(_case_b_world(through_role=ROLE_R))
    assert list(provider_b.find_assignment_ids_for_role(ROLE_R)) == [ASSIGNMENT_ID]
    assert list(provider_b.find_assignment_ids_for_role(ROLE_R2)) == [ASSIGNMENT_ID]


def test_the_mismatched_object_lineage_still_reaches_the_kernel() -> None:
    """Complete lineage is still fetched and validated before the mismatch is
    even considered - the mismatch is not a discovery-time or read-time
    shortcut."""

    provider = ReferenceAuthorityConfigurationProvider(_case_a_world())
    run(None, authority_configuration_port=provider, as_of=T2, authority_code=AUTHORITY_CODE)
    assert (BUSINESS_AUTHORITY_RULE, RULE_ID) in provider.observed_lineage_calls


# ===========================================================================
# PROOF 6 — malformed historical material is still not hidden
# ===========================================================================


def test_a_malformed_historical_retraction_still_fails_closed_despite_the_mismatch() -> None:
    """The mismatch handling must never swallow a lineage defect.

    Order of operations (11.3): complete lineage is validated FIRST, and only
    then is the current effective version's parent reference compared. A
    duplicated retraction of the historical version must therefore still fail
    the whole resolution closed, not be quietly reported as an ordinary
    nonqualification.
    """

    result = run(
        _case_a_world(retractions=(retraction("r1", V1), retraction("r2", V1))),
        as_of=T2,
        authority_code=AUTHORITY_CODE,
    )

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY
    assert result.result_level_reason != OTHER_NONQUALIFICATION


def test_invalid_provenance_on_the_mismatched_object_still_fails_closed() -> None:
    """The same guarantee for a provenance defect rather than a lineage one."""

    reparented_with_bad_provenance = rule_material(
        object_id=RULE_ID,
        versions=(
            version(
                V1,
                T0,
                payload=rule_payload(role_id=ROLE_R, authority_id=AUTHORITY_A),
                declared_effective_to=T1,
            ),
            version(
                V2,
                T1,
                payload=rule_payload(role_id=ROLE_R, authority_id=AUTHORITY_B),
                published_at=None,
            ),
        ),
    )
    materials = [
        authority_material(object_id=AUTHORITY_A),
        role_material(object_id=ROLE_R),
        reparented_with_bad_provenance,
        assignment_material(object_id=ASSIGNMENT_ID, role_id=ROLE_R),
    ]
    result = run(materials, as_of=T2, authority_code=AUTHORITY_CODE)
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == "PUBLICATION_PROVENANCE_INVALID"


# ===========================================================================
# PROOF 7 — the deterministic, kernel-generated explanation
# ===========================================================================


def _only_partial(result):
    assert len(result.partial_evaluations) == 1
    return result.partial_evaluations[0]


def test_the_rule_mismatch_carries_a_deterministic_explanation_naming_both_references() -> None:
    """The evidence must make the EXPECTED and the CURRENT reference
    unambiguous, using canonical stable identifiers only."""

    partial = _only_partial(run(_case_a_world(), as_of=T2, authority_code=AUTHORITY_CODE))

    explanation = partial.nonqualification_explanation
    assert explanation
    assert BUSINESS_AUTHORITY_RULE in explanation
    assert RULE_ID in explanation and V2 in explanation
    # BOTH the actual (B) and the expected (A) reference.
    assert AUTHORITY_B in explanation
    assert AUTHORITY_A in explanation
    assert BUSINESS_AUTHORITY in explanation


def test_the_assignment_mismatch_carries_the_expected_and_actual_role_references() -> None:
    partial = _only_partial(run(_case_b_world(through_role=ROLE_R), as_of=T2))

    explanation = partial.nonqualification_explanation
    assert explanation
    assert BUSINESS_AUTHORITY_ASSIGNMENT in explanation
    assert ASSIGNMENT_ID in explanation and V2 in explanation
    assert ROLE_R2 in explanation
    assert ROLE_R in explanation
    assert BUSINESS_AUTHORITY_ROLE in explanation


def test_the_explanation_is_byte_stable_across_repeated_runs() -> None:
    """Stable for the same canonical input, and built from a fixed template -
    never from provider text, user text or an exception message."""

    explanations = {
        _only_partial(
            run(_case_a_world(), as_of=T2, authority_code=AUTHORITY_CODE)
        ).nonqualification_explanation
        for _ in range(5)
    }
    assert len(explanations) == 1


def test_the_explanation_takes_no_part_in_ordering_or_result_selection() -> None:
    """It is deliberately absent from the 16.5 sort key, so it can never
    influence which item is first or which reason is reported."""

    partial = _only_partial(run(_case_a_world(), as_of=T2, authority_code=AUTHORITY_CODE))
    assert partial.nonqualification_explanation not in str(partial.sort_key)


# ===========================================================================
# PROOF 8 — provider order and repetition change nothing
# ===========================================================================


def test_shuffled_provider_order_and_repeated_runs_produce_identical_evidence() -> None:
    baseline = serialize_result(run(_case_a_world(), as_of=T2, authority_code=AUTHORITY_CODE))

    assert (
        serialize_result(
            run(_case_a_world(), as_of=T2, authority_code=AUTHORITY_CODE, order=ORDER_REVERSED)
        )
        == baseline
    )
    for seed in range(5):
        assert (
            serialize_result(
                run(
                    _case_a_world(),
                    as_of=T2,
                    authority_code=AUTHORITY_CODE,
                    order=ORDER_SHUFFLED,
                    seed=seed,
                )
            )
            == baseline
        )
    for _ in range(3):
        assert (
            serialize_result(run(_case_a_world(), as_of=T2, authority_code=AUTHORITY_CODE))
            == baseline
        )


# ===========================================================================
# PROOF 9 — an existing SPECIFIC reason is still used where it applies
# ===========================================================================


def test_an_inactive_mismatched_rule_reports_the_specific_reason_not_the_fallback() -> None:
    """OTHER_NONQUALIFICATION is NOT a shortcut for avoiding a specific reason.

    Here the current effective Rule version is BOTH inactive AND reparented.
    RULE_NOT_ACTIVE applies precisely, so it is the reason reported: the active
    check is evaluated before the reference comparison for exactly this reason.
    """

    result = run(_case_a_world(active_flag=False), as_of=T2, authority_code=AUTHORITY_CODE)

    reasons = {partial.reason_code for partial in result.partial_evaluations}
    assert reasons == {RULE_NOT_ACTIVE}
    assert OTHER_NONQUALIFICATION not in reasons


def test_an_assignment_in_a_valid_gap_reports_its_own_specific_reason() -> None:
    """A gap has its own precise reason and must keep using it."""

    gapped = assignment_material(
        object_id=ASSIGNMENT_ID,
        versions=(
            version(
                V1,
                T0,
                payload=assignment_payload(role_id=ROLE_R),
                declared_effective_to=T1,
            ),
            version(V2, T3, payload=assignment_payload(role_id=ROLE_R)),
        ),
    )
    materials = [
        authority_material(),
        role_material(object_id=ROLE_R),
        rule_material(object_id=RULE_ID, role_id=ROLE_R),
        gapped,
    ]
    result = run(materials, as_of=T2)
    reasons = {partial.reason_code for partial in result.partial_evaluations}
    assert reasons == {ASSIGNMENT_NOT_EFFECTIVE}
    assert OTHER_NONQUALIFICATION not in reasons


# ===========================================================================
# The fallback's own bounded semantics
# ===========================================================================


def test_the_fallback_is_promoted_to_the_result_level_when_every_path_shares_it() -> None:
    """The existing 15.3 branch 3c promotion applies unchanged, so the result
    stays legible; the per-path explanations remain in the evidence."""

    result = run(_case_a_world(), as_of=T2, authority_code=AUTHORITY_CODE)
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason == OTHER_NONQUALIFICATION
    assert _only_partial(result).nonqualification_explanation


def test_the_fallback_never_blocks_an_independently_qualifying_path() -> None:
    """It is ORDINARY nonqualification, so it may sit in the evidence of a
    resolution whose ALLOW came from a DIFFERENT path - exactly as every other
    path-level reason may (15.1). What it never does is grant, or decide an
    ALLOW."""

    materials = _case_b_world(through_role=ROLE_R) + [
        role_material(object_id=ROLE_R2),
        rule_material(object_id="rule-2", role_id=ROLE_R2),
    ]
    result = run(materials, as_of=T2)

    assert result.outcome == OUTCOME_ALLOW
    assert result.result_level_reason == ""
    assert OTHER_NONQUALIFICATION in {p.reason_code for p in result.partial_evaluations}
    # ... and never on the path that actually granted.
    for path in result.qualifying_paths:
        assert path.decisive_nonqualification_reason is None


def test_the_fallback_never_appears_as_a_fail_closed_reason() -> None:
    """It can never represent uncertainty, malformed, unavailable, stale,
    ambiguous or contradictory state; every one of those keeps its own
    fail-closed code."""

    fail_closed = run(
        _case_a_world(retractions=(retraction("r1", V1), retraction("r2", V1))),
        as_of=T2,
        authority_code=AUTHORITY_CODE,
    )
    assert fail_closed.resolution_status == STATUS_FAIL_CLOSED
    assert fail_closed.result_level_reason != OTHER_NONQUALIFICATION
    for defect in fail_closed.ordered_defects:
        assert defect.reason_code != OTHER_NONQUALIFICATION
