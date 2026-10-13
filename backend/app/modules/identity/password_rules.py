"""What a new password must be (TB-1 TB1-204 part a; the owner's decision of 7 October 2026).

Checked wherever a password is set - today only the server account tool's `create` and `reset-password`, generated or
chosen (`--password-stdin`). Passwords already stored are not checked: only their hash is kept. The development and
CI seed's `password` is exempt: `seed-demo-users` sets it, and only under a development APP_ENV.

No rule asks for a capital, a digit or a symbol: current guidance (NIST SP 800-63B) advises against them, and length
with a list of obvious passwords does more.
"""

from __future__ import annotations

MIN_PASSWORD_LENGTH = 12
# The sign-in request's own limit (identity/schemas.py): a longer password could be set and then never used.
MAX_PASSWORD_LENGTH = 200

# Refused anywhere in a password, in any case: the words and runs every guessing list starts with.
OBVIOUS_FRAGMENTS = (
    "password",
    "passw0rd",
    "qwerty",
    "asdfgh",
    "zxcvbn",
    "123456",
    "654321",
    "abcdef",
    "letmein",
    "welcome",
    "changeme",
    "iloveyou",
    "admin",
    "pbl",
)

RULES_TEXT = (
    f"A password must be {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters, must not contain the username, "
    "must not contain an obvious word or run such as 'password', 'qwerty', 'admin', 'pbl' or '123456', and must "
    "not be one character repeated."
)


def _is_utf8(text: str) -> bool:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def password_problem(password: str, username: str) -> str | None:
    """Why `password` may not be set for `username`, or None when it may. The reason names no part of it."""
    lowered = password.lower()
    # What the sign-in request refuses (identity/schemas.py) could be set and then never used.
    if "\x00" in password or not _is_utf8(password):
        return "it holds a character that cannot be typed at sign-in"
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"it is shorter than {MIN_PASSWORD_LENGTH} characters"
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"it is longer than {MAX_PASSWORD_LENGTH} characters"
    if len(set(password)) == 1:
        return "it is one character repeated"
    if username.strip() and username.strip().lower() in lowered:
        return "it contains the username"
    if any(fragment in lowered for fragment in OBVIOUS_FRAGMENTS):
        return "it contains an obvious word or run"
    return None
