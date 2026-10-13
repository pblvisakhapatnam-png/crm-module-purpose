"""What an offer's lifecycle allows next, including 9F immutable versions. It records nothing."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ACCEPTED_AWARDED,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REVISION_REQUESTED,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_CLARIFICATION_REQUESTED,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ON_HOLD,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_OTHER,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_PENDING,
    COMMERCIAL_OFFER_PURPOSE_CHANGE_QUOTATION,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_HANDOFF_BLOCKED,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_READY_FOR_HANDOFF,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_WORK_ORDER_EXISTS,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_AWAITING_CUSTOMER_RESPONSE,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_ABANDONED_HISTORY,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_CLARIFICATION_REQUESTED_ACTIVE,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_LABELS,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_NOT_YET_SUBMITTED,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_ON_HOLD_ACTIVE,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_OTHER_ACTIVE,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_PENDING_CUSTOMER_DECISION_ACTIVE,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_REJECTED_CLOSED,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_REPLACED_HISTORY,
    COMMERCIAL_OFFER_LIFECYCLE_STATE_REVISION_REQUESTED_ACTIVE,
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
    COMMERCIAL_OFFER_STATUS_ABANDONED,
    COMMERCIAL_OFFER_STATUS_CLOSED,
    COMMERCIAL_OFFER_STATUS_REJECTED,
    COMMERCIAL_OFFER_STATUS_REVISED,
    COMMERCIAL_OFFER_STATUS_SUBMITTED,
    COMMERCIAL_OFFER_STATUS_WITHDRAWN,
    COMMERCIAL_OFFER_VERSION_HISTORY_STATUSES,
    latest_response_not_accepted_reason,
)
from app.modules.commercial_offers.repository import (
    get_commercial_offer_context_by_public_id,
    get_commercial_offer_version_context,
    get_open_commercial_offer_revision_for_offer,
    list_commercial_offer_customer_responses_for_offer,
    list_offer_line_handoff,
    list_linked_work_order_contexts_for_offer,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferLifecycleGuidanceResponse,
    CommercialOfferLineHandoff,
    CommercialOfferLinkedWorkOrderSummary,
)

from app.modules.commercial_offers.services.common import (
    CommercialOfferNotFoundError,
    get_commercial_offer,
)


def get_commercial_offer_lifecycle_guidance(
    db: Session,
    public_id: UUID,
) -> CommercialOfferLifecycleGuidanceResponse:
    """Derive one coherent post-response lifecycle/readiness view.

    This is read-only and creates no business_event. It is explanatory guidance for
    the UI, not a substitute for the authoritative guards already enforced by
    create_commercial_offer_revision, create_commercial_offer_customer_response and
    the Work Order handoff endpoint, which independently validate their own
    preconditions regardless of what this view reports.
    """
    commercial_offer = get_commercial_offer(db, public_id)
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])

    customer_responses = list_commercial_offer_customer_responses_for_offer(
        db,
        commercial_offer_id=commercial_offer_id,
    )
    latest_response = customer_responses[0] if customer_responses else None

    open_revision = get_open_commercial_offer_revision_for_offer(db, commercial_offer_id=commercial_offer_id)
    can_open_revision = False
    has_open_revision_awaiting_resubmission = open_revision is not None
    version_context = get_commercial_offer_version_context(db, public_id=str(public_id))
    has_preparation_version = bool(version_context and version_context.get("preparation_offer_public_id"))
    can_make_new_version = bool(
        version_context
        and commercial_offer.offer_status_code == COMMERCIAL_OFFER_STATUS_SUBMITTED
        and not has_preparation_version
        and str(version_context.get("latest_sent_offer_public_id")) == str(public_id)
    )

    can_record_customer_response = (
        commercial_offer.offer_status_code in COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES
        and not has_preparation_version
    )

    linked_work_order_contexts = list_linked_work_order_contexts_for_offer(
        db,
        commercial_offer_id=commercial_offer_id,
    )
    linked_work_orders = [
        CommercialOfferLinkedWorkOrderSummary(
            public_id=context["public_id"],
            work_order_code=context["work_order_code"],
            work_order_status_code=context["work_order_status_code"],
        )
        for context in linked_work_order_contexts
    ]

    # Every active line with what Work Orders hold of it, counted in one statement (CS-04 part 1).
    line_handoff = [
        CommercialOfferLineHandoff(**line) for line in list_offer_line_handoff(db, commercial_offer_id=commercial_offer_id)
    ]
    active_line_count = len(line_handoff)

    work_order_handoff_blocked_reasons: list[str] = []
    if commercial_offer.offer_status_code != COMMERCIAL_OFFER_STATUS_ACCEPTED:
        work_order_handoff_blocked_reasons.append(
            "The offer is not accepted yet. A Work Order needs an accepted or awarded customer response."
        )
    if not commercial_offer.account_public_id:
        work_order_handoff_blocked_reasons.append(
            "The offer's Opportunity is not linked to an Account."
        )
    if active_line_count == 0:
        work_order_handoff_blocked_reasons.append(
            "The offer needs at least one active line before a Work Order can be created."
        )
    # CS-04 part 1 (owner, 8 October 2026): the same rules the handoff refuses by, so this view and the endpoint agree.
    if commercial_offer.offer_purpose == COMMERCIAL_OFFER_PURPOSE_CHANGE_QUOTATION:
        work_order_handoff_blocked_reasons.append(
            "A Change Quotation does not make a Work Order of its own: cite it on an amendment of the Work Order it "
            "changes."
        )
    if commercial_offer.offer_status_code == COMMERCIAL_OFFER_STATUS_ACCEPTED:
        if latest_response is None:
            work_order_handoff_blocked_reasons.append("No customer acceptance or award is recorded for this offer.")
        elif latest_response.response_outcome != COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ACCEPTED_AWARDED:
            # Named whatever else blocks the offer, as the handoff names it (review round 7).
            work_order_handoff_blocked_reasons.append(
                latest_response_not_accepted_reason(latest_response.response_outcome)
            )
    if line_handoff and all(line.quantity_left <= 0 for line in line_handoff):
        work_order_handoff_blocked_reasons.append("Every line of this offer is already on a Work Order in full.")
    work_order_handoff_available = not work_order_handoff_blocked_reasons

    if commercial_offer.offer_status_code == COMMERCIAL_OFFER_STATUS_ACCEPTED:
        is_commercially_active = True
        if linked_work_orders:
            lifecycle_state = COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_WORK_ORDER_EXISTS
            advisory_message = (
                "Customer response recorded as accepted/awarded, and a Work Order already exists for this "
                "Commercial Offer. Open it from the list below. A second Work Order from the same offer is only "
                "for work the customer awarded in parts: it may take only what is not on a Work Order yet."
            )
            recommended_next_action = "Open the existing Work Order."
        elif work_order_handoff_available:
            lifecycle_state = COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_READY_FOR_HANDOFF
            advisory_message = "Customer response recorded as accepted/awarded. This Commercial Offer is ready for its Work Order to be created."
            recommended_next_action = "Use Create Work Order to hand the award over to Ops."
        else:
            lifecycle_state = COMMERCIAL_OFFER_LIFECYCLE_STATE_ACCEPTED_HANDOFF_BLOCKED
            advisory_message = "Customer response recorded as accepted/awarded, but the Work Order cannot be created yet: " + " ".join(
                work_order_handoff_blocked_reasons
            )
            recommended_next_action = "Resolve the reason(s) above, then create the Work Order."
    elif commercial_offer.offer_status_code == COMMERCIAL_OFFER_STATUS_REVISED:
        lifecycle_state = COMMERCIAL_OFFER_LIFECYCLE_STATE_REPLACED_HISTORY
        is_commercially_active = False
        replacement_label = (
            f"v{commercial_offer.replaced_by_version_number}"
            if commercial_offer.replaced_by_version_number is not None
            else "a later version"
        )
        advisory_message = (
            f"This Commercial Offer version was replaced by {replacement_label} and remains read-only history."
        )
        recommended_next_action = "Open the replacement or latest live version."
    elif commercial_offer.offer_status_code == COMMERCIAL_OFFER_STATUS_ABANDONED:
        lifecycle_state = COMMERCIAL_OFFER_LIFECYCLE_STATE_ABANDONED_HISTORY
        is_commercially_active = False
        advisory_message = (
            "This Commercial Offer version was abandoned before it was sent. "
            "The previously sent version is unchanged."
        )
        recommended_next_action = "Open the previously sent or latest live version."
    elif commercial_offer.offer_status_code == COMMERCIAL_OFFER_STATUS_REJECTED:
        lifecycle_state = COMMERCIAL_OFFER_LIFECYCLE_STATE_REJECTED_CLOSED
        is_commercially_active = False
        advisory_message = "Customer response recorded as rejected/lost. This Commercial Offer is closed for further commercial action; history remains visible for traceability."
        recommended_next_action = "No further commercial action is expected on this Commercial Offer."
    elif commercial_offer.offer_status_code == COMMERCIAL_OFFER_STATUS_SUBMITTED:
        lifecycle_state = COMMERCIAL_OFFER_LIFECYCLE_STATE_AWAITING_CUSTOMER_RESPONSE
        is_commercially_active = True
        advisory_message = "This Commercial Offer has been submitted and is awaiting a customer response or award outcome."
        recommended_next_action = "Record the customer response / award outcome when it becomes available."
    else:
        lifecycle_state = COMMERCIAL_OFFER_LIFECYCLE_STATE_NOT_YET_SUBMITTED
        is_commercially_active = commercial_offer.offer_status_code not in (
            COMMERCIAL_OFFER_STATUS_WITHDRAWN,
            COMMERCIAL_OFFER_STATUS_CLOSED,
        )
        advisory_message = "No customer response has been recorded because this Commercial Offer has not been submitted yet."
        recommended_next_action = "Complete submission readiness, then record as Submitted / commercially committed."

    # The latest effective customer response takes precedence for non-final outcomes,
    # even if offer_status_code alone would otherwise look eligible (for example, an
    # ACCEPTED offer that later receives a REVISION_REQUESTED follow-up response).
    non_final_outcome_states = {
        COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REVISION_REQUESTED: (
            COMMERCIAL_OFFER_LIFECYCLE_STATE_REVISION_REQUESTED_ACTIVE,
            "Customer requested a revision.",
        ),
        COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_CLARIFICATION_REQUESTED: (
            COMMERCIAL_OFFER_LIFECYCLE_STATE_CLARIFICATION_REQUESTED_ACTIVE,
            "Customer requested clarification.",
        ),
        COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ON_HOLD: (
            COMMERCIAL_OFFER_LIFECYCLE_STATE_ON_HOLD_ACTIVE,
            "The customer decision/process is on hold.",
        ),
        COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_PENDING: (
            COMMERCIAL_OFFER_LIFECYCLE_STATE_PENDING_CUSTOMER_DECISION_ACTIVE,
            "Awaiting the customer's decision.",
        ),
        COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_OTHER: (
            COMMERCIAL_OFFER_LIFECYCLE_STATE_OTHER_ACTIVE,
            "An other/uncategorised customer response was recorded. Review the response notes for details.",
        ),
    }
    if (
        commercial_offer.offer_status_code not in COMMERCIAL_OFFER_VERSION_HISTORY_STATUSES
        and latest_response is not None
        and latest_response.response_outcome in non_final_outcome_states
    ):
        lifecycle_state, base_message = non_final_outcome_states[latest_response.response_outcome]
        is_commercially_active = True
        work_order_handoff_available = False
        if not work_order_handoff_blocked_reasons:
            work_order_handoff_blocked_reasons.append("Latest customer response is not accepted/awarded.")

        if lifecycle_state == COMMERCIAL_OFFER_LIFECYCLE_STATE_REVISION_REQUESTED_ACTIVE:
            if has_open_revision_awaiting_resubmission:
                advisory_message = (
                    f"{base_message} Revised offer {open_revision.revision_label} is already in progress and not yet "
                    "re-sent to the customer."
                )
                recommended_next_action = "Mark the revised offer as re-sent once you have evidence it was sent, or cancel it."
            elif can_make_new_version:
                advisory_message = f"{base_message} Make a new version and send that version to the customer."
                recommended_next_action = "Make a new version."
            else:
                advisory_message = f"{base_message} A new version cannot be made from this record in its current state."
                recommended_next_action = "Open the latest sent or in-preparation version."
        elif lifecycle_state == COMMERCIAL_OFFER_LIFECYCLE_STATE_CLARIFICATION_REQUESTED_ACTIVE:
            advisory_message = f"{base_message} Follow up with the customer, then record the next customer response when available."
            recommended_next_action = "Provide clarification to the customer, then record the next customer response."
        elif lifecycle_state == COMMERCIAL_OFFER_LIFECYCLE_STATE_ON_HOLD_ACTIVE:
            advisory_message = f"{base_message} This Commercial Offer stays on record, but a Work Order cannot be created yet."
            recommended_next_action = "Wait for the hold to clear, then record the next customer response."
        elif lifecycle_state == COMMERCIAL_OFFER_LIFECYCLE_STATE_PENDING_CUSTOMER_DECISION_ACTIVE:
            advisory_message = f"{base_message} A Work Order can be created only after the customer accepts or awards the offer."
            recommended_next_action = "Record the next customer response when the decision is received."
        else:
            advisory_message = base_message
            recommended_next_action = "Review the recorded response and record a categorised follow-up response if applicable."

    if has_preparation_version and commercial_offer.offer_status_code in COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES:
        advisory_message = (
            "A newer Commercial Offer version is being prepared. Send that version or abandon it before recording "
            "a customer response against this sent version."
        )
        recommended_next_action = "Open Offer versions, then send or abandon the version in preparation."

    return CommercialOfferLifecycleGuidanceResponse(
        commercial_offer_public_id=commercial_offer.public_id,
        offer_status_code=commercial_offer.offer_status_code,
        latest_customer_response_outcome=latest_response.response_outcome if latest_response else None,
        latest_customer_response_public_id=latest_response.public_id if latest_response else None,
        latest_customer_response_received_at=latest_response.response_received_at if latest_response else None,
        lifecycle_state=lifecycle_state,
        lifecycle_state_label=COMMERCIAL_OFFER_LIFECYCLE_STATE_LABELS[lifecycle_state],
        is_commercially_active=is_commercially_active,
        advisory_message=advisory_message,
        recommended_next_action=recommended_next_action,
        can_open_revision=can_open_revision,
        can_make_new_version=can_make_new_version,
        has_open_revision_awaiting_resubmission=has_open_revision_awaiting_resubmission,
        can_record_customer_response=can_record_customer_response,
        work_order_handoff_available=work_order_handoff_available,
        work_order_handoff_blocked_reasons=work_order_handoff_blocked_reasons,
        linked_work_orders=linked_work_orders,
        line_handoff=line_handoff,
    )
