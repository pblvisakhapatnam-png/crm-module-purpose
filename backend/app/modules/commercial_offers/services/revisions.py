"""Legacy Slice 6K revision compatibility.

Slice 9F refuses new in-place revision cycles because submitted offer rows are immutable. Existing
OPEN revision records remain listable and may be marked resubmitted or cancelled so pre-9F data is
not stranded; an OPEN legacy record never unlocks the offer's commercial content.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_EVENT_REVISION_CANCELLED,
    COMMERCIAL_OFFER_EVENT_REVISION_RESUBMITTED,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_RECORD_TYPE,
    COMMERCIAL_OFFER_REVISION_STATUS_CANCELLED,
    COMMERCIAL_OFFER_REVISION_STATUS_OPEN,
    COMMERCIAL_OFFER_REVISION_STATUS_RESUBMITTED,
)
from app.modules.commercial_offers.repository import (
    get_commercial_offer_context_by_public_id,
    get_commercial_offer_revision_for_offer,
    lock_commercial_offer_row,
    list_commercial_offer_revisions_for_offer,
    update_commercial_offer_revision_status,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferRevisionActionResponse,
    CommercialOfferRevisionCreate,
    CommercialOfferRevisionMarkResubmitted,
    CommercialOfferRevisionResponse,
    CommercialOfferResponse,
)
from app.modules.events.service import record_business_event

from app.modules.commercial_offers.services.common import (
    CommercialOfferNotFoundError,
    CommercialOfferRevisionNotFoundError,
    CommercialOfferValidationError,
    _event_dict,
    _revision_evidence_context,
    get_commercial_offer,
)


def list_commercial_offer_revisions(
    db: Session,
    public_id: UUID,
) -> list[CommercialOfferRevisionResponse]:
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    return list_commercial_offer_revisions_for_offer(
        db,
        commercial_offer_id=int(commercial_offer_context["commercial_offer_id"]),
    )


def create_commercial_offer_revision(
    db: Session,
    *,
    public_id: UUID,
    payload: CommercialOfferRevisionCreate,
    current_user_public_id: str | None,
) -> CommercialOfferRevisionActionResponse:
    # Status-dependent mutation: reads SUBMITTED then inserts a revision, so the offer is locked
    # for the transaction against a concurrent customer response committing a terminal status.
    if lock_commercial_offer_row(db, public_id=str(public_id)) is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    get_commercial_offer(db, public_id)
    raise CommercialOfferValidationError(
        "New in-place revision cycles are no longer started. Use Make a new version; existing revision records "
        "remain available as history and an already-open legacy revision may still be closed."
    )


def _revision_event_payload(
    revision: CommercialOfferRevisionResponse,
    *,
    previous_status: str | None = None,
) -> dict[str, object | None]:
    return {
        "commercial_offer_public_id": str(revision.commercial_offer_public_id),
        "revision_public_id": str(revision.public_id),
        "revision_label": revision.revision_label,
        "previous_revision_status": previous_status,
        "new_revision_status": revision.revision_status,
        "source_submission_evidence_public_id": str(revision.source_submission_evidence_public_id)
        if revision.source_submission_evidence_public_id
        else None,
        "resubmission_evidence_public_id": str(revision.resubmission_evidence_public_id)
        if revision.resubmission_evidence_public_id
        else None,
        "traceability_only": True,
        "commercial_offer_cloned": False,
    }


def _get_open_revision_context(
    db: Session,
    *,
    public_id: UUID,
    revision_public_id: UUID,
) -> tuple[CommercialOfferResponse, int, CommercialOfferRevisionResponse]:
    # Keep the legacy close action serialized with other status-dependent operations on the same
    # offer. This is compatibility only: the OPEN record does not make offer content editable.
    if lock_commercial_offer_row(db, public_id=str(public_id)) is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    commercial_offer = get_commercial_offer(db, public_id)
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])
    revision = get_commercial_offer_revision_for_offer(
        db,
        commercial_offer_id=commercial_offer_id,
        public_id=str(revision_public_id),
    )
    if revision is None:
        raise CommercialOfferRevisionNotFoundError("Commercial Offer revision not found.")
    if revision.revision_status != COMMERCIAL_OFFER_REVISION_STATUS_OPEN:
        raise CommercialOfferValidationError(
            f"Only an OPEN revision may be changed. Current revision status is {revision.revision_status}."
        )
    return commercial_offer, commercial_offer_id, revision


def mark_commercial_offer_revision_resubmitted(
    db: Session,
    *,
    public_id: UUID,
    revision_public_id: UUID,
    payload: CommercialOfferRevisionMarkResubmitted,
    current_user_public_id: str | None,
) -> CommercialOfferRevisionActionResponse:
    commercial_offer, commercial_offer_id, existing = _get_open_revision_context(
        db,
        public_id=public_id,
        revision_public_id=revision_public_id,
    )
    evidence = _revision_evidence_context(
        db,
        commercial_offer_id=commercial_offer_id,
        evidence_public_id=payload.resubmission_evidence_public_id,
        field_label="Resubmission evidence",
    )
    if evidence is None:
        raise CommercialOfferValidationError("Resubmission evidence is required.")

    try:
        revision = update_commercial_offer_revision_status(
            db,
            commercial_offer_id=commercial_offer_id,
            public_id=str(revision_public_id),
            expected_status=COMMERCIAL_OFFER_REVISION_STATUS_OPEN,
            new_status=COMMERCIAL_OFFER_REVISION_STATUS_RESUBMITTED,
            resubmission_evidence_id=int(evidence["id"]),
        )
        if revision is None:
            raise CommercialOfferValidationError("Only an OPEN revision may be marked resubmitted.")
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_REVISION_RESUBMITTED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            status_before=existing.revision_status,
            status_after=revision.revision_status,
            reason=(
                "Commercial Offer revision marked resubmitted using existing submission evidence. "
                "No evidence or quote document was created automatically."
            ),
            event_payload=_revision_event_payload(revision, previous_status=existing.revision_status),
        )
        db.commit()
    except (CommercialOfferValidationError, CommercialOfferRevisionNotFoundError):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return CommercialOfferRevisionActionResponse(revision=revision, event=_event_dict(event))


def cancel_commercial_offer_revision(
    db: Session,
    *,
    public_id: UUID,
    revision_public_id: UUID,
    current_user_public_id: str | None,
) -> CommercialOfferRevisionActionResponse:
    commercial_offer, commercial_offer_id, existing = _get_open_revision_context(
        db,
        public_id=public_id,
        revision_public_id=revision_public_id,
    )

    try:
        revision = update_commercial_offer_revision_status(
            db,
            commercial_offer_id=commercial_offer_id,
            public_id=str(revision_public_id),
            expected_status=COMMERCIAL_OFFER_REVISION_STATUS_OPEN,
            new_status=COMMERCIAL_OFFER_REVISION_STATUS_CANCELLED,
        )
        if revision is None:
            raise CommercialOfferValidationError("Only an OPEN revision may be cancelled.")
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_REVISION_CANCELLED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            status_before=existing.revision_status,
            status_after=revision.revision_status,
            reason="Commercial Offer revision/resubmission traceability record cancelled.",
            event_payload=_revision_event_payload(revision, previous_status=existing.revision_status),
        )
        db.commit()
    except CommercialOfferValidationError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return CommercialOfferRevisionActionResponse(revision=revision, event=_event_dict(event))
