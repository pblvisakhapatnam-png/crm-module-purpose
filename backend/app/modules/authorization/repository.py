from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.authorization.contract import AUTHZ_PERMISSION_TABLE, AUTHZ_ROLE_PERMISSION_TABLE


def list_active_permission_codes_for_role_codes(db: Session, role_codes: Sequence[str]) -> set[str]:
    """Return the set of active permission codes granted to any of `role_codes`.

    Both the permission and its role mapping must be active. An unknown role
    code (not present in `authz_role_permission`) simply contributes no
    permissions rather than raising, so a caller with zero recognized roles
    safely resolves to "no permissions" rather than an error.
    """

    distinct_codes = [code for code in dict.fromkeys(role_codes) if code]
    if not distinct_codes:
        return set()

    params: dict[str, object] = {f"role_{index}": code for index, code in enumerate(distinct_codes)}
    placeholders = ", ".join(f":role_{index}" for index in range(len(distinct_codes)))

    rows = db.execute(
        text(
            f"""
            SELECT DISTINCT p.permission_code
            FROM {AUTHZ_ROLE_PERMISSION_TABLE} rp
            JOIN {AUTHZ_PERMISSION_TABLE} p ON p.id = rp.permission_id
            WHERE rp.role_code IN ({placeholders})
              AND rp.is_active IS TRUE
              AND p.is_active IS TRUE
            """
        ),
        params,
    ).fetchall()

    return {row._mapping["permission_code"] for row in rows}


def list_role_permission_matrix(db: Session) -> dict[str, set[str]]:
    """Return the complete active role_code -> {permission_code} mapping.

    Used by administrative/diagnostic tooling and by tests that need to
    inspect the whole compatibility matrix rather than check a single
    role/permission pair.
    """

    rows = db.execute(
        text(
            f"""
            SELECT rp.role_code, p.permission_code
            FROM {AUTHZ_ROLE_PERMISSION_TABLE} rp
            JOIN {AUTHZ_PERMISSION_TABLE} p ON p.id = rp.permission_id
            WHERE rp.is_active IS TRUE AND p.is_active IS TRUE
            """
        )
    ).fetchall()

    matrix: dict[str, set[str]] = {}
    for row in rows:
        data = row._mapping
        matrix.setdefault(str(data["role_code"]), set()).add(str(data["permission_code"]))
    return matrix
