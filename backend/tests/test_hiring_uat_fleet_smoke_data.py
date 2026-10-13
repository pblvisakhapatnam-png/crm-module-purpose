"""The Hiring site's pre-load for the user-test restart (`hiring-uat-fleet`, 9 October 2026), and its cleanup.

The owner decided the Hiring site starts with only the invented fleet, with its papers, and the holiday calendar; the
testers enter every customer, offer and Work Order themselves. The sheets (docs/uat-hiring/) name the machines and say
what each answers for a site, so these tests pin that: the answers a tester reads from "Check for a site", who each
"not yet recorded" reminder has reached on the first day, that nothing else is seeded, and that the calendar's years
are complete and hold the holidays written out below - independently of the code that seeds them (TE-8 round 1).
Cleanup must leave every table the run wrote as it found it, as for `hiring-uat-seeded`; like it, the snapshot leaves
out the accounts, because the authors a run writes as are created switched off when missing and are not the run's to
remove (hiring_uat.scenario_hiring_uat_fleet). The scenario refuses, writing nothing - not even an author - where either
calendar year is already started; the empty-fleet guard is tested with the other equipment scenarios
(test_ert1_smoke_data.py).

The calendar years are moved to two of the backend tests' own years (2090 to 2094, which the HOL-1 tests clear): the
current year and the next may be real data in a developer's database.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from tests.business_day_test_support import TODAY, held_to_the_test_day
from tests.test_commercial_offers_api import client
from tests.test_hiring_uat_smoke_data import HEADERS, _not_yet_recorded, _ok, _sign_in, _snapshot
from tooling.smoke_data import hiring_uat
from tooling.smoke_data.builders import create_holiday_calendar_year, equipment_asset_public_id
from tooling.smoke_data.cleanup import cleanup_manifest
from tooling.smoke_data import scenarios
from tooling.smoke_data.scenarios import run_scenario
from tooling.smoke_data.status import check_manifest_status

TEST_YEARS = (2093, 2094)

# The practice calendar the sheets rely on, written out here rather than read from the code under test.
FIXED_HOLIDAYS = [
    ("01-26", "NATIONAL", "Republic Day", []),
    ("05-01", "FESTIVAL", "Gujarat Day", ["IN-GJ"]),
    ("05-01", "NATIONAL", "Maharashtra Day", ["IN-MH"]),
    ("08-15", "NATIONAL", "Independence Day", []),
    ("10-02", "NATIONAL", "Gandhi Jayanti", []),
    ("12-25", "FESTIVAL", "Christmas", []),
]
EXPECTED_CALENDAR = {
    2026: sorted(FIXED_HOLIDAYS + [("03-04", "FESTIVAL", "Holi", []), ("11-08", "FESTIVAL", "Diwali", [])]),
    2027: sorted(FIXED_HOLIDAYS + [("03-22", "FESTIVAL", "Holi", []), ("10-29", "FESTIVAL", "Diwali", [])]),
}

MACHINES = {
    *(f"UAT-CC250-0{n}" for n in range(1, 7)),
    *(f"UAT-AC100-0{n}" for n in range(1, 10)),
    "UAT-AC100-01C",
    "UAT-CC80-01",
    "UAT-CC80-02",
    "UAT-XC60-01",
}

# What the pre-load must not write: the testers make all of these.
NOT_SEEDED = (
    "business_party", "crm_lead", "crm_opportunity", "crm_commercial_offer", "crm_work_order",
    "resource_requirement", "resource_assignment",
)  # fmt: skip


@pytest.fixture(scope="module", autouse=True)
def _on_the_test_day():
    with held_to_the_test_day():
        yield


@pytest.fixture
def test_years(monkeypatch):
    monkeypatch.setattr(hiring_uat, "calendar_years_to_seed", lambda today: TEST_YEARS)
    _clear_test_years()
    yield TEST_YEARS
    _clear_test_years()


def _clear_test_years() -> None:
    with SessionLocal() as db:
        for statement in (
            "DELETE FROM holiday_calendar_holiday_state s USING holiday_calendar_holiday h, holiday_calendar_year y "
            "WHERE h.id = s.holiday_id AND y.id = h.year_id AND y.calendar_year IN (2093, 2094)",
            "DELETE FROM holiday_calendar_holiday h USING holiday_calendar_year y "
            "WHERE y.id = h.year_id AND y.calendar_year IN (2093, 2094)",
            "DELETE FROM holiday_calendar_year WHERE calendar_year IN (2093, 2094)",
        ):
            db.execute(text(statement))
        db.commit()


def _count(table: str) -> int:
    with SessionLocal() as db:
        return int(db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())


def _check(number: str, state: str, first: int, last: int, central: bool = False) -> tuple[str, set[tuple[str, str]]]:
    """What "Check for a site" answers for a machine, from `first` to `last` days after the pre-load."""
    body = _ok(
        client.get(
            f"/api/eligibility/assets/{equipment_asset_public_id(number)}/check",
            params={
                "state_code": state,
                "period_from": (TODAY + timedelta(days=first)).isoformat(),
                "period_to": (TODAY + timedelta(days=last)).isoformat(),
                "central_government_site": central,
            },
            headers=HEADERS["ops1"],
        )
    )
    not_valid = {
        (result["kind_code"], result["outcome_code"])
        for result in body["results"]
        if result["outcome_code"] not in ("VALID", "NOT_APPLICABLE", "NOT_REQUIRED")
    }
    return body["overall_code"], not_valid


def _calendar(year: int) -> tuple[bool, list[tuple[str, str, str, list[str]]]]:
    with SessionLocal() as db:
        complete = db.execute(
            text("SELECT complete_marked_at IS NOT NULL FROM holiday_calendar_year WHERE calendar_year = :y"), {"y": year}
        ).scalar_one()
        rows = db.execute(
            text(
                "SELECT h.holiday_date, h.holiday_kind_code, h.holiday_name, "
                "COALESCE(array_agg(s.jurisdiction_code ORDER BY s.jurisdiction_code) FILTER (WHERE s.jurisdiction_code IS NOT NULL), '{}') "
                "FROM holiday_calendar_holiday h JOIN holiday_calendar_year y ON y.id = h.year_id "
                "LEFT JOIN holiday_calendar_holiday_state s ON s.holiday_id = h.id WHERE y.calendar_year = :y "
                "GROUP BY h.id, h.holiday_date, h.holiday_kind_code, h.holiday_name ORDER BY h.holiday_date, h.holiday_name"
            ),
            {"y": year},
        ).all()
    return bool(complete), sorted((day.strftime("%m-%d"), kind, name, list(states)) for day, kind, name, states in rows)


def test_the_years_seeded_are_this_year_and_the_next() -> None:
    assert hiring_uat.calendar_years_to_seed(date(2026, 10, 11)) == (2026, 2027)
    assert hiring_uat.calendar_years_to_seed(date(2026, 12, 31)) == (2026, 2027)


def test_the_practice_calendar_is_the_one_the_sheets_rely_on() -> None:
    for year, expected in EXPECTED_CALENDAR.items():
        assert hiring_uat.practice_calendar(year) == expected
    # Any other year holds the fixed-date holidays only.
    assert hiring_uat.practice_calendar(TEST_YEARS[0]) == sorted(FIXED_HOLIDAYS)


def test_the_pre_load_holds_the_fleet_and_the_calendar_only_and_cleanup_leaves_every_table_as_it_was(test_years) -> None:
    _sign_in("ops1", "admin1", "readonly1", "sales1", "finance1")
    before = _snapshot()
    not_seeded = {table: _count(table) for table in NOT_SEEDED}
    manifest = run_scenario(hiring_uat.FLEET_SCENARIO_NAME)
    try:
        with SessionLocal() as db:
            numbers = set(db.execute(text("SELECT machine_number FROM equipment_asset WHERE machine_number LIKE 'UAT-%'")).scalars())
        assert numbers == MACHINES
        assert {table: _count(table) for table in NOT_SEEDED} == not_seeded

        # PBL's calendar for both years, complete, holding the practice holidays.
        for year in TEST_YEARS:
            assert _calendar(year) == (True, sorted(FIXED_HOLIDAYS))

        # The answers the sheets name: an all-terrain crane for a central-government site in Gujarat, 10 to 30 days on.
        answers = {number: _check(number, "IN-GJ", 10, 30, central=True) for number in sorted(MACHINES) if number.startswith("UAT-AC100-0") and number != "UAT-AC100-01C"}
        assert {number: overall for number, (overall, _) in answers.items()} == {
            "UAT-AC100-01": "ELIGIBLE", "UAT-AC100-03": "ELIGIBLE",
            "UAT-AC100-06": "WARNING", "UAT-AC100-07": "WARNING",
            "UAT-AC100-02": "BLOCKED", "UAT-AC100-04": "BLOCKED", "UAT-AC100-05": "BLOCKED",
            "UAT-AC100-08": "BLOCKED", "UAT-AC100-09": "BLOCKED",
        }  # fmt: skip
        assert answers["UAT-AC100-02"][1] == {("PERMIT", "MISSING")}
        assert answers["UAT-AC100-04"][1] == {("FITNESS", "MISSING"), ("PERMIT", "MISSING")}
        assert answers["UAT-AC100-05"][1] == {("INSURANCE", "COPY_MISSING")}
        assert answers["UAT-AC100-06"][1] == {("POLLUTION_UNDER_CONTROL", "RUNS_OUT_IN_PERIOD")}
        assert answers["UAT-AC100-07"][1] == {("INSURANCE", "RUNS_OUT_IN_PERIOD")}
        # The crane whose permit covers Maharashtra only is refused in Gujarat and allocated in Maharashtra.
        assert _check("UAT-AC100-02", "IN-MH", 10, 30)[0] == "ELIGIBLE"

        # The 250 t crawlers for a job from 5 to 60 days on: two with a warning, one that cannot go, one with nothing.
        crawlers = {number: _check(number, "IN-GJ", 5, 60) for number in sorted(MACHINES) if number.startswith("UAT-CC250-")}
        assert crawlers["UAT-CC250-01"] == ("ELIGIBLE", set())
        assert crawlers["UAT-CC250-03"] == ("ELIGIBLE", set())
        for number in ("UAT-CC250-02", "UAT-CC250-04"):
            assert crawlers[number] == ("WARNING", {("THOROUGH_EXAMINATION", "RUNS_OUT_IN_PERIOD")})
        assert crawlers["UAT-CC250-05"] == ("BLOCKED", {("FITNESS", "MISSING"), ("PERMIT", "MISSING")})
        assert crawlers["UAT-CC250-06"][0] == "BLOCKED"

        # "Not yet recorded" reaches Admin at once, Operations after 7 days, Management after 14; Sales and Accounts
        # are on no path.
        nothing = {"UAT-CC250-06", "UAT-AC100-08", "UAT-AC100-09"}
        assert _not_yet_recorded("admin1", nothing) == nothing
        assert _not_yet_recorded("ops1", nothing) == {"UAT-CC250-06", "UAT-AC100-08"}
        assert _not_yet_recorded("readonly1", nothing) == {"UAT-CC250-06"}
        for username in ("sales1", "finance1"):
            assert _ok(client.get("/api/eligibility/alerts", headers=HEADERS[username]))["items"] == []
    finally:
        cleanup_manifest(manifest)
    assert check_manifest_status(manifest)["residue_clear"] is True
    after = _snapshot()
    assert {table: (before[table], after.get(table)) for table in before if after.get(table) != before[table]} == {}


def test_the_pre_load_refuses_and_writes_nothing_where_a_calendar_year_is_already_started(test_years, monkeypatch) -> None:
    with SessionLocal() as db:
        admin = str(db.execute(text("SELECT public_id FROM app_user WHERE username = 'admin1'")).scalar_one())
    create_holiday_calendar_year(actor_public_id=admin, calendar_year=TEST_YEARS[1], holidays=[("01-26", "NATIONAL", "Republic Day", [])])

    # On a site the actor may not exist yet, and resolving it creates it: the refusal must come first (TE-8 round 1).
    def resolved_before_the_refusal(*args, **kwargs):
        raise AssertionError("the actor was resolved - and on a site, created - before the calendar refusal")

    monkeypatch.setattr(scenarios, "resolve_actor", resolved_before_the_refusal)
    written = ("equipment_asset", "equipment_model", "holiday_calendar_year", "holiday_calendar_holiday", "business_event", "app_user", "user_role")
    before = {table: _count(table) for table in written}
    try:
        manifest = run_scenario(hiring_uat.FLEET_SCENARIO_NAME)
    except hiring_uat.CalendarSeedRefused as refusal:
        assert f"for {TEST_YEARS[1]} is already started" in str(refusal)
    else:  # seeded after all: removed before failing, so a broken refusal never leaves a run behind
        cleanup_manifest(manifest)
        pytest.fail("hiring-uat-fleet seeded over a calendar year someone had started.")
    assert {table: _count(table) for table in written} == before


def test_the_pre_load_refuses_a_held_fleet_before_it_writes_anything_not_even_an_author(test_years, monkeypatch) -> None:
    """The empty-fleet guard, for this scenario on a site: with a Plum preview waiting, then with a machine held, it
    refuses before resolving - and on a site creating - an author, and before starting a calendar year; no user, role,
    calendar row, business event or equipment row changes (TE-8 round 3)."""
    from tests.equipment_test_support import equipment_created_here, plum_report, plum_row, suffix
    from tests.test_commercial_offers_api import auth_headers
    from tooling.smoke_data.builders import EquipmentSeedRefused

    def reached(*args, **kwargs):
        raise AssertionError("the scenario went past its empty-fleet guard")

    monkeypatch.setattr(scenarios, "resolve_actor", reached)
    monkeypatch.setattr(scenarios, "require_fleet_calendar_years_free", reached)
    written = (
        "app_user", "user_role", "holiday_calendar_year", "holiday_calendar_holiday", "business_event",
        "equipment_asset", "equipment_model", "equipment_source_import",
    )  # fmt: skip
    admin = auth_headers("admin1")
    with equipment_created_here():
        number = f"HELD-{suffix()}"
        waiting = client.post(
            "/api/equipment-reference/imports",
            data={"report_date": TODAY.isoformat()},
            files={"file": ("held.csv", plum_report([plum_row(number=number, category="FORK LIFT", capacity="3")]), "text/csv")},
            headers=admin,
        ).json()["equipment_import"]
        for held in ("a waiting preview", "a held machine"):
            if held == "a held machine":
                published = client.post(
                    f"/api/equipment-reference/imports/{waiting['import_public_id']}/publish",
                    json={"expected_preview_version": waiting["preview_version"]},
                    headers=admin,
                )
                assert published.status_code == 200, published.text
            before = {table: _count(table) for table in written}
            try:
                manifest = run_scenario(hiring_uat.FLEET_SCENARIO_NAME)
            except EquipmentSeedRefused:
                pass
            else:  # seeded after all: removed before failing
                cleanup_manifest(manifest)
                pytest.fail(f"hiring-uat-fleet seeded over {held}.")
            assert {table: _count(table) for table in written} == before, held
