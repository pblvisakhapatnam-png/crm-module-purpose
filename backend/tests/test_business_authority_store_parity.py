"""PF-1A-E2-B section 9: the CENTRAL PARITY PROOF, and DEFECT VISIBILITY.

ONE declarative scenario is driven through TWO compositions - the E2-A
reference provider and the E2-B PostgreSQL provider, each with THE SAME
synthetic actor and HR providers - and the two must agree on outcome,
resolution_status, result_level_reason, all three evidence collections WITH
their ordering, and the established_state header. The comparison is the
canonical serialized result, not a hand-picked subset: a weakened comparison
is how a parity corpus passes while hiding a real divergence.

THE CORPUS HAS EXACTLY THREE PARTS (section 9), and conflating them is the
F-10.3a defect:

    CLASS A     14   varies the MALFORMED stored state.
    V-01..V-12  12   varies the VALID stored state. NO class label; these are
                     not negative fixtures, and calling one "class A" would
                     attach a negative label to a state that is not a defect.
    NON-STORE   38   varies a provider, request, clock, orchestration or
                     evidence condition while BOTH compositions use the same
                     synthetic actor/HR providers.
                                                                  = 64 total

No class B1 or B2 fixture appears here, because no conforming implementation
of this schema can return a row the schema forbids storing; their coverage is
the structural-rejection tests plus E2-A's own direct tests at the boundaries
section 5.7 names. That exclusion is verification PLACEMENT, never a semantic
exemption.

WHERE THIS CORPUS DEPARTS FROM THE E2-A TEST BODIES, AND WHY. Several E2-A
scenarios are driven by class B1 shapes - an absent `published_at`, an
`end <= start` interval - which PostgreSQL rejects at write time. Those
scenarios are rebuilt here from CLASS A shapes carrying the same reason code,
exactly as section 5.7A requires of NS-DO-01..05. No constraint is disabled,
deferred or dropped to seed anything: a "pass" obtained that way would say
nothing about the shipped schema.
"""

from __future__ import annotations

import json

from app.modules.authorization.business_authority.contract import (
    ASSIGNMENT_NOT_ACTIVE,
    ASSIGNMENT_NOT_EFFECTIVE,
    ASSIGNMENT_SCOPE_NOT_MATCHED,
    AUTHORITY_CODE_NOT_CONFIGURED,
    AUTHORITY_CONFIGURATION_UNAVAILABLE,
    AUTHORITY_LINEAGE_CONTRADICTORY,
    AUTHORITY_NOT_ACTIVE,
    AUTHORITY_REFERENCE_DANGLING,
    BUSINESS_AUTHORITY,
    EVALUATOR_CONDITION_NOT_SATISFIED,
    EVALUATOR_EXACT_VALUE_SET,
    EVALUATOR_FACTS_INVALID,
    EVALUATOR_NONE,
    EVALUATOR_NUMERIC_BAND,
    EVALUATOR_PAYLOAD_INVALID,
    EVALUATOR_PERCENTAGE_BAND,
    EVALUATOR_UNKNOWN,
    NO_CANDIDATE_ASSIGNMENT,
    NO_QUALIFYING_PATH,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    PUBLICATION_PROVENANCE_INVALID,
    ROLE_NOT_ACTIVE,
    ROLE_NOT_EFFECTIVE,
    RULE_NOT_ACTIVE,
    RULE_NOT_EFFECTIVE,
    RULE_SCOPE_NOT_MATCHED,
    SCOPE_ANCESTRY,
    SCOPE_COMPOSITION_NOT_SATISFIED,
    SCOPE_CONTEXT_MISSING,
    SCOPE_EXACT,
    SCOPE_GLOBAL,
    SCOPE_SEMANTICS_UNSUPPORTED,
    STATUS_FAIL_CLOSED,
    STATUS_RESOLVED,
)
from app.modules.authorization.business_authority.domain import BusinessContext
from app.modules.authorization.business_authority.evidence import serialize_result
from app.modules.authorization.business_authority.scope import SCOPE_KIND_ORG_UNIT
from sqlalchemy import text

from tests.fixtures.pf_1a_e2_a_reference_providers import (
    ACTOR_ID,
    AUTHORITY_CODE,
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
    TICK,
    ReferenceActorPersonProvider,
    ReferenceAuthorityConfigurationProvider,
    ReferenceHrProvider,
    assignment_payload,
    authority_payload,
    retraction,
    role_payload,
    rule_payload,
    version,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    ASSIGNMENT_ID,
    AUTHORITY_ID,
    ROLE_ID,
    RULE_ID,
    V1,
    V2,
    assignment_material,
    authority_material,
    role_material,
    rule_material,
    world,
)
from tests.fixtures.pf_1a_e2_b_corpus import store_covers
from tests.fixtures.pf_1a_e2_b_store import (  # noqa: F401  (store_db is a fixture)
    assert_parity,
    clear_store,
    run_through_postgres,
    run_through_reference,
    seed_materials,
    store_db,
)

OTHER_CODE = "SOME_OTHER_AUTHORITY"
V3 = "0003"

ROLE_A, ROLE_B = "role-a", "role-b"
RULE_A, RULE_B = "rule-a", "rule-b"
ASSIGNMENT_A, ASSIGNMENT_B = "assignment-a", "assignment-b"

EARLIER = RECORDED_AT.replace(hour=11)
LATER = RECORDED_AT.replace(hour=14)


def _context(scope_id=None, **facts) -> BusinessContext:
    return BusinessContext(
        scope_type=SCOPE_KIND_ORG_UNIT if scope_id else None,
        scope_id=scope_id,
        declared_facts=facts,
    )


def _partial_reasons(result) -> set[str]:
    return {partial.reason_code for partial in result.partial_evaluations}


def _decisive_reasons(result) -> set[str]:
    return {path.decisive_nonqualification_reason for path in result.complete_nonqualifying_paths}


def _resolved_authority_version(result) -> str | None:
    reference = result.established_state.requested_authority
    return reference.object_version if reference is not None else None


def _gapped(payload_factory, family_material):
    """V1 [T0, T1), V2 from T3 - a valid gap covering T2."""

    return family_material(
        versions=(
            version(V1, T0, payload=payload_factory(), declared_effective_to=T1),
            version(V2, T3, payload=payload_factory()),
        )
    )


def _position_world():
    return world(assignment=assignment_material(person_id=None, position_id=POSITION_ID))


def _two_path_world(*, rule_b_overrides=None, assignment_b_overrides=None, extra=()):
    """Two INDEPENDENT complete paths to one authority: one person-based, one
    position-based, so they are genuinely different grants."""

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


# ===========================================================================
# CLASS A - DEFECT VISIBILITY plus FULL PARITY (fourteen fixtures)
# ===========================================================================
# Each seeds the malformed state in PostgreSQL, resolves through the WIRED
# kernel, and asserts BOTH that the expected fail-closed code is produced and
# that the PostgreSQL and reference resolutions are byte-identical.


@store_covers("A-01", parity=True)
def test_a01_contradictory_explicit_overlap(store_db) -> None:
    """The direct probe for attack surface 12a and 17a.

    Under the rejected `min(declared_effective_to, next_start)` formula, the
    T1 instant would fall inside a normalised V1 [T0, T2) and resolve cleanly.
    It must fail closed instead - on both providers, from the same stored rows.
    """

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(), declared_effective_to=T3),
            version(V2, T2, payload=authority_payload()),
        )
    )

    at_overlap = assert_parity(store_db, world(authority=authority), as_of=T2)
    assert at_overlap.resolution_status == STATUS_FAIL_CLOSED
    assert at_overlap.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY

    inside_would_be_truncation = assert_parity(store_db, world(authority=authority), as_of=T1)
    assert inside_would_be_truncation.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY
    assert _resolved_authority_version(inside_would_be_truncation) is None


@store_covers("A-02", parity=True)
def test_a02_duplicate_temporal_start(store_db) -> None:
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T0, payload=authority_payload()),
        )
    )
    result = assert_parity(store_db, world(authority=authority), as_of=T1)
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY
    assert _resolved_authority_version(result) is None


@store_covers("A-04", parity=True)
def test_a04_dangling_retraction(store_db) -> None:
    authority = authority_material(
        versions=(version(V1, T0, payload=authority_payload()),),
        retractions=(retraction("r1", "9999"),),
    )
    result = assert_parity(store_db, world(authority=authority))
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


@store_covers("A-05", parity=True)
def test_a05_duplicated_retraction(store_db) -> None:
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T2, payload=authority_payload()),
        ),
        retractions=(retraction("r1", V1), retraction("r2", V1)),
    )
    result = assert_parity(store_db, world(authority=authority))
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


@store_covers("A-06", parity=True)
def test_a06_correction_target_exists_but_is_not_retracted(store_db) -> None:
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T2, payload=authority_payload(), corrects_object_version=V1),
        )
    )
    result = assert_parity(store_db, world(authority=authority))
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


@store_covers("A-07", parity=True)
def test_a07_correction_target_does_not_exist(store_db) -> None:
    authority = authority_material(
        versions=(version(V2, T2, payload=authority_payload(), corrects_object_version="9999"),)
    )
    result = assert_parity(store_db, world(authority=authority))
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


@store_covers("A-08", parity=True)
def test_a08_retraction_recorded_before_its_target_was_published(store_db) -> None:
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T2, payload=authority_payload()),
        ),
        retractions=(retraction("r1", V1, retracted_at=EARLIER),),
    )
    result = assert_parity(store_db, world(authority=authority))
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID


@store_covers("A-09", parity=True)
def test_a09_correction_recorded_before_its_target_was_retracted(store_db) -> None:
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
        retractions=(retraction("r1", V1, retracted_at=LATER),),
    )
    result = assert_parity(store_db, world(authority=authority))
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID


@store_covers("A-10", parity=True)
def test_a10_published_at_decreasing_across_increasing_object_version(store_db) -> None:
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(), published_at=RECORDED_AT),
            version(V2, T2, payload=authority_payload(), published_at=EARLIER),
        )
    )
    result = assert_parity(store_db, world(authority=authority))
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID


@store_covers("A-11", parity=True)
def test_a11_reference_to_a_stable_identity_carrying_no_material(store_db) -> None:
    """The state the store's missing-parent foreign key would otherwise have
    swallowed, which is exactly why that key is class B2 and this is class A.

    In PostgreSQL the referenced stable identity ROW exists and has NO version
    rows; the reference provider simply holds nothing for the same id. Both
    decode to COMPLETE material with an empty `versions[]` (9.3.2), and both
    must therefore produce AUTHORITY_REFERENCE_DANGLING.
    """

    materials = [
        authority_material(),
        role_material(),
        rule_material(role_id="role-that-was-never-published"),
        assignment_material(),
    ]
    result = assert_parity(store_db, materials)
    assert result.result_level_reason == AUTHORITY_REFERENCE_DANGLING
    # DANGLING is distinct from a GAP: a gap has material but no effective
    # version, and is ordinary nonqualification (11.5).
    assert result.result_level_reason != ROLE_NOT_EFFECTIVE


@store_covers("A-13", parity=True)
def test_a13_unknown_stored_evaluator_type(store_db) -> None:
    for near_miss in ("SOME_FUTURE_EVALUATOR", "NUMERIC", "numeric_band", ""):
        result = assert_parity(
            store_db,
            world(rule=rule_material(evaluator_type=near_miss)),
            business_context=_context(ORG_BRANCH),
        )
        assert result.result_level_reason == EVALUATOR_UNKNOWN, near_miss


_INR_BAND = {
    "fact": "offer_value",
    "unit": "INR",
    "lower": 100,
    "lower_inclusive": True,
    "upper": 1000,
    "upper_inclusive": False,
}


def _band_world(payload=None, evaluator_type: str = EVALUATOR_NUMERIC_BAND):
    return world(
        rule=rule_material(
            evaluator_type=evaluator_type,
            parameter_payload=_INR_BAND if payload is None else payload,
        )
    )


@store_covers("A-14", parity=True)
def test_a14_malformed_stored_evaluator_payload(store_db) -> None:
    """Payload validation is authoritative at EVALUATION time, in the kernel,
    regardless of what any store accepted at write time (section 13)."""

    malformed_payloads = (
        {"fact": "offer_value", "unit": "INR", "lower": 100},  # no inclusivity flag
        {"fact": "offer_value", "lower": 100, "lower_inclusive": True},  # no explicit unit
        {"unit": "INR", "lower": 100, "lower_inclusive": True},  # names no fact
        {"fact": "offer_value", "unit": "INR"},  # neither bound
        "not-an-object",
    )
    for payload in malformed_payloads:
        result = assert_parity(
            store_db,
            _band_world(payload),
            business_context=_context(ORG_BRANCH, offer_value={"value": 500, "unit": "INR"}),
        )
        assert result.result_level_reason == EVALUATOR_PAYLOAD_INVALID, payload

    none_with_payload = assert_parity(
        store_db,
        world(rule=rule_material(evaluator_type=EVALUATOR_NONE, parameter_payload={"fact": "x"})),
        business_context=_context(ORG_BRANCH),
    )
    assert none_with_payload.result_level_reason == EVALUATOR_PAYLOAD_INVALID


@store_covers("A-15", parity=True)
def test_a15_unsupported_stored_scope_type(store_db) -> None:
    result = assert_parity(
        store_db,
        world(rule=rule_material(scope_type="REGION_TREE", scope_id=ORG_BRANCH)),
        business_context=_context(ORG_BRANCH),
    )
    assert result.outcome == OUTCOME_DENY
    assert result.result_level_reason == SCOPE_SEMANTICS_UNSUPPORTED


@store_covers("A-17", parity=True)
def test_a17_a_malformed_retraction_cannot_hide_the_only_bearing_version(store_db) -> None:
    """THE HIGHEST-VALUE REGRESSION TEST IN THIS PACKAGE.

    A dangling, duplicated or impossibly-provenanced retraction targeting the
    ONLY requested-code-bearing version - and, as a companion, the ONLY
    reference-bearing version of a candidate Assignment - must fail closed on
    THAT DEFECT'S OWN reason code. Never AUTHORITY_CODE_NOT_CONFIGURED, never
    NO_CANDIDATE_ASSIGNMENT, and never an empty candidate set: those are
    exactly what a retraction-excluding EXISTS in discovery would have
    produced.
    """

    shapes = {
        "dangling": ((retraction("r1", "9999"),), AUTHORITY_LINEAGE_CONTRADICTORY),
        "duplicated": ((retraction("r1", V1), retraction("r2", V1)), AUTHORITY_LINEAGE_CONTRADICTORY),
        "impossible provenance": (
            (retraction("r1", V1, retracted_at=EARLIER),),
            PUBLICATION_PROVENANCE_INVALID,
        ),
    }

    for label, (retractions, expected) in shapes.items():
        authority = authority_material(
            versions=(version(V1, T0, payload=authority_payload(AUTHORITY_CODE)),),
            retractions=retractions,
        )
        result = assert_parity(store_db, world(authority=authority), as_of=T2)
        assert result.resolution_status == STATUS_FAIL_CLOSED, label
        assert result.result_level_reason == expected, label
        assert result.result_level_reason != AUTHORITY_CODE_NOT_CONFIGURED, label
        assert result.result_level_reason != NO_CANDIDATE_ASSIGNMENT, label

    # The companion case, over an Assignment discovered by STABLE REFERENCE.
    assignment = assignment_material(
        versions=(version(V1, T0, payload=assignment_payload(role_id=ROLE_ID)),),
        retractions=(retraction("r1", V1), retraction("r2", V1)),
    )
    companion = assert_parity(store_db, world(assignment=assignment), as_of=T2)
    assert companion.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY
    assert companion.result_level_reason != NO_CANDIDATE_ASSIGNMENT


# ===========================================================================
# VALID-SHAPE PARITY SCENARIOS  V-01 to V-12
# ===========================================================================
# Their subject IS authority-store state, and that state is entirely VALID.
# They carry NO class label - describing one as "class A" is the F-10.3a
# defect - and they are equally owed parity, because misclassifying a valid
# shape is the mirror image of misclassifying a contradiction.


@store_covers("V-01", parity=True)
def test_v01_null_end_successor_closure(store_db) -> None:
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T2, payload=authority_payload()),
        )
    )
    before = assert_parity(store_db, world(authority=authority), as_of=T1)
    assert before.outcome == OUTCOME_ALLOW
    assert _resolved_authority_version(before) == V1

    at_and_after = assert_parity(store_db, world(authority=authority), as_of=T2)
    assert _resolved_authority_version(at_and_after) == V2
    # The closure is DERIVED: V1's published row still declares no end.
    assert authority.versions[0].declared_effective_to is None


@store_covers("V-02", parity=True)
def test_v02_explicit_adjacency(store_db) -> None:
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(), declared_effective_to=T2),
            version(V2, T2, payload=authority_payload()),
        )
    )
    assert _resolved_authority_version(
        assert_parity(store_db, world(authority=authority), as_of=T2 - TICK)
    ) == V1
    assert _resolved_authority_version(
        assert_parity(store_db, world(authority=authority), as_of=T2)
    ) == V2


@store_covers("V-03", parity=True)
def test_v03_a_declared_end_before_the_successor_is_a_valid_gap(store_db) -> None:
    """A gap is VALID history, never corruption, and is never reported as
    overlap or as a dangling reference. The three families that describe an
    ABSENT GRANT produce ordinary nonqualification with their own reason."""

    authority = _gapped(authority_payload, authority_material)
    inside = assert_parity(store_db, world(authority=authority), as_of=T2)
    assert inside.resolution_status == STATUS_FAIL_CLOSED
    assert inside.result_level_reason == AUTHORITY_CODE_NOT_CONFIGURED
    assert _resolved_authority_version(
        assert_parity(store_db, world(authority=authority), as_of=T1 - TICK)
    ) == V1

    gapped_assignment = assignment_material(
        versions=(
            version(V1, T0, payload=assignment_payload(), declared_effective_to=T1),
            version(V2, T3, payload=assignment_payload()),
        )
    )
    result = assert_parity(store_db, world(assignment=gapped_assignment), as_of=T2)
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert ASSIGNMENT_NOT_EFFECTIVE in _partial_reasons(result)

    gapped_rule = rule_material(
        versions=(
            version(V1, T0, payload=rule_payload(), declared_effective_to=T1),
            version(V2, T3, payload=rule_payload()),
        )
    )
    result = assert_parity(store_db, world(rule=gapped_rule), as_of=T2)
    assert result.resolution_status == STATUS_RESOLVED
    assert RULE_NOT_EFFECTIVE in _partial_reasons(result)

    gapped_role = _gapped(role_payload, role_material)
    result = assert_parity(store_db, world(role=gapped_role), as_of=T2)
    assert result.resolution_status == STATUS_RESOLVED
    assert ROLE_NOT_EFFECTIVE in _partial_reasons(result)
    assert result.result_level_reason != AUTHORITY_LINEAGE_CONTRADICTORY
    assert result.result_level_reason != AUTHORITY_REFERENCE_DANGLING


@store_covers("V-04", parity=True)
def test_v04_reactivation_after_a_gap_does_grant(store_db) -> None:
    authority = _gapped(authority_payload, authority_material)
    reactivated = assert_parity(store_db, world(authority=authority), as_of=T3)
    assert reactivated.outcome == OUTCOME_ALLOW
    assert _resolved_authority_version(reactivated) == V2


@store_covers("V-05", parity=True)
def test_v05_inactive_but_effective_versions_in_all_four_families(store_db) -> None:
    """An unambiguously INACTIVE effective version is a deliberate, known
    configuration state - deterministic NONQUALIFICATION, never a defect."""

    for family_material, payload_factory, expected in (
        (assignment_material, assignment_payload, ASSIGNMENT_NOT_ACTIVE),
        (rule_material, rule_payload, RULE_NOT_ACTIVE),
        (role_material, role_payload, ROLE_NOT_ACTIVE),
    ):
        inactive = family_material(
            versions=(version(V1, T0, payload=payload_factory(), active_flag=False),)
        )
        key = {
            assignment_material: "assignment",
            rule_material: "rule",
            role_material: "role",
        }[family_material]
        result = assert_parity(store_db, world(**{key: inactive}))
        assert result.resolution_status == STATUS_RESOLVED, key
        assert expected in _partial_reasons(result), key

    inactive_authority = authority_material(
        versions=(version(V1, T0, payload=authority_payload(), active_flag=False),)
    )
    result = assert_parity(store_db, world(authority=inactive_authority))
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason == AUTHORITY_NOT_ACTIVE
    # Inactivity and unresolvability are different answers, never merged.
    assert result.result_level_reason != AUTHORITY_CODE_NOT_CONFIGURED

    # active_flag and effective time are never inferred from one another.
    future_active = authority_material(
        versions=(version(V1, T3, payload=authority_payload(), active_flag=True),)
    )
    assert (
        assert_parity(store_db, world(authority=future_active), as_of=T2).result_level_reason
        == AUTHORITY_CODE_NOT_CONFIGURED
    )


@store_covers("V-06", parity=True)
def test_v06_an_inactive_version_still_closes_its_predecessor(store_db) -> None:
    """Excluding inactive versions from lineage would silently RE-OPEN a
    deactivated predecessor. If that happened, V1 would still be open at T3
    and the result would wrongly be ALLOW."""

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T2, payload=authority_payload(), active_flag=False),
        )
    )
    result = assert_parity(store_db, world(authority=authority), as_of=T3)
    assert result.outcome == OUTCOME_DENY
    assert result.result_level_reason == AUTHORITY_NOT_ACTIVE
    assert _resolved_authority_version(result) == V2


@store_covers("V-07", parity=True)
def test_v07_exact_half_open_boundary_instants(store_db) -> None:
    """`effective_from` INCLUSIVE; `asserted_effective_to` EXCLUSIVE."""

    bounded = authority_material(
        versions=(version(V1, T1, payload=authority_payload(), declared_effective_to=T3),)
    )
    assert assert_parity(store_db, world(authority=bounded), as_of=T1).outcome == OUTCOME_ALLOW
    assert (
        assert_parity(store_db, world(authority=bounded), as_of=T1 - TICK).result_level_reason
        == AUTHORITY_CODE_NOT_CONFIGURED
    )
    assert (
        assert_parity(store_db, world(authority=bounded), as_of=T3 - TICK).outcome == OUTCOME_ALLOW
    )
    assert (
        assert_parity(store_db, world(authority=bounded), as_of=T3).result_level_reason
        == AUTHORITY_CODE_NOT_CONFIGURED
    )

    gapped = _gapped(authority_payload, authority_material)
    for instant in (T1, T1 + TICK, T3 - TICK):
        assert (
            assert_parity(store_db, world(authority=gapped), as_of=instant).result_level_reason
            == AUTHORITY_CODE_NOT_CONFIGURED
        ), instant
    assert assert_parity(store_db, world(authority=gapped), as_of=T3).outcome == OUTCOME_ALLOW

    # A future-dated version confers nothing before its effective_from, in
    # every family.
    future_authority = authority_material(versions=(version(V1, T3, payload=authority_payload()),))
    assert (
        assert_parity(store_db, world(authority=future_authority), as_of=T1).resolution_status
        == STATUS_FAIL_CLOSED
    )
    for key, family_material, payload_factory, expected in (
        ("assignment", assignment_material, assignment_payload, ASSIGNMENT_NOT_EFFECTIVE),
        ("rule", rule_material, rule_payload, RULE_NOT_EFFECTIVE),
        ("role", role_material, role_payload, ROLE_NOT_EFFECTIVE),
    ):
        future = family_material(versions=(version(V1, T3, payload=payload_factory()),))
        result = assert_parity(store_db, world(**{key: future}), as_of=T1)
        assert expected in _partial_reasons(result), key


@store_covers("V-08", parity=True)
def test_v08_raw_discovery_over_valid_retraction_facts(store_db) -> None:
    """The object's COMPLETE lineage must reach the kernel, which then decides.

    Here the retraction is entirely VALID: the surviving effective version
    carries a different code, so the requested one is simply not established.
    """

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(AUTHORITY_CODE)),
            version(V2, T1, payload=authority_payload(OTHER_CODE)),
        ),
        retractions=(retraction("r1", V1),),
    )
    result = assert_parity(store_db, world(authority=authority), as_of=T2)
    assert result.result_level_reason == AUTHORITY_CODE_NOT_CONFIGURED

    rule = rule_material(
        versions=(
            version(V1, T0, payload=rule_payload(authority_id=AUTHORITY_ID)),
            version(V2, T1, payload=rule_payload(authority_id="some-other-authority")),
        ),
        retractions=(retraction("r1", V1),),
    )
    assert_parity(store_db, world(rule=rule), as_of=T2)


@store_covers("V-09", parity=True)
def test_v09_recorded_time_versus_business_effective_reconstruction(store_db) -> None:
    """CORRECTED BUSINESS-EFFECTIVE RECONSTRUCTION, not recorded-knowledge
    replay: a version published long AFTER a historical as_of still
    participates in reconstructing it, and a valid later correction CHANGES
    what that same business as_of reconstructs."""

    published_much_later = RECORDED_AT.replace(year=2027)
    late_publication = authority_material(
        versions=(version(V1, T0, payload=authority_payload(), published_at=published_much_later),)
    )
    assert assert_parity(store_db, world(authority=late_publication), as_of=T1).outcome == (
        OUTCOME_ALLOW
    )

    original_only = world(
        authority=authority_material(
            versions=(version(V1, T0, payload=authority_payload(AUTHORITY_CODE)),)
        )
    )
    assert assert_parity(store_db, original_only, as_of=T1).outcome == OUTCOME_ALLOW

    retracted_today = RECORDED_AT.replace(year=2027)
    after_retraction = world(
        authority=authority_material(
            versions=(version(V1, T0, payload=authority_payload()),),
            retractions=(retraction("r1", V1, retracted_at=retracted_today),),
        )
    )
    removed = assert_parity(store_db, after_retraction, as_of=T1)
    assert removed.resolution_status == STATUS_FAIL_CLOSED
    assert removed.outcome == OUTCOME_DENY

    corrected_later = RECORDED_AT.replace(hour=13)
    after_correction = world(
        authority=authority_material(
            versions=(
                version(V1, T0, payload=authority_payload(AUTHORITY_CODE)),
                version(
                    V2,
                    T0,
                    payload=authority_payload(OTHER_CODE),
                    corrects_object_version=V1,
                    published_at=corrected_later,
                ),
            ),
            retractions=(retraction("r1", V1),),
        )
    )
    reconstructed = assert_parity(store_db, after_correction, as_of=T1)
    assert reconstructed.result_level_reason == AUTHORITY_CODE_NOT_CONFIGURED


@store_covers("V-10", parity=True)
def test_v10_valid_scope_operands_each_alone(store_db) -> None:
    assert (
        assert_parity(store_db, world(), business_context=_context(ORG_BRANCH)).outcome
        == OUTCOME_ALLOW
    )
    assert (
        assert_parity(store_db, world(), business_context=_context(None)).outcome == OUTCOME_ALLOW
    )

    exact = world(rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH))
    assert assert_parity(store_db, exact, business_context=_context(ORG_BRANCH)).outcome == (
        OUTCOME_ALLOW
    )
    mismatch = assert_parity(store_db, exact, business_context=_context(ORG_DIVISION))
    assert mismatch.resolution_status == STATUS_RESOLVED
    assert RULE_SCOPE_NOT_MATCHED in _decisive_reasons(mismatch)

    assignment_mismatch = assert_parity(
        store_db,
        world(assignment=assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_ROOT)),
        business_context=_context(ORG_BRANCH),
    )
    assert ASSIGNMENT_SCOPE_NOT_MATCHED in _decisive_reasons(assignment_mismatch)

    for ancestor in (ORG_DIVISION, ORG_ROOT, ORG_BRANCH):
        ancestry = world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ancestor))
        assert (
            assert_parity(store_db, ancestry, business_context=_context(ORG_BRANCH)).outcome
            == OUTCOME_ALLOW
        ), ancestor

    unrelated = assert_parity(
        store_db,
        world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id="org-unrelated")),
        business_context=_context(ORG_BRANCH),
    )
    assert RULE_SCOPE_NOT_MATCHED in _decisive_reasons(unrelated)


@store_covers("V-11", parity=True)
def test_v11_scope_composition_is_intersection_never_union(store_db) -> None:
    global_rule_exact_assignment = [
        authority_material(),
        role_material(),
        rule_material(scope_type=SCOPE_GLOBAL),
        assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH),
    ]
    assert (
        assert_parity(
            store_db, global_rule_exact_assignment, business_context=_context(ORG_BRANCH)
        ).outcome
        == OUTCOME_ALLOW
    )

    exact_rule_global_assignment = [
        authority_material(),
        role_material(),
        rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH),
        assignment_material(scope_type=SCOPE_GLOBAL),
    ]
    assert (
        assert_parity(
            store_db, exact_rule_global_assignment, business_context=_context(ORG_BRANCH)
        ).outcome
        == OUTCOME_ALLOW
    )

    both_equal = [
        authority_material(),
        role_material(),
        rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH),
        assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH),
    ]
    assert (
        assert_parity(store_db, both_equal, business_context=_context(ORG_BRANCH)).outcome
        == OUTCOME_ALLOW
    )

    ancestry_and_exact = [
        authority_material(),
        role_material(),
        rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_ROOT),
        assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH),
    ]
    assert (
        assert_parity(store_db, ancestry_and_exact, business_context=_context(ORG_BRANCH)).outcome
        == OUTCOME_ALLOW
    )

    # NO union / widening: a GLOBAL rule does not rescue an assignment scoped
    # somewhere else.
    no_widening = [
        authority_material(),
        role_material(),
        rule_material(scope_type=SCOPE_GLOBAL),
        assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_ROOT),
    ]
    denied = assert_parity(store_db, no_widening, business_context=_context(ORG_BRANCH))
    assert denied.outcome == OUTCOME_DENY
    path = denied.complete_nonqualifying_paths[0]
    assert path.scope_evaluation.rule_operand_satisfied is True
    assert path.scope_evaluation.assignment_operand_satisfied is False
    assert path.scope_evaluation.composed_satisfied is False

    differing_exact = [
        authority_material(),
        role_material(),
        rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_DIVISION),
        assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_ROOT),
    ]
    both_differ = assert_parity(store_db, differing_exact, business_context=_context(ORG_BRANCH))
    assert both_differ.resolution_status == STATUS_RESOLVED
    assert _decisive_reasons(both_differ) & {
        RULE_SCOPE_NOT_MATCHED,
        ASSIGNMENT_SCOPE_NOT_MATCHED,
        SCOPE_COMPOSITION_NOT_SATISFIED,
    }


@store_covers("V-12", parity=True)
def test_v12_evaluator_satisfaction_and_legitimate_non_satisfaction(store_db) -> None:
    """The supplied facts are present, correctly typed AND
    unit/currency/basis-COMPATIBLE, so the declared comparison is actually
    performed. An INCOMPATIBILITY is malformed evaluator INPUT and belongs to
    NS-RQ-02, never here."""

    scope_only = world(rule=rule_material(evaluator_type=EVALUATOR_NONE, parameter_payload=None))
    assert (
        assert_parity(store_db, scope_only, business_context=_context(ORG_BRANCH)).outcome
        == OUTCOME_ALLOW
    )

    def value(amount):
        return _context(ORG_BRANCH, offer_value={"value": amount, "unit": "INR"})

    for amount, expected in ((100, OUTCOME_ALLOW), (999, OUTCOME_ALLOW), (99, OUTCOME_DENY), (1000, OUTCOME_DENY)):
        assert (
            assert_parity(store_db, _band_world(), business_context=value(amount)).outcome
            == expected
        ), amount

    flipped = dict(_INR_BAND, lower_inclusive=False, upper_inclusive=True)
    assert (
        assert_parity(store_db, _band_world(flipped), business_context=value(100)).outcome
        == OUTCOME_DENY
    )
    assert (
        assert_parity(store_db, _band_world(flipped), business_context=value(1000)).outcome
        == OUTCOME_ALLOW
    )

    legitimate_miss = assert_parity(store_db, _band_world(), business_context=value(5))
    assert legitimate_miss.resolution_status == STATUS_RESOLVED
    assert EVALUATOR_CONDITION_NOT_SATISFIED in _decisive_reasons(legitimate_miss)

    percentage = {
        "fact": "discount_percentage",
        "basis": "OFFER_VALUE",
        "upper": 10,
        "upper_inclusive": True,
    }
    percentage_world = _band_world(percentage, evaluator_type=EVALUATOR_PERCENTAGE_BAND)
    within = _context(ORG_BRANCH, discount_percentage={"value": 7, "basis": "OFFER_VALUE"})
    above = _context(ORG_BRANCH, discount_percentage={"value": 12, "basis": "OFFER_VALUE"})
    assert assert_parity(store_db, percentage_world, business_context=within).outcome == (
        OUTCOME_ALLOW
    )
    assert assert_parity(store_db, percentage_world, business_context=above).outcome == OUTCOME_DENY

    membership = {"fact": "region", "values": ["NORTH", "SOUTH"]}
    set_world = _band_world(membership, evaluator_type=EVALUATOR_EXACT_VALUE_SET)
    assert (
        assert_parity(
            store_db, set_world, business_context=_context(ORG_BRANCH, region="NORTH")
        ).outcome
        == OUTCOME_ALLOW
    )
    non_member = assert_parity(
        store_db, set_world, business_context=_context(ORG_BRANCH, region="EAST")
    )
    assert EVALUATOR_CONDITION_NOT_SATISFIED in _decisive_reasons(non_member)
