"""PF-1A-E2-A corrections FU-2, FU-3, FU-4 and FU-5.

FU-2  PROGRESSIVE, CANDIDATE-SCOPED EVIDENCE. A candidate that reached S9 and
      then failed closed retained only the requested Business Authority, even
      though its Rule, Role and Assignment had all been successfully
      established. Every failure boundary must now retain everything actually
      established for that candidate - and must still fabricate nothing.

FU-3  CLOSED EMPLOYMENT-STATE VOCABULARY. An `employment_status` outside the
      contract's own vocabulary was treated as a known, resolved non-active
      state and produced DENY + RESOLVED / EMPLOYMENT_NOT_ACTIVE. It is a
      provider-contract failure and must fail closed.

FU-4  NO PROVIDER PROSE OR ORDER ARTEFACT IN CANONICAL EVIDENCE. Exception
      text, list indices and iteration positions are not stable domain data and
      must never reach canonical authorization evidence or defect ordering.

FU-5  THE BOUNDED FALLBACK APPLIES TO COMPLETE PATHS TOO. OTHER_NONQUALIFICATION
      was reachable only on partial evaluations; a complete nonqualifying path
      could not carry it or its explanation.
"""

from __future__ import annotations

from app.modules.authorization.business_authority import evaluators, scope
from app.modules.authorization.business_authority.contract import (
    ASSIGNMENT_TARGET_INVALID,
    EMPLOYMENT_NOT_ACTIVE,
    EVALUATOR_CONDITION_NOT_SATISFIED,
    EVALUATOR_NUMERIC_BAND,
    EVALUATOR_UNKNOWN,
    HR_REFERENCE_STALE,
    HR_REFERENCE_UNAVAILABLE,
    OTHER_NONQUALIFICATION,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    PUBLICATION_PROVENANCE_INVALID,
    RULE_SCOPE_NOT_MATCHED,
    SCOPE_ANCESTRY,
    SCOPE_EXACT,
    SCOPE_SEMANTICS_UNSUPPORTED,
    STAGE_S4_RULES,
    STAGE_S5_ROLES,
    STAGE_S6_ASSIGNMENTS,
    STAGE_S7_TARGET,
    STAGE_S8_SCOPE,
    STAGE_S9_PARAMETERS,
    STATUS_FAIL_CLOSED,
    STATUS_RESOLVED,
)
from app.modules.authorization.business_authority.domain import BusinessContext
from app.modules.authorization.business_authority.evidence import serialize_result
from app.modules.authorization.business_authority.scope import (
    SCOPE_KIND_ORG_UNIT,
    ScopeCompositionResult,
)
from app.modules.hr_reference.contract import (
    EMPLOYMENT_ACTIVE,
    EMPLOYMENT_INACTIVE,
    EMPLOYMENT_LEFT,
    EMPLOYMENT_ON_LEAVE,
)
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    ORDER_REVERSED,
    ORDER_SHUFFLED,
    ORG_BRANCH,
    ORG_DIVISION,
    ORG_ROOT,
    PERSON_ID,
    POSITION_ID,
    T0,
    T2,
    ReferenceActorPersonProvider,
    ReferenceAuthorityConfigurationProvider,
    ReferenceHrProvider,
    assignment_payload,
    authority_payload,
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
    assignment_material,
    authority_material,
    role_material,
    rule_material,
    run,
    world,
)

STALE = T2.replace(year=2020)
THRESHOLD = 3600


def _fresh_actor():
    return ReferenceActorPersonProvider(snapshot_at=T2)


def _position_world():
    return world(assignment=assignment_material(person_id=None, position_id=POSITION_ID))


def _ancestry_context() -> BusinessContext:
    return BusinessContext(scope_type=SCOPE_KIND_ORG_UNIT, scope_id=ORG_BRANCH)


def _head(result):
    assert result.partial_evaluations, "a failure must retain partial evidence"
    return result.partial_evaluations[0]


def _established_ids(result) -> list[str]:
    return [ref.object_id for ref in _head(result).established]


# ===========================================================================
# FU-2  PROGRESSIVE EVIDENCE, stage by stage
# ===========================================================================


def test_an_s4_failure_retains_only_what_was_established_through_s4() -> None:
    """The Rule's own lineage failed, so the Rule is NOT established. Only the
    requested Business Authority is."""

    broken_rule = rule_material(
        versions=(version(V1, T0, payload=rule_payload(), published_at=None),)
    )
    result = run(world(rule=broken_rule))

    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert _head(result).last_stage_reached == STAGE_S4_RULES
    assert _established_ids(result) == [AUTHORITY_ID]


def test_an_s5_failure_retains_the_authority_and_the_rule() -> None:
    broken_role = role_material(
        versions=(version(V1, T0, payload=role_payload(), published_at=None),)
    )
    result = run(world(role=broken_role))

    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert _head(result).last_stage_reached == STAGE_S5_ROLES
    assert _established_ids(result) == [AUTHORITY_ID, RULE_ID]


def test_an_s6_failure_retains_the_authority_the_rule_and_the_role() -> None:
    broken_assignment = assignment_material(
        versions=(version(V1, T0, payload=assignment_payload(), published_at=None),)
    )
    result = run(world(assignment=broken_assignment))

    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert _head(result).last_stage_reached == STAGE_S6_ASSIGNMENTS
    assert _established_ids(result) == [AUTHORITY_ID, RULE_ID, ROLE_ID]


def test_an_s7_failure_retains_all_four_object_version_pairs() -> None:
    """The Assignment IS established at S6; it is its TARGET that is invalid."""

    both_targets = assignment_material(
        versions=(
            version(V1, T0, payload=assignment_payload(person_id="p", position_id="pos")),
        )
    )
    result = run(world(assignment=both_targets))

    assert result.result_level_reason == ASSIGNMENT_TARGET_INVALID
    assert _head(result).last_stage_reached == STAGE_S7_TARGET
    assert _established_ids(result) == [AUTHORITY_ID, RULE_ID, ROLE_ID, ASSIGNMENT_ID]


def test_an_s8_failure_retains_all_four_pairs_plus_hr_and_scope_state() -> None:
    unsupported_scope = assignment_material(scope_type="REGION_TREE", scope_id=ORG_ROOT)
    result = run(
        world(assignment=unsupported_scope),
        business_context=_ancestry_context(),
    )

    assert result.result_level_reason == SCOPE_SEMANTICS_UNSUPPORTED
    head = _head(result)
    assert head.last_stage_reached == STAGE_S8_SCOPE
    assert _established_ids(result) == [AUTHORITY_ID, RULE_ID, ROLE_ID, ASSIGNMENT_ID]
    assert head.hr_evidence is not None
    assert head.hr_evidence.person_id == PERSON_ID
    assert head.scope_evaluation is not None


def test_an_s9_failure_retains_everything_established_including_scope_and_parameters() -> None:
    """The exact controller reproduction: a complete candidate reached S9 and
    failed closed on an unknown evaluator, and the record retained only the
    requested Business Authority."""

    unknown_evaluator = rule_material(evaluator_type="SOME_FUTURE_EVALUATOR")
    result = run(world(rule=unknown_evaluator))

    assert result.result_level_reason == EVALUATOR_UNKNOWN
    head = _head(result)
    assert head.last_stage_reached == STAGE_S9_PARAMETERS
    assert _established_ids(result) == [AUTHORITY_ID, RULE_ID, ROLE_ID, ASSIGNMENT_ID]

    # ... with the per-object active/effective evaluations already made ...
    for evidence in head.established_objects:
        assert evidence.grant_eligibility.lineage_valid is True
        assert evidence.grant_eligibility.effective_at_as_of is True
        assert evidence.grant_eligibility.active_flag is True

    # ... the HR state relied upon ...
    assert head.hr_evidence is not None
    assert head.hr_evidence.person_id == PERSON_ID
    assert head.hr_evidence.employment_state_version_id
    assert len(head.hr_evidence.canonical_snapshot_at_values) >= 2

    # ... the scope evaluation already established ...
    assert head.scope_evaluation is not None
    assert head.scope_evaluation.composed_satisfied is True

    # ... and the evaluator state.
    assert head.parameter_evaluation is not None
    assert head.parameter_evaluation.evaluator_type == "SOME_FUTURE_EVALUATOR"


def test_an_s1_failure_establishes_and_therefore_retains_nothing() -> None:
    """Nothing is fabricated at the other extreme either."""

    result = run(world(), actor_person_port=ReferenceActorPersonProvider(status="MISSING"))
    head = _head(result)
    assert head.established == ()
    assert head.established_objects == ()
    assert head.hr_evidence is None


def test_an_s2_failure_retains_the_canonical_person_already_established() -> None:
    result = run(world(), hr_reference_port=ReferenceHrProvider(employment_result="MISSING"))
    head = _head(result)
    assert head.established_objects == ()
    assert head.hr_evidence is not None
    assert head.hr_evidence.person_id == PERSON_ID


# ===========================================================================
# FU-2  the state RESPONSIBLE for a stale failure is retained
# ===========================================================================


def test_a_stale_position_failure_retains_the_observed_position_and_snapshot() -> None:
    result = run(
        _position_world(),
        actor_person_port=_fresh_actor(),
        hr_reference_port=ReferenceHrProvider(snapshot_at=T2, position_snapshot_at=STALE),
        hr_staleness_threshold_seconds=THRESHOLD,
    )
    assert result.result_level_reason == HR_REFERENCE_STALE
    hr_evidence = _head(result).hr_evidence
    assert hr_evidence is not None
    assert hr_evidence.position_version_id == f"position-version-{POSITION_ID}"
    assert STALE in hr_evidence.canonical_snapshot_at_values


def test_a_stale_incumbency_failure_retains_the_observed_incumbency_and_snapshot() -> None:
    result = run(
        _position_world(),
        actor_person_port=_fresh_actor(),
        hr_reference_port=ReferenceHrProvider(snapshot_at=T2, incumbency_snapshot_at=STALE),
        hr_staleness_threshold_seconds=THRESHOLD,
    )
    assert result.result_level_reason == HR_REFERENCE_STALE
    hr_evidence = _head(result).hr_evidence
    assert hr_evidence is not None
    # The Position established BEFORE the failure, and the Incumbency that
    # caused it.
    assert hr_evidence.position_version_id == f"position-version-{POSITION_ID}"
    assert hr_evidence.incumbency_id == f"incumbency-{POSITION_ID}"
    assert STALE in hr_evidence.canonical_snapshot_at_values


def test_a_stale_organisation_unit_failure_retains_the_hops_traversed_so_far() -> None:
    result = run(
        world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_ROOT)),
        business_context=_ancestry_context(),
        actor_person_port=_fresh_actor(),
        hr_reference_port=ReferenceHrProvider(
            snapshot_at=T2, org_unit_snapshots={ORG_DIVISION: STALE}
        ),
        hr_staleness_threshold_seconds=THRESHOLD,
    )
    assert result.result_level_reason == HR_REFERENCE_STALE
    head = _head(result)
    assert head.scope_evaluation is not None
    # The first hop was traversed successfully before the deeper one failed.
    assert head.scope_evaluation.rule_scope_type == SCOPE_ANCESTRY


def test_a_mismatched_identity_failure_does_not_cite_the_foreign_object() -> None:
    """Identity-bound-but-stale state IS cited; state that was never about the
    requested object is NOT."""

    result = run(
        _position_world(),
        hr_reference_port=ReferenceHrProvider(returned_position_id="position-9999"),
    )
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE
    hr_evidence = _head(result).hr_evidence
    assert hr_evidence is not None
    assert hr_evidence.position_version_id is None
    assert "position-9999" not in serialize_result(result)


def test_no_partial_evaluation_ever_fabricates_an_unestablished_pair() -> None:
    scenarios = (
        run(world(rule=rule_material(versions=(version(V1, T0, payload=rule_payload(), published_at=None),)))),
        run(world(role=role_material(versions=(version(V1, T0, payload=role_payload(), published_at=None),)))),
        run(world(assignment=assignment_material(versions=(version(V1, T0, payload=assignment_payload(), published_at=None),)))),
        run(world(rule=rule_material(evaluator_type="SOME_FUTURE_EVALUATOR"))),
        run(world(), actor_person_port=ReferenceActorPersonProvider(status="MISSING")),
    )
    for result in scenarios:
        for partial in result.partial_evaluations:
            for ref in partial.established:
                assert ref.object_id and ref.object_version
            assert len(partial.established) == len(partial.established_objects)


def test_progressive_evidence_is_deterministic_under_shuffling() -> None:
    materials = world(rule=rule_material(evaluator_type="SOME_FUTURE_EVALUATOR"))
    baseline = serialize_result(run(materials))
    assert serialize_result(run(materials, order=ORDER_REVERSED)) == baseline
    for seed in range(4):
        assert serialize_result(run(materials, order=ORDER_SHUFFLED, seed=seed)) == baseline


def test_one_candidate_never_inherits_another_candidates_established_state() -> None:
    """Two rules under one authority: the failing candidate's record must not
    contain the other candidate's Role or Assignment."""

    materials = [
        authority_material(),
        role_material(object_id="role-a"),
        role_material(object_id="role-b"),
        rule_material(object_id="rule-a", role_id="role-a"),
        rule_material(
            object_id="rule-b",
            role_id="role-b",
            versions=(
                version(V1, T0, payload=rule_payload(role_id="role-b"), published_at=None),
            ),
        ),
        assignment_material(object_id="assignment-a", role_id="role-a"),
    ]
    result = run(materials)

    assert result.resolution_status == STATUS_FAIL_CLOSED
    failing = [p for p in result.partial_evaluations if p.is_defect][0]
    # rule-b's lineage failed, so ONLY the authority is established for it.
    assert [ref.object_id for ref in failing.established] == [AUTHORITY_ID]


# ===========================================================================
# FU-3  the employment-state vocabulary is CLOSED
# ===========================================================================


def test_every_legitimate_employment_state_still_behaves_as_defined() -> None:
    assert run(world(), hr_reference_port=ReferenceHrProvider(
        employment_status=EMPLOYMENT_ACTIVE)).outcome == OUTCOME_ALLOW

    for status in (EMPLOYMENT_INACTIVE, EMPLOYMENT_ON_LEAVE, EMPLOYMENT_LEFT):
        result = run(world(), hr_reference_port=ReferenceHrProvider(employment_status=status))
        assert result.outcome == OUTCOME_DENY, status
        assert result.resolution_status == STATUS_RESOLVED, status
        assert result.result_level_reason == EMPLOYMENT_NOT_ACTIVE, status


def test_an_unknown_employment_state_fails_closed_and_is_never_reported_non_active() -> None:
    """The exact controller reproduction. EMPLOYMENT_NOT_ACTIVE is for KNOWN,
    resolved non-active states; an unknown one is not authoritative state at
    all."""

    result = run(world(), hr_reference_port=ReferenceHrProvider(employment_status="ALIEN_STATUS"))

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE
    assert result.result_level_reason != EMPLOYMENT_NOT_ACTIVE
    assert result.result_level_reason != OTHER_NONQUALIFICATION


def test_employment_state_matching_is_exact_and_not_fuzzy_cased_or_prefixed() -> None:
    for status in ("active", "Active", "ACTIVE ", " ACTIVE", "ACTIVE_LEAVE", "INACTIVE_X", ""):
        result = run(world(), hr_reference_port=ReferenceHrProvider(employment_status=status))
        assert result.resolution_status == STATUS_FAIL_CLOSED, status
        assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE, status


# ===========================================================================
# FU-4  no provider prose, no order artefact, in canonical evidence
# ===========================================================================


def _raising_provider(message: str):
    from app.modules.authorization.business_authority.contract import BUSINESS_AUTHORITY

    return ReferenceAuthorityConfigurationProvider(world()).with_failure(
        raise_on=frozenset({(BUSINESS_AUTHORITY, AUTHORITY_ID)}), raise_message=message
    )


def test_two_providers_failing_the_same_way_produce_byte_identical_evidence() -> None:
    """Exception wording varies across provider, library and runtime versions.
    If it reached canonical evidence, the same failure would serialize
    differently on two deployments."""

    first = serialize_result(run(None, authority_configuration_port=_raising_provider("boom")))
    second = serialize_result(
        run(
            None,
            authority_configuration_port=_raising_provider(
                "ORA-01017: invalid username/password at 0x7f3c; retry 4/5"
            ),
        )
    )
    assert first == second


def test_provider_exception_text_never_appears_in_the_result_evidence() -> None:
    provider_prose = "provider diagnostic message alpha"
    result = run(None, authority_configuration_port=_raising_provider(provider_prose))
    serialized = serialize_result(result)
    assert provider_prose not in serialized
    assert "diagnostic message alpha" not in serialized



def test_discovery_failure_evidence_is_also_free_of_provider_prose() -> None:
    def resolve(message):
        provider = ReferenceAuthorityConfigurationProvider(world()).with_failure(
            raise_on_discovery=True, raise_message=message
        )
        return serialize_result(run(None, authority_configuration_port=provider))

    assert resolve("alpha") == resolve("omega: something entirely different")


def test_malformed_material_evidence_does_not_depend_on_provider_row_order() -> None:
    """The rejection names the offending record by its own canonical identity,
    never by a list index or iteration position."""

    malformed = authority_material(
        versions=(
            version("0001", T0, payload=authority_payload()),
            version("0002", effective_from=None, payload=authority_payload()),
            version("0003", T2, payload=authority_payload()),
        )
    )
    materials = world(authority=malformed)
    baseline = serialize_result(run(materials))

    assert serialize_result(run(materials, order=ORDER_REVERSED)) == baseline
    for seed in range(5):
        assert serialize_result(run(materials, order=ORDER_SHUFFLED, seed=seed)) == baseline
    assert "[0]" not in baseline and "[1]" not in baseline and "[2]" not in baseline


def test_defect_ordering_does_not_depend_on_exception_prose() -> None:
    """Two equal-stage fail-closed defects with reordered provider material and
    differing exception messages still select the same reported reason."""

    from app.modules.authorization.business_authority.contract import BUSINESS_AUTHORITY_RULE

    def resolve(message, order, seed):
        materials = [
            authority_material(),
            role_material(object_id="role-a"),
            role_material(object_id="role-b"),
            rule_material(object_id="rule-a", role_id="role-a"),
            rule_material(
                object_id="rule-b",
                role_id="role-b",
                versions=(
                    version(V1, T0, payload=rule_payload(role_id="role-b"), published_at=None),
                ),
            ),
        ]
        provider = ReferenceAuthorityConfigurationProvider(
            materials, order=order, seed=seed
        ).with_failure(
            raise_on=frozenset({(BUSINESS_AUTHORITY_RULE, "rule-a")}), raise_message=message
        )
        return run(None, authority_configuration_port=provider)

    baseline = resolve("first message", "contract", 0)
    assert baseline.resolution_status == STATUS_FAIL_CLOSED
    for message in ("first message", "a totally different failure text"):
        for order in ("contract", ORDER_REVERSED, ORDER_SHUFFLED):
            for seed in range(3):
                other = resolve(message, order, seed)
                assert other.result_level_reason == baseline.result_level_reason
                assert serialize_result(other) == serialize_result(baseline)


# ===========================================================================
# FU-5  the bounded fallback on a COMPLETE nonqualifying path
# ===========================================================================


def _unsatisfied_with_no_specific_reason(rule_operand, assignment_operand):
    """A fully resolved scope composition that does not qualify and for which
    no specific path-level reason applies.

    Injected deliberately: the current scope predicates always supply a
    specific reason, so this is the bounded synthetic condition FU-5 permits in
    order to prove the evidence and invariant machinery rather than inventing a
    new PBL policy scenario.
    """

    return ScopeCompositionResult(
        satisfied=False,
        rule_operand=rule_operand,
        assignment_operand=assignment_operand,
        nonqualification_reason=None,
        defect_reason=None,
    )


def test_a_complete_path_may_carry_the_bounded_fallback_at_s8(monkeypatch) -> None:
    monkeypatch.setattr(scope, "compose", _unsatisfied_with_no_specific_reason)

    result = run(world())

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason == OTHER_NONQUALIFICATION
    assert len(result.complete_nonqualifying_paths) == 1

    path = result.complete_nonqualifying_paths[0]
    assert path.decisive_nonqualification_reason == OTHER_NONQUALIFICATION
    # A COMPLETE path: all four object/version pairs are still present.
    for pair in (
        path.business_authority,
        path.business_authority_role,
        path.business_authority_rule,
        path.business_authority_assignment,
    ):
        assert pair.ref.object_id and pair.ref.object_version
    # ... and it carries the deterministic explanation.
    explanation = path.nonqualification_explanation
    assert explanation
    assert AUTHORITY_ID in explanation and RULE_ID in explanation
    assert ROLE_ID in explanation and ASSIGNMENT_ID in explanation
    assert STAGE_S8_SCOPE in explanation


def test_a_complete_path_may_carry_the_bounded_fallback_at_s9(monkeypatch) -> None:
    def unsatisfied_evaluator(evaluator_type, payload, facts):
        return evaluators.EvaluatorResult(
            satisfied=False,
            evaluator_type=evaluator_type,
            nonqualification_reason=None,
            defect_reason=None,
        )

    monkeypatch.setattr(evaluators, "evaluate", unsatisfied_evaluator)

    result = run(world())
    assert result.result_level_reason == OTHER_NONQUALIFICATION
    path = result.complete_nonqualifying_paths[0]
    assert path.decisive_nonqualification_reason == OTHER_NONQUALIFICATION
    assert STAGE_S9_PARAMETERS in path.nonqualification_explanation


def test_the_complete_path_explanation_is_deterministic_and_excluded_from_ordering(
    monkeypatch,
) -> None:
    monkeypatch.setattr(scope, "compose", _unsatisfied_with_no_specific_reason)

    explanations = {
        run(world()).complete_nonqualifying_paths[0].nonqualification_explanation
        for _ in range(5)
    }
    assert len(explanations) == 1

    path = run(world()).complete_nonqualifying_paths[0]
    assert path.nonqualification_explanation not in str(path.path_sort_key)

    baseline = serialize_result(run(world()))
    assert serialize_result(run(world(), order=ORDER_REVERSED)) == baseline


def test_the_fallback_never_displaces_an_existing_specific_reason() -> None:
    """Every specific reason still wins where it applies - no monkeypatching,
    the real predicates."""

    scope_denied = run(
        world(rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_ROOT)),
        business_context=_ancestry_context(),
    )
    assert scope_denied.complete_nonqualifying_paths[0].decisive_nonqualification_reason == (
        RULE_SCOPE_NOT_MATCHED
    )
    assert scope_denied.complete_nonqualifying_paths[0].nonqualification_explanation == ""

    band = {"fact": "offer_value", "unit": "INR", "lower": 1000, "lower_inclusive": True}
    parameter_denied = run(
        world(rule=rule_material(evaluator_type=EVALUATOR_NUMERIC_BAND, parameter_payload=band)),
        business_context=BusinessContext(
            declared_facts={"offer_value": {"value": 5, "unit": "INR"}}
        ),
    )
    assert parameter_denied.complete_nonqualifying_paths[0].decisive_nonqualification_reason == (
        EVALUATOR_CONDITION_NOT_SATISFIED
    )
    assert parameter_denied.complete_nonqualifying_paths[0].nonqualification_explanation == ""


def test_a_complete_fallback_path_never_prevents_an_independently_qualifying_path(
    monkeypatch,
) -> None:
    """An ALLOW may coexist with nonqualifying paths in evidence; the fallback
    never blocks a valid grant and is never the reason for an ALLOW."""

    real_compose = scope.compose

    def compose_only_for_role_b(rule_operand, assignment_operand):
        if assignment_operand.scope_id == ORG_BRANCH:
            return _unsatisfied_with_no_specific_reason(rule_operand, assignment_operand)
        return real_compose(rule_operand, assignment_operand)

    monkeypatch.setattr(scope, "compose", compose_only_for_role_b)

    materials = [
        authority_material(),
        role_material(object_id="role-a"),
        role_material(object_id="role-b"),
        rule_material(object_id="rule-a", role_id="role-a"),
        rule_material(object_id="rule-b", role_id="role-b"),
        assignment_material(object_id="assignment-a", role_id="role-a"),
        assignment_material(
            object_id="assignment-b", role_id="role-b", scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH
        ),
    ]
    result = run(materials, business_context=_ancestry_context())

    assert result.outcome == OUTCOME_ALLOW
    assert result.result_level_reason == ""
    assert result.qualifying_paths
    fallback_paths = [
        path
        for path in result.complete_nonqualifying_paths
        if path.decisive_nonqualification_reason == OTHER_NONQUALIFICATION
    ]
    assert fallback_paths
    assert fallback_paths[0].nonqualification_explanation
    for path in result.qualifying_paths:
        assert path.decisive_nonqualification_reason is None
        assert path.nonqualification_explanation == ""


def test_a_fail_closed_defect_still_wins_over_the_complete_path_fallback(monkeypatch) -> None:
    monkeypatch.setattr(scope, "compose", _unsatisfied_with_no_specific_reason)

    broken_role = role_material(
        object_id="role-b",
        versions=(version(V1, T0, payload=role_payload(), published_at=None),),
    )
    materials = [
        authority_material(),
        role_material(object_id="role-a"),
        broken_role,
        rule_material(object_id="rule-a", role_id="role-a"),
        rule_material(object_id="rule-b", role_id="role-b"),
        assignment_material(object_id="assignment-a", role_id="role-a"),
    ]
    result = run(materials)

    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID
    assert result.result_level_reason != OTHER_NONQUALIFICATION


def test_a_specific_nonqualification_path_and_a_fallback_path_coexist(monkeypatch) -> None:
    """Two complete nonqualifying paths, one with a SPECIFIC reason and one with
    the bounded fallback.

    Neither displaces the other, each keeps its own decisive reason, only the
    fallback path carries an explanation, and because the two reasons differ the
    15.3 branch 3c promotion correctly does NOT fire - the result is the ordinary
    NO_QUALIFYING_PATH.
    """

    from app.modules.authorization.business_authority.contract import NO_QUALIFYING_PATH

    real_compose = scope.compose

    def compose_fallback_only_for_role_b(rule_operand, assignment_operand):
        if rule_operand.scope_id == ORG_DIVISION:
            return _unsatisfied_with_no_specific_reason(rule_operand, assignment_operand)
        return real_compose(rule_operand, assignment_operand)

    monkeypatch.setattr(scope, "compose", compose_fallback_only_for_role_b)

    materials = [
        authority_material(),
        role_material(object_id="role-a"),
        role_material(object_id="role-b"),
        # role-a's rule names an exact scope the context does not match -> the
        # SPECIFIC reason RULE_SCOPE_NOT_MATCHED.
        rule_material(object_id="rule-a", role_id="role-a", scope_type=SCOPE_EXACT, scope_id=ORG_ROOT),
        # role-b's rule is routed to the injected no-specific-reason branch.
        rule_material(
            object_id="rule-b", role_id="role-b", scope_type=SCOPE_EXACT, scope_id=ORG_DIVISION
        ),
        assignment_material(object_id="assignment-a", role_id="role-a"),
        assignment_material(object_id="assignment-b", role_id="role-b"),
    ]
    result = run(materials, business_context=_ancestry_context())

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert result.result_level_reason == NO_QUALIFYING_PATH

    reasons = {
        path.decisive_nonqualification_reason for path in result.complete_nonqualifying_paths
    }
    assert reasons == {RULE_SCOPE_NOT_MATCHED, OTHER_NONQUALIFICATION}

    for path in result.complete_nonqualifying_paths:
        if path.decisive_nonqualification_reason == OTHER_NONQUALIFICATION:
            assert path.nonqualification_explanation
        else:
            assert path.nonqualification_explanation == ""
