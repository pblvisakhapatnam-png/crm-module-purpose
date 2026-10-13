import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import IDENTITY_ROLE_CATALOG_READ
from app.modules.authorization.dependencies import require_permission
from app.modules.events.service import record_business_event
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.repository import list_active_roles
from app.modules.identity.schemas import AuthUser, LoginRequest, LoginResponse, RoleSummary
from app.modules.identity.service import (
    AuthenticationError,
    SignInStoppedError,
    login_user,
    signed_in_event_payload,
    stop_message,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={429: {"description": "Too many failed sign-ins for this username; try again later."}},
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    now = datetime.now(timezone.utc)
    try:
        response = login_user(db, payload.username, payload.password, now)
        record_business_event(
            db,
            event_name="UserLoginSucceeded",
            source_module="identity",
            record_type="app_user",
            record_public_id=response.user.public_id,
            user_public_id=response.user.public_id,
            reason="User signed in.",
            event_payload=signed_in_event_payload(response.user),
        )
        db.commit()
        return response
    except AuthenticationError as exc:
        # A stop this attempt started was recorded with the stop itself (`login_user`); this is the attempt's own.
        record_business_event(
            db,
            event_name="UserLoginFailed",
            source_module="identity",
            record_type="auth_login",
            record_public_id=exc.account_public_id,
            reason=(
                "Refused: the username is stopped after repeated failed sign-ins."
                if isinstance(exc, SignInStoppedError)
                else "Invalid credentials."
            ),
            event_payload=exc.event_payload,
        )
        db.commit()
        if exc.stopped_until is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=stop_message(exc.stopped_until, now),
                headers={"Retry-After": str(max(1, math.ceil((exc.stopped_until - now).total_seconds())))},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        ) from exc


@router.get("/me", response_model=AuthUser)
def me(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
    return current_user


@router.get("/roles", response_model=list[RoleSummary])
def roles(
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(IDENTITY_ROLE_CATALOG_READ)),
) -> list[RoleSummary]:
    return [RoleSummary(**role) for role in list_active_roles(db)]
