"""PF-1A-E2-A section 18: MIXED PATHS AND AGGREGATION, and TOTAL FAIL-CLOSED
DEFECT ORDER.

Covers non-store scenarios NS-AG-01 to NS-AG-05 and NS-DO-01 to NS-DO-05.

WHY THESE ARE NOT CLASS A (F-10.3b). NS-AG-03, NS-AG-04 and every NS-DO
scenario COMPOSE a malformed stored object, and that object is separately a
class A fixture with its own storability, reason-code and parity obligations.
What these scenarios are ABOUT is the AGGREGATION PRECEDENCE and RELEVANCE
rules of 15.2/15.3 and the TOTAL ORDER of 15.5 - that a valid path never
rescues relevant corruption, that irrelevance must be decidable from identity
alone, and that the database is never what decides which defect is reported.
Seeding a row does not discharge them.
"""

from __future__ import annotations

from app.modules.authorization.business_authority.contract import (
    ASSIGNMENT_NOT_EFFECTIVE,
    AUTHORITY_LINEAGE_CONTRADICTORY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_RULE,
    EVALUATOR_CONDITION_NOT_SATISFIED,
    EVALUATOR_NUMERIC_BAND,
    NO_CANDIDATE_ASSIGNMENT,
    NO_QUALIFYING_PATH,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    PUBLICATION_PROVENANCE_INVALID,
    REASON_CODE_RANK,
    RULE_SCOPE_NOT_MATCHED,
    SCOPE_EXACT,
    STAGE_S4_RULES,
    STATUS_FAIL_CLOSED,
    STATUS_RESOLVED,
)
from app.modules.authorization.business_authority.defects import (
    DefectRecord,
    object_subject,
    order_defects,
)
from app.modules.authorization.business_authority.domain import BusinessContext
from app.modules.authorization.business_authority.evidence import serialize_result
from app.modules.authorization.business_authority.scope import SCOPE_KIND_ORG_UNIT
from tests.fixtures.pf_1a_e2_a_corpus import covers
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    ORDER_REVERSED,
    ORDER_SHUFFLED,
    ORG_BRANCH,
    ORG_DIVISION,
    ORG_ROOT,
    POSITION_ID,
    T0,
    T1,
    T2,
    T3,
    authority_payload,
    rule_payload,
    version,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    AUTHORITY_ID,
    V1,
    V2,
    assignment_material,
    authority_material,
    role_material,
    rule_material,
    run,
    world,
)

ROLE_A, ROLE_B = "role-a", "role-b"
RULE_A, RULE_B = "rule-a", "rule-b"
ASSIGNMENT_A, ASSIGNMENT_B = "assignment-a", "assignment-b"


def _two_path_world(*, rule_b_overrides=None, assignment_b_overrides=None, extra=()):
    """Two INDEPENDENT complete paths to one authority.

    Path A is person-based; path B is position-based, so the two are genuinely
    different grants rather than one path counted twice (15.1).
    """

    rule_b_overrides = rule_b_overrides or {}
    assignment_b_overrides = assignment_b_overrides or {}
    return [
        authority_material(),
        role_material(object_id=ROLE_A),
        role_material(object_id=ROLE_B),
        rule_material(object_id=RULE_A, role_id=ROLE_A),
        rule_material(object_id=RULE_B, role_id=ROLE_B, **rule_b_overrides),
        assignment_material(object_id=ASSIGNMENT_A, role_id=ROLE_A),
        assignment_material(
            object_id=ASSIGNMENT_B,
            role_id=ROLE_B,
            person_id=None,
            position_id=POSITION_ID,
            **assignment_b_overrides,
        ),
        *extra,
    ]


def _context(scope_id=None, **facts) -> BusinessContext:
    return BusinessContext(
        scope_type=SCOPE_KIND_ORG_UNIT if scope_id else None,
        scope_id=scope_id,
        declared_facts=facts,
    )


# ===========================================================================
# NS-AG-01  MULTIPLICITY IS NOT AMBIGUITY
# ===========================================================================


@covers("NS-AG-01")
def test_two_independently_valid_qualifying_paths_are_both_retained() -> None:
    """A person may legitimately hold the same authority through more than one
    complete, valid path. This is a NORMAL, SUPPORTED outcome, not corruption
    (15.1), and it is never silently reduced to one."""

    result = run(_two_path_world())

    assert result.outcome == OUTCOME_ALLOW
    assert result.resolution_status == STATUS_RESOLVED
    assert len(result.qualifying_paths) == 2

    # Deterministic order, computed from canonical identifiers (15.4) - never
    # an arbitrary "first".
    keys = [path.path_sort_key for path in result.qualifying_paths]
    assert keys == sorted(keys)

    # Both are genuinely distinct grants.
    assert {path.business_authority_role.ref.object_id for path in result.qualifying_paths} == {
        ROLE_A,
        ROLE_B,
    }


# ===========================================================================
# NS-AG-02  a qualifying path alongside a normally-nonqualifying one
# ===========================================================================


@covers("NS-AG-02")
def test_a_nonqualifying_path_is_retained_in_full_alongside_a_qualifying_one() -> None:
    materials = _two_path_world(
        rule_b_overrides={"scope_type": SCOPE_EXACT, "scope_id": ORG_ROOT}
    )
    result = run(materials, business_context=_context(ORG_BRANCH))

    assert result.outcome == OUTCOME_ALLOW
    assert len(result.qualifying_paths) == 1
    assert len(result.complete_nonqualifying_paths) == 1

    # RETAINED IN FULL under 16.3: the same four object/version pairs as a
    # qualifying path, plus the decisive reason.
    nonqualifying = result.complete_nonqualifying_paths[0]
    assert nonqualifying.decisive_nonqualification_reason == RULE_SCOPE_NOT_MATCHED
    for pair in (
        nonqualifying.business_authority_role,
        nonqualifying.business_authority,
        nonqualifying.business_authority_rule,
        nonqualifying.business_authority_assignment,
    ):
        assert pair.ref.object_id and pair.ref.object_version


# ===========================================================================
# NS-AG-03  a valid path does NOT rescue RELEVANT corruption
# ===========================================================================


@covers("NS-AG-03")
def test_a_relevant_corrupt_object_fails_closed_despite_a_valid_qualifying_path() -> None:
    """15.3 branch 1 takes precedence over branch 2, always.

    A defect in a lineage or dependency that IS relevant to this actor +
    requested authority + candidate graph can NEVER be masked by another,
    valid path (15.2).
    """

    corrupt_rule_b = rule_material(
        object_id=RULE_B,
        versions=(
            version(V1, T0, payload=rule_payload(role_id=ROLE_B, authority_id=AUTHORITY_ID)),
            version(V2, T0, payload=rule_payload(role_id=ROLE_B, authority_id=AUTHORITY_ID)),
        ),
    )
    materials = [
        authority_material(),
        role_material(object_id=ROLE_A),
        role_material(object_id=ROLE_B),
        rule_material(object_id=RULE_A, role_id=ROLE_A),
        corrupt_rule_b,
        assignment_material(object_id=ASSIGNMENT_A, role_id=ROLE_A),
        assignment_material(object_id=ASSIGNMENT_B, role_id=ROLE_B),
    ]

    result = run(materials, as_of=T1)
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY

    # The qualifying path's established evidence is STILL RETAINED, so a reader
    # can see what was established before the defect decided the result.
    assert len(result.qualifying_paths) == 1
    assert result.qualifying_paths[0].business_authority_role.ref.object_id == ROLE_A


# ===========================================================================
# NS-AG-04  IRRELEVANCE must be decidable from IDENTITY ALONE
# ===========================================================================


@covers("NS-AG-04")
def test_a_provably_irrelevant_corrupt_object_leaves_the_result_unaffected() -> None:
    """A record is PROVABLY IRRELEVANT only when the exclusion can be
    established WITHOUT relying on any defective, ambiguous or semantically
    interpreted field. Safe exclusions are structural and identity-only, and
    are evaluated over RAW published facts exactly as discovery is (15.2).

    Here NO raw published version of the corrupt object carries the requested
    authority_code, so it is excluded by an identity-only test.
    """

    unrelated_corrupt = authority_material(
        object_id="authority-unrelated",
        versions=(
            version(V1, T0, payload=authority_payload("A_COMPLETELY_DIFFERENT_AUTHORITY")),
            version(V2, T0, payload=authority_payload("A_COMPLETELY_DIFFERENT_AUTHORITY")),
        ),
    )
    result = run(world(extra=(unrelated_corrupt,)), as_of=T1)
    assert result.outcome == OUTCOME_ALLOW


@covers("NS-AG-04")
def test_an_object_whose_irrelevance_would_depend_on_the_defective_field_fails_closed() -> None:
    """The COMPANION CASE. If the exclusion WOULD depend on the defective field
    itself, the record is NOT provably irrelevant and the resolution fails
    closed rather than guessing relevance in order to reach an ALLOW.

    This rule has two duplicate-start versions, one referencing the requested
    authority and one referencing a different one. Which is effective would
    decide whether the object is relevant at all - and that is precisely the
    defective field.
    """

    ambiguous_relevance = rule_material(
        object_id=RULE_B,
        versions=(
            version(V1, T0, payload=rule_payload(role_id=ROLE_B, authority_id=AUTHORITY_ID)),
            version(
                V2, T0, payload=rule_payload(role_id=ROLE_B, authority_id="some-other-authority")
            ),
        ),
    )
    materials = [
        authority_material(),
        role_material(object_id=ROLE_A),
        role_material(object_id=ROLE_B),
        rule_material(object_id=RULE_A, role_id=ROLE_A),
        ambiguous_relevance,
        assignment_material(object_id=ASSIGNMENT_A, role_id=ROLE_A),
    ]

    result = run(materials, as_of=T1)
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


@covers("NS-AG-04")
def test_retraction_is_never_used_as_an_irrelevance_test() -> None:
    """An object whose only reference-bearing version is retracted remains
    RELEVANT and must be validated, because the retraction assertion itself may
    be the defect. Excluding it here would reintroduce, at the KERNEL, the very
    prefiltering the provider is forbidden to do (15.2)."""

    from tests.fixtures.pf_1a_e2_a_reference_providers import retraction

    malformed = rule_material(
        object_id=RULE_B,
        versions=(version(V1, T0, payload=rule_payload(role_id=ROLE_B, authority_id=AUTHORITY_ID)),),
        retractions=(retraction("r1", V1), retraction("r2", V1)),
    )
    materials = [
        authority_material(),
        role_material(object_id=ROLE_A),
        role_material(object_id=ROLE_B),
        rule_material(object_id=RULE_A, role_id=ROLE_A),
        malformed,
        assignment_material(object_id=ASSIGNMENT_A, role_id=ROLE_A),
    ]
    result = run(materials)
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


# ===========================================================================
# NS-AG-05  the result-level reason when no path qualifies
# ===========================================================================


@covers("NS-AG-05")
def test_no_candidate_assignment_when_rules_and_roles_were_established() -> None:
    materials = [
        authority_material(),
        role_material(object_id=ROLE_A),
        rule_material(object_id=RULE_A, role_id=ROLE_A),
    ]
    result = run(materials)
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason == NO_CANDIDATE_ASSIGNMENT


@covers("NS-AG-05")
def test_a_single_shared_path_level_reason_is_promoted_to_the_result_level() -> None:
    """15.3 branch 3c - what makes a denial LEGIBLE rather than a bare
    NO_QUALIFYING_PATH."""

    materials = _two_path_world(
        rule_b_overrides={"scope_type": SCOPE_EXACT, "scope_id": ORG_ROOT},
    )
    # Both rules now name an exact scope the context does not match.
    materials[3] = rule_material(
        object_id=RULE_A, role_id=ROLE_A, scope_type=SCOPE_EXACT, scope_id=ORG_DIVISION
    )
    result = run(materials, business_context=_context(ORG_BRANCH))

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason == RULE_SCOPE_NOT_MATCHED
    assert len(result.complete_nonqualifying_paths) == 2


@covers("NS-AG-05")
def test_differing_path_level_reasons_yield_no_qualifying_path() -> None:
    band = {
        "fact": "offer_value",
        "unit": "INR",
        "lower": 10_000,
        "lower_inclusive": True,
    }
    materials = _two_path_world(
        rule_b_overrides={"evaluator_type": EVALUATOR_NUMERIC_BAND, "parameter_payload": band}
    )
    materials[3] = rule_material(
        object_id=RULE_A, role_id=ROLE_A, scope_type=SCOPE_EXACT, scope_id=ORG_ROOT
    )
    result = run(
        materials,
        business_context=_context(ORG_BRANCH, offer_value={"value": 5, "unit": "INR"}),
    )

    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason == NO_QUALIFYING_PATH
    reasons = {
        path.decisive_nonqualification_reason for path in result.complete_nonqualifying_paths
    }
    assert reasons == {RULE_SCOPE_NOT_MATCHED, EVALUATOR_CONDITION_NOT_SATISFIED}


@covers("NS-AG-05")
def test_normal_nonqualification_never_triggers_the_fail_closed_branch() -> None:
    """Inactive, ineffective within a valid gap, scope miss, parameter miss,
    absent assignment or rule - none of these is a defect (15.3)."""

    gapped = assignment_material(
        versions=(
            version(
                V1,
                T0,
                payload=assignment_material().versions[0].payload,
                declared_effective_to=T1,
            ),
            version(V2, T3, payload=assignment_material().versions[0].payload),
        )
    )
    result = run(world(assignment=gapped), as_of=T2)
    assert result.resolution_status == STATUS_RESOLVED
    assert ASSIGNMENT_NOT_EFFECTIVE in {p.reason_code for p in result.partial_evaluations}
    assert result.ordered_defects == ()


# ===========================================================================
# NS-DO-01  SAME STAGE, TWO DIFFERENT DEFECTS
# ===========================================================================


def _two_defective_rules(*, provenance_on: str, contradiction_on: str):
    """One rule with invalid provenance and one with a lineage contradiction,
    both detected at stage S4."""

    provenance_rule = rule_material(
        object_id=provenance_on,
        versions=(
            version(
                V1,
                T0,
                payload=rule_payload(role_id=ROLE_A, authority_id=AUTHORITY_ID),
                published_at=None,
            ),
        ),
    )
    contradiction_rule = rule_material(
        object_id=contradiction_on,
        versions=(
            version(V1, T0, payload=rule_payload(role_id=ROLE_B, authority_id=AUTHORITY_ID)),
            version(V2, T0, payload=rule_payload(role_id=ROLE_B, authority_id=AUTHORITY_ID)),
        ),
    )
    return [
        authority_material(),
        role_material(object_id=ROLE_A),
        role_material(object_id=ROLE_B),
        provenance_rule,
        contradiction_rule,
    ]


@covers("NS-DO-01")
def test_two_different_defects_at_one_stage_are_ordered_by_the_canonical_subject_key() -> None:
    """The reported reason is the one the 15.5 TOTAL ORDER selects, and it is
    the same in every run.

    Both defects sit at stage S4, so `stage_rank` cannot separate them and the
    CANONICAL SUBJECT KEY decides. Swapping which rule carries which defect
    flips the reported reason - which is the proof that the subject key, not
    provider order and not the reason rank, is what ranks second.
    """

    first = run(_two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B), as_of=T1)
    assert first.resolution_status == STATUS_FAIL_CLOSED
    assert first.result_level_reason == PUBLICATION_PROVENANCE_INVALID
    assert first.ordered_defects[0].stage == STAGE_S4_RULES

    swapped = run(_two_defective_rules(provenance_on=RULE_B, contradiction_on=RULE_A), as_of=T1)
    assert swapped.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY

    # Stable across repeated runs.
    for _ in range(5):
        assert (
            run(_two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B), as_of=T1)
            .result_level_reason
            == PUBLICATION_PROVENANCE_INVALID
        )


# ===========================================================================
# NS-DO-02  SAME SUBJECT, TWO REASON CODES
# ===========================================================================


@covers("NS-DO-02")
def test_one_subject_carrying_two_reason_codes_is_decided_by_reason_code_rank() -> None:
    """When stage_rank AND canonical_subject_key are equal, the third
    component - the explicit, closed reason_code_rank table - decides,
    deterministically."""

    both_defects = authority_material(
        versions=(
            version(
                V1,
                T1,
                payload=authority_payload(),
                declared_effective_to=T0,  # nonsensical interval
                published_at=None,  # and absent provenance
            ),
        )
    )
    result = run(world(authority=both_defects), as_of=T2)

    assert result.resolution_status == STATUS_FAIL_CLOSED
    reported = {defect.reason_code for defect in result.ordered_defects}
    assert {AUTHORITY_LINEAGE_CONTRADICTORY, PUBLICATION_PROVENANCE_INVALID} <= reported

    # AUTHORITY_LINEAGE_CONTRADICTORY carries the lower declared rank.
    assert (
        REASON_CODE_RANK[AUTHORITY_LINEAGE_CONTRADICTORY]
        < REASON_CODE_RANK[PUBLICATION_PROVENANCE_INVALID]
    )
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


# ===========================================================================
# NS-DO-03  ACROSS FAMILIES AT ONE STAGE
# ===========================================================================


@covers("NS-DO-03")
def test_defects_across_families_at_one_stage_order_by_object_family_rank() -> None:
    """Ordering is by `object_family_rank`, NEVER by discovery order.

    This kernel detects each family's lineage defects at that family's own
    stage (S3 authority, S4 rule, S5 role, S6 assignment), so a same-stage
    cross-family collision cannot be composed through the ports. The property
    the scenario is about is the TOTAL ORDER itself, so it is proved directly
    against the canonical defect sort key, with defect records constructed at
    one stage across all four families.
    """

    families = (
        "BUSINESS_AUTHORITY",
        "BUSINESS_AUTHORITY_ROLE",
        BUSINESS_AUTHORITY_RULE,
        BUSINESS_AUTHORITY_ASSIGNMENT,
    )
    # Deliberately built in REVERSE family order, and given object ids whose
    # own ordering contradicts the family ranking, so a sort that fell back to
    # insertion order or to the identifier alone would fail here.
    defects = tuple(
        DefectRecord(
            reason_code=AUTHORITY_LINEAGE_CONTRADICTORY,
            stage=STAGE_S4_RULES,
            subject=object_subject(family, f"object-{index}"),
            detail="constructed",
        )
        for index, family in reversed(list(enumerate(families)))
    )

    ordered = order_defects(defects)
    assert [defect.subject.components[0] for defect in ordered] == ["00", "01", "02", "03"]


@covers("NS-DO-03")
def test_defects_in_different_families_order_by_stage_first() -> None:
    """The end-to-end complement: an authority defect (S3) outranks a rule
    defect (S4) because `stage_rank` is the FIRST component of the key."""

    materials = _two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B)
    materials[0] = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T0, payload=authority_payload()),
        )
    )
    result = run(materials, as_of=T1)
    assert result.ordered_defects[0].stage == "S3"
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


# ===========================================================================
# NS-DO-04  order, traversal and repetition must change NOTHING
# ===========================================================================


@covers("NS-DO-04")
def test_shuffled_provider_order_reversed_order_and_repeated_runs_are_byte_identical() -> None:
    """Provider order, SQL row order, dictionary/set iteration order, path
    traversal direction and concurrency MUST NOT affect the result (15.4,
    15.5).

    Reversing the provider's return order is the observable form of reversing
    traversal here: it reverses the order in which candidates and versions
    reach the kernel, which is the only traversal freedom the kernel has.
    """

    materials = _two_path_world()
    baseline = serialize_result(run(materials))

    assert serialize_result(run(materials, order=ORDER_REVERSED)) == baseline
    for seed in range(6):
        assert serialize_result(run(materials, order=ORDER_SHUFFLED, seed=seed)) == baseline

    # Repeated runs: no set/dict iteration, address, hash-seed or clock
    # dependence anywhere in the output.
    for _ in range(5):
        assert serialize_result(run(materials)) == baseline


@covers("NS-DO-04")
def test_ordering_is_stable_for_a_multi_defect_state_too() -> None:
    materials = _two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B)
    baseline = serialize_result(run(materials, as_of=T1))

    assert serialize_result(run(materials, order=ORDER_REVERSED, as_of=T1)) == baseline
    for seed in range(4):
        assert serialize_result(run(materials, order=ORDER_SHUFFLED, seed=seed, as_of=T1)) == (
            baseline
        )


# ===========================================================================
# NS-DO-05  ONE ORDER ONLY
# ===========================================================================


@covers("NS-DO-05")
def test_the_first_ordered_partial_evaluation_always_carries_the_result_level_reason() -> None:
    """There is deliberately only ONE order, so the first item of the ordered
    partial/failed collection and `result_level_reason` can never disagree
    about which defect is first (16.5)."""

    multi_defect_states = (
        _two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B),
        _two_defective_rules(provenance_on=RULE_B, contradiction_on=RULE_A),
        world(
            authority=authority_material(
                versions=(
                    version(
                        V1,
                        T1,
                        payload=authority_payload(),
                        declared_effective_to=T0,
                        published_at=None,
                    ),
                )
            )
        ),
    )

    for materials in multi_defect_states:
        result = run(materials, as_of=T1)
        assert result.resolution_status == STATUS_FAIL_CLOSED
        assert result.partial_evaluations
        assert result.partial_evaluations[0].reason_code == result.result_level_reason
        assert result.ordered_defects[0].reason_code == result.result_level_reason
