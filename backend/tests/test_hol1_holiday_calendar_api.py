"""HOL-1 - PBL's holiday calendar, through the API and at the database.

docs/agent/slices/hol-1-holiday-calendar.md, sections 5.1, 7, 8, 9, 10 and 14; the API is
docs/agent/contracts/holiday-calendar-api-contract.md. Every year saved here is one of the 2090s, owned by the test and
removed when it ends (`holiday_calendar_test_support`): the calendar is shared, so no test touches a real year.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.holiday_calendar import repository as calendar_repo
from app.modules.holiday_calendar import service as calendar_service
from app.modules.holiday_calendar.schemas import HolidayCalendarYearInput
from app.shared import business_time
from tests.holiday_calendar_test_support import calendar_test_years
from tests.test_commercial_offers_api import auth_headers, client

BASE = "/api/holiday-calendar"
ADMIN = "admin1"
READ_ROLES = ("admin1", "sales1", "manager1", "finance1", "ops1", "readonly1")
NOT_ADMIN = ("sales1", "manager1", "finance1", "ops1", "readonly1")


def _ok(response, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


def _detail(response, status: int = 422) -> str:
    assert response.status_code == status, response.text
    return response.json()["detail"]


def _holiday(year: int, month_day: str, name: str, *, kind: str = "FESTIVAL", states: list[str] | None = None) -> dict:
    return {
        "holiday_date": f"{year}-{month_day}",
        "holiday_kind_code": kind,
        "holiday_name": name,
        "applies_to_code": "STATES" if states else "ALL_INDIA",
        "state_codes": states or [],
    }


def _year_holidays(year: int) -> list[dict]:
    return [
        _holiday(year, "01-26", "Republic Day", kind="NATIONAL"),
        _holiday(year, "03-22", "Holi"),
        _holiday(year, "05-01", "Gujarat Day", states=["IN-GJ"]),
        _holiday(year, "05-01", "Maharashtra Day", kind="NATIONAL", states=["IN-MH"]),
        _holiday(year, "04-14", "Tamil New Year", states=["IN-TN"]),
        _holiday(year, "04-14", "Baisakhi", states=["IN-PB"]),
    ]


def _save(year: int, holidays: list[dict], *, version: int | None = None, complete: bool = False, username: str = ADMIN):
    body = {"expected_version": version, "is_complete": complete, "holidays": holidays}
    return client.put(f"{BASE}/years/{year}", json=body, headers=auth_headers(username))


def _get(year: int, username: str = "readonly1") -> dict:
    return _ok(client.get(f"{BASE}/years/{year}", headers=auth_headers(username)))


def _events(year_public_id: str) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT event_name, event_payload_json FROM business_event WHERE record_type = 'holiday_calendar_year' "
                "AND record_public_id = :id ORDER BY id"
            ),
            {"id": year_public_id},
        ).fetchall()
    return [{"event_name": row[0], "payload": json.loads(row[1]) if row[1] else {}} for row in rows]


def _stored(year: int) -> tuple[int, int, int]:
    """Year rows, holiday rows and state rows stored for a year."""
    with SessionLocal() as db:
        return tuple(
            int(db.execute(text(sql), {"y": year}).scalar_one())
            for sql in (
                "SELECT COUNT(*) FROM holiday_calendar_year WHERE calendar_year = :y",
                "SELECT COUNT(*) FROM holiday_calendar_holiday WHERE calendar_year = :y",
                "SELECT COUNT(*) FROM holiday_calendar_holiday_state s JOIN holiday_calendar_holiday h ON h.id = s.holiday_id "
                "WHERE h.calendar_year = :y",
            )
        )  # type: ignore[return-value]


@pytest.fixture
def year() -> Iterator[int]:
    with calendar_test_years() as years:
        yield years[0]


# --- The states and the years --------------------------------------------------------------------------------------


def test_the_states_are_elg1s_without_the_central_governments_own_sites() -> None:
    states = _ok(client.get(f"{BASE}/states", headers=auth_headers("readonly1")))
    codes = [state["state_code"] for state in states]
    assert len(states) == 36 and "IN" not in codes
    assert {"state_code": "IN-GJ", "state_label": "Gujarat", "state_kind_code": "STATE"} in states
    assert {state["state_kind_code"] for state in states} == {"STATE", "UNION_TERRITORY"}


def test_the_year_list_shows_the_current_and_next_year_even_when_not_started(year: int) -> None:
    body = _ok(client.get(f"{BASE}/years", headers=auth_headers("ops1")))
    today = date.fromisoformat(body["today"])
    by_year = {item["calendar_year"]: item for item in body["years"]}
    assert {today.year, today.year + 1} <= set(by_year)
    assert year not in by_year
    _ok(_save(year, _year_holidays(year)))
    started = {item["calendar_year"]: item for item in _ok(client.get(f"{BASE}/years", headers=auth_headers("ops1")))["years"]}[year]
    assert (started["year_version"], started["holiday_count"], started["is_complete"]) == (1, 6, False)
    assert started["updated_by_display_name"]


def test_a_year_not_started_reads_as_empty_and_not_complete(year: int) -> None:
    body = _get(year)
    assert (body["calendar_year"], body["year_public_id"], body["year_version"], body["is_complete"], body["holidays"]) == (
        year,
        None,
        None,
        False,
        [],
    )


@pytest.mark.parametrize("outside", [1999, 2101])
def test_a_year_outside_2000_to_2100_is_refused(outside: int) -> None:
    assert "from 2000 to 2100" in _detail(client.get(f"{BASE}/years/{outside}", headers=auth_headers(ADMIN)))
    assert "from 2000 to 2100" in _detail(_save(outside, []))


# --- Saving a year -------------------------------------------------------------------------------------------------


def test_admin_starts_a_year_and_reads_it_back_earliest_first(year: int) -> None:
    response = _ok(_save(year, _year_holidays(year)))
    body = response["year"]
    assert (body["year_version"], body["is_complete"], body["holiday_count"]) == (1, False, 6)
    assert [(item["holiday_date"], item["holiday_name"]) for item in body["holidays"]] == [
        (f"{year}-01-26", "Republic Day"),
        (f"{year}-03-22", "Holi"),
        (f"{year}-04-14", "Baisakhi"),
        (f"{year}-04-14", "Tamil New Year"),
        (f"{year}-05-01", "Gujarat Day"),
        (f"{year}-05-01", "Maharashtra Day"),
    ]
    republic, maharashtra = body["holidays"][0], body["holidays"][5]
    assert (republic["applies_to_code"], republic["states"], republic["holiday_kind_label"]) == ("ALL_INDIA", [], "National holiday")
    # A national holiday for one state only: Maharashtra's 1 May (1.2, point 2).
    assert (maharashtra["holiday_kind_code"], maharashtra["states"]) == ("NATIONAL", [{"state_code": "IN-MH", "state_label": "Maharashtra"}])
    assert _get(year) == {**body, "today": _get(year)["today"]}
    assert _stored(year) == (1, 6, 4)
    events = _events(body["year_public_id"])
    assert [item["event_name"] for item in events] == ["HOLIDAY_CALENDAR_YEAR_RECORDED"]
    assert response["event"]["event_name"] == "HOLIDAY_CALENDAR_YEAR_RECORDED"


def test_a_change_moves_the_version_and_the_event_names_the_dates_not_the_names(year: int) -> None:
    first = _ok(_save(year, _year_holidays(year)))["year"]
    changed = [
        _holiday(year, "01-26", "Republic Day", kind="NATIONAL"),
        _holiday(year, "03-22", "Holi (Dhuleti)"),
        _holiday(year, "05-01", "Gujarat Day", states=["IN-GJ", "IN-DH"]),
        _holiday(year, "05-01", "Maharashtra Day", kind="NATIONAL", states=["IN-MH"]),
        _holiday(year, "10-02", "Gandhi Jayanti", kind="NATIONAL"),
    ]
    body = _ok(_save(year, changed, version=1))
    assert body["year"]["year_version"] == 2
    payload = _events(first["year_public_id"])[-1]
    assert payload == {
        "event_name": "HOLIDAY_CALENDAR_YEAR_CHANGED",
        "payload": {
            "calendar_year": year,
            "year_version": 2,
            "is_complete": False,
            "was_complete": False,
            "holiday_count": 5,
            "added_dates": [f"{year}-10-02"],
            "removed_dates": [f"{year}-04-14"],
            "changed_dates": [f"{year}-03-22", f"{year}-05-01"],
        },
    }
    for words in ("Holi", "Dhuleti", "Gandhi", "Gujarat Day", "Republic"):
        assert words not in json.dumps([item["payload"] for item in _events(first["year_public_id"])])


def test_an_identical_save_changes_nothing_and_records_nothing(year: int) -> None:
    first = _ok(_save(year, _year_holidays(year)))["year"]
    again = _ok(_save(year, list(reversed(_year_holidays(year))), version=1))
    assert again["event"] is None and again["year"]["year_version"] == 1
    assert len(_events(first["year_public_id"])) == 1


def test_a_save_against_a_version_someone_else_moved_is_refused(year: int) -> None:
    _ok(_save(year, _year_holidays(year)))
    assert "after you opened it" in _detail(_save(year, [], version=None), 409)
    assert "after you opened it" in _detail(_save(year, [], version=5), 409)
    assert _get(year)["holiday_count"] == 6


def test_the_codes_are_accepted_in_any_case(year: int) -> None:
    holiday = {**_holiday(year, "05-01", "Gujarat Day", states=["in-gj"]), "holiday_kind_code": "festival", "applies_to_code": "states"}
    body = _ok(_save(year, [holiday]))["year"]
    assert (body["holidays"][0]["holiday_kind_code"], body["holidays"][0]["applies_to_code"], body["holidays"][0]["states"][0]["state_code"]) == (
        "FESTIVAL",
        "STATES",
        "IN-GJ",
    )


@pytest.mark.parametrize(
    "holidays, words",
    [
        (lambda y: [_holiday(y - 1, "12-25", "Christmas")], "is not in"),
        (lambda y: [_holiday(y, "01-26", "Republic Day", kind="WEEKLY_OFF")], "national or a festival holiday"),
        (lambda y: [_holiday(y, "01-26", "   ")], "a name"),
        (lambda y: [{**_holiday(y, "05-01", "Gujarat Day"), "applies_to_code": "STATES"}], "at least one state"),
        (lambda y: [{**_holiday(y, "05-01", "Gujarat Day"), "state_codes": ["IN-GJ"]}], "names no states"),
        (lambda y: [_holiday(y, "05-01", "Somewhere", states=["IN"])], "not a state or union territory"),
        (lambda y: [_holiday(y, "05-01", "Somewhere", states=["IN-XX"])], "not a state or union territory"),
        (lambda y: [_holiday(y, "01-26", "A"), _holiday(y, "01-26", "B")], "apply to all of India"),
        (lambda y: [_holiday(y, "01-26", "A"), _holiday(y, "01-26", "B", states=["IN-GJ"])], "already a holiday for all of India"),
        (lambda y: [_holiday(y, "05-01", "A", states=["IN-GJ"]), _holiday(y, "05-01", "B", states=["IN-GJ"])], "Gujarat twice"),
    ],
)
def test_each_refusal_is_in_words_and_stores_nothing(year: int, holidays, words: str) -> None:
    assert words in _detail(_save(year, holidays(year)))
    assert _stored(year) == (0, 0, 0)


def test_unknown_fields_and_overlong_names_are_refused(year: int) -> None:
    assert _save(year, [{**_holiday(year, "01-26", "Republic Day"), "note": "x"}]).status_code == 422
    # In words that name the date, as every refusal of a holiday is - never the request validator's list
    # (independent review, HOL1-R3-001).
    assert _detail(_save(year, [_holiday(year, "01-26", "x" * 256)])) == (
        f"The name of the holiday on 26 January {year} is longer than 255 characters."
    )
    assert _detail(_save(year, [_holiday(year, "01-26", "Republic Day", kind="N" * 21)])) == (
        f"Choose whether the holiday on 26 January {year} is a national or a festival holiday."
    )
    too_long_applies = {**_holiday(year, "01-26", "Republic Day"), "applies_to_code": "A" * 21}
    assert _detail(_save(year, [too_long_applies])) == (
        f"Choose whether the holiday on 26 January {year} applies to all of India or to the states named."
    )
    response = client.put(f"{BASE}/years/{year}", json={"expected_version": None, "holidays": []}, headers=auth_headers(ADMIN))
    assert response.status_code == 422, "the complete mark must be given"
    assert _stored(year) == (0, 0, 0)
    # A holiday's field left out, or null, is refused in the same words, naming the date (HOL1-R4-002).
    holiday = _holiday(year, "01-26", "Republic Day", kind="NATIONAL")
    without = lambda field: {key: value for key, value in holiday.items() if key != field}  # noqa: E731
    for given in (without("holiday_name"), {**holiday, "holiday_name": None}):
        assert _detail(_save(year, [given])) == f"Give the holiday on 26 January {year} a name."
    for given in (without("holiday_kind_code"), {**holiday, "holiday_kind_code": None}):
        assert _detail(_save(year, [given])) == (
            f"Choose whether the holiday on 26 January {year} is a national or a festival holiday."
        )
    for given in (without("applies_to_code"), {**holiday, "applies_to_code": None}):
        assert _detail(_save(year, [given])) == (
            f"Choose whether the holiday on 26 January {year} applies to all of India or to the states named."
        )
    for given in (without("state_codes"), {**holiday, "state_codes": None}):
        assert _detail(_save(year, [{**given, "applies_to_code": "STATES"}])) == (
            f"Choose at least one state for the holiday on 26 January {year}, or make it apply to all of India."
        )
    assert _stored(year) == (0, 0, 0)
    # An all-India holiday may leave its states out.
    assert _ok(_save(year, [without("state_codes")]))["year"]["holiday_count"] == 1
    # 255 characters are kept.
    assert _ok(_save(year, [_holiday(year, "01-26", "x" * 255)], version=1))["year"]["holiday_count"] == 1


def test_a_save_takes_the_contracts_field_names_and_refuses_the_ones_the_design_first_gave(year: int) -> None:
    """HOL1-R1-003: holiday-calendar-api-contract.md, "PUT .../years/{calendar_year}", names these fields. The design's
    section 8 first read `complete` and `description`; a client following it is refused, not half understood."""
    from app.modules.holiday_calendar.schemas import HolidayCalendarHolidayInput

    assert set(HolidayCalendarYearInput.model_fields) == {"expected_version", "is_complete", "holidays"}
    assert set(HolidayCalendarHolidayInput.model_fields) == {
        "holiday_date", "holiday_kind_code", "holiday_name", "applies_to_code", "state_codes"
    }
    holiday = _holiday(year, "01-26", "Republic Day", kind="NATIONAL")
    old_holiday = {**{k: v for k, v in holiday.items() if k != "holiday_name"}, "description": "Republic Day"}
    old_shape = {"expected_version": None, "complete": False, "holidays": [old_holiday]}
    assert client.put(f"{BASE}/years/{year}", json=old_shape, headers=auth_headers(ADMIN)).status_code == 422
    assert _stored(year) == (0, 0, 0)


# --- The complete mark ---------------------------------------------------------------------------------------------


def test_admin_marks_a_year_complete_and_takes_the_mark_off_again(year: int) -> None:
    first = _ok(_save(year, _year_holidays(year), complete=True))["year"]
    assert first["is_complete"] is True and first["complete_marked_by_display_name"] and first["complete_marked_at"]
    # A change while it stays complete keeps who marked it and when.
    changed = _ok(_save(year, _year_holidays(year)[:5], version=1, complete=True))["year"]
    assert (changed["complete_marked_at"], changed["complete_marked_by_display_name"]) == (
        first["complete_marked_at"],
        first["complete_marked_by_display_name"],
    )
    # The same again is no change.
    assert _ok(_save(year, _year_holidays(year)[:5], version=2, complete=True))["event"] is None
    unmarked = _ok(_save(year, _year_holidays(year)[:5], version=2, complete=False))
    assert unmarked["year"]["is_complete"] is False and unmarked["year"]["complete_marked_at"] is None
    payloads = [item["payload"] for item in _events(first["year_public_id"])]
    assert [(item["is_complete"], item["was_complete"]) for item in payloads] == [(True, False), (True, True), (False, True)]


# --- Who may do it -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("username", READ_ROLES)
def test_everyone_reads_the_calendar(username: str, year: int) -> None:
    for path in ("/states", "/years", f"/years/{year}"):
        assert client.get(f"{BASE}{path}", headers=auth_headers(username)).status_code == 200


@pytest.mark.parametrize("username", NOT_ADMIN)
def test_only_admin_keeps_the_calendar(username: str, year: int) -> None:
    assert _save(year, _year_holidays(year), username=username).status_code == 403
    assert _stored(year) == (0, 0, 0)


def test_signed_out_is_refused(year: int) -> None:
    assert client.get(f"{BASE}/years").status_code in (401, 403)
    assert client.put(f"{BASE}/years/{year}", json={"is_complete": False, "holidays": []}).status_code in (401, 403)


# --- One save at a time --------------------------------------------------------------------------------------------


def test_a_save_waits_for_the_calendar_lock_and_then_sees_what_was_saved_meanwhile(year: int) -> None:
    """The year is read under the module's write lock: a save that started while another held it waits, then finds the
    year the other saved and is refused, rather than writing over it."""
    outcome: dict[str, Any] = {}

    def save_late() -> None:
        with SessionLocal() as db:
            try:
                calendar_service.save_year(
                    db,
                    calendar_year=year,
                    payload=HolidayCalendarYearInput(expected_version=None, is_complete=False, holidays=[]),
                    user_public_id=_admin_public_id(),
                )
                outcome["result"] = "saved"
            except calendar_service.HolidayCalendarConflictError:
                outcome["result"] = "refused"

    with SessionLocal() as holder:
        calendar_repo.take_write_lock(holder)
        late = threading.Thread(target=save_late)
        late.start()
        time.sleep(1.0)
        assert late.is_alive(), "the second save did not wait for the lock"
        holder.execute(
            text(
                "INSERT INTO holiday_calendar_year (year_public_id, calendar_year, year_version) VALUES (:p, :y, 1)"
            ),
            {"p": str(uuid4()), "y": year},
        )
        holder.commit()
    late.join(timeout=30)
    assert outcome == {"result": "refused"}


@pytest.mark.parametrize("identical", [False, True])
def test_a_saves_answer_is_its_own_year_even_when_another_save_commits_straight_after(year: int, identical: bool) -> None:
    """HOL1-R1-001: the moment a save commits - or, saving nothing new, rolls back - it lets the lock go, and another
    save may commit at once. The answer must still be the year the first save produced, beside its own event: read
    after the lock was let go, it was the other save's."""
    from sqlalchemy import event

    _ok(_save(year, _year_holidays(year)))  # version 1
    admin = _admin_public_id()
    mine = _year_holidays(year) if identical else _year_holidays(year)[:5]
    fired: list[bool] = []

    def another_save(session) -> None:
        if fired:
            return
        fired.append(True)
        with SessionLocal() as other:
            calendar_service.save_year(
                other,
                calendar_year=year,
                payload=HolidayCalendarYearInput(expected_version=1 if identical else 2, is_complete=True, holidays=[]),
                user_public_id=admin,
            )

    with SessionLocal() as db:
        event.listen(db, "after_rollback" if identical else "after_commit", another_save)
        answer = calendar_service.save_year(
            db,
            calendar_year=year,
            payload=HolidayCalendarYearInput(expected_version=1, is_complete=False, holidays=mine),
            user_public_id=admin,
        )

    assert fired, "the other save never ran, so this test proved nothing"
    if identical:
        assert answer.event is None
        assert (answer.year.year_version, answer.year.holiday_count, answer.year.is_complete) == (1, 6, False)
    else:
        assert answer.event["event_payload"]["year_version"] == 2
        assert (answer.year.year_version, answer.year.holiday_count, answer.year.is_complete) == (2, 5, False)
    # The other save landed after it.
    after = _get(year)
    assert (after["year_version"], after["holiday_count"], after["is_complete"]) == (2 if identical else 3, 0, True)


def test_the_year_list_offers_no_year_beyond_2100(monkeypatch) -> None:
    """HOL1-R1-002: in 2100 the next year is outside the calendar, which could never save or complete it."""
    monkeypatch.setattr(business_time, "india_today", lambda: date(2100, 6, 1))
    years = [item["calendar_year"] for item in _ok(client.get(f"{BASE}/years", headers=auth_headers("readonly1")))["years"]]
    assert 2100 in years and 2101 not in years


def _admin_public_id() -> str:
    with SessionLocal() as db:
        return str(db.execute(text("SELECT public_id FROM app_user WHERE username = 'admin1'")).scalar_one())


# --- What the database itself refuses ------------------------------------------------------------------------------


def _insert_year(db, year: int, **values) -> int:
    row = {"p": str(uuid4()), "y": year, "v": 1, "by": None, "at": None, **values}
    return int(
        db.execute(
            text(
                "INSERT INTO holiday_calendar_year (year_public_id, calendar_year, year_version, complete_marked_by, "
                "complete_marked_at) VALUES (:p, :y, :v, :by, :at) RETURNING id"
            ),
            row,
        ).scalar_one()
    )


def _insert_holiday(db, year_id: int, year: int, on: str, **values) -> int:
    row = {"p": str(uuid4()), "year_id": year_id, "y": year, "on": on, "kind": "FESTIVAL", "name": "x", "applies": "ALL_INDIA", **values}
    return int(
        db.execute(
            text(
                "INSERT INTO holiday_calendar_holiday (holiday_public_id, year_id, calendar_year, holiday_date, holiday_kind_code, "
                "holiday_name, applies_to_code) VALUES (:p, :year_id, :y, :on, :kind, :name, :applies) RETURNING id"
            ),
            row,
        ).scalar_one()
    )


def _insert_state(db, holiday_id: int, on: str, code: str) -> None:
    db.execute(
        text("INSERT INTO holiday_calendar_holiday_state (holiday_id, holiday_date, jurisdiction_code) VALUES (:h, :on, :c)"),
        {"h": holiday_id, "on": on, "c": code},
    )


def _refused(statement, constraint: str) -> None:
    with SessionLocal() as db:
        with pytest.raises(IntegrityError) as refusal:
            statement(db)
        db.rollback()
    assert constraint in str(refusal.value)


def test_the_database_holds_a_year_to_its_rules(year: int) -> None:
    _refused(lambda db: _insert_year(db, 1999), "ck_holiday_calendar_year_range")
    _refused(lambda db: _insert_year(db, year, v=0), "ck_holiday_calendar_year_version")
    _refused(lambda db: _insert_year(db, year, at=datetime.now(timezone.utc)), "ck_holiday_calendar_year_complete_mark")
    _refused(lambda db: _insert_year(db, year, by=_admin_public_id()), "ck_holiday_calendar_year_complete_mark")

    def twice(db) -> None:
        _insert_year(db, year)
        _insert_year(db, year)

    _refused(twice, "uq_holiday_calendar_year")


def test_the_database_holds_a_holiday_to_its_year_and_its_rules(year: int) -> None:
    def with_year(make):
        def statement(db) -> None:
            make(db, _insert_year(db, year))

        return statement

    on = f"{year}-01-26"
    _refused(with_year(lambda db, y: _insert_holiday(db, y, year, f"{year + 1}-01-26")), "ck_holiday_calendar_holiday_in_year")
    _refused(with_year(lambda db, y: _insert_holiday(db, y, year + 1, f"{year + 1}-01-26")), "fk_holiday_calendar_holiday_year")
    _refused(with_year(lambda db, y: _insert_holiday(db, y, year, on, kind="WEEKLY_OFF")), "ck_holiday_calendar_holiday_kind")
    _refused(with_year(lambda db, y: _insert_holiday(db, y, year, on, name="  ")), "ck_holiday_calendar_holiday_name")
    _refused(with_year(lambda db, y: _insert_holiday(db, y, year, on, applies="ANYWHERE")), "ck_holiday_calendar_holiday_applies_to")

    def two_all_india(db, y) -> None:
        _insert_holiday(db, y, year, on)
        _insert_holiday(db, y, year, on, name="another")

    _refused(with_year(two_all_india), "uq_holiday_calendar_holiday_all_india_date")


def test_the_database_holds_a_holidays_states(year: int) -> None:
    on = f"{year}-05-01"

    def state(code: str, *, date_given: str = on, second: tuple[str, str] | None = None):
        def statement(db) -> None:
            year_id = _insert_year(db, year)
            holiday = _insert_holiday(db, year_id, year, on, applies="STATES")
            _insert_state(db, holiday, date_given, code)
            if second:
                other = _insert_holiday(db, year_id, year, on, applies="STATES", name="other")
                _insert_state(db, other, on, second[1])

        return statement

    _refused(state("IN"), "ck_holiday_calendar_holiday_state_not_central")
    _refused(state("IN-XX"), "fk_holiday_calendar_holiday_state_jurisdiction")
    _refused(state("IN-GJ", date_given=f"{year}-05-02"), "fk_holiday_calendar_holiday_state_holiday")
    _refused(state("IN-GJ", second=("", "IN-GJ")), "uq_holiday_calendar_holiday_state_date")
    with SessionLocal() as db:
        state("IN-GJ", second=("", "IN-MH"))(db)
        db.rollback()
