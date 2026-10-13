from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.accounts.contract import (
    ACCOUNT_STATUS_DRAFT,
    ADDRESS_TYPE_COMMUNICATION,
    PARTY_TYPE_ORGANIZATION,
    ACCOUNT_DOCUMENT_STORAGE_EXTERNAL_LINK,
    ACCOUNT_DOCUMENT_STATUS_LINKED,
    TAX_VERIFICATION_STATE_ENTERED_NOT_VERIFIED,
    TAX_VERIFICATION_STATE_NOT_AVAILABLE,
    QUALIFICATION_SOURCE_MANUAL,
)


class AccountCreate(BaseModel):
    party_type: str = Field(default=PARTY_TYPE_ORGANIZATION, max_length=50)
    account_name: str = Field(..., min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    pan: str | None = Field(default=None, max_length=10)
    gstin: str | None = Field(default=None, max_length=15)
    account_status_code: str = Field(default=ACCOUNT_STATUS_DRAFT, max_length=50)
    qualification_source: str = Field(default=QUALIFICATION_SOURCE_MANUAL, max_length=50)
    account_owner_user_public_id: UUID | None = None
    segment: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    source_remarks: str | None = Field(default=None, max_length=4000)
    is_strategic_account: bool = False
    classification_notes: str | None = Field(default=None, max_length=4000)


class AccountResponse(BaseModel):
    public_id: UUID
    party_type: str
    account_name: str
    legal_name: str | None = None
    pan: str | None = None
    gstin: str | None = None
    account_status_code: str
    qualification_source: str | None = None
    account_owner_user_public_id: UUID | None = None
    # Read-only display names beside the user ids, resolved from app_user.display_name; None when
    # the id is null or matches no user (UI cleanup package, September 2026).
    account_owner_display_name: str | None = None
    segment: str | None = None
    industry: str | None = None
    source_remarks: str | None = None
    is_strategic_account: bool = False
    classification_notes: str | None = None
    created_by: UUID | None = None
    created_by_display_name: str | None = None
    created_at: datetime
    updated_at: datetime


class AccountCreatedResponse(BaseModel):
    account: AccountResponse
    event: dict[str, Any]


class AccountClassificationUpdate(BaseModel):
    account_owner_user_public_id: UUID | None = None
    segment: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    is_strategic_account: bool = False
    classification_notes: str | None = Field(default=None, max_length=4000)


class AccountClassificationResponse(BaseModel):
    account_public_id: UUID
    account_owner_user_public_id: UUID | None = None
    # Read-only, resolved from app_user.display_name; None when the id is null or matches no user.
    account_owner_display_name: str | None = None
    segment: str | None = None
    industry: str | None = None
    is_strategic_account: bool = False
    classification_notes: str | None = None
    updated_at: datetime


class AccountClassificationUpdatedResponse(BaseModel):
    classification: AccountClassificationResponse
    event: dict[str, Any]


class AccountContactCreate(BaseModel):
    contact_name: str = Field(..., min_length=1, max_length=255)
    designation: str | None = Field(default=None, max_length=150)
    department: str | None = Field(default=None, max_length=150)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    is_primary: bool = False
    remarks: str | None = Field(default=None, max_length=4000)


class AccountContactResponse(BaseModel):
    public_id: UUID
    account_public_id: UUID
    contact_name: str
    designation: str | None = None
    department: str | None = None
    phone: str | None = None
    email: str | None = None
    is_primary: bool
    is_active: bool
    remarks: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AccountContactCreatedResponse(BaseModel):
    contact: AccountContactResponse
    event: dict[str, Any]


class AccountAddressCreate(BaseModel):
    address_type_code: str = Field(default=ADDRESS_TYPE_COMMUNICATION, max_length=50)
    address_line1: str = Field(..., min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(..., min_length=1, max_length=150)
    district: str | None = Field(default=None, max_length=150)
    state: str = Field(..., min_length=1, max_length=150)
    postal_code: str | None = Field(default=None, max_length=20)
    country_code: str = Field(default="IN", min_length=2, max_length=2)
    is_primary: bool = False
    remarks: str | None = Field(default=None, max_length=4000)


class AccountAddressResponse(BaseModel):
    public_id: UUID
    account_public_id: UUID
    address_type_code: str
    address_line1: str
    address_line2: str | None = None
    city: str
    district: str | None = None
    state: str
    postal_code: str | None = None
    country_code: str
    is_primary: bool
    is_active: bool
    remarks: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AccountAddressCreatedResponse(BaseModel):
    address: AccountAddressResponse
    event: dict[str, Any]


class AccountTaxProfileUpsert(BaseModel):
    pan: str | None = Field(default=None, max_length=10)
    pan_verification_state_code: str = Field(default=TAX_VERIFICATION_STATE_NOT_AVAILABLE, max_length=50)
    pan_legal_name: str | None = Field(default=None, max_length=255)
    remarks: str | None = Field(default=None, max_length=4000)


class AccountTaxProfileResponse(BaseModel):
    public_id: UUID
    account_public_id: UUID
    pan: str | None = None
    pan_verification_state_code: str
    pan_legal_name: str | None = None
    remarks: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AccountGstinCreate(BaseModel):
    gstin: str = Field(..., min_length=15, max_length=15)
    gstin_verification_state_code: str = Field(default=TAX_VERIFICATION_STATE_ENTERED_NOT_VERIFIED, max_length=50)
    state_code: str | None = Field(default=None, max_length=2)
    state_name: str | None = Field(default=None, max_length=150)
    legal_name: str | None = Field(default=None, max_length=255)
    trade_name: str | None = Field(default=None, max_length=255)
    is_primary: bool = False
    remarks: str | None = Field(default=None, max_length=4000)


class AccountGstinResponse(BaseModel):
    public_id: UUID
    account_public_id: UUID
    gstin: str
    gstin_verification_state_code: str
    state_code: str
    state_name: str | None = None
    legal_name: str | None = None
    trade_name: str | None = None
    is_primary: bool
    is_active: bool
    remarks: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AccountTaxProfileBundleResponse(BaseModel):
    tax_profile: AccountTaxProfileResponse | None = None
    gstins: list[AccountGstinResponse]


class AccountTaxProfileSavedResponse(BaseModel):
    tax_profile: AccountTaxProfileResponse
    event: dict[str, Any]


class AccountGstinCreatedResponse(BaseModel):
    gstin: AccountGstinResponse
    event: dict[str, Any]


class AccountDocumentCreate(BaseModel):
    document_type: str = Field(..., min_length=1, max_length=100)
    file_name: str = Field(..., min_length=1, max_length=255)
    original_file_name: str | None = Field(default=None, max_length=255)
    storage_mode: str = Field(default=ACCOUNT_DOCUMENT_STORAGE_EXTERNAL_LINK, max_length=50)
    storage_path_or_url: str | None = Field(default=None, max_length=1000)
    version_no: int = Field(default=1, ge=1)
    status: str = Field(default=ACCOUNT_DOCUMENT_STATUS_LINKED, max_length=50)
    remarks: str | None = Field(default=None, max_length=1000)


class AccountDocumentResponse(BaseModel):
    public_id: UUID
    account_public_id: UUID
    document_type: str
    file_name: str
    original_file_name: str | None = None
    storage_mode: str
    storage_path_or_url: str | None = None
    version_no: int
    status: str
    uploaded_by: UUID | None = None
    uploaded_at: datetime
    remarks: str | None = None


class AccountDocumentCreatedResponse(BaseModel):
    document: AccountDocumentResponse
    event: dict[str, Any]
