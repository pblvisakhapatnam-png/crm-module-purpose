from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

# payload_is_storable: for a caller that must know, before recording, whether the guard would refuse a payload.
from app.modules.events.repository import create_business_event, list_recent_business_events, payload_is_storable
from app.modules.events.schemas import BusinessEventCreate, BusinessEventSummary


def record_business_event(
    db: Session,
    *,
    event_name: str,
    source_module: str,
    record_type: str | None = None,
    record_public_id: str | None = None,
    user_public_id: str | None = None,
    status_before: str | None = None,
    status_after: str | None = None,
    reason: str | None = None,
    remarks: str | None = None,
    correlation_id: str | None = None,
    event_payload: dict[str, Any] | None = None,
) -> BusinessEventSummary:
    return create_business_event(
        db,
        BusinessEventCreate(
            event_name=event_name,
            source_module=source_module,
            record_type=record_type,
            record_public_id=record_public_id,
            user_public_id=user_public_id,
            status_before=status_before,
            status_after=status_after,
            reason=reason,
            remarks=remarks,
            correlation_id=correlation_id,
            event_payload=event_payload,
        ),
    )


def get_recent_business_events(
    db: Session,
    limit: int = 25,
    *,
    record_type: str | None = None,
    record_public_id: str | None = None,
) -> list[BusinessEventSummary]:
    return list_recent_business_events(
        db,
        limit=limit,
        record_type=record_type,
        record_public_id=record_public_id,
    )