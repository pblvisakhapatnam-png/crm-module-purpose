from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def _rows_to_user(rows: list[object]) -> dict[str, object] | None:
    if not rows:
        return None

    first = rows[0]._mapping
    return {
        "id": first["id"],
        "public_id": first["public_id"],
        "username": first["username"],
        "display_name": first["display_name"],
        "password_hash": first["password_hash"],
        "is_active": bool(first["is_active"]),
        "token_version": int(first["token_version"]),
        "roles": [row._mapping["role_name"] for row in rows if row._mapping["role_name"]],
        "role_codes": [row._mapping["role_code"] for row in rows if row._mapping["role_code"]],
    }


def get_user_with_roles_by_username(db: Session, username: str) -> dict[str, object] | None:
    rows = db.execute(
        text(
            """
            SELECT
                u.id,
                u.public_id,
                u.username,
                u.display_name,
                u.password_hash,
                u.is_active,
                u.token_version,
                r.role_code,
                r.role_name
            FROM app_user u
            LEFT JOIN user_role ur ON ur.user_id = u.id
            LEFT JOIN role r ON r.id = ur.role_id AND r.is_active IS TRUE
            -- Usernames are matched case-insensitively. SQL Server's default collation did this
            -- implicitly; PostgreSQL compares case-sensitively, so the rule is now explicit. The
            -- ux_app_user_username_lower unique index enforces the matching uniqueness rule and
            -- lets this lookup use the index rather than scanning. The row's stored username is
            -- returned unchanged, so responses and tokens carry the canonical form.
            WHERE lower(u.username) = lower(CAST(:username AS VARCHAR))
            ORDER BY r.role_name
            """
        ),
        {"username": username},
    ).all()
    return _rows_to_user(rows)


def get_user_with_roles_by_public_id(db: Session, public_id: str) -> dict[str, object] | None:
    rows = db.execute(
        text(
            """
            SELECT
                u.id,
                u.public_id,
                u.username,
                u.display_name,
                u.password_hash,
                u.is_active,
                u.token_version,
                r.role_code,
                r.role_name
            FROM app_user u
            LEFT JOIN user_role ur ON ur.user_id = u.id
            LEFT JOIN role r ON r.id = ur.role_id AND r.is_active IS TRUE
            WHERE u.public_id = :public_id
            ORDER BY r.role_name
            """
        ),
        {"public_id": public_id},
    ).all()
    return _rows_to_user(rows)


def replace_password_hash(db: Session, user_id: int, old_hash: str, new_hash: str) -> bool:
    """Swap `old_hash` for `new_hash`, only if `old_hash` is still the stored one. True if it was replaced.

    For the stronger hash written at a successful sign-in (TB-1 TB1-204 part a): a password reset that landed in
    the meantime is never overwritten. Not a password change, so `updated_at` and `token_version` are left alone.
    """
    replaced = db.execute(
        text(
            "UPDATE app_user SET password_hash = :new_hash "
            "WHERE id = :user_id AND password_hash = :old_hash RETURNING id"
        ),
        {"user_id": user_id, "old_hash": old_hash, "new_hash": new_hash},
    ).scalar()
    return replaced is not None


def list_active_roles(db: Session) -> list[dict[str, str]]:
    rows = db.execute(
        text(
            """
            SELECT role_code, role_name
            FROM role
            WHERE is_active IS TRUE
            ORDER BY role_name
            """
        )
    ).all()
    return [
        {"role_code": row._mapping["role_code"], "role_name": row._mapping["role_name"]}
        for row in rows
    ]