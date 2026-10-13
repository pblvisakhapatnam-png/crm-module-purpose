from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import ALL_PERMISSION_CODES
from app.modules.authorization.service import has_permission
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.schemas import AuthUser

# PF-1A-E1 authorization seam.
#
# `require_permission(...)` is the drop-in replacement for the pre-existing
# `require_roles(...)` route guard. It still authenticates through the
# existing, unmodified `get_current_user()` (JWT decode -> current AppUser ->
# AuthUser); it changes only what is checked afterwards: an explicit
# application-permission code resolved against the ORA-owned compatibility
# mapping, never a route-local role tuple.
#
# This module intentionally imports from `app.modules.identity.dependencies`
# (for authentication) and `app.modules.authorization.*` only. Identity does
# not import anything from `app.modules.authorization`, except for the one
# administrative route (`GET /api/auth/roles`) that itself depends on this
# module for its own authorization - that dependency direction is
# authorization -> identity (never the reverse for authentication), so no
# import cycle exists.


def require_permission(permission_code: str) -> Callable[..., AuthUser]:
    if permission_code not in ALL_PERMISSION_CODES:
        raise ValueError(
            f"Unknown application permission code: {permission_code!r}. "
            "Register it in app.modules.authorization.contract before use."
        )

    def dependency(
        current_user: AuthUser = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> AuthUser:
        if not has_permission(db, current_user.role_codes, permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have the required permission.",
            )
        return current_user

    # PF-1A-E1 C1-01 correction: make the permission a route actually requested
    # explicitly inspectable, rather than relying on the generic Python
    # `__qualname__` every `require_permission(...)` closure shares. Route
    # authorization tests read this attribute directly off the FastAPI
    # dependant's `call` to prove WHICH permission a route requests, not merely
    # that some permission dependency exists. This is metadata for
    # introspection only; it has no effect on runtime authorization behavior.
    dependency.required_permission_code = permission_code  # type: ignore[attr-defined]

    return dependency
