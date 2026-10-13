from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.accounts.schemas import AccountResponse
from app.modules.leads.contract import LEAD_ACTIVITY_TYPE_NOTE, LEAD_INITIAL_STATUS, LEAD_SOURCE_MANUAL
from app.modules.opportunities.schemas import OpportunityResponse
from app.shared.zoned_datetime import ZonedDateTime


class LeadCreate(BaseModel):
    lead_source: str = Field(default=LEAD_SOURCE_MANUAL, max_length=50)
    source_reference: str | None = Field(default=None, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    contact_email: str | None = Field(default=None, max_length=255)
    requirement_summary: str | None = Field(default=None, max_length=4000)
    lead_status_code: str = Field(default=LEAD_INITIAL_STATUS, max_length=50)
    assigned_to_user_public_id: UUID | None = None


class LeadUpdate(BaseModel):
    lead_source: str | None = Field(default=None, max_length=50)
    source_reference: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    contact_email: str | None = Field(default=None, max_length=255)
    requirement_summary: str | None = Field(default=None, max_length=4000)
    lead_status_code: str | None = Field(default=None, max_length=50)
    assigned_to_user_public_id: UUID | None = None


class LeadQualificationDecision(BaseModel):
    decision_status_code: str = Field(..., min_length=1, max_length=50)
    decision_notes: str | None = Field(default=None, max_length=4000)
    reason: str | None = Field(default=None, max_length=255)


class LeadResponse(BaseModel):
    public_id: UUID
    lead_source: str
    source_reference: str | None = None
    company_name: str
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    requirement_summary: str | None = None
    lead_status_code: str
    assigned_to_user_public_id: UUID | None = None
    # Read-only display names beside the user ids, resolved from app_user.display_name; None when
    # the id is null or matches no user (UI cleanup package, September 2026).
    assigned_to_display_name: str | None = None
    qualification_decision_notes: str | None = None
    qualification_reason: str | None = None
    qualification_decided_by: UUID | None = None
    qualification_decided_at: datetime | None = None
    converted_account_public_id: UUID | None = None
    converted_opportunity_public_id: UUID | None = None
    created_by: UUID | None = None
    created_by_display_name: str | None = None
    created_at: datetime
    updated_at: datetime


class LeadCreatedResponse(BaseModel):
    lead: LeadResponse
    event: dict[str, Any]


class LeadUpdatedResponse(BaseModel):
    lead: LeadResponse
    events: list[dict[str, Any]]


class LeadQualificationDecisionResponse(BaseModel):
    lead: LeadResponse
    event: dict[str, Any]


class LeadConversionCreate(BaseModel):
    account_name: str | None = Field(default=None, max_length=255)
    opportunity_name: str | None = Field(default=None, max_length=255)
    conversion_notes: str | None = Field(default=None, max_length=4000)


class LeadConversionResponse(BaseModel):
    lead: LeadResponse
    account: AccountResponse
    opportunity: OpportunityResponse
    events: list[dict[str, Any]]


class LeadActivityCreate(BaseModel):
    activity_type: str = Field(default=LEAD_ACTIVITY_TYPE_NOTE, max_length=50)
    activity_at: ZonedDateTime | None = None
    notes: str | None = Field(default=None, max_length=4000)
    outcome: str | None = Field(default=None, max_length=255)
    next_follow_up_at: ZonedDateTime | None = None


class LeadActivityResponse(BaseModel):
    public_id: UUID
    lead_public_id: UUID
    activity_type: str
    activity_at: datetime
    notes: str | None = None
    outcome: str | None = None
    next_follow_up_at: datetime | None = None
    created_by: UUID | None = None
    created_at: datetime


class LeadActivityCreatedResponse(BaseModel):
    activity: LeadActivityResponse
    event: dict[str, Any]
