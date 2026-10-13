from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.accounts.schemas import AccountResponse
from app.modules.opportunities.contract import OPPORTUNITY_INITIAL_STATUS, OPPORTUNITY_SOURCE_MANUAL


class OpportunityCreate(BaseModel):
    opportunity_name: str = Field(..., min_length=1, max_length=255)
    opportunity_source: str = Field(default=OPPORTUNITY_SOURCE_MANUAL, max_length=50)
    source_reference: str | None = Field(default=None, max_length=255)
    customer_requirement_summary: str | None = Field(default=None, max_length=4000)
    estimated_value: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    expected_close_date: date | None = None
    opportunity_status_code: str = Field(default=OPPORTUNITY_INITIAL_STATUS, max_length=50)
    owner_user_public_id: UUID | None = None


class OpportunityUpdate(BaseModel):
    opportunity_name: str | None = Field(default=None, max_length=255)
    opportunity_source: str | None = Field(default=None, max_length=50)
    source_reference: str | None = Field(default=None, max_length=255)
    customer_requirement_summary: str | None = Field(default=None, max_length=4000)
    estimated_value: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    expected_close_date: date | None = None
    opportunity_status_code: str | None = Field(default=None, max_length=50)
    owner_user_public_id: UUID | None = None


class OpportunityResponse(BaseModel):
    public_id: UUID
    opportunity_name: str
    opportunity_source: str
    source_reference: str | None = None
    account_public_id: UUID | None = None
    source_lead_public_id: UUID | None = None
    customer_requirement_summary: str | None = None
    estimated_value: Decimal | None = None
    expected_close_date: date | None = None
    opportunity_status_code: str
    owner_user_public_id: UUID | None = None
    # Read-only display names beside the user ids, resolved from app_user.display_name; None when
    # the id is null or matches no user (UI cleanup package, September 2026).
    owner_display_name: str | None = None
    created_by: UUID | None = None
    created_by_display_name: str | None = None
    created_at: datetime
    updated_at: datetime


class OpportunityCreatedResponse(BaseModel):
    opportunity: OpportunityResponse
    event: dict[str, Any]


class OpportunityUpdatedResponse(BaseModel):
    opportunity: OpportunityResponse
    events: list[dict[str, Any]]


class OpportunityAccountCreateRepair(BaseModel):
    account_name: str = Field(..., min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    segment: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    source_remarks: str | None = Field(default=None, max_length=4000)


class OpportunityAccountRepairRequest(BaseModel):
    account_public_id: UUID | None = None
    create_account: OpportunityAccountCreateRepair | None = None


class OpportunityAccountRepairResponse(BaseModel):
    opportunity: OpportunityResponse
    account: AccountResponse
    events: list[dict[str, Any]]
