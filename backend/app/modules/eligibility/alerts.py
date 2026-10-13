"""Certificate reminders and escalation (ELG-2): the Alerts, the "seen" marks and the settings.

Design: docs/agent/slices/elg-2-certificate-reminders.md; the API is docs/agent/contracts/eligibility-api-contract.md,
"Reminders and escalation".

- **Worked out when read.** Each read takes the current settings, reads the whole fleet's evidence once (as
  Certificates due does), reads the held allocations through the port Resource Assignments registers, judges each
  for its own site and days against that one reading, and reads the "seen" marks. Nothing is written but a "seen"
  mark or a new version of a setting, and nothing is sent: the screen is the only channel (NTF-001 not built).
- **Who sees what.** A person sees a reminder when one of their roles is on a step of its path that has reached
  them. The two allocation reminders name Work Orders and allocations, so they also need RESOURCE_ASSIGNMENT_READ.
- **"Seen"** is one person's mark on one reminder's current reminder day (Q17). It changes nothing else and records
  no business event; marking several is all or none.
- **Settings** are versioned, never edited, and changed only under ELIGIBILITY_RULE_MANAGE (Q18), with the module's
  write lock, as rules are.
- **PBL's holiday calendar** (HOL-1, Q2): a fifth reminder, for this year and next until Admin marks each complete,
  dated 1 January of the year. It is about a year, not a machine: the calendar answers which years are not complete
  through the port it registers (`ports.py`), and the reminder carries no asset or certificate.

This module uses only `service.py`'s public functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.modules.authorization.contract import RESOURCE_ASSIGNMENT_READ
from app.modules.authorization.service import has_permission
from app.modules.eligibility import evaluation, reminders, service
from app.modules.eligibility import repository as repo
from app.modules.eligibility.contract import (
    ALLOCATION_REMINDER_KIND_CODES,
    CHANNEL_CODES,
    ELIGIBILITY_MODULE_NAME,
    EVENT_ALERT_SETTING_CHANGED,
    MAX_ALERT_LIMIT,
    REASON_CALENDAR_NOT_COMPLETE,
    RECORD_TYPE_ALERT_SETTING,
    REMINDER_CALENDAR_NOT_SET_UP,
    REMINDER_KIND_CODES,
    REMINDER_KIND_LABELS,
    SUBJECT_ASSET,
    SUBJECT_CALENDAR_YEAR,
    SUBJECT_KIT_LINE,
)
from app.modules.eligibility.ports import AllocatedAsset, allocation_source, calendar_source
from app.modules.eligibility.schemas import (
    AlertAllocation,
    AlertBand,
    AlertCountResponse,
    AlertCounts,
    AlertItem,
    AlertReached,
    AlertRole,
    AlertSeenBy,
    AlertSettingActionResponse,
    AlertSettingInput,
    AlertSettingResponse,
    AlertSettingsResponse,
    AlertSettingVersion,
    AlertsResponse,
    AlertStepResponse,
    SeenInput,
    SeenResponse,
)
from app.modules.equipment_reference.service import AssetWithFittedParts, hold_equipment_writes
from app.modules.events.service import record_business_event
from app.modules.identity.repository import list_active_roles
from app.modules.identity.schemas import AuthUser
from app.shared import business_time

_KIND_ORDER = {code: index for index, code in enumerate(REMINDER_KIND_CODES)}


# --- Settings ----------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Version:
    row: dict[str, Any]
    setting: reminders.Setting


def _versions(db: Session) -> dict[str, list[_Version]]:
    """Every version of every kind's setting, newest first within a kind."""
    rows = repo.list_setting_rows(db)
    ids = [int(row["id"]) for row in rows]
    bands: dict[int, list[reminders.Band]] = {}
    for item in repo.list_band_rows(db, setting_ids=ids):
        bands.setdefault(int(item["setting_id"]), []).append(reminders.Band(int(item["from_days_before"]), int(item["every_days"])))
    steps: dict[int, list[reminders.Step]] = {}
    for item in repo.list_step_rows(db, setting_ids=ids):
        steps.setdefault(int(item["setting_id"]), []).append(
            reminders.Step(
                role_code=item["role_code"],
                starts_code=item["starts_code"],
                from_days_before=item["from_days_before"],
                channel_codes=tuple(item["channel_codes"]),
            )
        )
    versions: dict[str, list[_Version]] = {}
    for row in rows:
        versions.setdefault(row["reminder_kind_code"], []).append(
            _Version(
                row,
                reminders.Setting(
                    reminder_kind_code=row["reminder_kind_code"],
                    version_number=int(row["version_number"]),
                    bands=reminders.ordered_bands(bands.get(int(row["id"]), [])),
                    steps=tuple(steps.get(int(row["id"]), [])),
                ),
            )
        )
    return versions


def _current(db: Session) -> dict[str, reminders.Setting]:
    versions = _versions(db)
    missing = [code for code in REMINDER_KIND_CODES if code not in versions]
    if missing:
        # Migration 20260908_0046 loads a version of each; without one, no reminder of that kind could be judged.
        raise RuntimeError(f"No reminder setting is recorded for {', '.join(missing)}.")
    return {code: versions[code][0].setting for code in REMINDER_KIND_CODES}


def _role_labels(db: Session) -> dict[str, str]:
    return {row["role_code"]: row["role_name"] for row in list_active_roles(db)}


def _version_response(version: _Version, labels: dict[str, str]) -> AlertSettingVersion:
    row = version.row
    return AlertSettingVersion(
        setting_public_id=row["setting_public_id"],
        reminder_kind_code=row["reminder_kind_code"],
        version_number=int(row["version_number"]),
        saved_by=row["saved_by"],
        saved_by_display_name=row["saved_by_display_name"],
        saved_at=row["saved_at"],
        bands=[AlertBand(from_days_before=band.from_days_before, every_days=band.every_days) for band in version.setting.bands],
        steps=[
            AlertStepResponse(
                step_number=number,
                role_code=step.role_code,
                role_label=labels.get(step.role_code, step.role_code),
                starts_code=step.starts_code,
                from_days_before=step.from_days_before,
                channel_codes=list(step.channel_codes),
            )
            for number, step in enumerate(version.setting.steps, 1)
        ],
    )


def _setting_response(kind: str, versions: list[_Version], labels: dict[str, str]) -> AlertSettingResponse:
    return AlertSettingResponse(
        reminder_kind_code=kind,
        reminder_kind_label=REMINDER_KIND_LABELS[kind],
        current=_version_response(versions[0], labels),
        earlier=[_version_response(version, labels) for version in versions[1:]],
    )


def get_settings(db: Session) -> AlertSettingsResponse:
    versions = _versions(db)
    labels = _role_labels(db)
    return AlertSettingsResponse(
        settings=[_setting_response(kind, versions[kind], labels) for kind in REMINDER_KIND_CODES if kind in versions],
        roles=[AlertRole(role_code=code, role_label=label) for code, label in labels.items()],
        channel_codes=list(CHANNEL_CODES),
    )


def save_setting(
    db: Session, *, reminder_kind_code: str, payload: AlertSettingInput, user_public_id: str | None
) -> AlertSettingActionResponse:
    """A new version of one kind of reminder's setting (Q18). It applies at once: reminders are worked out when read."""
    if reminder_kind_code not in REMINDER_KIND_CODES:
        raise service.EligibilityNotFoundError("There is no such kind of reminder.")
    if not user_public_id:
        raise service.EligibilityValidationError("The signed-in user could not be identified, so nothing was saved.")
    bands = reminders.ordered_bands(reminders.Band(item.from_days_before, item.every_days) for item in payload.bands)
    steps = tuple(
        reminders.Step(
            role_code=item.role_code.strip().upper(),
            starts_code=item.starts_code.strip().upper(),
            from_days_before=item.from_days_before,
            channel_codes=tuple(code.strip().upper() for code in item.channel_codes),
        )
        for item in payload.steps
    )
    try:
        repo.take_write_lock(db)
        versions = _versions(db)[reminder_kind_code]
        current = versions[0]
        if payload.expected_version != current.setting.version_number:
            raise service.EligibilityConflictError(
                "Someone saved this setting after you opened it, so your change was not saved. Read it again."
            )
        labels = _role_labels(db)
        problem = reminders.setting_problem(bands, steps, active_roles=set(labels))
        if problem is not None:
            raise service.EligibilityValidationError(problem)
        if bands == current.setting.bands and steps == current.setting.steps:
            db.commit()
            return AlertSettingActionResponse(setting=_setting_response(reminder_kind_code, versions, labels), unchanged=True)
        public_id = str(uuid4())
        setting_id = repo.insert_setting(
            db,
            setting_public_id=public_id,
            reminder_kind_code=reminder_kind_code,
            version_number=current.setting.version_number + 1,
            saved_by=user_public_id,
            saved_at=datetime.now(timezone.utc),
        )
        repo.insert_bands(db, setting_id=setting_id, bands=[(band.from_days_before, band.every_days) for band in bands])
        repo.insert_steps(
            db,
            setting_id=setting_id,
            steps=[(step.role_code, step.starts_code, step.from_days_before, list(step.channel_codes)) for step in steps],
        )
        event = record_business_event(
            db,
            event_name=EVENT_ALERT_SETTING_CHANGED,
            source_module=ELIGIBILITY_MODULE_NAME,
            record_type=RECORD_TYPE_ALERT_SETTING,
            record_public_id=public_id,
            user_public_id=user_public_id,
            status_before=None,
            status_after=None,
            reason="Reminder setting changed.",
            event_payload={
                "reminder_kind_code": reminder_kind_code,
                "version_before": current.setting.version_number,
                "version_after": current.setting.version_number + 1,
                "bands": [{"from_days_before": band.from_days_before, "every_days": band.every_days} for band in bands],
                "steps": [
                    {
                        "role_code": step.role_code,
                        "starts_code": step.starts_code,
                        "from_days_before": step.from_days_before,
                        "channel_codes": list(step.channel_codes),
                    }
                    for step in steps
                ],
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return AlertSettingActionResponse(
        setting=_setting_response(reminder_kind_code, _versions(db)[reminder_kind_code], labels),
        unchanged=False,
        event=event.model_dump(mode="json"),
    )


# --- The reminders (section 5) -------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Reminder:
    key: str
    kind: str
    subject_type: str
    subject_public_id: str
    # The machine and its certificate's result; both None for a calendar reminder, which is about a year (HOL-1).
    unit: AssetWithFittedParts | None
    result: evaluation.Result | None
    dated: reminders.Dated
    days: reminders.Days
    reached: tuple[reminders.Reached, ...]
    began_on: date
    held: AllocatedAsset | None
    calendar_year: int | None = None


def _reminder(
    reading: service.FleetReading,
    settings: dict[str, reminders.Setting],
    *,
    kind: str,
    subject_type: str,
    subject_public_id: str,
    unit: AssetWithFittedParts,
    result: evaluation.Result,
    began_on: date,
    held: AllocatedAsset | None,
) -> _Reminder | None:
    assets = service.member_assets(unit)
    added = service.added_on(unit)
    dated = reminders.reminder_date(
        result,
        reading.evidence,
        assets=assets.get(result.asset_public_id, (result.asset_public_id,)),
        added_on=added.get(result.asset_public_id, unit.asset.added_on),
        today=reading.today,
        # A job's rules are chosen for its first day, or today once it has started - as the check chooses them.
        rule_day=max(reading.today, held.period_from) if held is not None else None,
    )
    if dated is None:
        return None
    if held is None:
        kind = reminders.asset_reminder_kind(dated)
    setting = settings[kind]
    days = reminders.reminder_days(setting.bands, date_on=dated.on, began_on=began_on, today=reading.today)
    if days is None:
        return None
    reached = reminders.reached_steps(setting.steps, first_on=days.first_on, date_on=dated.on, today=reading.today)
    key = reminders.reminder_key(kind, subject_type, subject_public_id, result.asset_public_id, result.kind_code or "", dated.on)
    return _Reminder(key, kind, subject_type, subject_public_id, unit, result, dated, days, tuple(reached), began_on, held)


def calendar_reminders_began(db: Session) -> date:
    """The day the calendar reminder came with the package: its setting's first version, loaded by migration
    20260908_0047, in Asia/Kolkata. A year not complete on that day - the year then running - is reminded from it,
    not from before the calendar existed (design section 5.4)."""
    saved_at = repo.first_setting_saved_at(db, reminder_kind_code=REMINDER_CALENDAR_NOT_SET_UP)
    if saved_at is None:
        raise RuntimeError(f"No reminder setting is recorded for {REMINDER_CALENDAR_NOT_SET_UP}.")
    return business_time.india_date(saved_at)


def _calendar_reminder(setting: reminders.Setting, *, calendar_year: int, today: date, began_on: date) -> _Reminder | None:
    """"PBL's holiday calendar for <year> is not set up" (HOL-1, Q2), dated 1 January of the year, on the schedule and
    path of its setting. It began when the reminder came with the package (`calendar_reminders_began`): a year that
    began before then is reminded from that day, as a machine is from the day it was added; a later year from the
    schedule's own first reminder."""
    on = date(calendar_year, 1, 1)
    days = reminders.reminder_days(setting.bands, date_on=on, began_on=began_on, today=today)
    if days is None:
        return None
    reached = reminders.reached_steps(setting.steps, first_on=days.first_on, date_on=on, today=today)
    return _Reminder(
        key=reminders.reminder_key(REMINDER_CALENDAR_NOT_SET_UP, SUBJECT_CALENDAR_YEAR, str(calendar_year), "", "", on),
        kind=REMINDER_CALENDAR_NOT_SET_UP,
        subject_type=SUBJECT_CALENDAR_YEAR,
        subject_public_id=str(calendar_year),
        unit=None,
        result=None,
        dated=reminders.Dated(on, REASON_CALENDAR_NOT_COMPLETE),
        days=days,
        reached=tuple(reached),
        began_on=days.first_on,
        held=None,
        calendar_year=calendar_year,
    )


def _all_reminders(db: Session, *, today: date | None = None) -> tuple[service.FleetReading, list[_Reminder]]:
    settings = _current(db)
    reading = service.read_fleet(db, today=today)
    found: list[_Reminder] = []
    # The renewal list: every active asset by the baseline rules - "running out", or "not yet recorded" (Q19a).
    for unit in reading.units:
        for result in service.baseline_of(reading, unit):
            item = _reminder(
                reading,
                settings,
                kind="",
                subject_type=SUBJECT_ASSET,
                subject_public_id=unit.asset.asset_public_id,
                unit=unit,
                result=result,
                began_on=unit.asset.added_on,
                held=None,
            )
            if item is not None:
                found.append(item)
    # The allocations: each held machine and listed piece, judged for its own site and days (8A, section 6.4).
    for held in allocation_source().held_for_reminders(db, today=reading.today):
        if held.site_problem_code is not None or held.site_state_code is None or held.central_government_site is None:
            continue
        unit = reading.by_asset.get(held.asset_public_id)
        if unit is None:
            continue
        decision = service.judge_in_fleet(
            reading,
            unit,
            state_code=held.site_state_code,
            central_government_site=held.central_government_site,
            period_from=held.period_from,
            period_to=held.period_to,
        )
        if decision is None:
            continue
        for result in decision.results:
            if result.kind_code is None:
                continue
            kind = reminders.allocation_reminder_kind(result.outcome_code, first_day=held.period_from, today=reading.today)
            if kind is None:
                continue
            item = _reminder(
                reading,
                settings,
                kind=kind,
                subject_type=held.subject_type,
                subject_public_id=held.subject_public_id,
                unit=unit,
                result=result,
                began_on=held.began_on,
                held=held,
            )
            if item is not None:
                found.append(item)
    # PBL's holiday calendar (HOL-1, Q2): this year and next, each until Admin marks it complete.
    years = [reading.today.year, reading.today.year + 1]
    began_on = calendar_reminders_began(db)
    for calendar_year in calendar_source().years_not_complete(db, years=years):
        item = _calendar_reminder(
            settings[REMINDER_CALENDAR_NOT_SET_UP], calendar_year=calendar_year, today=reading.today, began_on=began_on
        )
        if item is not None:
            found.append(item)
    return reading, found


def _reaching(db: Session, user: AuthUser, *, today: date | None = None) -> tuple[service.FleetReading, list[_Reminder]]:
    """The reminders that have reached this person: one of their roles is on a step reached by today."""
    roles = set(user.role_codes)
    sees_allocations = has_permission(db, user.role_codes, RESOURCE_ASSIGNMENT_READ)
    reading, found = _all_reminders(db, today=today)
    return reading, [
        item
        for item in found
        if (sees_allocations or item.kind not in ALLOCATION_REMINDER_KIND_CODES)
        and any(reached.step.role_code in roles for reached in item.reached)
    ]


def _seen_marks(db: Session, items: list[_Reminder]) -> dict[str, list[dict[str, Any]]]:
    """The "seen" marks on each reminder's current reminder day."""
    current = {item.key: item.days.current_on for item in items}
    marks: dict[str, list[dict[str, Any]]] = {}
    for row in repo.list_acknowledgement_rows(db, reminder_keys=sorted(current)):
        if row["reminder_on"] == current.get(row["reminder_key"]):
            marks.setdefault(row["reminder_key"], []).append(row)
    return marks


def _order(item: _Reminder, reading: service.FleetReading) -> tuple:
    result = item.result
    return (
        item.dated.on,
        _KIND_ORDER[item.kind],
        item.unit.asset.asset_reference if item.unit else "",
        reading.evidence.kinds[result.kind_code].display_order if result and result.kind_code else 0,
        item.held.assignment_reference if item.held else "",
        item.key,
    )


def _matches(item: _Reminder, needle: str) -> bool:
    if item.unit is None:
        # A calendar reminder: found by its year, or by what it is.
        return any(needle in value.lower() for value in (str(item.calendar_year), REMINDER_KIND_LABELS[item.kind]))
    asset = item.unit.asset
    values = [asset.machine_number, asset.asset_reference, asset.serial_number]
    if item.held is not None:
        values += [item.held.work_order_code, item.held.assignment_reference]
    return any(needle in (value or "").lower() for value in values)


def _reached(item: _Reminder, labels: dict[str, str]) -> list[AlertReached]:
    return [
        AlertReached(
            step_number=reached.step_number,
            role_code=reached.step.role_code,
            role_label=labels.get(reached.step.role_code, reached.step.role_code),
            reached_on=reached.reached_on,
        )
        for reached in item.reached
    ]


def _seen_by(marks: list[dict[str, Any]]) -> list[AlertSeenBy]:
    return [AlertSeenBy(display_name=mark["seen_by_display_name"] or "", seen_at=mark["seen_at"]) for mark in marks]


def _calendar_item(item: _Reminder, marks: list[dict[str, Any]], *, user_public_id: str, labels: dict[str, str]) -> AlertItem:
    """A calendar reminder as the Alerts list shows it: the year, and no machine, certificate or allocation."""
    return AlertItem(
        reminder_key=item.key,
        reminder_kind_code=item.kind,
        reminder_kind_label=REMINDER_KIND_LABELS[item.kind],
        asset=None,
        certificate_asset_reference=None,
        kind_code="",
        kind_label="",
        outcome_code="",
        date_on=item.dated.on,
        reason_code=item.dated.reason_code,
        mark_public_id=None,
        allocation=None,
        calendar_year=item.calendar_year,
        began_on=item.began_on,
        first_reminder_on=item.days.first_on,
        reminder_on=item.days.current_on,
        reminders_so_far=item.days.so_far,
        reached=_reached(item, labels),
        seen_by_me=any(mark["seen_by"] == user_public_id for mark in marks),
        seen_by=_seen_by(marks),
    )


def _item(
    item: _Reminder, reading: service.FleetReading, marks: list[dict[str, Any]], *, user_public_id: str, labels: dict[str, str]
) -> AlertItem:
    if item.unit is None or item.result is None:
        return _calendar_item(item, marks, user_public_id=user_public_id, labels=labels)
    result = item.result
    certificate_asset = result.certificate.asset_public_id if result.certificate else None
    held = item.held
    allocation = None
    if held is not None:
        allocation = AlertAllocation(
            assignment_public_id=held.assignment_public_id,
            assignment_reference=held.assignment_reference,
            work_order_public_id=held.work_order_public_id,
            work_order_code=held.work_order_code,
            work_order_line_number=held.work_order_line_number,
            unit_number=held.unit_number,
            trip_number=held.trip_number,
            kit_line_public_id=held.subject_public_id if held.subject_type == SUBJECT_KIT_LINE else None,
            site_label=held.site_label,
            site_state_code=held.site_state_code or "",
            site_state_label=reading.jurisdictions.get(held.site_state_code or "", {}).get("jurisdiction_label", held.site_state_code or ""),
            central_government_site=bool(held.central_government_site),
            period_from=held.period_from,
            period_to=held.period_to,
        )
    return AlertItem(
        reminder_key=item.key,
        reminder_kind_code=item.kind,
        reminder_kind_label=REMINDER_KIND_LABELS[item.kind],
        asset=service.asset_summary(reading, item.unit.asset),
        certificate_asset_reference=(
            reading.references.get(certificate_asset) if certificate_asset and certificate_asset != item.unit.asset.asset_public_id else None
        ),
        kind_code=result.kind_code or "",
        kind_label=service.kind_label(reading, result.kind_code) if result.kind_code else "",
        outcome_code=result.outcome_code,
        date_on=item.dated.on,
        reason_code=item.dated.reason_code,
        mark_public_id=result.mark.mark_public_id if result.mark else None,
        allocation=allocation,
        calendar_year=None,
        began_on=item.began_on,
        first_reminder_on=item.days.first_on,
        reminder_on=item.days.current_on,
        reminders_so_far=item.days.so_far,
        reached=_reached(item, labels),
        seen_by_me=any(mark["seen_by"] == user_public_id for mark in marks),
        seen_by=_seen_by(marks),
    )


def list_alerts(
    db: Session,
    user: AuthUser,
    *,
    reminder_kind_code: str | None,
    unseen_only: bool,
    search: str | None,
    limit: int,
    offset: int,
) -> AlertsResponse:
    kind = (reminder_kind_code or "").strip().upper() or None
    if kind is not None and kind not in REMINDER_KIND_CODES:
        raise service.EligibilityValidationError("Choose a kind of reminder from the list.")
    reading, items = _reaching(db, user)
    marks = _seen_marks(db, items)
    seen_by_me = {item.key for item in items if any(mark["seen_by"] == user.public_id for mark in marks.get(item.key, []))}
    by_kind = {code: 0 for code in REMINDER_KIND_CODES}
    for item in items:
        by_kind[item.kind] += 1
    counts = AlertCounts(total=len(items), unseen=sum(1 for item in items if item.key not in seen_by_me), by_kind=by_kind)
    needle = (search or "").strip().lower()
    shown = [
        item
        for item in items
        if (kind is None or item.kind == kind)
        and (not unseen_only or item.key not in seen_by_me)
        and (not needle or _matches(item, needle))
    ]
    shown.sort(key=lambda item: _order(item, reading))
    limit = max(1, min(limit, MAX_ALERT_LIMIT))
    labels = _role_labels(db)
    return AlertsResponse(
        today=reading.today,
        counts=counts,
        total=len(shown),
        limit=limit,
        offset=offset,
        items=[
            _item(item, reading, marks.get(item.key, []), user_public_id=user.public_id, labels=labels)
            for item in shown[offset : offset + limit]
        ],
    )


def count_alerts(db: Session, user: AuthUser) -> AlertCountResponse:
    _reading, items = _reaching(db, user)
    marks = _seen_marks(db, items)
    unseen = sum(1 for item in items if not any(mark["seen_by"] == user.public_id for mark in marks.get(item.key, [])))
    return AlertCountResponse(unseen=unseen, total=len(items))


def mark_seen(db: Session, user: AuthUser, *, payload: SeenInput) -> SeenResponse:
    """Mark reminders seen on their current reminder day: all, or none when any has not reached the person or has
    moved on since the list was read (design section 5.5)."""
    if not payload.items:
        raise service.EligibilityValidationError("Choose at least one reminder to mark as seen.")
    wanted = {(item.reminder_key, item.reminder_on) for item in payload.items}
    try:
        # The writes that change a reminder take one of these locks: Resource Assignments' (allocations, their dates
        # and kit, a requirement's change or cancellation), the Equipment Reference's (an asset retired, a part fitted
        # or removed, a model mapped), the holiday calendar's (a year saved or marked complete - HOL-1; that save takes
        # no other of these locks) and this module's (certificates and their copies, marks, rules, settings, and every
        # decision 8A stores). Taken in that order - no write takes two of them the other way round - the reminders are
        # worked out after any such write has committed, and none can commit until the marks are written (independent
        # review, ELG2-R1-002 and ELG2-R2-004).
        allocation_source().hold(db)
        hold_equipment_writes(db)
        calendar_source().hold(db)
        repo.take_write_lock(db)
        _reading, items = _reaching(db, user)
        by_key = {item.key: item for item in items}
        rows: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        for key, reminder_on in sorted(wanted):
            item = by_key.get(key)
            if item is None:
                raise service.EligibilityNotFoundError(
                    "A reminder is no longer due for you, so nothing was marked. Read the list again."
                )
            if item.days.current_on != reminder_on:
                raise service.EligibilityConflictError(
                    "A reminder has moved on since the list was read, so nothing was marked. Read the list again."
                )
            rows.append(
                {
                    "reminder_key": key,
                    "reminder_kind_code": item.kind,
                    # A calendar reminder is about a year: no asset and no certificate kind (HOL-1).
                    "equipment_asset_public_id": item.result.asset_public_id if item.result else None,
                    "subject_type": item.subject_type,
                    "subject_public_id": item.subject_public_id,
                    "kind_code": item.result.kind_code if item.result else None,
                    "reminder_on": reminder_on,
                    "reminder_date_on": item.dated.on,
                    "seen_by": user.public_id,
                    "seen_at": now,
                }
            )
        marked = repo.insert_acknowledgements(db, rows=rows)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return SeenResponse(marked=marked, already=len(rows) - marked)
