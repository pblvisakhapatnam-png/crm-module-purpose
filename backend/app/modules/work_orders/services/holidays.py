"""Slice 7D Part 4: the holidays a Work Order names - since HOL-1, its changes to PBL's holiday calendar.

Every Work Order inherits PBL's holiday calendar for each line's site state, and its own terms change it (owner,
2 October 2026; docs/agent/slices/hol-1-holiday-calendar.md, section 5.2). One list on the Work Order, for every line
(decision 27); each change is one of:

- **a holiday added**: a date, its kind - national or festival - and an optional description, as Part 4 recorded;
- **a working day**: a calendar holiday the Work Order works, charged at the normal rate or, every hour of it, at the
  line's own overtime rate, with an optional note (Q4).

Weekly off days are recorded with each line's billing terms (Part 1) and are not repeated here. A holiday is charged as
each line's off-day choice says (answer 24).

The answer beside the list - "the Work Order follows PBL's calendar unchanged" or "changes PBL's calendar as listed" -
is what tells a recorded "no change" from a list not entered yet (decision 29). No answer recorded, or "changes ... as
listed" with no change yet, is reported missing.

Every date is checked against the contract with contract_period_rules.py, as Part 3 checks a billing period's start
and a line's own dates: outside the contract, or in a gap before an extension, is refused naming both dates.
contract_period.py refuses the reverse - a contract change that would exclude a listed date - reading the dates
straight from the repository, so neither concern imports the other.

Nothing here writes to crm_work_order or crm_work_order_line, so the frozen handoff is untouched, and nothing is
calculated: log sheets and billing will read the holidays that apply (services/resulting_holidays.py) later.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.work_orders.contract_period_rules import (
    ContractGap,
    date_outside_contract_message,
    format_contract_date,
)
from app.modules.work_orders.contract import (
    WORK_ORDER_HOLIDAY_CHANGE_ADDED,
    WORK_ORDER_HOLIDAY_CHANGE_CODES,
    WORK_ORDER_HOLIDAY_CHANGE_WORKING_DAY,
    WORK_ORDER_HOLIDAY_DESCRIPTION_MAX_LENGTH,
    WORK_ORDER_HOLIDAY_KIND_CODES,
    WORK_ORDER_HOLIDAYS_ANSWER_CODES,
    WORK_ORDER_HOLIDAYS_CALENDAR_CHANGED,
    WORK_ORDER_HOLIDAYS_CALENDAR_UNCHANGED,
    WORK_ORDER_HOLIDAYS_EVENT_RECORDED,
    WORK_ORDER_HOLIDAYS_EVENT_UPDATED,
    WORK_ORDER_HOLIDAYS_MISSING,
    WORK_ORDER_WORKING_DAY_RATE_CODES,
)
from app.modules.work_orders.repository import (
    delete_work_order_holidays,
    get_work_order_holiday_list_row,
    get_work_order_holiday_list_snapshot,
    insert_work_order_holiday,
    insert_work_order_holiday_list,
    list_work_order_holiday_rows,
    update_work_order_holiday_list,
)
from app.modules.work_orders.schemas import (
    WorkOrderHolidayChangeResponse,
    WorkOrderHolidayListActionResponse,
    WorkOrderHolidayListResponse,
    WorkOrderHolidayListUpdate,
)
from app.modules.work_orders.services.common import (
    WorkOrderHolidayListConflictError,
    WorkOrderValidationError,
    _clean_optional,
    _get_work_order_and_id,
    _lock_work_order_for_contract_period,
    _record_billing_terms_event,
    _term_code,
    contract_bounds_for_work_order,
    contract_gaps_for_work_order,
)
from app.shared.transactions import rollback_on_error


_HOLIDAYS_CONFLICT_MESSAGE = "Someone else changed the holidays after you opened them. Reload to see their version."
_CHOOSE_ANSWER = "Choose whether the Work Order follows PBL's holiday calendar unchanged, or changes it as listed."

# What a change is compared on, to tell a changed date from one left alone.
_CHANGE_FIELDS = ("change_code", "holiday_kind_code", "working_day_rate_code", "description")


def _holiday_list_missing_items(row: dict[str, Any] | None, changes: list[dict[str, Any]]) -> list[str]:
    """Not answered yet, or answered "changes PBL's calendar as listed" with none entered, is missing. "Follows PBL's
    calendar unchanged" is an answer, so it is not (decision 29)."""
    if row is None:
        return [WORK_ORDER_HOLIDAYS_MISSING]
    if row["holidays_answer_code"] == WORK_ORDER_HOLIDAYS_CALENDAR_CHANGED and not changes:
        return [WORK_ORDER_HOLIDAYS_MISSING]
    return []


def _build_holiday_list_response(
    *, work_order_public_id: UUID, row: dict[str, Any] | None, changes: list[dict[str, Any]]
) -> WorkOrderHolidayListResponse:
    missing = _holiday_list_missing_items(row, changes)
    return WorkOrderHolidayListResponse(
        work_order_public_id=work_order_public_id,
        holiday_list_public_id=row.get("holiday_list_public_id") if row else None,
        list_version=int(row["list_version"]) if row else None,
        holidays_answer_code=row.get("holidays_answer_code") if row else None,
        changes=[
            WorkOrderHolidayChangeResponse(**{key: item.get(key) for key in WorkOrderHolidayChangeResponse.model_fields})
            for item in changes
        ],
        is_complete=not missing,
        missing_items=missing,
        updated_by=row.get("updated_by") if row else None,
        updated_by_display_name=row.get("updated_by_display_name") if row else None,
        updated_at=row.get("updated_at") if row else None,
    )


def _holiday_list_from_db(db: Session, *, work_order_public_id: UUID, work_order_id: int) -> WorkOrderHolidayListResponse:
    # One statement, so the answer and its changes always come from the same version (Part 4 review round 2, F-05). A
    # read takes no lock; a save holds the Work Order lock and reads its own writes.
    row, changes = get_work_order_holiday_list_snapshot(db, work_order_id=work_order_id)
    return _build_holiday_list_response(work_order_public_id=work_order_public_id, row=row, changes=changes)


def get_work_order_holidays(db: Session, work_order_public_id: UUID) -> WorkOrderHolidayListResponse:
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    return _holiday_list_from_db(db, work_order_public_id=work_order.public_id, work_order_id=work_order_id)


def _normalize_change(item: Any) -> dict[str, Any]:
    """One change, its codes checked and in capitals. A kind belongs to a holiday added and a rate to a working day,
    each only there (Q4). Every refusal names the date."""
    day = format_contract_date(item.holiday_date)
    change_code = _term_code(
        item.change_code, WORK_ORDER_HOLIDAY_CHANGE_CODES, f"The change on {day} must be a holiday added or a working day."
    )
    if change_code is None:
        raise WorkOrderValidationError(f"Choose whether {day} is a holiday added or a working day.")
    kind = _term_code(
        item.holiday_kind_code, WORK_ORDER_HOLIDAY_KIND_CODES, f"The holiday on {day} must be a national or a festival holiday."
    )
    rate = _term_code(
        item.working_day_rate_code,
        WORK_ORDER_WORKING_DAY_RATE_CODES,
        f"The working day on {day} must be charged at the normal rate or at the overtime rate.",
    )
    if change_code == WORK_ORDER_HOLIDAY_CHANGE_ADDED:
        if kind is None:
            raise WorkOrderValidationError(f"Choose whether the holiday on {day} is a national or a festival holiday.")
        if rate is not None:
            raise WorkOrderValidationError(
                f"The holiday added on {day} takes no rate of its own: it is charged as each line's off-day term says."
            )
    else:
        if rate is None:
            raise WorkOrderValidationError(
                f"Choose whether the working day on {day} is charged at the normal rate or at the overtime rate."
            )
        if kind is not None:
            raise WorkOrderValidationError(
                f"The working day on {day} takes no kind of its own: it is PBL's calendar holiday on that date."
            )
    description = _clean_optional(item.description)
    if description is not None and len(description) > WORK_ORDER_HOLIDAY_DESCRIPTION_MAX_LENGTH:
        what = "description of the holiday added" if change_code == WORK_ORDER_HOLIDAY_CHANGE_ADDED else "note on the working day"
        raise WorkOrderValidationError(
            f"The {what} on {day} is longer than {WORK_ORDER_HOLIDAY_DESCRIPTION_MAX_LENGTH} characters."
        )
    return {
        "change_code": change_code,
        "holiday_date": item.holiday_date,
        "holiday_kind_code": kind,
        "working_day_rate_code": rate,
        "description": description,
    }


def _normalize_holidays(
    payload: WorkOrderHolidayListUpdate,
    *,
    contract_start: date | None,
    contract_end: date | None,
    contract_gaps: tuple[ContractGap, ...],
) -> tuple[str, list[dict[str, Any]]]:
    """The answer and the changes, validated, in date order. Every refusal names the date it is about."""
    answer = _term_code(payload.holidays_answer_code, WORK_ORDER_HOLIDAYS_ANSWER_CODES, _CHOOSE_ANSWER)
    if answer is None:
        raise WorkOrderValidationError(_CHOOSE_ANSWER)
    if answer == WORK_ORDER_HOLIDAYS_CALENDAR_UNCHANGED and payload.changes:
        raise WorkOrderValidationError(
            "The Work Order is recorded as following PBL's holiday calendar unchanged, so it cannot list any changes. "
            "Remove them, or record that it changes the calendar as listed."
        )

    changes: list[dict[str, Any]] = []
    seen: set[date] = set()
    for item in payload.changes:
        if item.holiday_date in seen:
            raise WorkOrderValidationError(
                f"{format_contract_date(item.holiday_date)} is listed more than once. A date is either a holiday added "
                "or a working day: list it once."
            )
        seen.add(item.holiday_date)
        change = _normalize_change(item)
        # Outside the contract, or in a gap before an extension, is refused naming both dates - the rule Part 3 applies
        # to a billing period's start and a line's own dates. An unrecorded bound is never treated as broken.
        added = change["change_code"] == WORK_ORDER_HOLIDAY_CHANGE_ADDED
        outside = date_outside_contract_message(
            item.holiday_date,
            contract_start=contract_start,
            contract_end=contract_end,
            subject="A holiday is listed on" if added else "A working day is listed on",
            gaps=contract_gaps,
        )
        if outside is not None:
            raise WorkOrderValidationError(outside)
        changes.append(change)
    changes.sort(key=lambda entry: entry["holiday_date"])
    return answer, changes


def _holiday_changes(
    current: list[dict[str, Any]], new: list[dict[str, Any]]
) -> tuple[list[str], list[str], list[str]]:
    """The dates entered, taken off, and changed - in what they are, their kind, rate or description - as ISO dates,
    earliest first."""
    before = {item["holiday_date"]: item for item in current}
    after = {item["holiday_date"]: item for item in new}
    entered = sorted(day for day in after if day not in before)
    taken_off = sorted(day for day in before if day not in after)
    changed = sorted(
        day
        for day in after
        if day in before
        and any((before[day].get(field) or None) != (after[day].get(field) or None) for field in _CHANGE_FIELDS)
    )
    return [day.isoformat() for day in entered], [day.isoformat() for day in taken_off], [day.isoformat() for day in changed]


def save_work_order_holidays(
    db: Session,
    *,
    work_order_public_id: UUID,
    payload: WorkOrderHolidayListUpdate,
    current_user_public_id: str | None,
) -> WorkOrderHolidayListActionResponse:
    """Record the Work Order's answer and its changes to PBL's calendar, replacing the list as a whole.

    The Work Order is locked for the whole write, which also serializes it against a change to the contract dates -
    each constrains the other. An identical save records no event and keeps the version. The event carries the answer,
    the counts and the dates entered, taken off or changed, never the description or note text (the customer's
    wording, like Part 3's customer reference).
    """
    response: WorkOrderHolidayListActionResponse
    with rollback_on_error(db):
        work_order, work_order_id = _lock_work_order_for_contract_period(
            db, work_order_public_id, what_is_locked="Its holidays"
        )
        current = get_work_order_holiday_list_row(db, work_order_id=work_order_id)
        current_version = int(current["list_version"]) if current else None
        if payload.expected_list_version != current_version:
            raise WorkOrderHolidayListConflictError(_HOLIDAYS_CONFLICT_MESSAGE)

        contract_start, contract_end = contract_bounds_for_work_order(db, work_order_id=work_order_id)
        answer, changes = _normalize_holidays(
            payload,
            contract_start=contract_start,
            contract_end=contract_end,
            contract_gaps=contract_gaps_for_work_order(db, work_order_id=work_order_id),
        )
        current_changes = list_work_order_holiday_rows(db, holiday_list_id=int(current["holiday_list_id"])) if current else []
        entered, taken_off, changed = _holiday_changes(current_changes, changes)
        answer_changed = current is None or current["holidays_answer_code"] != answer

        if not answer_changed and not entered and not taken_off and not changed:
            # An identical save is not an edit: no version bump and no event.
            response = WorkOrderHolidayListActionResponse(
                holiday_list=_holiday_list_from_db(
                    db, work_order_public_id=work_order.public_id, work_order_id=work_order_id
                ),
                event=None,
            )
            db.rollback()
            return response

        if current is None:
            holiday_list_id = insert_work_order_holiday_list(
                db,
                public_id=str(uuid4()),
                work_order_id=work_order_id,
                holidays_answer_code=answer,
                current_user_public_id=current_user_public_id,
            )
            event_name = WORK_ORDER_HOLIDAYS_EVENT_RECORDED
            new_version = 1
            reason = "Holidays recorded for a Work Order."
        else:
            holiday_list_id = int(current["holiday_list_id"])
            updated = update_work_order_holiday_list(
                db,
                holiday_list_id=holiday_list_id,
                expected_list_version=int(current_version),
                holidays_answer_code=answer,
                current_user_public_id=current_user_public_id,
            )
            if updated != 1:
                raise WorkOrderHolidayListConflictError(_HOLIDAYS_CONFLICT_MESSAGE)
            delete_work_order_holidays(db, holiday_list_id=holiday_list_id)
            event_name = WORK_ORDER_HOLIDAYS_EVENT_UPDATED
            new_version = int(current_version) + 1
            reason = "Holidays changed for a Work Order."

        for item in changes:
            insert_work_order_holiday(db, public_id=str(uuid4()), holiday_list_id=holiday_list_id, **item)

        event = _record_billing_terms_event(
            db,
            work_order=work_order,
            event_name=event_name,
            reason=reason,
            current_user_public_id=current_user_public_id,
            payload={
                # Dates, codes and counts only - a date is not a commercial amount, and a description or note is the
                # customer's own wording, so it never leaves the record. "Added" names a kind of change since HOL-1,
                # so the dates a save puts on or takes off the list are "entered" and "taken off".
                "list_version": new_version,
                "holidays_answer_code": answer,
                "holidays_added_count": sum(1 for item in changes if item["change_code"] == WORK_ORDER_HOLIDAY_CHANGE_ADDED),
                "working_days_count": sum(
                    1 for item in changes if item["change_code"] == WORK_ORDER_HOLIDAY_CHANGE_WORKING_DAY
                ),
                "entered_dates": entered,
                "taken_off_dates": taken_off,
                "changed_dates": changed,
            },
        )
        response = WorkOrderHolidayListActionResponse(
            holiday_list=_holiday_list_from_db(db, work_order_public_id=work_order.public_id, work_order_id=work_order_id),
            event=event,
        )
        db.commit()
    return response
