from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BusinessEventCreate(BaseModel):
    event_name: str = Field(min_length=1, max_length=150)
    source_module: str = Field(min_length=1, max_length=100)
    record_type: str | None = Field(default=None, max_length=100)
    record_public_id: str | None = Field(default=None, max_length=36)
    user_public_id: str | None = Field(default=None, max_length=36)
    status_before: str | None = Field(default=None, max_length=100)
    status_after: str | None = Field(default=None, max_length=100)
    reason: str | None = Field(default=None, max_length=500)
    remarks: str | None = Field(default=None, max_length=1000)
    correlation_id: str | None = Field(default=None, max_length=100)
    event_payload: dict[str, Any] | None = None


class BusinessEventSummary(BaseModel):
    public_id: str
    event_name: str
    source_module: str
    record_type: str | None
    record_public_id: str | None
    user_public_id: str | None
    event_timestamp: datetime
    status_before: str | None
    status_after: str | None
    reason: str | None
    remarks: str | None
    correlation_id: str | None
    event_payload: dict[str, Any] | None = None