"""READ-ONLY PostgreSQL access to the published Business Authority store.

PF-1A-E2-B section 5.2.

    LOCATING a fact is permitted; JUDGING a fact is not (E2-A 9.5).

Every function here LOCATES rows. None of them decides effectiveness,
closure, activity, retraction validity, correction precedence, overlap,
ranking, scope qualification, evaluator semantics, temporal closure or
"latest version". Those are the E2-A kernel's, and a second implementation
here would be a blocking defect even while it agreed, because two copies
drift.

THREE DISCIPLINES THIS MODULE ENFORCES ON ITSELF

    RAW DISCOVERY (9.3.1, F-07). A discovery WHERE clause may reference ONLY
        the structurally trustworthy locating columns: the object family
        (through the table registry), the stable identity column, the
        `authority_code` column and the stable reference columns. There is
        deliberately NO `NOT EXISTS` over a retraction table, no effective-time
        predicate, no `active_flag` predicate, no scope, parameter, provenance
        or "latest version" predicate. Each excluded fact can ITSELF be the
        defect the kernel must detect, so being a superset is a CORRECTNESS
        requirement rather than a performance concession.

    COMPLETENESS OR NOTHING (9.3.2). A short read is never presented as
        complete. Every list query carries `COUNT(*) OVER ()` and the row
        count is checked against it, so a truncated result is detected and
        reported as UNAVAILABLE rather than silently resolved. A read error or
        a timeout raises `AuthorityConfigurationPortError`, which the kernel
        maps to AUTHORITY_CONFIGURATION_UNAVAILABLE - never an empty result
        and never DENY + RESOLVED.

    NO ARBITRARY ROW SELECTION (5.2). No `first()`, no `LIMIT 1`, no
        `scalar()` and no `DISTINCT ON` is used anywhere multiplicity or
        ambiguity could matter. The repository returns everything it found and
        the kernel fails closed on multiplicity; hiding ambiguity by selecting
        one row is a blocking defect.

    ONE SNAPSHOT PER LINEAGE READ (9.3.2, independent review finding F1).
        Versions and retraction assertions are read by ONE statement, so
        PostgreSQL's own single-statement snapshot is the consistency
        boundary. Two separate reads under READ COMMITTED can observe two
        different committed states, which would let a publication committing
        between them produce a combination that never existed while the
        provider still labelled it COMPLETE. See `load_lineage`.

THERE IS NO WRITE PATH. This module exposes no INSERT, UPDATE, DELETE,
publish, deactivate or retract operation, and none may be added: governed
change belongs to PF-1A-E3 (acceptance criterion R). Deterministic test
fixtures write their own rows directly and live under `backend/tests/`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.authorization.business_authority.ports import (
    AuthorityConfigurationPortError,
)
from app.modules.authorization.business_authority.store_contract import (
    BA_ASSIGNMENT_VERSION_TABLE,
    BA_AUTHORITY_VERSION_TABLE,
    BA_RULE_VERSION_TABLE,
    FAMILY_TABLES,
)

# Every version table's provider-neutral columns, in one canonical order so a
# reader can see at a glance that nothing family-specific leaks into the
# generic lineage query.
_VERSION_COLUMNS = (
    "object_id",
    "object_version",
    "effective_from",
    "declared_effective_to",
    "active_flag",
    "corrects_object_version",
    "publication_reference_type",
    "publication_reference_id",
    "published_at",
)

_RETRACTION_COLUMNS = (
    "object_id",
    "retraction_id",
    "object_version",
    "retracted_at",
    "publication_reference_type",
    "publication_reference_id",
)

# The one lineage read is a single statement over BOTH physical tables, so it
# needs the two column sets decomposed into what they SHARE and what each
# owns alone. Derived from the two tuples above rather than restated, so a
# column added there cannot be forgotten here.
_SHARED_LINEAGE_COLUMNS = tuple(
    name for name in _VERSION_COLUMNS if name in _RETRACTION_COLUMNS
)
_VERSION_ONLY_COLUMNS = tuple(
    name for name in _VERSION_COLUMNS if name not in _SHARED_LINEAGE_COLUMNS
)
_RETRACTION_ONLY_COLUMNS = tuple(
    name for name in _RETRACTION_COLUMNS if name not in _SHARED_LINEAGE_COLUMNS
)

# The family-specific payload columns, read alongside the generic ones.
_PAYLOAD_COLUMNS: dict[str, tuple[str, ...]] = {
    "authz_business_authority_version": (
        "authority_code",
        "authority_name",
        "description",
        "is_protected_meta_authority",
    ),
    "authz_business_authority_role_version": ("role_code", "role_name", "description"),
    "authz_business_authority_rule_version": (
        "business_authority_role_object_id",
        "business_authority_object_id",
        "scope_type",
        "scope_id",
        "parameter_evaluator_type",
        "parameter_payload",
    ),
    "authz_business_authority_assignment_version": (
        "business_authority_role_object_id",
        "person_id",
        "position_id",
        "scope_type",
        "scope_id",
    ),
}


class TruncatedReadError(AuthorityConfigurationPortError):
    """The database returned fewer rows than it reported for the same query.

    A truncated list presented as COMPLETE is the blocking defect E2-A 9.3.2
    names, so it is detected here rather than trusted away. It is a subclass
    of the port error, which means the kernel already handles it: the
    resolution fails closed with AUTHORITY_CONFIGURATION_UNAVAILABLE.
    """


def _tables(object_family: str):
    """Resolve a provider-neutral family to its physical tables.

    An unknown family raises rather than being interpolated into SQL. Table
    names reach the query text ONLY from this closed registry; every
    caller-controlled value is a bound parameter (attack surface 25).
    """

    tables = FAMILY_TABLES.get(object_family)
    if tables is None:
        raise AuthorityConfigurationPortError(
            f"unknown object family: {object_family!r}"
        )
    return tables


def _rows(db: Session, statement: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Execute one read and materialise it, refusing to under-report.

    `total_rows` is `COUNT(*) OVER ()` from the same statement, so a result
    that is short of what the database itself reported is caught here instead
    of being handed to the kernel as complete material.
    """

    try:
        result = db.execute(text(statement), params).mappings().all()
    except SQLAlchemyError as error:  # pragma: no cover - exercised via injection
        # The driver's own message is deliberately not propagated into the
        # resolution: the kernel discards provider exception text so evidence
        # stays byte-identical across providers and runtimes (E2-A FU-4).
        raise AuthorityConfigurationPortError(
            "the authority configuration store could not be read"
        ) from error

    rows = [dict(row) for row in result]
    if rows:
        reported = rows[0].get("total_rows")
        if reported is not None and len(rows) != reported:
            raise TruncatedReadError(
                "the authority configuration store returned a truncated result"
            )
    for row in rows:
        row.pop("total_rows", None)
    return rows


# ---------------------------------------------------------------------------
# RAW candidate discovery - stable identities only, deliberately a superset
# ---------------------------------------------------------------------------


def _discover(db: Session, version_table: str, column: str, value: str) -> list[str]:
    """Stable ids of every object ANY raw published version of which matches.

    `column` comes from a closed set of literal names owned by this module,
    never from a caller; `value` is always bound.

    Read the WHERE clause for what is ABSENT: no retraction anti-join, no
    `effective_from <= now`, no `active_flag IS TRUE`, no scope, no evaluator,
    no provenance test and no "latest version" restriction.
    """

    # DISTINCT is applied in the subquery so `COUNT(*) OVER ()` counts the
    # DISTINCT identities rather than the raw matching versions. Computing the
    # window over the un-deduplicated set would make the completeness guard
    # fire spuriously for any object with more than one matching version.
    statement = f"""
        SELECT d.object_id, COUNT(*) OVER () AS total_rows
        FROM (
            SELECT DISTINCT v.object_id
            FROM {version_table} v
            WHERE v.{column} = :value
        ) d
        ORDER BY d.object_id
    """
    return [str(row["object_id"]) for row in _rows(db, statement, {"value": value})]


def find_business_authority_ids_by_code(db: Session, authority_code: str) -> Sequence[str]:
    return _discover(db, BA_AUTHORITY_VERSION_TABLE, "authority_code", authority_code)


def find_rule_ids_for_authority(db: Session, business_authority_id: str) -> Sequence[str]:
    return _discover(
        db, BA_RULE_VERSION_TABLE, "business_authority_object_id", business_authority_id
    )


def find_assignment_ids_for_role(db: Session, business_authority_role_id: str) -> Sequence[str]:
    return _discover(
        db,
        BA_ASSIGNMENT_VERSION_TABLE,
        "business_authority_role_object_id",
        business_authority_role_id,
    )


# ---------------------------------------------------------------------------
# COMPLETE lineage material
# ---------------------------------------------------------------------------


# The discriminator values of the one lineage statement. They are integers,
# not words, so the outer ORDER BY puts every version row before every
# retraction row without depending on how the collation sorts two labels.
_VERSION_ROW_KIND = 0
_RETRACTION_ROW_KIND = 1


def _null_columns(names: Sequence[str]) -> str:
    """`NULL AS <name>` for each column the other branch of the union owns.

    The NULL is deliberately left UNTYPED. PostgreSQL resolves a union
    column's type from the branch that has one, so the stored column keeps
    its NATIVE type - `timestamptz` stays `timestamptz`, `boolean` stays
    `boolean`, `jsonb` stays `jsonb` - without this module restating a type
    name it would then have to keep in step with the migration.
    """

    return ", ".join(f"NULL AS {name}" for name in names)


def load_lineage(
    db: Session, object_family: str, object_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """EVERY published version row and EVERY retraction assertion, in ONE snapshot.

    WHY ONE STATEMENT RATHER THAN TWO READS (independent review finding F1).
    Under PostgreSQL READ COMMITTED a snapshot is taken per STATEMENT, so two
    separate reads can legitimately observe two different committed states. A
    publication that commits between them would then let a caller assemble a
    combination of versions and retractions that never existed together -
    for instance the versions from BEFORE a correction together with the
    retraction from AFTER it - and present it as COMPLETE. That is precisely
    the promise `COMPLETENESS_COMPLETE` makes, so the coherence has to be real
    rather than probable.

    The consistency boundary is therefore PostgreSQL's own single-statement
    snapshot: both collections come from ONE `db.execute` round trip, so they
    are read AS AT one committed state by construction. Nothing here changes
    the isolation level of a caller-owned Session, which would be both wider
    than needed and unsafe on a Session whose transaction has already begun.

    This is a READ-COHERENCE guarantee for one `get_lineage` call. It is not,
    and does not pretend to be, a whole-resolution transaction spanning the
    several provider calls one resolution makes; that remains a later
    (PF-1A-E3) question.

    WHAT IT STILL DOES NOT DO. Splitting the returned rows back into versions
    and retractions by their discriminator is STRUCTURAL DECODING, not
    judgement. Retracted, inactive, future-dated, superseded and corrected
    versions are all returned, every retraction assertion is returned as a
    FACT, nothing is filtered, ranked, coalesced or normalised, and the kernel
    still decides effectiveness, closure, retraction validity and correction
    precedence (11.3).

    The ORDER BY is total and canonical. Within the version rows it degenerates
    to `effective_from, object_version, id` because `retraction_id` is constant
    (NULL) there; within the retraction rows it degenerates to
    `object_version, retraction_id, id` because `effective_from` is constant
    (NULL) there - the same two orders the two reads produced before. The
    kernel re-sorts regardless (9.3.3); this is discipline, not a semantic
    contribution.
    """

    tables = _tables(object_family)
    payload_columns = _PAYLOAD_COLUMNS[tables.version]

    version_only = _VERSION_ONLY_COLUMNS + payload_columns
    retraction_only = _RETRACTION_ONLY_COLUMNS
    shared = _SHARED_LINEAGE_COLUMNS

    # `id` is read purely so the ORDER BY below stays total; it is projected
    # back out of both row shapes, which are exactly the ones the two reads
    # returned before.
    version_branch = ", ".join(f"v.{name}" for name in ("id",) + shared + version_only)
    retraction_branch = ", ".join(f"r.{name}" for name in ("id",) + shared)

    statement = f"""
        SELECT lineage.*, COUNT(*) OVER () AS total_rows
        FROM (
            SELECT {_VERSION_ROW_KIND} AS row_kind, {version_branch},
                   {_null_columns(retraction_only)}
            FROM {tables.version} v
            WHERE v.object_id = :object_id
            UNION ALL
            SELECT {_RETRACTION_ROW_KIND} AS row_kind, {retraction_branch},
                   {_null_columns(version_only)},
                   r.retraction_id, r.retracted_at
            FROM {tables.retraction} r
            WHERE r.object_id = :object_id
        ) lineage
        ORDER BY lineage.row_kind, lineage.effective_from, lineage.object_version,
                 lineage.retraction_id, lineage.id
    """

    version_keys = _VERSION_COLUMNS + payload_columns
    retraction_keys = _RETRACTION_COLUMNS

    versions: list[dict[str, Any]] = []
    retractions: list[dict[str, Any]] = []
    for row in _rows(db, statement, {"object_id": object_id}):
        if row["row_kind"] == _VERSION_ROW_KIND:
            versions.append({name: row[name] for name in version_keys})
        else:
            retractions.append({name: row[name] for name in retraction_keys})
    return versions, retractions


def load_version(
    db: Session, object_family: str, object_id: str, object_version: str
) -> dict[str, Any] | None:
    """The exact immutable stored version, or None if this store holds no such row.

    Dereference is ALWAYS available and never substitutes another version,
    regardless of retraction, correction, supersession, inactivity or
    effectiveness (9.3.2, 11.3).

    The unique (object_id, object_version) key makes at most one row possible,
    so returning a single row here hides no multiplicity. More than one row
    would be a schema violation and is raised rather than silently reduced.
    """

    tables = _tables(object_family)
    columns = ", ".join(
        f"v.{name}" for name in _VERSION_COLUMNS + _PAYLOAD_COLUMNS[tables.version]
    )
    statement = f"""
        SELECT {columns}, COUNT(*) OVER () AS total_rows
        FROM {tables.version} v
        WHERE v.object_id = :object_id AND v.object_version = :object_version
        ORDER BY v.id
    """
    rows = _rows(db, statement, {"object_id": object_id, "object_version": object_version})
    if not rows:
        return None
    if len(rows) > 1:
        raise AuthorityConfigurationPortError(
            "more than one stored row shares one (object_id, object_version) identity"
        )
    return rows[0]
