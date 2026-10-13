"""The authority configuration PORT: raw discovery plus complete lineage material.

PF-1A-E2-A section 9.3.

The first candidate for this contract exposed `list_effective_*` operations.
That was a blocking defect (F-02): a provider answering "the effective rows"
must itself decide what EFFECTIVE means, and can therefore hide duplicate
effective versions, interval overlap, broken supersession, contradictory
correction/retraction assertions and invalid provenance - exactly the defects
the kernel is REQUIRED to detect.

The single sentence a provider implementer should remember (9.5):

    LOCATING a fact is permitted; JUDGING a fact is not.

This port defines NO create/update/deactivate/publish/delete operation, and
none may be added. The E2 authority world is read-only in production terms;
the only writers are deterministic test fixtures and, later, PF-1A-E3's
governed Configuration Change activation (section 5, acceptance criterion Q).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.modules.authorization.business_authority.domain import (
    LineageMaterial,
    PublishedObjectVersion,
)


class AuthorityConfigurationPortError(Exception):
    """A provider read failed as a PORT rather than returning bad data.

    Raised for a transport-level failure: a connection error, a timeout, or
    any other condition in which the provider cannot answer at all. The kernel
    converts it to DENY + FAIL_CLOSED / AUTHORITY_CONFIGURATION_UNAVAILABLE.

    It is NEVER degraded to "no candidates found" and NEVER degraded to
    DENY + RESOLVED (9.3.3).
    """


@runtime_checkable
class AuthorityConfigurationPort(Protocol):
    """Raw candidate discovery plus complete per-object lineage material.

    DISCOVERY IS RAW AND IDENTITY-ONLY (9.3.1). It returns STABLE IDENTITIES,
    never a version, and it may narrow only by the structurally trustworthy
    storage keys named below: the object family, the stable identity columns,
    the `authority_code` column and the stable reference columns.

    Discovery MUST NOT exclude a candidate because a retraction assertion, a
    correction assertion, an `active_flag` value, a business-effective
    interval, an evaluator outcome, a scope value, a "latest version" notion,
    a provenance value or any other apparent semantic disqualification seems
    to rule it out. Every one of those is a semantic judgement reserved to the
    kernel, and every one of them can ITSELF be the defect the kernel is
    required to detect.

    Discovery is therefore deliberately a SUPERSET, and being a superset is a
    CORRECTNESS requirement rather than a performance concession.
    """

    def find_business_authority_ids_by_code(self, authority_code: str) -> Sequence[str]:
        """Stable ids of EVERY Business Authority any RAW published version/assertion
        of which carries this `authority_code` - INCLUDING one that is targeted by a
        retraction assertion, inactive, future-dated, superseded or otherwise
        apparently disqualified."""
        ...

    def find_rule_ids_for_authority(self, business_authority_id: str) -> Sequence[str]:
        """Stable ids of EVERY Rule any RAW published version/assertion of which
        carries this stable `business_authority_id` as its reference, under the same
        including-retracted rule."""
        ...

    def find_assignment_ids_for_role(self, business_authority_role_id: str) -> Sequence[str]:
        """Stable ids of EVERY Assignment any RAW published version/assertion of which
        carries this stable `business_authority_role_id` as its reference, under the
        same including-retracted rule."""
        ...

    def get_lineage(self, object_family: str, object_id: str) -> LineageMaterial:
        """COMPLETE lineage material for one stable object.

        The provider applies NO interpretation: it does not compute closure,
        does not decide which version is effective, does not exclude retracted
        or inactive versions, and does not rank them. A provider that cannot
        return the complete set MUST return `completeness = UNAVAILABLE`
        rather than a truncated list; a truncated list presented as complete
        is a blocking defect.
        """
        ...

    def get_published_version(
        self, object_family: str, object_id: str, object_version: str
    ) -> PublishedObjectVersion:
        """The immutable content of exactly that version, FOREVER, regardless of
        retraction or correction. Dereference is ALWAYS available; retraction affects
        RESOLUTION only (9.3.2, 16.5 durability)."""
        ...
