"""Rate basis and pricing evidence (Slice 4D), kept per offer line with each line's basis history (Slice 4G)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_ALLOWED_PRICING_EVIDENCE_TYPES,
    COMMERCIAL_OFFER_EVENT_BASIS_RATE_SELECTED,
    COMMERCIAL_OFFER_EVENT_HISTORICAL_RATE_ADDED,
    COMMERCIAL_OFFER_EVENT_MARKET_RATE_ADDED,
    COMMERCIAL_OFFER_LINE_STATUS_ACTIVE,
    COMMERCIAL_OFFER_MARKET_RATE_DOCUMENT_TYPE,
    COMMERCIAL_OFFER_MARKET_RATE_RECORD_TYPE,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_ONE_OPEN_BASIS_CHOICE_INDEX,
    COMMERCIAL_OFFER_RECORD_TYPE,
)
from app.modules.commercial_offers.repository import (
    choose_line_basis_rate,
    get_commercial_offer_context_by_public_id,
    get_commercial_offer_line_context,
    get_pricing_evidence_by_public_id,
    get_pricing_evidence_context,
    insert_pricing_evidence,
    list_basis_choices_for_rates,
    list_pricing_evidence_for_offer,
    list_quote_copy_holders_for_rates,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferLineBasisChoiceResponse,
    CommercialOfferMarketRateQuoteCopy,
    CommercialOfferPricingEvidenceBasisSelection,
    CommercialOfferPricingEvidenceCreate,
    CommercialOfferPricingEvidenceCreatedResponse,
    CommercialOfferPricingEvidenceResponse,
    CommercialOfferPricingEvidenceSelectedResponse,
)
from app.modules.documents.contract import STORAGE_MODE_LOCAL_UPLOAD
from app.modules.documents.service import AttachRequest, documents_linked_to_records, register_attach_check
from app.modules.events.service import record_business_event

from app.modules.commercial_offers.services.common import (
    CommercialOfferConflictError,
    CommercialOfferNotFoundError,
    CommercialOfferPricingEvidenceNotFoundError,
    CommercialOfferValidationError,
    _clean_optional,
    _event_dict,
    _lock_offer_for_content_change,
    _normalize_lower,
    _refuse_duplicate,
    _validate_currency,
    _validate_required_text,
)


def _chosen_at_the_same_time() -> CommercialOfferConflictError:
    return CommercialOfferConflictError(
        "Someone else chose a basis rate for this line at the same time, so yours was not saved. Reload the page to "
        "see which rate is selected, then choose again if you still need to."
    )


# A selection made at the same time as another one by a writer that does not take the offer's lock (CS-05c, TB-1
# TB1-304): the line keeps one current choice, which is its basis (Slice 4G), and this request is told to look again.
_SELECTED_AT_THE_SAME_TIME = {COMMERCIAL_OFFER_ONE_OPEN_BASIS_CHOICE_INDEX: _chosen_at_the_same_time}


def _normalize_pricing_evidence_type(value: str | None) -> str:
    evidence_type = _normalize_lower(value, "market_rate")
    if evidence_type not in COMMERCIAL_OFFER_ALLOWED_PRICING_EVIDENCE_TYPES:
        raise CommercialOfferValidationError(f"Pricing evidence type is not allowed: {value}")
    return evidence_type


def _validate_rate_amount(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        raise CommercialOfferValidationError("Rate amount cannot be negative.")
    return value


def _normalize_pricing_evidence_payload(
    payload: CommercialOfferPricingEvidenceCreate,
    current_user_public_id: str | None,
) -> dict[str, object | None]:
    evidence_type = _normalize_pricing_evidence_type(payload.evidence_type)
    selection_reason = _clean_optional(payload.selection_reason)
    is_selected_basis = bool(payload.is_selected_basis)

    if is_selected_basis and not selection_reason:
        raise CommercialOfferValidationError("Selection reason is required when adding an entry as the selected basis rate.")

    return {
        "evidence_type": evidence_type,
        "source_name": _clean_optional(payload.source_name),
        "vendor_contact": _clean_optional(payload.vendor_contact),
        "equipment_service_description": _validate_required_text(
            payload.equipment_service_description,
            "Equipment / service description",
        ),
        "rate_amount": _validate_rate_amount(payload.rate_amount),
        "currency_code": _validate_currency(payload.currency_code),
        "rate_basis": _validate_required_text(payload.rate_basis, "Rate basis"),
        "collected_by_name": _clean_optional(payload.collected_by_name),
        "collected_at": payload.collected_at,
        "source_reference": _clean_optional(payload.source_reference),
        "is_selected_basis": is_selected_basis,
        "selection_reason": selection_reason,
        "comparison_notes": _clean_optional(payload.comparison_notes),
        "created_by": current_user_public_id,
    }


def _pricing_evidence_added_event_name(evidence_type: str) -> str:
    if evidence_type == "historical_plum_rate":
        return COMMERCIAL_OFFER_EVENT_HISTORICAL_RATE_ADDED
    return COMMERCIAL_OFFER_EVENT_MARKET_RATE_ADDED


def _line_for_new_rate(db: Session, *, commercial_offer_id: int, line_public_id: UUID | None) -> dict[str, Any]:
    """The active line of this offer that a new rate is for (Slice 4G)."""
    if line_public_id is None:
        raise CommercialOfferValidationError("Choose the offer line this rate is for.")
    line = get_commercial_offer_line_context(
        db, commercial_offer_id=commercial_offer_id, line_public_id=str(line_public_id), for_update=True
    )
    if line is None:
        raise CommercialOfferValidationError("That line is not a line of this Commercial Offer.")
    if line["line_status_code"] != COMMERCIAL_OFFER_LINE_STATUS_ACTIVE:
        raise CommercialOfferValidationError(
            f"Line {line['line_number']} is cancelled, so no rate can be added to it. Its rates are kept as history."
        )
    return line


def _rates_with_a_quote_copy(db: Session, evidence_public_ids: list[str]) -> set[str]:
    """Which of these market rates have a quote copy: an attached VENDOR_QUOTE on the rate itself or on a rate it refers
    to, not rejected or archived (Slice 4G). A new rate may refer only to such a rate (review 4G-R1-004)."""
    holders = list_quote_copy_holders_for_rates(db, evidence_public_ids=evidence_public_ids)
    attached = {
        str(document["linked_record_public_id"])
        for document in documents_linked_to_records(
            db,
            linked_record_type=COMMERCIAL_OFFER_MARKET_RATE_RECORD_TYPE,
            linked_record_public_ids=sorted({str(holder["holder_public_id"]) for holder in holders}),
            document_type=COMMERCIAL_OFFER_MARKET_RATE_DOCUMENT_TYPE,
        )
    }
    return {str(holder["rate_public_id"]) for holder in holders if str(holder["holder_public_id"]) in attached}


def _quote_copy_rate(db: Session, *, commercial_offer_id: int, rate_public_id: UUID | None) -> dict[str, Any] | None:
    """Another rate of this offer whose attached document also holds the new rate's quote (Slice 4G)."""
    if rate_public_id is None:
        return None
    rate = get_pricing_evidence_context(
        db, commercial_offer_id=commercial_offer_id, evidence_public_id=str(rate_public_id)
    )
    if rate is None:
        raise CommercialOfferValidationError("The rate named for the quote copy is not a rate of this Commercial Offer.")
    if str(rate_public_id) not in _rates_with_a_quote_copy(db, [str(rate_public_id)]):
        raise CommercialOfferValidationError(
            "The rate named for the quote copy has no quote attached yet. Attach the quote to that rate first."
        )
    return rate


def _line_reference(line: dict[str, Any]) -> dict[str, object]:
    return {"line_public_id": str(line["line_public_id"]), "line_number": line["line_number"]}


def _with_history_and_quote_copies(
    db: Session, rates: list[CommercialOfferPricingEvidenceResponse]
) -> list[CommercialOfferPricingEvidenceResponse]:
    """Each rate with its basis history and the documents holding its quote (Slice 4G)."""
    rate_ids = [str(rate.public_id) for rate in rates]
    choices: dict[str, list[CommercialOfferLineBasisChoiceResponse]] = {}
    for row in list_basis_choices_for_rates(db, evidence_public_ids=rate_ids):
        choices.setdefault(str(row["pricing_evidence_public_id"]), []).append(
            CommercialOfferLineBasisChoiceResponse(**row, is_current=row["ended_at"] is None)
        )

    holders = list_quote_copy_holders_for_rates(db, evidence_public_ids=rate_ids)
    documents: dict[str, list[dict[str, Any]]] = {}
    for document in documents_linked_to_records(
        db,
        linked_record_type=COMMERCIAL_OFFER_MARKET_RATE_RECORD_TYPE,
        linked_record_public_ids=sorted({str(holder["holder_public_id"]) for holder in holders}),
        document_type=COMMERCIAL_OFFER_MARKET_RATE_DOCUMENT_TYPE,
    ):
        documents.setdefault(str(document["linked_record_public_id"]), []).append(document)
    quote_copies: dict[str, list[CommercialOfferMarketRateQuoteCopy]] = {}
    for holder in holders:
        for document in documents.get(str(holder["holder_public_id"]), []):
            quote_copies.setdefault(str(holder["rate_public_id"]), []).append(
                CommercialOfferMarketRateQuoteCopy(
                    document_public_id=document["document_public_id"],
                    file_name=document["file_name"],
                    uploaded_at=document["uploaded_at"].isoformat() if document.get("uploaded_at") else None,
                    attached_to_rate_public_id=holder["holder_public_id"],
                    attached_to_line_number=holder["holder_line_number"],
                    attached_to_offer_version_number=holder["holder_offer_version_number"],
                    attached_here=holder["depth"] == 0,
                )
            )

    return [
        rate.model_copy(
            update={
                "basis_history": choices.get(str(rate.public_id), []),
                "quote_copies": quote_copies.get(str(rate.public_id), []),
            }
        )
        for rate in rates
    ]


def _reload_rate(db: Session, evidence_public_id: str) -> CommercialOfferPricingEvidenceResponse:
    evidence = get_pricing_evidence_by_public_id(db, evidence_public_id)
    if evidence is None:
        raise RuntimeError("Commercial Offer pricing evidence could not be reloaded.")
    return _with_history_and_quote_copies(db, [evidence])[0]


def list_commercial_offer_pricing_evidence(
    db: Session,
    public_id: UUID,
) -> list[CommercialOfferPricingEvidenceResponse]:
    commercial_offer_context = get_commercial_offer_context_by_public_id(db, str(public_id))
    if commercial_offer_context is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    return _with_history_and_quote_copies(
        db,
        list_pricing_evidence_for_offer(
            db,
            commercial_offer_id=int(commercial_offer_context["commercial_offer_id"]),
        ),
    )


def _record_basis_selected(
    db: Session,
    *,
    public_id: UUID,
    commercial_offer_context: dict[str, Any],
    evidence: CommercialOfferPricingEvidenceResponse,
    line: dict[str, Any],
    selection_reason: str,
    previous_rate_public_id: str | None,
    current_user_public_id: str | None,
    reason: str,
):
    return record_business_event(
        db,
        event_name=COMMERCIAL_OFFER_EVENT_BASIS_RATE_SELECTED,
        source_module=COMMERCIAL_OFFER_MODULE_NAME,
        record_type=COMMERCIAL_OFFER_RECORD_TYPE,
        record_public_id=str(public_id),
        user_public_id=current_user_public_id,
        status_before=None,
        status_after=str(commercial_offer_context["offer_status_code"]),
        reason=reason,
        event_payload={
            "offer_code": commercial_offer_context.get("offer_code"),
            **_line_reference(line),
            "pricing_evidence_public_id": str(evidence.public_id),
            "previous_basis_pricing_evidence_public_id": previous_rate_public_id,
            "evidence_type": evidence.evidence_type,
            "rate_amount": str(evidence.rate_amount),
            "currency_code": evidence.currency_code,
            "rate_basis": evidence.rate_basis,
            "selection_reason": selection_reason,
        },
    )


def create_commercial_offer_pricing_evidence(
    db: Session,
    *,
    public_id: UUID,
    payload: CommercialOfferPricingEvidenceCreate,
    current_user_public_id: str | None,
) -> CommercialOfferPricingEvidenceCreatedResponse:
    commercial_offer_context = _lock_offer_for_content_change(db, public_id)
    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])

    values = _normalize_pricing_evidence_payload(payload, current_user_public_id)
    evidence_public_id = str(uuid4())

    try:
        line = _line_for_new_rate(db, commercial_offer_id=commercial_offer_id, line_public_id=payload.line_public_id)
        quote_copy = _quote_copy_rate(
            db, commercial_offer_id=commercial_offer_id, rate_public_id=payload.quote_copy_rate_public_id
        )
        evidence = insert_pricing_evidence(
            db,
            public_id=evidence_public_id,
            commercial_offer_id=commercial_offer_id,
            commercial_offer_line_id=int(line["line_id"]),
            quote_copy_evidence_id=int(quote_copy["pricing_evidence_id"]) if quote_copy else None,
            values=values,
        )
        events = [
            record_business_event(
                db,
                event_name=_pricing_evidence_added_event_name(evidence.evidence_type),
                source_module=COMMERCIAL_OFFER_MODULE_NAME,
                record_type=COMMERCIAL_OFFER_RECORD_TYPE,
                record_public_id=str(public_id),
                user_public_id=current_user_public_id,
                status_before=None,
                status_after=str(commercial_offer_context["offer_status_code"]),
                reason="Commercial Offer pricing evidence added.",
                event_payload={
                    "offer_code": commercial_offer_context.get("offer_code"),
                    **_line_reference(line),
                    "pricing_evidence_public_id": str(evidence.public_id),
                    "evidence_type": evidence.evidence_type,
                    "rate_amount": str(evidence.rate_amount),
                    "currency_code": evidence.currency_code,
                    "rate_basis": evidence.rate_basis,
                    "is_selected_basis": bool(values["is_selected_basis"]),
                    "quote_copy_pricing_evidence_public_id": (
                        str(quote_copy["evidence_public_id"]) if quote_copy else None
                    ),
                },
            )
        ]

        if values["is_selected_basis"]:
            new_rate = get_pricing_evidence_context(db, evidence_public_id=evidence_public_id)
            previous_rate_public_id = choose_line_basis_rate(
                db,
                commercial_offer_line_id=int(line["line_id"]),
                pricing_evidence_id=int(new_rate["pricing_evidence_id"]),
                selection_reason=str(values["selection_reason"]),
                current_user_public_id=current_user_public_id,
            )
            events.append(
                _record_basis_selected(
                    db,
                    public_id=public_id,
                    commercial_offer_context=commercial_offer_context,
                    evidence=evidence,
                    line=line,
                    selection_reason=str(values["selection_reason"]),
                    previous_rate_public_id=previous_rate_public_id,
                    current_user_public_id=current_user_public_id,
                    reason="Commercial Offer basis rate selected during pricing evidence creation.",
                )
            )

        evidence = _reload_rate(db, evidence_public_id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        _refuse_duplicate(exc, _SELECTED_AT_THE_SAME_TIME)
    except Exception:
        db.rollback()
        raise

    return CommercialOfferPricingEvidenceCreatedResponse(
        pricing_evidence=evidence,
        events=[_event_dict(event) for event in events],
    )


def select_commercial_offer_basis_rate(
    db: Session,
    *,
    public_id: UUID,
    evidence_public_id: UUID,
    payload: CommercialOfferPricingEvidenceBasisSelection,
    current_user_public_id: str | None,
) -> CommercialOfferPricingEvidenceSelectedResponse:
    commercial_offer_context = _lock_offer_for_content_change(db, public_id)
    commercial_offer_id = int(commercial_offer_context["commercial_offer_id"])

    selection_reason = _clean_optional(payload.selection_reason)
    if not selection_reason:
        raise CommercialOfferValidationError("Selection reason is required when selecting a basis rate.")

    try:
        rate = get_pricing_evidence_context(
            db, commercial_offer_id=commercial_offer_id, evidence_public_id=str(evidence_public_id)
        )
        if rate is None:
            raise CommercialOfferPricingEvidenceNotFoundError("Commercial Offer pricing evidence not found.")
        if rate["recorded_for_whole_offer"]:
            raise CommercialOfferValidationError(
                "This rate was recorded for the whole offer, before rates were kept per line, so it can no longer be "
                "chosen as a basis. Add the rate to the line it is for and choose it there."
            )
        line = get_commercial_offer_line_context(
            db, commercial_offer_id=commercial_offer_id, line_public_id=str(rate["line_public_id"]), for_update=True
        )
        if line is None or line["line_status_code"] != COMMERCIAL_OFFER_LINE_STATUS_ACTIVE:
            raise CommercialOfferValidationError(
                f"Line {rate['line_number']} is cancelled, so its basis rate cannot change. Its rates are kept as history."
            )
        if rate["is_selected_basis"]:
            raise CommercialOfferValidationError(f"This rate is already the basis rate for line {rate['line_number']}.")

        previous_rate_public_id = choose_line_basis_rate(
            db,
            commercial_offer_line_id=int(line["line_id"]),
            pricing_evidence_id=int(rate["pricing_evidence_id"]),
            selection_reason=selection_reason,
            current_user_public_id=current_user_public_id,
        )
        evidence = _reload_rate(db, str(evidence_public_id))
        event = _record_basis_selected(
            db,
            public_id=public_id,
            commercial_offer_context=commercial_offer_context,
            evidence=evidence,
            line=line,
            selection_reason=selection_reason,
            previous_rate_public_id=previous_rate_public_id,
            current_user_public_id=current_user_public_id,
            reason="Commercial Offer basis rate selected.",
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        _refuse_duplicate(exc, _SELECTED_AT_THE_SAME_TIME)
    except Exception:
        db.rollback()
        raise

    return CommercialOfferPricingEvidenceSelectedResponse(
        pricing_evidence=evidence,
        previous_basis_rate_public_id=previous_rate_public_id,
        event=_event_dict(event),
    )


def _market_rate_quote_copy_refusal(db: Session, request: AttachRequest) -> str | None:
    """Whether a file may be attached to this market rate as its quote copy (Slice 4G). It takes the offer's lock, held
    until the document's transaction ends, so the offer cannot be sent between this check and the file being stored."""
    if request.document_type != COMMERCIAL_OFFER_MARKET_RATE_DOCUMENT_TYPE:
        return "A market rate takes only its vendor quote (document type VENDOR_QUOTE)."
    if request.storage_mode != STORAGE_MODE_LOCAL_UPLOAD:
        return "Upload the quote itself: a link to a file kept elsewhere is not attached to a market rate."
    rate = get_pricing_evidence_context(db, evidence_public_id=request.linked_record_public_id)
    if rate is None:
        return "No market rate was found with that id, so the quote was not attached."
    if rate["recorded_for_whole_offer"]:
        return "This rate was recorded for the whole offer before rates were kept per line; it takes no new file."
    try:
        _lock_offer_for_content_change(db, UUID(str(rate["offer_public_id"])))
    except CommercialOfferValidationError as refusal:
        return str(refusal)
    # Read again under the lock: a line cancelled while this request waited for it is seen cancelled.
    rate = get_pricing_evidence_context(db, evidence_public_id=request.linked_record_public_id)
    if rate is None or rate["line_status_code"] != COMMERCIAL_OFFER_LINE_STATUS_ACTIVE:
        return "This rate's line is cancelled, so no file is attached to its rates."
    return None


register_attach_check(COMMERCIAL_OFFER_MARKET_RATE_RECORD_TYPE, _market_rate_quote_copy_refusal)
