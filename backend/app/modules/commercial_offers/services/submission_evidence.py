"""Submission evidence: how and when an offer was sent to the customer (Slice 6I)."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_ALLOWED_SUBMISSION_CHANNELS,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_EVENT_SUBMISSION_EVIDENCE_RECORDED,
    COMMERCIAL_OFFER_RECORD_TYPE,
)
from app.modules.commercial_offers.repository import (
    get_commercial_offer_context_by_public_id,
    insert_commercial_offer_submission_evidence,
    list_commercial_offer_submission_evidence_for_offer,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferSubmissionEvidenceCreate,
    CommercialOfferSubmissionEvidenceCreatedResponse,
    CommercialOfferSubmissionEvidenceResponse,
    CommercialOfferResponse,
)
from app.modules.events.service import record_business_event

from app.modules.commercial_offers.services.common import (
    CommercialOfferNotFoundError,
    CommercialOfferValidationError,
    _clean_optional,
    _event_dict,
    _lock_offer_for_content_change,
    _normalize_code,
    get_commercial_offer,
)


def _normalize_submission_channel(value: str | None) -> str:
    channel = _normalize_code(value, "")
    if channel not in COMMERCIAL_OFFER_ALLOWED_SUBMISSION_CHANNELS:
        allowed = ", ".join(COMMERCIAL_OFFER_ALLOWED_SUBMISSION_CHANNELS)
        raise CommercialOfferValidationError(f"Submission channel must be one of: {allowed}.")
    return channel


def _normalize_submission_evidence_payload(
    *,
    commercial_offer: CommercialOfferResponse,
    payload: CommercialOfferSubmissionEvidenceCreate,
    current_user_public_id: str | None,
) -> dict[str, object | None]:
    return {
        "submission_reference": _clean_optional(payload.submission_reference),
        "submission_channel": _normalize_submission_channel(payload.submission_channel),
        "submitted_at": payload.submitted_at,
        "submitted_by": current_user_public_id,
        "recipient_summary": _clean_optional(payload.recipient_summary),
        "submitted_amount_snapshot": commercial_offer.offer_value,
        "submitted_currency_snapshot": commercial_offer.currency_code,
        "submitted_version_snapshot": _clean_optional(payload.submitted_version_snapshot),
        "document_reference_label": _clean_optional(payload.document_reference_label),
        "document_reference_url_or_path": _clean_optional(payload.document_reference_url_or_path),
        "evidence_notes": _clean_optional(payload.evidence_notes),
        "created_by": current_user_public_id,
    }


def list_commercial_offer_submission_evidence(
    db: Session,
    public_id: UUID,
) -> list[CommercialOfferSubmissionEvidenceResponse]:
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    return list_commercial_offer_submission_evidence_for_offer(
        db,
        commercial_offer_id=int(commercial_offer_context["commercial_offer_id"]),
    )


def create_commercial_offer_submission_evidence(
    db: Session,
    *,
    public_id: UUID,
    payload: CommercialOfferSubmissionEvidenceCreate,
    current_user_public_id: str | None,
) -> CommercialOfferSubmissionEvidenceCreatedResponse:
    commercial_offer_context = _lock_offer_for_content_change(db, public_id)
    commercial_offer = get_commercial_offer(db, public_id)

    values = _normalize_submission_evidence_payload(
        commercial_offer=commercial_offer,
        payload=payload,
        current_user_public_id=current_user_public_id,
    )
    evidence_public_id = str(uuid4())

    try:
        evidence = insert_commercial_offer_submission_evidence(
            db,
            public_id=evidence_public_id,
            commercial_offer_id=int(commercial_offer_context["commercial_offer_id"]),
            values=values,
        )
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_SUBMISSION_EVIDENCE_RECORDED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            status_before=commercial_offer.offer_status_code,
            status_after=commercial_offer.offer_status_code,
            reason=(
                "Commercial Offer submission evidence metadata recorded. "
                "This does not generate quote documents, upload files or calculate credit exposure."
            ),
            event_payload={
                "offer_code": commercial_offer.offer_code,
                "commercial_offer_public_id": str(public_id),
                "submission_evidence_public_id": str(evidence.public_id),
                "submission_channel": evidence.submission_channel,
                "submitted_at": evidence.submitted_at.isoformat(),
                "submission_reference": evidence.submission_reference,
                "has_document_reference": bool(evidence.document_reference_label or evidence.document_reference_url_or_path),
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return CommercialOfferSubmissionEvidenceCreatedResponse(
        submission_evidence=evidence,
        event=_event_dict(event),
    )
