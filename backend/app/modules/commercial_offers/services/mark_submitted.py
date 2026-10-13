"""Marking an offer submitted: the controlled submission that commits it commercially (Slice 6J)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_EVENT_COMMERCIALLY_COMMITTED,
    COMMERCIAL_OFFER_EVENT_VERSION_REPLACED,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVAL_REQUIRED,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_NOT_ASSESSED,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_REJECTED_OR_ON_HOLD,
    COMMERCIAL_OFFER_LINE_STATUS_ACTIVE,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_MARK_SUBMITTED_ALLOWED_STATUSES,
    COMMERCIAL_OFFER_STATUS_REVISED,
    COMMERCIAL_OFFER_STATUS_SUBMITTED,
    COMMERCIAL_OFFER_RECORD_TYPE,
)
from app.modules.commercial_offers.repository import (
    get_commercial_offer_by_public_id,
    get_commercial_offer_context_by_public_id,
    get_current_commercial_offer_credit_review,
    get_commercial_offer_version_context,
    lock_commercial_offer_row,
    lock_commercial_offer_version_submission_rows,
    list_commercial_offer_lines_for_offer,
    list_commercial_offer_submission_evidence_for_offer,
    update_commercial_offer_by_public_id,
)
from app.modules.commercial_offers.schemas import CommercialOfferMarkedSubmittedResponse
from app.modules.events.service import record_business_event

from app.modules.commercial_offers.services.common import (
    CommercialOfferNotFoundError,
    CommercialOfferValidationError,
    _event_dict,
)


def mark_commercial_offer_submitted(
    db: Session,
    *,
    public_id: UUID,
    current_user_public_id: str | None,
) -> CommercialOfferMarkedSubmittedResponse:
    initial_version_context = get_commercial_offer_version_context(db, public_id=str(public_id))
    if initial_version_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    previous_offer_id = initial_version_context.get("previous_version_offer_id")
    if previous_offer_id is not None:
        # The predecessor has the lower id and is always locked first. Customer response and version creation
        # take that same row lock, so submission cannot replace a predecessor whose outcome changed meanwhile.
        lock_commercial_offer_version_submission_rows(
            db,
            current_offer_id=int(initial_version_context["commercial_offer_id"]),
            previous_offer_id=int(previous_offer_id),
        )
    elif lock_commercial_offer_row(db, public_id=str(public_id)) is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    version_context = get_commercial_offer_version_context(db, public_id=str(public_id))
    if version_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    existing = get_commercial_offer_by_public_id(db, str(public_id))
    if existing is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    if existing.offer_status_code not in COMMERCIAL_OFFER_MARK_SUBMITTED_ALLOWED_STATUSES:
        allowed = ", ".join(COMMERCIAL_OFFER_MARK_SUBMITTED_ALLOWED_STATUSES)
        raise CommercialOfferValidationError(
            f"Commercial Offer can be recorded as submitted only from: {allowed}. Current status is {existing.offer_status_code}."
        )
    if version_context.get("previous_version_offer_id") is not None and (
        version_context.get("previous_version_status_code") != COMMERCIAL_OFFER_STATUS_SUBMITTED
    ):
        raise CommercialOfferValidationError(
            "This version cannot be sent because the previous version is no longer Submitted. "
            "Record the customer outcome against the correct latest sent version."
        )
    if not existing.account_public_id:
        raise CommercialOfferValidationError(
            "Account traceability is required before the Commercial Offer can be recorded as submitted."
        )
    if not existing.opportunity_public_id:
        raise CommercialOfferValidationError(
            "Opportunity traceability is required before the Commercial Offer can be recorded as submitted."
        )

    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])

    active_lines = [
        line
        for line in list_commercial_offer_lines_for_offer(db, commercial_offer_id=commercial_offer_id)
        if line.line_status_code == COMMERCIAL_OFFER_LINE_STATUS_ACTIVE
    ]
    if not active_lines:
        raise CommercialOfferValidationError(
            "At least one active Commercial Offer line is required before recording submission."
        )

    submission_evidence = list_commercial_offer_submission_evidence_for_offer(
        db,
        commercial_offer_id=commercial_offer_id,
    )
    if not submission_evidence:
        raise CommercialOfferValidationError(
            "Submission evidence metadata is required before recording the Commercial Offer as submitted."
        )
    latest_submission_evidence = submission_evidence[0]

    current_credit_review = get_current_commercial_offer_credit_review(
        db,
        commercial_offer_id=commercial_offer_id,
    )
    if (
        current_credit_review
        and current_credit_review.review_status == COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_REJECTED_OR_ON_HOLD
    ):
        raise CommercialOfferValidationError(
            "Latest manual credit/exposure review is Rejected or On Hold. Submission cannot be recorded until that review is superseded."
        )

    warnings: list[str] = []
    if current_credit_review is None:
        warnings.append(
            "Manual credit/exposure review has not been recorded. Exposure calculation and Finance approval workflow remain deferred."
        )
    elif current_credit_review.review_status in {
        COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_NOT_ASSESSED,
        COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVAL_REQUIRED,
    }:
        warnings.append(
            f"Latest manual credit/exposure review is {current_credit_review.review_status}. "
            "This action does not calculate exposure or complete Finance approval workflow."
        )

    values: dict[str, object | None] = {
        "offer_status_code": COMMERCIAL_OFFER_STATUS_SUBMITTED,
        "submitted_at": latest_submission_evidence.submitted_at,
    }
    if latest_submission_evidence.submission_reference:
        values["submission_reference"] = latest_submission_evidence.submission_reference

    try:
        predecessor_public_id = version_context.get("previous_version_offer_public_id")
        if predecessor_public_id is not None:
            update_commercial_offer_by_public_id(
                db,
                public_id=str(predecessor_public_id),
                values={"offer_status_code": COMMERCIAL_OFFER_STATUS_REVISED},
            )
            record_business_event(
                db,
                event_name=COMMERCIAL_OFFER_EVENT_VERSION_REPLACED,
                source_module=COMMERCIAL_OFFER_MODULE_NAME,
                record_type=COMMERCIAL_OFFER_RECORD_TYPE,
                record_public_id=str(predecessor_public_id),
                user_public_id=current_user_public_id,
                status_before=COMMERCIAL_OFFER_STATUS_SUBMITTED,
                status_after=COMMERCIAL_OFFER_STATUS_REVISED,
                reason="A later Commercial Offer version was submitted and replaced this sent version.",
                event_payload={
                    "offer_code": existing.offer_code,
                    "replaced_offer_public_id": str(predecessor_public_id),
                    "replacement_offer_public_id": str(public_id),
                    "replacement_version_number": int(version_context["version_number"]),
                },
            )
        commercial_offer = update_commercial_offer_by_public_id(
            db,
            public_id=str(public_id),
            values=values,
        )
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_COMMERCIALLY_COMMITTED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            status_before=existing.offer_status_code,
            status_after=COMMERCIAL_OFFER_STATUS_SUBMITTED,
            reason=(
                "Commercial Offer recorded as submitted/shared with the customer and commercially committed for traceability. "
                "This action does not generate or send documents, calculate exposure or release a Work Order."
            ),
            event_payload={
                "offer_code": commercial_offer.offer_code,
                "commercial_offer_public_id": str(public_id),
                "status_before": existing.offer_status_code,
                "status_after": commercial_offer.offer_status_code,
                "latest_submission_evidence_public_id": str(latest_submission_evidence.public_id),
                "latest_credit_review_public_id": str(current_credit_review.public_id)
                if current_credit_review
                else None,
                "latest_credit_review_status": current_credit_review.review_status
                if current_credit_review
                else None,
                "commercially_committed": True,
                "submission_evidence_created_by_action": False,
                "exposure_calculated": False,
                "work_order_created": False,
                "previous_version_offer_public_id": str(predecessor_public_id) if predecessor_public_id else None,
                "previous_version_status_after": COMMERCIAL_OFFER_STATUS_REVISED if predecessor_public_id else None,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return CommercialOfferMarkedSubmittedResponse(
        commercial_offer=commercial_offer,
        event=_event_dict(event),
        warnings=warnings,
    )
