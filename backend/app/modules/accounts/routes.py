from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
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
    AccountCreate,
    AccountDocumentCreate,
    AccountDocumentCreatedResponse,
    AccountDocumentResponse,
    AccountGstinCreate,
    AccountGstinCreatedResponse,
    AccountTaxProfileBundleResponse,
    AccountTaxProfileSavedResponse,
    AccountTaxProfileUpsert,
    AccountCreatedResponse,
    AccountResponse,
)
from app.modules.accounts.service import (
    AccountNotFoundError,
    AccountValidationError,
    create_account,
    create_account_address,
    create_account_contact,
    get_account_classification,
    update_account_classification,
    create_account_document,
    create_account_gstin,
    get_account,
    get_account_tax_profile_bundle,
    list_account_addresses,
    list_account_documents,
    list_account_contacts,
    list_accounts,
    upsert_account_tax_profile,
)
from app.modules.authorization.contract import (
    ACCOUNT_CLASSIFICATION_MANAGE,
    ACCOUNT_CREATE as ACCOUNT_CREATE_PERMISSION,
    ACCOUNT_DOCUMENT_CAPTURE,
    ACCOUNT_READ as ACCOUNT_READ_PERMISSION,
    ACCOUNT_TAX_CAPTURE,
    ACCOUNT_TAX_VERIFY,
)
from app.modules.authorization.dependencies import require_permission
from app.modules.authorization.service import has_permission
from app.modules.identity.schemas import AuthUser

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

ACCOUNT_VERIFIED_TAX_STATES = ("VERIFIED", "REJECTED_INCORRECT")


def _user_public_id(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


def _assert_tax_verification_permission(db: Session, user: AuthUser, requested_state: str | None) -> None:
    state = (requested_state or "").upper()
    if state in ACCOUNT_VERIFIED_TAX_STATES and not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PAN/GST verification states can be set only by Finance / Accounts role.",
        )


@router.post("", response_model=AccountCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_account_endpoint(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(ACCOUNT_CREATE_PERMISSION)),
) -> AccountCreatedResponse:
    try:
        return create_account(
            db,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except AccountValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[AccountResponse])
def list_accounts_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    status_code: str | None = Query(default=None, max_length=50),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(ACCOUNT_READ_PERMISSION)),
) -> list[AccountResponse]:
    return list_accounts(db, limit=limit, offset=offset, status_code=status_code)



@router.get("/{public_id}/classification", response_model=AccountClassificationResponse)
def get_account_classification_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(ACCOUNT_READ_PERMISSION)),
) -> AccountClassificationResponse:
    try:
        return get_account_classification(db, account_public_id=public_id)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put("/{public_id}/classification", response_model=AccountClassificationUpdatedResponse, status_code=status.HTTP_200_OK)
def update_account_classification_endpoint(
    public_id: UUID,
    payload: AccountClassificationUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(ACCOUNT_CLASSIFICATION_MANAGE)),
) -> AccountClassificationUpdatedResponse:
    try:
        return update_account_classification(
            db,
            account_public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AccountValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

@router.get("/{public_id}/contacts", response_model=list[AccountContactResponse])
def list_account_contacts_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(ACCOUNT_READ_PERMISSION)),
) -> list[AccountContactResponse]:
    try:
        return list_account_contacts(db, account_public_id=public_id)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/{public_id}/contacts", response_model=AccountContactCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_account_contact_endpoint(
    public_id: UUID,
    payload: AccountContactCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(ACCOUNT_CREATE_PERMISSION)),
) -> AccountContactCreatedResponse:
    try:
        return create_account_contact(
            db,
            account_public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AccountValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/{public_id}/addresses", response_model=list[AccountAddressResponse])
def list_account_addresses_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(ACCOUNT_READ_PERMISSION)),
) -> list[AccountAddressResponse]:
    try:
        return list_account_addresses(db, account_public_id=public_id)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/{public_id}/addresses", response_model=AccountAddressCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_account_address_endpoint(
    public_id: UUID,
    payload: AccountAddressCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(ACCOUNT_CREATE_PERMISSION)),
) -> AccountAddressCreatedResponse:
    try:
        return create_account_address(
            db,
            account_public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AccountValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/{public_id}/tax-profile", response_model=AccountTaxProfileBundleResponse)
def get_account_tax_profile_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(ACCOUNT_READ_PERMISSION)),
) -> AccountTaxProfileBundleResponse:
    try:
        return get_account_tax_profile_bundle(db, account_public_id=public_id)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/{public_id}/tax-profile", response_model=AccountTaxProfileSavedResponse, status_code=status.HTTP_200_OK)
def upsert_account_tax_profile_endpoint(
    public_id: UUID,
    payload: AccountTaxProfileUpsert,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(ACCOUNT_TAX_CAPTURE)),
) -> AccountTaxProfileSavedResponse:
    _assert_tax_verification_permission(db, current_user, payload.pan_verification_state_code)
    try:
        return upsert_account_tax_profile(
            db,
            account_public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AccountValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/{public_id}/gstins", response_model=AccountGstinCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_account_gstin_endpoint(
    public_id: UUID,
    payload: AccountGstinCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(ACCOUNT_TAX_CAPTURE)),
) -> AccountGstinCreatedResponse:
    _assert_tax_verification_permission(db, current_user, payload.gstin_verification_state_code)
    try:
        return create_account_gstin(
            db,
            account_public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AccountValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/{public_id}/documents", response_model=list[AccountDocumentResponse])
def list_account_documents_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(ACCOUNT_READ_PERMISSION)),
) -> list[AccountDocumentResponse]:
    try:
        return list_account_documents(db, account_public_id=public_id)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/{public_id}/documents", response_model=AccountDocumentCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_account_document_endpoint(
    public_id: UUID,
    payload: AccountDocumentCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(ACCOUNT_DOCUMENT_CAPTURE)),
) -> AccountDocumentCreatedResponse:
    try:
        return create_account_document(
            db,
            account_public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AccountValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/{public_id}", response_model=AccountResponse)
def get_account_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(ACCOUNT_READ_PERMISSION)),
) -> AccountResponse:
    account = get_account(db, public_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )
    return account
