"""PF-1A-E2-B store seeding, the PostgreSQL-backed composition, and parity. TEST-ONLY.

PF-1A-E2-B sections 5.3 and 9.

THE CENTRAL IDEA OF THIS MODULE, and of the whole E2-B verification: ONE
declarative scenario - a list of `LineageMaterial` objects plus the request
inputs - is driven through TWO compositions and the two results are compared
field for field and order for order.

    reference composition   kernel + E2-A in-memory reference provider
                            + the synthetic actor/HR providers
    postgres composition    kernel + E2-B PostgreSQL provider
                            + THE SAME synthetic actor/HR providers

Because the scenario is the same object in both cases, a parity failure can
only come from the store or the provider, which is exactly what E2-B is
verifying.

THIS IS A TEST HARNESS, NOT A PRODUCT. It lives under `backend/tests/`
deliberately, so that section 5.3's unreachability property is STRUCTURAL: no
production module can import what is not on the production import path, and
the production composition seam refuses to compose rather than substituting
any of these synthetic providers.

WHY THE SEEDING HELPER MATERIALISES A REFERENCED-BUT-UNPUBLISHED IDENTITY.
`seed_materials` creates a bare stable-identity row for any role/authority a
seeded rule or assignment references but for which the scenario supplies no
material. That is NOT a repair and NOT a widening of what the store accepts:
E2-A 9.3.2 says an identity a provider holds nothing for returns COMPLETE
material with an EMPTY `versions[]`, so the reference provider and this store
must present the SAME state for such a reference - the class A
dangling-reference state of fixture A-11. The physical foreign key that would
otherwise reject the row protects this store's own parent/child
representation and is a persistence-only invariant (class B2, fixture B2-03),
proved separately by a direct INSERT in the structural-rejection tests, which
deliberately do not go through this helper.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.core.database import SessionLocal

from app.modules.authorization.business_authority.contract import (
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
)
from app.modules.authorization.business_authority.domain import (
    AuthenticatedActor,
    AuthorityResolutionRequest,
    BusinessContext,
    LineageMaterial,
)
from app.modules.authorization.business_authority.evidence import (
    AuthorityResolutionResult,
    serialize_result,
)
from app.modules.authorization.business_authority.kernel import resolve
from app.modules.authorization.business_authority.postgres_provider import (
    PostgresAuthorityConfigurationProvider,
)
from app.modules.authorization.business_authority.store_contract import (
    FAMILY_TABLES,
    STORE_TABLES_CHILD_FIRST,
)
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    ACTOR_ID,
    AUTHORITY_CODE,
    T2,
    ReferenceActorPersonProvider,
    ReferenceAuthorityConfigurationProvider,
    ReferenceHrProvider,
)

# Mirrors the `_DEFAULT` sentinel of the E2-A scenario helper, so "the caller
# said nothing" and "the caller explicitly wants this port UNBOUND" stay
# distinguishable - which is what NS-AP-03 and NS-HR-01 need.
_DEFAULT = object()

# payload attribute -> physical column, per family. Written out rather than
# derived, so a renamed DTO field fails loudly here instead of silently
# seeding a NULL.
_PAYLOAD_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    BUSINESS_AUTHORITY: (
        ("authority_code", "authority_code"),
        ("authority_name", "authority_name"),
        ("description", "description"),
        ("is_protected_meta_authority", "is_protected_meta_authority"),
    ),
    BUSINESS_AUTHORITY_ROLE: (
        ("role_code", "role_code"),
        ("role_name", "role_name"),
        ("description", "description"),
    ),
    BUSINESS_AUTHORITY_RULE: (
        ("business_authority_role_id", "business_authority_role_object_id"),
        ("business_authority_id", "business_authority_object_id"),
        ("scope_type", "scope_type"),
        ("scope_id", "scope_id"),
        ("parameter_evaluator_type", "parameter_evaluator_type"),
        ("parameter_payload", "parameter_payload"),
    ),
    BUSINESS_AUTHORITY_ASSIGNMENT: (
        ("business_authority_role_id", "business_authority_role_object_id"),
        ("person_id", "person_id"),
        ("position_id", "position_id"),
        ("scope_type", "scope_type"),
        ("scope_id", "scope_id"),
    ),
}

# The stable references a seeded version carries, and the family each points
# at. Used only to materialise a referenced identity that the scenario itself
# did not publish - see the module docstring.
_STABLE_REFERENCES: dict[str, tuple[tuple[str, str], ...]] = {
    BUSINESS_AUTHORITY_RULE: (
        ("business_authority_role_id", BUSINESS_AUTHORITY_ROLE),
        ("business_authority_id", BUSINESS_AUTHORITY),
    ),
    BUSINESS_AUTHORITY_ASSIGNMENT: (
        ("business_authority_role_id", BUSINESS_AUTHORITY_ROLE),
    ),
}

_VERSION_COLUMNS = (
    "object_version",
    "effective_from",
    "declared_effective_to",
    "active_flag",
    "corrects_object_version",
    "publication_reference_type",
    "publication_reference_id",
    "published_at",
)


# ---------------------------------------------------------------------------
# The session fixture every E2-B test uses
# ---------------------------------------------------------------------------


@pytest.fixture
def store_db():
    """A session over the real dockerized PostgreSQL, with an EMPTY store.

    The store is cleared before AND after every test, so no test can see a
    neighbour's rows and none leaves residue behind (section 9, REGRESSION).
    Clearing before as well as after also means a run interrupted mid-test
    cannot poison the next one.
    """

    db = SessionLocal()
    try:
        clear_store(db)
        yield db
    finally:
        db.rollback()
        clear_store(db)
        db.close()


# ---------------------------------------------------------------------------
# Teardown
# ---------------------------------------------------------------------------


def clear_store(db: Session) -> None:
    """Remove every row from the twelve store tables, children before parents.

    These tables are exclusively PF-1A-E2-B's and the migration seeds nothing
    into them (acceptance criterion S), so emptying them cannot touch business
    data. This is FIXTURE teardown: the production package exposes no delete
    path at all (acceptance criterion R).
    """

    for table in STORE_TABLES_CHILD_FIRST:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


def count_store_rows(db: Session) -> dict[str, int]:
    return {
        table: db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        for table in STORE_TABLES_CHILD_FIRST
    }


# ---------------------------------------------------------------------------
# Low-level INSERT helpers, used directly by the structural-rejection tests
# ---------------------------------------------------------------------------


def insert_stable_identity(db: Session, family: str, object_id: str) -> None:
    db.execute(
        text(f"INSERT INTO {FAMILY_TABLES[family].stable} (object_id) VALUES (:object_id)"),
        {"object_id": object_id},
    )


def _insert(db: Session, table: str, values: dict[str, Any]) -> None:
    columns = ", ".join(values)
    binds = ", ".join(f":{name}" for name in values)
    statement = text(f"INSERT INTO {table} ({columns}) VALUES ({binds})")
    if "parameter_payload" in values:
        # A structured payload needs its type declared explicitly, because a
        # bare bind of a Python dict has no PostgreSQL type to adapt to. The
        # VALUE is still passed straight through: nothing is reshaped,
        # defaulted or validated on the way in.
        statement = statement.bindparams(bindparam("parameter_payload", type_=JSONB))
    db.execute(statement, values)


def insert_version_row(db: Session, family: str, values: dict[str, Any]) -> None:
    """INSERT one version row EXACTLY as given, against the shipped schema.

    Deliberately dumb: it applies no default, fills in no missing column and
    repairs nothing, so a structural-rejection test proves what the MIGRATED
    SCHEMA AS SHIPPED does rather than what this helper does.
    """

    _insert(db, FAMILY_TABLES[family].version, values)


def insert_retraction_row(db: Session, family: str, values: dict[str, Any]) -> None:
    _insert(db, FAMILY_TABLES[family].retraction, values)


# ---------------------------------------------------------------------------
# Seeding a declarative scenario
# ---------------------------------------------------------------------------


def _version_values(version: Any) -> dict[str, Any]:
    return {name: getattr(version, name) for name in _VERSION_COLUMNS}


def _referenced_identities(materials: Sequence[LineageMaterial]) -> set[tuple[str, str]]:
    referenced: set[tuple[str, str]] = set()
    for material in materials:
        for attribute, family in _STABLE_REFERENCES.get(material.object_family, ()):
            for version in material.versions:
                value = getattr(version.payload, attribute, None)
                if isinstance(value, str) and value:
                    referenced.add((family, value))
    return referenced


def seed_materials(
    db: Session,
    materials: Iterable[LineageMaterial],
    *,
    reverse_physical_order: bool = False,
) -> None:
    """Write a declarative scenario into PostgreSQL exactly as published.

    Nothing is normalised on the way in: an explicit `declared_effective_to`
    later than the successor's `effective_from` is written as given, a NULL
    declared end stays NULL, duplicate temporal starts are written as two
    rows, and a dangling or duplicated retraction is written as-is. The
    read-back tests assert byte-identity for exactly this reason.

    `reverse_physical_order` inserts the rows of each object in the opposite
    order, so a determinism test can prove the result does not depend on
    physical row order.
    """

    materials = list(materials)
    published = {(m.object_family, m.object_id) for m in materials}

    for family, object_id in sorted(published):
        insert_stable_identity(db, family, object_id)
    # A reference to an identity the scenario never published: the reference
    # provider answers COMPLETE-with-empty-versions for it, so this store must
    # be able to present the same state. See the module docstring.
    for family, object_id in sorted(_referenced_identities(materials) - published):
        insert_stable_identity(db, family, object_id)

    for material in materials:
        family = material.object_family
        versions = list(material.versions)
        assertions = list(material.retraction_assertions)
        if reverse_physical_order:
            versions.reverse()
            assertions.reverse()

        for version in versions:
            values = _version_values(version)
            values["object_id"] = material.object_id
            for attribute, column in _PAYLOAD_COLUMNS[family]:
                values[column] = getattr(version.payload, attribute, None)
            insert_version_row(db, family, values)

        for assertion in assertions:
            insert_retraction_row(
                db,
                family,
                {
                    "object_id": material.object_id,
                    "retraction_id": assertion.retraction_id,
                    "object_version": assertion.object_version,
                    "retracted_at": assertion.retracted_at,
                    "publication_reference_type": assertion.publication_reference_type,
                    "publication_reference_id": assertion.publication_reference_id,
                },
            )

    db.commit()


# ---------------------------------------------------------------------------
# The two compositions
# ---------------------------------------------------------------------------


def _request(
    authority_code: str,
    actor_id: str,
    business_context: BusinessContext | None,
    hr_staleness_threshold_seconds: int | None,
) -> AuthorityResolutionRequest:
    return AuthorityResolutionRequest(
        authenticated_actor=AuthenticatedActor(actor_user_public_id=actor_id),
        authority_code=authority_code,
        business_context=business_context or BusinessContext(),
        hr_staleness_threshold_seconds=hr_staleness_threshold_seconds,
    )


def run_through_postgres(
    db: Session,
    materials: Iterable[LineageMaterial] | None,
    *,
    as_of: datetime = T2,
    authority_code: str = AUTHORITY_CODE,
    actor_id: str = ACTOR_ID,
    business_context: BusinessContext | None = None,
    actor_person_port: Any = _DEFAULT,
    hr_reference_port: Any = _DEFAULT,
    authority_configuration_port: Any = _DEFAULT,
    hr_staleness_threshold_seconds: int | None = None,
    reverse_physical_order: bool = False,
    seed: bool = True,
) -> AuthorityResolutionResult:
    """Resolve against the UNCHANGED kernel, wired to the PostgreSQL provider.

    Tests drive the kernel at an explicit business-effective instant rather
    than through `resolve_current_authority`, exactly as the E2-A corpus does
    and for the same reason: a deterministic temporal corpus needs an explicit
    instant, and only the live entry point may read a clock (E2-A 10.3).
    """

    if materials is not None and seed:
        seed_materials(db, materials, reverse_physical_order=reverse_physical_order)

    port = authority_configuration_port
    if port is _DEFAULT:
        port = PostgresAuthorityConfigurationProvider(db)

    return resolve(
        request=_request(
            authority_code, actor_id, business_context, hr_staleness_threshold_seconds
        ),
        as_of=as_of,
        authority_configuration_port=port,
        actor_person_port=(
            ReferenceActorPersonProvider() if actor_person_port is _DEFAULT else actor_person_port
        ),
        hr_reference_port=(
            ReferenceHrProvider() if hr_reference_port is _DEFAULT else hr_reference_port
        ),
    )


def run_through_reference(
    materials: Iterable[LineageMaterial] | None,
    *,
    as_of: datetime = T2,
    authority_code: str = AUTHORITY_CODE,
    actor_id: str = ACTOR_ID,
    business_context: BusinessContext | None = None,
    actor_person_port: Any = _DEFAULT,
    hr_reference_port: Any = _DEFAULT,
    authority_configuration_port: Any = _DEFAULT,
    hr_staleness_threshold_seconds: int | None = None,
    order: str = "contract",
    seed_value: int = 0,
) -> AuthorityResolutionResult:
    """The same scenario through the E2-A in-memory reference provider."""

    port = authority_configuration_port
    if port is _DEFAULT:
        port = (
            None
            if materials is None
            else ReferenceAuthorityConfigurationProvider(
                list(materials), order=order, seed=seed_value
            )
        )

    return resolve(
        request=_request(
            authority_code, actor_id, business_context, hr_staleness_threshold_seconds
        ),
        as_of=as_of,
        authority_configuration_port=port,
        actor_person_port=(
            ReferenceActorPersonProvider() if actor_person_port is _DEFAULT else actor_person_port
        ),
        hr_reference_port=(
            ReferenceHrProvider() if hr_reference_port is _DEFAULT else hr_reference_port
        ),
    )


# The keyword arguments that mean the same thing to both compositions.
_SHARED_KEYS = (
    "as_of",
    "authority_code",
    "actor_id",
    "business_context",
    "actor_person_port",
    "hr_reference_port",
    "hr_staleness_threshold_seconds",
)


def assert_parity(
    db: Session,
    materials: Iterable[LineageMaterial],
    *,
    reverse_physical_order: bool = False,
    **kwargs: Any,
) -> AuthorityResolutionResult:
    """Drive ONE scenario through BOTH compositions and require agreement.

    The comparison is `serialize_result`, the canonical byte-stable form of
    the whole result: outcome, resolution_status, result_level_reason, the
    established_state header, the evaluated business context, and all three
    evidence collections WITH their ordering and every field. Comparing the
    serialized form rather than a hand-picked subset is deliberate - a
    weakened comparison is how a parity corpus passes while hiding a real
    divergence (attack surface 15).

    Returns the (identical) result so a caller can additionally assert what
    the scenario is specifically about.
    """

    materials = list(materials)
    shared = {key: kwargs[key] for key in _SHARED_KEYS if key in kwargs}

    # Each parity call is INDEPENDENT: several scenarios reuse the same
    # canonical object ids, so a residue from a previous call would collide on
    # the stable-identity key rather than silently blending two scenarios.
    clear_store(db)

    reference = run_through_reference(materials, **shared)
    postgres = run_through_postgres(
        db, materials, reverse_physical_order=reverse_physical_order, **shared
    )

    assert serialize_result(postgres) == serialize_result(reference), (
        "the PostgreSQL-backed and reference-backed resolutions disagree"
    )
    return postgres
