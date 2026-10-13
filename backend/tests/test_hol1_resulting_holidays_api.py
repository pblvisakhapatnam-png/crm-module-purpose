"""HOL-1 - the holidays that apply to a Work Order's lines: PBL's calendar as the Work Order changes it.

docs/agent/slices/hol-1-holiday-calendar.md, sections 1.2 (points 6, 8, 9 and 15), 5.3 and 14. The Work Order is Part
3's three-line chain: line 1's site in Gujarat, line 2's in Maharashtra, line 3 with no site. The calendar year is one
of the 2090s, owned by the test and removed when it ends (`holiday_calendar_test_support`).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.holiday_calendar.service import last_year_started
from tests.holiday_calendar_test_support import calendar_test_years
from tests.test_commercial_offers_api import auth_headers, client, cleanup_test_work_orders
from tests.test_slice_7c_work_order_line_detail import _delete_account_records
from tests.test_slice_7d_part_3_contract_period import READ_ROLES, _save_period, chain  # noqa: F401  (chain is a fixture)
from tests.test_slice_7d_work_order_line_billing_terms import _add as _add_terms


def _ok(response, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


def _add_site(account_public_id: str, state: str) -> str:
    body = {"address_type_code": "SITE", "address_line1": "Plot 4, Invented Estate", "city": "Somewhere", "state": state}
    return _ok(client.post(f"/api/accounts/{account_public_id}/addresses", headers=auth_headers("sales1"), json=body), 201)["address"]["public_id"]


def _set_site(record: dict, line_index: int, address_public_id: str) -> None:
    work_order = record["work_order_public_id"]
    line = record["line_public_ids"][line_index]
    details = _ok(client.get(f"/api/work-orders/{work_order}/line-details", headers=auth_headers("sales1")))
    detail = next(item for item in details if item["work_order_line_public_id"] == line)
    body = {"expected_detail_version": detail["detail_version"], "site_address_public_id": address_public_id}
    _ok(client.put(f"/api/work-orders/{work_order}/lines/{line}/detail", headers=auth_headers("sales1"), json=body))


def _calendar(year: int, *, complete: bool = False) -> None:
    holidays = [
        ("01-26", "Republic Day", "NATIONAL", []),
        ("03-22", "Holi", "FESTIVAL", []),
        ("04-14", "Tamil New Year", "FESTIVAL", ["IN-TN"]),
        ("05-01", "Gujarat Day", "FESTIVAL", ["IN-GJ"]),
        ("05-01", "Maharashtra Day", "NATIONAL", ["IN-MH"]),
    ]
    body = {
        "expected_version": None,
        "is_complete": complete,
        "holidays": [
            {
                "holiday_date": f"{year}-{month_day}",
                "holiday_kind_code": kind,
                "holiday_name": name,
                "applies_to_code": "STATES" if states else "ALL_INDIA",
                "state_codes": states,
            }
            for month_day, name, kind, states in holidays
        ],
    }
    _ok(client.put(f"/api/holiday-calendar/years/{year}", json=body, headers=auth_headers("admin1")))


def _changes(record: dict, changes: list[dict], *, version: int | None = None) -> None:
    body = {"expected_list_version": version, "holidays_answer_code": "CALENDAR_CHANGED", "changes": changes}
    _ok(client.put(f"/api/work-orders/{record['work_order_public_id']}/holidays", headers=auth_headers("sales1"), json=body))


def _resulting(record: dict, username: str = "readonly1") -> dict:
    return _ok(client.get(f"/api/work-orders/{record['work_order_public_id']}/holidays/resulting", headers=auth_headers(username)))


def _days(group: dict) -> list[tuple]:
    return [(day["holiday_date"][5:], day["day_code"], day["source_code"], day["name"], day["working_day_rate_code"]) for day in group["days"]]


@pytest.fixture
def wo(chain) -> Iterator[dict]:
    """The chain with sites on lines 1 and 2, a contract over one test year, and that year's calendar."""
    with calendar_test_years() as years:
        year = years[0]
        record = {**chain, "year": year}
        try:
            _set_site(record, 0, _add_site(chain["account_public_id"], "Gujarat"))
            _set_site(record, 1, _add_site(chain["account_public_id"], "Maharashtra"))
            assert _save_period(chain, contract_start_date=f"{year}-01-01", contract_end_date=f"{year}-12-31").status_code == 200
            _calendar(year)
            yield record
        finally:
            cleanup_test_work_orders(chain["work_order_public_ids"])
            _delete_account_records([chain["account_public_id"]])


# --- Without a contract start --------------------------------------------------------------------------------------


def test_without_a_contract_start_it_asks_for_one_and_still_names_each_lines_state(chain) -> None:
    try:
        _set_site(chain, 0, _add_site(chain["account_public_id"], "Gujarat"))
        body = _resulting(chain)
        assert (body["period_from"], body["period_to"], body["period_note_code"]) == (None, None, "NO_CONTRACT_START")
        assert body["period_message"] == "Record the contract start to see the holidays that apply."
        assert [(group["state_code"], group["problem_code"], group["line_numbers"], group["days"]) for group in body["groups"]] == [
            ("IN-GJ", None, [1], []),
            (None, "SITE_NOT_RECORDED", [2, 3], []),
        ]
        assert body["calendar_days"] == [] and body["years_not_complete"] == [] and body["change_notes"] == []
    finally:
        cleanup_test_work_orders(chain["work_order_public_ids"])
        _delete_account_records([chain["account_public_id"]])


# --- The calendar for each state's lines ----------------------------------------------------------------------------


def test_each_states_lines_get_its_calendar_and_a_line_with_no_site_the_all_india_holidays(wo) -> None:
    year = wo["year"]
    body = _resulting(wo)
    assert (body["period_from"], body["period_to"], body["period_note_code"]) == (f"{year}-01-01", f"{year}-12-31", None)
    gujarat, maharashtra, no_site = body["groups"]
    assert (gujarat["state_code"], gujarat["state_label"], gujarat["line_numbers"]) == ("IN-GJ", "Gujarat", [1])
    assert _days(gujarat) == [
        ("01-26", "HOLIDAY", "CALENDAR", "Republic Day", None),
        ("03-22", "HOLIDAY", "CALENDAR", "Holi", None),
        ("05-01", "HOLIDAY", "CALENDAR", "Gujarat Day", None),
    ]
    assert (maharashtra["state_code"], maharashtra["line_numbers"]) == ("IN-MH", [2])
    assert [day[3] for day in _days(maharashtra)] == ["Republic Day", "Holi", "Maharashtra Day"]
    assert (no_site["state_code"], no_site["problem_code"], no_site["line_numbers"]) == (None, "SITE_NOT_RECORDED", [3])
    assert no_site["problem_message"].startswith("Line 3: no site recorded, so only the all-India holidays are shown")
    assert [day[3] for day in _days(no_site)] == ["Republic Day", "Holi"]
    # The choices the form offers: the calendar holidays of the Work Order's sites, one row per date. Tamil Nadu's is
    # not among them - no line is there.
    days = {day["holiday_date"][5:]: day for day in body["calendar_days"]}
    assert list(days) == ["01-26", "03-22", "05-01"]
    assert days["01-26"]["line_numbers"] == [1, 2, 3]
    assert sorted((entry["holiday_name"], tuple(entry["state_labels"])) for entry in days["05-01"]["entries"]) == [
        ("Gujarat Day", ("Gujarat",)),
        ("Maharashtra Day", ("Maharashtra",)),
    ]
    assert days["05-01"]["line_numbers"] == [1, 2]
    assert body["years_not_complete"] == [year]


def test_a_year_marked_complete_is_no_longer_named(wo) -> None:
    year = wo["year"]
    current = _ok(client.get(f"/api/holiday-calendar/years/{year}", headers=auth_headers("admin1")))
    body = {"expected_version": current["year_version"], "is_complete": True, "holidays": [
        {"holiday_date": item["holiday_date"], "holiday_kind_code": item["holiday_kind_code"], "holiday_name": item["holiday_name"],
         "applies_to_code": item["applies_to_code"], "state_codes": [state["state_code"] for state in item["states"]]}
        for item in current["holidays"]
    ]}
    _ok(client.put(f"/api/holiday-calendar/years/{year}", json=body, headers=auth_headers("admin1")))
    assert _resulting(wo)["years_not_complete"] == []


def test_a_site_state_the_platform_does_not_know_is_named_with_what_to_put_right(wo) -> None:
    _set_site(wo, 2, _add_site(wo["account_public_id"], "Gujrat"))
    group = _resulting(wo)["groups"][2]
    assert (group["problem_code"], group["line_numbers"]) == ("SITE_STATE_NOT_RECOGNISED", [3])
    assert "the site's state 'Gujrat' is not a state or union territory the platform knows" in group["problem_message"]
    assert group["problem_message"].endswith("Correct the site address on the Account.")
    assert [day[3] for day in _days(group)] == ["Republic Day", "Holi"]


# --- The Work Order's changes ---------------------------------------------------------------------------------------


def test_working_days_and_added_holidays_change_every_lines_days(wo) -> None:
    year = wo["year"]
    # Line 1 records an overtime rate; line 2 records overtime as "not in the Work Order"; line 3 has no terms.
    assert _add_terms(wo, {"billing_uom_code": "DAY", "overtime_rate_method_code": "RATE_PER_HOUR", "overtime_rate_amount": "450.00"}).status_code == 201
    assert _add_terms(wo, {"billing_uom_code": "DAY", "overtime_rate_method_code": "NONE"}, line_index=1).status_code == 201
    _changes(
        wo,
        [
            {"change_code": "WORKING_DAY", "holiday_date": f"{year}-03-22", "working_day_rate_code": "OVERTIME_RATE", "description": "Plant runs"},
            {"change_code": "WORKING_DAY", "holiday_date": f"{year}-05-01", "working_day_rate_code": "NORMAL_RATE"},
            {"change_code": "HOLIDAY_ADDED", "holiday_date": f"{year}-08-29", "holiday_kind_code": "FESTIVAL", "description": "Site foundation day"},
        ],
    )
    gujarat, maharashtra, no_site = _resulting(wo)["groups"]
    assert _days(gujarat) == [
        ("01-26", "HOLIDAY", "CALENDAR", "Republic Day", None),
        ("03-22", "WORKING_DAY", "CALENDAR", "Holi", "OVERTIME_RATE"),
        ("05-01", "WORKING_DAY", "CALENDAR", "Gujarat Day", "NORMAL_RATE"),
        ("08-29", "HOLIDAY", "WORK_ORDER", "Site foundation day", None),
    ]
    assert gujarat["days"][1]["note"] == "Plant runs"
    # 1 May is the Work Order's change for every line (decision 27): Maharashtra's line works its own 1 May too.
    assert [day[1] for day in _days(maharashtra)] == ["HOLIDAY", "WORKING_DAY", "WORKING_DAY", "HOLIDAY"]
    assert [day[1] for day in _days(no_site)] == ["HOLIDAY", "WORKING_DAY", "HOLIDAY"]
    # The overtime rate a working day needs: line 1 has one; line 2's overtime is not in the Work Order; line 3 has no
    # terms (1.2, point 15). Only an overtime working day asks.
    holi = lambda group: next(day for day in group["days"] if day["holiday_date"].endswith("03-22"))  # noqa: E731
    assert [holi(group)["lines_without_overtime_rate"] for group in (gujarat, maharashtra, no_site)] == [[], [2], [3]]
    assert all(day["lines_without_overtime_rate"] == [] for day in gujarat["days"] + maharashtra["days"] if day["working_day_rate_code"] != "OVERTIME_RATE")


def test_a_change_that_does_nothing_more_than_the_calendar_is_noted(wo) -> None:
    year = wo["year"]
    _changes(
        wo,
        [
            {"change_code": "HOLIDAY_ADDED", "holiday_date": f"{year}-01-26", "holiday_kind_code": "NATIONAL"},
            {"change_code": "WORKING_DAY", "holiday_date": f"{year}-04-14", "working_day_rate_code": "NORMAL_RATE"},
            {"change_code": "WORKING_DAY", "holiday_date": f"{year}-08-15", "working_day_rate_code": "NORMAL_RATE"},
            {"change_code": "HOLIDAY_ADDED", "holiday_date": f"{year}-05-01", "holiday_kind_code": "FESTIVAL"},
        ],
    )
    notes = [(note["holiday_date"][5:], note["note_code"], note["message"]) for note in _resulting(wo)["change_notes"]]
    assert notes == [
        ("01-26", "ALREADY_IN_CALENDAR", "Already a holiday in PBL's calendar for every site of this Work Order."),
        ("04-14", "DOES_NOTHING", "Not a holiday in PBL's calendar for any site of this Work Order: making it a working day does nothing."),
        ("08-15", "DOES_NOTHING", "Not a holiday in PBL's calendar for any site of this Work Order: making it a working day does nothing."),
    ]
    # 1 May is not a calendar holiday for line 3, whose site is not known, so adding it does something there.
    no_site = _resulting(wo)["groups"][2]
    assert any(day["holiday_date"].endswith("05-01") and day["source_code"] == "WORK_ORDER" for day in no_site["days"])


def test_a_working_day_before_the_year_is_set_up_is_kept_and_takes_effect_when_the_calendar_has_it(wo) -> None:
    """1.2, point 6: entered before the calendar has the day, it is noted as doing nothing; once Admin adds the day, it
    applies with no change to the Work Order."""
    year = wo["year"]
    _changes(wo, [{"change_code": "WORKING_DAY", "holiday_date": f"{year}-11-01", "working_day_rate_code": "NORMAL_RATE"}])
    assert [note["note_code"] for note in _resulting(wo)["change_notes"]] == ["DOES_NOTHING"]
    current = _ok(client.get(f"/api/holiday-calendar/years/{year}", headers=auth_headers("admin1")))
    holidays = [
        {"holiday_date": item["holiday_date"], "holiday_kind_code": item["holiday_kind_code"], "holiday_name": item["holiday_name"],
         "applies_to_code": item["applies_to_code"], "state_codes": [state["state_code"] for state in item["states"]]}
        for item in current["holidays"]
    ] + [{"holiday_date": f"{year}-11-01", "holiday_kind_code": "FESTIVAL", "holiday_name": "Diwali", "applies_to_code": "ALL_INDIA", "state_codes": []}]
    _ok(client.put(f"/api/holiday-calendar/years/{year}", json={"expected_version": 1, "is_complete": False, "holidays": holidays}, headers=auth_headers("admin1")))
    body = _resulting(wo)
    assert body["change_notes"] == []
    assert ("11-01", "WORKING_DAY", "CALENDAR", "Diwali", "NORMAL_RATE") in _days(body["groups"][0])


# --- The days shown ---------------------------------------------------------------------------------------------------


def test_an_open_end_runs_to_the_end_of_the_last_year_started(wo) -> None:
    year = wo["year"]
    response = _save_period(wo, expected_period_version=1, contract_start_date=f"{year}-01-01", contract_end_basis_code="UNTIL_WORK_COMPLETE", contract_end_date=None)
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        last = max(year, last_year_started(db) or year)
    body = _resulting(wo)
    assert (body["period_note_code"], body["period_to"]) == ("OPEN_END", f"{last}-12-31")
    assert body["period_message"] == f"No end date is recorded, so the holidays are shown to 31 December {last}."


def test_days_before_the_contract_starts_are_not_shown(wo) -> None:
    year = wo["year"]
    assert _save_period(wo, expected_period_version=1, contract_start_date=f"{year}-02-01", contract_end_date=f"{year}-12-31").status_code == 200
    body = _resulting(wo)
    assert [day["holiday_date"][5:] for day in body["groups"][0]["days"]] == ["03-22", "05-01"]
    assert [day["holiday_date"][5:] for day in body["calendar_days"]] == ["03-22", "05-01"]


# --- It reads, and who may ------------------------------------------------------------------------------------------


def _event_count() -> int:
    with SessionLocal() as db:
        return int(db.execute(text("SELECT COUNT(*) FROM business_event")).scalar_one())


@pytest.mark.parametrize("username", READ_ROLES)
def test_every_role_that_reads_work_orders_reads_it_and_nothing_is_written(wo, username: str) -> None:
    headers = auth_headers(username)  # signing in records an event of its own, so it comes first
    before = _event_count()
    response = client.get(f"/api/work-orders/{wo['work_order_public_id']}/holidays/resulting", headers=headers)
    assert _ok(response)["groups"]
    assert _event_count() == before


def test_signed_out_and_unknown_are_refused(wo) -> None:
    assert client.get(f"/api/work-orders/{wo['work_order_public_id']}/holidays/resulting").status_code in (401, 403)
    assert client.get(f"/api/work-orders/{uuid4()}/holidays/resulting", headers=auth_headers("sales1")).status_code == 404
