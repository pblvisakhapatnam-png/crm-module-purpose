"""An offer's lines: its scope, quantities and rates (Slice 4E)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_EVENT_LINE_ADDED,
    COMMERCIAL_OFFER_EVENT_LINE_UPDATED,
    COMMERCIAL_OFFER_LINE_INITIAL_STATUS,
    COMMERCIAL_OFFER_ALLOWED_LINE_STATUSES,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_RECORD_TYPE,
)
from app.modules.commercial_offers.repository import (
    get_commercial_offer_context_by_public_id,
    get_commercial_offer_line_context,
    get_next_commercial_offer_line_number,
    insert_commercial_offer_line,
    list_commercial_offer_lines_for_offer,
    update_commercial_offer_line_by_public_id,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferLineCreate,
    CommercialOfferLineCreatedResponse,
    CommercialOfferLineResponse,
    CommercialOfferLineUpdate,
    CommercialOfferLineUpdatedResponse,
)
from app.modules.events.service import record_business_event

from app.modules.commercial_offers.services.common import (
    CommercialOfferConflictError,
    CommercialOfferLineNotFoundError,
    CommercialOfferNotFoundError,
    CommercialOfferValidationError,
    _clean_optional,
    _event_dict,
    _lock_offer_for_content_change,
    _normalize_code,
    _validate_currency,
    _validate_required_text,
)


_LINE_CONFLICT_MESSAGE = (
    "Someone else changed this Commercial Offer line after you opened it, so your change was not saved. "
    "Reload the page to see their version, then make your change again."
)


def _commercial_offer_line_fields_set(payload: CommercialOfferLineUpdate) -> set[str]:
    model_fields_set = getattr(payload, "model_fields_set", None)
    if model_fields_set is not None:
        return set(model_fields_set)
    return set(getattr(payload, "__fields_set__", set()))


def _validate_positive_decimal(value: Decimal, field_label: str) -> Decimal:
    if value <= Decimal("0"):
        raise CommercialOfferValidationError(f"{field_label} must be greater than zero.")
    return value


def _validate_non_negative_optional_decimal(value: Decimal | None, field_label: str) -> Decimal | None:
    if value is not None and value < Decimal("0"):
        raise CommercialOfferValidationError(f"{field_label} cannot be negative.")
    return value


def _calculate_line_amount(quantity: Decimal | None, rate_amount: Decimal | None) -> Decimal | None:
    if quantity is None or rate_amount is None:
        return None
    return quantity * rate_amount


def _normalize_line_status(value: str | None) -> str:
    status_code = _normalize_code(value, COMMERCIAL_OFFER_LINE_INITIAL_STATUS)
    if status_code not in COMMERCIAL_OFFER_ALLOWED_LINE_STATUSES:
        raise CommercialOfferValidationError(f"Commercial Offer line status is not allowed: {status_code}")
    return status_code


def _normalize_line_create_payload(
    db: Session,
    *,
    payload: CommercialOfferLineCreate,
    commercial_offer_id: int,
    current_user_public_id: str | None,
) -> dict[str, object | None]:
    quantity = _validate_positive_decimal(payload.quantity, "Quantity")
    rate_amount = _validate_non_negative_optional_decimal(payload.rate_amount, "Rate amount")
    uom = _validate_required_text(payload.uom, "UOM")
    scope_description = _validate_required_text(payload.scope_description, "Scope / service description")
    line_number = payload.line_number or get_next_commercial_offer_line_number(db, commercial_offer_id=commercial_offer_id)

    return {
        "line_number": line_number,
        "line_status_code": COMMERCIAL_OFFER_LINE_INITIAL_STATUS,
        "scope_description": scope_description,
        "equipment_service_category": _clean_optional(payload.equipment_service_category),
        "quantity": quantity,
        "uom": uom,
        "rate_amount": rate_amount,
        "currency_code": _validate_currency(payload.currency_code),
        "line_amount": _calculate_line_amount(quantity, rate_amount),
        "remarks": _clean_optional(payload.remarks),
        "created_by": current_user_public_id,
    }


def _normalize_line_update_payload(
    *,
    payload: CommercialOfferLineUpdate,
    existing_line: dict[str, object],
) -> dict[str, object | None]:
    fields_set = _commercial_offer_line_fields_set(payload)
    values: dict[str, object | None] = {}

    if "line_number" in fields_set:
        if payload.line_number is None or payload.line_number < 1:
            raise CommercialOfferValidationError("Line number must be greater than zero.")
        values["line_number"] = payload.line_number

    if "line_status_code" in fields_set:
        values["line_status_code"] = _normalize_line_status(payload.line_status_code)

    if "scope_description" in fields_set:
        values["scope_description"] = _validate_required_text(payload.scope_description, "Scope / service description")

    if "equipment_service_category" in fields_set:
        values["equipment_service_category"] = _clean_optional(payload.equipment_service_category)

    if "quantity" in fields_set:
        if payload.quantity is None:
            raise CommercialOfferValidationError("Quantity is required when it is updated.")
        values["quantity"] = _validate_positive_decimal(payload.quantity, "Quantity")

    if "uom" in fields_set:
        values["uom"] = _validate_required_text(payload.uom, "UOM")

    if "rate_amount" in fields_set:
        values["rate_amount"] = _validate_non_negative_optional_decimal(payload.rate_amount, "Rate amount")

    if "currency_code" in fields_set:
        values["currency_code"] = _validate_currency(payload.currency_code)

    if "remarks" in fields_set:
        values["remarks"] = _clean_optional(payload.remarks)

    if not values:
        raise CommercialOfferValidationError("At least one Commercial Offer line field must be provided for update.")

    # existing_line is the line as locked for this write (CS-05a), so a field this save leaves out comes from the row
    # being written, never from an earlier read another save has since changed.
    prospective_quantity = values.get("quantity", existing_line.get("quantity"))
    prospective_rate = values.get("rate_amount", existing_line.get("rate_amount"))
    values["line_amount"] = _calculate_line_amount(
        prospective_quantity if isinstance(prospective_quantity, Decimal) else Decimal(str(prospective_quantity)),
        prospective_rate if prospective_rate is None or isinstance(prospective_rate, Decimal) else Decimal(str(prospective_rate)),
    )

    return values


def list_commercial_offer_lines(
    db: Session,
    public_id: UUID,
) -> list[CommercialOfferLineResponse]:
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    return list_commercial_offer_lines_for_offer(
        db,
        commercial_offer_id=int(commercial_offer_context["commercial_offer_id"]),
    )


def create_commercial_offer_line(
    db: Session,
    *,
    public_id: UUID,
    payload: CommercialOfferLineCreate,
    current_user_public_id: str | None,
) -> CommercialOfferLineCreatedResponse:
    commercial_offer_context = _lock_offer_for_content_change(db, public_id)

    values = _normalize_line_create_payload(
        db,
        payload=payload,
        commercial_offer_id=int(commercial_offer_context["commercial_offer_id"]),
        current_user_public_id=current_user_public_id,
    )
    line_public_id = str(uuid4())

    try:
        offer_line = insert_commercial_offer_line(
            db,
            public_id=line_public_id,
            commercial_offer_id=int(commercial_offer_context["commercial_offer_id"]),
            values=values,
        )
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_LINE_ADDED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=str(commercial_offer_context["offer_status_code"]),
            reason="Commercial Offer line added.",
            event_payload={
                "offer_code": commercial_offer_context.get("offer_code"),
                "offer_line_public_id": str(offer_line.public_id),
                "line_number": offer_line.line_number,
                "line_status_code": offer_line.line_status_code,
                "scope_description": offer_line.scope_description,
                "equipment_service_category": offer_line.equipment_service_category,
                "quantity": str(offer_line.quantity),
                "uom": offer_line.uom,
                "rate_amount": str(offer_line.rate_amount) if offer_line.rate_amount is not None else None,
                "currency_code": offer_line.currency_code,
                "line_amount": str(offer_line.line_amount) if offer_line.line_amount is not None else None,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return CommercialOfferLineCreatedResponse(offer_line=offer_line, event=_event_dict(event))


def update_commercial_offer_line(
    db: Session,
    *,
    public_id: UUID,
    line_public_id: UUID,
    payload: CommercialOfferLineUpdate,
    current_user_public_id: str | None,
) -> CommercialOfferLineUpdatedResponse:
    commercial_offer_context = _lock_offer_for_content_change(db, public_id)

    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])
    # CS-05a (TB-1 TB1-303): the line is read locked, compared with the version the screen loaded, and its amount
    # computed from it, so a save from a form opened before someone else's is refused rather than written over theirs.
    existing_line = get_commercial_offer_line_context(
        db,
        commercial_offer_id=commercial_offer_id,
        line_public_id=str(line_public_id),
        for_update=True,
    )
    if existing_line is None:
        raise CommercialOfferLineNotFoundError("Commercial Offer line not found.")
    if payload.expected_row_version != int(existing_line["row_version"]):
        raise CommercialOfferConflictError(_LINE_CONFLICT_MESSAGE)

    values = _normalize_line_update_payload(payload=payload, existing_line=existing_line)

    try:
        offer_line = update_commercial_offer_line_by_public_id(
            db,
            commercial_offer_id=commercial_offer_id,
            line_public_id=str(line_public_id),
            values=values,
            expected_row_version=payload.expected_row_version,
        )
        if offer_line is None:
            raise CommercialOfferConflictError(_LINE_CONFLICT_MESSAGE)

        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_LINE_UPDATED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            status_before=str(existing_line.get("line_status_code")),
            status_after=offer_line.line_status_code,
            reason="Commercial Offer line updated.",
            event_payload={
                "offer_code": commercial_offer_context.get("offer_code"),
                "offer_line_public_id": str(offer_line.public_id),
                "updated_fields": sorted(values.keys()),
                "row_version": offer_line.row_version,
                "line_number": offer_line.line_number,
                "line_status_code": offer_line.line_status_code,
                "scope_description": offer_line.scope_description,
                "equipment_service_category": offer_line.equipment_service_category,
                "quantity": str(offer_line.quantity),
                "uom": offer_line.uom,
                "rate_amount": str(offer_line.rate_amount) if offer_line.rate_amount is not None else None,
                "currency_code": offer_line.currency_code,
                "line_amount": str(offer_line.line_amount) if offer_line.line_amount is not None else None,
            },
        )
        db.commit()
    except CommercialOfferLineNotFoundError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return CommercialOfferLineUpdatedResponse(offer_line=offer_line, event=_event_dict(event))
