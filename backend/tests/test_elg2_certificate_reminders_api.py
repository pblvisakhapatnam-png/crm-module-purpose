"""ELG-2 - certificate reminders and escalation, through the API and at the database.

docs/agent/slices/elg-2-certificate-reminders.md, sections 5 to 10 and 14. The rules are the owner's answers of 27
September 2026 (ELG-1 Q14 to Q18) and 1 October 2026 (Q19, Q19a, Q20). Every machine is invented and carries a
run-unique token; each test looks only at its own by searching for it.

The fleet is 8A core's - cranes of one 250 t crawler model, a 100 t crawler, an all-terrain crane, an unmapped crane,
and kit held for the 250 t model - with, added here:
- on the 100 t crawler (`small`), papers running out in 20, 10 and 5 days, and a load test that ran out 2 days ago;
- a hook block (`short_hook`) whose thorough examination runs out in 30 days.
`bare` has nothing recorded: its papers are "not yet recorded".
"""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.eligibility import alerts as alerts_module
from app.modules.eligibility import ports
from app.modules.resource_assignments import service as assignment_service
from app.shared import business_time
from tests.business_day_test_support import TODAY, dated_on_the_test_day, held_to_the_test_day
from tests.eligibility_test_support import eligibility_created_here
from tests.test_8a_equipment_allocation import END, START, Fleet as AllocationFleet
from tests.test_8a_equipment_allocation import _add_kit, _allocated, _line_detail, _post, _requirement, crane_work_order
from tests.test_commercial_offers_api import auth_headers, client
from tests.test_elg1_machine_eligibility_api import _mark, _recorded, _status

ALERTS = "/api/eligibility/alerts"
SETTINGS = "/api/eligibility/alert-settings"
EQUIPMENT = "/api/equipment-reference"
ADMIN = "admin1"


def _ok(response, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


def _detail(response, status: int = 422) -> str:
    assert response.status_code == status, response.text
    return response.json()["detail"]


def _alerts(username: str = ADMIN, **params) -> dict:
    query = {"limit": 500, **params}
    return _ok(client.get(ALERTS, params=query, headers=auth_headers(username)))


def _items(username: str, search: str, **params) -> list[dict]:
    return _alerts(username, search=search, **params)["items"]


def _by_kind(items: list[dict]) -> dict[str, dict]:
    return {item["kind_code"]: item for item in items}


def _seen(username: str, *pairs: tuple[str, str], headers: dict[str, str] | None = None):
    body = {"items": [{"reminder_key": key, "reminder_on": on} for key, on in pairs]}
    return client.post(f"{ALERTS}/seen", json=body, headers=headers or auth_headers(username))


def _event_count() -> int:
    with SessionLocal() as db:
        return int(db.execute(text("SELECT COUNT(*) FROM business_event")).scalar_one())


class Fleet(AllocationFleet):
    """8A core's fleet, with papers running out on the 100 t crawler and a hook block examined for 30 days more."""

    def __init__(self) -> None:
        super().__init__()
        for kind in ("REGISTRATION", "ROAD_TAX"):
            _ok(_mark(self.small, kind), 201)
        _recorded(self.small, "INSURANCE", valid_until=TODAY + timedelta(days=20))
        _recorded(self.small, "POLLUTION_UNDER_CONTROL", valid_until=TODAY + timedelta(days=10))
        _recorded(self.small, "THOROUGH_EXAMINATION", valid_until=TODAY + timedelta(days=5))
        ran_out = TODAY - timedelta(days=400)
        _recorded(self.small, "LOAD_TEST", issued_on=ran_out, valid_from=ran_out, valid_until=TODAY - timedelta(days=2))
        models = _ok(client.get(f"{EQUIPMENT}/models", headers=auth_headers(ADMIN)))
        hook_model = next(item for item in models if item["model_name"] == f"CC 250 hook {self.sfx}")
        self.short_hook = self._kit(hook_model, 1)
        _recorded(self.short_hook, "THOROUGH_EXAMINATION", valid_until=TODAY + timedelta(days=30))
        _recorded(self.short_hook, "LOAD_TEST")


@pytest.fixture(scope="module", autouse=True)
def _on_the_test_day():
    # A reminder begins on the day its machine was added (dated in `fleet`) or its allocation or kit line recorded:
    # Resource Assignments' clock, which stamps those two, is held too.
    with held_to_the_test_day((assignment_service, "_now")):
        yield


@pytest.fixture(scope="module")
def fleet():
    with eligibility_created_here():
        with dated_on_the_test_day("equipment_asset"):
            made = Fleet()
        yield made


@pytest.fixture
def settings_restored() -> Iterator[None]:
    """A test that saves a version of a setting removes it after: settings are never edited by design, so only the
    test's own rows are deleted, newest first."""
    with SessionLocal() as db:
        boundary = int(db.execute(text("SELECT COALESCE(MAX(id), 0) FROM eligibility_alert_setting")).scalar_one())
    try:
        yield
    finally:
        with SessionLocal() as db:
            for table in ("eligibility_alert_band", "eligibility_alert_step"):
                db.execute(text(f"DELETE FROM {table} WHERE setting_id > :boundary"), {"boundary": boundary})
            db.execute(text("DELETE FROM eligibility_alert_setting WHERE id > :boundary"), {"boundary": boundary})
            db.commit()


def _on(monkeypatch, day: date) -> None:
    """Read the reminders as on another day: the service's today, as the routes take it."""
    monkeypatch.setattr(business_time, "india_today", lambda: day)


# --- The renewal list's reminders, and who they reach -----------------------------------------------------------


def test_papers_running_out_reach_each_role_as_the_standard_path_says(fleet):
    search = fleet.number("SMALL")
    admin = _by_kind(_items(ADMIN, search))
    assert set(admin) == {"INSURANCE", "POLLUTION_UNDER_CONTROL", "THOROUGH_EXAMINATION", "LOAD_TEST"}
    for kind, days in (("INSURANCE", 20), ("POLLUTION_UNDER_CONTROL", 10), ("THOROUGH_EXAMINATION", 5), ("LOAD_TEST", -2)):
        item = admin[kind]
        assert item["reminder_kind_code"] == "CERTIFICATE_RUNNING_OUT"
        assert item["date_on"] == (TODAY + timedelta(days=days)).isoformat()
        assert item["reason_code"] == "RUNS_OUT"
        assert item["allocation"] is None
        # Added today, inside the schedule's reach: flagged at once, its first reminder today.
        assert item["began_on"] == TODAY.isoformat()
        assert item["first_reminder_on"] == item["reminder_on"] == TODAY.isoformat()
        assert item["reminders_so_far"] == 1
    assert [step["role_code"] for step in admin["INSURANCE"]["reached"]] == ["ADMIN"]
    assert [step["role_code"] for step in admin["POLLUTION_UNDER_CONTROL"]["reached"]] == ["ADMIN", "OPERATIONS_USER"]
    assert [step["role_code"] for step in admin["LOAD_TEST"]["reached"]] == ["ADMIN", "OPERATIONS_USER", "MANAGEMENT_READ_ONLY"]
    assert set(_by_kind(_items("ops1", search))) == {"POLLUTION_UNDER_CONTROL", "THOROUGH_EXAMINATION", "LOAD_TEST"}
    assert set(_by_kind(_items("readonly1", search))) == {"THOROUGH_EXAMINATION", "LOAD_TEST"}
    for username in ("sales1", "manager1", "finance1"):
        assert _items(username, search) == []
    # The road papers marked not applicable without an end raise nothing.
    assert "REGISTRATION" not in admin and "ROAD_TAX" not in admin


def test_papers_not_yet_entered_reach_the_fleet_admin_first_then_operations_and_management(fleet, monkeypatch):
    search = fleet.number("BARE")
    admin = _by_kind(_items(ADMIN, search))
    assert {"REGISTRATION", "INSURANCE", "POLLUTION_UNDER_CONTROL", "ROAD_TAX", "THOROUGH_EXAMINATION", "LOAD_TEST"} <= set(admin)
    for item in admin.values():
        assert item["reminder_kind_code"] == "NOT_YET_RECORDED"
        assert item["reason_code"] == "MACHINE_ADDED"
        assert item["date_on"] == TODAY.isoformat()
        assert [step["role_code"] for step in item["reached"]] == ["ADMIN"]
    assert _items("ops1", search) == [] and _items("readonly1", search) == []
    _on(monkeypatch, TODAY + timedelta(days=7))
    assert _items("ops1", search) and _items("readonly1", search) == []
    _on(monkeypatch, TODAY + timedelta(days=14))
    seen_by_management = _by_kind(_items("readonly1", search))
    assert seen_by_management["INSURANCE"]["reminders_so_far"] == 15


def test_a_retired_piece_raises_no_reminder(fleet):
    sling = _ok(client.get(f"{EQUIPMENT}/machines/{fleet.sling}", headers=auth_headers(ADMIN)))
    assert _by_kind(_items(ADMIN, sling["asset_reference"]))["THOROUGH_EXAMINATION"]["reminder_kind_code"] == "NOT_YET_RECORDED"
    _ok(
        client.post(
            f"{EQUIPMENT}/machines/{fleet.sling}/retire",
            json={"expected_asset_version": sling["asset_version"], "reason_code": "SCRAPPED", "retired_on": TODAY.isoformat(), "note": None},
            headers=auth_headers(ADMIN),
        )
    )
    assert _items(ADMIN, sling["asset_reference"]) == []


def test_a_renewal_recorded_ahead_without_its_copy_is_dated_by_the_day_the_cover_before_it_ends(fleet):
    hook = _ok(client.get(f"{EQUIPMENT}/machines/{fleet.hook}", headers=auth_headers(ADMIN)))["asset_reference"]
    assert "THOROUGH_EXAMINATION" not in _by_kind(_items(ADMIN, hook))
    _recorded(fleet.hook, "THOROUGH_EXAMINATION", copy=False, issued_on=TODAY, valid_from=TODAY + timedelta(days=20))
    item = _by_kind(_items(ADMIN, hook))["THOROUGH_EXAMINATION"]
    # The examination in force is cut short by the renewal's missing copy: the reminder says so, dated by the day the
    # cover ends.
    assert (item["reminder_kind_code"], item["reason_code"], item["date_on"]) == (
        "CERTIFICATE_RUNNING_OUT", "COPY_MISSING", (TODAY + timedelta(days=19)).isoformat(),
    )


def test_certificates_dated_at_the_first_and_last_day_a_date_can_be_are_reminded_without_failing(fleet):
    search = fleet.number("UNKNOWN")
    first = date(1, 1, 1)
    _recorded(fleet.unknown, "INSURANCE", issued_on=first, valid_from=first, valid_until=first)
    item = _by_kind(_items(ADMIN, search))["INSURANCE"]
    assert (item["date_on"], item["reason_code"]) == ("0001-01-01", "RUNS_OUT")
    assert [step["role_code"] for step in item["reached"]] == ["ADMIN", "OPERATIONS_USER", "MANAGEMENT_READ_ONLY"]
    _recorded(fleet.unknown, "INSURANCE", issued_on=TODAY, valid_from=TODAY, valid_until=date(9999, 12, 31))
    assert "INSURANCE" not in _by_kind(_items(ADMIN, search))
    assert _ok(client.get(f"{ALERTS}/count", headers=auth_headers("readonly1")))["total"] >= 0


def test_a_renewal_with_its_copy_ends_the_reminder_and_one_without_its_copy_keeps_one(fleet, monkeypatch):
    search = fleet.number("SPARE")
    assert _items(ADMIN, search) == []
    # An examination recorded later, covering only three more days, is in force: reminded, to everyone.
    _recorded(fleet.spare, "THOROUGH_EXAMINATION", issued_on=TODAY, valid_from=TODAY, valid_until=TODAY + timedelta(days=3))
    (short,) = _items(ADMIN, search)
    assert (short["kind_code"], short["date_on"], short["reason_code"]) == ("THOROUGH_EXAMINATION", (TODAY + timedelta(days=3)).isoformat(), "RUNS_OUT")
    # Renewed the same day, with its copy: the reminder is gone.
    _recorded(fleet.spare, "THOROUGH_EXAMINATION", issued_on=TODAY, valid_from=TODAY)
    assert _items(ADMIN, search) == []
    # Renewed again, from tomorrow, without its copy: covered until today, then short - "running out", not "not yet
    # recorded", as the machine has had its papers since it was added.
    _recorded(fleet.spare, "THOROUGH_EXAMINATION", copy=False, issued_on=TODAY, valid_from=TODAY + timedelta(days=1))
    (ahead,) = _items(ADMIN, search)
    assert (ahead["reminder_kind_code"], ahead["reason_code"], ahead["date_on"]) == (
        "CERTIFICATE_RUNNING_OUT", "COPY_MISSING", TODAY.isoformat(),
    )
    # Once it has taken over, without its copy: the same reminder - the same date, the same reason (ELG2-R2-002).
    _on(monkeypatch, TODAY + timedelta(days=2))
    (taken_over,) = _items(ADMIN, search)
    assert taken_over["outcome_code"] == "COPY_MISSING"
    assert (taken_over["reminder_key"], taken_over["reason_code"]) == (ahead["reminder_key"], "COPY_MISSING")
    # Marked as seen; then another without its copy takes over that day, and a same-day replacement of it: the cover
    # ended once, so each is the same reminder, still seen (ELG2-R4-001).
    assert _ok(_seen(ADMIN, (taken_over["reminder_key"], taken_over["reminder_on"]))) == {"marked": 1, "already": 0}
    for _ in range(2):
        _recorded(fleet.spare, "THOROUGH_EXAMINATION", copy=False, issued_on=TODAY, valid_from=TODAY + timedelta(days=2))
        (again,) = _items(ADMIN, search)
        assert (again["reminder_key"], again["date_on"], again["seen_by_me"]) == (ahead["reminder_key"], TODAY.isoformat(), True)


# --- The allocation reminders ------------------------------------------------------------------------------------


def _assignment_reminders(username: str, assignment: dict) -> list[dict]:
    return [item for item in _items(username, assignment["assignment_reference"]) if item["allocation"] is not None]


def test_a_certificate_running_out_during_the_job_reaches_operations_at_once(fleet):
    cover_ends = date.fromisoformat(_status(fleet.warns, "THOROUGH_EXAMINATION")["cover_ends_on"])
    with crane_work_order() as wo:
        held = _allocated(wo, fleet.warns, accept_warnings=True)
        (item,) = _assignment_reminders("ops1", held)
        assert item["reminder_kind_code"] == "DURING_JOB"
        assert (item["kind_code"], item["date_on"], item["outcome_code"]) == ("THOROUGH_EXAMINATION", cover_ends.isoformat(), "RUNS_OUT_IN_PERIOD")
        assert item["first_reminder_on"] == item["began_on"] == TODAY.isoformat()
        assert [step["role_code"] for step in item["reached"]] == ["ADMIN", "OPERATIONS_USER"]
        allocation = item["allocation"]
        assert allocation["assignment_public_id"] == held["assignment_public_id"]
        assert allocation["work_order_code"] == wo["work_order_code"]
        assert (allocation["site_state_code"], allocation["site_state_label"], allocation["central_government_site"]) == ("IN-MH", "Maharashtra", False)
        assert (allocation["period_from"], allocation["period_to"]) == (START.isoformat(), END.isoformat())
        assert allocation["trip_number"] is None and allocation["kit_line_public_id"] is None
        # Management from 7 days before the cover ends, not yet.
        assert _assignment_reminders("readonly1", held) == []
        _ok(_post(held, "release", reason_code="NOT_NEEDED"))
        assert _assignment_reminders(ADMIN, held) == []


def test_a_job_starting_after_the_cover_ends_is_reminded_before_it_starts(fleet):
    cover_ends = date.fromisoformat(_status(fleet.warns, "THOROUGH_EXAMINATION")["cover_ends_on"])
    with crane_work_order() as wo:
        later = _requirement(wo, units=1, start=cover_ends + timedelta(days=5), end=END)
        held = _allocated(
            {**wo, "requirement": later}, fleet.warns, accept_warnings=True, planned_from=cover_ends + timedelta(days=5), planned_to=END
        )
        (item,) = _assignment_reminders(ADMIN, held)
        assert (item["reminder_kind_code"], item["outcome_code"], item["date_on"]) == (
            "BEFORE_JOB_STARTS", "RUNS_OUT_BEFORE_START", cover_ends.isoformat(),
        )


def test_kit_on_a_trip_is_reminded_over_its_own_days_until_it_is_removed(fleet):
    with crane_work_order() as wo:
        held = _allocated(wo, fleet.ok)
        listed = _ok(_add_kit(held, [(fleet.short_hook, 1)], accept_warnings=True), 201)["assignment"]
        line = listed["trips"][0]["kit"][0]
        (item,) = _assignment_reminders("ops1", held)
        assert item["asset"]["asset_public_id"] == fleet.short_hook
        assert (item["reminder_kind_code"], item["kind_code"], item["date_on"]) == (
            "DURING_JOB", "THOROUGH_EXAMINATION", (TODAY + timedelta(days=30)).isoformat(),
        )
        assert (item["allocation"]["trip_number"], item["allocation"]["kit_line_public_id"]) == (1, line["kit_line_public_id"])
        assert item["allocation"]["period_from"] == line["busy_from"]
        # A renewal recorded ahead, starting in 10 days, without its copy: the reminder is about the copy, dated by
        # the day the cover now ends (ELG2-R1-001, ELG2-R2-002).
        _recorded(fleet.short_hook, "THOROUGH_EXAMINATION", copy=False, issued_on=TODAY, valid_from=TODAY + timedelta(days=10))
        (renewed,) = _assignment_reminders("ops1", held)
        assert (renewed["reminder_kind_code"], renewed["reason_code"], renewed["date_on"]) == (
            "DURING_JOB", "COPY_MISSING", (TODAY + timedelta(days=9)).isoformat(),
        )
        _ok(_post(listed, f"kit/{line['kit_line_public_id']}/remove"))
        assert _assignment_reminders("ops1", held) == []


def test_fitness_and_a_permit_for_a_job_are_dated_by_a_transport_registration_taking_effect_before_it_starts(fleet):
    # ELG2-R2-003 through the routes (ELG2-R3-004): a registration saying transport, taking effect the day before the
    # job starts, makes fitness and a permit needed for the job from that day - as the allocation's check decides it.
    takes_effect = START - timedelta(days=1)
    with crane_work_order() as wo:
        held = _allocated(wo, fleet.ok)
        registration = _recorded(fleet.ok, "REGISTRATION", registered_as_code="TRANSPORT", issued_on=TODAY, valid_from=takes_effect)
        try:
            reminders = _by_kind(_assignment_reminders("ops1", held))
            for kind in ("FITNESS", "PERMIT"):
                item = reminders[kind]
                assert (item["reminder_kind_code"], item["outcome_code"], item["reason_code"], item["date_on"]) == (
                    "BEFORE_JOB_STARTS", "MISSING", "REGISTERED_TRANSPORT", takes_effect.isoformat(),
                )
            # Today the registration is not yet in force: the machine itself needs neither yet.
            own = [item["kind_code"] for item in _items(ADMIN, fleet.number("OK")) if item["allocation"] is None]
            assert not {"FITNESS", "PERMIT"} & set(own)
        finally:
            _ok(
                client.post(
                    f"/api/eligibility/certificates/{registration}/withdraw",
                    json={"reason": "Recorded for this test only."},
                    headers=auth_headers(ADMIN),
                )
            )


def test_an_allocation_whose_site_cannot_be_judged_raises_no_allocation_reminder(fleet):
    with crane_work_order() as wo:
        held = _allocated(wo, fleet.warns, accept_warnings=True)
        assert _assignment_reminders(ADMIN, held)
        _line_detail(wo, site_central_government=None)
        assert _assignment_reminders(ADMIN, held) == []
        # The machine itself is still reminded by the renewal list.
        assert any(item["allocation"] is None for item in _items(ADMIN, fleet.number("WARNS")))


def test_the_allocation_reminders_need_resource_assignment_read(fleet, monkeypatch):
    with crane_work_order() as wo:
        held = _allocated(wo, fleet.warns, accept_warnings=True)
        assert _assignment_reminders("ops1", held)
        monkeypatch.setattr(alerts_module, "has_permission", lambda db, roles, code: False)
        assert _assignment_reminders("ops1", held) == []
        assert _items("ops1", fleet.number("SMALL"))


def test_without_resource_assignments_loaded_the_reminders_fail_closed(fleet, monkeypatch):
    monkeypatch.setattr(ports, "_registered", [])
    with pytest.raises(RuntimeError, match="Resource Assignments is not loaded"):
        client.get(ALERTS, headers=auth_headers(ADMIN))


# --- Seen ----------------------------------------------------------------------------------------------------------


def test_marking_a_reminder_seen_quiets_it_for_that_person_until_its_next_reminder_day(fleet, monkeypatch):
    search = fleet.number("SMALL")
    puc = _by_kind(_items("ops1", search))["POLLUTION_UNDER_CONTROL"]
    before = _ok(client.get(f"{ALERTS}/count", headers=auth_headers("ops1")))
    # Signing in records an event of its own, so the headers come first.
    headers = auth_headers("ops1")
    events = _event_count()
    assert _ok(_seen("ops1", (puc["reminder_key"], puc["reminder_on"]), headers=headers)) == {"marked": 1, "already": 0}
    assert _event_count() == events
    after = _ok(client.get(f"{ALERTS}/count", headers=auth_headers("ops1")))
    assert (after["unseen"], after["total"]) == (before["unseen"] - 1, before["total"])
    assert "POLLUTION_UNDER_CONTROL" not in _by_kind(_items("ops1", search, unseen_only=True))
    mine = _by_kind(_items("ops1", search))["POLLUTION_UNDER_CONTROL"]
    assert mine["seen_by_me"] is True and [item["display_name"] for item in mine["seen_by"]]
    # Others see who has seen it; it is not seen for them.
    theirs = _by_kind(_items(ADMIN, search))["POLLUTION_UNDER_CONTROL"]
    assert theirs["seen_by_me"] is False and len(theirs["seen_by"]) == 1
    # Again: nothing more.
    assert _ok(_seen("ops1", (puc["reminder_key"], puc["reminder_on"]))) == {"marked": 0, "already": 1}
    # Ten days before, its next reminder day is 8 days before: until then it stays seen; then it is due again.
    _on(monkeypatch, TODAY + timedelta(days=1))
    assert _by_kind(_items("ops1", search))["POLLUTION_UNDER_CONTROL"]["seen_by_me"] is True
    _on(monkeypatch, TODAY + timedelta(days=2))
    again = _by_kind(_items("ops1", search))["POLLUTION_UNDER_CONTROL"]
    assert again["seen_by_me"] is False and again["reminder_on"] == (TODAY + timedelta(days=2)).isoformat()


def test_seen_is_refused_for_a_reminder_that_has_not_reached_the_person_or_has_moved_on(fleet):
    search = fleet.number("SMALL")
    admin = _by_kind(_items(ADMIN, search))
    insurance, exam, puc = admin["INSURANCE"], admin["THOROUGH_EXAMINATION"], admin["POLLUTION_UNDER_CONTROL"]
    # Operations is reached from 15 days before; the insurance runs out in 20.
    assert "no longer due for you" in _detail(_seen("ops1", (insurance["reminder_key"], insurance["reminder_on"])), 404)
    yesterday = (TODAY - timedelta(days=1)).isoformat()
    assert "moved on" in _detail(_seen("ops1", (exam["reminder_key"], yesterday)), 409)
    # All or none: the good one is not marked either.
    assert "moved on" in _detail(_seen("ops1", (exam["reminder_key"], exam["reminder_on"]), (puc["reminder_key"], yesterday)), 409)
    assert "no longer due" in _detail(_seen("ops1", (exam["reminder_key"], exam["reminder_on"]), (insurance["reminder_key"], insurance["reminder_on"])), 404)
    assert _by_kind(_items("ops1", search))["THOROUGH_EXAMINATION"]["seen_by_me"] is False
    assert "at least one" in _detail(client.post(f"{ALERTS}/seen", json={"items": []}, headers=auth_headers("ops1")))
    assert client.post(f"{ALERTS}/seen", json={"items": [], "extra": 1}, headers=auth_headers("ops1")).status_code == 422


def test_management_may_mark_seen_and_it_changes_nothing_else(fleet):
    search = fleet.number("SMALL")
    load_test = _by_kind(_items("readonly1", search))["LOAD_TEST"]
    assert _ok(_seen("readonly1", (load_test["reminder_key"], load_test["reminder_on"])))["marked"] == 1
    still = _by_kind(_items("readonly1", search))["LOAD_TEST"]
    assert still["reached"] == load_test["reached"] and still["date_on"] == load_test["date_on"]
    assert _status(fleet.small, "LOAD_TEST")["outcome_code"] == "RUN_OUT"


# --- The list ----------------------------------------------------------------------------------------------------


def test_the_list_filters_orders_counts_and_pages(fleet):
    search = fleet.number("SMALL")
    whole = _alerts(ADMIN, search=search)
    assert whole["total"] == 4 and whole["today"] == TODAY.isoformat()
    # Earliest date first: what has run out comes first.
    assert [item["kind_code"] for item in whole["items"]] == ["LOAD_TEST", "THOROUGH_EXAMINATION", "POLLUTION_UNDER_CONTROL", "INSURANCE"]
    # HOL-1 added a fifth kind: PBL's holiday calendar not set up.
    assert set(whole["counts"]["by_kind"]) == {
        "CERTIFICATE_RUNNING_OUT", "NOT_YET_RECORDED", "BEFORE_JOB_STARTS", "DURING_JOB", "HOLIDAY_CALENDAR_NOT_SET_UP",
    }
    paged = _alerts(ADMIN, search=search, limit=1, offset=1)
    assert paged["total"] == 4 and [item["kind_code"] for item in paged["items"]] == ["THOROUGH_EXAMINATION"]
    assert _alerts(ADMIN, search=search, reminder_kind_code="NOT_YET_RECORDED")["items"] == []
    assert "kind of reminder" in _detail(client.get(ALERTS, params={"reminder_kind_code": "SOMETIME"}, headers=auth_headers(ADMIN)))
    count = _ok(client.get(f"{ALERTS}/count", headers=auth_headers(ADMIN)))
    listed = _alerts(ADMIN)
    assert (count["total"], count["unseen"]) == (listed["counts"]["total"], listed["counts"]["unseen"])


def test_no_answer_carries_a_certificate_number_issuer_or_reason(fleet):
    view = _ok(client.get(f"/api/eligibility/assets/{fleet.small}/certificates", headers=auth_headers(ADMIN)))
    secrets = [item["number"] for item in view["certificates"]] + ["Invented Authority"]
    secrets += [item["reason"] for item in view["marks"] if item["reason"]]
    text_ = json.dumps(_alerts(ADMIN, search=fleet.number("SMALL")))
    assert secrets and not [secret for secret in secrets if secret in text_]


# --- Settings ------------------------------------------------------------------------------------------------------


def _settings(username: str = "readonly1") -> dict:
    return _ok(client.get(SETTINGS, headers=auth_headers(username)))


def _current(kind: str) -> dict:
    return next(item for item in _settings()["settings"] if item["reminder_kind_code"] == kind)["current"]


def _save(kind: str, *, version: int, bands: list[tuple[int, int]], steps: list[tuple[str, str, int | None]], username: str = ADMIN):
    body = {
        "expected_version": version,
        "bands": [{"from_days_before": start, "every_days": every} for start, every in bands],
        "steps": [
            {"role_code": role, "starts_code": starts, "from_days_before": days, "channel_codes": ["SCREEN"]}
            for role, starts, days in steps
        ],
    }
    return client.post(f"{SETTINGS}/{kind}", json=body, headers=auth_headers(username))


STANDARD_BANDS = [(60, 30), (15, 7), (7, 1), (0, 1)]
STANDARD_STEPS = [("ADMIN", "FIRST_REMINDER", None), ("OPERATIONS_USER", "DAYS_BEFORE", 15), ("MANAGEMENT_READ_ONLY", "DAYS_BEFORE", 7)]


def test_the_standard_settings_come_with_the_package():
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT s.reminder_kind_code, s.saved_by, "
                "(SELECT string_agg(b.from_days_before || '/' || b.every_days, ',' ORDER BY b.band_number) FROM eligibility_alert_band b WHERE b.setting_id = s.id) AS bands, "
                "(SELECT string_agg(t.role_code || ':' || t.starts_code || ':' || COALESCE(t.from_days_before::text, '') || ':' || array_to_string(t.channel_codes, '+'), ',' ORDER BY t.step_number) "
                " FROM eligibility_alert_step t WHERE t.setting_id = s.id) AS steps "
                "FROM eligibility_alert_setting s WHERE s.version_number = 1 ORDER BY s.reminder_kind_code"
            )
        ).fetchall()
    found = {row.reminder_kind_code: (row.saved_by, row.bands, row.steps) for row in rows}
    standard = "60/30,15/7,7/1,0/1"
    assert found == {
        "BEFORE_JOB_STARTS": (None, standard, "ADMIN:FIRST_REMINDER::SCREEN,OPERATIONS_USER:FIRST_REMINDER::SCREEN,MANAGEMENT_READ_ONLY:DAYS_BEFORE:7:SCREEN"),
        "CERTIFICATE_RUNNING_OUT": (None, standard, "ADMIN:FIRST_REMINDER::SCREEN,OPERATIONS_USER:DAYS_BEFORE:15:SCREEN,MANAGEMENT_READ_ONLY:DAYS_BEFORE:7:SCREEN"),
        "DURING_JOB": (None, standard, "ADMIN:FIRST_REMINDER::SCREEN,OPERATIONS_USER:FIRST_REMINDER::SCREEN,MANAGEMENT_READ_ONLY:DAYS_BEFORE:7:SCREEN"),
        "NOT_YET_RECORDED": (None, "0/1", "ADMIN:FIRST_REMINDER::SCREEN,OPERATIONS_USER:DAYS_BEFORE:-7:SCREEN,MANAGEMENT_READ_ONLY:DAYS_BEFORE:-14:SCREEN"),
        # HOL-1, Q2: counted to 1 January of the year; Admin from the first reminder, Management from 1 January.
        "HOLIDAY_CALENDAR_NOT_SET_UP": (None, standard, "ADMIN:FIRST_REMINDER::SCREEN,MANAGEMENT_READ_ONLY:DAYS_BEFORE:0:SCREEN"),
    }


def test_everyone_reads_the_settings():
    for username in ("admin1", "sales1", "manager1", "finance1", "ops1", "readonly1"):
        body = _settings(username)
        assert [item["reminder_kind_code"] for item in body["settings"]] == [
            "CERTIFICATE_RUNNING_OUT", "NOT_YET_RECORDED", "BEFORE_JOB_STARTS", "DURING_JOB", "HOLIDAY_CALENDAR_NOT_SET_UP",
        ]
    assert body["channel_codes"] == ["SCREEN"]
    assert {"ADMIN", "OPERATIONS_USER", "MANAGEMENT_READ_ONLY"} <= {role["role_code"] for role in body["roles"]}
    assert body["settings"][0]["reminder_kind_label"] == "A certificate running out"


def test_a_new_version_applies_at_once_and_records_who_and_when(fleet, settings_restored):
    current = _current("CERTIFICATE_RUNNING_OUT")
    search = fleet.number("SMALL")
    assert "INSURANCE" not in _by_kind(_items("ops1", search))
    steps = [("ADMIN", "FIRST_REMINDER", None), ("OPERATIONS_USER", "DAYS_BEFORE", 25), ("MANAGEMENT_READ_ONLY", "DAYS_BEFORE", 7)]
    saved = _ok(_save("CERTIFICATE_RUNNING_OUT", version=current["version_number"], bands=STANDARD_BANDS, steps=steps), 201)
    assert saved["unchanged"] is False
    new = saved["setting"]["current"]
    assert new["version_number"] == current["version_number"] + 1
    assert new["saved_by_display_name"] and new["steps"][1]["from_days_before"] == 25
    assert saved["setting"]["earlier"][0]["version_number"] == current["version_number"]
    event = saved["event"]
    assert event["event_name"] == "ELIGIBILITY_ALERT_SETTING_CHANGED"
    payload = event["event_payload"]
    assert (payload["reminder_kind_code"], payload["version_before"], payload["version_after"]) == (
        "CERTIFICATE_RUNNING_OUT", current["version_number"], current["version_number"] + 1,
    )
    assert payload["steps"][1] == {"role_code": "OPERATIONS_USER", "starts_code": "DAYS_BEFORE", "from_days_before": 25, "channel_codes": ["SCREEN"]}
    # It applies at once: Operations now sees the insurance running out in 20 days.
    assert "INSURANCE" in _by_kind(_items("ops1", search))
    # The same again records nothing.
    again = _save("CERTIFICATE_RUNNING_OUT", version=new["version_number"], bands=list(reversed(STANDARD_BANDS)), steps=steps)
    assert again.status_code == 200 and again.json()["unchanged"] is True
    assert _current("CERTIFICATE_RUNNING_OUT")["version_number"] == new["version_number"]


def test_a_setting_is_refused_in_words(settings_restored):
    current = _current("CERTIFICATE_RUNNING_OUT")["version_number"]
    assert "saved this setting after you opened it" in _detail(
        _save("CERTIFICATE_RUNNING_OUT", version=current + 5, bands=STANDARD_BANDS, steps=STANDARD_STEPS), 409
    )
    assert "no such kind" in _detail(_save("NEVER", version=1, bands=STANDARD_BANDS, steps=STANDARD_STEPS), 404)
    for bands, steps, words in (
        ([(60, 30), (7, 1)], STANDARD_STEPS, "never left without reminders"),
        ([], STANDARD_STEPS, "at least one band"),
        (STANDARD_BANDS, [], "at least one step"),
        (STANDARD_BANDS, [("NOBODY", "FIRST_REMINDER", None)], "role from the list"),
        (STANDARD_BANDS, [("OPERATIONS_USER", "DAYS_BEFORE", 15)], "first step must start"),
    ):
        assert words in _detail(_save("CERTIFICATE_RUNNING_OUT", version=current, bands=bands, steps=steps))
    assert _current("CERTIFICATE_RUNNING_OUT")["version_number"] == current


def test_only_admin_saves_a_setting(settings_restored):
    current = _current("DURING_JOB")["version_number"]
    for username in ("sales1", "manager1", "finance1", "ops1", "readonly1"):
        response = _save("DURING_JOB", version=current, bands=STANDARD_BANDS, steps=STANDARD_STEPS, username=username)
        assert response.status_code == 403, (username, response.text)
    assert _current("DURING_JOB")["version_number"] == current


def test_the_database_refuses_what_the_service_refuses():
    with SessionLocal() as db:
        setting_id = db.execute(text("SELECT id FROM eligibility_alert_setting ORDER BY id LIMIT 1")).scalar_one()
        asset = db.execute(text("SELECT asset_public_id FROM equipment_asset ORDER BY id LIMIT 1")).scalar()
        user = db.execute(text("SELECT public_id FROM app_user WHERE username = 'admin1'")).scalar_one()
    statements = [
        ("INSERT INTO eligibility_alert_band (setting_id, band_number, from_days_before, every_days) VALUES (:s, 99, -400, 1)", {}),
        ("INSERT INTO eligibility_alert_band (setting_id, band_number, from_days_before, every_days) VALUES (:s, 99, -300, 0)", {}),
        ("INSERT INTO eligibility_alert_step (setting_id, step_number, role_code, starts_code, from_days_before, channel_codes) "
         "VALUES (:s, 99, 'FINANCE_USER', 'DAYS_BEFORE', 3, ARRAY['EMAIL']::varchar[])", {}),
        ("INSERT INTO eligibility_alert_step (setting_id, step_number, role_code, starts_code, from_days_before, channel_codes) "
         "VALUES (:s, 99, 'FINANCE_USER', 'FIRST_REMINDER', 3, ARRAY['SCREEN']::varchar[])", {}),
        ("INSERT INTO eligibility_alert_step (setting_id, step_number, role_code, starts_code, from_days_before, channel_codes) "
         "VALUES (:s, 99, 'NOBODY', 'FIRST_REMINDER', NULL, ARRAY['SCREEN']::varchar[])", {}),
        ("INSERT INTO eligibility_alert_setting (setting_public_id, reminder_kind_code, version_number) VALUES (:p, 'SOMETIME', 1)", {"p": str(uuid.uuid4())}),
    ]
    if asset is not None:
        statements.append(
            (
                "INSERT INTO eligibility_alert_acknowledgement (reminder_key, reminder_kind_code, equipment_asset_public_id, subject_type, "
                "subject_public_id, kind_code, reminder_on, seen_by) VALUES ('DURING_JOB|asset|x|y|INSURANCE|2026-01-01', "
                "'CERTIFICATE_RUNNING_OUT', :a, 'asset', :a, 'INSURANCE', CURRENT_DATE, :u)",
                {"a": asset, "u": user},
            )
        )
    for sql, params in statements:
        with SessionLocal() as db:
            with pytest.raises(IntegrityError):
                db.execute(text(sql), {"s": setting_id, **params})
            db.rollback()


def test_the_database_holds_every_part_of_a_seen_marks_key(fleet):
    """ELG2-R1-004: the key names exactly the reminder the mark is about - each part checked on its own."""
    with SessionLocal() as db:
        user = db.execute(text("SELECT public_id FROM app_user WHERE username = 'admin1'")).scalar_one()
    asset = fleet.small
    good = {
        "key": f"CERTIFICATE_RUNNING_OUT|asset|{asset}|{asset}|INSURANCE|2026-10-21",
        "date_on": date(2026, 10, 21),
        "kind": "CERTIFICATE_RUNNING_OUT",
        "asset": asset,
        "subject_type": "asset",
        "subject": asset,
        "certificate_kind": "INSURANCE",
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
    other = fleet.spare
    for key in (
        f"DURING_JOB|asset|{asset}|{asset}|INSURANCE|2026-10-21",
        f"CERTIFICATE_RUNNING_OUT|resource_assignment|{asset}|{asset}|INSURANCE|2026-10-21",
        f"CERTIFICATE_RUNNING_OUT|asset|{other}|{asset}|INSURANCE|2026-10-21",
        f"CERTIFICATE_RUNNING_OUT|asset|{asset}|{other}|INSURANCE|2026-10-21",
        f"CERTIFICATE_RUNNING_OUT|asset|{asset}|{asset}|LOAD_TEST|2026-10-21",
        f"CERTIFICATE_RUNNING_OUT|asset|{asset}|{asset}|INSURANCE|21 October",
        # ELG2-R2-006: an impossible date, and a real date other than the one stored.
        f"CERTIFICATE_RUNNING_OUT|asset|{asset}|{asset}|INSURANCE|2026-99-99",
        f"CERTIFICATE_RUNNING_OUT|asset|{asset}|{asset}|INSURANCE|0000-00-00",
        f"CERTIFICATE_RUNNING_OUT|asset|{asset}|{asset}|INSURANCE|2026-10-22",
        f"CERTIFICATE_RUNNING_OUT|asset|{asset}|{asset}|INSURANCE|2026-10-21|extra",
        f"CERTIFICATE_RUNNING_OUT|asset|{asset}|{asset}|INSURANCE",
        # HOL1-R2-002: an empty seventh part read as none, so these passed ELG-2's check; HOL-1's compares the whole key.
        f"CERTIFICATE_RUNNING_OUT|asset|{asset}|{asset}|INSURANCE|2026-10-21|",
        f"CERTIFICATE_RUNNING_OUT|asset|{asset}|{asset}|INSURANCE|2026-10-21||extra",
    ):
        with SessionLocal() as db:
            with pytest.raises(IntegrityError):
                db.execute(text(insert), {**good, "key": key})
            db.rollback()
    # An underscore in a code is not a wildcard: a kind differing only there is refused.
    with SessionLocal() as db:
        with pytest.raises(IntegrityError):
            db.execute(text(insert), {**good, "key": good["key"].replace("CERTIFICATE_RUNNING_OUT", "CERTIFICATEXRUNNING_OUT", 1)})
        db.rollback()


def _seen_rows(key: str) -> int:
    with SessionLocal() as db:
        return int(db.execute(text("SELECT COUNT(*) FROM eligibility_alert_acknowledgement WHERE reminder_key = :key"), {"key": key}).scalar_one())


def _while_locked(lock_sql: str, statements: list[tuple[str, dict]], call) -> object:
    """Run `call` while another transaction holds a lock - and makes its changes - then commits: the call must wait for
    it, then see what it committed."""
    result: dict = {}
    with SessionLocal() as other:
        other.execute(text(lock_sql))
        for sql, params in statements:
            other.execute(text(sql), params)
        worker = threading.Thread(target=lambda: result.setdefault("response", call()))
        worker.start()
        worker.join(timeout=3)
        assert worker.is_alive(), "marking seen did not wait for the lock"
        other.commit()
    worker.join(timeout=60)
    return result["response"]


def test_marking_seen_waits_for_a_setting_saved_meanwhile_and_marks_nothing_no_longer_reaching_the_person(fleet, settings_restored):
    """ELG2-R1-002: a version saved while the marks are being made - here one that no longer reaches Operations - is
    seen, and nothing is marked."""
    with crane_work_order() as wo:
        held = _allocated(wo, fleet.warns, accept_warnings=True)
        (item,) = _assignment_reminders("ops1", held)
        headers = auth_headers("ops1")
        with SessionLocal() as db:
            current = db.execute(
                text("SELECT id, version_number FROM eligibility_alert_setting WHERE reminder_kind_code = 'DURING_JOB' ORDER BY version_number DESC LIMIT 1")
            ).first()
        new_version = (
            "INSERT INTO eligibility_alert_setting (setting_public_id, reminder_kind_code, version_number, saved_by) "
            "VALUES (:public_id, 'DURING_JOB', :version, NULL)"
        )
        statements = [
            (new_version, {"public_id": str(uuid.uuid4()), "version": current.version_number + 1}),
            (
                "INSERT INTO eligibility_alert_band (setting_id, band_number, from_days_before, every_days) "
                "SELECT (SELECT MAX(id) FROM eligibility_alert_setting), band_number, from_days_before, every_days "
                "FROM eligibility_alert_band WHERE setting_id = :old",
                {"old": current.id},
            ),
            (
                "INSERT INTO eligibility_alert_step (setting_id, step_number, role_code, starts_code, from_days_before, channel_codes) "
                "VALUES ((SELECT MAX(id) FROM eligibility_alert_setting), 1, 'ADMIN', 'FIRST_REMINDER', NULL, ARRAY['SCREEN']::varchar[])",
                {},
            ),
        ]
        response = _while_locked(
            "SELECT pg_advisory_xact_lock(hashtextextended('eligibility.write', 0))",
            statements,
            lambda: _seen("ops1", (item["reminder_key"], item["reminder_on"]), headers=headers),
        )
        assert response.status_code == 404, response.text
        assert _seen_rows(item["reminder_key"]) == 0


def test_marking_seen_waits_for_the_equipment_references_and_resource_assignments_locks(fleet):
    """ELG2-R1-002 and ELG2-R2-004: marking takes Resource Assignments' lock and the Equipment Reference's as their
    writes do, before this module's, so an allocation freed or moved, or an asset retired, meanwhile is seen."""
    load_test = _by_kind(_items("ops1", fleet.number("SMALL")))["LOAD_TEST"]
    headers = auth_headers("ops1")
    before = _seen_rows(load_test["reminder_key"])
    # And the Equipment Reference's: an asset retired, or a part fitted or removed, meanwhile is seen (ELG2-R2-004).
    response = _while_locked(
        "SELECT pg_advisory_xact_lock(hashtextextended('equipment_reference.write', 0))",
        [],
        lambda: _seen("ops1", (load_test["reminder_key"], load_test["reminder_on"]), headers=headers),
    )
    assert response.status_code == 200, response.text
    assert _seen_rows(load_test["reminder_key"]) == before + 1
    before += 1
    response = _while_locked(
        "SELECT pg_advisory_xact_lock(80450001)",
        [],
        lambda: _seen("ops1", (load_test["reminder_key"], load_test["reminder_on"]), headers=headers),
    )
    assert response.status_code == 200, response.text
    # Marked once already, under the Equipment Reference's lock above.
    assert response.json() == {"marked": 0, "already": 1}
    assert _seen_rows(load_test["reminder_key"]) == before
