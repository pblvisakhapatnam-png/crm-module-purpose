"""Frozen, inert domain objects for the governed configuration lifecycle (PF-1A-E3).

No dataclass validates a business rule at construction. Risk, eligibility, independence,
lineage and duplication belong to `configuration_policy` and `configuration_service`; a
convenience validator here would be a second, quieter copy of those rules.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class ConfigurationGovernanceError(RuntimeError):
    """A structurally invalid request - NOT a governance refusal.

    A refusal is a recorded governance answer ("this may not activate, and here is why"). This
    means the request was not a well-formed governed request at all: an unknown object family,
    an unknown change type, a payload field that does not exist, an unknown change identifier.
    """


@dataclass(frozen=True)
class ConfigurationChangeProposal:
    configuration_object_family: str
    configuration_object_id: str
    change_type: str
    change_payload: Mapping[str, Any]
    effective_from: datetime
    declared_effective_to: datetime | None = None
    # What the proposer believes is current. Compared at activation against the object's actual
    # current sequence, which is what stops a stale writer publishing over a version it never
    # saw.
    previous_object_version_expected: str | None = None


@dataclass(frozen=True)
class PublishedRow:
    """One raw published version row. `retracted` is a FACT, not a validity judgement.

    Every column the PF-1A-E2-A lineage kernel validates is carried, unchanged and
    uninterpreted, because PF-1A-E3 derives its authority graph by handing this material to that
    kernel rather than by ranking rows itself. An absent provenance or recorded-time value is
    therefore carried as `None` and classified there, never defaulted or repaired here.

    THERE IS DELIBERATELY NO `publication_sequence` FIELD, AND NONE MAY BE ADDED. An earlier
    revision carried the store's physical append order and used "the latest non-retracted row"
    as the current authority graph. That is not what PF-1A-E2 means by current: a later-published
    but FUTURE-effective (or inactive, or reassigned) successor would silently erase a version
    that is genuinely effective now, under-computing risk in exactly the direction that permits a
    single-person self-affecting publication. Currency is a lineage/effectiveness question and is
    answered only by `lineage.evaluate_lineage`.
    """

    object_family: str
    object_id: str
    object_version: str
    active_flag: bool | None
    retracted: bool
    effective_from: datetime | None
    declared_effective_to: datetime | None
    payload: Mapping[str, Any]
    corrects_object_version: str | None = None
    publication_reference_type: str | None = None
    publication_reference_id: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True)
class RetractionRow:
    """One raw retraction assertion row, carried as a FACT for the kernel to validate.

    It is never applied here as a filter. An INVALID retraction must fail the whole resolution
    closed rather than quietly removing its target (PF-1A-E2-A 11.3), which is only possible if
    the assertion reaches the kernel intact.
    """

    object_family: str
    object_id: str
    object_version: str | None
    retraction_id: str | None
    retracted_at: datetime | None = None
    publication_reference_type: str | None = None
    publication_reference_id: str | None = None


@dataclass(frozen=True)
class AllocationAnchor:
    """The ALL-TIME lexicographically greatest published identity of one object, and its
    `published_at`.

    DELIBERATELY NOT THE AUTHORITATIVE PREDECESSOR, and never to be used as one. It includes
    RETRACTED versions, because the kernel validates provenance across every published version:
    a new identity must sort after all of them, and a new `published_at` must not precede the
    one recorded against this anchor. Which version an UPDATE may legitimately supersede is a
    separate question, answered from the validated current asserted lineage.

    Both fields are `None` when the object has no published version at all.
    """

    object_version: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True)
class EffectiveConfigurationState:
    """The authority graph, derived through the UNCHANGED PF-1A-E2-A lineage kernel.

    `effective_rows` holds, per stable object, the single version EFFECTIVE at the context's
    `as_of` - lineage-valid, current-asserted and temporally effective. `predecessor_rows` holds
    the authoritative predecessor: the temporally last version of the validated CURRENT ASSERTED
    lineage, which is what an UPDATE or DEACTIVATE supersedes. The two are different questions
    and are answered separately; an object may have a predecessor and no effective version (a
    lapsed interval), or an effective version that is not the predecessor (a future-effective
    successor already exists).

    `unresolved` names every object whose lineage could not be established under E2 semantics.
    An entry here fails the whole governed action closed; it is never treated as "this object
    has nothing".
    """

    effective_rows: Mapping[tuple[str, str], PublishedRow] = field(default_factory=dict)
    predecessor_rows: Mapping[tuple[str, str], PublishedRow] = field(default_factory=dict)
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuthorityContext:
    """Current authoritative state, as at ONE instant, for ONE recomputation.

    `unresolved` is the fail-closed channel: any dependency that could not be established
    appears here and no governed action proceeds. An empty `unresolved` is the only state in
    which a classification may be trusted.

    `rows` and `retractions` are the RAW material, complete and unfiltered. `effective_state` is
    what the E2 kernel made of it at `as_of`; every governed rule reads that, never the raw rows,
    except the deliberately over-inclusive protection scan.
    """

    as_of: datetime
    rows: tuple[PublishedRow, ...]
    incumbent_person_by_position: Mapping[str, str | None]
    protected_candidate_codes: tuple[str, ...]
    unresolved: tuple[str, ...]
    fingerprint: str
    context_reference: Mapping[str, Any]
    retractions: tuple[RetractionRow, ...] = ()
    effective_state: EffectiveConfigurationState = field(
        default_factory=EffectiveConfigurationState
    )

    @property
    def is_resolved(self) -> bool:
        return not self.unresolved


@dataclass(frozen=True)
class RiskClassification:
    """A FRESHLY RECOMPUTED verdict. Never a stored boolean read back."""

    is_self_affecting: bool
    affects_protected_meta_authority: bool
    privilege_increasing: bool
    authorization_required: bool
    derivation: tuple[str, ...] = ()


@dataclass(frozen=True)
class GovernanceEvaluation:
    stage: str
    evaluated_at: datetime
    acting_person_id: str | None
    acting_actor_user_public_id: str | None
    risk: RiskClassification
    authorizer_eligible: bool
    authorizer_is_different_person: bool
    dependencies_current: bool
    authorization_satisfied: bool
    outcome: str
    refusal_reason: str | None
    dependency_fingerprint: str
    context_reference: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConfigurationChangeOutcome:
    accepted: bool
    configuration_change_id: str | None
    lifecycle_status: str | None
    evaluation: GovernanceEvaluation | None = None
    refusal_reason: str | None = None
    published_object_version: str | None = None
