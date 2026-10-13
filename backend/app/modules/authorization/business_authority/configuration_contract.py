"""Closed vocabularies and physical names for the governed configuration lifecycle (PF-1A-E3).

Names things; decides nothing. The object families and the publication provenance domain are
IMPORTED from the PF-1A-E2-A contract, never restated: a second spelling of either is how a
governed writer and the kernel reading its output come to disagree.

Protection is a DATA FLAG (ADR-033). There is deliberately no authority-code constant here
standing in for the configuration administration authority, and none may be added.
"""

from __future__ import annotations

import hashlib
from typing import Final

from app.modules.authorization.business_authority.contract import (
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
    CONFIGURATION_CHANGE,
    OBJECT_FAMILIES,
)

# DEACTIVATE is a PUBLICATION, not an edit: it publishes a NEW inactive version.
CHANGE_CREATE: Final = "CREATE"
CHANGE_UPDATE: Final = "UPDATE"
CHANGE_DEACTIVATE: Final = "DEACTIVATE"
CHANGE_TYPES: Final = (CHANGE_CREATE, CHANGE_UPDATE, CHANGE_DEACTIVATE)

LIFECYCLE_PENDING: Final = "PENDING"
LIFECYCLE_ACTIVE: Final = "ACTIVE"
LIFECYCLE_REJECTED: Final = "REJECTED"
LIFECYCLE_STATUSES: Final = (LIFECYCLE_PENDING, LIFECYCLE_ACTIVE, LIFECYCLE_REJECTED)
TERMINAL_LIFECYCLE_STATUSES: Final = (LIFECYCLE_ACTIVE, LIFECYCLE_REJECTED)

# PROPOSAL evidence is PRELIMINARY/AUDIT only; AUTHORIZATION and ACTIVATION each RECOMPUTE.
STAGE_PROPOSAL: Final = "PROPOSAL"
STAGE_AUTHORIZATION: Final = "AUTHORIZATION"
STAGE_REJECTION: Final = "REJECTION"
STAGE_ACTIVATION: Final = "ACTIVATION"
EVALUATION_STAGES: Final = (
    STAGE_PROPOSAL,
    STAGE_AUTHORIZATION,
    STAGE_REJECTION,
    STAGE_ACTIVATION,
)

OUTCOME_RECORDED: Final = "RECORDED"
OUTCOME_PERMITTED: Final = "PERMITTED"
OUTCOME_REFUSED: Final = "REFUSED"
EVALUATION_OUTCOMES: Final = (OUTCOME_RECORDED, OUTCOME_PERMITTED, OUTCOME_REFUSED)

# The outcomes an evaluation may carry and still be a SUCCESSFUL one. Stated as a closed tuple
# rather than as `!= OUTCOME_REFUSED`, so a later added outcome has to be classified
# deliberately instead of being accepted by a negation nobody revisited.
SUCCESSFUL_EVALUATION_OUTCOMES: Final = (OUTCOME_RECORDED, OUTCOME_PERMITTED)

# A refusal is a FIRST-CLASS PERSISTED outcome, never a swallowed exception.
INITIATOR_NOT_ELIGIBLE: Final = "INITIATOR_NOT_ELIGIBLE"
AUTHORIZER_NOT_ELIGIBLE: Final = "AUTHORIZER_NOT_ELIGIBLE"
AUTHORIZER_NO_LONGER_ELIGIBLE: Final = "AUTHORIZER_NO_LONGER_ELIGIBLE"
SAME_PERSON_AUTHORIZATION_FORBIDDEN: Final = "SAME_PERSON_AUTHORIZATION_FORBIDDEN"
AUTHORIZATION_MISSING: Final = "AUTHORIZATION_MISSING"
# An authorizer IS recorded, but the successful AUTHORIZATION evaluation that authorizer field
# is bound to cannot be loaded and verified as that authorizer's own successful authorization.
# Distinct from AUTHORIZATION_MISSING on purpose: "nobody authorized this" and "the recorded
# authorization cannot be verified" are different governance answers, and collapsing them would
# hide an evidence-integrity failure behind an ordinary missing-approval message.
AUTHORIZATION_EVIDENCE_UNVERIFIABLE: Final = "AUTHORIZATION_EVIDENCE_UNVERIFIABLE"
RISK_INCREASED_SINCE_AUTHORIZATION: Final = "RISK_INCREASED_SINCE_AUTHORIZATION"
AUTHORIZATION_CONTEXT_DRIFTED: Final = "AUTHORIZATION_CONTEXT_DRIFTED"
AUTHORITY_CONTEXT_UNAVAILABLE: Final = "AUTHORITY_CONTEXT_UNAVAILABLE"
LINEAGE_PRECONDITION_FAILED: Final = "LINEAGE_PRECONDITION_FAILED"
# The publication would record a `published_at` EARLIER than the one already recorded against the
# object's all-time lexicographic allocation anchor. Because a newly minted identity always sorts
# after that anchor, publishing it would violate the PF-1A-E2-A 11.8.3 rule that `published_at` is
# non-decreasing in `object_version` order, and the unchanged kernel would then read the object's
# provenance as contradictory and fail an otherwise clean later resolution CLOSED. Distinct from
# LINEAGE_PRECONDITION_FAILED, which is about superseding the wrong version: here the expected
# predecessor may be perfectly correct and the recorded CLOCK is what cannot be published behind.
PUBLICATION_TIMESTAMP_NOT_MONOTONIC: Final = "PUBLICATION_TIMESTAMP_NOT_MONOTONIC"
# APPENDING the exact proposed immutable version would leave the object's COMPLETE published
# lineage defective under UNCHANGED PF-1A-E2-A semantics - the material well-formedness boundary,
# the structural rules of 11.6, the provenance rules of 11.7/11.8.3, or the asserted-closure rules
# of 11.4. The observed case is an UPDATE whose new interval starts BEFORE a still-asserted
# predecessor's declared end, which 11.4 reads as an EXPLICIT OVERLAP and fails closed; the reason
# is deliberately not named for that one shape, because the rule is the general one: PF-1A-E3 never
# publishes an append the unchanged kernel would immediately classify as defective.
#
# DISTINCT FROM LINEAGE_PRECONDITION_FAILED, which is about superseding the WRONG version: here the
# expected predecessor may be exactly right, the authorization may be entirely in order, and it is
# the RESULTING lineage that could not be published. Distinct from PUBLICATION_TIMESTAMP_NOT_MONOTONIC
# for the same kind of reason - that check names one specific provenance-ordering failure with its
# own precise evidence, and is asserted FIRST so it keeps reporting it, even though the prospective
# evaluation below would also detect it.
PUBLICATION_LINEAGE_INVALID: Final = "PUBLICATION_LINEAGE_INVALID"
REFERENCED_OBJECT_MISSING: Final = "REFERENCED_OBJECT_MISSING"
DUPLICATE_ACTIVE_ASSIGNMENT: Final = "DUPLICATE_ACTIVE_ASSIGNMENT"
CONCURRENT_ACTIVATION_IN_PROGRESS: Final = "CONCURRENT_ACTIVATION_IN_PROGRESS"
LIFECYCLE_STATE_INVALID: Final = "LIFECYCLE_STATE_INVALID"
# Named for the GOVERNANCE DECISION, never for the acting role. An Application/Login Role code
# must not appear in this package's executable source, even incidentally inside a longer word.
CHANGE_REJECTED_BY_GOVERNANCE_DECISION: Final = "CHANGE_REJECTED_BY_GOVERNANCE_DECISION"

REFUSAL_REASONS: Final = (
    INITIATOR_NOT_ELIGIBLE,
    AUTHORIZER_NOT_ELIGIBLE,
    AUTHORIZER_NO_LONGER_ELIGIBLE,
    SAME_PERSON_AUTHORIZATION_FORBIDDEN,
    AUTHORIZATION_MISSING,
    AUTHORIZATION_EVIDENCE_UNVERIFIABLE,
    RISK_INCREASED_SINCE_AUTHORIZATION,
    AUTHORIZATION_CONTEXT_DRIFTED,
    AUTHORITY_CONTEXT_UNAVAILABLE,
    LINEAGE_PRECONDITION_FAILED,
    PUBLICATION_TIMESTAMP_NOT_MONOTONIC,
    PUBLICATION_LINEAGE_INVALID,
    REFERENCED_OBJECT_MISSING,
    DUPLICATE_ACTIVE_ASSIGNMENT,
    CONCURRENT_ACTIVATION_IN_PROGRESS,
    LIFECYCLE_STATE_INVALID,
    CHANGE_REJECTED_BY_GOVERNANCE_DECISION,
)

# `active_flag` is deliberately absent: it is a governed lifecycle decision (CREATE/UPDATE
# publish true, DEACTIVATE publishes false), not an editable payload field.
CHANGE_PAYLOAD_FIELDS: Final[dict[str, tuple[str, ...]]] = {
    BUSINESS_AUTHORITY: (
        "authority_code",
        "authority_name",
        "description",
        "is_protected_meta_authority",
    ),
    BUSINESS_AUTHORITY_ROLE: ("role_code", "role_name", "description"),
    BUSINESS_AUTHORITY_RULE: (
        "business_authority_role_object_id",
        "business_authority_object_id",
        "scope_type",
        "scope_id",
        "parameter_evaluator_type",
        "parameter_payload",
    ),
    BUSINESS_AUTHORITY_ASSIGNMENT: (
        "business_authority_role_object_id",
        "person_id",
        "position_id",
        "scope_type",
        "scope_id",
    ),
}

STABLE_REFERENCE_FIELDS: Final[dict[str, tuple[tuple[str, str], ...]]] = {
    BUSINESS_AUTHORITY: (),
    BUSINESS_AUTHORITY_ROLE: (),
    BUSINESS_AUTHORITY_RULE: (
        ("business_authority_role_object_id", BUSINESS_AUTHORITY_ROLE),
        ("business_authority_object_id", BUSINESS_AUTHORITY),
    ),
    BUSINESS_AUTHORITY_ASSIGNMENT: (
        ("business_authority_role_object_id", BUSINESS_AUTHORITY_ROLE),
    ),
}

CONFIGURATION_CHANGE_TABLE: Final = "authz_authority_configuration_change"
CONFIGURATION_EVALUATION_TABLE: Final = "authz_authority_configuration_evaluation"
CONFIGURATION_TABLES_CHILD_FIRST: Final = (
    CONFIGURATION_EVALUATION_TABLE,
    CONFIGURATION_CHANGE_TABLE,
)

# The ONE provenance a governed activation writes. PF-1A-E3 never writes bootstrap
# provenance, which is why no production module here imports that value.
PUBLICATION_REFERENCE_TYPE: Final = CONFIGURATION_CHANGE

# TWO PF-1A-E2 INVARIANTS APPLY TO `object_version` AT ONCE, AND BOTH MUST HOLD.
#
#   IT IS OPAQUE. A version published before PF-1A-E3 existed, or by any other authorized
#     mechanism, legitimately carries "v1", a UUID, or anything else its publisher chose.
#     PF-1A-E3 therefore PARSES NO VERSION IDENTIFIER, ANYWHERE: it compares an expected
#     predecessor against an exact opaque string, and it never reads one as a number. Any numeric
#     reading would make every legitimately non-numeric predecessor permanently unmanageable.
#
#   IT IS LEXICOGRAPHICALLY ORDERED. `lineage.py` states, in terms, that `object_version` is
#     compared lexicographically over its canonical string form and that A PUBLISHER MUST USE A
#     LEXICOGRAPHICALLY ORDERED VERSION IDENTITY. The kernel relies on that: 11.8.3 requires
#     `published_at` to be NON-DECREASING in `object_version` order, and 15.5 uses the same
#     ordering as a sort key. A merely unique, unordered identifier is therefore NOT sufficient -
#     a later publication that happened to sort before an earlier one is read by the unchanged
#     kernel as contradictory provenance and fails the whole resolution closed, which is a real
#     regression and not a theoretical one.
#
# THE ALLOCATION RULE THAT SATISFIES BOTH. A new identity is the object's ALL-TIME LEXICOGRAPHIC
# MAXIMUM - its ALLOCATION ANCHOR - with a non-empty PF-1A-E3 suffix appended.
#
#     new = anchor + suffix,  suffix non-empty
#
# `anchor` is therefore a PROPER PREFIX of `new`, and lexicographic comparison places a proper
# prefix strictly before its extension, so `new > anchor` for ANY anchor, whatever its syntax.
# Because `anchor >= v` for every existing version `v` and the ordering is total, `new > v` for
# all of them. The proof uses concatenation and nothing else: no character of the anchor is
# inspected, classified or interpreted, so the opacity invariant survives intact.
#
# THE ANCHOR IS NOT THE AUTHORITATIVE PREDECESSOR, and the two must never be conflated. The
# anchor spans EVERY published version including RETRACTED ones, because the kernel validates
# provenance across all of them and a new identity must sort after all of them. Which version an
# UPDATE may legitimately supersede is a separate question, answered from the validated current
# asserted lineage - where a retracted version is no answer at all, however great its spelling.
#
# The identifiers grow by the suffix width per publication. That is accepted deliberately.
# Governed authority configuration change is a rare, deliberate, administrative act, `Text` is
# unbounded, and no FIXED-WIDTH scheme can be proven greater than an arbitrary opaque
# predecessor - a predecessor of "zzzz..." defeats any bounded alphabet without reading its
# syntax, which is exactly what the opacity invariant forbids.
OBJECT_VERSION_SUFFIX_MARKER: Final = "e3"
OBJECT_VERSION_DIGEST_WIDTH: Final = 16


def object_version_suffix(configuration_change_id: str) -> str:
    """The non-empty token ONE governed activation appends.

    Alphanumeric by construction - a marker plus a hex digest, no punctuation - so the ordering
    argument above holds under a byte/codepoint comparison and under any collation that might
    order a stored column, without depending on how either treats separators.
    """

    if not configuration_change_id:
        raise ValueError("a Configuration Change identity is required to allocate a version")
    digest = hashlib.sha256(configuration_change_id.encode("utf-8")).hexdigest()
    return OBJECT_VERSION_SUFFIX_MARKER + digest[:OBJECT_VERSION_DIGEST_WIDTH]


def allocate_object_version(allocation_anchor: str | None, configuration_change_id: str) -> str:
    """The opaque identity ONE governed activation publishes under.

    STRICTLY GREATER, lexicographically, than every version already published for that stable
    object - see the proof above. `allocation_anchor` is the object's ALL-TIME lexicographic
    maximum, RETRACTED versions included, or None when the object has no published version at
    all, in which case the suffix stands alone and is trivially the maximum of a set that
    previously had none.

    THE ANCHOR IS NOT THE AUTHORITATIVE PREDECESSOR. Passing the predecessor here instead would
    be a real defect: if the all-time maximum has been retracted, the predecessor is some earlier
    version, and appending to THAT could mint an identity that sorts before the retracted row -
    which the unchanged kernel validates provenance against and would read as contradictory.

    UNIQUE for two independent reasons. The caller allocates inside the governance-wide
    publication boundary, so no concurrent governed allocator can observe the same anchor; and
    the suffix derives from the Configuration Change identity, which is unique. The published
    store's own (object_id, object_version) key is the structural backstop under both.

    NOT a replay control, and deliberately not described as one: a repeated activation would see
    an anchor that already includes its own earlier suffix and would allocate a different, longer
    identity. Replay is prevented where it actually belongs - the governed lifecycle, which moves
    PENDING to ACTIVE under a row lock inside the same transaction and refuses any later
    activation of a terminal change.
    """

    return (allocation_anchor or "") + object_version_suffix(configuration_change_id)
