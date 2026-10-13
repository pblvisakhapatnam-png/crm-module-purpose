from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from app.core.config import STANDARD_PASSWORD_HASH_ITERATIONS, get_settings

PASSWORD_ALGORITHM = "pbkdf2_sha256"


def password_iterations() -> int:
    """The work factor in force: 600,000 (`config.STANDARD_PASSWORD_HASH_ITERATIONS`) everywhere but development and
    CI, which may set fewer, and never more. A hash stored with fewer is still accepted, and is replaced at that user's
    next successful sign-in (`password_hash_needs_upgrade`)."""
    return get_settings().password_hash_iterations

# Stands in for a stored hash when there is none to check - an unknown username, or an account with no password -
# so refusing those costs the same hashing time as refusing a wrong password (TB1-204 part a, item e).
_UNUSABLE_HASH_SALT = os.urandom(16)


class TokenError(ValueError):
    """Raised when a bearer token is invalid or expired."""


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def hash_password(password: str, salt_hex: str | None = None) -> str:
    if not password:
        raise ValueError("Password must not be empty.")

    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    iterations = password_iterations()
    derived_key = _derive(password, salt, iterations)
    return f"{PASSWORD_ALGORITHM}${iterations}${salt.hex()}${derived_key.hex()}"


def _parse_password_hash(stored_hash: str | None) -> tuple[int, bytes, bytes] | None:
    """The iterations, salt and expected key of a stored hash, or None when it is not one this module could have
    written: the algorithm, from 1 to 600,000 iterations - the most any setting can write, so a hash stays usable
    whatever the setting later is, and none costs a refusal more than the stand-in does where the count is 600,000 -
    a non-empty hex salt and a 32-byte hex key. Anything else, from whatever source, is unusable rather than an error
    (TB-1 TB1-204 part a)."""
    if not stored_hash:
        return None
    try:
        algorithm, iterations_text, salt_hex, expected_hex = stored_hash.split("$", 3)
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
    except ValueError:
        return None
    if algorithm != PASSWORD_ALGORITHM or not 1 <= iterations <= STANDARD_PASSWORD_HASH_ITERATIONS:
        return None
    if not salt or len(expected) != hashlib.sha256().digest_size:
        return None
    return iterations, salt, expected


def verify_password(password: str, stored_hash: str | None) -> bool:
    """Whether `password` matches `stored_hash`. Every check costs exactly `password_iterations()` of hashing.

    So the time an answer takes does not say whether the account exists, has a password, or has an older hash: with
    no usable hash the same work is done against a stand-in, and a hash stored with fewer iterations is topped up to
    the current count whether or not it matches - a caller may still refuse a right password, a disabled account's,
    and that refusal must cost what any other does (TB-1 TB1-204 part a, item e). Where development or CI set fewer
    than 600,000, a hash stored with more than the setting is checked at its own count, which costs more; nowhere
    else can that happen, since 600,000 is both the count there and the most a hash may claim.
    """
    current = password_iterations()
    parsed = _parse_password_hash(stored_hash)
    if parsed is None:
        _derive(password or "", _UNUSABLE_HASH_SALT, current)
        return False

    iterations, salt, expected = parsed
    actual = _derive(password or "", salt, iterations)
    if iterations < current:
        _derive(password or "", salt, current - iterations)
    return bool(password) and hmac.compare_digest(actual, expected)


def password_hash_needs_upgrade(stored_hash: str | None) -> bool:
    """True for a hash this module wrote with fewer than the current count of iterations."""
    parsed = _parse_password_hash(stored_hash)
    return parsed is not None and parsed[0] < password_iterations()


def _json_dumps(data: dict[str, Any]) -> bytes:
    return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")


def create_access_token(
    *,
    subject: str,
    user_public_id: str,
    role_codes: list[str],
    token_version: int,
    expires_minutes: int | None = None,
) -> str:
    settings = get_settings()
    now = int(time.time())
    expiry_minutes = expires_minutes or settings.jwt_expires_minutes

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "user_public_id": user_public_id,
        "role_codes": role_codes,
        # The account's token_version when the token was issued; a later reset, disable, retire or end-sign-ins
        # raises the account's, and the token is refused (TB-1 TB1-204 part a).
        "ver": token_version,
        "iat": now,
        "exp": now + expiry_minutes * 60,
    }

    header_part = _base64url_encode(_json_dumps(header))
    payload_part = _base64url_encode(_json_dumps(payload))
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(settings.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_part}.{payload_part}.{_base64url_encode(signature)}"


def token_version_of(payload: dict[str, Any]) -> int:
    """The token_version a decoded token carries. A token issued before TB1-204 part a has none: 0, the starting value
    of every account active when revision 20260908_0048 ran, so deploying the change ended no active account's
    sign-in. Accounts already disabled or retired then started at 1, so their older tokens stay ended."""
    return payload.get("ver", 0)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()

    # A token is base64url text. Anything else - a non-ASCII character in the header, above all - is refused here
    # as a bad token; it used to raise UnicodeEncodeError, which answered 500 (TB-1 TB1-204 part a, item f).
    if not token.isascii():
        raise TokenError("Token format is invalid.")

    try:
        header_part, payload_part, signature_part = token.split(".")
    except ValueError as exc:
        raise TokenError("Token format is invalid.") from exc

    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    expected_signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    try:
        actual_signature = _base64url_decode(signature_part)
    except Exception as exc:
        raise TokenError("Token signature is invalid.") from exc

    if not hmac.compare_digest(actual_signature, expected_signature):
        raise TokenError("Token signature is invalid.")

    try:
        payload = json.loads(_base64url_decode(payload_part))
    except Exception as exc:
        raise TokenError("Token payload is invalid.") from exc

    if not isinstance(payload, dict):
        raise TokenError("Token payload is invalid.")

    expires_at = payload.get("exp", 0)
    if not isinstance(expires_at, int) or isinstance(expires_at, bool):
        raise TokenError("Token payload is invalid.")
    if expires_at < int(time.time()):
        raise TokenError("Token has expired.")

    version = payload.get("ver", 0)
    if not isinstance(version, int) or isinstance(version, bool) or version < 0:
        raise TokenError("Token payload is invalid.")

    if not payload.get("sub") or not payload.get("user_public_id"):
        raise TokenError("Token subject is invalid.")

    return payload
