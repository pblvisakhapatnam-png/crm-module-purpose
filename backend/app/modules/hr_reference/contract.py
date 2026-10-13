"""Canonical HR / organisation reference DTOs and lookup outcomes.

PF-1A-E2-A sections 7, 9.1 and 9.2. Every value crossing this boundary is
canonical and platform-owned. Provider identifiers, provider field names and
raw provider timestamps never appear here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

# ---------------------------------------------------------------------------
# Lookup outcome status
# ---------------------------------------------------------------------------
# Every canonical HR operation answers with one of these. Four of the five are
# explicit failure states that the authority kernel converts into fail-closed
# reason codes (PF_1A_E2_A 9.2); none of them is ever silently treated as an
# absent-but-acceptable answer.

HR_LOOKUP_OK: Final = "OK"
HR_LOOKUP_MISSING: Final = "MISSING"
HR_LOOKUP_AMBIGUOUS: Final = "AMBIGUOUS"
HR_LOOKUP_UNAVAILABLE: Final = "UNAVAILABLE"
HR_LOOKUP_STALE: Final = "STALE"

HR_LOOKUP_STATUSES: Final = (
    HR_LOOKUP_OK,
    HR_LOOKUP_MISSING,
    HR_LOOKUP_AMBIGUOUS,
    HR_LOOKUP_UNAVAILABLE,
    HR_LOOKUP_STALE,
)

# ---------------------------------------------------------------------------
# Canonical employment status values
# ---------------------------------------------------------------------------
# ACTIVE is the only status that permits a grant path to continue. The other
# three are UNAMBIGUOUSLY RESOLVED non-active answers, which produce an
# ordinary DENY + RESOLVED / EMPLOYMENT_NOT_ACTIVE - never a fail-closed
# result (PF_1A_E2_A 14.4, distinction 1: known-and-no is not not-known).

EMPLOYMENT_ACTIVE: Final = "ACTIVE"
EMPLOYMENT_INACTIVE: Final = "INACTIVE"
EMPLOYMENT_ON_LEAVE: Final = "ON_LEAVE"
EMPLOYMENT_LEFT: Final = "LEFT"

EMPLOYMENT_STATUSES: Final = (
    EMPLOYMENT_ACTIVE,
    EMPLOYMENT_INACTIVE,
    EMPLOYMENT_ON_LEAVE,
    EMPLOYMENT_LEFT,
)


@dataclass(frozen=True)
class ActorPersonReference:
    """The canonical person an authenticated application actor maps to.

    `person_id` is platform-owned (ADR-032) and is NEVER supplied by a client.
    The only input to the resolving port is the authenticated actor's own
    application-user public identifier, taken from the server-side
    authenticated context (PF_1A_E2_A 9.1, 7.1).
    """

    actor_user_public_id: str
    person_id: str
    canonical_snapshot_at: datetime
    reference_evidence: str


@dataclass(frozen=True)
class EmploymentStateReference:
    """Canonical employment state effective at the evaluation instant."""

    person_id: str
    employment_state_version_id: str
    employment_status: str
    canonical_snapshot_at: datetime


@dataclass(frozen=True)
class PositionVersionReference:
    """Canonical Position Version effective at the evaluation instant."""

    position_id: str
    position_version_id: str
    org_unit_id: str | None
    canonical_snapshot_at: datetime


@dataclass(frozen=True)
class IncumbencyReference:
    """Canonical Position Incumbency effective at the evaluation instant.

    A position assignment NEVER confers authority on a former incumbent:
    incumbency is re-resolved at the same single `as_of` on every resolution
    and is never inferred from history (PF_1A_E2_A 12.1).
    """

    position_id: str
    incumbency_id: str
    person_id: str
    canonical_snapshot_at: datetime


@dataclass(frozen=True)
class OrgUnitVersionReference:
    """Canonical Organisation Unit Version effective at the evaluation instant."""

    org_unit_id: str
    org_unit_version_id: str
    parent_org_unit_id: str | None
    canonical_snapshot_at: datetime


@dataclass(frozen=True)
class HrLookup:
    """A canonical HR answer plus its explicit outcome status.

    `value` is populated only when `status == HR_LOOKUP_OK`. Consumers must
    branch on `status`; there is deliberately no "empty means missing"
    convention, because MISSING, AMBIGUOUS, UNAVAILABLE and STALE carry
    different fail-closed reason codes.
    """

    status: str
    value: object | None = None

    @property
    def is_ok(self) -> bool:
        return self.status == HR_LOOKUP_OK


# ---------------------------------------------------------------------------
# Temporal shape (correction C2-2, reconciled field-by-field in C2 final)
# ---------------------------------------------------------------------------
# E2-A states TWO DIFFERENT temporal requirements, and they must not be
# conflated in either direction. There are therefore two predicates, and each
# caller applies the one its own field's normative text requires:
#
#   AWARE ONLY          effective_from            "inclusive, timezone-aware"   (E2-A 8.1)
#                       declared_effective_to     same table; awareness is also
#                                                 required by necessary implication,
#                                                 because I-6 and the 11.4 asserted-
#                                                 interval rule COMPARE it against
#                                                 effective_from, the successor's start
#                                                 and as_of
#                       canonical_snapshot_at     E2-A 7 / 9.1 / 9.2 state only that it
#                                                 is the canonical freshness indicator;
#                                                 awareness is required because the
#                                                 staleness rule subtracts it from as_of
#
#   UTC-NORMALIZED      as_of                     "It is timezone-aware and normalized to
#                                                 UTC" (E2-A 11.1)
#                       published_at              "timezone-aware, normalized to UTC, and
#                       retracted_at              NOT NULL" (E2-A 11.8.3)
#
# THE FIRST GROUP MUST NOT BE HELD TO THE SECOND GROUP'S RULE. A +05:30
# `effective_from` is a valid business-effective instant under 8.1; rejecting
# it would invent a requirement the contract does not state, and would reject
# conforming configuration data. Equally, the second group must not be relaxed
# to the first group's rule merely because Python could still compare the
# value: 11.1 and 11.8.3 say "normalized to UTC" in terms, and this
# implementation does not get to soften that.
#
# NEITHER PREDICATE EVER REWRITES ITS INPUT. A nonconforming value is reported
# through the field's existing fail-closed reason code; it is never quietly
# converted, because 11.8 forbids silently reinterpreting a supplied instant
# and because rewriting provider material to make malformed provenance conform
# would destroy the very evidence the check exists to surface.


def is_conforming_instant(value: object) -> bool:
    """Is `value` a usable business-effective instant - i.e. TIMEZONE-AWARE?

    The weaker of the two predicates, for the fields E2-A requires to be
    timezone-aware without also requiring UTC normalization: `effective_from`
    (8.1), `declared_effective_to` and `canonical_snapshot_at`.

    A NAIVE datetime is invalid: it names no instant, so comparing it against
    the authorization instant is either an error or a silent guess about which
    timezone was meant. The independent review reproduced exactly that - a
    naive `effective_from` raising an uncaught TypeError against the
    timezone-aware authorization instant.

    An AWARE datetime whose offset is not zero is ACCEPTED here and is not
    rewritten. It denotes an unambiguous instant, Python compares aware
    datetimes by absolute instant regardless of offset, and 8.1 requires only
    awareness for these fields. Do not tighten this to UTC without an E2-A
    section that says so for the specific field.

    `bool` is deliberately excluded along with every other non-datetime type,
    and `datetime` subclasses are accepted only if they are genuinely aware.
    """

    if not isinstance(value, datetime):
        return False
    return value.utcoffset() is not None


def is_utc_normalized_instant(value: object) -> bool:
    """Is `value` timezone-aware AND normalized to UTC?

    The stronger predicate, required in terms by E2-A 11.1 for the single
    authorization `as_of` and by E2-A 11.8.3 for `published_at` and
    `retracted_at`.

    "Normalized to UTC" is read here as a ZERO UTC OFFSET at the instant
    represented, which is what the value actually asserts about itself; the
    concrete `tzinfo` object is not constrained, so `timezone.utc`, a fixed
    zero-offset `timezone`, and a zone whose offset is zero at that moment are
    all accepted alike. What is rejected is a value that presents a NON-ZERO
    offset, because that is not a UTC-normalized value however comparable it
    might be.

    A nonconforming value is REPORTED, never normalized. Converting a supplied
    +05:30 `published_at` into UTC here would manufacture conformance for
    material the provider published nonconforming, which is precisely the
    silent reinterpretation 11.8 forbids.
    """

    if not isinstance(value, datetime):
        return False
    offset = value.utcoffset()
    return offset is not None and offset == timedelta(0)


def is_snapshot_stale(
    canonical_snapshot_at: datetime, as_of: datetime, threshold_seconds: int | None
) -> bool:
    """Apply a SUPPLIED canonical-snapshot staleness threshold.

    Lives here, on the canonical freshness indicator itself, because EVERY
    canonical HR/reference response actually relied upon by a resolution must
    be checked against the SAME supplied threshold and the SAME authoritative
    `as_of` - actor/person mapping, employment state, Position Version,
    Incumbency, and every Organisation Unit Version traversed for scope
    ancestry (PF_1A_E2_A 7, 9.2, 11.1). A per-caller copy of this rule is how
    one of those seams comes to be missed.

    The threshold VALUE remains a deferred policy parameter (section 7,
    section 23). When none is supplied the kernel applies none and relies on
    the provider's own explicit STALE answer: it INVENTS NO DEFAULT.

    `as_of` is the single authoritative BUSINESS-EFFECTIVE instant. The
    canonical snapshot indicator is RECORDED time and is compared against it
    only to answer "is this state too old to rely on"; it never becomes a
    second authorization clock and never selects which version is effective
    (11.8).
    """

    if threshold_seconds is None:
        return False
    return (as_of - canonical_snapshot_at) > timedelta(seconds=threshold_seconds)


def ok(value: object) -> HrLookup:
    return HrLookup(status=HR_LOOKUP_OK, value=value)


def missing() -> HrLookup:
    return HrLookup(status=HR_LOOKUP_MISSING)


def ambiguous() -> HrLookup:
    return HrLookup(status=HR_LOOKUP_AMBIGUOUS)


def unavailable() -> HrLookup:
    return HrLookup(status=HR_LOOKUP_UNAVAILABLE)


def stale() -> HrLookup:
    return HrLookup(status=HR_LOOKUP_STALE)
