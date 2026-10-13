"""PF-1A-E3 synthetic bootstrap context and providers. TEST-ONLY.

READ THIS BEFORE READING ANYTHING ELSE IN THIS FILE.

Everything below is a DETERMINISTIC TEST FIXTURE. It establishes synthetic actors, synthetic
persons and synthetic published authority configuration so the governed lifecycle has something
to operate against. It is:

    NOT a production bootstrap;
    NOT an answer to open question Q-10 (who first holds the protected meta-authority in the
        real deployment, and how a later change of that holder is itself authorized);
    NOT evidence that any real holder has been chosen.

It lives under the backend test tree deliberately, so production unreachability is STRUCTURAL,
and the PF-1A-E3 production composition seam refuses to compose rather than substituting any of
these providers.

WHY THE BOOTSTRAP WRITES THE PUBLISHED STORE DIRECTLY. The governed lifecycle cannot bootstrap
itself: proposing a configuration change requires already holding a protected meta-authority,
and before any configuration exists nobody holds anything. The fixture therefore writes its
initial synthetic state directly, under BOOTSTRAP_PROVENANCE with an id that says so in the
value itself. Every change AFTER bootstrap goes through the real governed service.

THE PROTECTED AUTHORITY'S CODE IS DELIBERATELY UNREMARKABLE, and a DECOY authority carrying the
suggestive illustrative administration code with the flag set FALSE is seeded alongside it, so
a code-string implementation would fail loudly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.authorization.business_authority import configuration_policy as policy
from app.modules.authorization.business_authority import (
    configuration_repository as configuration_store,
)
from app.modules.authorization.business_authority.configuration_contract import (
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
    CHANGE_PAYLOAD_FIELDS,
    CONFIGURATION_TABLES_CHILD_FIRST,
)
from app.modules.authorization.business_authority.configuration_domain import (
    ConfigurationChangeProposal,
)
from app.modules.authorization.business_authority.configuration_service import (
    GovernedAuthorityConfigurationService,
)
from app.modules.authorization.business_authority.contract import (
    BOOTSTRAP_PROVENANCE,
    EVALUATOR_NONE,
    SCOPE_GLOBAL,
)
from app.modules.authorization.business_authority.domain import AuthenticatedActor
from app.modules.authorization.business_authority.postgres_provider import (
    PostgresAuthorityConfigurationProvider,
)
from app.modules.authorization.business_authority.store_contract import (
    FAMILY_TABLES,
    STORE_TABLES_CHILD_FIRST,
)
from app.modules.hr_reference.contract import (
    EMPLOYMENT_ACTIVE,
    ActorPersonReference,
    EmploymentStateReference,
    HrLookup,
    IncumbencyReference,
    OrgUnitVersionReference,
    PositionVersionReference,
    missing,
    ok,
    unavailable,
)

# Labelled in the VALUE itself, so no reader of a row, an evidence dump or a failure message can
# mistake it for production bootstrap provenance.
SYNTHETIC_PROVENANCE_ID = "SYNTHETIC-E3-TEST-FIXTURE-NOT-A-PRODUCTION-BOOTSTRAP"

ADMIN_A_ACTOR, ADMIN_A_PERSON = "e3-actor-admin-a", "e3-person-admin-a"
ADMIN_B_ACTOR, ADMIN_B_PERSON = "e3-actor-admin-b", "e3-person-admin-b"
PLAIN_ACTOR, PLAIN_PERSON = "e3-actor-plain", "e3-person-plain"
OUTSIDER_ACTOR, OUTSIDER_PERSON = "e3-actor-outsider", "e3-person-outsider"

SEAT_POSITION = "e3-position-seat"
ORG_ROOT = "e3-org-root"

PROTECTED_AUTHORITY_CODE = "E3-SYNTHETIC-GOVERNANCE-CAPABILITY"
ORDINARY_AUTHORITY_CODE = "E3-SYNTHETIC-ORDINARY-CAPABILITY"
# A DECOY. The illustrative administration code from ADR-033, deliberately NOT protected, so
# any implementation that special-cases the string fails here.
DECOY_AUTHORITY_CODE = "AUTHORITY_CONFIGURATION_ADMIN"

AUTH_PROTECTED = "e3-auth-protected"
AUTH_ORDINARY = "e3-auth-ordinary"
AUTH_DECOY = "e3-auth-decoy"
ROLE_ADMIN = "e3-role-admin"
ROLE_ORDINARY = "e3-role-ordinary"
RULE_ADMIN = "e3-rule-admin"
RULE_ORDINARY = "e3-rule-ordinary"
ASSIGN_ADMIN_A = "e3-assign-admin-a"
ASSIGN_ADMIN_B = "e3-assign-admin-b"

V1 = "0001"

_GENERIC = (
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


def hours_ago(hours: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def hours_from_now(hours: float) -> datetime:
    """A FUTURE instant. Needed because a future-effective successor is exactly the shape that
    must not be mistaken for the object's current state."""

    return datetime.now(timezone.utc) + timedelta(hours=hours)


BOOTSTRAP_FROM = hours_ago(24 * 90)


class SyntheticActorPersonProvider:
    """Maps an authenticated actor to a canonical person. TEST-ONLY.

    The mapping is mutable so a test can model an actor-person link changing between
    authorization and activation. There is deliberately no parameter through which a caller
    could supply a person identity directly.
    """

    def __init__(self, mapping: Mapping[str, str] | None = None) -> None:
        self.mapping: dict[str, str] = dict(
            mapping
            if mapping is not None
            else {
                ADMIN_A_ACTOR: ADMIN_A_PERSON,
                ADMIN_B_ACTOR: ADMIN_B_PERSON,
                PLAIN_ACTOR: PLAIN_PERSON,
                OUTSIDER_ACTOR: OUTSIDER_PERSON,
            }
        )
        self.available = True

    def resolve_actor_person(self, actor_user_public_id: str, as_of: datetime) -> HrLookup:
        if not self.available:
            return unavailable()
        person_id = self.mapping.get(actor_user_public_id)
        if person_id is None:
            return missing()
        return ok(
            ActorPersonReference(
                actor_user_public_id=actor_user_public_id,
                person_id=person_id,
                canonical_snapshot_at=as_of,
                reference_evidence=f"synthetic-e3-actor-person-link:{actor_user_public_id}",
            )
        )


class SyntheticHrProvider:
    """Canonical HR/organisation answers for deterministic tests. TEST-ONLY.

    Per-position incumbency is mutable, which is what lets a test model the incumbency change
    that turns an ordinary pending change into a self-affecting one between authorization and
    activation.
    """

    def __init__(self, *, incumbents: Mapping[str, str] | None = None) -> None:
        self.incumbents: dict[str, str] = dict(
            incumbents if incumbents is not None else {SEAT_POSITION: OUTSIDER_PERSON}
        )
        self.employment: dict[str, str] = {}
        self.incumbency_available = True

    def get_employment_state(self, person_id: str, as_of: datetime) -> HrLookup:
        return ok(
            EmploymentStateReference(
                person_id=person_id,
                employment_state_version_id=f"e3-employment-{person_id}",
                employment_status=self.employment.get(person_id, EMPLOYMENT_ACTIVE),
                canonical_snapshot_at=as_of,
            )
        )

    def get_position(self, position_id: str, as_of: datetime) -> HrLookup:
        return ok(
            PositionVersionReference(
                position_id=position_id,
                position_version_id=f"e3-position-version-{position_id}",
                org_unit_id=ORG_ROOT,
                canonical_snapshot_at=as_of,
            )
        )

    def get_incumbency(self, position_id: str, as_of: datetime) -> HrLookup:
        if not self.incumbency_available:
            return unavailable()
        person_id = self.incumbents.get(position_id)
        if person_id is None:
            return missing()
        return ok(
            IncumbencyReference(
                position_id=position_id,
                incumbency_id=f"e3-incumbency-{position_id}",
                person_id=person_id,
                canonical_snapshot_at=as_of,
            )
        )

    def get_org_unit(self, org_unit_id: str, as_of: datetime) -> HrLookup:
        return ok(
            OrgUnitVersionReference(
                org_unit_id=org_unit_id,
                org_unit_version_id=f"e3-org-version-{org_unit_id}",
                parent_org_unit_id=None,
                canonical_snapshot_at=as_of,
            )
        )


def clear_everything(db: Session) -> None:
    """Empty the governed tables and the published store, children first.

    These tables are exclusively PF-1A-E2-B's and PF-1A-E3's, and neither migration seeds
    anything into them, so emptying them cannot touch business data. This is FIXTURE teardown;
    the production packages expose no delete path at all.
    """

    for table in CONFIGURATION_TABLES_CHILD_FIRST:
        db.execute(text(f"DELETE FROM {table}"))
    for table in STORE_TABLES_CHILD_FIRST:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


def bootstrap_version(
    db: Session,
    family: str,
    object_id: str,
    object_version: str,
    payload: Mapping[str, Any],
    *,
    active_flag: bool = True,
    effective_from: datetime | None = None,
    declared_effective_to: datetime | None = None,
    published_at: datetime | None = None,
    corrects_object_version: str | None = None,
) -> None:
    """Write ONE synthetic published version, under explicitly synthetic provenance.

    `object_version` is whatever the caller says, INCLUDING a non-numeric identifier. That is
    not a quirk of the fixture: PF-1A-E2 defines the value as opaque, so a pre-PF-1A-E3
    publication reading "v1" or a UUID is an ordinary predecessor and must behave like one.

    `published_at` and `corrects_object_version` are explicit because both are lineage inputs the
    governed writer must reason about but never writes itself: a recorded publication time AHEAD
    of the activation clock is what a rollback or a restored backup looks like, and a correction
    (retract-then-republish) is a legitimate history a governed UPDATE has to resolve its
    predecessor through.
    """

    tables = FAMILY_TABLES[family]
    db.execute(
        text(
            f"INSERT INTO {tables.stable} (object_id) VALUES (:oid) "
            "ON CONFLICT (object_id) DO NOTHING"
        ),
        {"oid": object_id},
    )
    values: dict[str, Any] = {
        "object_id": object_id,
        "object_version": object_version,
        "effective_from": effective_from or BOOTSTRAP_FROM,
        "declared_effective_to": declared_effective_to,
        "active_flag": active_flag,
        "corrects_object_version": corrects_object_version,
        "publication_reference_type": BOOTSTRAP_PROVENANCE,
        "publication_reference_id": SYNTHETIC_PROVENANCE_ID,
        "published_at": published_at or BOOTSTRAP_FROM,
    }
    columns = CHANGE_PAYLOAD_FIELDS[family]
    for name in columns:
        values[name] = payload.get(name)
    names = list(_GENERIC) + list(columns)
    statement = text(
        f"INSERT INTO {tables.version} ({', '.join(names)}) "
        f"VALUES ({', '.join(':' + n for n in names)})"
    )
    if "parameter_payload" in values:
        statement = statement.bindparams(bindparam("parameter_payload", type_=JSONB))
    db.execute(statement, values)
    db.commit()


def bootstrap_retraction(
    db: Session,
    family: str,
    object_id: str,
    object_version: str,
    *,
    retraction_id: str | None = None,
    retracted_at: datetime | None = None,
) -> None:
    """Assert, synthetically, that one published version was recorded in error.

    PF-1A-E3 deliberately implements no retraction path of its own, so a retraction can only ever
    arrive from another authorized mechanism - which is exactly why the governed writer has to
    resolve its predecessor THROUGH the kernel rather than by taking the greatest identity it can
    see. The retracted row is not deleted, hidden or edited: it stays stored, stays
    dereferenceable, and stays part of the provenance the kernel validates and the allocation
    anchor spans.
    """

    tables = FAMILY_TABLES[family]
    db.execute(
        text(
            f"INSERT INTO {tables.retraction} (object_id, retraction_id, object_version, "
            "retracted_at, publication_reference_type, publication_reference_id) "
            "VALUES (:oid, :rid, :ver, :at, :ptype, :pid)"
        ),
        {
            "oid": object_id,
            "rid": retraction_id or f"e3-retraction-{object_id}-{object_version}",
            "ver": object_version,
            "at": retracted_at or hours_ago(1),
            "ptype": BOOTSTRAP_PROVENANCE,
            "pid": SYNTHETIC_PROVENANCE_ID,
        },
    )
    db.commit()


def bootstrap_synthetic_context(db: Session) -> None:
    """Establish the synthetic world every PF-1A-E3 test starts from.

    Two independent holders of the protected meta-authority, so a genuine different-person
    authorization can be demonstrated without inventing one mid-test; one ordinary business
    authority, so an unrelated non-protected change can be shown to remain single-person; and
    one decoy authority carrying the illustrative administration CODE with the protection FLAG
    false, so a code-string implementation fails.
    """

    bootstrap_version(
        db,
        BUSINESS_AUTHORITY,
        AUTH_PROTECTED,
        V1,
        {
            "authority_code": PROTECTED_AUTHORITY_CODE,
            "authority_name": "Synthetic governance capability",
            "description": "Test-only protected meta-authority.",
            "is_protected_meta_authority": True,
        },
    )
    bootstrap_version(
        db,
        BUSINESS_AUTHORITY,
        AUTH_ORDINARY,
        V1,
        {
            "authority_code": ORDINARY_AUTHORITY_CODE,
            "authority_name": "Synthetic ordinary capability",
            "description": "Test-only ordinary business authority.",
            "is_protected_meta_authority": False,
        },
    )
    bootstrap_version(
        db,
        BUSINESS_AUTHORITY,
        AUTH_DECOY,
        V1,
        {
            "authority_code": DECOY_AUTHORITY_CODE,
            "authority_name": "Decoy - the code is suggestive, the flag is not set",
            "description": "Protection is a data flag, never a code string.",
            "is_protected_meta_authority": False,
        },
    )
    bootstrap_version(
        db,
        BUSINESS_AUTHORITY_ROLE,
        ROLE_ADMIN,
        V1,
        {
            "role_code": "E3_SYNTHETIC_GOVERNANCE_ROLE",
            "role_name": "Synthetic configuration governance role",
            "description": "",
        },
    )
    bootstrap_version(
        db,
        BUSINESS_AUTHORITY_ROLE,
        ROLE_ORDINARY,
        V1,
        {
            "role_code": "E3_SYNTHETIC_ORDINARY_ROLE",
            "role_name": "Synthetic ordinary role",
            "description": "",
        },
    )
    for rule_id, role_id, authority_id in (
        (RULE_ADMIN, ROLE_ADMIN, AUTH_PROTECTED),
        (RULE_ORDINARY, ROLE_ORDINARY, AUTH_ORDINARY),
    ):
        bootstrap_version(
            db,
            BUSINESS_AUTHORITY_RULE,
            rule_id,
            V1,
            {
                "business_authority_role_object_id": role_id,
                "business_authority_object_id": authority_id,
                "scope_type": SCOPE_GLOBAL,
                "scope_id": None,
                "parameter_evaluator_type": EVALUATOR_NONE,
                "parameter_payload": None,
            },
        )
    for object_id, person_id in (
        (ASSIGN_ADMIN_A, ADMIN_A_PERSON),
        (ASSIGN_ADMIN_B, ADMIN_B_PERSON),
    ):
        bootstrap_version(
            db,
            BUSINESS_AUTHORITY_ASSIGNMENT,
            object_id,
            V1,
            {
                "business_authority_role_object_id": ROLE_ADMIN,
                "person_id": person_id,
                "position_id": None,
                "scope_type": SCOPE_GLOBAL,
                "scope_id": None,
            },
        )


@dataclass
class E3Env:
    db: Session
    actors: SyntheticActorPersonProvider
    hr: SyntheticHrProvider
    provider: PostgresAuthorityConfigurationProvider
    service: GovernedAuthorityConfigurationService


@pytest.fixture
def env():
    """A session over the real dockerized PostgreSQL with a freshly bootstrapped world.

    The governed tables and the published store are cleared before AND after every test, so no
    test can see a neighbour's rows and none leaves residue behind. Clearing before as well as
    after also means a run interrupted mid-test cannot poison the next one.
    """

    db = SessionLocal()
    try:
        clear_everything(db)
        bootstrap_synthetic_context(db)
        actors = SyntheticActorPersonProvider()
        hr = SyntheticHrProvider()
        provider = PostgresAuthorityConfigurationProvider(db)
        yield E3Env(
            db=db,
            actors=actors,
            hr=hr,
            provider=provider,
            service=GovernedAuthorityConfigurationService(
                db,
                authority_configuration_port=provider,
                actor_person_port=actors,
                hr_reference_port=hr,
            ),
        )
    finally:
        db.rollback()
        clear_everything(db)
        db.close()


ADMIN_A = AuthenticatedActor(actor_user_public_id=ADMIN_A_ACTOR)
ADMIN_B = AuthenticatedActor(actor_user_public_id=ADMIN_B_ACTOR)
PLAIN = AuthenticatedActor(actor_user_public_id=PLAIN_ACTOR)


def proposal(
    family,
    object_id,
    change_type,
    payload,
    *,
    hours=1.0,
    previous=None,
    effective_from=None,
    declared_effective_to=None,
):
    """One proposal. `effective_from` overrides `hours` when a test needs an exact instant.

    `declared_effective_to` is explicit rather than derived, because the temporal-scope half of
    the privilege-increase rule is exactly what several tests need to vary deliberately.
    """

    return ConfigurationChangeProposal(
        configuration_object_family=family,
        configuration_object_id=object_id,
        change_type=change_type,
        change_payload=dict(payload),
        effective_from=hours_ago(hours) if effective_from is None else effective_from,
        declared_effective_to=declared_effective_to,
        previous_object_version_expected=previous,
    )


def role_payload(code: str = "E3_NEW_ROLE") -> dict[str, Any]:
    return {"role_code": code, "role_name": code.title(), "description": ""}


def assignment_payload(role_id, *, person_id=None, position_id=None, scope_id=None):
    return {
        "business_authority_role_object_id": role_id,
        "person_id": person_id,
        "position_id": position_id,
        "scope_type": SCOPE_GLOBAL if scope_id is None else "EXACT",
        "scope_id": scope_id,
    }


def version_rows(db: Session, family: str, object_id: str) -> list[dict[str, Any]]:
    """Every published version of one object, in PUBLICATION order.

    Ordered by `id`, never by `object_version`: the version identifier is opaque, so ordering by
    it would be meaningless for a PF-1A-E3-minted identity and misleading for a "v1"/UUID one.
    """

    return [
        dict(row)
        for row in db.execute(
            text(
                f"SELECT * FROM {FAMILY_TABLES[family].version} WHERE object_id = :oid "
                "ORDER BY id"
            ),
            {"oid": object_id},
        )
        .mappings()
        .all()
    ]


def current_version(db: Session, family: str, object_id: str) -> str | None:
    """The object's ALL-TIME lexicographic maximum - its ALLOCATION ANCHOR.

    This is what a new identity is minted from, and it deliberately spans retracted versions.
    Where an object has no retraction it also happens to be the authoritative predecessor, which
    is why most tests can use it as an expected predecessor; where a retraction exists the two
    diverge, and a test that means the predecessor must say so with
    `authoritative_predecessor(...)` below. Tests read identities back rather than predicting
    them, which is the point: an expected predecessor is an OPAQUE value a proposer was told, not
    a number anyone can compute.
    """

    versions = [row["object_version"] for row in version_rows(db, family, object_id)]
    return max(versions) if versions else None


def authoritative_predecessor(
    db: Session, family: str, object_id: str, as_of: datetime | None = None
) -> str | None:
    """The identity a governed UPDATE or DEACTIVATE must state, derived the production way.

    Calls the SAME production functions the governed activation calls - the E3 material read and
    `configuration_policy.derive_effective_state`, which delegates the semantics to the unchanged
    PF-1A-E2-A kernel - rather than re-deriving the answer here. A second copy in the fixture
    would be a copy that could agree with a bug.
    """

    rows, assertions = configuration_store.load_published_material(db)
    state = policy.derive_effective_state(
        rows, assertions, as_of or datetime.now(timezone.utc)
    )
    row = state.predecessor_rows.get((family, object_id))
    return None if row is None else row.object_version


def publish(env_: E3Env, prop, *, actor=ADMIN_A) -> str:
    """Propose, self-authorize and activate an ordinary change."""

    proposed = env_.service.propose(actor, prop)
    assert proposed.accepted, proposed.refusal_reason
    assert env_.service.authorize(actor, proposed.configuration_change_id).accepted
    activated = env_.service.activate(actor, proposed.configuration_change_id)
    assert activated.accepted, activated.refusal_reason
    return proposed.configuration_change_id
