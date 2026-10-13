from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.accounts.contract import (
    ACCOUNT_EVENT_CREATED,
    ACCOUNT_MODULE_NAME,
    ACCOUNT_STATUS_QUALIFIED_PROSPECT,
    BUSINESS_PARTY_RECORD_TYPE,
    PARTY_TYPE_ORGANIZATION,
    QUALIFICATION_SOURCE_ENQUIRY,
    QUALIFICATION_SOURCE_EXTERNAL_INTELLIGENCE,
    QUALIFICATION_SOURCE_MANUAL,
    QUALIFICATION_SOURCE_RFQ,
    QUALIFICATION_SOURCE_TENDER,
)
from app.modules.accounts.repository import (
    active_account_status_exists,
    get_business_party_id_by_public_id,
    insert_business_party,
)
from app.modules.events.service import record_business_event
from app.modules.leads.contract import (
    LEAD_ACTIVITY_ALLOWED_TYPES,
    LEAD_ACTIVITY_RECORD_TYPE,
    LEAD_ALLOWED_SOURCES,
    LEAD_CONVERSION_ALLOWED_STATUSES,
    LEAD_CREATE_ALLOWED_STATUSES,
    LEAD_DETAILS_UPDATE_ALLOWED_STATUSES,
    LEAD_EVENT_ACTIVITY_RECORDED,
    LEAD_EVENT_ASSIGNED,
    LEAD_EVENT_CLOSED,
    LEAD_EVENT_CONVERTED,
    LEAD_EVENT_CREATED,
    LEAD_EVENT_QUALIFICATION_READY,
    LEAD_EVENT_QUALIFIED,
    LEAD_EVENT_STATUS_CHANGED,
    LEAD_EVENT_UNQUALIFIED,
    LEAD_EVENT_UPDATED,
    LEAD_INITIAL_STATUS,
    LEAD_MODULE_NAME,
    LEAD_QUALIFICATION_DECISION_ALLOWED_STATUSES,
    LEAD_QUALIFICATION_REASON_REQUIRED_STATUSES,
    LEAD_RECORD_TYPE,
    LEAD_STATUS_CONVERTED,
)
from app.modules.leads.repository import (
    active_lead_status_exists,
    get_lead_by_public_id,
    get_lead_id_by_public_id,
    insert_lead,
    insert_lead_activity,
    list_lead_activities,
    list_recent_leads,
    lock_lead_row,
    update_lead_by_public_id,
    update_lead_conversion_by_public_id,
    update_lead_qualification_by_public_id,
)
from app.modules.opportunities.contract import (
    OPPORTUNITY_EVENT_CREATED,
    OPPORTUNITY_MODULE_NAME,
    OPPORTUNITY_RECORD_TYPE,
    OPPORTUNITY_SOURCE_LEAD_CONVERSION,
    OPPORTUNITY_STATUS_QUALIFIED,
)
from app.modules.opportunities.repository import (
    active_opportunity_status_exists,
    get_opportunity_by_source_lead_id,
    insert_opportunity,
)
from app.modules.leads.schemas import (
    LeadActivityCreate,
    LeadActivityCreatedResponse,
    LeadActivityResponse,
    LeadConversionCreate,
    LeadConversionResponse,
    LeadCreate,
    LeadCreatedResponse,
    LeadQualificationDecision,
    LeadQualificationDecisionResponse,
    LeadResponse,
    LeadUpdate,
    LeadUpdatedResponse,
)


class LeadValidationError(ValueError):
    pass


class LeadNotFoundError(LookupError):
    pass


CONVERTED_LEAD_IS_FINAL = (
    "This Lead has been converted, so its details and qualification decision can no longer be changed. "
    "Work continues on its Account and Opportunity."
)


def _locked_changeable_lead(db: Session, public_id: UUID) -> LeadResponse:
    """The Lead under its row lock, refused once converted (TB-1 finding TB1-302, 4 October 2026). Conversion writes
    CONVERTED with an UPDATE, which takes the same row lock, so an edit or decision waiting on it reads CONVERTED."""
    if lock_lead_row(db, str(public_id)) is None:
        raise LeadNotFoundError("Lead not found.")
    lead = get_lead_by_public_id(db, str(public_id))
    if lead is None:
        raise LeadNotFoundError("Lead not found.")
    if lead.lead_status_code == LEAD_STATUS_CONVERTED:
        raise LeadValidationError(CONVERTED_LEAD_IS_FINAL)
    return lead


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_source(value: str | None) -> str:
    return (value or "").strip().lower()


def _normalize_status(value: str | None) -> str:
    return (value or LEAD_INITIAL_STATUS).strip().upper()


def _normalize_activity_type(value: str | None) -> str:
    return (value or "").strip().upper()


def _validate_email(value: str | None) -> str | None:
    email = _clean_optional(value)
    if email is None:
        return None
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise LeadValidationError("Contact email must be a valid email-like value.")
    return email


def _payload_fields_set(payload: LeadUpdate) -> set[str]:
    model_fields_set = getattr(payload, "model_fields_set", None)
    if model_fields_set is not None:
        return set(model_fields_set)
    return set(getattr(payload, "__fields_set__", set()))


def _event_dict(event: object) -> dict[str, object | None]:
    return {
        "public_id": getattr(event, "public_id", None),
        "event_name": getattr(event, "event_name", None),
        "record_type": getattr(event, "record_type", None),
        "record_public_id": getattr(event, "record_public_id", None),
    }


def _validate_active_status(db: Session, status_code: str) -> None:
    if not active_lead_status_exists(db, status_code):
        raise LeadValidationError(f"Lead status is not active in workflow_status: {status_code}")


def _validate_active_account_status(db: Session, status_code: str) -> None:
    if not active_account_status_exists(db, status_code):
        raise LeadValidationError(f"Account status is not active in workflow_status: {status_code}")


def _validate_active_opportunity_status(db: Session, status_code: str) -> None:
    if not active_opportunity_status_exists(db, status_code):
        raise LeadValidationError(f"Opportunity status is not active in workflow_status: {status_code}")


def _lead_source_to_qualification_source(lead_source: str) -> str:
    normalized = _normalize_source(lead_source)
    if normalized == "rfq":
        return QUALIFICATION_SOURCE_RFQ
    if normalized == "tender":
        return QUALIFICATION_SOURCE_TENDER
    if normalized == "external_intelligence":
        return QUALIFICATION_SOURCE_EXTERNAL_INTELLIGENCE
    if normalized == "manual":
        return QUALIFICATION_SOURCE_MANUAL
    return QUALIFICATION_SOURCE_ENQUIRY


def _default_conversion_notes(lead: LeadResponse, provided_notes: str | None) -> str:
    prefix = f"Converted from Lead {lead.public_id}."
    notes = _clean_optional(provided_notes)
    return f"{prefix} {notes}" if notes else prefix


def _normalize_create_payload(db: Session, payload: LeadCreate, current_user_public_id: str | None) -> dict[str, object | None]:
    lead_source = _normalize_source(payload.lead_source)
    if lead_source not in LEAD_ALLOWED_SOURCES:
        raise LeadValidationError(f"Lead source is not allowed: {payload.lead_source}")

    lead_status_code = _normalize_status(payload.lead_status_code)
    if lead_status_code not in LEAD_CREATE_ALLOWED_STATUSES:
        raise LeadValidationError(f"Lead status cannot be used during initial Lead creation: {lead_status_code}")

    _validate_active_status(db, lead_status_code)

    company_name = payload.company_name.strip()
    if not company_name:
        raise LeadValidationError("Company name is required.")

    return {
        "lead_source": lead_source,
        "source_reference": _clean_optional(payload.source_reference),
        "company_name": company_name,
        "contact_name": _clean_optional(payload.contact_name),
        "contact_phone": _clean_optional(payload.contact_phone),
        "contact_email": _validate_email(payload.contact_email),
        "requirement_summary": _clean_optional(payload.requirement_summary),
        "lead_status_code": lead_status_code,
        "assigned_to_user_public_id": str(payload.assigned_to_user_public_id) if payload.assigned_to_user_public_id else None,
        "created_by": current_user_public_id,
    }


def _normalize_update_payload(db: Session, payload: LeadUpdate) -> dict[str, object | None]:
    fields_set = _payload_fields_set(payload)
    if not fields_set:
        raise LeadValidationError("At least one Lead field must be provided for update.")

    values: dict[str, object | None] = {}

    if "lead_source" in fields_set:
        lead_source = _normalize_source(payload.lead_source)
        if lead_source not in LEAD_ALLOWED_SOURCES:
            raise LeadValidationError(f"Lead source is not allowed: {payload.lead_source}")
        values["lead_source"] = lead_source

    if "source_reference" in fields_set:
        values["source_reference"] = _clean_optional(payload.source_reference)

    if "company_name" in fields_set:
        company_name = (payload.company_name or "").strip()
        if not company_name:
            raise LeadValidationError("Company name is required.")
        values["company_name"] = company_name

    if "contact_name" in fields_set:
        values["contact_name"] = _clean_optional(payload.contact_name)

    if "contact_phone" in fields_set:
        values["contact_phone"] = _clean_optional(payload.contact_phone)

    if "contact_email" in fields_set:
        values["contact_email"] = _validate_email(payload.contact_email)

    if "requirement_summary" in fields_set:
        values["requirement_summary"] = _clean_optional(payload.requirement_summary)

    if "lead_status_code" in fields_set:
        lead_status_code = _normalize_status(payload.lead_status_code)
        if lead_status_code not in LEAD_DETAILS_UPDATE_ALLOWED_STATUSES:
            raise LeadValidationError(f"Lead status cannot be used in early Lead details update: {lead_status_code}")
        _validate_active_status(db, lead_status_code)
        values["lead_status_code"] = lead_status_code

    if "assigned_to_user_public_id" in fields_set:
        values["assigned_to_user_public_id"] = (
            str(payload.assigned_to_user_public_id) if payload.assigned_to_user_public_id else None
        )

    if not values:
        raise LeadValidationError("At least one Lead field must be provided for update.")

    return values


def _normalize_activity_payload(payload: LeadActivityCreate, current_user_public_id: str | None) -> dict[str, object | None]:
    activity_type = _normalize_activity_type(payload.activity_type)
    if activity_type not in LEAD_ACTIVITY_ALLOWED_TYPES:
        raise LeadValidationError(f"Lead activity type is not allowed: {payload.activity_type}")

    notes = _clean_optional(payload.notes)
    outcome = _clean_optional(payload.outcome)

    return {
        "activity_type": activity_type,
        "activity_at": payload.activity_at or datetime.now(timezone.utc).replace(tzinfo=None),
        "notes": notes,
        "outcome": outcome,
        "next_follow_up_at": payload.next_follow_up_at,
        "created_by": current_user_public_id,
    }


def _normalize_qualification_payload(
    db: Session,
    payload: LeadQualificationDecision,
    current_user_public_id: str | None,
) -> dict[str, object | None]:
    decision_status_code = _normalize_status(payload.decision_status_code)
    if decision_status_code not in LEAD_QUALIFICATION_DECISION_ALLOWED_STATUSES:
        raise LeadValidationError(f"Lead qualification decision status is not allowed: {decision_status_code}")

    _validate_active_status(db, decision_status_code)

    reason = _clean_optional(payload.reason)
    if decision_status_code in LEAD_QUALIFICATION_REASON_REQUIRED_STATUSES and reason is None:
        raise LeadValidationError("Reason is required when a Lead is unqualified or closed.")

    return {
        "lead_status_code": decision_status_code,
        "qualification_decision_notes": _clean_optional(payload.decision_notes),
        "qualification_reason": reason,
        "qualification_decided_by": current_user_public_id,
        "qualification_decided_at": datetime.now(timezone.utc).replace(tzinfo=None),
    }


def _qualification_event_name(status_code: str) -> str:
    if status_code == "QUALIFICATION_READY":
        return LEAD_EVENT_QUALIFICATION_READY
    if status_code == "QUALIFIED":
        return LEAD_EVENT_QUALIFIED
    if status_code == "UNQUALIFIED":
        return LEAD_EVENT_UNQUALIFIED
    if status_code == "CLOSED":
        return LEAD_EVENT_CLOSED
    raise LeadValidationError(f"No Lead qualification event is mapped for status: {status_code}")


def create_lead(
    db: Session,
    *,
    payload: LeadCreate,
    current_user_public_id: str | None,
) -> LeadCreatedResponse:
    values = _normalize_create_payload(db, payload, current_user_public_id)
    lead_public_id = str(uuid4())
    try:
        lead = insert_lead(db, public_id=lead_public_id, values=values)
        event = record_business_event(
            db,
            event_name=LEAD_EVENT_CREATED,
            source_module=LEAD_MODULE_NAME,
            record_type=LEAD_RECORD_TYPE,
            record_public_id=str(lead.public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=lead.lead_status_code,
            reason="Lead created through Lead API.",
            event_payload={
                "lead_source": lead.lead_source,
                "company_name": lead.company_name,
                "assigned_to_user_public_id": str(lead.assigned_to_user_public_id) if lead.assigned_to_user_public_id else None,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return LeadCreatedResponse(
        lead=lead,
        event=_event_dict(event),
    )


def update_lead(
    db: Session,
    *,
    public_id: UUID,
    payload: LeadUpdate,
    current_user_public_id: str | None,
) -> LeadUpdatedResponse:
    existing = _locked_changeable_lead(db, public_id)

    values = _normalize_update_payload(db, payload)

    old_status = existing.lead_status_code
    old_assigned = str(existing.assigned_to_user_public_id) if existing.assigned_to_user_public_id else None

    try:
        lead = update_lead_by_public_id(db, public_id=str(public_id), values=values)
        new_assigned = str(lead.assigned_to_user_public_id) if lead.assigned_to_user_public_id else None

        events = [
            record_business_event(
                db,
                event_name=LEAD_EVENT_UPDATED,
                source_module=LEAD_MODULE_NAME,
                record_type=LEAD_RECORD_TYPE,
                record_public_id=str(lead.public_id),
                user_public_id=current_user_public_id,
                status_before=old_status,
                status_after=lead.lead_status_code,
                reason="Lead updated through Lead API.",
                event_payload={
                    "updated_fields": sorted(values.keys()),
                    "company_name": lead.company_name,
                },
            )
        ]

        if old_status != lead.lead_status_code:
            events.append(
                record_business_event(
                    db,
                    event_name=LEAD_EVENT_STATUS_CHANGED,
                    source_module=LEAD_MODULE_NAME,
                    record_type=LEAD_RECORD_TYPE,
                    record_public_id=str(lead.public_id),
                    user_public_id=current_user_public_id,
                    status_before=old_status,
                    status_after=lead.lead_status_code,
                    reason="Lead status changed during early Lead details.",
                    event_payload={"status_before": old_status, "status_after": lead.lead_status_code},
                )
            )

        if old_assigned != new_assigned:
            events.append(
                record_business_event(
                    db,
                    event_name=LEAD_EVENT_ASSIGNED,
                    source_module=LEAD_MODULE_NAME,
                    record_type=LEAD_RECORD_TYPE,
                    record_public_id=str(lead.public_id),
                    user_public_id=current_user_public_id,
                    status_before=old_status,
                    status_after=lead.lead_status_code,
                    reason="Lead assignment field changed during early Lead details.",
                    event_payload={"assigned_before": old_assigned, "assigned_after": new_assigned},
                )
            )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return LeadUpdatedResponse(lead=lead, events=[_event_dict(event) for event in events])


def decide_lead_qualification(
    db: Session,
    *,
    public_id: UUID,
    payload: LeadQualificationDecision,
    current_user_public_id: str | None,
) -> LeadQualificationDecisionResponse:
    existing = _locked_changeable_lead(db, public_id)

    values = _normalize_qualification_payload(db, payload, current_user_public_id)
    old_status = existing.lead_status_code
    decision_status_code = str(values["lead_status_code"])

    try:
        lead = update_lead_qualification_by_public_id(db, public_id=str(public_id), values=values)
        event = record_business_event(
            db,
            event_name=_qualification_event_name(decision_status_code),
            source_module=LEAD_MODULE_NAME,
            record_type=LEAD_RECORD_TYPE,
            record_public_id=str(lead.public_id),
            user_public_id=current_user_public_id,
            status_before=old_status,
            status_after=lead.lead_status_code,
            reason="Lead qualification or closure decision recorded.",
            event_payload={
                "decision_status_code": lead.lead_status_code,
                "qualification_reason": lead.qualification_reason,
                "has_decision_notes": bool(lead.qualification_decision_notes),
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return LeadQualificationDecisionResponse(lead=lead, event=_event_dict(event))


def convert_lead(
    db: Session,
    *,
    public_id: UUID,
    payload: LeadConversionCreate,
    current_user_public_id: str | None,
) -> LeadConversionResponse:
    lead = get_lead_by_public_id(db, str(public_id))
    if lead is None:
        raise LeadNotFoundError("Lead not found.")

    if lead.lead_status_code == LEAD_STATUS_CONVERTED:
        raise LeadValidationError("Lead is already converted.")

    if lead.lead_status_code not in LEAD_CONVERSION_ALLOWED_STATUSES:
        raise LeadValidationError("Only a qualified Lead can be converted.")

    lead_id = get_lead_id_by_public_id(db, str(public_id))
    if lead_id is None:
        raise LeadNotFoundError("Lead not found.")

    existing_opportunity = get_opportunity_by_source_lead_id(db, lead_id)
    if existing_opportunity is not None:
        raise LeadValidationError("Lead already has a converted Opportunity.")

    _validate_active_account_status(db, ACCOUNT_STATUS_QUALIFIED_PROSPECT)
    _validate_active_opportunity_status(db, OPPORTUNITY_STATUS_QUALIFIED)
    _validate_active_status(db, LEAD_STATUS_CONVERTED)

    account_name = _clean_optional(payload.account_name) or lead.company_name
    opportunity_name = _clean_optional(payload.opportunity_name) or f"{lead.company_name} Opportunity"
    conversion_notes = _default_conversion_notes(lead, payload.conversion_notes)
    owner_user_public_id = current_user_public_id or (str(lead.assigned_to_user_public_id) if lead.assigned_to_user_public_id else None)

    account_public_id = str(uuid4())
    opportunity_public_id = str(uuid4())

    try:
        account = insert_business_party(
            db,
            public_id=account_public_id,
            values={
                "party_type": PARTY_TYPE_ORGANIZATION,
                "account_name": account_name,
                "legal_name": None,
                "pan": None,
                "gstin": None,
                "account_status_code": ACCOUNT_STATUS_QUALIFIED_PROSPECT,
                "qualification_source": _lead_source_to_qualification_source(lead.lead_source),
                "account_owner_user_public_id": owner_user_public_id,
                "segment": None,
                "industry": None,
                "source_remarks": conversion_notes,
                "is_strategic_account": False,
                "classification_notes": _clean_optional(payload.conversion_notes),
                "created_by": current_user_public_id,
            },
        )

        business_party_id = get_business_party_id_by_public_id(db, account_public_id)
        if business_party_id is None:
            raise RuntimeError("Converted Account could not be resolved for Opportunity linkage.")

        opportunity = insert_opportunity(
            db,
            public_id=opportunity_public_id,
            values={
                "opportunity_name": opportunity_name,
                "opportunity_source": OPPORTUNITY_SOURCE_LEAD_CONVERSION,
                "source_reference": _clean_optional(lead.source_reference),
                "business_party_id": business_party_id,
                "source_lead_id": lead_id,
                "customer_requirement_summary": _clean_optional(lead.requirement_summary),
                "estimated_value": None,
                "expected_close_date": None,
                "opportunity_status_code": OPPORTUNITY_STATUS_QUALIFIED,
                "owner_user_public_id": owner_user_public_id,
                "created_by": current_user_public_id,
            },
        )

        converted_lead = update_lead_conversion_by_public_id(
            db,
            public_id=str(public_id),
            values={"lead_status_code": LEAD_STATUS_CONVERTED},
        )

        account_event = record_business_event(
            db,
            event_name=ACCOUNT_EVENT_CREATED,
            source_module=ACCOUNT_MODULE_NAME,
            record_type=BUSINESS_PARTY_RECORD_TYPE,
            record_public_id=str(account.public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=account.account_status_code,
            reason="Account created through Lead conversion.",
            remarks=conversion_notes,
            event_payload={
                "source_lead_public_id": str(lead.public_id),
                "qualification_source": account.qualification_source,
            },
        )
        opportunity_event = record_business_event(
            db,
            event_name=OPPORTUNITY_EVENT_CREATED,
            source_module=OPPORTUNITY_MODULE_NAME,
            record_type=OPPORTUNITY_RECORD_TYPE,
            record_public_id=str(opportunity.public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=opportunity.opportunity_status_code,
            reason="Opportunity created through Lead conversion.",
            remarks=conversion_notes,
            event_payload={
                "source_lead_public_id": str(lead.public_id),
                "account_public_id": str(account.public_id),
                "opportunity_source": opportunity.opportunity_source,
            },
        )
        lead_event = record_business_event(
            db,
            event_name=LEAD_EVENT_CONVERTED,
            source_module=LEAD_MODULE_NAME,
            record_type=LEAD_RECORD_TYPE,
            record_public_id=str(converted_lead.public_id),
            user_public_id=current_user_public_id,
            status_before=lead.lead_status_code,
            status_after=converted_lead.lead_status_code,
            reason="Lead converted to Account and Opportunity.",
            remarks=conversion_notes,
            event_payload={
                "account_public_id": str(account.public_id),
                "opportunity_public_id": str(opportunity.public_id),
                "opportunity_status_code": opportunity.opportunity_status_code,
                "has_conversion_notes": bool(_clean_optional(payload.conversion_notes)),
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return LeadConversionResponse(
        lead=converted_lead,
        account=account,
        opportunity=opportunity,
        events=[_event_dict(account_event), _event_dict(opportunity_event), _event_dict(lead_event)],
    )


def create_lead_activity(
    db: Session,
    *,
    public_id: UUID,
    payload: LeadActivityCreate,
    current_user_public_id: str | None,
) -> LeadActivityCreatedResponse:
    lead = get_lead_by_public_id(db, str(public_id))
    if lead is None:
        raise LeadNotFoundError("Lead not found.")

    lead_id = get_lead_id_by_public_id(db, str(public_id))
    if lead_id is None:
        raise LeadNotFoundError("Lead not found.")

    values = _normalize_activity_payload(payload, current_user_public_id)
    activity_public_id = str(uuid4())

    try:
        activity = insert_lead_activity(db, public_id=activity_public_id, lead_id=lead_id, values=values)
        event = record_business_event(
            db,
            event_name=LEAD_EVENT_ACTIVITY_RECORDED,
            source_module=LEAD_MODULE_NAME,
            record_type=LEAD_ACTIVITY_RECORD_TYPE,
            record_public_id=str(activity.public_id),
            user_public_id=current_user_public_id,
            status_before=lead.lead_status_code,
            status_after=lead.lead_status_code,
            reason="Lead activity recorded.",
            event_payload={
                "lead_public_id": str(lead.public_id),
                "activity_type": activity.activity_type,
                "next_follow_up_at": activity.next_follow_up_at.isoformat() if activity.next_follow_up_at else None,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return LeadActivityCreatedResponse(activity=activity, event=_event_dict(event))


def list_leads(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    status_code: str | None = None,
    lead_source: str | None = None,
) -> list[LeadResponse]:
    normalized_status = _normalize_status(status_code) if status_code else None
    normalized_source = _normalize_source(lead_source) if lead_source else None
    return list_recent_leads(
        db,
        limit=limit,
        offset=offset,
        status_code=normalized_status,
        lead_source=normalized_source,
    )


def get_lead(db: Session, public_id: UUID) -> LeadResponse:
    lead = get_lead_by_public_id(db, str(public_id))
    if lead is None:
        raise LeadNotFoundError("Lead not found.")
    return lead


def get_lead_activities(db: Session, public_id: UUID, limit: int = 20) -> list[LeadActivityResponse]:
    lead = get_lead_by_public_id(db, str(public_id))
    if lead is None:
        raise LeadNotFoundError("Lead not found.")
    return list_lead_activities(db, lead_public_id=str(public_id), limit=limit)


