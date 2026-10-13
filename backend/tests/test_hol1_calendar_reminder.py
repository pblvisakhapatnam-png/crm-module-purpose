"""HOL-1, Q2 - "PBL's holiday calendar for <year> is not set up", a fifth reminder on ELG-2's Alerts.

docs/agent/slices/hol-1-holiday-calendar.md, sections 1.1 (Q2), 5.4, 10 and 14. Every test reads the Alerts as on a day
in 2093, through the service's today as the routes take it, so the years reminded about - 2093 and 2094 - are test
years nobody keeps a real calendar for; they are cleared before and after. The four certificate reminders are ELG-2's
own tests', unchanged but for the fifth kind's place in their lists.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from zoneinfo import ZoneInfo
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.eligibility import alerts as alerts_module
from app.modules.eligibility import ports
from app.modules.eligibility import reminders
from app.shared import business_time
from tests.holiday_calendar_test_support import remove_calendar_years
from tests.test_commercial_offers_api import auth_headers, client
from tests.test_elg2_certificate_reminders_api import settings_restored  # noqa: F401  (a fixture)

ALERTS = "/api/eligibility/alerts"
KIND = "HOLIDAY_CALENDAR_NOT_SET_UP"
THIS_YEAR, NEXT_YEAR = 2093, 2094
TODAY = date(THIS_YEAR, 11, 15)


def _ok(response, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


def _on(monkeypatch, day: date) -> None:
    monkeypatch.setattr(business_time, "india_today", lambda: day)


def _calendar_items(username: str = "admin1", **params) -> dict[int, dict]:
    body = _ok(client.get(ALERTS, params={"limit": 500, "reminder_kind_code": KIND, **params}, headers=auth_headers(username)))
    return {item["calendar_year"]: item for item in body["items"]}


def _save_year(year: int, *, complete: bool, version: int | None = None) -> dict:
    body = {"expected_version": version, "is_complete": complete, "holidays": []}
    return _ok(client.put(f"/api/holiday-calendar/years/{year}", json=body, headers=auth_headers("admin1")))["year"]


def _seen_ids_above(boundary: int) -> list[dict]:
    with SessionLocal() as db:
        return [
            dict(row._mapping)
            for row in db.execute(
                text(
                    "SELECT reminder_key, reminder_kind_code, equipment_asset_public_id, subject_type, subject_public_id, kind_code, "
                    "reminder_date_on, reminder_on FROM eligibility_alert_acknowledgement WHERE id > :b ORDER BY id"
                ),
                {"b": boundary},
            ).fetchall()
        ]


@pytest.fixture
def seen_boundary() -> Iterator[int]:
    """The test's years cleared before and after, with the "seen" marks the test made."""
    remove_calendar_years([THIS_YEAR, NEXT_YEAR])
    with SessionLocal() as db:
        boundary = int(db.execute(text("SELECT COALESCE(MAX(id), 0) FROM eligibility_alert_acknowledgement")).scalar_one())
    try:
        yield boundary
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM eligibility_alert_acknowledgement WHERE id > :b"), {"b": boundary})
            db.commit()
        remove_calendar_years([THIS_YEAR, NEXT_YEAR])


def test_this_year_and_next_are_reminded_on_their_schedule_until_marked_complete(monkeypatch, seen_boundary) -> None:
    _on(monkeypatch, TODAY)
    items = _calendar_items()
    assert set(items) == {THIS_YEAR, NEXT_YEAR}
    this_year, next_year = items[THIS_YEAR], items[NEXT_YEAR]
    # This year began without a calendar: reminded every day since 1 January.
    assert (this_year["date_on"], this_year["reminder_on"], this_year["reason_code"]) == ("2093-01-01", TODAY.isoformat(), "CALENDAR_NOT_COMPLETE")
    assert (this_year["asset"], this_year["kind_code"], this_year["allocation"], this_year["mark_public_id"]) == (None, "", None, None)
    assert this_year["reminder_kind_label"] == "PBL's holiday calendar not set up"
    assert this_year["reminder_key"] == "HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|2093|||2093-01-01"
    assert {step["role_code"] for step in this_year["reached"]} == {"ADMIN", "MANAGEMENT_READ_ONLY"}
    # Next year: 60 days before 1 January was 2 November, the schedule's first reminder; Management from 1 January.
    assert (next_year["date_on"], next_year["first_reminder_on"], next_year["reminder_on"]) == ("2094-01-01", "2093-11-02", "2093-11-02")
    assert [step["role_code"] for step in next_year["reached"]] == ["ADMIN"]

    # Started is not complete; only the mark ends the reminder.
    started = _save_year(THIS_YEAR, complete=False)
    assert set(_calendar_items()) == {THIS_YEAR, NEXT_YEAR}
    _save_year(THIS_YEAR, complete=True, version=started["year_version"])
    assert set(_calendar_items()) == {NEXT_YEAR}
    marked = _save_year(NEXT_YEAR, complete=True)
    assert _calendar_items() == {}
    # The mark taken off raises it again.
    _save_year(NEXT_YEAR, complete=False, version=marked["year_version"])
    assert set(_calendar_items()) == {NEXT_YEAR}


def test_next_year_waits_for_the_schedules_first_reminder(monkeypatch, seen_boundary) -> None:
    _on(monkeypatch, date(THIS_YEAR, 11, 1))  # 61 days before 1 January 2094
    assert set(_calendar_items()) == {THIS_YEAR}
    _on(monkeypatch, date(THIS_YEAR, 11, 2))
    assert set(_calendar_items()) == {THIS_YEAR, NEXT_YEAR}


@pytest.mark.parametrize(
    "username, years",
    [
        ("readonly1", {THIS_YEAR}),
        ("ops1", set()),
        ("sales1", set()),
        ("manager1", set()),
        ("finance1", set()),
    ],
)
def test_it_reaches_admin_and_then_management_and_nobody_else(monkeypatch, seen_boundary, username: str, years: set) -> None:
    _on(monkeypatch, TODAY)
    assert set(_calendar_items(username)) == years


def test_it_is_found_by_its_year(monkeypatch, seen_boundary) -> None:
    _on(monkeypatch, TODAY)
    assert set(_calendar_items(search="2094")) == {NEXT_YEAR}
    assert set(_calendar_items(search="holiday calendar")) == {THIS_YEAR, NEXT_YEAR}
    body = _ok(client.get(ALERTS, params={"limit": 500}, headers=auth_headers("admin1")))
    count = _ok(client.get(f"{ALERTS}/count", headers=auth_headers("admin1")))
    assert body["counts"]["by_kind"][KIND] == 2
    assert (count["total"], count["unseen"]) == (body["counts"]["total"], body["counts"]["unseen"])


def test_marking_it_seen_quiets_it_for_that_person_until_its_next_reminder_day(monkeypatch, seen_boundary) -> None:
    _on(monkeypatch, TODAY)
    item = _calendar_items()[THIS_YEAR]
    body = {"items": [{"reminder_key": item["reminder_key"], "reminder_on": item["reminder_on"]}]}
    assert _ok(client.post(f"{ALERTS}/seen", json=body, headers=auth_headers("admin1"))) == {"marked": 1, "already": 0}
    assert _calendar_items()[THIS_YEAR]["seen_by_me"] is True
    assert _calendar_items("readonly1")[THIS_YEAR]["seen_by_me"] is False
    assert [item["display_name"] for item in _calendar_items("readonly1")[THIS_YEAR]["seen_by"]]
    # About a year: no machine, no certificate kind.
    assert _seen_ids_above(seen_boundary) == [
        {
            "reminder_key": "HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|2093|||2093-01-01",
            "reminder_kind_code": KIND,
            "equipment_asset_public_id": None,
            "subject_type": "holiday_calendar_year",
            "subject_public_id": "2093",
            "kind_code": None,
            "reminder_date_on": date(2093, 1, 1),
            "reminder_on": TODAY,
        }
    ]
    # Daily since 1 January: the next day is a new reminder day, not yet seen.
    _on(monkeypatch, TODAY + timedelta(days=1))
    assert _calendar_items()[THIS_YEAR]["seen_by_me"] is False


def test_a_reminder_settled_meanwhile_cannot_be_marked(monkeypatch, seen_boundary) -> None:
    _on(monkeypatch, TODAY)
    item = _calendar_items()[NEXT_YEAR]
    _save_year(NEXT_YEAR, complete=True)
    body = {"items": [{"reminder_key": item["reminder_key"], "reminder_on": item["reminder_on"]}]}
    response = client.post(f"{ALERTS}/seen", json=body, headers=auth_headers("admin1"))
    assert response.status_code == 404 and "no longer due for you" in response.json()["detail"]
    assert _seen_ids_above(seen_boundary) == []


def test_admin_changes_who_it_reaches_on_reminder_settings(monkeypatch, seen_boundary, settings_restored) -> None:
    _on(monkeypatch, TODAY)
    settings = _ok(client.get("/api/eligibility/alert-settings", headers=auth_headers("readonly1")))["settings"]
    current = next(item for item in settings if item["reminder_kind_code"] == KIND)["current"]
    body = {
        "expected_version": current["version_number"],
        "bands": current["bands"],
        "steps": [{"role_code": "ADMIN", "starts_code": "FIRST_REMINDER", "from_days_before": None, "channel_codes": ["SCREEN"]}],
    }
    _ok(client.post(f"/api/eligibility/alert-settings/{KIND}", json=body, headers=auth_headers("admin1")), 201)
    assert _calendar_items("readonly1") == {}
    assert set(_calendar_items()) == {THIS_YEAR, NEXT_YEAR}


def test_in_2100_no_reminder_is_raised_for_a_year_the_calendar_cannot_keep(monkeypatch, seen_boundary) -> None:
    """HOL1-R1-002: from 2 November 2100 the next year would be 2101, which the calendar cannot save or complete - its
    reminder could never end. Only 2100 is reminded."""
    remove_calendar_years([2100])
    try:
        _on(monkeypatch, date(2100, 12, 15))
        assert set(_calendar_items()) == {2100}
        with SessionLocal() as db:
            assert ports.calendar_source().years_not_complete(db, years=[1999, 2100, 2101]) == [2100]
    finally:
        remove_calendar_years([2100])


def test_without_the_calendar_loaded_the_reminders_fail_closed(monkeypatch, seen_boundary) -> None:
    monkeypatch.setattr(ports, "_calendar_registered", [])
    with pytest.raises(RuntimeError, match="holiday calendar is not loaded"):
        client.get(ALERTS, headers=auth_headers("admin1"))


# --- When a year's reminder begins (design section 5.4) -------------------------------------------------------------

STANDARD = reminders.Setting(
    reminder_kind_code=KIND,
    version_number=1,
    bands=reminders.ordered_bands(reminders.Band(start, every) for start, every in ((60, 30), (15, 7), (7, 1), (0, 1))),
    steps=(
        reminders.Step("ADMIN", "FIRST_REMINDER", None, ("SCREEN",)),
        reminders.Step("MANAGEMENT_READ_ONLY", "DAYS_BEFORE", 0, ("SCREEN",)),
    ),
)


def test_a_year_running_when_the_reminder_came_is_reminded_from_that_day_not_before() -> None:
    """The calendar did not exist before the package came: the year then running is reminded from that day, once, and
    reaches Management at once, since its 1 January has passed - never "reminded 286 times" back to a time before."""
    installed = date(2026, 10, 2)
    item = alerts_module._calendar_reminder(STANDARD, calendar_year=2026, today=installed, began_on=installed)
    assert item is not None
    assert (item.days.first_on, item.days.current_on, item.days.so_far) == (installed, installed, 1)
    assert [(step.step.role_code, step.reached_on) for step in item.reached] == [("ADMIN", installed), ("MANAGEMENT_READ_ONLY", installed)]
    later = alerts_module._calendar_reminder(STANDARD, calendar_year=2026, today=date(2026, 10, 5), began_on=installed)
    assert (later.days.first_on, later.days.current_on, later.days.so_far) == (installed, date(2026, 10, 5), 4)


def test_a_later_year_is_reminded_on_its_schedule_from_its_first_reminder() -> None:
    installed = date(2026, 10, 2)
    assert alerts_module._calendar_reminder(STANDARD, calendar_year=2027, today=installed, began_on=installed) is None
    item = alerts_module._calendar_reminder(STANDARD, calendar_year=2027, today=date(2026, 11, 2), began_on=installed)
    assert item is not None and (item.days.first_on, item.days.so_far) == (date(2026, 11, 2), 1)
    assert [step.step.role_code for step in item.reached] == ["ADMIN"]


def test_the_reminder_began_when_the_package_loaded_its_setting() -> None:
    with SessionLocal() as db:
        began = alerts_module.calendar_reminders_began(db)
        first = db.execute(
            text("SELECT MIN(saved_at) FROM eligibility_alert_setting WHERE reminder_kind_code = :kind"), {"kind": KIND}
        ).scalar_one()
    assert began == first.astimezone(ZoneInfo("Asia/Kolkata")).date()


# --- What the database holds a "seen" mark on a year to ---------------------------------------------------------


def test_the_database_holds_a_year_marks_parts(seen_boundary) -> None:
    with SessionLocal() as db:
        user = db.execute(text("SELECT public_id FROM app_user WHERE username = 'admin1'")).scalar_one()
        asset = db.execute(text("SELECT asset_public_id FROM equipment_asset LIMIT 1")).scalar()
    good = {
        "key": "HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|2093|||2093-01-01",
        "kind": KIND,
        "asset": None,
        "subject_type": "holiday_calendar_year",
        "subject": "2093",
        "certificate_kind": None,
        "date_on": date(2093, 1, 1),
        "user": user,
    }
    insert = (
        "INSERT INTO eligibility_alert_acknowledgement (reminder_key, reminder_kind_code, equipment_asset_public_id, "
        "subject_type, subject_public_id, kind_code, reminder_date_on, reminder_on, seen_by) "
        "VALUES (:key, :kind, :asset, :subject_type, :subject, :certificate_kind, :date_on, CURRENT_DATE, :user)"
    )
    with SessionLocal() as db:
        db.execute(text(insert), good)
        db.rollback()
    refused = [
        # Not 1 January; the year it names not the date's.
        {**good, "key": "HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|2093|||2093-01-02", "date_on": date(2093, 1, 2)},
        {**good, "key": "HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|2092|||2093-01-01", "subject": "2092"},
        # A certificate kind, or a key naming one.
        {**good, "certificate_kind": "INSURANCE", "key": "HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|2093||INSURANCE|2093-01-01"},
        {**good, "key": "HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|2093||INSURANCE|2093-01-01"},
        # Another kind of reminder about a year; a year's reminder about an asset.
        {**good, "kind": "CERTIFICATE_RUNNING_OUT", "key": "CERTIFICATE_RUNNING_OUT|holiday_calendar_year|2093|||2093-01-01"},
        {**good, "subject_type": "asset", "key": "HOLIDAY_CALENDAR_NOT_SET_UP|asset|2093|||2093-01-01"},
        # The key is its six parts and nothing more: an empty seventh part is not "none" (HOL1-R2-002).
        {**good, "key": "HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|2093|||2093-01-01|"},
        {**good, "key": "HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|2093|||2093-01-01||suffix"},
        {**good, "key": "|HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|2093|||2093-01-01"},
    ]
    if asset:
        refused.append({**good, "asset": asset, "key": f"HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|2093|{asset}||2093-01-01"})
        # A certificate reminder without its asset or its kind - the columns are nullable only for a year's mark.
        refused.append(
            {
                **good,
                "kind": "CERTIFICATE_RUNNING_OUT",
                "subject_type": "asset",
                "subject": asset,
                "key": f"CERTIFICATE_RUNNING_OUT|asset|{asset}|||2093-01-01",
            }
        )
    for values in refused:
        with SessionLocal() as db:
            with pytest.raises(IntegrityError):
                db.execute(text(insert), values)
            db.rollback()
