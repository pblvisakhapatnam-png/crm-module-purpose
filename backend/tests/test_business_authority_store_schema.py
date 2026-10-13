"""PF-1A-E2-B section 9: SCHEMA / MIGRATION and STORAGE INTEGRITY.

Three questions, and the answers must not be confused with one another:

    WHAT THE SCHEMA REJECTS      class B1 and class B2. The INSERT must FAIL
                                 against the MIGRATED SCHEMA EXACTLY AS
                                 SHIPPED - never with a constraint disabled,
                                 deferred, dropped or ALTERed in a fixture,
                                 because a "pass" obtained that way says
                                 nothing about what will actually be deployed.
    WHAT THE SCHEMA MUST ACCEPT  class A. Every one of the fourteen is a state
                                 E2-A requires the KERNEL to reject; if the
                                 database rejected it first, the kernel could
                                 never be proved to classify it and the defect
                                 class would be silently suppressed.
    WHAT THE SCHEMA MUST NOT DO  normalise. What was published is what is
                                 stored and what is read back, byte for byte.

A structural rejection is a VERIFICATION-PLACEMENT fact, never a semantic
exemption: E2-A still proves every class B1 shape's fail-closed response at
its own named boundary, and class B2 records honestly that there is no
provider-neutral semantic rule to prove at all.
"""

from __future__ import annotations

import inspect
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError

from app.modules.authorization.business_authority import (
    postgres_provider,
    production_composition,
    repository,
)
from app.modules.authorization.business_authority.contract import (
    BOOTSTRAP_PROVENANCE,
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
)
from app.modules.authorization.business_authority.store_contract import (
    ALL_STORE_TABLES,
    FAMILY_TABLES,
)
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    RECORDED_AT,
    SYNTHETIC_PROVENANCE_ID,
    T0,
    T1,
    T2,
    T3,
    authority_payload,
    retraction,
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
    role_material,
    rule_material,
    world,
)
from tests.fixtures.pf_1a_e2_b_corpus import (
    E1_PROTECTED_TABLES,
    EXPECTED_CONSTRAINTS,
    EXPECTED_INDEXES,
    executable_source,
    store_covers,
)
from tests.fixtures.pf_1a_e2_b_store import (  # noqa: F401  (store_db is a fixture)
    count_store_rows,
    insert_retraction_row,
    insert_stable_identity,
    insert_version_row,
    seed_materials,
    store_db,
)

E2_B_REVISION = "20260904_0031"
E2_B_DOWN_REVISION = "20260831_0030"


# ===========================================================================
# Helpers
# ===========================================================================


def _valid_version(**overrides):
    """A structurally valid version row. Every rejection test perturbs ONE field."""

    values = {
        "object_id": AUTHORITY_ID,
        "object_version": V1,
        "effective_from": T0,
        "declared_effective_to": None,
        "active_flag": True,
        "corrects_object_version": None,
        "publication_reference_type": BOOTSTRAP_PROVENANCE,
        "publication_reference_id": SYNTHETIC_PROVENANCE_ID,
        "published_at": RECORDED_AT,
    }
    values.update(overrides)
    return values


def _valid_retraction(**overrides):
    values = {
        "object_id": AUTHORITY_ID,
        "retraction_id": "r1",
        "object_version": V1,
        "retracted_at": RECORDED_AT,
        "publication_reference_type": BOOTSTRAP_PROVENANCE,
        "publication_reference_id": SYNTHETIC_PROVENANCE_ID,
    }
    values.update(overrides)
    return values


def _rejection_detail(error) -> tuple[str | None, str]:
    """The constraint name PostgreSQL itself reported, plus the message.

    Reading `diag.constraint_name` rather than pattern-matching prose is what
    lets a test name the exact constraint that rejected the write, which is
    what section 9 requires of every class B1 and B2 case.
    """

    diagnostic = getattr(getattr(error, "orig", None), "diag", None)
    name = getattr(diagnostic, "constraint_name", None)
    column = getattr(diagnostic, "column_name", None)
    return name or column, str(error)


def _assert_rejected(db, write, *, constraint: str) -> None:
    """The write FAILS, and the thing that rejected it is the named one."""

    with pytest.raises((IntegrityError, DataError)) as caught:
        write()
        db.flush()
    reported, message = _rejection_detail(caught.value)
    assert reported == constraint or constraint in message, (
        f"expected rejection by {constraint!r}, got {reported!r}: {message}"
    )
    db.rollback()


def _rows(db, table, **where):
    clause = " AND ".join(f"{column} = :{column}" for column in where) or "TRUE"
    return db.execute(text(f"SELECT * FROM {table} WHERE {clause}"), where).mappings().all()


# ===========================================================================
# SCHEMA / MIGRATION
# ===========================================================================


@store_covers()
def test_the_migration_graph_has_one_head_and_preserves_e2_b_lineage(store_db) -> None:
    """E2-B stays correctly parented while authorized successors may advance the head.

    The original E2-B acceptance test asserted that E2-B itself was the repository
    head. That was a phase-local fact: a later authorized migration must advance the
    unique head. The durable E2-B contract is that revision 0031 remains present,
    keeps its 0030 parent, and stays on the one active migration lineage.
    """

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = list(script.get_heads())
    assert len(heads) == 1, heads
    current_head = heads[0]

    e2_b_revision = script.get_revision(E2_B_REVISION)
    assert e2_b_revision is not None
    assert e2_b_revision.down_revision == E2_B_DOWN_REVISION

    ancestry = {
        revision.revision for revision in script.iterate_revisions(current_head, "base")
    }
    assert E2_B_REVISION in ancestry, (current_head, sorted(ancestry))

    stamped = store_db.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    assert stamped == [current_head], stamped


@store_covers()
def test_every_store_table_exists_and_the_migration_seeded_nothing(store_db) -> None:
    """Acceptance criterion S: no catalogue, no rule, no assignment, no
    bootstrap holder. Q-10 remains open and untouched."""

    present = set(
        store_db.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'"
            )
        )
        .scalars()
        .all()
    )
    assert set(ALL_STORE_TABLES) <= present
    assert len(ALL_STORE_TABLES) == 12

    # The `store_db` fixture clears the store, so this proves emptiness of the
    # fixture state; the migration's own no-seed property is proved by the
    # clean-database check below.
    assert set(count_store_rows(store_db).values()) == {0}


@store_covers()
def test_a_clean_database_upgraded_to_head_contains_no_authority_configuration() -> None:
    """The migration itself seeds nothing.

    Asserted against the revision SOURCE rather than against a live table,
    because a live table can be emptied by a fixture while the migration still
    inserts rows on the next clean deployment.
    """

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(Config("alembic.ini"))
    source = inspect.getsource(script.get_revision(E2_B_REVISION).module)
    upgrade_source = source.split("def upgrade()")[1].split("def downgrade()")[0]
    for forbidden in ("op.bulk_insert", "INSERT INTO", "op.execute"):
        assert forbidden not in upgrade_source, (
            f"the migration appears to seed authority configuration via {forbidden}"
        )


@store_covers()
def test_the_structural_constraint_set_is_exactly_the_one_section_5_6_lists(store_db) -> None:
    """"No more, no less" (section 5.7).

    A "helpful" extra constraint silently moves a class A fixture into B1 or
    B2 and suppresses a defect class the kernel owns; a silently removed one
    strips a rejection proof. Both directions are reconciliation findings, so
    the actual set is enumerated and compared rather than spot-checked.
    """

    rows = (
        store_db.execute(
            text(
                """
                SELECT conrelid::regclass::text AS tbl, contype::text AS kind, conname
                FROM pg_constraint
                WHERE conrelid::regclass::text = ANY(:tables)
                """
            ),
            {"tables": list(ALL_STORE_TABLES)},
        )
        .mappings()
        .all()
    )

    actual: dict[str, set[tuple[str, str]]] = {table: set() for table in ALL_STORE_TABLES}
    for row in rows:
        actual[row["tbl"]].add((row["kind"], row["conname"]))

    assert actual == EXPECTED_CONSTRAINTS


@store_covers()
def test_the_index_set_supports_discovery_lineage_and_dereference(store_db) -> None:
    rows = (
        store_db.execute(
            text(
                "SELECT tablename, indexname FROM pg_indexes "
                "WHERE tablename = ANY(:tables)"
            ),
            {"tables": list(ALL_STORE_TABLES)},
        )
        .mappings()
        .all()
    )
    actual: dict[str, set[str]] = {table: set() for table in ALL_STORE_TABLES}
    for row in rows:
        actual[row["tablename"]].add(row["indexname"])

    assert actual == EXPECTED_INDEXES


@store_covers()
def test_no_stored_derived_closure_or_current_flag_column_exists(store_db) -> None:
    """Closure is DERIVED per resolution (11.4). Storing it would create a
    second source of truth that can disagree with the kernel."""

    columns = (
        store_db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = ANY(:tables)"
            ),
            {"tables": list(ALL_STORE_TABLES)},
        )
        .scalars()
        .all()
    )
    forbidden = {
        "asserted_effective_to",
        "is_current",
        "is_effective",
        "effective_to",
        "current_version",
        "is_retracted",
        "is_superseded",
    }
    assert forbidden.isdisjoint(set(columns))


@store_covers()
def test_no_existing_table_was_altered_and_no_link_to_the_login_role_table_exists(
    store_db,
) -> None:
    """Section 7: E1 is immutable, and a Business Authority Role is NOT an
    Application/Login Role. A foreign key between them would be a blocking
    defect regardless of how convenient the join looked."""

    for table in E1_PROTECTED_TABLES:
        assert (
            store_db.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = current_schema() AND table_name = :name"
                ),
                {"name": table},
            ).scalar_one()
            == 1
        )

    # No foreign key in either direction between the store and any E1 or
    # identity table.
    crossing = (
        store_db.execute(
            text(
                """
                SELECT conname
                FROM pg_constraint
                WHERE contype = 'f'
                  AND (
                        (conrelid::regclass::text = ANY(:store)
                         AND confrelid::regclass::text = ANY(:e1))
                     OR (conrelid::regclass::text = ANY(:e1)
                         AND confrelid::regclass::text = ANY(:store))
                  )
                """
            ),
            {"store": list(ALL_STORE_TABLES), "e1": list(E1_PROTECTED_TABLES)},
        )
        .scalars()
        .all()
    )
    assert crossing == []


# ===========================================================================
# STORAGE INTEGRITY - CLASS B1 STRUCTURAL REJECTION (twelve fixtures)
# ===========================================================================
# Each asserts the WRITE FAILS against the shipped schema and names the
# constraint that rejected it. E2-A proves the provider-neutral fail-closed
# response for the equivalent malformed input at the boundary section 5.7
# names - PURE KERNEL for all but B1-06/B1-07, which are DTO/port
# well-formedness cases. Neither half discharges the other.


@store_covers("B1-01")
def test_b1_01_duplicate_object_id_and_object_version_is_rejected(store_db) -> None:
    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    insert_version_row(store_db, BUSINESS_AUTHORITY, _valid_version())
    store_db.flush()
    _assert_rejected(
        store_db,
        lambda: insert_version_row(store_db, BUSINESS_AUTHORITY, _valid_version()),
        constraint="uq_ba_authority_version_object_version",
    )


def _assignment_version(**overrides):
    values = _valid_version(object_id=ASSIGNMENT_ID)
    values.update(
        {
            "business_authority_role_object_id": ROLE_ID,
            "person_id": "person-0001",
            "position_id": None,
            "scope_type": "GLOBAL",
            "scope_id": None,
        }
    )
    values.update(overrides)
    return values


def _prepare_assignment(store_db) -> None:
    insert_stable_identity(store_db, BUSINESS_AUTHORITY_ROLE, ROLE_ID)
    insert_stable_identity(store_db, BUSINESS_AUTHORITY_ASSIGNMENT, ASSIGNMENT_ID)
    store_db.flush()


@store_covers("B1-02")
def test_b1_02_an_assignment_carrying_both_targets_is_rejected(store_db) -> None:
    _prepare_assignment(store_db)
    _assert_rejected(
        store_db,
        lambda: insert_version_row(
            store_db,
            BUSINESS_AUTHORITY_ASSIGNMENT,
            _assignment_version(person_id="person-0001", position_id="position-0001"),
        ),
        constraint="ck_ba_assignment_version_target_xor",
    )


@store_covers("B1-03")
def test_b1_03_an_assignment_carrying_neither_target_is_rejected(store_db) -> None:
    _prepare_assignment(store_db)
    _assert_rejected(
        store_db,
        lambda: insert_version_row(
            store_db,
            BUSINESS_AUTHORITY_ASSIGNMENT,
            _assignment_version(person_id=None, position_id=None),
        ),
        constraint="ck_ba_assignment_version_target_xor",
    )


@store_covers("B1-04")
def test_b1_04_a_declared_end_before_the_start_is_rejected(store_db) -> None:
    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    store_db.flush()
    _assert_rejected(
        store_db,
        lambda: insert_version_row(
            store_db,
            BUSINESS_AUTHORITY,
            _valid_version(effective_from=T2, declared_effective_to=T0),
        ),
        constraint="ck_ba_authority_version_interval",
    )


@store_covers("B1-05")
def test_b1_05_a_declared_end_equal_to_the_start_is_rejected(store_db) -> None:
    """The EMPTY interval. Rejected by the SAME single-row interval CHECK -
    which is why B1-04 and B1-05 are two manifest IDs over two inputs rather
    than one entry covering both shapes."""

    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    store_db.flush()
    _assert_rejected(
        store_db,
        lambda: insert_version_row(
            store_db,
            BUSINESS_AUTHORITY,
            _valid_version(effective_from=T2, declared_effective_to=T2),
        ),
        constraint="ck_ba_authority_version_interval",
    )


@store_covers("B1-06")
def test_b1_06_a_version_with_no_effective_from_is_rejected(store_db) -> None:
    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    store_db.flush()
    _assert_rejected(
        store_db,
        lambda: insert_version_row(
            store_db, BUSINESS_AUTHORITY, _valid_version(effective_from=None)
        ),
        constraint="effective_from",
    )


@store_covers("B1-07")
def test_b1_07_a_version_with_no_active_flag_is_rejected(store_db) -> None:
    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    store_db.flush()
    _assert_rejected(
        store_db,
        lambda: insert_version_row(
            store_db, BUSINESS_AUTHORITY, _valid_version(active_flag=None)
        ),
        constraint="active_flag",
    )


@store_covers("B1-08a")
def test_b1_08a_a_version_with_no_published_at_is_rejected(store_db) -> None:
    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    store_db.flush()
    _assert_rejected(
        store_db,
        lambda: insert_version_row(
            store_db, BUSINESS_AUTHORITY, _valid_version(published_at=None)
        ),
        constraint="published_at",
    )


@store_covers("B1-08b")
def test_b1_08b_a_retraction_with_no_retracted_at_is_rejected(store_db) -> None:
    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    store_db.flush()
    _assert_rejected(
        store_db,
        lambda: insert_retraction_row(
            store_db, BUSINESS_AUTHORITY, _valid_retraction(retracted_at=None)
        ),
        constraint="retracted_at",
    )


@store_covers("B1-09a")
def test_b1_09a_an_absent_publication_reference_type_is_rejected(store_db) -> None:
    """ABSENCE IS NOT UNKNOWN-VALUE. This is the shape B1-10 does NOT cover:
    a schema (or a kernel) that only checks membership in the two defined
    values passes B1-10 and fails this one."""

    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    store_db.flush()
    _assert_rejected(
        store_db,
        lambda: insert_version_row(
            store_db, BUSINESS_AUTHORITY, _valid_version(publication_reference_type=None)
        ),
        constraint="publication_reference_type",
    )


@store_covers("B1-09b")
def test_b1_09b_an_absent_publication_reference_id_is_rejected(store_db) -> None:
    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    store_db.flush()
    _assert_rejected(
        store_db,
        lambda: insert_version_row(
            store_db, BUSINESS_AUTHORITY, _valid_version(publication_reference_id=None)
        ),
        constraint="publication_reference_id",
    )


@store_covers("B1-10")
def test_b1_10_a_publication_reference_type_outside_the_two_values_is_rejected(
    store_db,
) -> None:
    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    store_db.flush()
    _assert_rejected(
        store_db,
        lambda: insert_version_row(
            store_db,
            BUSINESS_AUTHORITY,
            _valid_version(publication_reference_type="SOME_FUTURE_PROVENANCE"),
        ),
        constraint="ck_ba_authority_publication_reference_type",
    )


@store_covers()
def test_every_family_carries_the_same_provenance_and_interval_constraints(store_db) -> None:
    """The B1 cases above are proved on one representative family; this proves
    the same constraints exist on all four, so no family is quietly laxer."""

    for family in (
        BUSINESS_AUTHORITY,
        BUSINESS_AUTHORITY_ROLE,
        BUSINESS_AUTHORITY_RULE,
        BUSINESS_AUTHORITY_ASSIGNMENT,
    ):
        tables = FAMILY_TABLES[family]
        for table in (tables.version, tables.retraction):
            checks = {
                name
                for (kind, name) in EXPECTED_CONSTRAINTS[table]
                if kind == "c" and "publication_reference_type" in name
            }
            assert len(checks) == 1, table
        interval = {
            name
            for (kind, name) in EXPECTED_CONSTRAINTS[tables.version]
            if kind == "c" and name.endswith("_version_interval")
        }
        assert len(interval) == 1, tables.version


# ===========================================================================
# STORAGE INTEGRITY - CLASS B2 STRUCTURAL REJECTION (three fixtures)
# ===========================================================================
# These have NO provider-neutral counterpart and none may be fabricated: the
# E2-A contract carries `object_id` on the LineageMaterial CONTAINER, so a
# version or retraction cannot be orphaned at that boundary, and a reference
# to a stable identity ROW that does not exist decodes onto class A fixture
# A-11. What these foreign keys protect is this store's own parent/child
# representation - a real invariant, but not a semantic rule of E2-A.


@store_covers("B2-01")
def test_b2_01_a_version_row_with_no_stable_identity_parent_is_rejected(store_db) -> None:
    _assert_rejected(
        store_db,
        lambda: insert_version_row(
            store_db, BUSINESS_AUTHORITY, _valid_version(object_id="never-published")
        ),
        constraint="fk_ba_authority_version_object_id",
    )


@store_covers("B2-02")
def test_b2_02_a_retraction_row_with_no_object_parent_is_rejected(store_db) -> None:
    _assert_rejected(
        store_db,
        lambda: insert_retraction_row(
            store_db, BUSINESS_AUTHORITY, _valid_retraction(object_id="never-published")
        ),
        constraint="fk_ba_authority_retraction_object_id",
    )


@store_covers("B2-03")
def test_b2_03_a_rule_referencing_a_non_existent_stable_identity_is_rejected(
    store_db,
) -> None:
    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    insert_stable_identity(store_db, BUSINESS_AUTHORITY_RULE, RULE_ID)
    store_db.flush()

    values = _valid_version(object_id=RULE_ID)
    values.update(
        {
            "business_authority_role_object_id": "role-that-has-no-row",
            "business_authority_object_id": AUTHORITY_ID,
            "scope_type": "GLOBAL",
            "scope_id": None,
            "parameter_evaluator_type": "NONE",
            "parameter_payload": None,
        }
    )
    _assert_rejected(
        store_db,
        lambda: insert_version_row(store_db, BUSINESS_AUTHORITY_RULE, values),
        constraint="fk_ba_rule_version_role_reference",
    )


@store_covers("B2-03", "A-11")
def test_the_stable_identity_foreign_key_is_not_extended_into_class_a_territory(
    store_db,
) -> None:
    """THE DISTINCTION THE WHOLE B2 CLASSIFICATION DEPENDS ON.

    The foreign key rejects a reference to a stable identity ROW that does not
    exist at all. It must NOT be extended to reject a reference to a stable
    identity row that EXISTS but carries NO version rows - that state IS class
    A fixture A-11 (AUTHORITY_REFERENCE_DANGLING) and must remain storable and
    parity-tested. Extending the key would silently swallow a class A fixture.
    """

    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    insert_stable_identity(store_db, BUSINESS_AUTHORITY_ROLE, ROLE_ID)
    insert_stable_identity(store_db, BUSINESS_AUTHORITY_RULE, RULE_ID)

    values = _valid_version(object_id=RULE_ID)
    values.update(
        {
            "business_authority_role_object_id": ROLE_ID,  # exists, and has NO versions
            "business_authority_object_id": AUTHORITY_ID,
            "scope_type": "GLOBAL",
            "scope_id": None,
            "parameter_evaluator_type": "NONE",
            "parameter_payload": None,
        }
    )
    insert_version_row(store_db, BUSINESS_AUTHORITY_RULE, values)
    store_db.commit()

    assert len(_rows(store_db, FAMILY_TABLES[BUSINESS_AUTHORITY_RULE].version)) == 1
    assert _rows(store_db, FAMILY_TABLES[BUSINESS_AUTHORITY_ROLE].version) == []


# ===========================================================================
# STORAGE INTEGRITY - CLASS A STORABILITY (the store must NOT reject these)
# ===========================================================================


@store_covers("A-02", "V-01", "V-02", "V-03")
def test_all_five_lineage_shapes_of_11_4_are_storable_and_are_not_normalised(
    store_db,
) -> None:
    """The five shapes of E2-A 11.4, of which only TWO are negative fixtures.

    V-01 (null-end successor closure), V-02 (explicit adjacency) and V-03
    (explicit end before the successor, producing a valid gap) are VALID and
    carry no class label. A-01 (contradictory explicit overlap) and A-02
    (duplicate start) are class A. All five must be STORABLE - the kernel, not
    the schema, is what classifies them - and none may be normalised on write
    or on read.

    The read-back is byte-identical, which is the direct probe for attack
    surface 12a: an explicit declared end LATER than the successor's start
    must not have been truncated to that start.
    """

    shapes = {
        "V-01 null-end successor closure": ((V1, T0, None), (V2, T2, None)),
        "V-02 explicit adjacency": ((V1, T0, T2), (V2, T2, None)),
        "V-03 explicit end before successor (valid gap)": ((V1, T0, T1), (V2, T3, None)),
        "A-01 contradictory explicit overlap": ((V1, T0, T3), (V2, T2, None)),
        "A-02 duplicate temporal start": ((V1, T0, None), (V2, T0, None)),
    }

    for label, pair in shapes.items():
        object_id = f"authority-{abs(hash(label)) % 100000}"
        insert_stable_identity(store_db, BUSINESS_AUTHORITY, object_id)
        for object_version, effective_from, declared_end in pair:
            insert_version_row(
                store_db,
                BUSINESS_AUTHORITY,
                _valid_version(
                    object_id=object_id,
                    object_version=object_version,
                    effective_from=effective_from,
                    declared_effective_to=declared_end,
                    authority_code="CREDIT_ASSESSOR",
                ),
            )
        store_db.commit()

        stored = {
            row["object_version"]: (row["effective_from"], row["declared_effective_to"])
            for row in _rows(
                store_db, FAMILY_TABLES[BUSINESS_AUTHORITY].version, object_id=object_id
            )
        }
        assert len(stored) == 2, label
        for object_version, effective_from, declared_end in pair:
            assert stored[object_version] == (effective_from, declared_end), label


@store_covers("A-04", "A-05")
def test_a_dangling_and_a_duplicated_retraction_are_both_storable(store_db) -> None:
    """Enforcing either structurally would suppress a defect class the kernel
    owns - the same mistake as a retraction-excluding EXISTS in discovery,
    in a different place."""

    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    insert_version_row(store_db, BUSINESS_AUTHORITY, _valid_version())
    # A-04: targets a version that does not exist.
    insert_retraction_row(
        store_db, BUSINESS_AUTHORITY, _valid_retraction(retraction_id="r0", object_version="9999")
    )
    # A-05: two assertions for ONE (object_id, object_version).
    insert_retraction_row(store_db, BUSINESS_AUTHORITY, _valid_retraction(retraction_id="r1"))
    insert_retraction_row(store_db, BUSINESS_AUTHORITY, _valid_retraction(retraction_id="r2"))
    store_db.commit()

    stored = _rows(store_db, FAMILY_TABLES[BUSINESS_AUTHORITY].retraction)
    assert len(stored) == 3
    assert {row["retraction_id"] for row in stored} == {"r0", "r1", "r2"}


@store_covers("A-06", "A-07")
def test_a_correcting_version_with_a_missing_or_unretracted_target_is_storable(
    store_db,
) -> None:
    """There is deliberately no foreign key and no CHECK on
    `corrects_object_version` - both shapes are class A."""

    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    insert_version_row(store_db, BUSINESS_AUTHORITY, _valid_version(object_version=V1))
    # A-06: the target exists but was never retracted.
    insert_version_row(
        store_db,
        BUSINESS_AUTHORITY,
        _valid_version(object_version=V2, effective_from=T2, corrects_object_version=V1),
    )
    # A-07: the target does not exist at all.
    insert_version_row(
        store_db,
        BUSINESS_AUTHORITY,
        _valid_version(object_version="0003", effective_from=T3, corrects_object_version="9999"),
    )
    store_db.commit()

    stored = {
        row["object_version"]: row["corrects_object_version"]
        for row in _rows(store_db, FAMILY_TABLES[BUSINESS_AUTHORITY].version)
    }
    assert stored == {V1: None, V2: V1, "0003": "9999"}


@store_covers("A-08", "A-09", "A-10")
def test_impossible_recorded_provenance_is_storable_and_never_rewritten(store_db) -> None:
    """A CROSS-ROW recorded-timestamp constraint would REJECT the write and so
    prevent the kernel from ever being proved to fail closed on it. Only the
    single-row NOT NULL / timezone-aware conditions are enforced."""

    earlier = RECORDED_AT - timedelta(hours=1)
    later = RECORDED_AT + timedelta(hours=2)

    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    insert_version_row(store_db, BUSINESS_AUTHORITY, _valid_version(object_version=V1))
    # A-10: published_at DECREASES across increasing object_version.
    insert_version_row(
        store_db,
        BUSINESS_AUTHORITY,
        _valid_version(object_version=V2, effective_from=T2, published_at=earlier),
    )
    # A-08: retracted_at precedes its target's published_at.
    insert_retraction_row(
        store_db, BUSINESS_AUTHORITY, _valid_retraction(retracted_at=earlier)
    )
    # A-09 material: a retraction recorded AFTER the correction that cites it.
    insert_retraction_row(
        store_db,
        BUSINESS_AUTHORITY,
        _valid_retraction(retraction_id="r2", object_version=V2, retracted_at=later),
    )
    store_db.commit()

    published = {
        row["object_version"]: row["published_at"]
        for row in _rows(store_db, FAMILY_TABLES[BUSINESS_AUTHORITY].version)
    }
    assert published == {V1: RECORDED_AT, V2: earlier}, "published_at was rewritten"
    retracted = {
        row["retraction_id"]: row["retracted_at"]
        for row in _rows(store_db, FAMILY_TABLES[BUSINESS_AUTHORITY].retraction)
    }
    assert retracted == {"r1": earlier, "r2": later}, "retracted_at was rewritten"


@store_covers("A-13", "A-14", "A-15")
def test_unknown_evaluator_malformed_payload_and_unsupported_scope_are_storable(
    store_db,
) -> None:
    """No closed enum, no lookup foreign key and no per-type payload schema
    check on `parameter_evaluator_type`, `scope_type` or `parameter_payload`.
    A database-side vocabulary would make all three fixtures unseedable and
    therefore un-parity-testable."""

    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    insert_stable_identity(store_db, BUSINESS_AUTHORITY_ROLE, ROLE_ID)
    insert_stable_identity(store_db, BUSINESS_AUTHORITY_RULE, RULE_ID)

    values = _valid_version(object_id=RULE_ID)
    values.update(
        {
            "business_authority_role_object_id": ROLE_ID,
            "business_authority_object_id": AUTHORITY_ID,
            "scope_type": "REGION_TREE",  # A-15: unsupported scope semantics
            "scope_id": "org-branch",
            "parameter_evaluator_type": "SOME_FUTURE_EVALUATOR",  # A-13
            "parameter_payload": "not-an-object",  # A-14
        }
    )
    insert_version_row(store_db, BUSINESS_AUTHORITY_RULE, values)
    store_db.commit()

    stored = _rows(store_db, FAMILY_TABLES[BUSINESS_AUTHORITY_RULE].version)[0]
    assert stored["scope_type"] == "REGION_TREE"
    assert stored["parameter_evaluator_type"] == "SOME_FUTURE_EVALUATOR"
    assert stored["parameter_payload"] == "not-an-object"


@store_covers()
def test_no_uniqueness_or_exclusion_constraint_exists_on_object_id_and_effective_from(
    store_db,
) -> None:
    """Temporal start is deliberately NOT a structural identity key.

    Duplicate-start classification and its parity are required (fixture A-02),
    so a unique constraint, partial index, exclusion constraint or trigger on
    (object_id, effective_from) is forbidden. The immutable
    (object_id, object_version) key above is a DIFFERENT thing and remains
    mandatory; do not reason from one to the other.
    """

    definitions = (
        store_db.execute(
            text(
                "SELECT indexdef FROM pg_indexes WHERE tablename = ANY(:tables)"
            ),
            {"tables": list(ALL_STORE_TABLES)},
        )
        .scalars()
        .all()
    )
    for definition in definitions:
        assert "effective_from" not in definition, definition

    exclusions = (
        store_db.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE contype = 'x' AND conrelid::regclass::text = ANY(:tables)"
            ),
            {"tables": list(ALL_STORE_TABLES)},
        )
        .scalars()
        .all()
    )
    assert exclusions == []

    triggers = (
        store_db.execute(
            text(
                "SELECT tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE NOT t.tgisinternal AND c.relname = ANY(:tables)"
            ),
            {"tables": list(ALL_STORE_TABLES)},
        )
        .scalars()
        .all()
    )
    assert triggers == []


@store_covers()
def test_a_jsonb_payload_round_trips_exactly(store_db) -> None:
    """Nested structures and numeric precision survive unchanged.

    `Decimal` is deliberately NOT among these: it is not a JSON value, so it
    is not a supported PUBLISHED payload representation in this store. E2-A's
    evaluator accepts a `Decimal` from the REQUEST context, which this package
    never persists.
    """

    payload = {
        "fact": "offer_value",
        "unit": "INR",
        "bounds": {"lower": 0.1, "upper": 12345678901234567890, "steps": [1, 2.5, -3]},
        "flags": {"lower_inclusive": True, "upper_inclusive": False},
        "note": None,
        "unicode": "₹ lakh",
    }

    insert_stable_identity(store_db, BUSINESS_AUTHORITY, AUTHORITY_ID)
    insert_stable_identity(store_db, BUSINESS_AUTHORITY_ROLE, ROLE_ID)
    insert_stable_identity(store_db, BUSINESS_AUTHORITY_RULE, RULE_ID)
    values = _valid_version(object_id=RULE_ID)
    values.update(
        {
            "business_authority_role_object_id": ROLE_ID,
            "business_authority_object_id": AUTHORITY_ID,
            "scope_type": "GLOBAL",
            "scope_id": None,
            "parameter_evaluator_type": "NUMERIC_BAND",
            "parameter_payload": payload,
        }
    )
    insert_version_row(store_db, BUSINESS_AUTHORITY_RULE, values)
    store_db.commit()

    stored = _rows(store_db, FAMILY_TABLES[BUSINESS_AUTHORITY_RULE].version)[0]
    assert stored["parameter_payload"] == payload


@store_covers()
def test_no_code_path_in_the_package_writes_published_authority_configuration() -> None:
    """Acceptance criterion R, and attack surface 1 and 6.

    Published version rows and retraction rows are append-only, and there is
    no production mutation surface for authority configuration at all: no
    INSERT, no UPDATE, no DELETE, no publish, no deactivate and no retract in
    the repository, the provider or the composition seam.
    """

    for module in (repository, postgres_provider, production_composition):
        # Docstrings and comments are stripped first: these modules DESCRIBE
        # the forbidden statements at length, deliberately, so a raw substring
        # scan would find the prose rather than the code.
        body = executable_source(module).upper()
        for forbidden in ("INSERT INTO", "UPDATE ", "DELETE FROM", "TRUNCATE ", "MERGE INTO"):
            assert forbidden not in body, (
                f"{module.__name__} appears to contain a {forbidden.strip()} statement"
            )

    # The stronger, structural half: neither the repository nor the provider
    # exposes any callable whose name suggests a write.
    for module in (repository, postgres_provider):
        for name in dir(module):
            assert not any(
                name.startswith(prefix)
                for prefix in ("insert_", "update_", "delete_", "publish_", "retract_", "save_")
            ), f"{module.__name__}.{name} looks like a write path"


@store_covers()
def test_the_seeded_scenario_world_stores_and_reads_back_unchanged(store_db) -> None:
    """The positive control for the whole seeding harness: a valid four-object
    world round-trips, so a later failure is a real divergence rather than a
    broken fixture."""

    seed_materials(store_db, world())
    counts = count_store_rows(store_db)
    assert counts["authz_business_authority_version"] == 1
    assert counts["authz_business_authority_role_version"] == 1
    assert counts["authz_business_authority_rule_version"] == 1
    assert counts["authz_business_authority_assignment_version"] == 1
    assert sum(
        counts[table] for table in counts if table.endswith("_retraction")
    ) == 0


@store_covers()
def test_a_seeded_object_carrying_every_kind_of_version_stores_all_of_them(
    store_db,
) -> None:
    """Retracted, inactive, future-dated and superseded versions all persist.

    A store that dropped any of them would silently re-open a deactivated
    object or hide the very lineage the kernel needs.
    """

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T2, payload=authority_payload(), active_flag=False),
            version("0003", T3, payload=authority_payload()),
        ),
        retractions=(retraction("r1", V1),),
    )
    seed_materials(store_db, world(authority=authority))

    stored = _rows(
        store_db, FAMILY_TABLES[BUSINESS_AUTHORITY].version, object_id=AUTHORITY_ID
    )
    assert {row["object_version"] for row in stored} == {V1, V2, "0003"}
    assert {row["active_flag"] for row in stored} == {True, False}
    assert (
        len(_rows(store_db, FAMILY_TABLES[BUSINESS_AUTHORITY].retraction)) == 1
    ), "the retracted version's assertion was dropped"
    assert len(stored) == 3, "a retracted or inactive version was dropped on write"
