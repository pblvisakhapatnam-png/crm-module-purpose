"""The PURE governed-configuration policy: risk, independence, duplication (PF-1A-E3).

No clock, no session, no provider, no SQLAlchemy: it takes a proposal plus an already-loaded
context and returns a verdict, so every rule below is directly and deterministically testable
and the service layer cannot quietly acquire a second copy of one.

THREE DIRECTIONS OF CONSERVATISM, EACH DELIBERATE:

  PROTECTION IS OVER-INCLUSIVE. An object counts as protected if ANY non-retracted published
    version asserts `is_protected_meta_authority`, or if the proposal itself asserts it.
    CLEARING the flag therefore does not make the clearing change ordinary, which is exactly
    what ADR-033 requires: setting OR clearing protection is itself protected.

  PRIVILEGE INCREASE IS ASSUMED UNLESS PROVEN OTHERWISE. Scope and threshold semantics belong
    to the PF-1A-E2-A kernel, so no narrowing of THOSE is inferred here. Only two cases are
    provably non-increasing: a DEACTIVATE, and an UPDATE whose published content is
    byte-identical AND whose declared temporal scope is unchanged or strictly narrowed. The
    temporal half is not decoration: a change that alters nothing but moves `effective_from`
    earlier, pushes `declared_effective_to` later, or removes a declared end entirely, grants
    authority over time it did not previously cover, and is a privilege increase however
    identical its payload looks.

  LINKAGE USES THE STATE THE E2 KERNEL SAYS IS CURRENT, not "ever" and not "most recently
    written". An assignment that was deactivated must stop making its former holder
    self-affected, or ordinary administration would become permanently two-person for anyone who
    ever held anything - but a version that is genuinely EFFECTIVE now must never be erased by a
    later-published successor that is future-dated, inactive or reassigned.

PRIVILEGE RISK AND PUBLICATION VALIDITY ARE TWO QUESTIONS, AND NEITHER ANSWERS THE OTHER.

"Does this change grant more than what it supersedes?" is `classify_risk`, and it decides how many
people must agree. "Could the resulting immutable lineage be published at all?" is
`prospective_publication_defects`, and it decides whether anything may be written. A proposal can
legitimately answer NO to the first and still be refused by the second: PF-1A-E3's UPDATE APPENDS a
version rather than retracting and republishing, so a predecessor carrying a finite
`declared_effective_to` stays asserted beside the new version, and a NARROWER new interval that
starts before that declared end is read by PF-1A-E2-A 11.4 as an EXPLICIT OVERLAP. The correct
response is to refuse the publication, NOT to reclassify every narrowing as a privilege increase -
that would demand a second person to REDUCE someone's own authority, which is conservative in the
useless direction ADR-033 warns about, and would still not stop the defective append.

THE AUTHORITY GRAPH IS DERIVED BY THE UNCHANGED PF-1A-E2-A KERNEL, NOT BY THIS MODULE.

An earlier revision ranked rows by the store's physical append order and treated "the latest
non-retracted row" as the current authority graph. That is a second, quieter notion of currency
which disagrees with the kernel's in both directions, and the disagreement is exploitable rather
than academic: publish a future-effective inactive successor to your own assignment, and a
shortcut that reads only the latest row concludes you hold nothing, so your own privilege
increase stops being self-affecting and becomes a single-person change. The same shortcut lets a
future-effective rule successor hide a protected meta-authority linkage that is live today.

`derive_effective_state` therefore hands COMPLETE lineage material - every version and every
retraction assertion, unfiltered - to `material.check_material_well_formed` and then to
`lineage.evaluate_lineage`, and reads the answer back:

    validate retraction / correction / provenance assertions   (kernel)
    derive the CURRENT ASSERTED lineage                        (kernel)
    derive asserted intervals / closure                        (kernel)
    select the SINGLE version effective at as_of               (kernel)
    then apply active_flag / grant eligibility                 (here)

Anything the kernel cannot establish - a contradictory lineage, an ambiguous version at as_of,
invalid provenance, ill-formed material - is reported as UNRESOLVED and fails the whole governed
action closed. There is deliberately no local re-implementation of effectiveness, closure,
retraction validity or correction precedence; two copies would drift, and the copy that drifts
silently is the one that decides who may change authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from app.modules.authorization.business_authority.configuration_contract import (
    AUTHORITY_CONTEXT_UNAVAILABLE,
    AUTHORIZATION_CONTEXT_DRIFTED,
    AUTHORIZATION_EVIDENCE_UNVERIFIABLE,
    AUTHORIZATION_MISSING,
    AUTHORIZER_NOT_ELIGIBLE,
    AUTHORIZER_NO_LONGER_ELIGIBLE,
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
    CHANGE_DEACTIVATE,
    CHANGE_UPDATE,
    DUPLICATE_ACTIVE_ASSIGNMENT,
    LINEAGE_PRECONDITION_FAILED,
    OUTCOME_PERMITTED,
    OUTCOME_RECORDED,
    OUTCOME_REFUSED,
    PUBLICATION_LINEAGE_INVALID,
    PUBLICATION_TIMESTAMP_NOT_MONOTONIC,
    REFERENCED_OBJECT_MISSING,
    RISK_INCREASED_SINCE_AUTHORIZATION,
    SAME_PERSON_AUTHORIZATION_FORBIDDEN,
    STAGE_ACTIVATION,
    STAGE_AUTHORIZATION,
    STAGE_PROPOSAL,
)
from app.modules.authorization.business_authority.configuration_domain import (
    AllocationAnchor,
    AuthorityContext,
    ConfigurationChangeProposal,
    EffectiveConfigurationState,
    GovernanceEvaluation,
    PublishedRow,
    RetractionRow,
    RiskClassification,
)
from app.modules.authorization.business_authority.domain import (
    LineageMaterial,
    PublishedObjectVersion,
    RetractionAssertion,
)
from app.modules.authorization.business_authority.lineage import evaluate_lineage
from app.modules.authorization.business_authority.material import check_material_well_formed
from app.modules.hr_reference.contract import is_utc_normalized_instant

_ASSIGNMENT_KEY = (
    "business_authority_role_object_id",
    "person_id",
    "position_id",
    "scope_type",
    "scope_id",
)

# The fail-closed channel entry for one object whose lineage could not be established.
LINEAGE_UNRESOLVED_PREFIX = "LINEAGE"


def canonical_json(value: Any) -> str:
    """A byte-stable rendering, used for fingerprints and payload equality."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _material(
    family: str,
    object_id: str,
    rows: Sequence[PublishedRow],
    assertions: Sequence[RetractionRow],
) -> LineageMaterial:
    """One object's COMPLETE lineage material, in the kernel's own DTO shape.

    Every field is carried through unchanged. Nothing is defaulted, coerced, filtered, ordered or
    repaired: an absent provenance value, an unknown reference type and a retraction with no
    recorded time each have a semantic classification in the kernel, and pre-empting any of them
    here would make that classification unreachable.

    The payload is carried as the raw governed-write mapping rather than translated into an E2
    family payload object. Lineage semantics never inspect payload content - only its presence -
    so translating it would add a second copy of the row/DTO mapping for no gain.
    """

    return LineageMaterial(
        object_family=family,
        object_id=object_id,
        versions=tuple(
            PublishedObjectVersion(
                object_version=row.object_version,
                effective_from=row.effective_from,
                active_flag=row.active_flag,
                payload=dict(row.payload),
                declared_effective_to=row.declared_effective_to,
                corrects_object_version=row.corrects_object_version,
                publication_reference_type=row.publication_reference_type,
                publication_reference_id=row.publication_reference_id,
                published_at=row.published_at,
            )
            for row in rows
        ),
        retraction_assertions=tuple(
            RetractionAssertion(
                retraction_id=assertion.retraction_id,
                object_version=assertion.object_version,
                retracted_at=assertion.retracted_at,
                publication_reference_type=assertion.publication_reference_type,
                publication_reference_id=assertion.publication_reference_id,
            )
            for assertion in assertions
        ),
    )


def derive_effective_state(
    rows: Sequence[PublishedRow],
    assertions: Sequence[RetractionRow],
    as_of: datetime,
) -> EffectiveConfigurationState:
    """Resolve every stable object's effective version and authoritative predecessor, at `as_of`.

    THE EFFECTIVE VERSION is the single one the kernel selects as effective at `as_of` from the
    validated current asserted lineage. It answers "what does this object mean right now", which
    is what every linkage and grant question needs.

    THE AUTHORITATIVE PREDECESSOR is the temporally LAST version of that same validated current
    asserted lineage. It answers "what would an UPDATE or DEACTIVATE supersede", which is a
    lineage-position question rather than an effectiveness one: an object whose declared interval
    has lapsed still has a predecessor, and a republication of it grants nothing new. A RETRACTED
    version is never a predecessor, however great its spelling - which is precisely why the
    allocation anchor and the predecessor are read separately and must never be conflated.

    Both are unambiguous by construction once the lineage validates: duplicate starts, explicit
    overlaps and multiple effective versions are all kernel-detected defects, and any defect at
    all lands the object in `unresolved` rather than producing a best guess.
    """

    versions_by_object: dict[tuple[str, str], list[PublishedRow]] = {}
    assertions_by_object: dict[tuple[str, str], list[RetractionRow]] = {}
    for row in rows:
        versions_by_object.setdefault((row.object_family, row.object_id), []).append(row)
    for assertion in assertions:
        assertions_by_object.setdefault(
            (assertion.object_family, assertion.object_id), []
        ).append(assertion)

    effective_rows: dict[tuple[str, str], PublishedRow] = {}
    predecessor_rows: dict[tuple[str, str], PublishedRow] = {}
    unresolved: list[str] = []

    for key in sorted(set(versions_by_object) | set(assertions_by_object)):
        family, object_id = key
        object_rows = versions_by_object.get(key, [])
        material = _material(family, object_id, object_rows, assertions_by_object.get(key, []))
        unestablished = f"{LINEAGE_UNRESOLVED_PREFIX}:{family}/{object_id}"

        if check_material_well_formed(material) is not None:
            unresolved.append(unestablished)
            continue
        evaluation = evaluate_lineage(material, as_of)
        if evaluation.has_defect:
            unresolved.append(unestablished)
            continue

        by_version = {row.object_version: row for row in object_rows}
        selected: list[str] = []
        if evaluation.effective_version is not None:
            selected.append(str(evaluation.effective_version.object_version))
        if evaluation.asserted_intervals:
            # `asserted_intervals` is ordered by (effective_from, object_version), so the last
            # entry is the temporally latest version of the current asserted lineage.
            selected.append(str(evaluation.asserted_intervals[-1].version.object_version))
        if any(identity not in by_version for identity in selected):
            # The kernel cited a version this material does not contain. That cannot happen from
            # a coherent read, so it is reported rather than worked around.
            unresolved.append(unestablished)
            continue

        if evaluation.effective_version is not None:
            effective_rows[key] = by_version[str(evaluation.effective_version.object_version)]
        if evaluation.asserted_intervals:
            predecessor_rows[key] = by_version[
                str(evaluation.asserted_intervals[-1].version.object_version)
            ]

    return EffectiveConfigurationState(
        effective_rows=effective_rows,
        predecessor_rows=predecessor_rows,
        unresolved=tuple(unresolved),
    )


def effective_row(
    context: AuthorityContext, family: str, object_id: str
) -> PublishedRow | None:
    """The version EFFECTIVE at the context instant, or None. Never "the latest written"."""

    return context.effective_state.effective_rows.get((family, object_id))


def predecessor_row(
    context: AuthorityContext, family: str, object_id: str
) -> PublishedRow | None:
    """The version an UPDATE or DEACTIVATE would supersede, or None."""

    return context.effective_state.predecessor_rows.get((family, object_id))


def authoritative_predecessor(
    context: AuthorityContext, family: str, object_id: str
) -> str | None:
    """The OPAQUE identity of the authoritative predecessor, or None if there is none.

    None means the current asserted lineage is empty - the object has never been published, or
    every version it has was retracted. It never means "the lineage could not be established":
    that case is in `context.unresolved` and has already failed the governed action closed
    before any caller reaches this.
    """

    row = predecessor_row(context, family, object_id)
    return None if row is None else row.object_version


def active_effective_rows(context: AuthorityContext, family: str) -> tuple[PublishedRow, ...]:
    """Grant-eligible rows of one family: lineage-valid AND effective at as_of AND active.

    The three conditions stay separate all the way down - the kernel decides the first two and
    `active_flag` is applied here - because a reader of the evidence must be able to see which
    one failed.
    """

    return tuple(
        row
        for (row_family, _object_id), row in sorted(
            context.effective_state.effective_rows.items()
        )
        if row_family == family and row.active_flag is True
    )


def publication_time_is_non_decreasing(
    anchor: AllocationAnchor, publishing_at: datetime
) -> bool:
    """May a publication recorded at `publishing_at` sit after `anchor` in the kernel's order?

    PF-1A-E2-A 11.8.3 requires `published_at` to be NON-DECREASING as `object_version` increases.
    A newly minted identity is always lexicographically greater than the all-time anchor, so its
    recorded time must not be EARLIER than the anchor's - which a clock rollback, a restored
    backup or a mis-set container clock can produce even though every other rule holds. EQUALITY
    is fine: the kernel requires non-decreasing, not strictly increasing.

    Fails closed on anything it cannot compare, and never rewrites a timestamp to make the
    comparison succeed. Fabricating or advancing a recorded time would manufacture the very
    provenance conformance this check exists to verify.
    """

    if anchor.object_version is None:
        return True
    if not is_utc_normalized_instant(anchor.published_at):
        return False
    if not is_utc_normalized_instant(publishing_at):
        return False
    return publishing_at >= anchor.published_at


def prospective_publication_defects(
    context: AuthorityContext, proposed: PublishedRow
) -> tuple[str, ...]:
    """Would APPENDING `proposed` leave an E2-VALID lineage for its own stable object?

    THE QUESTION THIS ANSWERS IS NOT A RISK QUESTION, AND CONFLATING THE TWO IS THE DEFECT THIS
    FUNCTION EXISTS TO REMOVE. `classify_risk` decides whether a change GRANTS MORE than what it
    supersedes, and a narrower temporal interval correctly answers "no". This decides whether the
    resulting IMMUTABLE LINEAGE could be published at all, and a narrower interval can answer "no"
    to that too - because PF-1A-E3's UPDATE model APPENDS rather than retracting and republishing,
    so a predecessor carrying a finite `declared_effective_to` remains asserted alongside the new
    version. Where the new version starts before that declared end, PF-1A-E2-A 11.4 reads the pair
    as an EXPLICIT OVERLAP and fails the whole object's resolution closed. Both answers are correct;
    they are answers to different questions, and only the second may block publication.

    THE COMPLETE PROSPECTIVE MATERIAL IS EVALUATED, NOT THE PROPOSED ROW IN ISOLATION. Every
    existing published version of the object, every existing retraction assertion, and the proposed
    version exactly as it would be written all go to the UNCHANGED `check_material_well_formed` and
    `lineage.evaluate_lineage`. There is deliberately NO local "do these two intervals overlap?"
    rule here: the security goal is broader than the one observed shape, and a partial local copy
    would pass every defect class it did not happen to anticipate - duplicate starts, invalid
    provenance, a recorded time that decreases across the version order, an unretracted correction
    target - while also becoming a second copy of semantics this package has already refused to own.

    Returns EVERY defect it found, as canonical strings, rather than a bare boolean, so a refusal
    can be attributed to a named kernel classification rather than to "something was wrong". An
    empty tuple means the append is publishable.
    """

    family, object_id = proposed.object_family, proposed.object_id
    existing_rows = [
        row
        for row in context.rows
        if row.object_family == family and row.object_id == object_id
    ]
    existing_assertions = [
        assertion
        for assertion in context.retractions
        if assertion.object_family == family and assertion.object_id == object_id
    ]
    material = _material(
        family, object_id, [*existing_rows, proposed], existing_assertions
    )

    rejection = check_material_well_formed(material)
    if rejection is not None:
        # The DTO/port boundary rejected the prospective material outright. That is a distinct
        # failure from a semantic defect and is reported as such rather than being folded into one.
        return (f"{rejection.kind}::{rejection.detail}",)

    evaluation = evaluate_lineage(material, context.as_of)
    return tuple(
        sorted(
            f"{defect.reason_code}:{defect.object_version or ''}:{defect.detail}"
            for defect in evaluation.defects
        )
    )


def protected_authority_object_ids(context: AuthorityContext) -> frozenset[str]:
    """OVER-INCLUSIVE by design: any non-retracted assertion of protection counts."""

    return frozenset(
        row.object_id
        for row in context.rows
        if row.object_family == BUSINESS_AUTHORITY
        and not row.retracted
        and row.payload.get("is_protected_meta_authority") is True
    )


def role_ids_for_authority(context: AuthorityContext, authority_object_id: str) -> frozenset[str]:
    return frozenset(
        str(row.payload["business_authority_role_object_id"])
        for row in active_effective_rows(context, BUSINESS_AUTHORITY_RULE)
        if row.payload.get("business_authority_object_id") == authority_object_id
        and row.payload.get("business_authority_role_object_id") is not None
    )


def authority_ids_for_roles(
    context: AuthorityContext, role_object_ids: frozenset[str]
) -> frozenset[str]:
    return frozenset(
        str(row.payload["business_authority_object_id"])
        for row in active_effective_rows(context, BUSINESS_AUTHORITY_RULE)
        if row.payload.get("business_authority_role_object_id") in role_object_ids
        and row.payload.get("business_authority_object_id") is not None
    )


def _targets_person(
    context: AuthorityContext, payload: Mapping[str, Any], person_id: str | None
) -> bool:
    if not person_id:
        return False
    if payload.get("person_id") == person_id:
        return True
    position_id = payload.get("position_id")
    if position_id is None:
        return False
    return context.incumbent_person_by_position.get(str(position_id)) == person_id


def person_linked_role_ids(context: AuthorityContext, person_id: str | None) -> frozenset[str]:
    """Roles the person currently holds, directly or through a position they occupy.

    "Currently" is the kernel's effectiveness, not the store's write order: an assignment that is
    effective and active NOW makes its holder self-affected even if a future-dated, inactive or
    reassigned successor has already been published against the same object.
    """

    return frozenset(
        str(row.payload["business_authority_role_object_id"])
        for row in active_effective_rows(context, BUSINESS_AUTHORITY_ASSIGNMENT)
        if row.payload.get("business_authority_role_object_id") is not None
        and _targets_person(context, row.payload, person_id)
    )


def _temporal_broadening(
    proposal: ConfigurationChangeProposal, existing: PublishedRow
) -> tuple[bool, str]:
    """(broadened_or_unprovable, reason) for the DECLARED temporal scope.

    An interval is read as `[effective_from, declared_effective_to)`, an ABSENT declared end
    meaning unbounded. The proposed interval BROADENS the published one when it starts earlier,
    when it ends later, or when it replaces a finite declared end with no end at all - the
    largest broadening of the three, and the one most easily mistaken for a tidy-up.

    Anything that cannot be compared - an absent published start, a value that is not a
    timestamp, a naive/aware mixture - is reported as broadening. An unprovable narrowing is not
    a narrowing, and this is the direction that fails closed.

    This is a WRITE-BOUNDARY judgement about the declared interval a governed publication would
    assert. It is not effectiveness: whether that interval actually grants anything at a given
    instant remains the PF-1A-E2-A kernel's question.
    """

    published_from, published_to = existing.effective_from, existing.declared_effective_to
    proposed_from, proposed_to = proposal.effective_from, proposal.declared_effective_to

    if not isinstance(published_from, datetime) or not isinstance(proposed_from, datetime):
        return True, "TEMPORAL_SCOPE_INCOMPARABLE"
    if any(
        value is not None and not isinstance(value, datetime)
        for value in (published_to, proposed_to)
    ):
        return True, "TEMPORAL_SCOPE_INCOMPARABLE"

    try:
        if proposed_from < published_from:
            return True, "TEMPORAL_SCOPE_STARTS_EARLIER"
        if published_to is not None:
            if proposed_to is None:
                return True, "TEMPORAL_SCOPE_BECOMES_UNBOUNDED"
            if proposed_to > published_to:
                return True, "TEMPORAL_SCOPE_ENDS_LATER"
    except TypeError:
        # Unorderable timestamps (typically a naive/aware mixture) are unprovable, not narrow.
        return True, "TEMPORAL_SCOPE_INCOMPARABLE"
    return False, "TEMPORAL_SCOPE_IS_UNCHANGED_OR_NARROWED"


def _privilege_increasing(
    proposal: ConfigurationChangeProposal, existing: PublishedRow | None
) -> tuple[bool, str]:
    """Provably non-increasing, or assumed increasing. There is no third answer.

    `existing` is the AUTHORITATIVE PREDECESSOR - the version this publication would supersede -
    because that is what "unchanged" has to be measured against. An object whose declared
    interval has lapsed still has one, and republishing it identically grants nothing new; an
    object with no predecessor at all has nothing to be identical to, so the unsafe direction is
    assumed.

    A byte-identical payload is NOT sufficient on its own. The declared temporal scope is part
    of what a publication grants, so an otherwise-identical UPDATE that starts earlier, ends
    later or drops its declared end broadens the grant and is treated as an increase.
    """

    if proposal.change_type == CHANGE_DEACTIVATE:
        # A DEACTIVATE publishes an INACTIVE version. It withdraws the grant whatever interval
        # it declares, so its interval cannot broaden anything.
        return False, "DEACTIVATION_IS_PROVABLY_NON_INCREASING"
    if (
        proposal.change_type == CHANGE_UPDATE
        and existing is not None
        and existing.active_flag is True
        and canonical_json(dict(proposal.change_payload))
        == canonical_json(dict(existing.payload))
    ):
        broadened, reason = _temporal_broadening(proposal, existing)
        if not broadened:
            return False, "PUBLISHED_CONTENT_AND_TEMPORAL_SCOPE_ARE_UNCHANGED_OR_NARROWED"
        return True, reason
    # Scope and threshold semantics belong to the kernel. This module does not attempt to prove
    # a narrowing of those, so it assumes the unsafe direction.
    return True, "NOT_PROVABLY_NON_INCREASING"


def classify_risk(
    proposal: ConfigurationChangeProposal,
    context: AuthorityContext,
    initiator_person_id: str | None,
) -> RiskClassification:
    """Recompute, from CURRENT state only, whether independence is required.

    TWO VIEWS OF "CURRENT" ARE USED, AND THEY ARE DIFFERENT ON PURPOSE. `existing` is the
    authoritative predecessor - what this publication would supersede - and is what the
    privilege-increase comparison measures against. `current` is the version EFFECTIVE right now,
    which is what a live reference or a live self-linkage actually is. They coincide most of the
    time; where they do not, a reference asserted by EITHER counts, because losing either one
    under-computes risk.
    """

    family = proposal.configuration_object_family
    object_id = proposal.configuration_object_id
    payload = dict(proposal.change_payload)
    protected = protected_authority_object_ids(context)
    linked = person_linked_role_ids(context, initiator_person_id)
    existing = predecessor_row(context, family, object_id)
    current = effective_row(context, family, object_id)
    why: list[str] = []
    affects_protected = False
    is_self = False

    def merged(name: str) -> frozenset[str]:
        found: set[str] = set()
        sources: list[Mapping[str, Any]] = [payload]
        for published in (existing, current):
            if published is not None:
                sources.append(published.payload)
        for source in sources:
            if source.get(name) is not None:
                found.add(str(source[name]))
        return frozenset(found)

    if family == BUSINESS_AUTHORITY:
        if payload.get("is_protected_meta_authority") is True:
            affects_protected = True
            why.append("PROPOSED_PAYLOAD_ASSERTS_PROTECTED_META_AUTHORITY")
        if object_id in protected:
            affects_protected = True
            why.append("TARGET_AUTHORITY_IS_PUBLISHED_PROTECTED_META_AUTHORITY")
        if role_ids_for_authority(context, object_id) & linked:
            is_self = True
            why.append("INITIATOR_HOLDS_A_ROLE_CARRYING_THE_TARGET_AUTHORITY")
    elif family == BUSINESS_AUTHORITY_ROLE:
        if authority_ids_for_roles(context, frozenset({object_id})) & protected:
            affects_protected = True
            why.append("TARGET_ROLE_CARRIES_A_PROTECTED_META_AUTHORITY")
        if object_id in linked:
            is_self = True
            why.append("INITIATOR_HOLDS_THE_TARGET_ROLE")
    elif family == BUSINESS_AUTHORITY_RULE:
        if merged("business_authority_object_id") & protected:
            affects_protected = True
            why.append("RULE_REFERENCES_A_PROTECTED_META_AUTHORITY")
        if merged("business_authority_role_object_id") & linked:
            is_self = True
            why.append("INITIATOR_HOLDS_A_ROLE_THE_RULE_GRANTS_FROM")
    elif family == BUSINESS_AUTHORITY_ASSIGNMENT:
        roles = merged("business_authority_role_object_id")
        if authority_ids_for_roles(context, roles) & protected:
            affects_protected = True
            why.append("ASSIGNED_ROLE_CARRIES_A_PROTECTED_META_AUTHORITY")
        if _targets_person(context, payload, initiator_person_id):
            is_self = True
            why.append("PROPOSED_ASSIGNMENT_TARGETS_THE_INITIATOR")
        if any(
            published is not None
            and _targets_person(context, published.payload, initiator_person_id)
            for published in (existing, current)
        ):
            is_self = True
            why.append("EXISTING_ASSIGNMENT_ALREADY_TARGETS_THE_INITIATOR")

    increasing, reason = _privilege_increasing(proposal, existing)
    why.append(reason)
    required = affects_protected or (is_self and increasing)
    why.append("AUTHORIZATION_REQUIRED" if required else "SINGLE_PERSON_PERMITTED")
    return RiskClassification(
        is_self_affecting=is_self,
        affects_protected_meta_authority=affects_protected,
        privilege_increasing=increasing,
        authorization_required=required,
        derivation=tuple(why),
    )


def _intervals_overlap(a_from, a_to, b_from, b_to) -> bool:
    if a_from is None or b_from is None:
        # A missing start cannot be shown NOT to overlap, so it is treated as overlapping.
        return True
    if a_to is not None and b_from >= a_to:
        return False
    if b_to is not None and a_from >= b_to:
        return False
    return True


def conflicting_active_assignment(
    proposal: ConfigurationChangeProposal, context: AuthorityContext
) -> str | None:
    """The stable id of an already-active assignment this proposal duplicates.

    A governed WRITE-boundary rule, applied at proposal and re-applied inside the activation
    transaction. It rejects the same role, target, scope and an overlapping declared interval
    on a DIFFERENT stable object. A later version of the SAME object is supersession, not
    duplication, and is deliberately excluded.
    """

    if proposal.configuration_object_family != BUSINESS_AUTHORITY_ASSIGNMENT:
        return None
    if proposal.change_type == CHANGE_DEACTIVATE:
        return None
    key = tuple(proposal.change_payload.get(name) for name in _ASSIGNMENT_KEY)
    for row in active_effective_rows(context, BUSINESS_AUTHORITY_ASSIGNMENT):
        if row.object_id == proposal.configuration_object_id:
            continue
        if tuple(row.payload.get(name) for name in _ASSIGNMENT_KEY) != key:
            continue
        if _intervals_overlap(
            proposal.effective_from,
            proposal.declared_effective_to,
            row.effective_from,
            row.declared_effective_to,
        ):
            return row.object_id
    return None


def _made(
    *,
    stage,
    context,
    risk,
    person,
    actor,
    eligible,
    different,
    current,
    satisfied,
    outcome,
    refusal,
) -> GovernanceEvaluation:
    return GovernanceEvaluation(
        stage=stage,
        evaluated_at=context.as_of,
        acting_person_id=person,
        acting_actor_user_public_id=actor,
        risk=risk,
        authorizer_eligible=eligible,
        authorizer_is_different_person=different,
        dependencies_current=current,
        authorization_satisfied=satisfied,
        outcome=outcome,
        refusal_reason=refusal,
        dependency_fingerprint=context.fingerprint,
        context_reference=context.context_reference,
    )


def unresolved_context_evaluation(*, stage, context, person, actor) -> GovernanceEvaluation:
    """Fail closed: an unestablished dependency permits nothing, at any stage."""

    unknown = RiskClassification(
        is_self_affecting=True,
        affects_protected_meta_authority=True,
        privilege_increasing=True,
        authorization_required=True,
        derivation=("CONTEXT_UNRESOLVED",) + tuple(sorted(context.unresolved)),
    )
    return _made(
        stage=stage,
        context=context,
        risk=unknown,
        person=person,
        actor=actor,
        eligible=False,
        different=False,
        current=False,
        satisfied=False,
        outcome=OUTCOME_REFUSED,
        refusal=AUTHORITY_CONTEXT_UNAVAILABLE,
    )


def evaluate_proposal(
    *, context, risk, person, actor, eligible, blocking_reason, stage=STAGE_PROPOSAL
) -> GovernanceEvaluation:
    """PRELIMINARY/AUDIT evidence. This authorizes nothing and activates nothing."""

    refusal = (
        blocking_reason
        if blocking_reason is not None
        else (None if eligible else AUTHORIZER_NOT_ELIGIBLE)
    )
    satisfied = refusal is None
    return _made(
        stage=stage,
        context=context,
        risk=risk,
        person=person,
        actor=actor,
        eligible=eligible,
        different=False,
        current=True,
        satisfied=satisfied,
        outcome=OUTCOME_RECORDED if satisfied else OUTCOME_REFUSED,
        refusal=refusal,
    )


def evaluate_authorization(
    *, context, risk, initiator_person_id, person, actor, eligible, proposal_fingerprint
) -> GovernanceEvaluation:
    """Decide whether authorization may be RECORDED, on FRESHLY recomputed risk.

    The preventive invariant lives here: where independence is required the requester can never
    satisfy it themselves, and an ineligible second person does not satisfy it either. Where it
    is NOT required, the same administrator may authorize their own ordinary change - the case
    ADR-033 explicitly preserves. Turning every edit into a two-person process would be a
    different defect, not extra safety.
    """

    different = person != initiator_person_id
    refusal: str | None = None
    if not eligible:
        refusal = AUTHORIZER_NOT_ELIGIBLE
    elif risk.authorization_required and not different:
        refusal = SAME_PERSON_AUTHORIZATION_FORBIDDEN
    satisfied = refusal is None
    return _made(
        stage=STAGE_AUTHORIZATION,
        context=context,
        risk=risk,
        person=person,
        actor=actor,
        eligible=eligible,
        different=different,
        current=context.fingerprint == proposal_fingerprint,
        satisfied=satisfied,
        outcome=OUTCOME_RECORDED if satisfied else OUTCOME_REFUSED,
        refusal=refusal,
    )


def evaluate_activation(
    *,
    context,
    risk,
    initiator_person_id,
    recorded_authorizer_person_id,
    authorization_evidence_verified,
    authorizer_still_eligible,
    authorization_fingerprint,
    authorization_required_at_authorization,
    person,
    actor,
    lineage_ok,
    references_present,
    conflicting_assignment_object_id,
    publication_timestamp_monotonic,
    publication_lineage_valid,
) -> GovernanceEvaluation:
    """The MANDATORY pre-activation recomputation, atomic with publication.

    THE AUTHORIZATION EVIDENCE IS ONE BOUND FACT, NOT A COMBINATION. `authorization_fingerprint`
    and `authorization_required_at_authorization` must come from the SAME successful
    AUTHORIZATION evaluation the recorded authorizer is bound to - never from whichever
    AUTHORIZATION evaluation happens to be the most recent. A later REFUSED attempt records its
    own evaluation against the same change, and reading that one's freshly-recomputed evidence
    alongside an older successful authorizer identity would assemble an authorization that never
    happened: an approver from one context, a risk verdict and dependency fingerprint from
    another. The caller establishes the binding; `authorization_evidence_verified` is that
    caller's verdict on it, and a false verdict refuses here rather than proceeding on
    unverifiable evidence.

    Order matters and is deliberate. A structural precondition (lineage, references,
    duplication, publication ordering, publication validity) is reported before an authorization
    question, because blaming an authorizer for a change that could not have been published in any
    case would mislead. A risk increase since authorization is named specifically rather than collapsed into
    "same person", and an authorizer who has since lost the authority is named before mere
    context drift.

    `publication_timestamp_monotonic` is the fourth structural precondition and the least
    obvious: a newly minted identity always sorts after the object's all-time allocation anchor,
    so recording it with an EARLIER `published_at` than that anchor's would publish provenance
    the unchanged kernel reads as contradictory (11.8.3), turning a clean later resolution
    FAIL_CLOSED. The refusal is the correct outcome, and advancing the clock to get past it would
    manufacture exactly the conformance being checked.

    `publication_lineage_valid` is the fifth, and it generalises the fourth. The caller has by now
    established the EXACT immutable version this activation would append, and has asked the
    unchanged kernel whether the object's COMPLETE lineage would still be valid with that version in
    it (`prospective_publication_defects`). PF-1A-E3's UPDATE appends rather than retracting and
    republishing, so an append can leave a lineage the kernel immediately classifies as defective
    even when the expected predecessor is exactly right, the authorization is entirely in order and
    the change grants nothing new - the narrowing-into-a-still-declared-end case being the reachable
    example. Publishing it would fail every later resolution of that object closed, and - because
    the authority graph is whole-configuration - would block governed administration outright.
    Refusing is the correct outcome, and it is NOT reached by reclassifying a narrowing as a
    privilege increase: risk classification and publication validity stay separate answers to
    separate questions.

    The two publication checks are kept SEPARATE and IN THIS ORDER even though the fifth would also
    detect the fourth's failure. The specific check names its cause precisely -
    "the recorded clock cannot be published behind" - and a reader of the refused evaluation is
    better served by that than by a general "the resulting lineage would be defective".
    """

    different = (
        recorded_authorizer_person_id is not None
        and recorded_authorizer_person_id != initiator_person_id
    )
    current = (
        authorization_evidence_verified
        and authorization_fingerprint is not None
        and context.fingerprint == authorization_fingerprint
    )
    refusal: str | None = None
    if not lineage_ok:
        refusal = LINEAGE_PRECONDITION_FAILED
    elif not references_present:
        refusal = REFERENCED_OBJECT_MISSING
    elif conflicting_assignment_object_id is not None:
        refusal = DUPLICATE_ACTIVE_ASSIGNMENT
    elif not publication_timestamp_monotonic:
        refusal = PUBLICATION_TIMESTAMP_NOT_MONOTONIC
    elif not publication_lineage_valid:
        refusal = PUBLICATION_LINEAGE_INVALID
    elif recorded_authorizer_person_id is None:
        refusal = AUTHORIZATION_MISSING
    elif not authorization_evidence_verified:
        refusal = AUTHORIZATION_EVIDENCE_UNVERIFIABLE
    elif risk.authorization_required and authorization_required_at_authorization is False:
        refusal = RISK_INCREASED_SINCE_AUTHORIZATION
    elif risk.authorization_required and not different:
        refusal = SAME_PERSON_AUTHORIZATION_FORBIDDEN
    elif not authorizer_still_eligible:
        refusal = AUTHORIZER_NO_LONGER_ELIGIBLE
    elif risk.authorization_required and not current:
        refusal = AUTHORIZATION_CONTEXT_DRIFTED
    satisfied = refusal is None
    return _made(
        stage=STAGE_ACTIVATION,
        context=context,
        risk=risk,
        person=person,
        actor=actor,
        eligible=authorizer_still_eligible,
        different=different,
        current=current,
        satisfied=satisfied,
        outcome=OUTCOME_PERMITTED if satisfied else OUTCOME_REFUSED,
        refusal=refusal,
    )


def dependency_fingerprint(
    rows: Sequence[PublishedRow],
    assertions: Sequence[RetractionRow],
    incumbency: Mapping[str, str | None],
    protected_candidate_codes: Sequence[str],
) -> str:
    """A byte-stable fingerprint of everything a recomputation could rely on.

    Whole-configuration rather than change-scoped, deliberately: a change-scoped fingerprint
    has to decide in advance which facts could possibly matter, and getting that wrong is
    silent. Because drift only BLOCKS where independence is required, a broad fingerprint costs
    an ordinary single-person change nothing.

    EVERYTHING THE DERIVATION READS IS COVERED, not merely the payload. Effectiveness now depends
    on the declared interval, and lineage validity on provenance, recorded times, correction
    targets and every retraction assertion, so all of them are fingerprinted: a drift that could
    change which version is effective must be visible as drift. Every element is rendered as text
    before sorting, so a `None` beside a `bool` or a timestamp can never make the sort itself
    raise.
    """

    material = canonical_json(
        {
            "rows": sorted(
                [
                    row.object_family,
                    row.object_id,
                    row.object_version,
                    str(row.active_flag),
                    str(row.retracted),
                    str(row.effective_from),
                    str(row.declared_effective_to),
                    str(row.corrects_object_version),
                    str(row.publication_reference_type),
                    str(row.publication_reference_id),
                    str(row.published_at),
                    canonical_json(dict(row.payload)),
                ]
                for row in rows
            ),
            "retraction_assertions": sorted(
                [
                    assertion.object_family,
                    assertion.object_id,
                    str(assertion.object_version),
                    str(assertion.retraction_id),
                    str(assertion.retracted_at),
                    str(assertion.publication_reference_type),
                    str(assertion.publication_reference_id),
                ]
                for assertion in assertions
            ),
            "incumbency": sorted(incumbency.items()),
            "protected_candidate_codes": sorted(protected_candidate_codes),
        }
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
