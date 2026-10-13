from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.accounts.contract import (
    ACCOUNT_EVENT_CREATED,
    ACCOUNT_MODULE_NAME,
    ACCOUNT_STATUS_QUALIFIED_PROSPECT,
    BUSINESS_PARTY_RECORD_TYPE,
    PARTY_TYPE_ORGANIZATION,
    QUALIFICATION_SOURCE_MANUAL,
)
from app.modules.accounts.repository import (
    active_account_status_exists,
    get_business_party_by_public_id,
    get_business_party_id_by_public_id,
    insert_business_party,
)
from app.modules.events.service import record_business_event
from app.modules.opportunities.contract import (
    OPPORTUNITY_ALLOWED_SOURCES,
    OPPORTUNITY_CREATE_ALLOWED_STATUSES,
    OPPORTUNITY_EVENT_CREATED,
    OPPORTUNITY_EVENT_ACCOUNT_REPAIRED,
    OPPORTUNITY_EVENT_STAGE_CHANGED,
    OPPORTUNITY_EVENT_UPDATED,
    OPPORTUNITY_INITIAL_STATUS,
    OPPORTUNITY_MODULE_NAME,
    OPPORTUNITY_RECORD_TYPE,
    OPPORTUNITY_STAGE_UPDATE_ALLOWED_STATUSES,
)
from app.modules.opportunities.repository import (
    active_opportunity_status_exists,
    get_opportunity_account_repair_context,
    get_opportunity_by_public_id,
    insert_opportunity,
    link_opportunity_business_party_if_unlinked,
    list_recent_opportunities,
    update_opportunity_by_public_id,
)
from app.modules.opportunities.schemas import (
    OpportunityAccountRepairRequest,
    OpportunityAccountRepairResponse,
    OpportunityCreate,
    OpportunityCreatedResponse,
    OpportunityResponse,
    OpportunityUpdate,
    OpportunityUpdatedResponse,
)


class OpportunityValidationError(ValueError):
    pass


class OpportunityNotFoundError(LookupError):
    pass


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_source(value: str | None) -> str:
    return (value or "").strip().lower()


def _normalize_status(value: str | None) -> str:
    return (value or OPPORTUNITY_INITIAL_STATUS).strip().upper()


def _payload_fields_set(payload: OpportunityUpdate) -> set[str]:
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
    if not active_opportunity_status_exists(db, status_code):
        raise OpportunityValidationError(f"Opportunity status is not active in workflow_status: {status_code}")


def _validate_estimated_value(value: Decimal | None) -> Decimal | None:
    if value is not None and value < Decimal("0"):
        raise OpportunityValidationError("Estimated value cannot be negative.")
    return value


def _normalize_repair_account_create_values(
    db: Session,
    *,
    payload: OpportunityAccountRepairRequest,
    opportunity_public_id: str,
    current_user_public_id: str | None,
) -> dict[str, object | None]:
    create_account = payload.create_account
    if create_account is None:
        raise OpportunityValidationError("Provide either an existing Account public id or minimal Account details.")

    account_name = _clean_optional(create_account.account_name)
    if not account_name:
        raise OpportunityValidationError("Account name is required to create a minimal Account.")

    if not active_account_status_exists(db, ACCOUNT_STATUS_QUALIFIED_PROSPECT):
        raise OpportunityValidationError(
            f"Account status is not active in workflow_status: {ACCOUNT_STATUS_QUALIFIED_PROSPECT}"
        )

    source_remarks = _clean_optional(create_account.source_remarks)
    repair_note = f"Created as minimal/provisional Account for Opportunity Account repair: {opportunity_public_id}."

    return {
        "party_type": PARTY_TYPE_ORGANIZATION,
        "account_name": account_name,
        "legal_name": _clean_optional(create_account.legal_name),
        "pan": None,
        "gstin": None,
        "account_status_code": ACCOUNT_STATUS_QUALIFIED_PROSPECT,
        "qualification_source": QUALIFICATION_SOURCE_MANUAL,
        "account_owner_user_public_id": current_user_public_id,
        "segment": _clean_optional(create_account.segment),
        "industry": _clean_optional(create_account.industry),
        "source_remarks": f"{repair_note} {source_remarks}" if source_remarks else repair_note,
        "is_strategic_account": False,
        "classification_notes": None,
        "created_by": current_user_public_id,
    }


def _validate_repair_request(payload: OpportunityAccountRepairRequest) -> None:
    has_existing_account = payload.account_public_id is not None
    has_create_account = payload.create_account is not None
    if has_existing_account == has_create_account:
        raise OpportunityValidationError("Provide either an existing Account public id or minimal Account details, not both.")


def _normalize_create_payload(
    db: Session,
    payload: OpportunityCreate,
    current_user_public_id: str | None,
) -> dict[str, object | None]:
    opportunity_source = _normalize_source(payload.opportunity_source)
    if opportunity_source not in OPPORTUNITY_ALLOWED_SOURCES:
        raise OpportunityValidationError(f"Opportunity source is not allowed: {payload.opportunity_source}")

    opportunity_status_code = _normalize_status(payload.opportunity_status_code)
    if opportunity_status_code not in OPPORTUNITY_CREATE_ALLOWED_STATUSES:
        raise OpportunityValidationError(
            f"Opportunity status cannot be used during initial Opportunity creation: {opportunity_status_code}"
        )

    _validate_active_status(db, opportunity_status_code)

    opportunity_name = payload.opportunity_name.strip()
    if not opportunity_name:
        raise OpportunityValidationError("Opportunity name is required.")

    return {
        "opportunity_name": opportunity_name,
        "opportunity_source": opportunity_source,
        "source_reference": _clean_optional(payload.source_reference),
        # Slice 3A/3C keeps link columns nullable and does not implement Lead
        # conversion or deliberate Account linkage. Later slices may populate
        # these columns deliberately.
        "business_party_id": None,
        "source_lead_id": None,
        "customer_requirement_summary": _clean_optional(payload.customer_requirement_summary),
        "estimated_value": _validate_estimated_value(payload.estimated_value),
        "expected_close_date": payload.expected_close_date,
        "opportunity_status_code": opportunity_status_code,
        "owner_user_public_id": str(payload.owner_user_public_id) if payload.owner_user_public_id else current_user_public_id,
        "created_by": current_user_public_id,
    }


def _normalize_update_payload(db: Session, payload: OpportunityUpdate) -> dict[str, object | None]:
    fields_set = _payload_fields_set(payload)
    if not fields_set:
        raise OpportunityValidationError("At least one Opportunity field must be provided for update.")

    values: dict[str, object | None] = {}

    if "opportunity_name" in fields_set:
        opportunity_name = (payload.opportunity_name or "").strip()
        if not opportunity_name:
            raise OpportunityValidationError("Opportunity name is required.")
        values["opportunity_name"] = opportunity_name

    if "opportunity_source" in fields_set:
        opportunity_source = _normalize_source(payload.opportunity_source)
        if opportunity_source not in OPPORTUNITY_ALLOWED_SOURCES:
            raise OpportunityValidationError(f"Opportunity source is not allowed: {payload.opportunity_source}")
        values["opportunity_source"] = opportunity_source

    if "source_reference" in fields_set:
        values["source_reference"] = _clean_optional(payload.source_reference)

    if "customer_requirement_summary" in fields_set:
        values["customer_requirement_summary"] = _clean_optional(payload.customer_requirement_summary)

    if "estimated_value" in fields_set:
        values["estimated_value"] = _validate_estimated_value(payload.estimated_value)

    if "expected_close_date" in fields_set:
        values["expected_close_date"] = payload.expected_close_date

    if "opportunity_status_code" in fields_set:
        opportunity_status_code = _normalize_status(payload.opportunity_status_code)
        if opportunity_status_code not in OPPORTUNITY_STAGE_UPDATE_ALLOWED_STATUSES:
            raise OpportunityValidationError(
                f"Opportunity status cannot be set to {opportunity_status_code}."
            )
        _validate_active_status(db, opportunity_status_code)
        values["opportunity_status_code"] = opportunity_status_code

    if "owner_user_public_id" in fields_set:
        values["owner_user_public_id"] = str(payload.owner_user_public_id) if payload.owner_user_public_id else None

    if not values:
        raise OpportunityValidationError("At least one Opportunity field must be provided for update.")

    return values


def create_opportunity(
    db: Session,
    *,
    payload: OpportunityCreate,
    current_user_public_id: str | None,
) -> OpportunityCreatedResponse:
    values = _normalize_create_payload(db, payload, current_user_public_id)
    opportunity_public_id = str(uuid4())
    try:
        opportunity = insert_opportunity(db, public_id=opportunity_public_id, values=values)
        event = record_business_event(
            db,
            event_name=OPPORTUNITY_EVENT_CREATED,
            source_module=OPPORTUNITY_MODULE_NAME,
            record_type=OPPORTUNITY_RECORD_TYPE,
            record_public_id=str(opportunity.public_id),
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=opportunity.opportunity_status_code,
            reason="Opportunity created through Opportunity API.",
            event_payload={
                "opportunity_source": opportunity.opportunity_source,
                "opportunity_status_code": opportunity.opportunity_status_code,
                "has_account_link": bool(opportunity.account_public_id),
                "has_source_lead_link": bool(opportunity.source_lead_public_id),
                "has_estimated_value": opportunity.estimated_value is not None,
                "expected_close_date": opportunity.expected_close_date.isoformat() if opportunity.expected_close_date else None,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return OpportunityCreatedResponse(opportunity=opportunity, event=_event_dict(event))


def update_opportunity(
    db: Session,
    *,
    public_id: UUID,
    payload: OpportunityUpdate,
    current_user_public_id: str | None,
) -> OpportunityUpdatedResponse:
    existing = get_opportunity_by_public_id(db, str(public_id))
    if existing is None:
        raise OpportunityNotFoundError("Opportunity not found.")

    values = _normalize_update_payload(db, payload)
    old_status = existing.opportunity_status_code
    old_owner = str(existing.owner_user_public_id) if existing.owner_user_public_id else None

    try:
        opportunity = update_opportunity_by_public_id(db, public_id=str(public_id), values=values)
        new_owner = str(opportunity.owner_user_public_id) if opportunity.owner_user_public_id else None

        events = [
            record_business_event(
                db,
                event_name=OPPORTUNITY_EVENT_UPDATED,
                source_module=OPPORTUNITY_MODULE_NAME,
                record_type=OPPORTUNITY_RECORD_TYPE,
                record_public_id=str(opportunity.public_id),
                user_public_id=current_user_public_id,
                status_before=old_status,
                status_after=opportunity.opportunity_status_code,
                reason="Opportunity updated through Opportunity API.",
                event_payload={
                    "updated_fields": sorted(values.keys()),
                    "opportunity_source": opportunity.opportunity_source,
                    "owner_changed": old_owner != new_owner,
                    "has_estimated_value": opportunity.estimated_value is not None,
                    "expected_close_date": opportunity.expected_close_date.isoformat() if opportunity.expected_close_date else None,
                },
            )
        ]

        if old_status != opportunity.opportunity_status_code:
            events.append(
                record_business_event(
                    db,
                    event_name=OPPORTUNITY_EVENT_STAGE_CHANGED,
                    source_module=OPPORTUNITY_MODULE_NAME,
                    record_type=OPPORTUNITY_RECORD_TYPE,
                    record_public_id=str(opportunity.public_id),
                    user_public_id=current_user_public_id,
                    status_before=old_status,
                    status_after=opportunity.opportunity_status_code,
                    reason="Opportunity stage changed.",
                    event_payload={
                        "status_before": old_status,
                        "status_after": opportunity.opportunity_status_code,
                    },
                )
            )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return OpportunityUpdatedResponse(opportunity=opportunity, events=[_event_dict(event) for event in events])


def repair_opportunity_account(
    db: Session,
    *,
    public_id: UUID,
    payload: OpportunityAccountRepairRequest,
    current_user_public_id: str | None,
) -> OpportunityAccountRepairResponse:
    _validate_repair_request(payload)
    opportunity_public_id = str(public_id)
    context = get_opportunity_account_repair_context(db, opportunity_public_id)
    if context is None:
        raise OpportunityNotFoundError("Opportunity not found.")
    if context.get("business_party_id") is not None:
        raise OpportunityValidationError("Opportunity already has a linked Account and cannot be silently relinked.")

    events: list[object] = []

    try:
        if payload.account_public_id is not None:
            account_public_id = str(payload.account_public_id)
            business_party_id = get_business_party_id_by_public_id(db, account_public_id)
            if business_party_id is None:
                raise OpportunityValidationError("Selected Account was not found.")
            account = get_business_party_by_public_id(db, account_public_id)
            if account is None:
                raise OpportunityValidationError("Selected Account was not found.")
            repair_mode = "existing_account"
        else:
            account_public_id = str(uuid4())
            values = _normalize_repair_account_create_values(
                db,
                payload=payload,
                opportunity_public_id=opportunity_public_id,
                current_user_public_id=current_user_public_id,
            )
            account = insert_business_party(db, public_id=account_public_id, values=values)
            business_party_id = get_business_party_id_by_public_id(db, account_public_id)
            if business_party_id is None:
                raise RuntimeError("Created Account could not be resolved for Opportunity repair.")
            events.append(
                record_business_event(
                    db,
                    event_name=ACCOUNT_EVENT_CREATED,
                    source_module=ACCOUNT_MODULE_NAME,
                    record_type=BUSINESS_PARTY_RECORD_TYPE,
                    record_public_id=account_public_id,
                    user_public_id=current_user_public_id,
                    status_before=None,
                    status_after=account.account_status_code,
                    reason="Minimal/provisional Account created during Opportunity Account repair.",
                    remarks=values.get("source_remarks"),
                    event_payload={
                        "party_type": account.party_type,
                        "account_status_code": account.account_status_code,
                        "qualification_source": account.qualification_source,
                        "opportunity_public_id": opportunity_public_id,
                        "customer_master_activation": "deferred",
                    },
                )
            )
            repair_mode = "created_minimal_account"

        opportunity = link_opportunity_business_party_if_unlinked(
            db,
            opportunity_public_id=opportunity_public_id,
            business_party_id=business_party_id,
        )
        if opportunity is None:
            raise OpportunityValidationError("Opportunity already has a linked Account and cannot be silently relinked.")

        events.append(
            record_business_event(
                db,
                event_name=OPPORTUNITY_EVENT_ACCOUNT_REPAIRED,
                source_module=OPPORTUNITY_MODULE_NAME,
                record_type=OPPORTUNITY_RECORD_TYPE,
                record_public_id=str(opportunity.public_id),
                user_public_id=current_user_public_id,
                status_before=str(context["opportunity_status_code"]),
                status_after=opportunity.opportunity_status_code,
                reason="Opportunity Account traceability repaired through controlled Opportunity API.",
                event_payload={
                    "repair_mode": repair_mode,
                    "account_public_id": str(account.public_id),
                    "opportunity_public_id": str(opportunity.public_id),
                    "customer_master_activation": "deferred",
                },
            )
        )

        db.commit()
    except (OpportunityNotFoundError, OpportunityValidationError):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return OpportunityAccountRepairResponse(
        opportunity=opportunity,
        account=account,
        events=[_event_dict(event) for event in events],
    )


def get_opportunity(db: Session, public_id: UUID) -> OpportunityResponse:
    opportunity = get_opportunity_by_public_id(db, str(public_id))
    if opportunity is None:
        raise OpportunityNotFoundError("Opportunity not found.")
    return opportunity


def list_opportunities(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    status_code: str | None = None,
    opportunity_source: str | None = None,
) -> list[OpportunityResponse]:
    normalized_status = _normalize_status(status_code) if status_code else None
    normalized_source = _normalize_source(opportunity_source) if opportunity_source else None
    return list_recent_opportunities(
        db,
        limit=limit,
        offset=offset,
        status_code=normalized_status,
        opportunity_source=normalized_source,
    )
