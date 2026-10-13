"""PF-1A-E2-B section 9: NON-STORE CONFORMANCE, DETERMINISM and EVIDENCE DURABILITY.

The thirty-eight parity-YES scenarios of section 5.7A, driven identically
through BOTH compositions, plus the determinism and evidence-durability
obligations that only a persisted store can be asked to demonstrate.

WHAT MAKES THESE NON-STORE, and why it matters. Their SUBJECT is a provider,
a request input, resolver orchestration or the resolution clock, deterministic
defect ordering, or the evidence contract - never a malformed stored row.
Store PARTICIPATION and store SUBJECTHOOD are two INDEPENDENT dimensions:
NS-RS-01 reads entirely VALID rows and still fails closed; NS-AG-03,
NS-AG-04 and NS-DO-01..05 legitimately COMPOSE already-classified class A
malformed rows as CONTROLLED INGREDIENTS, and those rows keep their own class
and their own obligations in the authority-store manifest. Seeding such a row
does not discharge a non-store obligation, and the presence of one does not
turn the enclosing scenario into an authority-store fixture.

NS-DO-01..05 MUST be built from CLASS A shapes, because class B1 and B2 shapes
cannot be seeded in PostgreSQL at all. Where the E2-A test bodies use an
absent `published_at` or an `end <= start` interval to compose a multi-defect
state, this module composes the same reason codes from storable class A
shapes instead. No constraint is disabled, deferred or dropped anywhere.
"""

from __future__ import annotations

import threading

from app.modules.authorization.business_authority.contract import (
    ACTOR_PERSON_MAPPING_AMBIGUOUS,
    ACTOR_PERSON_MAPPING_MISSING,
    ACTOR_PERSON_PROVIDER_NOT_CONFIGURED,
    AUTHORITY_CODE_NOT_CONFIGURED,
    AUTHORITY_CONFIGURATION_UNAVAILABLE,
    AUTHORITY_LINEAGE_CONTRADICTORY,
    BUSINESS_AUTHORITY,
    EMPLOYMENT_STATE_AMBIGUOUS,
    EMPLOYMENT_STATE_MISSING,
    EVALUATOR_CONDITION_NOT_SATISFIED,
    EVALUATOR_FACTS_INVALID,
    EVALUATOR_NUMERIC_BAND,
    EVALUATOR_PERCENTAGE_BAND,
    HR_REFERENCE_PROVIDER_NOT_CONFIGURED,
    HR_REFERENCE_STALE,
    HR_REFERENCE_UNAVAILABLE,
    INCUMBENCY_AMBIGUOUS,
    INCUMBENCY_MISSING,
    NO_CANDIDATE_ASSIGNMENT,
    NO_QUALIFYING_PATH,
    ORG_HIERARCHY_UNRESOLVABLE,
    ORG_UNIT_STATE_AMBIGUOUS,
    ORG_UNIT_STATE_MISSING,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    POSITION_STATE_AMBIGUOUS,
    POSITION_STATE_MISSING,
    PUBLICATION_PROVENANCE_INVALID,
    REASON_CODE_RANK,
    RULE_SCOPE_NOT_MATCHED,
    SCOPE_ANCESTRY,
    SCOPE_CONTEXT_MISSING,
    SCOPE_EXACT,
    STAGE_S1_PERSON,
    STAGE_S2_EMPLOYMENT,
    STAGE_S4_RULES,
    STATUS_FAIL_CLOSED,
    STATUS_RESOLVED,
)
from app.modules.authorization.business_authority.domain import BusinessContext
from app.modules.authorization.business_authority.evidence import serialize_result
from app.modules.authorization.business_authority.scope import SCOPE_KIND_ORG_UNIT
from app.modules.authorization.business_authority.store_contract import ALL_STORE_TABLES
from sqlalchemy import text

from tests.fixtures.pf_1a_e2_a_reference_providers import (
    AUTHORITY_CODE,
    ORDER_REVERSED,
    ORDER_SHUFFLED,
    ORG_BRANCH,
    ORG_DIVISION,
    ORG_ROOT,
    POSITION_ID,
    RECORDED_AT,
    T0,
    T1,
    T2,
    T3,
    ReferenceActorPersonProvider,
    ReferenceAuthorityConfigurationProvider,
    ReferenceHrProvider,
    assignment_payload,
    authority_payload,
    retraction,
    rule_payload,
    version,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    AUTHORITY_ID,
    ROLE_ID,
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
ROLE_A, ROLE_B = "role-a", "role-b"
RULE_A, RULE_B = "rule-a", "rule-b"
ASSIGNMENT_A, ASSIGNMENT_B = "assignment-a", "assignment-b"
EARLIER = RECORDED_AT.replace(hour=11)


def _context(scope_id=None, **facts) -> BusinessContext:
    return BusinessContext(
        scope_type=SCOPE_KIND_ORG_UNIT if scope_id else None,
        scope_id=scope_id,
        declared_facts=facts,
    )


def _decisive_reasons(result) -> set[str]:
    return {path.decisive_nonqualification_reason for path in result.complete_nonqualifying_paths}


def _position_world():
    return world(assignment=assignment_material(person_id=None, position_id=POSITION_ID))


def _ancestry_world(scope_id=ORG_ROOT):
    return world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=scope_id))


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


def _two_path_world(*, rule_b_overrides=None, assignment_b_overrides=None, extra=()):
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


def _duplicate_start_rule(object_id: str, role_id: str, authority_id: str = AUTHORITY_ID):
    """CLASS A fixture A-02, as a CONTROLLED INGREDIENT.

    It keeps its own class and its own storability/parity obligations in the
    authority-store manifest; using it here composes an ORCHESTRATION scenario
    rather than re-testing the row.
    """

    return rule_material(
        object_id=object_id,
        versions=(
            version(V1, T0, payload=rule_payload(role_id=role_id, authority_id=authority_id)),
            version(V2, T0, payload=rule_payload(role_id=role_id, authority_id=authority_id)),
        ),
    )


def _decreasing_provenance_rule(object_id: str, role_id: str):
    """CLASS A fixture A-10, as a CONTROLLED INGREDIENT.

    E2-A's own multi-defect fixtures use an ABSENT `published_at` for this,
    which is class B1 and is rejected by the shipped schema. A DECREASING
    `published_at` produces the same PUBLICATION_PROVENANCE_INVALID from a
    storable class A shape, so the scenario runs against the real store rather
    than against a circumvented constraint.
    """

    return rule_material(
        object_id=object_id,
        versions=(
            version(
                V1,
                T0,
                payload=rule_payload(role_id=role_id, authority_id=AUTHORITY_ID),
                published_at=RECORDED_AT,
            ),
            version(
                V2,
                T2,
                payload=rule_payload(role_id=role_id, authority_id=AUTHORITY_ID),
                published_at=EARLIER,
            ),
        ),
    )


def _two_defective_rules(*, provenance_on: str, contradiction_on: str):
    return [
        authority_material(),
        role_material(object_id=ROLE_A),
        role_material(object_id=ROLE_B),
        _decreasing_provenance_rule(provenance_on, ROLE_A),
        _duplicate_start_rule(contradiction_on, ROLE_B),
    ]


# ===========================================================================
# NS-AP  the actor -> canonical person seam
# ===========================================================================


@store_covers("NS-AP-01", parity=True)
def test_ns_ap_01_no_actor_person_mapping(store_db) -> None:
    result = assert_parity(
        store_db, world(), actor_person_port=ReferenceActorPersonProvider(status="MISSING")
    )
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == ACTOR_PERSON_MAPPING_MISSING
    assert result.ordered_defects[0].stage == STAGE_S1_PERSON
    # E2-A 16.4 partial evidence: NO fabricated object/version pairs.
    assert result.partial_evaluations[0].established == ()


@store_covers("NS-AP-02", parity=True)
def test_ns_ap_02_an_ambiguous_actor_person_mapping_never_picks_one(store_db) -> None:
    result = assert_parity(
        store_db, world(), actor_person_port=ReferenceActorPersonProvider(status="AMBIGUOUS")
    )
    assert result.result_level_reason == ACTOR_PERSON_MAPPING_AMBIGUOUS
    assert result.established_state.person_id is None


@store_covers("NS-AP-03", parity=True)
def test_ns_ap_03_an_unbound_actor_person_provider(store_db) -> None:
    result = assert_parity(store_db, world(), actor_person_port=None)
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == ACTOR_PERSON_PROVIDER_NOT_CONFIGURED


# ===========================================================================
# NS-HR  the canonical HR reference seam
# ===========================================================================


@store_covers("NS-HR-01", parity=True)
def test_ns_hr_01_an_unbound_hr_provider(store_db) -> None:
    result = assert_parity(store_db, world(), hr_reference_port=None)
    assert result.result_level_reason == HR_REFERENCE_PROVIDER_NOT_CONFIGURED
    assert result.ordered_defects[0].stage == STAGE_S2_EMPLOYMENT


@store_covers("NS-HR-02", parity=True)
def test_ns_hr_02_an_unavailable_hr_reference(store_db) -> None:
    result = assert_parity(
        store_db, world(), hr_reference_port=ReferenceHrProvider(employment_result="UNAVAILABLE")
    )
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE


@store_covers("NS-HR-03", parity=True)
def test_ns_hr_03_a_stale_canonical_snapshot(store_db) -> None:
    """The staleness threshold VALUE remains a deferred policy parameter: the
    test SUPPLIES one and the kernel invents no default."""

    stale = assert_parity(
        store_db,
        world(),
        actor_person_port=ReferenceActorPersonProvider(snapshot_at=T2),
        hr_reference_port=ReferenceHrProvider(snapshot_at=T2.replace(year=2025)),
        hr_staleness_threshold_seconds=3600,
    )
    assert stale.resolution_status == STATUS_FAIL_CLOSED
    assert stale.result_level_reason == HR_REFERENCE_STALE

    reported = assert_parity(
        store_db, world(), hr_reference_port=ReferenceHrProvider(employment_result="STALE")
    )
    assert reported.result_level_reason == HR_REFERENCE_STALE


@store_covers("NS-HR-04", parity=True)
def test_ns_hr_04_a_missing_employment_state(store_db) -> None:
    result = assert_parity(
        store_db, world(), hr_reference_port=ReferenceHrProvider(employment_result="MISSING")
    )
    assert result.result_level_reason == EMPLOYMENT_STATE_MISSING


@store_covers("NS-HR-05", parity=True)
def test_ns_hr_05_an_ambiguous_employment_state(store_db) -> None:
    result = assert_parity(
        store_db, world(), hr_reference_port=ReferenceHrProvider(employment_result="AMBIGUOUS")
    )
    assert result.result_level_reason == EMPLOYMENT_STATE_AMBIGUOUS


@store_covers("NS-HR-06", parity=True)
def test_ns_hr_06_a_missing_position_state(store_db) -> None:
    """PG-DATA is YES here: the resolution only REACHES S7 once a valid rule
    and assignment have been stored and read."""

    result = assert_parity(
        store_db, _position_world(), hr_reference_port=ReferenceHrProvider(position_result="MISSING")
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == POSITION_STATE_MISSING


@store_covers("NS-HR-07", parity=True)
def test_ns_hr_07_an_ambiguous_position_state(store_db) -> None:
    result = assert_parity(
        store_db,
        _position_world(),
        hr_reference_port=ReferenceHrProvider(position_result="AMBIGUOUS"),
    )
    assert result.result_level_reason == POSITION_STATE_AMBIGUOUS


@store_covers("NS-HR-08", parity=True)
def test_ns_hr_08_no_incumbent_at_as_of(store_db) -> None:
    result = assert_parity(
        store_db,
        _position_world(),
        hr_reference_port=ReferenceHrProvider(incumbency_result="MISSING"),
    )
    assert result.result_level_reason == INCUMBENCY_MISSING


@store_covers("NS-HR-09", parity=True)
def test_ns_hr_09_more_than_one_incumbent_at_as_of(store_db) -> None:
    result = assert_parity(
        store_db,
        _position_world(),
        hr_reference_port=ReferenceHrProvider(incumbency_result="AMBIGUOUS"),
    )
    assert result.result_level_reason == INCUMBENCY_AMBIGUOUS


@store_covers("NS-HR-10", parity=True)
def test_ns_hr_10_a_missing_organisation_unit_version(store_db) -> None:
    result = assert_parity(
        store_db,
        _ancestry_world(),
        business_context=_context(ORG_BRANCH),
        hr_reference_port=ReferenceHrProvider(org_unit_result="MISSING"),
    )
    assert result.result_level_reason == ORG_UNIT_STATE_MISSING


@store_covers("NS-HR-11", parity=True)
def test_ns_hr_11_an_ambiguous_organisation_unit_version(store_db) -> None:
    result = assert_parity(
        store_db,
        _ancestry_world(),
        business_context=_context(ORG_BRANCH),
        hr_reference_port=ReferenceHrProvider(org_unit_result="AMBIGUOUS"),
    )
    assert result.result_level_reason == ORG_UNIT_STATE_AMBIGUOUS


@store_covers("NS-HR-12", parity=True)
def test_ns_hr_12_an_unresolvable_organisation_hierarchy(store_db) -> None:
    """A cycle, and separately depth exhaustion. Ancestry traversal is BOUNDED."""

    cyclic = assert_parity(
        store_db,
        _ancestry_world("org-unreachable"),
        business_context=_context("org-a"),
        hr_reference_port=ReferenceHrProvider(org_parents={"org-a": "org-b", "org-b": "org-a"}),
    )
    assert cyclic.result_level_reason == ORG_HIERARCHY_UNRESOLVABLE

    chain = {f"org-{index:02d}": f"org-{index + 1:02d}" for index in range(40)}
    chain["org-40"] = None
    exhausted = assert_parity(
        store_db,
        _ancestry_world("org-unreachable"),
        business_context=_context("org-00"),
        hr_reference_port=ReferenceHrProvider(org_parents=chain),
    )
    assert exhausted.result_level_reason == ORG_HIERARCHY_UNRESOLVABLE


# ===========================================================================
# NS-RQ  the request / scope / evaluator input seam
# ===========================================================================


@store_covers("NS-RQ-01", parity=True)
def test_ns_rq_01_a_required_canonical_scope_absent_from_the_request(store_db) -> None:
    """The STORED operand is well formed and VALID; only the caller's request
    is defective, which is what makes this a non-store scenario."""

    result = assert_parity(
        store_db,
        world(rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH)),
        business_context=_context(None),
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == SCOPE_CONTEXT_MISSING


@store_covers("NS-RQ-02", parity=True)
def test_ns_rq_02_malformed_evaluator_input_from_the_request(store_db) -> None:
    """THREE malformed request conditions, not two: ABSENT, WRONG TYPE, and
    UNIT/CURRENCY/BASIS INCOMPATIBLE.

    All three are malformed evaluator INPUT and fail closed with
    EVALUATOR_FACTS_INVALID. None is ever reported as
    EVALUATOR_CONDITION_NOT_SATISFIED, which is reserved for a declared
    comparison that was actually performed and legitimately returned false.
    """

    absent = assert_parity(store_db, _band_world(), business_context=_context(ORG_BRANCH))
    assert absent.resolution_status == STATUS_FAIL_CLOSED
    assert absent.result_level_reason == EVALUATOR_FACTS_INVALID

    for wrong in ("five hundred", {"value": "500", "unit": "INR"}, {"value": True, "unit": "INR"}):
        typed = assert_parity(
            store_db, _band_world(), business_context=_context(ORG_BRANCH, offer_value=wrong)
        )
        assert typed.result_level_reason == EVALUATOR_FACTS_INVALID, wrong

    # The amount would be INSIDE the band if the unit were compatible, so a
    # correct implementation cannot pass this by accident.
    mismatched_unit = assert_parity(
        store_db,
        _band_world(),
        business_context=_context(ORG_BRANCH, offer_value={"value": 500, "unit": "USD"}),
    )
    assert mismatched_unit.result_level_reason == EVALUATOR_FACTS_INVALID
    assert mismatched_unit.result_level_reason != EVALUATOR_CONDITION_NOT_SATISFIED

    percentage = {
        "fact": "discount_percentage",
        "basis": "OFFER_VALUE",
        "upper": 10,
        "upper_inclusive": True,
    }
    mismatched_basis = assert_parity(
        store_db,
        _band_world(percentage, evaluator_type=EVALUATOR_PERCENTAGE_BAND),
        business_context=_context(
            ORG_BRANCH, discount_percentage={"value": 5, "basis": "LINE_VALUE"}
        ),
    )
    assert mismatched_basis.result_level_reason == EVALUATOR_FACTS_INVALID

    without_unit = assert_parity(
        store_db,
        _band_world(),
        business_context=_context(ORG_BRANCH, offer_value={"value": 500}),
    )
    assert without_unit.result_level_reason == EVALUATOR_FACTS_INVALID


# ===========================================================================
# NS-PT-01  the authority configuration PORT's read/transport behaviour
# ===========================================================================


@store_covers("NS-PT-01", parity=True)
def test_ns_pt_01_a_port_failure_fails_closed_identically_on_both_providers(
    store_db,
) -> None:
    """The port fails as a PORT rather than returning bad data.

    Both compositions are driven to the SAME failure point - a raised error
    during authority DISCOVERY - so the comparison is of like with like: the
    reference provider is told to raise, and the PostgreSQL side is given a
    genuinely failed transaction, so its very next read errors for real.

    Neither is ever degraded to "no candidates found" and neither becomes
    DENY + RESOLVED.
    """

    clear_store(store_db)
    seed_materials(store_db, world())

    reference = run_through_reference(
        world(),
        authority_configuration_port=ReferenceAuthorityConfigurationProvider(
            world()
        ).with_failure(raise_on_discovery=True),
    )

    try:
        store_db.execute(text("SELECT 1 / 0"))
    except Exception:  # noqa: BLE001 - deliberately poisoning the transaction
        pass

    postgres = run_through_postgres(store_db, None, seed=False)
    store_db.rollback()

    assert postgres.resolution_status == STATUS_FAIL_CLOSED
    assert postgres.result_level_reason == AUTHORITY_CONFIGURATION_UNAVAILABLE
    assert postgres.result_level_reason != AUTHORITY_CODE_NOT_CONFIGURED
    assert postgres.result_level_reason != NO_CANDIDATE_ASSIGNMENT
    assert serialize_result(postgres) == serialize_result(reference)


# ===========================================================================
# NS-RS  resolver orchestration, clock and entry points
# ===========================================================================


@store_covers("NS-RS-01", parity=True)
def test_ns_rs_01_the_requested_authority_has_no_grant_eligible_version(store_db) -> None:
    """The former fixture A-12, moved without subtraction.

    EVERY STORED ROW IS VALID. What is under test is the RESOLVER's deliberate
    asymmetry at an as_of (11.5): the other three families describe an ABSENT
    GRANT, while an unestablished REQUESTED authority describes an UNKNOWN
    QUESTION and therefore fails closed. Three shapes: lineage not started,
    lineage ended, and an as_of inside a VALID GAP.
    """

    not_started = authority_material(versions=(version(V1, T3, payload=authority_payload()),))
    ended = authority_material(
        versions=(version(V1, T0, payload=authority_payload(), declared_effective_to=T1),)
    )
    gapped = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(), declared_effective_to=T1),
            version(V2, T3, payload=authority_payload()),
        )
    )

    for authority in (not_started, ended, gapped):
        result = assert_parity(store_db, world(authority=authority), as_of=T2)
        assert result.outcome == OUTCOME_DENY
        assert result.resolution_status == STATUS_FAIL_CLOSED
        assert result.result_level_reason == AUTHORITY_CODE_NOT_CONFIGURED
        assert result.partial_evaluations
        assert result.partial_evaluations[0].reason_code == AUTHORITY_CODE_NOT_CONFIGURED


@store_covers("NS-RS-02", parity=True)
def test_ns_rs_02_one_instant_governs_every_stage_under_real_read_latency(
    store_db,
) -> None:
    """Real PostgreSQL reads between port calls make a second clock actually
    observable, which is why this scenario is worth running against the store
    and not only against the in-memory provider."""

    actor = ReferenceActorPersonProvider()
    hr = ReferenceHrProvider()

    result = assert_parity(
        store_db, _position_world(), as_of=T2, actor_person_port=actor, hr_reference_port=hr
    )
    assert result.outcome == OUTCOME_ALLOW

    observed = set(actor.observed_as_of) | set(hr.observed_as_of)
    assert observed == {T2}, observed
    assert result.as_of == T2


@store_covers("NS-RS-04", parity=True)
def test_ns_rs_04_shifting_only_the_recorded_timestamps_changes_nothing(store_db) -> None:
    """`published_at` / `retracted_at` are recorded-time EVIDENCE and
    validation input, never a second business clock and never a filter."""

    def build(published_at):
        return world(
            authority=authority_material(
                versions=(version(V1, T0, payload=authority_payload(), published_at=published_at),)
            )
        )

    original = assert_parity(store_db, build(RECORDED_AT), as_of=T2)
    shifted = assert_parity(store_db, build(RECORDED_AT.replace(year=2027)), as_of=T2)

    assert original.outcome == shifted.outcome == OUTCOME_ALLOW
    assert original.resolution_status == shifted.resolution_status
    assert original.result_level_reason == shifted.result_level_reason
    assert [path.path_sort_key for path in original.qualifying_paths] == [
        path.path_sort_key for path in shifted.qualifying_paths
    ]


# ===========================================================================
# NS-AG  aggregation, relevance and the result-level reason
# ===========================================================================


@store_covers("NS-AG-01", parity=True)
def test_ns_ag_01_two_valid_qualifying_paths_are_both_retained(store_db) -> None:
    """MULTIPLICITY IS NOT AMBIGUITY. Two complete valid paths is a normal,
    supported outcome and is never silently reduced to one."""

    result = assert_parity(store_db, _two_path_world())
    assert result.outcome == OUTCOME_ALLOW
    assert len(result.qualifying_paths) == 2
    keys = [path.path_sort_key for path in result.qualifying_paths]
    assert keys == sorted(keys)
    assert {path.business_authority_role.ref.object_id for path in result.qualifying_paths} == {
        ROLE_A,
        ROLE_B,
    }


@store_covers("NS-AG-02", parity=True)
def test_ns_ag_02_a_nonqualifying_path_is_retained_in_full(store_db) -> None:
    result = assert_parity(
        store_db,
        _two_path_world(rule_b_overrides={"scope_type": SCOPE_EXACT, "scope_id": ORG_ROOT}),
        business_context=_context(ORG_BRANCH),
    )
    assert result.outcome == OUTCOME_ALLOW
    assert len(result.qualifying_paths) == 1
    assert len(result.complete_nonqualifying_paths) == 1

    nonqualifying = result.complete_nonqualifying_paths[0]
    assert nonqualifying.decisive_nonqualification_reason == RULE_SCOPE_NOT_MATCHED
    for pair in (
        nonqualifying.business_authority_role,
        nonqualifying.business_authority,
        nonqualifying.business_authority_rule,
        nonqualifying.business_authority_assignment,
    ):
        assert pair.ref.object_id and pair.ref.object_version


@store_covers("NS-AG-03", parity=True)
def test_ns_ag_03_a_valid_path_never_rescues_relevant_corruption(store_db) -> None:
    """15.3 branch 1 takes precedence over branch 2, ALWAYS.

    The malformed rule is class A fixture A-02 used as a CONTROLLED
    INGREDIENT; what this scenario is ABOUT is the aggregation precedence.
    """

    materials = [
        authority_material(),
        role_material(object_id=ROLE_A),
        role_material(object_id=ROLE_B),
        rule_material(object_id=RULE_A, role_id=ROLE_A),
        _duplicate_start_rule(RULE_B, ROLE_B),
        assignment_material(object_id=ASSIGNMENT_A, role_id=ROLE_A),
        assignment_material(object_id=ASSIGNMENT_B, role_id=ROLE_B),
    ]
    result = assert_parity(store_db, materials, as_of=T1)
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY
    # The qualifying path's established evidence is STILL retained.
    assert len(result.qualifying_paths) == 1
    assert result.qualifying_paths[0].business_authority_role.ref.object_id == ROLE_A


@store_covers("NS-AG-04", parity=True)
def test_ns_ag_04_irrelevance_must_be_decidable_from_identity_alone(store_db) -> None:
    """A record is PROVABLY IRRELEVANT only when the exclusion can be
    established WITHOUT relying on any defective field."""

    unrelated_corrupt = authority_material(
        object_id="authority-unrelated",
        versions=(
            version(V1, T0, payload=authority_payload("A_COMPLETELY_DIFFERENT_AUTHORITY")),
            version(V2, T0, payload=authority_payload("A_COMPLETELY_DIFFERENT_AUTHORITY")),
        ),
    )
    unaffected = assert_parity(store_db, world(extra=(unrelated_corrupt,)), as_of=T1)
    assert unaffected.outcome == OUTCOME_ALLOW

    # THE COMPANION CASE: whether the object is relevant at all would depend on
    # the defective field itself, so it is NOT provably irrelevant.
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
        authority_material(object_id="some-other-authority", versions=(
            version(V1, T0, payload=authority_payload(OTHER_CODE)),
        )),
        role_material(object_id=ROLE_A),
        role_material(object_id=ROLE_B),
        rule_material(object_id=RULE_A, role_id=ROLE_A),
        ambiguous_relevance,
        assignment_material(object_id=ASSIGNMENT_A, role_id=ROLE_A),
    ]
    companion = assert_parity(store_db, materials, as_of=T1)
    assert companion.resolution_status == STATUS_FAIL_CLOSED
    assert companion.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY

    # And a RETRACTION is never used as an irrelevance test: the assertion
    # itself may be the defect.
    malformed = rule_material(
        object_id=RULE_B,
        versions=(version(V1, T0, payload=rule_payload(role_id=ROLE_B, authority_id=AUTHORITY_ID)),),
        retractions=(retraction("r1", V1), retraction("r2", V1)),
    )
    retraction_case = assert_parity(
        store_db,
        [
            authority_material(),
            role_material(object_id=ROLE_A),
            role_material(object_id=ROLE_B),
            rule_material(object_id=RULE_A, role_id=ROLE_A),
            malformed,
            assignment_material(object_id=ASSIGNMENT_A, role_id=ROLE_A),
        ],
    )
    assert retraction_case.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


@store_covers("NS-AG-05", parity=True)
def test_ns_ag_05_the_result_level_reason_when_no_path_qualifies(store_db) -> None:
    no_assignment = assert_parity(
        store_db,
        [authority_material(), role_material(object_id=ROLE_A), rule_material(object_id=RULE_A, role_id=ROLE_A)],
    )
    assert no_assignment.outcome == OUTCOME_DENY
    assert no_assignment.resolution_status == STATUS_RESOLVED
    assert no_assignment.result_level_reason == NO_CANDIDATE_ASSIGNMENT

    # 15.3 branch 3c: one SHARED path-level reason is PROMOTED, which is what
    # makes a denial legible rather than a bare NO_QUALIFYING_PATH.
    shared = _two_path_world(rule_b_overrides={"scope_type": SCOPE_EXACT, "scope_id": ORG_ROOT})
    shared[3] = rule_material(
        object_id=RULE_A, role_id=ROLE_A, scope_type=SCOPE_EXACT, scope_id=ORG_DIVISION
    )
    promoted = assert_parity(store_db, shared, business_context=_context(ORG_BRANCH))
    assert promoted.result_level_reason == RULE_SCOPE_NOT_MATCHED
    assert len(promoted.complete_nonqualifying_paths) == 2

    band = {"fact": "offer_value", "unit": "INR", "lower": 10_000, "lower_inclusive": True}
    differing = _two_path_world(
        rule_b_overrides={"evaluator_type": EVALUATOR_NUMERIC_BAND, "parameter_payload": band}
    )
    differing[3] = rule_material(
        object_id=RULE_A, role_id=ROLE_A, scope_type=SCOPE_EXACT, scope_id=ORG_ROOT
    )
    mixed = assert_parity(
        store_db,
        differing,
        business_context=_context(ORG_BRANCH, offer_value={"value": 5, "unit": "INR"}),
    )
    assert mixed.resolution_status == STATUS_RESOLVED
    assert mixed.result_level_reason == NO_QUALIFYING_PATH
    assert _decisive_reasons(mixed) == {RULE_SCOPE_NOT_MATCHED, EVALUATOR_CONDITION_NOT_SATISFIED}


# ===========================================================================
# NS-DO  deterministic defect ordering
# ===========================================================================


@store_covers("NS-DO-01", parity=True)
def test_ns_do_01_two_different_defects_at_one_stage(store_db) -> None:
    """Both defects sit at stage S4, so `stage_rank` cannot separate them and
    the CANONICAL SUBJECT KEY decides. Swapping which rule carries which
    defect flips the reported reason - the proof that the subject key, not
    provider order, not physical row order and not the reason rank, ranks
    second."""

    first = assert_parity(
        store_db, _two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B), as_of=T1
    )
    assert first.resolution_status == STATUS_FAIL_CLOSED
    assert first.result_level_reason == PUBLICATION_PROVENANCE_INVALID
    assert first.ordered_defects[0].stage == STAGE_S4_RULES

    swapped = assert_parity(
        store_db, _two_defective_rules(provenance_on=RULE_B, contradiction_on=RULE_A), as_of=T1
    )
    assert swapped.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY

    for _ in range(3):
        again = assert_parity(
            store_db, _two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B), as_of=T1
        )
        assert again.result_level_reason == PUBLICATION_PROVENANCE_INVALID


@store_covers("NS-DO-02", parity=True)
def test_ns_do_02_one_subject_carrying_two_reason_codes(store_db) -> None:
    """When `stage_rank` AND the canonical subject key are equal, the third
    component - the explicit, closed `reason_code_rank` table - decides.

    Both defects are on version V2 of one authority: its correction target
    does not exist (A-07) AND its `published_at` decreases relative to V1
    (A-10). Both shapes are class A and therefore storable, which is what lets
    this scenario run against the real store.
    """

    both_defects = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(), published_at=RECORDED_AT),
            version(
                V2,
                T2,
                payload=authority_payload(),
                corrects_object_version="9999",
                published_at=EARLIER,
            ),
        )
    )
    result = assert_parity(store_db, world(authority=both_defects), as_of=T3)

    assert result.resolution_status == STATUS_FAIL_CLOSED
    reported = {defect.reason_code for defect in result.ordered_defects}
    assert {AUTHORITY_LINEAGE_CONTRADICTORY, PUBLICATION_PROVENANCE_INVALID} <= reported

    # Same stage and same canonical subject, so only the reason rank can decide.
    ranked = [
        defect
        for defect in result.ordered_defects
        if defect.reason_code
        in {AUTHORITY_LINEAGE_CONTRADICTORY, PUBLICATION_PROVENANCE_INVALID}
    ]
    assert {defect.stage for defect in ranked} == {"S3"}
    assert len({defect.subject for defect in ranked}) == 1

    assert (
        REASON_CODE_RANK[AUTHORITY_LINEAGE_CONTRADICTORY]
        < REASON_CODE_RANK[PUBLICATION_PROVENANCE_INVALID]
    )
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


@store_covers("NS-DO-03", parity=True)
def test_ns_do_03_defects_in_different_families_order_by_stage_first(store_db) -> None:
    """An authority defect (S3) outranks a rule defect (S4), because
    `stage_rank` is the FIRST component of the canonical defect key."""

    materials = _two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B)
    materials[0] = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T0, payload=authority_payload()),
        )
    )
    result = assert_parity(store_db, materials, as_of=T1)
    assert result.ordered_defects[0].stage == "S3"
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY


@store_covers("NS-DO-04", "NS-EV-05", parity=True)
def test_ns_do_04_physical_row_order_and_repetition_change_nothing(store_db) -> None:
    """THE DATABASE IS NEVER WHAT DECIDES (attack surface 14).

    The same logical state is presented with the rows inserted in the opposite
    physical order, with the reference provider's return order reversed and
    shuffled, and repeatedly - and every run produces BYTE-IDENTICAL
    serialized output.
    """

    for materials, as_of in (
        (_two_path_world(), T2),
        (_two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B), T1),
    ):
        baseline = serialize_result(run_through_reference(materials, as_of=as_of))

        assert (
            serialize_result(run_through_reference(materials, as_of=as_of, order=ORDER_REVERSED))
            == baseline
        )
        for seed_value in range(4):
            assert (
                serialize_result(
                    run_through_reference(
                        materials, as_of=as_of, order=ORDER_SHUFFLED, seed_value=seed_value
                    )
                )
                == baseline
            )

        clear_store(store_db)
        forward = serialize_result(run_through_postgres(store_db, materials, as_of=as_of))
        assert forward == baseline

        clear_store(store_db)
        reversed_rows = serialize_result(
            run_through_postgres(store_db, materials, as_of=as_of, reverse_physical_order=True)
        )
        assert reversed_rows == baseline

        # Repeated runs over the SAME stored rows: no set/dict iteration,
        # address, hash-seed or clock dependence anywhere in the output.
        for _ in range(3):
            assert (
                serialize_result(run_through_postgres(store_db, None, as_of=as_of, seed=False))
                == baseline
            )


@store_covers("NS-DO-05", parity=True)
def test_ns_do_05_the_first_ordered_partial_carries_the_result_level_reason(
    store_db,
) -> None:
    """There is deliberately only ONE order, so the head of the ordered
    partial/failed collection and `result_level_reason` can never disagree."""

    both_defects = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(), published_at=RECORDED_AT),
            version(
                V2,
                T2,
                payload=authority_payload(),
                corrects_object_version="9999",
                published_at=EARLIER,
            ),
        )
    )
    states = (
        (_two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B), T1),
        (_two_defective_rules(provenance_on=RULE_B, contradiction_on=RULE_A), T1),
        (world(authority=both_defects), T3),
    )

    for materials, as_of in states:
        result = assert_parity(store_db, materials, as_of=as_of)
        assert result.resolution_status == STATUS_FAIL_CLOSED
        assert result.partial_evaluations
        assert result.partial_evaluations[0].reason_code == result.result_level_reason
        assert result.ordered_defects[0].reason_code == result.result_level_reason


# ===========================================================================
# NS-EV  the evidence contract
# ===========================================================================


@store_covers("NS-EV-01", parity=True)
def test_ns_ev_01_an_allow_carries_all_four_pairs_and_every_evaluation(store_db) -> None:
    result = assert_parity(store_db, _position_world())
    assert result.outcome == OUTCOME_ALLOW

    path = result.qualifying_paths[0]
    for pair in (
        path.business_authority_role,
        path.business_authority,
        path.business_authority_rule,
        path.business_authority_assignment,
    ):
        assert pair.ref.object_id and pair.ref.object_version
        assert pair.grant_eligibility.active_flag is True
        assert pair.grant_eligibility.effective_at_as_of is True
        assert pair.publication_reference_type
        assert pair.recorded_published_at is not None

    # Canonical HR evidence for the states actually relied upon.
    assert path.hr_evidence.person_id
    assert path.hr_evidence.position_version_id
    assert path.hr_evidence.incumbency_id
    assert path.scope_evaluation.composed_satisfied is True
    assert path.parameter_evaluation.evaluator_type


@store_covers("NS-EV-02", parity=True)
def test_ns_ev_02_a_scope_denial_and_a_parameter_denial_are_proved(store_db) -> None:
    scope_denial = assert_parity(
        store_db,
        world(rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_ROOT)),
        business_context=_context(ORG_BRANCH),
    )
    path = scope_denial.complete_nonqualifying_paths[0]
    assert path.decisive_nonqualification_reason == RULE_SCOPE_NOT_MATCHED
    assert path.scope_evaluation.rule_operand_satisfied is False
    for pair in (
        path.business_authority_role,
        path.business_authority,
        path.business_authority_rule,
        path.business_authority_assignment,
    ):
        assert pair.ref.object_version

    parameter_denial = assert_parity(
        store_db,
        _band_world(),
        business_context=_context(ORG_BRANCH, offer_value={"value": 5, "unit": "INR"}),
    )
    parameter_path = parameter_denial.complete_nonqualifying_paths[0]
    assert parameter_path.decisive_nonqualification_reason == EVALUATOR_CONDITION_NOT_SATISFIED
    assert parameter_path.parameter_evaluation.satisfied is False
    assert parameter_path.parameter_evaluation.decisive_comparison


@store_covers("NS-EV-03", parity=True)
def test_ns_ev_03_a_partial_evaluation_never_fabricates_a_pair(store_db) -> None:
    """It records what WAS established and NAMES what does not exist; absent
    pairs are ABSENT, never null-filled placeholders."""

    early = assert_parity(
        store_db, world(), actor_person_port=ReferenceActorPersonProvider(status="MISSING")
    )
    assert early.partial_evaluations[0].established == ()
    assert early.partial_evaluations[0].last_stage_reached == STAGE_S1_PERSON

    later = assert_parity(
        store_db,
        _position_world(),
        hr_reference_port=ReferenceHrProvider(incumbency_result="MISSING"),
    )
    partial = later.partial_evaluations[0]
    # The requested Authority, Rule and Role WERE established before S7 failed.
    assert partial.established
    assert all(ref.object_id and ref.object_version for ref in partial.established)
    assert partial.hr_evidence is not None


@store_covers("NS-EV-04", parity=True)
def test_ns_ev_04_a_zero_path_deny_resolved_still_explains_itself(store_db) -> None:
    result = assert_parity(
        store_db,
        [authority_material(), role_material(object_id=ROLE_A), rule_material(object_id=RULE_A, role_id=ROLE_A)],
    )
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.complete_nonqualifying_paths == ()
    assert result.qualifying_paths == ()

    established = result.established_state
    assert established.person_id
    assert established.requested_authority is not None
    assert established.rules_discovered == 1
    assert established.roles_referenced == 1
    assert established.assignments_discovered == 0
    assert established.last_stage_reached

    # And the evaluated business context is reported as evaluated.
    assert result.authority_code == AUTHORITY_CODE
    assert result.business_context is not None


@store_covers("NS-EV-05", parity=True)
def test_ns_ev_05_every_candidate_appears_in_exactly_one_collection(store_db) -> None:
    materials = _two_path_world(
        rule_b_overrides={"scope_type": SCOPE_EXACT, "scope_id": ORG_ROOT}
    )
    result = assert_parity(store_db, materials, business_context=_context(ORG_BRANCH))

    qualifying = {path.candidate_key for path in result.qualifying_paths}
    nonqualifying = {path.candidate_key for path in result.complete_nonqualifying_paths}
    partial = {evaluation.candidate_key for evaluation in result.partial_evaluations}

    assert qualifying & nonqualifying == set()
    assert qualifying & partial == set()
    assert nonqualifying & partial == set()

    for collection in (result.qualifying_paths, result.complete_nonqualifying_paths):
        keys = [path.path_sort_key for path in collection]
        assert keys == sorted(keys)
    partial_keys = [evaluation.sort_key for evaluation in result.partial_evaluations]
    assert partial_keys == sorted(partial_keys)


@store_covers("NS-EV-06", parity=True)
def test_ns_ev_06_no_secret_or_provider_specific_identifier_appears_in_evidence(
    store_db,
) -> None:
    """Asserted INDEPENDENTLY on the PostgreSQL side, not only through parity.

    A provider-specific identifier could only ever leak on that side, so
    agreement between the two compositions is necessary but not sufficient.
    """

    scenarios = (
        (_position_world(), {}),
        (world(rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_ROOT)),
         {"business_context": _context(ORG_BRANCH)}),
        (world(authority=authority_material(
            versions=(
                version(V1, T0, payload=authority_payload()),
                version(V2, T0, payload=authority_payload()),
            )
        )), {"as_of": T1}),
    )

    forbidden = (
        "password",
        "passwd",
        "secret",
        "token",
        "credential",
        "session",
        "psycopg",
        "sqlalchemy",
        "postgres",
        "SELECT ",
        "INSERT ",
        *ALL_STORE_TABLES,
        "object_id_fk",
        "authz_permission",
    )

    for materials, kwargs in scenarios:
        result = assert_parity(store_db, materials, **kwargs)
        serialized = serialize_result(result)
        lowered = serialized.lower()
        for needle in forbidden:
            assert needle.lower() not in lowered, needle
        # The physical primary keys of the store never surface either: every
        # cited identity is a canonical object/version pair.
        assert '"id":' not in serialized


@store_covers("NS-EV-07", parity=True)
def test_ns_ev_07_evidence_stays_dereferenceable_and_byte_identical(store_db) -> None:
    """EVIDENCE DURABILITY, and the deliberate 11.8.1 asymmetry.

    A cited version stays dereferenceable and byte-identical after later
    versions, a retraction and a valid correction are published, while the
    historical resolver may legitimately reconstruct a DIFFERENT answer for
    the same business as_of. Both answers are provable and neither overwrites
    the other.
    """

    from app.modules.authorization.business_authority.postgres_provider import (
        PostgresAuthorityConfigurationProvider,
    )

    original_version = version(V1, T0, payload=authority_payload(AUTHORITY_CODE))
    before = world(authority=authority_material(versions=(original_version,)))

    captured = assert_parity(store_db, before, as_of=T1)
    assert captured.outcome == OUTCOME_ALLOW
    cited = captured.qualifying_paths[0].business_authority.ref

    dereferenced_at_decision_time = PostgresAuthorityConfigurationProvider(
        store_db
    ).get_published_version(cited.object_family, cited.object_id, cited.object_version)

    corrected_later = RECORDED_AT.replace(hour=13)
    after = world(
        authority=authority_material(
            versions=(
                original_version,
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
    reconstructed = assert_parity(store_db, after, as_of=T1)

    dereferenced_afterwards = PostgresAuthorityConfigurationProvider(
        store_db
    ).get_published_version(cited.object_family, cited.object_id, cited.object_version)

    # DEREFERENCE IS ALWAYS AVAILABLE: retraction affects RESOLUTION only.
    assert dereferenced_afterwards == dereferenced_at_decision_time
    # ...while the reconstruction for the SAME business as_of has changed.
    assert reconstructed.result_level_reason == AUTHORITY_CODE_NOT_CONFIGURED
    # The captured result object itself is unchanged.
    assert captured.outcome == OUTCOME_ALLOW


# ===========================================================================
# DETERMINISM UNDER PERSISTENCE (criterion N2)
# ===========================================================================


@store_covers()
def test_determinism_survives_table_reorganisation_and_concurrent_resolutions(
    store_db,
) -> None:
    """Physical reorganisation and concurrency are the two persistence-specific
    ways a result could start depending on the database rather than on the
    kernel's own total order.

    WHY THE CONCURRENCY HALF IS GENUINELY PARALLEL (independent review finding
    F3). It used to open two sessions and resolve through them one after the
    other, which is a second SEQUENTIAL resolution wearing two sessions - it
    could not have detected shared mutable state, an ordering that depends on
    interleaved reads, or a provider that is not re-entrant, because none of
    those conditions was ever created. Criterion N2 asks for concurrent
    resolutions, so this now runs two resolutions in two threads, on two
    SEPARATE PostgreSQL connections, and PROVES the overlap:

        a `threading.Barrier(2)` is tripped INSIDE the provider, during the
            first lineage acquisition of each resolution. Neither thread can
            pass it until the other has also entered resolution, so the two
            executions demonstrably overlap;
        the barrier carries a timeout, so a serialized execution does not
            quietly degrade into a weaker test - it raises `BrokenBarrierError`
            and fails; and
        the two backend PIDs are asserted distinct, so the two resolutions
            cannot have shared one physical connection.

    Both results must equal the serialized baseline IN FULL - the canonical
    serialized form, not a chosen subset.
    """

    from app.core.database import SessionLocal
    from app.modules.authorization.business_authority.postgres_provider import (
        PostgresAuthorityConfigurationProvider,
    )

    materials = _two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B)
    clear_store(store_db)
    baseline = serialize_result(run_through_postgres(store_db, materials, as_of=T1))

    # VACUUM (FULL) rewrites the heap, so physical row order genuinely differs.
    # It cannot run inside a transaction block, so this needs an autocommit
    # connection.
    #
    # THE AUTOCOMMIT IS SCOPED, NOT LEAKED (correction C2). This used to take a
    # `raw_connection()` and call `set_autocommit(True)` on the DBAPI
    # connection directly. The pool's reset-on-return issues a ROLLBACK but
    # does NOT restore autocommit, so that connection went back into the pool
    # STILL IN AUTOCOMMIT - and a later, unrelated test drawing it would find
    # `LOCK TABLE` rejected with `NoActiveSqlTransaction` and `SET LOCAL`
    # silently ineffective, because neither has a transaction block to act in.
    # `execution_options(isolation_level="AUTOCOMMIT")` is the supported form:
    # SQLAlchemy restores the connection's original isolation level when it is
    # returned to the pool. This is the same class of defect as independent
    # review finding F2 - a test leaving connection state behind for a
    # stranger - and is fixed the same way, by scoping rather than by undoing.
    store_db.commit()
    with store_db.get_bind().connect().execution_options(
        isolation_level="AUTOCOMMIT"
    ) as maintenance:
        for table in ALL_STORE_TABLES:
            maintenance.execute(text(f"VACUUM (FULL, ANALYZE) {table}"))

    assert serialize_result(run_through_postgres(store_db, None, as_of=T1, seed=False)) == baseline

    # -- two GENUINELY concurrent resolutions --------------------------------

    class _RendezvousProvider(PostgresAuthorityConfigurationProvider):
        """The real provider, which waits for its counterpart exactly once.

        The wait is inside `get_lineage`, so it happens while the kernel is
        mid-resolution rather than before resolution starts.
        """

        def __init__(self, db, barrier: threading.Barrier) -> None:
            super().__init__(db)
            self._barrier = barrier
            self._met = False

        def get_lineage(self, object_family: str, object_id: str):
            if not self._met:
                self._met = True
                # Raises BrokenBarrierError if the other resolution never
                # arrives, so a serialized run FAILS rather than passing.
                self._barrier.wait(timeout=60)
            return super().get_lineage(object_family, object_id)

    barrier = threading.Barrier(2)
    results: dict[int, str] = {}
    backend_pids: dict[int, int] = {}
    met_inside_resolution: dict[int, bool] = {}
    worker_failures: list[BaseException] = []
    lock = threading.Lock()

    def resolve_concurrently(worker: int) -> None:
        try:
            with SessionLocal() as session:
                pid = session.execute(text("SELECT pg_backend_pid()")).scalar_one()
                provider = _RendezvousProvider(session, barrier)
                serialized = serialize_result(
                    run_through_postgres(
                        session,
                        None,
                        as_of=T1,
                        seed=False,
                        authority_configuration_port=provider,
                    )
                )
                session.rollback()
            with lock:
                backend_pids[worker] = pid
                results[worker] = serialized
                met_inside_resolution[worker] = provider._met
        except BaseException as error:  # noqa: BLE001 - re-raised on the main thread
            with lock:
                worker_failures.append(error)
            barrier.abort()

    threads = [
        threading.Thread(target=resolve_concurrently, args=(worker,), daemon=True)
        for worker in (0, 1)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)

    assert not worker_failures, f"a concurrent resolution failed: {worker_failures[0]!r}"
    assert not any(thread.is_alive() for thread in threads), "a concurrent resolution hung"

    # The overlap actually happened: both tripped the in-resolution barrier,
    # which neither could pass alone.
    assert met_inside_resolution == {0: True, 1: True}, met_inside_resolution
    # ...on two separate physical PostgreSQL connections.
    assert len(set(backend_pids.values())) == 2, backend_pids
    # ...and both agree with the serialized baseline in full.
    assert results[0] == baseline
    assert results[1] == baseline


@store_covers()
def test_the_kernel_re_sorts_even_without_a_provider_order_by(store_db) -> None:
    """A MUTATION-STYLE check: with the provider's ORDER BY deliberately
    removed, the KERNEL's canonical re-sort must still produce the same
    answer. Determinism must not depend on the provider being well behaved.
    """

    from app.modules.authorization.business_authority import repository

    materials = _two_defective_rules(provenance_on=RULE_A, contradiction_on=RULE_B)
    clear_store(store_db)
    baseline = serialize_result(run_through_postgres(store_db, materials, as_of=T1))

    real_load_lineage = repository.load_lineage

    def unordered_lineage(db, family, object_id):
        versions, retractions = real_load_lineage(db, family, object_id)
        return list(reversed(versions)), list(reversed(retractions))

    repository.load_lineage = unordered_lineage
    try:
        assert (
            serialize_result(run_through_postgres(store_db, None, as_of=T1, seed=False))
            == baseline
        )
    finally:
        repository.load_lineage = real_load_lineage
