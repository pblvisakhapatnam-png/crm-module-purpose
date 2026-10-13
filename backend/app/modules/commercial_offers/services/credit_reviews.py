"""The manual credit/exposure readiness review recorded on an offer (Slice 6I.2)."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_ALLOWED_CREDIT_REVIEW_STATUSES,
    COMMERCIAL_OFFER_EVENT_CREDIT_REVIEW_RECORDED,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVED,
    COMMERCIAL_OFFER_CURRENT_CREDIT_REVIEW_INDEX,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_RECORD_TYPE,
)
from app.modules.commercial_offers.repository import (
    get_commercial_offer_context_by_public_id,
    insert_commercial_offer_credit_review,
    list_commercial_offer_credit_reviews_for_offer,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferCreditReviewCreate,
    CommercialOfferCreditReviewCreatedResponse,
    CommercialOfferCreditReviewResponse,
)
from app.modules.events.service import record_business_event

from app.modules.commercial_offers.services.common import (
    CommercialOfferConflictError,
    CommercialOfferNotFoundError,
    CommercialOfferValidationError,
    _clean_optional,
    _event_dict,
    _lock_offer_for_content_change,
    _normalize_code,
    _refuse_duplicate,
    get_commercial_offer,
)


def _normalize_credit_review_status(value: str | None) -> str:
    review_status = _normalize_code(value, "")
    if review_status not in COMMERCIAL_OFFER_ALLOWED_CREDIT_REVIEW_STATUSES:
        allowed = ", ".join(COMMERCIAL_OFFER_ALLOWED_CREDIT_REVIEW_STATUSES)
        raise CommercialOfferValidationError(f"Credit review status must be one of: {allowed}.")
    return review_status


def _normalize_credit_review_payload(
    *,
    payload: CommercialOfferCreditReviewCreate,
    current_user_public_id: str | None,
) -> dict[str, object | None]:
    review_status = _normalize_credit_review_status(payload.review_status)
    review_reference = _clean_optional(payload.review_reference)
    if review_status == COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVED and not review_reference:
        raise CommercialOfferValidationError("Review reference is required for Approved With Reference status.")
    return {
        "review_status": review_status,
        "review_basis": _clean_optional(payload.review_basis),
        "review_reference": review_reference,
        "reviewed_at": payload.reviewed_at,
        "reviewed_by": current_user_public_id,
        "approved_amount_snapshot": payload.approved_amount_snapshot,
        "credit_days_snapshot": payload.credit_days_snapshot,
        "exposure_note": _clean_optional(payload.exposure_note),
        "created_by": current_user_public_id,
    }


def list_commercial_offer_credit_reviews(
    db: Session,
    public_id: UUID,
) -> list[CommercialOfferCreditReviewResponse]:
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    return list_commercial_offer_credit_reviews_for_offer(
        db,
        commercial_offer_id=int(commercial_offer_context["commercial_offer_id"]),
    )


def create_commercial_offer_credit_review(
    db: Session,
    *,
    public_id: UUID,
    payload: CommercialOfferCreditReviewCreate,
    current_user_public_id: str | None,
) -> CommercialOfferCreditReviewCreatedResponse:
    commercial_offer_context = _lock_offer_for_content_change(db, public_id)
    commercial_offer = get_commercial_offer(db, public_id)

    values = _normalize_credit_review_payload(
        payload=payload,
        current_user_public_id=current_user_public_id,
    )
    review_public_id = str(uuid4())

    try:
        review = insert_commercial_offer_credit_review(
            db,
            public_id=review_public_id,
            commercial_offer_id=int(commercial_offer_context["commercial_offer_id"]),
            values=values,
        )
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_CREDIT_REVIEW_RECORDED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            status_before=commercial_offer.offer_status_code,
            status_after=commercial_offer.offer_status_code,
            reason=(
                "Manual Commercial Offer credit/exposure review evidence recorded. "
                "This does not calculate exposure, approve Finance workflow or change lifecycle status."
            ),
            event_payload={
                "offer_code": commercial_offer.offer_code,
                "commercial_offer_public_id": str(public_id),
                "credit_review_public_id": str(review.public_id),
                "review_status": review.review_status,
                "review_reference": review.review_reference,
                "reviewed_at": review.reviewed_at.isoformat(),
                "manual_review_only": True,
            },
        )
        db.commit()
    except IntegrityError as exc:
        # A review recorded at the same time by a writer that does not take the offer's lock (CS-05c, TB-1 TB1-304):
        # the offer keeps one current review, and this request is told to look again (409).
        db.rollback()
        _refuse_duplicate(
            exc,
            {
                COMMERCIAL_OFFER_CURRENT_CREDIT_REVIEW_INDEX: lambda: CommercialOfferConflictError(
                    "Someone else recorded a credit review for this Commercial Offer at the same time, so yours was "
                    "not saved. Reload the page to see it, then record yours again if it is still needed."
                ),
            },
        )
    except Exception:
        db.rollback()
        raise

    return CommercialOfferCreditReviewCreatedResponse(
        credit_review=review,
        event=_event_dict(event),
    )
