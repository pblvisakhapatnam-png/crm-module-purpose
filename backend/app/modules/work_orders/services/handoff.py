"""Creating a Work Order from an accepted Commercial Offer, and reading Work Orders (Slices 5A, 6A, 6O).

The handoff itself is frozen: docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md, with its dated
amendment of 8 October 2026 (CS-04 part 1).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import latest_response_not_accepted_reason
from app.modules.events.service import record_business_event
from app.modules.work_orders.contract import (
    WORK_ORDER_EVENT_CREATED,
    WORK_ORDER_CUSTOMER_REFERENCE_INDEX,
    WORK_ORDER_EVENT_CREATED_FROM_COMMERCIAL_OFFER,
    WORK_ORDER_HANDOFF_OFFER_PURPOSES,
    WORK_ORDER_HANDOFF_RESPONSE_OUTCOME,
    WORK_ORDER_INITIAL_STATUS,
    WORK_ORDER_LINE_QUANTITY_RULE,
    WORK_ORDER_MODULE_NAME,
    WORK_ORDER_RECORD_TYPE,
)
from app.modules.work_orders.repository import (
    find_work_order_with_customer_reference,
    get_commercial_offer_handoff_context,
    get_work_order_internal_id,
    get_work_order_line_reference_row,
    insert_work_order,
    insert_work_order_line,
    list_active_offer_line_contexts,
    list_offer_line_work_order_parts,
    list_recent_work_orders,
    list_related_commercial_offer_contexts,
    list_work_order_lines_by_public_id,
    lock_commercial_offer_row,
)
from app.modules.work_orders.schemas import (
    WorkOrderCreateFromCommercialOffer,
    WorkOrderCreatedResponse,
    WorkOrderHandoffLineQuantity,
    WorkOrderLineReference,
    WorkOrderLineResponse,
    WorkOrderRelatedOfferSummary,
    WorkOrderResponse,
)
from app.modules.work_orders.services.common import (
    WorkOrderCommercialOfferNotFoundError,
    WorkOrderHandoffConflictError,
    WorkOrderLineNotFoundError,
    WorkOrderNotFoundError,
    WorkOrderValidationError,
    _clean_optional,
    _event_dict,
)
from app.shared.transactions import rollback_on_error


def _select_offer_lines(
    *,
    available_lines: list[dict[str, object]],
    selected_offer_line_public_ids: list[UUID] | None,
) -> list[dict[str, object]]:
    if not available_lines:
        raise WorkOrderValidationError("At least one active Commercial Offer line is required to create a Work Order.")

    if not selected_offer_line_public_ids:
        return available_lines

    selected_ids = {str(public_id) for public_id in selected_offer_line_public_ids}
    available_by_id = {str(line["line_public_id"]): line for line in available_lines}
    missing_ids = sorted(selected_ids.difference(available_by_id.keys()))
    if missing_ids:
        raise WorkOrderValidationError(
            "Selected Commercial Offer line(s) were not found as active lines for this offer: " + ", ".join(missing_ids)
        )

    return [line for line in available_lines if str(line["line_public_id"]) in selected_ids]


def _check_offer_may_be_handed_off(offer_context: dict[str, object]) -> None:
    """Which accepted offers make a Work Order (CS-04 part 1). Runs after the account check, as before."""
    if offer_context["offer_purpose"] not in WORK_ORDER_HANDOFF_OFFER_PURPOSES:
        raise WorkOrderValidationError(
            "This is a Change Quotation. It changes work already on a Work Order, so it does not make a Work Order of "
            "its own: cite it on an amendment of that Work Order instead."
        )
    latest_outcome = offer_context.get("latest_customer_response_outcome")
    if latest_outcome is None:
        raise WorkOrderValidationError(
            "No customer acceptance or award is recorded for this offer. Record it first, then create the Work Order."
        )
    if latest_outcome != WORK_ORDER_HANDOFF_RESPONSE_OUTCOME:
        raise WorkOrderValidationError(latest_response_not_accepted_reason(str(latest_outcome)))


def _quantity_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _work_order_parts(
    db: Session,
    *,
    selected_lines: list[dict[str, object]],
    line_quantities: list[WorkOrderHandoffLineQuantity] | None,
    every_line_by_default: bool,
) -> list[tuple[dict[str, object], Decimal, Decimal | None]]:
    """Each selected offer line with the quantity this Work Order takes of it, and what that part is worth.

    An offer line's quantity goes onto Work Orders once, whole or in parts, never more in all (CS-04 part 1). A line
    asked for with nothing left, or for more than is left, refuses the whole request, naming the Work Orders that hold
    it. When no line was chosen, every active line is offered and a line with nothing left is passed over, so asking
    again with no choice once everything is on a Work Order is refused rather than repeated."""
    selected_by_id = {str(line["line_public_id"]): line for line in selected_lines}
    asked: dict[str, Decimal] = {}
    for item in line_quantities or []:
        line_id = str(item.offer_line_public_id)
        if line_id not in selected_by_id:
            raise WorkOrderValidationError(f"A quantity was given for an offer line that is not selected: {line_id}.")
        if line_id in asked:
            raise WorkOrderValidationError(f"A quantity was given twice for the same offer line: {line_id}.")
        asked[line_id] = item.quantity

    held: dict[int, list[dict[str, object]]] = {}
    for part in list_offer_line_work_order_parts(
        db, commercial_offer_line_ids=[int(line["commercial_offer_line_id"]) for line in selected_lines]
    ):
        held.setdefault(int(part["commercial_offer_line_id"]), []).append(part)

    parts: list[tuple[dict[str, object], Decimal, Decimal | None]] = []
    refusals: list[str] = []
    for line in selected_lines:
        line_id = str(line["line_public_id"])
        holdings = held.get(int(line["commercial_offer_line_id"]), [])
        offered = Decimal(line["quantity"])
        left = offered - sum((Decimal(part["quantity"]) for part in holdings), Decimal("0"))
        where = ", ".join(f"{part['work_order_code']} ({_quantity_text(Decimal(part['quantity']))})" for part in holdings)
        if left <= 0:
            if every_line_by_default and line_id not in asked:
                continue
            refusals.append(f"Line {line['line_number']} is already on a Work Order in full: {where}.")
            continue
        quantity = asked.get(line_id, left)
        if quantity > left:
            refusals.append(
                f"Line {line['line_number']} has {_quantity_text(left)} of {_quantity_text(offered)} left to hand off "
                f"(on a Work Order: {where}); {_quantity_text(quantity)} was asked."
            )
            continue
        parts.append((line, quantity, _part_amount(line, quantity, offered - left)))

    if refusals:
        raise WorkOrderHandoffConflictError(
            " ".join(refusals) + " An offer line's quantity goes onto Work Orders once, whole or in parts: open the "
            "Work Order named, or ask only for what is left."
        )
    if not parts:
        every = ", ".join(sorted({str(part["work_order_code"]) for holdings in held.values() for part in holdings}))
        raise WorkOrderHandoffConflictError(f"Every line of this offer is already on a Work Order in full: {every}.")
    return parts


def _part_amount(line: dict[str, object], quantity: Decimal, taken: Decimal) -> Decimal | None:
    """What this part of an offer line is worth: the line's amount up to the end of the part, less its amount up to the
    part's start, each the rate times the quantity so far, rounded to the paisa as the offer's own line is.

    However a line is split, and in whatever order, its parts then add up to the line's own amount exactly and none is
    below zero - rounding each part on its own could leave the parts a paisa off the line (CEX-001's allocation
    reconciles). A line taken whole keeps the offer's own amount."""
    offered = Decimal(line["quantity"])
    line_amount = line.get("line_amount")
    rate = line.get("rate_amount")
    if rate is None:
        return line_amount if taken == 0 and quantity == offered else None

    def worth_up_to(so_far: Decimal) -> Decimal:
        if so_far == 0:
            return Decimal("0")
        if so_far == offered and line_amount is not None:
            return Decimal(line_amount)
        return (Decimal(rate) * so_far).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return worth_up_to(taken + quantity) - worth_up_to(taken)


def _check_customer_reference(db: Session, *, commercial_offer_id: int, reference: str | None) -> str:
    """One customer order makes one Work Order (the owner, 8 October 2026): the customer's reference - their order
    number, or the Letter of Intent's - is required, and a reference already on a Work Order of this offer is refused,
    naming it. A repeated request, whole line or part, therefore makes no second Work Order; a second order of the
    same size carries its own number."""
    if reference is None:
        raise WorkOrderValidationError(
            "Enter the customer's Work Order reference - their order number, or the Letter of Intent's - to create the "
            "Work Order."
        )
    holder = find_work_order_with_customer_reference(db, commercial_offer_id=commercial_offer_id, reference=reference)
    if holder is not None:
        raise WorkOrderHandoffConflictError(
            f"Customer reference {reference} is already on {holder} for this offer. One customer order makes one Work "
            f"Order: open {holder}, or enter the reference of the new order."
        )
    return reference


def _violated(exc: IntegrityError) -> str | None:
    return getattr(getattr(exc.orig, "diag", None), "constraint_name", None)


def _offer_version_reference(offer_context: dict[str, object]) -> str:
    """The offer as a person names it: its code, with "v2", "v3" for a later version (Slice 9F; version 1 is the code
    alone, as in a quotation's reference)."""
    code = str(offer_context.get("offer_code") or "Commercial Offer")
    version = int(offer_context.get("version_number") or 1)
    return code if version == 1 else f"{code} v{version}"


def _handed_off_line(line: WorkOrderLineResponse) -> dict[str, object]:
    """One Work Order line as `CommercialOfferConvertedToWorkOrder` records it: the offer line it came from, the line
    it became, and how much of what (CS-04 part 2, item c)."""
    return {
        "offer_line_public_id": str(line.source_offer_line_public_id) if line.source_offer_line_public_id else None,
        "work_order_line_public_id": str(line.public_id),
        "line_number": line.line_number,
        "quantity": str(line.quantity),
        "uom": line.uom,
        "currency_code": line.currency_code,
        "line_amount": str(line.line_amount) if line.line_amount is not None else None,
    }


def create_work_order_from_commercial_offer(
    db: Session,
    *,
    payload: WorkOrderCreateFromCommercialOffer,
    current_user_public_id: str | None,
) -> WorkOrderCreatedResponse:
    commercial_offer_public_id = str(payload.commercial_offer_public_id)
    # Lock the source offer before reading its status: this reads ACCEPTED and then inserts a
    # Work Order shell, so a concurrent customer response committing REJECTED in between would
    # otherwise produce a shell from an offer that is no longer accepted.
    lock_commercial_offer_row(db, commercial_offer_public_id=commercial_offer_public_id)
    offer_context = get_commercial_offer_handoff_context(db, commercial_offer_public_id)
    if offer_context is None:
        raise WorkOrderCommercialOfferNotFoundError("Commercial Offer not found.")

    offer_status = str(offer_context["offer_status_code"])
    if offer_status != "ACCEPTED":
        raise WorkOrderValidationError("A Work Order can be created only from an accepted Commercial Offer.")

    if not offer_context.get("account_public_id"):
        raise WorkOrderValidationError(
            "A Work Order cannot be created until the offer's Opportunity is linked to an Account. A basic "
            "Account (Qualified Prospect) is enough: link or create one from the Opportunity page, then try again."
        )

    _check_offer_may_be_handed_off(offer_context)
    reference = _check_customer_reference(
        db,
        commercial_offer_id=int(offer_context["commercial_offer_id"]),
        reference=_clean_optional(payload.customer_wo_reference),
    )

    available_lines = list_active_offer_line_contexts(
        db,
        commercial_offer_id=int(offer_context["commercial_offer_id"]),
    )
    selected_lines = _select_offer_lines(
        available_lines=available_lines,
        selected_offer_line_public_ids=payload.selected_offer_line_public_ids,
    )
    parts = _work_order_parts(
        db,
        selected_lines=selected_lines,
        line_quantities=payload.selected_offer_line_quantities,
        every_line_by_default=not payload.selected_offer_line_public_ids,
    )
    try:
        return _insert_work_order_shell(
            db,
            payload=payload,
            offer_context=offer_context,
            parts=parts,
            current_user_public_id=current_user_public_id,
        )
    except IntegrityError as exc:
        # A database rule refused what the checks above passed: another Work Order took the line, or the reference,
        # after them, which the offer lock prevents for every writer that takes it. Name what holds it now, as the
        # checks would.
        if _violated(exc) == WORK_ORDER_CUSTOMER_REFERENCE_INDEX:
            _check_customer_reference(db, commercial_offer_id=int(offer_context["commercial_offer_id"]), reference=reference)
        elif _violated(exc) != WORK_ORDER_LINE_QUANTITY_RULE:
            raise
        _work_order_parts(
            db,
            selected_lines=selected_lines,
            line_quantities=payload.selected_offer_line_quantities,
            every_line_by_default=not payload.selected_offer_line_public_ids,
        )
        raise WorkOrderHandoffConflictError(
            "Another Work Order took this offer's lines at the same time. Reload the page to see what is left."
        ) from exc


def _insert_work_order_shell(
    db: Session,
    *,
    payload: WorkOrderCreateFromCommercialOffer,
    offer_context: dict[str, object],
    parts: list[tuple[dict[str, object], Decimal, Decimal | None]],
    current_user_public_id: str | None,
) -> WorkOrderCreatedResponse:
    commercial_offer_public_id = str(payload.commercial_offer_public_id)
    offer_status = str(offer_context["offer_status_code"])

    work_order_public_id = str(uuid4())
    work_order_title = f"Work Order from {_offer_version_reference(offer_context)}"
    values = {
        "commercial_offer_id": offer_context["commercial_offer_id"],
        "opportunity_id": offer_context["opportunity_id"],
        "business_party_id": offer_context.get("business_party_id"),
        "work_order_title": work_order_title,
        "work_order_status_code": WORK_ORDER_INITIAL_STATUS,
        "customer_wo_reference": _clean_optional(payload.customer_wo_reference),
        "received_date": payload.received_date,
        "source_offer_status_code": offer_status,
        "remarks": _clean_optional(payload.remarks),
        "created_by": current_user_public_id,
    }

    with rollback_on_error(db):
        work_order = insert_work_order(db, public_id=work_order_public_id, values=values)
        work_order_id = get_work_order_internal_id(db, work_order_public_id)
        if work_order_id is None:
            raise RuntimeError("Inserted Work Order internal id could not be reloaded.")

        for line, quantity, amount in parts:
            insert_work_order_line(
                db,
                public_id=str(uuid4()),
                work_order_id=work_order_id,
                values={
                    "commercial_offer_line_id": line["commercial_offer_line_id"],
                    "line_number": line["line_number"],
                    "line_status_code": "HANDOFF_CREATED",
                    "scope_description": line["scope_description"],
                    "equipment_service_category": line.get("equipment_service_category"),
                    "quantity": quantity,
                    "uom": line["uom"],
                    "rate_amount": line.get("rate_amount"),
                    "currency_code": line["currency_code"],
                    "line_amount": amount,
                    "remarks": line.get("remarks"),
                },
            )

        lines = list_work_order_lines_by_public_id(db, work_order_public_id) or []
        events = [
            record_business_event(
                db,
                event_name=WORK_ORDER_EVENT_CREATED,
                source_module=WORK_ORDER_MODULE_NAME,
                record_type=WORK_ORDER_RECORD_TYPE,
                record_public_id=str(work_order.public_id),
                user_public_id=current_user_public_id,
                status_before=None,
                status_after=work_order.work_order_status_code,
                reason="Work Order created from the accepted Commercial Offer.",
                event_payload={
                    "work_order_code": work_order.work_order_code,
                    "commercial_offer_public_id": str(work_order.commercial_offer_public_id),
                    "commercial_offer_code": work_order.commercial_offer_code,
                    "commercial_offer_version_number": work_order.commercial_offer_version_number,
                    "opportunity_public_id": str(work_order.opportunity_public_id),
                    "account_public_id": str(work_order.account_public_id) if work_order.account_public_id else None,
                    "line_count": len(lines),
                    "deferred_controls": [
                        "Customer Master finance approval",
                        "WO release/posting control",
                        "equipment allocation",
                        "crew allocation",
                        "log sheets",
                        "billing",
                    ],
                },
            ),
            record_business_event(
                db,
                event_name=WORK_ORDER_EVENT_CREATED_FROM_COMMERCIAL_OFFER,
                source_module=WORK_ORDER_MODULE_NAME,
                record_type="commercial_offer",
                record_public_id=commercial_offer_public_id,
                user_public_id=current_user_public_id,
                status_before=offer_status,
                status_after=offer_status,
                reason="Accepted Commercial Offer handed over to Ops as a Work Order.",
                event_payload={
                    "work_order_public_id": str(work_order.public_id),
                    "work_order_code": work_order.work_order_code,
                    "commercial_offer_version_number": work_order.commercial_offer_version_number,
                    "line_count": len(lines),
                    # What moved from the offer onto the Work Order, line by line: the record credit exposure's
                    # Potential-to-Firm transfer (CEX-001) and later readers count from (CS-04 part 2, item c).
                    "lines": [_handed_off_line(line) for line in lines],
                },
            ),
        ]
        db.commit()

    return WorkOrderCreatedResponse(
        work_order=work_order,
        lines=lines,
        events=[_event_dict(event) for event in events],
    )


def list_work_orders(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    commercial_offer_public_id: UUID | None = None,
) -> list[WorkOrderResponse]:
    return list_recent_work_orders(
        db,
        limit=limit,
        offset=offset,
        commercial_offer_public_id=str(commercial_offer_public_id) if commercial_offer_public_id else None,
    )


def list_work_order_lines(db: Session, public_id: UUID) -> list[WorkOrderLineResponse]:
    lines = list_work_order_lines_by_public_id(db, str(public_id))
    if lines is None:
        raise WorkOrderNotFoundError("Work Order not found.")
    return lines


def get_work_order_line_reference(db: Session, line_public_id: UUID) -> WorkOrderLineReference:
    """One line and the Work Order it belongs to, from the line's public id alone (WRR-001).

    Read-only, for another module that holds a line's public id and must not read Work Order tables
    itself - a Resource Requirement is created for a line."""
    row = get_work_order_line_reference_row(db, line_public_id=str(line_public_id))
    if row is None:
        raise WorkOrderLineNotFoundError("Work Order line not found.")
    return WorkOrderLineReference(**row)


def list_work_order_related_offers(db: Session, public_id: UUID) -> list[WorkOrderRelatedOfferSummary]:
    """Slice 6O.1 read-only traceability: Supplementary Offers / Change Quotations linked to
    this Work Order. Does not imply the Work Order has been amended, released or posted."""
    work_order_id = get_work_order_internal_id(db, str(public_id))
    if work_order_id is None:
        raise WorkOrderNotFoundError("Work Order not found.")
    contexts = list_related_commercial_offer_contexts(db, work_order_id)
    return [WorkOrderRelatedOfferSummary(**context) for context in contexts]
