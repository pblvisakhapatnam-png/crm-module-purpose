"""Slice 7D Part 3: the contract period and its extensions.

The Work Order's contract start and end dates, in crm_work_order_contract_period; the extensions that
move the end date, in crm_work_order_contract_extension; and each line's own dates, on the 7C detail
row. Nothing here writes to crm_work_order or crm_work_order_line, so the frozen handoff is untouched.
Nothing is calculated: these are recorded inputs that log sheets, release and billing will read later.

Every refusal names the dates it is refusing over (owner decision 17). The rule behind them is in
contract_period_rules.py, which has no database and no clock so it can be tested exhaustively and
reused by those later slices. Reading the contract bounds and gaps is in common.py, because line
detail and billing terms check dates against them too.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.work_orders.contract_period_rules import (
    contract_end_conflict_message,
    contract_start_conflict_message,
    contract_state,
    day_after,
    format_contract_date,
)
from app.modules.work_orders.contract import (
    WORK_ORDER_CONTRACT_END_BASIS_CODES,
    WORK_ORDER_CONTRACT_END_BASIS_FIXED_DATE,
    WORK_ORDER_CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE,
    WORK_ORDER_CONTRACT_EXTENSION_EVENT_RECORDED,
    WORK_ORDER_CONTRACT_EXTENSION_EVENT_REMOVED,
    WORK_ORDER_CONTRACT_PERIOD_EVENT_RECORDED,
    WORK_ORDER_CONTRACT_PERIOD_EVENT_UPDATED,
    WORK_ORDER_CONTRACT_PERIOD_MISSING_END,
    WORK_ORDER_CONTRACT_PERIOD_MISSING_START,
    WORK_ORDER_HOLIDAY_CHANGE_WORKING_DAY,
)
from app.modules.work_orders.repository import (
    delete_work_order_contract_extension,
    insert_work_order_contract_extension,
    insert_work_order_contract_period,
    list_work_order_billing_period_start_rows,
    list_work_order_contract_extension_rows,
    list_work_order_holiday_dates,
    list_work_order_line_date_rows,
    update_work_order_contract_period,
)
from app.modules.work_orders.schemas import (
    WorkOrderContractExtensionCreate,
    WorkOrderContractExtensionResponse,
    WorkOrderContractGapResponse,
    WorkOrderContractPeriodActionResponse,
    WorkOrderContractPeriodResponse,
    WorkOrderContractPeriodUpdate,
)
from app.modules.work_orders.services.common import (
    WorkOrderContractExtensionNotFoundError,
    WorkOrderContractPeriodConflictError,
    WorkOrderValidationError,
    _changed_line_detail_fields,
    _clean_optional,
    _contract_bounds,
    _contract_gaps,
    _contract_period_row,
    _get_work_order_and_id,
    _end_dates_changed,
    _lock_work_order_for_contract_period,
    _record_billing_terms_event,
    _same_value,
    _term_code,
)
from app.shared import business_time
from app.shared.transactions import rollback_on_error


_CONTRACT_PERIOD_CONFLICT_MESSAGE = (
    "Someone else changed the contract dates after you opened them. Reload to see their version."
)


def _check_contract_change_against_recorded_dates(
    db: Session,
    *,
    work_order_id: int,
    contract_start: date | None,
    contract_end: date | None,
) -> None:
    """Refuse a contract period that would exclude something already recorded (owner decision 17).

    Three things can already sit inside the contract and must not fall outside it: a line's own start
    and end dates, a billing-terms period start, and - since Slice 7D Part 4 - a holiday the Work Order
    lists. All are checked here rather than in each caller, because an edit of the dates, an extension
    and removing an extension all move the same bounds.

    The owner's example is the end side - "The contract cannot end on 1 February 2027, because this
    line has terms starting 1 March 2027". The start side is the same rule read the other way: dates
    are often entered before the contract is, so a start moved forward past a period that begins
    earlier is the same class of nonsense, and is refused with the matching message.
    """
    for row in list_work_order_billing_period_start_rows(db, work_order_id=work_order_id):
        period_start = row["effective_from"]
        subject = f"line {row['line_number']} has terms starting"
        if contract_start is not None and period_start < contract_start:
            raise WorkOrderValidationError(
                contract_start_conflict_message(contract_start, blocking_date=period_start, blocking_subject=subject)
            )
        if contract_end is not None and period_start > contract_end:
            raise WorkOrderValidationError(
                contract_end_conflict_message(contract_end, blocking_date=period_start, blocking_subject=subject)
            )

    # Slice 7D Part 4: a listed holiday is inside the contract when it is recorded, and the contract
    # cannot then move to leave it outside - the rule above, read for the holiday list. Since HOL-1 the
    # list also holds working days (Q4), held to the same rule and named for what they are. Gaps need no
    # check here: a gap only ever follows the end an extension continues from, so any day in it was
    # already after the contract's end and could not have been listed.
    for holiday_date, change_code in list_work_order_holiday_dates(db, work_order_id=work_order_id):
        subject = "a working day is listed on" if change_code == WORK_ORDER_HOLIDAY_CHANGE_WORKING_DAY else "a holiday is listed on"
        if contract_start is not None and holiday_date < contract_start:
            raise WorkOrderValidationError(
                contract_start_conflict_message(contract_start, blocking_date=holiday_date, blocking_subject=subject)
            )
        if contract_end is not None and holiday_date > contract_end:
            raise WorkOrderValidationError(
                contract_end_conflict_message(contract_end, blocking_date=holiday_date, blocking_subject=subject)
            )

    # An extension order cannot have been received before the contract starts (owner, 22 September
    # 2026). The extension route checks that as it records one; this is the same rule read from the
    # other side, so moving the start later cannot quietly leave an order dated before it.
    #
    # Nor can the start move past the end an extension continued from. An order that arrives after
    # the contract has ended is recorded normally (owner, 22 September 2026), so its received date is
    # no guard here: without this, a start could be moved into - or past - the days the extension
    # followed, and the contract would "start" after the end it was extended from.
    if contract_start is not None:
        for row in list_work_order_contract_extension_rows(db, work_order_id=work_order_id):
            number = int(row["extension_sequence_no"])
            received = row["received_date"]
            if received < contract_start:
                raise WorkOrderValidationError(
                    contract_start_conflict_message(
                        contract_start,
                        blocking_date=received,
                        blocking_subject=f"extension {number}'s order was received on",
                    )
                )
            previous_end = row.get("previous_end_date")
            if previous_end is not None and contract_start > previous_end:
                raise WorkOrderValidationError(
                    contract_start_conflict_message(
                        contract_start,
                        blocking_date=previous_end,
                        blocking_subject=f"extension {number} continues from an end date of",
                    )
                )

    for row in list_work_order_line_date_rows(db, work_order_id=work_order_id):
        line_start = row.get("line_start_date")
        line_end = row.get("line_end_date")
        if contract_start is not None and line_start is not None and line_start < contract_start:
            raise WorkOrderValidationError(
                contract_start_conflict_message(
                    contract_start, blocking_date=line_start, blocking_subject=f"line {row['line_number']} starts on"
                )
            )
        if contract_end is not None and line_end is not None and line_end > contract_end:
            raise WorkOrderValidationError(
                contract_end_conflict_message(
                    contract_end, blocking_date=line_end, blocking_subject=f"line {row['line_number']} ends on"
                )
            )
        # A line whose own start falls after a shortened contract end is equally excluded.
        if contract_end is not None and line_start is not None and line_start > contract_end:
            raise WorkOrderValidationError(
                contract_end_conflict_message(
                    contract_end, blocking_date=line_start, blocking_subject=f"line {row['line_number']} starts on"
                )
            )
        if contract_start is not None and line_end is not None and line_end < contract_start:
            raise WorkOrderValidationError(
                contract_start_conflict_message(
                    contract_start, blocking_date=line_end, blocking_subject=f"line {row['line_number']} ends on"
                )
            )


def _contract_period_missing_items(row: dict[str, Any] | None) -> list[str]:
    """What has not been answered yet. "Until the work is complete" is an answer, so it is not missing;
    that it still leaves the Work Order un-closable is reported by needs_firm_end_date instead."""
    missing: list[str] = []
    if row is None or row.get("contract_start_date") is None:
        missing.append(WORK_ORDER_CONTRACT_PERIOD_MISSING_START)
    if row is None or row.get("contract_end_basis_code") is None:
        missing.append(WORK_ORDER_CONTRACT_PERIOD_MISSING_END)
    return missing


def _build_contract_extension(row: dict[str, Any]) -> WorkOrderContractExtensionResponse:
    return WorkOrderContractExtensionResponse(
        extension_public_id=row["extension_public_id"],
        extension_sequence_no=int(row["extension_sequence_no"]),
        previous_end_basis_code=row.get("previous_end_basis_code"),
        previous_end_date=row.get("previous_end_date"),
        new_end_date=row["new_end_date"],
        extension_start_date=row.get("extension_start_date"),
        customer_reference=row.get("customer_reference"),
        received_date=row["received_date"],
        extension_notes=row.get("extension_notes"),
        created_by=row.get("created_by"),
        created_by_display_name=row.get("created_by_display_name"),
        created_at=row["created_at"],
    )


def _build_contract_period_response(
    *,
    work_order_public_id: UUID,
    row: dict[str, Any] | None,
    extensions: list[dict[str, Any]],
    today: date,
) -> WorkOrderContractPeriodResponse:
    start, end = _contract_bounds(row)
    basis = row.get("contract_end_basis_code") if row else None
    gaps = _contract_gaps(extensions)
    state = contract_state(
        contract_start=start, contract_end=end, contract_end_basis_code=basis, today=today, gaps=gaps
    )
    missing = _contract_period_missing_items(row)
    return WorkOrderContractPeriodResponse(
        work_order_public_id=work_order_public_id,
        period_public_id=row.get("period_public_id") if row else None,
        period_version=int(row["period_version"]) if row else None,
        contract_start_date=start,
        contract_end_basis_code=basis,
        contract_end_date=end,
        contract_notes=row.get("contract_notes") if row else None,
        contract_state_code=state.state_code,
        contract_state_label=state.state_label,
        days_until_start=state.days_until_start,
        days_until_end=state.days_until_end,
        needs_firm_end_date=basis == WORK_ORDER_CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE,
        is_complete=not missing,
        missing_items=missing,
        extensions=[_build_contract_extension(item) for item in extensions],
        gaps=[
            WorkOrderContractGapResponse(
                first_day=gap.first_day, last_day=gap.last_day, extension_sequence_no=gap.extension_sequence_no
            )
            for gap in gaps
        ],
        updated_by=row.get("updated_by") if row else None,
        updated_by_display_name=row.get("updated_by_display_name") if row else None,
        updated_at=row.get("updated_at") if row else None,
    )


def _contract_period_from_db(
    db: Session, *, work_order_public_id: UUID, work_order_id: int, today: date
) -> WorkOrderContractPeriodResponse:
    return _build_contract_period_response(
        work_order_public_id=work_order_public_id,
        row=_contract_period_row(db, work_order_id=work_order_id),
        extensions=list_work_order_contract_extension_rows(db, work_order_id=work_order_id),
        today=today,
    )


def get_work_order_contract_period(
    db: Session, work_order_public_id: UUID, *, today: date | None = None
) -> WorkOrderContractPeriodResponse:
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    return _contract_period_from_db(
        db,
        work_order_public_id=work_order.public_id,
        work_order_id=work_order_id,
        today=today or business_time.india_today(),
    )


def _normalize_contract_period(payload: WorkOrderContractPeriodUpdate) -> dict[str, Any]:
    """Validate the answer's own shape and return storable values.

    The end basis and the end date travel together: FIXED_DATE needs a date, UNTIL_WORK_COMPLETE
    carries none, and neither recorded carries none either. A date without a basis is refused rather
    than given one, because which of the two answers the user meant is exactly what is missing.
    """
    basis = _term_code(
        payload.contract_end_basis_code,
        WORK_ORDER_CONTRACT_END_BASIS_CODES,
        "The contract end must be a date, or recorded as until the work is complete.",
    )
    start = payload.contract_start_date
    end = payload.contract_end_date

    if basis == WORK_ORDER_CONTRACT_END_BASIS_FIXED_DATE and end is None:
        raise WorkOrderValidationError("Enter the date the contract ends, or record it as until the work is complete.")
    if basis == WORK_ORDER_CONTRACT_END_BASIS_UNTIL_WORK_COMPLETE and end is not None:
        raise WorkOrderValidationError(
            "A contract that runs until the work is complete has no end date. Remove the date, or choose a fixed end date."
        )
    if basis is None and end is not None:
        raise WorkOrderValidationError(
            "Choose whether the contract ends on a fixed date or runs until the work is complete."
        )
    if start is not None and end is not None and end < start:
        raise WorkOrderValidationError(
            f"The contract cannot end on {format_contract_date(end)}, "
            f"before it starts on {format_contract_date(start)}."
        )

    return {
        "contract_start_date": start,
        "contract_end_basis_code": basis,
        "contract_end_date": end,
        "contract_notes": _clean_optional(payload.contract_notes),
    }


def _contract_period_event_payload(
    *, period_version: int, values: dict[str, Any], changed_fields: list[str]
) -> dict[str, object]:
    """Dates and codes only - a contract date is not a commercial amount, and there are none here."""
    return {
        "period_version": period_version,
        "contract_start_date": values["contract_start_date"].isoformat() if values["contract_start_date"] else None,
        "contract_end_basis_code": values["contract_end_basis_code"],
        "contract_end_date": values["contract_end_date"].isoformat() if values["contract_end_date"] else None,
        "changed_fields": changed_fields,
    }


def save_work_order_contract_period(
    db: Session,
    *,
    work_order_public_id: UUID,
    payload: WorkOrderContractPeriodUpdate,
    current_user_public_id: str | None,
) -> WorkOrderContractPeriodActionResponse:
    response: WorkOrderContractPeriodActionResponse
    with rollback_on_error(db):
        work_order, work_order_id = _lock_work_order_for_contract_period(
            db, work_order_public_id, what_is_locked="Its contract dates"
        )
        current = _contract_period_row(db, work_order_id=work_order_id)
        current_version = int(current["period_version"]) if current else None
        if payload.expected_period_version != current_version:
            raise WorkOrderContractPeriodConflictError(_CONTRACT_PERIOD_CONFLICT_MESSAGE)

        values = _normalize_contract_period(payload)
        # Once an extension exists, the end date moves only through extensions (owner, 22 September
        # 2026). Before that decision the form could change it, and a save silently undid every
        # extension recorded so far - the owner's screen check found it happening twice. The start date
        # and the notes stay editable; resending the end unchanged is not a change.
        if current is not None and list_work_order_contract_extension_rows(db, work_order_id=work_order_id):
            end_changed = not _same_value(
                current.get("contract_end_basis_code"), values["contract_end_basis_code"]
            ) or not _same_value(current.get("contract_end_date"), values["contract_end_date"])
            if end_changed:
                raise WorkOrderValidationError(
                    "Once an extension has been recorded, the contract end date changes only through extensions. "
                    "Record another extension, or remove the latest one."
                )
        _check_contract_change_against_recorded_dates(
            db,
            work_order_id=work_order_id,
            contract_start=values["contract_start_date"],
            contract_end=values["contract_end_date"],
        )
        changed_fields = _changed_line_detail_fields(current, values)

        if current is not None and not changed_fields:
            # An identical save is not an edit: no version bump and no event.
            response = WorkOrderContractPeriodActionResponse(
                contract_period=_contract_period_from_db(
                    db,
                    work_order_public_id=work_order.public_id,
                    work_order_id=work_order_id,
                    today=business_time.india_today(),
                ),
                event=None,
            )
            db.rollback()
            return response

        if current is None:
            insert_work_order_contract_period(
                db,
                public_id=str(uuid4()),
                work_order_id=work_order_id,
                values=values,
                current_user_public_id=current_user_public_id,
            )
            event_name = WORK_ORDER_CONTRACT_PERIOD_EVENT_RECORDED
            new_version = 1
            reason = "Contract dates recorded for a Work Order."
        else:
            updated = update_work_order_contract_period(
                db,
                work_order_id=work_order_id,
                expected_period_version=int(current_version),
                values=values,
                current_user_public_id=current_user_public_id,
            )
            if updated != 1:
                raise WorkOrderContractPeriodConflictError(_CONTRACT_PERIOD_CONFLICT_MESSAGE)
            event_name = WORK_ORDER_CONTRACT_PERIOD_EVENT_UPDATED
            new_version = int(current_version) + 1
            reason = "Contract dates changed for a Work Order."

        event = _record_billing_terms_event(
            db,
            work_order=work_order,
            event_name=event_name,
            reason=reason,
            current_user_public_id=current_user_public_id,
            payload=_contract_period_event_payload(
                period_version=new_version, values=values, changed_fields=changed_fields
            ),
        )
        # 8A core: a requirement without an end of its own runs to the contract's end.
        _end_dates_changed(db, work_order_public_id=work_order.public_id, current_user_public_id=current_user_public_id)
        response = WorkOrderContractPeriodActionResponse(
            contract_period=_contract_period_from_db(
                db, work_order_public_id=work_order.public_id, work_order_id=work_order_id, today=business_time.india_today()
            ),
            event=event,
        )
        db.commit()
    return response


def _extension_start_date(
    payload: WorkOrderContractExtensionCreate,
    *,
    current_basis: str | None,
    current_end: date | None,
    new_end: date,
) -> date | None:
    """The day an extension starts (owner, 22 September 2026).

    Normally the day after the fixed end it follows, and that is what an omitted start means. A later
    start leaves days no contract runs on, so it is recorded only when the caller says the user
    confirmed it - the screen asks, naming the days. A start on or before the current end is not an
    extension. Where the end is open-ended or not recorded there is no end to follow, so there is no
    start date to record, and one given is refused rather than silently dropped.
    """
    if current_basis != WORK_ORDER_CONTRACT_END_BASIS_FIXED_DATE or current_end is None:
        if payload.extension_start_date is not None:
            raise WorkOrderValidationError(
                "An extension start date applies only when the contract has a fixed end date to continue "
                "from. Leave it empty: this extension sets the end date."
            )
        return None
    normal_start = day_after(current_end)
    extension_start = payload.extension_start_date or normal_start
    if extension_start <= current_end:
        raise WorkOrderValidationError(
            f"An extension must start after the contract's current end date, {format_contract_date(current_end)}. "
            f"It normally starts the day after, on {format_contract_date(normal_start)}."
        )
    if extension_start > new_end:
        raise WorkOrderValidationError(
            f"The extension cannot start on {format_contract_date(extension_start)}, "
            f"after its own end date of {format_contract_date(new_end)}."
        )
    if extension_start > normal_start:
        if payload.gap_confirmed_from is None:
            raise WorkOrderValidationError(
                f"This extension starts on {format_contract_date(extension_start)}, not on "
                f"{format_contract_date(normal_start)}, the day after the contract ends. The days from "
                f"{format_contract_date(normal_start)} to {format_contract_date(extension_start - timedelta(days=1))} "
                "would be outside the contract. Confirm that to record it."
            )
        # The confirmation must be for these days. If the end moved after the page was read - another
        # user recorded or removed an extension - the user agreed to a different gap, and one user's
        # agreement to one gap must not record another (the same lesson as review findings F-02/F-07).
        if payload.gap_confirmed_from != normal_start:
            raise WorkOrderContractPeriodConflictError(
                "The contract end date changed after you opened this page, so the days this extension would "
                "leave outside the contract are not the ones you confirmed. Reload to see the latest dates."
            )
    return extension_start


def create_work_order_contract_extension(
    db: Session,
    *,
    work_order_public_id: UUID,
    payload: WorkOrderContractExtensionCreate,
    current_user_public_id: str | None,
) -> WorkOrderContractPeriodActionResponse:
    """Record one extension and move the contract end date to it.

    The extension row keeps what the contract said before, so previous end dates stay as history
    (owner decision 15). An extension must move a fixed end later, and its order may not be dated
    before the contract starts (owner's screen check, 22 September 2026). An extension typed wrongly
    is removed with remove_work_order_contract_extension rather than answered with another; from 17 to
    22 September recording another, earlier or later, was how it was put right.

    Where no contract period has been recorded at all, the extension creates one and sets the end
    date, with no previous end recorded. That is truthful rather than tidy: the customer did send an
    end date, and refusing it would only force the same date to be typed somewhere else first.
    """
    response: WorkOrderContractPeriodActionResponse
    with rollback_on_error(db):
        work_order, work_order_id = _lock_work_order_for_contract_period(
            db, work_order_public_id, what_is_locked="Its contract dates"
        )
        current = _contract_period_row(db, work_order_id=work_order_id)
        start, current_end = _contract_bounds(current)
        current_basis = current.get("contract_end_basis_code") if current else None
        new_end = payload.new_end_date

        # An extension must move the end later (owner, 22 September 2026). Until then any different
        # date was accepted, because recording another extension was how a mistake was put right; now
        # the latest extension can be removed instead, so an earlier date is no longer an extension.
        if current_basis == WORK_ORDER_CONTRACT_END_BASIS_FIXED_DATE and current_end is not None and new_end <= current_end:
            raise WorkOrderValidationError(
                f"An extension must move the end date later. The contract currently ends on "
                f"{format_contract_date(current_end)}, so {format_contract_date(new_end)} would not extend it. "
                "To correct an extension recorded in error, remove it instead."
            )
        # Any received date is accepted except one before the contract starts (owner, 22 September
        # 2026) - including one after the contract has ended, when a verbal commitment came first and
        # the order arrived later. An order dated long ago is only warned about, on the screen.
        if start is not None and payload.received_date < start:
            raise WorkOrderValidationError(
                f"This extension order is dated {format_contract_date(payload.received_date)}, "
                f"before the contract starts on {format_contract_date(start)}."
            )
        extension_start = _extension_start_date(
            payload, current_basis=current_basis, current_end=current_end, new_end=new_end
        )
        if start is not None and new_end < start:
            raise WorkOrderValidationError(
                f"The contract cannot end on {format_contract_date(new_end)}, "
                f"before it starts on {format_contract_date(start)}."
            )
        _check_contract_change_against_recorded_dates(
            db, work_order_id=work_order_id, contract_start=start, contract_end=new_end
        )

        extensions = list_work_order_contract_extension_rows(db, work_order_id=work_order_id)
        sequence_no = len(extensions) + 1
        extension_public_id = str(uuid4())
        insert_work_order_contract_extension(
            db,
            public_id=extension_public_id,
            work_order_id=work_order_id,
            extension_sequence_no=sequence_no,
            previous_end_basis_code=current_basis,
            previous_end_date=current_end,
            new_end_date=new_end,
            extension_start_date=extension_start,
            customer_reference=_clean_optional(payload.customer_reference),
            received_date=payload.received_date,
            extension_notes=_clean_optional(payload.extension_notes),
            current_user_public_id=current_user_public_id,
        )

        values = {
            "contract_start_date": start,
            "contract_end_basis_code": WORK_ORDER_CONTRACT_END_BASIS_FIXED_DATE,
            "contract_end_date": new_end,
            "contract_notes": current.get("contract_notes") if current else None,
        }
        if current is None:
            insert_work_order_contract_period(
                db,
                public_id=str(uuid4()),
                work_order_id=work_order_id,
                values=values,
                current_user_public_id=current_user_public_id,
            )
        else:
            updated = update_work_order_contract_period(
                db,
                work_order_id=work_order_id,
                expected_period_version=int(current["period_version"]),
                values=values,
                current_user_public_id=current_user_public_id,
            )
            if updated != 1:
                raise WorkOrderContractPeriodConflictError(_CONTRACT_PERIOD_CONFLICT_MESSAGE)

        event = _record_billing_terms_event(
            db,
            work_order=work_order,
            event_name=WORK_ORDER_CONTRACT_EXTENSION_EVENT_RECORDED,
            reason="Contract extension recorded for a Work Order.",
            current_user_public_id=current_user_public_id,
            payload={
                "extension_public_id": extension_public_id,
                "extension_sequence_no": sequence_no,
                "previous_end_basis_code": current_basis,
                "previous_end_date": current_end.isoformat() if current_end else None,
                "new_end_date": new_end.isoformat(),
                "extension_start_date": extension_start.isoformat() if extension_start else None,
                "starts_after_a_gap": bool(
                    current_end is not None and extension_start is not None
                    and extension_start > day_after(current_end)
                ),
                "received_date": payload.received_date.isoformat(),
                "has_customer_reference": bool(_clean_optional(payload.customer_reference)),
            },
        )
        # 8A core: a requirement without an end of its own runs to the contract's end.
        _end_dates_changed(db, work_order_public_id=work_order.public_id, current_user_public_id=current_user_public_id)
        response = WorkOrderContractPeriodActionResponse(
            contract_period=_contract_period_from_db(
                db, work_order_public_id=work_order.public_id, work_order_id=work_order_id, today=business_time.india_today()
            ),
            event=event,
        )
        db.commit()
    return response


def remove_work_order_contract_extension(
    db: Session,
    *,
    work_order_public_id: UUID,
    extension_public_id: UUID,
    current_user_public_id: str | None,
) -> WorkOrderContractPeriodActionResponse:
    """Remove the most recent extension and put the contract end back to what it was before it.

    The owner's decision of 22 September 2026, replacing "record another extension" as the way to put
    a mistake right. Only the latest can go, exactly as only the latest billing-terms period can: a
    chain with a gap in the middle would no longer explain how the current end was reached. Remove
    every extension and the end date becomes editable again.

    The row is deleted; the business event is what keeps the fact that it existed. Restoring an
    earlier end is checked like any other move of the end, so it cannot leave a billing period or a
    line's own date outside the contract.
    """
    response: WorkOrderContractPeriodActionResponse
    with rollback_on_error(db):
        work_order, work_order_id = _lock_work_order_for_contract_period(
            db, work_order_public_id, what_is_locked="Its contract dates"
        )
        current = _contract_period_row(db, work_order_id=work_order_id)
        extensions = list_work_order_contract_extension_rows(db, work_order_id=work_order_id)
        target = next(
            (row for row in extensions if str(row["extension_public_id"]) == str(extension_public_id)), None
        )
        if current is None or target is None:
            raise WorkOrderContractExtensionNotFoundError("Contract extension not found on this Work Order.")
        latest = extensions[-1]
        if str(latest["extension_public_id"]) != str(extension_public_id):
            raise WorkOrderValidationError(
                f"Only the most recent extension can be removed. Extension "
                f"{int(latest['extension_sequence_no'])} is the most recent; reload if you did not expect that."
            )

        restored_basis = target.get("previous_end_basis_code")
        restored_end = target.get("previous_end_date")
        start = current.get("contract_start_date")
        # The start can have moved later since this extension was recorded, past the end it replaced.
        if start is not None and restored_end is not None and restored_end < start:
            raise WorkOrderValidationError(
                f"This extension cannot be removed. The contract would end on {format_contract_date(restored_end)}, "
                f"before it starts on {format_contract_date(start)}."
            )
        try:
            _check_contract_change_against_recorded_dates(
                db, work_order_id=work_order_id, contract_start=start, contract_end=restored_end
            )
        except WorkOrderValidationError as exc:
            raise WorkOrderValidationError(f"This extension cannot be removed. {exc}") from exc

        deleted = delete_work_order_contract_extension(
            db, work_order_id=work_order_id, public_id=str(extension_public_id)
        )
        if deleted != 1:
            raise WorkOrderContractPeriodConflictError(_CONTRACT_PERIOD_CONFLICT_MESSAGE)
        updated = update_work_order_contract_period(
            db,
            work_order_id=work_order_id,
            expected_period_version=int(current["period_version"]),
            values={
                "contract_start_date": start,
                "contract_end_basis_code": restored_basis,
                "contract_end_date": restored_end,
                "contract_notes": current.get("contract_notes"),
            },
            current_user_public_id=current_user_public_id,
        )
        if updated != 1:
            raise WorkOrderContractPeriodConflictError(_CONTRACT_PERIOD_CONFLICT_MESSAGE)

        event = _record_billing_terms_event(
            db,
            work_order=work_order,
            event_name=WORK_ORDER_CONTRACT_EXTENSION_EVENT_REMOVED,
            reason="Contract extension removed from a Work Order.",
            current_user_public_id=current_user_public_id,
            payload={
                "extension_public_id": str(extension_public_id),
                "extension_sequence_no": int(target["extension_sequence_no"]),
                "removed_new_end_date": target["new_end_date"].isoformat(),
                "restored_end_basis_code": restored_basis,
                "restored_end_date": restored_end.isoformat() if restored_end else None,
            },
        )
        # 8A core: a requirement without an end of its own runs to the contract's end.
        _end_dates_changed(db, work_order_public_id=work_order.public_id, current_user_public_id=current_user_public_id)
        response = WorkOrderContractPeriodActionResponse(
            contract_period=_contract_period_from_db(
                db, work_order_public_id=work_order.public_id, work_order_id=work_order_id, today=business_time.india_today()
            ),
            event=event,
        )
        db.commit()
    return response
