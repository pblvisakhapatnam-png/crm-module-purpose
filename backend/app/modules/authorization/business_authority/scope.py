"""Scope predicates and INTERSECTION composition.

PF-1A-E2-A sections 12.3 and 12.4.

E2-A defines a bounded, deterministic scope mechanism. It does NOT invent a
PBL organisation hierarchy: ancestry is resolved ONLY through the
provider-neutral canonical organisation reference (`get_org_unit`,
`parent_org_unit_id`), at the SAME single `as_of` for every hop (attack
surface 22).

SHAPE OF AN OPERAND, recorded because the contract states the predicate and
the identity in one phrase. A stored operand is a pair:

    scope_type   the PREDICATE - GLOBAL, EXACT or ANCESTRY. A value outside
                 those three is a scope semantics the evaluator does not
                 support and fails closed (SCOPE_SEMANTICS_UNSUPPORTED). It is
                 NEVER treated as GLOBAL and never silently ignored.
    scope_id     the CANONICAL scope identity the predicate is about - an
                 `org_unit_id`. A raw provider identifier is never a scope_id.

The business context supplies the same pair for the request being authorized.
`SCOPE_KIND_ORG_UNIT` is the one canonical scope kind authorization consumes
in E2-A; a context naming any other kind is likewise unsupported semantics
rather than a permissive match.

COMPOSITION IS INTERSECTION, NEVER UNION (12.4). Both operands must be
satisfied; there is no widening and no "either will do". GLOBAL is the
unconstrained TOP element for its own operand, so GLOBAL INTERSECT X = X.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Final

from app.modules.authorization.business_authority.contract import (
    ASSIGNMENT_SCOPE_NOT_MATCHED,
    MAX_ANCESTRY_DEPTH,
    ORG_HIERARCHY_UNRESOLVABLE,
    ORG_UNIT_STATE_AMBIGUOUS,
    ORG_UNIT_STATE_MISSING,
    RULE_SCOPE_NOT_MATCHED,
    SCOPE_ANCESTRY,
    SCOPE_COMPOSITION_NOT_SATISFIED,
    SCOPE_CONTEXT_MISSING,
    SCOPE_EXACT,
    SCOPE_GLOBAL,
    SCOPE_SEMANTICS_UNSUPPORTED,
    SUPPORTED_SCOPE_TYPES,
)
from app.modules.hr_reference.contract import (
    HR_LOOKUP_AMBIGUOUS,
    HR_LOOKUP_MISSING,
    HR_LOOKUP_OK,
    HR_LOOKUP_STALE,
    HR_LOOKUP_STATUSES,
    HR_LOOKUP_UNAVAILABLE,
    OrgUnitVersionReference,
    is_conforming_instant,
    is_snapshot_stale,
)
from app.modules.hr_reference.ports import CanonicalHrReferencePort

SCOPE_KIND_ORG_UNIT: Final = "ORG_UNIT"

# Operand roles, used only to choose the correct path-level reason code.
OPERAND_RULE: Final = "RULE"
OPERAND_ASSIGNMENT: Final = "ASSIGNMENT"

_NOT_MATCHED_REASON = {
    OPERAND_RULE: RULE_SCOPE_NOT_MATCHED,
    OPERAND_ASSIGNMENT: ASSIGNMENT_SCOPE_NOT_MATCHED,
}


@dataclass(frozen=True)
class ScopeOperandResult:
    """The evaluation of ONE scope operand.

    Three genuinely different answers, which must never be merged:
      satisfied            the operand is met;
      not-matched          a well-formed, SUPPORTED operand that simply does
                           not match - ordinary nonqualification, not a defect;
      defect               unsupported semantics, missing required context, or
                           an unresolvable organisation relationship - fail
                           closed.
    """

    satisfied: bool
    nonqualification_reason: str | None = None
    defect_reason: str | None = None
    detail: str = ""
    org_unit_versions_traversed: tuple[OrgUnitVersionReference, ...] = ()
    # The operand's own published values, carried so the composition can apply
    # the 12.4 structural rule about two EXACT operands naming different
    # canonical scopes, and so the evidence can show what each operand was.
    scope_type: str | None = None
    scope_id: str | None = None

    @property
    def is_defect(self) -> bool:
        return self.defect_reason is not None


@dataclass(frozen=True)
class ScopeCompositionResult:
    """The composed result over the Rule operand and the Assignment operand."""

    satisfied: bool
    rule_operand: ScopeOperandResult
    assignment_operand: ScopeOperandResult
    nonqualification_reason: str | None = None
    defect_reason: str | None = None
    detail: str = ""

    @property
    def is_defect(self) -> bool:
        return self.defect_reason is not None


_HR_DEFECT_FOR_ORG_UNIT = {
    HR_LOOKUP_MISSING: ORG_UNIT_STATE_MISSING,
    HR_LOOKUP_AMBIGUOUS: ORG_UNIT_STATE_AMBIGUOUS,
}


def _org_unit_lookup_defect(status: str) -> str:
    # UNAVAILABLE and STALE are reported through the HR-reference codes by the
    # caller; here only MISSING and AMBIGUOUS are org-unit-specific.
    return _HR_DEFECT_FOR_ORG_UNIT.get(status, ORG_HIERARCHY_UNRESOLVABLE)


@dataclass(frozen=True)
class _OrgUnitAnswer:
    """One fully validated canonical organisation unit, or the defect instead."""

    reference: OrgUnitVersionReference | None = None
    defect_reason: str | None = None
    detail: str = ""


def _resolve_org_unit(
    *,
    org_unit_id: str,
    hr_port: CanonicalHrReferencePort,
    as_of: datetime,
    hr_unavailable_reason: str,
    hr_stale_reason: str,
    staleness_threshold_seconds: int | None,
) -> _OrgUnitAnswer:
    """THE ONE PLACE an organisation unit becomes authoritative state.

    Extracted by correction C2-1. The validation sequence below - contract
    status, then value type, then IDENTITY BINDING, then FRESHNESS - previously
    existed only inside the upward traversal loop, so it governed every unit
    the walk PASSED THROUGH but not the ancestor the walk TERMINATED ON. A
    child unit could therefore satisfy an ancestry operand by merely DECLARING
    the operand's scope as its `parent_org_unit_id`, while that ancestor had no
    canonical record at all - missing, unavailable, ambiguous, stale, or
    answered by a response about a different unit. That is a fail-open: an
    unverifiable claim by the subordinate granted authority over the superior.

    A declared parent identifier is a CLAIM. It becomes authoritative state
    only once the canonical reference confirms it, at the SAME single `as_of`
    and under the SAME supplied staleness threshold as every other hop.

    The order matters and is deliberate. Identity is checked BEFORE freshness
    because a response that is not about the requested unit has no meaningful
    freshness to assess, and the foreign identity is never echoed outward.
    """

    lookup = hr_port.get_org_unit(org_unit_id, as_of)

    # A status OUTSIDE the closed lookup vocabulary is not authoritative state,
    # and is never trusted merely because a value is attached to it. It is a
    # provider-contract failure, so it takes the existing provider-failure
    # classification rather than a new reason code.
    if lookup.status not in HR_LOOKUP_STATUSES:
        return _OrgUnitAnswer(
            defect_reason=hr_unavailable_reason,
            detail="the canonical organisation reference returned a non-contract status",
        )
    if lookup.status == HR_LOOKUP_UNAVAILABLE:
        return _OrgUnitAnswer(
            defect_reason=hr_unavailable_reason,
            detail="the canonical organisation reference is unavailable",
        )
    if lookup.status == HR_LOOKUP_STALE:
        return _OrgUnitAnswer(
            defect_reason=hr_stale_reason,
            detail="the canonical organisation snapshot is stale",
        )
    if lookup.status != HR_LOOKUP_OK:
        return _OrgUnitAnswer(
            defect_reason=_org_unit_lookup_defect(lookup.status),
            detail=(
                f"the canonical response for organisation unit {org_unit_id} reported "
                f"{lookup.status}"
            ),
        )

    org_unit = lookup.value
    if not isinstance(org_unit, OrgUnitVersionReference):
        return _OrgUnitAnswer(
            defect_reason=hr_unavailable_reason,
            detail=f"organisation unit {org_unit_id} returned no canonical version",
        )

    # IDENTITY BINDING (correction FU-1). A response identifying a DIFFERENT
    # organisation unit must never stand in for this one: following it would
    # walk, or terminate on, a chain the request never asked about.
    if org_unit.org_unit_id != org_unit_id:
        return _OrgUnitAnswer(
            defect_reason=hr_unavailable_reason,
            detail=(
                f"the canonical response for organisation unit {org_unit_id} identified a "
                "different organisation unit"
            ),
        )

    # A non-conforming snapshot instant cannot be compared against the
    # authorization instant at all (correction C2-2), so the freshness question
    # below is unanswerable and the state is not established.
    if not is_conforming_instant(org_unit.canonical_snapshot_at):
        return _OrgUnitAnswer(
            defect_reason=hr_unavailable_reason,
            detail=(
                f"the canonical response for organisation unit {org_unit_id} carried a "
                "snapshot that is not a timezone-aware instant"
            ),
        )

    # EVERY unit actually relied upon is checked against the SAME supplied
    # threshold and the SAME authoritative as_of. A stale hop half way up an
    # ancestry chain - or a stale TERMINATING ancestor - is exactly as unusable
    # as a stale employment state.
    if is_snapshot_stale(org_unit.canonical_snapshot_at, as_of, staleness_threshold_seconds):
        return _OrgUnitAnswer(
            defect_reason=hr_stale_reason,
            detail=(
                f"the canonical snapshot for organisation unit {org_unit_id} is older than "
                "the configured staleness threshold"
            ),
        )

    return _OrgUnitAnswer(reference=org_unit)


def evaluate_operand(
    *,
    operand_role: str,
    scope_type: str | None,
    scope_id: str | None,
    context_scope_type: str | None,
    context_scope_id: str | None,
    hr_port: CanonicalHrReferencePort | None,
    as_of: datetime,
    hr_unavailable_reason: str,
    hr_stale_reason: str,
    staleness_threshold_seconds: int | None = None,
) -> ScopeOperandResult:
    """Evaluate one operand against the authoritative request context."""

    result = _evaluate_operand(
        operand_role=operand_role,
        scope_type=scope_type,
        scope_id=scope_id,
        context_scope_type=context_scope_type,
        context_scope_id=context_scope_id,
        hr_port=hr_port,
        as_of=as_of,
        hr_unavailable_reason=hr_unavailable_reason,
        hr_stale_reason=hr_stale_reason,
        staleness_threshold_seconds=staleness_threshold_seconds,
    )
    return replace(result, scope_type=scope_type, scope_id=scope_id)


def _evaluate_operand(
    *,
    operand_role: str,
    scope_type: str | None,
    scope_id: str | None,
    context_scope_type: str | None,
    context_scope_id: str | None,
    hr_port: CanonicalHrReferencePort | None,
    as_of: datetime,
    hr_unavailable_reason: str,
    hr_stale_reason: str,
    staleness_threshold_seconds: int | None,
) -> ScopeOperandResult:
    if scope_type not in SUPPORTED_SCOPE_TYPES:
        return ScopeOperandResult(
            satisfied=False,
            defect_reason=SCOPE_SEMANTICS_UNSUPPORTED,
            detail=f"scope_type {scope_type!r} is not a supported scope semantics",
        )

    if scope_type == SCOPE_GLOBAL:
        # GLOBAL is the unconstrained TOP element for this operand. It is
        # satisfied for every applicable business context, and it never
        # overrides a narrower operand on the other side of the intersection.
        return ScopeOperandResult(satisfied=True)

    # A non-GLOBAL operand needs a canonical scope identity of its own.
    if not scope_id:
        return ScopeOperandResult(
            satisfied=False,
            defect_reason=SCOPE_SEMANTICS_UNSUPPORTED,
            detail=f"a {scope_type} operand carries no canonical scope_id",
        )

    # A business context that does not supply a scope required by a non-GLOBAL
    # operand FAILS CLOSED rather than matching permissively.
    if not context_scope_id or not context_scope_type:
        return ScopeOperandResult(
            satisfied=False,
            defect_reason=SCOPE_CONTEXT_MISSING,
            detail=f"a {scope_type} operand requires a canonical scope the context does not supply",
        )

    if context_scope_type != SCOPE_KIND_ORG_UNIT:
        return ScopeOperandResult(
            satisfied=False,
            defect_reason=SCOPE_SEMANTICS_UNSUPPORTED,
            detail=f"context scope kind {context_scope_type!r} is not supported",
        )

    if scope_type == SCOPE_EXACT:
        if context_scope_id == scope_id:
            return ScopeOperandResult(satisfied=True)
        return ScopeOperandResult(
            satisfied=False,
            nonqualification_reason=_NOT_MATCHED_REASON[operand_role],
            detail="exact scope operand does not match the request context",
        )

    if scope_type != SCOPE_ANCESTRY:
        # Unreachable while SUPPORTED_SCOPE_TYPES holds exactly three values,
        # and retained deliberately so that adding a fourth predicate without
        # implementing it fails CLOSED here rather than falling through into
        # the ancestry branch and being evaluated as something it is not.
        return ScopeOperandResult(
            satisfied=False,
            defect_reason=SCOPE_SEMANTICS_UNSUPPORTED,
            detail=f"scope_type {scope_type!r} has no implemented predicate",
        )

    # SCOPE_ANCESTRY. Satisfied when the context's canonical scope IS the
    # operand's scope, or a DESCENDANT of it. Traversal walks upward from the
    # context toward the operand.
    if hr_port is None:
        return ScopeOperandResult(
            satisfied=False,
            defect_reason=ORG_HIERARCHY_UNRESOLVABLE,
            detail="ancestry evaluation requires the canonical organisation reference",
        )

    traversed: list[OrgUnitVersionReference] = []

    def resolved(org_unit_id: str) -> _OrgUnitAnswer:
        return _resolve_org_unit(
            org_unit_id=org_unit_id,
            hr_port=hr_port,
            as_of=as_of,
            hr_unavailable_reason=hr_unavailable_reason,
            hr_stale_reason=hr_stale_reason,
            staleness_threshold_seconds=staleness_threshold_seconds,
        )

    def failure(answer: _OrgUnitAnswer) -> ScopeOperandResult:
        return ScopeOperandResult(
            satisfied=False,
            defect_reason=answer.defect_reason,
            detail=answer.detail,
            org_unit_versions_traversed=tuple(traversed),
        )

    def satisfied_at(target: OrgUnitVersionReference) -> ScopeOperandResult:
        # The terminating ancestor is retained in the operand's evidence exactly
        # like every unit the walk passed through, so the record shows WHICH
        # canonical units the grant actually rested on (correction C2-1).
        if all(unit.org_unit_id != target.org_unit_id for unit in traversed):
            traversed.append(target)
        return ScopeOperandResult(satisfied=True, org_unit_versions_traversed=tuple(traversed))

    # THE SELF-MATCH IS A TERMINATION TOO (correction C2-1). "The context IS the
    # operand's scope" was previously answered from the two identifiers alone,
    # so an ancestry operand naming a scope with no canonical record could be
    # satisfied by a context asserting that same identifier. Identifier equality
    # is not evidence that the scope exists; the canonical reference is.
    if context_scope_id == scope_id:
        answer = resolved(context_scope_id)
        if answer.reference is None:
            return failure(answer)
        return satisfied_at(answer.reference)

    visited: set[str] = {context_scope_id}
    current = context_scope_id

    for _ in range(MAX_ANCESTRY_DEPTH):
        answer = resolved(current)
        if answer.reference is None:
            return failure(answer)
        org_unit = answer.reference

        traversed.append(org_unit)
        parent = org_unit.parent_org_unit_id

        if parent is None:
            # The chain ended at a root without reaching the operand's scope.
            # That is an ordinary non-match, not a defect: the hierarchy was
            # fully resolvable and simply does not contain the operand above
            # this context.
            return ScopeOperandResult(
                satisfied=False,
                nonqualification_reason=_NOT_MATCHED_REASON[operand_role],
                detail="ancestry operand is not an ancestor of the request context",
                org_unit_versions_traversed=tuple(traversed),
            )

        if parent == scope_id:
            # A DECLARED parent is a CLAIM by the subordinate unit, not
            # authoritative state (correction C2-1). It grants nothing until the
            # canonical reference confirms the ancestor itself - present,
            # unambiguous, about the unit asked for, and fresh.
            target = resolved(parent)
            if target.reference is None:
                return failure(target)
            return satisfied_at(target.reference)

        if parent in visited:
            return ScopeOperandResult(
                satisfied=False,
                defect_reason=ORG_HIERARCHY_UNRESOLVABLE,
                detail="the canonical organisation hierarchy contains a cycle",
                org_unit_versions_traversed=tuple(traversed),
            )

        visited.add(parent)
        current = parent

    return ScopeOperandResult(
        satisfied=False,
        defect_reason=ORG_HIERARCHY_UNRESOLVABLE,
        detail=f"ancestry traversal exceeded the bounded depth of {MAX_ANCESTRY_DEPTH}",
        org_unit_versions_traversed=tuple(traversed),
    )


def compose(
    rule_operand: ScopeOperandResult, assignment_operand: ScopeOperandResult
) -> ScopeCompositionResult:
    """Compose the two operands by INTERSECTION (12.4).

    A defect on either operand decides the composition, because an
    unresolvable or unsupported operand is not a non-match: it is a state the
    kernel could not establish. Otherwise both must be satisfied.

    Two EXACT operands naming different canonical scopes can never both be
    satisfied by one context. That is ordinary nonqualification
    (SCOPE_COMPOSITION_NOT_SATISFIED), not a defect and not a configuration
    error.
    """

    if rule_operand.is_defect:
        return ScopeCompositionResult(
            satisfied=False,
            rule_operand=rule_operand,
            assignment_operand=assignment_operand,
            defect_reason=rule_operand.defect_reason,
            detail=rule_operand.detail,
        )
    if assignment_operand.is_defect:
        return ScopeCompositionResult(
            satisfied=False,
            rule_operand=rule_operand,
            assignment_operand=assignment_operand,
            defect_reason=assignment_operand.defect_reason,
            detail=assignment_operand.detail,
        )

    if rule_operand.satisfied and assignment_operand.satisfied:
        return ScopeCompositionResult(
            satisfied=True,
            rule_operand=rule_operand,
            assignment_operand=assignment_operand,
        )

    # Two EXACT operands naming DIFFERENT canonical scopes can never both be
    # satisfied by one context, whichever of the two the context happens to
    # match. 12.4 names that structural case explicitly, so it reports the
    # composition reason rather than one operand's own non-match.
    both_exact_and_different = (
        rule_operand.scope_type == SCOPE_EXACT
        and assignment_operand.scope_type == SCOPE_EXACT
        and rule_operand.scope_id != assignment_operand.scope_id
    )
    if both_exact_and_different:
        return ScopeCompositionResult(
            satisfied=False,
            rule_operand=rule_operand,
            assignment_operand=assignment_operand,
            nonqualification_reason=SCOPE_COMPOSITION_NOT_SATISFIED,
            detail="the rule and assignment operands name different exact canonical scopes",
        )

    # Exactly one operand failed: report THAT operand's own reason, so the
    # evidence shows which operand was decisive. Both failed: the composition
    # itself is what could not be satisfied.
    if rule_operand.satisfied != assignment_operand.satisfied:
        decisive = assignment_operand if rule_operand.satisfied else rule_operand
        return ScopeCompositionResult(
            satisfied=False,
            rule_operand=rule_operand,
            assignment_operand=assignment_operand,
            nonqualification_reason=decisive.nonqualification_reason,
            detail=decisive.detail,
        )

    return ScopeCompositionResult(
        satisfied=False,
        rule_operand=rule_operand,
        assignment_operand=assignment_operand,
        nonqualification_reason=SCOPE_COMPOSITION_NOT_SATISFIED,
        detail="neither scope operand is satisfied by this business context",
    )
