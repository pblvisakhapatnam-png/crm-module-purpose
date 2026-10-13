"""What more than one Commercial Offer concern needs: the module's exceptions, and the helpers several
concerns share.

The exceptions are the Commercial Offer module's error vocabulary - routes.py maps each to an HTTP
status - so they stay together here even where only one concern raises them. Everything else is here
because more than one concern calls it: reading an offer, the lock every change to an offer's content
takes, the text, value, currency and date checks, the Account traceability guard, the evidence a revision
or a customer response cites, and the T&C readiness view, which the T&C clauses and the submission
readiness checklist both read. A helper one concern alone uses lives with that concern. Since CS-05c, also how a
duplicate the database refused is answered, which four concerns share.

Everything was moved, not changed, so that splitting the service changed no function's body (CS-11).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from decimal import Decimal
from typing import Any, NoReturn
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import database_error_fields
from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
    COMMERCIAL_OFFER_STATUS_SUBMITTED,
    COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES,
    COMMERCIAL_OFFER_PRE_SUBMISSION_STATUSES,
)
from app.modules.commercial_offers.repository import (
    get_commercial_offer_by_public_id,
    get_commercial_offer_context_by_public_id,
    get_commercial_offer_version_context,
    get_open_commercial_offer_revision_for_offer,
    get_submission_evidence_context_for_offer,
    lock_commercial_offer_row,
    list_active_commercial_offer_tc_clause_attachment_contexts,
    list_recommended_tc_clause_contexts,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferTcClauseReadinessClauseResponse,
    CommercialOfferTcClauseReadinessResponse,
    CommercialOfferResponse,
)

from app.shared.currency import operating_currency

logger = logging.getLogger(__name__)


class CommercialOfferValidationError(ValueError):
    pass


class CommercialOfferNotFoundError(LookupError):
    pass


class CommercialOfferOpportunityNotFoundError(LookupError):
    pass


class CommercialOfferRevisionNotFoundError(LookupError):
    pass


class CommercialOfferQuoteDocumentNotFoundError(LookupError):
    pass


class CommercialOfferPricingEvidenceNotFoundError(LookupError):
    pass


class CommercialOfferLineNotFoundError(LookupError):
    pass


class CommercialOfferTcClauseNotFoundError(LookupError):
    pass


class CommercialOfferConflictError(ValueError):
    """A save sent with a version the record no longer has: someone else saved it after the form was opened
    (CS-05a, TB-1 finding TB1-303). routes.py answers it with 409."""


COMMERCIAL_OFFER_ACCOUNT_TRACEABILITY_REQUIRED_STATUSES = {
    COMMERCIAL_OFFER_STATUS_SUBMITTED,
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
}


COMMERCIAL_OFFER_TC_RECOMMENDATION_BASIS_ALIASES = {
    "TRANSPORT": "TRANSPORTATION",
    "TRANSPORTATION": "TRANSPORTATION",
    "HIRING": "HIRING",
    "HIRE": "HIRING",
    "EQUIPMENT_HIRING": "HIRING",
    "EQUIPMENT HIRING": "HIRING",
    "EQUIPMENT HIRE": "HIRING",
}


COMMERCIAL_OFFER_TC_READINESS_DEFERRAL_NOTES = [
    "This readiness view is guidance only. It is not legal approval.",
    "Line-level T&C selection, omitted mandatory-clause approval, clause editing and quote/PDF generation are deferred.",
    "Commercial Offer T&C readiness does not release, post, execute or bill any Work Order.",
]


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_code(value: str | None, default: str) -> str:
    return (value or default).strip().upper()


def _normalize_lower(value: str | None, default: str) -> str:
    return (value or default).strip().lower()


def _event_dict(event: object) -> dict[str, object | None]:
    return {
        "public_id": getattr(event, "public_id", None),
        "event_name": getattr(event, "event_name", None),
        "record_type": getattr(event, "record_type", None),
        "record_public_id": getattr(event, "record_public_id", None),
        "status_before": getattr(event, "status_before", None),
        "status_after": getattr(event, "status_after", None),
        "event_payload": getattr(event, "event_payload", None),
    }


def _validate_offer_value(value: Decimal | None) -> Decimal | None:
    if value is not None and value < Decimal("0"):
        raise CommercialOfferValidationError("Offer value cannot be negative.")
    return value


def _validate_currency(value: str | None) -> str:
    try:
        return operating_currency(value)
    except ValueError as exc:
        raise CommercialOfferValidationError(str(exc)) from exc


def _validate_dates(offer_date: object | None, valid_until: object | None) -> None:
    if offer_date and valid_until and valid_until < offer_date:
        raise CommercialOfferValidationError("Valid until date cannot be earlier than offer date.")


def _ensure_account_traceability_for_lifecycle_action(
    *,
    commercial_offer: CommercialOfferResponse,
    target_status: str | None,
) -> None:
    if target_status not in COMMERCIAL_OFFER_ACCOUNT_TRACEABILITY_REQUIRED_STATUSES:
        return

    if commercial_offer.account_public_id:
        return

    raise CommercialOfferValidationError(
        "Commercial Offer cannot be submitted or accepted until Account traceability is available through the linked "
        "Opportunity. Create or repair a minimal/provisional Account / Qualified Prospect through the existing "
        "Lead, Opportunity and Account flow before continuing."
    )


def _lock_offer_for_content_change(db: Session, public_id: UUID) -> dict[str, Any]:
    """Lock the offer and allow content changes only while this row is in preparation.

    An offer's lines, pricing evidence and basis rate, T&C clauses, credit reviews and submission evidence stay as
    they were once this row is sent. Later customer-facing changes belong on a copied Commercial Offer version;
    changes after an award belong on a Work Order amendment or Change Quotation. The lock comes first, as for every
    write that reads the offer's status, so a change waiting behind submission or a customer outcome sees the new
    status and is refused (Slice 9F).

    Returns the offer's context, as get_commercial_offer_context_by_public_id gives it.
    """
    if lock_commercial_offer_row(db, public_id=str(public_id)) is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    status = str(commercial_offer_context["offer_status_code"])
    status_label = status.replace("_", " ").title()
    if status not in COMMERCIAL_OFFER_PRE_SUBMISSION_STATUSES:
        raise CommercialOfferValidationError(
            f"This Commercial Offer is {status_label}, so its lines, prices, T&C, credit reviews and submission "
            "evidence can no longer change on this version. Use Make a new version for a customer-facing change; a change after an award "
            "goes on a Work Order amendment or Change Quotation."
        )
    return commercial_offer_context


def _ensure_no_preparation_version(db: Session, commercial_offer: CommercialOfferResponse) -> None:
    context = get_commercial_offer_version_context(db, public_id=str(commercial_offer.public_id))
    if context and context.get("preparation_offer_public_id"):
        raise CommercialOfferValidationError(
            "A newer Commercial Offer version is being prepared. Abandon it or send it before recording a customer "
            "response, withdrawing or closing the sent version."
        )


def _refuse_duplicate(exc: IntegrityError, refusals: dict[str, Callable[[], Exception]]) -> NoReturn:
    """Answer a duplicate the database refused - two requests made at once - with the module's own refusal (TB-1
    finding TB1-304; CS-05c), never a server error.

    `refusals` maps each rule's name to what makes its refusal; an error on any other rule, or of any other kind, is
    raised as it came. The caller has rolled the session back, so a refusal may read again to name what holds the place
    now. Logged by what identifies the rule - its name, the table, the SQLSTATE - never by the database's message,
    whose DETAIL repeats the duplicated key (CODING_STANDARDS.md section 9).
    """
    refusal = refusals.get(getattr(getattr(exc.orig, "diag", None), "constraint_name", None))
    if refusal is None:
        raise exc
    logger.warning("A Commercial Offer write met a duplicate made at the same time: %s", database_error_fields(exc))
    raise refusal() from None


def get_commercial_offer(db: Session, public_id: UUID) -> CommercialOfferResponse:
    commercial_offer = get_commercial_offer_by_public_id(db, str(public_id))
    if commercial_offer is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    return commercial_offer


def _revision_evidence_context(
    db: Session,
    *,
    commercial_offer_id: int,
    evidence_public_id: UUID | None,
    field_label: str,
) -> dict[str, object] | None:
    if evidence_public_id is None:
        return None
    context = get_submission_evidence_context_for_offer(
        db,
        commercial_offer_id=commercial_offer_id,
        public_id=str(evidence_public_id),
    )
    if context is None:
        raise CommercialOfferValidationError(
            f"{field_label} must identify an existing active submission evidence record for this Commercial Offer."
        )
    return context


def _validate_required_text(value: str | None, field_label: str) -> str:
    cleaned = _clean_optional(value)
    if not cleaned:
        raise CommercialOfferValidationError(f"{field_label} is required.")
    return cleaned


def normalize_tc_recommendation_basis(value: str | None) -> str | None:
    cleaned = _clean_optional(value)
    if cleaned is None:
        return None
    normalized = cleaned.upper().replace("-", "_").strip()
    normalized = " ".join(normalized.split())
    normalized = normalized.replace(" ", "_")
    if normalized in COMMERCIAL_OFFER_TC_RECOMMENDATION_BASIS_ALIASES:
        return COMMERCIAL_OFFER_TC_RECOMMENDATION_BASIS_ALIASES[normalized]

    spaced = normalized.replace("_", " ")
    if spaced in COMMERCIAL_OFFER_TC_RECOMMENDATION_BASIS_ALIASES:
        return COMMERCIAL_OFFER_TC_RECOMMENDATION_BASIS_ALIASES[spaced]

    raise CommercialOfferValidationError("Recommendation basis must be TRANSPORTATION or HIRING.")


def _tc_readiness_status_text(
    *,
    recommendation_basis: str | None,
    total_recommended_count: int,
    missing_recommended_count: int,
) -> str:
    if recommendation_basis is None:
        return "Select a recommendation basis to compare attached clauses with the recommended clause list."
    if total_recommended_count == 0:
        return f"No active header-level recommended clauses are available for {recommendation_basis}."
    if missing_recommended_count == 0:
        return f"All recommended {recommendation_basis} header-level clauses are attached."
    return f"{missing_recommended_count} recommended {recommendation_basis} header-level clause(s) are not yet attached."


def get_commercial_offer_tc_clause_readiness(
    db: Session,
    *,
    public_id: UUID,
    recommendation_basis: str | None,
) -> CommercialOfferTcClauseReadinessResponse:
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    normalized_basis = normalize_tc_recommendation_basis(recommendation_basis)
    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])
    attachment_contexts = list_active_commercial_offer_tc_clause_attachment_contexts(
        db,
        commercial_offer_id=commercial_offer_id,
    )
    attachments_by_clause_id = {int(row["tc_clause_id"]): row for row in attachment_contexts}
    attached_optional_count = sum(1 for row in attachment_contexts if not bool(row["mandatory_default_snapshot"]))

    recommended_contexts = (
        list_recommended_tc_clause_contexts(db, recommendation_basis=normalized_basis) if normalized_basis else []
    )
    readiness_clauses: list[CommercialOfferTcClauseReadinessClauseResponse] = []

    for clause in recommended_contexts:
        attachment = attachments_by_clause_id.get(int(clause["tc_clause_id"]))
        readiness_clauses.append(
            CommercialOfferTcClauseReadinessClauseResponse(
                tc_clause_public_id=clause["public_id"],
                clause_id=clause["clause_id"],
                title=clause["title"],
                clause_text=clause["clause_text"],
                business_line=clause["business_line"],
                clause_category=clause["clause_category"],
                source_clause_number=clause.get("source_clause_number"),
                mandatory_default=bool(clause["mandatory_default"]),
                risk_category=clause.get("risk_category"),
                applies_to_header=bool(clause["applies_to_header"]),
                applies_to_line=bool(clause["applies_to_line"]),
                requires_approval_if_omitted=bool(clause["requires_approval_if_omitted"]),
                requires_approval_if_modified=bool(clause["requires_approval_if_modified"]),
                active=bool(clause["active"]),
                source_reference=clause.get("source_reference"),
                status="ATTACHED" if attachment else "NOT_ATTACHED",
                attachment_public_id=attachment["public_id"] if attachment else None,
            )
        )

    attached_recommended_count = sum(1 for clause in readiness_clauses if clause.status == "ATTACHED")
    total_recommended_count = len(readiness_clauses)
    missing_recommended_count = total_recommended_count - attached_recommended_count

    return CommercialOfferTcClauseReadinessResponse(
        commercial_offer_public_id=public_id,
        recommendation_basis=normalized_basis,
        total_recommended_count=total_recommended_count,
        attached_recommended_count=attached_recommended_count,
        missing_recommended_count=missing_recommended_count,
        attached_optional_count=attached_optional_count,
        status_text=_tc_readiness_status_text(
            recommendation_basis=normalized_basis,
            total_recommended_count=total_recommended_count,
            missing_recommended_count=missing_recommended_count,
        ),
        deferral_notes=COMMERCIAL_OFFER_TC_READINESS_DEFERRAL_NOTES,
        recommended_clauses=readiness_clauses,
    )
