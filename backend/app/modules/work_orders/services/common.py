"""What more than one Work Order concern needs: the module's exceptions, and the helpers several
concerns share.

The exceptions are the Work Order module's error vocabulary - routes.py maps each to an HTTP status -
so they stay together here even where only one concern raises them. Everything else is here because
more than one of handoff, amendments, line_detail, billing_terms, contract_period, holidays and
resulting_holidays calls it;
a helper one concern alone uses lives with that concern.

Some names still carry the concern that first needed them: `_record_billing_terms_event` records every
Work Order event the contract period and the holiday list write too, `_changed_line_detail_fields`
compares any two sets of stored values, and `_lock_work_order_for_contract_period` also serializes
copying billing terms and saving the holiday list. They were moved, not renamed, so that splitting the
service changed no function's body (TE-6).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.accounts.service import (
    AccountNotFoundError,
    get_account_tax_profile_bundle,
    list_account_addresses,
)
from app.modules.events.schemas import BusinessEventSummary
from app.modules.events.service import record_business_event
from app.modules.work_orders.contract_period_rules import ContractGap, gap_before_extension
from app.modules.work_orders.contract import (
    WORK_ORDER_CONTRACT_PERIOD_LOCKED_WORK_ORDER_STATUSES,
    WORK_ORDER_MODULE_NAME,
    WORK_ORDER_RECORD_TYPE,
)
from app.modules.work_orders.repository import (
    get_work_order_by_public_id,
    get_work_order_contract_period_row,
    get_work_order_internal_id,
    list_work_order_contract_extension_rows,
    lock_work_order_row,
    share_lock_work_order_status,
)
from app.modules.work_orders.schemas import WorkOrderResponse
from app.shared import business_time


class WorkOrderNotFoundError(LookupError):
    pass


class WorkOrderCommercialOfferNotFoundError(LookupError):
    pass


class WorkOrderValidationError(ValueError):
    pass


class WorkOrderAmendmentNotFoundError(LookupError):
    pass


class WorkOrderAmendmentLineNotFoundError(LookupError):
    pass


class WorkOrderLineNotFoundError(LookupError):
    pass


class WorkOrderLineDetailConflictError(ValueError):
    """The detail was changed by someone else after the caller read it."""


class WorkOrderLineBillingTermNotFoundError(LookupError):
    pass


class WorkOrderContractExtensionNotFoundError(LookupError):
    """The extension named is not on this Work Order (or has already been removed)."""


class WorkOrderContractPeriodConflictError(ValueError):
    """The contract period moved underneath the caller. Reported as 409, like the other two."""


class WorkOrderLineBillingTermsConflictError(ValueError):
    """A line's billing terms were changed by someone else after the caller read them."""


class WorkOrderHolidayListConflictError(ValueError):
    """The Work Order's holiday list was changed by someone else after the caller read it (Slice 7D
    Part 4). Reported as 409, like the others."""


class WorkOrderHandoffConflictError(ValueError):
    """The handoff's refusal of what is already on a Work Order (CS-04 part 1), reported as 409 with a message naming
    the Work Orders concerned. Two kinds: an offer line with nothing left, or less than asked - a line may be split
    across several Work Orders, but together they hold no more than its quantity; or a customer reference already on a
    Work Order of the offer - one customer order makes one Work Order."""


def _event_dict(event: BusinessEventSummary) -> dict[str, object]:
    return event.model_dump()


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


# Moved here from line_detail.py by HOL-1: the holidays that apply (resulting_holidays.py) read each line's site as
# the line's detail does, so two concerns now call them.


def _account_reference_maps(
    db: Session, account_public_id: UUID | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Active addresses and active GSTINs of the Work Order's Account, keyed by public id.

    The accounts service lists active records only, so a reference missing from these maps is
    either another Account's record or one no longer active - both are unusable here."""
    if account_public_id is None:
        return {}, {}
    try:
        addresses = list_account_addresses(db, account_public_id=account_public_id)
        gstins = get_account_tax_profile_bundle(db, account_public_id=account_public_id).gstins
    except AccountNotFoundError:
        return {}, {}
    return (
        {str(address.public_id): address for address in addresses},
        {str(gstin.public_id): gstin for gstin in gstins},
    )


def _usable_address(addresses: dict[str, Any], public_id: object, allowed_types: tuple[str, ...]) -> Any | None:
    if public_id is None:
        return None
    address = addresses.get(str(public_id))
    if address is None or address.address_type_code not in allowed_types:
        return None
    return address


def get_work_order(db: Session, public_id: UUID) -> WorkOrderResponse:
    work_order = get_work_order_by_public_id(db, str(public_id))
    if work_order is None:
        raise WorkOrderNotFoundError("Work Order not found.")
    return work_order


def _get_work_order_and_id(
    db: Session,
    work_order_public_id: UUID,
    *,
    for_update: bool = False,
) -> tuple[WorkOrderResponse, int]:
    """Fetch one Work Order, optionally locking it first.

    `for_update=True` is required by amendment creation, which cannot lock the amendment row it
    is about to insert and must instead serialize on the parent. Taking the lock inside this
    shared read means the caller cannot read the Work Order's existing amendments and *then*
    remember to lock: the lock is part of the read, or it is absent for a caller that does not
    need it.
    """
    if for_update and lock_work_order_row(db, public_id=str(work_order_public_id)) is None:
        raise WorkOrderNotFoundError("Work Order not found.")

    work_order = get_work_order(db, work_order_public_id)
    work_order_id = get_work_order_internal_id(db, str(work_order_public_id))
    if work_order_id is None:
        raise WorkOrderNotFoundError("Work Order not found.")
    return work_order, work_order_id


def _same_value(old_value: object, new_value: object) -> bool:
    if old_value is None or new_value is None:
        return old_value is None and new_value is None
    if isinstance(new_value, Decimal) or isinstance(old_value, Decimal):
        return Decimal(str(old_value)) == Decimal(str(new_value))
    return str(old_value) == str(new_value)


def _changed_line_detail_fields(current: dict[str, Any] | None, values: dict[str, Any]) -> list[str]:
    """Fields whose stored value would change. On a first save, every field given a value."""
    return [
        column
        for column, new_value in values.items()
        if not _same_value(current.get(column) if current else None, new_value)
    ]


INDIA_TIME_ZONE = business_time.BUSINESS_TIME_ZONE


# 8A core (independent review, round 1): a module that keeps something worked out from a Work Order's contract end or
# a line's own end registers here when it is imported - Resource Requirements, whose requirements without an end of
# their own run to them. This module never imports it. Each listener is called in the writing transaction, after the
# dates are written and while the Work Order's row lock is held, with the Work Order's public id and the user.
EndDatesListener = Callable[[Session, str, "str | None"], None]
_END_DATES_LISTENERS: list[EndDatesListener] = []


def hold_work_order_status(db: Session, work_order_public_id: UUID | str) -> str:
    """The Work Order's status, read under a shared lock on its row held until the caller's transaction ends (8A
    core, independent review round 2, 8A-R2-001). A module writing records that belong to a Work Order takes it
    first, so a change to the Work Order - its closure included, which takes the row's update lock as every Work
    Order write does - either waits for that write or is seen by it."""
    status_code = share_lock_work_order_status(db, public_id=str(work_order_public_id))
    if status_code is None:
        raise WorkOrderNotFoundError("Work Order not found.")
    return status_code


def register_end_dates_listener(listener: EndDatesListener) -> None:
    """Called when a module that depends on a Work Order's end dates is imported; registering twice has no effect."""
    if listener not in _END_DATES_LISTENERS:
        _END_DATES_LISTENERS.append(listener)


def _end_dates_changed(db: Session, *, work_order_public_id: UUID | str, current_user_public_id: str | None) -> None:
    """Tell the registered listeners that the contract's end or a line's own end may have moved."""
    for listener in _END_DATES_LISTENERS:
        listener(db, str(work_order_public_id), current_user_public_id)


def _term_code(value: str | None, allowed: tuple[str, ...], message: str) -> str | None:
    cleaned = _clean_optional(value)
    if cleaned is None:
        return None
    cleaned = cleaned.upper()
    if cleaned not in allowed:
        raise WorkOrderValidationError(message)
    return cleaned


def _record_billing_terms_event(
    db: Session,
    *,
    work_order: WorkOrderResponse,
    event_name: str,
    reason: str,
    current_user_public_id: str | None,
    payload: dict[str, object],
) -> dict[str, object]:
    return _event_dict(
        record_business_event(
            db,
            event_name=event_name,
            source_module=WORK_ORDER_MODULE_NAME,
            record_type=WORK_ORDER_RECORD_TYPE,
            record_public_id=str(work_order.public_id),
            user_public_id=current_user_public_id,
            reason=reason,
            event_payload=payload,
        )
    )


def _contract_period_row(db: Session, *, work_order_id: int) -> dict[str, Any] | None:
    return get_work_order_contract_period_row(db, work_order_id=work_order_id)


def _contract_bounds(row: dict[str, Any] | None) -> tuple[date | None, date | None]:
    """The two dates the rules need. "Until the work is complete" has no end date to check against."""
    if row is None:
        return None, None
    return row.get("contract_start_date"), row.get("contract_end_date")


def contract_bounds_for_work_order(db: Session, *, work_order_id: int) -> tuple[date | None, date | None]:
    """The contract start and end of one Work Order, for a caller that has to check a date against it."""
    return _contract_bounds(_contract_period_row(db, work_order_id=work_order_id))


def _contract_gaps(extensions: list[dict[str, Any]]) -> tuple[ContractGap, ...]:
    """The days no contract runs on, one per extension that starts later than the day after the end
    it follows (owner, 22 September 2026). Oldest first, as the extensions are."""
    gaps = (
        gap_before_extension(
            previous_end=row.get("previous_end_date"),
            extension_start=row.get("extension_start_date"),
            extension_sequence_no=int(row["extension_sequence_no"]),
        )
        for row in extensions
    )
    return tuple(gap for gap in gaps if gap is not None)


def contract_gaps_for_work_order(db: Session, *, work_order_id: int) -> tuple[ContractGap, ...]:
    """A caller checking a date against the contract needs these beside the start and end: a date in
    a gap is outside the contract (owner, 22 September 2026)."""
    return _contract_gaps(list_work_order_contract_extension_rows(db, work_order_id=work_order_id))


def _lock_work_order_for_contract_period(
    db: Session, work_order_public_id: UUID, *, what_is_locked: str
) -> tuple[WorkOrderResponse, int]:
    """Lock the Work Order, serializing every change to its contract period, its lines' dates and its
    lines' billing terms against each other - they all constrain one another."""
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id, for_update=True)
    if work_order.work_order_status_code in WORK_ORDER_CONTRACT_PERIOD_LOCKED_WORK_ORDER_STATUSES:
        raise WorkOrderValidationError(f"This Work Order is closed. {what_is_locked} can no longer be changed.")
    return work_order, work_order_id
