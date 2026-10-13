from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, password_hash_needs_upgrade, verify_password
from app.modules.events.service import payload_is_storable, record_business_event
from app.modules.identity import throttle
from app.modules.identity.repository import get_user_with_roles_by_username, replace_password_hash
from app.modules.identity.schemas import AuthUser, LoginResponse


class AuthenticationError(ValueError):
    """Raised when username/password authentication fails.

    `event_payload` is what the failure's event may record (see `storable_event_payload`), never what was typed (TB-1
    TB1-204 part a); `account_public_id` is the account the typed name reaches, if any, for the event's record id.
    `stopped_until` is set when this failure stopped the name, or when the name was already stopped.
    """

    def __init__(
        self,
        *,
        event_payload: dict[str, object],
        account_public_id: str | None,
        stopped_until: datetime | None = None,
    ) -> None:
        super().__init__("Invalid credentials.")
        self.event_payload = event_payload
        self.account_public_id = account_public_id
        self.stopped_until = stopped_until


class SignInStoppedError(AuthenticationError):
    """The name was already stopped: refused without checking the password."""


def stop_message(stopped_until: datetime, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    minutes = max(1, math.ceil((stopped_until - now).total_seconds() / 60))
    unit = "minute" if minutes == 1 else "minutes"
    return f"Too many failed sign-ins for this username. Try again in {minutes} {unit}."


def to_auth_user(user: dict[str, object]) -> AuthUser:
    return AuthUser(
        public_id=str(user["public_id"]),
        username=str(user["username"]),
        display_name=str(user["display_name"]),
        roles=[str(role) for role in user.get("roles", [])],
        role_codes=[str(role_code) for role_code in user.get("role_codes", [])],
    )


# In an event's payload in place of a username the event log would refuse. A fixed value, so always storable; the
# account itself is the event's record id, its public id - a UUID the application chose.
USERNAME_WITHHELD: dict[str, object] = {"username_withheld": True}


def storable_event_payload(payload: dict[str, object]) -> dict[str, object]:
    """`payload` if the event log can store it whole, else USERNAME_WITHHELD: text the log refuses in any field - a
    username, a role code, a display name; since TB-1 TB1-500, text shaped like a credential - never stops a sign-in or
    an account-tool command (TB-1 TB1-204 part a). A payload names an account by its username; the event's record id
    names it either way. Callers compose the whole payload first and withhold it once (review rounds 11 and 12)."""
    return payload if payload_is_storable(payload) else dict(USERNAME_WITHHELD)


def signed_in_event_payload(user: AuthUser) -> dict[str, object]:
    """The success event's payload: the account and its role codes, whole or withheld (`storable_event_payload`).
    Built here, so the route reads no role codes (`tests/test_authorization_route_migration_guard.py`)."""
    return storable_event_payload({"username": user.username, "role_codes": user.role_codes})


def _record_stop_event(
    db: Session, event_name: str, reason: str, payload: dict[str, object], account_public_id: str | None
) -> None:
    record_business_event(
        db, event_name=event_name, source_module="identity", record_type="auth_login",
        record_public_id=account_public_id, reason=reason, event_payload=payload,
    )


def login_user(db: Session, username: str, password: str, now: datetime | None = None) -> LoginResponse:
    """Check one sign-in. Commits old attempts' pruning on its own, then the attempt's count - with the stop's event,
    when the attempt starts one - before the password is checked (see `throttle`); the caller owns, and commits, the
    rest: the success's event, or the failure's."""
    now = now or datetime.now(timezone.utc)
    throttle.prune(db, now)
    db.commit()
    user = get_user_with_roles_by_username(db, username)
    # The account, or only that the typed name reaches no account: what was typed is never recorded, because it is
    # sometimes a password typed in the wrong box.
    named: dict[str, object] = {"username": str(user["username"])} if user else {"username_known": False}
    event_payload = storable_event_payload(named)
    account_public_id = str(user["public_id"]) if user else None

    attempt = throttle.register_attempt(db, username, now)
    if attempt.stops_until is not None:
        _record_stop_event(
            db, "UserSignInLocked", "Stopped after repeated failed sign-ins.",
            storable_event_payload({**named, "locked_until": attempt.stops_until.isoformat()}), account_public_id,
        )
    db.commit()
    if attempt.stopped_until is not None:
        raise SignInStoppedError(
            event_payload=event_payload, account_public_id=account_public_id, stopped_until=attempt.stopped_until
        )

    # Always checked, against a stand-in when there is no usable hash, and always at the same cost (see
    # `verify_password`), so a refusal takes the same time whether or not the account exists, is active or has a
    # password.
    stored_hash = str(user["password_hash"]) if user and user.get("password_hash") else None
    password_ok = verify_password(password, stored_hash)
    if not user or not user.get("is_active") or not password_ok:
        raise AuthenticationError(
            event_payload=event_payload, account_public_id=account_public_id, stopped_until=attempt.stops_until
        )

    # Only this attempt and those before it are cleared: one that came after, still being checked or failed, counts.
    if throttle.clear_attempts(db, attempt, now):
        _record_stop_event(
            db, "UserSignInUnlocked", "Lifted by a successful sign-in: too few attempts came after it to keep the stop.",
            event_payload, account_public_id,
        )
    if stored_hash is not None and password_hash_needs_upgrade(stored_hash):
        replace_password_hash(db, int(user["id"]), stored_hash, hash_password(password))

    auth_user = to_auth_user(user)
    token = create_access_token(
        subject=auth_user.username,
        user_public_id=auth_user.public_id,
        role_codes=auth_user.role_codes,
        token_version=int(user["token_version"]),
    )
    return LoginResponse(access_token=token, user=auth_user)
