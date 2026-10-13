"""The customer's response to an offer and the outcome it records (Slices 6L and 6M.1)."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_ALLOWED_CUSTOMER_RESPONSE_CHANNELS,
    COMMERCIAL_OFFER_ALLOWED_CUSTOMER_RESPONSE_OUTCOMES,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ACCEPTED_AWARDED,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REJECTED_LOST,
    COMMERCIAL_OFFER_EVENT_CUSTOMER_RESPONSE_RECORDED,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
    COMMERCIAL_OFFER_STATUS_REJECTED,
    COMMERCIAL_OFFER_RECORD_TYPE,
)
from app.modules.commercial_offers.repository import (
    get_commercial_offer_context_by_public_id,
    get_revision_context_for_offer,
    insert_commercial_offer_customer_response,
    lock_commercial_offer_row,
    list_commercial_offer_customer_responses_for_offer,
    list_linked_work_order_contexts_for_offer,
    update_commercial_offer_by_public_id,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferCustomerResponseCreate,
    CommercialOfferCustomerResponseCreatedResponse,
    CommercialOfferCustomerResponseResponse,
)
from app.modules.events.service import record_business_event
from app.shared import business_time

from app.modules.commercial_offers.services.common import (
    CommercialOfferNotFoundError,
    CommercialOfferValidationError,
    _clean_optional,
    _ensure_account_traceability_for_lifecycle_action,
    _ensure_no_preparation_version,
    _event_dict,
    _normalize_code,
    _revision_evidence_context,
    _validate_currency,
    get_commercial_offer,
)


def list_commercial_offer_customer_responses(
    db: Session,
    public_id: UUID,
) -> list[CommercialOfferCustomerResponseResponse]:
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    return list_commercial_offer_customer_responses_for_offer(
        db,
        commercial_offer_id=int(commercial_offer_context["commercial_offer_id"]),
    )


def _normalize_customer_response_code(value: str, allowed: tuple[str, ...], label: str) -> str:
    normalized = _normalize_code(value, "")
    if normalized not in allowed:
        raise CommercialOfferValidationError(f"{label} must be one of: {', '.join(allowed)}.")
    return normalized


def create_commercial_offer_customer_response(
    db: Session,
    *,
    public_id: UUID,
    payload: CommercialOfferCustomerResponseCreate,
    current_user_public_id: str | None,
) -> CommercialOfferCustomerResponseCreatedResponse:
    # Lock the offer row before reading its status. This action reads offer_status_code and
    # then conditionally writes it, so without the lock two concurrent requests could both pass
    # the guard below and the later commit would win - allowing an ACCEPTED_AWARDED response to
    # reactivate an offer a concurrent REJECTED_LOST had just made final.
    if lock_commercial_offer_row(db, public_id=str(public_id)) is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    existing = get_commercial_offer(db, public_id)
    if existing.offer_status_code not in COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES:
        if existing.offer_status_code == COMMERCIAL_OFFER_STATUS_REJECTED:
            raise CommercialOfferValidationError(
                "This Commercial Offer was rejected and is final. A later award cannot be "
                "recorded against it. Record the outcome against the replacement Commercial "
                "Offer for this Opportunity instead."
            )
        raise CommercialOfferValidationError(
            "Customer response / award outcome may be recorded only after submission. "
            f"Current Commercial Offer status is {existing.offer_status_code}."
        )
    _ensure_no_preparation_version(db, existing)

    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])

    outcome = _normalize_customer_response_code(
        payload.response_outcome,
        COMMERCIAL_OFFER_ALLOWED_CUSTOMER_RESPONSE_OUTCOMES,
        "Customer response outcome",
    )
    channel = _normalize_customer_response_code(
        payload.response_channel,
        COMMERCIAL_OFFER_ALLOWED_CUSTOMER_RESPONSE_CHANNELS,
        "Customer response channel",
    )
    # An offer with a Work Order is not recorded lost (CS-04 part 1, owner 8 October 2026): nothing can cancel a Work
    # Order yet, so a rejected offer would own a live one. The handoff takes the same row lock, so neither can pass the
    # other's check.
    if outcome == COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REJECTED_LOST:
        work_orders = list_linked_work_order_contexts_for_offer(db, commercial_offer_id=commercial_offer_id)
        if work_orders:
            codes = ", ".join(sorted(str(item["work_order_code"] or item["public_id"]) for item in work_orders))
            raise CommercialOfferValidationError(
                f"This offer already has Work Order {codes}, so it cannot be recorded as lost or rejected. A Work "
                "Order cannot be cancelled yet."
            )
    linked_evidence = _revision_evidence_context(
        db,
        commercial_offer_id=commercial_offer_id,
        evidence_public_id=payload.linked_submission_evidence_public_id,
        field_label="Linked submission evidence",
    )
    linked_revision = None
    if payload.linked_revision_public_id is not None:
        linked_revision = get_revision_context_for_offer(
            db,
            commercial_offer_id=commercial_offer_id,
            public_id=str(payload.linked_revision_public_id),
        )
        if linked_revision is None:
            raise CommercialOfferValidationError(
                "Linked revision must identify an existing revision record for this Commercial Offer."
            )

    awarded_currency = _clean_optional(payload.awarded_currency_snapshot)
    if payload.awarded_amount_snapshot is not None:
        awarded_currency = _validate_currency(awarded_currency or "INR")
    elif awarded_currency is not None:
        awarded_currency = _validate_currency(awarded_currency)

    target_status = existing.offer_status_code
    if outcome == COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ACCEPTED_AWARDED:
        target_status = COMMERCIAL_OFFER_STATUS_ACCEPTED
    elif outcome == COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REJECTED_LOST:
        target_status = COMMERCIAL_OFFER_STATUS_REJECTED
    _ensure_account_traceability_for_lifecycle_action(
        commercial_offer=existing,
        target_status=target_status,
    )

    response_reference = _clean_optional(payload.response_reference)
    response_notes = _clean_optional(payload.customer_response_notes)
    values = {
        "response_outcome": outcome,
        "response_reference": response_reference,
        "response_received_at": payload.response_received_at,
        "response_channel": channel,
        "received_from": _clean_optional(payload.received_from),
        "awarded_amount_snapshot": payload.awarded_amount_snapshot,
        "awarded_currency_snapshot": awarded_currency,
        "awarded_version_snapshot": _clean_optional(payload.awarded_version_snapshot),
        "customer_po_or_wo_reference": _clean_optional(payload.customer_po_or_wo_reference),
        "customer_response_notes": response_notes,
        "linked_submission_evidence_id": int(linked_evidence["id"]) if linked_evidence else None,
        "linked_revision_id": int(linked_revision["id"]) if linked_revision else None,
        "created_by": current_user_public_id,
    }
    offer_update_values: dict[str, object] = {}
    if target_status != existing.offer_status_code:
        offer_update_values["offer_status_code"] = target_status
        # The day the response came, in India: the time arrives in UTC, so 01:00 in India is the day before in UTC.
        offer_update_values["outcome_date"] = business_time.india_date(payload.response_received_at)
        offer_update_values["outcome_remarks"] = response_notes or response_reference

    try:
        customer_response = insert_commercial_offer_customer_response(
            db,
            public_id=str(uuid4()),
            commercial_offer_id=commercial_offer_id,
            values=values,
        )
        commercial_offer = update_commercial_offer_by_public_id(
            db,
            public_id=str(public_id),
            values=offer_update_values,
        )
        status_changed = existing.offer_status_code != commercial_offer.offer_status_code
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_CUSTOMER_RESPONSE_RECORDED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            status_before=existing.offer_status_code,
            status_after=commercial_offer.offer_status_code,
            reason="Customer response / award outcome recorded after Commercial Offer submission.",
            event_payload={
                "commercial_offer_public_id": str(public_id),
                "customer_response_public_id": str(customer_response.public_id),
                "response_outcome": outcome,
                "response_reference": response_reference,
                "response_received_at": payload.response_received_at.isoformat(),
                "linked_submission_evidence_public_id": (
                    str(customer_response.linked_submission_evidence_public_id)
                    if customer_response.linked_submission_evidence_public_id
                    else None
                ),
                "linked_revision_public_id": (
                    str(customer_response.linked_revision_public_id)
                    if customer_response.linked_revision_public_id
                    else None
                ),
                "previous_offer_status_code": existing.offer_status_code,
                "new_offer_status_code": commercial_offer.offer_status_code,
                "status_changed": status_changed,
                "work_order_created": False,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return CommercialOfferCustomerResponseCreatedResponse(
        customer_response=customer_response,
        commercial_offer=commercial_offer,
        event=_event_dict(event),
    )
