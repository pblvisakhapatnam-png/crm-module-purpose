"""Slice 9D - static guard: no `record_business_event(...)` call in
`app/modules/interactions/service.py` may pass a restricted field in `event_payload`.

Restricted here means: the stored message body, the subject line, or a participant's email
address/phone number. `DATA_CLASSIFICATION_AND_HANDLING.md` requires business events to carry
context, not the restricted payload itself; this table is the first one in the programme that
will actively tempt someone to break that rule, because the event's own record_public_id points
straight at a row containing exactly that content.

DESIGN: fail-closed allowlist, not a blacklist. The check does not look for forbidden key names
like "body_text" - it asserts every key actually used in an `event_payload={...}` literal is a
member of an explicit safe set. A blacklist only catches names it already knows to look for; a
renamed or newly added restricted field would slip straight through it. An allowlist catches
that same case, because an unrecognised key is rejected regardless of what it is called.

Per the Slice 9B lesson repeated three times in that package's review history: a guard that has
never been shown to fail is an assertion of intent, not a control. Every check below carries a
test that drives it with synthetic bad input.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from tests.test_commercial_offers_api import (
    auth_headers,
    client,
    create_account_linked_test_opportunity,
)
from tests.test_interactions_api import _iso_now, _teardown_full_chain

INTERACTIONS_SERVICE_PATH = Path(__file__).resolve().parents[1] / "app" / "modules" / "interactions" / "service.py"

# Every key an event_payload literal in interactions/service.py may legitimately use. Deliberately
# narrow: metadata that identifies and traces the interaction, never its content. Adding a key
# here must be a deliberate, reviewed decision - see the module docstring.
SAFE_EVENT_PAYLOAD_KEYS = frozenset(
    {
        "schema_version",
        "linked_record_type",
        "linked_record_public_id",
        "channel_code",
        "direction_code",
        "occurred_at",
        "next_follow_up_at",
    }
)

# Keys that must never appear, named explicitly so a violation reports what was found rather
# than only that something unrecognised was found. This list exists for a better error message;
# the actual protection is the allowlist check above, which fails closed on ANY unrecognised
# key, named here or not.
KNOWN_RESTRICTED_KEYS = frozenset({"subject", "body_text", "body", "participants", "address_or_number", "outcome"})


def _find_event_payload_dict_keys(source: str) -> list[tuple[int, set[str]]]:
    """Parse `source` and return, for every `record_business_event(...)` call, the line number
    and the set of literal keys passed as `event_payload={...}`.

    Only inspects a literal dict passed via the `event_payload=` keyword. A call that builds the
    payload dynamically (a variable, a function call, `**unpacking`) would not be visible to this
    scan - which is a real, documented limitation, not a silent gap: see
    test_the_guard_flags_a_dynamically_built_payload_as_unrecognised below, which proves the
    fail-closed behaviour that limitation actually produces.
    """
    tree = ast.parse(source)
    results: list[tuple[int, set[str]]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_record_call = (isinstance(func, ast.Name) and func.id == "record_business_event") or (
            isinstance(func, ast.Attribute) and func.attr == "record_business_event"
        )
        if not is_record_call:
            continue

        for keyword in node.keywords:
            if keyword.arg != "event_payload":
                continue
            if isinstance(keyword.value, ast.Dict):
                keys: set[str] = set()
                for key_node in keyword.value.keys:
                    if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                        keys.add(key_node.value)
                    else:
                        # A non-literal key (e.g. built from a variable) cannot be verified
                        # statically. Represent it as an always-unrecognised sentinel so the
                        # allowlist check below fails closed rather than silently passing.
                        keys.add("<non-literal-key>")
                results.append((node.lineno, keys))
            else:
                # event_payload was passed but not as a literal dict (a variable, a function
                # call, a comprehension). Cannot verify statically - fail closed with the same
                # sentinel rather than skipping the call site.
                results.append((node.lineno, {"<non-dict-event-payload>"}))

    return results


def assert_event_payloads_use_only_safe_keys(source: str, *, safe_keys: frozenset[str]) -> None:
    """The actual guard. Raises AssertionError naming every offending call site and key."""
    offenders: list[str] = []
    for lineno, keys in _find_event_payload_dict_keys(source):
        unrecognised = keys - safe_keys
        if unrecognised:
            offenders.append(f"line {lineno}: unrecognised event_payload key(s) {sorted(unrecognised)}")

    assert offenders == [], "restricted or unrecognised event_payload key(s) found: " + "; ".join(offenders)


# ===========================================================================
# The guard driven against real source
# ===========================================================================


def test_every_record_business_event_call_in_interactions_service_uses_only_safe_keys() -> None:
    source = INTERACTIONS_SERVICE_PATH.read_text(encoding="utf-8")
    assert_event_payloads_use_only_safe_keys(source, safe_keys=SAFE_EVENT_PAYLOAD_KEYS)


def test_the_scan_actually_found_all_three_call_sites() -> None:
    """Proves the scanner is examining something, not vacuously passing over zero call sites -
    the exact 9B failure mode of a detector that collects only offenders."""
    source = INTERACTIONS_SERVICE_PATH.read_text(encoding="utf-8")
    call_sites = _find_event_payload_dict_keys(source)
    assert len(call_sites) == 3, (
        f"expected exactly 3 record_business_event(...) calls with a literal event_payload in "
        f"interactions/service.py (create/update/delete), found {len(call_sites)}. If a call "
        "site was added or removed, update this count deliberately."
    )


# ===========================================================================
# The guard driven with synthetic bad input
# ===========================================================================


def test_the_guard_accepts_a_payload_using_only_safe_keys() -> None:
    source = (
        "def create_interaction(db):\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_name='InteractionRecorded',\n"
        "        event_payload={'linked_record_type': x, 'channel_code': y},\n"
        "    )\n"
    )
    assert_event_payloads_use_only_safe_keys(source, safe_keys=SAFE_EVENT_PAYLOAD_KEYS)


def test_the_guard_rejects_body_text_in_the_payload() -> None:
    source = (
        "def create_interaction(db):\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_payload={'linked_record_type': x, 'body_text': row['body_text']},\n"
        "    )\n"
    )
    with pytest.raises(AssertionError) as exc:
        assert_event_payloads_use_only_safe_keys(source, safe_keys=SAFE_EVENT_PAYLOAD_KEYS)
    assert "body_text" in str(exc.value)


def test_the_guard_rejects_subject_in_the_payload() -> None:
    source = (
        "def create_interaction(db):\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_payload={'subject': row['subject']},\n"
        "    )\n"
    )
    with pytest.raises(AssertionError) as exc:
        assert_event_payloads_use_only_safe_keys(source, safe_keys=SAFE_EVENT_PAYLOAD_KEYS)
    assert "subject" in str(exc.value)


def test_the_guard_rejects_a_participant_address_in_the_payload() -> None:
    source = (
        "def create_interaction(db):\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_payload={'address_or_number': participant['address_or_number']},\n"
        "    )\n"
    )
    with pytest.raises(AssertionError) as exc:
        assert_event_payloads_use_only_safe_keys(source, safe_keys=SAFE_EVENT_PAYLOAD_KEYS)
    assert "address_or_number" in str(exc.value)


def test_the_guard_flags_a_dynamically_built_payload_as_unrecognised() -> None:
    """Documents the scan's real limitation (it cannot see into a variable or function call)
    and proves the limitation fails CLOSED: an unverifiable call site is flagged, not skipped."""
    source = (
        "def create_interaction(db):\n"
        "    payload = build_payload(row)\n"
        "    record_business_event(db, event_payload=payload)\n"
    )
    with pytest.raises(AssertionError):
        assert_event_payloads_use_only_safe_keys(source, safe_keys=SAFE_EVENT_PAYLOAD_KEYS)


def test_the_guard_flags_a_non_literal_key_as_unrecognised() -> None:
    source = (
        "def create_interaction(db):\n"
        "    record_business_event(db, event_payload={some_variable_key: 'value'})\n"
    )
    with pytest.raises(AssertionError):
        assert_event_payloads_use_only_safe_keys(source, safe_keys=SAFE_EVENT_PAYLOAD_KEYS)


def test_the_guard_finds_record_business_event_called_via_a_module_attribute() -> None:
    """A call spelled `events_service.record_business_event(...)` must be found too, not only
    the bare-name form actually used in this module today."""
    source = (
        "def create_interaction(db):\n"
        "    events_service.record_business_event(db, event_payload={'body_text': 'leak'})\n"
    )
    call_sites = _find_event_payload_dict_keys(source)
    assert len(call_sites) == 1
    with pytest.raises(AssertionError):
        assert_event_payloads_use_only_safe_keys(source, safe_keys=SAFE_EVENT_PAYLOAD_KEYS)


def test_the_known_restricted_keys_are_all_actually_excluded_from_the_safe_set() -> None:
    """Cross-check between the two lists at the top of this file: every key named as
    'known restricted' must genuinely be absent from the safe allowlist, or the explicit error
    message for that key would never fire."""
    overlap = KNOWN_RESTRICTED_KEYS & SAFE_EVENT_PAYLOAD_KEYS
    assert overlap == set(), f"key(s) listed as both safe and restricted: {sorted(overlap)}"


# ===========================================================================
# Runtime proof: a real create call, real restricted content, real database row
# ===========================================================================


def test_a_real_recorded_interaction_leaves_no_restricted_content_in_its_event_row() -> None:
    """The static guard above proves the source code cannot express a leak. This proves the
    running system does not produce one either - the two are independent proofs of the same
    property, the same double-check pattern PF-1A-E1's PROOF A/PROOF B pair already uses."""
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        marker_body = "RUNTIME-GUARD-MARKER-BODY"
        marker_subject = "RUNTIME-GUARD-MARKER-SUBJECT"
        marker_address = "runtime-guard-marker@example.com"

        response = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "EMAIL",
                "direction_code": "INBOUND",
                "occurred_at": _iso_now(),
                "subject": marker_subject,
                "body_text": marker_body,
                "participants": [{"party_role_code": "FROM", "address_or_number": marker_address}],
            },
        )
        assert response.status_code == 201
        interaction_public_id = response.json()["interaction"]["public_id"]
        interaction_ids.append(interaction_public_id)

        with SessionLocal() as db:
            row = db.execute(
                text(
                    "SELECT event_payload_json FROM business_event "
                    "WHERE event_name = 'InteractionRecorded' AND record_public_id = :public_id"
                ),
                {"public_id": interaction_public_id},
            ).first()
        assert row is not None
        payload_text = row[0] or ""
        assert marker_body not in payload_text
        assert marker_subject not in payload_text
        assert marker_address not in payload_text
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )
