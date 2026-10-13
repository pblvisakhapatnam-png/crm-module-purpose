"""Temporal semantics, publication lineage and derived closure.

PF-1A-E2-A sections 11.2 to 11.8. This module owns the SEMANTICS; providers
supply facts only (5.1). A provider that implements a second copy of the rules
below is a blocking defect even if its answers happen to agree, because the
two copies will drift.

THE REJECTED FORMULA. Closure is NOT `min(declared_effective_to, next_start)`.
That formula silently rewrites a genuine, explicitly declared overlap into two
adjacent non-overlapping intervals, which makes the overlap contradiction of
11.6 unreachable for any case other than a duplicate start (F-09). It is
rejected by 11.4 and must never be reintroduced; attack surface 17a probes for
it directly with V1 [t0, t3) and V2 from t2.

ORDER OF OPERATIONS (11.3), which matters and is not optional. The kernel
receives COMPLETE lineage material; validates every retraction and correction
assertion and all provenance; and only THEN derives the current asserted
lineage. An INVALID retraction never removes its target - it fails the whole
resolution closed. A retraction is therefore never a shortcut for making an
inconvenient version disappear, at any layer.

VERSION ORDERING. `object_version` is compared lexicographically over its
canonical string form. That is the only ordering this contract needs (for the
11.8.3 non-decreasing-published_at rule and for the 15.5 sort key), and it is
deterministic and provider-independent. A publisher must therefore use a
lexicographically ordered version identity; the fixtures use zero-padded
numerics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.authorization.business_authority.contract import (
    AUTHORITY_LINEAGE_CONTRADICTORY,
    AUTHORITY_VERSION_AMBIGUOUS,
    PUBLICATION_PROVENANCE_INVALID,
    PUBLICATION_REFERENCE_TYPES,
)
from app.modules.authorization.business_authority.domain import (
    LineageMaterial,
    PublishedObjectVersion,
    RetractionAssertion,
)
from app.modules.hr_reference.contract import is_utc_normalized_instant


@dataclass(frozen=True)
class LineageDefect:
    """One detected lineage/provenance defect, attributed to a version where it has one.

    `object_version` is None for a defect about the object's lineage AS A
    WHOLE rather than about one version. That distinction is load-bearing for
    the 15.5 sort key, where an unestablished object_version sorts as the
    empty/lowest value so lineage-level defects precede version-level defects
    for the same object.
    """

    reason_code: str
    object_version: str | None
    detail: str


@dataclass(frozen=True)
class AssertedInterval:
    """A version together with its DERIVED asserted end (never stored)."""

    version: PublishedObjectVersion
    asserted_effective_to: datetime | None


@dataclass(frozen=True)
class LineageEvaluation:
    """The complete outcome of validating and evaluating one object's lineage."""

    defects: tuple[LineageDefect, ...]
    current_asserted: tuple[PublishedObjectVersion, ...]
    asserted_intervals: tuple[AssertedInterval, ...]
    effective_version: PublishedObjectVersion | None
    is_dangling: bool
    # The RECORDED `retracted_at` of every VALID retraction assertion that
    # participated in establishing this object's current asserted lineage, in a
    # deterministic canonical order that does not depend on provider order
    # (16.2, 16.5). Populated only once the whole lineage has validated, so an
    # INVALID assertion can never reach successful evidence: it fails the
    # resolution closed instead (11.3).
    participating_retracted_at: tuple[datetime, ...] = ()

    @property
    def has_defect(self) -> bool:
        return bool(self.defects)


# ---------------------------------------------------------------------------
# 11.7 / 11.8.3  Provenance validation
# ---------------------------------------------------------------------------
# Stated field by field so no shape can be assumed covered by another (F-10.1).
# An ABSENT publication_reference_type and an UNKNOWN publication_reference_type
# are TWO DISTINCT malformed states. A kernel that validates only membership in
# the two defined values passes the unknown-value case while failing the
# absent-type one - precisely the gap the fourth independent review found.


def _validate_version_provenance(version: PublishedObjectVersion) -> list[LineageDefect]:
    defects: list[LineageDefect] = []
    label = version.object_version

    if version.publication_reference_type is None:
        defects.append(
            LineageDefect(
                PUBLICATION_PROVENANCE_INVALID,
                label,
                "version publication_reference_type is absent",
            )
        )
    elif version.publication_reference_type not in PUBLICATION_REFERENCE_TYPES:
        defects.append(
            LineageDefect(
                PUBLICATION_PROVENANCE_INVALID,
                label,
                "version publication_reference_type is outside the two defined values",
            )
        )

    if version.publication_reference_id is None:
        defects.append(
            LineageDefect(
                PUBLICATION_PROVENANCE_INVALID,
                label,
                "version publication_reference_id is absent",
            )
        )

    if version.published_at is None:
        defects.append(
            LineageDefect(
                PUBLICATION_PROVENANCE_INVALID, label, "version published_at is absent"
            )
        )
    elif not is_utc_normalized_instant(version.published_at):
        # 11.8.3 requires recorded timestamps to be "timezone-aware, normalized
        # to UTC, and NOT NULL", in those terms. A NAIVE value names no instant,
        # so the ordering constraints below could not be evaluated against it at
        # all; an AWARE value carrying a non-zero offset is comparable but is
        # still not the UTC-normalized provenance 11.8.3 requires. Both are
        # invalid provenance and neither is rewritten to conform (correction
        # C2-2, reconciled field-by-field in C2 final).
        defects.append(
            LineageDefect(
                PUBLICATION_PROVENANCE_INVALID,
                label,
                "version published_at is not a UTC-normalized timezone-aware instant",
            )
        )

    return defects


def _validate_retraction_provenance(assertion: RetractionAssertion) -> list[LineageDefect]:
    defects: list[LineageDefect] = []
    label = assertion.object_version

    if assertion.publication_reference_type is None:
        defects.append(
            LineageDefect(
                PUBLICATION_PROVENANCE_INVALID,
                label,
                "retraction publication_reference_type is absent",
            )
        )
    elif assertion.publication_reference_type not in PUBLICATION_REFERENCE_TYPES:
        defects.append(
            LineageDefect(
                PUBLICATION_PROVENANCE_INVALID,
                label,
                "retraction publication_reference_type is outside the two defined values",
            )
        )

    if assertion.publication_reference_id is None:
        defects.append(
            LineageDefect(
                PUBLICATION_PROVENANCE_INVALID,
                label,
                "retraction publication_reference_id is absent",
            )
        )

    if assertion.retracted_at is None:
        defects.append(
            LineageDefect(
                PUBLICATION_PROVENANCE_INVALID, label, "retraction retracted_at is absent"
            )
        )
    elif not is_utc_normalized_instant(assertion.retracted_at):
        # Same 11.8.3 rule as published_at above; retracted_at is named in the
        # same sentence and takes the identical treatment.
        defects.append(
            LineageDefect(
                PUBLICATION_PROVENANCE_INVALID,
                label,
                "retraction retracted_at is not a UTC-normalized timezone-aware instant",
            )
        )

    return defects


def _validate_recorded_timestamps(
    versions: tuple[PublishedObjectVersion, ...],
    retractions: tuple[RetractionAssertion, ...],
) -> list[LineageDefect]:
    """The 11.8.3 validity constraints on RECORDED timestamps.

    These are VALIDATION only. They never select which version is
    business-effective, and they never act as a filter on lineage material
    (11.8, acceptance criterion F). Nothing here ties `published_at` to
    `effective_from`: a version published today may assert any
    business-effective interval, past or future, because a backdated
    correction is normal and expected.
    """

    defects: list[LineageDefect] = []
    by_version = {v.object_version: v for v in versions}

    # Only CONFORMING recorded timestamps take part in the ordering constraints
    # below, under the same 11.8.3 rule the per-record checks applied. A
    # nonconforming one has already been reported as invalid provenance there;
    # a naive one would raise rather than classify if compared here, and a
    # non-UTC one must not silently satisfy an ordering constraint it was never
    # eligible to participate in (correction C2-2).
    def _recorded(value: object) -> object:
        return value if is_utc_normalized_instant(value) else None

    # published_at must be NON-DECREASING in object_version order. Version
    # numbers are assigned in publication order, so a higher object_version
    # whose published_at precedes that of a lower one is contradictory.
    ordered = sorted(
        (v for v in versions if _recorded(v.published_at) is not None),
        key=lambda v: v.object_version or "",
    )
    for earlier, later in zip(ordered, ordered[1:]):
        if later.published_at < earlier.published_at:  # type: ignore[operator]
            defects.append(
                LineageDefect(
                    PUBLICATION_PROVENANCE_INVALID,
                    later.object_version,
                    "published_at decreases across increasing object_version",
                )
            )

    # A retraction recorded BEFORE the thing it retracts was published is
    # impossible provenance. Equal timestamps are permitted.
    for assertion in retractions:
        target = by_version.get(assertion.object_version)
        if (
            target is None
            or _recorded(assertion.retracted_at) is None
            or _recorded(target.published_at) is None
        ):
            continue
        if assertion.retracted_at < target.published_at:
            defects.append(
                LineageDefect(
                    PUBLICATION_PROVENANCE_INVALID,
                    assertion.object_version,
                    "retracted_at precedes the published_at of the version it retracts",
                )
            )

    # A correction recorded BEFORE its target was retracted is impossible
    # provenance (correction is retract-then-republish, 11.6).
    retracted_at_by_version: dict[str, datetime] = {}
    for assertion in retractions:
        if assertion.object_version is None or _recorded(assertion.retracted_at) is None:
            continue
        existing = retracted_at_by_version.get(assertion.object_version)
        if existing is None or assertion.retracted_at < existing:
            retracted_at_by_version[assertion.object_version] = assertion.retracted_at

    for version in versions:
        target_version = version.corrects_object_version
        if target_version is None or _recorded(version.published_at) is None:
            continue
        target_retracted_at = retracted_at_by_version.get(target_version)
        if target_retracted_at is None:
            continue
        if version.published_at < target_retracted_at:
            defects.append(
                LineageDefect(
                    PUBLICATION_PROVENANCE_INVALID,
                    version.object_version,
                    "correcting version published_at precedes its target retracted_at",
                )
            )

    return defects


# ---------------------------------------------------------------------------
# 11.6  Structural lineage contradictions
# ---------------------------------------------------------------------------


def _validate_structure(
    versions: tuple[PublishedObjectVersion, ...],
    retractions: tuple[RetractionAssertion, ...],
) -> list[LineageDefect]:
    defects: list[LineageDefect] = []

    # A duplicate (object_id, object_version) pair within one lineage. The
    # provider-neutral counterpart of a store's identity/version uniqueness
    # key: versions[] is a LIST, so two entries sharing one object_version are
    # trivially constructible (class B1, fixture DUPLICATE-OBJECT-VERSION).
    seen_versions: set[str] = set()
    duplicated: set[str] = set()
    for version in versions:
        key = version.object_version or ""
        if key in seen_versions and key not in duplicated:
            duplicated.add(key)
            defects.append(
                LineageDefect(
                    AUTHORITY_LINEAGE_CONTRADICTORY,
                    version.object_version,
                    "duplicate object_version within one object's material",
                )
            )
        seen_versions.add(key)

    # A version whose own declared_effective_to <= its own effective_from
    # (invariant I-6). This covers BOTH an end before the start and the empty
    # end == start interval, and is the 11.4 NONSENSICAL DECLARED INTERVAL
    # pre-check (class B1, fixtures INTERVAL-END-BEFORE-START and
    # INTERVAL-END-EQUALS-START). A malformed interval fails closed; it is
    # never repaired.
    for version in versions:
        if version.declared_effective_to is None or version.effective_from is None:
            continue
        if version.declared_effective_to <= version.effective_from:
            defects.append(
                LineageDefect(
                    AUTHORITY_LINEAGE_CONTRADICTORY,
                    version.object_version,
                    "declared_effective_to is not strictly greater than effective_from",
                )
            )

    known_versions = {v.object_version for v in versions}

    # A retraction assertion referencing a version that does not exist.
    for assertion in retractions:
        if assertion.object_version not in known_versions:
            defects.append(
                LineageDefect(
                    AUTHORITY_LINEAGE_CONTRADICTORY,
                    assertion.object_version,
                    "retraction assertion targets a version that does not exist",
                )
            )

    # More than one retraction assertion for the same (object_id, object_version).
    retraction_counts: dict[str, int] = {}
    for assertion in retractions:
        key = assertion.object_version or ""
        retraction_counts[key] = retraction_counts.get(key, 0) + 1
    for version_key, count in retraction_counts.items():
        if count > 1:
            defects.append(
                LineageDefect(
                    AUTHORITY_LINEAGE_CONTRADICTORY,
                    version_key or None,
                    "more than one retraction assertion for one version",
                )
            )

    # Correction lineage. A correcting version's target must EXIST and must
    # itself be RETRACTED - correction is retract-then-republish (11.6).
    retracted_versions = {a.object_version for a in retractions}
    for version in versions:
        target = version.corrects_object_version
        if target is None:
            continue
        if target not in known_versions:
            defects.append(
                LineageDefect(
                    AUTHORITY_LINEAGE_CONTRADICTORY,
                    version.object_version,
                    "corrects_object_version target does not exist",
                )
            )
        elif target not in retracted_versions:
            defects.append(
                LineageDefect(
                    AUTHORITY_LINEAGE_CONTRADICTORY,
                    version.object_version,
                    "corrects_object_version target exists but is not retracted",
                )
            )

    return defects


# ---------------------------------------------------------------------------
# 11.4  Derived asserted closure
# ---------------------------------------------------------------------------


def _derive_asserted_intervals(
    current_asserted: tuple[PublishedObjectVersion, ...],
) -> tuple[tuple[AssertedInterval, ...], list[LineageDefect]]:
    """Apply the 11.4 ASSERTED INTERVAL RULE to a duplicate-start-free lineage.

    Four branches, exactly as the contract states them:

        NO SUCCESSOR             declared NULL      -> open-ended
                                 declared non-null  -> honoured as declared
        SUCCESSOR EXISTS         declared NULL      -> successor CLOSES it      VALID
                                 declared < next    -> honoured; VALID GAP      VALID
                                 declared == next   -> explicit ADJACENCY       VALID
                                 declared >  next   -> EXPLICIT OVERLAP    FAIL CLOSED

    The overlap branch never truncates, never normalizes to next_start, never
    prefers either version and never repairs. Correction is a governed
    append-only act, not a resolution-time adjustment.
    """

    defects: list[LineageDefect] = []
    ordered = sorted(current_asserted, key=lambda v: (v.effective_from, v.object_version or ""))

    intervals: list[AssertedInterval] = []
    for index, version in enumerate(ordered):
        next_start = ordered[index + 1].effective_from if index + 1 < len(ordered) else None

        if next_start is None:
            asserted_end = version.declared_effective_to
        elif version.declared_effective_to is None:
            asserted_end = next_start
        elif version.declared_effective_to > next_start:
            defects.append(
                LineageDefect(
                    AUTHORITY_LINEAGE_CONTRADICTORY,
                    version.object_version,
                    "declared_effective_to is later than the next valid successor start "
                    "(explicit overlap)",
                )
            )
            asserted_end = version.declared_effective_to
        else:
            asserted_end = version.declared_effective_to

        intervals.append(AssertedInterval(version=version, asserted_effective_to=asserted_end))

    return tuple(intervals), defects


def is_effective(interval: AssertedInterval, as_of: datetime) -> bool:
    """The 11.2 half-open EFFECTIVE predicate.

        effective_from   INCLUSIVE
        asserted_to      EXCLUSIVE, nullable ("no known end")

    This is a purely TEMPORAL/lineage predicate. It says nothing whatsoever
    about `active_flag`; grant-eligibility is lineage-valid AND effective AND
    active, and the three must never be merged into one predicate because a
    reader of the evidence must be able to see which condition failed (8.2).
    """

    version = interval.version
    if version.effective_from is None or version.effective_from > as_of:
        return False
    if interval.asserted_effective_to is None:
        return True
    return as_of < interval.asserted_effective_to


def _select_effective(
    intervals: tuple[AssertedInterval, ...], as_of: datetime
) -> tuple[PublishedObjectVersion | None, list[LineageDefect]]:
    """Select the single effective version, defending the 11.4a theorem.

    The residual "more than one effective version" clause of 11.6 is PROVED
    UNREACHABLE from any provider input by the single-effective-version
    theorem of 11.4a. It is retained here DELIBERATELY as a defensive kernel
    invariant and MUST NOT be deleted as dead code: it is the one guard that
    would catch a future refactor of ordering, closure or retraction
    validation silently granting authority from an ambiguous lineage.

    Its reason code is normative, not implementer's choice:
    AUTHORITY_VERSION_AMBIGUOUS - not AUTHORITY_LINEAGE_CONTRADICTORY, which
    is reserved for the contradictions the pre-checks and the overlap branch
    DO reach, and not INTERNAL_CONTRACT_VIOLATION, which is reserved for a
    violated kernel invariant that is not about authority-version
    multiplicity.
    """

    effective = [interval.version for interval in intervals if is_effective(interval, as_of)]

    if len(effective) > 1:
        return None, [
            LineageDefect(
                AUTHORITY_VERSION_AMBIGUOUS,
                None,
                "more than one version of the current asserted lineage is effective at as_of",
            )
        ]

    return (effective[0] if effective else None), []


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def evaluate_lineage(material: LineageMaterial, as_of: datetime) -> LineageEvaluation:
    """Validate one object's complete lineage and resolve its effective version.

    Returns every defect detected, not merely the first: two distinct
    fail-closed defects on ONE object must both reach the 15.5 total order so
    the reason_code_rank tie-break can decide between them deterministically
    (NS-DO-02).
    """

    versions = tuple(material.versions)
    retractions = tuple(material.retraction_assertions)

    # DANGLING: no lineage material exists for this stable identity at all.
    # This is established from COMPLETE material, never from a discovery-time
    # exclusion (11.5). The caller classifies it, because whether a dangling
    # reference is a defect depends on which family referenced it.
    if not versions:
        return LineageEvaluation(
            defects=(),
            current_asserted=(),
            asserted_intervals=(),
            effective_version=None,
            is_dangling=True,
        )

    defects: list[LineageDefect] = []
    defects.extend(_validate_structure(versions, retractions))
    for version in versions:
        defects.extend(_validate_version_provenance(version))
    for assertion in retractions:
        defects.extend(_validate_retraction_provenance(assertion))
    defects.extend(_validate_recorded_timestamps(versions, retractions))

    if defects:
        # Closure is not derived over material already known to be
        # contradictory: 11.3 fixes the order of operations, and deriving
        # closure from invalid assertions would be meaningless.
        return LineageEvaluation(
            defects=tuple(defects),
            current_asserted=(),
            asserted_intervals=(),
            effective_version=None,
            is_dangling=False,
        )

    # CURRENT ASSERTED LINEAGE: the versions carrying no VALID retraction
    # assertion, established only AFTER every retraction has been validated.
    retracted = {a.object_version for a in retractions}
    current_asserted = tuple(v for v in versions if v.object_version not in retracted)

    # Every assertion reaching this point has been validated, so every one of
    # them PARTICIPATED in establishing the current asserted lineage. Their
    # recorded times are ordered by the assertion's own canonical identity
    # rather than by value or by provider order, so the evidence is stable
    # under a shuffled provider (16.5).
    participating_retracted_at = tuple(
        assertion.retracted_at
        for assertion in sorted(
            retractions, key=lambda a: (a.object_version or "", a.retraction_id or "")
        )
        if assertion.retracted_at is not None
    )

    if not current_asserted:
        # Every version retracted with no replacement lineage record.
        return LineageEvaluation(
            defects=(),
            current_asserted=(),
            asserted_intervals=(),
            effective_version=None,
            is_dangling=True,
            participating_retracted_at=participating_retracted_at,
        )

    # PRE-CHECK: DUPLICATE START. Two or more versions of the current asserted
    # lineage sharing one effective_from. Closure is NOT derived and NO
    # tie-break is attempted.
    starts: dict[datetime, int] = {}
    for version in current_asserted:
        starts[version.effective_from] = starts.get(version.effective_from, 0) + 1
    if any(count > 1 for count in starts.values()):
        # Exactly ONE lineage-level defect, however many starts are
        # duplicated. Emitting one per duplicated instant would produce two
        # defect records with an identical canonical sort key, which 15.5
        # forbids: the condition is a property of this object's lineage as a
        # whole, not of any one version.
        return LineageEvaluation(
            defects=(
                LineageDefect(
                    AUTHORITY_LINEAGE_CONTRADICTORY,
                    None,
                    "two versions of the current asserted lineage share one effective_from",
                ),
            ),
            current_asserted=current_asserted,
            asserted_intervals=(),
            effective_version=None,
            is_dangling=False,
            participating_retracted_at=participating_retracted_at,
        )

    intervals, closure_defects = _derive_asserted_intervals(current_asserted)
    if closure_defects:
        return LineageEvaluation(
            defects=tuple(closure_defects),
            current_asserted=current_asserted,
            asserted_intervals=intervals,
            effective_version=None,
            is_dangling=False,
            participating_retracted_at=participating_retracted_at,
        )

    effective_version, multiplicity_defects = _select_effective(intervals, as_of)
    return LineageEvaluation(
        defects=tuple(multiplicity_defects),
        current_asserted=current_asserted,
        asserted_intervals=intervals,
        effective_version=effective_version,
        is_dangling=False,
        participating_retracted_at=participating_retracted_at,
    )
