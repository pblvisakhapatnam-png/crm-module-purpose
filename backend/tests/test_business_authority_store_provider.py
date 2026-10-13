"""PF-1A-E2-B section 9: PROVIDER FIDELITY.

    LOCATING a fact is permitted; JUDGING a fact is not (E2-A 9.5).

Every test here attacks the same question from a different side: does the
PostgreSQL provider hand the kernel the RAW facts, or does it quietly decide
something first? A provider that pre-filters, ranks, deduplicates or
"helpfully" validates is a blocking defect even when its answers agree,
because the excluded fact can ITSELF be the defect the kernel is required to
detect - and because two copies of a semantic rule drift.

The highest-value case in the module, and the reason the withdrawn
retraction-excluding EXISTS is called out by name: a MALFORMED retraction
must not be able to make the only requested-code-bearing or only
reference-bearing version invisible, so that its own defect is reported as an
absent candidate.
"""

from __future__ import annotations

import inspect
import threading
import time

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.authorization.business_authority import repository
from app.modules.authorization.business_authority.contract import (
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
    COMPLETENESS_COMPLETE,
)
from app.modules.authorization.business_authority.ports import (
    AuthorityConfigurationPort,
    AuthorityConfigurationPortError,
)
from app.modules.authorization.business_authority.postgres_provider import (
    PostgresAuthorityConfigurationProvider,
)
from app.modules.authorization.business_authority.store_contract import FAMILY_TABLES
from app.core.database import SessionLocal
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    AUTHORITY_CODE,
    BOOTSTRAP_PROVENANCE,
    RECORDED_AT,
    SYNTHETIC_PROVENANCE_ID,
    T0,
    T1,
    T2,
    T3,
    assignment_payload,
    authority_payload,
    retraction,
    role_payload,
    rule_payload,
    version,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    ASSIGNMENT_ID,
    AUTHORITY_ID,
    ROLE_ID,
    RULE_ID,
    V1,
    V2,
    assignment_material,
    authority_material,
    rule_material,
    world,
)
from tests.fixtures.pf_1a_e2_b_corpus import executable_source, store_covers
from tests.fixtures.pf_1a_e2_b_store import (  # noqa: F401  (store_db is a fixture)
    insert_retraction_row,
    insert_version_row,
    seed_materials,
    store_db,
)

OTHER_CODE = "SOME_OTHER_AUTHORITY"

# The retraction published by the concurrent writer in the interleaving test.
CONCURRENT_RETRACTION_ID = "r-concurrent-publication"


def _provider(store_db) -> PostgresAuthorityConfigurationProvider:
    return PostgresAuthorityConfigurationProvider(store_db)


# ===========================================================================
# The port contract itself
# ===========================================================================


@store_covers()
def test_the_provider_satisfies_the_authority_configuration_port(store_db) -> None:
    """Structural conformance is ASSERTED rather than assumed, and the port is
    exactly candidate discovery plus complete lineage material - there is no
    `list_effective_*` operation, and reintroducing one would be a blocking
    defect."""

    provider = _provider(store_db)
    assert isinstance(provider, AuthorityConfigurationPort)

    operations = {name for name in dir(provider) if not name.startswith("_")}
    assert operations == {
        "find_business_authority_ids_by_code",
        "find_rule_ids_for_authority",
        "find_assignment_ids_for_role",
        "get_lineage",
        "get_published_version",
    }


@store_covers("NS-RS-03")
def test_no_port_operation_exposes_a_recorded_time_cutoff(store_db) -> None:
    """`published_at` / `retracted_at` are recorded-time EVIDENCE and kernel
    validation input. Offering a caller-selected "known as at" bound would be
    a backdating attack under a different name (E2-A 11.8.2), so no operation
    on this provider - or in the repository beneath it - accepts one."""

    provider = _provider(store_db)
    forbidden = {"as_of", "as_at", "known_as_at", "published_before", "recorded_at", "cutoff"}
    for name in (
        "find_business_authority_ids_by_code",
        "find_rule_ids_for_authority",
        "find_assignment_ids_for_role",
        "get_lineage",
        "get_published_version",
    ):
        parameters = set(inspect.signature(getattr(provider, name)).parameters)
        assert forbidden.isdisjoint(parameters), name

    for name, member in vars(repository).items():
        if not callable(member) or name.startswith("_"):
            continue
        try:
            parameters = set(inspect.signature(member).parameters)
        except (TypeError, ValueError):  # pragma: no cover - not a function
            continue
        assert forbidden.isdisjoint(parameters), f"repository.{name}"


# ===========================================================================
# RAW DISCOVERY - identity only, and deliberately a superset
# ===========================================================================


@store_covers()
def test_discovery_returns_stable_identities_only(store_db) -> None:
    seed_materials(store_db, world())
    provider = _provider(store_db)

    assert list(provider.find_business_authority_ids_by_code(AUTHORITY_CODE)) == [AUTHORITY_ID]
    assert list(provider.find_rule_ids_for_authority(AUTHORITY_ID)) == [RULE_ID]
    assert list(provider.find_assignment_ids_for_role(ROLE_ID)) == [ASSIGNMENT_ID]


@store_covers("NS-PR-03")
def test_discovery_applies_no_semantic_predicate_of_any_kind(store_db) -> None:
    """ONE SEEDED CASE PER EXCLUDED PREDICATE (section 9, PROVIDER FIDELITY).

    Every shape below is one a "sensible" WHERE clause would have removed, and
    every one of them must still be discovered. Being a superset is a
    CORRECTNESS requirement, not a performance concession.

    Note which provenance shape is used: `published_at` DECREASING across
    versions, a CLASS A shape. The absent-`published_at` shape the E2-A corpus
    uses for the same purpose is class B1 and is not storable here, so a class
    A equivalent carries the case rather than a constraint being circumvented.
    """

    earlier = RECORDED_AT.replace(hour=11)
    shapes = {
        "retracted": authority_material(
            versions=(version(V1, T0, payload=authority_payload()),),
            retractions=(retraction("r1", V1),),
        ),
        "inactive": authority_material(
            versions=(version(V1, T0, payload=authority_payload(), active_flag=False),)
        ),
        "not yet effective": authority_material(
            versions=(version(V1, T3, payload=authority_payload()),)
        ),
        "already ended": authority_material(
            versions=(version(V1, T0, payload=authority_payload(), declared_effective_to=T1),)
        ),
        "superseded / not the latest": authority_material(
            versions=(
                version(V1, T0, payload=authority_payload()),
                version(V2, T1, payload=authority_payload(OTHER_CODE)),
            )
        ),
        "invalid provenance": authority_material(
            versions=(
                version(V1, T0, payload=authority_payload(), published_at=RECORDED_AT),
                version(V2, T2, payload=authority_payload(), published_at=earlier),
            )
        ),
    }

    for label, authority in shapes.items():
        seed_materials(store_db, [authority])
        discovered = _provider(store_db).find_business_authority_ids_by_code(AUTHORITY_CODE)
        assert list(discovered) == [AUTHORITY_ID], f"discovery excluded a candidate that is {label}"
        store_db.execute(text(f"DELETE FROM {FAMILY_TABLES[BUSINESS_AUTHORITY].retraction}"))
        store_db.execute(text(f"DELETE FROM {FAMILY_TABLES[BUSINESS_AUTHORITY].version}"))
        store_db.execute(text(f"DELETE FROM {FAMILY_TABLES[BUSINESS_AUTHORITY].stable}"))
        store_db.commit()


@store_covers("NS-PR-03", "V-08")
def test_retraction_is_never_a_discovery_filter(store_db) -> None:
    """The withdrawn retraction-excluding EXISTS, probed directly.

    An object whose ONLY code-bearing version is retracted must still be
    returned by `find_business_authority_ids_by_code`, and one whose ONLY
    reference-bearing version is retracted must still be returned by
    `find_rule_ids_for_authority` / `find_assignment_ids_for_role`. Whether
    the retraction is valid is a kernel judgement made after `get_lineage`,
    never a WHERE clause.
    """

    materials = [
        authority_material(
            versions=(version(V1, T0, payload=authority_payload()),),
            retractions=(retraction("r1", V1),),
        ),
        rule_material(
            versions=(version(V1, T0, payload=rule_payload()),),
            retractions=(retraction("r1", V1),),
        ),
        assignment_material(
            versions=(version(V1, T0, payload=assignment_payload()),),
            retractions=(retraction("r1", V1),),
        ),
    ]
    seed_materials(store_db, materials)
    provider = _provider(store_db)

    assert list(provider.find_business_authority_ids_by_code(AUTHORITY_CODE)) == [AUTHORITY_ID]
    assert list(provider.find_rule_ids_for_authority(AUTHORITY_ID)) == [RULE_ID]
    assert list(provider.find_assignment_ids_for_role(ROLE_ID)) == [ASSIGNMENT_ID]


@store_covers("NS-PR-03")
def test_no_discovery_query_contains_a_retraction_anti_join_or_a_semantic_predicate() -> None:
    """READ THE SQL, not the docstring (attack surface 8a).

    The discovery query is a single, small, closed piece of text owned by this
    package, so the assertion is made against its source directly.
    """

    upper = executable_source(repository._discover).upper()

    for forbidden in (
        "NOT EXISTS",
        "RETRACTION",
        "ACTIVE_FLAG",
        "EFFECTIVE_FROM",
        "DECLARED_EFFECTIVE_TO",
        "PUBLISHED_AT",
        "SCOPE_",
        "PARAMETER_",
        "LIMIT ",
        "DISTINCT ON",
    ):
        assert forbidden not in upper, (
            f"the discovery query appears to apply a {forbidden.strip()} predicate"
        )

    # And no discovery entry point may reach a retraction table at all.
    for name in (
        "find_business_authority_ids_by_code",
        "find_rule_ids_for_authority",
        "find_assignment_ids_for_role",
    ):
        assert "retraction" not in executable_source(getattr(repository, name))


@store_covers("NS-RS-04")
def test_recorded_timestamps_are_never_used_as_a_discovery_or_lineage_filter(
    store_db,
) -> None:
    """Shifting only the recorded timestamps, keeping them valid, changes no
    discovery result and no lineage set."""

    def seeded(published_at):
        store_db.execute(text(f"DELETE FROM {FAMILY_TABLES[BUSINESS_AUTHORITY].version}"))
        store_db.execute(text(f"DELETE FROM {FAMILY_TABLES[BUSINESS_AUTHORITY].stable}"))
        store_db.commit()
        seed_materials(
            store_db,
            [
                authority_material(
                    versions=(
                        version(V1, T0, payload=authority_payload(), published_at=published_at),
                    )
                )
            ],
        )
        provider = _provider(store_db)
        lineage = provider.get_lineage(BUSINESS_AUTHORITY, AUTHORITY_ID)
        return (
            list(provider.find_business_authority_ids_by_code(AUTHORITY_CODE)),
            [v.object_version for v in lineage.versions],
        )

    assert seeded(RECORDED_AT) == seeded(RECORDED_AT.replace(year=2027))
    assert seeded(RECORDED_AT) == seeded(RECORDED_AT.replace(year=2020))


# ===========================================================================
# COMPLETE LINEAGE MATERIAL
# ===========================================================================


@store_covers("NS-PR-03")
def test_get_lineage_returns_every_version_and_every_retraction_assertion(
    store_db,
) -> None:
    """Seed ONE object carrying all four kinds at once - retracted, inactive,
    future-dated and superseded - and assert the returned set is complete."""

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),  # superseded, and retracted
            version(V2, T1, payload=authority_payload(), active_flag=False),  # inactive
            version("0003", T3, payload=authority_payload()),  # future-dated at T2
        ),
        retractions=(retraction("r1", V1), retraction("r2", "9999")),
    )
    seed_materials(store_db, [authority])

    material = _provider(store_db).get_lineage(BUSINESS_AUTHORITY, AUTHORITY_ID)

    assert material.object_family == BUSINESS_AUTHORITY
    assert material.object_id == AUTHORITY_ID
    assert material.completeness == COMPLETENESS_COMPLETE
    assert {v.object_version for v in material.versions} == {V1, V2, "0003"}
    assert {a.retraction_id for a in material.retraction_assertions} == {"r1", "r2"}
    # The DANGLING assertion is returned as a FACT for the kernel to classify,
    # not filtered out because its target does not exist.
    assert {a.object_version for a in material.retraction_assertions} == {V1, "9999"}


@store_covers("NS-PR-03")
def test_the_provider_computes_no_closure_effectiveness_ranking_or_deduplication(
    store_db,
) -> None:
    """Given a lineage whose "obvious" answer differs from the raw set, the
    RAW set comes back.

    A judging provider would return one row here - the one it believed was
    effective - and would drop the retraction assertions, so the kernel could
    never tell a correct retraction from a malformed one.
    """

    authority = authority_material(
        versions=(
            # A CONTRADICTORY EXPLICIT OVERLAP: an "obvious" answer would
            # truncate V1 to [T0, T2) and resolve cleanly.
            version(V1, T0, payload=authority_payload(), declared_effective_to=T3),
            version(V2, T2, payload=authority_payload()),
        ),
        retractions=(retraction("r1", V1), retraction("r2", V1)),
    )
    seed_materials(store_db, [authority])

    material = _provider(store_db).get_lineage(BUSINESS_AUTHORITY, AUTHORITY_ID)

    assert len(material.versions) == 2
    by_version = {v.object_version: v for v in material.versions}
    # NOT truncated to the successor's start.
    assert by_version[V1].declared_effective_to == T3
    assert by_version[V2].declared_effective_to is None
    # The DUPLICATED retraction is not deduplicated away.
    assert len(material.retraction_assertions) == 2
    # No derived closure or "current" marker is attached to anything.
    for stored in material.versions:
        assert not hasattr(stored, "asserted_effective_to")
        assert not hasattr(stored, "is_current")


@store_covers("A-11")
def test_an_identity_with_no_material_returns_complete_with_an_empty_version_list(
    store_db,
) -> None:
    """A TRUTHFUL answer the kernel classifies as AUTHORITY_REFERENCE_DANGLING
    - never an error, never UNAVAILABLE and never a "no such object" signal
    (9.3.2). This is exactly why the store's missing-parent foreign keys are a
    persistence-only invariant rather than a semantic one."""

    provider = _provider(store_db)

    # An identity row that exists and carries nothing...
    seed_materials(store_db, [authority_material(versions=())])
    existing = provider.get_lineage(BUSINESS_AUTHORITY, AUTHORITY_ID)
    assert existing.completeness == COMPLETENESS_COMPLETE
    assert existing.versions == ()
    assert existing.retraction_assertions == ()

    # ...and an identity this store has never heard of decode to the SAME
    # provider-neutral state, which is the whole B2-03 rationale.
    unknown = provider.get_lineage(BUSINESS_AUTHORITY_ROLE, "never-published")
    assert unknown.completeness == COMPLETENESS_COMPLETE
    assert unknown.versions == ()


@store_covers()
def test_lineage_is_returned_under_an_explicit_total_order(store_db) -> None:
    """Deterministic ordering is applied IN THE QUERY, so the provider never
    returns an order-dependent result. Inserting the rows in the opposite
    physical order changes nothing."""

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T1, payload=authority_payload()),
            version("0003", T2, payload=authority_payload()),
        ),
        retractions=(retraction("r2", V2), retraction("r1", V1)),
    )

    seed_materials(store_db, [authority])
    forward = _provider(store_db).get_lineage(BUSINESS_AUTHORITY, AUTHORITY_ID)

    for table in ("retraction", "version", "stable"):
        store_db.execute(
            text(f"DELETE FROM {getattr(FAMILY_TABLES[BUSINESS_AUTHORITY], table)}")
        )
    store_db.commit()

    seed_materials(store_db, [authority], reverse_physical_order=True)
    reversed_insert = _provider(store_db).get_lineage(BUSINESS_AUTHORITY, AUTHORITY_ID)

    assert [v.object_version for v in forward.versions] == [V1, V2, "0003"]
    assert forward.versions == reversed_insert.versions
    assert forward.retraction_assertions == reversed_insert.retraction_assertions


@store_covers()
def test_no_repository_query_uses_a_one_row_shortcut_where_multiplicity_matters() -> None:
    """`first()`, `LIMIT 1`, `scalar()` and `DISTINCT ON` are how a provider
    hides ambiguity. The repository returns everything it found and the kernel
    fails closed on multiplicity (attack surface 13)."""

    source = executable_source(repository)
    for forbidden in (".first()", "LIMIT 1", ".scalar()", ".scalar_one()", "DISTINCT ON"):
        assert forbidden not in source, forbidden


@store_covers()
def test_a_duplicate_identity_would_surface_rather_than_being_silently_reduced() -> None:
    """`load_version` returns one row only because the unique
    (object_id, object_version) key makes at most one possible. If that key
    were ever removed, the multiplicity RAISES instead of being collapsed to
    an arbitrary first row."""

    source = executable_source(repository.load_version)
    assert "len(rows) > 1" in source
    assert "raise AuthorityConfigurationPortError" in source


# ===========================================================================
# IMMUTABLE DEREFERENCE
# ===========================================================================


@store_covers("NS-EV-07")
def test_dereference_returns_the_exact_version_even_when_retracted_or_superseded(
    store_db,
) -> None:
    """Retraction, correction, supersession and deactivation affect RESOLUTION
    only. Dereference is always available, forever, and never substitutes
    another version."""

    corrected_later = RECORDED_AT.replace(hour=13)
    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(
                V2,
                T0,
                payload=authority_payload(OTHER_CODE),
                corrects_object_version=V1,
                published_at=corrected_later,
            ),
        ),
        retractions=(retraction("r1", V1),),
    )
    seed_materials(store_db, [authority])
    provider = _provider(store_db)

    retracted = provider.get_published_version(BUSINESS_AUTHORITY, AUTHORITY_ID, V1)
    assert retracted.object_version == V1
    assert retracted.payload.authority_code == AUTHORITY_CODE
    assert retracted.published_at == RECORDED_AT

    superseding = provider.get_published_version(BUSINESS_AUTHORITY, AUTHORITY_ID, V2)
    assert superseding.payload.authority_code == OTHER_CODE

    # A version this store genuinely does not hold is an absence, not a
    # substitution.
    with pytest.raises(KeyError):
        provider.get_published_version(BUSINESS_AUTHORITY, AUTHORITY_ID, "9999")


# ===========================================================================
# NS-PT-01  the PORT's read/transport behaviour, at the WIRED repository
# ===========================================================================


class _TruncatingResult:
    """A result that drops its last row while the query still reports the true
    count - the exact shape of a truncated read."""

    def __init__(self, rows) -> None:
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows[:-1]


@store_covers("NS-PT-01")
def test_a_truncated_read_is_never_reported_as_complete(store_db, monkeypatch) -> None:
    """A truncated list presented as COMPLETE is a blocking defect (9.3.2).

    The repository asks each query for `COUNT(*) OVER ()` alongside its rows,
    so a short result is DETECTED here rather than handed to the kernel as
    complete material. The failure surfaces as a port error, which the kernel
    maps to AUTHORITY_CONFIGURATION_UNAVAILABLE - never an empty result.
    """

    seed_materials(
        store_db,
        [
            authority_material(
                versions=(
                    version(V1, T0, payload=authority_payload()),
                    version(V2, T2, payload=authority_payload()),
                )
            )
        ],
    )

    real_execute = store_db.execute

    def truncating_execute(statement, params=None, *args, **kwargs):
        result = real_execute(statement, params, *args, **kwargs)
        rows = result.mappings().all()
        return _TruncatingResult(rows)

    monkeypatch.setattr(store_db, "execute", truncating_execute)

    with pytest.raises(AuthorityConfigurationPortError):
        _provider(store_db).get_lineage(BUSINESS_AUTHORITY, AUTHORITY_ID)


@store_covers("NS-PT-01")
def test_a_read_error_raises_a_port_error_rather_than_returning_an_empty_result(
    store_db,
) -> None:
    """A REAL database failure, not a simulated one: the transaction is put
    into a failed state, so every subsequent read in it genuinely errors."""

    seed_materials(store_db, world())

    with pytest.raises(Exception):
        store_db.execute(text("SELECT 1 / 0"))

    provider = _provider(store_db)
    with pytest.raises(AuthorityConfigurationPortError):
        provider.get_lineage(BUSINESS_AUTHORITY, AUTHORITY_ID)
    with pytest.raises(AuthorityConfigurationPortError):
        provider.find_business_authority_ids_by_code(AUTHORITY_CODE)

    store_db.rollback()


@store_covers("NS-PT-01")
def test_one_lineage_read_never_straddles_a_concurrent_publication(store_db) -> None:
    """COMPLETE must mean COHERENT, proved against a REAL committing writer.

    THE DEFECT THIS CLOSES (independent review finding F1). `get_lineage`
    used to issue TWO statements - one for versions, one for retractions.
    Under PostgreSQL READ COMMITTED each statement takes its OWN snapshot, so
    a publication committing between them could be half-seen: the versions
    from BEFORE the correction together with the retraction from AFTER it - a
    combination that never existed in any committed state - returned with
    `completeness = COMPLETE`.

    THE INTERLEAVING IS FORCED, NOT HOPED FOR. A writer connection takes an
    ACCESS EXCLUSIVE lock on the RETRACTION table only, then - still
    uncommitted - publishes both a new correcting version and a retraction of
    the old one. The version table is deliberately left unlocked, so at that
    instant:

        a versions read SUCCEEDS and returns the PRE-commit set;
        a retractions read must WAIT.

    which is precisely the state that produces the hybrid. The reader is then
    started on its own connection and blocks. The test does not sleep and
    hope: it waits until POSTGRESQL ITSELF REPORTS an ungranted lock request
    on that table, which is the deterministic proof that the reader is inside
    lineage acquisition. Only then does the writer commit.

    A conforming reader must come back with one of the two states that
    genuinely existed, never with a mixture of both.
    """

    version_table = FAMILY_TABLES[BUSINESS_AUTHORITY].version
    retraction_table = FAMILY_TABLES[BUSINESS_AUTHORITY].retraction

    seed_materials(
        store_db,
        [authority_material(versions=(version(V1, T0, payload=authority_payload()),))],
    )
    # Hold no lock of this session own, so the blocked party can only be the
    # reader and the blocking party can only be the writer.
    store_db.rollback()

    def ungranted_lock_requests(db, table: str) -> int:
        return db.execute(
            text(
                "SELECT COUNT(*) FROM pg_locks l JOIN pg_class c ON c.oid = l.relation "
                "WHERE c.relname = :table AND NOT l.granted"
            ),
            {"table": table},
        ).scalar_one()

    observed: dict = {}
    reader_failure: list[BaseException] = []
    reader_started = threading.Event()

    # Three connections are checked out EXPLICITLY and held for the whole
    # test, rather than left to a Session to acquire and release around each
    # transaction. A Session returns its connection to the pool when its
    # transaction ends, which would let two of these parties silently share
    # one physical backend and make the interleaving unprovable.
    engine = store_db.get_bind()
    writer_connection = engine.connect()
    control_connection = engine.connect()
    reader_connection = engine.connect()

    def read_lineage(reader: Session) -> None:
        try:
            observed["material"] = PostgresAuthorityConfigurationProvider(reader).get_lineage(
                BUSINESS_AUTHORITY, AUTHORITY_ID
            )
            reader.rollback()
        except BaseException as error:  # noqa: BLE001 - re-raised on the main thread
            reader_failure.append(error)

    writer = Session(bind=writer_connection)
    control = Session(bind=control_connection)
    reader_session = Session(bind=reader_connection)
    reader_thread = threading.Thread(target=read_lineage, args=(reader_session,), daemon=True)
    try:
        writer_pid = writer.execute(text("SELECT pg_backend_pid()")).scalar_one()
        control_pid = control.execute(text("SELECT pg_backend_pid()")).scalar_one()
        observed["reader_backend_pid"] = reader_session.execute(
            text("SELECT pg_backend_pid()")
        ).scalar_one()
        reader_session.rollback()
        reader_started.set()

        # 1. The writer blocks retraction reads, then publishes BOTH halves of
        #    one lineage-changing commit, and does not commit yet.
        writer.execute(text(f"LOCK TABLE {retraction_table} IN ACCESS EXCLUSIVE MODE"))
        insert_version_row(
            writer,
            BUSINESS_AUTHORITY,
            {
                "object_id": AUTHORITY_ID,
                "object_version": V2,
                "effective_from": T0,
                "declared_effective_to": None,
                "active_flag": True,
                "corrects_object_version": V1,
                "publication_reference_type": BOOTSTRAP_PROVENANCE,
                "publication_reference_id": SYNTHETIC_PROVENANCE_ID,
                "published_at": RECORDED_AT,
                "authority_code": AUTHORITY_CODE,
                "authority_name": "Credit Assessor",
                "description": None,
                "is_protected_meta_authority": False,
            },
        )
        insert_retraction_row(
            writer,
            BUSINESS_AUTHORITY,
            {
                "object_id": AUTHORITY_ID,
                "retraction_id": CONCURRENT_RETRACTION_ID,
                "object_version": V1,
                "retracted_at": RECORDED_AT,
                "publication_reference_type": BOOTSTRAP_PROVENANCE,
                "publication_reference_id": SYNTHETIC_PROVENANCE_ID,
            },
        )

        # 2. THE HYBRID IS GENUINELY AVAILABLE AT THIS INSTANT: an independent
        #    session reads the version table without waiting and sees the
        #    PRE-commit version set, while the retraction table is locked.
        pre_commit_versions = (
            control.execute(
                text(
                    f"SELECT object_version FROM {version_table} WHERE object_id = :object_id"
                ),
                {"object_id": AUTHORITY_ID},
            )
            .scalars()
            .all()
        )
        assert sorted(pre_commit_versions) == [V1], pre_commit_versions
        control.rollback()

        # 3. The reader enters lineage acquisition and blocks. Waited for, not
        #    slept through: PostgreSQL reporting an ungranted lock request is
        #    the proof that the interleaving actually happened.
        reader_thread.start()
        assert reader_started.wait(timeout=60), "the reader never started"
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if reader_failure:
                break
            if ungranted_lock_requests(control, retraction_table) >= 1:
                observed["blocked"] = True
                break
            control.rollback()
        assert not reader_failure, f"the reader failed: {reader_failure[0]!r}"
        assert observed.get("blocked"), (
            "the reader never blocked on the retraction table, so the concurrent "
            "publication was not actually interleaved with lineage acquisition"
        )
        assert reader_thread.is_alive(), "the reader returned before the writer committed"
        control.rollback()

        # 4. The publication commits WHILE the reader is inside acquisition.
        writer.commit()

        reader_thread.join(timeout=60)
        assert not reader_thread.is_alive(), "the reader never returned"
        assert not reader_failure, f"the reader failed: {reader_failure[0]!r}"
    finally:
        # The writer is released FIRST, so a reader blocked on its lock can
        # finish before it is joined. `ident` is None until a thread has
        # actually started, and joining an unstarted thread would raise from
        # inside this cleanup and MASK whatever really failed.
        writer.rollback()
        writer.close()
        control.rollback()
        control.close()
        if reader_thread.ident is not None:
            reader_thread.join(timeout=60)
        reader_session.close()
        for connection in (writer_connection, control_connection, reader_connection):
            connection.close()

    # Three genuinely distinct backends, so this was real concurrency.
    assert len({writer_pid, control_pid, observed["reader_backend_pid"]}) == 3

    material = observed["material"]
    assert material.completeness == COMPLETENESS_COMPLETE
    versions = {v.object_version for v in material.versions}
    retractions = {r.retraction_id for r in material.retraction_assertions}

    # THE INVARIANT: the two halves of one commit are seen together or not at
    # all. The two-statement implementation returned {V1} with the retraction.
    assert (V2 in versions) == (CONCURRENT_RETRACTION_ID in retractions), (
        f"a lineage read straddled a concurrent publication: versions={sorted(versions)}, "
        f"retractions={sorted(retractions)}"
    )
    assert (versions, retractions) in (
        ({V1}, set()),
        ({V1, V2}, {CONCURRENT_RETRACTION_ID}),
    ), (sorted(versions), sorted(retractions))

    # And, deterministically, the one statement takes its snapshot AFTER the
    # lock it waited for is released, so it observes the post-commit state.
    assert versions == {V1, V2}
    assert retractions == {CONCURRENT_RETRACTION_ID}


@store_covers("NS-PT-01")
def test_a_real_lock_timeout_raises_a_port_error(store_db) -> None:
    """A REAL, database-produced timeout, on a connection of its own.

    A second connection takes an ACCESS EXCLUSIVE lock on the version table,
    which blocks every read of it; the reading transaction sets a short
    `lock_timeout`, so PostgreSQL itself aborts the wait. That is a genuine
    transport-level failure rather than an injected exception, and it must
    surface as a port error - never as "no candidates found".

    WHY THIS TEST OWNS ITS CONNECTION AND USES `SET LOCAL` (independent
    review finding F2). It used to set a SESSION-level `lock_timeout` on the
    SHARED `store_db` session and undo it afterwards with `RESET`. That is
    unsafe for a reason that has nothing to do with what is being tested: a
    Session RELEASES its physical connection to the pool when its transaction
    ends, so the later `RESET` can be issued on a DIFFERENT checkout while the
    original pooled connection keeps the 250ms setting. A later, entirely
    unrelated test that happened to draw that connection could then fail with
    `LockNotAvailable`. Two properties remove the hazard rather than making it
    less likely:

        the connection is checked out EXPLICITLY and closed by this test, so
            no other test can be handed it mid-experiment; and
        the timeout is `SET LOCAL` inside the reading transaction, so
            PostgreSQL itself reverts it at ROLLBACK - the cleanup cannot land
            on the wrong connection because there is no separate cleanup
            statement to misdirect.

    Both halves are then PROVEN rather than assumed: the same backend PID is
    asserted before and after, `lock_timeout` is asserted back at its server
    default on that same physical connection before it is released, and a
    sweep of freshly drawn pooled connections is asserted clean.
    """

    locked_table = FAMILY_TABLES[BUSINESS_AUTHORITY].version
    seed_materials(store_db, world())
    # End this session's transaction before the blocker starts, so it holds no
    # lock of its own and the blocker cannot be the one left waiting.
    store_db.rollback()

    locked = threading.Event()
    release = threading.Event()
    failure: list[BaseException] = []

    def hold_the_lock() -> None:
        try:
            with SessionLocal() as blocker:
                blocker.execute(
                    text(f"LOCK TABLE {locked_table} IN ACCESS EXCLUSIVE MODE")
                )
                locked.set()
                release.wait(timeout=60)
                blocker.rollback()
        except BaseException as error:  # noqa: BLE001 - reported to the main thread
            failure.append(error)
            locked.set()

    engine = store_db.get_bind()
    timed_connection = engine.connect()
    holder = threading.Thread(target=hold_the_lock, daemon=True)
    try:
        backend_pid = timed_connection.execute(
            text("SELECT pg_backend_pid()")
        ).scalar_one()
        server_default_timeout = timed_connection.execute(
            text("SHOW lock_timeout")
        ).scalar_one()
        timed_connection.rollback()

        holder.start()
        assert locked.wait(timeout=60), "the blocking lock was never acquired"
        assert not failure, f"the blocking session failed: {failure[0]!r}"

        timed = Session(bind=timed_connection)
        try:
            timed.execute(text("SET LOCAL lock_timeout = '250ms'"))
            assert timed.execute(text("SHOW lock_timeout")).scalar_one() == "250ms"

            # Asserted from PostgreSQL's own catalogue rather than assumed: if
            # the lock were not actually held, the read would simply succeed
            # and the assertion below would pass vacuously, proving nothing.
            held = timed.execute(
                text(
                    "SELECT COUNT(*) FROM pg_locks l JOIN pg_class c ON c.oid = l.relation "
                    "WHERE c.relname = :table AND l.mode = 'AccessExclusiveLock' AND l.granted"
                ),
                {"table": locked_table},
            ).scalar_one()
            assert held == 1, f"no ACCESS EXCLUSIVE lock is held on {locked_table}"

            with pytest.raises(AuthorityConfigurationPortError):
                PostgresAuthorityConfigurationProvider(timed).get_lineage(
                    BUSINESS_AUTHORITY, AUTHORITY_ID
                )
            timed.rollback()
        finally:
            timed.close()

        # THE CLEANUP PROOF, on the SAME physical backend, before the
        # connection can be returned to the pool.
        assert (
            timed_connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
            == backend_pid
        )
        assert (
            timed_connection.execute(text("SHOW lock_timeout")).scalar_one()
            == server_default_timeout
        )
        timed_connection.rollback()
    finally:
        release.set()
        holder.join(timeout=60)
        timed_connection.close()

    # And nothing the pool can hand to a later test carries the setting.
    sampled = [SessionLocal() for _ in range(6)]
    try:
        residue = [
            (
                sample.execute(text("SELECT pg_backend_pid()")).scalar_one(),
                sample.execute(text("SHOW lock_timeout")).scalar_one(),
            )
            for sample in sampled
        ]
    finally:
        for sample in sampled:
            sample.rollback()
            sample.close()
    assert all(value == server_default_timeout for _pid, value in residue), residue


@store_covers()
def test_no_e2b_test_returns_a_connection_to_the_pool_in_autocommit(store_db) -> None:
    """No pooled connection may carry transaction-mode state to a stranger.

    THE DEFECT THIS CLOSES, found while verifying correction C2. The criterion
    N2 determinism test needs autocommit for `VACUUM (FULL)`, and it used to
    get it by calling `set_autocommit(True)` on a raw DBAPI connection. The
    pool's reset-on-return issues a ROLLBACK but does NOT restore autocommit,
    so that connection went back into the pool STILL IN AUTOCOMMIT. Any later
    test that drew it found `LOCK TABLE` rejected outright with
    `NoActiveSqlTransaction`, and - far worse, because it is SILENT -
    `SET LOCAL` simply ineffective, since neither has a transaction block to
    act in. That is the same class of defect as independent review finding F2:
    a test leaving connection state behind for a stranger.

    This is the same-process guard. It draws a spread of pooled connections
    and requires each to be in an ordinary transactional mode, which is what
    every other test in this suite assumes without saying so.
    """

    engine = store_db.get_bind()
    sampled = [SessionLocal() for _ in range(8)]
    try:
        for sample in sampled:
            # The DBAPI flag is read DIRECTLY. `get_isolation_level()` asks the
            # server for `transaction isolation level` and never reports
            # autocommit at all, so it cannot see this defect; the psycopg
            # connection's own `autocommit` attribute can.
            driver_connection = sample.connection().connection.dbapi_connection
            assert getattr(driver_connection, "autocommit", False) is False, (
                "a pooled connection came back in AUTOCOMMIT; SET LOCAL would be "
                "silently ineffective and LOCK TABLE would be rejected on it"
            )
            sample.rollback()
    finally:
        for sample in sampled:
            sample.close()

    # And a connection drawn straight from the engine agrees.
    with engine.connect() as connection:
        assert getattr(connection.connection.dbapi_connection, "autocommit", False) is False


@store_covers()
def test_the_timeout_test_never_sets_a_session_level_lock_timeout() -> None:
    """The structural half of finding F2, so the fix cannot silently regress.

    `SET LOCAL` is reverted by PostgreSQL at transaction end on the connection
    that carries it. A bare `SET` is not, and a separate `RESET` can be issued
    on a different pooled checkout, leaving a booby-trapped connection behind
    for an unrelated test. This module must therefore contain no session-level
    `SET`, and no `RESET` at all.
    """

    import tests.test_business_authority_store_provider as module

    statements = [
        line.strip()
        for line in executable_source(module).splitlines()
        if "lock_timeout" in line
    ]
    assert statements, "the lock_timeout test disappeared"
    for statement in statements:
        assert "RESET" not in statement, statement
        if "SET" in statement:
            assert "SET LOCAL" in statement, statement


@store_covers("NS-PT-01")
def test_an_unknown_object_family_raises_rather_than_reaching_sql(store_db) -> None:
    """Table names come ONLY from the closed family registry; a caller-supplied
    family is rejected rather than interpolated (attack surface 25)."""

    with pytest.raises(AuthorityConfigurationPortError):
        _provider(store_db).get_lineage("'; DROP TABLE role; --", AUTHORITY_ID)

    # And the table it named is still there.
    assert (
        store_db.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = current_schema() AND table_name = 'role'"
            )
        ).scalar_one()
        == 1
    )


@store_covers()
def test_every_repository_query_binds_its_caller_controlled_values(store_db) -> None:
    """No string interpolation of a caller-controlled value, anywhere.

    Table and column names are interpolated - they come from this package's
    own closed registry - but every value the caller supplies is bound.
    """

    seed_materials(store_db, world())
    hostile = "' OR 1=1 --"
    provider = _provider(store_db)

    assert list(provider.find_business_authority_ids_by_code(hostile)) == []
    assert list(provider.find_rule_ids_for_authority(hostile)) == []
    assert list(provider.find_assignment_ids_for_role(hostile)) == []
    assert provider.get_lineage(BUSINESS_AUTHORITY, hostile).versions == ()
