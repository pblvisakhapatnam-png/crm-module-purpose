"""The Commercial Offer record: creating, listing and updating it (Slices 4A and 4C).

Reading one offer, get_commercial_offer, is in common.py: most concerns read the offer they act on.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_ALLOWED_MODES,
    COMMERCIAL_OFFER_ALLOWED_TYPES,
    COMMERCIAL_OFFER_CREATE_ALLOWED_STATUSES,
    COMMERCIAL_OFFER_EVENT_CREATED,
    COMMERCIAL_OFFER_EVENT_ACCEPTED,
    COMMERCIAL_OFFER_EVENT_CLOSED,
    COMMERCIAL_OFFER_EVENT_REJECTED,
    COMMERCIAL_OFFER_EVENT_STATUS_CHANGED,
    COMMERCIAL_OFFER_EVENT_SUBMITTED,
    COMMERCIAL_OFFER_EVENT_UPDATED,
    COMMERCIAL_OFFER_EVENT_WITHDRAWN,
    COMMERCIAL_OFFER_INITIAL_STATUS,
    COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES,
    COMMERCIAL_OFFER_MODULE_NAME,
    COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX,
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
    COMMERCIAL_OFFER_STATUS_CLOSED,
    COMMERCIAL_OFFER_STATUS_REJECTED,
    COMMERCIAL_OFFER_STATUS_SUBMITTED,
    COMMERCIAL_OFFER_STATUS_WITHDRAWN,
    COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES,
    COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES,
    COMMERCIAL_OFFER_PRE_SUBMISSION_STATUSES,
    COMMERCIAL_OFFER_RECORD_TYPE,
    COMMERCIAL_OFFER_STATUS_UPDATE_ALLOWED_STATUSES,
    COMMERCIAL_OFFER_VERSION_HISTORY_STATUSES,
    COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES,
)
from app.modules.commercial_offers.repository import (
    active_commercial_offer_status_exists,
    get_commercial_offer_by_public_id,
    get_existing_actionable_commercial_offer_for_opportunity,
    lock_commercial_offer_row,
    lock_opportunity_row,
    get_opportunity_context_by_public_id,
    insert_commercial_offer,
    list_recent_commercial_offers,
    update_commercial_offer_by_public_id,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferCreate,
    CommercialOfferCreatedResponse,
    CommercialOfferResponse,
    CommercialOfferUpdate,
    CommercialOfferUpdatedResponse,
)
from app.modules.events.service import record_business_event
from app.modules.opportunities.contract import (
    OPPORTUNITY_STATUS_CLOSED,
    OPPORTUNITY_STATUS_LOST,
    OPPORTUNITY_STATUS_WON,
)

from app.modules.commercial_offers.services.common import (
    CommercialOfferConflictError,
    CommercialOfferNotFoundError,
    CommercialOfferOpportunityNotFoundError,
    CommercialOfferValidationError,
    _clean_optional,
    _ensure_account_traceability_for_lifecycle_action,
    _ensure_no_preparation_version,
    _event_dict,
    _normalize_code,
    _normalize_lower,
    _refuse_duplicate,
    _validate_currency,
    _validate_dates,
    _validate_offer_value,
)


_OFFER_CONFLICT_MESSAGE = (
    "Someone else changed this Commercial Offer after you opened it, so your change was not saved. "
    "Reload the page to see their version, then make your change again."
)


def _payload_fields_set(payload: CommercialOfferUpdate) -> set[str]:
    model_fields_set = getattr(payload, "model_fields_set", None)
    if model_fields_set is not None:
        return set(model_fields_set)
    return set(getattr(payload, "__fields_set__", set()))


def _validate_active_status(db: Session, status_code: str) -> None:
    if not active_commercial_offer_status_exists(db, status_code):
        raise CommercialOfferValidationError(f"Commercial Offer status is not active in workflow_status: {status_code}")


def _active_base_offer_refusal(db: Session, *, opportunity_id: int) -> CommercialOfferValidationError | None:
    """The refusal of a new Base Offer while the Opportunity has an active one (Slice 6B.1), naming it; None if not."""
    existing_actionable_offer = get_existing_actionable_commercial_offer_for_opportunity(
        db,
        opportunity_id=opportunity_id,
        inactive_statuses=COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES,
    )
    if existing_actionable_offer is None:
        return None
    return CommercialOfferValidationError(
        "An active/actionable Commercial Offer already exists for this Opportunity. "
        f"Open existing Commercial Offer {existing_actionable_offer.offer_code} "
        f"({existing_actionable_offer.public_id}) instead of creating another one."
    )


def _normalize_create_payload(
    db: Session,
    payload: CommercialOfferCreate,
    current_user_public_id: str | None,
) -> tuple[dict[str, object | None], dict[str, object | None]]:
    opportunity_public_id = str(payload.opportunity_public_id)
    # Lock the parent Opportunity before reading its status. Both the eligibility check below
    # and the one-active-Base-Offer check are read-then-insert, so without the lock the
    # Opportunity can close, or a second creation can interleave, between read and insert.
    lock_opportunity_row(db, opportunity_public_id=opportunity_public_id)

    opportunity_context = get_opportunity_context_by_public_id(db, opportunity_public_id)
    if opportunity_context is None:
        raise CommercialOfferOpportunityNotFoundError("Opportunity not found for Commercial Offer creation.")

    opportunity_status = str(opportunity_context["opportunity_status_code"])
    if opportunity_status in {OPPORTUNITY_STATUS_WON, OPPORTUNITY_STATUS_LOST, OPPORTUNITY_STATUS_CLOSED}:
        raise CommercialOfferValidationError(
            f"Commercial Offer cannot be created for Opportunity status: {opportunity_status}"
        )

    refusal = _active_base_offer_refusal(db, opportunity_id=int(opportunity_context["opportunity_id"]))
    if refusal is not None:
        raise refusal

    offer_mode = _normalize_lower(payload.offer_mode, "plum_generated")
    if offer_mode not in COMMERCIAL_OFFER_ALLOWED_MODES:
        raise CommercialOfferValidationError(f"Commercial Offer mode is not allowed: {payload.offer_mode}")

    offer_type = _normalize_lower(payload.offer_type, "budgetary")
    if offer_type not in COMMERCIAL_OFFER_ALLOWED_TYPES:
        raise CommercialOfferValidationError(f"Commercial Offer type is not allowed: {payload.offer_type}")

    offer_status_code = _normalize_code(payload.offer_status_code, COMMERCIAL_OFFER_INITIAL_STATUS)
    if offer_status_code not in COMMERCIAL_OFFER_CREATE_ALLOWED_STATUSES:
        raise CommercialOfferValidationError(
            f"A new Commercial Offer cannot start with status {offer_status_code}."
        )
    _validate_active_status(db, offer_status_code)

    _validate_dates(payload.offer_date, payload.valid_until)

    opportunity_name = str(opportunity_context["opportunity_name"])
    offer_title = _clean_optional(payload.offer_title) or f"{opportunity_name} Commercial Offer"

    values = {
        "opportunity_id": opportunity_context["opportunity_id"],
        "business_party_id": opportunity_context.get("business_party_id"),
        "offer_title": offer_title,
        "offer_mode": offer_mode,
        "offer_type": offer_type,
        "offer_status_code": offer_status_code,
        "offer_value": _validate_offer_value(payload.offer_value),
        "currency_code": _validate_currency(payload.currency_code),
        "offer_date": payload.offer_date,
        "valid_until": payload.valid_until,
        "remarks": _clean_optional(payload.remarks),
        "created_by": current_user_public_id,
    }
    return values, opportunity_context


def _normalize_update_payload(db: Session, payload: CommercialOfferUpdate) -> dict[str, object | None]:
    # The version the screen loaded is not a field of the offer (CS-05a).
    fields_set = _payload_fields_set(payload) - {"expected_row_version"}
    if not fields_set:
        raise CommercialOfferValidationError("At least one Commercial Offer field must be provided for update.")

    values: dict[str, object | None] = {}

    if "offer_title" in fields_set:
        values["offer_title"] = _clean_optional(payload.offer_title)

    if "offer_mode" in fields_set:
        offer_mode = _normalize_lower(payload.offer_mode, "")
        if offer_mode not in COMMERCIAL_OFFER_ALLOWED_MODES:
            raise CommercialOfferValidationError(f"Commercial Offer mode is not allowed: {payload.offer_mode}")
        values["offer_mode"] = offer_mode

    if "offer_type" in fields_set:
        offer_type = _normalize_lower(payload.offer_type, "")
        if offer_type not in COMMERCIAL_OFFER_ALLOWED_TYPES:
            raise CommercialOfferValidationError(f"Commercial Offer type is not allowed: {payload.offer_type}")
        values["offer_type"] = offer_type

    if "offer_status_code" in fields_set:
        offer_status_code = _normalize_code(payload.offer_status_code, "")
        if offer_status_code not in COMMERCIAL_OFFER_STATUS_UPDATE_ALLOWED_STATUSES:
            raise CommercialOfferValidationError(
                f"Commercial Offer status cannot be set to {offer_status_code}."
            )
        _validate_active_status(db, offer_status_code)
        values["offer_status_code"] = offer_status_code

    if "offer_value" in fields_set:
        values["offer_value"] = _validate_offer_value(payload.offer_value)

    if "currency_code" in fields_set:
        values["currency_code"] = _validate_currency(payload.currency_code)

    if "offer_date" in fields_set:
        values["offer_date"] = payload.offer_date

    if "valid_until" in fields_set:
        values["valid_until"] = payload.valid_until

    if "submitted_at" in fields_set:
        values["submitted_at"] = payload.submitted_at

    if "submission_reference" in fields_set:
        values["submission_reference"] = _clean_optional(payload.submission_reference)

    if "submission_proof_note" in fields_set:
        values["submission_proof_note"] = _clean_optional(payload.submission_proof_note)

    if "outcome_date" in fields_set:
        values["outcome_date"] = payload.outcome_date

    if "outcome_remarks" in fields_set:
        values["outcome_remarks"] = _clean_optional(payload.outcome_remarks)

    if "remarks" in fields_set:
        values["remarks"] = _clean_optional(payload.remarks)

    if not values:
        raise CommercialOfferValidationError("At least one Commercial Offer field must be provided for update.")

    prospective_offer_date = values.get("offer_date", payload.offer_date)
    prospective_valid_until = values.get("valid_until", payload.valid_until)
    _validate_dates(prospective_offer_date, prospective_valid_until)

    return values


def create_commercial_offer(
    db: Session,
    *,
    payload: CommercialOfferCreate,
    current_user_public_id: str | None,
) -> CommercialOfferCreatedResponse:
    values, opportunity_context = _normalize_create_payload(db, payload, current_user_public_id)
    commercial_offer_public_id = str(uuid4())

    try:
        commercial_offer = insert_commercial_offer(db, public_id=commercial_offer_public_id, values=values)
        event = record_business_event(
            db,
            event_name=COMMERCIAL_OFFER_EVENT_CREATED,
            source_module=COMMERCIAL_OFFER_MODULE_NAME,
            record_type=COMMERCIAL_OFFER_RECORD_TYPE,
            record_public_id=str(commercial_offer.public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=commercial_offer.offer_status_code,
            reason="Commercial Offer created.",
            event_payload={
                "offer_code": commercial_offer.offer_code,
                "opportunity_public_id": str(commercial_offer.opportunity_public_id),
                "account_public_id": str(commercial_offer.account_public_id) if commercial_offer.account_public_id else None,
                "opportunity_status_code": opportunity_context["opportunity_status_code"],
                "offer_mode": commercial_offer.offer_mode,
                "offer_type": commercial_offer.offer_type,
                "has_offer_value": commercial_offer.offer_value is not None,
                "offer_date": commercial_offer.offer_date.isoformat() if commercial_offer.offer_date else None,
                "valid_until": commercial_offer.valid_until.isoformat() if commercial_offer.valid_until else None,
            },
        )
        db.commit()
    except IntegrityError as exc:
        # The database's one-active-Base-Offer rule (CS-05c) refused what the check above passed: another Base Offer
        # became active for the Opportunity after it, which the Opportunity's row lock prevents for every writer that
        # takes it. Answered as the check answers, naming the offer that holds the place now.
        db.rollback()
        opportunity_id = int(opportunity_context["opportunity_id"])
        _refuse_duplicate(
            exc,
            {
                COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX: lambda: _active_base_offer_refusal(
                    db, opportunity_id=opportunity_id
                )
                or CommercialOfferValidationError(
                    "Another Commercial Offer was made active for this Opportunity at the same time. Reload the page "
                    "to see it."
                ),
            },
        )
    except Exception:
        db.rollback()
        raise

    return CommercialOfferCreatedResponse(commercial_offer=commercial_offer, event=_event_dict(event))


def update_commercial_offer(
    db: Session,
    *,
    public_id: UUID,
    payload: CommercialOfferUpdate,
    current_user_public_id: str | None,
) -> CommercialOfferUpdatedResponse:
    # Lock before reading, for the same reason the customer-response path does: this function
    # reads offer_status_code, validates it against the cannot-leave/cannot-enter sets, and then
    # writes an unconditional UPDATE. Without the lock a general update could read SUBMITTED,
    # a concurrent customer response could commit REJECTED, and this UPDATE would then overwrite
    # that rejection with DRAFT or READY_FOR_REVIEW - reactivating a rejected offer through a
    # different route than the one Slice 9B closed.
    if lock_commercial_offer_row(db, public_id=str(public_id)) is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")

    existing = get_commercial_offer_by_public_id(db, str(public_id))
    if existing is None:
        raise CommercialOfferNotFoundError("Commercial Offer not found.")
    # CS-05a (TB-1 TB1-303): compared under the row lock, so a save from a form opened before someone else's save -
    # an edit, marking it submitted, a customer response - is refused rather than written over theirs.
    if payload.expected_row_version != existing.row_version:
        raise CommercialOfferConflictError(_OFFER_CONFLICT_MESSAGE)

    values = _normalize_update_payload(db, payload)
    old_status = existing.offer_status_code
    target_status = str(values.get("offer_status_code", old_status))
    if (
        existing.previous_version_offer_public_id is not None
        and old_status in COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES
    ):
        if {"submitted_at", "submission_reference", "submission_proof_note"} & set(values):
            raise CommercialOfferValidationError(
                "Submission details for a later Commercial Offer version come only from submission evidence. "
                "Record that evidence, then use Record as Submitted / Commercially Committed."
            )
        if target_status not in COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES:
            raise CommercialOfferValidationError(
                "A later Commercial Offer version can be sent only through Record as Submitted / Commercially "
                "Committed. To stop preparing it, use Abandon this version."
            )
    if old_status in COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES and target_status != old_status:
        raise CommercialOfferValidationError(
            f"Commercial Offer status {old_status} is final and cannot be changed through general update. "
            "Use the dedicated Commercial Offer workflow actions (such as customer response recording) where applicable."
        )
    if old_status == COMMERCIAL_OFFER_STATUS_SUBMITTED and target_status in COMMERCIAL_OFFER_PRE_SUBMISSION_STATUSES:
        raise CommercialOfferValidationError(
            "A submitted Commercial Offer cannot go back to Draft or Ready for Review through general update. "
            "It can be withdrawn or closed here, or the customer's response recorded in the Submission tab."
        )
    if old_status == COMMERCIAL_OFFER_STATUS_SUBMITTED and target_status != old_status:
        _ensure_no_preparation_version(db, existing)
    if target_status in COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES and target_status != old_status:
        raise CommercialOfferValidationError(
            f"Commercial Offer status cannot be set to {target_status} through general update. "
            "Use the dedicated Customer Response action (Submission tab) to record the award or rejection outcome."
        )
    if old_status != target_status and target_status == COMMERCIAL_OFFER_STATUS_SUBMITTED:
        raise CommercialOfferValidationError(
            "Use Record as Submitted / Commercially Committed so submission evidence and lifecycle guards are enforced."
        )
    if old_status in COMMERCIAL_OFFER_VERSION_HISTORY_STATUSES:
        raise CommercialOfferValidationError(
            "A replaced or abandoned Commercial Offer version is read-only history. "
            "Open the latest live version for any further commercial action."
        )
    if old_status not in COMMERCIAL_OFFER_PRE_SUBMISSION_STATUSES:
        allowed_fields = {"outcome_date", "outcome_remarks"}
        if "offer_status_code" in values and target_status == old_status:
            allowed_fields.add("offer_status_code")
        if (
            old_status == COMMERCIAL_OFFER_STATUS_SUBMITTED
            and target_status in {COMMERCIAL_OFFER_STATUS_WITHDRAWN, COMMERCIAL_OFFER_STATUS_CLOSED}
            and target_status != old_status
        ):
            allowed_fields.add("offer_status_code")
        refused_fields = set(values) - allowed_fields
        if refused_fields:
            raise CommercialOfferValidationError(
                "A sent Commercial Offer is read-only. Make a new version to change its commercial content; only "
                "withdrawal or closure and outcome notes may be recorded on this version."
            )
    _ensure_account_traceability_for_lifecycle_action(
        commercial_offer=existing,
        target_status=target_status,
    )

    if "offer_date" not in values:
        values_offer_date = existing.offer_date
    else:
        values_offer_date = values.get("offer_date")

    if "valid_until" not in values:
        values_valid_until = existing.valid_until
    else:
        values_valid_until = values.get("valid_until")

    _validate_dates(values_offer_date, values_valid_until)

    try:
        commercial_offer = update_commercial_offer_by_public_id(
            db, public_id=str(public_id), values=values, expected_row_version=payload.expected_row_version
        )
        if commercial_offer is None:
            raise CommercialOfferConflictError(_OFFER_CONFLICT_MESSAGE)
        events = [
            record_business_event(
                db,
                event_name=COMMERCIAL_OFFER_EVENT_UPDATED,
                source_module=COMMERCIAL_OFFER_MODULE_NAME,
                record_type=COMMERCIAL_OFFER_RECORD_TYPE,
                record_public_id=str(commercial_offer.public_id),
                user_public_id=current_user_public_id,
                status_before=old_status,
                status_after=commercial_offer.offer_status_code,
                reason="Commercial Offer updated.",
                event_payload={
                    "updated_fields": sorted(values.keys()),
                    "row_version": commercial_offer.row_version,
                    "offer_code": commercial_offer.offer_code,
                    "opportunity_public_id": str(commercial_offer.opportunity_public_id),
                    "account_public_id": str(commercial_offer.account_public_id) if commercial_offer.account_public_id else None,
                    "offer_mode": commercial_offer.offer_mode,
                    "offer_type": commercial_offer.offer_type,
                    "has_offer_value": commercial_offer.offer_value is not None,
                    "offer_date": commercial_offer.offer_date.isoformat() if commercial_offer.offer_date else None,
                    "valid_until": commercial_offer.valid_until.isoformat() if commercial_offer.valid_until else None,
                    "submitted_at": commercial_offer.submitted_at.isoformat() if commercial_offer.submitted_at else None,
                    "submission_reference": commercial_offer.submission_reference,
                    "has_submission_proof_note": bool(commercial_offer.submission_proof_note),
                    "outcome_date": commercial_offer.outcome_date.isoformat() if commercial_offer.outcome_date else None,
                    "has_outcome_remarks": bool(commercial_offer.outcome_remarks),
                },
            )
        ]

        if old_status != commercial_offer.offer_status_code:
            events.append(
                record_business_event(
                    db,
                    event_name=COMMERCIAL_OFFER_EVENT_STATUS_CHANGED,
                    source_module=COMMERCIAL_OFFER_MODULE_NAME,
                    record_type=COMMERCIAL_OFFER_RECORD_TYPE,
                    record_public_id=str(commercial_offer.public_id),
                    user_public_id=current_user_public_id,
                    status_before=old_status,
                    status_after=commercial_offer.offer_status_code,
                    reason="Commercial Offer status changed.",
                    event_payload={
                        "offer_code": commercial_offer.offer_code,
                        "status_before": old_status,
                        "status_after": commercial_offer.offer_status_code,
                    },
                )
            )

            lifecycle_event_by_status = {
                COMMERCIAL_OFFER_STATUS_SUBMITTED: COMMERCIAL_OFFER_EVENT_SUBMITTED,
                COMMERCIAL_OFFER_STATUS_ACCEPTED: COMMERCIAL_OFFER_EVENT_ACCEPTED,
                COMMERCIAL_OFFER_STATUS_REJECTED: COMMERCIAL_OFFER_EVENT_REJECTED,
                COMMERCIAL_OFFER_STATUS_WITHDRAWN: COMMERCIAL_OFFER_EVENT_WITHDRAWN,
                COMMERCIAL_OFFER_STATUS_CLOSED: COMMERCIAL_OFFER_EVENT_CLOSED,
            }
            lifecycle_event_name = lifecycle_event_by_status.get(commercial_offer.offer_status_code)
            if lifecycle_event_name:
                events.append(
                    record_business_event(
                        db,
                        event_name=lifecycle_event_name,
                        source_module=COMMERCIAL_OFFER_MODULE_NAME,
                        record_type=COMMERCIAL_OFFER_RECORD_TYPE,
                        record_public_id=str(commercial_offer.public_id),
                        user_public_id=current_user_public_id,
                        status_before=old_status,
                        status_after=commercial_offer.offer_status_code,
                        reason="Commercial Offer lifecycle status recorded.",
                        event_payload={
                            "offer_code": commercial_offer.offer_code,
                            "status_before": old_status,
                            "status_after": commercial_offer.offer_status_code,
                            "submitted_at": commercial_offer.submitted_at.isoformat() if commercial_offer.submitted_at else None,
                            "submission_reference": commercial_offer.submission_reference,
                            "has_submission_proof_note": bool(commercial_offer.submission_proof_note),
                            "outcome_date": commercial_offer.outcome_date.isoformat() if commercial_offer.outcome_date else None,
                            "has_outcome_remarks": bool(commercial_offer.outcome_remarks),
                        },
                    )
                )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return CommercialOfferUpdatedResponse(commercial_offer=commercial_offer, events=[_event_dict(event) for event in events])


def list_commercial_offers(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    status_code: str | None = None,
    offer_mode: str | None = None,
    opportunity_public_id: UUID | None = None,
) -> list[CommercialOfferResponse]:
    normalized_status = _normalize_code(status_code, "") if status_code else None
    normalized_mode = _normalize_lower(offer_mode, "") if offer_mode else None
    return list_recent_commercial_offers(
        db,
        limit=limit,
        offset=offset,
        status_code=normalized_status,
        offer_mode=normalized_mode,
        opportunity_public_id=str(opportunity_public_id) if opportunity_public_id else None,
    )
