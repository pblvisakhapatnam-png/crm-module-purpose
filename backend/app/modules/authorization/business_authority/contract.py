"""Closed vocabularies, stage ranks and the explicit reason-rank table.

PF-1A-E2-A sections 8, 12.2, 13, 14 and 15.5.

Everything in this module is a CLOSED, EXPLICIT, IMMUTABLE part of the
contract. In particular the reason ranks are deliberately assigned integers,
not alphabetical spellings and not accidental definition order: adding a
reason code requires assigning it a rank deliberately (PF_1A_E2_A 15.5, and
independent-review attack surface item 25a).
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# 8.1  The four configurable object families, and their fixed closed ranking
# ---------------------------------------------------------------------------
# The ranking is the `object_family_rank` component of the canonical subject
# key (PF_1A_E2_A 15.5, form (a)). It is fixed and closed; reordering it
# changes which defect is reported for a same-stage multi-family collision.

BUSINESS_AUTHORITY: Final = "BUSINESS_AUTHORITY"
BUSINESS_AUTHORITY_ROLE: Final = "BUSINESS_AUTHORITY_ROLE"
BUSINESS_AUTHORITY_RULE: Final = "BUSINESS_AUTHORITY_RULE"
BUSINESS_AUTHORITY_ASSIGNMENT: Final = "BUSINESS_AUTHORITY_ASSIGNMENT"

OBJECT_FAMILIES: Final = (
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
    BUSINESS_AUTHORITY_ASSIGNMENT,
)

OBJECT_FAMILY_RANK: Final = {
    BUSINESS_AUTHORITY: 0,
    BUSINESS_AUTHORITY_ROLE: 1,
    BUSINESS_AUTHORITY_RULE: 2,
    BUSINESS_AUTHORITY_ASSIGNMENT: 3,
}

# ---------------------------------------------------------------------------
# 9.3.2  Lineage material completeness
# ---------------------------------------------------------------------------
# Deliberately two-valued. A provider that cannot return the complete set must
# say UNAVAILABLE; there is no "partial", because a truncated list presented
# as complete is a blocking defect.

COMPLETENESS_COMPLETE: Final = "COMPLETE"
COMPLETENESS_UNAVAILABLE: Final = "UNAVAILABLE"

# ---------------------------------------------------------------------------
# 11.7  Publication provenance types
# ---------------------------------------------------------------------------
# BOOTSTRAP_PROVENANCE is the only type E2 fixtures use and is explicitly
# synthetic/test provenance. CONFIGURATION_CHANGE is a FORWARD-COMPATIBLE
# reference shape that PF-1A-E3 will populate; E2 defines the value and never
# creates such a record.
#
# This tuple is a VALIDATION vocabulary, not a language-level closed enum on
# the DTO: an ABSENT type and an UNKNOWN type are two distinct malformed
# states the kernel must classify separately (PF_1A_E2_A 9.3.4, 11.7).

BOOTSTRAP_PROVENANCE: Final = "BOOTSTRAP_PROVENANCE"
CONFIGURATION_CHANGE: Final = "CONFIGURATION_CHANGE"

PUBLICATION_REFERENCE_TYPES: Final = (BOOTSTRAP_PROVENANCE, CONFIGURATION_CHANGE)

# ---------------------------------------------------------------------------
# 12.3  Scope predicate operand types
# ---------------------------------------------------------------------------

SCOPE_GLOBAL: Final = "GLOBAL"
SCOPE_EXACT: Final = "EXACT"
SCOPE_ANCESTRY: Final = "ANCESTRY"

SUPPORTED_SCOPE_TYPES: Final = (SCOPE_GLOBAL, SCOPE_EXACT, SCOPE_ANCESTRY)

# Bounded ancestry traversal. An explicit maximum depth is mandatory; depth
# exhaustion, a cycle or a missing hop fail closed with
# ORG_HIERARCHY_UNRESOLVABLE (PF_1A_E2_A 12.3).
MAX_ANCESTRY_DEPTH: Final = 16

# ---------------------------------------------------------------------------
# 13  Parameter evaluator types
# ---------------------------------------------------------------------------
# Illustrative of the MECHANISM, not a promise of the production catalogue.
# Evaluator selection is deterministic and total: exactly one registered
# evaluator per type, resolved by EXACT match - never by prefix, fuzzy match
# or fallback. There is no executable expression language of any kind.

EVALUATOR_NONE: Final = "NONE"
EVALUATOR_NUMERIC_BAND: Final = "NUMERIC_BAND"
EVALUATOR_PERCENTAGE_BAND: Final = "PERCENTAGE_BAND"
EVALUATOR_EXACT_VALUE_SET: Final = "EXACT_VALUE_SET"

REGISTERED_EVALUATOR_TYPES: Final = (
    EVALUATOR_NONE,
    EVALUATOR_NUMERIC_BAND,
    EVALUATOR_PERCENTAGE_BAND,
    EVALUATOR_EXACT_VALUE_SET,
)

# ---------------------------------------------------------------------------
# 12.2  Deterministic evaluation stages
# ---------------------------------------------------------------------------
# stage_rank(S0) = 0 ... stage_rank(S9) = 9. This numbering is a fixed, CLOSED
# part of the contract: inserting a stage later requires renumbering
# deliberately and re-reviewing 15.5, never quietly appending an out-of-order
# value.

STAGE_S0_ACTOR: Final = "S0"
STAGE_S1_PERSON: Final = "S1"
STAGE_S2_EMPLOYMENT: Final = "S2"
STAGE_S3_AUTHORITY: Final = "S3"
STAGE_S4_RULES: Final = "S4"
STAGE_S5_ROLES: Final = "S5"
STAGE_S6_ASSIGNMENTS: Final = "S6"
STAGE_S7_TARGET: Final = "S7"
STAGE_S8_SCOPE: Final = "S8"
STAGE_S9_PARAMETERS: Final = "S9"

STAGES: Final = (
    STAGE_S0_ACTOR,
    STAGE_S1_PERSON,
    STAGE_S2_EMPLOYMENT,
    STAGE_S3_AUTHORITY,
    STAGE_S4_RULES,
    STAGE_S5_ROLES,
    STAGE_S6_ASSIGNMENTS,
    STAGE_S7_TARGET,
    STAGE_S8_SCOPE,
    STAGE_S9_PARAMETERS,
)

STAGE_RANK: Final = {stage: rank for rank, stage in enumerate(STAGES)}

# ---------------------------------------------------------------------------
# 14  Outcome and resolution status
# ---------------------------------------------------------------------------
# Two ORTHOGONAL dimensions. Never collapse them into a single boolean.
# ALLOW is only ever valid with RESOLVED; FAIL_CLOSED always implies DENY.

OUTCOME_ALLOW: Final = "ALLOW"
OUTCOME_DENY: Final = "DENY"

STATUS_RESOLVED: Final = "RESOLVED"
STATUS_FAIL_CLOSED: Final = "FAIL_CLOSED"

# ---------------------------------------------------------------------------
# 14.1  Path-level nonqualification reasons
# ---------------------------------------------------------------------------
# NORMAL outcomes. These contribute to DENY + RESOLVED and are NEVER defects.
# A path-level reason never by itself decides the result.

ASSIGNMENT_NOT_EFFECTIVE: Final = "ASSIGNMENT_NOT_EFFECTIVE"
ASSIGNMENT_NOT_ACTIVE: Final = "ASSIGNMENT_NOT_ACTIVE"
ASSIGNMENT_TARGET_NOT_THIS_PERSON: Final = "ASSIGNMENT_TARGET_NOT_THIS_PERSON"
ROLE_NOT_EFFECTIVE: Final = "ROLE_NOT_EFFECTIVE"
ROLE_NOT_ACTIVE: Final = "ROLE_NOT_ACTIVE"
RULE_NOT_EFFECTIVE: Final = "RULE_NOT_EFFECTIVE"
RULE_NOT_ACTIVE: Final = "RULE_NOT_ACTIVE"
RULE_SCOPE_NOT_MATCHED: Final = "RULE_SCOPE_NOT_MATCHED"
ASSIGNMENT_SCOPE_NOT_MATCHED: Final = "ASSIGNMENT_SCOPE_NOT_MATCHED"
SCOPE_COMPOSITION_NOT_SATISFIED: Final = "SCOPE_COMPOSITION_NOT_SATISFIED"
EVALUATOR_CONDITION_NOT_SATISFIED: Final = "EVALUATOR_CONDITION_NOT_SATISFIED"

# THE ONE BOUNDED FALLBACK (owner clarification, correction C1).
#
# The path-level taxonomy must not grow a new permanent reason code for every
# minor, rare, fully understood nonqualification variant. This is the single
# fallback, and its semantics are STRICT:
#
#   - authoritative state was COMPLETELY AND UNAMBIGUOUSLY RESOLVED, and this
#     candidate simply does not qualify for a well-understood reason for which
#     no existing specific path-level reason precisely applies;
#   - ordinary nonqualification ONLY; it may contribute only to DENY + RESOLVED;
#   - it never appears on a QUALIFYING path and is never the result-level
#     reason of an ALLOW;
#   - it can NEVER represent uncertainty, malformed state, unavailable state,
#     stale state, ambiguous state, contradictory state, unsupported semantics,
#     provider failure, or a kernel invariant failure - every one of those has
#     an existing FAIL-CLOSED code and must keep using it;
#   - the existing specific nonqualification reasons remain authoritative and
#     MUST be used wherever they apply. This is not a shortcut for avoiding one.
#
# There is deliberately NO `OTHER_FAIL_CLOSED`. INTERNAL_CONTRACT_VIOLATION
# remains the defensive kernel-invariant fail-closed category (14.3).
#
# Every use carries a SHORT, DETERMINISTIC, KERNEL-GENERATED explanation built
# from a fixed template over canonical identifiers
# (`PartialEvaluation.nonqualification_explanation`). That explanation never
# participates in result selection or ordering.
OTHER_NONQUALIFICATION: Final = "OTHER_NONQUALIFICATION"

PATH_LEVEL_REASONS: Final = (
    ASSIGNMENT_NOT_EFFECTIVE,
    ASSIGNMENT_NOT_ACTIVE,
    ASSIGNMENT_TARGET_NOT_THIS_PERSON,
    ROLE_NOT_EFFECTIVE,
    ROLE_NOT_ACTIVE,
    RULE_NOT_EFFECTIVE,
    RULE_NOT_ACTIVE,
    RULE_SCOPE_NOT_MATCHED,
    ASSIGNMENT_SCOPE_NOT_MATCHED,
    SCOPE_COMPOSITION_NOT_SATISFIED,
    EVALUATOR_CONDITION_NOT_SATISFIED,
    OTHER_NONQUALIFICATION,
)

# ---------------------------------------------------------------------------
# 14.2  Result-level DENY + RESOLVED reasons
# ---------------------------------------------------------------------------
# A path-level reason may additionally be PROMOTED to result level when every
# nonqualifying path and partial evaluation shares exactly one of them
# (15.3 branch 3c), which is what makes a denial legible.

AUTHORITY_NOT_ACTIVE: Final = "AUTHORITY_NOT_ACTIVE"
EMPLOYMENT_NOT_ACTIVE: Final = "EMPLOYMENT_NOT_ACTIVE"
NO_CANDIDATE_ASSIGNMENT: Final = "NO_CANDIDATE_ASSIGNMENT"
NO_QUALIFYING_PATH: Final = "NO_QUALIFYING_PATH"

RESULT_LEVEL_RESOLVED_REASONS: Final = (
    AUTHORITY_NOT_ACTIVE,
    EMPLOYMENT_NOT_ACTIVE,
    NO_CANDIDATE_ASSIGNMENT,
    NO_QUALIFYING_PATH,
)

# ---------------------------------------------------------------------------
# 14.3  DENY + FAIL_CLOSED reasons
# ---------------------------------------------------------------------------

ACTOR_PERSON_PROVIDER_NOT_CONFIGURED: Final = "ACTOR_PERSON_PROVIDER_NOT_CONFIGURED"
HR_REFERENCE_PROVIDER_NOT_CONFIGURED: Final = "HR_REFERENCE_PROVIDER_NOT_CONFIGURED"
ACTOR_PERSON_MAPPING_MISSING: Final = "ACTOR_PERSON_MAPPING_MISSING"
ACTOR_PERSON_MAPPING_AMBIGUOUS: Final = "ACTOR_PERSON_MAPPING_AMBIGUOUS"
HR_REFERENCE_UNAVAILABLE: Final = "HR_REFERENCE_UNAVAILABLE"
HR_REFERENCE_STALE: Final = "HR_REFERENCE_STALE"
EMPLOYMENT_STATE_MISSING: Final = "EMPLOYMENT_STATE_MISSING"
EMPLOYMENT_STATE_AMBIGUOUS: Final = "EMPLOYMENT_STATE_AMBIGUOUS"
POSITION_STATE_MISSING: Final = "POSITION_STATE_MISSING"
POSITION_STATE_AMBIGUOUS: Final = "POSITION_STATE_AMBIGUOUS"
INCUMBENCY_MISSING: Final = "INCUMBENCY_MISSING"
INCUMBENCY_AMBIGUOUS: Final = "INCUMBENCY_AMBIGUOUS"
ORG_UNIT_STATE_MISSING: Final = "ORG_UNIT_STATE_MISSING"
ORG_UNIT_STATE_AMBIGUOUS: Final = "ORG_UNIT_STATE_AMBIGUOUS"
ORG_HIERARCHY_UNRESOLVABLE: Final = "ORG_HIERARCHY_UNRESOLVABLE"
AUTHORITY_CODE_NOT_CONFIGURED: Final = "AUTHORITY_CODE_NOT_CONFIGURED"
AUTHORITY_CONFIGURATION_UNAVAILABLE: Final = "AUTHORITY_CONFIGURATION_UNAVAILABLE"
AUTHORITY_VERSION_AMBIGUOUS: Final = "AUTHORITY_VERSION_AMBIGUOUS"
AUTHORITY_LINEAGE_CONTRADICTORY: Final = "AUTHORITY_LINEAGE_CONTRADICTORY"
AUTHORITY_REFERENCE_DANGLING: Final = "AUTHORITY_REFERENCE_DANGLING"
PUBLICATION_PROVENANCE_INVALID: Final = "PUBLICATION_PROVENANCE_INVALID"
ASSIGNMENT_TARGET_INVALID: Final = "ASSIGNMENT_TARGET_INVALID"
SCOPE_SEMANTICS_UNSUPPORTED: Final = "SCOPE_SEMANTICS_UNSUPPORTED"
SCOPE_CONTEXT_MISSING: Final = "SCOPE_CONTEXT_MISSING"
EVALUATOR_UNKNOWN: Final = "EVALUATOR_UNKNOWN"
EVALUATOR_PAYLOAD_INVALID: Final = "EVALUATOR_PAYLOAD_INVALID"
EVALUATOR_FACTS_INVALID: Final = "EVALUATOR_FACTS_INVALID"
INTERNAL_CONTRACT_VIOLATION: Final = "INTERNAL_CONTRACT_VIOLATION"

FAIL_CLOSED_REASONS: Final = (
    ACTOR_PERSON_PROVIDER_NOT_CONFIGURED,
    HR_REFERENCE_PROVIDER_NOT_CONFIGURED,
    ACTOR_PERSON_MAPPING_MISSING,
    ACTOR_PERSON_MAPPING_AMBIGUOUS,
    HR_REFERENCE_UNAVAILABLE,
    HR_REFERENCE_STALE,
    EMPLOYMENT_STATE_MISSING,
    EMPLOYMENT_STATE_AMBIGUOUS,
    POSITION_STATE_MISSING,
    POSITION_STATE_AMBIGUOUS,
    INCUMBENCY_MISSING,
    INCUMBENCY_AMBIGUOUS,
    ORG_UNIT_STATE_MISSING,
    ORG_UNIT_STATE_AMBIGUOUS,
    ORG_HIERARCHY_UNRESOLVABLE,
    AUTHORITY_CODE_NOT_CONFIGURED,
    AUTHORITY_CONFIGURATION_UNAVAILABLE,
    AUTHORITY_VERSION_AMBIGUOUS,
    AUTHORITY_LINEAGE_CONTRADICTORY,
    AUTHORITY_REFERENCE_DANGLING,
    PUBLICATION_PROVENANCE_INVALID,
    ASSIGNMENT_TARGET_INVALID,
    SCOPE_SEMANTICS_UNSUPPORTED,
    SCOPE_CONTEXT_MISSING,
    EVALUATOR_UNKNOWN,
    EVALUATOR_PAYLOAD_INVALID,
    EVALUATOR_FACTS_INVALID,
    INTERNAL_CONTRACT_VIOLATION,
)

ALL_REASON_CODES: Final = PATH_LEVEL_REASONS + RESULT_LEVEL_RESOLVED_REASONS + FAIL_CLOSED_REASONS

# ---------------------------------------------------------------------------
# 15.5  The CLOSED, EXPLICIT, IMMUTABLE reason-rank table
# ---------------------------------------------------------------------------
# `reason_code_rank` is the third component of the canonical defect sort key.
# The integers below are ASSIGNED DELIBERATELY. They are not derived from the
# alphabetical spelling of a code and not from its position in any tuple
# above; the gaps are intentional spare room so a future code can be inserted
# at a considered position without renumbering the whole table.
#
# The ordering intent, recorded so that a later change is a considered one:
# composition/provider-availability defects rank ahead of canonical-identity
# defects, which rank ahead of HR/organisation state defects, which rank ahead
# of published-authority-state defects, which rank ahead of scope/evaluator
# input defects. INTERNAL_CONTRACT_VIOLATION ranks last among fail-closed
# codes because a genuine authoritative-state defect is always the more
# informative thing to report when both are present.
#
# Nonqualification reasons carry ranks too. They are NEVER defects and never
# enter the defect order (15.5), but 16.5 orders nonqualifying partial
# evaluations by reason_code_rank after their stage and identifiers, so the
# rank must exist for them as well.

REASON_CODE_RANK: Final = {
    # -- fail-closed: composition / provider availability ------------------
    ACTOR_PERSON_PROVIDER_NOT_CONFIGURED: 100,
    HR_REFERENCE_PROVIDER_NOT_CONFIGURED: 110,
    AUTHORITY_CONFIGURATION_UNAVAILABLE: 120,
    HR_REFERENCE_UNAVAILABLE: 130,
    HR_REFERENCE_STALE: 140,
    # -- fail-closed: canonical identity -----------------------------------
    ACTOR_PERSON_MAPPING_MISSING: 200,
    ACTOR_PERSON_MAPPING_AMBIGUOUS: 210,
    # -- fail-closed: canonical HR / organisation state --------------------
    EMPLOYMENT_STATE_MISSING: 300,
    EMPLOYMENT_STATE_AMBIGUOUS: 310,
    POSITION_STATE_MISSING: 320,
    POSITION_STATE_AMBIGUOUS: 330,
    INCUMBENCY_MISSING: 340,
    INCUMBENCY_AMBIGUOUS: 350,
    ORG_UNIT_STATE_MISSING: 360,
    ORG_UNIT_STATE_AMBIGUOUS: 370,
    ORG_HIERARCHY_UNRESOLVABLE: 380,
    # -- fail-closed: published authority state ----------------------------
    AUTHORITY_LINEAGE_CONTRADICTORY: 400,
    PUBLICATION_PROVENANCE_INVALID: 410,
    AUTHORITY_VERSION_AMBIGUOUS: 420,
    AUTHORITY_REFERENCE_DANGLING: 430,
    AUTHORITY_CODE_NOT_CONFIGURED: 440,
    ASSIGNMENT_TARGET_INVALID: 450,
    # -- fail-closed: scope and evaluator input ----------------------------
    SCOPE_SEMANTICS_UNSUPPORTED: 500,
    SCOPE_CONTEXT_MISSING: 510,
    EVALUATOR_UNKNOWN: 520,
    EVALUATOR_PAYLOAD_INVALID: 530,
    EVALUATOR_FACTS_INVALID: 540,
    # -- fail-closed: kernel-internal --------------------------------------
    INTERNAL_CONTRACT_VIOLATION: 900,
    # -- path-level nonqualification (never defects; 16.5 ordering only) ---
    ASSIGNMENT_NOT_EFFECTIVE: 1000,
    ASSIGNMENT_NOT_ACTIVE: 1010,
    ASSIGNMENT_TARGET_NOT_THIS_PERSON: 1020,
    ROLE_NOT_EFFECTIVE: 1030,
    ROLE_NOT_ACTIVE: 1040,
    RULE_NOT_EFFECTIVE: 1050,
    RULE_NOT_ACTIVE: 1060,
    RULE_SCOPE_NOT_MATCHED: 1070,
    ASSIGNMENT_SCOPE_NOT_MATCHED: 1080,
    SCOPE_COMPOSITION_NOT_SATISFIED: 1090,
    EVALUATOR_CONDITION_NOT_SATISFIED: 1100,
    # The bounded fallback ranks LAST among path-level reasons, deliberately:
    # where a specific reason also applies it is the specific one that must be
    # used, and this ordering makes that preference visible in the table.
    OTHER_NONQUALIFICATION: 1110,
    # -- result-level RESOLVED reasons -------------------------------------
    AUTHORITY_NOT_ACTIVE: 1200,
    EMPLOYMENT_NOT_ACTIVE: 1210,
    NO_CANDIDATE_ASSIGNMENT: 1220,
    NO_QUALIFYING_PATH: 1230,
}

# ---------------------------------------------------------------------------
# 15.5  Canonical subject-key vocabulary
# ---------------------------------------------------------------------------
# `subject_form_rank` distinguishes the three mutually-orderable forms of the
# canonical subject key, and is its first component so the three forms are
# totally ordered against one another.

SUBJECT_FORM_OBJECT: Final = 0
SUBJECT_FORM_PATH: Final = 1
SUBJECT_FORM_DEPENDENCY: Final = 2

# Form (c) `subject_token` comes from this CLOSED, fixed-rank vocabulary. No
# value outside it may be used, and no new provider surface may be invented in
# order to name one (PF_1A_E2_A 9.7.0).
SUBJECT_TOKEN_ACTOR_PERSON_PORT: Final = "ACTOR_PERSON_PORT"
SUBJECT_TOKEN_HR_EMPLOYMENT_PORT: Final = "HR_EMPLOYMENT_PORT"
SUBJECT_TOKEN_HR_POSITION_PORT: Final = "HR_POSITION_PORT"
SUBJECT_TOKEN_HR_INCUMBENCY_PORT: Final = "HR_INCUMBENCY_PORT"
SUBJECT_TOKEN_HR_ORG_UNIT_PORT: Final = "HR_ORG_UNIT_PORT"
SUBJECT_TOKEN_AUTHORITY_CONFIGURATION_PORT: Final = "AUTHORITY_CONFIGURATION_PORT"
SUBJECT_TOKEN_KERNEL_INVARIANT: Final = "KERNEL_INVARIANT"

SUBJECT_TOKENS: Final = (
    SUBJECT_TOKEN_ACTOR_PERSON_PORT,
    SUBJECT_TOKEN_HR_EMPLOYMENT_PORT,
    SUBJECT_TOKEN_HR_POSITION_PORT,
    SUBJECT_TOKEN_HR_INCUMBENCY_PORT,
    SUBJECT_TOKEN_HR_ORG_UNIT_PORT,
    SUBJECT_TOKEN_AUTHORITY_CONFIGURATION_PORT,
    SUBJECT_TOKEN_KERNEL_INVARIANT,
)

SUBJECT_TOKEN_RANK: Final = {token: rank for rank, token in enumerate(SUBJECT_TOKENS)}
