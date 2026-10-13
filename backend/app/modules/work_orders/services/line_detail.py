"""Slice 7C Work Order line operational detail.

Detail recorded after handoff, in crm_work_order_line_detail. Nothing here writes to crm_work_order or
crm_work_order_line, and nothing here is reachable from the handoff. Account addresses and GSTINs are
read through the accounts service only.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.events.service import record_business_event
from app.modules.work_orders.contract_period_rules import (
    ContractGap,
    date_outside_contract_message,
    format_contract_date,
)
from app.modules.work_orders.contract import (
    WORK_ORDER_LINE_BILLING_ADDRESS_TYPES,
    WORK_ORDER_LINE_BILLING_GSTIN_EXCLUDED_STATES,
    WORK_ORDER_LINE_DETAIL_EVENT_RECORDED,
    WORK_ORDER_LINE_DETAIL_EVENT_UPDATED,
    WORK_ORDER_LINE_DETAIL_LOCKED_WORK_ORDER_STATUSES,
    WORK_ORDER_LINE_DETAIL_MISSING_BILLING_ADDRESS,
    WORK_ORDER_LINE_DETAIL_MISSING_BILLING_GSTIN,
    WORK_ORDER_LINE_DETAIL_MISSING_SITE_ADDRESS,
    WORK_ORDER_LINE_SITE_ADDRESS_TYPES,
    WORK_ORDER_MODULE_NAME,
    WORK_ORDER_RECORD_TYPE,
)
from app.modules.work_orders.repository import (
    get_work_order_line_context,
    get_work_order_line_detail_row,
    insert_work_order_line_detail,
    list_work_order_line_detail_rows,
    update_work_order_line_detail,
)
from app.modules.work_orders.schemas import (
    WorkOrderLineDetailActionResponse,
    WorkOrderLineDetailAddress,
    WorkOrderLineDetailGstin,
    WorkOrderLineDetailResponse,
    WorkOrderLineDetailUpdate,
)
from app.modules.work_orders.services.common import (
    WorkOrderLineDetailConflictError,
    WorkOrderLineNotFoundError,
    WorkOrderValidationError,
    _account_reference_maps,
    _changed_line_detail_fields,
    _clean_optional,
    _end_dates_changed,
    _event_dict,
    _get_work_order_and_id,
    _usable_address,
    contract_bounds_for_work_order,
    contract_gaps_for_work_order,
)
from app.shared.transactions import rollback_on_error


def _detail_address(address: Any | None) -> WorkOrderLineDetailAddress | None:
    if address is None:
        return None
    return WorkOrderLineDetailAddress(
        public_id=address.public_id,
        address_type_code=address.address_type_code,
        address_line1=address.address_line1,
        city=address.city,
        state=address.state,
        postal_code=address.postal_code,
    )


def _detail_gstin(gstin: Any | None) -> WorkOrderLineDetailGstin | None:
    if gstin is None:
        return None
    return WorkOrderLineDetailGstin(
        public_id=gstin.public_id,
        gstin=gstin.gstin,
        state_code=gstin.state_code,
        verification_state_code=gstin.gstin_verification_state_code,
    )


def _usable_gstin(gstins: dict[str, Any], public_id: object) -> Any | None:
    if public_id is None:
        return None
    gstin = gstins.get(str(public_id))
    if gstin is None or gstin.gstin_verification_state_code in WORK_ORDER_LINE_BILLING_GSTIN_EXCLUDED_STATES:
        return None
    return gstin


def _build_line_detail_response(
    row: dict[str, Any], *, addresses: dict[str, Any], gstins: dict[str, Any]
) -> WorkOrderLineDetailResponse:
    """Resolve one line's detail for display and compute its advisory completeness.

    Completeness is evaluated against the Account's records as they are now, not as they were when
    picked: a GSTIN later rejected, or an address no longer active, reads as missing again."""
    site_address = _usable_address(addresses, row.get("site_address_public_id"), WORK_ORDER_LINE_SITE_ADDRESS_TYPES)
    billing_address = _usable_address(
        addresses, row.get("billing_address_public_id"), WORK_ORDER_LINE_BILLING_ADDRESS_TYPES
    )
    billing_gstin = _usable_gstin(gstins, row.get("billing_gstin_public_id"))

    # The billing basis and contracted hours are billing terms since Slice 7D, and are reported there.
    missing_items: list[str] = []
    if site_address is None:
        missing_items.append(WORK_ORDER_LINE_DETAIL_MISSING_SITE_ADDRESS)
    if billing_gstin is None:
        missing_items.append(WORK_ORDER_LINE_DETAIL_MISSING_BILLING_GSTIN)
    if billing_address is None:
        missing_items.append(WORK_ORDER_LINE_DETAIL_MISSING_BILLING_ADDRESS)

    return WorkOrderLineDetailResponse(
        work_order_line_public_id=row["work_order_line_public_id"],
        line_number=row["line_number"],
        source_offer_line_public_id=row.get("source_offer_line_public_id"),
        detail_public_id=row.get("detail_public_id"),
        detail_version=row.get("detail_version"),
        site_address_public_id=row.get("site_address_public_id"),
        site_address=_detail_address(site_address),
        billing_gstin_public_id=row.get("billing_gstin_public_id"),
        billing_gstin=_detail_gstin(billing_gstin),
        billing_address_public_id=row.get("billing_address_public_id"),
        billing_address=_detail_address(billing_address),
        customer_line_reference=row.get("customer_line_reference"),
        operational_notes=row.get("operational_notes"),
        line_start_date=row.get("line_start_date"),
        line_end_date=row.get("line_end_date"),
        site_central_government=row.get("site_central_government"),
        is_complete=not missing_items,
        missing_items=missing_items,
        updated_by=row.get("updated_by"),
        updated_by_display_name=row.get("updated_by_display_name"),
        updated_at=row.get("updated_at"),
    )


def list_work_order_line_details(db: Session, work_order_public_id: UUID) -> list[WorkOrderLineDetailResponse]:
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    addresses, gstins = _account_reference_maps(db, work_order.account_public_id)
    return [
        _build_line_detail_response(row, addresses=addresses, gstins=gstins)
        for row in list_work_order_line_detail_rows(db, work_order_id=work_order_id)
    ]


def _normalize_line_detail_payload(
    payload: WorkOrderLineDetailUpdate,
    *,
    addresses: dict[str, Any],
    gstins: dict[str, Any],
    current: dict[str, Any] | None,
    contract_start: date | None,
    contract_end: date | None,
    contract_gaps: tuple[ContractGap, ...] = (),
) -> dict[str, Any]:
    """Validate against the Work Order's own Account and return storable values.

    A reference to another Account's record fails with the same message as an unknown one, so the
    response never confirms that a public id exists elsewhere."""
    values: dict[str, Any] = {
        "site_address_public_id": None,
        "billing_gstin_public_id": None,
        "billing_address_public_id": None,
    }

    if payload.site_address_public_id is not None:
        if _usable_address(addresses, payload.site_address_public_id, WORK_ORDER_LINE_SITE_ADDRESS_TYPES) is None:
            raise WorkOrderValidationError(
                "The site must be an active Site address on this Work Order's Account. If the site is not there yet, "
                "add it on the Account first, then pick it here."
            )
        values["site_address_public_id"] = str(payload.site_address_public_id)

    if payload.billing_gstin_public_id is not None:
        if _usable_gstin(gstins, payload.billing_gstin_public_id) is None:
            raise WorkOrderValidationError(
                "The billing GSTIN must be an active GST number on this Work Order's Account that has not been "
                "rejected as incorrect."
            )
        values["billing_gstin_public_id"] = str(payload.billing_gstin_public_id)

    if payload.billing_address_public_id is not None:
        if (
            _usable_address(addresses, payload.billing_address_public_id, WORK_ORDER_LINE_BILLING_ADDRESS_TYPES)
            is None
        ):
            raise WorkOrderValidationError(
                "The billing address must be an active Registered Office or Billing address on this Work Order's "
                "Account."
            )
        values["billing_address_public_id"] = str(payload.billing_address_public_id)

    values["customer_line_reference"] = _clean_optional(payload.customer_line_reference)
    values["operational_notes"] = _clean_optional(payload.operational_notes)
    values["line_start_date"], values["line_end_date"] = _normalize_line_dates(
        payload,
        current=current,
        contract_start=contract_start,
        contract_end=contract_end,
        contract_gaps=contract_gaps,
    )
    # 8A core: omitted keeps what is recorded, as the line's dates do (so a caller that predates the field
    # never erases an answer); sent as null, it clears.
    values["site_central_government"] = (
        payload.site_central_government
        if "site_central_government" in payload.model_fields_set
        else (current or {}).get("site_central_government")
    )
    return values


def _normalize_line_dates(
    payload: WorkOrderLineDetailUpdate,
    *,
    current: dict[str, Any] | None,
    contract_start: date | None,
    contract_end: date | None,
    contract_gaps: tuple[ContractGap, ...] = (),
) -> tuple[date | None, date | None]:
    """Slice 7D Part 3: a line's own dates must sit inside the contract period (owner decision 13).

    Blank means the line follows the Work Order, so a blank date is never checked and never missing.
    A date is refused only when the contract bound it breaks is actually recorded - the rule in
    `contract_period_rules.py` answers NOT_DETERMINED where a bound is unknown, and this never turns
    that into a refusal.

    **An omitted date field keeps what is recorded; an explicit null clears it.** These two fields
    alone depart from this route's whole-replacement shape, deliberately: they were added after the
    route existed, so a caller written against the earlier shape - the smoke-data harness's own
    `set_work_order_line_detail` among them - sends every field it knows about and none of these,
    and whole-replacement would silently erase dates nobody touched. Independent review found that
    (round 1, finding F-03). Clearing a date is still possible, by sending it as null.
    """
    given = payload.model_fields_set
    line_start = (
        payload.line_start_date if "line_start_date" in given else (current or {}).get("line_start_date")
    )
    line_end = (
        payload.line_end_date if "line_end_date" in given else (current or {}).get("line_end_date")
    )
    if line_start is not None and line_end is not None and line_end < line_start:
        raise WorkOrderValidationError(
            f"This line cannot end on {format_contract_date(line_end)}, "
            f"before it starts on {format_contract_date(line_start)}."
        )
    for value, subject in ((line_start, "This line starts on"), (line_end, "This line ends on")):
        if value is None:
            continue
        message = date_outside_contract_message(
            value,
            contract_start=contract_start,
            contract_end=contract_end,
            subject=subject,
            gaps=contract_gaps,
        )
        if message is not None:
            raise WorkOrderValidationError(message)
    return line_start, line_end


def save_work_order_line_detail(
    db: Session,
    *,
    work_order_public_id: UUID,
    line_public_id: UUID,
    payload: WorkOrderLineDetailUpdate,
    current_user_public_id: str | None,
) -> WorkOrderLineDetailActionResponse:
    event: dict[str, object] | None = None
    response: WorkOrderLineDetailActionResponse
    with rollback_on_error(db):
        # The Work Order lock serializes every save on its lines, including two first saves of the
        # same line; uq_wol_detail_work_order_line is the backstop.
        work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id, for_update=True)
        line_context = get_work_order_line_context(
            db, work_order_id=work_order_id, line_public_id=str(line_public_id)
        )
        if line_context is None:
            raise WorkOrderLineNotFoundError("Work Order line not found on this Work Order.")

        if work_order.work_order_status_code in WORK_ORDER_LINE_DETAIL_LOCKED_WORK_ORDER_STATUSES:
            raise WorkOrderValidationError(
                "This Work Order is closed. Its site and billing details can no longer be changed."
            )
        if work_order.account_public_id is None:
            raise WorkOrderValidationError(
                "This Work Order has no linked Account, so there are no site or billing records to pick from."
            )

        work_order_line_id = int(line_context["work_order_line_id"])
        current = get_work_order_line_detail_row(db, work_order_line_id=work_order_line_id)
        current_version = int(current["detail_version"]) if current else None
        if payload.expected_detail_version != current_version:
            raise WorkOrderLineDetailConflictError(
                "Someone else changed these details after you opened them. Reload to see their version."
            )

        addresses, gstins = _account_reference_maps(db, work_order.account_public_id)
        contract_start, contract_end = contract_bounds_for_work_order(db, work_order_id=work_order_id)
        values = _normalize_line_detail_payload(
            payload,
            addresses=addresses,
            gstins=gstins,
            current=current,
            contract_start=contract_start,
            contract_end=contract_end,
            contract_gaps=contract_gaps_for_work_order(db, work_order_id=work_order_id),
        )
        changed_fields = _changed_line_detail_fields(current, values)

        if current is not None and not changed_fields:
            # An identical save is not an edit: no version bump and no event (the Slice 9D defect
            # was an event that looked like an edit when nothing changed).
            response = _captured_line_detail_response(
                db, work_order_id=work_order_id, line_public_id=line_public_id, addresses=addresses, gstins=gstins, event=None
            )
            db.rollback()
        else:
            if current is None:
                insert_work_order_line_detail(
                    db,
                    public_id=str(uuid4()),
                    work_order_line_id=work_order_line_id,
                    values=values,
                    current_user_public_id=current_user_public_id,
                )
                event_name = WORK_ORDER_LINE_DETAIL_EVENT_RECORDED
                new_version = 1
                reason = "Site and billing details recorded for a Work Order line."
            else:
                updated = update_work_order_line_detail(
                    db,
                    work_order_line_id=work_order_line_id,
                    expected_detail_version=int(current_version),
                    values=values,
                    current_user_public_id=current_user_public_id,
                )
                if updated != 1:
                    raise WorkOrderLineDetailConflictError(
                        "Someone else changed these details after you opened them. Reload to see their version."
                    )
                event_name = WORK_ORDER_LINE_DETAIL_EVENT_UPDATED
                new_version = int(current_version) + 1
                reason = "Site and billing details changed for a Work Order line."

            # Public ids and codes only: never the GSTIN value or address text.
            event = _event_dict(
                record_business_event(
                    db,
                    event_name=event_name,
                    source_module=WORK_ORDER_MODULE_NAME,
                    record_type=WORK_ORDER_RECORD_TYPE,
                    record_public_id=str(work_order.public_id),
                    user_public_id=current_user_public_id,
                    reason=reason,
                    event_payload={
                        "work_order_line_public_id": str(line_public_id),
                        "detail_version": new_version,
                        "changed_fields": changed_fields,
                        "site_address_public_id": values["site_address_public_id"],
                        "billing_gstin_public_id": values["billing_gstin_public_id"],
                        "billing_address_public_id": values["billing_address_public_id"],
                        "line_start_date": (
                            values["line_start_date"].isoformat() if values["line_start_date"] else None
                        ),
                        "line_end_date": values["line_end_date"].isoformat() if values["line_end_date"] else None,
                        "site_central_government": values["site_central_government"],
                    },
                )
            )
            # 8A core: a requirement without an end of its own runs to its line's end.
            if "line_end_date" in changed_fields:
                _end_dates_changed(db, work_order_public_id=work_order.public_id, current_user_public_id=current_user_public_id)
            # Built while the Work Order lock is still held, so the returned detail is exactly the
            # version this save wrote - a later save cannot land between the commit and the read -
            # and nothing that can fail runs after the write is permanent.
            response = _captured_line_detail_response(
                db, work_order_id=work_order_id, line_public_id=line_public_id, addresses=addresses, gstins=gstins, event=event
            )
            db.commit()

    return response


def _captured_line_detail_response(
    db: Session,
    *,
    work_order_id: int,
    line_public_id: UUID,
    addresses: dict[str, Any],
    gstins: dict[str, Any],
    event: dict[str, object] | None,
) -> WorkOrderLineDetailActionResponse:
    """The save response, read inside the caller's still-open transaction."""
    rows = list_work_order_line_detail_rows(db, work_order_id=work_order_id)
    row = next(item for item in rows if str(item["work_order_line_public_id"]) == str(line_public_id))
    return WorkOrderLineDetailActionResponse(
        line_detail=_build_line_detail_response(row, addresses=addresses, gstins=gstins),
        event=event,
    )
