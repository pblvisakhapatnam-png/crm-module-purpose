"""Governed-lifecycle persistence, and THE ONE governed writer (PF-1A-E3).

WHY THE GOVERNED WRITER LIVES HERE AND NOT IN THE PF-1A-E2-B REPOSITORY. That module states,
in terms, that it has no write path and that none may be added, because resolving published
authority and changing who holds it are distinct security problems. Adding an INSERT there
would put the write surface behind the same import every read consumer already has. It lives
here instead, reachable only through the governed activation transaction.

WHAT THIS MODULE READS, AND WHAT IT REFUSES TO DECIDE. It LOCATES rows. It does not decide
effectiveness, closure, retraction validity, correction precedence, overlap, ranking, scope or
evaluator semantics; those remain the PF-1A-E2-A kernel's.

Every table name reaches the SQL text from a CLOSED registry and every caller-controlled value
is a bound parameter.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.modules.authorization.business_authority.configuration_contract import (
    CHANGE_PAYLOAD_FIELDS,
    CONFIGURATION_CHANGE_TABLE,
    CONFIGURATION_EVALUATION_TABLE,
    OBJECT_FAMILIES,
    PUBLICATION_REFERENCE_TYPE,
)
from app.modules.authorization.business_authority.configuration_domain import (
    AllocationAnchor,
    ConfigurationGovernanceError,
    PublishedRow,
    RetractionRow,
)
from app.modules.authorization.business_authority.store_contract import (
    BA_AUTHORITY_VERSION_TABLE,
    FAMILY_TABLES,
)

# The generic per-version columns the governed writer supplies, in one place so a schema change
# cannot silently leave one unset.
_GENERIC_VERSION_COLUMNS = (
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

_JSONB_BINDS = (
    "change_payload",
    "proposal_context_snapshot",
    "context_reference",
    "risk_derivation",
    "parameter_payload",
)


def _tables(object_family: str):
    tables = FAMILY_TABLES.get(object_family)
    if tables is None:
        raise ConfigurationGovernanceError(f"unknown object family: {object_family!r}")
    return tables


def _statement(sql: str, values: Mapping[str, Any]):
    statement = text(sql)
    names = [name for name in _JSONB_BINDS if name in values]
    if names:
        statement = statement.bindparams(*[bindparam(name, type_=JSONB) for name in names])
    return statement


# The discriminator values of the one per-family lineage statement. Integers rather than words,
# so the ORDER BY separates the two shapes without depending on how a collation sorts two labels.
_VERSION_ROW_KIND = 0
_RETRACTION_ROW_KIND = 1


def _text(value: Any) -> str | None:
    return None if value is None else str(value)


def load_published_material(db: Session) -> tuple[
    tuple[PublishedRow, ...], tuple[RetractionRow, ...]
]:
    """Every published version AND every retraction assertion, per family in ONE statement.

    Retracted, inactive, future-dated and superseded rows are all returned, and every retraction
    is returned as a FACT rather than applied as a filter. Filtering any of them out here would
    be the provider-side judgement the kernel's contract prohibits, and the semantics that decide
    which version is effective, which is the authoritative predecessor, and whether a retraction
    is even valid genuinely need the rows a naive filter would drop.

    ONE SNAPSHOT PER FAMILY, for the reason PF-1A-E2-B's `load_lineage` gives. Under PostgreSQL
    READ COMMITTED a snapshot is taken per STATEMENT, so reading versions and retractions
    separately could observe two different committed states and assemble a combination that never
    existed - the versions from before a correction together with the retraction from after it.
    Both collections therefore come from one `db.execute` round trip.

    `retracted` is computed from the assertions read in that same statement, so the flag and the
    assertions can never disagree. It records only that an assertion TARGETS the version; whether
    that assertion is VALID remains the kernel's question.
    """

    rows: list[PublishedRow] = []
    assertions: list[RetractionRow] = []
    for family in OBJECT_FAMILIES:
        tables = _tables(family)
        payload_columns = CHANGE_PAYLOAD_FIELDS[family]
        version_payload = ", ".join(f"v.{name}" for name in payload_columns)
        # Left UNTYPED deliberately: PostgreSQL resolves a union column's type from the branch
        # that has one, so each stored column keeps its native type without this module restating
        # a type name it would then have to keep in step with the migration.
        absent_payload = ", ".join(f"NULL AS {name}" for name in payload_columns)
        statement = text(
            f"""
            SELECT {_VERSION_ROW_KIND} AS row_kind, v.id, v.object_id, v.object_version,
                   v.publication_reference_type, v.publication_reference_id,
                   v.active_flag, v.effective_from, v.declared_effective_to,
                   v.corrects_object_version, v.published_at, {version_payload},
                   NULL AS retraction_id, NULL AS retracted_at
            FROM {tables.version} v
            UNION ALL
            SELECT {_RETRACTION_ROW_KIND} AS row_kind, r.id, r.object_id, r.object_version,
                   r.publication_reference_type, r.publication_reference_id,
                   NULL AS active_flag, NULL AS effective_from, NULL AS declared_effective_to,
                   NULL AS corrects_object_version, NULL AS published_at, {absent_payload},
                   r.retraction_id, r.retracted_at
            FROM {tables.retraction} r
            ORDER BY row_kind, object_id, id
            """
        )
        records = db.execute(statement).mappings().all()

        retraction_records = [
            record for record in records if record["row_kind"] == _RETRACTION_ROW_KIND
        ]
        targeted = {
            (_text(record["object_id"]), _text(record["object_version"]))
            for record in retraction_records
        }

        for record in records:
            if record["row_kind"] != _VERSION_ROW_KIND:
                continue
            object_id = str(record["object_id"])
            object_version = str(record["object_version"])
            rows.append(
                PublishedRow(
                    object_family=family,
                    object_id=object_id,
                    object_version=object_version,
                    active_flag=record["active_flag"],
                    retracted=(object_id, object_version) in targeted,
                    effective_from=record["effective_from"],
                    declared_effective_to=record["declared_effective_to"],
                    payload={name: record[name] for name in payload_columns},
                    corrects_object_version=_text(record["corrects_object_version"]),
                    publication_reference_type=_text(record["publication_reference_type"]),
                    publication_reference_id=_text(record["publication_reference_id"]),
                    published_at=record["published_at"],
                )
            )

        for record in retraction_records:
            assertions.append(
                RetractionRow(
                    object_family=family,
                    object_id=str(record["object_id"]),
                    object_version=_text(record["object_version"]),
                    retraction_id=_text(record["retraction_id"]),
                    retracted_at=record["retracted_at"],
                    publication_reference_type=_text(record["publication_reference_type"]),
                    publication_reference_id=_text(record["publication_reference_id"]),
                )
            )
    return tuple(rows), tuple(assertions)


def load_protected_candidate_codes(db: Session) -> tuple[str, ...]:
    """Authority codes any non-retracted version of which asserts protection.

    A deliberately OVER-INCLUSIVE candidate list. It decides nothing: it only says which
    authority codes are worth asking the unchanged kernel about. The strict question - is the
    authority version that actually granted this person protected right now - is answered by
    dereferencing the exact version the kernel cited, never by this list.
    """

    statement = text(
        f"""
        SELECT DISTINCT v.authority_code
        FROM {BA_AUTHORITY_VERSION_TABLE} v
        WHERE v.is_protected_meta_authority IS TRUE
          AND v.authority_code IS NOT NULL
        ORDER BY v.authority_code
        """
    )
    return tuple(str(value) for value in db.execute(statement).scalars().all())


def stable_identity_exists(db: Session, object_family: str, object_id: str) -> bool:
    tables = _tables(object_family)
    statement = text(f"SELECT COUNT(*) FROM {tables.stable} WHERE object_id = :object_id")
    return int(db.execute(statement, {"object_id": object_id}).scalar_one()) > 0


def ensure_stable_identity(db: Session, object_family: str, object_id: str) -> None:
    """Create the stable identity row for a governed CREATE, exactly once.

    `ON CONFLICT DO NOTHING` is idempotency, not repair: the identity is created by the
    activation that publishes the object's first version, and a retry of that same activation
    must not fail on its own prior effect.
    """

    tables = _tables(object_family)
    db.execute(
        text(
            f"INSERT INTO {tables.stable} (object_id) VALUES (:object_id) "
            "ON CONFLICT (object_id) DO NOTHING"
        ),
        {"object_id": object_id},
    )


def allocation_anchor(db: Session, object_family: str, object_id: str) -> AllocationAnchor:
    """The ALL-TIME lexicographic maximum published identity for one object, and its
    `published_at`.

    THIS IS AN ALLOCATION ANCHOR, NOT AN AUTHORITATIVE PREDECESSOR, and the two must never be
    conflated. It deliberately includes RETRACTED versions, because the unchanged PF-1A-E2 kernel
    validates provenance across EVERY published version of an object, not only the currently
    asserted ones: a newly minted identity must sort after all of them (11.8.3 reads `published_at`
    as non-decreasing in `object_version` order), and a new `published_at` must not precede the one
    already recorded against this anchor. Which version an UPDATE may legitimately supersede is a
    different question, answered from the validated current asserted lineage, where a retracted
    version is not an answer at all however great its spelling.

    THE MAXIMUM IS TAKEN IN PYTHON with `max()` - the same comparison `lineage.py` uses - never by
    a SQL `ORDER BY` over the text column, which would apply the DATABASE COLLATION and let the
    store believe a different identity was greatest from the one the kernel does.

    Comparing whole opaque strings is not parsing them. A version reading "v1", a UUID, or
    anything else its publisher chose is compared exactly as stored, and any implementation that
    reduced this question to "the highest number" would make every one of them unmanageable.

    Called only inside the governed activation transaction, after the governance-wide publication
    boundary is held, so the answer cannot be superseded between reading it and publishing.
    """

    tables = _tables(object_family)
    statement = text(
        f"SELECT v.object_version, v.published_at FROM {tables.version} v "
        "WHERE v.object_id = :object_id ORDER BY v.id"
    )
    records = db.execute(statement, {"object_id": object_id}).mappings().all()
    published = [str(record["object_version"]) for record in records]
    if not published:
        return AllocationAnchor()
    anchor = max(published)
    recorded = [
        record["published_at"]
        for record in records
        if str(record["object_version"]) == anchor
    ]
    # The store's (object_id, object_version) uniqueness key makes more than one impossible; an
    # absent recorded time is carried through as None and refused by the caller, never defaulted.
    return AllocationAnchor(
        object_version=anchor, published_at=recorded[0] if recorded else None
    )


# ---------------------------------------------------------------------------
# Publication serialization
# ---------------------------------------------------------------------------
# TWO BOUNDARIES, AND THE WIDER ONE IS THE ONE THAT MATTERS.
#
# A per-object lock serializes two activations of the SAME stable object. It does nothing at all
# for two activations of DIFFERENT stable objects whose governed outcomes nonetheless depend on
# each other - two assignment objects that would duplicate one another, a rule and the authority
# it grants from, an assignment and the role it cites. Under READ COMMITTED each of those pairs
# can validate against a snapshot taken before the other published, and both then publish.
#
# The GOVERNANCE-WIDE boundary below is therefore the primary control: exactly one governed
# activation may be validating and publishing at a time, application-wide. Governed
# configuration administration is a rare, deliberate, low-frequency path, so serializing it
# whole costs nothing worth protecting.
#
# WHAT THIS BOUNDARY DOES NOT DO. It serializes activations against THIS application's database.
# It does not - and must not be described as - serializing any external HR/organisation or
# actor-person system, whose state this package only ever reads through the authoritative
# providers. That remains handled by failing closed: the production composition refuses to
# compose while those providers are absent, and an unresolvable dependency refuses the governed
# action outright.

GOVERNANCE_PUBLICATION_LOCK_KEY = "pf-1a-e3:governance-publication"


def _lock_key(object_family: str, object_id: str) -> str:
    return f"pf-1a-e3:{object_family}:{object_id}"


def try_lock_governance_publication(db: Session) -> bool:
    """Take THE governance-wide, transaction-scoped publication boundary.

    NON-BLOCKING, for the same reason the per-object lock is: a blocking acquisition would make
    a contended activation wait an unbounded time inside an open transaction and would make the
    contention invisible. Refusing immediately is bounded and legible, and the caller may retry.
    Refusing is also strictly safe - it is a refusal to publish, never a permission to.
    """

    statement = text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))")
    return bool(db.execute(statement, {"key": GOVERNANCE_PUBLICATION_LOCK_KEY}).scalar_one())


def lock_governance_publication(db: Session) -> None:
    """Blocking acquisition. Used only to hold the boundary deliberately during verification."""

    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": GOVERNANCE_PUBLICATION_LOCK_KEY},
    )


def try_lock_object(db: Session, object_family: str, object_id: str) -> bool:
    """Take the transaction-scoped publication lock for ONE stable object.

    SECONDARY DEFENCE ONLY, and retained deliberately as such. The governance-wide boundary
    above is what actually serializes governed publication; this narrower lock is kept because
    it names the contended object precisely, which is the more useful thing to see in evidence,
    and because it would still hold if a future package ever introduced a second, narrower
    publication path. It is NOT sufficient on its own: two activations of two different stable
    objects take two different keys and would not exclude one another.

    NON-BLOCKING, for the same reason as the governance-wide boundary.
    """

    statement = text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))")
    return bool(
        db.execute(statement, {"key": _lock_key(object_family, object_id)}).scalar_one()
    )


def lock_object(db: Session, object_family: str, object_id: str) -> None:
    """Blocking acquisition. Used only to hold the lock deliberately during verification."""

    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": _lock_key(object_family, object_id)},
    )


def insert_published_version(db: Session, version: PublishedRow) -> None:
    """Publish ONE immutable version, EXACTLY as `version` states it.

    This is the ONLY production write into the published Business Authority store in the whole
    application. It appends; it never updates and never deletes.

    IT TAKES THE WHOLE ROW, AND THAT IS THE POINT. The caller must validate the prospective
    lineage - the object's complete existing material plus the version about to be appended -
    through the unchanged PF-1A-E2-A kernel before publishing. If this function reassembled the
    row from loose arguments, the row that was VALIDATED and the row that is WRITTEN would be two
    constructions that merely agree today, and any later divergence between them would publish
    something no kernel ever approved. Passing one immutable object through both makes them the
    same row by construction.

    TWO VALUES ARE STILL REFUSED HERE RATHER THAN TRUSTED. `corrects_object_version` must be
    absent, because PF-1A-E3 implements publication and deactivation, not correction or retraction:
    asserting a correction would create a lineage claim the governed lifecycle has no authorization
    path for. `publication_reference_type` must be the CONFIGURATION_CHANGE provenance, because
    this writer is that provenance and must never be able to mint the bootstrap one. Both are
    structural refusals, not silent overwrites - rewriting a caller's value into a conforming one
    is how the validated row and the stored row come apart.
    """

    if version.corrects_object_version is not None:
        raise ConfigurationGovernanceError(
            "PF-1A-E3 publishes and deactivates; it never asserts a correction"
        )
    if version.publication_reference_type != PUBLICATION_REFERENCE_TYPE:
        raise ConfigurationGovernanceError(
            "a governed publication must carry the CONFIGURATION_CHANGE provenance, not "
            f"{version.publication_reference_type!r}"
        )
    if not version.publication_reference_id:
        raise ConfigurationGovernanceError(
            "a governed publication must name the Configuration Change that produced it"
        )

    tables = _tables(version.object_family)
    payload_columns = CHANGE_PAYLOAD_FIELDS[version.object_family]

    values: dict[str, Any] = {
        "object_id": version.object_id,
        "object_version": version.object_version,
        "effective_from": version.effective_from,
        "declared_effective_to": version.declared_effective_to,
        "active_flag": version.active_flag,
        "corrects_object_version": version.corrects_object_version,
        "publication_reference_type": version.publication_reference_type,
        "publication_reference_id": version.publication_reference_id,
        "published_at": version.published_at,
    }
    for name in payload_columns:
        values[name] = version.payload.get(name)

    columns = list(_GENERIC_VERSION_COLUMNS) + list(payload_columns)
    binds = ", ".join(f":{name}" for name in columns)
    db.execute(
        _statement(
            f"INSERT INTO {tables.version} ({', '.join(columns)}) VALUES ({binds})", values
        ),
        values,
    )


_CHANGE_COLUMNS = (
    "configuration_change_id",
    "configuration_object_family",
    "configuration_object_id",
    "change_type",
    "change_payload",
    "proposed_active_flag",
    "effective_from",
    "declared_effective_to",
    "previous_object_version_expected",
    "proposal_time_is_self_affecting",
    "proposal_time_affects_protected_meta_authority",
    "proposal_time_privilege_increasing",
    "proposal_time_authorization_required",
    "proposal_context_snapshot",
    "proposal_dependency_fingerprint",
    "initiated_by_person_id",
    "initiated_by_actor_user_public_id",
    "initiated_at",
    "lifecycle_status",
)

_EVALUATION_COLUMNS = (
    "evaluation_id",
    "configuration_change_id",
    "evaluation_stage",
    "evaluated_at",
    "acting_person_id",
    "acting_actor_user_public_id",
    "recomputed_is_self_affecting",
    "recomputed_affects_protected_meta_authority",
    "recomputed_privilege_increasing",
    "recomputed_authorization_required",
    "authorizer_eligible",
    "authorizer_is_different_person",
    "dependencies_current",
    "authorization_satisfied",
    "outcome",
    "refusal_reason",
    "dependency_fingerprint",
    "context_reference",
    "risk_derivation",
)


def insert_change(db: Session, values: Mapping[str, Any]) -> None:
    missing = [name for name in _CHANGE_COLUMNS if name not in values]
    if missing:
        raise ConfigurationGovernanceError(
            f"a Configuration Change is missing required fields: {sorted(missing)}"
        )
    payload = {name: values[name] for name in _CHANGE_COLUMNS}
    binds = ", ".join(f":{name}" for name in _CHANGE_COLUMNS)
    db.execute(
        _statement(
            f"INSERT INTO {CONFIGURATION_CHANGE_TABLE} ({', '.join(_CHANGE_COLUMNS)}) "
            f"VALUES ({binds})",
            payload,
        ),
        payload,
    )


def load_change(
    db: Session, configuration_change_id: str, *, for_update: bool = False
) -> dict[str, Any] | None:
    suffix = " FOR UPDATE" if for_update else ""
    record = (
        db.execute(
            text(
                f"SELECT * FROM {CONFIGURATION_CHANGE_TABLE} "
                "WHERE configuration_change_id = :cid" + suffix
            ),
            {"cid": configuration_change_id},
        )
        .mappings()
        .first()
    )
    return dict(record) if record is not None else None


def record_authorization(
    db: Session,
    configuration_change_id: str,
    *,
    person_id: str,
    actor_id: str,
    at: datetime,
    evaluation_id: str,
) -> None:
    """Record a SUCCESSFUL authorization as ONE self-contained, bound fact.

    The authorizer identity and `authorized_evaluation_id` are written in a SINGLE statement, so
    an authorizer can never exist without the exact successful AUTHORIZATION evaluation that
    established them. Activation loads that bound evaluation and nothing else.

    Called ONLY on a satisfied authorization. A refused attempt records its own evaluation and
    leaves every column below untouched, so a refusal can neither create an authorization nor
    re-point an existing one at its own freshly-recomputed evidence. A LATER successful
    authorization legitimately replaces all four columns together, which is the re-authorization
    path a drifted change must take.
    """

    db.execute(
        text(
            f"UPDATE {CONFIGURATION_CHANGE_TABLE} SET authorized_by_person_id = :person, "
            "authorized_by_actor_user_public_id = :actor, authorized_at = :at, "
            "authorized_evaluation_id = :evaluation "
            "WHERE configuration_change_id = :cid"
        ),
        {
            "person": person_id,
            "actor": actor_id,
            "at": at,
            "evaluation": evaluation_id,
            "cid": configuration_change_id,
        },
    )


def record_rejection(
    db: Session,
    configuration_change_id: str,
    *,
    status: str,
    person_id: str,
    at: datetime,
    reason: str,
) -> None:
    db.execute(
        text(
            f"UPDATE {CONFIGURATION_CHANGE_TABLE} SET lifecycle_status = :status, "
            "rejected_by_person_id = :person, rejected_at = :at, rejection_reason = :reason "
            "WHERE configuration_change_id = :cid"
        ),
        {
            "status": status,
            "person": person_id,
            "at": at,
            "reason": reason,
            "cid": configuration_change_id,
        },
    )


def record_activation(
    db: Session, configuration_change_id: str, *, status: str, version: str, at: datetime
) -> None:
    db.execute(
        text(
            f"UPDATE {CONFIGURATION_CHANGE_TABLE} SET lifecycle_status = :status, "
            "published_object_version = :version, activated_at = :at "
            "WHERE configuration_change_id = :cid"
        ),
        {
            "status": status,
            "version": version,
            "at": at,
            "cid": configuration_change_id,
        },
    )


def insert_evaluation(db: Session, values: Mapping[str, Any]) -> None:
    payload = {name: values.get(name) for name in _EVALUATION_COLUMNS}
    binds = ", ".join(f":{name}" for name in _EVALUATION_COLUMNS)
    db.execute(
        _statement(
            f"INSERT INTO {CONFIGURATION_EVALUATION_TABLE} "
            f"({', '.join(_EVALUATION_COLUMNS)}) VALUES ({binds})",
            payload,
        ),
        payload,
    )


def load_evaluations(
    db: Session, configuration_change_id: str, *, stage: str | None = None
) -> tuple[dict[str, Any], ...]:
    parameters: dict[str, Any] = {"cid": configuration_change_id}
    clause = ""
    if stage is not None:
        parameters["stage"] = stage
        clause = " AND evaluation_stage = :stage"
    return tuple(
        dict(row)
        for row in db.execute(
            text(
                f"SELECT * FROM {CONFIGURATION_EVALUATION_TABLE} "
                "WHERE configuration_change_id = :cid" + clause + " ORDER BY id"
            ),
            parameters,
        )
        .mappings()
        .all()
    )


def latest_evaluation(
    db: Session, configuration_change_id: str, stage: str
) -> dict[str, Any] | None:
    """The most recent evaluation of one stage. AUDIT/INSPECTION ONLY.

    Deliberately NOT how activation finds the authorization it relies on. "Most recent" and "the
    one the recorded authorizer is bound to" are different rows the moment a refused attempt is
    recorded after a successful one; activation uses `load_bound_evaluation`.
    """

    found = load_evaluations(db, configuration_change_id, stage=stage)
    return found[-1] if found else None


def load_bound_evaluation(
    db: Session, configuration_change_id: str, evaluation_id: str
) -> dict[str, Any] | None:
    """ONE evaluation, by its own identity AND its owning change. Both, always.

    Scoping the lookup by `configuration_change_id` as well as `evaluation_id` is what makes it
    structurally impossible for one change's authorization evidence to be satisfied by another
    change's evaluation, however the binding column came to hold that value.
    """

    record = (
        db.execute(
            text(
                f"SELECT * FROM {CONFIGURATION_EVALUATION_TABLE} "
                "WHERE configuration_change_id = :cid AND evaluation_id = :eid"
            ),
            {"cid": configuration_change_id, "eid": evaluation_id},
        )
        .mappings()
        .first()
    )
    return dict(record) if record is not None else None


def governed_state_counts(db: Session) -> dict[str, int]:
    """How much governed and governed-published state currently exists."""

    counts = {
        table: int(db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
        for table in (CONFIGURATION_CHANGE_TABLE, CONFIGURATION_EVALUATION_TABLE)
    }
    published = 0
    for family in OBJECT_FAMILIES:
        published += int(
            db.execute(
                text(
                    f"SELECT COUNT(*) FROM {_tables(family).version} "
                    "WHERE publication_reference_type = :provenance"
                ),
                {"provenance": PUBLICATION_REFERENCE_TYPE},
            ).scalar_one()
        )
    counts["published_configuration_change_versions"] = published
    return counts
