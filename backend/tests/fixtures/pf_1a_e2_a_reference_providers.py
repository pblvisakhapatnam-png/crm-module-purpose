"""PF-1A-E2-A reference/synthetic providers and scenario builders. TEST-ONLY.

PF-1A-E2-A section 9.6.

    These are test/reference artefacts ONLY. They exist to make the kernel's
    semantics deterministically provable without a database, a real HR system
    or a real identity link.

They live under `backend/tests/` deliberately, never under a production
package path, so section 9.6's unreachability property is STRUCTURAL rather
than merely asserted: no production module can import what is not on the
production import path. No production composition binds them, and the ONE
production composition seam,
`business_authority.production_composition.build_production_business_authority_resolver`,
refuses to compose at all rather than substituting one. (It was
`business_authority.resolver.build_production_resolver` until PF-1A-E2-B
correction C2 withdrew that duplicate seam under independent review finding
F4; the refusal behaviour this paragraph describes is unchanged.)

CRITICAL PROPERTY - THESE PROVIDERS MUST NOT VALIDATE (9.3.4, 18, 22.17b).
Neither the provider below nor the builders impose any identity-uniqueness,
person/position XOR, interval-sanity, provenance-presence, closed-enum or
referential restriction over the DTO-OPTIONAL fields. A "convenience
validator" here would silently destroy the very class B1 coverage the
verification contract depends on, and is a blocking defect. Every malformed
shape the manifest names must be constructible with these builders.

CRITICAL PROPERTY - DISCOVERY IS RAW (9.3.1). Discovery scans EVERY raw
published version, INCLUDING versions that are retracted, inactive,
future-dated, superseded or otherwise apparently disqualified. It applies no
active_flag, effective-interval, scope, parameter, evaluator-outcome,
provenance or "latest version" predicate. Being a superset is a CORRECTNESS
requirement, not a performance concession.

SYNTHETIC BOOTSTRAP PROVENANCE IS NOT A PRODUCTION BOOTSTRAP. Every fixture
below uses `BOOTSTRAP_PROVENANCE` with an explicitly synthetic reference id,
and that is not a resolution of Q-10, not a production bootstrap, and not a
choice of any real authority holder (11.7, section 23).
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from app.modules.authorization.business_authority.contract import (
    BOOTSTRAP_PROVENANCE,
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_RULE,
    COMPLETENESS_COMPLETE,
    COMPLETENESS_UNAVAILABLE,
    EVALUATOR_NONE,
    SCOPE_GLOBAL,
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
from app.modules.authorization.business_authority.ports import AuthorityConfigurationPortError
from app.modules.hr_reference.contract import (
    EMPLOYMENT_ACTIVE,
    ActorPersonReference,
    EmploymentStateReference,
    HrLookup,
    IncumbencyReference,
    OrgUnitVersionReference,
    PositionVersionReference,
    ambiguous,
    missing,
    ok,
    stale,
    unavailable,
)

# ---------------------------------------------------------------------------
# A fixed synthetic timeline. Every instant below is timezone-aware UTC.
# ---------------------------------------------------------------------------

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T1 = datetime(2026, 3, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 6, 1, tzinfo=timezone.utc)
T3 = datetime(2026, 9, 1, tzinfo=timezone.utc)
TICK = timedelta(microseconds=1)

RECORDED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

# Explicitly SYNTHETIC provenance. Labelled as such in the value itself so a
# reader of any fixture, evidence dump or failure message can see immediately
# that it is not production bootstrap provenance.
SYNTHETIC_PROVENANCE_ID = "SYNTHETIC-E2A-TEST-FIXTURE-NOT-A-PRODUCTION-BOOTSTRAP"

ACTOR_ID = "actor-0001"
PERSON_ID = "person-0001"
OTHER_PERSON_ID = "person-0002"
POSITION_ID = "position-0001"
ORG_ROOT = "org-root"
ORG_DIVISION = "org-division"
ORG_BRANCH = "org-branch"

AUTHORITY_CODE = "CREDIT_ASSESSOR"

# Sentinel meaning "leave this field ABSENT". Needed because `None` is itself a
# legitimate value for `declared_effective_to` ("no known end"), so a builder
# default of `None` could not distinguish the two.
_UNSET = object()


def version(
    object_version: str,
    effective_from: datetime | None = T0,
    *,
    payload: object = None,
    active_flag: bool | None = True,
    declared_effective_to: datetime | None = None,
    corrects_object_version: str | None = None,
    publication_reference_type: object = _UNSET,
    publication_reference_id: object = _UNSET,
    published_at: object = _UNSET,
) -> PublishedObjectVersion:
    """Build one published version.

    Every DTO-OPTIONAL field can be made ABSENT by passing `None` explicitly,
    which is exactly what the class B1 provenance fixtures need. The `_UNSET`
    default is what distinguishes "the caller said nothing, use a valid
    default" from "the caller explicitly wants this field absent".
    """

    return PublishedObjectVersion(
        object_version=object_version,
        effective_from=effective_from,
        active_flag=active_flag,
        payload=payload,
        declared_effective_to=declared_effective_to,
        corrects_object_version=corrects_object_version,
        publication_reference_type=(
            BOOTSTRAP_PROVENANCE
            if publication_reference_type is _UNSET
            else publication_reference_type
        ),
        publication_reference_id=(
            SYNTHETIC_PROVENANCE_ID
            if publication_reference_id is _UNSET
            else publication_reference_id
        ),
        published_at=RECORDED_AT if published_at is _UNSET else published_at,
    )


def retraction(
    retraction_id: str,
    object_version: str | None,
    *,
    retracted_at: object = _UNSET,
    publication_reference_type: object = _UNSET,
    publication_reference_id: object = _UNSET,
) -> RetractionAssertion:
    """Build one append-only retraction assertion."""

    return RetractionAssertion(
        retraction_id=retraction_id,
        object_version=object_version,
        retracted_at=RECORDED_AT if retracted_at is _UNSET else retracted_at,
        publication_reference_type=(
            BOOTSTRAP_PROVENANCE
            if publication_reference_type is _UNSET
            else publication_reference_type
        ),
        publication_reference_id=(
            SYNTHETIC_PROVENANCE_ID
            if publication_reference_id is _UNSET
            else publication_reference_id
        ),
    )


def material(
    object_family: str,
    object_id: str,
    versions: Sequence[PublishedObjectVersion] = (),
    retraction_assertions: Sequence[RetractionAssertion] = (),
    completeness: str = COMPLETENESS_COMPLETE,
) -> LineageMaterial:
    return LineageMaterial(
        object_family=object_family,
        object_id=object_id,
        versions=tuple(versions),
        retraction_assertions=tuple(retraction_assertions),
        completeness=completeness,
    )


def authority_payload(
    code: str = AUTHORITY_CODE, *, is_protected_meta_authority: bool = False
) -> BusinessAuthorityPayload:
    return BusinessAuthorityPayload(
        authority_code=code,
        authority_name=code.replace("_", " ").title(),
        is_protected_meta_authority=is_protected_meta_authority,
    )


def role_payload(code: str = "CREDIT_ASSESSMENT_ROLE") -> BusinessAuthorityRolePayload:
    return BusinessAuthorityRolePayload(role_code=code, role_name=code.replace("_", " ").title())


def rule_payload(
    *,
    role_id: str | None = "role-1",
    authority_id: str | None = "authority-1",
    scope_type: str | None = SCOPE_GLOBAL,
    scope_id: str | None = None,
    evaluator_type: str | None = EVALUATOR_NONE,
    parameter_payload: object = None,
) -> BusinessAuthorityRulePayload:
    return BusinessAuthorityRulePayload(
        business_authority_role_id=role_id,
        business_authority_id=authority_id,
        scope_type=scope_type,
        scope_id=scope_id,
        parameter_evaluator_type=evaluator_type,
        parameter_payload=parameter_payload,
    )


def assignment_payload(
    *,
    role_id: str | None = "role-1",
    person_id: str | None = PERSON_ID,
    position_id: str | None = None,
    scope_type: str | None = SCOPE_GLOBAL,
    scope_id: str | None = None,
) -> BusinessAuthorityAssignmentPayload:
    return BusinessAuthorityAssignmentPayload(
        business_authority_role_id=role_id,
        person_id=person_id,
        position_id=position_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )


# ---------------------------------------------------------------------------
# The reference authority configuration provider
# ---------------------------------------------------------------------------

ORDER_CONTRACT = "contract"
ORDER_REVERSED = "reversed"
ORDER_SHUFFLED = "shuffled"


@dataclass
class _Failure:
    """Injected PORT-level failure behaviour (never a data defect)."""

    raise_on_discovery: bool = False
    raise_on: frozenset[tuple[str, str]] = frozenset()
    unavailable_on: frozenset[tuple[str, str]] = frozenset()
    truncate_on: frozenset[tuple[str, str]] = frozenset()
    # The exception MESSAGE a raising provider uses. Two providers failing the
    # same way with different messages must produce byte-identical canonical
    # evidence (correction FU-4), so the message is injectable purely to prove
    # it never reaches the result.
    raise_message: str = "injected read failure"
    # Return material whose own canonical identity differs from the one that
    # was requested (correction FU-1, case F).
    return_family_of: str | None = None
    return_object_id_of: str | None = None


class ReferenceAuthorityConfigurationProvider:
    """An in-memory provider that supplies FACTS ONLY.

    It stores lineage material exactly as published and returns it. It does
    NOT filter to "the effective row", does NOT exclude retracted, inactive,
    superseded or future versions from discovery or from lineage, does NOT
    compute or store a derived asserted end, does NOT deduplicate, does NOT
    tie-break, does NOT select a "latest", and does NOT use published_at or
    retracted_at as a filter.
    """

    def __init__(
        self,
        materials: Sequence[LineageMaterial] = (),
        *,
        order: str = ORDER_CONTRACT,
        seed: int = 0,
        failure: _Failure | None = None,
    ) -> None:
        self._materials: dict[tuple[str, str], LineageMaterial] = {
            (item.object_family, item.object_id): item for item in materials
        }
        self._order = order
        self._random = random.Random(seed)
        self._failure = failure or _Failure()
        # Every `as_of` this provider was asked about, so a test can prove ONE
        # instant governed the whole resolution (NS-RS-02).
        self.observed_lineage_calls: list[tuple[str, str]] = []

    # -- construction helpers ------------------------------------------------

    def with_order(self, order: str, *, seed: int = 0) -> ReferenceAuthorityConfigurationProvider:
        return ReferenceAuthorityConfigurationProvider(
            tuple(self._materials.values()), order=order, seed=seed, failure=self._failure
        )

    def with_failure(self, **kwargs: object) -> ReferenceAuthorityConfigurationProvider:
        return ReferenceAuthorityConfigurationProvider(
            tuple(self._materials.values()),
            order=self._order,
            failure=_Failure(**kwargs),  # type: ignore[arg-type]
        )

    def add(self, item: LineageMaterial) -> None:
        self._materials[(item.object_family, item.object_id)] = item

    # -- RAW, identity-only discovery ---------------------------------------

    def _raw_versions(self, family: str) -> list[tuple[str, PublishedObjectVersion]]:
        found: list[tuple[str, PublishedObjectVersion]] = []
        for (item_family, object_id), item in self._materials.items():
            if item_family != family:
                continue
            for published in item.versions:
                found.append((object_id, published))
        return found

    def find_business_authority_ids_by_code(self, authority_code: str) -> Sequence[str]:
        if self._failure.raise_on_discovery:
            raise AuthorityConfigurationPortError(self._failure.raise_message)
        ids = [
            object_id
            for object_id, published in self._raw_versions(BUSINESS_AUTHORITY)
            if getattr(published.payload, "authority_code", None) == authority_code
        ]
        return self._order_ids(ids)

    def find_rule_ids_for_authority(self, business_authority_id: str) -> Sequence[str]:
        if self._failure.raise_on_discovery:
            raise AuthorityConfigurationPortError(self._failure.raise_message)
        ids = [
            object_id
            for object_id, published in self._raw_versions(BUSINESS_AUTHORITY_RULE)
            if getattr(published.payload, "business_authority_id", None) == business_authority_id
        ]
        return self._order_ids(ids)

    def find_assignment_ids_for_role(self, business_authority_role_id: str) -> Sequence[str]:
        if self._failure.raise_on_discovery:
            raise AuthorityConfigurationPortError(self._failure.raise_message)
        ids = [
            object_id
            for object_id, published in self._raw_versions(BUSINESS_AUTHORITY_ASSIGNMENT)
            if getattr(published.payload, "business_authority_role_id", None)
            == business_authority_role_id
        ]
        return self._order_ids(ids)

    def _order_ids(self, ids: list[str]) -> list[str]:
        unique = list(dict.fromkeys(ids))
        if self._order == ORDER_REVERSED:
            return list(reversed(unique))
        if self._order == ORDER_SHUFFLED:
            shuffled = list(unique)
            self._random.shuffle(shuffled)
            return shuffled
        return unique

    # -- complete lineage material -------------------------------------------

    def get_lineage(self, object_family: str, object_id: str) -> LineageMaterial:
        key = (object_family, object_id)
        self.observed_lineage_calls.append(key)

        if key in self._failure.raise_on:
            raise AuthorityConfigurationPortError(self._failure.raise_message)

        item = self._materials.get(key)
        if item is None:
            # An identity the provider holds nothing for returns COMPLETE
            # material with an EMPTY versions[] (9.3.2). It does NOT raise, does
            # NOT return UNAVAILABLE and does NOT invent a "no such object"
            # signal.
            return material(object_family, object_id)

        if key in self._failure.unavailable_on:
            return replace(item, completeness=COMPLETENESS_UNAVAILABLE)

        versions = list(item.versions)
        if key in self._failure.truncate_on and versions:
            # A TRUNCATED read presented as COMPLETE. This is the blocking
            # defect 9.3.2 names, reproduced deliberately so the kernel can be
            # shown to fail closed rather than silently resolve a short list.
            versions = versions[:-1]

        assertions = list(item.retraction_assertions)

        if self._order == ORDER_REVERSED:
            versions.reverse()
            assertions.reverse()
        elif self._order == ORDER_SHUFFLED:
            self._random.shuffle(versions)
            self._random.shuffle(assertions)
        else:
            versions.sort(key=lambda v: ((v.effective_from or T0), v.object_version or ""))
            assertions.sort(key=lambda a: (a.object_version or "", a.retraction_id or ""))

        returned = replace(item, versions=tuple(versions), retraction_assertions=tuple(assertions))

        # A NON-CONFORMING provider claiming to answer about a different
        # canonical object than the one requested.
        if self._failure.return_family_of is not None:
            returned = replace(returned, object_family=self._failure.return_family_of)
        if self._failure.return_object_id_of is not None:
            returned = replace(returned, object_id=self._failure.return_object_id_of)
        return returned

    def get_published_version(
        self, object_family: str, object_id: str, object_version: str
    ) -> PublishedObjectVersion:
        """Dereference is ALWAYS available, forever, regardless of retraction or
        correction. Retraction affects RESOLUTION only (9.3.2)."""

        item = self._materials.get((object_family, object_id))
        if item is None:
            raise KeyError((object_family, object_id))
        for published in item.versions:
            if published.object_version == object_version:
                return published
        raise KeyError((object_family, object_id, object_version))


class JudgingAuthorityConfigurationProvider(ReferenceAuthorityConfigurationProvider):
    """A NON-CONFORMING provider that supplies JUDGEMENTS instead of FACTS.

    It exists solely so a conformance test has something that must be
    REJECTED (NS-PR-03). It prefilters to what it believes is "the effective
    row", drops retracted and inactive versions from discovery and from
    lineage, and therefore hides exactly the defects the kernel is required to
    detect. Nothing in the production package may ever behave like this.
    """

    def get_lineage(self, object_family: str, object_id: str) -> LineageMaterial:
        item = super().get_lineage(object_family, object_id)
        retracted = {a.object_version for a in item.retraction_assertions}
        judged = [
            published
            for published in item.versions
            if published.object_version not in retracted and published.active_flag
        ]
        # It also drops the retraction assertions themselves, so the kernel
        # could never tell a correct retraction from a malformed one.
        return replace(item, versions=tuple(judged[-1:]), retraction_assertions=())

    def find_business_authority_ids_by_code(self, authority_code: str) -> Sequence[str]:
        found = super().find_business_authority_ids_by_code(authority_code)
        return [
            object_id
            for object_id in found
            if any(
                published.active_flag
                for published in self._materials[(BUSINESS_AUTHORITY, object_id)].versions
            )
        ]


# ---------------------------------------------------------------------------
# The reference actor-person and HR providers
# ---------------------------------------------------------------------------


class ReferenceActorPersonProvider:
    """Resolves the AUTHENTICATED actor to a canonical person. TEST-ONLY.

    The input is only ever the authenticated actor's application-user public
    identifier. There is deliberately no parameter through which a caller
    could supply a person identity.
    """

    def __init__(
        self,
        mapping: dict[str, str] | None = None,
        *,
        status: str | None = None,
        status_override: str | None = None,
        returned_actor_id: str | None = None,
        snapshot_at: datetime = RECORDED_AT,
    ) -> None:
        self._mapping = mapping if mapping is not None else {ACTOR_ID: PERSON_ID}
        self._status = status
        # A status OUTSIDE the closed lookup vocabulary, returned together with
        # an entirely plausible value. A conforming kernel must never trust the
        # value merely because it is present.
        self._status_override = status_override
        # The actor identity the RESPONSE claims to be about, when that is
        # deliberately not the actor that was requested (correction FU-1).
        self._returned_actor_id = returned_actor_id
        self._snapshot_at = snapshot_at
        self.observed_as_of: list[datetime] = []

    def resolve_actor_person(self, actor_user_public_id: str, as_of: datetime) -> HrLookup:
        self.observed_as_of.append(as_of)

        if self._status == "MISSING":
            return missing()
        if self._status == "AMBIGUOUS":
            return ambiguous()
        if self._status == "UNAVAILABLE":
            return unavailable()
        if self._status == "STALE":
            return stale()

        person_id = self._mapping.get(actor_user_public_id)
        if person_id is None:
            return missing()

        reference = ActorPersonReference(
            actor_user_public_id=self._returned_actor_id or actor_user_public_id,
            person_id=person_id,
            canonical_snapshot_at=self._snapshot_at,
            reference_evidence=f"synthetic-actor-person-link:{actor_user_public_id}",
        )
        if self._status_override is not None:
            return HrLookup(status=self._status_override, value=reference)
        return ok(reference)


class ReferenceHrProvider:
    """Canonical HR/organisation answers for deterministic tests. TEST-ONLY.

    Every response carries a canonical snapshot indicator and no provider
    identifier, no provider field name and no raw provider timestamp.
    """

    def __init__(
        self,
        *,
        employment_status: str = EMPLOYMENT_ACTIVE,
        employment_result: str | None = None,
        position_result: str | None = None,
        incumbency_result: str | None = None,
        org_unit_result: str | None = None,
        incumbent_person_id: str = PERSON_ID,
        org_parents: dict[str, str | None] | None = None,
        snapshot_at: datetime = RECORDED_AT,
        position_snapshot_at: datetime | None = None,
        incumbency_snapshot_at: datetime | None = None,
        org_unit_snapshots: dict[str, datetime] | None = None,
        employment_status_override: str | None = None,
        position_status_override: str | None = None,
        incumbency_status_override: str | None = None,
        org_unit_status_override: str | None = None,
        org_unit_results: dict[str, str] | None = None,
        returned_org_unit_ids: dict[str, str] | None = None,
        returned_person_id: str | None = None,
        returned_position_id: str | None = None,
        returned_incumbency_position_id: str | None = None,
        returned_org_unit_id: str | None = None,
    ) -> None:
        self._employment_status = employment_status
        self._employment_result = employment_result
        self._position_result = position_result
        self._incumbency_result = incumbency_result
        self._org_unit_result = org_unit_result
        self._incumbent_person_id = incumbent_person_id
        self._org_parents = (
            org_parents
            if org_parents is not None
            else {ORG_BRANCH: ORG_DIVISION, ORG_DIVISION: ORG_ROOT, ORG_ROOT: None}
        )
        self._snapshot_at = snapshot_at
        # PER-OPERATION canonical snapshots, so a fixture can make exactly ONE
        # HR state stale while every other state stays fresh. That is what
        # exposes a staleness check applied at some seams but not at all of them.
        self._position_snapshot_at = position_snapshot_at or snapshot_at
        self._incumbency_snapshot_at = incumbency_snapshot_at or snapshot_at
        self._org_unit_snapshots = org_unit_snapshots or {}
        # PER-OPERATION non-contract statuses, each returned with a plausible
        # value attached.
        self._employment_status_override = employment_status_override
        self._position_status_override = position_status_override
        self._incumbency_status_override = incumbency_status_override
        self._org_unit_status_override = org_unit_status_override
        # PER-UNIT failure and identity knobs (correction C2-1). The existing
        # `org_unit_result` / `returned_org_unit_id` knobs apply to EVERY unit
        # at once, which cannot express the shape this correction is about: a
        # subordinate unit that resolves perfectly and DECLARES an ancestor,
        # while that ANCESTOR is the one the canonical reference cannot supply.
        self._org_unit_results = org_unit_results or {}
        self._returned_org_unit_ids = returned_org_unit_ids or {}
        # The canonical identity each RESPONSE claims to be about, when that is
        # deliberately not the identity that was requested (correction FU-1).
        self._returned_person_id = returned_person_id
        self._returned_position_id = returned_position_id
        self._returned_incumbency_position_id = returned_incumbency_position_id
        self._returned_org_unit_id = returned_org_unit_id
        self.observed_as_of: list[datetime] = []

    @staticmethod
    def _explicit(result: str | None) -> HrLookup | None:
        return {
            "MISSING": missing(),
            "AMBIGUOUS": ambiguous(),
            "UNAVAILABLE": unavailable(),
            "STALE": stale(),
        }.get(result or "")

    def get_employment_state(self, person_id: str, as_of: datetime) -> HrLookup:
        self.observed_as_of.append(as_of)
        explicit = self._explicit(self._employment_result)
        if explicit is not None:
            return explicit
        value = EmploymentStateReference(
            person_id=self._returned_person_id or person_id,
            employment_state_version_id=f"employment-version-{person_id}",
            employment_status=self._employment_status,
            canonical_snapshot_at=self._snapshot_at,
        )
        if self._employment_status_override is not None:
            return HrLookup(status=self._employment_status_override, value=value)
        return ok(value)

    def get_position(self, position_id: str, as_of: datetime) -> HrLookup:
        self.observed_as_of.append(as_of)
        explicit = self._explicit(self._position_result)
        if explicit is not None:
            return explicit
        value = PositionVersionReference(
            position_id=self._returned_position_id or position_id,
            position_version_id=f"position-version-{position_id}",
            org_unit_id=ORG_BRANCH,
            canonical_snapshot_at=self._position_snapshot_at,
        )
        if self._position_status_override is not None:
            return HrLookup(status=self._position_status_override, value=value)
        return ok(value)

    def get_incumbency(self, position_id: str, as_of: datetime) -> HrLookup:
        self.observed_as_of.append(as_of)
        explicit = self._explicit(self._incumbency_result)
        if explicit is not None:
            return explicit
        value = IncumbencyReference(
            position_id=self._returned_incumbency_position_id or position_id,
            incumbency_id=f"incumbency-{position_id}",
            person_id=self._incumbent_person_id,
            canonical_snapshot_at=self._incumbency_snapshot_at,
        )
        if self._incumbency_status_override is not None:
            return HrLookup(status=self._incumbency_status_override, value=value)
        return ok(value)

    def get_org_unit(self, org_unit_id: str, as_of: datetime) -> HrLookup:
        self.observed_as_of.append(as_of)
        explicit = self._explicit(self._org_unit_results.get(org_unit_id))
        if explicit is None:
            explicit = self._explicit(self._org_unit_result)
        if explicit is not None:
            return explicit
        if org_unit_id not in self._org_parents:
            return missing()
        value = OrgUnitVersionReference(
            org_unit_id=(
                self._returned_org_unit_ids.get(org_unit_id)
                or self._returned_org_unit_id
                or org_unit_id
            ),
            org_unit_version_id=f"org-version-{org_unit_id}",
            parent_org_unit_id=self._org_parents[org_unit_id],
            canonical_snapshot_at=self._org_unit_snapshots.get(org_unit_id, self._snapshot_at),
        )
        if self._org_unit_status_override is not None:
            return HrLookup(status=self._org_unit_status_override, value=value)
        return ok(value)
