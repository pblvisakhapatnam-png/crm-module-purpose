from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import EVENTS_READ
from app.modules.authorization.dependencies import require_permission
from app.modules.events.schemas import BusinessEventSummary
from app.modules.events.service import get_recent_business_events
from app.modules.identity.schemas import AuthUser

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/recent", response_model=list[BusinessEventSummary])
def recent_events(
    limit: int = Query(default=25, ge=1, le=100),
    record_type: str | None = Query(default=None, max_length=100),
    record_public_id: str | None = Query(default=None, max_length=36),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(EVENTS_READ)),
) -> list[BusinessEventSummary]:
    return get_recent_business_events(
        db,
        limit=limit,
        record_type=record_type,
        record_public_id=record_public_id,
    )