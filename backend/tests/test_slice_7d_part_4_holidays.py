"""Slice 7D Part 4 - the holidays a Work Order names; since HOL-1, its changes to PBL's holiday calendar.

Each test maps to an item in the "Test plan" of docs/agent/slices/slice-7d-part-4-remaining-billing-terms.md, as
carried into docs/agent/slices/hol-1-holiday-calendar.md, section 14. The rules come from the owner's answer 25 of
17-18 September 2026 and decisions 27 and 29 of 24 September 2026 - one list on the Work Order, for every line; an
explicit answer beside it, so a recorded "no change" is never mistaken for "not entered"; and every date checked
against the contract, as Part 3 checks a billing period's start - and from HOL-1 (owner, 2 October 2026): the answer
reworded ("follows PBL's calendar unchanged" / "changes it as listed") and each change either a holiday added or a
calendar holiday made a working day, charged at the normal or the overtime rate (Q4).

The three-line chain fixture and the contract-period helpers are Part 3's, imported rather than rebuilt. Business
events need no explicit cleanup: conftest removes every event created by the session.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from tests.test_commercial_offers_api import auth_headers, client
from tests.test_slice_7d_part_3_contract_period import (  # noqa: F401  (chain is a fixture)
    NON_WRITE_ROLES,
    READ_ROLES,
    WRITE_ROLES,
    _events,
    _extend,
    _extension_ids,
    _remove_extension,
    _save_period,
    chain,
)

UNCHANGED = "CALENDAR_UNCHANGED"
CHANGED = "CALENDAR_CHANGED"

LIST_KEYS = {
    "work_order_public_id",
    "holiday_list_public_id",
    "list_version",
    "holidays_answer_code",
    "changes",
    "is_complete",
    "missing_items",
    "updated_by",
    "updated_by_display_name",
    "updated_at",
}
CHANGE_KEYS = {"change_public_id", "change_code", "holiday_date", "holiday_kind_code", "working_day_rate_code", "description"}

REPUBLIC_DAY = {"change_code": "HOLIDAY_ADDED", "holiday_date": "2027-01-26", "holiday_kind_code": "NATIONAL", "description": "Republic Day"}
HOLI = {"change_code": "HOLIDAY_ADDED", "holiday_date": "2027-03-22", "holiday_kind_code": "FESTIVAL", "description": "Holi"}
PONGAL = {"change_code": "HOLIDAY_ADDED", "holiday_date": "2027-01-15", "holiday_kind_code": "FESTIVAL", "description": "Pongal"}
# A calendar holiday the Work Order works (HOL-1, Q4).
HOLI_WORKED = {"change_code": "WORKING_DAY", "holiday_date": "2027-03-22", "working_day_rate_code": "OVERTIME_RATE", "description": "Plant runs"}
GUDI_PADWA_WORKED = {"change_code": "WORKING_DAY", "holiday_date": "2027-03-08", "working_day_rate_code": "NORMAL_RATE"}


def _url(chain) -> str:
    return f"/api/work-orders/{chain['work_order_public_id']}/holidays"


def _get(chain, username: str = "sales1"):
    return client.get(_url(chain), headers=auth_headers(username))


def _save(
    chain,
    *,
    answer: str | None = CHANGED,
    changes: list[dict] | None = None,
    expected_list_version: int | None = None,
    username: str = "sales1",
):
    body = {"expected_list_version": expected_list_version, "changes": changes or []}
    if answer is not None:
        body["holidays_answer_code"] = answer
    return client.put(_url(chain), headers=auth_headers(username), json=body)


def _stored_list_count(work_order_public_id: str) -> tuple[int, int]:
    """How many list rows and change rows this Work Order holds, read straight from the tables."""
    with SessionLocal() as db:
        lists = db.execute(
            text(
                "SELECT COUNT(*) FROM crm_work_order_holiday_list l JOIN crm_work_order wo ON wo.id = l.work_order_id "
                "WHERE wo.work_order_public_id = :id"
            ),
            {"id": work_order_public_id},
        ).scalar_one()
        dates = db.execute(
            text(
                "SELECT COUNT(*) FROM crm_work_order_holiday h "
                "JOIN crm_work_order_holiday_list l ON l.id = h.work_order_holiday_list_id "
                "JOIN crm_work_order wo ON wo.id = l.work_order_id WHERE wo.work_order_public_id = :id"
            ),
            {"id": work_order_public_id},
        ).scalar_one()
    return int(lists), int(dates)


# --- Not answered, answered "unchanged", and changed ---------------------------------------------------------------


def test_a_work_order_with_no_answer_reports_its_holidays_missing(chain) -> None:
    response = _get(chain)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == LIST_KEYS
    assert body["holidays_answer_code"] is None
    assert body["list_version"] is None
    assert body["changes"] == []
    assert body["is_complete"] is False
    assert body["missing_items"] == ["HOLIDAYS"]


def test_follows_the_calendar_unchanged_is_a_recorded_answer_not_a_missing_one(chain) -> None:
    """Decision 29: an empty list alone could not tell "no change" from "not entered"; the answer does."""
    response = _save(chain, answer=UNCHANGED)
    assert response.status_code == 200, response.text
    body = response.json()["holiday_list"]
    assert body["holidays_answer_code"] == UNCHANGED
    assert body["changes"] == []
    assert body["is_complete"] is True
    assert body["missing_items"] == []
    assert body["list_version"] == 1
    assert response.json()["event"]["event_name"] == "WorkOrderHolidaysRecorded"


def test_changes_the_calendar_with_none_entered_is_still_missing(chain) -> None:
    response = _save(chain, answer=CHANGED, changes=[])
    assert response.status_code == 200, response.text
    body = response.json()["holiday_list"]
    assert body["holidays_answer_code"] == CHANGED
    assert body["is_complete"] is False
    assert body["missing_items"] == ["HOLIDAYS"]


def test_added_holidays_are_recorded_in_date_order(chain) -> None:
    response = _save(chain, changes=[HOLI, REPUBLIC_DAY, PONGAL])
    assert response.status_code == 200, response.text
    body = response.json()["holiday_list"]
    assert body["is_complete"] is True
    assert [item["holiday_date"] for item in body["changes"]] == ["2027-01-15", "2027-01-26", "2027-03-22"]
    assert [item["holiday_kind_code"] for item in body["changes"]] == ["FESTIVAL", "NATIONAL", "FESTIVAL"]
    assert {item["change_code"] for item in body["changes"]} == {"HOLIDAY_ADDED"}
    assert [item["working_day_rate_code"] for item in body["changes"]] == [None, None, None]
    assert body["changes"][1]["description"] == "Republic Day"
    assert set(body["changes"][0]) == CHANGE_KEYS
    assert body["updated_by_display_name"]
    assert _get(chain).json() == body


@pytest.mark.parametrize("rate", ["NORMAL_RATE", "OVERTIME_RATE"])
def test_a_calendar_holiday_made_a_working_day_is_recorded_with_its_rate(chain, rate: str) -> None:
    """Q4: a festival the Work Order works is charged at the normal or the overtime rate. It has no kind of its own:
    it is PBL's calendar holiday on that date."""
    response = _save(chain, changes=[{**HOLI_WORKED, "working_day_rate_code": rate}, REPUBLIC_DAY])
    assert response.status_code == 200, response.text
    body = response.json()["holiday_list"]
    assert body["is_complete"] is True
    worked = body["changes"][1]
    assert (worked["change_code"], worked["holiday_date"], worked["working_day_rate_code"], worked["holiday_kind_code"]) == (
        "WORKING_DAY",
        "2027-03-22",
        rate,
        None,
    )
    assert worked["description"] == "Plant runs"


def test_a_list_of_working_days_alone_is_complete(chain) -> None:
    response = _save(chain, changes=[GUDI_PADWA_WORKED])
    assert response.status_code == 200, response.text
    body = response.json()["holiday_list"]
    assert body["is_complete"] is True and body["missing_items"] == []
    assert body["changes"][0]["description"] is None


def test_a_description_is_optional_and_blank_is_stored_as_none(chain) -> None:
    response = _save(
        chain, changes=[{**REPUBLIC_DAY, "description": "   "}, {**HOLI, "description": None}, {**GUDI_PADWA_WORKED, "description": " "}]
    )
    assert response.status_code == 200, response.text
    assert [item["description"] for item in response.json()["holiday_list"]["changes"]] == [None, None, None]


def test_the_codes_are_accepted_in_any_case(chain) -> None:
    response = _save(
        chain,
        answer="calendar_changed",
        changes=[
            {**REPUBLIC_DAY, "change_code": "holiday_added", "holiday_kind_code": "national"},
            {**HOLI_WORKED, "change_code": "working_day", "working_day_rate_code": "overtime_rate"},
        ],
    )
    assert response.status_code == 200, response.text
    body = response.json()["holiday_list"]
    assert body["holidays_answer_code"] == CHANGED
    assert [(item["change_code"], item["holiday_kind_code"], item["working_day_rate_code"]) for item in body["changes"]] == [
        ("HOLIDAY_ADDED", "NATIONAL", None),
        ("WORKING_DAY", None, "OVERTIME_RATE"),
    ]


# --- What is refused ------------------------------------------------------------------------------------------------


def test_follows_the_calendar_unchanged_cannot_carry_changes(chain) -> None:
    for change in (REPUBLIC_DAY, HOLI_WORKED):
        response = _save(chain, answer=UNCHANGED, changes=[change])
        assert response.status_code == 422
        assert "following PBL's holiday calendar unchanged" in response.json()["detail"]
    assert _stored_list_count(chain["work_order_public_id"]) == (0, 0)


@pytest.mark.parametrize("answer", ["", "   ", "MAYBE", "NONE", "LISTED"])
def test_an_answer_that_is_not_one_of_the_two_is_refused(chain, answer: str) -> None:
    """Part 4's codes NONE and LISTED are gone: the migration rewrote every stored answer (HOL-1)."""
    assert _save(chain, answer=answer).status_code == 422
    assert _stored_list_count(chain["work_order_public_id"]) == (0, 0)


def test_the_answer_is_required(chain) -> None:
    # In words, left out or null alike (HOL1-R4-002).
    choose = "Choose whether the Work Order follows PBL's holiday calendar unchanged, or changes it as listed."
    response = _save(chain, answer=None)
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == choose
    response = client.put(_url(chain), headers=auth_headers("sales1"), json={"holidays_answer_code": None, "changes": []})
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == choose
    assert _stored_list_count(chain["work_order_public_id"]) == (0, 0)


@pytest.mark.parametrize("kind", ["WEEKLY_OFF", "", "COMPANY"])
def test_a_holiday_kind_other_than_national_or_festival_is_refused(chain, kind: str) -> None:
    """Weekly off days are recorded with each line's terms, so they are not a kind on this list."""
    response = _save(chain, changes=[{**REPUBLIC_DAY, "holiday_kind_code": kind}])
    assert response.status_code == 422
    assert "26 January 2027" in response.json()["detail"]
    assert _stored_list_count(chain["work_order_public_id"]) == (0, 0)


@pytest.mark.parametrize("change_code", ["", "REMOVED", "WORK_THROUGH"])
def test_a_change_other_than_a_holiday_added_or_a_working_day_is_refused(chain, change_code: str) -> None:
    response = _save(chain, changes=[{**REPUBLIC_DAY, "change_code": change_code}])
    assert response.status_code == 422
    assert "26 January 2027" in response.json()["detail"]
    assert _stored_list_count(chain["work_order_public_id"]) == (0, 0)


def test_the_change_code_is_required(chain) -> None:
    # In words naming the date, left out or null alike (HOL1-R4-002).
    change = {key: value for key, value in REPUBLIC_DAY.items() if key != "change_code"}
    for given in (change, {**change, "change_code": None}):
        response = _save(chain, changes=[given])
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == "Choose whether 26 January 2027 is a holiday added or a working day."
    assert _stored_list_count(chain["work_order_public_id"]) == (0, 0)


@pytest.mark.parametrize("rate", [None, "", "HOLIDAY_RATE", "DOUBLE"])
def test_a_working_day_without_the_normal_or_overtime_rate_is_refused(chain, rate) -> None:
    response = _save(chain, changes=[{**HOLI_WORKED, "working_day_rate_code": rate}])
    assert response.status_code == 422
    assert "working day on 22 March 2027" in response.json()["detail"]
    assert _stored_list_count(chain["work_order_public_id"]) == (0, 0)


def test_a_working_day_takes_no_kind_and_an_added_holiday_no_rate(chain) -> None:
    worked = _save(chain, changes=[{**HOLI_WORKED, "holiday_kind_code": "FESTIVAL"}])
    assert worked.status_code == 422
    assert worked.json()["detail"] == (
        "The working day on 22 March 2027 takes no kind of its own: it is PBL's calendar holiday on that date."
    )
    added = _save(chain, changes=[{**REPUBLIC_DAY, "working_day_rate_code": "NORMAL_RATE"}])
    assert added.status_code == 422
    assert added.json()["detail"] == (
        "The holiday added on 26 January 2027 takes no rate of its own: it is charged as each line's off-day term says."
    )
    assert _stored_list_count(chain["work_order_public_id"]) == (0, 0)


def test_a_date_listed_twice_is_refused_naming_it(chain) -> None:
    for second in ({**REPUBLIC_DAY, "holiday_kind_code": "FESTIVAL"}, {**HOLI_WORKED, "holiday_date": "2027-01-26"}):
        response = _save(chain, changes=[REPUBLIC_DAY, second])
        assert response.status_code == 422
        assert response.json()["detail"] == (
            "26 January 2027 is listed more than once. A date is either a holiday added or a working day: list it once."
        )


def test_an_unknown_field_is_refused(chain) -> None:
    assert _save(chain, changes=[{**REPUBLIC_DAY, "state": "KA"}]).status_code == 422
    assert _save(chain, changes=[{**REPUBLIC_DAY, "reason": "x"}]).status_code == 422
    response = client.put(_url(chain), headers=auth_headers("sales1"), json={"holidays_answer_code": UNCHANGED, "notes": "x"})
    assert response.status_code == 422
    # Part 4's field name is gone with its shape.
    response = client.put(_url(chain), headers=auth_headers("sales1"), json={"holidays_answer_code": CHANGED, "holidays": []})
    assert response.status_code == 422


def test_a_description_longer_than_255_characters_is_refused(chain) -> None:
    # In words that name the date - never the request validator's list (independent review, HOL1-R3-001).
    response = _save(chain, changes=[{**REPUBLIC_DAY, "description": "x" * 256}])
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "The description of the holiday added on 26 January 2027 is longer than 255 characters."
    response = _save(chain, changes=[{**HOLI_WORKED, "description": "x" * 256}])
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "The note on the working day on 22 March 2027 is longer than 255 characters."
    # A code too long is a code not known, in words too.
    response = _save(chain, changes=[{**REPUBLIC_DAY, "holiday_kind_code": "N" * 51}])
    assert response.status_code == 422, response.text
    assert "26 January 2027" in response.json()["detail"]
    # 255 characters are kept.
    assert _save(chain, changes=[{**REPUBLIC_DAY, "description": "x" * 255}]).status_code == 200


# --- Checked against the contract -----------------------------------------------------------------------------------


def test_a_holiday_before_the_contract_starts_is_refused_naming_both_dates(chain) -> None:
    assert _save_period(chain).status_code == 200  # 1 January to 31 March 2027
    response = _save(chain, changes=[{**REPUBLIC_DAY, "holiday_date": "2026-12-25"}])
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "A holiday is listed on 25 December 2026, before the contract starts on 1 January 2027."
    )


def test_a_working_day_outside_the_contract_is_refused_naming_it_for_what_it_is(chain) -> None:
    assert _save_period(chain).status_code == 200
    response = _save(chain, changes=[{**HOLI_WORKED, "holiday_date": "2026-12-25"}])
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "A working day is listed on 25 December 2026, before the contract starts on 1 January 2027."
    )


def test_a_holiday_after_the_contract_ends_is_refused_naming_both_dates(chain) -> None:
    assert _save_period(chain).status_code == 200
    response = _save(chain, changes=[{**REPUBLIC_DAY, "holiday_date": "2027-04-14"}])
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "A holiday is listed on 14 April 2027, after the contract ends on 31 March 2027."
    )


def test_the_contracts_first_and_last_days_may_be_changed(chain) -> None:
    assert _save_period(chain).status_code == 200
    response = _save(
        chain,
        changes=[
            {"change_code": "HOLIDAY_ADDED", "holiday_date": "2027-01-01", "holiday_kind_code": "FESTIVAL"},
            {"change_code": "WORKING_DAY", "holiday_date": "2027-03-31", "working_day_rate_code": "NORMAL_RATE"},
        ],
    )
    assert response.status_code == 200, response.text


def test_a_holiday_in_a_gap_before_an_extension_is_refused(chain) -> None:
    """Gap days are outside the contract (owner, 22 September 2026), so no change falls on one."""
    assert _save_period(chain).status_code == 200
    extended = _extend(
        chain, new_end_date="2027-06-30", extension_start_date="2027-04-15", gap_confirmed_from="2027-04-01"
    )
    assert extended.status_code == 201, extended.text
    for change in (REPUBLIC_DAY, HOLI_WORKED):
        response = _save(chain, changes=[{**change, "holiday_date": "2027-04-10"}])
        assert response.status_code == 422
        assert "10 April 2027, when no contract runs" in response.json()["detail"]
    # A day in the extension itself is inside the contract.
    assert _save(chain, changes=[{**REPUBLIC_DAY, "holiday_date": "2027-05-01"}]).status_code == 200


def test_with_no_contract_dates_recorded_any_date_is_accepted(chain) -> None:
    """An unrecorded bound is never treated as broken (the Part 3 rule)."""
    response = _save(chain, changes=[{**REPUBLIC_DAY, "holiday_date": "2031-08-15"}, {**HOLI_WORKED, "holiday_date": "2031-03-10"}])
    assert response.status_code == 200, response.text


def test_the_contract_start_cannot_move_past_a_listed_holiday(chain) -> None:
    assert _save_period(chain).status_code == 200
    assert _save(chain, changes=[REPUBLIC_DAY]).status_code == 200
    response = _save_period(chain, expected_period_version=1, contract_start_date="2027-02-01")
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The contract cannot start on 1 February 2027, because a holiday is listed on 26 January 2027."
    )


def test_the_contract_end_cannot_move_before_a_listed_holiday(chain) -> None:
    assert _save_period(chain).status_code == 200
    assert _save(chain, changes=[HOLI]).status_code == 200
    response = _save_period(chain, expected_period_version=1, contract_end_date="2027-03-01")
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The contract cannot end on 1 March 2027, because a holiday is listed on 22 March 2027."
    )


def test_the_contract_cannot_move_past_a_working_day_either(chain) -> None:
    """HOL-1: a working day is held to the rule a holiday added is, and named for what it is."""
    assert _save_period(chain).status_code == 200
    assert _save(chain, changes=[HOLI_WORKED]).status_code == 200
    response = _save_period(chain, expected_period_version=1, contract_end_date="2027-03-01")
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The contract cannot end on 1 March 2027, because a working day is listed on 22 March 2027."
    )


def test_contract_dates_recorded_after_the_holidays_cannot_exclude_them(chain) -> None:
    """Changes entered before the contract dates are checked when the dates arrive."""
    assert _save(chain, changes=[{**REPUBLIC_DAY, "holiday_date": "2026-12-25"}]).status_code == 200
    response = _save_period(chain)  # would start on 1 January 2027
    assert response.status_code == 422
    assert "a holiday is listed on 25 December 2026" in response.json()["detail"]


def test_an_extension_cannot_be_removed_when_the_old_end_would_exclude_a_listed_date(chain) -> None:
    assert _save_period(chain).status_code == 200
    assert _extend(chain, new_end_date="2027-06-30").status_code == 201
    assert _save(chain, changes=[{**REPUBLIC_DAY, "holiday_date": "2027-05-01"}]).status_code == 200
    response = _remove_extension(chain, _extension_ids(chain)[0])
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "This extension cannot be removed. "
        "The contract cannot end on 31 March 2027, because a holiday is listed on 1 May 2027."
    )
    assert _save(chain, changes=[{**HOLI_WORKED, "holiday_date": "2027-05-01"}], expected_list_version=1).status_code == 200
    response = _remove_extension(chain, _extension_ids(chain)[0])
    assert response.status_code == 422
    assert "because a working day is listed on 1 May 2027" in response.json()["detail"]


# --- Versions, identical saves and events ---------------------------------------------------------------------------


def test_a_save_against_a_version_someone_else_moved_is_refused(chain) -> None:
    assert _save(chain, changes=[REPUBLIC_DAY]).status_code == 200
    # Nothing recorded yet, as far as this caller knew.
    assert _save(chain, changes=[HOLI], expected_list_version=None).status_code == 409
    # A version that is not the current one.
    assert _save(chain, changes=[HOLI], expected_list_version=5).status_code == 409
    assert [item["holiday_date"] for item in _get(chain).json()["changes"]] == ["2027-01-26"]


def test_an_identical_save_is_not_an_edit(chain) -> None:
    assert _save(chain, changes=[REPUBLIC_DAY, HOLI_WORKED]).status_code == 200
    again = _save(chain, changes=[HOLI_WORKED, REPUBLIC_DAY], expected_list_version=1)
    assert again.status_code == 200, again.text
    assert again.json()["event"] is None
    assert again.json()["holiday_list"]["list_version"] == 1
    assert len(_events(chain["work_order_public_id"], "WorkOrderHolidaysUpdated")) == 0


def test_a_change_moves_the_version_and_the_event_names_the_dates_not_the_words(chain) -> None:
    assert _save(chain, changes=[REPUBLIC_DAY, PONGAL, GUDI_PADWA_WORKED]).status_code == 200
    response = _save(
        chain,
        changes=[
            {**REPUBLIC_DAY, "description": "Republic Day (Gantantra Diwas)"},
            HOLI_WORKED,
            {**GUDI_PADWA_WORKED, "working_day_rate_code": "OVERTIME_RATE"},
        ],
        expected_list_version=1,
    )
    assert response.status_code == 200, response.text
    assert response.json()["holiday_list"]["list_version"] == 2
    assert response.json()["event"]["event_name"] == "WorkOrderHolidaysUpdated"
    payload = _events(chain["work_order_public_id"], "WorkOrderHolidaysUpdated")[-1]
    assert payload == {
        "list_version": 2,
        "holidays_answer_code": CHANGED,
        "holidays_added_count": 1,
        "working_days_count": 2,
        "entered_dates": ["2027-03-22"],
        "taken_off_dates": ["2027-01-15"],
        "changed_dates": ["2027-01-26", "2027-03-08"],
    }
    # The customer's own wording never reaches the audit trail.
    recorded = json.dumps(_events(chain["work_order_public_id"], "WorkOrderHolidaysRecorded"))
    for words in ("Republic Day", "Pongal", "Holi", "Gantantra", "Plant runs"):
        assert words not in json.dumps(payload) and words not in recorded


def test_turning_a_holiday_added_into_a_working_day_is_a_change_of_that_date(chain) -> None:
    assert _save(chain, changes=[HOLI]).status_code == 200
    response = _save(chain, changes=[{**HOLI_WORKED, "description": "Holi"}], expected_list_version=1)
    assert response.status_code == 200, response.text
    payload = _events(chain["work_order_public_id"], "WorkOrderHolidaysUpdated")[-1]
    assert (payload["entered_dates"], payload["taken_off_dates"], payload["changed_dates"]) == ([], [], ["2027-03-22"])


def test_changing_the_answer_to_unchanged_removes_every_change(chain) -> None:
    assert _save(chain, changes=[REPUBLIC_DAY, HOLI_WORKED]).status_code == 200
    response = _save(chain, answer=UNCHANGED, expected_list_version=1)
    assert response.status_code == 200, response.text
    assert response.json()["holiday_list"]["changes"] == []
    assert _stored_list_count(chain["work_order_public_id"]) == (1, 0)
    payload = _events(chain["work_order_public_id"], "WorkOrderHolidaysUpdated")[-1]
    assert payload["holidays_answer_code"] == UNCHANGED
    assert payload["taken_off_dates"] == ["2027-01-26", "2027-03-22"]


# --- A read never mixes two versions --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "first, second",
    [
        ({"answer": UNCHANGED, "changes": []}, {"answer": CHANGED, "changes": [REPUBLIC_DAY, HOLI_WORKED]}),
        ({"answer": CHANGED, "changes": [REPUBLIC_DAY, HOLI_WORKED]}, {"answer": UNCHANGED, "changes": []}),
    ],
)
def test_a_save_committing_during_a_read_never_yields_a_mix_of_two_versions(chain, first, second) -> None:
    """Review round 2, finding F-05. A save is forced to commit straight after the read's first holiday statement has
    run. Read in two statements - the answer, then the changes - the read returned version 1's answer beside version
    2's changes, a list that never existed. Read in one statement it returns version 1 whole; the save still lands, as
    the read afterwards shows."""
    from sqlalchemy import event

    from app.core.database import engine
    from app.modules.work_orders.schemas import WorkOrderHolidayListUpdate
    from app.modules.work_orders.services import holidays as holidays_service

    assert _save(chain, answer=first["answer"], changes=first["changes"]).status_code == 200
    fired: list[bool] = []

    def commit_a_save_between_statements(conn, cursor, statement, parameters, context, executemany) -> None:
        if fired or "crm_work_order_holiday" not in statement:
            return
        fired.append(True)
        with SessionLocal() as other:
            holidays_service.save_work_order_holidays(
                other,
                work_order_public_id=chain["work_order_public_id"],
                payload=WorkOrderHolidayListUpdate(
                    expected_list_version=1, holidays_answer_code=second["answer"], changes=second["changes"]
                ),
                current_user_public_id=None,
            )

    event.listen(engine, "after_cursor_execute", commit_a_save_between_statements)
    try:
        with SessionLocal() as db:
            read = holidays_service.get_work_order_holidays(db, chain["work_order_public_id"])
    finally:
        event.remove(engine, "after_cursor_execute", commit_a_save_between_statements)

    assert fired, "the concurrent save never ran, so this test proved nothing"
    assert read.list_version == 1
    assert read.holidays_answer_code == first["answer"]
    assert [item.holiday_date.isoformat() for item in read.changes] == [h["holiday_date"] for h in first["changes"]]
    after = _get(chain).json()
    assert after["list_version"] == 2
    assert after["holidays_answer_code"] == second["answer"]


# --- Who may do it --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("username", READ_ROLES)
def test_every_read_role_can_see_the_holidays(chain, username: str) -> None:
    assert _get(chain, username=username).status_code == 200


@pytest.mark.parametrize("username", WRITE_ROLES)
def test_every_role_that_writes_billing_terms_can_record_holidays(chain, username: str) -> None:
    assert _save(chain, answer=UNCHANGED, username=username).status_code == 200


@pytest.mark.parametrize("username", NON_WRITE_ROLES)
def test_finance_and_read_only_cannot_record_holidays(chain, username: str) -> None:
    assert _save(chain, answer=UNCHANGED, username=username).status_code == 403
    assert _save(chain, changes=[HOLI_WORKED], username=username).status_code == 403
    assert _stored_list_count(chain["work_order_public_id"]) == (0, 0)


def test_signed_out_is_refused(chain) -> None:
    assert client.get(_url(chain)).status_code in (401, 403)
    assert client.put(_url(chain), json={"holidays_answer_code": UNCHANGED}).status_code in (401, 403)


def test_a_closed_work_order_refuses_the_holiday_list(chain) -> None:
    with SessionLocal() as db:
        db.execute(
            text("UPDATE crm_work_order SET work_order_status_code = 'CLOSED' WHERE work_order_public_id = :id"),
            {"id": chain["work_order_public_id"]},
        )
        db.commit()
    response = _save(chain, answer=UNCHANGED)
    assert response.status_code == 422
    assert response.json()["detail"] == "This Work Order is closed. Its holidays can no longer be changed."
    # Reading still works.
    assert _get(chain).status_code == 200


def test_an_unknown_work_order_is_not_found(chain) -> None:
    missing = str(uuid4())
    assert client.get(f"/api/work-orders/{missing}/holidays", headers=auth_headers("sales1")).status_code == 404
    response = client.put(
        f"/api/work-orders/{missing}/holidays", headers=auth_headers("sales1"), json={"holidays_answer_code": UNCHANGED}
    )
    assert response.status_code == 404


# --- The handoff is untouched ---------------------------------------------------------------------------------------


def test_the_handoff_writes_no_holiday_list(chain) -> None:
    """The frozen handoff creates the Work Order and its lines and nothing else."""
    assert _stored_list_count(chain["work_order_public_id"]) == (0, 0)


# --- What the database itself refuses -------------------------------------------------------------------------------


def _work_order_id(work_order_public_id: str) -> int:
    with SessionLocal() as db:
        return int(
            db.execute(
                text("SELECT id FROM crm_work_order WHERE work_order_public_id = :id"), {"id": work_order_public_id}
            ).scalar_one()
        )


def _insert_list_directly(work_order_id: int, answer: str, list_version: int = 1) -> int:
    with SessionLocal() as db:
        try:
            list_id = db.execute(
                text(
                    "INSERT INTO crm_work_order_holiday_list (work_order_holiday_list_public_id, work_order_id, "
                    "holidays_answer_code, list_version) VALUES (:public_id, :work_order_id, :answer, :list_version) "
                    "RETURNING id"
                ),
                {"public_id": str(uuid4()), "work_order_id": work_order_id, "answer": answer, "list_version": list_version},
            ).scalar_one()
            db.commit()
            return int(list_id)
        finally:
            db.rollback()


def _insert_change_directly(
    list_id: int, holiday_date: str, kind: str | None, *, change_code: str = "HOLIDAY_ADDED", rate: str | None = None
) -> None:
    with SessionLocal() as db:
        try:
            db.execute(
                text(
                    "INSERT INTO crm_work_order_holiday (work_order_holiday_public_id, work_order_holiday_list_id, "
                    "change_code, holiday_date, holiday_kind_code, working_day_rate_code) "
                    "VALUES (:public_id, :list_id, :change_code, :holiday_date, :kind, :rate)"
                ),
                {
                    "public_id": str(uuid4()),
                    "list_id": list_id,
                    "change_code": change_code,
                    "holiday_date": holiday_date,
                    "kind": kind,
                    "rate": rate,
                },
            )
            db.commit()
        finally:
            db.rollback()


@pytest.mark.parametrize("answer", ["MAYBE", "NONE", "LISTED"])
def test_the_database_refuses_an_answer_other_than_the_two(chain, answer: str) -> None:
    with pytest.raises(IntegrityError) as refusal:
        _insert_list_directly(_work_order_id(chain["work_order_public_id"]), answer)
    assert "ck_wo_holiday_list_answer" in str(refusal.value)


@pytest.mark.parametrize("list_version", [0, -1])
def test_the_database_refuses_a_list_version_below_one(chain, list_version: int) -> None:
    """Review round 1, finding F-03: the version CHECK was the one new constraint no test named."""
    with pytest.raises(IntegrityError) as refusal:
        _insert_list_directly(_work_order_id(chain["work_order_public_id"]), UNCHANGED, list_version=list_version)
    assert "ck_wo_holiday_list_version" in str(refusal.value)
    assert _stored_list_count(chain["work_order_public_id"]) == (0, 0)


def test_the_database_refuses_a_second_list_for_one_work_order(chain) -> None:
    work_order_id = _work_order_id(chain["work_order_public_id"])
    _insert_list_directly(work_order_id, UNCHANGED)
    with pytest.raises(IntegrityError) as refusal:
        _insert_list_directly(work_order_id, CHANGED)
    assert "uq_wo_holiday_list_work_order" in str(refusal.value)


def test_the_database_refuses_an_unknown_kind_and_a_repeated_date(chain) -> None:
    list_id = _insert_list_directly(_work_order_id(chain["work_order_public_id"]), CHANGED)
    with pytest.raises(IntegrityError) as refusal:
        _insert_change_directly(list_id, "2027-01-26", "WEEKLY_OFF")
    assert "ck_wo_holiday_kind" in str(refusal.value)
    _insert_change_directly(list_id, "2027-01-26", "NATIONAL")
    with pytest.raises(IntegrityError) as refusal:
        _insert_change_directly(list_id, "2027-01-26", "FESTIVAL")
    assert "uq_wo_holiday_date" in str(refusal.value)
    # A date is a holiday added or a working day, never both.
    with pytest.raises(IntegrityError) as refusal:
        _insert_change_directly(list_id, "2027-01-26", None, change_code="WORKING_DAY", rate="NORMAL_RATE")
    assert "uq_wo_holiday_date" in str(refusal.value)


@pytest.mark.parametrize(
    "change_code, kind, rate, constraint",
    [
        # A holiday added needs its kind - an empty one too, which `NULL IN (...)` alone would let through.
        ("HOLIDAY_ADDED", None, None, "ck_wo_holiday_kind"),
        ("HOLIDAY_ADDED", "NATIONAL", "NORMAL_RATE", "ck_wo_holiday_working_day_rate"),
        # A working day needs its rate, empty refused too, and has no kind.
        ("WORKING_DAY", None, None, "ck_wo_holiday_working_day_rate"),
        ("WORKING_DAY", None, "HOLIDAY_RATE", "ck_wo_holiday_working_day_rate"),
        ("WORKING_DAY", "FESTIVAL", "OVERTIME_RATE", "ck_wo_holiday_kind"),
        ("REMOVED", None, None, "ck_wo_holiday_change"),
    ],
)
def test_the_database_holds_each_change_to_its_own_parts(chain, change_code: str, kind, rate, constraint: str) -> None:
    list_id = _insert_list_directly(_work_order_id(chain["work_order_public_id"]), CHANGED)
    with pytest.raises(IntegrityError) as refusal:
        _insert_change_directly(list_id, "2027-03-22", kind, change_code=change_code, rate=rate)
    assert constraint in str(refusal.value)


@pytest.mark.parametrize("rate", ["NORMAL_RATE", "OVERTIME_RATE"])
def test_the_database_accepts_a_working_day_at_either_rate(chain, rate: str) -> None:
    list_id = _insert_list_directly(_work_order_id(chain["work_order_public_id"]), CHANGED)
    _insert_change_directly(list_id, "2027-03-22", None, change_code="WORKING_DAY", rate=rate)
    assert _stored_list_count(chain["work_order_public_id"]) == (1, 1)


def test_the_database_refuses_a_date_that_belongs_to_no_list(chain) -> None:
    with pytest.raises(IntegrityError) as refusal:
        _insert_change_directly(-1, "2027-01-26", "NATIONAL")
    assert "fk_wo_holiday_list" in str(refusal.value)
