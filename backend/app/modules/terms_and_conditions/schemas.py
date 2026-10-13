from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TermsAndConditionsClauseResponse(BaseModel):
    public_id: UUID
    clause_id: str
    business_line: str
    clause_category: str
    source_clause_number: str | None = None
    title: str
    clause_text: str
    mandatory_default: bool
    risk_category: str | None = None
    applies_to_header: bool
    applies_to_line: bool
    requires_approval_if_omitted: bool
    requires_approval_if_modified: bool
    active: bool
    source_reference: str | None = None
    created_at: datetime
    updated_at: datetime

