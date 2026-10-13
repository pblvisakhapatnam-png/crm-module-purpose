"""The evidence contract: negative outcomes are FIRST-CLASS.

PF-1A-E2-A section 16.

    "It returned DENY with a reason code" is not sufficient evidence and is a
    blocking defect.

A resolution result retains deterministic evidence sufficient to prove exactly
why it allowed, denied or failed closed, and what authoritative state was
used. A denial must be as explainable as an approval.

FOUR COLLECTIONS plus a result header:

    16.1  result header, including `established_state` - what WAS established
          and the exact stage at which evaluation stopped. This is what makes
          a DENY + RESOLVED with ZERO complete paths explainable.
    16.2  qualifying paths            all four object/version pairs
    16.3  complete nonqualifying paths  the SAME structure, plus the decisive
                                        path-level reason
    16.4  partial / failed evaluations  what exists, what does not, the exact
                                        failed stage, the deterministic reason

NEVER FABRICATE. A partial evaluation records what exists and NAMES what does
not; it must not emit placeholder, null-filled or guessed object/version pairs
that a later reader could mistake for established state. Every candidate the
kernel touched is accounted for in exactly one of the three collections.

NEVER INCLUDED: passwords, password hashes, tokens, session identifiers, any
authentication secret, or any provider-specific identifier or field.

RECORDED TIME IS LABELLED AS SUCH. `published_at` and `retracted_at` are
carried as provenance evidence under names that say RECORDED, never as
effective time, so a later reader cannot mistake one for the other (11.8.4).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime

from app.modules.authorization.business_authority.contract import (
    REASON_CODE_RANK,
    STAGE_RANK,
)
from app.modules.authorization.business_authority.defects import DefectRecord
from app.modules.authorization.business_authority.domain import ObjectVersionRef


@dataclass(frozen=True)
class GrantEligibilityEvaluation:
    """The THREE conditions of section 8.2, reported SEPARATELY.

    They must never be merged into one predicate, because a caller of the
    evidence contract must be able to see which of the three failed. INACTIVE
    and INEFFECTIVE are different conditions with different reason codes for
    every family, and neither is ever reported as the other.
    """

    lineage_valid: bool
    effective_at_as_of: bool
    active_flag: bool | None


@dataclass(frozen=True)
class ObjectEvidence:
    """One established (object_id, object_version) pair and its provenance."""

    ref: ObjectVersionRef
    publication_reference_type: str | None
    publication_reference_id: str | None
    recorded_published_at: datetime | None
    recorded_retracted_at_of_participating_assertions: tuple[datetime, ...]
    grant_eligibility: GrantEligibilityEvaluation


@dataclass(frozen=True)
class HrEvidence:
    """Canonical HR/organisation evidence for one path.

    Only canonical identities and the canonical freshness indicator. No
    provider identifier, no provider field name, no raw provider timestamp.
    """

    person_id: str
    # OPTIONAL because a failure at S2 has already established the canonical
    # person but not yet the employment state, and that partially-established
    # HR state is still required evidence (16.4, correction FU-2).
    employment_state_version_id: str | None = None
    position_version_id: str | None = None
    incumbency_id: str | None = None
    org_unit_version_ids: tuple[str, ...] = ()
    canonical_snapshot_at_values: tuple[datetime, ...] = ()


@dataclass(frozen=True)
class ScopeEvidence:
    """Each operand's OWN evaluation plus the composed outcome, so a reviewer
    can see which operand was decisive (12.4)."""

    rule_scope_type: str | None
    rule_scope_id: str | None
    rule_operand_satisfied: bool
    assignment_scope_type: str | None
    assignment_scope_id: str | None
    assignment_operand_satisfied: bool
    composed_satisfied: bool
    detail: str = ""


@dataclass(frozen=True)
class ParameterEvidence:
    """The evaluator type and the decisive comparison actually performed."""

    evaluator_type: str | None
    satisfied: bool
    decisive_comparison: str = ""


@dataclass(frozen=True)
class PathEvidence:
    """A COMPLETE candidate path: all four object/version pairs.

    16.2 (qualifying) and 16.3 (complete nonqualifying) share this structure
    exactly. Omitting any one of the four pairs is a blocking defect; that is
    ORA-001's requirement as corrected by the authority configuration model.

    `decisive_nonqualification_reason` is set only on a 16.3 path, and is what
    allows a scope denial or a parameter denial to be PROVED rather than
    merely asserted.
    """

    business_authority_role: ObjectEvidence
    business_authority: ObjectEvidence
    business_authority_rule: ObjectEvidence
    business_authority_assignment: ObjectEvidence
    hr_evidence: HrEvidence
    scope_evaluation: ScopeEvidence
    parameter_evaluation: ParameterEvidence
    decisive_nonqualification_reason: str | None = None
    # THE BOUNDED-FALLBACK EXPLANATION ON A COMPLETE PATH (correction FU-5).
    #
    # Mandatory when `decisive_nonqualification_reason` is
    # OTHER_NONQUALIFICATION, and empty otherwise. It is the same kind of
    # short, deterministic, kernel-generated string the partial-evaluation
    # record carries: a fixed implementation-owned template over canonical
    # identifiers, stable for identical canonical input, never provider or
    # user prose.
    #
    # It is AUDIT EVIDENCE ONLY. It is deliberately absent from
    # `path_sort_key`, so it takes no part in candidate ordering, in result
    # selection, or in whether the path qualifies.
    nonqualification_explanation: str = ""

    @property
    def path_sort_key(self) -> tuple[str, ...]:
        """The 15.4 total order, computed from canonical identifiers only.

        Never depends on provider order, SQL row order, iteration order,
        traversal direction or concurrency, and never selects an arbitrary
        "first" path when more than one qualifies.
        """

        return (
            self.business_authority_role.ref.object_id,
            self.business_authority_role.ref.object_version,
            self.business_authority.ref.object_id,
            self.business_authority.ref.object_version,
            self.business_authority_rule.ref.object_id,
            self.business_authority_rule.ref.object_version,
            self.business_authority_assignment.ref.object_id,
            self.business_authority_assignment.ref.object_version,
        )

    @property
    def candidate_key(self) -> tuple[str, ...]:
        return self.path_sort_key


@dataclass(frozen=True)
class PartialEvaluation:
    """A candidate that could not be completed, or an early fail-closed defect.

    Carries every successfully established evidence item IN THE ORDER
    ESTABLISHED, the exact stage that failed or was absent, and the
    deterministic reason. It never carries a fabricated pair.

    PROGRESSIVE, CANDIDATE-SCOPED ACCOUNTING (correction FU-2). Before this
    correction the record retained only the requested Business Authority, even
    when the Rule, Role and Assignment for that candidate had all been
    successfully established before a later stage failed. That collapsed real,
    established state and violated 16.4. Every item below is what was ACTUALLY
    established for THIS candidate at the moment it failed:

        established_objects   the object/version pairs, WITH their per-object
                              active/effective evaluations, in establishment
                              order (requested Authority, Rule, Role,
                              Assignment - as far as the candidate got);
        hr_evidence           the canonical person, employment state, Position,
                              Incumbency, organisation-unit ancestry hops and
                              canonical snapshots relied upon so far;
        scope_evaluation      the scope operands already evaluated;
        parameter_evaluation  the evaluator state already established.

    Nothing here is ever fabricated: an object that was not established simply
    does not appear, and no placeholder pair is emitted.
    """

    established_objects: tuple[ObjectEvidence, ...]
    last_stage_reached: str
    reason_code: str
    is_defect: bool
    detail: str = ""
    # EVERY defect that ended THIS candidate, not merely the first (correction
    # C2-4). One malformed lineage can violate several structural rules at
    # once, and the earlier shape - one partial per defect - split a single
    # logical candidate across several evidence items. That made
    # `partial_evaluations` read as though more candidates had been examined
    # than actually were, and it forced the candidate key to be padded with the
    # reason code and detail text merely to keep those duplicates distinct.
    #
    # The defects themselves are unchanged and are still reported individually
    # in `ordered_defects` under the ONE total order of 15.5; this collection
    # only groups them by the candidate they ended.
    defects: tuple[DefectRecord, ...] = ()
    candidate_key: tuple[str, ...] = ()
    hr_evidence: HrEvidence | None = None
    scope_evaluation: ScopeEvidence | None = None
    parameter_evaluation: ParameterEvidence | None = None
    # THE BOUNDED-FALLBACK EXPLANATION (owner clarification, correction C1).
    #
    # Populated only for OTHER_NONQUALIFICATION, and mandatory there. It is a
    # SHORT, DETERMINISTIC, KERNEL-GENERATED string built from a fixed
    # implementation-owned template over canonical identifiers, so that the
    # exact condition is legible without a new permanent reason code.
    #
    # It never comes from provider text, user text, an exception message or any
    # arbitrary external prose; it is stable for the same canonical input; and
    # it deliberately does NOT appear in `sort_key`, so it can never
    # participate in result selection or in evidence ordering.
    nonqualification_explanation: str = ""

    @property
    def defect(self) -> DefectRecord | None:
        """The DECISIVE defect for this candidate: the first one recorded.

        Derived from `defects` rather than stored beside it, so the two can
        never disagree about which defect decided the candidate (correction
        C2-4). `sort_key` and the result-level reason both read this, and both
        continue to see exactly what they saw before the grouping change.
        """

        return self.defects[0] if self.defects else None

    @property
    def established(self) -> tuple[ObjectVersionRef, ...]:
        """The established object/version pairs, in establishment order.

        Derived from `established_objects` rather than stored alongside it, so
        the two can never disagree about what was established.
        """

        return tuple(evidence.ref for evidence in self.established_objects)

    @property
    def sort_key(self) -> tuple:
        """16.5 ordering.

        Defect items sort by the ONE total defect order of 15.5 - the
        identical canonical sort key used to select `result_level_reason`, so
        the first item here and the result-level reason can never disagree
        about which defect is first.

        A partial evaluation that ended in a NONQUALIFICATION rather than a
        defect sorts AFTER every defect item, ordered by
        (last_stage_reached ASC, then the established canonical identifiers in
        the 15.4 field order with unestablished fields sorting last, then
        reason_code_rank).
        """

        if self.is_defect and self.defect is not None:
            return (0,) + self.defect.sort_key
        return (
            1,
            STAGE_RANK[self.last_stage_reached],
            tuple(
                f"{ref.object_id}:{ref.object_version}" for ref in self.established
            ),
            REASON_CODE_RANK[self.reason_code],
            self.detail,
        )


@dataclass(frozen=True)
class EstablishedState:
    """16.1 - what WAS successfully established, and where evaluation stopped.

    This is what makes a `DENY + RESOLVED` with ZERO complete paths
    explainable: it records what was established and therefore why no grant
    path could exist.
    """

    person_id: str | None = None
    employment_state_version_id: str | None = None
    employment_status: str | None = None
    requested_authority: ObjectVersionRef | None = None
    requested_authority_eligibility: GrantEligibilityEvaluation | None = None
    rules_discovered: int = 0
    roles_referenced: int = 0
    assignments_discovered: int = 0
    complete_paths_evaluated: int = 0
    canonical_snapshot_at_values: tuple[datetime, ...] = ()
    last_stage_reached: str = "S0"


@dataclass(frozen=True)
class EvaluatedBusinessContext:
    """The business context AS EVALUATED - the scope and the declared facts
    actually used (16.1)."""

    scope_type: str | None
    scope_id: str | None
    declared_fact_names: tuple[str, ...]


@dataclass(frozen=True)
class AuthorityResolutionResult:
    """The complete, immutable answer plus its evidence.

    `outcome` and `resolution_status` are two ORTHOGONAL dimensions and are
    never collapsed into a boolean. ALLOW is only ever valid with RESOLVED;
    FAIL_CLOSED always implies DENY.

    `result_level_reason` is the empty string on an ALLOW, and only there.
    Section 14 defines result-level reasons for DENY + RESOLVED (14.2) and for
    DENY + FAIL_CLOSED (14.3) and defines NONE for a grant - the reason a
    grant happened is the qualifying paths themselves, which 16.2 requires in
    full. The empty value is therefore a deliberate absence, not an omission,
    and no reason code was invented to fill it.
    """

    outcome: str
    resolution_status: str
    result_level_reason: str
    authority_code: str
    as_of: datetime
    actor_user_public_id: str
    established_state: EstablishedState
    business_context: EvaluatedBusinessContext
    qualifying_paths: tuple[PathEvidence, ...] = ()
    complete_nonqualifying_paths: tuple[PathEvidence, ...] = ()
    partial_evaluations: tuple[PartialEvaluation, ...] = ()
    ordered_defects: tuple[DefectRecord, ...] = field(default=(), repr=False)


def order_paths(paths: tuple[PathEvidence, ...]) -> tuple[PathEvidence, ...]:
    return tuple(sorted(paths, key=lambda path: path.path_sort_key))


def order_partials(partials: tuple[PartialEvaluation, ...]) -> tuple[PartialEvaluation, ...]:
    return tuple(sorted(partials, key=lambda partial: partial.sort_key))


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def serialize_result(result: AuthorityResolutionResult) -> str:
    """A canonical, byte-stable serialization of a result and its evidence.

    Used by the determinism tests: shuffling every provider's return order,
    reversing traversal direction and repeating a run must all produce
    BYTE-IDENTICAL output. `sort_keys=False` is deliberate - the collections
    are already in their contract order, and re-sorting keys here would hide a
    real ordering regression rather than expose it.
    """

    payload = asdict(result)
    # `ordered_defects` duplicates information already present in the
    # partial-evaluation collection and carries no additional evidence, so it
    # is excluded from the canonical form rather than serialized twice.
    payload.pop("ordered_defects", None)
    return json.dumps(payload, default=_json_default, sort_keys=False, separators=(",", ":"))
