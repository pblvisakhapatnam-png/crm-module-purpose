"""The PostgreSQL implementation of the E2-A authority configuration port.

PF-1A-E2-B section 5.2.

This class is a TRANSLATOR, not a decision-maker. It turns stored rows into
the provider-neutral DTOs of E2-A section 9.3.2 and hands them to the
UNCHANGED kernel. It contains no second implementation of effectiveness,
closure, activity, gap-versus-contradiction, correction precedence, scope
composition, aggregation or "latest version", and adding one would be a
blocking defect even if its answers agreed (E2-A 5.1, E2-B 5.2).

THE ONE SENTENCE TO REMEMBER: LOCATING a fact is permitted; JUDGING a fact is
not.

WHAT THE TRANSLATION DELIBERATELY DOES NOT DO

    It does not normalise. A stored `declared_effective_to` LATER than the
    successor's `effective_from` is returned exactly as published; it is never
    truncated to the successor's start, a NULL end is never rewritten into a
    concrete one, versions are never coalesced, merged, split, reordered or
    renumbered, and a retracted row is never hidden (5.6, attack surface 12a).

    It does not filter. Retracted, inactive, future-dated, superseded and
    corrected versions all appear in lineage material, and every retraction
    assertion is returned as a FACT for the kernel to validate rather than
    applied as a filter.

    It does not treat recorded time as a clock. `published_at` and
    `retracted_at` are returned as immutable provenance evidence and kernel
    validation input. They are never a filter, never a business-effective
    bound, and no operation here exposes a recorded-time cutoff or
    "known as at" parameter (E2-A 11.8).

    It does not degrade a failure into an absence. A read error, a timeout or
    a truncated read surfaces as a raised `AuthorityConfigurationPortError`,
    which the kernel maps to AUTHORITY_CONFIGURATION_UNAVAILABLE - never an
    empty candidate set and never DENY + RESOLVED.

READ-ONLY. There is no create, update, deactivate, publish, retract or delete
operation on this class or on the repository beneath it.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.modules.authorization.business_authority import repository
from app.modules.authorization.business_authority.contract import (
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
    COMPLETENESS_COMPLETE,
)
from app.modules.authorization.business_authority.domain import (
    BusinessAuthorityAssignmentPayload,
    BusinessAuthorityPayload,
    BusinessAuthorityRolePayload,
    BusinessAuthorityRulePayload,
    LineageMaterial,
    PublishedObjectVersion,
    RetractionAssertion,
)
from app.modules.authorization.business_authority.ports import (
    AuthorityConfigurationPortError,
)


def _authority_payload(row: dict[str, Any]) -> BusinessAuthorityPayload:
    return BusinessAuthorityPayload(
        authority_code=row["authority_code"],
        authority_name=row["authority_name"],
        description=row["description"],
        is_protected_meta_authority=row["is_protected_meta_authority"],
    )


def _role_payload(row: dict[str, Any]) -> BusinessAuthorityRolePayload:
    return BusinessAuthorityRolePayload(
        role_code=row["role_code"],
        role_name=row["role_name"],
        description=row["description"],
    )


def _rule_payload(row: dict[str, Any]) -> BusinessAuthorityRulePayload:
    return BusinessAuthorityRulePayload(
        business_authority_role_id=row["business_authority_role_object_id"],
        business_authority_id=row["business_authority_object_id"],
        scope_type=row["scope_type"],
        scope_id=row["scope_id"],
        parameter_evaluator_type=row["parameter_evaluator_type"],
        parameter_payload=row["parameter_payload"],
    )


def _assignment_payload(row: dict[str, Any]) -> BusinessAuthorityAssignmentPayload:
    return BusinessAuthorityAssignmentPayload(
        business_authority_role_id=row["business_authority_role_object_id"],
        person_id=row["person_id"],
        position_id=row["position_id"],
        scope_type=row["scope_type"],
        scope_id=row["scope_id"],
    )


_PAYLOAD_BUILDERS = {
    BUSINESS_AUTHORITY: _authority_payload,
    BUSINESS_AUTHORITY_ROLE: _role_payload,
    BUSINESS_AUTHORITY_RULE: _rule_payload,
    BUSINESS_AUTHORITY_ASSIGNMENT: _assignment_payload,
}


def _version(object_family: str, row: dict[str, Any]) -> PublishedObjectVersion:
    """One stored row, as the immutable published version it records.

    Every field is carried through unchanged. Nothing is defaulted, coerced,
    recomputed or repaired, and no derived value is attached.
    """

    return PublishedObjectVersion(
        object_version=row["object_version"],
        effective_from=row["effective_from"],
        active_flag=row["active_flag"],
        payload=_PAYLOAD_BUILDERS[object_family](row),
        declared_effective_to=row["declared_effective_to"],
        corrects_object_version=row["corrects_object_version"],
        publication_reference_type=row["publication_reference_type"],
        publication_reference_id=row["publication_reference_id"],
        published_at=row["published_at"],
    )


def _retraction(row: dict[str, Any]) -> RetractionAssertion:
    return RetractionAssertion(
        retraction_id=row["retraction_id"],
        object_version=row["object_version"],
        retracted_at=row["retracted_at"],
        publication_reference_type=row["publication_reference_type"],
        publication_reference_id=row["publication_reference_id"],
    )


class PostgresAuthorityConfigurationProvider:
    """Reads published authority configuration from PostgreSQL, and only reads it.

    It satisfies `AuthorityConfigurationPort` structurally; the protocol is
    runtime-checkable, and a test asserts the conformance rather than assuming
    it.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # -- RAW, identity-only discovery ---------------------------------------

    def find_business_authority_ids_by_code(self, authority_code: str) -> Sequence[str]:
        return repository.find_business_authority_ids_by_code(self._db, authority_code)

    def find_rule_ids_for_authority(self, business_authority_id: str) -> Sequence[str]:
        return repository.find_rule_ids_for_authority(self._db, business_authority_id)

    def find_assignment_ids_for_role(self, business_authority_role_id: str) -> Sequence[str]:
        return repository.find_assignment_ids_for_role(self._db, business_authority_role_id)

    # -- COMPLETE lineage material -------------------------------------------

    def get_lineage(self, object_family: str, object_id: str) -> LineageMaterial:
        """Every stored version and every stored retraction assertion.

        Both collections are read by ONE statement, so they observe ONE
        committed PostgreSQL snapshot and can never be a hybrid of a
        pre-commit and a post-commit state.

        An identity this store holds nothing for returns COMPLETE material
        with an EMPTY `versions` and an EMPTY `retraction_assertions`. That is
        a TRUTHFUL answer the kernel classifies (as AUTHORITY_REFERENCE_DANGLING
        where it is referenced), never an error and never a "no such object"
        signal - which is precisely why the store's own missing-parent foreign
        keys are a persistence-only invariant (class B2) rather than a
        semantic one (9.3.2).
        """

        version_rows, retraction_rows = repository.load_lineage(
            self._db, object_family, object_id
        )

        return LineageMaterial(
            object_family=object_family,
            object_id=object_id,
            versions=tuple(_version(object_family, row) for row in version_rows),
            retraction_assertions=tuple(_retraction(row) for row in retraction_rows),
            # COMPLETE is asserted only because the repository refuses to
            # under-report AND refuses to under-cohere: a short read raises
            # rather than returning here, and both collections come from ONE
            # PostgreSQL statement, so they are read as at ONE committed
            # snapshot. Two separate reads could otherwise straddle a
            # concurrent publication and present a combination of versions and
            # retractions that never existed together as COMPLETE
            # (independent review finding F1; see `repository.load_lineage`).
            completeness=COMPLETENESS_COMPLETE,
        )

    # -- immutable dereference ------------------------------------------------

    def get_published_version(
        self, object_family: str, object_id: str, object_version: str
    ) -> PublishedObjectVersion:
        """The exact immutable content of that version, forever.

        Retraction, correction, supersession, deactivation and expiry affect
        RESOLUTION only. None of them removes a version from dereference, and
        no other version is ever substituted.
        """

        row = repository.load_version(self._db, object_family, object_id, object_version)
        if row is None:
            raise KeyError((object_family, object_id, object_version))
        return _version(object_family, row)


__all__ = [
    "AuthorityConfigurationPortError",
    "PostgresAuthorityConfigurationProvider",
]
