"""The submission readiness checklist: what an offer still needs before it is submitted (Slice 6H, with
the rows later slices added)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ACCEPTED_AWARDED,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REJECTED_LOST,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REVISION_REQUESTED,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_CLARIFICATION_REQUESTED,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVED,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVAL_REQUIRED,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_REJECTED_OR_ON_HOLD,
    COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_WITHIN_LIMIT,
    COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES,
    COMMERCIAL_OFFER_LINE_STATUS_ACTIVE,
    COMMERCIAL_OFFER_STATUS_SUBMITTED,
    COMMERCIAL_OFFER_REVISION_STATUS_CANCELLED,
    COMMERCIAL_OFFER_REVISION_STATUS_OPEN,
    COMMERCIAL_OFFER_REVISION_STATUS_RESUBMITTED,
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_APPROVED_FOR_ISSUE,
)
from app.modules.commercial_offers.repository import (
    get_commercial_offer_context_by_public_id,
    get_current_commercial_offer_credit_review,
    list_pricing_evidence_for_offer,
    list_commercial_offer_lines_for_offer,
    list_commercial_offer_submission_evidence_for_offer,
    list_commercial_offer_customer_responses_for_offer,
    list_commercial_offer_revisions_for_offer,
    count_interactions_in_commercial_offer_chain,
    list_commercial_offer_quote_documents_for_offer,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferSubmissionReadinessItemResponse,
    CommercialOfferSubmissionReadinessResponse,
    CommercialOfferSubmissionReadinessSummaryResponse,
)

from app.modules.commercial_offers.services.common import (
    CommercialOfferNotFoundError,
    get_commercial_offer,
    get_commercial_offer_tc_clause_readiness,
)


COMMERCIAL_OFFER_SUBMISSION_READINESS_DEFERRED_ITEMS = (
    (
        "APPROVAL_WORKFLOW",
        "Commercial approval workflow",
        "Not built yet. Nothing here approves the Commercial Offer or its T&C wording.",
    ),
    (
        "SUBMISSION_PROOF_UPLOAD",
        "Submission proof upload/storage",
        "Not built yet. Submission evidence records how and when the offer was sent; it does not store the file that was sent.",
    ),
)
# QUOTE_DOCUMENT_GENERATION was removed from the tuple above by Slice 9E, which implements it:
# see the QUOTATION_DOCUMENT readiness row added to get_commercial_offer_submission_readiness()
# below. It is not a deferred future control any more.


def _submission_readiness_item(
    *,
    code: str,
    label: str,
    status: str,
    severity: str,
    message: str,
    evidence: dict[str, object] | None = None,
    deferred: bool = False,
) -> CommercialOfferSubmissionReadinessItemResponse:
    return CommercialOfferSubmissionReadinessItemResponse(
        code=code,
        label=label,
        status=status,
        severity=severity,
        message=message,
        evidence=evidence or {},
        deferred=deferred,
    )


def _submission_readiness_status(
    *,
    blocking_count: int,
    warning_count: int,
) -> str:
    if blocking_count > 0:
        return "NOT_READY"
    if warning_count > 0:
        return "ATTENTION_REQUIRED"
    return "READY"


def _line_numbers(numbers: list[int]) -> str:
    return ", ".join(str(number) for number in numbers)


def get_commercial_offer_submission_readiness(
    db: Session,
    *,
    public_id: UUID,
    recommendation_basis: str | None,
) -> CommercialOfferSubmissionReadinessResponse:
    commercial_offer = get_commercial_offer(db, public_id)
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])
    offer_lines = list_commercial_offer_lines_for_offer(db, commercial_offer_id=commercial_offer_id)
    active_lines = [line for line in offer_lines if line.line_status_code == COMMERCIAL_OFFER_LINE_STATUS_ACTIVE]
    pricing_evidence = list_pricing_evidence_for_offer(db, commercial_offer_id=commercial_offer_id)
    selected_pricing_evidence = [item for item in pricing_evidence if item.is_selected_basis]
    submission_evidence = list_commercial_offer_submission_evidence_for_offer(
        db,
        commercial_offer_id=commercial_offer_id,
    )
    revisions = list_commercial_offer_revisions_for_offer(
        db,
        commercial_offer_id=commercial_offer_id,
    )
    customer_responses = list_commercial_offer_customer_responses_for_offer(
        db,
        commercial_offer_id=commercial_offer_id,
    )
    current_credit_review = get_current_commercial_offer_credit_review(
        db,
        commercial_offer_id=commercial_offer_id,
    )
    tc_readiness = get_commercial_offer_tc_clause_readiness(
        db,
        public_id=public_id,
        recommendation_basis=recommendation_basis,
    )

    items: list[CommercialOfferSubmissionReadinessItemResponse] = []

    offer_inactive = commercial_offer.offer_status_code in COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES
    items.append(
        _submission_readiness_item(
            code="COMMERCIAL_OFFER_ACTIONABLE",
            label="Commercial Offer active/actionable",
            status="BLOCKING" if offer_inactive else "PASS",
            severity="BLOCKING" if offer_inactive else "INFO",
            message=(
                "Commercial Offer is inactive/final and should not be submitted again."
                if offer_inactive
                else "The offer has not been lost, withdrawn or closed."
            ),
            evidence={
                "offer_code": commercial_offer.offer_code,
                "offer_status_code": commercial_offer.offer_status_code,
            },
        )
    )

    commercially_committed = commercial_offer.offer_status_code == COMMERCIAL_OFFER_STATUS_SUBMITTED
    if commercially_committed:
        commitment_message = (
            "Commercial Offer lifecycle is Submitted. Customer sharing and commercial commitment are recorded for traceability."
        )
    elif submission_evidence:
        commitment_message = (
            "Submission evidence is recorded, but the offer has not yet been recorded as submitted."
        )
    else:
        commitment_message = (
            "Commercial commitment is not recorded. Add submission evidence before using the controlled Record as Submitted action."
        )
    items.append(
        _submission_readiness_item(
            code="COMMERCIAL_COMMITMENT_STATUS",
            label="Recorded as submitted",
            status="PASS" if commercially_committed else "ATTENTION_REQUIRED",
            severity="INFO" if commercially_committed else "WARNING",
            message=commitment_message,
            evidence={
                "offer_status_code": commercial_offer.offer_status_code,
                "commercially_committed": commercially_committed,
                "submission_evidence_count": len(submission_evidence),
            },
        )
    )

    latest_revision = revisions[0] if revisions else None
    open_revision_attention = bool(
        commercially_committed
        and latest_revision
        and latest_revision.revision_status == COMMERCIAL_OFFER_REVISION_STATUS_OPEN
    )
    if open_revision_attention:
        revision_message = "A revised offer is in progress and has not been re-sent yet."
    elif latest_revision and latest_revision.revision_status == COMMERCIAL_OFFER_REVISION_STATUS_RESUBMITTED:
        revision_message = "The latest revised offer has been re-sent, with evidence."
    elif latest_revision and latest_revision.revision_status == COMMERCIAL_OFFER_REVISION_STATUS_CANCELLED:
        revision_message = "The latest revised offer was cancelled, so nothing needs to be re-sent for it."
    else:
        revision_message = "No revised offer has been started."
    items.append(
        _submission_readiness_item(
            code="REVISION_RESUBMISSION_TRACEABILITY",
            label="Revised offers",
            status="ATTENTION_REQUIRED" if open_revision_attention else "PASS",
            severity="WARNING" if open_revision_attention else "INFO",
            message=revision_message,
            evidence={
                "latest_revision_public_id": str(latest_revision.public_id) if latest_revision else None,
                "latest_revision_label": latest_revision.revision_label if latest_revision else None,
                "latest_revision_status": latest_revision.revision_status if latest_revision else None,
                "resubmission_evidence_public_id": (
                    str(latest_revision.resubmission_evidence_public_id)
                    if latest_revision and latest_revision.resubmission_evidence_public_id
                    else None
                ),
                "traceability_only": True,
                "hard_lifecycle_block": False,
            },
        )
    )

    latest_customer_response = customer_responses[0] if customer_responses else None
    response_attention = False
    if latest_customer_response is None:
        response_message = (
            "Customer response / award outcome not yet recorded."
            if commercial_offer.offer_status_code == COMMERCIAL_OFFER_STATUS_SUBMITTED
            else "No customer response / award outcome is recorded."
        )
    elif latest_customer_response.response_outcome == COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_ACCEPTED_AWARDED:
        response_message = "Customer response recorded as accepted/awarded."
    elif latest_customer_response.response_outcome == COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REJECTED_LOST:
        response_message = "Customer response recorded as rejected/lost."
    elif latest_customer_response.response_outcome in {
        COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_REVISION_REQUESTED,
        COMMERCIAL_OFFER_CUSTOMER_RESPONSE_OUTCOME_CLARIFICATION_REQUESTED,
    }:
        response_attention = True
        response_message = "Customer requested revision/clarification."
    else:
        response_message = "Latest customer response / award outcome is recorded for traceability."
    items.append(
        _submission_readiness_item(
            code="CUSTOMER_RESPONSE_AWARD_OUTCOME",
            label="Customer response / award outcome",
            status="ATTENTION_REQUIRED" if response_attention else "PASS",
            severity="WARNING" if response_attention else "INFO",
            message=response_message,
            evidence={
                "customer_response_count": len(customer_responses),
                "latest_customer_response_public_id": (
                    str(latest_customer_response.public_id) if latest_customer_response else None
                ),
                "latest_response_outcome": latest_customer_response.response_outcome if latest_customer_response else None,
                "hard_lifecycle_block": False,
                "work_order_created": False,
            },
        )
    )

    items.append(
        _submission_readiness_item(
            code="ACCOUNT_TRACEABILITY",
            label="Linked to an Account",
            status="PASS" if commercial_offer.account_public_id else "BLOCKING",
            severity="INFO" if commercial_offer.account_public_id else "BLOCKING",
            message=(
                "The offer's Opportunity is linked to an Account."
                if commercial_offer.account_public_id
                else "The offer's Opportunity is not linked to an Account. The offer cannot be submitted or accepted until it is."
            ),
            evidence={"account_public_id": str(commercial_offer.account_public_id) if commercial_offer.account_public_id else None},
        )
    )

    items.append(
        _submission_readiness_item(
            code="OPPORTUNITY_TRACEABILITY",
            label="Linked to an Opportunity",
            status="PASS" if commercial_offer.opportunity_public_id else "BLOCKING",
            severity="INFO" if commercial_offer.opportunity_public_id else "BLOCKING",
            message=(
                "This offer is linked to an Opportunity."
                if commercial_offer.opportunity_public_id
                else "This offer is not linked to an Opportunity."
            ),
            evidence={"opportunity_public_id": str(commercial_offer.opportunity_public_id) if commercial_offer.opportunity_public_id else None},
        )
    )

    items.append(
        _submission_readiness_item(
            code="COMMERCIAL_OFFER_LINES",
            label="Commercial Offer active lines",
            status="PASS" if active_lines else "BLOCKING",
            severity="INFO" if active_lines else "BLOCKING",
            message=(
                f"{len(active_lines)} active Commercial Offer line(s) are available."
                if active_lines
                else "No active Commercial Offer lines are available for customer-facing submission readiness."
            ),
            evidence={
                "active_line_count": len(active_lines),
                "total_line_count": len(offer_lines),
                "active_line_public_ids": [str(line.public_id) for line in active_lines],
            },
        )
    )

    # Slice 4G: each active line is checked for its own market rates and basis rate. This warns; it never blocks
    # recording the offer as sent (owner, 11 October 2026). Rates recorded for the whole offer before then count for
    # no line.
    lines_without_rates = [
        line.line_number
        for line in active_lines
        if not any(str(rate.line_public_id) == str(line.public_id) for rate in pricing_evidence)
    ]
    lines_without_basis = [
        line.line_number
        for line in active_lines
        if line.line_number not in lines_without_rates
        and not any(str(rate.line_public_id) == str(line.public_id) for rate in selected_pricing_evidence)
    ]
    pricing_gaps = []
    if lines_without_rates:
        pricing_gaps.append(f"No market rate on line(s) {_line_numbers(lines_without_rates)}.")
    if lines_without_basis:
        pricing_gaps.append(f"No basis rate chosen on line(s) {_line_numbers(lines_without_basis)}.")
    items.append(
        _submission_readiness_item(
            code="PRICING_EVIDENCE",
            label="Market rates and basis rate on each line",
            status="ATTENTION_REQUIRED" if pricing_gaps or not active_lines else "PASS",
            severity="WARNING" if pricing_gaps or not active_lines else "INFO",
            message=(
                " ".join(pricing_gaps)
                + " This does not block anything, but check it before sending the offer to the customer."
                if pricing_gaps
                else (
                    "Every active line has market rates and a chosen basis rate."
                    if active_lines
                    else "There are no active lines to check for market rates."
                )
            ),
            evidence={
                "pricing_evidence_count": len(pricing_evidence),
                "selected_pricing_evidence_public_ids": [str(item.public_id) for item in selected_pricing_evidence],
                "lines_without_rates": lines_without_rates,
                "lines_without_basis": lines_without_basis,
            },
        )
    )

    items.append(
        _submission_readiness_item(
            code="SUBMISSION_EVIDENCE",
            label="Submission evidence recorded",
            status="PASS" if submission_evidence else "ATTENTION_REQUIRED",
            severity="INFO" if submission_evidence else "WARNING",
            message=(
                f"{len(submission_evidence)} submission evidence record(s) are available."
                if submission_evidence
                else "No submission evidence metadata is recorded yet. Record metadata when the Commercial Offer, customer-format quote or tender bid is shared with the customer."
            ),
            evidence={
                "submission_evidence_count": len(submission_evidence),
                "latest_submission_evidence_public_id": str(submission_evidence[0].public_id)
                if submission_evidence
                else None,
                "latest_submission_channel": submission_evidence[0].submission_channel if submission_evidence else None,
                "latest_submitted_at": submission_evidence[0].submitted_at.isoformat()
                if submission_evidence
                else None,
            },
        )
    )

    credit_review_status = current_credit_review.review_status if current_credit_review else None
    credit_review_pass = credit_review_status in {
        COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_WITHIN_LIMIT,
        COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVED,
    }
    credit_review_blocking = credit_review_status == COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_REJECTED_OR_ON_HOLD
    if current_credit_review is None:
        credit_review_message = (
            "Manual credit/exposure review has not yet been recorded. Actual exposure calculation and PAN-level credit-limit consumption remain future work."
        )
    elif credit_review_pass:
        credit_review_message = (
            f"Latest manual credit/exposure review is {credit_review_status}. This is readiness evidence only; no exposure calculation was performed."
        )
    elif credit_review_blocking:
        credit_review_message = (
            "Latest manual credit/exposure review is rejected or on hold. This is a blocking-style advisory only and does not change lifecycle status."
        )
    elif credit_review_status == COMMERCIAL_OFFER_CREDIT_REVIEW_STATUS_APPROVAL_REQUIRED:
        credit_review_message = (
            "Latest manual credit/exposure review says approval is required. Finance approval workflow and exposure calculation are not implemented."
        )
    else:
        credit_review_message = (
            "Latest manual credit/exposure review is not assessed. Actual exposure calculation and PAN-level credit-limit consumption remain future work."
        )

    items.append(
        _submission_readiness_item(
            code="CREDIT_EXPOSURE_REVIEW",
            label="Manual credit/exposure review",
            status="PASS" if credit_review_pass else "BLOCKING" if credit_review_blocking else "ATTENTION_REQUIRED",
            severity="INFO" if credit_review_pass else "BLOCKING" if credit_review_blocking else "WARNING",
            message=credit_review_message,
            evidence={
                "credit_review_public_id": str(current_credit_review.public_id) if current_credit_review else None,
                "review_status": credit_review_status,
                "review_reference": current_credit_review.review_reference if current_credit_review else None,
                "reviewed_at": current_credit_review.reviewed_at.isoformat() if current_credit_review else None,
                "approved_amount_snapshot": str(current_credit_review.approved_amount_snapshot)
                if current_credit_review and current_credit_review.approved_amount_snapshot is not None
                else None,
                "credit_days_snapshot": current_credit_review.credit_days_snapshot if current_credit_review else None,
                "manual_review_only": True,
                "exposure_calculation_implemented": False,
            },
        )
    )

    tc_basis_missing = tc_readiness.recommendation_basis is None
    tc_missing = tc_readiness.missing_recommended_count > 0
    tc_has_recommended = tc_readiness.total_recommended_count > 0
    tc_attention = tc_basis_missing or tc_missing or not tc_has_recommended
    items.append(
        _submission_readiness_item(
            code="HEADER_TC_READINESS",
            label="Header T&C readiness",
            status="ATTENTION_REQUIRED" if tc_attention else "PASS",
            severity="WARNING" if tc_attention else "INFO",
            message=(
                "Select a recommendation basis to assess recommended header T&C clauses."
                if tc_basis_missing
                else tc_readiness.status_text
            ),
            evidence={
                "recommendation_basis": tc_readiness.recommendation_basis,
                "total_recommended_count": tc_readiness.total_recommended_count,
                "attached_recommended_count": tc_readiness.attached_recommended_count,
                "missing_recommended_count": tc_readiness.missing_recommended_count,
                "attached_optional_count": tc_readiness.attached_optional_count,
            },
        )
    )

    # Slice 9E - Quotation Generation. Both rows below are advisory, matching this checklist's
    # existing convention: nothing here hard-blocks any other lifecycle action.
    quote_documents = list_commercial_offer_quote_documents_for_offer(db, commercial_offer_id=commercial_offer_id)
    approved_quote_documents = [
        quote_document
        for quote_document in quote_documents
        if quote_document["quote_status_code"] == COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_APPROVED_FOR_ISSUE
        and quote_document.get("superseded_at") is None
    ]
    items.append(
        _submission_readiness_item(
            code="QUOTATION_DOCUMENT",
            label="Quotation document approved for issue",
            status="PASS" if approved_quote_documents else "ATTENTION_REQUIRED",
            severity="INFO" if approved_quote_documents else "WARNING",
            message=(
                f"An approved quotation document is available ({approved_quote_documents[0]['quote_reference']})."
                if approved_quote_documents
                else "No quotation document has been generated and approved for issue yet."
            ),
            evidence={
                "quote_document_count": len(quote_documents),
                "approved_quote_document_count": len(approved_quote_documents),
                "latest_approved_quote_reference": approved_quote_documents[0]["quote_reference"]
                if approved_quote_documents
                else None,
                "approval_is_a_procedural_control_not_an_access_control": True,
            },
        )
    )

    # This is the FRD row (source line 855: "capture all communications ... in a time-stamped
    # log before a quote can be raised") that Slice 9D deliberately deferred out of its own
    # package - see docs/agent/contracts/interaction-contract.md, "Explicitly out of scope for
    # v1.0": "Hard enforcement of the FRD logging rule before quoting - after the pilot habit
    # forms." Advisory only, exactly as that contract records; it does not block generation,
    # approval or anything else.
    interaction_count = count_interactions_in_commercial_offer_chain(
        db,
        commercial_offer_public_id=str(public_id),
        opportunity_public_id=str(commercial_offer.opportunity_public_id)
        if commercial_offer.opportunity_public_id
        else None,
        account_public_id=str(commercial_offer.account_public_id) if commercial_offer.account_public_id else None,
    )
    items.append(
        _submission_readiness_item(
            code="INTERACTION_LOG",
            label="Customer communications logged",
            status="PASS" if interaction_count > 0 else "ATTENTION_REQUIRED",
            severity="INFO" if interaction_count > 0 else "WARNING",
            message=(
                f"{interaction_count} conversation(s) are logged against this offer or its linked Opportunity/Account."
                if interaction_count > 0
                else (
                    "No conversation has been logged yet. PBL's process expects conversations to be logged before a "
                    "quote is raised; this is advisory guidance while the pilot habit forms, not a hard block."
                )
            ),
            evidence={"interaction_count": interaction_count, "hard_block": False},
        )
    )

    for code, label, message in COMMERCIAL_OFFER_SUBMISSION_READINESS_DEFERRED_ITEMS:
        items.append(
            _submission_readiness_item(
                code=code,
                label=label,
                status="DEFERRED",
                severity="DEFERRED",
                message=message,
                deferred=True,
            )
        )

    passed_count = sum(1 for item in items if item.status == "PASS")
    warning_count = sum(1 for item in items if item.severity == "WARNING")
    blocking_count = sum(1 for item in items if item.severity == "BLOCKING")
    deferred_count = sum(1 for item in items if item.deferred)

    return CommercialOfferSubmissionReadinessResponse(
        commercial_offer_public_id=public_id,
        readiness_status=_submission_readiness_status(
            blocking_count=blocking_count,
            warning_count=warning_count,
        ),
        summary=CommercialOfferSubmissionReadinessSummaryResponse(
            passed_count=passed_count,
            warning_count=warning_count,
            blocking_count=blocking_count,
            deferred_count=deferred_count,
        ),
        checklist_items=items,
    )
