"""Account changes for the server tool. Callers own the transaction: nothing here commits."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Sequence
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.modules.events.service import payload_is_storable, record_business_event
from app.modules.identity import throttle
from app.modules.identity.service import storable_event_payload


@dataclass(frozen=True)
class DemoUser:
    public_id: str
    username: str
    display_name: str
    role_code: str


# The six demo users development and CI sign in as, with the password `password`. Until 7 October
# 2026 Alembic revision 20260629_0002 created them on every database; since TB-1 TB1-203 only
# `seed_demo_users` (development and CI) and `add_demo_author` (practice data, switched off) create
# them. The public ids and display names are the ones that migration used, so databases seeded
# either way show the same authors.
DEMO_USERS: tuple[DemoUser, ...] = (
    DemoUser("00000000-0000-0000-0000-000000000201", "admin1", "Admin User 1", "ADMIN"),
    DemoUser("00000000-0000-0000-0000-000000000202", "sales1", "Sales User 1", "SALES_USER"),
    DemoUser("00000000-0000-0000-0000-000000000203", "manager1", "Sales Manager 1", "SALES_MANAGER"),
    DemoUser("00000000-0000-0000-0000-000000000204", "finance1", "Finance User 1", "FINANCE_USER"),
    DemoUser("00000000-0000-0000-0000-000000000205", "ops1", "Operations User 1", "OPERATIONS_USER"),
    DemoUser("00000000-0000-0000-0000-000000000206", "readonly1", "Management Read Only User 1", "MANAGEMENT_READ_ONLY"),
)
DEMO_USERNAMES: tuple[str, ...] = tuple(user.username for user in DEMO_USERS)

# The demo users' password. Set only by `seed_demo_users`; otherwise used to find accounts that
# still accept it.
DEMO_PASSWORD = "password"

# Lower case only, so two accounts can never differ just by case in what a tester is told to type.
USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,99}$")
DISPLAY_NAME_MAX_LENGTH = 200

EVENT_SOURCE_MODULE = "identity"
EVENT_RECORD_TYPE = "app_user"
EVENT_REASON = "Changed with the server account tool (backend/tooling/user_admin)."


class UserAdminError(RuntimeError):
    """Raised for a request the tool refuses. The message is safe to show."""


@dataclass(frozen=True)
class UserSummary:
    public_id: str
    username: str
    display_name: str
    is_active: bool
    has_password: bool
    role_codes: tuple[str, ...]


def _summaries(rows: Sequence[object]) -> list[UserSummary]:
    users: dict[str, dict[str, object]] = {}
    for row in rows:
        mapping = row._mapping
        user = users.setdefault(
            str(mapping["public_id"]),
            {
                "public_id": str(mapping["public_id"]),
                "username": mapping["username"],
                "display_name": mapping["display_name"],
                "is_active": bool(mapping["is_active"]),
                "has_password": bool(mapping["has_password"]),
                "role_codes": [],
            },
        )
        if mapping["role_code"]:
            user["role_codes"].append(mapping["role_code"])
    return [
        UserSummary(**{**user, "role_codes": tuple(sorted(user["role_codes"]))})  # type: ignore[arg-type]
        for user in users.values()
    ]


_USER_SELECT = """
    SELECT
        u.public_id,
        u.username,
        u.display_name,
        u.is_active,
        (u.password_hash IS NOT NULL AND u.password_hash <> '') AS has_password,
        r.role_code
    FROM app_user u
    LEFT JOIN user_role ur ON ur.user_id = u.id
    LEFT JOIN role r ON r.id = ur.role_id
"""


def list_users(db: Session) -> list[UserSummary]:
    rows = db.execute(text(_USER_SELECT + " ORDER BY lower(u.username), r.role_code")).all()
    return _summaries(rows)


def get_user(db: Session, username: str) -> UserSummary | None:
    rows = db.execute(
        text(_USER_SELECT + " WHERE lower(u.username) = lower(CAST(:username AS VARCHAR)) ORDER BY r.role_code"),
        {"username": username},
    ).all()
    summaries = _summaries(rows)
    return summaries[0] if summaries else None


def _require_user(db: Session, username: str) -> UserSummary:
    user = get_user(db, username)
    if user is None:
        raise UserAdminError(f"No user named {username!r}.")
    return user


def _lock_user_row(db: Session, username: str) -> int:
    user_id = db.execute(
        text("SELECT id FROM app_user WHERE lower(username) = lower(CAST(:username AS VARCHAR)) FOR UPDATE"),
        {"username": username},
    ).scalar()
    if user_id is None:
        raise UserAdminError(f"No user named {username!r}.")
    return int(user_id)


def _role_ids(db: Session, role_codes: Iterable[str]) -> dict[str, int]:
    wanted = sorted({code.strip().upper() for code in role_codes if code.strip()})
    if not wanted:
        raise UserAdminError("Give at least one role.")
    rows = db.execute(
        text("SELECT role_code, id FROM role WHERE is_active IS TRUE AND role_code = ANY(:codes)"),
        {"codes": wanted},
    ).all()
    found = {row._mapping["role_code"]: int(row._mapping["id"]) for row in rows}
    unknown = [code for code in wanted if code not in found]
    if unknown:
        available = db.execute(text("SELECT role_code FROM role WHERE is_active IS TRUE ORDER BY role_code")).scalars()
        raise UserAdminError(f"Unknown or inactive role(s) {unknown}. Available: {list(available)}.")
    return found


def _record(
    db: Session,
    *,
    event_name: str,
    user: UserSummary,
    status_before: str | None = None,
    status_after: str | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    record_business_event(
        db,
        event_name=event_name,
        source_module=EVENT_SOURCE_MODULE,
        record_type=EVENT_RECORD_TYPE,
        record_public_id=user.public_id,
        status_before=status_before,
        status_after=status_after,
        reason=EVENT_REASON,
        # The username, or a fixed stand-in when the log would refuse any of the payload (TB-1 TB1-204 part a; the
        # record id names the account): a command on an account a database already holds - unlock, end-sign-ins, a
        # reset, a role change - must still do what it says.
        event_payload=storable_event_payload({"username": user.username, **(payload or {})}),
    )


def _status(active: bool) -> str:
    return "ACTIVE" if active else "INACTIVE"


def create_user(
    db: Session,
    *,
    username: str,
    display_name: str,
    role_codes: Iterable[str],
    password_hash: str,
) -> UserSummary:
    if not USERNAME_PATTERN.fullmatch(username):
        raise UserAdminError(
            "A username must be 3 to 100 characters: lower-case letters, digits, '.', '_' or '-', "
            "starting with a letter or digit."
        )
    display_name = display_name.strip()
    if not display_name or len(display_name) > DISPLAY_NAME_MAX_LENGTH:
        raise UserAdminError(f"A display name must be 1 to {DISPLAY_NAME_MAX_LENGTH} characters.")
    # A new account's names are refused when the event log would refuse them - since TB-1 TB1-500, text shaped like a
    # credential - rather than written into a record whose every event would then withhold them; an account a database
    # already holds is still managed, its events withheld (`_record`).
    if not payload_is_storable({"username": username, "display_name": display_name}):
        raise UserAdminError(
            "The event log refuses text shaped like a password, an access token or a private key, "
            "including in a display name. Choose another."
        )
    return _insert_user(
        db,
        public_id=str(uuid4()),
        username=username,
        display_name=display_name,
        role_codes=role_codes,
        password_hash=password_hash,
        active=True,
    )


def _insert_user(
    db: Session,
    *,
    public_id: str,
    username: str,
    display_name: str,
    role_codes: Iterable[str],
    password_hash: str | None,
    active: bool,
) -> UserSummary:
    if get_user(db, username) is not None:
        raise UserAdminError(f"A user named {username!r} already exists (usernames ignore case).")
    roles = _role_ids(db, role_codes)

    user_id = db.execute(
        text(
            """
            INSERT INTO app_user (public_id, username, display_name, password_hash, is_active)
            VALUES (:public_id, :username, :display_name, :password_hash, :is_active)
            RETURNING id
            """
        ),
        {
            "public_id": public_id,
            "username": username,
            "display_name": display_name,
            "password_hash": password_hash,
            "is_active": active,
        },
    ).scalar_one()
    for role_id in roles.values():
        db.execute(
            text("INSERT INTO user_role (user_id, role_id) VALUES (:user_id, :role_id)"),
            {"user_id": user_id, "role_id": role_id},
        )

    user = _require_user(db, username)
    _record(
        db,
        event_name="UserAccountCreated",
        user=user,
        status_after=_status(active),
        payload={"display_name": user.display_name, "role_codes": list(user.role_codes)},
    )
    return user


def seed_demo_users(db: Session) -> list[str]:
    """Make each demo user exist, be active, hold its role and accept the demo password.

    For development and CI only: `seed-demo-users`, the one caller, refuses outside a development
    APP_ENV (TB-1 TB1-203). Only what differs is changed, and each change is recorded as the tool's
    other changes are, so a second run changes and records nothing. Returns the usernames changed.
    """
    changed: list[str] = []
    for demo in DEMO_USERS:
        user = get_user(db, demo.username)
        if user is None:
            _insert_user(
                db,
                public_id=demo.public_id,
                username=demo.username,
                display_name=demo.display_name,
                role_codes=[demo.role_code],
                password_hash=hash_password(DEMO_PASSWORD),
                active=True,
            )
            changed.append(demo.username)
            continue
        user_id = _lock_user_row(db, demo.username)
        password_hash = db.execute(
            text("SELECT password_hash FROM app_user WHERE id = :user_id"), {"user_id": user_id}
        ).scalar()
        accepts_password = verify_password(DEMO_PASSWORD, password_hash)
        if demo.role_code not in user.role_codes:
            set_roles(db, username=demo.username, role_codes=[*user.role_codes, demo.role_code])
        if not user.is_active:
            set_active(db, username=demo.username, active=True)
        if not accepts_password:
            set_password_hash(db, username=demo.username, password_hash=hash_password(DEMO_PASSWORD))
        if demo.role_code not in user.role_codes or not user.is_active or not accepts_password:
            changed.append(demo.username)
    return changed


def add_demo_author(db: Session, username: str) -> UserSummary:
    """Create one missing demo user switched off and with no password, as an author of practice data.

    Outside development no database gets the demo users (TB-1 TB1-203), but the hosted sites'
    practice data is written as them, so testers can tell it from their own work. A user made here
    cannot sign in: it is inactive and has no password, as `retire_users` leaves one.
    """
    demo = next((user for user in DEMO_USERS if user.username == username.strip().lower()), None)
    if demo is None:
        raise UserAdminError(f"{username!r} is not a demo user.")
    return _insert_user(
        db,
        public_id=demo.public_id,
        username=demo.username,
        display_name=demo.display_name,
        role_codes=[demo.role_code],
        password_hash=None,
        active=False,
    )


def set_roles(db: Session, *, username: str, role_codes: Iterable[str]) -> UserSummary:
    user_id = _lock_user_row(db, username)
    before = _require_user(db, username)
    roles = _role_ids(db, role_codes)

    db.execute(text("DELETE FROM user_role WHERE user_id = :user_id"), {"user_id": user_id})
    for role_id in roles.values():
        db.execute(
            text("INSERT INTO user_role (user_id, role_id) VALUES (:user_id, :role_id)"),
            {"user_id": user_id, "role_id": role_id},
        )
    db.execute(text("UPDATE app_user SET updated_at = CURRENT_TIMESTAMP WHERE id = :user_id"), {"user_id": user_id})

    after = _require_user(db, username)
    _record(
        db,
        event_name="UserRolesChanged",
        user=after,
        payload={"role_codes_before": list(before.role_codes), "role_codes_after": list(after.role_codes)},
    )
    return after


def _end_sign_ins(db: Session, user_id: int) -> None:
    """Every sign-in token the account holds is refused from its next request (TB-1 TB1-204 part a)."""
    db.execute(text("UPDATE app_user SET token_version = token_version + 1 WHERE id = :user_id"), {"user_id": user_id})


def set_active(db: Session, *, username: str, active: bool) -> UserSummary:
    user_id = _lock_user_row(db, username)
    before = _require_user(db, username)
    db.execute(
        text("UPDATE app_user SET is_active = :active, updated_at = CURRENT_TIMESTAMP WHERE id = :user_id"),
        {"active": active, "user_id": user_id},
    )
    if not active:
        # Disabling refused them already; ending them too means enabling the account again does not bring back a
        # sign-in made before it was disabled.
        _end_sign_ins(db, user_id)
    after = _require_user(db, username)
    _record(
        db,
        event_name="UserAccountEnabled" if active else "UserAccountDisabled",
        user=after,
        status_before=_status(before.is_active),
        status_after=_status(after.is_active),
    )
    return after


def set_password_hash(db: Session, *, username: str, password_hash: str) -> UserSummary:
    user_id = _lock_user_row(db, username)
    db.execute(
        text("UPDATE app_user SET password_hash = :password_hash, updated_at = CURRENT_TIMESTAMP WHERE id = :user_id"),
        {"password_hash": password_hash, "user_id": user_id},
    )
    _end_sign_ins(db, user_id)
    user = _require_user(db, username)
    _record(db, event_name="UserPasswordReset", user=user)
    return user


def end_sign_ins(db: Session, *, username: str) -> UserSummary:
    """End every sign-in the account holds without changing its password - for a lost phone, say."""
    user_id = _lock_user_row(db, username)
    _end_sign_ins(db, user_id)
    user = _require_user(db, username)
    _record(db, event_name="UserSignInsEnded", user=user)
    return user


def unlock_sign_in(db: Session, *, username: str) -> bool:
    """Lift a stop on signing in as `username` early (TB-1 TB1-204 part a). True if it was stopped.

    Any name can be stopped, an account's or not, so this does not require an account; the event is recorded only
    when one exists, because it is about that account.
    """
    unlocked = throttle.unlock(db, username, datetime.now(timezone.utc))
    user = get_user(db, username)
    if unlocked and user is not None:
        _record(db, event_name="UserSignInUnlocked", user=user)
    return unlocked


def retire_users(db: Session, usernames: Iterable[str]) -> list[UserSummary]:
    """Disable each named user and remove its password, so it cannot sign in even if re-enabled.

    Records it created stay attributed to it. A name with no user is skipped. Returns the users
    that were changed; one already disabled with no password is left alone.
    """
    retired: list[UserSummary] = []
    for username in usernames:
        if get_user(db, username) is None:
            continue
        user_id = _lock_user_row(db, username)
        before = _require_user(db, username)
        if not before.is_active and not before.has_password:
            continue
        db.execute(
            text(
                "UPDATE app_user SET is_active = FALSE, password_hash = NULL, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = :user_id"
            ),
            {"user_id": user_id},
        )
        _end_sign_ins(db, user_id)
        after = _require_user(db, username)
        _record(
            db,
            event_name="UserAccountRetired",
            user=after,
            status_before=_status(before.is_active),
            status_after=_status(after.is_active),
        )
        retired.append(after)
    return retired


def current_transaction_id(db: Session) -> str:
    """This transaction's id, so a commit whose confirmation is lost can be looked up afterwards."""
    return str(db.execute(text("SELECT CAST(pg_current_xact_id() AS TEXT)")).scalar_one())


def transaction_status(db: Session, transaction_id: str) -> str | None:
    """PostgreSQL's answer for a recent transaction: "committed", "aborted" or "in progress"."""
    return db.execute(
        text("SELECT pg_xact_status(CAST(:transaction_id AS xid8))"), {"transaction_id": transaction_id}
    ).scalar()


def users_accepting_password(db: Session, password: str) -> list[str]:
    """Usernames of active accounts that would accept `password` at sign-in."""
    rows = db.execute(
        text("SELECT username, password_hash FROM app_user WHERE is_active IS TRUE ORDER BY lower(username)")
    ).all()
    return [
        row._mapping["username"]
        for row in rows
        if verify_password(password, row._mapping["password_hash"])
    ]
