from __future__ import annotations

import re
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.accounts.contract import (
    ACCOUNT_ADDRESS_EVENT_CREATED,
    ACCOUNT_CLASSIFICATION_EVENT_UPDATED,
    ACCOUNT_ALLOWED_ADDRESS_TYPES,
    ACCOUNT_ALLOWED_DOCUMENT_STATUSES,
    ACCOUNT_ALLOWED_DOCUMENT_STORAGE_MODES,
    ACCOUNT_ALLOWED_DOCUMENT_TYPES,
    ACCOUNT_ALLOWED_TAX_VERIFICATION_STATES,
    ACCOUNT_ALLOWED_PARTY_TYPES,
    ACCOUNT_ALLOWED_QUALIFICATION_SOURCES,
    ACCOUNT_CONTACT_EVENT_CREATED,
    ACCOUNT_CREATE_ALLOWED_STATUSES,
    ACCOUNT_EVENT_CREATED,
    ACCOUNT_DOCUMENT_EVENT_RECORDED,
    ACCOUNT_MODULE_NAME,
    ACCOUNT_GSTIN_EVENT_CREATED,
    ACCOUNT_TAX_PROFILE_EVENT_UPSERTED,
    BUSINESS_PARTY_ADDRESS_RECORD_TYPE,
    BUSINESS_PARTY_CONTACT_RECORD_TYPE,
    BUSINESS_PARTY_GSTIN_RECORD_TYPE,
    BUSINESS_PARTY_RECORD_TYPE,
    DOCUMENT_METADATA_RECORD_TYPE,
    BUSINESS_PARTY_TAX_PROFILE_RECORD_TYPE,
    PARTY_TYPE_ORGANIZATION,
    QUALIFICATION_SOURCE_MANUAL,
    TAX_VERIFICATION_STATE_ENTERED_NOT_VERIFIED,
    TAX_VERIFICATION_STATE_NOT_AVAILABLE,
)
from app.modules.accounts.repository import (
    active_account_status_exists,
    get_business_party_by_public_id,
    get_business_party_classification_by_public_id,
    get_business_party_id_by_public_id,
    insert_business_party,
    insert_business_party_address,
    insert_business_party_contact,
    insert_account_document_metadata,
    insert_business_party_gstin,
    get_business_party_tax_profile_by_account_public_id,
    gstin_exists,
    list_business_party_addresses,
    list_business_party_contacts,
    list_account_document_metadata,
    list_business_party_gstins,
    list_recent_business_parties,
    update_business_party_classification,
    upsert_business_party_tax_profile,
)
from app.modules.accounts.schemas import (
    AccountAddressCreate,
    AccountAddressCreatedResponse,
    AccountAddressResponse,
    AccountClassificationResponse,
    AccountClassificationUpdate,
    AccountClassificationUpdatedResponse,
    AccountContactCreate,
    AccountContactCreatedResponse,
    AccountContactResponse,
    AccountDocumentCreate,
    AccountDocumentCreatedResponse,
    AccountDocumentResponse,
    AccountCreate,
    AccountGstinCreate,
    AccountGstinCreatedResponse,
    AccountGstinResponse,
    AccountCreatedResponse,
    AccountResponse,
    AccountTaxProfileBundleResponse,
    AccountTaxProfileResponse,
    AccountTaxProfileSavedResponse,
    AccountTaxProfileUpsert,
)
from app.modules.events.service import record_business_event

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COUNTRY_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")
STATE_CODE_PATTERN = re.compile(r"^[0-9]{2}$")


class AccountValidationError(ValueError):
    """Raised when Account API input violates business rules."""


class AccountNotFoundError(ValueError):
    """Raised when an Account public id cannot be resolved."""


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_code(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    return cleaned.upper() if cleaned else None


def _clean_source(value: str | None) -> str:
    cleaned = _clean_text(value)
    return cleaned.lower() if cleaned else QUALIFICATION_SOURCE_MANUAL


def _clean_uuid(value: UUID | str | None) -> str | None:
    return str(value) if value else None


def _normalize_account_payload(
    db: Session,
    payload: AccountCreate,
    *,
    current_user_public_id: str | None,
) -> dict[str, Any]:
    party_type = (_clean_text(payload.party_type) or PARTY_TYPE_ORGANIZATION).lower()
    if party_type not in ACCOUNT_ALLOWED_PARTY_TYPES:
        raise AccountValidationError("Only organisation Accounts are supported.")

    account_name = _clean_text(payload.account_name)
    if not account_name:
        raise AccountValidationError("Account name is required.")

    pan = _clean_code(payload.pan)
    if pan and not PAN_PATTERN.fullmatch(pan):
        raise AccountValidationError("PAN must be a valid 10-character Indian PAN if provided.")

    gstin = _clean_code(payload.gstin)
    if gstin and not GSTIN_PATTERN.fullmatch(gstin):
        raise AccountValidationError("GSTIN must be a valid 15-character Indian GSTIN if provided.")

    account_status_code = _clean_code(payload.account_status_code) or ACCOUNT_CREATE_ALLOWED_STATUSES[0]
    if account_status_code not in ACCOUNT_CREATE_ALLOWED_STATUSES:
        raise AccountValidationError("A new Account can start only as Draft or Qualified Prospect.")

    if not active_account_status_exists(db, account_status_code):
        raise AccountValidationError(f"Account status is not active in workflow_status: {account_status_code}")

    qualification_source = _clean_source(payload.qualification_source)
    if qualification_source not in ACCOUNT_ALLOWED_QUALIFICATION_SOURCES:
        raise AccountValidationError("Invalid Account qualification source.")

    return {
        "party_type": party_type,
        "account_name": account_name,
        "legal_name": _clean_text(payload.legal_name),
        "pan": pan,
        "gstin": gstin,
        "account_status_code": account_status_code,
        "qualification_source": qualification_source,
        "account_owner_user_public_id": _clean_uuid(payload.account_owner_user_public_id) or current_user_public_id,
        "segment": _clean_text(payload.segment),
        "industry": _clean_text(payload.industry),
        "source_remarks": _clean_text(payload.source_remarks),
        "is_strategic_account": bool(payload.is_strategic_account),
        "classification_notes": _clean_text(payload.classification_notes),
        "created_by": current_user_public_id,
    }


def _normalize_contact_payload(
    payload: AccountContactCreate,
    *,
    current_user_public_id: str | None,
) -> dict[str, Any]:
    contact_name = _clean_text(payload.contact_name)
    if not contact_name:
        raise AccountValidationError("Contact name is required.")

    phone = _clean_text(payload.phone)
    email = _clean_text(payload.email)
    if email:
        email = email.lower()
        if not EMAIL_PATTERN.fullmatch(email):
            raise AccountValidationError("Email must be a valid email address if provided.")

    return {
        "contact_name": contact_name,
        "designation": _clean_text(payload.designation),
        "department": _clean_text(payload.department),
        "phone": phone,
        "email": email,
        "is_primary": bool(payload.is_primary),
        "remarks": _clean_text(payload.remarks),
        "created_by": current_user_public_id,
    }


def _normalize_address_payload(
    payload: AccountAddressCreate,
    *,
    current_user_public_id: str | None,
) -> dict[str, Any]:
    address_type_code = _clean_code(payload.address_type_code)
    if address_type_code not in ACCOUNT_ALLOWED_ADDRESS_TYPES:
        raise AccountValidationError("Invalid Account address type.")

    address_line1 = _clean_text(payload.address_line1)
    if not address_line1:
        raise AccountValidationError("Address line 1 is required.")

    city = _clean_text(payload.city)
    if not city:
        raise AccountValidationError("City is required.")

    state = _clean_text(payload.state)
    if not state:
        raise AccountValidationError("State is required.")

    country_code = _clean_code(payload.country_code) or "IN"
    if not COUNTRY_CODE_PATTERN.fullmatch(country_code):
        raise AccountValidationError("Country code must be a valid two-letter code.")

    return {
        "address_type_code": address_type_code,
        "address_line1": address_line1,
        "address_line2": _clean_text(payload.address_line2),
        "city": city,
        "district": _clean_text(payload.district),
        "state": state,
        "postal_code": _clean_text(payload.postal_code),
        "country_code": country_code,
        "is_primary": bool(payload.is_primary),
        "remarks": _clean_text(payload.remarks),
        "created_by": current_user_public_id,
    }



def _normalize_tax_verification_state(value: str | None, *, default: str) -> str:
    state = _clean_code(value) or default
    if state not in ACCOUNT_ALLOWED_TAX_VERIFICATION_STATES:
        raise AccountValidationError("Invalid PAN/GST verification state.")
    return state


def _normalize_tax_profile_payload(
    payload: AccountTaxProfileUpsert,
    *,
    current_user_public_id: str | None,
) -> dict[str, Any]:
    pan = _clean_code(payload.pan)
    if pan and not PAN_PATTERN.fullmatch(pan):
        raise AccountValidationError("PAN must match Indian PAN format, for example ABCDE1234F.")

    return {
        "pan": pan,
        "pan_verification_state_code": _normalize_tax_verification_state(
            payload.pan_verification_state_code,
            default=TAX_VERIFICATION_STATE_NOT_AVAILABLE if not pan else TAX_VERIFICATION_STATE_ENTERED_NOT_VERIFIED,
        ),
        "pan_legal_name": _clean_text(payload.pan_legal_name),
        "remarks": _clean_text(payload.remarks),
        "created_by": current_user_public_id,
    }


def _normalize_gstin_payload(
    payload: AccountGstinCreate,
    *,
    current_user_public_id: str | None,
) -> dict[str, Any]:
    gstin = _clean_code(payload.gstin)
    if not gstin or not GSTIN_PATTERN.fullmatch(gstin):
        raise AccountValidationError("GSTIN must match Indian GSTIN format, for example 29ABCDE1234F1Z5.")

    state_code = _clean_code(payload.state_code) or gstin[:2]
    if not STATE_CODE_PATTERN.fullmatch(state_code):
        raise AccountValidationError("GSTIN state code must be two digits.")
    if state_code != gstin[:2]:
        raise AccountValidationError("GSTIN state code must match the first two digits of the GSTIN.")

    return {
        "gstin": gstin,
        "gstin_verification_state_code": _normalize_tax_verification_state(
            payload.gstin_verification_state_code,
            default=TAX_VERIFICATION_STATE_ENTERED_NOT_VERIFIED,
        ),
        "state_code": state_code,
        "state_name": _clean_text(payload.state_name),
        "legal_name": _clean_text(payload.legal_name),
        "trade_name": _clean_text(payload.trade_name),
        "is_primary": bool(payload.is_primary),
        "remarks": _clean_text(payload.remarks),
        "created_by": current_user_public_id,
    }


def _normalize_document_payload(
    payload: AccountDocumentCreate,
    *,
    current_user_public_id: str | None,
) -> dict[str, Any]:
    document_type = _clean_code(payload.document_type)
    if document_type not in ACCOUNT_ALLOWED_DOCUMENT_TYPES:
        raise AccountValidationError("Invalid Account document type.")

    file_name = _clean_text(payload.file_name)
    if not file_name:
        raise AccountValidationError("Document file name is required.")

    storage_mode = _clean_text(payload.storage_mode) or "external_link"
    if storage_mode not in ACCOUNT_ALLOWED_DOCUMENT_STORAGE_MODES:
        raise AccountValidationError("Invalid Account document storage mode.")

    status = _clean_text(payload.status) or "Linked"
    if status not in ACCOUNT_ALLOWED_DOCUMENT_STATUSES:
        raise AccountValidationError("Invalid Account document status.")

    return {
        "document_type": document_type,
        "file_name": file_name,
        "original_file_name": _clean_text(payload.original_file_name) or file_name,
        "storage_mode": storage_mode,
        "storage_path_or_url": _clean_text(payload.storage_path_or_url),
        "version_no": payload.version_no,
        "status": status,
        "uploaded_by": current_user_public_id,
        "remarks": _clean_text(payload.remarks),
    }



def _normalize_classification_payload(payload: AccountClassificationUpdate) -> dict[str, Any]:
    return {
        "account_owner_user_public_id": _clean_uuid(payload.account_owner_user_public_id),
        "segment": _clean_text(payload.segment),
        "industry": _clean_text(payload.industry),
        "is_strategic_account": bool(payload.is_strategic_account),
        "classification_notes": _clean_text(payload.classification_notes),
    }

def create_account(
    db: Session,
    *,
    payload: AccountCreate,
    current_user_public_id: str | None,
) -> AccountCreatedResponse:
    values = _normalize_account_payload(
        db,
        payload,
        current_user_public_id=current_user_public_id,
    )
    public_id = str(uuid4())

    try:
        account = insert_business_party(db, public_id=public_id, values=values)
        event = record_business_event(
            db,
            event_name=ACCOUNT_EVENT_CREATED,
            source_module=ACCOUNT_MODULE_NAME,
            record_type=BUSINESS_PARTY_RECORD_TYPE,
            record_public_id=public_id,
            user_public_id=current_user_public_id,
            status_before=None,
            status_after=account.account_status_code,
            reason="Account created through Account API.",
            # No Account event copies the user's own text - remarks or notes - into the append-only
            # log: it may hold a PAN, a GSTIN or a person's name. It stays on the record (TB-1 TB1-202).
            event_payload={
                "party_type": account.party_type,
                "account_status_code": account.account_status_code,
                "qualification_source": account.qualification_source,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AccountCreatedResponse(
        account=account,
        event={
            "public_id": event.public_id,
            "event_name": event.event_name,
            "record_type": event.record_type,
            "record_public_id": event.record_public_id,
        },
    )


def get_account(db: Session, public_id: UUID) -> AccountResponse | None:
    return get_business_party_by_public_id(db, str(public_id))


def list_accounts(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    status_code: str | None = None,
) -> list[AccountResponse]:
    normalized_status = _clean_code(status_code)
    return list_recent_business_parties(
        db,
        limit=limit,
        offset=offset,
        status_code=normalized_status,
    )



def get_account_classification(
    db: Session,
    *,
    account_public_id: UUID,
) -> AccountClassificationResponse:
    account_public_id_text = str(account_public_id)
    classification = get_business_party_classification_by_public_id(db, account_public_id_text)
    if classification is None:
        raise AccountNotFoundError("Account not found.")
    return classification


def update_account_classification(
    db: Session,
    *,
    account_public_id: UUID,
    payload: AccountClassificationUpdate,
    current_user_public_id: str | None,
) -> AccountClassificationUpdatedResponse:
    account_public_id_text = str(account_public_id)
    before = get_business_party_classification_by_public_id(db, account_public_id_text)
    if before is None:
        raise AccountNotFoundError("Account not found.")

    values = _normalize_classification_payload(payload)

    try:
        classification = update_business_party_classification(
            db,
            account_public_id=account_public_id_text,
            values=values,
        )
        event = record_business_event(
            db,
            event_name=ACCOUNT_CLASSIFICATION_EVENT_UPDATED,
            source_module=ACCOUNT_MODULE_NAME,
            record_type=BUSINESS_PARTY_RECORD_TYPE,
            record_public_id=account_public_id_text,
            user_public_id=current_user_public_id,
            reason="Account ownership/classification updated through Account API.",
            event_payload={
                "account_public_id": account_public_id_text,
                "owner_before": str(before.account_owner_user_public_id) if before.account_owner_user_public_id else None,
                "owner_after": str(classification.account_owner_user_public_id) if classification.account_owner_user_public_id else None,
                "segment": classification.segment,
                "industry": classification.industry,
                "is_strategic_account": classification.is_strategic_account,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AccountClassificationUpdatedResponse(
        classification=classification,
        event={
            "public_id": event.public_id,
            "event_name": event.event_name,
            "record_type": event.record_type,
            "record_public_id": event.record_public_id,
        },
    )

def create_account_contact(
    db: Session,
    *,
    account_public_id: UUID,
    payload: AccountContactCreate,
    current_user_public_id: str | None,
) -> AccountContactCreatedResponse:
    account_public_id_text = str(account_public_id)
    business_party_id = get_business_party_id_by_public_id(db, account_public_id_text)
    if business_party_id is None:
        raise AccountNotFoundError("Account not found.")

    values = _normalize_contact_payload(payload, current_user_public_id=current_user_public_id)
    public_id = str(uuid4())

    try:
        contact = insert_business_party_contact(
            db,
            public_id=public_id,
            business_party_id=business_party_id,
            values=values,
        )
        event = record_business_event(
            db,
            event_name=ACCOUNT_CONTACT_EVENT_CREATED,
            source_module=ACCOUNT_MODULE_NAME,
            record_type=BUSINESS_PARTY_CONTACT_RECORD_TYPE,
            record_public_id=public_id,
            user_public_id=current_user_public_id,
            reason="Account contact created through Account API.",
            # The contact's public id, never the person's name: a business contact's name is
            # personal data, which stays out of the event log (TB-1 TB1-202).
            event_payload={
                "account_public_id": account_public_id_text,
                "contact_public_id": public_id,
                "is_primary": contact.is_primary,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AccountContactCreatedResponse(
        contact=contact,
        event={
            "public_id": event.public_id,
            "event_name": event.event_name,
            "record_type": event.record_type,
            "record_public_id": event.record_public_id,
        },
    )


def list_account_contacts(db: Session, *, account_public_id: UUID) -> list[AccountContactResponse]:
    account_public_id_text = str(account_public_id)
    business_party_id = get_business_party_id_by_public_id(db, account_public_id_text)
    if business_party_id is None:
        raise AccountNotFoundError("Account not found.")

    return list_business_party_contacts(db, account_public_id=account_public_id_text)


def create_account_address(
    db: Session,
    *,
    account_public_id: UUID,
    payload: AccountAddressCreate,
    current_user_public_id: str | None,
) -> AccountAddressCreatedResponse:
    account_public_id_text = str(account_public_id)
    business_party_id = get_business_party_id_by_public_id(db, account_public_id_text)
    if business_party_id is None:
        raise AccountNotFoundError("Account not found.")

    values = _normalize_address_payload(payload, current_user_public_id=current_user_public_id)
    public_id = str(uuid4())

    try:
        address = insert_business_party_address(
            db,
            public_id=public_id,
            business_party_id=business_party_id,
            values=values,
        )
        event = record_business_event(
            db,
            event_name=ACCOUNT_ADDRESS_EVENT_CREATED,
            source_module=ACCOUNT_MODULE_NAME,
            record_type=BUSINESS_PARTY_ADDRESS_RECORD_TYPE,
            record_public_id=public_id,
            user_public_id=current_user_public_id,
            reason="Account address created through Account API.",
            event_payload={
                "account_public_id": account_public_id_text,
                "address_type_code": address.address_type_code,
                "city": address.city,
                "state": address.state,
                "is_primary": address.is_primary,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AccountAddressCreatedResponse(
        address=address,
        event={
            "public_id": event.public_id,
            "event_name": event.event_name,
            "record_type": event.record_type,
            "record_public_id": event.record_public_id,
        },
    )


def list_account_addresses(db: Session, *, account_public_id: UUID) -> list[AccountAddressResponse]:
    account_public_id_text = str(account_public_id)
    business_party_id = get_business_party_id_by_public_id(db, account_public_id_text)
    if business_party_id is None:
        raise AccountNotFoundError("Account not found.")

    return list_business_party_addresses(db, account_public_id=account_public_id_text)


def get_account_tax_profile_bundle(
    db: Session,
    *,
    account_public_id: UUID,
) -> AccountTaxProfileBundleResponse:
    account_public_id_text = str(account_public_id)
    business_party_id = get_business_party_id_by_public_id(db, account_public_id_text)
    if business_party_id is None:
        raise AccountNotFoundError("Account not found.")

    return AccountTaxProfileBundleResponse(
        tax_profile=get_business_party_tax_profile_by_account_public_id(
            db,
            account_public_id=account_public_id_text,
        ),
        gstins=list_business_party_gstins(db, account_public_id=account_public_id_text),
    )


def upsert_account_tax_profile(
    db: Session,
    *,
    account_public_id: UUID,
    payload: AccountTaxProfileUpsert,
    current_user_public_id: str | None,
) -> AccountTaxProfileSavedResponse:
    account_public_id_text = str(account_public_id)
    business_party_id = get_business_party_id_by_public_id(db, account_public_id_text)
    if business_party_id is None:
        raise AccountNotFoundError("Account not found.")

    values = _normalize_tax_profile_payload(payload, current_user_public_id=current_user_public_id)
    public_id = str(uuid4())

    try:
        tax_profile = upsert_business_party_tax_profile(
            db,
            public_id=public_id,
            business_party_id=business_party_id,
            values=values,
        )
        event = record_business_event(
            db,
            event_name=ACCOUNT_TAX_PROFILE_EVENT_UPSERTED,
            source_module=ACCOUNT_MODULE_NAME,
            record_type=BUSINESS_PARTY_TAX_PROFILE_RECORD_TYPE,
            record_public_id=str(tax_profile.public_id),
            user_public_id=current_user_public_id,
            reason="Account PAN tax profile captured through Account API.",
            event_payload={
                "account_public_id": account_public_id_text,
                "pan_present": bool(tax_profile.pan),
                "pan_verification_state_code": tax_profile.pan_verification_state_code,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AccountTaxProfileSavedResponse(
        tax_profile=tax_profile,
        event={
            "public_id": event.public_id,
            "event_name": event.event_name,
            "record_type": event.record_type,
            "record_public_id": event.record_public_id,
        },
    )


def create_account_gstin(
    db: Session,
    *,
    account_public_id: UUID,
    payload: AccountGstinCreate,
    current_user_public_id: str | None,
) -> AccountGstinCreatedResponse:
    account_public_id_text = str(account_public_id)
    business_party_id = get_business_party_id_by_public_id(db, account_public_id_text)
    if business_party_id is None:
        raise AccountNotFoundError("Account not found.")

    values = _normalize_gstin_payload(payload, current_user_public_id=current_user_public_id)
    if gstin_exists(db, values["gstin"]):
        raise AccountValidationError("GSTIN already exists in the Account GSTIN register.")

    public_id = str(uuid4())

    try:
        gstin = insert_business_party_gstin(
            db,
            public_id=public_id,
            business_party_id=business_party_id,
            values=values,
        )
        event = record_business_event(
            db,
            event_name=ACCOUNT_GSTIN_EVENT_CREATED,
            source_module=ACCOUNT_MODULE_NAME,
            record_type=BUSINESS_PARTY_GSTIN_RECORD_TYPE,
            record_public_id=public_id,
            user_public_id=current_user_public_id,
            reason="Account GSTIN captured through Account API.",
            # The GSTIN's public id and state code, never the GSTIN: characters 3 to 12 of it are the
            # holder's PAN, which stays out of the event log as the PAN event's does (TB-1 TB1-202).
            event_payload={
                "account_public_id": account_public_id_text,
                "gstin_public_id": public_id,
                "state_code": gstin.state_code,
                "gstin_verification_state_code": gstin.gstin_verification_state_code,
                "is_primary": gstin.is_primary,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AccountGstinCreatedResponse(
        gstin=gstin,
        event={
            "public_id": event.public_id,
            "event_name": event.event_name,
            "record_type": event.record_type,
            "record_public_id": event.record_public_id,
        },
    )


def list_account_documents(db: Session, *, account_public_id: UUID) -> list[AccountDocumentResponse]:
    account_public_id_text = str(account_public_id)
    business_party_id = get_business_party_id_by_public_id(db, account_public_id_text)
    if business_party_id is None:
        raise AccountNotFoundError("Account not found.")

    return list_account_document_metadata(db, account_public_id=account_public_id_text)


def create_account_document(
    db: Session,
    *,
    account_public_id: UUID,
    payload: AccountDocumentCreate,
    current_user_public_id: str | None,
) -> AccountDocumentCreatedResponse:
    account_public_id_text = str(account_public_id)
    business_party_id = get_business_party_id_by_public_id(db, account_public_id_text)
    if business_party_id is None:
        raise AccountNotFoundError("Account not found.")

    values = _normalize_document_payload(payload, current_user_public_id=current_user_public_id)
    public_id = str(uuid4())

    try:
        document = insert_account_document_metadata(
            db,
            public_id=public_id,
            account_public_id=account_public_id_text,
            values=values,
        )
        event = record_business_event(
            db,
            event_name=ACCOUNT_DOCUMENT_EVENT_RECORDED,
            source_module=ACCOUNT_MODULE_NAME,
            record_type=DOCUMENT_METADATA_RECORD_TYPE,
            record_public_id=public_id,
            user_public_id=current_user_public_id,
            reason="Account document metadata recorded through Account API.",
            event_payload={
                "account_public_id": account_public_id_text,
                "document_type": document.document_type,
                "storage_mode": document.storage_mode,
                "status": document.status,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AccountDocumentCreatedResponse(
        document=document,
        event={
            "public_id": event.public_id,
            "event_name": event.event_name,
            "record_type": event.record_type,
            "record_public_id": event.record_public_id,
        },
    )
