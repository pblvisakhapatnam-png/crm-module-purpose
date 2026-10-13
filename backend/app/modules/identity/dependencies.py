from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenError, decode_access_token, token_version_of
from app.modules.identity.repository import get_user_with_roles_by_public_id
from app.modules.identity.schemas import AuthUser
from app.modules.identity.service import to_auth_user

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    user = get_user_with_roles_by_public_id(db, str(payload["user_public_id"]))
    if not user or not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user is no longer active.",
        )

    # A password reset, disabling or retiring the account, or the account tool's end-sign-ins raised the account's
    # number after this token was issued (TB-1 TB1-204 part a).
    if token_version_of(payload) != user["token_version"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This sign-in has ended. Sign in again.",
        )

    return to_auth_user(user)