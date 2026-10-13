"""TB-1 finding TB1-102 part b (corrective package CS-06's early step): one replay rule for a create that carries a
request key - the key plus a fingerprint of the request; the same request again is answered with the first record,
flagged `replayed`; any other request with the key is refused (409).

Each module's own behaviour is tested beside its other tests: equipment models in test_ert1_equipment_import_api.py,
kit in test_ert2_detachable_kit.py, resource requirements in test_wrr001_resource_requirements.py, allocations (8A,
the rule's first home) in test_8a_equipment_allocation.py. Here: the shared fingerprint, and what the database holds
to (migration 20260908_0050).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

import pytest
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError

from app.core.database import SessionLocal
from app.modules.resource_assignments import service as assignments_service
from app.modules.resource_assignments.schemas import AssignmentCreate
from app.shared.request_keys import is_same_request, request_fingerprint
from tests.request_key_test_support import KEYED_TABLES

# A fixed allocation request and its fingerprint as 8A core stores it. Fingerprints are kept in the database, so the
# shared function must give exactly what 8A gave before it was shared: a change would refuse the retry of every
# request already made.
ALLOCATION = {
    "create_request_key": "form-1",
    "requirement_public_id": "6a4c3f5e-2b1d-4c8e-9f7a-0123456789ab",
    "unit_number": 1,
    "machine_public_id": "0f1e2d3c-4b5a-4968-8776-5544332211aa",
    "planned_from": "2027-01-10",
    "notes": "Night shifts",
}
ALLOCATION_FINGERPRINT = "26d6b630ad1d64ae03942a2160b14214f43a39e0c15d671fa58dfa966571a754"


def _as_8a_wrote_it(payload: BaseModel, *, acts_on: Any = None) -> str:
    """8A core's `_fingerprint` exactly as it stood before the rule was shared (resource_assignments/service.py at
    5e19123), kept here as the reference."""
    sent = payload.model_dump(mode="json", exclude_unset=True, exclude={"create_request_key"})
    body = json.dumps({"acts_on": str(acts_on) if acts_on else None, "request": sent}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def test_the_shared_fingerprint_is_the_one_8a_stores() -> None:
    payload = AssignmentCreate(**ALLOCATION)
    acts_on = uuid.UUID("11111111-2222-4333-8444-555555555555")
    assert request_fingerprint(payload) == _as_8a_wrote_it(payload) == ALLOCATION_FINGERPRINT
    assert request_fingerprint(payload, acts_on=acts_on) == _as_8a_wrote_it(payload, acts_on=acts_on)
    assert assignments_service._fingerprint(payload, acts_on=acts_on) == request_fingerprint(payload, acts_on=acts_on)


def test_the_fingerprint_is_the_request_as_sent_without_its_key() -> None:
    payload = AssignmentCreate(**ALLOCATION)
    assert request_fingerprint(AssignmentCreate(**{**ALLOCATION, "create_request_key": "form-2"})) == request_fingerprint(payload)
    # Every value counts, and a field left out is not the field sent empty.
    assert request_fingerprint(AssignmentCreate(**{**ALLOCATION, "unit_number": 2})) != request_fingerprint(payload)
    assert request_fingerprint(AssignmentCreate(**{**ALLOCATION, "planned_to": None})) != request_fingerprint(payload)
    # So is the record a request acts on.
    assert request_fingerprint(payload, acts_on="a") != request_fingerprint(payload, acts_on="b")
    assert len(request_fingerprint(payload)) == 64 and set(request_fingerprint(payload)) <= set("0123456789abcdef")


def test_a_key_without_a_fingerprint_is_never_the_same_request() -> None:
    fingerprint = request_fingerprint(AssignmentCreate(**ALLOCATION))
    assert is_same_request(fingerprint, fingerprint) is True
    assert is_same_request(None, fingerprint) is False
    assert is_same_request("0" * 64, fingerprint) is False


# --- The database (migration 20260908_0050) --------------------------------------------------------------------


@contextmanager
def _rolled_back() -> Iterator[Any]:
    with SessionLocal() as db:
        try:
            yield db
        finally:
            db.rollback()


def test_each_keyed_table_holds_a_well_formed_fingerprint_only_with_a_key_and_never_changes_it() -> None:
    with SessionLocal() as db:
        checks = dict(
            db.execute(
                text(
                    "SELECT conrelid::regclass::text, pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conname = 'ck_' || conrelid::regclass::text || '_create_request_fingerprint'"
                )
            ).all()
        )
        triggers = dict(
            db.execute(
                text(
                    "SELECT tgrelid::regclass::text, tgenabled FROM pg_trigger "
                    "WHERE tgname = 'trg_' || tgrelid::regclass::text || '_create_request_kept'"
                )
            ).all()
        )
    assert set(checks) == set(KEYED_TABLES) == set(triggers)
    for definition in checks.values():
        assert "create_request_key IS NOT NULL" in definition and "^[0-9a-f]{64}$" in definition
    # Enabled: a test that sets one aside for a moment (request_key_test_support) has put it back.
    assert set(triggers.values()) == {"O"}


def _insert_model(db, *, fingerprint: str | None) -> str:
    key = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO equipment_model (model_public_id, maker, model_name, class_code, create_request_key, "
            "create_request_fingerprint) VALUES (:p, 'ZED', :n, 'FORKLIFT', :k, :f)"
        ),
        {"p": str(uuid.uuid4()), "n": f"TB1-102B {uuid.uuid4().hex[:8]}", "k": key, "f": fingerprint},
    )
    return key


@pytest.mark.parametrize("fingerprint", ["0" * 63, "G" * 64, "A" * 64, ""])
def test_a_fingerprint_that_is_not_64_hexadecimal_digits_is_refused(fingerprint: str) -> None:
    with _rolled_back() as db, pytest.raises(IntegrityError, match="ck_equipment_model_create_request_fingerprint"):
        _insert_model(db, fingerprint=fingerprint)
    # A longer one does not fit the column at all.
    with _rolled_back() as db, pytest.raises(DataError, match="value too long"):
        _insert_model(db, fingerprint="0" * 65)


def test_a_fingerprint_without_a_key_is_refused() -> None:
    with _rolled_back() as db, pytest.raises(IntegrityError, match="ck_equipment_asset_create_request_fingerprint"):
        db.execute(
            text(
                "INSERT INTO equipment_asset (asset_public_id, asset_kind_code, origin_code, class_code, machine_number, "
                "asset_status_code, create_request_fingerprint) VALUES (:p, 'MACHINE', 'PLUM', 'CRANE', :n, 'ACTIVE', :f)"
            ),
            {"p": str(uuid.uuid4()), "n": f"TB1-102B-{uuid.uuid4().hex[:8]}", "f": "0" * 64},
        )


@pytest.mark.parametrize(
    "change", ["create_request_fingerprint = :other", "create_request_fingerprint = NULL", "create_request_key = :key2"]
)
def test_the_request_that_made_a_model_never_changes(change: str) -> None:
    with _rolled_back() as db:
        key = _insert_model(db, fingerprint="0" * 64)
        with pytest.raises(IntegrityError, match="The request that made a record never changes"):
            db.execute(
                text(f"UPDATE equipment_model SET {change} WHERE create_request_key = :key"),
                {"key": key, "other": "1" * 64, "key2": str(uuid.uuid4())},
            )


def test_a_model_made_before_fingerprints_keeps_none_and_its_other_columns_still_change() -> None:
    """A record from before migration 0050 is not given a fingerprint, and the guard does not stop ordinary changes
    to it - only to the request that made it."""
    with _rolled_back() as db:
        key = _insert_model(db, fingerprint=None)
        changed = db.execute(
            text("UPDATE equipment_model SET maker_part_number = 'PN', model_version = model_version + 1 WHERE create_request_key = :key"),
            {"key": key},
        ).rowcount
        assert changed == 1
        with pytest.raises(IntegrityError, match="The request that made a record never changes"):
            db.execute(text("UPDATE equipment_model SET create_request_fingerprint = :f WHERE create_request_key = :key"), {"key": key, "f": "0" * 64})
