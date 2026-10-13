import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session", autouse=True)
def _remove_business_events_created_by_this_test_session():
    """Delete only the `business_event` rows this pytest session created.

    The suite runs against the shared Docker development database. Business events are
    written by the same service code the real routes use, and the module test files clean
    up their own business records but not every event those records produced - so repeated
    runs accumulated `business_event` rows indefinitely.

    The boundary is the maximum id present before any test runs. Rows at or below it are
    pre-existing and are never touched. Rows above it were created by this session and are
    removed in the finalizer.

    Deleting at session teardown rather than per test is deliberate: several tests assert on
    events emitted earlier in the same test, and some assert across a small sequence of
    actions. Removing events mid-run would break those assertions, so events remain fully
    visible for the whole session and are cleared only once it ends.

    `business_event` has no foreign key to any business table, so deleting by id range is
    FK-safe and cannot orphan or cascade into business records.

    The finalizer runs on normal completion and on ordinary test failures, because pytest
    finalizes session fixtures either way. It does not run if the process is killed outright
    (SIGKILL, or a hard crash of the interpreter).
    """
    from sqlalchemy import text

    from app.core.database import SessionLocal

    with SessionLocal() as db:
        boundary_id = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM business_event")).scalar_one()

    yield boundary_id

    with SessionLocal() as db:
        db.execute(
            text("DELETE FROM business_event WHERE id > :boundary_id"),
            {"boundary_id": boundary_id},
        )
        db.commit()


@pytest.fixture(scope="session", autouse=True)
def _remove_sign_in_counts_created_by_this_test_session():
    """Delete the `sign_in_attempt` and `sign_in_stop` rows this pytest session created (TB-1 TB1-204 part a).

    Every sign-in leaves an attempt for its typed username, and a stop when it reaches the limit, which later sign-ins
    would otherwise prune only once their window has passed. Rows that existed before the session are left as they are.
    """
    from sqlalchemy import text

    from app.core.database import SessionLocal

    with SessionLocal() as db:
        last_attempt = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM sign_in_attempt")).scalar_one()
        stops_before = set(db.execute(text("SELECT username_digest FROM sign_in_stop")).scalars())

    yield

    with SessionLocal() as db:
        db.execute(text("DELETE FROM sign_in_attempt WHERE id > :last"), {"last": last_attempt})
        for digest in set(db.execute(text("SELECT username_digest FROM sign_in_stop")).scalars()) - stops_before:
            db.execute(text("DELETE FROM sign_in_stop WHERE username_digest = :digest"), {"digest": digest})
        db.commit()


@pytest.fixture(scope="session", autouse=True)
def _isolate_the_smoke_run_directory(tmp_path_factory):
    """Point the TE-1 harness's run/scope directory at a temporary one for the whole session.

    Seeding and manifest persistence both write here, and a long-lived backend container had
    accumulated hundreds of files for runs that no longer existed. Isolating the directory keeps
    the real one untouched by the test session.

    **This lives in conftest.py rather than in test_smoke_data_harness.py, and that placement is
    the fix rather than a detail.** Putting it in that module left `test_slice_9b_pilot_hardening.py`
    - which also calls `run_scenario` and `cleanup_manifest` - still writing to the real directory,
    and six orphan scopes per full-suite run proved it. A guard scoped to the module that happens
    to be *about* the harness misses every other module that merely *uses* it.

    Isolating the directory rather than deleting artifacts afterwards is deliberate: a teardown
    step only removes what it remembers to, which is the exact failure mode the harness exists to
    fix. A directory the tests cannot escape needs no such memory.

    `store.runs_dir()` reads this module global on every call, so patching it reaches
    `save_manifest`, `list_runs` and `manifest_path_for_run` alike.
    """
    from tooling.smoke_data import store as store_module

    original = store_module.RUNS_DIR
    store_module.RUNS_DIR = tmp_path_factory.mktemp("smoke-runs")
    try:
        yield store_module.RUNS_DIR
    finally:
        store_module.RUNS_DIR = original
