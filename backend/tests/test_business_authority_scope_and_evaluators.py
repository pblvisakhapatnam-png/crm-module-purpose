"""PF-1A-E2-A section 18: SCOPE AND COMPOSITION, and EVALUATORS.

Covers valid-shape scenarios V-10, V-11 and V-12, class A fixtures A-13, A-14
and A-15, and non-store scenarios NS-RQ-01, NS-RQ-02 and NS-HR-10 to NS-HR-12.

THE BOUNDARY BETWEEN A STORED DEFECT AND A REQUEST DEFECT (9.7.0). An
unsupported `scope_type` VALUE on a stored rule is class A fixture A-15; an
unknown evaluator TYPE is A-13 and a malformed evaluator PAYLOAD is A-14 -
all of them stored data. A required canonical scope the REQUEST does not
supply, and a required business fact the REQUEST supplies wrongly, are
NON-STORE scenarios NS-RQ-01 and NS-RQ-02: the stored operand and the stored
evaluator are entirely valid, and only the caller's request is defective.
"""

from __future__ import annotations

from decimal import Decimal

from app.modules.authorization.business_authority.contract import (
    ASSIGNMENT_SCOPE_NOT_MATCHED,
    EVALUATOR_CONDITION_NOT_SATISFIED,
    EVALUATOR_EXACT_VALUE_SET,
    EVALUATOR_FACTS_INVALID,
    EVALUATOR_NONE,
    EVALUATOR_NUMERIC_BAND,
    EVALUATOR_PAYLOAD_INVALID,
    EVALUATOR_PERCENTAGE_BAND,
    EVALUATOR_UNKNOWN,
    ORG_HIERARCHY_UNRESOLVABLE,
    ORG_UNIT_STATE_AMBIGUOUS,
    ORG_UNIT_STATE_MISSING,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
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
from app.modules.authorization.business_authority.scope import SCOPE_KIND_ORG_UNIT
from tests.fixtures.pf_1a_e2_a_corpus import covers
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    ORG_BRANCH,
    ORG_DIVISION,
    ORG_ROOT,
    ReferenceHrProvider,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    assignment_material,
    rule_material,
    run,
    world,
)


def _context(scope_id: str | None = ORG_BRANCH, **facts) -> BusinessContext:
    return BusinessContext(
        scope_type=SCOPE_KIND_ORG_UNIT if scope_id else None,
        scope_id=scope_id,
        declared_facts=facts,
    )


def _decisive_reasons(result) -> set[str]:
    return {
        path.decisive_nonqualification_reason for path in result.complete_nonqualifying_paths
    }


# ===========================================================================
# V-10  each valid operand alone
# ===========================================================================


@covers("V-10")
def test_a_global_operand_is_satisfied_for_every_applicable_context() -> None:
    """GLOBAL is the unconstrained TOP element for its own operand."""

    assert run(world(), business_context=_context()).outcome == OUTCOME_ALLOW
    assert run(world(), business_context=_context(scope_id=None)).outcome == OUTCOME_ALLOW


@covers("V-10")
def test_an_exact_operand_matches_and_mismatches_deterministically() -> None:
    matching = world(rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH))
    assert run(matching, business_context=_context(ORG_BRANCH)).outcome == OUTCOME_ALLOW

    result = run(matching, business_context=_context(ORG_DIVISION))
    # A well-formed, SUPPORTED operand that simply does not match is ORDINARY
    # nonqualification, not a defect.
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert RULE_SCOPE_NOT_MATCHED in _decisive_reasons(result)


@covers("V-10")
def test_an_assignment_operand_mismatch_reports_its_own_reason_code() -> None:
    materials = world(assignment=assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_ROOT))
    result = run(materials, business_context=_context(ORG_BRANCH))
    assert result.resolution_status == STATUS_RESOLVED
    assert ASSIGNMENT_SCOPE_NOT_MATCHED in _decisive_reasons(result)


@covers("V-10")
def test_ancestry_matches_an_ancestor_and_does_not_match_an_unrelated_scope() -> None:
    """Resolved ONLY through the canonical organisation reference, at the SAME
    as_of for every hop. Authorization invents no hierarchy of its own."""

    for ancestor in (ORG_DIVISION, ORG_ROOT):
        materials = world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ancestor))
        assert run(materials, business_context=_context(ORG_BRANCH)).outcome == OUTCOME_ALLOW

    unrelated = world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id="org-unrelated"))
    result = run(unrelated, business_context=_context(ORG_BRANCH))
    assert result.resolution_status == STATUS_RESOLVED
    assert RULE_SCOPE_NOT_MATCHED in _decisive_reasons(result)


@covers("V-10")
def test_ancestry_is_satisfied_when_the_context_is_the_operand_scope_itself() -> None:
    materials = world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_BRANCH))
    assert run(materials, business_context=_context(ORG_BRANCH)).outcome == OUTCOME_ALLOW


# ===========================================================================
# A-15  an unsupported scope_type VALUE on a STORED rule
# ===========================================================================


@covers("A-15")
def test_an_unsupported_stored_scope_type_fails_closed() -> None:
    """A scope_type the evaluator does not support is NEVER treated as GLOBAL
    and never silently ignored (12.3)."""

    materials = world(rule=rule_material(scope_type="REGION_TREE", scope_id=ORG_BRANCH))
    result = run(materials, business_context=_context(ORG_BRANCH))

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == SCOPE_SEMANTICS_UNSUPPORTED


# ===========================================================================
# NS-RQ-01  the REQUEST does not supply a required canonical scope
# ===========================================================================


@covers("NS-RQ-01")
def test_a_missing_required_canonical_scope_fails_closed_rather_than_matching() -> None:
    """The stored rule/assignment is VALID and is read normally; the defect is
    in the REQUEST (9.7.0). A business context that does not supply a scope
    required by a non-GLOBAL operand FAILS CLOSED rather than matching
    permissively."""

    materials = world(rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH))
    result = run(materials, business_context=_context(scope_id=None))

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == SCOPE_CONTEXT_MISSING
    # Explicitly NOT an ordinary scope non-match.
    assert result.result_level_reason != RULE_SCOPE_NOT_MATCHED


# ===========================================================================
# NS-HR-10 to NS-HR-12  the organisation hierarchy during ancestry evaluation
# ===========================================================================


@covers("NS-HR-10")
def test_a_missing_organisation_unit_version_fails_closed() -> None:
    materials = world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_ROOT))
    result = run(
        materials,
        business_context=_context(ORG_BRANCH),
        hr_reference_port=ReferenceHrProvider(org_unit_result="MISSING"),
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == ORG_UNIT_STATE_MISSING


@covers("NS-HR-11")
def test_an_ambiguous_organisation_unit_version_fails_closed() -> None:
    materials = world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_ROOT))
    result = run(
        materials,
        business_context=_context(ORG_BRANCH),
        hr_reference_port=ReferenceHrProvider(org_unit_result="AMBIGUOUS"),
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == ORG_UNIT_STATE_AMBIGUOUS


@covers("NS-HR-12")
def test_an_organisation_hierarchy_cycle_fails_closed() -> None:
    materials = world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id="org-unreachable"))
    cyclic = ReferenceHrProvider(org_parents={"org-a": "org-b", "org-b": "org-a"})
    result = run(
        materials,
        business_context=_context("org-a"),
        hr_reference_port=cyclic,
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == ORG_HIERARCHY_UNRESOLVABLE


@covers("NS-HR-12")
def test_ancestry_depth_exhaustion_fails_closed() -> None:
    """Ancestry traversal must be BOUNDED by an explicit maximum depth (12.3)."""

    chain = {f"org-{index:02d}": f"org-{index + 1:02d}" for index in range(40)}
    chain["org-40"] = None
    materials = world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id="org-unreachable"))
    result = run(
        materials,
        business_context=_context("org-00"),
        hr_reference_port=ReferenceHrProvider(org_parents=chain),
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == ORG_HIERARCHY_UNRESOLVABLE


# ===========================================================================
# V-11  scope COMPOSITION over valid operands - INTERSECTION, never union
# ===========================================================================


@covers("V-11")
def test_global_rule_intersect_exact_assignment_is_constrained_by_the_assignment() -> None:
    """GLOBAL INTERSECT X = X. GLOBAL never overrides a narrower operand."""

    materials = world(
        rule=rule_material(scope_type=SCOPE_GLOBAL),
        assignment=assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH),
    )
    assert run(materials, business_context=_context(ORG_BRANCH)).outcome == OUTCOME_ALLOW

    constrained = run(materials, business_context=_context(ORG_DIVISION))
    assert constrained.outcome == OUTCOME_DENY
    assert ASSIGNMENT_SCOPE_NOT_MATCHED in _decisive_reasons(constrained)


@covers("V-11")
def test_exact_rule_intersect_global_assignment_is_constrained_by_the_rule() -> None:
    materials = world(
        rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH),
        assignment=assignment_material(scope_type=SCOPE_GLOBAL),
    )
    assert run(materials, business_context=_context(ORG_BRANCH)).outcome == OUTCOME_ALLOW
    assert run(materials, business_context=_context(ORG_DIVISION)).outcome == OUTCOME_DENY


@covers("V-11")
def test_two_exact_operands_naming_the_same_scope_are_both_satisfied() -> None:
    materials = world(
        rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH),
        assignment=assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH),
    )
    assert run(materials, business_context=_context(ORG_BRANCH)).outcome == OUTCOME_ALLOW


@covers("V-11")
def test_two_exact_operands_naming_different_scopes_can_never_both_be_satisfied() -> None:
    """Ordinary nonqualification (SCOPE_COMPOSITION_NOT_SATISFIED), not a
    defect and not a configuration error (12.4)."""

    materials = world(
        rule=rule_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH),
        assignment=assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_DIVISION),
    )
    for scope_id in (ORG_BRANCH, ORG_DIVISION, ORG_ROOT):
        result = run(materials, business_context=_context(scope_id))
        assert result.resolution_status == STATUS_RESOLVED, scope_id
        assert SCOPE_COMPOSITION_NOT_SATISFIED in _decisive_reasons(result), scope_id


@covers("V-11")
def test_ancestry_intersect_exact_composes_by_intersection() -> None:
    materials = world(
        rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_ROOT),
        assignment=assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_BRANCH),
    )
    assert run(materials, business_context=_context(ORG_BRANCH)).outcome == OUTCOME_ALLOW
    assert run(materials, business_context=_context(ORG_DIVISION)).outcome == OUTCOME_DENY


@covers("V-11")
def test_there_is_no_union_or_widening_behaviour() -> None:
    """The decisive proof that composition is INTERSECTION.

    Under a union rule, a satisfied GLOBAL rule operand would rescue an
    unsatisfied EXACT assignment operand and the result would be ALLOW.
    """

    materials = world(
        rule=rule_material(scope_type=SCOPE_GLOBAL),
        assignment=assignment_material(scope_type=SCOPE_EXACT, scope_id=ORG_ROOT),
    )
    result = run(materials, business_context=_context(ORG_BRANCH))
    assert result.outcome == OUTCOME_DENY

    path = result.complete_nonqualifying_paths[0]
    # The evidence shows WHICH operand was decisive (12.4, 16.3).
    assert path.scope_evaluation.rule_operand_satisfied is True
    assert path.scope_evaluation.assignment_operand_satisfied is False
    assert path.scope_evaluation.composed_satisfied is False


# ===========================================================================
# V-12  evaluator satisfaction and LEGITIMATE non-satisfaction
# ===========================================================================

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


@covers("V-12")
def test_the_none_evaluator_makes_a_rule_scope_only() -> None:
    materials = world(rule=rule_material(evaluator_type=EVALUATOR_NONE, parameter_payload=None))
    assert run(materials, business_context=_context()).outcome == OUTCOME_ALLOW


@covers("V-12")
def test_a_numeric_band_is_evaluated_at_each_boundary_under_each_inclusivity_flag() -> None:
    """Boundary semantics are EXPLICIT. A payload naming a bound without
    stating its inclusivity is malformed (section 13)."""

    def value(amount):
        return _context(offer_value={"value": amount, "unit": "INR"})

    # lower INCLUSIVE, upper EXCLUSIVE
    assert run(_band_world(), business_context=value(100)).outcome == OUTCOME_ALLOW
    assert run(_band_world(), business_context=value(999)).outcome == OUTCOME_ALLOW
    assert run(_band_world(), business_context=value(99)).outcome == OUTCOME_DENY
    assert run(_band_world(), business_context=value(1000)).outcome == OUTCOME_DENY

    # the OPPOSITE inclusivity flags on both bounds
    flipped = dict(_INR_BAND, lower_inclusive=False, upper_inclusive=True)
    assert run(_band_world(flipped), business_context=value(100)).outcome == OUTCOME_DENY
    assert run(_band_world(flipped), business_context=value(1000)).outcome == OUTCOME_ALLOW


@covers("V-12")
def test_a_legitimate_band_non_match_is_ordinary_nonqualification() -> None:
    """WELL-FORMED is a precondition on the INPUT, not a description of the
    outcome: the facts are present, correctly typed AND unit-compatible, so the
    declared comparison was actually performed and legitimately returned
    false."""

    result = run(
        _band_world(), business_context=_context(offer_value={"value": 5, "unit": "INR"})
    )
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    assert EVALUATOR_CONDITION_NOT_SATISFIED in _decisive_reasons(result)


@covers("V-12")
def test_a_percentage_band_evaluates_against_an_explicit_basis() -> None:
    payload = {
        "fact": "discount_percentage",
        "basis": "OFFER_VALUE",
        "upper": Decimal("10"),
        "upper_inclusive": True,
    }
    materials = _band_world(payload, evaluator_type=EVALUATOR_PERCENTAGE_BAND)

    within = _context(discount_percentage={"value": Decimal("7.5"), "basis": "OFFER_VALUE"})
    assert run(materials, business_context=within).outcome == OUTCOME_ALLOW

    above = _context(discount_percentage={"value": Decimal("12"), "basis": "OFFER_VALUE"})
    assert run(materials, business_context=above).outcome == OUTCOME_DENY


@covers("V-12")
def test_exact_value_set_membership_and_non_membership() -> None:
    payload = {"fact": "region", "values": ["NORTH", "SOUTH"]}
    materials = _band_world(payload, evaluator_type=EVALUATOR_EXACT_VALUE_SET)

    assert run(materials, business_context=_context(region="NORTH")).outcome == OUTCOME_ALLOW

    result = run(materials, business_context=_context(region="EAST"))
    assert result.resolution_status == STATUS_RESOLVED
    assert EVALUATOR_CONDITION_NOT_SATISFIED in _decisive_reasons(result)


# ===========================================================================
# A-13 / A-14  malformed STORED evaluator type and payload
# ===========================================================================


@covers("A-13")
def test_an_unknown_stored_evaluator_type_fails_closed() -> None:
    """Selection is by EXACT match - never by prefix, fuzzy match or fallback.
    An unknown type is never treated as satisfied and never silently skipped."""

    materials = world(rule=rule_material(evaluator_type="SOME_FUTURE_EVALUATOR"))
    result = run(materials, business_context=_context())
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == EVALUATOR_UNKNOWN


@covers("A-13")
def test_evaluator_selection_never_falls_back_to_a_near_match() -> None:
    for near_miss in ("NUMERIC", "NUMERIC_BAND_V2", "numeric_band", ""):
        materials = world(rule=rule_material(evaluator_type=near_miss))
        result = run(materials, business_context=_context())
        assert result.result_level_reason == EVALUATOR_UNKNOWN, near_miss


@covers("A-14")
def test_a_malformed_stored_payload_fails_closed() -> None:
    """Payload validation is AUTHORITATIVE HERE and runs at evaluation time
    against the published payload, regardless of what any store validated at
    write time (section 13)."""

    malformed_payloads = (
        {"fact": "offer_value", "unit": "INR", "lower": 100},  # no inclusivity flag
        {"fact": "offer_value", "lower": 100, "lower_inclusive": True},  # no explicit unit
        {"unit": "INR", "lower": 100, "lower_inclusive": True},  # names no fact
        {"fact": "offer_value", "unit": "INR"},  # neither bound
        "not-an-object",
    )
    for payload in malformed_payloads:
        result = run(
            _band_world(payload),
            business_context=_context(offer_value={"value": 500, "unit": "INR"}),
        )
        assert result.resolution_status == STATUS_FAIL_CLOSED, payload
        assert result.result_level_reason == EVALUATOR_PAYLOAD_INVALID, payload


@covers("A-14")
def test_a_none_evaluator_carrying_a_payload_is_malformed() -> None:
    materials = world(
        rule=rule_material(evaluator_type=EVALUATOR_NONE, parameter_payload={"fact": "x"})
    )
    result = run(materials, business_context=_context())
    assert result.result_level_reason == EVALUATOR_PAYLOAD_INVALID


# ===========================================================================
# NS-RQ-02  malformed evaluator INPUT supplied by the REQUEST
# ===========================================================================


@covers("NS-RQ-02")
def test_a_required_business_fact_absent_from_the_request_fails_closed() -> None:
    result = run(_band_world(), business_context=_context())
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == EVALUATOR_FACTS_INVALID


@covers("NS-RQ-02")
def test_a_required_business_fact_of_the_wrong_type_fails_closed() -> None:
    for wrong in ("five hundred", {"value": "500", "unit": "INR"}, {"value": True, "unit": "INR"}):
        result = run(_band_world(), business_context=_context(offer_value=wrong))
        assert result.resolution_status == STATUS_FAIL_CLOSED, wrong
        assert result.result_level_reason == EVALUATOR_FACTS_INVALID, wrong


@covers("NS-RQ-02")
def test_a_unit_currency_or_basis_incompatibility_is_malformed_input_not_a_false_comparison() -> None:
    """F-10.3-DC-01, stated in terms.

    Section 13 makes a unit/currency/basis incompatibility MALFORMED EVALUATOR
    INPUT: it fails closed with EVALUATOR_FACTS_INVALID, is never coerced or
    converted implicitly, and is NEVER reported as
    EVALUATOR_CONDITION_NOT_SATISFIED.
    """

    # The amount would be INSIDE the band if the unit were compatible, so a
    # correct implementation cannot pass this by accident.
    mismatched_unit = run(
        _band_world(), business_context=_context(offer_value={"value": 500, "unit": "USD"})
    )
    assert mismatched_unit.resolution_status == STATUS_FAIL_CLOSED
    assert mismatched_unit.result_level_reason == EVALUATOR_FACTS_INVALID
    assert mismatched_unit.result_level_reason != EVALUATOR_CONDITION_NOT_SATISFIED

    percentage_payload = {
        "fact": "discount_percentage",
        "basis": "OFFER_VALUE",
        "upper": 10,
        "upper_inclusive": True,
    }
    mismatched_basis = run(
        _band_world(percentage_payload, evaluator_type=EVALUATOR_PERCENTAGE_BAND),
        business_context=_context(discount_percentage={"value": 5, "basis": "LINE_VALUE"}),
    )
    assert mismatched_basis.resolution_status == STATUS_FAIL_CLOSED
    assert mismatched_basis.result_level_reason == EVALUATOR_FACTS_INVALID


@covers("NS-RQ-02")
def test_a_fact_supplied_without_its_explicit_unit_fails_closed() -> None:
    result = run(_band_world(), business_context=_context(offer_value={"value": 500}))
    assert result.result_level_reason == EVALUATOR_FACTS_INVALID


# ===========================================================================
# No executable expression language, anywhere (attack surface 26)
# ===========================================================================


def test_the_evaluator_module_contains_no_executable_expression_mechanism() -> None:
    """No eval, no exec, no user-authored code, no script, no SQL, no lambda
    string, no regex-as-policy, no template expansion. Conditions are
    declarative DATA interpreted by registered, reviewed evaluator code."""

    import inspect

    from app.modules.authorization.business_authority import evaluators

    source = inspect.getsource(evaluators)
    for forbidden in ("eval(", "exec(", "compile(", "__import__", "subprocess", "importlib"):
        assert forbidden not in source, f"{forbidden} appears in the evaluator registry"
