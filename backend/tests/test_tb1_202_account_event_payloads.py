"""TB-1 TB1-202: the Accounts service's business events carry no restricted value.

AccountGstinCaptured carried the whole GSTIN, whose characters 3 to 12 are the holder's PAN, and
AccountContactCreated carried the contact person's name. DATA_CLASSIFICATION_AND_HANDLING.md classes
both as restricted personal/statutory data, with "no real values in fixtures/logs/events", and the
event log is append-only: nothing written there can be taken back. Owner's decision, 7 October 2026:
the GSTIN event records the GSTIN's public id and state code, the contact event the contact's public
id.

Two layers, as Slice 9D's guard for interactions (whose scanner this file reuses):

- a fail-closed allowlist over every `record_business_event(...)` call in accounts/service.py, so a
  restricted key added to any Account event later fails here whatever it is called; and, since the
  first review round, a check that no call passes the user's own text - `remarks` or `reason` other
  than a fixed string - where a PAN, a GSTIN or a name could be typed (TB1-202 round 1: the events
  used to copy the remarks sent with a GSTIN or contact into the event's `remarks` column);
- the GSTIN, contact and PAN-profile events written through the real routes with those values in the
  remarks too, read back from `business_event`.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from tests.test_accounts_api import (
    auth_headers,
    cleanup_test_records,
    client,
    create_test_account,
    unique_gstin,
)
from tests.test_slice_9d_interaction_event_payloads import (
    _find_event_payload_dict_keys,
    assert_event_payloads_use_only_safe_keys,
)

ACCOUNTS_SERVICE_PATH = Path(__file__).resolve().parents[1] / "app" / "modules" / "accounts" / "service.py"

# Every key an event_payload literal in accounts/service.py may use: references, codes, flags and
# the address's city and state (TB1-202 records that the address event carries no street address).
# Adding a key here must be a deliberate, reviewed decision.
SAFE_ACCOUNT_EVENT_PAYLOAD_KEYS = frozenset(
    {
        "account_public_id",
        "party_type",
        "account_status_code",
        "qualification_source",
        "contact_public_id",
        "is_primary",
        "address_type_code",
        "city",
        "state",
        "pan_present",
        "pan_verification_state_code",
        "gstin_public_id",
        "state_code",
        "gstin_verification_state_code",
        "owner_before",
        "owner_after",
        "segment",
        "industry",
        "is_strategic_account",
        "document_type",
        "storage_mode",
        "status",
    }
)


def test_every_account_event_payload_uses_only_safe_keys() -> None:
    source = ACCOUNTS_SERVICE_PATH.read_text(encoding="utf-8-sig")
    assert_event_payloads_use_only_safe_keys(source, safe_keys=SAFE_ACCOUNT_EVENT_PAYLOAD_KEYS)


def test_the_scan_found_every_account_event() -> None:
    """The allowlist above is vacuous if the scanner finds nothing: account created, classification
    changed, contact, address, PAN profile, GSTIN and document - seven calls, each with a literal
    payload."""
    call_sites = _find_event_payload_dict_keys(ACCOUNTS_SERVICE_PATH.read_text(encoding="utf-8-sig"))
    assert len(call_sites) == 7, f"expected 7 record_business_event calls in accounts/service.py, found {len(call_sites)}"


@pytest.mark.parametrize("restricted_key", ["gstin", "contact_name", "pan"])
def test_the_allowlist_refuses_the_restricted_values(restricted_key: str) -> None:
    """The keys the two events carried before TB1-202, and the PAN itself, are not in the allowlist:
    put back into an Account event, the guard above fails."""
    source = (
        "def create_account_gstin(db):\n"
        "    record_business_event(\n"
        "        db,\n"
        f"        event_payload={{'account_public_id': 'a', '{restricted_key}': 'x'}},\n"
        "    )\n"
    )
    with pytest.raises(AssertionError, match=restricted_key):
        assert_event_payloads_use_only_safe_keys(source, safe_keys=SAFE_ACCOUNT_EVENT_PAYLOAD_KEYS)


# The record_business_event arguments that are text a person could have typed: each must be a fixed
# string (or absent). The other arguments are names, ids, codes and the payload checked above.
FREE_TEXT_ARGUMENTS = ("remarks", "reason", "correlation_id")


def _free_text_arguments_not_fixed(source: str) -> list[str]:
    """Each `record_business_event(...)` call's text argument that is not a string literal or None."""
    offenders: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not ((isinstance(func, ast.Name) and func.id == "record_business_event") or (
            isinstance(func, ast.Attribute) and func.attr == "record_business_event"
        )):
            continue
        for keyword in node.keywords:
            if keyword.arg is None:
                offenders.append(f"line {node.lineno}: **unpacked arguments")
            elif keyword.arg in FREE_TEXT_ARGUMENTS and not (
                isinstance(keyword.value, ast.Constant) and (keyword.value.value is None or isinstance(keyword.value.value, str))
            ):
                offenders.append(f"line {node.lineno}: {keyword.arg}={ast.unparse(keyword.value)}")
    return offenders


def test_no_account_event_copies_text_a_user_typed() -> None:
    assert _free_text_arguments_not_fixed(ACCOUNTS_SERVICE_PATH.read_text(encoding="utf-8-sig")) == []


@pytest.mark.parametrize(
    "argument", ['remarks=values.get("remarks")', 'reason=payload.reason', "**extra", 'correlation_id=values["note"]']
)
def test_the_free_text_check_refuses_a_value_from_the_request(argument: str) -> None:
    source = f"def create_account_gstin(db):\n    record_business_event(db, reason='fixed', {argument})\n"
    assert _free_text_arguments_not_fixed(source) != []


def _stored_event(event_name: str, record_public_id: str) -> dict[str, object]:
    with SessionLocal() as db:
        row = db.execute(
            text(
                "SELECT * FROM business_event WHERE event_name = :event_name AND record_public_id = :record_public_id"
            ),
            {"event_name": event_name, "record_public_id": record_public_id},
        ).mappings().one()
    return dict(row)


def test_the_gstin_contact_and_pan_events_hold_public_ids_not_the_values() -> None:
    """The values are sent where they belong and again in each request's free-text remarks, which a
    user may fill with anything; no event row may hold them in any column."""
    gstin_value = unique_gstin()
    pan_in_gstin = gstin_value[2:12]
    contact_name = "Tb1 Two Zero Two Contact Person"
    remarks = f"GSTIN {gstin_value}, PAN {pan_in_gstin}, ask for {contact_name}"
    account_ids: list[str] = []
    gstin_ids: list[str] = []
    contact_ids: list[str] = []
    tax_profile_ids: list[str] = []
    try:
        account_public_id = str(create_test_account("sales1")["public_id"])
        account_ids.append(account_public_id)

        gstin_response = client.post(
            f"/api/accounts/{account_public_id}/gstins",
            headers=auth_headers("sales1"),
            json={
                "gstin": gstin_value,
                "gstin_verification_state_code": "ENTERED_NOT_VERIFIED",
                "state_name": "Karnataka",
                "is_primary": True,
                "remarks": remarks,
            },
        )
        assert gstin_response.status_code == 201
        gstin_public_id = gstin_response.json()["gstin"]["public_id"]
        gstin_ids.append(gstin_public_id)
        assert gstin_response.json()["gstin"]["remarks"] == remarks  # kept on the record itself

        contact_response = client.post(
            f"/api/accounts/{account_public_id}/contacts",
            headers=auth_headers("sales1"),
            json={"contact_name": contact_name, "is_primary": True, "remarks": remarks},
        )
        assert contact_response.status_code == 201
        contact_public_id = contact_response.json()["contact"]["public_id"]
        contact_ids.append(contact_public_id)

        profile_response = client.post(
            f"/api/accounts/{account_public_id}/tax-profile",
            headers=auth_headers("sales1"),
            json={"pan": pan_in_gstin, "pan_verification_state_code": "ENTERED_NOT_VERIFIED", "remarks": remarks},
        )
        assert profile_response.status_code == 200
        tax_profile_public_id = profile_response.json()["tax_profile"]["public_id"]
        tax_profile_ids.append(tax_profile_public_id)

        gstin_event = _stored_event("AccountGstinCaptured", gstin_public_id)
        assert json.loads(gstin_event["event_payload_json"]) == {
            "account_public_id": account_public_id,
            "gstin_public_id": gstin_public_id,
            "state_code": "29",
            "gstin_verification_state_code": "ENTERED_NOT_VERIFIED",
            "is_primary": True,
        }
        contact_event = _stored_event("AccountContactCreated", contact_public_id)
        assert json.loads(contact_event["event_payload_json"]) == {
            "account_public_id": account_public_id,
            "contact_public_id": contact_public_id,
            "is_primary": True,
        }

        profile_event = _stored_event("AccountTaxProfileCaptured", tax_profile_public_id)
        assert json.loads(profile_event["event_payload_json"]) == {
            "account_public_id": account_public_id,
            "pan_present": True,
            "pan_verification_state_code": "ENTERED_NOT_VERIFIED",
        }

        # Nowhere in any of the three stored rows, in any column - remarks included.
        for row in (gstin_event, contact_event, profile_event):
            assert row["remarks"] is None
            stored = " ".join(str(value) for value in row.values())
            assert gstin_value not in stored
            assert pan_in_gstin not in stored
            assert contact_name not in stored
    finally:
        cleanup_test_records(
            account_public_ids=account_ids,
            contact_public_ids=contact_ids,
            gstin_public_ids=gstin_ids,
            tax_profile_public_ids=tax_profile_ids,
        )
