"""Entered times (October 2026): a date and time typed in India's time comes back as the same time, and the API refuses
one with no zone.

Found in the Slice 4G screen check (11 October 2026): a market rate's "Collected at" typed as 10:30 showed 4:00 pm.
The offer page sent the India time typed with no zone, the API stored it as if it were UTC, and the screen read it as
UTC. The screen now sends the typed time as a UTC instant with its zone (`frontend/src/components/enteredDateTime.ts`),
the API refuses a time without one (`app/shared/zoned_datetime.py`), and the CRM tables keep UTC. These tests send what
the screen sends and read back what the screen reads.
"""

from __future__ import annotations

import typing
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.dependencies.utils import get_flat_dependant
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.main import app
from app.shared.business_time import BUSINESS_TIME_ZONE
from app.shared.zoned_datetime import ZONELESS_DATETIME_MESSAGE, in_utc, written_with_zone
from tests.offer_version_test_support import offer_row_version
from tests.test_commercial_offers_api import (
    auth_headers,
    cleanup_test_records,
    client,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    create_test_offer_line,
)
from tests.test_interactions_api import _cleanup_interactions
from tests.test_leads_api import cleanup_test_leads, create_test_lead

# 10:30 typed on 12 October 2026, as enteredDateTime.ts sends it; the same moment written with India's offset; what
# the API sends back (UTC, no zone - TB-1 TB1-401), which the screen shows as "12 Oct 2026, 10:30 am"; and the typed
# time with no zone, which is what the offer page used to send.
BROWSER_SENDS = "2026-10-12T05:00:00.000Z"
WITH_INDIA_OFFSET = "2026-10-12T10:30:00+05:30"
STORED_UTC = "2026-10-12T05:00:00"
ZONELESS = "2026-10-12T10:30:00"
# The same moment as seconds since 1970, which Pydantic alone would read as UTC: a number, and digits as text.
EPOCH_SECONDS = 1791781200
EPOCH_TEXT = "1791781200"


def _india_time(returned: str) -> str:
    """What the screen shows for a returned time, as the day and the 24-hour time in India (formatDateTime's rule: a
    time with no zone is UTC)."""
    moment = datetime.fromisoformat(returned.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(BUSINESS_TIME_ZONE).strftime("%Y-%m-%d %H:%M")


def _assert_refused_for_no_zone(response, field: str) -> None:
    assert response.status_code == 422, response.text
    errors = [error for error in response.json()["detail"] if error["loc"][-1] == field]
    assert errors, response.json()
    assert ZONELESS_DATETIME_MESSAGE in errors[0]["msg"]


# --- Every date and time the API takes ----------------------------------------------------------------------------

# Every input that takes a date and time, by route and field. Pinned, so that the walk below finding fewer is noticed
# as surely as one without its zone. A new one is added here when its package adds it.
EXPECTED_DATE_TIME_INPUTS = {
    ("PUT", "/api/commercial-offers/{public_id}", "payload.submitted_at"),
    ("POST", "/api/commercial-offers/{public_id}/pricing-evidence", "payload.collected_at"),
    ("POST", "/api/commercial-offers/{public_id}/submission-evidence", "payload.submitted_at"),
    ("POST", "/api/commercial-offers/{public_id}/credit-review", "payload.reviewed_at"),
    ("POST", "/api/commercial-offers/{public_id}/revisions", "payload.opened_at"),
    ("POST", "/api/commercial-offers/{public_id}/customer-responses", "payload.response_received_at"),
    ("POST", "/api/leads/{public_id}/activities", "payload.activity_at"),
    ("POST", "/api/leads/{public_id}/activities", "payload.next_follow_up_at"),
    ("POST", "/api/interactions", "payload.occurred_at"),
    ("POST", "/api/interactions", "payload.next_follow_up_at"),
    ("PUT", "/api/interactions/{public_id}", "payload.next_follow_up_at"),
    ("GET", "/api/interactions", "occurred_from"),
    ("GET", "/api/interactions", "occurred_to"),
}


def _date_time_inputs(annotation, metadata, path: str, found: list[tuple[str, bool]], seen: frozenset) -> None:
    """Every datetime inside an input's type - through Optional, lists and nested models - and whether it is
    ZonedDateTime (both its checks: `written_with_zone` on the value as sent, `in_utc` on the moment). A plain `date`
    is not a datetime and is not listed."""
    if typing.get_origin(annotation) is typing.Annotated:
        base, *more = typing.get_args(annotation)
        _date_time_inputs(base, [*metadata, *more], path, found, seen)
        return
    if annotation is datetime:
        checks = {getattr(item, "func", None) for item in metadata}
        found.append((path, {written_with_zone, in_utc} <= checks))
        return
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if annotation in seen:
            return
        for name, field in annotation.model_fields.items():
            _date_time_inputs(field.annotation, field.metadata, f"{path}.{name}", found, seen | {annotation})
        return
    for argument in typing.get_args(annotation):
        _date_time_inputs(argument, [], path, found, seen)


def _every_date_time_input() -> dict[tuple[str, str, str], bool]:
    inputs: dict[tuple[str, str, str], bool] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        dependant = get_flat_dependant(route.dependant)
        params = [
            *dependant.path_params,
            *dependant.query_params,
            *dependant.header_params,
            *dependant.cookie_params,
            *dependant.body_params,
        ]
        for param in params:
            found: list[tuple[str, bool]] = []
            _date_time_inputs(param.field_info.annotation, param.field_info.metadata, param.name, found, frozenset())
            for path, zoned in found:
                for method in route.methods:
                    inputs[(method, route.path, path)] = zoned
    return inputs


def test_every_date_and_time_the_api_takes_must_carry_its_zone() -> None:
    inputs = _every_date_time_input()
    assert sorted(key for key, zoned in inputs.items() if not zoned) == []
    assert set(inputs) == EXPECTED_DATE_TIME_INPUTS


def test_in_utc_converts_an_offset_and_refuses_no_zone() -> None:
    india = timezone(timedelta(hours=5, minutes=30))
    assert in_utc(datetime(2026, 10, 12, 10, 30, tzinfo=india)) == datetime(2026, 10, 12, 5, 0, tzinfo=timezone.utc)
    assert in_utc(datetime(2026, 10, 12, 10, 30, tzinfo=india)).utcoffset() == timedelta(0)
    with pytest.raises(ValueError, match="with its time zone"):
        in_utc(datetime(2026, 10, 12, 10, 30))


@pytest.mark.parametrize(
    "value",
    ["2026-10-12T05:00:00.000Z", "2026-10-12T05:00:00Z", "2026-10-12T10:30:00+05:30", "2026-10-12T10:30+0530"],
)
def test_text_with_its_zone_passes_the_first_check(value: str) -> None:
    assert written_with_zone(value) == value


@pytest.mark.parametrize(
    "value",
    [ZONELESS, "2026-10-12T10:30", "2026-10-12", EPOCH_SECONDS, float(EPOCH_SECONDS), EPOCH_TEXT, "", None, b"x"],
)
def test_anything_but_text_with_its_zone_or_a_datetime_is_refused(value: object) -> None:
    with pytest.raises(ValueError, match="with its time zone"):
        written_with_zone(value)
    # A datetime made in code passes the first check; the second then decides on its zone.
    assert written_with_zone(datetime(2026, 10, 12, 10, 30)) == datetime(2026, 10, 12, 10, 30)


# --- The offer page: header, market rate, submission evidence, credit review, customer response --------------------


@pytest.fixture()
def linked_offer():
    records = {"leads": [], "accounts": [], "opportunities": [], "offers": []}
    linked = create_account_linked_test_opportunity()
    records["leads"].append(str(linked["lead"]["public_id"]))
    records["accounts"].append(str(linked["account"]["public_id"]))
    records["opportunities"].append(str(linked["opportunity"]["public_id"]))
    try:
        offer_public_id = str(create_test_commercial_offer(str(linked["opportunity"]["public_id"]))["public_id"])
        records["offers"].append(offer_public_id)
        yield offer_public_id
    finally:
        cleanup_test_records(
            opportunity_public_ids=records["opportunities"],
            offer_public_ids=records["offers"],
            account_public_ids=records["accounts"],
            lead_public_ids=records["leads"],
        )


def _count(path: str) -> int:
    response = client.get(path, headers=auth_headers("sales1"))
    assert response.status_code == 200
    return len(response.json())


def test_offer_times_typed_in_india_come_back_as_typed_and_dates_are_unchanged(linked_offer: str) -> None:
    offer = f"/api/commercial-offers/{linked_offer}"

    # The header's "Submitted at", saved with the offer's dates: the time comes back as typed, the dates as entered.
    header = {"offer_date": "2026-10-01", "valid_until": "2026-11-30"}
    refused = client.put(
        offer,
        headers=auth_headers("sales1"),
        json={"expected_row_version": offer_row_version(linked_offer), **header, "submitted_at": ZONELESS},
    )
    _assert_refused_for_no_zone(refused, "submitted_at")
    saved = client.put(
        offer,
        headers=auth_headers("sales1"),
        json={"expected_row_version": offer_row_version(linked_offer), **header, "submitted_at": BROWSER_SENDS},
    )
    assert saved.status_code == 200, saved.text
    header_offer = saved.json()["commercial_offer"]
    assert header_offer["submitted_at"] == STORED_UTC
    assert _india_time(header_offer["submitted_at"]) == "2026-10-12 10:30"
    assert (header_offer["offer_date"], header_offer["valid_until"]) == ("2026-10-01", "2026-11-30")

    # A line's market rate, "Collected at".
    line_public_id = str(create_test_offer_line(linked_offer)["public_id"])
    rate = {
        "line_public_id": line_public_id,
        "evidence_type": "market_rate",
        "equipment_service_description": "80T crawler crane with operator",
        "rate_amount": "95000.00",
        "rate_basis": "per_day",
    }
    rates_before = _count(f"{offer}/pricing-evidence")
    for no_zone in (ZONELESS, EPOCH_SECONDS, EPOCH_TEXT):
        _assert_refused_for_no_zone(
            client.post(
                f"{offer}/pricing-evidence", headers=auth_headers("sales1"), json={**rate, "collected_at": no_zone}
            ),
            "collected_at",
        )
    assert _count(f"{offer}/pricing-evidence") == rates_before
    recorded = client.post(
        f"{offer}/pricing-evidence", headers=auth_headers("sales1"), json={**rate, "collected_at": BROWSER_SENDS}
    )
    assert recorded.status_code == 201, recorded.text
    assert recorded.json()["pricing_evidence"]["collected_at"] == STORED_UTC
    offset_rate = client.post(
        f"{offer}/pricing-evidence", headers=auth_headers("sales1"), json={**rate, "collected_at": WITH_INDIA_OFFSET}
    )
    assert offset_rate.status_code == 201, offset_rate.text
    assert offset_rate.json()["pricing_evidence"]["collected_at"] == STORED_UTC

    # Submission evidence, "Submitted at".
    evidence = {"submission_reference": f"SUB-TZ-{uuid4()}", "submission_channel": "EMAIL"}
    _assert_refused_for_no_zone(
        client.post(
            f"{offer}/submission-evidence", headers=auth_headers("sales1"), json={**evidence, "submitted_at": ZONELESS}
        ),
        "submitted_at",
    )
    assert _count(f"{offer}/submission-evidence") == 0
    sent = client.post(
        f"{offer}/submission-evidence", headers=auth_headers("sales1"), json={**evidence, "submitted_at": BROWSER_SENDS}
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["submission_evidence"]["submitted_at"] == STORED_UTC

    # The credit review, "Reviewed at".
    review = {"review_status": "WITHIN_LIMIT_AS_PER_MANUAL_REVIEW", "review_reference": f"CREDIT-TZ-{uuid4()}"}
    _assert_refused_for_no_zone(
        client.post(f"{offer}/credit-review", headers=auth_headers("sales1"), json={**review, "reviewed_at": ZONELESS}),
        "reviewed_at",
    )
    assert _count(f"{offer}/credit-review") == 0
    reviewed = client.post(
        f"{offer}/credit-review", headers=auth_headers("sales1"), json={**review, "reviewed_at": BROWSER_SENDS}
    )
    assert reviewed.status_code == 201, reviewed.text
    assert reviewed.json()["credit_review"]["reviewed_at"] == STORED_UTC

    # Recorded as sent: the header takes the submission evidence's time, still as typed.
    marked = client.post(f"{offer}/mark-submitted", headers=auth_headers("sales1"))
    assert marked.status_code == 200, marked.text
    assert marked.json()["commercial_offer"]["submitted_at"] == STORED_UTC
    assert marked.json()["commercial_offer"]["valid_until"] == "2026-11-30"


def test_a_customer_response_keeps_its_time_and_its_day_in_india(linked_offer: str) -> None:
    offer = f"/api/commercial-offers/{linked_offer}"
    create_test_offer_line(linked_offer)
    evidence = client.post(
        f"{offer}/submission-evidence",
        headers=auth_headers("sales1"),
        json={"submission_reference": f"SUB-TZ-{uuid4()}", "submission_channel": "EMAIL", "submitted_at": BROWSER_SENDS},
    )
    assert evidence.status_code == 201, evidence.text
    assert client.post(f"{offer}/mark-submitted", headers=auth_headers("sales1")).status_code == 200

    response = {"response_outcome": "ACCEPTED_AWARDED", "response_channel": "EMAIL", "response_reference": "LOA-TZ"}
    _assert_refused_for_no_zone(
        client.post(
            f"{offer}/customer-responses",
            headers=auth_headers("manager1"),
            json={**response, "response_received_at": "2026-10-12T00:30:00"},
        ),
        "response_received_at",
    )
    assert _count(f"{offer}/customer-responses") == 0

    # Half past midnight in India on 12 October is still 11 October in UTC; the outcome's day is India's.
    accepted = client.post(
        f"{offer}/customer-responses",
        headers=auth_headers("manager1"),
        json={**response, "response_received_at": "2026-10-11T19:00:00.000Z"},
    )
    assert accepted.status_code == 201, accepted.text
    body = accepted.json()
    assert body["customer_response"]["response_received_at"] == "2026-10-11T19:00:00"
    assert _india_time(body["customer_response"]["response_received_at"]) == "2026-10-12 00:30"
    assert body["commercial_offer"]["offer_status_code"] == "ACCEPTED"
    assert body["commercial_offer"]["outcome_date"] == "2026-10-12"
    assert body["commercial_offer"]["valid_until"] == "2026-08-15"


# --- A Lead's activity --------------------------------------------------------------------------------------------


def test_a_lead_activity_keeps_its_times() -> None:
    lead_public_ids: list[str] = []
    try:
        lead_public_id = str(create_test_lead()["public_id"])
        lead_public_ids.append(lead_public_id)
        activities = f"/api/leads/{lead_public_id}/activities"
        activity = {"activity_type": "CALL", "notes": "Entered-time check."}

        for field in ("activity_at", "next_follow_up_at"):
            for no_zone in (ZONELESS, EPOCH_SECONDS):
                _assert_refused_for_no_zone(
                    client.post(activities, headers=auth_headers("sales1"), json={**activity, field: no_zone}), field
                )
        assert _count(activities) == 0

        recorded = client.post(
            activities,
            headers=auth_headers("sales1"),
            json={**activity, "activity_at": BROWSER_SENDS, "next_follow_up_at": WITH_INDIA_OFFSET},
        )
        assert recorded.status_code == 201, recorded.text
        saved = recorded.json()["activity"]
        assert (saved["activity_at"], saved["next_follow_up_at"]) == (STORED_UTC, STORED_UTC)
        assert _india_time(saved["activity_at"]) == "2026-10-12 10:30"
    finally:
        cleanup_test_leads(lead_public_ids)


# --- The shared conversation log ---------------------------------------------------------------------------------


def test_a_conversation_keeps_its_times_and_its_filters_need_a_zone() -> None:
    chain = create_account_linked_test_opportunity()
    opportunity_public_id = str(chain["opportunity"]["public_id"])
    interaction_public_ids: list[str] = []
    try:
        conversation = {
            "linked_record_type": "opportunity",
            "linked_record_public_id": opportunity_public_id,
            "channel_code": "CALL",
            "direction_code": "OUTBOUND",
            "subject": "Entered-time check",
        }
        for field in ("occurred_at", "next_follow_up_at"):
            for no_zone in (ZONELESS, EPOCH_SECONDS):
                values = {"occurred_at": BROWSER_SENDS, field: no_zone}
                _assert_refused_for_no_zone(
                    client.post("/api/interactions", headers=auth_headers("sales1"), json={**conversation, **values}),
                    field,
                )

        recorded = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={**conversation, "occurred_at": BROWSER_SENDS, "next_follow_up_at": WITH_INDIA_OFFSET},
        )
        assert recorded.status_code == 201, recorded.text
        saved = recorded.json()["interaction"]
        interaction_public_ids.append(saved["public_id"])
        assert _india_time(saved["occurred_at"]) == "2026-10-12 10:30"
        assert _india_time(saved["next_follow_up_at"]) == "2026-10-12 10:30"

        _assert_refused_for_no_zone(
            client.put(
                f"/api/interactions/{saved['public_id']}",
                headers=auth_headers("sales1"),
                json={"next_follow_up_at": ZONELESS},
            ),
            "next_follow_up_at",
        )

        listing = {"linked_record_type": "opportunity", "linked_record_public_id": opportunity_public_id}
        for field in ("occurred_from", "occurred_to"):
            for no_zone in (ZONELESS, EPOCH_TEXT):
                _assert_refused_for_no_zone(
                    client.get("/api/interactions", headers=auth_headers("sales1"), params={**listing, field: no_zone}),
                    field,
                )
        found = client.get(
            "/api/interactions",
            headers=auth_headers("sales1"),
            params={**listing, "occurred_from": "2026-10-12T10:30:00+05:30", "occurred_to": "2026-10-12T05:00:00Z"},
        )
        assert found.status_code == 200, found.text
        assert [item["public_id"] for item in found.json()] == [saved["public_id"]]
    finally:
        _cleanup_interactions(interaction_public_ids)
        cleanup_test_records(
            opportunity_public_ids=[opportunity_public_id],
            offer_public_ids=[],
            account_public_ids=[str(chain["account"]["public_id"])],
            lead_public_ids=[str(chain["lead"]["public_id"])],
        )
