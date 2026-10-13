from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.modules.authorization import repository
from app.modules.authorization.contract import ALL_PERMISSION_CODES


class UnknownPermissionCodeError(ValueError):
    """Raised when code asks about a permission code that is not registered.

    This is a programming-error guard, not a business/authorization outcome:
    every permission code a route depends on must be declared in
    `app.modules.authorization.contract`. It is intentionally raised eagerly
    (see `dependencies.require_permission`) so a typo fails at route
    registration/import time rather than silently allowing or denying access
    at request time.
    """


def has_permission(db: Session, role_codes: Sequence[str], permission_code: str) -> bool:
    """Return whether any of `role_codes` currently grants `permission_code`.

    There is no implicit bypass for any role, including ADMIN: the result is
    always derived from the active `authz_role_permission` compatibility
    mapping, never from a role-name comparison.
    """

    if permission_code not in ALL_PERMISSION_CODES:
        raise UnknownPermissionCodeError(
            f"Unknown application permission code: {permission_code!r}. "
            "Register it in app.modules.authorization.contract before use."
        )

    if not role_codes:
        return False

    granted_codes = repository.list_active_permission_codes_for_role_codes(db, role_codes)
    return permission_code in granted_codes
