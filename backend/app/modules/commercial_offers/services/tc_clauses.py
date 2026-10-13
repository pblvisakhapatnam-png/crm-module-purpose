"""Terms and conditions on an offer: listing, attaching and removing clauses from the library, and
attaching the recommended ones (Slices 6F and 6G).

The T&C readiness view is in common.py, because the submission readiness checklist reads it too.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_ACTIVE_TC_CLAUSE_INDEX,
    COMMERCIAL_OFFER_EVENT_TC_CLAUSE_ATTACHED,
    COMMERCIAL_OFFER_EVENT_TC_CLAUSE_REMOVED,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_RECORD_TYPE,
)
from app.modules.commercial_offers.repository import (
    active_commercial_offer_tc_clause_attachment_exists,
    deactivate_commercial_offer_tc_clause_attachment,
    get_commercial_offer_context_by_public_id,
    get_commercial_offer_tc_clause_attachment_context,
    get_next_commercial_offer_tc_clause_sort_order,
    get_tc_clause_context_by_public_id,
    insert_commercial_offer_tc_clause_attachment,
    list_commercial_offer_tc_clauses_for_offer,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferTcClauseAttachRequest,
    CommercialOfferTcClauseAttachRecommendedRequest,
    CommercialOfferTcClauseAttachedResponse,
    CommercialOfferTcClauseAttachRecommendedResponse,
    CommercialOfferTcClauseRemovedResponse,
    CommercialOfferTcClauseResponse,
)
from app.modules.events.service import record_business_event

from app.modules.commercial_offers.services.common import (
    CommercialOfferNotFoundError,
    CommercialOfferTcClauseNotFoundError,
    CommercialOfferValidationError,
    _event_dict,
    _lock_offer_for_content_change,
    _refuse_duplicate,
    get_commercial_offer_tc_clause_readiness,
)


def list_commercial_offer_tc_clauses(
    db: Session,
    public_id: UUID,
) -> list[CommercialOfferTcClauseResponse]:
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    return list_commercial_offer_tc_clauses_for_offer(
        db,
        commercial_offer_id=int(commercial_offer_context["commercial_offer_id"]),
    )


def attach_recommended_commercial_offer_tc_clauses(
    db: Session,
    *,
    public_id: UUID,
    payload: CommercialOfferTcClauseAttachRecommendedRequest,
    current_user_public_id: str | None,
) -> CommercialOfferTcClauseAttachRecommendedResponse:
    basis_value = payload.recommendation_basis or payload.business_line
    readiness = get_commercial_offer_tc_clause_readiness(
        db,
        public_id=public_id,
        recommendation_basis=basis_value,
    )
    if readiness.recommendation_basis is None:
        raise CommercialOfferValidationError("Recommendation basis is required before attaching recommended clauses.")

    missing_clause_public_ids = [
        clause.tc_clause_public_id for clause in readiness.recommended_clauses if clause.status == "NOT_ATTACHED"
    ]
    if not missing_clause_public_ids:
        return CommercialOfferTcClauseAttachRecommendedResponse(
            readiness=readiness,
            tc_clauses=[],
            events=[],
            attached_count=0,
            status_text="All recommended header-level clauses are already attached.",
        )

    attached_response = attach_commercial_offer_tc_clauses(
        db,
        public_id=public_id,
        payload=CommercialOfferTcClauseAttachRequest(clause_public_ids=missing_clause_public_ids),
        current_user_public_id=current_user_public_id,
    )
    updated_readiness = get_commercial_offer_tc_clause_readiness(
        db,
        public_id=public_id,
        recommendation_basis=readiness.recommendation_basis,
    )
    attached_count = len(attached_response.tc_clauses)
    return CommercialOfferTcClauseAttachRecommendedResponse(
        readiness=updated_readiness,
        tc_clauses=attached_response.tc_clauses,
        events=attached_response.events,
        attached_count=attached_count,
        status_text=f"Attached {attached_count} recommended header-level clause(s).",
    )


def _unique_clause_public_ids(payload: CommercialOfferTcClauseAttachRequest) -> list[str]:
    values = [str(value) for value in payload.clause_public_ids]
    if len(values) != len(set(values)):
        raise CommercialOfferValidationError("Duplicate T&C clause IDs were provided in the same attachment request.")
    return values


def _snapshot_values_from_clause(
    *,
    clause_context: dict[str, object],
    sort_order: int,
    current_user_public_id: str | None,
) -> dict[str, object | None]:
    return {
        "clause_id_snapshot": clause_context["clause_id"],
        "title_snapshot": clause_context["title"],
        "clause_text_snapshot": clause_context["clause_text"],
        "business_line_snapshot": clause_context["business_line"],
        "clause_category_snapshot": clause_context["clause_category"],
        "source_clause_number_snapshot": clause_context.get("source_clause_number"),
        "source_reference_snapshot": clause_context.get("source_reference"),
        "mandatory_default_snapshot": bool(clause_context["mandatory_default"]),
        "risk_category_snapshot": clause_context.get("risk_category"),
        "applies_to_header_snapshot": bool(clause_context["applies_to_header"]),
        "applies_to_line_snapshot": bool(clause_context["applies_to_line"]),
        "requires_approval_if_omitted_snapshot": bool(clause_context["requires_approval_if_omitted"]),
        "requires_approval_if_modified_snapshot": bool(clause_context["requires_approval_if_modified"]),
        "sort_order": sort_order,
        "attached_by": current_user_public_id,
    }


def attach_commercial_offer_tc_clauses(
    db: Session,
    *,
    public_id: UUID,
    payload: CommercialOfferTcClauseAttachRequest,
    current_user_public_id: str | None,
) -> CommercialOfferTcClauseAttachedResponse:
    commercial_offer_context = _lock_offer_for_content_change(db, public_id)

    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])
    clause_public_ids = _unique_clause_public_ids(payload)
    attached: list[CommercialOfferTcClauseResponse] = []
    events: list[object] = []
    attaching: object = None

    try:
        next_sort_order = get_next_commercial_offer_tc_clause_sort_order(db, commercial_offer_id=commercial_offer_id)
        for clause_public_id in clause_public_ids:
            clause_context = get_tc_clause_context_by_public_id(db, clause_public_id)
            if clause_context is None:
                raise CommercialOfferTcClauseNotFoundError("T&C library clause not found.")

            if not bool(clause_context["active"]):
                raise CommercialOfferValidationError("Only active T&C library clauses may be attached to a Commercial Offer.")

            if not bool(clause_context["applies_to_header"]):
                raise CommercialOfferValidationError(
                    "Only header-applicable T&C library clauses may be attached to the Commercial Offer header."
                )

            tc_clause_id = int(clause_context["tc_clause_id"])
            attaching = clause_context["clause_id"]
            if active_commercial_offer_tc_clause_attachment_exists(
                db,
                commercial_offer_id=commercial_offer_id,
                tc_clause_id=tc_clause_id,
            ):
                raise CommercialOfferValidationError(
                    f"T&C clause {clause_context['clause_id']} is already attached to this Commercial Offer."
                )

            attachment = insert_commercial_offer_tc_clause_attachment(
                db,
                public_id=str(uuid4()),
                commercial_offer_id=commercial_offer_id,
                tc_clause_id=tc_clause_id,
                values=_snapshot_values_from_clause(
                    clause_context=clause_context,
                    sort_order=next_sort_order,
                    current_user_public_id=current_user_public_id,
                ),
            )
            next_sort_order += 1
            attached.append(attachment)
            events.append(
                record_business_event(
                    db,
                    event_name=COMMERCIAL_OFFER_EVENT_TC_CLAUSE_ATTACHED,
                    source_module=COMMERCIAL_OFFER_MODULE_NAME,
                    record_type=COMMERCIAL_OFFER_RECORD_TYPE,
                    record_public_id=str(public_id),
                    user_public_id=current_user_public_id,
                    status_before=None,
                    status_after=str(commercial_offer_context["offer_status_code"]),
                    reason="T&C clause attached to the Commercial Offer.",
                    event_payload={
                        "offer_code": commercial_offer_context.get("offer_code"),
                        "tc_clause_attachment_public_id": str(attachment.public_id),
                        "tc_clause_public_id": clause_public_id,
                        "clause_id_snapshot": attachment.clause_id_snapshot,
                        "title_snapshot": attachment.title_snapshot,
                        "mandatory_default_snapshot": attachment.mandatory_default_snapshot,
                        "requires_approval_if_omitted_snapshot": attachment.requires_approval_if_omitted_snapshot,
                        "requires_approval_if_modified_snapshot": attachment.requires_approval_if_modified_snapshot,
                    },
                )
            )

        db.commit()
    except (CommercialOfferTcClauseNotFoundError, CommercialOfferValidationError):
        db.rollback()
        raise
    except IntegrityError as exc:
        # The clause was attached at the same time by a writer that does not take the offer's lock (CS-05c, TB-1
        # TB1-304): answered as the check above answers a clause already attached.
        db.rollback()
        _refuse_duplicate(
            exc,
            {
                COMMERCIAL_OFFER_ACTIVE_TC_CLAUSE_INDEX: lambda: CommercialOfferValidationError(
                    f"T&C clause {attaching} is already attached to this Commercial Offer."
                ),
            },
        )
    except Exception:
        db.rollback()
        raise

    return CommercialOfferTcClauseAttachedResponse(
        tc_clauses=attached,
        events=[_event_dict(event) for event in events],
    )


def remove_commercial_offer_tc_clause(
    db: Session,
    *,
    public_id: UUID,
    attachment_public_id: UUID,
    current_user_public_id: str | None,
) -> CommercialOfferTcClauseRemovedResponse:
    commercial_offer_context = _lock_offer_for_content_change(db, public_id)

    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])
    existing = get_commercial_offer_tc_clause_attachment_context(
        db,
        commercial_offer_id=commercial_offer_id,
        attachment_public_id=str(attachment_public_id),
    )
    if existing is None or not bool(existing["active"]):
        raise CommercialOfferTcClauseNotFoundError("Commercial Offer T&C clause attachment not found.")

    try:
        attachment = deactivate_commercial_offer_tc_clause_attachment(
            db,
            commercial_offer_id=commercial_offer_id,
            attachment_public_id=str(attachment_public_id),
        )
        if attachment is None:
            raise CommercialOfferTcClauseNotFoundError("Commercial Offer T&C clause attachment not found.")

        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_TC_CLAUSE_REMOVED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=str(commercial_offer_context["offer_status_code"]),
            reason="T&C clause removed from the Commercial Offer.",
            event_payload={
                "offer_code": commercial_offer_context.get("offer_code"),
                "tc_clause_attachment_public_id": str(attachment.public_id),
                "tc_clause_public_id": str(attachment.tc_clause_public_id),
                "clause_id_snapshot": attachment.clause_id_snapshot,
                "title_snapshot": attachment.title_snapshot,
            },
        )
        db.commit()
    except CommercialOfferTcClauseNotFoundError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return CommercialOfferTcClauseRemovedResponse(tc_clause=attachment, event=_event_dict(event))
