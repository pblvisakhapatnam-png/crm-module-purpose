"""Slice 6O.2 Work Order Amendment intake foundation.

A Work Order Amendment is an intake/review record only. Nothing in this module ever writes to
crm_work_order or crm_work_order_line; every function below either reads that data (for
validation/snapshot purposes) or writes exclusively to the crm_work_order_amendment /
crm_work_order_amendment_line tables.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.events.service import record_business_event
from app.modules.work_orders.contract import (
    WORK_ORDER_AMENDMENT_ALLOWED_STATUSES,
    WORK_ORDER_AMENDMENT_ALLOWED_TRANSITIONS,
    WORK_ORDER_AMENDMENT_ALLOWED_TYPES,
    WORK_ORDER_AMENDMENT_COMMERCIAL_BASIS_REQUIRED_TYPES,
    WORK_ORDER_AMENDMENT_DECISION_EVENTS,
    WORK_ORDER_AMENDMENT_DECISION_REASON_REQUIRED_STATUSES,
    WORK_ORDER_AMENDMENT_EDITABLE_STATUSES,
    WORK_ORDER_AMENDMENT_EVENT_LINE_ADDED,
    WORK_ORDER_AMENDMENT_EVENT_LINE_REMOVED,
    WORK_ORDER_AMENDMENT_EVENT_LINE_UPDATED,
    WORK_ORDER_AMENDMENT_EVENT_RECORDED,
    WORK_ORDER_AMENDMENT_EVENT_UPDATED,
    WORK_ORDER_AMENDMENT_INITIAL_STATUS,
    WORK_ORDER_AMENDMENT_LINE_ACTIONS_REQUIRING_SOURCE_LINE,
    WORK_ORDER_AMENDMENT_LINE_ACTION_ADD,
    WORK_ORDER_AMENDMENT_LINE_ALLOWED_ACTIONS,
    WORK_ORDER_AMENDMENT_SOURCE_OFFER_ACCEPTED_STATUS,
    WORK_ORDER_AMENDMENT_SOURCE_OFFER_ELIGIBLE_PURPOSES,
    WORK_ORDER_AMENDMENT_STATUS_CANCELLED,
    WORK_ORDER_AMENDMENT_STATUS_RECEIVED,
    WORK_ORDER_AMENDMENT_STATUS_REJECTED,
    WORK_ORDER_AMENDMENT_STATUS_UNDER_REVIEW,
    WORK_ORDER_AMENDMENT_STATUS_VALIDATED,
    WORK_ORDER_AMENDMENT_TERMINAL_STATUSES,
    WORK_ORDER_AMENDMENT_TYPE_ADMINISTRATIVE,
    WORK_ORDER_MODULE_NAME,
    WORK_ORDER_RECORD_TYPE,
)
from app.modules.work_orders.repository import (
    apply_work_order_amendment_decision,
    delete_amendment_line,
    get_amendment_internal_id,
    get_amendment_line_for_amendment,
    get_next_amendment_line_number,
    get_next_amendment_sequence_no,
    get_related_offer_context_for_amendment,
    get_work_order_amendment_by_reference,
    get_work_order_amendment_for_work_order,
    get_work_order_line_context,
    get_work_order_lineage_ids,
    insert_work_order_amendment,
    insert_work_order_amendment_line,
    list_amendment_lines_for_amendment,
    list_work_order_amendments_for_work_order,
    lock_commercial_offer_row,
    lock_work_order_amendment_row,
    update_amendment_line,
    update_work_order_amendment_header,
)
from app.modules.work_orders.schemas import (
    WorkOrderAmendmentActionResponse,
    WorkOrderAmendmentCreate,
    WorkOrderAmendmentDecision,
    WorkOrderAmendmentLineActionResponse,
    WorkOrderAmendmentLineCreate,
    WorkOrderAmendmentLineResponse,
    WorkOrderAmendmentLineUpdate,
    WorkOrderAmendmentReadinessResponse,
    WorkOrderAmendmentResponse,
    WorkOrderAmendmentUpdate,
)
from app.modules.work_orders.services.common import (
    WorkOrderAmendmentLineNotFoundError,
    WorkOrderAmendmentNotFoundError,
    WorkOrderValidationError,
    _clean_optional,
    _event_dict,
    _get_work_order_and_id,
)
from app.shared.currency import operating_currency
from app.shared.transactions import rollback_on_error


def _normalize_code(value: str | None, default: str) -> str:
    return (value or default).strip().upper()


def _validate_required_text(value: str | None, field_label: str) -> str:
    cleaned = _clean_optional(value)
    if not cleaned:
        raise WorkOrderValidationError(f"{field_label} is required.")
    return cleaned


def _validate_non_negative_optional_decimal(value: Decimal | None, field_label: str) -> Decimal | None:
    if value is not None and value < Decimal("0"):
        raise WorkOrderValidationError(f"{field_label} cannot be negative.")
    return value


def _validate_currency(value: str | None) -> str:
    try:
        return operating_currency(value)
    except ValueError as exc:
        raise WorkOrderValidationError(str(exc)) from exc


def _fields_set(payload: object) -> set[str]:
    model_fields_set = getattr(payload, "model_fields_set", None)
    if model_fields_set is not None:
        return set(model_fields_set)
    return set(getattr(payload, "__fields_set__", set()))


def _calculate_amendment_line_amount(quantity: Decimal | None, rate_amount: Decimal | None) -> Decimal | None:
    if quantity is None or rate_amount is None:
        return None
    return quantity * rate_amount


def _get_amendment_and_id(
    db: Session,
    *,
    work_order_id: int,
    amendment_public_id: UUID,
    for_update: bool = False,
) -> tuple[WorkOrderAmendmentResponse, int]:
    """Fetch one amendment, optionally locking it first.

    `for_update=True` is mandatory for every mutating path. Taking the lock inside this shared
    read means a caller cannot read amendment status and *then* remember to lock: the lock is
    part of the read, or it is absent for a read-only caller that does not need it.
    """
    if for_update and lock_work_order_amendment_row(
        db, work_order_id=work_order_id, public_id=str(amendment_public_id)
    ) is None:
        raise WorkOrderAmendmentNotFoundError("Work Order Amendment not found.")

    amendment = get_work_order_amendment_for_work_order(
        db, work_order_id=work_order_id, public_id=str(amendment_public_id)
    )
    if amendment is None:
        raise WorkOrderAmendmentNotFoundError("Work Order Amendment not found.")
    amendment_id = get_amendment_internal_id(db, work_order_id=work_order_id, public_id=str(amendment_public_id))
    if amendment_id is None:
        raise WorkOrderAmendmentNotFoundError("Work Order Amendment not found.")
    return amendment, amendment_id


def _validate_related_offer_for_amendment(
    db: Session,
    *,
    work_order_id: int,
    related_commercial_offer_public_id: UUID | None,
) -> dict[str, Any] | None:
    """Structural lineage check only - status-agnostic. A Draft or Submitted related offer
    may be cited as a pending commercial basis; only the VALIDATED transition (see
    _compute_amendment_readiness) requires it to currently be Accepted, checked live."""
    if related_commercial_offer_public_id is None:
        return None

    offer_context = get_related_offer_context_for_amendment(db, str(related_commercial_offer_public_id))
    if offer_context is None:
        raise WorkOrderValidationError("Related Commercial Offer (commercial basis) was not found.")

    if offer_context["offer_purpose"] not in WORK_ORDER_AMENDMENT_SOURCE_OFFER_ELIGIBLE_PURPOSES:
        raise WorkOrderValidationError(
            "The commercial basis for a Work Order Amendment must be a Supplementary Offer or Change Quotation "
            "linked to this Work Order, not a Base Offer."
        )

    if offer_context.get("related_work_order_id") != work_order_id:
        raise WorkOrderValidationError(
            "The selected Commercial Offer is not linked to this Work Order and cannot be used as its commercial "
            "basis."
        )

    work_order_lineage = get_work_order_lineage_ids(db, work_order_id=work_order_id)
    if work_order_lineage is not None:
        offer_opportunity_id = offer_context.get("opportunity_id")
        if offer_opportunity_id is not None and offer_opportunity_id != work_order_lineage.get("opportunity_id"):
            raise WorkOrderValidationError(
                "The selected Commercial Offer does not belong to the same Opportunity as this Work Order."
            )
        offer_business_party_id = offer_context.get("business_party_id")
        work_order_business_party_id = work_order_lineage.get("business_party_id")
        if (
            offer_business_party_id is not None
            and work_order_business_party_id is not None
            and offer_business_party_id != work_order_business_party_id
        ):
            raise WorkOrderValidationError(
                "The selected Commercial Offer does not belong to the same Account as this Work Order."
            )

    return offer_context


def _compute_amendment_readiness(
    db: Session,
    *,
    amendment: WorkOrderAmendmentResponse,
    amendment_id: int,
) -> WorkOrderAmendmentReadinessResponse:
    is_editable = amendment.amendment_status_code in WORK_ORDER_AMENDMENT_EDITABLE_STATUSES
    commercial_basis_required = amendment.amendment_type_code in WORK_ORDER_AMENDMENT_COMMERCIAL_BASIS_REQUIRED_TYPES
    has_required_header_info = bool(_clean_optional(amendment.amendment_reason)) and (
        amendment.amendment_type_code == WORK_ORDER_AMENDMENT_TYPE_ADMINISTRATIVE
        or bool(_clean_optional(amendment.commercial_change_summary))
    )

    related_offer_linked = amendment.related_commercial_offer_public_id is not None
    related_offer_accepted = False
    if related_offer_linked:
        # Re-fetch live status rather than trusting the amendment's own snapshot join,
        # since the related offer's lifecycle can advance after this amendment's intake.
        offer_context = get_related_offer_context_for_amendment(db, str(amendment.related_commercial_offer_public_id))
        related_offer_accepted = bool(
            offer_context
            and offer_context.get("offer_status_code") == WORK_ORDER_AMENDMENT_SOURCE_OFFER_ACCEPTED_STATUS
        )

    has_required_change_detail = True
    if amendment.amendment_type_code != WORK_ORDER_AMENDMENT_TYPE_ADMINISTRATIVE:
        # This foundation has no separate non-line commercial-term model (e.g. payment
        # terms) on the Work Order, so the spec's documented fallback does not apply here:
        # Commercial/Mixed amendments require at least one amendment line to validate.
        lines = list_amendment_lines_for_amendment(db, amendment_id=amendment_id)
        has_required_change_detail = len(lines) > 0

    blocking_reasons: list[str] = []
    can_move_to_under_review = amendment.amendment_status_code == WORK_ORDER_AMENDMENT_STATUS_RECEIVED
    can_move_to_validated = False

    if amendment.amendment_status_code == WORK_ORDER_AMENDMENT_STATUS_UNDER_REVIEW:
        if not has_required_header_info:
            blocking_reasons.append(
                "Required header information is incomplete (amendment reason, and commercial change summary for "
                "Commercial/Mixed amendments)."
            )
        if commercial_basis_required and not related_offer_linked:
            blocking_reasons.append(
                "A Commercial or Mixed amendment requires a linked Supplementary Offer / Change Quotation as its "
                "commercial basis before it can be validated."
            )
        elif commercial_basis_required and not related_offer_accepted:
            blocking_reasons.append(
                "The linked Supplementary Offer / Change Quotation must be Accepted through its own lifecycle "
                "before this amendment can be validated."
            )
        if not has_required_change_detail:
            blocking_reasons.append(
                "A Commercial or Mixed amendment requires at least one amendment line describing the proposed "
                "change before it can be validated."
            )
        can_move_to_validated = not blocking_reasons
    elif amendment.amendment_status_code == WORK_ORDER_AMENDMENT_STATUS_RECEIVED:
        blocking_reasons.append("Move this amendment to Under Review before it can be validated.")
    else:
        blocking_reasons.append(
            f"Amendment status {amendment.amendment_status_code} is terminal; no further transition is available."
        )

    if amendment.amendment_status_code in WORK_ORDER_AMENDMENT_TERMINAL_STATUSES:
        advisory_message = (
            f"This amendment is {amendment.amendment_status_code} and is read-only. It has not been applied to "
            "the Work Order."
        )
    elif can_move_to_validated:
        advisory_message = (
            "This amendment is ready to be validated for future downstream processing. Validating it does not "
            "apply it to the Work Order."
        )
    else:
        advisory_message = "This amendment is not yet ready to be validated. See blocking reasons."

    return WorkOrderAmendmentReadinessResponse(
        amendment_public_id=amendment.public_id,
        amendment_type_code=amendment.amendment_type_code,
        amendment_status_code=amendment.amendment_status_code,
        is_editable=is_editable,
        has_required_header_info=has_required_header_info,
        commercial_basis_required=commercial_basis_required,
        related_offer_linked=related_offer_linked,
        related_offer_accepted=related_offer_accepted,
        has_required_change_detail=has_required_change_detail,
        can_move_to_under_review=can_move_to_under_review,
        can_move_to_validated=can_move_to_validated,
        blocking_reasons=blocking_reasons,
        advisory_message=advisory_message,
        applied_to_work_order=False,
    )


def create_work_order_amendment(
    db: Session,
    *,
    work_order_public_id: UUID,
    payload: WorkOrderAmendmentCreate,
    current_user_public_id: str | None,
) -> WorkOrderAmendmentActionResponse:
    # Locked: the sequence number and the customer-reference uniqueness check below are both
    # read-then-insert over this Work Order's existing amendments. See lock_work_order_row.
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id, for_update=True)

    amendment_type = _normalize_code(payload.amendment_type_code, "")
    if amendment_type not in WORK_ORDER_AMENDMENT_ALLOWED_TYPES:
        allowed = ", ".join(WORK_ORDER_AMENDMENT_ALLOWED_TYPES)
        raise WorkOrderValidationError(f"Amendment type must be one of: {allowed}.")

    amendment_reason = _validate_required_text(payload.amendment_reason, "Amendment reason / summary")

    commercial_change_summary = _clean_optional(payload.commercial_change_summary)
    if amendment_type != WORK_ORDER_AMENDMENT_TYPE_ADMINISTRATIVE and not commercial_change_summary:
        raise WorkOrderValidationError("Commercial change summary is required for Commercial and Mixed amendments.")

    if payload.received_date is None:
        raise WorkOrderValidationError("Received date is required.")

    customer_amendment_reference = _clean_optional(payload.customer_amendment_reference)
    if customer_amendment_reference:
        existing = get_work_order_amendment_by_reference(
            db, work_order_id=work_order_id, customer_amendment_reference=customer_amendment_reference
        )
        if existing is not None:
            raise WorkOrderValidationError(
                f"Customer amendment reference '{customer_amendment_reference}' is already used for this Work "
                "Order."
            )

    related_offer_context = _validate_related_offer_for_amendment(
        db,
        work_order_id=work_order_id,
        related_commercial_offer_public_id=payload.related_commercial_offer_public_id,
    )

    amendment_sequence_no = get_next_amendment_sequence_no(db, work_order_id=work_order_id)
    values: dict[str, Any] = {
        "amendment_sequence_no": amendment_sequence_no,
        "amendment_type_code": amendment_type,
        "amendment_status_code": WORK_ORDER_AMENDMENT_INITIAL_STATUS,
        "customer_amendment_reference": customer_amendment_reference,
        "customer_amendment_date": payload.customer_amendment_date,
        "received_date": payload.received_date,
        "effective_date": payload.effective_date,
        "amendment_reason": amendment_reason,
        "administrative_change_summary": _clean_optional(payload.administrative_change_summary),
        "commercial_change_summary": commercial_change_summary,
        "related_commercial_offer_id": int(related_offer_context["commercial_offer_id"])
        if related_offer_context
        else None,
        "customer_document_reference": _clean_optional(payload.customer_document_reference),
        "remarks": _clean_optional(payload.remarks),
        "created_by": current_user_public_id,
    }

    amendment_public_id = str(uuid4())
    with rollback_on_error(db):
        amendment = insert_work_order_amendment(
            db, public_id=amendment_public_id, work_order_id=work_order_id, values=values
        )
        event = record_business_event(
            db,
            event_name=WORK_ORDER_AMENDMENT_EVENT_RECORDED,
            source_module=WORK_ORDER_MODULE_NAME,
            record_type=WORK_ORDER_RECORD_TYPE,
            record_public_id=str(work_order.public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=amendment.amendment_status_code,
            reason=(
                "Work Order Amendment intake recorded. This is an intake/review record only; it is not applied "
                "to the Work Order and does not change any Work Order or Work Order line."
            ),
            event_payload={
                "amendment_public_id": amendment_public_id,
                "amendment_sequence_no": amendment_sequence_no,
                "amendment_type_code": amendment_type,
                "related_commercial_offer_public_id": (
                    str(related_offer_context["offer_public_id"]) if related_offer_context else None
                ),
                "applied_to_work_order": False,
            },
        )
        db.commit()

    return WorkOrderAmendmentActionResponse(amendment=amendment, event=_event_dict(event))


def get_work_order_amendment(
    db: Session,
    *,
    work_order_public_id: UUID,
    amendment_public_id: UUID,
) -> WorkOrderAmendmentResponse:
    _, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    amendment, _ = _get_amendment_and_id(db, work_order_id=work_order_id, amendment_public_id=amendment_public_id)
    return amendment


def list_work_order_amendments(db: Session, *, work_order_public_id: UUID) -> list[WorkOrderAmendmentResponse]:
    _, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    return list_work_order_amendments_for_work_order(db, work_order_id=work_order_id)


def get_work_order_amendment_readiness(
    db: Session,
    *,
    work_order_public_id: UUID,
    amendment_public_id: UUID,
) -> WorkOrderAmendmentReadinessResponse:
    _, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    amendment, amendment_id = _get_amendment_and_id(
        db, work_order_id=work_order_id, amendment_public_id=amendment_public_id
    )
    return _compute_amendment_readiness(db, amendment=amendment, amendment_id=amendment_id)


def update_work_order_amendment(
    db: Session,
    *,
    work_order_public_id: UUID,
    amendment_public_id: UUID,
    payload: WorkOrderAmendmentUpdate,
    current_user_public_id: str | None,
) -> WorkOrderAmendmentActionResponse:
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    amendment, _ = _get_amendment_and_id(db, work_order_id=work_order_id, amendment_public_id=amendment_public_id, for_update=True)

    if amendment.amendment_status_code not in WORK_ORDER_AMENDMENT_EDITABLE_STATUSES:
        raise WorkOrderValidationError(
            f"This amendment is {amendment.amendment_status_code} and is read-only. Generic edit cannot bypass "
            "the amendment status transition rules."
        )

    fields_set = _fields_set(payload)
    values: dict[str, Any] = {}

    if "customer_amendment_reference" in fields_set:
        new_reference = _clean_optional(payload.customer_amendment_reference)
        if new_reference and new_reference != amendment.customer_amendment_reference:
            existing = get_work_order_amendment_by_reference(
                db, work_order_id=work_order_id, customer_amendment_reference=new_reference
            )
            if existing is not None and str(existing.public_id) != str(amendment_public_id):
                raise WorkOrderValidationError(
                    f"Customer amendment reference '{new_reference}' is already used for this Work Order."
                )
        values["customer_amendment_reference"] = new_reference

    if "customer_amendment_date" in fields_set:
        values["customer_amendment_date"] = payload.customer_amendment_date

    if "received_date" in fields_set:
        if payload.received_date is None:
            raise WorkOrderValidationError("Received date is required.")
        values["received_date"] = payload.received_date

    if "effective_date" in fields_set:
        values["effective_date"] = payload.effective_date

    if "amendment_reason" in fields_set:
        values["amendment_reason"] = _validate_required_text(payload.amendment_reason, "Amendment reason / summary")

    if "administrative_change_summary" in fields_set:
        values["administrative_change_summary"] = _clean_optional(payload.administrative_change_summary)

    commercial_summary_provided = "commercial_change_summary" in fields_set
    new_commercial_change_summary = (
        _clean_optional(payload.commercial_change_summary)
        if commercial_summary_provided
        else amendment.commercial_change_summary
    )
    if commercial_summary_provided:
        values["commercial_change_summary"] = new_commercial_change_summary
    if amendment.amendment_type_code != WORK_ORDER_AMENDMENT_TYPE_ADMINISTRATIVE and not new_commercial_change_summary:
        raise WorkOrderValidationError("Commercial change summary is required for Commercial and Mixed amendments.")

    if "related_commercial_offer_public_id" in fields_set:
        if payload.related_commercial_offer_public_id is None:
            values["related_commercial_offer_id"] = None
        else:
            related_offer_context = _validate_related_offer_for_amendment(
                db,
                work_order_id=work_order_id,
                related_commercial_offer_public_id=payload.related_commercial_offer_public_id,
            )
            values["related_commercial_offer_id"] = (
                int(related_offer_context["commercial_offer_id"]) if related_offer_context else None
            )

    if "customer_document_reference" in fields_set:
        values["customer_document_reference"] = _clean_optional(payload.customer_document_reference)

    if "remarks" in fields_set:
        values["remarks"] = _clean_optional(payload.remarks)

    with rollback_on_error(db):
        updated = update_work_order_amendment_header(
            db, work_order_id=work_order_id, public_id=str(amendment_public_id), values=values
        )
        if updated is None:
            raise WorkOrderAmendmentNotFoundError("Work Order Amendment not found.")
        event = record_business_event(
            db,
            event_name=WORK_ORDER_AMENDMENT_EVENT_UPDATED,
            source_module=WORK_ORDER_MODULE_NAME,
            record_type=WORK_ORDER_RECORD_TYPE,
            record_public_id=str(work_order.public_id),
            user_public_id=current_user_public_id,
            status_before=amendment.amendment_status_code,
            status_after=updated.amendment_status_code,
            reason="Work Order Amendment header updated.",
            event_payload={
                "amendment_public_id": str(amendment_public_id),
                "changed_fields": sorted(values.keys()),
                "applied_to_work_order": False,
            },
        )
        db.commit()

    return WorkOrderAmendmentActionResponse(amendment=updated, event=_event_dict(event))


def decide_work_order_amendment(
    db: Session,
    *,
    work_order_public_id: UUID,
    amendment_public_id: UUID,
    payload: WorkOrderAmendmentDecision,
    current_user_public_id: str | None,
) -> WorkOrderAmendmentActionResponse:
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    amendment, amendment_id = _get_amendment_and_id(
        db, work_order_id=work_order_id, amendment_public_id=amendment_public_id, for_update=True
    )

    target_status = _normalize_code(payload.target_status_code, "")
    if target_status not in WORK_ORDER_AMENDMENT_ALLOWED_STATUSES:
        raise WorkOrderValidationError(f"Amendment status is not allowed: {payload.target_status_code}")

    allowed_targets = WORK_ORDER_AMENDMENT_ALLOWED_TRANSITIONS.get(amendment.amendment_status_code, ())
    if target_status not in allowed_targets:
        allowed_text = ", ".join(allowed_targets) if allowed_targets else "none (terminal status)"
        raise WorkOrderValidationError(
            f"Amendment cannot move from {amendment.amendment_status_code} to {target_status}. Allowed next "
            f"status(es): {allowed_text}."
        )

    reason = _clean_optional(payload.reason)
    if target_status in WORK_ORDER_AMENDMENT_DECISION_REASON_REQUIRED_STATUSES and not reason:
        raise WorkOrderValidationError(f"A reason is required to move this amendment to {target_status}.")

    if target_status == WORK_ORDER_AMENDMENT_STATUS_VALIDATED:
        # Fourth status-dependent mutation. Validation requires the cited related Commercial
        # Offer to be currently ACCEPTED and then commits VALIDATED, so the offer is locked for
        # the transaction first - otherwise a concurrent customer response can reject it between
        # the readiness read and this commit, and the amendment validates against a rejected
        # commercial basis.
        if amendment.related_commercial_offer_public_id:
            lock_commercial_offer_row(
                db, commercial_offer_public_id=str(amendment.related_commercial_offer_public_id)
            )
        readiness = _compute_amendment_readiness(db, amendment=amendment, amendment_id=amendment_id)
        if not readiness.can_move_to_validated:
            raise WorkOrderValidationError(
                "Amendment cannot be validated yet: " + " ".join(readiness.blocking_reasons)
            )

    notes = _clean_optional(payload.notes) or reason
    timestamp_column = {
        WORK_ORDER_AMENDMENT_STATUS_UNDER_REVIEW: "reviewed_at",
        WORK_ORDER_AMENDMENT_STATUS_VALIDATED: "validated_at",
        WORK_ORDER_AMENDMENT_STATUS_REJECTED: "rejected_at",
        WORK_ORDER_AMENDMENT_STATUS_CANCELLED: "cancelled_at",
    }[target_status]

    with rollback_on_error(db):
        updated = apply_work_order_amendment_decision(
            db,
            work_order_id=work_order_id,
            public_id=str(amendment_public_id),
            expected_status=amendment.amendment_status_code,
            new_status=target_status,
            decided_by=current_user_public_id,
            decision_notes=notes,
            timestamp_column=timestamp_column,
        )
        if updated is None:
            raise WorkOrderValidationError(
                "Amendment could not be updated; its status may have changed concurrently. Reload and retry."
            )

        event_name = WORK_ORDER_AMENDMENT_DECISION_EVENTS[target_status]
        event = record_business_event(
            db,
            event_name=event_name,
            source_module=WORK_ORDER_MODULE_NAME,
            record_type=WORK_ORDER_RECORD_TYPE,
            record_public_id=str(work_order.public_id),
            user_public_id=current_user_public_id,
            status_before=amendment.amendment_status_code,
            status_after=target_status,
            reason=reason or "Work Order Amendment decision recorded.",
            event_payload={
                "amendment_public_id": str(amendment_public_id),
                "amendment_sequence_no": amendment.amendment_sequence_no,
                "amendment_type_code": amendment.amendment_type_code,
                "previous_status": amendment.amendment_status_code,
                "new_status": target_status,
                "notes": notes,
                "applied_to_work_order": False,
            },
        )
        db.commit()

    return WorkOrderAmendmentActionResponse(amendment=updated, event=_event_dict(event))


def list_work_order_amendment_lines(
    db: Session,
    *,
    work_order_public_id: UUID,
    amendment_public_id: UUID,
) -> list[WorkOrderAmendmentLineResponse]:
    _, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    _, amendment_id = _get_amendment_and_id(db, work_order_id=work_order_id, amendment_public_id=amendment_public_id)
    return list_amendment_lines_for_amendment(db, amendment_id=amendment_id)


def create_work_order_amendment_line(
    db: Session,
    *,
    work_order_public_id: UUID,
    amendment_public_id: UUID,
    payload: WorkOrderAmendmentLineCreate,
    current_user_public_id: str | None,
) -> WorkOrderAmendmentLineActionResponse:
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    amendment, amendment_id = _get_amendment_and_id(
        db, work_order_id=work_order_id, amendment_public_id=amendment_public_id, for_update=True
    )

    if amendment.amendment_status_code not in WORK_ORDER_AMENDMENT_EDITABLE_STATUSES:
        raise WorkOrderValidationError(
            f"Amendment lines cannot be changed while the amendment status is {amendment.amendment_status_code}."
        )

    action_code = _normalize_code(payload.action_code, "")
    if action_code not in WORK_ORDER_AMENDMENT_LINE_ALLOWED_ACTIONS:
        allowed = ", ".join(WORK_ORDER_AMENDMENT_LINE_ALLOWED_ACTIONS)
        raise WorkOrderValidationError(f"Amendment line action must be one of: {allowed}.")

    requires_source = action_code in WORK_ORDER_AMENDMENT_LINE_ACTIONS_REQUIRING_SOURCE_LINE
    if requires_source and payload.source_work_order_line_public_id is None:
        raise WorkOrderValidationError(f"{action_code} requires a source Work Order line.")
    if not requires_source and payload.source_work_order_line_public_id is not None:
        raise WorkOrderValidationError("ADD_LINE must not reference an existing Work Order line.")

    source_line_context: dict[str, Any] | None = None
    if requires_source:
        source_line_context = get_work_order_line_context(
            db, work_order_id=work_order_id, line_public_id=str(payload.source_work_order_line_public_id)
        )
        if source_line_context is None:
            raise WorkOrderValidationError("Source Work Order line was not found for this Work Order.")

    change_summary = _clean_optional(payload.change_summary)
    if requires_source and not change_summary:
        raise WorkOrderValidationError(f"A change summary is required for {action_code}.")

    proposed_scope_description = _clean_optional(payload.proposed_scope_description)
    if action_code == WORK_ORDER_AMENDMENT_LINE_ACTION_ADD and not proposed_scope_description:
        raise WorkOrderValidationError("A proposed description / scope is required for ADD_LINE.")

    proposed_quantity = _validate_non_negative_optional_decimal(payload.proposed_quantity, "Proposed quantity")
    proposed_rate_amount = _validate_non_negative_optional_decimal(payload.proposed_rate_amount, "Proposed rate amount")
    proposed_amount = _calculate_amendment_line_amount(proposed_quantity, proposed_rate_amount)
    proposed_currency_code = _clean_optional(payload.proposed_currency_code)
    if proposed_currency_code is not None:
        proposed_currency_code = _validate_currency(proposed_currency_code)

    line_number = get_next_amendment_line_number(db, amendment_id=amendment_id)
    values: dict[str, Any] = {
        "line_number": line_number,
        "action_code": action_code,
        "source_work_order_line_id": source_line_context["work_order_line_id"] if source_line_context else None,
        "change_summary": change_summary,
        "proposed_scope_description": proposed_scope_description,
        "proposed_equipment_service_category": _clean_optional(payload.proposed_equipment_service_category),
        "proposed_quantity": proposed_quantity,
        "proposed_uom": _clean_optional(payload.proposed_uom),
        "proposed_rate_amount": proposed_rate_amount,
        "proposed_currency_code": proposed_currency_code,
        "proposed_amount": proposed_amount,
        "original_scope_description": source_line_context["scope_description"] if source_line_context else None,
        "original_equipment_service_category": (
            source_line_context.get("equipment_service_category") if source_line_context else None
        ),
        "original_quantity": source_line_context["quantity"] if source_line_context else None,
        "original_uom": source_line_context["uom"] if source_line_context else None,
        "original_rate_amount": source_line_context.get("rate_amount") if source_line_context else None,
        "original_currency_code": source_line_context["currency_code"] if source_line_context else None,
        "original_amount": source_line_context.get("line_amount") if source_line_context else None,
        "original_source_offer_line_public_id": (
            str(source_line_context["source_offer_line_public_id"])
            if source_line_context and source_line_context.get("source_offer_line_public_id")
            else None
        ),
        "created_by": current_user_public_id,
    }

    amendment_line_public_id = str(uuid4())
    with rollback_on_error(db):
        amendment_line = insert_work_order_amendment_line(
            db, public_id=amendment_line_public_id, amendment_id=amendment_id, values=values
        )
        event = record_business_event(
            db,
            event_name=WORK_ORDER_AMENDMENT_EVENT_LINE_ADDED,
            source_module=WORK_ORDER_MODULE_NAME,
            record_type=WORK_ORDER_RECORD_TYPE,
            record_public_id=str(work_order.public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=None,
            reason=f"Work Order Amendment line ({action_code}) recorded as a proposal only; no Work Order line was created or changed.",
            event_payload={
                "amendment_public_id": str(amendment_public_id),
                "amendment_line_public_id": amendment_line_public_id,
                "action_code": action_code,
                "source_work_order_line_public_id": (
                    str(payload.source_work_order_line_public_id)
                    if payload.source_work_order_line_public_id
                    else None
                ),
                "applied_to_work_order": False,
            },
        )
        db.commit()

    return WorkOrderAmendmentLineActionResponse(amendment_line=amendment_line, event=_event_dict(event))


def update_work_order_amendment_line(
    db: Session,
    *,
    work_order_public_id: UUID,
    amendment_public_id: UUID,
    line_public_id: UUID,
    payload: WorkOrderAmendmentLineUpdate,
    current_user_public_id: str | None,
) -> WorkOrderAmendmentLineActionResponse:
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    amendment, amendment_id = _get_amendment_and_id(
        db, work_order_id=work_order_id, amendment_public_id=amendment_public_id, for_update=True
    )

    if amendment.amendment_status_code not in WORK_ORDER_AMENDMENT_EDITABLE_STATUSES:
        raise WorkOrderValidationError(
            f"Amendment lines cannot be changed while the amendment status is {amendment.amendment_status_code}."
        )

    existing_line = get_amendment_line_for_amendment(db, amendment_id=amendment_id, public_id=str(line_public_id))
    if existing_line is None:
        raise WorkOrderAmendmentLineNotFoundError("Work Order Amendment line not found.")

    fields_set = _fields_set(payload)
    values: dict[str, Any] = {}

    if "change_summary" in fields_set:
        change_summary = _clean_optional(payload.change_summary)
        if existing_line.action_code in WORK_ORDER_AMENDMENT_LINE_ACTIONS_REQUIRING_SOURCE_LINE and not change_summary:
            raise WorkOrderValidationError(f"A change summary is required for {existing_line.action_code}.")
        values["change_summary"] = change_summary

    if "proposed_scope_description" in fields_set:
        new_description = _clean_optional(payload.proposed_scope_description)
        if existing_line.action_code == WORK_ORDER_AMENDMENT_LINE_ACTION_ADD and not new_description:
            raise WorkOrderValidationError("A proposed description / scope is required for ADD_LINE.")
        values["proposed_scope_description"] = new_description

    if "proposed_equipment_service_category" in fields_set:
        values["proposed_equipment_service_category"] = _clean_optional(payload.proposed_equipment_service_category)

    quantity_provided = "proposed_quantity" in fields_set
    rate_provided = "proposed_rate_amount" in fields_set
    if quantity_provided:
        values["proposed_quantity"] = _validate_non_negative_optional_decimal(
            payload.proposed_quantity, "Proposed quantity"
        )
    if rate_provided:
        values["proposed_rate_amount"] = _validate_non_negative_optional_decimal(
            payload.proposed_rate_amount, "Proposed rate amount"
        )
    if quantity_provided or rate_provided:
        quantity = values.get("proposed_quantity", existing_line.proposed_quantity)
        rate = values.get("proposed_rate_amount", existing_line.proposed_rate_amount)
        values["proposed_amount"] = _calculate_amendment_line_amount(quantity, rate)

    if "proposed_uom" in fields_set:
        values["proposed_uom"] = _clean_optional(payload.proposed_uom)

    if "proposed_currency_code" in fields_set:
        currency = _clean_optional(payload.proposed_currency_code)
        values["proposed_currency_code"] = _validate_currency(currency) if currency is not None else None

    with rollback_on_error(db):
        updated_line = update_amendment_line(
            db, amendment_id=amendment_id, public_id=str(line_public_id), values=values
        )
        if updated_line is None:
            raise WorkOrderAmendmentLineNotFoundError("Work Order Amendment line not found.")
        event = record_business_event(
            db,
            event_name=WORK_ORDER_AMENDMENT_EVENT_LINE_UPDATED,
            source_module=WORK_ORDER_MODULE_NAME,
            record_type=WORK_ORDER_RECORD_TYPE,
            record_public_id=str(work_order.public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=None,
            reason="Work Order Amendment line proposal updated; no Work Order line was created or changed.",
            event_payload={
                "amendment_public_id": str(amendment_public_id),
                "amendment_line_public_id": str(line_public_id),
                "applied_to_work_order": False,
            },
        )
        db.commit()

    return WorkOrderAmendmentLineActionResponse(amendment_line=updated_line, event=_event_dict(event))


def delete_work_order_amendment_line(
    db: Session,
    *,
    work_order_public_id: UUID,
    amendment_public_id: UUID,
    line_public_id: UUID,
    current_user_public_id: str | None,
) -> dict[str, Any]:
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    amendment, amendment_id = _get_amendment_and_id(
        db, work_order_id=work_order_id, amendment_public_id=amendment_public_id, for_update=True
    )

    if amendment.amendment_status_code not in WORK_ORDER_AMENDMENT_EDITABLE_STATUSES:
        raise WorkOrderValidationError(
            f"Amendment lines cannot be changed while the amendment status is {amendment.amendment_status_code}."
        )

    existing_line = get_amendment_line_for_amendment(db, amendment_id=amendment_id, public_id=str(line_public_id))
    if existing_line is None:
        raise WorkOrderAmendmentLineNotFoundError("Work Order Amendment line not found.")

    with rollback_on_error(db):
        deleted = delete_amendment_line(db, amendment_id=amendment_id, public_id=str(line_public_id))
        if not deleted:
            raise WorkOrderAmendmentLineNotFoundError("Work Order Amendment line not found.")
        event = record_business_event(
            db,
            event_name=WORK_ORDER_AMENDMENT_EVENT_LINE_REMOVED,
            source_module=WORK_ORDER_MODULE_NAME,
            record_type=WORK_ORDER_RECORD_TYPE,
            record_public_id=str(work_order.public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=None,
            reason="Work Order Amendment line proposal removed; no Work Order line was created or changed.",
            event_payload={
                "amendment_public_id": str(amendment_public_id),
                "amendment_line_public_id": str(line_public_id),
                "applied_to_work_order": False,
            },
        )
        db.commit()

    return _event_dict(event)
