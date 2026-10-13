"""PF-1A-E3: publication immutability, provenance, evidence and the downgrade guard."""

from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

import app
from app.core.database import SessionLocal
from app.modules.authorization.business_authority import configuration_contract as e3
from app.modules.authorization.business_authority import configuration_repository as store
from tests.fixtures.pf_1a_e3_reference_context import (  # noqa: F401
    ADMIN_A,
    current_version,
    env,
    proposal,
    publish,
    role_payload,
    version_rows,
)

ROLE = e3.BUSINESS_AUTHORITY_ROLE

_MIGRATION = (
    Path(app.__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260906_0032_pf_1a_e3_governed_authority_configuration.py"
)


def _migration_module():
    spec = importlib.util.spec_from_file_location("pf_1a_e3_migration", _MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_an_earlier_published_row_is_untouched_after_a_later_version_publishes(env) -> None:
    publish(env, proposal(ROLE, "e3-imm", e3.CHANGE_CREATE, role_payload()))
    before = version_rows(env.db, ROLE, "e3-imm")
    publish(
        env,
        proposal(
            ROLE, "e3-imm", e3.CHANGE_UPDATE, role_payload("E3_RENAMED"), hours=0.9,
            previous=current_version(env.db, ROLE, "e3-imm"),
        ),
    )
    after = version_rows(env.db, ROLE, "e3-imm")
    assert len(before) == 1 and len(after) == 2
    assert after[0] == before[0], "the earlier published row was mutated"


def test_deactivation_publishes_a_new_inactive_version_and_never_edits_the_old_row(env) -> None:
    created = publish(env, proposal(ROLE, "e3-de", e3.CHANGE_CREATE, role_payload()))
    original = version_rows(env.db, ROLE, "e3-de")[0]
    deactivated = publish(
        env,
        proposal(
            ROLE, "e3-de", e3.CHANGE_DEACTIVATE, role_payload(), hours=0.9,
            previous=current_version(env.db, ROLE, "e3-de"),
        ),
    )
    first_version = e3.allocate_object_version(None, created)
    rows = version_rows(env.db, ROLE, "e3-de")
    assert [row["object_version"] for row in rows] == [
        first_version,
        e3.allocate_object_version(first_version, deactivated),
    ]
    assert rows[0] == original
    assert (rows[0]["active_flag"], rows[1]["active_flag"]) == (True, False)
    # The inactive successor sorts AFTER the version it supersedes, which is what lets the
    # unchanged kernel read the pair as ordinary lineage rather than contradictory provenance.
    assert rows[1]["object_version"] > rows[0]["object_version"]


def test_every_publication_carries_configuration_change_provenance(env) -> None:
    cid = publish(env, proposal(ROLE, "e3-pr", e3.CHANGE_CREATE, role_payload()))
    row = version_rows(env.db, ROLE, "e3-pr")[0]
    assert row["publication_reference_type"] == "CONFIGURATION_CHANGE"
    assert row["publication_reference_id"] == cid
    # PF-1A-E3 implements publication and deactivation, not correction.
    assert row["corrects_object_version"] is None


def test_a_historical_version_stays_dereferenceable_after_later_versions(env) -> None:
    created = publish(env, proposal(ROLE, "e3-h", e3.CHANGE_CREATE, role_payload("A")))
    publish(
        env,
        proposal(
            ROLE, "e3-h", e3.CHANGE_UPDATE, role_payload("B"), hours=0.9,
            previous=current_version(env.db, ROLE, "e3-h"),
        ),
    )
    publish(
        env,
        proposal(
            ROLE, "e3-h", e3.CHANGE_UPDATE, role_payload("C"), hours=0.8,
            previous=current_version(env.db, ROLE, "e3-h"),
        ),
    )
    first = env.provider.get_published_version(
        ROLE, "e3-h", e3.allocate_object_version(None, created)
    )
    assert first.payload.role_code == "A"
    assert first.publication_reference_type == "CONFIGURATION_CHANGE"


def test_each_stage_appends_its_own_evaluation_and_none_is_overwritten(env) -> None:
    cid = publish(env, proposal(ROLE, "e3-ev", e3.CHANGE_CREATE, role_payload()))
    stages = [row["evaluation_stage"] for row in store.load_evaluations(env.db, cid)]
    assert stages == [e3.STAGE_PROPOSAL, e3.STAGE_AUTHORIZATION, e3.STAGE_ACTIVATION]
    activation = store.latest_evaluation(env.db, cid, e3.STAGE_ACTIVATION)
    assert activation["outcome"] == e3.OUTCOME_PERMITTED
    assert activation["authorization_satisfied"] is True
    assert activation["dependency_fingerprint"]
    assert activation["risk_derivation"]


def test_the_downgrade_guard_passes_when_empty_and_refuses_once_governed_state_exists(
    env,
) -> None:
    module = _migration_module()
    assert set(module.governed_state_counts(env.db.connection()).values()) == {0}
    # An empty development database still downgrades cleanly and intentionally.
    module.assert_no_governed_state(env.db.connection())

    publish(env, proposal(ROLE, "e3-guard", e3.CHANGE_CREATE, role_payload()))
    counts = module.governed_state_counts(env.db.connection())
    assert counts[e3.CONFIGURATION_CHANGE_TABLE] == 1
    assert counts["published_configuration_change_versions"] == 1
    with pytest.raises(RuntimeError) as raised:
        module.assert_no_governed_state(env.db.connection())
    assert "refusing to downgrade PF-1A-E3" in str(raised.value)
    assert store.governed_state_counts(env.db) == counts


def test_the_downgrade_guard_locks_every_table_a_governed_activation_writes() -> None:
    """The lock order is FIXED, DOCUMENTED and wider than the tables this revision drops.

    A governed activation writes a published version row into a PF-1A-E2-B version table and a
    lifecycle row into a PF-1A-E3 table in ONE transaction. Locking only the tables about to be
    dropped would leave the other half of that write free to commit inside the check-to-drop
    window, and the downgrade would then destroy governed state it had just certified absent.
    """

    module = _migration_module()
    assert module.DOWNGRADE_LOCK_ORDER == (
        "authz_business_authority_version",
        "authz_business_authority_role_version",
        "authz_business_authority_rule_version",
        "authz_business_authority_assignment_version",
        e3.CONFIGURATION_CHANGE_TABLE,
        e3.CONFIGURATION_EVALUATION_TABLE,
    )
    # Every table the governed writer can touch is covered, in one fixed order so two concurrent
    # downgrades acquire the same locks in the same sequence and cannot deadlock each other.
    assert len(module.DOWNGRADE_LOCK_ORDER) == len(set(module.DOWNGRADE_LOCK_ORDER))
    assert set(module.PUBLISHED_VERSION_TABLES) < set(module.DOWNGRADE_LOCK_ORDER)


def test_a_concurrent_governed_writer_cannot_commit_into_the_check_to_drop_window(env) -> None:
    """THE DESTRUCTIVE-DOWNGRADE RACE REGRESSION.

    A writer holds an uncommitted governed lifecycle INSERT. Its row is invisible to every other
    transaction, so a guard that COUNTED FIRST would read zero, certify "no governed state", and
    only afterwards ask for the locks the DROP needs - by which time the writer may have
    committed. The guard must therefore be unable to reach its own count at all while that writer
    is in flight.

    Proved with a bounded `lock_timeout` rather than with threads: the guard is required to WAIT
    for the writer, so the observable, deterministic evidence that it waits is that it aborts on
    the timeout instead of returning a comfortable zero-state verdict.
    """

    module = _migration_module()

    writer = SessionLocal()
    guard = SessionLocal()
    try:
        # An uncommitted governed lifecycle write, through the real governed writer.
        store.insert_change(writer, _pending_change_values("e3-race-writer"))
        assert writer.execute(
            text(f"SELECT COUNT(*) FROM {e3.CONFIGURATION_CHANGE_TABLE}")
        ).scalar_one() == 1

        # It is invisible elsewhere - which is exactly what would make a count-first guard say
        # "empty" and proceed to drop a table that is about to have a row in it.
        guard.execute(text("SET LOCAL lock_timeout = '750ms'"))
        assert guard.execute(
            text(f"SELECT COUNT(*) FROM {e3.CONFIGURATION_CHANGE_TABLE}")
        ).scalar_one() == 0

        with pytest.raises(DBAPIError) as raised:
            module.assert_no_governed_state(guard.connection())
        assert "lock" in str(raised.value).lower()
        guard.rollback()

        # The writer was never blocked out of committing by a half-finished guard.
        writer.commit()
    finally:
        guard.rollback()
        guard.close()
        writer.rollback()
        writer.close()

    # And once that same row IS visible, the guard refuses in the ordinary, recorded way.
    with pytest.raises(RuntimeError) as refusal:
        module.assert_no_governed_state(env.db.connection())
    assert "refusing to downgrade PF-1A-E3" in str(refusal.value)
    env.db.rollback()


def _pending_change_values(object_id: str) -> dict:
    """A minimal, structurally valid PENDING Configuration Change row.

    Written through `configuration_repository.insert_change`, so this exercises the real
    governed writer rather than a hand-rolled INSERT that could drift from it.
    """

    now = datetime.now(timezone.utc)
    return {
        "configuration_change_id": f"cc-{uuid.uuid4()}",
        "configuration_object_family": ROLE,
        "configuration_object_id": object_id,
        "change_type": e3.CHANGE_CREATE,
        "change_payload": {"role_code": "E3_RACE", "role_name": "Race", "description": ""},
        "proposed_active_flag": True,
        "effective_from": now,
        "declared_effective_to": None,
        "previous_object_version_expected": None,
        "proposal_time_is_self_affecting": False,
        "proposal_time_affects_protected_meta_authority": False,
        "proposal_time_privilege_increasing": True,
        "proposal_time_authorization_required": False,
        "proposal_context_snapshot": {},
        "proposal_dependency_fingerprint": "race-fixture-fingerprint",
        "initiated_by_person_id": "e3-person-race",
        "initiated_by_actor_user_public_id": "e3-actor-race",
        "initiated_at": now,
        "lifecycle_status": e3.LIFECYCLE_PENDING,
    }
