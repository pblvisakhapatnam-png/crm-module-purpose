"""Supplementary Offers and Change Quotations raised against a Base Offer (Slice 6O.1)."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_ALLOWED_MODES,
    COMMERCIAL_OFFER_ALLOWED_TYPES,
    COMMERCIAL_OFFER_EVENT_RELATED_OFFER_CREATED,
    COMMERCIAL_OFFER_PURPOSE_BASE,
    COMMERCIAL_OFFER_PURPOSE_CHANGE_QUOTATION,
    COMMERCIAL_OFFER_PURPOSE_LABELS,
    COMMERCIAL_OFFER_RELATED_OFFER_ALLOWED_PURPOSES,
    COMMERCIAL_OFFER_RELATED_OFFER_BASE_ELIGIBLE_STATUSES,
    COMMERCIAL_OFFER_INITIAL_STATUS,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_RECORD_TYPE,
)
from app.modules.commercial_offers.repository import (
    get_base_offer_creation_context,
    get_commercial_offer_context_by_public_id,
    get_work_order_lineage_context,
    list_related_commercial_offers_for_base_offer,
    lock_commercial_offer_row,
    insert_commercial_offer,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferRelatedOfferCreate,
    CommercialOfferRelatedOfferCreatedResponse,
    CommercialOfferResponse,
)
from app.modules.events.service import record_business_event

from app.modules.commercial_offers.services.common import (
    CommercialOfferNotFoundError,
    CommercialOfferValidationError,
    _clean_optional,
    _event_dict,
    _normalize_code,
    _normalize_lower,
    _validate_currency,
    _validate_dates,
    _validate_offer_value,
    _validate_required_text,
)


def _validate_related_work_order(
    db: Session,
    *,
    base_offer_context: dict[str, object],
    work_order_public_id: UUID | None,
) -> dict[str, object] | None:
    if work_order_public_id is None:
        return None

    work_order_context = get_work_order_lineage_context(db, str(work_order_public_id))
    if work_order_context is None:
        raise CommercialOfferValidationError("Linked Work Order was not found.")

    if int(work_order_context["opportunity_id"]) != int(base_offer_context["opportunity_id"]):
        raise CommercialOfferValidationError(
            "Linked Work Order does not belong to the same Opportunity as the Base Commercial Offer."
        )

    base_business_party_id = base_offer_context.get("business_party_id") or base_offer_context.get(
        "opportunity_business_party_id"
    )
    work_order_business_party_id = work_order_context.get("business_party_id")
    if (
        base_business_party_id is not None
        and work_order_business_party_id is not None
        and int(base_business_party_id) != int(work_order_business_party_id)
    ):
        raise CommercialOfferValidationError(
            "Linked Work Order does not belong to the same Account as the Base Commercial Offer."
        )

    return work_order_context


def create_related_commercial_offer(
    db: Session,
    *,
    base_offer_public_id: UUID,
    payload: CommercialOfferRelatedOfferCreate,
    current_user_public_id: str | None,
) -> CommercialOfferRelatedOfferCreatedResponse:
    """Creates a Supplementary Offer or Change Quotation as a SEPARATE Commercial Offer
    series linked directly to its Base Offer. This is never a revision of the Base Offer:
    the Base Offer's own status, lines and lifecycle history are never touched here, and
    no Work Order or Work Order Amendment is ever created automatically."""
    # Status-dependent mutation: this reads the Base Offer's status, requires ACCEPTED, and then
    # inserts a related offer. ACCEPTED is *not* immutable - the Slice 6L customer-response route
    # writes the status directly and can move it to REJECTED - so the Base Offer is locked for
    # the transaction before it is read, or a concurrent rejection could land in between.
    if lock_commercial_offer_row(db, public_id=str(base_offer_public_id)) is None:
        raise CommercialOfferNotFoundError("Base Commercial Offer not found.")

    base_offer_context = get_base_offer_creation_context(db, str(base_offer_public_id))
    if base_offer_context is None:
        raise CommercialOfferNotFoundError("Base Commercial Offer not found.")

    if base_offer_context["offer_purpose"] != COMMERCIAL_OFFER_PURPOSE_BASE:
        raise CommercialOfferValidationError(
            "A Supplementary Offer or Change Quotation can be created only from a Base Offer, not from another "
            "related offer. Every related offer links directly to the Base Offer, so chains of related offers "
            "are not allowed."
        )

    if base_offer_context["offer_status_code"] not in COMMERCIAL_OFFER_RELATED_OFFER_BASE_ELIGIBLE_STATUSES:
        raise CommercialOfferValidationError(
            "The Base Commercial Offer must currently be Accepted / awarded before a Supplementary Offer or "
            f"Change Quotation can be created. Current status is {base_offer_context['offer_status_code']}."
        )

    if not base_offer_context.get("account_public_id"):
        raise CommercialOfferValidationError(
            "The Base Commercial Offer's Opportunity is not linked to an Account. Link it to an Account "
            "from the Opportunity page before creating a related offer."
        )

    offer_purpose = _normalize_code(payload.offer_purpose, "")
    if offer_purpose not in COMMERCIAL_OFFER_RELATED_OFFER_ALLOWED_PURPOSES:
        allowed = ", ".join(COMMERCIAL_OFFER_RELATED_OFFER_ALLOWED_PURPOSES)
        raise CommercialOfferValidationError(f"Related offer purpose must be one of: {allowed}.")

    customer_request_summary = _validate_required_text(payload.customer_request_summary, "Request / change summary")

    work_order_context = _validate_related_work_order(
        db,
        base_offer_context=base_offer_context,
        work_order_public_id=payload.related_work_order_public_id,
    )
    if offer_purpose == COMMERCIAL_OFFER_PURPOSE_CHANGE_QUOTATION and work_order_context is None:
        raise CommercialOfferValidationError("A Change Quotation must be linked to an existing Work Order.")

    offer_mode = _normalize_lower(payload.offer_mode, "plum_generated")
    if offer_mode not in COMMERCIAL_OFFER_ALLOWED_MODES:
        raise CommercialOfferValidationError(f"Commercial Offer mode is not allowed: {payload.offer_mode}")

    offer_type = _normalize_lower(payload.offer_type, "budgetary")
    if offer_type not in COMMERCIAL_OFFER_ALLOWED_TYPES:
        raise CommercialOfferValidationError(f"Commercial Offer type is not allowed: {payload.offer_type}")

    _validate_dates(payload.offer_date, payload.valid_until)

    purpose_label = COMMERCIAL_OFFER_PURPOSE_LABELS[offer_purpose]
    offer_title = _clean_optional(payload.offer_title) or f"{base_offer_context['offer_code']} {purpose_label}"

    values: dict[str, object | None] = {
        "opportunity_id": base_offer_context["opportunity_id"],
        "business_party_id": base_offer_context.get("business_party_id")
        or base_offer_context.get("opportunity_business_party_id"),
        "offer_title": offer_title,
        "offer_mode": offer_mode,
        "offer_type": offer_type,
        "offer_status_code": COMMERCIAL_OFFER_INITIAL_STATUS,
        "offer_value": _validate_offer_value(payload.offer_value),
        "currency_code": _validate_currency(payload.currency_code),
        "offer_date": payload.offer_date,
        "valid_until": payload.valid_until,
        "remarks": _clean_optional(payload.remarks),
        "offer_purpose": offer_purpose,
        "base_offer_id": int(base_offer_context["commercial_offer_id"]),
        "related_work_order_id": int(work_order_context["work_order_id"]) if work_order_context else None,
        "customer_request_reference": _clean_optional(payload.customer_request_reference),
        "customer_request_received_date": payload.customer_request_received_date,
        "customer_request_summary": customer_request_summary,
        "created_by": current_user_public_id,
    }

    related_offer_public_id = str(uuid4())
    try:
        commercial_offer = insert_commercial_offer(db, public_id=related_offer_public_id, values=values)
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_RELATED_OFFER_CREATED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(commercial_offer.public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=commercial_offer.offer_status_code,
            reason=(
                f"{purpose_label} created as a separate Commercial Offer series linked to its Base Offer. "
                "This is not a revision of the Base Offer and does not create a Work Order or Work Order "
                "Amendment automatically."
            ),
            event_payload={
                "offer_code": commercial_offer.offer_code,
                "offer_purpose": offer_purpose,
                "base_offer_public_id": str(base_offer_public_id),
                "base_offer_code": base_offer_context["offer_code"],
                "opportunity_public_id": str(commercial_offer.opportunity_public_id),
                "account_public_id": str(commercial_offer.account_public_id)
                if commercial_offer.account_public_id
                else None,
                "related_work_order_public_id": str(work_order_context["work_order_public_id"])
                if work_order_context
                else None,
                "customer_request_reference": commercial_offer.customer_request_reference,
                "has_customer_request_summary": bool(commercial_offer.customer_request_summary),
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return CommercialOfferRelatedOfferCreatedResponse(commercial_offer=commercial_offer, event=_event_dict(event))


def list_related_commercial_offers(db: Session, public_id: UUID) -> list[CommercialOfferResponse]:
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    return list_related_commercial_offers_for_base_offer(
        db,
        base_offer_id=int(commercial_offer_context["commercial_offer_id"]),
    )
