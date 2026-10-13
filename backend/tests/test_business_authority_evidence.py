"""PF-1A-E2-A section 18: EVIDENCE.

Covers non-store scenarios NS-EV-01 to NS-EV-06. (NS-EV-07, evidence
durability across later versions/retraction/correction, is exercised with the
recorded-time cases in `test_business_authority_discovery.py`, where the same
seeded state drives the 11.8.1 asymmetry it must be read against.)

NEGATIVE OUTCOMES ARE FIRST-CLASS (section 16). "It returned DENY with a
reason code" is not sufficient evidence and is a blocking defect. A denial
must be as explainable as an approval.
"""

from __future__ import annotations

from app.modules.authorization.business_authority.contract import (
    EVALUATOR_CONDITION_NOT_SATISFIED,
    EVALUATOR_NUMERIC_BAND,
    NO_CANDIDATE_ASSIGNMENT,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    RULE_SCOPE_NOT_MATCHED,
    SCOPE_ANCESTRY,
    SCOPE_EXACT,
    STAGE_S1_PERSON,
    STATUS_FAIL_CLOSED,
    STATUS_RESOLVED,
)
from app.modules.authorization.business_authority.domain import BusinessContext
from app.modules.authorization.business_authority.evidence import serialize_result
from app.modules.authorization.business_authority.scope import SCOPE_KIND_ORG_UNIT
from tests.fixtures.pf_1a_e2_a_corpus import covers
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    ACTOR_ID,
    ORDER_REVERSED,
    ORDER_SHUFFLED,
    ORG_BRANCH,
    ORG_DIVISION,
    ORG_ROOT,
    PERSON_ID,
    POSITION_ID,
    RECORDED_AT,
    T0,
    T1,
    T2,
    T3,
    ReferenceActorPersonProvider,
    ReferenceHrProvider,
    authority_payload,
    retraction,
    version,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    ASSIGNMENT_ID,
    AUTHORITY_ID,
    ROLE_ID,
    RULE_ID,
    V1,
    assignment_material,
    authority_material,
    role_material,
    rule_material,
    run,
    world,
)

_BAND = {
    "fact": "offer_value",
    "unit": "INR",
    "lower": 1000,
    "lower_inclusive": True,
}


def _context(scope_id=None, **facts) -> BusinessContext:
    return BusinessContext(
        scope_type=SCOPE_KIND_ORG_UNIT if scope_id else None,
        scope_id=scope_id,
        declared_facts=facts,
    )


# ===========================================================================
# NS-EV-01  every ALLOW carries all four pairs and every evaluation
# ===========================================================================


@covers("NS-EV-01")
def test_an_allow_carries_all_four_object_version_pairs_and_every_evaluation() -> None:
    """Omitting any one of the four pairs is a blocking defect: that is
    ORA-001's requirement as corrected by the authority configuration model
    (16.2)."""

    materials = world(
        rule=rule_material(evaluator_type=EVALUATOR_NUMERIC_BAND, parameter_payload=_BAND),
        assignment=assignment_material(person_id=None, position_id=POSITION_ID),
    )
    result = run(materials, business_context=_context(offer_value={"value": 5000, "unit": "INR"}))
    assert result.outcome == OUTCOME_ALLOW

    path = result.qualifying_paths[0]

    # All FOUR pairs.
    assert path.business_authority.ref.object_id == AUTHORITY_ID
    assert path.business_authority_role.ref.object_id == ROLE_ID
    assert path.business_authority_rule.ref.object_id == RULE_ID
    assert path.business_authority_assignment.ref.object_id == ASSIGNMENT_ID
    for pair in (
        path.business_authority,
        path.business_authority_role,
        path.business_authority_rule,
        path.business_authority_assignment,
    ):
        assert pair.ref.object_version == V1
        # THE THREE CONDITIONS OF 8.2, REPORTED SEPARATELY.
        assert pair.grant_eligibility.lineage_valid is True
        assert pair.grant_eligibility.effective_at_as_of is True
        assert pair.grant_eligibility.active_flag is True
        # RECORDED-TIME provenance, labelled as recorded time (11.8.4).
        assert pair.recorded_published_at is not None
        assert pair.publication_reference_type == "BOOTSTRAP_PROVENANCE"

    # HR evidence, including the position path's re-resolved incumbency.
    assert path.hr_evidence.person_id == PERSON_ID
    assert path.hr_evidence.employment_state_version_id
    assert path.hr_evidence.incumbency_id == f"incumbency-{POSITION_ID}"
    assert path.hr_evidence.canonical_snapshot_at_values

    # Scope operands AND the composed result.
    assert path.scope_evaluation.rule_operand_satisfied is True
    assert path.scope_evaluation.assignment_operand_satisfied is True
    assert path.scope_evaluation.composed_satisfied is True

    # Parameter evaluation, with the decisive comparison actually performed.
    assert path.parameter_evaluation.evaluator_type == EVALUATOR_NUMERIC_BAND
    assert path.parameter_evaluation.satisfied is True
    assert "offer_value=5000" in path.parameter_evaluation.decisive_comparison


# ===========================================================================
# NS-EV-02  complete nonqualifying paths, for a scope AND a parameter denial
# ===========================================================================


@covers("NS-EV-02")
def test_a_scope_denial_is_proved_rather_than_asserted() -> None:
    materials = world(rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_ROOT))
    result = run(materials, business_context=_context(ORG_BRANCH))

    assert result.outcome == OUTCOME_DENY
    path = result.complete_nonqualifying_paths[0]
    # The SAME structure as a qualifying path - all four pairs - plus the
    # decisive reason.
    assert path.business_authority.ref.object_version == V1
    assert path.business_authority_assignment.ref.object_version == V1
    assert path.decisive_nonqualification_reason == RULE_SCOPE_NOT_MATCHED
    assert path.scope_evaluation.rule_operand_satisfied is False
    assert path.scope_evaluation.assignment_operand_satisfied is True


@covers("NS-EV-02")
def test_a_parameter_denial_is_proved_rather_than_asserted() -> None:
    materials = world(
        rule=rule_material(evaluator_type=EVALUATOR_NUMERIC_BAND, parameter_payload=_BAND)
    )
    result = run(materials, business_context=_context(offer_value={"value": 5, "unit": "INR"}))

    path = result.complete_nonqualifying_paths[0]
    assert path.decisive_nonqualification_reason == EVALUATOR_CONDITION_NOT_SATISFIED
    assert path.parameter_evaluation.satisfied is False
    # The decisive comparison shows WHAT was compared, so the denial can be
    # reconstructed later without re-running it.
    assert "lower=1000" in path.parameter_evaluation.decisive_comparison


# ===========================================================================
# NS-EV-03  partial evaluations NEVER fabricate a pair
# ===========================================================================


@covers("NS-EV-03")
def test_a_partial_evaluation_records_what_exists_and_names_what_does_not() -> None:
    """NEVER fabricate the missing object/version pairs. A partial evaluation
    records what exists and NAMES what does not; it must not emit placeholder,
    null-filled or guessed pairs that a later reader could mistake for
    established state (16.4)."""

    result = run(world(), actor_person_port=ReferenceActorPersonProvider(status="MISSING"))

    assert result.resolution_status == STATUS_FAIL_CLOSED
    partial = result.partial_evaluations[0]
    # Nothing was established, so NOTHING is recorded - not four null pairs.
    assert partial.established == ()
    assert partial.last_stage_reached == STAGE_S1_PERSON
    assert partial.reason_code == result.result_level_reason
    assert partial.is_defect is True


@covers("NS-EV-03")
def test_a_partial_evaluation_records_the_pairs_that_WERE_established() -> None:
    """A later-stage failure retains EVERY item established before it, in the
    order established (correction FU-2).

    This assertion previously expected ONLY the requested Business Authority,
    which is what the defect looked like from the inside: the Rule and the Role
    had both been successfully established at S4 and S5 before the Assignment's
    provenance failed at S6, and collapsing them back to the Authority alone
    discarded real established state and violated 16.4.
    """

    result = run(
        world(
            assignment=assignment_material(
                versions=(
                    version(
                        V1,
                        T0,
                        payload=assignment_material().versions[0].payload,
                        published_at=None,
                    ),
                )
            )
        )
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    established = result.partial_evaluations[0].established
    # Authority (S3), Rule (S4) and Role (S5) were all established; the
    # Assignment was NOT, and is therefore absent rather than null-filled.
    assert [ref.object_id for ref in established] == [AUTHORITY_ID, RULE_ID, ROLE_ID]
    for ref in established:
        assert ref.object_version, "an established reference must never be a null placeholder"

    # The per-object active/effective evaluations established along the way are
    # retained too, not just the bare pairs.
    for evidence in result.partial_evaluations[0].established_objects:
        assert evidence.grant_eligibility.lineage_valid is True
        assert evidence.grant_eligibility.effective_at_as_of is True
        assert evidence.grant_eligibility.active_flag is True

    # And the HR state established before the failure.
    hr_evidence = result.partial_evaluations[0].hr_evidence
    assert hr_evidence is not None
    assert hr_evidence.person_id == PERSON_ID
    assert hr_evidence.employment_state_version_id


# ===========================================================================
# NS-EV-04  a zero-path DENY + RESOLVED still explains itself
# ===========================================================================


@covers("NS-EV-04")
def test_a_deny_resolved_with_zero_complete_paths_explains_what_was_established() -> None:
    """`established_state` is what makes this explainable: it records what was
    established and therefore why no grant path could exist (16.1)."""

    materials = [authority_material(), role_material(), rule_material()]
    result = run(materials)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason == NO_CANDIDATE_ASSIGNMENT
    assert result.qualifying_paths == ()
    assert result.complete_nonqualifying_paths == ()

    established = result.established_state
    assert established.person_id == PERSON_ID
    assert established.employment_state_version_id
    assert established.employment_status == "ACTIVE"
    assert established.requested_authority is not None
    assert established.requested_authority_eligibility.active_flag is True
    assert established.rules_discovered == 1
    assert established.roles_referenced == 1
    assert established.assignments_discovered == 0
    assert established.complete_paths_evaluated == 0
    assert established.last_stage_reached in ("S6", "S7")
    assert established.canonical_snapshot_at_values


@covers("NS-EV-04")
def test_the_result_header_carries_the_single_as_of_and_the_evaluated_context() -> None:
    result = run(world(), business_context=_context(ORG_BRANCH, offer_value={"value": 1}))
    assert result.as_of == T2
    assert result.authority_code == "CREDIT_ASSESSOR"
    assert result.actor_user_public_id == ACTOR_ID
    assert result.business_context.scope_type == SCOPE_KIND_ORG_UNIT
    assert result.business_context.scope_id == ORG_BRANCH
    # The declared facts ACTUALLY USED are recorded by name. Values are not
    # copied wholesale into evidence; the decisive comparison on each path
    # carries exactly the value the decision turned on, which is the
    # data-minimising form of the same fact (section 7, 16.5).
    assert result.business_context.declared_fact_names == ("offer_value",)


# ===========================================================================
# NS-EV-05  one collection each, and deterministic ordering
# ===========================================================================


@covers("NS-EV-05")
def test_every_candidate_touched_appears_in_exactly_one_collection() -> None:
    """Every candidate the kernel touched is accounted for in exactly one of
    16.2, 16.3 or 16.4, and a partial evaluation is never silently dropped."""

    materials = [
        authority_material(),
        role_material(object_id="role-a"),
        role_material(object_id="role-b"),
        rule_material(object_id="rule-a", role_id="role-a"),
        rule_material(
            object_id="rule-b", role_id="role-b", scope_type=SCOPE_EXACT, scope_id=ORG_ROOT
        ),
        assignment_material(object_id="assignment-a", role_id="role-a"),
        assignment_material(object_id="assignment-b", role_id="role-b"),
        assignment_material(object_id="assignment-c", role_id="role-a", person_id="person-0002"),
    ]
    result = run(materials, business_context=_context(ORG_BRANCH))

    keys = (
        [path.candidate_key for path in result.qualifying_paths]
        + [path.candidate_key for path in result.complete_nonqualifying_paths]
        + [partial.candidate_key for partial in result.partial_evaluations]
    )
    assert len(keys) == len(set(keys)), "a candidate appears in more than one collection"
    assert result.qualifying_paths, "the valid path must still be retained"
    assert result.complete_nonqualifying_paths, "the scope-denied path must be retained"
    assert result.partial_evaluations, "the wrong-person candidate must be retained"


@covers("NS-EV-05")
def test_all_collections_are_deterministically_ordered_under_shuffled_provider_output() -> None:
    materials = [
        authority_material(),
        role_material(object_id="role-a"),
        role_material(object_id="role-b"),
        rule_material(object_id="rule-a", role_id="role-a"),
        rule_material(
            object_id="rule-b", role_id="role-b", scope_type=SCOPE_EXACT, scope_id=ORG_ROOT
        ),
        assignment_material(object_id="assignment-a", role_id="role-a"),
        assignment_material(object_id="assignment-b", role_id="role-b"),
    ]
    context = _context(ORG_BRANCH)
    baseline = serialize_result(run(materials, business_context=context))

    assert serialize_result(run(materials, business_context=context, order=ORDER_REVERSED)) == (
        baseline
    )
    for seed in range(5):
        assert serialize_result(
            run(materials, business_context=context, order=ORDER_SHUFFLED, seed=seed)
        ) == baseline

    # And the path ordering is the 15.4 total order, not insertion order.
    result = run(materials, business_context=context, order=ORDER_REVERSED)
    for collection in (result.qualifying_paths, result.complete_nonqualifying_paths):
        keys = [path.path_sort_key for path in collection]
        assert keys == sorted(keys)


# ===========================================================================
# NS-EV-06  no secret, credential or provider-specific identifier
# ===========================================================================

_FORBIDDEN_IN_EVIDENCE = (
    "password",
    "password_hash",
    "token",
    "secret",
    "credential",
    "session_id",
    "authorization:",
    "bearer ",
    # provider-specific detail that must never cross the canonical boundary
    "sharepoint",
    "list_item",
    "listitem",
    "plum",
    "provider_code",
    "source_binding",
    "source_record_key",
)


@covers("NS-EV-06")
def test_no_secret_credential_or_provider_specific_identifier_appears_in_evidence() -> None:
    """NEVER INCLUDED (16.5): passwords, password hashes, tokens, session
    identifiers, any authentication secret, or any provider-specific
    identifier or field (section 7)."""

    scenarios = (
        run(world()),
        run(world(assignment=assignment_material(person_id=None, position_id=POSITION_ID))),
        run(world(), actor_person_port=ReferenceActorPersonProvider(status="AMBIGUOUS")),
        run(world(), hr_reference_port=ReferenceHrProvider(employment_result="MISSING")),
        run(
            world(
                authority=authority_material(
                    versions=(version(V1, T0, payload=authority_payload(), published_at=None),)
                )
            )
        ),
        run(world(rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_ROOT)),
            business_context=_context(ORG_BRANCH)),
    )

    for result in scenarios:
        serialized = serialize_result(result).lower()
        for forbidden in _FORBIDDEN_IN_EVIDENCE:
            assert forbidden not in serialized, f"{forbidden!r} appeared in evidence"


@covers("NS-EV-06")
def test_evidence_carries_the_actor_public_identifier_but_no_credential() -> None:
    """16.1 requires the authenticated actor REFERENCE - the application-user
    public identifier - and never a credential."""

    result = run(world())
    serialized = serialize_result(result)
    assert ACTOR_ID in serialized
    assert "password" not in serialized.lower()


# ===========================================================================
# Candidate accounting when two Rules legitimately share one Role
# ===========================================================================
# Found by self-review, not by the manifest: the kernel's own 16.4 accounting
# invariant fired on a perfectly ordinary configuration because the candidate
# key was keyed on the object being evaluated rather than on the whole
# established path prefix. Two Rules referencing ONE Role - the same Business
# Authority Role carrying the authority under two different scopes or
# parameter bands - is legitimate configuration, and each Rule/Role/Assignment
# combination is a SEPARATE candidate.


def _two_rules_one_role(assignment):
    return [
        authority_material(),
        role_material(object_id=ROLE_ID),
        rule_material(object_id="rule-a", role_id=ROLE_ID),
        rule_material(object_id="rule-b", role_id=ROLE_ID),
        assignment,
    ]


@covers("NS-EV-05")
def test_two_rules_sharing_one_role_produce_distinct_candidates_when_all_qualify() -> None:
    result = run(_two_rules_one_role(assignment_material()))
    assert result.outcome == OUTCOME_ALLOW
    assert len(result.qualifying_paths) == 2
    keys = [path.candidate_key for path in result.qualifying_paths]
    assert len(set(keys)) == 2


@covers("NS-EV-05")
def test_two_rules_sharing_one_role_produce_distinct_partials_for_one_assignment() -> None:
    """The regression this fix exists for.

    An INACTIVE assignment reached through two Rules yields TWO partial
    evaluations. With a colliding candidate key the accounting invariant fired
    and an ordinary DENY + RESOLVED became INTERNAL_CONTRACT_VIOLATION -
    uncertainty manufactured out of an entirely valid configuration.
    """

    inactive = assignment_material(
        versions=(
            version(
                V1,
                T0,
                payload=assignment_material().versions[0].payload,
                active_flag=False,
            ),
        )
    )
    result = run(_two_rules_one_role(inactive))

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason != "INTERNAL_CONTRACT_VIOLATION"
    assert len(result.partial_evaluations) == 2
    keys = [partial.candidate_key for partial in result.partial_evaluations]
    assert len(set(keys)) == 2


@covers("NS-EV-05")
def test_two_rules_sharing_one_role_in_a_gap_produce_distinct_partials() -> None:
    """The same collision one level up, at the Role rather than the Assignment."""

    from tests.fixtures.pf_1a_e2_a_reference_providers import role_payload

    gapped_role = role_material(
        object_id=ROLE_ID,
        versions=(
            version(V1, T0, payload=role_payload(), declared_effective_to=T1),
            version("0002", T3, payload=role_payload()),
        ),
    )
    materials = [
        authority_material(),
        gapped_role,
        rule_material(object_id="rule-a", role_id=ROLE_ID),
        rule_material(object_id="rule-b", role_id=ROLE_ID),
    ]
    result = run(materials, as_of=T2)

    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason == "ROLE_NOT_EFFECTIVE"
    assert len(result.partial_evaluations) == 2
    assert len({partial.candidate_key for partial in result.partial_evaluations}) == 2


# ===========================================================================
# C1-3A  RETRACTION EVIDENCE
# ===========================================================================
# `ObjectEvidence.recorded_retracted_at_of_participating_assertions` and the
# evidence helper both existed, but the kernel left the collection empty. Where
# VALID retraction assertions participated in establishing an object's current
# asserted lineage, their recorded times are required evidence (16.2).


def _authority_with_retractions(retractions, versions):
    return world(authority=authority_material(versions=versions, retractions=retractions))


def _authority_evidence(result):
    return result.qualifying_paths[0].business_authority


@covers("NS-EV-01")
def test_a_participating_retraction_carries_its_recorded_time_into_evidence() -> None:
    """The retracted version is excluded from RESOLUTION, and the assertion
    that excluded it is recorded as RECORDED-TIME provenance."""

    materials = _authority_with_retractions(
        (retraction("r1", V1),),
        (
            version(V1, T0, payload=authority_payload()),
            version("0002", T1, payload=authority_payload()),
        ),
    )
    result = run(materials, as_of=T2)

    assert result.outcome == OUTCOME_ALLOW
    evidence = _authority_evidence(result)
    # The SURVIVING version is what resolved ...
    assert evidence.ref.object_version == "0002"
    # ... and the assertion that removed its predecessor is retained.
    assert evidence.recorded_retracted_at_of_participating_assertions == (RECORDED_AT,)


@covers("NS-EV-01")
def test_an_object_with_no_retractions_carries_an_empty_collection_not_a_fabricated_one() -> None:
    result = run(world())
    assert _authority_evidence(result).recorded_retracted_at_of_participating_assertions == ()


@covers("NS-EV-05")
def test_multiple_participating_retractions_are_ordered_deterministically() -> None:
    """Ordered by the assertion's own canonical identity, NOT by timestamp value
    and NOT by provider order.

    The two recorded times are deliberately in DESCENDING value order relative
    to the object_versions they retract, so an implementation that sorted the
    datetimes - or that echoed provider order - would produce a different tuple.
    """

    later = RECORDED_AT.replace(hour=14)
    earlier = RECORDED_AT.replace(hour=13)
    materials = _authority_with_retractions(
        (
            retraction("r1", V1, retracted_at=later),
            retraction("r2", "0002", retracted_at=earlier),
        ),
        (
            version(V1, T0, payload=authority_payload()),
            version("0002", T1, payload=authority_payload()),
            version("0003", T2, payload=authority_payload()),
        ),
    )

    expected = (later, earlier)
    baseline = run(materials, as_of=T3)
    assert baseline.outcome == OUTCOME_ALLOW
    assert _authority_evidence(baseline).recorded_retracted_at_of_participating_assertions == (
        expected
    )

    for order in (ORDER_REVERSED, ORDER_SHUFFLED):
        for seed in range(4):
            shuffled = run(materials, as_of=T3, order=order, seed=seed)
            assert (
                _authority_evidence(shuffled).recorded_retracted_at_of_participating_assertions
                == expected
            )


@covers("NS-EV-07")
def test_captured_retraction_evidence_survives_later_publication_and_correction() -> None:
    """A captured result is immutable, and its retraction evidence stays
    byte-stable while the configuration moves on (16.5 durability)."""

    before = run(
        _authority_with_retractions(
            (retraction("r1", V1),),
            (
                version(V1, T0, payload=authority_payload()),
                version("0002", T1, payload=authority_payload()),
            ),
        ),
        as_of=T2,
    )
    captured = _authority_evidence(before).recorded_retracted_at_of_participating_assertions
    captured_serialized = serialize_result(before)
    assert captured == (RECORDED_AT,)

    # Publish further versions, another retraction and a valid correction.
    corrected_later = RECORDED_AT.replace(hour=15)
    run(
        _authority_with_retractions(
            (retraction("r1", V1), retraction("r2", "0002")),
            (
                version(V1, T0, payload=authority_payload()),
                version("0002", T1, payload=authority_payload()),
                version(
                    "0003",
                    T1,
                    payload=authority_payload(),
                    corrects_object_version="0002",
                    published_at=corrected_later,
                ),
            ),
        ),
        as_of=T2,
    )

    # The previously captured result object is unchanged.
    assert _authority_evidence(before).recorded_retracted_at_of_participating_assertions == captured
    assert serialize_result(before) == captured_serialized


def test_an_invalid_retraction_never_reaches_successful_evidence() -> None:
    """It fails the resolution closed instead, so no evidence collection can
    ever carry the recorded time of an assertion that was not validated."""

    result = run(
        _authority_with_retractions(
            (retraction("r1", V1), retraction("r2", V1)),
            (
                version(V1, T0, payload=authority_payload()),
                version("0002", T1, payload=authority_payload()),
            ),
        ),
        as_of=T2,
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.qualifying_paths == ()
    assert result.complete_nonqualifying_paths == ()


# ===========================================================================
# C1-3B  COMPLETE HR SNAPSHOT EVIDENCE
# ===========================================================================
# The path evidence retained only the employment snapshot. It must account for
# EVERY canonical HR/reference state actually relied upon by the decision - not
# merely the freshest or the oldest, and with nothing silently omitted.

_ACTOR_SNAPSHOT = T2.replace(hour=1)
_EMPLOYMENT_SNAPSHOT = T2.replace(hour=2)
_POSITION_SNAPSHOT = T2.replace(hour=3)
_INCUMBENCY_SNAPSHOT = T2.replace(hour=4)
_BRANCH_SNAPSHOT = T2.replace(hour=5)
_DIVISION_SNAPSHOT = T2.replace(hour=6)
# The TERMINATING ancestor of the ANCESTRY operand. It is now canonically
# resolved rather than accepted on the subordinate unit's declared parent
# identifier (correction C2-1), so it is genuinely relied upon and must be
# accounted for like every other hop. It carries its own distinct value here
# so that omitting it again could not hide behind another unit's snapshot.
_ROOT_SNAPSHOT = T2.replace(hour=7)


def _distinct_snapshot_world():
    """A position-based assignment under an ANCESTRY-scoped rule, so all five
    kinds of HR state are relied upon in one path."""

    return world(
        rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_ROOT),
        assignment=assignment_material(person_id=None, position_id=POSITION_ID),
    )


def _distinct_snapshot_ports():
    return (
        ReferenceActorPersonProvider(snapshot_at=_ACTOR_SNAPSHOT),
        ReferenceHrProvider(
            snapshot_at=_EMPLOYMENT_SNAPSHOT,
            position_snapshot_at=_POSITION_SNAPSHOT,
            incumbency_snapshot_at=_INCUMBENCY_SNAPSHOT,
            org_unit_snapshots={
                ORG_BRANCH: _BRANCH_SNAPSHOT,
                ORG_DIVISION: _DIVISION_SNAPSHOT,
                ORG_ROOT: _ROOT_SNAPSHOT,
            },
        ),
    )


@covers("NS-EV-01")
def test_path_evidence_accounts_for_every_hr_state_actually_relied_upon() -> None:
    """Actor/person, employment, Position, Incumbency and EVERY Organisation
    Unit ancestry hop - each with a distinct snapshot value, so an omitted one
    is visible rather than hidden behind a duplicate."""

    actor_port, hr_port = _distinct_snapshot_ports()
    result = run(
        _distinct_snapshot_world(),
        business_context=BusinessContext(
            scope_type=SCOPE_KIND_ORG_UNIT, scope_id=ORG_BRANCH
        ),
        actor_person_port=actor_port,
        hr_reference_port=hr_port,
    )

    assert result.outcome == OUTCOME_ALLOW
    hr_evidence = result.qualifying_paths[0].hr_evidence

    assert hr_evidence.canonical_snapshot_at_values == (
        _ACTOR_SNAPSHOT,
        _EMPLOYMENT_SNAPSHOT,
        _POSITION_SNAPSHOT,
        _INCUMBENCY_SNAPSHOT,
        _BRANCH_SNAPSHOT,
        _DIVISION_SNAPSHOT,
        _ROOT_SNAPSHOT,
    )
    # Neither the freshest nor the oldest alone.
    assert len(hr_evidence.canonical_snapshot_at_values) == 7

    # The canonical identities behind those snapshots are retained too - all
    # THREE organisation units, including the terminating ancestor the grant
    # actually rested on (correction C2-1).
    assert hr_evidence.position_version_id == f"position-version-{POSITION_ID}"
    assert hr_evidence.incumbency_id == f"incumbency-{POSITION_ID}"
    assert hr_evidence.org_unit_version_ids == (
        f"org-version-{ORG_BRANCH}",
        f"org-version-{ORG_DIVISION}",
        f"org-version-{ORG_ROOT}",
    )


@covers("NS-EV-05")
def test_hr_snapshot_evidence_is_deterministic_under_shuffled_provider_output() -> None:
    context = BusinessContext(scope_type=SCOPE_KIND_ORG_UNIT, scope_id=ORG_BRANCH)

    def resolve(order, seed):
        actor_port, hr_port = _distinct_snapshot_ports()
        return run(
            _distinct_snapshot_world(),
            business_context=context,
            actor_person_port=actor_port,
            hr_reference_port=hr_port,
            order=order,
            seed=seed,
        )

    baseline = serialize_result(resolve("contract", 0))
    assert serialize_result(resolve(ORDER_REVERSED, 0)) == baseline
    for seed in range(4):
        assert serialize_result(resolve(ORDER_SHUFFLED, seed)) == baseline


@covers("NS-EV-01")
def test_a_person_based_path_records_exactly_the_two_states_it_relied_upon() -> None:
    """No fabricated position or incumbency value where no position path was
    taken, and no silent omission of the two that were used."""

    actor_port = ReferenceActorPersonProvider(snapshot_at=_ACTOR_SNAPSHOT)
    hr_port = ReferenceHrProvider(snapshot_at=_EMPLOYMENT_SNAPSHOT)
    result = run(world(), actor_person_port=actor_port, hr_reference_port=hr_port)

    hr_evidence = result.qualifying_paths[0].hr_evidence
    assert hr_evidence.canonical_snapshot_at_values == (
        _ACTOR_SNAPSHOT,
        _EMPLOYMENT_SNAPSHOT,
    )
    assert hr_evidence.position_version_id is None
    assert hr_evidence.incumbency_id is None
    assert hr_evidence.org_unit_version_ids == ()


@covers("NS-EV-06")
def test_the_completed_hr_evidence_still_exposes_no_provider_specific_identifier() -> None:
    """Completing the evidence must not have leaked provider detail across the
    canonical boundary (section 7)."""

    actor_port, hr_port = _distinct_snapshot_ports()
    result = run(
        _distinct_snapshot_world(),
        business_context=BusinessContext(
            scope_type=SCOPE_KIND_ORG_UNIT, scope_id=ORG_BRANCH
        ),
        actor_person_port=actor_port,
        hr_reference_port=hr_port,
    )
    serialized = serialize_result(result).lower()
    for forbidden in _FORBIDDEN_IN_EVIDENCE:
        assert forbidden not in serialized, forbidden
