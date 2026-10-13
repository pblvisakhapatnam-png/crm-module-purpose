"""Holiday calendar API (HOL-1). docs/agent/contracts/holiday-calendar-api-contract.md.

Reading follows HOLIDAY_CALENDAR_READ (the six roles); saving a year, and marking it complete or not, needs
HOLIDAY_CALENDAR_MANAGE (Admin until a position is mapped under ORA-001).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import HOLIDAY_CALENDAR_MANAGE, HOLIDAY_CALENDAR_READ
from app.modules.authorization.dependencies import require_permission
from app.modules.holiday_calendar import service
from app.modules.holiday_calendar.schemas import (
    HolidayCalendarState,
    HolidayCalendarYearActionResponse,
    HolidayCalendarYearInput,
    HolidayCalendarYearResponse,
    HolidayCalendarYearsResponse,
)
from app.modules.identity.schemas import AuthUser

router = APIRouter(prefix="/api/holiday-calendar", tags=["holiday-calendar"])

_read = require_permission(HOLIDAY_CALENDAR_READ)
_manage = require_permission(HOLIDAY_CALENDAR_MANAGE)


def _run(call: Callable[[], Any]) -> Any:
    try:
        return call()
    except service.HolidayCalendarConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except service.HolidayCalendarValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


def _user(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


@router.get("/states", response_model=list[HolidayCalendarState])
def list_states_endpoint(db: Session = Depends(get_db), _: AuthUser = Depends(_read)) -> list[HolidayCalendarState]:
    return service.list_states(db)


@router.get("/years", response_model=HolidayCalendarYearsResponse)
def list_years_endpoint(db: Session = Depends(get_db), _: AuthUser = Depends(_read)) -> HolidayCalendarYearsResponse:
    return service.list_years(db)


@router.get("/years/{calendar_year}", response_model=HolidayCalendarYearResponse)
def get_year_endpoint(
    calendar_year: int = Path(...), db: Session = Depends(get_db), _: AuthUser = Depends(_read)
) -> HolidayCalendarYearResponse:
    return _run(lambda: service.get_year(db, calendar_year))


@router.put("/years/{calendar_year}", response_model=HolidayCalendarYearActionResponse)
def save_year_endpoint(
    payload: HolidayCalendarYearInput,
    calendar_year: int = Path(...),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(_manage),
) -> HolidayCalendarYearActionResponse:
    return _run(lambda: service.save_year(db, calendar_year=calendar_year, payload=payload, user_public_id=_user(user)))
