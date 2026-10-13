"""Immutable submitted Commercial Offer versions (Slice 9F)."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_ALLOWED_REVISION_REASONS,
    COMMERCIAL_OFFER_CODE_VERSION_INDEX,
    COMMERCIAL_OFFER_EVENT_VERSION_ABANDONED,
    COMMERCIAL_OFFER_EVENT_VERSION_CREATED,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_RECORD_TYPE,
    COMMERCIAL_OFFER_STATUS_ABANDONED,
    COMMERCIAL_OFFER_STATUS_DRAFT,
    COMMERCIAL_OFFER_STATUS_SUBMITTED,
    COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES,
)
from app.modules.commercial_offers.repository import (
    copy_commercial_offer_version_children,
    get_commercial_offer_context_by_public_id,
    get_commercial_offer_version_context,
    insert_commercial_offer,
    list_commercial_offer_versions_for_code,
    lock_commercial_offer_row,
    update_commercial_offer_by_public_id,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferResponse,
    CommercialOfferVersionActionResponse,
    CommercialOfferVersionCreate,
)
from app.modules.events.service import record_business_event

from app.modules.commercial_offers.services.common import (
    CommercialOfferNotFoundError,
    CommercialOfferValidationError,
    _clean_optional,
    _event_dict,
    _normalize_code,
)


def _version_reason(value: str) -> str:
    reason = _normalize_code(value, "")
    if reason not in COMMERCIAL_OFFER_ALLOWED_REVISION_REASONS:
        raise CommercialOfferValidationError(
            "Version reason must be one of: " + ", ".join(COMMERCIAL_OFFER_ALLOWED_REVISION_REASONS) + "."
        )
    return reason


def list_commercial_offer_versions(db: Session, public_id: UUID) -> list[CommercialOfferResponse]:
    context = get_commercial_offer_version_context(db, public_id=str(public_id))
    if context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    return list_commercial_offer_versions_for_code(db, offer_code=str(context["offer_code"]))


def create_commercial_offer_version(
    db: Session,
    *,
    public_id: UUID,
    payload: CommercialOfferVersionCreate,
    current_user_public_id: str | None,
) -> CommercialOfferVersionActionResponse:
    if lock_commercial_offer_row(db, public_id=str(public_id)) is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    source = get_commercial_offer_version_context(db, public_id=str(public_id))
    if source is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    if source["offer_status_code"] != COMMERCIAL_OFFER_STATUS_SUBMITTED:
        raise CommercialOfferValidationError(
            "A new version may be made only from the latest Submitted Commercial Offer. "
            f"Current status is {source['offer_status_code']}."
        )
    if str(source["latest_sent_offer_public_id"]) != str(public_id):
        raise CommercialOfferValidationError("Make the new version from the latest sent Commercial Offer version.")
    if source.get("preparation_offer_public_id"):
        raise CommercialOfferValidationError(
            "Only one Commercial Offer version may be prepared at a time. Open or abandon the version already in preparation."
        )

    next_version = int(source["maximum_version_number"] or source["version_number"]) + 1
    values = {
        "offer_code": source["offer_code"],
        "opportunity_id": source["opportunity_id"],
        "business_party_id": source["business_party_id"],
        "offer_title": source["offer_title"],
        "offer_mode": source["offer_mode"],
        "offer_type": source["offer_type"],
        "offer_status_code": COMMERCIAL_OFFER_STATUS_DRAFT,
        "offer_value": source["offer_value"],
        "currency_code": source["currency_code"],
        "offer_date": source["offer_date"],
        "valid_until": source["valid_until"],
        "remarks": source["remarks"],
        "offer_purpose": source["offer_purpose"],
        "base_offer_id": source["base_offer_id"],
        "related_work_order_id": source["related_work_order_id"],
        "customer_request_reference": source["customer_request_reference"],
        "customer_request_received_date": source["customer_request_received_date"],
        "customer_request_summary": source["customer_request_summary"],
        "version_number": next_version,
        "previous_version_offer_id": source["commercial_offer_id"],
        "version_reason": _version_reason(payload.version_reason),
        "version_note": _clean_optional(payload.version_note),
        "created_by": current_user_public_id,
    }
    new_public_id = str(uuid4())
    try:
        new_offer = insert_commercial_offer(db, public_id=new_public_id, values=values)
        new_context = get_commercial_offer_context_by_public_id(db, new_public_id)
        if new_context is None:
            raise RuntimeError("New Commercial Offer version could not be reloaded.")
        copied = copy_commercial_offer_version_children(
            db,
            source_offer_id=int(source["commercial_offer_id"]),
            target_offer_id=int(new_context["commercial_offer_id"]),
            current_user_public_id=current_user_public_id,
        )
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_VERSION_CREATED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=new_public_id,
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=COMMERCIAL_OFFER_STATUS_DRAFT,
            reason="A new Commercial Offer version was made from the latest sent version.",
            event_payload={
                "offer_code": new_offer.offer_code,
                "source_offer_public_id": str(public_id),
                "source_version_number": int(source["version_number"]),
                "new_offer_public_id": new_public_id,
                "new_version_number": next_version,
                "version_reason": values["version_reason"],
                "copied": copied,
                "submission_evidence_copied": False,
                "quote_documents_copied": False,
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == COMMERCIAL_OFFER_CODE_VERSION_INDEX:
            raise CommercialOfferValidationError(
                "Another Commercial Offer version was made at the same time. Reload the version history."
            ) from None
        raise
    except Exception:
        db.rollback()
        raise
    return CommercialOfferVersionActionResponse(commercial_offer=new_offer, event=_event_dict(event))


def abandon_commercial_offer_version(
    db: Session, *, public_id: UUID, current_user_public_id: str | None
) -> CommercialOfferVersionActionResponse:
    if lock_commercial_offer_row(db, public_id=str(public_id)) is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    context = get_commercial_offer_version_context(db, public_id=str(public_id))
    if context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    if context["previous_version_offer_id"] is None or context["offer_status_code"] not in COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES:
        raise CommercialOfferValidationError("Only a Draft or Ready for Review later version may be abandoned.")
    previous_status = str(context["offer_status_code"])
    try:
        abandoned = update_commercial_offer_by_public_id(
            db, public_id=str(public_id), values={"offer_status_code": COMMERCIAL_OFFER_STATUS_ABANDONED}
        )
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_VERSION_ABANDONED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            status_before=previous_status,
            status_after=COMMERCIAL_OFFER_STATUS_ABANDONED,
            reason="Commercial Offer version preparation was abandoned; the previously sent version is unchanged.",
            event_payload={
                "offer_code": abandoned.offer_code,
                "version_number": abandoned.version_number,
                "previous_version_offer_public_id": str(abandoned.previous_version_offer_public_id),
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return CommercialOfferVersionActionResponse(commercial_offer=abandoned, event=_event_dict(event))
