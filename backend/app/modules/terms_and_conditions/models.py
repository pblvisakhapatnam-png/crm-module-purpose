from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.modules.terms_and_conditions.contract import TC_CLAUSE_LIBRARY_TABLE


class TermsAndConditionsClause(Base):
    __tablename__ = TC_CLAUSE_LIBRARY_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    clause_id: Mapped[str] = mapped_column(Unicode(50), unique=True, nullable=False)
    business_line: Mapped[str] = mapped_column(String(50), nullable=False)
    clause_category: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    source_clause_number: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    title: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    clause_text: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    mandatory_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_category: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    applies_to_header: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    applies_to_line: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_approval_if_omitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_approval_if_modified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_reference: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
