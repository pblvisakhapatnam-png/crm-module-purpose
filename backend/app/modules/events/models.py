from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BusinessEvent(Base):
    __tablename__ = "business_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    event_name: Mapped[str] = mapped_column(String(150), nullable=False)
    source_module: Mapped[str] = mapped_column(String(100), nullable=False)
    record_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    record_public_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    user_public_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status_before: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status_after: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remarks: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())